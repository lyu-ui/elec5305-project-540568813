"""Select the pre-registered confirmation set from metadata only (no audio).

Official Test II recordings from containers never used anywhere in this project
(neither upstream training nor the 33-recording study), with the original
eligibility rules: clean annotation, approximately constant flow, 4-22 s,
cylindrical or semiconical. Up to three recordings per container, taken in
item_id order. Writes reference/confirmation_manifest.csv.
"""
from pathlib import Path
import ast

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PER_CONTAINER = 3


def main():
    used = pd.read_csv(ROOT/'reference/recording_manifest.csv')
    train = pd.read_csv(ROOT/'reference/official_train.csv')
    d = pd.read_csv(ROOT/'reference/official_test_II.csv')
    d = d[(d.clean == 'yes') & (d.flow_rate_appx == 'constant') & ((d.end_time - d.start_time).between(4, 22))
          & d['shape'].isin(['cylindrical', 'semiconical'])
          & ~d.container_id.isin(set(used.container_id) | set(train.container_id))
          & ~d.item_id.isin(used.item_id)]
    d = d.assign(cnum=d.container_id.str.extract(r'(\d+)$')[0].astype(int)).sort_values(['cnum', 'item_id'])
    d = d.groupby('container_id', sort=False).head(PER_CONTAINER).reset_index(drop=True)
    rows = []
    for i, r in enumerate(d.itertuples(), 1):
        m = ast.literal_eval(r.measurements)
        rb, rt = m['diameter_bottom']/2, m['diameter_top']/2
        rows.append(dict(clip=f'conf_{i:02d}', item_id=r.item_id, container_id=r.container_id, shape=r.shape,
                         material=r.material, split='test_II', role='confirmation',
                         height_cm=m['net_height'], radius_cm=(rb+rt)/2, radius_bottom_cm=rb, radius_top_cm=rt,
                         start_time=r.start_time, end_time=r.end_time, video_id=r.video_id,
                         source_url=f'https://huggingface.co/datasets/bpiyush/sound-of-water/resolve/main/audios/{r.item_id}.wav',
                         audio_file=f'data/confirmation/conf_{i:02d}.wav'))
    out = pd.DataFrame(rows)
    assert out.item_id.is_unique and not set(out.container_id) & set(used.container_id)
    out.to_csv(ROOT/'reference/confirmation_manifest.csv', index=False)
    print(out.groupby('shape').agg(containers=('container_id', 'nunique'), recordings=('clip', 'size')))


if __name__ == '__main__':
    main()
