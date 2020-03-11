# -*- coding: utf-8 -*-

#### BEGIN core python modules
import sys, traceback, inspect, numbers
import warnings
import os, pickle
import collections
import itertools
import typing, types

#### END core python modules

#### BEGIN 3rd party modules
import numpy as np
import pandas as pd
import quantities as pq
import matplotlib as mpl
import matplotlib.pyplot as plt
import neo
from scipy import optimize, cluster#, where

from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.uic import loadUiType as __loadUiType__ 

#### END 3rd party modules

#### BEGIN pict.core modules
import core.neoutils as neoutils
import core.workspacefunctions as wf
import core.signalprocessing as sigp
import core.curvefitting as crvf
import core.datatypes as datatypes
import core.plots as plots
import core.models as models

#from core.patchneo import neo
from core.utilities import safeWrapper
#### END pict.core modules

#### BEGIN pict.gui modules
import gui.signalviewer as sv
import gui.textviewer as tv
import gui.tableeditor as te
import gui.matrixviewer as matview
import gui.pictgui as pgui
import gui.quickdialog as quickdialog
import gui.scipyenviewer as scipyenviewer
from gui.scipyenviewer import ScipyenViewer, ScipyenFrameViewer
#### END pict.gui modules

#### BEGIN pict.iolib modules
import iolib.pictio as pio
#### END pict.iolib modules

LTPOptionsFile = os.path.join(os.path.dirname(__file__), "options", "LTPOptions.pkl")
optionsDir     = os.path.join(os.path.dirname(__file__), "options")

__module_path__ = os.path.abspath(os.path.dirname(__file__))

#__UI_LTPWindow__, __QMainWindow__ = __loadUiType__(os.path.join(__module_path__,"LTPWindow.ui"))
__UI_LTPWindow__, __QMainWindow__ = __loadUiType__(os.path.join(__module_path__,"LTPWindow.ui"), 
                                                   from_imports=True, 
                                                   import_from="gui") #  so that resources can be imported too


# NOTE: 2017-05-07 20:18:37
# overwrite neo's Epoch with our own
#import neoepoch
#neo.core.epoch.Epoch = neoepoch.Epoch
#neo.core.Epoch = neoepoch.Epoch
#neo.Epoch = neoepoch.Epoch

"""
NOTE: 2020-02-14 16:54:19 LTP options revamp
NOTATIONS: Im = membrane current; Vm = membrane potential

Configurations for synaptic plasticity experiments (ex vivo slice) = dictionary with the following fields:

A synaptic plasticity experiment takes place in three stages:
        1. pre-conditioning ("baseline") test synaptic responses
        2. conditioning (plasticity induction protocol)
        3. post-conditioning ("chase") test synaptic responses
        
Test synaptic responses are evoked at low frequency (< 1 Hz) by stimulations of 
presynaptic axons. Because of normal fluctuations in the synaptic response, the 
average synaptic response during each minute is usually more relevant: for 0.1 Hz 
stimulation this is the average of six consecutive responses.

Averaging can be performed "on-line" during the experiment, and the minute-average
responses are recorded directly (Signal2 from CED, and Clampex from Axon/MolecularDevices
can do this). Alternatively, the averaging can be performed off-line, using the saved
data.

The synaptic responses can be recorded as:
    * evoked post-synaptic currents or potentials, using in whole-cell patch clamp 
        or with intracellular (sharp) electrodes, in current clamp;
        
    * evoked field potentials, using in extracellular field recordings.
        
Conditioning consists of a sequence of stimulations delivered to presynaptic axons,
optionally combined with depolarization of the postsynaptic cell(s). 

Postsynaptic cell depolarization:
--------------------------------
Postsynaptic current injections are used to elicit postsynaptic action potentials
(with intracellular sharp electrodes or whole-cell patch clamp), or tonic 
depolarization (whole-cell patch clamp with Na+ channel blockers in the intracellular 
solution). Antidromic stimulation of the efferent axons using extracellulal electrodes
can also be used to elicit postsynaptic action potentials in extracellular field 
recordings.

1. Single pathway experiments:
--------------------------------
A single stimulation electrode is used to stimulate a single pathway (bundle of 
presynaptic axons), and the evoked responses are recorded. 

Synaptic plasticity is determined by comparing the magnitude of the average 
synaptic response some time after conditioning, to that of the average synaptic 
response during the baseline immediately prior conditioning.

2. Dual-pathway experiments. 
--------------------------------
Synaptic responses are recorded, ideally, from two  pathways: 
* a conditioned ("Test") pathway - the pathway ot which the conditioning protocol
    is applied
    
* a non-conditioned ("Control") pathway which is left unperturbed (not stimulated)
    during conditioning.

The occurrence of synaptic plasticity is determined by comparing the averaged
synaptic responses some time after conditioning, to the averaged synaptic responses
during the baseline immediately before conditioning, in each pathway. 

Homosynaptic plasticity is indicated by a persistent change in synaptic response
magnitude in the Test pathway, and no change in the Control pathway.

3 Single recording electrode
--------------------------------
In dual-pathway experiments, the two pathways converge and make synapses on the 
same cell (in whole-cell recording) or within the same cell population (in 
extracellular field recording), and a single electrode is used to record the evoked
synaptic responses from both pathways. The Control pathway serves as a "reference" 
(or "internal control") for the stability of synaptic responses in the absence of
conditioning. 

To distinguish between the pathway source of synaptic responses, the experiment
records intervealed sweeps, with each pathway stimulated alternatively.

4 Two recording electrodes
------------------------------
Two recording electrodes may be used to combine whole-cell recording with 
extracellular field recording (e.g., Zalutsky & Nicoll, 1990).

This can be used in single- or dual-pathway configurations.

Configuration ("LTP_options") -- dictionary
-------------------------------------------

"paths": dictionary of path specifications, with each key being a path "name"

Must contain at least one key: "Test", mapped to the specification of the "test"
    pathway
    
Members (keys) of a pathway specification dictionary:
"sweep_index"
    


Configuration fields:
        
"paths": collection of one or two path dictionaries

    Test synaptic responses from each path are recorded in interleaved sweeps.
    
    For Clampex, this means the experiment is recorded in runs containing 
        
    The test responses during (or typically at the end of) the chase are compared
    to the average baseline test response, on a specific measure, e.g. the amplitude
    of the EPSC or EPSP, or the slope of the (field) EPSP, to determine whether
    synaptic plasticity has been induced.
        
    There is no prescribed duration of the baseline or chase stages - these
    depend on the protocol, recording mode and what it is sought by the
    experiment. 
    
    Very short baselines (less than 5 min) are not considered reliable. 
    Long baselines (15 min or more) while not commonly used in LTP experiments
    with whole-cell recordings in order to avoid "LTP wash-out", unless the 
    perforated patch technique is used. On the other hand, long baselines are 
    recommended for when using field potential recordings and for LTD 
    experiments with whole-cell recordings (wash-out is thought not to be an
    issue).
        
    When only a path dictionary is present, this is implied to represent the 
        conditioned (test) pathway.
    
    For two pathways, the conditioned pathway is indicated by the name 
        "Test". The other pathways can have any unique name, but the one that is
        used as a control should be distinguished by its name (e.g. "Control")
        
    Key/value pairs in the path dictionary:
        name: str, possible vales: "Test", "Control", or any name
        index: the index of the sweep that contains data recorded from this path
        
    
"mode":str, one of ["VC", "IC", "fEPSP"]



"paired":bool. When True, test stimulation is paired-pulse; this applies to all 
    paths in the experiment (see below)

"isi":[float, pq.quantity] - interval between stimuli in paired-pulse stimulation
    when a pq.quantity, it must be in time units compatible with the data
    when a float, the time units of the data are implicit
    

"paths":dict with keys "Test" and "Control", or empty
    paths["Test"]:int
    paths["Control"]:[int, NoneType]
    
    When present and non-empty, indicates that this is a dual pathway experiment
    where one is the test pathway and the other, the control pathway.
    
    The values of the "Test" pathway is the integer index of the sweep corresponding 
    to the test pathway, in each "Run" stored as an *.abf file
    
    Similarly, the value of "Control" is the integer index of the sweep containing
    data recorded on the control pathway, in each run stored in the *.abf file
    
    Although the paths key is used primarily when importing abf files into an
    experiment, it is also used during analysis, to signal that the experiment is
    a dual-pathway experiment.
    
    An Exception is raised when:
        a) both "Test" and "Control" have the same value, or
        b) any of "Test" and "Control" have values < 0 or > max number of sweeps
        in the run (NOTE: a run is stored internally as a neo.Block; hence the 
        number of sweeps in the run equals the number of segments in the Block)
    
    The experiment is implicitly considered to be single-pathway when:
    a) "paths" is absent
    b) "paths" is None or an empty dictionary
    c) "paths" only contains one pathway specification (any name, any value)
    d) "paths" contains both "Test", and "Control" fields but Control is either
        None, or has a negative value
        
"xtalk": dictionary with configuration parameters for testing cross-talk between
    pathways
    Ignored when "dual" is False.
    


1) allow for one or two pathways experiment

2) allow for single or paired-pulse stimulation (must be the same in both pathways)

3) allow for the following recording modes:
3.a) whole-cell patch clamp:
3.a.1) mode="VC": voltage clamp mode => measures series and input resistances,
    and the peak amplitude of EPSC (one or two, if paire-pulse is True
    
    field: "Rm": 
        defines the baseline region for series and input resistance calculation
            
        subfields:
        
        "Rbase" either:
            tuple(position:[float, pq.quantity], window:[float, pq.quantity], name:str)
            
            of sequence of two tuples as above
            
            each tuple defines a cursor;
                when a single cursor is defined, its window defines the baseline
                region
                
                when two cursors are defined, their positions delimit the baseline region
            
            
        
            sets up the cursor Rbase - for Rs and Rin calculations
            type: vertical, position, window, name = Rbase
            
            placed manually before the depolarizing Vm square waveform
            for the membrane resistance test 
        
        field: "Rs":
        
        tuple(position:[float, pq.quantity], window:[float, pq.quantity], name:str)
        
            sets up the second cursors for the calculation of Rs:
            this can be
        
        * Rs: 
            required LTP options fields:
                cursor 1 for resistance test baseline 
                        
                cursor 2 for peak of capacitance transient
                    type: vertical, position, window, name = Rs
                    
                    placed manually
                        either on the peak of the 1st capacitance transient at the
                        onset of the positive Vm step waveform for the membrane
                        resistance test
                        
                        or after this peak, to use with positive peak detection
                    
                value of Vm step (mV)
                
                name of the Im signal
                
                use peak detection: bool, default False
            
            calculation of Rs:
                Irs = Im_Rs - Im_Rbase where:
                    Im_Rs = average Im across the window of Rs cursor
                    Im_Rbase = averae Im across the window of the Rbase cursor
                
            Rs = Vm_step/Irs in megaohm
            
            
        * Rin:
            required LTP options fields:
                cursor 1 for steady-state Im during the positive (i.e. depolarizing)
                    VM step waveform
                    
                    type: vertical, position, window, name=Rin
                    
                    placed manualy towards the end of the Vm step waveform BEFORE repolarization
                    
            calculated as :
                Irin = Im_Rin - Im_Rbase, where:
                    Im_Rin = average Im acros the window of the Rin cursor
                    Im_Rbase -- see Rs
                    
                Rin = Vm_step/Irin
                
        * EPSC0: peak amplitude of 1st EPSC
            required LTP options fields:
                cursor for baseline before stimulus artifact
                type: vertical; position, window, name=EPSC0_base
                manually placed before stimuus artifact for 1st EPSC
                
                cursor for peak of EPSC0
                type: vertical, position, window, name=EPSC0
                placed either manually, or use inward peak detection between
                    two cursors
                
                
        if paired-pulse stimulation: 
            peak amplitude of 2nd EPSC
            ratio 2nd EPSC peak amplitude / 1st EPSC peak amplitude
            
        EPSC amplitudes measurements:
            - at cursor placed at EPSC peak (manually) or by peak-finding
            - relative to baseline cursor before stimulus artifact
            - value = average of data within cursor's WINDOW
            
            
"""

