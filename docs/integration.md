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
| Library | Replace `SoundService` with API calls for list/playback URLs, upload, deletion, visibility, and reports. Upload receives the browser-recorded `Blob`. |
| Parameters | Implement `BeatService.generate`; return a stable beat ID only when generation is accepted. |
| Audio output | Implement `getOutput` with `{ id, name, audioUrl, durationSeconds, waveform, downloadUrl }`. URLs may be signed and short-lived. |
| Profile | Implement `ProfileService` for profile reads, edits, and photo upload. |

Keep the exported interfaces stable when adding production adapters. Reads may replace fixtures after a successful response; failed writes must not mutate the displayed fixtures. Generation navigates to `/beat?id=<beat-id>` only after the service resolves.

## Browser recording lifecycle

The recorder requests microphone permission before the countdown, displays 3–2–1, records for 1.5 seconds, stops every media track, and creates a temporary object URL for review. Closing, retrying, or unmounting clears timers, stops tracks, and revokes the object URL. The object URL is not persistence; the production upload adapter must send the supplied blob and return the created sound.

Fermata's conditioning vocabulary is represented as select-menu options only. The fixed pattern is an illustration, not model output. There is no model execution, MIDI/audio conversion, or sound classification.

Earlier versions of the app may have left browser-local records on the same origin. This navigation prototype does not access or erase them.
