import csv
import unittest
from pathlib import Path
from unittest.mock import patch

import mido
from fastapi import HTTPException
import api

from Apply_Sounds.yamnet_mapping import TABLE, build_sound_mapping, load_class_table, resolve_class


class YamnetMappingTests(unittest.TestCase):
    def test_table_covers_official_classes_without_renaming(self):
        rows = load_class_table()
        with TABLE.with_name("yamnet_class_map.csv").open(encoding="utf-8", newline="") as stream:
            official = list(csv.DictReader(stream))
        self.assertEqual([(r["index"], r["mid"], r["display_name"]) for r in rows],
                         [(int(r["index"]), r["mid"], r["display_name"]) for r in official])
        for row in rows:
            self.assertTrue(row["instrument"])
            result = build_sound_mapping([{"file": "sample.wav", "yamnet_class": row["index"]}]) if row["enabled"] else None
            if result:
                self.assertEqual(len(result["assignments"]), 1)

    def test_equivalent_class_identifiers(self):
        rows = load_class_table()
        expected = resolve_class("Clapping", rows)
        for value in [58, "58", "/m/0l15bq", "clapping"]:
            self.assertEqual(resolve_class(value, rows), expected)

    def test_user_class_overrides_prediction_and_confidence_is_ignored(self):
        result = build_sound_mapping([{"file": "tap.wav", "yamnet_class": "Speech", "user_class": "Knock", "score": .01}])
        self.assertEqual(result["mapping"]["drums"]["76"]["file"], "tap.wav")
        self.assertTrue(result["assignments"][0]["user_corrected"])

    def test_collision_priority_and_stable_ties(self):
        sounds = [{"file": "first.wav", "yamnet_class": "Clapping"},
                  {"file": "preferred.wav", "yamnet_class": "Clapping", "priority": 2}]
        self.assertEqual(build_sound_mapping(sounds)["mapping"]["drums"]["39"]["file"], "preferred.wav")
        sounds[1]["priority"] = 0
        self.assertEqual(build_sound_mapping(sounds)["mapping"]["drums"]["39"]["file"], "first.wav")

    def test_midi_coverage_and_strict_omissions(self):
        midi = mido.MidiFile()
        track = mido.MidiTrack()
        midi.tracks.append(track)
        track.extend([mido.Message("program_change", program=48),
                      mido.Message("note_on", note=60, velocity=100),
                      mido.Message("note_off", note=60, time=480),
                      mido.Message("note_on", note=43, velocity=100, channel=9),
                      mido.Message("note_off", note=43, time=240, channel=9)])
        sounds = [{"file": "glass.wav", "yamnet_class": "Chink, clink", "root_note": 84},
                  {"file": "knock.wav", "yamnet_class": "Knock"}]
        with patch("Apply_Sounds.yamnet_mapping.mido.MidiFile", return_value=midi):
            result = build_sound_mapping(sounds, "test.mid")
            strict = build_sound_mapping(sounds, "test.mid", fallback="omit")
        self.assertEqual(set(result["mapping"]["programs"]), {"48"})
        self.assertEqual(set(result["mapping"]["drums"]), {"43"})
        self.assertEqual(result["mapping"]["programs"]["48"]["root_note"], 84)
        self.assertEqual(result["unmapped"], [])
        self.assertEqual(len(strict["unmapped"]), 2)

    def test_exact_match_beats_high_priority_fallback(self):
        sounds = [{"file": "clap.wav", "yamnet_class": "Clapping", "priority": 99},
                  {"file": "snare.wav", "yamnet_class": "Snare drum"}]
        result = build_sound_mapping(sounds)
        self.assertEqual(result["mapping"]["drums"]["38"]["file"], "snare.wav")

    def test_silence_is_reported_and_unknown_labels_rejected(self):
        result = build_sound_mapping([{"file": "quiet.wav", "yamnet_class": "Silence"},
                                      {"file": "clap.wav", "yamnet_class": "Clapping"}])
        self.assertEqual(len(result["skipped_sounds"]), 1)
        for label in ["invented class", 521, -1, True, None]:
            with self.assertRaises(ValueError):
                build_sound_mapping([{"file": "a.wav", "yamnet_class": label}])

    def test_invalid_controls_rejected(self):
        for changes in [{"root_note": 128}, {"loop": "false"}, {"priority": float("nan")}]:
            with self.assertRaises(ValueError):
                build_sound_mapping([dict(file="a.wav", yamnet_class="Clapping", **changes)])

    def test_api_mapping_uses_library_files_and_rejects_escaping_paths(self):
        request = api.MappingRequest(sounds=[{"file": "hand_clap.wav", "yamnet_class": "Clapping"}])
        result = api.create_mapping(request)
        self.assertEqual(result["mapping"]["drums"]["39"]["file"], "hand_clap.wav")
        with self.assertRaises(HTTPException) as error:
            api.create_mapping(api.MappingRequest(sounds=[{"file": "../outside.wav", "yamnet_class": "Clapping"}]))
        self.assertEqual(error.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
