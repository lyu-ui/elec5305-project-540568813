# Demonstrating the completed study

The demonstration applies the frozen development-fitted score to one complete
recording and displays the spectrum, physical estimate and selected frames.

## Preparation

Complete the [one-time setup](REPRODUCIBILITY.md), then use the same Python
environment. List all available recordings with:

```bash
python python/demo_recording.py --list
```

## Three cases to inspect

Run each command from the project root:

```bash
python python/demo_recording.py --clip clip_22
python python/demo_recording.py --clip clip_18
python python/demo_recording.py --clip clip_24
```

Each command writes `diagnostic.png`, `frames.csv`, and `summary.json` under
`outputs/demo/<clip>/`. Open the PNG to see the spectrum and model pitch,
physical estimate and retained frames, and the frozen reliability score.

| Recording | Purpose | Full-recording reference MAE |
| --- | --- | ---: |
| `clip_22` | A relatively successful held-out example | 0.431 cm |
| `clip_18` | An intermediate held-out example | 1.800 cm |
| `clip_24` | Endpoint failure despite a plausible ridge over much of the clip | 5.950 cm |

These examples were selected after evaluation to illustrate three outcomes.
Errors use the filling reference defined in [Methods](METHODS.md).

Default ranking retains 70% of frames (rounded up). To explore the existing
coverage trade-off, use `--retention 0.9`. The JSON also reports coverage and
error for the unchanged development threshold. Within-clip ranking and a
fixed threshold are different selection rules; their coverage need not match.

The demo reads only pitch/physical predictions and acoustic features before
selection. Reference errors are calculated afterwards. In clip 24, many
high-ranked frames inherit the global endpoint error.

The command accepts the 33 manifest recordings. Adding a recording requires
neural inference and input-format checks.

## Listening

In MATLAB, after preparing the data:

```matlab
R = run_project(false, false);
r2_listen(R,'pours');
r2_listen(R,'comparison');
```

The second command sequence plays the original A/B recordings and then the
four shared-gain processing examples. Listening observations are described
in [Results](RESULTS.md).

## A short walkthrough

1. Explain the question: can acoustic features help identify unreliable estimates?
2. Show the official split design: 11 development, 8 seen, 8 unseen and 6 diagnostic recordings.
3. Open the three case plots. Explain that an obvious resonance can coexist with a bad physical offset.
4. Show the coverage/error results and split boundary: Test I shares 7/8 containers with score development. Test II improvement is inconclusive. Then show container LOCO and global threshold curves.
5. Play the noise comparison and explain why waveform SNR and natural sound quality differ.
6. Show the confirmation experiment: 11 new containers reproduce the fill-position and gain findings. Explain how these results motivate recording-level improvements.

## Acceptance checks

```bash
python python/verify_project.py
python python/verify_inputs.py
python python/verify_selection.py
```

The first command checks published files, split constraints, cached physical
calculations, summary aggregation, the statistical audit and 25 behavior tests.
It uses the saved results and writes `outputs/verification/project_check.json`.
The other two commands check the analysis WAVs and metadata selection after
setup. Use `verify_inputs.py --portable` after portable setup: it accepts
platform-dependent float32 bytes after format and length checks. The optional
`verify_project.py --with-data` route requires exact historical CSV bytes;
add `--portable` for numeric checks instead.

The GitHub workflow runs the first check on changes to `main` in Python 3.12
and 3.13. A separate job executes MATLAB and audits its four output tables.
These checks use frozen predictions and do not rerun the neural network.
