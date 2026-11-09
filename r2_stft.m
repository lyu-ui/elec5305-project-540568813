function [f, t, P] = r2_stft(x, M, H, N)
    % R2_STFT Complete-frame periodic-Hann one-sided power spectral density.
    % Input audio is 16 kHz mono, double, and DC-removed by the caller.
    fs = 16000;
    x = x(:);
    starts = 0:H:(numel(x) - M);
    w = 0.5 - 0.5 * cos(2 * pi * (0:M - 1)' / M);
    S = fft(x((1:M)' + starts) .* w, N, 1);
    S = S(1:N / 2 + 1, :);
    P = abs(S).^2 / (fs * sum(w.^2));
    P(2:end - 1, :) = 2 * P(2:end - 1, :);
    f = (0:N / 2)' * fs / N;
    t = (starts + M / 2)' / fs;
end
