import re, sys, glob
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
print("=== /auth/me response fields ===")
src = open("src/modules/auth_module/__init__.py", encoding="utf-8").read()
i = src.find("/auth/me")
print(src[i:i+600])
print("\n=== inline lang-switcher-btn across templates ===")
for f in glob.glob("src/templates/*.html"):
    t = open(f, encoding="utf-8", errors="replace").read()
    c = t.count("lang-switcher-btn")
    if c:
        print(f"  {f}: {c}")
print("\n=== studio synced-content endpoints ===")
src2 = open("src/modules/content/routes.py", encoding="utf-8").read()
print([m for m in re.findall(r'@router\.(?:get|post)\("([^"]+)"', src2)])
print("meta_live_cache used in routes:", "meta_live_cache" in src2 or "feed_sync" in src2)
print("\n=== threads insights UI present? ===")
for f in glob.glob("src/templates/*.html"):
    t = open(f, encoding="utf-8", errors="replace").read()
    if "/api/threads/insights" in t:
        print("  referenced in:", f)
