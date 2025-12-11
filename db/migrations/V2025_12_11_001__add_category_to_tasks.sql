-- Migration: Add category column to tasks table
-- Description: Add category field for task grouping (Work, Personal, etc.)
-- Date: 2025-12-11

-- Add category column with default value 'General'
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS category VARCHAR(100) DEFAULT 'General';

-- Index for category-based queries
CREATE INDEX IF NOT EXISTS idx_tasks_category ON tasks(category);

-- Combined index for category + period queries
CREATE INDEX IF NOT EXISTS idx_tasks_category_period ON tasks(category, period_type, period_date);

-- ROLLBACK:
-- DROP INDEX IF EXISTS idx_tasks_category_period;
-- DROP INDEX IF EXISTS idx_tasks_category;
-- ALTER TABLE tasks DROP COLUMN IF EXISTS category;
