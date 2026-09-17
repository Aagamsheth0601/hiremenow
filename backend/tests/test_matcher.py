from backend.models import Job, JobPreferences, Resume
from backend.services.matcher import build_profile, passes_threshold, score_job


def _job(title: str, description: str) -> Job:
    return Job(
        source_url="https://example.com/job",
        title=title,
        description=description,
        company_name="Example",
        company_slug="example",
    )


def test_relevant_job_ranks_above_unrelated_job_with_evidence() -> None:
    resume = Resume(filename="resume.pdf", raw_text="", parsed={
        "skills": ["Python", "FastAPI", "PostgreSQL"],
        "experience": [{"title": "Backend Engineer"}],
    })
    prefs = JobPreferences(target_roles=["Backend Engineer"])
    profile = build_profile(resume, prefs)

    relevant_score, relevant = score_job(
        _job("Backend Engineer", "Build Python and FastAPI services with PostgreSQL and Docker."),
        profile,
    )
    unrelated_score, unrelated = score_job(
        _job("Sales Manager", "Manage sales accounts and partnerships."), profile,
    )

    assert relevant_score > unrelated_score
    assert relevant["matched_skills"] == ["python", "fastapi", "postgresql"]
    assert relevant["missing_skills"] == ["Docker"]
    assert relevant["matched_target_roles"] == ["backend engineer"]
    assert passes_threshold(relevant_score, relevant)
    assert not passes_threshold(unrelated_score, unrelated)


def test_short_skill_name_does_not_match_inside_other_word() -> None:
    profile = build_profile(
        Resume(filename="resume.pdf", raw_text="", parsed={"skills": ["Go"]}), None
    )
    _, details = score_job(_job("Engineer", "Build systems at Google."), profile)
    assert details["matched_skills"] == []


def test_ai_suggested_roles_used_until_visitor_saves_preferences() -> None:
    resume = Resume(filename="resume.pdf", raw_text="", parsed={
        "skills": ["React"],
        "suggested_target_roles": ["Full Stack Engineer"],
    })
    profile = build_profile(resume, None)
    score, details = score_job(
        _job("Full-stack Engineer", "Build React applications."), profile
    )
    assert details["role_in_title"]
    assert score > 0
    assert passes_threshold(score, details)
