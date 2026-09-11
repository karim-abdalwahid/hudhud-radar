"""Tests: Facebook Page mentions -> parsed events -> CRM leads (threads_manage_mentions / Page mentions)."""
import pytest
from unittest.mock import MagicMock, patch

from src.core.supabase_client import InMemoryDatabase
from src.identity.resolver import IdentityResolver
from src.meta_api.webhooks import webhook_handler
from src.leads.comment_bridge import capture_comment_lead
from src.leads.models import PlatformSource


@pytest.fixture
def bridged_db(monkeypatch):
    db = InMemoryDatabase()
    import src.leads.comment_bridge as bridge_mod
    import src.leads.service as leads_service_mod
    monkeypatch.setattr(bridge_mod, "supabase_db", db)
    monkeypatch.setattr(bridge_mod, "identity_resolver", IdentityResolver(db=db))
    monkeypatch.setattr(leads_service_mod.lead_service, "db", db)
    return db


def test_mentions_field_mention_inside_comment():
    """Someone mentions the Page inside a comment -> one parsed event."""
    payload = {
        "object": "page",
        "entry": [{
            "id": "page_1",
            "time": 1700000000000,
            "changes": [{
                "field": "mentions",
                "value": {
                    "item": "comment",
                    "comment_id": "mention_cmt_1",
                    "post_id": "post_9",
                    "message": "check out @PageName best deals!",
                    "from": {"id": "fan_42", "name": "Rania Kamal"},
                },
            }],
        }],
    }
    events = webhook_handler.parse_comment_events(payload)
    assert len(events) == 1
    ev = events[0]
    assert ev["comment_id"] == "mention_cmt_1"
    assert ev["sender_id"] == "fan_42"
    assert ev["sender_name"] == "Rania Kamal"
    assert ev["is_mention"] is True
    assert ev["platform"] == PlatformSource.FACEBOOK


def test_mentions_field_mention_inside_post():
    """Someone tags the Page in a standalone post -> one event keyed by post_id."""
    payload = {
        "object": "page",
        "entry": [{
            "id": "page_1",
            "changes": [{
                "field": "mentions",
                "value": {
                    "item": "post",
                    "post_id": "tagged_post_7",
                    "message": "thanks @PageName!",
                    "from": {"id": "fan_77", "name": "Omar Adel"},
                },
            }],
        }],
    }
    events = webhook_handler.parse_comment_events(payload)
    assert len(events) == 1
    assert events[0]["comment_id"] == "tagged_post_7"
    assert events[0]["is_mention"] is True


def test_mentions_self_skipped():
    """The Page mentioning itself must not create a lead."""
    payload = {
        "object": "page",
        "entry": [{
            "id": "page_1",
            "changes": [{
                "field": "mentions",
                "value": {
                    "post_id": "own_post",
                    "message": "welcome!",
                    "from": {"id": "page_1", "name": "My Page"},
                },
            }],
        }],
    }
    assert webhook_handler.parse_comment_events(payload) == []


def test_mentions_without_identity_skipped():
    payload = {
        "object": "page",
        "entry": [{
            "id": "page_1",
            "changes": [{"field": "mentions", "value": {"message": "hi"}}],
        }],
    }
    assert webhook_handler.parse_comment_events(payload) == []


@pytest.mark.asyncio
async def test_mention_flows_into_crm_with_mention_metadata(bridged_db):
    event = {
        "platform": PlatformSource.FACEBOOK,
        "account_id": "page_1",
        "comment_id": "mention_cmt_2",
        "post_id": "post_3",
        "sender_id": "fan_99",
        "sender_name": "Nour Hana",
        "text": "loved @PageName service!",
        "is_mention": True,
    }
    result = await capture_comment_lead(event)
    assert result is not None
    leads = bridged_db.select("leads", {"facebook_account_id": "fan_99"})
    assert len(leads) == 1
    assert leads[0]["full_name"] == "Nour Hana"
    msgs = bridged_db.select("messages", {"lead_id": leads[0]["id"]})
    assert len(msgs) == 1
    assert msgs[0]["metadata"]["type"] == "mention"


def test_regular_comments_not_marked_mention():
    payload = {
        "object": "page",
        "entry": [{
            "id": "page_1",
            "changes": [{
                "field": "feed",
                "value": {"item": "comment", "verb": "add", "comment_id": "c1",
                          "post_id": "p1", "message": "nice",
                          "from": {"id": "fan_1", "name": "A"}},
            }],
        }],
    }
    events = webhook_handler.parse_comment_events(payload)
    assert len(events) == 1
    assert "is_mention" not in events[0]
