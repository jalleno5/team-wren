# Navigation prototype and future integrations

Encore currently contains only presentation and navigation. It does not expose a working service layer. There are no audio, persistence, or simulated-generation implementations to reuse accidentally.

## Current boundaries

- `src/fixtures.ts`: named static samples, illustrated waveforms, selected-sound examples, and a fixed example pattern. Waveform numbers are decorative; samples contain no files or audio blobs.
- `src/model.ts`: `SoundView` and `LaneView` presentation types plus parameter-menu options. No validation, generation, or storage behavior.
- `src/App.tsx`: screen components, links, library-tab selection, accessible dialogs/tooltips, and responsive layout measurement. All screens are reachable without signing in or creating data.
- `src/styles.css`: visual layouts, theme, and responsive styles. Controls use normal active styling. Form values may change within a screen, while application operations remain unimplemented.

## Future functionality to build independently

| Screen | Future responsibilities |
| --- | --- |
| Login | Authentication, sessions, account recovery |
| Library | Microphone capture, 1.5-second validation, playable sound assets, search, selection, ownership, visibility, deletion, reporting |
| Parameters | User-controlled values, 60–200 BPM validation, generation request |
| Beat editor | Real event state, edit actions, audio scheduling, volume/mute, MP3 encoding |
| Profile | User data, photo handling, profile updates, account settings |

Introduce those capabilities explicitly through future component props or injected service interfaces. Replace fixture imports with application state only when implementing each feature. Wire the visible controls to real behavior when ready; do not interpret navigation to the beat screen as successful generation or the login link as authentication.

Fermata's conditioning vocabulary is represented as select-menu options only. The fixed pattern is an illustration, not model output. There is no model execution, MIDI/audio conversion, or sound classification.

Earlier versions of the app may have left browser-local records on the same origin. This navigation prototype does not access or erase them.
