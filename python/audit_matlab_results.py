"""Compare recorded MATLAB outputs with Python tables; does not run MATLAB."""
from pathlib import Path
import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
names = ['frame_features.csv', 'selective_by_clip.csv',
         'wiener_trials.csv', 'lpc_control.csv']
for name in names:
    a = pd.read_csv(root / 'matlab_results' / name)
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
print('All four recorded MATLAB tables agree with the Python reference.')
