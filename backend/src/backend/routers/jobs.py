from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import Session, func, select

from backend.db import get_session
from backend.models import Draft, Job, JobPreferences, Resume, VisitorJobState
from backend.services.matcher import build_profile, passes_threshold, score_job, search_terms_from_profile
from backend.services.outreach import (
    OutreachError,
    draft_email,
    draft_linkedin,
)
from backend.services.yc_scraper import (
    enrich_company_for_job,
    enrich_jobs_batch,
    scrape_yc_jobs,
)
from backend.visitor import get_visitor_hash

router = APIRouter(prefix="/jobs", tags=["jobs"])

APPLICATION_STATUSES = ("reached_out", "applied", "replied", "rejected")


def _resume_for(session: Session, owner_hash: str) -> Resume | None:
    return session.exec(
        select(Resume).where(Resume.owner_hash == owner_hash).order_by(Resume.uploaded_at.desc())
    ).first()


def _prefs_for(session: Session, owner_hash: str) -> JobPreferences | None:
    return session.exec(select(JobPreferences).where(JobPreferences.owner_hash == owner_hash)).first()


def _states_for(session: Session, owner_hash: str, job_ids: list[int]) -> dict[int, VisitorJobState]:
    if not job_ids:
        return {}
    rows = session.exec(
        select(VisitorJobState).where(
            VisitorJobState.owner_hash == owner_hash,
            VisitorJobState.job_id.in_(job_ids),
        )
    ).all()
    return {row.job_id: row for row in rows}


def _state_for(session: Session, owner_hash: str, job_id: int) -> VisitorJobState:
    state = session.exec(select(VisitorJobState).where(
        VisitorJobState.owner_hash == owner_hash, VisitorJobState.job_id == job_id
    )).first()
    return state or VisitorJobState(owner_hash=owner_hash, job_id=job_id)


class StatusPayload(BaseModel):
    status: str | None


class StarPayload(BaseModel):
    is_starred: bool


class EnrichBatchPayload(BaseModel):
    job_ids: list[int]
    force: bool = False

_INDIA_TERMS = (
    "india", "bangalore", "bengaluru", "mumbai", "delhi", "hyderabad",
    "pune", "chennai", "gurgaon", "gurugram", "noida", "kolkata",
    "ahmedabad", "jaipur",
)
_US_TERMS = (
    "united states", "usa", "u.s.", "san francisco", "new york", "nyc",
    "los angeles", "boston", "seattle", "chicago", "austin", "denver",
    "miami", "atlanta", "dallas", "houston", "san jose", "palo alto",
    "mountain view", "menlo park", "berkeley", "oakland", "sunnyvale",
    "santa clara", "redwood city", "cambridge",
)
_US_STATE_RE = re.compile(r",\s*[A-Z]{2}\b")


def _matches_region(locations: list[str], region: str, *, title: str = "") -> bool:
    blob = " ".join(locations or []).lower()
    if title:
        blob += " " + title.lower()
    raw = " ".join(locations or []) + " " + title
    is_india = any(t in blob for t in _INDIA_TERMS)
    is_us = any(t in blob for t in _US_TERMS) or bool(_US_STATE_RE.search(raw))
    is_remote = "remote" in blob
    if is_remote and not is_india and not is_us:
        return True
    if region == "india":
        return is_india
    if region == "us":
        if is_india:
            return False
        return is_us
    return True


@router.post("/scrape")
def trigger_scrape(
    company_limit: int = Query(default=10, ge=1, le=200),
    job_limit_per_company: int = Query(default=10, ge=1, le=50),
    region: str | None = Query(default=None, pattern="^(us|india)$"),
    session: Session = Depends(get_session),
    owner_hash: str = Depends(get_visitor_hash),
) -> dict:
    search_terms: list[str] | None = None
    resume = _resume_for(session, owner_hash)
    prefs = _prefs_for(session, owner_hash)
    profile = build_profile(resume, prefs)
    if not profile.is_empty():
        search_terms = search_terms_from_profile(profile)

    match_profile = profile if not profile.is_empty() else None

    stats = scrape_yc_jobs(
        session,
        company_limit=company_limit,
        job_limit_per_company=job_limit_per_company,
        region=region,
        search_terms=search_terms,
        match_profile=match_profile,
    )
    total = session.exec(select(func.count(Job.id))).one()
    return {
        "companies_visited": stats.companies_visited,
        "jobs_seen": stats.jobs_seen,
        "jobs_inserted": stats.jobs_inserted,
        "jobs_updated": stats.jobs_updated,
        "jobs_skipped": stats.jobs_skipped,
        "errors": stats.errors,
        "total_jobs_in_db": total,
    }


@router.get("/count")
def jobs_count(
    session: Session = Depends(get_session), owner_hash: str = Depends(get_visitor_hash)
) -> dict:
    total = session.exec(select(func.count(Job.id))).one()
    return {"total": total}


