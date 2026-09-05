"""
Manual Identity Verification Review Queue Manager.
Allows authorized human supervisors to explicitly confirm or reject candidate links.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from src.core.supabase_client import supabase_db
from src.core.logger import logger
from src.leads.models import VerificationMethod


class IdentityReviewQueue:
    """Manages pending candidate matches requiring explicit human review."""

    def __init__(self, db=supabase_db):
        self.db = db

    def get_pending_reviews(self) -> List[Dict[str, Any]]:
        """Retrieve all candidate matches awaiting supervisor review."""
        return self.db.select("identity_verification_queue", {"status": "pending"})

    def approve_match(self, queue_id: str, reviewer_name: str, notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Explicitly confirms that two candidate accounts belong to the same person.
        Updates both lead records with mutual linked_account_id and updates provenance.
        """
        items = self.db.select("identity_verification_queue", {"id": queue_id})
        if not items:
            raise ValueError(f"Queue item {queue_id} not found.")

        item = items[0]
        primary_id = item["primary_lead_id"]
        candidate_id = item["candidate_lead_id"]
        now = datetime.now(timezone.utc).isoformat()

        # Update primary lead
        self.db.update("leads", primary_id, {
            "linked_account_id": candidate_id,
            "is_verified_link": True
        })

        # Update candidate lead
        self.db.update("leads", candidate_id, {
            "linked_account_id": primary_id,
            "is_verified_link": True
        })

        # Update queue status
        updated_queue = self.db.update("identity_verification_queue", queue_id, {
            "status": "approved",
            "reviewed_by": reviewer_name,
            "reviewed_at": now,
            "notes": notes or "Manually verified and confirmed by supervisor"
        })

        logger.info(f"Identity match APPROVED by {reviewer_name}: leads {primary_id} <-> {candidate_id}")
        return updated_queue

    def reject_match(self, queue_id: str, reviewer_name: str, notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Explicitly rejects candidate match. Accounts remain strictly separate.
        """
        items = self.db.select("identity_verification_queue", {"id": queue_id})
        if not items:
            raise ValueError(f"Queue item {queue_id} not found.")

        now = datetime.now(timezone.utc).isoformat()
        updated_queue = self.db.update("identity_verification_queue", queue_id, {
            "status": "rejected",
            "reviewed_by": reviewer_name,
            "reviewed_at": now,
            "notes": notes or "Manually rejected by supervisor - accounts confirmed distinct"
        })

        logger.info(f"Identity match REJECTED by {reviewer_name}: queue_id={queue_id}")
        return updated_queue


identity_review_queue = IdentityReviewQueue()
