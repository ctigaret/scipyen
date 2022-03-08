"""
WARNING code in this script to be executed block by block by copy/paste into 
PICT console as it requires modules imported into PICT console workspace

Blocks are deliminited by BEGIN / END comment statements. The code can be 
either copied & pasted or dragged into PICT console, where it can be edited and/or
navigated through and executedas if it was typed directly into the console.

CAUTION: 2022-03-08 22:42:50
Function signatures in ephys.membrane module have changed since this script was 
written - use it as a guide, and NOT verbatim !

"""
# using replcate data (option 1)
AP_analysis_0000 = membrane.analyse_AP_step_series_replicate(trains_0000, 
thr=20, name="AP_analysis_0000")

AP_analysis_0000_300pA = 
membrane.summarise_AP_analysis_at_depol_step(AP_analysis_0000, test_current = 
300*pq.pA, name="AP_analysis_0000")

AP_analysis_0000_300pA_summary, AP_analysis_0000_300pA_params, 
AP_analysis_0000_300pA_waveforms = 
membrane.report_AP_analysis(AP_analysis_0000_300pA, "AP_analysis_0000_300pA")



#### BEGIN primary analysis of AP trains and extraction of duration & AP frequency data
injection_steps = ("300", "500", "700", "900", "1100")

prefix = "CACNA1C187fHE_19h09_c04"

drugs = ("control", "isr", "isr_aga", "isr_aga_cd")
 
for n in ('trains_0001', 
          'trains_0002', 
          'trains_0003', 
          'trains_0004', 
          'trains_0005',
          'trains_isr_0000', 
          'trains_isr_0001', 
          'trains_isr_0002', 
          'trains_isr_aga_0000', 
          'trains_isr_aga_0001', 
          'trains_isr_aga_0002', 
          'trains_isr_aga_cd_0000', 
          'trains_isr_aga_cd_0001', 
          'trains_isr_aga_cd_0002', 
          'trains_isr_aga_cd_0003'):
    d = eval(n)
    vmim = membrane.extract_Vm_Im(d, t0=0.03*pq.s, t1=0.53*pq.s)
    
# NOTE: 2022-03-08 22:45:02
#### BEGIN
# alternatively, when Im signal is not available/usable:
protocols = neoutils.getABFProtocolEpochs(d)
# manually inspect protocols then set up i0, delta_i, istart and istop manually:
i0 = rheo_0000_protocols[0].loc["First Level", "B"]
di = rheo_0000_protocols[0].loc["Delta Level", "B"]
istart = rheo_0000_protocols[0].loc["First duration (ms)", "A"]
istop = rheo_0000_protocols[0].loc["First duration (ms)", "A"] + rheo_0000_protocols[0].loc["First duration (ms)", "B"]
# run primary analysis:
result = membrane.analyse_AP_step_injection_series(d, VmSignal = "Vm_prim_0", 
                                                   Iinj_0 = i0, delta_I = di, 
                                                   Istart = istart, Istop = istop, 
                                                   Itimes_relative=True, thr=20)

#### END





    analysis = membrane.analyse_AP_step_injection_series(vmim, thr=20, resample_with_period=1e-5*pq.s)
    apds = membrane.get_AP_param_vs_injected_current(analysis, "AP_durations_at_Ref_Vm")
    freqvsiinj = membrane.get_AP_frequency_vs_injected_current(analysis, name="Mean AP Frequency")
    assignin(vmim, "%s_%s_VmIm" % (prefix, n))
    assignin(analysis, "%s_%s_AP_analysis" % (prefix,n))
    assignin(apds, "%s_%s_AP_durations_15mV" % (prefix,n))
    assignin(freqvsiinj, "%s_%s_AP_freq_v_Iinj" % (prefix, n))

del(d, analysis, vmim, apds, freqvsiinj, n)

#### END  primary analysis of AP trains and extraction of duration & AP frequency data

#### BEGIN one off extraction of AP freq v injected current post hoc
#for n in ():
    #analysis  = eval(n)
    #freqvsiinj = membrane.get_AP_frequency_vs_injected_current(analysis, name="Mean AP Frequency")
    #new_name = n.replace("AP_analysis", "AP_freq_v_Iinj")
    #assignin(freqvsiinj, new_name)
    
##### END one off extraction of AP freq v injected current post hoc

#### BEGIN normalize durations to 1st AP - for each cell

