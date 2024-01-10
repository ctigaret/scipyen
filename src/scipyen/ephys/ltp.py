# -*- coding: utf-8 -*-

#### BEGIN core python modules
import os, sys, traceback, inspect, numbers, warnings, pathlib, time
import functools, itertools
import collections, enum
import typing, types
import dataclasses
import subprocess
from dataclasses import (dataclass, KW_ONLY, MISSING, field)

#### END core python modules

#### BEGIN 3rd party modules
import numpy as np
import pandas as pd
import quantities as pq
# from quantities.decorators import with_doc
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
from core.workspacefunctions import (user_workspace, validate_varname, get_symbol_in_namespace, assignin)
import core.signalprocessing as sigp
import core.curvefitting as crvf
import core.pyabfbridge as pab
import core.datatypes  
from core.datatypes import (Episode, Schedule, TypeEnum)
import plots.plots as plots
import core.models as models
import core.neoutils as neoutils
from core.neoutils import (clear_events, get_index_of_named_signal, is_empty, 
                           concatenate_blocks, concatenate_signals,
                           average_segments)

from core.sysutils import adapt_ui_path

import core.triggerprotocols as tp
from core.triggerprotocols import (TriggerProtocol,
                                   embed_trigger_protocol, 
                                   embed_trigger_event,
                                   parse_trigger_protocols,
                                   remove_trigger_protocol,)

from core.triggerevent import (DataMark, TriggerEvent, TriggerEventType,)
from core.datasignal import (DataSignal, IrregularlySampledDataSignal)
from core.datazone import DataZone

from core import (prog, traitcontainers, strutils, neoutils, models,)
from core.prog import (safeWrapper, AttributeAdapter, with_doc)
from core.basescipyen import BaseScipyenData
from core.traitcontainers import DataBag
from core import quantities as cq
from core.quantities import(arbitrary_unit, 
                            pixel_unit, 
                            channel_unit,
                            space_frequency_unit,
                            angle_frequency_unit,
                            day_in_vitro,
                            week_in_vitro, postnatal_day, postnatal_month,
                            embryonic_day, embryonic_week, embryonic_month,
                            unit_quantity_from_name_or_symbol,
                            check_time_units,
                            units_convertible)

from core.utilities import (safeWrapper, 
                            reverse_mapping_lookup, 
                            get_index_for_seq, 
                            sp_set_loc,
                            normalized_index,
                            unique,
                            duplicates,
                            GeneralIndexType)

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
from gui.cursors import SignalCursor
from gui.workspacegui import (DirectoryFileWatcher, FileStatChecker)
#### END pict.gui modules

#### BEGIN pict.iolib modules
import iolib.pictio as pio
#### END pict.iolib modules

import ephys.ephys as ephys
from ephys.ephys import (ClampMode, ElectrodeMode, LocationMeasure, 
                         Source, SynapticStimulus, 
                         AuxiliaryInput, AuxiliaryOutput,
                         synstim, auxinput, auxoutput)
import ephys.membrane as membrane


LTPOptionsFile = os.path.join(os.path.dirname(__file__), "options", "LTPOptions.pkl")
optionsDir     = os.path.join(os.path.dirname(__file__), "options")

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__ui_path__ = adapt_ui_path(__module_path__,"LTPWindow.ui")
    

#__UI_LTPWindow__, __QMainWindow__ = __loadUiType__(os.path.join(__module_path__,"LTPWindow.ui"))
# __UI_LTPWindow__, __QMainWindow__ = __loadUiType__(os.path.join(__module_path__,"LTPWindow.ui"), 
# __UI_LTPWindow__, __QMainWindow__ = __loadUiType__(os.path.join(__ui_path__,"LTPWindow.ui"), 
__UI_LTPWindow__, __QMainWindow__ = __loadUiType__(__ui_path__, 
                                                   from_imports=True, 
                                                   import_from="gui") #  so that resources can be imported too

def twoPathwaysSource(adc:int=0, dac:typing.Optional[typing.Union[int,str]]=None,
                      path0:int=0, path1:int=1, name:str="cell", 
                      **kwargs):
    """Factory for a data source in two-pathways synaptic plasticity experiments.
    
    Synaptic stimulation is carried out via extracellular electrodes using
    simulus devices driven by TTLs via DIG channels.

    By default DIG channel indices are 0 and 1, but they can be specified using 
    the 'path0' and 'path1' parameters.
    
    By default, the 'dac' parameter is None, indicating a recording from an 
    𝑢𝑛𝑐𝑙𝑎𝑚𝑝𝑒𝑑 Source (e.g. a field recording, or recording from an unclamped cell).
    
    When 'dac' parameter is specified as an int (index) or str (name), the 
    source is considered to be recorded in 𝑐𝑙𝑎𝑚𝑝𝑖𝑛𝑔 mode (i.e. voltage- or 
    current-clamp), and, by implication, the Source is a cell or a membrane 
    patch.
    
    Synaptic responses are recorded on ADC 0 by default, but this can be specified
    using the 'adc' parameter as an int (index) or str (name).
    
    By default the source 'name' field is "cell"¹ but this can be specified using
    the 'name' parameter as a str.
    
    Sources with more complex configurations (e.g. using photostimulation of 
    synaptic activity triggered with DAC-emulated TTLs) should be constructed
    directly (see ephys.Source documentation for details).
    
    Named parameters:
    -----------------
    adc, dac, name: See ephys.ephys.Source constructor for a full description.
    path0, path1 (int) >= 0 indices of DIG channels used to stimulate the pathways.
    
    
    Here, the default parameter values associate 'adc' 0 with 'dac' 0 and two 
    SynapticStimulus objects, using 'dig' 0 and 'dig' 1, respectively.
    
    Var-keyword parameters:
    --------------------------
    These are 'out' and 'aux' and here are given the default values of 'None'.
    
    In a given application, the 'name' field of Source objects should have unique
    values in order to allow the lookup of these objects according to this field.
    
    Returns:
    --------
    An immutable ephys.ephys.Source object (a NamedTuple). 

    One can create a modified version using the '_replace' method:
    (WARNING: Remember to also change the value of the Source's 'name' field)
    
    
    cell  = twoPathwaysSource()
    cell1 = twoPathwaysSource(dac=1, name="cell1")
    cell2 = cell._replace(dac=1,   name="cell1")
    
    assert cell1 == cell2, "The objects are different"
    
    ¹ It is illegal to use Python keywords as name here.
    
    """
    syn     = (SynapticStimulus('path0', path0), SynapticStimulus('path1', path1)) 
    out     = kwargs.pop("out", None)
    aux     = kwargs.pop("aux", None)
    
    if aux is not None:
        if (isinstance(aux, (list, tuple)) and not all(isinstance(v, AuxiliaryInput) for v in aux)) or not isinstance(aux, AuxiliaryInput):
            raise TypeError(f"'aux' expected to be an AuxiliaryInput or a sequence of AuxiliaryInput, or None")

    return Source(name, adc, dac, syn, aux, out)

class _LTPFilesSimulator_(QtCore.QThread):
    """
    Used for testing LTPOnline on already recorded files
    """
    supplyFile = pyqtSignal(pathlib.Path, name = "supplyFile")
    
    defaultTimeout = 10000 # ms
    
    def __init__(self, parent, simulation:dict = None):
        super().__init__(parent=parent)
        
        # print(f"Simulating a supply of ABF (Axon) binary data files")
        
        self._simulatedFile_ = None
        self._simulationCounter_ = 0
        self._simulationFiles_ = []
        self._simulationTimeOut_ = self.defaultTimeout
        
        files = None
        
        if isinstance(simulation, dict):
            self._simulationTimeOut_ = simulation.get("timeout",self.defaultTimeout )
            
            files = simulation.get("files", None)
            
            if not isinstance(files, (list, tuple)) or len(files) == 0 or not all(isinstance(v, (str, pathlib.Path)) for v in files):
                files = None
            
        if files is None:
            print(f"Looking for ABF files in current directory ({os.getcwd()}) ...")
            files = subprocess.run(["ls"], capture_output=True).stdout.decode().split("\n")
            print(f"Found {len(files)} ABF files")
        
        if isinstance(files, list) and len(files) > 0 and all(isinstance(v, (str, pathlib.Path)) for v in files):
            simFilesPaths = list(filter(lambda x: x.is_file() and x.suffix == ".abf", [pathlib.Path(v) for v in files]))
            
            if len(simFilesPaths):
                # NOTE: 2024-01-08 17:45:21
                # bound to introduce some delay, but needs must, for simulation purposes
                print("Sorting ABF data based on recording time ...")
                self._simulationFiles_ = sorted(simFilesPaths, key = lambda x: pio.loadAxonFile(x).rec_datetime)
                print("... done.")
                
        if len(self._simulationFiles_) == 0:
            print(f"No Axon binary files (ABF) were supplied, and no ABFs were found in current directory ({os.getcwd()})")
                
    def run(self):
        self._simulationCounter_ = 0
        for k,f in enumerate(self._simulationFiles_):
            print(f"{k}ᵗʰ file: {f}\n")
            self.simulateFile()
            QtCore.QThread.sleep(int(self._simulationTimeOut_/1000)) # seconds!
            if self.isInterruptionRequested():
                break
            
    @pyqtSlot()
    def simulateFile(self):
        if self._simulationCounter_ >= len(self._simulationFiles_):
            self.stop()
            return
        
        self._simulatedFile_ = self._simulationFiles_[self._simulationCounter_]
        self._simulationCounter_ += 1
        
        self.supplyFile.emit(self._simulatedFile_)
        
        
class _LTPOnlineSupplier_(QtCore.QThread):
    abfRunReady = pyqtSignal(pathlib.Path, name="abfRunReady")
    stopTimer = pyqtSignal(name="stopTimer")
    
    def __init__(self, parent: QtCore.QObject,
                 abfRunBuffer: collections.deque, 
                 emitterWindow: QtCore.QObject,
                 directory: pathlib.Path,
                 simulator: typing.Optional[_LTPFilesSimulator_] = None):
        """
        """
        QtCore.QThread.__init__(self, parent)
        self._abfRunBuffer_ = abfRunBuffer
        self._filesQueue_ = collections.deque()
        self._pending_ = dict() # pathlib.Path are hashable; hence we use the RSV ↦ ABF

        self._simulator_ = simulator
        
        wsp = wf.user_workspace()
        
        if emitterWindow is None:
            self._emitterWindow_ = wsp["mainWindow"]

        elif type(emitterWindow).__name__ != 'ScipyenWindow':
            raise ValueError(f"Expecting an instance of ScipyenWindow; instead, got {type(emitterWindow).__name__}")

        else:
            self._emitterWindow_ = emitterWindow

        if directory is None:
            self._watchedDir_ = pathlib.Path(self._emitterWindow_.currentDir).absolute()
            
        elif isinstance(directory, str):
            self._watchedDir_ = pathlib.Path(directory)

        elif isinstance(directory, pathlib.Path):
            self._watchedDir_ = directory
            
        else:
            raise TypeError(f"'directory' expected to be a str, a pathlib.Path, or None; instead, got {type(directory).__name__}")
        
        if isinstance(self._simulator_, _LTPFilesSimulator_):
            self._simulator_.supplyFile.connect(self._simulateFile_)
            
        # watches for changes (additions and removals of files) in the monitored
        # directory
        self._dirMonitor_ = DirectoryFileWatcher(emitter = self._emitterWindow_,
                                                directory = self._watchedDir_,
                                                observer = self)
        
        self._abfListener_ = FileStatChecker(interval = 10, maxUnchangedIntervals = 5,
                                            callback = self.supplyFile)
        

    def newFiles(self, val:typing.Union[typing.Sequence[pathlib.Path]]):
        """Callback needed by DirectoryFileWatcher"""
        # print(f"{self.__class__.__name__}.newFiles {[v.name for v in val]}\n")
        self._filesQueue_.extend(val)
        self._setupPendingAbf_()

        # print(f"\t→ pending: {self._pending_}\n")
        # self._a_ += 1

    def changedFiles(self, val:typing.Union[typing.Sequence[pathlib.Path]]):
        """Callback needed by DirectoryFileWatcher"""
        # print(f"{self.__class__.__name__}.changedFiles {[v.name for v in val]}\n")
        # print(f"\t→ latestAbf = {self._latestAbf_}\n")
        # self._a_ += 1
        pass
        
    def removedFiles(self, val:typing.Union[typing.Sequence[pathlib.Path]]):
        """Callback needed by DirectoryFileWatcher"""
        # print(f"{self.__class__.__name__}.removedFiles {[v.name for v in val]}\n")
        # self._a_ += 1
        if not all(isinstance(v, pathlib.Path) and v.parent == self._watchedDir_ and v.suffix in (".rsv", ".abf") for v in val):
            return

        # if len(val) > 1:
        #     # CAUTION!
        #     return

        removed = val[0]

        # expecting the rsv file to be removed by Clampex;
        # when this is done, watch the pending ABF file for changes
        # print(f"\t→ pending = {self._pending_}\n")
        if removed.suffix == ".rsv":
            if removed in self._pending_:
                self._latestAbf_ = self._pending_[removed]
                if self._abfListener_.active:
                    self._abfListener_.stop()
                if  not self._latestAbf_.exists() or not self._latestAbf_.is_file():
                    self._latestAbf_ = None
                    self._pending_.clear()
                    self._filesQueue_.clear()
                    return
                self._abfListener_.monitoredFile = self._latestAbf_
                self._abfListener_.start()
                # print(f"\t\t→ latest = {self._latestAbf_}\n")
                self._pending_.clear()
                # NOTE: to stop monitoring abf file after it has been processed
                # in the processAbfFile(…)
                
    def filesChanged(self, filePaths:typing.Sequence[str]):
        """
        Used in communicating with the directory monitor
        """
        # print(f"{self.__class__.__name__}.filesChanged {filePaths}\n")
        for f in filePaths:
            fp = pathlib.Path(f)
            stat = fp.stat()
            # print(f"\t → {fp.name}: {stat.st_size}, {stat.st_atime_ns, stat.st_mtime_ns, stat.st_ctime_ns}")
        # self._a_ += 1
        
    def _rsvForABF_(self, abf:pathlib.Path):
        """Returns the rsv file paired with the abf
        Used in communicating with the directory monitor
        """
        paired = [f for f in self._filesQueue_ if f.suffix == ".rsv" and f.stem == abf.stem and f.parent == abf.parent]
        if len(paired):
            return paired[0]

    def _abfForRsv_(self, rsv:pathlib.Path):
        """Returns the abf file paired with the rsv.
        Used in communicating with the directory monitor
        """
        paired = [f for f in self._filesQueue_ if f.suffix == ".abf" and f.stem == rsv.stem and f.parent == rsv.parent]
        if len(paired):
            return paired[0]
        
    def _setupPendingAbf_(self):
        """
        Used in communicating with the directory monitor
        """
        self._pending_.clear()

        if len(self._filesQueue_) < 2:
            return
        
        latestFile = self._filesQueue_[-1]
        
        if latestFile.suffix == ".rsv":
            abf = self._abfForRsv_(latestFile)
            if isinstance(abf, pathlib.Path) and abf.is_file():
                self._pending_[latestFile] = abf
                
        elif latestFile.suffix == ".abf":
            rsv = self._rsvForABF_(latestFile)
            if isinstance(rsv, pathlib.Path) and rsv.is_file():
                self._pending_[rsv] = latestFile
            
        for rsv, abf in self._pending_.items():
            if rsv in self._filesQueue_:
                self._filesQueue_.remove(rsv)
                
            if abf in self._filesQueue_:
                self._filesQueue_.remove(abf)
            
    def run(self):
        # print(f"{self.__class__.__name__}.run(): simulator = {self._simulator_}")
        if isinstance(self._simulator_, _LTPFilesSimulator_):
            # print(f"Starting simulation...")
            self._simulator_.start()
        else:
            # starts directory monitor and captures newly created files
            self._emitterWindow_.enableDirectoryMonitor(self._watchedDir_, True)
    
    @pyqtSlot()
    def quit(self):
        if isinstance(self._simulator_, _LTPFilesSimulator_):
            if self._simulator_.isRunning():
                self._simulator_.requestInterruption()
                self._simulator_.quit()
                self._simulator_.wait()
        # self.stopTimer.emit()
        # if isinstance(self._simulationTimer_, QtCore.QTimer):
        #     self._simulationTimer_.stop()
        super().quit()

    @pyqtSlot(pathlib.Path)
    def _simulateFile_(self, value):
        # print(f"{self.__class__.__name__}._simulateFile_: {value}")
        
        self.supplyFile(value)
            
    def supplyFile(self, abfFile:pathlib.Path):
        """Callback called by FileStatChecker"""
        # print(f"{self.__class__.__name__}.supplyFile to buffer: abfFile {abfFile.name}\n")
        self._abfListener_.reset()
        self.abfRunReady.emit(abfFile)
        
    @property
    def abfListener(self) -> FileStatChecker:
        return self._abfListener_
    
    @property
    def watchedDirectory(self) -> pathlib.Path:
        return self._watchedDir_

