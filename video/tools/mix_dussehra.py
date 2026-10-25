"""Sound design + music for the Dussehra reel (no narration).

Reads src/dussehra/timeline.json and writes public/audio/dussehra.wav:
dhol groove + tanpura drone + a shehnai-like melody, the bow and the flaming arrow, the fire,
firecrackers and fireworks, then a triumphant beat into the end card. All synthesised.
"""

import json
from pathlib import Path

import numpy as np
from scipy import signal

from sfx import *  # noqa: F403 (shared synth toolkit)

ROOT = Path(__file__).resolve().parent.parent
TL = json.loads((ROOT / "src" / "dussehra" / "timeline.json").read_text())
N = int((TL["total"] + 0.6) * SR)
Q = TL["cues"]
SC = TL["scenes"]
SPB = 60 / TL["bpm"]
HIT = Q["aim.hit"]
COLLAPSE = Q["burn.collapse"]

music = np.zeros((N, 2))
fx = np.zeros((N, 2))


# ---------- instruments ----------
def dagga(gain: float = 1.0) -> np.ndarray:
    """Dhol bass side."""
    d = 0.45
    body = np.tanh(sweep_sine(d, 105, 52) * decay(d, 8) * 2.2)
    thump = filt(noise(0.05), "lowpass", 400) * decay(0.05, 60)
    body[: len(thump)] += thump * 0.8
    return norm(attack(body, 1)) * gain


def tilli(gain: float = 1.0) -> np.ndarray:
    """Dhol treble side: the sharp stick slap."""
    d = 0.14
    slap = filt(noise(d), "bandpass", [1400, 6000]) * decay(d, 38)
    tone = np.sin(2 * np.pi * 520 * tt(d)) * decay(d, 30) * 0.6
    return norm(attack(slap + tone, 0.5)) * gain


def tanpura(f: float, d: float = 2.2) -> np.ndarray:
    t = tt(d)
    x = sum(signal.sawtooth(2 * np.pi * f * k * t + k) / k for k in (1, 2, 3)) * 0.5
    x = filt(x, "lowpass", 2200, 2) * np.exp(-t * 1.4)
    return attack(x, 8)


def shehnai(notes: list[tuple[float, float]], start_f: float | None = None) -> np.ndarray:
    """Reedy lead with glides and vibrato. notes: (frequency, beats)."""
    total = sum(b for _, b in notes) * SPB
    n = int(total * SR)
    f = np.zeros(n)
    i = 0
    prev = start_f or notes[0][0]
    for freq, beats in notes:
        m = int(beats * SPB * SR)
        glide = min(m, int(0.06 * SR))
        f[i : i + glide] = np.linspace(prev, freq, glide)
        f[i + glide : i + m] = freq
        prev = freq
        i += m
    t = np.arange(n) / SR
    f = f * (1 + 0.012 * np.sin(2 * np.pi * 5.5 * t) * np.clip(t * 2, 0, 1))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = 0.6 * signal.sawtooth(ph) + 0.4 * signal.square(ph, 0.3)
    x = filt(x, "bandpass", [500, 3200], 2)
    env = np.minimum(1, t / 0.05) * np.minimum(1, (total - t) / 0.15)
    return x * env


def crackle(d: float, density: float = 60, seed: int = 0) -> np.ndarray:
    """Fire crackle: random tiny pops of varying size."""
    r = np.random.default_rng(seed)
    out = np.zeros(int(d * SR))
    tpos = 0.0
    while True:
        tpos += r.exponential(1 / density)
        if tpos >= d - 0.02:
            break
        ln = r.uniform(0.002, 0.012)
        pop = filt(r.standard_normal(int(ln * SR) + 8), "highpass", r.uniform(800, 3000), 2) * np.exp(-np.linspace(0, 6, int(ln * SR) + 8))
        a = int(tpos * SR)
        out[a : a + len(pop)] += pop * r.uniform(0.1, 1) ** 2
    return out


def roar(d: float) -> np.ndarray:
    t = tt(d)
    x = filt(noise(d), "lowpass", 700) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.7 * t) * np.sin(2 * np.pi * 1.9 * t))
    return x + filt(noise(d), "bandpass", [150, 400]) * 0.6


def cheer(d: float = 2.6) -> np.ndarray:
    t = tt(d)
    env = np.minimum(1, t / 0.25) * np.exp(-np.maximum(0, t - 0.4) * 1.3)
    x = sum(filt(noise(d), "bandpass", [lo, lo * 2.2]) for lo in (400, 900, 1800))
    return norm(x * env * (0.8 + 0.2 * np.sin(2 * np.pi * 7 * t)))


def pop() -> np.ndarray:
    d = 0.09
    x = filt(noise(d), "highpass", 700) * decay(d, 55)
    th = np.sin(2 * np.pi * 90 * tt(d)) * decay(d, 40)
    return norm(x + th * 0.8)


