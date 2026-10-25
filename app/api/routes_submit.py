"""Submitting reels (invited users only), job status, disputes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.deps import client_ip, config_dep, limit_ip, limit_submitter
from app.clients import DISPUTES, mongo
from app.config import Config
from app.log import log
from app.services import submissions
from app.services.submissions import BudgetExceeded, parse_reel_url
from app.trace import trace_id_var

router = APIRouter(prefix="/api/v1")


class Submission(BaseModel):
    reel_url: str = Field(min_length=10, max_length=300)


@router.post("/submissions", status_code=202)
async def submit(
    body: Submission, email: str = Depends(limit_submitter), config: Config = Depends(config_dep)
) -> Any:
    reel_id = parse_reel_url(body.reel_url)
    if not reel_id:
        raise HTTPException(status_code=422, detail="That doesn't look like an Instagram reel link.")
    try:
        return await submissions.submit(reel_id, email, config)
    except BudgetExceeded as exc:
        raise HTTPException(
            status_code=429, detail="Today's check limit has been reached. Please try again tomorrow."
        ) from exc


@router.get("/jobs/{job_id}", dependencies=[Depends(limit_ip("jobs"))])
async def job(job_id: str) -> Any:
    result = await submissions.get_job(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Job not found.")
    return result


class Dispute(BaseModel):
    reel_id: str = Field(min_length=5, max_length=40)
    claim_id: str | None = Field(None, max_length=80)
    message: str = Field(min_length=10, max_length=4000)
    contact: str | None = Field(None, max_length=200)


@router.post("/disputes", status_code=201, dependencies=[Depends(limit_ip("dispute"))])
async def dispute(body: Dispute, request: Request, config: Config = Depends(config_dep)) -> Any:
    dispute_id = uuid.uuid4().hex
    await mongo()[DISPUTES].insert_one(
        {
            "_id": dispute_id,
            **body.model_dump(),
            "status": "open",
            "ip": client_ip(request, config),
            "trace_id": trace_id_var.get(),
            "created_at": datetime.now(UTC),
        }
    )
    log.info("dispute received", reel_id=body.reel_id, dispute_id=dispute_id)
    return {"dispute_id": dispute_id}
