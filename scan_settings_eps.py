import re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
src = open("src/templates/settings.html", encoding="utf-8").read()
eps = sorted(set(re.findall(r"fetch\(['\"`][^'\"`]*?(/api/[a-zA-Z0-9_/{}.\-]+|/auth/[a-zA-Z0-9_/]+)", src)))
print("Endpoints called by settings.html:")
for e in eps:
    print("  ", e)
funcs = re.findall(r'(?:async )?function (\w+)\(\)', src)
print("\nJS functions:", len(funcs))
print([f for f in funcs if 'load' in f or 'save' in f or 'check' in f or 'sync' in f][:20])
