-- Create api_keys table
create table if not exists api_keys (
    id uuid primary key default gen_random_uuid(),
    created_at timestamptz not null default now(),
    key_hash text not null unique,
    customer_id text not null,
    email text not null,
    tier text not null default 'free' check (tier in ('free', 'starter', 'growth')),
    calls_this_month integer not null default 0,
    last_used_at timestamptz
);

-- Index for fast key lookup during auth
create index idx_api_keys_key_hash on api_keys (key_hash);

-- Index for Stripe customer lookups
create index idx_api_keys_customer_id on api_keys (customer_id);

-- Enable RLS
alter table api_keys enable row level security;

-- Users can only read their own keys (matched by auth email)
create policy "Users can view own keys"
    on api_keys for select
    using (email = auth.jwt() ->> 'email');

-- Users can update their own keys (e.g. last_used_at)
create policy "Users can update own keys"
    on api_keys for update
    using (email = auth.jwt() ->> 'email');

-- Only service role can insert/delete (server-side key provisioning)
create policy "Service role can insert keys"
    on api_keys for insert
    with check (auth.role() = 'service_role');

create policy "Service role can delete keys"
    on api_keys for delete
    using (auth.role() = 'service_role');
