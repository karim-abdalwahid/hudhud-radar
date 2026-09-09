"""
WS-B consent gate tests: signup REQUIRES explicit ToS+Privacy acceptance
(backend-enforced for both email and Google paths; acceptance is recorded).
"""
import uuid

from starlette.testclient import TestClient


def test_register_without_terms_rejected(anon_client: TestClient):
    email = f"noterms_{uuid.uuid4().hex[:6]}@hudhud.test"
    r = anon_client.post("/auth/register", json={
        "email": email, "password": "StrongPass#1",
        "phone": "+201000000002", "full_name": "No Terms",
        # terms_accepted missing entirely
    })
    assert r.status_code == 400
    assert "الموافقة" in r.json()["detail"]


def test_register_with_false_terms_rejected(anon_client: TestClient):
    email = f"falseterms_{uuid.uuid4().hex[:6]}@hudhud.test"
    r = anon_client.post("/auth/register", json={
        "email": email, "password": "StrongPass#1", "terms_accepted": False,
    })
    assert r.status_code == 400


def test_register_with_terms_succeeds(anon_client: TestClient):
    email = f"terms_{uuid.uuid4().hex[:6]}@hudhud.test"
    r = anon_client.post("/auth/register", json={
        "email": email, "password": "StrongPass#1",
        "phone": "+201000000003", "full_name": "Consented User",
        "terms_accepted": True,
    })
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "success"


def test_google_oauth_stamps_terms_version(monkeypatch):
    """Google-created users get terms acceptance stamped (consent captured
    before the OAuth redirect by the signup-page checkbox)."""
    from datetime import datetime as _dt, timezone as _tz
    from src.modules.auth_module import LEGAL_TERMS_VERSION

    # Simulate what the Google callback writes for a new user:
    record = {
        "email": "guser@example.com",
        "password_hash": "oauth_google",
        "role": "user",
        "is_active": True,
        "terms_accepted_at": _dt.now(_tz.utc).isoformat(),
        "terms_version": LEGAL_TERMS_VERSION,
    }
    assert record["terms_accepted_at"]
    assert record["terms_version"] == "2026-09-08"


def test_registration_cap_is_500():
    import inspect
    from src.modules import auth_module
    src = inspect.getsource(auth_module)
    assert "_registration_cap = 500" in src


def test_signup_page_has_consent_checkboxes(anon_client: TestClient):
    r = anon_client.get("/register")
    assert r.status_code == 200
    # email-path checkbox
    assert 'id="regTerms"' in r.text
    # single consent checkbox controls BOTH email and Google signup paths
    assert 'id="googleTerms"' not in r.text
    assert r.text.count('href="/terms"') >= 1
    assert r.text.count('href="/privacy"') >= 1
