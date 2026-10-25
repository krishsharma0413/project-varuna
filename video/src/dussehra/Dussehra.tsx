import type { CSSProperties, ReactNode } from "react";
import { AbsoluteFill, Html5Audio, random, staticFile, useCurrentFrame } from "remotion";
import { Plane } from "../components/icons";
import { Grain, Vignette } from "../components/Overlays";
import { Slam } from "../components/SlamWords";
import { Stamp } from "../components/Stamp";
import { C, clamp01, display, ease, FONT, label, outline, shake, springAt } from "../theme";
import { Effigy, HEADS, LABEL_ORDER, NAVEL } from "./Effigy";
import { Embers, type Emitter, FIRE, Firework, Flames, FlameWarp, Smoke } from "./Fire";
import tl from "./timeline.json";

export const DTL = tl;
const Q = tl.cues;
const SC = tl.scenes;
const HIT = Q["aim.hit"];
const TWANG = Q["aim.twang"];
const COLLAPSE = Q["burn.collapse"];
const GLOW = `0 0 40px rgba(${FIRE.mid.join(",")},.75), 0 0 90px rgba(${FIRE.low.join(",")},.55)`;

// ---------- camera ----------
const KEYS: [number, number, number, number][] = [
  [0, 1.45, 540, 1640],
  [2.4, 1.0, 540, 1000],
  [5.2, 1.04, 540, 990],
  [5.9, 1.0, 540, 790],
  [9.3, 1.02, 540, 770],
  [9.9, 1.18, 540, 1040],
  [HIT, 1.26, 540, 1090],
  [12.0, 1.0, 540, 1000],
  [COLLAPSE, 1.02, 540, 1000],
  [SC.burn[1], 1.12, 540, 1180],
];
const camera = (t: number) => {
  let i = 0;
  while (i < KEYS.length - 2 && t > KEYS[i + 1][0]) i++;
  const [t0, s0, x0, y0] = KEYS[i];
  const [t1, s1, x1, y1] = KEYS[i + 1];
  const k = ease(clamp01((t - t0) / (t1 - t0)));
  return { s: s0 + (s1 - s0) * k, cx: x0 + (x1 - x0) * k, cy: y0 + (y1 - y0) * k };
};

// ---------- fire layout ----------
const dist = (x: number, y: number) => Math.hypot(x - NAVEL.x, y - NAVEL.y);
const ig = (x: number, y: number, i: number) => HIT + dist(x, y) / 430 + random(`ig${i}`) * 0.15;
const BURN: Emitter[] = [];
const add = (x: number, y: number, size: number, rise: number, spread: number, n = 7, head?: string) =>
  BURN.push({ x, y, ignite: ig(x, y, BURN.length), size, rise, spread, n, head });
add(NAVEL.x, NAVEL.y, 130, 260, 60, 9);
for (let r = 0; r < 4; r++) for (let c = 0; c < 4; c++) add(380 + c * 105, 870 + r * 95, 110, 230, 70);
for (let r = 0; r < 3; r++) for (let c = 0; c < 4; c++) add(330 + c * 140 + r * 0, 1260 + r * 110, 120, 240, 90);
[[250, 960], [230, 1100], [830, 960], [850, 1100], [220, 1255], [880, 1400]].forEach(([x, y]) => add(x, y, 100, 220, 60));
HEADS.forEach((h) => {
  add(h.cx, h.cy, h.w * 1.1, h.h * 1.8, h.w * 0.6, 8, h.id);
  add(h.cx, h.cy - h.h / 2 - h.crown * 0.4, h.w * 0.8, h.h * 1.4, h.w * 0.5, 5, h.id);
});
[[465, 1640], [615, 1640]].forEach(([x, y]) => add(x, y, 90, 200, 40));
const headIgnite = (id: string) => {
  const h = HEADS.find((x) => x.id === id)!;
  return ig(h.cx, h.cy, 0);
};
// burnt heads drop off one by one just before the body gives way
const FALL_ORDER = ["L4", "R4", "L3", "R3", "T", "L2", "R2", "L1", "R1", "M"];
const headFall = (id: string, t: number) => {
  const start = COLLAPSE - 1.3 + FALL_ORDER.indexOf(id) * 0.09;
  if (t < start) return undefined;
  const d = t - start;
  const side = id.startsWith("L") ? -1 : id.startsWith("R") ? 1 : 0;
  return { dy: 0.5 * 2600 * d * d, rot: side * d * 140 + (id === "M" ? d * 40 : 0) };
};

