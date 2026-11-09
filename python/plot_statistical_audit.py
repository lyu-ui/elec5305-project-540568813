"""Scientific figures for the split/statistical audit; no label changes."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'experiments/statistical_audit'
F=R/'figures'
LABELS={'seen_test':'Test I: 7/8 development containers',
        'unseen_test':'Test II: new containers'}
COLORS={'Combined':'#176b73','Prominence':'#bc7028','Model support':'#7b6c9b',
        'Random expectation':'#7b8589','Error oracle':'#64835c','Endpoint stability':'#b44e40'}


def save(fig,name):
    F.mkdir(exist_ok=True)
    fig.savefig(F/f'{name}.svg',metadata={'Date':None})
    path=F/f'{name}.svg'
    path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
    out=ROOT/'outputs/statistical_audit';out.mkdir(exist_ok=True)
    fig.savefig(out/f'{name}.png',dpi=155)
    plt.close(fig)


def main():
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none',
                         'svg.hashsalt':'elec5305-statistical-audit','axes.spines.top':False,
                         'axes.spines.right':False})
    frames=pd.read_csv(ROOT/'outputs/statistical_audit/frame_features.csv')
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained',sharey=True)
    rows=[]
    coverages=np.arange(10,101)/100
    for ax,role in zip(axes,LABELS):
        g=frames[frames.role==role]
        rng=np.random.default_rng(5305)
        resamples=rng.integers(0,8,(2000,8))
        for method,field in [('Combined','reliability_score'),('Prominence','prom_db'),
                             ('Model support','model_support_db'),('Random expectation',None),('Error oracle','abs_error_cm')]:
            values=[]
            for clip,z in g.groupby('clip',sort=True):
                ix=np.arange(len(z)) if field is None else np.argsort(z[field] if method=='Error oracle' else -z[field],kind='stable')
                errors=z.abs_error_cm.to_numpy()[ix]
                means=np.array([errors[:int(np.ceil(c*len(z)))].mean() for c in coverages])
                if field is None: means[:]=errors.mean()
                values.append(means)
            values=np.asarray(values)
            mean=values.mean(axis=0)
            ax.plot(coverages*100,mean,label=method,color=COLORS[method],lw=1.7 if method=='Combined' else 1.1)
            if method=='Combined':
                boot=values[resamples].mean(axis=1)
                low,high=np.quantile(boot,[.025,.975],axis=0)
                ax.fill_between(coverages*100,low,high,color=COLORS[method],alpha=.16,lw=0)
                for c,m,l,h in zip(coverages,mean,low,high):
                    rows.append(dict(role=role,coverage=c,mean_cm=m,ci_low=l,ci_high=h))
        ax.set(title=LABELS[role],xlabel='Frames retained within every recording (%)',ylabel='Macro reference MAE (cm)',ylim=(0,4.5),xlim=(10,100))
        ax.grid(alpha=.18)
    axes[0].legend(fontsize=8)
    fig.suptitle('Within-recording selection | common vertical scale\nShading: pointwise 95% container bootstrap, eight containers per group',fontsize=12)
    save(fig,'within_recording_selection')
    pd.DataFrame(rows).to_csv(R/'within_recording_curve.csv',index=False)

    curve=pd.read_csv(R/'global_risk_coverage.csv')
    areas=pd.read_csv(R/'aurc.csv')
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained',sharey=True)
    for ax,role in zip(axes,LABELS):
        for method in ['Combined','Prominence','Model support','Endpoint stability','Error oracle']:
            g=curve[(curve.role==role)&(curve.method==method)]
            area=areas[(areas.role==role)&(areas.method==method)].aurc_cm.iloc[0]
            ax.step(np.r_[0,g.coverage*100],np.r_[g.risk_cm.iloc[0],g.risk_cm],where='pre',color=COLORS[method],label=f'{method} | {area:.3f}',lw=1.2)
        base=areas[areas.role==role].full_risk_cm.iloc[0]
        ax.axhline(base,color=COLORS['Random expectation'],ls=':',label=f'Constant risk | {base:.3f}')
        ax.set(title=LABELS[role],xlabel='Globally retained weighted frame mass (%)',ylabel='Conditional reference risk (cm)',xlim=(0,100))
        ax.legend(fontsize=8);ax.grid(alpha=.18)
    fig.suptitle('Global thresholds can reject whole recordings | legend reports exact AURC (cm)\nEqual initial mass per recording; tied scores enter together; curves are descriptive',fontsize=12)
    save(fig,'global_risk_coverage')

    loco=pd.read_csv(R/'loco_by_container.csv')
    pivot=loco.pivot(index='container_id',columns='method',values='delta_cm')
    fig,ax=plt.subplots(figsize=(11,4.4),layout='constrained')
    positions=np.arange(len(pivot))
    ax.bar(positions-.17,pivot['Fixed ridge 0.1'],.34,color='#176b73',label='Fixed ridge 0.1')
    ax.bar(positions+.17,pivot['Nested ridge'],.34,color='#bc7028',label='Ridge selected inside each training fold')
    ax.axhline(0,color='#182d34',lw=.8)
    ax.set(xticks=positions,xticklabels=pivot.index.str.replace('container_',''),xlabel='Held-out container ID',ylabel='Change in reference MAE (cm)',title='19 recordings, 11 outer container folds | 70% within-recording retention')
    ax.legend(fontsize=9);ax.grid(axis='y',alpha=.18)
    save(fig,'container_loco')


if __name__=='__main__':
    main()
