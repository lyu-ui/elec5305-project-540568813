"""Check the fixed audio inputs and split integrity.

Default: every 16 kHz analysis WAV must match its recorded SHA-256.
--portable: resampled float32 bytes may differ by CPU architecture (observed on
Apple Silicon), so analysis WAVs are checked for format, length and finite
values instead; regenerated results are then compared numerically by
prepare_portable_analysis.py. Source-recording hashes are always exact in
setup_project.py.
"""
from pathlib import Path
import argparse
import hashlib

import numpy as np
import pandas as pd
from scipy.io import wavfile

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--portable', action='store_true')
args = parser.parse_args()
d = pd.read_csv(root/'reference/recording_manifest.csv')
differ = []
for r in d.itertuples():
    path = root/r.audio_file
    if hashlib.sha256(path.read_bytes()).hexdigest() == r.analysis_sha256:
        continue
    assert args.portable, f'{r.clip}: analysis hash differs (use --portable for numeric cross-platform checks)'
    fs, y = wavfile.read(path)
    assert fs == 16000 and y.dtype == np.float32 and y.ndim == 1, r.clip
    assert len(y) == r.samples and np.all(np.isfinite(y)), r.clip
    differ.append(r.clip)
tr = pd.read_csv(root/'reference/official_train.csv')
assert d.item_id.is_unique
assert not set(d[d.role=='unseen_test'].container_id)&set(tr.container_id)
assert not set(d[d.role=='development'].video_id)&set(d[d.role.isin(['seen_test','unseen_test'])].video_id)
if differ:
    print(f'{len(d)-len(differ)}/{len(d)} analysis hashes exact; {len(differ)} platform-dependent byte differences '
          f'passed format/length checks: {", ".join(differ)}. Split constraints passed.')
else:
    print(f'All {len(d)} audio hashes and the declared split constraints passed.')