#"def" pairedPulseEPSCs(data_block, Im_signal, Vm_signal, epoch = None):

class LTPWindow(ScipyenFrameViewer, __UI_LTPWindow__):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.settings = QtCore.QSettings()
        self.threadpool = QtCore.QThreadPool()
        
        self._data_ = dict()
        self._data_["Baseline"] = dict()
        self._data_["Baseline"]["Test"] = None
        self._data_["Baseline"]["Control"] = None
        self._data_["Chase"] = dict()
        self._data_["Chase"]["Test"] = None
        self._data_["Chase"]["Control"] = None
        
        self._viewers_ = dict()
        
        self._viewers_["baseline_source"] = None
        self._viewers_["conditioning_source"] = None
        self._viewers_["chase_source"] = None
        
        self._viewers_["pathways"] = dict()
        
        
        # NOTE: 2020-02-23 11:10:20
        # During conditioning the "Control" synaptic pathway is unperturbed but
        # it is possible to stimulate additional synaptic pathways for other
        # purposes: 
        # for NST+SWR experiments, a separate synmaptic pathway is used to
        # simulated sharp wave/ripple events
        # during cooperative LTP experiments, an additional "strong" pathway is 
        # stimulated concomitently with the "Test" (or "weak") pathway so that
        # LTP is induced in the weak pathway - without the strong pathway 
        # stimulation there would be no LTP on the weak ("Test") pathway.
        self._data_["Conditioning"] = dict()
        self._data_["Conditioning"]["Test"] = None
        
        
        # raw data: collections of neo.Blocks, sources from software 
        # vendor-specific data files. These can be:
        # a) axon (ABF v2) files (generated with Clampex)
        # 
        #    Each block contains data from a single trial.
        #
        #    In turn, each trial contains data ither from a single run, 
        #    or averaged data from several runs per trial (the timgins of 
        #    sweeps/run and run/trial should bve set so that they result
        #    in minute-by-minute averages). In the first case (single run per 
        #    trial) the data shuold be averaged offline, either manually or 
        #    using LTPWindow API.
        #
        # b) CFS files (generated with CED Signal) -- TODO
        #    there is usually a single file generated for the entire experiment
        #    but, depending on the script used for the acquisition, it may be
        #    accompanied by two other cfs files, each with pathway-specific 
        #    minute-by-minute average signals.
        #
        #    Notably, the "pulse" information is NOT saved with the file 
        #    unless extra ADC inputs are used to piggyback the digital output 
        #    signals (tee-ed out). Also, the sampling configuration allows
        #    several "pulse" protocols which can be selected / sequenced
        #    and do nto necessarily result in separate baseline and chase
        #    data.
        #
        self._baseline_source_data_ = list()
        self._chase_source_data_ = list()
        self._conditioning_source_data_ = list()
        self._path_xtalk_source_data_ = list()
        
        self._data_var_name_ = None
        
        self._ltpOptions_ = dict()
        
    def _configureGUI_(self):
        self.setupUi(self)
        
        self.actionOpenExperimentFile.triggered.connect(self.slot_openExperimentFile)
        self.actionOPenBaselineSourceFiles.triggered.connect(self.slot_openBaselineSourceFiles)
        self.actionOpenChaseSourceFiles.triggered.connect(self.slot_openChaseSourceFiles)
        self.actionOpenConditioningSourceFiles.triggered.connect(self.slot_openConditioningSourceFiles)
        self.actionOpenPathwayCrosstalkSourceFiles.triggered.connect(self.slot_openPathwaysXTalkSourceFiles)
        
        #self.dataIsMinuteAvegaredCheckBox.stateChanged[int].connect(self._slot_averaged_checkbox_state_changed_)
        
        self.actionOpenOptions.triggered.connect(self.slot_openOptionsFile)
        self.actionImportOptions.triggered.connect(self.slot_importOptions)
        
        self.actionSaveOptions.triggered.connect(self.slot_saveOptionsFile)
        self.actionExportOptions.triggered.connect(self.slot_exportOptions)
        
        self.pushButtonBaselineSources.clicked.connect(self.slot_viewBaselineSourceData)
        
        
    @pyqtSlot()
    @safeWrapper
    def slot_openOptionsFile(self):
        pass
    
    @pyqtSlot()
    @safeWrapper
    def slot_importOptions(self):
        pass
    
    @pyqtSlot()
    @safeWrapper
    def slot_saveOptionsFile(self):
        pass
    
    @pyqtSlot()
    @safeWrapper
    def slot_exportOptions(self):
        pass
        
    @pyqtSlot()
    @safeWrapper
    def slot_viewBaselineSourceData(self):
        if len(self._baseline_source_data_) == 0:
            return

        data = None
        
        if not isinstance(self._viewers_["baseline_source"], sv.SignalViewer):
            self._viewers_["baseline_source"] = sv.SignalViewer()
            
        viewer = self._viewers_["baseline_source"]
            
        if len(self._baseline_source_data_) == 1:
            data = self._baseline_source_data_[0]
            
        else:
            nameList = [b.name for b in self._baseline_source_data_]
            choiceDialog = pgui.ItemsListDialog(parent=self, title="Select Baseline Trial", itemsList = nameList)
            
            ans = choiceDialog.exec()
            
            if ans == QtWidgets.QDialog.Accepted and choiceDialog.selectedItem is not None:
                data_index = nameList.index(choiceDialog.selectedItem)
                data = self._baseline_source_data_[data_index]


        if isinstance(data, neo.Block):
            viewer.view(data)
            
    @pyqtSlot()
    @safeWrapper
    def slot_viewChaseSourceData(self):
        if len(self._chase_source_data_) == 0:
            return

        data = None
        
        if not isinstance(self._viewers_["conditioning_source"], sv.SignalViewer):
            self._viewers_["conditioning_source"] = sv.SignalViewer()
            
        viewer = self._viewers_["conditioning_source"]
            
        if len(self._chase_source_data_) == 1:
            data = self._chase_source_data_[0]
            
        else:
            nameList = [b.name for b in self._chase_source_data_]
            choiceDialog = pgui.ItemsListDialog(parent=self, title="Select Baseline Trial", itemsList = nameList)
            
            ans = choiceDialog.exec()
            
            if ans == QtWidgets.QDialog.Accepted and choiceDialog.selectedItem is not None:
                data_index = nameList.index(choiceDialog.selectedItem)
                data = self._chase_source_data_[data_index]


        if isinstance(data, neo.Block):
            viewer.view(data)
            
            
    @pyqtSlot()
    @safeWrapper
    def slot_viewConditioningSourceData(self):
        if len(self._conditioning_source_data_) == 0:
            return

        data = None
        
        if not isinstance(self._viewers_["conditioning_source"], sv.SignalViewer):
            self._viewers_["conditioning_source"] = sv.SignalViewer()
            
        viewer = self._viewers_["conditioning_source"]
            
        if len(self._conditioning_source_data_) == 1:
            data = self._conditioning_source_data_[0]
            
        else:
            nameList = [b.name for b in self._conditioning_source_data_]
            choiceDialog = pgui.ItemsListDialog(parent=self, title="Select Baseline Trial", itemsList = nameList)
            
            ans = choiceDialog.exec()
            
            if ans == QtWidgets.QDialog.Accepted and choiceDialog.selectedItem is not None:
                data_index = nameList.index(choiceDialog.selectedItem)
                data = self._conditioning_source_data_[data_index]


        if isinstance(data, neo.Block):
            viewer.view(data)
            
    @pyqtSlot()
    @safeWrapper
    def slot_viewCrossTalkSourceData(self):
        if len(self._path_xtalk_source_data_) == 0:
            return

        data = None
        
        if not isinstance(self._viewers_["conditioning_source"], sv.SignalViewer):
            self._viewers_["conditioning_source"] = sv.SignalViewer()
            
        viewer = self._viewers_["conditioning_source"]
            
        if len(self._path_xtalk_source_data_) == 1:
            data = self._path_xtalk_source_data_[0]
            
        else:
            nameList = [b.name for b in self._path_xtalk_source_data_]
            choiceDialog = pgui.ItemsListDialog(parent=self, title="Select Baseline Trial", itemsList = nameList)
            
            ans = choiceDialog.exec()
            
            if ans == QtWidgets.QDialog.Accepted and choiceDialog.selectedItem is not None:
                data_index = nameList.index(choiceDialog.selectedItem)
                data = self._path_xtalk_source_data_[data_index]


        if isinstance(data, neo.Block):
            viewer.view(data)
            
            
    #@pyqtSlot(int)
    #@safeWrapper
    #def _slot_averaged_checkbox_state_changed_(self, val):
        #checked = val == QtCore.Qt.Checked
        
        #self.sweepAverageGroupBox.setEnabled(not checked)
    
    
    def _parsedata_(self, newdata=None, varname=None):
        # TODO parse options
        if isinstance(newdata, (dict, type(None))):
            self._data_ = newdata
            
    @safeWrapper
    def _parse_clampex_trial_(self, trial:neo.Block):
        """TODO unfinished business
        """
        ret = dict()
        ret["interleaved_stimulation"] = False
        ret["averaged_sweeps"] = False
        ret["averaged_interval"] = 0*pq.s
        
        protocol = trial.annotations.get("protocol", None)
        
        if not isinstance(protocol, dict):
            return ret
        
        # by now the fields below should always be present
        nEpisodes = protocol["lEpisodesPerRun"]
        
        if nEpisodes != len(trial.segments):
            raise RuntimeError("Mismatch between protocol Episodes Per Run (%d) and number of sweeps in trial (%d)" % (nEpisodes, len(trial.segments)))
        
        runs_per_trial = protocol["lRunsPerTrial"]
        
        inter_trial_interval = procotol["fTrialStartToStart"] * pq.s
        inter_run_interval = protocol["fRunStartToStart"] * pq.s
        inter_sweep_interval = protocol["fEpisodeStartToStart"] * pq.s
        
        trial_duration = inter_run_interval * runs_per_trial
        if trial_duration == 0 * pq.s:
            raise RuntimeError("Trial metadata indicates trial duration of %s" % trial_duration )
        
        
        trials_per_minute = int((trial_duration + inter_trial_interval) / (60*pq.s))
        
        alternate_pathway_stimulation = protocol["nAlternateDigitalOutputState"] == 1
        
        alternate_command_ouptut = protocol["nAlternateDACOutputState"] == 1
        
        if alternate_pathway_stimulation:
            ret["interleaved_stimulation"] = True
            
        else:
            ret["interleaved_stimulation"] = False
            
            
        if runs_per_trial > 1:
            ret["averaged_sweeps"] = True
            if trials_per_minute == 1:
                ret["averaged_interval"] = 60*pq.s
                    
        # NOTE: 2020-02-23 14:46:57
        # find out if there is a protocol epoch for membrane test (whole-cell)
        
        protocol_epochs = trial.annotations["EpochInfo"]
        
        if len(protocol_epochs):
            if alternate_command_ouptut:
                # DAC0 and DAC1 commands are sent alternatively with each sweep
                # first sweep is DAC0;
                pass
        
        return ret
            
        
    @pyqtSlot()
    @safeWrapper
    def slot_openExperimentFile(self):
        import mimetypes, io
        targetDir = self._scipyenWindow_.currentDir
        
        pickleFileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, 
                                                                  caption="Open Experiment file",
                                                                  filter="Pickle Files (*.pkl)",
                                                                  directory=targetDir)
    
    
        if len(pickleFileName) == 0:
            return
        
        data = pio.loadPickleFile(pickleFileName)
        
        if not self._check_for_linescan_data_(data):
            QtWidgets.QMessageBox.critical(self, "Open ScanData file", "Chosen file does not contain a valid ScanData object")
            return
        
        _data_var_name_ = os.path.splitext(os.path.basename(pickleFileName))[0]
        
        self._parsedata_(data, _data_var_name_)
        
        self._scipyenWindow_.assignToWorkspace(_data_var_name_, data)
        
    @pyqtSlot()
    @safeWrapper
    def slot_openBaselineSourceFiles(self):
        """Opens vendor-specific record files with trials for the baseline responses.
        
        Currently only ABF v2 files are supported.
        
        TODO add support for CED Signal files, etc.
        
        TODO Parse electrophysiology records meta information into a vendor-agnostic
        data structure -- see core.neoutils module.
        """
        # list of neo.Blocks, each with a baseline trial
        # these may already contain minute-averages
        self._baseline_source_data_ = self.openDataAcquisitionFiles()
        
        #### BEGIN code to parse the record and interpret the protocol - DO NOT DELETE
        
        ## we need to figure out:
        ##
        ## 1) if the data contains averaged sweeps and if so, whether these are
        ##       minute averages
        ##
        ## 2) how many stimulation pathways are involved
        ##
        ## 3) what is the test stimulus: 
        ##       single or paired-pulse
        ##       stimulus onset (in each pathway)
        ##       if paired-pulse, what is the inter-stimulus interval
        
        #trial_infos = [self._parse_clampex_trial_(trial) for trial in self._baseline_source_data_]
        
        #for k, ti in enumerate(trial_infos[1:]):
            #for key in ti:
                #if ti[key] != trial_infos[0][key]:
                    #raise RuntimeError("Mismatch in %s betweenn first and %dth trial" % (key, k+1))
                
        
        
        
        #if trial_infos[0]["averaged_sweeps"]:
            #if trial_infos[0]["averaged_interval"] != 60*pq.s:
                #raise ValueError("Expecting sweeps averaged over one minute interval; got %s instead" % trial_infos[0]["averaged_interval"])
            
            #signalBlockers = [QtCore.QSignalBlocker(w) for w in [self.dataIsMinuteAvegaredCheckBox]]
            
            #self.dataIsMinuteAvegaredCheckBox.setCheckState(True)
            
            #self.sweepAverageGroupBox.setEnabled(False)
            
        #else:
            #self.dataIsMinuteAvegaredCheckBox.setCheckState(False)
            
            #self.sweepAverageGroupBox.setEnabled(True)
            
        #### END code to parse the record and interpret the protocol
            
    @pyqtSlot()
    @safeWrapper
    def slot_openChaseSourceFiles(self):
        self._chase_source_data_ = self.openDataAcquisitionFiles()
        
    @pyqtSlot()
    @safeWrapper
    def slot_openConditioningSourceFiles(self):
        self._conditioning_source_data_ = self.openDataAcquisitionFiles()
        
    @pyqtSlot()
    @safeWrapper
    def slot_openPathwaysXTalkSourceFiles(self):
        self._path_xtalk_source_data_ = self.openDataAcquisitionFiles()
        
    @safeWrapper
    def openDataAcquisitionFiles(self):
        """Opens electrophysiology data acquisition files.
        
        Currently supports the following electrphysiology acquisition software:
        pClamp(Axon binary files version 2 (*.abf) and axon text files, *.atf
        
        TODO: support for:
            CED Signal CED Filing System files (*.cfs)
            CED Spike2 files (SON library)
            Ephus (matlab files?)
        
        """
        import mimetypes, io
        targetDir = self._scipyenWindow_.currentDir
        
        # TODO: 2020-02-17 17:44:55 
        # 1) write code for CED Signal files (*.cfs)
        # 2) write code for Axon Text files
        # 3) write code for pickle files
        # 4) Allow all files then pick up the appropriate loader for each file.
        #
        # Although it may seem convenient for the user, cases 1-4 above complicate 
        # the code for the following reasons:
        # case 1: we need to actually write the CFS file reading logic :-)
        # case 2: the need to make sure that each text file resoves to an appropriate
        # neo.Block (adapt from the code for binary files?)
        # case 3: the pickle file may contain already concatenated records, so we 
        # need a way to distinguish that (adapt from the code for binary files?)
        # case 4: compounds all of the above PLUS resolve the file loader for each
        # file in the list
        # 
        # To keep it simple, we avoid the "All Files" case (for now)
        
        # TODO 2020-02-17 17:49:46
        # how to process axon text files?
        # Again, avoid this case also
        #file_filters = ";; ".join( ["Axon Binary Files (*.abf)",
                                    #"Axon Text Files (*.atf)",
                                    #"CED Signal Files (*.cfs)",
                                    #"Python Pickle Files (*.pkl)",
                                    #"All Files (*.*)"])
        
        file_filters = ";; ".join( ["Axon Binary Files (*.abf)"])
        
        
        
        
        # fileNames: list of fully qualified file names
        # fileFilter: the actual file filter used in the dialog
        fileNames, fileFilter = QtWidgets.QFileDialog.getOpenFileNames(mainWindow, 
                                                                       filter=file_filters)

        if len(fileNames) == 0:
            return
        
        if "Axon Binary" in fileFilter:
            record_data = [pio.loadAxonFile(f) for f in fileNames]
            
        else:
            raise RuntimeError("%s are not supported" % fileFilter)
        
        # NOTE: 2020-02-17 17:51:32
        #### BEGIN DO NOT DELETE - TO BE REVISITED
        #elif "Axon Text" in fileFilter:
            #axon_data = [pio.loadAxonTextFile(f) for f in fileNames]
            #data = [a[0] for a in axon_data]
            ## CAUTION 2020-02-17 17:40:17 test this !
            #metadata = [a[1] for a in axon_data]
            
        #elif "Pickle" in fileFilter:
            ## ATTENTION: 2020-02-17 17:41:58 keep fingers crossed
            #data = [pio.loadPickleFile(f) for f in fileNames]
            
        #elif "CED" in fileFilter:
            #warnings.warn("CED Signal Files not  yet supported")
        #### END DO NOT DELETE
            
        return record_data
    
            
