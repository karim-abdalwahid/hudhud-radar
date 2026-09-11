import re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
src = open("src/templates/overview.html", encoding="utf-8").read()

print("=== create post mentions ===")
for m in re.finditer(r"[^\n]*[Cc]reate[^\n]*[Pp]ost[^\n]*", src):
    print(" ", m.group(0).strip()[:170])

print("\n=== /studio links in overview ===")
for m in re.finditer(r'href="([^"]*studio[^"]*)"', src):
    print(" ", m.group(1))

print("\n=== app-topbar block ===")
i = src.find("app-topbar")
print(src[i-40:i+900])
