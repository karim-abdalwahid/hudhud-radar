-- ============================================================
-- Migration 002: Security hardening from live audit (Phase 2)
-- Fixes critical RLS exposure found in the live database audit.
-- PROBLEM: anon role had full SELECT/INSERT/UPDATE/DELETE on all
-- business tables. Anyone with the public SUPABASE_KEY could read
-- PII (leads, messages), modify or DELETE data — bypassing the app.
-- FIX: revoke anon entirely; keep authenticated+service_role grants;
-- keep USING(true) policies (app-level auth is enforced by our
-- AuthMiddleware; service_role bypasses RLS anyway).
-- Also: enable pgvector for Phase 5, add missing audit indexes.
-- ============================================================

-- 1. CRITICAL: strip anon privileges from ALL business tables
REVOKE ALL ON public.leads FROM anon;
REVOKE ALL ON public.messages FROM anon;
REVOKE ALL ON public.activity_logs FROM anon;
REVOKE ALL ON public.content_posts FROM anon;
REVOKE ALL ON public.identity_verification_queue FROM anon;
REVOKE ALL ON public.page_performance_metrics FROM anon;
REVOKE ALL ON public.campaigns FROM anon;
REVOKE ALL ON public.app_settings FROM anon;
REVOKE ALL ON public.processed_events FROM anon;
REVOKE ALL ON public.users FROM anon;

-- anon should not even see table structure in this schema
REVOKE USAGE ON SCHEMA public FROM anon;

-- 2. Enable pgvector (Phase 5 prerequisite — 'vector' is available)
CREATE EXTENSION IF NOT EXISTS vector;

-- 3. Missing performance indexes (found in audit)
CREATE INDEX IF NOT EXISTS idx_content_posts_status_sched ON public.content_posts(status, scheduled_for) WHERE status = 'scheduled';
CREATE INDEX IF NOT EXISTS idx_content_posts_created ON public.content_posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_lead_time ON public.messages(lead_id, sent_at DESC);

-- 4. Documentation comments for the audit trail
COMMENT ON POLICY "Allow all access to service_role" ON public.users IS 'Policy name kept for compatibility; actual protection = anon revoked + AuthMiddleware at app level. See archive 022.';
