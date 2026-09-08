"""
WS0.4 — Registry-driven sidebar navigation tests.
The sidebar is rendered server-side from the module registry: role-aware,
active-aware, drift-impossible. Legacy client-side injection removed.
"""
import re
from starlette.testclient import TestClient

import src.modules.pages  # noqa: F401 — registers nav entries


def _nav_of(client: TestClient, path: str) -> str:
    r = client.get(path)
    m = re.search(r'<nav class="sidebar-nav">(.*?)</nav>', r.text, re.S)
    assert m, f"no sidebar nav rendered on {path}"
    return m.group(1)


def test_admin_sees_all_nav_with_active_state(client: TestClient):
    nav = _nav_of(client, "/settings")
    assert "/settings" in nav and "/identity" in nav and "/analytics" in nav
    assert 'nav-item active' in nav          # current page highlighted
    assert nav.count("nav-section-title") == 3
    assert nav.count('class="nav-item') == 12  # /users + /templates admin console entries


def test_regular_user_hides_admin_nav(client_as_user: TestClient):
    nav = _nav_of(client_as_user, "/leads")
    assert "/leads" in nav
    assert "/settings" not in nav
    assert "/identity" not in nav
    assert "/analytics" not in nav
    assert 'nav-item active' in nav


def test_nav_has_no_drift_between_pages(client: TestClient):
    """The original WS0.4 purpose: two pages can never disagree again.
    (active-class placement differs by current page — normalize it away.)"""
    nav_a = _nav_of(client, "/dashboard").replace(' class="nav-item active"', ' class="nav-item"')
    nav_b = _nav_of(client, "/leads").replace(' class="nav-item active"', ' class="nav-item"')
    assert nav_a == nav_b


def test_automations_link_guaranteed_present(client: TestClient):
    """Regression: leads.html used to lack the /automations link (drift bug)."""
    nav = _nav_of(client, "/leads")
    assert '/automations' in nav
