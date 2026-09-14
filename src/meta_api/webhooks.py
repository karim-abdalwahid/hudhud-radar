"""
Meta Webhook Verifier and Event Parser.
Handles SHA-256 HMAC verification and extracts incoming Direct Messages.
"""
import hmac
import hashlib
from typing import Dict, Any, List, Optional
from src.config import settings
from src.core.logger import logger
from src.leads.models import PlatformSource


class WebhookHandler:
    """Validates and parses inbound Meta webhook payloads."""

    @staticmethod
    def verify_subscription(mode: str, token: str, challenge: str) -> Optional[str]:
        """Validates GET webhook challenge from Meta App dashboard.
        Constant-time comparison; the submitted token is never logged raw."""
        valid_tokens = {settings.META_WEBHOOK_VERIFY_TOKEN, settings.EFFECTIVE_WEBHOOK_VERIFY_TOKEN}
        if mode == "subscribe" and token:
            for vt in valid_tokens:
                if vt and hmac.compare_digest(token.encode("utf-8"), vt.encode("utf-8")):
                    logger.info("Meta Webhook challenge successfully verified.")
                    return challenge
        logger.warning("Meta Webhook challenge rejected (token mismatch).")
        return None

    @staticmethod
    def verify_signature(payload_bytes: bytes, signature_header: Optional[str]) -> bool:
        """Verifies HMAC SHA-256 signature against META_APP_SECRET.
        Fail-closed: without a secret, webhooks are ALWAYS rejected (any env)."""
        if not settings.META_APP_SECRET:
            logger.error("META_APP_SECRET not configured — webhook rejected (fail-closed).")
            return False

        if not signature_header:
            logger.error("Missing X-Hub-Signature-256 header.")
            return False

        parts = signature_header.split("sha256=")
        if len(parts) != 2:
            return False
        expected_hash = parts[1]

        computed_hash = hmac.new(
            key=settings.META_APP_SECRET.encode("utf-8"),
            msg=payload_bytes,
            digestmod=hashlib.sha256
        ).hexdigest()

        is_valid = hmac.compare_digest(computed_hash, expected_hash)
        if not is_valid:
            logger.error("HMAC SHA-256 signature verification failed.")
        return is_valid

    @staticmethod
    def parse_messaging_events(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parses incoming Facebook and Instagram DM events.
        Extracts sender ID, recipient ID, message text, message ID, timestamp, and platform.
        Hardened: non-dict entries/values are skipped, never crash (500-hunter audit).
        """
        events = []
        if not isinstance(payload, dict):
            return events
        obj = payload.get("object")
        platform = PlatformSource.INSTAGRAM if obj == "instagram" else PlatformSource.FACEBOOK

        entries = payload.get("entry")
        for entry in (entries if isinstance(entries, list) else []):
            if not isinstance(entry, dict):
                continue
            messaging = entry.get("messaging")
            for msg_event in (messaging if isinstance(messaging, list) else []):
                if not isinstance(msg_event, dict):
                    continue
                sender = (msg_event.get("sender") or {}).get("id")
                recipient = (msg_event.get("recipient") or {}).get("id")
                message = msg_event.get("message")
                if not isinstance(message, dict):
                    continue
                timestamp = msg_event.get("timestamp")

                if message and sender:
                    events.append({
                        "event_type": "message",
                        "platform": platform,
                        "sender_id": sender,
                        "recipient_id": recipient,
                        "message_id": message.get("mid"),
                        "text": message.get("text", ""),
                        "timestamp": timestamp,
                        "is_echo": message.get("is_echo", False),
                        "raw_event": msg_event
                    })
        return events

    @staticmethod
    def parse_comment_events(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parses incoming Instagram & Facebook post/reel comments and feed changes.
        Hardened: malformed entries/changes/values are skipped, never crash.
        """
        events = []
        if not isinstance(payload, dict):
            return events
        obj = payload.get("object")
        platform = PlatformSource.INSTAGRAM if obj == "instagram" else PlatformSource.FACEBOOK

        entries = payload.get("entry")
        for entry in (entries if isinstance(entries, list) else []):
            if not isinstance(entry, dict):
                continue
            account_id = entry.get("id")
            changes = entry.get("changes")
            for change in (changes if isinstance(changes, list) else []):
                if not isinstance(change, dict):
                    continue
                field = change.get("field")
                val = change.get("value") or {}
                if not isinstance(val, dict):
                    continue

                # Instagram comments
                if field == "comments":
                    comment_id = val.get("id")
                    text = val.get("text", "")
                    media = val.get("media", {})
                    media_id = media.get("id")
                    from_user = val.get("from", {})
                    sender_id = from_user.get("id")
                    username = from_user.get("username", "")

                    if comment_id and sender_id != account_id:
                        events.append({
                            "event_type": "comment",
                            "platform": PlatformSource.INSTAGRAM,
                            "account_id": account_id,
                            "comment_id": comment_id,
                            "media_id": media_id,
                            "sender_id": sender_id,
                            "username": username,
                            "text": text,
                            "raw_change": change
                        })

                # Facebook feed comments/reactions
                elif field == "feed":
                    item = val.get("item")
                    verb = val.get("verb")
                    if item == "comment" and verb == "add":
                        comment_id = val.get("comment_id")
                        post_id = val.get("post_id")
                        text = val.get("message", "")
                        from_user = val.get("from", {})
                        sender_id = from_user.get("id")
                        sender_name = from_user.get("name", "")

                        if comment_id and sender_id != account_id:
                            events.append({
                                "event_type": "comment",
                                "platform": PlatformSource.FACEBOOK,
                                "account_id": account_id,
                                "comment_id": comment_id,
                                "post_id": post_id,
                                "sender_id": sender_id,
                                "sender_name": sender_name,
                                "text": text,
                                "raw_change": change
                            })

                # Facebook Page mentions (threads_manage_mentions / Page mentions):
                # someone tags or mentions the Page in a post/comment. Meta sends
                # the `mentions` field with either a comment_id (mention inside a
                # comment) or a standalone post_id (mention inside a post).
                elif field == "mentions":
                    comment_id = val.get("comment_id")
                    post_id = val.get("post_id")
                    stable_id = comment_id or post_id
                    text = val.get("message", "") or val.get("text", "")
                    from_user = val.get("from", {})
                    sender_id = from_user.get("id")
                    sender_name = (from_user.get("name", "")
                                   or val.get("sender_name", ""))

                    if stable_id and sender_id and sender_id != account_id:
                        events.append({
                            "event_type": "comment",
                            "platform": PlatformSource.FACEBOOK,
                            "account_id": account_id,
                            "comment_id": stable_id,
                            "post_id": post_id,
                            "sender_id": sender_id,
                            "sender_name": sender_name,
                            "text": text,
                            "is_mention": True,
                            "raw_change": change
                        })
        return events



webhook_handler = WebhookHandler()
