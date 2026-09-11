"""Stay on dashboard (no navigation) — verify overview data actually loads."""
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

errors = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(viewport={"width": 1920, "height": 1080}).new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)[:200]))
    pg.on("console", lambda m: errors.append(m.text[:200]) if m.type == "error" else None)

    pg.goto("http://localhost:8000/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test")
    pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn")
    pg.wait_for_url("**/dashboard**", timeout=10000)
    pg.wait_for_timeout(6000)  # let all fetches settle — NO navigation

    kpis = pg.evaluate("""() => {
        const out = {};
        document.querySelectorAll('.metric-card, [id^=kpi-]').forEach(el => {
            const id = el.id || el.querySelector('[id^=kpi-]')?.id;
            if (id) out[id] = document.getElementById(id)?.textContent?.trim();
        });
        out.leads_rows = document.querySelectorAll('#overview-leads-body tr').length;
        return out;
    }""")
    print("KPIs after settling:", kpis)
    print("JS errors while idle:", len(errors))
    for e in errors[:6]:
        print("  ", e)
    b.close()
print("DONE")
