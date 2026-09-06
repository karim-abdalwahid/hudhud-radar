"""Verify new token validity + fix insights metrics per Graph API v26."""
import sys

sys.path.insert(0, ".")

import httpx
from dotenv import load_dotenv

load_dotenv()
import os  # noqa: E402

from src.config import settings  # noqa: E402
from src.meta_api.extended_api import _resolve_credentials  # noqa: E402


def main():
    token = os.getenv("META_PAGE_ACCESS_TOKEN")
    app_token = f"{settings.META_APP_ID}|{settings.META_APP_SECRET}"

    # 1. Token validity via debug_token
    r = httpx.get(
        f"{settings.META_GRAPH_API_BASE_URL}/debug_token",
        params={"input_token": token, "access_token": app_token},
        timeout=15,
    )
    d = r.json().get("data", {})
    print("VALID:", d.get("is_valid"), "| TYPE:", d.get("type"), "| EXPIRES:", d.get("expires_at"), "(0=never)")
    print("SCOPES:", ", ".join(d.get("scopes", [])))

    creds = _resolve_credentials()

    # 2. Correct FB metrics (v26 valid names)
    async def test():
        async with httpx.AsyncClient(timeout=15) as c:
            r1 = await c.get(
                f"{settings.META_GRAPH_API_BASE_URL}/{creds['page_id']}/insights",
                params={
                    "metric": "page_impressions,page_post_engagements,page_follows",
                    "period": "day", "date_preset": "last_7d",
                    "access_token": token,
                },
            )
            print("FB insights:", r1.status_code, r1.text[:250])

            r2 = await c.get(
                f"{settings.META_GRAPH_API_BASE_URL}/{creds['ig_id']}/insights",
                params={
                    "metric": "reach,views,follower_count",
                    "period": "day", "date_preset": "last_7d",
                    "access_token": token,
                },
            )
            print("IG insights:", r2.status_code, r2.text[:250])

    import asyncio
    asyncio.run(test())


if __name__ == "__main__":
    main()