const BONFIRE: Emitter[] = Array.from({ length: 9 }, (_, i) => ({
  x: 290 + i * 62,
  y: 1760,
  ignite: COLLAPSE - 0.6 + random(`bf${i}`) * 0.4,
  size: 220,
  rise: 520,
  spread: 110,
  n: 8,
}));
const TORCHES: Emitter[] = [
  { x: 150, y: 1585, ignite: -1, size: 70, rise: 120, spread: 20, n: 6 },
  { x: 930, y: 1585, ignite: -1, size: 70, rise: 120, spread: 20, n: 6 },
];

export const Dussehra = ({ audio }: { audio: string | null }) => {
  const t = useCurrentFrame() / tl.fps;
  return (
    <AbsoluteFill style={{ background: "#000", color: "#fff", overflow: "hidden" }}>
      {t < SC.burn[1] && <World t={t} />}
      {t >= SC.varuna[0] && t < SC.varuna[1] && <VarunaCard t={t} />}
      {t >= SC.end[0] && <EndCard t={t} />}
      <Vignette strength={0.6} />
      <Grain opacity={0.1} />
      {audio && <Html5Audio src={staticFile(audio)} />}
    </AbsoluteFill>
  );
};

// ---------- the maidan: sky, effigy, crowd, fire ----------
const World = ({ t }: { t: number }) => {
  const cam = camera(t);
  const sh = shake(t, [HIT, HIT + 0.05, COLLAPSE, ...Q["burn.fireworks"].map((f) => f + 0.02)], 26, 7);
  const burn = clamp01((t - HIT) / 3);
  const fall = t > COLLAPSE ? Math.pow(t - COLLAPSE, 2) * 2200 : 0;
  const tilt = t > COLLAPSE ? (t - COLLAPSE) * 9 : 0;
  const frame = Math.round(t * tl.fps);
  const burning = BURN.map((e) => (e.head ? { ...e, y: e.y + (headFall(e.head, t)?.dy ?? 0) } : e));
  const labelsOn = Q["heads.labels"][0];
  const eyeGlow = t < HIT ? clamp01((t - labelsOn) / 0.6) : clamp01(1 - (t - HIT) / 0.5);
  const flashHit = clamp01(1 - (t - HIT) / 0.35) * (t >= HIT ? 1 : 0);
  const fadeOut = clamp01((t - (SC.burn[1] - 0.45)) / 0.45);
  const fireGlow = t < HIT ? 0.18 : 0.18 + 0.7 * clamp01((t - HIT) / 1.5) * (0.85 + 0.15 * Math.sin(t * 23) * Math.sin(t * 7));

  return (
    <AbsoluteFill>
      <FlameWarp id="flameWarp" frame={frame} />
      <Sky t={t} cam={cam} glow={fireGlow} />
      <AbsoluteFill
        style={{
          transform: `translate(${540 - cam.s * cam.cx + sh.x}px, ${960 - cam.s * cam.cy + sh.y}px) scale(${cam.s}) rotate(${sh.r}deg)`,
          transformOrigin: "0 0",
        }}
      >
        <div style={{ position: "absolute", inset: 0, transform: `translateY(${fall}px) rotate(${tilt}deg)`, transformOrigin: "540px 1780px" }}>
          <div style={{ position: "absolute", inset: 0, filter: `brightness(${0.8 - 0.55 * burn}) contrast(${1 + 0.25 * burn})` }}>
            <Effigy eyeGlow={eyeGlow} fall={(id) => headFall(id, t)} />
          </div>
          {/* warm light on the effigy: torches first, then the fire */}
          <div
            style={{
              position: "absolute",
              left: -200,
              top: 0,
              width: 1480,
              height: 1920,
              background: `radial-gradient(ellipse 70% 55% at 50% 85%, rgba(255,150,70,${0.25 + 0.6 * burn}) 0%, rgba(255,120,40,${0.1 + 0.4 * burn}) 50%, rgba(0,0,0,0) 100%)`,
              mixBlendMode: "multiply",
              opacity: 0.9,
            }}
          />
          <HeadTags t={t} />
          <Flames emitters={burning} t={t} warp="flameWarp" />
          {/* the arrow stays lodged in the effigy as it falls */}
          <Arrow t={t} />
        </div>
        <Smoke t={t} from={HIT + 0.6} x0={250} x1={830} y={700} amount={0.9 + fall / 600} />
        <Flames emitters={BONFIRE} t={t} warp="flameWarp" />
        <Torches t={t} />
        <Crowd t={t} glow={fireGlow} />
      </AbsoluteFill>

      {Q["burn.fireworks"].map((f, i) => (
        <Firework key={i} t={t} at={f} seed={i} x={160 + random(`fwx${i}`) * 760} y={170 + random(`fwy${i}`) * 300} />
      ))}
      <Embers t={t} from={HIT} amount={0.9} />
      <Reticle t={t} />
      <TextBand t={t} />
      <AbsoluteFill style={{ background: "#fff6e0", opacity: flashHit * 0.9, mixBlendMode: "screen" }} />
      <AbsoluteFill style={{ background: "#000", opacity: fadeOut }} />
    </AbsoluteFill>
  );
};

