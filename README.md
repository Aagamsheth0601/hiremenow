# hiremenow

Personal job-hunt automation. Given a resume, hiremenow:

1. Scrapes startup job openings (YC first, LinkedIn later) and matches them against the resume.
2. Resolves founder / hiring-manager contacts (LinkedIn URL + email) for matched companies.
3. Drafts personalized outreach emails (and, in a later phase, LinkedIn messages).
4. Sends emails directly from the app — every send is gated behind an explicit user click.

## Layout

```
hiremenow/
├── frontend/   # Next.js 15 (App Router, TypeScript, Tailwind, shadcn/ui)
├── backend/    # Python 3.10+ (FastAPI, SQLModel, uv)
├── .env.example
└── .gitignore
```

## Hard rules

- **Public-data-only scraping.** No authenticated/logged-in scraping. Respect every source's policy.
- **No automatic sending.** Every email goes through a human review queue and waits for an explicit Send click.
- **OAuth-only auth.** No password flows. Google OAuth for Gmail send permission.

## Running locally

Copy `.env.example` to `.env` and fill in keys.

### Backend

```bash
cd backend
python -m uv sync          # one-time: install deps
python -m uv run backend   # start FastAPI on http://127.0.0.1:8000
```

Health check: `GET http://127.0.0.1:8000/health` → `{"status": "ok"}`
API docs: `http://127.0.0.1:8000/docs`

### Frontend

```bash
cd frontend
npm install                # one-time
npm run dev                # Next.js on http://localhost:3000
```

## Status

Scaffolding complete. Feature 1 (resume ingestion) up next.
