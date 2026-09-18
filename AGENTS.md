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
