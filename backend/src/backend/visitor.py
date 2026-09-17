"""Anonymous browser identities. Only token hashes are stored on the server."""

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import delete
from sqlmodel import Session
from sqlmodel import select

from backend.db import get_session
from backend.models import Draft, JobPreferences, Resume, VisitorJobState
from backend.models.visitor import VisitorSession

router = APIRouter(prefix="/sessions", tags=["sessions"])
SESSION_IDLE_DAYS = 7
_REFRESH_INTERVAL = timedelta(hours=1)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _remove_visitor(session: Session, visitor: VisitorSession) -> None:
    """Delete all private records when an anonymous session expires."""
    owner = visitor.token_hash
    for model in (Draft, VisitorJobState, JobPreferences, Resume):
        session.exec(delete(model).where(model.owner_hash == owner))
    session.delete(visitor)


def _cleanup_expired(session: Session, now: datetime) -> None:
    cutoff = now - timedelta(days=SESSION_IDLE_DAYS)
    expired = session.exec(
        select(VisitorSession).where(VisitorSession.last_seen_at < cutoff).limit(25)
    ).all()
    for visitor in expired:
        _remove_visitor(session, visitor)
    if expired:
        session.commit()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_session(session: Session = Depends(get_session)) -> dict[str, str]:
    _cleanup_expired(session, datetime.now(timezone.utc))
    token = secrets.token_urlsafe(32)
    session.add(VisitorSession(token_hash=_hash_token(token)))
    session.commit()
    return {"token": token}


def get_visitor_hash(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> str:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        raise HTTPException(status_code=401, detail="Start a new browser session.")
    token_hash = _hash_token(token)
    visitor = session.get(VisitorSession, token_hash)
    if visitor is None:
        raise HTTPException(status_code=401, detail="Invalid browser session.")
    now = datetime.now(timezone.utc)
    idle = now - _utc(visitor.last_seen_at)
    if idle > timedelta(days=SESSION_IDLE_DAYS):
        _remove_visitor(session, visitor)
        session.commit()
        raise HTTPException(status_code=401, detail="Browser session expired.")
    if idle > _REFRESH_INTERVAL:
        visitor.last_seen_at = now
        session.add(visitor)
        session.commit()
    return token_hash
