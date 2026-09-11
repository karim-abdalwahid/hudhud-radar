"""
COMPREHENSIVE STATIC AUDIT — WS-A (drift) + WS-B (CSS classes/vars) + WS-E2 (broken names).
Outputs a structured report to docs/PROJECT_REPORTS/AUDIT_2026-09-11_STATIC.md
"""
import re
import sys
import json
import hashlib
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent
TPL = ROOT / "src" / "templates"
OUT = []
S = lambda s: OUT.append(s)

# ================= WS-A: Deployment drift (public assets hash compare) =================
S("# 🔍 Static Audit Report — 2026-09-11\n")
S("## WS-A: Deployment Drift (local vs hudhd.com)\n")
static_dir = TPL / "static"
assets = ["saas.js", "saas.css", "i18n.js"]
drift_rows = []
for a in assets:
    local = (static_dir / a).read_bytes()
    lh = hashlib.sha256(local).hexdigest()[:12]
    try:
        req = urllib.request.Request(f"https://www.hudhd.com/static/{a}?cb={a}", headers={"User-Agent": "Mozilla/5.0", "Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=20) as r:
            remote = r.read()
        rh = hashlib.sha256(remote).hexdigest()[:12]
        drift_rows.append((a, lh, rh, "MATCH" if lh == rh else "**DRIFT**"))
    except Exception as e:
        drift_rows.append((a, lh, "-", f"fetch error: {str(e)[:60]}"))
S("| Asset | Local hash | Production hash | Status |")
S("|---|---|---|---|")
for a, lh, rh, st in drift_rows:
    S(f"| {a} | `{lh}` | `{rh}` | {st} |")
S("")

# ================= WS-B: CSS classes & variables =================
S("## WS-B: CSS Classes & Variables\n")
html_files = list(TPL.rglob("*.html"))
js_files = list(TPL.rglob("*.js"))

# classes used in templates (static class="..." + JS classList/className strings)
used_classes = set()
for f in html_files:
    t = f.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r'class="([^"]+)"', t):
        for c in m.group(1).split():
            if not c.startswith("${") and not c.startswith("$"):
                used_classes.add(c)
for f in js_files:
    t = f.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r"classList\.(?:add|remove|toggle)\(['\"]([\w-]+)['\"]", t):
        used_classes.add(m.group(1))
    for m in re.finditer(r"className\s*=\s*['\"]([^'\"]+)['\"]", t):
        for c in m.group(1).split():
            if not c.startswith("${"):
                used_classes.add(c)

# classes defined in all CSS sources
css_sources = {}
for f in TPL.rglob("*.css"):
    css_sources[f.name] = f.read_text(encoding="utf-8", errors="replace")
for f in html_files:
    t = f.read_text(encoding="utf-8", errors="replace")
    inline = "\n".join(re.findall(r"<style>([\s\S]*?)</style>", t))
    if inline:
        css_sources[f"{f.name}:inline"] = inline

defined_classes = set()
for name, css in css_sources.items():
    for m in re.finditer(r"\.([a-zA-Z][\w-]*)", css):
        defined_classes.add(m.group(1))

# classes referenced but never defined (excluding dynamic/template artifacts)
dynamic_patterns = re.compile(r"^(badge|btn|chip|tab|conv|msg|lead|status|theme|lang|mode|nav|sidebar|panel|form)-?.*$")
unstyled = sorted(c for c in used_classes - defined_classes if len(c) > 3 and not dynamic_patterns.match(c))
S(f"### Classes used but NEVER defined in any CSS ({len(unstyled)})\n")
for c in unstyled[:40]:
    S(f"- `{c}`")
S("")

# CSS variables: used vs defined
used_vars = set()
for name, css in css_sources.items():
    used_vars |= set(re.findall(r"var\(\s*(--[\w-]+)", css))
for f in html_files:
    t = f.read_text(encoding="utf-8", errors="replace")
    used_vars |= set(re.findall(r"var\(\s*(--[\w-]+)", t))
defined_vars = set()
for name, css in css_sources.items():
    defined_vars |= set(re.findall(r"(--[\w-]+)\s*:", css))
missing_vars = sorted(used_vars - defined_vars)
S(f"### CSS variables USED but never DEFINED ({len(missing_vars)})\n")
for v in missing_vars:
    S(f"- `{v}`")
S("")

# ================= WS-E2: i18n hardcoded strings in JS-generated HTML =================
S("## WS-E2: JS-generated HTML with hardcoded user-facing Arabic strings (no data-i18n)\n")
leaks = []
for f in js_files:
    t = f.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r"""(?:innerHTML|insertAdjacentHTML)\s*[=+]?\s*[`'"]([^`'"]{40,400})""", t):
        frag = m.group(1)
        if re.search(r"[\u0600-\u06FF]", frag) and "isAr" not in frag[:60] and "data-i18n" not in frag:
            leaks.append((f.name, frag.strip()[:90]))
S(f"### Suspicious hardcoded Arabic in JS templates ({len(leaks)})\n")
for fname, frag in leaks[:20]:
    S(f"- `{fname}`: `{frag}`")
S("")

# ================= WS-K: cron double-run + env collisions =================
S("## WS-K (static part): scheduler double-run + env collisions\n")
main_src = (ROOT / "src" / "main.py").read_text(encoding="utf-8", errors="replace")
S(f"- main.py lifespan starts in-process scheduler: `{'scheduler_task' in main_src}`")
S(f"- Vercel cron configured (vercel.json): `{'crons' in (ROOT / 'vercel.json').read_text()}`")
cron_admin = (ROOT / "src" / "modules" / "cron_admin" / "routes.py").read_text(encoding="utf-8", errors="replace")
S(f"- cron_admin has its own scheduler tick: `{'scheduler' in cron_admin.lower()}`")
env_keys = [l.split("=")[0].strip() for l in (ROOT / ".env").read_text(encoding="utf-8").splitlines() if re.match(r"^[A-Z_0-9]+\s*=", l)]
dups = [k for k in set(env_keys) if env_keys.count(k) > 1]
S(f"- .env duplicate keys: `{dups if dups else 'none'}`")
S("")

report = "\n".join(OUT)
(ROOT / "docs" / "PROJECT_REPORTS" / "AUDIT_2026-09-11_STATIC.md").write_text(report, encoding="utf-8")
print(report[:3500])
