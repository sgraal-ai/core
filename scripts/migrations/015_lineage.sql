CREATE TABLE IF NOT EXISTS memory_lineage (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), memory_id uuid, changed_by_agent text, change_reason text, parent_version_id uuid, created_at timestamptz DEFAULT now());
ALTER TABLE memory_lineage ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS "Service role full on memory_lineage" ON memory_lineage FOR ALL USING (auth.role() = 'service_role');
