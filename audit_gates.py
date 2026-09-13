"""Phase 2: gate consistency — declared security model (PUBLIC/ADMIN lists)
vs observed responses for anon and regular user. Flags mismatches."""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from playwright.sync_api import sync_playwright

from src.main import app
from src.core.auth import (PUBLIC_EXACT_PATHS, PUBLIC_PATH_PREFIXES,
                           ADMIN_EXACT_PATHS, ADMIN_PATH_PREFIXES,
                           ADMIN_PAGE_PATHS)
from src.core.modules import module_registry

B = "http://localhost:8000"

# expected model
admin_pages = set(ADMIN_PAGE_PATHS) | module_registry.admin_page_paths()
admin_apis = set(ADMIN_EXACT_PATHS)
admin_prefixes = tuple(ADMIN_PATH_PREFIXES)
public_exact = set(PUBLIC_EXACT_PATHS)
public_prefixes = tuple(PUBLIC_PATH_PREFIXES)

def is_public(p):
    return p in public_exact or any(p.startswith(x) for x in public_prefixes)

def admin_required(p, method="GET"):
    return (p in admin_apis or p in admin_pages or p.startswith(admin_prefixes))

paths = []
for r in app.routes:
    m = getattr(r, "methods", set())
    p = getattr(r, "path", "")
    if p and "GET" in m and (p.startswith("/api/") or p in ("/dashboard", "/users", "/leads", "/inbox", "/studio", "/automations", "/knowledge", "/identity", "/analytics", "/settings", "/templates", "/onboarding")):
        paths.append(p)
paths = sorted(set(paths))

def probe(p):
    # cron + webhook endpoints need special params; skip their happy-path
    if "/cron/" in p or "webhook" in p or "callback" in p or "{" in p:
        return None
    return p

results = []
with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True)
    anon = b.new_context().new_page()
    pg = b.new_context().new_page()
    pg.goto(f"{B}/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "user.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_timeout(3500)

    for path in paths:
        tp = probe(path)
        if not tp:
            continue
        expected_admin = admin_required(tp)
        ra = anon.request.get(B + tp, timeout=15000)
        ru = pg.request.get(B + tp, timeout=15000)
        problems = []
        # anon must NOT get 200 data unless public
        if not is_public(tp) and ra.status == 200 and tp.startswith("/api/"):
            problems.append("anon sees API data")
        if not is_public(tp) and ra.status not in (303, 401, 403, 405, 422):
            problems.append(f"anon {ra.status}")
        # user: admin-required must be 403/303; non-admin should not be 403
        if expected_admin and ru.status not in (403, 303, 405, 422, 401):
            problems.append(f"user bypasses admin gate: {ru.status}")
        if not expected_admin and not is_public(tp) and ru.status == 403 and not tp.startswith("/api/admin"):
            problems.append("user over-blocked (403) though not admin-gated")
        if problems:
            results.append((tp, ra.status, ru.status, "; ".join(problems)))
    b.close()

print(f"swept {len([1 for p in paths if probe(p)])} GETs")
if not results:
    print("✅ GATE MODEL: 100% consistent (no mismatches)")
for p, a, u, msg in results:
    print(f"  ⚠️ {p}  anon={a} user={u}  -> {msg}")
