import { AbsoluteFill } from "remotion";
import { C } from "./theme";

// The V from frontend/public/favicon.svg (32×32 viewBox), scaled up. Instagram crops avatars to a
// circle, so the mark stays well inside the middle ~70%.
const V = "M7 8h4.2L16 20.6 20.8 8H25l-7 17h-4z";
const SCALE = 30;
const SHADOW = 0.75; // in favicon units, like the site's hard offset shadows

export const Avatar = ({ invert = false }: { invert?: boolean }) => {
  const bg = invert ? C.fg : C.bg;
  const fg = invert ? C.bg : C.fg;
  // centre the mark's bounding box (x 7–25, y 8–25) including its shadow
  const w = 18 + SHADOW;
  const h = 17 + SHADOW;
  const tx = 540 - (7 + w / 2) * SCALE;
  const ty = 540 - (8 + h / 2) * SCALE;
  return (
    <AbsoluteFill style={{ background: bg }}>
      <svg width={1080} height={1080} viewBox="0 0 1080 1080">
        <g transform={`translate(${tx} ${ty}) scale(${SCALE})`}>
          <path d={V} fill={C.shadow} transform={`translate(${SHADOW} ${SHADOW})`} />
          <path d={V} fill={fg} />
        </g>
      </svg>
    </AbsoluteFill>
  );
};
