-- Migration 007: Admin Console foundations (WS-E+H)
-- 1) users gains plan/credits columns (manual management pre-Phase 9;
--    Phase 9 turns these into real subscriptions with billing)
-- 2) site_traffic: lightweight internal page-view tracking (no tracking
--    cookies, no third-party scripts) for the admin traffic dashboard.

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS plan VARCHAR(30) NOT NULL DEFAULT 'free',
    ADD COLUMN IF NOT EXISTS ai_credits INTEGER NOT NULL DEFAULT 100,
    ADD COLUMN IF NOT EXISTS plan_updated_at TIMESTAMPTZ;

COMMENT ON COLUMN public.users.plan IS 'Manual plan assignment pre-Phase 9 (free|starter|growth|scale).';
COMMENT ON COLUMN public.users.ai_credits IS 'AI-action credits consumed by LLM calls (replies, content generation).';

CREATE TABLE IF NOT EXISTS public.site_traffic (
    id BIGSERIAL PRIMARY KEY,
    path VARCHAR(255) NOT NULL,
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    is_admin BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_traffic_recent ON public.site_traffic (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_traffic_path ON public.site_traffic (path);

ALTER TABLE public.site_traffic ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY "Service role full access on site_traffic" ON public.site_traffic
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

COMMENT ON TABLE public.site_traffic IS 'Internal lightweight page-view log (no tracking cookies). Powers admin traffic dashboard.';
