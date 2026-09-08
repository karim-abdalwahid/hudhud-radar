"""
Shared pytest fixtures for HudhudRadar test suite.

- Forces the auth UserStore into in-memory isolation so tests never create
  real rows in the live Supabase `users` table.
- Provides an authenticated ADMIN TestClient (`client` fixture) that passes
  the AuthMiddleware for all dashboard/API tests.
"""
import uuid
from pathlib import Path

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
    # Knowledge Base: force FILE mode in a tmp dir so tests never read/write
    # the live Supabase kb_documents/kb_chunks tables.
    import tempfile
    from src.agent import knowledge_base as kb_mod
    _tmp_kb_dir = tempfile.mkdtemp(prefix="hudhud_test_kb_")
    kb_mod.knowledge_base._mode = "file"
    kb_mod.knowledge_base.kb_dir = Path(_tmp_kb_dir)
    kb_mod.knowledge_base.reload()
    # LLM: force deterministic fallback heuristics (no live Gemini calls)
    from src.config import settings as _settings
    _orig_gemini_key = _settings.GEMINI_API_KEY
    _settings.GEMINI_API_KEY = None
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
    _settings.GEMINI_API_KEY = _orig_gemini_key
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


@pytest.fixture(autouse=True)
def _clear_auth_limiter_per_test():
    """Tests register repeatedly from the same TestClient IP; the auth rate
    limiter would trip 429 mid-suite. Clear it before EVERY test."""
    from src.core import auth as _auth
    _auth.auth_limiter._history.clear()
    yield
    _auth.auth_limiter._history.clear()


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
                "terms_accepted": True,
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


@pytest.fixture(scope="session")
def _regular_user_creds(admin_creds):
    """Registers one regular (non-admin) user after the admin exists."""
    from src.main import app

    email = f"user_{uuid.uuid4().hex[:8]}@hudhud.test"
    bootstrap = TestClient(app)
    res = bootstrap.post(
        "/auth/register",
        json={
            "email": email,
            "password": ADMIN_PASSWORD,
            "phone": "+201000000001",
            "full_name": "Hudhud Test User",
            "terms_accepted": True,
        },
    )
    assert res.status_code == 200, f"User registration failed: {res.text}"
    assert res.json()["role"] == "user"
    return {"email": email, "password": ADMIN_PASSWORD}


@pytest.fixture
def client_as_user(_regular_user_creds):
    """Authenticated REGULAR (non-admin) TestClient."""
    from src.main import app

    c = TestClient(app)
    res = c.post(
        "/auth/login",
        json={"email": _regular_user_creds["email"], "password": _regular_user_creds["password"]},
    )
    assert res.status_code == 200, f"User login failed: {res.text}"
    return c
