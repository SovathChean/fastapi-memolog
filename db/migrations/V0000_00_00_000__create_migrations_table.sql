-- Migration: Create schema_migrations tracking table
-- Version: V0000_00_00_000
-- Created: 2025-12-05
-- Description: Bootstrap migration that creates the migrations tracking table

CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    version VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_schema_migrations_version ON schema_migrations(version);

-- ROLLBACK:
-- DROP INDEX IF EXISTS idx_schema_migrations_version;
-- DROP TABLE IF EXISTS schema_migrations;
