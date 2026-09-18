-- 日本語語音・翻譯 cross-device sync
-- Run this once in the Supabase SQL editor for the project used by translator.html.

create table if not exists public.translation_sync_state (
  user_id uuid primary key references auth.users(id) on delete cascade,
  history jsonb not null default '[]'::jsonb,
  auto_save boolean not null default true,
  updated_at timestamptz not null default now()
);

alter table public.translation_sync_state enable row level security;

-- Recreate policies safely so rerunning this file is idempotent.
drop policy if exists "translation sync select own" on public.translation_sync_state;
drop policy if exists "translation sync insert own" on public.translation_sync_state;
drop policy if exists "translation sync update own" on public.translation_sync_state;
drop policy if exists "translation sync delete own" on public.translation_sync_state;

create policy "translation sync select own"
on public.translation_sync_state
for select
to authenticated
using (auth.uid() = user_id);

create policy "translation sync insert own"
on public.translation_sync_state
for insert
to authenticated
with check (auth.uid() = user_id);

create policy "translation sync update own"
on public.translation_sync_state
for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "translation sync delete own"
on public.translation_sync_state
for delete
to authenticated
using (auth.uid() = user_id);

revoke all on table public.translation_sync_state from anon;
grant select, insert, update, delete on table public.translation_sync_state to authenticated;

comment on table public.translation_sync_state is
'Per-user browser translation history and settings for Japanese Learning translator cloud sync.';
