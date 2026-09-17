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
