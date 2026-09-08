"""
Cron Endpoints + Admin Alerts + Debug Diagnostics module — self-contained vertical slice (modular architecture WS0.3).
"""
from src.core.modules import module_registry
from src.modules.cron_admin.routes import router


def register(app) -> None:
    app.include_router(router)


module_registry.register_module(
    name="cron_admin",
    description="Cron Endpoints + Admin Alerts + Debug Diagnostics",
    register_router=register,
)
