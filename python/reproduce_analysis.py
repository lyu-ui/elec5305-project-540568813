from pathlib import Path
import numpy as np,pandas as pd,json,ast
from scipy.io import wavfile,savemat
from scipy.linalg import toeplitz,solve
from scipy.signal import lfilter
from scipy.stats import spearmanr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
RES=ROOT/'results';RES.mkdir(exist_ok=True)
FIG=ROOT/'figures';FIG.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Serif','font.size':10,'axes.titlesize':11,'axes.labelsize':10,'legend.fontsize':8,'figure.dpi':140,'savefig.dpi':190,'axes.spines.top':False,'axes.spines.right':False})
EPS=1e-30;FS=16000;M=640;HOP=320;NFFT=2048
FEAT=['prom_db','competition','jump_cents_log','entropy','model_support_db']

def stft(x,M=M,H=HOP,N=NFFT):
    starts=np.arange(0,len(x)-M+1,H);w=.5-.5*np.cos(2*np.pi*np.arange(M)/M)
    z=x[starts[:,None]+np.arange(M)];S=np.fft.rfft(z*w,N,axis=1).T
    P=abs(S)**2/(FS*np.sum(w*w));P[1:-1]*=2
    return np.arange(N//2+1)*FS/N,(starts+M/2)/FS,P

def features(x,pred,M=M):
    f,t,P=stft(x,M=M);full_f=f.copy();full_P=P.copy();band=(f>=300)&(f<=5000);f=f[band];P=P[band]
    cols=[]
    for s in P.T:
        # Genuine local peaks, separated by at least 100 Hz.
        peaks=np.where((s[1:-1]>s[:-2])&(s[1:-1]>=s[2:]))[0]+1
        if not len(peaks):peaks=np.array([int(np.argmax(s))])
        order=peaks[np.argsort(-s[peaks],kind='stable')];k1=order[0]
        second=order[np.abs(f[order]-f[k1])>=100]
        ratio=np.sqrt(s[second[0]]/max(s[k1],EPS)) if len(second) else 0
        prob=s/max(sum(s),EPS);entropy=-sum(prob*np.log(np.maximum(prob,EPS)))/np.log(len(s))
        cols.append([f[k1],10*np.log10((s[k1]+EPS)/(np.median(s)+EPS)),ratio,entropy])
    cols=np.asarray(cols)
    pp=pred[(pred.time_s>=t[0])&(pred.time_s<=t[-1])].copy()
    for name,j in [('peak_hz',0),('prom_db',1),('competition',2),('entropy',3)]:pp[name]=np.interp(pp.time_s,t,cols[:,j])
    full_jump=np.r_[0,1200*np.abs(np.diff(np.log2(pred.pitch_hz)))]
    pp['jump_cents']=np.interp(pp.time_s,pred.time_s,full_jump)
    pp['jump_cents_log']=np.log1p(pp.jump_cents)
    # Support of model frequency is deliberately separate from the strongest peak.
    support=[];harm=[]
    for ti,fi in zip(pp.time_s,pp.pitch_hz):
        j=np.argmin(abs(t-ti));s=P[:,j]
        mask=abs(full_f-fi)<=50
        v=max(full_P[mask,j]) if np.any(mask) else EPS
        support.append(10*np.log10((v+EPS)/(np.median(s)+EPS)))
        hs=[]
        for mult in [3,5]:
            if 300<=mult*fi<=5000:
                z=abs(f-mult*fi)<=50;hs.append(max(s[z])/(np.median(s)+EPS))
        harm.append(10*np.log10(np.mean(hs)+EPS) if hs else np.nan)
    pp['model_support_db']=support;pp['odd_harmonic_support_db']=harm
    return pp,(f,t,P,cols)

def fit_score(d):
    X=d[FEAT].to_numpy();y=np.log1p(d.abs_error_cm.to_numpy())
    w=1/d.groupby('clip').clip.transform('size').to_numpy();w=w/w.sum()
    mu=(w[:,None]*X).sum(axis=0);sd=np.sqrt((w[:,None]*(X-mu)**2).sum(axis=0));sd=np.maximum(sd,1e-8)
    Z=np.c_[np.ones(len(X)),(X-mu)/sd]
    # Fixed dimensionless regularization, chosen before inspecting test errors.
    lam=.1;pen=np.diag([0]+[lam]*len(FEAT))
    beta=np.linalg.solve(Z.T@(w[:,None]*Z)+pen,Z.T@(w*y))
    return mu,sd,beta

def score(d,params):
    mu,sd,beta=params
    return -(np.c_[np.ones(len(d)),(d[FEAT].to_numpy()-mu)/sd]@beta)

def save(name):plt.savefig(FIG/(name+'.png'),bbox_inches='tight');plt.close()

def lpc_coeff(x,p):
    x=x-np.mean(x);x=x*(.5-.5*np.cos(2*np.pi*np.arange(len(x))/len(x)))
    r=np.array([np.dot(x[:len(x)-k],x[k:])/len(x) for k in range(p+1)])
    r[0]*=(1+1e-6)
    a=np.r_[1,solve(toeplitz(r[:p]),-r[1:p+1],assume_a='sym')]
    g=max(r[0]+a[1:]@r[1:],EPS)
    return a,g

def wiener(x,n,kind):
    L=640;hop=160;w=.5-.5*np.cos(2*np.pi*np.arange(L)/L)
    s=np.pad(x,(L,L));noise=np.pad(n,(L,L));y=s+noise
    starts=np.arange(0,len(y)-L+1,hop);idx=starts[:,None]+np.arange(L)
    S=np.fft.rfft(s[idx]*w,axis=1);N=np.fft.rfft(noise[idx]*w,axis=1);Y=S+N
    if kind=='identity':G=np.ones_like(abs(Y))
    elif kind=='oracle':G=abs(S)**2/np.maximum(abs(S)**2+abs(N)**2,EPS)
    else:
        # A disjoint 0.5 s noise-only calibration sample is passed separately.
        cal=NOISE_CAL;ci=np.arange(0,len(cal)-L+1,hop)[:,None]+np.arange(L)
        psd=np.mean(abs(np.fft.rfft(cal[ci]*w,axis=1))**2,axis=0)
        power=abs(Y)**2;sm=np.empty_like(power);sm[0]=power[0]
        for k in range(1,len(sm)):sm[k]=.8*sm[k-1]+.2*power[k]
        G=np.maximum(.05,1-psd/np.maximum(sm,EPS))
    frames=np.fft.irfft(Y*G,n=L,axis=1)*w
    z=np.zeros(len(y));den=np.zeros(len(y))
    for i,start in enumerate(starts):z[start:start+L]+=frames[i];den[start:start+L]+=w*w
    z=z/np.maximum(den,EPS)
    return z[L:L+len(x)]

def main():
    global NOISE_CAL
    meta=pd.read_csv(ROOT/'reference/recording_manifest.csv');parts=[];spec={}
    for r in meta.itertuples():
        fs,x=wavfile.read(ROOT/r.audio_file);x=x.astype(float);x-=x.mean()
        p=pd.read_csv(ROOT/'reference/model_predictions'/(r.clip+'.csv'))
        d,s=features(x,p);spec[r.clip]=s
        for c in ['clip','role','split','container_id','shape','material']:d[c]=getattr(r,c)
        d['height_cm']=r.height_cm;d['duration_s']=r.duration_s
        m=ast.literal_eval(r.measurements);rb=m['diameter_bottom']/2;rt=m['diameter_top']/2
        q=d.time_s.to_numpy()/r.duration_s
        if r.shape=='semiconical' and abs(rt-rb)>1e-8:
            water_height=r.height_cm*((rb**3+(rt**3-rb**3)*q)**(1/3)-rb)/(rt-rb)
            geom=r.height_cm-water_height
        else:geom=d.length_ref_cm.to_numpy()
        d['length_geometry_proxy_cm']=geom
        d['geometry_proxy_error_cm']=abs(d.length_pred_cm-geom)
        d['fill_fraction_pred']=1-d.length_pred_cm/r.height_cm
        d['fill_fraction_reference']=q
        parts.append(d)
    allf=pd.concat(parts,ignore_index=True);dev=allf[allf.role=='development']
    params=fit_score(dev);allf['reliability_score']=score(allf,params)
    mu,sd,beta=params
    coeff=pd.DataFrame(dict(feature=['intercept']+FEAT,coefficient=beta,mean=np.r_[0,mu],sd=np.r_[1,sd]));coeff.to_csv(RES/'score_coefficients.csv',index=False)
    # Out-of-container predictions for development sanity check only.
    oof=[]
    for cid in dev.container_id.unique():
        a=dev[dev.container_id!=cid];b=dev[dev.container_id==cid].copy();b['score_oof']=score(b,fit_score(a));oof.append(b)
    pd.concat(oof).to_csv(RES/'development_grouped_oof.csv',index=False)
    allf.to_csv(RES/'frame_features.csv',index=False)
    cliprows=[]
    for clip,d in allf.groupby('clip',sort=False):
        row={k:d.iloc[0][k] for k in ['clip','role','split','container_id','shape','material']}
        row.update(frames=len(d),mae_cm=d.abs_error_cm.mean(),geometry_mae_cm=d.geometry_proxy_error_cm.mean(),
                   fill_mae=d.abs_error_cm.mean()/d.height_cm.iloc[0],score_mean=d.reliability_score.mean(),
                   negative_length_fraction=(d.length_pred_cm<0).mean())
        row.update({f:d[f].mean() for f in FEAT})
        cliprows.append(row)
    clips=pd.DataFrame(cliprows);clips.to_csv(RES/'clip_summary.csv',index=False)
    rows=[]
    # Rank within each complete recording: equal clip weight and no test labels used in selection.
    for (clip,d) in allf[allf.role.isin(['seen_test','unseen_test'])].groupby('clip'):
        for cov in [1.,.9,.8,.7]:
            n=int(np.ceil(cov*len(d)))
            rankings={'Combined':np.argsort(-d.reliability_score.to_numpy(),kind='stable'),
                      'Prominence':np.argsort(-d.prom_db.to_numpy(),kind='stable'),
                      'Model support':np.argsort(-d.model_support_db.to_numpy(),kind='stable'),
                      'Random expectation':np.arange(len(d)),
                      'Error oracle':np.argsort(d.abs_error_cm.to_numpy(),kind='stable')}
            for method,ix in rankings.items():
                e=d.abs_error_cm.mean() if method=='Random expectation' else d.abs_error_cm.iloc[ix[:n]].mean()
                rows.append(dict(clip=clip,role=d.role.iloc[0],container_id=d.container_id.iloc[0],coverage=cov,realized_coverage=n/len(d),method=method,mae_cm=e))
    sel=pd.DataFrame(rows);sel.to_csv(RES/'selective_by_clip.csv',index=False)
    summ=sel.groupby(['role','coverage','method'],sort=False).mae_cm.agg(['mean','std']).reset_index();summ.to_csv(RES/'selective_summary.csv',index=False)
    # Container bootstrap: each test stratum has one selected clip per container.
    rng=np.random.default_rng(5305);cis=[]
    for role in ['seen_test','unseen_test']:
        a=sel[(sel.role==role)&(sel.method=='Combined')]
        baseline=a[a.coverage==1].set_index('clip').mae_cm
        for cov in [.9,.8,.7]:
            retained=a[a.coverage==cov].set_index('clip').mae_cm
            delta=retained-baseline;boot=delta.to_numpy()[rng.integers(0,len(delta),(2000,len(delta)))].mean(axis=1)
            cis.append(dict(role=role,coverage=cov,delta_cm=delta.mean(),ci_low=np.quantile(boot,.025),ci_high=np.quantile(boot,.975),containers=len(delta)))
    pd.DataFrame(cis).to_csv(RES/'paired_container_bootstrap.csv',index=False)
    # Frozen development threshold demonstrates that deployment coverage is not guaranteed.
    threshold=float(np.quantile(allf[allf.role=='development'].reliability_score,.2))
    thr=[]
    for clip,d in allf[allf.role.isin(['seen_test','unseen_test'])].groupby('clip'):
        keep=d.reliability_score>=threshold
        thr.append(dict(clip=clip,role=d.role.iloc[0],threshold=threshold,coverage=keep.mean(),mae_cm=d.loc[keep,'abs_error_cm'].mean()))
    pd.DataFrame(thr).to_csv(RES/'fixed_threshold.csv',index=False)
    # Descriptive correlations across recordings; no frame-independence assumption.
    cor=[]
    for role in ['development','seen_test','unseen_test']:
        d=clips[clips.role==role]
        for f in FEAT+['score_mean']:
            cor.append(dict(role=role,feature=f,n=len(d),rho=spearmanr(d[f],d.mae_cm).statistic))
    pd.DataFrame(cor).to_csv(RES/'recording_correlations.csv',index=False)

    # Figure 1: one scientific pipeline, including the scope of reference labels.
    fig,ax=plt.subplots(figsize=(8.4,2.5));ax.set_xlim(0,10);ax.set_ylim(0,3);ax.axis('off')
    boxes=[(1,2.2,'33 source WAVs\nOfficial split labels'),(4,2.2,'Frozen pitch model\nWavelength and air column'),(8,2.2,'Error against an\nassumption-based reference'),(1,.7,'STFT diagnostics\nWiener and LPC studies'),(4,.7,'Development-only\nreliability regression'),(8,.7,'Seen and unseen tests\nCoverage versus error')]
    for x,y,s in boxes:ax.text(x,y,s,ha='center',va='center',bbox=dict(boxstyle='round,pad=.45',fc='#f1f3f5',ec='#6c7278'),fontsize=9)
    for x1,y1,x2,y2 in [(2.05,2.2,2.7,2.2),(5.5,2.2,6.4,2.2),(1,1.8,1,1.14),(2.1,.7,2.7,.7),(5.2,.7,6.4,.7),(8,1.8,8,1.1)]:ax.annotate('',(x2,y2),(x1,y1),arrowprops=dict(arrowstyle='->',color='#555'))
    save('fig01_pipeline')

    # Original pair diagnostic, not used as two independent containers.
    fig,axs=plt.subplots(2,1,figsize=(8.1,4.8),layout='constrained')
    for ax,cl,label in zip(axs,['clip_01','clip_27'],['Original recording A','Original recording B']):
        f,t,P,_=spec[cl];im=ax.pcolormesh(t,f,10*np.log10(np.maximum(P,EPS)/np.max(P)),cmap='magma',shading='auto',vmin=-60,vmax=0)
        d=allf[allf["clip"]==cl];ax.plot(d.time_s,d.pitch_hz,'c',lw=1.2,label='Pretrained model');ax.plot(d.time_s,d.peak_hz,'w',lw=.6,alpha=.7,label='Strongest local peak')
        ax.set(ylabel='Frequency (Hz)',ylim=(300,3000),title=label);ax.legend(loc='upper left')
    axs[-1].set_xlabel('Time from WAV start (s)');fig.colorbar(im,ax=axs,label='Power relative to panel maximum (dB)',shrink=.8);save('fig02_original_pair')

    # Three held-out cases, selected by observed error for explanation only.
    held=clips[clips.role.isin(['seen_test','unseen_test'])].sort_values('mae_cm')
    chosen=[held.iloc[0],held.iloc[len(held)//2],held.iloc[-1]]
    fig,axs=plt.subplots(3,1,figsize=(8.1,6.8),layout='constrained')
    for ax,r in zip(axs,chosen):
        f,t,P,_=spec[r['clip']];im=ax.pcolormesh(t,f,10*np.log10(np.maximum(P,EPS)/np.max(P)),cmap='magma',shading='auto',vmin=-60,vmax=0)
        d=allf[allf["clip"]==r['clip']];mr=meta[meta["clip"]==r['clip']].iloc[0]
        ax.plot(d.time_s,d.pitch_hz,'c',lw=1.3,label='Model pitch')
        fr=34000/(4*(d.length_ref_cm+.62*mr.radius_cm))
        ax.plot(d.time_s,fr,'w--',lw=1,label='Linear-fill physics reference')
        ax.set(ylabel='Frequency (Hz)',ylim=(300,3500),title=f"{r['clip']} | {r.role.replace("_"," ")} | {r["shape"]} | reference MAE {r.mae_cm:.2f} cm");ax.legend(loc='upper left')
    axs[-1].set_xlabel('Time (s)');fig.colorbar(im,ax=axs,label='Power relative to panel maximum (dB)',shrink=.7);save('fig03_success_ambiguity_failure')

    fig,axs=plt.subplots(2,3,figsize=(8.5,4.9),layout='constrained');labels=['Peak prominence (dB)','Competing amplitude ratio','log(1 + jump in cents)','Normalized entropy','Model-ridge support (dB)','Mean reliability score']
    for ax,key,label in zip(axs.flat,FEAT+['score_mean'],labels):
        for role,col,mark in [('development','#777777','.'),('seen_test','#176b96','o'),('unseen_test','#b24f34','^')]:
            d=clips[clips.role==role];ax.scatter(d[key],d.mae_cm,c=col,marker=mark,s=28,label=role.replace('_',' '))
        ax.set(xlabel=label,ylabel='Reference MAE (cm)');ax.grid(alpha=.2)
    axs[0,0].legend(fontsize=7);save('fig04_feature_error')

    fig,axs=plt.subplots(1,2,figsize=(8.2,3.3),layout='constrained')
    for ax,role in zip(axs,['seen_test','unseen_test']):
        for method,sty,col in [('Combined','-o','#176b96'),('Prominence','--s','#969696'),('Model support','-.^','#b24f34'),('Random expectation',':','#444444'),('Error oracle','--','#5c8a63')]:
            d=summ[(summ.role==role)&(summ.method==method)].sort_values('coverage');ax.plot(100*d.coverage,d['mean'],sty,label=method,color=col,ms=4)
        ax.set(xlabel='Retained predictions (%)',ylabel='Macro reference MAE (cm)',title=role.replace('_',' ').title(),xticks=[70,80,90,100]);ax.grid(alpha=.2)
    axs[0].legend(fontsize=7);save('fig05_selective_prediction')

    fig,axs=plt.subplots(1,2,figsize=(8.2,3.2),layout='constrained')
    for ax,role in zip(axs,['seen_test','unseen_test']):
        d=clips[clips.role==role];xx=np.arange(len(d));ax.bar(xx-.16,d.mae_cm,.32,label='Linear-fill reference',color='#176b96');ax.bar(xx+.16,d.geometry_mae_cm,.32,label='Geometry-adjusted proxy',color='#c79b64')
        ax.set(xticks=xx,xticklabels=d["clip"].str.replace('clip_',''),ylabel='Reference MAE (cm)',xlabel='Clip number',title=role.replace('_',' ').title());ax.grid(axis='y',alpha=.2)
    axs[0].legend(fontsize=7);save('fig06_geometry_sensitivity')

    fig,axs=plt.subplots(2,1,figsize=(8.1,4.7),layout='constrained')
    for ax,cl in zip(axs,['clip_28','clip_32']):
        f,t,P,_=spec[cl];im=ax.pcolormesh(t,f,10*np.log10(np.maximum(P,EPS)/np.max(P)),cmap='magma',shading='auto',vmin=-60,vmax=0)
        d=allf[allf["clip"]==cl];r=meta[meta["clip"]==cl].iloc[0];ax.plot(d.time_s,d.pitch_hz,'c',lw=1.3,label='Axial-head prediction')
        ax.set(ylabel='Frequency (Hz)',ylim=(300,3500),title=f'{cl} | {r.container_id} | {r["shape"]} | geometry stress case');ax.legend(loc='upper left')
    axs[-1].set_xlabel('Time (s)');fig.colorbar(im,ax=axs,label='Power relative to panel maximum (dB)',shrink=.8);save('fig07_shape_failures')

    # LPC: controlled two-resonator identification + genuine pouring-frame envelope.
    rng=np.random.default_rng(707);noise=rng.standard_normal(16000)
    poles=[]
    for f0,bw in [(650,60),(1400,100)]:
        rr=np.exp(-np.pi*bw/FS);poles += [rr*np.exp(2j*np.pi*f0/FS),rr*np.exp(-2j*np.pi*f0/FS)]
    atrue=np.poly(poles).real;control=lfilter([1],atrue,noise);control=control[-4096:];control/=np.std(control)
    savemat(ROOT/'data/lpc_control.mat',dict(control=control[:,None],a_true=atrue,fs=FS))
    rows=[];fig,axs=plt.subplots(1,2,figsize=(8.2,3.3),layout='constrained')
    freq=np.arange(1025)*FS/2048
    for ax,x,label in [(axs[0],control,'Known two-resonator control'),(axs[1],wavfile.read(ROOT/'data/clip_01.wav')[1][int(6.5*FS):int(6.6*FS)],'Recording A at 6.50 to 6.60 s')]:
        pwr=abs(np.fft.rfft((x-x.mean())*np.hanning(len(x)),8192))**2
        ax.plot(np.arange(4097)*FS/8192,10*np.log10(pwr/max(pwr)),color='.7',lw=.7,label='Windowed spectrum')
        for order,col in [(8,'#176b96'),(16,'#b24f34'),(32,'#648055')]:
            a,g=lpc_coeff(x,order);env=g/np.maximum(abs(np.fft.rfft(a,2048))**2,EPS)
            ax.plot(freq,10*np.log10(env/max(env)),label=f'LPC order {order}',lw=1,color=col)
            if ax==axs[0]:
                roots=np.roots(a);positive=roots[np.imag(roots)>0];fr=np.angle(positive)*FS/(2*np.pi)
                rows.append(dict(order=order,pole1_hz=fr[np.argmin(abs(fr-650))],pole2_hz=fr[np.argmin(abs(fr-1400))],max_pole_radius=max(abs(roots))))
        ax.set(xlim=(300,2500),ylim=(-65,3),xlabel='Frequency (Hz)',ylabel='Relative level (dB)',title=label);ax.grid(alpha=.2)
    axs[0].legend(fontsize=7);save('fig08_lpc_resonances');pd.DataFrame(rows).to_csv(RES/'lpc_control.csv',index=False)

    # New Week 6 controlled comparison: no artificial low-pass advantage.
    fs,raw=wavfile.read(ROOT/'data/clip_01.wav');x=raw[int(3*fs):int(9*fs)].astype(float);x-=x.mean()
    rng=np.random.default_rng(606);noise_bank=rng.standard_normal((len(x),3));cal_bank=rng.standard_normal((8000,3))
    savemat(ROOT/'data/wiener_inputs.mat',dict(clean=x[:,None],noise_bank=noise_bank,calibration_bank=cal_bank,fs=FS))
    rows=[];audio=ROOT/'audio_comparisons';audio.mkdir(exist_ok=True)
    reference_peak=features(x,pd.DataFrame(dict(time_s=np.arange(.02,5.98,.02),pitch_hz=np.ones(298)*1000)))[0] if False else None
    f,t,P=stft(x);band=(f>=300)&(f<=5000);refpeak=f[band][np.argmax(P[band],axis=0)]
    for snr in [0,10,20]:
        for seed in range(3):
            unit=noise_bank[:,seed];scale=np.sqrt(np.mean(x*x)/np.mean(unit*unit))*10**(-snr/20);n=scale*unit;NOISE_CAL=scale*cal_bank[:,seed]
            for method in ['Noisy','Estimated Wiener','Oracle Wiener']:
                y=x+n if method=='Noisy' else wiener(x,n,'estimated' if method=='Estimated Wiener' else 'oracle')
                measured=10*np.log10(np.sum(x*x)/np.sum((y-x)**2));_,_,py=stft(y);pk=f[band][np.argmax(py[band],axis=0)]
                rows.append(dict(input_snr_db=snr,seed=seed+1,method=method,output_snr_db=measured,peak_deviation_hz=np.mean(abs(pk-refpeak))))
                if snr==10 and seed==0:
                    gain=.8/max(np.max(abs(x)),np.max(abs(x+n)))
                    wavfile.write(audio/(method.replace(' ','_')+'.wav'),FS,(gain*y).astype(np.float32))
            if snr==10 and seed==0:wavfile.write(audio/'Original_segment.wav',FS,(gain*x).astype(np.float32))
    noise=pd.DataFrame(rows);noise.to_csv(RES/'wiener_trials.csv',index=False)
    nt=noise.groupby(['input_snr_db','method']).agg(snr_mean=('output_snr_db','mean'),snr_sd=('output_snr_db','std'),peak_mae=('peak_deviation_hz','mean')).reset_index();nt.to_csv(RES/'wiener_summary.csv',index=False)
    fig,axs=plt.subplots(1,2,figsize=(8.2,3.1),layout='constrained')
    for method,col in [('Noisy','#777777'),('Estimated Wiener','#176b96'),('Oracle Wiener','#b24f34')]:
        z=nt[nt.method==method];axs[0].errorbar(z.input_snr_db,z.snr_mean,yerr=z.snr_sd,fmt='o-',color=col,label=method,capsize=3)
        axs[1].plot(z.input_snr_db,z.peak_mae,'o-',color=col,label=method)
    axs[0].set(xlabel='Input SNR (dB)',ylabel='Output SNR (dB)');axs[1].set(xlabel='Input SNR (dB)',ylabel='Band-maximum deviation (Hz)')
    for ax in axs:ax.grid(alpha=.2);ax.set_xticks([0,10,20])
    axs[0].legend(fontsize=7);save('fig09_wiener_tradeoff')

    # Controlled close competing modes, illustrating what coarse auditory pooling loses.
    tt=np.arange(16000)/FS;sig=np.cos(2*np.pi*1000*tt)+.9*np.cos(2*np.pi*1150*tt)
    f,t,P=stft(sig);p=P[:,len(t)//2];centers=(np.exp(np.linspace(9.2789*np.log(1+.004368*300),9.2789*np.log(1+.004368*5000),20)/9.2789)-1)/.004368
    weights=np.maximum(0,1-abs(f[:,None]-centers[None,:])/(24.673*(1+.004368*centers[None,:])))
    pooled=weights.T@p/np.maximum(weights.sum(axis=0),EPS)
    fig,ax=plt.subplots(figsize=(8.2,2.5));ax.plot(f,10*np.log10(np.maximum(p,EPS)/p.max()),label='40 ms STFT');ax.plot(centers,10*np.log10(np.maximum(pooled,EPS)/pooled.max()),'o-',label='20 ERB-spaced triangular bands')
    ax.set(xlim=(650,1600),ylim=(-65,3),xlabel='Frequency (Hz)',ylabel='Relative power (dB)');ax.legend();ax.grid(alpha=.2);save('fig10_auditory_resolution')
    pd.DataFrame(dict(centre_hz=centers,band_energy=pooled)).to_csv(RES/'auditory_control.csv',index=False)

    # Explicit numerical audit, no claim of MATLAB execution.
    identity=wiener(x,np.zeros_like(x),'identity');err=np.linalg.norm(identity-x)/np.linalg.norm(x)
    train_ids=set(pd.read_csv(ROOT/'reference/official_train.csv').container_id)
    audit=dict(recordings=len(meta),containers=meta.container_id.nunique(),frames=len(allf),score_features=FEAT,
               wiener_identity_nrmse=err,no_duplicate_items=meta.item_id.is_unique,
               unseen_container_overlap=sorted(set(meta[meta.role=='unseen_test'].container_id)&train_ids),
               selected_cases=[x['clip'] for x in chosen],threshold=threshold,python_verified=True,matlab_executed=False)
    assert err<1e-12 and audit['no_duplicate_items'] and not audit['unseen_container_overlap']
    (RES/'verification.json').write_text(json.dumps(audit,indent=2))
    print('AUDIT',audit)
    print('SELECTIVE\n',summ[summ.method=='Combined'].to_string(index=False))
    print('BOOTSTRAP\n',pd.DataFrame(cis).to_string(index=False))
    print('WIENER\n',nt.to_string(index=False))
    print('COEFFICIENTS\n',coeff.to_string(index=False))

if __name__=='__main__':main()
