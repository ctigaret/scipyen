sig0 = merge_IN0[:,0]
sig_dc = merge_IN0[:,1]
theta = membrane.slide_detect(sig_dc.magnitude[:,0], modelWabeform.magnitude[:,0])
theta = membrane.slide_detect(sig_dc.magnitude[:,0], modelWaveform.magnitude[:,0])
SignalViewer_0.plot(theta.θ)
theta_dc = membrane.slide_detect(sig_dc.magnitude[:,0], modelWaveform.magnitude[:,0])
theta = membrane.slide_detect(sig.magnitude[:,0], modelWaveform.magnitude[:,0])
theta = membrane.slide_detect(sig0.magnitude[:,0], modelWaveform.magnitude[:,0])
SignalViewer_0.plot(theta.θ)
SignalViewer_0.plot(theta.α)
SignalViewer_0.plot(theta.β)
SignalViewer_0.plot(sig0.times, theta.θ)
SignalViewer_0.plot(sig0.times, theta.α)
SignalViewer_0.plot(sig0.times, theta.β)
SignalViewer_0.plot(sig0.times, theta.ε)
SignalViewer_0.plot(sig0.times, theta.σ)
SignalViewer_0.plot(sig0.times, theta.σ/modelWaveform.shape[0])
SignalViewer_0.plot(sig0.times, np.sqrt(theta.σ/modelWaveform.shape[0]))
SignalViewer_0.plot(sig0_dc.times, np.sqrt(theta_dc.σ/modelWaveform.shape[0]))
SignalViewer_0.plot(sig0_dc.times, np.sqrt(theta_dc.σ/modelWaveform.shape[0]))
SignalViewer_0.plot(sig0_dc.times, theta_dc.β)
SignalViewer_0.plot(sig0_dc.times, np.sqrt(theta_dc.σ/modelWaveform.shape[0]))
SignalViewer_0.plot(sig0_dc.times, theta_dc.β / np.sqrt(theta_dc.σ/modelWaveform.shape[0]))
SignalViewer_0.plot(sig0_dc.times, theta_dc.θ)
SignalViewer_0.plot(sig0_dc.times, theta_dc.β / np.sqrt(theta_dc.σ/modelWaveform.shape[0]))
SignalViewer_0.plot(sig0_dc.times, theta_dc.θ)
SignalViewer_0.plot(sig0_dc.times, theta_dc.ε)
SignalViewer_0.plot(sig0_dc.times, theta_dc.β / np.sqrt(theta_dc.σ/(modelWaveform.shape[0]-1)))
reload(membrane)
theta = membrane.slide_detect(sig0.magnitude[:,0], modelWaveform.magnitude[:,0])
theta_dc = membrane.slide_detect(sig0_dc.magnitude[:,0], modelWaveform.magnitude[:,0])
SignalViewer_0.plot(sig0_dc.times, theta_dc.θ)
SignalViewer_0.plot(sig0_dc.times, theta_dc.β / np.sqrt(theta_dc.ε/(modelWaveform.shape[0]-1)))
SignalViewer_0.plot(sig0_dc.times, theta_dc.ε)
theta_dc = membrane.slide_detect(sig0_dc.magnitude[:,0], modelWaveform_1.magnitude[:,0])
SignalViewer_0.plot(sig0_dc.times, theta_dc.ε)
SignalViewer_0.plot(sig0.times, theta.ε)
theta_dc = membrane.slide_detect(sig0_dc.magnitude[:,0], modelWaveform_2.magnitude[:,0])
SignalViewer_0.plot(sig0_dc.times, theta_dc.ε)
sig0_dc_norm = sigp.normalise_waveform(sig0_dc)
sig0_norm = sigp.normalise_waveform(sig0)
sig0_norm_dc = sigp.remove_dc(sig0_norm)
theta = membrane.slide_detect(sig0_norm_dc.magnitude[:,0], modelWaveform.magnitude[:,0])
SignalViewer_0.plot(sig0_norm_dc.times, theta.ε)
sig0_norm_dc_ε = np.concatenate(sig0_norm_dc.magnitude, theta.ε[:,np.newaxis]], axis=1)
sig0_norm_dc_ε = np.concatenate([sig0_norm_dc.magnitude, theta.ε[:,np.newaxis]], axis=1)
ε_norm = sigp.normalise_waveform(theta.ε)
sig0_norm_dc_ε = np.concatenate([sig0_norm_dc.magnitude, ε_norm[:,np.newaxis]], axis=1)
α_norm - sigp.normalise_waveform(theta.α)
α_norm = sigp.normalise_waveform(theta.α)
β_norm = sigp.normalise_waveform(theta.β)
sig0_norm_dc_α_β_ε = np.concatenate([sig0_norm_dc.magnitude, α_norm[:,np.newaxis], β_norm[:,np.newaxis], ε_norm[:,np.newaxis]], axis=1)
np.dot(modelWaveform.magnitude[:,0], modelWaveform.magnitude[:,0]) == np.sum(modelWaveform.magnitude[:,0] * modelWaveform.magnitude[:,0])
