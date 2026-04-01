-- Memory store for /v1/store/memories and /v1/memory/graph
create table if not exists memory_store (
    id uuid primary key default gen_random_uuid(),
    created_at timestamptz not null default now(),
    api_key_hash text not null,
    agent_id text,
    content text not null,
    memory_type text not null default 'semantic',
    metadata jsonb default '{}'::jsonb,
    omega_score float default 0,
    blocked boolean default false
);

-- Index for fast key-scoped queries
create index idx_memory_store_api_key_hash on memory_store (api_key_hash);
create index idx_memory_store_agent_id on memory_store (agent_id);

-- Enable RLS
alter table memory_store enable row level security;

-- Service role full access (server-side operations)
create policy "Service role full access on memory_store"
    on memory_store for all
    using (auth.role() = 'service_role');
