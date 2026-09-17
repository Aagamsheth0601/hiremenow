from datetime import datetime, timezone

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Draft(SQLModel, table=True):
    __tablename__ = "drafts"
    __table_args__ = (
        UniqueConstraint("owner_hash", "job_id", "kind", name="uq_drafts_owner_job_kind"),
    )

    id: int | None = Field(default=None, primary_key=True)
    owner_hash: str = Field(index=True)
    job_id: int = Field(foreign_key="jobs.id", index=True)
    kind: str = Field(index=True)

    subject: str | None = None
    body: str | None = None
    message: str | None = None

    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
