# Pouring-Sound Reliability

Acoustic diagnostics for physical estimates from pouring sounds.

**[Project website](https://lyu-ui.github.io/elec5305-project-540568813/)** ·
[Methods](docs/METHODS.md) · [Results](docs/RESULTS.md) ·
[Reproduce the experiments](docs/REPRODUCIBILITY.md)

**Question:** can acoustic evidence identify when a pretrained model's
air-column estimate is unreliable?

This project evaluates a frozen [Sound of Water](https://github.com/bpiyush/SoundOfWater)
model on 33 recordings from 25 containers. It combines spectral diagnostics,
a development-only reliability model, held-out selective prediction, and
focused Wiener/LPC controls. The MATLAB experiment helpers have been run and
checked against an independent Python implementation.

**Scope:** errors are measured against an assumption-derived filling curve.
There are no independently measured liquid-level trajectories in this project.
Results therefore describe agreement with that reference, not validated
liquid-level accuracy. The extension also includes explicitly provisional,
AI-assisted image-relative references. The author has confirmed all 46 green
water-surface bands; these are not calibrated measurements.

## Extended experiments

- **160 model conditions:** 16 clean controls and 144 noisy runs across all test
  recordings, with the network and reliability score frozen. At 0 dB, the score
  still retains many high-error frames.
- **33-recording endpoint comparison:** a fixed terminal median repairs two
  severe global offsets but worsens several other recordings. Every case is retained.
- **72 video time points screened:** 46 provisional visual labels and 26 documented
  exclusions. The project author has confirmed all 46 displayed green water-surface
  bands. Independent blinded review, rim/base confirmation and calibrated physical
  validation remain open.

[Extension methods, findings and reproduction](docs/EXPERIMENT_EXTENSION.md) ·
[Per-recording results](experiments/results/)

![Processing pipeline](figures/fig01_pipeline.png)

## Main findings

| Evaluation group | Full-coverage MAE | MAE at 70% retention | Paired change and 95% interval |
| --- | ---: | ---: | --- |
| Seen containers, 8 recordings | 1.742 cm | 1.538 cm | -0.204 cm [-0.274, -0.134] |
| Unseen containers, 8 recordings | 2.479 cm | 2.414 cm | -0.065 cm [-0.158, +0.031] |

Values are equal-recording means. Selection uses acoustic scores; the paired
interval resamples containers 2,000 times. The unseen interval includes zero,
so generalization is inconclusive. A simple prominence baseline outperforms
the combined score on the unseen subset at 70% retention (2.235 cm).

![Coverage and reference error](matlab_results/figure_05.png)

An endpoint pitch switch can shift the entire physical trajectory even when
most of the recording has a plausible spectral ridge. This is a stronger
diagnostic finding than the small unseen-group improvement. See
[results and interpretation](docs/RESULTS.md).

## Quick start

### Prepare the inputs once

Download or clone the project. In a terminal at the project root, use Python
3.12 and the pinned analysis dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r python/requirements-analysis.txt
python python/setup_project.py
```

On Windows, use `.venv\Scripts\activate` for activation. The setup script
fetches the 33 recordings directly from the original public dataset, verifies
the source and resampled WAV hashes, and recreates the fixed control inputs,
listening examples and complete Python result tables. It then checks all
14 generated CSVs against their recorded hashes. Internet access is required
for this preparation; no neural-network checkpoint is downloaded.

### Run MATLAB

Select the project root as MATLAB Current Folder, then run:

```matlab
R = run_project;
```

This recomputes the analysis, checks it against the prepared Python reference
tables, and writes the complete MATLAB figures and CSVs to `matlab_results/`.
After setup this route runs offline. For listening:

```matlab
R = run_project(true);
```

For a numerical run without opening figure windows:

```matlab
R = run_project(false, false);
```

Tested computation environment: **MATLAB R2025b Update 6**, base MATLAB.
The `run_project` entry point calls the unchanged, previously executed
numerical helpers. The wrapper has passed static checks; it has not itself
been executed in MATLAB in the packaging environment.

Expected core output:

```text
MATLAB checks passed: 33 recordings, 21494 frames. Maximum mismatch 3.32e-10.
```

The last value can vary slightly by platform. The code checks explicit numeric
tolerances. Use a comfortable listening volume; playback is disabled by default.

## Demonstrate and verify

After setup, inspect one held-out recording without rerunning the full study:

```bash
python python/demo_recording.py --clip clip_24
python python/verify_project.py --with-data
```

The demo writes a diagnostic plot, frame-level CSV and summary under
`outputs/demo/clip_24/`. It uses the frozen score; errors are calculated only
after selection. See the [demonstration guide](docs/DEMONSTRATION.md) for
the three illustrative cases, listening and a short walkthrough.

`python python/verify_project.py` runs without audio downloads and is also
used by [automated verification](https://github.com/lyu-ui/elec5305-project-540568813/actions/workflows/verify.yml).
The [project summary](docs/PROJECT_SUMMARY.md) connects the completed work
to the main conclusion and remaining scientific limitations.

## Experiments

| Component | Purpose | Evidence |
| --- | --- | --- |
| Spectral diagnostics | Quantify prominence, competition, continuity, entropy and model support | `results/frame_features.csv` (generated by setup) |
| Reliability scoring | Fit only on development containers, then rank held-out frames | `results/score_coefficients.csv`, `results/selective_by_clip.csv` |
| Held-out evaluation | Separate seen and unseen container tests | `results/selective_summary.csv`, `results/paired_container_bootstrap.csv` |
| Endpoint diagnosis | Explain a global error caused by the final pitch sample | `results/endpoint_diagnostic.csv` |
| Geometry sensitivity | Change the filling reference for tapered vessels | `results/clip_summary.csv` |
| Wiener comparison | Compare noise removal with spectral distortion and audition | `results/wiener_trials.csv`, `audio_comparisons/` |
| LPC control | Check estimated resonances on a known two-resonator signal | `results/lpc_control.csv` |
| Frequency pooling control | Show how coarse bands weaken evidence of competing peaks | `results/auditory_control.csv` |

## Project layout

| Path | Contents |
| --- | --- |
| `run_project.m` | MATLAB entry point |
| `r2_*.m` | Modular analysis, plotting and playback helpers |
| `data/` | Analysis WAVs and fixed controls created by setup |
| `reference/` | Official metadata, selection manifest, cached predictions and provenance |
| `results/` | Reference summaries; full frame tables regenerated by setup |
| `matlab_results/` | Recorded summary tables, selected scientific figures and execution log; full outputs regenerated in MATLAB |
| `figures/` | Scientific figures and pipeline; setup regenerates the complete figure set |
| `audio_comparisons/` | Shared-gain listening examples generated locally |
| `python/` | Independent analysis and optional pretrained-model inference |
| `verification/` | Numerical comparison evidence and listening observations |
| `docs/` | Methods, data, results and reproduction documentation |
| `experiments/` | Fixed extension settings, noise/endpoint results, provisional visual labels and figures |
| `legacy/early-spectral-analysis/` | Original two-recording exploratory code, data and outputs |

The [early two-recording analysis](legacy/early-spectral-analysis/README.md) is
retained separately as project history. Its exploratory features are not the
fitted reliability score evaluated in the current experiment.

The historical `r2_` helper prefix is retained to keep the checked numerical
implementation unchanged. After the one-time preparation, the project runs
from MATLAB without a course report or Live Script. The source recording
manifest, cached model predictions, summary results and analysis code are
tracked; new recording copies and generated control/audio assets stay local.

## Verification of preparation

A clean-input test fetched and verified all 33 recordings, reproduced all
14 Python CSV tables exactly, and recreated both fixed control arrays and
all four listening WAVs without changes. See
[setup validation](verification/SETUP_VALIDATION.json). This test did not
execute MATLAB; the original MATLAB execution and four-table comparison
are documented separately.

## Documentation

- [Methods and parameter choices](docs/METHODS.md)
- [Results, failures and interpretation](docs/RESULTS.md)
- [Noise, endpoint and visual-reference extension](docs/EXPERIMENT_EXTENSION.md)
- [Data selection and provenance](docs/DATA.md)
- [Reproduction and verification](docs/REPRODUCIBILITY.md)
- [Third-party sources and notices](THIRD_PARTY_NOTICES.md)

## Known limitations

- Reference trajectories assume filling behavior; they are not measured truth.
- Image-relative visual annotations are AI-assisted; the author confirmed the 46
  green water-surface bands after results were available. This is not independent
  blinded validation. Blue rim/base bands were not separately confirmed; perspective,
  refraction and visibility selection prevent a centimetre-accuracy claim.
- Only 8 seen and 8 unseen recordings enter the principal held-out comparison.
- Ranking uses complete recordings, and physical endpoint correction uses the
  last model sample. The current workflow is offline.
- Bottleneck cases diagnose physical-model mismatch and are excluded from the
  principal cylindrical/semiconical accuracy summary.
- Listening observations come from one informal, unblinded comparison.
- The combined score is not a calibrated confidence probability and does not
  outperform every baseline on every split.

## Attribution

Project author: **Yueyao Lyu**, University of Sydney, ELEC5305, 2026.

This project builds on Bagad et al., *The Sound of Water: Inferring Physical
Properties from Pouring Liquids*, IEEE TPAMI, 2026,
[DOI: 10.1109/TPAMI.2026.3690989](https://doi.org/10.1109/TPAMI.2026.3690989).
The pretrained network and source recordings are upstream contributions.
This project's contribution is the acoustic reliability analysis, controlled
experiments, diagnosis and reproducible evaluation.

[Upstream code](https://github.com/bpiyush/SoundOfWater) ·
[Dataset](https://huggingface.co/datasets/bpiyush/sound-of-water) ·
[Model weights](https://huggingface.co/bpiyush/sound-of-water-models)
