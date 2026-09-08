"""
Platform adapter contract tests (WS0.2).
Registry-driven platform access: capability gating, honest status, clean
NotImplementedError for unsupported operations.
"""
import pytest


def test_registry_has_expected_platforms():
    from src.platforms.registry import supported_platforms, get_adapter
    assert set(supported_platforms()) == {"facebook", "instagram", "threads"}
    for name in supported_platforms():
        a = get_adapter(name)
        assert a is not None and a.name == name


def test_capabilities_gate_behavior():
    from src.platforms.registry import get_adapter
    fb = get_adapter("facebook")
    assert fb.capabilities.messaging and fb.capabilities.publishing
    th = get_adapter("threads")
    assert not th.capabilities.messaging          # Threads has no DM API
    with pytest.raises(NotImplementedError):
        th.send_message("user", "hello")


def test_meta_status_never_raises_and_is_honest(monkeypatch):
    from src.platforms.meta_adapter import MetaPlatformAdapter
    a = MetaPlatformAdapter("facebook", "Facebook Page")
    monkeypatch.setattr("src.core.admin_alerts.collect_alerts",
                        lambda **kw: [{"id": "meta_token", "level": "critical"}])
    st = a.get_status()
    assert st.connected is False


def test_threads_status_maps_real_fields(monkeypatch):
    from src.platforms.threads_adapter import ThreadsPlatformAdapter

    class _Fake:
        def get_status(self):
            return {"configured": True, "connected": True,
                    "username": "real_user", "expires_in_days": 30.0}
    import src.platforms.threads_adapter as mod
    monkeypatch.setattr(mod, "threads_oauth", _Fake())
    st = ThreadsPlatformAdapter().get_status()
    assert st.connected and st.username == "real_user"
    assert st.expires_at is not None