class _LTPOnlineFileProcessor_(QtCore.QThread):
    """Helper class for LTPOnline.
        Runs analysis on a single Clampex trial in a separate thread.
    """
    def __init__(self, parent:QtCore.QObject, 
                 abfBuffer:collections.deque,
                 abfRunParams:dict,
                 presynapticTriggers: dict,
                 landmarks:dict,
                 data:dict, 
                 resultsAnalysis:dict,
                 viewers:dict):
        QtCore.QThread.__init__(self, parent)
        
        self._abfRunBuffer_ = abfBuffer
        self._runParams_ = abfRunParams
        self._presynaptic_triggers_ = presynapticTriggers
        self._landmarks_ = landmarks
        self._data_ = data
        self._results_ = resultsAnalysis
        self._viewers_ = viewers
        
    @safeWrapper
    @pyqtSlot(pathlib.Path)
    def processAbfFile(self, abfFile:pathlib.Path):
        """Reads and ABF protocol from the ABF file and analyses the data
        """
        
        try:
            abfRun = pio.loadAxonFile(str(abfFile))
            self._runParams_.abfRunTimesMinutes.append(abfRun.rec_datetime)
            deltaMinutes = (abfRun.rec_datetime - self._runParams_.abfRunTimesMinutes[0]).seconds/60
            self._runParams_.abfRunDeltaTimesMinutes.append(deltaMinutes)
            
            # NOTE: 2023-12-29 14:59:01
            # get the ADC channels from the signals in abfRun
            
            protocol = pab.ABFProtocol(abfRun)

            # check that the number of sweeps actually stored in the ABF file/neo.Block
            # equals that advertised by the protocol
            # NOTE: mismatches can happen when trials are acquired very fast (i.e.
            # back to back) - in this case check the sequencing key in Clampex
            # and set an appropriate interval between successive trials !
            assert(protocol.nSweeps) == len(abfRun.segments), f"In {abfRun.name}: Mismatch between number of sweeps in the protocol ({protocol.nSweeps}) and actual sweeps in the file ({len(abfRun.segments)}); check the sequencing key?"

#             if isinstance(self._runParams_.dacChannels, int):
#                 dacs = [protocol.outputConfiguration(c) for c in range(self._runParams_.dacChannels)]
#                 
#             elif isinstance(self._runParams_.dacChannels, (tuple, list)) and all(isinstance(v, int) for v in self._runParams_.dacChannels):
#                 dacs = [protocol.outputConfiguration(c) for c in self._runParams_.dacChannels]
            
            # if protocol.activeDACChannelIndex not in [d.number for d in dacs]:
            #     raise ValueError(f"Neither dac in {self._runParams_.dacChannels} is the active DAC channel for this protocol")
            
#             if len(self._runParams_.episodes) == 0:
#                 # this is the first run ever ⇒ create a new recording episode
#                 episodeName = self._runParams_.episodeName
#                 if not isinstance(episodeName, str) or len(episodeName.strip()) == 0:
#                     episodeName = protocol.name
#                     
#             episodes = list(self._results_.keys())
            
            # check that the protocol in the ABF file is the same as the current one
            # else create a new episode automatically
            # 
            # upon first run, self._runParams_.protocol is None
            if not isinstance(self._runParams_.currentProtocol, pab.ABFProtocol):
                self._runParams_.currentProtocol = protocol
                # set up new episode
                # since Clampex only runs on Windows, we simply split the string up:
                #
                episodeName = protocol.name
                
            elif protocol != self._runParams_.currentProtocol:
                # a different protocol - here, newEpisode should have been "True"
                # if not, then automatically set a new episode and "invent" a name 
                # for it
                if not self._runParams_.newEpisode:
                    self._runParams_.newEpisode = True
                    episodeName = self._runParams_.currentEpisodeName
                    newEpisodeName = utilities.counter_suffix(episodeName, self._runParams_.episodes)
                    
            

            # NOTE: 2023-09-29 14:12:56
            # we need:
            #
            # 1) the recording clamp mode must be the same, either:
            #   VoltageClamp, CurrentClamp, or NoClamp (i=0), for field recordings
            #
            # 2) on the active DAC index there must be epochs:
            #   2.a) for patch clamp experiments:
            #       2.a.0) optional baseline step epoch with firstLevel == 0 and deltaLevel == 0
            #           alternatively the next epoch must start at First Duration > 0
            #       2.a.1) for membrane test: step epoch with firstLevel != 0, in :
            #           [mV] for VoltageClamp,
            #           [pA] for CurrentClamp

            # TODO/FIXME: 2023-10-03 23:25:04 - the following is a procedural convention
            # need to make it more generic
            # we assume the very first abfRun is a monitoring one => baseline episode
            # we add subsequent runs to the baseline episode until protocol changes
            #   => assume new protocol is conditioning protocol, which MAY be repeated
            #       for several runs => add subsequent runs to the conditioning episode
            #       until protocol changes again => the new protocol must be identical
            # to the monitoring protocol => chase episode
            #
            # TODO allow for several conditioning episodes (with same or different
            # conditioning protocols), possibly interleaved with monitoring episodes
            # which should have the same monitoring protocol
            #
            
