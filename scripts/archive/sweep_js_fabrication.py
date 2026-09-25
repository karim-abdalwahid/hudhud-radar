"""JS + inline-script fabrication sweep (client-side invented data)."""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PATTERNS = [
    (r"Math\.random", "Math.random"),
    (r"(views|impressions|reach|followers|likes|engagement)\s*[:=]\s*[\w\s]*\*\s*\d", "derived-from-multiplier"),
    (r"\b(base|seed|avg|fake|demo|mock|sample)\w*\s*(metrics|views|reach|impressions)", "invented metric vars"),
    (r"\[\s*\d{3,6}\s*,\s*\d{3,6}\s*,\s*\d{3,6}", "hardcoded number series"),
    (r"||\s*\d{4,}\b.*?(views|reach|impressions|followers)", "fallback big numbers"),
    (r"(views|reach|impressions|followers)\s*\|\|\s*\d", "metric or-number fallback"),
    (r"random", "random usage"),
]
hits = []
files = list(Path("src/templates").rglob("*.html")) + list(Path("src/templates").rglob("*.js"))
for f in files:
    text = f.read_text(encoding="utf-8", errors="replace")
    for i, line in enumerate(text.splitlines(), 1):
        for pat, label in PATTERNS:
            if re.search(pat, line, re.I):
                hits.append((f.name, i, label, line.strip()[:130]))
seen = set()
out = []
for h in hits:
    key = (h[0], h[1])
    if key in seen:
        continue
    seen.add(key)
    out.append(h)
for h in out[:60]:
    print(f"{h[0]}:{h[1]} [{h[2]}]  {h[3]}")
print(f"\nTOTAL: {len(out)}")
