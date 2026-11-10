"""What makes the estimate work and fail at different levels.

Post-hoc explanatory experiments fixed in experiments/failure_levels_protocol.json:
  E1  split each recording's signed error into recording offset, trajectory
      rate, slow deviation and frame-level fluctuation;
  E2  test what the acoustic features actually predict once fill position is
      controlled (time-only and time-stratified baselines, paired exact tests);
  E3  use the author-confirmed video labels to separate reference-assumption
      error from model error by pour phase;
  E4  repeat the frame-level analysis with 20, 40 and 80 ms STFT windows.

Requires setup (results/frame_features.csv and data/*.wav). Errors remain
relative to the assumption-derived reference; no new labels are created.
"""
from __future__ import annotations

import itertools
import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import wavfile
from scipy.stats import spearmanr

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from reproduce_analysis import FEAT, features

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'experiments/failure_levels'
FIG = OUT/'figures'
PROTOCOL = ROOT/'experiments/failure_levels_protocol.json'
ROLES = ['development', 'seen_test', 'unseen_test', 'shape_diagnostic']
LABEL = {'development': 'Development', 'seen_test': 'Test I (7/8 dev. containers)',
         'unseen_test': 'Test II (new containers)', 'shape_diagnostic': 'Shape diagnostics'}
SHORT = {'development': 'Development', 'seen_test': 'Test I', 'unseen_test': 'Test II',
         'shape_diagnostic': 'Shape diag.'}
LEVELS = ['recording_offset', 'trajectory_rate', 'slow_deviation', 'frame_fluctuation']
LEVEL_LABEL = {'recording_offset': 'Recording offset', 'trajectory_rate': 'Trajectory rate',
               'slow_deviation': 'Slow deviation (>1 s)', 'frame_fluctuation': 'Frame-level fluctuation'}
COLORS = {'recording_offset': '#b44e40', 'trajectory_rate': '#bc7028',
          'slow_deviation': '#7b6c9b', 'frame_fluctuation': '#176b73'}
SLOW_FRAMES = 51          # 1.0 s at the 20 ms prediction spacing
BINS = 10
SEED = 5305
C_CM_S = 34000.0


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------- E1
def decompose(g: pd.DataFrame) -> pd.DataFrame:
    """Return per-frame components; columns sum to the signed error."""
    e = (g.length_pred_cm - g.length_ref_cm).to_numpy()
    q = g.fill_fraction_reference.to_numpy()
    qc = q - q.mean()
    b1 = float(qc @ (e - e.mean()) / (qc @ qc))
    b0 = float(e.mean())
    u = e - b0 - b1*qc
    slow = pd.Series(u).rolling(SLOW_FRAMES, center=True, min_periods=1).mean().to_numpy()
    fast = u - slow
    return pd.DataFrame({'e': e, 'q': q, 'offset': b0, 'rate': b1*qc, 'slow': slow, 'fast': fast},
                        index=g.index)


