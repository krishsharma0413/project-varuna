"""Reel details and video: instaloader first, yt-dlp as fallback (order in config.yaml).

Two steps so the topic gate can run in between: `fetch_info` reads the caption, creator and length
without downloading the video; `download_video` fetches the video only once the reel has passed.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from app.config import Config
from app.log import log


class PermanentError(Exception):
    """A failure retrying won't fix (not a video, too long, private...). Shown to the user."""


class DownloadError(Exception):
    pass


@dataclass
class ReelInfo:
    caption: str
    owner: str
    duration: float | None
    source: str              # downloader that answered
    video_url: str | None    # direct video URL when the downloader provides one


def _reel_url(shortcode: str) -> str:
    return f"https://www.instagram.com/reel/{shortcode}/"


def _check_duration(duration: float | None, config: Config) -> None:
    if duration and duration > config.pipeline.max_video_seconds:
        raise PermanentError(f"The reel is longer than {config.pipeline.max_video_seconds} seconds.")


# ---------- instaloader ----------

# After Instagram rejects a login, don't try again for a while: repeated failed logins get accounts locked.
_login_paused_until = 0.0


def _login(loader: Any, session_file: Path, config: Config) -> None:
    global _login_paused_until
    settings = config.downloader.instaloader
    if time.monotonic() < _login_paused_until:
        minutes = round((_login_paused_until - time.monotonic()) / 60)
        raise DownloadError(f"instaloader login paused for {minutes} more minutes after Instagram rejected it")
    try:
        loader.login(settings.username, settings.password)
    except Exception:
        _login_paused_until = time.monotonic() + settings.login_cooldown_minutes * 60
        log.error("Instagram rejected the instaloader login; pausing logins",
                  minutes=settings.login_cooldown_minutes)
        raise
    loader.save_session_to_file(str(session_file))


def _instaloader_post(shortcode: str, config: Config) -> Any:
    import instaloader

    loader = instaloader.Instaloader(
        download_pictures=False, download_video_thumbnails=False, download_geotags=False,
        download_comments=False, save_metadata=False, compress_json=False, quiet=True,
        max_connection_attempts=1, request_timeout=config.downloader.timeout_seconds,
    )
    settings = config.downloader.instaloader
    session_file: Path | None = None
    if settings.username:
        session_file = Path(settings.session_dir) / f"session-{settings.username}"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        if session_file.is_file():
            loader.load_session_from_file(settings.username, str(session_file))
        else:
            _login(loader, session_file, config)
    try:
        return instaloader.Post.from_shortcode(loader.context, shortcode)
    except instaloader.exceptions.LoginRequiredException:
        if not settings.username or session_file is None:
            raise
        # Saved session expired: log in again once.
        session_file.unlink(missing_ok=True)
        _login(loader, session_file, config)
        return instaloader.Post.from_shortcode(loader.context, shortcode)


def _info_instaloader(shortcode: str, config: Config) -> ReelInfo:
    post = _instaloader_post(shortcode, config)
    if not post.is_video or not post.video_url:
        raise PermanentError("This post has no video to check.")
    duration = float(post.video_duration) if post.video_duration else None
    _check_duration(duration, config)
    return ReelInfo(post.caption or "", (post.owner_username or "").lower(), duration, "instaloader", post.video_url)


def _stream_to_file(url: str, target: Path, max_bytes: int, timeout: float) -> None:
    written = 0
    with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as response:
        response.raise_for_status()
        with target.open("wb") as fh:
            for chunk in response.iter_bytes(1 << 16):
                written += len(chunk)
                if written > max_bytes:
                    raise PermanentError("The reel's video file is larger than the configured limit.")
                fh.write(chunk)


def _video_instaloader(shortcode: str, info: ReelInfo, workdir: Path, config: Config) -> Path:
    url = info.video_url if info.source == "instaloader" and info.video_url else None
    if url is None:
        url = _info_instaloader(shortcode, config).video_url
    target = workdir / "video.mp4"
    _stream_to_file(str(url), target, config.pipeline.max_video_mb * 1024 * 1024,
                    config.downloader.timeout_seconds * 2)
    return target


