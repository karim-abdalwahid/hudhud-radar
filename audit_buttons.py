"""Button/Wire audit: every onclick + href + fetch in templates mapped to
real backend routes. Reports dead wires, missing handlers, fake paths."""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from src.main import app

# ---- registered routes ----
routes = set()
for r in app.routes:
    m = getattr(r, "methods", set())
    p = getattr(r, "path", "")
    if p and ("GET" in m or "POST" in m or "PUT" in m or "PATCH" in m or "DELETE" in m):
        for method in (m - {"HEAD", "OPTIONS"}):
            routes.add((method, p))

def route_path_exists(path: str) -> bool:
    # match with param segments
    segs = path.split("?")[0].rstrip("/") or "/"
    for _m, tmpl in routes:
        tsegs = tmpl.split("/")
        if len(tsegs) != len(segs.split("/")):
            continue
        ok = True
        for a, b in zip(tsegs, segs.split("/")):
            if a.startswith("{") and a.endswith("}"):
                continue
            if a != b:
                ok = False
                break
        if ok:
            return True
    return False

def norm(js_path: str) -> str:
    js_path = re.sub(r"\$\{[^}]*\}", "PARAM", js_path)
    js_path = re.sub(r"'\s*\+\s*\w+\s*\+\s*'", "PARAM", js_path)
    js_path = re.sub(r"PARAM/[^/?]*", "PARAM", js_path)
    js_path = js_path.replace("PARAM", "x")
    return js_path.split("?")[0]

templates = sorted(Path("src/templates").rglob("*.html"))
inline_modules = []
for f in Path("src/modules").rglob("*.py"):
    if "_HTML" in f.read_text(encoding="utf-8", errors="replace")[:4000] or "onclick=" in f.read_text(encoding="utf-8", errors="replace"):
        inline_modules.append(f)

issues = []
handler_defs = {}
for f in templates + inline_modules:
    text = f.read_text(encoding="utf-8", errors="replace")
    fname = f.name
    # collect function definitions in this file
    defined = set(re.findall(r"(?:async\s+)?function\s+(\w+)\s*\(", text))
    defined |= set(re.findall(r"(\w+)\s*[:(]\s*(?:async\s*)?\(", text))
    # window.FOO = patterns and method defs on objects
    defined |= set(re.findall(r"window\.(\w+)\s*=", text))
    # onclick handlers used
    for m in re.finditer(r"onclick=[\"'`]?[^\"'`>]*?\b(\w+)\s*\(", text):
        fn = m.group(1)
        if fn in ("return", "if", "else", "event", "this", "confirm", "alert"):
            continue
        handler_defs.setdefault(fn, set()).add(fname)
    # fetch endpoints used
    for m in re.finditer(r"fetch\(\s*[`'\"],?\s*([`'\"])([^`'\"{]*)\1", text):
        pass
    for m in re.finditer(r"fetch\((?:fetch\()?\s*[`'\"]([^`'\"]+)[`'\"]", text):
        ep = m.group(1)
        if not ep.startswith("/") or ep.startswith("//"):
            continue
        if "http" in ep:
            ep = "/" + ep.split("/", 3)[-1]
        n = norm(ep)
        if not route_path_exists(n):
            issues.append((fname, "fetch->MISSING ROUTE", ep, n))
    # location.href targets
    for m in re.finditer(r"(?:location\.href\s*=\s*|window\.location\s*=\s*)['\"`]([^'\"`]+)['\"`]", text):
        tgt = m.group(1)
        if tgt.startswith("http") or tgt.startswith("/"):
            n = norm(tgt)
            if not route_path_exists(n):
                issues.append((fname, "navigate->MISSING ROUTE", tgt, n))

# handlers used anywhere but defined in NO file at all
all_defined = set(re.findall(r"(?:async\s+)?function\s+(\w+)\s*\(", " ".join(
    f.read_text(encoding="utf-8", errors="replace") for f in templates + list(Path("src/templates/static").glob("*.js")) + inline_modules)))
all_defined |= set(re.findall(r"(\w+)\s*[:(]\s*(?:async\s*)?\(", " ".join(
    f.read_text(encoding="utf-8", errors="replace") for f in list(Path("src/templates/static").glob("*.js")))))
# also object methods like obj.method = or shorthand in registry objects:
missing_handlers = {fn for fn, files in handler_defs.items() if fn not in all_defined}

print(f"templates scanned: {len(templates)} + {len(inline_modules)} module-inline pages")
print(f"onclick handlers referenced: {len(handler_defs)}")
if missing_handlers:
    print("\n⚠️  handlers referenced but NOT defined anywhere (check if native/aliases):")
    for h in sorted(missing_handlers)[:30]:
        print("   ", h, "used in:", sorted(handler_defs[h])[:3])
else:
    print("\n✅ all referenced handlers defined somewhere")

if issues:
    print(f"\n⚠️  {len(issues)} dead wires (fetch/navigate to missing backend routes):")
    for fname, kind, raw, n in issues:
        print(f"   {fname}: {kind}  raw={raw[:70]}  norm={n}")
else:
    print("✅ zero dead fetch/navigate targets")
