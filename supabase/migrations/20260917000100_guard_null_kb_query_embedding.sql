-- A Python-side keyword fallback handles an unavailable embedding.  This
-- database guard makes the same invariant hold for any future RPC caller:
-- NULL vectors must never be ranked as if they were semantically relevant.

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
        WHERE query_embedding IS NOT NULL
          AND c.embedding IS NOT NULL
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
