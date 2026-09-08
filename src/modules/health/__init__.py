"""
System Health & Info module — self-contained vertical slice (modular architecture WS0.3).
"""
from src.core.modules import module_registry
from src.modules.health.routes import router


def register(app) -> None:
    app.include_router(router)


module_registry.register_module(
    name="health",
    description="System Health & Info",
    register_router=register,
)
