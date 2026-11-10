import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'python'))
from confirm_analysis import one_sided_sign_flip, permutation_less


class ConfirmationStatisticsTests(unittest.TestCase):
    def test_one_sided_sign_flip_matches_enumeration(self):
        self.assertEqual(one_sided_sign_flip(-np.ones(11), 'less'), 1/2048)
        self.assertEqual(one_sided_sign_flip(np.ones(11), 'greater'), 1/2048)
        self.assertEqual(one_sided_sign_flip(np.ones(11), 'less'), 1.0)

    def test_permutation_less_extreme_split(self):
        values = np.array([0., 0, 0, 0, 0, 1, 1, 1, 1, 1, 1])
        is_a = np.array([True]*5 + [False]*6)
        self.assertEqual(permutation_less(values, is_a), 1/462)
        self.assertEqual(permutation_less(values, ~is_a), 1.0)


if __name__ == '__main__':
    unittest.main()
