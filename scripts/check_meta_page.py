import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp('http://127.0.0.1:9222')
    for ctx in browser.contexts:
        for pg in ctx.pages:
            if 'developers.facebook.com' in pg.url:
                print('Meta page found:', pg.url)
                text = pg.evaluate('document.body.innerText')
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                for l in lines:
                    if any(w in l.lower() for w in ['instagram_basic', 'instagram basic', 'missing', 'screencast', 'submission']):
                        print('->', l)
