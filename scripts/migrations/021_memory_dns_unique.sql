-- Memory-DNS: unique constraint on (org_id, entry_id) for URI collision prevention
ALTER TABLE memory_store ADD COLUMN IF NOT EXISTS uri text;
CREATE UNIQUE INDEX IF NOT EXISTS idx_memory_store_uri ON memory_store (uri) WHERE uri IS NOT NULL;
