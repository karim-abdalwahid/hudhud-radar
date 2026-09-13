"""Settings-page backend review — every endpoint the page calls, LIVE,
cross-checked against Meta where possible. Read-only where writes are risky."""
import json
import os
import sys
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from playwright.sync_api import sync_playwright

TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN")
PAGE_ID = os.getenv("META_PAGE_ID")
APP_ID = os.getenv("META_APP_ID")
APP_SECRET = os.getenv("META_APP_SECRET")
G = "https://graph.facebook.com/v21.0"
B = "http://localhost:8000"
rows = []


def g(params):
    url = f"{G}/debug_token?" + urllib.parse.urlencode(
        {"input_token": TOKEN, "access_token": f"{APP_ID}|{APP_SECRET}"})
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.loads(r.read().decode())["data"]


real = g({})

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context().new_page()
    pg.goto(f"{B}/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=15000)

    def probe(method, ep, note="", body=None):
        r = (pg.request.post(ep if ep.startswith("http") else B + ep, data=body)
             if method == "POST" else pg.request.get(B + ep))
        rows.append((method, ep, r.status, note, r.text()[:140]))
        return r

    # ============ Meta tab ============
    r = probe("GET", "/api/meta/status", "must mirror debug_token")
    st = r.json()
    checks = {
        "token_valid matches Meta debug_token": (st.get("token_valid") == bool(real.get("is_valid"))),
        "configured": st.get("configured", True),
    }
    rows[-1] = rows[-1][:3] + ("fields: " + json.dumps({k: v for k, v in checks.items()}, ensure_ascii=False),) + (rows[-1][4],)
    # page name truth
    try:
        url = f"{G}/{PAGE_ID}?" + urllib.parse.urlencode({"fields": "name", "access_token": TOKEN})
        with urllib.request.urlopen(url, timeout=15) as rr:
            real_name = json.loads(rr.read().decode())["name"]
    except Exception:
        real_name = "?"
    rows.append(("CHK", "page name vs app's page_name", 200, "Meta says", real_name[:60]))

    # exchange-token error path (fake token must fail CLEAN, not 500)
    probe("POST", "/api/meta/exchange-token", "fake token -> clean 4xx", {"access_token": "EAABFAKE123"})
    # user-pages error path (needs USER token; fake -> clean error)
    probe("GET", "/api/meta/user-pages?token=FAKE", "fake user token -> clean")

    # ============ Threads tab ============
    r = probe("GET", "/api/threads/status", "connected must reflect reality")
    ts = r.json()
    rows[-1] = rows[-1][:3] + (f"configured={ts.get('configured')} connected={ts.get('connected')} user={ts.get('username')}",) + (rows[-1][4],)

    # ============ AI tab ============
    r = probe("GET", "/api/ai/providers", "real providers list")
    r = probe("GET", "/api/ai/models", "real models list")
    n_models = len(r.json().get("models", [])) if r.status == 200 else -1
    rows[-1] = rows[-1][:3] + (f"models={n_models}",) + (rows[-1][4],)
    r = probe("GET", "/api/ai/pause", "pause state shape")
    pause = r.json() if r.status == 200 else {}
    rows[-1] = rows[-1][:3] + (f"keys={sorted(pause.keys())}",) + (rows[-1][4],)

    # ============ Security tab ============
    r = probe("POST", "/auth/change-password", "wrong current -> clean 4xx, no change",
              {"current_password": "WrongPass123!", "new_password": "Whatever#2026"})
    # verify password unchanged
    still_ok = pg.request.post(f"{B}/auth/login", data={"email": "admin.test@hudhud.test", "password": "AdminTest#2026"})
    rows.append(("CHK", "admin.test still logs in", still_ok.status, "password untouched", ""))

    # ============ admin gate for regular users ============
    b.close()
with sync_playwright() as p:
    b2 = p.chromium.launch(headless=True)
    pg2 = b2.new_context().new_page()
    pg2.goto(f"{B}/login"); pg2.wait_for_load_state("networkidle")
    pg2.fill("#loginEmail", "user.test@hudhud.test"); pg2.fill("#loginPassword", "AdminTest#2026")
    pg2.click("#loginBtn"); pg2.wait_for_timeout(3000)
    for ep in ["/api/threads/status", "/api/meta/status", "/api/ai/pause", "/api/ai/providers"]:
        r = pg2.request.get(B + ep)
        rows.append(("user", ep, r.status, "gate check", ""))
    b2.close()

print(f"{'M':<5} {'ENDPOINT':<38} {'HTTP':<5} {'NOTE':<38} BODY")
for m, ep, code, note, body in rows:
    print(f"{m:<5} {ep:<38} {code:<5} {note:<38} {str(body)[:60]}")
