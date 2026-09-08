-- Migration 008: message templates manager (WS-G)
-- Owner requirement: editable message templates (welcome on signup/login,
-- trial reminders, plan purchase, credits low, new-lead alerts...) rendered
-- into in-app notifications (email channel later, v1.1). Editable at any
-- time from the /templates admin page; defaults are seeded here and can be
-- restored per template.

CREATE TABLE IF NOT EXISTS public.message_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(80) NOT NULL UNIQUE,                -- e.g. welcome_signup
    channel VARCHAR(20) NOT NULL DEFAULT 'inapp',   -- inapp (email reserved v1.1)
    subject TEXT NOT NULL,
    body TEXT NOT NULL,                              -- supports {placeholders}
    is_active BOOLEAN NOT NULL DEFAULT true,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.message_templates ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY "Service role full access on message_templates" ON public.message_templates
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Seed the lifecycle templates (owner can edit/restore from the admin page)
INSERT INTO public.message_templates (key, subject, body) VALUES
('welcome_signup',
 '🎉 أهلاً بك في هدهد، {user_name}!',
 'حسابك جاهز الآن. الخطوة التالية: اربط صفحتك من الإعدادات وسيبدأ الوكيل الذكي بالرد على عملائك فوراً.'),
('welcome_login',
 '👋 رجوع سعيد، {user_name}',
 'أهلاً بعودتك! راجع إشعارات محادثاتك الجديدة من صندوق الوارد.'),
('trial_ending',
 '⏳ تجربتك المجانية تنتهي قريباً',
 'تجربتك المجانية (14 يوماً) تنتهي بتاريخ {trial_end}. للاستمرار في خدمة الردود الذكية، فعّل خطتك من لوحة التحكم.'),
('plan_purchased',
 '✅ تم تفعيل خطتك: {plan}',
 'مبروك! خطتك ({plan}) مفعّلة الآن — رصيد الذكاء الاصطناعي المخصص أُضيف لحسابك.'),
('credits_low',
 '⚠️ رصيد الذكاء الاصطناعي منخفض',
 'باقي لديك {credits} رصيد فقط. الوكيل سيعمل بالقوالب الاحتياطية عند النفاد — تواصل معنا للتجديد.'),
('agent_new_lead',
 '🎯 عميل محتمل جديد!',
 'الوكيل التقط عميلاً مهتماً: {lead_name} — شاهده في إدارة العملاء.')
ON CONFLICT (key) DO NOTHING;

COMMENT ON TABLE public.message_templates IS 'Editable lifecycle message templates (rendered to notifications; placeholders like {user_name}). Admin-managed.';
