import type { CSSProperties, ReactNode } from "react";
import { AbsoluteFill, random } from "remotion";
import { ReelPost } from "../components/ReelPost";
import { SCREEN_H, SCREEN_W } from "../components/Phone";
import { SlamLines } from "../components/SlamWords";
import { Stamp } from "../components/Stamp";
import { POSTS } from "../posts";
import { body, C, clamp01, display, FONT, kicks, label, outline, prog, scene, shake, TL, words } from "../theme";

const [RS] = scene("room");
const [CS, CE] = scene("creators");
const [SS, SE] = scene("still");
const CLICK = TL.cues["room.click"];
const STAMPS = TL.cues["creators.stamps"];
const ROOM_W = words("room"); // Was any of it true
const CR = words("creators"); // Creators may be paid or not They can be right or misleading
const ST = words("still"); // So should you still believe everything you see

const PIVOT = { x: 540, y: -60 };
const CORD = 600;

/** Bulb brightness: flickers on at the click, steady through the creators, dies during "still". */
const lightAt = (t: number) => {
  if (t < CLICK) return 0;
  const d = t - CLICK;
  if (d < 0.06) return 1;
  if (d < 0.12) return 0.05;
  if (d < 0.18) return 0.8;
  if (d < 0.22) return 0.2;
  if (t < SS) return 1;
  const p = clamp01((t - SS) / (SE - SS));
  const f = Math.floor(t * 30);
  const flick = random(`fl${f}`) < 0.12 + p * 0.35 ? 0.25 : 1;
  return Math.max(0.06, (1 - 0.82 * p) * flick);
};

const swingAt = (t: number) => {
  const d = Math.max(0, t - CLICK);
  return 0.32 * Math.cos((d / 2.6) * Math.PI * 2) * Math.exp(-d * 0.1);
};

export const Room = ({ t }: { t: number }) => {
  const light = lightAt(t);
  const theta = swingAt(t);
  const inCreators = t >= CS && t < CE;
  const inStill = t >= SS;

  if (inCreators) return <DeskTop t={t} light={light} />;

  const push = inStill ? 1 + 0.14 * prog(t, SS, SE - SS, (x) => x) : 1 + 0.03 * prog(t, RS, 2);
  return (
    <AbsoluteFill style={{ background: C.bg, overflow: "hidden" }}>
      <AbsoluteFill style={{ transform: `scale(${push})`, transformOrigin: "50% 40%" }}>
        <WallView light={light} theta={theta} t={t} />
      </AbsoluteFill>
      {!inStill ? <RoomLine t={t} /> : <StillLine t={t} />}
    </AbsoluteFill>
  );
};

