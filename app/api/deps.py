"""Request dependencies: client IP, rate limits, signed-in user."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from ipaddress import ip_address, ip_network

from fastapi import Depends, HTTPException, Request

from app.auth import read_session
from app.clients import queue_redis
from app.config import Config, get_config
from app.log import log
from app.ratelimit import hit


def config_dep() -> Config:
    return get_config()


def client_ip(request: Request, config: Config) -> str:
    peer = request.client.host if request.client else "0.0.0.0"
    try:
        trusted = any(ip_address(peer) in ip_network(c) for c in config.network.trusted_proxy_cidrs)
    except ValueError:
        trusted = False
    if trusted:
        forwarded = request.headers.get(config.network.client_ip_header)
        if forwarded:
            return forwarded.split(",")[0].strip()
    return peer


async def _enforce(bucket: str, identity: str, rules: list[str]) -> None:
    try:
        retry_after = await hit(queue_redis(), bucket, identity, rules)
    except ValueError as exc:
        log.error("bad rate limit rule in config.yaml", bucket=bucket, error=str(exc))
        return
    except Exception as exc:  # Redis down: fail open rather than take the site down
        log.exception("rate limiter unavailable", exc)
        return
    if retry_after:
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )


def limit_ip(bucket: str) -> Callable[..., Awaitable[None]]:
    async def dependency(request: Request, config: Config = Depends(config_dep)) -> None:
        await _enforce(bucket, client_ip(request, config), getattr(config.rate_limits, bucket))

    return dependency


def session_email(request: Request, config: Config) -> str | None:
    token = request.cookies.get(config.auth.jwt.cookie_name)
    if not token:
        header = request.headers.get("authorization", "")
        if header.lower().startswith("bearer "):
            token = header[7:].strip()
    return read_session(token, config) if token else None


async def optional_user(request: Request, config: Config = Depends(config_dep)) -> str | None:
    return session_email(request, config)


async def invited_user(request: Request, config: Config = Depends(config_dep)) -> str:
    email = session_email(request, config)
    if not email:
        raise HTTPException(status_code=401, detail="Sign in with Google to submit a reel.")
    if not config.is_invited_email(email):
        raise HTTPException(status_code=403, detail="Your email isn't on the invite list yet.")
    return email


async def limit_submitter(email: str = Depends(invited_user), config: Config = Depends(config_dep)) -> str:
    await _enforce("submit", email, config.rate_limits.submit)
    return email
