"""Google sign-in and session JWTs.

The browser gets a Google ID token from Google Identity Services and posts it here. We verify it
against Google's public keys, check the email against `auth.invited.mail`, and issue our own JWT
(subject = email, lifetime = `auth.jwt.ttl_hours`) in an httpOnly cookie. The invite list is checked
again on every protected request, so removing an email from config.yaml takes effect immediately.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.config import Config

GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}

_google_keys = jwt.PyJWKClient(GOOGLE_CERTS_URL, cache_keys=True, lifespan=3600, timeout=10)


class AuthError(Exception):
    pass


def _verify_google(token: str, client_id: str) -> dict[str, Any]:
    signing_key = _google_keys.get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=client_id,
        options={"require": ["exp", "iat", "aud", "iss", "sub"]},
    )
    if claims.get("iss") not in GOOGLE_ISSUERS:
        raise AuthError("Token was not issued by Google.")
    if not claims.get("email") or not claims.get("email_verified"):
        raise AuthError("Your Google account email is not verified.")
    return claims


async def verify_google_id_token(token: str, config: Config) -> dict[str, Any]:
    if not config.auth.google.client_id:
        raise AuthError("Google sign-in is not configured.")
    try:
        return await asyncio.to_thread(_verify_google, token, config.auth.google.client_id)
    except jwt.PyJWTError as exc:
        raise AuthError(f"Google sign-in failed: {exc}") from exc


def issue_session(email: str, config: Config) -> tuple[str, datetime]:
    now = datetime.now(UTC)
    expires = now + timedelta(hours=config.auth.jwt.ttl_hours)
    payload = {"sub": email.lower(), "iat": now, "exp": expires, "typ": "session"}
    token = jwt.encode(payload, config.auth.jwt.secret, algorithm=config.auth.jwt.algorithm)
    return token, expires


def read_session(token: str, config: Config) -> str | None:
    try:
        payload = jwt.decode(
            token,
            config.auth.jwt.secret,
            algorithms=[config.auth.jwt.algorithm],
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError:
        return None
    if payload.get("typ") != "session":
        return None
    return str(payload["sub"])
