// The Ravana effigy, drawn in the site's greys. World coordinates are the 1080×1920 frame.

export type HeadSpec = { id: string; cx: number; cy: number; w: number; h: number; crown: number; label: string };

const SIDE = { w: 96, h: 128, crown: 70, cy: 662 };
export const HEADS: HeadSpec[] = [
  { id: "L4", cx: 75, ...SIDE, label: "Rumours" },
  { id: "L3", cx: 175, ...SIDE, label: "Deepfakes" },
  { id: "L2", cx: 275, ...SIDE, label: "Half-truths" },
  { id: "L1", cx: 375, ...SIDE, label: "Fake news" },
  { id: "M", cx: 540, cy: 642, w: 220, h: 250, crown: 125, label: "Propaganda" },
  { id: "R1", cx: 705, ...SIDE, label: "Edited clips" },
  { id: "R2", cx: 805, ...SIDE, label: "Clickbait" },
  { id: "R3", cx: 905, ...SIDE, label: "Paid agendas" },
  { id: "R4", cx: 1005, ...SIDE, label: "Out of context" },
  { id: "T", cx: 540, cy: 335, w: 92, h: 112, crown: 52, label: "Blind forwards" },
];
// the order the labels appear in (main head last, as a stamp)
export const LABEL_ORDER = ["L1", "R1", "L2", "R2", "L3", "R3", "L4", "R4", "T", "M"];
export const NAVEL = { x: 540, y: 1128 };

const INK = "#0d0d0d";
const SW = 4;

export type Fall = { dy: number; rot: number };

const Head = ({ h, eyeGlow, fall }: { h: HeadSpec; eyeGlow: number; fall?: Fall }) => {
  const { cx, cy, w } = h;
  const hh = h.h;
  const top = cy - hh / 2;
  const ct = top - h.crown;
  const spikes = h.id === "M" ? 5 : 3;
  const cw = w * 0.92;
  const pts: string[] = [`${cx - cw / 2},${top + 6}`];
  for (let i = 0; i < spikes; i++) {
    const x0 = cx - cw / 2 + (cw / spikes) * i;
    const peak = i === Math.floor(spikes / 2) ? ct : ct + h.crown * 0.28;
    pts.push(`${x0 + cw / spikes / 2},${peak}`, `${x0 + cw / spikes},${top - h.crown * 0.32}`);
  }
  pts.push(`${cx + cw / 2},${top + 6}`);
  const eyeFill = eyeGlow > 0 ? `rgb(255,${Math.round(255 - 120 * eyeGlow)},${Math.round(255 - 220 * eyeGlow)})` : "#fff";
  return (
    <g transform={fall ? `translate(0 ${fall.dy}) rotate(${fall.rot} ${cx} ${cy})` : undefined}>
      {/* ears + earrings */}
      <ellipse cx={cx - w * 0.52} cy={cy} rx={w * 0.1} ry={hh * 0.13} fill="#bdbdbd" stroke={INK} strokeWidth={SW} />
      <ellipse cx={cx + w * 0.52} cy={cy} rx={w * 0.1} ry={hh * 0.13} fill="#bdbdbd" stroke={INK} strokeWidth={SW} />
      <circle cx={cx - w * 0.53} cy={cy + hh * 0.2} r={w * 0.07} fill="none" stroke="#efefef" strokeWidth={SW} />
      <circle cx={cx + w * 0.53} cy={cy + hh * 0.2} r={w * 0.07} fill="none" stroke="#efefef" strokeWidth={SW} />
      {/* crown */}
      <polygon points={pts.join(" ")} fill="#e9e9e9" stroke={INK} strokeWidth={SW} strokeLinejoin="round" />
      <rect x={cx - cw / 2} y={top - h.crown * 0.34} width={cw} height={h.crown * 0.34 + 8} fill="#bcbcbc" stroke={INK} strokeWidth={SW} />
      {[-0.3, 0, 0.3].map((k) => (
        <circle key={k} cx={cx + cw * k} cy={top - h.crown * 0.16} r={w * 0.045} fill={INK} />
      ))}
      {/* face */}
      <rect x={cx - w / 2} y={top} width={w} height={hh} rx={w * 0.32} fill="#d4d4d4" stroke={INK} strokeWidth={SW} />
      {/* tilak */}
      <path d={`M${cx - w * 0.05} ${top + hh * 0.08} L${cx + w * 0.05} ${top + hh * 0.08} L${cx} ${top + hh * 0.3} Z`} fill={INK} />
      {/* angry brows */}
      <path d={`M${cx - w * 0.36} ${cy - hh * 0.2} L${cx - w * 0.07} ${cy - hh * 0.07}`} stroke={INK} strokeWidth={w * 0.08} strokeLinecap="round" />
      <path d={`M${cx + w * 0.36} ${cy - hh * 0.2} L${cx + w * 0.07} ${cy - hh * 0.07}`} stroke={INK} strokeWidth={w * 0.08} strokeLinecap="round" />
      {/* eyes */}
      {[-1, 1].map((s) => (
        <g key={s}>
          <ellipse cx={cx + s * w * 0.19} cy={cy - hh * 0.0} rx={w * 0.12} ry={hh * 0.065} fill={eyeFill} stroke={INK} strokeWidth={SW * 0.8} />
          <circle cx={cx + s * w * 0.17} cy={cy} r={w * 0.045} fill={INK} />
        </g>
      ))}
      {/* nose */}
      <path d={`M${cx} ${cy + hh * 0.02} L${cx - w * 0.07} ${cy + hh * 0.17} L${cx + w * 0.06} ${cy + hh * 0.17}`} fill="none" stroke={INK} strokeWidth={SW * 0.8} strokeLinejoin="round" />
      {/* curled moustache */}
      {[-1, 1].map((s) => (
        <path
          key={s}
          d={`M${cx} ${cy + hh * 0.23} Q${cx + s * w * 0.22} ${cy + hh * 0.18} ${cx + s * w * 0.36} ${cy + hh * 0.26} Q${cx + s * w * 0.46} ${cy + hh * 0.3} ${cx + s * w * 0.42} ${cy + hh * 0.16}`}
          fill="none"
          stroke={INK}
          strokeWidth={w * 0.065}
          strokeLinecap="round"
        />
      ))}
      {/* grin */}
      <path d={`M${cx - w * 0.18} ${cy + hh * 0.33} Q${cx} ${cy + hh * 0.44} ${cx + w * 0.18} ${cy + hh * 0.33}`} fill="#fff" stroke={INK} strokeWidth={SW * 0.8} />
    </g>
  );
};

