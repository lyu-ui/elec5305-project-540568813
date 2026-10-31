function model = r2_fit_score(D)
%R2_FIT_SCORE Fixed-penalty ridge regression; equal weight per recording.
% Training target is log(1 + reference error/cm), not measured level error.
names={'prom_db','competition','jump_cents_log','entropy','model_support_db'};
X=D{:,names}; y=log1p(D.abs_error_cm); w=zeros(height(D),1);
clips=unique(D.clip,'stable');
for k=1:numel(clips),ii=D.clip==clips(k);w(ii)=1/sum(ii);end
w=w/sum(w);mu=sum(X.*w,1);sd=sqrt(sum((X-mu).^2.*w,1));sd=max(sd,1e-8);
Z=[ones(height(D),1),(X-mu)./sd];pen=diag([0 repmat(0.1,1,5)]);
beta=(Z'*(Z.*w)+pen)\(Z'*(w.*y));
model=struct('names',{names},'mu',mu,'sd',sd,'beta',beta);
end