def level_table(frames: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    comp, rows = [], []
    for clip, g in frames.groupby('clip', sort=False):
        c = decompose(g)
        comp.append(c)
        total = float(np.mean(c.e**2))
        ms = {'recording_offset': float(np.mean(c.offset**2)), 'trajectory_rate': float(np.mean(c.rate**2)),
              'slow_deviation': float(np.mean(c.slow**2)), 'frame_fluctuation': float(np.mean(c.fast**2))}
        row = dict(clip=clip, role=g.role.iloc[0], container_id=g.container_id.iloc[0], frames=len(g),
                   mae_cm=float(np.mean(np.abs(c.e))), rmse_cm=np.sqrt(total),
                   offset_cm=float(c.offset.iloc[0]), rate_cm_per_fill=float((c.rate/(c.q-c.q.mean())).dropna().iloc[0]),
                   cross_term_share=float(2*np.mean(c.slow*c.fast)/total))
        for k, v in ms.items():
            row[f'{k}_share'] = v/total
            row[f'{k}_rms_cm'] = np.sqrt(v)
        rows.append(row)
    return pd.DataFrame(rows), pd.concat(comp)


def scale_table(frames: pd.DataFrame) -> pd.DataFrame:
    """Secondary, added after E1: fit L_pred = k * L_ref through the origin.

    Endpoint correction forces prediction and reference to zero at the final
    frame, so a gain (scale) error appears as offset plus rate in E1.
    k is computed against the linear reference and, for every recording,
    against the geometry-adjusted (constant-volume frustum) reference.
    """
    meta = pd.read_csv(ROOT/'reference/recording_manifest.csv').set_index('clip')
    rows = []
    for clip, g in frames.groupby('clip', sort=False):
        P = g.length_pred_cm.to_numpy()
        row = dict(clip=clip, role=g.role.iloc[0], container_id=g.container_id.iloc[0], shape=meta.loc[clip, 'shape'],
                   material=meta.loc[clip, 'material'], height_cm=meta.loc[clip, 'height_cm'],
                   radius_cm=meta.loc[clip, 'radius_cm'])
        for name, col in [('linear', 'length_ref_cm'), ('geometry', 'length_geometry_proxy_cm')]:
            L = g[col].to_numpy()
            k = float(L @ P/(L @ L))
            row[f'k_{name}'] = k
            row[f'scale_explained_{name}'] = 1 - np.mean((P-k*L)**2)/np.mean((P-L)**2)
        rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- statistics
def exact_sign_flip(d: np.ndarray) -> float:
    d = np.asarray(d, float)
    obs = abs(d.mean())
    null = [abs(np.mean(d*np.array(s))) for s in itertools.product([1, -1], repeat=len(d))]
    return float(np.mean(np.array(null) >= obs - 1e-12))


def bootstrap_ci(d: np.ndarray, seed: int = SEED) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), (2000, len(d)))
    boot = np.asarray(d)[idx].mean(axis=1)
    return float(np.quantile(boot, .025)), float(np.quantile(boot, .975))


def holm(p: list[float]) -> list[float]:
    order = np.argsort(p)
    adj = np.empty(len(p))
    running = 0.
    for rank, i in enumerate(order):
        running = max(running, (len(p)-rank)*p[i])
        adj[i] = min(1., running)
    return adj.tolist()


def partial_spearman(x, y, z) -> float:
    rx, ry, rz = (pd.Series(v).rank().to_numpy() for v in (x, y, z))
    def resid(a):
        A = np.c_[np.ones_like(rz), rz]
        return a - A @ np.linalg.lstsq(A, a, rcond=None)[0]
    ex, ey = resid(rx), resid(ry)
    den = np.sqrt((ex @ ex)*(ey @ ey))
    return float(ex @ ey/den) if den > 0 else np.nan


# ---------------------------------------------------------------- E2
def select(g: pd.DataFrame, method: str, cov: float, target: str, score: str = 'reliability_score') -> float:
    y = g[target].to_numpy()
    n = len(g)
    if method == 'no_selection' or cov >= 1:
        return float(y.mean())
    if method == 'combined':
        ix = np.argsort(-g[score].to_numpy(), kind='stable')[:int(np.ceil(cov*n))]
    elif method == 'time_only':
        ix = np.argsort(-g.time_s.to_numpy(), kind='stable')[:int(np.ceil(cov*n))]
    elif method == 'oracle':
        ix = np.argsort(y, kind='stable')[:int(np.ceil(cov*n))]
    elif method in ('time_stratified_combined', 'time_stratified_retargeted'):
        col = score if method == 'time_stratified_combined' else 'retargeted_score'
        b = np.minimum((g.fill_fraction_reference.to_numpy()*BINS).astype(int), BINS-1)
        s = g[col].to_numpy()
        ix = []
        for k in range(BINS):
            members = np.where(b == k)[0]
            if len(members):
                keep = int(np.ceil(cov*len(members)))
                ix.extend(members[np.argsort(-s[members], kind='stable')[:keep]])
        ix = np.asarray(ix)
    else:
        raise ValueError(method)
    return float(y[ix].mean())


def fit_ridge(d: pd.DataFrame, target: np.ndarray, cols=FEAT, lam=.1):
    X = d[cols].to_numpy()
    w = 1/d.groupby('clip').clip.transform('size').to_numpy()
    w = w/w.sum()
    mu = (w[:, None]*X).sum(0)
    sd = np.maximum(np.sqrt((w[:, None]*(X-mu)**2).sum(0)), 1e-8)
    Z = np.c_[np.ones(len(X)), (X-mu)/sd]
    beta = np.linalg.solve(Z.T @ (w[:, None]*Z) + np.diag([0]+[lam]*len(cols)), Z.T @ (w*target))
    return lambda e: -(np.c_[np.ones(len(e)), (e[cols].to_numpy()-mu)/sd] @ beta)


