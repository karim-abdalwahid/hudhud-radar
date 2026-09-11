import re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
src = open("src/templates/studio.html", encoding="utf-8").read()
print("=== studio tab buttons / sections ===")
for m in re.finditer(r'<button[^>]*(?:data-tab|onclick="setStudioTab[^"]*")[^>]*>[^<]{0,60}', src):
    print(" ", m.group(0)[:130])
print("\n=== ids of major sections ===")
print(re.findall(r'id="(studio-[\w-]+|tab-[\w-]+|composer[\w-]*|create[\w-]*)"', src)[:20])
print("\n=== hash/tab handling ===")
for m in re.finditer(r'[^\n]*(location\.hash|setTab|switchTab|tab=)[^\n]*', src):
    print(" ", m.group(0).strip()[:130])
print("\n=== the 3 /studio links context in overview ===")
ov = open("src/templates/overview.html", encoding="utf-8").read()
for m in re.finditer(r'[^\n]*/studio[^\n]*', ov):
    print(" ", m.group(0).strip()[:150])
