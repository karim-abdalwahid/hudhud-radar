"""
Full, reliable Vercel env sync from local .env (source of truth).
Uses subprocess with clean stdin (no PowerShell pipe corruption).

Usage: python scripts/sync_vercel_env.py
"""
import os
import subprocess
import sys

from dotenv import load_dotenv

load_dotenv(override=True)

# Values that differ intentionally between local and production
OVERRIDES = {
    "APP_ENV": "production",
    "APP_DEBUG": "false",
}
# Local-only keys that must NOT go to Vercel
SKIP = {"HOST", "PORT", "APP_DEBUG", "NX_DAEMON", "VERCEL", "VERCEL_ENV"}

VERCEL_CMD = os.path.expandvars(r"%APPDATA%\npm\vercel.cmd")
if not os.path.exists(VERCEL_CMD):
    VERCEL_CMD = "vercel.cmd" if sys.platform == "win32" else "vercel"


def set_env(key: str, value: str) -> bool:
    subprocess.run(
        [VERCEL_CMD, "env", "rm", key, "production", "--yes"],
        capture_output=True, text=True, timeout=120,
    )
    r = subprocess.run(
        [VERCEL_CMD, "env", "add", key, "production"],
        input=value, text=True, capture_output=True, timeout=120,
    )
    return r.returncode == 0


def main():
    # Collect all keys from .env
    env: dict = {}
    with open(".env", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = v.strip().strip('"').strip("'")
            if v:
                env[k.strip()] = v

    print(f"Source .env: {len(env)} keys")
    uploaded = 0
    failed = []
    for k in sorted(env):
        if k in SKIP:
            continue
        value = OVERRIDES.get(k, env[k])
        if set_env(k, value):
            uploaded += 1
            print(f"  ✓ {k}")
        else:
            failed.append(k)
            print(f"  ✗ {k}")

    print(f"\nUploaded: {uploaded}/{len([k for k in env if k not in SKIP])}")
    if failed:
        print("FAILED:", ", ".join(failed))
        sys.exit(2)
    print("\n⚠️  Redeploy required: vercel --prod")


if __name__ == "__main__":
    main()
