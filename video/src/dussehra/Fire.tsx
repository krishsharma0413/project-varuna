import { random } from "remotion";

// The one warm accent in an otherwise black-and-white reel.
export const FIRE = {
  core: [255, 246, 214],
  hot: [255, 198, 92],
  mid: [255, 132, 38],
  low: [214, 62, 22],
};

const mix = (a: number[], b: number[], k: number) => a.map((v, i) => Math.round(v + (b[i] - v) * k));
const flameColor = (a: number) =>
  a < 0.2 ? mix(FIRE.core, FIRE.hot, a / 0.2) : a < 0.5 ? mix(FIRE.hot, FIRE.mid, (a - 0.2) / 0.3) : mix(FIRE.mid, FIRE.low, (a - 0.5) / 0.5);

export type Emitter = { x: number; y: number; ignite: number; size: number; rise: number; spread: number; n?: number; until?: number; head?: string };

/** Particle flames. Each emitter loops short-lived blobs that rise, shrink and cool, over a soft glow. */
export const Flames = ({ emitters, t, gain = 1, warp }: { emitters: Emitter[]; t: number; gain?: number; warp?: string }) => {
  const out = [];
  const glows = [];
  for (let i = 0; i < emitters.length; i++) {
    const e = emitters[i];
    if (t < e.ignite) continue;
    const since = t - e.ignite;
    const fadeOut = e.until !== undefined ? Math.max(0, 1 - (t - e.until) / 0.8) : 1;
    if (fadeOut <= 0) continue;
    const ramp = Math.min(1, since / 0.35);
    const n = (e.n ?? 7) + 5;
    const gs = e.size * 2.6 * ramp * gain;
    const gf = 0.8 + 0.2 * Math.sin(t * 17 + i * 2.3);
    glows.push(
      <div
        key={`g${i}`}
        style={{
          position: "absolute",
          left: e.x - gs / 2,
          top: e.y - gs * 0.75,
          width: gs,
          height: gs * 1.2,
          borderRadius: "50%",
          background: `radial-gradient(ellipse at 50% 60%, rgba(${FIRE.mid.join(",")},${0.38 * gf * fadeOut}) 0%, rgba(${FIRE.low.join(",")},${0.18 * gf * fadeOut}) 40%, rgba(0,0,0,0) 70%)`,
          mixBlendMode: "screen",
        }}
      />,
    );
    for (let j = 0; j < n; j++) {
      const L = 0.5 + random(`L${i}-${j}`) * 0.45;
      const off = random(`o${i}-${j}`) * L;
      const age0 = since - off;
      if (age0 < 0) continue;
      const cycle = Math.floor(age0 / L);
      const a = (age0 - cycle * L) / L;
      const r1 = random(`x${i}-${j}-${cycle}`);
      const r2 = random(`s${i}-${j}-${cycle}`);
      const x = e.x + (r1 - 0.5) * e.spread * (1 - a * 0.5) + Math.sin(t * 7 + i * 1.7 + j) * 10 * a;
      const y = e.y - a * e.rise * (0.8 + r2 * 0.4);
      const size = e.size * 0.8 * Math.pow(1 - a, 0.55) * (0.6 + r2 * 0.6) * ramp * fadeOut * gain;
      if (size < 2) continue;
      const [r, g, b] = flameColor(a);
      const op = Math.pow(1 - a, 1.1) * 0.95;
      out.push(
        <div
          key={`${i}-${j}`}
          style={{
            position: "absolute",
            left: x - size / 2,
            top: y - size * 0.7,
            width: size,
            height: size * 1.7,
            borderRadius: "50% 50% 45% 45% / 70% 70% 30% 30%",
            background: `radial-gradient(ellipse at 50% 62%, rgba(${r},${g},${b},${op}) 0%, rgba(${r},${g},${b},${op * 0.55}) 35%, rgba(${r},${g},${b},0) 70%)`,
            mixBlendMode: "screen",
          }}
        />,
      );
    }
  }
  return (
    <>
      {glows}
      {warp === "none" ? out : <div style={{ position: "absolute", inset: 0, filter: warp ? `url(#${warp}) blur(2px)` : "blur(2px)" }}>{out}</div>}
    </>
  );
};

/** SVG filter that makes flame edges lick upward. Re-seeded every other frame for flicker. */
export const FlameWarp = ({ id, frame, scale = 38 }: { id: string; frame: number; scale?: number }) => (
  <svg width={0} height={0} style={{ position: "absolute" }}>
    <filter id={id} x="-20%" y="-20%" width="140%" height="140%">
      <feTurbulence type="fractalNoise" baseFrequency="0.018 0.045" numOctaves={2} seed={Math.floor(frame / 2)} result="n" />
      <feDisplacementMap in="SourceGraphic" in2="n" scale={scale} xChannelSelector="R" yChannelSelector="G" />
    </filter>
  </svg>
);

