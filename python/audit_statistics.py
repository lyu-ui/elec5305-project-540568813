"""Audit split overlap, exact paired tests, nested LOCO and global selection.

Run after data setup. Historical tables and the frozen score are not replaced.
"""
from pathlib import Path
import hashlib
import itertools
import json

import numpy as np
import pandas as pd
from scipy.io import wavfile

from reproduce_analysis import FEAT, features, score

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'experiments/statistical_audit'
PROTOCOL = ROOT / 'experiments/statistical_audit_protocol.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact_sign_flip(differences):
    """Two-sided mean-statistic test, including equality and all sign patterns."""
    d = np.asarray(differences, dtype=float)
    if d.ndim != 1 or not 1 <= len(d) <= 20 or not np.isfinite(d).all():
        raise ValueError('One to twenty finite cluster differences required.')
    signs = np.asarray(list(itertools.product((-1, 1), repeat=len(d))))
    statistics = signs @ d / len(d)
    observed = abs(d.mean())
    tolerance = 1e-12 * max(1., observed)
    return float(np.mean(abs(statistics) >= observed - tolerance))


def holm(pvalues):
    p = np.asarray(pvalues, dtype=float)
    order = np.argsort(p, kind='stable')
    adjusted = np.maximum.accumulate(p[order] * np.arange(len(p), 0, -1))
    result = np.empty_like(p)
    result[order] = np.minimum(1., adjusted)
    return result


def fit_ridge(frame, penalty):
    x = frame[FEAT].to_numpy()
    y = np.log1p(frame.abs_error_cm.to_numpy())
    w = 1 / frame.groupby('clip').clip.transform('size').to_numpy()
    w /= w.sum()
    mu = (w[:, None] * x).sum(axis=0)
    sd = np.maximum(np.sqrt((w[:, None] * (x - mu)**2).sum(axis=0)), 1e-8)
    z = np.c_[np.ones(len(x)), (x - mu) / sd]
    reg = np.diag([0.] + [penalty] * len(FEAT))
    beta = np.linalg.solve(z.T @ (w[:, None] * z) + reg, z.T @ (w * y))
    return mu, sd, beta


def load_features(meta):
    cache = ROOT / 'outputs/statistical_audit'
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / 'frame_features.csv'
    identity = dict(manifest=digest(ROOT/'reference/recording_manifest.csv'),
                    feature_code=digest(ROOT/'python/reproduce_analysis.py'))
    identity_path = cache / 'feature_identity.json'
    if path.exists() and identity_path.exists() and json.loads(identity_path.read_text()) == identity:
        return pd.read_csv(path)
    parts = []
    for r in meta.itertuples():
        audio_path = ROOT / r.audio_file
        if digest(audio_path) != r.analysis_sha256:
            raise ValueError(f'Audio identity mismatch: {r.clip}')
        fs, x = wavfile.read(audio_path)
        if fs != 16000:
            raise ValueError('Expected verified 16 kHz analysis audio.')
        x = x.astype(float)
        x -= x.mean()
        pred = pd.read_csv(ROOT/'reference/model_predictions'/f'{r.clip}.csv')
        frame, _ = features(x, pred)
        for column in ['clip', 'role', 'container_id']:
            frame[column] = getattr(r, column)
        parts.append(frame)
    frame = pd.concat(parts, ignore_index=True)
    coeff = pd.read_csv(ROOT/'results/score_coefficients.csv')
    params = (coeff['mean'].to_numpy()[1:], coeff.sd.to_numpy()[1:], coeff.coefficient.to_numpy())
    frame['reliability_score'] = score(frame, params)
    refit = fit_ridge(frame[frame.role == 'development'], .1)
    np.testing.assert_allclose(score(frame, refit), frame.reliability_score, atol=1e-10)
    frame.to_csv(path, index=False)
    identity_path.write_text(json.dumps(identity, indent=2)+'\n')
    return frame


def paired_tests():
    table = pd.read_csv(ROOT/'results/selective_by_clip.csv')
    archival = pd.read_csv(ROOT/'results/paired_container_bootstrap.csv')
    rows, differences = [], []
    for role in ['seen_test', 'unseen_test']:
        for method in ['Combined', 'Prominence']:
            g = table[(table.role == role) & (table.method == method)]
            wide = g.pivot(index=['container_id', 'clip'], columns='coverage', values='mae_cm')
            d = wide[.7] - wide[1.]
            rng = np.random.default_rng(5305)
            boot = d.to_numpy()[rng.integers(0, len(d), (2000, len(d)))].mean(axis=1)
            low, high = np.quantile(boot, [.025, .975])
            if method == 'Combined':
                old = archival[(archival.role == role) & (archival.coverage == .7)].iloc[0]
                low, high = old.ci_low, old.ci_high
            rows.append(dict(role=role, method=method, containers=len(d),
                             full_mae_cm=wide[1.].mean(), retained_mae_cm=wide[.7].mean(),
                             delta_cm=d.mean(), improved=int((d < 0).sum()),
                             worsened=int((d > 0).sum()), ci_low=low, ci_high=high,
                             exact_p=exact_sign_flip(d), sign_patterns=2**len(d)))
            for (container, clip), value in d.items():
                differences.append(dict(role=role, method=method, container_id=container,
                                        clip=clip, delta_cm=value))
    summary = pd.DataFrame(rows)
    summary['holm_p_four_comparisons'] = holm(summary.exact_p)
    summary.to_csv(OUT/'paired_tests.csv', index=False)
    pd.DataFrame(differences).to_csv(OUT/'paired_differences.csv', index=False)
    return summary


