-- HudhudRadar: align the live Data API with a backend-only access model.
-- Apply only after SUPABASE_SERVICE_ROLE_KEY is replaced with a real secret/service-role key.
-- This migration deliberately grants no direct anon/authenticated access: the FastAPI backend
-- is the sole database client and carries the service role key server-side.

BEGIN;

CREATE TABLE IF NOT EXISTS public.app_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.app_settings IS
    'Server-managed application configuration. Never expose credentials to browser clients.';

ALTER TABLE public.app_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.identity_verification_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.activity_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.page_performance_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.content_posts ENABLE ROW LEVEL SECURITY;

-- The browser never talks to the Data API in this architecture.
REVOKE ALL ON TABLE public.app_settings, public.leads, public.messages,
    public.identity_verification_queue, public.activity_logs,
    public.page_performance_metrics, public.campaigns, public.content_posts
    FROM anon, authenticated;

-- Explicit grants are needed when the project has Data API auto-exposure disabled.
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.app_settings, public.leads,
    public.messages, public.identity_verification_queue, public.activity_logs,
    public.page_performance_metrics, public.campaigns, public.content_posts
    TO service_role;

-- service_role bypasses RLS; the old policies are unnecessary and the content_posts
-- policy previously allowed every Data API client to access every row.
DROP POLICY IF EXISTS "Service role full access on leads" ON public.leads;
DROP POLICY IF EXISTS "Service role full access on messages" ON public.messages;
DROP POLICY IF EXISTS "Service role full access on verification queue" ON public.identity_verification_queue;
DROP POLICY IF EXISTS "Service role full access on activity logs" ON public.activity_logs;
DROP POLICY IF EXISTS "Service role full access on page metrics" ON public.page_performance_metrics;
DROP POLICY IF EXISTS "Service role full access on campaigns" ON public.campaigns;
DROP POLICY IF EXISTS "Allow all access on content_posts" ON public.content_posts;
DROP POLICY IF EXISTS "Service role full access on content_posts" ON public.content_posts;

CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

REVOKE ALL ON FUNCTION public.update_updated_at_column() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.update_updated_at_column() TO service_role;

COMMIT;
