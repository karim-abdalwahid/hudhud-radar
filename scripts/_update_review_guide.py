"""Update META_APP_REVIEW_GUIDE.md with current status (hudhd.com + verified)."""
from pathlib import Path

P = Path("PROJECT_BRAIN/Roadmap/META_APP_REVIEW_GUIDE.md")
c = P.read_text(encoding="utf-8")

c = c.replace(
    "✅ Privacy Policy حية: `https://hudhud-radar.vercel.app/privacy`",
    "✅ Privacy Policy حية: `https://www.hudhd.com/privacy` (ثنائية EN/AR)")
c = c.replace(
    "✅ Data Deletion: صفحة `https://hudhud-radar.vercel.app/data-deletion` + callback API",
    "✅ Data Deletion: صفحة `https://www.hudhd.com/data-deletion` + callback موقّع fail-closed")

STATUS = """
---

## ⚡ الحالة الحالية (سبتمبر 2026 — قبل التقديم)

| المتطلب | الحالة |
|---|---|
| Business Verification | ✅ مكتمل |
| Tech Provider (Access Verification) | ✅ **معتمد — SaaS Platform** (Entry 036) |
| Privacy Policy (دون تسجيل دخول) | ✅ `https://www.hudhd.com/privacy` |
| Data Deletion (صفحة + callback موقّع) | ✅ `https://www.hudhd.com/data-deletion` |
| Webhooks callback موحد على hudhd.com | ✅ (`APP_BASE_URL` مصدر وحيد) |
| جاهز للتقديم | ✅ **كل شيء جاهز — نفّذ الدفعات أدناه** |

> ملاحظة S-Purge (Entry 035): المنصة محايدة تماماً — لا بيزنس شخصي في الواجهات/النصوص، وهذا يقوّي الـ Review.

## 2. ما أنجزناه بالفعل (متطلبات جاهزة)"""

c = c.replace("## 2. ما أنجزناه بالفعل (متطلبات جاهزة)", STATUS, 1)
P.write_text(c, encoding="utf-8")
print("guide updated with current status")
