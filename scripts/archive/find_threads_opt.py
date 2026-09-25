import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
src = open("src/templates/studio.html", encoding="utf-8").read()
import re
for m in re.finditer(r'value="threads"', src):
    i = m.start()
    print("=== occurrence at", i, "===")
    print(src[i-260:i+120])
    print()
