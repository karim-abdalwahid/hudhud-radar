"""
One-time migration: mark DEV-SIM-era messages with fabricated receipts.

Before the zero-fabrication hardening (Entry 026), missing Meta tokens made
the client return fake message ids (`mid.simulated.*` / `ig.mid.simulated.*`)
while logging "success". Those rows are honest conversation content written
by our own fallback — but their delivery receipts are NOT real Meta sends.

This script flags them in `messages.metadata.simulated = true` (data is
NEVER deleted) and appends one honest correction entry to activity_logs.

Usage:
    python scripts/migrate_simulated_messages.py            # dry-run count
    python scripts/migrate_simulated_messages.py --apply    # apply marking
"""
import json
import os
import sys

import httpx

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

H = {"apikey": SERVICE_KEY, "Authorization": f"Bearer {SERVICE_KEY}",
     "Content-Type": "application/json", "Prefer": "return=representation"}


def main():
    apply = "--apply" in sys.argv
    if not SUPABASE_URL or not SERVICE_KEY:
        print("Set SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY first.")
        sys.exit(1)

    with httpx.Client(timeout=30) as c:
        r = c.get(f"{SUPABASE_URL}/rest/v1/messages",
                  params={"platform_message_id": "not.is.null",
                          "select": "id,platform_message_id,sender_type,metadata"},
                  headers=H)
        rows = r.json() if r.status_code == 200 else []
        targets = [m for m in rows if m.get("platform_message_id") and "mid.simulated" in m["platform_message_id"]]

        print(f"Messages with receipts: {len(rows)}")
        print(f"Simulated-receipt messages found: {len(targets)}")
        for m in targets[:10]:
            print(f"  - {m['id']} | {m['platform_message_id']} | sender={m['sender_type']}")

        if not targets:
            print("Nothing to mark.")
            return
        if not apply:
            print("DRY-RUN — rerun with --apply to mark these rows.")
            return

        marked = 0
        for m in targets:
            meta = m.get("metadata") or {}
            if meta.get("simulated"):
                continue
            meta.update({
                "simulated": True,
                "simulated_note": "Historical DEV-SIM receipt — no real Meta send occurred (pre-hardening era)",
            })
            r2 = c.patch(f"{SUPABASE_URL}/rest/v1/messages",
                         params={"id": f"eq.{m['id']}"},
                         headers=H,
                         content=json.dumps({"metadata": meta}))
            if r2.status_code in (200, 204):
                marked += 1
            else:
                print(f"  PATCH failed for {m['id']}: {r2.status_code} {r2.text[:150]}")

        # Honest audit-trail entry for the correction itself
        c.post(f"{SUPABASE_URL}/rest/v1/activity_logs", headers=H, content=json.dumps({
            "action_type": "data_correction_migration",
            "platform": "system",
            "target_id": f"messages:{marked}",
            "status": "success",
            "details": {
                "marked_simulated": marked,
                "total_scanned": len(rows),
                "note": "Marked pre-hardening simulated delivery receipts; no rows deleted",
            },
        }))

        print(f"Marked {marked}/{len(targets)} messages as simulated. Audit entry appended.")


if __name__ == "__main__":
    main()