@router.get("")
def list_jobs(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    region: str | None = Query(default=None, pattern="^(us|india)$"),
    application_status: str | None = Query(
        default=None,
        pattern="^(active|reached_out|applied|replied|rejected|starred|all)$",
    ),
    matched: bool = Query(default=True),
    session: Session = Depends(get_session),
    owner_hash: str = Depends(get_visitor_hash),
) -> list[dict]:
    all_rows = session.exec(select(Job).order_by(Job.scraped_at.desc())).all()

    if region:
        all_rows = [j for j in all_rows if _matches_region(j.locations, region, title=j.title or "")]

    states = _states_for(session, owner_hash, [j.id for j in all_rows if j.id is not None])
    if application_status and application_status != "all":
        if application_status == "active":
            all_rows = [j for j in all_rows if states.get(j.id) is None or states[j.id].application_status is None]
        elif application_status == "starred":
            all_rows = [j for j in all_rows if states.get(j.id) is not None and states[j.id].is_starred]
        else:
            all_rows = [j for j in all_rows if states.get(j.id) is not None and states[j.id].application_status == application_status]

    scored: list[tuple[Job, float, dict]] = []
    if matched:
        resume = _resume_for(session, owner_hash)
        prefs = _prefs_for(session, owner_hash)
        profile = build_profile(resume, prefs)
        if profile.is_empty():
            return []
        for j in all_rows:
            s, breakdown = score_job(j, profile)
            if passes_threshold(s, breakdown):
                scored.append((j, s, breakdown))
        scored.sort(key=lambda x: x[1], reverse=True)
        page = scored[offset : offset + limit]
        page_ids = [j.id for j, _, _ in page if j.id is not None]
        kinds_map = _draft_kinds_for(session, owner_hash, page_ids)
        return [
            _serialize(j, score=_to_ten(s), match_details=details, draft_kinds=kinds_map.get(j.id, []), state=states.get(j.id))
            for j, s, details in page
        ]

    page_rows = all_rows[offset : offset + limit]
    page_ids = [j.id for j in page_rows if j.id is not None]
    kinds_map = _draft_kinds_for(session, owner_hash, page_ids)
    return [_serialize(j, draft_kinds=kinds_map.get(j.id, []), state=states.get(j.id)) for j in page_rows]


def _draft_kinds_for(session: Session, owner_hash: str, job_ids: list[int]) -> dict[int, list[str]]:
    if not job_ids:
        return {}
    rows = session.exec(
        select(Draft.job_id, Draft.kind).where(Draft.owner_hash == owner_hash, Draft.job_id.in_(job_ids))
    ).all()
    result: dict[int, list[str]] = {}
    for jid, kind in rows:
        result.setdefault(jid, []).append(kind)
    return result


def _to_ten(raw: float) -> float:
    return round(min(raw / 2.0, 10.0), 1)


@router.post("/{job_id}/draft")
def draft_outreach(
    job_id: int,
    kind: str = Query(..., pattern="^(email|linkedin)$"),
    session: Session = Depends(get_session),
    owner_hash: str = Depends(get_visitor_hash),
) -> dict:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    resume = _resume_for(session, owner_hash)
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload a resume first.",
        )

    try:
        enrich_company_for_job(session, job)
    except Exception as e:
        # enrichment is best-effort; don't block drafting
        import logging
        logging.getLogger(__name__).warning("enrich failed for job %s: %s", job.id, e)

    try:
        if kind == "email":
            email = draft_email(job, resume)
            _upsert_draft(session, owner_hash, job.id, kind, subject=email.subject, body=email.body)
            return {
                "kind": "email",
                "subject": email.subject,
                "body": email.body,
                "recipients": job.contact_emails or [],
                "founders": job.founders or [],
                "cached": False,
            }
        message = draft_linkedin(job, resume)
        _upsert_draft(session, owner_hash, job.id, kind, message=message)
        return {
            "kind": "linkedin",
            "message": message,
            "founders": job.founders or [],
            "cached": False,
        }
    except OutreachError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e)
        ) from e


def _upsert_draft(
    session: Session,
    owner_hash: str,
    job_id: int | None,
    kind: str,
    *,
    subject: str | None = None,
    body: str | None = None,
    message: str | None = None,
) -> None:
    if job_id is None:
        return
    existing = session.exec(
        select(Draft).where(Draft.owner_hash == owner_hash, Draft.job_id == job_id, Draft.kind == kind)
    ).first()
    now = datetime.now(timezone.utc)
    if existing is None:
        session.add(
            Draft(
                owner_hash=owner_hash,
                job_id=job_id,
                kind=kind,
                subject=subject,
                body=body,
                message=message,
                updated_at=now,
            )
        )
    else:
        existing.subject = subject
        existing.body = body
        existing.message = message
        existing.updated_at = now
        session.add(existing)
    session.commit()


