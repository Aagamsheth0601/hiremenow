from __future__ import annotations

import io

import anthropic
import pypdf
from pydantic import BaseModel, Field

from backend.config import get_settings


class Experience(BaseModel):
    title: str
    company: str
    start: str | None = None
    end: str | None = None
    summary: str | None = None


class Education(BaseModel):
    school: str
    degree: str | None = None
    field: str | None = None
    year: str | None = None


class Contact(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    location: str | None = None


class ParsedResume(BaseModel):
    contact: Contact = Field(default_factory=Contact)
    summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    years_experience: float | None = None


SYSTEM_PROMPT = """You extract structured fields from resume text. Be faithful to the source — do not invent information that is not present. Leave fields empty/null when the resume does not contain them.

For `years_experience`, estimate total professional experience in years (a single number, can be fractional). If only roles with date ranges are present, sum the durations. Return null if not derivable.

For `skills`, list concrete technical skills, tools, languages, and frameworks the candidate claims. Skip soft skills."""


class ResumeParseError(Exception):
    pass


def extract_text(pdf_bytes: bytes) -> str:
    try:
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    except Exception as e:
        raise ResumeParseError(f"Could not read PDF: {e}") from e

    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")

    text = "\n\n".join(p.strip() for p in pages if p.strip())
    if not text:
        raise ResumeParseError("PDF contained no extractable text (may be a scanned image).")
    return text


def extract_fields(text: str) -> ParsedResume:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise ResumeParseError("ANTHROPIC_API_KEY is not configured.")

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    response = client.messages.parse(
        model="claude-opus-4-7",
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Extract structured fields from this resume:\n\n<resume>\n{text}\n</resume>",
            }
        ],
        output_format=ParsedResume,
    )

    return response.parsed_output


def parse_pdf(pdf_bytes: bytes) -> tuple[str, ParsedResume]:
    text = extract_text(pdf_bytes)
    fields = extract_fields(text)
    return text, fields
