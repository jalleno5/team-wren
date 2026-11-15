# Mock backend behavior and frontend integration plan

This document records the mock backend merged into `origin/main` at commit
`11df5f7` (`KAN-65 Add mock API endpoints for every layer (#9)`) and maps it to
the TypeScript frontend in this branch. It is a planning reference, not an
implementation of the connection.

## Recommended architecture

Use Supabase for identity, persisted relational data, and file storage. Keep the
HTTP API boundary for application operations so the mock and future generation
worker share one client contract.

```text
React frontend
  ├─ Supabase Auth: Google sign-in, sign-out, session refresh
  └─ /api client: profiles, sound metadata, reports, classification, beats,
        and signed Supabase Storage upload/download operations
        ├─ local: in-memory Node mock on port 3001
        └─ production: API using Supabase/Postgres, Storage, and workers
```

All relational data access goes through `/api`; the frontend does not call
Supabase PostgREST directly. Supabase Auth remains in the browser so it can run
the Google OAuth flow. Storage access should use short-lived signed operations
issued by the API rather than public bucket URLs or a browser service-role key.

The browser should send the Supabase access token as
`Authorization: Bearer <access-token>` to authenticated API calls. The backend
must derive the user ID from the verified token; it must never trust a
client-supplied `user_id`. Never put a Supabase service-role key in Vite.

## Confirmed product decisions

- All row data is read and changed through the application API. Supabase is the
  persistence and identity provider behind that API.
- Reporting retains the mock backend model: `sound_reports.description`. The
  frontend's selected reason is sent as `description`; no moderation `status`
  field is required for this integration.
- Beat generation currently sends only `speed` (mapped from tempo), `genre`, and
  `sound_ids`, plus an optional title. Other visible frontend parameters are not
  part of the backend contract yet.
- Export is a direct download of the generated audio file; there is no separate
  MP3 conversion job.
- Guests may select public sounds, generate a beat, and listen to it. Creating a
  generation job does not require login. Downloading the result requires a
  signed-in user.
- Google/Supabase account email is display-only. Profile updates do not change
  the authentication email address.
- Guest generation jobs and their generated audio expire after one hour. Limit
  each IP address to ten guest generations per rolling hour.
- When a guest signs in, claim the guest-generated beat into that user's account
  before enabling download.

## How the merged mock backend runs

- `npm run mock-api` starts `mock-server/server.js` with Node's built-in HTTP
  server.
- The port is `MOCK_API_PORT` or `3001` by default.
- The merged JavaScript Vite config proxies browser requests beginning with
  `/api` to `http://localhost:3001`, avoiding a different frontend API URL in
  development.
- The server accepts JSON request bodies. An empty body becomes `{}` and
  malformed JSON returns `400 { "error": "Request body must be valid JSON" }`.
- Responses with a body are JSON. A `204` response has no body.
- CORS currently allows every origin and the methods `GET`, `POST`, `PATCH`,
  `DELETE`, and `OPTIONS`. It only lists `Content-Type` as an allowed header.
- Route matching is implemented in `mock-server/routes.js`. It supports exact
  paths and `:parameter` segments, tolerates a trailing slash, and returns a JSON
  404 for unknown method/path combinations.
- All state is in memory. Restarting the server resets the fixtures. Each
  `createMockApi()` call also receives fresh data, which isolates unit tests.
- IDs created during a server run are sequential strings such as `sound-100`,
  `report-101`, and `beat-102`; they are not UUIDs.
- Every request behaves as if it came from the fixed user `user-1`. The mock
  does not read cookies, Supabase sessions, or authorization headers.

## Seed data

The mock starts with:

- Profile `user-1` / `demo_user` / `demo@example.com`.
- Three sounds owned by `user-1`: two private and one public.
- Two public sounds owned by other users.
- One completed private beat using two owned sounds.
- Four deterministic sets of three YAMNet-like classification results.
- No sound reports.

A sound is visible when it belongs to `user-1` or has `visibility: "public"`.
A beat is visible when it belongs to `user-1` or is public.

## Endpoint contract

All errors use `{ "error": string }`.

