"""Phase 1: LIVE sweep of every GET route as admin — catch 5xx, non-JSON, crashes.
Also flags duplicate route registrations."""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from playwright.sync_api import sync_playwright

from src.main import app

B = "http://localhost:8000"
SKIP = {"/api/threads/oauth/callback", "/auth/google/callback",  # redirect flows
        "/api/meta/user-pages"}  # needs real user token (already 403-reviewed)

get_paths, seen = [], {}
for r in app.routes:
    methods = getattr(r, "methods", set())
    path = getattr(r, "path", "")
    if not path or path.startswith("/static"):
        continue
    if "GET" in methods:
        seen[path] = seen.get(path, 0) + 1
        get_paths.append(path)

dups = {p: c for p, c in seen.items() if c > 1}
paths = sorted(set(get_paths) - SKIP - set(dups))

def needs_params(p):
    return "{" in p

def fill(p):
    p = p.replace("{lead_id}", "1b61e13c-7502-422d-9b1e-2ffe6e9d2c20")
    p = p.replace("{filename}", "business_profile.md")
    p = p.replace("{wf_id}", "wf_ig_reel_sales")
    p = p.replace("{post_id}", "00000000-0000-0000-0000-000000000000")
    p = p.replace("{platform}", "threads")
    p = p.replace("{provider_id}", "ca4bb86a-8e95-4e7d-a8d9-b0dfafd79be1")
    p = p.replace("{model_id}", "19fbd962-8fd3-4535-a5fa-16587ebffa87")
    p = p.replace("{user_id}", "190bb1d1-7d62-455c-bf62-af4eb53157e5")
    p = p.replace("{queue_id}", "00000000-0000-0000-0000-000000000000")
    p = p.replace("{thread_id}", "00000000")
    p = p.replace("{coupon_id}", "00000000-0000-0000-0000-000000000000")
    p = p.replace("{notification_id}", "00000000-0000-0000-0000-000000000000")
    return p

bad = []
ok = 0
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context().new_page()
    pg.goto(f"{B}/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=15000)

    for path in paths:
        if path.endswith((".html", "")) and not path.startswith("/api") and not path.startswith("/webhooks") and not path.startswith("/auth"):
            target = fill(path)
            r = pg.request.get(B + target, timeout=20000)
            code = r.status
            is_page = code == 200 or (code == 303 and "login" in (r.headers.get("location") or ""))
        else:
            target = fill(path)
            r = pg.request.get(B + target, timeout=20000)
            code = r.status
            ok_json = False
            try:
                j = r.json(); ok_json = isinstance(j, (dict, list))
            except Exception:
                ok_json = code < 400 and "text" in (r.headers.get("content-type") or "")
            if code not in (200, 303) or not ok_json:
                bad.append((path, code, "BAD-JSON" if ok_json is False else ""))
                continue
        if code >= 500:
            bad.append((path, code, "5XX"))
        else:
            ok += 1
    b.close()

print(f"GET paths swept: {len(paths)} | clean: {ok} | problems: {len(bad)}")
for pth, code, why in bad:
    print(f"  ❌ {pth}  -> {code} {why}")
if dups:
    print("DUPLICATE ROUTE REGISTRATIONS:", dups)
else:
    print("duplicate registrations: none")
