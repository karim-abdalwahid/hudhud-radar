"""Revoke anon from leads (missed by the split parser) + verify."""
import os
import httpx

TOKEN = os.environ.get("SUPABASE_MANAGEMENT_TOKEN", "")
REF = "yncxwcvxssvnjffrvxib"
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def main():
    with httpx.Client(timeout=60) as client:
        r = client.post(
            f"https://api.supabase.com/v1/projects/{REF}/database/query",
            headers=H, json={"query": "REVOKE ALL ON public.leads FROM anon;"},
        )
        print("Revoke leads:", r.status_code, r.text[:120] if r.text else "OK")

        q = "SELECT table_name, privilege_type FROM information_schema.role_table_grants WHERE table_schema='public' AND grantee='anon' ORDER BY table_name;"
        r2 = client.post(
            f"https://api.supabase.com/v1/projects/{REF}/database/query",
            headers=H, json={"query": q},
        )
        rows = r2.json()
        print("Remaining anon grants:", rows if rows else "NONE — all clean ✓")


if __name__ == "__main__":
    main()
