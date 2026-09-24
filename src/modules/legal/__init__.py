"""
Legal module — Terms of Service, Privacy Policy & Data Deletion pages.

Unified, cohesive, responsive design system matching hudhd.com:
- Single clean Globe language selector (🌐) with dropdown.
- Full bilingual English and Arabic support across all legal pages.
- Sticky branded navbar with Back to Home link and legal navigation tabs.
- Clean typography (Plus Jakarta Sans / Tajawal / Inter).
- Branded footer with direct links, contact info, and copyright.
- Honest to actual product behavior (zero fabrication).

Governing law: Arab Republic of Egypt — Cairo Economic Courts.
"""
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from src.core.modules import module_registry

LEGAL_VERSION = "2026-09-10"

_ABOUT = {
    "company_en": "Hudhud (hudhd.com)",
    "company_ar": "هدهد (hudhd.com)",
    "email": "support@hudhd.com",
    "site": "https://www.hudhd.com",
    "version": LEGAL_VERSION,
}

# ---------------------------------------------------------------------------
# Document Bodies (Clean Section Content without outer HTML wrapper)
# ---------------------------------------------------------------------------

_TERMS_BODY_EN = """<h2>1. Introduction</h2>
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
offered (currently three days), the checkout page states its payment,
renewal, and cancellation terms before you complete it. Fees are billed in
advance and are non-refundable except where required by law or stated
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
<p>Questions about these Terms: <a href="mailto:{email}">{email}</a>.</p>"""

_TERMS_BODY_AR = """<h2>1. المقدمة</h2>
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
<p>الخطط والأسعار الحالية معروضة على الموقع. عند توفّر تجربة مجانية (مدتها
الحالية 3 أيام)، تعرض صفحة الدفع شروط وسيلة الدفع والتجديد والإلغاء قبل إتمامها.
الرسوم تُحصّل مقدماً وغير قابلة للاسترداد إلا إذا طلب القانون ذلك أو نُصّ على
خلافه عند الشراء. قد نغيّر الأسعار بإشعار مسبق معقول.</p>

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
<p>لأي استفسار حول هذه الشروط: <a href="mailto:{email}">{email}</a>.</p>"""

_PRIVACY_BODY_EN = """<h2>1. Introduction</h2>
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

<h2>9. Cookies &amp; Product Analytics</h2>
<p>We use a small number of strictly necessary cookies: a signed session
cookie (to keep you logged in) and a language preference cookie. We may use
privacy-respecting internal traffic statistics to understand aggregate usage;
when third-party analytics (such as Google Analytics) are enabled, they load
only after you consent, where consent is required.</p>
<p>When enabled, we also use <strong>PostHog</strong> (hosted in the European
Union) to understand how the Service is used and to improve the user
experience: product analytics, aggregate web traffic, and — in anonymized
form — session replays in which input fields are masked. Analytics is
disabled by default and only activated by us; it does not include advertising
or cross-site tracking, and you can opt out at any time by contacting
<a href="mailto:{email}">{email}</a>.</p>

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
<p>Data protection questions: <a href="mailto:{email}">{email}</a>.</p>"""

_PRIVACY_BODY_AR = """<h2>1. المقدمة</h2>
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

<h2>9. الكوكيز وتحليلات المنتج</h2>
<p>نستخدم عدداً صغيراً من الكوكيز الضرورية فقط: كوكي جلسة موقّعة (لإبقائك
مسجلاً) وكوكي تفضيل اللغة. وقد نستخدم إحصاءات زيارات داخلية تحترم الخصوصية
لفهم الاستخدام الإجمالي؛ وعند تفعيل أدوات تحليلات خارجية (مثل Google
Analytics) لا تُحمّل إلا بعد موافقتك حيث تكون الموافقة مطلوبة.</p>
<p>عند التفعيل، نستخدم أيضاً <strong>PostHog</strong> (مستضافاً في الاتحاد
الأوروبي) لفهم كيفية استخدام الخدمة وتحسين تجربة الاستخدام: تحليلات المنتج،
وزيارات الموقع الإجمالية، وتسجيلات جلسات مجهولة الهوية يُخفى فيها حقول
الإدخال. التحليلات معطّلة افتراضياً ولا تُفعَّل إلا منا، ولا تتضمن إعلانات أو
تتبعاً عبر المواقع، ويمكنك إلغاؤها في أي وقت بالتواصل مع
<a href="mailto:{email}">{email}</a>.</p>

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
<p>لأي استفسار حول حماية البيانات: <a href="mailto:{email}">{email}</a>.</p>"""

