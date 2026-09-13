import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
src = open("src/meta_api/rate_limiter.py", encoding="utf-8").read()
i = src.find("def _parse_usage")
print("=== _parse_usage ==="); print(src[i:i+700])
j = src.find("def update_from_headers")
print("=== update_from_headers ==="); print(src[j:j+500])

k = open("src/core/event_dedup.py", encoding="utf-8").read()
m = k.find("def claim")
print("=== event_dedup.claim ==="); print(k[m:m+900])

n = open("src/main.py", encoding="utf-8").read()
for line in n.splitlines():
    if "is_serverless" in line or "scheduler_task" in line:
        print("MAIN:", line.strip()[:100])