def selection_tables(frames: pd.DataFrame):
    methods = ['no_selection', 'combined', 'time_only', 'time_stratified_combined',
               'time_stratified_retargeted', 'oracle']
    rows = []
    for role in ['seen_test', 'unseen_test']:
        for clip, g in frames[frames.role == role].groupby('clip', sort=False):
            for target in ['abs_error_cm', 'abs_fast_cm']:
                for cov in [1., .9, .8, .7]:
                    for m in methods:
                        rows.append(dict(clip=clip, role=role, container_id=g.container_id.iloc[0],
                                         target=target, coverage=cov, method=m, mae_cm=select(g, m, cov, target)))
    by_clip = pd.DataFrame(rows)
    summary = (by_clip.groupby(['role', 'target', 'coverage', 'method'], sort=False).mae_cm.mean()
               .rename('mean_mae_cm').reset_index())
    primary = [('seen_test', 'abs_error_cm', 'time_only', 'combined'),
               ('unseen_test', 'abs_error_cm', 'time_only', 'combined'),
               ('seen_test', 'abs_fast_cm', 'time_stratified_combined', 'no_selection'),
               ('unseen_test', 'abs_fast_cm', 'time_stratified_combined', 'no_selection')]
    tests = []
    for role, target, a, b in primary:
        z = by_clip[(by_clip.role == role) & (by_clip.target == target) & (by_clip.coverage == .7)]
        A = z[z.method == a].set_index('clip').mae_cm
        B = z[z.method == b].set_index('clip').mae_cm.loc[A.index]
        d = (A-B).to_numpy()
        lo, hi = bootstrap_ci(d)
        tests.append(dict(role=role, target=target, comparison=f'{a} minus {b}', coverage=.7,
                          mean_a_cm=A.mean(), mean_b_cm=B.mean(), delta_cm=d.mean(), ci_low=lo, ci_high=hi,
                          improved=int((d < 0).sum()), worsened=int((d > 0).sum()),
                          exact_p=exact_sign_flip(d), sign_patterns=2**len(d)))
    tests = pd.DataFrame(tests)
    tests['holm_p'] = holm(tests.exact_p.tolist())
    return by_clip, summary, tests


