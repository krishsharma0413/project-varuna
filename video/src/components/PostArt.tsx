import { random } from "remotion";
import type { PostBg } from "../posts";

/** Black-and-white backdrops for the fake reels: protest crowds, the Jantar Mantar yantra, barricades. */
export const PostArt = ({ bg, w, h, seed }: { bg: PostBg; w: number; h: number; seed: number }) => {
  const r = (i: number) => random(`${seed}-${i}`);
  switch (bg) {
    case "stripes":
      return (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: "repeating-linear-gradient(-45deg, #262626 0 34px, #0a0a0a 34px 84px)",
          }}
        />
      );
    case "dots":
      return (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: "radial-gradient(circle, #3a3a3a 0 9px, transparent 10px) 0 0 / 44px 44px, #080808",
            maskImage: "radial-gradient(ellipse at 50% 35%, #000 20%, transparent 75%)",
          }}
        />
      );
    case "static":
      return (
        <svg width={w} height={h} style={{ position: "absolute", inset: 0 }}>
          <filter id={`n${seed}`}>
            <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed={seed} />
            <feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.35 0" />
          </filter>
          <rect width={w} height={h} fill="#0b0b0b" />
          <rect width={w} height={h} filter={`url(#n${seed})`} />
          {Array.from({ length: 14 }, (_, i) => (
            <rect key={i} x={0} y={r(i) * h} width={w} height={2 + r(i + 40) * 6} fill="#fff" opacity={0.05 + r(i + 80) * 0.08} />
          ))}
        </svg>
      );
    case "monument": {
      // Samrat Yantra silhouette: the giant sloped gnomon with quadrant arcs, plus a crowd at its foot.
      const base = h * 0.66;
      return (
        <svg width={w} height={h} style={{ position: "absolute", inset: 0 }}>
          <defs>
            <linearGradient id={`sky${seed}`} x1="0" x2="0" y1="0" y2="1">
              <stop offset="0" stopColor="#1e1e1e" />
              <stop offset="1" stopColor="#050505" />
            </linearGradient>
          </defs>
          <rect width={w} height={h} fill={`url(#sky${seed})`} />
          <path d={`M${w * 0.18} ${base} L${w * 0.58} ${h * 0.2} L${w * 0.66} ${h * 0.2} L${w * 0.66} ${base} Z`} fill="#2c2c2c" />
          {Array.from({ length: 18 }, (_, i) => {
            const k = i / 18;
            const x = w * 0.18 + (w * 0.4) * k;
            const y = base - (base - h * 0.2) * k;
            return <rect key={i} x={x} y={y - 6} width={w * 0.022} height={6} fill="#3d3d3d" />;
          })}
          <path d={`M${w * 0.66} ${base} A ${w * 0.3} ${w * 0.3} 0 0 1 ${w * 0.96} ${base - w * 0.3} L ${w * 0.96} ${base} Z`} fill="#202020" />
          <path d={`M${w * 0.18} ${base} A ${w * 0.22} ${w * 0.22} 0 0 0 ${w * -0.04} ${base - w * 0.22} L ${w * -0.04} ${base} Z`} fill="#202020" />
          <Crowd w={w} h={h} top={base - 30} seed={seed} />
        </svg>
      );
    }
    case "barricade": {
      const y = h * 0.58;
      return (
        <svg width={w} height={h} style={{ position: "absolute", inset: 0 }}>
          <rect width={w} height={h} fill="#0c0c0c" />
          <Crowd w={w} h={h} top={h * 0.4} seed={seed} dim />
          {[0, 1, 2].map((i) => (
            <g key={i} transform={`translate(${i * w * 0.36 - 30}, ${y})`}>
              <rect width={w * 0.34} height={70} fill="#e6e6e6" />
              {Array.from({ length: 5 }, (_, j) => (
                <path key={j} d={`M${j * 64} 0 L${j * 64 + 32} 0 L${j * 64 + 2} 70 L${j * 64 - 30} 70 Z`} fill="#111" />
              ))}
              <rect x={20} y={70} width={14} height={180} fill="#9a9a9a" />
              <rect x={w * 0.34 - 34} y={70} width={14} height={180} fill="#9a9a9a" />
            </g>
          ))}
        </svg>
      );
    }
    case "crowd":
    default:
      return (
        <svg width={w} height={h} style={{ position: "absolute", inset: 0 }}>
          <rect width={w} height={h} fill="#0e0e0e" />
          <circle cx={w * 0.72} cy={h * 0.16} r={120} fill="#1f1f1f" />
          <Crowd w={w} h={h} top={h * 0.34} seed={seed} />
        </svg>
      );
  }
};

/** Rows of head-and-shoulder silhouettes with raised placards. */
const Crowd = ({ w, h, top, seed, dim }: { w: number; h: number; top: number; seed: number; dim?: boolean }) => {
  const rows = 5;
  const out = [];
  for (let row = 0; row < rows; row++) {
    const y = top + row * ((h - top) / rows) * 0.8;
    const s = 0.7 + row * 0.22;
    const shade = dim ? 18 + row * 6 : 24 + row * 10;
    const n = 9 - row;
    for (let i = 0; i < n; i++) {
      const rx = random(`c${seed}-${row}-${i}`);
      const x = (i + rx * 0.8) * (w / (n - 0.4)) - 20;
      const col = `rgb(${shade},${shade},${shade})`;
      out.push(
        <g key={`${row}-${i}`} transform={`translate(${x}, ${y}) scale(${s})`}>
          {random(`p${seed}-${row}-${i}`) > 0.62 && row < 3 ? (
            <g>
              <rect x={-4} y={-190} width={8} height={170} fill="#5a5a5a" />
              <rect x={-70} y={-280} width={140} height={100} fill={row % 2 ? "#d8d8d8" : "#f2f2f2"} />
              <rect x={-50} y={-255} width={100} height={14} fill="#111" />
              <rect x={-50} y={-228} width={70} height={14} fill="#111" />
            </g>
          ) : null}
          <circle cx={0} cy={0} r={30} fill={col} />
          <path d="M-62 120 C-62 50 -40 34 0 34 C40 34 62 50 62 120 Z" fill={col} />
        </g>,
      );
    }
  }
  return <g>{out}</g>;
};