#             if self._runParams_.currentProtocol is None:
#                 if protocol.clampMode() == self._runParams_.clampMode:
#                     assert(protocol.nSweeps in range(1,3)), f"Protocols with {protocol.nSweeps} are not supported"
#                     if protocol.nSweeps == 2:
#                         assert(dac.alternateDigitalOutputStateEnabled), "Alternate Digital Output should have been enabled"
#                         assert(not dac.alternateDACOutputStateEnabled), "Alternate Waveform should have been disabled"
#                         
#                         # TODO check for alternate digital outputs → True ; alternate waveform → False
#                         # → see # NOTE: 2023-10-07 21:35:39 - DONE ?!?
#                     # self._runParams_.monitorProtocol = protocol
#                     self._runParams_.currentProtocol = protocol
#                     self._runParams_.newEpisode = False
#                     self.processTrackingProtocol(protocol)
#                 else:
#                     raise ValueError(f"First run protocol has unexpected clamp mode: {protocol.clampMode()} instead of {self._runParams_.clampMode}")
#                 
#             else:
#                 # if protocol != self._runParams_.monitorProtocol:
#                 if protocol != self._runParams_.currentProtocol:
#                     if self._runParams_.newEpisode:
#                         if self._runParams_.currentEpisodeName is None:
#                             self._runParams_.currentEpisodeName = protocol.name
#                         if self._runParams_.currentProtocolIsConditioning:
#                             self._runParams_.conditioningProtocols.append(protocol)
#                         else:
#                             self._runParams_.monitoringProtocols.append(protocol)
#                             
#             if self._runParams_.currentProtocol.nSweeps == 2:
#                 # if not self._monitorProtocol_.alternateDigitalOutputStateEnabled:
#                 if not self._runParams_.currentProtocol.alternateDigitalOutputStateEnabled:
#                     # NOTE: this is moot, because the protocol has already been checked
#                     # in the processTrackingProtocol
#                     raise ValueError("When the protocol defines two sweeps, alternate digtal outputs MUST have been enabled in the protocol")
#                 # NOTE: 2023-10-07 21:35:39
#                 # we are alternatively stimulating two pathways
#                 # NOTE: the ABF Run should ALWAYS have two sweeps in this case - one
#                 # for each pathway - regardless of how many runs there are per trial
#                 # if number of runs > 1 then the ABF file stores the average record
#                 # of each sweep, across the number of runs (or however the averaging mode
#                 # was set in the protocol; WARNING: this last bit of information is 
#                 # NOT currently used here)
#                 
#             elif self._monitorProtocol_.nSweeps != 1:
#                 raise ValueError(f"Expecting 1 or 2 sweeps in the protocol; instead, got {self._monitorProtocol_.nSweeps}")
#                 
#             # From here on we do things differently, depending on whether protocol is a
#             # the monitoring protocol or the conditioning protocol
#             if protocol == self._runParams_.currentProtocol:
#                 adc = protocol.inputConfiguration(self._runParams_.adcChannel)
#                 sigIndex = neoutils.get_index_of_named_signal(abfRun.segments[0].analogsignals, adc.name)
#                 # for k, seg in enumerate(abfRun.segments[:1]): # use this line for debugging
#                 for k, seg in enumerate(abfRun.segments):
#                     pndx = f"path{k}"
#                     if k > 1:
#                         break
#                     
#                     adcSignal = seg.analogsignals[sigIndex]
#                     
#                     sweepStartTime = protocol.sweepTime(k)
#                     
#                     # self._data_["baseline"][pndx].segments.append(abfRun.segments[k])
#                     self._data_[self._runParams_.currentEpisodeName][pndx].segments.append(abfRun.segments[k])
#                     if isinstance(self._presynaptic_triggers_[self._runParams_.currentEpisodeName][pndx], TriggerEvent):
#                         self._data_["baseline"][pndx].segments[-1].events.append(self._presynaptic_triggers_[pndx])
#                         
#                     viewer = self._viewers_[pndx]#["synaptic"]
#                     viewer.view(self._data_["baseline"][pndx],
#                                 doc_title=pndx,
#                                 showFrame = len(self._data_["baseline"][pndx].segments)-1)
#                     
#                     self._signalAxes_[pndx] = viewer.axis(adc.name)
#                     
#                     viewer.currentAxis = self._signalAxes_[pndx]
#                     # viewer.xAxesLinked = True
#                     
#                     viewer.plotAnalogSignalsCheckBox.setChecked(True)
#                     viewer.plotEventsCheckBox.setChecked(True)
#                     viewer.analogSignalComboBox.setCurrentIndex(viewer.currentAxisIndex+1)
#                     viewer.analogSignalComboBox.activated.emit(viewer.currentAxisIndex+1)
#                     # viewer.currentAxis.vb.enableAutoRange()
#                     # viewer.currentAxis.vb.autoRange()
#                     self._signalAxes_[pndx].vb.enableAutoRange()
#                     
#                     cnames = [c.name for c in viewer.dataCursors]
#                     
#                     if self._clampMode_ == ephys.ClampMode.VoltageClamp:
#                         for landmarkname, landmarkcoords in self._landmarks_.items():
#                             if k > 0 and landmarkname in ("Rbase", "Rs", "Rin"):
#                                 # don't need those in both pathways!
#                                 continue
#                             if landmarkname not in cnames:
#                                 if landmarkname ==  "Rs":
#                                     # overwrite this with the local signal extremum
#                                     # (first capacitance transient)
#                                     sig = adcSignal.time_slice(self._mbTestStart_+ sweepStartTime,
#                                                                                     self._mbTestStart_ + self._mbTestDuration_+ sweepStartTime)
#                                     if self._mbTestAmplitude_ > 0:
#                                         # look for a local maximum in the dac
#                                         transientTime = sig.times[sig.argmax()]
#                                     else:
#                                         transientTime = sig.times[sig.argmin()]
#                                         # look for local minimum in the dac
#                                         
#                                     start = transientTime - self._responseBaselineDuration_/2
#                                     duration = self._responseBaselineDuration_
#                                     
#                                 else:
#                                     if any(v is None for v in landmarkcoords):
#                                         # for the case when only a single pulse was used
#                                         continue
#                                     start, duration = landmarkcoords
#                                     
#                                 x = float((start + duration / 2 + sweepStartTime).rescale(pq.s))
#                                 xwindow = float(duration.rescale(pq.s))
#                                 # print(f"x = {x}, xwindow = {xwindow}")
#                                 viewer.addCursor(sv.SignalCursorTypes.vertical,
#                                                 x = x,
#                                                 xwindow = xwindow,
#                                                 label = landmarkname,
#                                                 follows_mouse = False,
#                                                 axis = self._signalAxes_[pndx],
#                                                 relative=True,
#                                                 precision=5)
#                                 
#                         # we allow cursors to be repositioned during the recording
#                         # therefore we do not generate neo.Epochs anymore
#                         
#                         if k == 0:
#                             # calculate DC, Rs, and Rin for pathway 0 only
#                             Rbase_cursor = viewer.dataCursor("Rbase")
#                             coords = ((Rbase_cursor.x - Rbase_cursor.xwindow/2) * pq.s, (Rbase_cursor.x + Rbase_cursor.xwindow/2) * pq.s)
#                             Idc = np.mean(adcSignal.time_slice(*coords))
#                                         
#                             self._results_["DC"].append(Idc)
#                             
#                             Rs_cursor = viewer.dataCursor("Rs")
#                             coords = ((Rs_cursor.x - Rs_cursor.xwindow/2) * pq.s, (Rs_cursor.x + Rs_cursor.xwindow/2) * pq.s)
#                             if self._mbTestAmplitude_ > 0:
#                                 Irs = np.max(adcSignal.time_slice(*coords))
#                             else:
#                                 Irs = np.min(adcSignal.time_slice(*coords))
#                                 
#                             Rs  = (self._mbTestAmplitude_ / (Irs-Idc)).rescale(pq.MOhm)
#                             
#                             self._results_["Rs"].append(Rs)
#                             
#                             Rin_cursor = viewer.dataCursor("Rin")
#                             coords = ((Rin_cursor.x - Rin_cursor.xwindow/2) * pq.s, (Rin_cursor.x + Rin_cursor.xwindow/2) * pq.s)
#                             Irin = np.mean(adcSignal.time_slice(*coords))
#                                 
#                             Rin = (self._mbTestAmplitude_ / (Irin-Idc)).rescale(pq.MOhm)
#                             
#                             self._results_["Rin"].append(Rin)
#                             
#                             
#                         Ipsc_base_cursor = viewer.dataCursor("PSCBase")
#                         coords = ((Ipsc_base_cursor.x - Ipsc_base_cursor.xwindow/2) * pq.s, (Ipsc_base_cursor.x + Ipsc_base_cursor.xwindow/2) * pq.s)
#                         
#                         IpscBase = np.mean(adcSignal.time_slice(*coords))
#                         
#                         Ipsc0Peak_cursor = viewer.dataCursor("PSC0Peak")
#                         coords = ((Ipsc0Peak_cursor.x - Ipsc0Peak_cursor.xwindow/2) * pq.s, (Ipsc0Peak_cursor.x + Ipsc0Peak_cursor.xwindow/2) * pq.s)
#                         
#                         Ipsc0Peak = np.mean(adcSignal.time_slice(*coords))
#                         
#                         Ipsc0 = Ipsc0Peak - IpscBase
#                         
#                         self._results_[pndx]["Response0"].append(Ipsc0)
#                         
#                         if self._presynaptic_triggers_[pndx].size > 1:
#                             Ipsc1Peak_cursor = viewer.dataCursor("PSC1Peak")
#                             coords = ((Ipsc1Peak_cursor.x - Ipsc1Peak_cursor.xwindow/2) * pq.s, (Ipsc1Peak_cursor.x + Ipsc1Peak_cursor.xwindow/2) * pq.s)
#                             
#                             Ipsc1Peak = np.mean(adcSignal.time_slice(*coords))
#                             Ipsc1 = Ipsc1Peak - IpscBase
#                             
#                             self._results_[pndx]["Response1"].append(Ipsc1)
#                             
#                             self._results_[pndx]["PairedPulseRatio"].append(Ipsc1/Ipsc0)
#                         
#                         
#                 responses = dict(amplitudes = dict(path0 = None, path1 = None), 
#                                 pprs = dict(path0 = None, path1 = None), 
#                                 rs = None, rincap = None, dc = None)
#     #             pprs = dict(path0 = None, path1 = None)
#     #             
#     #             mbTest = dict(rs = None, rincap = None)
#     #             
#                 for field, value in self._results_.items():
#                     if not field.startswith("path"):
#                         if len(value):
#                             # pts = IrregularlySampledDataSignal(np.arange(len(value)),
#                             #                                     value, units = value[0].units,
#                             #                                     time_units = pq.dimensionless,
#                             #                                     name = field,
#                             #                                     domain_name="Sweep")
#                             
#                             pts = IrregularlySampledDataSignal(self._abfRunDeltaTimes_,
#                                                             value, units = value[0].units,
#                                                             time_units = pq.min,
#                                                             name = field,
#                                                             domain_name="Time")
#                             
#                             if field in ("DC", "tau"):
#                                 responses["dc"] = pts
#                                 # self._viewers_["dc"].view(pts)
#                                     
#                             elif field == "Rs":
#                                 responses["rs"] = pts
#                                 # mbTest["rs"] = pts
#                                 # self._viewers_["rs"].view(pts)
#                                 
#                             elif field in ("Rin", "Cap"):
#                                 responses["rincap"] = pts
#                                 # mbTest["rincap"] = pts
#                                 # self._viewers_["rin"].view(pts)
#                                 
#                     else:
#                         pname = field
#                         resp0 = value["Response0"]
#                         if len(resp0) == 0:
#                             continue
#                         
#                         resp1 = value["Response1"]
#                         
#                         sname = "Slope" if self._clampMode_ == ephys.ClampMode.CurrentClamp and self._useSlopeInIClamp_ else "Amplitude"
#                         
#     #                     if len(resp1) == len(resp0):
#     #                         response = IrregularlySampledDataSignal(np.arange(len(resp0)),
#     #                                                            np.vstack((resp0, resp1)).T,
#     #                                                            units = resp0[0].units,
#     #                                                            time_units = pq.dimensionless,
#     #                                                            domain_name = "Sweep",
#     #                                                            name = f"{sname} {pname}")
#     #                         
#     #                     else:
#     #                         response = IrregularlySampledDataSignal(np.arange(len(resp0)),
#     #                                                            resp0,
#     #                                                            units = resp0[0].units,
#     #                                                            time_units = pq.dimensionless,
#     #                                                            domain_name = "Sweep",
#     #                                                            name = f"{sname} {pname}")
#                         # NOTE: 2023-10-06 08:21:13 
#                         # only plot the first response amplitude
#                         response = IrregularlySampledDataSignal(self._abfRunDeltaTimes_,
#                                                             resp0,
#                                                             units = resp0[0].units,
#                                                             time_units = pq.min,
#                                                             domain_name = "Time",
#                                                             name = f"{sname} {pname}")
#                             
#                         # response = IrregularlySampledDataSignal(np.arange(len(resp0)),
#                         #                                     resp0,
#                         #                                     units = resp0[0].units,
#                         #                                     time_units = pq.dimensionless,
#                         #                                     domain_name = "Sweep",
#                         #                                     name = f"{sname} {pname}")
#                             
#                         # self._viewers_[pname]["amplitudes"].view(pts)
#                         
#                         responses["amplitudes"][pname] = response
#                         
#                         ppr = value["PairedPulseRatio"]
#                         
#                         if len(ppr):
#                             pts = IrregularlySampledDataSignal(self._abfRunDeltaTimes_,
#                                                             ppr,
#                                                             units = pq.dimensionless,
#                                                             time_units = pq.min,
#                                                             domain_name = "Time",
#                                                             name = f"PPR {pname}")
#                             
#                             # pts = IrregularlySampledDataSignal(np.arange(len(ppr)),
#                             #                                    ppr,
#                             #                                    units = pq.dimensionless,
#                             #                                    time_units = pq.dimensionless,
#                             #                                    domain_name = "Sweep",
#                             #                                    name = f"PPR {pname}")
#                             
#                             responses["pprs"][pname] = pts
#                             # pprs[pname] = pts
#                             
#                 resultsPlot = list()
#                 
#                 if isinstance(responses["amplitudes"]["path0"], IrregularlySampledDataSignal):
#                     resultsPlot.append(responses["amplitudes"]["path0"])
#                     if isinstance(responses["amplitudes"]["path1"], IrregularlySampledDataSignal):
#                         resultsPlot.append(responses["amplitudes"]["path1"])
#                     
#                 if isinstance(responses["pprs"]["path0"], IrregularlySampledDataSignal):
#                     resultsPlot.append(responses["pprs"]["path0"])
#                     if isinstance(responses["pprs"]["path1"], IrregularlySampledDataSignal):
#                         resultsPlot.append(responses["pprs"]["path1"])
#                         
#                 if isinstance(responses["rs"], IrregularlySampledDataSignal):
#                     resultsPlot.append(responses["rs"])
#                     
#                     if isinstance(responses["rincap"], IrregularlySampledDataSignal):
#                         resultsPlot.append(responses["rincap"])
#                         
#                 if isinstance(responses["dc"], IrregularlySampledDataSignal):
#                     resultsPlot.append(responses["dc"])
#                     
#                 self._viewers_["results"].view(resultsPlot, symbolColor="black", symbolBrush="black")
#                 
#                 return (self._data_, self._results_)
                
        except:
            traceback.print_exc()
        

    def processProtocol(self, protocol:pab.ABFProtocol):
        clampMode = protocol.clampMode(self._adcChannel_, self._dacChannel_)
        adc = protocol.inputConfiguration(self._adcChannel_)
        dac = protocol.outputConfiguration(self._dacChannel_)
        
        
        pass
    
    def storeProtocol(self, protocol:pab.ABFProtocol):
        if protocol.nSweeps == 2:
            assert(dac.alternateDigitalOutputStateEnabled), "Alternate Digital Output should have been enabled"
            assert(not dac.alternateDACOutputStateEnabled), "Alternate Waveform should have been disabled"
            
        if self._runParams_.protocol is None:
            self._runParams_.newEpisode = True
            
        self._runParams_.protocol = protocol
        
        if self._runParams_.currentProtocolIsConditioning:
            self._runParams_.newEpisode
            self._runParams_.conditioningProtocols.append(protocol)
        else:
            self._runParams_.monitoringProtocols.append(protocol)
        
        if self._runParams_.newEpisode:
            self.processTrackingProtocol(protocol)
        

    def processTrackingProtocol(self, protocol:pab.ABFProtocol):
        """Infers the timings of the landmarks from protocol.
        Called only when self._monitorProtocol_ is None (i.e., at first run)
        """
        # TODO: 2023-10-03 12:31:19
        # implement the case where TTLs are emulated with a DAC channel (with its
        # output routed to a simulus isolator)
        #
        # NOTE: 2023-10-04 18:42:34
        # the code below assumes voltage-clamp and EPSCs hence relies on signal
        # baseline before the response to measure amplitude
        #
        # TODO: 2023-10-04 18:43:12 URGENT FIXME
        # code for current-clamp/field recordings where we measure the slope of 
        #   the rising phase of the synaptic potentials !
        #
        
        
        # the DAC used to send out the command waveforms
        dac = protocol.outputConfiguration(self._dacChannel_)
        
        # Guess which DAC output has digital outputs enabled.
        #
        # In Clampex, there can be only one!¹
        #
        # Ths is necessary because one may have confgured dig outputs in a DAC
        # different from the one used for command waveform.
        #
        # HOWEVER, this is only possble when alternate digital outputs are 
        # enabled in the protocol - and, hence, this dac must have the same epochs
        # defined as the DAC used for clamping.
        #
        # ¹) For this reason, additional triggers can only be sent out by emulating
        #    TTL waveforms in the analog command epochs on additional DAC outputs.
        #
        digOutDacs = list(filter(lambda x: x.digitalOutputEnabled, (protocol.outputConfiguration(k) for k in range(protocol.nDACChannels))))
        
        if len(digOutDacs) == 0:
            raise ValueError("The protocol indicates there are no DAC channels with digtal output enabled")
        
        digOutDACIndex = digOutDacs[0].number
        
        if digOutDACIndex != self._dacChannel_:
            if not protocol.alternateDigitalOutputStateEnabled:
                raise ValueError(f"Digital outputs are enabled on DAC {digOutDACIndex} and command waveforms are sent via DAC {self._dacChannel_}, but alternative digital outputs are disabled in the protocol")
        
            assert protocol.nSweeps % 2 == 0, "For alternate DIG pattern the protocol is expected to have an even number of sweeps"
            
        # DAC where dig out is enabled;
        # when alt dig out is enabled, this stores the main dig pattern
        # (the dig pattern sent out on even sweeps 0, 2, 4, etc)
        # whereas the "main" dac retrieved above stores the alternate digital pattern
        # (the dig pattern set out on odd sweeps, 1,3, 5, etc)
        
        digdac = protocol.outputConfiguration(digOutDACIndex)
        
        if len(digdac.epochs) == 0:
            raise ValueError("DAC with digital outputs has no epochs!")
        
        digEpochsTable = digdac.epochsTable(0)
        dacEpochsTable = dac.epochsTable(0)
        
        digEpochsTable_reduced = digEpochsTable.loc[[i for i in digEpochsTable.index if not i.startswith("Digital Pattern")], :]
        dacEpochsTable_reduced = dacEpochsTable.loc[[i for i in dacEpochsTable.index if not i.startswith("Digital Pattern")], :]
        
        digEpochsTableAlt = None
        digEpochsTableAlt_reduced = None
        
        if digOutDACIndex != self._dacChannel_:
            # a this point, this implies protocol.alternateDigitalOutputStateEnabled == True
            #
            # What we check here:
            # when alternate digital output is enabled, AND the dig dac is dfferent 
            # from the main dac, the epochs defned in each of the dacs MUST be the same
            # EXCEPT for the reported (stored) digital patterns
            # 
            # The idea is that the main experimental epochs are defined in the dacChannel,
            # but the digital outputs may be defined in the "alternative" DAC channel,
            # with the condition that the same epochs are defined there
            # 
            # NOTE: In general this is a SOFT requirement (one can imagine 
            # doing completely different things in the "alternate" digital output)
            #
            # However, for a synaptic plasticity experiment, sending stimuli at
            # different times on the alternate pathway is an unnecessary complication
            # hence, HERE, this is is a HARD requirement (for now...)
            #
            digEpochsTableAlt = digdac.epochsTable(1)
            digEpochsTableAlt_reduced = digEpochsTableAlt.loc[[i for i in digEpochsTableAlt.index if not i.startswith("Digital Pattern")], :]
            assert(np.all(digEpochsTable_reduced == dacEpochsTable_reduced)), "Epochs table mismatch between DAC channels"
            assert(np.all(digEpochsTableAlt_reduced == dacEpochsTable_reduced)), "Epochs table mismatch between DAC channels with alternate digital outputs"
        
        
        # Locate the presynaptic triggers epoch
        # first try and find epochs with digital trains
        # there should be only one such epoch, sending at least one TTL pulse per train
        #
        
        synStimEpochs = list(filter(lambda x: len(x.trainDigitalOutputChannels("all"))>0, 
                                    digdac.epochs))
        
        # synStimEpochs = list(filter(lambda x: any(x.hasDigitalTrain(d) for d in stimDIG), 
        #                             digdac.epochs))
        
        # ideally there is only one such epoch
        if len(synStimEpochs) > 1:
            warnings.warn(f"There are {len(synStimEpochs)} in the protocol; will use the first one")
            synStimEpochs = [synStimEpochs[0]]
            # return False
        
        elif len(synStimEpochs) == 0:
            # Try prestim triggers defined as digital pulses instead of trains.
            #
            # Here we can expect to have more than one such epochs, together 
            #   emulating a train of TTL pulses (with one pulse per epoch).
            #
            # There should be no intervening epochs here...
            #
            # Obviously, this is a contrived scenario that might work for the 
            # synaptic monitoring episodes of the experiment (when one might use
            # single,  paired-pulse, or even a few pulses - although I am not 
            # sure there is good case for the latter) but is not so usable during 
            # conditioning episodes, especially those using high frequency trains
            # (one would run out of epochs pretty fast...); nevertheless, I can 
            # imagine case where low frequency triggers could be generated
            # using pulses instead of trains for conditioning as well (e.g.
            # low frequency stimulations)
            #
            synStimEpochs = list(filter(lambda x: len(x.pulseDigitalOutputChannels("all"))>0, 
                                        digdac.epochs))
        
            # synStimEpochs = list(filter(lambda x: any(x.hasDigitalPulse(d) for d in stimDIG), 
            #                             digdac.epochs))
            if len(synStimEpochs) == 0:
                raise ValueError("There are no epoch sending digital triggers")
            
        # store these for later
        stimDIG = unique(synStimEpochs[0].usedDigitalOutputChannels("all"))
            
        # We need:
        # start of membrane test
        # duration of membrane test
        # magnitude of membrane test
        
        # locate the membrane test epoch; this is a step or pulse epoch, with:
        # (• are hard requirements, ∘ are soft requirements)
        # • first level !=0
        # • delta level == 0
        # • delta duration == 0
        # ∘ no digital info 
        
        mbTestEpochs = list(filter(lambda x: x.epochType in (pab.ABFEpochType.Step, pab.ABFEpochType.Pulse) \
                                            and not any(x.hasDigitalOutput(d) for d in stimDIG) \
                                            and x.firstLevel !=0 and x.deltaLevel == 0 and x.deltaDuration == 0, 
                                   dac.epochs))
        
        # NOTE: for the moment, I do not expect to have more than one such epoch
        # WARNING we require a membrane test epoch in voltage clamp;
        # in current clamp this is not mandatory as we may be using field recordings
        if len(mbTestEpochs) == 0:
            if self._clampMode_ == ephys.ClampMode.VoltageClamp:
                raise ValueError("No membrane test epoch appears to have been defined")
            self._membraneTestEpoch_ = None
            
        else:
            self._membraneTestEpoch_ = mbTestEpochs[0]
        
        if self._membraneTestEpoch_ is None:
            self._mbTestAmplitude_ = None
            self._mbTestStart_ = None
            self._mbTestDuration_ = None
            self._signalBaselineStart_ = 0 * pq.s
            self._signalBaselineDuration_ = dac.epochRelativeStartTime(synStimEpochs[0], 0)
            self._responseBaselineStart_ = self._signalBaselineStart_
            self._responseBaselineDuration_ = self._signalBaselineDuration_
        else:
            self._mbTestAmplitude_ = self._membraneTestEpoch_.firstLevel
        
            self._mbTestStart_ = dac.epochRelativeStartTime(self._membraneTestEpoch_, 0)
            self._mbTestDuration_ = self._membraneTestEpoch_.firstDuration
        
        
            # Figure out the global signal baseline and the baseline for synaptic 
            # responses, based on the relative timings of the membrane test and trigger
            #   epochs
            #
            # For this purpose I guess could use the epoch number or letter but since
            #   I need the timings, I prefer to do it as below.
            #

            # NOTE: 2023-10-05 12:16:09
            # Setup landmark timings - all relative to the sweep start time
            #
            # 1) parse the protocol for epochs
            #
            if dac.epochRelativeStartTime(self._membraneTestEpoch_, 0) + self._membraneTestEpoch_.firstDuration < digdac.epochRelativeStartTime(synStimEpochs[0], 0):
                # membrane test is delivered completely sometime BEFORE triggers
                #
                
                if self._mbTestStart_ == 0:
                    # membrane test is at the very beginning of the sweep (but always 
                    # after the holding time; odd, but allowed...)
                        
                    self._signalBaselineStart_ = 0 * pq.s
                    self._signalBaselineDuration_ = dac.epochRelativeStartTime(self._membraneTestEpoch_, 0)
                    
                else:
                    # are there any epochs definded BEFORE mb test?
                    initialEpochs = list(filter(lambda x: dac.epochRelativeStartTime(x, 0) + x.firstDuration <=  dac.epochRelativeStartTime(self._membraneTestEpoch_, 0) \
                                                        and x.firstDuration > 0 and x.deltaDuration == 0, 
                                                    dac.epochs))
                    
                    if len(initialEpochs):
                        baselineEpochs = list(filter(lambda x: x.firstLevel == 0 and x.deltaLevel == 0, initialEpochs))
                        if len(baselineEpochs):
                            self._signalBaselineStart_ = dac.epochRelativeStartTime(baselineEpochs[0], 0)
                            self._signalBaselineDuration_ = baselineEpochs[0].firstDuration
                        else:
                            self._signalBaselineStart_ = 0 * pq.s
                            self._signalBaselineDuration_ = dac.epochRelativeStartTime(initialEpochs[0], 0)
                            
                    else:
                        # no epochs before the membrane test (odd, but can be allowed...)
                        self._signalBaselineStart_ = max(self._mbTestStart_ - 2 * dac.holdingTime, 0*pq.s)
                        self._signalBaselineDuration_ = max(dac.holdingTime, self._membraneTestEpoch_.firstDuration)
                
                
                # Finally, get an epoch for the synaptic response baseline;
                # NOTE: IN the case where membrane test is delivered BEFORE the triggers,
                # we would expect to have another epoch intervening between the 
                # membrane test and the first epoch in synStimEpochs -  we will use
                # that to calculate the baseline for the synaptic responses
                #
                # This is not mandatory, but it would make more sense to let the cell
                # membrane "settle" after a membrane test before delivering a synaptic
                # stimulus.
                #
                # NOTE: 2023-10-04 18:34:59
                # we take 5 ms duration for this (arbitrary)
                #
                
                responseBaselineEpochs = list(filter(lambda x: x.firstLevel == 0 and x.deltaLevel == 0 and x.firstDuration >= self._responseBaselineDuration_ \
                                                            and dac.epochRelativeStartTime(x, 0) > self._mbTestStart_ + self._mbTestDuration_ \
                                                            and dac.epochRelativeStartTime(x, 0) + x.firstDuration <= digdac.epochRelativeStartTime(synStimEpochs[0], 0) - self._responseBaselineDuration_,
                                                    dac.epochs))
                
                if len(responseBaselineEpochs):
                    # take the last one
                    self._responseBaselineStart_ = dac.epochRelativeStartTime(responseBaselineEpochs[-1], 0)
                
                else:
                    self._responseBaselineStart_ = digdac.epochRelativeStartTime(synStimEpochs[0], 0) - 2 * self._responseBaselineDuration_
                    
                
                    
            elif dac.epochRelativeStartTime(self._membraneTestEpoch_, 0) > digdac.epochRelativeStartTime(synStimEpochs[-1], 0) + synStimEpochs[-1].firstDuration:
                # membrane test delivered somwehere towards the end of the sweep, 
                # surely AFTER the triggers (and hopefully when the synaptic responses
                # have decayed...)
                #
                # in this case, best is to use the first epoch before the synStimEpochs (if any)
                # or the dac holding
                #
                initialEpochs = list(filter(lambda x: dac.epochRelativeStartTime(x, 0) + x.firstDuration <=  digdac.epochRelativeStartTime(synStimEpochs[0], 0) \
                                                    and x.firstDuration > 0 and x.deltaDuration == 0, 
                                                dac.epochs))
                
                if len(initialEpochs):
                    # there are epochs before synStimEpochs - are any of these baseline-like?
                    baselineEpochs = list(filter(lambda x: x.firstLevel == 0 and x.deltaLevel == 0, initialEpochs))
                    if len(baselineEpochs):
                        self._signalBaselineStart_ = dac.epochRelativeStartTime(baselineEpochs[0], 0)
                        self._signalBaselineDuration_ = baselineEpochs[0].firstDuration
                    else:
                        self._signalBaselineStart_ = 0 * pq.s
                        self._signalBaselineDuration_ = dac.epochRelativeStartTime(initialEpochs[0], 0)
                        
                else:
                    # no epochs before the membrane test (odd, but can be allowed...)
                    self._signalBaselineStart_ = max(digdac.epochRelativeStartTime(synStimEpochs[0], 0) - 2 * dac.holdingTime, 0*pq.s)
                    self._signalBaselineDuration_ = max(dac.holdingTime, synStimEpochs[0].firstDuration)
            
                # Now, determine the response baseline for this scenario.
                responseBaselineEpochs = list(filter(lambda x: x.firstLevel == 0 and x.deltaLevel == 0 and x.firstDuration >= self._responseBaselineDuration_ \
                                                            and dac.epochRelativeStartTime(x, 0) > self._mbTestStart_ + self._mbTestDuration_ \
                                                            and dac.epochRelativeStartTime(x, 0) + x.firstDuration <= digdac.epochRelativeStartTime(synStimEpochs[0], 0) - self._responseBaselineDuration_,
                                                    dac.epochs))
                
                if len(responseBaselineEpochs):
                    # take the last one
                    self._responseBaselineStart_ = dac.epochRelativeStartTime(responseBaselineEpochs[-1], 0)
                
                else:
                    self._responseBaselineStart_ = digdac.epochRelativeStartTime(synStimEpochs[0], 0) - 2 * self._responseBaselineDuration_
        #
        # 2) create trigger events
        #
        for path in range(protocol.nSweeps):
            pndx = f"path{path}"
            pathEpochs = sorted(synStimEpochs, key = lambda x: dac.epochRelativeStartTime(x, path))
            trig = dac.triggerEvents(pathEpochs[0], path) # will add sweep start time here
            if len(pathEpochs) > 1:
                for e in pathEpochs[1:]:
                    trig = trig.merge(dac.triggerEvents(e, path))#, label="EPSC"))
                
            ntrigs = trig.size
            ll = [f"EPSC{k}" for k in range(ntrigs)]
            trig.labels = ll
            
            if not isinstance(self._presynaptic_triggers_.get(pndx, None), TriggerEvent):
                self._presynaptic_triggers_[pndx] = trig
            else: # not needed, really, because we set these up only upon the first run...
                assert(trig == self._presynaptic_triggers_[pndx]), f"Presynaptic triggers mismatch {trig} vs path0 trigger {self._presynaptic_triggers_[pndx]}"
                
        #
        # 3) populate the landmarks dictionary
        #
        # TODO: populate self._landmarks_ with neo.Epochs-like lists (start, duration)
        # use these to generate cursors in the corresponding pathway signal viewer
        # DECIDE: we need:
        #
        # • for voltage clamp:
        #
        #   ∘ global baseline Rbase epoch interval  -> aveage of signal slice
        #
        #   ∘ Rs epoch interval                     -> extremum of signal slice
        #       ⋆ max for positive Vm step, min for negative Vm step
        #
        #   ∘ Rin epoch interval                    -> average of signal slice
        #   
        #   ∘ EPSCbase interval (or EPSC0Base and EPSC1Base intervals) 
        #       ⋆ NOTE a single EPSCBase should also be used for paire-pulse,
        #           where we use it as a common baseline for BOTH EPSCs -> 
        #           TODO Adapt functions for LTP analysis in this module
        #
        #   ∘ EPSCPeak interval (or EPSC0Peak and EPSC1Peak intervals)
        #       ⋆ NOTE needs two intervals for paired-pulse
        # 
        # • for current-clamp:
        #
        #   ∘ global baseline Baseline epoch interval  -> aveage of signal slice
        #
        #   ∘ measure the membrane test with membrane.passive_Iclamp(…) 
        #       ⋆ => calculate tau, Rin and capacitance
        #
        #   ∘ EPSP interval or EPSP0 and EPSP1 intervals (for paired-pulse)
        #       ⋆ measure slope of 10-90% of rising phase
        #
        if self._clampMode_ == ephys.ClampMode.VoltageClamp:
            self._landmarks_["Rbase"] = [self._signalBaselineStart_, self._signalBaselineDuration_]
            
            # Rs landmark will be overwritten after find out local extremum in 
            # the adc signal (searching for the first capacitance transient)
            # also, NOTE that we only need Rbase, Rs, and Rin for the pathway 0
            #
            self._landmarks_["Rs"] = [dac.epochRelativeStartTime(self._membraneTestEpoch_), 
                                      self._responseBaselineDuration_]
            self._landmarks_["Rin"] = [dac.epochRelativeStartTime(self._membraneTestEpoch_) + self._membraneTestEpoch_.firstDuration - 2 * self._responseBaselineDuration_,
                                       self._responseBaselineDuration_]
            self._landmarks_["PSCBase"] = [self._responseBaselineStart_, self._responseBaselineDuration_]
            self._landmarks_["PSC0Peak"] = [self._presynaptic_triggers_["path0"].times[0] - protocol.sweepTime(0) + 15 * pq.ms,
                                           2 * pq.ms]
            if self._presynaptic_triggers_["path0"].size > 1:
                self._landmarks_["PSC1Peak"] = [self._presynaptic_triggers_["path0"].times[1] - protocol.sweepTime(0) + 15 * pq.ms,
                                            2 * pq.ms]
        else:
            # WARNING - needs more work to adapt to what passive_Iclamp needs:
            # vm signal (slice of the adc data on VmTest)
            # im as a list of amplitude, VmTest start, VmTest stop
            # steadystate duration - default is 50 ms
            self._landmarks_["Base"] = [self._signalBaselineStart_,self._signalBaselineDuration_]
            if self._membraneTestEpoch_ is not None:
                self._landmarks_["VmTest"] = [dac.epochRelativeStartTime(self._membraneTestEpoch_),
                                            self._membraneTestEpoch_.firstDuration]
            