_DELETION_BODY_EN = """<h2>1. Overview &amp; Data Privacy Commitment</h2>
<p>At {company_en}, we prioritize user privacy, data security, and full compliance with
global data protection regulations and official platform guidelines (Meta Graph API &amp; Threads API).
You retain full ownership of your accounts and may request permanent deletion of your profile,
connected platform tokens, and stored customer interactions at any time.</p>

<h2>2. In-App Direct Account &amp; Data Deletion</h2>
<p>To request permanent deletion of your Hudhud account and all associated operational data:</p>
<ul>
<li>Log in to your account, navigate to <strong>Settings</strong>, and click <strong>Delete Account &amp; Data</strong>.</li>
<li>Alternatively, email our data privacy team at <a href="mailto:{email}">{email}</a> with the subject line <code>Data Deletion Request</code>.</li>
<li>Upon verification, your account, stored credentials, knowledge base documents, customer conversation histories, and captured leads will be permanently expunged from our Supabase production databases within seven (7) business days.</li>
</ul>

<h2>3. Meta Platform Deauthorization &amp; Automated Deletion (Facebook &amp; Instagram)</h2>
<p>If you connected your Facebook Page or Instagram account and wish to revoke application access and trigger automated data removal via Meta:</p>
<ol>
<li>Go to your personal Facebook profile, click your profile icon in the top right, and select <strong>Settings &amp; privacy</strong> → <strong>Settings</strong>.</li>
<li>In the left-hand navigation menu, select <strong>Apps and Websites</strong>.</li>
<li>Locate <strong>Hudhud</strong> in the list of active apps and click the <strong>Remove</strong> button.</li>
<li>In the confirmation modal, check the option allowing Meta to notify Hudhud to delete your activity and data.</li>
<li>Meta automatically sends a cryptographically signed request to our official endpoint at <code>/api/data-deletion</code>. Our system immediately verifies the HMAC-SHA256 signature, invalidates your tokens, schedules data deletion, and returns a unique confirmation code and status tracking URL.</li>
</ol>

<h2>4. Threads Account Deauthorization</h2>
<p>If you linked a Threads profile through our official integration:</p>
<ul>
<li>Open the Threads mobile app or visit <a href="https://www.threads.net" target="_blank" rel="noopener">threads.net</a>.</li>
<li>Go to <strong>Settings</strong> → <strong>Account</strong> → <strong>Website Permissions</strong>.</li>
<li>Find <strong>Hudhud</strong> and select <strong>Revoke Access</strong>.</li>
<li>Our server will receive the deauthorization webhook and clear all cached Threads access tokens automatically.</li>
</ul>

<h2>5. What Data is Expunged?</h2>
<ul>
<li><strong>Profile Credentials:</strong> Name, email address, phone number, and PBKDF2 password hashes.</li>
<li><strong>Platform Tokens:</strong> Meta Page Access Tokens, Instagram tokens, and Threads credentials.</li>
<li><strong>Customer Interactions:</strong> Cached inbound customer messages, AI-generated responses, and moderation logs.</li>
<li><strong>Leads &amp; Contacts:</strong> Stored customer phone numbers, emails, and conversation metadata.</li>
<li><strong>Custom Knowledge:</strong> Uploaded business knowledge documents and synthesized profiles.</li>
</ul>

<h2>6. Status Check &amp; Support Inquiries</h2>
<p>If you initiated a deletion request and received a confirmation code, you may verify your status on this page using the reference URL provided, or contact our support team at <a href="mailto:{email}">{email}</a> quoting your confirmation code.</p>"""

