from backend.models import Job, Resume
from backend.services import outreach


def test_outreach_uses_only_current_visitor_and_respects_channel_limits(monkeypatch) -> None:
    job = Job(
        source_url="https://example.com/job",
        title="Data Engineer",
        company_name="Example Labs",
        company_slug="example-labs",
        description="Build reliable Python data systems.",
        locations=["Remote"],
    )
    resume = Resume(
        owner_hash="visitor-a",
        filename="resume.pdf",
        raw_text="Taylor writes Python data pipelines.",
        parsed={"contact": {"name": "Taylor Lee"}, "skills": ["Python"]},
    )

    monkeypatch.setattr(outreach, "_call_llm", lambda *_args, **_kwargs: {"message": "x" * 301})
    linkedin = outreach.draft_linkedin(job, resume)
    assert 0 < len(linkedin) <= 300
    assert "Taylor" in linkedin
    assert "Data Engineer" in linkedin
    assert "Accenture" not in linkedin

    monkeypatch.setattr(outreach, "_call_llm", lambda *_args, **_kwargs: {"subject": "A relevant subject", "body": "x" * 1001})
    email = outreach.draft_email(job, resume)
    assert 0 < len(email.body) <= 1000
    assert "Taylor" in email.body
    assert "Accenture" not in email.body
