"""
Test suite for Visual Automations & Workflows System and Meta Feed Sync & Filtering.
Automations API now requires authentication — the shared `client` fixture
(defined in tests/conftest.py) logs in as an admin.
"""
import pytest
from src.automations.service import automations_service


def test_automations_crud_and_simulation(client):
    """Verifies complete CRUD operations and step simulation for visual automations."""
    # 1. List automations
    res = client.get("/api/automations")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert len(data["workflows"]) >= 3

    # Verify standard workflows exist
    wf_names = [w["name"] for w in data["workflows"]]
    assert any("Instagram Reel" in name for name in wf_names)
    assert any("Facebook" in name for name in wf_names)

    # 2. Create new automation
    new_wf_payload = {
        "name": "Custom VIP Instagram Auto-DM",
        "description": "Test custom automation",
        "platform": "instagram",
        "trigger_type": "ig_reel_comment",
        "status": "active",
        "nodes": [
            {
                "id": "t1",
                "category": "trigger",
                "type": "ig_comment_trigger",
                "label": "Instagram Comment",
                "platform": "instagram",
                "icon": "📸",
                "config": {"keywords": ["vip", "خاص"]},
                "position": {"x": 100, "y": 200}
            },
            {
                "id": "a1",
                "category": "action",
                "type": "meta_dm_action",
                "label": "Send VIP DM",
                "platform": "instagram",
                "icon": "💬",
                "config": {"message": "أهلاً بك في فئة الـ VIP"},
                "position": {"x": 450, "y": 200}
            }
        ],
        "connections": [
            {"id": "c1", "from_node": "t1", "from_port": "output", "to_node": "a1", "to_port": "input"}
        ]
    }
    create_res = client.post("/api/automations", json=new_wf_payload)
    assert create_res.status_code == 200
    created = create_res.json()["workflow"]
    wf_id = created["id"]
    assert created["name"] == "Custom VIP Instagram Auto-DM"

    # 3. Get by ID
    get_res = client.get(f"/api/automations/{wf_id}")
    assert get_res.status_code == 200
    assert get_res.json()["workflow"]["id"] == wf_id

    # 4. Update automation
    update_res = client.put(f"/api/automations/{wf_id}", json={"name": "Updated VIP Closer"})
    assert update_res.status_code == 200
    assert update_res.json()["workflow"]["name"] == "Updated VIP Closer"

    # 5. Toggle active/paused status
    toggle_res = client.post(f"/api/automations/{wf_id}/toggle")
    assert toggle_res.status_code == 200
    assert toggle_res.json()["status_state"] == "paused"

    # 6. Test simulation
    test_res = client.post(f"/api/automations/{wf_id}/test")
    assert test_res.status_code == 200
    sim_data = test_res.json()
    assert sim_data["status"] == "success"
    assert sim_data["steps_count"] == 2
    assert len(sim_data["trace"]) == 2
    assert sim_data["total_latency_ms"] > 0

    # 7. Delete automation
    del_res = client.delete(f"/api/automations/{wf_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "success"


def test_meta_feed_filtering_and_metrics(client):
    """Verifies live Meta feed post_type filtering and engagement metrics."""
    # 1. Fetch all posts
    res = client.get("/api/meta/posts?platform=all&post_type=all&limit=100")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    posts = data["posts"]
    assert len(posts) > 0

    # Verify engagement metrics structure on cards
    first = posts[0]
    assert "likes_count" in first
    assert "comments_count" in first
    assert "shares_count" in first
    assert "views_count" in first
    assert "post_type" in first
    assert "platform" in first
    assert first["post_type"] in ["reel", "post"]
    assert first["platform"] in ["facebook", "instagram"]

    # 2. Filter by post_type=reel
    res_reels = client.get("/api/meta/posts?post_type=reel&limit=50")
    assert res_reels.status_code == 200
    reels = res_reels.json()["posts"]
    for r in reels:
        assert r["post_type"] == "reel"

    # 3. Filter by post_type=post
    res_posts = client.get("/api/meta/posts?post_type=post&limit=50")
    assert res_posts.status_code == 200
    normal_posts = res_posts.json()["posts"]
    for p in normal_posts:
        assert p["post_type"] == "post"

    # 4. Filter by platform=facebook
    res_fb = client.get("/api/meta/posts?platform=facebook&limit=50")
    assert res_fb.status_code == 200
    fb_items = res_fb.json()["posts"]
    for fb in fb_items:
        assert fb["platform"] == "facebook"

    # 5. Filter by platform=instagram
    res_ig = client.get("/api/meta/posts?platform=instagram&limit=50")
    assert res_ig.status_code == 200
    ig_items = res_ig.json()["posts"]
    for ig in ig_items:
        assert ig["platform"] == "instagram"


def test_logo_unification_and_automations_page(client):
    """Verifies that the unified Hudhud. brand logo is present across pages and automations route loads."""
    # Check landing page
    res_landing = client.get("/")
    assert res_landing.status_code == 200
    assert "brand-dot" in res_landing.text

    # Check dashboard
    res_dash = client.get("/dashboard")
    assert res_dash.status_code == 200
    assert "brand-dot" in res_dash.text
    assert "brand-logo-link" in res_dash.text

    # Check studio
    res_studio = client.get("/studio")
    assert res_studio.status_code == 200
    assert "brand-dot" in res_studio.text
    assert "flt-type-reels" in res_studio.text
    assert "metrics-pill-group" in res_studio.text
    assert "meta-pagination-container" in res_studio.text
    assert "meta-live-section" in res_studio.text
    # Verify section order: AI Generator before Live Meta Archive
    ai_gen_idx = res_studio.text.find("st.ai_gen_title")
    live_idx = res_studio.text.find("meta-live-section")
    assert ai_gen_idx < live_idx, "AI Generator should appear before Live Meta Archive"

    # Check automations page
    res_auto = client.get("/automations")
    assert res_auto.status_code == 200
    assert "canvas-world" in res_auto.text
    assert "canvas-svg" in res_auto.text
    assert "brand-dot" in res_auto.text


def test_webhook_endpoints_and_challenge_verification(client):
    """Verifies all webhook aliases respond to Meta challenge verification."""
    from src.config import settings

    token = settings.EFFECTIVE_WEBHOOK_VERIFY_TOKEN
    challenge = "meta_verify_challenge_998877"

    # Test all aliases
    endpoints = ["/webhooks/meta", "/api/webhook/meta", "/api/webhook/instagram", "/api/webhooks/meta"]
    for ep in endpoints:
        res = client.get(f"{ep}?hub.mode=subscribe&hub.challenge={challenge}&hub.verify_token={token}")
        assert res.status_code == 200, f"Failed for {ep}"
        assert res.text == challenge

    # Test rejection with invalid token
    bad_res = client.get(f"/api/webhook/meta?hub.mode=subscribe&hub.challenge={challenge}&hub.verify_token=wrong_token")
    assert bad_res.status_code == 403

    # Test receiving a comment event via POST
    comment_payload = {
        "object": "instagram",
        "entry": [
            {
                "id": "17841400000000000",
                "time": 1725510000,
                "changes": [
                    {
                        "field": "comments",
                        "value": {
                            "id": "comm_12345",
                            "text": "مهتم بكورس السوشيال والتفاصيل",
                            "media": {"id": "18000000000000000"},
                            "from": {"id": "user_999", "username": "lead_client"}
                        }
                    }
                ]
            }
        ]
    }
    # Test receiving a comment event via POST with valid HMAC signature
    import hmac
    import hashlib
    import json

    raw_payload = json.dumps(comment_payload).encode("utf-8")
    secret = (settings.META_APP_SECRET or "dev-secret").encode("utf-8")
    sig = "sha256=" + hmac.new(secret, raw_payload, hashlib.sha256).hexdigest()

    post_res = client.post(
        "/api/webhook/meta",
        content=raw_payload,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig}
    )
    assert post_res.status_code == 200
    assert post_res.json()["status"] == "received"
    assert post_res.json()["events_queued"] >= 1


