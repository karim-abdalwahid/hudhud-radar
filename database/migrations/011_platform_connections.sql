-- Migration 011: platform_connections (Phase 9.7 — Wave 9.1 skeleton, deferred)
-- Per-user platform connections: every user connects THEIR OWN accounts.
-- Tokens stored ENCRYPTED (Fernet, key derived from SECRET_KEY in src/core/crypto.py).
-- Entitlements (user_entitlements, migration 009) remain the ONLY source of
-- permission — a connection never grants service by itself (fail-closed gates).

CREATE TABLE IF NOT EXISTS public.platform_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    platform VARCHAR(30) NOT NULL CHECK (platform IN ('facebook','instagram','threads')),
    account_id VARCHAR(120),                        -- page_id / ig user_id / threads user_id
    account_name VARCHAR(160),                      -- human-readable (@username / page name)
    access_token_encrypted TEXT NOT NULL,           -- never plaintext
    token_expires_at TIMESTAMPTZ,                   -- null = never (page tokens)
    scopes TEXT NOT NULL DEFAULT '{}',              -- granted scopes array
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,    -- linked_ig_id, page_id, discovered upsell data
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','revoked','expired')),
    connected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_platform_conn_user_platform_account
    ON public.platform_connections (user_id, platform, account_id);
CREATE INDEX IF NOT EXISTS idx_platform_conn_user ON public.platform_connections (user_id);
CREATE INDEX IF NOT EXISTS idx_platform_conn_user_platform
    ON public.platform_connections (user_id, platform, status);

-- updated_at trigger (SOP-03 principle 4)
CREATE OR REPLACE FUNCTION public.touch_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_platform_connections_updated_at ON public.platform_connections;
CREATE TRIGGER trg_platform_connections_updated_at
    BEFORE UPDATE ON public.platform_connections
    FOR EACH ROW EXECUTE FUNCTION public.touch_updated_at();

-- RLS: house pattern (service_role full access; anon already revoked platform-wide)
ALTER TABLE public.platform_connections ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY "Service role full access on platform_connections" ON public.platform_connections
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
