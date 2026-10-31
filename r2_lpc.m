function [a,g] = r2_lpc(x,p)
%R2_LPC Autocorrelation all-pole model, using base MATLAB only.
% The small diagonal load stabilizes nearly sinusoidal frames.
x=x(:)-mean(x);N=numel(x);x=x.*(0.5-0.5*cos(2*pi*(0:N-1)'/N));
r=zeros(p+1,1);
for k=0:p,r(k+1)=sum(x(1:end-k).*x(1+k:end))/N;end
r(1)=r(1)*(1+1e-6);a=[1;-(toeplitz(r(1:p))\r(2:p+1))];
g=max(r(1)+a(2:end)'*r(2:end),1e-30);
end
