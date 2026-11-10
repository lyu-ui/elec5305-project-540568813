# Reproduction and verification

For the additional 160 neural conditions, all-recording endpoint comparison,
and provisional video references, see the separate
[extension reproduction commands](EXPERIMENT_EXTENSION.md#reproduce-and-audit).
The commands below preserve the original benchmark. New inference is optional
and requires the extension dependencies and released checkpoint.

## One-time data preparation

Use Python 3.12 or 3.13 (both checked in CI) and an internet connection. From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r python/requirements-analysis.txt
python python/setup_project.py --portable
```

On Windows activate with `.venv\Scripts\activate`. Source audio is downloaded
from the official public dataset URLs in the manifest and cached under
`.cache/source_audio/`. Source hashes are always verified exactly.
Portable mode recreates LPC/Wiener controls, four listening files and local
frame tables. It compares all twelve archived summary tables at atol 1e-7 and
rtol 1e-9, including text and missing-value identities; it checks cached-prediction
alignment, frozen-score equations and container-out-of-fold scores for the two
large generated tables. Published summaries and figures are restored byte-for-byte.
Evidence is saved in `outputs/verification/portable_analysis.json`.

Omitting `--portable` retains the original strict fourteen-CSV hash test. Identical
package versions can still produce different CSV bytes on another platform.
The original hashes remain archival evidence; they are not silently replaced
when portable mode is used. Source WAV hashes are exact in both modes. The
default mode also requires exact 16 kHz analysis WAV bytes. Portable mode does
not: resampling to float32 can round differently by CPU architecture. On
Apple Silicon (macOS 26, numpy 2.3.5, scipy 1.17.0), 3 of 33 analysis WAVs
(clip_13, clip_22, clip_28) differed in bytes, yet all regenerated tables
matched the archive within 1.3e-9. Portable mode checks such files for 16 kHz
mono float32 format, manifest length and finite values, records them in
`outputs/verification/analysis_wav_portability.json`, and then applies the
numeric table comparison above. `verify_inputs.py --portable` and
`verify_project.py --with-data --portable` apply the same rule.

The checkout includes summary tables, recorded MATLAB execution evidence,
selected figures and cached neural predictions. Audio, control MAT files and
large frame tables are generated locally. The historical two original WAVs
already present in the early repository are retained under `legacy/`.

## MATLAB route

1. Finish the setup above, then select the project root as MATLAB Current Folder.
2. Run `R = run_project;` in the Command Window.
3. Inspect the completion message, regenerated CSVs and figures in
   `outputs/matlab/` (ignored by git; `matlab_results/` keeps archived
   evidence and is not overwritten). The core assertions stop execution on a numerical or
   split mismatch.
4. For listening, run `r2_listen(R,'pours')` and
   `r2_listen(R,'comparison')`, or start with `run_project(true)`.

The numerical helpers were executed historically in MATLAB R2025b Update 6
on 30 October 2026. On 9 November 2026, GitHub CI actually ran
`R = run_project(false,false)` and `r2_plot(R,5)` in R2025b Update 7
(25.2.0.3360999), then independently audited all four result tables. The run
passed on all 33 recordings and 21,494 frames. The maximum feature mismatch
was 2.49145e-10 and identity NRMSE was 1.98838e-16.

On 10 November 2026 the complete route was also run locally on Apple Silicon
(macOS 26, MATLAB R2025b Update 6, Python 3.13.5): portable setup, then
`R = run_project;` with all 11 figures. All four MATLAB tables matched Python
(maximum 1.43e-9) and the run changed no tracked file. See
[local execution evidence](../verification/MAC_LOCAL_EXECUTION.json).

[Completed run](https://github.com/lyu-ui/elec5305-project-540568813/actions/runs/42541443174)
and [retained evidence](../verification/MATLAB_CI_EXECUTION.json) identify the
executed commit and downloadable artifact. The workflow runs this entry point
on every push and checks the lightweight project tests in both Python 3.12 and
3.13. It uses the official MathWorks setup/run-command actions; automatic
licensing applies to this public repository's base-MATLAB workflow.

Base MATLAB is sufficient for the supplied numerical implementations.
The plotting helper requests Times New Roman; if unavailable, MATLAB may
substitute another font. No report export or document-font check is needed.

## Repeat analysis or compare implementations

The setup command already executes the independent Python analysis. To repeat
the portable route while preserving published summary bytes:

```bash
python python/prepare_portable_analysis.py
```

For exact-byte reproduction in the original environment:

```bash
python python/reproduce_analysis.py
python python/endpoint_diagnostic.py
python python/verify_generated_results.py
```

After running the MATLAB entry point, compare all four complete MATLAB CSVs in
`outputs/matlab/` (add `--dir matlab_results` to audit archived evidence):

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

## Statistical revision

See [the statistical audit](STATISTICAL_AUDIT.md#reproduction) for container LOCO,
inner grouped ridge selection, exact paired tests, global risk-coverage curves
and AURC. These scripts preserve historical benchmark outputs.
