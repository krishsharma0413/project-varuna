import { AbsoluteFill } from "remotion";
import { Phone, PHONE_H, PHONE_W } from "../components/Phone";
import { Slam } from "../components/SlamWords";
import { body, C, clamp01, display, FONT, label, outline, scene, springAt, TL, words } from "../theme";

const [S, E] = scene("paste");
const PASTE = TL.cues["paste.paste"];
const PRESS = TL.cues["paste.press"];
const PW = words("paste");
const URL = "instagram.com/reel/C9xJantarM4/";
const STAGES = ["Queued", "Checking topic", "Downloading", "Reading the reel", "Checking claims"];
const SCALE = 0.8;

export const Paste = ({ t }: { t: number }) => {
  const local = t - S;
  const rise = springAt(t, S, { damping: 16, stiffness: 160 });
  const pasted = t >= PASTE;
  const flash = pasted ? 1 - clamp01((t - PASTE) / 0.35) : 0;
  const pressed = t >= PRESS && t < PRESS + 0.14;
  const stagesP = clamp01((t - PRESS - 0.15) / (E - PRESS - 0.1));
  const exit = clamp01((t - (E - 0.15)) / 0.15);

  // finger: hovers over the input, taps it, then moves to the button
  const toBtn = clamp01((t - (PASTE + 0.15)) / 0.3);
  // positions in phone (unscaled) coordinates: the input, then the button
  const fx = 430 - toBtn * 230;
  const fy = 780 + toBtn * 135;
  const tap = (t > PASTE - 0.05 && t < PASTE + 0.1) || pressed;

  return (
    <AbsoluteFill style={{ background: C.bg, overflow: "hidden" }}>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse 60% 40% at 50% 60%, rgba(255,255,255,.12), rgba(0,0,0,0) 70%)" }} />
      <div style={{ position: "absolute", left: 72, top: 120, whiteSpace: "nowrap" }}>
        <Slam w={{ text: "Paste", at: PW[0].t, size: 110 }} t={t} />
        <Slam w={{ text: "any", at: PW[1].t, size: 110 }} t={t} />
        <Slam w={{ text: "reel", at: PW[2].t, size: 110, outlined: true }} t={t} />
        <Slam w={{ text: "link", at: PW[3].t, size: 110, boxed: true }} t={t} />
      </div>

      <div
        style={{
          position: "absolute",
          left: (1080 - PHONE_W * SCALE) / 2,
          top: 330,
          width: PHONE_W,
          height: PHONE_H,
          transform: `translateY(${(1 - rise) * 1300 - exit * 80}px) scale(${SCALE})`,
          transformOrigin: "0 0",
          opacity: 1 - exit,
        }}
      >
        <Phone style={{ left: 0, top: 0 }}>
          <div style={{ position: "absolute", inset: 0, background: "#000", color: "#fff" }}>
            {/* nav */}
            <div style={{ position: "absolute", top: 100, left: 0, right: 0, height: 100, borderBottom: "4px solid #fff", display: "flex", alignItems: "center", padding: "0 44px", justifyContent: "space-between" }}>
              <span style={{ ...display(54, 125), lineHeight: 1 }}>Varuna</span>
              <span style={{ ...label(24, 0.04), border: "3px solid #fff", padding: "8px 14px" }}>Check a reel</span>
            </div>
            <div style={{ position: "absolute", top: 250, left: 44, right: 44 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
                <span style={{ width: 84, height: 84, borderRadius: "50%", background: "#fff", color: "#000", display: "grid", placeItems: "center", fontFamily: FONT, fontWeight: 900, fontSize: 30 }}>01</span>
              </div>
              <div style={{ ...display(150), marginTop: 26 }}>
                Check <span style={outline(4)}>a reel</span>
              </div>
              <p style={{ ...body(30), color: C.muted, marginTop: 24 }}>
                Paste an Instagram reel link. We download it, read everything it says, and check each claim against ranked sources.
              </p>
              <div style={{ ...label(24, 0.05), marginTop: 44, marginBottom: 12 }}>Reel link</div>
              <div style={{ height: 110, border: "4px solid #fff", display: "flex", alignItems: "center", padding: "0 26px", ...body(32), overflow: "hidden", whiteSpace: "nowrap" }}>
                {pasted ? (
                  <span style={{ background: flash > 0 ? `rgba(255,255,255,${flash})` : "transparent", color: flash > 0.5 ? "#000" : "#fff" }}>https://www.{URL}</span>
                ) : (
                  <span style={{ color: C.soft2 }}>https://www.instagram.com/reel/…</span>
                )}
                {!pasted && Math.floor(local * 4) % 2 === 0 && <span style={{ width: 3, height: 44, background: "#fff", marginLeft: 4 }} />}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 22, marginTop: 34 }}>
                <div
                  style={{
                    ...label(30, 0.04),
                    height: 92,
                    padding: "0 34px",
                    display: "flex",
                    alignItems: "center",
                    background: "#fff",
                    color: "#000",
                    border: "4px solid #fff",
                    boxShadow: pressed ? `1px 1px 0 ${C.shadow}` : `8px 8px 0 ${C.shadow}`,
                    transform: pressed ? "translate(4px, 4px)" : "none",
                  }}
                >
                  {t >= PRESS ? "Submitting…" : "Start check"}
                </div>
              </div>
              {/* job stages */}
              <div style={{ marginTop: 56 }}>
                {STAGES.map((s, i) => {
                  const done = stagesP * STAGES.length > i + 1;
                  const active = !done && stagesP * STAGES.length > i;
                  return (
                    <div
                      key={s}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 20,
                        padding: "18px 0",
                        borderTop: `3px solid ${done || active ? "#fff" : "#333"}`,
                        ...label(28, 0.04),
                        color: done || active ? "#fff" : "#555",
                      }}
                    >
                      <span style={{ width: 34, textAlign: "center" }}>{done ? "✓" : active ? "●" : "·"}</span>
                      {s}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </Phone>
        {/* finger */}
        {t > PASTE - 0.35 && t < E - 0.2 && (
          <div
            style={{
              position: "absolute",
              left: fx - 55,
              top: fy - 55,
              width: 110,
              height: 110,
              borderRadius: "50%",
              background: "rgba(255,255,255,.45)",
              border: "4px solid #fff",
              transform: `scale(${tap ? 0.8 : 1})`,
            }}
          />
        )}
        {pasted && t < PASTE + 0.6 && (
          <div style={{ position: "absolute", left: 360, top: 640, ...label(30, 0.06), background: "#fff", color: "#000", padding: "12px 20px", opacity: 1 - clamp01((t - PASTE - 0.4) / 0.2) }}>
            Pasted
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
