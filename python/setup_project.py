"""Prepare public dataset inputs and regenerate the complete local experiment.

Run from the repository root after installing requirements-analysis.txt.
Audio is fetched directly from the original public dataset, never from a
private account. Source and 16 kHz analysis WAV hashes must match the manifest.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_recording(row: dict, cache: Path) -> str:
    source = cache / (row['item_id'] + '.wav')
    if not source.exists() or sha256(source) != row['source_sha256']:
        request = urllib.request.Request(row['source_url'], headers={'User-Agent': 'PouringSoundResearch/1.0'})
        with urllib.request.urlopen(request, timeout=90) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != row['source_sha256']:
            raise ValueError(f"Source hash mismatch: {row['clip']}; the upstream file may have changed.")
        source.write_bytes(data)
    target = ROOT / row['audio_file']
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or sha256(target) != row['analysis_sha256']:
        fs, raw = wavfile.read(source)
        if str(fs) != row['source_fs'] or raw.dtype != np.int16:
            raise ValueError(f"Unexpected source format: {row['clip']}; expected the recorded 16-bit PCM input.")
        x = raw.astype(np.float64) / 32768.0
        if x.ndim == 2:
            x = x.mean(axis=1)
        factor = math.gcd(fs, 16000)
        analysis = resample_poly(x, 16000 // factor, fs // factor).astype(np.float32)
        with tempfile.NamedTemporaryFile(dir=target.parent, suffix='.wav', delete=False) as handle:
            temporary = Path(handle.name)
        try:
            wavfile.write(temporary, 16000, analysis)
            if sha256(temporary) != row['analysis_sha256']:
                raise ValueError(f"Analysis hash mismatch: {row['clip']}. Use the pinned analysis dependencies.")
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    # Preserve the original-sample-rate inputs for the historical diagnostic.
    legacy_name = row.get('original_report1_name', '')
    if legacy_name:
        destination = ROOT / 'legacy' / 'early-spectral-analysis' / 'data' / legacy_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists() or sha256(destination) != row['source_sha256']:
            shutil.copyfile(source, destination)
    return row['clip']


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers', type=int, default=4, choices=range(1, 9), metavar='1..8')
    parser.add_argument('--data-only', action='store_true', help='Download/verify WAVs without regenerating analysis outputs.')
    args = parser.parse_args()
    cache = ROOT / '.cache' / 'source_audio'
    cache.mkdir(parents=True, exist_ok=True)
    with (ROOT / 'reference' / 'recording_manifest.csv').open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for number, clip in enumerate(pool.map(lambda row: prepare_recording(row, cache), rows), 1):
            print(f'Verified {number}/{len(rows)}: {clip}', flush=True)
    scripts = ['verify_inputs.py', 'verify_selection.py']
    if not args.data_only:
        scripts += ['reproduce_analysis.py', 'endpoint_diagnostic.py', 'verify_generated_results.py']
    for script in scripts:
        subprocess.run([sys.executable, str(ROOT / 'python' / script)], cwd=ROOT, check=True)
    print('Audio verified.' if args.data_only else 'Setup complete. Open the project in MATLAB and run: R = run_project;')


if __name__ == '__main__':
    main()
