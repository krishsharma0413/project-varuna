"""Synthesise the sound design and mix it with the voice-over.

Reads src/timeline.json (+ the VO clips) and writes:
  public/audio/mix.wav      voice + sound effects + music bed
  public/audio/nomusic.wav  voice + sound effects only (for adding a trending sound in Instagram)
  public/audio/nonarration.wav  sound effects + music only (to record your own voice over)
Everything is generated here, so there is nothing to license.
"""

import json
import wave
from pathlib import Path

import numpy as np
from scipy import signal

from sfx import *  # noqa: F403 (shared synth toolkit)

ROOT = Path(__file__).resolve().parent.parent
TL = json.loads((ROOT / "src" / "timeline.json").read_text())
N = int((TL["total"] + 0.5) * SR)

sc = TL["scenes"]
cues = TL["cues"]
words = TL["words"]
HOOK = sc["hook"][1]


# ---------- buses ----------
voice = np.zeros(N)
sfx = np.zeros((N, 2))
music = np.zeros((N, 2))


# ---------- voice ----------
for key, v in TL["vo"].items():
    x = read_wav(ROOT / "public" / "audio" / f"vo_{key}.wav")
    x = filt(x, "highpass", 75, 2)
    x = np.tanh(x * 1.8) / np.tanh(1.8)  # gentle glue/compression
    place(voice, x, v["start"], 0.9)

# ---------- 1. hook ----------
snaps = cues["hook.snaps"]
free = snaps[-1]
hook_sfx = np.zeros((N, 2))
hook_music = np.zeros((N, 2))
# low room tone + heartbeat
hum = filt(noise(HOOK), "lowpass", 220) * 0.5 + np.sin(2 * np.pi * 55 * tt(HOOK)) * 0.25
place(hook_music, hum * np.minimum(1, tt(HOOK) / 0.3), 0, 0.35)
for i, tb in enumerate([0.02, 0.74, 1.38, 1.9, 2.3, 2.62, 2.9, 3.12, 3.3, 3.45]):
    place(hook_music, heartbeat(), tb, 0.9 if i < 4 else 1.0)
for i, s in enumerate(snaps):
    place(hook_sfx, swipe(), s - 0.05, 0.7, pan=-0.2 if i % 2 else 0.2)
    place(hook_sfx, ping(1320 if i % 2 else 1568), s + 0.08, 0.28, pan=0.5 if i % 2 else -0.5)
# free scroll: a swipe each time a post passes, faster and faster
K, POW = 10.5, 2.6
n = 1
while True:
    dt = (n / K) ** (1 / POW)
    if free + dt >= HOOK - 0.02:
        break
    place(hook_sfx, swipe(), free + dt - 0.04, 0.35 + 0.25 * dt, pan=rng.uniform(-0.6, 0.6))
    n += 1
for i in range(10):  # bubbles
    place(hook_sfx, ping(rng.choice([1175, 1320, 1568, 1760, 2093])), free + 0.12 + i * 0.09, 0.22, pan=rng.uniform(-0.8, 0.8))
for g in (free + 0.45, free + 0.8, free + 1.05, HOOK - 0.15):
    place(hook_sfx, glitch(), g, 0.3, pan=rng.uniform(-0.5, 0.5))
place(hook_music, riser(HOOK - free + 0.3), free - 0.3, 0.6)
# hard cut to silence at the end of the hook
cut = int(HOOK * SR)
for b in (hook_sfx, hook_music):
    b[cut - int(0.004 * SR) : cut] *= np.linspace(1, 0, int(0.004 * SR))[:, None]
    b[cut:] = 0
sfx += hook_sfx
music += hook_music

# ---------- 2. question ----------
place(sfx, tape_stop(), HOOK, 0.45)
q = [w["t"] for w in words["q1"]]
place(sfx, whoosh(0.25, 600, 5000), q[0] - 0.08, 0.35)
for i, size, g in ((2, 0.6, 0.55), (4, 1.0, 0.9), (5, 0.7, 0.6), (7, 1.1, 0.95)):
    place(sfx, sub_hit(size), q[i] - 0.02, g)

