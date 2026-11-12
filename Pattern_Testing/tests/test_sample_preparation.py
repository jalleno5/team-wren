import unittest

import numpy as np

from Apply_Sounds.render_midi_sounds import SAMPLE_RATE, active_rms, prepare_sample, synth_note


class SamplePreparationTests(unittest.TestCase):
    def tone(self, amplitude=.5):
        t = np.arange(SAMPLE_RATE // 2) / SAMPLE_RATE
        return np.repeat((amplitude * np.sin(2 * np.pi * 440 * t))[:, None], 2, axis=1).astype(np.float32)

    def test_different_recording_levels_converge_without_mutating_input(self):
        loud, quiet = self.tone(.5), self.tone(.05)
        original = loud.copy()
        a, b = prepare_sample(loud), prepare_sample(quiet)
        np.testing.assert_array_equal(loud, original)
        self.assertEqual(a.shape, loud.shape)
        self.assertAlmostEqual(active_rms(a), .1, places=3)
        self.assertAlmostEqual(active_rms(a), active_rms(b), places=5)

    def test_velocity_is_applied_after_preparation(self):
        sample = prepare_sample(self.tone())
        soft = synth_note(sample, 60, 40, 60, .5, False, True)
        hard = synth_note(sample, 60, 100, 60, .5, False, True)
        np.testing.assert_allclose(soft, hard * .4, atol=1e-7)

    def test_stereo_balance_and_edge_fades(self):
        sample = self.tone()
        sample[:, 1] *= .25
        prepared = prepare_sample(sample)
        np.testing.assert_allclose(prepared[:, 1], prepared[:, 0] * .25, atol=1e-7)
        self.assertTrue(np.all(prepared[0] == 0) and np.all(prepared[-1] == 0))

    def test_silence_and_near_silence_do_not_get_boosted(self):
        for sample in [np.zeros((1000, 2)), self.tone(1e-7)]:
            self.assertTrue(np.all(prepare_sample(sample) == 0))

    def test_transients_stay_finite_and_below_ceiling(self):
        sample = self.tone(.01)
        sample[1000:1010] = 10
        prepared = prepare_sample(sample)
        self.assertTrue(np.isfinite(prepared).all())
        self.assertLessEqual(float(np.abs(prepared).max()), .900001)

    def test_nonfinite_samples_rejected(self):
        sample = self.tone()
        sample[1, 0] = np.nan
        with self.assertRaises(ValueError):
            prepare_sample(sample)


if __name__ == "__main__":
    unittest.main()
