"""
Boot guard: every route annotation must RESOLVE.

Regression guard for the 2026-09-10 production outage — a route signature
used `request: Request` without importing Request. Local Python 3.14 defers
annotation evaluation (PEP 649) so the NameError never surfaced locally,
while the older Vercel runtime evaluated eagerly at import → boot failure.

typing.get_type_hints() forces eager resolution of every annotation, so this
test catches missing imports on ANY Python version.
"""
import typing

from fastapi.routing import APIRoute

from src.main import app


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
    paths = {getattr(r, "path", None) for r in app.routes}
    for required in ("/health", "/auth/login", "/api/connections",
                     "/api/inbox/conversations/{lead_id}/send-message"):
        assert required in paths, f"missing route: {required}"
