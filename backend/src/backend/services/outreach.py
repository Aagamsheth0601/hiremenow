from __future__ import annotations

import json
from typing import Any

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from backend.config import get_settings
from backend.models import Job, Resume


class OutreachError(Exception):
    pass


class EmailDraft(BaseModel):
    subject: str
    body: str


_EMAIL_SYSTEM = """You draft cold outreach emails for a candidate applying to a specific job. Tone: warm, direct, professional — not stiff, not gimmicky.

Hard rules:
- Entire email body must be at most 1000 characters.
- Subject line: 6-10 words, specific to the role and the candidate's strongest relevant angle. No clickbait.
- Open with a greeting. If a hiring manager or founder name is provided, use it. Otherwise use "Hi {{Company}} team,".
- 1-2 sentences on why this role/company specifically (use the company one-liner and the role).
- 2-3 sentences on the candidate's most relevant qualifications drawn from the resume. Name 2-4 concrete skills/experiences that map to this job description. Do NOT list everything.
- 1 sentence call-to-action: ask for a 15-min chat or invite a reply.
- Sign off with the candidate's name from the resume.
- Do NOT invent skills, employers, dates, or accomplishments. Use only what's in the resume.
- Do NOT include subject line inside the body.
- Plain text body — no markdown, no bullet points unless absolutely warranted.

Return ONLY a JSON object: {"subject": "...", "body": "..."}."""

_LINKEDIN_SYSTEM = """Draft a brief LinkedIn connection message about the target job.
Use only candidate experience that appears in the supplied resume and only company details
that appear in the job information. Never infer a specific employer or achievement.
Mention the role, one relevant skill or experience, and a short invitation to connect.
Use a founder's first name only when provided. Sign with the candidate's first name if known.
Keep the entire message at or below 300 characters, including spaces.
Return only JSON with one string field named message."""


def _client() -> OpenAI:
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise OutreachError("OPENROUTER_API_KEY is not configured.")
    return OpenAI(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
    )


def _resume_context(resume: Resume) -> str:
    parsed: dict[str, Any] = resume.parsed or {}
    contact = parsed.get("contact") or {}
    name = contact.get("name") or "(name not in resume)"
    skills = parsed.get("skills") or []
    summary = parsed.get("summary") or ""
    experience = parsed.get("experience") or []

    exp_lines = []
    for e in experience[:5]:
        if not isinstance(e, dict):
            continue
        title = e.get("title") or ""
        company = e.get("company") or ""
        s = e.get("summary") or ""
        line = f"- {title} at {company}"
        if s:
            line += f": {s[:280]}"
        exp_lines.append(line)

    return (
        f"Candidate name: {name}\n"
        f"Summary: {summary}\n"
        f"Top skills: {', '.join(skills[:25])}\n"
        f"Recent experience:\n" + "\n".join(exp_lines)
    )


def _job_context(job: Job) -> str:
    return (
        f"Company: {job.company_name}\n"
        f"Role: {job.title}\n"
        f"Company one-liner: {job.company_one_liner or '(none)'}\n"
        f"Industry: {job.company_industry or '(unknown)'}\n"
        f"Stage: {job.company_stage or '(unknown)'}\n"
        f"Locations: {', '.join(job.locations) or '(unspecified)'}\n"
        f"Job description:\n{(job.description or '(no description scraped)')[:3500]}"
    )