# all conditions
data = (CACNA1C187fHE_19h09_c04_trains_0001_AP_durations_15mV, 
        CACNA1C187fHE_19h09_c04_trains_0002_AP_durations_15mV, 
        CACNA1C187fHE_19h09_c04_trains_0003_AP_durations_15mV, 
        CACNA1C187fHE_19h09_c04_trains_0004_AP_durations_15mV, 
        CACNA1C187fHE_19h09_c04_trains_0005_AP_durations_15mV, 
        CACNA1C187fHE_19h09_c04_trains_isr_0000_AP_durations_15mV, 
        CACNA1C187fHE_19h09_c04_trains_isr_0001_AP_durations_15mV, 
        CACNA1C187fHE_19h09_c04_trains_isr_0002_AP_durations_15mV, 
        CACNA1C187fHE_19h09_c04_trains_isr_aga_0000_AP_durations_15mV, 
        CACNA1C187fHE_19h09_c04_trains_isr_aga_0001_AP_durations_15mV, 
        CACNA1C187fHE_19h09_c04_trains_isr_aga_0002_AP_durations_15mV, 
        CACNA1C187fHE_19h09_c04_trains_isr_aga_cd_0000_AP_durations_15mV, 
        CACNA1C187fHE_19h09_c04_trains_isr_aga_cd_0001_AP_durations_15mV, 
        CACNA1C187fHE_19h09_c04_trains_isr_aga_cd_0002_AP_durations_15mV, 
        CACNA1C187fHE_19h09_c04_trains_isr_aga_cd_0003_AP_durations_15mV)

for df in data:
    dss = list()
    for c in df.columns:
        d = df[c].values.flatten()
        d_norm = d/d[0]
        ds = pd.Series(d_norm, name="%s_norm" % c)
        dss.append(ds)
        
    for ds in dss:
        if ds.name not in df.columns:
            df.insert(loc = len(df.columns), column=ds.name, value=ds)
            
        else:
            df[ds.name] = ds
        
del(data, dss, df, c, d_norm, ds, d)

#### END  normalize durations to 1st AP - for each cell


#### BEGIN average durations, for each cell

# control
data = (CACNA1C187fHE_19h09_c04_trains_0001_AP_durations_15mV, 
        CACNA1C187fHE_19h09_c04_trains_0002_AP_durations_15mV, 
        CACNA1C187fHE_19h09_c04_trains_0003_AP_durations_15mV,
        CACNA1C187fHE_19h09_c04_trains_0004_AP_durations_15mV,
        CACNA1C187fHE_19h09_c04_trains_0003_AP_durations_15mV)

d_dict = dict()
d_norm_dict = dict()

for iinj in injection_steps:
    dd = np.full((10, len(data)), np.nan)
    dd_norm = np.full((10, len(data)), np.nan)
    
    for k, df in enumerate(data):
        di = df[iinj].values.flatten()
        
        if len(di) < 10:
            dd[0:len(di), k] = di[:]
        else:
            dd[:,k] = di[0:10]
        
        di_norm = df["%s_norm" % iinj].values.flatten()
        
        if len(di_norm) < 10:
            dd_norm[0:len(di_norm), k] = di_norm[:]
        else:
            dd_norm[:,k] = di_norm[0:10]
        
    d_avg = np.nanmean(dd, axis=1)
    
    d_dict[iinj] = pd.Series(d_avg, name=iinj)
    
    df_avg = pd.DataFrame(d_dict)
        
    assignin(df_avg, "%s_control_durations" % prefix)
    
    d_norm_avg = np.nanmean(dd_norm, axis=1)
    
    d_norm_dict["%s_norm" % iinj] = pd.Series(d_norm_avg, name="%s_norm" % iinj)
    
    df_norm_avg = pd.DataFrame(d_norm_dict)
        
    assignin(df_norm_avg, "%s_control_durations_normalized" % prefix)
    
# isradipine
data = (CACNA1C187fHE_19h09_c04_trains_isr_0000_AP_durations_15mV, 
        CACNA1C187fHE_19h09_c04_trains_isr_0001_AP_durations_15mV, 
        CACNA1C187fHE_19h09_c04_trains_isr_0002_AP_durations_15mV)

d_dict = dict()
d_norm_dict = dict()

for iinj in injection_steps:
    dd = np.full((10, len(data)), np.nan)
    dd_norm = np.full((10, len(data)), np.nan)
    
    for k, df in enumerate(data):
        di = df[iinj].values.flatten()
        
        if len(di) < 10:
            dd[0:len(di), k] = di[:]
        else:
            dd[:,k] = di[0:10]
        
        di_norm = df["%s_norm" % iinj].values.flatten()
        
        if len(di_norm) < 10:
            dd_norm[0:len(di_norm), k] = di_norm[:]
        else:
            dd_norm[:,k] = di_norm[0:10]
        
    d_avg = np.nanmean(dd, axis=1)
    
    d_dict[iinj] = pd.Series(d_avg, name=iinj)
    
    df_avg = pd.DataFrame(d_dict)
        
    assignin(df_avg, "%s_isradipine_durations" % prefix)
    
    d_norm_avg = np.nanmean(dd_norm, axis=1)
    
    d_norm_dict["%s_norm" % iinj] = pd.Series(d_norm_avg, name="%s_norm" % iinj)
    
    df_norm_avg = pd.DataFrame(d_norm_dict)
        
    assignin(df_norm_avg, "%s_isradipine_durations_normalized" % prefix)
    
    
# isradipine + aga
data = (CACNA1C187fHE_19h09_c04_trains_isr_aga_0000_AP_durations_15mV, 
        CACNA1C187fHE_19h09_c04_trains_isr_aga_0001_AP_durations_15mV, 
        CACNA1C187fHE_19h09_c04_trains_isr_aga_0002_AP_durations_15mV)