def generate_synaptic_plasticity_options(**kwargs) -> dict:
    """Constructs a dict with options for synaptic plasticity experiments.
    
    The options specify synaptic pathways, analysis cursors and optional 
    minute-by-minute averaging of data from synaptic plasticity experiments.
    
    All synaptic plasticity experiments have a stimulation pathway 
    ("test pathway") where synaptic responses are monitored before and after 
    a conditioning protocol is applied. Homo-synaptic plasticity is considered
    to occur when the conditioning protocol induces changes in the magnitude
    of the synaptic response in the conditioned pathway.
    
    The "test" pathway is assigned index 0 by default, unless specified 
    otherwise.
    
    Ideally, synaptic responses are also monitored on a "control" pathway, which 
    is unperturbed during the conditioning, in order to distinguish the changes
    in synaptic responses in the conditioned ("test") pathway, from changes 
    induced by other causes conditioned (test) pathway.
    
    When a "control" pathway is present, the data from the two pathways is
    expected to have been recorded in alternative, interleaved sweeps.
    
    NOTE: These options are adapted for off-line analysis of data acquired with
    custom protocols in Clampex.
    
    TODO: 
    1. Accommodate data acquired in Clampex using the built-in LTP protocol
    2. Accommodate data acquired with CED Signal (v5 and later).
    3. Allow for single pathway experiments (i.e. test pathway only)
    4. Allow for monitoring extra synaptic pathways (e.g., cooperative LTP as in
       Golding et al, Nature 2002)
    5. Use in acquisition; on-line analysis.
    
    Var-keyword parameters:
    =======================
    
    "field":bool = flag indicating whether the options are for field recordings
        (when True) or whole-cell and intracellular recordings (False)
        Default is False.
    
    "average":int = number of consecutive single-run trials to average 
        off-line (default: 6).
        
        A value of 0 indicates no off-line averaging. 
        
    "every":int   = number of consecutive single-run trials to skip before next 
        offline average (default: 6)
        
    "reference":int  = number of minute-average responses used to assess 
        plasticity; this is the number of reponses at the end of the chase
        stage, and it equals the number of responses at the end of the baseline
        stage. Therefore it cannot be larger than the duration of the baseline 
        stage, in minutes.
        
        Default is 5 (i.e. compare the average of the last 5 minute-averaged 
            responses of the chase stage, to the average of the last 5 
            minute-averaged responses of the baseline stage, in each pathway)
            
            
    "cursor_measures": dict = cursor-based measurements used in analysis.
        Can be empty
        each key is a str (measurement name) that is mapped to a nested dict 
            with the following keys:
        
            "function": a cursor-based signal function as defined in the 
                neoutils module, or membrane module
            
                function(signal, cursor0, cursor1,...,channel) -> Quantity
            
                The function accepts a neo.AnalogSignal or datatypes.DataSignal
                as first parameter, 
                followed by any number of vertical SignalCursor objects
                
                The functions must be defined and present in the scope therefore
                they can be specified as module.function, unless imported 
                directly in the workspace where ltp analysis is performed.
            
                Examples: 
                neoutils.cursors_chord_slope()
                neoutils.cursors_difference()
                ephys.membrane.cursor_Rs_Rin()
            
            "cursors": list of (x, xwindow, label) triplets that specify
             notional vertical signal cursors
                
                NOTE: SignalCursor objects cannot be serialized. Therefore, in 
                order for the options to be persistent, the cursors have to be
                represented by their parameter tuple (time, window) which can be
                stored on disk, and used to generate a cursor at runtime.
                
            "channel": (optional) if present, it must contain an int
            
            "pathway": int, the index of the pathway where the measurement is
                performed, or None (applied to both pathways)
                
        "epoch_measures": dict: epoch_based measurements
            Can be empty.
            
            Has a similar structure to cursor_measures, but uses epoch-based
            measurement functions instead.
            
            "function": epoch-based signal function as defined in the neoutils and
                membrane modules
                
            "epoch": a single neo.Epoch (they can be serialized) or the tuple
                (times, durations, labels, name) with arguments suitable to 
                construct the Epoch at run time.
            
            Examples:
            neoutils.epoch_average
        
        Using the examples above:
        
        measures[""]
        
        
        
    "test":int , default = 0 index of the "test" pathway, for dual pathway
        interleaved experiments.
        
        For data acquired using Clampex with a custom LTP protocol, this 
        represents the index of the test pathway sweep within each run.
        The sampling protocol is expected to record data alternatively
        from the test and control pathway. 
        
        Trials with a single run will be saved to disk as files contains two 
        sweeps, one for each pathway. 
        
        When the protocol specifies several runs per trial, the saved file will
        also contain two sweeps, with data for the corresponding pathway being 
        averaged acrosss the runs.
    
    "control":int, default = 1
    
    """
    field = kwargs.pop("field", False)
    
    test_path = kwargs.pop("test", 0)
    
    if test_path < 0 or test_path > 1:
        raise ValueError("Invalid test path index (%d); expecting 0 or 1" % test_path)
    
    control_path = kwargs.pop("control", None)
    
    if isinstance(control_path, int):
        if control_path < 0 or control_path > 1:
            raise ValueError("Invalid control path index (%d) expecting 0 or 1" % control_path)
        
        if control_path == test_path:
            raise ValueError("Control path index must be different from the test path index (%d)" % test_path)
    
    average = kwargs.pop("average", 6)
    average_every = kwargs.pop("every", 6)
    
    reference = keargs.pop("reference", 5)
    
    measure = kwargs.pop("measure", "amplitude")
    
    cursors = kwargs.pop("cursors", dict())
    
    LTPopts = dict()
    
    LTPopts["Average"] = {'Count': average, 'Every': average_every}
    LTPopts["Pathways"] = dict()
    LTPopts["Pathways"]["Test"] = test_path
    
    if isinstance(control_path, int):
        LTPopts["Pathways"]["Control"] = control_path
        
    LTPopts["Reference"] = kwargs.get("Reference", 5)
    
    
    if field:
        LTPopts["Signals"] = kwargs.get("Signals",['Vm_sec_1'])
        
        if len(cursors):
            LTPopts["Cursors"] = cursors
            
        else:
            LTPopts["Cursors"] = {"fEPSP0_10": (0.168, 0.001), 
                                  "fEPSP0_90": (0.169, 0.001)}
            
            #LTPopts["Cursors"] = {'Labels': ['fEPSP0','fEPSP1'],
                                #'time': [0.168, 0.169], 
                                #'Pathway1': [5.168, 5.169], 
                                #'Windows': [0.001, 0.001]} # NOTE: cursor windows are not used here
            
        
    else:
        LTPopts["Signals"] = kwargs.get("Signals",['Im_prim_1', 'Vm_sec_1'])
        LTPopts["Cursors"] = {'Labels': ['Rbase','Rs','Rin','EPSC0base','EPSC0Peak','EPSC1base','EPSC1peak'],
                              'Pathway0': [0.06, 0.06579859882206893, 0.16, 0.26, 0.273, 0.31, 0.32334583993039734], 
                              'Pathway1': [5.06, 5.065798598822069,   5.16, 5.26, 5.273, 5.31, 5.323345839930397], 
                              'Windows': [0.01, 0.003, 0.01, 0.01, 0.005, 0.01, 0.005]}
        
    
    return LTPopts
    
