"""
AI Providers & Models (Phase 8) module — self-contained vertical slice (modular architecture WS0.3).
"""
from src.core.modules import module_registry
from src.modules.ai.routes import router


def register(app) -> None:
    app.include_router(router)


module_registry.register_module(
    name="ai",
    description="AI Providers & Models (Phase 8)",
    register_router=register,
)
