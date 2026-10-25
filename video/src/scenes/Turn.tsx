import { AbsoluteFill } from "remotion";
import { Slam } from "../components/SlamWords";
import { C, clamp01, display, label, scene, shake, springAt, TL, words } from "../theme";

const [S] = scene("turn");
const TW = words("turn"); // Why not fact-check it with Varuna once
const MARK = TL.cues["turn.wordmark"];

export const Turn = ({ t }: { t: number }) => {
  const local = t - S;
  const flash = 1 - clamp01(local / 0.45);
  const sh = shake(t, [S, MARK], 22);
  const at = (i: number) => TW[i].t;

  return (
    <AbsoluteFill style={{ background: C.bg, overflow: "hidden" }}>
      {/* dot grid + spotlight */}
      <AbsoluteFill
        style={{
          background: "radial-gradient(circle, #2a2a2a 0 2.5px, transparent 3px) 0 0 / 36px 36px",
          maskImage: "radial-gradient(ellipse 70% 55% at 50% 50%, #000 0%, transparent 100%)",
          opacity: clamp01(local / 0.6),
        }}
      />
      <AbsoluteFill style={{ background: "radial-gradient(ellipse 55% 40% at 50% 52%, rgba(255,255,255,.14), rgba(0,0,0,0) 70%)" }} />

      <AbsoluteFill style={{ transform: `translate(${sh.x}px, ${sh.y}px) rotate(${sh.r}deg)` }}>
        <div style={{ position: "absolute", left: 72, top: 470, whiteSpace: "nowrap" }}>
          <Slam w={{ text: "Why", at: at(0), size: 132 }} t={t} />
          <Slam w={{ text: "not", at: at(1), size: 132 }} t={t} />
          <br />
          <Slam w={{ text: "fact-check", at: at(2), size: 132, outlined: true }} t={t} />
          <Slam w={{ text: "it", at: at(3), size: 132 }} t={t} />
        </div>

        {/* wordmark: letters drop in on "Varuna" */}
        <div style={{ position: "absolute", left: 0, right: 0, top: 830, display: "flex", justifyContent: "center" }}>
          {"VARUNA".split("").map((ch, i) => {
            const a = MARK + i * 0.035;
            const p = springAt(t, a, { damping: 11, stiffness: 340 });
            return (
              <span
                key={i}
                style={{
                  ...display(166, 125),
                  lineHeight: 1,
                  color: C.fg,
                  textShadow: `14px 14px 0 ${C.shadow}`,
                  display: "inline-block",
                  opacity: t >= a ? 1 : 0,
                  transform: `translateY(${(1 - p) * -260}px) scale(${1.4 - 0.4 * p})`,
                  letterSpacing: "-0.02em",
                }}
              >
                {ch}
              </span>
            );
          })}
        </div>
        <div style={{ position: "absolute", left: 0, right: 0, top: 1110, textAlign: "center" }}>
          <Slam w={{ text: "once?", at: at(6), size: 190, boxed: true }} t={t} style={{ marginRight: 0 }} />
        </div>
        {t > MARK + 0.3 && (
          <div
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              top: 1360,
              textAlign: "center",
              ...label(28, 0.1),
              color: C.muted,
              opacity: clamp01((t - MARK - 0.3) / 0.3),
            }}
          >
            The fact checker for the reels in your feed
          </div>
        )}
      </AbsoluteFill>

      {/* rule lines sweeping in under the wordmark */}
      <div style={{ position: "absolute", left: 72, top: 1090, height: 6, background: C.fg, width: 936 * clamp01((t - MARK) / 0.3) }} />
      <div style={{ position: "absolute", left: 72, top: 1330, height: 3, background: C.soft2, width: 936 * clamp01((t - MARK - 0.2) / 0.3) }} />

      <AbsoluteFill style={{ background: "#fff", opacity: flash }} />
    </AbsoluteFill>
  );
};
