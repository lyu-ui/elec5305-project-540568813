"""Inference-only adapter of Bagad et al.'s released SoundOfWater model.
The architecture, forward order and 215 checkpoint tensors are preserved.
No training code, Lightning trainer, video decoder or backbone download is needed.
Input files are the fixed 16 kHz mono analysis WAVs in the submission.
"""
from pathlib import Path
import argparse, math, json, hashlib, time
import numpy as np
import pandas as pd
import torch
from torch import nn
from transformers import Wav2Vec2Config,Wav2Vec2Model
from scipy.io import wavfile

class TimeEncoding(nn.Module):
    def forward(self,t):
        i=(t*49).to(torch.int64)
        div=torch.exp(torch.arange(0,512,2,dtype=torch.float32)*(-math.log(10000)/512))
        pe=torch.zeros(*t.shape,512)
        pe[:,:,0::2]=torch.sin(i[:,:,None].float()*div)
        pe[:,:,1::2]=torch.cos(i[:,:,None].float()*div)
        return 0.01*pe

class Backbone(nn.Module):
    def __init__(self,config):
        super().__init__()
        self.net=Wav2Vec2Model(config)
        self.time_encoding=TimeEncoding()
        self.layer_norm=nn.Identity()
    def forward(self,x,duration):
        feat=self.net.feature_extractor(x).transpose(1,2)
        times=torch.linspace(0,duration,feat.shape[1])[None,:]
        feat=self.layer_norm(feat+self.time_encoding(times))
        hidden,_=self.net.feature_projection(feat)
        return self.net.encoder(hidden,attention_mask=None,output_attentions=False,
                                output_hidden_states=False,return_dict=True)[0]

class InferenceModel(nn.Module):
    def __init__(self,config):
        super().__init__();self.backbone=Backbone(config)
        self.intermediate_layers=nn.Identity()
        self.axial_head=nn.Linear(768,64);self.radial_head=nn.Linear(768,64)
    def forward(self,x,duration):
        h=self.intermediate_layers(self.backbone(x,duration))
        return torch.softmax(self.axial_head(h),dim=-1)

def main(root,checkpoint,config):
    torch.set_num_threads(4);torch.manual_seed(0)
    cfg=Wav2Vec2Config.from_json_file(str(config))
    # Eager attention matches the original forward implementation.
    cfg._attn_implementation='eager'
    model=InferenceModel(cfg)
    state=torch.load(checkpoint,map_location='cpu',weights_only=True)
    status=model.load_state_dict(state,strict=True)
    print('Strict checkpoint load:',status,flush=True)
    model.eval()
    d=pd.read_csv(root/'reference/recording_manifest.csv')
    out=root/'reference/model_predictions';out.mkdir(exist_ok=True)
    props=[]
    with torch.inference_mode():
        for r in d.itertuples():
            tic=time.time();fs,x=wavfile.read(root/r.audio_file);assert fs==16000
            x=x.astype(np.float32)
            x=(x-x.mean())/np.sqrt(x.var()+1e-7)
            prob=model(torch.from_numpy(x[None,:]),len(x)/fs)[0]
            lam=(prob@torch.linspace(0,100,64)).numpy()
            t=(np.arange(len(lam))*320+200)/fs
            # Released endpoint-corrected, full-recording estimator, in cm.
            length=(lam-lam[-1])/4
            ref=r.height_cm*(1-t/(len(x)/fs))
            p=pd.DataFrame(dict(time_s=t,wavelength_cm=lam,pitch_hz=34000/lam,
                                length_pred_cm=length,length_ref_cm=ref,
                                abs_error_cm=np.abs(length-ref)))
            p.to_csv(out/(r.clip+'.csv'),index=False)
            props.append(dict(clip=r.clip,height_pred_cm=(lam[0]-lam[-1])/4,
                              radius_pred_cm=lam[-1]/(4*.62),mae_reference_cm=float(np.mean(np.abs(length-ref)))))
            print(r.clip,r.role,'frames',len(lam),'reference MAE',round(props[-1]['mae_reference_cm'],3),'seconds',round(time.time()-tic,2),flush=True)
    pd.DataFrame(props).to_csv(root/'reference/model_properties.csv',index=False)
    versions=dict(torch=torch.__version__,transformers=__import__('transformers').__version__,numpy=np.__version__,
                  scipy=__import__('scipy').__version__,checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
                  strict_checkpoint_keys=len(state),eval_mode=True,reference='H * (1 - t / WAV duration); assumption-derived, not independent level measurements',
                  upstream_commit='9253107392c8168396f8e7cf405a88dd9b6b6d82')
    (root/'reference/model_run.json').write_text(json.dumps(versions,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--config',type=Path,required=True)
    a=p.parse_args();main(a.root,a.checkpoint,a.config)
