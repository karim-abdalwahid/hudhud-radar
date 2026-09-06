-- Migration 003c: switch to gemini-embedding-001 (3072 dims — text-embedding-004 retired)
ALTER TABLE public.kb_chunks DROP COLUMN IF EXISTS embedding;
ALTER TABLE public.kb_chunks ADD COLUMN embedding vector(3072);
DROP INDEX IF EXISTS idx_kb_chunks_embedding;
CREATE INDEX IF NOT EXISTS idx_kb_chunks_embedding ON public.kb_chunks
    USING hnsw (embedding vector_cosine_ops);

-- Update the RPC signature
CREATE OR REPLACE FUNCTION public.match_kb_chunks(
    query_embedding vector(3072),
    query_text text,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    document_id uuid,
    filename varchar,
    chunk_index int,
    chunk_text text,
    score float
)
LANGUAGE sql STABLE
SECURITY INVOKER
SET search_path = public
AS $$
    WITH semantic AS (
        SELECT c.id, c.document_id, d.filename, c.chunk_index, c.chunk_text,
               row_number() OVER (ORDER BY c.embedding <=> query_embedding) AS rn
        FROM kb_chunks c
        JOIN kb_documents d ON d.id = c.document_id
        WHERE c.embedding IS NOT NULL
        ORDER BY c.embedding <=> query_embedding
        LIMIT match_count * 4
    ),
    keyword AS (
        SELECT c.id, c.document_id, d.filename, c.chunk_index, c.chunk_text,
               row_number() OVER (ORDER BY ts_rank(c.tsv, websearch_to_tsquery('simple', query_text)) DESC) AS rn
        FROM kb_chunks c
        JOIN kb_documents d ON d.id = c.document_id
        WHERE c.tsv @@ websearch_to_tsquery('simple', query_text)
        LIMIT match_count * 4
    )
    SELECT
        COALESCE(s.document_id, k.document_id) AS document_id,
        COALESCE(s.filename, k.filename) AS filename,
        COALESCE(s.chunk_index, k.chunk_index) AS chunk_index,
        COALESCE(s.chunk_text, k.chunk_text) AS chunk_text,
        (COALESCE(1.0 / (60 + s.rn), 0) + COALESCE(1.0 / (60 + k.rn), 0))::float AS score
    FROM semantic s
    FULL OUTER JOIN keyword k ON s.id = k.id
    ORDER BY score DESC
    LIMIT match_count;
$$;

REVOKE ALL ON FUNCTION public.match_kb_chunks(vector(3072), text, int) FROM anon;
