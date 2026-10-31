from pathlib import Path
import pandas as pd, numpy as np, ast, hashlib, urllib.request, concurrent.futures, shutil
from scipy.io import wavfile
from scipy.signal import resample_poly

BASE=Path(__file__).resolve().parents[1]
OUT=BASE
(OUT/'data').mkdir(parents=True,exist_ok=True)
(OUT/'reference').mkdir(exist_ok=True)
sp=BASE/'reference'
rows=[]
for split,role,n in [('train','development',5),('test_I','seen_test',4),('test_II','unseen_test',4)]:
    d=pd.read_csv(sp/('official_'+split+'.csv'))
    d=d[(d.clean=='yes')&(d.flow_rate_appx=='constant')&((d.end_time-d.start_time).between(4,22))]
    d=d.assign(cnum=d.container_id.str.extract(r'(\d+)$')[0].astype(int))
    for shape in ['cylindrical','semiconical']:
        q=d[d['shape']==shape].sort_values(['cnum','item_id']).groupby('container_id',sort=False).head(1).head(n)
        for _,r in q.iterrows():r=r.to_dict();r.update(split=split,role=role);rows.append(r)
train=pd.read_csv(sp/'official_train.csv')
# Retain both original Report 1 recordings as descriptive development examples.
for item in ['VID_20240116_230040_2.1_16.7','VID_20240116_230132_3.3_18.8']:
    if item not in [r['item_id'] for r in rows]:
        r=train[train.item_id==item].iloc[0].to_dict();r.update(split='train',role='development');rows.append(r)
d=pd.read_csv(sp/'official_test_III.csv')
d=d[(d.clean=='yes')&(d.flow_rate_appx=='constant')&((d.end_time-d.start_time).between(4,22))]
d=d.assign(cnum=d.container_id.str.extract(r'(\d+)$')[0].astype(int)).sort_values(['cnum','item_id'])
for _,r in d[d['shape']=='bottleneck'].groupby('container_id',sort=False).head(1).head(4).iterrows():
    r=r.to_dict();r.update(split='test_III',role='shape_diagnostic');rows.append(r)
# Include an additional cylindrical case and a pointed conical geometry as qualitative tests.
for cid in ['container_3','container_15']:
    q=d[d.container_id==cid]
    if len(q):r=q.iloc[0].to_dict();r.update(split='test_III',role='shape_diagnostic');rows.append(r)
assert len(set(r['item_id'] for r in rows))==len(rows)


manifest=pd.read_csv(OUT/'reference/recording_manifest.csv')
assert [r['item_id'] for r in rows]==manifest.item_id.tolist(), 'Selection differs from the submitted manifest'
assert [r['role'] for r in rows]==manifest.role.tolist()
print('Metadata-only selection matches all',len(rows),'submitted recordings.')
