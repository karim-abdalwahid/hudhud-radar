"""
Definitive domain fix via Vercel REST API (no CLI scope confusion):
1. Find & delete the orphaned alias hudhud-radar.vercel.app (owned by old 'hudhud' project deployment)
2. Point it to the LATEST production deployment of hudhud-radar project
3. Re-create the steel alias (accidentally removed)
"""
import json
import os

import httpx

TOKEN_FILE = os.path.expandvars(r"%LOCALAPPDATA%\com.vercel.cli\auth.json")

PROJECT_ID = "prj_yxGldzs2buJhSxS6MFdDm6K6zZtB"
TEAM_ID = "team_pxVxcLPcF22yie3cC4lxSax3"


def get_token() -> str:
    with open(TOKEN_FILE, encoding="utf-8") as f:
        data = json.load(f)
    # auth.json format: {"token": "..."} or {"user": {...}, "token": "..."}
    return data.get("token") or data.get("data", {}).get("token", "")


def main():
    token = get_token()
    if not token:
        print("❌ No CLI token found at", TOKEN_FILE)
        sys_exit = 1
        return
    H = {"Authorization": f"Bearer {token}"}
    qs = f"?teamId={TEAM_ID}"

    with httpx.Client(timeout=60) as c:
        # 1. List all aliases for the team
        r = c.get(f"https://api.vercel.com/v4/aliases{qs}", headers=H)
        aliases = r.json().get("aliases", [])
        target = [a for a in aliases if a.get("alias") == "hudhud-radar.vercel.app"]
        print(f"Found {len(aliases)} total aliases; hudhud-radar.vercel.app matches: {len(target)}")
        for a in target:
            print("  alias id:", a["uid"], "→ deployment:", a.get("deployment", {}).get("id"))
            # 2. Delete the orphaned alias
            d = c.delete(f"https://api.vercel.com/v2/alias/{a['uid']}{qs}", headers=H)
            print("  delete:", d.status_code, d.text[:120] if d.text else "OK")

        # 3. Get latest production deployment of hudhud-radar
        r2 = c.get(
            f"https://api.vercel.com/v6/deployments{qs}",
            headers=H,
            params={"projectId": PROJECT_ID, "target": "production", "limit": 1, "state": "READY"},
        )
        deps = r2.json().get("deployments", [])
        if not deps:
            print("❌ No production deployment found")
            return
        latest = deps[0]
        dep_id = latest["uid"]
        dep_url = latest.get("url")
        print(f"Latest prod deployment: {dep_id} ({dep_url})")

        # 4. Alias it to hudhud-radar.vercel.app + steel
        for alias in ["hudhud-radar.vercel.app", "hudhud-radar-steel.vercel.app"]:
            r3 = c.post(
                f"https://api.vercel.com/v2/deployments/{dep_id}/aliases{qs}",
                headers=H,
                json={"alias": [alias]},
            )
            print(f"alias {alias}:", r3.status_code, r3.text[:150] if r3.text else "OK")


if __name__ == "__main__":
    main()
