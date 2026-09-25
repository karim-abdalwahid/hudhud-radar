import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
src = open("src/templates/studio.html", encoding="utf-8").read()
i = src.find('id="post-platform"')
print(src[i-30:i+520])
