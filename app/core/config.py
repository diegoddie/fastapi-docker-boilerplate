"""The core config."""

import tomllib
from functools import cache
from pathlib import Path
from typing import Literal

from pydantic import Field, PostgresDsn, computed_field
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

    # Database
    DATABASE_URL: PostgresDsn
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    # Pydantic
    model_config = SettingsConfigDict(env_prefix="FASTAPI_")

    @property
    def docs_enabled(self) -> bool:
        """Tell if the API docs and the OpenAPI schema are served."""
        if self.DOCS_ENABLED is None:
            return self.ENVIRONMENT == "local"
        return self.DOCS_ENABLED

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
