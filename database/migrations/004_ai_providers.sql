-- ============================================================
-- Migration 004: AI Providers & Models system (Phase 8, opencode-style)
-- ============================================================

-- Providers: official (Google AI / Anthropic / OpenAI / OpenRouter) or custom
CREATE TABLE IF NOT EXISTS public.ai_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kind VARCHAR(20) NOT NULL DEFAULT 'official',        -- official | custom
    provider_key VARCHAR(50) NOT NULL,                   -- google | anthropic | openai | openrouter | custom-*
    display_name VARCHAR(100) NOT NULL,
    logo_key VARCHAR(30) NOT NULL DEFAULT 'custom',      -- google | anthropic | openai | openrouter | custom
    api_key TEXT,                                        -- masked in UI, never returned raw
    base_url TEXT,
    custom_headers JSONB NOT NULL DEFAULT '[]'::jsonb,   -- [{header, value}]
    status VARCHAR(20) NOT NULL DEFAULT 'active',        -- active | disabled
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_provider_key UNIQUE (provider_key)
);

COMMENT ON TABLE public.ai_providers IS 'AI provider connections (official + custom OpenAI-compatible), managed by admin.';

-- Models discovered from each provider (or added manually for custom)
CREATE TABLE IF NOT EXISTS public.ai_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id UUID NOT NULL REFERENCES public.ai_providers(id) ON DELETE CASCADE,
    model_id VARCHAR(120) NOT NULL,                      -- e.g. gemini-flash-latest
    display_name VARCHAR(150) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT true,               -- admin toggle → visible to clients
    available BOOLEAN NOT NULL DEFAULT true,             -- from live discovery (permission/quota check)
    source VARCHAR(20) NOT NULL DEFAULT 'discovered',    -- discovered | manual
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_provider_model UNIQUE (provider_id, model_id)
);

COMMENT ON TABLE public.ai_models IS 'Models per provider; enabled+available = visible in client Brain selector.';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_ai_models_provider ON public.ai_models(provider_id);
CREATE INDEX IF NOT EXISTS idx_ai_models_enabled ON public.ai_models(enabled, available) WHERE enabled AND available;

-- RLS (project pattern: anon revoked)
ALTER TABLE public.ai_providers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_models ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY "Allow all access to service_role" ON public.ai_providers
        FOR ALL USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE POLICY "Allow all access to service_role" ON public.ai_models
        FOR ALL USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN null; END $$;

REVOKE ALL ON public.ai_providers FROM anon;
REVOKE ALL ON public.ai_models FROM anon;

-- updated_at trigger
DROP TRIGGER IF EXISTS trg_ai_providers_updated_at ON public.ai_providers;
CREATE TRIGGER trg_ai_providers_updated_at
    BEFORE UPDATE ON public.ai_providers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_ai_models_updated_at ON public.ai_models;
CREATE TRIGGER trg_ai_models_updated_at
    BEFORE UPDATE ON public.ai_models
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Client brain selection (which model the user's agent uses)
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS agent_brain VARCHAR(160);
COMMENT ON COLUMN public.users.agent_brain IS 'Selected model ref: provider_key/model_id — shown only from enabled+available models.';
