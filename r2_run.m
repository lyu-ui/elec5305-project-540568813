function R = r2_run(root)
%R2_RUN Recompute all core acoustic features and held-out selection results.
% Pretrained trajectories are frozen input data. No internet/Python is needed.
if nargin==0,root=fileparts(mfilename('fullpath'));end
addpath(root);out=fullfile(root,'matlab_results');if ~exist(out,'dir'),mkdir(out);end
meta=readtable(fullfile(root,'reference','recording_manifest.csv'),'TextType','string','VariableNamingRule','preserve');
allD=cell(height(meta),1);
for j=1:height(meta)
    [x,fs]=audioread(fullfile(root,meta.audio_file(j)));
    assert(fs==16000 && size(x,2)==1 && all(isfinite(x)),'Bad analysis audio.');
    x=x-mean(x);pred=readtable(fullfile(root,'reference','model_predictions',meta.clip(j)+".csv"));
    D=r2_features(x,pred);n=height(D);
    names={'clip','role','split','container_id','shape','material'};
    for k=1:numel(names),D.(names{k})=repmat(meta.(names{k})(j),n,1);end
    D.height_cm=repmat(meta.height_cm(j),n,1);D.duration_s=repmat(meta.duration_s(j),n,1);
    q=D.time_s/meta.duration_s(j);rb=meta.radius_bottom_cm(j);rt=meta.radius_top_cm(j);
    geom=D.length_ref_cm;
    if meta.shape(j)=="semiconical" && abs(rt-rb)>1e-8
        water=meta.height_cm(j)*((rb^3+(rt^3-rb^3)*q).^(1/3)-rb)/(rt-rb);
        geom=meta.height_cm(j)-water;
    end
    D.length_geometry_proxy_cm=geom;D.geometry_proxy_error_cm=abs(D.length_pred_cm-geom);
    D.fill_fraction_pred=1-D.length_pred_cm/meta.height_cm(j);D.fill_fraction_reference=q;
    allD{j}=D;
end
D=vertcat(allD{:});model=r2_fit_score(D(D.role=="development",:));
D.reliability_score=r2_predict_score(D,model);writetable(D,fullfile(out,'frame_features.csv'));
% Validate against independently computed Python results, without replacing them.
ref=readtable(fullfile(root,'results','frame_features.csv'),'TextType','string');
assert(height(ref)==height(D) && all(ref.clip==D.clip),'Frame/recording mismatch.');
names=[model.names,{'reliability_score','length_geometry_proxy_cm'}];maxerr=0;
for k=1:numel(names),maxerr=max(maxerr,max(abs(D.(names{k})-ref.(names{k}))));end
assert(maxerr<1e-4,'Independent numerical comparison failed: %.6g',maxerr);
tr=readtable(fullfile(root,'reference','official_train.csv'),'TextType','string','VariableNamingRule','preserve');
assert(isempty(intersect(meta.container_id(meta.role=="unseen_test"),tr.container_id)));
assert(numel(unique(meta.item_id))==height(meta));
assert(isempty(intersect(meta.video_id(meta.role=="development"),meta.video_id(contains(meta.role,"test")))));

% Equal-recording selective error at 100, 90, 80 and 70 percent retention.
roles=["seen_test","unseen_test"];methods=["Combined","Prominence","Model support","Random expectation","Error oracle"];
records={};
for a=1:2
    clips=unique(D.clip(D.role==roles(a)),'stable');
    for j=1:numel(clips)
        z=D(D.clip==clips(j),:);
        for coverage=[1 .9 .8 .7]
            n=ceil(coverage*height(z));
            for k=1:5
                switch k
                    case 1,[~,ix]=sort(z.reliability_score,'descend');
                    case 2,[~,ix]=sort(z.prom_db,'descend');
                    case 3,[~,ix]=sort(z.model_support_db,'descend');
                    case 4,ix=(1:height(z))';
                    case 5,[~,ix]=sort(z.abs_error_cm,'ascend');
                end
                mae=mean(z.abs_error_cm(ix(1:n)));
                if k==4,mae=mean(z.abs_error_cm);end
                records(end+1,:)={clips(j),roles(a),z.container_id(1),coverage,n/height(z),methods(k),mae}; %#ok<AGROW>
            end
        end
    end
