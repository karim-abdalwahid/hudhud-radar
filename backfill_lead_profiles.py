"""
Backfill: fetch REAL profiles (name + photo) for existing leads missing them,
using the official Messenger/Instagram Profile API. Zero fabrication — only
fields returned by the Graph API are written. Skips anything not returned.
"""
import os
import sys
import json
import urllib.request
import urllib.parse
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
load_dotenv()

SUPA_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPA_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "")
PAGE_TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN", "")
GRAPH = "https://graph.facebook.com/v21.0"


def graph_get(node, fields):
    url = f"{GRAPH}/{node}?" + urllib.parse.urlencode({"fields": fields, "access_token": PAGE_TOKEN})
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)}


def rest_select(table, params):
    url = f"{SUPA_URL}/rest/v1/{table}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def rest_patch(table, record_id, updates):
    url = f"{SUPA_URL}/rest/v1/{table}?id=eq.{record_id}"
    req = urllib.request.Request(url, data=json.dumps(updates).encode(), method="PATCH",
                                 headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}",
                                          "Content-Type": "application/json", "Prefer": "return=minimal"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.status


def main():
    leads = rest_select("leads", {"select": "*", "order": "created_at.desc", "limit": "200"})
    updated = 0
    for lead in leads:
        fb_id = lead.get("facebook_account_id")
        ig_id = lead.get("instagram_account_id")
        needs = (not lead.get("full_name")) or (not lead.get("avatar_url"))
        if not needs:
            continue

        updates = {}
        if fb_id and str(fb_id).isdigit():
            prof = graph_get(fb_id, "first_name,last_name,name,profile_pic")
            if not prof.get("error"):
                name = prof.get("name") or f"{prof.get('first_name', '')} {prof.get('last_name', '')}".strip()
                if name and not lead.get("full_name"):
                    updates["full_name"] = name
                if prof.get("profile_pic") and not lead.get("avatar_url"):
                    updates["avatar_url"] = prof["profile_pic"]
        elif ig_id:
            prof = graph_get(ig_id, "username,name,profile_pic")
            if not prof.get("error"):
                if prof.get("name") and not lead.get("full_name"):
                    updates["full_name"] = prof["name"]
                if prof.get("username") and not lead.get("username"):
                    updates["username"] = prof["username"]
                if prof.get("profile_pic") and not lead.get("avatar_url"):
                    updates["avatar_url"] = prof["profile_pic"]

        if updates:
            status = rest_patch("leads", lead["id"], updates)
            if status == 200:
                updated += 1
                print(f"  Updated lead {lead['id'][:8]}...: {updates.get('full_name') or lead.get('full_name')} "
                      f"+ avatar={'yes' if updates.get('avatar_url') else 'no'}")
            else:
                print(f"  FAILED patch {lead['id'][:8]}: HTTP {status}")
        else:
            print(f"  Skipped lead {lead['id'][:8]}... (no data returned by API — kept as-is)")

    print(f"\nDone: {updated} lead(s) enriched with real profile data.")


if __name__ == "__main__":
    main()
