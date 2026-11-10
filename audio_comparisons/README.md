# Listening examples

`python python/setup_project.py --portable` generates four local WAVs using a shared gain:
`Original_segment.wav`, `Noisy.wav`, `Estimated_Wiener.wav`, and
`Oracle_Wiener.wav`. They use seconds 3–9 of public dataset clip 01, the fixed
10 dB noise condition and the first noise realization.

In MATLAB, use `R = run_project(true);` after setup. The recorded listening
observations are in
[`verification/LISTENING_OBSERVATIONS.json`](../verification/LISTENING_OBSERVATIONS.json).
These observations come from one informal, unblinded comparison.

## Browser playback

The [project website](https://lyu-ui.github.io/elec5305-project-540568813/#listen)
contains an original-source preview and four local-file players. Choose the four
WAVs generated in this directory for playback on your device. Keep the playback
volume unchanged between versions.
Python setup alone produces the WAVs; MATLAB is optional for listening.

The four processed examples are generated locally. Redistribution terms are
documented in
[the dated source review](../THIRD_PARTY_NOTICES.md#audio-publication-review-9-november-2026).
The source-preview player loads the upstream recording before shared-gain processing.