def correlation_table(frames: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for clip, g in frames.groupby('clip', sort=False):
        for var in FEAT + ['reliability_score']:
            for target in ['abs_error_cm', 'abs_fast_cm']:
                rows.append(dict(clip=clip, role=g.role.iloc[0], variable=var, target=target,
                                 raw_spearman=spearmanr(g[var], g[target]).statistic,
                                 partial_spearman=partial_spearman(g[var], g[target], g.fill_fraction_reference)))
        rows.append(dict(clip=clip, role=g.role.iloc[0], variable='fill_position', target='abs_error_cm',
                         raw_spearman=spearmanr(g.fill_fraction_reference, g.abs_error_cm).statistic,
                         partial_spearman=np.nan))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- E3
def visual_table() -> tuple[pd.DataFrame, pd.DataFrame]:
    v = pd.read_csv(ROOT/'experiments/results/visual_by_frame.csv')
    v = v[(v.status != 'excluded') & (v.human_review_status == 'author_confirmed_water_band')].copy()
    v['phase'] = np.select([v.fraction <= .3, v.fraction >= .7], ['early', 'late'], 'middle')
    v['reference_gap_pp'] = 100*(v.visual_fraction_midpoint - v.assumed_fraction)
    v['model_gap_pp'] = 100*(v.audio_model_fraction - v.visual_fraction_midpoint)
    v['reference_outside_interval'] = (v.assumed_fraction < v.visual_fraction_lower) | (v.assumed_fraction > v.visual_fraction_upper)
    v['model_outside_interval'] = (v.audio_model_fraction < v.visual_fraction_lower) | (v.audio_model_fraction > v.visual_fraction_upper)
    per = v.groupby(['clip', 'phase']).agg(labels=('frame', 'size'), reference_gap_pp=('reference_gap_pp', 'mean'),
                                          model_gap_pp=('model_gap_pp', 'mean')).reset_index()
    rows = []
    for phase in ['early', 'middle', 'late']:
        p = per[per.phase == phase]
        w = v[v.phase == phase]
        rows.append(dict(phase=phase, recordings=len(p), labels=int(p.labels.sum()),
                         reference_gap_pp=p.reference_gap_pp.mean(), model_gap_pp=p.model_gap_pp.mean(),
                         recordings_reference_gap_positive=int((p.reference_gap_pp > 0).sum()),
                         recordings_model_gap_positive=int((p.model_gap_pp > 0).sum()),
                         reference_outside_visual_interval=int(w.reference_outside_interval.sum()),
                         model_outside_visual_interval=int(w.model_outside_interval.sum())))
    return pd.DataFrame(rows), per


# ---------------------------------------------------------------- E4
def window_table(frames: pd.DataFrame, comp: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    meta = pd.read_csv(ROOT/'reference/recording_manifest.csv')
    meta = meta[meta.role.isin(['development', 'seen_test', 'unseen_test'])]
    base = frames[['clip', 'time_s', 'fill_fraction_reference', 'abs_fast_cm', 'abs_error_cm']]
    tables = {}
    for M in [320, 640, 1280]:
        parts = []
        for r in meta.itertuples():
            fs, x = wavfile.read(ROOT/r.audio_file)
            x = x.astype(float)
            x -= x.mean()
            pred = pd.read_csv(ROOT/'reference/model_predictions'/f'{r.clip}.csv')
            pp, _ = features(x, pred, M=M)
            pp['clip'], pp['role'], pp['container_id'] = r.clip, r.role, r.container_id
            parts.append(pp)
        tables[M] = pd.concat(parts, ignore_index=True)
    common = None
    for M, t in tables.items():
        keys = set(zip(t['clip'], np.round(t.time_s, 6)))
        common = keys if common is None else common & keys
    rows, sel = [], []
    for M, t in tables.items():
        t = t[[k in common for k in zip(t['clip'], np.round(t.time_s, 6))]].copy()
        t['tkey'] = t.time_s.round(6)
        b = base.assign(tkey=base.time_s.round(6)).drop(columns=['time_s'])
        t = t.drop(columns=['abs_error_cm']).merge(b, on=['clip', 'tkey'], how='inner', validate='one_to_one')
        dev = t[t.role == 'development']
        t['window_score'] = fit_ridge(dev, np.log1p(dev.abs_error_cm.to_numpy()))(t)
        t['reliability_score'] = t['window_score']
        for clip, g in t.groupby('clip', sort=False):
            for var in ['prom_db', 'competition', 'model_support_db', 'window_score']:
                rows.append(dict(window_samples=M, window_ms=1000*M/16000, mainlobe_hz=2*16000/M, clip=clip,
                                 role=g.role.iloc[0], variable=var,
                                 partial_spearman_fast=partial_spearman(g[var], g.abs_fast_cm, g.fill_fraction_reference)))
            if g.role.iloc[0] in ('seen_test', 'unseen_test'):
                full = g.abs_fast_cm.mean()
                strat = select(g, 'time_stratified_combined', .7, 'abs_fast_cm', score='window_score')
                sel.append(dict(window_samples=M, window_ms=1000*M/16000, clip=clip, role=g.role.iloc[0],
                                frames=len(g), full_fast_mae_cm=full, stratified_fast_mae_cm=strat, delta_cm=strat-full))
    return pd.DataFrame(rows), pd.DataFrame(sel)


# ---------------------------------------------------------------- figures
def style():
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'svg.fonttype': 'none',
                         'svg.hashsalt': 'elec5305-failure-levels', 'axes.spines.top': False,
                         'axes.spines.right': False})


def save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    path = FIG/f'{name}.svg'
    fig.savefig(path, metadata={'Date': None})
    path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
    png = ROOT/'outputs/failure_levels'
    png.mkdir(parents=True, exist_ok=True)
    fig.savefig(png/f'{name}.png', dpi=155)
    plt.close(fig)