const Sky = ({ t, cam, glow }: { t: number; cam: { s: number; cy: number }; glow: number }) => {
  const par = (cam.cy - 1000) * 0.15;
  return (
    <AbsoluteFill style={{ background: "linear-gradient(180deg, #040406 0%, #0b0b0d 55%, #141210 100%)" }}>
      {Array.from({ length: 90 }, (_, i) => {
        const tw = 0.35 + 0.65 * Math.abs(Math.sin(t * (0.8 + random(`tw${i}`) * 2) + i));
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: random(`stx${i}`) * 1080,
              top: random(`sty${i}`) * 1100 - par,
              width: 2 + random(`sts${i}`) * 3,
              height: 2 + random(`sts${i}`) * 3,
              borderRadius: "50%",
              background: "#fff",
              opacity: tw * 0.7,
            }}
          />
        );
      })}
      <div style={{ position: "absolute", right: 120, top: 230 - par, width: 120, height: 120, borderRadius: "50%", boxShadow: "-26px 10px 0 0 #e9e9e9", opacity: 0.9 }} />
      <AbsoluteFill style={{ background: `radial-gradient(ellipse 90% 45% at 50% 95%, rgba(${FIRE.mid.join(",")},${glow * 0.55}) 0%, rgba(${FIRE.low.join(",")},${glow * 0.25}) 45%, rgba(0,0,0,0) 80%)` }} />
    </AbsoluteFill>
  );
};

const Torches = ({ t }: { t: number }) => (
  <>
    {TORCHES.map((e, i) => (
      <div key={i} style={{ position: "absolute", left: e.x - 9, top: e.y, width: 18, height: 200, background: "#3a3a3a", border: "3px solid #0d0d0d" }} />
    ))}
    <Flames emitters={TORCHES} t={t} />
  </>
);

