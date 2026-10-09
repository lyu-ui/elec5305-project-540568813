# Audio provenance

The two WAVs are unmodified source audio files downloaded on 4 September 2026 from the publicly accessible Sound of Water dataset associated with Bagad et al. (2025). Local names were shortened for portability. No audio sample values were edited on disk. Mean removal is performed in the analysis code. The source files are already segmented: do not trim them again using the original video timestamps. Durations in this report are measured from the WAV sample count and can differ slightly from annotated video intervals.

Dataset: https://huggingface.co/datasets/bpiyush/sound-of-water

Paper: https://doi.org/10.1109/ICASSP49660.2025.10889950

Source metadata: https://huggingface.co/datasets/bpiyush/sound-of-water/blob/main/annotations/localisation.csv

The included source_metadata.csv preserves the two corresponding annotation rows. Both are marked container_1, water_normal, constant flow_rate_appx, clean=yes and bg-noise=no. These are source labels, not independently measured noiselessness or volume ground truth. Data and original annotations remain attributable to their creators; no new data license is asserted here.

## pour_A.wav

Original: `VID_20240116_230040_2.1_16.7.wav`

Source: https://huggingface.co/datasets/bpiyush/sound-of-water/resolve/main/audios/VID_20240116_230040_2.1_16.7.wav

SHA-256: `3c481c2de6e95320354ba062ba5e62d794dc73daa8c302f2424d9c1a1d0c0340`

## pour_B.wav

Original: `VID_20240116_230132_3.3_18.8.wav`

Source: https://huggingface.co/datasets/bpiyush/sound-of-water/resolve/main/audios/VID_20240116_230132_3.3_18.8.wav

SHA-256: `6e74927c46d7f2985f02244346fa11be511f0df141de5e18565508ce1ffacb76`

