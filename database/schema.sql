-- ====================================================================
-- HudhudRadar: Supabase Production PostgreSQL Schema
-- Version: 1.0.0
-- Standards: Compliant with Zero-Assumption Policy & Strict Audit Trail
-- ====================================================================

-- Enable required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Clean existing types if necessary
DO $$ BEGIN
    CREATE TYPE lead_source_enum AS ENUM ('facebook', 'instagram', 'manual', 'other');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE platform_enum AS ENUM ('facebook', 'instagram', 'system');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE sender_enum AS ENUM ('lead', 'agent', 'admin');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE verification_status_enum AS ENUM ('pending', 'approved', 'rejected');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE activity_status_enum AS ENUM ('success', 'failed', 'in_progress', 'throttled');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- --------------------------------------------------------------------
-- 1. Table: leads
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source lead_source_enum NOT NULL DEFAULT 'other',
    full_name VARCHAR(255),
    username VARCHAR(255),
    profile_url TEXT,
    bio TEXT,
    location VARCHAR(255),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    facebook_account_id VARCHAR(255),
    instagram_account_id VARCHAR(255),
    linked_account_id UUID REFERENCES public.leads(id) ON DELETE SET NULL,
    data_provenance JSONB NOT NULL DEFAULT '{
        "collected_at": null,
        "source": null,
        "verification_method": "direct",
        "provenance_notes": []
    }'::jsonb,
    is_verified_link BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Comments on leads table
COMMENT ON TABLE public.leads IS 'Stores leads captured with zero fabrication and complete provenance tracking.';
COMMENT ON COLUMN public.leads.linked_account_id IS 'Points to another confirmed lead record belonging to the same human identity.';
COMMENT ON COLUMN public.leads.data_provenance IS 'Audit metadata detailing where every piece of information originated and verification history.';

-- --------------------------------------------------------------------
-- 2. Table: messages
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL REFERENCES public.leads(id) ON DELETE CASCADE,
    platform platform_enum NOT NULL,
    platform_message_id VARCHAR(255) UNIQUE,
    sender_type sender_enum NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.messages IS 'Stores granular conversation history strictly linked to leads.';

-- --------------------------------------------------------------------
-- 3. Table: identity_verification_queue
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.identity_verification_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    primary_lead_id UUID NOT NULL REFERENCES public.leads(id) ON DELETE CASCADE,
    candidate_lead_id UUID NOT NULL REFERENCES public.leads(id) ON DELETE CASCADE,
    match_reason TEXT NOT NULL,
    confidence_score DECIMAL(5,2) NOT NULL CHECK (confidence_score >= 0.00 AND confidence_score <= 1.00),
    status verification_status_enum NOT NULL DEFAULT 'pending',
    reviewed_by VARCHAR(255),
    reviewed_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_lead_pair UNIQUE (primary_lead_id, candidate_lead_id)
);

COMMENT ON TABLE public.identity_verification_queue IS 'Queue of ambiguous identity matches requiring explicit human review before merging.';

-- --------------------------------------------------------------------
-- 4. Table: activity_logs
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_type VARCHAR(100) NOT NULL,
    platform platform_enum NOT NULL DEFAULT 'system',
    target_id VARCHAR(255),
    status activity_status_enum NOT NULL DEFAULT 'in_progress',
    error_reason TEXT,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.activity_logs IS 'Immutable audit trail of all agent actions, successes, and failure root causes.';

-- --------------------------------------------------------------------
-- 5. Table: page_performance_metrics
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.page_performance_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform platform_enum NOT NULL,
    metric_date DATE NOT NULL,
    reach BIGINT NOT NULL DEFAULT 0,
    impressions BIGINT NOT NULL DEFAULT 0,
    engagement_rate DECIMAL(6,3) NOT NULL DEFAULT 0.000,
    followers_count BIGINT NOT NULL DEFAULT 0,
    leads_captured INT NOT NULL DEFAULT 0,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_platform_date UNIQUE (platform, metric_date)
);

-- --------------------------------------------------------------------
-- 6. Table: campaigns
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    platform platform_enum NOT NULL,
    target_criteria JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    total_contacts INT NOT NULL DEFAULT 0,
    messages_sent INT NOT NULL DEFAULT 0,
    messages_failed INT NOT NULL DEFAULT 0,
    conversions_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- --------------------------------------------------------------------
