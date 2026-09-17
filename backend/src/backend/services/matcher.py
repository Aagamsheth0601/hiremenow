from __future__ import annotations

import re
from dataclasses import dataclass

from backend.models import Job, JobPreferences, Resume

_TOKEN_RE = re.compile(r"[a-z0-9+#./-]+")
_STOPWORDS = {
    "the", "a", "an", "and", "or", "for", "to", "of", "in", "on", "with",
    "at", "by", "from", "is", "are", "be", "as", "we", "you", "your", "our",
    "this", "that", "it", "will", "have", "has", "any", "all", "but",
    "engineer", "engineering", "developer", "team", "role", "work", "join",
    "build", "building", "company", "product", "products", "platform",
    "experience", "looking", "candidate", "ideal", "strong", "ability",
}

# A small vocabulary lets us name skills present in a job post but absent from
# the resume. The resume's own skills are also searched, so new skills can match
# without waiting for this list to be updated.
_KNOWN_SKILLS = (
    "Python", "Java", "JavaScript", "TypeScript", "Go", "Rust", "C++", "C#",
    "React", "Next.js", "Vue", "Angular", "Node.js", "Express", "FastAPI",
    "Django", "Flask", "Spring Boot", "AWS", "Azure", "GCP", "Docker",
    "Kubernetes", "Terraform", "PostgreSQL", "MySQL", "MongoDB", "Redis",
    "GraphQL", "SQL", "Linux", "Kafka", "Spark", "PyTorch", "TensorFlow",
    "Machine Learning", "CI/CD", "Git", "REST API", "HTML", "CSS",
)
_ALIASES = {
    "node.js": ("node.js", "nodejs", "node js"),
    "next.js": ("next.js", "nextjs", "next js"),
    "react": ("react", "react.js", "reactjs"),
    "postgresql": ("postgresql", "postgres"),
    "kubernetes": ("kubernetes", "k8s"),
    "javascript": ("javascript",),
    "typescript": ("typescript",),
    "rest api": ("rest api", "restful api"),
}


def _tokens(text: str) -> set[str]:
    return {
        t for t in _TOKEN_RE.findall(text.lower().replace("-", " "))
        if len(t) > 1 and t not in _STOPWORDS
    }


def _phrases(items: list[str]) -> list[str]:
    out = []
    for item in items:
        s = (item or "").strip().lower()
        if s:
            out.append(s)
    return out


def _contains_phrase(text: str, phrase: str) -> bool:
    """Match whole terms, so 'Go' does not match 'Google'."""
    variants = _ALIASES.get(phrase.lower(), (phrase.lower(),))
    text = text.replace("-", " ")
    return any(
        re.search(r"(?<![a-z0-9])" + re.escape(v.replace("-", " ")) + r"(?![a-z0-9])", text)
        for v in variants
    )


@dataclass
class MatchProfile:
    target_role_phrases: list[str]
    skill_tokens: set[str]
    skill_phrases: list[str]
    experience_title_phrases: list[str]

    def is_empty(self) -> bool:
        return not (
            self.target_role_phrases
            or self.skill_tokens
            or self.experience_title_phrases
        )


def build_profile(resume: Resume | None, prefs: JobPreferences | None) -> MatchProfile:
    parsed = (resume.parsed if resume else {}) or {}
    skills_raw: list[str] = parsed.get("skills") or []
    experience: list[dict] = parsed.get("experience") or []

    skill_phrases = _phrases(skills_raw)
    skill_tokens: set[str] = set()
    for s in skill_phrases:
        skill_tokens |= _tokens(s)

    exp_titles = _phrases([e.get("title", "") for e in experience if isinstance(e, dict)])

    saved_roles = (prefs.target_roles if prefs else []) or []
    suggested_roles = parsed.get("suggested_target_roles") or []
    target_roles = _phrases(saved_roles or suggested_roles)

    return MatchProfile(
        target_role_phrases=target_roles,
        skill_tokens=skill_tokens,
        skill_phrases=skill_phrases,
        experience_title_phrases=exp_titles,
    )


def _phrase_hits(phrases: list[str], text: str) -> int:
    text_lc = text.lower()
    return sum(1 for p in phrases if p and _contains_phrase(text_lc, p))


