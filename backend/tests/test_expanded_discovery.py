import html
import json

import httpx

from backend.services import yc_scraper as scraper


def test_search_expands_company_jobs_deduplicates_and_filters_region(monkeypatch):
    monkeypatch.setattr(scraper.time, 'sleep', lambda _: None)
    monkeypatch.setattr(scraper, '_public_job_listings', lambda *a, **k: [])
    postings = [
        {'url': '/companies/new-co/jobs/backend', 'companyName': 'New Co', 'location': 'Bengaluru'},
        {'url': '/companies/new-co/jobs/us-only', 'location': 'Remote (US)'},
        {'url': '/companies/new-co/jobs/indiana', 'location': 'Indianapolis, IN, US'},
    ]
    def respond(request):
        if request.url.host == 'www.workatastartup.com':
            return httpx.Response(200, json={'jobs': [{'companySlug': 'new-co'}] * 2})
        data = html.escape(json.dumps({'props': {'jobPostings': postings}}), quote=True)
        return httpx.Response(200, text=f'<div data-page="{data}"></div>')
    stats = scraper.ScrapeStats()
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        companies = scraper._expanded_job_listings(client, region='india', company_limit=200, stats=stats)
    assert len(companies) == 1
    assert companies[0]['_job_paths'] == ['/companies/new-co/jobs/backend']
    assert stats.errors == 0


def test_failed_search_preserves_landing_jobs_and_records_errors(monkeypatch):
    monkeypatch.setattr(scraper.time, 'sleep', lambda _: None)
    existing = {'slug': 'old', '_job_paths': ['/companies/old/jobs/one'], '_job_locations': {}}
    monkeypatch.setattr(scraper, '_public_job_listings', lambda *a, **k: [existing])
    stats = scraper.ScrapeStats()
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(503))) as client:
        companies = scraper._expanded_job_listings(client, region='india', company_limit=200, stats=stats)
    assert companies == [existing]
    assert stats.errors == 6
