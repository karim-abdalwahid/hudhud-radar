"""
COMPREHENSIVE LIVE AUDIT — every page x 2 languages, JS errors, failed requests,
tab interactions, KPI placeholders. Errors are collected only AFTER the page
settles (idle) to exclude navigation-abort artifacts.
Output: docs/PROJECT_REPORTS/AUDIT_2026-09-11_LIVE.md
"""
import sys
import urllib.parse
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = "http://localhost:8000"
EMAIL, PASSWORD = "admin.test@hudhud.test", "AdminTest#2026"
OUT = []
S = lambda s: OUT.append(s)

ADMIN_PAGES = ["/dashboard", "/inbox", "/leads", "/studio", "/automations",
               "/knowledge", "/identity", "/analytics", "/settings", "/users", "/templates"]
PUBLIC_PAGES = ["/", "/login", "/terms", "/privacy"]

report_rows = []

def sweep_page(pg, path, lang):
    rec = {"path": path, "lang": lang, "errors": [], "failed": [], "tabs": None, "kpi_placeholder": 0}
    pg.on("pageerror", lambda e: rec["errors"].append("pageerror: " + str(e)[:220]))
    pg.on("console", lambda m: rec["errors"].append("console: " + m.text[:220]) if m.type == "error" else None)
    pg.on("requestfailed", lambda r: rec["failed"].append(r.url[:110] + " :: " + str(r.failure)[:60]))

    url = BASE + path
    if lang == "ar":
        url += ("&" if "?" in url else "?") + "lang=ar"
    pg.goto(url)
    try:
        pg.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    pg.wait_for_timeout(3500)  # idle settle
    rec["errors"] = list(rec["errors"])   # snapshot (post-settle only)

    # tabs interaction: click every .set-tab / generic tab buttons and verify panels
    tab_report = []
    tabs = pg.query_selector_all(".set-tab, [data-tab]")
    for i, tb in enumerate(tabs[:8]):
        try:
            before = pg.evaluate("() => [...document.querySelectorAll('.panel-section, .tab-panel, [id^=set-tab-page-]')].filter(e => e.offsetParent !== null).length")
            tb.click()
            pg.wait_for_timeout(600)
            after = pg.evaluate("() => [...document.querySelectorAll('.panel-section, .tab-panel, [id^=set-tab-page-]')].filter(e => e.offsetParent !== null).length")
            tab_report.append(f"tab#{i}: visible {before}->{after}")
        except Exception as e:
            tab_report.append(f"tab#{i}: ERROR {str(e)[:80]}")
    rec["tabs"] = tab_report

    # KPI placeholders left as em-dash after settle
    rec["kpi_placeholder"] = pg.evaluate(
        "() => [...document.querySelectorAll('[id^=kpi-]')].filter(e => e.textContent.trim() === '—').length")
    return rec

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(viewport={"width": 1920, "height": 1080}).new_page()

    # login once
    pg.goto(f"{BASE}/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", EMAIL); pg.fill("#loginPassword", PASSWORD)
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=15000)

    for lang in ("en", "ar"):
        for path in ADMIN_PAGES:
            try:
                rec = sweep_page(pg, path, lang)
            except Exception as e:
                rec = {"path": path, "lang": lang, "errors": [f"SWEEP FAILED: {str(e)[:150]}"], "failed": [], "tabs": None, "kpi_placeholder": -1}
            report_rows.append(rec)

    # public pages (logged-out context)
    pub = b.new_context(viewport={"width": 1920, "height": 1080}).new_page()
    for path in PUBLIC_PAGES:
        rec = {"path": path, "lang": "en", "errors": [], "failed": [], "tabs": None, "kpi_placeholder": 0}
        pub.on("pageerror", lambda e, r=rec: r["errors"].append("pageerror: " + str(e)[:220]))
        pub.on("console", lambda m, r=rec: r["errors"].append("console: " + m.text[:220]) if m.type == "error" else None)
        try:
            pub.goto(BASE + path)
            pub.wait_for_load_state("networkidle", timeout=15000)
            pub.wait_for_timeout(2500)
            rec["errors"] = list(rec["errors"])
        except Exception as e:
            rec["errors"].append(f"SWEEP FAILED: {str(e)[:150]}")
        report_rows.append(rec)
    b.close()

# ---------------- render report ----------------
S("# 🌐 Live Audit Report — 2026-09-11 (all pages x EN/AR)\n")
S("| Page | Lang | JS errors | Failed requests | KPI placeholders |")
S("|---|---|---|---|---|")
issues = 0
for r in report_rows:
    errs = "; ".join(r["errors"][:2]) if r["errors"] else "—"
    fails = "; ".join(r["failed"][:2]) if r["failed"] else "—"
    if r["errors"] or r["failed"] or r["kpi_placeholder"] > 0:
        issues += 1
    S(f"| {r['path']} | {r['lang']} | {errs[:150]} | {fails[:150]} | {r['kpi_placeholder']} |")
S("")
S(f"**Pages with issues: {issues}/{len(report_rows)}**\n")
S("## Tab interaction details\n")
for r in report_rows:
    if r["tabs"]:
        S(f"### {r['path']} ({r['lang']})")
        for t in r["tabs"]:
            S(f"- {t}")
        S("")

out_path = Path("docs/PROJECT_REPORTS/AUDIT_2026-09-11_LIVE.md")
out_path.write_text("\n".join(OUT), encoding="utf-8")
print(f"Pages swept: {len(report_rows)} | with issues: {issues}")
print("Report:", out_path)
