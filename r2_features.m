function D = r2_features(x,pred)
%R2_FEATURES Acoustic features aligned with cached pretrained-model outputs.
% Local spectral peaks are not assumed to be the physical fundamental.
[ff,t,PP]=r2_stft(x,640,320,2048); band=ff>=300 & ff<=5000;
f=ff(band); P=PP(band,:); v=zeros(numel(t),4); tiny=1e-30;
for k=1:numel(t)
    s=P(:,k); peaks=find(s(2:end-1)>s(1:end-2) & s(2:end-1)>=s(3:end))+1;
    if isempty(peaks), [~,peaks]=max(s); end
    [~,q]=sort(s(peaks),'descend'); order=peaks(q); a=order(1);
    second=order(abs(f(order)-f(a))>=100);
    ratio=0; if ~isempty(second), ratio=sqrt(s(second(1))/max(s(a),tiny)); end
    prob=s/max(sum(s),tiny);
    v(k,:)=[f(a),10*log10((s(a)+tiny)/(median(s)+tiny)),ratio,...
        -sum(prob.*log(max(prob,tiny)))/log(numel(s))];
end
valid=pred.time_s>=t(1) & pred.time_s<=t(end); D=pred(valid,:);
names={'peak_hz','prom_db','competition','entropy'};
for j=1:4, D.(names{j})=interp1(t,v(:,j),D.time_s,'linear'); end
jump=[0;1200*abs(diff(log2(pred.pitch_hz)))];
D.jump_cents=jump(valid); D.jump_cents_log=log1p(D.jump_cents);
D.model_support_db=zeros(height(D),1);D.odd_harmonic_support_db=nan(height(D),1);
for k=1:height(D)
    [~,j]=min(abs(t-D.time_s(k))); s=P(:,j); f0=D.pitch_hz(k);
    % Use the full spectrum for model support: model pitch can exceed 5 kHz.
    near=abs(ff-f0)<=50; val=tiny;
    if any(near), val=max(PP(near,j)); end
    D.model_support_db(k)=10*log10((val+tiny)/(median(s)+tiny));
    hs=[];
    for multiple=[3 5] % Odd modes of an approximately closed-open air column.
        if multiple*f0>=300 && multiple*f0<=5000
            hs(end+1)=max(s(abs(f-multiple*f0)<=50))/(median(s)+tiny); %#ok<AGROW>
        end
    end
    if ~isempty(hs),D.odd_harmonic_support_db(k)=10*log10(mean(hs)+tiny);end
end
end
