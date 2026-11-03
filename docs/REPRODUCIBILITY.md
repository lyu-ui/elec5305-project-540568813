# Reproduction and verification

## One-time data preparation

Use Python 3.12 and an internet connection. From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r python/requirements-analysis.txt
python python/setup_project.py
```

On Windows activate with `.venv\Scripts\activate`. Source audio is downloaded
from the official public dataset URLs in the manifest and cached under
`.cache/source_audio/`. The source and 16 kHz analysis WAV hashes are verified.
The script recreates fixed LPC/Wiener controls, four listening files, all Python
result tables and figures. The 14 CSV hashes are checked against
`reference/generated_results_sha256.json`. A source or result mismatch stops
setup rather than silently changing the reference.

The checkout includes summary tables, recorded MATLAB execution evidence,
selected figures and cached neural predictions. Audio, control MAT files and
large frame tables are generated locally. The historical two original WAVs
already present in the early repository are retained under `legacy/`.

## MATLAB route

1. Finish the setup above, then select the project root as MATLAB Current Folder.
2. Run `R = run_project;` in the Command Window.
3. Inspect the completion message, regenerated CSVs and figures in
   `matlab_results/`. The core assertions stop execution on a numerical or
   split mismatch.
4. For listening, run `r2_listen(R,'pours')` and
   `r2_listen(R,'comparison')`, or start with `run_project(true)`.

The numerical helpers were executed in MATLAB R2025b Update 6
(25.2.0.3312555) on 30 October 2026. The retained log records 10:21:04.
The executed workflow's saved final marker was 10:22:06. The new standalone
entry point uses those unchanged helpers, but has not itself been run in
MATLAB in the packaging environment. Static syntax checking is separate
from native execution.

Base MATLAB is sufficient for the supplied numerical implementations.
The plotting helper requests Times New Roman; if unavailable, MATLAB may
substitute another font. No report export or document-font check is needed.

## Repeat analysis or compare implementations

The setup command already executes the independent Python analysis. To repeat
it after preparing the WAVs:

```bash
python python/reproduce_analysis.py
python python/endpoint_diagnostic.py
python python/verify_generated_results.py
```

After running the MATLAB entry point, compare all four complete MATLAB CSVs:

```bash
python python/audit_matlab_results.py
```

The original four-table audit is recorded in
`verification/MATLAB_NUMERIC_AUDIT.json`; the large MATLAB frame table is
regenerated locally. Analysis writes CSVs into `results/` and plots into
`figures/`, so use a working copy if preserving supplied output bytes matters.

MATLAB recomputes core acoustic features, scoring, selective prediction,
Wiener comparisons and LPC controls. Python additionally regenerates grouped
development diagnostics, container bootstrap intervals, the fixed-threshold
analysis and the endpoint diagnostic. These scopes are documented separately.

## Optional neural-network inference

Keep a separate working copy for this optional route: the released inference
adapter writes predictions and provenance under `reference/`. Regenerated
predictions can differ slightly by platform and will no longer match the
frozen checkout checksums. The normal analysis and demonstration use the
recorded predictions and do not require this step.

The approximately 378 MB checkpoint is not bundled. The normal MATLAB and
Python analysis routes do not download it. To reproduce neural inference,
create a separate environment using `python/requirements-inference.txt`,
install the appropriate CPU PyTorch wheel, then run:

```bash
python python/download_model.py
python python/infer_official.py --root . --checkpoint python/checkpoint.pth --config python/wav2vec2_config.json
```

The checkpoint downloader verifies SHA-256 before use. See
`reference/model_run.json` for the original inference environment. A different
hardware/software stack may produce small floating-point differences.

## Numerical evidence

| CSV | Rows | Maximum numeric difference, MATLAB vs Python |
| --- | ---: | ---: |
| `frame_features.csv` | 21,494 | 3.69e-10 |
| `selective_by_clip.csv` | 320 | 5.33e-15 |
| `wiener_trials.csv` | 27 | 4.98e-13 |
| `lpc_control.csv` | 3 | 1.35e-9 |

Column-level evidence is retained in `verification/MATLAB_NUMERIC_AUDIT.json`.
The identity-mask overlap-add reconstruction error was 2.1352e-16 NRMSE.
The audit script compares the generated files after MATLAB execution using `atol=1e-7`, `rtol=1e-9`,
matching nonnumeric columns and missing-value locations. It does not claim
to have run MATLAB.

`verification/PACKAGING_CHECKS.json` records checks performed on this project
bundle. It distinguishes the actual earlier MATLAB execution from static
checks and Python reproduction in the packaging environment.
