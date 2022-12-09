sig0 = merge_IN0_detrend[:,0]
sig0_detrend = merge_IN0_detrend[:,1]
theta0 = membrane.slide_detect(sig0.magnitude[:,0], modelWaveform.magnitude[:,0])
SignalViewer_0.plot(sig0.times, theta0.θ)
theta0_detrend = membrane.slide_detect(sig0_detrend.magnitude[:,0], modelWaveform.magnitude[:,0])
SignalViewer_0.plot(sig0.times, theta0_detrend.θ)
theta0 = membrane.slide_detect(sig0.magnitude[:,0], modelWaveform_0.magnitude[:,0])
SignalViewer_0.plot(sig0.times, theta0.θ)
theta0_detrend = membrane.slide_detect(sig0_detrend.magnitude[:,0], modelWaveform_0.magnitude[:,0])
SignalViewer_0.plot(sig0.times, theta0_detrend.θ)
SignalViewer_0.plot(sig0.times, theta0.θ)

