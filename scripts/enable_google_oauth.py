"""Enable Google OAuth provider in Supabase Auth via Management API."""
import sys

import httpx

TOKEN = "sbp_fc6bd018f43733b522f2326ecac2b54e8ce20e7f"
REF = "yncxwcvxssvnjffrvxib"
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

CLIENT_ID = "963263901125-6pgblcislp00kf47epv4dbkupdejacag.apps.googleusercontent.com"
CLIENT_SECRET = "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"


def main():
    body = {
        "external_google_enabled": True,
        "external_google_client_id": CLIENT_ID,
        "external_google_secret": CLIENT_SECRET,
        "site_url": "https://hudhud-radar.vercel.app",
        "redirect_allow_list": [
            "https://hudhud-radar.vercel.app/**",
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
