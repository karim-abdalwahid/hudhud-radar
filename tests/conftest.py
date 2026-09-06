"""
Shared pytest fixtures for HudhudRadar test suite.

- Forces the auth UserStore into in-memory isolation so tests never create
  real rows in the live Supabase `users` table.
- Provides an authenticated ADMIN TestClient (`client` fixture) that passes
  the AuthMiddleware for all dashboard/API tests.
"""
import uuid

import pytest
from starlette.testclient import TestClient

ADMIN_PASSWORD = "HudhudTest#2026"
_ADMIN_EMAIL = {"value": None}


@pytest.fixture(scope="session", autouse=True)
def _isolated_user_store():
    """Isolates user store AND automations persistence in memory for the whole
    test session, so tests never write real rows to the live Supabase."""
    from src.core import auth as auth_mod
    from src.core.event_dedup import event_deduplicator
    from src.automations.service import AutomationsService

    auth_mod.user_store._memory_fallback = lambda: True
    # Webhook dedup: force memory-only for ALL instances (class-level) — the live
    # processed_events table now exists, so tests must never round-trip to it.
    from src.core.event_dedup import EventDeduplicator, event_deduplicator
    _orig_db_ready = EventDeduplicator._db_ready
    EventDeduplicator._db_ready = lambda self: False
    event_deduplicator._db_disabled = True
    # Automations: force memory-only persistence (no Supabase, no disk writes)
    _orig_save_supabase = AutomationsService._save_supabase
    _orig_load_supabase = AutomationsService._load_supabase
    _orig_save_disk = AutomationsService._save
    AutomationsService._save_supabase = lambda self: False
    AutomationsService._load_supabase = lambda self: None
    AutomationsService._save = lambda self: None
    yield
    # Restore original state
    EventDeduplicator._db_ready = _orig_db_ready
    event_deduplicator._db_disabled = False
    for name, fn in (
        ("_save_supabase", _orig_save_supabase),
        ("_load_supabase", _orig_load_supabase),
        ("_save", _orig_save_disk),
    ):
        setattr(AutomationsService, name, fn)
    if "_memory_fallback" in auth_mod.user_store.__dict__:
        del auth_mod.user_store._memory_fallback


@pytest.fixture(scope="session")
def admin_creds():
    """Registers exactly one admin user (first user becomes admin) for the session."""
    from src.main import app

    if _ADMIN_EMAIL["value"] is None:
        _ADMIN_EMAIL["value"] = f"owner_{uuid.uuid4().hex[:8]}@hudhud.test"
        bootstrap = TestClient(app)
        res = bootstrap.post(
            "/auth/register",
            json={
                "email": _ADMIN_EMAIL["value"],
                "password": ADMIN_PASSWORD,
                "phone": "+201000000000",
                "full_name": "Hudhud Test Admin",
            },
        )
        assert res.status_code == 200, f"Admin registration failed: {res.text}"
        assert res.json()["role"] == "admin"
    return {"email": _ADMIN_EMAIL["value"], "password": ADMIN_PASSWORD}


@pytest.fixture
def client(admin_creds):
    """Authenticated admin TestClient (passes AuthMiddleware)."""
    from src.main import app

    c = TestClient(app)
    res = c.post(
        "/auth/login",
        json={"email": admin_creds["email"], "password": admin_creds["password"]},
    )
    assert res.status_code == 200, f"Admin login failed: {res.text}"
    return c


@pytest.fixture
def anon_client():
    """Unauthenticated TestClient for testing protection/redirect behavior."""
    from src.main import app

    return TestClient(app)
