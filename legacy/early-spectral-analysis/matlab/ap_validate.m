function ap_validate(signals,base,stageRows,windowRows,overlapRows,fs)
%AP_VALIDATE Numerical checks for the fixed report configuration.
% Parseval check: integrating a frame PSD must recover its window-weighted
% mean-square amplitude. This checks units and one-sided scaling.
b=base{1}; M=b.M; w=0.5-0.5*cos(2*pi*(0:M-1)'/M);
weightedPower=sum((signals{1}(1:M).*w).^2)/sum(w.^2);
integratedPSD=sum(b.P(:,1))*(fs/8192);
assert(abs(integratedPSD-weightedPower) < 1e-12*max(1,weightedPower));
fprintf('PSD scaling check passed; absolute error %.3g.\n', ...
    abs(integratedPSD-weightedPower));

% Optional comparison against MATLAB's standard toolbox function.
if exist('spectrogram','file')==2 && license('test','Signal_Toolbox')
    [~,F,T,P]=spectrogram(signals{1},w,M/2,8192,fs);
    relError=max(abs(P(:)-b.P(:)))/max(b.P(:));
    assert(relError<1e-9 && max(abs(F(:)-b.f(:)))<1e-9);
    assert(max(abs(T(:)-b.t(:)))<1e-9);
    fprintf('spectrogram cross-check passed; relative error %.3g.\n',relError);
end

% Check bundled-data results against an independent NumPy calculation.
expectedPeak=[503.90625;755.859375;1593.75;468.75;761.71875;996.09375];
expectedCentroid=[1946.245205667;1820.048659961;1832.123465965; ...
    1727.411277674;1656.764954544;1466.970102999];
expectedRms=[-43.007513995;-49.399396735;-58.613191834; ...
    -41.934626626;-50.131680502;-66.016481842];
assert(max(abs(stageRows(:,3)-expectedPeak))<1e-6);
assert(max(abs(stageRows(:,4)-expectedCentroid))<1e-6);
assert(max(abs(stageRows(:,5)-expectedRms))<1e-6);
assert(isequal(windowRows(:,5),[2930;731;292]));
assert(isequal(overlapRows(:,3),[366;731;1462]));
fprintf('All bundled-data reference checks passed.\n');
end
