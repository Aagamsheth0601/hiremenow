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

    frontend_url: str = "http://localhost:5173"

    anthropic_api_key: str = ""

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    resume_parser_model: str = "meta-llama/llama-3.3-70b-instruct:free"

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"


@lru_cache
def get_settings() -> Settings:
    return Settings()
