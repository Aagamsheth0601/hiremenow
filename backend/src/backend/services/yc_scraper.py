from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
from bs4 import BeautifulSoup
from sqlmodel import Session, select

from backend.models import Job

log = logging.getLogger(__name__)

YC_BASE = "https://www.ycombinator.com"
ALGOLIA_APP_ID = "45BWZJ1SGC"
ALGOLIA_SEARCH_KEY = (
    "NzllNTY5MzJiZGM2OTY2ZTQwMDEzOTNhYWZiZGRjODlhYzVkNjBmOGRjNzJiMWM4ZTU0ZDlhYTZjOTJiMjlhMW"
    "FuYWx5dGljc1RhZ3M9eWNkYyZyZXN0cmljdEluZGljZXM9WUNDb21wYW55X3Byb2R1Y3Rpb24lMkNZQ0NvbXBh"
    "bnlfQnlfTGF1bmNoX0RhdGVfcHJvZHVjdGlvbiZ0YWdGaWx0ZXJzPSU1QiUyMnljZGNfcHVibGljJTIyJTVE"
)
ALGOLIA_INDEX = "YCCompany_production"
USER_AGENT = "hiremenow/0.1 (+personal job-hunt tool; public-data only)"
REQUEST_DELAY_SECONDS = 0.5


@dataclass
class ScrapeStats:
    companies_visited: int = 0
    jobs_seen: int = 0
    jobs_inserted: int = 0
    jobs_updated: int = 0
    errors: int = 0


def _algolia_search_hiring(client: httpx.Client, hits_per_page: int) -> list[dict[str, Any]]:
    url = f"https://{ALGOLIA_APP_ID}-dsn.algolia.net/1/indexes/{ALGOLIA_INDEX}/query"
    headers = {
        "X-Algolia-API-Key": ALGOLIA_SEARCH_KEY,
        "X-Algolia-Application-Id": ALGOLIA_APP_ID,
        "Content-Type": "application/json",
    }
    body = {
        "query": "",
        "hitsPerPage": hits_per_page,
        "page": 0,
        "facetFilters": ["isHiring:true"],
    }
    r = client.post(url, headers=headers, json=body, timeout=15.0)
    r.raise_for_status()
    return r.json().get("hits", [])


def _fetch(client: httpx.Client, url: str) -> str | None:
    try:
        r = client.get(url, timeout=15.0)
        r.raise_for_status()
        return r.text
    except httpx.HTTPError as e:
        log.warning("fetch failed %s: %s", url, e)
        return None


def _parse_company_jobs(html: str, company_slug: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    paths: list[str] = []
    seen: set[str] = set()
    prefix = f"/companies/{company_slug}/jobs/"
    for a in soup.select(f"a[href^='{prefix}']"):
        href = a.get("href")
        if isinstance(href, str) and href not in seen:
            seen.add(href)
            paths.append(href)
    return paths


def _parse_job_page(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.select_one("h1.ycdc-section-title")
    if title_el is None:
        for h1 in soup.select("h1"):
            text = h1.get_text(strip=True)
            if text and not text.startswith("You're excited") and text.lower() != "compensation":
                title_el = h1
                break
    title = title_el.get_text(strip=True) if title_el else ""

    prose_blocks = soup.select("div.prose")
    if prose_blocks:
        description = "\n\n".join(
            block.get_text(separator="\n", strip=True) for block in prose_blocks
        )
    else:
        for tag in soup.select("nav, header, footer, script, style, noscript"):
            tag.decompose()
        body = soup.body or soup
        description = body.get_text(separator="\n", strip=True)
    if len(description) > 8000:
        description = description[:8000]

    return {
        "title": title,
        "description": description,
        "locations": [],
    }


def _upsert_job(
    session: Session,
    *,
    company: dict[str, Any],
    job_path: str,
    parsed: dict[str, Any],
    stats: ScrapeStats,
) -> None:
    source_url = f"{YC_BASE}{job_path}"
    yc_job_id = job_path.rstrip("/").split("/")[-1]
    now = datetime.now(timezone.utc)

    existing = session.exec(select(Job).where(Job.source_url == source_url)).first()
    locations = parsed["locations"] or (
        [company["all_locations"]] if company.get("all_locations") else []
    )

    fields = dict(
        source="yc",
        source_url=source_url,
        yc_job_id=yc_job_id,
        title=parsed["title"] or "Untitled role",
        description=parsed["description"],
        company_name=company.get("name", ""),
        company_slug=company.get("slug", ""),
        company_one_liner=company.get("one_liner"),
        company_logo_url=company.get("small_logo_thumb_url"),
        company_website=company.get("website"),
        company_team_size=company.get("team_size"),
        company_industry=company.get("industry"),
        company_stage=company.get("stage"),
        company_batch=company.get("batch"),
        locations=locations,
        tags=company.get("tags") or [],
        updated_at=now,
    )

    if existing is None:
        job = Job(**fields, scraped_at=now)
        session.add(job)
        stats.jobs_inserted += 1
    else:
        for k, v in fields.items():
            setattr(existing, k, v)
        stats.jobs_updated += 1


def scrape_yc_jobs(
    session: Session,
    *,
    company_limit: int = 10,
    job_limit_per_company: int = 10,
) -> ScrapeStats:
    stats = ScrapeStats()
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}

    with httpx.Client(headers=headers, follow_redirects=True) as client:
        try:
            companies = _algolia_search_hiring(client, hits_per_page=company_limit)
        except httpx.HTTPError as e:
            log.error("algolia search failed: %s", e)
            stats.errors += 1
            return stats

        for company in companies:
            slug = company.get("slug")
            if not slug:
                continue
            stats.companies_visited += 1

            company_url = f"{YC_BASE}/companies/{slug}"
            html = _fetch(client, company_url)
            time.sleep(REQUEST_DELAY_SECONDS)
            if html is None:
                stats.errors += 1
                continue

            job_paths = _parse_company_jobs(html, slug)[:job_limit_per_company]

            for path in job_paths:
                stats.jobs_seen += 1
                job_url = f"{YC_BASE}{path}"
                job_html = _fetch(client, job_url)
                time.sleep(REQUEST_DELAY_SECONDS)
                if job_html is None:
                    stats.errors += 1
                    continue
                try:
                    parsed = _parse_job_page(job_html)
                    _upsert_job(
                        session,
                        company=company,
                        job_path=path,
                        parsed=parsed,
                        stats=stats,
                    )
                except Exception as e:
                    log.warning("upsert failed for %s: %s", job_url, e)
                    stats.errors += 1

            session.commit()

    return stats
