-- Migration 007: Risk assessments table
-- Mirrors: app.models.risk.RiskAssessmentCreate / RiskAssessmentRead
-- contributing_factors stored as JSONB array

CREATE TABLE risk_assessments (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id            UUID      NOT NULL REFERENCES triage_sessions(id) ON DELETE CASCADE,
    score                 FLOAT     NOT NULL CHECK (score BETWEEN 0.0 AND 1.0),
    acuity_level          SMALLINT  NOT NULL CHECK (acuity_level BETWEEN 1 AND 5),
    reasoning             TEXT      NOT NULL CHECK (char_length(reasoning) >= 1),
    contributing_factors  JSONB     NOT NULL DEFAULT '[]'::jsonb,
    similar_cases_count   INTEGER   NOT NULL DEFAULT 0 CHECK (similar_cases_count >= 0),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_risk_assessments_session_id ON risk_assessments (session_id);

CREATE INDEX idx_risk_assessments_acuity ON risk_assessments (acuity_level);

ALTER TABLE risk_assessments ENABLE ROW LEVEL SECURITY;
