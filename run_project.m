function R = run_project(playAudio, makeFigures)
    % RUN_PROJECT Recompute and validate the pouring-sound reliability experiments.
    %   R = run_project;              % numerical analysis and all figures
    %   R = run_project(true);        % also play original/processed audio
    %   R = run_project(false,false); % numerical checks only
    if nargin < 1
        playAudio = false;
    end
    if nargin < 2
        makeFigures = true;
    end
    validateattributes(playAudio, {'logical', 'numeric'}, {'scalar', 'real', 'finite'});
    validateattributes(makeFigures, {'logical', 'numeric'}, {'scalar', 'real', 'finite'});
    assert(playAudio == 0 || playAudio == 1, 'playAudio must be true or false.');
    assert(makeFigures == 0 || makeFigures == 1, 'makeFigures must be true or false.');
    root = fileparts(mfilename('fullpath'));
    addpath(root);
    required = {fullfile(root, 'reference', 'recording_manifest.csv'), ...
              fullfile(root, 'data', 'clip_01.wav'), ...
              fullfile(root, 'results', 'frame_features.csv')};
    for k = 1:numel(required)
        assert(isfile(required{k}), 'Missing input: %s. First run python python/setup_project.py; see README.md.', required{k});
    end
    R = r2_run(root);
    if makeFigures
        for number = 1:11
            r2_plot(R, number);
        end
    end
    if playAudio
        r2_listen(R, 'pours');
        r2_listen(R, 'comparison');
    end
    fprintf('Project completed: %d recordings | %d frames.\n', height(R.meta), height(R.frames));
    fprintf('Outputs: %s\n', fullfile(root, 'matlab_results'));
end
