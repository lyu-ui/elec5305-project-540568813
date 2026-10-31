"""Check all fixed audio inputs against submitted hashes, and split integrity."""
from pathlib import Path
import pandas as pd,hashlib
root=Path(__file__).resolve().parents[1];d=pd.read_csv(root/'reference/recording_manifest.csv')
for r in d.itertuples():
    assert hashlib.sha256((root/r.audio_file).read_bytes()).hexdigest()==r.analysis_sha256,r.clip
tr=pd.read_csv(root/'reference/official_train.csv')
assert d.item_id.is_unique
assert not set(d[d.role=='unseen_test'].container_id)&set(tr.container_id)
assert not set(d[d.role=='development'].video_id)&set(d[d.role.isin(['seen_test','unseen_test'])].video_id)
print('All 33 audio hashes and the declared split constraints passed.')