# ---------- yt-dlp ----------

class _SilentYtdlpLogger:
    """yt-dlp prints errors to stderr itself; we already raise and log them."""

    def debug(self, msg: str) -> None: ...
    def info(self, msg: str) -> None: ...
    def warning(self, msg: str) -> None: ...
    def error(self, msg: str) -> None: ...


def _ytdlp_options(workdir: Path | None, config: Config) -> dict[str, object]:
    options: dict[str, object] = {
        "logger": _SilentYtdlpLogger(),
        "format": "best[ext=mp4]/best",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "max_filesize": config.pipeline.max_video_mb * 1024 * 1024,
        "socket_timeout": config.downloader.timeout_seconds,
    }
    if workdir is not None:
        options["outtmpl"] = str(workdir / "video.%(ext)s")
    if config.downloader.yt_dlp.cookies_file:
        options["cookiefile"] = config.downloader.yt_dlp.cookies_file
    return options


def _info_ytdlp(shortcode: str, config: Config) -> ReelInfo:
    import yt_dlp

    with yt_dlp.YoutubeDL(_ytdlp_options(None, config)) as ydl:
        info = ydl.extract_info(_reel_url(shortcode), download=False)
    duration = float(info["duration"]) if info.get("duration") else None
    _check_duration(duration, config)
    return ReelInfo(info.get("description") or "", ytdlp_handle(info), duration, "yt-dlp", None)


def ytdlp_handle(info: dict[str, Any]) -> str:
    """Instagram username from yt-dlp metadata. `uploader_id` is the numeric account ID and `uploader`
    the display name, so prefer `channel` (the username) and never store a bare number as a handle."""
    for key in ("channel", "uploader_id"):
        value = str(info.get(key) or "").strip().lstrip("@").lower()
        if value and not value.isdigit():
            return value
    return ""


def _video_ytdlp(shortcode: str, info: ReelInfo, workdir: Path, config: Config) -> Path:
    import yt_dlp

    with yt_dlp.YoutubeDL(_ytdlp_options(workdir, config)) as ydl:
        result = ydl.extract_info(_reel_url(shortcode), download=True)
    downloads = result.get("requested_downloads") or []
    video = Path(downloads[0]["filepath"]) if downloads else next(workdir.glob("video.*"), None)
    if not video or not video.is_file():
        raise DownloadError("yt-dlp finished without producing a video file.")
    return video


_INFO = {"instaloader": _info_instaloader, "yt-dlp": _info_ytdlp}
_VIDEO = {"instaloader": _video_instaloader, "yt-dlp": _video_ytdlp}


async def fetch_info(shortcode: str, config: Config) -> ReelInfo:
    errors: list[str] = []
    for name in config.downloader.order:
        try:
            info = await asyncio.to_thread(_INFO[name], shortcode, config)
            log.info("reel details fetched", downloader=name, reel_id=shortcode, caption_chars=len(info.caption))
            return info
        except PermanentError:
            raise
        except Exception as exc:
            log.exception("could not fetch reel details", exc, downloader=name, reel_id=shortcode)
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
    raise DownloadError("Could not read the reel. " + " | ".join(errors))


async def download_video(shortcode: str, info: ReelInfo, workdir: Path, config: Config) -> Path:
    """Video download, starting with the downloader that provided the details."""
    await asyncio.to_thread(workdir.mkdir, parents=True, exist_ok=True)
    order = [info.source, *(n for n in config.downloader.order if n != info.source)]
    errors: list[str] = []
    for name in order:
        try:
            video = await asyncio.to_thread(_VIDEO[name], shortcode, info, workdir, config)
            log.info("reel downloaded", downloader=name, reel_id=shortcode)
            return video
        except PermanentError:
            raise
        except Exception as exc:
            log.exception("video download failed", exc, downloader=name, reel_id=shortcode)
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
    raise DownloadError("Could not download the reel. " + " | ".join(errors))
