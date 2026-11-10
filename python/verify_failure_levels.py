"""Check the published multi-level failure analysis without audio downloads."""
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'experiments/failure_levels'


def validate() -> dict:
    status = json.loads((OUT/'status.json').read_text())
    for key, path in [('protocol_sha256', 'experiments/failure_levels_protocol.json'),
                      ('script_sha256', 'python/failure_levels.py')]:
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != status[key]:
            raise ValueError(f'{path} changed after the failure-level results were computed')
    levels = pd.read_csv(OUT/'error_levels_by_clip.csv')
    if len(levels) != 33:
        raise ValueError('Expected one error decomposition per recording.')
    shares = levels[[c for c in levels if c.endswith('_share')]].sum(axis=1)
    if not np.allclose(shares, 1, atol=1e-6):
        raise ValueError('Error-level shares do not sum to one.')
    tests = pd.read_csv(OUT/'primary_tests.csv')
    if len(tests) != 4 or not ((tests.sign_patterns == 256) & tests.holm_p.between(0, 1)).all():
        raise ValueError('Primary comparison table is incomplete.')
    by_clip = pd.read_csv(OUT/'selection_by_clip.csv')
    for row in tests.itertuples():
        a, b = row.comparison.split(' minus ')
        z = by_clip[(by_clip.role == row.role) & (by_clip.target == row.target) & (by_clip.coverage == .7)]
        delta = (z[z.method == a].set_index('clip').mae_cm - z[z.method == b].set_index('clip').mae_cm).mean()
        if abs(delta - row.delta_cm) > 1e-12:
            raise ValueError('Primary comparison does not match per-recording selections.')
    visual = pd.read_csv(OUT/'reference_or_model_by_phase.csv')
    if visual.labels.sum() != 46:
        raise ValueError('Expected the 46 author-confirmed visual labels.')
    windows = pd.read_csv(OUT/'stft_window_selection.csv')
    if sorted(windows.window_ms.unique()) != [20., 40., 80.]:
        raise ValueError('Expected 20, 40 and 80 ms windows.')
    return {'status': 'passed', 'recordings': int(len(levels)), 'primary_comparisons': int(len(tests)),
            'visual_labels': int(visual.labels.sum()), 'scope': 'Published tables and identities; no new computation.'}


if __name__ == '__main__':
    print(json.dumps(validate(), indent=2))
