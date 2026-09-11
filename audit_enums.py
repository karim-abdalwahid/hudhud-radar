"""Enumerate ALL enum types + cleanup second test thread."""
import asyncio, json, os, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from src.meta_api.extended_api import threads_publisher

ref = os.getenv("SUPABASE_PROJECT_REF"); tok = os.getenv("SUPABASE_MANAGEMENT_TOKEN")
def sql(q):
    req = urllib.request.Request(
        f"https://api.supabase.com/v1/projects/{ref}/database/query",
        data=json.dumps({"query": q}).encode(), method="POST",
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

async def cleanup():
    d = await threads_publisher.delete_thread("18121592207305061")
    print("delete 2nd test thread:", d)

enums = sql("""
SELECT t.typname AS enum_name, e.enumlabel AS val, e.enumsortorder AS ord
FROM pg_type t JOIN pg_enum e ON e.enumtypid = t.oid
ORDER BY t.typname, e.enumsortorder;
""")
cur = None
for row in enums:
    if row["enum_name"] != cur:
        cur = row["enum_name"]
        print(f"\n{cur}:")
    print(f"   {row['val']}")

print("\n--- columns using each enum:")
cols = sql("""
SELECT table_name, column_name, udt_name FROM information_schema.columns
WHERE table_schema='public' AND udt_name IN ('lead_source_enum','platform_enum')
ORDER BY table_name;
""")
for c in cols:
    print(f"   {c['table_name']}.{c['column_name']} -> {c['udt_name']}")

asyncio.run(cleanup())
