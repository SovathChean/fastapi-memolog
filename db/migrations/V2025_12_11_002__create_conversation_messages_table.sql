-- Create conversation_messages table for storing Telegram chat history
-- Used for conversation memory and context retention across sessions

CREATE TABLE IF NOT EXISTS conversation_messages (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Index for efficient user history lookup (most recent first)
CREATE INDEX IF NOT EXISTS idx_conversation_messages_user_id
ON conversation_messages(telegram_user_id);

CREATE INDEX IF NOT EXISTS idx_conversation_user_created
ON conversation_messages(telegram_user_id, created_at DESC);

-- Add comment for documentation
COMMENT ON TABLE conversation_messages IS 'Stores Telegram conversation history for AI memory';
COMMENT ON COLUMN conversation_messages.role IS 'Message role: human or ai';
COMMENT ON COLUMN conversation_messages.extra_data IS 'Optional JSON extra data (query context, intent, etc.)';
