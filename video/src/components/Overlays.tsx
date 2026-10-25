import { AbsoluteFill, Img, random, staticFile, useCurrentFrame } from "remotion";

/** Film grain: a pre-rendered noise tile, jittered every frame. */
export const Grain = ({ opacity = 0.09 }: { opacity?: number }) => {
  // grain moves at 15 fps: looks more like film and halves what the encoder has to spend on noise
  const f = Math.floor(useCurrentFrame() / 2);
  const x = Math.floor(random(`gx${f}`) * 400);
  const y = Math.floor(random(`gy${f}`) * 400);
  return (
    <AbsoluteFill style={{ pointerEvents: "none", overflow: "hidden", mixBlendMode: "screen", opacity }}>
      <Img src={staticFile("grain.png")} style={{ position: "absolute", left: -x, top: -y, width: 1600, height: 2400, imageRendering: "pixelated" }} />
    </AbsoluteFill>
  );
};

export const Vignette = ({ strength = 0.6 }: { strength?: number }) => (
  <AbsoluteFill
    style={{
      pointerEvents: "none",
      background: `radial-gradient(ellipse 75% 60% at 50% 48%, rgba(0,0,0,0) 55%, rgba(0,0,0,${strength}) 100%)`,
    }}
  />
);

export const Scanlines = ({ opacity = 0.12 }: { opacity?: number }) => (
  <AbsoluteFill
    style={{
      pointerEvents: "none",
      opacity,
      background: "repeating-linear-gradient(0deg, rgba(255,255,255,.5) 0 1px, transparent 1px 4px)",
    }}
  />
);