def whistle(d: float = 0.45) -> np.ndarray:
    t = tt(d)
    f = 900 * (2600 / 900) ** (t / d) * (1 + 0.02 * np.sin(2 * np.pi * 18 * t))
    return norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, t / 0.05)) * 0.6


def twang() -> np.ndarray:
    d = 0.9
    t = tt(d)
    f = 98 * (1 - 0.04 * t)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = sum(np.sin(ph * k) / k**1.2 for k in range(1, 7)) * np.exp(-t * 6)
    slap = filt(noise(0.03), "bandpass", [600, 4000]) * decay(0.03, 80)
    x[: len(slap)] += slap * 0.8
    return norm(attack(x, 0.5))


def creak(d: float = 0.5) -> np.ndarray:
    t = tt(d)
    x = filt(noise(d), "bandpass", [250, 900]) * (0.3 + 0.7 * (t / d)) * (0.6 + 0.4 * np.sin(2 * np.pi * 30 * t))
    return norm(x) * 0.6


def beep(f: float = 1800) -> np.ndarray:
    d = 0.08
    return norm(np.sin(2 * np.pi * f * tt(d)) * decay(d, 30))


def bass_note(f: float, d: float) -> np.ndarray:
    x = np.tanh(np.sin(2 * np.pi * f * tt(d)) * 2 + 0.3 * np.sin(2 * np.pi * 2 * f * tt(d))) * decay(d, 2.5)
    return attack(fade_out(x, 15), 4)


# ---------- 1. the maidan: drone, crowd, dhol ----------
D2, A2, D3 = 73.42, 110.0, 146.83
k = 0
tp = 0.0
while tp < SC["aim"][0]:
    for f in (A2, D3, D3, D2):
        place(music, tanpura(f), tp, 0.22, pan=-0.3 if f == A2 else 0.3)
        tp += SPB
place(music, filt(noise(SC["aim"][0]), "bandpass", [300, 1800]) * np.clip(tt(SC["aim"][0]) / 1.0, 0, 1), 0, 0.05)  # crowd murmur


def dhol_bar(t0: float, full: bool, gain: float = 1.0) -> None:
    e = SPB / 2
    bass = (0, 3, 5) if full else (0, 4)
    treble = (2, 4, 6, 7) if full else (4,)
    for s in bass:
        place(music, dagga(), t0 + s * e, 0.9 * gain, pan=-0.1)
    for s in treble:
        place(music, tilli(), t0 + s * e, (0.55 if s in (2, 6) else 0.35) * gain, pan=0.2)


bar = 4 * SPB
tb = 0.0
while tb < SC["aim"][0] - 0.05:
    dhol_bar(tb, full=tb >= SC["why"][0] - 0.01, gain=0.6 + 0.4 * min(1, tb / SC["heads"][0]))
    tb += bar

# shehnai motif while the heads get their new names
D4, E4, Fs4, A4, B4, D5 = 293.66, 329.63, 369.99, 440.0, 493.88, 587.33
motif = [(A4, 1), (B4, 0.5), (A4, 0.5), (Fs4, 1), (E4, 0.5), (D4, 1.5), (Fs4, 1), (A4, 1), (D5, 2)]
place(music, shehnai(motif), SC["heads"][0] - 0.05, 0.16, pan=0.15)

# labels landing on the heads
for i, c in enumerate(Q["heads.labels"][:-1]):
    place(fx, click(rng.uniform(1600, 2600), 0.06), c, 0.5, pan=-0.5 if i % 2 == 0 else 0.5)
    place(fx, thud(), c, 0.25)
place(fx, thud(), Q["heads.labels"][-1], 1.0)
place(fx, sub_hit(0.8), Q["heads.labels"][-1], 0.6)
place(fx, whoosh(0.3, 600, 5000), Q["heads.feed"] - 0.1, 0.35)

# ---------- 2. aim + the arrow ----------
aim = Q["aim.text"]
place(fx, tape_stop(0.4), SC["aim"][0], 0.35)
place(music, heartbeat(), aim, 0.8)
place(music, heartbeat(), aim + 0.6, 0.9)
for i in range(3):
    place(fx, beep(1600 + i * 300), aim + 0.1 + i * 0.18, 0.25)
place(fx, creak(0.5), Q["aim.twang"] - 0.5, 0.5)
place(fx, twang(), Q["aim.twang"], 0.9)
d = HIT - Q["aim.twang"]
place(fx, whoosh(d + 0.05, 200, 3500), Q["aim.twang"], 0.7)
place(fx, filt(noise(d), "highpass", 3000) * np.linspace(0.2, 1, int(d * SR)), Q["aim.twang"], 0.25)
place(fx, riser(d + 0.2), Q["aim.twang"] - 0.2, 0.4)

