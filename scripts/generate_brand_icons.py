"""
Brand icon generator v3 — adds a TRANSPARENT background family.

Output structure (per owner request):
  brand/                    → white-bg versions (existing, unchanged)
  brand/transparent/        → SAME sizes with transparent background
    icon-1024.png / icon-512.png / icon-192.png / apple-touch-icon.png
    google-logo-120.png / favicon-32.png / favicon-16.png
    hudhud-icon-master.svg

Usage: python scripts/generate_brand_icons.py          (both families)
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT / "brand"
BRAND_T = BRAND / "transparent"
STATIC = ROOT / "src" / "templates" / "static"

# Brand palette (from the site's own CSS)
NAVY = (15, 23, 42, 255)        # #0f172a — wordmark
WHITE = (255, 255, 255, 255)    # #ffffff — white-bg family background
BLUE = (37, 99, 235, 255)       # #2563eb — the brand dot
TRANSPARENT = (0, 0, 0, 0)      # transparent family background
FONT_PATH = r"C:\Windows\Fonts\Montserrat-ExtraBold.ttf"
CORNER_RATIO = 0.18


def _bg(size: int, color) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    radius = int(size * CORNER_RATIO)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=color)
    return img


def _font(px: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_PATH, px)


def _fit_wordmark(size: int, text_full: bool) -> tuple:
    main, dot = ("Hudhud", ".") if text_full else ("H", ".")
    max_w = size * 0.86
    px = int(size * 0.42)
    while px > 8:
        f = _font(px)
        w = ImageDraw.Draw(Image.new("RGBA", (8, 8))).textlength(main + dot, font=f)
        if w <= max_w:
            return main, dot, f, w
        px = int(px * 0.92)
    return main, dot, _font(8), 0


def _draw_wordmark(img: Image.Image, text_full: bool = True) -> None:
    size = img.size[0]
    d = ImageDraw.Draw(img)
    main, dot, f, w_main = _fit_wordmark(size, text_full)
    w_dot = d.textlength(dot, font=f)
    x = (size - w_main - w_dot) / 2
    asc, desc = f.getmetrics()
    y = (size - (asc + desc)) / 2
    d.text((x, y), main, font=f, fill=NAVY)
    d.text((x + w_main, y), dot, font=f, fill=BLUE)


def _svg_master(transparent: bool = False) -> str:
    bg = "none" if transparent else "#ffffff"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">
  <defs>
    <clipPath id="r"><rect width="1024" height="1024" rx="184"/></clipPath>
  </defs>
  <g clip-path="url(#r)">
    <rect width="1024" height="1024" fill="{bg}"/>
    <text x="512" y="516" font-family="Montserrat, 'Plus Jakarta Sans', sans-serif"
          font-weight="800" font-size="292" fill="#0f172a"
          text-anchor="middle" dominant-baseline="central">Hudhud<tspan fill="#2563eb">.</tspan></text>
  </g>
</svg>"""


def main():
    BRAND.mkdir(exist_ok=True)
    BRAND_T.mkdir(exist_ok=True)

    # Masters
    (BRAND / "hudhud-icon-master.svg").write_text(_svg_master(False), encoding="utf-8")
    (BRAND_T / "hudhud-icon-master-transparent.svg").write_text(_svg_master(True), encoding="utf-8")

    # ── White-bg family (as before) ──
    for size in (1024, 512, 192):
        img = _bg(size, WHITE)
        _draw_wordmark(img, text_full=True)
        img.save(BRAND / f"icon-{size}.png")
    img = _bg(180, WHITE)
    _draw_wordmark(img, text_full=True)
    img.save(BRAND / "apple-touch-icon.png")

    big = _bg(480, WHITE)
    _draw_wordmark(big, text_full=False)
    big.resize((120, 120), Image.LANCZOS).save(BRAND / "google-logo-120.png")

    big32 = _bg(128, WHITE)
    _draw_wordmark(big32, text_full=False)
    big32.resize((32, 32), Image.LANCZOS).save(BRAND / "favicon-32.png")
    big32.resize((16, 16), Image.LANCZOS).save(BRAND / "favicon-16.png")

    imgs = [big32.resize((s, s), Image.LANCZOS) for s in (16, 32, 48)]
    imgs[0].save(STATIC / "favicon.ico", format="ICO",
                 sizes=[(16, 16), (32, 32), (48, 48)], append_images=imgs[1:])
    for name, dest in [
        ("icon-192.png", "icon-192.png"), ("icon-512.png", "icon-512.png"),
        ("apple-touch-icon.png", "apple-touch-icon.png"),
        ("favicon-32.png", "favicon-32.png"), ("favicon-16.png", "favicon-16.png"),
    ]:
        (STATIC / dest).write_bytes((BRAND / name).read_bytes())
    print("white-bg family regenerated (brand/ + static/)")

    # ── Transparent family (new) ──
    for size in (1024, 512, 192):
        img = _bg(size, TRANSPARENT)
        _draw_wordmark(img, text_full=True)
        img.save(BRAND_T / f"icon-{size}.png")
    img = _bg(180, TRANSPARENT)
    _draw_wordmark(img, text_full=True)
    img.save(BRAND_T / "apple-touch-icon.png")

    big = _bg(480, TRANSPARENT)
    _draw_wordmark(big, text_full=False)
    big.resize((120, 120), Image.LANCZOS).save(BRAND_T / "google-logo-120.png")

    big32 = _bg(128, TRANSPARENT)
    _draw_wordmark(big32, text_full=False)
    big32.resize((32, 32), Image.LANCZOS).save(BRAND_T / "favicon-32.png")
    big32.resize((16, 16), Image.LANCZOS).save(BRAND_T / "favicon-16.png")
    print("transparent family regenerated (brand/transparent/)")


if __name__ == "__main__":
    main()
