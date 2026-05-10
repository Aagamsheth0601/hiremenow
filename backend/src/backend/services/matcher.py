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


def _tokens(text: str) -> set[str]:
    return {
        t for t in _TOKEN_RE.findall(text.lower())
        if len(t) > 1 and t not in _STOPWORDS
    }


def _phrases(items: list[str]) -> list[str]:
    out = []
    for item in items:
        s = (item or "").strip().lower()
        if s:
            out.append(s)
    return out


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

    target_roles = _phrases((prefs.target_roles if prefs else []) or [])

    return MatchProfile(
        target_role_phrases=target_roles,
        skill_tokens=skill_tokens,
        skill_phrases=skill_phrases,
        experience_title_phrases=exp_titles,
    )


def _phrase_hits(phrases: list[str], text: str) -> int:
    text_lc = text.lower()
    return sum(1 for p in phrases if p and p in text_lc)


def score_job(job: Job, profile: MatchProfile) -> tuple[float, dict]:
    title = job.title or ""
    desc = job.description or ""
    title_lc = title.lower()
    desc_lc = desc.lower()

    title_role_hits = _phrase_hits(profile.target_role_phrases, title_lc)
    desc_role_hits = _phrase_hits(profile.target_role_phrases, desc_lc)

    title_skill_hits = _phrase_hits(profile.skill_phrases, title_lc)
    desc_skill_hits = _phrase_hits(profile.skill_phrases, desc_lc)

    title_tokens = _tokens(title)
    skill_token_hits_in_title = len(title_tokens & profile.skill_tokens)

    exp_title_hits = _phrase_hits(profile.experience_title_phrases, title_lc)

    score = 0.0
    score += 8.0 * title_role_hits
    score += 5.0 * title_skill_hits
    score += 2.0 * skill_token_hits_in_title
    score += 3.0 * exp_title_hits
    score += 1.5 * desc_role_hits
    score += min(desc_skill_hits, 6) * 0.5

    breakdown = {
        "title_role_hits": title_role_hits,
        "title_skill_hits": title_skill_hits,
        "skill_token_hits_in_title": skill_token_hits_in_title,
        "exp_title_hits": exp_title_hits,
        "desc_role_hits": desc_role_hits,
        "desc_skill_hits": desc_skill_hits,
    }
    return score, breakdown


def passes_threshold(score: float, breakdown: dict) -> bool:
    if breakdown["title_role_hits"] > 0:
        return True
    if breakdown["title_skill_hits"] > 0:
        return True
    if breakdown["skill_token_hits_in_title"] >= 2:
        return True
    if breakdown["exp_title_hits"] > 0:
        return True
    if breakdown["desc_role_hits"] >= 1 and breakdown["desc_skill_hits"] >= 2:
        return True
    return False
