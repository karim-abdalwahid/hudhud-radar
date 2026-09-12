import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
addition = '''

## 2️⃣8️⃣ استكمال إثبات الحقيقة للمنصات الثلاث (طلب المالك: "نفس المشكلة كانت فيهم")
- **Instagram round-trip حي**: Studio publish (container flow) → media id `17980390685898162` **مقروء على Graph مع permalink عام** → حذف من التطبيق `meta_deleted.instagram:true` → Graph يؤكد الاختفاء ✅
- **Threads round-trip حي**: نشر → نص المنشور مقروء → حذف `deleted_id` → غائب ✅
- **Facebook** (سابقًا): permalink → delete → gone ✅
- تنويه موثق: تحذيرات decrypt المحلية = SECRET_KEY مختلف بيئتيًا (الإنتاج يفك تشفير صفوفه بنفسه) — سلوك سليم وليس خللًا.
- 293/293 · commit 4ab4ebf.'''
open("docs/PROJECT_REPORTS/SESSION_LOGS/2026-09-11_session.md", "a", encoding="utf-8").write(addition)
addition2 = '''

### 22. Post-Entry Addition — all 3 platforms PROVEN publish+delete REAL (live round-trips)
- IG permalink proof + Threads + FB all: publish->Graph-live-read->app-delete->Graph-confirms-gone. commit 4ab4ebf. 293/293.'''
open("PROJECT_MEMORY.md", "a", encoding="utf-8").write(addition2)
print("logged")
