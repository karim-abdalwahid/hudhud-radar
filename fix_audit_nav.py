import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "audit_live.py"
src = open(p, encoding="utf-8").read()
old = ('    url = BASE + path\n'
       '    if lang == "ar":\n'
       '        url += ("&" if "?" in url else "?") + "lang=ar"\n'
       '    pg.goto(url)')
new = ('    url = BASE + path\n'
       '    if lang == "ar":\n'
       '        url += ("&" if "?" in url else "?") + "lang=ar"\n'
       '    # skip redundant navigation when already on the target (avoids aborting\n'
       '    # in-flight fetches of the just-loaded page - measurement artifact)\n'
       '    if not pg.url.split("?")[0].rstrip("/").endswith(path):\n'
       '        pg.goto(url)')
assert old in src, "anchor not found"
src = src.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(src)
print("navigation guard added to audit_live.py")
