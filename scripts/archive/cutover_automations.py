import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---- 1. _load(): DB table first, then legacy cascade, with bootstrap mirror ----
p = "src/automations/service.py"
src = open(p, encoding="utf-8").read()

old_load = '''    def _load(self):
        """Loads workflows: Supabase first, then disk, then defaults."""
        # 1. Supabase (serverless-safe source of truth)
        cloud = self._load_supabase()'''
new_load = '''    def _load(self):
        """Loads workflows: DB table (Wave 9.8 source of truth) first,
        then legacy Supabase settings, then disk, then defaults.
        Legacy loads are mirrored into the table once (self-healing bootstrap)."""
        # 0. automations_workflows table (per-user ready)
        table_rows = self._load_db()
        if table_rows:
            for wf in table_rows:
                self._workflows[wf.id] = wf
            self._sanitize_legacy_fabrications()
            logger.info(f"Loaded {len(self._workflows)} workflows from automations_workflows table")
            return

        # 1. Supabase legacy (serverless-safe until cutover is proven)
        cloud = self._load_supabase()'''
assert old_load in src
src = src.replace(old_load, new_load, 1)

# legacy branches call _save() at the end of cascade; _save now mirrors to DB.
# 2. _save(): add the DB mirror
old_save_head = '''    def _save(self):
        """Persists workflows to Supabase (primary) and disk (cache)."""
        saved_cloud = self._save_supabase()'''
new_save_head = '''    def _save(self):
        """Persists workflows: DB table (Wave 9.8 primary) + legacy Supabase
        settings mirror + disk cache."""
        saved_db = self._save_db()
        saved_cloud = self._save_supabase()'''
assert old_save_head in src
src = src.replace(old_save_head, new_save_head, 1)

open(p, "w", encoding="utf-8").write(src)
import ast; ast.parse(src)
print("service _load/_save cutover applied")
