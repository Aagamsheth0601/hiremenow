from collections.abc import Iterator

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from backend.config import get_settings

_settings = get_settings()

engine = create_engine(
    _settings.database_url,
    echo=_settings.debug,
    connect_args={"check_same_thread": False}
    if _settings.database_url.startswith("sqlite")
    else {},
)


def _ensure_columns() -> None:
    if not _settings.database_url.startswith("sqlite"):
        return
    with engine.begin() as conn:
        resume_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(resumes)"))}
        if "pdf_bytes" not in resume_cols:
            conn.execute(text("ALTER TABLE resumes ADD COLUMN pdf_bytes BLOB"))

        job_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(jobs)"))}
        if "founders" not in job_cols:
            conn.execute(text("ALTER TABLE jobs ADD COLUMN founders JSON"))
        if "contact_emails" not in job_cols:
            conn.execute(text("ALTER TABLE jobs ADD COLUMN contact_emails JSON"))


def init_db() -> None:
    import backend.models  # noqa: F401  ensure models are registered

    SQLModel.metadata.create_all(engine)
    _ensure_columns()


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