# ---------- 3-5. dark room ----------
place(sfx, click(2200, 0.06), cues["room.click"], 0.8)
place(sfx, click(1400, 0.05), cues["room.click"] + 0.12, 0.4)
room_a, room_b = sc["room"][0], sc["still"][1]
dur = room_b - room_a
t = tt(dur)
drone = (
    filt(signal.sawtooth(2 * np.pi * 55 * t) + signal.sawtooth(2 * np.pi * 55.35 * t), "lowpass", 260, 2) * 0.5
    + np.sin(2 * np.pi * 27.5 * t) * 0.6
    + np.sin(2 * np.pi * 659.3 * t + 3 * np.sin(2 * np.pi * 5 * t)) * 0.04
)
env = np.clip((t - (cues["room.click"] - room_a)) / 0.6, 0, 1) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.3 * t))
env *= 1 + 0.8 * np.clip((t - (sc["still"][0] - room_a)) / (sc["still"][1] - sc["still"][0]), 0, 1)
place(music, drone * env, room_a, 0.3)
buzz = np.sign(np.sin(2 * np.pi * 100 * t)) * 0.5
buzz = filt(buzz, "bandpass", [90, 900], 2) * np.clip((t - (cues["room.click"] - room_a)) / 0.1, 0, 1)
place(sfx, buzz, room_a, 0.025)
# typewriter on "Was any of it true?"
for w in words["room"]:
    for k in range(len(w["w"])):
        place(sfx, typekey(), w["t"] + k * 0.045, 0.22, pan=rng.uniform(-0.3, 0.3))
place(sfx, whoosh(0.5, 200, 2500), sc["creators"][0] - 0.1, 0.3)
for i, s in enumerate(cues["creators.stamps"]):
    place(sfx, thud(), s, 0.95, pan=(-0.25, 0.25, -0.2, 0.0)[i])
st = [w["t"] for w in words["still"]]
for i, size, g in ((1, 0.5, 0.4), (3, 1.0, 0.85), (7, 0.8, 0.6)):
    place(sfx, sub_hit(size), st[i] - 0.02, g)
rise_from = sc["still"][0] + 0.3
place(music, riser(cues["turn.flash"] - rise_from), rise_from, 0.55)

# ---------- 6. the turn ----------
place(sfx, impact(), cues["turn.flash"], 1.0)
for i in (0, 2):
    place(sfx, whoosh(0.22, 800, 6000), words["turn"][i]["t"] - 0.06, 0.3)
place(sfx, impact(), cues["turn.wordmark"], 0.9)

# ---------- beat: from the wordmark to the final "Varuna it." ----------
beat_a = cues["turn.wordmark"]
beat_b = cues["end.varuna"]
spb = 60 / 118
bass_notes = [55.0, 55.0, 43.65, 49.0]  # A1 A1 F1 G1, one per bar
k = 0
tb = beat_a
while tb < beat_b - 0.05:
    bar, beat = divmod(k, 4)
    place(music, kick(), tb, 0.85)
    if beat in (1, 3):
        place(music, clap(), tb, 0.35, pan=0.1)
    place(music, hat(), tb + spb / 2, 0.18, pan=0.35)
    place(music, hat(beat == 3), tb + spb * 0.75, 0.1, pan=-0.35)
    f = bass_notes[bar % 4]
    d = spb * 0.9
    b = np.tanh(np.sin(2 * np.pi * f * tt(d)) * 2.2 + 0.4 * np.sin(2 * np.pi * f * 2 * tt(d))) * decay(d, 3)
    place(music, attack(fade_out(b, 15), 4), tb, 0.45)
    k += 1
    tb = beat_a + k * spb
