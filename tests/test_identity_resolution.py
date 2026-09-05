"""
Unit Tests for Zero-Assumption Extraction and Identity Resolution.
Verifies deterministic linking, ambiguous queuing, and zero data fabrication.
"""
import pytest
from src.identity.extractor import ProfileDataExtractor
from src.identity.resolver import IdentityResolver
from src.identity.review_queue import IdentityReviewQueue
from src.core.supabase_client import InMemoryDatabase
from src.leads.models import PlatformSource, LeadCreate


@pytest.fixture
def mock_db():
    return InMemoryDatabase()


def test_zero_assumption_extractor_no_fabrication():
    """Verify that missing fields in raw payload remain None and are never fabricated."""
    raw_fb = {"id": "fb_12345", "name": "Ahmed Salem"}
    lead = ProfileDataExtractor.extract_from_facebook(raw_fb)

    assert lead.full_name == "Ahmed Salem"
    assert lead.facebook_account_id == "fb_12345"
    assert lead.contact_email is None
    assert lead.contact_phone is None
    assert lead.bio is None
    assert lead.location is None
    assert lead.instagram_account_id is None
    assert lead.data_provenance.source_platform == PlatformSource.FACEBOOK


def test_deterministic_official_linking(mock_db):
    """Verify that officially linked accounts (100% confidence) are auto-linked."""
    resolver = IdentityResolver(db=mock_db)

    # 1. Existing Instagram lead
    ig_lead = LeadCreate(
        source=PlatformSource.INSTAGRAM,
        username="ahmed_official",
        full_name="Ahmed Salem",
        instagram_account_id="ig_999"
    )
    ig_record, is_new, _ = resolver.resolve_and_save_lead(ig_lead)
    assert is_new is True

    # 2. Incoming Facebook lead that officially contains the same linked Instagram ID in payload
    fb_lead = LeadCreate(
        source=PlatformSource.FACEBOOK,
        full_name="Ahmed Salem",
        facebook_account_id="fb_888",
        instagram_account_id="ig_999"  # Officially declared link
    )
    fb_record, is_new_fb, queue_id = resolver.resolve_and_save_lead(fb_lead)

    assert is_new_fb is True
    assert queue_id is None  # Deterministic! No manual queue needed
    assert fb_record["linked_account_id"] == ig_record["id"]
    assert fb_record["is_verified_link"] is True

    # Verify reciprocal link on the original lead
    updated_ig = mock_db.select("leads", {"id": ig_record["id"]})[0]
    assert updated_ig["linked_account_id"] == fb_record["id"]
    assert updated_ig["is_verified_link"] is True


def test_ambiguous_identity_queued_for_manual_review_never_auto_merged(mock_db):
    """
    Verify that when an ambiguous match occurs (e.g. same username on another platform),
    the system DOES NOT auto-merge, but flags it for manual supervisor review.
    """
    resolver = IdentityResolver(db=mock_db)
    queue = IdentityReviewQueue(db=mock_db)

    # 1. Primary lead on Facebook
    lead1 = LeadCreate(
        source=PlatformSource.FACEBOOK,
        full_name="Tariq Mansour",
        username="tariq_m",
        facebook_account_id="fb_111"
    )
    rec1, _, _ = resolver.resolve_and_save_lead(lead1)

    # 2. Candidate lead on Instagram with identical username, but NO official API link
    lead2 = LeadCreate(
        source=PlatformSource.INSTAGRAM,
        full_name="Tariq M.",
        username="tariq_m",
        instagram_account_id="ig_222"
    )
    rec2, _, queue_id = resolver.resolve_and_save_lead(lead2)

    # Must be enqueued for manual human confirmation!
    assert queue_id is not None
    assert rec2["linked_account_id"] is None  # NOT merged!
    assert rec2["is_verified_link"] is False

    pending = queue.get_pending_reviews()
    assert len(pending) == 1
    assert pending[0]["id"] == queue_id
    assert pending[0]["primary_lead_id"] == rec1["id"]
    assert pending[0]["candidate_lead_id"] == rec2["id"]
    assert pending[0]["confidence_score"] == 0.70

    # 3. Supervisor manually confirms and approves the link
    approved = queue.approve_match(queue_id, reviewer_name="Supervisor_Sarah")
    assert approved["status"] == "approved"
    assert approved["reviewed_by"] == "Supervisor_Sarah"

    # Now both records are safely linked
    lead1_post = mock_db.select("leads", {"id": rec1["id"]})[0]
    lead2_post = mock_db.select("leads", {"id": rec2["id"]})[0]
    assert lead1_post["linked_account_id"] == rec2["id"]
    assert lead2_post["linked_account_id"] == rec1["id"]
    assert lead1_post["is_verified_link"] is True