class LTPOnline(QtCore.QObject):
    """On-line analysis for synaptic plasticity experiments
    """
        
    test_protocol_properties = ("activeDACChannelIndex",
                                "nSweeps",
                                "acquisitionMode",
                                "samplingRate",
                                "alternateDigitalOutputStateEnabled",
                                "alternateDACOutputStateEnabled")
    
    timings_fields = ("dcStart", "dcStop", 
                      "RsStart", "RsStop",
                      "RinStop", "RinStop",
                      "EPSC0BaseStart", "EPSC0BaseStop",
                      "EPSC0PeakStart", "EPSC0PeakStop",
                      "EPSC1BaseStart", "EPSC1BaseStop",
                      "EPSC1PeakStart", "EPSC1PeakStop",
                      )
    
    resultsReady = pyqtSignal(object, name="resultsReady")
    

    def __init__(self, *args,
                 useEmbeddedProtocol:bool=True,
                 trackingClampMode:typing.Union[int, ephys.ClampMode] = ephys.ClampMode.VoltageClamp,
                 conditioningClampMode:typing.Union[int, ephys.ClampMode]=ephys.ClampMode.CurrentClamp,
                 baselineDurations:pq.Quantity = 5 * pq.ms,
                 steadyStateIClampMbTestDuration = 0.05 * pq.s,
                 useSlopeInIClamp:bool = True,
                 signalBaselineStart:typing.Optional[pq.Quantity] = None,
                 signalBaselineDuration:typing.Optional[pq.Quantity] = None,
                 emitterWindow:typing.Optional[QtWidgets.QMainWindow] = None,
                 directory:typing.Optional[typing.Union[str, pathlib.Path]] = None,
                 autoStart:bool=False, # NOTE: change to True when done coding TODO
                 parent=None,
                 simulate = None
                 ):
        """
        Var-positional parameters:
        --------------------------
    
        One or more ephys.Source specifying the logical association between
        input and outputs in this experiment.
    
        trackingClampMode: expected clamping mode; one of ephys.ClampMode.VoltageClamp
            or ephys.ClampMode.CurrentClamp, or their respective int values (2, 4)

            NOTE: even if recording field potentials (I=0 "clamping mode") the units
            of the DAC and ADC should pair up as for current clamp (i.e., DAC in mV
            and ADC in pA) because I=0 is actually current clamp without actual clamping
            (i.e. no current injected into the cell whatsoever)

            Also NOTE this is irrespective of electrode mode: patch clamp can
            record in either clamp modes; on the other hand, sharp (intracellular)
            or field recording electrodes are useless in voltage clamp...

        conditioningMode: as above;
            for patch-clamp recordings one may choose to trigger postsynaptic
                activity by current injection (current clamp) or 'emulated' in
                voltage-clamp with AP-like waveforms, dynamic clamp and such...
                (if the cell can be voltage-clamped with some degree of accuracy)

                therefore, any of voltage- or current-clamp modes are valid
        
        responseBaselineDuration: time Quantity (default is 5 * pq.ms)
            Duration of baseline before the response - used in Voltage clamp
        
        """
        
        super().__init__(parent=parent)
        
        if len(args) == 0:
            self._sources_ = None
            # TODO: 2024-01-04 22:19:44 
            # write code to infer Source from first ABF file (in _LTPOnlineFileProcessor_)
            raise ValueError("I must have at least one Source defined")
        else:
            if not all(isinstance(a, Source) for a in args):
                raise TypeError(f"Expecting one or more Source objects")
            sset = set(args)
            
            if len(sset) < len(args):
                dupsrc = duplicates(args, indices=True)
                raise ValueError(f"Duplicate sources detected in 'args': {dupsrc}")
        
            # parse sources from args; make sure there are identical names
            dupNames = duplicates([a.name for a in args], indices=True)

            if len(dupNames):
                warnings.warn("The sources do not have unique names; names will be adapted.")
                snames = list()
                self._sources_ = list()
                for src in args:
                    if src.name not in snames:
                        snames.append(src.name)
                        sources.append(src)
                        
                    else:
                        # adapt name to avoid duplicates; since an ephys.Source is 
                        # an immutable named tuple, we use its _replace method to create
                        # a copy with a new name
                        new_name = utilities.counter_suffix(src.name, snames)
                        snames.append(new_name)
                        sources.append(src._replace(name=new_name))
                        
            else:
                self._sources_ = args
                
            #### BEGIN Checks
            #
            # NOTE: 2024-01-04 22:20:55
            # check consistency of synaptic stimuli in sources
            
            # make sure sources specify distinct signal layouts for synaptic
            # simulations; in particular sources must specifiy:
            # • unique ADC ↦ DAC pairs
            # • unique synaptic stimulus configurations
            # • unique auxiliary ADCs (when used) — these are useful to infer 
            #   trigger protocols from input signals recorded via auxiliary inputs
            #   — specified using AuxiliaryInput objects:
            #   
            
            # DACs used to emulate TTLs for synaptic stimuli
            syndacs = set(itertools.chain.from_iterable(s.syn_dac for s in self._sources_))
            
            # DACs used to emulate TTLs for other purposes
            ttldacs = set(itertools.chain.from_iterable(s.out_dac_triggers for s in self._sources_))
            
            # DACs used to emit waveforms other than clamping
            # these should REALLY be distinct from ttldacs
            cmddacs = set(itertools.chain.from_iterable(s.other_outputs for s in self._sources_))
            
            # DIGs used for synaptic stimulation
            syndigs = set(itertools.chain.from_iterable(s.syn_dig for s in self._sources_))
            
            # DIGs used to trigger anything other than synapses
            digs = set(itertools.chain.from_iterable(s.out_dig_triggers for s in self._sources_))
            
            
            # 1. all sources must have a primary ADC
            if any(s.adc is None for s in self._sources_):
                raise ValueError("All source must specify a primary ADC input")
            
            adcs, snames  = list(zip(*[(s.adc, s.name) for s in self._sources_]))
            
            # 2. primary ADCs cannot be shared among sources
            dupadcs     = duplicates(adcs)  # sources must have distinct main ADCs
            if len(dupadcs):
                raise ValueError(f"Sharing of primary ADCs ({dupadcs}) among sources is forbidden")
            
            # 3. source names should be unique
            dupnames = duplicates(snames)
            if len(dupnames):
                raise ValueError(f"Sharing of names ({dupnames}) among sources is forbidden")
                
            # 4. for clamped sources only - by definition these define a primary DAC
            #   needed for clamping and to provide waveforms for optionally for 
            #   membrane test (recommended) and possibly other electrical 
            #   manipulations of the clamped cell (e.g., to elicit postsynaptic spikes).
            #
            #   See detailed checks below (4.1, 4.2, etc)
            #
            # In the SAME experiment, a DAC cannot be used, simultaneously, for:
            # • clamping command waveforms
            # • TTL emulation (± 5 V !)
            # 
            
            clamped_sources = [s for s in self._sources_ if s.clamped]
            if len(clamped_sources):
                # these DACs MUST be unique
                dacs = [s.dac for s in clamped_sources]
                
                # 4.1 primary DACs must be unique
                dupdacs = duplicates(dacs)
                if len(dupdacs):
                    raise ValueError(f"Sharing of primary DACs ({dupdacs}) among sources is forbidden")
                
                # 4.2 primary DACs CANNOT be used for synaptic stimulation
                ovlap = syndacs & set(dacs)
                if len(ovlap):
                    raise ValueError(f"The following DACs {ovlap} seem to be used both for clamping and synaptic stimulation")
            
                # 4.3 primary DACs CANNOT be used to emulate TTLs for 3ʳᵈ party devices in the same experiment
                ovlap = ttldacs & set(dacs)
                if len(ovlap):
                    raise ValueError(f"The following DACs {ovlap} seem to be used both for clamping and TTL emulation for 3ʳᵈ party devices")
                
                # 4.4 primary DACs CANNOT be used to send command signal waveforms
                # to other than the source (cell or membrane patch)
                ovlap = cmddacs & set(dacs)
                if len(ovlap):
                    raise ValueError(f"The following DACs {ovlap} seem to be used both for clamping and controlling 3ʳᵈ party devices")
                
            # 5. check that DIG channels do not overlap with those used for syn stim
            ovlap = digs & syndigs
            if len(ovlap):
                raise ValueError(f"The following DIGs {ovlap} seem to be used both for synaptic stimulation and triggering 3ʳᵈ party devices")
            
            # 6. in each Source, the SynapticStimulus objects must have unique names 
            # (but OK to share across sources)
            
            for k, s in enumerate(self._sources_):
                if isinstance(s.syn, typing.Sequence):
                    assert len(set(s_.name for s_ in s.syn)) == len(s.syn), f"{k}ᵗʰ source ({s.name}) has duplicate names for SynapticStimulus"
            
            #
            #### END   Checks
                
        self._episodeResults_ = dict()
        self._landmarks_ = dict()
        self._results_ = dict() 
        
        # stores the data received from Clampex 
        # ATTENTION 
        # Clampex sends one trial per ABF file → one neo.Block containing ALL 
        # data in a trial (i.e. segments = sweeps, each segment with same 
        # number of analogsignals); we need information in self._sources_ to
        # group accordingly.
        #
        # Epsiodes: 
        # A synaptic plasticity experiment occurs in three episodes (or stages):
        #
        # 1. baseline      — records the evolution of synaptic responses BEFORE
        #                   conditioning (see below); responses are recorded as 
        #                   analog signals via a specific ADC.
        #
        #                   Responses can be recorded on two synaptic pathways in
        #                   the same Source: e.g., a 'Test' pathway receiving the
        #                   conditioning protocol (see below), and a 'Control' 
        #                   pathway (not stimulated during conditioning).
        #
        #                   Responses in both pathways are recorded using the 
        #                   same electrode, but are evoked with TTL signals sent
        #                   via two distinct digital channels, two distinct DAC
        #                   channels (as analog signals emulating TTL pulses), 
        #                   or a combination of a digital and a DAC channel.
        #                   In order to distinguish the pathway origin of the
        #                   responses, the pathways are recorded in alternative 
        #                   sweeps (segments). 
        #
        #                   NOTE Clampex (pClamp) has no means to specify the 
        #                   particular sweeps when a given DIG (or DAC-emulated)
        #                   TTL should be output. However, Clampex does allow TWO 
        #                   alternative DIG outputs, with each one active on 
        #                   alternative sweeps — hence Clampex trials (written 
        #                   as ABF files) will contain recordings from one
        #                   pathway in odd-numbered sweeps, and from the other 
        #                   in even-numbered sweeps.
        #
        #                   NOTE: CED Signal is more flexible in this respect,
        #                   as it allows a definition of 'states', with each state
        #                   defining a set of 'pulses'; states can then be run in 
        #                   a user-defined sequence (a.k.a., 'protocol') such that
        #                   a given 'state' is applied every 𝒏 sweeps, or only
        #                   once, in a sweep of your choice, during a trial ⟹
        #                   one can in principle enure interleaved stimulation
        #                   of more than two pathways (provided the outputs are 
        #                   physically available).
        #
        #                   At the time of writing, this code supports only 
        #                   ABF/Clampex files.
        #
        # 2. conditioning  — the protocol (a combination of synaptic and postsynaptic
        #                   activity) used to induce (or attempt to induce) synaptic
        #                   plasticity at a defined synaptic pathway — i.e., the 
        #                   'Test' pathway.
        #
        #                   The electrical behaviour of the Source (cell or field)
        #                   is optionally recorded via the same ADC as the one
        #                   used to record the baseline responses. Obviously, when
        #                   recorded, the all sweeps of the trial will contain 
        #                   synaptic responses only from the conditioned pathway.
        #                   
        # 3. chase         — records synaptic responses AFTER conditioning — 
        #                   signal layout is identical to that of the baseline episode.
        # 
        
        # Data is organized by Source; for each Source we may have more than one
        # SynapticStimulus configuration
        
        # technically, Conditioning should only use ONE pathway; since an empty
        #       neo.Block does not use much resources, we leave this empty
        # 
        
        # set up data dictionary ⇒ to be populated with recorded data from ABF files
        # e.g.: {name1 ↦ {source         ↦ src,
        #
        #                 baseline       ↦ { 'path0' ↦ neo.Block,
        #                                    'path1' ↦ neo.block},
        #
        #                 conditioning   ↦ { 'path0' ↦ neo.Block,
        #                                    'path1' ↦ neo.block},
        #
        #                 chase          ↦ { 'path0' ↦ neo.Block,
        #                                    'path1' ↦ neo.block}
        #                },
        #
        #       name2 ↦ … as above …
        #       }
        #
        self._data_ = dict((src.name, dict((("source",          src),
                                            ("baseline",        dict(src.syn_blocks)),
                                            ("conditioning",    dict(src.syn_blocks)),
                                            ("chase",           dict(src.syn_blocks))))) for src in self._sources_)
        
        
        # place analysis results inside each episode sub-dict ⇒ do away with _episodeResults_
        
        self._runParams_ = DataBag(sources = self._sources_,
                                   data = self._data_,
                                   newEpisode = True,
                                   episodeName = None, # default is "baseline"
                                   abfRunTimesMinutes = list(),
                                   abfRunDeltaTimesMinutes = list(),
                                   baselineDurations = baselineDurations,
                                   steadyStateIClampMbTestDuration = steadyStateIClampMbTestDuration,
                                   trackingClampMode = trackingClampMode,
                                   conditioningClampMode = conditioningClampMode,
                                   useSlopeInIClamp = useSlopeInIClamp,
                                   signalBaselineStart = signalBaselineStart,
                                   signalBaselineDuration = signalBaselineDuration,
                                   currentProtocolIsConditioning = False,
                                   currentProtocol = None,
                                   useEmbeddedProtocol = useEmbeddedProtocol)
        
        
        # self._episode_ = "baseline"

        # TODO: 2024-01-08 00:04:55 FIXME
        # FINALIZE THIS !!!
        #
        
        # WARNING: 2023-10-05 12:10:40
        # below, all timings in self._landmarks_ are RELATIVE to the start of the sweep!
        # timings are stored as [start time, duration] (all Quantity scalars, with units of time)
        if self._runParams_.trackingClampMode == ephys.ClampMode.VoltageClamp:
            self._episodeResults_ = {"path0": {"Response0":[], "Response1":[], "PairedPulseRatio":[]},
                              "path1": {"Response0":[], "Response1":[], "PairedPulseRatio":[]},
                              "DC": [], "Rs":[], "Rin":[], }
            
            self._landmarks_ = {"Rbase":[self._runParams_.signalBaselineStart, self._runParams_.signalBaselineDuration], 
                                "Rs":[None, None], 
                                "Rin":[None, None], 
                                "PSCBase":[None, None],
                                            
                                "PSC0Peak":[None, None], 
                                "PSC1Peak":[None, None]}
    
        else:
            self._episodeResults_ = {"path0": {"Response0":[], "Response1":[], "PairedPulseRatio":[]},
                              "path1": {"Response0":[], "Response1":[], "PairedPulseRatio":[]},
                              "tau":[], "Rin":[], "Cap":[], }
            
            if self._runParams_.useSlopeInIClamp:
                self._landmarks_ = {"Base":[self._runParams_.signalBaselineStart, self._runParams_.signalBaselineDuration], 
                                    "VmTest":[None, None], 
                                    "PSP0Base":[None, None],
                                    "PSP0Peak":[None, None],
                                    "PSP1Base":[None, None],
                                    "PSP1Peak":[None, None]}
            else:
                self._landmarks_ = {"Base":[self._runParams_.signalBaselineStart, self._runParams_.signalBaselineDuration], 
                                    "VmTest":[None, None], 
                                    "PSPBase":[None, None],
                                    "PSP0Peak":[None, None],
                                    "PSP1Peak":[None, None]}
        
                
        #### BEGIN about ABF epochs

        # expected epochs layout (and order):
        #
        # Role                              ABF Epoch                   Comments
        # ======================================================================
        # baseline (for DC, Rs and Rin)     A or None                   When None use DAC holding time
        #
        # membrane test                     B (when A present)          Can be AFTER synaptic response
        #
        # synaptic baseline                 C (when A, B present)       Can be the baseline when mb test AFTER syn resp
        #
        # synaptic response                 D (1 or 2 pulses DIG train) The first epoch with a DIG train


        # just one Epoch;
        # • if ABF Epoch, then it needs to be the first one, type Step,
        #   ∘ first duration > 0, delta duration == 0
        #   ∘ first level == 0, delta level == 0
        # • if NOT an ABF epoch then:
        #   ∘ by default corresponds to the DAC holding time
        #
        self._baselineEpoch_ = None

        # just one epoch:
        # for voltage clamp needs:
        # • type Step,
        # • first duration > 0
        # • delta duration == 0
        # • first level != 0
        # • delta level == 0
        #
        self._membraneTestEpoch_ = None

        # baseline before 1ˢᵗ synaptic stimulation below
        #   it must STOP before  1ˢᵗ synaptic stimulation below
        #   MAY be the same as baseline if membrane test comes AFTER the last
        #       synaptic response epoch (as is usual in current clamp)
        #
        self._synapticBaselineEpoch_ = None

        # list of one or two epochs
        # 1) the 1ˢᵗ (and possibly, the only) one is the stimulation for the 1ˢᵗ
        #   synaptic response
        # 2) the 2ⁿᵈ (if present) is the stimulation for the 2ⁿᵈ synaptic response
        #
        self._synapticStimulationEpochs = list()

        #### END   about ABF epochs

        self._signalAxes_ = dict(path0 = None, path1 = None)

        self._presynaptic_triggers_ = dict()

        # ### BEGIN set up emitter window and viewers
        #
        # NOTE: 2023-10-07 11:20:22
        # _emitterWindow_ needed here, to set up viewers
        wsp = wf.user_workspace()
        
        if emitterWindow is None:
            self._emitterWindow_ = wsp["mainWindow"]

        elif type(emitterWindow).__name__ != 'ScipyenWindow':
            raise ValueError(f"Expecting an instance of ScipyenWindow; instead, got {type(emitterWindow).__name__}")

        else:
            self._emitterWindow_ = emitterWindow

        if directory is None:
            self._watchedDir_ = pathlib.Path(self._emitterWindow_.currentDir).absolute()
            
        elif isinstance(directory, str):
            self._watchedDir_ = pathlib.Path(directory)

        elif isinstance(directory, pathlib.Path):
            self._watchedDir_ = directory
            
        else:
            raise TypeError(f"'directory' expected to be a str, a pathlib.Path, or None; instead, got {type(directory).__name__}")
        
        synapticViewer0 = sv.SignalViewer(parent=self._emitterWindow_, scipyenWindow = self._emitterWindow_, win_title = "path0 Recording")
        synapticViewer0.annotationsDockWidget.hide()
        synapticViewer0.cursorsDockWidget.hide()
        
        synapticViewer1 = sv.SignalViewer(parent=self._emitterWindow_, scipyenWindow = self._emitterWindow_, win_title = "path1 Recording")
        synapticViewer1.annotationsDockWidget.hide()
        synapticViewer1.cursorsDockWidget.hide()
        
        resultsViewer = sv.SignalViewer(parent=self._emitterWindow_, scipyenWindow = self._emitterWindow_, win_title = "Analysis")
        resultsViewer.annotationsDockWidget.hide()
        resultsViewer.cursorsDockWidget.hide()
        
        self._viewers_ = dict(path0 = synapticViewer0,
                              path1 = synapticViewer1,
                              results = resultsViewer)
        
        #
        # ### END set up emitter window and viewers
        
        self._abfRunBuffer_ = collections.deque()
        
        self._abfProcessorThread_ = _LTPOnlineFileProcessor_(self, 
                                                             self._abfRunBuffer_,
                                                             self._runParams_,
                                                             self._presynaptic_triggers_, 
                                                             self._landmarks_,
                                                             self._data_, 
                                                             self._results_, 
                                                             self._viewers_)
        
        self._simulation_ = None
        
        self._simulatorThread_ = None
        
        self._doSimulation_ = False
        
        self._simulator_params_ = dict(files=None, timeout=_LTPFilesSimulator_.defaultTimeout)
        
        self._running_ = False
        
        if isinstance(simulate, dict):
            files = simulate.get("files", None)
            timeout = simulate.get("timeout", 2000) # ms
            if isinstance(files, (tuple,list)) and len(files) > 0 and all(isinstance(v, str) for v in files):
                self._simulator_params_ = dict(files=files, timeout=timeout)
                self._doSimulation_ = True
                
        elif isinstance(simulate, bool):
            self._doSimulation_ = simulate
            
        elif isinstance(simulate, (int, float)):
            self._doSimulation_ = True
            self._simulator_params_ = dict(files=None, timeout = int(simulate))
        
        if self._doSimulation_:
            self._simulatorThread_ = _LTPFilesSimulator_(self, self._simulator_params_)
            self._abfSupplierThread_ = _LTPOnlineSupplier_(self, self._abfRunBuffer_,
                                        self._emitterWindow_, self._watchedDir_,
                                        simulator = self._simulatorThread_)
            
        else:
            self._abfSupplierThread_ = _LTPOnlineSupplier_(self, self._abfRunBuffer_,
                                        self._emitterWindow_, self._watchedDir_)
        
        self._abfSupplierThread_.abfRunReady.connect(self._abfProcessorThread_.processAbfFile,
                                                     QtCore.Qt.QueuedConnection)
        
        if autoStart:
            self._abfSupplierThread_.start()
            self._abfProcessorThread_.start()
            self._running_ = True

    def __del__(self):
        if self._running_:
            self.stop()
        try:
            for viewer in self._viewers_.values():
                viewer.close()
            if self._emitterWindow_.isDirectoryMonitored(self._watchedDir_):
                self._emitterWindow_.enableDirectoryMonitor(self._watchedDir_, False)
            if isinstance(self._simulatorThread_, _LTPFilesSimulator_):
                self._simulatorThread_.requestInterruption()
                self._simulatorThread_.quit()
                self._simulatorThread_.wait()
                self._simulatorThread_.deleteLater()
            self._abfSupplierThread_.abfListener.stop()
            self._abfSupplierThread_.quit()
            self._abfSupplierThread_.wait()
            self._abfProcessorThread_.quit()
            self._abfProcessorThread_.wait()
                
            self._abfSupplierThread_.deleteLater()
            self._abfProcessorThread_.deleteLater()
            
        except:
            traceback.print_exc()
        
        if hasattr(super(object, self), "__del__"):
            super().__del__()
            
    @pyqtSlot()
    def doWork(self):
        self.start()

    @property
    def data(self) -> dict:
        return self._data_
    
    def stop(self):
        if self._doSimulation_ and isinstance(self._simulatorThread_, _LTPFilesSimulator_):
            self._simulatorThread_.requestInterruption()
            self._simulatorThread_.quit()
            self._simulatorThread_.wait()
            
        if isinstance(self._abfSupplierThread_, FileStatChecker):
            self._abfSupplierThread_.abfListener.stop()
            
            
        self._abfSupplierThread_.quit()
        self._abfSupplierThread_.wait()
        self._abfProcessorThread_.quit()
        self._abfProcessorThread_.wait()
        
        if self._emitterWindow_.isDirectoryMonitored(self._watchedDir_):
            self._emitterWindow_.enableDirectoryMonitor(self._watchedDir_, False)
            
        self.resultsReady.emit((self._data_, self._results_))
        
        self._running_ = False
        
    def reset(self):
        # self._monitorProtocol_ = None
        # self._conditioningProtocol_ = None
        
        self._data_["baseline"]["path0"].segments.clear()
        self._data_["baseline"]["path1"].segments.clear()
        self._data_["chase"]["path0"].segments.clear()
        self._data_["chase"]["path1"].segments.clear()
        self._data_["conditioning"]["path0"].segments.clear()
        self._data_["conditioning"]["path1"].segments.clear()
        
        if self._clampMode_ == ephys.ClampMode.VoltageClamp:
            self._results_ = {"path0": {"Response0":[], "Response1":[], "PairedPulseRatio":[]},
                              "path1": {"Response0":[], "Response1":[], "PairedPulseRatio":[]},
                              "DC": [], "Rs":[], "Rin":[], }
            
            self._landmarks_ = {"Rbase":[self._signalBaselineStart_, self._signalBaselineDuration_], 
                                "Rs":[None, None], 
                                "Rin":[None, None], 
                                "PSCBase":[None, None],
                                            
                                "PSC0Peak":[None, None], 
                                "PSC1Peak":[None, None]}
    
        else:
            self._results_ = {"path0": {"Response0":[], "Response1":[], "PairedPulseRatio":[]},
                              "path1": {"Response0":[], "Response1":[], "PairedPulseRatio":[]},
                              "tau":[], "Rin":[], "Cap":[], }
            
            if self._useSlopeInIClamp_:
                self._landmarks_ = {"Base":[self._signalBaselineStart_, self._signalBaselineDuration_], 
                                    "VmTest":[None, None], 
                                    "PSP0Base":[None, None],
                                    "PSP0Peak":[None, None],
                                    "PSP1Base":[None, None],
                                    "PSP1Peak":[None, None]}
            else:
                self._landmarks_ = {"Base":[self._signalBaselineStart_, self._signalBaselineDuration_], 
                                    "VmTest":[None, None], 
                                    "PSPBase":[None, None],
                                    "PSP0Peak":[None, None],
                                    "PSP1Peak":[None, None]}
        
                
        for viewer in self._viewers_.values():
            viewer.clear()
            

    def start(self, directory:typing.Optional[typing.Union[str, pathlib.Path]] = None):
        if self._running_:
            print("Already started")
            return

        if directory is None:
            if self._watchedDir_ is None:
                self._watchedDir_ = pathlib.Path(self._emitterWindow_.currentDir).absolute()

        elif isinstance(directory, str):
            self._watchedDir_ = pathlib.Path(directory)

        elif isinstance(directory, pathlib.Path):
            self._watchedDir_ = directory

        else:
            raise TypeError(f"'directory' expected to be a str, a pathlib.Path, or None; instead, got {type(directory).__name__}")
    

        # self._pending_.clear() # pathlib.Path are hashable; hence we use the RSV ↦ ABF

        self._latestAbf_ = None # last ABF file to have been created by Clampex

        if not self._doSimulation_ or not isinstance(self._simulatorThread_, _LTPFilesSimulator_):
            if self._abfSupplierThread_._dirMonitor_.directory != self._watchedDir_:
                self._abfSupplierThread_._dirMonitor_.directory = self._watchedDir_
                
            if not self._emitterWindow_.isDirectoryMonitored(self._watchedDir_):
                self._emitterWindow_.enableDirectoryMonitor(self._watchedDir_, True)
            
        self._abfSupplierThread_.start()
        self._abfProcessorThread_.start()
        
        self._running_ = True
            