# ---------- 3. the burn ----------
place(fx, impact(), HIT, 1.0)
place(fx, sub_hit(1.2), HIT, 0.8)
place(fx, cheer(3.0), HIT + 0.15, 0.35)
burn_d = SC["burn"][1] - HIT + 1.5
env = np.clip(tt(burn_d) / 1.2, 0, 1) * np.clip((burn_d - tt(burn_d)) / 1.5, 0, 1)
place(fx, roar(burn_d) * env, HIT, 0.22)
place(fx, crackle(burn_d, 70, 1) * env, HIT, 0.5, pan=-0.3)
place(fx, crackle(burn_d, 50, 2) * env, HIT, 0.4, pan=0.3)
# a string of firecrackers going off
tc = Q["burn.crackers"]
while tc < Q["burn.crackers"] + 1.3:
    place(fx, pop(), tc, rng.uniform(0.25, 0.55), pan=rng.uniform(-0.7, 0.7))
    tc += rng.uniform(0.03, 0.09)
for i, fw in enumerate(Q["burn.fireworks"] + [SC["end"][0] + 0.25, 23.4, Q["end.final"]]):
    pan = rng.uniform(-0.6, 0.6)
    place(fx, whistle(), fw - 0.45, 0.18, pan=pan)
    place(fx, sub_hit(0.5), fw, 0.45, pan=pan)
    place(fx, crackle(1.2, 120, 10 + i) * np.exp(-tt(1.2) * 2.5), fw + 0.05, 0.35, pan=pan)
# heads dropping off, then the body giving way
order = ["L4", "R4", "L3", "R3", "T", "L2", "R2", "L1", "R1", "M"]
for i, _ in enumerate(order):
    place(fx, thud(), COLLAPSE - 1.3 + i * 0.09 + 0.55, 0.35, pan=rng.uniform(-0.5, 0.5))
place(fx, impact(), COLLAPSE + 0.1, 0.9)
place(fx, filt(noise(2.0), "lowpass", 200) * np.exp(-tt(2.0) * 1.5), COLLAPSE + 0.1, 0.6)
place(fx, cheer(3.2), COLLAPSE + 0.2, 0.45)

# ---------- triumphant beat: from "Burn Ravana" to the end ----------
beat_a = Q["burn.t1"]
beat_b = Q["end.final"]
notes = [D2, D2, 61.74, 65.41]  # D, D, B, C: one per bar
k = 0
tb = beat_a
while tb < beat_b - 0.05:
    barno, beat = divmod(k, 4)
    filtered = SC["varuna"][0] <= tb < Q["varuna.mark"]  # pull back before the logo hit
    g = 0.45 if filtered else 1.0
    place(music, kick(), tb, 0.8 * g)
    if beat in (1, 3):
        place(music, clap(), tb, 0.35 * g, pan=0.1)
    place(music, hat(), tb + SPB / 2, 0.16 * g, pan=0.35)
    if beat == 0:
        dhol_bar(tb, full=True, gain=0.7 * g)
    place(music, bass_note(notes[barno % 4], SPB * 0.92), tb, 0.4 * g)
    k += 1
    tb = beat_a + k * SPB
place(music, riser(Q["varuna.mark"] - SC["varuna"][0]), SC["varuna"][0], 0.5)
place(fx, impact(), Q["varuna.mark"], 0.9)
for c in (Q["varuna.l1"], Q["varuna.l2"]):
    place(fx, whoosh(0.25, 600, 5000), c - 0.08, 0.3)
place(music, shehnai(motif), SC["end"][0], 0.14, pan=0.15)

# ---------- end card ----------
place(fx, whoosh(0.45, 200, 3000), Q["end.ticket"] - 0.15, 0.4)
place(fx, thud(), Q["end.ticket"] + 0.14, 0.9)
place(fx, ping(1568), Q["end.dm"], 0.25)
place(fx, thud(), Q["end.dm"], 0.4)
tp = Q["end.dm"] + 0.4
while tp < Q["end.final"] - 0.2:
    place(fx, click(2000, 0.04), tp, 0.22)
    tp += 1.2
place(fx, impact(), Q["end.final"], 0.9)
tail = TL["total"] - Q["end.final"] + 0.5
place(music, tanpura(D2, tail) * 2, Q["end.final"], 0.35)
place(music, tanpura(A2, tail) * 2, Q["end.final"], 0.2, pan=-0.3)

# ---------- master ----------
fx = reverb(fx, 1.4, 0.3)
music = reverb(music, 0.8, 0.12)
out = master(music * 0.8, fx * 0.7)
fade = int(0.4 * SR)
out[-fade:] *= np.linspace(1, 0, fade)[:, None]
write(ROOT / "public" / "audio" / "dussehra.wav", out[: int(TL["total"] * SR)])
print(f"wrote dussehra.wav ({TL['total']:.2f}s)")
