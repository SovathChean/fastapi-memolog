-- Migration: Create tasks table
-- Description: Create tasks table for memolog task tracking with vector embeddings
-- Date: 2025-12-09

-- Create tasks table for memolog task tracking
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    period_type VARCHAR(20) NOT NULL DEFAULT 'daily',
    period_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    completed_at TIMESTAMP WITH TIME ZONE,
    pending_reason TEXT,
    embedding vector(1536),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_tasks_period_type ON tasks(period_type);
CREATE INDEX IF NOT EXISTS idx_tasks_period_date ON tasks(period_date);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_period_type_date ON tasks(period_type, period_date);

-- IVFFlat index for vector similarity search (cosine distance)
-- Note: This index requires at least some data to be effective
-- For small datasets (<1000 rows), consider using HNSW instead or skip this index
CREATE INDEX IF NOT EXISTS idx_tasks_embedding ON tasks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Auto-update trigger for updated_at
-- Uses the existing update_updated_at_column() function from users migration
CREATE TRIGGER update_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ROLLBACK:
-- DROP TRIGGER IF EXISTS update_tasks_updated_at ON tasks;
-- DROP INDEX IF EXISTS idx_tasks_embedding;
-- DROP INDEX IF EXISTS idx_tasks_period_type_date;
-- DROP INDEX IF EXISTS idx_tasks_status;
-- DROP INDEX IF EXISTS idx_tasks_period_date;
-- DROP INDEX IF EXISTS idx_tasks_period_type;
-- DROP TABLE IF EXISTS tasks;
