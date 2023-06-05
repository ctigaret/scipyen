"""GUI for synaptic plasticity experiments
"""

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
import core.workspacefunctions as wf
import core.signalprocessing as sigp
import core.curvefitting as crvf
import core.datatypes as dt
from core.datatypes import TypeEnum
from core.quantities import units_convertible
import plots.plots as plots
import core.models as models
import core.neoutils as neoutils
import core.triggerprotocols as tp
from core.triggerevent import (TriggerEvent, TriggerEventType,)

#from core.patchneo import neo
from core.utilities import safeWrapper, reverse_mapping_lookup
#### END pict.core modules

#### BEGIN pict.gui modules
import gui.signalviewer as sv
import gui.textviewer as tv
import gui.tableeditor as te
import gui.matrixviewer as matview
import gui.pictgui as pgui
from gui.itemslistdialog import ItemsListDialog
import gui.quickdialog as quickdialog
import gui.scipyenviewer as scipyenviewer
from gui.scipyenviewer import ScipyenViewer, ScipyenFrameViewer
#### END pict.gui modules

#### BEGIN pict.iolib modules
import iolib.pictio as pio
#### END pict.iolib modules

import ephys.ephys as ephys
from ephys.ephys import ClampMode, ElectrodeMode
import ephys.ltp as ltp
from ephys.ltp import PathwayType, SynapticPathway

__module_path__ = os.path.abspath(os.path.dirname(__file__))

__UI_LTPWindow__, __QMainWindow__ = __loadUiType__(os.path.join(__module_path__,"LTPWindow.ui"), 
                                                   from_imports=True, 
                                                   import_from="gui") #  so that resources can be imported too

class LTPWindow(ScipyenFrameViewer, __UI_LTPWindow__):
    def __init__(self, data=None, win_title:str = "Synaptic plasticity", parent:typing.Optional[QtWidgets.QMainWindow]=None, **kwargs):
        
        self.qsettings = QtCore.QSettings()
        self.threadpool = QtCore.QThreadPool()
        
        super().__init__(data=data, win_title = win_title, doc_title="", parent=parent)
        
        self._data_ = dict()
        self._data_["Baseline"] = dict()
        self._data_["Baseline"]["Test"] = None
        self._data_["Baseline"]["Control"] = None
        self._data_["Chase"] = dict()
        self._data_["Chase"]["Test"] = None
        self._data_["Chase"]["Control"] = None
        
        self._synaptic_pathways_ = dict() # contains SynapticPathway objects
        
        # NOTE: 2020-02-23 11:10:20
        # During conditioning the "Control" synaptic pathway is unperturbed but
        # it is possible to stimulate additional synaptic pathways for other
        # purposes: 
        # for NST+SWR experiments, a separate synaptic pathway is used to
        # simulated sharp wave/ripple events
        # during cooperative LTP experiments, an additional "strong" pathway is 
        # stimulated concomitently with the "Test" (or "weak") pathway so that
        # LTP is induced in the weak pathway - without the strong pathway 
        # stimulation there would be no LTP on the weak ("Test") pathway.
        self._data_["Conditioning"] = dict()
        self._data_["Conditioning"]["Test"] = None
        
        self._viewers_ = dict()
        self._plotWindows_ = dict()
