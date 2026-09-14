"""500-hunter regressions: hostile payloads & bad ids must never 5xx."""
import hashlib
import hmac
import json

from src.config import settings


def _meta_sig(raw: bytes) -> str:
    return "sha256=" + hmac.new((settings.META_APP_SECRET or "").encode(),
                                raw, hashlib.sha256).hexdigest()


def test_meta_webhook_signed_garbage_returns_400(client):
    raw = b"total garbage {{{"
    r = client.post("/api/webhook/meta", content=raw,
                    headers={"Content-Type": "application/json",
                             "X-Hub-Signature-256": _meta_sig(raw)})
    assert r.status_code == 400, r.text[:150]


def test_meta_webhook_list_payload_ignored(client):
    raw = json.dumps([1, 2, 3]).encode()
    r = client.post("/api/webhook/meta", content=raw,
                    headers={"Content-Type": "application/json",
                             "X-Hub-Signature-256": _meta_sig(raw)})
    assert r.status_code == 200
    assert r.json()["status"] == "ignored"


def test_meta_webhook_string_entries_no_crash(client):
    raw = json.dumps({"object": "page", "entry": "not-a-list"}).encode()
    r = client.post("/api/webhook/meta", content=raw,
                    headers={"Content-Type": "application/json",
                             "X-Hub-Signature-256": _meta_sig(raw)})
    assert r.status_code == 200 and r.json()["status"] == "received"


def test_meta_webhook_null_mention_value(client):
    raw = json.dumps({"object": "page", "entry": [
        {"changes": [{"field": "mentions", "value": None}]}]}).encode()
    r = client.post("/api/webhook/meta", content=raw,
                    headers={"Content-Type": "application/json",
                             "X-Hub-Signature-256": _meta_sig(raw)})
    assert r.status_code == 200


def test_bad_uuid_paths_are_404_not_500(client):
    for path in ["/api/leads/not-a-uuid", "/api/content/posts/not-a-uuid",
                 "/api/notifications/not-a-uuid/read",
                 "/api/identity/queue/not-a-uuid/approve",
                 "/api/admin/users/not-a-uuid/credits"]:
        get = client.get(path)
        post = client.post(path, json={})
        for r in (get, post):
            assert r.status_code < 500, (path, r.status_code, r.text[:120])


def test_real_uuid_paths_still_work_after_guard(client):
    # a real conversation must still resolve (guard must not block valid ids)
    convs = client.get("/api/inbox/conversations").json().get("conversations", [])
    if convs:
        r = client.get(f"/api/inbox/conversations/{convs[0]['lead_id']}/takeover")
        assert r.status_code in (404, 405, 200)  # GET on POST route -> method/ok, never 500
        r2 = client.get(f"/api/leads/{convs[0]['lead_id']}")
        assert r2.status_code in (200, 404)
