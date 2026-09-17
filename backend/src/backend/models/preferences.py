from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JobPreferences(SQLModel, table=True):
    __tablename__ = "job_preferences"

    id: int | None = Field(default=None, primary_key=True)
    owner_hash: str = Field(index=True, unique=True)
    target_roles: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    seniority: str | None = None
    locations: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    work_modes: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    company_sizes: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    needs_visa_sponsorship: bool = False
    extras: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    updated_at: datetime = Field(default_factory=_utcnow)
