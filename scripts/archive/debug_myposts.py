import re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
src = open("src/meta_api/extended_api.py", encoding="utf-8").read()
i = src.find("async def get_my_posts")
print("get_my_posts at:", i)
print(src[max(0, i-320):i+500])
print("=== singletons ===")
for m in re.finditer(r"^\w+ = \w+\(\)", src, re.M):
    print(f"  line {src[:m.start()].count(chr(10))+1}: {m.group(0)}")
