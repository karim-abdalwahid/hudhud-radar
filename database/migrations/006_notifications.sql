-- Migration 006: in-app notifications (WS-F)
-- Per-owner plan: every user sees in-app notifications for actions in their
-- account (publish jobs, automations, syncs, AI replies); admin can also
-- broadcast to all users or target one. Email channel arrives later (v1.1)
-- on top of the SAME notifications table.

CREATE TABLE IF NOT EXISTS public.notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL DEFAULT 'info',       -- info|success|warning|error|broadcast
    title VARCHAR(255) NOT NULL,
    body TEXT,
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    read BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_recent
    ON public.notifications (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_unread
    ON public.notifications (user_id) WHERE read = false;

ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY "Service role full access on notifications" ON public.notifications
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Notification helper used by job hooks (server-side only; service role)
CREATE OR REPLACE FUNCTION public.create_notification(
    p_user_id UUID, p_type VARCHAR, p_title VARCHAR, p_body TEXT, p_meta JSONB DEFAULT '{}'
) RETURNS UUID AS $$
    INSERT INTO public.notifications (user_id, type, title, body, meta)
    VALUES (p_user_id, p_type, p_title, p_body, p_meta)
    RETURNING id;
$$ LANGUAGE SQL SECURITY DEFINER;

COMMENT ON TABLE public.notifications IS 'In-app user notifications (job results, lifecycle events, admin broadcasts). Email delivery rides on this table later (v1.1).';
