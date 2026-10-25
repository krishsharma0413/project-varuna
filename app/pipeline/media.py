"""FFmpeg/ffprobe helpers: probe, audio chunks for transcription, deduplicated frames for OCR."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path

import imagehash
from PIL import Image

from app.config import Config, FrameInterval


class MediaError(Exception):
    pass


@dataclass
class Probe:
    duration: float
    has_audio: bool
    has_video: bool


async def _run(*args: str) -> bytes:
    process = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise MediaError(f"{args[0]} failed: {stderr.decode(errors='replace')[-500:]}")
    return stdout


async def probe(video: Path) -> Probe:
    raw = await _run("ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(video))
    data = json.loads(raw)
    streams = data.get("streams", [])
    return Probe(
        duration=float(data.get("format", {}).get("duration") or 0),
        has_audio=any(s.get("codec_type") == "audio" for s in streams),
        has_video=any(s.get("codec_type") == "video" for s in streams),
    )


async def audio_chunks(video: Path, workdir: Path, chunk_seconds: int) -> list[Path]:
    out = workdir / "audio"
    out.mkdir(exist_ok=True)
    await _run(
        "ffmpeg", "-nostdin", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000",
        "-c:a", "libmp3lame", "-b:a", "48k", "-f", "segment", "-segment_time", str(chunk_seconds),
        str(out / "chunk_%03d.mp3"),
    )
    return sorted(out.glob("chunk_*.mp3"))


def frame_interval(duration: float, intervals: list[FrameInterval]) -> float:
    for row in sorted(intervals, key=lambda r: r.max_seconds):
        if duration <= row.max_seconds:
            return row.every
    return sorted(intervals, key=lambda r: r.max_seconds)[-1].every if intervals else 2.0


def _dedupe(paths: list[Path], max_distance: int) -> list[Path]:
    kept: list[Path] = []
    last_hash = None
    for path in paths:
        with Image.open(path) as image:
            current = imagehash.phash(image)
        if last_hash is None or current - last_hash > max_distance:
            kept.append(path)
            last_hash = current
    return kept


def evenly_spaced(items: list[Path], limit: int) -> list[Path]:
    if len(items) <= limit:
        return items
    step = len(items) / limit
    return [items[int(i * step)] for i in range(limit)]


async def frames(video: Path, workdir: Path, duration: float, config: Config) -> list[Path]:
    settings = config.pipeline.frames
    every = frame_interval(duration, settings.intervals)
    out = workdir / "frames"
    out.mkdir(exist_ok=True)
    await _run(
        "ffmpeg", "-nostdin", "-y", "-i", str(video),
        "-vf", f"fps=1/{every},scale={settings.width}:-2", "-q:v", "3",
        str(out / "f_%04d.jpg"),
    )
    extracted = sorted(out.glob("f_*.jpg"))
    unique = await asyncio.to_thread(_dedupe, extracted, settings.dedupe_distance)
    return evenly_spaced(unique, settings.max_frames)