/** Silhouetted crowd in the foreground, a few phones raised and filming. */
const Crowd = ({ t, glow }: { t: number; glow: number }) => {
  const people = [];
  for (let row = 0; row < 3; row++) {
    const n = 9 + row * 2;
    for (let i = 0; i < n; i++) {
      const s = 1 + row * 0.35;
      const x = (i + random(`cx${row}-${i}`) * 0.7) * (1300 / n) - 120;
      const y = 1700 + row * 85 + random(`cy${row}-${i}`) * 20;
      const bob = Math.sin(t * 3 + i * 1.3 + row) * 4;
      const phone = random(`ph${row}-${i}`) > 0.72 && row < 2;
      people.push(
        <g key={`${row}-${i}`} transform={`translate(${x}, ${y + bob}) scale(${s})`}>
          {phone && (
            <g>
              <rect x={22} y={-150} width={12} height={110} fill="#050505" transform="rotate(12 28 -40)" />
              <rect x={20} y={-205} width={44} height={74} rx={6} fill="#050505" stroke="#222" strokeWidth={2} transform="rotate(12 28 -40)" />
              <rect x={25} y={-199} width={34} height={60} rx={3} fill="#f4f4f4" opacity={0.85} transform="rotate(12 28 -40)" />
            </g>
          )}
          <circle cx={0} cy={0} r={32} fill="#050505" />
          <path d="M-70 140 C-70 60 -44 40 0 40 C44 40 70 60 70 140 Z" fill="#050505" />
        </g>,
      );
    }
  }
  return (
    <svg width={1080} height={1920} viewBox="0 0 1080 1920" style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}>
      <defs>
        <linearGradient id="rim" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor={`rgba(${FIRE.mid.join(",")},${0.35 * glow})`} />
          <stop offset="0.25" stopColor="rgba(0,0,0,0)" />
        </linearGradient>
      </defs>
      <rect x={-300} y={1760} width={1680} height={500} fill="#050505" />
      {people}
    </svg>
  );
};

const HeadTags = ({ t }: { t: number }) => (
  <>
    {LABEL_ORDER.map((id, k) => {
      const at = Q["heads.labels"][k];
      if (t < at) return null;
      const h = HEADS.find((x) => x.id === id)!;
      const burnAt = headIgnite(id) + 0.15;
      const gone = clamp01((t - burnAt) / 0.6);
      if (gone >= 1) return null;
      const char = `brightness(${1 - gone * 0.8}) sepia(${gone})`;
      if (id === "M")
        return (
          <Stamp key={id} t={t} at={at} size={56} kind="fill" rotate={-7} style={{ left: h.cx - 225, top: h.cy - 60, opacity: 1 - gone, filter: char }}>
            Propaganda
          </Stamp>
        );
      const idx = HEADS.findIndex((x) => x.id === id);
      const above = id === "T" ? null : idx % 2 === 1;
      const p = springAt(t, at, { damping: 11, stiffness: 320 });
      const style: CSSProperties =
        id === "T"
          ? { left: h.cx + 60, top: h.cy - 30 }
          : above
            ? { left: h.cx, top: h.cy - h.h / 2 - h.crown - 64, transform: `translateX(-50%) rotate(${-4 + (k % 3)}deg) scale(${p * (1 + gone * 0.2)})` }
            : { left: h.cx, top: h.cy + h.h / 2 + 62, transform: `translateX(-50%) rotate(${3 - (k % 3)}deg) scale(${p * (1 + gone * 0.2)})` };
      if (id === "T") style.transform = `rotate(-4deg) scale(${p})`;
      // the outermost tags hug the frame edge instead of centring on their head
      if (id === "L4") Object.assign(style, { left: 14, transform: `rotate(3deg) scale(${p})`, transformOrigin: "0 0" });
      if (id === "R4") Object.assign(style, { left: undefined, right: 14, transform: `rotate(3deg) scale(${p})`, transformOrigin: "100% 0" });
      return (
        <div
          key={id}
          style={{
            position: "absolute",
            ...display(32),
            lineHeight: 1,
            whiteSpace: "nowrap",
            background: "#fff",
            color: "#000",
            border: "3px solid #000",
            padding: "8px 12px",
            boxShadow: `6px 6px 0 ${C.shadow}`,
            opacity: 1 - gone,
            filter: char,
            ...style,
          }}
        >
          {HEADS[idx].label}
        </div>
      );
    })}
  </>
);

