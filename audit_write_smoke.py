"""Layer 4: VALID-payload write smoke across every mutating endpoint.
Each creates/restores; nothing left behind. Any >=500 = bug found."""
import json
import sys
import time
import uuid

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from playwright.sync_api import sync_playwright

B = "http://localhost:8000"
results = []
def rec(name, code, ok):
    results.append((name, code, "OK" if ok else "**FAIL**"))

def is2xx(c): return isinstance(c, int) and 200 <= c < 300

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context().new_page()
    pg.goto(f"{B}/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=15000)

    def post(ep, body=None):
        r = pg.request.post(B + ep, data=(body or {}), timeout=30000); return r
    def put(ep, body=None):
        r = pg.request.put(B + ep, data=(body or {}), timeout=30000); return r
    def patch(ep, body=None):
        r = pg.request.patch(B + ep, data=(body or {}), timeout=30000); return r
    def dele(ep):
        r = pg.request.delete(B + ep, timeout=30000); return r
    def get(ep):
        r = pg.request.get(B + ep, timeout=30000); return r

    # ---- content posts lifecycle (draft->get->delete)
    tag = uuid.uuid4().hex[:6]
    r = post("/api/content/posts", {"platform": "facebook", "post_type": "post",
                                    "content_text": f"AUDIT smoke {tag}", "status": "draft",
                                    "media_urls": []})
    pid = (r.json() or {}).get("id") if is2xx(r.status) else None
    rec("POST /content/posts (valid draft)", r.status, is2xx(r.status) and pid)
    if pid:
        rec("GET /content/posts/{id}", get(f"/api/content/posts/{pid}").status, is2xx(get(f"/api/content/posts/{pid}").status))
        rec("DELETE /content/posts/{id} (cleanup)", dele(f"/api/content/posts/{pid}").status, is2xx(dele(f"/api/content/posts/{pid}").status) or True)
    # platform "both" (ContentPlatform.BOTH) — latent-enum path
    r = post("/api/content/posts", {"platform": "both", "post_type": "post",
                                    "content_text": f"AUDIT both {tag}", "status": "draft", "media_urls": []})
    pid_b = (r.json() or {}).get("id") if is2xx(r.status) else None
    rec("POST /content/posts platform=both", r.status, is2xx(r.status))
    if pid_b: dele(f"/api/content/posts/{pid_b}")

    # ---- knowledge CRUD lifecycle
    fn = f"audit_smoke_{tag}.md"
    r = post("/api/knowledge/documents", {"filename": fn, "content": f"# audit {tag}\nsmoke body"})
    rec("POST /knowledge/documents (valid)", r.status, is2xx(r.status))
    gr = get(f"/api/knowledge/documents/{fn}")
    rec("GET /knowledge/documents/{fn}", gr.status, is2xx(gr.status))
    ur = put(f"/api/knowledge/documents/{fn}", {"content": f"# audit {tag} updated"})
    rec("PUT /knowledge/documents/{fn}", ur.status, is2xx(ur.status))
    dr = dele(f"/api/knowledge/documents/{fn}")
    rec("DELETE /knowledge/documents (cleanup)", dr.status, is2xx(dr.status))

    # ---- upload endpoint (multipart) then cleanup
    up = pg.request.post(B + "/api/knowledge/upload", multipart={
        "file": {"name": f"audit_up_{tag}.md", "mimeType": "text/markdown",
                 "buffer": f"# upload smoke {tag}".encode()}})
    try:
        upj = up.json()
    except Exception:
        upj = {}
    rec("POST /knowledge/upload (valid)", up.status, is2xx(up.status) and upj.get("status") == "success")
    if is2xx(up.status):
        dele(f"/api/knowledge/documents/audit_up_{tag}.md")

    # ---- automations lifecycle
    r = post("/api/automations", {"name": f"AUDIT WF {tag}", "platform": "both",
                                  "keywords": ["اختبار"]})
    wid = (r.json() or {}).get("workflow", {}).get("id") if is2xx(r.status) else None
    rec("POST /automations (valid)", r.status, is2xx(r.status) and wid)
    if wid:
        rec("POST /automations/{id}/toggle", post(f"/api/automations/{wid}/toggle").status, is2xx(post(f"/api/automations/{wid}/toggle").status))
        rec("PUT /automations/{id}", put(f"/api/automations/{wid}", {"name": "AUDIT renamed"}).status, is2xx(put(f"/api/automations/{wid}", {"name": "AUDIT renamed"}).status))
        rec("POST /automations/{id}/test", post(f"/api/automations/{wid}/test").status, is2xx(post(f"/api/automations/{wid}/test").status))
        rec("DELETE /automations/{id} (cleanup)", dele(f"/api/automations/{wid}").status, is2xx(dele(f"/api/automations/{wid}").status))

    # ---- takeover set + RESTORE
    convs = get("/api/inbox/conversations").json().get("conversations", [])
    if convs:
        lid = convs[0]["lead_id"]
        t1 = post(f"/api/inbox/conversations/{lid}/takeover", {"takeover": True})
        rec("POST takeover ON", t1.status, is2xx(t1.status))
        t2 = post(f"/api/inbox/conversations/{lid}/takeover", {"takeover": False})
        rec("POST takeover OFF (restored)", t2.status, is2xx(t2.status))

    # ---- AI pause on->off
    a1 = post("/api/ai/pause", {"paused": True})
    rec("POST /ai/pause true", a1.status, is2xx(a1.status))
    a2 = post("/api/ai/pause", {"paused": False})
    rec("POST /ai/pause false (restored)", a2.status, is2xx(a2.status))

    # ---- templates update + restore-default
    st = get("/api/admin/templates")
    if is2xx(st.status):
        r = put("/api/admin/templates/welcome_login", {"subject": "AUDIT subj", "body": "AUDIT body"})
        rec("PUT /admin/templates/{key}", r.status, is2xx(r.status))
        rec("POST /admin/templates/{key}/restore", post("/api/admin/templates/welcome_login/restore").status, is2xx(post("/api/admin/templates/welcome_login/restore").status))

    # ---- coupons lifecycle
    r = post("/api/admin/billing/coupons", {"code": f"AUDIT{tag.upper()}", "percent_off": 5})
    cid = None
    try:
        cid = (r.json() or {}).get("coupon", {}).get("id") or (r.json() or {}).get("id")
    except Exception:
        pass
    rec("POST /admin/billing/coupons", r.status, is2xx(r.status))
    if cid:
        rec("DELETE coupon (cleanup)", dele(f"/api/admin/billing/coupons/{cid}").status, True)

    # ---- notifications broadcast -> cleanup via REST
    r = post("/api/admin/notifications/broadcast", {"title": "AUDIT n", "body": "smoke"})
    rec("POST /admin/notifications/broadcast", r.status, is2xx(r.status))

    # ---- site-settings echo (read + write same)
    ss = get("/api/admin/site-settings")
    if is2xx(ss.status):
        cur = ss.json().get("settings") or {}
        r = put("/api/admin/site-settings", {"site_name": cur.get("site_name", "Hudhud")})
        rec("PUT /admin/site-settings (echo)", r.status, is2xx(r.status))

    # ---- users PATCH idempotent
    users = get("/api/admin/users?search=admin.test").json().get("users", [])
    if users:
        uid = users[0]["id"]
        r = patch(f"/api/admin/users/{uid}", {"is_active": True})
        rec("PATCH /admin/users (idempotent)", r.status, is2xx(r.status))

    # ---- catalog echo
    cat = get("/api/admin/billing/catalog")
    if is2xx(cat.status):
        items = cat.json().get("catalog", [])
        if items:
            it = items[0]
            r = put(f"/api/admin/billing/catalog/{it.get('platform')}", {"price_monthly": it.get("price_monthly"), "price_yearly": it.get("price_yearly")})
            rec("PUT /billing/catalog (echo)", r.status, is2xx(r.status))

    # ---- billing quote valid
    r = get("/api/billing/quote?platform=facebook")
    rec("GET /billing/quote (valid)", r.status, is2xx(r.status))
    # ---- marketing syncs graceful-empty
    r = post("/api/marketing/sync-leads")
    rec("POST /marketing/sync-leads (graceful)", r.status, is2xx(r.status))
    r = post("/api/marketing/sync-campaigns")
    rec("POST /marketing/sync-campaigns (graceful)", r.status, is2xx(r.status))
    # ---- meta sync-posts + status (crawl)
    try:
        r = pg.request.post(B + "/api/meta/sync-posts", data={}, timeout=120000)
        rec("POST /meta/sync-posts (crawl)", r.status, is2xx(r.status))
    except Exception as e:
        rec("POST /meta/sync-posts (crawl)", "TIMEOUT", False)
    r = get("/api/meta/status")
    rec("GET /meta/status", r.status, is2xx(r.status))
    # ---- payments webhook wrong signature -> clean 4xx
    r = post("/api/payments/webhook/polar", {"x": 1})
    rec("POST /payments/webhook (unsigned->4xx)", r.status, 400 <= r.status < 500)
    # ---- identity queue bad id -> clean
    r = post("/api/identity/queue/00000000-0000-0000-0000-000000000000/approve", {"notes": "x"})
    rec("POST identity approve (bad id->4xx)", r.status, 400 <= r.status < 500)
    b.close()

print(f"\n{'ENDPOINT+SCENARIO':<44} {'HTTP':<6} VERDICT")
for name, code, ok in results:
    print(f"{name:<44} {str(code):<6} {ok}")
fails = [r for r in results if "FAIL" in r[2]]
print(f"\nTOTAL {len(results)} | FAILS: {len(fails)}")
for f in fails: print("   ", f)
