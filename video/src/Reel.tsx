import { AbsoluteFill, Html5Audio, staticFile, useCurrentFrame } from "remotion";
import { Grain, Vignette } from "./components/Overlays";
import { End } from "./scenes/End";
import { Hook } from "./scenes/Hook";
import { Paste } from "./scenes/Paste";
import { Pipeline } from "./scenes/Pipeline";
import { Question } from "./scenes/Question";
import { Receipts } from "./scenes/Receipts";
import { Room } from "./scenes/Room";
import { Turn } from "./scenes/Turn";
import { FPS, TL } from "./theme";

const SC = TL.scenes;
const within = (t: number, [a, b]: number[]) => t >= a && t < b;

export const Reel = ({ audio }: { audio: string | null }) => {
  const t = useCurrentFrame() / FPS;
  const inRoom = t >= SC.room[0] && t < SC.still[1];
  return (
    <AbsoluteFill style={{ background: "#000", color: "#fff" }}>
      {within(t, SC.hook) && <Hook t={t} />}
      {within(t, SC.question) && <Question t={t} />}
      {inRoom && <Room t={t} />}
      {within(t, SC.turn) && <Turn t={t} />}
      {within(t, SC.paste) && <Paste t={t} />}
      {within(t, SC.pipeline) && <Pipeline t={t} />}
      {within(t, SC.receipts) && <Receipts t={t} />}
      {t >= SC.end[0] && <End t={t} />}
      <Vignette strength={0.55} />
      <Grain opacity={0.1} />
      {audio && <Html5Audio src={staticFile(audio)} />}
    </AbsoluteFill>
  );
};
