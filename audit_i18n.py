"""
i18n Audit: scans ALL templates for data-i18n / data-i18n-ph keys and
cross-checks them against the EN and AR dictionaries in i18n.js.
Outputs every missing key per language so nothing leaks as raw text.
"""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent
TPL = ROOT / "src" / "templates"
I18N = TPL / "static" / "i18n.js"

used = set()
for f in TPL.rglob("*.html"):
    text = f.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r'data-i18n(?:-ph)?="([^"]+)"', text):
        used.add(m.group(1))
    # keys used from JS: t('key') / hudhudI18n.t("key")
for f in TPL.rglob("*.js"):
    text = f.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r"""\bt\(\s*['"]([a-zA-Z0-9_.-]+)['"]\s*\)""", text):
        used.add(m.group(1))

js = I18N.read_text(encoding="utf-8", errors="replace")

# Split dictionaries: en block and ar block (order of declaration)
en_match = re.search(r"en\s*:\s*\{", js)
ar_match = re.search(r"ar\s*:\s*\{", js)
en_block = js[en_match.start(): ar_match.start()] if en_match and ar_match else ""
ar_block = js[ar_match.start():] if ar_match else ""

def keys_in(block):
    return set(re.findall(r'"([a-zA-Z0-9_.-]+)"\s*:', block))

en_keys = keys_in(en_block)
ar_keys = keys_in(ar_block)

missing_en = sorted(k for k in used if k not in en_keys)
missing_ar = sorted(k for k in used if k not in ar_keys)

print(f"Used keys: {len(used)}  |  EN dict: {len(en_keys)}  |  AR dict: {len(ar_keys)}")
print(f"\n=== MISSING IN EN ({len(missing_en)}) ===")
for k in missing_en:
    print(" ", k)
print(f"\n=== MISSING IN AR ({len(missing_ar)}) ===")
for k in missing_ar:
    print(" ", k)
