from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, func, select

from backend.db import get_session
from backend.models import Job
from backend.services.yc_scraper import scrape_yc_jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/scrape")
def trigger_scrape(
    company_limit: int = Query(default=10, ge=1, le=200),
    job_limit_per_company: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
) -> dict:
    stats = scrape_yc_jobs(
        session,
        company_limit=company_limit,
        job_limit_per_company=job_limit_per_company,
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
