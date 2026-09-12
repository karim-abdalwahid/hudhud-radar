"""JS fabrication sweep v2 (fixed regexes, JS-only lines)."""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PATTERNS = [
    (r"Math\.random\s*\(", "Math.random"),
    (r"\b(?:views|impressions|reach|followers|likes|engagement|comments)\w*\s*[:=][^;\n]*\*\s*\d+", "derived-by-multiplier"),
    (r"\[\s*\d{3,6}\s*,\s*\d{3,6}\s*,\s*\d{3,6}", "hardcoded number series"),
    (r"\b(?:fake|mock|demo|sample|dummy|placeholder)(?:_\w+)?\b", "fake/mock markers"),
    (r"(?:views|reach|impressions|followers)\b[^;\n]{0,40}\|\|\s*\d+", "metric or-number fallback"),
    (r"\?(?:base|seed)\w*\b.*(?:views|reach|impressions|followers)", "seeded metrics"),
]
hits = []
for f in sorted(Path("src/templates").rglob("*.html")) + sorted(Path("src/templates").rglob("*.js")):
    for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        for pat, label in PATTERNS:
            if re.search(pat, line, re.I):
                hits.append((f.name, i, label, line.strip()[:140]))
for h in hits:
    print(f"{h[0]}:{h[1]} [{h[2]}]  {h[3]}")
print(f"\nTOTAL: {len(hits)}")