d_dict = dict()
d_norm_dict = dict()

for iinj in injection_steps:
    dd = np.full((10, len(data)), np.nan)
    dd_norm = np.full((10, len(data)), np.nan)
    
    for k, df in enumerate(data):
        di = df[iinj].values.flatten()
        
        if len(di) < 10:
            dd[0:len(di), k] = di[:]
        else:
            dd[:,k] = di[0:10]
        
        di_norm = df["%s_norm" % iinj].values.flatten()
        
        if len(di_norm) < 10:
            dd_norm[0:len(di_norm), k] = di_norm[:]
        else:
            dd_norm[:,k] = di_norm[0:10]
        
    d_avg = np.nanmean(dd, axis=1)
    
    d_dict[iinj] = pd.Series(d_avg, name=iinj)
    
    df_avg = pd.DataFrame(d_dict)
        
    assignin(df_avg, "%s_isr_aga_durations" % prefix)
    
    d_norm_avg = np.nanmean(dd_norm, axis=1)
    
    d_norm_dict["%s_norm" % iinj] = pd.Series(d_norm_avg, name="%s_norm" % iinj)
    
    df_norm_avg = pd.DataFrame(d_norm_dict)
        
    assignin(df_norm_avg, "%s_isr_aga_durations_normalized" % prefix)
    
    
# isradipine + aga + cd
data = (CACNA1C187fHE_19h09_c04_trains_isr_aga_cd_0000_AP_durations_15mV, 
        CACNA1C187fHE_19h09_c04_trains_isr_aga_cd_0001_AP_durations_15mV, 
        CACNA1C187fHE_19h09_c04_trains_isr_aga_cd_0002_AP_durations_15mV, 
        CACNA1C187fHE_19h09_c04_trains_isr_aga_cd_0003_AP_durations_15mV)

d_dict = dict()
d_norm_dict = dict()

for iinj in injection_steps:
    dd = np.full((10, len(data)), np.nan)
    dd_norm = np.full((10, len(data)), np.nan)
    
    for k, df in enumerate(data):
        di = df[iinj].values.flatten()
        
        if len(di) < 10:
            dd[0:len(di), k] = di[:]
        else:
            dd[:,k] = di[0:10]
        
        di_norm = df["%s_norm" % iinj].values.flatten()
        
        if len(di_norm) < 10:
            dd_norm[0:len(di_norm), k] = di_norm[:]
        else:
            dd_norm[:,k] = di_norm[0:10]
        
    d_avg = np.nanmean(dd, axis=1)
    
    d_dict[iinj] = pd.Series(d_avg, name=iinj)
    
    df_avg = pd.DataFrame(d_dict)
        
    assignin(df_avg, "%s_isr_aga_cd_durations" % prefix)
    
    d_norm_avg = np.nanmean(dd_norm, axis=1)
    
    d_norm_dict["%s_norm" % iinj] = pd.Series(d_norm_avg, name="%s_norm" % iinj)
    
    df_norm_avg = pd.DataFrame(d_norm_dict)
        
    assignin(df_norm_avg, "%s_isr_aga_cd_durations_normalized" % prefix)
    
del(d_dict, dd, di, df, k, d_avg, df_avg, 
    d_norm_dict, dd_norm, di_norm, d_norm_avg, df_norm_avg, iinj, data)

#### END average durations, for each cell

#### BEGIN AP fequency vs current injection (average for each cell)

# control
data = (CACNA1C187fHE_19h09_c04_trains_0000_AP_freq_v_Iinj, 
        CACNA1C187fHE_19h09_c04_trains_0001_AP_freq_v_Iinj, 
        CACNA1C187fHE_19h09_c04_trains_0002_AP_freq_v_Iinj)

base_iinj = np.full((max([len(d) for d in data]), len(data)), np.nan)

for k,d in enumerate(data):
    base_iinj[0:len(d),k] = d.as_array()[:,0]
    
CACNA1C187fHE_19h09_c04_control_AP_freq_v_Iinj = dt.IrregularlySampledDataSignal(signal=np.nanmean(base_iinj, axis=1), 
                                                                                  domain=data[0].domain, 
                                                                                  name="Mean AP Frequency",
                                                                                  units = pq.Hz)

CACNA1C187fHE_19h09_c04_control_AP_freq_v_Iinj.domain_name = "Injected current"

del(base_iinj, d, k, data)

# Isradipine
data = (CACNA1C187fHE_19h09_c04_trains_isr_0000_AP_freq_v_Iinj, 
        CACNA1C187fHE_19h09_c04_trains_isr_0001_AP_freq_v_Iinj, 
        CACNA1C187fHE_19h09_c04_trains_isr_0002_AP_freq_v_Iinj)

base_iinj = np.full((max([len(d) for d in data]), len(data)), np.nan)

for k,d in enumerate(data):
    base_iinj[0:len(d),k] = d.as_array()[:,0]
    
