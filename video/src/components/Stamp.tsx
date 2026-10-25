import type { CSSProperties, ReactNode } from "react";
import { C, display, springAt } from "../theme";

export type StampKind = "solid" | "double" | "dashed" | "fill";

/** The site's .verdict-lg: rotated, hard-shadowed stamp. Slams in from large at `at`. */
export const Stamp = ({
  t,
  at,
  children,
  kind = "solid",
  rotate = -3,
  size = 96,
  style,
}: {
  t: number;
  at: number;
  children: ReactNode;
  kind?: StampKind;
  rotate?: number;
  size?: number;
  style?: CSSProperties;
}) => {
  if (t < at) return null;
  const p = springAt(t, at, { damping: 13, stiffness: 260 });
  const scale = 2.6 - 1.6 * p;
  const border =
    kind === "double" ? `${Math.round(size * 0.12)}px double ${C.fg}` : kind === "dashed" ? `${Math.round(size * 0.07)}px dashed ${C.fg}` : `${Math.round(size * 0.06)}px solid ${C.fg}`;
  return (
    <div
      style={{
        position: "absolute",
        ...display(size, 125),
        lineHeight: 1,
        padding: "0.14em 0.36em",
        background: kind === "fill" ? C.fg : C.bg,
        color: kind === "fill" ? C.bg : C.fg,
        border: kind === "fill" ? "none" : border,
        boxShadow: `${size * 0.1}px ${size * 0.1}px 0 ${C.shadow}`,
        transform: `rotate(${rotate}deg) scale(${scale})`,
        opacity: Math.min(1, (t - at) * 14),
        whiteSpace: "nowrap",
        ...style,
      }}
    >
      {children}
    </div>
  );
};
