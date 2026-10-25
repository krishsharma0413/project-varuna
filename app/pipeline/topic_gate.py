"""Topic gate: decide from the caption alone whether a reel is about a topic we check.

Runs before the video is downloaded, transcribed or searched, so off-topic content costs one small
model call on a short text and nothing else.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from app.config import Config
from app.pipeline import llm, prompts

# Bump when the gate's behaviour changes, so remembered rejections are re-evaluated.
GATE_VERSION = "3"
DEFAULT_REJECTION = "The caption doesn't match any topic we check."


class GateDecision(BaseModel):
    relevant: bool
    matched_topics: list[str] = Field(default_factory=list)
    reason: str = Field(min_length=1, description="One short, neutral sentence explaining the decision.")


def topics_hash(topics: list[str]) -> str:
    """Changes whenever the topic list (order and case don't matter) or the gate version changes."""
    normalized = sorted({t.strip().lower() for t in topics if t.strip()})
    return hashlib.sha256("\n".join([f"gate:{GATE_VERSION}", *normalized]).encode()).hexdigest()[:16]


def match_topics(claimed: list[str], topics: list[str]) -> list[str]:
    """Map the model's topic names onto the configured ones (exact, then containment, case-insensitive)."""
    matched: list[str] = []
    for topic in topics:
        t = topic.strip().lower()
        for name in claimed:
            n = name.strip().lower()
            if n and (n == t or n in t or t in n):
                matched.append(topic)
                break
    return matched


def is_remembered_rejection(gate: dict[str, Any] | None, config: Config, now: datetime) -> bool:
    """A recent rejection for the same topic list can be reused without calling the model again."""
    if not gate or gate.get("relevant") or not config.topic_gate.enabled:
        return False
    if gate.get("topics_hash") != topics_hash(config.topics):
        return False
    checked_at = gate.get("checked_at")
    return bool(checked_at and checked_at > now - timedelta(hours=config.topic_gate.remember_hours))


async def check(caption: str, config: Config) -> GateDecision:
    settings = config.topic_gate
    if not settings.enabled:
        return GateDecision(relevant=True, reason="The topic check is switched off.")
    if not config.topics:
        return GateDecision(relevant=True, reason="No topics are configured, so every reel is checked.")
    text = caption.strip()
    if not text:
        if settings.empty_caption == "allow":
            return GateDecision(relevant=True, reason="The reel has no caption; checked anyway.")
        return GateDecision(
            relevant=False,
            reason="The reel has no caption, so we can't tell whether it's about a topic we check.",
        )
    prompt = prompts.render(
        "topic_gate",
        topics="\n".join(f"- {t}" for t in config.topics),
        caption=text[: settings.max_caption_chars],
    )
    decision = await llm.chat_json(
        config.openrouter.models.small, [{"role": "user", "content": prompt}], GateDecision, temperature=0,
        reasoning=config.openrouter.reasoning.topic_gate,
    )
    decision.matched_topics = match_topics(decision.matched_topics, config.topics)
    if decision.relevant and not decision.matched_topics:
        return GateDecision(relevant=False, reason=DEFAULT_REJECTION)
    if not decision.relevant:
        decision.matched_topics = []
        decision.reason = decision.reason.strip() or DEFAULT_REJECTION
    return decision
