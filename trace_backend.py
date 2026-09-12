import re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

src = open("src/modules/analytics/routes.py", encoding="utf-8").read()
print("=== analytics endpoints ===")
print(re.findall(r'@router\.(?:get|post)\("([^"]+)"', src))
print("\n=== any fallback/synthesized numbers? ===")
for m in re.finditer(r"[^\n]*(fallback|synthes|generate.*metric|if not.*real|random|placeholder)[^\n]*", src, re.I):
    print(" ", m.group(0).strip()[:140])

es = open("src/meta_api/extended_api.py", encoding="utf-8").read()
i = es.find("def _store_profile_fallback")
print("\n=== _store_profile_fallback ===")
print(es[i:i+900])

pub = open("src/meta_api/publishing.py", encoding="utf-8").read()
print("\n=== publishing.py: real Graph calls? ===")
print("graph urls:", sorted(set(re.findall(r"graph\.facebook\.com[^\"]*|self\.BASE_URL[^\"]*", pub)))[:12])
for m in re.finditer(r"[^\n]*(fallback|simulat|fake|stub|not implemented)[^\n]*", pub, re.I):
    print("  SUSPECT:", m.group(0).strip()[:140])

cs = open("src/content_studio/service.py", encoding="utf-8").read()
i = cs.find("def delete_post")
print("\n=== studio delete_post ===")
print(cs[i:i+500] if i > 0 else "delete_post NOT in service")
cr = open("src/modules/content/routes.py", encoding="utf-8").read()
i = cr.find('@router.delete("/api/content/posts/{post_id}"')
print("\n=== delete route ===")
print(cr[i:i+700])
