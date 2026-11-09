# Frontend service boundaries

Encore keeps production integrations behind the interfaces in `src/services.ts`. The checked-in adapters intentionally throw `ServiceNotConfiguredError`; they do not issue network requests or return mock successes.

## Current boundaries

- `src/fixtures.ts`: named static samples and decorative waveform data used when reads are unavailable.
- `src/model.ts`: sound presentation types and parameter-menu options.
- `src/services.ts`: auth, sound, beat, and profile interfaces plus the stand-in adapters.
- `src/App.tsx`: UI state, browser microphone capture, accessible dialogs, and adapter calls.
- `src/styles.css`: visual layouts, theme, and responsive styles. Controls use normal active styling. Form values may change within a screen, while application operations remain unimplemented.

## Future functionality to build independently

| Screen | Future responsibilities |
| --- | --- |
| Login | Replace `AuthService` with a Supabase client adapter. `signInWithGoogle` should call `supabase.auth.signInWithOAuth({ provider: 'google' })`; `signOut` should call `supabase.auth.signOut()`. |
| Library | The included adapter reads `sounds`, uploads blobs to the configured Storage bucket, updates sound visibility, and inserts moderation requests into `sound_flags`. |
| Parameters | Implement `BeatService.generate`; its parameter payload includes `lengthBars` (1, 2, or 4), and it returns a stable beat ID only when generation is accepted. |
| Audio output | Implement `getOutput` with `{ id, name, audioUrl, durationSeconds, waveform, downloadUrl }`. URLs may be signed and short-lived. |
| Profile | Implement `ProfileService` for profile reads, edits, and photo upload. |

Keep the exported interfaces stable when adding production adapters. Reads may replace fixtures after a successful response; failed writes must not mutate the displayed fixtures. Generation navigates to `/beat?id=<beat-id>` only after the service resolves.

## Browser recording lifecycle

The recorder requests microphone permission before the countdown, displays 3–2–1, records for 1.5 seconds, stops every media track, and creates a temporary object URL for review. Closing, retrying, or unmounting clears timers, stops tracks, and revokes the object URL. The object URL is not persistence; the production upload adapter must send the supplied blob and return the created sound.

Before saving, the review screen exposes draggable handles on both edges of the waveform. The handles support pointer and arrow-key input. The selected values are sent as `trim_start_seconds` and `trim_end_seconds`, stored with the sound row, and honored by sample playback.

## Guest access

Choosing guest mode stores a session-scoped access flag. Guest sessions are restricted to public sounds; attempts to open the private library, record a sound, or export an MP3 produce a sign-in dialog. A successful production Google sign-in must replace the flag with `member` before routing to the library.

## Supabase table contract

Copy `.env.example` to `.env.local` and provide `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` to activate the REST adapter. The configured project must expose:

- `sounds`: `id`, `name`, `creator`, `owned`, `visibility`, `waveform`, `audio_url`, `trim_start_seconds`, `trim_end_seconds`, and `created_at`.
- `sound_flags`: `id`, `sound_id`, `reason`, `status`, and `created_at`.
- A public or appropriately signed Storage bucket matching `VITE_SUPABASE_SOUND_BUCKET` (defaults to `sounds`).

Row-level security should allow visitors to select public sounds, authenticated owners to select/update their sounds, and authenticated users to insert flags. Do not expose a service-role key to Vite; the frontend adapter is designed for an anon key plus RLS.

Fermata's conditioning vocabulary is represented as select-menu options only. The fixed pattern is an illustration, not model output. There is no model execution, MIDI/audio conversion, or sound classification.

Earlier versions of the app may have left browser-local records on the same origin. This navigation prototype does not access or erase them.
