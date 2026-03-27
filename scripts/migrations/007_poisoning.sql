CREATE TABLE IF NOT EXISTS poisoning_baselines (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key_hash text NOT NULL,
    memory_type text NOT NULL,
    mean_scores jsonb DEFAULT '{}',
    std_scores jsonb DEFAULT '{}',
    sample_count int DEFAULT 0,
    updated_at timestamptz DEFAULT now(),
    UNIQUE(api_key_hash, memory_type)
);
CREATE TABLE IF NOT EXISTS poisoning_log (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    forensics_id text UNIQUE NOT NULL,
    api_key_hash text NOT NULL,
    memory_id text,
    signals text[],
    confidence float,
    created_at timestamptz DEFAULT now()
);
ALTER TABLE poisoning_baselines ENABLE ROW LEVEL SECURITY;
ALTER TABLE poisoning_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS "Service role full access on poisoning_baselines" ON poisoning_baselines FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY IF NOT EXISTS "Service role full access on poisoning_log" ON poisoning_log FOR ALL USING (auth.role() = 'service_role');
