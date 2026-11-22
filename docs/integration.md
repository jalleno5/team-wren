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
| Poll a beat | `GET /api/beats/:id`, once per second for up to 30 minutes |

The in-memory mock implements classification deterministically. The real
`POST /api/classify` reads a saved classification or calls the Python service
in `classify/`. The frontend reviews the suggestion before creating the beat.

Wire fields are mapped at the service boundary: sound `title` becomes UI
`name`, tempo becomes beat `speed`, category labels become lowercase wire
values, and the selected report reason becomes `description`. Ownership is calculated from the current profile ID. Missing
creator/waveform fields receive presentation-only labels and waveform values;
they are never written back as real backend data.

Read failures retain the checked-in fixtures so the layout remains usable.
Write failures never mutate fixture or displayed records.

## Additional implemented capabilities

The real API also provides these routes:

| Capability | Expected contract |
| --- | --- |
| Avatar upload | `POST /api/uploads` with `purpose: "avatar"` |
| Guest beat creation | `POST /api/beats` returns `{ id, status, guest_token }` when unauthenticated |
| Guest polling | `GET /api/beats/:id` with `X-Guest-Job-Token` |
| Claim after login | Idempotent `POST /api/beats/:id/claim` with the guest-token header returns the claimed beat |
| Authenticated download | `GET /api/beats/:id/download` returns `{ url }` for the stored generated file |

The generation worker, guest authorization, audio storage and duration metadata
are integrated as described in the setup section below.

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


## Real generation after the background-worker merge

Apply `20261122140000_music_generation_jobs.sql` after the existing guest and
grant migrations. The earlier, unshipped `beat_worker_jobs` migration has been
replaced by this migration. Do not apply both versions. Configure Node with
`SUPABASE_SECRET_KEY`, `MUSIC_WORKER_URL`, `MUSIC_API_KEY`, and
`CLASSIFY_WORKER_URL` (classifier local port 8001, music port 8000).
The Python music service needs its Supabase URL and matching worker key.

There is one orchestration path: `/api/beats` stores the sound/category links
and a durable generation request. `server/worker.js` runs in the Node API
process and leases requests from the database. `server/generation.js` submits
or resumes the Python job, downloads only the rendered WAV, and saves
`beats/<beat-id>.wav`. GET status routes only read state and sign links; closing
the browser does not stop completion. Run a persistent Node process, not a
short-lived serverless invocation, for this background loop.

Job references, prompt, duration, and renewable ownership leases are persisted;
user sessions and signed download URLs are not. Python accepts a beat UUID as
an idempotency key, preventing duplicate generation after lost responses or
Node restarts. Transient network, queue-full and storage errors retry the same
job. The existing guest expiry, claim and private playback/download lifecycle
uses the same `beats` bucket. Historical placeholder completed beats are not
regenerated. Existing queued/processing beats are backfilled into the job table.

The merged frontend sends `sounds: [{sound_id, category}]`. Its confirmed,
beat-specific category is saved in `sounds_beats.category` and drives rendering;
the original sound's `classification` is the fallback for historical links.
Legacy `sound_ids` requests derive those categories from `sounds.classification`.
This preserves the merged manual-category UI rather than silently ignoring it.
`POST /api/classify` returns an existing database classification or forwards a
signed sound URL to the classifier. It returns the suggested category for review;
the confirmed per-beat category is saved when creating the beat. It does not
modify a shared community sound's global classification.

Before issuing sample URLs the background worker rechecks public visibility or
ownership. Only the trusted Node service may submit the signed sample manifest
to Python, using `MUSIC_API_KEY`. Python restricts URLs to signed sound objects
in the configured Supabase project and stages them before queuing. This works
for public guest samples and private member samples without persisting JWTs.

Output downloads are WAV. The UI polls up to 30 minutes, retrying temporary
errors. The compute queue remains the single-process Python prototype, which
requires persistent output storage. A lost Python job fails explicitly rather
than being silently regenerated.
