"""Behavioral checks for score use and selection, independent of audio downloads."""
import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'python'))
from demo_recording import apply_frozen_score, select_frames
from reproduce_analysis import FEAT


class DemoTests(unittest.TestCase):
    def test_reference_columns_cannot_change_scores(self):
        coef = pd.read_csv(ROOT / 'results/score_coefficients.csv')
        frames = pd.DataFrame([coef['mean'].to_numpy()[1:]] * 3, columns=FEAT)
        scores = apply_frozen_score(frames, coef)
        frames['abs_error_cm'] = [0, 1000, -1000]
        frames['length_ref_cm'] = [np.nan, np.inf, -np.inf]
        np.testing.assert_array_equal(scores, apply_frozen_score(frames, coef))

    def test_equal_scores_keep_temporal_order_and_ceil_count(self):
        np.testing.assert_array_equal(select_frames(np.ones(3), .5), [True, True, False])

    def test_highest_scores_retained(self):
        np.testing.assert_array_equal(select_frames([-2, -.5, -1, -3], .5), [False, True, True, False])

    def test_invalid_scores_and_retention_rejected(self):
        for scores, retention in [([], .7), ([1, np.nan], .7), ([1], 0), ([1], 1.1), ([1], np.nan)]:
            with self.subTest(scores=scores, retention=retention), self.assertRaises(ValueError):
                select_frames(scores, retention)

    def test_missing_or_reordered_features_rejected(self):
        coef = pd.read_csv(ROOT / 'results/score_coefficients.csv')
        frame = pd.DataFrame(np.ones((1, len(FEAT))), columns=FEAT)
        with self.assertRaises(ValueError):
            apply_frozen_score(frame, coef.iloc[::-1])
        with self.assertRaises(KeyError):
            apply_frozen_score(frame.drop(columns=FEAT[0]), coef)


if __name__ == '__main__':
    unittest.main()
