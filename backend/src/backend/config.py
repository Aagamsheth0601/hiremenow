from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "hiremenow"
    debug: bool = False

    database_url: str = "sqlite:///./hiremenow.db"

    frontend_url: str = "http://localhost:3000"

    anthropic_api_key: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"


@lru_cache
def get_settings() -> Settings:
    return Settings()
