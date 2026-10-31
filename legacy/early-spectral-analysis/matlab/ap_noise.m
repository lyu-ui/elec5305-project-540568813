function result=ap_noise(x,fs)
%AP_NOISE Measured noise benchmark; reference is band-limited real audio.
% Five stored noise realizations ensure NumPy/MATLAB use identical inputs.
% SNR measures added distortion against this constructed reference, not the
% unknown physical SNR of the original field recording.
h=ap_fir(fs,6000,513); segment=x(2*fs+1:6*fs);
s=conv(segment,h,'same');N=numel(s);
bank=load('noise_bank.mat','noiseBank');
assert(isequal(size(bank.noiseBank),[N 5]),'Unexpected noise bank.');
valid=(round(.04*fs)+1):(N-round(.04*fs));
b=ap_stft(s,fs,40,.5,8192);
frameValid=b.t>=.06 & b.t<=N/fs-.06;
snrs=[0 10 20]; rows=zeros(3,5);
for j=1:3
    outSNR=zeros(1,5);inMAE=zeros(1,5);outMAE=zeros(1,5);
    for k=1:5
        v=bank.noiseBank(:,k);v=v-mean(v);
        v=v*sqrt(mean(s(valid).^2)/(10^(snrs(j)/10)*mean(v(valid).^2)));
        z=s+v; y=conv(z,h,'same');
        measured=10*log10(sum(s(valid).^2)/sum(v(valid).^2));
        assert(abs(measured-snrs(j))<1e-9);
        outSNR(k)=10*log10(sum(s(valid).^2)/sum((y(valid)-s(valid)).^2));
        bi=ap_stft(z,fs,40,.5,8192);bo=ap_stft(y,fs,40,.5,8192);
        inMAE(k)=mean(abs(bi.centroid(frameValid)-b.centroid(frameValid)));
        outMAE(k)=mean(abs(bo.centroid(frameValid)-b.centroid(frameValid)));
        if j==2 && k==1, shown={b,bi,bo}; end
    end
    rows(j,:)=[snrs(j),mean(outSNR),std(outSNR),mean(inMAE),mean(outMAE)];
end
result=array2table(rows,'VariableNames',{'InputSNR_dB','OutputSNR_mean_dB', ...
    'OutputSNR_SD_dB','CentroidMAE_input_Hz','CentroidMAE_output_Hz'});
assert(max(abs(rows(:,2)-[6.0549710246;16.0426251608;25.9207498661]))<1e-6);
assert(max(abs(rows(:,5)-[617.084155061;136.710604781;19.512462360]))<1e-5);
figure('Color','w','Position',[50 50 1050 420]);
subplot(1,2,1);errorbar(rows(:,1),rows(:,2),rows(:,3),'o-');hold on;
plot([0 20],[0 20],'--');hold off;
xlabel('Added-noise input SNR (dB)');ylabel('Output SNR against reference (dB)');
title('Five fixed noise realizations');legend('Filtered: mean +/- SD','Unprocessed');
subplot(1,2,2);hold on;
for j=1:3
    z=shown{j};plot(z.f/1000,10*log10(max(mean(z.P,2),1e-16)));
end
hold off;xlim([0 24]);ylim([-140 -40]);
xlabel('Frequency (kHz)');ylabel('Mean PSD (dB re 1 FS^2/Hz)');
title('Spectral effect at 10 dB input SNR');
legend('Band-limited reference','10 dB noisy','Filtered noisy','Location','best');
end
