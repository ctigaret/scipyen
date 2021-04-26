===================================================================
Action potential (AP) detection and analysis in I-clamp experiment.
===================================================================

Performs action potential (AP) detection and analysis in data from a single 
I-clamp experiment (a "run") with a series of increasing depolarizing current 
injection steps (one injection per "sweep").

Parameters:
-----------
data : neo.Block, list of neo.Segment, or a neo.Segment.

    Contains the recording from one run of a series of depolarizing current          injections steps.

    When a **neo.Block** or a list of **neo.Segment** objects, each segment corresponds to one recorded sweep with a rectangular current injection *step*.

    When a single **neo.Segment**, this contains data from a single step current injection.

    Prerequisites:

    1. Each segment must contain two analog signals (**neo.AnalogSignal**):
        * recorded membrane potential
        * the injected current

        The amount of injected current is different in each segment, but the duration of the current injection step is the same in all segments.

Var-keyword parameters (kwargs):
--------------------------------

.. NOTE:: Unless specified otherwise, the string values are case-sensitive

cell : str (default, "NA"). The Cell ID

source : str (default, "NA"). Source ID (e.g. animal)

genotype: str (default "NA"). genotype (e.g., WT, HET, HOM or any other appropriate string)

sex : str (default "M")

sex : either "F" or "M"

.. NOTE:: Case-insensitive

treatment : str (default "veh") ATTENTION: case-sensitive!

age : python Quantity (one of days, months, years), "NA" or None 
        Default is None; either None or "NA" result in the string "NA" for age

post_natal : bool (default True)

