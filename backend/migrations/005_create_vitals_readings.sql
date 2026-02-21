-- Migration 005: Vitals readings table with medical-range CHECK constraints
-- Mirrors: app.models.vitals.VitalsCreate / VitalsRead
-- Constraint bounds match constants in app.models.vitals

CREATE TABLE vitals_readings (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id       UUID    NOT NULL REFERENCES triage_sessions(id) ON DELETE CASCADE,
    heart_rate_bpm   FLOAT   NOT NULL CHECK (heart_rate_bpm BETWEEN 20.0 AND 300.0),
    spo2_percent     FLOAT            CHECK (spo2_percent BETWEEN 0.0 AND 100.0),
    respiratory_rate FLOAT            CHECK (respiratory_rate BETWEEN 4.0 AND 60.0),
    systolic_bp      FLOAT            CHECK (systolic_bp BETWEEN 40.0 AND 300.0),
    diastolic_bp     FLOAT            CHECK (diastolic_bp BETWEEN 20.0 AND 200.0),
    confidence       FLOAT   NOT NULL CHECK (confidence BETWEEN 0.0 AND 1.0),
    recorded_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_vitals_readings_session_id ON vitals_readings (session_id);

ALTER TABLE vitals_readings ENABLE ROW LEVEL SECURITY;
