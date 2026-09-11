import os, json, urllib.request, urllib.parse, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import load_dotenv
load_dotenv()
IG_ID = os.getenv("META_INSTAGRAM_ACCOUNT_ID")
tok = os.getenv("META_PAGE_ACCESS_TOKEN")

url = (f"https://graph.facebook.com/v21.0/{IG_ID}/media?"
       + urllib.parse.urlencode({
           "fields": "id,media_product_type,like_count,comments_count,timestamp",
           "limit": "5", "access_token": tok}))
with urllib.request.urlopen(url, timeout=15) as r:
    data = json.loads(r.read().decode())
print(json.dumps(data, indent=1)[:900])

# pick the newest reel and get insights (views + plays)
mid = data["data"][0]["id"]
for metric in ("views", "plays", "impressions", "reach"):
    u = (f"https://graph.facebook.com/v21.0/{mid}/insights?"
         + urllib.parse.urlencode({"metric": metric, "access_token": tok}))
    try:
        with urllib.request.urlopen(u, timeout=15) as r:
            print(metric, "->", json.loads(r.read().decode()))
    except Exception as e:
        print(metric, "->", str(e)[:120])
