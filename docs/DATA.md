# Data and provenance

Source dataset: [Sound of Water](https://huggingface.co/datasets/bpiyush/sound-of-water).
The project selects a fixed 33-recording subset. The setup script downloads
the source recordings directly from their original public host and downsamples
them to 16 kHz mono for local analysis. The source authors recorded and released these sounds; they
are not new measurements collected by this project.

| Role | Official split | Recordings | Containers |
| --- | --- | ---: | ---: |
| Development | train | 11 | 10 |
| Seen test | Test I | 8 | 8 |
| Unseen test | Test II | 8 | 8 |
| Shape diagnostics | Test III | 6 | 6 |

There are 25 unique containers across roles, because seen containers can
recur across official splits. Counts must not be added as if all groups
contained distinct containers. The shape-diagnostic set includes four
bottleneck cases, one cylinder and one pointed semiconical/conical case;
there is no verified hemispherical recording in this subset.

## Provenance files

- `reference/recording_manifest.csv`: original IDs, upstream URLs, analysis
  paths, source and analysis SHA-256 hashes, sampling properties and geometry.
- `reference/official_*.csv`: original official metadata and split labels.
- `reference/model_run.json`: exact checkpoint hash, upstream commit and
  inference environment.
- `reference/adapter_verification.json`: strict checkpoint/forward comparison.
- `reference/model_predictions/`: frozen outputs required for MATLAB.

`python/setup_project.py` prepares all 33 analysis WAVs.
`python/verify_inputs.py` verifies their hashes and
the declared split constraints. `python/verify_selection.py` reconstructs
the metadata-only subset selection.

## Input controls

The setup script recreates `data/wiener_inputs.mat` (clean segment, seeded
noise and calibration realizations) and `data/lpc_control.mat` (known-resonator
control). It also creates the shared-gain listening examples in
`audio_comparisons/`. These generated WAV/MAT assets are not tracked in the
public project. The fixed seeds and the pinned numerical environment preserve
the experimental inputs; source and analysis WAVs are checked by SHA-256.
See [reproduction instructions](REPRODUCIBILITY.md) for the one-time setup.

## Reference-label limitation

The height and WAV duration define an empty-to-full linear-height reference.
For tapered containers, a geometry-adjusted constant-volume curve is a
sensitivity comparison. Neither curve is an independently measured water
level. Per-frame errors must be described as *reference errors*.

## Recording index

Full source URLs and hashes remain in the CSV manifest.

| Clip | Role | Container | Shape | Duration (s) |
| --- | --- | --- | --- | ---: |
| clip_01 | development | container_1 | cylindrical | 14.656 |
| clip_02 | development | container_6 | cylindrical | 13.184 |
| clip_03 | development | container_7 | cylindrical | 10.219 |
| clip_04 | development | container_17 | cylindrical | 21.909 |
| clip_05 | development | container_18 | cylindrical | 20.736 |
| clip_06 | development | container_4 | semiconical | 7.424 |
| clip_07 | development | container_5 | semiconical | 6.699 |
| clip_08 | development | container_25 | semiconical | 8.832 |
| clip_09 | development | container_30 | semiconical | 7.744 |
| clip_10 | development | container_31 | semiconical | 13.973 |
| clip_11 | seen_test | container_1 | cylindrical | 12.267 |
| clip_12 | seen_test | container_6 | cylindrical | 7.744 |
| clip_13 | seen_test | container_7 | cylindrical | 7.552 |
| clip_14 | seen_test | container_18 | cylindrical | 16.896 |
| clip_15 | seen_test | container_25 | semiconical | 4.267 |
| clip_16 | seen_test | container_30 | semiconical | 7.147 |
| clip_17 | seen_test | container_31 | semiconical | 13.013 |
| clip_18 | seen_test | container_40 | semiconical | 9.216 |
| clip_19 | unseen_test | container_2 | cylindrical | 20.885 |
| clip_20 | unseen_test | container_11 | cylindrical | 17.984 |
| clip_21 | unseen_test | container_20 | cylindrical | 14.507 |
| clip_22 | unseen_test | container_21 | cylindrical | 11.093 |
| clip_23 | unseen_test | container_9 | semiconical | 21.760 |
| clip_24 | unseen_test | container_13 | semiconical | 18.901 |
| clip_25 | unseen_test | container_28 | semiconical | 9.899 |
| clip_26 | unseen_test | container_37 | semiconical | 17.109 |
| clip_27 | development | container_1 | cylindrical | 15.531 |
| clip_28 | shape_diagnostic | container_19 | bottleneck | 13.867 |
| clip_29 | shape_diagnostic | container_26 | bottleneck | 18.389 |
| clip_30 | shape_diagnostic | container_32 | bottleneck | 16.192 |
| clip_31 | shape_diagnostic | container_33 | bottleneck | 5.568 |
| clip_32 | shape_diagnostic | container_3 | cylindrical | 13.419 |
| clip_33 | shape_diagnostic | container_15 | semiconical | 12.949 |
