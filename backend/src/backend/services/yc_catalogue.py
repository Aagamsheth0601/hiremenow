"""Bounded, incremental refresh of public YC company job snapshots."""
import json
import re
import time
from datetime import datetime, timedelta, timezone

import httpx
from bs4 import BeautifulSoup
from sqlmodel import Session, select

from backend.models import Job
from backend.models.collection import CompanyCatalogueCheck, JobCatalogueState
from backend.services.job_regions import matches_region
from backend.services.yc_scraper import (
    REQUEST_DELAY_SECONDS, USER_AGENT, YC_BASE, ScrapeStats, YCRateLimit,
    YCRateLimited, _parse_job_page, _public_job_listings,
)

TRACKED_COMPANIES = 16
NEW_COMPANIES = 4
DETAIL_REQUESTS = 5
MIN_CONFIRMATION_GAP = timedelta(hours=20)


def _job_key(path: str) -> str:
    slug = path.rstrip("/").rsplit("/", 1)[-1]
    # YC's seven-character URL ID survives a change to the title slug.
    match = re.match(r"^([a-zA-Z0-9]{7})-", slug)
    return match.group(1) if match else slug


def _snapshot(client: httpx.Client, slug: str) -> dict:
    response = client.get(f"{YC_BASE}/companies/{slug}/jobs")
    response.raise_for_status()
    node = BeautifulSoup(response.text, "html.parser").select_one("[data-page]")
    if node is None:
        raise ValueError("Missing YC company snapshot")
    page = json.loads(node["data-page"])
    if page.get("component") != "WaasShowJobsPage":
        raise ValueError("Unexpected YC company page")
    props = page["props"]
    postings = props["jobPostings"]
    if not isinstance(postings, list) or not isinstance(props.get("company"), dict):
        raise ValueError("Invalid YC company snapshot")
    result = {}
    for posting in postings:
        path = posting["url"]
        title = posting["title"]
        location = posting.get("location") or ""
        if (not isinstance(title, str) or not title.strip() or not isinstance(location, str)
                or not re.fullmatch(rf"/companies/{re.escape(slug)}/jobs/[\w-]+/?", path)):
            raise ValueError("Invalid YC posting")
        key = _job_key(path)
        if key in result:
            raise ValueError("Duplicate YC posting ID")
        result[key] = posting
    return result


