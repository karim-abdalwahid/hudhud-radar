import os, json, urllib.request, urllib.parse, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import load_dotenv
load_dotenv()

IG_ID = os.getenv("META_INSTAGRAM_ACCOUNT_ID")
page_tok = os.getenv("META_PAGE_ACCESS_TOKEN")
ig_tok = os.getenv("IG_BUSINESS_ACCESS_TOKEN")

for label, tok in [("page_token", page_tok), ("ig_business_token", ig_tok)]:
    if not tok:
        print(label, "-> not configured"); continue
    url = (f"https://graph.facebook.com/v21.0/{IG_ID}/media?"
           + urllib.parse.urlencode({"fields": "id,like_count,comments_count,media_product_type",
                                     "limit": "3", "access_token": tok}))
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode()).get("data", [])
        print(f"--- {label}:")
        for d in data:
            print(f"    {d.get('media_product_type')}: likes={d.get('like_count')} comments={d.get('comments_count')}")
    except Exception as e:
        print(f"--- {label}: ERROR {str(e)[:150]}")
