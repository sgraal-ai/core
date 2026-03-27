-- Domain Profile Configurator
CREATE TABLE IF NOT EXISTS profiles (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key_hash text NOT NULL,
    name text NOT NULL,
    base_domain text DEFAULT 'general',
    custom_weights jsonb DEFAULT '{}',
    warn_threshold float DEFAULT 40,
    ask_user_threshold float DEFAULT 60,
    block_threshold float DEFAULT 80,
    description text DEFAULT '',
    created_at timestamptz DEFAULT now(),
    UNIQUE(api_key_hash, name)
);

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS "Service role full access on profiles" ON profiles FOR ALL USING (auth.role() = 'service_role');
