"""Run the frozen released model on the pre-registered confirmation recordings.

First repeats inference on clip_01, clip_19 and clip_24 and stops unless the
maximum wavelength difference from the cached predictions is below 0.01 cm
(experiments/confirmation_protocol.json). Then writes per-recording
predictions in the same format as reference/model_predictions/.

Requires python/requirements-inference.txt and python/checkpoint.pth
(python python/download_model.py).
"""
from pathlib import Path
import hashlib
import json
import time

import numpy as np
import pandas as pd
import torch
from scipy.io import wavfile
from transformers import Wav2Vec2Config

from infer_official import InferenceModel

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = ROOT/'python/checkpoint.pth'
CONFIG = ROOT/'python/wav2vec2_config.json'
EXPECTED = '2fa3d8cec1488ee65bb5a6e30f1b79716d8243bbe4ddc4c0687ce2a02c84303c'
TOLERANCE_CM = 0.01


def load_model():
    torch.set_num_threads(4)
    torch.manual_seed(0)
    cfg = Wav2Vec2Config.from_json_file(str(CONFIG))
    cfg._attn_implementation = 'eager'
    model = InferenceModel(cfg)
    if hashlib.sha256(CHECKPOINT.read_bytes()).hexdigest() != EXPECTED:
        raise RuntimeError('Checkpoint hash mismatch.')
    state = torch.load(CHECKPOINT, map_location='cpu', weights_only=True)
    model.load_state_dict(state, strict=True)
    return model.eval(), len(state)


def predict(model, path, height_cm):
    fs, x = wavfile.read(path)
    assert fs == 16000
    x = x.astype(np.float32)
    x = (x - x.mean())/np.sqrt(x.var() + 1e-7)
    with torch.inference_mode():
        prob = model(torch.from_numpy(x[None, :]), len(x)/fs)[0]
    lam = (prob @ torch.linspace(0, 100, 64)).numpy()
    t = (np.arange(len(lam))*320 + 200)/fs
    length = (lam - lam[-1])/4
    ref = height_cm*(1 - t/(len(x)/fs))
    return pd.DataFrame(dict(time_s=t, wavelength_cm=lam, pitch_hz=34000/lam, length_pred_cm=length,
                             length_ref_cm=ref, abs_error_cm=np.abs(length - ref)))


def main():
    model, keys = load_model()
    meta = pd.read_csv(ROOT/'reference/recording_manifest.csv').set_index('clip')
    check = {}
    for clip in ['clip_01', 'clip_19', 'clip_24']:
        p = predict(model, ROOT/meta.loc[clip, 'audio_file'], meta.loc[clip, 'height_cm'])
        cached = pd.read_csv(ROOT/'reference/model_predictions'/f'{clip}.csv')
        diff = float(np.max(np.abs(p.wavelength_cm.to_numpy() - cached.wavelength_cm.to_numpy())))
        check[clip] = diff
        print(f'adapter check {clip}: max wavelength difference {diff:.2e} cm', flush=True)
    if max(check.values()) >= TOLERANCE_CM:
        raise SystemExit('Adapter check failed; confirmation inference not run.')
    conf = pd.read_csv(ROOT/'reference/confirmation_manifest.csv')
    audio = pd.read_csv(ROOT/'reference/confirmation_audio.csv').set_index('clip')
    out = ROOT/'reference/confirmation_predictions'
    out.mkdir(exist_ok=True)
    for r in conf.itertuples():
        if not audio.loc[r.clip, 'included']:
            continue
        tic = time.time()
        p = predict(model, ROOT/r.audio_file, r.height_cm)
        p.to_csv(out/f'{r.clip}.csv', index=False)
        print(r.clip, r.container_id, 'frames', len(p), 'seconds', round(time.time() - tic, 2), flush=True)
    run = dict(torch=torch.__version__, transformers=__import__('transformers').__version__, numpy=np.__version__,
               scipy=__import__('scipy').__version__, checkpoint_sha256=EXPECTED, strict_checkpoint_keys=keys,
               adapter_check_max_wavelength_difference_cm=check, tolerance_cm=TOLERANCE_CM,
               platform=__import__('platform').platform())
    (ROOT/'reference/confirmation_model_run.json').write_text(json.dumps(run, indent=2) + '\n')
    print('done')


if __name__ == '__main__':
    main()
