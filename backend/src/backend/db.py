from collections.abc import Iterator

from sqlalchemy import event, text
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


if _settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _secure_sqlite_deletes(dbapi_connection, _connection_record) -> None:
        dbapi_connection.execute("PRAGMA secure_delete=ON")


def _ensure_columns() -> None:
    if not _settings.database_url.startswith("sqlite"):
        return
    with engine.begin() as conn:
        visitor_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(visitor_sessions)"))}
        if visitor_cols and "last_seen_at" not in visitor_cols:
            conn.execute(text("ALTER TABLE visitor_sessions ADD COLUMN last_seen_at TIMESTAMP"))
            conn.execute(text("UPDATE visitor_sessions SET last_seen_at = created_at WHERE last_seen_at IS NULL"))

        resume_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(resumes)"))}
        if "pdf_bytes" not in resume_cols:
            conn.execute(text("ALTER TABLE resumes ADD COLUMN pdf_bytes BLOB"))

        job_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(jobs)"))}
        if "founders" not in job_cols:
            conn.execute(text("ALTER TABLE jobs ADD COLUMN founders JSON"))
        if "contact_emails" not in job_cols:
            conn.execute(text("ALTER TABLE jobs ADD COLUMN contact_emails JSON"))
        if "application_status" not in job_cols:
            conn.execute(text("ALTER TABLE jobs ADD COLUMN application_status TEXT"))
        if "status_updated_at" not in job_cols:
            conn.execute(text("ALTER TABLE jobs ADD COLUMN status_updated_at TIMESTAMP"))
        if "is_starred" not in job_cols:
            conn.execute(text("ALTER TABLE jobs ADD COLUMN is_starred BOOLEAN DEFAULT 0"))


def init_db() -> None:
    import backend.models  # noqa: F401  ensure models are registered

    SQLModel.metadata.create_all(engine)
    _ensure_columns()


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
