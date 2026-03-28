CREATE TABLE IF NOT EXISTS agent_identities (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), api_key_hash text NOT NULL, agent_id text NOT NULL, fingerprint text, metadata jsonb DEFAULT '{}', created_at timestamptz DEFAULT now(), UNIQUE(api_key_hash, agent_id));
ALTER TABLE agent_identities ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS "Service role full on agent_identities" ON agent_identities FOR ALL USING (auth.role() = 'service_role');