def _extract_json_block(content: str) -> str | None:
    start = content.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(content)):
        ch = content[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return content[start : i + 1]
    return None


def _call_llm(system: str, user: str, *, max_tokens: int) -> dict:
    settings = get_settings()
    client = _client()
    try:
        response = client.chat.completions.create(
            model=settings.resume_parser_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
            max_tokens=max_tokens,
        )
    except Exception as e:
        raise OutreachError(f"OpenRouter request failed: {e}") from e

    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise OutreachError("Model returned empty response.")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        block = _extract_json_block(content)
        if not block:
            raise OutreachError(f"Model returned non-JSON response: {content[:200]}")
        try:
            return json.loads(block)
        except json.JSONDecodeError as e:
            raise OutreachError(
                f"Model returned malformed JSON: {e}; raw: {content[:200]}"
            ) from e


def _email_template_fallback(job: Job, resume: Resume) -> EmailDraft:
    parsed = resume.parsed or {}
    contact = parsed.get("contact") or {}
    name = (contact.get("name") or "").strip()
    skills = [s for s in (parsed.get("skills") or []) if isinstance(s, str)][:4]
    years = parsed.get("years_experience")

    founder_first = None
    if job.founders:
        first = next(
            (f for f in job.founders if isinstance(f, dict) and f.get("name")),
            None,
        )
        if first:
            founder_first = first["name"].split()[0]

    greeting = (
        f"Hi {founder_first},"
        if founder_first
        else f"Hi {job.company_name} team,"
    )

    first_name = name.split()[0] if name else "I"
    role = job.title or "the role"
    subject = (
        f"{first_name} — interested in the {role} role at {job.company_name}"
        if name
        else f"Interested in the {role} role at {job.company_name}"
    )

    one_liner = (job.company_one_liner or "").strip().rstrip(".")
    intro = (
        f"I came across your {role} posting and wanted to reach out — "
        f"the work you're doing on {one_liner} resonated with me."
        if one_liner
        else f"I came across your {role} posting at {job.company_name} and wanted to reach out."
    )

    skill_pitch = ""
    if skills:
        skill_list = ", ".join(skills[:3])
        if isinstance(years, (int, float)) and years > 0:
            skill_pitch = (
                f"I bring around {int(years)} years of experience with a stack "
                f"centered on {skill_list}, which feels aligned with what you're building."
            )
        else:
            skill_pitch = (
                f"My recent work centers on {skill_list}, which feels closely "
                f"aligned with what you're building."
            )

    cta = (
        "Would you have 15 minutes to chat about how I could contribute? "
        "Happy to share more — resume attached."
    )

    sign = f"— {name}" if name else "— [Your Name]"

    body_parts = [greeting, "", intro]
    if skill_pitch:
        body_parts.extend(["", skill_pitch])
    body_parts.extend(["", cta, "", sign])

    return EmailDraft(subject=subject, body="\n".join(body_parts)[:1000])


def draft_email(job: Job, resume: Resume) -> EmailDraft:
    founders_line = ""
    if job.founders:
        names = [f.get("name") for f in job.founders if isinstance(f, dict) and f.get("name")]
        if names:
            founders_line = f"\nKnown founder(s) to address: {', '.join(names)}"

    user = (
        f"{_resume_context(resume)}\n\n--- TARGET JOB ---\n{_job_context(job)}{founders_line}\n\n"
        "Write the outreach email."
    )
    try:
        data = _call_llm(_EMAIL_SYSTEM, user, max_tokens=900)
        try:
            email = EmailDraft.model_validate(data)
            if (
                email.subject
                and len(email.subject.strip()) >= 5
                and 0 < len(email.body.strip()) <= 1000
            ):
                return email
        except ValidationError:
            pass
    except OutreachError:
        pass

    return _email_template_fallback(job, resume)


def _linkedin_template(job: Job, resume: Resume) -> str:
    parsed = resume.parsed or {}
    contact = parsed.get("contact") or {}
    name = (contact.get("name") or "").strip().split()
    skills = [skill for skill in (parsed.get("skills") or []) if isinstance(skill, str)]
    founder = next((f for f in (job.founders or []) if isinstance(f, dict) and f.get("name")), None)
    greeting = f"Hi {founder['name'].split()[0]}," if founder else "Hi,"
    role = (job.title or "the open role")[:65]
    company = (job.company_name or "your company")[:50]
    skill = skills[0][:45] if skills else "my experience"
    signoff = f" I'm {name[0]}." if name else ""
    message = f"{greeting} I'm interested in the {role} role at {company}. My background in {skill} looks relevant. Would you be open to connecting?{signoff}"
    return message[:300]


def draft_linkedin(job: Job, resume: Resume) -> str:
    import logging
    _log = logging.getLogger(__name__)

    founders_line = ""
    if job.founders:
        names = [f.get("name") for f in job.founders if isinstance(f, dict) and f.get("name")]
        if names:
            founders_line = f"\nKnown founder(s): {', '.join(names)}"

    user = (
        f"{_resume_context(resume)}\n\n--- TARGET JOB ---\n{_job_context(job)}{founders_line}\n\n"
        "Write the LinkedIn message."
    )
    try:
        data = _call_llm(_LINKEDIN_SYSTEM, user, max_tokens=1200)
        msg = data.get("message") if isinstance(data, dict) else None
        if isinstance(msg, str):
            msg = msg.strip()
            if 0 < len(msg) <= 300:
                return msg
            _log.warning("linkedin LLM message too short (%d chars), using template", len(msg))
        else:
            _log.warning("linkedin LLM returned no 'message' key: %s", list(data.keys()) if isinstance(data, dict) else type(data))
    except OutreachError as e:
        _log.warning("linkedin LLM call failed: %s — using template fallback", e)

    return _linkedin_template(job, resume)
