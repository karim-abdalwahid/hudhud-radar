"""
Webhook Pipeline Diagnostic — checks every link in the chain WITHOUT printing secrets.
Chain: User message -> Meta -> Webhook POST (hudhd.com) -> HMAC check -> Supabase -> Inbox
"""
import os
import sys
import json
import hmac
import hashlib
import urllib.request
import urllib.parse
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
load_dotenv()

APP_ID = os.getenv("META_APP_ID", "")
APP_SECRET = os.getenv("META_APP_SECRET", "")
PAGE_ID = os.getenv("META_PAGE_ID", "")
PAGE_TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN", "")
VERIFY_TOKEN = os.getenv("META_WEBHOOK_VERIFY_TOKEN", "")
BASE_URL = os.getenv("APP_BASE_URL", "https://www.hudhd.com").rstrip("/")
SUPA_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPA_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "")

GRAPH = "https://graph.facebook.com/v21.0"


def api_get(url, params=None):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except Exception:
            return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


def section(title):
    print(f"\n{'='*60}\n  {title}\n{'='*60}")


def main():
    app_access_token = f"{APP_ID}|{APP_SECRET}"

    # ---------- 1. USER PAGE TOKEN health + scopes ----------
    section("1. PAGE ACCESS TOKEN (META_PAGE_ACCESS_TOKEN) - scopes & validity")
    r = api_get(f"{GRAPH}/debug_token", {
        "input_token": PAGE_TOKEN,
        "access_token": app_access_token
    })
    data = r.get("data", {})
    if data.get("is_valid"):
        print(f"  VALID: Yes")
        print(f"  Type: {data.get('type')}")
        print(f"  App ID matches: {data.get('app_id') == APP_ID}")
        print(f"  Expires: {data.get('expires_at', 'never (long-lived)')}")
        scopes = data.get("scopes", [])
        print(f"  Scopes ({len(scopes)}): {', '.join(scopes) if scopes else 'NONE'}")
        needed = ["pages_messaging", "pages_manage_metadata", "pages_read_engagement",
                  "pages_manage_posts", "pages_show_list", "pages_read_user_content"]
        missing = [s for s in needed if s not in scopes]
        if missing:
            print(f"  >>> MISSING CRITICAL SCOPES: {missing}")
        else:
            print("  >>> All critical page scopes present")
    else:
        print(f"  VALID: NO -> {r.get('error', r.get('data', {}))}")

    # ---------- 2. Page reachable via token ----------
    section(f"2. PAGE REACHABILITY (id={PAGE_ID})")
    r = api_get(f"{GRAPH}/{PAGE_ID}", {
        "fields": "id,name,access_token",
        "access_token": PAGE_TOKEN
    })
    if "error" in r:
        print(f"  ERROR: {r['error'].get('message', r['error'])[:200]}")
    else:
        print(f"  Page name: {r.get('name')}")

    # ---------- 3. THE KEY CHECK: subscribed_apps on the Page ----------
    section("3. PAGE WEBHOOK SUBSCRIPTION (subscribed_apps)  <<< MOST LIKELY CULPRIT")
    r = api_get(f"{GRAPH}/{PAGE_ID}/subscribed_apps", {
        "access_token": PAGE_TOKEN,
        "fields": "id,name,subscribed_fields"
    })
    if "error" in r:
        print(f"  ERROR: {r['error'].get('message', r['error'])[:200]}")
    else:
        apps = r.get("data", [])
        if not apps:
            print("  >>> NO APPS SUBSCRIBED TO THIS PAGE — webhooks will NEVER fire!")
            print("  >>> FIX: POST /{page-id}/subscribed_apps?subscribed_fields=messages,messaging_postbacks,feed")
        for a in apps:
            print(f"  App: {a.get('name')} ({a.get('id')})")
            fields = a.get("subscribed_fields", [])
            print(f"  Subscribed fields ({len(fields)}): {', '.join(fields) if fields else 'NONE'}")
            required = ["messages", "messaging_postbacks", "feed", "messaging_referrals"]
            missing = [f for f in required if f not in fields]
            if missing:
                print(f"  >>> MISSING FIELDS: {missing}")
            else:
                print("  >>> All required fields subscribed")

    # ---------- 4. Production webhook verifier endpoint ----------
    section(f"4. PRODUCTION WEBHOOK VERIFIER ({BASE_URL}/api/webhook/meta)")
    challenge = "diag_" + os.urandom(4).hex()
    r = api_get(f"{BASE_URL}/api/webhook/meta", {
        "hub.mode": "subscribe",
        "hub.challenge": challenge,
        "hub.verify_token": VERIFY_TOKEN,
    })
    if isinstance(r, dict) and r.get("error"):
        print(f"  ERROR: {str(r['error'])[:200]}")
    elif isinstance(r, dict) and r.get("detail"):
        print(f"  REJECTED: {r['detail']}")
    elif challenge in json.dumps(r):
        print(f"  Challenge echoed back: OK")
    else:
        print(f"  Unexpected response: {json.dumps(r)[:200]}")

    # ---------- 5. Simulate a REAL signed webhook POST to production ----------
    section("5. SIMULATED SIGNED WEBHOOK POST (tests HMAC end-to-end on production)")
    payload = {
        "object": "page",
        "entry": [{
            "id": PAGE_ID,
            "time": 1700000000000,
            "messaging": [{
                "sender": {"id": "diag_test_sender"},
                "recipient": {"id": PAGE_ID},
                "timestamp": 1700000000000,
                "message": {"mid": f"diag_{os.urandom(4).hex()}", "text": "Diagnostic test message"}
            }]
        }]
    }
    body = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
    req = urllib.request.Request(
        f"{BASE_URL}/api/webhook/meta",
        data=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"  HTTP {resp.status}: {resp.read().decode()[:200]}")
            print("  >>> If events_queued=1, the production pipeline works end-to-end")
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.read().decode()[:200]}")

    # ---------- 6. Supabase: are messages landing? ----------
    section("6. SUPABASE messages/leads TABLES (latest rows)")
    for table, order in [("messages", "created_at"), ("leads", "created_at")]:
        url = f"{SUPA_URL}/rest/v1/{table}?select=id,created_at&order={order}.desc&limit=3"
        req = urllib.request.Request(url, headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                rows = json.loads(resp.read().decode())
                if rows:
                    for row in rows:
                        print(f"  {table}: id={str(row.get('id'))[:20]} at {row.get('created_at')}")
                else:
                    print(f"  {table}: EMPTY")
        except urllib.error.HTTPError as e:
            body_txt = e.read().decode()[:150]
            if "does not exist" in body_txt or "Could not find" in body_txt or e.code == 404:
                print(f"  {table}: TABLE NOT FOUND")
            else:
                print(f"  {table}: HTTP {e.code} {body_txt}")
        except Exception as e:
            print(f"  {table}: {str(e)[:100]}")

    print("\n" + "="*60 + "\n  DIAGNOSTIC COMPLETE\n" + "="*60)


if __name__ == "__main__":
    main()
