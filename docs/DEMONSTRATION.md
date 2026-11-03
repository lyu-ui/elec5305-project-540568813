# Demonstrating the completed study

The demonstration applies the existing development-fitted score to one fixed
recording. It does not fit another model, choose parameters using test error,
or introduce a new validation sample. It is an offline research prototype.

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

These examples were selected after evaluation to explain the results. They
do not establish a new test set. The reference assumes filling behavior;
it is not measured water height.

Default ranking retains 70% of frames (rounded up). To explore the existing
coverage trade-off, use `--retention 0.9`. The JSON also reports coverage and
error for the unchanged development threshold. Within-clip ranking and a
fixed threshold are different selection rules; their coverage need not match.

The demo reads only pitch/physical predictions and acoustic features before
selection. Reference errors are calculated afterwards. A high score is not a
probability or a guarantee that a physical estimate is correct. In clip 24,
even many high-ranked frames inherit the global endpoint error.

Only the 33 manifest recordings are accepted. An arbitrary new recording
requires new neural inference and validation of its input format and domain;
this demonstration does not claim to supply a validated general water sensor.

## Listening

In MATLAB, after preparing the data:

```matlab
R = run_project(false, false);
r2_listen(R,'pours');
r2_listen(R,'comparison');
```

The second command sequence plays the original A/B recordings and then the
four shared-gain processing examples. The observed listening results and
their limitations are described in [Results](RESULTS.md).

## A short walkthrough

1. Explain the question: can acoustic features help identify unreliable estimates?
2. Show the official split design: 11 development, 8 seen, 8 unseen and 6 diagnostic recordings.
3. Open the three case plots. Explain that an obvious resonance can coexist with a bad physical offset.
4. Show the held-out coverage/error results. Seen performance improves; the unseen combined-score improvement is inconclusive.
5. Play the noise comparison and explain why waveform SNR and natural sound quality differ.
6. Finish with the limitation: independent water-level measurements are needed to validate actual sensing accuracy.

## Acceptance checks

```bash
python python/verify_project.py
python python/verify_project.py --with-data
```

The first command checks the published files, split constraints, cached
physical calculations, summary aggregation and five demonstration behavior
tests. It does not download data. The second additionally checks all analysis
WAV hashes, metadata selection and the 14 prepared result tables. Output is
written to `outputs/verification/project_check.json`.

The GitHub workflow runs the first check on changes to `main`. Neither check
executes MATLAB or reruns the neural network. Use the separate MATLAB route
and four-table audit for those numerical outputs.
