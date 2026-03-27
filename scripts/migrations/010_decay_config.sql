CREATE TABLE IF NOT EXISTS decay_config (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key_hash text NOT NULL,
    memory_type text NOT NULL,
    decay_function text DEFAULT 'weibull' CHECK (decay_function IN ('weibull','gompertz','power_law','exponential')),
    lambda_param float DEFAULT 0.1,
    k_param float DEFAULT 1.5,
    created_at timestamptz DEFAULT now(),
    UNIQUE(api_key_hash, memory_type)
);
ALTER TABLE decay_config ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS "Service role full on decay_config" ON decay_config FOR ALL USING (auth.role() = 'service_role');
