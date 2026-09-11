"""Locate usage context of potentially-missing CSS classes (filter false positives)."""
import re, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TPL = Path("src/templates")
targets = ["active-filter", "card-thumb-wrap", "connection-line", "font-bold",
           "hero-content", "hero-mockup-wrap", "metrics-pill-group", "np-h-name",
           "np-h-value", "np-model-id", "np-model-name", "set-tab", "thumb-fallback",
           "badge-fb", "badge-ig", "badge-muted", "badge-neutral", "badge-pending", "published"]
for t in targets:
    hits = []
    for f in list(TPL.rglob("*.html")) + list(TPL.rglob("*.js")):
        txt = f.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(re.escape(t), txt):
            ctx = txt[max(0, m.start()-50):m.end()+30].replace("\n", " ")
            # is it a CSS definition in this file?
            if re.search(r"\." + re.escape(t) + r"\s*[{,:]", txt):
                hits.append(f"{f.name}: DEFINED in its own <style>")
                break
            hits.append(f"{f.name}: {ctx[:90]!r}")
            if len(hits) >= 3:
                break
    print(f"--- {t}")
    for h in hits[:3]:
        print(f"    {h}")
