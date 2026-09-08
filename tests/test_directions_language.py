"""
WS-C+D tests: page directions (EN=form left, AR=mirrored) and English as
the default language everywhere (no page boots Arabic on its own).
"""
import re
from starlette.testclient import TestClient

import src.modules.pages  # noqa: F401


def test_auth_defaults_to_english_ltr(anon_client: TestClient):
    r = anon_client.get("/login")
    assert r.status_code == 200
    assert '<html lang="en" dir="ltr">' in r.text
    assert '<html lang="ar" dir="rtl">' not in r.text


def test_auth_ar_explicit_opt_in(anon_client: TestClient):
    """auth.html flips lang/dir client-side from localStorage (its own i18n);
    ?lang=ar still lands EN/LTR server-side — the JS applies AR after load."""
    r = anon_client.get("/login?lang=ar")
    assert r.status_code == 200
    assert "hudhud_lang" in r.text          # language machinery present
    assert "applyLang" in r.text            # client-side direction flip runs


def test_auth_served_through_unified_pipeline(anon_client: TestClient):
    """HUDHUD_BASE_URL injection must reach the login page (unified pipeline)."""
    r = anon_client.get("/login")
    assert "window.HUDHUD_BASE_URL" in r.text


def test_body_uses_row_reverse_for_direction(anon_client: TestClient):
    r = anon_client.get("/login")
    assert "flex-direction: row-reverse" in r.text
    assert 'html[dir="rtl"] body { flex-direction: row; }' in r.text


def test_no_ar_fallback_in_auth_source(anon_client: TestClient):
    """The 'Arabic from nowhere' bug: JS fallback `|| "ar"` must stay dead."""
    r = anon_client.get("/login")
    assert '|| "ar"' not in r.text


def test_auth_has_no_duplicate_login_routes(client: TestClient):
    """pages module owns /login+register; auth_module must not also serve them."""
    from src.main import app
    login_routes = [r for r in app.routes if getattr(r, "path", "") in ("/login", "/register")]
    assert len(login_routes) == 2
