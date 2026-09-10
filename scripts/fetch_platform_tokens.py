"""
Local-only OAuth token fetcher for Threads + Instagram Business (App Review usage).

  python scripts/fetch_platform_tokens.py threads [--extra]   # graph.threads.net token
  python scripts/fetch_platform_tokens.py ig                  # graph.instagram.com token

Zero platform writes — token goes to LOCAL .env only (THREADS_ACCESS_TOKEN /
IG_BUSINESS_ACCESS_TOKEN). Threads uses response_type=code; the redirect lands
on this local catcher which reads ?code= directly.

Requires http://localhost:8000/settings whitelisted on the respective app
(dev mode auto-allows localhost) + local server on port 8000 stopped.
"""
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode

import httpx

ROOT = Path(__file__).resolve().parent.parent
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PORT = 8000
CERT = ROOT / "scripts" / "local_https_cert.pem"
KEY = ROOT / "scripts" / "local_https_key.pem"
# threads.net REJECTS http redirects ("Insecure Login Blocked") — use local HTTPS
# with the self-signed cert (browser warning: click "Advanced → proceed").
USE_HTTPS = CERT.exists() and KEY.exists()
REDIRECT_URI = f"{'https' if USE_HTTPS else 'http'}://localhost:{PORT}/settings"

THREADS_CORE = ("threads_basic,threads_content_publish,threads_manage_replies,"
                "threads_manage_insights,threads_read_replies")
THREADS_EXTRA = "threads_delete"
IG_SCOPES = ("instagram_business_basic,instagram_business_manage_insights,"
             "instagram_business_content_publish,instagram_business_manage_comments,"
             "instagram_business_manage_messages")

captured = {"code": None, "error": None}


def env(k, default=""):
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(k + "="):
            return line.split("=", 1)[1].strip()
    return default


def save_env(updates: dict):
    import re
    p = ROOT / ".env"
    content = p.read_text(encoding="utf-8")
    for k, v in updates.items():
        if re.search(rf"^{k}=.*$", content, flags=re.M):
            content = re.sub(rf"^{k}=.*$", f"{k}={v}", content, flags=re.M)
        else:
            content += f"\n{k}={v}"
    p.write_text(content, encoding="utf-8")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        q = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
        captured["code"] = (q.get("code") or [None])[0]
        captured["error"] = (q.get("error_description") or q.get("error_message") or [None])[0]
        msg = "Token code captured — you can close this window." if captured["code"] \
            else f"OAuth error: {captured['error']}"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(f"<!doctype html><meta charset=utf-8><body>{msg}</body>".encode())


def catch_code(authorize_url: str) -> str:
    # Threading: single-threaded server hangs on Chrome's pre-connect during the
    # cert warning — the real request then times out (ERR_TIMED_OUT).
    server = ThreadingHTTPServer(("localhost", PORT), Handler)
    if USE_HTTPS:
        import ssl
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(str(CERT), str(KEY))
        server.socket = ctx.wrap_socket(server.socket, server_side=True)
        print(f"🔒 local HTTPS catcher on port {PORT} (self-signed cert — browser warning is expected)")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"\n1. Open this URL and approve:\n\n{authorize_url}\n")
    print(f"2. Redirect lands on {REDIRECT_URI} — this catcher reads ?code=")
    try:
        while not captured["code"] and not captured["error"]:
            time.sleep(0.5)
    finally:
        server.shutdown()
    if captured["error"]:
        print(f"❌ OAuth error: {captured['error']}")
        sys.exit(1)
    print("✅ code captured")
    return captured["code"]


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "threads":
        app_id = env("THREADS_APP_ID") or env("META_APP_ID")
        scopes = THREADS_CORE + ("," + THREADS_EXTRA if "--extra" in sys.argv else "")
        authorize = ("https://threads.net/oauth/authorize?"
                     + urlencode({"client_id": app_id, "redirect_uri": REDIRECT_URI,
                                  "response_type": "code", "scope": scopes,
                                  "state": "local-threads"}))
        print(f"app_id: {app_id} | scopes: {scopes}")
        code = catch_code(authorize)
        # short-lived token
        r = httpx.post("https://graph.threads.net/oauth/access_token", data={
            "client_id": app_id, "client_secret": env("THREADS_APP_SECRET") or env("META_APP_SECRET"),
            "grant_type": "authorization_code", "redirect_uri": REDIRECT_URI,
            "code": code}, timeout=30)
        short = r.json().get("access_token")
        if not short:
            print(f"❌ exchange failed: {r.text[:300]}")
            sys.exit(1)
        # long-lived
        r = httpx.get("https://graph.threads.net/access_token", params={
            "grant_type": "th_exchange_token",
            "client_secret": env("THREADS_APP_SECRET") or env("META_APP_SECRET"),
            "access_token": short}, timeout=30)
        tok = r.json().get("access_token") or short
        # profile
        r = httpx.get("https://graph.threads.net/v1.0/me",
                      params={"fields": "id,username,threads_profile_description",
                              "access_token": tok}, timeout=30)
        me = r.json()
        save_env({"THREADS_ACCESS_TOKEN": tok, "THREADS_USER_ID": me.get("id", "me")})
        print(f"✅ Threads token saved ({me.get('username')} / {me.get('id')})")

    elif mode == "ig":
        # child Instagram app (Meta creates a SEPARATE app id for the Instagram
        # product) — "Invalid platform app" if you use the main app id here
        app_id = env("IG_APP_ID")
        secret = env("IG_APP_SECRET") or env("META_APP_SECRET")
        if not app_id:
            print("IG_APP_ID missing in .env — set it from dashboard → Instagram API → App information")
            sys.exit(1)
        authorize = ("https://www.instagram.com/oauth/authorize?"
                     + urlencode({"client_id": app_id, "redirect_uri": REDIRECT_URI,
                                  "response_type": "code", "scope": IG_SCOPES}))
        print(f"app_id: {app_id} | scopes: {IG_SCOPES}")
        code = catch_code(authorize)
        r = httpx.post("https://api.instagram.com/oauth/access_token", data={
            "client_id": app_id, "client_secret": secret,
            "grant_type": "authorization_code", "redirect_uri": REDIRECT_URI,
            "code": code}, timeout=30)
        j = r.json()
        short = (j.get("access_token") or "")
        if not short:
            print(f"❌ exchange failed: {r.text[:300]}")
            sys.exit(1)
        uid = j.get("user_id", "me")
        # long-lived
        r = httpx.get("https://graph.instagram.com/access_token", params={
            "grant_type": "ig_exchange_token", "client_secret": secret,
            "access_token": short}, timeout=30)
        tok = r.json().get("access_token") or short
        r = httpx.get(f"https://graph.instagram.com/v23.0/{uid}",
                      params={"fields": "user_id,username,account_type",
                              "access_token": tok}, timeout=30)
        me = r.json()
        save_env({"IG_BUSINESS_ACCESS_TOKEN": tok,
                  "IG_BUSINESS_USER_ID": str(me.get("user_id") or me.get("id") or uid)})
        print(f"✅ IG Business token saved ({me.get('username')})")

    else:
        print(__doc__)
        sys.exit(1)
    print("\nNext: python scripts/test_threads_permissions.py  /  test_ig_business_permissions.py")


if __name__ == "__main__":
    main()
