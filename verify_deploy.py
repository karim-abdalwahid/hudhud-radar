import urllib.request, time, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
for attempt in range(8):
    try:
        req = urllib.request.Request(
            "https://www.hudhd.com/static/saas.js?cb=" + str(int(time.time())),
            headers={"User-Agent": "Mozilla/5.0", "Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=20) as r:
            js = r.read().decode("utf-8", errors="replace")
        if "_isAdmin" in js and "stripDevNav" in js:
            print(f"DEPLOY VERIFIED attempt {attempt+1}: new role-separation code is LIVE on hudhd.com")
            break
        print(f"attempt {attempt+1}: not yet")
    except Exception as e:
        print(f"attempt {attempt+1}: {str(e)[:80]}")
    time.sleep(30)
