-- Add completion_note column to tasks table
-- Allows users to add a note when marking a task as completed

ALTER TABLE tasks
ADD COLUMN IF NOT EXISTS completion_note TEXT;

-- Add comment for documentation
COMMENT ON COLUMN tasks.completion_note IS 'Optional note added when completing a task';
