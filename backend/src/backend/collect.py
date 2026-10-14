"""Run with python -m backend.collect. No resume or Gemini key is used."""
import logging
from datetime import datetime, timezone
from sqlmodel import Session
from backend.db import engine, init_db
from backend.models.collection import CollectionRun
from backend.services.yc_scraper import scrape_yc_jobs

log = logging.getLogger(__name__)

def collect_region(session: Session, region: str, scrape=scrape_yc_jobs) -> CollectionRun:
    run = CollectionRun(region=region)
    session.add(run)
    session.commit()
    session.refresh(run)
    try:
        # Collect shared source data first. Ranking belongs in the visitor API.
        stats = scrape(session, region=region, company_limit=200, job_limit_per_company=50)
        run.companies = stats.companies_visited
        run.jobs_seen = stats.jobs_seen
        run.jobs_saved = stats.jobs_inserted + stats.jobs_updated
        run.errors = stats.errors
        run.status = ("completed" if stats.errors == 0 else "partial") if run.jobs_saved else "failed"
    except Exception:
        session.rollback()
        run.status = "failed"
        run.errors += 1
        # Avoid logging database connection details or provider payloads.
        log.error("Collection failed for %s", region)
    run.finished_at = datetime.now(timezone.utc)
    session.add(run)
    session.commit()
    session.refresh(run)
    return run

def main():
    init_db()
    failed = False
    for region in ("india", "us"):
        with Session(engine) as session:
            run = collect_region(session, region)
            print(f"{region}: {run.status}; companies={run.companies}; saved={run.jobs_saved}; errors={run.errors}")
            failed = failed or run.status != "completed"
    if failed:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
