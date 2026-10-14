"""The core config tests."""

import tomllib

import pytest
from pydantic import ValidationError

from app.core.config import PROJECT_ROOT, Settings, get_project_version


def test_settings_docs_enabled_by_environment() -> None:
    """Test the docs are enabled by default only in local environments."""
    assert Settings(ENVIRONMENT="local").docs_enabled is True
    assert Settings(ENVIRONMENT="remote").docs_enabled is False


def test_settings_docs_enabled_explicitly() -> None:
    """Test the docs setting overrides the environment default."""
    assert Settings(ENVIRONMENT="remote", DOCS_ENABLED=True).docs_enabled is True
    assert Settings(ENVIRONMENT="local", DOCS_ENABLED=False).docs_enabled is False


def test_settings_docs_urls() -> None:
    """Test the docs URLs are built from the API root and the paths."""
    settings = Settings(
        DOCS_ENABLED=True, API_ROOT="/api/", DOCS_PATH="/docs/", OPENAPI_PATH="schema"
    )
    assert settings.DOCS_URL == "/api/docs"
    assert settings.OPENAPI_URL == "/api/schema"


def test_settings_docs_urls_disabled() -> None:
    """Test disabled docs have no URLs."""
    settings = Settings(DOCS_ENABLED=False)
    assert settings.DOCS_URL is None
    assert settings.OPENAPI_URL is None


def test_settings_log_format_by_environment() -> None:
    """Test logs are JSON by default only in remote environments."""
    assert Settings(ENVIRONMENT="local").log_format == "console"
    assert Settings(ENVIRONMENT="remote").log_format == "json"


def test_settings_log_format_explicitly() -> None:
    """Test the log format setting overrides the environment default."""
    assert Settings(ENVIRONMENT="local", LOG_FORMAT="json").log_format == "json"
    assert Settings(ENVIRONMENT="remote", LOG_FORMAT="console").log_format == "console"


def test_settings_version() -> None:
    """Test the version is read from pyproject.toml."""
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as file:
        version = tomllib.load(file)["project"]["version"]
    assert get_project_version() == version
    assert version == Settings().VERSION


def test_settings_secret_key_too_short() -> None:
    """Test a secret key too short for HS256 is rejected at startup."""
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(SECRET_KEY="too-short")
