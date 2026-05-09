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


@router.get("")
def list_jobs(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> list[dict]:
    rows = session.exec(
        select(Job).order_by(Job.scraped_at.desc()).offset(offset).limit(limit)
    ).all()
    return [
        {
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
            "source_url": j.source_url,
            "scraped_at": j.scraped_at.isoformat(),
        }
        for j in rows
    ]
