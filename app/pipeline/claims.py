"""Cleanup and claim extraction."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.config import Config
from app.pipeline import llm, prompts


class ExtractedClaim(BaseModel):
    text: str
    original: str = ""
    delivery: Literal["literal", "sarcastic", "hyperbole", "quoted"] = "literal"
    type: Literal["verifiable", "contested", "opinion", "prediction"]
    volatility: Literal["breaking", "ongoing", "settled"] = "ongoing"
    topic_tags: list[str] = Field(default_factory=list)
    resolution_date: str | None = None
    search_queries: list[str] = Field(default_factory=list)


class ClaimList(BaseModel):
    claims: list[ExtractedClaim]


def normalize(text: str) -> str:
    text = re.sub(r"[^\w\s]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def claim_id(text: str) -> str:
    return "clm_" + hashlib.sha256(normalize(text).encode()).hexdigest()[:24]


async def cleanup(caption: str, transcript: str, ocr_text: str, config: Config) -> str:
    if not (caption or transcript or ocr_text):
        return ""
    prompt = prompts.render(
        "cleanup",
        caption=caption or "(none)", transcript=transcript or "(none)", ocr=ocr_text or "(none)"
    )
    return (await llm.chat(config.openrouter.models.small, [{"role": "user", "content": prompt}],
                           reasoning=config.openrouter.reasoning.cleanup)).strip()


async def extract_claims(text: str, config: Config) -> list[ExtractedClaim]:
    if not text.strip():
        return []
    prompt = prompts.render(
        "claims",
        today=datetime.now(UTC).date().isoformat(),
        max_claims=config.pipeline.max_claims_per_reel,
        topics=", ".join(config.topics) or "(none)",
        text=text[:20_000],
    )
    result = await llm.chat_json(config.openrouter.models.small, [{"role": "user", "content": prompt}], ClaimList,
                                  reasoning=config.openrouter.reasoning.claims)
    seen: set[str] = set()
    unique: list[ExtractedClaim] = []
    for claim in result.claims:
        key = claim_id(claim.text)
        if claim.text.strip() and key not in seen:
            seen.add(key)
            unique.append(claim)
    return unique[: config.pipeline.max_claims_per_reel]
