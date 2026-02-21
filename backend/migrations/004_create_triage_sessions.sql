-- Migration 004: Triage sessions table with pgvector embedding
-- Mirrors: app.models.triage.TriageSessionCreate / TriageSessionRead
-- embedding column: 768-dimensional vector for similarity search (Phase 11)

CREATE TABLE triage_sessions (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id   UUID         NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    status       VARCHAR(20)  NOT NULL DEFAULT 'pending'
                 CHECK (status IN (
                     'pending', 'capturing', 'processing',
                     'awaiting_review', 'completed', 'cancelled'
                 )),
    started_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    embedding    vector(768),
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_triage_sessions_patient_id ON triage_sessions (patient_id);

CREATE INDEX idx_triage_sessions_status ON triage_sessions (status);

CREATE INDEX idx_triage_sessions_embedding ON triage_sessions
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE TRIGGER trg_triage_sessions_updated_at
    BEFORE UPDATE ON triage_sessions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

ALTER TABLE triage_sessions ENABLE ROW LEVEL SECURITY;
