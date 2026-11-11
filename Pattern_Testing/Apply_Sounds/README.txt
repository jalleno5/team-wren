Apply everyday sounds to an existing MIDI

Run these commands from the pattern_testing folder. Use the shared .venv;
there is no separate renderer environment or requirements file.
Follow ../README.md for initial setup.

Install/update the shared dependencies if needed:
.venv/Scripts/python -m pip install -r requirements.txt

Render an existing MIDI with the provided mapping:
.venv/Scripts/python Apply_Sounds/render_midi_sounds.py "../MIDI_sequences/jazz.mid" --mapping sound_map.json --output jazz_custom.wav

This writes outputs/rendered/jazz_custom.wav. The input MIDI stays unchanged.
The renderer resolves relative CLI paths from the Apply_Sounds directory;
sample paths in the mapping resolve from Sounds by default.

To create a new mapping template for an existing MIDI:
.venv/Scripts/python Apply_Sounds/new_sound_map.py "../MIDI_sequences/jazz.mid" --output custom_map.json

Edit Apply_Sounds/custom_map.json to replace placeholder filenames with files
from Sounds, then render with --mapping custom_map.json. Choose the sample
for each program/drum note yourself. This command replaces the selected output
JSON file if it already exists.

The callable apply_sounds() function also accepts a dictionary or JSON path;
see the main README for an example.