### Health

| Method and path | Request | Success |
| --- | --- | --- |
| `GET /api/health` | None | `200 { "status": "ok" }` |

### Profile

| Method and path | Request | Success and validation |
| --- | --- | --- |
| `GET /api/profile` | None | `200` with the fixed current profile. |
| `PATCH /api/profile` | `{ username?, avatar_url? }` | Trims and updates `username`; copies `avatar_url`; returns the profile. A supplied blank username returns `400`. Other fields, including email, are ignored. |

The mock has no profile creation or photo-upload endpoint.

### Sounds and reports

| Method and path | Request | Success and validation |
| --- | --- | --- |
| `GET /api/sounds` | Query `scope=mine|public`; defaults to `mine` | `mine` returns all sounds owned by `user-1`; `public` returns all public sounds. Other values return `400`. There is no search query support. |
| `POST /api/sounds` | `{ title }` | Creates a private sound owned by `user-1` and returns it with `201`. Blank titles return `400`. No audio is uploaded or stored. |
| `PATCH /api/sounds/:id` | `{ title?, visibility? }` | An owner can rename a sound and/or set `private` or `public`. An invisible sound returns `404`; another user's visible sound returns `403`; invalid fields return `400`. |
| `DELETE /api/sounds/:id` | None | Deletes an owned sound and returns `204`. Visibility/ownership errors match PATCH. Related in-memory records are not cascaded. |
| `POST /api/sounds/:id/reports` | `{ description? }` | Creates a report with `reporter_id=user-1`, nullable description, and server time; returns `201`. The target must be visible. |

Mock sound objects only contain `id`, `user_id`, `title`, and `visibility`.
They do not contain creator display data, waveform data, audio location, duration,
source type, or trim boundaries.

### Classification

| Method and path | Request | Success and validation |
| --- | --- | --- |
| `POST /api/classify` | `{ sound_id }` | Returns `{ sound_id, labels }`, where `labels` is a deterministic array of three `{ label, score }` objects. A missing or invisible sound returns `404`. |

The result is selected by hashing the characters in the sound ID. No model or
audio processing runs in the mock.

### Beats

| Method and path | Request | Success and validation |
| --- | --- | --- |
| `GET /api/beats` | None | Returns all beats owned by `user-1`. |
| `POST /api/beats` | `{ title?, speed, genre?, sound_ids }` | Validates 1–4 visible sounds and an integer speed from 60–200. Creates a private queued beat and returns `202 { id, status: "queued" }`. A blank title becomes `Untitled beat`. |
| `GET /api/beats/:id` | None | Returns an owned or public beat. The first read of a newly queued beat returns `queued` but mutates stored state to `completed`; the second read returns `completed` with `/mock-audio/<id>.wav`. Missing/private foreign beats return `404`. |

The mock does not serve the `/mock-audio/*` files. It also has no export route,
no cancellation route, no failed generation state, and no job timeout.

## Supabase schema and policy behavior

The merged migrations define these tables:

- `users`: `id`, `username`, `avatar_url`, `email`, `created_at`; `id` references
  `auth.users(id)`.
- `sounds`: `id`, `user_id`, `title`, `source_type`, `duration_in_ms`,
  `visibility`, `created_at`.
- `beats`: `id`, `user_id`, `title`, `speed`, `genre`, `visibility`,
  `created_at`.
- `sounds_beats`: junction rows containing `sound_id`, `beat_id`, and
  `created_at`.
- `sound_reports`: `sound_id`, `reporter_id`, optional `description`, and
  `created_at`.

Row-level security is enabled. The final migration fixes sound and beat ownership
checks to compare `auth.uid()` with `user_id`, rather than with the row ID.
Authenticated users can create, update, and delete their own profiles, sounds,
and beats. Anonymous and authenticated sessions can select public sounds and
beats; authenticated owners can also select their private rows.

Two policies need attention before real integration:

1. `sounds_beats` INSERT currently requires the sound to belong to the current
   user. That conflicts with the product flow, which lets users build beats from
   other users' public sounds.
