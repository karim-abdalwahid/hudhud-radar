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


def resolve_page_token(user_id: Optional[str], account_id: Optional[str]) -> Optional[str]:
    """Resolve a token only when both tenant and recipient account are known."""
    if not user_id or not account_id or str(account_id).startswith("your-"):
        return None
    try:
        from src.core.supabase_client import supabase_db as active_db
        if not active_db.is_connected:
            return None
        rows = (active_db.select("platform_connections", {
            "user_id": user_id, "status": "active"}) or [])
        for r in rows:
            if r.get("platform") not in ("facebook", "instagram"):
                continue
            if str(r.get("account_id") or "") != str(account_id):
                continue
            try:
                from src.core.crypto import decrypt_token
                tok = decrypt_token(r.get("access_token_encrypted") or "")
                if tok:
                    return tok
            except Exception as e:
                logger.warning(f"Per-page token decrypt failed for account {account_id}: {e}")
                return None
    except Exception as e:
        logger.warning(f"Per-page token resolution unavailable: {e}")
    return None


class MetaGraphClient:
    """Production client for Facebook & Instagram Graph API."""

    BASE_URL = settings.META_GRAPH_API_BASE_URL

    def __init__(
        self,
        access_token: Optional[str] = None,
        page_id: Optional[str] = None,
        instagram_id: Optional[str] = None
    ):
        # SaaS paths pass an exact tenant credential for every Graph call.
        # Environment values only keep isolated local/single-workspace tooling
        # usable; this client never reads a shared database token.
        self.access_token = access_token or settings.META_PAGE_ACCESS_TOKEN
        self.page_id = page_id or settings.META_PAGE_ID
        self.instagram_id = instagram_id or settings.META_INSTAGRAM_ACCOUNT_ID

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

    async def get_profile(
        self,
        user_id: str,
        fields: str = "id,name,first_name,last_name,profile_pic,username",
        access_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetches public user profile information via Graph API."""
        rate_limiter.check_and_acquire("facebook")
        url = f"{self.BASE_URL}/{user_id}"
        token = access_token or self.access_token
        if not token:
            raise MetaAPIError("Meta access token is not configured")
        params = {"fields": fields, "access_token": token}

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
        tag: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """Validates Meta 24-hour standard messaging policy window."""
        if settings.ENFORCE_24H_WINDOW and not tag and last_interaction_time:
            now = datetime.now(timezone.utc)
            diff = now - last_interaction_time
            if diff > timedelta(hours=24):
                hours = diff.total_seconds() / 3600
                logger.error(f"Cannot send {platform.capitalize()} DM to {recipient_id}: 24h window expired ({hours:.1f}h)")
                self._log_activity("send_message", platform, recipient_id, "failed",
                                   f"24h window expired ({hours:.1f}h)", user_id=user_id)
                raise MessagingWindowExpiredError(recipient_id=recipient_id, elapsed_hours=hours)

    async def send_facebook_message(
        self,
        recipient_id: str,
        message_text: str,
        last_interaction_time: Optional[datetime] = None,
        tag: Optional[str] = None,
        access_token: Optional[str] = None,
        messaging_type: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Sends a Direct Message to a Facebook Page conversation.
        Strictly enforces the 24-hour messaging window unless a legitimate tag or
        an approved human-agent context is supplied.
        access_token: per-page token when provided (Wave 9.8), else legacy global.
        messaging_type: e.g. HUMAN_AGENT — the sanctioned out-of-window path.
        """
        if messaging_type != "HUMAN_AGENT":
            self._validate_messaging_window(recipient_id, "facebook", last_interaction_time, tag, user_id)

        token = access_token or self.access_token
        rate_limiter.check_and_acquire("facebook")
        url = f"{self.BASE_URL}/me/messages"
        params = {"access_token": token}
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": message_text}
        }
        if tag:
            payload["messaging_type"] = "MESSAGE_TAG"
            payload["tag"] = tag
        if messaging_type and messaging_type != "MESSAGE_TAG":
            payload["messaging_type"] = messaging_type

        try:
            # ZERO-FABRICATION: without a real token we FAIL honestly —
            # no simulated delivery receipts, no fake activity_logs success.
            if not token or token.startswith("your-"):
                logger.error(f"FB DM to {recipient_id} NOT sent: Meta token not configured (fail-closed, no simulation).")
                self._log_activity("send_message", "facebook", recipient_id, "failed", "Meta token not configured", user_id)
                raise MetaAPIError("Meta Page Access Token غير مضبوط — لم يتم إرسال الرسالة (لا توجد محاكاة)", status_code=503)

            resp = await self._post_with_retry(url, params, payload, "facebook", recipient_id, "send_message")
            if resp.status_code != 200:
                err_msg = resp.text
                self._log_activity("send_message", "facebook", recipient_id, "failed", err_msg, user_id)
                raise MetaAPIError(f"Meta Send API Error: {err_msg}", status_code=resp.status_code)

            data = resp.json()
            self._log_activity("send_message", "facebook", recipient_id, "success", None, user_id)
            return data
        except httpx.RequestError as e:
            self._log_activity("send_message", "facebook", recipient_id, "failed", str(e), user_id)
            raise MetaAPIError(f"Network error sending message: {str(e)}")

    async def send_instagram_message(
        self,
        recipient_id: str,
        message_text: str,
        last_interaction_time: Optional[datetime] = None,
        access_token: Optional[str] = None,
        messaging_type: Optional[str] = None,
        tag: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Sends an Instagram Direct Message adhering to Instagram Business Messaging rules.
        access_token: per-account token when provided (Wave 9.8), else legacy global.
        messaging_type: HUMAN_AGENT — sanctioned out-of-window human path.
        tag: approved message tag (MESSAGE_TAG path) for out-of-window sends.
        """
        if tag:
            self._validate_messaging_window(recipient_id, "instagram", last_interaction_time, tag, user_id)
        elif messaging_type != "HUMAN_AGENT":
            self._validate_messaging_window(recipient_id, "instagram", last_interaction_time, user_id=user_id)

        token = access_token or self.access_token
        rate_limiter.check_and_acquire("instagram")
        url = f"{self.BASE_URL}/me/messages"
        params = {"access_token": token}
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": message_text}
        }
        if tag:
            payload["messaging_type"] = "MESSAGE_TAG"
            payload["tag"] = tag
        if messaging_type and messaging_type != "MESSAGE_TAG":
            payload["messaging_type"] = messaging_type

        try:
            # ZERO-FABRICATION: without a real token we FAIL honestly —
            # no simulated delivery receipts, no fake activity_logs success.
            if not token or token.startswith("your-"):
                logger.error(f"IG DM to {recipient_id} NOT sent: Meta token not configured (fail-closed, no simulation).")
                self._log_activity("send_message", "instagram", recipient_id, "failed", "Meta token not configured", user_id)
                raise MetaAPIError("Meta Page Access Token غير مضبوط — لم يتم إرسال الرسالة (لا توجد محاكاة)", status_code=503)

            resp = await self._post_with_retry(url, params, payload, "instagram", recipient_id, "send_ig_message")
            if resp.status_code != 200:
                err_msg = resp.text
                self._log_activity("send_message", "instagram", recipient_id, "failed", err_msg, user_id)
                raise MetaAPIError(f"Instagram Send API Error: {err_msg}", status_code=resp.status_code)

            data = resp.json()
            self._log_activity("send_message", "instagram", recipient_id, "success", None, user_id)
            return data
        except httpx.RequestError as e:
            self._log_activity("send_message", "instagram", recipient_id, "failed", str(e), user_id)
            raise MetaAPIError(f"Network error sending IG message: {str(e)}")

    def _log_activity(self, action_type: str, platform: str, target_id: str,
                      status: str, error_reason: Optional[str], user_id: Optional[str] = None):
        """Records an owned action into the tenant audit trail.

        ``activity_logs.user_id`` is intentionally mandatory in production.
        A webhook/system event that cannot be tied to a customer must not
        create a tenantless database record (or become visible in reports).
        Its details remain in the application log for operators instead.
        """
        if not user_id:
            logger.warning(
                "Skipping tenantless activity log: action=%s platform=%s target=%s",
                action_type, platform, target_id,
            )
            return
        row = {
            "action_type": action_type,
            "platform": platform,
            "target_id": target_id,
            "status": status,
            "error_reason": error_reason,
            "details": {"timestamp": datetime.now(timezone.utc).isoformat()}
        }
        row["user_id"] = user_id
        supabase_db.insert("activity_logs", row)


meta_client = MetaGraphClient()
