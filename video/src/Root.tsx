import { Composition } from "remotion";
import { Avatar } from "./Avatar";
import { DTL, Dussehra } from "./dussehra/Dussehra";
import { Reel } from "./Reel";
import { FPS, H, TL, W } from "./theme";

export const Root = () => (
  <>
    <Composition id="Reel" component={Reel} durationInFrames={TL.frames} fps={FPS} width={W} height={H} defaultProps={{ audio: "audio/mix.wav" }} />
    <Composition
      id="ReelNoMusic"
      component={Reel}
      durationInFrames={TL.frames}
      fps={FPS}
      width={W}
      height={H}
      defaultProps={{ audio: "audio/nomusic.wav" }}
    />
    <Composition
      id="ReelNoNarration"
      component={Reel}
      durationInFrames={TL.frames}
      fps={FPS}
      width={W}
      height={H}
      defaultProps={{ audio: "audio/nonarration.wav" }}
    />
    <Composition id="Avatar" component={Avatar} durationInFrames={1} fps={FPS} width={1080} height={1080} defaultProps={{ invert: false }} />
    <Composition id="AvatarLight" component={Avatar} durationInFrames={1} fps={FPS} width={1080} height={1080} defaultProps={{ invert: true }} />
    <Composition id="Dussehra" component={Dussehra} durationInFrames={Math.round(DTL.total * DTL.fps)} fps={DTL.fps} width={W} height={H} defaultProps={{ audio: "audio/dussehra.wav" }} />
    <Composition id="DussehraSilent" component={Dussehra} durationInFrames={Math.round(DTL.total * DTL.fps)} fps={DTL.fps} width={W} height={H} defaultProps={{ audio: null }} />
    <Composition id="ReelSilent" component={Reel} durationInFrames={TL.frames} fps={FPS} width={W} height={H} defaultProps={{ audio: null }} />
  </>
);
