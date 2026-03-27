CREATE TABLE IF NOT EXISTS memory_versions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id uuid NOT NULL,
    version_number int NOT NULL,
    content text,
    metadata jsonb DEFAULT '{}',
    omega_score float DEFAULT 0,
    created_at timestamptz DEFAULT now()
);
ALTER TABLE memory_versions ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS "Service role full on memory_versions" ON memory_versions FOR ALL USING (auth.role() = 'service_role');
CREATE INDEX IF NOT EXISTS idx_memory_versions_mid ON memory_versions(memory_id, version_number DESC);
