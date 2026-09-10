"""
Local-only scoped-token fetcher — NO platform writes (clean multi-tenant state).

Gets a page access token carrying the FULL App Review scope list (including
pages_utility_messaging + human_agent) via the Facebook OAuth dialog, then:
  1. exchanges the short-lived user token for a long-lived one
  2. derives the never-expiring PAGE token (GET /me/accounts)
  3. writes META_PAGE_ACCESS_TOKEN / META_PAGE_ID / META_INSTAGRAM_ACCOUNT_ID
     to the LOCAL .env only — never calls /api/meta/configure or Supabase.

Run:  python scripts/fetch_scoped_token.py
Then: open http://localhost:8000/settings?__fbscoped=1 flow auto-opens the dialog.

Requires http://localhost:8000/settings in the Meta app's Valid OAuth Redirect
URIs, and the local server on port 8000 stopped first.
"""
import json
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlencode

import httpx

ROOT = Path(__file__).resolve().parent.parent
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PORT = 8000
REDIRECT_URI = f"http://localhost:{PORT}/settings"
SCOPES = ("pages_show_list,pages_messaging,pages_manage_metadata,pages_read_engagement,"
          "pages_manage_posts,pages_read_user_content,read_insights,instagram_basic,"
          "instagram_manage_messages,instagram_manage_comments,instagram_content_publish,"
          "pages_utility_messaging")
# NOTE: human_agent is NOT dialog-requestable ("Invalid Scope") — Meta grants it
# app-level via App Review; the HUMAN_AGENT tag stays #100-gated until then.

captured = {"token": None}


def env(k, default=""):
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(k + "="):
            return line.split("=", 1)[1].strip()
    return default


def save_env(updates: dict):
    p = ROOT / ".env"
    content = p.read_text(encoding="utf-8")
    for k, v in updates.items():
        if re.search(rf"^{k}=.*$", content, flags=re.M):
            content = re.sub(rf"^{k}=.*$", f"{k}={v}", content, flags=re.M)
        else:
            content += f"\n{k}={v}"
    p.write_text(content, encoding="utf-8")


PAGE_HTML = """<!doctype html><meta charset=utf-8><body>
<script>
const h = new URLSearchParams(location.hash.substring(1));
fetch('/__fbcatch', {method:'POST', headers:{'Content-Type':'application/json'},
  body: JSON.stringify({token: h.get('access_token')})})
  .then(() => document.body.textContent = 'Token captured — you can close this window.')
  .catch(() => document.body.textContent = 'No token in URL — authorize first.');
</script>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(PAGE_HTML.encode())

    def do_POST(self):
        if self.path != "/__fbcatch":
            self.send_response(404)
            self.end_headers()
            return
        n = int(self.headers.get("Content-Length", 0))
        captured["token"] = json.loads(self.rfile.read(n) or b"{}").get("token")
        self.send_response(200)
        self.end_headers()


def main():
    app_id = env("META_APP_ID")
    app_secret = env("META_APP_SECRET")
    if not app_id or not app_secret:
        print("META_APP_ID / META_APP_SECRET missing in .env")
        sys.exit(1)

    server = HTTPServer(("localhost", PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    dialog = ("https://www.facebook.com/v26.0/dialog/oauth?"
              + urlencode({"client_id": app_id, "redirect_uri": REDIRECT_URI,
                           "scope": SCOPES, "response_type": "token",
                           "auth_type": "rerequest"}))
    print(f"\n1. Open this URL in your browser and approve ALL permissions:\n\n{dialog}\n")
    print(f"2. Facebook redirects to {REDIRECT_URI} — this catcher grabs the token.")
    print("   Waiting for the redirect ... (Ctrl+C to abort)\n")

    try:
        while not captured["token"]:
            import time
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Aborted.")
        sys.exit(1)
    finally:
        server.shutdown()

    user_tok = captured["token"]
    print("✅ user token captured")

    # long-lived user token
    r = httpx.get("https://graph.facebook.com/v26.0/oauth/access_token", params={
        "grant_type": "fb_exchange_token", "client_id": app_id,
        "client_secret": app_secret, "fb_exchange_token": user_tok}, timeout=30)
    ll_tok = r.json().get("access_token")
    if not ll_tok:
        print(f"❌ exchange failed: {r.text[:200]} — using short-lived token anyway")
        ll_tok = user_tok
    else:
        print("✅ long-lived user token")

    # page token (never expires when derived from a long-lived user token)
    r = httpx.get("https://graph.facebook.com/v26.0/me/accounts",
                  params={"access_token": ll_tok}, timeout=30)
    pages = r.json().get("data", [])
    if not pages:
        print(f"❌ no pages on this account: {r.text[:200]}")
        sys.exit(1)
    for i, p in enumerate(pages):
        print(f"   [{i}] {p['name']} ({p['id']})")
    pick = pages[0]
    if len(pages) > 1:
        pick = pages[int(input("   pick page index: ") or 0)]
    page_tok = pick["access_token"]
    updates = {"META_PAGE_ACCESS_TOKEN": page_tok, "META_PAGE_ID": pick["id"]}

    # instagram business account linked to the page
    r = httpx.get(f"https://graph.facebook.com/v26.0/{pick['id']}",
                  params={"fields": "instagram_business_account",
                          "access_token": page_tok}, timeout=30)
    ig = r.json().get("instagram_business_account", {}).get("id")
    if ig:
        updates["META_INSTAGRAM_ACCOUNT_ID"] = ig
        print(f"✅ instagram account: {ig}")

    save_env(updates)
    print(f"✅ saved to LOCAL .env: page '{pick['name']}' ({pick['id']})")

    # verify scopes on the new page token
    r = httpx.get("https://graph.facebook.com/v26.0/debug_token", params={
        "input_token": page_tok, "access_token": f"{app_id}|{app_secret}"}, timeout=30)
    scopes = r.json().get("data", {}).get("scopes", [])
    missing = [s for s in ("pages_utility_messaging",) if s not in scopes]
    print(f"   token scopes: {', '.join(scopes)}")
    print(f"❌ still missing on token: {missing}" if missing
          else "✅ pages_utility_messaging present on token")
    print("\nNext: python scripts/test_missing_meta_permissions.py --send")


if __name__ == "__main__":
    main()
