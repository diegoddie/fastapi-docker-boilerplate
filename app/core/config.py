"""The core config."""

from typing import Literal

from pydantic import PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Core settings."""

    ENVIRONMENT: Literal["local", "remote"] = "remote"
    DEBUG: bool = False

    API_ROOT: str = "/api"
    DOCS_PATH: str = "docs"
    OPENAPI_PATH: str = "openapi.json"

    CORS_ALLOWED_ORIGINS: list[str] = []

    # Database
    DATABASE_URL: PostgresDsn
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    # Pydantic
    model_config = SettingsConfigDict(env_prefix="FASTAPI_")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DOCS_URL(self) -> str | None:
        """Return the URL for the API documentation."""
        return (
            self.API_ROOT.rstrip("/") + "/" + self.DOCS_PATH.strip("/")
            if self.DOCS_PATH != ""
            else None
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def OPENAPI_URL(self) -> str | None:
        """Return the URL for the OpenAPI schema."""
        return (
            self.API_ROOT.rstrip("/") + "/" + self.OPENAPI_PATH.strip("/")
            if self.OPENAPI_PATH != ""
            else None
        )


settings = Settings()
