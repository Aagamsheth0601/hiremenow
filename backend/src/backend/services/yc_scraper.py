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
from backend.services.matcher import MatchProfile, score_job, passes_threshold

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
REQUEST_DELAY_SECONDS = 0.75

REGION_FILTERS: dict[str, str] = {
    "us": "United States of America",
    "india": "India",
}
HTTP_LIMITS = httpx.Limits(
    max_keepalive_connections=5,
    max_connections=10,
    keepalive_expiry=30.0,
)


@dataclass
class ScrapeStats:
    companies_visited: int = 0
    jobs_seen: int = 0
    jobs_inserted: int = 0
    jobs_updated: int = 0
    jobs_skipped: int = 0
    errors: int = 0


def _algolia_query(
    client: httpx.Client,
    *,
    query: str,
    hits_per_page: int,
    facet_filters: list[Any],
) -> list[dict[str, Any]]:
    url = f"https://{ALGOLIA_APP_ID}-dsn.algolia.net/1/indexes/{ALGOLIA_INDEX}/query"
    headers = {
        "X-Algolia-API-Key": ALGOLIA_SEARCH_KEY,
        "X-Algolia-Application-Id": ALGOLIA_APP_ID,
        "Content-Type": "application/json",
    }
    body = {
        "query": query,
        "hitsPerPage": hits_per_page,
        "page": 0,
        "facetFilters": facet_filters,
    }
    r = client.post(url, headers=headers, json=body, timeout=15.0)
    r.raise_for_status()
    return r.json().get("hits", [])


def _build_facet_filters(region: str | None) -> tuple[list[Any], str | None]:
    facet_filters: list[Any] = ["isHiring:true"]
    region_term: str | None = None
    if region:
        region_term = REGION_FILTERS.get(region.lower())
        if region_term:
            facet_filters.append(f"regions:{region_term}")
    return facet_filters, region_term


def _filter_by_region(hits: list[dict[str, Any]], region_term: str | None) -> list[dict[str, Any]]:
    if not region_term:
        return hits
    needle = region_term.lower()
    country_short = "united states" if needle.startswith("united states") else needle
    filtered = [
        h for h in hits
        if country_short in (h.get("all_locations") or "").lower()
        or country_short in " ".join(h.get("regions") or []).lower()
    ]
    return filtered or hits


def _algolia_search_hiring(
    client: httpx.Client,
    *,
    hits_per_page: int,
    region: str | None = None,
) -> list[dict[str, Any]]:
    facet_filters, region_term = _build_facet_filters(region)
    fetch_count = hits_per_page
    if region_term:
        fetch_count = max(hits_per_page * 3, hits_per_page)

    hits = _algolia_query(
        client, query="", hits_per_page=fetch_count, facet_filters=facet_filters,
    )
    hits = _filter_by_region(hits, region_term)
    return hits[:hits_per_page]


def _algolia_search_multi(
    client: httpx.Client,
    *,
    search_terms: list[str],
    hits_per_query: int = 15,
    region: str | None = None,
) -> list[dict[str, Any]]:
    facet_filters: list[Any] = ["isHiring:true"]

    seen_slugs: set[str] = set()
    results: list[dict[str, Any]] = []

    for term in search_terms:
        log.info("algolia targeted query: %r", term)
        try:
            hits = _algolia_query(
                client, query=term, hits_per_page=hits_per_query, facet_filters=facet_filters,
            )
        except httpx.HTTPError as e:
            log.warning("algolia query failed for %r: %s", term, e)
            continue
        for h in hits:
            slug = h.get("slug")
            if slug and slug not in seen_slugs:
                seen_slugs.add(slug)
                results.append(h)
        time.sleep(REQUEST_DELAY_SECONDS)

    log.info("targeted search: %d terms -> %d unique companies", len(search_terms), len(results))
    return results


def _fetch(client: httpx.Client, url: str) -> str | None:
    try:
        r = client.get(url, timeout=15.0)
        r.raise_for_status()
        return r.text
    except httpx.HTTPError as e:
        log.warning("fetch failed %s: %s", url, e)
        return None


