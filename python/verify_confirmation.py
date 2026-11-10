"""Check the published pre-registered confirmation without audio or model."""
from pathlib import Path
import hashlib
import json

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'experiments/confirmation'


def validate() -> dict:
    status = json.loads((OUT/'status.json').read_text())
    for key, path in [('protocol_sha256', 'experiments/confirmation_protocol.json'),
                      ('script_sha256', 'python/confirm_analysis.py'),
                      ('manifest_sha256', 'reference/confirmation_manifest.csv')]:
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != status[key]:
            raise ValueError(f'{path} changed after the confirmation results were computed')
    manifest = pd.read_csv(ROOT/'reference/confirmation_manifest.csv')
    used = pd.read_csv(ROOT/'reference/recording_manifest.csv')
    if set(manifest.container_id) & set(used.container_id) or len(manifest) != 33:
        raise ValueError('Confirmation containers must be new; expected 33 recordings.')
    audio = pd.read_csv(ROOT/'reference/confirmation_audio.csv')
    preds = list((ROOT/'reference/confirmation_predictions').glob('conf_*.csv'))
    if int(audio.included.sum()) != len(preds) or status['recordings_included'] != len(preds):
        raise ValueError('Predictions do not match included recordings.')
    run = json.loads((ROOT/'reference/confirmation_model_run.json').read_text())
    if max(run['adapter_check_max_wavelength_difference_cm'].values()) >= run['tolerance_cm']:
        raise ValueError('Adapter check exceeded tolerance.')
    tests = pd.read_csv(OUT/'primary_tests.csv')
    if tests.hypothesis.tolist() != ['H1_fill_position', 'H2_frame_level', 'H3_gain', 'H4_geometry']:
        raise ValueError('Primary hypotheses incomplete.')
    return {'status': 'passed', 'recordings': len(preds), 'containers': status['containers'],
            'confirmed': tests[tests.confirmed].hypothesis.tolist(),
            'not_confirmed': tests[~tests.confirmed].hypothesis.tolist(),
            'scope': 'Published identities and tables; no inference or recomputation.'}


if __name__ == '__main__':
    print(json.dumps(validate(), indent=2))
