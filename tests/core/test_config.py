"""The core config tests."""

from app.core.config import Settings


def test_settings_docs_urls() -> None:
    """Test the docs URLs are built from the API root and the paths."""
    settings = Settings(API_ROOT="/api/", DOCS_PATH="/docs/", OPENAPI_PATH="schema")
    assert settings.DOCS_URL == "/api/docs"
    assert settings.OPENAPI_URL == "/api/schema"


def test_settings_docs_urls_disabled() -> None:
    """Test empty paths disable the docs and the OpenAPI schema."""
    settings = Settings(DOCS_PATH="", OPENAPI_PATH="")
    assert settings.DOCS_URL is None
    assert settings.OPENAPI_URL is None