def score_job(job: Job, profile: MatchProfile) -> tuple[float, dict]:
    title = job.title or ""
    desc = job.description or ""
    title_lc = title.lower()
    desc_lc = desc.lower()

    title_role_hits = _phrase_hits(profile.target_role_phrases, title_lc)
    desc_role_hits = _phrase_hits(profile.target_role_phrases, desc_lc)
    exp_title_hits = _phrase_hits(profile.experience_title_phrases, title_lc)

    # Score by coverage of skills actually named in this job post. A long resume
    # should not automatically outrank a focused resume with the relevant skills.
    resume_skills = list(dict.fromkeys(profile.skill_phrases))
    mentioned_resume_skills = [s for s in resume_skills if _contains_phrase(desc_lc, s) or _contains_phrase(title_lc, s)]
    known_in_job = [s for s in _KNOWN_SKILLS if _contains_phrase(desc_lc, s.lower()) or _contains_phrase(title_lc, s.lower())]
    matched_known = [s for s in known_in_job if any(_contains_phrase(s.lower(), r) or _contains_phrase(r, s.lower()) for r in resume_skills)]
    missing_skills = [s for s in known_in_job if s not in matched_known]
    matched_skills = list(dict.fromkeys(mentioned_resume_skills))
    for skill in matched_known:
        if not any(_contains_phrase(skill.lower(), s) or _contains_phrase(s, skill.lower()) for s in matched_skills):
            matched_skills.append(skill.lower())

    job_skill_count = len(matched_skills) + len(missing_skills)
    skill_coverage = len(matched_skills) / job_skill_count if job_skill_count else 0.0
    title_tokens = _tokens(title)
    role_overlap = max(
        (len(title_tokens & _tokens(role)) / len(_tokens(role)) for role in profile.target_role_phrases if _tokens(role)),
        default=0.0,
    )
    role_points = 3.5 if title_role_hits else (2.0 * role_overlap if role_overlap else (1.0 if desc_role_hits else 0.0))
    skill_points = 5.0 * skill_coverage
    experience_points = 1.0 if exp_title_hits else 0.0
    evidence_points = 0.5 if matched_skills and title_role_hits else 0.0
    score = 2.0 * min(10.0, role_points + skill_points + experience_points + evidence_points)

    breakdown = {
        "title_role_hits": title_role_hits,
        "desc_role_hits": desc_role_hits,
        "exp_title_hits": exp_title_hits,
        "matched_skills": matched_skills[:10],
        "missing_skills": missing_skills[:10],
        "matched_target_roles": [r for r in profile.target_role_phrases if _contains_phrase(title_lc, r) or _contains_phrase(desc_lc, r)],
        "skill_coverage": round(skill_coverage, 2),
        "role_in_title": bool(title_role_hits or role_overlap >= 0.5),
    }
    return score, breakdown


_GENERIC_SKILLS = {
    "git", "sql", "css", "api", "cli", "os", "ui", "ux", "ci", "cd",
    "html", "rest", "oop", "ide", "qa", "agile", "scrum", "jira",
}


def search_terms_from_profile(
    profile: MatchProfile, *, max_terms: int = 12
) -> list[str]:
    if profile.is_empty():
        return []

    terms: list[str] = []
    seen_lower: set[str] = set()

    def _add(term: str) -> bool:
        if len(terms) >= max_terms:
            return False
        if term in seen_lower:
            return False
        if any(term in existing for existing in seen_lower):
            return False
        terms.append(term)
        seen_lower.add(term)
        return True

    for role in profile.target_role_phrases[:5]:
        _add(role)

    for title in profile.experience_title_phrases[:3]:
        _add(title)

    for skill in profile.skill_phrases:
        if len(terms) >= max_terms:
            break
        if len(skill) <= 2 or skill in _GENERIC_SKILLS:
            continue
        _add(skill)

    return terms


def passes_threshold(score: float, breakdown: dict) -> bool:
    return bool(
        breakdown["role_in_title"]
        or breakdown["exp_title_hits"]
        or (breakdown["desc_role_hits"] and len(breakdown["matched_skills"]) >= 2)
        or len(breakdown["matched_skills"]) >= 3
    )
