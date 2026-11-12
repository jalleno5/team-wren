# Sample-aware genre experiments

Two 16-second MusicGen Small prompts with explicit BPM and prominent instruments
chosen to match the available samples. All renders use automatic sample
preparation before MIDI velocity. No source sample files were edited.

| Style | Requested BPM | Estimated source BPM | Original | Everyday samples | Mixed samples |
| --- | --- | --- | --- | --- | --- |
| Minimal house | 110 | 109.96 | [Play](minimal_house_110/original.wav) | [Play](minimal_house_110/everyday.wav) | [Play](minimal_house_110/mixed.wav) |
| Latin / bossa | 90 | 120.19 | [Play](latin_bossa_90/original.wav) | [Play](latin_bossa_90/everyday.wav) | [Play](latin_bossa_90/mixed.wav) |

Tempo estimates use librosa beat tracking on the original audio without supplying
the requested BPM. They are estimates from short clips, with possible beat
ambiguity. Nothing was stretched, quantized or retimed to make the results match
the prompt. MIDI tempo metadata is absent; default MIDI tempo does not describe
the estimated musical pulse. Both originals are 15.94 seconds long.

House prompt: "Minimal house groove at 110 BPM with a clear glockenspiel melody,
deep fingered electric bass, steady bass drum, woodblock percussion and hand
claps. Clean dry sound, sparse arrangement."

Bossa prompt: "Sparse relaxed Latin bossa nova instrumental at exactly 90 BPM in
steady 4/4 time. Prominent playful marimba melody with occasional glockenspiel
notes, warm fingered electric bass playing a simple syncopated bass line, dry
woodblock rhythm, soft hand claps and finger snaps, gentle bass drum. Exclusive
instrumentation: marimba, glockenspiel, electric bass, woodblock, hand claps,
finger snaps, bass drum. Short distinct notes, spacious arrangement, clean dry
studio recording."

## Sample selection and actual results

The everyday candidates are door knock, finger snap, clap, switch click, glass
clink and water drop. Mixed additionally offers kick.wav and bass.wav. Paper
crumple, zipper and key jingle were omitted for this comparison so long noisy
tails cannot build up. These are intentionally restricted demo libraries; the
application's global class table and default sample library were not changed.

The previous country demo triggered the 1.1-second paper sample 52 times; pop
triggered it 30 times. Overlapping one-shot tails are a plausible contributor
to the wash of noise. Level normalization alone does not prevent this overlap.

House transcription recovered only 8 drum notes. The everyday render uses door
knock (4 notes) and finger snap (4 notes); mixed uses kick (4) and finger snap
(4). It does not reproduce a complete house arrangement.

Bossa transcription recovered 58 notes, classified as celesta and alto sax,
despite the instrument requests. Both variants map these to glass_clink.wav,
so the everyday and mixed bossa WAVs are identical. The source prompt did not
reliably constrain the transcription's instrument assignments.

Every transcribed note was rendered with no unmapped parts. All six final WAVs
were checked for readable, finite, non-silent audio. These are pipeline
experiments, not an auditory quality assessment.

The first house attempt returned no transcribed notes. It is preserved as
minimal_house_110/original_attempt1.wav and transcribed_attempt1.mid; the linked
house take uses the shorter prompt above with seed 243. Bossa uses seed 242.
Full prompts, seeds, mapping choices and counts are saved in each folder.
Machine-specific raw logs were removed for sharing. Artifact paths in JSON
reports are relative to `outputs/`.
tempo_analysis.json records the independent tempo estimates.

Generation and transcription both ran with Transformers 4.43.4 and the shared
GPU environment. MusicGen's loading code was fixed to use explicit device
placement because this version does not support device_map="auto".
