function result=ap_reconstruct(x,fs)
%AP_RECONSTRUCT Analysis/synthesis Hann OLA with boundary-safe normalization.
% Hann squared at 50% overlap is not constant. Divide by actual accumulated
% window products; pad and trim to recover every original sample.
M=round(.020*fs);hop=M/2;nfft=2^nextpow2(M);
w=0.5-0.5*cos(2*pi*(0:M-1)'/M);
xp=[zeros(M,1);x(:);zeros(M,1)];y=zeros(size(xp));den=y;
for start=1:hop:(numel(xp)-M+1)
    ii=start:start+M-1;S=fft(xp(ii).*w,nfft);
    pos=S(1:nfft/2+1);
    full=[pos;conj(pos(end-1:-1:2))]; % Hermitian symmetry for real synthesis.
    frame=real(ifft(full,nfft));frame=frame(1:M).*w;
    y(ii)=y(ii)+frame;den(ii)=den(ii)+w.^2;
end
mask=den>1e-12;y(mask)=y(mask)./den(mask);
ii=M+(1:numel(x));xr=y(ii);err=xr-x(:);
nrmse=norm(err)/norm(x);maxError=max(abs(err));
minWeight=min(den(ii));maxWeight=max(den(ii));
assert(all(den(ii)>0) && nrmse<1e-12,'STFT reconstruction failed.');
result=table(nrmse,maxError,minWeight,maxWeight, ...
    'VariableNames',{'NRMSE','MaxAbsoluteError_FS','MinimumWeight','MaximumWeight'});
figure('Color','w','Position',[50 50 1050 400]);
subplot(1,2,1);jj=M+(1:2*M);plot((0:2*M-1)/fs*1000,den(jj));
xlabel('Interior time (ms)');ylabel('Sum of squared window weights');
ylim([.4 1.1]);title('50% overlap: denominator is not constant');
subplot(1,2,2);step=max(1,floor(numel(x)/3000));
plot((0:step:numel(x)-1)/fs,err(1:step:end));
xlabel('Time (s)');ylabel('Reconstruction error (FS)');title('Normalized overlap-add');
end
