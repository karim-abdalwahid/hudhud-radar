"""
Brand icon generator v2 (owner specs):
  - LARGE icons (1024/512/192/180): WHITE background, full "Hudhud" wordmark
    with every letter visible + blue dot — matching the site navbar exactly.
  - SMALL icons (google-120, favicons): white bg, compact "H." with the blue
    dot, high quality rendering.

Usage: python scripts/generate_brand_icons.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT / "brand"
STATIC = ROOT / "src" / "templates" / "static"

# Brand palette (from the site's own CSS)
NAVY = (15, 23, 42, 255)        # #0f172a — wordmark color (text-main)
WHITE = (255, 255, 255, 255)    # #ffffff — background (owner spec v2)
BLUE = (37, 99, 235, 255)       # #2563eb — the brand dot
FONT_PATH = r"C:\Windows\Fonts\Montserrat-ExtraBold.ttf"
CORNER_RATIO = 0.18             # rounded-square corners


def _rounded_bg(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    radius = int(size * CORNER_RATIO)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=WHITE)
    return img


def _font(px: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_PATH, px)


def _fit_wordmark(size: int, text_full: bool) -> tuple:
    """Find the largest font size where the wordmark fits within 86% of the
    canvas width — guarantees EVERY letter is visible (owner spec v2)."""
    main, dot = ("Hudhud", ".") if text_full else ("H", ".")
    max_w = size * 0.86
    px = int(size * 0.42)  # upper bound
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
    text_h = asc + desc
    y = (size - text_h) / 2
    d.text((x, y), main, font=f, fill=NAVY)
    d.text((x + w_main, y), dot, font=f, fill=BLUE)


def _svg_master() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">
  <defs>
    <clipPath id="r"><rect width="1024" height="1024" rx="184"/></clipPath>
  </defs>
  <g clip-path="url(#r)">
    <rect width="1024" height="1024" fill="#ffffff"/>
    <text x="512" y="516" font-family="Montserrat, 'Plus Jakarta Sans', sans-serif"
          font-weight="800" font-size="292" fill="#0f172a"
          text-anchor="middle" dominant-baseline="central">Hudhud<tspan fill="#2563eb">.</tspan></text>
  </g>
</svg>"""


def main():
    BRAND.mkdir(exist_ok=True)
    (BRAND / "hudhud-icon-master.svg").write_text(_svg_master(), encoding="utf-8")

    # LARGE: white bg + full wordmark, every letter visible
    for size in (1024, 512, 192):
        img = _rounded_bg(size)
        _draw_wordmark(img, text_full=True)
        img.save(BRAND / f"icon-{size}.png")
        print(f"icon-{size}.png (full wordmark)")

    # Apple touch (iOS flattens — opaque white)
    img = _rounded_bg(180)
    _draw_wordmark(img, text_full=True)
    img.save(BRAND / "apple-touch-icon.png")
    print("apple-touch-icon.png (full wordmark)")

    # Google consent logo (120, compact H. — high quality via 4x supersample)
    big = _rounded_bg(480)
    _draw_wordmark(big, text_full=False)
    small = big.resize((120, 120), Image.LANCZOS)
    small.save(BRAND / "google-logo-120.png")
    print("google-logo-120.png (H. supersampled)")

    # Favicons (H. compact, supersampled for crispness)
    big32 = _rounded_bg(128)
    _draw_wordmark(big32, text_full=False)
    big32.resize((32, 32), Image.LANCZOS).save(BRAND / "favicon-32.png")
    big32.resize((16, 16), Image.LANCZOS).save(BRAND / "favicon-16.png")
    print("favicon-32/16.png (H. supersampled)")

    # favicon.ico multi-res
    imgs = [big32.resize((s, s), Image.LANCZOS) for s in (16, 32, 48)]
    imgs[0].save(STATIC / "favicon.ico", format="ICO",
                 sizes=[(16, 16), (32, 32), (48, 48)], append_images=imgs[1:])
    print("static/favicon.ico written")

    # Served copies
    for name, dest in [
        ("icon-192.png", "icon-192.png"),
        ("icon-512.png", "icon-512.png"),
        ("apple-touch-icon.png", "apple-touch-icon.png"),
        ("favicon-32.png", "favicon-32.png"),
        ("favicon-16.png", "favicon-16.png"),
    ]:
        (STATIC / dest).write_bytes((BRAND / name).read_bytes())
        print(f"static/{dest} written")


if __name__ == "__main__":
    main()