CACNA1C187fHE_19h09_c04_isr_AP_freq_v_Iinj = dt.IrregularlySampledDataSignal(signal=np.nanmean(base_iinj, axis=1), 
                                                                                  domain=data[0].domain, 
                                                                                  name="Mean AP Frequency",
                                                                                  units = pq.Hz)

CACNA1C187fHE_19h09_c04_isr_AP_freq_v_Iinj.domain_name = "Injected current"

del(base_iinj, d, k, data)

# Isradipine + Aga
data = (CACNA1C187fHE_19h09_c04_trains_isr_aga_0000_AP_freq_v_Iinj, 
        CACNA1C187fHE_19h09_c04_trains_isr_aga_0001_AP_freq_v_Iinj, 
        CACNA1C187fHE_19h09_c04_trains_isr_aga_0002_AP_freq_v_Iinj)

base_iinj = np.full((max([len(d) for d in data]), len(data)), np.nan)

for k,d in enumerate(data):
    base_iinj[0:len(d),k] = d.as_array()[:,0]
    
CACNA1C187fHE_19h09_c04_isr_aga_AP_freq_v_Iinj = dt.IrregularlySampledDataSignal(signal=np.nanmean(base_iinj, axis=1), 
                                                                                  domain=data[0].domain, 
                                                                                  name="Mean AP Frequency",
                                                                                  units = pq.Hz)

CACNA1C187fHE_19h09_c04_isr_aga_AP_freq_v_Iinj.domain_name = "Injected current"

del(base_iinj, d, k, data)

# Isradipine + Aga + Cd
data = (CACNA1C187fHE_19h09_c04_trains_isr_aga_cd_0000_AP_freq_v_Iinj, 
        CACNA1C187fHE_19h09_c04_trains_isr_aga_cd_0001_AP_freq_v_Iinj, 
        CACNA1C187fHE_19h09_c04_trains_isr_aga_cd_0002_AP_freq_v_Iinj,
        CACNA1C187fHE_19h09_c04_trains_isr_aga_cd_0003_AP_freq_v_Iinj)

base_iinj = np.full((max([len(d) for d in data]), len(data)), np.nan)

for k,d in enumerate(data):
    base_iinj[0:len(d),k] = d.as_array()[:,0]
    
CACNA1C187fHE_19h09_c04_isr_aga_cd_AP_freq_v_Iinj = dt.IrregularlySampledDataSignal(signal=np.nanmean(base_iinj, axis=1), 
                                                                                  domain=data[0].domain, 
                                                                                  name="Mean AP Frequency",
                                                                                  units = pq.Hz)

CACNA1C187fHE_19h09_c04_isr_aga_AP_freq_v_Iinj.domain_name = "Injected current"

del(base_iinj, d, k, data)

#### END AP fequency vs current injection (average for each cell)

# NOTE: this for later when several cells have been analysed

#### BEGIN collect averaged cell data in one DataFrame
# generates one pandas DataFrame that can be exported to CSV and imported in R

#durations_data_names = ['CACNA1C187fHE_19h09_c01_isr_aga_cd_durations', 
                        #'CACNA1C187fHE_19h09_c01_isr_aga_durations', 
                        #'CACNA1C187fHE_19h09_c01_isradipine_durations', 
                        #'CACNA1C187fHE_19h09_c01_veh_durations', 
                        #'CACNA1C187fHE_19h09_c02_control_durations', 
                        #'CACNA1C187fHE_19h09_c02_isr_aga_cd_durations', 
                        #'CACNA1C187fHE_19h09_c02_isr_aga_durations', 
                        #'CACNA1C187fHE_19h09_c02_isradipine_durations', 
                        #'CACNA1C187fHE_19h09_c03_control_durations', 
                        #'CACNA1C187fHE_19h09_c03_isr_aga_cd_durations', 
                        #'CACNA1C187fHE_19h09_c03_isr_aga_durations', 
                        #'CACNA1C187fHE_19h09_c03_isradipine_durations', 
                        #'CACNA1C187fHE_19h09_c04_control_durations', 
                        #'CACNA1C187fHE_19h09_c04_isr_aga_cd_durations', 
                        #'CACNA1C187fHE_19h09_c04_isr_aga_durations', 
                        #'CACNA1C187fHE_19h09_c04_isradipine_durations']

