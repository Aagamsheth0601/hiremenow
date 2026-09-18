import httpx

from backend.routers.jobs import _matches_region
from backend.services.yc_scraper import _public_job_listings


def test_public_yc_jobs_are_read_and_region_codes_match() -> None:
    html = """
    <ul>
      <li><div><a href="/companies/india-co">India Co (S24) • Builds APIs</a>
        <a href="/companies/india-co/jobs/abc-backend-engineer">Backend Engineer</a>
        <div>Full-time • Engineering • IN / Remote (IN)</div></div></li>
      <li><div><a href="/companies/us-co">US Co (W25) • Builds tools</a>
        <a href="/companies/us-co/jobs/xyz-designer">Product Designer</a>
        <div>Full-time • Design • San Francisco, CA, US</div></div></li>
    </ul>
    """
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text=html))
    with httpx.Client(transport=transport) as client:
        india = _public_job_listings(client, region="india", search_terms=["Backend Engineer"], company_limit=10)
        us = _public_job_listings(client, region="us", search_terms=["Designer"], company_limit=10)
    assert [company["slug"] for company in india] == ["india-co"]
    assert india[0]["_job_paths"] == ["/companies/india-co/jobs/abc-backend-engineer"]
    assert [company["slug"] for company in us] == ["us-co"]
    assert _matches_region(["IN / Remote (IN)"], "india")
    assert _matches_region(["San Francisco, CA, US"], "us")
