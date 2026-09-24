"""Customer account page regression tests.

The page must remain safe for normal users: no admin capability is exposed and
all server actions continue to derive ownership from the signed session.
"""
from starlette.testclient import TestClient


def test_account_page_requires_session(anon_client: TestClient):
    response = anon_client.get("/account", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/login?next=/account")


def test_normal_user_can_open_account_and_analytics(client_as_user: TestClient):
    account = client_as_user.get("/account")
    assert account.status_code == 200
    assert "Subscription &amp; plan" in account.text or "Subscription & plan" in account.text
    assert "Connected channels" in account.text
    assert "connectThreads" in account.text
    assert client_as_user.get("/analytics").status_code == 200


def test_account_page_uses_dom_events_not_user_data_inside_inline_handlers(client_as_user: TestClient):
    page = client_as_user.get("/account")
    assert page.status_code == 200
    assert "__ACCOUNT_EMAIL__" not in page.text
    assert "onclick=" not in page.text
    assert "addEventListener('click'" in page.text
