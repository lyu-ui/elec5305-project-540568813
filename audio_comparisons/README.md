# Listening examples

`python python/setup_project.py --portable` generates four local WAVs using a shared gain:
`Original_segment.wav`, `Noisy.wav`, `Estimated_Wiener.wav`, and
`Oracle_Wiener.wav`. They use seconds 3–9 of public dataset clip 01, the fixed
10 dB noise condition and the first noise realization.

In MATLAB, use `R = run_project(true);` after setup. The recorded listening
observations are in
[`verification/LISTENING_OBSERVATIONS.json`](../verification/LISTENING_OBSERVATIONS.json).
These observations are from one informal unblinded comparison, not a
controlled perceptual study. The audio files are generated locally.

## Browser playback

The [project website](https://lyu-ui.github.io/elec5305-project-540568813/#listen)
contains an original-source preview and four local-file players. Choose the four
WAVs generated in this directory; the browser creates local object URLs and does
not upload the files. Keep the playback volume unchanged between versions.
Python setup alone produces the WAVs; MATLAB is optional for listening.

The four processed examples are not newly uploaded as public MP3/OGG assets.
The dataset card/API currently provide no explicit redistribution license; see
[the dated source review](../THIRD_PARTY_NOTICES.md#audio-publication-review-9-november-2026).
The original source player loads the file from its upstream host. It is not
the shared-gain comparison file.