/** Target reticle that locks onto the navel before the shot (screen space, follows the camera). */
const Reticle = ({ t }: { t: number }) => {
  const a = Q["aim.text"];
  if (t < a || t > HIT + 0.05) return null;
  const cam = camera(t);
  const x = 540 + (NAVEL.x - cam.cx) * cam.s;
  const y = 960 + (NAVEL.y - cam.cy) * cam.s;
  const p = springAt(t, a, { damping: 14, stiffness: 120 });
  const r = 150 - 50 * p;
  const blink = Math.floor(t * 10) % 2 === 0 ? 1 : 0.55;
  return (
    <div style={{ position: "absolute", left: x - r, top: y - r, width: r * 2, height: r * 2, transform: `rotate(${(1 - p) * 90}deg) scale(${2.4 - 1.4 * p})`, opacity: blink }}>
      <div style={{ position: "absolute", inset: 0, borderRadius: "50%", border: "4px solid #fff" }} />
      <div style={{ position: "absolute", inset: r * 0.35, borderRadius: "50%", border: "3px dashed #fff" }} />
      {[0, 90, 180, 270].map((d) => (
        <div key={d} style={{ position: "absolute", left: r - 2, top: -30, width: 4, height: 50, background: "#fff", transform: `rotate(${d}deg)`, transformOrigin: `2px ${r + 30}px` }} />
      ))}
    </div>
  );
};

/** The flaming arrow: flies in from bottom-left and slows into the navel. */
const ARROW_FROM = { x: -260, y: 1900 };
const arrowAt = (u: number) => {
  const p = 1 - Math.pow(1 - u, 2.4);
  const x = ARROW_FROM.x + (NAVEL.x - ARROW_FROM.x) * p;
  const y = ARROW_FROM.y + (NAVEL.y - ARROW_FROM.y) * p - Math.sin(Math.PI * p) * 120;
  return { x, y };
};
const Arrow = ({ t }: { t: number }) => {
  if (t < TWANG) return null;
  const dur = HIT - TWANG;
  const u = clamp01((t - TWANG) / dur);
  const { x, y } = arrowAt(u);
  const prev = arrowAt(Math.max(0, u - 0.02));
  const ang = u >= 1 ? Math.atan2(NAVEL.y - arrowAt(0.97).y, NAVEL.x - arrowAt(0.97).x) : Math.atan2(y - prev.y, x - prev.x);
  const stuck = u >= 1;
  const trail = [];
  if (!stuck) {
    for (let k = 1; k <= 10; k++) {
      const q = arrowAt(Math.max(0, u - k * 0.025));
      const s = 46 * (1 - k / 11);
      trail.push(
        <div
          key={k}
          style={{
            position: "absolute",
            left: q.x - s / 2,
            top: q.y - s / 2,
            width: s,
            height: s,
            borderRadius: "50%",
            background: `radial-gradient(circle, rgba(${FIRE.hot.join(",")},${0.9 - k * 0.08}) 0%, rgba(${FIRE.low.join(",")},0) 70%)`,
            mixBlendMode: "screen",
          }}
        />,
      );
    }
  }
  const tipFire: Emitter[] = [{ x: 0, y: 0, ignite: TWANG, size: stuck ? 0 : 60, rise: 50, spread: 14, n: 5 }];
  return (
    <>
      {trail}
      <div style={{ position: "absolute", left: x, top: y, transform: `rotate(${ang}rad)`, transformOrigin: "0 0" }}>
        {/* shaft (tip at the origin, pointing +x) */}
        <div style={{ position: "absolute", left: -300, top: -5, width: 270, height: 10, background: "#e6e6e6", border: "2px solid #111" }} />
        <div style={{ position: "absolute", left: -44, top: -18, width: 0, height: 0, borderTop: "18px solid transparent", borderBottom: "18px solid transparent", borderLeft: "48px solid #f4f4f4" }} />
        {[-1, 1].map((s) => (
          <div key={s} style={{ position: "absolute", left: -310, top: s < 0 ? -30 : 4, width: 60, height: 26, background: "#cfcfcf", border: "2px solid #111", transform: `skewX(${s * 30}deg)` }} />
        ))}
        {!stuck && <Flames emitters={tipFire} t={t} warp="none" />}
      </div>
    </>
  );
};

