"""Regenerate local MATLAB inputs with explicit cross-platform numeric checks.

Archived summaries and figures are restored byte-for-byte after regeneration.
Large generated frame tables stay local. The exact-byte checker is unchanged.
"""
from pathlib import Path
import hashlib
import io
import json
import subprocess
import sys

import numpy as np
import pandas as pd

from reproduce_analysis import fit_score, score

ROOT = Path(__file__).resolve().parents[1]


def compare_tables(actual, expected):
    if actual.shape != expected.shape or list(actual.columns) != list(expected.columns):
        raise AssertionError('Table shape/columns differ.')
    maximum = 0.
    for column in expected:
        a, b = actual[column], expected[column]
        if not a.isna().equals(b.isna()):
            raise AssertionError(f'Missing values differ: {column}')
        if pd.api.types.is_numeric_dtype(b):
            np.testing.assert_allclose(a,b,atol=1e-7,rtol=1e-9,equal_nan=True,err_msg=column)
            delta = abs(a.to_numpy(dtype=float)-b.to_numpy(dtype=float))
            if np.isfinite(delta).any():
                maximum = max(maximum,float(np.nanmax(delta)))
        elif not a.fillna('').equals(b.fillna('')):
            raise AssertionError(f'Text values differ: {column}')
    return maximum


def main():
    manifest = json.loads((ROOT/'reference/generated_results_sha256.json').read_text())['files']
    generated_only = {'results/frame_features.csv','results/development_grouped_oof.csv'}
    originals = {}
    for name, expected_hash in manifest.items():
        if name in generated_only:
            continue
        data = (ROOT/name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected_hash:
            raise ValueError(f'Archived baseline was changed: {name}; use a clean checkout.')
        originals[name] = data
    # The original generator also renders figures and writes a historical marker.
    for directory in ['figures']:
        for path in (ROOT/directory).glob('*'):
            if path.is_file():
                originals[str(path.relative_to(ROOT))] = path.read_bytes()
    originals['results/verification.json'] = (ROOT/'results/verification.json').read_bytes()
    report = {'status':'passed','numeric_atol':1e-7,'numeric_rtol':1e-9,'tables':{}}
    try:
        for script in ['reproduce_analysis.py','endpoint_diagnostic.py']:
            subprocess.run([sys.executable,str(ROOT/'python'/script)],cwd=ROOT,check=True)
        for name,data in originals.items():
            if name in manifest:
                report['tables'][name] = compare_tables(pd.read_csv(ROOT/name),pd.read_csv(io.BytesIO(data)))
        frames = pd.read_csv(ROOT/'results/frame_features.csv')
        for clip, g in frames.groupby('clip',sort=False):
            p = pd.read_csv(ROOT/'reference/model_predictions'/f'{clip}.csv')
            p = p[(p.time_s>=g.time_s.iloc[0]) & (p.time_s<=g.time_s.iloc[-1])].reset_index(drop=True)
            compare_tables(g[list(p.columns)].reset_index(drop=True),p)
        coeff = pd.read_csv(io.BytesIO(originals['results/score_coefficients.csv']))
        frozen = (coeff['mean'].to_numpy()[1:],coeff.sd.to_numpy()[1:],coeff.coefficient.to_numpy())
        np.testing.assert_allclose(frames.reliability_score,score(frames,frozen),atol=1e-7,rtol=1e-9)
        dev = frames[frames.role=='development']
        oof = pd.read_csv(ROOT/'results/development_grouped_oof.csv')
        assert len(oof)==len(dev) and not oof.duplicated(['clip','time_s']).any()
        for container,g in oof.groupby('container_id',sort=False):
            train = dev[dev.container_id!=container]
            np.testing.assert_allclose(g.score_oof,score(g,fit_score(train)),atol=1e-7,rtol=1e-9)
        report['generated_frames_checked'] = len(frames)
        report['development_oof_frames_checked'] = len(oof)
        report['large_table_scope'] = 'Cached prediction alignment, frozen score, and leave-container-out score equations; not byte identity.'
        out = ROOT/'outputs/verification/portable_analysis.json'
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
    finally:
        for name,data in originals.items():
            (ROOT/name).write_bytes(data)


if __name__=='__main__':
    main()
