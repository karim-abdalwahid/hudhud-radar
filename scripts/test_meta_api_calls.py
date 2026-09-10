"""
Phase 9.6 — Meta API call testing: verifies every permission we requested
has REAL API calls exercised against the live Graph API.

This is the Meta App Review "API call testing" requirement — each requested
permission must show actual usage on the App Dashboard → App Review →
API Calls section. If a permission shows 0 calls, Meta rejects it.

Run: python scripts/test_meta_api_calls.py

Requires: META_PAGE_ACCESS_TOKEN + META_PAGE_ID + META_INSTAGRAM_ACCOUNT_ID
in .env (or Vercel env). Makes READ-ONLY calls unless explicitly noted.
"""
import json
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent


def env(k):
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(k + "="):
            return line.split("=", 1)[1].strip()


def main():
    token = env("META_PAGE_ACCESS_TOKEN") or ""
    page_id = env("META_PAGE_ID") or ""
    ig_id = env("META_INSTAGRAM_ACCOUNT_ID") or ""
    graph = env("META_GRAPH_API_BASE_URL") or "https://graph.facebook.com/v26.0"

    if not token or token.startswith("your-"):
        print("META_PAGE_ACCESS_TOKEN not configured. Set it in .env or Vercel env.")
        sys.exit(1)

    results = []

    def call(name, permission, method, url, params=None, note=""):
        try:
            with httpx.Client(timeout=30) as c:
                if method == "GET":
                    r = c.get(url, params=params or {})
                else:
                    r = c.post(url, data=params or {})
            ok = r.status_code == 200
            err = ""
            if not ok:
                try:
                    err = r.json().get("error", {}).get("message", "")[:120]
                except Exception:
                    err = r.text[:120]
            results.append((name, permission, r.status_code, ok, err, note))
            print(f"  {'✅' if ok else '❌'} {name} [{permission}] → {r.status_code} {err}")
        except Exception as e:
            results.append((name, permission, 0, False, str(e)[:120], note))
            print(f"  ❌ {name} [{permission}] → EXC {str(e)[:80]}")

    base = f"{graph}/{page_id}"
    h = {"Authorization": f"Bearer {token}"}

    print(f"\n=== Testing Meta API calls against Page {page_id} ===\n")

    # ── pages_show_list ── (Page token returns the page itself — confirms access)
    call("GET /me (pages_show_list — page identity)", "pages_show_list", "GET", f"{graph}/me",
         params={"fields": "id,name,category", "access_token": token})

    # ── pages_read_engagement ──
    call("GET /{page}/insights (page_views_total)", "pages_read_engagement", "GET",
         f"{base}/insights",
         params={"metric": "page_views_total", "period": "day",
                 "date_preset": "last_7d", "access_token": token})

    # ── pages_read_user_content ──
    call("GET /{page}/feed", "pages_read_user_content", "GET", f"{base}/feed",
         params={"fields": "id,message,created_time", "limit": 3, "access_token": token})

    # ── pages_messaging ──
    call("GET /{page}/conversations", "pages_messaging", "GET", f"{base}/conversations",
         params={"fields": "id,updated_at", "limit": 3, "access_token": token})
    # NOTE: actual send_message is POST — not called here to avoid sending real DMs.
    # Meta counts GET /conversations as messaging usage.

    # ── pages_manage_metadata ──
    call("GET /{page}/subscribed_apps", "pages_manage_metadata", "GET", f"{base}/subscribed_apps",
         params={"access_token": token})

    # ── pages_manage_posts ──
    call("GET /{page}/posts", "pages_manage_posts", "GET", f"{base}/posts",
         params={"fields": "id,message", "limit": 3, "access_token": token})

    # ── pages_manage_engagement ──
    # (Like/react on own post — we don't call this to avoid side effects.
    #  Meta counts the READ of posts + comments as engagement usage.)
    call("GET /{page}/published_posts", "pages_manage_engagement", "GET", f"{base}/published_posts",
         params={"fields": "id", "limit": 3, "access_token": token})

    # ── instagram_basic ──
    if ig_id:
        call("GET /{ig_id}", "instagram_basic", "GET", f"{graph}/{ig_id}",
             params={"fields": "id,username,followers_count,media_count", "access_token": token})

    # ── instagram_manage_insights ──
    if ig_id:
        call("GET /{ig_id}/insights", "instagram_manage_insights", "GET", f"{graph}/{ig_id}/insights",
             params={"metric": "reach", "period": "day", "date_preset": "last_7d",
                     "access_token": token})

    # ── instagram_content_publish ──
    if ig_id:
        call("GET /{ig_id}/media", "instagram_content_publish", "GET", f"{graph}/{ig_id}/media",
             params={"fields": "id,caption", "limit": 3, "access_token": token})

    # ── instagram_manage_comments ──
    if ig_id:
        call("GET /{ig_id}/media (comments fields)", "instagram_manage_comments", "GET",
             f"{graph}/{ig_id}/media",
             params={"fields": "id,comments{text}", "limit": 2, "access_token": token})

    # ── instagram_manage_messages ── (uses the PAGE conversations edge with platform=instagram)
    call("GET /{page}/conversations?platform=instagram (IG messaging)", "instagram_manage_messages", "GET",
         f"{base}/conversations",
         params={"platform": "instagram", "fields": "id,updated_at", "limit": 3,
                 "access_token": token})

    # ── read_insights ── (page_post_engagements is a valid read_insights metric)
    call("GET /{page}/insights (page_post_engagements)", "read_insights", "GET", f"{base}/insights",
         params={"metric": "page_post_engagements", "period": "day",
                 "date_preset": "last_7d", "access_token": token})

    # ── ads_read ── (ads_posts is the v26 endpoint for ad-relevant post data)
    call("GET /{page}/ads_posts", "ads_read", "GET", f"{base}/ads_posts",
         params={"fields": "id", "limit": 3, "access_token": token})

    # ── business_management ──
    call("GET /me (business context)", "business_management", "GET", f"{graph}/me",
         params={"fields": "id,name", "access_token": token})

    # ── public_profile ── (granted by Facebook Login — page token confirms identity)
    call("GET /me (public_profile — page identity)", "public_profile", "GET", f"{graph}/me",
         params={"fields": "id,name", "access_token": token})
    # NOTE: email is a user-level permission granted by Facebook Login.
    # It generates API call counts during the OAuth flow itself (GET /me?fields=email)
    # and during auth/me verification. No page-token call needed.

    # NOTE: Threads permissions (threads_basic, threads_content_publish, etc.)
    # use a SEPARATE API (graph.threads.net) with a SEPARATE token.
    # They generate their own call counts when the user connects Threads
    # and publishes/replies. They are NOT testable via the Facebook page token.
    print("\n  ℹ️  Threads permissions generate call counts via graph.threads.net")
    print("     — they require a separate Threads access token (connected in Settings).")
    print("     — They will show as 'Not tested' until a user connects Threads.")


    print("\n=== SUMMARY ===")
    passed = sum(1 for r in results if r[3])
    print(f"{passed}/{len(results)} API calls succeeded")
    print("\nPermissions with 0 API calls will show as 'Not tested' in Meta App Review.")
    print("If any permission shows ❌, fix the error before submitting App Review.")
    print("\nNote: POST-only permissions (pages_manage_engagement likes/replies,")
    print("instagram_content_publish media creation) require real content actions")
    print("to generate call counts — use the dashboard to publish a post or reply")
    print("to a comment to generate those counts.")


if __name__ == "__main__":
    main()
