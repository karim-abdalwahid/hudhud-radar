import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 1. mirror-to-DB after legacy bootstrap loads (cloud/disk branches)
p = "src/automations/service.py"
src = open(p, encoding="utf-8").read()
old_cloud = '''                self._sanitize_legacy_fabrications()
                logger.info(f"Loaded {len(self._workflows)} workflows from Supabase app_settings")
                return'''
new_cloud = '''                self._sanitize_legacy_fabrications()
                logger.info(f"Loaded {len(self._workflows)} workflows from Supabase app_settings")
                self._save_db()  # one-time bootstrap mirror into the table
                return'''
assert old_cloud in src
src = src.replace(old_cloud, new_cloud, 1)
old_disk = '''                self._sanitize_legacy_fabrications()
                logger.info(f"Loaded {len(self._workflows)} workflows from {STORE_PATH}")
                return'''
new_disk = '''                self._sanitize_legacy_fabrications()
                logger.info(f"Loaded {len(self._workflows)} workflows from {STORE_PATH}")
                self._save_db()  # one-time bootstrap mirror into the table
                return'''
assert old_disk in src
src = src.replace(old_disk, new_disk, 1)
open(p, "w", encoding="utf-8").write(src)
import ast; ast.parse(src)
print("bootstrap mirrors added")

# 2. conftest isolation for the new table methods (same pattern as existing)
c = "tests/conftest.py"
src2 = open(c, encoding="utf-8").read()
src2 = src2.replace(
    """    _orig_save_supabase = AutomationsService._save_supabase
    _orig_load_supabase = AutomationsService._load_supabase
    _orig_save_disk = AutomationsService._save
    AutomationsService._save_supabase = lambda self: False
    AutomationsService._load_supabase = lambda self: None
    AutomationsService._save = lambda self: None""",
    """    _orig_save_supabase = AutomationsService._save_supabase
    _orig_load_supabase = AutomationsService._load_supabase
    _orig_save_disk = AutomationsService._save
    _orig_save_db = AutomationsService._save_db
    _orig_load_db = AutomationsService._load_db
    AutomationsService._save_supabase = lambda self: False
    AutomationsService._load_supabase = lambda self: None
    AutomationsService._save_db = lambda self: False
    AutomationsService._load_db = lambda self: None
    AutomationsService._save = lambda self: None""", 1)
src2 = src2.replace(
    """    for name, fn in (
        ("_save_supabase", _orig_save_supabase),
        ("_load_supabase", _orig_load_supabase),
        ("_save", _orig_save_disk),
    ):""",
    """    for name, fn in (
        ("_save_supabase", _orig_save_supabase),
        ("_load_supabase", _orig_load_supabase),
        ("_save_db", _orig_save_db),
        ("_load_db", _orig_load_db),
        ("_save", _orig_save_disk),
    ):""", 1)
open(c, "w", encoding="utf-8").write(src2)
ast.parse(src2)
print("conftest isolation extended")
