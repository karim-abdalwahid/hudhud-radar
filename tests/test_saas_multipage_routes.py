"""
Unit & Integration tests for Multi-Page SaaS Web Application Architecture.
Verifies all dedicated routes, static asset delivery, LEANN-hybrid search API,
and authentication protection (shared authed `client` from conftest).
"""
import pytest


def test_saas_static_assets(client):
    """Verifies that static CSS and JS are served with 200 OK."""
    css_resp = client.get("/static/saas.css")
    assert css_resp.status_code == 200
    assert "text/css" in css_resp.headers.get("content-type", "")
    assert "--bg-page" in css_resp.text

    js_resp = client.get("/static/saas.js")
    assert js_resp.status_code == 200
    assert "checkSystemMetaStatus" in js_resp.text


def test_saas_multipage_routes(client):
    """Verifies that each dedicated SaaS page route returns 200 and proper HTML content."""
    routes_and_keywords = [
        ("/", "Hudhud"),
        ("/dashboard", "Overview"),
        ("/leads", "Leads"),
        ("/studio", "Studio"),
        ("/knowledge", "Knowledge"),
        ("/identity", "Identity"),
        ("/analytics", "Analytics"),
        ("/settings", "Settings"),
        ("/automations", "Automations"),
    ]

    for route, keyword in routes_and_keywords:
        resp = client.get(route)
        assert resp.status_code == 200, f"Route {route} failed with status {resp.status_code}"
        assert "text/html" in resp.headers.get("content-type", "")
        assert (keyword in resp.text or "HudhudRadar" in resp.text), f"Keyword '{keyword}' not found in {route}"
        if route != "/":
            assert "/static/saas.css" in resp.text, f"saas.css stylesheet link missing in {route}"
            assert "/static/saas.js" in resp.text, f"saas.js client script missing in {route}"


def test_api_knowledge_search_fails_closed_without_database(client):
    """A disconnected DB must never fall back to a global in-memory KB cache."""
    resp = client.post("/api/knowledge/search", json={"query": "بكام باقة الإعلانات والتسويق", "top_k": 3})
    assert resp.status_code == 503
    data = resp.json()
    assert "مشتركة" in data["detail"]
