# Third-party sources and notices

## Sound of Water code

The upstream model implementation in `python/upstream/model.py` comes from
[bpiyush/SoundOfWater](https://github.com/bpiyush/SoundOfWater).
Its MIT license and copyright notice are preserved in
`python/upstream/LICENSE`. The exact upstream commit is recorded in
`reference/model_run.json`.

## Dataset and weights

Audio, official metadata and pretrained model outputs originate from the
[Sound of Water dataset](https://huggingface.co/datasets/bpiyush/sound-of-water)
and [model release](https://huggingface.co/bpiyush/sound-of-water-models).
Per-recording source URLs and hashes are retained in the manifest. Source
recordings and model weights are third-party work; the upstream code's MIT
notice is not asserted as a blanket license for every dataset asset.
No new dataset license is granted by this repository. Consult the upstream
distribution terms when reusing or redistributing those assets.

The visual extension downloads paired public videos from the same dataset.
Video files and extracted frame images stay local; the repository publishes
source URLs, hashes, provisional annotation coordinates and derived analysis.
Optional private review sheets show attributed frame crops for annotation
inspection. The AI-assisted coordinates are project annotations, not labels
provided or certified by the dataset authors.

## Reference

Bagad et al. (2026). *The Sound of Water: Inferring Physical Properties from
Pouring Liquids*. IEEE Transactions on Pattern Analysis and Machine Intelligence.
https://doi.org/10.1109/TPAMI.2026.3690989

## Project scope

The original analysis, reliability diagnostics and documentation are by
Yueyao Lyu. This package does not include university report PDFs, Live Script
reports, teacher feedback, marking rubrics or course sample reports.
