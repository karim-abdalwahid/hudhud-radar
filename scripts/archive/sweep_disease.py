"""Cross-site hunter for the same disease classes:
A. unguarded request.json() / .json() on bodies
B. parsers/loops assuming dict/list without isinstance
C. DB calls with raw user-controlled id segments (500 risk)
D. handlers that mutate memory/DB but whose data never reaches a UI read endpoint
"""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path("src")

# ---- A: unguarded await request.json() ----
print("=== A) request.json() call sites (check each for try/except) ===")
for f in sorted(ROOT.rglob("*.py")):
    txt = f.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r"(\w+)\s*=\s*await\s+request\.json\(\)", txt):
        line = txt[:m.start()].count("\n") + 1
        # look back 3 lines for try:
        prev = txt.split("\n")[max(0, line - 4):line - 1]
        guarded = any("try:" in p for p in prev)
        print(f"  {'OK  ' if guarded else 'UNGUARDED'}  {f}:{line}")

# ---- B: for-loop .get on JSON structure without isinstance guard ----
print("\n=== B) payload-iteration .get chains without isinstance guard (webhook-ish files) ===")
targets = [f for f in sorted(ROOT.rglob("*.py"))
           if re.search(r"request\.json|payload|webhook|change\.get|entry", f.read_text(encoding='utf-8', errors='replace')[:20000] if f.exists() else "")]
count = 0
for f in sorted(ROOT.rglob("*.py")):
    txt = f.read_text(encoding="utf-8", errors="replace")
    if "await request.json()" not in txt:
        continue
    for m in re.finditer(r"for (\w+) in (\w+)\.get\(([^)]+)\):\n\s+(if not isinstance)", txt):
        pass
    # crude: count loops over .get lists and how many isinstance guards exist
    loops = len(re.findall(r"for \w+ in \w+\.get\(", txt))
    guards = txt.count("isinstance")
    print(f"  {f}: loops={loops} isinstance={guards}")

# ---- C: user-controlled path ids reaching select/eq without validation ----
print("\n=== C) path-id -> db call sites (potential invalid-uuid 500s) ===")
for f in sorted(ROOT.rglob("*.py")):
    txt = f.read_text(encoding="utf-8", errors="replace")
    # endpoints that take *_id: str path params and pass them to db.select/update/delete
    eps = re.findall(r"async def (\w+)\((?:[^)]*?)(\w*_id): str", txt)
    for name, idname in eps:
        # find body mention of the id with db calls
        i = txt.find(f"async def {name}(")
        body = txt[i:i + 1200]
        if re.search(r"db\.(select|update|delete)\(|\.eq\(", body):
            print(f"  {f.name}:{name}  id={idname}")
