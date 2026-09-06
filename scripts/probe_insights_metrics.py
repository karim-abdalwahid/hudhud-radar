"""Probe valid v26 insights metric names for FB + IG."""
import sys

sys.path.insert(0, ".")

import httpx  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv()
import os  # noqa: E402

PAGE_ID = "1108892288983475"
IG_ID = "17841459820747642"

FB_METRICS = ["page_views", "page_views_total", "page_follows", "page_post_engagements", "page_actions_post_total", "page_daily_follows"]
IG_METRICS = ["views", "reach", "follower_count", "accounts_engaged", "total_interactions"]


def main():
    token = os.getenv("META_PAGE_ACCESS_TOKEN")
    print("=== FB (page) ===")
    ok_fb = []
    for m in FB_METRICS:
        r = httpx.get(
            f"https://graph.facebook.com/v26.0/{PAGE_ID}/insights",
            params={"metric": m, "period": "day", "date_preset": "last_7d", "access_token": token},
            timeout=15,
        )
        status = r.status_code
        has_data = bool(r.json().get("data"))
        print(f"  {m}: {status} data={has_data}")
        if status == 200:
            ok_fb.append(m)

    print("=== IG (instagram) ===")
    ok_ig = []
    for m in IG_METRICS:
        r = httpx.get(
            f"https://graph.facebook.com/v26.0/{IG_ID}/insights",
            params={"metric": m, "period": "day", "date_preset": "last_7d", "access_token": token},
            timeout=15,
        )
        print(f"  {m}: {r.status_code} {r.text[:100]}")
        if r.status_code == 200:
            ok_ig.append(m)

    print("\nFB working:", ok_fb)
    print("IG working:", ok_ig)


if __name__ == "__main__":
    main()
