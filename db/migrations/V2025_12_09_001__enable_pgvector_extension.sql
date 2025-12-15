-- Migration: Enable pgvector extension and create utility functions
-- Description: Enable pgvector extension for vector similarity search in memolog
-- Date: 2025-12-09

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Create utility function for auto-updating updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ROLLBACK:
-- DROP FUNCTION IF EXISTS update_updated_at_column();
-- DROP EXTENSION IF EXISTS vector;
