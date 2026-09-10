"""
Meta App Review — missing API test calls (permissions NOT "Completed" on dashboard).

Dashboard status (round 2, "Testing in progress"):
  pages_utility_messaging          0 of 1 API call(s) required  ← CRITICAL (0 calls)
  Human Agent                      0 API test call(s)           ← CRITICAL (0 calls)
  Business Asset User Profile Access   35 API test call(s)
  instagram_manage_messages           157 API test call(s)
  email                               147 API test call(s)  (user-level, OAuth flow)
  public_profile                      711 API test call(s)  (user-level + page /me)
  pages_show_list                    5007 API test call(s)  (user-level, /me/accounts)

The two ZERO permissions only register usage on POST /{page-id}/messages
(a real send) — GET /conversations does NOT credit them.

Run:
  python scripts/test_missing_meta_permissions.py            # read-only inventory
  python scripts/test_missing_meta_permissions.py --send     # + real sends (1 msg each)

Requires META_PAGE_ACCESS_TOKEN + META_PAGE_ID (+ META_INSTAGRAM_ACCOUNT_ID) in .env.
"""
import sys
from pathlib import Path

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SEND = "--send" in sys.argv


def env(k):
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(k + "="):
            return line.split("=", 1)[1].strip()


def main():
    token = env("META_PAGE_ACCESS_TOKEN") or ""
    page_id = env("META_PAGE_ID") or ""
    ig_id = env("META_INSTAGRAM_ACCOUNT_ID") or ""
    graph = env("META_GRAPH_API_BASE_URL") or "https://graph.facebook.com/v26.0"

    if not token or token.startswith("your-"):
        print("META_PAGE_ACCESS_TOKEN not configured in .env")
        sys.exit(1)

    results = []

    def report(name, permission, status, ok, err="", note=""):
        results.append((name, permission, ok))
        icon = "✅" if ok else "❌"
        line = f"  {icon} {name} [{permission}] → {status}"
        if err:
            line += f"  {err}"
        if note:
            line += f"  ({note})"
        print(line)

    def get(name, permission, url, params, note=""):
        try:
            r = httpx.get(url, params=params, timeout=30)
            err = ""
            if r.status_code != 200:
                try:
                    err = r.json().get("error", {}).get("message", "")[:150]
                except Exception:
                    err = r.text[:150]
            report(name, permission, r.status_code, r.status_code == 200, err, note)
            return r.json() if r.status_code == 200 else None
        except Exception as e:
            report(name, permission, "EXC", False, str(e)[:150], note)
            return None

    def post(name, permission, url, data, note=""):
        try:
            r = httpx.post(url, data=data, timeout=30)
            err = ""
            if r.status_code != 200:
                try:
                    err = r.json().get("error", {}).get("message", "")[:150]
                except Exception:
                    err = r.text[:150]
            report(name, permission, r.status_code, r.status_code == 200, err, note)
            return r.json() if r.status_code == 200 else None
        except Exception as e:
            report(name, permission, "EXC", False, str(e)[:150], note)
            return None

    base = f"{graph}/{page_id}"
    print(f"\n=== Missing-permission test calls — Page {page_id} (send={SEND}) ===\n")

    # ── token sanity ──
    me = get("GET /me (token identity)", "public_profile", f"{graph}/me",
             {"fields": "id,name", "access_token": token})
    if not me:
        print("\nToken invalid/expired — refresh META_PAGE_ACCESS_TOKEN in .env first.")
        sys.exit(1)
    print(f"     page identity: {me.get('name')} ({me.get('id')})\n")

    # ── 1. pages_show_list (user-level: exercised by GET /me/accounts with USER token;
    #    page token can only confirm its own page — real counts come from user connect flows) ──
    get("GET /{page} (page node — show_list corroboration)", "pages_show_list",
        f"{graph}/{page_id}", {"fields": "id,name,category,link", "access_token": token},
        note="main counts arrive via user OAuth /me/accounts")

    # ── 2. Business Asset User Profile Access — read conversation participants ──
    convs = get("GET /{page}/conversations + participants", "business_asset_user_profile_access",
                f"{base}/conversations",
                {"fields": "id,updated_time,participants,unread_count", "limit": 10,
                 "access_token": token},
                note="participant profile read = BUPA usage")
    conv_list = (convs or {}).get("data", [])
    print(f"     conversations found: {len(conv_list)}")

    # newest conversation = send target for the ZERO-permission messaging calls
    target = None
    if conv_list:
        target = conv_list[0]
        psid = None
        for p in target.get("participants", {}).get("data", []):
            # participants include the page itself — pick the non-page one (the customer)
            if p.get("id") != page_id and p.get("email") != "":
                psid = p.get("id")
                break
        upd = target.get("updated_time", "?")
        print(f"     newest conversation: {target.get('id')} updated {upd} → PSID {psid}")

    # ── 3. instagram_manage_messages — IG conversations via page node ──
    get("GET /{page}/conversations?platform=instagram", "instagram_manage_messages",
        f"{base}/conversations",
        {"platform": "instagram", "fields": "id,updated_time,participants", "limit": 5,
         "access_token": token},
        note="page_id + platform=instagram (ig_id is invalid here)")

    # ── 4. pages_utility_messaging — message_templates edge REQUIRES this
    #    permission (error #200 names it explicitly). GET list is a qualifying
    #    call; --send also creates a real utility template (full manage usage).
    mt = get("GET /{page}/message_templates", "pages_utility_messaging",
             f"{base}/message_templates",
             {"access_token": token},
             note="endpoint requires pages_utility_messaging (Meta error #200)")
    if SEND and mt is not None:
        post("POST /{page}/message_templates (create utility template)",
             "pages_utility_messaging",
             f"{base}/message_templates",
             {"name": "hudhud_test_utility_template",
              "text": "Hello {{user_name}}, your order {{order_number}} status: {{status}}.",
              "category": "UTILITY",
              "access_token": token},
             note="full manage usage")

    # ── 5. Human Agent — beyond-24h replies go through the HUMAN_AGENT tag ──
    if SEND:
        # Dev mode: only app role-holders are messageable (#551 otherwise).
        candidates = []
        seen = set()
        for c in conv_list:
            for p in c.get("participants", {}).get("data", []):
                pid = p.get("id")
                if pid and pid != page_id and pid not in seen:
                    seen.add(pid)
                    candidates.append(pid)
        print(f"\n  candidate PSIDs (newest conversation first): {len(candidates)}")

        psid = None
        for cand in candidates:
            r = post(f"POST /messages tag=HUMAN_AGENT → {cand}", "human_agent",
                     f"{base}/messages",
                     {"recipient": f'{{"id":"{cand}"}}',
                      "messaging_type": "MESSAGE_TAG",
                      "tag": "HUMAN_AGENT",
                      "message": f'{{"text":"Hudhud test — human agent reply check"}}',
                      "access_token": token},
                     note="0-call permission; 7-day tag window")
            if r:
                psid = cand
                break
        if not psid and candidates:
            print("\n  ⚠️ No messageable PSID / tag approval yet — details above.")
    else:
        print("\n  ℹ️ human_agent needs a real HUMAN_AGENT-tagged send (--send).")

    # ── summary ──
    print("\n=== SUMMARY ===")
    ok = sum(1 for r in results if r[2])
    print(f"{ok}/{len(results)} calls succeeded")
    print("\nUser-level permissions (email/public_profile/pages_show_list) accumulate")
    print("counts via the app's OAuth connect flow — their existing counts (147/711/5007)")
    print("are generated when users connect their accounts.")
    print("\nKEY: the .env page token must carry pages_utility_messaging + human_agent")
    print("scopes. If GET /message_templates fails with #200, re-connect the Page from")
    print("Settings (scopes list updated in settings.html) — then re-run this script.")


if __name__ == "__main__":
    main()
