import re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
src = open("src/modules/knowledge/routes.py", encoding="utf-8").read()
print("=== knowledge endpoints ===")
print(re.findall(r'@router\.(?:get|post|put|delete)\("([^"]+)"', src))
print("writes kb_documents:", "kb_documents" in src)
print("uses session user:", "verify_session_token" in src or "_session_user" in src)
print("stamps user_id:", "user_id" in src)

src2 = open("src/modules/content/routes.py", encoding="utf-8").read()
print("\n=== content endpoints ===")
print(re.findall(r'@router\.(?:get|post|put|delete)\("([^"]+)"', src2)[:10])
print("stamps user_id:", "user_id" in src2)

src3 = open("src/automations/service.py", encoding="utf-8").read()
print("\n=== automations service ===")
print("file-store:", "automations_store.json" in src3)
print("uses supabase:", "supabase" in src3.lower())
