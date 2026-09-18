from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.db import get_session
from backend.main import app
from backend.models import Draft, Job, JobPreferences, Resume, VisitorJobState
from backend.services.resume_parser import ParsedResume
from backend.visitor import _hash_token


def test_replacement_resume_resets_private_profile_and_skip_uses_resume(monkeypatch) -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)

    def test_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = test_session
    try:
        client = TestClient(app)
        token = client.post("/sessions").json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        owner = _hash_token(token)
        with Session(engine) as db:
            job = Job(source_url="https://example.com/new", title="Engineer", description="React", company_name="Example", company_slug="example", locations=["Mumbai, India"])
            db.add(job)
            db.commit()
            db.refresh(job)
            db.add(Resume(owner_hash=owner, filename="old.pdf", raw_text="Old", parsed={"skills": ["Python"]}, pdf_bytes=b"%PDF-old"))
            db.add(JobPreferences(owner_hash=owner, target_roles=["Old role"]))
            db.add(Draft(owner_hash=owner, job_id=job.id, kind="email", body="Old draft"))
            db.add(VisitorJobState(owner_hash=owner, job_id=job.id, is_starred=True))
            db.commit()

        monkeypatch.setattr(
            "backend.routers.resumes.parse_pdf",
            lambda _: ("New resume", ParsedResume(skills=["React"], suggested_target_roles=["Frontend Engineer"])),
        )
        response = client.post(
            "/resumes", headers=headers,
            files={"file": ("new.pdf", b"%PDF-new", "application/pdf")},
        )
        assert response.status_code == 201
        assert [r["filename"] for r in client.get("/resumes", headers=headers).json()] == ["new.pdf"]
        assert client.get("/preferences", headers=headers).json()["target_roles"] == ["Frontend Engineer"]
        assert client.get("/preferences", headers=headers).json()["has_saved"] is False
        with Session(engine) as db:
            assert db.exec(select(Draft).where(Draft.owner_hash == owner)).all() == []
            assert db.exec(select(VisitorJobState).where(VisitorJobState.owner_hash == owner)).all() == []

        assert client.put("/preferences", headers=headers, json={"target_roles": ["Custom role"]}).status_code == 200
        assert client.delete("/preferences", headers=headers).status_code == 204
        assert client.get("/preferences", headers=headers).json()["target_roles"] == ["Frontend Engineer"]
        assert client.get("/preferences", headers=headers).json()["has_saved"] is False
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