-- Indexes for High Performance Querying
-- --------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_leads_facebook_id ON public.leads(facebook_account_id) WHERE facebook_account_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_leads_instagram_id ON public.leads(instagram_account_id) WHERE instagram_account_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_leads_username ON public.leads(username) WHERE username IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_leads_linked_account ON public.leads(linked_account_id) WHERE linked_account_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_messages_lead_id ON public.messages(lead_id);
CREATE INDEX IF NOT EXISTS idx_messages_sent_at ON public.messages(sent_at);
CREATE INDEX IF NOT EXISTS idx_messages_platform_msg_id ON public.messages(platform_message_id) WHERE platform_message_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_verification_status ON public.identity_verification_queue(status);
CREATE INDEX IF NOT EXISTS idx_activity_logs_status_time ON public.activity_logs(status, executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_page_metrics_date ON public.page_performance_metrics(platform, metric_date DESC);

-- --------------------------------------------------------------------
-- Automatic updated_at Trigger Function
-- --------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS trg_leads_updated_at ON public.leads;
CREATE TRIGGER trg_leads_updated_at
    BEFORE UPDATE ON public.leads
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_campaigns_updated_at ON public.campaigns;
CREATE TRIGGER trg_campaigns_updated_at
    BEFORE UPDATE ON public.campaigns
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- --------------------------------------------------------------------
-- Row-Level Security (RLS) Configuration
-- --------------------------------------------------------------------
ALTER TABLE public.leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.identity_verification_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.activity_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.page_performance_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.campaigns ENABLE ROW LEVEL SECURITY;

-- Allow authenticated service_role full access
DO $$ BEGIN
    CREATE POLICY "Service role full access on leads" ON public.leads
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE POLICY "Service role full access on messages" ON public.messages
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE POLICY "Service role full access on verification queue" ON public.identity_verification_queue
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE POLICY "Service role full access on activity logs" ON public.activity_logs
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE POLICY "Service role full access on page metrics" ON public.page_performance_metrics
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE POLICY "Service role full access on campaigns" ON public.campaigns
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- --------------------------------------------------------------------
-- 7. Table: content_posts (AI & Manual Posts, Reels, Stories)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.content_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(50) NOT NULL DEFAULT 'both',
    post_type VARCHAR(50) NOT NULL DEFAULT 'post',
    content_text TEXT NOT NULL,
    media_urls JSONB DEFAULT '[]'::jsonb,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    scheduled_for TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    meta_post_id VARCHAR(255),
    creation_mode VARCHAR(50) NOT NULL DEFAULT 'ai_generated',
    generation_prompt TEXT,
    error_message TEXT,
    performance_metrics JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.content_posts ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY "Service role full access on content_posts" ON public.content_posts
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- --------------------------------------------------------------------
-- 8. Table: users (Authentication & Future SaaS Multi-Tenancy)
-- --------------------------------------------------------------------
DO $$ BEGIN
    CREATE TYPE user_role_enum AS ENUM ('admin', 'user');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(50),
    full_name VARCHAR(255),
    password_hash TEXT NOT NULL,
    role user_role_enum NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT true,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY "Service role full access on users" ON public.users
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- --------------------------------------------------------------------
-- 9. Table: processed_events (Webhook Idempotency / Deduplication)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.processed_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_key VARCHAR(255) NOT NULL UNIQUE,
    event_type VARCHAR(50) NOT NULL DEFAULT 'message',
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_processed_events_key ON public.processed_events(event_key);
CREATE INDEX IF NOT EXISTS idx_processed_events_time ON public.processed_events(processed_at DESC);

ALTER TABLE public.processed_events ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY "Service role full access on processed_events" ON public.processed_events
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- --------------------------------------------------------------------
-- 10. Table: app_settings (Serverless-safe key/value persistence)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.app_settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.app_settings ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY "Service role full access on app_settings" ON public.app_settings
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- --------------------------------------------------------------------
-- 11. leads.human_takeover (Human-in-the-loop inbox control)
-- --------------------------------------------------------------------
ALTER TABLE public.leads ADD COLUMN IF NOT EXISTS human_takeover BOOLEAN NOT NULL DEFAULT false;


-- --------------------------------------------------------------------
-- 12. Table: platform_connections (Phase 9.7 — per-user connections)
-- Every user connects THEIR OWN accounts; tokens ENCRYPTED at rest
-- (Fernet key derived from SECRET_KEY — src/core/crypto.py).
-- Entitlements (user_entitlements) remain the only permission source.
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.platform_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    platform VARCHAR(30) NOT NULL CHECK (platform IN ('facebook','instagram','threads')),
    account_id VARCHAR(120),
    account_name VARCHAR(160),
    access_token_encrypted TEXT NOT NULL,
    token_expires_at TIMESTAMPTZ,
    scopes TEXT NOT NULL DEFAULT '{}',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
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

ALTER TABLE public.platform_connections ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY "Service role full access on platform_connections" ON public.platform_connections
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- --------------------------------------------------------------------
-- Backend-only Data API access alignment
-- --------------------------------------------------------------------
-- The browser talks to this application through FastAPI, never directly to
-- Supabase Data API. Keep all application-table CRUD server-side.
REVOKE ALL ON TABLE public.app_settings, public.leads, public.messages,
    public.identity_verification_queue, public.activity_logs,
    public.page_performance_metrics, public.campaigns, public.content_posts,
    public.users, public.processed_events, public.platform_connections
    FROM anon, authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.app_settings, public.leads,
    public.messages, public.identity_verification_queue, public.activity_logs,
    public.page_performance_metrics, public.campaigns, public.content_posts,
    public.users, public.processed_events, public.platform_connections
    TO service_role;

COMMENT ON TABLE public.app_settings IS
    'Server-managed application configuration. Never expose credentials to browser clients.';