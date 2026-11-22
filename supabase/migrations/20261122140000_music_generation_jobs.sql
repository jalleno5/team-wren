create table public.beat_worker_jobs (
  beat_id uuid primary key references public.beats(id) on delete cascade,
  worker_job_id uuid unique,
  prompt text,
  duration double precision not null default 10 check (duration between 1 and 30),
  lease_token uuid,
  lease_until timestamptz,
  created_at timestamptz not null default now()
);
alter table public.beat_worker_jobs enable row level security;
revoke all on public.beat_worker_jobs from anon, authenticated;
grant all on public.beat_worker_jobs to service_role;

-- Atomic lease acquisition supports restarts and multiple API instances.
create function public.claim_beat_generation() returns jsonb
language plpgsql security definer set search_path = '' as $$
declare j public.beat_worker_jobs;
begin
  select jobs.* into j from public.beat_worker_jobs jobs
    join public.beats beats on beats.id = jobs.beat_id
    where beats.status in ('queued', 'processing')
      and (jobs.lease_until is null or jobs.lease_until < now())
      and (beats.user_id is not null or beats.guest_expires_at > now())
    order by coalesce(jobs.lease_until, jobs.created_at)
    limit 1 for update of jobs skip locked;
  if not found then return null; end if;
  update public.beat_worker_jobs set lease_token = gen_random_uuid(), lease_until = now() + interval '3 minutes'
    where beat_id = j.beat_id returning * into j;
  update public.beats set status = 'processing' where id = j.beat_id;
  return to_jsonb(j);
end $$;

create function public.finish_beat_generation(p_beat_id uuid, p_lease_token uuid,
  p_status text, p_output_path text, p_duration integer, p_error text) returns boolean
language plpgsql security definer set search_path = '' as $$
begin
  if p_status not in ('completed', 'failed') then raise exception 'Invalid completion status'; end if;
  perform 1 from public.beat_worker_jobs where beat_id = p_beat_id and lease_token = p_lease_token
    and lease_until > now() for update;
  if not found then return false; end if;
  update public.beats set status = p_status::public.beat_status, output_path = p_output_path,
    duration_in_ms = p_duration, error_message = p_error
    where id = p_beat_id and status in ('queued', 'processing')
      and (user_id is not null or guest_expires_at > now());
  return found;
end $$;
revoke all on function public.claim_beat_generation() from public, anon, authenticated;
revoke all on function public.finish_beat_generation(uuid,uuid,text,text,integer,text) from public, anon, authenticated;
grant execute on function public.claim_beat_generation() to service_role;
grant execute on function public.finish_beat_generation(uuid,uuid,text,text,integer,text) to service_role;

-- Make previously queued placeholder requests eligible for real processing.
insert into public.beat_worker_jobs (beat_id)
  select id from public.beats where status in ('queued', 'processing');
