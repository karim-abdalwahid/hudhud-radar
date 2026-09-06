"""
Meta Graph API Async Client.
Handles Facebook Page and Instagram Business Account messaging, profile retrieval, and insights.
"""
import asyncio
from typing import Dict, Any, Optional
import httpx
from datetime import datetime, timezone, timedelta
from src.config import settings
from src.core.logger import logger
from src.core.exceptions import MetaAPIError, MessagingWindowExpiredError
from src.meta_api.rate_limiter import rate_limiter
from src.core.supabase_client import supabase_db

# Transient HTTP status codes worth retrying (network/server throttling hiccups)
RETRYABLE_STATUS_CODES = {500, 502, 503, 504}
MAX_SEND_RETRIES = 2
RETRY_BASE_DELAY_SECONDS = 1.0


class MetaGraphClient:
    """Production client for Facebook & Instagram Graph API."""

    BASE_URL = settings.META_GRAPH_API_BASE_URL

    def __init__(
        self,
        access_token: Optional[str] = settings.META_PAGE_ACCESS_TOKEN,
        page_id: Optional[str] = settings.META_PAGE_ID,
        instagram_id: Optional[str] = settings.META_INSTAGRAM_ACCOUNT_ID
    ):
        self.access_token = access_token
        self.page_id = page_id
        self.instagram_id = instagram_id

    async def _post_with_retry(
        self, url: str, params: Dict[str, Any], json_payload: Dict[str, Any],
        platform: str, target_id: str, action: str
    ) -> httpx.Response:
        """
        POST with bounded exponential backoff on transient failures.
        Never retries 4xx policy errors (they are deterministic).
        """
        last_error: Optional[Exception] = None
        for attempt in range(MAX_SEND_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, params=params, json=json_payload)
                    rate_limiter.update_from_headers(platform, dict(resp.headers))
                if resp.status_code == 200:
                    return resp
                if resp.status_code in RETRYABLE_STATUS_CODES and attempt < MAX_SEND_RETRIES:
                    delay = RETRY_BASE_DELAY_SECONDS * (2 ** attempt)
                    logger.warning(
                        f"Transient Meta {resp.status_code} on {action} to {target_id} — retrying in {delay:.0f}s "
                        f"(attempt {attempt + 1}/{MAX_SEND_RETRIES})"
                    )
                    await asyncio.sleep(delay)
                    continue
                return resp
            except httpx.RequestError as e:
                last_error = e
                if attempt < MAX_SEND_RETRIES:
                    delay = RETRY_BASE_DELAY_SECONDS * (2 ** attempt)
                    logger.warning(f"Network error on {action} to {target_id} — retrying in {delay:.0f}s: {e}")
                    await asyncio.sleep(delay)
                    continue
                raise
        raise last_error or MetaAPIError(f"{action} failed after retries")

    async def get_profile(self, user_id: str, fields: str = "id,name,first_name,last_name,profile_pic,username") -> Dict[str, Any]:
        """Fetches public user profile information via Graph API."""
        rate_limiter.check_and_acquire("facebook")
        url = f"{self.BASE_URL}/{user_id}"
        params = {"fields": fields, "access_token": self.access_token}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                rate_limiter.update_from_headers("facebook", dict(resp.headers))
                if resp.status_code != 200:
                    raise MetaAPIError(f"Failed to fetch profile: {resp.text}", status_code=resp.status_code)
                return resp.json()
        except httpx.RequestError as e:
            logger.error(f"Network error getting profile {user_id}: {e}")
            raise MetaAPIError(f"Network error: {str(e)}")

    def _validate_messaging_window(
        self,
        recipient_id: str,
        platform: str,
        last_interaction_time: Optional[datetime],
        tag: Optional[str] = None
    ):
        """Validates Meta 24-hour standard messaging policy window."""
        if settings.ENFORCE_24H_WINDOW and not tag and last_interaction_time:
            now = datetime.now(timezone.utc)
            diff = now - last_interaction_time
            if diff > timedelta(hours=24):
                hours = diff.total_seconds() / 3600
                logger.error(f"Cannot send {platform.capitalize()} DM to {recipient_id}: 24h window expired ({hours:.1f}h)")
                self._log_activity("send_message", platform, recipient_id, "failed", f"24h window expired ({hours:.1f}h)")
                raise MessagingWindowExpiredError(recipient_id=recipient_id, elapsed_hours=hours)

    async def send_facebook_message(
        self,
        recipient_id: str,
        message_text: str,
        last_interaction_time: Optional[datetime] = None,
        tag: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends a Direct Message to a Facebook Page conversation.
        Strictly enforces the 24-hour messaging window unless a legitimate tag is supplied.
        """
        self._validate_messaging_window(recipient_id, "facebook", last_interaction_time, tag)

        rate_limiter.check_and_acquire("facebook")
        url = f"{self.BASE_URL}/me/messages"
        params = {"access_token": self.access_token}
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": message_text}
        }
        if tag:
            payload["messaging_type"] = "MESSAGE_TAG"
            payload["tag"] = tag

        try:
            # If access_token is empty or mock, simulate successful send in development
            if not self.access_token or self.access_token.startswith("your-"):
                logger.info(f"[DEV SIMULATION] Sent FB DM to {recipient_id}: '{message_text}'")
                simulated_resp = {"recipient_id": recipient_id, "message_id": f"mid.simulated.{recipient_id}"}
                self._log_activity("send_message", "facebook", recipient_id, "success", None)
                return simulated_resp

            resp = await self._post_with_retry(url, params, payload, "facebook", recipient_id, "send_message")
            if resp.status_code != 200:
                err_msg = resp.text
                self._log_activity("send_message", "facebook", recipient_id, "failed", err_msg)
                raise MetaAPIError(f"Meta Send API Error: {err_msg}", status_code=resp.status_code)

            data = resp.json()
            self._log_activity("send_message", "facebook", recipient_id, "success", None)
            return data
        except httpx.RequestError as e:
            self._log_activity("send_message", "facebook", recipient_id, "failed", str(e))
            raise MetaAPIError(f"Network error sending message: {str(e)}")

    async def send_instagram_message(
        self,
        recipient_id: str,
        message_text: str,
        last_interaction_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Sends an Instagram Direct Message adhering to Instagram Business Messaging rules.
        """
        self._validate_messaging_window(recipient_id, "instagram", last_interaction_time)

        rate_limiter.check_and_acquire("instagram")
        url = f"{self.BASE_URL}/me/messages"
        params = {"access_token": self.access_token}
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": message_text}
        }

        try:
            if not self.access_token or self.access_token.startswith("your-"):
                logger.info(f"[DEV SIMULATION] Sent IG DM to {recipient_id}: '{message_text}'")
                simulated_resp = {"recipient_id": recipient_id, "message_id": f"ig.mid.simulated.{recipient_id}"}
                self._log_activity("send_message", "instagram", recipient_id, "success", None)
                return simulated_resp

            resp = await self._post_with_retry(url, params, payload, "instagram", recipient_id, "send_ig_message")
            if resp.status_code != 200:
                err_msg = resp.text
                self._log_activity("send_message", "instagram", recipient_id, "failed", err_msg)
                raise MetaAPIError(f"Instagram Send API Error: {err_msg}", status_code=resp.status_code)

            data = resp.json()
            self._log_activity("send_message", "instagram", recipient_id, "success", None)
            return data
        except httpx.RequestError as e:
            self._log_activity("send_message", "instagram", recipient_id, "failed", str(e))
            raise MetaAPIError(f"Network error sending IG message: {str(e)}")

    def _log_activity(self, action_type: str, platform: str, target_id: str, status: str, error_reason: Optional[str]):
        """Records the action into the activity_logs table for auditability."""
        supabase_db.insert("activity_logs", {
            "action_type": action_type,
            "platform": platform,
            "target_id": target_id,
            "status": status,
            "error_reason": error_reason,
            "details": {"timestamp": datetime.now(timezone.utc).isoformat()}
        })


meta_client = MetaGraphClient()
