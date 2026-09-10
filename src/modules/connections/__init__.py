"""
Phase 9.7 — Connections module: per-user platform connections (three doors).

📘 facebook / 📸 instagram doors implemented here; 🧵 threads door reuses the
existing threads OAuth callback (now session-aware, storing per-user).

Golden rule enforced in service.py: entitlements (what the user paid for)
are the ONLY source of permission — connections never grant service.
"""
from src.core.modules import module_registry
from src.modules.connections.routes import router


def register(app) -> None:
    app.include_router(router)


module_registry.register_module(
    name="connections",
    description="Per-user platform connections (facebook/instagram/threads doors) "
                "+ entitlement-gated feature access (Phase 9.7)",
    register_router=register,
    pages=[],
    public_exact=[],
    # callbacks are browser flows carrying the session cookie; they validate
    # their own signed state — and must be reachable while the session rides along
    public_prefixes=["/api/connections/facebook/callback",
                     "/api/connections/instagram/callback"],
)
