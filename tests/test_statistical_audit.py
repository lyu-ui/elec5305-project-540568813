import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from audit_statistics import exact_sign_flip, holm, risk_curve
from prepare_portable_analysis import compare_tables


class StatisticalAuditTests(unittest.TestCase):
    def test_exact_p_includes_both_tails(self):
        self.assertEqual(exact_sign_flip(np.ones(8)),2/256)
        self.assertEqual(exact_sign_flip(np.zeros(8)),1)
        d=np.array([1.,2.,-4.])
        self.assertEqual(exact_sign_flip(d),exact_sign_flip(-d))

    def test_global_curve_cannot_cherry_pick_equal_scores(self):
        curve,area=risk_curve([1,9],[2,2],[1,1])
        self.assertEqual(len(curve),1)
        self.assertEqual(area,5)
        curve,area=risk_curve([1,9],[2,1],[1,3])
        np.testing.assert_allclose(curve.coverage,[.25,1])
        np.testing.assert_allclose(curve.risk_cm,[1,7])
        self.assertAlmostEqual(area,.25*1+.75*7)

    def test_holm_is_monotone_in_ordered_p_values(self):
        np.testing.assert_allclose(holm([.4,.01,.02]),[.4,.03,.04])

    def test_portable_check_rejects_real_numeric_and_text_changes(self):
        reference=pd.DataFrame({'id':['a','b'],'x':[1.,2.]})
        harmless=reference.copy();harmless.loc[0,'x']+=1e-12
        compare_tables(harmless,reference)
        changed=reference.copy();changed.loc[0,'x']+=.01
        with self.assertRaises(AssertionError):compare_tables(changed,reference)
        changed=reference.copy();changed.loc[0,'id']='another'
        with self.assertRaises(AssertionError):compare_tables(changed,reference)


if __name__=='__main__':unittest.main()
