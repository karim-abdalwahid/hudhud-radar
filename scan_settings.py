import re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
src = open("src/templates/settings.html", encoding="utf-8").read()
print("file size:", len(src))
for m in re.finditer(r'<(h2|h3|section|div class="(?:panel|settings-card|card)[^"]*")[^>]*>([^<]{0,80})', src):
    print(f"{m.start():>6}  <{m.group(1)[:24]}> {m.group(2).strip()[:70]!r}")
