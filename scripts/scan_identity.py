"""Identity scanner (S-Purge): no personal/business identity in platform code.

Scans all src/*.py + templates for known personal/business identifiers.
Any hit = platform-branded to one business — a violation of the neutral
SaaS architecture (Entry 035 / R16).
"""
from pathlib import Path

FORBIDDEN = [
    "إبدأ ماركتينج", "ابدأ ماركتينج", "Ebd'a Marketing", "ebdamarketing",
    "كريم عبد الواحد", "كريم عبدالواحد", "Karim Abdalwahid", "karim__abdalwahid",
    "كريم عبد", "with Karim", "مع كريم",
]

# Files where the brand wordmark "Hudhud" is fine; personal names are never.
roots = [Path("src")]
hits = []

for root in roots:
    for p in root.rglob("*"):
        if p.suffix not in (".py", ".html", ".js") or not p.is_file():
            continue
        if "test" in p.name.lower() or p.parts[0] == "tests":
            continue
        txt = p.read_text(encoding="utf-8", errors="ignore")
        for pat in FORBIDDEN:
            for i, line in enumerate(txt.splitlines(), 1):
                if pat in line:
                    hits.append(f"{p}:{i}: [{pat}] {line.strip()[:80]}")

if hits:
    print(f"PERSONAL IDENTITY FOUND ({len(hits)}):")
    for h in hits:
        print(" ", h)
    raise SystemExit(1)
print("CLEAN — no personal/business identity in platform code")
