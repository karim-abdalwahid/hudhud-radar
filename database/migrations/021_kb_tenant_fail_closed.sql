-- Migration 021: tenant-safe RAG retrieval.
--
-- The original 3-argument RPC remains a separate PostgreSQL overload after
-- migration 017 added p_user_id. Remove it and make the tenant parameter
-- mandatory so an accidental unscoped RPC call cannot search every document.

DROP FUNCTION IF EXISTS public.match_kb_chunks(vector, text, integer);
DROP FUNCTION IF EXISTS public.match_kb_chunks(vector, text, integer, uuid);

CREATE OR REPLACE FUNCTION public.match_kb_chunks(
    query_embedding vector,
    query_text text,
    match_count integer,
    p_user_id uuid
)
RETURNS TABLE(
    document_id uuid,
    filename character varying,
    chunk_index integer,
    chunk_text text,
    score double precision
)
LANGUAGE sql
STABLE
SET search_path TO 'public'
AS $function$
    WITH semantic AS (
        SELECT c.id, c.document_id, d.filename, c.chunk_index, c.chunk_text,
               row_number() OVER (ORDER BY c.embedding <=> query_embedding) AS rn
        FROM kb_chunks c
        JOIN kb_documents d ON d.id = c.document_id
        WHERE c.embedding IS NOT NULL
          AND d.user_id = p_user_id
        ORDER BY c.embedding <=> query_embedding
        LIMIT match_count * 4
    ),
    keyword AS (
        SELECT c.id, c.document_id, d.filename, c.chunk_index, c.chunk_text,
               row_number() OVER (
                   ORDER BY ts_rank(c.tsv, websearch_to_tsquery('simple', query_text)) DESC
               ) AS rn
        FROM kb_chunks c
        JOIN kb_documents d ON d.id = c.document_id
        WHERE c.tsv @@ websearch_to_tsquery('simple', query_text)
          AND d.user_id = p_user_id
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
$function$;

-- FastAPI is the only database client. Browser roles cannot read tenant data
-- nor invoke either the new RPC or any remaining privileged function.
ALTER TABLE public.kb_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kb_chunks ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.kb_documents, public.kb_chunks FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.kb_documents, public.kb_chunks TO service_role;

REVOKE ALL ON FUNCTION public.match_kb_chunks(vector, text, integer, uuid)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.match_kb_chunks(vector, text, integer, uuid)
    TO service_role;
