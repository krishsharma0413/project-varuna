"""Domain models shared by the API and the pipeline."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Verdict = Literal["true", "false", "misleading", "unverified", "outdated", "opinion"]
ClaimType = Literal["verifiable", "contested", "opinion", "prediction"]
Volatility = Literal["breaking", "ongoing", "settled"]
JobStatus = Literal["queued", "processing", "done", "failed", "rejected"]

VERDICTS: tuple[Verdict, ...] = ("true", "false", "misleading", "unverified", "outdated", "opinion")
# Most severe first; decides which claim headlines a reel.
SEVERITY: tuple[Verdict, ...] = ("false", "misleading", "outdated", "unverified", "true", "opinion")


class Source(BaseModel):
    url: str
    domain: str
    title: str = ""
    snippet: str = ""
    tier: int = Field(ge=1, le=3)
    kind: str = "other"   # primary | wire | outlet | factcheck | other
    rank: str = "D"
    found_via: str = ""
    stance: str = ""  # supports | contradicts | related (how it bears on the claim), "" if not assessed
    published: str = ""  # publication date as the search provider gave it, "" if unknown


class ClaimResult(BaseModel):
    claim_id: str
    text: str
    original: str = ""
    delivery: str = "literal"  # literal | sarcastic | hyperbole | quoted (how the video said it)
    type: ClaimType
    volatility: Volatility
    topic_tags: list[str] = []
    resolution_date: str | None = None
    verdict: Verdict
    explanation: str
    sources: list[Source] = []
    queries: list[str] = []      # every web search made for this claim, in order
    search_rounds: int = 0       # 1 = initial searches only; more when the model asked for follow-ups
    checked_at: datetime
    expires_at: datetime
    reused: bool = False


class Extraction(BaseModel):
    caption: str = ""
    transcript: str = ""
    ocr_text: str = ""
    cleaned_text: str = ""
    frames_used: int = 0


class Summary(BaseModel):
    verdict: Verdict
    claim_text: str
    counts: dict[str, int]
    claim_count: int


class CheckResult(BaseModel):
    checked_at: datetime
    expires_at: datetime
    claims: list[ClaimResult]
    summary: Summary | None
    inputs_used: list[str]
    extraction: Extraction
    pipeline_version: str
    models: dict[str, str]
    trace_id: str
    job_id: str