_DELETION_BODY_AR = """<h2>1. نظرة عامة والتزامنا بحماية البيانات</h2>
<p>تضع منصة {company_ar} أمان بياناتك وخصوصيتها على رأس أولوياتها، ملتزمةً بالقوانين
المعمول بها وسياسات منصات التواصل الرسمية (Meta Graph API وThreads API). تبقى بياناتك
ومحتواك ملكك بالكامل، ويحق لك في أي وقت طلب الحذف النهائي لحسابك وتوكنات الربط
وسجلات العملاء والمحادثات المخزنة.</p>

<h2>2. حذف الحساب والبيانات مباشرة من المنصة</h2>
<p>لطلب حذف حسابك وكافة البيانات المرتبطة به نهائياً:</p>
<ul>
<li>سجل دخولك إلى حسابك في المنصة، وتوجه إلى صفحة <strong>الإعدادات</strong> واختر <strong>حذف الحساب والبيانات</strong>.</li>
<li>أو أرسل بريداً إلكترونياً إلى فريق حماية البيانات: <a href="mailto:{email}">{email}</a> بعنوان <code>طلب حذف بيانات</code>.</li>
<li>بمجرد استلام الطلب والتحقق من ملكية الحساب، تُحذف بيانات اعتمادك وتوكنات الوصول للمنصات وسجلات العملاء والمحادثات ومستندات المعرفة نهائياً من قواعد بياناتنا على Supabase خلال مهلة أقصاها سبعة (7) أيام عمل.</li>
</ul>

<h2>3. إلغاء الربط والحذف الآلي عبر فيسبوك وإنستغرام (Meta)</h2>
<p>إذا كنت قد ربطت صفحاتك أو حساب إنستغرام عبر تسجيل الدخول بفيسبوك وترغب في سحب الصلاحيات وتفعيل الحذف الآلي من ميتا:</p>
<ol>
<li>افتح حسابك الشخصي على فيسبوك، ثم انقر على صورة ملفك الشخصي أعلى اليسار/اليمين، واختر <strong>الإعدادات والخصوصية</strong> ← <strong>الإعدادات</strong>.</li>
<li>من القائمة الجانبية، اختر <strong>التطبيقات ومواقع الويب</strong> (Apps and Websites).</li>
<li>ابحث عن تطبيق <strong>هدهد (Hudhud)</strong> ضمن التطبيقات النشطة واضغط على زر <strong>إزالة (Remove)</strong>.</li>
<li>في النافذة المنبثقة، تأكد من تحديد خيار إرسال إشعار حذف البيانات إلى هدهد.</li>
<li>ستقوم شركة Meta بإرسال طلب موقع رقمياً (Signed Request) إلى واجهة الحذف الرسمية لدينا <code>/api/data-deletion</code>، ويقوم نظامنا بالتحقق من التوقيع الرقمي، وإبطال التوكنات، وحذف السجلات، وإصدار رمز تأكيد فوري ورابط لمتابعة حالة الحذف.</li>
</ol>

<h2>4. إلغاء ربط حساب ثريدز (Threads)</h2>
<p>إذا قمت بربط حسابك على منصة Threads عبر واجهتنا الرسمية:</p>
<ul>
<li>افتح تطبيق Threads أو الموقع <a href="https://www.threads.net" target="_blank" rel="noopener">threads.net</a>.</li>
<li>انتقل إلى <strong>الإعدادات</strong> ← <strong>الحساب</strong> ← <strong>أذونات مواقع الويب</strong> (Website permissions).</li>
<li>اختر تطبيق <strong>هدهد</strong> ثم اضغط على <strong>إلغاء الوصول (Revoke Access)</strong>.</li>
<li>يتلقى خادمنا إشعار سحب التفويض فوراً ويقوم بمسح كافة توكنات الوصول الخاصة بحساب ثريدز تلقائياً.</li>
</ul>

<h2>5. ما البيانات التي يتم مسحها نهائياً؟</h2>
<ul>
<li><strong>بيانات الملف الشخصي:</strong> الاسم، البريد الإلكتروني، رقم الهاتف، وبصمة كلمة المرور المشفرة.</li>
<li><strong>توكنات المنصات:</strong> توكنات صفحات فيسبوك، حسابات إنستغرام، وتفويضات ثريدز (تُتلف وتُلغى صلاحيتها فوراً).</li>
<li><strong>تفاعلات ورسائل العملاء:</strong> سجلات الرسائل الواردة، ردود الذكاء الاصطناعي، وملاحظات المحادثات.</li>
<li><strong>بيانات العملاء المحتملين:</strong> أرقام الهواتف والإيميلات التي تم جمعها طواعية أثناء المحادثات.</li>
<li><strong>مستندات المعرفة الخاصة:</strong> الملفات وقواعد المعرفة التي تم رفعها لتدريب مساعد الذكاء الاصطناعي.</li>
</ul>

<h2>6. متابعة حالة الحذف والاستفسارات</h2>
<p>إذا تم الحذف عبر منصة ميتا وحصلت على رمز تأكيد مرجعي (Confirmation Code)، يمكنك استخدام الرابط المرجعي لمراجعة حالة الطلب في هذه الصفحة، أو مراسلتنا على: <a href="mailto:{email}">{email}</a> مع ذكر رمز التأكيد.</p>"""


