import re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
src = open("src/modules/auth_module/__init__.py", encoding="utf-8").read()
i = src.find('"/auth/me"')
seg = src[i:i+900]
print("=== /auth/me handler ===")
print(seg)
print("\n=== onboarding has app-topbar? ===")
o = open("src/templates/onboarding.html", encoding="utf-8", errors="replace").read()
print("app-topbar:", "app-topbar" in o, "| app-sidebar:", "app-sidebar" in o)
print("\n=== studio.html fetch endpoints ===")
s = open("src/templates/studio.html", encoding="utf-8", errors="replace").read()
print(sorted(set(re.findall(r"fetch\('([^']+)'", s))))
