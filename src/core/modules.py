"""
HudhudRadar Module Registry — the architectural backbone.

Every feature area lives in its OWN self-contained module under src/modules/<name>/
and registers itself via `register_module()`. Modules declare:
  - their routes (via a register_router(app) callback)
  - their pages (dashboard HTML pages, optionally admin-only)
  - their navigation entries (sidebar, grouped by section)
  - their auth requirements (public / user / admin) — DECLARED, never forgotten

AUTH IS DEFAULT-DENY FOR MUTATIONS: any POST/PUT/PATCH/DELETE route registered
through the registry without an explicit access="public" declaration is treated
as requiring a session. Admin requirements are explicit per route/page.

Adding a new feature = create a module package + one register_module() call in
its __init__. Nothing else. No giant main.py edits, no scattered path lists.

Human-readable and AI-agent-readable by design.
"""
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from src.core.logger import logger

# Access levels a route or page can declare.
ACCESS_PUBLIC = "public"      # no session required (landing, health, callbacks)
ACCESS_USER = "user"          # any authenticated session (default for reads)
ACCESS_ADMIN = "admin"        # admin session required (any method)


@dataclass
class NavEntry:
    """A sidebar navigation item contributed by a module."""
    href: str                      # e.g. "/leads" or "/admin/users"
    label_key: str                 # i18n key, e.g. "nav.leads"
    icon: str = "•"                # emoji or glyph shown before the label
    section: str = "Workspaces"    # sidebar section title (i18n-agnostic display key)
    admin_only: bool = False       # sidebar renders it only for admins
    order: int = 100               # sort order inside its section (lower = earlier)


@dataclass
class PageSpec:
    """A dashboard HTML page served by a module."""
    path: str                      # e.g. "/settings"
    template: str                  # template filename inside the module's templates dir
    access: str = ACCESS_USER      # ACCESS_USER or ACCESS_ADMIN (pages are never public)
    title_key: str = ""            # i18n key for the page title


@dataclass
class Module:
    """A self-contained feature module."""
    name: str                      # unique slug, e.g. "inbox", "admin_users"
    description: str = ""          # one line — helps humans and AI agents
    register_router: Optional[Callable[[Any], None]] = None
    pages: List[PageSpec] = field(default_factory=list)
    nav: List[NavEntry] = field(default_factory=list)
    # Path prefixes that are public despite being under the module (webhooks etc.)
    public_prefixes: List[str] = field(default_factory=list)
    # Exact paths that are public (callbacks, health, landing)
    public_exact: List[str] = field(default_factory=list)