# a pad under the product section
pa = beat_a
pd = beat_b - pa
pt = tt(pd)
pad = sum(np.sin(2 * np.pi * f * pt + 0.3 * np.sin(2 * np.pi * 0.2 * pt)) for f in (220, 261.6, 329.6)) / 3
pad = filt(pad, "lowpass", 1200, 2) * np.clip(pt / 1.5, 0, 1) * np.clip((pd - pt) / 0.3, 0, 1)
place(music, pad, pa, 0.07)

# ---------- 7. paste ----------
ps = sc["paste"][0]
place(sfx, whoosh(0.4, 300, 3000), ps, 0.4)
place(sfx, click(3000), cues["paste.paste"] - 0.04, 0.5)
place(sfx, ping(1760), cues["paste.paste"] + 0.02, 0.18)
place(sfx, thud(), cues["paste.press"], 0.4)
place(sfx, click(1800), cues["paste.press"], 0.6)
for i in range(5):
    place(sfx, tick(), cues["paste.press"] + 0.2 + i * 0.11, 0.18)

# ---------- 8. pipeline ----------
for i, c in enumerate(cues["pipeline.cards"]):
    place(sfx, whoosh(0.3, 400, 5000), c - 0.12, 0.45, pan=-0.4 if i % 2 == 0 else 0.4)
    place(sfx, thud(), c + 0.1, 0.35)

# ---------- 9. receipts ----------
place(sfx, whoosh(0.4, 300, 4000), sc["receipts"][0] - 0.05, 0.45, pan=0.4)
place(sfx, thud(), cues["receipts.stamp"], 1.0)
place(sfx, sub_hit(0.7), cues["receipts.stamp"], 0.5)
place(sfx, whoosh(0.35, 300, 3000), cues["receipts.stamp"] + 0.25, 0.35)
for r in cues["receipts.rows"]:
    place(sfx, tick(), r, 0.3, pan=0.3)

# ---------- 10. end ----------
place(sfx, whoosh(0.45, 200, 3000), cues["end.ticket"] - 0.15, 0.4)
place(sfx, thud(), cues["end.ticket"] + 0.14, 0.9)
place(sfx, ping(1568), cues["end.dm"], 0.25)
place(sfx, thud(), cues["end.dm"], 0.4)
tp = cues["end.dm"] + 0.4
while tp < sc["end"][1] - 0.3:
    place(sfx, click(2000, 0.04), tp, 0.25)
    tp += 1.1
place(sfx, sub_hit(0.6), cues["end.forward"], 0.4)
place(sfx, impact(), cues["end.varuna"], 1.0)
tail = sc["end"][1] - cues["end.varuna"] + 0.4
tl_ = tt(tail)
place(music, filt(np.sin(2 * np.pi * 55 * tl_) + 0.5 * signal.sawtooth(2 * np.pi * 110 * tl_), "lowpass", 400) * np.exp(-tl_ * 1.6), cues["end.varuna"], 0.25)


# ---------- reverb, ducking, master ----------
sfx = reverb(sfx, 1.2, 0.35)
music = reverb(music, 0.9, 0.15)

# sidechain: duck music under the voice
venv = filt(np.abs(voice), "lowpass", 8, 2)
venv = np.clip(venv / (np.max(venv) * 0.25), 0, 1)
duck = 1 - 0.7 * venv
music_dry = music.copy()  # un-ducked bed for the no-narration mix
music *= duck[:, None]

voice_st = np.stack([voice, voice], axis=1)


out = ROOT / "public" / "audio"
write(out / "mix.wav", master(voice_st * 1.0, sfx * 0.55, music * 0.5))
write(out / "nomusic.wav", master(voice_st * 1.0, sfx * 0.55))
write(out / "nonarration.wav", master(sfx * 0.55, music_dry * 0.5))
print(f"wrote mix.wav, nomusic.wav and nonarration.wav ({N / SR:.2f}s)")
