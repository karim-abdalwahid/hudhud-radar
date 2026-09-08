"""
Brand icon generator — renders the Hudhud wordmark ("Hudhud" + blue dot)
at every required size from one deterministic script.

Usage:  python scripts/generate_brand_icons.py

Outputs into brand/ (sources) and src/templates/static/ (served files):
  icon-1024.png / icon-512.png / icon-192.png   — PWA / app icon (wordmark)
  apple-touch-icon.png (180)                     — iOS
  google-logo-120.png                            — Google consent screen ("H." for legibility)
  favicon-32.png / favicon-16.png / favicon.ico  — browser tab ("H." variant)
  hudhud-icon-master.svg                         — vector master
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT / "brand"
STATIC = ROOT / "src" / "templates" / "static"

# Brand palette (extracted from the site's own CSS)
NAVY = (15, 23, 42, 255)        # #0f172a — sidebar/dark background
WHITE = (248, 250, 252, 255)    # #f8fafc — wordmark text
BLUE = (37, 99, 235, 255)       # #2563eb — the brand dot
FONT_PATH = r"C:\Windows\Fonts\Montserrat-ExtraBold.ttf"
CORNER_RATIO = 0.20             # rounded-square corner radius ratio


def _rounded_bg(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    radius = int(size * CORNER_RATIO)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=NAVY)
    return img


def _font(px: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_PATH, px)


def _draw_wordmark(img: Image.Image, text_full: bool = True) -> None:
    """Centers the wordmark. Wordmark = 'Hudhud' (white) + '.' (blue).
    text_full=False renders the compact 'H.' mark for tiny sizes."""
    size = img.size[0]
    d = ImageDraw.Draw(img)
    if text_full:
        main, dot = "Hudhud", "."
        font_px = int(size * 0.30)
    else:
        main, dot = "H", "."
        font_px = int(size * 0.52)
    f = _font(font_px)
    w_main = d.textlength(main, font=f)
    w_dot = d.textlength(dot, font=f)
    total = w_main + w_dot
    x = (size - total) / 2
    y = (size - font_px) / 2 - font_px * 0.08
    d.text((x, y), main, font=f, fill=WHITE)
    d.text((x + w_main, y), dot, font=f, fill=BLUE)


def _svg_master() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">
  <defs>
    <clipPath id="r"><rect width="1024" height="1024" rx="205"/></clipPath>
  </defs>
  <g clip-path="url(#r)">
    <rect width="1024" height="1024" fill="#0f172a"/>
    <text x="512" y="512" font-family="Montserrat, 'Plus Jakarta Sans', sans-serif"
          font-weight="800" font-size="307" fill="#f8fafc"
          text-anchor="middle" dominant-baseline="central">Hudhud<tspan fill="#2563eb">.</tspan></text>
  </g>
</svg>"""


def main():
    BRAND.mkdir(exist_ok=True)
    (BRAND / "hudhud-icon-master.svg").write_text(_svg_master(), encoding="utf-8")

    # Wordmark sizes (full "Hudhud.")
    for size in (1024, 512, 192):
        img = _rounded_bg(size)
        _draw_wordmark(img, text_full=True)
        img.save(BRAND / f"icon-{size}.png")
        print(f"icon-{size}.png written")

    # Apple touch icon (iOS flattens transparency — opaque bg)
    img = _rounded_bg(180)
    _draw_wordmark(img, text_full=True)
    img.save(BRAND / "apple-touch-icon.png")
    print("apple-touch-icon.png written")

    # Google consent logo (120, compact mark for legibility)
    img = _rounded_bg(120)
    _draw_wordmark(img, text_full=False)
    img.save(BRAND / "google-logo-120.png")
    print("google-logo-120.png written")

    # Favicons (compact mark)
    for size in (32, 16):
        img = _rounded_bg(size)
        _draw_wordmark(img, text_full=False)
        img.save(BRAND / f"favicon-{size}.png")
        print(f"favicon-{size}.png written")

    # favicon.ico (multi-resolution)
    imgs = []
    for size in (16, 32, 48):
        img = _rounded_bg(size)
        _draw_wordmark(img, text_full=False)
        imgs.append(img)
    imgs[0].save(STATIC / "favicon.ico", format="ICO",
                 sizes=[(16, 16), (32, 32), (48, 48)], append_images=imgs[1:])
    print("static/favicon.ico written")

    # Copy served copies into static/
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
