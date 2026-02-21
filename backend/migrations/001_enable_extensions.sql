-- Migration 001: Enable required PostgreSQL extensions
-- pgvector: vector similarity search for historical case matching
-- pgcrypto: gen_random_uuid() for UUID primary key generation

CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
