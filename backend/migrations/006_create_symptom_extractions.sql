-- Migration 006: Symptom extractions table
-- Mirrors: app.models.symptoms.SymptomExtractionCreate / SymptomExtractionRead
-- symptoms and follow_up_questions stored as JSONB arrays

CREATE TABLE symptom_extractions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID         NOT NULL REFERENCES triage_sessions(id) ON DELETE CASCADE,
    chief_complaint     VARCHAR(500) NOT NULL CHECK (char_length(chief_complaint) >= 1),
    symptoms            JSONB        NOT NULL DEFAULT '[]'::jsonb,
    follow_up_questions JSONB        NOT NULL DEFAULT '[]'::jsonb,
    confidence          FLOAT        NOT NULL CHECK (confidence BETWEEN 0.0 AND 1.0),
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_symptom_extractions_session_id ON symptom_extractions (session_id);

ALTER TABLE symptom_extractions ENABLE ROW LEVEL SECURITY;
