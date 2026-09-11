import re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
src = open("src/templates/overview.html", encoding="utf-8").read()
i = src.find("function loadOverviewData")
print(repr(src[max(0, i - 160):i + 60]))
print("---leads routes---")
main = open("src/modules/leads/routes.py", encoding="utf-8").read()
print(re.findall(r'@router\.(?:get|post)\("([^"]+)"', main))
