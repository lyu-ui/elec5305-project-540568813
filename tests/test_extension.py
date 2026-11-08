import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'python'))
from run_extension import add_noise, terminal_estimate
from evaluate_visual_reference import relative_bounds, error_bounds


class ExtensionTests(unittest.TestCase):
    def test_noise_snr_and_repeatability(self):
        x = np.sin(np.arange(16000)*.137).astype(np.float32)
        a, snr = add_noise(x, 10, 7)
        b, _ = add_noise(x, 10, 7)
        np.testing.assert_array_equal(a, b)
        self.assertAlmostEqual(snr, 10, places=5)
        c, _ = add_noise(x, 20, 7)
        np.testing.assert_allclose((a-x)/np.sqrt(10), c-x, atol=2e-7)

    def test_silent_signal_rejected(self):
        with self.assertRaises(ValueError):
            add_noise(np.zeros(100), 10, 1)

    def test_endpoint_change_is_a_global_offset(self):
        t = np.arange(20)*.02
        lam = np.r_[np.linspace(80, 20, 19), 60]
        terminal = terminal_estimate(t, lam, .2)
        baseline = (lam-lam[-1])/4
        changed = (lam-terminal)/4
        np.testing.assert_allclose(changed-baseline, (lam[-1]-terminal)/4)

    def test_smoothing_can_hurt_a_perfect_trajectory(self):
        t = np.arange(51)*.02
        lam = 60-40*t
        truth = (lam-lam[-1])/4
        replacement = (lam-terminal_estimate(t,lam,.2))/4
        self.assertGreater(np.mean(np.abs(replacement-truth)), 0)

    def test_visual_proxy_is_invariant_to_pixel_scale_and_origin(self):
        a = relative_bounds([10,12], [100,104], [49,53])
        b = relative_bounds([27,31], [207,215], [105,113])
        np.testing.assert_allclose(a,b)
        self.assertLessEqual(a[1],a[0])
        self.assertGreaterEqual(a[2],a[0])

    def test_visual_interval_is_not_a_point_label(self):
        self.assertEqual(error_bounds(.5,.4,.6)[0],0)
        np.testing.assert_allclose(error_bounds(.8,.4,.6),(.2,.4))
        with self.assertRaises(ValueError):
            relative_bounds([10,20],[15,25],[18,22])


if __name__ == '__main__':
    unittest.main()
