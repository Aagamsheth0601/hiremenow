"""Persistent source refresh history, independent of any visitor profile."""
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel

class CollectionRun(SQLModel, table=True):
    __tablename__ = "collection_runs"
    id: int | None = Field(default=None, primary_key=True)
    region: str = Field(index=True)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    status: str = "running"
    companies: int = 0
    jobs_seen: int = 0
    jobs_saved: int = 0
    errors: int = 0
