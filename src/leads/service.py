"""
Service layer for Leads and Messages.
Handles persistence, linking, and provenance updates.
"""
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timezone
from src.core.supabase_client import supabase_db
from src.core.logger import logger
from src.leads.models import LeadCreate, LeadUpdate, LeadInDB, MessageCreate, MessageInDB, PlatformSource


class LeadService:
    """Encapsulates business operations on leads and their linked messages."""

    def __init__(self, db=supabase_db):
        self.db = db

    def get_lead_by_id(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single lead by its UUID."""
        results = self.db.select("leads", {"id": lead_id})
        return results[0] if results else None

    def find_lead_by_platform_id(self, platform: PlatformSource, account_id: str) -> Optional[Dict[str, Any]]:
        """Locate an existing lead by Facebook ID or Instagram ID."""
        if not account_id:
            return None
        if platform == PlatformSource.FACEBOOK:
            results = self.db.select("leads", {"facebook_account_id": account_id})
        elif platform == PlatformSource.INSTAGRAM:
            results = self.db.select("leads", {"instagram_account_id": account_id})
        else:
            return None
        return results[0] if results else None

    def find_lead_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Locate an existing lead by exact username."""
        if not username:
            return None
        results = self.db.select("leads", {"username": username})
        return results[0] if results else None

    def create_lead(self, lead_in: LeadCreate) -> Dict[str, Any]:
        """Create a new lead with zero assumptions and valid provenance."""
        data = lead_in.model_dump(mode="json")
        inserted = self.db.insert("leads", data)
        logger.info(f"Created new lead: id={inserted.get('id')} source={lead_in.source}")
        return inserted

    def update_lead(self, lead_id: str, lead_update: Union[LeadUpdate, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Update existing lead fields (accepts LeadUpdate model OR raw dict)."""
        if hasattr(lead_update, "model_dump"):
            update_data = {k: v for k, v in lead_update.model_dump(mode="json").items() if v is not None}
        else:
            update_data = {k: v for k, v in dict(lead_update).items() if v is not None}
        if not update_data:
            return self.get_lead_by_id(lead_id)
        updated = self.db.update("leads", lead_id, update_data)
        logger.info(f"Updated lead: id={lead_id}")
        return updated

    def link_accounts(self, lead_id: str, linked_lead_id: str, is_verified: bool = True) -> Optional[Dict[str, Any]]:
        """Link two distinct lead records as representing the same verified person."""
        return self.db.update("leads", lead_id, {
            "linked_account_id": linked_lead_id,
            "is_verified_link": is_verified
        })

    def add_message(self, message_in: MessageCreate) -> Dict[str, Any]:
        """Store a conversation message linked strictly to a lead."""
        data = message_in.model_dump(mode="json")
        inserted = self.db.insert("messages", data)
        logger.info(f"Stored message: id={inserted.get('id')} lead_id={message_in.lead_id} sender={message_in.sender_type}")
        return inserted

    def get_messages_for_lead(self, lead_id: str) -> List[Dict[str, Any]]:
        """Fetch all messages exchanged with a specific lead in chronological order."""
        messages = self.db.select("messages", {"lead_id": lead_id})
        return sorted(messages, key=lambda m: m.get("sent_at", ""))

    def get_all_leads(self, limit: int = 100, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List leads — scoped to the requesting user when user_id provided
        (Phase 9.5 per-user isolation)."""
        if user_id:
            leads = self.db.select("leads", {"user_id": user_id})
        else:
            leads = self.db.select("leads")
        return leads[:limit]


lead_service = LeadService()
