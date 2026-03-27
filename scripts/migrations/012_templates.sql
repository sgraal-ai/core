CREATE TABLE IF NOT EXISTS preflight_templates (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key_hash text NOT NULL,
    name text NOT NULL,
    memory_state jsonb NOT NULL,
    domain text DEFAULT 'general',
    action_type text DEFAULT 'reversible',
    options jsonb DEFAULT '{}',
    created_at timestamptz DEFAULT now(),
    UNIQUE(api_key_hash, name)
);
ALTER TABLE preflight_templates ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS "Service role full on preflight_templates" ON preflight_templates FOR ALL USING (auth.role() = 'service_role');
