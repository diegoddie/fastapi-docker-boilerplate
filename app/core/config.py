"""The core config."""

import tomllib
from functools import cache
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    Field,
    PostgresDsn,
    RedisDsn,  # copier:celery
    SecretStr,
    computed_field,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@cache
def get_project_metadata() -> dict[str, Any]:
    """Return the project metadata, declared once in pyproject.toml."""
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as file:
        return dict(tomllib.load(file)["project"])


def get_project_version() -> str:
    """Return the project version."""
    return str(get_project_metadata()["version"])


def get_project_description() -> str:
    """Return the project description."""
    return str(get_project_metadata()["description"])


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

    # copier:sentry:start
    # Sentry (the DSN and the environment are read by sentry-sdk itself)
    SENTRY_TRACES_SAMPLE_RATE: float = Field(default=0.0, ge=0, le=1)

    # copier:sentry:end
    # Database
    DATABASE_URL: PostgresDsn
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    # copier:celery:start
    # Background jobs (Celery worker and beat)
    CELERY_BROKER_URL: RedisDsn = RedisDsn("redis://localhost:6379/0")
    # Why: Celery starts a process per CPU of the host, not of the container, and
    # each one takes ~75 MiB: on a large host, the worker would exhaust its memory.
    CELERY_WORKER_CONCURRENCY: int = Field(default=2, gt=0)

    # copier:celery:end
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

    # Why: each password hash takes 64 MiB of memory: at most this many run at
    # once in a worker (the others wait), so a burst of logins cannot exhaust the
    # memory of the container. Size the memory of a container accordingly.
    PASSWORD_HASH_CONCURRENCY: int = Field(default=2, gt=0)

    # Rate limits of the authentication endpoints
    # Why: per IP, they slow down credential stuffing and registration spam, but
    # many users may share an IP (offices, mobile networks): keep them generous.
    RATE_LIMIT_AUTH_REQUESTS_PER_MINUTE: int = Field(default=30, gt=0)
    RATE_LIMIT_REGISTRATIONS_PER_HOUR: int = Field(default=10, gt=0)
    # Why: per account and IP, they stop password guessing.
    RATE_LIMIT_PASSWORD_ATTEMPTS_PER_MINUTE: int = Field(default=5, gt=0)
    # Why: per recipient, whatever the IP, so nobody can flood someone's inbox.
    RATE_LIMIT_EMAILS_PER_HOUR: int = Field(default=5, gt=0)

    # Email verification and password reset
    # Why: the links in the emails open these pages of the frontend, which send
    # the token to the API.
    FRONTEND_URL: str = "http://localhost:3000"
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = Field(default=24, gt=0)
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = Field(default=30, gt=0)

    # Emails
    # Why: by default emails are written to the logs locally, sent remotely; the
    # console backend logs the links, so it must not be used where logs are kept.
    EMAIL_BACKEND: Literal["console", "smtp"] | None = None
    EMAIL_FROM: str = "no-reply@example.com"
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_SECURITY: Literal["starttls", "ssl", "none"] = "starttls"
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: SecretStr | None = None
    SMTP_TIMEOUT_SECONDS: float = Field(default=10, gt=0)

    # Google sign-in (disabled when the client id is not set)
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CERTS_URL: str = "https://www.googleapis.com/oauth2/v3/certs"

    # copier:posthog:start
    # PostHog product analytics and feature flags (disabled when the key is not set)
    # Why: the project API key only lets clients send events, so it is not secret
    # (the frontend has it too).
    POSTHOG_API_KEY: str | None = None
    # Why: the region of the PostHog project; https://us.i.posthog.com for the US.
    POSTHOG_HOST: str = "https://eu.i.posthog.com"
    # Why: a route behind a flag waits for PostHog; when it is slow, the flag is off.
    POSTHOG_FEATURE_FLAGS_TIMEOUT_SECONDS: float = Field(default=1, gt=0)

    # copier:posthog:end
    # copier:ai:start
    # AI with Claude (disabled when the API key is not set)
    ANTHROPIC_API_KEY: SecretStr | None = None
    AI_MODEL: str = "claude-opus-5-5"
    AI_TIMEOUT_SECONDS: float = Field(default=60, gt=0)
    # Why: the SDK retries rate limits, overloads and network errors; one retry
    # keeps a slow answer within two timeouts.
    AI_MAX_RETRIES: int = Field(default=1, ge=0)
    # Why: per user, since every request costs tokens.
    RATE_LIMIT_AI_REQUESTS_PER_HOUR: int = Field(default=20, gt=0)
    # Langfuse tracing of the AI calls (disabled when the keys are not set)
    LANGFUSE_PUBLIC_KEY: str | None = None
    LANGFUSE_SECRET_KEY: SecretStr | None = None
    LANGFUSE_BASE_URL: str = "https://cloud.langfuse.com"
    # Why: prompts and answers can hold personal data; by default the traces keep
    # the model, the tokens, the timings and the metadata, not the text.
    LANGFUSE_CAPTURE_CONTENT: bool = False
    # copier:ai:end

    # Pydantic
    model_config = SettingsConfigDict(env_prefix="FASTAPI_")

    @property
    def docs_enabled(self) -> bool:
        """Tell if the API docs and the OpenAPI schema are served."""
        if self.DOCS_ENABLED is None:
            return self.ENVIRONMENT == "local"
        return self.DOCS_ENABLED

    @property
    def email_backend(self) -> Literal["console", "smtp"]:
        """Return how emails are delivered."""
        if self.EMAIL_BACKEND is None:
            return "console" if self.ENVIRONMENT == "local" else "smtp"
        return self.EMAIL_BACKEND

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
