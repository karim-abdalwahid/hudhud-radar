"""Insert all missing i18n keys into EN and AR dictionaries of i18n.js."""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
P = Path("src/templates/static/i18n.js")

EN = {
    "back_home": "Back to",
    "home": "Home",
    "cc_search_ph": "Search by country name or code…",
    "confirm": "Confirm Password",
    "consent_and": "and",
    "consent_prefix": "I agree to the",
    "consent_privacy": "Privacy Policy",
    "consent_required": "Required to create an account.",
    "consent_terms": "Terms of Service",
    "email": "Email",
    "email_ph": "you@example.com",
    "fullname": "Full Name",
    "fullname_ph": "Your full name",
    "google_btn": "Continue with Google",
    "inbox.dossier_contact": "Contact Captured:",
    "login": "Sign In",
    "login_btn": "Sign in to Dashboard",
    "nav.dev_console": "Developer Console",
    "onboard.brain_admin_note": "Models listed are the ones enabled by the platform admin",
    "onboard.no_sub_desc": "You don't have an active subscription or trial. Start a free trial or",
    "onboard.no_sub_title": "No active subscription",
    "onboard.role_custom_ph": "Describe your role…",
    "onboard.role_opt_other": "Other (write your own)",
    "onboard.skip": "Skip for now",
    "onboard.skip_all": "Skip for now — finish setup without connecting",
    "onboard.start_trial": "Start Free Trial (3 days)",
    "onboard.subscribe": "Subscribe to a plan",
    "or": "or",
    "password": "Password",
    "password_hint": "At least 8 characters — a mix of letters and numbers is stronger",
    "password_ph": "••••••••",
    "phone": "Phone Number",
    "phone_hint": "Pick your country and enter your number — stored in full international format",
    "phone_ph": "1X XXXX XXXX",
    "register": "Create Account",
    "register_btn": "Create Account & Sign In",
    "sc.demo.customer": "Sara M.",
    "sc.demo.live": "Live reply",
    "sc.demo.stat1": "Response time",
    "sc.demo.stat2": "Buying intent",
    "sc.demo.stat3": "Coverage",
    "sc.demo.via": "Instagram Direct · Now",
    "sc.headline": "Your AI agent replies to your customers",
    "sc.sub": "Turns Reel comments and DMs into real sales conversations",
    "set.security_desc": "Update your account password anytime — changes are instant and require your current password",
    "set.security_title": "Change Password",
    "set.threads_connect": "Connect Threads Account",
}

AR = {
    "back_home": "العودة إلى",
    "home": "الصفحة الرئيسية",
    "cc_search_ph": "ابحث باسم الدولة أو كود الهاتف…",
    "confirm": "تأكيد كلمة المرور",
    "consent_and": "و",
    "consent_prefix": "أوافق على",
    "consent_privacy": "سياسة الخصوصية",
    "consent_required": "مطلوب لإنشاء الحساب.",
    "consent_terms": "شروط الاستخدام",
    "email": "البريد الإلكتروني",
    "email_ph": "you@example.com",
    "fullname": "الاسم الكامل",
    "fullname_ph": "اسمك الكامل",
    "google_btn": "المتابعة باستخدام Google",
    "inbox.dossier_contact": "بيانات التواصل الملتقطة:",
    "login": "تسجيل الدخول",
    "login_btn": "دخول إلى لوحة التحكم",
    "nav.dev_console": "لوحة المطور",
    "onboard.brain_admin_note": "النماذج المعروضة هي المفعّلة من مسؤول المنصة",
    "onboard.no_sub_desc": "ليس لديك اشتراك أو فترة تجريبية نشطة. ابدأ تجربة مجانية أو",
    "onboard.no_sub_title": "لا يوجد اشتراك نشط",
    "onboard.role_custom_ph": "اكتب دورك الوظيفي…",
    "onboard.role_opt_other": "أخرى (اكتبها بنفسك)",
    "onboard.skip": "تخطَّ الآن",
    "onboard.skip_all": "تخطَّ الآن — أكمل الإعداد بدون ربط",
    "onboard.start_trial": "ابدأ التجربة المجانية (3 أيام)",
    "onboard.subscribe": "اشترك في خطة",
    "or": "أو",
    "password": "كلمة المرور",
    "password_hint": "8 أحرف على الأقل — مزيج حروف وأرقام أقوى",
    "password_ph": "••••••••",
    "phone": "رقم الهاتف",
    "phone_hint": "اختر دولتك واكتب رقمك — يُحفظ بصيغة دولية كاملة",
    "phone_ph": "1X XXXX XXXX",
    "register": "إنشاء حساب",
    "register_btn": "إنشاء الحساب والدخول",
    "sc.demo.customer": "سارة م.",
    "sc.demo.live": "رد حي",
    "sc.demo.stat1": "زمن الرد",
    "sc.demo.stat2": "نية شراء",
    "sc.demo.stat3": "التغطية",
    "sc.demo.via": "إنستجرام دايركت · الآن",
    "sc.headline": "وكيلك الذكي يرد على عملائك",
    "sc.sub": "يحوّل تعليقات الريلز والرسائل إلى محادثات بيع حقيقية",
    "set.security_desc": "حدّث كلمة مرور حسابك في أي وقت — التغيير فوري ويتطلب كلمة المرور الحالية",
    "set.security_title": "تغيير كلمة المرور",
    "set.threads_connect": "ربط حساب Threads",
}


def dump(d):
    return "".join(f'        "{k}": {v!s},\n' for k, v in d.items())


def js_str(v):
    return '"' + v.replace('\\', '\\\\').replace('"', '\\"') + '"'


def block(d):
    return "".join(f'        "{k}": {js_str(v)},\n' for k, v in d.items())


js = P.read_text(encoding="utf-8")

# Insert right after each dictionary opening brace (en: { and ar: {)
en_block = "\n" + block(EN)
ar_block = "\n" + block(AR)

js = re.sub(r"(en\s*:\s*\{)", r"\1" + en_block.replace("\\", "\\\\"), js, count=1)
js = re.sub(r"(ar\s*:\s*\{)", r"\1" + ar_block.replace("\\", "\\\\"), js, count=1)

P.write_text(js, encoding="utf-8")
print("inserted EN keys:", len(EN), "| AR keys:", len(AR))
