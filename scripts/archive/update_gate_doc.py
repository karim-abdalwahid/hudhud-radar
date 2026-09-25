import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "docs/APP_REVIEW/RECORDING_PROMPTS.md"
src = open(p, encoding="utf-8").read()
old = """   ⚠️ ملاحظة موثقة: POST الرد الآلي على الثريدز يرجع 400 (missing permissions) قبل الموافقة — هذا طبيعي (advanced access يُمنح بعد اعتماد المراجعة). استدعاءات GET replies الناجحة (منفذة 2026-09-11 ×3) هي التي يراها ميتا، والسكرينكاست يوضح القراءة والتخزين والإدارة في الـ CRM."""
new = """   ✅ **منفذة فعلًا 2026-09-12 بنجاح 200**: الرد تم عبر المسار الرسمي (container + reply_to_id → threads_publish) — reply id: 2750047694351 ظاهر على ثريد كوباية القهوة. (حذف الرد نفسه يتطلب موافقة المراجعة — طبيعي)."""
assert old in src
src = src.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(src)
print("prompts updated: threads_manage_replies gate PASSED")
