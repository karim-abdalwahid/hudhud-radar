"""
Compliance module — Meta/Threads legally-mandated callbacks & pages.

Self-contained module (modular architecture pilot): pages, callbacks, and
their public-path declarations in ONE place. Registered via module_registry.
"""
from src.core.modules import module_registry
from src.meta_api.compliance_pages import register_compliance_routes


def register(app) -> None:
    register_compliance_routes(app)


module_registry.register_module(
    name="compliance",
    description="Meta data-deletion + deauthorization + Threads uninstall callbacks, privacy & deletion pages",
    register_router=register,
    pages=[
        # pages served inside compliance_pages are public HTML (privacy/deletion)
    ],
    public_exact=["/privacy", "/data-deletion", "/data_deletion"],
    public_prefixes=["/api/data-deletion", "/api/threads/uninstall", "/api/deauthorize"],
)
