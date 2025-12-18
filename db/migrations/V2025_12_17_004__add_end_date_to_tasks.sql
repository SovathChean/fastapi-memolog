-- Migration: V2025_12_17_004__add_end_date_to_tasks
-- Description: Add end_date column to tasks table for multi-day daily tasks

ALTER TABLE tasks ADD COLUMN end_date DATE;

-- Create index for end_date queries
CREATE INDEX idx_tasks_end_date ON tasks(end_date);

COMMENT ON COLUMN tasks.end_date IS 'Optional end date for multi-day daily tasks';
