import re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
src = open("src/modules/billing/__init__.py", encoding="utf-8").read()
i = src.find('"/api/billing/quote"')
print(src[i-120:i+500])
