function r2_listen(R,selection)
%R2_LISTEN Sequential playback with blocking; begin at a low device volume.
% No separate normalization of the processed comparisons is performed.
switch selection
    case 'pours'
        for name=["clip_01","clip_27"]
            i=R.meta.clip==name;[x,fs]=audioread(fullfile(R.root,R.meta.audio_file(i)));
            fprintf('Playing %s. Listen for rising resonances and splash transients.\n',name);
            playblocking(audioplayer(.8*x/max(abs(x)),fs));
        end
    otherwise
        keys={'original','noisy','estimated','oracle'};
        for k=1:4
            fprintf('Playing %s, common comparison gain. Listen for hiss and tonal changes.\n',keys{k});
            playblocking(audioplayer(R.audio.(keys{k}),16000));
        end
end
end
