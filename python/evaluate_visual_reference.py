"""Compare frozen audio predictions with explicitly provisional image proxies.

No centimetre-accuracy output is produced. Pixel ranges capture annotation
ambiguity only; they do not calibrate refraction, perspective, or true height.
"""
from pathlib import Path
import hashlib
import itertools
import json

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'experiments/results'


def load_human_review(annotation_path, review_path=None):
    """Validate author confirmation without changing frozen AI coordinates.

    Confirmation covers displayed green water-surface bands only. It does not
    certify rim/base geometry, exclusions, physical height, or independence.
    """
    if review_path is None:
        review_path = annotation_path.with_name('visual_human_review.json')
    if not review_path.exists():
        return None, set()
    review = json.loads(review_path.read_text())
    if review['annotation_sha256'] != hashlib.sha256(annotation_path.read_bytes()).hexdigest():
        raise ValueError('Human review refers to a different annotation version.')
    if review['scope'] != 'displayed_green_water_surface_bands_only':
        raise ValueError('Unsupported human-review scope.')
    annotations = json.loads(annotation_path.read_text())
    confirmed = set()
    for clip, frames in review['confirmed_frames'].items():
        if clip not in annotations['clips']:
            raise ValueError('Human review names an unknown clip.')
        for frame in frames:
            if type(frame) is not int or not 1 <= frame <= 9 or (clip, frame) in confirmed:
                raise ValueError('Invalid or duplicate reviewed frame.')
            if annotations['clips'][clip]['water_y_bounds'][frame-1] is None:
                raise ValueError('An excluded frame has no green water band to confirm.')
            confirmed.add((clip, frame))
    return review, confirmed


def relative_bounds(rim, base, water):
    values = np.asarray([rim, base, water], dtype=float)
    if values.shape != (3,2) or not np.isfinite(values).all() or np.any(values[:,0] > values[:,1]):
        raise ValueError('Finite ordered pixel intervals required.')
    if base[0] <= rim[1]:
        raise ValueError('Base must lie below rim in image coordinates.')
    corners = [(b-s)/(b-t) for t,b,s in itertools.product(rim,base,water)]
    t,b,s = values.mean(axis=1)
    return (b-s)/(b-t), min(corners), max(corners)


def error_bounds(pred, lower, upper):
    return max(lower-pred, pred-upper, 0), max(abs(pred-lower), abs(pred-upper))


