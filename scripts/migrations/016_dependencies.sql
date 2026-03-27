CREATE TABLE IF NOT EXISTS memory_dependencies (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), api_key_hash text, source_id text, target_id text, relationship text DEFAULT 'depends_on', created_at timestamptz DEFAULT now());
ALTER TABLE memory_dependencies ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS "Service role full on memory_dependencies" ON memory_dependencies FOR ALL USING (auth.role() = 'service_role');
