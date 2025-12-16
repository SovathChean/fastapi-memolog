-- Migration: Create crypto_trades table
-- Description: Create crypto_trades table for crypto profit/loss tracking
-- Date: 2025-12-16

-- Create crypto_trades table for P&L tracking
CREATE TABLE IF NOT EXISTS crypto_trades (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES telegram_users(id) ON DELETE CASCADE,
    coin VARCHAR(50) NOT NULL,
    budget NUMERIC(18, 8) NOT NULL,
    entry NUMERIC(18, 8) NOT NULL,
    stoploss NUMERIC(18, 8) NOT NULL,
    take_profit NUMERIC(18, 8),
    exit_price NUMERIC(18, 8),
    leverage INTEGER NOT NULL DEFAULT 50,
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    profit NUMERIC(18, 8),
    loss NUMERIC(18, 8),
    reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_crypto_trades_user_id ON crypto_trades(user_id);
CREATE INDEX IF NOT EXISTS idx_crypto_trades_coin ON crypto_trades(coin);
CREATE INDEX IF NOT EXISTS idx_crypto_trades_status ON crypto_trades(status);
CREATE INDEX IF NOT EXISTS idx_crypto_trades_created_at ON crypto_trades(created_at);

-- Auto-update trigger for updated_at
CREATE TRIGGER update_crypto_trades_updated_at
    BEFORE UPDATE ON crypto_trades
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ROLLBACK:
-- DROP TRIGGER IF EXISTS update_crypto_trades_updated_at ON crypto_trades;
-- DROP INDEX IF EXISTS idx_crypto_trades_created_at;
-- DROP INDEX IF EXISTS idx_crypto_trades_status;
-- DROP INDEX IF EXISTS idx_crypto_trades_coin;
-- DROP INDEX IF EXISTS idx_crypto_trades_user_id;
-- DROP TABLE IF EXISTS crypto_trades;
