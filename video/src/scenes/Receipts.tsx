import { AbsoluteFill, Img, staticFile } from "remotion";
import { Stamp } from "../components/Stamp";
import { C, clamp01, label, scene, shake, springAt, TL } from "../theme";

const [S, E] = scene("receipts");
const STAMP = TL.cues["receipts.stamp"];
const ROWS = TL.cues["receipts.rows"];

// Crops of the real screenshots, in source-image pixels.
const HERO = { src: "shots/hero.png", w: 2880, h: 1061, x: 140, y: 90, cw: 1520, ch: 870 };
const TABLE = { src: "shots/verdict-table.png", w: 2548, h: 1008, x: 1460, y: 290, cw: 1050, ch: 650 };
const CARD_W = 960;

const Crop = ({ img }: { img: typeof HERO }) => {
  const k = CARD_W / img.cw;
  return (
    <div style={{ width: CARD_W, height: img.ch * k, overflow: "hidden", position: "relative" }}>
      <Img src={staticFile(img.src)} style={{ position: "absolute", width: img.w * k, height: img.h * k, left: -img.x * k, top: -img.y * k }} />
    </div>
  );
};

export const Receipts = ({ t }: { t: number }) => {
  const local = t - S;
  const heroIn = springAt(t, S, { damping: 16, stiffness: 170 });
  const tableIn = springAt(t, STAMP + 0.3, { damping: 16, stiffness: 170 });
  const sh = shake(t, [STAMP], 20);
  const zoom = 1 + local * 0.025;
  const exit = clamp01((t - (E - 0.15)) / 0.15);
  const k = CARD_W / TABLE.cw;

  return (
    <AbsoluteFill style={{ background: C.bg, overflow: "hidden" }}>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse 70% 50% at 50% 45%, rgba(255,255,255,.1), rgba(0,0,0,0) 70%)" }} />
      <AbsoluteFill style={{ transform: `translate(${sh.x}px, ${sh.y}px) scale(${zoom * (1 - exit * 0.05)})`, opacity: 1 - exit }}>
        <div style={{ position: "absolute", left: 60, top: 140, ...label(40, 0.12), color: C.fg, display: "flex", gap: 16, alignItems: "center" }}>
          <span style={{ background: C.fg, color: C.bg, padding: "6px 14px" }}>Receipts</span> not vibes
        </div>

        <div
          style={{
            position: "absolute",
            left: 60,
            top: 230,
            border: `4px solid ${C.fg}`,
            boxShadow: `14px 14px 0 ${C.shadow}`,
            transform: `perspective(1600px) translateX(${(1 - heroIn) * 900}px) rotateY(${(1 - heroIn) * -35}deg)`,
          }}
        >
          <Crop img={HERO} />
        </div>
        <Stamp t={t} at={STAMP} size={70} kind="double" rotate={-4} style={{ left: 250, top: 720 }}>
          ◐ Misleading
        </Stamp>

        <div
          style={{
            position: "absolute",
            left: 60,
            top: 930,
            background: "#fff",
            border: "4px solid #fff",
            boxShadow: `14px 14px 0 ${C.shadow}`,
            transform: `translateY(${(1 - tableIn) * 1100}px) rotate(${(1 - tableIn) * 6 - 1}deg)`,
          }}
        >
          <div style={{ position: "relative", overflow: "hidden" }}>
            <Crop img={TABLE} />
            {/* each source row is uncovered on a tick */}
            {ROWS.map((r, i) => {
              const p = clamp01((t - r) / 0.12);
              return (
                <div
                  key={i}
                  style={{
                    position: "absolute",
                    left: (2050 - TABLE.x) * k + p * 520,
                    top: (410 - TABLE.y + i * 84) * k,
                    width: 520,
                    height: 82 * k,
                    background: "#fff",
                  }}
                />
              );
            })}
          </div>
        </div>
        <div style={{ position: "absolute", left: 60, top: 1600, ...label(34, 0.1), color: C.muted, opacity: clamp01((t - ROWS[5]) / 0.2) }}>
          Every source shown · ranked · dated
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
