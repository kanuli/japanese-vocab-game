-- Free translation-router quota guard.
-- Run once in Supabase SQL Editor before enabling Google/Azure provider secrets.

create table if not exists public.translation_provider_usage (
  provider text not null,
  period text not null,
  used_chars bigint not null default 0 check (used_chars >= 0),
  updated_at timestamptz not null default now(),
  primary key (provider, period)
);

alter table public.translation_provider_usage enable row level security;

revoke all on table public.translation_provider_usage from anon, authenticated;

create or replace function public.reserve_translation_quota(
  p_provider text,
  p_period text,
  p_chars bigint,
  p_limit bigint
)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
begin
  if p_provider is null or p_provider = '' then
    return false;
  end if;
  if p_period is null or p_period = '' then
    return false;
  end if;
  if p_chars <= 0 or p_limit <= 0 or p_chars > p_limit then
    return false;
  end if;

  insert into public.translation_provider_usage(provider, period, used_chars)
  values (p_provider, p_period, 0)
  on conflict (provider, period) do nothing;

  update public.translation_provider_usage
  set used_chars = used_chars + p_chars,
      updated_at = now()
  where provider = p_provider
    and period = p_period
    and used_chars + p_chars <= p_limit;

  return found;
end;
$$;

revoke all on function public.reserve_translation_quota(text, text, bigint, bigint) from public, anon, authenticated;
grant execute on function public.reserve_translation_quota(text, text, bigint, bigint) to service_role;

comment on table public.translation_provider_usage is
'Internal monthly character counters used by the Supabase translation-router Edge Function. Not readable by browser clients.';

comment on function public.reserve_translation_quota(text, text, bigint, bigint) is
'Atomically reserves characters under a provider monthly safety cap; returns false when the cap would be exceeded.';
