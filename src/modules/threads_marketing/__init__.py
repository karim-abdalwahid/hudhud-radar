"""
Threads & Marketing Extended APIs module — self-contained vertical slice (modular architecture WS0.3).
"""
from src.core.modules import module_registry
from src.modules.threads_marketing.routes import router


def register(app) -> None:
    app.include_router(router)


module_registry.register_module(
    name="threads_marketing",
    description="Threads & Marketing Extended APIs",
    register_router=register,
)
