# Listening examples

`python python/setup_project.py` generates four local WAVs using a shared gain:
`Original_segment.wav`, `Noisy.wav`, `Estimated_Wiener.wav`, and
`Oracle_Wiener.wav`. They use seconds 3–9 of public dataset clip 01, the fixed
10 dB noise condition and the first noise realization.

In MATLAB, use `R = run_project(true);` after setup. The recorded listening
observations are in
[`verification/LISTENING_OBSERVATIONS.json`](../verification/LISTENING_OBSERVATIONS.json).
These observations are from one informal unblinded comparison, not a
controlled perceptual study. The audio files are generated locally.
