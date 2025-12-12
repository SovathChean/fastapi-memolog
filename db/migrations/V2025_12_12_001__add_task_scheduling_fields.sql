-- Add scheduling and priority fields to tasks
-- Priority: low, normal, high
-- Duration: stored as minutes
-- Time: start and optional end time
-- Date: optional scheduled date

ALTER TABLE tasks ADD COLUMN IF NOT EXISTS priority VARCHAR(20) DEFAULT 'normal' NOT NULL;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS duration_minutes INTEGER;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS scheduled_time TIME;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS scheduled_end_time TIME;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS scheduled_date DATE;

-- Index for queries by priority
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);

-- Index for queries by scheduled_date
CREATE INDEX IF NOT EXISTS idx_tasks_scheduled_date ON tasks(scheduled_date);

-- Index for queries by scheduled_time
CREATE INDEX IF NOT EXISTS idx_tasks_scheduled_time ON tasks(scheduled_time);
