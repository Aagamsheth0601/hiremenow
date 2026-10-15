# hiremenow project notes

## Bug log / gotchas

| Symptom | Root cause | Fix / status |
| --- | --- | --- |
| Backend tests could not start: the `.venv` launcher tried to use a missing Python 3.10 executable. | The local Python installation referenced by the virtual environment was gone. | Rebuilt `.venv` with Python 3.10.21 and verified the health endpoint. |
| Frontend production build failed on `subject`, `body`, and `message` accesses in JobsPage. | TypeScript could not preserve the draft type narrowing inside click callbacks. | Narrow email and LinkedIn drafts into separate variables before rendering their controls. |
| Node failed with `EPERM` while resolving the Codex workspace path in the sandbox. | The sandbox blocked a parent path lookup. | Run build and lint with normal filesystem access; both now pass. |
| Local Git clone failed looking for `git-upload-pack`. | The local Git installation could not invoke that helper for the source checkout. | Copied the checkout into the Codex workspace without local environment, database, or uploaded documents. |
| A second visitor could read the latest resume, preferences, drafts, and job state. | These endpoints selected global rows without a visitor identity. | Added anonymous browser sessions, stored only token hashes, and scoped private queries and mutations to the session. Start the new version with a fresh database. |
| An isolation test crashed after its database session closed. | SQLAlchemy expires ORM objects after commit and cannot refresh a detached job. | Captured the numeric job ID while the session was open. |
| A malformed-token test failed in the HTTP client before reaching the API. | HTTP header values must be ASCII. | Used an invalid ASCII token to exercise API validation. |
| The old SQLite file could not be removed. | The local uvicorn process still held the database open. | Stopped the verified HireMeNow process, removed the old database, and checked that the fresh database starts empty. |
| A checkout smoke test said `visitor_sessions` did not exist. | The test client was created without entering the app lifespan, so startup did not create tables. | Entered the test client lifespan and reran the health, session, and empty-data checks. |
| Outreach drafts included one developer's past employer and achievements for every visitor. | The LinkedIn prompt and fallback were hardcoded for the original résumé. | Replaced them with resume-based text and enforced 300/1,000-character limits with tests. |
| A filtered list with zero matches said there were no jobs in the database. | The empty state ignored active refinements and status filters. | Show a context-specific message and a direct way to refine matches. |
| The preview browser sometimes closed during screenshot checks. | The Playwright browser context or local preview server ended between calls. | Restarted the isolated preview and verified the UI at 390, 768, and 1280 pixels. |
| Replacing a resume could leave old priorities, outreach drafts, and saved job states attached to the new profile. | Uploading a new PDF only inserted another resume row. | After a successful parse, replace the browser's private profile and verify the reset in a request-level test. |
| Skipping priorities could keep an earlier saved refinement. | Skip only navigated to Discover Jobs. | Delete saved priorities before navigating; the API then falls back to resume-derived suggestions. |
| The first sync of verified files stopped before copying. | The path safety check rejected files directly under the repository root. | Allowed the verified root directory itself and reran the named-file copy successfully. |
| Discover Jobs reported zero companies and no error after a successful resume upload. | YC's old hardcoded Algolia search credential returned HTTP 403, and the scraper swallowed targeted query failures. | Read YC's public job pages instead; recognize IN/US region codes and show source errors in the UI. |
| Resume analysis felt too slow for an interactive upload flow. | Parsing and outreach depended on a slower routed free model. | Call Gemini Flash-Lite directly through Google's OpenAI-compatible endpoint with bounded timeouts and retries. |

### Scheduled collection and misleading freshness
- Symptom: refresh updated jobs but the page still said last scraped weeks ago, and job cards called the same date a posting date.
- Root cause: scraped_at was an immutable first-seen timestamp; the UI ignored updated_at. Collection was driven by visitors and filtered shared storage by their profiles.
- Fix: expose last_checked_at, label first-seen dates honestly, persist region-level collection runs, and collect an unpersonalized catalogue on a 12-hour GitHub Actions schedule. Failed/partial runs preserve last successful refresh. The source is explicitly YC only.
- Regression coverage also found listing refreshes overwrote enriched contacts with empty values; preserve existing enrichment when a refresh has no replacement.
- The workflow needs COLLECTOR_DATABASE_URL in GitHub Actions secrets. It refuses to fall back to local SQLite if that secret is absent.

### Verification — automated catalogue and discovery workspace
- Production workflow 38650634432 completed successfully: India 7 companies / 15 listings saved; US 33 companies / 33 listings saved; zero errors. Live API freshness confirmed both regions completed and not stale.
- Backend regression suite: 12 passed. Frontend TypeScript/Vite production build passed.
- List selection and overflow checked with synthetic browser fixtures at 390, 768, and 1280px. No Refresh jobs button; selected role changes in the detail panel. Existing outreach actions were retained, not live-sent or regenerated during this UI check.

### Optional profile preferences
- Symptom: resume home location was prefilled as a desired work location, and profile setup looked mandatory.
- Fix: leave unsaved location/work-mode preferences empty; show role chips, detected skills, collapsed optional filters, and a bold Skip preferences action. Return visitors can go directly to matches. Visitors without a resume redirect from /jobs to upload.
- Verified TypeScript/Vite build, existing 12 backend tests plus a home-location regression, and browser save/skip/redirect at 390/768/1280 using synthetic API fixtures. Skip sends DELETE; role selection and additions save without implicit location filters.

### Country refinements and region selection
- Symptom: USA/US preferences opened India jobs or kept the old region after saving.
- Root cause: resume home address overrode saved search location; frontend did not update region after refinement; backend used literal substring matching for country aliases.
- Fix: saved location takes precedence, saving updates the region, normalize US/USA/U.S./United States and India/IN aliases, and ignore stale job/count responses. Country filters also respect restrictions on remote listings. Use one select-only country list for profile and discovery; changing the discovery country persists the preference, preventing conflicting filters. Coverage is explicitly India and United States.
- Verified backend regressions, production frontend build, and synthetic browser save/reload/change/clear flows at 390/768/1280px with no horizontal overflow.

### Consistent profile and discovery design
- Replaced the mixed green styling with shared navy/blue panels, clearer typography, a match-evidence illustration labeled Example, and a three-step profile flow. Preserved optional preferences and bold skip.
- Verified both pages at 390/768/1280px, country persistence between both pages, frontend build and 46 backend tests. Broader country collection remains outside current India/US coverage.
- Added 150–280ms panel entrances, hover and press feedback; verified reduced-motion disables animation and no overflow at 390/768/1280px.
