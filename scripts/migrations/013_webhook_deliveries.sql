CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    webhook_id text,
    event text,
    url text,
    status_code int,
    success bool DEFAULT false,
    payload jsonb DEFAULT '{}',
    response_body text DEFAULT '',
    created_at timestamptz DEFAULT now()
);
ALTER TABLE webhook_deliveries ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS "Service role full on webhook_deliveries" ON webhook_deliveries FOR ALL USING (auth.role() = 'service_role');
