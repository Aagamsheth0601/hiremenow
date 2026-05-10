from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import Session, func, select

from backend.db import get_session
from backend.models import Draft, Job, JobPreferences, Resume
from backend.services.matcher import build_profile, passes_threshold, score_job
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

router = APIRouter(prefix="/jobs", tags=["jobs"])

APPLICATION_STATUSES = ("reached_out", "applied", "replied", "rejected")


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


def _matches_region(locations: list[str], region: str) -> bool:
    blob = " ".join(locations or []).lower()
    raw = " ".join(locations or [])
    is_india = any(t in blob for t in _INDIA_TERMS)
    if region == "india":
        return is_india
    if region == "us":
        if is_india:
            return False
        if any(t in blob for t in _US_TERMS):
            return True
        return bool(_US_STATE_RE.search(raw))
    return True


@router.post("/scrape")
def trigger_scrape(
    company_limit: int = Query(default=10, ge=1, le=200),
    job_limit_per_company: int = Query(default=10, ge=1, le=50),
    region: str | None = Query(default=None, pattern="^(us|india)$"),
    session: Session = Depends(get_session),
) -> dict:
    stats = scrape_yc_jobs(
        session,
        company_limit=company_limit,
        job_limit_per_company=job_limit_per_company,
        region=region,
    )
    total = session.exec(select(func.count(Job.id))).one()
    return {
        "companies_visited": stats.companies_visited,
        "jobs_seen": stats.jobs_seen,
        "jobs_inserted": stats.jobs_inserted,
        "jobs_updated": stats.jobs_updated,
        "errors": stats.errors,
        "total_jobs_in_db": total,
    }


@router.get("/count")
def jobs_count(session: Session = Depends(get_session)) -> dict:
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
) -> list[dict]:
    all_rows = session.exec(select(Job).order_by(Job.scraped_at.desc())).all()

    if region:
        all_rows = [j for j in all_rows if _matches_region(j.locations, region)]

    if application_status and application_status != "all":
        if application_status == "active":
            all_rows = [j for j in all_rows if j.application_status is None]
        elif application_status == "starred":
            all_rows = [j for j in all_rows if j.is_starred]
        else:
            all_rows = [j for j in all_rows if j.application_status == application_status]

    scored: list[tuple[Job, float]] = []
    if matched:
        resume = session.exec(select(Resume).order_by(Resume.uploaded_at.desc())).first()
        prefs = session.exec(select(JobPreferences)).first()
        profile = build_profile(resume, prefs)
        if not profile.is_empty():
            for j in all_rows:
                s, breakdown = score_job(j, profile)
                if passes_threshold(s, breakdown):
                    scored.append((j, s))
            scored.sort(key=lambda x: x[1], reverse=True)
            page = scored[offset : offset + limit]
            page_ids = [j.id for j, _ in page if j.id is not None]
            kinds_map = _draft_kinds_for(session, page_ids)
            return [
                _serialize(j, score=_to_ten(s), draft_kinds=kinds_map.get(j.id, []))
                for j, s in page
            ]

    page_rows = all_rows[offset : offset + limit]
    page_ids = [j.id for j in page_rows if j.id is not None]
    kinds_map = _draft_kinds_for(session, page_ids)
    return [_serialize(j, draft_kinds=kinds_map.get(j.id, [])) for j in page_rows]


def _draft_kinds_for(session: Session, job_ids: list[int]) -> dict[int, list[str]]:
    if not job_ids:
        return {}
    rows = session.exec(
        select(Draft.job_id, Draft.kind).where(Draft.job_id.in_(job_ids))
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
) -> dict:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    resume = session.exec(select(Resume).order_by(Resume.uploaded_at.desc())).first()
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
            _upsert_draft(session, job.id, kind, subject=email.subject, body=email.body)
            return {
                "kind": "email",
                "subject": email.subject,
                "body": email.body,
                "recipients": job.contact_emails or [],
                "founders": job.founders or [],
                "cached": False,
            }
        message = draft_linkedin(job, resume)
        _upsert_draft(session, job.id, kind, message=message)
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
        select(Draft).where(Draft.job_id == job_id, Draft.kind == kind)
    ).first()
    now = datetime.now(timezone.utc)
    if existing is None:
        session.add(
            Draft(
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
) -> dict:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    cached = session.exec(
        select(Draft).where(Draft.job_id == job_id, Draft.kind == kind)
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
) -> dict[int, dict]:
    if not payload.job_ids:
        return {}
    jobs = session.exec(select(Job).where(Job.id.in_(payload.job_ids))).all()
    return enrich_jobs_batch(session, jobs, force=payload.force)


def _serialize(
    j: Job, *, score: float | None = None, draft_kinds: list[str] | None = None
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
        "application_status": j.application_status,
        "status_updated_at": j.status_updated_at.isoformat() if j.status_updated_at else None,
        "is_starred": bool(j.is_starred),
        "source_url": j.source_url,
        "scraped_at": j.scraped_at.isoformat(),
    }
    if score is not None:
        out["match_score"] = round(score, 1)
    return out


@router.patch("/{job_id}/status")
def update_status(
    job_id: int,
    payload: StatusPayload,
    session: Session = Depends(get_session),
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

    job.application_status = new_status
    job.status_updated_at = datetime.now(timezone.utc) if new_status is not None else None
    session.add(job)
    session.commit()
    session.refresh(job)
    return {
        "application_status": job.application_status,
        "status_updated_at": job.status_updated_at.isoformat() if job.status_updated_at else None,
    }


@router.patch("/{job_id}/star")
def update_star(
    job_id: int,
    payload: StarPayload,
    session: Session = Depends(get_session),
) -> dict:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    job.is_starred = payload.is_starred
    session.add(job)
    session.commit()
    session.refresh(job)
    return {"is_starred": bool(job.is_starred)}


@router.get("/status-counts")
def status_counts(
    region: str | None = Query(default=None, pattern="^(us|india)$"),
    session: Session = Depends(get_session),
) -> dict[str, int]:
    rows = session.exec(select(Job)).all()
    if region:
        rows = [j for j in rows if _matches_region(j.locations, region)]
    counts = {"all": len(rows), "active": 0, "starred": 0}
    for s in APPLICATION_STATUSES:
        counts[s] = 0
    for j in rows:
        if j.application_status is None:
            counts["active"] += 1
        elif j.application_status in counts:
            counts[j.application_status] += 1
        if j.is_starred:
            counts["starred"] += 1
    return counts


@router.post("/{job_id}/enrich")
def enrich_job(
    job_id: int,
    force: bool = Query(default=False),
    session: Session = Depends(get_session),
) -> dict:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    enrich_company_for_job(session, job, force=force)
    return {
        "founders": job.founders or [],
        "contact_emails": job.contact_emails or [],
    }
