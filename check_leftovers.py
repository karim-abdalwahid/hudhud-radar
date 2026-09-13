import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
b = open("src/modules/billing/__init__.py", encoding="utf-8").read()
i = b.find("quote")
print("--- quote route ---")
print(b[i-200:i+600])

from src.core.supabase_client import supabase_db
print("\n=== leftover AUDIT rows check ===")
wfs = supabase_db.select("automations_workflows") or []
print("automations_workflows:", [(w["id"], w["name"]) for w in wfs][:8])
kb = supabase_db.select("kb_documents", {"filename": "like.audit_smoke"}) if False else supabase_db.select("kb_documents") or []
print("kb docs:", [d["filename"] for d in kb])
nots = supabase_db.select("notifications") or []
print("recent notif titles:", [n.get("title") for n in sorted(nots, key=lambda x: x.get("created_at") or "")[-5:]])
posts = supabase_db.select("content_posts", {"status": "draft"}) or []
print("draft posts with AUDIT:", [p["content_text"][:30] for p in posts if "AUDIT" in (p.get("content_text") or "")])
