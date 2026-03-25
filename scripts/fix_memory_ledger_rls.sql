-- Enable RLS on memory_ledger if not already enabled
ALTER TABLE memory_ledger ENABLE ROW LEVEL SECURITY;

-- Service role can do everything
CREATE POLICY IF NOT EXISTS "Service role full access on memory_ledger"
    ON memory_ledger FOR ALL
    USING (auth.role() = 'service_role');

-- Verify all tables have RLS enabled
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('api_keys', 'outcome_log', 'audit_log', 'memory_ledger')
ORDER BY tablename;
