"""The auth package security tests."""

from datetime import UTC, datetime, timedelta
from uuid import uuid7

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


def test_jwt_access_token_codec(jwt_access_token_codec: JWTAccessTokenCodec) -> None:
    """Test an access token carries the user id and its lifetime."""
    user_id = uuid7()
    access_token = jwt_access_token_codec.encode(user_id)
    assert access_token.expires_in == 900
    assert jwt_access_token_codec.decode(access_token.token) == user_id


def test_jwt_access_token_codec_expired(
    jwt_access_token_codec: JWTAccessTokenCodec,
) -> None:
    """Test an expired access token is rejected."""
    jwt_access_token_codec.lifetime = timedelta(seconds=-1)
    token = jwt_access_token_codec.encode(uuid7()).token
    with pytest.raises(InvalidAccessTokenError):
        jwt_access_token_codec.decode(token)


def test_jwt_access_token_codec_wrong_key(
    jwt_access_token_codec: JWTAccessTokenCodec,
) -> None:
    """Test an access token signed with another key is rejected."""
    other_codec = JWTAccessTokenCodec(
        "another-secret-key-that-is-long-enough!", "HS256", timedelta(minutes=1)
    )
    with pytest.raises(InvalidAccessTokenError):
        jwt_access_token_codec.decode(other_codec.encode(uuid7()).token)


@pytest.mark.parametrize(
    "subject",
    [None, "not-a-uuid"],
    ids=["missing_subject", "invalid_subject"],
)
def test_jwt_access_token_codec_invalid_subject(
    jwt_access_token_codec: JWTAccessTokenCodec, subject: str | None
) -> None:
    """Test an access token without a valid user id is rejected."""
    now = datetime.now(UTC)
    payload = {"sub": subject, "iat": now, "exp": now + timedelta(minutes=1)}
    token = jwt.encode(
        {name: value for name, value in payload.items() if value is not None},
        jwt_access_token_codec.secret_key,
        algorithm="HS256",
    )
    with pytest.raises(InvalidAccessTokenError):
        jwt_access_token_codec.decode(token)


def test_get_access_token_codec() -> None:
    """Test the dependency returns a codec configured from the settings."""
    codec = get_access_token_codec()
    user_id = uuid7()
    assert codec.decode(codec.encode(user_id).token) == user_id
