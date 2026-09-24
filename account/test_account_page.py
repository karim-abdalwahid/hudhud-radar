"""Regression tests for the customer account page and role separation.

These lock in the three defects the page was created to fix:
  1. OAuth callbacks landed non-admin customers on an admin-only page (403).
  2. Pause-AI / change-password / disconnect existed as APIs with no reachable UI.
  3. /analytics served per-user data but was gated as admin-only.
"""
import re
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"


# ---------------------------------------------------------------------------
# 1. OAuth callbacks must land somewhere a customer is allowed to open
# ---------------------------------------------------------------------------
def test_oauth_callbacks_never_redirect_to_an_admin_only_page():
    from src.core.auth import ADMIN_PAGE_PATHS

    offenders = []
    for name in ("connections/routes.py", "threads_marketing/routes.py"):
        text = (SRC / "modules" / name).read_text(encoding="utf-8")
        for target in re.findall(r'RedirectResponse\(\s*url=["\']([^"\']+)|RedirectResponse\(\s*["\'](/[^"\']+)', text):
            url = (target[0] or target[1]).split("?")[0]
            if url in ADMIN_PAGE_PATHS:
                offenders.append(f"{name} -> {url}")
    assert not offenders, f"customer OAuth flow redirects into an admin page: {offenders}"


def test_connect_callbacks_point_at_the_account_page():
    text = (SRC / "modules" / "connections" / "routes.py").read_text(encoding="utf-8")
    assert '"/account?connected=facebook"' in text
    assert '"/account?connected=instagram"' in text


# ---------------------------------------------------------------------------
# 2. The account page exists, is customer-accessible, and wires the real APIs
# ---------------------------------------------------------------------------
def test_account_page_is_registered_for_any_authenticated_user():
    import src.modules.account_page  # noqa: F401  (registers on import)
    from src.core.auth import is_admin_page, is_public_path

    assert not is_admin_page("/account"), "/account must not be admin-gated"
    assert not is_public_path("/account"), "/account must still require a session"


def test_account_page_exposes_every_self_service_action():
    from src.modules.account_page import _ACCOUNT_HTML

    for endpoint in (
        "/api/ai/pause",            # pause my own agent
        "/auth/change-password",    # rotate my own password
        "/api/connections",         # list my channels
        "/api/threads/disconnect",  # drop Threads
        "/api/billing/subscription",
    ):
        assert endpoint in _ACCOUNT_HTML, f"account page never calls {endpoint}"

    # The DELETE call is built dynamically, so assert on the method + path base.
    assert "'/api/connections/' + encodeURIComponent(platform)" in _ACCOUNT_HTML
    assert "method: 'DELETE'" in _ACCOUNT_HTML


def test_account_page_uses_no_undefined_i18n_keys():
    """hudhudI18n.t() returns the raw key when missing, printing e.g.
    'acct.title' on screen. Only keys that exist in i18n.js may be used."""
    from src.modules.account_page import _ACCOUNT_HTML

    i18n = (SRC / "templates" / "static" / "i18n.js").read_text(encoding="utf-8")
    used = set(re.findall(r'data-i18n="([^"]+)"', _ACCOUNT_HTML))
    missing = sorted(k for k in used if f'"{k}"' not in i18n)
    assert not missing, f"account page references i18n keys that do not exist: {missing}"


def test_account_nav_entry_is_visible_to_customers():
    import src.modules.account_page  # noqa: F401
    from src.core.modules import module_registry, SIDEBAR_SECTIONS

    hrefs = [n.href for n in module_registry.sorted_nav(is_admin=False)]
    assert "/account" in hrefs, "customers cannot see the account page in the sidebar"

    sections = {n.section for n in module_registry.sorted_nav(is_admin=False)}
    assert sections <= set(SIDEBAR_SECTIONS), \
        "a nav entry uses a section with no SIDEBAR_SECTIONS title"


# ---------------------------------------------------------------------------
# 3. Analytics is per-user data, so customers must reach it
# ---------------------------------------------------------------------------
def test_analytics_is_available_to_customers():
    import src.modules.pages  # noqa: F401
    from src.core.auth import is_admin_page
    from src.core.modules import module_registry

    assert not is_admin_page("/analytics")
    hrefs = [n.href for n in module_registry.sorted_nav(is_admin=False)]
    assert "/analytics" in hrefs


def test_operator_tooling_stays_admin_only():
    from src.core.auth import is_admin_page

    for path in ("/settings", "/identity"):
        assert is_admin_page(path), f"{path} must remain operator-only"


# ---------------------------------------------------------------------------
# 4. One free trial per account
# ---------------------------------------------------------------------------
def test_trial_cannot_be_restarted(monkeypatch):
    from src.modules.billing.services import entitlement_service

    for sub in ({"trial_ends_at": "2026-01-01T00:00:00+00:00", "status": "canceled"},
                {"status": "trialing"},
                {"status": "active"}):
        monkeypatch.setattr(entitlement_service, "get_subscription", lambda _u, s=sub: s)
        assert entitlement_service.has_used_trial("u1") is True
        assert entitlement_service.start_trial("u1") is False, \
            "an account that already consumed a trial must not get another"


def test_first_trial_is_allowed(monkeypatch):
    from src.modules.billing.services import entitlement_service

    monkeypatch.setattr(entitlement_service, "get_subscription", lambda _u: None)
    assert entitlement_service.has_used_trial("fresh-user") is False


def test_trial_endpoint_refuses_a_second_trial():
    text = (SRC / "modules" / "billing" / "__init__.py").read_text(encoding="utf-8")
    route = text.split('@app.post("/api/billing/trial"')[1].split("@app.")[0]
    assert "has_used_trial" in route, "the trial endpoint does not check prior trial use"
    assert "409" in route
