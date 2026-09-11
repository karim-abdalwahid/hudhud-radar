-- Migration 017 (Wave 9.8): per-user Knowledge Base schema upgrade.
--
-- 1. Filenames become unique PER USER (not globally): the global unique on
--    filename prevented two users from owning the same document name.
--    Legacy NULL-user rows collapse under a sentinel UUID for uniqueness.
-- 2. match_kb_chunks RPC gains an optional p_user_id: when provided, search
--    is scoped to that user's documents; when NULL, legacy behavior (all).

-- 1a. Replace the global filename uniqueness with per-user uniqueness
ALTER TABLE public.kb_documents DROP CONSTRAINT IF EXISTS kb_documents_filename_key;
CREATE UNIQUE INDEX IF NOT EXISTS uq_kb_documents_user_filename
    ON public.kb_documents (COALESCE(user_id, '00000000-0000-0000-0000-000000000000'::uuid), filename);

-- 1b. Drop the orphaned plain user index (superseded by the composite one)
DROP INDEX IF EXISTS public.idx_kb_documents_user;

-- 2. User-scoped hybrid search (same RRF scoring; optional owner filter)
CREATE OR REPLACE FUNCTION public.match_kb_chunks(
    query_embedding vector,
    query_text text,
    match_count integer DEFAULT 5,
    p_user_id uuid DEFAULT NULL
)
 RETURNS TABLE(document_id uuid, filename character varying, chunk_index integer, chunk_text text, score double precision)
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
          AND (p_user_id IS NULL OR d.user_id = p_user_id)
        ORDER BY c.embedding <=> query_embedding
        LIMIT match_count * 4
    ),
    keyword AS (
        SELECT c.id, c.document_id, d.filename, c.chunk_index, c.chunk_text,
               row_number() OVER (ORDER BY ts_rank(c.tsv, websearch_to_tsquery('simple', query_text)) DESC) AS rn
        FROM kb_chunks c
        JOIN kb_documents d ON d.id = c.document_id
        WHERE c.tsv @@ websearch_to_tsquery('simple', query_text)
          AND (p_user_id IS NULL OR d.user_id = p_user_id)
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
