# Methods

## Data and evaluation design

The subset contains 33 recordings from 25 containers. Development uses 11
recordings from 10 containers. Official Test I supplies 8 seen-container
recordings, Test II supplies 8 unseen-container recordings, and Test III
supplies 6 shape-diagnostic recordings. Two original examples from the same
development container stay together in grouped validation.

Selection uses metadata: clean annotation, approximately constant flow,
duration between 4 and 22 seconds, then numerical container/item ordering.
No video crosses development and principal test roles. All eight selected
unseen containers are absent from the official training-container list.
`python/verify_selection.py` reconstructs the selection and asserts agreement.

## Frozen physical estimates

The real-finetuned upstream checkpoint is fixed. Its 215 state-dictionary
keys matched strictly, and the inference adapter matched the released forward
pass on the recorded verification input. Per-frame trajectories are cached
in `reference/model_predictions/`; the MATLAB route consumes those files.

For a cylindrical air column, the simplified resonance relation is

$$f(t)=\frac{c}{4[L(t)+\beta R]}.$$

The released endpoint-corrected estimate used here is

$$\hat L(t)=\frac{\hat\lambda(t)-\hat\lambda(T)}{4}.$$

The primary reference is $L_{ref}(t)=H(1-t/T)$, with $T$ taken from the
analysis WAV duration. It assumes empty-to-full filling at constant height
rate. It is not an observed liquid-level label. A constant-volume frustum
reference is evaluated separately for semiconical containers; it changes
the reference curve, not the predictions.

## Acoustic representation

| Parameter | Value | Reason |
| --- | --- | --- |
| Sample rate | 16 kHz, mono | Match the pretrained input |
| Window | 640-sample periodic Hann | 40 ms observation interval |
| Hop | 320 samples | 20 ms updates |
| FFT | 2,048 points | 7.8125 Hz grid spacing |
| Peak band | 300-5,000 Hz | Search the relevant acoustic band |
| Peak separation | At least 100 Hz | Reduce double counting of one main lobe |
| Model support | Within 50 Hz of predicted pitch | Compare model frequency with the full 0-8 kHz spectrum |

Zero padding makes the plotted frequency grid denser; it does not improve
the window's true resolving power. The Hann main lobe spans about 100 Hz
between its first zeros.

The fitted score uses five standardized features: spectral prominence,
competing-peak amplitude ratio, log-transformed pitch jump in cents,
normalized spectral entropy, and model-frequency support. Optional odd-mode
support near 3f and 5f is retained as a diagnostic, not fitted as a sixth
predictor.

## Reliability model and evaluation

A ridge regression predicts `log(1 + reference absolute error)` with penalty
0.1. Standardization and coefficients are fitted on development data only,
with equal total weight per recording. The score is the negative prediction;
it is not a calibrated probability.

Evaluation retains 100%, 90%, 80% or 70% of frames within each complete test
recording. Acoustic scores determine selection; test reference errors do not.
Comparators include prominence, model support, the exact expectation of
uniform random retention, and an explicitly labelled error oracle.
Per-recording MAEs are averaged equally. The paired uncertainty analysis
resamples containers 2,000 times with seed 5305; frames are not treated as
independent experimental units.

## Controlled extensions

**Wiener masking:** a 3-9 s segment of recording A is corrupted with three
fixed Gaussian-noise realizations at 0, 10 and 20 dB. The estimated mask
uses a separate 0.5 s noise-only calibration segment, smoothing factor 0.8
and gain floor 0.05. The oracle uses clean/noise spectra as an informative
upper-bound comparison. Synthesis uses 40 ms Hann windows, 10 ms hops and
squared-window normalization.

**LPC:** autocorrelation Yule-Walker fits with orders 8, 16 and 32 are checked
on a fixed two-resonator control near 650 and 1,400 Hz. A real 6.5-6.6 s
frame illustrates envelope sensitivity, not validated fundamental accuracy.

**Frequency pooling:** a 1,000/1,150 Hz two-tone control compares the narrowband
STFT with 20 ERB-spaced triangular bands. This is an illustrative pooling
control, not a cochlear or perceptual experiment.