end
sel=cell2table(records,'VariableNames',{'clip','role','container_id','coverage','realized_coverage','method','mae_cm'});
writetable(sel,fullfile(out,'selective_by_clip.csv'));
sr=readtable(fullfile(root,'results','selective_by_clip.csv'),'TextType','string');
[~,ia]=sortrows([string(sel.clip),string(sel.coverage),string(sel.method)]);
[~,ib]=sortrows([sr.clip,string(sr.coverage),sr.method]);
assert(max(abs(sel.mae_cm(ia)-sr.mae_cm(ib)))<1e-4,'Selective-result mismatch.');

% Week 6 fixed-noise inputs: gain is shared across playback comparisons.
A=load(fullfile(root,'data','wiener_inputs.mat'));x=A.clean(:);noiseRows={};
[f,~,P]=r2_stft(x,640,320,2048);band=f>=300 & f<=5000;fb=f(band);[~,kk]=max(P(band,:),[],1);refPeak=fb(kk);
audio=struct();
for snr=[0 10 20]
    for seed=1:3
        unit=A.noise_bank(:,seed);scale=sqrt(mean(x.^2)/mean(unit.^2))*10^(-snr/20);
        noise=scale*unit;cal=scale*A.calibration_bank(:,seed);
        variants={x+noise,r2_wiener(x,noise,cal,'estimated'),r2_wiener(x,noise,cal,'oracle')};
        labels=["Noisy","Estimated Wiener","Oracle Wiener"];
        for k=1:3
            y=variants{k};outSNR=10*log10(sum(x.^2)/sum((y-x).^2));
            [~,~,p]=r2_stft(y,640,320,2048);[~,ki]=max(p(band,:),[],1);pk=fb(ki);
            noiseRows(end+1,:)={snr,seed,labels(k),outSNR,mean(abs(pk-refPeak))}; %#ok<AGROW>
        end
        if snr==10 && seed==1
            gain=.8/max([abs(x);abs(x+noise)]);
            audio.original=gain*x;audio.noisy=gain*variants{1};audio.estimated=gain*variants{2};audio.oracle=gain*variants{3};
        end
    end
end
noiseTable=cell2table(noiseRows,'VariableNames',{'input_snr_db','seed','method','output_snr_db','peak_deviation_hz'});
writetable(noiseTable,fullfile(out,'wiener_trials.csv'));
nr=readtable(fullfile(root,'results','wiener_trials.csv'),'TextType','string');
assert(max(abs(noiseTable.output_snr_db-nr.output_snr_db))<1e-4);
identity=r2_wiener(x,zeros(size(x)),zeros(8000,1),'identity');
nrmse=norm(identity-x)/norm(x);assert(nrmse<1e-12,'Overlap-add reconstruction failed.');

% Week 7 pole estimation check on the known control.
C=load(fullfile(root,'data','lpc_control.mat'));lpcRows=[];
for p=[8 16 32]
    a=r2_lpc(C.control,p);z=roots(a);zp=z(imag(z)>0);fr=angle(zp)*16000/(2*pi);
    [~,i]=min(abs(fr-650));[~,j]=min(abs(fr-1400));
    lpcRows(end+1,:)=[p,fr(i),fr(j),max(abs(z))]; %#ok<AGROW>
end
lpcTable=array2table(lpcRows,'VariableNames',{'order','pole1_hz','pole2_hz','max_pole_radius'});
writetable(lpcTable,fullfile(out,'lpc_control.csv'));
lr=readtable(fullfile(root,'results','lpc_control.csv'));
assert(max(abs(lpcTable{:,:}-lr{:,:}),[],'all')<1e-3,'LPC mismatch.');
fid=fopen(fullfile(out,'MATLAB_VERIFICATION.txt'),'w');
fprintf(fid,'MATLAB execution completed: %s\nVersion: %s\nMaximum feature mismatch: %.6g\nIdentity NRMSE: %.6g\n',char(datetime('now')),version,maxerr,nrmse);fclose(fid);
R=struct('root',root,'meta',meta,'frames',D,'model',model,'selective',sel,'noise',noiseTable,'lpc',lpcTable,'audio',audio);
fprintf('MATLAB checks passed: %d recordings, %d frames. Maximum mismatch %.3g.\n',height(meta),height(D),maxerr);
end
