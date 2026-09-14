import ast
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "src/main.py"
src = open(p, encoding="utf-8").read()

guard_start = src.find("# --------------------------------------------------------------------\n# UUID-segment guard")
guard_end = src.find("# --------------------------------------------------------------------\n# Static assets")
assert 0 < guard_start < guard_end
guard_block = src[guard_start:guard_end].rstrip() + "\n\n\n"
src = src[:guard_start] + src[guard_end:]

anchor = '@app.middleware("http")\nasync def auth_middleware'
assert anchor in src
src = src.replace(anchor, guard_block + anchor, 1)
open(p, "w", encoding="utf-8").write(src)
ast.parse(src)

# verify order: guard defined before auth => auth runs FIRST (last-added is outermost)
gi = src.find("async def uuid_segment_guard")
ai = src.find("async def auth_middleware")
print("uuid guard defined before auth (auth runs first):", gi < ai)
