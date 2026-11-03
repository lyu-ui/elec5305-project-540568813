"""Inspect one of the 33 fixed recordings using the frozen reliability model.

This is an offline research demonstration. Selection uses acoustic features
only; assumption-derived reference errors are added afterwards for evaluation.
It neither retrains the score nor changes the published benchmark files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import wavfile
import matplotlib.pyplot as plt

from reproduce_analysis import FEAT, features

ROOT = Path(__file__).resolve().parents[1]


def apply_frozen_score(frame: pd.DataFrame, coefficients: pd.DataFrame) -> np.ndarray:
    """Apply published development-only coefficients without accessing labels."""
    expected = ['intercept'] + FEAT
    if list(coefficients.feature) != expected:
        raise ValueError('Unexpected coefficient feature order.')
    values = frame[FEAT].to_numpy(dtype=float)
    means = coefficients['mean'].to_numpy(dtype=float)[1:]
    scales = coefficients.sd.to_numpy(dtype=float)[1:]
    beta = coefficients.coefficient.to_numpy(dtype=float)
    if not all(np.isfinite(a).all() for a in [values, means, scales, beta]) or np.any(scales <= 0):
        raise ValueError('Features and coefficients must be finite, with positive scales.')
    return -(np.column_stack([np.ones(len(values)), (values - means) / scales]) @ beta)


def select_frames(scores: np.ndarray, retention: float) -> np.ndarray:
    """Stable within-recording ranking; exact same ceil rule as the benchmark."""
    scores = np.asarray(scores, dtype=float)
    if scores.ndim != 1 or not len(scores) or not np.isfinite(scores).all():
        raise ValueError('Scores must be a nonempty finite vector.')
    if not np.isfinite(retention) or not 0 < retention <= 1:
        raise ValueError('Retention must be greater than zero and at most one.')
    keep = np.zeros(len(scores), dtype=bool)
    keep[np.argsort(-scores, kind='stable')[:int(np.ceil(retention * len(scores)))]] = True
    return keep


def inspect_recording(clip: str, retention: float, output_dir: Path) -> dict:
    manifest = pd.read_csv(ROOT / 'reference/recording_manifest.csv')
    selected = manifest[manifest['clip'] == clip]
    if len(selected) != 1:
        raise ValueError(f'Unknown recording {clip!r}. Use --list to see the available IDs.')
    row = selected.iloc[0]
    source = ROOT / row.audio_file
    if not source.is_file():
        raise ValueError('Audio is missing. Run python python/setup_project.py first.')
    if hashlib.sha256(source.read_bytes()).hexdigest() != row.analysis_sha256:
        raise ValueError('Audio hash mismatch. Restore the fixed input with setup_project.py.')
    fs, raw = wavfile.read(source)
    if fs != 16000 or raw.ndim != 1 or not np.isfinite(raw).all():
        raise ValueError('Expected finite 16 kHz mono audio.')
    waveform = raw.astype(float)
    waveform -= waveform.mean()
    prediction = pd.read_csv(ROOT / 'reference/model_predictions' / f'{clip}.csv')
    # Deliberately exclude reference labels and errors from feature extraction.
    physical = prediction[['time_s', 'wavelength_cm', 'pitch_hz', 'length_pred_cm']].copy()
    if not np.isfinite(physical.to_numpy()).all() or np.any(np.diff(physical.time_s) <= 0):
        raise ValueError('Invalid cached trajectory.')
    frame, spectrum = features(waveform, physical)
    coefficients = pd.read_csv(ROOT / 'results/score_coefficients.csv')
    frame['reliability_score'] = apply_frozen_score(frame, coefficients)
    frame['retained_by_rank'] = select_frames(frame.reliability_score, retention)
    thresholds = pd.read_csv(ROOT / 'results/fixed_threshold.csv').threshold.unique()
    if len(thresholds) != 1 or not np.isfinite(thresholds[0]):
        raise ValueError('Expected one frozen development threshold.')
    threshold = float(thresholds[0])
    frame['retained_by_fixed_threshold'] = frame.reliability_score >= threshold
    # Evaluation comes after selection. No measured water-level label is claimed.
    frame['assumed_reference_cm'] = row.height_cm * (1 - frame.time_s / (len(raw) / fs))
    frame['reference_absolute_error_cm'] = abs(frame.length_pred_cm - frame.assumed_reference_cm)
    kept = frame.retained_by_rank
    fixed = frame.retained_by_fixed_threshold
    summary = {
        'clip': clip, 'container_id': row.container_id, 'split': row.split,
        'role': row.role, 'shape': row['shape'], 'frames': len(frame),
        'requested_retention': retention, 'realized_retention': float(kept.mean()),
        'fixed_development_threshold': threshold, 'fixed_threshold_coverage': float(fixed.mean()),
        'reference_mae_all_cm': float(frame.reference_absolute_error_cm.mean()),
        'reference_mae_retained_cm': float(frame.loc[kept, 'reference_absolute_error_cm'].mean()),
        'reference_mae_fixed_threshold_cm': float(frame.loc[fixed, 'reference_absolute_error_cm'].mean()) if fixed.any() else None,
        'negative_length_fraction': float((frame.length_pred_cm < 0).mean()),
        'reference': 'H * (1 - t / WAV duration); assumed filling, not measured level',
        'interpretation': 'A ranking score, not a probability or guarantee of correct liquid height.',
        'scope': 'Frozen existing recording; offline full-clip analysis; no new validation sample.',
    }
    if row.role == 'shape_diagnostic':
        summary['shape_caution'] = 'Cylinder-style reference disagreement is diagnostic only for this group.'
    output_dir.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_dir / 'frames.csv', index=False)
    (output_dir / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    f, t, power, _ = spectrum
    fig, axes = plt.subplots(3, 1, figsize=(9, 8), layout='constrained')
    axes[0].pcolormesh(t, f, 10 * np.log10(np.maximum(power, 1e-30) / power.max()),
                       shading='auto', cmap='magma', vmin=-60, vmax=0)
    axes[0].plot(frame.time_s, frame.pitch_hz, color='cyan', lw=1.1, label='Frozen model pitch')
    axes[0].set(ylabel='Frequency (Hz)', ylim=(300, 5000), title=f'{clip} | {row.container_id} | {row.role}')
    axes[0].legend(loc='upper left')
    axes[1].plot(frame.time_s, frame.assumed_reference_cm, 'k--', label='Assumed filling reference')
    axes[1].plot(frame.time_s, frame.length_pred_cm, color='#aaa', lw=1, label='All estimates')
    axes[1].scatter(frame.loc[kept, 'time_s'], frame.loc[kept, 'length_pred_cm'], s=4,
                    color='#087e8b', label=f'Retained {100 * kept.mean():.1f}%')
    axes[1].set(ylabel='Air-column length (cm)', title='Retaining a frame does not certify its physical estimate')
    axes[1].legend()
    axes[2].plot(frame.time_s, frame.reliability_score, color='#087e8b', lw=1)
    axes[2].axhline(threshold, color='black', ls='--', label='Frozen development threshold')
    axes[2].set(xlabel='Time from WAV start (s)', ylabel='Reliability ranking score',
                title='Higher score means higher rank; this is not a confidence probability')
    axes[2].legend()
    fig.savefig(output_dir / 'diagnostic.png', dpi=160)
    plt.close(fig)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--clip', default='clip_22')
    parser.add_argument('--retention', type=float, default=0.7)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--list', action='store_true', help='List the fixed recordings; no audio needed.')
    args = parser.parse_args()
    if args.list:
        data = pd.read_csv(ROOT / 'reference/recording_manifest.csv')
        print(data[['clip', 'container_id', 'role', 'shape']].to_string(index=False))
        return
    try:
        output = args.output_dir or ROOT / 'outputs/demo' / args.clip
        result = inspect_recording(args.clip, args.retention, output)
    except (ValueError, FileNotFoundError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))
    print(f'Outputs: {output.resolve()}')


if __name__ == '__main__':
    main()
