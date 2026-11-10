# Third-party sources and notices

## Sound of Water code

The upstream model implementation in `python/upstream/model.py` comes from
[bpiyush/SoundOfWater](https://github.com/bpiyush/SoundOfWater).
Its MIT license and copyright notice are preserved in
`python/upstream/LICENSE`. The exact upstream commit is recorded in
`reference/model_run.json`.

## Scope of the project MIT license

The root LICENSE covers original project code and documentation. Dataset media,
weights, metadata and third-party illustrations retain their source terms.
The vendored model includes its upstream MIT license and copyright notice.

## Dataset and weights

Audio, official metadata and pretrained model outputs originate from the
[Sound of Water dataset](https://huggingface.co/datasets/bpiyush/sound-of-water)
and [model release](https://huggingface.co/bpiyush/sound-of-water-models).
The manifest records per-recording source URLs and hashes. Reuse and
redistribution of recordings and weights follow the upstream distribution terms.

The visual extension downloads paired public videos from the same dataset.
Video files and extracted frame images stay local; the repository publishes
source URLs, hashes, provisional annotation coordinates and derived analysis.
Optional private review sheets show attributed frame crops for annotation
inspection. These coordinates were produced within this project. Their origin and author review
are documented in the [visual-reference methods](docs/EXPERIMENT_EXTENSION.md#visual-reference-without-a-ruler).

## Reference

Bagad et al. (2026). *The Sound of Water: Inferring Physical Properties from
Pouring Liquids*. IEEE Transactions on Pattern Analysis and Machine Intelligence.
https://doi.org/10.1109/TPAMI.2026.3690989

## Audio publication review (9 November 2026)

The dataset API at revision `12575460ee39d6adaebbe5aff531a5f4a24a627b`
has no `cardData.license` value and lists no LICENSE file. The README contains
a placeholder comment about adding a license. Redistribution terms are
unconfirmed. Sources: [dataset API](https://huggingface.co/api/datasets/bpiyush/sound-of-water)
and [dataset card](https://huggingface.co/datasets/bpiyush/sound-of-water).
The historical `legacy/early-spectral-analysis/data/pour_A.wav` and `pour_B.wav`
remain under the source terms. The website uses source-hosted preview audio
and local playback for the four generated comparisons. Public hosting of those
processed examples awaits clarification of redistribution permission.
