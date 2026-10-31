# Locally prepared analysis inputs

From the project root, install `python/requirements-analysis.txt` and run
`python python/setup_project.py`. The script downloads all 33 source WAVs
directly from the original public Sound of Water dataset, verifies source
SHA-256 hashes, resamples them to 16 kHz mono, verifies the analysis hashes,
and regenerates the fixed LPC/Wiener inputs and complete Python tables.

The authoritative source URLs, geometry and hashes are in
[`reference/recording_manifest.csv`](../reference/recording_manifest.csv).
WAV and MAT files in this directory are generated locally and are not tracked.
After setup, the normal MATLAB analysis can run offline.
