from collections.abc import Iterator

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


def init_db() -> None:
    import backend.models  # noqa: F401  ensure models are registered

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
