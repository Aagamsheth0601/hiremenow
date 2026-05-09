from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from backend.db import get_session
from backend.models import JobPreferences, Resume

router = APIRouter(prefix="/preferences", tags=["preferences"])

SENIORITY_OPTIONS = ["intern", "junior", "mid", "senior", "staff+"]
WORK_MODE_OPTIONS = ["remote", "hybrid", "on-site"]
COMPANY_SIZE_OPTIONS = ["startup", "mid-size", "large-mnc"]


class PreferencesPayload(BaseModel):
    target_roles: list[str] = Field(default_factory=list)
    seniority: str | None = None
    locations: list[str] = Field(default_factory=list)
    work_modes: list[str] = Field(default_factory=list)
    company_sizes: list[str] = Field(default_factory=list)
    needs_visa_sponsorship: bool = False


class PreferencesResponse(PreferencesPayload):
    has_saved: bool
    updated_at: str | None = None


def _seniority_from_years(years: float | None) -> str | None:
    if years is None:
        return None
    if years < 1:
        return "intern"
    if years < 2:
        return "junior"
    if years < 5:
        return "mid"
    if years < 10:
        return "senior"
    return "staff+"


def _prefill_from_resume(session: Session) -> PreferencesPayload:
    resume = session.exec(select(Resume).order_by(Resume.uploaded_at.desc())).first()
    if resume is None or not resume.parsed:
        return PreferencesPayload()

    parsed = resume.parsed
    contact = parsed.get("contact") or {}
    experience = parsed.get("experience") or []

    titles: list[str] = []
    for exp in experience:
        title = (exp or {}).get("title")
        if title and title not in titles:
            titles.append(title)
    titles = titles[:5]

    location = (contact.get("location") or "").strip()
    locations = [location] if location else []

    return PreferencesPayload(
        target_roles=titles,
        seniority=_seniority_from_years(parsed.get("years_experience")),
        locations=locations,
        work_modes=[],
        company_sizes=[],
        needs_visa_sponsorship=False,
    )


def _to_response(prefs: JobPreferences | None, fallback: PreferencesPayload) -> PreferencesResponse:
    if prefs is None:
        return PreferencesResponse(**fallback.model_dump(), has_saved=False, updated_at=None)
    return PreferencesResponse(
        target_roles=prefs.target_roles,
        seniority=prefs.seniority,
        locations=prefs.locations,
        work_modes=prefs.work_modes,
        company_sizes=prefs.company_sizes,
        needs_visa_sponsorship=prefs.needs_visa_sponsorship,
        has_saved=True,
        updated_at=prefs.updated_at.isoformat(),
    )


@router.get("")
def get_preferences(session: Session = Depends(get_session)) -> PreferencesResponse:
    prefs = session.exec(select(JobPreferences)).first()
    if prefs is not None:
        return _to_response(prefs, PreferencesPayload())
    return _to_response(None, _prefill_from_resume(session))


@router.put("")
def upsert_preferences(
    payload: PreferencesPayload,
    session: Session = Depends(get_session),
) -> PreferencesResponse:
    has_resume = session.exec(select(Resume.id)).first() is not None
    if not has_resume:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload a resume before saving preferences.",
        )

    prefs = session.exec(select(JobPreferences)).first()
    if prefs is None:
        prefs = JobPreferences()

    prefs.target_roles = payload.target_roles
    prefs.seniority = payload.seniority
    prefs.locations = payload.locations
    prefs.work_modes = payload.work_modes
    prefs.company_sizes = payload.company_sizes
    prefs.needs_visa_sponsorship = payload.needs_visa_sponsorship
    prefs.updated_at = datetime.now(timezone.utc)

    session.add(prefs)
    session.commit()
    session.refresh(prefs)

    return _to_response(prefs, PreferencesPayload())


@router.get("/options")
def get_options() -> dict[str, list[str]]:
    return {
        "seniority": SENIORITY_OPTIONS,
        "work_mode": WORK_MODE_OPTIONS,
        "company_size": COMPANY_SIZE_OPTIONS,
    }
