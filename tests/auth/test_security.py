"""The auth package security tests."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
import pytest

from app.auth.security import (
    Argon2PasswordHasher,
    InvalidAccessTokenError,
    JWTAccessTokenCodec,
    get_access_token_codec,
    get_password_hasher,
    password_hasher,
)

USER_ID = UUID("0194f8a0-2000-7000-8000-000000000001")
SECRET_KEY = "a-test-secret-key-that-is-long-enough-for-hs256"


def make_codec(lifetime: timedelta = timedelta(minutes=15)) -> JWTAccessTokenCodec:
    """Return a codec with a test secret key."""
    return JWTAccessTokenCodec(SECRET_KEY, "HS256", lifetime)


def test_argon2_password_hasher() -> None:
    """Test passwords are hashed with argon2 and verified."""
    hasher = Argon2PasswordHasher()
    password_hash = hasher.hash("a-strong-password")
    assert password_hash.startswith("$argon2id$")
    assert hasher.verify("a-strong-password", password_hash) is True
    assert hasher.verify("another-password", password_hash) is False


def test_get_password_hasher() -> None:
    """Test the dependency returns the shared hasher."""
    assert get_password_hasher() is password_hasher


def test_jwt_access_token_codec() -> None:
    """Test an access token carries the user id and its lifetime."""
    codec = make_codec()
    access_token = codec.encode(USER_ID)
    assert access_token.expires_in == 900
    assert codec.decode(access_token.token) == USER_ID


def test_jwt_access_token_codec_expired() -> None:
    """Test an expired access token is rejected."""
    codec = make_codec(lifetime=timedelta(seconds=-1))
    with pytest.raises(InvalidAccessTokenError):
        codec.decode(codec.encode(USER_ID).token)


def test_jwt_access_token_codec_wrong_key() -> None:
    """Test an access token signed with another key is rejected."""
    other = JWTAccessTokenCodec(
        "another-secret-key-that-is-long-enough!", "HS256", timedelta(minutes=1)
    )
    with pytest.raises(InvalidAccessTokenError):
        make_codec().decode(other.encode(USER_ID).token)


@pytest.mark.parametrize(
    "payload",
    [
        {"iat": datetime.now(UTC), "exp": datetime.now(UTC) + timedelta(minutes=1)},
        {
            "sub": "not-a-uuid",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=1),
        },
    ],
    ids=["missing_subject", "invalid_subject"],
)
def test_jwt_access_token_codec_invalid_subject(payload: dict[str, object]) -> None:
    """Test an access token without a valid user id is rejected."""
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    with pytest.raises(InvalidAccessTokenError):
        make_codec().decode(token)


def test_get_access_token_codec() -> None:
    """Test the dependency returns a codec configured from the settings."""
    codec = get_access_token_codec()
    assert codec.decode(codec.encode(USER_ID).token) == USER_ID
