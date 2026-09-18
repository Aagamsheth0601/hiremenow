# hiremenow

Upload a PDF résumé, review the extracted profile, and discover startup jobs ranked by role and skill fit. A visitor can optionally refine target roles, location, and work mode. The app also drafts an email (at most 1,000 characters) or LinkedIn message (at most 300 characters) for review and copying. It never sends messages automatically.

## Privacy and matching

- No account is required. Each browser gets a random anonymous token. Only its SHA-256 hash is stored in the database.
- Résumés, preferences, saved jobs, and drafts are scoped to that browser token. A different browser starts with an empty private profile.
- The same browser can return within seven days of activity. Expired sessions and their private data are deleted during session cleanup.
- PDF only, maximum 10 MB. The server checks the file signature and does not expose uploaded PDFs through a public URL.
- Match scores use résumé and job text, with visible matching and missing skills. AI helps extract the résumé and draft outreach, but a match score is a guide, not an employer assessment.
- Scraping uses public job pages. Founder links and email addresses are best effort and must be reviewed before use.

## Run locally in VS Code Git Bash

Open two terminals from the repo root. Add your OpenRouter key to a gitignored `backend/.env`; copy [`backend/.env.example`](backend/.env.example) as a starting point. Use the Vite 5 toolchain in `frontend/package-lock.json` with Node 20.11.1.

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

## Free deployment

The repo includes [`netlify.toml`](netlify.toml) for a Netlify static frontend, [`frontend/vercel.json`](frontend/vercel.json) for Vercel if preferred, and [`render.yaml`](render.yaml) for a one-worker FastAPI service on Render. The API requires a persistent PostgreSQL database, for example a Neon free database. **Do not use SQLite on a free Render service:** its filesystem is erased on sleep and redeploy.

1. Create an empty PostgreSQL database in Neon. Copy its connection string into Render's secret `DATABASE_URL`. The application creates its tables on startup.
2. In Render, create a Blueprint from this GitHub repo and its `master` branch. Choose the free plan. Render will prompt for `DATABASE_URL`, `OPENROUTER_API_KEY`, and `FRONTEND_URL`.
3. In Netlify, import the same repo and its `master` branch. The root [`netlify.toml`](netlify.toml) builds only `frontend/`. Set `VITE_BACKEND_URL` to the public Render API origin, such as `https://hiremenow-api.onrender.com`, before deploying. If you choose Vercel instead, set its Root Directory to `frontend`, use the Vite preset, and set the same `VITE_BACKEND_URL` build environment variable.
4. Set Render's `FRONTEND_URL` to the exact public frontend origin Netlify or Vercel assigns, such as `https://hiremenow.netlify.app`. Do not add a trailing slash. Redeploy the backend after setting or changing this value. FastAPI's `CORSMiddleware` allows this origin; browser preflight requests from other origins are rejected.
5. After deploy, open `<API URL>/health`, then open the site in two different browsers. Confirm that uploading a test PDF in one browser does not expose it in the other. Confirm the skip path and a saved refinement.

Render's free API sleeps after inactivity, so the first visit may be slow. Free database and API quotas are limited; this setup is suitable for an initial public beta, with usage monitoring before broad promotion. Keep all keys in service environment variables, never in `VITE_*` values or GitHub.
