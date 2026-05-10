from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, func, select

from backend.db import get_session
from backend.models import Job, JobPreferences, Resume
from backend.services.matcher import build_profile, passes_threshold, score_job
from backend.services.outreach import (
    OutreachError,
    draft_email,
    draft_linkedin,
)
from backend.services.yc_scraper import enrich_company_for_job, scrape_yc_jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])

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
    matched: bool = Query(default=True),
    session: Session = Depends(get_session),
) -> list[dict]:
    all_rows = session.exec(select(Job).order_by(Job.scraped_at.desc())).all()

    if region:
        all_rows = [j for j in all_rows if _matches_region(j.locations, region)]

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
            return [_serialize(j, score=_to_ten(s)) for j, s in page]

    page_rows = all_rows[offset : offset + limit]
    return [_serialize(j) for j in page_rows]


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
            draft = draft_email(job, resume)
            return {
                "kind": "email",
                "subject": draft.subject,
                "body": draft.body,
                "recipients": job.contact_emails or [],
                "founders": job.founders or [],
            }
        message = draft_linkedin(job, resume)
        return {
            "kind": "linkedin",
            "message": message,
            "founders": job.founders or [],
        }
    except OutreachError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e)
        ) from e


def _serialize(j: Job, *, score: float | None = None) -> dict:
    out = {
        "id": j.id,
        "title": j.title,
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
        "source_url": j.source_url,
        "scraped_at": j.scraped_at.isoformat(),
    }
    if score is not None:
        out["match_score"] = round(score, 1)
    return out


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
