import asyncio, json, os, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from src.meta_api.extended_api import threads_publisher
from src.core.supabase_client import supabase_db

async def cleanup():
    d = await threads_publisher.delete_thread("18097344728566031")
    print("delete 3rd test thread:", d)

threads = supabase_db.select("leads", {"source": "threads"}) or []
print(f"Threads leads in CRM: {len(threads)}")
for l in threads:
    print(f"  username={l.get('username')} name={l.get('full_name')} avatar={'yes' if l.get('avatar_url') else 'no'} threads_id={l.get('threads_account_id')}")
    msgs = supabase_db.select("messages", {"lead_id": l["id"]}) or []
    for m in msgs:
        print(f"    message: [{m.get('platform')}] {str(m.get('content'))[:60]!r}")

asyncio.run(cleanup())