def generate_LTP_options(cursors, signal_names, path0, path1, baseline_minutes, \
                        average_count, average_every):
    """Save LTP options for Voltage-clamp experiments
    
    cursors = iterable with four elements
        labels              (iterable of str)
        times for path 0    (iterable of floats)
        times for path 1    (iterable of floats)
        windows             (iterable of floats)
        
        where each of which are iterables of same length, containing data types as described above.
        
        Obviously, this assumes that cursor times are the same for each segment (sweep) in a given pathway,
        and that all cursor widows are identical.
    
    signal_names   = sequence of two strings with the names of the analog signals for Im and Vm, respectively
                     or sequence of two integral indices (for the Im and Vm analog signals, respectively)

    path0   = int: index of the segments (within the block) holding data from the 1st pathway
    
    path1   = int or None: index of the segments (within the block) for the 2nd pathway (or None for single path experiments)
    
    baseline_minutes = int: number of last baseline minutes before conditioning, to consider for
                    normalizing the EPSCs
                    
    average: bool. Whether to average individual blocks in order to generage minute-average data.
        For pClamp:
            When the acquisition protocol specifies one run/trial, each Axon binary file
            contains individual sweeps (one per path)
    average_count  = int: number of trials to average per minute
    average_every  = int: number of trials to skip between two consecutive averages
                                        
    NOTE:
    
    For a two-pathway protocol (the GOLD STANDARD), the data is expected to have been recorded 
    as alternative segments (sweeps), one for each pathway. In Clampex this is achieved 
    by a "trial" with one "run", with two "sweeps" per "run" (protocol editor window,
    "Mode/Rate" tab. Furthermore, the sweeps are set up as "alternative" in the 
    "Waveform" tab (both "ALternate waveforms" and "Alternate digital outputs" are turned ON).
    The protocol is then repeated indefinitely while recording
    (by activating the "repeat" toggle button in the Acquisition toolbar of Clampex). 
    
    For voltage clamp, the membrane current AND the membrane voltage commands
    should be recorded (by making sure they are selected as inputs into the protocol 
    editor).
    
    This results in a single file per trial, containing unaveraged signals (sweeps)
    for each run, which when loaded individually in python, will generate a series
    of Block objects, each with two segments, corresponding to the repsonse in each 
    pathway, for each run (trial).
    
    For a single pathway, there should be one segment (sweep) per block. In clampex 
    this means one sweep per run.
    
    TODO: adapt for CED Signal data as well, bearing in mind that all experiment data 
    (excep for the protocol itself, see below) is saved in a single cfs file 
    (including baseline pre-conditioning, conditioning, AND chase post-conditioning). 
    For a two-pathway LTP protcol (which is the STANDARD) this would (should?) 
    result in a single Block with an even number of segments (alternatively probing
    each pathway).
    
    The command voltage is not immediately available in CED files (although the command
    voltage waveform and ist timings are save in the conguration file). This signal can.
    however, be recorded in Signal5 by routing from the amplifier into another analog input
    in the CED board (if available!) and recording it by apropriately configuring the Signal5.
    
    Failing that, one can use Vm=True in fruther analyses and supply the value of the test Vm pulse in 
    signal_index_Vm in LTP functions.
    
    The CED issue is not of immediate importance as this kind of analysis is easily done in Signal5
    directly and in real-time (or offline)

    CED protocols are saved independently of recording in sgc configuration files.
    
    TODO: specify the Vm when command voltage signal is not available in voltage-clamp
    
    TODO: adapt for current-clamp/field recording experiments as well.
    
    TODO: accept signal indices as well, not just names, although using names keeps it more
    generic and insensitive to changes in signal order inside a segment, between experiments
    
    """
    
    options = dict()
    
    #crs = collections.namedtuple("Cursors")
    
    options["Cursors"] = {"Labels":cursors[0], "Pathway0": cursors[1], "Pathway1": cursors[2], "Windows": cursors[3]}
    
    if signal_names is not None:
        if isinstance(signal_names, (list, tuple)) and len(signal_names) > 0 and len(signal_names) <=2 and all(isinstance(n, str) for n in signal_names):
            options["Signals"] = signal_names
        elif isinstance(signal_names,str):
            options["Signals"] = signal_names
        else:
            raise TypeError("Unexpected type for signal_names")
    else:
        raise ValueError("signal_names cannot be None")
    
    
    options["Pathway0"] = path0
    options["Pathway1"] = path1
    
    options["Reference"] = baseline_minutes
    
    options["Average"] = {"Count" : average_count, "Every" : average_every}
    
    return options
    
    
            
