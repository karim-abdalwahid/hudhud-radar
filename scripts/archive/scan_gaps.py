"""Find large EMPTY gaps in landing + login pages (render-blocking gaps)."""
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = "http://localhost:8000"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(viewport={"width": 1920, "height": 1080}).new_page()
    for path in ("/", "/login", "/register"):
        pg.goto(BASE + path)
        pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(1500)
        gaps = pg.evaluate("""() => {
            const out = [];
            document.querySelectorAll('body *').forEach(el => {
                const r = el.getBoundingClientRect();
                const txt = (el.innerText || '').trim();
                const kids = el.children.length;
                const tag = el.tagName.toLowerCase();
                if (r.height >= 60 && !txt && kids === 0
                    && !['script','style','svg','path','br','input','img','circle','rect'].includes(tag)) {
                    out.push({tag, cls: (el.className||'').toString().slice(0,50),
                              id: el.id || '', h: Math.round(r.height), w: Math.round(r.width)});
                }
            });
            return out.sort((a,b) => b.h - a.h).slice(0, 8);
        }""")
        print(f"\n===== {path} — large empty elements =====")
        for g in gaps:
            print(f"  <{g['tag']} class={g['cls']!r} id={g['id']!r}> {g['w']}x{g['h']}")
        if not gaps:
            print("  none")
    b.close()
print("DONE")
