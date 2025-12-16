-- Add direction column to crypto_trades table
-- Tracks if the trade is Long or Short

ALTER TABLE crypto_trades
ADD COLUMN direction VARCHAR(10) NOT NULL DEFAULT 'long';

-- Add comment
COMMENT ON COLUMN crypto_trades.direction IS 'Trade direction: long or short';