// ---------- text ----------
const Band = ({ children, top = 1270 }: { children: ReactNode; top?: number }) => (
  <>
    <div style={{ position: "absolute", left: 0, right: 0, top: top - 120, height: 1920 - top + 120, background: "linear-gradient(180deg, rgba(0,0,0,0), rgba(0,0,0,.75) 30%, rgba(0,0,0,.85))" }} />
    <div style={{ position: "absolute", left: 70, right: 40, top, whiteSpace: "nowrap" }}>{children}</div>
  </>
);

const Tag = ({ t, at, children }: { t: number; at: number; children: ReactNode }) =>
  t < at ? <div style={{ height: 84 }} /> : (
    <div style={{ height: 84 }}>
      <span
        style={{
          ...label(48, 0.1),
          display: "inline-block",
          background: "#fff",
          color: "#000",
          padding: "10px 20px",
          boxShadow: `6px 6px 0 ${C.shadow}`,
          transform: `rotate(-2deg) scale(${0.6 + 0.4 * springAt(t, at, { damping: 10, stiffness: 300 })})`,
        }}
      >
        {children}
      </span>
    </div>
  );

const TextBand = ({ t }: { t: number }) => {
  const inScene = (k: keyof typeof SC) => t >= SC[k][0] && t < SC[k][1];
  if (inScene("open"))
    return (
      <Band>
        <Tag t={t} at={Q["open.l1"]}>Every Dussehra,</Tag>
        <div style={{ marginTop: 16 }}>
          <Slam w={{ text: "we burn", at: Q["open.l2"], size: 170 }} t={t} />
        </div>
        <div style={{ marginTop: 6 }}>
          <Slam w={{ text: "Ravana.", at: Q["open.l3"], size: 230, outlined: true }} t={t} />
        </div>
      </Band>
    );
  if (inScene("why")) {
    if (t < Q["why.l1"])
      return (
        <Band top={1330}>
          <Slam w={{ text: "Why?", at: Q["why.q"], size: 300 }} t={t} />
        </Band>
      );
    return (
      <Band>
        <Tag t={t} at={Q["why.l1"]}>To remember that</Tag>
        <div style={{ marginTop: 16 }}>
          <Slam w={{ text: "Truth", at: Q["why.l2"], size: 200, boxed: true }} t={t} />
        </div>
        <div style={{ marginTop: 10 }}>
          <Slam w={{ text: "always wins.", at: Q["why.l3"], size: 170 }} t={t} />
        </div>
      </Band>
    );
  }
  if (inScene("heads")) {
    const feed = t >= Q["heads.feed"];
    return (
      <Band top={1340}>
        {!feed ? (
          <>
            <Tag t={t} at={Q["heads.l1"]}>But this year,</Tag>
            <div style={{ marginTop: 16 }}>
              <Slam w={{ text: "Ravana has", at: Q["heads.l2"], size: 150 }} t={t} />
            </div>
            <div style={{ marginTop: 8 }}>
              <Slam w={{ text: "new heads.", at: Q["heads.l3"], size: 150, outlined: true }} t={t} />
            </div>
          </>
        ) : (
          <>
            <div style={{ height: 100 }} />
            <Slam w={{ text: "And he lives", at: Q["heads.feed"], size: 150 }} t={t} />
            <div style={{ marginTop: 8 }}>
              <Slam w={{ text: "in your feed.", at: Q["heads.feed"] + 0.3, size: 150, boxed: true }} t={t} />
            </div>
          </>
        )}
      </Band>
    );
  }
  if (inScene("aim"))
    return (
      <Band top={1420}>
        <Slam w={{ text: "Aim at", at: Q["aim.text"], size: 170 }} t={t} />
        <Slam w={{ text: "the lies.", at: Q["aim.text"] + 0.25, size: 170, outlined: true }} t={t} />
      </Band>
    );
  if (inScene("burn") && t >= Q["burn.t1"]) {
    const glow: CSSProperties = { textShadow: GLOW };
    if (t < Q["burn.t2"])
      return (
        <Band top={1380}>
          <Slam w={{ text: "Burn", at: Q["burn.t1"], size: 190 }} t={t} style={glow} />
          <Slam w={{ text: "Ravana.", at: Q["burn.t1"] + 0.3, size: 190 }} t={t} style={glow} />
        </Band>
      );
    return (
      <Band top={1230}>
        <Slam w={{ text: "Burn the", at: Q["burn.t2"], size: 150 }} t={t} style={glow} />
        <div style={{ marginTop: 6 }}>
          <Slam w={{ text: "propaganda", at: Q["burn.t3"], size: 172, boxed: true }} t={t} />
        </div>
        <div style={{ marginTop: 6 }}>
          <Slam w={{ text: "too.", at: Q["burn.t4"], size: 150 }} t={t} style={glow} />
        </div>
      </Band>
    );
  }
  return null;
};