def plot_levels(levels, comp, frames):
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6), layout='constrained', gridspec_kw={'width_ratios': [1.35, 1]})
    clip = 'clip_22'
    g = frames[frames['clip'] == clip]
    c = comp.loc[g.index]
    ax = axes[0]
    ax.plot(g.time_s, c.e, color='#9aa4a8', lw=.8, label='Signed error (model - reference)')
    ax.plot(g.time_s, c.offset + c.rate, color=COLORS['trajectory_rate'], lw=1.8, label='Offset + rate (linear trend)')
    ax.plot(g.time_s, c.offset + c.rate + c.slow, color=COLORS['slow_deviation'], lw=1.2, label='+ slow deviation (1 s mean)')
    ax.axhline(0, color='k', lw=.6)
    ax.set(xlabel='Time (s)', ylabel='Air-column error (cm)',
           title=f'{clip} (Test II, cylindrical): error is mostly a smooth trend')
    ax.legend(fontsize=8, loc='lower right')
    ax.grid(alpha=.2)
    ax = axes[1]
    groups = [r for r in ROLES if r in set(levels.role)]
    bottom = np.zeros(len(groups))
    for k in LEVELS:
        vals = np.array([levels[levels.role == r][f'{k}_share'].mean() for r in groups])
        ax.bar([SHORT[r] for r in groups], vals, bottom=bottom, color=COLORS[k], label=LEVEL_LABEL[k])
        for i, v in enumerate(vals):
            if v > .06:
                ax.text(i, bottom[i]+v/2, f'{100*v:.0f}%', ha='center', va='center', color='white', fontsize=8.5)
        bottom += vals
    ax.set(ylabel='Share of mean-square error', ylim=(0, 1.05), title='Where the error lives (equal-recording means)')
    ax.legend(fontsize=8, loc='upper center', bbox_to_anchor=(.5, -.12), ncol=2)
    fig.suptitle('E1. Splitting each recording\'s error into levels', fontsize=12)
    save(fig, 'error_levels')


def plot_selection(summary, tests):
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.4), layout='constrained')
    spec = [('abs_error_cm', ['no_selection', 'combined', 'time_only', 'oracle'], 'Total error |e|: what the original score improves'),
            ('abs_fast_cm', ['no_selection', 'time_stratified_combined', 'time_stratified_retargeted', 'oracle'],
             'Frame-level error |fast|: what acoustics alone can see')]
    names = {'no_selection': 'No selection', 'combined': 'Acoustic score', 'time_only': 'Time only (drop earliest)',
             'time_stratified_combined': 'Acoustic score within time bins', 'time_stratified_retargeted': 'Retargeted score within bins',
             'oracle': 'Error oracle'}
    cols = {'no_selection': '#7b8589', 'combined': '#176b73', 'time_only': '#bc7028', 'time_stratified_combined': '#176b73',
            'time_stratified_retargeted': '#3f9aa3', 'oracle': '#64835c'}
    for ax, (target, methods, title) in zip(axes, spec):
        x = np.arange(2)
        w = .8/len(methods)
        for i, m in enumerate(methods):
            vals = [summary[(summary.role == r) & (summary.target == target) & (summary.coverage == (1. if m == 'no_selection' else .7))
                            & (summary.method == m)].mean_mae_cm.iloc[0] for r in ['seen_test', 'unseen_test']]
            ax.bar(x+(i-(len(methods)-1)/2)*w, vals, w*.92, color=cols[m], alpha=.55 if 'retargeted' in m else 1,
                   hatch='//' if m == 'oracle' else None, edgecolor='white', label=names[m])
            for xi, v in zip(x+(i-(len(methods)-1)/2)*w, vals):
                ax.text(xi, v, f'{v:.2f}', ha='center', va='bottom', fontsize=7.5)
        ax.set_xticks(x, ['Test I', 'Test II'])
        ax.set(ylabel='Mean absolute error (cm), 70% retained', title=title)
        ax.legend(fontsize=7.5, loc='upper left')
        ax.grid(axis='y', alpha=.2)
    fig.suptitle('E2. Controlling for fill position changes what the acoustic score appears to do', fontsize=12)
    save(fig, 'selection_by_level')


