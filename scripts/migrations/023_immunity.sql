CREATE TABLE IF NOT EXISTS immunity_certificates (
    certificate_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key_hash text NOT NULL,
    agent_id text NOT NULL,
    issued_at timestamptz DEFAULT now(),
    valid_days int DEFAULT 90,
    immunity_score float NOT NULL,
    passed boolean NOT NULL,
    level text DEFAULT 'standard',
    attempts_total int,
    attempts_blocked int
);
ALTER TABLE immunity_certificates ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS "Service role full on immunity_certificates" ON immunity_certificates FOR ALL USING (auth.role() = 'service_role');
CREATE INDEX IF NOT EXISTS idx_immunity_agent ON immunity_certificates (agent_id);
