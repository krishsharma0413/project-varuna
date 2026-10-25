import { AbsoluteFill } from "remotion";
import { Scanlines } from "../components/Overlays";
import { SlamLines } from "../components/SlamWords";
import { C, clamp01, display, kicks, label, outline, scene, shake, springAt, words } from "../theme";

const [S, E] = scene("question");
const Q = words("q1"); // But wait should you believe everything you watch

export const Question = ({ t }: { t: number }) => {
  const local = t - S;
  const at = (i: number) => Q[i].t;

  // CRT switch-off of the white blur: squash to a line, then to a dot
  const sy = 1 - clamp01(local / 0.12);
  const sx = 1 - clamp01((local - 0.12) / 0.12);
  const crt = local < 0.26;

  const punches = [at(2), at(4), at(5), at(7)];
  const punch = 1 + kicks(t, punches, 11) * 0.05;
  const sh = shake(t, [at(4), at(7)], 12);
  const out = clamp01((t - (E - 0.12)) / 0.12);

  return (
    <AbsoluteFill style={{ background: C.bg, overflow: "hidden" }}>
      {crt && (
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
          <div
            style={{
              width: 1080 * Math.max(sx, 0.01),
              height: 1920 * Math.max(sy, 0.003),
              background: "#fff",
              boxShadow: "0 0 80px 20px rgba(255,255,255,.7)",
            }}
          />
        </AbsoluteFill>
      )}

      {/* a giant outlined question mark drifting behind */}
      <div
        style={{
          position: "absolute",
          right: -180,
          top: 240,
          ...display(1500),
          ...outline(4),
          opacity: 0.16 * clamp01((local - 0.3) / 0.5),
          transform: `rotate(${8 + local * 3}deg)`,
        }}
      >
        ?
      </div>

      <div
        style={{
          position: "absolute",
          left: 72,
          top: 470,
          transform: `translate(${sh.x}px, ${sh.y}px) rotate(${sh.r}deg) scale(${punch * (1 - out * 0.1)})`,
          transformOrigin: "30% 50%",
          opacity: 1 - out,
        }}
      >
        <div style={{ marginBottom: 34, height: 92 }}>
          {t >= at(0) && (
            <span
              style={{
                ...label(64, 0.1),
                display: "inline-block",
                background: C.fg,
                color: C.bg,
                padding: "14px 24px",
                boxShadow: `8px 8px 0 ${C.shadow}`,
                transform: `rotate(-2deg) scale(${0.6 + 0.4 * springAt(t, at(0), { damping: 10, stiffness: 300 })})`,
              }}
            >
              But wait,
            </span>
          )}
        </div>
        <SlamLines
          t={t}
          gap={14}
          lines={[
            [
              { text: "Should", at: at(2), size: 196 },
              { text: "you", at: at(3), size: 196 },
            ],
            [{ text: "believe", at: at(4), size: 300, outlined: true }],
            [{ text: "everything", at: at(5), size: 196 }],
            [
              { text: "you", at: at(6), size: 196 },
              { text: "watch?", at: at(7), size: 196, boxed: true },
            ],
          ]}
        />
      </div>
      <Scanlines opacity={0.07} />
    </AbsoluteFill>
  );
};
