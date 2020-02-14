
# get the AxonIO object on the abf file
axonio = neo.io.AxonIO("/home/cezar/Externally Mounted Disks/SamsungLinux_2/LabData/DEFINE/Abdel/20-02-13/slice 1/baseline_0000.abf")

# meta data (contains acquisition info)
metadata = axonio._axon_info # a dict

protocol = metadata["protocol"] # a dict

"""
Putative semantics of relevant(?) fields:
GUI: dialog title [tab title] / gui control, group, or dialog / gui control within group or dialog : value of gui control
=========================================================================================================================
### BEGIN acquisition mode
protocol["nOperationMode"]  
    type:   int
    value:  5
    GUI:    "Edit Protocol" ["Mode/Rate"] / "Acquisition Mode":"Episodic Stimulation"
### END acquisition mode

### BEGIN episodic stimulation
protocol["INumSamplesPerEpisode"]
    int
    total data throughput (samples/s)
    
protocol["fTrialStartToStart"]
    type:   float
    value:  0.0
    GUI:    Sequencing? (delay to next "key")
    
protocol["fFirstRunDelayS"]
    type:   float
    value:  0.0
    GUI
protocol["IRunsPerTrial"]   
    type:   int
    value:  6
    GUI tab:        "Mode/Rate"
    GUI control:    "Runs/trial"
    Notes: Averaging: when runs/trial > 1 average will be saved
    
protocol["IEpisodesPerRun"] 
    type:   int
    value:  2
    GUI tab:        "Mode/Rate"
    GUI control:    "Sweeps/run"    
    
protocol["fRunStartToStart"]
    type:   float
    value:  10.0
    GUI tab:        "Mode/Rate"
    GUI control:    "Start-to-Start intervals"/"Run (s)"
    
protocol["fEpisodeStartToStart"]
    type:   float
    value:  5.0
    GUI tab:        "Mode/Rate"
    GUI control:    "Start-to-Start intervals"/"Sweeps (s)"
    

### BEGIN sweep averaging -- within episodic stimulation - this take place automatically when Runs/trial > 1
protocol["nAveragingMode"]
    type:   int
    value:  0
    GUI tab:        "Mode/Rate"
    GUI control:    "Averaging Options" dialog / "Type": "Cumulative"
                                                            
protocol["nUndoRunCount"]   
    type:   int
    value:  -1
    GUYI tab:       "Mode/Rate"
    GUI control:    "Averaging Options" dialog / "Undo File": <OFF>
                                                            
### END sweep averaging

### END episodic stimulation
"""




