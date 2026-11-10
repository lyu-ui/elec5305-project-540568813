"""Compare MATLAB output tables with the Python reference; does not run MATLAB.

By default this audits a fresh run in outputs/matlab/ (written by run_project).
Use --dir matlab_results to audit archived evidence instead.
"""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--dir', type=Path, default=root / 'outputs' / 'matlab',
                    help='Directory containing the four MATLAB CSVs (default: outputs/matlab).')
args = parser.parse_args()
source = args.dir if args.dir.is_absolute() else root / args.dir
print(f'Auditing MATLAB tables in {source.relative_to(root) if source.is_relative_to(root) else source}')
names = ['frame_features.csv', 'selective_by_clip.csv',
         'wiener_trials.csv', 'lpc_control.csv']
for name in names:
    a = pd.read_csv(source / name)
    b = pd.read_csv(root / 'results' / name)
    if a.shape != b.shape or list(a.columns) != list(b.columns):
        raise AssertionError(f'{name}: dimensions or columns differ')
    maximum = 0.0
    for column in a:
        if not a[column].isna().equals(b[column].isna()):
            raise AssertionError(f'{name}: missing-value positions differ in {column}')
        if pd.api.types.is_numeric_dtype(a[column]) and pd.api.types.is_numeric_dtype(b[column]):
            np.testing.assert_allclose(a[column], b[column], rtol=1e-9,
                                       atol=1e-7, equal_nan=True,
                                       err_msg=f'{name}: {column}')
            difference = np.abs(a[column].to_numpy() - b[column].to_numpy())
            if np.any(np.isfinite(difference)):
                maximum = max(maximum, float(np.nanmax(difference)))
        elif not a[column].fillna('').equals(b[column].fillna('')):
            raise AssertionError(f'{name}: text differs in {column}')
    print(f'{name}: {len(a):,} rows; maximum numeric difference {maximum:.3g}')
print('All four MATLAB tables agree with the Python reference.')
