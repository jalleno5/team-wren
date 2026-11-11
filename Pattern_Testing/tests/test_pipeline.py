import json
import tempfile
import unittest
import types
from pathlib import Path
from unittest.mock import patch

import mido
import numpy as np
import soundfile as sf
from fastapi import HTTPException

import api
import pipeline
from Apply_Sounds.render_midi_sounds import apply_sounds, extract_notes
from transcribe import transcribe


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.midi = self.root / "input.mid"
        midi = mido.MidiFile()
        track = mido.MidiTrack()
        midi.tracks.append(track)
        track.extend([
            mido.MetaMessage("set_tempo", tempo=500000),
            mido.Message("note_on", note=60, velocity=100),
            mido.MetaMessage("set_tempo", tempo=1000000, time=480),
            mido.Message("note_off", note=60, time=480),
        ])
        midi.save(self.midi)
        sf.write(self.root / "tap.wav", np.sin(np.arange(4410) * .1) * .2, 44100)
        self.mapping = {"programs": {"0": {"file": "tap.wav", "loop": True}}}

    def test_tempo_changes(self):
        notes = extract_notes(mido.MidiFile(self.midi))
        self.assertAlmostEqual(notes[0][1], 1.5)

    def test_transcriber_receives_waveform_and_actual_sample_rate(self):
        received = {}

        def infer(waveform, **kwargs):
            received.update(kwargs, shape=waveform.shape, dtype=waveform.dtype)
            return mido.MidiFile(self.midi)

        with patch.dict("sys.modules", {"mt3_infer": types.SimpleNamespace(transcribe=infer)}):
            output = transcribe(self.root / "tap.wav", self.root / "transcribed.mid")
        self.assertEqual(received["sr"], 44100)
        self.assertEqual(received["shape"], (4410,))
        self.assertEqual(received["dtype"], np.float32)
        self.assertEqual(received["model"], "yourmt3")
        self.assertTrue(output.is_file())

    def test_dictionary_and_json_render_identically(self):
        mapping_path = self.root / "map.json"
        mapping_path.write_text(json.dumps(self.mapping))
        a, b = self.root / "a.wav", self.root / "b.wav"
        result = apply_sounds(self.midi, self.mapping, a, sounds_dir=self.root)
        apply_sounds(self.midi, mapping_path, b)
        self.assertEqual(a.read_bytes(), b.read_bytes())
        self.assertEqual(result["rendered_notes"], 1)
        audio, rate = sf.read(a)
        self.assertEqual(rate, 44100)
        self.assertEqual(audio.shape, (77175, 2))
        self.assertGreater(np.abs(audio).max(), 0)

    def test_unmapped_notes_fail_explicitly(self):
        with self.assertRaisesRegex(ValueError, "No notes"):
            apply_sounds(self.midi, {"drums": {"36": "tap.wav"}}, self.root / "out.wav", sounds_dir=self.root)

    def test_midi_survives_optional_render_failure(self):
        def generate(prompt, output, **kwargs):
            output.touch()
            return output

        def transcribe(audio, output, **kwargs):
            output.write_bytes(self.midi.read_bytes())
            return output

        stages = []
        with patch.object(pipeline, "generate_music", side_effect=generate), patch.object(
            pipeline, "transcribe_audio", side_effect=transcribe
        ):
            result = pipeline.run_pipeline("beat", self.root / "job", mapping={"programs": {"0": "missing.wav"}},
                                           sounds_dir=self.root, progress=stages.append)
        self.assertIn("render_error", result)
        self.assertTrue((self.root / "job" / result["artifacts"]["midi"]).is_file())
        self.assertEqual(stages, ["generating", "transcribing", "rendering"])

    def test_api_rejects_sample_escape(self):
        with patch.object(api, "SOUNDS", self.root):
            with self.assertRaises(HTTPException) as error:
                api.validate_mapping({"programs": {"0": "../outside.wav"}})
        self.assertEqual(error.exception.status_code, 422)

    def test_api_requires_key(self):
        with patch.dict("os.environ", {"MUSIC_API_KEY": "secret"}):
            with self.assertRaises(HTTPException) as error:
                api.authorize(None)
        self.assertEqual(error.exception.status_code, 401)

    def test_api_job_status_and_midi_download(self):
        folder = self.root / "550e8400-e29b-41d4-a716-446655440000"
        folder.mkdir()
        (folder / "transcribed.mid").write_bytes(self.midi.read_bytes())
        with patch.object(api, "OUTPUTS", self.root):
            api.update_job(folder, id=folder.name, status="failed")
            data = api.get_job(folder.name)
            self.assertIn("midi", data["downloads"])
            response = api.download(folder.name, "midi")
            self.assertEqual(response.media_type, "audio/midi")
            with self.assertRaises(HTTPException):
                api.download(folder.name, "../job.json")


if __name__ == "__main__":
    unittest.main()