2. `sound_reports` INSERT is granted to `anon` and `authenticated`, but requires
   `auth.uid() = reporter_id` while `reporter_id` is non-null. An anonymous
   session cannot satisfy that condition, so reporting is effectively
   authenticated-only.

## Contract differences to resolve

| Concern | TypeScript frontend | Mock API | Supabase migration |
| --- | --- | --- | --- |
| Sound title | `name` | `title` | `title` |
| Ownership | Boolean `owned` | Compare `user_id` with `user-1` | Compare `user_id` with authenticated user |
| Creator | Display string `creator` | Missing | Join `sounds.user_id` to `users.username` |
| Audio | `audioUrl` plus playback lookup | Missing | Missing column; use Storage path or metadata column |
| Recording metadata | Trim start/end and waveform | Missing | Only required `source_type` and `duration_in_ms` exist |
| Flag/report | `sound_flags` with `reason` and `status` | `sound_reports.description` | Retain `sound_reports.description`; map the selected reason into it and remove the frontend status dependency |
| Beat tempo | `parameters.tempo` | `speed` | `speed` |
| Beat sounds | `soundIds` | Inline `sound_ids` | `sounds_beats` junction table |
| Generation output | Name, duration, waveform, playback/download URLs | Status and relative WAV URL | No status or output fields |
| Extra generation parameters | Length, ensemble, meter, key, mode, instruments | Ignored/not accepted | No columns |
| Profile update | Username and email; separate photo upload | Username/avatar URL only | Username, email, avatar URL |
| Guest identity | Explicit guest mode | Always `user-1` | Anonymous Supabase session |

The frontend branch now maps the mock's wire fields through `/api` and uses
Supabase only for authentication. Missing creator, waveform, audio, and trim
metadata remain presentation fallbacks or explicit capability errors until the
backend adds them.

## Frontend connection and remaining backend work

The frontend-facing work in the API, authentication, profile/sound, and beat
sections is implemented on this branch. Supabase migrations and mock-server
changes described below remain backend work and are intentionally not copied or
modified here before the later merge.

### 1. Freeze the shared API contract

- Add TypeScript DTOs that match API wire names exactly (`title`, `speed`,
  `sound_ids`, `description`) and map them into the existing UI models at the
  service boundary.
- Keep presentation-only fields such as `owned` computed in the adapter.
- Add a single API client that handles JSON, `204`, `{ error }`, abort signals,
  and Supabase bearer tokens.
- In development, call relative `/api` URLs through the Vite proxy. Add an
  environment-specific base URL only for deployments that cannot share an
  origin.

### 2. Connect Supabase authentication

- Implement Google OAuth with `supabase.auth.signInWithOAuth` and sign-out with
  `supabase.auth.signOut`.
- Restore the session on application startup and derive member/guest mode from
  Supabase session state instead of `sessionStorage` flags.
- Subscribe to auth-state changes so expired sessions and OAuth callbacks update
  the UI.
- Attach the current access token to API requests. Update mock CORS to allow the
  `Authorization` header.
- Preserve the development-only bypass, but make its identity behavior explicit:
  either use the mock fixed user or a configured Supabase test account.

### 3. Align Supabase persistence

- Add migrations for sound Storage metadata: at minimum `storage_path` (preferred
  over a permanent public URL), `trim_start_ms`, and `trim_end_ms`. Decide whether
  waveform values are persisted or generated in the browser.
- Add beat generation fields: `status`, output storage path, and duration. For
  now, persist only the supported generation inputs: speed, genre, selected
  sounds, and optional title.
- Update the `sounds_beats` insert policy to allow an owned sound or a public
  sound when the destination beat belongs to the current user.
- Keep moderation on `sound_reports.description`. Map the frontend's reason to
  `description` and do not require a report status field.
- Create the `public.users` row after first authentication, normally with an
  `auth.users` trigger or an idempotent onboarding call.
- Add a representation for guest generation jobs. The existing non-null
  `beats.user_id` foreign key cannot store an unauthenticated owner. Prefer a
  separate short-lived generation-job record or queue entry rather than making
  user-owned beat rows publicly writable.

### 4. Connect profiles and sounds

