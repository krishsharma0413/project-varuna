import { AbsoluteFill, random } from "remotion";
import { Phone, PHONE_H, PHONE_W, SCREEN_H, SCREEN_W } from "../components/Phone";
import { ReelPost } from "../components/ReelPost";
import { Heart } from "../components/icons";
import { POSTS } from "../posts";
import { C, clamp01, ease, H, label, prog, scene, springAt, TL, W } from "../theme";

const [S, E] = scene("hook");
const SNAPS = TL.cues["hook.snaps"];
const SNAP_DUR = 0.22;
const FREE = SNAPS[SNAPS.length - 1];
const K = 10.5;
const POW = 2.6;

/** Feed position in "posts" (1 = one full screen scrolled). */
const feedPos = (t: number) => {
  let pos = 0;
  SNAPS.slice(0, -1).forEach((s) => {
    pos += ease(clamp01((t - s) / SNAP_DUR));
  });
  if (t > FREE) pos += K * Math.pow(t - FREE, POW);
  return pos;
};

const feedVel = (t: number) => (feedPos(t + 0.5 / 30) - feedPos(t - 0.5 / 30)) * 30;

const BUBBLES = [
  { text: "+99 new reels", x: 30, y: 300 },
  { text: "♥ 1.2M", x: 760, y: 470 },
  { text: "@you were tagged", x: 40, y: 1180 },
  { text: "trending · jantar mantar", x: 470, y: 1540 },
  { text: "12 new posts", x: 700, y: 900 },
  { text: "● LIVE now", x: 90, y: 760 },
  { text: "+1.4K comments", x: 560, y: 210 },
  { text: "shared 48K times", x: 120, y: 1620 },
  { text: "♥ 2.0M", x: 780, y: 1300 },
  { text: "you might like", x: 60, y: 520 },
];

export const Hook = ({ t }: { t: number }) => {
  const local = t - S;
  const pos = feedPos(local);
  const vel = feedVel(local);
  const speed = clamp01((local - FREE) / (E - S - FREE));

  // camera: slow push, then a shaky rush toward the screen
  const push = 0.9 + 0.06 * prog(local, 0, FREE, (x) => x) + 0.2 * Math.pow(speed, 2.2);
  const jitter = Math.pow(speed, 1.5) * 14;
  const jx = Math.sin(local * 97) * jitter;
  const jy = Math.cos(local * 71) * jitter;
  const tilt = 4 - 4 * prog(local, 0, 1.2) + Math.sin(local * 53) * speed * 1.5;

  const idx = Math.floor(pos);
  const frac = pos - idx;
  // light smear on the snaps; the heavy blur only builds once the feed runs away
  const blur = Math.min(vel * 2.5 + Math.pow(speed, 1.4) * 260, 280);
  const whiteout = clamp01((local - (E - S - 0.5)) / 0.5);

  return (
    <AbsoluteFill style={{ background: C.bg, overflow: "hidden" }}>
      {/* room light behind the phone */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 60% 45% at 50% 42%, rgba(255,255,255,${0.1 + speed * 0.25}) 0%, rgba(0,0,0,0) 70%)`,
        }}
      />
      <svg width={0} height={0} style={{ position: "absolute" }}>
        <filter id="vblur" x="0" y="-20%" width="100%" height="140%">
          <feGaussianBlur stdDeviation={`0 ${blur.toFixed(1)}`} />
        </filter>
      </svg>

      <div
        style={{
          position: "absolute",
          left: (W - PHONE_W) / 2,
          top: (H - PHONE_H) / 2,
          width: PHONE_W,
          height: PHONE_H,
          transform: `translate(${jx}px, ${jy}px) perspective(2400px) rotateX(${tilt}deg) scale(${push})`,
        }}
      >
        <Phone style={{ left: 0, top: 0 }}>
          <div style={{ position: "absolute", inset: 0, filter: blur > 1 ? "url(#vblur)" : undefined }}>
            {[0, 1].map((k) => {
              const i = idx + k;
              const post = POSTS[i % POSTS.length];
              const from = i === 0 ? 0 : SNAPS[i - 1];
              const live = i < SNAPS.length ? clamp01((local - from) / (SNAPS[i] - from)) : 0.6;
              return (
                <ReelPost
                  key={i}
                  post={post}
                  w={SCREEN_W}
                  h={SCREEN_H}
                  seed={i}
                  live={live}
                  style={{ top: (k - frac) * SCREEN_H }}
                />
              );
            })}
          </div>
          {/* streak glare when scrolling fast */}
          <div style={{ position: "absolute", inset: 0, background: "#fff", opacity: clamp01(speed * 0.5 + whiteout * 0.6), mixBlendMode: "screen" }} />
        </Phone>

        {/* touch indicator: a thumb flick before every snap */}
        {SNAPS.map((s, i) => {
          const a = s - 0.16;
          const p = clamp01((local - a) / 0.34);
          if (local < a || p >= 1) return null;
          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: PHONE_W / 2 - 50,
                top: PHONE_H * 0.72 - ease(p) * 520,
                width: 100,
                height: 100,
                borderRadius: "50%",
                background: "rgba(255,255,255,.5)",
                border: "3px solid #fff",
                opacity: 1 - p,
                transform: `scale(${1 - p * 0.3})`,
              }}
            />
          );
        })}
      </div>

      {/* notification bubbles piling up as the feed speeds up */}
      {BUBBLES.map((b, i) => {
        const at = FREE + 0.12 + i * 0.09;
        if (local < at) return null;
        const p = springAt(local, at, { damping: 10, stiffness: 300 });
        const dark = random(`b${i}`) > 0.5;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: b.x,
              top: b.y,
              ...label(30, 0.04),
              padding: "14px 22px",
              background: dark ? C.bg : C.fg,
              color: dark ? C.fg : C.bg,
              border: `3px solid ${C.fg}`,
              boxShadow: `6px 6px 0 ${C.shadow}`,
              transform: `scale(${p}) rotate(${(random(`r${i}`) - 0.5) * 8}deg)`,
              whiteSpace: "nowrap",
              display: "flex",
              gap: 10,
              alignItems: "center",
            }}
          >
            {b.text.startsWith("♥") ? (
              <>
                <Heart size={30} color={dark ? "#fff" : "#000"} fill={dark ? "#fff" : "#000"} stroke={4} />
                {b.text.slice(2)}
              </>
            ) : (
              b.text
            )}
          </div>
        );
      })}

      {/* speed lines across the whole frame */}
      {speed > 0.15 &&
        Array.from({ length: 26 }, (_, i) => {
          const x = random(`sl${i}`) * W;
          const len = 300 + random(`sll${i}`) * 900;
          const y = ((random(`sly${i}`) * H * 2 - local * 9000 * (0.5 + random(`slv${i}`))) % (H * 2) + H * 2) % (H * 2) - len;
          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: x,
                top: y,
                width: 2 + random(`slw${i}`) * 4,
                height: len,
                background: "linear-gradient(180deg, rgba(255,255,255,0), rgba(255,255,255,.9), rgba(255,255,255,0))",
                opacity: clamp01((speed - 0.15) * 1.6),
              }}
            />
          );
        })}

      <AbsoluteFill style={{ background: "#fff", opacity: whiteout * 0.95 }} />
    </AbsoluteFill>
  );
};
