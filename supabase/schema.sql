-- 在 Supabase Dashboard -> SQL Editor 中运行一次。可重复执行。
begin;
create table if not exists public.market_data_snapshots (
    dataset text not null check (dataset in ('snapshot','intraday','brokers','ticker','broker_history','ccass')),
    code text not null,
    record_date date not null,
    payload jsonb not null check (jsonb_typeof(payload) = 'object'),
    metadata jsonb not null default '{}'::jsonb,
    fetched_at timestamptz not null default now(),
    primary key (dataset, code, record_date)
);
alter table public.market_data_snapshots enable row level security;
-- 不向未登录访问者开放；开发演示由 Streamlit 服务端密钥读取。
revoke all on public.market_data_snapshots from anon, authenticated;
grant select, insert, update on public.market_data_snapshots to service_role;
comment on table public.market_data_snapshots is '06731 原始数据快照；本机采集上传，云端页面读取；不含账户/交易密码';
notify pgrst, 'reload schema';
commit;
