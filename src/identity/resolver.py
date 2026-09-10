"""
Identity Resolution Engine with Zero-Assumption and Confidence-Based Match Rules.
Prevents silent merging and enforces human-in-the-loop review for uncertain identities.
"""
from typing import Optional, Dict, Any, Tuple
from src.core.supabase_client import supabase_db
from src.core.logger import logger
from src.config import settings
from src.leads.models import LeadCreate, LeadUpdate, PlatformSource, DataProvenance, VerificationMethod


class IdentityResolver:
    """
    Resolves customer identities across Facebook and Instagram.
    Enforces strict data provenance and queues ambiguous matches for manual human verification.
    """

    def __init__(self, db=supabase_db):
        self.db = db

    def resolve_and_save_lead(self, incoming: LeadCreate) -> Tuple[Dict[str, Any], bool, Optional[str]]:
        """
        Processes an incoming lead:
        1. Checks for existing deterministic record.
        2. Checks for potential cross-platform links.
        3. Either links with 100% confidence, creates new lead, or flags candidate for manual review.
        Returns: (lead_record, is_new_record, optional_queue_id)
        """
        # 1. Deterministic Search: Check by specific platform account ID
        existing_lead = None
        if incoming.source == PlatformSource.FACEBOOK and incoming.facebook_account_id:
            matches = self.db.select("leads", {"facebook_account_id": incoming.facebook_account_id})
            if matches:
                existing_lead = matches[0]
        elif incoming.source == PlatformSource.INSTAGRAM and incoming.instagram_account_id:
            matches = self.db.select("leads", {"instagram_account_id": incoming.instagram_account_id})
            if matches:
                existing_lead = matches[0]
        elif incoming.source == PlatformSource.THREADS and incoming.threads_account_id:
            matches = self.db.select("leads", {"threads_account_id": incoming.threads_account_id})
            if matches:
                existing_lead = matches[0]

        if existing_lead:
            # Deterministic existing lead found. Update any newly available verified info.
            updated = self._update_existing_lead_fields(existing_lead["id"], incoming)
            logger.info(f"Identity resolved (Deterministic): Matched existing lead {existing_lead['id']}")
            return updated, False, None

        # 2. Check for cross-platform candidate matches
        candidate, score, reason = self._find_potential_candidate(incoming)

        # 3. Decision Matrix:
        # Case A: Official deterministic cross-link (Score >= 0.95, e.g. officially linked API accounts)
        if candidate and score >= settings.CONFIDENCE_THRESHOLD_AUTO_LINK:
            created = self.db.insert("leads", incoming.model_dump(mode="json"))
            # Auto-link both records
            self.db.update("leads", created["id"], {
                "linked_account_id": candidate["id"],
                "is_verified_link": True
            })
            self.db.update("leads", candidate["id"], {
                "linked_account_id": created["id"],
                "is_verified_link": True
            })
            logger.info(f"Deterministic cross-platform link established between {created['id']} and {candidate['id']} ({reason})")
            return created, True, None

        # Case B: Ambiguous / Probabilistic match (Score >= 0.50): Flag for Manual Human Review
        if candidate and score >= settings.CONFIDENCE_THRESHOLD_QUEUE_REVIEW:
            created = self.db.insert("leads", incoming.model_dump(mode="json"))
            queue_item = self._add_to_verification_queue(
                primary_lead_id=candidate["id"],
                candidate_lead_id=created["id"],
                match_reason=reason,
                confidence_score=score
            )
            logger.warning(
                f"Ambiguous identity detected (Score: {score:.2f}, Reason: {reason}). "
                f"Enqueued for manual human confirmation: queue_id={queue_item.get('id')}"
            )
            return created, True, queue_item.get("id")

        # Case C: Completely distinct or low similarity -> create clean independent lead
        created = self.db.insert("leads", incoming.model_dump(mode="json"))
        logger.info(f"Created distinct independent lead: id={created['id']}")
        return created, True, None

    def _find_potential_candidate(self, incoming: LeadCreate) -> Tuple[Optional[Dict[str, Any]], float, str]:
        """
        Scans ALL leads, evaluates every possible match signal per lead, and
        returns the HIGHEST-confidence candidate (not the first found).
        """
        all_leads = self.db.select("leads")

        best_lead: Optional[Dict[str, Any]] = None
        best_score = 0.0
        best_reason = "No candidate match found"

        for lead in all_leads:
            score = 0.0
            reason = None

            # Signal 1: Official cross-link specified directly in payload (strongest)
            if (incoming.source == PlatformSource.FACEBOOK and incoming.instagram_account_id
                    and lead.get("instagram_account_id") == incoming.instagram_account_id):
                score, reason = 1.00, "Official API-linked Instagram account detected in Facebook profile"
            elif (incoming.source == PlatformSource.INSTAGRAM and incoming.facebook_account_id
                    and lead.get("facebook_account_id") == incoming.facebook_account_id):
                score, reason = 1.00, "Official API-linked Facebook page detected in Instagram profile"
            # Signal 2: Exact email match
            elif (incoming.contact_email and lead.get("contact_email")
                    and lead["contact_email"].lower() == incoming.contact_email.lower()):
                score, reason = 0.90, f"Exact email match ({incoming.contact_email})"
            # Signal 3: Exact phone match
            elif (incoming.contact_phone and lead.get("contact_phone")
                    and lead["contact_phone"] == incoming.contact_phone):
                score, reason = 0.88, f"Exact phone number match ({incoming.contact_phone})"
            # Signal 4: Identical username across platforms
            elif (incoming.username and lead.get("username")
                    and lead["username"].lower() == incoming.username.lower()):
                score, reason = 0.70, f"Identical username match (@{incoming.username})"
            # Signal 5: Identical full name + same location
            elif (incoming.full_name and incoming.location and lead.get("full_name") and lead.get("location")
                    and lead["full_name"].lower() == incoming.full_name.lower()
                    and lead["location"].lower() == incoming.location.lower()):
                score, reason = 0.55, f"Same full name and location match ({incoming.full_name} in {incoming.location})"

            if score > best_score:
                best_lead, best_score, best_reason = lead, score, reason

        return best_lead, best_score, best_reason

    def _add_to_verification_queue(self, primary_lead_id: str, candidate_lead_id: str, match_reason: str, confidence_score: float) -> Dict[str, Any]:
        """Inserts candidate pair into the verification queue table for human approval."""
        return self.db.insert("identity_verification_queue", {
            "primary_lead_id": primary_lead_id,
            "candidate_lead_id": candidate_lead_id,
            "match_reason": match_reason,
            "confidence_score": round(confidence_score, 2),
            "status": "pending"
        })

    def _update_existing_lead_fields(self, lead_id: str, incoming: LeadCreate) -> Dict[str, Any]:
        """Enriches existing lead record with newly surfaced non-null fields."""
        existing = self.db.select("leads", {"id": lead_id})[0]
        updates = {}
        for field in ["full_name", "username", "avatar_url", "profile_url", "bio", "location", "contact_email", "contact_phone", "facebook_account_id", "instagram_account_id", "threads_account_id"]:
            new_val = getattr(incoming, field, None)
            if new_val and not existing.get(field):
                updates[field] = new_val

        if updates:
            self.db.update("leads", lead_id, updates)
            existing.update(updates)
        return existing


identity_resolver = IdentityResolver()
