-- Outcome log table for tracking preflight outcomes and shadow calibration
create table if not exists outcome_log (
    outcome_id uuid primary key default gen_random_uuid(),
    preflight_id uuid,
    agent_id text,
    task_id text,
    status text not null default 'open' check (status in ('open', 'success', 'failure', 'partial')),
    component_attribution jsonb default '[]'::jsonb,
    created_at timestamptz not null default now(),
    closed_at timestamptz
);

-- Index for looking up open outcomes
create index idx_outcome_log_status on outcome_log (status);

-- Index for agent lookups
create index idx_outcome_log_agent_id on outcome_log (agent_id);

-- Enable RLS
alter table outcome_log enable row level security;

-- Service role can do everything
create policy "Service role full access on outcome_log"
    on outcome_log for all
    using (auth.role() = 'service_role');
