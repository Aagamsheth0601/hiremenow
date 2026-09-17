from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from backend.db import get_session
from backend.models import JobPreferences, Resume
from backend.services.resume_parser import (
    ParsedResume,
    ResumeParseError,
    suggest_target_roles,
)
from backend.visitor import get_visitor_hash

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


def _prefill_from_resume(session: Session, owner_hash: str) -> PreferencesPayload:
    resume = session.exec(
        select(Resume).where(Resume.owner_hash == owner_hash).order_by(Resume.uploaded_at.desc())
    ).first()
    if resume is None or not resume.parsed:
        return PreferencesPayload()

    parsed = resume.parsed
    contact = parsed.get("contact") or {}
    experience = parsed.get("experience") or []

    suggested = parsed.get("suggested_target_roles") or []
    target_roles: list[str] = []
    for role in suggested:
        if isinstance(role, str) and role.strip() and role not in target_roles:
            target_roles.append(role.strip())

    if not target_roles:
        for exp in experience:
            title = (exp or {}).get("title")
            if title and title not in target_roles:
                target_roles.append(title)
    target_roles = target_roles[:7]

    location = (contact.get("location") or "").strip()
    locations = [location] if location else []

    return PreferencesPayload(
        target_roles=target_roles,
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
def get_preferences(
    session: Session = Depends(get_session), owner_hash: str = Depends(get_visitor_hash)
) -> PreferencesResponse:
    prefs = session.exec(select(JobPreferences).where(JobPreferences.owner_hash == owner_hash)).first()
    if prefs is not None:
        return _to_response(prefs, PreferencesPayload())
    return _to_response(None, _prefill_from_resume(session, owner_hash))


@router.put("")
def upsert_preferences(
    payload: PreferencesPayload,
    session: Session = Depends(get_session),
    owner_hash: str = Depends(get_visitor_hash),
) -> PreferencesResponse:
    has_resume = session.exec(select(Resume.id).where(Resume.owner_hash == owner_hash)).first() is not None
    if not has_resume:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload a resume before saving preferences.",
        )

    prefs = session.exec(select(JobPreferences).where(JobPreferences.owner_hash == owner_hash)).first()
    if prefs is None:
        prefs = JobPreferences(owner_hash=owner_hash)

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


@router.post("/suggest-roles")
def suggest_roles(
    session: Session = Depends(get_session), owner_hash: str = Depends(get_visitor_hash)
) -> dict[str, list[str]]:
    resume = session.exec(
        select(Resume).where(Resume.owner_hash == owner_hash).order_by(Resume.uploaded_at.desc())
    ).first()
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload a resume first.",
        )
    try:
        parsed = ParsedResume.model_validate(resume.parsed or {})
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stored resume is malformed: {e}",
        ) from e

    try:
        roles = suggest_target_roles(parsed)
    except ResumeParseError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        ) from e

    return {"target_roles": roles}


@router.get("/options")
def get_options() -> dict[str, list[str]]:
    return {
        "seniority": SENIORITY_OPTIONS,
        "work_mode": WORK_MODE_OPTIONS,
        "company_size": COMPANY_SIZE_OPTIONS,
    }
