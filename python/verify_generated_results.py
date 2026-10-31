"""Verify regenerated CSV bytes against the recorded pinned Python environment."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[1]
expected = json.loads((root / 'reference' / 'generated_results_sha256.json').read_text())
failures = []
for relative, digest in expected['files'].items():
    path = root / relative
    if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        failures.append(relative)
if failures:
    raise AssertionError('Generated CSVs differ from the recorded environment: ' + ', '.join(failures) + '. Check the pinned analysis dependencies before using these tables as the MATLAB reference.')
print(f"All {len(expected['files'])} regenerated CSV tables match the recorded reference hashes.")
