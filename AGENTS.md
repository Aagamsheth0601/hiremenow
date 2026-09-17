# hiremenow project notes

## Bug log / gotchas

| Symptom | Root cause | Fix / status |
| --- | --- | --- |
| Backend tests could not start: the `.venv` launcher tried to use a missing Python 3.10 executable. | The local Python installation referenced by the virtual environment is gone. | Recreate `.venv` from a working Python installation before backend tests; pending. |
| Frontend production build failed on `subject`, `body`, and `message` accesses in JobsPage. | TypeScript could not preserve the draft type narrowing inside click callbacks. | Narrow email and LinkedIn drafts into separate variables before rendering their controls. |
| Node failed with `EPERM` while resolving the Codex workspace path in the sandbox. | The sandbox blocked a parent path lookup. | Run build and lint with normal filesystem access; both now pass. |
| Local Git clone failed looking for `git-upload-pack`. | The local Git installation could not invoke that helper for the source checkout. | Copied the checkout into the Codex workspace without local environment, database, or uploaded documents. |
