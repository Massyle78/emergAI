-- Migration 003: Patients table
-- Mirrors: app.models.patient.PatientCreate / PatientRead

CREATE TABLE patients (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name            VARCHAR(100)  NOT NULL CHECK (char_length(first_name) >= 1),
    last_name             VARCHAR(100)  NOT NULL CHECK (char_length(last_name) >= 1),
    date_of_birth         DATE          NOT NULL CHECK (date_of_birth <= CURRENT_DATE),
    phone                 VARCHAR(20),
    medical_record_number VARCHAR(50),
    created_at            TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_patients_mrn ON patients (medical_record_number)
    WHERE medical_record_number IS NOT NULL;

CREATE INDEX idx_patients_last_name ON patients (last_name);

CREATE TRIGGER trg_patients_updated_at
    BEFORE UPDATE ON patients
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
