-- Make the public schema backend-only, remove legacy tenantless records,
-- and add the missing tenant keys needed by the SaaS paths.
--
-- FastAPI is the sole production database client and uses service_role.
-- Browser roles must never read application data or execute privileged RPCs.

BEGIN;

-- -------------------------------------------------------------------------
-- Explicitly approved legacy-data cleanup.  The owner requested removal of
-- every old record that has no tenant owner, including anonymous telemetry.
-- -------------------------------------------------------------------------
DELETE FROM public.messages WHERE user_id IS NULL;
DELETE FROM public.leads WHERE user_id IS NULL;
DELETE FROM public.content_posts WHERE user_id IS NULL;
DELETE FROM public.page_performance_metrics WHERE user_id IS NULL;
DELETE FROM public.activity_logs WHERE user_id IS NULL;
DELETE FROM public.notifications WHERE user_id IS NULL;
DELETE FROM public.payment_events WHERE user_id IS NULL;
DELETE FROM public.automations_workflows WHERE user_id IS NULL;
DELETE FROM public.kb_chunks
WHERE document_id IN (SELECT id FROM public.kb_documents WHERE user_id IS NULL);
DELETE FROM public.kb_documents WHERE user_id IS NULL;
DELETE FROM public.site_traffic WHERE user_id IS NULL;
-- This table has no owner column.  Existing keys belong to the old global
-- workspace and could incorrectly suppress a new tenant's webhook event.
DELETE FROM public.processed_events;
-- Global plaintext page/Threads tokens were replaced with encrypted,
-- tenant-owned platform_connections. Keep only non-secret application config.
DELETE FROM public.app_settings
WHERE key IN (
    'meta_credentials', 'threads_credentials', 'automations_workflows',
    'meta_cached_posts'
);

-- -------------------------------------------------------------------------
-- Tenant keys and uniqueness.  There are no campaign rows at migration time,
-- so campaigns can become tenant-owned immediately.
-- -------------------------------------------------------------------------
ALTER TABLE public.campaigns ADD COLUMN IF NOT EXISTS user_id uuid;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'campaigns_user_id_fkey'
    ) THEN
        ALTER TABLE public.campaigns
            ADD CONSTRAINT campaigns_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;
    END IF;
END $$;

ALTER TABLE public.campaigns ALTER COLUMN user_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS idx_campaigns_user ON public.campaigns(user_id);

ALTER TABLE public.page_performance_metrics
    DROP CONSTRAINT IF EXISTS unique_platform_date;
ALTER TABLE public.page_performance_metrics ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE public.page_performance_metrics
    ADD CONSTRAINT unique_user_platform_date UNIQUE (user_id, platform, metric_date);

ALTER TABLE public.leads ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE public.messages ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE public.content_posts ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE public.kb_documents ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE public.automations_workflows ALTER COLUMN user_id SET NOT NULL;

-- These legacy foreign keys used SET NULL.  That contradicts the mandatory
-- ownership above and would make deletion of a user fail at runtime.
ALTER TABLE public.activity_logs
    DROP CONSTRAINT IF EXISTS activity_logs_user_id_fkey;
ALTER TABLE public.activity_logs
    ADD CONSTRAINT activity_logs_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;
ALTER TABLE public.activity_logs ALTER COLUMN user_id SET NOT NULL;

ALTER TABLE public.kb_documents
    DROP CONSTRAINT IF EXISTS kb_documents_user_id_fkey;
ALTER TABLE public.kb_documents
    ADD CONSTRAINT kb_documents_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

-- Payment webhooks are persisted only after their gateway identity maps to a
-- Hudhud user, and are removed with that user during account deletion.
ALTER TABLE public.payment_events
    DROP CONSTRAINT IF EXISTS payment_events_user_id_fkey;
ALTER TABLE public.payment_events
    ADD CONSTRAINT payment_events_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;
ALTER TABLE public.payment_events ALTER COLUMN user_id SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_active_platform_connection_account
    ON public.platform_connections(platform, account_id)
    WHERE status = 'active' AND account_id IS NOT NULL AND account_id <> '';

-- -------------------------------------------------------------------------
-- Remove the historical public-permissive policies.  A policy without `TO`
-- applies to PUBLIC; its descriptive name does not limit it to service_role.
-- -------------------------------------------------------------------------
DROP POLICY IF EXISTS "Allow all access to service_role" ON public.activity_logs;
DROP POLICY IF EXISTS "Allow all access to service_role" ON public.ai_models;
DROP POLICY IF EXISTS "Allow all access to service_role" ON public.ai_providers;
DROP POLICY IF EXISTS "Allow all access to service_role" ON public.app_settings;
DROP POLICY IF EXISTS "Allow all access to service_role" ON public.campaigns;
DROP POLICY IF EXISTS "Allow all access to service_role" ON public.content_posts;
DROP POLICY IF EXISTS "Allow all access to service_role" ON public.identity_verification_queue;
DROP POLICY IF EXISTS "Allow all access to service_role" ON public.kb_chunks;
DROP POLICY IF EXISTS "Allow all access to service_role" ON public.kb_documents;
DROP POLICY IF EXISTS "Allow all access to service_role" ON public.leads;
DROP POLICY IF EXISTS "Allow all access to service_role" ON public.messages;
DROP POLICY IF EXISTS "Allow all access to service_role" ON public.page_performance_metrics;
DROP POLICY IF EXISTS "Allow all access to service_role" ON public.processed_events;
DROP POLICY IF EXISTS "Allow all access to service_role" ON public.users;

-- Keep RLS switched on.  service_role bypasses it, while every browser role
-- loses table privileges below.  This is deliberate because the application
-- uses its own signed sessions rather than Supabase Auth JWTs.
ALTER TABLE public.activity_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_providers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.app_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.automations_workflows ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.content_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.coupon_redemptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.coupons ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.identity_verification_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kb_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kb_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.message_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.page_performance_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payment_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.platform_addons_catalog ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.platform_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.processed_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.site_traffic ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_entitlements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;

-- The app does not use this RPC. Keep it backend-only and remove the unsafe
-- SECURITY DEFINER behavior while fixing the search path.
CREATE OR REPLACE FUNCTION public.create_notification(
    p_user_id uuid,
    p_type character varying,
    p_title character varying,
    p_body text,
    p_meta jsonb DEFAULT '{}'::jsonb
)
RETURNS uuid
LANGUAGE sql
SECURITY INVOKER
SET search_path TO 'public'
AS $function$
    INSERT INTO public.notifications (user_id, type, title, body, meta)
    VALUES (p_user_id, p_type, p_title, p_body, p_meta)
    RETURNING id;
$function$;

REVOKE ALL ON FUNCTION public.create_notification(uuid, character varying, character varying, text, jsonb)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.create_notification(uuid, character varying, character varying, text, jsonb)
    TO service_role;

-- Do not recreate permissive access for future backend tables/functions.
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE ALL ON TABLES FROM PUBLIC, anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC, anon, authenticated;

COMMIT;
