"""Speech transcription and on-screen text via OpenRouter models (base64 audio and images)."""

from __future__ import annotations

import base64
from pathlib import Path

from app.config import Config
from app.log import log
from app.pipeline import llm, prompts
from app.pipeline.media import evenly_spaced


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


async def transcribe(chunks: list[Path], config: Config) -> str:
    """Speech to text, one audio chunk at a time.

    api "stt": OpenRouter's /audio/transcriptions endpoint with a speech model such as Whisper.
    api "chat": an audio-capable chat model, given the audio plus the TRANSCRIBE prompt.
    """
    settings = config.pipeline.transcription
    model = config.openrouter.models.transcription
    parts: list[str] = []
    for index, chunk in enumerate(chunks):
        if settings.api == "stt":
            text, usage = await llm.speech_to_text(model, _b64(chunk), "mp3", settings.language)
            log.debug("transcribed audio chunk", index=index, chars=len(text),
                      seconds=usage.get("seconds"), cost_usd=usage.get("cost"))
        else:
            text = await llm.chat(
                model,
                [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompts.render("transcribe")},
                        {"type": "input_audio", "input_audio": {"data": _b64(chunk), "format": "mp3"}},
                    ],
                }],
                temperature=0,
                reasoning=config.openrouter.reasoning.transcription,
            )
            log.debug("transcribed audio chunk", index=index, chars=len(text))
        parts.append(text.strip())
    return "\n".join(p for p in parts if p)


async def read_screen_text(frames: list[Path], config: Config) -> str:
    if config.pipeline.ocr.engine == "none" or not frames:
        return ""
    selected = evenly_spaced(frames, config.pipeline.ocr.max_frames)
    content: list[dict[str, object]] = [{"type": "text", "text": prompts.render("ocr")}]
    for frame in selected:
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_b64(frame)}"}})
    text = await llm.chat(config.openrouter.models.vision, [{"role": "user", "content": content}], temperature=0,
                          reasoning=config.openrouter.reasoning.ocr)
    log.debug("read on-screen text", frames=len(selected), chars=len(text))
    return text.strip()