#         self._viewers_["baseline_source"] = None
#         self._viewers_["conditioning_source"] = None
#         self._viewers_["chase_source"] = None
#         
#         # NOTE: 2023-05-11 18:10:06
#         # str (pathway name) ↦ int (pathway index)
#         self._viewers_["pathways"] = dict()
        
        # NOTE: 2023-05-11 11:00:47 recording configuration
        # electrode mode see ephys.ElectrodeMode; one of:
        # • ephys.ElectrodeMode.WholeCellPatch (default)
        # • ephys.ElectrodeMode.Field
        # • ephys.ElectrodeMode.Sharp
        # clamp mode: one for tracking (i.e. baseline + chase) and one for induction
        # NOTE: normally baseline and chase have both the same clamping mode unless
        # you need to so something extremely unorthodox
        # By default, these are:
        # • tracking = ClampMode.VoltageClamp
        # • induction = ClampMode.CurrentClamp
        #
        # • possible values are 
        #   ∘ ClampMode.NoClamp ↦ For Multiclamp series using MultiClamp commander,
        #                          this is achieved by turning OFF Holding in either
        #                           clamp modes (VC, IC) or by using IC=0 mode
        #                         For other amplifiers, see the appropriate manuals.
        #
        #                         Typically, this is used in field recordings.
        #
        #
        #   ∘ ClampMode.VoltageClamp, 
        #   ∘ ClampMode.CurrentClamp ↦ any patch mode, and sharp electrodes.
        self._recording_configuration_ = dict()
        self._recording_configuration_["ElectrodeMode"] = ElectrodeMode.WholeCellPatch
        self._recording_configuration_["ClampMode"] = dict()
        self._recording_configuration_["ClampMode"]["tracking"] = ClampMode.VoltageClamp
        self._recording_configuration_["ClampMode"]["induction"] = ClampMode.CurrentClamp
        
        
        # NOTE: 2023-05-11 18:14:08
        # str (analog signal name) ↦ int (signal index)
        # Since there can be multiple stimulation pathways (e.g. Test & Control,
        # or Test & Control & Ripple) we need a list of these for each pathway
        # we need
        self._input_signals_ = dict()
        
        # NOTE: 2023-05-11 18:17:55 self._synaptic_signal_
        # name or index of the input analogsignal that carries the synaptic 
        # response - 
        # ATTENTION: this signal MUST be present in self._input_signals_ and
        # can be:
        # • a current signal - units pA (usually) or nA
        #       if ElectrodeMode is WholeCellPatch AND tracking ClampMode is VoltageClamp)
        #
        # • a voltage signal - units of mV 
        #       if any of the following is satisfied:
        #           ∘ ElectrodeMode is WholeCellPatch and ClampMode is CurrentClamp
        #           ∘ ElectrodeMode is Field ( ClampMode may be NoClamp or CurrentClamp)
        #           ∘ ElectrodeMode is Sharp and ClampMode is CurrentClamp
        #
        # This relies on the signal having appropriate units. In turn, this requires
        # a Telegraph input from the amplitifer to the DAQ board; failing that,
        # the units should be set up correctly in the recording software (either
        # as part of the protocol, or in software configuration)
        #
        # As a last resort, the units can be set up manually in this GUI (TODO)
        self._synaptic_signal_ = dict()
        self._synaptic_signal_["tracking"] = None
        self._synaptic_signal_["induction"] = None
        
        # NOTE: 2023-05-11 21:35:06 self._command_signal_as_input_
        # stores the signal names of the command signals RECORDED AS AUXILIARY
        # INPUTS IN THE PROTOCOL
        #
        # this approach is recommended until we can successfully parse the ABF
        # protocols
        #
        # NOTE: these may be None!
        #
        # The names of these signals MUST be found among the keys of self._input_signals_
        #
        # This signal can be (with appropriate units, see e.g., NOTE: 2023-05-11 18:17:55):
        # • a voltage signal:   in ElectrodeMode WholeCellPatch and ClampMode VoltageClamp
        # • a current signal:   in (ElectrodeMode.WholeCellPatch or ElectrodeMode.Sharp) and Clampmode.CurrentClamp
        # • None:               in ElectrodeMode.Field or ClampMode NoClamp
        self._command_signal_as_input_ = dict()
        self._command_signal_as_input_["tracking"] = None
        self._command_signal_as_input_["induction"] = None
        
        # NOTE:2023-05-12 10:55:03 self._digital_signal_as_input_ 
        # stored the names of the digital stimuli AS RECORDED THROUGH AUXILIARY
        # INPUTS
        #
        # As for self._command_signal_as_input_, this approach is recommended
        # until I can succesfully parse the digital waveforms from the ABF protocol
        #
        # Until then, this signal is useful to determine the timing of the 
        # presynaptic stimulations.
        #
        # Also, since there typically are two pathways (rarely one, exceptionally
        # more than one), we need to have dictionary for each pathway
        self._digital_signal_as_input_ = dict()
        self._digital_signal_as_input_["tracking"] = None
        
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
        
        self._reportWindow_ = te.TableEditor(win_title="Synaptic Plasticity Results", parent=self)
        self._reportWindow_.setVisible(False)
        
    def _configureUI_(self):
        self.setupUi(self)
        
        self.actionOpenExperimentFile.triggered.connect(self.slot_openExperimentFile)
        self.actionOpenBaselineSourceFiles.triggered.connect(self.slot_openBaselineSourceFiles)
        self.actionOpenChaseSourceFiles.triggered.connect(self.slot_openChaseSourceFiles)
        self.actionOpenConditioningSourceFiles.triggered.connect(self.slot_openConditioningSourceFiles)
        self.actionOpenPathwayCrosstalkSourceFiles.triggered.connect(self.slot_openPathwaysXTalkSourceFiles)
        
        #self.dataIsMinuteAvegaredCheckBox.stateChanged[int].connect(self._slot_averaged_checkbox_state_changed_)
        
        self.actionOpenOptions.triggered.connect(self.slot_openOptionsFile)
        self.actionImportOptions.triggered.connect(self.slot_importOptions)
        
        self.actionSaveOptions.triggered.connect(self.slot_saveOptionsFile)
        self.actionExportOptions.triggered.connect(self.slot_exportOptions)
        
        self.pushButtonBaselineSources.clicked.connect(self.slot_viewBaselineSourceData)
        
    def _setupViewers_(self):
        for synapticPathway in self._synaptic_pathways_:
            self._setupViewerForPathway(synapticPathway)
        
    def _setupViewerForPathway(self, pathway:SynapticPathway):
        viewerTitle = f"{self._winTitle_}: {pathway.name} ({pathway.pathwayType})"
        viewerConfigTag = f"PathwayViewer_{pathway.pathwayType}_{pathway.name}"
        self._viewers_[pathway.name] = sv.SignalViewer(win_title = viewerTitle, 
                                                                parent=self, 
                                                                configTag = viewerConfigTag)
        
        self._viewers_[pathway.name]._sig_closeMe.connect(self._slot_ephysViewer_closed)
        self._viewers_[pathway.name]._sig_newEpochInData.connect(self._slot_newEpochGenerated)
        
        self._viewers_[pathway.name]._sig_axisActivated.connect(self._slot_newSignalViewerAxisSelected)
        
        self.linkToViewers(self._viewers_[pathway.name])
        
    @pyqtSlot(int)
    def _slot_newSignalViewerAxisSelected(self, index:int):
        pass
    
    @pyqtSlot()
    def _slot_newEpochGenerated(self):
        pass
    
    @pyqtSlot(int)
    def _slot_ephysViewer_closed(self):
        viewer = self.sender()
        viewerKey = [k for k, v in self._viewers_.items() if v == viewer]
        if len(viewerKey):
            key = viewerKey[0]
            self.unlinkFromViewers(viewer)
            self._viewers_.pop(key, None)
        
        
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
            choiceDialog = ItemsListDialog(parent=self, title="Select Baseline Trial", itemsList = nameList)
            
            ans = choiceDialog.exec()
            
            if ans == QtWidgets.QDialog.Accepted and len(choiceDialog.selectedItemsText):
                data_index = nameList.index(choiceDialog.selectedItemsText[0])
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
            choiceDialog = ItemsListDialog(parent=self, title="Select Baseline Trial", itemsList = nameList)
            
            ans = choiceDialog.exec()
            
            if ans == QtWidgets.QDialog.Accepted and len(choiceDialog.selectedItemsText):
                data_index = nameList.index(choiceDialog.selectedItemsText[0])
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
            choiceDialog = ItemsListDialog(parent=self, title="Select Baseline Trial", itemsList = nameList)
            
            ans = choiceDialog.exec()
            
            if ans == QtWidgets.QDialog.Accepted and len(choiceDialog.selectedItemsText):
                data_index = nameList.index(choiceDialog.selectedItemsText[0])
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
            choiceDialog = ItemsListDialog(parent=self, title="Select Baseline Trial", itemsList = nameList)
            
            ans = choiceDialog.exec()
            
            if ans == QtWidgets.QDialog.Accepted and len(choiceDialog.selectedItemsText):
                data_index = nameList.index(choiceDialog.selectedItemsText[0])
                data = self._path_xtalk_source_data_[data_index]


        if isinstance(data, neo.Block):
            viewer.view(data)
            
            
    #@pyqtSlot(int)
    #@safeWrapper
    #def _slot_averaged_checkbox_state_changed_(self, val):
        #checked = val == QtCore.Qt.Checked
        
        #self.sweepAverageGroupBox.setEnabled(not checked)
    
    def closeEvent(self, evt):
        viewerKeys = [k for k in self._viewers_.keys()]
        
        for k in viewerKeys:
            self._viewers_[k].clear()
            self._viewers_[k].close()
            self._viewers_[k] = None
            self._viewers_.pop(k, None)
        
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
        
        inter_trial_interval = protocol["fTrialStartToStart"] * pq.s
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
        data structure -- see core.ephys module.
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
    
            

