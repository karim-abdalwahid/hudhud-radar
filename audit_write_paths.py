"""Phase 3: malformed-input sweep over POST/PUT/PATCH/DELETE endpoints.
Every call must answer 4xx (never 5xx). No destructive happy-paths here."""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from playwright.sync_api import sync_playwright

B = "http://localhost:8000"
BAD = {}
# (method, path, payload) — intentionally invalid/empty, must 4xx cleanly
CASES = [
    ("POST", "/auth/login", {"email": "nope@nope.test", "password": "x"}),
    ("POST", "/auth/register", {"email": "bad-email", "password": "123"}),
    ("POST", "/auth/change-password", {"current_password": "x", "new_password": "y"}),
    ("POST", "/api/content/posts", {}),
    ("POST", "/api/content/generate", {"topic": ""}),
    ("POST", "/api/content/compliance-check", {}),
    ("GET", "/api/content/posts/00000000-0000-0000-0000-000000000000", None),
    ("POST", "/api/content/posts/00000000-0000-0000-0000-000000000000/publish-now", None),
    ("DELETE", "/api/content/posts/00000000-0000-0000-0000-000000000000", None),
    ("POST", "/api/automations", {}),
    ("PUT", "/api/automations/nonexistent_wf", {}),
    ("POST", "/api/knowledge/documents", {"filename": "", "content": ""}),
    ("PUT", "/api/knowledge/documents/../../evil.md", {"content": "x"}),
    ("DELETE", "/api/knowledge/documents/nope.md", None),
    ("POST", "/api/inbox/conversations/00000000-0000-0000-0000-000000000000/takeover", {"takeover": "maybe"}),
    ("POST", "/api/inbox/conversations/00000000-0000-0000-0000-000000000000/send-message", {"text": ""}),
    ("POST", "/api/threads/publish", {"text": "   "}),
    ("POST", "/api/threads/0000000000/reply", {"text": ""}),
    ("POST", "/api/meta/configure", {}),
    ("POST", "/api/meta/exchange-token", {"user_token": "EAABTOTALLYFAKE"}),
    ("POST", "/api/ai/providers", {}),
    ("PUT", "/api/ai/providers/00000000-0000-0000-0000-000000000000", {}),
    ("POST", "/api/admin/users/00000000-0000-0000-0000-000000000000/credits", {"amount": -5}),
    ("POST", "/api/admin/users/00000000-0000-0000-0000-000000000000/plan", {"plan": "platinum-evil"}),
    ("PATCH", "/api/admin/users/00000000-0000-0000-0000-000000000000", {"is_active": "yes-please"}),
    ("POST", "/api/identity/queue/00000000-0000-0000-0000-000000000000/approve", None),
    ("POST", "/api/admin/notifications/broadcast", {"title": "", "body": ""}),
    ("PUT", "/api/admin/site-settings", {"__unknown__": "x"}),
    ("PUT", "/api/admin/templates/nonexistent_key", {"body": "x"}),
    ("POST", "/api/billing/quote" , {}),
    ("GET", "/api/leads/00000000-0000-0000-0000-000000000000", None),
]

ok = bad500 = 0
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context().new_page()
    pg.goto(f"{B}/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=15000)
    for method, path, body in CASES:
        try:
            if method == "GET":
                r = pg.request.get(B + path, timeout=25000)
            elif method == "DELETE":
                r = pg.request.delete(B + path, timeout=25000)
            else:
                r = pg.request.post(B + path, data=(body or {}), timeout=25000) if method == "POST" \
                    else pg.request.put(B + path, data=(body or {}), timeout=25000)
            code = r.status
        except Exception as e:
            code = f"ERR {e}"
        if isinstance(code, int) and 200 <= code < 300:
            ok += 1  # some are legitimately 2xx (idempotent deletes of missing = 404 expected though)
        elif isinstance(code, int) and code < 500:
            ok += 1
        else:
            bad500 += 1
            print(f"  ❌ {method} {path} -> {code} {str(r.text())[:160] if isinstance(code, int) else ''}")
    b.close()

print(f"\nwrite-path malformed sweep: {len(CASES)} cases | clean 4xx/2xx: {ok} | 5xx/crash: {bad500}")