def save_LTP_options(val):
    if not os.path.isdir(optionsDir):
        os.mkdir(optionsDir)
        
    with open(LTPOptionsFile, "wb") as fileDest:
        pickle.dump(val, fileDest, pickle.HIGHEST_PROTOCOL)
    
@safeWrapper
def load_synaptic_plasticity_options(LTPOptionsFile:[str, type(None)]=None, **kwargs):
    """Loads LTP options from a file or generates one from arguments.
    
    Parameters:
    ===========
    LTPOptionsFile: str or None (default)
        If a str, it should resolve to an existing pickle file containing a 
        dictionary with valid synaptic plasticity options.
        
        When None, a dictionary of LTP options is generated using kwargs and
        "reasonable" defaults.
        
        WARNING: the contents of the dictionary are not checked for validity as
        options in synaptic plasticity experiments.
        
    Var-keyword parameters:
    =======================
    Passed directly to generate_synaptic_plasticity_options(), used when 
    LTPOptionsFile is None or specifies a non-existent file. 
        
    
    """
    
    if LTPOptionsFile is None or not os.path.isfile(LTPOptionsFile):
        
        LTPopts = generate_synaptic_plasticity_options(**kwargs)
        
        print("Now, save the options as %s" % os.path.join(os.path.dirname(__file__), "options", "LTPOptions.pkl"))
        
        #raise RuntimeError("No options file found. Have you ever run save_LTP_options ?")
    else:
        with open(LTPOptionsFile, "rb") as fileSrc:
            LTPopts = pickle.load(fileSrc)
        
    return LTPopts

@safeWrapper
def generate_minute_average_data_for_LTP(prefix_baseline, prefix_chase, LTPOptions, test_pathway_index, result_name_prefix):
    """
    basenames : two-element tuple with regexp strings, respectively for the variable names of 
                the baseline and chase Blocks
                
    LTPOptions : a dict as returned by generate_LTP_options
    
    test_pathway_index : an int (0 or 1) indicating which of the two pathways is the test pathway
    
    Returns a dict with two fields: "Test" and "Control", mapping the data for the 
            Test and Control pathways, respectively.
            In turn the data is itself a dict with two fields: "Baseline" and "Chase"
            mapping onto the minute-by-minute average of the sweep data in the 
            respective pathway.
    
    """
    from operator import attrgetter, itemgetter, methodcaller
    
    if not isinstance(test_pathway_index, int):
        raise TypeError("Unexpected type for test_pathway_index: must be an int (0 or 1)")
    
    if test_pathway_index < 0 or test_pathway_index > 1:
        raise ValueError("Unexpected value for test pathway index: must be either 0 or 1")
    
    baseline_blocks = [b for b in wf.getvars(prefix_baseline) if isinstance(b, neo.Block)]
        
    baseline_blocks.sort(key = attrgetter("rec_datetime"))
    
    
    chase_blocks = [b for b in wf.getvars(prefix_chase) if isinstance(b, neo.Block)]
        
    chase_blocks.sort(key = attrgetter("rec_datetime"))
    
    #print(len(baseline_blocks))
    #print(len(chase_blocks))
    
    if LTPOptions["Average"] is None:
        baseline = [neoutils.concatenate_blocks(baseline_blocks,
                                                segment_index = LTPOptions["Pathway0"],
                                                signal_index = LTPOptions["Signals"],
                                                name = result_name_prefix + "_path0_baseline"),
                    neoutils.concatenate_blocks(baseline_blocks,
                                                segment_index = LTPOptions["Pathway1"],
                                                signal_index = LTPOptions["Signals"],
                                                name = result_name_prefix + "_path1_baseline")]
    else:
        baseline    = [neoutils.average_blocks(baseline_blocks,
                                            segment_index = LTPOptions["Pathway0"],
                                            signal_index = LTPOptions["Signals"],
                                            count = LTPOptions["Average"]["Count"],
                                            every = LTPOptions["Average"]["Every"],
                                            name = result_name_prefix + "_path0_baseline"),
                    neoutils.average_blocks(baseline_blocks,
                                            segment_index = LTPOptions["Pathway1"],
                                            signal_index = LTPOptions["Signals"],
                                            count = LTPOptions["Average"]["Count"], 
                                            every = LTPOptions["Average"]["Every"], 
                                            name = result_name_prefix + "_path1_baseline")]
              
    baseline[test_pathway_index].name += "_Test"
    baseline[1-test_pathway_index].name += "_Control"
    
    
    if LTPOptions["Average"] is None:
        chase   = [neoutils.concatenate_blocks(chase_blocks,
                                                segment_index = LTPOptions["Pathway0"],
                                                signal_index = LTPOptions["Signals"],
                                                name = result_name_prefix + "_path0_chase"),
                   neoutils.concatenate_blocks(chase_blocks,
                                                segment_index = LTPOptions["Pathway1"],
                                                signal_index = LTPOptions["Signals"],
                                                name = result_name_prefix + "_path1_chase")]
        
    else:
        chase   = [neoutils.average_blocks(chase_blocks,
                                            segment_index = LTPOptions["Pathway0"], 
                                            signal_index = LTPOptions["Signals"],
                                            count = LTPOptions["Average"]["Count"], 
                                            every = LTPOptions["Average"]["Every"],
                                            name = result_name_prefix + "_path0_chase"),
                   neoutils.average_blocks(chase_blocks,
                                            segment_index = LTPOptions["Pathway1"], 
                                            signal_index = LTPOptions["Signals"],
                                            count = LTPOptions["Average"]["Count"], 
                                            every = LTPOptions["Average"]["Every"],
                                            name = result_name_prefix + "_path1_chase")]
                
    chase[test_pathway_index].name += "_Test"
    chase[1-test_pathway_index].name += "_Control"
    
    ret = {"Test"    : {"Baseline" : baseline[test_pathway_index],   "Chase" : chase[test_pathway_index],   "Path" : test_pathway_index}, \
           "Control" : {"Baseline" : baseline[1-test_pathway_index], "Chase" : chase[1-test_pathway_index], "Path" : 1-test_pathway_index}, \
           "LTPOptions": LTPOptions, "name":result_name_prefix}
        

    return ret

