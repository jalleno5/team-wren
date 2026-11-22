-- guest beats, a bucket for finished beats, and profile photos

-- 1. a guest beat has no owner until someone signs in and claims it
-- rls already hides rows with no owner from users, only the server (secret key) reads them
alter table public.beats alter column user_id drop not null;
alter table public.beats add column guest_token_hash text;        -- sha256 of the guest token, the token itself is never saved
alter table public.beats add column guest_expires_at timestamptz;  -- unclaimed guest beats get deleted after this
alter table public.beats add column guest_ip text;                 -- for the guest beats per hour limit

-- 2. users could read every column of beats, keep the guest ones server only
revoke select on public.beats from anon, authenticated;
grant select (id, user_id, title, speed, genre, visibility, created_at, status, error_message, output_path, duration_in_ms)
  on public.beats to anon, authenticated;

-- 3. finished beats go in their own private bucket
-- only the worker writes here and the api signs links after checking who is asking, so no policies
-- 4. profile photos are shown to everyone so that bucket is public (anyone can read, 5 MB, images only)
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
  ('beats',   'beats',   false, 52428800, array['audio/*']),
  ('avatars', 'avatars', true,  5242880,  array['image/jpeg', 'image/png', 'image/webp', 'image/gif'])
on conflict (id) do update
  set public             = excluded.public,
      file_size_limit    = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;

-- you can only put photos in a folder named after your own id
create policy "Avatars: owner can upload" on storage.objects
  for insert to authenticated
  with check (bucket_id = 'avatars' and (storage.foldername(name))[1] = (select auth.uid())::text);

create policy "Avatars: owner can replace" on storage.objects
  for update to authenticated
  using (bucket_id = 'avatars' and (storage.foldername(name))[1] = (select auth.uid())::text)
  with check (bucket_id = 'avatars' and (storage.foldername(name))[1] = (select auth.uid())::text);

create policy "Avatars: owner can delete" on storage.objects
  for delete to authenticated
  using (bucket_id = 'avatars' and (storage.foldername(name))[1] = (select auth.uid())::text);