def main():
    annotation_path = ROOT/'experiments/visual_annotations.json'
    annotations = json.loads(annotation_path.read_text())
    review_path = ROOT/'experiments/visual_human_review.json'
    review, confirmed = load_human_review(annotation_path, review_path)
    manifest = pd.read_csv(OUT/'visual_frame_manifest.csv')
    source = pd.read_csv(ROOT/'reference/recording_manifest.csv').set_index('clip')
    if len(manifest) != 72 or manifest.duplicated(['clip','frame']).any():
        raise ValueError('Every planned video/time must occur once.')
    rows = []
    # First validate all decisions and images. Only then open model predictions.
    for r in manifest.itertuples():
        spec = annotations['clips'][r.clip]
        image = ROOT/r.image_path
        if hashlib.sha256(image.read_bytes()).hexdigest() != r.image_sha256:
            raise ValueError('Visual evidence image hash mismatch.')
        water = spec['water_y_bounds'][r.frame-1]
        row = dict(clip=r.clip, container_id=r.container_id, frame=r.frame,
                   actual_audio_time_s=r.actual_audio_time_s, fraction=r.fraction,
                   status='ai_provisional' if water else 'excluded',
                   human_review_status='author_confirmed_water_band' if (r.clip, r.frame) in confirmed else 'not_reviewed',
                   reason=spec['caution'] if water else spec.get('excluded_all',spec.get('excluded',{}).get(str(r.frame))))
        if not row['reason']:
            raise ValueError('Every inclusion/exclusion must have a reason.')
        if water:
            rim, base = spec['rim_y_bounds'], spec['base_y_bounds']
            midpoint, lower, upper = relative_bounds(rim,base,water)
            row.update(rim_y_low=rim[0],rim_y_high=rim[1],base_y_low=base[0],base_y_high=base[1],
                       water_y_low=water[0],water_y_high=water[1],
                       visual_fraction_midpoint=midpoint,visual_fraction_lower=lower,visual_fraction_upper=upper)
        rows.append(row)
    predictions = {}
    for row in rows:
        if row['status'] == 'excluded':
            continue
        clip, t = row['clip'], row['actual_audio_time_s']
        if clip not in predictions:
            predictions[clip] = pd.read_csv(ROOT/'reference/model_predictions'/f'{clip}.csv')
        p = predictions[clip]
        if not p.time_s.iloc[0] <= t <= p.time_s.iloc[-1]:
            raise ValueError('Refusing to extrapolate model estimates.')
        height, duration = source.loc[clip, ['height_cm','duration_s']]
        pred = 1-np.interp(t, p.time_s, p.length_pred_cm)/height
        row['audio_model_fraction'] = pred
        row['assumed_fraction'] = t/duration
        mid, lo, hi = [row[f'visual_fraction_{k}'] for k in ['midpoint','lower','upper']]
        for name, estimate in [('model',pred),('assumed',t/duration)]:
            low_error, high_error = error_bounds(estimate,lo,hi)
            row[f'{name}_proxy_abs_difference_pp'] = abs(estimate-mid)*100
            row[f'{name}_difference_lower_pp'] = low_error*100
            row[f'{name}_difference_upper_pp'] = high_error*100
        row['visual_midpoint_band'] = 'low' if mid<1/3 else 'middle' if mid<2/3 else 'high'
        row['band_boundary_ambiguous'] = any(lo<=v<=hi for v in [1/3,2/3])
    frame = pd.DataFrame(rows)
    frame.to_csv(OUT/'visual_by_frame.csv',index=False)
    summaries = []
    for clip, g in frame.groupby('clip',sort=False):
        valid = g[g.status=='ai_provisional']
        result = dict(clip=clip, planned_frames=len(g), usable_provisional_frames=len(valid),
                      excluded_frames=int((g.status=='excluded').sum()),
                      human_reviewed_frames=int(g.human_review_status.eq('author_confirmed_water_band').sum()))
        if len(valid):
            for name in ['model','assumed']:
                result[f'{name}_mean_proxy_difference_pp'] = float(valid[f'{name}_proxy_abs_difference_pp'].mean())
                result[f'{name}_annotation_lower_pp'] = float(valid[f'{name}_difference_lower_pp'].mean())
                result[f'{name}_annotation_upper_pp'] = float(valid[f'{name}_difference_upper_pp'].mean())
            result['model_visual_spearman'] = float(spearmanr(valid.audio_model_fraction,valid.visual_fraction_midpoint).statistic)
            result['visual_time_spearman'] = float(spearmanr(valid.actual_audio_time_s,valid.visual_fraction_midpoint).statistic)
        summaries.append(result)
    summary = pd.DataFrame(summaries)
    summary.to_csv(OUT/'visual_by_clip.csv',index=False)
    usable = frame[frame.status=='ai_provisional']
    by_band = usable.groupby(['clip','visual_midpoint_band']).agg(
        frames=('frame','size'),model_proxy_difference_pp=('model_proxy_abs_difference_pp','mean'),
        assumed_proxy_difference_pp=('assumed_proxy_abs_difference_pp','mean'),
        ambiguous_band_assignments=('band_boundary_ambiguous','sum')).reset_index()
    by_band.to_csv(OUT/'visual_by_level_band.csv',index=False)
    report = dict(status='exploratory_AI_assisted_visual_proxy', planned_videos=8, planned_frames=72,
                  usable_videos=int((summary.usable_provisional_frames>0).sum()),
                  usable_provisional_frames=len(usable), excluded_frames=72-len(usable), human_reviewed_frames=len(confirmed),
                  human_review_scope='displayed green water-surface bands only; project-author confirmation',
                  human_review_record_sha256=hashlib.sha256(review_path.read_bytes()).hexdigest() if review else None,
                  independent_blinded_review=False,
                  rim_and_base_human_review_status='not_explicitly_confirmed',
                  status_definition='ai_provisional retains AI origin and uncalibrated measurement status; human review is recorded separately.',
                  annotation_sha256=hashlib.sha256(annotation_path.read_bytes()).hexdigest(),
                  equal_clip_model_proxy_difference_pp=float(summary.model_mean_proxy_difference_pp.mean()),
                  equal_clip_assumed_proxy_difference_pp=float(summary.assumed_mean_proxy_difference_pp.mean()),
                  unit='percentage points of image-relative visible filling; not centimetres',
                  limitations=['Green water-surface bands were confirmed by the project author after exploratory results were available; this is not independent blinded validation.' if confirmed else 'AI annotations have not received human review.',
                    'Confirmation does not separately certify blue rim/base bands or excluded images.',
                    'Image-relative fraction can differ systematically from physical height fraction.',
                    'Pixel bounds are sensitivity ranges, not confidence intervals or calibrated metrology.',
                    'This reuses seen-test videos; it adds a modality, not new independent test containers.',
                    'Frames are dependent and missingness is visibility-dependent; no framewise significance test.'])
    (OUT/'visual_status.json').write_text(json.dumps(report,indent=2)+'\n')
    print(summary.to_string(index=False))
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
