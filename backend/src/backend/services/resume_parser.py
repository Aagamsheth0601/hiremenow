from __future__ import annotations

import io
import json

import pypdf
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

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


SYSTEM_PROMPT_TEMPLATE = """You extract structured fields from resume text. Be faithful to the source — do not invent information that is not present. Leave fields empty/null when the resume does not contain them.

For `years_experience`, estimate total professional experience in years (a single number, can be fractional). If only roles with date ranges are present, sum the durations. Return null if not derivable.

For `skills`, list concrete technical skills, tools, languages, and frameworks the candidate claims. Skip soft skills.

Return ONLY a single JSON object matching this schema. No prose, no markdown fences, no commentary.

Schema:
{schema}"""


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


def _extract_json_block(content: str) -> str | None:
    start = content.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(content)):
        if content[i] == "{":
            depth += 1
        elif content[i] == "}":
            depth -= 1
            if depth == 0:
                return content[start : i + 1]
    return None


def _parse_response(content: str) -> ParsedResume:
    try:
        return ParsedResume.model_validate(json.loads(content))
    except (json.JSONDecodeError, ValidationError):
        pass

    block = _extract_json_block(content)
    if block is None:
        raise ResumeParseError("Model response did not contain a JSON object.")
    try:
        return ParsedResume.model_validate(json.loads(block))
    except (json.JSONDecodeError, ValidationError) as e:
        raise ResumeParseError(f"Model returned invalid JSON: {e}") from e


def extract_fields(text: str) -> ParsedResume:
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise ResumeParseError("OPENROUTER_API_KEY is not configured.")

    client = OpenAI(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
    )

    schema = json.dumps(ParsedResume.model_json_schema(), indent=2)
    system = SYSTEM_PROMPT_TEMPLATE.replace("{schema}", schema)

    try:
        response = client.chat.completions.create(
            model=settings.resume_parser_model,
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": f"Extract structured fields from this resume:\n\n<resume>\n{text}\n</resume>",
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=4096,
        )
    except Exception as e:
        raise ResumeParseError(f"OpenRouter request failed: {e}") from e

    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise ResumeParseError("Model returned empty response.")
    return _parse_response(content)


def parse_pdf(pdf_bytes: bytes) -> tuple[str, ParsedResume]:
    text = extract_text(pdf_bytes)
    fields = extract_fields(text)
    return text, fields
