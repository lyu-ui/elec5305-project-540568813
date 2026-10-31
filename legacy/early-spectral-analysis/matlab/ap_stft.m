function out = ap_stft(x, fs, windowMs, overlapFraction, nfft)
%AP_STFT Explicit one-sided STFT, PSD and frame features (base MATLAB).
% M is the window length, O the overlap, H the hop, NFFT the FFT length.
% Complete frames only; center times follow the spectrogram convention.
% PSD is in full-scale amplitude squared per Hz. No frame normalization.
validateattributes(x, {'double'}, {'vector','real','finite','nonempty'});
validateattributes(fs, {'numeric'}, {'scalar','positive','finite'});
assert(windowMs > 0 && overlapFraction >= 0 && overlapFraction < 1);
x = x(:);
M = round(fs*windowMs/1000);
O = round(M*overlapFraction);
H = M-O;
assert(M >= 2 && H >= 1 && M <= numel(x), 'Invalid frame length.');
assert(nfft >= M && mod(nfft,2) == 0, 'Use an even NFFT >= M.');
starts = 0:H:(numel(x)-M);
indices = (1:M)' + starts;          % Each column is one complete frame.
frames = x(indices);
w = 0.5-0.5*cos(2*pi*(0:M-1)'/M); % Periodic Hann, no toolbox required.
S = fft(frames.*w,nfft,1);
S = S(1:nfft/2+1,:);
P = abs(S).^2/(fs*sum(w.^2));       % Two-sided PSD scaling first.
P(2:end-1,:) = 2*P(2:end-1,:);      % One-sided: retain DC and Nyquist.
f = (0:nfft/2)'*fs/nfft;
t = (starts+M/2)/fs;
band = f >= 300 & f <= 5000;        % Fixed exploratory peak-search band.
fb = f(band);
[~,ix] = max(P(band,:),[],1);
peak = reshape(fb(ix),1,[]);        % Band maximum, NOT a pitch estimate.
cb = f <= 8000;
centroid = sum(f(cb).*P(cb,:),1)./max(sum(P(cb,:),1),realmin);
frameRms = sqrt(mean(frames.^2,1)); % RMS of unwindowed, DC-removed frames.
out = struct('P',P,'f',f,'t',t,'peak',peak,'centroid',centroid, ...
    'rms',frameRms,'M',M,'H',H,'frames',numel(starts));
end
