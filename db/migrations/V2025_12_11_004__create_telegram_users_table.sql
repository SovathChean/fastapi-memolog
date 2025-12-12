-- Create telegram_users table for storing Telegram user information
-- Each Telegram user will have their own isolated task list

CREATE TABLE IF NOT EXISTS telegram_users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    chat_id BIGINT,
    username VARCHAR(255),
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255),
    language_code VARCHAR(10),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Index for efficient lookup by telegram_id
CREATE INDEX IF NOT EXISTS idx_telegram_users_telegram_id ON telegram_users(telegram_id);

-- Index for active users
CREATE INDEX IF NOT EXISTS idx_telegram_users_active ON telegram_users(is_active) WHERE is_active = TRUE;

-- Add comments for documentation
COMMENT ON TABLE telegram_users IS 'Stores Telegram user information for multi-user task management';
COMMENT ON COLUMN telegram_users.telegram_id IS 'Unique Telegram user ID from update.effective_user.id';
COMMENT ON COLUMN telegram_users.chat_id IS 'Chat ID for sending messages to user';
COMMENT ON COLUMN telegram_users.username IS 'Telegram @username (optional)';
COMMENT ON COLUMN telegram_users.is_active IS 'Whether user is active (can be deactivated)';
