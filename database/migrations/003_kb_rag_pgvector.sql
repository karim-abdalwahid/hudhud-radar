-- ============================================================
-- Migration 003: Knowledge Base in database + pgvector hybrid RAG
-- (Phase 5 of Roadmap v2 — approved: pgvector over LEANN)
-- ============================================================

-- 1. kb_documents: one row per knowledge document (replaces markdown files)
CREATE TABLE IF NOT EXISTS public.kb_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    filename VARCHAR(255) NOT NULL UNIQUE,
    content TEXT NOT NULL DEFAULT '',
    source VARCHAR(50) NOT NULL DEFAULT 'upload', -- upload | onboarding | meta_analysis | manual
    word_count INT NOT NULL DEFAULT 0,
    is_core BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.kb_documents IS 'Knowledge base documents (DB-backed, replaces markdown files; serverless-safe).';

-- 2. kb_chunks: semantic chunks with Gemini embeddings (768 dims) + full-text vector
CREATE TABLE IF NOT EXISTS public.kb_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES public.kb_documents(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL DEFAULT 0,
    chunk_text TEXT NOT NULL,
    embedding vector(768),
    tsv tsvector,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.kb_chunks IS 'RAG chunks: cosine via embedding (HNSW) + keyword via tsv (GIN), merged with RRF.';

-- 3. Indexes
CREATE INDEX IF NOT EXISTS idx_kb_chunks_embedding ON public.kb_chunks
    USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_kb_chunks_tsv ON public.kb_chunks USING gin (tsv);
CREATE INDEX IF NOT EXISTS idx_kb_chunks_doc ON public.kb_chunks(document_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_kb_documents_user ON public.kb_documents(user_id) WHERE user_id IS NOT NULL;

-- 4. RLS + grants (project pattern: anon revoked; service_role bypasses)
ALTER TABLE public.kb_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kb_chunks ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY "Allow all access to service_role" ON public.kb_documents
        FOR ALL USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE POLICY "Allow all access to service_role" ON public.kb_chunks
        FOR ALL USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN null; END $$;

REVOKE ALL ON public.kb_documents FROM anon;
REVOKE ALL ON public.kb_chunks FROM anon;

-- 5. updated_at trigger
DROP TRIGGER IF EXISTS trg_kb_documents_updated_at ON public.kb_documents;
CREATE TRIGGER trg_kb_documents_updated_at
    BEFORE UPDATE ON public.kb_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
