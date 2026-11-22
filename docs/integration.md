# Frontend integration contract

The TypeScript frontend uses Supabase only for Google authentication. All
profile, sound, report, and beat data travels through the application API in
`src/services.ts`. See [the mock-backend analysis](mock-backend-integration-plan.md)
for the behavior currently merged into `main` and its Supabase schema gaps.

## Local configuration

Copy `.env.example` to `.env.local` and set the Supabase project URL and
publishable/anon key. Never expose a service-role key to Vite.

`VITE_API_BASE_URL` is optional. When it is blank, the app calls relative
`/api/*` paths and the development server proxies them to
`http://localhost:3001`. Start the real API with `npm run api` (code in
`server/`, reads `.env.local`) or the in-memory mock with `npm run mock-api`.
Both listen on port 3001.

The API client adds `Authorization: Bearer <Supabase access token>` for member
requests and `X-Guest-Job-Token` when polling or claiming a guest beat. It
supports JSON responses, empty `204` responses, abort signals, and `{ error }`
error bodies.

## Implemented API mappings

| Frontend operation | API contract |
| --- | --- |
| Get profile | `GET /api/profile` |
| Update username | `PATCH /api/profile` with `{ username }`; email is read-only |
| List sounds | `GET /api/sounds?scope=mine|public`; search is filtered in the browser |
| Change visibility/title | `PATCH /api/sounds/:id` |
| Delete a sound | `DELETE /api/sounds/:id` |
| Report a sound | `POST /api/sounds/:id/reports` with `{ description }`; stored as `sound_reports.reason` |
| Signed upload | `POST /api/uploads` with `{ purpose: "sound", content_type, size_bytes }` returns `{ upload_url, storage_path, headers? }`; the browser then `PUT`s the file and calls `POST /api/sounds` |
| Sound playback | `GET /api/sounds/:id/playback` returns `{ url, trim_start_seconds }` (a signed link valid for 1 hour) |
| Classify a sound | `POST /api/classify` with `{ sound_id }` returns `{ sound_id, category }` |
| Queue a beat | `POST /api/beats` with `{ title?, speed, genre, sounds: [{ sound_id, category }] }` |
| Poll a beat | `GET /api/beats/:id`, once per second for at most 60 seconds |

The in-memory mock implements classification deterministically. In production,
`POST /api/classify` is the boundary supplied by the sound-classification
backend; this repository validates and consumes its category response but does
not contain the classifier model itself.

Wire fields are mapped at the service boundary: sound `title` becomes UI
`name`, tempo becomes beat `speed`, category labels become lowercase wire
values, and the selected report reason becomes `description`. Ownership is calculated from the current profile ID. Missing
creator/waveform fields receive presentation-only labels and waveform values;
they are never written back as real backend data.

Read failures retain the checked-in fixtures so the layout remains usable.
Write failures never mutate fixture or displayed records.

## Required backend capabilities not yet present

The frontend defines these calls but converts a missing route into an explicit
`BackendCapabilityError`:

| Capability | Expected contract |
| --- | --- |
| Avatar upload | `POST /api/uploads` with `purpose: "avatar"` (returns 404 until an avatar bucket exists) |
| Guest beat creation | `POST /api/beats` returns `{ id, status, guest_token }` when unauthenticated |
| Guest polling | `GET /api/beats/:id` with `X-Guest-Job-Token` |
| Claim after login | Idempotent `POST /api/beats/:id/claim` with the guest-token header returns the claimed beat |
| Authenticated download | `GET /api/beats/:id/download` returns `{ url }` for the stored generated file |

The backend must also provide public-only guest authorization, a generation
worker that moves beats out of `queued`, served beat audio, and complete beat
duration/output metadata.

Guest jobs expire after one hour and are limited to two generations per IP per
rolling hour. These constants live in `server/routes.js`:

```js
// bound unauthenticated compute/storage: guest jobs expire after 1 hour and each IP may create at most 2 guest generations in a rolling hour
export const GUEST_JOB_TTL_MS = 60 * 60 * 1000
export const GUEST_GENERATION_LIMIT_PER_HOUR = 2
```

## Browser behavior

- Supabase restores sessions on startup and listens for auth changes. Explicit
  guest mode, selected sounds, the latest successfully generated beat ID, OAuth
  return path, and a pending guest credential live only in `sessionStorage`.
- Workflow navigation is sequential: Parameters requires a selected sound, and
  Listen & export requires a successful generation response. Changing the sound
  selection invalidates the generated-beat navigation state.
- Entering Parameters classifies any selected sound without a current category.
  All classification calls must succeed before navigation; failures keep the
  user on Sounds for retry. Categories are session-scoped to the current beat,
  and manual overrides invalidate any previously generated beat.
- Guests may browse public sounds, select 1–4 sounds, generate, poll, and listen.
  Private sounds, recording, reporting, Profile, and downloads require sign-in.
- After OAuth, the app returns to the beat and claims it before enabling direct
  download. A failed claim retains the credential for retry.
- Recording requests microphone permission, announces 3–2–1, records for 1.5
  seconds, releases tracks, and permits handle-based trimming. Saving requires a
  title, decodes and clips the selected range into a PCM WAV blob in the browser,
  then sends only that clipped blob through the signed-upload contract above.
  Since the uploaded file begins at the selection boundary, its trim metadata is
  normalized to zero through the clipped duration.
- Beat generation sends tempo/speed, genre, an optional title, and one of
  `percussion`, `rhythmic`, `melodic`, `ambient`, or `transition` for every
  selected sound. Unsupported length and advanced controls are not shown.

## Leftover files

`index.html` loads `src/main.tsx`. The older JSX entry files (`src/App.jsx`,
`src/main.jsx`, `src/App.css`, `src/index.css`) are no longer used.
