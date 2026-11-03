cd into the Apply_Sounds directory
cd ./Apply_Sounds

In order to apply the sounds you must have a mapping json and the requirements installed
Run the below line to do so:
python -m pip install -r requirements.txt

Create your json mapping
Choosing which sounds go where could be automated in the future but seems classification related
Right now you must manually add sound path
python new_sound_map.py "../MIDI_sequences/beat1.mid"



To apply the sounds and get your output run the following
python render_midi_sounds.py "../MIDI_sequences/jazz.mid" --mapping sound_map.json --output jazz_custom.wav

This will lead to generating a midi file in the midi_sequences folder.