durations_data_names = ['CACNA1C164mWT_19g24_c02_baseline_durations', 
                        'CACNA1C164mWT_19g24_c02_isradipine_durations', 
                        'CACNA1C164mWT_19g24_c03_baseline_durations', 
                        'CACNA1C164mWT_19g24_c03_isradipine_durations', 
                        'CACNA1C164mWT_19g24_c04_baseline_durations', 
                        'CACNA1C164mWT_19g24_c04_isradipine_durations', 
                        'CACNA1C165mWT_19g25_c01_baseline_durations', 
                        'CACNA1C165mWT_19g25_c01_isradipine_durations', 
                        'CACNA1C165mWT_19g25_c02_baseline_durations', 
                        'CACNA1C165mWT_19g25_c02_isradipine_durations', 
                        'CACNA1C173fWT_19g30_c01_baseline_durations', 
                        'CACNA1C173fWT_19g30_c01_isradipine_durations', 
                        'CACNA1C173fWT_19g30_c02_baseline_durations', 
                        'CACNA1C173fWT_19g30_c02_isradipine_durations', 
                        'CACNA1C173fWT_19g30_c03_baseline_durations', 
                        'CACNA1C173fWT_19g30_c03_isradipine_durations', 
                        'CACNA1C174fWT_19h02_c01_baseline_durations', 
                        'CACNA1C174fWT_19h02_c01_isradipine_durations', 
                        'CACNA1C174fWT_19h02_c02_baseline_durations', 
                        'CACNA1C174fWT_19h02_c02_isradipine_durations', 
                        'CACNA1C174fWT_19h02_c03_baseline_durations', 
                        'CACNA1C174fWT_19h02_c03_isradipine_durations', 
                        'CACNA1C174fWT_19h02_c04_baseline_durations', 
                        'CACNA1C174fWT_19h02_c04_isradipine_durations', 
                        'CACNA1C178fWT_19h01_c01_baseline_durations', 
                        'CACNA1C178fWT_19h01_c01_isradipine_durations', 
                        'CACNA1C178fWT_19h01_c03_baseline_durations', 
                        'CACNA1C178fWT_19h01_c03_isradipine_durations', 
                        'CACNA1C178fWT_19h01_c04_baseline_durations', 
                        'CACNA1C178fWT_19h01_c04_isradipine_durations', 
                        'CACNA1C179fWT_19g30_c01_baseline_durations', 
                        'CACNA1C179fWT_19g30_c01_isradipine_durations', 
                        'CACNA1C179fWT_19g30_c02_baseline_durations', 
                        'CACNA1C179fWT_19g30_c02_isradipine_durations', 
                        'CACNA1C179fWT_19g30_c03_baseline_durations', 
                        'CACNA1C179fWT_19g30_c03_isradipine_durations']

result_frames = list()

for n in durations_data_names:
    data = eval(n)
    
    if "isradipine" in n.lower():
        treatment="Isr"
        terms = n.replace("_isradipine_durations", "").split("_")
        
    elif any([s in n.lower() for s in ("control", "veh", "baseline")]):
        treatment = "Control"
        terms = n.replace("_control_durations", "").split("_")
        
    elif "cd" in n.lower():
        treatment = "IsrAgaCd"
        terms = n.replace("_isr_aga_cd_durations", "").split("_")
        
    else:
        treatment = "IsrAga"
        terms = n.replace("_isr_aga_durations", "").split("_")
    
    cellid = terms[-1]
    
    srcid = "_".join(terms[0:2])
    
    dataid = "_".join(terms[0:3])
    
    genotype = "WT" if "wt" in srcid.lower() else "HET"
    
    sex = "M" if "m" in srcid.lower() else "F"
    
    values = [(pd.Series([eval(c.split("_")[0])]*len(data), name="Iinj", dtype="category"), pd.Series(list(data[c]), name="Durations_15mV")) for c in data.columns]
    
    iinj_series = pd.concat([v[0] for v in values])
    
    apval_series = pd.concat([v[1] for v in values], ignore_index = True)
    
    ap_numbers = iinj_series.index
    
    iinj_series.index = [k for k in range(iinj_series.size)]
    
    treatments = [treatment] * iinj_series.size
    sexes = [sex] * iinj_series.size
    genotypes = [genotype] * iinj_series.size
    cellids = [cellid] * iinj_series.size
    srcids = [srcid] * iinj_series.size
    dataids = [dataid] * iinj_series.size
    
    treatment_series = pd.Series(treatments, name="Treatment", dtype="category")
    treatment_series.cat.categories = unique(treatments)
    
    iinj_series = pd.Series(iinj_series, name="Iinj", dtype="category")
    iinj_series.cat.categories = unique(list(iinj_series))
    
    sex_series = pd.Series(sexes, name="Sex", dtype="category")
    sex_series.cat.categories = unique(sexes)
    
    genotype_series = pd.Series(genotypes, name="Genotype", dtype="category")
    genotype_series.cat.categories = unique(genotypes)
    
    cellid_series = pd.Series(cellids, name="Cell", dtype="category")
    cellid_series.cat.categories = unique(cellids)
    
    srcid_series = pd.Series(srcids, name="Source", dtype="category")
    srcid_series.cat.categories = unique(srcids)
    
    dataid_series = pd.Series(dataids, name="ID", dtype="category")
    dataid_series.cat.categories = unique(dataids)
    
    apnum_series = pd.Series(ap_numbers, name="AP", dtype="category")
    apnum_series.cat.categories = unique(list(ap_numbers))
    
    df = pd.DataFrame({"ID": dataid_series,
                       "Source": srcid_series,
                       "Cell": cellid_series,
                       "Genotype": genotype_series,
                       "Sex": sex_series,
                       "Iinj": iinj_series,
                       "Treatment": treatment_series,
                       "AP": apnum_series,
                       "Duration_15mV":apval_series})
    
    
    result_frames.append(df)
    
