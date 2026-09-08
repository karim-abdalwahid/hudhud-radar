"""
Analytics & Performance Reports module — self-contained vertical slice (modular architecture WS0.3).
"""
from src.core.modules import module_registry
from src.modules.analytics.routes import router


def register(app) -> None:
    app.include_router(router)


module_registry.register_module(
    name="analytics",
    description="Analytics & Performance Reports",
    register_router=register,
)
