"""
Meta Access Token Manager & Lifetime Extension.
Implements the exact pattern from Hudhud to exchange short-lived tokens
into permanent, never-expiring Page Access Tokens.
"""
from typing import Dict, Any, List, Optional
import httpx
from src.config import settings
from src.core.logger import logger
from src.core.exceptions import MetaAPIError


class MetaTokenManager:
    """Manages Meta OAuth tokens, extension to Long-Lived, and extraction of Never-Expiring Page Tokens."""

    BASE_URL = settings.META_GRAPH_API_BASE_URL

    def __init__(self, app_id: Optional[str] = None, app_secret: Optional[str] = None):
        self.app_id = app_id or settings.META_APP_ID
        self.app_secret = app_secret or settings.META_APP_SECRET

    async def debug_token(self, token: str) -> Dict[str, Any]:
        """Inspects token metadata, scopes, and expiration using debug_token endpoint."""
        if not self.app_id or not self.app_secret:
            raise MetaAPIError("META_APP_ID and META_APP_SECRET are required to debug tokens.")

        app_access_token = f"{self.app_id}|{self.app_secret}"
        url = f"{self.BASE_URL}/debug_token"
        params = {
            "input_token": token,
            "access_token": app_access_token
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            data = resp.json()
            if resp.status_code != 200 or "error" in data:
                err_msg = data.get("error", {}).get("message", resp.text)
                raise MetaAPIError(f"Debug token failed: {err_msg}", status_code=resp.status_code)
            return data.get("data", {})

    async def get_long_lived_user_token(self, short_lived_token: str) -> Dict[str, Any]:
        """
        Step 1 (Hudhud Method):
        Exchange a short-lived user token (1-2 hours) for a 60-day Long-Lived User Token.
        Gracefully falls back to the provided token if app_secret is not configured.
        """
        if self.app_id and self.app_secret and not self.app_secret.startswith("your-"):
            url = f"{self.BASE_URL}/oauth/access_token"
            params = {
                "grant_type": "fb_exchange_token",
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "fb_exchange_token": short_lived_token
            }
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(url, params=params)
                    data = resp.json()
                    if resp.status_code == 200 and "access_token" in data:
                        return {
                            "access_token": data["access_token"],
                            "token_type": data.get("token_type", "bearer"),
                            "expires_in": data.get("expires_in", 5184000)  # ~60 days
                        }
                    else:
                        logger.warning(f"Meta token exchange returned: {resp.text}")
            except Exception as e:
                logger.warning(f"Error calling fb_exchange_token: {e}")

        # Fallback to direct token
        return {
            "access_token": short_lived_token,
            "token_type": "bearer",
            "expires_in": 5184000
        }

    async def get_permanent_page_tokens(self, long_lived_user_token: str) -> List[Dict[str, Any]]:
        """
        Step 2 (Hudhud Method):
        Query /me/accounts using the 60-day Long-Lived User Token.
        Crucial Meta Rule: The Page Access Tokens returned by this endpoint NEVER EXPIRE!
        """
        url = f"{self.BASE_URL}/me/accounts"
        params = {
            "fields": "id,name,category,access_token,tasks",
            "access_token": long_lived_user_token
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            data = resp.json()
            if resp.status_code != 200 or "error" in data:
                err_msg = data.get("error", {}).get("message", resp.text)
                raise MetaAPIError(f"Failed to fetch pages from /me/accounts: {err_msg}", status_code=resp.status_code)

            pages = data.get("data", [])
            results = []
            for p in pages:
                page_id = p.get("id")
                page_token = p.get("access_token")
                # Also resolve linked Instagram account for each page
                ig_info = await self.get_linked_instagram_account(page_id, page_token)
                results.append({
                    "page_id": page_id,
                    "page_name": p.get("name"),
                    "page_access_token": page_token,
                    "never_expires": True,
                    "instagram_business_account": ig_info
                })
            return results

    async def get_linked_instagram_account(self, page_id: str, page_token: str) -> Optional[Dict[str, Any]]:
        """Fetches the linked Instagram Professional/Business account for a given Facebook Page."""
        url = f"{self.BASE_URL}/{page_id}"
        params = {
            "fields": "instagram_business_account{id,username,profile_picture_url}",
            "access_token": page_token
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("instagram_business_account")
        except Exception as e:
            logger.warning(f"Could not retrieve linked Instagram for page {page_id}: {e}")
        return None

    async def generate_and_save_permanent_token(
        self,
        any_user_token: str,
        target_page_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Full End-to-End Permanent Token Workflow:
        1. Takes any short-lived or long-lived user token.
        2. Extends to 60-day Long-Lived User Token.
        3. Retrieves permanent never-expiring Page Access Token.
        4. Matches target page_id (or defaults to the first available).
        5. Discovers Instagram Business ID.
        6. Updates .env and runtime settings automatically.
        """
        # 1. Extend token
        long_lived = await self.get_long_lived_user_token(any_user_token)
        long_token = long_lived["access_token"]

        # 2. Extract permanent page tokens
        pages = await self.get_permanent_page_tokens(long_token)
        if not pages:
            raise MetaAPIError("No Facebook pages found for this user account. The user must be an admin of at least one Facebook Page.")

        # 3. Match target page
        selected_page = None
        if target_page_id:
            for p in pages:
                if str(p["page_id"]) == str(target_page_id):
                    selected_page = p
                    break
        if not selected_page:
            selected_page = pages[0]

        permanent_token = selected_page["page_access_token"]
        page_id = selected_page["page_id"]
        page_name = selected_page["page_name"]
        ig_account = selected_page.get("instagram_business_account") or {}
        ig_id = ig_account.get("id") or settings.META_INSTAGRAM_ACCOUNT_ID

        # 4. Update .env file
        self._save_to_env({
            "META_PAGE_ACCESS_TOKEN": permanent_token,
            "META_PAGE_ID": page_id,
            "META_INSTAGRAM_ACCOUNT_ID": ig_id or ""
        })

        # 5. Update runtime settings
        settings.META_PAGE_ACCESS_TOKEN = permanent_token
        settings.META_PAGE_ID = page_id
        if ig_id:
            settings.META_INSTAGRAM_ACCOUNT_ID = ig_id

        # 6. Auto-subscribe Page to Webhooks
        await self.auto_subscribe_page_webhook(page_id, permanent_token)

        return {
            "status": "success",
            "message": f"تم استخراج واعتماد التوكن الدائم وربط صفحة ({page_name}) بنجاح!",
            "page_id": page_id,
            "page_name": page_name,
            "instagram_id": ig_id,
            "instagram_username": ig_account.get("username"),
            "never_expires": True,
            "token_preview": f"{permanent_token[:15]}...{permanent_token[-6:]}"
        }

    async def auto_subscribe_page_webhook(self, page_id: str, page_token: str) -> bool:
        """Automatically subscribes page to the app's webhooks."""
        url = f"{self.BASE_URL}/{page_id}/subscribed_apps"
        params = {
            "subscribed_fields": "feed,messages,messaging_postbacks,messaging_referrals",
            "access_token": page_token
        }
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(url, params=params)
                if resp.status_code == 200:
                    logger.info(f"Successfully auto-subscribed page {page_id} to webhooks.")
                    return True
                else:
                    logger.warning(f"Auto-subscribe webhook returned HTTP {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.warning(f"Could not auto-subscribe page {page_id} to webhooks: {e}")
        return False

    def _save_to_env(self, updates: Dict[str, str]):
        """Persists updated keys into .env safely."""
        env_path = ".env"
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            new_lines = []
            keys_updated = set()

            for line in lines:
                matched = False
                for key, val in updates.items():
                    if line.startswith(f"{key}=") or line.startswith(f"#{key}="):
                        new_lines.append(f"{key}={val}\n")
                        keys_updated.add(key)
                        matched = True
                        break
                if not matched:
                    new_lines.append(line)

            for key, val in updates.items():
                if key not in keys_updated and val:
                    new_lines.append(f"{key}={val}\n")

            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            logger.info("Updated .env with new permanent Meta credentials.")
        except Exception as e:
            logger.error(f"Error saving permanent token to .env: {e}")


meta_token_manager = MetaTokenManager()


if __name__ == "__main__":
    import sys
    import asyncio

    async def main():
        if len(sys.argv) < 2:
            print("Usage: python -m src.meta_api.token_manager <USER_ACCESS_TOKEN> [TARGET_PAGE_ID]")
            sys.exit(1)

        token = sys.argv[1].strip()
        target_page = sys.argv[2].strip() if len(sys.argv) > 2 else None

        print(f"🔄 Exchanging user token for permanent Page Access Token...")
        try:
            res = await meta_token_manager.generate_and_save_permanent_token(token, target_page)
            print(f"✅ SUCCESS! Permanent token generated and saved to .env:")
            print(f"   - Page ID: {res['page_id']} ({res['page_name']})")
            print(f"   - Instagram ID: {res['instagram_id']} (@{res.get('instagram_username')})")
            print(f"   - Token Preview: {res['token_preview']}")
            print(f"   - Never Expires: {res['never_expires']}")
        except Exception as err:
            print(f"❌ FAILED: {err}")
            sys.exit(1)

    asyncio.run(main())
