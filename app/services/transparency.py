"""Public description of how checks are made, built from config.yaml on every request.

Only explicitly listed, non-secret fields are copied out. Never pass whole config sections through:
they contain API keys, the JWT secret and account credentials.
"""

from __future__ import annotations

from typing import Any

from app.config import Config
from app.pipeline import prompts
from app.pipeline.orchestrator import PIPELINE_VERSION
from app.pipeline.search import plan

REASONING_LABEL = {"default": "the model's default", "none": "off"}


def _model(role: str, slug: str, step: str, receives: str, returns: str, reasoning: str = "") -> dict[str, str]:
    return {
        "role": role,
        "slug": slug,
        "url": f"https://openrouter.ai/{slug}" if slug else "",
        "step": step,
        "receives": receives,
        "returns": returns,
        "reasoning": reasoning,
    }


def _effort(value: str) -> str:
    return REASONING_LABEL.get(value, value)


def build(config: Config) -> dict[str, Any]:
    m = config.openrouter.models
    texts = prompts.get()
    p = config.pipeline
    stt = p.transcription.api == "stt"
    gate = config.topic_gate
    r = config.openrouter.reasoning
    models = [
        *([_model("gate", m.small, "Check the topic",
                  f"Only the reel's caption (up to {gate.max_caption_chars} characters) and our topic list",
                  "Whether the reel is about a topic we check, and which one", _effort(r.topic_gate))]
          if gate.enabled else []),
        _model("transcription", m.transcription, "Transcribe speech",
               "The reel's audio, in chunks of up to "
               f"{p.transcription.chunk_seconds} seconds",
               "A verbatim transcript in the language spoken"),
        _model("vision", m.vision if p.ocr.engine == "vision" else "", "Read on-screen text",
               f"Up to {p.ocr.max_frames} keyframes from the video",
               "The text visible on screen: captions, overlays, documents", _effort(r.ocr)),
        _model("small", m.small, "Clean up and extract claims",
               "The caption, transcript and on-screen text",
               "One clean text, then a list of separate, classified claims",
               f"cleanup {_effort(r.cleanup)}, claims {_effort(r.claims)}"),
        _model("strong", m.strong, "Decide verdicts",
               "One claim plus the evidence found for it, with each source's date, tier and rank",
               "A verdict, a short explanation, the sources it relies on and, if needed, follow-up searches",
               _effort(r.verdict)),
    ]
    if m.embedding:
        models.append(_model("embedding", m.embedding, "Match repeated claims",
                             "Each claim's text", "A vector used to find the same claim in other reels"))

    return {
        "pipeline_version": PIPELINE_VERSION,
        "prompt_version": texts.version,
        "provider": "OpenRouter",
        "models": models,
        "topic_gate": {
            "enabled": gate.enabled,
            "topics": list(config.topics),
            "empty_caption": gate.empty_caption,
            "remember_hours": gate.remember_hours,
        },
        "download": {
            "tools": list(config.downloader.order),
            "max_video_seconds": p.max_video_seconds,
            "max_video_mb": p.max_video_mb,
        },
        "extraction": {
            "frame_intervals": [{"up_to_seconds": r.max_seconds, "every_seconds": r.every} for r in p.frames.intervals],
            "max_frames": p.frames.max_frames,
            "ocr_engine": p.ocr.engine,
            "ocr_frames": p.ocr.max_frames,
            "transcription_api": p.transcription.api,
            "transcription_language": p.transcription.language or "auto-detect",
            "chunk_seconds": p.transcription.chunk_seconds,
            "max_claims_per_reel": p.max_claims_per_reel,
        },
        "verification": {
            # Order of the fallback chain, e.g. ["searxng:google", "searxng:duckduckgo", "serper", "selenium:bing"].
            "search_chain": [a.name for a in plan(config)],
            "results_per_query": config.search.results_per_query,
            "max_queries_per_claim": config.search.max_queries_per_claim,
            "factcheck_api_enabled": bool(config.factcheck.google_api_key),
            "official_sites": list(config.verification.official_sites),
            "factcheck_sites": list(config.verification.factcheck_sites),
            "min_independent_sources": config.verification.min_independent_sources,
            "max_evidence": config.verification.max_evidence,
            "research_rounds": config.verification.research.max_rounds,
            "follow_up_queries_per_round": config.verification.research.queries_per_round,
            "new_evidence_per_round": config.verification.research.new_evidence_per_round,
            "default_rank": config.verification.default_rank,
        },
        "ttl_hours": {
            "breaking": config.ttl.breaking_hours,
            "ongoing": config.ttl.ongoing_hours,
            "settled": config.ttl.settled_hours,
            "default": config.ttl.default_hours,
        },
        "retention": {
            "history_max_entries": config.history.max_entries,
            "history_keeps_raw_text": config.history.keep_raw_text,
            "jobs_days": config.retention.jobs_days,
            "requests_days": config.retention.requests_days,
        },
        "creators_min_sample": config.creators.min_sample,
        "hero_window_hours": config.hero.window_hours,
        "limits": {
            "submit": list(config.rate_limits.submit),
            "daily_check_cap": config.budget.daily_check_cap,
        },
        "prompts": [
            *([{"name": "Topic check", "text": texts.texts["topic_gate"]}] if gate.enabled else []),
            *([] if stt else [{"name": "Transcription", "text": texts.texts["transcribe"]}]),
            {"name": "On-screen text", "text": texts.texts["ocr"]},
            {"name": "Cleanup", "text": texts.texts["cleanup"]},
            {"name": "Claim extraction", "text": texts.texts["claims"]},
            {"name": "Verdict", "text": texts.texts["verdict"]},
            *([{"name": "Verdict: research note (rounds before the last)", "text": texts.texts["research_more"]},
               {"name": "Verdict: research note (last round)", "text": texts.texts["research_last"]}]
              if config.verification.research.max_rounds > 1 else []),
        ],
    }
