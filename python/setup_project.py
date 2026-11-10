"""Prepare public dataset inputs and regenerate the complete local experiment.

Run from the repository root after installing requirements-analysis.txt.
Audio is fetched directly from the original public dataset, never from a
private account. Source and 16 kHz analysis WAV hashes must match the manifest.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
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


def check_analysis_wav(path: Path, row: dict) -> None:
    """Platform-independent checks used when analysis bytes may differ."""
    fs, y = wavfile.read(path)
    if fs != 16000 or y.dtype != np.float32 or y.ndim != 1:
        raise ValueError(f"Unexpected analysis format: {row['clip']}; expected 16 kHz mono float32.")
    if len(y) != int(row['samples']) or not np.all(np.isfinite(y)):
        raise ValueError(f"Analysis length/value check failed: {row['clip']}.")


def prepare_recording(row: dict, cache: Path, exact_analysis: bool = True) -> tuple[str, bool]:
    """Return (clip, analysis_bytes_match_manifest).

    Source bytes are always exact. In portable mode, resampled float32 bytes may
    differ by CPU architecture; those files are kept after format/length checks
    and validated downstream through numeric table comparisons.
    """
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
    exact = target.exists() and sha256(target) == row['analysis_sha256']
    if not exact:
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
            exact = sha256(temporary) == row['analysis_sha256']
            if not exact and exact_analysis:
                raise ValueError(f"Analysis hash mismatch: {row['clip']}. Use the pinned analysis dependencies, "
                                 "or use --portable for numeric cross-platform checks.")
            check_analysis_wav(temporary, row)
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
    return row['clip'], exact


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers', type=int, default=4, choices=range(1, 9), metavar='1..8')
    parser.add_argument('--data-only', action='store_true', help='Download/verify WAVs without regenerating analysis outputs.')
    parser.add_argument('--portable', action='store_true', help='Check regenerated values numerically across platforms, preserving archived summaries; exact-byte mode remains the default.')
    args = parser.parse_args()
    cache = ROOT / '.cache' / 'source_audio'
    cache.mkdir(parents=True, exist_ok=True)
    with (ROOT / 'reference' / 'recording_manifest.csv').open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    differing = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = pool.map(lambda row: prepare_recording(row, cache, exact_analysis=not args.portable), rows)
        for number, (clip, exact) in enumerate(results, 1):
            note = '' if exact else ' (analysis bytes differ on this platform; numeric checks follow)'
            print(f'Verified {number}/{len(rows)}: {clip}{note}', flush=True)
            if not exact:
                differing.append(clip)
    if args.portable:
        import platform
        import scipy
        report = {
            'source_hashes_exact': len(rows),
            'analysis_hash_exact': len(rows) - len(differing),
            'analysis_bytes_differ': sorted(differing),
            'platform': platform.platform(),
            'machine': platform.machine(),
            'python': platform.python_version(),
            'numpy': np.__version__,
            'scipy': scipy.__version__,
            'scope': 'Differing analysis WAVs pass format/length checks; regenerated tables are compared numerically next.',
        }
        out = ROOT / 'outputs' / 'verification' / 'analysis_wav_portability.json'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + '\n')
        print(f"Analysis WAV bytes: {report['analysis_hash_exact']}/{len(rows)} exact; "
              f"differing: {', '.join(report['analysis_bytes_differ']) or 'none'}", flush=True)
    scripts = [['verify_inputs.py', '--portable'] if args.portable else ['verify_inputs.py'], ['verify_selection.py']]
    if not args.data_only:
        scripts += [['prepare_portable_analysis.py']] if args.portable else [['reproduce_analysis.py'], ['endpoint_diagnostic.py'], ['verify_generated_results.py']]
    for script, *extra in scripts:
        subprocess.run([sys.executable, str(ROOT / 'python' / script), *extra], cwd=ROOT, check=True)
    print('Audio verified.' if args.data_only else 'Setup complete. Open the project in MATLAB and run: R = run_project;')


if __name__ == '__main__':
    main()
