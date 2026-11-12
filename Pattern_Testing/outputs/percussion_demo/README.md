# HDemucs percussion-replacement test

**[Listen to the final mix](rendered.wav)**

This reuses the original MusicGen trap take from `simple_trap_retry/take_501`;
it does not generate another song. HDemucs splits it into a drum stem and the
sum of bass, vocals and other accompaniment. YourMT3+ transcribes only drums.
Everyday samples replace the recovered percussion; the accompaniment remains
audio and is mixed back in at its original timing.

| File | Contents |
| --- | --- |
| [generated.wav](generated.wav) | Original full song |
| [drums.wav](drums.wav) | HDemucs drums |
| [accompaniment.wav](accompaniment.wav) | Remaining music, not resynthesized |
| [transcribed.mid](transcribed.mid) | 57 retained drum notes |
| [raw_transcribed.mid](raw_transcribed.mid) | Unfiltered drum-stem transcription |
| [percussion.wav](percussion.wav) | Replacement samples before remix level matching |
| [rendered.wav](rendered.wav) | Final 11.94-second remix |

The demo uses the short one-shot copies from `../simple_trap_retry/one_shots`,
with the explicit drum mapping in `demo_mapping.json`. The API requires these
files to be staged inside its configured `MUSIC_SOUNDS_DIR`; this CLI experiment
instead passes the demo library through `--sounds`.

All 57 filtered notes were rendered, with no unmapped pitches. The original
full-mix transcription recovered 51 drum notes. More notes alone are not an
accuracy score. Separation can leave residual percussion in accompaniment.

Both mix controls are 0 dB. Replacement percussion is level-matched toward the
separated drum stem first, then the combined mix is scaled to avoid clipping.
The final clip keeps the original song duration and offsets. `result.json`
records the gains and artifact names; paths are local to this demo folder.
The separator uses TorchAudio's pretrained `HDEMUCS_HIGH_MUSDB_PLUS` bundle.

Reproduce from `pattern_testing` in the shared environment, with model cache
variables configured as in the main README:

```powershell
python percussion_pipeline.py --audio outputs/simple_trap_retry/take_501/original.wav --mapping outputs/percussion_demo/demo_mapping.json --sounds outputs/simple_trap_retry/one_shots --output-dir outputs/percussion_demo
```
