# Handwritten trap control

This control bypasses generation, transcription and classification to isolate
arrangement and sample rendering. The production pipeline still uses MusicGen
and YourMT3+.

- [MIDI](handwritten_trap.mid): 85 manually written notes, four bars of 4/4,
  exactly 10 seconds at 96 BPM.
- [Mixed render](handwritten_trap.wav): kick/bass samples plus everyday foley.
- [Everyday-only render](handwritten_trap_everyday.wav): the identical MIDI using
  only synthetic everyday sound samples.

| MIDI part | Mixed mapping | Everyday-only mapping |
| --- | --- | --- |
| Bass, program 38 | bass.wav | glass_clink.wav |
| Melody, program 9 | glass_clink.wav | water_drop.wav |
| Kick, drum 36 | kick.wav | door_knock.wav |
| Snare, drum 38 | hand_clap.wav | hand_clap.wav |
| Hi-hat, drum 42 | finger_snap.wav | finger_snap.wav |
| Side stick, drum 37 | switch_click.wav | switch_click.wav |

`mapping.json` and `everyday_mapping.json` contain the exact settings. Sample
paths refer to the project's Sounds library. Both renders apply sample
preparation before velocity and finish with a short fade at ten seconds.
Water-drop pitch is a sweep, so its MIDI root reference is approximate.

`create_demo.py` reproduces the MIDI and mixed render. The saved everyday mapping
can be passed directly to `apply_sounds()` with the same MIDI; to reproduce the
exact ten-second file, apply the same final duration/fade as the script.
