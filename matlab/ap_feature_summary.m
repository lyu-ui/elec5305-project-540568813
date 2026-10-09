function result=ap_feature_summary(base,durations)
%AP_FEATURE_SUMMARY Power-based spread and 90% energy roll-off, 0-8 kHz.
rows=zeros(6,4);r=0;
for j=1:2
    b=base{j}; keep=b.f<=8000; f=b.f(keep); P=b.P(keep,:);
    p=P./max(sum(P,1),realmin);
    spread=sqrt(sum((f-b.centroid).^2.*p,1));
    [~,k]=max(cumsum(p,1)>=0.90,[],1); rolloff=reshape(f(k),1,[]);
    tau=b.t/durations(j);
    for third=0:2
        r=r+1; mask=tau>=third/3 & tau<(third+1)/3;
        rows(r,:)=[j,third+1,median(spread(mask)),median(rolloff(mask))];
    end
end
result=array2table(rows,'VariableNames', ...
    {'Recording_1A_2B','Third','Spread_Hz','Rolloff90_Hz'});
end
