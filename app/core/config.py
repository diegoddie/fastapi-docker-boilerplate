"""The core config."""

import tomllib
from functools import cache
from pathlib import Path
from typing import Literal

from pydantic import Field, PostgresDsn, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@cache
def get_project_version() -> str:
    """Return the project version, declared once in pyproject.toml."""
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as file:
        return str(tomllib.load(file)["project"]["version"])


class Settings(BaseSettings):
    """Core settings."""

    ENVIRONMENT: Literal["local", "remote"] = "remote"
    DEBUG: bool = False
    VERSION: str = Field(default_factory=get_project_version)

    API_ROOT: str = "/api"
    # Why: the interactive docs expose the whole API surface, so by default they
    # are served only in local environments; set it explicitly to override.
    DOCS_ENABLED: bool | None = None
    DOCS_PATH: str = "docs"
    OPENAPI_PATH: str = "openapi.json"

    CORS_ALLOWED_ORIGINS: list[str] = []

    # Logging
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    # Why: log platforms parse one JSON object per line, but JSON is hard to read
    # in a terminal, so by default it is used only in remote environments.
    LOG_FORMAT: Literal["console", "json"] | None = None

    # Database
    DATABASE_URL: PostgresDsn
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    # Authentication
    # Why: it signs the access tokens, so it has no default and must be long
    # enough for HS256 (generate one with `openssl rand -hex 32`).
    SECRET_KEY: SecretStr = Field(min_length=32)
    JWT_ALGORITHM: Literal["HS256", "HS384", "HS512"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, gt=0)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30, gt=0)
    # Why: two tabs, or two requests sent together, refresh with the same token;
    # for this long after a rotation, the old token is not treated as stolen.
    REFRESH_TOKEN_REUSE_GRACE_SECONDS: int = Field(default=30, ge=0)

    # Google sign-in (disabled when the client id is not set)
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CERTS_URL: str = "https://www.googleapis.com/oauth2/v3/certs"

    # Pydantic
    model_config = SettingsConfigDict(env_prefix="FASTAPI_")

    @property
    def docs_enabled(self) -> bool:
        """Tell if the API docs and the OpenAPI schema are served."""
        if self.DOCS_ENABLED is None:
            return self.ENVIRONMENT == "local"
        return self.DOCS_ENABLED

    @property
    def log_format(self) -> Literal["console", "json"]:
        """Return how log lines are rendered."""
        if self.LOG_FORMAT is None:
            return "console" if self.ENVIRONMENT == "local" else "json"
        return self.LOG_FORMAT

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DOCS_URL(self) -> str | None:
        """Return the URL for the API documentation."""
        return self._api_url(self.DOCS_PATH) if self.docs_enabled else None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def OPENAPI_URL(self) -> str | None:
        """Return the URL for the OpenAPI schema."""
        return self._api_url(self.OPENAPI_PATH) if self.docs_enabled else None

    def _api_url(self, path: str) -> str:
        """Return a path under the API root."""
        return self.API_ROOT.rstrip("/") + "/" + path.strip("/")


settings = Settings()
