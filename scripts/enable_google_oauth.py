"""Enable Google OAuth provider in Supabase Auth via Management API.

SECURITY: credentials now come from environment variables — never hardcoded.
NOTE: this Supabase-hosted flow is LEGACY; the app now uses the direct
backend Google OAuth (/auth/google). This script remains only for managing
the Supabase Auth config.
"""
import sys

import httpx
import os

TOKEN = os.environ.get("SUPABASE_MANAGEMENT_TOKEN", "")
REF = os.environ.get("SUPABASE_PROJECT_REF", "")
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")


def main():
    if not TOKEN or not REF or not CLIENT_ID or not CLIENT_SECRET:
        print("Set SUPABASE_MANAGEMENT_TOKEN, SUPABASE_PROJECT_REF, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET env vars first.")
        sys.exit(1)
    body = {
        "external_google_enabled": True,
        "external_google_client_id": CLIENT_ID,
        "external_google_secret": CLIENT_SECRET,
        "site_url": os.environ.get("APP_BASE_URL", "https://hudhud-radar.vercel.app"),
        "redirect_allow_list": [
            os.environ.get("APP_BASE_URL", "https://hudhud-radar.vercel.app") + "/**",
            "http://localhost:8000/**",
        ],
    }
    r = httpx.put(
        f"https://api.supabase.com/v1/projects/{REF}/config/auth",
        headers=H, json=body, timeout=60,
    )
    print("Config auth:", r.status_code, r.text[:300] if r.text else "OK")
    # Verify
    r2 = httpx.get(f"https://api.supabase.com/v1/projects/{REF}/config/auth", headers=H, timeout=30)
    if r2.status_code == 200:
        d = r2.json()
        print("google enabled:", d.get("external_google_enabled"))
        print("site_url:", d.get("site_url"))


if __name__ == "__main__":
    main()
