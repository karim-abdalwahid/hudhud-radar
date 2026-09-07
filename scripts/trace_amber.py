"""Trace amber redirect chain + confirm restoration (script to avoid PS escaping)."""
import httpx

s = httpx.Client(timeout=30)
url = "https://hudhud-amber.vercel.app/"
for i in range(5):
    r = s.get(url, follow_redirects=False)
    loc = r.headers.get("location", "")
    print(f"step {i+1}: {r.status_code} -> {loc[:70] if loc else '(end)'}")
    if not loc or r.status_code not in (301, 302, 307, 308):
        print("final:", r.status_code)
        if "<title>" in r.text:
            t = r.text
            print("title:", t[t.find("<title>") + 7:t.find("</title>")][:60])
        break
    url = loc if loc.startswith("http") else "https://hudhud-amber.vercel.app" + loc
