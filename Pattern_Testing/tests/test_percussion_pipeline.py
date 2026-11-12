import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, Mock

from fastapi import HTTPException
import mido
import numpy as np
import soundfile as sf
import torch

import api
import percussion_pipeline as pipeline
from Apply_Sounds.render_midi_sounds import extract_notes
from separate_audio import overlap_separate, separate_audio
from transcribe import transcribe


class FakeSeparator(torch.nn.Module):
    sources = ["drums", "bass", "other", "vocals"]

    def __init__(self):
        super().__init__()
        self.marker = torch.nn.Parameter(torch.zeros(1))

    def forward(self, waveform):
        return torch.stack([waveform * fraction for fraction in [.2, .3, .4, .1]], dim=1)


class PercussionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.audio = self.root / "source.wav"
        self.wave = np.repeat((.1 * np.sin(np.arange(44100) * .06) + .01)[:, None], 2, axis=1).astype(np.float32)
        sf.write(self.audio, self.wave, 44100, subtype="FLOAT")
        self.midi = self.root / "raw.mid"
        midi = mido.MidiFile()
        track = mido.MidiTrack()
        midi.tracks.append(track)
        track.extend([mido.MetaMessage("set_tempo", tempo=500000),
                      mido.Message("note_on", channel=0, note=60, velocity=90),
                      mido.Message("note_on", channel=9, note=36, velocity=100, time=240),
                      mido.MetaMessage("set_tempo", tempo=1000000, time=240),
                      mido.Message("note_off", channel=9, note=36, time=240),
                      mido.Message("note_off", channel=0, note=60, time=240)])
        midi.save(self.midi)

    def test_drum_filter_preserves_tempo_and_absolute_times(self):
        output = self.root / "drums.mid"
        self.assertEqual(pipeline.keep_drum_notes(self.midi, output), 1)
        notes = extract_notes(mido.MidiFile(output))
        self.assertEqual(len(notes), 1)
        self.assertTrue(notes[0][5])
        self.assertAlmostEqual(notes[0][0], .25)
        self.assertAlmostEqual(notes[0][1], .75)
        self.assertAlmostEqual(mido.MidiFile(output).length, mido.MidiFile(self.midi).length)

    def test_no_drums_fails_instead_of_rendering_melodic_leakage(self):
        original = mido.MidiFile(self.midi)
        for track in original.tracks:
            for msg in track:
                if getattr(msg, "channel", None) == 9:
                    msg.channel = 0
        original.save(self.midi)
        with self.assertRaisesRegex(ValueError, "no drum-channel"):
            pipeline.keep_drum_notes(self.midi, self.root / "out.mid")

    def test_chunk_overlap_has_no_gaps_or_timing_shift(self):
        signal = torch.linspace(-1, 1, 17000).repeat(2, 1)
        output = overlap_separate(FakeSeparator(), signal, 1000)
        self.assertEqual(output.shape, (4, 2, 17000))
        torch.testing.assert_close(output.sum(0), signal, atol=3e-7, rtol=1e-5)

    def test_two_stems_include_all_non_drum_sources_at_original_level(self):
        bundle = SimpleNamespace(sample_rate=44100, get_model=lambda: FakeSeparator())
        with patch("torchaudio.pipelines.HDEMUCS_HIGH_MUSDB_PLUS", bundle), patch("torch.cuda.is_available", return_value=False):
            drums, accompaniment = separate_audio(self.audio, self.root / "stems")
        a, rate = sf.read(drums)
        b, _ = sf.read(accompaniment)
        self.assertEqual(rate, 44100)
        np.testing.assert_allclose(a + b, self.wave, atol=1e-7)
        self.assertEqual(a.shape, self.wave.shape)

    def test_mix_preserves_accompaniment_alignment_and_matches_drum_level(self):
        backing, hits, reference = [self.root / name for name in ["back.wav", "hits.wav", "drums.wav"]]
        sf.write(backing, np.full((4410, 2), .2), 44100, subtype="FLOAT")
        sf.write(hits, np.full((4410, 2), .05), 44100, subtype="FLOAT")
        sf.write(reference, np.full((4410, 2), .1), 44100, subtype="FLOAT")
        output = self.root / "mixed.wav"
        report = pipeline.mix_tracks(backing, hits, reference, output)
        audio, rate = sf.read(output)
        np.testing.assert_allclose(audio, .3, atol=4e-5)
        self.assertEqual(audio.shape, (4410, 2))
        self.assertEqual(rate, 44100)
        self.assertAlmostEqual(report["percussion_level_match_db"], 6.021, places=3)
        self.assertEqual(report["master_gain_db"], 0)

    def test_mix_resamples_pads_and_limits_output(self):
        sf.write(self.root / "back.wav", np.full(2205, .8), 22050, subtype="FLOAT")
        sf.write(self.root / "hits.wav", np.full(4410, .8), 44100, subtype="FLOAT")
        report = pipeline.mix_tracks(self.root / "back.wav", self.root / "hits.wav", self.root / "hits.wav", self.root / "out.wav")
        audio, rate = sf.read(self.root / "out.wav")
        self.assertEqual(audio.shape, (4410, 2))
        self.assertLessEqual(np.abs(audio).max(), .98001)
        self.assertLess(report["master_gain_db"], 0)

    def test_existing_audio_orchestration_keeps_only_drums_and_creates_final_mix(self):
        folder = self.root / "job"
        def separator(command, **kwargs):
            sf.write(folder / "drums.wav", self.wave * .2, 44100, subtype="FLOAT")
            sf.write(folder / "accompaniment.wav", self.wave * .8, 44100, subtype="FLOAT")
        def transcribe(audio, output):
            self.assertEqual(audio.name, "drums.wav")
            output.write_bytes(self.midi.read_bytes())
            return output
        stages = []
        with patch.object(pipeline, "generate_music") as generate, patch.object(pipeline.subprocess, "run", side_effect=separator), patch.object(pipeline, "transcribe_audio", side_effect=transcribe):
            result = pipeline.run_percussion_pipeline(None, folder, source_audio=self.audio,
                       mapping={"drums": {"36": "source.wav"}}, sounds_dir=self.root, progress=stages.append)
        generate.assert_not_called()
        self.assertEqual(result["midi"]["notes"], 1)
        self.assertEqual(result["midi"]["programs"], [])
        self.assertTrue((folder / result["artifacts"]["rendered"]).is_file())
        self.assertEqual(stages, ["copying_audio", "separating", "transcribing_drums", "rendering_percussion", "mixing"])

    def test_api_validation_and_dispatch_use_separate_pipeline(self):
        request = api.PercussionRequest(prompt="trap", mapping={"drums": {"36": "source.wav"}})
        with patch.object(api, "SOUNDS", self.root):
            api.validate_percussion_request(request)
        for payload in [dict(prompt="trap"), dict(prompt=" ", mapping=request.mapping),
                        dict(prompt="trap", source_job_id="id", mapping=request.mapping),
                        dict(prompt="trap", mapping={"programs": {"0": "source.wav"}})]:
            with self.assertRaises(HTTPException):
                api.validate_percussion_request(api.PercussionRequest(**payload))
        folder = self.root / "job"
        folder.mkdir()
        with patch.object(api, "run_percussion_pipeline", return_value={"artifacts": {}}) as run, patch.object(api, "update_job") as update, patch.object(api, "SLOTS", Mock()):
            api.execute(folder, request)
        run.assert_called_once()
        self.assertEqual(update.call_args.kwargs["status"], "completed")

    def test_api_artifacts_and_classified_paths(self):
        with patch.object(api, "SOUNDS", self.root):
            with self.assertRaises(HTTPException) as error:
                api.validate_percussion_request(api.PercussionRequest(prompt="trap", sounds=[{"file": "../escape.wav", "yamnet_class": "Clapping"}]))
        self.assertEqual(error.exception.status_code, 422)
        paths = {route.path for route in api.app.routes}
        self.assertIn("/music/percussion-jobs", paths)
        for kind in ["drums", "accompaniment", "percussion", "raw_midi"]:
            self.assertIn(kind, api.ARTIFACTS)

    def test_float_stem_normalization_affects_inference_only(self):
        waveform = self.wave * 30
        sf.write(self.audio, waveform, 44100, subtype="FLOAT")
        original = self.audio.read_bytes()
        received = []
        def infer(signal, **kwargs):
            received.append(signal)
            return mido.MidiFile(self.midi)
        with patch.dict("sys.modules", {"mt3_infer": SimpleNamespace(transcribe=infer)}):
            transcribe(self.audio, self.root / "normalized.mid")
        self.assertAlmostEqual(float(np.abs(received[0]).max()), 1)
        self.assertEqual(self.audio.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
