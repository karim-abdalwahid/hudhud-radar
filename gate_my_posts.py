import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "src/core/auth.py"
src = open(p, encoding="utf-8").read()
anchor = '    "/api/threads/publish",'
assert anchor in src
if '"/api/threads/my-posts"' not in src:
    src = src.replace(anchor, anchor + '\n    "/api/threads/my-posts",', 1)
    open(p, "w", encoding="utf-8").write(src)
    print("auth gate added for /api/threads/my-posts")
else:
    print("already gated")
import ast
ast.parse(src)
print("auth.py syntax OK")
