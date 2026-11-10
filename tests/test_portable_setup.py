import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'python'))
from setup_project import check_analysis_wav


class PortableAnalysisWavTests(unittest.TestCase):
    """Portable mode accepts platform-dependent bytes only for valid analysis WAVs."""

    def write(self, folder, fs, y):
        path = Path(folder)/'clip.wav'
        wavfile.write(path, fs, y)
        return path

    def test_accepts_16k_mono_float32_with_manifest_length(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.write(folder, 16000, np.zeros(160, np.float32))
            check_analysis_wav(path, {'clip': 'clip_x', 'samples': '160'})

    def test_rejects_wrong_length_rate_type_or_values(self):
        bad = [(16000, np.zeros(159, np.float32)), (48000, np.zeros(160, np.float32)),
               (16000, np.zeros(160, np.int16)), (16000, np.full(160, np.nan, np.float32))]
        for fs, y in bad:
            with self.subTest(fs=fs, dtype=y.dtype, n=len(y)), tempfile.TemporaryDirectory() as folder:
                with self.assertRaises(ValueError):
                    check_analysis_wav(self.write(folder, fs, y), {'clip': 'clip_x', 'samples': '160'})


if __name__ == '__main__':
    unittest.main()
