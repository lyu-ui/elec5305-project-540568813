function [f,a] = ap_spectrum(x,fs,nfft)
%AP_SPECTRUM Coherent-gain-corrected, one-sided Hann amplitude spectrum.
% For a nonstationary record this is a descriptive global representation;
% the peak height is not the amplitude of a stationary sinusoid.
x = x(:); N = numel(x);
if nargin < 3, nfft = 2^nextpow2(N); end
assert(nfft >= N && mod(nfft,2) == 0, 'Use even NFFT >= signal length.');
w = 0.5-0.5*cos(2*pi*(0:N-1)'/N);
X = fft(x.*w,nfft);
a = abs(X(1:nfft/2+1))/sum(w);
a(2:end-1) = 2*a(2:end-1);
f = (0:nfft/2)'*fs/nfft;
end