#AP_durations_19h05 = pd.concat(result_frames)
collected_result = pd.concat(result_frames)
assignin(collected_result, "AP_durations_%s_Isr_only_19h12" % genotype)

del(cellid, cellid_series, cellids, data, genotype, genotype_series, 
    genotypes, iinj_series, n, result_frames, sex, sex_series, sexes, 
    srcid, srcid_series, srcids, terms, treatment, treatment_series, treatments,
    ap_numbers, apnum_series, dataids, dataid_series, dataid, df, apval_series, values,
    collected_result, durations_data_names)

#### END collect averaged cell data in one DataFrame

#### BEGIN collect averaged cell data (normalized durations) in one DataFrame
# generates one pandas DataFrame that can be exported to CSV and imported in R

#durations_norm_data_names = ['CACNA1C187fHE_19h09_c01_isr_aga_cd_durations_normalized', 
                        #'CACNA1C187fHE_19h09_c01_isr_aga_durations_normalized', 
                        #'CACNA1C187fHE_19h09_c01_isradipine_durations_normalized', 
                        #'CACNA1C187fHE_19h09_c01_veh_durations_normalized', 
                        #'CACNA1C187fHE_19h09_c02_control_durations_normalized', 
                        #'CACNA1C187fHE_19h09_c02_isr_aga_cd_durations_normalized', 
                        #'CACNA1C187fHE_19h09_c02_isr_aga_durations_normalized', 
                        #'CACNA1C187fHE_19h09_c02_isradipine_durations_normalized', 
                        #'CACNA1C187fHE_19h09_c03_control_durations_normalized', 
                        #'CACNA1C187fHE_19h09_c03_isr_aga_cd_durations_normalized', 
                        #'CACNA1C187fHE_19h09_c03_isr_aga_durations_normalized', 
                        #'CACNA1C187fHE_19h09_c03_isradipine_durations_normalized', 
                        #'CACNA1C187fHE_19h09_c04_control_durations_normalized', 
                        #'CACNA1C187fHE_19h09_c04_isr_aga_cd_durations_normalized', 
                        #'CACNA1C187fHE_19h09_c04_isr_aga_durations_normalized', 
                        #'CACNA1C187fHE_19h09_c04_isradipine_durations_normalized']


durations_norm_data_names = ['CACNA1C164mWT_19g24_c02_baseline_durations_normalized', 
                             'CACNA1C164mWT_19g24_c02_isradipine_durations_normalized', 
                             'CACNA1C164mWT_19g24_c03_baseline_durations_normalized', 
                             'CACNA1C164mWT_19g24_c03_isradipine_durations_normalized', 
                             'CACNA1C164mWT_19g24_c04_baseline_durations_normalized', 
                             'CACNA1C164mWT_19g24_c04_isradipine_durations_normalized', 
                             'CACNA1C165mWT_19g25_c01_baseline_durations_normalized', 
                             'CACNA1C165mWT_19g25_c01_isradipine_durations_normalized', 
                             'CACNA1C165mWT_19g25_c02_baseline_durations_normalized', 
                             'CACNA1C165mWT_19g25_c02_isradipine_durations_normalized', 
                             'CACNA1C173fWT_19g30_c01_baseline_durations_normalized', 
                             'CACNA1C173fWT_19g30_c01_isradipine_durations_normalized', 
                             'CACNA1C173fWT_19g30_c02_baseline_durations_normalized', 
                             'CACNA1C173fWT_19g30_c02_isradipine_durations_normalized', 
                             'CACNA1C173fWT_19g30_c03_baseline_durations_normalized', 
                             'CACNA1C173fWT_19g30_c03_isradipine_durations_normalized', 
                             'CACNA1C174fWT_19h02_c01_baseline_durations_normalized', 
                             'CACNA1C174fWT_19h02_c01_isradipine_durations_normalized', 
                             'CACNA1C174fWT_19h02_c02_baseline_durations_normalized', 
                             'CACNA1C174fWT_19h02_c02_isradipine_durations_normalized', 
                             'CACNA1C174fWT_19h02_c03_baseline_durations_normalized', 
                             'CACNA1C174fWT_19h02_c03_isradipine_durations_normalized', 
                             'CACNA1C174fWT_19h02_c04_baseline_durations_normalized', 
                             'CACNA1C174fWT_19h02_c04_isradipine_durations_normalized', 
                             'CACNA1C178fWT_19h01_c01_baseline_durations_normalized', 
                             'CACNA1C178fWT_19h01_c01_isradipine_durations_normalized', 
                             'CACNA1C178fWT_19h01_c03_baseline_durations_normalized', 
                             'CACNA1C178fWT_19h01_c03_isradipine_durations_normalized', 
                             'CACNA1C178fWT_19h01_c04_baseline_durations_normalized', 
                             'CACNA1C178fWT_19h01_c04_isradipine_durations_normalized', 
                             'CACNA1C179fWT_19g30_c01_baseline_durations_normalized', 
                             'CACNA1C179fWT_19g30_c01_isradipine_durations_normalized', 
                             'CACNA1C179fWT_19g30_c02_baseline_durations_normalized', 
                             'CACNA1C179fWT_19g30_c02_isradipine_durations_normalized', 
                             'CACNA1C179fWT_19g30_c03_baseline_durations_normalized', 
                             'CACNA1C179fWT_19g30_c03_isradipine_durations_normalized']



