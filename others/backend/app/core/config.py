"""Template Settings pattern, with repository-absolute configuration and PostgreSQL-only validation."""
import json
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[4]
BRANDING = json.loads((ROOT / "others/config/branding.json").read_text(encoding="utf-8"))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", env_ignore_empty=True, extra="ignore")
    APP_ENV: Literal["development", "test", "production"] = "development"
    PROJECT_NAME: str = BRANDING["fullName"]
    SECRET_KEY: str
    DATABASE_URL: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:48621,https://localhost,http://localhost"

    @field_validator("SECRET_KEY")
    @classmethod
    def check_secret(cls, value: str) -> str:
        if len(value) < 32 or any(word in value.lower() for word in ("change_me", "changethis", "replace_")):
            raise ValueError("SECRET_KEY must be a generated secret of at least 32 characters")
        return value

    @field_validator("DATABASE_URL")
    @classmethod
    def postgres_only(cls, value: str) -> str:
        url = make_url(value)
        if url.get_backend_name() != "postgresql":
            raise ValueError("A real PostgreSQL database is required")
        return url.set(drivername="postgresql+psycopg").render_as_string(hide_password=False)


settings = Settings()
