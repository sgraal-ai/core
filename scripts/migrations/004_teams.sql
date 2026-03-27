-- Teams and RBAC
CREATE TABLE IF NOT EXISTS teams (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    owner_email text NOT NULL,
    stripe_customer_id text,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS team_members (
    team_id uuid REFERENCES teams(id) ON DELETE CASCADE,
    user_email text NOT NULL,
    role text NOT NULL CHECK (role IN ('admin', 'developer', 'viewer', 'auditor')),
    status text DEFAULT 'pending' CHECK (status IN ('pending', 'active')),
    invited_at timestamptz DEFAULT now(),
    PRIMARY KEY (team_id, user_email)
);

CREATE TABLE IF NOT EXISTS team_api_keys (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id uuid REFERENCES teams(id) ON DELETE CASCADE,
    api_key_hash text UNIQUE NOT NULL,
    name text,
    scopes text[] DEFAULT '{}',
    ip_allowlist text[] DEFAULT '{}',
    created_by text,
    created_at timestamptz DEFAULT now()
);

ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_api_keys ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "Service role full access on teams" ON teams FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY IF NOT EXISTS "Service role full access on team_members" ON team_members FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY IF NOT EXISTS "Service role full access on team_api_keys" ON team_api_keys FOR ALL USING (auth.role() = 'service_role');
