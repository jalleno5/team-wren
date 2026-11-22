Apply sounds to MIDI

Use the shared environment and run commands from pattern_testing.
See ../README.md for installation and generation instructions.

After the pipeline creates outputs/local/transcribed.mid:

python Apply_Sounds/yamnet_mapping.py Sounds/everyday_classifications.json --midi outputs/local/transcribed.mid --output outputs/local/mapping.json
python Apply_Sounds/render_midi_sounds.py "../outputs/local/transcribed.mid" --mapping "../outputs/local/mapping.json" --output-dir "../outputs/local" --output rendered.wav

The output is outputs/local/rendered.wav. The input MIDI is unchanged.
The renderer CLI resolves relative paths from Apply_Sounds.

To create an editable mapping template instead:
python Apply_Sounds/new_sound_map.py "../outputs/local/transcribed.mid" --output "../outputs/local/custom_map.json"

Replace its placeholders with filenames from Sounds before rendering.
The callable apply_sounds() function also accepts a dictionary or JSON path.