def nested_loco(frame, grid):
    pool = frame[frame.role.isin(['development', 'seen_test'])].copy()
    ids = sorted(pool.container_id.unique())
    rows, folds, validation = [], [], []
    for held in ids:
        train = pool[pool.container_id != held]
        test = pool[pool.container_id == held]
        inner_ids = sorted(train.container_id.unique())
        objectives = []
        for alpha in grid:
            losses = []
            for inner in inner_ids:
                inner_train = train[train.container_id != inner]
                inner_test = train[train.container_id == inner]
                pred = -score(inner_test, fit_ridge(inner_train, alpha))
                errors = (pred - np.log1p(inner_test.abs_error_cm.to_numpy()))**2
                loss = pd.DataFrame({'clip':inner_test['clip'].to_numpy(), 'error':errors}).groupby('clip').error.mean().mean()
                losses.append(loss)
            objectives.append(np.mean(losses))
            validation.append(dict(held_out_container=held, ridge_penalty=alpha,
                                   mean_inner_container_log_mse=np.mean(losses)))
        chosen = grid[int(np.argmin(objectives))]
        folds.append(dict(held_out_container=held, train_containers=inner_ids,
                          test_clips=sorted(test['clip'].unique()), selected_penalty=chosen,
                          inner_containers=inner_ids, standardization='outer training only'))
        for name, alpha in [('Fixed ridge 0.1', .1), ('Nested ridge', chosen)]:
            scored = test.assign(audit_score=score(test, fit_ridge(train, alpha)))
            for clip, g in scored.groupby('clip'):
                take = np.argsort(-g.audit_score.to_numpy(), kind='stable')[:int(np.ceil(.7*len(g)))]
                base, selected = g.abs_error_cm.mean(), g.abs_error_cm.iloc[take].mean()
                rows.append(dict(container_id=held, clip=clip, original_role=g.role.iloc[0],
                                 method=name, ridge_penalty=alpha, full_mae_cm=base,
                                 retained_mae_cm=selected, delta_cm=selected-base, frames=len(g)))
        print(f'LOCO {held}: held {test['clip'].nunique()} recordings; alpha={chosen:g}', flush=True)
    clips = pd.DataFrame(rows)
    containers = clips.groupby(['method','container_id'], sort=False)[['full_mae_cm','retained_mae_cm','delta_cm']].mean().reset_index()
    summaries = []
    for name,g in containers.groupby('method',sort=False):
        summaries.append(dict(method=name, containers=len(g), recordings=len(pool['clip'].unique()),
                              full_mae_cm=g.full_mae_cm.mean(), retained_mae_cm=g.retained_mae_cm.mean(),
                              delta_cm=g.delta_cm.mean(), improved_containers=int((g.delta_cm<0).sum())))
    clips.to_csv(OUT/'loco_by_clip.csv',index=False)
    containers.to_csv(OUT/'loco_by_container.csv',index=False)
    pd.DataFrame(summaries).to_csv(OUT/'loco_summary.csv',index=False)
    pd.DataFrame(validation).to_csv(OUT/'ridge_inner_cv.csv',index=False)
    (OUT/'loco_folds.json').write_text(json.dumps(folds,indent=2)+'\n')
    return pd.DataFrame(summaries)


def recording_indicators(meta, frame):
    rows = []
    for r in meta.itertuples():
        pred = pd.read_csv(ROOT/'reference/model_predictions'/f'{r.clip}.csv')
        previous = pred[(pred.time_s >= pred.time_s.iloc[-1]-.2) & (pred.time_s < pred.time_s.iloc[-1])]
        cents = abs(1200*np.log2(pred.pitch_hz.iloc[-1]/previous.pitch_hz.median()))
        rows.append(dict(clip=r.clip, role=r.role, container_id=r.container_id,
                         endpoint_jump_cents=cents, final_pitch_hz=pred.pitch_hz.iloc[-1],
                         preceding_median_pitch_hz=previous.pitch_hz.median(),
                         reference_mae_cm=frame.loc[frame['clip']==r.clip,'abs_error_cm'].mean()))
    table = pd.DataFrame(rows)
    threshold = float(table.loc[table.role=='development','endpoint_jump_cents'].quantile(.9))
    table['development_threshold_cents'] = threshold
    table['flagged'] = table.endpoint_jump_cents > threshold
    table.to_csv(OUT/'recording_indicator.csv', index=False)
    return table


