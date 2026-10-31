function z = r2_wiener(x,n,calibration,kind)
%R2_WIENER Power-domain Wiener masks with normalized weighted overlap-add.
% Estimated mask uses only the mixture plus a disjoint noise-only segment.
% Oracle mask knows clean/noise STFTs and is an analysis benchmark only.
L=640;hop=160;w=0.5-0.5*cos(2*pi*(0:L-1)'/L);tiny=1e-30;
x=x(:);n=n(:);ns=numel(x);s=[zeros(L,1);x;zeros(L,1)];
noise=[zeros(L,1);n;zeros(L,1)];starts=0:hop:(numel(s)-L);
ix=(1:L)'+starts;S=fft(s(ix).*w,L,1);N=fft(noise(ix).*w,L,1);
S=S(1:L/2+1,:);N=N(1:L/2+1,:);Y=S+N;
switch kind
    case 'identity',G=ones(size(Y));
    case 'oracle',G=abs(S).^2./max(abs(S).^2+abs(N).^2,tiny);
    otherwise
        ci=(1:L)'+(0:hop:(numel(calibration)-L));
        C=fft(calibration(ci).*w,L,1);psd=mean(abs(C(1:L/2+1,:)).^2,2);
        p=abs(Y).^2;sm=zeros(size(p));sm(:,1)=p(:,1);
        for k=2:size(p,2),sm(:,k)=0.8*sm(:,k-1)+0.2*p(:,k);end
        G=max(0.05,1-psd./max(sm,tiny));
end
Q=Y.*G;full=[Q;conj(Q(end-1:-1:2,:))];frames=real(ifft(full,L,1)).*w;
z=zeros(size(s));den=zeros(size(s));
for k=1:numel(starts),ii=starts(k)+(1:L);z(ii)=z(ii)+frames(:,k);den(ii)=den(ii)+w.^2;end
z=z./max(den,tiny);z=z(L+1:L+ns);
end