def plot_visual(vis, per):
    fig, ax = plt.subplots(figsize=(8.6, 4.3), layout='constrained')
    phases = ['early', 'middle', 'late']
    x = np.arange(3)
    for off, col, key, lab in [(-.15, '#7b6c9b', 'reference_gap_pp', 'Visible water minus linear reference'),
                               (.15, '#b44e40', 'model_gap_pp', 'Model minus visible water')]:
        ax.bar(x+off, [vis[vis.phase == p][key].iloc[0] for p in phases], .28, color=col, alpha=.75, label=lab)
        for i, p in enumerate(phases):
            pts = per[per.phase == p][key]
            ax.scatter(np.full(len(pts), i+off), pts, color=col, s=16, zorder=3, edgecolor='#222222', lw=.5)
    ax.axhline(0, color='k', lw=.7)
    ax.set_xticks(x, ['Early (10-30%)', 'Middle (40-60%)', 'Late (70-90%)'])
    ax.set(ylabel='Fill-fraction difference (percentage points)',
           title='E3. Early error: part reference assumption, most of it model (6 Test I recordings)')
    ax.legend(fontsize=8)
    ax.grid(axis='y', alpha=.2)
    save(fig, 'reference_or_model')


def plot_scale(scale):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), layout='constrained')
    roles = ['development', 'seen_test', 'unseen_test', 'shape_diagnostic']
    marks = {'cylindrical': 'o', 'semiconical': '^', 'bottleneck': 's'}
    cols = {'cylindrical': '#176b73', 'semiconical': '#bc7028', 'bottleneck': '#7b6c9b'}
    rng = np.random.default_rng(SEED)
    for ax, ref, title in [(axes[0], 'linear', 'Against the linear reference'),
                           (axes[1], 'geometry', 'Against the geometry-adjusted reference')]:
        for i, role in enumerate(roles):
            z = scale[scale.role == role]
            for shape, g in z.groupby('shape'):
                ax.scatter(i + rng.uniform(-.18, .18, len(g)), g[f'k_{ref}'], marker=marks.get(shape, 'x'),
                           color=cols.get(shape, 'k'), s=30, label=shape if i == 0 or role == 'shape_diagnostic' else None)
        ax.axhline(1, color='k', lw=.8, ls='--')
        ax.set_xticks(range(len(roles)), [SHORT[r] for r in roles])
        ax.set(ylabel='Scale factor k (predicted = k x reference)', title=title, ylim=(-.6, 1.4))
        ax.grid(axis='y', alpha=.2)
        handles, labels = ax.get_legend_handles_labels()
        uniq = dict(zip(labels, handles))
        ax.legend(uniq.values(), uniq.keys(), fontsize=8, loc='lower left')
    fig.suptitle('Secondary (added after E1): the model under-scales the air column; k = 1 means no gain error', fontsize=12)
    save(fig, 'scale_factor')


def plot_window(wcorr, wsel):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), layout='constrained')
    ms = [20, 40, 80]
    xs = np.arange(3)
    ax = axes[0]
    for var, col, lab in [('prom_db', '#bc7028', 'Prominence'), ('competition', '#7b6c9b', 'Competing-peak ratio'),
                          ('window_score', '#176b73', 'Score (higher = called reliable)')]:
        for role, mk, ls in [('seen_test', 'o', '-'), ('unseen_test', '^', '--')]:
            vals = [wcorr[(wcorr.window_ms == m) & (wcorr.variable == var) & (wcorr.role == role)].partial_spearman_fast.median() for m in ms]
            ax.plot(xs, vals, ls, marker=mk, color=col, label=f'{lab}, {SHORT[role]}')
    ax.axhline(0, color='k', lw=.6)
    ax.set_xticks(xs, ['20 ms\n(200 Hz main lobe)', '40 ms\n(100 Hz)', '80 ms\n(50 Hz)'])
    ax.set(ylabel='Median partial Spearman with |fast|\n(fill position held fixed)',
           title='Positive = higher value goes with larger frame error')
    ax.legend(fontsize=7, ncol=2, loc='upper center', bbox_to_anchor=(.5, -.2))
    ax.grid(alpha=.2)
    ax = axes[1]
    for role, col in [('seen_test', '#176b73'), ('unseen_test', '#b44e40')]:
        vals = [wsel[(wsel.window_ms == m) & (wsel.role == role)].delta_cm.mean() for m in ms]
        ax.plot(xs, vals, '-o', color=col, label=SHORT[role])
    ax.axhline(0, color='k', lw=.6)
    ax.set_xticks(xs, ['20 ms', '40 ms', '80 ms'])
    ax.set(ylabel='Change in frame-level MAE at 70% (cm)',
           title='Score-based selection within time bins (positive = worse)')
    ax.legend(fontsize=8)
    ax.grid(alpha=.2)
    fig.suptitle('E4. Time-frequency resolution and frame-level reliability', fontsize=12)
    save(fig, 'stft_window')


