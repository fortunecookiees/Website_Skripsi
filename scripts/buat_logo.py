"""Buat assets/logo.png (favicon) & assets/logo.svg dari desain di components/logo.py. Jalankan sekali:

    .venv\\Scripts\\python scripts\\buat_logo.py
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from components.logo import _PARTIKEL, svg_mentah  # noqa: E402

INK, PUTIH = (28, 28, 28, 255), (255, 255, 255, 255)
SKALA = 8                      # 64 -> 512 px
LEBAR = 5 * SKALA


def s(v: float) -> float:
    return v * SKALA


def garis(d: ImageDraw.ImageDraw, x1, y1, x2, y2):
    d.line([(s(x1), s(y1)), (s(x2), s(y2))], fill=PUTIH, width=LEBAR)
    for x, y in ((x1, y1), (x2, y2)):  # ujung membulat
        d.ellipse([s(x) - LEBAR / 2, s(y) - LEBAR / 2, s(x) + LEBAR / 2, s(y) + LEBAR / 2], fill=PUTIH)


def busur(d: ImageDraw.ImageDraw, cx, cy, r, mulai, akhir, ujung):
    d.arc([s(cx - r) - LEBAR / 2, s(cy - r) - LEBAR / 2, s(cx + r) + LEBAR / 2, s(cy + r) + LEBAR / 2],
          mulai, akhir, fill=PUTIH, width=LEBAR)
    x, y = ujung
    d.ellipse([s(x) - LEBAR / 2, s(y) - LEBAR / 2, s(x) + LEBAR / 2, s(y) + LEBAR / 2], fill=PUTIH)


img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle([0, 0, 511, 511], radius=s(15), fill=INK)
garis(d, 12, 24, 34, 24); busur(d, 34, 17, 7, 180, 90, (27, 17))   # garis atas, melingkar ke atas
garis(d, 12, 34, 44, 34); busur(d, 44, 41, 7, 270, 180, (37, 41))  # garis tengah, melingkar ke bawah
garis(d, 12, 44, 26, 44)
for x, y, r in _PARTIKEL:
    d.ellipse([s(x - r), s(y - r), s(x + r), s(y + r)], fill=PUTIH)

(ROOT / "assets").mkdir(exist_ok=True)
img.save(ROOT / "assets" / "logo.png")
(ROOT / "assets" / "logo.svg").write_text(svg_mentah(512, latar="#1C1C1C", garis="#FFFFFF"), encoding="utf-8")
print("Tersimpan: assets/logo.png, assets/logo.svg")
