"""Token verification. The one place where trusting the wrong input is fatal."""

import time
import uuid

import jwt
import pytest

from app.core.config import get_settings
from app.core.security import (
    InvalidToken,
    hash_anonymous_token,
    new_anonymous_token,
    verify_access_token,
)

SECRET = "test-secret-at-least-32-characters-long!!"


@pytest.fixture(autouse=True)
def _hs256_project(monkeypatch: pytest.MonkeyPatch):
    """
    Exercises the HS256 fallback path.

    Supabase issues ES256 by default and the JWKS branch is covered by the live
    end-to-end run; this keeps the offline suite free of a network dependency.
    """
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _token(**overrides) -> str:
    settings = get_settings()
    claims = {
        "sub": str(uuid.uuid4()),
        "email": "seller@example.com",
        "aud": "authenticated",
        "iss": settings.jwt_issuer,
        "exp": int(time.time()) + 600,
        **overrides,
    }
    return jwt.encode(claims, SECRET, algorithm="HS256")


def test_valid_token_yields_its_subject() -> None:
    subject = str(uuid.uuid4())
    user = verify_access_token(_token(sub=subject))
    assert user.user_id == subject
    assert user.email == "seller@example.com"


def test_expired_token_is_rejected() -> None:
    with pytest.raises(InvalidToken):
        verify_access_token(_token(exp=int(time.time()) - 10))


def test_token_from_another_project_is_rejected() -> None:
    with pytest.raises(InvalidToken):
        verify_access_token(_token(iss="https://evil.example.com/auth/v1"))


def test_wrong_audience_is_rejected() -> None:
    with pytest.raises(InvalidToken):
        verify_access_token(_token(aud="anon"))


def test_unsigned_token_is_rejected() -> None:
    """The alg=none attack: a token nobody signed must never be trusted."""
    forged = jwt.encode({"sub": str(uuid.uuid4())}, key="", algorithm="none")
    with pytest.raises(InvalidToken):
        verify_access_token(forged)


def test_token_signed_with_the_wrong_key_is_rejected() -> None:
    forged = jwt.encode(
        {"sub": "x", "exp": time.time() + 60}, "other", algorithm="HS256"
    )
    with pytest.raises(InvalidToken):
        verify_access_token(forged)


def test_garbage_is_rejected() -> None:
    with pytest.raises(InvalidToken):
        verify_access_token("not-a-token")


def test_anonymous_tokens_are_unguessable_and_stored_only_as_digests() -> None:
    tokens = {new_anonymous_token() for _ in range(200)}
    assert len(tokens) == 200
    assert all(len(token) >= 40 for token in tokens)

    token = new_anonymous_token()
    digest = hash_anonymous_token(token)
    assert token not in digest
    assert digest == hash_anonymous_token(token)
    assert digest != hash_anonymous_token(new_anonymous_token())