def main():
    style()
    OUT.mkdir(parents=True, exist_ok=True)
    frames = pd.read_csv(ROOT/'results/frame_features.csv')
    frames = frames.sort_values(['clip', 'time_s'], kind='stable').reset_index(drop=True)
    levels, comp = level_table(frames)
    frames['abs_fast_cm'] = comp.fast.abs().to_numpy()
    dev = frames[frames.role == 'development']
    frames['retargeted_score'] = fit_ridge(dev, np.log1p(dev.abs_fast_cm.to_numpy()))(frames)

    levels.to_csv(OUT/'error_levels_by_clip.csv', index=False)
    share_cols = [f'{k}_share' for k in LEVELS]
    lsum = levels.groupby('role', sort=False)[share_cols + ['cross_term_share', 'mae_cm', 'rmse_cm']].mean().reindex(ROLES)
    lsum.insert(0, 'recordings', levels.groupby('role').size().reindex(ROLES))
    lsum.reset_index().to_csv(OUT/'error_levels_summary.csv', index=False)

    by_clip, summary, tests = selection_tables(frames)
    by_clip.to_csv(OUT/'selection_by_clip.csv', index=False)
    summary.to_csv(OUT/'selection_summary.csv', index=False)
    tests.to_csv(OUT/'primary_tests.csv', index=False)

    corr = correlation_table(frames)
    corr.to_csv(OUT/'correlations_by_clip.csv', index=False)
    csum = (corr.groupby(['role', 'variable', 'target'], sort=False)
            .agg(recordings=('clip', 'size'), median_raw=('raw_spearman', 'median'),
                 median_partial=('partial_spearman', 'median'),
                 negative_partial=('partial_spearman', lambda s: int((s < 0).sum()))).reset_index())
    csum.to_csv(OUT/'correlations_summary.csv', index=False)

    scale = scale_table(frames)
    scale.to_csv(OUT/'scale_factor_by_clip.csv', index=False)
    (scale.groupby(['role', 'shape'], sort=False)
     .agg(recordings=('clip', 'size'), k_linear_median=('k_linear', 'median'), k_geometry_median=('k_geometry', 'median'),
          scale_explained_linear_median=('scale_explained_linear', 'median'))
     .reset_index().to_csv(OUT/'scale_factor_summary.csv', index=False))
    plot_scale(scale)

    vis, per = visual_table()
    vis.to_csv(OUT/'reference_or_model_by_phase.csv', index=False)
    per.to_csv(OUT/'reference_or_model_by_clip.csv', index=False)

    wcorr, wsel = window_table(frames, comp)
    wcorr.to_csv(OUT/'stft_window_correlations.csv', index=False)
    wsel.to_csv(OUT/'stft_window_selection.csv', index=False)

    plot_levels(levels, comp, frames)
    plot_selection(summary, tests)
    plot_visual(vis, per)
    plot_window(wcorr, wsel)

    status = dict(status='computed', protocol_sha256=digest(PROTOCOL), script_sha256=digest(Path(__file__)),
                  frames=len(frames), recordings=int(frames['clip'].nunique()),
                  reference='Assumption-derived linear filling reference; no new labels.',
                  design='Post-hoc explanatory analysis motivated by disclosed exploration; see protocol.')
    (OUT/'status.json').write_text(json.dumps(status, indent=2)+'\n')
    pd.set_option('display.width', 200)
    print(lsum.round(3).to_string())
    print(tests.round(4).to_string(index=False))
    print(vis.round(2).to_string(index=False))
    print(scale.groupby(['role', 'shape']).agg(n=('clip', 'size'), k_lin=('k_linear', 'median'), k_geo=('k_geometry', 'median'), expl=('scale_explained_linear', 'median')).round(3).to_string())
    print(wsel.groupby(['window_ms', 'role']).delta_cm.mean().round(4).to_string())


if __name__ == '__main__':
    main()
