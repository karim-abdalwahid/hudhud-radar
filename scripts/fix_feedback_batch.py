"""One-off fixes per owner feedback:
1. Brand wordmark: 'Hudhud' (capital H) everywhere — matches homepage i18n.
2. Auth page placeholders must switch AR/EN with the language toggle.
3. Standardize canonical domain hudhud-radar.vercel.app in settings callbacks
   + config default + App Review guide.
"""
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "src" / "templates"

# 1. Wordmark capital H everywhere (spans + titles + JS fallbacks)
REPLACEMENTS = [
    ('<span class="brand-logo-text">hudhud</span>', '<span class="brand-logo-text">Hudhud</span>'),
    ('<span class="crumb-root" data-i18n="brand.name">hudhud</span>', '<span class="crumb-root" data-i18n="brand.name">Hudhud</span>'),
    ('<span data-i18n="brand.name">hudhud</span>', '<span data-i18n="brand.name">Hudhud</span>'),
    ('<title>Executive Overview - hudhud.</title>', '<title>Executive Overview - Hudhud.</title>'),
]

changed = []
for f in TEMPLATES.rglob("*.html"):
    text = f.read_text(encoding="utf-8")
    new = text
    for old, repl in REPLACEMENTS:
        new = new.replace(old, repl)
    if new != text:
        f.write_text(new, encoding="utf-8")
        changed.append(f.name)

# saas.js sidebar fallback
saas = TEMPLATES / "static" / "saas.js"
t = saas.read_text(encoding="utf-8")
if '<span class="brand-logo-text">hudhud</span>' in t:
    t = t.replace('<span class="brand-logo-text">hudhud</span>', '<span class="brand-logo-text">Hudhud</span>')
    saas.write_text(t, encoding="utf-8")
    changed.append("saas.js")

# 2. Canonical domain standardization
STEELE = "hudhud-radar-steel.vercel.app"
CANON = "hudhud-radar.vercel.app"
for f in TEMPLATES.rglob("*.html"):
    text = f.read_text(encoding="utf-8")
    if STEELE in text:
        f.write_text(text.replace(STEELE, CANON), encoding="utf-8")
        changed.append(f"{f.name} (domain)")

# config.py default
config = Path(__file__).resolve().parent.parent / "src" / "config.py"
t = config.read_text(encoding="utf-8")
if STEELE in t:
    config.write_text(t.replace(STEELE, CANON), encoding="utf-8")
    changed.append("config.py (domain)")

# App Review guide
guide = Path(__file__).resolve().parent.parent / "PROJECT_BRAIN" / "Roadmap" / "META_APP_REVIEW_GUIDE.md"
t = guide.read_text(encoding="utf-8")
if STEELE in t:
    guide.write_text(t.replace(STEELE, CANON), encoding="utf-8")
    changed.append("META_APP_REVIEW_GUIDE.md (domain)")

print("Updated:", changed or "nothing")
