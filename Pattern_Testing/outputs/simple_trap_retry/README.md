# Simple trap retry

**[Start here: everyday-sound preview](listen.wav)** (9.10 seconds).

Prompt: "A simple trap instrumental at 90 BPM, punchy kick, crisp snare, ticking
hi-hats, deep sub bass and a sparse bell melody. Clean dry recording."

MusicGen Small generated two 12-second takes. YourMT3+ transcribed each. The
selected take has note onsets in 9 of 12 seconds; the alternate has onsets in
5 of 12 seconds and a long gap. This selection measures temporal coverage,
not transcription accuracy or an auditory quality rating. BPM is requested,
not guaranteed or independently measured in this experiment.

| Take | MusicGen original | Everyday render | Mixed render | Transcribed notes |
| --- | --- | --- | --- | --- |
| 501, selected | [Play](take_501/original.wav) | [Play](take_501/everyday.wav) | [Play](take_501/mixed.wav) | 51 drums |
| 502, alternate | [Play](take_502/original.wav) | [Play](take_502/everyday.wav) | [Play](take_502/mixed.wav) | 30 drums |

## Selected preview

The main preview uses the unchanged take-501 MIDI with everyday sounds only:

- Door knock: 31 kick/tom hits.
- Switch click: 4 side-stick hits.
- Finger snap: 9 hi-hat hits.
- Hand clap: 7 snare hits.

The door-knock source contains three knocks. `one_shots/` contains copies cut
to a single short hit, with a short tail fade, to prevent busy notes from
triggering multiple knocks. Other percussive samples are similarly shortened.
The original Sounds files remain unchanged; `one_shots/sources.json` records
their hashes and the copy durations. No paper, key-jingle or zipper sample is
used. Normal renderer smoothing and balancing precede MIDI velocity.

`take_501/everyday_tight.wav` preserves the original timing. `listen.wav`
removes 2.17 seconds of leading empty time and adds a short final fade. It does
not add notes, replace the transcription with a written pattern, quantize or
retime the beat. Bass and bell parts were lost during transcription; this is
a percussion-only reconstruction rather than the full original arrangement.

Mappings for these auditions are selected manually by drum/program role.
They do not run YAMNet or change the application's global class table.
The mixed versions use the existing kick and bass samples where applicable;
neither take recovered a melodic bass part.

`run_demos.py` reproduces the two cached-model pipeline attempts;
`prepare_preview.py` reproduces the short-hit preview without model calls.
Reports use paths relative to outputs. Raw machine-specific logs were removed
from the review artifacts. Audio was checked for finite, non-silent samples;
listening quality remains for the listener to assess.
