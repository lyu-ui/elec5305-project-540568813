# Project summary

## Question and contribution

This study asks when pouring-sound physical estimates can be trusted. It
uses the released Sound of Water model as a fixed predictor, then investigates
whether interpretable acoustic features identify unreliable frames. The
contribution is the reliability evaluation and explanation of failure
mechanisms, together with controlled signal-processing experiments.

The project does not retrain the network. It keeps continuous air-column
length as the target and separates seen from unseen containers. All errors
are against an assumption-derived filling reference. No independently
measured liquid-level trajectory is available in this experiment. The new
visual extension is an image-relative proxy comparison with author confirmation
of the 46 green water-surface bands, not independent blinded validation.

## Completed experimental scope

- 33 recordings from 25 containers, selected from official splits using metadata.
- Frozen pretrained inference, with checkpoint/adapter provenance and cached trajectories.
- STFT prominence, mode competition, continuity, spectral entropy and model support.
- Development-only reliability fitting and leave-one-container-out development diagnostics.
- Held-out selective prediction at 100%, 90%, 80% and 70% retention, simple baselines, a fixed threshold and container bootstrap intervals.
- Geometry/reference sensitivity, successful/intermediate/failure examples and endpoint diagnosis.
- LPC resonator controls, Wiener noise/distortion comparisons, frequency-pooling controls and documented listening observations.
- Independent Python reproduction and previously executed MATLAB numerical outputs.
- Standalone batch analysis, single-recording demonstration, input/result verification and public documentation.
- Full-model inference under 144 generated-noise conditions plus 16 clean controls.
- Fixed terminal-window comparisons across all 33 recordings, including worsened cases.
- All 72 prespecified video frames screened; 46 AI-assisted visual candidates and 26 exclusions. The author confirmed the 46 displayed green water-surface bands.

## Main findings

At 70% retention, seen macro reference MAE falls from 1.742 to 1.538 cm.
The paired change is -0.204 cm, with a 95% container-bootstrap interval of
[-0.274, -0.134] cm. Unseen macro reference MAE falls from 2.479 to 2.414 cm;
its -0.065 cm change has an interval of [-0.158, +0.031] cm. Exact sign-flip
p-values are 0.0078 for Test I and 0.26 for Test II. Test I shares
7/8 score-development containers, so its benefit is recording-held-out.

The [level-by-level analysis](FAILURE_LEVELS.md) explains these numbers. Offset
and rate trends carry 83–95% of test mean-square error and frame-level
fluctuation only 1–4%. The model under-scales the air column, by a median gain
of 0.82–0.85 for cylinders and 0.51–0.57 for semiconical test containers. The
score's benefit comes mainly from fill position: dropping the earliest 30% of
frames is better in 8/8 recordings of both groups (exact p = 0.0078), and
inside time bins the original score selects worse frames.

A [pre-registered confirmation](CONFIRMATION.md) on 33 recordings from 11
containers never used in the project confirmed the fill-position mechanism, the
frame-level result and the gain error (Holm p ≤ 0.005), but not the claim that
semiconical containers have lower gain (p = 0.59).
Prominence has a lower observed Test II mean (2.235 cm; p=0.45 versus no
selection), but worsens 7/8 Test I recordings. Its direction is unstable.

The post-review 11-container outer-LOCO audit pools 19 development/Test I
recordings: fixed ridge changes mean reference MAE from 1.457 to 1.329 cm;
nested ridge selection gives 1.331 cm. Global Combined AURC is 1.293/2.738 cm
for Test I/II (constant-risk 1.742/2.479 cm): on new containers, global
score ranking is worse than no selection.
See [statistical audit](STATISTICAL_AUDIT.md).

The clearest failure mechanism is global endpoint correction. In clip 24,
a final pitch switch shifts the entire physical estimate. Replacing that
correction using known geometry reduces reference disagreement, but that
post-hoc diagnostic uses extra information and is not a validated replacement
for unknown-container inference.

Noise masking provides a separate processing lesson: the estimated mask
improves output SNR, while at 20 dB it slightly worsens mean peak deviation.
The single listener also heard intermittent sound in the oracle example.
Numerical noise reduction does not guarantee preserved resonances or natural
audio quality.

## Evidence and demonstration

Use [Methods](METHODS.md), [Results](RESULTS.md), [Data](DATA.md) and
[Reproduction](REPRODUCIBILITY.md) for the full reasoning and numeric sources.
The [demonstration guide](DEMONSTRATION.md) gives a short walkthrough and
single-recording commands. Verification records distinguish executed Python
checks, historical MATLAB execution, and static checks.

The existing numerical benchmark is frozen. The earlier completion work added
usability and verification. The [experimental extension](EXPERIMENT_EXTENSION.md)
adds actual noisy neural inference, a systematic endpoint comparison and
provisional visual references. At 0 dB, reference MAE rises to 4.142/4.326 cm
for seen/unseen groups. The 0.2 s terminal median improves unseen reference MAE
from 2.482 to 1.583 cm but worsens the seen mean from 1.742 to 1.778 cm.
The author has confirmed the 46 green water-surface bands, with no coordinate
changes. This is one author review after results were available, not an independent
blinded study; blue rim/base bands were not separately confirmed. These proxies
do not measure true physical height. That validation boundary remains open.

## Boundaries of the conclusion

The selected subset supports a substantial reliability and failure study.
It does not establish deployment accuracy. Eight recordings in each main
test group, correlated frames, geometry assumptions and confounded material/
opacity labels limit generalisation. A fixed score can help rank some local
observations while missing a global physical-model failure.

Fresh containers with independently measured level traces would be a new
validation study. Reassigned spectrograms, network retraining and additional
unrelated algorithms are not required to interpret the completed experiment.
