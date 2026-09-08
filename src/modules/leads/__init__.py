"""
Leads & Conversations API module — self-contained vertical slice (modular architecture WS0.3).
"""
from src.core.modules import module_registry
from src.modules.leads.routes import router


def register(app) -> None:
    app.include_router(router)


module_registry.register_module(
    name="leads",
    description="Leads & Conversations API",
    register_router=register,
)
