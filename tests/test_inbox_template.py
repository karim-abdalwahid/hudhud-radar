"""
Inbox template zero-fabrication regression: the page must never ship
hardcoded demo conversations/persons that flash before real data loads.
"""
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1] / "src" / "templates" / "inbox.html"


def test_inbox_template_has_no_demo_personas():
    src = TEMPLATE.read_text(encoding="utf-8")
    assert "Alex Johnson" not in src
    assert "alex_agency" not in src
    assert "Hot Lead (94% Intent)" not in src
    assert "annual agency growth tier" not in src


def test_inbox_template_has_no_fake_response_times():
    src = TEMPLATE.read_text(encoding="utf-8")
    assert "3.2s" not in src
    assert "responseTime" not in src


def test_inbox_empty_state_shown_immediately():
    src = TEMPLATE.read_text(encoding="utf-8")
    # renderEmptyChat must be called on DOMContentLoaded BEFORE the fetch,
    # so users never see a blank/fabricated panel during load.
    dom = src[src.index("DOMContentLoaded"):]
    assert dom.index("renderEmptyChat()") < dom.index("fetchLiveConversations(false)")


def test_inbox_polls_for_new_messages_every_5s():
    """AUDIT-2026-09-15 Fix: the inbox was fetch-once — a message arriving
    30s after load never appeared until a full page reload. Now a silent
    5-second poll re-renders only when the conversation signature changes."""
    src = TEMPLATE.read_text(encoding="utf-8")
    assert "fetchLiveConversations(true), 5000" in src
    assert "conversationSignature" in src


def test_inbox_sorts_threads_by_last_message():
    """AUDIT-2026-09-15 Fix: newest activity must rise to the top — both on
    the server (get_inbox_conversations sort) and in the client render."""
    src = TEMPLATE.read_text(encoding="utf-8")
    assert ".sort(" in src
    assert "localeCompare" in src
