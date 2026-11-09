# Encore — frontend integration prototype

React + TypeScript screens for a sound-to-beat workflow. The interface uses flat stacked rows, light surfaces, violet private sounds, teal public sounds, and blue, coral, and green accents. Fixtures keep the prototype visible while typed service adapters mark every future backend boundary.

## Run locally

Use Node.js 22.12+ and npm.

```sh
npm ci
npm run dev
```

Open the printed localhost URL. Authentication and backend operations use explicit not-configured adapters and never make network requests. Each route can also be opened directly:

- `/login`
- `/library`
- `/parameters`
- `/beat`
- `/profile`

`npm run build` produces a static build; `npm run preview` serves it. No API keys or backend configuration are required. Fonts are bundled locally.

## Included interactions

Screen navigation, transient library selection, local fixture search, disclosure panels, info tooltips, and responsive layouts are included. Microphone recording requests browser permission, counts down from three, captures 1.5 seconds with `MediaRecorder`, and provides a local review player before the upload adapter is called. The beat page presents the generated-audio contract as a waveform player and enables playback/export when a future service supplies URLs.

## Not implemented

There is no real authentication, persistence, server upload, sharing, deletion, moderation, beat generation, or MP3 export. Those controls call typed adapters in `src/services.ts`, which reject with `ServiceNotConfiguredError`. Recorded browser audio exists only as a temporary object URL until a production upload adapter is installed.

There are no network integrations, local-storage calls, IndexedDB records, or account sessions. Prior local data from earlier iterations is not read, modified, or cleared by this prototype.

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