class IncrementalCatalogue:
    def __init__(self, now: datetime | None = None, transport=None):
        self.now = now or datetime.now(timezone.utc)
        self.rate_limit = YCRateLimit()
        self.snapshots = {}
        self.reconciled = set()
        self.transport = transport

    def collect(self, session: Session, *, region: str, **_limits) -> ScrapeStats:
        stats = ScrapeStats()
        if self.rate_limit.blocked:
            print(f"{region}: skipped after the source rate limit")
            stats.errors = 1
            return stats

        existing = session.exec(select(Job).where(Job.source == "yc")).all()
        by_company = {}
        tracked = set()
        for job in existing:
            by_company.setdefault(job.company_slug, []).append(job)
            if (re.fullmatch(r"[a-zA-Z0-9-]+", job.company_slug)
                    and matches_region(job.locations, region, title=job.title)):
                tracked.add(job.company_slug)
        checks = {row.slug: row for row in session.exec(select(CompanyCatalogueCheck))}
        oldest = datetime.min
        def check_order(slug):
            return (checks[slug].checked_at.replace(tzinfo=None) if slug in checks else oldest, slug)

        selected = sorted(tracked, key=check_order)[:TRACKED_COMPANIES]

        # Pace every request, including discovery and job details, on the shared
        # run. Disable redirects so a changed source cannot multiply requests.
        def pace(_request):
            time.sleep(REQUEST_DELAY_SECONDS)

        with httpx.Client(
            headers={"User-Agent": USER_AGENT}, timeout=12,
            event_hooks={"request": [pace], "response": [self.rate_limit.check_response]},
            transport=self.transport,
        ) as client:
            try:
                landing = _public_job_listings(client, region=region, search_terms=None,
                                               company_limit=TRACKED_COMPANIES + NEW_COMPANIES)
                discovered = [
                    item["slug"] for item in landing
                    if item["slug"] not in tracked and re.fullmatch(r"[a-zA-Z0-9-]+", item["slug"])
                ]
                selected.extend(sorted(set(discovered), key=check_order)[:NEW_COMPANIES])
                return self._apply(session, region, selected, by_company, checks, client, stats)
            except YCRateLimited:
                stats.errors += 1
            except (httpx.HTTPError, RuntimeError, ValueError, KeyError, TypeError, AttributeError) as exc:
                print(f"{region}: YC refresh interrupted ({type(exc).__name__})")
                stats.errors += 1
        return stats

    def _apply(self, session, region, selected, by_company, checks, client, stats):
        pending = []
        present_ids = {}
        for slug in selected:
            try:
                if slug not in self.snapshots:
                    self.snapshots[slug] = _snapshot(client, slug)
            except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as exc:
                print(f"{region}: could not verify company {slug} ({type(exc).__name__})")
                stats.errors += 1
                self._record_attempt(session, checks, slug)
                session.commit()
                continue
            postings = self.snapshots[slug]
            stats.companies_visited += 1
            known = {}
            present_ids[slug] = set()
            for job in sorted(by_company.get(slug, []), key=lambda item: item.id):
                known.setdefault(_job_key(job.source_url), []).append(job)
            for key, posting in postings.items():
                source_url = f"{YC_BASE}{posting['url']}"
                candidates = known.get(key, [])
                # Legacy rows were keyed by full URL. Prefer its current owner
                # when an older title slug and the new slug already coexist.
                job = next((row for row in candidates if row.source_url == source_url),
                           candidates[0] if candidates else None)
                title = posting["title"]
                location = posting.get("location") or ""
                if job is None and not matches_region([location], region, title=title):
                    continue
                stats.jobs_seen += 1
                if job is None:
                    skills = posting.get("skills") or []
                    job = Job(
                        source_url=source_url, yc_job_id=key,
                        title=title, company_slug=slug,
                        company_name=posting.get("companyName") or slug,
                        company_one_liner=posting.get("companyOneLiner"),
                        description=", ".join(skill for skill in skills if isinstance(skill, str))
                        if isinstance(skills, list) else "",
                        scraped_at=self.now,
                    )
                    session.add(job)
                    session.flush()
                    state = JobCatalogueState(job_id=job.id, needs_details=True)
                    stats.jobs_inserted += 1
                else:
                    state = session.get(JobCatalogueState, job.id)
                    job.title = title
                    job.source_url = source_url
                    job.yc_job_id = key
                    stats.jobs_updated += 1
                job.locations = [location] if location else job.locations
                job.updated_at = self.now
                present_ids[slug].add(job.id)
                if state:
                    state.first_missing_at = None
                    state.closed_at = None
                    session.add(state)
                    if state.needs_details:
                        pending.append((job, state, posting["url"]))
                session.add(job)
            self._record_attempt(session, checks, slug)
            session.commit()

        for job, state, path in sorted(pending, key=lambda item: item[0].id)[:DETAIL_REQUESTS]:
            response = client.get(f"{YC_BASE}{path}")
            if response.status_code in (404, 410):
                continue  # It may have closed between the snapshot and detail request.
            response.raise_for_status()
            description = _parse_job_page(response.text)["description"]
            if description:
                job.description = description
                state.needs_details = False
                session.commit()

        # Apply negative evidence only after the selected sweep completed.
        # An overlapping region or a same-day retry cannot count twice.
        if stats.errors:
            return stats
        for slug in set(selected) - self.reconciled:
            for job in by_company.get(slug, []):
                if job.id in present_ids[slug]:
                    continue
                state = session.get(JobCatalogueState, job.id) or JobCatalogueState(job_id=job.id)
                if state.first_missing_at is None:
                    state.first_missing_at = self.now
                elif self.now - state.first_missing_at.replace(tzinfo=timezone.utc) >= MIN_CONFIRMATION_GAP:
                    state.closed_at = state.closed_at or self.now
                session.add(state)
        session.commit()
        self.reconciled.update(selected)
        return stats

    def _record_attempt(self, session, checks, slug):
        check = checks.get(slug) or CompanyCatalogueCheck(slug=slug, checked_at=self.now)
        check.checked_at = self.now
        session.add(check)
