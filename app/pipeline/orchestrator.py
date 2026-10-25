"""Runs one job end to end:
details → topic check → download → extract → transcribe/read screen → cleanup → claims → verify → store.

The topic check comes before anything expensive: an off-topic reel stops after one small model call
on its caption, and its daily-budget slot is given back.
"""

from __future__ import annotations

import asyncio
import contextlib
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.cache import invalidate
from app.clients import JOBS, mongo, queue_redis
from app.config import Config, get_config
from app.locks import acquire, extend, owner, release
from app.log import log
from app.models import CheckResult, Extraction
from app.pipeline import claims as claim_step
from app.pipeline import extract, media, prompts, topic_gate
from app.pipeline.download import PermanentError, download_video, fetch_info
from app.pipeline.llm import embed
from app.pipeline.verify import verify_claim
from app.queue import schedule
from app.services.history import summarize
from app.services.reels import save_embedding, save_gate, store_result
from app.services.submissions import permalink, refund_budget
from app.trace import trace_id_var

PIPELINE_VERSION = "0.2.0"


class TopicRejected(Exception):
    """The reel isn't about a topic we check. Not an error: the job ends as `rejected`."""


async def _job_update(job_id: str, **fields: Any) -> None:
    fields["updated_at"] = datetime.now(UTC)
    await mongo()[JOBS].update_one({"_id": job_id}, {"$set": fields})


async def _step(job_id: str, step: str) -> None:
    log.info("step started", step=step)
    await _job_update(job_id, status="processing", step=step)


async def run_pipeline(job_id: str, reel_id: str, config: Config) -> None:
    workdir = Path(config.pipeline.work_dir) / job_id
    try:
        await _step(job_id, "metadata")
        reel = await fetch_info(reel_id, config)

        await _step(job_id, "topic_check")
        decision = await topic_gate.check(reel.caption, config)
        await save_gate(reel_id, decision.model_dump(), topic_gate.topics_hash(config.topics),
                        caption=reel.caption, creator_handle=reel.owner)
        log.info("topic check", relevant=decision.relevant, topics=",".join(decision.matched_topics))
        if not decision.relevant:
            raise TopicRejected(decision.reason)

        await _step(job_id, "download")
        video = await download_video(reel_id, reel, workdir, config)

        await _step(job_id, "extract")
        info = await media.probe(video)
        if not info.has_video:
            raise PermanentError("The downloaded file has no video stream.")
        if info.duration > config.pipeline.max_video_seconds:
            raise PermanentError(f"The reel is longer than {config.pipeline.max_video_seconds} seconds.")
        chunks = (
            await media.audio_chunks(video, workdir, config.pipeline.transcription.chunk_seconds)
            if info.has_audio else []
        )
        frames = await media.frames(video, workdir, info.duration, config)

        await _step(job_id, "transcribe")
        transcript, ocr_text = await asyncio.gather(
            extract.transcribe(chunks, config), extract.read_screen_text(frames, config)
        )

        await _step(job_id, "cleanup")
        cleaned = await claim_step.cleanup(reel.caption, transcript, ocr_text, config)

        await _step(job_id, "claims")
        extracted = await claim_step.extract_claims(cleaned, config)
        log.info("claims extracted", count=len(extracted))

        await _step(job_id, "verify")
        results = []
        for claim in extracted:
            results.append(await verify_claim(claim, cleaned, config))
            if config.openrouter.models.embedding:
                await _embed(results[-1].claim_id, claim.text, config)

        await _step(job_id, "store")
        now = datetime.now(UTC)
        inputs = [name for name, value in
                  (("caption", reel.caption), ("transcript", transcript), ("on-screen text", ocr_text))
                  if value]
        inputs.append(f"frames:{len(frames)}")
        result = CheckResult(
            checked_at=now,
            expires_at=min((r.expires_at for r in results),
                           default=now + _hours(config.ttl.default_hours)),
            claims=results,
            summary=summarize(results),
            inputs_used=inputs,
            extraction=Extraction(caption=reel.caption, transcript=transcript, ocr_text=ocr_text,
                                  cleaned_text=cleaned, frames_used=len(frames)),
            pipeline_version=PIPELINE_VERSION,
            models={
                "small": config.openrouter.models.small,
                "strong": config.openrouter.models.strong,
                "transcription": config.openrouter.models.transcription,
                "transcription_api": config.pipeline.transcription.api,
                "vision": config.openrouter.models.vision,
                "prompts": prompts.version(),
                "reasoning": ",".join(f"{k}={v}" for k, v in config.openrouter.reasoning.model_dump().items()),
                "downloader": reel.source,
            },
            trace_id=trace_id_var.get(),
            job_id=job_id,
        )
        await store_result(
            reel_id, permalink=permalink(reel_id), creator_handle=reel.owner,
            caption=reel.caption, duration_s=info.duration or reel.duration,
            result=result, config=config,
        )
        await invalidate()
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _hours(hours: float) -> timedelta:
    return timedelta(hours=hours)


