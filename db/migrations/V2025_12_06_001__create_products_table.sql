-- Migration: Create products table
-- Version: V2025_12_06_001
-- Created: 2025-12-06
-- Description: Creates the products table with id, name, description fields

-- Create products table
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create index on name for faster lookups
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);

-- Create trigger for products table (reuses update_updated_at_column function from users migration)
DROP TRIGGER IF EXISTS update_products_updated_at ON products;
CREATE TRIGGER update_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ROLLBACK:
-- DROP TRIGGER IF EXISTS update_products_updated_at ON products;
-- DROP INDEX IF EXISTS idx_products_name;
-- DROP TABLE IF EXISTS products;