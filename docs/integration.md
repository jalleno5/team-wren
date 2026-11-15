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
`http://localhost:3001`. This branch intentionally does not contain or modify
the mock server; it will arrive in a later merge.

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
| Report a sound | `POST /api/sounds/:id/reports` with `{ description }` |
| Queue a beat | `POST /api/beats` with `{ title?, speed, genre, sound_ids }` |
| Poll a beat | `GET /api/beats/:id`, once per second for at most 60 seconds |

Wire fields are mapped at the service boundary: sound `title` becomes UI
`name`, tempo becomes beat `speed`, and the selected report reason becomes
`description`. Ownership is calculated from the current profile ID. Missing
creator/waveform fields receive presentation-only labels and waveform values;
they are never written back as real backend data.

Read failures retain the checked-in fixtures so the layout remains usable.
Write failures never mutate fixture or displayed records.

## Required backend capabilities not yet present

The frontend defines these calls but converts a missing route into an explicit
`BackendCapabilityError`:

| Capability | Expected contract |
| --- | --- |
| Signed upload | `POST /api/uploads` with `{ purpose: "sound" | "avatar", content_type, size_bytes }` returns `{ upload_url, storage_path, headers? }`; the browser then `PUT`s the file |
| Sound playback | `GET /api/sounds/:id/playback` returns `{ url, trim_start_seconds?, trim_end_seconds? }` |
| Guest beat creation | `POST /api/beats` returns `{ id, status, guest_token }` when unauthenticated |
| Guest polling | `GET /api/beats/:id` with `X-Guest-Job-Token` |
| Claim after login | Idempotent `POST /api/beats/:id/claim` with the guest-token header returns the claimed beat |
| Authenticated download | `GET /api/beats/:id/download` returns `{ url }` for the stored generated file |

The backend must also provide real per-user JWT verification, public-only guest
authorization, creator joins, trim/storage metadata, served audio, durable job
state, and complete beat duration/output metadata.

Guest jobs expire after one hour and are limited to ten generations per IP per
rolling hour. The future backend constants must retain an explanatory comment:

```js
// Bound unauthenticated compute/storage: guest jobs expire after 1 hour and
// each IP may create at most 10 guest generations in a rolling hour.
const GUEST_JOB_TTL_MS = 60 * 60 * 1000
const GUEST_GENERATION_LIMIT_PER_HOUR = 10
```

## Browser behavior

- Supabase restores sessions on startup and listens for auth changes. Explicit
  guest mode, selected sounds, the latest successfully generated beat ID, OAuth
  return path, and a pending guest credential live only in `sessionStorage`.
- Workflow navigation is sequential: Parameters requires a selected sound, and
  Listen & export requires a successful generation response. Changing the sound
  selection invalidates the generated-beat navigation state.
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
- Beat generation sends only tempo/speed, genre, selected sound IDs, and an
  optional title. Unsupported length and advanced controls are not shown.

## Later merge notes

Do not resolve main-branch conflicts on this frontend-only branch. The later
merge is expected to reconcile `.env.example`, `package.json`, the lockfile,
Vite configuration, and duplicate JSX/TypeScript entrypoints. Preserve this
branch's TypeScript application and `/api` service boundary while retaining the
mock server and migrations from `main`.
