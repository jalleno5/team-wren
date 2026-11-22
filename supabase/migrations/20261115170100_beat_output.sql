-- where the generation worker saves the finished beat
-- users can't write these columns (beat_status.sql limits them) so only the worker can
alter table public.beats add column output_path text;
alter table public.beats add column duration_in_ms integer;
