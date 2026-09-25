"""App Review verification: ads account reality + campaigns data + identity chip."""
import os, json, urllib.request, urllib.parse, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import load_dotenv
load_dotenv()
TOK = os.getenv("META_PAGE_ACCESS_TOKEN")
G = "https://graph.facebook.com/v21.0"

def get(node, fields, tok=None):
    url = f"{G}/{node}?" + urllib.parse.urlencode({"fields": fields, "access_token": tok or TOK})
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode()[:150]}

print("=== 1. Ad accounts reachable by the page token ===")
r = get("me/adaccounts", "id,name,account_status,currency")
if "error" in r:
    print("  ERROR:", r["error"])
else:
    accts = r.get("data", [])
    print(f"  ad accounts: {len(accts)}")
    for a in accts[:3]:
        print("   -", a.get("name"), "| status:", a.get("account_status"))
        # campaigns in this account
        cid = a["id"]
        camps = get(f"{cid}/campaigns", "id,name,status,effective_status,objective", TOK)
        if "error" in camps:
            print("     campaigns error:", str(camps["error"])[:100])
        else:
            cl = camps.get("data", [])
            print(f"     campaigns: {len(cl)}")
            for c in cl[:5]:
                print("      *", c.get("name"), "|", c.get("effective_status"))

print("\n=== 2. Users table identity fields (public_profile readiness) ===")
import urllib.request as u2
SUPA = os.getenv("SUPABASE_URL").rstrip("/")
KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
req = u2.Request(SUPA + "/rest/v1/users?select=email,full_name,avatar_url,role", headers={"apikey": KEY, "Authorization": "Bearer " + KEY})
with u2.urlopen(req, timeout=15) as r2:
    for row in json.loads(r2.read().decode()):
        print(f"  {row.get('email'):<32} name={row.get('full_name')!r} avatar={'yes' if row.get('avatar_url') else 'NO'}")
