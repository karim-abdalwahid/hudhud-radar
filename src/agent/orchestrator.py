"""
Agent Orchestrator.
Coordinates the entire lifecycle: webhook event -> extraction -> identity resolution ->
lead & message storage -> AI response -> outbound dispatch -> activity logging.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from src.core.logger import logger
from src.leads.models import MessageCreate, PlatformSource, SenderType, LeadUpdate
from src.leads.service import lead_service
from src.identity.extractor import ProfileDataExtractor
from src.identity.resolver import identity_resolver
from src.agent.conversation_engine import conversation_engine
from src.meta_api.client import meta_client
from src.core.supabase_client import supabase_db


class AgentOrchestrator:
    """End-to-end orchestrator for Meta messaging and lead capture."""

    def __init__(self):
        self.lead_svc = lead_service
        self.resolver = identity_resolver
        self.engine = conversation_engine
        self.client = meta_client

    async def process_incoming_message_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes full workflow for an inbound message event.
        """
        platform: PlatformSource = event["platform"]
        sender_id: str = event["sender_id"]
        message_id: str = event.get("message_id")
        text: str = event.get("text", "")
        raw_event = event.get("raw_event", {})

        logger.info(f"Processing incoming {platform} message from {sender_id}: mid={message_id}")

        # 1. Zero-Assumption Profile Extraction — enrich with the REAL profile
        # (name + photo) from the Messenger/Instagram Profile API before storing.
        if platform == PlatformSource.FACEBOOK:
            profile_payload = {"id": sender_id}
            try:
                fb_profile = await self.client.get_profile(
                    sender_id, fields="id,first_name,last_name,name,profile_pic"
                )
                if isinstance(fb_profile, dict) and not fb_profile.get("error"):
                    profile_payload.update(fb_profile)
            except Exception as e:
                logger.warning(f"Profile enrichment skipped for Facebook sender {sender_id}: {e}")
            lead_in = ProfileDataExtractor.extract_from_facebook(profile_payload)
        else:
            profile_payload = {"id": sender_id, "username": raw_event.get("sender", {}).get("username")}
            try:
                ig_profile = await self.client.get_profile(
                    sender_id, fields="id,username,name,profile_pic"
                )
                if isinstance(ig_profile, dict) and not ig_profile.get("error"):
                    profile_payload.update(ig_profile)
            except Exception as e:
                logger.warning(f"Profile enrichment skipped for Instagram sender {sender_id}: {e}")
            lead_in = ProfileDataExtractor.extract_from_instagram(profile_payload)

        # 2. Identity Resolution & Linking
        lead_record, is_new, queue_id = self.resolver.resolve_and_save_lead(lead_in)
        lead_id = lead_record["id"]

        # 3. Human Takeover check: never auto-reply when a human is in control
        if lead_record.get("human_takeover"):
            logger.info(f"Human takeover active for lead {lead_id} — skipping AI auto-reply.")
            return {
                "lead_id": lead_id,
                "is_new_lead": is_new,
                "queue_id": queue_id,
                "reply_sent": None,
                "is_converted": False,
                "human_takeover": True,
            }

        # 4. Store Inbound Message linked to lead
        inbound_msg = MessageCreate(
            lead_id=lead_id,
            platform=platform,
            platform_message_id=message_id,
            sender_type=SenderType.LEAD,
            content=text,
            sent_at=datetime.now(timezone.utc)
        )
        self.lead_svc.add_message(inbound_msg)

        # 5. Check for contact details extracted directly from message text
        contact_info = self.engine.extract_contact_info(text)
        updates = {}
        if contact_info["email"] and not lead_record.get("contact_email"):
            updates["contact_email"] = contact_info["email"]
        if contact_info["phone"] and not lead_record.get("contact_phone"):
            updates["contact_phone"] = contact_info["phone"]
        if updates:
            self.lead_svc.update_lead(lead_id, LeadUpdate(**updates))
            lead_record.update(updates)

        # 6. Generate AI Response
        history = self.lead_svc.get_messages_for_lead(lead_id)
        reply_text, is_converted = await self.engine.generate_response(lead_record, text, history)

        # 7. Send Outbound Response adhering to 24-hr window & Rate Limits.
        # Use the real event timestamp when available (accurate 24h-window basis).
        event_ts = event.get("timestamp")
        try:
            last_interaction = (
                datetime.fromtimestamp(int(event_ts) / 1000, tz=timezone.utc)
                if event_ts else datetime.now(timezone.utc)
            )
        except (TypeError, ValueError):
            last_interaction = datetime.now(timezone.utc)

        send_result = {}
        try:
            if platform == PlatformSource.FACEBOOK:
                send_result = await self.client.send_facebook_message(
                    recipient_id=sender_id,
                    message_text=reply_text,
                    last_interaction_time=last_interaction
                )
            else:
                send_result = await self.client.send_instagram_message(
                    recipient_id=sender_id,
                    message_text=reply_text,
                    last_interaction_time=last_interaction
                )

            # 8. Store Outbound Message
            outbound_msg = MessageCreate(
                lead_id=lead_id,
                platform=platform,
                platform_message_id=send_result.get("message_id"),
                sender_type=SenderType.AGENT,
                content=reply_text,
                sent_at=datetime.now(timezone.utc),
                metadata={"is_conversion_reply": is_converted}
            )
            self.lead_svc.add_message(outbound_msg)
        except Exception as e:
            logger.error(f"Failed to dispatch outbound response to {sender_id}: {e}")

        return {
            "lead_id": lead_id,
            "is_new_lead": is_new,
            "queue_id": queue_id,
            "reply_sent": reply_text,
            "is_converted": is_converted
        }


agent_orchestrator = AgentOrchestrator()
