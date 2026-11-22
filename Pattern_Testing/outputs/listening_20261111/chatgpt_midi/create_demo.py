"""Handwritten four-bar trap pattern: 96 BPM, exactly ten seconds of MIDI."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "outputs"))
from artifact_paths import write_report
import mido
import numpy as np
import soundfile as sf
from Apply_Sounds.render_midi_sounds import apply_sounds

OUT = Path(__file__).resolve().parent
TPQ = 480
END = 16 * TPQ
TEMPO = 625000  # 96 BPM; four bars of 4/4 = 10 seconds.


def make_track(midi, name, channel, notes, program=None):
    track = mido.MidiTrack()
    midi.tracks.append(track)
    track.append(mido.MetaMessage("track_name", name=name))
    if program is not None:
        track.append(mido.Message("program_change", program=program, channel=channel))
    events = []
    for beat, length, pitch, velocity in notes:
        start = round(beat * TPQ)
        stop = min(END, start + max(1, round(length * TPQ)))
        events.extend([(start, 1, mido.Message("note_on", channel=channel, note=pitch, velocity=velocity)),
                       (stop, 0, mido.Message("note_off", channel=channel, note=pitch, velocity=0))])
    previous = 0
    for tick, _, message in sorted(events, key=lambda event: (event[0], event[1])):
        track.append(message.copy(time=tick - previous))
        previous = tick
    track.append(mido.MetaMessage("end_of_track", time=END - previous))


def main():
    midi = mido.MidiFile(ticks_per_beat=TPQ)
    conductor = mido.MidiTrack()
    midi.tracks.append(conductor)
    conductor.extend([mido.MetaMessage("set_tempo", tempo=TEMPO),
                      mido.MetaMessage("time_signature", numerator=4, denominator=4),
                      mido.MetaMessage("key_signature", key="Cm"),
                      mido.MetaMessage("end_of_track", time=END)])
    drums, bass, melody = [], [], []
    kicks = [[0, 1.5, 2.75], [0, .75, 3.25], [0, 1.75, 2.75], [0, 1.25, 3.5]]
    bass_lines = [
        [(0, 1.3, 36), (1.5, .65, 36), (2.75, .9, 43)],
        [(0, 1.4, 32), (1.75, .65, 32), (3.25, .55, 35)],
        [(0, 1.4, 36), (1.75, .65, 43), (2.75, .85, 39)],
        [(0, 1.0, 31), (1.25, 1.25, 31), (3.5, .35, 35)],
    ]
    for bar in range(4):
        offset = bar * 4
        for beat in kicks[bar]:
            drums.append((offset + beat, .1, 36, 116 if beat == 0 else 102))
        # Half-time backbeat on beat three, with a quiet last-bar pickup.
        drums.append((offset + 2, .1, 38, 110))
        if bar == 3:
            drums.append((offset + 3.75, .08, 38, 57))
        for step in range(8):
            drums.append((offset + step * .5, .06, 42, 70 if step % 2 == 0 else 46))
        # Sparse sixteenth/triplet rolls, rather than continuous busy hats.
        for beat in ([3.25, 3.75] if bar % 2 == 0 else [3.5 + 1/6, 3.5 + 2/6]):
            drums.append((offset + beat, .04, 42, 40))
        drums.append((offset + .75, .05, 37, 40))
        bass.extend((offset + beat, length, pitch, 106) for beat, length, pitch in bass_lines[bar])
        motif = [(0, .3, 84), (.75, .3, 79), (1.5, .5, 75)]
        if bar % 2:
            motif = [(0, .3, 80), (1, .3, 79), (2.75, .5, 74)]
        melody.extend((offset + beat, length, pitch, 66) for beat, length, pitch in motif)
    make_track(midi, "Trap drums", 9, drums)
    make_track(midi, "Sub bass", 0, bass, program=38)
    make_track(midi, "Sparse minor glass melody", 1, melody, program=9)
    path = OUT / "handwritten_trap.mid"
    midi.save(path)
    assert abs(mido.MidiFile(path).length - 10) < 1e-6

    # Estimate a reference pitch from the existing bass sample's strongest low
    # frequency, not a classifier/model. Save it so the transposition is explicit.
    sample, rate = sf.read(ROOT / "Sounds/bass.wav", always_2d=True)
    mono = sample.mean(axis=1)
    spectrum = np.abs(np.fft.rfft(mono * np.hanning(len(mono))))
    frequencies = np.fft.rfftfreq(len(mono), 1 / rate)
    band = np.flatnonzero((frequencies >= 30) & (frequencies <= 500))
    frequency = float(frequencies[band[np.argmax(spectrum[band])]])
    bass_root = int(round(69 + 12 * np.log2(frequency / 440)))
    mapping = {
        "programs": {
            "38": {"file": "bass.wav", "root_note": bass_root, "loop": True},
            "9": {"file": "glass_clink.wav", "root_note": 84, "loop": False},
        },
        "drums": {"36": "kick.wav", "38": "hand_clap.wav", "42": "finger_snap.wav", "37": "switch_click.wav"},
    }
    (OUT / "mapping.json").write_text(json.dumps(mapping, indent=2) + "\n")
    result = apply_sounds(path, mapping, OUT / "handwritten_trap.wav", sounds_dir=ROOT / "Sounds")
    # End the listening preview at precisely ten seconds, fading only its last
    # 15 ms. The untrimmed sample-tail render is not needed for this short demo.
    audio, rate = sf.read(OUT / "handwritten_trap.wav", always_2d=True)
    target = rate * 10
    if len(audio) < target:
        audio = np.pad(audio, ((0, target - len(audio)), (0, 0)))
    audio = audio[:target]
    fade = round(.015 * rate)
    audio[-fade:] *= np.linspace(1, 0, fade)[:, None]
    sf.write(OUT / "handwritten_trap.wav", audio, rate, subtype="PCM_16")
    result.update(bpm=96, duration_seconds=10, note_count=len(drums) + len(bass) + len(melody),
                  bass_reference_hz=frequency, bass_reference_midi=bass_root,
                  source="Handwritten notes; no generation/transcription/classification models")
    write_report(OUT / "result.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