export const Effigy = ({ eyeGlow = 0, fall = () => undefined }: { eyeGlow?: number; fall?: (id: string) => Fall | undefined }) => (
  <svg width={1080} height={1920} viewBox="0 0 1080 1920" style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}>
    <defs>
      <pattern id="chev" width="60" height="40" patternUnits="userSpaceOnUse">
        <rect width="60" height="40" fill="#9c9c9c" />
        <path d="M0 30 L30 8 L60 30" fill="none" stroke="#e6e6e6" strokeWidth="8" />
      </pattern>
      <pattern id="pleat" width="44" height="20" patternUnits="userSpaceOnUse">
        <rect width="44" height="20" fill="#b3b3b3" />
        <rect width="14" height="20" fill="#7d7d7d" />
      </pattern>
      <pattern id="dots" width="36" height="36" patternUnits="userSpaceOnUse">
        <rect width="36" height="36" fill="#8a8a8a" />
        <circle cx="18" cy="18" r="6" fill="#e3e3e3" />
      </pattern>
      <pattern id="band" width="40" height="40" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect width="40" height="40" fill="#cfcfcf" />
        <rect width="16" height="40" fill="#5f5f5f" />
      </pattern>
    </defs>

    {/* bamboo scaffold + platform */}
    <rect x={250} y={1745} width={580} height={40} fill="#3a3a3a" stroke={INK} strokeWidth={SW} />
    {[300, 780].map((x) => (
      <rect key={x} x={x - 8} y={1240} width={16} height={510} fill="#4a4a4a" />
    ))}
    {/* legs */}
    {[465, 615].map((x) => (
      <rect key={x} x={x - 30} y={1560} width={60} height={190} fill="url(#band)" stroke={INK} strokeWidth={SW} />
    ))}
    {/* skirt */}
    <polygon points="385,1180 695,1180 800,1580 280,1580" fill="url(#pleat)" stroke={INK} strokeWidth={SW} strokeLinejoin="round" />
    <rect x={280} y={1540} width={520} height={40} fill="url(#band)" stroke={INK} strokeWidth={SW} />
    <rect x={375} y={1170} width={330} height={36} fill="#e6e6e6" stroke={INK} strokeWidth={SW} />
    {/* arms */}
    <polygon points="335,845 285,850 205,1170 262,1182" fill="url(#dots)" stroke={INK} strokeWidth={SW} strokeLinejoin="round" />
    <polygon points="745,845 795,850 875,1170 818,1182" fill="url(#dots)" stroke={INK} strokeWidth={SW} strokeLinejoin="round" />
    {/* shield */}
    <circle cx={220} cy={1255} r={96} fill="#bdbdbd" stroke={INK} strokeWidth={SW} />
    <circle cx={220} cy={1255} r={62} fill="none" stroke={INK} strokeWidth={SW} />
    {[0, 1, 2, 3, 4, 5].map((k) => (
      <circle key={k} cx={220 + Math.cos((k / 6) * Math.PI * 2) * 78} cy={1255 + Math.sin((k / 6) * Math.PI * 2) * 78} r={7} fill={INK} />
    ))}
    {/* sword */}
    <polygon points="842,1190 866,1186 912,1600 896,1640 880,1602" fill="#efefef" stroke={INK} strokeWidth={SW} strokeLinejoin="round" />
    <rect x={812} y={1176} width={86} height={18} fill="#6d6d6d" stroke={INK} strokeWidth={SW} transform="rotate(-6 855 1185)" />
    <circle cx={238} cy={1180} r={30} fill="#d4d4d4" stroke={INK} strokeWidth={SW} />
    <circle cx={850} cy={1180} r={30} fill="#d4d4d4" stroke={INK} strokeWidth={SW} />
    {/* torso */}
    <polygon points="330,830 750,830 702,1190 378,1190" fill="url(#chev)" stroke={INK} strokeWidth={SW} strokeLinejoin="round" />
    <path d="M360 840 Q540 1000 720 840" fill="none" stroke="#efefef" strokeWidth={10} />
    <path d="M385 850 Q540 1050 695 850" fill="none" stroke="#efefef" strokeWidth={6} strokeDasharray="4 14" strokeLinecap="round" />
    {/* navel medallion: the arrow's target */}
    <circle cx={NAVEL.x} cy={NAVEL.y} r={38} fill="#efefef" stroke={INK} strokeWidth={SW} />
    {Array.from({ length: 12 }, (_, k) => {
      const a = (k / 12) * Math.PI * 2;
      return <line key={k} x1={NAVEL.x + Math.cos(a) * 44} y1={NAVEL.y + Math.sin(a) * 44} x2={NAVEL.x + Math.cos(a) * 60} y2={NAVEL.y + Math.sin(a) * 60} stroke="#efefef" strokeWidth={6} />;
    })}
    <circle cx={NAVEL.x} cy={NAVEL.y} r={14} fill={INK} />
    {/* shoulders + neck */}
    <rect x={500} y={760} width={80} height={80} fill="#c4c4c4" stroke={INK} strokeWidth={SW} />
    <path d="M300 860 Q330 805 400 812 L680 812 Q750 805 780 860 Z" fill="#e3e3e3" stroke={INK} strokeWidth={SW} />
    {/* collar band holding the heads */}
    <rect x={30} y={748} width={1020} height={26} fill="url(#band)" stroke={INK} strokeWidth={SW} />
    {HEADS.filter((h) => h.id !== "M" && h.id !== "T").map((h) => (
      <Head key={h.id} h={h} eyeGlow={eyeGlow} fall={fall(h.id)} />
    ))}
    <rect x={526} y={360} width={28} height={160} fill="#4a4a4a" />
    <Head h={HEADS[9]} eyeGlow={eyeGlow} fall={fall("T")} />
    <Head h={HEADS[4]} eyeGlow={eyeGlow} fall={fall("M")} />
  </svg>
);