def generate_synaptic_plasticity_options(npathways, mode, /, **kwargs):
    """Constructs a dict with options for synaptic plasticity experiments.
    
    Positional parameters:
    ======================
    npathways: int - the number of pathways recorded from - must be >= 1
        
    mode: int, one of 0, 1, 2 or str, one of "voltage", "current", or "field"
    
    Var-keyword parameters:
    =======================
    "pathways": dict with pathway designation, mapping a str (pathway type)
        to int (pathway index)
        
        e.g. {"test":0, "control":1, "ripples": 2, etc}
        
        default is {"test":0, "control":1}
        
        The keys must contain at least "test".
        
        The indices must be valid given the number of pathways in npathways
        
    "cursors": dict with vertical cursor coordinates for each pathway where 
        measurements are made, this must contain the following key-value pairs
        (default values are show below):
        
        "Labels" = ["Rbase", "Rs", "Rin", "EPSC0Base", "EPSC0Peak", "EPSC1Base", "EPSC1Peak"]
        "Windows" = [0.01, 0.003, 0.01, 0.01, 0.005, 0.01, 0.005]
        "Pathways" = [
                        [0.06, 0.066, 0.16, 0.26, 0.28, 0.31, 0.33],
                        [5.06, 5.066, 5.16, 5.26, 5.28, 5.31, 5.33]]
    
    "average":int = number of consecutive single-run trials to average 
        off-line (default: 6).
        
        NOTE: Any value < 2 indicates no off-line averaging. 
        
    "every":int   = number of consecutive single-run trials to skip before next 
        offline average (default: 6)
        
        NOTE: This is only considered when average is >= 2
        
    "reference":int  = number of minute-average responses used to assess 
        plasticity; this is the number of reponses at the end of the chase
        stage, and it equals the number of responses at the end of the baseline
        stage. Therefore it cannot be larger than the duration of the baseline 
        stage, in minutes.
        
        Default is 5 (i.e. compare the average of the last 5 minute-averaged 
            responses of the chase stage, to the average of the last 5 
            minute-averaged responses of the baseline stage, in each pathway)
            
            
    "cursor_measures": dict = cursor-based measurements used in analysis.
        Can be empty.
        
        Each key is a str (measurement name) that is mapped to a nested dict 
            with the following keys:
        
            "function": a cursor-based signal function as defined in the 
                ephys module, or membrane module
            
                function(signal, cursor0, cursor1,...,channel) -> Quantity
            
                The function accepts a neo.AnalogSignal or datatypes.DataSignal
                as first parameter, 
                followed by any number of vertical SignalCursor objects
                
                The functions must be defined and present in the scope therefore
                they can be specified as module.function, unless imported 
                directly in the workspace where ltp analysis is performed.
            
                Examples: 
                ephys.cursors_chord_slope()
                ephys.cursors_difference()
                ephys.membrane.cursor_Rs_Rin()
            
            "cursors": list of (x, xwindow, label) triplets that specify
             notional vertical signal cursors
                
                NOTE: SignalCursor objects cannot be serialized. Therefore, in 
                order for the options to be persistent, the cursors have to be
                represented by their parameter tuple (time, window) which can be
                stored on disk, and used to generate a cursor at runtime.
                
            "channel": (optional) if present, it must contain an int, which is
                the index of the signal where the cursors are used
            
            "pathway": int, the index of the pathway where the measurement is
                performed, or None (applied to both pathways)
                
        "epoch_measures": dict: epoch-based measurements
            Can be empty.
            
            Has a similar structure to cursor_measures, but uses epoch-based
            measurement functions instead.
            
            "function": epoch-based signal function as defined in the ephys and
                membrane modules
                
            "epoch": a single neo.Epoch (they can be serialized) or the tuple
                (times, durations, labels, name) with arguments suitable to 
                construct the Epoch at run time.
            
            Examples:
            ephys.epoch_average
        
    "Im": str, int: name or index of the signal carrying synaptic responses (epscs, for
        voltage-clamp experiments) or command current (for current-clamp experiments)
        
        Default is 0
        
        NOTE: This signal must be present in all sweeps!
        
    "Vm": str, int: name or index of the signal carrying command voltage (for 
        voltage-clamp experiments) or synaptic responses (epsp, for current-clamp experiments)
        
        Default is 1
        
        NOTE: This signal must be present in all sweeps!
        
    "stim": list of signal names or indices containing the digital triggers 
        for the recorded pathways (e.g. 1st is for pathway 0, etc)
    
        Default is [2]
    
    Description
    ============
        
    The function constructs an options dict specifying synaptic pathways, 
    analysis cursors and optional minute-by-minute averaging of data from 
    synaptic plasticity experiments.
    
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
    6. Heuristic for cursors set up (single or paired pulse?); voltage clamp,
        current clamp,, or field recordings (we calculate Rs Rin only for voltage-clamp)
        
        
    """
    
    recording_types = {1:"voltage",2:"current", 3:"field"}
    
    if npathways < 1:
        raise ValueError(f"Expecting at least one pathway; got {npathways} instead")
    
    if isinstance(mode, str):
        if mode not in ("voltage", "current", "field"):
            raise ValueError(f"Invalid mode; expecting one of 'voltage', 'current', 'field'; got {mode} instead")
        
    elif isinstance(mode, int):
        if mode not in [1,2,3]:
            raise ValueError(f"Invalid mode; expecting 1, 2, or 3; got {mode} instead")
        
        mode = recording_types[mode]
        
    else:
        raise TypeError(f"Invalid mode type; expecting a str or int; got {type(mode).__name__} instead")
    
    # field = kwargs.pop("field", False)
