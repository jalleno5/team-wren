-- Beats need a status so the frontend knows when generation is finished.
create type public.beat_status as enum ('queued', 'processing', 'completed', 'failed');

alter table public.beats add column status public.beat_status not null default 'queued';
alter table public.beats add column error_message text;

-- Users must NOT be able to mark their own beat "completed"; only the generation
-- worker should. So list exactly which columns users may fill in or change.
revoke insert, update on public.beats from authenticated;
grant insert (user_id, title, speed, genre, visibility) on public.beats to authenticated;
grant update (title, visibility)                        on public.beats to authenticated;
