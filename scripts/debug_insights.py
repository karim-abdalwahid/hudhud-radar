"""Debug: test Meta insights endpoints directly to see real API errors."""
import asyncio

import httpx
from dotenv import load_dotenv

load_dotenv()
from src.config import settings  # noqa: E402
from src.meta_api.extended_api import _resolve_credentials  # noqa: E402


async def main():
    creds = _resolve_credentials()
    token = creds["token"]
    since = 1757100000  # ~a week ago
    until = 1757800000

    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(
            f"{settings.META_GRAPH_API_BASE_URL}/{creds['page_id']}/insights",
            params={
                "metric": "page_impressions,page_post_engagements,page_follows",
                "period": "day", "since": since, "until": until,
                "access_token": token,
            },
        )
        print("FB insights:", r.status_code)
        print(r.text[:500])
        print()
        r2 = await c.get(
            f"{settings.META_GRAPH_API_BASE_URL}/{creds['ig_id']}/insights",
            params={
                "metric": "impressions,reach,follower_count",
                "period": "day", "since": since, "until": until,
                "access_token": token,
            },
        )
        print("IG insights:", r2.status_code)
        print(r2.text[:500])


asyncio.run(main())