result_frames = list()

for n in durations_norm_data_names:
    data = eval(n)
    
    if "isradipine" in n.lower():
        treatment="Isr"
        terms = n.replace("_isradipine_durations_normalized", "").split("_")
        
    elif any([s in n.lower() for s in ("control", "veh", "baseline")]):
        treatment = "Control"
        terms = n.replace("_control_durations_normalized", "").split("_")
        
    elif "cd" in n.lower():
        treatment = "IsrAgaCd"
        terms = n.replace("_isr_aga_cd_durations_normalized", "").split("_")
        
    else:
        treatment = "IsrAga"
        terms = n.replace("_isr_aga_durations_normalized", "").split("_")
    
    
    cellid = terms[-1]
    
    srcid = "_".join(terms[0:2])
    
    dataid = "_".join(terms[0:3])
    
    genotype = "WT" if "wt" in srcid.lower() else "HET"
    
    sex = "M" if "m" in srcid.lower() else "F"
    
    values = [(pd.Series([eval(c.split("_")[0])]*len(data), name="Iinj", dtype="category"), pd.Series(list(data[c]), name="Durations_15mV")) for c in data.columns]
    
    iinj_series = pd.concat([v[0] for v in values])
    
    apval_series = pd.concat([v[1] for v in values], ignore_index = True)
    
    ap_numbers = iinj_series.index
    
    iinj_series.index = [k for k in range(iinj_series.size)]
    
    treatments = [treatment] * iinj_series.size
    sexes = [sex] * iinj_series.size
    genotypes = [genotype] * iinj_series.size
    cellids = [cellid] * iinj_series.size
    srcids = [srcid] * iinj_series.size
    dataids = [dataid] * iinj_series.size
    
    treatment_series = pd.Series(treatments, name="Treatment", dtype="category")
    treatment_series.cat.categories = unique(treatments)
    
    iinj_series = pd.Series(iinj_series, name="Iinj", dtype="category")
    iinj_series.cat.categories = unique(list(iinj_series))
    
    sex_series = pd.Series(sexes, name="Sex", dtype="category")
    sex_series.cat.categories = unique(sexes)
    
    genotype_series = pd.Series(genotypes, name="Genotype", dtype="category")
    genotype_series.cat.categories = unique(genotypes)
    
    cellid_series = pd.Series(cellids, name="Cell", dtype="category")
    cellid_series.cat.categories = unique(cellids)
    
    srcid_series = pd.Series(srcids, name="Source", dtype="category")
    srcid_series.cat.categories = unique(srcids)
    
    dataid_series = pd.Series(dataids, name="ID", dtype="category")
    dataid_series.cat.categories = unique(dataids)
    
    apnum_series = pd.Series(ap_numbers, name="AP", dtype="category")
    apnum_series.cat.categories = unique(list(ap_numbers))
    
    df = pd.DataFrame({"ID": dataid_series,
                       "Source": srcid_series,
                       "Cell": cellid_series,
                       "Genotype": genotype_series,
                       "Sex": sex_series,
                       "Iinj": iinj_series,
                       "Treatment": treatment_series,
                       "AP": apnum_series,
                       "Duration_15mV":apval_series})
    
    
    result_frames.append(df)
    
collected_result = pd.concat(result_frames)
assignin(collected_result, "AP_durations_%s_normalized_Isr_only_19h12" % genotype)
#AP_durations_19h05_norm = pd.concat(result_frames)

del(cellid, cellid_series, cellids, data, genotype, genotype_series, 
    genotypes, iinj_series, n, result_frames, sex, sex_series, sexes, 
    srcid, srcid_series, srcids, terms, treatment, treatment_series, treatments,
    ap_numbers, apnum_series, dataids, dataid_series, dataid, df, apval_series, values, 
    collected_result, durations_norm_data_names)


#### END collect averaged cell data (normalized durations) in one DataFrame