#     
#     test_pathway_index = kwargs.pop("test", 0)
#     
#     if test_pathway_index < 0 or test_pathway_index >= npathways:
#         raise ValueError(f"Invalid test path index {test_pathway_index}; expecting a value between 0 and {npathways-1}")
#     
#     control_pathway_index = kwargs.pop("control", None)
#     
#     if npathways >= 2:
#         if control_path is None:
#             control_path = 1 if test_path == 0 else 0
#         elif control_path == test_path:
#             raise ValueError(f"control path cannot have the same index ({control_path}) as the test path index ({test_path})")
#     else:
#         control_path = None
        
#     if isinstance(control_path, int):
#         if control_path < 0 or control_path > 1:
#             raise ValueError("Invalid control path index (%d) expecting 0 or 1" % control_path)
#         
#         if control_path == test_path:
#             raise ValueError("Control path index must be different from the test path index (%d)" % test_path)
    
    average = kwargs.pop("average", 6)
    average_every = kwargs.pop("every", 6)
    
    reference = kwargs.pop("reference", 5)
    
    measure = kwargs.pop("measure", "amplitude")
    
    default_cursors_dict = dict()
    
    default_cursors_dict["Labels"] = ["Rbase", "Rs", "Rin", "EPSC0Base", "EPSC0Peak", "EPSC1Base", "EPSC1Peak"]
    default_cursors_dict["Windows"] = [0.01, 0.003, 0.01, 0.01, 0.005, 0.01, 0.005]
    default_cursors_dict["Pathways"] = list()
    default_cursors_dict["Pathways"].append([0.06, 0.066, 0.16, 0.26, 0.28, 0.31, 0.33])
    default_cursors_dict["Pathways"].append([c + 5 for c in default_cursors_dict["Pathways"][0]])
    
    cursors = kwargs.pop("cursors", default_cursors_dict)
    if len(cursors) == 0:
        raise ValueError(f"cursors must be specified")
    
    default_pathways = {"test":0}
    if npathways > 1:
        default_pathways["control"] = 1
    
    pathways = kwargs.pop("pathways", default_pathways)
    
    if "test" not in pathways.keys():
        raise ValueError("The index of the test pathway must be specified")

    if max(pathways.values()) >= npathways:
        raise ValueError(f"Invalid pathway value {max(pathways.values())} for {npathways} pathways")
    
    Im = kwargs.pop("Im", 0)
    Vm = kwargs.pop("Vm", 1)
    stim = kwargs.pop("stim", list())
    
    if len(stim) > npathways:
        raise ValueError(f"When specified, triggers must have the same length as the number of pathways or less")
    
    pathways_conf = list()

    for k in range(npathways):
        path = {"Im":Im, "Vm": Vm}
        
        if k < len(stim):
            path["stim"] = stim[k]
            
        if k < len(cursors["Pathways"]):
            path["cursors"] = cursors["Pathways"][k]
            
        path["assignment"] = reverse_mapping_lookup(pathways, k)
        
        pathways_conf.append(path)

    signals = [Im, Vm]
    signals.extend(stim)
    
    LTPopts = dict()
    
    LTPopts["Average"] = {'Count': average, 'Every': average_every}
    LTPopts["Pathways"] = pathways_conf

    LTPopts["Reference"] = reference
    
    LTPopts["Signals"] = signals
    
    LTPopts["Cursors"] = dict()
    LTPopts["Cursors"]["Labels"]  = cursors["Labels"]
    LTPopts["Cursors"]["Windows"] = cursors["Windows"]
    
    
#     if mode=="field":
#         LTPopts["Signals"] = kwargs.get("Signals",['Vm_sec_1'])
#         
#         if len(cursors):
#             LTPopts["Cursors"] = cursors
#             
#         else:
#             LTPopts["Cursors"] = {"fEPSP0_10": (0.168, 0.001), 
#                                   "fEPSP0_90": (0.169, 0.001)}
#             
#             #LTPopts["Cursors"] = {'Labels': ['fEPSP0','fEPSP1'],
#                                 #'time': [0.168, 0.169], 
#                                 #'Pathway1': [5.168, 5.169], 
#                                 #'Windows': [0.001, 0.001]} # NOTE: cursor windows are not used here
#             
#         
#     else:
#         LTPopts["Signals"] = kwargs.get("Signals",['Im_prim_1', 'Vm_sec_1'])
#         LTPopts["Cursors"] = {'Labels': ['Rbase','Rs','Rin','EPSC0Base','EPSC0Peak','EPSC1Base','EPSC1peak'],
#                               'Pathway0': [0.06, 0.06579859882206893, 0.16, 0.26, 0.273, 0.31, 0.32334583993039734], 
#                               'Pathway1': [5.06, 5.065798598822069,   5.16, 5.26, 5.273, 5.31, 5.323345839930397], 
#                               'Windows': [0.01, 0.003, 0.01, 0.01, 0.005, 0.01, 0.005]}
#         
    
    return LTPopts
    
