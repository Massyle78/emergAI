-- Migration 008: Postgres function for cosine-similarity KNN search
-- Called via Supabase RPC: match_triage_sessions(query_embedding, match_count)
-- Uses the IVFFlat index created in migration 004.

CREATE OR REPLACE FUNCTION match_triage_sessions(
    query_embedding vector(768),
    match_count     INT DEFAULT 5
)
RETURNS TABLE (
    id          UUID,
    patient_id  UUID,
    status      VARCHAR(20),
    similarity  DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        ts.id,
        ts.patient_id,
        ts.status,
        1 - (ts.embedding <=> query_embedding) AS similarity
    FROM triage_sessions ts
    WHERE ts.embedding IS NOT NULL
    ORDER BY ts.embedding <=> query_embedding
    LIMIT match_count;
$$;
