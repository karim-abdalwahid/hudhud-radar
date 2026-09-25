import re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
src = open("src/templates/studio.html", encoding="utf-8").read()
occ = [m.start() for m in re.finditer(r'id="post-platform"', src)]
print("id=post-platform occurrences:", occ)
for i in occ:
    seg = src[i-150:i+400]
    has_threads = 'value="threads"' in seg
    print(f"\n--- at {i} | threads in next 400 chars: {has_threads}")
    print(seg[:420])
