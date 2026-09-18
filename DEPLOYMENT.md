# Deployment runbook

The public app uses Netlify (or Vercel) for the static frontend, Render for the FastAPI backend, and a persistent PostgreSQL database such as Neon. Render's free filesystem is temporary, so do not use SQLite there.

1. Create an empty PostgreSQL database. Copy its connection string into Render's `DATABASE_URL` secret.
2. In Render, create a Blueprint from the GitHub `master` branch using `render.yaml`. Set `DATABASE_URL`, `OPENROUTER_API_KEY`, and `FRONTEND_URL` as secrets. The app creates tables on startup.
3. In Netlify, import the same repo. `netlify.toml` builds `frontend/`. Set `VITE_BACKEND_URL` to the Render API origin and deploy. If using Vercel, set Root Directory to `frontend`, use the Vite preset, and set the same variable.
4. Set Render's `FRONTEND_URL` to the exact Netlify or Vercel site origin, with no trailing slash, and redeploy the API. The FastAPI CORS middleware permits that origin.
5. Verify `<API URL>/health`. Open the site in two different browsers and confirm résumé data stays separate. Test uploading a PDF, skipping preferences, saving refinements, and viewing ranked cards.

Keep the OpenRouter key and database URL only in service environment variables. Never put either in a `VITE_*` variable or commit it. Render's free API sleeps after inactivity and free tiers have usage limits, so monitor the services before broad promotion.
