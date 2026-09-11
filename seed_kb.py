"""Seed kb_documents with the owner's real knowledge files (one-time migration)."""
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

from src.knowledge.db_knowledge_base import db_knowledge_base
from src.core.supabase_client import supabase_db

OWNER_ID = "8d0ab6c3-544d-4a14-84c9-d021acf26ddf"  # hudhud.support@gmail.com (owner)
CORE = {"business_profile.md", "products_and_services.md", "sales_scripts_and_closing.md",
        "faqs.md", "brand_tone.md"}
SKIP = {"uploaded_test.md"}  # test artifact

kb_dir = Path("docs/KNOWLEDGE_BASE")
files = sorted(kb_dir.glob("*.md"))
print(f"local files: {[f.name for f in files]}")

for f in files:
    if f.name in SKIP:
        print(f"  SKIP {f.name} (test artifact)")
        continue
    content = f.read_text(encoding="utf-8", errors="replace")
    if not content.strip():
        print(f"  SKIP {f.name} (empty)")
        continue
    r = db_knowledge_base.save_document(
        f.name, content, source="seed_local_migration",
        user_id=OWNER_ID, is_core=f.name in CORE)
    print(f"  SEEDED {f.name}: {str(r)[:80]}")

# verify
rows = supabase_db.select("kb_documents") or []
print(f"\nkb_documents rows now: {len(rows)}")
for r in rows:
    print(f"  - {r.get('filename')} (core={r.get('is_core')}, user={str(r.get('user_id'))[:8]}, {len(r.get('content') or '')} chars)")
