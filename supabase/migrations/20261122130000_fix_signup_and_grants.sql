-- 20261121173336_remote_schema.sql came from a db pull and undid parts of
-- 20261115151414_profiles_grants_and_policy_fixes.sql and 20261115170000_sound_grants_and_storage_fixes.sql
-- this puts back what the app needs

-- 1. users.email was dropped, so the sign up trigger can't write it anymore
-- the api gets email from the login itself so the column isn't needed
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.users (id, username, avatar_url)
  values (
    new.id,
    coalesce(
      new.raw_user_meta_data->>'username',
      new.raw_user_meta_data->>'full_name',
      new.raw_user_meta_data->>'name',
      split_part(new.email, '@', 1)
    ),
    coalesce(new.raw_user_meta_data->>'avatar_url', new.raw_user_meta_data->>'picture')
  )
  on conflict (id) do nothing;  -- if a profile already exists don't error
  return new;
end;
$$;

-- 2. profiles: anyone can see usernames and photos, you can only change your own (rls)
grant select (id, username, avatar_url, created_at) on public.users to anon, authenticated;
grant update (username, avatar_url)                 on public.users to authenticated;

-- 3. sounds: only the columns the app needs, visibility is left out of insert so new sounds start private
grant insert (user_id, title, source_type, duration_in_ms, storage_path) on public.sounds to authenticated;
grant update (title, visibility)                                         on public.sounds to authenticated;
