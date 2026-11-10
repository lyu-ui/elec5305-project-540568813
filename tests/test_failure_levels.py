import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'python'))
from failure_levels import decompose, exact_sign_flip, partial_spearman, select


def recording(n=400, seed=0):
    rng = np.random.default_rng(seed)
    q = np.linspace(0, 1, n, endpoint=False)
    ref = 10*(1-q)
    pred = .7*ref + .2*np.sin(6*q) + rng.normal(0, .05, n)
    return pd.DataFrame({'time_s': .02*np.arange(n), 'fill_fraction_reference': q, 'length_ref_cm': ref,
                         'length_pred_cm': pred, 'reliability_score': rng.normal(size=n)})


class FailureLevelTests(unittest.TestCase):
    def test_components_rebuild_error_and_shares_sum_to_one(self):
        g = recording()
        c = decompose(g)
        np.testing.assert_allclose(c.offset + c.rate + c.slow + c.fast, c.e, atol=1e-12)
        total = np.mean(c.e**2)
        parts = [np.mean(c.offset**2), np.mean(c.rate**2), np.mean(c.slow**2), np.mean(c.fast**2),
                 2*np.mean(c.slow*c.fast)]
        self.assertAlmostEqual(sum(parts)/total, 1, places=6)

    def test_gain_error_appears_as_offset_and_rate(self):
        g = recording()
        g['length_pred_cm'] = .7*g.length_ref_cm
        c = decompose(g)
        self.assertLess(np.mean(c.slow**2) + np.mean(c.fast**2), 1e-20)

    def test_time_stratified_selection_keeps_every_bin(self):
        g = recording(n=100)
        g['y'] = g.fill_fraction_reference          # error tied to position only
        g['reliability_score'] = -g.fill_fraction_reference
        # Global ranking would drop late frames; stratified keeps 70% of every bin.
        self.assertLess(select(g, 'combined', .7, 'y'), g.y.mean())
        self.assertAlmostEqual(select(g, 'time_stratified_combined', .7, 'y'), g.y.mean(), delta=.02)

    def test_partial_correlation_removes_shared_position(self):
        rng = np.random.default_rng(1)
        q = rng.uniform(size=3000)
        x, y = q + .05*rng.normal(size=3000), q + .05*rng.normal(size=3000)
        self.assertGreater(np.corrcoef(x, y)[0, 1], .9)
        self.assertLess(abs(partial_spearman(x, y, q)), .06)

    def test_exact_sign_flip_for_eight_consistent_changes(self):
        self.assertEqual(exact_sign_flip(-np.ones(8)), 2/256)


if __name__ == '__main__':
    unittest.main()
