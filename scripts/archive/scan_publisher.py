import re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
src = open("src/templates/studio.html", encoding="utf-8").read()
i = src.find('studio-pane-publisher')
seg = src[i-200:i+1600]
print(seg)
