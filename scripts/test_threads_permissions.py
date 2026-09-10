"""
Threads API — App Review usage calls for ALL requested threads_* permissions.

Run after: python scripts/fetch_platform_tokens.py threads
     then: python scripts/test_threads_permissions.py

Publishes ONE clearly-labeled test post to the connected Threads account,
exercises replies/insights on it, and deletes it when threads_delete scope
is present (create -> publish -> read -> insights -> delete = full lifecycle).
"""
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://graph.threads.net/v1.0"
TEST_TEXT = "Hudhud App Review test post — will be deleted shortly."


def env(k, default=""):
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(k + "="):
            return line.split("=", 1)[1].strip()
    return default


results = []


def report(name, permission, ok, detail=""):
    results.append((permission, ok))
    print(f"  {'✅' if ok else '❌'} {name} [{permission}] {detail}")


def call(name, permission, method, url, data=None, params=None):
    try:
        r = httpx.request(method, url, data=data or {}, params=params or {}, timeout=30)
        err = ""
        if r.status_code != 200:
            try:
                j = r.json().get("error", {})
                err = j.get("message", "")[:140]
            except Exception:
                err = r.text[:140]
        report(name, permission, r.status_code == 200, f"→ {r.status_code} {err}".strip())
        try:
            return r.json() if r.status_code == 200 else None
        except Exception:
            return None
    except Exception as e:
        report(name, permission, False, f"EXC {str(e)[:100]}")
        return None


def main():
    tok = env("THREADS_ACCESS_TOKEN")
    user = env("THREADS_USER_ID") or "me"
    if not tok:
        print("THREADS_ACCESS_TOKEN missing — run scripts/fetch_platform_tokens.py threads first")
        sys.exit(1)

    # token scopes
    r = httpx.get(f"{BASE}/me", params={"fields": "id,username",
                                        "access_token": tok}, timeout=30)
    me = r.json() if r.status_code == 200 else {}
    print(f"\n=== Threads usage — account: {me.get('username')} ({me.get('id')}) ===\n")
    report("GET /me (profile)", "threads_basic", r.status_code == 200,
           f"→ {r.status_code}")

    # existing posts (for replies/insights targets)
    own = call("GET /me/threads (own posts)", "threads_manage_replies",
               "GET", f"{BASE}/{user}/threads",
               params={"fields": "id,text,timestamp,media_type", "limit": 5,
                       "access_token": tok})
    posts = (own or {}).get("data", [])

    # publish lifecycle: container -> publish
    c = call("POST /{user}/threads (TEXT container)", "threads_content_publish",
             "POST", f"{BASE}/{user}/threads",
             data={"media_type": "TEXT", "text": TEST_TEXT, "access_token": tok})
    container = (c or {}).get("id")
    published_id = None
    if container:
        p = call("POST /{user}/threads_publish", "threads_content_publish",
                 "POST", f"{BASE}/{user}/threads_publish",
                 data={"creation_id": container, "access_token": tok})
        published_id = (p or {}).get("id")
        print(f"     published test post: {published_id}")

    target = published_id or (posts[0]["id"] if posts else None)

    # replies read
    if target:
        call("GET /{media}/replies", "threads_read_replies",
             "GET", f"{BASE}/{target}/replies",
             params={"fields": "id,text,timestamp,username", "access_token": tok})

    # insights (account-level + media-level)
    call("GET /me/threads_insights", "threads_manage_insights",
         "GET", f"{BASE}/me/threads_insights",
         params={"metric": "views,likes,replies", "access_token": tok})
    if target:
        call("GET /{media}/insights", "threads_manage_insights",
             "GET", f"{BASE}/{target}/insights",
             params={"metric": "views,likes,replies", "access_token": tok})

    # delete our test post (requires threads_delete scope on the token)
    if published_id:
        d = call("DELETE /{media} (our test post)", "threads_delete",
                 "DELETE", f"{BASE}/{published_id}", params={"access_token": tok})
        if not d:
            print("     ⚠️ test post NOT deleted (scope missing?) — delete it manually")

    # discovery / keyword search (need their scopes on the token)
    call("GET /{user}?fields=username (discovery)", "threads_profile_discovery",
         "GET", f"{BASE}/{user}", params={"fields": "username", "access_token": tok})
    call("GET /keyword_search", "threads_keyword_search",
         "GET", f"{BASE}/keyword_search",
         params={"q": "marketing", "access_token": tok})

    # mentions — no reliable read edge without an actual mention; attempt documents the gate
    call("GET /me/mentions (attempt)", "threads_manage_mentions",
         "GET", f"{BASE}/me/mentions", params={"access_token": tok})

    ok = sum(1 for _, s in results if s)
    print(f"\n=== SUMMARY: {ok}/{len(results)} calls succeeded ===")
    print("Dashboard counters refresh with delay (24h+) — usage is logged by Meta now.")
    if not any(p == "threads_delete" and s for p, s in results):
        print("threads_delete NOT exercised — either add threads_delete to the OAuth scopes")
        print("and re-fetch the token, or REMOVE the permission from the review list.")


if __name__ == "__main__":
    main()
