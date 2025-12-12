-- Add user_id to tasks table for multi-user support
-- This migration deletes existing tasks (as confirmed by user)

-- Step 1: Delete all existing tasks (they have no user association)
DELETE FROM tasks;

-- Step 2: Add user_id column (NOT NULL since we deleted all tasks)
ALTER TABLE tasks ADD COLUMN user_id INTEGER NOT NULL;

-- Step 3: Add foreign key constraint
ALTER TABLE tasks
ADD CONSTRAINT fk_tasks_user
FOREIGN KEY (user_id) REFERENCES telegram_users(id) ON DELETE CASCADE;

-- Step 4: Create composite index for efficient user+period queries
CREATE INDEX IF NOT EXISTS idx_tasks_user_period
ON tasks(user_id, period_type, period_date);

-- Step 5: Create index for user+status queries
CREATE INDEX IF NOT EXISTS idx_tasks_user_status
ON tasks(user_id, status);

-- Add comment for documentation
COMMENT ON COLUMN tasks.user_id IS 'Foreign key to telegram_users - each user has isolated tasks';
