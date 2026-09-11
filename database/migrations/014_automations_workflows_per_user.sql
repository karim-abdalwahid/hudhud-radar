-- Migration 014: automations workflows table (per-user, Wave 9.8 alignment).
-- FINDING (audit 2026-09-11): the automations service persists workflows in a
-- legacy JSON FILE store (src/knowledge/automations_store.json) — global, not
-- per-user, not backed up, and the table never existed in the live database.
-- This migration creates the table with per-user ownership from day one so the
-- service cutover (Wave 9.8) has its destination ready.

CREATE TABLE IF NOT EXISTS public.automations_workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    platform TEXT NOT NULL DEFAULT 'both',
    status TEXT NOT NULL DEFAULT 'active',
    keywords JSONB DEFAULT '[]'::jsonb,
    target_type TEXT DEFAULT 'all',
    target_post_id TEXT,
    like_comment BOOLEAN DEFAULT false,
    reply_comment BOOLEAN DEFAULT false,
    reply_comment_text TEXT,
    send_dm BOOLEAN DEFAULT false,
    dm_text TEXT,
    last_executed_at TIMESTAMPTZ,
    execution_count INTEGER DEFAULT 0,
    config JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_automations_user ON public.automations_workflows (user_id);

ALTER TABLE public.automations_workflows ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access on automations_workflows"
    ON public.automations_workflows
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
