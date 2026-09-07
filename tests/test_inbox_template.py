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
    assert dom.index("renderEmptyChat()") < dom.index("fetchLiveConversations()")
