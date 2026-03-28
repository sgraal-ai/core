CREATE TABLE IF NOT EXISTS agent_registry (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), api_key_hash text NOT NULL, agent_id text NOT NULL, memory_count int DEFAULT 0, last_seen timestamptz DEFAULT now(), created_at timestamptz DEFAULT now(), UNIQUE(api_key_hash, agent_id));
ALTER TABLE agent_registry ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS "Service role full on agent_registry" ON agent_registry FOR ALL USING (auth.role() = 'service_role');
