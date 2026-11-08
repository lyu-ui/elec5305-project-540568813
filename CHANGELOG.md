# Changelog

## Experimental extension - November 2026

- Executed 16 clean controls and 144 Gaussian-noise neural inference conditions with the frozen model and score.
- Compared fixed terminal medians with the original decoder across all 33 recordings, retaining negative results.
- Screened all 72 fixed-time paired-video frames; recorded 46 provisional AI visual labels and 26 exclusions.
- Added stage-wise analysis, mechanism examples, container-level uncertainty, source/alignment audits and reproducible checks.
- Kept the original benchmark and default decoder unchanged. Visual human review and calibrated physical validation remain open.

## Demonstration and acceptance checks - 3 November 2026

- Added a single-recording demonstration with acoustic-only scoring followed by separate reference-error evaluation.
- Added fixed-input, physical-decoding, split and summary checks, plus five score/selection behavior tests.
- Added an automated GitHub verification workflow that requires no audio or checkpoint downloads.
- Added a final project summary and demonstration walkthrough.
- Kept the original numerical benchmark and its conclusions unchanged.

## Public project preparation - 1 November 2026

- Added a setup script that obtains source audio directly from the official public dataset and verifies source/analysis hashes.
- Regenerate fixed controls, listening examples and large frame tables locally using the recorded seeds and pinned dependencies.
- Keep summary results, cached model predictions, execution evidence and selected figures in the public tree.
- Documented the initial Python preparation and subsequent offline MATLAB workflow.


## Complete project — 30 October 2026

- Expanded the project from two exploratory recordings to 33 recordings from 25 containers, using frozen pretrained-model predictions and development-only reliability fitting.
- Added a standalone MATLAB entry point using the checked experiment helpers.
- Documented methods, data provenance, held-out results and known failures.
- Preserved actual MATLAB outputs and independent Python reference tables.
- Added a numerical comparison command, input verification and project file checksums.
- Updated the GitHub Pages project overview with current findings and instructions for the shared-gain listening experiment.
- Retained the early code, recordings and results under `legacy/early-spectral-analysis/`.
- Removed course-report PDFs and submission text from the current project tree. Previous commits retain their original history.
