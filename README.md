# hiremenow

Personal job-hunt automation. Given a resume, hiremenow:

1. Scrapes startup job openings (YC first, LinkedIn later) and matches them against the resume.
2. Resolves founder / hiring-manager contacts (LinkedIn URL + email) for matched companies.
3. Drafts personalized outreach emails (and, in a later phase, LinkedIn messages).
4. Sends emails directly from the app.

## Stack

- **Frontend:** Next.js (React, TypeScript) — `frontend/`
- **Backend:** Python (FastAPI) — `backend/`
- **Layout:** monorepo

## Status

Scaffolding. Feature planning in progress.

## Scraping policy

- Prefer official / first-party sources (YC's Work at a Startup, YC company directory, public profile pages).
- No authenticated LinkedIn scraping.
- Aggressive rate-limiting and respectful crawling.
- Contact enrichment via legitimate APIs (e.g. Hunter.io, Apollo) where possible, not bulk scraping.
