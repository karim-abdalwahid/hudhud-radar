"""
Legal module — Terms of Service & Privacy Policy pages.

Bilingual (EN default + AR toggle), honest to actual product behavior:
every claim in these documents maps to a real feature/control in the code
(zero-fabrication applies to legal text too). Replaces the legacy
compliance_pages privacy string (which remains served at /privacy by the
compliance module until this module takes over the route).

Governing law per owner decision: Arab Republic of Egypt — Cairo Economic Courts.
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from src.core.modules import module_registry

LEGAL_VERSION = "2026-09-08"

_ABOUT = {
    "company_en": "Ebd'a Marketing (Hudhud) — Karim Abdalwahid",
    "company_ar": "إبدأ ماركتينج (هدهد) — كريم عبد الواحد",
    "email": "karim@ebdamarketing.com",
    "site": "https://www.hudhd.com",
}

_TERMS_EN = """<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Terms of Service — Hudhud</title>
<link rel="icon" href="/static/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/static/favicon-32.png">
<style>
body{font-family:'Plus Jakarta Sans','Tajawal',system-ui,sans-serif;background:#f8fafc;color:#0f172a;line-height:1.8;margin:0;padding:40px 20px;}
.wrap{max-width:820px;margin:0 auto;background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:48px;}
h1{font-size:28px;margin:0 0 8px;} h2{font-size:18px;margin-top:32px;border-bottom:1px solid #e2e8f0;padding-bottom:8px;}
.meta{color:#64748b;font-size:13px;margin-bottom:24px;} a{color:#2563eb;}
.lang{float:right;} .lang a{font-size:13px;}
</style>
</head>
<body><div class="wrap">
<span class="lang"><a href="/terms?lang=ar">العربية</a> · <a href="/privacy">Privacy Policy</a></span>
<h1>Terms of Service</h1>
<div class="meta">Version {version} · Operator: {company_en} · <a href="mailto:{email}">{email}</a></div>

<h2>1. Introduction</h2>
<p>These Terms of Service ("Terms") govern your access to and use of the Hudhud
platform and website at {site} (the "Service"), operated by {company_en}
("we", "us", "our"). By creating an account or using the Service, you agree to
these Terms. If you do not agree, do not use the Service.</p>

<h2>2. The Service</h2>
<p>Hudhud is a SaaS platform that helps businesses manage customer conversations
and content on their own connected social media accounts. The Service includes:
an AI assistant that replies to customer comments and direct messages on
accounts you connect; lead capture and organization; content creation and
scheduling; and performance analytics.</p>

<h2>3. Accounts and eligibility</h2>
<p>You must provide accurate registration details (a valid email address and,
where requested, a phone number). You are responsible for keeping your
credentials confidential and for all activity under your account. You may stop
using the Service at any time; we may suspend or terminate accounts that
violate these Terms.</p>

<h2>4. Your data and your customers</h2>
<p>The Service works only on social media accounts that <strong>you</strong>
connect through official platform authorizations. You represent that you own
or are authorized to operate every account you connect. Data we process on
your behalf — messages, comments, and contact details customers share with you
— remains yours. We never sell Platform Data. Details are in our
<a href="/privacy">Privacy Policy</a>.</p>

<h2>5. Messaging and platform rules</h2>
<p>Outbound messaging through the Service follows the platforms' official
rules, including Meta's 24-hour standard messaging window, which the Service
enforces by default. You are responsible for the lawfulness of messages sent
from your accounts, including obtaining any consent required for follow-up
messages.</p>

<h2>6. AI features</h2>
<p>AI-generated replies and content are produced by automated models
(including Google's Gemini API) using your own connected-account data and the
knowledge documents you provide. AI output may contain errors — review before
acting on it where accuracy matters. You can pause automatic AI replies for
any conversation at any time using the Human Takeover control.</p>

<h2>7. Billing, trials, and refunds</h2>
<p>Current plans and prices are shown on the website. Where a free trial is
offered (for example, a 14-day trial), it applies to the plan stated at
sign-up and converts only if you confirm a paid subscription. Fees are billed
in advance and are non-refundable except where required by law or stated
otherwise at purchase. We may change prices with reasonable advance notice.</p>

<h2>8. Acceptable use</h2>
<p>You agree not to: use the Service for spam or unsolicited bulk messaging;
send unlawful, misleading, or harmful content; harvest data from platforms in
violation of their terms; impersonate others; reverse engineer or overload the
Service; or use it in a way that violates any applicable law or the rules of
the connected platforms (Meta, Google, Threads).</p>

<h2>9. Intellectual property</h2>
<p>The Service, its software, and its branding are owned by the operator and
its licensors. You keep ownership of content you create through the Service
and of your business data. You grant us only the limited rights needed to
operate the Service for you.</p>

<h2>10. Disclaimers</h2>
<p>The Service is provided "as is" without warranties of any kind, whether
express or implied, including fitness for a particular purpose. We do not
warrant that the Service will be uninterrupted or error-free, and we do not
control third-party platforms whose outages or rule changes may affect the
Service.</p>

<h2>11. Limitation of liability</h2>
<p>To the maximum extent permitted by law, our total liability arising out of
or relating to the Service is limited to the fees you paid us in the three (3)
months before the event giving rise to the claim. We are not liable for
indirect, incidental, special, or consequential damages, or lost profits or
data.</p>

<h2>12. Termination</h2>
<p>You may delete your account and data at any time via the
<a href="/data-deletion">Data Deletion</a> page or by contacting us. We may
terminate or suspend access for material breach of these Terms, or if
required by law or a platform provider. Sections that should survive
termination (including intellectual property, disclaimers, and limitation of
liability) will survive.</p>

<h2>13. Governing law and jurisdiction</h2>
<p>These Terms are governed by the laws of the <strong>Arab Republic of
Egypt</strong>. Any dispute arising out of or relating to these Terms or the
Service shall be subject to the exclusive jurisdiction of the competent
<strong>Cairo Economic Courts, Arab Republic of Egypt</strong>.</p>

<h2>14. Changes to these Terms</h2>
<p>We may update these Terms from time to time. We will post the updated
version on this page with a new version date. Continued use of the Service
after changes are posted constitutes acceptance of the updated Terms.</p>

<h2>15. Contact</h2>
<p>Questions about these Terms: <a href="mailto:{email}">{email}</a>.</p>
</div></body></html>"""

_TERMS_AR = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>شروط الاستخدام — هدهد</title>
<link rel="icon" href="/static/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/static/favicon-32.png">
<style>
body{font-family:'Tajawal','Plus Jakarta Sans',system-ui,sans-serif;background:#f8fafc;color:#0f172a;line-height:1.9;margin:0;padding:40px 20px;}
.wrap{max-width:820px;margin:0 auto;background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:48px;}
h1{font-size:28px;margin:0 0 8px;} h2{font-size:18px;margin-top:32px;border-bottom:1px solid #e2e8f0;padding-bottom:8px;}
.meta{color:#64748b;font-size:13px;margin-bottom:24px;} a{color:#2563eb;}
.lang{float:left;} .lang a{font-size:13px;}
</style>
</head>
<body><div class="wrap">
<span class="lang"><a href="/terms">English</a> · <a href="/privacy">سياسة الخصوصية</a></span>
<h1>شروط الاستخدام</h1>
<div class="meta">الإصدار {version} · المشغّل: {company_ar} · <a href="mailto:{email}">{email}</a></div>

<h2>1. المقدمة</h2>
<p>تحكم شروط الاستخدام هذه وصولك إلى واستخدامك لمنصة هدهد وموقعها {site}
(«الخدمة») التي يُشغّلها {company_ar} («نحن»). بإنشائك حساباً أو استخدامك
الخدمة فإنك توافق على هذه الشروط. إذا لم توافق، فلا تستخدم الخدمة.</p>

<h2>2. الخدمة</h2>
<p>هدهد منصة SaaS تساعد الشركات على إدارة محادثات العملاء والمحتوى على حساباتها
الخاصة التي تربطها بنفسها. تشمل الخدمة: مساعداً ذكياً يرد على تعليقات العملاء
والرسائل على الحسابات التي تربطها، وتنظيم العملاء المحتملين، وإنشاء المحتوى
وجدولته، وتحليلات الأداء.</p>

<h2>3. الحسابات والأهلية</h2>
<p>يجب أن تقدّم بيانات تسجيل صحيحة (بريداً إلكترونياً صالحاً ورقم هاتف عند
الطلب). أنت مسؤول عن سرية بيانات دخولك وعن كل نشاط يتم عبر حسابك. يمكنك
التوقف عن استخدام الخدمة متى شئت، ويحق لنا إيقاف أو إنهاء الحسابات المخالفة
لهذه الشروط.</p>

<h2>4. بياناتك وبيانات عملائك</h2>
<p>تعمل الخدمة فقط على حسابات التواصل الاجتماعي التي <strong>تربطها أنت</strong>
عبر تفويضات المنصات الرسمية. أنت تقرّ بأنك تملك كل حساب تربطه أو مرخّص بتشغيله.
البيانات التي نعالجها نيابةً عنك — الرسائل والتعليقات وبيانات التواصل التي
يشاركها عملاؤك — تبقى ملكك. نحن لا نبيع بيانات المنصات إطلاقاً. التفاصيل في
<a href="/privacy">سياسة الخصوصية</a>.</p>

<h2>5. المراسلة وقواعد المنصات</h2>
<p>الرسائل الصادرة عبر الخدمة تتبع القواعد الرسمية للمنصات، ومنها نافذة
المراسلة القياسية (24 ساعة) من Meta التي تفرضها الخدمة افتراضياً. أنت مسؤول
عن شرعية الرسائل المرسلة من حساباتك، بما في ذلك الحصول على أي موافقات
مطلوبة قانوناً للرسائل اللاحقة.</p>

<h2>6. ميزات الذكاء الاصطناعي</h2>
<p>الردود والمحتوى المولّد آلياً تنتجه نماذج ذكاء اصطناعي (بما فيها واجهة
Gemini من Google) اعتماداً على بيانات حساباتك المتصلة والمستندات التي ترفعها.
قد يحتوي مخرج الذكاء الاصطناعي على أخطاء — راجعه قبل الاعتماد عليه. يمكنك
إيقاف الردود الآلية لأي محادثة متى شئت عبر خاصية «تولّي المحادثة شخصياً».</p>

<h2>7. الفوترة والتجربة والاسترداد</h2>
<p>الخطط والأسعار الحالية معروضة على الموقع. عند توفّر تجربة مجانية (مثل تجربة
14 يوماً) فهي تخص الخطة المعلنة عند التسجيل ولا تتحول لاشتراك مدفوع إلا بعد
تأكيدك. الرسوم تُحصّل مقدماً وغير قابلة للاسترداد إلا إذا طلب القانون ذلك أو
نُصّ على خلافه عند الشراء. قد نغيّر الأسعار بإشعار مسبق معقول.</p>

<h2>8. الاستخدام المقبول</h2>
<p>توافق على ألا تستخدم الخدمة للرسائل المزعجة أو الجماعية غير المرغوبة، أو
إرسال محتوى غير قانوني أو مضلل أو ضار، أو حصاد بيانات المنصات بما يخالف
شروطها، أو انتحال شخصيات، أو هندسة عكسية أو إثقال الخدمة، أو أي استخدام يخالف
القانون أو قواعد المنصات المتصلة (Meta وGoogle وThreads).</p>

<h2>9. الملكية الفكرية</h2>
<p>الخدمة وبرمجياتها وهوية علامتها مملوكة للمشغّل ومرخّصيه. تبقى أنت مالكاً
للمحتوى الذي تنشئه عبر الخدمة ولبيانات نشاطك التجاري. لا نمنح أنفسنا سوى
الحقوق المحدودة اللازمة لتشغيل الخدمة لصالحك.</p>

<h2>10. إخلاء الضمان</h2>
<p>تُقدَّم الخدمة «كما هي» دون أي ضمانات صريحة أو ضمنية، بما فيها الملاءمة
لغرض معين. لا نضمن خلو الخدمة من الانقطاع أو الأخطاء، ولا نتحكم في المنصات
الخارجية التي قد يؤثر انقطاعها أو تغيّر قواعدها على الخدمة.</p>

<h2>11. حدود المسؤولية</h2>
<p>إلى أقصى حد يسمح به القانون، لا يتجاوز إجمالي مسؤوليتنا عن أي مطالبة
متعلقة بالخدمة الرسوم التي دفعتها لنا خلال ثلاثة (3) أشهر السابقة للحدث،
ولا نتحمل مسؤولية عن الأضرار غير المباشرة أو التبعية أو الأرباح أو البيانات
الفقيدة.</p>

<h2>12. الإنهاء</h2>
<p>يمكنك حذف حسابك وبياناتك في أي وقت عبر صفحة <a href="/data-deletion">حذف
البيانات</a> أو بالتواصل معنا. يحق لنا إنهاء أو إيقاف الوصول عند المخالفة
الجسيمة لهذه الشروط أو إذا طلبت ذلك جهة قانونية أو إحدى المنصات. تبقى
الأقسام التي يتعين بقاؤها سارية بعد الإنهاء (الملكية الفكرية وإخلاء الضمان
وحدود المسؤولية).</p>

<h2>13. القانون الحاكم والاختصاص القضائي</h2>
<p>تخضع هذه الشروط لقوانين <strong>جمهورية مصر العربية</strong>، وتُخصَّص أي
نزاعات تنشأ عنها أو عن الخدمة للمحاكم <strong>الاقتصادية بالقاهرة — جمهورية
مصر العربية</strong> اختصاصاً حصرياً.</p>

<h2>14. تعديل الشروط</h2>
<p>قد نحدّث هذه الشروط من وقت لآخر، وننشر النسخة المحدثة على هذه الصفحة مع
تاريخ إصدار جديد. ويُعد استمرارك في استخدام الخدمة بعد نشر التعديلات موافقة
عليها.</p>

<h2>15. التواصل</h2>
<p>لأي استفسار حول هذه الشروط: <a href="mailto:{email}">{email}</a>.</p>
</div></body></html>"""

_PRIVACY_EN = """<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Privacy Policy — Hudhud</title>
<link rel="icon" href="/static/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/static/favicon-32.png">
<style>
body{font-family:'Plus Jakarta Sans','Tajawal',system-ui,sans-serif;background:#f8fafc;color:#0f172a;line-height:1.8;margin:0;padding:40px 20px;}
.wrap{max-width:820px;margin:0 auto;background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:48px;}
h1{font-size:28px;margin:0 0 8px;} h2{font-size:18px;margin-top:32px;border-bottom:1px solid #e2e8f0;padding-bottom:8px;}
.meta{color:#64748b;font-size:13px;margin-bottom:24px;} a{color:#2563eb;}
.lang{float:right;} .lang a{font-size:13px;}
</style>
</head>
<body><div class="wrap">
<span class="lang"><a href="/privacy?lang=ar">العربية</a> · <a href="/terms">Terms of Service</a></span>
<h1>Privacy Policy</h1>
<div class="meta">Version {version} · Operator: {company_en} · <a href="mailto:{email}">{email}</a></div>

<h2>1. Introduction</h2>
<p>This Privacy Policy explains how {company_en} ("we", "us") collects, uses,
and protects personal data when you use the Hudhud platform at {site}.
It also explains the rights you have over your data.</p>

<h2>2. Data we collect</h2>
<ul>
<li><strong>Account data:</strong> your name, email address, phone number
(when provided), password hash (we never store plain passwords), and role.</li>
<li><strong>Connected-account data:</strong> for the Facebook Pages and
Instagram (and Threads) accounts YOU connect: page/account names, IDs, and
access tokens issued by the platform's official authorization.</li>
<li><strong>Customer conversations:</strong> messages and comments your
customers send on your connected accounts, and contact details customers
voluntarily share (such as a phone number or email).</li>
<li><strong>Usage data:</strong> records of actions performed through the
Service (for example, a message sent or a post published), kept for your
operations log and service analytics.</li>
</ul>

<h2>3. How we use data</h2>
<ul>
<li>To deliver the Service: replying to your customers within the platform
messaging rules, organizing leads, publishing content you schedule, and
showing performance analytics for your own accounts.</li>
<li>To secure accounts and prevent abuse.</li>
<li>We do <strong>not</strong> sell personal data, and we do not use your
data or your customers' data to advertise to third parties.</li>
</ul>

<h2>4. AI processing</h2>
<p>Automated replies and content drafts are generated with AI models,
including Google's Gemini API. When the AI drafts a reply to one of your
customers, the conversation text and the knowledge documents you upload may
be processed by the AI provider solely to generate that output. You can
pause AI replies per conversation at any time (Human Takeover).</p>

<h2>5. Legal bases (EEA/UK visitors)</h2>
<p>Where GDPR applies: we process account data to perform our contract with
you (Art. 6(1)(b)); service and security logs on the basis of our legitimate
interests (Art. 6(1)(f)); and any optional analytics on the basis of your
consent (Art. 6(1)(a)), which you can withdraw at any time.</p>

<h2>6. Sharing and service providers</h2>
<p>We share data only with the providers needed to run the Service:
<strong>Supabase</strong> (database hosting), <strong>Vercel</strong>
(application hosting), <strong>Google</strong> (Gemini AI and Google
Sign-In), and the social platforms themselves (Meta / Threads) to deliver
actions on your connected accounts. Each provider processes data under its
own terms; we do not share data for their independent marketing.</p>

<h2>7. Retention</h2>
<p>Account and conversation data are kept while your account is active. When
you delete your account (see section 10), we delete the associated personal
data, except records we must keep for legal compliance or security audits.</p>

<h2>8. Your rights</h2>
<p>You may request access, correction, export, or deletion of your personal
data, and object to or restrict certain processing. Use the
<a href="/data-deletion">Data Deletion</a> page or email us at
<a href="mailto:{email}">{email}</a>. We respond within a reasonable timeframe
and in any case within the period required by applicable law.</p>

<h2>9. Cookies</h2>
<p>We use a small number of strictly necessary cookies: a signed session
cookie (to keep you logged in) and a language preference cookie. We may use
privacy-respecting internal traffic statistics to understand aggregate usage;
when third-party analytics (such as Google Analytics) are enabled, they load
only after you consent, where consent is required.</p>

<h2>10. Data deletion</h2>
<p>You can delete your account and associated data at any time via the
<a href="/data-deletion">Data Deletion</a> page. Platform-initiated deletion
requests (through Meta's Data Deletion Callback) are honored and confirmed
with a reference code.</p>

<h2>11. Security</h2>
<p>Passwords are stored as PBKDF2-HMAC-SHA256 hashes (never in plain text).
Sessions use signed, HTTP-only cookies. Data is stored in PostgreSQL with
row-level security, hosted by Supabase. Access to production data is
restricted.</p>

<h2>12. Children</h2>
<p>The Service is not directed to children under 13 (or the equivalent minimum
age in your jurisdiction), and we do not knowingly collect their personal
data.</p>

<h2>13. Changes to this policy</h2>
<p>We may update this policy from time to time and will post the updated
version here with a new version date.</p>

<h2>14. Contact</h2>
<p>Data protection questions: <a href="mailto:{email}">{email}</a>.</p>
</div></body></html>"""

_PRIVACY_AR = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>سياسة الخصوصية — هدهد</title>
<link rel="icon" href="/static/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/static/favicon-32.png">
<style>
body{font-family:'Tajawal','Plus Jakarta Sans',system-ui,sans-serif;background:#f8fafc;color:#0f172a;line-height:1.9;margin:0;padding:40px 20px;}
.wrap{max-width:820px;margin:0 auto;background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:48px;}
h1{font-size:28px;margin:0 0 8px;} h2{font-size:18px;margin-top:32px;border-bottom:1px solid #e2e8f0;padding-bottom:8px;}
.meta{color:#64748b;font-size:13px;margin-bottom:24px;} a{color:#2563eb;}
.lang{float:left;} .lang a{font-size:13px;}
</style>
</head>
<body><div class="wrap">
<span class="lang"><a href="/privacy">English</a> · <a href="/terms">شروط الاستخدام</a></span>
<h1>سياسة الخصوصية</h1>
<div class="meta">الإصدار {version} · المشغّل: {company_ar} · <a href="mailto:{email}">{email}</a></div>

<h2>1. المقدمة</h2>
<p>توضح سياسة الخصوصية هذه كيفية جمع {company_ar} («نحن») للبيانات الشخصية
واستخدامها وحمايتها عند استخدامك منصة هدهد على {site}، والحقوق التي تملكها
بشأن بياناتك.</p>

<h2>2. البيانات التي نجمعها</h2>
<ul>
<li><strong>بيانات الحساب:</strong> اسمك وبريدك الإلكتروني ورقم هاتفك (عند
الإدخال) وبصمة كلمة المرور (لا نخزن كلمات المرور نصاً أبداً) ودورك.</li>
<li><strong>بيانات الحسابات المتصلة:</strong> لصفحات فيسبوك وحسابات إنستغرام
(وثريدز) التي <strong>تربطها أنت</strong>: أسماء الصفحات والمعرّفات وتوكنات
الوصول الصادرة عبر تفويض المنصة الرسمي.</li>
<li><strong>محادثات العملاء:</strong> الرسائل والتعليقات التي يرسلها عملاؤك
على حساباتك المتصلة، وبيانات التواصل التي يشاركها العملاء طواعية (كالبريد أو
رقم الهاتف).</li>
<li><strong>بيانات الاستخدام:</strong> سجل العمليات المنفذة عبر الخدمة (مثل
رسالة أُرسلت أو منشور نُشر) لأغراض سجل التشغيل والتحليلات.</li>
</ul>

<h2>3. كيف نستخدم البيانات</h2>
<ul>
<li>لتشغيل الخدمة: الرد على عملائك ضمن قواعد المراسلة الرسمية، وتنظيم
العملاء المحتملين، ونشر المحتوى الذي تجدوله، وعرض تحليلات أداء حساباتك أنت.</li>
<li>لتأمين الحسابات ومنع إساءة الاستخدام.</li>
<li><strong>لا نبيع</strong> البيانات الشخصية، ولا نستخدم بياناتك أو بيانات
عملائك للإعلان لصالح جهات أخرى.</li>
</ul>

<h2>4. معالجة الذكاء الاصطناعي</h2>
<p>تولّد الردود والمسودات آلياً بنماذج ذكاء اصطناعي منها واجهة Gemini من
Google. عند صياغة الرد على أحد عملائك قد تُعالج لدى مزوّد الذكاء الاصطناعي
نصوص المحادثة والمستندات التي ترفعها، وذلك فقط لتوليد المخرج المطلوب. يمكنك
إيقاف الردود الآلية لأي محادثة في أي وقت (تولّي المحادثة شخصياً).</p>

<h2>5. الأسس القانونية (لزوار المنطقة الاقتصادية الأوروبية والمملكة المتحدة)</h2>
<p>حيث ينطبق GDPR: نعالج بيانات الحساب تنفيذاً لعقدنا معك (المادة 6/1/b)،
وسجلات التشغيل والأمان بناءً على مصلحتنا المشروعة (6/1/f)، وأي تحليلات
اختيارية بموافقتك (6/1/a) والتي يمكنك سحبها متى شئت.</p>

<h2>6. المشاركة ومزوّدو الخدمة</h2>
<p>لا نشارك البيانات إلا مع المزودين اللازمين لتشغيل الخدمة:
<strong>Supabase</strong> (استضافة قاعدة البيانات)، <strong>Vercel</strong>
(استضافة التطبيق)، <strong>Google</strong> (ذكاء Gemini وتسجيل الدخول
بجوجل)، والمنصات الاجتماعية نفسها (Meta / Threads) لتنفيذ العمليات على
حساباتك المتصلة. كل مزوّد يعالج البيانات وفق شروطه، ولا نشاركه البيانات
لأغراضه التسويقية المستقلة.</p>

<h2>7. مدة الاحتفاظ</h2>
<p>تُحفظ بيانات الحساب والمحادثات ما دام حسابك نشطاً. عند حذفك الحساب (القسم
10) نحذف البيانات الشخصية المرتبطة، باستثناء ما يجب إبقاؤه للامتثال القانوني
أو مراجعات الأمان.</p>

<h2>8. حقوقك</h2>
<p>يمكنك طلب الوصول إلى بياناتك أو تصحيحها أو تصديرها أو حذفها، ويمكنك الاعتراض
على بعض المعالجات أو تقييدها. استخدم صفحة <a href="/data-deletion">حذف
البيانات</a> أو راسلنا على <a href="mailto:{email}">{email}</a>. نرد خلال
مدة معقولة وداخل المهلة التي يحددها القانون المطبق.</p>

<h2>9. الكوكيز</h2>
<p>نستخدم عدداً صغيراً من الكوكيز الضرورية فقط: كوكي جلسة موقّعة (لإبقائك
مسجلاً) وكوكي تفضيل اللغة. وقد نستخدم إحصاءات زيارات داخلية تحترم الخصوصية
لفهم الاستخدام الإجمالي؛ وعند تفعيل أدوات تحليلات خارجية (مثل Google
Analytics) لا تُحمّل إلا بعد موافقتك حيث تكون الموافقة مطلوبة.</p>

<h2>10. حذف البيانات</h2>
<p>يمكنك حذف حسابك وبياناته في أي وقت عبر <a href="/data-deletion">صفحة حذف
البيانات</a>. وتُستجاب طلبات الحذف الواردة من المنصات نفسها (عبر واجهة حذف
بيانات Meta) ويصدر عنها رمز تأكيد مرجعي.</p>

<h2>11. الأمان</h2>
<p>تُخزن كلمات المرور كبصمات PBKDF2-HMAC-SHA256 (وليس نصاً أبداً)، والجلسات
عبر كوكيز موقّعة ومنعزلة (HTTP-only). تُحفظ البيانات في PostgreSQL مع أمان
الصفوف (RLS) مستضافة على Supabase، والوصول لبيانات الإنتاج مقيّد.</p>

<h2>12. الأطفال</h2>
<p>الخدمة غير موجهة لمن هم دون 13 عاماً (أو الحد الأدنى المكافئ في بلدك)، ولا
نجمع بياناتهم الشخصية عن علم.</p>

<h2>13. تعديل السياسة</h2>
<p>قد نحدّث هذه السياسة من وقت لآخر وننشر النسخة المحدثة هنا مع تاريخ إصدار
جديد.</p>

<h2>14. التواصل</h2>
<p>لأي استفسار حول حماية البيانات: <a href="mailto:{email}">{email}</a>.</p>
</div></body></html>"""


def register(app: FastAPI) -> None:
    @app.get("/terms", response_class=HTMLResponse, include_in_schema=False)
    async def terms_page(request: Request):
        lang = request.query_params.get("lang") or request.cookies.get("hudhud_lang") or "en"
        tpl = _TERMS_AR if lang == "ar" else _TERMS_EN
        return HTMLResponse(content=_fill(tpl))

    @app.get("/privacy", response_class=HTMLResponse, include_in_schema=False)
    async def privacy_page(request: Request):
        lang = request.query_params.get("lang") or request.cookies.get("hudhud_lang") or "en"
        tpl = _PRIVACY_AR if lang == "ar" else _PRIVACY_EN
        return HTMLResponse(content=_fill(tpl))


def _fill(tpl: str) -> str:
    """Placeholder substitution that does NOT touch CSS braces (unlike str.format)."""
    html = tpl
    for k, v in {**_ABOUT, "version": LEGAL_VERSION}.items():
        html = html.replace("{" + k + "}", v)
    return html


module_registry.register_module(
    name="legal",
    description=f"Bilingual Terms of Service + Privacy Policy (v{LEGAL_VERSION}, Egyptian law)",
    register_router=register,
    public_exact=["/terms", "/privacy"],
)
