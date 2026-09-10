"""
Boot guard: every route annotation must RESOLVE + every critical route exists.

Regression guard for the 2026-09-10 production outage — a route signature
used `request: Request` without importing Request. Local Python 3.14 defers
annotation evaluation (PEP 649) so the NameError never surfaced locally,
while the older Vercel runtime evaluated eagerly at import → boot failure.

Two mechanics handled here:
- typing.get_type_hints() forces eager annotation resolution on any Python.
- Recent FastAPI defers include_router flattening (lazy _IncludedRouter);
  app.openapi() forces full flattening — so we call it BEFORE inspecting.
"""
import typing

from fastapi.routing import APIRoute

from src.main import app

_openapi = app.openapi()  # forces lazy _IncludedRouter flattening


def test_all_route_annotations_resolve():
    broken = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        try:
            typing.get_type_hints(route.endpoint)
        except Exception as e:
            broken.append(f"{getattr(route, 'path', '?')} → {type(e).__name__}: {e}")
    assert not broken, "routes with unresolved annotations:\n" + "\n".join(broken)


def test_app_has_core_routes():
    """The app booted (import above) and the critical surfaces are registered."""
    paths = set(_openapi["paths"])
    for required in ("/health", "/auth/login", "/api/connections",
                     "/api/inbox/conversations/{lead_id}/send-message"):
        assert required in paths, f"missing route: {required}"


def test_route_count_sanity():
    """Full flattening must expose a healthy route count (outage = ~80)."""
    n = len(_openapi["paths"])
    assert n > 100, f"only {n} paths registered — module registration incomplete"
