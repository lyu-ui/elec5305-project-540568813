function r2_plot(R, number)
    % R2_PLOT Regenerate report plots from audio and verified numerical outputs.
    % Figure 1 is an explanatory diagram supplied with the report.
    set(groot, 'defaultAxesFontName', 'Times New Roman', 'defaultTextFontName', 'Times New Roman', ...
        'defaultAxesFontSize', 11, 'defaultTextFontSize', 11);
    fig = figure('Color', 'w', 'Position', [80 80 1050 650]);
    % Keep exported labels readable even when the desktop uses a dark theme.
    if isprop(fig, 'Theme')
        fig.Theme = 'light';
    end
    D = R.frames;
    meta = R.meta;
    switch number
        case 1
            image(imread(fullfile(R.root, 'figures', 'fig01_pipeline.png')));
            axis image off;
        case 2
            for j = 1:2
                ids = ["clip_01", "clip_27"];
                subplot(2, 1, j);
                spectrum(R, ids(j), 3000);
                hold on;
                d = D(D.clip == ids(j), :);
                plot(d.time_s, d.pitch_hz, 'c', 'LineWidth', 1.3);
                plot(d.time_s, d.peak_hz, 'w', 'LineWidth', .5);
                title("Original recording " + string(char('A' + j - 1)));
            end
        case 3
            ids = ["clip_22", "clip_18", "clip_24"];
            for j = 1:3
                subplot(3, 1, j);
                spectrum(R, ids(j), 3500);
                hold on;
                d = D(D.clip == ids(j), :);
                r = meta(meta.clip == ids(j), :);
                p1 = plot(d.time_s, d.pitch_hz, 'c', 'LineWidth', 1.3);
                fref = 34000 ./ (4 * (d.length_ref_cm + .62 * r.radius_cm));
                p2 = plot(d.time_s, fref, 'w--', 'LineWidth', 1);
                title(sprintf('%s | %s | Reference MAE %.2f cm', ids(j), r.shape, mean(d.abs_error_cm)), 'Interpreter', 'none');
                legend([p1, p2], {'Model pitch', 'Linear-fill physics reference'}, 'Location', 'northwest', ...
                       'Color', [.15 .15 .15], 'TextColor', 'w', 'EdgeColor', [.5 .5 .5]);
            end
        case 4
            C = clip_summary(D);
            names = [R.model.names, {'score_mean'}];
            labels = {'Prominence (dB)', 'Competing amplitude ratio', 'log(1 + jump in cents)', ...
                    'Normalized entropy', 'Model support (dB)', 'Mean reliability score'};
            roles = ["development", "seen_test", "unseen_test"];
            marks = {'.', 'o', '^'};
            for j = 1:6
                subplot(2, 3, j);
                hold on;
                for k = 1:3
                    z = C(C.role == roles(k), :);
                    scatter(z.(names{j}), z.mae_cm, 32, marks{k}, 'DisplayName', role_label(roles(k)));
                end
                xlabel(labels{j});
                ylabel('Reference MAE (cm)');
                grid on;
                if j == 1
                    legend('Location', 'best', 'Interpreter', 'none');
                end
            end
        case 5
            roles = ["seen_test", "unseen_test"];
            titles = {"Test I: 7/8 development containers", "Test II: new containers"};
            methods = ["Combined", "Prominence", "Model support", "Random expectation", "Error oracle"];
            cov = [.7 .8 .9 1];
            % Shade the paired change of the combined score relative to 100%
            % retention (95% container bootstrap from results/), so the band
            % matches the tested quantity rather than between-container spread.
            B = readtable(fullfile(R.root, 'results', 'paired_container_bootstrap.csv'), 'TextType', 'string');
            for j = 1:2
                subplot(1, 2, j);
                hold on;
                full = mean(R.selective.mae_cm(R.selective.role == roles(j) & ...
                            R.selective.method == "Combined" & R.selective.coverage == 1));
                lower = full * ones(1, 4);
                upper = full * ones(1, 4);
                for a = 1:3
                    b = B(B.role == roles(j) & abs(B.coverage - cov(a)) < 1e-9, :);
                    assert(height(b) == 1, 'Missing paired bootstrap row.');
                    lower(a) = full + b.ci_low;
                    upper(a) = full + b.ci_high;
                end
                fill(100 * [cov fliplr(cov)], [lower fliplr(upper)], [.1 .42 .57], ...
                     'FaceAlpha', .18, 'EdgeColor', 'none', 'DisplayName', 'Combined: 95% paired-change interval');
                allVals = [lower upper];
                for k = 1:5
                    vals = zeros(1, 4);
                    for a = 1:4
                        z = R.selective(R.selective.role == roles(j) & ...
                                        R.selective.method == methods(k) & R.selective.coverage == cov(a), :);
                        vals(a) = mean(z.mae_cm);
                    end
                    allVals = [allVals vals]; %#ok<AGROW>
                    plot(100 * cov, vals, '-o', 'DisplayName', methods(k), 'LineWidth', 1.3);
                end
                xlabel('Retained predictions (%)');
                ylabel('Macro reference MAE (cm)');
                title(titles{j});
                pad = .08 * (max(allVals) - min(allVals));
                ylim([min(allVals) - pad, max(allVals) + pad]);
                grid on;
                if j == 1
                    legend('Location', 'southeast');
                end
            end
            sgtitle({'Shading: 95% container-bootstrap interval of the combined score''s paired change from 100% retention', ...
                     'Eight containers per group; panels use separate y-axis ranges'}, 'FontSize', 11);
        case 6
            C = clip_summary(D);
            roles = ["seen_test", "unseen_test"];
            for j = 1:2
                subplot(1, 2, j);
                z = C(C.role == roles(j), :);
                bar([z.mae_cm, z.geometry_mae_cm]);
                xticks(1:height(z));
                xticklabels(erase(z.clip, 'clip_'));
                xlabel('Clip number');
                ylabel('Reference MAE (cm)');
                title(role_label(roles(j)), 'Interpreter', 'none');
                grid on;
                if j == 1
                    legend('Linear-fill reference', 'Geometry-adjusted proxy');
                end
            end
        case 7
            ids = ["clip_28", "clip_32"];
            for j = 1:2
                subplot(2, 1, j);
                spectrum(R, ids(j), 3500);
                hold on;
                d = D(D.clip == ids(j), :);
                plot(d.time_s, d.pitch_hz, 'c', 'LineWidth', 1.3);
                r = meta(meta.clip == ids(j), :);
                title(ids(j) + " | " + r.container_id + " | " + r.shape, 'Interpreter', 'none');
            end
        case 8
            C = load(fullfile(R.root, 'data', 'lpc_control.mat'));
            [raw, fs] = audioread(fullfile(R.root, 'data', 'clip_01.wav'));
            signals = {C.control, raw(round(6.5 * fs) + 1:round(6.6 * fs))};
            titles = {'Known two-resonator control', 'Recording A at 6.50 to 6.60 s'};
            for j = 1:2
                subplot(1, 2, j);
                hold on;
                x = signals{j}(:);
                w = .5 - .5 * cos(2 * pi * (0:numel(x) - 1)' / (numel(x) - 1));
                power = abs(fft((x - mean(x)) .* w, 8192)).^2;
                power = power(1:4097);
                plot((0:4096) * fs / 8192, 10 * log10(max(power, 1e-30) / max(power)), 'Color', [.7 .7 .7], 'DisplayName', 'Windowed spectrum');
                for order = [8 16 32]
                    [a, g] = r2_lpc(x, order);
                    env = g ./ max(abs(fft(a, 2048)).^2, 1e-30);
                    env = env(1:1025);
                    plot((0:1024) * fs / 2048, 10 * log10(env / max(env)), 'DisplayName', sprintf('LPC order %d', order));
                end
                xlim([300 2500]);
                ylim([-65 3]);
                xlabel('Frequency (Hz)');
                ylabel('Relative level (dB)');
                title(titles{j});
                grid on;
                if j == 1
                    legend('Location', 'best');
                end
            end
        case 9
            labels = ["Noisy", "Estimated Wiener", "Oracle Wiener"];
            for j = 1:2
                subplot(1, 2, j);
                hold on;
                for k = 1:3
                    vals = zeros(1, 3);
                    errs = zeros(1, 3);
                    snrs = [0 10 20];
                    for a = 1:3
                        z = R.noise(R.noise.method == labels(k) & R.noise.input_snr_db == snrs(a), :);
                        if j == 1
                            v = z.output_snr_db;
                        else
                            v = z.peak_deviation_hz;
                        end
                        vals(a) = mean(v);
                        errs(a) = std(v);
                    end
                    errorbar(snrs, vals, errs, '-o', 'DisplayName', labels(k));
                end
                xlabel('Input SNR (dB)');
                grid on;
                if j == 1
                    ylabel('Output SNR (dB)');
                    legend('Location', 'best');
                else
                    ylabel('Band-maximum deviation (Hz)');
                end
            end
        case 10
            t = (0:15999)' / 16000;
            x = cos(2 * pi * 1000 * t) + .9 * cos(2 * pi * 1150 * t);
            [f, tt, P] = r2_stft(x, 640, 320, 2048);
            p = P(:, floor(numel(tt) / 2) + 1);
            centers = (exp(linspace(9.2789 * log(1 + .004368 * 300), 9.2789 * log(1 + .004368 * 5000), 20) / 9.2789) - 1) / .004368;
            W = max(0, 1 - abs(f - centers) ./ (24.673 * (1 + .004368 * centers)));
            pooled = (W' * p) ./ max(sum(W, 1)', 1e-30);
            plot(f, 10 * log10(max(p, 1e-30) / max(p)));
            hold on;
            plot(centers, 10 * log10(max(pooled, 1e-30) / max(pooled)), '-o');
            xlim([650 1600]);
            ylim([-65 3]);
            xlabel('Frequency (Hz)');
            ylabel('Relative power (dB)');
            legend('40 ms STFT', '20 ERB-spaced triangular bands');
            grid on;
        case 11
            d = readtable(fullfile(R.root, 'reference', 'model_predictions', 'clip_24.csv'));
            r = meta(meta.clip == "clip_24", :);
            subplot(1, 2, 1);
            plot(d.time_s, d.pitch_hz);
            hold on;
            scatter(d.time_s(end), d.pitch_hz(end), 40, 'filled');
            xlabel('Time (s)');
            ylabel('Model pitch (Hz)');
            title('Endpoint switch in clip 24');
            grid on;
            subplot(1, 2, 2);
            plot(d.time_s, d.length_ref_cm, 'k--');
            hold on;
            plot(d.time_s, d.length_pred_cm);
            plot(d.time_s, d.wavelength_cm / 4 - .62 * r.radius_cm);
            xlabel('Time (s)');
            ylabel('Air-column length (cm)');
            title('Effect of endpoint correction');
            legend('Linear-fill reference', 'Released endpoint correction', 'Known-radius diagnostic', 'Location', 'best');
            grid on;
    end
    out = fullfile(R.root, 'outputs', 'matlab');
    if isfield(R, 'out')
        out = R.out;
    end
    if ~exist(out, 'dir')
        mkdir(out);
    end
    % Hide interactive axes toolbars so exported images stay clean.
    ax = findall(fig, 'Type', 'axes');
    for k = 1:numel(ax)
        if isprop(ax(k), 'Toolbar') && ~isempty(ax(k).Toolbar)
            ax(k).Toolbar.Visible = 'off';
        end
    end
    exportgraphics(fig, fullfile(out, sprintf('figure_%02d.png', number)), 'Resolution', 180);
end

function label = role_label(role)
    % Display names: Test I shares 7/8 containers with score development.
    role = string(role);
    label = role;
    label(role == "development") = "Development";
    label(role == "seen_test") = "Test I (7/8 development containers)";
    label(role == "unseen_test") = "Test II (new containers)";
end

function spectrum(R, clip, top)
    r = R.meta(R.meta.clip == clip, :);
    x = audioread(fullfile(R.root, r.audio_file));
    x = x - mean(x);
    [f, t, P] = r2_stft(x, 640, 320, 2048);
    b = f >= 300 & f <= 5000;
    P = P(b, :);
    f = f(b);
    imagesc(t, f, 10 * log10(max(P, 1e-30) / max(P(:))));
    axis xy;
    ylim([300 top]);
    clim([-60 0]);
    colormap(parula);
    xlabel('Time (s)');
    ylabel('Frequency (Hz)');
    c = colorbar;
    c.Label.String = 'Relative power (dB)';
end

function C = clip_summary(D)
    ids = unique(D.clip, 'stable');
    records = {};
    for k = 1:numel(ids)
        d = D(D.clip == ids(k), :);
        records(end + 1, :) = {ids(k), d.role(1), mean(d.abs_error_cm), mean(d.geometry_proxy_error_cm), ...
                          mean(d.prom_db), mean(d.competition), mean(d.jump_cents_log), mean(d.entropy), mean(d.model_support_db), mean(d.reliability_score)}; %#ok<AGROW>
    end
    C = cell2table(records, 'VariableNames', {'clip', 'role', 'mae_cm', 'geometry_mae_cm', 'prom_db', 'competition', 'jump_cents_log', 'entropy', 'model_support_db', 'score_mean'});
end
