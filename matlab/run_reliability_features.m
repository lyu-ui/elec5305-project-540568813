% Preliminary acoustic reliability diagnostics on two existing recordings.
% IMPORTANT: These are unsupervised acoustic descriptors, NOT validation
% of physical fill-level accuracy or the official pretrained model.
% Paths are resolved relative to this script, independently of Current Folder.
clear; close all; clc;
scriptDir = fileparts(mfilename('fullpath'));
projectDir = fileparts(scriptDir);
addpath(scriptDir);
resultsDir = fullfile(projectDir,'results');
if ~exist(resultsDir,'dir'), mkdir(resultsDir); end
files = {'pour_A.wav','pour_B.wav'};
rows = [];
for j=1:numel(files)
    [x,fs] = audioread(fullfile(projectDir,'data',files{j}));
    x=mean(x,2); x=x-mean(x);
    b=ap_stft(x,fs,40,0.5,8192);
    band=b.f>=300 & b.f<=5000;
    f=b.f(band); S=b.P(band,:);
    % Frame-wise top two local spectral peaks (exclude neighbouring bins).
    n=size(S,2); prom=nan(1,n); ratio=nan(1,n); entropy=nan(1,n);
    peakFreq=nan(1,n);
    for k=1:n
        a=S(:,k); total=sum(a);
        if total<=realmin, continue; end
        [p1,idx1]=max(a); peakFreq(k)=f(idx1);
        % Peak contrast against the band median (dB).
        prom(k)=10*log10((p1+realmin)/(median(a)+realmin));
        available=true(size(a));
        exclusionHz=100;
        available(abs(f-f(idx1))<=exclusionHz)=false;
        if any(available)
            p2=max(a(available)); ratio(k)=p2/max(p1,realmin);
        end
        prob=a/total; prob=prob(prob>0);
        entropy(k)=-sum(prob.*log(prob))/log(numel(a));
    end
    jump=[NaN abs(diff(peakFreq))]; % Hz per hop; heuristic ridge switching
    for k=1:n
        rows=[rows;j,b.t(k),peakFreq(k),prom(k),ratio(k),jump(k),entropy(k)]; %#ok<AGROW>
    end
    fig=figure('Visible','off','Color','w','Position',[90 90 1100 720]);
    subplot(2,1,1);
    imagesc(b.t,b.f,10*log10(max(b.P,realmin))); axis xy; ylim([300 5000]);
    colormap('parula'); colorbar; hold on;
    plot(b.t,peakFreq,'w','LineWidth',0.8);
    xlabel('Time (s)');ylabel('Frequency (Hz)');
    title(sprintf('Recording %s: STFT and band-maximum trajectory (not model pitch)',files{j}),'Interpreter','none');
    subplot(2,1,2);
    plot(b.t,prom,'DisplayName','Peak prominence (dB)');hold on;
    plot(b.t,ratio*20,'DisplayName','Competing-mode ratio x20');
    plot(b.t,entropy*20,'DisplayName','Normalised entropy x20');
    xlabel('Time (s)');ylabel('Descriptive feature (scaled for display)');
    legend('Location','best');grid on;title('Frame-wise acoustic diagnostics');
    exportgraphics(fig,fullfile(resultsDir,sprintf('preliminary_diagnostics_%s.png',files{j}(1:6))),'Resolution',140);
    close(fig);
end
T=array2table(rows,'VariableNames',{'Recording','Time_s','BandPeak_Hz', ...
    'RidgeProminence_dB','CompetingModeRatio','PeakJump_Hz','SpectralEntropy'});
writetable(T,fullfile(resultsDir,'preliminary_reliability_features.csv'));
disp(['Saved diagnostic CSV and spectrogram figures to: ',resultsDir]);
disp('No ground-truth error or model reliability conclusion is calculated.');
