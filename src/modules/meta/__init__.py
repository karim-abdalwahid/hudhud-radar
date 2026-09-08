"""
Meta Platform & Social Connection Management module — self-contained vertical slice (modular architecture WS0.3).
"""
from src.core.modules import module_registry
from src.modules.meta.routes import router


def register(app) -> None:
    app.include_router(router)


module_registry.register_module(
    name="meta",
    description="Meta Platform & Social Connection Management",
    register_router=register,
)
