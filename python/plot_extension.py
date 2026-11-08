"""Render extension figures from saved results; no fitting or label changes."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
R = ROOT/'experiments/results'
F = ROOT/'experiments/figures'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,
                     'axes.spines.top':False,'axes.spines.right':False,
                     'svg.fonttype':'none','savefig.dpi':170})
COLORS = {'seen_test':'#087e8b','unseen_test':'#ad4b36'}


def save(fig,name):
    svg=F/f'{name}.svg'
    fig.savefig(svg)
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    preview = ROOT/'outputs/extension_figures'
    preview.mkdir(parents=True,exist_ok=True)
    fig.savefig(preview/f'{name}.png')
    plt.close(fig)


def main():
    F.mkdir(exist_ok=True)
    n = pd.read_csv(R/'noise_summary.csv')
    fig, axs = plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    for role, color in COLORS.items():
        g = n[n.role==role].assign(order=lambda d:d.snr_db.map({20:1,10:2,0:3}).fillna(0)).sort_values('order')
        axs[0].plot(range(4),g.reference_mae_cm,'o-',color=color,label=role.replace('_test','').title()+' | all frames')
        axs[0].plot(range(4),g.rank70_reference_mae_cm,'s--',color=color,label=role.replace('_test','').title()+' | top 70%')
        axs[1].plot(range(4),g.fixed_coverage*100,'o-',color=color,label=role.replace('_test','').title())
    for ax in axs:
        ax.set_xticks(range(4),['No added noise','20 dB','10 dB','0 dB'])
        ax.grid(axis='y',alpha=.2);ax.legend(fontsize=8)
    axs[0].set(ylabel='Assumed-reference MAE (cm)',title='Strong noise defeats frame ranking')
    axs[1].set(ylabel='Frames retained (%)',ylim=(0,100),title='Frozen threshold still retains many frames')
    fig.suptitle('16 test recordings | 3 seeds per SNR | frozen network and score',fontsize=13)
    save(fig,'noise_robustness')

    phase = pd.read_csv(R/'noise_by_phase.csv').assign(snr=lambda d:d.snr_db.fillna(99))
    fig, axs = plt.subplots(1,2,figsize=(10,4.2),layout='constrained')
    for ax, role in zip(axs,COLORS):
        table = phase[phase.role==role].groupby(['phase','snr']).reference_mae_cm.mean().unstack().loc[['early','middle','late'],[99,20,10,0]]
        im=ax.imshow(table,vmin=0,vmax=7,cmap='YlOrRd',aspect='auto')
        ax.set_xticks(range(4),['No added','20 dB','10 dB','0 dB'])
        ax.set_yticks(range(3),['Early third','Middle third','Late third'])
        ax.set_title(role.replace('_test','').title()+' containers')
        for i in range(3):
            for j in range(4):
                ax.text(j,i,f'{table.iloc[i,j]:.2f}',ha='center',va='center',color='white' if table.iloc[i,j]>4.5 else 'black')
    fig.colorbar(im,ax=axs,label='Assumed-reference MAE (cm)',shrink=.8)
    fig.suptitle('Recording phase is elapsed time, not measured water level',fontsize=12)
    save(fig,'noise_by_phase')

    e=pd.read_csv(R/'endpoint_by_clip.csv')
    meta=pd.read_csv(ROOT/'reference/recording_manifest.csv').set_index('clip')
    fig=plt.figure(figsize=(11,9),layout='constrained')
    gs=fig.add_gridspec(2,2,height_ratios=[1,1.1]);ax=fig.add_subplot(gs[0,:])
    g=e[(e.window_s==.2)&e.role.isin(COLORS)]
    ax.bar(g['clip'].str.replace('clip_',''),g.delta_mae_cm,color=g.role.map(COLORS))
    ax.axhline(0,color='black',lw=.8);ax.set(xlabel='Recording ID (11-18 seen; 19-26 unseen)',
          ylabel='Change in reference MAE (cm)',title='A fixed 0.2 s terminal median: improvement is concentrated in two failures')
    for j, clip in enumerate(['clip_24','clip_15']):
        ax=fig.add_subplot(gs[1,j]);p=pd.read_csv(ROOT/'reference/model_predictions'/f'{clip}.csv')
        change=float(e[(e['clip']==clip)&(e.window_s==.2)].global_shift_cm.iloc[0])
        ax.plot(p.time_s,p.length_ref_cm,'k--',label='Assumed filling reference')
        ax.plot(p.time_s,p.length_pred_cm,color='#ad4b36',label='Final sample')
        ax.plot(p.time_s,p.length_pred_cm+change,color='#087e8b',label='Terminal median (0.2 s)')
        ax.set(xlabel='Time (s)',ylabel='Air-column estimate (cm)',title=clip+(' | large offset removed' if j==0 else ' | small worsening'))
        ax.legend(fontsize=8);ax.grid(alpha=.15)
    save(fig,'endpoint_comparison')

    cache=ROOT/'outputs/extension_noise'
    if cache.exists():
        fig,axs=plt.subplots(2,2,figsize=(11,8),layout='constrained')
        for j,clip in enumerate(['clip_14','clip_24']):
            for tag,color,label in [('clean','#182d34','No added noise'),('snr20_seed5305','#087e8b','20 dB'),
                                    ('snr10_seed5305','#b57714','10 dB'),('snr0_seed5305','#ad4b36','0 dB')]:
                p=pd.read_csv(cache/f'{clip}_{tag}.csv')
                axs[0,j].plot(p.time_s,p.wavelength_cm,color=color,lw=1,label=label)
                axs[1,j].plot(p.time_s,p.length_pred_cm,color=color,lw=1,label=label)
            axs[1,j].plot(p.time_s,meta.loc[clip,'height_cm']*(1-p.time_s/meta.loc[clip,'duration_s']),'k--',label='Assumed reference')
            for i in range(2):
                axs[i,j].set(xlabel='Time (s)',ylabel='Wavelength (cm)' if i==0 else 'Air-column estimate (cm)')
                axs[i,j].legend(fontsize=8);axs[i,j].grid(alpha=.15)
            axs[0,j].set_title(clip+(' | noise degradation' if j==0 else ' | apparent improvement after endpoint change'))
        fig.suptitle('Exploratory mechanism examples | seed 5305 | no true pitch or level label',fontsize=12)
        save(fig,'noise_mechanisms')

    visual=pd.read_csv(R/'visual_by_frame.csv');valid=visual[visual.status=='ai_provisional']
    fig,axs=plt.subplots(2,3,figsize=(12,7.5),layout='constrained')
    for ax,(clip,g) in zip(axs.flat,valid.groupby('clip',sort=False)):
        t=g.actual_audio_time_s;v=g.visual_fraction_midpoint*100
        ax.errorbar(t,v,yerr=np.vstack([v-g.visual_fraction_lower*100,g.visual_fraction_upper*100-v]),
                    fmt='o',color='#087e8b',ms=4,capsize=2,label='AI visual proxy + pixel range')
        ax.plot(t,g.audio_model_fraction*100,'s-',color='#ad4b36',ms=3,label='Audio model / metadata height')
        ax.plot(t,g.assumed_fraction*100,'k--',label='Assumed linear filling')
        ax.set(title=f'{clip} | {len(g)}/9 usable frames',xlabel='Audio time (s)',ylabel='Relative filling (%)',ylim=(-5,125))
        ax.grid(alpha=.15)
    handles,labels=axs[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='outside lower center',ncol=3,fontsize=9)
    fig.suptitle('Exploratory image-relative comparison | AI annotations, no independent human review\nPixel ranges do not calibrate perspective or refraction; clips 16 and 18 excluded (cropped bases)',fontsize=12)
    save(fig,'visual_proxy_comparison')


if __name__=='__main__':
    main()
