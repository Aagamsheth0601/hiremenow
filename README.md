# hiremenow

Upload a PDF résumé, review the extracted profile, and discover startup jobs ranked by role and skill fit. A visitor can optionally refine target roles, location, and work mode. The app also drafts an email (at most 1,000 characters) or LinkedIn message (at most 300 characters) for review and copying. It never sends messages automatically.

## Highlights

- No account is required. Each browser gets a random anonymous token. Only its SHA-256 hash is stored in the database.
- Résumés, preferences, saved jobs, and drafts are scoped to that browser token. A different browser starts with an empty private profile.
- The same browser can return within seven days of activity. Expired sessions and their private data are deleted during session cleanup.
- PDF only, maximum 10 MB. The server checks the file signature and does not expose uploaded PDFs through a public URL.
- Match scores use résumé and job text, with visible matching and missing skills. AI helps extract the résumé and draft outreach, but a match score is a guide, not an employer assessment.
- Scraping uses public job pages. Founder links and email addresses are best effort and must be reviewed before use.

## How it works

1. Upload a résumé PDF. The API extracts text and asks OpenRouter to build a structured profile.
2. Review the suggested match focus or skip straight to Discover Jobs.
3. Explore public startup openings ranked by role and skill overlap. Strong, medium, and low fit cards show the evidence behind each score.
4. Refine matches by role, location, or work mode. Save promising jobs and track outreach status in the same browser.
5. Generate an email or LinkedIn draft, review it, and open the destination yourself. The app never sends a message for you.

## Stack

React, TypeScript, Vite, Tailwind CSS, FastAPI, SQLModel, PostgreSQL/SQLite, and OpenRouter.

## Run locally in VS Code Git Bash

Open two terminals from the repo root. Add your OpenRouter key to a gitignored `backend/.env`; copy [`backend/.env.example`](backend/.env.example) as a starting point. The locked Vite 6 toolchain supports this machine's Node 20.11.1.

Backend:

```bash
cd backend
./.venv/Scripts/python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

If the virtual environment does not exist, create it with Python 3.10 and install the backend project first:

```bash
cd backend
py -3.10 -m venv .venv
./.venv/Scripts/python.exe -m pip install -e .
```

Frontend:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. The API health check is `http://127.0.0.1:8000/health`.
