-- Migration 013: Threads replies → CRM bridge.
-- leads.threads_account_id = the official Threads user id of the reply author
-- (deterministic identity key; username-only authors stay username-keyed).

ALTER TABLE public.leads ADD COLUMN IF NOT EXISTS threads_account_id TEXT;
CREATE INDEX IF NOT EXISTS idx_leads_threads ON public.leads (threads_account_id);
