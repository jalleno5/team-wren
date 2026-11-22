-- fixes from the repo review, runs after 20261115153407_beat_status.sql

-- 1. guests can browse public sounds so they also need to read the public bucket
-- signed playback links can't be made without read access
drop policy "Public bucket: public select" on storage.objects;

create policy "Public bucket: anyone can read" on storage.objects
  for select to anon, authenticated
  using (bucket_id = 'sounds-public');

-- 2. the anon key is in the browser so users can call supabase directly and skip our api
-- before this they could change any column of their own sounds (like storage_path)
-- so only allow the columns the app needs
-- visibility is left out of insert so a new sound always starts private like its file
revoke insert, update on public.sounds from authenticated;
grant insert (user_id, title, source_type, duration_in_ms, storage_path) on public.sounds to authenticated;
grant update (title, visibility)                                       on public.sounds to authenticated;

-- 3. the first migration made every future table give anon and authenticated truncate
-- truncate skips rls so turn that off, new tables should grant what they need themselves
alter default privileges for role postgres in schema public
  revoke all on tables from anon, authenticated;

-- 4. POST /api/uploads checks size and type from what the browser says
-- so make storage enforce them too (10 MB, audio only)
-- this also creates the buckets on a fresh local database
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
  ('sounds-private', 'sounds-private', false, 10485760, array['audio/*']),
  ('sounds-public',  'sounds-public',  false, 10485760, array['audio/*'])
on conflict (id) do update
  set file_size_limit    = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;
