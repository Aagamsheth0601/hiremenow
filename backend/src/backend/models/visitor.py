from datetime import datetime, timezone

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class VisitorSession(SQLModel, table=True):
    __tablename__ = "visitor_sessions"

    token_hash: str = Field(primary_key=True)
    created_at: datetime = Field(default_factory=_utcnow)
    last_seen_at: datetime = Field(default_factory=_utcnow, index=True)


class VisitorJobState(SQLModel, table=True):
    __tablename__ = "visitor_job_states"
    __table_args__ = (UniqueConstraint("owner_hash", "job_id"),)

    id: int | None = Field(default=None, primary_key=True)
    owner_hash: str = Field(index=True)
    job_id: int = Field(foreign_key="jobs.id", index=True)
    application_status: str | None = None
    status_updated_at: datetime | None = None
    is_starred: bool = False
