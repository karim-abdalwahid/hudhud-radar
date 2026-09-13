"""Final consolidated layer: cleanup AUDIT leftovers, corrected re-run of the 3
smoke scenarios, and Layer 6 frontend<->backend contract key verification."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from playwright.sync_api import sync_playwright
from src.core.supabase_client import supabase_db

B = "http://localhost:8000"
out = []

# ---------- cleanup leftovers ----------
print("=== cleanup leftovers ===")
for w in supabase_db.select("automations_workflows") or []:
    if "AUDIT" in (w.get("name") or ""):
        supabase_db.delete("automations_workflows", w["id"])
        print("  removed automation", w["id"])
removed_notifs = 0
for n in (supabase_db.select("notifications") or []):
    if (n.get("title") or "").startswith("AUDIT"):
        supabase_db.delete("notifications", n["id"])
        removed_notifs += 1
print(f"  removed {removed_notifs} AUDIT notifications")

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context().new_page()
    pg.goto(f"{B}/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=15000)

    def r200(name, r, pred=lambda x: 200 <= x.status < 300):
        out.append((name, r.status, "OK" if pred(r) else "FAIL"))

    # corrected coupons with right payload then delete
    r = pg.request.post(B + "/api/admin/billing/coupons",
                        data={"code": "AUDITX1", "kind": "percent", "value": 5})
    cid = None
    try:
        j = r.json()
        cid = (j.get("coupon") or {}).get("id") or j.get("id")
    except Exception:
        pass
    out.append(("POST /admin/billing/coupons (valid payload)", r.status, "OK" if 200 <= r.status < 300 and cid else f"FAIL {r.text()[:120]}"))
    if cid:
        rd = pg.request.delete(B + f"/api/admin/billing/coupons/{cid}")
        out.append(("DELETE coupon (cleanup)", rd.status, "OK" if 200 <= rd.status < 300 else "FAIL"))
    r = pg.request.get(B + "/api/billing/quote?platforms=facebook")
    out.append(("GET /billing/quote?platforms=facebook", r.status, "OK" if 200 <= r.status < 300 else f"FAIL {r.text()[:120]}"))
    # single-call deletes with gone-checks
    wid = None
    r = pg.request.post(B + "/api/automations", data={"name": "AUDIT prune test", "platform": "both"})
    wid = (r.json().get("workflow") or {}).get("id")
    r = pg.request.delete(B + f"/api/automations/{wid}")
    out.append(("DELETE /automations (single)", r.status, "OK" if 200 <= r.status < 300 else "FAIL"))
    # verify prune actually removed it from the TABLE
    row = [w for w in (supabase_db.select("automations_workflows") or []) if w["id"] == wid]
    out.append(("automation row pruned from DB table", "-", "OK" if not row else f"FAIL still-present"))
    # second delete now 404
    r2 = pg.request.delete(B + f"/api/automations/{wid}")
    out.append(("re-delete -> 404 (true deletion)", r2.status, "OK" if r2.status == 404 else f"FAIL {r2.status}"))

    # ---------- Layer 6: contract keys ----------
    expectations = {
        "/api/inbox/conversations": ["conversations"],
        "/api/meta/status": ["configured"],
        "/api/admin/overview": ["users_total", "leads_total"],
        "/api/admin/traffic": ["by_path"],
        "/api/admin/users": ["users"],
        "/api/automations": ["workflows"],
        "/api/knowledge/documents": ["documents"],
        "/api/ai/models": ["models"],
        "/api/ai/pause": ["effective_paused"],
        "/api/analytics/summary": ["operations", "leads_and_conversions"],
        "/api/studio/posts": None,  # list
        "/api/notifications": ["unread"],
        "/api/connections": None,
        "/api/billing/catalog-public": None,
    }
    for ep, keys in expectations.items():
        r = pg.request.get(B + ep)
        try:
            j = r.json()
        except Exception:
            out.append((f"CONTRACT {ep}", r.status, "FAIL not-json"))
            continue
        if keys is None:
            good = isinstance(j, (list, dict))
        else:
            good = all(k in j for k in keys)
        out.append((f"CONTRACT {ep}", r.status, "OK" if good else f"FAIL missing:{[k for k in (keys or []) if isinstance(j,dict) and k not in j]}"))
    b.close()

print(f"\n{'CHECK':<46} {'HTTP':<6} VERDICT")
for n, c, v in out:
    print(f"{str(n):<46} {str(c):<6} {v}")
bad = [o for o in out if "FAIL" in o[2]]
print(f"\nTOTAL {len(out)} | FAILS {len(bad)}")
