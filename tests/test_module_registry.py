"""
Modular architecture foundation tests (WS0.1).
The module registry must: register modules, contribute public paths to the
auth policy, stay default-deny for undeclared mutations, and keep legacy
lists working during the strangler migration.
"""
import pytest

import src.modules.compliance  # noqa: F401 — registration happens at import


def test_compliance_module_registered_and_declares_public_paths():
    from src.core.modules import module_registry

    m = module_registry.get("compliance")
    assert m is not None, "compliance pilot module must be registered"
    assert "/privacy" in module_registry.public_exact_paths()
    assert "/data-deletion" in module_registry.public_exact_paths()
    assert any(p.startswith("/api/data-deletion") for p in module_registry.public_prefixes())
    assert any(p.startswith("/api/threads/uninstall") for p in module_registry.public_prefixes())


def test_auth_policy_includes_registry_paths():
    from src.core.auth import is_public_path

    # Module-declared paths must be public WITHOUT being in legacy lists
    assert is_public_path("/privacy") is True
    assert is_public_path("/data-deletion") is True
    # Legacy list path still works (strangler compat)
    assert is_public_path("/health") is True
    # Undeclared API path stays protected (default-deny)
    assert is_public_path("/api/definitely-not-a-real-endpoint") is False


def test_duplicate_module_names_rejected():
    from src.core.modules import ModuleRegistry, Module

    reg = ModuleRegistry()
    reg.register(Module(name="dup"))
    with pytest.raises(ValueError):
        reg.register(Module(name="dup"))


def test_nav_sorted_and_admin_filtered():
    from src.core.modules import ModuleRegistry, Module, NavEntry

    reg = ModuleRegistry()
    reg.register(Module(name="m1", nav=[
        NavEntry(href="/b", label_key="nav.b", section="Workspaces", order=2),
        NavEntry(href="/a", label_key="nav.a", section="Workspaces", order=1),
        NavEntry(href="/secret", label_key="nav.secret", section="Workspaces",
                 admin_only=True, order=0),
    ]))
    user_nav = reg.sorted_nav(is_admin=False)
    assert [n.href for n in user_nav] == ["/a", "/b"]          # admin-only filtered, sorted
    admin_nav = reg.sorted_nav(is_admin=True)
    assert [n.href for n in admin_nav] == ["/secret", "/a", "/b"]  # admin sees all, sorted
