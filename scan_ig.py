import re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
src = open("src/meta_api/feed_sync.py", encoding="utf-8").read()

# IG media fetch: fields requested + how metrics are stored
i = src.find("def fetch_instagram_media")
print("=== fetch_instagram_media (first 2000 chars) ===")
print(src[i:i+2000])
