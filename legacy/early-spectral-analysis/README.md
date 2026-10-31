# Early spectral analysis

This directory preserves the project's two-recording exploratory stage from
9 October 2026. Both recordings belong to the same annotated container.
These early acoustic descriptors do not establish physical-estimation error
or cross-container generalization. The current 33-recording study and its
separate development/held-out evaluation are documented in the
[main README](../../README.md).

## Contents

- `data/`: original source WAVs and the corresponding metadata rows.
- `matlab/`: FFT/STFT and other early analysis helpers.
- `results/`: saved early experiment tables and diagnostic figures.
- [Audio provenance](docs/DATA_PROVENANCE.md): original file links and hashes.

## Reproduce the early diagnostic figures

From the repository root in MATLAB:

```matlab
run('legacy/early-spectral-analysis/matlab/run_reliability_features.m')
```

The script resolves its paths relative to its own location and writes the two
diagnostic figures and feature CSV within this directory's `results/` folder.
It begins with `clear; close all; clc;` and clears the current MATLAB workspace.
This historical folder contains helpers and recorded results; it does not
claim to rerun every earlier Live Script experiment, whose fixed noise bank
and course document are outside this public project.
