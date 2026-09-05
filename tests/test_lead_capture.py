"""
Unit Tests for Lead Capture, Message Linking, and 24-Hour Policy Window.
"""
import pytest
from datetime import datetime, timezone, timedelta
from src.leads.models import LeadCreate, MessageCreate, PlatformSource, SenderType
from src.leads.service import LeadService
from src.core.supabase_client import InMemoryDatabase
from src.agent.conversation_engine import ConversationEngine
from src.meta_api.client import MetaGraphClient
from src.core.exceptions import MessagingWindowExpiredError


@pytest.fixture
def mock_db():
    return InMemoryDatabase()


def test_lead_and_message_linking(mock_db):
    """Verify that messages table is strictly linked to leads table."""
    lead_svc = LeadService(db=mock_db)

    # 1. Create a lead
    lead_in = LeadCreate(
        source=PlatformSource.FACEBOOK,
        full_name="Khaled Omar",
        facebook_account_id="fb_555"
    )
    lead = lead_svc.create_lead(lead_in)
    lead_id = lead["id"]

    # 2. Add inbound message
    msg1 = MessageCreate(
        lead_id=lead_id,
        platform=PlatformSource.FACEBOOK,
        sender_type=SenderType.LEAD,
        content="السلام عليكم، مهتم بخدماتكم"
    )
    saved_msg1 = lead_svc.add_message(msg1)

    # 3. Add outbound agent response
    msg2 = MessageCreate(
        lead_id=lead_id,
        platform=PlatformSource.FACEBOOK,
        sender_type=SenderType.AGENT,
        content="وعليكم السلام يا خالد، يسعدنا تواصلك!"
    )
    saved_msg2 = lead_svc.add_message(msg2)

    # 4. Verify messages are linked and retrievable
    history = lead_svc.get_messages_for_lead(lead_id)
    assert len(history) == 2
    assert history[0]["lead_id"] == lead_id
    assert history[1]["lead_id"] == lead_id
    assert history[0]["sender_type"] == SenderType.LEAD
    assert history[1]["sender_type"] == SenderType.AGENT


def test_contact_info_extraction_from_conversation():
    """Verify that email and phone provided in DM text are accurately parsed."""
    engine = ConversationEngine()

    msg_with_email = "تفضل إيميلي khaled.omar@example.com للتواصل"
    extracted1 = engine.extract_contact_info(msg_with_email)
    assert extracted1["email"] == "khaled.omar@example.com"

    msg_with_phone = "رقم هاتفي هو +966501234567"
    extracted2 = engine.extract_contact_info(msg_with_phone)
    assert extracted2["phone"] is not None
    assert "966501234567" in extracted2["phone"]


@pytest.mark.asyncio
async def test_24_hour_messaging_window_enforcement():
    """Verify that sending a message outside the 24-hr window is blocked by policy."""
    client = MetaGraphClient()
    expired_interaction = datetime.now(timezone.utc) - timedelta(hours=25)

    with pytest.raises(MessagingWindowExpiredError) as exc_info:
        await client.send_facebook_message(
            recipient_id="user_test_123",
            message_text="رسالة متابعة ترويجية",
            last_interaction_time=expired_interaction
        )

    assert exc_info.value.recipient_id == "user_test_123"
    assert exc_info.value.elapsed_hours >= 25.0
