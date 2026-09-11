import json, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
try:
    c = json.load(open("src/knowledge/meta_live_cache.json", encoding="utf-8"))
    posts = c.get("posts", c if isinstance(c, list) else [])
    ig = [p for p in posts if p.get("platform") == "instagram"][:6]
    for p in ig:
        print("[{}] likes={} comments={} views={} text={!r}".format(
            p.get("post_type"), p.get("likes_count"), p.get("comments_count"),
            p.get("views_count"), str(p.get("content_text"))[:35]))
except Exception as e:
    print("err", e)
