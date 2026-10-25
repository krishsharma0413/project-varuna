import type { ReactNode } from "react";
import { AbsoluteFill } from "remotion";
import { body, C, clamp01, display, label, scene, springAt, TL } from "../theme";

const [S, E] = scene("pipeline");
const CARDS = TL.cues["pipeline.cards"];

const STEPS = [
  { title: "Reads it", sub: "Speech, caption and on-screen text." },
  { title: "Splits claims", sub: "Opinions are marked, not judged." },
  { title: "Checks sources", sub: "Records → fact-checkers → ranked web." },
  { title: "Stamps a verdict", sub: "With sources and a re-check date." },
];

export const Pipeline = ({ t }: { t: number }) => {
  const exit = clamp01((t - (E - 0.12)) / 0.12);
  return (
    <AbsoluteFill style={{ background: C.bg, overflow: "hidden" }}>
      <AbsoluteFill
        style={{
          background: "linear-gradient(#141414 2px, transparent 2px) 0 0 / 100% 120px, linear-gradient(90deg, #141414 2px, transparent 2px) 0 0 / 120px 100%",
        }}
      />
      <div style={{ position: "absolute", left: 60, top: 150, ...label(40, 0.12), color: C.fg, display: "flex", gap: 16, alignItems: "center" }}>
        <span style={{ width: 18, height: 18, borderRadius: "50%", background: C.fg, opacity: 0.4 + 0.6 * Math.abs(Math.sin(t * 4)) }} />
        How varuna works
      </div>
      {STEPS.map((s, i) => {
        const at = CARDS[i];
        if (t < at) return null;
        const p = springAt(t, at, { damping: 15, stiffness: 220 });
        const from = i % 2 ? 1 : -1;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: 60,
              top: 260 + i * 350,
              width: 940,
              height: 310,
              border: `5px solid ${C.fg}`,
              background: C.bg,
              boxShadow: `14px 14px 0 ${C.shadow}`,
              transform: `translateX(${(1 - p) * from * 1200 + exit * from * -40}px) rotate(${(1 - p) * from * 6}deg)`,
              opacity: 1 - exit,
              display: "flex",
              alignItems: "center",
              padding: "0 36px",
              gap: 30,
            }}
          >
            <div style={{ ...display(230, 125), lineHeight: 0.8, width: 170 }}>{i + 1}</div>
            <div style={{ flex: 1 }}>
              <div style={{ ...display(86) }}>{s.title}</div>
              <div style={{ ...body(28), color: C.muted, marginTop: 12 }}>{s.sub}</div>
            </div>
            <Icon i={i} t={t - at} />
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

const Box = ({ children }: { children: ReactNode }) => (
  <div style={{ width: 200, height: 200, border: `3px solid ${C.fg}`, position: "relative", overflow: "hidden", flex: "none" }}>{children}</div>
);

const Icon = ({ i, t }: { i: number; t: number }) => {
  if (i === 0)
    return (
      <Box>
        <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
          {Array.from({ length: 9 }, (_, k) => (
            <div key={k} style={{ width: 12, height: 20 + Math.abs(Math.sin(t * 9 + k * 0.9)) * 120, background: C.fg }} />
          ))}
        </div>
      </Box>
    );
  if (i === 1) {
    const p = clamp01(t / 0.4);
    return (
      <Box>
        {[0, 1, 2].map((k) => (
          <div
            key={k}
            style={{
              position: "absolute",
              left: 24,
              top: 40 + k * 46 + (k - 1) * p * 10,
              width: 150 - k * 20,
              height: 30,
              background: k === 1 ? "transparent" : C.fg,
              border: `3px solid ${C.fg}`,
              transform: `translateX(${(k - 1) * p * 14}px)`,
            }}
          />
        ))}
      </Box>
    );
  }
  if (i === 2)
    return (
      <Box>
        {["T1", "T2", "T3"].map((tier, k) => {
          const on = t > 0.12 + k * 0.14;
          return (
            <div
              key={tier}
              style={{
                position: "absolute",
                left: 22,
                right: 22,
                top: 22 + k * 56,
                height: 44,
                border: `3px solid ${C.fg}`,
                background: on ? C.fg : "transparent",
                color: on ? C.bg : C.fg,
                ...label(24, 0.04),
                display: "flex",
                alignItems: "center",
                paddingLeft: 10,
              }}
            >
              {tier}
            </div>
          );
        })}
      </Box>
    );
  const p = springAt(t, 0.05, { damping: 12, stiffness: 300 });
  return (
    <Box>
      <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center" }}>
        <div style={{ ...display(120, 125), lineHeight: 1, border: `8px double ${C.fg}`, padding: "0 16px", transform: `rotate(-6deg) scale(${2 - p})` }}>◐</div>
      </div>
    </Box>
  );
};