def calculate_fEPSP(block:neo.Block,
                    signal_index:[int, str],
                    epoch:[neo.Epoch, type(None)]=None,
                    out_file:[str, type(None)]=None) -> dict:
    """
    Calculates the slope of field EPSPs.
    
    Parameters:
    ===========
    block: a neo.Block; must contain the analogsignal for the field potential,
        found at the same index in each segment's list of analogsignals,
        throughout the block.
        
    signal_index: int or str.
        When an int: the index of the field potential signal, in the collection
            of analog signals in each segment (same index throughout)
            
        When a str: the name of the analog signal containing the field potential
            data. It must be present in alll segments of the block.
        
            
    epoch: a neo.Epoch, or None (default).
        When a neo.Epoch, it must have at least one interval defined:
        fEPSP0, (optionally, fEPSP1)

     When None, the epoch is supposed to be found embedded in each segment of 
     the block.
     
    
    Returns
    =======
    
    A dict with the following keys:
    
    "fEPSP0" slope of the first field EPSP
    
    Optionally (if there are two intervas in the epoch):
    
    "fEPSP1" slope of the first field EPSP
    "PPR" (paired-pulse ratio)
    
    """
    
    if isinstance(signal_index, str):
        singal_index = neoutils.get_index(block, signal_index)
        
    for k, seg in enumerate(block.segments):
        pass
    
def calculateRmEPSCsLTP(block: neo.Block, 
                        signal_index_Im, 
                        signal_index_Vm, 
                        Vm = False, 
                        epoch = None, 
                        out_file=None) -> dict:
    """
    Calculates membrane Rin, Rs, and EPSC amplitudes in whole-cell voltage clamp.
    
    Parameters:
    ==========
    block: a neo.Block; must contain one analogsignal each for Im and Vm;
        these signals must be found at the same indices in each segment's list
        of analogsignals, throughout the block.
    
    epoch: a neo.Epoch; must have 5 or 7 intervals defined:
        Rbase, Rs, Rin, EPSC0base, EPSC0peak (optionally, EPSC1base, EPSC1peak)
        
    signal_index_Im: index of the Im signal
    signal_index_Vm: index of the Vm signal (if Vm is False) else the detla Vm used in the Vmtest pulse
    
    Vm: boolean, optional( default it False); when True, then signal_index_Vm is taken to be the actul
        amount of membrane voltage depolarization (in mV) used during the Vm test pulse
        
    NOTE: 2017-04-29 22:41:16 API CHANGE
    Returns a dictionary with keys as follows:
    
    (Rs, Rin, DC, EPSC0) - if there are only 5 intervals in the epoch
    
    (Rs, Rin, DC, EPSC0, EPSC1, PPR) - if there are 7 intervals defined in the epoch
    
    Where EPSC0 and EPSC1 anre EPSc amplitudes, and PPR is the paired-pulse ratio (EPSC1/EPSC0)
    
    """
    Irbase = np.ndarray((len(block.segments)))
    Rs     = np.ndarray((len(block.segments)))
    Rin    = np.ndarray((len(block.segments)))
    EPSC0  = np.ndarray((len(block.segments)))
    EPSC1  = np.ndarray((len(block.segments)))
    
    ui = None
    ri = None
    
    
    if isinstance(signal_index_Im, str):
        signal_index_Im = neoutils.get_index(block, signal_index_Im)
    
    if isinstance(signal_index_Vm, str):
        signal_index_Vm = neoutils.get_index(block, signal_index_Vm)
        Vm = False
        
    for (k, seg) in enumerate(block.segments):
        (irbase, rs, rin, epsc0, epsc1) = _segment_measure_synaptic_plasticity_v_clamp_(seg, signal_index_Im, signal_index_Vm, Vm=Vm, epoch=epoch)
        ui = irbase.units
        ri = rs.units
        
        Irbase[k] = irbase
        Rs[k]     = rs
        Rin[k]    = rin
        EPSC0[k]  = epsc0
        EPSC1[k]  = epsc1

    ret = dict()
    
    ret["Rs"] = Rs * ri
    ret["Rin"] = Rin * ri
    ret["DC"] = Irbase * ui
    ret["EPSC0"] = EPSC0 * ui
    
    if all(EPSC1):
        ret["EPSC1"] = EPSC1* ui
        ret["PPR"] = ret["EPSC1"]/ ret["EPSC0"]
        
    if isinstance(out_file, str):
        if all(EPSC1):
            header = ["EPSC0", 
                      "EPSC1", 
                      "PPR", 
                      "Rs", 
                      "Rin", 
                      "DC"]
            
            units = [str(ui), 
                     str(ui), 
                     str(ret["PPR"].units), 
                     str((ret["Rs"]*1000).units), 
                     str((ret["Rin"]*1000).units),
                     str(ret["DC"].units)]
            
            out_array = np.concatenate((EPSC0[:,np.newaxis],
                                        EPSC1[:,np.newaxis],
                                        ret["PPR"].magnitude[:,np.newaxis],
                                        (Rs*1000)[:,np.newaxis],
                                        (Rin*1000)[:,np.newaxis],
                                        Irbase[:,np.newaxis]), axis=1)
            
        else:
            header = ["EPSC0", 
                      "Rs", 
                      "Rin", 
                      "DC"]
            
            units = [str(ui), 
                     str((ret["Rs"]*1000).units), 
                     str((ret["Rin"]*1000).units),
                     str(ret["DC"].units)]
            
            out_array = np.concatenate((EPSC0[:,np.newaxis],
                                        (Rs*1000)[:,np.newaxis],
                                        (Rin*1000)[:,np.newaxis],
                                        Irbase[:,np.newaxis]), axis=1)
            
        header = np.array([header, units])
        
        pio.writeCsv(out_array, out_file, header=header)
        
        
    return ret

@safeWrapper
def calculate_segment_Rs_Rin(segment: neo.Segment):
    pass

def _segment_measure_synaptic_plasticity_i_clamp_(s: neo.Segment, 
                                       signal_index: int, 
                                       epoch: typing.Optional[neo.Epoch]=None) -> np.ndarray:
    if epoch is None:
        if len(s.epochs) == 0:
            raise ValueError("Segment has no epochs and no external epoch has been defined")

        epoch = s.epochs[0]
        
        if len(epoch) != 1 and len(epoch) != 2:
            raise ValueError("Expecting an Epoch with 1 or 2 intervals; got %d instead" % len(epoch))
        
        # each epoch interval should cover the signal time slice over which the 
        # chord slope of the field EPSP is calculated; this time slice should be
        # between the x coordinates of two adjacent cursors, placed respectively 
        # on 10% and 90% from base to (negative) peak (10-90 "rise time")
        
        t0 = epoch.times
        dt = epoch.durations
        t1 = epoch.times + dt
        
        signal = s.analogsignals[signal_index]
        
        epsp_rises = [signal.time_slice(t_0, t_1) for t_0, t_1 in zip(t0,t1)]
        
        chord_slopes = [((sig.max()-sig.min())/d_t).rescale(pq.V/pq.s) for (sig, d_t) in zip(epsp_rises, dt)]
        
        return chord_slopes
        
        
