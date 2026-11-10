# Results and interpretation

## Selective prediction

Test I is recording-held-out, with **7/8 containers shared with score development**;
clip_18/container_40 is the exception. Test II is container-disjoint from score
development and upstream model training.

| Retained frames | Test I macro reference MAE (cm) | Test II macro reference MAE (cm) |
| --- | ---: | ---: |
| 100% | 1.742 | 2.479 |
| 90% | 1.673 | 2.447 |
| 80% | 1.604 | 2.429 |
| 70% | 1.538 | 2.414 |

At 70%, the Combined paired changes are -0.204 cm [-0.274, -0.134] for Test I
and -0.065 cm [-0.158, +0.031] for Test II (archived percentile-bootstrap intervals).
Exact two-sided sign-flip p-values are 0.0078 and 0.26, respectively.
The improvement is clear on Test I; the Test II interval crosses zero.

Prominence raises Test I mean error to 1.834 cm, worsening 7/8 recordings
(p=0.016 versus no selection). Its Test II mean is lower at 2.235 cm, mainly
through clips 20 and 23, but p=0.45 versus no selection. The direction
changes across groups. See the
[four-test Holm adjustment and per-clip changes](STATISTICAL_AUDIT.md).

![Coverage versus reference error](../experiments/statistical_audit/figures/within_recording_selection.svg)

The new 19-recording, 11-container outer-LOCO evaluation yields 1.457 to 1.329 cm
for fixed ridge 0.1 and 1.331 cm for nested penalty selection. All recordings
of the outer container are withheld from this development/Test I pool.

The original development-fitted threshold produces approximately 76.9% Test I
and 79.6% Test II coverage. The new global curves give Combined AURC of
1.293/2.738 cm, versus constant-risk areas of 1.742/2.479 cm. Thus within-recording
ranking and cross-recording rejection have different behavior. The
[full audit](STATISTICAL_AUDIT.md) defines weighting, AURC, development-only
thresholds and the recording-level endpoint-jump diagnostic.

## Endpoint failure

![Endpoint switching and physical correction](../matlab_results/figure_11.png)

Clip 24 has a final model frequency far below its preceding ridge. Because
the released calculation subtracts the final wavelength from every frame,
the isolated switch introduces a global offset. Its primary reference MAE
is 5.950 cm. Substituting the metadata radius for diagnosis gives 0.294 cm.
This intervention uses the known container radius.

The same intervention worsens clip 22 (0.431 to 0.806 cm) and helps clip 18
(1.800 to 1.439 cm), showing that the effect depends on the original offset.
See `results/endpoint_diagnostic.csv`.

## Geometry and acoustic ambiguity

Semiconical reference error is sensitive to the assumed filling law. The
mean changes from 2.115 to 1.450 cm in seen semiconical recordings and from
3.591 to 2.887 cm in unseen semiconical recordings when the geometry-adjusted
reference is used. Predictions are unchanged. Bottleneck examples show
competing branches and motivate a different physical model; their
cylinder-reference errors are diagnostic only.

## Noise removal and listening

| Input SNR | Estimated output SNR | Oracle output SNR |
| --- | ---: | ---: |
| 0 dB | 6.85 dB | 10.94 dB |
| 10 dB | 13.13 dB | 16.08 dB |
| 20 dB | 20.98 dB | 22.82 dB |

Values average three noise realizations. At 20 dB, the estimated mask raises
output SNR while slightly worsening
mean band-maximum deviation, from approximately 62.3 to 63.1 Hz.

![Wiener SNR and peak deviation](../matlab_results/figure_09.png)

The author listened to the original, noisy, estimated-Wiener and oracle-Wiener
signals at 10 dB using shared gain and noise realization 1. The noisy version
had obvious noise; the estimated-Wiener version retained clear water sound
and was not obviously different from the original; the oracle sounded
intermittent. The comparison was informal and unblinded.

## LPC and pooling controls

All fitted control poles lie inside the unit circle. Resonance errors vary
non-monotonically with order. The real-frame example illustrates LPC envelope
peaks; physical mode identification requires the acoustic model as well.

The ERB-spaced pooling control weakens the valley between two nearby tones.
This explains the choice to retain a narrowband representation when
diagnosing competing peaks.

## Main interpretation

Acoustic features help reject some high-reference-error frames, on the recording-held-out Test I subset,
which shares 7/8 containers with score development. The
[level-by-level analysis](FAILURE_LEVELS.md) shows that this benefit comes mainly
from fill position: most error is a smooth recording-level gain error, and a
time-only rule outperforms the score in both test groups. A
[pre-registered confirmation](CONFIRMATION.md) on 11 new containers reproduced
these findings, except the container-shape explanation of the gain error.
The results point to recording-level gain and endpoint checks as the next
targets for improving the physical conversion.
