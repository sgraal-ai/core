-- Memory Aging Rules Engine
CREATE TABLE IF NOT EXISTS aging_rules (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key_hash text NOT NULL,
    memory_type text NOT NULL,
    ttl_days float NOT NULL,
    warn_at_percent float DEFAULT 70,
    block_at_percent float DEFAULT 90,
    auto_heal_action text DEFAULT 'REFETCH',
    created_at timestamptz DEFAULT now(),
    UNIQUE(api_key_hash, memory_type)
);

ALTER TABLE aging_rules ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS "Service role full access on aging_rules" ON aging_rules FOR ALL USING (auth.role() = 'service_role');
