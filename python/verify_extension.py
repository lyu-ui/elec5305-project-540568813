"""Audit saved extension tables without downloading audio, video or the network."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from run_extension import interval
from evaluate_visual_reference import relative_bounds, load_human_review

ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'experiments/results'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate():
    protocol=json.loads((ROOT/'experiments/extension_protocol.json').read_text())
    run=json.loads((R/'noise_run.json').read_text())
    for key,path in [('protocol_sha256','experiments/extension_protocol.json'),
                     ('coefficients_sha256','results/score_coefficients.csv'),
                     ('manifest_sha256','reference/recording_manifest.csv'),
                     ('inference_adapter_sha256','python/infer_official.py'),
                     ('experiment_script_sha256','python/run_extension.py')]:
        assert run[key]==digest(ROOT/path),key
    assert run['completed'] and run['clean_runs']==16 and run['noisy_runs']==144
    assert run['strict_checkpoint_keys']==215 and run['eval_mode']
    meta=pd.read_csv(ROOT/'reference/recording_manifest.csv')
    expected=set(meta.loc[meta.role.isin(protocol['noise']['roles']),'clip'])
    trials=pd.read_csv(R/'noise_trials.csv')
    assert len(trials)==160 and set(trials['clip'])==expected
    assert not trials.duplicated(['clip','condition','snr_db','seed']).any()
    for clip,g in trials.groupby('clip'):
        assert len(g[g.condition=='clean'])==1
        pairs=set(map(tuple,g[g.condition=='gaussian'][['snr_db','seed']].to_numpy()))
        assert pairs=={(s,k) for s in protocol['noise']['snr_db'] for k in protocol['noise']['seeds']}
    noisy=trials[trials.condition=='gaussian']
    assert (noisy.achieved_snr_db-noisy.snr_db).abs().max()<1e-4
    for name in ['rank70_coverage','fixed_coverage','negative_length_fraction']:
        assert trials[name].between(0,1).all()
    np.testing.assert_allclose(trials.rank70_coverage,np.ceil(.7*trials.frames)/trials.frames)
    assert np.isfinite(trials[['reference_mae_cm','rank70_reference_mae_cm','score_mean']]).all().all()
    assert trials.input_float32_sha256.str.fullmatch('[0-9a-f]{64}').all()
    audit=pd.read_csv(R/'clean_inference_audit.csv')
    assert set(audit['clip'])==expected and len(audit)==16
    assert audit.max_wavelength_difference_cm.max()<protocol['noise']['clean_cache_max_wavelength_difference_cm']
    summary=pd.read_csv(R/'noise_summary.csv')
    assert len(summary)==8
    for row in summary.itertuples():
        g=trials[(trials.role==row.role)&(trials.condition==row.condition)]
        if row.condition!='clean':g=g[g.snr_db==row.snr_db]
        by_clip=g.groupby('clip').reference_mae_cm.mean()
        clean=trials[(trials.role==row.role)&(trials.condition=='clean')].set_index('clip').reference_mae_cm
        delta=by_clip-clean
        np.testing.assert_allclose([row.reference_mae_cm,row.paired_change_from_clean_cm],
                                   [by_clip.mean(),delta.mean()],atol=1e-12)
        containers=meta.set_index('clip').loc[delta.index,'container_id']
        clustered=pd.DataFrame({'delta':delta,'container_id':containers}).groupby('container_id').delta.mean()
        np.testing.assert_allclose([row.ci_low_cm,row.ci_high_cm],interval(clustered),atol=1e-12)
    phases=pd.read_csv(R/'noise_by_phase.csv')
    assert len(phases)==480
    assert set(phases.phase)=={'early','middle','late'}
    assert (phases.frames>0).all()
    endpoint=pd.read_csv(R/'endpoint_by_clip.csv')
    assert len(endpoint)==132 and set(endpoint['clip'])==set(meta['clip'])
    assert set(endpoint.window_s)=={0,.1,.2,.5}
    for clip,g in endpoint.groupby('clip'):
        base=g[g.window_s==0].iloc[0]
        np.testing.assert_allclose(g.reference_mae_cm-base.reference_mae_cm,g.delta_mae_cm,atol=1e-12)
        np.testing.assert_allclose((base.endpoint_wavelength_cm-g.endpoint_wavelength_cm)/4,g.global_shift_cm,atol=1e-12)
    visual=pd.read_csv(R/'visual_by_frame.csv')
    vmanifest=pd.read_csv(R/'visual_frame_manifest.csv')
    annotation_path=ROOT/'experiments/visual_annotations.json'
    annotations=json.loads(annotation_path.read_text())
    status=json.loads((R/'visual_status.json').read_text())
    assert status['annotation_sha256']==digest(annotation_path)
    assert len(visual)==len(vmanifest)==72
    assert not visual.duplicated(['clip','frame']).any()
    assert visual.groupby('clip').size().eq(9).all()
    assert visual.reason.notna().all()
    review_path=ROOT/'experiments/visual_human_review.json'
    review,confirmed=load_human_review(annotation_path,review_path)
    assert review is not None
    assert status['human_review_record_sha256']==digest(review_path)
    assert status['human_reviewed_frames']==len(confirmed)==46
    assert status['independent_blinded_review'] is False
    assert status['rim_and_base_human_review_status']=='not_explicitly_confirmed'
    for r in visual.itertuples():
        expected='author_confirmed_water_band' if (r.clip,r.frame) in confirmed else 'not_reviewed'
        assert r.human_review_status==expected
    usable=visual[visual.status=='ai_provisional']
    assert len(usable)==status['usable_provisional_frames']==46
    assert visual.status.eq('excluded').sum()==status['excluded_frames']==26
    assert vmanifest.nearest_frame_error_s.abs().max()<.035
    for r in usable.itertuples():
        a=annotations['clips'][r.clip]
        vals=relative_bounds(a['rim_y_bounds'],a['base_y_bounds'],a['water_y_bounds'][r.frame-1])
        np.testing.assert_allclose(vals,[r.visual_fraction_midpoint,r.visual_fraction_lower,r.visual_fraction_upper])
    videos=json.loads((R/'video_audit.json').read_text())
    assert len(videos)==8 and min(r['audio_correlation'] for r in videos)>.9997
    assert all(r['audio_alignment_lag_samples']==0 for r in videos)
    return dict(status='passed',noise_trials=160,clean_controls=16,noisy_conditions=144,
                endpoint_recording_conditions=132,video_frames_accounted_for=72,
                provisional_visual_labels=46,visual_exclusions=26,human_reviewed_visual_labels=46,
                human_review_scope='Project-author confirmation of green water bands only; not independent blinded or calibrated validation.',
                max_clean_wavelength_difference_cm=float(audit.max_wavelength_difference_cm.max()),
                max_added_snr_error_db=float((noisy.achieved_snr_db-noisy.snr_db).abs().max()),
                scope='Saved-data consistency, identities and experimental coverage; no new MATLAB execution or calibrated ground truth.')


if __name__=='__main__':
    result=validate()
    path=ROOT/'verification/EXPERIMENT_EXTENSION_VALIDATION.json'
    path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
