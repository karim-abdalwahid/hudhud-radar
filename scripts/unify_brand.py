"""One-off: unify the brand wordmark to 'hudhud.' across all templates
(matches the approved landing-page logo exactly)."""
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "src" / "templates"

REPLACEMENTS = [
    ('<span class="brand-logo-text">Hudhud</span>', '<span class="brand-logo-text">hudhud</span>'),
    ('<span class="crumb-root" data-i18n="brand.name">Hudhud</span>', '<span class="crumb-root" data-i18n="brand.name">hudhud</span>'),
    ('<span data-i18n="brand.name">Hudhud</span>', '<span data-i18n="brand.name">hudhud</span>'),
    ('<title>Executive Overview - Hudhud</title>', '<title>Executive Overview - hudhud.</title>'),
]

changed = []
for f in TEMPLATES.glob("*.html"):
    text = f.read_text(encoding="utf-8")
    new = text
    for old, repl in REPLACEMENTS:
        new = new.replace(old, repl)
    if new != text:
        f.write_text(new, encoding="utf-8")
        changed.append(f.name)

print("Updated:", changed or "nothing to change")
