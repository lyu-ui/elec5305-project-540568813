function h=ap_fir(fs,fc,taps)
%AP_FIR Odd-length symmetric Hamming-windowed sinc, normalized at DC.
% Base MATLAB implementation; fc is the ideal cutoff, not a brick-wall edge.
assert(mod(taps,2)==1 && fc>0 && fc<fs/2);
n=(-(taps-1)/2:(taps-1)/2)'; u=2*fc/fs*n;
v=ones(size(u)); mask=u~=0; v(mask)=sin(pi*u(mask))./(pi*u(mask));
w=0.54-0.46*cos(2*pi*(0:taps-1)'/(taps-1));
h=(2*fc/fs)*v.*w; h=h/sum(h);
end
