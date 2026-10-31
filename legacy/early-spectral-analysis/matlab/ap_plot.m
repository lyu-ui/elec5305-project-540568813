function ap_plot(kind, varargin)
%AP_PLOT Plot helpers keep the Live Script's analysis blocks short.
switch kind
    case 'wave_fft'
        signals=varargin{1}; fs=varargin{2};
        figure('Color','w','Position',[50 50 1050 600]);
        colors=[0 .50 .53; .77 .34 .13];
        for j=1:2
            x=signals{j}; t=(0:numel(x)-1)'/fs;
            subplot(2,2,2*j-1);
            plot(t,x,'Color',colors(j,:),'LineWidth',0.5);
            xlabel('Time (s)'); ylabel('Amplitude (full scale)');
            title(sprintf('Recording %c: waveform','A'+j-1));
            xlim([0 numel(x)/fs]); ylim(1.1*max(abs(x))*[-1 1]);
            [f,a]=ap_spectrum(x,fs);
            subplot(2,2,2*j);
            plot(f/1000,20*log10(max(a,1e-8)),'Color',colors(j,:));
            xlabel('Frequency (kHz)'); ylabel('Amplitude (dB re 1 FS)');
            title(sprintf('Recording %c: whole-record Hann FFT','A'+j-1));
            xlim([0 8]); ylim([-100 0]);
        end
    case 'windows'
        x=varargin{1}; fs=varargin{2}; durations=[10 40 100];
        figure('Color','w','Position',[50 50 950 900]);
        for j=1:3
            b=ap_stft(x,fs,durations(j),0.5,8192);
            subplot(3,1,j); keep=b.f<=8000;
            imagesc(b.t,b.f(keep)/1000,10*log10(max(b.P(keep,:),1e-16)));
            axis xy; caxis([-105 -35]); ylim([0 8]);
            ylabel('Frequency (kHz)'); xlabel('Time (s)');
            title(sprintf('%d ms Hann | 50%% overlap | NFFT = 8192',durations(j)));
            cb=colorbar; ylabel(cb,'PSD (dB re 1 FS^2/Hz)');
        end
        colormap(parula);
    case 'features'
        base=varargin{1}; durations=varargin{2};
        figure('Color','w','Position',[50 50 1050 850]);
        colors=[0 .50 .53; .77 .34 .13];
        labels={'Band maximum (Hz)','Power centroid (Hz)','RMS (dB re 1 FS)'};
        for j=1:2
            b=base{j}; tau=b.t/durations(j);
            values={b.peak,b.centroid,20*log10(max(b.rms,1e-12))};
            for r=1:3
                subplot(3,2,2*(r-1)+j); y=values{r};
                plot(tau,y,'Color',colors(j,:),'LineWidth',0.6); hold on;
                for k=0:2
                    mask=tau>=k/3 & tau<(k+1)/3;
                    plot([k k+1]/3,median(y(mask))*[1 1],'k','LineWidth',2);
                end
                xline(1/3,':'); xline(2/3,':'); xlim([0 1]);
                ylabel(labels{r});
                if r==1, title(sprintf('Recording %c: 40 ms, 50%% overlap','A'+j-1)); end
                if r==3, xlabel('Normalized elapsed time (not fill fraction)'); end
                hold off;
            end
        end
    case 'padding'
        fs=48000;
        figure('Color','w','Position',[50 50 1050 400]);
        specs=[10 512;10 8192;100 8192];
        for j=1:3
            M=round(specs(j,1)*fs/1000);
            t=((0:M-1)'-(M-1)/2)/fs; % Tones aligned in phase at window center.
            y=cos(2*pi*1000*t)+cos(2*pi*1100*t);
            [f,a]=ap_spectrum(y,fs,specs(j,2));
            if j<3, subplot(1,2,1); else, subplot(1,2,2); end
            hold on;
            if j==1, style='o-'; else, style='-'; end
            plot(f,a,style,'LineWidth',1.2,'MarkerSize',3, ...
                'DisplayName',sprintf('%d ms / NFFT %d',specs(j,1),specs(j,2)));
        end
        for j=1:2
            subplot(1,2,j); xlim([700 1400]); ylim([0 2]);
            xline(1000,':','HandleVisibility','off');
            xline(1100,':','HandleVisibility','off');
            xlabel('Frequency (Hz)'); ylabel('One-sided amplitude');
            legend('show','Location','northeast');
            if j==1, title('Short window: padding alone');
            else, title('Longer window: two tones resolved'); end
            hold off;
        end
    otherwise
        error('Unknown plot kind: %s',kind);
end
end