def generate_LTP_options(cursors, signal_names, path0, path1, baseline_minutes, 
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
    
    Failing that, one can use Vm=True in further analyses and supply the value of the test Vm pulse in 
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
def load_synaptic_plasticity_options(LTPOptionsFile:[str, type(None)]=None, 
                                     **kwargs):
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
    
    if len(kwargs) == 0 and (LTPOptionsFile is None or len(LTPOptionsFile.strip()) == 0):
        LTPOptionsFile = os.path.join(os.path.dirname(__file__), "options", "LTPOptions.pkl")
    
    if LTPOptionsFile is None or not os.path.isfile(LTPOptionsFile):
        
        LTPopts = generate_synaptic_plasticity_options(**kwargs)
        
        print("Now, save the options as %s" % os.path.join(os.path.dirname(__file__), "options", "LTPOptions.pkl"))
        
        #raise RuntimeError("No options file found. Have you ever run save_LTP_options ?")
    else:
        with open(LTPOptionsFile, "rb") as fileSrc:
            LTPopts = pickle.load(fileSrc)
        
    return LTPopts

@safeWrapper
def generate_minute_average_data_for_LTP(prefix_baseline, prefix_chase, 
                                         LTPOptions, test_pathway_index, result_name_prefix):
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
                                                segments = LTPOptions["Pathway0"],
                                                analogsignals = LTPOptions["Signals"],
                                                name = result_name_prefix + "_path0_baseline"),
                    neoutils.concatenate_blocks(baseline_blocks,
                                                segments = LTPOptions["Pathway1"],
                                                analogsignals = LTPOptions["Signals"],
                                                name = result_name_prefix + "_path1_baseline")]
    else:
        baseline    = [neoutils.average_blocks(baseline_blocks,
                                            segment = LTPOptions["Pathway0"],
                                            analog = LTPOptions["Signals"],
                                            count = LTPOptions["Average"]["Count"],
                                            every = LTPOptions["Average"]["Every"],
                                            name = result_name_prefix + "_path0_baseline"),
                    neoutils.average_blocks(baseline_blocks,
                                            segment = LTPOptions["Pathway1"],
                                            analog = LTPOptions["Signals"],
                                            count = LTPOptions["Average"]["Count"], 
                                            every = LTPOptions["Average"]["Every"], 
                                            name = result_name_prefix + "_path1_baseline")]
              
    baseline[test_pathway_index].name += "_Test"
    baseline[1-test_pathway_index].name += "_Control"
    
    
    if LTPOptions["Average"] is None:
        chase   = [neoutils.concatenate_blocks(chase_blocks,
                                                segments = LTPOptions["Pathway0"],
                                                analogsignals = LTPOptions["Signals"],
                                                name = result_name_prefix + "_path0_chase"),
                   neoutils.concatenate_blocks(chase_blocks,
                                                segments = LTPOptions["Pathway1"],
                                                analogsignals = LTPOptions["Signals"],
                                                name = result_name_prefix + "_path1_chase")]
        
    else:
        chase   = [neoutils.average_blocks(chase_blocks,
                                            segment = LTPOptions["Pathway0"], 
                                            analog = LTPOptions["Signals"],
                                            count = LTPOptions["Average"]["Count"], 
                                            every = LTPOptions["Average"]["Every"],
                                            name = result_name_prefix + "_path0_chase"),
                   neoutils.average_blocks(chase_blocks,
                                            segment = LTPOptions["Pathway1"], 
                                            analog = LTPOptions["Signals"],
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
    Calculates the slope of field EPSPs. TODO
    
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
        singal_index = ephys.get_index(block, signal_index)
        
    for k, seg in enumerate(block.segments):
        pass
    
def calculate_LTP_measures_in_block(block: neo.Block, 
                                    signal_index_Im, /, 
                                    signal_index_Vm = None, 
                                    trigger_signal_index = None,
                                    testVm = None, 
                                    epoch = None, 
                                    stim = None,
                                    isi = None,
                                    out_file=None) -> pd.DataFrame:
    """
    Calculates membrane Rin, Rs, and EPSC amplitudes in whole-cell voltage clamp.
    
    Parameters:
    ==========
    block: a neo.Block; must contain one analogsignal each for Im and Vm;
        these signals must be found at the same indices in each segment's list
        of analogsignals, throughout the block.
    
    signal_index_Im: (str, int) Name or index of the Im signal
    
    signal_index_Vm: (str, int, None) Optional (default None).
        Name or index of the Vm signal
        
    trigger_signal_index: (str, int, None) Optional (default None)
    
    Vm: (float, None) Optional (default None)
        When a float, this is taken to be the actual amplitude of the depolarizing
        VM test pulse. 
        
        When None, the amplitude of the test pulse is inferred from the Vm signal
        (selected using the signal_index_Vm given above)
        
    epoch: neo.Epoch (optional, default None)
        This must contain 5 or 7 intervals (Epochs) defined and named as follows:
        Rbase, Rs, Rin, EPSC0base, EPSC0peak (optionally, EPSC1base, EPSC1peak)
        
        When None, then this epoch is supposed to exist (embedded) in every
        segment of the block.
        
    
        
    Returns:
    ---------
    NOTE: 2020-09-30 14:56:00 API CHANGE
    
    A pandas DataFrame with the following columns:
    Rs, Rin, DC, EPSC0, and optionally, EPSC1, PPR, and ISI
    
    NOTE: 2017-04-29 22:41:16 API CHANGE
    Returns a dictionary with keys as follows:
    
    (Rs, Rin, DC, EPSC0) - if there are only 5 intervals in the epoch
    
    (Rs, Rin, DC, EPSC0, EPSC1, PPR) - if there are 7 intervals defined in the epoch
    
    Where EPSC0 and EPSC1 are EPSc amplitudes, and PPR is the paired-pulse ratio (EPSC1/EPSC0)
    
    """
    Idc = list()
    Rs     = list()
    Rin    = list()
    EPSC0  = list()
    EPSC1  = list()
    PPR    = list()
    ISI    = list()
    
    ui = None
    ri = None
    
    # print(f"calculate_LTP_measures_in_block signal_index_Im, {signal_index_Im}")
    
    if isinstance(signal_index_Im, str):
        signal_index_Im = ephys.get_index_of_named_signal(block, signal_index_Im)
        
    # print(f"calculate_LTP_measures_in_block signal_index_Im, {signal_index_Im}")
    
    if isinstance(signal_index_Vm, str):
        signal_index_Vm = ephys.get_index_of_named_signal(block, signal_index_Vm)
        
    if isinstance(trigger_signal_index, str):
        trigger_signal_index = ephys.get_index_of_named_signal(block, trigger_signal_index)
        
    for (k, seg) in enumerate(block.segments):
        #print("segment %d" % k)
        if isinstance(signal_index_Im, (tuple, list)):
            im_signal = signal_index_Im[k]
        else:
            im_signal = signal_index_Im
            
        if isinstance(signal_index_Vm, (tuple, list)):
            vm_signal = signal_index_Vm[k]
        else:
            vm_signal = signal_index_Vm
            
        (irbase, rs, rin, epsc0, epsc1, ppr, isi_) = segment_synplast_params_v_clamp(seg, 
                                                                                    im_signal, 
                                                                                    signal_index_Vm=vm_signal, 
                                                                                    trigger_signal_index=trigger_signal_index,
                                                                                    testVm=testVm, 
                                                                                    stim=stim,
                                                                                    isi=isi,
                                                                                    epoch=epoch)
        ui = irbase.units
        ri = rs.units
        
        Idc.append(np.atleast_1d(irbase))
        Rs.append(np.atleast_1d(rs))
        Rin.append(np.atleast_1d(rin))
        EPSC0.append(np.atleast_1d(epsc0))
        EPSC1.append(np.atleast_1d(epsc1))
        PPR.append(np.atleast_1d(ppr))
        ISI.append(np.atleast_1d(isi_))

    ret = dict()
    
    ret["Rs"]       = np.concatenate(Rs) * Rs[0].units
    #print("Rin", Rin)
    ret["Rin"]      = np.concatenate(Rin) * Rin[0].units
    ret["DC"]       = np.concatenate(Idc) * Idc[0].units
    ret["EPSC0"]    = np.concatenate(EPSC0) * EPSC0[0].units
    
    EPSC1_array     = np.concatenate(EPSC1) * EPSC1[0].units
    PPR_array       = np.concatenate(PPR) # dimensionless
    ISI_array       = np.concatenate(ISI) * ISI[0].units
    
    if not np.all(np.isnan(EPSC1_array)):
        ret["EPSC1"] = EPSC1_array
        ret["PPR"]   = PPR_array
        ret["ISI"]   = ISI_array
        
        
    result = pd.DataFrame(ret)
    
    if isinstance(out_file, str):
        result.to_csv(out_file)
        
    return result


def segment_synplast_params_i_clamp(s: neo.Segment, 
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
    

    
def segment_synplast_params_v_clamp(s: neo.Segment, 
                                       signal_index_Im: int,
                                       signal_index_Vm: typing.Optional[int]=None,
                                       trigger_signal_index: typing.Optional[int] = None,
                                       testVm: typing.Union[float, pq.Quantity, None]=None,
                                       epoch: typing.Optional[neo.Epoch]=None,
                                       stim: typing.Optional[TriggerEvent]=None,
                                       isi:typing.Union[float, pq.Quantity, None]=None) -> tuple:
    """
    Calculates several signal measures in a synaptic plasticity experiment.
    
    See NOTE further below, for details about these parameters.
    
    Parameters:
    ----------
    s:neo.Segment
        The segment must contain one analog signal with the recording of the
        membrane current.
        
        Optionally, the segment may also contain:
        
        1) An analog signal containing the recorded membrane potential (in 
            Axon amplifiers this is usually the secondary output of the recording
            channel, in voltage-clamp configuration).
        
            When present, this is used to determine the amplitude of the 
            depolarizing test pulse, which is used to calculate Rs and Rin.
        
            WARNING 
            The function expects such a test pulse to be present in every sweep
            (segment), delivered shortly after the sweep onset, and typically 
            BEFORE the synaptic stimulus. This test pulse can also be delivered 
            towards the end of the sweep, after the synaptic responses. 
            
            Rs and Rin are calculated based on three mandatory intervals ("Rbase",
            "Rs" and "Rin") with their onset times set to fall before, and 
            during the test pulse defined inside the epoch parameter (or embedded in 
            the segment, see below).  The onset times for these intervals should
            be within the test pulse.
            
            The test puIf a depolarizing test pulse is absent, the calculated
        Rs and Rin values will make no sense.
        
        When absent, then the amplitude of such a test pulse MUST be given as a
        separate parameter ("testVm") see below.
        
        1) a neo.Epoch named "LTP" (case-insensitive) with intervals as defined
            in the NOTE further below - used to determine the regions of the 
            membrane current signal where measurements are made.
        
            When such an Epoch is missing, then it must be supplied as an 
            addtional parameter.
        
    signal_index_Im: int 
        Index into the segment's "analogsignals" collection, for the signal
        containing the membrane current.
        
    signal_index_Vm: int 
        Optional (default is None).
        Index into the segment's "analogsignals" collection, for the signal
        containing the recorded membrane potential
        
        ATTENTION: Either signal_index_Vm, or Vm (see below) must be specified and
            not None.
        
    trigger_signal_index: int
        Optional (default is None)
        Index of the signal containing the triggers for synaptic stimulation.
        Useful to determine the time of the synaptic stimulus and the inter-stimulus
        interval (when appropriate).
    
    testVm: scalar float or Python Quantity with units of membrane potential 
        (V, mV, etc)
        Optional (default is None).
        The amplitude of the Vm test pulse.
        
        ATTENTION: Either signal_index_Vm, or Vm must be specified and not None.
        
    stim: TriggerEvent 
        Optional, default is None.
        
        This must be a presynaptic trigger event (i.e. stim.event_type equals
        TriggerEventType.presynaptic) with one or two elements, corresponding to
        the first and, optionally, the second synaptic stimulus trigger.
        
        When present, it will be used to determine the inter-stimulus interval.
        
        When absent, the interstimulus interval can be manually specified ("isi"
        parameter, below) or detected from a trigger signal (specified using the
        "trigger_signal_index" parameter, see above).
        
    epoch: neo.Epoch
        Optional (default is None).
        When present, indicates the segments of the membrane current signal 
        where the measures are determined -- see NOTE, below, for details.
        
        ATTENTION: When None, the neo.Segment "s" is expected to contain a
        neo.Epoch with intervals defined in the NOTE below.
        
    isi: scalar float or Python Quantity, or None.
        Optional (default is None).
        When None but either trigger_signal_index or stim parameters are specified
        then inter-stimulius interval is determined from these.
        
        
    Returns:
    --------
    
    A tuple of scalars (Idc, Rs, Rin, EPSC0, EPSC1, PPR, ISI) where:
    
    Idc: scalar Quantity = the baseline (DC) current (measured at the Rbase epoch
            interval, see below)
    
    Rs: scalar Quantity = Series (access) resistance
    
    Rin: scalar Quantity = Input resistance
    
    EPSC0: scalar Quantity = Amplitude of first synaptic response.
    
    EPSC1: scalar Quantity = Amplitude of second synaptic response in
            paired-pulse experiments,
            
            or np.nan in the case of single-pulse experiments
            
            In either case the value has membrane current units.
            
    PPR: float scalar = Paired-pulse ratio (EPSC0 / EPSC1, for paired-pulse experiments)
            or np.nan (single-pulse experiments)
            
    ISI: scalar Quantity;
        This is either the value explicitly given in the "isi" parameter or it
        is calculated from the "stim" parameter, or is determined from a trigger
        signal specified with "trigger_signal_index".
        
        When neither "isi", "stim" or "trigger_signal_index" are specified, then
        ISI is returned as NaN * time units associated with the membrane current
        signal.
        
        
    NOTE:
    There are two groups of signal measures:
    
    a) Mandatory measures:
        The series resistance (Rs), the input resistance (Rin), and the amplitude
        of the (first) synaptic response (EPSC0)
    
    b) Optional measures - only for paired-pulse experiments:
        The amplitude of the second synaptic response (EPSC1) and the paired-pulse
        ratio (PPR = EPSC1/EPSC0)
        
    The distinction between single- and paired-pulse stimulation is obtained 
    from the parameter "epoch", which must contain the following intervals or
    regions of the Im signal:
    
    Interval        Mandatory/  Time onset                  Measurement:
    #   label:      Optional:
    ============================================================================
    1   Rbase       Mandatory   Before the depolarizing     Baseline membrane current
                                test pulse.                 to calculate Rs & Rin.
                                                        
    2   Rs          Mandatory   Just before the peak of     The capacitive current
                                the capacitive current      at the onset of the
                                and after the onset of      depolarizing test pulse.
                                the depolarizing test       (to calculate series 
                                pulse.                      resistance).
                                                    
    3   Rin         Mandatory   Towards the end of the      Steady-state current
                                depolarizing pulse.         during the depilarizing
                                                            tets pulse (to calculate
                                                            input resistance).
                                
    4   EPSC0Base   Mandatory   Before the stimulus         Im baseline before  
                                artifact of the first       the first synaptic
                                presynaptic stimulus.       response (to calculate
                                                            amplitude of the first 
                                                            EPSC)
                                
        
    5   EPSC0Peak   Mandatory   At the "peak" (or, rather   Peak of the (first)  
                                "trough") of the first      EPSC (to calculate
                                EPSC                        EPSC amplitude).
                                
    6   EPSC1Base   Optional    Before the stimulus         Im baseline before  
                                artifact of the second      the second synaptic
                                presynaptic stimulus.       response (to calculate
                                                            amplitude of the 2nd 
                                                            EPSC and PPR)
        
    7   EPSC1Peak   Optional    At the "peak" (or, rather   Peak of the 2nd  
                                "trough") of the 2nd        EPSC (to calculate
                                EPSC                        2nd EPSC amplitude
                                                            and PPR).
    
    The labels are used to locate the appropriate signal regions for each 
    measurement and are case-sensitive.
    
    Epochs with 5 intervals are considered to belong to a single-pulse experiment.
    A paired-pulse experiment is represented by an epoch with 7 intervals.
    
    The intervals (and the epoch) can be constructed manually, or visually using
    vertical cursors in Scipyen's SignalViewer. In the latter case, the cursors
    should be labelled accordingly, then an epoch embedded in the segment can be 
    generated with the appropriate menu function in SignalViewer window.
    
    
    """
    def __interval_index__(labels, label):
        #print("__interval_index__ labels:", labels, "label:", label, "label type:", type(label))
        if labels.size == 0:
            raise ValueError("Expecting a non-empty labels array")
        
        if isinstance(label, str):
            w = np.where(labels == label)[0]
        elif isinstance(label, bytes):
            w = np.where(labels == label.decode())[0]
            
        else:
            raise TypeError("'label' expected to be str or bytes; got %s instead" % type(label).__name__)
        
        if w.size == 0:
            raise IndexError("Interval %s not found" % label.decode())
        
        if w.size > 1:
            warnings.warn("Several intervals named %s were found; will return the index of the first one and discard the rest" % label.decode())
        
        return int(w)
        
    membrane_test_intervals = [b"Rbase", b"Rs", b"Rin"]
    mandatory_intervals = [b"EPSC0Base", b"EPSC0Peak"]
    optional_intervals = [b"EPSC1Base", b"EPSC1Peak"]
    
    if epoch is None:
        if len(s.epochs) == 0:
            raise ValueError("Segment has no epochs, and no external epoch has been defined either")
        
        ltp_epochs = [e for e in s.epochs if (isinstance(e.name, str) and e.name.strip().lower() == "ltp")]
        
        if len(ltp_epochs) == 0:
            raise ValueError("Segment seems to have no LTP epoch defined, and no external epoch has been defined either")
        
        elif len(ltp_epochs) > 1:
            warnings.warn("There seem to be more than one LTP epoch defined in the segment; only the FIRST one will be used")
        
        epoch = ltp_epochs[0]
        
    if epoch.size != 5 and epoch.size != 7:
        raise ValueError("The LTP epoch (either supplied or embedded in the segment) has incorrect length; expected to contain 5 or 7 intervals")
    
    if epoch.labels.size == 0 or epoch.labels.size != epoch.size:
        raise ValueError("Mismatch between epoch size and number of labels in the epoch")
    
    membrane_test_intervals_ndx = [__interval_index__(epoch.labels, l) for l in membrane_test_intervals]
    mandatory_intervals_ndx = [__interval_index__(epoch.labels, l) for l in mandatory_intervals]
    optional_intervals_ndx = [__interval_index__(epoch.labels, l) for l in optional_intervals]
    
    
    # [Rbase, Rs, Rin]
    t_test = [(epoch.times[k], epoch.times[k] + epoch.durations[k]) for k in membrane_test_intervals_ndx]
    
    
    # [EPSC0Base, EPSC0Peak]
    t = [(epoch.times[k], epoch.times[k] + epoch.durations[k]) for k in mandatory_intervals_ndx]
    
    Idc    = np.mean(s.analogsignals[signal_index_Im].time_slice(t_test[0][0], t_test[0][1]))
    
    Irs    = np.max(s.analogsignals[signal_index_Im].time_slice(t_test[1][0], t_test[1][1])) 
    
    Irin   = np.mean(s.analogsignals[signal_index_Im].time_slice(t_test[2][0], t_test[2][1]))

    
    if signal_index_Vm is None:
        if isinstance(testVm, numbers.Number):
            testVm = testVm * pq.mV
            
        elif isinstance(testVm, pq.Quantity):
            if not units_convertible(testVm, pq.V):
                raise TypeError("When a quantity, testVm must have voltage units; got %s instead" % testVm.dimensionality)
            
            if testVm.size != 1:
                raise ValueError("testVm must be a scalar; got %s instead" % testVm)
            
        else:
            raise TypeError("When signal_index_Vm is None, testVm is expected to be specified as a scalar float or Python Quantity, ; got %s instead" % type(testVm).__name__)

    else:
        # NOTE: 2020-09-30 09:56:30
        # Vin - Vbase is the test pulse amplitude
        
        vm_signal = s.analogsignals[signal_index_Vm]
        
        if not units_convertible(vm_signal, pq.V):
            warnings.warn(f"The Vm signal has wrong units ({vm_signal.units}); expecting electrical potential units")
            warnings.warn(f"The Vm signal will be FORCED to correct units ({pq.mV}). If this is NOT what you want then STOP NOW")
            klass = type(vm_signal)
            vm_signal = klass(vm_signal.magnitude, units = pq.mV, 
                                         t_start = vm_signal.t_start, sampling_rate = vm_signal.sampling_rate,
                                         name=vm_signal.name)
        
        # vm_signal = s.analogsignals[signal_index_Vm].time_slice(t[0][0], t[0][1])
        # vm_signal = vm_signal.time_slice(t[0][0], t[0][1])
        
        Vbase = np.mean(vm_signal.time_slice(t_test[0][0], t_test[0][1])) # where Idc is measured
        # Vbase = np.mean(s.analogsignals[signal_index_Vm].time_slice(t[0][0], t[0][1])) # where Idc is measured
        #print("Vbase", Vbase)

        Vss   = np.mean(vm_signal.time_slice(t_test[2][0], t_test[2][1])) # where Rin is calculated
        # Vss   = np.mean(s.analogsignals[signal_index_Vm].time_slice(t[2][0], t[2][1])) # where Rin is calculated
        #print("Vss", Vss)
        
        testVm  = Vss - Vbase

    # print("testVm", testVm)
    
    Rs     = (testVm / (Irs - Idc)).rescale(pq.Mohm)
    Rin    = (testVm / (Irin - Idc)).rescale(pq.Mohm)
        
    #print("dIRs", (Irs-Idc), "dIRin", (Irin-Idc), "Rs", Rs, "Rin", Rin)
        
    Iepsc0base = np.mean(s.analogsignals[signal_index_Im].time_slice(t[0][0], t[0][1])) 
    
    Iepsc0peak = np.mean(s.analogsignals[signal_index_Im].time_slice(t[1][0], t[1][1])) 

    EPSC0 = Iepsc0peak - Iepsc0base
    
    if len(epoch) == 7 and len(optional_intervals_ndx) == 2:
        
        # [EPSC1Base, EPSC1Peak]
        t = [(epoch.times[k], epoch.times[k] + epoch.durations[k]) for k in optional_intervals_ndx]
        
        Iepsc1base = np.mean(s.analogsignals[signal_index_Im].time_slice(t[0][0], t[0][1])) 
        
        Iepsc1peak = np.mean(s.analogsignals[signal_index_Im].time_slice(t[1][0], t[1][1])) 
        
        EPSC1 = Iepsc1peak - Iepsc1base
        PPR = (EPSC1 / EPSC0).magnitude.flatten()[0] # because it's dimensionless
        
    else:
        EPSC1 = np.nan * pq.mV
        PPR = np.nan
            
    ISI = np.nan * s.analogsignals[signal_index_Im].times.units
    
    event = None
    
    if isinstance(isi, float):
        warnings.warn("Inter-stimulus interval explicitly given: %s" % isi)
        ISI = isi * s.analogsignals[signal_index_Im].times.units
        
    elif isinstance(isi, pq.Quantity):
        if isi.size != 1:
            raise ValueError("ISI given explicitly must be a scalar; got %s instead" % isi)
            
        if not units_convertible(isi, s.analogsignals[signal_index_Im].times):
            raise ValueError("ISI given explicitly has units %s which are incompatible with the time axis" % isi.units)
            
        warnings.warn("Inter-stimulus interval is explicitly given: %s" % isi)
        
        ISI = isi
        
    else:
        if isinstance(stim, TriggerEvent): # check for presyn stim event param
            if stim.event_type != TriggerEventType.presynaptic:
                raise TypeError("'stim' expected to be a presynaptic TriggerEvent; got %s instead" % stim.event_type.name)
            
            if stim.size < 1 or stim.size > 2:
                raise ValueError("'stim' expected to contain one or two triggers; got %s instead" % stim.size)
            
            event = stim
            
        elif len(s.events): # check for presyn stim event embedded in segment
            ltp_events = [e for e in s.events if (isinstance(e, TriggerEvent) and e.event_type == TriggerEventType.presynaptic and isinstance(e.name, str) and e.name.strip().lower() == "ltp")]
            
            if len(ltp_events):
                if len(ltp_events)>1:
                    warnings.warn("More than one LTP event array was found; taking the first and discarding the rest")
                    
                event = ltp_events[0]
                    
                
        if event is None: # none of the above => try to determine from trigger signal if given
            if isinstance(trigger_signal_index, (str)):
                trigger_signal_index = ephys.get_index_of_named_signal(s, trigger_signal_index)
                
            elif isinstance(trigger_signal_index, int):
                if trigger_signal_index < 0 or trigger_signal_index > len(s.analogsignals):
                    raise ValueError("invalid index for trigger signal; expected  0 <= index < %s; got %d instead" % (len(s.analogsignals), trigger_signal_index))
                
                event = tp.detect_trigger_events(s.analogsignals[trigger_signal_index], "presynaptic", name="LTP")
                
            elif not isinstance(trigger_signal_index, (int, type(None))):
                raise TypeError("trigger_signal_index expected to be a str, int or None; got %s instead" % type(trigger_signal_index).__name__)

            
        if isinstance(event, TriggerEvent) and event.size == 2:
            ISI = np.diff(event.times)[0]

    return (Idc, Rs, Rin, EPSC0, EPSC1, PPR, ISI)

                 
def analyse_LTP_in_pathway(baseline_block: neo.Block, 
                           chase_block: neo.Block, 
                           signal_index_Im: typing.Union[int, str], 
                           path_index: int,
                           /, 
                           baseline_range=range(-5,-1),
                           signal_index_Vm: typing.Union[int, str]=None, 
                           trigger_signal_index: typing.Union[int, str, None]=None,
                           baseline_epoch:typing.Optional[neo.Epoch]=None, 
                           chase_epoch:typing.Optional[neo.Epoch] = None,
                           testVm:typing.Optional[typing.Union[float, pq.Quantity]] = None,
                           stim:typing.Optional[TriggerEvent] = None,
                           isi:typing.Optional[typing.Union[float, pq.Quantity]] = None,
                           basename:str=None, 
                           normalize:bool=False,
                           field:bool=False,
                           is_test:bool = False,
                           v_clamp:bool = True,
                           out_file:typing.Optional[str]=None) -> pd.DataFrame:
    """
    Parameters:
    -----------
    baseline_block: neo.Block with baseline (pre-induction) sweeps (segments)
    chase_block: neo.Block with chase (post-induction) sweeps (segments)
    signal_index_Im: int
    signal_index_Vm: int or str
    trigger_signal_index
    path_index: 
    baseline_range  = range(-5,-1)
    baseline_epoch  = None
    chase_epoch     = None
    Vm              = False
    basename        = None

    The baseline and chase blocks are expected to contain segments from the same 
    synaptic pathway. That is, they were obtained by calling 
    neoutils.concatenate_blocks passing the index of the segments for the desired
    as the 'segments' parameter (see neoutils.concatenate_blocks for details)
    
    """
    # TODO 2020-10-26 09:18:18
    # analysis of fEPSPs
    # analysis of EPSPs (LTP experiments in I-clamp)
    
    #if field:
        #pass
        
    #else:
    
    # print(f"analyse_LTP_in_pathway signal_index_Im = {signal_index_Im}")


    baseline_result     = calculate_LTP_measures_in_block(baseline_block, signal_index_Im, 
                                                          signal_index_Vm = signal_index_Vm, 
                                                          trigger_signal_index = trigger_signal_index,
                                                          testVm = testVm, 
                                                          epoch = baseline_epoch,
                                                          stim = stim,
                                                          isi = isi)
    
    chase_result        = calculate_LTP_measures_in_block(chase_block, signal_index_Im, 
                                                            signal_index_Vm = signal_index_Vm, 
                                                            trigger_signal_index = trigger_signal_index,
                                                            testVm = testVm, 
                                                            epoch = chase_epoch,
                                                            stim = stim,
                                                            isi = isi)

    result = pd.concat([baseline_result, chase_result],
                       ignore_index = True, axis=0)#, sort=True)
    
    # time index (minutes) relative to the first post-conditioning stimulus (set 
    # to minute zero); this is stored as the index of the data frame
    
    result.index = range(-len(baseline_result), len(chase_result))
    
    if normalize: # augment with normalized values
        meanEPSC0baseline   = np.mean(baseline_result["EPSC0"].iloc[baseline_range])
        result["EPSC0Norm"] = result["EPSC0"] / meanEPSC0baseline
        
        if not np.all(np.isnan(baseline_result["EPSC1"])):
            meanEPSC1baseline = np.nanmean(baseline_result["EPSC1"].iloc[baseline_range])
            result["EPSC1Norm"] = result["EPSC1"] / meanEPSC1baseline
        
    if basename is None:
        basename = ""
        
    name = "%s %s (%d)" % (basename, "Test" if is_test else "Control", path_index)
    
    if hasattr(result, "attr"):
        result.attr["Name"] = name  #requires more recent Pandas
    
    if isinstance(out_file, str):
        result.to_csv(out_file)
    
    return result

# def LTP_analysis_new(path0_base:neo.Block, path0_chase:neo.Block, path0_options:dict,\
#                  path1_base:typing.Optional[neo.Block]=None, \
#                  path1_chase:typing.Optional[neo.Block]=None, \
#                  path1_options:typing.Optional[dict]=None,\
#                  basename:typing.Optional[str]=None):
#     """
#     path0_base: neo.Block with minute-averaged sweeps with synaptic responses
#             on pathway 0 before conditioning
#                 
#     path0_chase: neo.Block with minute-average sweeps with synaptic reponses
#             on pathway 0 after conditioning
#                 
#     path0_options: a mapping (dict-like) wiht the key/value items listed below
#             (these are passed directly as parameters to analyse_LTP_in_pathway):
#                 
#             Im: int, str                    index of the Im signal
#             Vm: int, str, None              index of the Vm signal
#             DIG: int, str, None             index of the trigger signal
#             base_epoch: neo.Epoch, None
#             chase_epoch: neo.Epoxh, None
#             testVm: float, python Quantity, None
#             stim: TriggerEvent, None
#             isi: float, Quantity, None
#             normalize: bool
#             field: bool                     Vm must be a valid index
#             is_test: bool
#             v_clamp:bool
#             index: int
#             baseline_sweeps: iterable (sequence of ints, or range)
#                 
#     
#     """
#     pass
    
def LTP_analysis(mean_average_dict, current_signal, vm_command, /, LTPOptions=None, 
                 results_basename=None, normalize=False):
    """
    LTP analysis for voltage-clamp experiments with paired-pulse stimulation
    interleaved on two pathways.
    
    Positional arguments:
    ====================
    mean_average_dict = dictionary (see generate_minute_average_data_for_LTP)
    
    current_signal: index or name of the signal carrying synaptic response (EPSCs)
    
    vm_command: index or name of the signal carrying the command voltage
    
    Named arguments:
    ================
    result_basename = common prefix for result variables
    LTPoptions      = dictionary (see generate_LTP_options()); optional, default 
        is None, expecting that mean_average_dict contains an "LTPOptions" key.
    
    normalize:bool  = flag whether to calculate EPSC amplitude normalization
                    default is False
        
    Returns:
    
    ret_test, ret_control - two dictionaries with results for test and control 
        (as calculated by analyse_LTP_in_pathway)
    
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
    
    if LTPOptions is None:
        LTPOptions = mean_average_dict["LTPOptions"]
    
    ret_test = analyse_LTP_in_pathway(mean_average_dict["Test"]["Baseline"],
                                 mean_average_dict["Test"]["Chase"], 
                                 current_signal, 
                                 mean_average_dict["Test"]["Path"], 
                                 baseline_range=range(-1*LTPOptions["Reference"], -1),
                                 signal_index_Vm = vm_command,
                                 basename=results_basename+"_test", 
                                 normalize=normalize)
    
    ret_control = analyse_LTP_in_pathway(mean_average_dict["Control"]["Baseline"], 
                                         mean_average_dict["Control"]["Chase"], 
                                         current_signal,
                                         mean_average_dict["Control"]["Path"], 
                                         baseline_range=range(-1*LTPOptions["Reference"], -1),
                                         signal_index_Vm = vm_command,
                                         basename=results_basename+"_control", 
                                         normalize=normalize)
    
    return (ret_test, ret_control)


#"def" plotAverageLTPPathways(data, state, viewer0, viewer1, keepCursors=True, **kwargs):
def plotAverageLTPPathways(data, state, viewer0=None, viewer1=None,
                           keepCursors=True, **kwargs):
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
        
    
    viewer.setupCursors("v", LTPOptions["Cursors"]["Pathway%d"%pathway], 
                        xwindow = LTPOptions["Cursors"]["Windows"],
                        labels = LTPOptions["Cursors"]["Labels"])
        
def extract_sample_EPSPs(data, test_base_segments_ndx, test_chase_segments_ndx, 
                         control_base_segments_ndx, control_chase_segments_ndx, 
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
        
        
        
    average_test_base = neoutils.set_relative_time_start(ephys.average_segments([data["Test"]["Baseline"].segments[ndx] for ndx in test_base_segments_ndx], 
                                                        signal_index = data["LTPOptions"]["Signals"][0])[0])

    test_base = neoutils.set_relative_time_start(ephys.get_time_slice(average_test_base, t0, t1))
    
    average_test_chase = neoutils.set_relative_time_start(ephys.average_segments([data["Test"]["Chase"].segments[ndx] for ndx in test_chase_segments_ndx],
                                          signal_index = data["LTPOptions"]["Signals"][0])[0])
    
    test_chase = neoutils.set_relative_time_start(ephys.get_time_slice(average_test_chase, t0, t1))
    
    control_base_average = neoutils.set_relative_time_start(ephys.average_segments([data["Control"]["Baseline"].segments[ndx] for ndx in control_base_segments_ndx],
                                                            signal_index = data["LTPOptions"]["Signals"][0])[0])
    
    control_base = neoutils.set_relative_time_start(ephys.get_time_slice(control_base_average, t0, t1))
    
    control_chase_average = neoutils.set_relative_time_start(ephys.average_segments([data["Control"]["Chase"].segments[ndx] for ndx in control_chase_segments_ndx],
                                          signal_index = data["LTPOptions"]["Signals"][0])[0])
    
    control_chase = neoutils.set_relative_time_start(ephys.get_time_slice(control_chase_average, t0, t1))
    
    
    result = neo.Block(name = "%s_sample_traces" % data["name"])
    
    
    # correct for baseline
    
    #print(test_base.analogsignals[0].t_start)
    
    test_base.analogsignals[0] -= np.mean(test_base.analogsignals[0].time_slice(0.0002 * pq.s, 0.002 * pq.s))
    test_chase.analogsignals[0] -= np.mean(test_chase.analogsignals[0].time_slice(0.0002 * pq.s, 0.002 * pq.s))
    
    control_base.analogsignals[0] -= np.mean(control_base.analogsignals[0].time_slice(0.0002 * pq.s, 0.002 * pq.s))
    control_chase.analogsignals[0] -= np.mean(control_chase.analogsignals[0].time_slice(0.0002 * pq.s, 0.002 * pq.s))
    
    test_traces = ephys.concatenate_signals(test_base.analogsignals[0], test_chase.analogsignals[0], axis=1)
    test_traces.name = "Test"
    
    control_traces = ephys.concatenate_signals(control_base.analogsignals[0], control_chase.analogsignals[0], axis=1)
    control_traces.name= "Control"
    
    result_segment = neo.Segment()
    result_segment.analogsignals.append(test_traces)
    result_segment.analogsignals.append(control_traces)
    
    result.segments.append(result_segment)
    
    return result

def make_path_dict(src:Source):
    if isinstance(src, SynapticStimulus):
        pass

