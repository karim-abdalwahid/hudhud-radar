-- Migration 009: Billing & Entitlements foundation (Phase 9.1)
-- Owner model: NO base plan — pricing = platforms chosen, multi-platform
-- discounts (admin-editable), Polar.sh payments, entitlements gate everything.

-- 1) Platform addons catalog (admin-editable pricing)
CREATE TABLE IF NOT EXISTS public.platform_addons_catalog (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(30) NOT NULL UNIQUE,           -- facebook|instagram|threads|whatsapp
    display_name VARCHAR(80) NOT NULL,
    price_usd NUMERIC(10,2) NOT NULL DEFAULT 0,
    is_available BOOLEAN NOT NULL DEFAULT true,
    sort_order INT NOT NULL DEFAULT 100,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2) User subscriptions (platform-composable; NO base plan)
CREATE TABLE IF NOT EXISTS public.user_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'none',     -- none|trialing|active|past_due|canceled
    trial_ends_at TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    payment_provider VARCHAR(30),                   -- polar|paymob|... (gateway registry)
    provider_subscription_id VARCHAR(120),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_subs_one_per_user
    ON public.user_subscriptions (user_id);

-- 3) Entitlements — THE single source of truth for what a user may use
CREATE TABLE IF NOT EXISTS public.user_entitlements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    entitlement VARCHAR(80) NOT NULL,               -- platform:facebook | feature:automations | credits:1000
    source VARCHAR(30) NOT NULL DEFAULT 'subscription', -- subscription|trial|grant|coupon
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,                          -- null = permanent while subscription active
    UNIQUE (user_id, entitlement)
);
CREATE INDEX IF NOT EXISTS idx_entitlements_user ON public.user_entitlements (user_id);

-- 4) Payment events (idempotency + audit for every gateway)
CREATE TABLE IF NOT EXISTS public.payment_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(30) NOT NULL,                  -- polar|paymob|...
    event_id VARCHAR(160) NOT NULL,                 -- provider's event id (dedup key)
    event_type VARCHAR(60) NOT NULL,
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    processed BOOLEAN NOT NULL DEFAULT false,
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_payment_events_dedup
    ON public.payment_events (provider, event_id);

-- 5) Usage ledger (AI actions consumption → ai_credits)
CREATE TABLE IF NOT EXISTS public.usage_events (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    kind VARCHAR(60) NOT NULL,                      -- ai_reply|ai_generate|...
    amount INT NOT NULL DEFAULT 1,
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_usage_user_recent ON public.usage_events (user_id, created_at DESC);

-- 6) Coupons (owner: per-user or general, usage limits, value or platform unlock)
CREATE TABLE IF NOT EXISTS public.coupons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(40) NOT NULL UNIQUE,
    kind VARCHAR(20) NOT NULL,                      -- percent|fixed|platform_unlock|credits
    value NUMERIC(10,2) NOT NULL DEFAULT 0,         -- percent 0-100 | usd | credits count
    platform VARCHAR(30),                           -- for platform_unlock
    applies_to_user UUID REFERENCES public.users(id) ON DELETE CASCADE, -- null = anyone
    max_total_uses INT,                             -- null = unlimited
    max_uses_per_user INT NOT NULL DEFAULT 1,
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.coupon_redemptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coupon_id UUID NOT NULL REFERENCES public.coupons(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    redeemed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (coupon_id, user_id)
);

-- 7) Site settings additions: discounts + trial + theme defaults (admin-editable)
--    (stored in app_settings JSON via admin panel — no schema needed here)

ALTER TABLE public.user_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_entitlements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payment_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.platform_addons_catalog ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.coupons ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.coupon_redemptions ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY "Service role full access on user_subscriptions" ON public.user_subscriptions
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    CREATE POLICY "Service role full access on user_entitlements" ON public.user_entitlements
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    CREATE POLICY "Service role full access on payment_events" ON public.payment_events
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    CREATE POLICY "Service role full access on usage_events" ON public.usage_events
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    CREATE POLICY "Service role full access on platform_addons_catalog" ON public.platform_addons_catalog
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    CREATE POLICY "Service role full access on coupons" ON public.coupons
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    CREATE POLICY "Service role full access on coupon_redemptions" ON public.coupon_redemptions
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Seed catalog defaults (admin-editable prices; USD base — geo pricing via app_settings)
INSERT INTO public.platform_addons_catalog (platform, display_name, price_usd, sort_order) VALUES
    ('facebook',  'Facebook Page', 15.00, 1),
    ('instagram', 'Instagram Business', 15.00, 2),
    ('threads',   'Threads', 10.00, 3)
ON CONFLICT (platform) DO NOTHING;
