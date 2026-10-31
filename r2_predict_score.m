function q = r2_predict_score(D,model)
% Higher q means lower predicted log error. This is not a probability.
Z=[ones(height(D),1),(D{:,model.names}-model.mu)./model.sd];
q=-Z*model.beta;
end
