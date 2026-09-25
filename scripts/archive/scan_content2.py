import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
svc = open("src/content_studio/service.py", encoding="utf-8").read()
i = svc.find("def create_post")
print(svc[i+700:i+1500])
print("=== list_posts ===")
j = svc.find("def list_posts")
print(svc[j:j+900])
