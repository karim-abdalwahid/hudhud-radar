"""Audit critical Vercel env values (lengths only — no secrets printed)."""
import os

from dotenv import load_dotenv

load_dotenv(".vercel/.env.production", override=True)

CRITICAL = [
    "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY",
    "META_APP_ID", "META_APP_SECRET", "META_PAGE_ACCESS_TOKEN",
    "META_INSTAGRAM_ACCOUNT_ID", "META_PAGE_ID", "META_WEBHOOK_VERIFY_TOKEN",
    "THREADS_APP_ID", "THREADS_APP_SECRET", "THREADS_REDIRECT_URI",
    "GEMINI_API_KEY", "LLM_MODEL", "CRON_SECRET", "SECRET_KEY", "APP_ENV",
]
print("=== Vercel production env audit ===")
for k in CRITICAL:
    v = os.getenv(k)
    if v is None:
        print(f"  ❌ {k}: MISSING")
    elif v == "":
        print(f"  ❌ {k}: EMPTY")
    else:
        print(f"  ✓ {k}: set ({len(v)} chars, prefix {v[:6]}…)")
