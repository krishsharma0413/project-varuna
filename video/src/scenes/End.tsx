import { AbsoluteFill } from "remotion";
import { Plane } from "../components/icons";
import { Slam } from "../components/SlamWords";
import { C, clamp01, display, label, scene, shake, springAt, TL, words } from "../theme";

const [S] = scene("end");
const TICKET = TL.cues["end.ticket"];
const DM = TL.cues["end.dm"];
const IV = words("invite"); // Invite only for now DM us for access
const OUT = words("outro"); // Before you forward it Varuna it
const VARUNA = TL.cues["end.varuna"];

const TICKER = ["✕ False", "✓ True", "◐ Misleading", "? Unverified", "↻ Outdated", "— Not checkable"];

export const End = ({ t }: { t: number }) => {
  const local = t - S;
  const drop = springAt(t, TICKET, { damping: 11, stiffness: 200 });
  const dmIn = springAt(t, DM, { damping: 12, stiffness: 260 });
  // the button presses itself on a loop once it's in
  const cyc = t > DM + 0.4 ? (t - DM - 0.4) % 1.1 : 1;
  const pressed = cyc < 0.12;
  const sh = shake(t, [TICKET + 0.12, VARUNA], 16);
  const live = 0.35 + 0.65 * Math.abs(Math.sin(t * 3.5));

  return (
    <AbsoluteFill style={{ background: C.bg, overflow: "hidden" }}>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse 70% 40% at 50% 30%, rgba(255,255,255,.12), rgba(0,0,0,0) 70%)" }} />
      <AbsoluteFill style={{ transform: `translate(${sh.x}px, ${sh.y}px)` }}>
        {/* ticket */}
        <div
          style={{
            position: "absolute",
            left: 70,
            top: 230,
            width: 940,
            height: 420,
            transform: `translateY(${(1 - drop) * -900}px) rotate(${-4 + (1 - drop) * -10}deg)`,
            display: "flex",
            border: `5px solid ${C.fg}`,
            background: C.bg,
            boxShadow: `16px 16px 0 ${C.shadow}`,
          }}
        >
          <div style={{ width: 150, borderRight: `5px dashed ${C.fg}`, display: "grid", placeItems: "center" }}>
            <div style={{ ...label(32, 0.3), transform: "rotate(-90deg)", whiteSpace: "nowrap" }}>Admit one</div>
          </div>
          <div style={{ flex: 1, padding: "36px 40px", position: "relative" }}>
            <div style={{ ...label(30, 0.12), display: "flex", alignItems: "center", gap: 14, color: C.muted }}>
              <span style={{ width: 16, height: 16, borderRadius: "50%", background: C.fg, opacity: live }} />
              Status
            </div>
            <div style={{ marginTop: 18, whiteSpace: "nowrap" }}>
              <Slam w={{ text: "Invite", at: IV[0].t, size: 140 }} t={t} />
              <Slam w={{ text: "only", at: IV[1].t, size: 140, outlined: true }} t={t} />
            </div>
            <div style={{ marginTop: 14, opacity: t >= IV[2].t ? 1 : 0 }}>
              <span style={{ ...label(44, 0.12), background: C.fg, color: C.bg, padding: "8px 18px" }}>· for now ·</span>
            </div>
          </div>
        </div>

        {/* DM button */}
        {t >= DM && (
          <div
            style={{
              position: "absolute",
              left: 70,
              top: 760,
              width: 940,
              height: 150,
              background: C.fg,
              color: C.bg,
              border: `5px solid ${C.fg}`,
              boxShadow: pressed ? `2px 2px 0 ${C.shadow}` : `12px 12px 0 ${C.shadow}`,
              transform: `translate(${pressed ? 8 : 0}px, ${pressed ? 8 : 0}px) scale(${0.6 + 0.4 * dmIn})`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 26,
              ...display(84),
            }}
          >
            <Plane size={74} color="#000" stroke={6} />
            DM "varuna" for access
          </div>
        )}

        {/* sign-off */}
        <div style={{ position: "absolute", left: 70, top: 1040, whiteSpace: "nowrap" }}>
          <div>
            <Slam w={{ text: "Before", at: OUT[0].t, size: 150 }} t={t} />
            <Slam w={{ text: "you", at: OUT[1].t, size: 150 }} t={t} />
          </div>
          <div style={{ marginTop: 10 }}>
            <Slam w={{ text: "forward", at: OUT[2].t, size: 150, outlined: true }} t={t} />
            <Slam w={{ text: "it,", at: OUT[3].t, size: 150 }} t={t} />
          </div>
          <div style={{ marginTop: 18 }}>
            <Slam w={{ text: "Varuna", at: OUT[4].t, size: 210, boxed: true }} t={t} />
            <Slam w={{ text: "it.", at: OUT[5].t, size: 210 }} t={t} />
          </div>
        </div>
      </AbsoluteFill>

      {/* verdict ticker */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: 1620,
          height: 86,
          borderTop: `4px solid ${C.fg}`,
          borderBottom: `4px solid ${C.fg}`,
          overflow: "hidden",
          opacity: clamp01((local - 0.2) / 0.3),
        }}
      >
        {/* same trick as the site's .ticker-track: two copies, slide to -50%, loop */}
        <div style={{ display: "flex", width: "max-content", transform: `translateX(${-((local * 5) % 50)}%)`, whiteSpace: "nowrap" }}>
          {[...TICKER, ...TICKER, ...TICKER, ...TICKER].map((v, i) => (
            <span key={i} style={{ ...label(34, 0.06), padding: "22px 30px", display: "inline-flex", gap: 14, alignItems: "center", flexShrink: 0 }}>
              <b style={{ background: C.fg, color: C.bg, padding: "2px 12px" }}>{v.split(" ")[0]}</b>
              {v.slice(2)}
            </span>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};
