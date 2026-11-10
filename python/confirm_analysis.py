"""Pre-registered confirmation analysis (experiments/confirmation_protocol.json).

Applies the frozen reliability score, the development-only retargeted score and
the level decomposition from python/failure_levels.py to 33 recordings from 11
containers never used in this project. Tests H1-H4 once at the container level
(one-sided exact tests, Holm-adjusted) and reports D1-D4. Nothing is refitted on
the confirmation data.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import wavfile
from scipy.stats import spearmanr

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from reproduce_analysis import features, score
from failure_levels import decompose, fit_ridge, holm, select

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'experiments/confirmation'
PROTOCOL = ROOT/'experiments/confirmation_protocol.json'
SEED = 5305


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def one_sided_sign_flip(d: np.ndarray, direction: str) -> float:
    """Exact one-sided p for the mean of d; direction 'less' or 'greater'."""
    d = np.asarray(d, float)
    obs = d.mean()
    null = np.array([np.mean(d*np.array(s)) for s in itertools.product([1, -1], repeat=len(d))])
    return float(np.mean(null <= obs + 1e-12) if direction == 'less' else np.mean(null >= obs - 1e-12))


def permutation_less(values: np.ndarray, is_a: np.ndarray) -> float:
    """Exact one-sided p that mean(values[a]) - mean(values[b]) is this small."""
    values, is_a = np.asarray(values, float), np.asarray(is_a, bool)
    obs = values[is_a].mean() - values[~is_a].mean()
    n, k = len(values), int(is_a.sum())
    null = []
    for idx in itertools.combinations(range(n), k):
        mask = np.zeros(n, bool)
        mask[list(idx)] = True
        null.append(values[mask].mean() - values[~mask].mean())
    return float(np.mean(np.array(null) <= obs + 1e-12))


def boot_ci(d: np.ndarray) -> tuple[float, float]:
    rng = np.random.default_rng(SEED)
    b = np.asarray(d)[rng.integers(0, len(d), (2000, len(d)))].mean(1)
    return float(np.quantile(b, .025)), float(np.quantile(b, .975))


def frozen_params():
    c = pd.read_csv(ROOT/'results/score_coefficients.csv')
    return c['mean'].to_numpy()[1:], c.sd.to_numpy()[1:], c.coefficient.to_numpy()


def retargeted_scorer():
    dev = pd.read_csv(ROOT/'results/frame_features.csv')
    dev = dev[dev.role == 'development'].sort_values(['clip', 'time_s'], kind='stable').reset_index(drop=True)
    fast = pd.concat([decompose(g).fast for _, g in dev.groupby('clip', sort=False)])
    dev['abs_fast_cm'] = fast.abs().to_numpy()
    return fit_ridge(dev, np.log1p(dev.abs_fast_cm.to_numpy()))


def frames_for(r, audio_row) -> pd.DataFrame:
    fs, x = wavfile.read(ROOT/r.audio_file)
    x = x.astype(float)
    x -= x.mean()
    pred = pd.read_csv(ROOT/'reference/confirmation_predictions'/f'{r.clip}.csv')
    pp, _ = features(x, pred)
    pp['clip'], pp['container_id'], pp['shape'] = r.clip, r.container_id, r.shape
    pp['role'] = 'confirmation'
    pp['fill_fraction_reference'] = pp.time_s/(len(x)/fs)
    return pp.sort_values('time_s', kind='stable').reset_index(drop=True)


def recording_metrics(g: pd.DataFrame) -> dict:
    c = decompose(g)
    g = g.assign(abs_fast_cm=c.fast.abs().to_numpy())
    total = float(np.mean(c.e**2))
    L, P = g.length_ref_cm.to_numpy(), g.length_pred_cm.to_numpy()
    return dict(
        frames=len(g), mae_cm=float(g.abs_error_cm.mean()),
        time_only_70=select(g, 'time_only', .7, 'abs_error_cm'),
        combined_70=select(g, 'combined', .7, 'abs_error_cm'),
        fast_none=float(g.abs_fast_cm.mean()),
        fast_stratified_frozen_70=select(g, 'time_stratified_combined', .7, 'abs_fast_cm'),
        fast_stratified_retargeted_70=select(g, 'time_stratified_retargeted', .7, 'abs_fast_cm'),
        k=float(L @ P/(L @ L)),
        offset_rate_share=float((np.mean(c.offset**2) + np.mean(c.rate**2))/total),
        frame_share=float(np.mean(c.fast**2)/total))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = pd.read_csv(ROOT/'reference/confirmation_manifest.csv')
    audio = pd.read_csv(ROOT/'reference/confirmation_audio.csv').set_index('clip')
    params, retarget = frozen_params(), retargeted_scorer()
    rec = []
    for r in manifest.itertuples():
        if not bool(audio.loc[r.clip, 'included']):
            continue
        g = frames_for(r, audio.loc[r.clip])
        g['reliability_score'] = score(g, params)
        g['retargeted_score'] = retarget(g)
        rec.append(dict(clip=r.clip, container_id=r.container_id, shape=r.shape,
                        taper_ratio=r.radius_top_cm/r.radius_bottom_cm, height_cm=r.height_cm, **recording_metrics(g)))
    rec = pd.DataFrame(rec)
    rec.to_csv(OUT/'recording_metrics.csv', index=False)
    num = [c for c in rec.columns if c not in ('clip', 'container_id', 'shape')]
    con = rec.groupby(['container_id', 'shape'], sort=False)[num].mean().reset_index()
    con.insert(2, 'recordings', rec.groupby('container_id', sort=False).size().to_numpy())
    con.to_csv(OUT/'container_metrics.csv', index=False)

    semi = (con['shape'] == 'semiconical').to_numpy()
    tests = []
    for name, d, direction, label in [
            ('H1_fill_position', (con.time_only_70 - con.combined_70).to_numpy(), 'less', 'time only minus frozen score, total |e| MAE (cm)'),
            ('H2_frame_level', (con.fast_stratified_frozen_70 - con.fast_none).to_numpy(), 'greater', 'frozen score within time bins minus no selection, |fast| MAE (cm)'),
            ('H3_gain', (con.k - 1).to_numpy(), 'less', 'k minus 1')]:
        lo, hi = boot_ci(d)
        tests.append(dict(hypothesis=name, quantity=label, predicted=direction, containers=len(d), estimate=float(d.mean()),
                          ci_low=lo, ci_high=hi, in_predicted_direction=int((d < 0).sum() if direction == 'less' else (d > 0).sum()),
                          exact_p_one_sided=one_sided_sign_flip(d, direction), null_size=2**len(d)))
    diff = con.k[semi].mean() - con.k[~semi].mean()
    tests.append(dict(hypothesis='H4_geometry', quantity='mean k semiconical minus cylindrical', predicted='less',
                      containers=len(con), estimate=float(diff), ci_low=np.nan, ci_high=np.nan,
                      in_predicted_direction=int(diff < 0), exact_p_one_sided=permutation_less(con.k.to_numpy(), semi),
                      null_size=int(len(list(itertools.combinations(range(len(con)), int(semi.sum())))))))
    tests = pd.DataFrame(tests)
    tests['holm_p'] = holm(tests.exact_p_one_sided.tolist())
    tests['confirmed'] = (tests.holm_p < .05) & (np.sign(tests.estimate) == np.where(tests.predicted == 'less', -1, 1))
    tests.to_csv(OUT/'primary_tests.csv', index=False)

    d2 = (con.fast_stratified_retargeted_70 - con.fast_none).to_numpy()
    d4 = (con.combined_70 - con.mae_cm).to_numpy()
    lo4, hi4 = boot_ci(d4)
    from failure_levels import exact_sign_flip
    desc = dict(
        D1_levels=dict(offset_rate_share=float(con.offset_rate_share.mean()), frame_share=float(con.frame_share.mean()),
                       expectation_met=bool(con.offset_rate_share.mean() > .5 and con.frame_share.mean() < .1)),
        D2_retargeted=dict(estimate_cm=float(d2.mean()), improved_containers=int((d2 < 0).sum()),
                           exact_p_one_sided=one_sided_sign_flip(d2, 'less'), expectation_met=bool(d2.mean() < 0)),
        D3_taper=dict(spearman=float(spearmanr(con.taper_ratio, con.k).statistic), expectation_met=bool(spearmanr(con.taper_ratio, con.k).statistic < 0)),
        D4_original_claim=dict(estimate_cm=float(d4.mean()), ci_low=lo4, ci_high=hi4, improved_containers=int((d4 < 0).sum()),
                               exact_p_two_sided=exact_sign_flip(d4)))
    status = dict(status='computed', protocol_sha256=digest(PROTOCOL), script_sha256=digest(Path(__file__)),
                  manifest_sha256=digest(ROOT/'reference/confirmation_manifest.csv'),
                  recordings_included=int(len(rec)), containers=int(len(con)), descriptive=desc,
                  reference='Assumption-derived linear filling reference; no new labels.')
    (OUT/'status.json').write_text(json.dumps(status, indent=2) + '\n')
    plot(con, tests)
    pd.set_option('display.width', 220)
    print(tests.round(4).to_string(index=False))
    print(json.dumps(desc, indent=2))


def plot(con, tests):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'svg.fonttype': 'none',
                         'svg.hashsalt': 'elec5305-confirmation', 'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(1, 4, figsize=(15, 4.2), layout='constrained')
    col = np.where(con['shape'] == 'semiconical', '#bc7028', '#176b73')
    t = tests.set_index('hypothesis')
    def lab(h):
        r = t.loc[h]
        return f"Holm p = {r.holm_p:.3g} · {'confirmed' if r.confirmed else 'not confirmed'}"
    for ax, a, b, ttl, h in [(axes[0], 'combined_70', 'time_only_70', 'H1: total |e| MAE at 70%', 'H1_fill_position'),
                             (axes[1], 'fast_none', 'fast_stratified_frozen_70', 'H2: frame-level |fast| MAE', 'H2_frame_level')]:
        for i in range(len(con)):
            ax.plot([0, 1], [con[a].iloc[i], con[b].iloc[i]], color=col[i], alpha=.8, marker='o', ms=4)
        ax.set_xticks([0, 1], ['Acoustic score', 'Time only'] if h == 'H1_fill_position' else ['No selection', 'Score within\ntime bins'])
        ax.set(title=f'{ttl}\n{lab(h)}', ylabel='cm (container mean)', xlim=(-.3, 1.3))
        ax.grid(axis='y', alpha=.2)
    ax = axes[2]
    ax.scatter(np.arange(len(con)), con.k, c=col, s=36, zorder=3)
    ax.axhline(1, color='k', ls='--', lw=.8)
    ax.set_xticks(np.arange(len(con)), [c.replace('container_', 'c') for c in con.container_id], rotation=60, fontsize=8)
    ax.set(title=f'H3: gain k per container\n{lab("H3_gain")}', ylabel='k (predicted = k x reference)')
    ax.grid(axis='y', alpha=.2)
    ax = axes[3]
    for j, (shape, c) in enumerate([('cylindrical', '#176b73'), ('semiconical', '#bc7028')]):
        v = con.k[con['shape'] == shape]
        ax.scatter(np.full(len(v), j) + np.linspace(-.12, .12, len(v)), v, color=c, s=36, zorder=3)
        ax.hlines(v.mean(), j - .25, j + .25, color='k', lw=1.5)
    ax.set_xticks([0, 1], ['Cylindrical', 'Semiconical'])
    ax.set(title=f'H4: k by official shape\n{lab("H4_geometry")}', ylabel='k (container mean)', xlim=(-.6, 1.6))
    ax.grid(axis='y', alpha=.2)
    fig.suptitle('Pre-registered confirmation on 11 containers never used in this project (teal = cylindrical, orange = semiconical)', fontsize=12)
    (OUT/'figures').mkdir(parents=True, exist_ok=True)
    path = OUT/'figures/confirmation_overview.svg'
    fig.savefig(path, metadata={'Date': None})
    path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines()) + '\n')
    png = ROOT/'outputs/confirmation'
    png.mkdir(parents=True, exist_ok=True)
    fig.savefig(png/'confirmation_overview.png', dpi=155)
    plt.close(fig)


if __name__ == '__main__':
    main()