@router.get("/{job_id}/draft")
def get_cached_draft(
    job_id: int,
    kind: str = Query(..., pattern="^(email|linkedin)$"),
    session: Session = Depends(get_session),
    owner_hash: str = Depends(get_visitor_hash),
) -> dict:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    cached = session.exec(
        select(Draft).where(Draft.owner_hash == owner_hash, Draft.job_id == job_id, Draft.kind == kind)
    ).first()
    if cached is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No cached draft.")

    if kind == "email":
        return {
            "kind": "email",
            "subject": cached.subject or "",
            "body": cached.body or "",
            "recipients": job.contact_emails or [],
            "founders": job.founders or [],
            "cached": True,
            "updated_at": cached.updated_at.isoformat(),
        }
    return {
        "kind": "linkedin",
        "message": cached.message or "",
        "founders": job.founders or [],
        "cached": True,
        "updated_at": cached.updated_at.isoformat(),
    }


@router.post("/enrich-batch")
def enrich_batch(
    payload: EnrichBatchPayload,
    session: Session = Depends(get_session),
    owner_hash: str = Depends(get_visitor_hash),
) -> dict[int, dict]:
    if not payload.job_ids:
        return {}
    jobs = session.exec(select(Job).where(Job.id.in_(payload.job_ids))).all()
    return enrich_jobs_batch(session, jobs, force=payload.force)


def _serialize(
    j: Job, *, score: float | None = None, match_details: dict | None = None,
    draft_kinds: list[str] | None = None, state: VisitorJobState | None = None,
) -> dict:
    out = {
        "id": j.id,
        "title": j.title,
        "description": j.description or "",
        "draft_kinds": draft_kinds or [],
        "company_name": j.company_name,
        "company_one_liner": j.company_one_liner,
        "company_industry": j.company_industry,
        "company_stage": j.company_stage,
        "company_batch": j.company_batch,
        "company_website": j.company_website,
        "locations": j.locations,
        "tags": j.tags,
        "founders": j.founders or [],
        "contact_emails": j.contact_emails or [],
        "application_status": state.application_status if state else None,
        "status_updated_at": state.status_updated_at.isoformat() if state and state.status_updated_at else None,
        "is_starred": bool(state.is_starred) if state else False,
        "source_url": j.source_url,
        "scraped_at": j.scraped_at.isoformat(),
    }
    if score is not None:
        out["match_score"] = round(score, 1)
        out["match_details"] = match_details or {}
    return out


@router.patch("/{job_id}/status")
def update_status(
    job_id: int,
    payload: StatusPayload,
    session: Session = Depends(get_session),
    owner_hash: str = Depends(get_visitor_hash),
) -> dict:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    new_status = payload.status
    if new_status is not None and new_status not in APPLICATION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Allowed: {list(APPLICATION_STATUSES)} or null.",
        )

    state = _state_for(session, owner_hash, job_id)
    state.application_status = new_status
    state.status_updated_at = datetime.now(timezone.utc) if new_status is not None else None
    session.add(state)
    session.commit()
    session.refresh(state)
    return {
        "application_status": state.application_status,
        "status_updated_at": state.status_updated_at.isoformat() if state.status_updated_at else None,
    }


@router.patch("/{job_id}/star")
def update_star(
    job_id: int,
    payload: StarPayload,
    session: Session = Depends(get_session),
    owner_hash: str = Depends(get_visitor_hash),
) -> dict:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    state = _state_for(session, owner_hash, job_id)
    state.is_starred = payload.is_starred
    session.add(state)
    session.commit()
    session.refresh(state)
    return {"is_starred": bool(state.is_starred)}


@router.get("/status-counts")
def status_counts(
    region: str | None = Query(default=None, pattern="^(us|india)$"),
    session: Session = Depends(get_session),
    owner_hash: str = Depends(get_visitor_hash),
) -> dict[str, int]:
    rows = session.exec(select(Job)).all()
    if region:
        rows = [j for j in rows if _matches_region(j.locations, region, title=j.title or "")]

    resume = _resume_for(session, owner_hash)
    prefs = _prefs_for(session, owner_hash)
    profile = build_profile(resume, prefs)
    if profile.is_empty():
        rows = []
    else:
        rows = [j for j in rows if passes_threshold(*score_job(j, profile))]

    states = _states_for(session, owner_hash, [j.id for j in rows if j.id is not None])

    counts = {"all": len(rows), "active": 0, "starred": 0}
    for s in APPLICATION_STATUSES:
        counts[s] = 0
    for j in rows:
        state = states.get(j.id)
        if state is None or state.application_status is None:
            counts["active"] += 1
        elif state.application_status in counts:
            counts[state.application_status] += 1
        if state and state.is_starred:
            counts["starred"] += 1
    return counts


@router.post("/{job_id}/enrich")
def enrich_job(
    job_id: int,
    force: bool = Query(default=False),
    session: Session = Depends(get_session),
    owner_hash: str = Depends(get_visitor_hash),
) -> dict:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    enrich_company_for_job(session, job, force=force)
    return {
        "founders": job.founders or [],
        "contact_emails": job.contact_emails or [],
    }
