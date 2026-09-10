"""
Comment → Lead Bridge (Instagram & Facebook).
Converts comment webhook events into CRM leads and stores the comment as the
first inbound message. Data source = the webhook payload itself + deterministic
identity resolution (zero fabrication: no profile guesses, no invented names).
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from src.core.logger import logger
from src.core.supabase_client import supabase_db
from src.leads.models import LeadCreate, MessageCreate, PlatformSource, SenderType
from src.identity.resolver import identity_resolver
from src.leads.service import lead_service


async def capture_comment_lead(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Captures an Instagram/Facebook comment as (or into) a lead.
    Event shape comes from webhook_handler.parse_comment_events():
      IG: sender_id, username, comment_id, text, media_id
      FB: sender_id, sender_name, comment_id, text, post_id
    """
    platform = event.get("platform")
    account_id = event.get("sender_id")
    comment_id = event.get("comment_id")
    text = event.get("text") or ""

    if not platform or not account_id or not comment_id:
        logger.warning("Comment bridge skipped: missing platform/sender/comment_id.")
        return None

    # Idempotency across re-deliveries/restarts (route-level dedup already ran)
    existing_msg = supabase_db.select("messages", {"platform_message_id": comment_id})
    if existing_msg:
        return {"lead_id": existing_msg[0].get("lead_id"), "duplicate": True}

    if platform == PlatformSource.INSTAGRAM:
        username = event.get("username")
        lead_in = LeadCreate(
            source=PlatformSource.INSTAGRAM,
            username=username,
            profile_url=f"https://www.instagram.com/{username}/" if username else None,
            instagram_account_id=account_id,
        )
    elif platform == PlatformSource.FACEBOOK:
        lead_in = LeadCreate(
            source=PlatformSource.FACEBOOK,
            full_name=event.get("sender_name"),
            facebook_account_id=account_id,
        )
    else:
        return None

    lead_record, is_new, queue_id = identity_resolver.resolve_and_save_lead(lead_in)
    lead_id = lead_record["id"]

    message = MessageCreate(
        lead_id=lead_id,
        platform=platform,
        platform_message_id=comment_id,
        sender_type=SenderType.LEAD,
        content=text,
        sent_at=datetime.now(timezone.utc),
        metadata={"type": "comment", "media_id": event.get("media_id") or event.get("post_id")},
    )
    lead_service.add_message(message)

    logger.info(
        f"Comment captured as lead: {platform.value} comment {comment_id} → "
        f"lead {lead_id} (new={is_new}, queue_id={queue_id})"
    )
    return {"lead_id": lead_id, "is_new": is_new, "queue_id": queue_id}
