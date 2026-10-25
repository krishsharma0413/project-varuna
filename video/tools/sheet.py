"""Contact sheet of selected frames: python tools/sheet.py out.png f1 f2 ... (frame numbers)."""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
out, frames = sys.argv[1], [int(x) for x in sys.argv[2:]]
cols = min(6, len(frames))
rows = (len(frames) + cols - 1) // cols
tw, th = 300, 533
sheet = Image.new("RGB", (cols * tw, rows * (th + 24)), "#444")
d = ImageDraw.Draw(sheet)
for i, f in enumerate(frames):
    p = [q for q in (ROOT / "out" / "seq").glob("*.jpeg") if int(q.stem.rsplit("-", 1)[1]) == f]
    img = Image.open(p[0]).resize((tw, th))
    x, y = (i % cols) * tw, (i // cols) * (th + 24)
    sheet.paste(img, (x, y + 24))
    d.text((x + 6, y + 4), f"f{f} {f/30:.2f}s", fill="#fff")
sheet.save(out)
