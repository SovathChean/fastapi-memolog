-- Add bot_type column to telegram_users table
-- Allows distinguishing users by which bot they interact with

-- Add bot_type column with default 'memolog' for existing records
ALTER TABLE telegram_users
ADD COLUMN bot_type VARCHAR(50) NOT NULL DEFAULT 'memolog';

-- Drop existing unique constraint on telegram_id
DROP INDEX IF EXISTS idx_telegram_users_telegram_id;
ALTER TABLE telegram_users DROP CONSTRAINT IF EXISTS telegram_users_telegram_id_key;

-- Create composite unique constraint (telegram_id + bot_type)
ALTER TABLE telegram_users
ADD CONSTRAINT telegram_users_telegram_id_bot_type_key
UNIQUE (telegram_id, bot_type);

-- Create new index for efficient lookup by telegram_id and bot_type
CREATE INDEX idx_telegram_users_telegram_id_bot_type
ON telegram_users(telegram_id, bot_type);

-- Add documentation
COMMENT ON COLUMN telegram_users.bot_type IS 'Bot identifier: memolog, crypto, etc.';
