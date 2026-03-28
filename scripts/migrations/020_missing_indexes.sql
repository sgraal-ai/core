-- Missing indexes identified in pre-launch audit
CREATE INDEX IF NOT EXISTS idx_audit_log_api_key_id ON audit_log (api_key_id);
CREATE INDEX IF NOT EXISTS idx_outcome_log_preflight_id ON outcome_log (preflight_id);
CREATE INDEX IF NOT EXISTS idx_memory_store_created_at ON memory_store (created_at);
