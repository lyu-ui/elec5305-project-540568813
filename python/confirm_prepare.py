"""Download and resample the pre-registered confirmation recordings.

Follows experiments/confirmation_protocol.json: official per-item WAVs, mono
mean, 16 kHz float32 exactly as setup_project.py. Source and analysis SHA-256
are recorded at first download in reference/confirmation_audio.csv; later runs
verify the source bytes against that record. Exclusions follow the protocol.
"""
from pathlib import Path
import hashlib
import math
import urllib.request

import numpy as np
import pandas as pd
from scipy.io import wavfile
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT/'reference/confirmation_audio.csv'


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main():
    m = pd.read_csv(ROOT/'reference/confirmation_manifest.csv')
    known = pd.read_csv(RECORD).set_index('clip') if RECORD.exists() else None
    cache = ROOT/'.cache/confirmation_audio'
    cache.mkdir(parents=True, exist_ok=True)
    rows = []
    for r in m.itertuples():
        row = dict(clip=r.clip, item_id=r.item_id, included=True, exclusion_reason='')
        try:
            src = cache/f'{r.item_id}.wav'
            if not src.exists():
                req = urllib.request.Request(r.source_url, headers={'User-Agent': 'PouringSoundResearch/1.0'})
                with urllib.request.urlopen(req, timeout=120) as resp:
                    src.write_bytes(resp.read())
            data = src.read_bytes()
            row['source_sha256'] = sha(data)
            if known is not None and known.loc[r.clip, 'source_sha256'] != row['source_sha256']:
                raise ValueError('source bytes differ from the first recorded download')
            fs, raw = wavfile.read(src)
            if raw.dtype != np.int16:
                raise ValueError(f'unexpected sample type {raw.dtype}')
            x = raw.astype(np.float64)/32768.0
            if x.ndim == 2:
                x = x.mean(axis=1)
            g = math.gcd(fs, 16000)
            y = resample_poly(x, 16000//g, fs//g).astype(np.float32)
            dur = len(y)/16000
            row.update(source_fs=fs, source_channels=1 if raw.ndim == 1 else raw.shape[1], samples=len(y), duration_s=dur,
                       metadata_duration_s=r.end_time - r.start_time)
            if abs(dur - (r.end_time - r.start_time)) > 0.1:
                raise ValueError(f'duration {dur:.3f} s differs from metadata {r.end_time - r.start_time:.3f} s by > 0.1 s')
            out = ROOT/r.audio_file
            out.parent.mkdir(parents=True, exist_ok=True)
            wavfile.write(out, 16000, y)
            row['analysis_sha256'] = sha(out.read_bytes())
        except Exception as exc:  # protocol exclusion, always reported
            row.update(included=False, exclusion_reason=str(exc))
        rows.append(row)
        print(row['clip'], 'ok' if row['included'] else 'EXCLUDED: ' + row['exclusion_reason'], flush=True)
    out = pd.DataFrame(rows)
    if known is None:
        out.to_csv(RECORD, index=False)
    print(f"{int(out.included.sum())}/{len(out)} recordings included")


if __name__ == '__main__':
    main()
