-- Add currency tracking to donations (safe to re-run)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'donations' AND column_name = 'currency'
    ) THEN
        ALTER TABLE donations ADD COLUMN currency TEXT DEFAULT 'usd';
    END IF;
END $$;