// ---------- after the fire ----------
const VarunaCard = ({ t }: { t: number }) => {
  const mark = Q["varuna.mark"];
  const sh = shake(t, [mark], 20);
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse 80% 40% at 50% 100%, rgba(${FIRE.low.join(",")},.35), rgba(0,0,0,0) 70%)` }} />
      <div style={{ position: "absolute", inset: 0, transform: "translateY(700px)" }}>
        <Smoke t={t} from={SC.varuna[0] - 2} x0={0} x1={1080} y={1500} amount={0.7} n={18} />
      </div>
      <Embers t={t} from={SC.varuna[0] - 3} amount={0.8} />
      <AbsoluteFill style={{ transform: `translate(${sh.x}px, ${sh.y}px)` }}>
        <div style={{ position: "absolute", left: 70, top: 250, whiteSpace: "nowrap", display: "flex", flexDirection: "column", gap: 8 }}>
          <div><Slam w={{ text: "Before you", at: Q["varuna.l1"], size: 124 }} t={t} /></div>
          <div><Slam w={{ text: "believe it,", at: Q["varuna.l1"] + 0.2, size: 124, outlined: true }} t={t} /></div>
          <div style={{ marginTop: 14 }}><Slam w={{ text: "before you", at: Q["varuna.l2"], size: 124 }} t={t} /></div>
          <div><Slam w={{ text: "forward it,", at: Q["varuna.l2"] + 0.2, size: 124, outlined: true }} t={t} /></div>
        </div>
        <div style={{ position: "absolute", left: 0, right: 0, top: 860, display: "flex", justifyContent: "center", alignItems: "baseline" }}>
          {"VARUNA".split("").map((ch, i) => {
            const a = mark + i * 0.035;
            const p = springAt(t, a, { damping: 11, stiffness: 340 });
            return (
              <span
                key={i}
                style={{
                  ...display(166, 125),
                  lineHeight: 1,
                  display: "inline-block",
                  opacity: t >= a ? 1 : 0,
                  textShadow: `12px 12px 0 ${C.shadow}, ${GLOW}`,
                  transform: `translateY(${(1 - p) * -260}px) scale(${1.4 - 0.4 * p})`,
                }}
              >
                {ch}
              </span>
            );
          })}
        </div>
        <div style={{ position: "absolute", left: 0, right: 0, top: 1080, textAlign: "center" }}>
          <Slam w={{ text: "it.", at: mark + 0.3, size: 190, boxed: true }} t={t} style={{ marginRight: 0 }} />
        </div>
        <div style={{ position: "absolute", left: 72, top: 1060, height: 6, background: "#fff", width: 936 * clamp01((t - mark) / 0.3) }} />
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: 1310,
            textAlign: "center",
            ...label(34, 0.12),
            color: C.muted,
            opacity: clamp01((t - Q["varuna.sub"]) / 0.3),
          }}
        >
          Your fact checker for reels
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const EndCard = ({ t }: { t: number }) => {
  const ticket = Q["end.ticket"];
  const dm = Q["end.dm"];
  const drop = springAt(t, ticket, { damping: 11, stiffness: 200 });
  const dmIn = springAt(t, dm, { damping: 12, stiffness: 260 });
  const cyc = t > dm + 0.4 ? (t - dm - 0.4) % 1.2 : 1;
  const pressed = cyc < 0.12;
  const sh = shake(t, [ticket + 0.12, Q["end.final"]], 16);
  const live = 0.35 + 0.65 * Math.abs(Math.sin(t * 3.5));
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse 80% 35% at 50% 100%, rgba(${FIRE.low.join(",")},.3), rgba(0,0,0,0) 70%)` }} />
      <Firework t={t} at={SC.end[0] + 0.25} x={820} y={260} seed={11} />
      <Firework t={t} at={23.4} x={230} y={300} seed={12} />
      <Firework t={t} at={Q["end.final"]} x={600} y={240} seed={13} />
      <Embers t={t} from={SC.end[0] - 3} amount={0.7} />
      <AbsoluteFill style={{ transform: `translate(${sh.x}px, ${sh.y}px)` }}>
        <div style={{ position: "absolute", left: 70, top: 260, whiteSpace: "nowrap" }}>
          <Slam w={{ text: "Happy", at: Q["end.l1"], size: 150 }} t={t} />
          <br />
          <Slam w={{ text: "Dussehra", at: Q["end.l2"], size: 210, outlined: true }} t={t} style={{ textShadow: GLOW }} />
          <div
            style={{
              marginTop: 18,
              fontFamily: '"Nirmala UI", "Mangal", sans-serif',
              fontWeight: 700,
              fontSize: 64,
              color: `rgb(${FIRE.hot.join(",")})`,
              opacity: clamp01((t - Q["end.hindi"]) / 0.3),
              transform: `translateY(${(1 - clamp01((t - Q["end.hindi"]) / 0.3)) * 20}px)`,
            }}
          >
            शुभ विजयादशमी
          </div>
        </div>

        {/* ticket */}
        <div
          style={{
            position: "absolute",
            left: 70,
            top: 820,
            width: 940,
            height: 380,
            transform: `translateY(${(1 - drop) * -1200}px) rotate(${-4 + (1 - drop) * -10}deg)`,
            display: "flex",
            border: "5px solid #fff",
            background: "#000",
            boxShadow: `16px 16px 0 ${C.shadow}`,
          }}
        >
          <div style={{ width: 140, borderRight: "5px dashed #fff", display: "grid", placeItems: "center" }}>
            <div style={{ ...label(30, 0.3), transform: "rotate(-90deg)", whiteSpace: "nowrap" }}>Admit one</div>
          </div>
          <div style={{ flex: 1, padding: "32px 40px" }}>
            <div style={{ ...label(24, 0.1), display: "flex", alignItems: "center", gap: 14, color: C.muted, whiteSpace: "nowrap" }}>
              <span style={{ width: 16, height: 16, borderRadius: "50%", background: "#fff", opacity: live }} />
              varuna · your fact checker for reels
            </div>
            <div style={{ ...display(140), marginTop: 18, whiteSpace: "nowrap" }}>
              Invite <span style={outline(4)}>only</span>
            </div>
            <div style={{ marginTop: 14 }}>
              <span style={{ ...label(40, 0.12), background: "#fff", color: "#000", padding: "8px 18px" }}>· for now ·</span>
            </div>
          </div>
        </div>

        {t >= dm && (
          <div
            style={{
              position: "absolute",
              left: 70,
              top: 1310,
              width: 940,
              height: 150,
              background: "#fff",
              color: "#000",
              border: "5px solid #fff",
              boxShadow: pressed ? `2px 2px 0 ${C.shadow}` : `12px 12px 0 ${C.shadow}`,
              transform: `translate(${pressed ? 8 : 0}px, ${pressed ? 8 : 0}px) scale(${0.6 + 0.4 * dmIn})`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 26,
              ...display(84),
              fontFamily: FONT,
            }}
          >
            <Plane size={74} color="#000" stroke={6} />
            DM "varuna" for access
          </div>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
