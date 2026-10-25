"""Build the reel timeline from the voice-over timings.

Writes src/timeline.json, which is the single source of truth for both the Remotion scenes
(visual cues) and tools/mix.py (where voice lines and sound effects land).
All times are in seconds from the start of the reel.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VO = json.loads((ROOT / "src" / "vo.json").read_text())

FPS = 30
HOOK = 3.6
# Snap points in the hook feed: post n is replaced by post n+1 at these times; free-scroll starts at the last.
HOOK_SNAPS = [0.72, 1.36, 1.88, 2.32]

scenes: dict[str, list[float]] = {}
vo_start: dict[str, float] = {}


def words(key: str) -> dict[str, list[float]]:
    """Absolute start time of every spoken word, keyed by lower-case word (repeats become lists)."""
    out: dict[str, list[float]] = {}
    for w in VO[key]["words"]:
        out.setdefault(w["w"].lower().strip(",.?"), []).append(round(vo_start[key] + w["t"], 3))
    return out


def vo_end(key: str) -> float:
    return vo_start[key] + VO[key]["dur"]


t = 0.0
scenes["hook"] = [0.0, HOOK]
t = HOOK

# 2. the question
vo_start["q1"] = t + 0.3
scenes["question"] = [t, vo_end("q1") + 0.25]
t = scenes["question"][1]

# 3. dark room: bulb clicks on, then the line
vo_start["room"] = t + 0.4
scenes["room"] = [t, vo_end("room") + 0.15]
t = scenes["room"][1]

# 4. creators, stamped on the desk
vo_start["creators"] = t + 0.1
scenes["creators"] = [t, vo_end("creators") + 0.25]
t = scenes["creators"][1]

# 5. callback question
vo_start["still"] = t + 0.1
scenes["still"] = [t, vo_end("still") + 0.35]
t = scenes["still"][1]

# 6. the turn: flash + wordmark
vo_start["turn"] = t + 0.3
scenes["turn"] = [t, vo_end("turn") + 0.3]
t = scenes["turn"][1]

# 7. paste a link
vo_start["paste"] = t + 0.2
scenes["paste"] = [t, t + 1.75]
t = scenes["paste"][1]

# 8 + 9. pipeline cards, then receipts from the word "and"
vo_start["pipeline"] = t + 0.05
pw = words("pipeline")
scenes["pipeline"] = [t, pw["and"][0] - 0.05]
scenes["receipts"] = [scenes["pipeline"][1], vo_end("pipeline") + 1.1]
t = scenes["receipts"][1]

# 10. invite-only end card, then the sign-off line
vo_start["invite"] = t + 0.25
vo_start["outro"] = vo_end("invite") + 0.1
scenes["end"] = [t, vo_end("outro") + 0.8]
t = scenes["end"][1]

TOTAL = round(t, 3)
w = {k: words(k) for k in VO}

cues = {
    "hook.snaps": HOOK_SNAPS,
    "q1.words": [round(vo_start["q1"] + x["t"], 3) for x in VO["q1"]["words"]],
    "room.click": scenes["room"][0] + 0.08,
    "creators.stamps": [w["creators"]["paid"][0], w["creators"]["not"][0], w["creators"]["right"][0],
                        w["creators"]["misleading"][0]],
    "still.words": [round(vo_start["still"] + x["t"], 3) for x in VO["still"]["words"]],
    "turn.flash": scenes["turn"][0],
    "turn.words": [round(vo_start["turn"] + x["t"], 3) for x in VO["turn"]["words"]],
    "turn.wordmark": w["turn"]["varuna"][0],
    "paste.paste": scenes["paste"][0] + 0.45,
    "paste.press": scenes["paste"][0] + 1.0,
    "pipeline.cards": [w["pipeline"]["listens"][0], w["pipeline"]["splits"][0], w["pipeline"]["checks"][0],
                       round((w["pipeline"]["sources"][0] + w["pipeline"]["and"][0]) / 2, 3)],
    "receipts.stamp": w["pipeline"]["receipts"][0] + 0.05,
    "receipts.rows": [round(w["pipeline"]["receipts"][0] + 0.55 + i * 0.13, 3) for i in range(6)],
    "end.ticket": scenes["end"][0] + 0.1,
    "end.dm": w["invite"]["dm"][0],
    "end.forward": w["outro"]["before"][0],
    "end.varuna": w["outro"]["varuna"][0],
}

out = {
    "fps": FPS,
    "total": TOTAL,
    "frames": round(TOTAL * FPS),
    "scenes": {k: [round(a, 3), round(b, 3)] for k, (a, b) in scenes.items()},
    "vo": {k: {"start": round(vo_start[k], 3), "dur": VO[k]["dur"]} for k in VO},
    "words": {k: [{"w": x["w"], "t": round(vo_start[k] + x["t"], 3)} for x in VO[k]["words"]] for k in VO},
    "cues": cues,
}
(ROOT / "src" / "timeline.json").write_text(json.dumps(out, indent=2))
for k, (a, b) in out["scenes"].items():
    print(f"{k:10s} {a:6.2f} -> {b:6.2f}  ({b - a:4.2f}s)")
print(f"total {TOTAL:.2f}s, {out['frames']} frames")
