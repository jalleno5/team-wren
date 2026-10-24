cd into the fermata directory
cd ./Fermata

In order to generate using the fermata wrapper you must install the requirements in a python environment:
Run the below line to do so:
python -m pip install -r requirements.txt

To generate the midi run this command. Check the parameters of the generation function if you would like to add more
python fermata.py --genre jazz --bpm 95 --instruments 0 33 48 --output ../MIDI_sequences/jazz.mid

This will lead to generating a midi file in the midi_sequences folder.
