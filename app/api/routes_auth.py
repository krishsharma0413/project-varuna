"""Google sign-in → session cookie."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.api.deps import config_dep, limit_ip, session_email
from app.auth import AuthError, issue_session, verify_google_id_token
from app.config import Config
from app.log import log

router = APIRouter(prefix="/api/v1/auth", dependencies=[Depends(limit_ip("auth"))])


class GoogleLogin(BaseModel):
    credential: str = Field(min_length=20, max_length=4096)


@router.post("/google")
async def google_login(body: GoogleLogin, response: Response, config: Config = Depends(config_dep)) -> Any:
    try:
        claims = await verify_google_id_token(body.credential, config)
    except AuthError as exc:
        log.info("google sign-in rejected", reason=str(exc))
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    email = str(claims["email"]).lower()
    if not config.is_invited_email(email):
        log.info("sign-in from email not on the invite list")
        raise HTTPException(status_code=403, detail="Your email isn't on the invite list yet.")
    token, expires = issue_session(email, config)
    response.set_cookie(
        config.auth.jwt.cookie_name,
        token,
        max_age=int(config.auth.jwt.ttl_hours * 3600),
        httponly=True,
        secure=config.auth.jwt.cookie_secure,
        samesite="lax",
        path="/",
    )
    log.info("signed in")
    return {"email": email, "name": claims.get("name"), "picture": claims.get("picture"), "expires_at": expires}


@router.get("/me")
async def me(request: Request, config: Config = Depends(config_dep)) -> Any:
    email = session_email(request, config)
    return {
        "email": email,
        "invited": bool(email) and config.is_invited_email(email or ""),
        "is_admin": bool(email) and config.is_admin(email or ""),
    }


@router.post("/logout")
async def logout(response: Response, config: Config = Depends(config_dep)) -> Any:
    response.delete_cookie(config.auth.jwt.cookie_name, path="/")
    return {"ok": True}
