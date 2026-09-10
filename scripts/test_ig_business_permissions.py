"""
Instagram API with Instagram Login (instagram_business_*) — App Review usage.

Run after: python scripts/fetch_platform_tokens.py ig
     then: python scripts/test_ig_business_permissions.py

All calls target graph.instagram.com with the Instagram-user token.
Publish test = media CONTAINER only (never published — nothing visible).
"""
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://graph.instagram.com/v23.0"
CONTAINER_IMAGE = "https://www.hudhd.com/static/icon-512.png"


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
    tok = env("IG_BUSINESS_ACCESS_TOKEN")
    uid = env("IG_BUSINESS_USER_ID")
    if not tok:
        print("IG_BUSINESS_ACCESS_TOKEN missing — run scripts/fetch_platform_tokens.py ig first")
        sys.exit(1)

    me = call("GET /{ig-user} (identity)", "instagram_business_basic",
              "GET", f"{BASE}/{uid}",
              params={"fields": "user_id,username,account_type,media_count",
                      "access_token": tok})
    print(f"\n=== IG Business usage — {me or uid} ===\n")

    # insights (metrics valid for IG-login API; fallback tried on failure)
    ins = call("GET /{ig-user}/insights", "instagram_business_manage_insights",
               "GET", f"{BASE}/{uid}/insights",
               params={"metric": "reach,follower_count", "period": "day",
                       "date_preset": "last_7d", "access_token": tok})
    if not ins:
        call("GET /{ig-user}/insights (fallback views)", "instagram_business_manage_insights",
             "GET", f"{BASE}/{uid}/insights",
             params={"metric": "views", "period": "day",
                     "date_preset": "last_7d", "access_token": tok})

    # content publish = container only (auto-expires unpublished, nothing visible)
    c = call("POST /{ig-user}/media (container)", "instagram_business_content_publish",
             "POST", f"{BASE}/{uid}/media",
             data={"image_url": CONTAINER_IMAGE,
                   "caption": "internal test container — never published",
                   "access_token": tok})
    container_id = (c or {}).get("id")
    print(f"     container: {container_id} (not published)")

    # comments read
    media = call("GET /{ig-user}/media + comments", "instagram_business_manage_comments",
                 "GET", f"{BASE}/{uid}/media",
                 params={"fields": "id,comments{text,username}", "limit": 5,
                         "access_token": tok})
    mlist = (media or {}).get("data", [])
    if mlist:
        call("GET /{media}/comments", "instagram_business_manage_comments",
             "GET", f"{BASE}/{mlist[0]['id']}/comments",
             params={"fields": "id,text,username", "access_token": tok})

    # messages — new-API conversations shape (same as messenger pattern)
    msgs = call("GET /{ig-user}/conversations?platform=instagram",
                "instagram_business_manage_messages",
                "GET", f"{BASE}/{uid}/conversations",
                params={"platform": "instagram", "fields": "id,updated_time",
                        "limit": 5, "access_token": tok})
    if not msgs:
        call("GET /me/conversations?platform=instagram (fallback)",
             "instagram_business_manage_messages",
             "GET", f"{BASE}/me/conversations",
             params={"platform": "instagram", "fields": "id,updated_time",
                     "limit": 5, "access_token": tok})

    ok = sum(1 for _, s in results if s)
    print(f"\n=== SUMMARY: {ok}/{len(results)} calls succeeded ===")
    print("Counters refresh with delay (24h+) — usage is logged by Meta now.")


if __name__ == "__main__":
    main()
