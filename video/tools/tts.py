"""Render each voice-over line with edge-tts, trim silence, and write durations + word timings to src/vo.json."""

import asyncio
import json
import subprocess
import sys
import wave
from pathlib import Path

import edge_tts
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "public" / "audio"
FFMPEG = ROOT / "node_modules" / "@remotion" / "compositor-win32-x64-msvc" / "ffmpeg.exe"
SR = 48000

VOICE = sys.argv[1] if len(sys.argv) > 1 else "en-IN-PrabhatNeural"
RATE = "+14%"
PITCH = "-6Hz"

LINES = {
    "q1": "But wait, should you believe everything you watch?",
    "room": "Was any of it true?",
    "creators": "Creators may be paid, or not. They can be right, or misleading.",
    "still": "So, should you still believe everything you see?",
    "turn": "Why not fact-check it with Varuna, once?",
    "paste": "Paste any reel link.",
    "pipeline": "It listens, splits every claim, checks ranked sources, and shows you the receipts.",
    "invite": "Invite only, for now. DM us for access.",
    "outro": "Before you forward it, Varuna it.",
}


def trim(src: Path, dst: Path) -> float:
    """Decode to 48 kHz mono WAV and strip leading/trailing silence. Returns seconds cut from the start."""
    subprocess.run(
        [str(FFMPEG), "-y", "-v", "error", "-i", str(src), "-ac", "1", "-ar", str(SR), str(dst)], check=True
    )
    with wave.open(str(dst)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    loud = np.flatnonzero(np.abs(x) > 32768 * 10 ** (-42 / 20))
    pad = int(0.03 * SR)
    start = max(loud[0] - pad, 0)
    x = x[start: loud[-1] + pad]
    with wave.open(str(dst), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(x.tobytes())
    return start / SR


async def render(key: str, text: str) -> dict:
    raw = OUT / f"raw_{key}.mp3"
    words = []
    comm = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH, boundary="WordBoundary")
    with raw.open("wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append({"w": chunk["text"], "t": chunk["offset"] / 1e7, "d": chunk["duration"] / 1e7})
    path = OUT / f"vo_{key}.wav"
    lead = trim(raw, path)
    raw.unlink()
    with wave.open(str(path)) as w:
        dur = w.getnframes() / w.getframerate()
    for word in words:
        word["t"] = round(max(word["t"] - lead, 0), 3)
        word["d"] = round(word["d"], 3)
    return {"text": text, "dur": round(dur, 3), "words": words}


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    out = {}
    for key, text in LINES.items():
        out[key] = await render(key, text)
        print(f"{key:10s} {out[key]['dur']:5.2f}s  {text}")
    print(f"total VO {sum(v['dur'] for v in out.values()):.2f}s")
    (ROOT / "src" / "vo.json").write_text(json.dumps(out, indent=2))


asyncio.run(main())
