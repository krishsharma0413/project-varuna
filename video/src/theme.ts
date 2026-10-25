import type { CSSProperties } from "react";
import { continueRender, delayRender, Easing, spring, staticFile } from "remotion";
import timeline from "./timeline.json";

export const TL = timeline;
export const FPS = timeline.fps;
export const W = 1080;
export const H = 1920;

// The site's "invert" palette (frontend/src/styles/app.css .invert)
export const C = {
  bg: "#000",
  fg: "#fff",
  muted: "#c4c4c4",
  soft: "#1c1c1c",
  soft2: "#5a5a5a",
  shadow: "#6d6d6d",
};

export const FONT = '"Archivo", "Arial Narrow", Arial, sans-serif';

const fontHandle = delayRender("Archivo font");
const archivo = new FontFace("Archivo", `url(${staticFile("fonts/archivo-latin-wdth-normal.woff2")}) format("woff2")`, {
  weight: "100 900",
  stretch: "62% 125%",
});
archivo
  .load()
  .then((f) => {
    document.fonts.add(f);
    continueRender(fontHandle);
  })
  .catch((err) => {
    console.error(err);
    continueRender(fontHandle);
  });

/** Condensed poster headline, like .hero-claim / .sec-title on the site. */
export const display = (size: number, stretch = 62): CSSProperties => ({
  fontFamily: FONT,
  fontWeight: 900,
  fontStretch: `${stretch}%`,
  fontSize: size,
  lineHeight: 0.86,
  textTransform: "uppercase",
  letterSpacing: "-0.01em",
});

/** Small uppercase label, like .eyebrow / .mini-label on the site. */
export const label = (size: number, spacing = 0.08): CSSProperties => ({
  fontFamily: FONT,
  fontWeight: 800,
  fontStretch: "100%",
  fontSize: size,
  textTransform: "uppercase",
  letterSpacing: `${spacing}em`,
  lineHeight: 1.1,
});

export const body = (size: number): CSSProperties => ({
  fontFamily: FONT,
  fontWeight: 500,
  fontStretch: "100%",
  fontSize: size,
  lineHeight: 1.4,
});

/** The site's outlined emphasis (em in .sec-title / .hero-claim). */
export const outline = (px: number): CSSProperties => ({
  color: "transparent",
  WebkitTextStroke: `${px}px ${C.fg}`,
});

export const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
export const ease = Easing.bezier(0.2, 0, 0, 1);
export const easeIn = Easing.bezier(0.55, 0, 1, 0.45);

/** 0→1 progress of a tween starting at `start` lasting `dur` seconds. */
export const prog = (t: number, start: number, dur: number, fn: (x: number) => number = ease) =>
  fn(clamp01((t - start) / dur));

/** Spring from 0→1 triggered at `start` (seconds). */
export const springAt = (t: number, start: number, cfg: { damping?: number; stiffness?: number; mass?: number } = {}) =>
  t < start ? 0 : spring({ frame: (t - start) * FPS, fps: FPS, config: { damping: 14, stiffness: 180, mass: 1, ...cfg } });

/** Decaying kick: 1 at `start`, falling to 0. Summed over cues it gives camera punches. */
export const kick = (t: number, start: number, decay = 9) => (t < start ? 0 : Math.exp(-(t - start) * decay));

export const kicks = (t: number, starts: number[], decay = 9) => starts.reduce((a, s) => a + kick(t, s, decay), 0);

/** Camera shake offset in px from a list of impact times. */
export const shake = (t: number, starts: number[], amp = 18, decay = 10) => {
  const k = kicks(t, starts, decay);
  return {
    x: Math.sin(t * 91.7) * Math.cos(t * 37.3) * amp * k,
    y: Math.cos(t * 83.1) * Math.sin(t * 29.9) * amp * k,
    r: Math.sin(t * 61.3) * amp * 0.05 * k,
  };
};

export const scene = (name: keyof typeof timeline.scenes) => timeline.scenes[name] as [number, number];
export const words = (key: keyof typeof timeline.words) => timeline.words[key];