const WallView = ({ light, theta, t }: { light: number; theta: number; t: number }) => {
  const bx = PIVOT.x + Math.sin(theta) * CORD;
  const poolX = PIVOT.x + Math.sin(theta) * 1500;
  return (
    <AbsoluteFill>
      {/* wall */}
      <AbsoluteFill style={{ background: "repeating-linear-gradient(90deg, #121212 0 118px, #0d0d0d 118px 120px)" }} />
      {/* desk */}
      <div style={{ position: "absolute", left: -100, right: -100, top: 1290, bottom: 0, perspective: 1100 }}>
        <div
          style={{
            position: "absolute",
            inset: 0,
            transform: "rotateX(52deg)",
            transformOrigin: "50% 0%",
            background: "repeating-linear-gradient(8deg, #1d1d1d 0 9px, #181818 9px 22px)",
            borderTop: "6px solid #333",
          }}
        >
          <Folder x={140} y={60} r={-7} labelText="Records" />
          <Folder x={560} y={120} r={5} labelText="Court order" />
          <Sheet x={360} y={330} r={-2} title="Gazette notification" />
          <Folder x={720} y={420} r={-4} labelText="Fact-check" />
          <Sheet x={60} y={460} r={8} title="FIR no. 0412/26" />
        </div>
      </div>

      {/* cone of light + dust, swinging with the bulb */}
      <div style={{ position: "absolute", left: PIVOT.x, top: PIVOT.y, transform: `rotate(${-theta}rad)`, transformOrigin: "0 0" }}>
        <div
          style={{
            position: "absolute",
            left: -760,
            top: CORD + 40,
            width: 1520,
            height: 1700,
            clipPath: "polygon(47% 0, 53% 0, 100% 100%, 0 100%)",
            background: `linear-gradient(180deg, rgba(255,255,255,${0.32 * light}) 0%, rgba(255,255,255,${0.07 * light}) 60%, rgba(255,255,255,0) 100%)`,
          }}
        />
        {Array.from({ length: 46 }, (_, i) => {
          const depth = random(`dy${i}`);
          const y = CORD + 120 + depth * 1300;
          const spread = ((y - CORD) / 1700) * 700;
          const x = (random(`dx${i}`) - 0.5) * 2 * spread + Math.sin(t * 0.7 + i) * 18;
          const dy = ((t * (12 + random(`dv${i}`) * 20)) % 60) - 30;
          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: x,
                top: y + dy,
                width: 3 + random(`ds${i}`) * 5,
                height: 3 + random(`ds${i}`) * 5,
                borderRadius: "50%",
                background: "#fff",
                opacity: light * (0.15 + 0.5 * random(`do${i}`)) * (1 - depth * 0.6),
              }}
            />
          );
        })}
      </div>

      {/* darkness: everything outside the pool of light falls off to black */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 760px 900px at ${poolX}px 1450px, rgba(0,0,0,0) 0%, rgba(0,0,0,.5) 45%, rgba(0,0,0,.96) 100%)`,
        }}
      />
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle 420px at ${bx}px ${PIVOT.y + Math.cos(theta) * CORD + 70}px, rgba(255,255,255,${0.16 * light}) 0%, rgba(255,255,255,0) 100%)`,
        }}
      />
      <AbsoluteFill style={{ background: "#000", opacity: 1 - light }} />

      {/* cord, socket, bulb: drawn above the darkness so the bulb is the brightest thing in the room */}
      <div style={{ position: "absolute", left: PIVOT.x, top: PIVOT.y, transform: `rotate(${-theta}rad)`, transformOrigin: "0 0" }}>
        <div style={{ position: "absolute", left: -2, top: 0, width: 4, height: CORD - 40, background: "#2a2a2a" }} />
        <div style={{ position: "absolute", left: -26, top: CORD - 44, width: 52, height: 64, background: "#1e1e1e", borderRadius: "6px 6px 2px 2px" }} />
        <div
          style={{
            position: "absolute",
            left: -48,
            top: CORD + 14,
            width: 96,
            height: 112,
            borderRadius: "48% 48% 50% 50% / 40% 40% 60% 60%",
            background: `radial-gradient(circle at 50% 55%, rgba(255,255,255,1) 0%, rgba(${Math.round(40 + 215 * light)},${Math.round(40 + 215 * light)},${Math.round(40 + 215 * light)},1) 45%, #2a2a2a 100%)`,
            opacity: 0.35 + 0.65 * light,
            boxShadow: `0 0 ${60 + 140 * light}px ${20 + 60 * light}px rgba(255,255,255,${0.55 * light})`,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};

const Folder = ({ x, y, r, labelText }: { x: number; y: number; r: number; labelText: string }) => (
  <div style={{ position: "absolute", left: x, top: y, width: 380, height: 250, transform: `rotate(${r}deg)` }}>
    <div style={{ position: "absolute", left: 0, top: -26, width: 150, height: 34, background: "#8f8f8f", borderRadius: "8px 8px 0 0" }} />
    <div style={{ position: "absolute", inset: 0, background: "#9c9c9c", boxShadow: "0 18px 30px rgba(0,0,0,.6)" }} />
    <div style={{ position: "absolute", left: 18, top: -12, right: 18, height: 40, background: "#e8e8e8" }} />
    <div
      style={{
        position: "absolute",
        left: 34,
        top: 60,
        padding: "8px 16px",
        border: "3px solid #111",
        fontFamily: FONT,
        fontWeight: 800,
        fontStretch: "100%",
        fontSize: 32,
        letterSpacing: ".12em",
        textTransform: "uppercase",
        color: "#111",
        background: "#cfcfcf",
      }}
    >
      {labelText}
    </div>
    <div style={{ position: "absolute", left: 34, top: 140, width: 220, height: 10, background: "#7a7a7a" }} />
    <div style={{ position: "absolute", left: 34, top: 166, width: 160, height: 10, background: "#7a7a7a" }} />
  </div>
);

const Sheet = ({ x, y, r, title, w = 320 }: { x: number; y: number; r: number; title: string; w?: number }) => (
  <div
    style={{
      position: "absolute",
      left: x,
      top: y,
      width: w,
      height: w * 1.3,
      transform: `rotate(${r}deg)`,
      background: "#ededed",
      boxShadow: "0 14px 26px rgba(0,0,0,.6)",
      padding: 26,
    }}
  >
    <div style={{ ...label(20, 0.1), color: "#111", borderBottom: "3px solid #111", paddingBottom: 8, marginBottom: 16 }}>{title}</div>
    {Array.from({ length: 11 }, (_, i) => (
      <div key={i} style={{ height: 8, marginBottom: 14, width: `${60 + random(`${title}${i}`) * 40}%`, background: "#9a9a9a" }} />
    ))}
  </div>
);

/** "Was any of it true?" typed out under the bulb. */
const RoomLine = ({ t }: { t: number }) => {
  const text = "WAS ANY OF IT TRUE?";
  // reveal each word's letters across that word's spoken duration
  const bounds: [number, number][] = [];
  let i = 0;
  text.split(" ").forEach((wd, k) => {
    bounds.push([i, i + wd.length]);
    i += wd.length + 1;
  });
  let shown = 0;
  bounds.forEach(([a, b], k) => {
    const st = ROOM_W[k]?.t ?? 0;
    const en = ROOM_W[k + 1]?.t ?? st + 0.3;
    const p = clamp01((t - st) / Math.max(0.08, en - st - 0.04));
    if (p > 0) shown = Math.max(shown, a + Math.ceil((b - a) * p) + (p >= 1 ? 1 : 0));
  });
  const caret = Math.floor(t * 4) % 2 === 0;
  const chars = text.slice(0, shown);
  const anyStart = 4;
  return (
    <div style={{ position: "absolute", left: 76, right: 60, top: 820 }}>
      <div style={{ ...display(176), color: C.fg, whiteSpace: "pre-wrap" }}>
        {chars.split("").map((ch, k) => (
          <span key={k} style={k >= anyStart && k < anyStart + 3 ? outline(4) : undefined}>
            {k === 7 ? "\n" : ch}
          </span>
        ))}
        {t > CLICK + 0.2 && <span style={{ display: "inline-block", width: 70, height: 140, marginLeft: 8, background: caret ? C.fg : "transparent", verticalAlign: "-8px" }} />}
      </div>
    </div>
  );
};

/** Top-down desk: printed reels, case files, a wandering pool of light, stamps on the words. */
const DeskTop = ({ t, light }: { t: number; light: number }) => {
  const local = t - CS;
  const enter = prog(local, 0, 0.35);
  const dx = Math.sin(local * 0.45) * 40;
  const dy = Math.cos(local * 0.35) * 30 - local * 10;
  const rot = -2 + local * 0.5;
  const poolX = 540 + Math.sin(local * 1.4) * 260;
  const poolY = 960 + Math.cos(local * 1.1) * 160;
  const sh = shake(t, STAMPS, 16);
  const theyAt = CR[6].t;
  const older = (i: number) => (i < 2 && t >= theyAt ? 0.3 : 1);

  return (
    <AbsoluteFill style={{ background: "#000", overflow: "hidden" }}>
      <AbsoluteFill
        style={{
          transform: `translate(${dx + sh.x}px, ${dy + sh.y}px) rotate(${rot + sh.r}deg) scale(${1.5 - 0.42 * enter})`,
          transformOrigin: "50% 50%",
        }}
      >
        <div style={{ position: "absolute", left: -300, top: -300, right: -300, bottom: -300, background: "repeating-linear-gradient(12deg, #1c1c1c 0 11px, #171717 11px 26px)" }} />
        <Placed x={-60} y={180} r={-9}>
          <Folder x={0} y={0} r={0} labelText="Records" />
        </Placed>
        <Placed x={640} y={140} r={11}>
          <Sheet x={0} y={0} r={0} title="Gazette notification" w={360} />
        </Placed>
        <Placed x={620} y={1420} r={6}>
          <Folder x={0} y={0} r={0} labelText="Court order" />
        </Placed>
        <Polaroid x={70} y={620} r={-6} post={0} />
        <Polaroid x={560} y={560} r={8} post={1} />
        <Polaroid x={300} y={1180} r={-3} post={3} />
        <Placed x={40} y={1560} r={-14}>
          <div style={{ width: 420, height: 18, background: "#d0d0d0", borderRadius: 9 }} />
        </Placed>
      </AbsoluteFill>

      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 720px 820px at ${poolX}px ${poolY}px, rgba(0,0,0,0) 0%, rgba(0,0,0,.45) 50%, rgba(0,0,0,.95) 100%)`,
        }}
      />
      <AbsoluteFill style={{ background: "#000", opacity: (1 - light) + (1 - enter) * 0.6 }} />

      {/* caption */}
      <div style={{ position: "absolute", left: 72, top: 190, ...label(58, 0.1), color: C.fg, display: "flex", gap: 18, alignItems: "center" }}>
        {t >= CR[0].t && t < theyAt && <Caption>Creators may be…</Caption>}
        {t >= theyAt && <Caption>They can be…</Caption>}
      </div>

      <Stamp t={t} at={STAMPS[0]} rotate={-7} size={120} style={{ left: 90, top: 400, opacity: older(0) }}>
        Paid?
      </Stamp>
      <Stamp t={t} at={STAMPS[1]} rotate={5} size={104} kind="fill" style={{ left: 400, top: 640, opacity: older(1) }}>
        Or not.
      </Stamp>
      <Stamp t={t} at={STAMPS[2]} rotate={4} size={120} kind="dashed" style={{ left: 110, top: 1010 }}>
        Right?
      </Stamp>
      <Stamp t={t} at={STAMPS[3]} rotate={-4} size={80} kind="double" style={{ left: 60, top: 1330 }}>
        ◐ Misleading?
      </Stamp>
    </AbsoluteFill>
  );
};

const Caption = ({ children }: { children: ReactNode }) => (
  <span style={{ display: "inline-flex", gap: 16, alignItems: "center", background: "rgba(0,0,0,.6)", padding: "10px 18px", border: `3px solid ${C.fg}` }}>
    <span style={{ width: 16, height: 16, borderRadius: "50%", background: C.fg }} />
    {children}
  </span>
);

const Placed = ({ x, y, r, children, style }: { x: number; y: number; r: number; children: ReactNode; style?: CSSProperties }) => (
  <div style={{ position: "absolute", left: x, top: y, transform: `rotate(${r}deg)`, ...style }}>{children}</div>
);

const PHOTO = 0.4;
const Polaroid = ({ x, y, r, post }: { x: number; y: number; r: number; post: number }) => (
  <Placed x={x} y={y} r={r}>
    <div style={{ background: "#efefef", padding: "16px 16px 64px", boxShadow: "0 22px 40px rgba(0,0,0,.7)" }}>
      <div style={{ width: SCREEN_W * PHOTO, height: SCREEN_H * PHOTO, position: "relative", overflow: "hidden" }}>
        <div style={{ transform: `scale(${PHOTO})`, transformOrigin: "0 0", position: "absolute" }}>
          <ReelPost post={POSTS[post]} w={SCREEN_W} h={SCREEN_H} seed={post} live={0.7} blurClaim={26} />
        </div>
      </div>
      <div style={{ ...body(24), color: "#333", marginTop: 12, fontStyle: "normal" }}>@{POSTS[post].handle}</div>
    </div>
  </Placed>
);

/** "So, should you still believe everything you see?" — the callback, as the light dies. */
const StillLine = ({ t }: { t: number }) => {
  const at = (i: number) => ST[i].t;
  const punch = 1 + kicks(t, [at(1), at(3), at(4), at(7)], 11) * 0.05;
  const flickerStill = t > at(3) + 0.25 && random(`st${Math.floor(t * 30)}`) < 0.18 ? 0.3 : 1;
  return (
    <div style={{ position: "absolute", left: 72, top: 760, transform: `scale(${punch})`, transformOrigin: "20% 50%" }}>
      <SlamLines
        t={t}
        gap={12}
        lines={[
          [
            { text: "So,", at: at(0), size: 150 },
            { text: "should", at: at(1), size: 150 },
            { text: "you", at: at(2), size: 150 },
          ],
          [{ text: "still", at: at(3), size: 340, outlined: true, dim: flickerStill }],
          [{ text: "believe", at: at(4), size: 150 }],
          [{ text: "everything", at: at(5), size: 150 }],
          [
            { text: "you", at: at(6), size: 150 },
            { text: "see?", at: at(7), size: 150, boxed: true },
          ],
        ]}
      />
    </div>
  );
};
