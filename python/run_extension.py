"""Frozen-model robustness and endpoint experiments; baseline files are read-only.

Run --endpoint for the cached, all-recording endpoint comparison.
Run --noise after download_model.py and installation of inference dependencies.
Errors below use the original assumed filling curve, not measured water levels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
from scipy.io import wavfile

from demo_recording import apply_frozen_score, select_frames
from reproduce_analysis import features

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'experiments/results'
PROTOCOL = ROOT / 'experiments/extension_protocol.json'
CHECKPOINT_SHA = '2fa3d8cec1488ee65bb5a6e30f1b79716d8243bbe4ddc4c0687ce2a02c84303c'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def add_noise(x, snr_db, seed):
    """Deterministic, zero-mean noise with declared *additional*-noise SNR."""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 1 or not len(x) or not np.isfinite(x).all():
        raise ValueError('Expected finite mono signal.')
    signal_power = np.mean((x-x.mean())**2)
    if signal_power <= 0 or not np.isfinite(snr_db):
        raise ValueError('SNR requires nonzero signal power and finite target.')
    z = np.random.default_rng(seed).standard_normal(len(x))
    z -= z.mean()
    z *= np.sqrt(signal_power / (np.mean(z*z) * 10**(snr_db/10)))
    y = (x + z).astype(np.float32)
    actual_noise = y.astype(float)-x
    actual = 10*np.log10(signal_power / np.mean(actual_noise**2))
    return y, float(actual)


def terminal_estimate(times, wavelength, window_s):
    times, wavelength = np.asarray(times), np.asarray(wavelength)
    if len(times) != len(wavelength) or not len(times) or np.any(np.diff(times) <= 0):
        raise ValueError('Ordered, paired nonempty predictions required.')
    if window_s <= 0:
        raise ValueError('Window must be positive.')
    return float(np.median(wavelength[times >= times[-1]-window_s-1e-10]))


def interval(values, seed=20261108):
    a = np.asarray(values, dtype=float)
    a = a[np.isfinite(a)]
    if not len(a):
        return [None, None]
    draws = np.random.default_rng(seed).choice(a, (2000, len(a)), replace=True).mean(axis=1)
    return [float(v) for v in np.quantile(draws, [.025, .975])]


def endpoint():
    protocol = json.loads(PROTOCOL.read_text())
    rows, phases = [], []
    for r in pd.read_csv(ROOT/'reference/recording_manifest.csv').itertuples():
        p = pd.read_csv(ROOT/'reference/model_predictions'/f'{r.clip}.csv')
        lam, t = p.wavelength_cm.to_numpy(), p.time_s.to_numpy()
        ref = r.height_cm*(1-t/r.duration_s)
        baseline = (lam-lam[-1])/4
        for window in [0, .2, *protocol['endpoint']['sensitivity_windows_s']]:
            end = float(lam[-1]) if window == 0 else terminal_estimate(t, lam, window)
            pred = (lam-end)/4
            error = np.abs(pred-ref)
            row = dict(clip=r.clip, container_id=r.container_id, role=r.role,
                       window_s=window, endpoint_wavelength_cm=end,
                       global_shift_cm=(lam[-1]-end)/4,
                       reference_mae_cm=float(error.mean()),
                       reference_bias_cm=float((pred-ref).mean()),
                       delta_mae_cm=float(error.mean()-np.abs(baseline-ref).mean()),
                       negative_length_fraction=float((pred<0).mean()), frames=len(p))
            rows.append(row)
            for i, name in enumerate(['early', 'middle', 'late']):
                mask = (t/r.duration_s >= i/3) & (t/r.duration_s < (i+1)/3)
                phases.append(dict(clip=r.clip, role=r.role, window_s=window, phase=name,
                                   frames=int(mask.sum()), reference_mae_cm=float(error[mask].mean())))
    d = pd.DataFrame(rows)
    d.to_csv(OUT/'endpoint_by_clip.csv', index=False)
    pd.DataFrame(phases).to_csv(OUT/'endpoint_by_phase.csv', index=False)
    summaries = []
    for (role, w), g in d.groupby(['role', 'window_s'], sort=False):
        by_container = g.groupby('container_id')[['reference_mae_cm', 'delta_mae_cm']].mean()
        lo, hi = interval(by_container.delta_mae_cm)
        summaries.append(dict(role=role, window_s=w, recordings=len(g), containers=len(by_container),
                              reference_mae_cm=by_container.reference_mae_cm.mean(),
                              paired_delta_cm=by_container.delta_mae_cm.mean(), ci_low_cm=lo, ci_high_cm=hi,
                              improved=int((g.delta_mae_cm < -1e-8).sum()),
                              worsened=int((g.delta_mae_cm > 1e-8).sum()),
                              unchanged=int((g.delta_mae_cm.abs() <= 1e-8).sum())))
    pd.DataFrame(summaries).to_csv(OUT/'endpoint_summary.csv', index=False)
    print(pd.DataFrame(summaries).to_string(index=False), flush=True)


def infer(model, torch, x):
    z = x.astype(np.float32)
    z = (z-z.mean())/np.sqrt(z.var()+1e-7)
    with torch.inference_mode():
        prob = model(torch.from_numpy(z[None,:]), len(z)/16000)[0]
        lam = (prob@torch.linspace(0,100,64)).numpy()
    t = (np.arange(len(lam))*320+200)/16000
    return pd.DataFrame(dict(time_s=t, wavelength_cm=lam, pitch_hz=34000/lam,
                             length_pred_cm=(lam-lam[-1])/4))


def noise():
    import torch
    import transformers
    import scipy
    from infer_official import InferenceModel
    from transformers import Wav2Vec2Config
    protocol = json.loads(PROTOCOL.read_text())
    cfg = protocol['noise']
    checkpoint = ROOT/'python/checkpoint.pth'
    if sha(checkpoint) != CHECKPOINT_SHA:
        raise ValueError('Checkpoint identity mismatch.')
    torch.set_num_threads(4)
    torch.manual_seed(0)
    model_config = Wav2Vec2Config.from_json_file(str(ROOT/'python/wav2vec2_config.json'))
    model_config._attn_implementation = 'eager'
    model = InferenceModel(model_config)
    state = torch.load(checkpoint, map_location='cpu', weights_only=True)
    model.load_state_dict(state, strict=True)
    model.eval()
    coeff = pd.read_csv(ROOT/'results/score_coefficients.csv')
    threshold = float(pd.read_csv(ROOT/'results/fixed_threshold.csv').threshold.iloc[0])
    manifest = pd.read_csv(ROOT/'reference/recording_manifest.csv')
    manifest = manifest[manifest.role.isin(cfg['roles'])]
    cache = ROOT/'outputs/extension_noise'
    cache.mkdir(parents=True, exist_ok=True)
    identity = dict(protocol_sha256=sha(PROTOCOL), checkpoint_sha256=sha(checkpoint),
                    coefficients_sha256=sha(ROOT/'results/score_coefficients.csv'),
                    manifest_sha256=sha(ROOT/'reference/recording_manifest.csv'),
                    torch=torch.__version__, transformers=transformers.__version__,
                    numpy=np.__version__, scipy=scipy.__version__, strict_checkpoint_keys=len(state))
    identity_path = cache/'identity.json'
    if identity_path.exists() and json.loads(identity_path.read_text()) != identity:
        raise ValueError('Resume cache identity mismatch; use a fresh output directory.')
    identity_path.write_text(json.dumps(identity, indent=2)+'\n')
    rows, phase_rows, clean_audit = [], [], []
    for r in manifest.itertuples():
        source = ROOT/r.audio_file
        if sha(source) != r.analysis_sha256:
            raise ValueError(f'{r.clip}: input SHA mismatch.')
        fs, x = wavfile.read(source)
        if fs != 16000 or x.ndim != 1:
            raise ValueError('Input format mismatch.')
        x = x.astype(np.float32)
        conditions = [('clean', None, None)] + [(f'snr{snr}_seed{seed}', snr, seed)
                      for snr in cfg['snr_db'] for seed in cfg['seeds']]
        clean = None
        for tag, snr, seed in conditions:
            tic = time.time()
            mixed, actual = (x, None) if snr is None else add_noise(x, snr, seed+10000*int(r.clip[-2:]))
            path = cache/f'{r.clip}_{tag}.csv'
            p = pd.read_csv(path) if path.exists() else infer(model, torch, mixed)
            if not path.exists():
                p.to_csv(path, index=False)
            if tag == 'clean':
                clean = p
                old = pd.read_csv(ROOT/'reference/model_predictions'/f'{r.clip}.csv')
                if len(old) != len(p):
                    raise ValueError('Clean output frame count changed.')
                drift = float(np.max(np.abs(old.wavelength_cm-p.wavelength_cm)))
                clean_audit.append(dict(clip=r.clip, frames=len(p), max_wavelength_difference_cm=drift))
                if drift > cfg['clean_cache_max_wavelength_difference_cm']:
                    raise ValueError(f'{r.clip}: clean cache drift {drift}; inspect before noisy evaluation.')
            physical = p[['time_s', 'wavelength_cm', 'pitch_hz', 'length_pred_cm']].copy()
            frames, _ = features(mixed.astype(float)-mixed.astype(float).mean(), physical)
            scores = apply_frozen_score(frames, coeff)
            keep = select_frames(scores, cfg['rank_retention'])
            fixed = scores >= threshold
            ref = r.height_cm*(1-frames.time_s.to_numpy()/r.duration_s)
            error = np.abs(frames.length_pred_cm.to_numpy()-ref)
            lam_delta = p.wavelength_cm.to_numpy()-clean.wavelength_cm.to_numpy()
            common = dict(clip=r.clip, container_id=r.container_id, role=r.role,
                          condition='clean' if snr is None else 'gaussian', snr_db=snr, seed=seed)
            rows.append(dict(**common, achieved_snr_db=actual,
                       input_float32_sha256=hashlib.sha256(mixed.astype('<f4').tobytes()).hexdigest(),
                       frames=len(frames), reference_mae_cm=float(error.mean()),
                       rank70_reference_mae_cm=float(error[keep].mean()), rank70_coverage=float(keep.mean()),
                       fixed_coverage=float(fixed.mean()),
                       fixed_reference_mae_cm=float(error[fixed].mean()) if fixed.any() else None,
                       mean_abs_wavelength_change_cm=float(np.mean(np.abs(lam_delta))),
                       endpoint_global_shift_cm=float(-lam_delta[-1]/4),
                       negative_length_fraction=float((frames.length_pred_cm<0).mean()),
                       score_mean=float(scores.mean())))
            q = frames.time_s.to_numpy()/r.duration_s
            for i, name in enumerate(['early', 'middle', 'late']):
                mask = (q>=i/3)&(q<(i+1)/3)
                chosen = mask & keep
                phase_rows.append(dict(**common, phase=name, frames=int(mask.sum()),
                                  reference_mae_cm=float(error[mask].mean()),
                                  rank70_reference_mae_cm=float(error[chosen].mean()) if chosen.any() else None,
                                  rank70_coverage=float(keep[mask].mean()), fixed_coverage=float(fixed[mask].mean())))
            print(r.clip, tag, 'reference MAE', round(error.mean(),3), 'seconds', round(time.time()-tic,2), flush=True)
        # Checkpoint partial tables after each full recording, never mark them complete.
        pd.DataFrame(rows).to_csv(cache/'partial_trials.csv', index=False)
    d = pd.DataFrame(rows)
    d.to_csv(OUT/'noise_trials.csv', index=False)
    pd.DataFrame(phase_rows).to_csv(OUT/'noise_by_phase.csv', index=False)
    pd.DataFrame(clean_audit).to_csv(OUT/'clean_inference_audit.csv', index=False)
    summaries = []
    clean_rows = d[d.condition=='clean'].set_index('clip')
    metrics = ['reference_mae_cm', 'rank70_reference_mae_cm', 'fixed_coverage',
               'fixed_reference_mae_cm', 'mean_abs_wavelength_change_cm', 'negative_length_fraction']
    for (role, condition, snr), g in d.assign(snr_label=d.snr_db.fillna(999)).groupby(['role','condition','snr_label']):
        a = g.groupby(['clip','container_id'])[metrics].mean().reset_index()
        delta = a.reference_mae_cm.to_numpy()-clean_rows.loc[a['clip'],'reference_mae_cm'].to_numpy()
        by_container = a.assign(delta=delta).groupby('container_id')[metrics+['delta']].mean()
        lo, hi = interval(by_container.delta)
        summaries.append(dict(role=role, condition=condition, snr_db=None if snr==999 else snr,
                              recordings=len(a), containers=len(by_container), trials=len(g),
                              **{name:float(by_container[name].mean()) for name in metrics},
                              paired_change_from_clean_cm=float(by_container.delta.mean()),
                              ci_low_cm=lo, ci_high_cm=hi,
                              recordings_with_fixed_selection=int(a.fixed_reference_mae_cm.notna().sum())))
    pd.DataFrame(summaries).to_csv(OUT/'noise_summary.csv', index=False)
    identity.update(completed=True, recordings=len(manifest), clean_runs=len(clean_audit),
                    noisy_runs=int((d.condition!='clean').sum()), eval_mode=True,
                    source='original recorded audio plus generated noise; clean audio can already contain ambient noise',
                    inference_adapter_sha256=sha(ROOT/'python/infer_official.py'),
                    experiment_script_sha256=sha(Path(__file__)),
                    reference='assumed filling curve; not independently measured level accuracy')
    (OUT/'noise_run.json').write_text(json.dumps(identity,indent=2)+'\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--endpoint', action='store_true')
    p.add_argument('--noise', action='store_true')
    a = p.parse_args()
    if not (a.endpoint or a.noise):
        p.error('Choose --endpoint and/or --noise.')
    OUT.mkdir(parents=True, exist_ok=True)
    if a.endpoint:
        endpoint()
    if a.noise:
        noise()


if __name__ == '__main__':
    main()