#### BEGIN collect AP frequencies by injected current
#
####
ap_freq_data = ['CACNA1C187fHE_19h09_c04_control_AP_freq_v_Iinj', 
                'CACNA1C187fHE_19h09_c04_isradipine_AP_freq_v_Iinj', 
                'CACNA1C164mWT_19g24_c03_control_AP_freq_v_Iinj', 
                'CACNA1C164mWT_19g24_c03_isradipine_AP_freq_v_Iinj', 
                'CACNA1C187fHE_19h09_c04_control_AP_freq_v_Iinj', 
                'CACNA1C187fHE_19h09_c04_isradipine_AP_freq_v_Iinj', 
                'CACNA1C165mWT_19g25_c01_control_AP_freq_v_Iinj', 
                'CACNA1C165mWT_19g25_c01_isradipine_AP_freq_v_Iinj', 
                'CACNA1C165mWT_19g25_c02_control_AP_freq_v_Iinj', 
                'CACNA1C165mWT_19g25_c02_isradipine_AP_freq_v_Iinj', 
                'CACNA1C173fWT_19g30_c01_control_AP_freq_v_Iinj', 
                'CACNA1C173fWT_19g30_c01_isradipine_AP_freq_v_Iinj', 
                'CACNA1C173fWT_19g30_c02_control_AP_freq_v_Iinj', 
                'CACNA1C173fWT_19g30_c02_isradipine_AP_freq_v_Iinj', 
                'CACNA1C173fWT_19g30_c03_control_AP_freq_v_Iinj', 
                'CACNA1C173fWT_19g30_c03_isradipine_AP_freq_v_Iinj', 
                'CACNA1C174fWT_19h02_c01_control_AP_freq_v_Iinj', 
                'CACNA1C174fWT_19h02_c01_isradipine_AP_freq_v_Iinj', 
                'CACNA1C174fWT_19h02_c02_control_AP_freq_v_Iinj', 
                'CACNA1C174fWT_19h02_c02_isradipine_AP_freq_v_Iinj', 
                'CACNA1C174fWT_19h02_c03_control_AP_freq_v_Iinj', 
                'CACNA1C174fWT_19h02_c03_isradipine_AP_freq_v_Iinj', 
                'CACNA1C174fWT_19h02_c04_control_AP_freq_v_Iinj', 
                'CACNA1C174fWT_19h02_c04_isradipine_AP_freq_v_Iinj', 
                'CACNA1C178fWT_19h01_c01_control_AP_freq_v_Iinj', 
                'CACNA1C178fWT_19h01_c01_isradipine_AP_freq_v_Iinj', 
                'CACNA1C178fWT_19h01_c03_control_AP_freq_v_Iinj', 
                'CACNA1C178fWT_19h01_c03_isradipine_AP_freq_v_Iinj', 
                'CACNA1C178fWT_19h01_c04_control_AP_freq_v_Iinj', 
                'CACNA1C178fWT_19h01_c04_isradipine_AP_freq_v_Iinj', 
                'CACNA1C179fWT_19g30_c01_control_AP_freq_v_Iinj', 
                'CACNA1C179fWT_19g30_c01_isradipine_AP_freq_v_Iinj', 
                'CACNA1C179fWT_19g30_c02_control_AP_freq_v_Iinj', 
                'CACNA1C179fWT_19g30_c02_isradipine_AP_freq_v_Iinj', 
                'CACNA1C179fWT_19g30_c03_control_AP_freq_v_Iinj', 
                'CACNA1C179fWT_19g30_c03_isradipine_AP_freq_v_Iinj']

injection_current = ["300", "500", "700", "900", "1100"]

dataID = list()
srcID = list()
cellID = list()
gtype = list()
sexes = list()
treatments = list()
inj_current = list()
ap_freqs = list()

for n in ap_freq_data:
    data = eval(n)
    
    if "isradipine" in n.lower():
        treatment="Isr"
        terms = n.replace("_isradipine_durations", "").split("_")
        
    else:
        treatment = "Control"
        terms = n.replace("_control_durations", "").split("_")
    
    cellid = terms[2]
    
    srcid = "_".join(terms[0:2])
    
    dataid = "_".join(terms[0:3])
    
    genotype = "WT" if "wt" in srcid.lower() else "HET"
    
    sex = "M" if "m" in srcid.lower() else "F"
    
    ap_freq = data[2:].as_array().flatten()
    
    for k, v in enumerate(ap_freq):
        dataID.append(dataid)
        srcID.append(srcid)
        cellID.append(cellid)
        gtype.append(genotype)
        sexes.append(sex)
        treatments.append(treatment)
        inj_current.append(injection_current[k])
        ap_freqs.append(float(v))
    
AP_frequencies_by_Injected_current_19h06 = pd.DataFrame(dict({"ID":pd.Series(dataID, name="ID", dtype="category"),
                                                              "Source": pd.Series(srcID, name="Source", dtype="category"),
                                                              "Cell": pd.Series(cellID, name="Cell", dtype="category"),
                                                              "Sex":pd.Series(sexes, name="Sex", dtype="category"),
                                                              "Genotype": pd.Series(gtype, name="Genotype", dtype="category"),
                                                              "Treatment": pd.Series(treatments, name="Treatment", dtype="category"),
                                                              "Iinj": pd.Series(inj_current, name="Iinj", dtype="category"),
                                                              "Frequency": pd.Series(ap_freqs, name="Frequency")}))



del(dataID, srcID, cellID, gtype, sexes, treatments, inj_current, ap_freqs, 
    n, data, dataid, srcid, cellid, genotype, sex, ap_freq, k, v)
    

#### END collect AP frequencies by injected current