thr : float or python Quantity
        value of the dV/dt (in V/s) above which the waveform belongs to an AP.
        optional; default is 20 V/s

    VmSignal: int or str
        integer index, or name (string) of the Vm analog signal
        optional; default is "Vm_prim_1"
        
    ImSignal = int or str
        index, or name (string) of the Im analog signal
        optional; default is "Im_sec_1"
        
    Iinj_0: python quantity (pA), float scalar, or None: value of the first injected current
        When None (default) the value will be determined from the Im signal of the first
        depolarization step
    
    delta_I: python quantity (pA), float scalar, or None: size of the current injection increment
        When None (defaut) the value will be determined from the Im signal
        
    Iinj: None (default), or sequence of current injection values. When not None,
        this must contain as many elements as injection steps, and these must be
        python quantities in units compatible with pA
        
        
    rheo: boolean, default True
    
        When True, the function attempts to calculate the rheobase & membrane
        time constant using rheobase_latency() function.
        
        This assumes that data is a neo.Block or a sequence of neo.Segment
        containing records of different current injection step amplitudes
        (one segment for each value of depolarizing current intensity).
        
        This parameter is ignored when data has lees than minsteps segments
        
    minsteps: int (default is 3)
        minimum number of curent injection steps where APs were triggered, for
        performing rheobase-latency analysis
        
    name: str
        name of the results (string), or None; 
        optional; default is None
        
    plot_rheo: boolean, default is True 
        (plots the fitted curve) -- useful when a block or a list of segments is
        analyzed 
        
    The following are used by analyse_AP_step_injection():
    ========================================================
    tail: scalar Quantity (units: "s"); default is 0 s
        duration of the analyzed Vm trace after current injection has ceased
    
    
    resample_with_period: None (default), scalar float or Quantity
        When not None, the Vm signal will be resampled before processing.
        
        When Quantity, it must be in units convertible (scalable) to the signal's
        sampling period units.
        
        Resampling occurs on the region corresponding to the depolarizing current
        injection, before detection of AP waveforms.
        
        Upsampling might be useful (see Naundorf et al, 2006) but slows down
        the execution. To upsample the Vm signal, pass here a value smaller than
        the sampling period of the Vm signal.
        
    resample_with_rate: None (default), scalar float or Quantity
        When not None, the Vm signal will be resampled before processing.
        
        When Quantity, it must be in units convertible (scalable) to the signal's
        sampling rate units.
        
        Resampling occurs on the region corresponding to the depolarizing current
        injection, before performing detection of AP waveforms.
        
        Upsampling might be useful (see Naundorf et al, 2006) but slows down
        the execution. To upsample the Vm signal, pass here a value larger than 
        the sampling period of the Vm signal.
        
    box_size: int >= 0; default is 0.
    
        size of the boxcar (scipy.signal.boxcar) used for filtering the Im signal
        (containing the step current injection) before detecting the step 
        boundaries (start & stop)
        
        default is 0 (no boxcar filtering)
        
    method: str, one of "state_levels" (default) or "kmeans"
    
    adcres, adcrange, adcscale: float scalars, see signalprocessing.state_levels()
        called from ephys.parse_step_waveform_signal() 
        
        Used only when method is "state_levels"
        
    thr: floating point scalar: the minimum value of dV/dt of the Vm waveform to
        be considered an action potential (default is 10) -- parameter is passed to detect_AP_waveforms_in_train()
        
    before, after: floating point scalars, or Python Quantity objects in time 
        units convertible to the time units used by VmSignal.
        interval of the VmSignal data, respectively, before and after the actual
        AP in the returned AP waveforms -- parameters are passed to detect_AP_waveforms_in_train()
        
        defaults are:
        before: 1e-3
        after: None
        
    min_fast_rise_duration : None, scalar or Quantity (units "s");
    
        The minimum duration of the initial (fast) segment of the rising 
        phase of a putative AP waveform.
        
        When None, is will be set to the next higher power of 10 above the sampling period
        of the signal.
    
    min_ap_isi : None, scalar or Quantity;
    
                Minimum interval between two consecutive AP fast rising times 
                ("kinks"). Used to discriminate against suprious fast rising time
                points that occur DURING the rising phase of AP waveforms.
                
                This can happen when the AP waveforms has prominent IS and the SD 
                "spikes", 
                
                see Bean, B. P. (2007) The action potential in mammalian central neurons.
                Nat.Rev.Neurosci (8), 451-465

    rtol, atol: float scalars;
        the relative and absolute tolerance, respectively, used in value 
        comparisons (see numpy.isclose())
        
        defaults are:
        rtol: 1e-5
        atol: 1e-8
                
    use_min_detected_isi: boolean, default True
    
        When True, individual AP waveforms cropped from the Vm signal "sig" will
            have the duration equal to the minimum detected inter-AP interval.
        
        When False, the durations of the AP waveforms will be taken to the onset
            of the next AP waveform, or the end of the Vm signal
            
    smooth_window: int >= 0; default is 5
        The length (in samples) of a smoothing window (boxcar) used for the 
        signal's derivatives.
        
        The length of the window will be adjusted if the signal is upsampled.
        
    interpolate_roots: boolean, default False
        When true, use linear inerpolation to find the time coordinates of the
        AP waveform rise and decay phases crossing over the onset, half-maximum
        and 0 mV. 
        
        When False, use the time coordinate of the first & last sample >= Vm value
        (onset, half-max, or 0 mV) respectively, on the rise and decay phases of
        the AP waveform.
        
        see ap_waveform_roots()
        
    decay_intercept_approx: str, one of "linear" (default) or "levels"
        Used when the end of the decay phase cannot be estimated from the onset
        Vm.
        
        The end of the decay is considerd to be the time point when the decaying
        Vm crosses over (i.e. goes below) the onset value of the action potential.
        
        Whe the AP waveform is riing on a rising baseline, this time point cannot
        be determined.
        
        Instead, it is estimated as specified by "decay_intercept_approx" parameter:
        
        When decay_intercept_approx is "linear", the function uses linear extrapolation
        from a (higher than Vm onset) value specified by decay_ref (see below)
        to the onset value.
        
        When decay_intercept_approx is "levels", the function estimates a "pseudo-baseline"
        as the lowest of two state levels determined from the AP waveform histogram.
        
        The pseudo-baseline is then used to estimate the time intercept on the decay
        phase.
        
    decay_ref: str, one of "hm" or "zero", or floating point scalar
        Which Vm value should be used to approximate the end of the decay phase
        when using the "linear" approximation method (see above)
        
    get_duration_at_Vm: also get AP waveform duration at specified Vm,
        (in addition to Vhal-max and V0)
            default: -15 mV

    NOTE: See analyse_AP_step_injection() documentation for details
    
    Returns:
    ---------
    
    ret: ordered dict with the following key/value pairs:
    
        "Name": str or None; 
            the name parameter
            
        "Segment_k" where k is a running counter (int): a dictionary with the
            following key/value pairs:
            
            "Name": the name of the kth segment
            
            "AP_analysis": the result returned by calling analyse_AP_step_injection on
                the kth segment
            
            "Vm_signal": the region of the Vm signal in the kth segment, that 
                has been analyzed (possibly, upsampled); this corresponds to the
                current injection step or longer as specified by the "tail" 
                parameter to the analyse_AP_step_injection function, so it is usually only
                a time slice of the original Vm signal.
        
        ret["Injected_current"] : neo.IrregularlySampledSignal
            The intensity of the injected current step, one per segment.
                                            
        ret["Reference_AP_threshold"] : neo.IrregularlySampledSignal
            values of Vm at AP threshold, one per segment.
            
        ret["Reference_AP_latency"] : neo.IrregularlySampledSignal
            the latency of the first AP detected (time from start of step current 
            injection), one per segment.
            
        ret["Mean_AP_Frequency"] : neo.IrregularlySampledSignal
            mean AP frequency (ie. number of APs / duration of the current injection
            step, expressed in Hz), one for each segment,
            
        ret["Inter_AP_intervals"]   = list of arrays with inter-AP intervals
            (one array per segment) or None for segments without APs
        
        ret["AP_peak_values"]            = list of arrays with AP_peak_values
            (one for each segment, or None for segments without APs)
            
        ret["AP_peak_amplitudes"]        = list of arrays with AP amplitudes
            (one for each segment or None for segments without APs)
        
        ret["AP_durations_at_half-max"]     = list of arrays with AP width at 1/2 max
            (one for eaxch segment or None for segments without APs)
            
        ret["AP_durations_V_0"]         = list of arrays with AP width at Vm = 0
            (one for each segment, or None for segments without APs)
            
        ret["AP_durations_V_onset"]    = list of arrays with AP_width_at_threshold vm
            (one for each segment or None for segments without APs)
            
        ret["AP_maximum_dV_dt"]          = list of arrays with the maximum dV/dt per AP
            (one for each segment, or None for segments without APs)
    
    NOTE: the lengths of the arrays returned as list elements equals the number of APs
        detected in the corresponding segment; if no APs are detected, None is inserted
        instead of an empty array.
        

