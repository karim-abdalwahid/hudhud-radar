import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# credits/plan validation
src = open("src/modules/admin_console/__init__.py", encoding="utf-8").read()
i = src.find("def grant_credits")
print("=== grant_credits ==="); print(src[i-120:i+600])
j = src.find("def set_plan")
print("\n=== set_plan ==="); print(src[j-150:j+600])

# scheduler due-publish race guard
s2 = open("src/agent/scheduler.py", encoding="utf-8").read()
k = s2.find("def check_and_publish_due_posts")
print("\n=== check_and_publish_due_posts ==="); print(s2[k:k+900])
