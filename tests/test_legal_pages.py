"""
Legal pages tests (WS-A): bilingual /terms + /privacy served by the legal
module, honest placeholders filled, public access, lang toggle.
"""
import re

from starlette.testclient import TestClient

import src.modules.legal  # noqa: F401 — route registration


def test_terms_en_public(anon_client: TestClient):
    r = anon_client.get("/terms")
    assert r.status_code == 200
    assert "Terms of Service" in r.text
    assert "Arab Republic of Egypt" in r.text          # governing law (owner decision)
    assert "Cairo Economic Courts" in r.text
    assert "support@hudhd.com" in r.text                # platform contact (S-Purge)
    assert "www.hudhd.com" in r.text                    # our real site
    assert "Gemini" in r.text                           # honest AI disclosure
    assert "24-hour standard messaging window" in r.text  # real enforced rule
    assert "currently three days" in r.text              # matches the live trial contract
    assert "Ebd'a" not in r.text and "ebdamarketing" not in r.text


def test_terms_ar_toggle(anon_client: TestClient):
    r = anon_client.get("/terms?lang=ar")
    assert r.status_code == 200
    assert "شروط الاستخدام" in r.text
    assert "جمهورية مصر العربية" in r.text
    assert 'dir="rtl"' in r.text


def test_privacy_en_full_policy(anon_client: TestClient):
    r = anon_client.get("/privacy")
    assert r.status_code == 200
    assert "Privacy Policy" in r.text
    for section in ["Data we collect", "AI processing", "Your rights",
                    "Cookies", "Security", "Data deletion"]:
        assert section in r.text, f"missing section: {section}"
    assert "Supabase" in r.text and "Vercel" in r.text   # real providers
    assert "we never store plain passwords" in r.text or "never store plain passwords" in r.text
    assert "PBKDF2" in r.text


def test_privacy_ar_toggle(anon_client: TestClient):
    r = anon_client.get("/privacy?lang=ar")
    assert r.status_code == 200
    assert "سياسة الخصوصية" in r.text
    assert "لا نبيع" in r.text


def test_legal_pages_have_no_placeholders_left(anon_client: TestClient):
    for path in ("/terms", "/privacy", "/terms?lang=ar", "/privacy?lang=ar"):
        r = anon_client.get(path)
        assert "{company_en}" not in r.text and "{email}" not in r.text
        assert "{version}" not in r.text