def _segment_measure_synaptic_plasticity_v_clamp_(s: neo.Segment,
                                       signal_index_Im: int,
                                       signal_index_Vm: int, 
                                       Vm: bool=False,
                                       epoch: typing.Optional[neo.Epoch]=None) -> tuple:
    if epoch is None:
        if len(s.epochs) == 0:
            raise ValueError("Segment has no epochs and no external epoch has been defined")
        
        epoch = s.epochs[0]
        
        if len(epoch) != 5 and len(epoch) != 7:
            raise ValueError("Epoch as supplied or taken from segment has incorrect length; expected to contain 5 or 7 intervals")
        
        t0 = epoch.times
        t1 = epoch.times + epoch.durations
    
        Irbase = np.mean(s.analogsignals[signal_index_Im].time_slice(t0[0], t1[0]))
        
        Irs    = np.max(s.analogsignals[signal_index_Im].time_slice(t0[1], t1[1])) 
        
        Irin   = np.mean(s.analogsignals[signal_index_Im].time_slice(t0[2], t1[2]))
        
        if Vm:
            Rs  = signal_index_Vm * pq.mV / (Irs - Irbase)
            Rin = signal_index_Vm * pq.mV / (Irin - Irbase)
            
        else:
            Vbase = np.mean(s.analogsignals[signal_index_Vm].time_slice(t0[0], t1[0])) 

            Vin   = np.mean(s.analogsignals[signal_index_Vm].time_slice(t0[2], t1[2])) 

            Rs     = (Vin - Vbase) / (Irs - Irbase)
            Rin    = (Vin - Vbase) / (Irin - Irbase)
            
        Iepsc0base = np.mean(s.analogsignals[signal_index_Im].time_slice(t0[3], t1[3])) 
        
        Iepsc0peak = np.mean(s.analogsignals[signal_index_Im].time_slice(t0[4], t1[4])) 
    
        EPSC0 = Iepsc0peak - Iepsc0base
        
        if len(epoch) == 7:
            
            Iepsc1base = np.mean(s.analogsignals[signal_index_Im].time_slice(t0[5], t1[5])) 
            
            Iepsc1peak = np.mean(s.analogsignals[signal_index_Im].time_slice(t0[6], t1[6])) 
            
            EPSC1 = Iepsc1peak - Iepsc1base
            
        else:
            EPSC1 = None
            
            

    return (Irbase, Rs, Rin, EPSC0, EPSC1)

                 
def analyzeLTPPathway(baseline_block:neo.Block, 
                      chase_block:neo.Block, 
                      LTPOptions:dict,
                      signal_index_Im, 
                      signal_index_Vm, 
                      path_index,
                      baseline_epoch=None, 
                      chase_epoch = None,
                      Vm = False,
                      baseline_range=range(-5,-1),
                      basename=None, 
                      pathType=None,
                      normalize=False,
                      field=False):
    """
    baseline_block
    chase_block
    path_index
    signal_index_Im
    signal_index_Vm
    baseline_epoch  = None
    chase_epoch     = None
    Vm              = False
    baseline_range  = range(-5,-1)
    basename        = None
    """
    if field:
        pass
        
    else:
        baseline_result     = calculateRmEPSCsLTP(baseline_block, signal_index_Im = signal_index_Im, signal_index_Vm = signal_index_Vm, Vm = Vm, epoch = baseline_epoch)
        chase_result        = calculateRmEPSCsLTP(chase_block,    signal_index_Im = signal_index_Im, signal_index_Vm = signal_index_Vm, Vm = Vm, epoch = chase_epoch)
    
    meanEPSC0baseline   = np.mean(baseline_result["EPSC0"][baseline_range])
    
    if normalize:
        baseEPSC0Norm       = baseline_result["EPSC0"]/meanEPSC0baseline
        chaseEPSC0Norm      = chase_result["EPSC0"]/meanEPSC0baseline
    
    else:
        baseEPSC0Norm       = baseline_result["EPSC0"]
        chaseEPSC0Norm      = chase_result["EPSC0"]
        
    #baseline_times      = [seg.rec_datetime for seg in baseline_block.segments] # not used atm
    
    if basename is None:
        basename = ""
        
    if path_index is not None:
        basename += "_path%d" % (path_index)
        
    if normalize:
        header = ["Index_path_%d_%s"        % (path_index, pathType), \
                  "EPSC0_norm_path_%d_%s"   % (path_index, pathType), \
                  "PPR_path_%d_%s"          % (path_index, pathType), \
                  "Rin_path_%d_%s"          % (path_index, pathType), \
                  "RS_path_%d_%s"           % (path_index, pathType), \
                  "DC_path_%d_%s"           % (path_index, pathType)]

    else:
        header = ["Index_path_%d_%s"        % (path_index, pathType), \
                  "EPSC0_path_%d_%s"        % (path_index, pathType), \
                  "PPR_path_%d_%s"          % (path_index, pathType), \
                  "Rin_path_%d_%s"          % (path_index, pathType), \
                  "RS_path_%d_%s"           % (path_index, pathType), \
                  "DC_path_%d_%s"           % (path_index, pathType)]
        
    units  = [" ",  str(baseEPSC0Norm.units), \
                    str(baseline_result["PPR"].units), \
                    str((baseline_result["Rin"]*1000).units), \
                    str((baseline_result["Rs"]*1000).units), \
                    str(baseline_result["DC"].units)]
    
    header = np.array([header, units])
    
    #print(header)
    #print(header.dtype)
    
    EPSC0NormOut_base = np.concatenate((np.arange(len(baseEPSC0Norm))[:,np.newaxis], \
                                        baseEPSC0Norm[:,np.newaxis].magnitude), axis=1)
    
    EPSC0NormOut_chase = np.concatenate((np.arange(len(chaseEPSC0Norm))[:, np.newaxis] ,\
                                        chaseEPSC0Norm[:,np.newaxis].magnitude), axis=1)
    
    EPSC0NormOut = np.concatenate((EPSC0NormOut_base, EPSC0NormOut_chase), axis=0)
    
    Rin_out = np.concatenate(((baseline_result["Rin"]*1000).magnitude, (chase_result["Rin"]*1000).magnitude))
    
    Rs_out = np.concatenate(((baseline_result["Rs"]*1000).magnitude, (chase_result["Rs"]*1000).magnitude))
    
    PPR_out = np.concatenate((baseline_result["PPR"].magnitude, chase_result["PPR"].magnitude))
    
    DC_out = np.concatenate((baseline_result["DC"].magnitude, chase_result["DC"].magnitude))
    
    Out_array = np.concatenate((EPSC0NormOut,   \
                PPR_out[:,np.newaxis],          \
                Rin_out[:,np.newaxis],          \
                Rs_out[:, np.newaxis],          \
                DC_out[:, np.newaxis]), axis=1)
    
    pio.writeCsv(Out_array, "%s_%s" % (basename, "result"), header=header)
        
    ret = dict()
    
    ret["%s_%s" % (basename, "baseline_result")]            = baseline_result
    ret["%s_%s" % (basename, "chase_result")]               = chase_result
    ret["%s_%s" % (basename, "baseline_EPSC0_mean")]        = meanEPSC0baseline
    ret["%s_%s" % (basename, "baseline_EPSC0_normalized")]  = baseEPSC0Norm
    ret["%s_%s" % (basename, "chase_EPSC0_normalized")]     = chaseEPSC0Norm
    
    return ret

    
def LTP_analysis(mean_average_dict, LTPOptions, results_basename=None, normalize=False):
    """
    Arguments:
    ==========
    mean_average_dict = dictionary (see generate_minute_average_data_for_LTP)
    result_basename = common prefix for result variables
    LTPoptions    = dictionary (see generate_LTP_options()); optional, default 
        is None, expecting that mean_average_dict contains an "LTPOptions"key.
        
    Returns:
    
    ret_test, ret_control - two dictionaries with results for test and control (as calculated by analyzeLTPPathway)
    
    NOTE 1: The segments in the blocks inside mean_average_dict must have already been assigned epochs from cursors!
    NOTE 2: The "Test" and "Control" dictionaries in mean_average_dict must contain a field "Path" with the actual path index
    """
    
    if results_basename is None:
        if "name" in mean_average_dict:
            results_basename = mean_average_dict["name"]
            
        else:
            warnings.warn("LTP Data dictionary lacks a 'name' field and a result basename has not been supplied; results will get a default generic name")
            results_basename = "Minute_averaged_LTP_Data"
            
    elif not isinstance(results_basename, str):
        raise TypeError("results_basename parameter must be a str or None; for %s instead" % type(results_basename).__name__)
    
    ret_test = analyzeLTPPathway(mean_average_dict["Test"]["Baseline"],
                                 mean_average_dict["Test"]["Chase"], 0, 1, 
                                 mean_average_dict["Test"]["Path"], 
                                 basename=results_basename+"_test", 
                                 pathType="Test", 
                                 normalize=normalize)
    
    ret_control = analyzeLTPPathway(mean_average_dict["Control"]["Baseline"], mean_average_dict["Control"]["Chase"], 0, 1, mean_average_dict["Control"]["Path"], \
                                basename=results_basename+"_control", pathType="Control", normalize=normalize)
    
    return (ret_test, ret_control)


