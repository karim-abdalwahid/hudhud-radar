"""Layer-1 fixes (ruff findings — backend only, zero UI):
1. polar.py: missing `List` import (would NameError on real checkout webhook events).
2. meta/routes: remove local shadow of _meta_status_cache/META_STATUS_CACHE_TTL
   (it split the cache from the context-owned one the tests/other code share).
3. cron_admin/routes: remove duplicate _verify_cron_secret definition (the
   context-imported one is canonical; two copies can drift)."""
import ast
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 1. polar List import
p = "src/payments/polar.py"
src = open(p, encoding="utf-8").read()
old = "from typing import Any, Dict, Optional"
assert old in src
src = src.replace(old, "from typing import Any, Dict, List, Optional", 1)
open(p, "w", encoding="utf-8").write(src)
ast.parse(src)
print("1. polar.py: List imported")

# 2. meta routes shadow removal (keep the context import)
p = "src/modules/meta/routes.py"
src = open(p, encoding="utf-8").read()
shadow = '''import time

_meta_status_cache: Dict[str, Any] = {"ts": 0.0, "data": None}
META_STATUS_CACHE_TTL = 60.0
'''
assert shadow in src, "shadow block not found"
src = src.replace(shadow, "import time\n", 1)
open(p, "w", encoding="utf-8").write(src)
ast.parse(src)
print("2. meta routes: context cache used (shadow removed)")

# 3. cron_admin duplicate def removal
p = "src/modules/cron_admin/routes.py"
src = open(p, encoding="utf-8").read()
i = src.find("def _verify_cron_secret(request: Request):")
assert i > 0
# find end: next top-level statement after the def block
lines = src.split("\n")
start = src[:i].count("\n")
end = start
depth_seen = False
for j in range(start + 1, len(lines)):
    ln = lines[j]
    if ln.strip() == "":
        continue
    if not ln.startswith((" ", "\t", "#")):  # next top-level construct
        end = j
        break
    depth_seen = True
else:
    end = len(lines)
block = "\n".join(lines[start:end]).rstrip() + "\n\n\n"
assert block in src
src = src.replace(block, "", 1)
open(p, "w", encoding="utf-8").write(src)
ast.parse(src)
print("3. cron_admin: duplicate _verify_cron_secret removed (uses context's)")
