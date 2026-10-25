"""Shared synth toolkit for the reel sound designs: primitives, sound effects, bus helpers, master."""

import wave
from pathlib import Path

import numpy as np
from scipy import signal

SR = 48000
rng = np.random.default_rng(42)


# ---------- primitives ----------
def tt(dur: float) -> np.ndarray:
    return np.arange(int(dur * SR)) / SR


def noise(dur: float) -> np.ndarray:
    return rng.standard_normal(int(dur * SR))


def filt(x: np.ndarray, kind: str, f, order: int = 4) -> np.ndarray:
    sos = signal.butter(order, f, btype=kind, fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def decay(dur: float, rate: float) -> np.ndarray:
    return np.exp(-tt(dur) * rate)


def attack(x: np.ndarray, ms: float = 3) -> np.ndarray:
    n = min(len(x), int(ms / 1000 * SR))
    x = x.copy()
    x[:n] *= np.linspace(0, 1, n)
    return x


def fade_out(x: np.ndarray, ms: float = 20) -> np.ndarray:
    n = min(len(x), int(ms / 1000 * SR))
    x = x.copy()
    x[-n:] *= np.linspace(1, 0, n)
    return x


def sweep_sine(dur: float, f0: float, f1: float, curve: str = "exp") -> np.ndarray:
    t = tt(dur)
    f = f0 * (f1 / f0) ** (t / dur) if curve == "exp" else f0 + (f1 - f0) * t / dur
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def norm(x: np.ndarray, peak: float = 1.0) -> np.ndarray:
    m = np.max(np.abs(x)) or 1
    return x / m * peak


# ---------- sound effects ----------
def sub_hit(size: float = 1.0) -> np.ndarray:
    d = 1.4 * size
    body = sweep_sine(d, 70, 34) * decay(d, 3.2 / size)
    click = filt(noise(0.03), "highpass", 2000) * decay(0.03, 120) * 0.5
    thump = filt(noise(0.25), "lowpass", 180) * decay(0.25, 18) * 2.5
    out = np.zeros(len(body))
    out += np.tanh(body * 1.6)
    out[: len(click)] += click
    out[: len(thump)] += thump
    return norm(attack(out, 1))


def impact() -> np.ndarray:
    d = 2.6
    boom = np.tanh(sweep_sine(d, 90, 30) * decay(d, 2.0) * 2.2)
    crash = filt(noise(d), "highpass", 3000) * decay(d, 3.5) * 0.35
    mid = filt(noise(0.4), "bandpass", [200, 1500]) * decay(0.4, 9) * 1.2
    out = boom + crash
    out[: len(mid)] += mid
    return norm(attack(out, 1))


def riser(dur: float) -> np.ndarray:
    t = tt(dur)
    p = t / dur
    nz = noise(dur)
    lo = filt(nz, "bandpass", [400, 1600])
    hi = filt(nz, "bandpass", [2500, 9000])
    air = lo * (1 - p) + hi * p
    tone = sweep_sine(dur, 110, 880) * 0.35 + sweep_sine(dur, 110 * 1.5, 880 * 1.5) * 0.15
    trem = 0.75 + 0.25 * np.sin(2 * np.pi * np.cumsum(4 + 18 * p**2) / SR)
    out = (air * 0.6 + tone) * (p**2.2) * trem
    return norm(fade_out(out, 10))


def whoosh(dur: float = 0.35, lo: float = 300, hi: float = 4000) -> np.ndarray:
    t = tt(dur)
    env = np.sin(np.pi * t / dur) ** 2
    return norm(filt(noise(dur), "bandpass", [lo, hi]) * env)


def swipe() -> np.ndarray:
    return whoosh(0.22, 900, 7000) * 0.8


def ping(base: float = 1320) -> np.ndarray:
    d = 0.45
    t = tt(d)
    x = np.sin(2 * np.pi * base * t) + 0.5 * np.sin(2 * np.pi * base * 1.5 * t) * (t > 0.07)
    return norm(attack(x * decay(d, 9)))


def click(freq: float = 2500, d: float = 0.05) -> np.ndarray:
    x = filt(noise(d), "bandpass", [freq * 0.6, min(freq * 2.2, 20000)]) * decay(d, 140)
    return norm(attack(x, 0.3))


def tick() -> np.ndarray:
    d = 0.06
    return norm(np.sin(2 * np.pi * 2800 * tt(d)) * decay(d, 70) + click(5000, d) * 0.4)


def thud() -> np.ndarray:
    d = 0.5
    low = np.tanh(sweep_sine(d, 120, 45) * decay(d, 11) * 2)
    slap = filt(noise(0.06), "bandpass", [300, 2500]) * decay(0.06, 60) * 1.4
    out = low.copy()
    out[: len(slap)] += slap
    return norm(attack(out, 0.5))


def heartbeat() -> np.ndarray:
    beat = lambda: np.sin(2 * np.pi * 52 * tt(0.22)) * decay(0.22, 22)
    out = np.zeros(int(0.5 * SR))
    b = beat()
    out[: len(b)] += b
    o = int(0.17 * SR)
    out[o : o + len(b)] += b * 0.7
    return norm(np.tanh(out * 2))


def glitch(d: float = 0.18) -> np.ndarray:
    x = noise(d)
    hold = 40
    x = np.repeat(x[::hold], hold)[: int(d * SR)]
    gate = (np.floor(tt(d) * 40) % 2).astype(float)
    return norm(filt(x, "bandpass", [500, 6000]) * gate * decay(d, 8))


def tape_stop(d: float = 0.45) -> np.ndarray:
    return norm(np.tanh(sweep_sine(d, 420, 40) * 2) * (1 - tt(d) / d) ** 1.5)


def typekey() -> np.ndarray:
    return click(rng.uniform(1800, 3200), 0.04)


def kick() -> np.ndarray:
    d = 0.4
    x = np.tanh(sweep_sine(d, 150, 45) * decay(d, 9) * 3)
    c = click(3000, 0.01)
    x[: len(c)] += c * 0.2
    return norm(x)


def hat(open_: bool = False) -> np.ndarray:
    d = 0.18 if open_ else 0.05
    return norm(filt(noise(d), "highpass", 7000) * decay(d, 25 if open_ else 90))


def clap() -> np.ndarray:
    d = 0.22
    x = filt(noise(d), "bandpass", [900, 4000])
    env = decay(d, 16)
    for o in (0.0, 0.012, 0.024):
        n = int(o * SR)
        env[n : n + 60] += 0.6
    return norm(x * env)


def place(bus: np.ndarray, x: np.ndarray, t: float, gain: float = 1.0, pan: float = 0.0) -> None:
    i = int(round(t * SR))
    if i >= len(bus) or i + len(x) <= 0:
        return
    if i < 0:
        x, i = x[-i:], 0
    x = x[: len(bus) - i]
    if bus.ndim == 1:
        bus[i : i + len(x)] += x * gain
    else:
        bus[i : i + len(x), 0] += x * gain * np.sqrt((1 - pan) / 2) * np.sqrt(2)
        bus[i : i + len(x), 1] += x * gain * np.sqrt((1 + pan) / 2) * np.sqrt(2)


def read_wav(p: Path) -> np.ndarray:
    with wave.open(str(p)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768


def reverb(x: np.ndarray, secs: float, wet: float) -> np.ndarray:
    ir_t = tt(secs)
    out = x.copy()
    for ch in range(2):
        ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 6 / secs)
        ir = filt(ir, "lowpass", 6000, 2)
        ir /= np.sqrt(np.sum(ir**2))
        out[:, ch] += signal.fftconvolve(x[:, ch], ir)[: len(x)] * wet
    return out


def master(*buses: np.ndarray) -> np.ndarray:
    x = sum(buses)
    x = np.tanh(x * 1.1) / np.tanh(1.1)
    x = x / np.max(np.abs(x)) * 0.93
    return x


def write(path: Path, x: np.ndarray) -> None:
    y = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(y.tobytes())
