from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: int | None = Field(default=None, primary_key=True)
    source: str = Field(default="yc", index=True)
    source_url: str = Field(unique=True, index=True)
    yc_job_id: str | None = Field(default=None, index=True)

    title: str
    description: str = ""

    company_name: str = Field(index=True)
    company_slug: str = Field(index=True)
    company_one_liner: str | None = None
    company_logo_url: str | None = None
    company_website: str | None = None
    company_team_size: int | None = None
    company_industry: str | None = None
    company_stage: str | None = None
    company_batch: str | None = None

    locations: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    founders: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    contact_emails: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    application_status: str | None = Field(default=None, index=True)
    status_updated_at: datetime | None = Field(default=None)
    is_starred: bool = Field(default=False, index=True)

    scraped_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
