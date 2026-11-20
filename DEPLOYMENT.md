# Deployment runbook

The public app uses Netlify (or Vercel) for the static frontend, Render for the FastAPI backend, and a persistent PostgreSQL database such as Neon. Render's free filesystem is temporary, so do not use SQLite there.

1. Create an empty PostgreSQL database. Copy its connection string into Render's `DATABASE_URL` secret.
2. In Render, create a Blueprint from the GitHub `master` branch using `render.yaml`. Set `DATABASE_URL`, `GEMINI_API_KEY`, and `FRONTEND_URL` as secrets. The app creates tables on startup.
3. In Netlify, import the same repo. `netlify.toml` builds `frontend/`. Set `VITE_BACKEND_URL` to the Render API origin and deploy. If using Vercel, set Root Directory to `frontend`, use the Vite preset, and set the same variable.
4. Set Render's `FRONTEND_URL` to the exact Netlify or Vercel site origin, with no trailing slash, and redeploy the API. The FastAPI CORS middleware permits that origin.
5. Verify `<API URL>/health`. Open the site in two different browsers and confirm résumé data stays separate. Test uploading a PDF, skipping preferences, saving refinements, and viewing ranked cards.

Keep the Gemini key and database URL only in service environment variables. Never put either in a `VITE_*` variable or commit it. Render's free API sleeps after inactivity and free tiers have usage limits, so monitor the services before broad promotion.

## Scheduled YC collection

`.github/workflows/collect-jobs.yml` runs daily at 01:23 UTC, independently of web traffic. GitHub may delay scheduled starts. Configure `COLLECTOR_DATABASE_URL` as an Actions secret pointing at the same PostgreSQL database as Render. Do not commit it. The workflow requires only database access, not a Gemini key, and can also be dispatched manually.

The collector stores per-region attempts and successful/partial/failed outcomes in `collection_runs`; this additive table is created at startup. A running attempt older than two hours is reported as interrupted. Public visitors cannot trigger scraping. Matching remains per visitor; source collection is shared and YC-only. Each run checks a rotating subset of known companies and discovers a few more from public YC landing pages. A listing is hidden from active results after two complete checks of its company snapshot at least 20 hours apart show it missing. Saved jobs and application history remain available. Failed checks and HTTP 429 do not advance freshness.

Verify a successful Actions run for both India and US and `/jobs/freshness?region=india` with a visitor token. A failed workflow must be investigated; a healthy `/health` response alone does not verify collection.
