import os, json, urllib.request, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import load_dotenv
load_dotenv()
ref = os.getenv("SUPABASE_PROJECT_REF"); tok = os.getenv("SUPABASE_MANAGEMENT_TOKEN")
sql = ("UPDATE public.content_posts SET user_id = '8d0ab6c3-544d-4a14-84c9-d021acf26ddf' "
       "WHERE user_id IS NULL;")
req = urllib.request.Request(
    f"https://api.supabase.com/v1/projects/{ref}/database/query",
    data=json.dumps({"query": sql}).encode(), method="POST",
    headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=30) as r:
    print("Backfill content_posts -> owner:", r.status)
