-- Migration 010: per-user data isolation (Phase 9.5)
-- Every business row gains an owner: users see/manage only their own data.

ALTER TABLE public.leads ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES public.users(id) ON DELETE CASCADE;
ALTER TABLE public.messages ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES public.users(id) ON DELETE CASCADE;
ALTER TABLE public.content_posts ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES public.users(id) ON DELETE CASCADE;
ALTER TABLE public.notifications ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES public.users(id) ON DELETE CASCADE;
ALTER TABLE public.activity_logs ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES public.users(id) ON DELETE SET NULL;
ALTER TABLE public.page_performance_metrics ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES public.users(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_leads_user ON public.leads (user_id);
CREATE INDEX IF NOT EXISTS idx_messages_user ON public.messages (user_id);
CREATE INDEX IF NOT EXISTS idx_content_posts_user ON public.content_posts (user_id);
CREATE INDEX IF NOT EXISTS idx_metrics_user ON public.page_performance_metrics (user_id);
