import sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(viewport={"width": 1920, "height": 1080}).new_page()
    pg.goto("http://localhost:8000/login")
    pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(1200)
    js1 = """() => {
        const out = [];
        ['sc.headline','sc.sub','consent_prefix','password_hint'].forEach(k => {
            const el = document.querySelector('[data-i18n="' + k + '"]');
            out.push({key: k, exists: !!el,
                      text: el ? el.textContent.trim().slice(0, 50) : null,
                      visible: el ? el.offsetParent !== null : false});
        });
        return out;
    }"""
    for x in pg.evaluate(js1):
        print(x)
    pg.click("#tabRegister")
    pg.wait_for_timeout(800)
    js2 = """() => {
        const out = [];
        ['consent_prefix','consent_terms','consent_required','password_hint','fullname'].forEach(k => {
            const el = document.querySelector('[data-i18n="' + k + '"]');
            out.push({key: k, exists: !!el,
                      text: el ? el.textContent.trim().slice(0, 40) : null,
                      visible: el ? el.offsetParent !== null : false});
        });
        return out;
    }"""
    print("--- register tab:")
    for x in pg.evaluate(js2):
        print(x)
    b.close()