class ModuleRegistry:
    """Central registry of all feature modules."""

    def __init__(self):
        self._modules: Dict[str, Module] = {}
        self._registered_apps: List[Any] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    def register(self, module: Module) -> Module:
        if module.name in self._modules:
            raise ValueError(f"Module '{module.name}' registered twice — duplicate module name")
        self._modules[module.name] = module
        logger.info(f"Module registered: {module.name} ({len(module.pages)} pages, {len(module.nav)} nav entries)")
        return module

    def register_module(
        self,
        name: str,
        description: str = "",
        register_router: Optional[Callable[[Any], None]] = None,
        pages: Optional[List[PageSpec]] = None,
        nav: Optional[List[NavEntry]] = None,
        public_prefixes: Optional[List[str]] = None,
        public_exact: Optional[List[str]] = None,
    ) -> Module:
        """Convenience one-call registration used by module __init__ files."""
        return self.register(Module(
            name=name,
            description=description,
            register_router=register_router,
            pages=pages or [],
            nav=nav or [],
            public_prefixes=public_prefixes or [],
            public_exact=public_exact or [],
        ))

    def mount_all(self, app) -> None:
        """Called once by the app factory: registers every module's router."""
        for module in self._modules.values():
            if module.register_router:
                module.register_router(app)
                logger.info(f"Module router mounted: {module.name}")
        self._registered_apps.append(app)

    # ------------------------------------------------------------------
    # Auth policy derivation (replaces hand-maintained path lists)
    # ------------------------------------------------------------------
    def public_exact_paths(self) -> set:
        """Exact paths that require no session — union of all modules' declarations
        plus the static framework set in core/auth."""
        out = set()
        for m in self._modules.values():
            out.update(m.public_exact)
            for page in m.pages:
                if page.access == ACCESS_PUBLIC:
                    out.add(page.path)
        return out

    def public_prefixes(self) -> tuple:
        out = set()
        for m in self._modules.values():
            out.update(m.public_prefixes)
        return tuple(sorted(out))

    def admin_page_paths(self) -> set:
        return {p.path for m in self._modules.values() for p in m.pages if p.access == ACCESS_ADMIN}

    def module_names(self) -> List[str]:
        return sorted(self._modules.keys())

    def get(self, name: str) -> Optional[Module]:
        return self._modules.get(name)

    def all_modules(self) -> List[Module]:
        return [self._modules[k] for k in sorted(self._modules.keys())]

    def sorted_nav(self, is_admin: bool) -> List[NavEntry]:
        """Sidebar entries for a user: sections in stable order, entries by order."""
        entries = [n for m in self._modules.values() for n in m.nav]
        if not is_admin:
            entries = [n for n in entries if not n.admin_only]
        # stable unique sections
        sections: Dict[str, List[NavEntry]] = {}
        for n in entries:
            sections.setdefault(n.section, []).append(n)
        result: List[NavEntry] = []
        for section in sorted(sections.keys()):
            result.extend(sorted(sections[section], key=lambda x: (x.order, x.label_key)))
        return result


module_registry = ModuleRegistry()


# --------------------------------------------------------------------
# Canonical sidebar navigation — THE single source of truth (WS0.4).
# Templates no longer hardcode nav; the server renders it from here.
# Adding a dashboard page = one NavEntry. Drift between pages is impossible.
# --------------------------------------------------------------------
from dataclasses import dataclass as _dc  # noqa: E402


@_dc
class SidebarSection:
    key: str          # i18n key for the section title
    fallback: str     # English fallback text


SIDEBAR_SECTIONS = {
    "nav.conversations": SidebarSection("nav.conversations", "Conversations & AI Agent"),
    "nav.workspaces": SidebarSection("nav.workspaces", "Workspaces"),
    "nav.analytics_system": SidebarSection("nav.analytics_system", "Analytics & System"),
}


def render_sidebar_nav(current_path: str, is_admin: bool) -> str:
    """Renders the sidebar <nav> HTML from the registry — role-aware."""
    import html as _html
    entries = module_registry.sorted_nav(is_admin)
    parts = ['<nav class="sidebar-nav">']
    last_section = None
    for n in entries:
        if n.section != last_section:
            sec = SIDEBAR_SECTIONS.get(n.section)
            label = _html.escape(sec.fallback if sec else n.section)
            parts.append(
                f'<div class="nav-section-title" data-i18n="{n.section}">{label}</div>'
            )
            last_section = n.section
        active = " active" if current_path == n.href else ""
        icon = _html.escape(n.icon, quote=False)
        label_fb = n.href.strip("/") or "home"
        parts.append(
            f'<a href="{_html.escape(n.href)}" class="nav-item{active}">'
            f'<span class="nav-icon">{icon}</span> '
            f'<span data-i18n="{n.label_key}">{_html.escape(label_fb)}</span></a>'
        )
    parts.append("</nav>")
    return "\n".join(parts)


def platform_icon_svg(platform: str, size: int = 20, radius: int = 6) -> str:
    """Official brand SVG for a connected platform (facebook/instagram/...).
    Implemented in src/platforms/brand_icons.py — keeps this file import-light."""
    try:
        from src.platforms.brand_icons import platform_icon_svg as _impl
        return _impl(platform, size, radius)
    except Exception:
        return (f'<span style="display:inline-flex;width:{size}px;height:{size}px;'
                f'border-radius:{radius}px;background:#64748b;"></span>')
