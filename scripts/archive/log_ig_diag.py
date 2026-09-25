import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
addition = '''

## 3️⃣3️⃣ تشخيص: DM من إنستجرام الشخصي لم يظهر في الإنبوكس
**النتيجة القاطعة**: لا حدث وصل للويب هوك على الإطلاق (processed_events آخر حدث فيسبوك قديم). **طرفنا سليم تمامًا**: محاكاة حدث `object=instagram` موقّعة HMAC على الإنتاج → webhook 200 → ليد src=instagram بـ username → رسالة مخزنة بالنص → الإنبوكس يعرضه. (رد AI لم يُخزن = fail-closed لأن send API لـ IG نفسه محجوب بالصلاحية تحت المراجعة — سلوك صادق.)
**العند الآخر**: `POST /{IG_ID}/subscribed_apps` → خطأ #3 "Application does not have the capability" = اشتراك ويبهوكات إنستجرام يتطلب `instagram_manage_messages` (Advanced Access — تحت المراجعة الآن).
**خطة المالك**: 1) انتظار اعتماد المراجعة (المسار الرئيسي، وبعدها الاشتراك/API يتفعلان) 2) الآن في الداشبورد: Messenger → إعدادات → ربط حساب إنستجرام @karim__abdalwahid بحقل Messages في ويبهوكاته (قد يفعّل تسليم وضع التطوير) 3) إضافة حساب المالك الشخصي Tester في Roles.
**تنظيف**: evt-x leftover من الاختبارات أُزيل + كل صفوف البروب اندفعت. أدوات: diag_ig_dm.py / try_ig_subscribe.py / test_ig_pipeline_e2e.py.'''
open("docs/PROJECT_REPORTS/SESSION_LOGS/2026-09-11_session.md", "a", encoding="utf-8").write(addition)
addition2 = '''

### 28. Post-Entry Addition — IG DM delivery diagnosis
- Site side PROVEN working (signed instagram-object event -> lead+message via prod webhook). Delivery gap is Meta-side: IG webhook subscription needs instagram_manage_messages capability (pending review; subscribed_apps returns error #3). Owner checklist logged (dashboard IG connect + tester role + await approval). Probe leftovers cleaned.'''
open("PROJECT_MEMORY.md", "a", encoding="utf-8").write(addition2)
print("logged")