# ---------------------------------------------------------------------------
# Unified Page Renderer
# ---------------------------------------------------------------------------

_PAGE_CONFIG = {
    "terms": {
        "en": {
            "title": "Terms of Service",
            "badge": "Legal Terms",
            "body": _TERMS_BODY_EN,
        },
        "ar": {
            "title": "شروط الاستخدام",
            "badge": "الشروط القانونية",
            "body": _TERMS_BODY_AR,
        },
    },
    "privacy": {
        "en": {
            "title": "Privacy Policy",
            "badge": "Privacy & Data Protection",
            "body": _PRIVACY_BODY_EN,
        },
        "ar": {
            "title": "سياسة الخصوصية",
            "badge": "الخصوصية وحماية البيانات",
            "body": _PRIVACY_BODY_AR,
        },
    },
    "data-deletion": {
        "en": {
            "title": "Data Deletion Instructions",
            "badge": "Platform Compliance",
            "body": _DELETION_BODY_EN,
        },
        "ar": {
            "title": "تعليمات حذف البيانات",
            "badge": "الامتثال وحذف البيانات",
            "body": _DELETION_BODY_AR,
        },
    },
}


def render_legal_document(page_key: str, lang: str = "en", confirmation_id: Optional[str] = None) -> str:
    """Renders a legal/compliance document inside the unified Hudhud design system."""
    clean_lang = "ar" if lang == "ar" else "en"
    doc_cfg = _PAGE_CONFIG.get(page_key, _PAGE_CONFIG["terms"])
    spec = doc_cfg[clean_lang]

    # Shared UI Strings
    if clean_lang == "ar":
        doc_title = spec["title"] + " — هدهد"
        direction = "rtl"
        font_family = "'Tajawal', 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif"
        home_text = "الرئيسية"
        back_home = "العودة للرئيسية ←"
        terms_tab = "شروط الاستخدام"
        privacy_tab = "سياسة الخصوصية"
        deletion_tab = "حذف البيانات"
        current_lang = "العربية"
        ver_label = "الإصدار"
        op_label = "المشغّل"
        tagline = "أتمتة المبيعات والمراسلة بالذكاء الاصطناعي"
        rights = "جميع الحقوق محفوظة."
        confirm_title = "تم استلام وتسجيل طلب الحذف بنجاح"
        confirm_desc = (
            f"الرمز التأكيدي: <code class=\"confirm-code\">{confirmation_id}</code>.<br>"
            "تم توثيق طلبك على خوادمنا بنجاح. سيتم مسح كافة التوكنات، وسجلات العملاء، "
            "وبيانات الحساب نهائياً خلال مهلة أقصاها 7 أيام عمل."
        )
    else:
        doc_title = spec["title"] + " — Hudhud"
        direction = "ltr"
        font_family = "'Plus Jakarta Sans', 'Inter', system-ui, -apple-system, sans-serif"
        home_text = "Home"
        back_home = "← Back to Home"
        terms_tab = "Terms of Service"
        privacy_tab = "Privacy Policy"
        deletion_tab = "Data Deletion"
        current_lang = "English"
        ver_label = "Version"
        op_label = "Operator"
        tagline = "AI Social Selling & Messaging Automation"
        rights = "All rights reserved."
        confirm_title = "Deletion Request Received &amp; Logged"
        confirm_desc = (
            f"Confirmation code: <code class=\"confirm-code\">{confirmation_id}</code>.<br>"
            "Your data deletion request has been formally recorded by our servers. "
            "All associated platform tokens, customer lead records, and credentials "
            "will be completely removed within 7 business days."
        )

    # Active Tab Indicators
    active_terms = "active" if page_key == "terms" else ""
    active_privacy = "active" if page_key == "privacy" else ""
    active_deletion = "active" if page_key == "data-deletion" else ""

    # Tab hrefs preserving language
    query_str = "?lang=ar" if clean_lang == "ar" else "?lang=en"

    # Confirmation box if confirmation_id present
    confirm_box_html = ""
    if confirmation_id:
        confirm_box_html = f"""
        <div class="confirm-box">
          <div class="confirm-icon">✅</div>
          <div>
            <div class="confirm-title">{confirm_title}</div>
            <div class="confirm-desc">{confirm_desc}</div>
          </div>
        </div>
        """

    # Fill placeholders in the body
    body_html = spec["body"]
    for k, v in _ABOUT.items():
        body_html = body_html.replace("{" + k + "}", v)

    operator_name = _ABOUT["company_ar"] if clean_lang == "ar" else _ABOUT["company_en"]

    html = f"""<!DOCTYPE html>
<html lang="{clean_lang}" dir="{direction}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{doc_title}</title>
<link rel="icon" href="/static/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/static/favicon-32.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Tajawal:wght@400;500;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {{
  --primary: #2563eb;
  --primary-hover: #1d4ed8;
  --primary-light: #eff6ff;
  --text-main: #0f172a;
  --text-muted: #64748b;
  --text-body: #334155;
  --bg-page: #f8fafc;
  --bg-card: #ffffff;
  --border-default: #e2e8f0;
  --border-subtle: #f1f5f9;
  --radius-lg: 16px;
  --radius-md: 10px;
  --radius-sm: 8px;
  --shadow-card: 0 4px 20px -2px rgba(15, 23, 42, 0.05), 0 2px 6px -1px rgba(15, 23, 42, 0.03);
  --shadow-dropdown: 0 10px 25px -3px rgba(15, 23, 42, 0.12), 0 4px 6px -4px rgba(15, 23, 42, 0.05);
}}

* {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
  font-family: {font_family};
  background-color: var(--bg-page);
  color: var(--text-body);
  line-height: 1.85;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  -webkit-font-smoothing: antialiased;
}}

/* Sticky Navbar */
.legal-navbar {{
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border-default);
}}
.nav-container {{
  max-width: 1080px;
  margin: 0 auto;
  padding: 14px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}}

.brand-group {{
  display: flex;
  align-items: center;
  gap: 16px;
}}
.brand-logo {{
  font-size: 22px;
  font-weight: 800;
  color: var(--text-main);
  text-decoration: none;
  letter-spacing: -0.5px;
  display: inline-flex;
  align-items: center;
}}
.brand-dot {{ color: var(--primary); }}

.nav-back-link {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-muted);
  text-decoration: none;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  background: #f1f5f9;
  border: 1px solid var(--border-default);
  transition: all 0.15s ease;
}}
.nav-back-link:hover {{
  color: var(--primary);
  background: var(--primary-light);
  border-color: #bfdbfe;
}}

/* Legal Tabs */
.nav-tabs {{
  display: flex;
  align-items: center;
  gap: 6px;
  background: #f1f5f9;
  padding: 4px;
  border-radius: 12px;
  list-style: none;
}}
.tab-link {{
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
  text-decoration: none;
  padding: 6px 14px;
  border-radius: 8px;
  transition: all 0.15s ease;
  white-space: nowrap;
}}
.tab-link:hover {{
  color: var(--text-main);
}}
.tab-link.active {{
  background: #ffffff;
  color: var(--primary);
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
}}

/* Globe Switcher */
.lang-dropdown-wrapper {{
  position: relative;
}}
.lang-globe-btn {{
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 14px;
  background: #ffffff;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-main);
  font-family: inherit;
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
  transition: all 0.15s ease;
}}
.lang-globe-btn:hover {{
  border-color: #cbd5e1;
  background: #f8fafc;
}}
.globe-icon {{ font-size: 15px; }}
.chevron-icon {{ font-size: 11px; color: var(--text-muted); }}

.lang-dropdown-menu {{
  display: none;
  position: absolute;
  top: calc(100% + 8px);
  inset-inline-end: 0;
  background: #ffffff;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-dropdown);
  min-width: 165px;
  overflow: hidden;
  z-index: 200;
}}
.lang-dropdown-menu.show {{ display: block; }}
.lang-option {{
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 16px;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-main);
  text-decoration: none;
  transition: background 0.15s;
}}
.lang-option:hover {{ background: #f8fafc; }}
.lang-option.selected {{
  background: var(--primary-light);
  color: var(--primary);
}}
.lang-option:not(:first-child) {{
  border-top: 1px solid var(--border-subtle);
}}

/* Content Card */
.legal-main {{
  flex: 1;
  max-width: 920px;
  width: 100%;
  margin: 36px auto 64px;
  padding: 0 20px;
}}
.legal-card {{
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 48px;
  box-shadow: var(--shadow-card);
}}
.legal-badge {{
  display: inline-block;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--primary);
  background: var(--primary-light);
  border: 1px solid #bfdbfe;
  padding: 3px 10px;
  border-radius: 20px;
  margin-bottom: 12px;
}}
.legal-title {{
  font-size: 30px;
  font-weight: 800;
  color: var(--text-main);
  letter-spacing: -0.5px;
  margin-bottom: 10px;
}}
.legal-meta {{
  color: var(--text-muted);
  font-size: 13.5px;
  margin-bottom: 32px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border-default);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}}
.meta-dot {{ color: #cbd5e1; }}
.legal-meta a {{ color: var(--primary); text-decoration: none; font-weight: 500; }}
.legal-meta a:hover {{ text-decoration: underline; }}

/* Confirmation Alert */
.confirm-box {{
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 32px;
  display: flex;
  align-items: flex-start;
  gap: 14px;
}}
.confirm-icon {{ font-size: 22px; line-height: 1; flex-shrink: 0; }}
.confirm-title {{ font-size: 14.5px; font-weight: 700; color: #166534; margin-bottom: 4px; }}
.confirm-desc {{ font-size: 13.5px; color: #15803d; line-height: 1.6; }}
.confirm-code {{
  background: #dcfce7;
  padding: 2px 8px;
  border-radius: 6px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-weight: 700;
  color: #14532d;
}}

/* Legal Body typography */
.legal-body h2 {{
  font-size: 19px;
  font-weight: 700;
  color: var(--text-main);
  margin-top: 36px;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-subtle);
}}
.legal-body p {{
  font-size: 15px;
  color: var(--text-body);
  margin-bottom: 16px;
}}
.legal-body ul, .legal-body ol {{
  margin: 0 0 18px;
  padding-inline-start: 24px;
  font-size: 15px;
}}
.legal-body li {{
  margin-bottom: 8px;
}}
.legal-body strong {{
  color: var(--text-main);
  font-weight: 600;
}}
.legal-body a {{
  color: var(--primary);
  text-decoration: underline;
  text-underline-offset: 2px;
}}
.legal-body a:hover {{
  color: var(--primary-hover);
}}

/* Footer */
.legal-footer {{
  background: #ffffff;
  border-top: 1px solid var(--border-default);
  padding: 40px 24px 32px;
  margin-top: auto;
}}
.footer-container {{
  max-width: 1080px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 24px;
}}
.footer-brand {{
  font-size: 20px;
  font-weight: 800;
  color: var(--text-main);
  text-decoration: none;
  display: inline-block;
  margin-bottom: 4px;
}}
.footer-tagline {{
  font-size: 13px;
  color: var(--text-muted);
}}
.footer-right {{
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
}}
[dir="rtl"] .footer-right {{
  align-items: flex-start;
}}
.footer-links {{
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}}
.footer-links a {{
  font-size: 13.5px;
  color: var(--text-muted);
  text-decoration: none;
  font-weight: 500;
  transition: color 0.15s;
}}
.footer-links a:hover {{
  color: var(--primary);
  text-decoration: underline;
}}
.footer-copy {{
  font-size: 12.5px;
  color: #94a3b8;
}}

@media (max-width: 768px) {{
  .nav-container {{ flex-wrap: wrap; }}
  .nav-tabs {{ order: 3; width: 100%; justify-content: center; }}
  .legal-card {{ padding: 28px 20px; }}
  .legal-title {{ font-size: 24px; }}
  .footer-container {{ flex-direction: column; align-items: flex-start; }}
  .footer-right {{ align-items: flex-start; }}
}}
</style>
</head>
<body>

<!-- Sticky Header -->
<header class="legal-navbar">
  <div class="nav-container">
    <div class="brand-group">
      <a href="/" class="brand-logo">
        <span>Hudhud</span><span class="brand-dot">.</span>
      </a>
      <a href="/" class="nav-back-link">
        <span>{back_home}</span>
      </a>
    </div>

    <nav class="nav-tabs">
      <a href="/terms{query_str}" class="tab-link {active_terms}">{terms_tab}</a>
      <a href="/privacy{query_str}" class="tab-link {active_privacy}">{privacy_tab}</a>
      <a href="/data-deletion{query_str}" class="tab-link {active_deletion}">{deletion_tab}</a>
    </nav>

    <div class="lang-dropdown-wrapper">
      <button type="button" class="lang-globe-btn" onclick="toggleLangMenu(event)" aria-label="Language Switcher">
        <span class="globe-icon">🌐</span>
        <span>{current_lang}</span>
        <span class="chevron-icon">▾</span>
      </button>
      <div id="langMenu" class="lang-dropdown-menu">
        <a href="?lang=en" onclick="setLang('en'); return false;" class="lang-option {'selected' if clean_lang == 'en' else ''}">
          <span>🇺🇸</span>
          <span>English</span>
        </a>
        <a href="?lang=ar" onclick="setLang('ar'); return false;" class="lang-option {'selected' if clean_lang == 'ar' else ''}">
          <span>🇪🇬</span>
          <span>العربية</span>
        </a>
      </div>
    </div>
  </div>
</header>

<!-- Main Legal Content -->
<main class="legal-main">
  <article class="legal-card">
    <div class="legal-badge">{spec['badge']}</div>
    <h1 class="legal-title">{spec['title']}</h1>
    <div class="legal-meta">
      <span>{ver_label} {_ABOUT['version']}</span>
      <span class="meta-dot">·</span>
      <span>{op_label}: {operator_name}</span>
      <span class="meta-dot">·</span>
      <a href="mailto:{_ABOUT['email']}">{_ABOUT['email']}</a>
    </div>

    {confirm_box_html}

    <div class="legal-body">
      {body_html}
    </div>
  </article>
</main>

<!-- Footer -->
<footer class="legal-footer">
  <div class="footer-container">
    <div>
      <a href="/" class="footer-brand">
        <span>Hudhud</span><span class="brand-dot">.</span>
      </a>
      <p class="footer-tagline">{tagline}</p>
    </div>
    <div class="footer-right">
      <div class="footer-links">
        <a href="/terms{query_str}">{terms_tab}</a>
        <a href="/privacy{query_str}">{privacy_tab}</a>
        <a href="/data-deletion{query_str}">{deletion_tab}</a>
        <a href="/">{home_text}</a>
      </div>
      <div class="footer-copy">
        <a href="mailto:{_ABOUT['email']}" style="color:var(--text-muted); text-decoration:none; margin-inline-end:8px;">{_ABOUT['email']}</a>
        © 2026 Hudhud (hudhd.com). {rights}
      </div>
    </div>
  </div>
</footer>

<script>
function toggleLangMenu(e) {{
  if (e) e.stopPropagation();
  var m = document.getElementById('langMenu');
  if (m) m.classList.toggle('show');
}}
function setLang(newLang) {{
  document.cookie = "hudhud_lang=" + newLang + ";path=/;max-age=31536000;SameSite=Lax";
  try {{
    var url = new URL(window.location.href);
    url.searchParams.set("lang", newLang);
    window.location.href = url.toString();
  }} catch (err) {{
    window.location.href = "?lang=" + newLang;
  }}
}}
document.addEventListener('click', function(e) {{
  var m = document.getElementById('langMenu');
  if (m && !e.target.closest('.lang-dropdown-wrapper')) {{
    m.classList.remove('show');
  }}
}});
</script>
</body>
</html>"""
    return html


def register(app: FastAPI) -> None:
    @app.get("/terms", response_class=HTMLResponse, include_in_schema=False)
    async def terms_page(request: Request):
        lang = request.query_params.get("lang") or request.cookies.get("hudhud_lang") or "en"
        html = render_legal_document("terms", lang=lang)
        return HTMLResponse(content=html)

    @app.get("/privacy", response_class=HTMLResponse, include_in_schema=False)
    async def privacy_page(request: Request):
        lang = request.query_params.get("lang") or request.cookies.get("hudhud_lang") or "en"
        html = render_legal_document("privacy", lang=lang)
        return HTMLResponse(content=html)


module_registry.register_module(
    name="legal",
    description=f"Bilingual Terms of Service + Privacy Policy (v{LEGAL_VERSION}, Egyptian law)",
    register_router=register,
    public_exact=["/terms", "/privacy"],
)
