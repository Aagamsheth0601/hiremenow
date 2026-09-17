from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Column, LargeBinary
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Resume(SQLModel, table=True):
    __tablename__ = "resumes"

    id: int | None = Field(default=None, primary_key=True)
    owner_hash: str = Field(index=True)
    filename: str
    raw_text: str
    parsed: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    pdf_bytes: bytes | None = Field(default=None, sa_column=Column(LargeBinary))
    uploaded_at: datetime = Field(default_factory=_utcnow)
