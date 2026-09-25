import re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
src = open("src/templates/studio.html", encoding="utf-8").read()
i = src.find('id="post-platform"')
print("select block:", src[i-20:i+320])
print("---")
print("threads option present:", 'value="threads"' in src)
# route check
r = open("src/modules/threads_marketing/routes.py", encoding="utf-8").read()
print("my-posts route present:", "/api/threads/my-posts" in r)
a = open("src/core/auth.py", encoding="utf-8").read()
print("auth gate present:", '"/api/threads/my-posts"' in a)
