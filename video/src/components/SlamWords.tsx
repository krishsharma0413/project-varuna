import type { CSSProperties } from "react";
import { C, display, outline, springAt } from "../theme";

export type SlamWord = { text: string; at: number; outlined?: boolean; size?: number; boxed?: boolean; dim?: number };

/** One poster word that slams in (scale + blur settle) at its spoken time. */
export const Slam = ({ w, t, style }: { w: SlamWord; t: number; style?: CSSProperties }) => {
  const visible = t >= w.at;
  const p = springAt(t, w.at, { damping: 12, stiffness: 320 });
  const size = w.size ?? 200;
  return (
    <span
      style={{
        display: "inline-block",
        ...display(size),
        ...(w.outlined ? outline(Math.max(3, size / 60)) : { color: C.fg }),
        ...(w.boxed ? { background: C.fg, color: C.bg, padding: "0 0.12em" } : null),
        opacity: visible ? Math.min(1, (t - w.at) * 16) * (w.dim ?? 1) : 0,
        transform: `scale(${visible ? 1.7 - 0.7 * p : 1.7})`,
        filter: visible && p < 0.9 ? `blur(${(1 - p) * 14}px)` : undefined,
        transformOrigin: "50% 60%",
        marginRight: "0.18em",
        ...style,
      }}
    >
      {w.text}
    </span>
  );
};

/** Lines of slam words. */
export const SlamLines = ({ lines, t, gap = 10, style }: { lines: SlamWord[][]; t: number; gap?: number; style?: CSSProperties }) => (
  <div style={{ display: "flex", flexDirection: "column", gap, ...style }}>
    {lines.map((line, i) => (
      <div key={i} style={{ whiteSpace: "nowrap" }}>
        {line.map((w, j) => (
          <Slam key={j} w={w} t={t} />
        ))}
      </div>
    ))}
  </div>
);
