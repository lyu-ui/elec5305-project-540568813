function result=ap_ratechange(x,fs)
%AP_RATECHANGE Controlled alias test and correctly labelled real-audio export.
% A symmetric FIR is applied by centered convolution: its causal 256-sample
% delay is compensated offline. Discard 50 ms edges in the synthetic test.
h=ap_fir(fs,6000,513); fsOut=fs/3;
t=(0:fs-1)'/fs;
tone=0.5*cos(2*pi*1000*t)+0.5*cos(2*pi*12000*t);
naive=tone(1:3:end); filtered=conv(tone,h,'same'); safe=filtered(1:3:end);
ii=(round(.05*fsOut)+1):(numel(naive)-round(.05*fsOut));
tt=(ii(:)-1)/fsOut;
amp=@(z,f) 2*abs(sum(z(ii).*exp(-2i*pi*f*tt)))/numel(ii);
a0=amp(naive,4000);a1=amp(safe,4000);suppression=20*log10(a0/a1);
H=abs(fft(h,65536));H=H(1:32769);f=(0:32768)'*fs/65536;
stopMax=max(20*log10(max(H(f>=8000),1e-16)));
result=table(a0,a1,amp(safe,1000),suppression,stopMax, ...
    'VariableNames',{'NaiveAlias_FS','FilteredAlias_FS','Retained1k_FS', ...
    'AliasSuppression_dB','StopbandMaximum_dB'});
assert(suppression>75 && abs(amp(safe,1000)-.5)<.001);
assert(abs(suppression-80.059500137)<1e-5);
% This rate change is a separate experiment, not a hidden baseline change.
y=conv(x,h,'same');y=y(1:3:end);
assert(max(abs(y))<1,'Derived audio would clip.');
audiowrite(fullfile('matlab_results','pour_A_16k.wav'),y,fsOut);
figure('Color','w','Position',[50 50 1050 420]);
subplot(1,2,1);plot(f/1000,20*log10(max(H,1e-10)));
xline(8,':');xlim([0 24]);ylim([-120 5]);
xlabel('Frequency (kHz)');ylabel('Gain (dB)');title('513-tap FIR; cutoff 6 kHz');
subplot(1,2,2);
[f,a]=ap_spectrum(naive(ii),fsOut,16384);
plot(f/1000,20*log10(max(a,1e-8)));hold on;
[f,a]=ap_spectrum(safe(ii),fsOut,16384);
plot(f/1000,20*log10(max(a,1e-8)));hold off;
xlim([0 8]);ylim([-130 0]);xlabel('Frequency (kHz)');
ylabel('Amplitude (dB re 1 FS)');title('48 to 16 kHz: known-tone test');
legend('Unfiltered decimation','FIR + decimation','Location','best');
end