def risk_curve(errors, scores, weights):
    """Global threshold curve; ties enter together, AURC uses right-step risk."""
    e, s, w = map(lambda x:np.asarray(x,dtype=float), (errors,scores,weights))
    if not (e.shape==s.shape==w.shape and e.ndim==1 and len(e)):
        raise ValueError('Equal-length nonempty vectors required.')
    if not (np.isfinite(e).all() and np.isfinite(s).all() and np.isfinite(w).all() and (w>0).all()):
        raise ValueError('Finite values and positive weights required.')
    w = w/w.sum()
    order = np.argsort(-s,kind='stable')
    end = np.r_[np.flatnonzero(np.diff(s[order]) != 0), len(s)-1]
    mass = np.cumsum(w[order])[end]
    risk = np.cumsum((w*e)[order])[end]/mass
    aurc = float(np.sum(np.diff(np.r_[0,mass])*risk))
    return pd.DataFrame({'threshold':s[order][end], 'coverage':mass, 'risk_cm':risk}), aurc


def global_selection(frame, indicators):
    table = frame.copy()
    table['endpoint_stability'] = -table['clip'].map(indicators.set_index('clip').endpoint_jump_cents)
    curves, areas, grid_rows = [], [], []
    fields = {'Combined':'reliability_score','Prominence':'prom_db',
              'Model support':'model_support_db','Endpoint stability':'endpoint_stability',
              'Error oracle':'oracle'}
    table['oracle'] = -table.abs_error_cm
    for role in ['seen_test','unseen_test']:
        g = table[table.role==role]
        w = 1/g.groupby('clip').clip.transform('size').to_numpy()
        w /= w.sum()
        base = float(w @ g.abs_error_cm.to_numpy())
        for method, field in fields.items():
            curve, area = risk_curve(g.abs_error_cm, g[field], w)
            count = len(curve)
            # Preserve all thresholds for AURC; export at most 201 display points.
            points = np.unique(np.linspace(0, count-1, min(count, 201)).round().astype(int))
            curve = curve.iloc[points].copy()
            curve.insert(0,'method',method);curve.insert(0,'role',role)
            curves.append(curve)
            areas.append(dict(role=role,method=method,aurc_cm=area,full_risk_cm=base,
                              constant_risk_reference_area_cm=base,aurc_minus_constant_cm=area-base,
                              distinct_thresholds=count,exported_points=len(curve)))
        dev = table[table.role=='development'].reliability_score.to_numpy()
        # The deployment grid depends only on development scores, never test labels.
        for q in np.linspace(0,1,101):
            threshold = float(np.quantile(dev,q))
            keep = g.reliability_score.to_numpy() >= threshold
            mass = float(w[keep].sum())
            grid_rows.append(dict(role=role,development_quantile=q,threshold=threshold,
                                  coverage=mass,risk_cm=float(w[keep]@g.abs_error_cm.to_numpy()[keep]/mass) if mass else np.nan,
                                  recordings_retained=g.loc[keep,'clip'].nunique()))
    pd.concat(curves,ignore_index=True).to_csv(OUT/'global_risk_coverage.csv',index=False)
    pd.DataFrame(areas).to_csv(OUT/'aurc.csv',index=False)
    pd.DataFrame(grid_rows).to_csv(OUT/'development_threshold_grid.csv',index=False)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    protocol = json.loads(PROTOCOL.read_text())
    meta = pd.read_csv(ROOT/'reference/recording_manifest.csv')
    dev_ids = set(meta.loc[meta.role=='development','container_id'])
    overlap = meta[['clip','role','container_id','video_id']].copy()
    overlap['container_in_score_development'] = overlap.container_id.isin(dev_ids)
    overlap.to_csv(OUT/'split_audit.csv',index=False)
    seen = overlap[overlap.role=='seen_test']
    assert seen.container_in_score_development.sum()==7
    tests = paired_tests()
    frame = load_features(meta)
    historical = pd.read_csv(ROOT/'results/clip_summary.csv').set_index('clip')
    actual = frame.groupby('clip').abs_error_cm.mean()
    np.testing.assert_allclose(actual,historical.loc[actual.index,'mae_cm'],atol=1e-12)
    loco = nested_loco(frame,protocol['nested_loco']['ridge_grid'])
    indicators = recording_indicators(meta,frame)
    global_selection(frame,indicators)
    status = dict(status='computed', protocol_sha256=digest(PROTOCOL),
                  script_sha256=digest(Path(__file__)),manifest_sha256=digest(ROOT/'reference/recording_manifest.csv'),
                  frozen_score_sha256=digest(ROOT/'results/score_coefficients.csv'),
                  test_I_overlap_containers=7,test_I_containers=8,loco_containers=11,loco_recordings=19,
                  reference='Assumption-derived reference error; no new measured water-level labels.',
                  design='Post-review exploratory audit; network stays frozen; existing benchmark is not overwritten.')
    (OUT/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(tests.to_string(index=False));print(loco.to_string(index=False))


if __name__=='__main__':
    main()
