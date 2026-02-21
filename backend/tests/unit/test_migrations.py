"""Tests validating migration file structure and model-schema alignment.

These tests verify migrations without a live database (Rule 2).
They parse SQL text to confirm tables, columns, constraints, and
foreign keys align with the Pydantic domain models.
"""

import re
from pathlib import Path

import pytest

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"

EXPECTED_FILES = [
    "001_enable_extensions.sql",
    "002_create_updated_at_trigger.sql",
    "003_create_patients.sql",
    "004_create_triage_sessions.sql",
    "005_create_vitals_readings.sql",
    "006_create_symptom_extractions.sql",
    "007_create_risk_assessments.sql",
    "008_create_similarity_search_function.sql",
]


def _read_migration(filename: str) -> str:
    """Read a migration file and return its contents."""
    return (MIGRATIONS_DIR / filename).read_text(encoding="utf-8")


class TestMigrationFilesExist:
    def test_all_migration_files_present(self):
        actual = sorted(f.name for f in MIGRATIONS_DIR.glob("*.sql"))
        assert actual == sorted(EXPECTED_FILES)

    def test_files_are_sequentially_numbered(self):
        numbers = [int(f.split("_")[0]) for f in EXPECTED_FILES]
        assert numbers == list(range(1, len(EXPECTED_FILES) + 1))

    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_migration_is_not_empty(self, filename: str):
        content = _read_migration(filename)
        stripped = content.strip()
        assert len(stripped) > 0


class TestExtensionsMigration:
    def test_enables_pgvector(self):
        sql = _read_migration("001_enable_extensions.sql")
        assert 'CREATE EXTENSION IF NOT EXISTS "vector"' in sql

    def test_enables_pgcrypto(self):
        sql = _read_migration("001_enable_extensions.sql")
        assert 'CREATE EXTENSION IF NOT EXISTS "pgcrypto"' in sql


class TestUpdatedAtTrigger:
    def test_creates_function(self):
        sql = _read_migration("002_create_updated_at_trigger.sql")
        assert "CREATE OR REPLACE FUNCTION set_updated_at()" in sql
        assert "NEW.updated_at" in sql


class TestPatientsTable:
    @pytest.fixture()
    def sql(self) -> str:
        return _read_migration("003_create_patients.sql")

    def test_creates_table(self, sql: str):
        assert "CREATE TABLE patients" in sql

    def test_has_uuid_primary_key(self, sql: str):
        assert "id" in sql
        assert "UUID PRIMARY KEY" in sql

    def test_has_required_columns(self, sql: str):
        for col in ["first_name", "last_name", "date_of_birth",
                     "phone", "medical_record_number",
                     "created_at", "updated_at"]:
            assert col in sql, f"Missing column: {col}"

    def test_varchar_lengths_match_model(self, sql: str):
        assert "VARCHAR(100)" in sql
        assert "VARCHAR(20)" in sql
        assert "VARCHAR(50)" in sql

    def test_has_dob_check_constraint(self, sql: str):
        assert "date_of_birth <= CURRENT_DATE" in sql

    def test_has_updated_at_trigger(self, sql: str):
        assert "trg_patients_updated_at" in sql

    def test_enables_rls(self, sql: str):
        assert "ENABLE ROW LEVEL SECURITY" in sql

    def test_has_mrn_index(self, sql: str):
        assert "idx_patients_mrn" in sql


class TestTriageSessionsTable:
    @pytest.fixture()
    def sql(self) -> str:
        return _read_migration("004_create_triage_sessions.sql")

    def test_creates_table(self, sql: str):
        assert "CREATE TABLE triage_sessions" in sql

    def test_has_patient_fk(self, sql: str):
        assert "REFERENCES patients(id)" in sql

    def test_has_status_check(self, sql: str):
        for status in ["pending", "capturing", "processing",
                        "awaiting_review", "completed", "cancelled"]:
            assert f"'{status}'" in sql

    def test_has_embedding_column(self, sql: str):
        assert "vector(768)" in sql

    def test_has_vector_index(self, sql: str):
        assert "ivfflat" in sql
        assert "vector_cosine_ops" in sql

    def test_has_updated_at_trigger(self, sql: str):
        assert "trg_triage_sessions_updated_at" in sql

    def test_enables_rls(self, sql: str):
        assert "ENABLE ROW LEVEL SECURITY" in sql


class TestVitalsReadingsTable:
    @pytest.fixture()
    def sql(self) -> str:
        return _read_migration("005_create_vitals_readings.sql")

    def test_creates_table(self, sql: str):
        assert "CREATE TABLE vitals_readings" in sql

    def test_has_session_fk(self, sql: str):
        assert "REFERENCES triage_sessions(id)" in sql

    def test_heart_rate_range_matches_model(self, sql: str):
        assert "heart_rate_bpm BETWEEN 20.0 AND 300.0" in sql

    def test_spo2_range_matches_model(self, sql: str):
        assert "spo2_percent BETWEEN 0.0 AND 100.0" in sql

    def test_respiratory_rate_range_matches_model(self, sql: str):
        assert "respiratory_rate BETWEEN 4.0 AND 60.0" in sql

    def test_bp_ranges_match_model(self, sql: str):
        assert "systolic_bp BETWEEN 40.0 AND 300.0" in sql
        assert "diastolic_bp BETWEEN 20.0 AND 200.0" in sql

    def test_confidence_range(self, sql: str):
        assert "confidence BETWEEN 0.0 AND 1.0" in sql

    def test_enables_rls(self, sql: str):
        assert "ENABLE ROW LEVEL SECURITY" in sql


class TestSymptomExtractionsTable:
    @pytest.fixture()
    def sql(self) -> str:
        return _read_migration("006_create_symptom_extractions.sql")

    def test_creates_table(self, sql: str):
        assert "CREATE TABLE symptom_extractions" in sql

    def test_has_session_fk(self, sql: str):
        assert "REFERENCES triage_sessions(id)" in sql

    def test_chief_complaint_max_length(self, sql: str):
        assert "VARCHAR(500)" in sql

    def test_jsonb_columns(self, sql: str):
        assert re.search(r"symptoms\s+JSONB", sql)
        assert re.search(r"follow_up_questions\s+JSONB", sql)

    def test_confidence_range(self, sql: str):
        assert "confidence BETWEEN 0.0 AND 1.0" in sql

    def test_enables_rls(self, sql: str):
        assert "ENABLE ROW LEVEL SECURITY" in sql


class TestRiskAssessmentsTable:
    @pytest.fixture()
    def sql(self) -> str:
        return _read_migration("007_create_risk_assessments.sql")

    def test_creates_table(self, sql: str):
        assert "CREATE TABLE risk_assessments" in sql

    def test_has_session_fk(self, sql: str):
        assert "REFERENCES triage_sessions(id)" in sql

    def test_score_range(self, sql: str):
        assert "score BETWEEN 0.0 AND 1.0" in sql

    def test_acuity_range_matches_esi(self, sql: str):
        assert "acuity_level BETWEEN 1 AND 5" in sql

    def test_contributing_factors_jsonb(self, sql: str):
        assert re.search(r"contributing_factors\s+JSONB", sql)

    def test_similar_cases_non_negative(self, sql: str):
        assert "similar_cases_count >= 0" in sql

    def test_has_acuity_index(self, sql: str):
        assert "idx_risk_assessments_acuity" in sql

    def test_enables_rls(self, sql: str):
        assert "ENABLE ROW LEVEL SECURITY" in sql
