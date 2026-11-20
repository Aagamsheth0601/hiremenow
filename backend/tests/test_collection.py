from datetime import datetime, timedelta, timezone
from functools import partial

import httpx
from sqlmodel import Session, SQLModel, create_engine, select
from backend.collect import collect_region
from backend.models import Job
from backend.models.collection import CollectionRun
from backend.services.yc_scraper import ScrapeStats, _upsert_job
from backend.routers.jobs import collection_freshness, _serialize
from backend.services import yc_scraper


def test_refresh_preserves_first_seen_and_advances_last_checked():
    engine = create_engine('sqlite://')
    SQLModel.metadata.create_all(engine)
    old = datetime.now(timezone.utc) - timedelta(days=26)
    with Session(engine) as session:
        session.add(Job(source_url='https://www.ycombinator.com/companies/example/jobs/one', title='Old', company_name='Example', company_slug='example', scraped_at=old, updated_at=old, founders=[{'name':'Founder'}], contact_emails=['hello@example.com']))
        session.commit()
        stats = ScrapeStats()
        _upsert_job(session, company={'name':'Example','slug':'example','all_locations':'IN'}, job_path='/companies/example/jobs/one', parsed={'title':'New','description':'Python','locations':[]},stats=stats)
        session.commit()
        job = session.exec(select(Job)).one()
        output = _serialize(job)
        assert job.title == 'New' and stats.jobs_updated == 1
        assert output['last_checked_at'] > output['scraped_at']
        assert output['last_checked_at'].endswith('+00:00')
        assert job.contact_emails == ['hello@example.com']


def test_collection_is_unpersonalized_and_failure_preserves_success():
    engine = create_engine('sqlite://')
    SQLModel.metadata.create_all(engine)
    def success(session, **kwargs):
        assert kwargs['region'] == 'india'
        assert 'match_profile' not in kwargs and 'search_terms' not in kwargs
        return ScrapeStats(companies_visited=2,jobs_seen=3,jobs_updated=3)
    with Session(engine) as session:
        assert collect_region(session,'india',success).status == 'completed'
        good = collection_freshness('india',session,'test')['last_success_at']
        assert collect_region(session,'india',lambda *_a,**_k: ScrapeStats(errors=1)).status == 'failed'
        state = collection_freshness('india',session,'test')
        assert state['status'] == 'failed' and state['last_success_at'] == good
        assert collection_freshness('us',session,'test')['stale']


def test_partial_and_interrupted_runs_are_not_success():
    engine = create_engine('sqlite://')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        assert collect_region(session,'india',lambda *_a,**_k: ScrapeStats(jobs_updated=1,errors=1)).status == 'partial'
        assert collection_freshness('india',session,'test')['last_success_at'] is None
        session.add(CollectionRun(region='us',started_at=datetime.now(timezone.utc)-timedelta(hours=3)))
        session.commit()
        assert collection_freshness('us',session,'test')['status'] == 'interrupted'


def test_rate_limit_stops_both_regions_and_preserves_saved_jobs(monkeypatch):
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    paths = [f"/companies/example/jobs/{number}" for number in range(3)]
    requests = []

    def respond(request):
        requests.append(request.url.path)
        return httpx.Response(200, text="job") if len(requests) == 1 else httpx.Response(429)

    client = partial(httpx.Client, transport=httpx.MockTransport(respond))
    monkeypatch.setattr(yc_scraper.httpx, "Client", client)
    monkeypatch.setattr(yc_scraper, "REQUEST_DELAY_SECONDS", 0)
    monkeypatch.setattr(yc_scraper, "_expanded_job_listings", lambda *args, **kwargs: [{
        "slug": "example", "name": "Example", "_job_paths": paths, "_job_locations": {},
    }])
    monkeypatch.setattr(yc_scraper, "_parse_job_page", lambda html: {
        "title": "Engineer", "description": "Python", "locations": [],
    })
    scrape = partial(yc_scraper.scrape_yc_jobs, rate_limit=yc_scraper.YCRateLimit())

    with Session(engine) as session:
        india = collect_region(session, "india", scrape)
        us = collect_region(session, "us", scrape)
        assert (india.status, india.jobs_saved, india.errors) == ("partial", 1, 1)
        assert (us.status, us.jobs_saved, us.errors) == ("failed", 0, 1)
        assert session.exec(select(Job)).one().title == "Engineer"
    assert requests == paths[:2]
