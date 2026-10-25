import type { CSSProperties, ReactNode } from "react";
import { FONT } from "../theme";

export const PHONE_W = 860;
export const PHONE_H = 1760;
export const BEZEL = 16;
export const SCREEN_W = PHONE_W - BEZEL * 2;
export const SCREEN_H = PHONE_H - BEZEL * 2;

/** A plain dark phone: bezel, dynamic island, status bar. Children fill the screen. */
export const Phone = ({ children, style, statusLight = true }: { children: ReactNode; style?: CSSProperties; statusLight?: boolean }) => (
  <div
    style={{
      position: "absolute",
      width: PHONE_W,
      height: PHONE_H,
      borderRadius: 104,
      background: "#0d0d0d",
      boxShadow: "0 0 0 3px #2b2b2b, 0 0 0 5px #070707, 0 40px 120px rgba(0,0,0,.9), inset 0 0 0 2px #1d1d1d",
      ...style,
    }}
  >
    <div
      style={{
        position: "absolute",
        left: BEZEL,
        top: BEZEL,
        width: SCREEN_W,
        height: SCREEN_H,
        borderRadius: 88,
        overflow: "hidden",
        background: "#000",
      }}
    >
      {children}
      <div
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          padding: "34px 64px 0",
          fontFamily: FONT,
          fontWeight: 700,
          fontSize: 30,
          color: statusLight ? "#fff" : "#000",
        }}
      >
        <span>9:41</span>
        <span style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <svg width={34} height={22} viewBox="0 0 34 22">
            {[0, 1, 2, 3].map((i) => (
              <rect key={i} x={i * 9} y={16 - i * 5} width={6} height={6 + i * 5} rx={1.5} fill="currentColor" />
            ))}
          </svg>
          <svg width={46} height={22} viewBox="0 0 46 22">
            <rect x={1} y={1} width={38} height={20} rx={6} fill="none" stroke="currentColor" strokeWidth={2} opacity={0.6} />
            <rect x={4} y={4} width={28} height={14} rx={3} fill="currentColor" />
            <rect x={41} y={7} width={3} height={8} rx={1} fill="currentColor" opacity={0.6} />
          </svg>
        </span>
      </div>
      <div
        style={{
          position: "absolute",
          top: 22,
          left: "50%",
          width: 210,
          height: 60,
          marginLeft: -105,
          borderRadius: 30,
          background: "#000",
        }}
      />
    </div>
  </div>
);
