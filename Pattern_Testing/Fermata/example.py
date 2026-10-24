
from fermata import Fermata

model = Fermata()

tokens = model.generate(
    output="../MIDI_sequences/example_beat.mid",
    genre="electronic",
    ensemble="band",
    bpm=120,
    key=0,
    mode="minor",
    meter="4/4",
    instruments=[0, 5, 33],
    drums=True,
    temperature=0.8,
    top_k=24,
    top_p=0.95,
    max_new_tokens=1800,
    seed=42,
)
