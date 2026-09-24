"""Regressions for the final comprehensive audit (this session):
prune, polar List import, meta cache shadow removal, cron defun duplication."""
import ast


def test_automations_save_prunes_removed_rows():
    from src.core.supabase_client import InMemoryDatabase
    from src.automations.models import Workflow
    from src.automations.service import db_save_workflows

    class FakeDB(InMemoryDatabase):
        is_connected = True

    db = FakeDB()
    w1, w2 = Workflow(name="A"), Workflow(name="B")
    db_save_workflows(db, {w1.id: w1, w2.id: w2}, owner_user_id="user-1")
    assert len(db.select("automations_workflows")) == 2
    db_save_workflows(db, {w1.id: w1}, owner_user_id="user-1")  # w2 deleted in memory
    assert len(db.select("automations_workflows")) == 1


def test_polar_typing_complete():
    import src.payments.polar as pol
    assert "List" in dir(pol) or getattr(pol, "List", None) is not None


def test_meta_status_cache_is_shared_with_context():
    import src.modules.meta.routes as mr
    import src.modules.context as ctx
    assert mr._meta_status_cache is ctx._meta_status_cache


def test_cron_secret_single_source():
    import src.modules.cron_admin.routes as cr
    import src.modules.context as ctx
    assert cr._verify_cron_secret is ctx._verify_cron_secret


def test_settings_parity_effective_props_exist():
    from src.config import Settings
    s = Settings()
    assert hasattr(s, "EFFECTIVE_WEBHOOK_VERIFY_TOKEN")
    assert hasattr(s, "EFFECTIVE_THREADS_REDIRECT_URI")
