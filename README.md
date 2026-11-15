# Encore — frontend integration prototype

React + TypeScript screens for a sound-to-beat workflow. The interface uses flat stacked rows, light surfaces, violet private sounds, teal public sounds, and blue, coral, and green accents. Fixtures keep the prototype visible while typed service adapters mark every future backend boundary.

## Run locally

Use Node.js 22.12+ and npm.

```sh
npm ci
npm run dev
```

Copy `.env.example` to `.env.local` to enable Supabase Google authentication. Data operations call relative `/api` endpoints; during development Vite proxies them to a separately running API on port 3001. This frontend-only branch does not contain that server, so read failures retain fixtures and missing capabilities produce explicit errors. Each route can also be opened directly:

- `/login`
- `/library`
- `/parameters`
- `/beat`
- `/profile`

`npm run build` produces a static build; `npm run preview` serves it. Google sign-in requires Supabase configuration, while guest mode and the development bypass remain available without it. Fonts are bundled locally.

## Included interactions

Screen navigation, session-scoped sound selection, API-backed library search, info tooltips, and responsive layouts are included. The Parameters step remains locked until at least one sound is selected, and Listen & export remains locked until generation succeeds. Microphone recording requests browser permission, counts down from three, captures 1.5 seconds with `MediaRecorder`, and provides a named local review before the signed-upload adapter is called. The beat page polls queued jobs and enables playback/download when the backend supplies the required URLs.

Recorded sounds can be trimmed by dragging the left and right edges of the waveform before saving; the handles also support arrow-key adjustment. On save, the browser decodes the recording, extracts only that selection, and encodes a PCM WAV blob, so unselected audio is never passed to the upload adapter. Supabase is used only for authentication in the browser. Profile, sound, report, and beat data goes through the typed `/api` client, and reports retain the mock backend's `sound_reports.description` model.

The sign-in screen also offers guest mode. Guests can browse and select up to four community sounds and generate/listen to a beat, while private sounds, recording, reporting, Profile, and direct download open a sign-in prompt.

During `npm run dev`, the sign-in page includes a clearly labeled testing bypass that starts a member-mode session. Vite removes this control from production builds.

Beat generation currently sends only tempo/speed, genre, selected sound IDs, and an optional title. Unsupported length and advanced controls are intentionally hidden.

## Not implemented

The current mock backend still lacks signed uploads, sound playback metadata, served audio, guest credentials/limits, beat claiming, and authenticated direct-download URLs. The frontend calls the documented future contracts and reports `BackendCapabilityError` when a route is absent; it never returns mock success for those operations.

Workflow state is session-scoped and no IndexedDB or durable browser database is used. Prior browser-local records from earlier iterations are not read, modified, or cleared.

## Building functionality separately

`src/fixtures.ts` contains static presentation data, `src/model.ts` contains presentation types and select-menu options, and `src/services.ts` defines the replaceable integration contracts. See [docs/integration.md](docs/integration.md) for the expected production behavior.

## Testing policy

No tests or test tooling are included. Tests will be written by hand by the team. CI only installs dependencies and builds the app.

## Team contribution rules

- Main is protected; use a feature branch and a pull request.
- Obtain at least one teammate approval and passing CI before merging; keep the branch up to date.
- Mention the Jira issue title in the PR description.
- For AI-assisted PRs, add a log under `ai_logs/` using `ai_logs/example.MD`: full chat history, tool/model, available usage/cost information, and **takeaways written manually by the contributor**. Do not invent unavailable usage data or have AI write the personal reflection.
- Review teammates’ PRs within a day or so.

## Typography

Font families are defined once in `src/styles.css`. `src/main.tsx` bundles Inter at weights 400 through 800. Numeric accents use a system monospace stack and need no downloaded font. Keep new stylesheet weights aligned with these imports.
