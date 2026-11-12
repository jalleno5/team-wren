# Audio pipeline review artifacts

Latest: [simple trap retry and selected everyday-sound preview](simple_trap_retry/README.md).

This folder contains generated audio, transcribed MIDI, sample mappings and
experiment metadata for colleague review. The application pipeline remains
**MusicGen Small -> YourMT3+ -> sample rendering**.

## Start listening

| Experiment | Original | Everyday samples | Mixed samples |
| --- | --- | --- | --- |
| Trap | [Original](listening_20261111/trap/original.wav) | [Prepared](listening_20261111/trap/everyday_smoothed.wav) | [Prepared](listening_20261111/trap/mixed_smoothed.wav) |
| Country | [Original](listening_20261111/country/original.wav) | [Prepared](listening_20261111/country/everyday_smoothed.wav) | [Prepared](listening_20261111/country/mixed_smoothed.wav) |
| Pop | [Original](listening_20261111/pop/original.wav) | [Prepared](listening_20261111/pop/everyday_smoothed.wav) | [Prepared](listening_20261111/pop/mixed_smoothed.wav) |
| Choir / religious | [Original](listening_20261111/choir/original.wav) | [Prepared](listening_20261111/choir/everyday_smoothed.wav) | [Prepared](listening_20261111/choir/mixed_smoothed.wav) |
| Minimal house, 110 BPM requested | [Original](listening_focused_20261111/minimal_house_110/original.wav) | [Prepared](listening_focused_20261111/minimal_house_110/everyday.wav) | [Prepared](listening_focused_20261111/minimal_house_110/mixed.wav) |
| Latin / bossa, 90 BPM requested | [Original](listening_focused_20261111/latin_bossa_90/original.wav) | [Prepared](listening_focused_20261111/latin_bossa_90/everyday.wav) | [Prepared](listening_focused_20261111/latin_bossa_90/mixed.wav) |
| Handwritten control, exact 96 BPM | [MIDI](listening_20261111/chatgpt_midi/handwritten_trap.mid) | [Everyday only](listening_20261111/chatgpt_midi/handwritten_trap_everyday.wav) | [Mixed](listening_20261111/chatgpt_midi/handwritten_trap.wav) |

Prepared renders balance and smooth samples before applying MIDI velocity.
The earlier unprepared WAVs remain alongside them for comparison.
Mixed renders offer the existing bass/drum samples in addition to everyday
foley; both bossa variants are identical because the mapper selected glass
clink for every transcribed note. Everyday sounds here are synthetic foley.

## Experiment notes and provenance

- [Initial four-genre experiment](listening_20261111/README.md): prompts, versions,
  note counts, and before/after preparation comparisons.
- [Sample-aware prompt experiment](listening_focused_20261111/README.md): a smaller
  sound library without paper crumple, explicit BPMs and independent tempo estimates.
- [Handwritten control](listening_20261111/chatgpt_midi/README.md): a separate
  comparison that bypasses generation and transcription.
- [Legacy jazz renders](rendered/README.md): earlier mapping examples.
- `review_manifest.json`: media sizes, durations and SHA-256 hashes.

Each successful model experiment includes `original.wav`, `transcribed.mid`,
rendered WAVs, mapping decisions and `result.json`. `session.json` summarizes
the batch. JSON artifact paths are relative to **this outputs folder**; sample
filenames inside mappings refer to the shared `../Sounds` library.

Short-clip tempo estimates are approximate. Sparse transcription and instrument
misidentification are recorded rather than corrected by adding invented notes.
Failed first house audio/MIDI are retained with `_attempt1` filenames and are
identified in the focused experiment's notes. Empty MIDI is not a successful result.

Scripts locate the project from their own file location; no personal machine
paths or credentials are required. The main project's shared environment is
used to rerun them. Raw diagnostic logs and test fixtures were removed.

## Local model cache

`.model_cache/` is retained locally so existing checkpoints can be reused.
It is excluded from the review file list. Reviewable media and reports do not
depend on that cache for playback or inspection. It is only needed for inference.

## Include the review artifacts in a commit

The output ignore rules include the curated review folders and exclude model
caches, logs and new runtime output folders. From `pattern_testing`, stage them:

```powershell
git add outputs
git diff --cached --stat
```

`review-files.txt` includes only the review audio, MIDI, reports, documentation
and reproducible scripts. Model weights and cache metadata stay local. The
cleanup did not stage, commit or push files. Rerunning experiments may produce
new files; review and update this list before including additional artifacts.
