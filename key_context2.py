import re, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
keys = ['cc_search_ph', 'email_ph', 'fullname_ph', 'password_ph', 'phone_ph']
for f in Path("src/templates").rglob("*.*"):
    if f.suffix not in (".html", ".js"):
        continue
    t = f.read_text(encoding="utf-8", errors="replace")
    for k in keys:
        for m in re.finditer(r'[a-zA-Z-]+="[^"]*' + k + r'[^"]*"([^>]{0,80})', t):
            print(f"{f.name:<16} {k:<15} ctx={m.group(0)[:110]!r}")
