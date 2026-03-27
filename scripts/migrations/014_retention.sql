CREATE TABLE IF NOT EXISTS retention_policies (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key_hash text NOT NULL,
    name text NOT NULL,
    condition text NOT NULL,
    action text DEFAULT 'archive' CHECK (action IN ('archive','delete','block')),
    created_at timestamptz DEFAULT now(),
    UNIQUE(api_key_hash, name)
);
ALTER TABLE retention_policies ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS "Service role full on retention_policies" ON retention_policies FOR ALL USING (auth.role() = 'service_role');
