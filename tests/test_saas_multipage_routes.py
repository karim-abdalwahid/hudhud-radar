"""
Unit & Integration tests for Multi-Page SaaS Web Application Architecture.
Verifies all 7 dedicated routes, static asset delivery, and LEANN-hybrid search API.
"""
import pytest
from starlette.testclient import TestClient
from src.main import app


@pytest.fixture
def client():
    return TestClient(app)


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


def test_api_knowledge_hybrid_search(client):
    """Verifies the LEANN-inspired hybrid semantic search endpoint."""
    resp = client.post("/api/knowledge/search", json={"query": "بكام باقة الإعلانات والتسويق", "top_k": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert "query" in data
    assert "results" in data
    assert isinstance(data["results"], list)
    if data["results"]:
        top_res = data["results"][0]
        assert "score" in top_res
        assert "filename" in top_res
        assert "chunk" in top_res
        assert top_res["score"] > 0
