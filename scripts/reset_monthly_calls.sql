-- Function to reset calls_this_month for all API keys
create or replace function reset_monthly_calls()
returns void
language sql
security definer
as $$
    update api_keys set calls_this_month = 0;
$$;

-- Schedule with pg_cron: runs at midnight UTC on the 1st of every month
-- pg_cron is enabled by default on Supabase Pro plans.
-- Enable it via Dashboard > Database > Extensions > pg_cron if needed.
select cron.schedule(
    'reset-monthly-calls',
    '0 0 1 * *',
    'select reset_monthly_calls()'
);

-- To verify the job is scheduled:
-- select * from cron.job where jobname = 'reset-monthly-calls';

-- To remove the job:
-- select cron.unschedule('reset-monthly-calls');

-- If pg_cron is not available (Supabase Free plan), call the function
-- manually or via an external cron (e.g. Railway cron, GitHub Actions):
--   curl -X POST https://<project>.supabase.co/rest/v1/rpc/reset_monthly_calls \
--     -H "apikey: <SUPABASE_SERVICE_KEY>" \
--     -H "Authorization: Bearer <SUPABASE_SERVICE_KEY>"
