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


class CompanyCatalogueCheck(SQLModel, table=True):
    __tablename__ = "company_catalogue_checks"

    slug: str = Field(primary_key=True)
    checked_at: datetime


class JobCatalogueState(SQLModel, table=True):
    __tablename__ = "job_catalogue_states"

    job_id: int = Field(primary_key=True, foreign_key="jobs.id")
    first_missing_at: datetime | None = None
    closed_at: datetime | None = None
    needs_details: bool = False
