from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import delete
from sqlmodel import Session, select

from backend.db import get_session
from backend.models import Draft, JobPreferences, Resume, VisitorJobState
from backend.services.resume_parser import ResumeParseError, extract_fields, parse_pdf
from backend.visitor import get_visitor_hash

router = APIRouter(prefix="/resumes", tags=["resumes"])

MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB


def _latest_for_owner(session: Session, owner_hash: str) -> Resume | None:
    return session.exec(
        select(Resume).where(Resume.owner_hash == owner_hash).order_by(Resume.uploaded_at.desc())
    ).first()


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    owner_hash: str = Depends(get_visitor_hash),
) -> dict:
    if file.content_type not in ("application/pdf", "application/x-pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF uploads are accepted.",
        )

    pdf_bytes = await file.read(MAX_PDF_BYTES + 1)
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(pdf_bytes) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF exceeds 10MB limit.")
    if not pdf_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="The file is not a PDF.")

    try:
        raw_text, parsed = parse_pdf(pdf_bytes)
    except ResumeParseError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    # A replacement résumé starts a new match profile for this browser. Do this
    # only after parsing succeeds so a failed upload keeps the previous profile.
    for model in (Draft, VisitorJobState, JobPreferences, Resume):
        session.exec(delete(model).where(model.owner_hash == owner_hash))

    resume = Resume(
        owner_hash=owner_hash,
        filename=file.filename or "resume.pdf",
        raw_text=raw_text,
        parsed=parsed.model_dump(),
        pdf_bytes=pdf_bytes,
    )
    session.add(resume)
    session.commit()
    session.refresh(resume)

    return {
        "id": resume.id,
        "filename": resume.filename,
        "uploaded_at": resume.uploaded_at.isoformat(),
        "parsed": resume.parsed,
    }


@router.post("/latest/reparse")
def reparse_latest(
    session: Session = Depends(get_session), owner_hash: str = Depends(get_visitor_hash)
) -> dict:
    resume = _latest_for_owner(session, owner_hash)
    if resume is None:
        raise HTTPException(status_code=404, detail="No resume uploaded.")
    if not resume.raw_text:
        raise HTTPException(status_code=422, detail="No raw text to re-parse.")
    try:
        parsed = extract_fields(resume.raw_text)
    except ResumeParseError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    resume.parsed = parsed.model_dump()
    session.add(resume)
    session.commit()
    session.refresh(resume)
    return {"id": resume.id, "filename": resume.filename, "parsed": resume.parsed}


@router.get("/latest/pdf")
def latest_resume_pdf(
    session: Session = Depends(get_session), owner_hash: str = Depends(get_visitor_hash)
) -> Response:
    resume = _latest_for_owner(session, owner_hash)
    if resume is None:
        raise HTTPException(status_code=404, detail="No resume uploaded.")
    if not resume.pdf_bytes:
        raise HTTPException(
            status_code=410,
            detail="Resume was uploaded before PDF storage was enabled. Re-upload to download.",
        )
    return Response(
        content=resume.pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'inline; filename="resume.pdf"',
        },
    )


@router.get("")
def list_resumes(
    session: Session = Depends(get_session), owner_hash: str = Depends(get_visitor_hash)
) -> list[dict]:
    rows = session.exec(
        select(Resume).where(Resume.owner_hash == owner_hash).order_by(Resume.uploaded_at.desc())
    ).all()
    return [
        {
            "id": r.id,
            "filename": r.filename,
            "uploaded_at": r.uploaded_at.isoformat(),
            "parsed": r.parsed,
        }
        for r in rows
    ]
