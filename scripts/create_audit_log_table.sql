-- Audit log for all preflight and heal API calls
create table if not exists audit_log (
    id uuid primary key default gen_random_uuid(),
    event_type text not null,
    request_id text not null,
    api_key_id text,
    decision text,
    omega_mem_final float,
    timestamp timestamptz not null default now(),
    entry_id text,
    extra jsonb default '{}'::jsonb
);

create index idx_audit_log_request_id on audit_log (request_id);
create index idx_audit_log_event_type on audit_log (event_type);
create index idx_audit_log_timestamp on audit_log (timestamp);

alter table audit_log enable row level security;

create policy "Service role full access on audit_log"
    on audit_log for all
    using (auth.role() = 'service_role');
