import hashlib
import logging
import secrets
import time
from dataclasses import dataclass

import jwt
from jwt import PyJWKClient

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

_ANON_TOKEN_BYTES = 32


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    user_id: str
    email: str | None


class _JwksCache:
    """
    Caches the project's public keys.

    Supabase issues asymmetric (ES256/RS256) tokens by default and serves the
    public keys from a JWKS endpoint, so verification is local and needs no
    round trip to the Auth server per request.
    """

    def __init__(self, url: str, ttl_seconds: int = 600) -> None:
        self._url = url
        self._ttl = ttl_seconds
        self._client: PyJWKClient | None = None
        self._loaded_at = 0.0

    def client(self) -> PyJWKClient:
        now = time.monotonic()
        if self._client is None or now - self._loaded_at > self._ttl:
            self._client = PyJWKClient(self._url, cache_keys=True)
            self._loaded_at = now
        return self._client


_jwks_cache: _JwksCache | None = None


def _get_jwks_cache(settings: Settings) -> _JwksCache:
    global _jwks_cache
    if _jwks_cache is None:
        _jwks_cache = _JwksCache(settings.jwks_url)
    return _jwks_cache


def reset_jwks_cache() -> None:
    global _jwks_cache
    _jwks_cache = None


class InvalidToken(Exception):
    pass


def verify_access_token(token: str) -> AuthenticatedUser:
    """
    Verifies a Supabase access token and returns its subject.

    Tries the JWKS public keys first, then falls back to the shared HS256
    secret for older projects that have not migrated to signing keys.
    """
    settings = get_settings()
    claims: dict | None = None

    header = _read_header(token)
    algorithm = header.get("alg", "")

    if algorithm.startswith(("ES", "RS", "PS", "Ed")):
        claims = _verify_asymmetric(token, settings)
    elif algorithm == "HS256":
        claims = _verify_symmetric(token, settings)
    else:
        raise InvalidToken(f"unsupported algorithm: {algorithm!r}")

    subject = claims.get("sub")
    if not subject:
        raise InvalidToken("token has no subject")

    return AuthenticatedUser(user_id=subject, email=claims.get("email"))


def _read_header(token: str) -> dict:
    try:
        return jwt.get_unverified_header(token)
    except jwt.PyJWTError as error:
        raise InvalidToken("malformed token") from error


def _decode(token: str, key, algorithms: list[str], settings: Settings) -> dict:
    return jwt.decode(
        token,
        key,
        algorithms=algorithms,
        audience=settings.supabase_jwt_audience,
        issuer=settings.jwt_issuer,
        options={"require": ["exp", "sub"]},
    )


def _verify_asymmetric(token: str, settings: Settings) -> dict:
    try:
        signing_key = _get_jwks_cache(settings).client().get_signing_key_from_jwt(token)
        return _decode(
            token,
            signing_key.key,
            ["ES256", "RS256", "PS256", "EdDSA"],
            settings,
        )
    except jwt.PyJWTError as error:
        raise InvalidToken(str(error)) from error
    except Exception as error:  # JWKS fetch failures
        logger.warning("jwks verification failed: %s", error)
        raise InvalidToken("could not verify token") from error


def _verify_symmetric(token: str, settings: Settings) -> dict:
    if not settings.supabase_jwt_secret:
        raise InvalidToken("HS256 token but no shared secret configured")
    try:
        return _decode(token, settings.supabase_jwt_secret, ["HS256"], settings)
    except jwt.PyJWTError as error:
        raise InvalidToken(str(error)) from error


def new_anonymous_token() -> str:
    """Opaque bearer credential. Only ever leaves the server in a cookie."""
    return secrets.token_urlsafe(_ANON_TOKEN_BYTES)


def hash_anonymous_token(token: str) -> str:
    """
    The database stores only this digest, so a dump cannot be replayed against
    the API. The token has full entropy, so a plain SHA-256 is sufficient — no
    password stretching is warranted.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
