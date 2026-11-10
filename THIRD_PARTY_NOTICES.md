# Third-party sources and notices

## Sound of Water code

The upstream model implementation in `python/upstream/model.py` comes from
[bpiyush/SoundOfWater](https://github.com/bpiyush/SoundOfWater).
Its MIT license and copyright notice are preserved in
`python/upstream/LICENSE`. The exact upstream commit is recorded in
`reference/model_run.json`.

## Scope of the project MIT license

The root LICENSE covers original project code and documentation only.
It does not relicense dataset audio/video, pretrained weights, upstream metadata,
or third-party illustrations. The vendored model retains the original upstream
MIT copyright notice separately. Existing third-party assets keep their own terms.

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
inspection. These coordinates are project annotations, not labels provided or
certified by the dataset authors. Their origin and subsequent author review
are documented in the [visual-reference methods](docs/EXPERIMENT_EXTENSION.md#visual-reference-without-a-ruler).

## Reference

Bagad et al. (2026). *The Sound of Water: Inferring Physical Properties from
Pouring Liquids*. IEEE Transactions on Pattern Analysis and Machine Intelligence.
https://doi.org/10.1109/TPAMI.2026.3690989

## Project scope

The original analysis, reliability diagnostics and documentation are by
Yueyao Lyu. This package does not include university report PDFs, Live Script
reports, teacher feedback, marking rubrics or course sample reports.

## Audio publication review (9 November 2026)

The dataset API at revision `12575460ee39d6adaebbe5aff531a5f4a24a627b`
has no `cardData.license` value and lists no LICENSE file. The README contains
a placeholder comment about adding a license, not an express redistribution
grant. Sources: [dataset API](https://huggingface.co/api/datasets/bpiyush/sound-of-water)
and [dataset card](https://huggingface.co/datasets/bpiyush/sound-of-water).
This observation does not determine every possible legal basis for use.

The repository already contains the historical `legacy/early-spectral-analysis/data/pour_A.wav`
and `pour_B.wav`; their presence does not establish permission to publish new
derivatives. This revision adds no new hosted audio copies. The website offers
an original-source preview and local playback of the four generated comparison
files. Selecting local files does not upload them. Public MP3/OGG redistribution
of the four processed examples remains pending clarification of the source terms.
