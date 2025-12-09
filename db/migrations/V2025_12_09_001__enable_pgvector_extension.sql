-- Migration: Enable pgvector extension
-- Description: Enable pgvector extension for vector similarity search in memolog
-- Date: 2025-12-09

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- ROLLBACK:
-- DROP EXTENSION IF EXISTS vector;
