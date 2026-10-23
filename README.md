# Encore — navigation-only frontend

React + TypeScript screens for navigating a sound-to-beat workflow. The interface uses flat stacked rows, light surfaces, violet private sounds, teal public sounds, and blue, coral, and green accents. All samples, selections, parameters, profiles, and sequencer steps are static presentation fixtures.

## Run locally

Use Node.js 22.12+ and npm.

```sh
npm ci
npm run dev
```

Open the printed localhost URL. The sign-in button only links to the library; no authentication takes place. Each route can also be opened directly:

- `/login`
- `/library`
- `/parameters`
- `/beat`
- `/profile`

`npm run build` produces a static build; `npm run preview` serves it. No API keys or backend configuration are required. Fonts are bundled locally.

## Included interactions

Screen navigation, transient library selection (for visual added/unadded states only), library tabs, disclosure panels, info tooltips, opening/closing placeholder dialogs, and responsive sequencer wrapping. Continue buttons only navigate between screens.

## Not implemented

There is no microphone access, audio capture, audio decoding, playback, waveform analysis, file upload, profile persistence, search processing, persistent sound selection, sharing, deletion, moderation, authentication, beat generation, step editing, transport timer, or export. Controls have active styling and editable form values, but capability buttons are unconnected. Opening a recording, deletion, report, or export dialog only previews its layout and never performs an underlying operation. Confirm buttons dismiss the dialog without deleting data or creating a file.

There are no services, local-storage calls, IndexedDB, audio blobs, permission prompts, account sessions, or network integrations. Prior local data from earlier iterations is not read, modified, or cleared by this prototype.

## Building functionality separately

`src/fixtures.ts` contains static presentation data. `src/model.ts` contains presentation types and select-menu options. `src/App.tsx` contains screen components and navigation. See [docs/integration.md](docs/integration.md) for future integration boundaries. The previous audio and mock-service implementations have been removed rather than left dormant.

## Testing policy

No tests or test tooling are included. Tests will be written by hand by the team. CI only installs dependencies and builds the app.

## Team contribution rules

- Main is protected; use a feature branch and a pull request.
- Obtain at least one teammate approval and passing CI before merging; keep the branch up to date.
- Mention the Jira issue title in the PR description.
- For AI-assisted PRs, add a log under `ai_logs/` using `ai_logs/example.MD`: full chat history, tool/model, available usage/cost information, and **takeaways written manually by the contributor**. Do not invent unavailable usage data or have AI write the personal reflection.
- Review teammates’ PRs within a day or so.

## Typography

Font families are defined once in `src/styles.css`. `src/main.tsx` bundles Nunito at weights 400, 500, 600, 700, and 800 and Fredoka at 500 and 600. Numeric accents use a system monospace stack and need no downloaded font. Keep new stylesheet weights aligned with these imports.