def _parse_company_founders(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    founders: list[dict[str, Any]] = []
    seen: set[str] = set()

    for a in soup.select('a[href*="linkedin.com/in/"]'):
        href = (a.get("href") or "").strip()
        if not href or href in seen:
            continue
        seen.add(href)

        name: str | None = None
        node = a
        for _ in range(6):
            node = node.parent
            if node is None:
                break
            for h in node.find_all(["h1", "h2", "h3", "h4", "strong"], limit=4):
                t = h.get_text(strip=True)
                if t and 2 < len(t) < 60 and not t.lower().startswith("active "):
                    name = t
                    break
            if name:
                break

        twitter_url: str | None = None
        anchor_parent = a.parent
        if anchor_parent is not None:
            tw = anchor_parent.find(
                "a",
                href=lambda h: bool(h)
                and ("twitter.com/" in h or "x.com/" in h),
            )
            if tw:
                twitter_url = tw.get("href")

        founders.append({
            "name": name or "Founder",
            "linkedin_url": href,
            "twitter_url": twitter_url,
        })

    return founders[:6]


_EMAIL_PATHS = ("", "/careers", "/contact", "/about", "/jobs")
_EMAIL_PRIORITY = ("careers@", "jobs@", "hiring@", "recruit@", "talent@",
                   "founders@", "hello@", "contact@", "team@", "info@")


def _discover_emails(client: httpx.Client, website: str | None) -> list[str]:
    if not website:
        return []
    if not website.startswith(("http://", "https://")):
        website = "https://" + website
    base = website.rstrip("/")
    found: set[str] = set()
    for path in _EMAIL_PATHS:
        url = base + path
        try:
            r = client.get(url, timeout=8.0, follow_redirects=True)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.select('a[href^="mailto:"]'):
                raw = (a.get("href") or "").replace("mailto:", "").split("?")[0]
                email = raw.strip().lower()
                if not email or "@" not in email:
                    continue
                local, _, domain = email.partition("@")
                if not local or "." not in domain:
                    continue
                if email.endswith(("@example.com", "@test.com", "@sentry.io")):
                    continue
                if domain.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
                    continue
                found.add(email)
        except (httpx.HTTPError, Exception) as e:
            log.debug("email discovery failed for %s: %s", url, e)
            continue
        time.sleep(0.3)

    primary = sorted(e for e in found if e.startswith(_EMAIL_PRIORITY))
    rest = sorted(e for e in found if not e.startswith(_EMAIL_PRIORITY))
    return (primary + rest)[:5]


def _enrich_one(client: httpx.Client, job: Job, *, force: bool) -> bool:
    needs_founders = force or not (job.founders or [])
    needs_emails = force or not (job.contact_emails or [])
    if not needs_founders and not needs_emails:
        return False
    if needs_founders and job.company_slug:
        company_url = f"{YC_BASE}/companies/{job.company_slug}"
        html = _fetch(client, company_url)
        time.sleep(REQUEST_DELAY_SECONDS)
        if html:
            job.founders = _parse_company_founders(html)
    if needs_emails:
        job.contact_emails = _discover_emails(client, job.company_website)
    return True


def enrich_jobs_batch(
    session: Session, jobs: list[Job], *, force: bool = False
) -> dict[int, dict[str, Any]]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Connection": "keep-alive",
    }
    results: dict[int, dict[str, Any]] = {}
    if not jobs:
        return results
    with httpx.Client(
        headers=headers,
        follow_redirects=True,
        limits=HTTP_LIMITS,
    ) as client:
        for job in jobs:
            try:
                changed = _enrich_one(client, job, force=force)
            except Exception as e:
                log.warning("enrich failed for job %s: %s", job.id, e)
                continue
            if changed:
                session.add(job)
                results[job.id] = {
                    "founders": job.founders or [],
                    "contact_emails": job.contact_emails or [],
                }
        session.commit()
    return results


def enrich_company_for_job(
    session: Session, job: Job, *, force: bool = False
) -> Job:
    needs_founders = force or not (job.founders or [])
    needs_emails = force or not (job.contact_emails or [])
    if not needs_founders and not needs_emails:
        return job

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Connection": "keep-alive",
    }
    with httpx.Client(
        headers=headers,
        follow_redirects=True,
        limits=HTTP_LIMITS,
    ) as client:
        if needs_founders and job.company_slug:
            company_url = f"{YC_BASE}/companies/{job.company_slug}"
            html = _fetch(client, company_url)
            time.sleep(REQUEST_DELAY_SECONDS)
            if html:
                job.founders = _parse_company_founders(html)
        if needs_emails:
            job.contact_emails = _discover_emails(client, job.company_website)

    session.add(job)
    session.commit()
    session.refresh(job)
    return job


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
        founders=company.get("_founders") or [],
        contact_emails=company.get("_contact_emails") or [],
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
    region: str | None = None,
    search_terms: list[str] | None = None,
    match_profile: MatchProfile | None = None,
) -> ScrapeStats:
    stats = ScrapeStats()
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Connection": "keep-alive",
    }

    with httpx.Client(
        headers=headers,
        follow_redirects=True,
        limits=HTTP_LIMITS,
        http2=False,
    ) as client:
        try:
            if search_terms:
                hits_per_query = max(10, min(25, company_limit // len(search_terms) + 5))
                companies = _algolia_search_multi(
                    client,
                    search_terms=search_terms,
                    hits_per_query=hits_per_query,
                    region=region,
                )[:company_limit]
                log.info(
                    "targeted scrape: %d terms -> %d unique companies",
                    len(search_terms), len(companies),
                )
            else:
                companies = _algolia_search_hiring(
                    client, hits_per_page=company_limit, region=region
                )
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

            company_founders = _parse_company_founders(html)
            company_emails = _discover_emails(client, company.get("website"))
            company["_founders"] = company_founders
            company["_contact_emails"] = company_emails

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
                    if match_profile:
                        temp = Job(
                            title=parsed["title"] or "Untitled role",
                            description=parsed["description"],
                        )
                        sc, bd = score_job(temp, match_profile)
                        if not passes_threshold(sc, bd):
                            stats.jobs_skipped += 1
                            continue
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
