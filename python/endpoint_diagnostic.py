from pathlib import Path
import pandas as pd,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parents[1];d=pd.read_csv(root/'results/frame_features.csv');m=pd.read_csv(root/'reference/recording_manifest.csv')
rows=[]
for clip in ['clip_22','clip_18','clip_24']:
    a=d[d['clip']==clip].copy();r=m[m['clip']==clip].iloc[0];alt=a.wavelength_cm/4-.62*r.radius_cm
    rows.append(dict(clip=clip,endpoint_mae_cm=a.abs_error_cm.mean(),known_radius_mae_cm=abs(alt-a.length_ref_cm).mean(),radius_metadata_cm=r.radius_cm))
pd.DataFrame(rows).to_csv(root/'results/endpoint_diagnostic.csv',index=False)
cl='clip_24';a=pd.read_csv(root/'reference/model_predictions'/f'{cl}.csv');r=m[m['clip']==cl].iloc[0]
plt.rcParams.update({'font.family':'DejaVu Serif','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axs=plt.subplots(1,2,figsize=(8.2,3.2),layout='constrained')
axs[0].plot(a.time_s,a.pitch_hz,color='#176b96');axs[0].scatter(a.time_s.iloc[-1],a.pitch_hz.iloc[-1],color='#b24f34',zorder=3,label='Last model sample')
axs[0].set(xlabel='Time (s)',ylabel='Model pitch (Hz)',title='Endpoint switch in clip 24');axs[0].legend(fontsize=8)
axs[1].plot(a.time_s,a.length_ref_cm,'k--',label='Linear-fill reference')
axs[1].plot(a.time_s,a.length_pred_cm,color='#b24f34',label='Released endpoint correction')
axs[1].plot(a.time_s,a.wavelength_cm/4-.62*r.radius_cm,color='#176b96',label='Known-radius diagnostic')
axs[1].set(xlabel='Time (s)',ylabel='Air-column length (cm)',title='A single endpoint shifts the whole estimate')
axs[1].legend(fontsize=7)
for ax in axs:ax.grid(alpha=.2)
plt.savefig(root/'figures/fig11_endpoint_failure.png',dpi=190,bbox_inches='tight')
print(pd.DataFrame(rows).to_string(index=False))
