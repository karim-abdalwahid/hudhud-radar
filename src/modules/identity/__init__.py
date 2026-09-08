"""
Identity Resolution Review Queue module — self-contained vertical slice (modular architecture WS0.3).
"""
from src.core.modules import module_registry
from src.modules.identity.routes import router


def register(app) -> None:
    app.include_router(router)


module_registry.register_module(
    name="identity",
    description="Identity Resolution Review Queue",
    register_router=register,
)
