"""Validate the published project without downloading audio or model weights.

Use --with-data after setup to additionally validate the 33 WAVs and all 14
regenerated CSVs. This validator does not execute MATLAB or neural inference.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def validate() -> dict:
    checked = 0
    for line in (ROOT / 'CHECKSUMS.sha256').read_text().splitlines():
        expected, name = line.split('  ', 1)
        path = ROOT / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Published file is missing or changed: {name}')
        checked += 1
    manifest = pd.read_csv(ROOT / 'reference/recording_manifest.csv')
    counts = manifest.role.value_counts().to_dict()
    expected_counts = {'development': 11, 'seen_test': 8, 'unseen_test': 8, 'shape_diagnostic': 6}
    if counts != expected_counts or manifest.container_id.nunique() != 25 or not manifest.item_id.is_unique:
        raise ValueError('Unexpected data selection or duplicate source IDs.')
    train = pd.read_csv(ROOT / 'reference/official_train.csv')
    if set(manifest.loc[manifest.role == 'unseen_test', 'container_id']) & set(train.container_id):
        raise ValueError('Unseen-container overlap with official training data.')
    dev = manifest[manifest.role == 'development']
    test = manifest[manifest.role.isin(['seen_test', 'unseen_test'])]
    if set(dev.video_id) & set(test.video_id):
        raise ValueError('Video overlap between development and held-out test.')
    predictions = 0
    for row in manifest.itertuples():
        frame = pd.read_csv(ROOT / 'reference/model_predictions' / f'{row.clip}.csv')
        if not np.isfinite(frame.to_numpy()).all() or np.any(np.diff(frame.time_s) <= 0):
            raise ValueError(f'{row.clip}: nonfinite values or unordered timestamps.')
        if np.any(frame.wavelength_cm <= 0) or frame.time_s.min() < 0 or frame.time_s.max() > row.duration_s:
            raise ValueError(f'{row.clip}: invalid physical domain or timestamps.')
        np.testing.assert_allclose(frame.pitch_hz, 34000 / frame.wavelength_cm, rtol=2e-6)
        np.testing.assert_allclose(frame.length_pred_cm, (frame.wavelength_cm-frame.wavelength_cm.iloc[-1])/4, atol=2e-6)
        np.testing.assert_allclose(frame.length_ref_cm, row.height_cm*(1-frame.time_s/row.duration_s), atol=2e-6)
        np.testing.assert_allclose(frame.abs_error_cm, abs(frame.length_pred_cm-frame.length_ref_cm), atol=2e-6)
        predictions += len(frame)
    selected = pd.read_csv(ROOT / 'results/selective_by_clip.csv')
    reported = pd.read_csv(ROOT / 'results/selective_summary.csv')
    actual = selected.groupby(['role', 'coverage', 'method']).mae_cm.agg(['mean', 'std'])
    expected = reported.set_index(['role', 'coverage', 'method'])[['mean', 'std']]
    pd.testing.assert_frame_equal(actual.sort_index(), expected.sort_index(), atol=1e-12, rtol=1e-12)
    threshold = pd.read_csv(ROOT / 'results/fixed_threshold.csv')
    if threshold.threshold.nunique() != 1 or len(threshold) != 16:
        raise ValueError('Fixed threshold results do not share one development threshold.')
    return {'published_files_verified': checked, 'recordings': len(manifest),
            'containers': int(manifest.container_id.nunique()), 'roles': counts,
            'cached_prediction_frames': predictions, 'summary_aggregation': 'passed',
            'physical_equations': 'passed', 'split_integrity': 'passed',
            'scope': 'File integrity, cached physical decoding and evaluation consistency; no MATLAB execution.'}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--with-data', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs/verification/project_check.json')
    args = parser.parse_args()
    result = validate()
    from verify_extension import validate as validate_extension
    result['experimental_extension'] = validate_extension()
    from verify_statistical_audit import validate as validate_statistical_audit
    result['statistical_audit'] = validate_statistical_audit()
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', str(ROOT/'tests'), '-v'], cwd=ROOT, check=True)
    result['demonstration_behavior_tests'] = 'passed'
    if args.with_data:
        for name in ['verify_inputs.py', 'verify_selection.py', 'verify_generated_results.py']:
            subprocess.run([sys.executable, str(ROOT/'python'/name)], cwd=ROOT, check=True)
        result['local_inputs_and_regenerated_tables'] = 'passed'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    print('Project verification passed.')


if __name__ == '__main__':
    main()
