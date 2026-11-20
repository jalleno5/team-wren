-- Runs AFTER 20261115142311_remote_schema.sql (Gavin's buckets + sounds.storage_path).
-- File storage is handled by Gavin's migration (sounds-private / sounds-public buckets),
-- so this file does not create a bucket or a file_path column.
-- What this does:
--   1. Automatically create a public.users profile whenever someone signs in for the first time
--   2. Create profiles for people who already signed in before this trigger existed
--   3. Fill in user_id automatically on new rows
--   4. Replace the "everyone can do everything" grants with only what the app needs
--   5. Fix/add a few row-level-security policies

-- =========================================================
-- 1. AUTO-CREATE A PROFILE ON SIGNUP
-- =========================================================

-- A profile's id must be the SAME id as the login account (auth.users.id),
-- so stop Postgres from inventing a random one.
alter table public.users alter column id drop default;

-- A "trigger function" is code the database runs by itself when something happens.
-- "security definer" = run it with the table owner's permissions, because the
-- person signing up isn't allowed to insert into public.users directly.
-- "set search_path = ''" = a safety setting; we write full names like public.users.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  -- "new" is the auth.users row that was just created.
  -- Google puts the person's info in raw_user_meta_data. coalesce() picks the
  -- first value that isn't empty: username -> Google name -> start of their email.
  insert into public.users (id, email, username, avatar_url)
  values (
    new.id,
    new.email,
    coalesce(
      new.raw_user_meta_data->>'username',
      new.raw_user_meta_data->>'full_name',
      new.raw_user_meta_data->>'name',
      split_part(new.email, '@', 1)
    ),
    coalesce(new.raw_user_meta_data->>'avatar_url', new.raw_user_meta_data->>'picture')
  )
  on conflict (id) do nothing;   -- if a profile already exists, don't error
  return new;
end;
$$;

-- Hook the function up: "after a row is added to auth.users, run handle_new_user".
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- =========================================================
-- 2. BACKFILL: profiles for people who signed in before the trigger existed
-- =========================================================

insert into public.users (id, email, username, avatar_url)
select
  u.id,
  u.email,
  coalesce(u.raw_user_meta_data->>'username', u.raw_user_meta_data->>'full_name',
           u.raw_user_meta_data->>'name', split_part(u.email, '@', 1)),
  coalesce(u.raw_user_meta_data->>'avatar_url', u.raw_user_meta_data->>'picture')
from auth.users u
where u.email is not null
on conflict (id) do nothing;

-- =========================================================
-- 3. DEFAULTS: if the app forgets user_id, fill in "whoever is logged in"
-- =========================================================

alter table public.sounds        alter column user_id     set default auth.uid();
alter table public.beats         alter column user_id     set default auth.uid();
alter table public.sound_reports alter column reporter_id set default auth.uid();

-- =========================================================
-- 4. GRANTS
-- Grants = which ACTIONS a role may attempt at all.
-- Policies (section 5) = which ROWS they may do it to. Both must say yes.
-- anon = not logged in, authenticated = logged in.
-- =========================================================

-- Start from zero (an earlier migration gave anon everything, including TRUNCATE).
revoke all on public.users, public.sounds, public.beats, public.sounds_beats, public.sound_reports
  from anon, authenticated;

-- Profiles: anyone can read these columns. email is left out on purpose so it stays private.
grant select (id, username, avatar_url, created_at) on public.users to anon, authenticated;
grant update (username, avatar_url)                 on public.users to authenticated;

grant select                 on public.sounds, public.beats, public.sounds_beats to anon, authenticated;
grant insert, update, delete on public.sounds, public.beats                      to authenticated;
grant insert, delete         on public.sounds_beats                              to authenticated;
grant select, insert         on public.sound_reports                             to authenticated;

-- =========================================================
-- 5. POLICIES
-- =========================================================

-- Usernames/avatars are public (the old policy only let you see your own).
create policy "Profiles are public"
  on public.users for select to anon, authenticated
  using (true);

-- FIX: the old rule was "the SOUND must be yours, the BEAT can be public", which is backwards.
-- Correct: "the BEAT must be yours, the SOUND can be yours or public".
drop policy "Users can insert sounds into beats" on public.sounds_beats;

create policy "Add own or public sounds to own beats"
  on public.sounds_beats for insert to authenticated
  with check (
    exists (select 1 from public.beats b
            where b.id = sounds_beats.beat_id and b.user_id = (select auth.uid()))
    and
    exists (select 1 from public.sounds s
            where s.id = sounds_beats.sound_id
              and (s.user_id = (select auth.uid()) or s.visibility = 'public'))
  );

-- Reporters can see the reports they filed (there was no select policy before).
create policy "See own reports"
  on public.sound_reports for select to authenticated
  using (reporter_id = (select auth.uid()));
