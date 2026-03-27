-- Memory Store MVP
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS memory_store (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key_hash text NOT NULL,
    agent_id text,
    content text NOT NULL,
    memory_type text DEFAULT 'semantic',
    metadata jsonb DEFAULT '{}',
    omega_score float DEFAULT 0,
    last_preflight_at timestamptz DEFAULT now(),
    created_at timestamptz DEFAULT now(),
    expires_at timestamptz,
    blocked bool DEFAULT false
);

ALTER TABLE memory_store ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS "Service role full access on memory_store" ON memory_store FOR ALL USING (auth.role() = 'service_role');
CREATE INDEX IF NOT EXISTS idx_memory_store_key_agent ON memory_store(api_key_hash, agent_id);
CREATE INDEX IF NOT EXISTS memory_store_content_trgm ON memory_store USING gin(content gin_trgm_ops);
