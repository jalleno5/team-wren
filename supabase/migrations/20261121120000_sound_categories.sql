alter table public.sounds_beats
  add column category text;

alter table public.sounds_beats
  add constraint sounds_beats_category_check
  check (category in ('percussion', 'rhythmic', 'melodic', 'ambient', 'transition'));

comment on column public.sounds_beats.category is
  'Beat-specific role selected for this sound. Historical associations may be null.';
