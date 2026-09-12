"""Delete ztest_audit.md wherever it lives (any owner), then verify phase C user-scoped sync."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from src.core.supabase_client import supabase_db

# delete by raw query (any user)
deleted = []
try:
    rows = supabase_db.client.table("kb_documents").select("id,user_id").eq("filename", "ztest_audit.md").execute().data
    for r in rows:
        supabase_db.client.table("kb_chunks").delete().eq("document_id", r["id"]).execute()
        supabase_db.client.table("kb_documents").delete().eq("id", r["id"]).execute()
        deleted.append(str(r.get("user_id"))[:8])
except Exception as e:
    print("delete error:", e)
print("ztest deleted (user):", deleted)
if deleted:
    import os
    fp = "docs/KNOWLEDGE_BASE/ztest_audit.md"
    if os.path.exists(fp):
        os.remove(fp)
        print("local test file removed too")

# remaining docs per user
docs = supabase_db.client.table("kb_documents").select("filename,user_id,source").execute().data
print("\nkb_documents now:")
for d in docs:
    print(f"  {d['filename']:<28} user={str(d.get('user_id'))[:8] or 'NULL'} src={d.get('source')}")
