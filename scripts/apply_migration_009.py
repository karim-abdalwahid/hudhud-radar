"""Apply migration 009 (billing & entitlements) to production Supabase."""
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent


def env(k):
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(k + "="):
            return line.split("=", 1)[1].strip()


def main():
    token = env("SUPABASE_MANAGEMENT_TOKEN")
    ref = env("SUPABASE_PROJECT_REF")
    sql = (ROOT / "database" / "migrations" / "009_billing_entitlements.sql").read_text(encoding="utf-8")
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    with httpx.Client(timeout=90) as c:
        r = c.post(f"https://api.supabase.com/v1/projects/{ref}/database/query",
                   headers=h, json={"query": sql})
        print("migration 009:", r.status_code, "OK ✅" if r.status_code in (200, 201) else r.text[:400])
        # verify
        r2 = c.post(f"https://api.supabase.com/v1/projects/{ref}/database/query",
                    headers=h,
                    json={"query": "SELECT table_name FROM information_schema.tables WHERE table_name IN ('user_subscriptions','user_entitlements','payment_events','usage_events','coupons','coupon_redemptions','platform_addons_catalog') ORDER BY table_name"})
        print("tables:", r2.text)
        r3 = c.post(f"https://api.supabase.com/v1/projects/{ref}/database/query",
                    headers=h,
                    json={"query": "SELECT platform, price_usd FROM platform_addons_catalog ORDER BY sort_order"})
        print("catalog:", r3.text)


if __name__ == "__main__":
    main()
