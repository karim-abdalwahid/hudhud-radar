"""Store the owner's Polar product mapping into production app_settings
(sandbox). One-time setup for Phase 9.2b — live checkout testing."""
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent


def env(k):
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(k + "="):
            return line.split("=", 1)[1].strip()


def main():
    url, key = env("SUPABASE_URL").rstrip("/"), env("SUPABASE_SERVICE_ROLE_KEY")
    h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    mapping = {
        "facebook": "f814fbcb-94bd-41fd-b020-cf1586518ecd",
        "instagram": "04509b5b-b2f5-4f78-87ba-4f11a3d8f712",
        "threads": "8fb7d645-f441-45e5-a178-e2c5fe72fccb",
        "trial-facebook": "1719ac1c-36f9-4956-ab06-2ab29f44ffc4",
        "trial-instagram": "fcb1ff26-bdc6-43d7-b397-744b0824ec9b",
        "trial-threads": "232fc181-c196-436c-84d4-227634822e69",
    }
    with httpx.Client(timeout=30) as c:
        r = c.post(f"{url}/rest/v1/app_settings",
                   headers={**h, "Prefer": "resolution=merge-duplicates"},
                   json={"key": "polar_product_ids", "value": mapping,
                         "updated_at": "2026-09-09T16:30:00Z"})
        print("polar_product_ids stored:", r.status_code)
        r2 = c.get(f"{url}/rest/v1/app_settings?key=eq.polar_product_ids&select=value", headers=h)
        got = r2.json()[0]["value"]
        print("verify keys:", sorted(got.keys()))
        assert len(got) == 6
        print("✅ mapping live on production")


if __name__ == "__main__":
    main()
