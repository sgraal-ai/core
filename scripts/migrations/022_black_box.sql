CREATE TABLE IF NOT EXISTS black_box_capsules (
    capsule_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key_hash text NOT NULL,
    agent_id text NOT NULL,
    timestamp timestamptz DEFAULT now(),
    decision_input_snapshot jsonb,
    why_explanation text,
    compliance_state jsonb,
    action_override_chain jsonb,
    repair_plan_snapshot jsonb,
    hash text NOT NULL
);
ALTER TABLE black_box_capsules ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS "Service role full on black_box_capsules" ON black_box_capsules FOR ALL USING (auth.role() = 'service_role');
CREATE INDEX IF NOT EXISTS idx_black_box_agent_id ON black_box_capsules (agent_id);
CREATE INDEX IF NOT EXISTS idx_black_box_timestamp ON black_box_capsules (timestamp);
