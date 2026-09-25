"""Remove duplicate inline language buttons from dashboard templates
(the saas.js globe on .app-topbar is the single control). Landing/auth/
onboarding keep theirs (no app-topbar there)."""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DASH = ["analytics.html", "automations.html", "identity.html", "inbox.html",
        "knowledge.html", "leads.html", "overview.html", "settings.html",
        "studio.html"]

pat = re.compile(
    r'\s*<button[^>]*class="lang-switcher-btn"[^>]*>\s*'
    r'(?:<span[^>]*>.*?</span>\s*)?</button>', re.S)

for name in DASH:
    p = f"src/templates/{name}"
    t = open(p, encoding="utf-8", errors="replace").read()
    new = pat.sub("", t, count=1)
    removed = len(t) - len(new)
    if removed:
        open(p, "w", encoding="utf-8").write(new)
    print(f"{name}: removed {removed} chars of duplicate lang button")
