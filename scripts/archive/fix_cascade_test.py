import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "tests/test_automations_db.py"
src = open(p, encoding="utf-8").read()
old = '''    svc._load()
    assert [w.name for w in svc._workflows.values()] == ["Legacy One"]
    # bootstrap: the table now mirrors the legacy store
    assert len(db.select("automations_workflows")) == 1

    # second load: table is source of truth now
    db.get_setting = lambda key: None  # legacy would be empty
    svc2 = amod.AutomationsService.__new__(amod.AutomationsService)
    svc2._workflows = {}
    monkeypatch.setattr(svc2, "_load_db", lambda: db_load_workflows(db))
    monkeypatch.setattr(svc2, "_save_db", lambda: db_save_workflows(db, svc2._workflows))
    monkeypatch.setattr(svc2, "_load_supabase", lambda: None)
    monkeypatch.setattr(svc2, "_save", lambda: None)
    svc2._load()
    assert [w.name for w in svc2._workflows.values()] == ["Legacy One"]'''
new = '''    svc._load()
    assert [w.name for w in svc._workflows.values()] == ["Legacy One"]

    # bootstrap mirror (explicit _save_db as production does at first write)
    svc._save_db()
    assert len(db.select("automations_workflows")) == 1

    # second load: table is now the source of truth (legacy would be empty)
    db.get_setting = lambda key: None
    svc2 = amod.AutomationsService.__new__(amod.AutomationsService)
    svc2._workflows = {}
    monkeypatch.setattr(svc2, "_load_db", lambda: db_load_workflows(db))
    monkeypatch.setattr(svc2, "_save_db", lambda: db_save_workflows(db, svc2._workflows))
    monkeypatch.setattr(svc2, "_load_supabase", lambda: None)
    monkeypatch.setattr(svc2, "_save", lambda: None)
    svc2._load()
    assert [w.name for w in svc2._workflows.values()] == ["Legacy One"]'''
assert old in src
src = src.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(src)
print("cascade test aligned with production flow")
