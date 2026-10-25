"""Write public/grain.png: a grey noise tile for the film-grain overlay."""

import struct
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
W, H = 800, 1200
rng = np.random.default_rng(7)
px = np.clip(rng.normal(128, 70, (H, W)), 0, 255).astype(np.uint8)
raw = b"".join(b"\x00" + row.tobytes() for row in px)


def chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 0, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
(ROOT / "public" / "grain.png").write_bytes(png)
print("grain.png", len(png) // 1024, "KB")
