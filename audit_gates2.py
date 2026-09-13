"""Phase 2b: confirm anon '200's are login-redirect follow (not data leaks) + user 403s
are entitlement gates by design on connections authorize."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from playwright.sync_api import sync_playwright

B = "http://localhost:8000"
checks = ["/dashboard", "/inbox", "/leads", "/studio", "/automations", "/knowledge",
          "/onboarding", "/analytics", "/identity", "/settings", "/users", "/templates"]

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context()
    pg = ctx.new_page()
    for path in checks:
        r = ctx.request.get(f"{B}{path}", max_redirects=0, timeout=15000)
        loc = r.headers.get("location") or ""
        verdict = "OK 303->login" if r.status == 303 and "/login" in loc else \
                  ("OK 401" if r.status == 401 else f"CHECK {r.status} -> {loc[:60]}")
        nxt = "next=" in loc
        print(f"{path:<14} {r.status} -> {'login' if '/login' in loc else loc[:40]!r} next-param={nxt} {verdict}")
    # entitlement gate proof: user WITHOUT subscription gets 403 (by design, Wave 9.7)
    pg2 = b.new_context().new_page()
    pg2.goto(f"{B}/login"); pg2.wait_for_load_state("networkidle")
    pg2.fill("#loginEmail", "user.test@hudhud.test"); pg2.fill("#loginPassword", "AdminTest#2026")
    pg2.click("#loginBtn"); pg2.wait_for_timeout(3000)
    r = pg2.request.get(f"{B}/api/connections/facebook/authorize", max_redirects=0)
    print("\nuser authorize gate:", r.status, r.text()[:100])
    r2 = pg2.request.get(f"{B}/api/knowledge/documents", max_redirects=0)
    print("user own-scoped knowledge:", r2.status, r2.text()[:80])
    b.close()