#"def" plotAverageLTPPathways(data, state, viewer0, viewer1, keepCursors=True, **kwargs):
def plotAverageLTPPathways(data, state, viewer0=None, viewer1=None, keepCursors=True, **kwargs):
    """Plots averaged LTP pathway data in two SignalViewer windows
    
    Arguments:
    =========
    
    data = a dict as returned by generate_minute_average_data_for_LTP()
    
    state: str, one of "baseline" or "chase"
    
    viewer0, viewer1: SignalViewer objects to show respectively, pathway 0 and 1
        These default to None, in which case two new SignalViewer windows will be created.
    
    keepCursors (boolean, optional, default True) 
        when False, a new set of LTP cursors will be created in both viewers, 
        replacing any existing cursors; 
        
        when True, previous cursors (if any) will be left in place; if thre are 
            no cursors, then new cursors will be added to the viewer window
            
            
    Keyword arguments:
    =================
    passed on to SignalViewer.plot() function (e.g. signal=...)
    
    """
    # NOTE: this should have been "injected" at module level by by PictMainWinow at __init__()
    # FIXME find out a more elegant way
    global appWindow 
    
    if not isinstance(data, dict):
        raise TypeError("Expecting a dict, got %s instead" % type(data).__name__)
    
    if not isinstance(state, str):
        raise TypeError("State is expected to be a str, got %s instead" % type(state).__name__)
    
    if state not in ("baseline", "Baseline", "base", "Base", "chase", "Chase"):
        raise ValueError("State is expected to be one of 'baseline' or 'chase'; got %s instead" % state)
    
    if state.lower() in ("baseline", "base"):
        state = "Baseline"
        
    else:
        state="Chase"
        
    if isinstance(viewer0, (tuple, list)) and len(viewer0) == 2 and all([isinstance(v, sv.SignalViewer) for v in viewer0]):
        viewer1 = viewer0[1]
        viewer0 = viewer0[0]
        
    else:
        if viewer0 is None:
            if appWindow is not None:
                viewer0 = appWindow.newSignalViewerWindow()
            else:
                raise TypeError("A SignalViewer must be specified for viewer0")
            
        if viewer1 is None:
            if appWindow is not None:
                viewer1 = appWindow.newSignalViewerWindow()
            else:
                raise TypeError("A SignalViewer must be specified for viewer1")
            
    if data["Test"]["Path"] == 0:
        viewer0.plot(data["Test"][state], **kwargs)
        viewer1.plot(data["Control"][state], **kwargs)
        
    else:
        viewer0.plot(data["Control"][state], **kwargs)
        viewer1.plot(data["Test"][state], **kwargs)

    if len(viewer0.verticalCursors) == 0 or not keepCursors:
        viewer0.currentAxes = 0
        setupLTPCursors(viewer0, data["LTPOptions"], 0)
        
    if len(viewer1.verticalCursors) == 0 or not keepCursors:
        viewer1.currentAxes = 0
        setupLTPCursors(viewer1, data["LTPOptions"], 1)
    
def setupLTPCursors(viewer, LTPOptions, pathway, axis=None):
    """ Convenience function for setting up cursors for LTP experiments:
    
    Arguments:
    ==========
    
    LTPOptions: a dict with the following mandatory key/value pairs:
    
        {'Average': {'Count': 6, 'Every': 6},

        'Cursors': 
            {'Labels':  ['Rbase',
                        'Rs',
                        'Rin',
                        'EPSC0base',
                        'EPSC0Peak',
                        'EPSC1base',
                        'EPSC1peak'],

            'Pathway0': [0.06,
                        0.06579859882206893,
                        0.16,
                        0.26,
                        0.273,
                        0.31,
                        0.32334583993039734],

            'Pathway1': [5.06,
                        5.065798598822069,
                        5.16,
                        5.26,
                        5.273,
                        5.31,
                        5.323345839930397],

            'Windows': [0.01, 0.003, 0.01, 0.01, 0.005, 0.01, 0.005]},

        'Pathway0': 0,

        'Pathway1': 1,

        'Reference': 5,

        'Signals': ['Im_prim_1', 'Vm_sec_1']}
        
    pathway: int = the pathway for which the cursors are shown: can be 0 or 1
    
    axis: optional default None: an int index into the axis receiving the cursors
        (when None, the fist axis i.e. at index 0, is chosen)
    """
    
    if not isinstance(viewer, sv.SignalViewer):
        raise TypeError("The parameter 'viewer' was expected to be a SignalViewer; got %s instead" % type(viewer).__name__)
    
    if axis is not None:
        if isinstance(axis, int):
            if axis < 0 or axis >= len(viewer.axesWithLayoutPositions):
                raise ValueError("When specified, axis must be an integer between 0 and %d" % len(viewer.axesWithLayoutPositions))
            
            viewer.currentAxes = axis
            
        else:
            raise ValueError("When specified, axis must be an integer between 0 and %d" % len(viewer.axesWithLayoutPositions))
        
    
    viewer.setupCursors("v", LTPOptions["Cursors"]["Pathway%d"%pathway])
        
def extract_sample_EPSPs(data, 
                         test_base_segments_ndx, 
                         test_chase_segments_ndx, 
                         control_base_segments_ndx, 
                         control_chase_segments_ndx,
                         t0, t1):
    """
    data: dict; an LTP data dict
    
    test_base_segments_ndx,
    test_chase_segments_ndx,
    control_base_segments_ndx, 
    control_chase_segments_ndx: indices of segments ot average in the corresponding path & state

    t0: Python Quantity in time units: start of time interval in the signal
    t1: Python Quantity in time units: end of the time interval
    
    Both t0 and t1 must be relative to 0
    
    Returns a neo.Segment
    
    """
    if not isinstance(data, dict):
        raise TypeError("Expecting a dict, got %s instead" % type(data).__name__)

    
    if not isinstance(test_base_segments_ndx, (tuple, list, range)):
        raise TypeError("test_base_segments_ndx expected a sequence or range; got %s instead" % type(test_base_segments_ndx).__name__)
    
    if isinstance(test_base_segments_ndx, (tuple, list)):
        if not all([isinstance(v, int) for v in test_base_segments_ndx]):
            raise TypeError("when a sequence, test_base_segments_ndx musy contain only integers")
        
        
    if not isinstance(test_chase_segments_ndx, (tuple, list, range)):
        raise TypeError("test_chase_segments_ndx expected a sequence or range; got %s instead" % type(test_chase_segments_ndx).__name__)
    
    if isinstance(test_chase_segments_ndx, (tuple, list)):
        if not all([isinstance(v, int) for v in test_chase_segments_ndx]):
            raise TypeError("when a sequence, test_chase_segments_ndx musy contain only integers")
        
        
    if not isinstance(control_base_segments_ndx, (tuple, list, range)):
        raise TypeError("control_base_segments_ndx expected a sequence or range; got %s instead" % type(control_base_segments_ndx).__name__)
    
    if isinstance(control_base_segments_ndx, (tuple, list)):
        if not all([isinstance(v, int) for v in control_base_segments_ndx]):
            raise TypeError("when a sequence, control_base_segments_ndx musy contain only integers")
        
        
    if not isinstance(control_chase_segments_ndx, (tuple, list, range)):
        raise TypeError("control_chase_segments_ndx expected a sequence or range; got %s instead" % type(control_chase_segments_ndx).__name__)
    
    if isinstance(control_chase_segments_ndx, (tuple, list)):
        if not all([isinstance(v, int) for v in control_chase_segments_ndx]):
            raise TypeError("when a sequence, control_chase_segments_ndx musy contain only integers")
        
        
        
    average_test_base = neoutils.set_relative_time_start(neoutils.average_segments([data["Test"]["Baseline"].segments[ndx] for ndx in test_base_segments_ndx], 
                                                        signal_index = data["LTPOptions"]["Signals"][0])[0])

    test_base = neoutils.set_relative_time_start(neoutils.get_time_slice(average_test_base, t0, t1))
    
    average_test_chase = neoutils.set_relative_time_start(neoutils.average_segments([data["Test"]["Chase"].segments[ndx] for ndx in test_chase_segments_ndx],
                                          signal_index = data["LTPOptions"]["Signals"][0])[0])
    
    test_chase = neoutils.set_relative_time_start(neoutils.get_time_slice(average_test_chase, t0, t1))
    
    control_base_average = neoutils.set_relative_time_start(neoutils.average_segments([data["Control"]["Baseline"].segments[ndx] for ndx in control_base_segments_ndx],
                                                            signal_index = data["LTPOptions"]["Signals"][0])[0])
    
    control_base = neoutils.set_relative_time_start(neoutils.get_time_slice(control_base_average, t0, t1))
    
    control_chase_average = neoutils.set_relative_time_start(neoutils.average_segments([data["Control"]["Chase"].segments[ndx] for ndx in control_chase_segments_ndx],
                                          signal_index = data["LTPOptions"]["Signals"][0])[0])
    
    control_chase = neoutils.set_relative_time_start(neoutils.get_time_slice(control_chase_average, t0, t1))
    
    
    result = neo.Block(name = "%s_sample_traces" % data["name"])
    
    
    # correct for baseline
    
    #print(test_base.analogsignals[0].t_start)
    
    test_base.analogsignals[0] -= np.mean(test_base.analogsignals[0].time_slice(0.0002 * pq.s, 0.002 * pq.s))
    test_chase.analogsignals[0] -= np.mean(test_chase.analogsignals[0].time_slice(0.0002 * pq.s, 0.002 * pq.s))
    
    control_base.analogsignals[0] -= np.mean(control_base.analogsignals[0].time_slice(0.0002 * pq.s, 0.002 * pq.s))
    control_chase.analogsignals[0] -= np.mean(control_chase.analogsignals[0].time_slice(0.0002 * pq.s, 0.002 * pq.s))
    
    test_traces = neoutils.concatenate_signals(test_base.analogsignals[0], test_chase.analogsignals[0], axis=1)
    test_traces.name = "Test"
    
    control_traces = neoutils.concatenate_signals(control_base.analogsignals[0], control_chase.analogsignals[0], axis=1)
    control_traces.name= "Control"
    
    result_segment = neo.Segment()
    result_segment.analogsignals.append(test_traces)
    result_segment.analogsignals.append(control_traces)
    
    result.segments.append(result_segment)
    
    return result


    
    
