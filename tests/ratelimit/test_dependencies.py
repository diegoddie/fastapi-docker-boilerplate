"""The ratelimit package dependencies tests."""

from fastapi import Request

from app.ratelimit.dependencies import get_client_ip


def test_get_client_ip() -> None:
    """Test the client address is read from the connection."""
    request = Request({"type": "http", "client": ("203.0.113.7", 54321)})
    assert get_client_ip(request) == "203.0.113.7"


def test_get_client_ip_unknown() -> None:
    """Test a request without a client address still gets a key."""
    assert get_client_ip(Request({"type": "http"})) == "unknown"
