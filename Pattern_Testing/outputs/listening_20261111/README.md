# Listening demos — November 11, 2026

Updated renders with automatic sample smoothing and balancing before MIDI velocity:

| Style | Everyday smoothed | Mixed smoothed |
| --- | --- | --- |
| Trap | [Play](trap/everyday_smoothed.wav) | [Play](trap/mixed_smoothed.wav) |
| Country | [Play](country/everyday_smoothed.wav) | [Play](country/mixed_smoothed.wav) |
| Pop | [Play](pop/everyday_smoothed.wav) | [Play](pop/mixed_smoothed.wav) |
| Choir / religious | [Play](choir/everyday_smoothed.wav) | [Play](choir/mixed_smoothed.wav) |

Original renders below remain available for comparison. Source sample files
were verified unchanged by SHA-256 hashes. smoothed_results.json records the
new renders and preparation settings.

Artifact paths in JSON reports are relative to `outputs/`.

Four requested prompts were generated with MusicGen Small (12 seconds requested,
11.94 seconds saved), transcribed with YourMT3+ and rendered from the local Sounds
library. Each folder includes the original WAV, MIDI, two renders, mapping reports,
prompt/seed metadata. Machine-specific raw logs were removed for sharing.

| Style | MusicGen original | Everyday foley only | Foley + existing bass/drum samples |
| --- | --- | --- | --- |
| Trap | [Original](trap/original.wav) | [Everyday](trap/everyday.wav) | [Mixed](trap/mixed.wav) |
| Country | [Original](country/original.wav) | [Everyday](country/everyday.wav) | [Mixed](country/mixed.wav) |
| Pop | [Original](pop/original.wav) | [Everyday](pop/everyday.wav) | [Mixed](pop/mixed.wav) |
| Choir / religious | [Original](choir/original.wav) | [Everyday](choir/everyday.wav) | [Mixed](choir/mixed.wav) |

Everyday renders use the ten synthetic foley samples and their manually assigned
YAMNet labels. Mixed renders additionally offer bass.wav, kick.wav, snare.wav,
hi-hat.wav and whoosh.wav, with labels supplied from their filenames. No YAMNet
inference was run for these previews. The class mapping chooses samples per MIDI
part; it may reuse samples and leave some unused. See each mapping report for
the exact decisions. Rendered audio contains only those samples, not a blend
with the MusicGen original.

Transcription retained 16 notes for trap (drums only), 355 for country, 100 for
pop and 34 for choir. All transcribed notes were rendered without unmapped
programs/drums. The trap render is shorter than its source because its final
transcribed note ends earlier. MIDI transcription is an approximation; the choir
render replaces the transcribed parts with samples rather than preserving voices.

All 12 WAV files were checked for readable, finite, non-silent audio.
validation.json records lengths/peaks. This is file validation, not an auditory
quality assessment.

The first generation pass used Transformers 4.57.6; YourMT3 failed with that
version. Saved originals were successfully transcribed after switching to
4.43.4. requirements.txt now pins 4.43.4 and the exact MT3-Infer commit used.
PyTorch 2.8.0 + CUDA 12.8 ran on the RTX 4060 Laptop GPU in the shared .venv.

run_demos.py reproduces the four prompts and both mappings. Existing originals
and MIDI files are reused; choose a fresh output location for fresh generations.
The optional additional second-take batch was not run.


latin_bossa and minimal_house were tests to see if strict adherence to bpm could be trusted.
Results show that while guided the model does not perfectly match exact bpm. 