/** Soft smoke blobs drifting up from a band of the effigy. */
export const Smoke = ({ t, from, x0, x1, y, amount = 1, n = 26 }: { t: number; from: number; x0: number; x1: number; y: number; amount?: number; n?: number }) => {
  if (t < from) return null;
  const out = [];
  for (let i = 0; i < n; i++) {
    const L = 3 + random(`sL${i}`) * 2;
    const off = random(`so${i}`) * L;
    const age0 = t - from - off;
    if (age0 < 0) continue;
    const cycle = Math.floor(age0 / L);
    const a = (age0 - cycle * L) / L;
    const x = x0 + random(`sx${i}-${cycle}`) * (x1 - x0) + Math.sin(t * 0.8 + i) * 40 + a * 120;
    const yy = y - a * 900;
    const size = 160 + a * 520;
    const op = Math.sin(Math.PI * a) * 0.42 * amount * Math.min(1, (t - from) / 0.8);
    const g = 34 + Math.round(random(`sg${i}`) * 18);
    out.push(
      <div
        key={i}
        style={{
          position: "absolute",
          left: x - size / 2,
          top: yy - size / 2,
          width: size,
          height: size,
          borderRadius: "50%",
          background: `radial-gradient(circle, rgba(${g},${g},${g},${op}) 0%, rgba(${g},${g},${g},${op * 0.5}) 40%, rgba(${g},${g},${g},0) 70%)`,
        }}
      />,
    );
  }
  return <>{out}</>;
};

/** Embers rising through the frame (screen space). */
export const Embers = ({ t, from, n = 70, amount = 1 }: { t: number; from: number; n?: number; amount?: number }) => {
  if (t < from) return null;
  const out = [];
  for (let i = 0; i < n; i++) {
    const L = 2.2 + random(`eL${i}`) * 2.5;
    const off = random(`eo${i}`) * L;
    const age0 = t - from - off;
    if (age0 < 0) continue;
    const cycle = Math.floor(age0 / L);
    const a = (age0 - cycle * L) / L;
    const x = random(`ex${i}-${cycle}`) * 1080 + Math.sin(t * 2 + i) * 30 * a;
    const y = 1980 - a * (1400 + random(`ey${i}`) * 900);
    const s = 3 + random(`es${i}`) * 6;
    const flick = 0.6 + 0.4 * Math.sin(t * 20 + i * 3);
    const [r, g, b] = mix(FIRE.hot, FIRE.mid, random(`ec${i}`));
    out.push(
      <div
        key={i}
        style={{
          position: "absolute",
          left: x,
          top: y,
          width: s,
          height: s,
          borderRadius: "50%",
          background: `rgb(${r},${g},${b})`,
          boxShadow: `0 0 ${s * 2.5}px ${s * 0.8}px rgba(${r},${g},${b},.7)`,
          opacity: (1 - a) * flick * amount,
        }}
      />,
    );
  }
  return <>{out}</>;
};

/** A rocket that climbs and bursts into streaks (screen space). */
export const Firework = ({ t, at, x, y, seed }: { t: number; at: number; x: number; y: number; seed: number }) => {
  const climb = 0.45;
  const start = at - climb;
  if (t < start || t > at + 1.6) return null;
  if (t < at) {
    const p = (t - start) / climb;
    const yy = 1900 - (1900 - y) * (1 - Math.pow(1 - p, 2));
    return (
      <>
        {Array.from({ length: 8 }, (_, k) => (
          <div
            key={k}
            style={{
              position: "absolute",
              left: x - 3,
              top: yy + k * 22,
              width: 6,
              height: 18,
              borderRadius: 3,
              background: `rgba(${FIRE.hot.join(",")},${1 - k / 8})`,
            }}
          />
        ))}
      </>
    );
  }
  const a = (t - at) / 1.6;
  const parts = [];
  const N = 44;
  for (let k = 0; k < N; k++) {
    const ang = (k / N) * Math.PI * 2 + random(`fa${seed}-${k}`) * 0.12;
    const sp = 380 + random(`fs${seed}-${k}`) * 260;
    const d = sp * (1 - Math.exp(-3 * a * 1.6)) / 3;
    const px = x + Math.cos(ang) * d;
    const py = y + Math.sin(ang) * d + 260 * a * a;
    const white = k % 3 === 0;
    const col = white ? "255,255,255" : FIRE.hot.join(",");
    const twinkle = a > 0.55 ? (random(`ft${seed}-${k}-${Math.floor(t * 20)}`) > 0.4 ? 1 : 0.2) : 1;
    parts.push(
      <div
        key={k}
        style={{
          position: "absolute",
          left: px - 2.5,
          top: py - 14,
          width: 5,
          height: 28 * (1 - a) + 6,
          borderRadius: 3,
          background: `linear-gradient(rgba(${col},0), rgba(${col},${(1 - a) * twinkle}))`,
          transform: `rotate(${(ang * 180) / Math.PI - 90}deg)`,
          transformOrigin: "50% 100%",
          boxShadow: `0 0 10px rgba(${col},${0.6 * (1 - a)})`,
        }}
      />,
    );
  }
  const flash = Math.max(0, 1 - a * 6);
  return (
    <>
      <div
        style={{
          position: "absolute",
          left: x - 220,
          top: y - 220,
          width: 440,
          height: 440,
          borderRadius: "50%",
          background: `radial-gradient(circle, rgba(255,240,210,${flash}) 0%, rgba(255,160,60,${flash * 0.4}) 30%, rgba(0,0,0,0) 70%)`,
          mixBlendMode: "screen",
        }}
      />
      {parts}
    </>
  );
};
