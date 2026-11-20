import html
import json
from datetime import datetime, timedelta, timezone

import httpx
from sqlmodel import Session, SQLModel, create_engine, select

from backend.collect import collect_region
from backend.models import Job, VisitorJobState
from backend.models.collection import JobCatalogueState
from backend.routers.jobs import list_jobs
from backend.services import yc_catalogue


def test_daily_incremental_refresh_and_closure(monkeypatch):
    now = datetime(2026, 11, 20, 1, 23, tzinfo=timezone.utc)
    monkeypatch.setattr(yc_catalogue, "REQUEST_DELAY_SECONDS", 0)
    monkeypatch.setattr(yc_catalogue, "_public_job_listings", lambda *a, **kw: [{"slug": "example"}])
    monkeypatch.setattr(yc_catalogue, "_parse_job_page", lambda _: {"description": "Full description"})
    postings = [{
        "url": "/companies/example/jobs/Ab12Cd3-engineer",
        "title": "Engineer", "location": "Bengaluru", "companyName": "Example",
    }]
    paths = []
    blocked = False
    malformed = False

    def respond(request):
        paths.append(request.url.path)
        if blocked:
            return httpx.Response(429)
        if malformed:
            return httpx.Response(200, text="<html>Unexpected source page</html>")
        if request.url.path == "/companies/example/jobs":
            data = {"component": "WaasShowJobsPage", "props": {
                "company": {}, "jobPostings": postings,
            }}
            return httpx.Response(200, text=f'<div data-page="{html.escape(json.dumps(data))}"></div>')
        return httpx.Response(200, text="detail")

    def run(session, hours):
        refresh = yc_catalogue.IncrementalCatalogue(now + timedelta(hours=hours), httpx.MockTransport(respond))
        return collect_region(session, "india", refresh.collect), refresh

    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        first, _ = run(session, 0)
        job = session.exec(select(Job)).one()
        job_id = job.id
        assert (first.status, first.jobs_saved, job.description) == ("completed", 1, "Full description")
        assert paths == ["/companies/example/jobs", postings[0]["url"]]
        session.add(VisitorJobState(owner_hash="owner", job_id=job_id, is_starred=True))
        session.commit()

        postings[0]["url"] = "/companies/example/jobs/Ab12Cd3-renamed"
        paths.clear()
        assert run(session, 24)[0].status == "completed"
        assert paths == ["/companies/example/jobs"]
        assert session.exec(select(Job)).one().id == job_id
        assert job.description == "Full description"
        assert job.source_url.endswith("Ab12Cd3-renamed")

        removed = postings.pop()
        assert run(session, 48)[0].status == "completed"
        assert session.get(JobCatalogueState, job_id).closed_at is None
        assert run(session, 49)[0].status == "completed"
        assert session.get(JobCatalogueState, job_id).closed_at is None

        blocked = True
        failed, refresh = run(session, 72)
        assert failed.status == "failed"
        assert session.get(JobCatalogueState, job_id).closed_at is None
        calls = len(paths)
        assert collect_region(session, "us", refresh.collect).status == "failed"
        assert len(paths) == calls

        blocked = False
        malformed = True
        assert run(session, 73)[0].status == "failed"
        assert session.get(JobCatalogueState, job_id).closed_at is None

        malformed = False
        assert run(session, 96)[0].status == "completed"
        assert session.get(JobCatalogueState, job_id).closed_at is not None
        args = dict(limit=10, offset=0, region="india", matched=False, session=session)
        assert list_jobs(**args, application_status="active", owner_hash="owner") == []
        assert list_jobs(**args, application_status="all", owner_hash="visitor") == []
        assert list_jobs(**args, application_status="starred", owner_hash="owner")[0]["is_closed"]

        postings.append(removed)
        assert run(session, 120)[0].status == "completed"
        assert session.get(JobCatalogueState, job_id).closed_at is None
        assert list_jobs(**args, application_status="active", owner_hash="owner")[0]["id"] == job_id


def test_existing_canonical_url_is_reused_when_old_title_slug_also_exists(monkeypatch):
    monkeypatch.setattr(yc_catalogue, "REQUEST_DELAY_SECONDS", 0)
    monkeypatch.setattr(yc_catalogue, "_public_job_listings", lambda *a, **kw: [{"slug": "example"}])
    path = "/companies/example/jobs/Ab12Cd3-current"
    page = {"component": "WaasShowJobsPage", "props": {
        "company": {}, "jobPostings": [{"url": path, "title": "Engineer", "location": "Remote (US)"}],
    }}
    calls = []

    def respond(request):
        calls.append(request.url.path)
        return httpx.Response(200, text=f'<div data-page="{html.escape(json.dumps(page))}"></div>')

    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        current = Job(source_url=f"{yc_catalogue.YC_BASE}{path}", title="Current title",
                      description="Already enriched", company_slug="example", company_name="Example",
                      locations=["Remote (US)"])
        duplicate = Job(source_url=f"{yc_catalogue.YC_BASE}/companies/example/jobs/Ab12Cd3-old",
                        title="Old title", company_slug="example", company_name="Example",
                        locations=["Remote (US)"])
        session.add_all([current, duplicate])
        session.commit()
        session.add(VisitorJobState(owner_hash="owner", job_id=duplicate.id, is_starred=True))
        session.commit()

        refresh = yc_catalogue.IncrementalCatalogue(transport=httpx.MockTransport(respond))
        result = collect_region(session, "us", refresh.collect)
        assert (result.status, result.jobs_saved, result.errors) == ("completed", 1, 0)
        assert calls == ["/companies/example/jobs"]
        assert current.title == "Engineer" and current.description == "Already enriched"
        assert duplicate.source_url.endswith("-old")
        assert session.exec(select(VisitorJobState)).one().job_id == duplicate.id
        assert session.get(JobCatalogueState, duplicate.id).first_missing_at is not None
