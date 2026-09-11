-- Migration 018 (owner request): global AI pause per user.
-- Users can silence the AI across ALL conversations/automations so they can
-- manage their pages personally. Independent from (and overrides) the
-- per-conversation Human Takeover flag.

ALTER TABLE public.users ADD COLUMN IF NOT EXISTS ai_paused BOOLEAN NOT NULL DEFAULT false;
