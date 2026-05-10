from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlmodel import Session, select

from backend.db import get_session
from backend.models import Resume
from backend.services.resume_parser import ResumeParseError, parse_pdf

router = APIRouter(prefix="/resumes", tags=["resumes"])

MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> dict:
    if file.content_type not in ("application/pdf", "application/x-pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF uploads are accepted.",
        )

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(pdf_bytes) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF exceeds 10MB limit.")

    try:
        raw_text, parsed = parse_pdf(pdf_bytes)
    except ResumeParseError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    resume = Resume(
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


@router.get("/latest/pdf")
def latest_resume_pdf(session: Session = Depends(get_session)) -> Response:
    resume = session.exec(
        select(Resume).order_by(Resume.uploaded_at.desc())
    ).first()
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
            "Content-Disposition": f'inline; filename="{resume.filename}"',
        },
    )


@router.get("")
def list_resumes(session: Session = Depends(get_session)) -> list[dict]:
    rows = session.exec(select(Resume).order_by(Resume.uploaded_at.desc())).all()
    return [
        {
            "id": r.id,
            "filename": r.filename,
            "uploaded_at": r.uploaded_at.isoformat(),
            "parsed": r.parsed,
        }
        for r in rows
    ]
