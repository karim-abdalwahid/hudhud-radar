-- Migration 005: Terms-of-service acceptance tracking (WS-B consent gate)
-- Owner-approved plan: users must accept ToS/Privacy before account creation
-- (both email signup and Google OAuth). We record WHEN and WHICH VERSION.

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS terms_version VARCHAR(20);

COMMENT ON COLUMN public.users.terms_accepted_at IS 'Timestamp of explicit ToS+Privacy acceptance at signup (consent gate).';
COMMENT ON COLUMN public.users.terms_version IS 'Legal terms version accepted (e.g. 2026-09-08).';
