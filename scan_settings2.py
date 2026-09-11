import re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
src = open("src/templates/settings.html", encoding="utf-8").read()
m = re.search(r"function switchSettingsTab[\s\S]{0,1200}", src)
print(m.group(0)[:1200] if m else "switchSettingsTab NOT FOUND!")
print("---")
print("tab page divs:", re.findall(r'id="set-tab-page-([a-z]+)"', src))
print("panel-section count:", src.count('panel-section'))
