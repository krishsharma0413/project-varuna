# varuna reel

The Instagram reel from [scripts/first.md](../scripts/first.md), built with Remotion. Everything is generated: the voice (edge-tts), the sound design and music (numpy/scipy), and the visuals (React). The only external inputs are the real screenshots in `docs/screenshots/` and the Archivo font.

## Rebuild

```bash
cd video
npm install
python -m venv .venv && .venv/Scripts/python -m pip install edge-tts numpy scipy pillow

.venv/Scripts/python tools/tts.py        # voice lines -> public/audio/vo_*.wav + src/vo.json (word timings)
.venv/Scripts/python tools/timeline.py   # scene + cue times -> src/timeline.json
.venv/Scripts/python tools/grain.py      # film-grain tile -> public/grain.png
.venv/Scripts/python tools/mix.py        # sound design + mix -> public/audio/mix.wav, nomusic.wav, nonarration.wav

npm run render          # out/varuna-reel.mp4
npm run render:nomusic  # out/varuna-reel-no-music.mp4 (voice + sound effects, for adding a trending sound)
npm run render:nonarration  # out/varuna-reel-no-narration.mp4 (music + sound effects, no voice, no ducking)
npm run cover           # out/cover.png
npm run avatar          # out/profile-picture.png (+ -light), 1080×1080 Instagram profile pictures
npm run studio          # live preview
```

### Dussehra reel (no narration)

```bash
.venv/Scripts/python tools/mix_dussehra.py   # music + sound effects -> public/audio/dussehra.wav
npm run render:dussehra                      # out/varuna-reel-dussehra.mp4
npm run cover:dussehra                       # out/cover-dussehra.png
```

Its timings live in `src/dussehra/timeline.json` (beat-aligned at 100 BPM); the scenes are in `src/dussehra/`. Both mixers share the synth toolkit in `tools/sfx.py`.

`src/timeline.json` is the single source of truth: the scenes read their cues from it and `mix.py` places every sound on the same times. To change a line, edit `LINES` in `tools/tts.py`, then rerun tts, timeline and mix. The visuals follow automatically.

To try another voice: `.venv/Scripts/python tools/tts.py en-IN-NeerjaNeural`.
