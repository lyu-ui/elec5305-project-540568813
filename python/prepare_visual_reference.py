"""Recover paired public videos and extract fixed-time frames without predictions.

Downloads stay in .cache; inspection images stay in outputs. No video/audio is
uploaded by this script. Visual annotations must describe visibility and bounds.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import urllib.request

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
from scipy.io import wavfile
from scipy.signal import correlate, correlation_lags

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    'clip_11': '14110c6d995aa145738bbb4d544a24b4032d12c3a47dc6a67f246aed74885e7e',
    'clip_12': '4cf7b1cc27ff42490820b203e668f724fd8bd26247d250f8e131dcbc36d44ed4',
    'clip_13': '324a33c3c93650c72b209075d042c699777a039cdf30cbcd6ca086636561611b',
    'clip_14': '57dea6384cd494f244fedbbb316c1ee450307f5c4db434d8737fd14f9cf3a876',
    'clip_15': 'bb5264f6cc46159b13fa5e6b11e73df42e381aaa4dd72728eb96c0d57d0ef6ca',
    'clip_16': 'abb7be7e693941220bc8106535c98a556caa33487903cca849c4fff53582d44b',
    'clip_17': '44db9f63c4207e83b2f4a67de8fb9f6bc060f28fa1d04565dd94b37618e9c165',
    'clip_18': 'f3372e67a53f27485c2636be5251ac741abad9f69f42089ea0c3fe2c4cd6ddda'
}


def probe(path, stream):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams',stream,
                     '-show_frames','-show_entries','frame=best_effort_timestamp_time',
                     '-of','json',str(path)]))['frames']


def main():
    cache = ROOT/'.cache/visual_videos'
    out = ROOT/'outputs/visual_reference'
    cache.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    rows, audit = [], []
    manifest = pd.read_csv(ROOT/'reference/recording_manifest.csv')
    fractions = json.loads((ROOT/'experiments/extension_protocol.json').read_text())['visual']['fractions_of_audio_duration']
    for r in manifest[manifest.role=='seen_test'].itertuples():
        url = f'https://huggingface.co/datasets/bpiyush/sound-of-water/resolve/main/videos/{r.item_id}.mp4'
        path = cache/f'{r.clip}.mp4'
        if not path.exists():
            urllib.request.urlretrieve(url, path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != EXPECTED[r.clip]:
            raise ValueError(f'{r.clip}: public video identity changed.')
        vt = np.array([float(f['best_effort_timestamp_time']) for f in probe(path,'v:0')])
        at = np.array([float(f['best_effort_timestamp_time']) for f in probe(path,'a:0')])
        actual_audio = np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(path),
                             '-vn','-ac','1','-ar','16000','-f','f32le','-']), dtype='<f4').astype(float)
        fs, original = wavfile.read(ROOT/r.audio_file)
        original = original.astype(float)
        original -= original.mean()
        actual_audio -= actual_audio.mean()
        cc = correlate(actual_audio, original, method='fft')
        lags = correlation_lags(len(actual_audio),len(original))
        allowed = np.abs(lags)<=1600
        lag = int(lags[allowed][np.argmax(cc[allowed])])
        start_a, start_o = max(0,lag), max(0,-lag)
        n = min(len(actual_audio)-start_a, len(original)-start_o)
        corr = float(np.corrcoef(actual_audio[start_a:start_a+n], original[start_o:start_o+n])[0,1])
        if corr < .95 or abs(lag)>8:
            raise ValueError(f'{r.clip}: audio alignment needs review: lag={lag}, r={corr}.')
        # The decoded audio begins at at[0]; cross-correlation verifies that the
        # manifest WAV has the same audio origin to within 0.5 ms.
        target = np.array(fractions)*r.duration_s+at[0]+lag/fs
        indexes = [int(np.argmin(np.abs(vt-t))) for t in target]
        folder = out/r.clip
        folder.mkdir(exist_ok=True)
        select = '+'.join(f'eq(n\\,{i})' for i in indexes)
        subprocess.run(['ffmpeg','-v','error','-y','-i',str(path),'-vf',f'select={select}',
                        '-fps_mode','vfr',str(folder/'frame_%02d.png')],check=True)
        sheet = Image.new('RGB',(270*3,504*3),'#ffffff')
        draw = ImageDraw.Draw(sheet)
        for j, (frac,index) in enumerate(zip(fractions,indexes),1):
            image_path = folder/f'frame_{j:02d}.png'
            image = Image.open(image_path).convert('RGB')
            if image.size != (270,480):
                raise ValueError('Unexpected resolution; inspect before labeling.')
            x, y = (j-1)%3*270, (j-1)//3*504
            sheet.paste(image,(x,y+24))
            actual_time = float(vt[index]-at[0]-lag/fs)
            draw.text((x+4,y+5),f'{r.clip} F{j:02d}  t={actual_time:.3f}s',fill='black')
            rows.append(dict(clip=r.clip, container_id=r.container_id, frame=j, fraction=frac,
                             target_audio_time_s=frac*r.duration_s, video_frame_index=index,
                             video_pts_s=float(vt[index]), actual_audio_time_s=actual_time,
                             nearest_frame_error_s=actual_time-frac*r.duration_s,
                             image_sha256=hashlib.sha256(image_path.read_bytes()).hexdigest(),
                             image_path=str(image_path.relative_to(ROOT))))
        sheet.save(out/f'{r.clip}_contact.png')
        audit.append(dict(clip=r.clip, url=url, video_sha256=digest, audio_first_pts_s=float(at[0]),
                          audio_alignment_lag_samples=lag, audio_correlation=corr, frames_sampled=len(indexes)))
        print(r.clip, 'aligned', corr, 'lag', lag, flush=True)
    pd.DataFrame(rows).to_csv(ROOT/'experiments/results/visual_frame_manifest.csv',index=False)
    (ROOT/'experiments/results/video_audit.json').write_text(json.dumps(audit,indent=2)+'\n')


if __name__ == '__main__':
    main()
