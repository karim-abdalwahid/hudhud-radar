import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "audit_500_hunter.py"
src = open(p, encoding="utf-8").read()
extra = '''

# ---- write-methods with malformed UUID segments (phase A2) ----
BAD = "not-a-uuid"
add("credits bad uuid", "post", f"/api/admin/users/{BAD}/credits",
    json.dumps({"amount": 5}).encode(), {"Content-Type": "application/json"})
add("plan bad uuid", "post", f"/api/admin/users/{BAD}/plan",
    json.dumps({"plan": "starter"}).encode(), {"Content-Type": "application/json"})
add("patch user bad uuid", "patch", f"/api/admin/users/{BAD}",
    json.dumps({"is_active": False}).encode(), {"Content-Type": "application/json"})
add("notification read bad uuid", "post", f"/api/notifications/{BAD}/read")
add("coupon delete bad uuid", "delete", f"/api/admin/billing/coupons/{BAD}")
add("model toggle bad uuid", "post", f"/api/ai/models/{BAD}/toggle")
add("provider sync bad uuid", "post", f"/api/ai/providers/{BAD}/sync")
add("queue approve bad uuid", "post", f"/api/identity/queue/{BAD}/approve")
add("content delete bad uuid", "delete", f"/api/content/posts/{BAD}")
add("billing sub bad uuid", "post", f"/api/billing/subscription/{BAD}/cancel")
'''
marker = "# ==================================================================="
assert marker in src
src = src.replace(marker, extra + "\n" + marker, 1)
open(p, "w", encoding="utf-8").write(src)
print("hunter extended with write-method cases")
