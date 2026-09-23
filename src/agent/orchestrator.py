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
        recipient_id = event.get("recipient_id")

        # In Meta webhooks the sender is the *end customer*. The recipient is
        # the business account, and therefore the only trustworthy tenant key.
        # Never accept or answer an event that cannot be mapped to one active
        # connected account; guessing here could expose another client's KB.
        from src.modules.connections.service import connection_service
        owner_user_id = connection_service.owner_for_account(platform.value, recipient_id)
        if not owner_user_id:
            logger.error(
                "Webhook ignored: no unique active owner for %s recipient %s",
                platform.value, recipient_id or "<missing>",
            )
            return {
                "reply_sent": None,
                "is_converted": False,
                "ignored": True,
                "reason": "unmapped_recipient_account",
            }

        page_token = connection_service.get_active_token_for_account(
            owner_user_id, platform.value, recipient_id
        )
        if not page_token:
            logger.warning(
                "Webhook ignored: no entitled token for owner %s recipient %s",
                owner_user_id, recipient_id or "<missing>",
            )
            return {
                "reply_sent": None,
                "is_converted": False,
                "ignored": True,
                "reason": "no_entitled_account_token",
            }

        logger.info(f"Processing incoming {platform} message from {sender_id}: mid={message_id}")

        # 1. Zero-Assumption Profile Extraction — enrich with the REAL profile
        # (name + photo) from the Messenger/Instagram Profile API before storing.
        if platform == PlatformSource.FACEBOOK:
            profile_payload = {"id": sender_id}
            try:
                fb_profile = await self.client.get_profile(
                    sender_id,
                    fields="id,first_name,last_name,name,profile_pic",
                    access_token=page_token,
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
                    sender_id,
                    fields="id,username,name,profile_pic",
                    access_token=page_token,
                )
                if isinstance(ig_profile, dict) and not ig_profile.get("error"):
                    profile_payload.update(ig_profile)
            except Exception as e:
                logger.warning(f"Profile enrichment skipped for Instagram sender {sender_id}: {e}")
            lead_in = ProfileDataExtractor.extract_from_instagram(profile_payload)

        provenance = lead_in.data_provenance.model_copy(
            update={"source_account_id": str(recipient_id or "")}
        )
        lead_in = lead_in.model_copy(update={
            "user_id": owner_user_id,
            "data_provenance": provenance,
        })

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
            user_id=owner_user_id,
            platform=platform,
            platform_message_id=message_id,
            sender_type=SenderType.LEAD,
            content=text,
            sent_at=datetime.now(timezone.utc)
        )
        self.lead_svc.add_message(inbound_msg)

        # 4b. Global AI pause (Wave 9.8): the user manages personally — the
        # inbound message is STILL stored (human replies from the inbox),
        # but the AI never generates a reply anywhere.
        try:
            from src.ai.pause import is_ai_paused
            if is_ai_paused(lead_record.get("user_id")):
                logger.info(f"AI paused for lead {lead_id} owner — inbound stored, no auto-reply.")
                return {
                    "lead_id": lead_id,
                    "is_new_lead": is_new,
                    "queue_id": queue_id,
                    "reply_sent": None,
                    "is_converted": False,
                    "ai_paused": True,
                }
        except Exception as e:
            logger.warning(f"AI pause check skipped (non-blocking): {e}")

        # 4c. Credit gate (money brain): fails CLOSED, unlike the AI-pause
        # check above — usage_service.has_credits() never raises (it catches
        # its own lookup errors and returns False), so a billing-check outage
        # can never silently grant unlimited free AI usage the way an outer
        # "except: proceed anyway" wrapper would. Out-of-credit tenants keep
        # receiving messages for manual reply, exactly like AI-pause: only
        # generation stops, nothing is dropped.
        from src.modules.billing.usage import usage_service, KIND_AI_REPLY
        if not usage_service.has_credits(owner_user_id):
            logger.info(f"Out of AI credits for owner {owner_user_id} — inbound stored, no auto-reply.")
            usage_service.notify_if_exhausted(owner_user_id)
            return {
                "lead_id": lead_id,
                "is_new_lead": is_new,
                "queue_id": queue_id,
                "reply_sent": None,
                "is_converted": False,
                "credits_exhausted": True,
            }

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
        history = self.lead_svc.get_messages_for_lead(lead_id, user_id=owner_user_id)
        reply_text, is_converted, used_ai = await self.engine.generate_response(lead_record, text, history)

        # 6b. Bill the credit — only for a reply an actual Gemini call
        # produced. The canned conversion acknowledgement and the offline
        # heuristic fallback are free, by policy (see conversation_engine's
        # generate_response docstring).
        if used_ai:
            usage_service.record_usage(
                owner_user_id, KIND_AI_REPLY,
                meta={"lead_id": lead_id, "platform": platform.value},
            )

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
                    last_interaction_time=last_interaction,
                    access_token=page_token,
                    user_id=owner_user_id,
                )
            else:
                send_result = await self.client.send_instagram_message(
                    recipient_id=sender_id,
                    message_text=reply_text,
                    last_interaction_time=last_interaction,
                    access_token=page_token,
                    user_id=owner_user_id,
                )

            # 8. Store Outbound Message
            outbound_msg = MessageCreate(
                lead_id=lead_id,
                user_id=owner_user_id,
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
