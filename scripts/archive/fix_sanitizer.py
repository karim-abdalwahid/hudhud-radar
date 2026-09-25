import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "src/automations/service.py"
src = open(p, encoding="utf-8").read()

# 1. Robust sanitizer: handle pydantic NodeData AND dict nodes (pre-existing bug)
old = '''    def _sanitize_legacy_fabrications(self):
        """One-time cleanup of previously-shipped fabricated defaults that
        could DM real customers a fake booking link / discount code."""
        dirty = False
        for wf in self._workflows.values():
            for node in (wf.nodes or []):
                cfg = node.get("config") or {}
                if cfg.get("discount_code") == "HUDHUD20":
                    cfg["discount_code"] = ""
                    cfg["include_offer"] = False
                    node["config"] = cfg
                    dirty = True
                if cfg.get("calendar_link") == "https://calendar.app.google/hudhud-meeting":
                    cfg["calendar_link"] = ""
                    cfg["cta_button"] = ""
                    node["config"] = cfg
                    dirty = True
        if dirty:
            logger.warning("Sanitized legacy fabricated automation defaults (HUDHUD20 / fake calendar link).")
            self._save()'''
new = '''    def _sanitize_legacy_fabrications(self):
        """One-time cleanup of previously-shipped fabricated defaults that
        could DM real customers a fake booking link / discount code.
        Nodes may be pydantic NodeData or raw dicts (legacy stores)."""
        dirty = False
        for wf in self._workflows.values():
            for node in (wf.nodes or []):
                if isinstance(node, dict):
                    cfg = node.get("config") or {}
                else:
                    cfg = getattr(node, "config", None) or {}
                if not isinstance(cfg, dict):
                    continue
                changed = False
                if cfg.get("discount_code") == "HUDHUD20":
                    cfg["discount_code"] = ""
                    cfg["include_offer"] = False
                    changed = True
                if cfg.get("calendar_link") == "https://calendar.app.google/hudhud-meeting":
                    cfg["calendar_link"] = ""
                    cfg["cta_button"] = ""
                    changed = True
                if changed:
                    if isinstance(node, dict):
                        node["config"] = cfg
                    else:
                        node.config = cfg
                    dirty = True
        if dirty:
            logger.warning("Sanitized legacy fabricated automation defaults (HUDHUD20 / fake calendar link).")
            self._save()'''
assert old in src
src = src.replace(old, new, 1)

# 2. make the table branch parse-safe like the legacy branches
old_branch = '''        table_rows = self._load_db()
        if table_rows:
            for wf in table_rows:
                self._workflows[wf.id] = wf
            self._sanitize_legacy_fabrications()
            logger.info(f"Loaded {len(self._workflows)} workflows from automations_workflows table")
            return'''
new_branch = '''        try:
            table_rows = self._load_db()
        except Exception as e:
            logger.error(f"Error loading automations from table: {e}")
            table_rows = None
            self._workflows = {}
        if table_rows:
            for wf in table_rows:
                self._workflows[wf.id] = wf
            self._sanitize_legacy_fabrications()
            logger.info(f"Loaded {len(self._workflows)} workflows from automations_workflows table")
            return'''
assert old_branch in src
src = src.replace(old_branch, new_branch, 1)

open(p, "w", encoding="utf-8").write(src)
import ast; ast.parse(src)
print("sanitizer fixed + table branch hardened")
