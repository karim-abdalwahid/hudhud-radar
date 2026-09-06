-- ====================================================================
-- HudhudRadar Migration 001: Users & Authentication + Security Tables
-- Date: 2026-09-06
-- Applies: users, processed_events, app_settings, leads.human_takeover,
--          content_posts RLS hardening
-- HOW TO APPLY: Supabase Dashboard -> SQL Editor -> paste -> Run
-- ====================================================================

-- --------------------------------------------------------------------
-- 1. users table (Authentication & Future SaaS Multi-Tenancy)
-- --------------------------------------------------------------------
DO $$ BEGIN
    CREATE TYPE user_role_enum AS ENUM ('admin', 'user');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(50),
    full_name VARCHAR(255),
    password_hash TEXT NOT NULL,
    role user_role_enum NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT true,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.users IS 'Application users: admin (owner) and future SaaS customers. Phone captured at signup per owner requirement.';

-- --------------------------------------------------------------------
-- 2. processed_events table (Webhook Idempotency / Deduplication)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.processed_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_key VARCHAR(255) NOT NULL UNIQUE,
    event_type VARCHAR(50) NOT NULL DEFAULT 'message',
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.processed_events IS 'Idempotency ledger: prevents duplicate webhook processing (Meta retries) causing repeated replies/DMs.';

CREATE INDEX IF NOT EXISTS idx_processed_events_key ON public.processed_events(event_key);
CREATE INDEX IF NOT EXISTS idx_processed_events_time ON public.processed_events(processed_at DESC);

-- --------------------------------------------------------------------
-- 3. app_settings table (Serverless-safe key/value persistence)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.app_settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.app_settings IS 'Runtime key/value settings (meta_credentials, meta_cached_posts, agent config) surviving serverless restarts.';

-- --------------------------------------------------------------------
-- 4. leads.human_takeover column (Human-in-the-loop inbox control)
-- --------------------------------------------------------------------
ALTER TABLE public.leads ADD COLUMN IF NOT EXISTS human_takeover BOOLEAN NOT NULL DEFAULT false;
COMMENT ON COLUMN public.leads.human_takeover IS 'When true, the AI agent pauses automatic replies for this lead (Human Takeover).';

-- --------------------------------------------------------------------
-- 5. Security Hardening: RLS on new tables
-- --------------------------------------------------------------------
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.processed_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.app_settings ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY "Service role full access on users" ON public.users
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE POLICY "Service role full access on processed_events" ON public.processed_events
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE POLICY "Service role full access on app_settings" ON public.app_settings
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- --------------------------------------------------------------------
-- 6. Fix content_posts RLS: align with service_role model (was USING(true))
-- --------------------------------------------------------------------
DROP POLICY IF EXISTS "Allow all access on content_posts" ON public.content_posts;
DO $$ BEGIN
    CREATE POLICY "Service role full access on content_posts" ON public.content_posts
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- --------------------------------------------------------------------
-- 7. updated_at trigger for users
-- --------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_users_updated_at ON public.users;
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
