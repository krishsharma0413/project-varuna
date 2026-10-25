import type { CSSProperties } from "react";

type P = { size?: number; color?: string; fill?: string; style?: CSSProperties; stroke?: number };

export const Heart = ({ size = 64, color = "#fff", fill = "none", stroke = 5, style }: P) => (
  <svg width={size} height={size} viewBox="0 0 64 64" style={style}>
    <path
      d="M32 55 C10 40 4 29 4 20 C4 11 11 5 19 5 C25 5 29 8 32 13 C35 8 39 5 45 5 C53 5 60 11 60 20 C60 29 54 40 32 55 Z"
      fill={fill}
      stroke={color}
      strokeWidth={stroke}
      strokeLinejoin="round"
    />
  </svg>
);

export const Bubble = ({ size = 64, color = "#fff", stroke = 5, style }: P) => (
  <svg width={size} height={size} viewBox="0 0 64 64" style={style}>
    <path
      d="M32 6 C16 6 5 16 5 30 C5 37 8 43 13 47 L10 59 L23 53 C26 54 29 54 32 54 C48 54 59 44 59 30 C59 16 48 6 32 6 Z"
      fill="none"
      stroke={color}
      strokeWidth={stroke}
      strokeLinejoin="round"
    />
  </svg>
);

export const Plane = ({ size = 64, color = "#fff", stroke = 5, style }: P) => (
  <svg width={size} height={size} viewBox="0 0 64 64" style={style}>
    <path d="M58 6 L6 26 L27 33 L34 56 Z M58 6 L27 33" fill="none" stroke={color} strokeWidth={stroke} strokeLinejoin="round" />
  </svg>
);

export const Dots = ({ size = 64, color = "#fff", style }: P) => (
  <svg width={size} height={size} viewBox="0 0 64 64" style={style}>
    {[14, 32, 50].map((x) => (
      <circle key={x} cx={x} cy={32} r={5} fill={color} />
    ))}
  </svg>
);

export const Camera = ({ size = 56, color = "#fff", stroke = 5, style }: P) => (
  <svg width={size} height={size} viewBox="0 0 64 64" style={style}>
    <rect x={6} y={16} width={52} height={38} rx={8} fill="none" stroke={color} strokeWidth={stroke} />
    <circle cx={32} cy={35} r={10} fill="none" stroke={color} strokeWidth={stroke} />
    <path d="M22 16 L26 9 H38 L42 16" fill="none" stroke={color} strokeWidth={stroke} strokeLinejoin="round" />
  </svg>
);

export const Music = ({ size = 40, color = "#fff", style }: P) => (
  <svg width={size} height={size} viewBox="0 0 64 64" style={style}>
    <path d="M24 48 V12 L54 6 V42" fill="none" stroke={color} strokeWidth={6} />
    <circle cx={17} cy={48} r={8} fill={color} />
    <circle cx={47} cy={42} r={8} fill={color} />
  </svg>
);
