"""Read-only consistency audit for the published statistical revision."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from audit_statistics import digest, exact_sign_flip, holm

ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'experiments/statistical_audit'


def validate():
    status=json.loads((R/'status.json').read_text())
    for key,path in [('protocol_sha256','experiments/statistical_audit_protocol.json'),
                     ('script_sha256','python/audit_statistics.py'),
                     ('manifest_sha256','reference/recording_manifest.csv'),
                     ('frozen_score_sha256','results/score_coefficients.csv')]:
        assert status[key]==digest(ROOT/path)
    manifest=pd.read_csv(ROOT/'reference/recording_manifest.csv')
    audit=pd.read_csv(R/'split_audit.csv')
    dev=set(manifest.loc[manifest.role=='development','container_id'])
    assert audit.container_in_score_development.equals(audit.container_id.isin(dev))
    assert audit.loc[audit.role=='seen_test','container_in_score_development'].sum()==7
    assert not audit.loc[audit.role=='unseen_test','container_in_score_development'].any()
    tests=pd.read_csv(R/'paired_tests.csv')
    diffs=pd.read_csv(R/'paired_differences.csv')
    assert len(tests)==4 and len(diffs)==32
    for row in tests.itertuples():
        g=diffs[(diffs.role==row.role)&(diffs.method==row.method)]
        assert len(g)==g.container_id.nunique()==8
        np.testing.assert_allclose(exact_sign_flip(g.delta_cm),row.exact_p,atol=1e-14)
        np.testing.assert_allclose(g.delta_cm.mean(),row.delta_cm,atol=1e-14)
    np.testing.assert_allclose(holm(tests.exact_p),tests.holm_p_four_comparisons)
    folds=json.loads((R/'loco_folds.json').read_text())
    pool=manifest[manifest.role.isin(['development','seen_test'])]
    assert len(pool)==19 and pool.container_id.nunique()==len(folds)==11
    inner=pd.read_csv(R/'ridge_inner_cv.csv')
    for f in folds:
        held=f['held_out_container']
        assert held not in f['train_containers']
        assert set(f['train_containers'])==set(pool.container_id)-{held}
        assert f['inner_containers']==f['train_containers']
        assert set(f['test_clips'])==set(pool.loc[pool.container_id==held,'clip'])
        grid=inner[inner.held_out_container==held]
        assert len(grid)==6
        assert f['selected_penalty']==grid.loc[grid.mean_inner_container_log_mse.idxmin(),'ridge_penalty']
    clips=pd.read_csv(R/'loco_by_clip.csv')
    containers=pd.read_csv(R/'loco_by_container.csv')
    assert len(clips)==38 and len(containers)==22
    expected=clips.groupby(['method','container_id'])[['full_mae_cm','retained_mae_cm','delta_cm']].mean()
    pd.testing.assert_frame_equal(expected,containers.set_index(['method','container_id'])[expected.columns].sort_index(),atol=1e-12)
    areas=pd.read_csv(R/'aurc.csv');curves=pd.read_csv(R/'global_risk_coverage.csv')
    assert len(areas)==10
    for row in areas.itertuples():
        g=curves[(curves.role==row.role)&(curves.method==row.method)]
        assert len(g)==row.exported_points<=201
        assert np.all(np.diff(g.coverage)>0) and np.isclose(g.coverage.iloc[-1],1)
        np.testing.assert_allclose(g.risk_cm.iloc[-1],row.full_risk_cm,atol=1e-12)
    grid=pd.read_csv(R/'development_threshold_grid.csv')
    assert len(grid)==202
    np.testing.assert_array_equal(grid[grid.role=='seen_test'].threshold,grid[grid.role=='unseen_test'].threshold)
    return dict(status='passed',test_I_score_development_overlap='7/8 containers',
                exact_tests=4,sign_patterns_per_test=256,loco_containers=11,loco_recordings=19,
                global_threshold_curves=10,scope='Saved-data consistency and fold identities; not independent physical-level validation.')


if __name__=='__main__':
    result=validate()
    (ROOT/'verification/STATISTICAL_AUDIT_VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