- `ProfileService.get` -> `GET /api/profile`.
- `ProfileService.update` -> `PATCH /api/profile` for username/avatar metadata.
  Display the Google/Supabase-managed email as read-only and never include it in
  the profile update payload.
- Request a signed avatar upload operation from the API, upload to Supabase
  Storage, then PATCH the returned storage path.
- `SoundService.list` -> `GET /api/sounds?scope=mine|public`; extend the endpoint
  with a search query or filter client-side.
- Before upload, decode the recording in the browser and encode only the
  handle-selected range as a PCM WAV file. Request a signed recording upload
  operation from the API, upload that clipped blob to private Supabase Storage,
  then `POST /api/sounds` with the title, storage key, normalized trim bounds
  (`0` through the clipped duration), and audio metadata. The API should assign
  `user_id`, `source_type`, visibility, and timestamps.
- Add a playback contract that returns a short-lived signed URL plus trim
  boundaries. Do not assume Storage objects are public.
- Map visibility and deletion to the existing PATCH and DELETE routes.
- Map flagging to `POST /api/sounds/:id/reports` with
  `{ description: selectedReason }`.

### 5. Connect beat generation and output

- Map frontend `tempo` to API `speed` and submit `genre`, selected sound IDs, and
  an optional title. Do not send length, ensemble, meter, key, mode, or
  per-sound instruments until the worker contract expands. The UI should not
  imply those unsupported values affect generation.
- Allow unauthenticated `POST /api/beats` only when every selected sound is
  public. Return an opaque job credential with the beat ID so the guest can poll
  and listen without gaining access to another guest's job.
- Enforce a one-hour TTL for guest jobs and generated objects, plus a rolling
  limit of ten guest generation requests per IP address per hour. Keep an
  explanatory comment beside the implementation constants, for example:

  ```js
  // Bound unauthenticated compute/storage: guest jobs expire after 1 hour and
  // each IP may create at most 10 guest generations in a rolling hour.
  const GUEST_JOB_TTL_MS = 60 * 60 * 1000
  const GUEST_GENERATION_LIMIT_PER_HOUR = 10
  ```

- On `202`, navigate with the returned beat ID and poll `GET /api/beats/:id`
  while status is `queued` or `processing`. Use an abort signal on unmount and a
  bounded retry/backoff policy. Guest polling must also present the opaque job
  credential.
- When completed, map the output to `BeatOutput`. The backend should return a
  playable signed URL and duration.
- Treat export as a direct download of the stored generated-audio object. The
  download API must require a valid Supabase session and return a short-lived
  signed download URL. A guest export attempt opens the frontend sign-in prompt
  and receives `401` if it reaches the API.
- Preserve the guest job credential through the OAuth redirect. After sign-in,
  call an authenticated, idempotent `POST /api/beats/:id/claim` with that
  credential. The API assigns the beat and generated object to the authenticated
  user, returns the claimed beat, and only then enables its download.
- Add explicit `failed` status and an error message before production use.

### 6. Upgrade the mock without hiding production gaps

- Accept optional Authorization headers and simulate authenticated versus guest
  behavior instead of always using `user-1`.
- Permit guest beat creation only from public fixture sounds and issue a
  deterministic test job credential. Keep profile, recording, private sound,
  and download operations authenticated.
- Simulate guest expiry, the ten-per-IP hourly limit, and idempotent beat
  claiming after sign-in.
- Add representative audio metadata and serve a real fixture audio file or a
  stable test URL.
- Mirror required Supabase fields and UUID-like IDs closely enough to catch
  mapping errors.
- Add tests for malformed JSON, query validation, visibility, report auth,
  generation polling, failed jobs, missing audio, and guest export denial.
- Keep the mock in-memory and deterministic; it should emulate contracts, not
  become a second database.

## Suggested delivery order

1. Contract decision and schema migration PR.
2. Supabase auth/session adapter and authenticated API client.
3. Profile and sound list/read integration.
4. Storage upload, trim metadata, visibility, deletion, and reporting.
5. Beat creation, polling, playback, and export.
6. Guest authorization, error cases, and end-to-end tests.

