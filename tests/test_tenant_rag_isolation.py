"""Regression tests for tenant-safe inbound AI replies and RAG retrieval."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agent.conversation_engine import ConversationEngine
from src.knowledge.db_knowledge_base import DBKnowledgeBase


def test_db_rag_refuses_missing_tenant_id():
    """No user_id must never degrade to a cross-tenant database search."""
    kb = DBKnowledgeBase()
    assert kb.search("price list", user_id=None) == []


@pytest.mark.asyncio
async def test_conversation_uses_only_the_lead_owner_context():
    calls = []

    class TenantKB:
        def search_relevant_chunks(self, query, top_k=3, user_id=None):
            calls.append(("search", user_id))
            return "TENANT A PRODUCT FACTS"

        def get_sales_closing_context(self, user_id=None):
            calls.append(("sales", user_id))
            return "TENANT A SALES SCRIPT"

    engine = ConversationEngine(kb=TenantKB())
    reply, converted = await engine.generate_response(
        {"user_id": "tenant-a", "full_name": "Customer"}, "what services do you offer?", []
    )
    assert converted is False
    assert "TENANT A SALES SCRIPT" in reply
    assert calls == [("sales", "tenant-a")]


@pytest.mark.asyncio
async def test_orchestrator_stamps_owner_and_ignores_unknown_recipient(monkeypatch):
    from src.agent.orchestrator import AgentOrchestrator
    from src.leads.models import PlatformSource

    orch = AgentOrchestrator()
    monkeypatch.setattr(orch.client, "get_profile", AsyncMock(return_value={"id": "psid-1"}))
    monkeypatch.setattr(
        "src.modules.connections.service.connection_service.owner_for_account",
        lambda *_: "tenant-a",
    )
    resolve = MagicMock(return_value=({"id": "lead-1", "human_takeover": True, "user_id": "tenant-a"}, True, None))
    monkeypatch.setattr(orch.resolver, "resolve_and_save_lead", resolve)

    result = await orch.process_incoming_message_event({
        "platform": PlatformSource.FACEBOOK, "sender_id": "psid-1",
        "recipient_id": "page-a", "message_id": "mid-1", "text": "hello", "raw_event": {},
    })
    assert result["human_takeover"] is True
    assert resolve.call_args.args[0].user_id == "tenant-a"

    monkeypatch.setattr(
        "src.modules.connections.service.connection_service.owner_for_account",
        lambda *_: None,
    )
    ignored = await orch.process_incoming_message_event({
        "platform": PlatformSource.FACEBOOK, "sender_id": "psid-2",
        "recipient_id": "unknown-page", "message_id": "mid-2", "text": "hello", "raw_event": {},
    })
    assert ignored["reason"] == "unmapped_recipient_account"
