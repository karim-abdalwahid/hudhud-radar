"""Fabrication sweep: find any backend code producing data NOT from the real APIs."""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PATTERNS = [
    (r"\brandom\.", "random values"),
    (r"\bfake|mock_|_mock", "mock/fake markers"),
    (r"\bsimulat|simulated", "simulation"),
    (r"\bdemo_|sample_|placeholder", "demo/sample/placeholder"),
    (r"fabricat", "fabrication mentions"),
    (r"\bdefault_metric|metrics\s*=\s*\{\s*[\"']?views?[\"']?\s*:\s*\d", "invented metrics"),
    (r"\[\s*\d{2,}\s*,\s*\d{2,}\s*,", "hardcoded number arrays"),
    (r"return\s+\{\s*\"?(id|mid)\":\s*\"(simulated|mock|fake)", "fabricated ids"),
    (r"\"status\":\s*\"success\"[^)]{0,80}no\s+(real|graph|api)", "success-without-api"),
]
hits = []
for f in sorted(Path("src").rglob("*.py")):
    text = f.read_text(encoding="utf-8", errors="replace")
    for i, line in enumerate(text.splitlines(), 1):
        low = line.lower()
        if "# test" in low or 'tests/' in low:
            continue
        for pat, label in PATTERNS:
            if re.search(pat, line, re.I):
                hits.append((str(f), i, label, line.strip()[:120]))

# also: suspicious "fallback" numbers in analytics/insights/feed paths
for f in sorted(Path("src").rglob("*.py")):
    if not re.search(r"analytics|insight|feed|statistics|report", str(f), re.I):
        continue
    text = f.read_text(encoding="utf-8", errors="replace")
    for i, line in enumerate(text.splitlines(), 1):
        if re.search(r"fallback|stub|if not .*real", line, re.I) and re.search(r"\d{2,}", line):
            hits.append((str(f), i, "numeric fallback", line.strip()[:120]))

for h in hits[:80]:
    print(f"{h[0]}:{h[1]} [{h[2]}]  {h[3]}")
print(f"\nTOTAL suspicious lines: {len(hits)}")
