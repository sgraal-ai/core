CREATE TABLE IF NOT EXISTS feedback_log (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), api_key_hash text, preflight_id text, feedback_type text CHECK (feedback_type IN ('false_positive','false_negative','correct','suggestion')), comment text, created_at timestamptz DEFAULT now());
ALTER TABLE feedback_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS "Service role full on feedback_log" ON feedback_log FOR ALL USING (auth.role() = 'service_role');