async def _keep_lock(reel_id: str, job_id: str, ttl: int) -> None:
    """Re-extend the reel's lock while the pipeline runs, so a long run doesn't let a second check start."""
    while True:
        await asyncio.sleep(max(1, ttl // 3))
        try:
            await extend(queue_redis(), reel_id, job_id, ttl)
        except Exception as exc:
            log.exception("could not extend the reel lock", exc, reel_id=reel_id)


async def _embed(claim_id: str, text: str, config: Config) -> None:
    try:
        await save_embedding(claim_id, await embed(config.openrouter.models.embedding, text))
    except Exception as exc:
        log.exception("embedding failed", exc, claim_id=claim_id)


async def handle_job(payload: dict[str, Any]) -> None:
    """Queue handler. Retries transient failures with backoff; permanent ones fail the job at once."""
    token = trace_id_var.set(payload.get("trace_id") or "-")
    job_id, reel_id = payload["job_id"], payload["reel_id"]
    attempt = int(payload.get("attempt", 0))
    config = get_config()
    redis = queue_redis()
    try:
        # Hold the reel's lock for this run. A job resumed after a restart may find its lock expired
        # (take it back) or taken by a newer check of the same reel (step aside, no duplicate run).
        holder = await owner(redis, reel_id)
        if holder not in (None, job_id):
            log.info("job superseded by a newer check of the same reel", job_id=job_id, newer=holder)
            await _job_update(job_id, status="failed", step="failed", finished_at=datetime.now(UTC),
                              error="Superseded by a newer check of the same reel.")
            return
        if holder is None and not await acquire(redis, reel_id, job_id, config.pipeline.lock_ttl_seconds):
            log.info("job superseded by a newer check of the same reel", job_id=job_id)
            await _job_update(job_id, status="failed", step="failed", finished_at=datetime.now(UTC),
                              error="Superseded by a newer check of the same reel.")
            return
        await extend(redis, reel_id, job_id, config.pipeline.lock_ttl_seconds)
        log.info("job started", job_id=job_id, reel_id=reel_id, attempt=attempt)
        await _job_update(job_id, attempts=attempt + 1)
        keeper = asyncio.create_task(_keep_lock(reel_id, job_id, config.pipeline.lock_ttl_seconds))
        try:
            await run_pipeline(job_id, reel_id, config)
        finally:
            keeper.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await keeper
        await _job_update(job_id, status="done", step="done", error=None, finished_at=datetime.now(UTC))
        log.info("job done", job_id=job_id)
        await release(redis, reel_id, job_id)
    except TopicRejected as exc:
        log.info("job rejected by the topic check", job_id=job_id, reason=str(exc))
        await _job_update(job_id, status="rejected", step="rejected", error=str(exc), finished_at=datetime.now(UTC))
        await refund_budget(payload.get("budget_key"))
        await release(redis, reel_id, job_id)
    except PermanentError as exc:
        log.info("job failed permanently", job_id=job_id, reason=str(exc))
        await _job_update(job_id, status="failed", step="failed", error=str(exc), finished_at=datetime.now(UTC))
        await release(redis, reel_id, job_id)
    except Exception as exc:
        log.exception("job attempt failed", exc, job_id=job_id, attempt=attempt)
        if attempt < config.worker.max_retries:
            backoff = config.worker.retry_backoff_seconds or [30]
            delay = backoff[min(attempt, len(backoff) - 1)]
            await _job_update(job_id, status="queued", step="retrying",
                              error=f"Attempt {attempt + 1} failed, retrying in {delay}s.")
            await extend(redis, reel_id, job_id, config.pipeline.lock_ttl_seconds + delay)
            await schedule(redis, {**payload, "attempt": attempt + 1}, delay)
        else:
            await _job_update(job_id, status="failed", step="failed",
                              error="The check could not be completed. Please try again later.",
                              finished_at=datetime.now(UTC))
            await release(redis, reel_id, job_id)
    finally:
        trace_id_var.reset(token)
