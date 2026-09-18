"""Small per-process guard for the API's expensive public actions.

The deployment uses one backend worker. A shared gateway limit is still needed
if the service is later scaled to multiple workers or machines.
"""

import hashlib
import threading
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse

_calls: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def _policy(path: str, method: str) -> tuple[str, int, int] | None:
    if method != "POST":
        return None
    if path == "/sessions":
        return "sessions", 100, 3600
    if path == "/resumes":
        return "resumes", 5, 3600
    if path == "/jobs/scrape":
        return "scrape", 3, 3600
    if path == "/jobs/enrich-batch" or path.endswith("/enrich"):
        return "enrich", 20, 3600
    if path.endswith("/draft"):
        return "draft", 20, 3600
    return None


async def guard_expensive_actions(request: Request, call_next):
    policy = _policy(request.url.path, request.method)
    if policy is None:
        return await call_next(request)
    action, limit, window = policy
    identity = (request.headers.get("authorization") or "").strip()
    if not identity:
        identity = request.client.host if request.client else "unknown"
    key = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    now = time.monotonic()
    with _lock:
        calls = _calls[(action, key)]
        while calls and calls[0] < now - window:
            calls.popleft()
        if len(calls) >= limit:
            retry_after = max(1, int(window - (now - calls[0])))
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": str(retry_after)},
            )
        calls.append(now)
    return await call_next(request)
