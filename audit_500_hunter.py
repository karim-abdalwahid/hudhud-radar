"""500-hunter sweep: edge cases likely to crash handlers.
Phase A: broad probe (raise_server_exceptions=False) -> list every 5xx.
Phase B: re-run the failures with raise=True to capture tracebacks."""
import hashlib
import hmac
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

import httpx  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402
from src.config import settings  # noqa: E402

META_SIG = lambda raw: "sha256=" + hmac.new((settings.META_APP_SECRET or "").encode(), raw, hashlib.sha256).hexdigest()

CASES = []

def add(label, method, path, body=None, headers=None, auth=True):
    CASES.append((label, method, path, body, headers or {}, auth))

def meta_hdrs(raw):
    return {"Content-Type": "application/json", "X-Hub-Signature-256": META_SIG(raw)}

# ---- webhook abuse (valid signature, hostile payloads) ----
p = b"this is not json {{{"
add("meta webhook: signed garbage body", "post", "/api/webhook/meta", p, meta_hdrs(p))
p2 = json.dumps([1, 2, 3]).encode()
add("meta webhook: signed list payload", "post", "/api/webhook/meta", p2, meta_hdrs(p2))
p3 = json.dumps({"object": "page", "entry": "not-a-list"}).encode()
add("meta webhook: entry=string", "post", "/api/webhook/meta", p3, meta_hdrs(p3))
p4 = json.dumps({"object": "page", "entry": [{"messaging": [{}]}]}).encode()
add("meta webhook: messaging no sender", "post", "/api/webhook/meta", p4, meta_hdrs(p4))
p5 = json.dumps({"object": "page", "entry": [{"changes": [{"field": "mentions", "value": None}]}]}).encode()
add("meta webhook: mentions value=null", "post", "/api/webhook/meta", p5, meta_hdrs(p5))
pt = b"garbage"
add("threads webhook: signed garbage", "post", "/api/webhook/threads", pt,
    {"Content-Type": "application/json", "X-Hub-Signature-256":
     "sha256=" + hmac.new((settings.THREADS_APP_SECRET or "x").encode(), pt, hashlib.sha256).hexdigest()})
pt2 = json.dumps({"object": "threads", "entry": [{"changes": [{"value": "str"}]}]}).encode()
add("threads webhook: value string", "post", "/api/webhook/threads", pt2,
    {"Content-Type": "application/json", "X-Hub-Signature-256":
     "sha256=" + hmac.new((settings.THREADS_APP_SECRET or "x").encode(), pt2, hashlib.sha256).hexdigest()})

# ---- malformed UUID path params ----
BAD = "not-a-uuid"
for path in [f"/api/leads/{BAD}", f"/api/content/posts/{BAD}", f"/api/automations/{BAD}",
             f"/api/knowledge/documents/{BAD}.md", f"/api/notifications/{BAD}/read",
             f"/api/admin/users/{BAD}", f"/api/identity/queue/{BAD}/approve",
             f"/api/reports/bogus-type", f"/api/inbox/conversations/{BAD}/takeover",
             f"/api/content/posts/{BAD}/publish-now", f"/api/ai/providers/{BAD}/sync",
             f"/api/ai/models/{BAD}/toggle", f"/api/threads/{BAD}",
             f"/api/threads/{BAD}/reply", f"/api/billing/subscription/{BAD}"]:
    add(f"uuid-path: {path.split('/')[-2 if '/' in path else -1]}", "get", path)

# ---- hostile query params ----
add("quote: empty platforms", "get", "/api/billing/quote?platforms=")
add("quote: junk platforms", "get", "/api/billing/quote?platforms=,,,evil")
add("meta posts: bogus type", "get", "/api/meta/posts?platform=zzz&post_type=qqq")
add("studio: status bogus", "get", "/api/content/posts?status=not-a-status")
add("admin users: wildcard search", "get", "/api/admin/users?search=%25")
add("inbox conv: unknown param", "get", "/api/inbox/conversations?bogus=1")
add("sync-leads: junk form id", "post", "/api/marketing/sync-leads?form_id=%%%" )

# ---- malformed bodies on write endpoints ----
add("login: dict-as-string", "post", "/auth/login", "hello",
    {"Content-Type": "application/json"})
add("takeover: body string", "post", "/api/inbox/conversations/1b61e13c-7502-422d-9b1e-2ffe6e9d2c20/takeover",
    '"not-an-object"', {"Content-Type": "application/json"})
add("site-settings: body array", "put", "/api/admin/site-settings", '[1,2]', {"Content-Type": "application/json"})
add("billing webhook: bad json", "post", "/api/payments/webhook/polar", "{bad json",
    {"Content-Type": "application/json"})
add("change-password: json list", "post", "/auth/change-password", '["x"]',
    {"Content-Type": "application/json"})



# ---- write-methods with malformed UUID segments (phase A2) ----
BAD = "not-a-uuid"
add("credits bad uuid", "post", f"/api/admin/users/{BAD}/credits",
    json.dumps({"amount": 5}).encode(), {"Content-Type": "application/json"})
add("plan bad uuid", "post", f"/api/admin/users/{BAD}/plan",
    json.dumps({"plan": "starter"}).encode(), {"Content-Type": "application/json"})
add("patch user bad uuid", "patch", f"/api/admin/users/{BAD}",
    json.dumps({"is_active": False}).encode(), {"Content-Type": "application/json"})
add("notification read bad uuid", "post", f"/api/notifications/{BAD}/read")
add("coupon delete bad uuid", "delete", f"/api/admin/billing/coupons/{BAD}")
add("model toggle bad uuid", "post", f"/api/ai/models/{BAD}/toggle")
add("provider sync bad uuid", "post", f"/api/ai/providers/{BAD}/sync")
add("queue approve bad uuid", "post", f"/api/identity/queue/{BAD}/approve")
add("content delete bad uuid", "delete", f"/api/content/posts/{BAD}")
add("billing sub bad uuid", "post", f"/api/billing/subscription/{BAD}/cancel")

# ===================================================================
def run(raise_exc=False):
    from src.main import app
    client = TestClient(app, raise_server_exceptions=raise_exc)
    # login admin via API for authed requests
    r = client.post("/auth/login", json={"email": "admin.test@hudhud.test", "password": "AdminTest#2026"})
    results = []
    for label, method, path, body, headers, auth in CASES:
        kw = {}
        if isinstance(body, bytes):
            kw["content"] = body
        elif isinstance(body, str):
            kw["content"] = body.encode()
        if headers:
            kw["headers"] = {**({"cookie": r.headers.get("set-cookie", "").split(";")[0]} if auth else {}), **headers}
        elif auth:
            kw["headers"] = {"cookie": r.headers.get("set-cookie", "").split(";")[0]}
        try:
            resp = getattr(client, method)(path, **kw)
            results.append((label, path, resp.status_code, None))
        except Exception as e:
            import traceback
            tb = "".join(traceback.format_tb(e.__traceback__)).replace("\n", " | ")
            results.append((label, path, 500, f"{type(e).__name__}: {str(e)[:120]} :: {tb[-300:]}"))
    return results

if __name__ == "__main__":
    print("== PHASE A (broad) ==")
    res = run(raise_exc=False)
    bad = [r for r in res if r[2] >= 500]
    print(f"cases: {len(res)} | 5xx: {len(bad)}")
    for label, path, code, tb in bad:
        print(f"  ❌ {label}: {path} -> {code}")
    print("\n== statuses by group ==")
    for label, path, code, tb in res:
        flag = "  " if code < 500 else "❌"
        print(f"  {flag} {code:<4} {label[:38]:<40} {path[:60]}")
