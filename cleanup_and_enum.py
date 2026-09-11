"""Cleanup: delete the audit test thread + inspect lead_source_enum values."""
import asyncio, json, os, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

from src.meta_api.extended_api import threads_publisher


async def main():
    d = await threads_publisher.delete_thread("18218978428323231")
    print("delete test thread:", d)

import os
ref = os.getenv("SUPABASE_PROJECT_REF"); tok = os.getenv("SUPABASE_MANAGEMENT_TOKEN")
req = urllib.request.Request(
    f"https://api.supabase.com/v1/projects/{ref}/database/query",
    data=json.dumps({"query": "SELECT t.typname, e.enumlabel FROM pg_type t JOIN pg_enum e ON e.enumtypid=t.oid WHERE t.typname ILIKE '%lead%' OR t.typname ILIKE '%source%' ORDER BY t.typname, e.enumsortorder;"}).encode(),
    method="POST", headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=30) as r:
    print(json.dumps(json.loads(r.read().decode()), indent=1))

asyncio.run(main())
