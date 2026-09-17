from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import func
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.db import get_session
from backend.main import app
from backend.models import Draft, Job, JobPreferences, Resume, VisitorJobState, VisitorSession
from backend.visitor import _hash_token


def test_two_browsers_cannot_read_each_others_private_data() -> None:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)

    def test_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = test_session
    try:
        client = TestClient(app)
        token_a = client.post("/sessions").json()["token"]
        token_b = client.post("/sessions").json()["token"]
        a = {"Authorization": f"Bearer {token_a}"}
        b = {"Authorization": f"Bearer {token_b}"}

        with Session(engine) as db:
            job = Job(
                source_url="https://example.com/backend-job",
                title="Backend Engineer",
                description="Build Python APIs.",
                company_name="Example",
                company_slug="example",
                locations=["Mumbai, India"],
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            job_id = job.id
            db.add(Resume(
                owner_hash=_hash_token(token_a), filename="private.pdf",
                raw_text="Python", parsed={"skills": ["Python"], "experience": []},
                pdf_bytes=b"%PDF-private-a",
            ))
            db.add(JobPreferences(owner_hash=_hash_token(token_a), target_roles=["Backend Engineer"]))
            db.add(Draft(
                owner_hash=_hash_token(token_a), job_id=job_id, kind="email",
                subject="Private subject", body="Private body",
            ))
            db.commit()

        assert client.get("/resumes").status_code == 401
        bad_token = {"Authorization": "Bearer " + "!" * 43}
        assert client.get("/resumes", headers=bad_token).status_code == 401
        own_resumes = client.get("/resumes", headers=a)
        assert own_resumes.headers["cache-control"] == "no-store"
        assert len(own_resumes.json()) == 1
        assert client.get("/resumes", headers=b).json() == []
        assert client.get("/resumes/latest/pdf", headers=b).status_code == 404
        assert client.get("/resumes/latest/pdf", headers=a).content == b"%PDF-private-a"
        assert client.get("/preferences", headers=a).json()["target_roles"] == ["Backend Engineer"]
        assert client.get("/preferences", headers=b).json()["target_roles"] == []
        assert client.get("/preferences", headers=b).json()["has_saved"] is False

        jobs_a = client.get("/jobs?region=india", headers=a).json()
        jobs_b = client.get("/jobs?region=india", headers=b).json()
        assert jobs_a[0]["match_score"] > 0
        assert jobs_b == []
        public_jobs_b = client.get("/jobs?region=india&matched=false", headers=b).json()
        assert public_jobs_b[0].get("match_score") is None
        assert jobs_a[0]["draft_kinds"] == ["email"]
        assert public_jobs_b[0]["draft_kinds"] == []
        assert client.get(f"/jobs/{job_id}/draft?kind=email", headers=b).status_code == 404

        assert client.patch(f"/jobs/{job_id}/star", headers=a, json={"is_starred": True}).status_code == 200
        assert client.patch(f"/jobs/{job_id}/status", headers=a, json={"status": "applied"}).status_code == 200
        assert client.get("/jobs?region=india&matched=false", headers=b).json()[0]["is_starred"] is False
        assert client.get("/jobs?region=india&matched=false", headers=b).json()[0]["application_status"] is None
        assert client.get("/jobs/status-counts?region=india", headers=a).json()["applied"] == 1
        assert client.get("/jobs/status-counts?region=india", headers=b).json()["all"] == 0

        # A returning visitor keeps their data after a few hours.
        with Session(engine) as db:
            visitor_a = db.get(VisitorSession, _hash_token(token_a))
            visitor_a.last_seen_at = datetime.now(timezone.utc) - timedelta(hours=4)
            db.add(visitor_a)
            db.commit()
        assert len(client.get("/resumes", headers=a).json()) == 1

        # After seven idle days the old token is rejected and private data is erased.
        with Session(engine) as db:
            visitor_a = db.get(VisitorSession, _hash_token(token_a))
            visitor_a.last_seen_at = datetime.now(timezone.utc) - timedelta(days=8)
            db.add(visitor_a)
            db.commit()
        assert client.get("/resumes", headers=a).status_code == 401
        assert client.get("/resumes", headers=b).json() == []
        with Session(engine) as db:
            assert db.get(VisitorSession, _hash_token(token_a)) is None
            for model in (Resume, JobPreferences, Draft, VisitorJobState):
                assert db.exec(select(func.count()).select_from(model)).one() == 0
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
