# -*- coding: utf-8 -*-

#### BEGIN core python modules
import os, sys, traceback, inspect, numbers, warnings, pathlib, time, io
import datetime
import functools, itertools
from functools import (singledispatch, singledispatchmethod)
import collections, enum
import typing, types
import dataclasses
import subprocess
from dataclasses import (dataclass, KW_ONLY, MISSING, field)

#### END core python modules

#### BEGIN 3rd party modules
from traitlets import Bunch
import numpy as np
import pandas as pd
import quantities as pq
# from quantities.decorators import with_doc
import matplotlib as mpl
import matplotlib.pyplot as plt
import neo
from scipy import optimize, cluster#, where
import colorama

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
from core.prog import (safeWrapper, AttributeAdapter, with_doc, printStyled)
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
                            GeneralIndexType,
                            counter_suffix)

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

from ephys.ephys_protocol import ElectrophysiologyProtocol
import ephys.ephys as ephys
from ephys.ephys import (ClampMode, ElectrodeMode, LocationMeasure,
                         RecordingSource, RecordingEpisode, RecordingEpisodeType,
                         RecordingSchedule,
                         SynapticStimulus, SynapticPathway, AuxiliaryInput, AuxiliaryOutput,
                         synstim, auxinput, auxoutput, 
                         amplitudeMeasure, chordSlopeMeasure, durationMeasure)
import ephys.membrane as membrane
from gui.cursors import DataCursor


LTPOptionsFile = os.path.join(os.path.dirname(__file__), "options", "LTPOptions.pkl")
optionsDir     = os.path.join(os.path.dirname(__file__), "options")

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__ui_path__ = adapt_ui_path(__module_path__,"LTPWindow.ui")
    

__UI_LTPWindow__, __QMainWindow__ = __loadUiType__(__ui_path__, 
                                                   from_imports=True, 
                                                   import_from="gui") #  so that resources can be imported too

# def conditioningSource(adc:typing.Union[int, str] = 0, dac:typing.Optional[int] = None, path:int=0, 
#               pathname:typing.Optional[str]=None,
#               name:str = "cell", **kwargs):
#     """Factory for RecordingSource for plasticity induction.
#     
#     Parameters:
#     -----------------
#     adc, dac, name: See ephys.ephys.RecordingSource constructor for a full description.
#         Briefly:
#         adc, dac: int, physical indexes of the ADC & DAC used 
#         name: str, name of the source (e.g. 'cell01')
#         
#     NOTE: for convenience, a string may be passed as first parameter (in place of `adc`). 
#     This will be used as the 'name' of the source, and `adc` will be set to 0 (zero). 
#     In this case, specifying the `name` parameter again will raise an exception.
#     
#     path: int — the index of the digital output channel
#     pathname: str, None — the name of the synaptic stimulus; 
#         When None (the default) the synaptic stimulus will be named as "pathX"
#         where "X" is the value of the `path` parameter.
#         
#     Here, the default parameter values associate `adc` 0 with `dac` 0 and one 
#     SynapticStimulus object using the first digital output channel (0).
#     
#     Var-keyword parameters (kwargs):
#     --------------------------------
#     These are `auxin` and `auxout`, and by default are set to None.
#     
#     In a given application, the 'name' field of RecordingSource objects should 
#     have unique values in order to allow the lookup of these objects according 
#     to their `name` field.
#     
#     Returns:
#     --------
#     An immutable ephys.ephys.RecordingSource object (a NamedTuple). 
#     
#     One can create a modified version using the '_replace' method:
#     (WARNING: Remember to also change the value of the RecordingSource's 'name' field)
#     
#     """
#     if pathname is None or (isinstance(pathname, str) and len(pathname.strip()) == 0):
#         pathname = f"path{path}"
#         
#     elif not isinstance(pathname, str):
#         raise TypeError(f"'pathname' expected an int or None; instead, got {type(pathname).__name__}")
#     
#     _name = None
#     if isinstance(adc, str) and len(adc.strip()):
#         _name = adc
#         adc = 0
#         
#     if name is None:
#         if isinstance(_name, str):
#             name = _name
#         else:
#             name = "cell"
#         
#     elif isinstance(name, str):
#         if isinstance(_name, str):
#             raise SyntaxError("'name' was already specified by first parameter")
#         
#         if len(name.strip()) == 0:
#             name = "cell"
#             
#     else:
#         raise TypeError(f"'name' expected to be  str or None; instead, got {type(name).__name__}")
#         
#     syn = SynapticStimulus(pathname, path)
#     auxin   = kwargs.pop("auxin", None)
#     auxout  = kwargs.pop("auxout", None)
#     
#     if auxin is not None:
#         if (isinstance(auxin, typing.Sequence) and not all(isinstance(v, AuxiliaryInput) for v in auxin)) or not isinstance(auxin, AuxiliaryInput):
#             raise TypeError(f"'auxin' expected to be an AuxiliaryInput or a sequence of AuxiliaryInput, or None")
#     
#     if auxout is not None:
#         if (isinstance(auxout, typing.Sequence) and not all(isinstance(v, AuxiliaryOutput) for v in auxout)) or not isinstance(auxout, AuxiliaryOutput):
#             raise TypeError(f"'auxout' expected to be an AuxiliaryOutput or a sequence of AuxiliaryOutput, or None")
# 
#     
#     return RecordingSource(name, adc, dac, syn, auxin, auxout)
# 

def twoPathwaysSource(adc:typing.Union[int, str]=0, dac:typing.Optional[int]=None,
                      path0:int=0, path1:int=1, name:typing.Optional[str]=None, 
                      
                      **kwargs):
    """Factory for a RecordingSource in two-pathways synaptic plasticity experiments.
    
    Synaptic stimulation is carried out via extracellular electrodes using
    simulus devices driven by TTLs via DIG channels.

    By default DIG channel indices are 0 and 1, but they can be specified using 
    the 'path0' and 'path1' parameters.
    
    By default, the 'dac' parameter is None, indicating a recording from an 
    𝑢𝑛𝑐𝑙𝑎𝑚𝑝𝑒𝑑 RecordingSource (e.g. a field recording, or recording from an unclamped cell).
    
    When 'dac' parameter is specified as an int (index) or str (name), the 
    source is considered to be recorded in 𝑐𝑙𝑎𝑚𝑝𝑖𝑛𝑔 mode (i.e. voltage- or 
    current-clamp), and, by implication, the RecordingSource is a cell or a membrane 
    patch.
    
    Synaptic responses are recorded on ADC 0 by default, but this can be specified
    using the 'adc' parameter as an int (index) or str (name).
    
    By default the source 'name' field is "cell"¹ but this can be specified using
    the 'name' parameter as a str.
    
    RecordingSources with more complex configurations (e.g. using photostimulation of 
    synaptic activity triggered with DAC-emulated TTLs) should be constructed
    directly (see ephys.RecordingSource documentation for details).
    
    Named parameters:
    -----------------
    adc, dac, name: See ephys.ephys.RecordingSource constructor for a full description.
        Briefly:
        adc, dac: int, physical indexes of the ADC & DAC used 
        name: str, name of the source (e.g. 'cell01')
    
    NOTE: for convenience, a string may be passed as first parameter (in place of `adc`). 
    This will be used as the 'name' of the source, and `adc` will be set to 0 (zero). 
    In this case, specifying the `name` parameter again will raise an exception.
                
    path0, path1 (int) >= 0 indices of DIG channels used to stimulate the pathways.
    
    Here, the default parameter values associate 'adc' 0 with 'dac' 0 and two 
    SynapticStimulus objects, using 'dig' 0 and 'dig' 1, respectively.
    
    Var-keyword parameters:
    --------------------------
    These are `auxin` and `auxout`, and by default are set to 'None'.
    
    In a given application, the 'name' field of RecordingSource objects should have unique
    values in order to allow the lookup of these objects according to this field.
    
    Returns:
    --------
    An immutable ephys.ephys.RecordingSource object (a NamedTuple). 

    One can create a modified version using the '_replace' method:
    (WARNING: Remember to also change the value of the RecordingSource's 'name' field)
    
    
    cell  = twoPathwaysSource()
    cell1 = twoPathwaysSource(dac=1, name="cell1")
    cell2 = cell._replace(dac=1,   name="cell1")
    
    assert cell1 == cell2, "The objects are different"
    
    ¹ It is illegal to use Python keywords as name here.
    
    """
    _name = None
    if isinstance(adc, str) and len(adc.strip()):
        _name = adc
        adc = 0
        
    if name is None:
        if isinstance(_name, str):
            name = _name
        else:
            name = "cell"
        
    elif isinstance(name, str):
        if isinstance(_name, str):
            raise SyntaxError("'name' was already specified by first parameter")
        
        if len(name.strip()) == 0:
            name = "cell"
            
    else:
        raise TypeError(f"'name' expected to be  str or None; instead, got {type(name).__name__}")
    
    assert path0 != path1, f"Test and control pathways must correspond to output channels with distinct indexes; instead got test path: {test_path}, control path: {control_path}"
        
    syn     = (SynapticStimulus('path0', path0), SynapticStimulus('path1', path1)) 
    auxin   = kwargs.pop("auxin", None)
    auxout  = kwargs.pop("auxout", None)
    
    if auxin is not None:
        if (isinstance(auxin, typing.Sequence) and not all(isinstance(v, AuxiliaryInput) for v in auxin)) or not isinstance(auxin, AuxiliaryInput):
            raise TypeError(f"'auxin' expected to be an AuxiliaryInput or a sequence of AuxiliaryInput, or None")
    
    if auxout is not None:
        if (isinstance(auxout, typing.Sequence) and not all(isinstance(v, AuxiliaryOutput) for v in auxout)) or not isinstance(auxout, AuxiliaryOutput):
            raise TypeError(f"'auxout' expected to be an AuxiliaryOutput or a sequence of AuxiliaryOutput, or None")

    return RecordingSource(name, adc, dac, syn, auxin, auxout)

class _LTPFilesSimulator_(QtCore.QThread):
    """
    Used for testing LTPOnline on already recorded files
    """
    
    simulationDone = pyqtSignal(name = "simulationDone")
    
    supplyFile = pyqtSignal(pathlib.Path, name = "supplyFile")
    
    defaultTimeout = 10000 # ms
    
    
    def __init__(self, parent, simulation:dict = None,
                 out: typing.Optional[io.TextIOBase] = None):
        super().__init__(parent=parent)
        
        # print(f"Simulating a supply of ABF (Axon) binary data files")
        
        self._simulatedFile_ = None
        self._simulationCounter_ = 0
        self._simulationFiles_ = []
        self._simulationTimeOut_ = self.defaultTimeout
        self._stdout_ = out
        self._paused_ = False
        
        files = None
        
        if isinstance(simulation, dict):
            self._simulationTimeOut_ = simulation.get("timeout",self.defaultTimeout )
            
            files = simulation.get("files", None)
            
            if not isinstance(files, (list, tuple)) or len(files) == 0 or not all(isinstance(v, (str, pathlib.Path)) for v in files):
                files = None
            
        if files is None:
            print(f"{self.__class__.__name__}:\n Looking for ABF files in directory: ({os.getcwd()}) ...")
            files = subprocess.run(["ls"], capture_output=True).stdout.decode().split("\n")
            # print(f" Found {len(files)} ABF files")
        
        if isinstance(files, list) and len(files) > 0 and all(isinstance(v, (str, pathlib.Path)) for v in files):
            simFilesPaths = list(filter(lambda x: x.is_file() and x.suffix == ".abf", [pathlib.Path(v) for v in files]))
            
            if len(simFilesPaths):
                # NOTE: 2024-01-08 17:45:21
                # bound to introduce some delay, but needs must, for simulation purposes
                print(f" Sorting {len(simFilesPaths)} ABF data based on recording time ...")
                self._simulationFiles_ = sorted(simFilesPaths, key = lambda x: pio.loadAxonFile(x).rec_datetime)
                print(" ... done.")
                
        if len(self._simulationFiles_) == 0:
            print(f" No Axon binary files (ABF) were supplied, and no ABFs were found in current directory ({os.getcwd()})")
               
    def print(self, msg):
        if isinstance(self._stdout_, io.TextIOBase):
            print(msg, file = self._stdout_)
        else:
            print(msg)
               
    def run(self):
        self._simulationCounter_ = 0
        for k,f in enumerate(self._simulationFiles_):
            self.print(f"\n****\n{self.__class__.__name__}.run: simulation counter {self._simulationCounter_}\n reading file {k}: {colorama.Fore.RED}{colorama.Style.BRIGHT}{f}{colorama.Style.RESET_ALL}")
            self.simulateFile()
            if self.isInterruptionRequested():
                self.print(f"\n{self.__class__.__name__}.run: {colorama.Fore.YELLOW}{colorama.Style.BRIGHT}Interruption requested{colorama.Style.RESET_ALL}\n")
                break
            QtCore.QThread.sleep(int(self._simulationTimeOut_/1000)) # seconds!
            # if k < (len(self._simulationFiles_)-1):
            #     QtCore.QThread.sleep(int(self._simulationTimeOut_/1000)) # seconds!
            
        # if not self._paused_:
        if k < (len(self._simulationFiles_) - 1):
            self._paused_ = True
        else:
            self.simulationDone.emit()
            
    def resume(self):
        """Resumes simulation"""
        if self._simulationCounter_ < len(self._simulationFiles_):
            self._paused_ = False
            for k in range(self._simulationCounter_, len(self._simulationFiles_)):
                f = self._simulationFiles_[k]
                self.print(f"\n****\n{self.__class__.__name__}.run: simulation counter {self._simulationCounter_}\n reading file {k}: {colorama.Fore.RED}{colorama.Style.BRIGHT}{f}{colorama.Style.RESET_ALL} for simulation counter {self._simulationCounter_}")
                self.simulateFile()
                if self.isInterruptionRequested():
                    self.print(f"\n{self.__class__.__name__}.run: {colorama.Fore.YELLOW}{colorama.Style.BRIGHT}Interruption requested{colorama.Style.RESET_ALL}\n")
                    break
                QtCore.QThread.sleep(int(self._simulationTimeOut_/1000)) # seconds!
                
            if k < (len(self._simulationFiles_)-1):
                self._paused_ = True
                
            else:
                self.simulationDone.emit()
                
    @pyqtSlot()
    def simulateFile(self):
        if self._simulationCounter_ >= len(self._simulationFiles_):
            self.simulationDone.emit()
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
                 simulator: typing.Optional[_LTPFilesSimulator_] = None,
                 out: typing.Optional[io.TextIOBase] = None):
        """
        """
        QtCore.QThread.__init__(self, parent)
        self._abfRunBuffer_ = abfRunBuffer
        self._filesQueue_ = collections.deque()
        self._pending_ = dict() # pathlib.Path are hashable; hence we use the RSV ↦ ABF

        self._simulator_ = simulator
        self._stdout_ = out
        
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
            
    def print(self, msg):
        if isinstance(self._stdout_, io.TextIOBase):
            print(msg, self._stdout_)
        else:
            print(msg)
               
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
    # NOTE: 2024-02-08 15:05:35
    # for each source in _runData_.sources, determine the relationships between
    # a DAC, input signal (logical ADC) and stimulus channels
    # CAUTION: all ADC/DAC signals indexes in a source are PHYSICAL indexes
    #
    # also, each paths have "equal" until an induction protocol is supplied,
    # which will determine the identity of test and control pathways
    #
    def __init__(self, parent:QtCore.QObject, 
                 abfBuffer:collections.deque,
                 abfRunData:dict,
                 # presynapticTriggers: dict,
                 # landmarks:dict,
                 # data:dict, 
                 # resultsAnalysis:dict,
                 viewers:dict,
                 out: typing.Optional[io.TextIOBase] = None):
        QtCore.QThread.__init__(self, parent)
        
        self._abfRunBuffer_ = abfBuffer
        self._runData_ = abfRunData
        self._viewers_ = viewers
        self._stdout_ = out
        
    def print(self, msg:object):
        if isinstance(self._stdout_, io.TextIOBase):
            print(msg, file=self._stdout_)
        else:
            print(msg)
        
    @safeWrapper
    @pyqtSlot(pathlib.Path)
    def processAbfFile(self, abfFile:pathlib.Path):
        """Reads and ABF protocol from the ABF file and analyses the data
        """
        msg = f"{self.__class__.__name__}.processAbfFile received {colorama.Fore.RED}{colorama.Style.BRIGHT}{abfFile}{colorama.Style.RESET_ALL}"
        self.print(msg)
            
        try:
            # NOTE: 2024-02-08 14:18:32
            # abfRun should be a neo.Block
            abfRun = pio.loadAxonFile(str(abfFile))
            self._runData_.abfRunTimesMinutes.append(abfRun.rec_datetime)
            deltaMinutes = (abfRun.rec_datetime - self._runData_.abfRunTimesMinutes[0]).seconds/60
            self._runData_.abfRunDeltaTimesMinutes.append(deltaMinutes)
            
            if isinstance(self._runData_.locationMeasures, (list, tuple)) and all(isinstance(l, LocationMeasure) for l in self._runData_.locationMaeasures):
                # TODO: 2024-02-18 23:28:45 URGENTLY
                # use location emasures to measure on pathways' ADC
                scipywarn(f"Using custom location measures is not yet supported", out = self._stdout_)
                pass
            else:
                protocol = pab.ABFProtocol(abfRun)
                opMode = protocol.acquisitionMode # why does this return a tuple ?!?
                if isinstance(opMode, (tuple, list)):
                    opMode = opMode[0]
                assert opMode == pab.ABFAcquisitionMode.episodic_stimulation, f"Files must be recorded in episodic mode"

                # check that the number of sweeps actually stored in the ABF file/neo.Block
                # equals that advertised by the protocol
                # NOTE: mismatches can happen when trials are acquired very fast (i.e.
                # back to back) - in this case check the sequencing key in Clampex
                # and set an appropriate interval between successive trials !
                assert(protocol.nSweeps) == len(abfRun.segments), f"In {abfRun.name}: Mismatch between number of sweeps in the protocol ({protocol.nSweeps}) and actual sweeps in the file ({len(abfRun.segments)}); check the sequencing key?"

                # self.print(self._runData_.sources)
                
                # check that the protocol in the ABF file is the same as the current one
                # else create a new episode automatically
                # 
                # upon first run, self._runData_.protocol is None
                if not isinstance(self._runData_.currentProtocol, pab.ABFProtocol):
                    self.print(f"{colorama.Fore.GREEN}{colorama.Style.BRIGHT}initial protocol{colorama.Style.RESET_ALL}: {protocol.name}")
                
                    self._runData_.currentProtocol = protocol
                    
                    # TODO: 2024-02-17 22:58:32 see ### TODO: 2024-02-17 22:56:15 ###
                    # episode = RecordingEpisode(name=self._runData_.episodeName, 
                    #                            protocol = self._runData_.currentProtocol,
                    #                            sources = self._runData_.sources,
                    #                            pathways = self._runData_.pathways,
                    #                            beginFrame = 0,
                    #                            # beginFrame=self._runData_.sweeps,
                    #                            begin=abfRun.rec_datetime)
                    
                    # self._runData_.schedule.addEpisode(episode)
                    # self._runData_.currentEpisode = episode
                    
                    self.processProtocol(protocol)
                    
                    
                elif protocol != self._runData_.currentProtocol:
                    # a different protocol emdash — WARNING: signals a new episode:
                    self.print(f"{colorama.Fore.CYAN}{colorama.Style.BRIGHT}new protocol{colorama.Style.RESET_ALL}: {protocol.name}")
                    
                    # 1. finish off current episode with the previously loaded ABF file
                    # NOTE: 2024-02-16 08:28:43
                    # self._runData_.sweeps hasn't been incremented yet
                    # self._runData_.currentEpisode.end = self._runData_.abfRunTimesMinutes[-1]
                    # self._runData_.currentEpisode.endFrame = self._runData_.sweeps
                    # episodeNames = [e.name for e in self._runData_.schedule.episodes]
                    # if self._runData_.episodeName in episodeNames:
                    #     episodeName = counter_suffix(self._runData_.episodeName, episodeNames)
                    #     self._runData_.episodeName = episodeName
                    # else:
                    #     episodeName = self._runData_.episodeName
                    
                    self._runData_.currentProtocol = protocol
                    
                else: # same protocol → add data to currrent episode
                    self.print(f"{colorama.Fore.BLUE}{colorama.Style.BRIGHT}current protocol{colorama.Style.RESET_ALL}: {protocol.name}")
                    # TODO 2024-02-18 12:01:00 FIXME:
                    # ony adjust for pathways where the protocol has recorded from !
                    # ⇒ get an index of these pathways in processProtocol, store in _runData_
                    pathways = [self._runData_.pathways[k] for k in self._runData_.recordedPathways]
                    for pathway in pathways:
                        pathway.schedule.episodes[-1].endFrame += 1
                        pathway.schedule.episodes[-1].end = datetime.datetime.now()
                    
            self._runData_.sweeps += 1
            
            # self.print(f"{self.__class__.__name__}.processABFFile @ end: _runData_\n{self._runData_}")

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
            
#             if self._runData_.currentProtocol is None:
#                 if protocol.clampMode() == self._runData_.clampMode:
#                     assert(protocol.nSweeps in range(1,3)), f"Protocols with {protocol.nSweeps} are not supported"
#                     if protocol.nSweeps == 2:
#                         assert(dac.alternateDigitalOutputStateEnabled), "Alternate Digital Output should have been enabled"
#                         assert(not dac.alternateDACOutputStateEnabled), "Alternate Waveform should have been disabled"
#                         
#                         # TODO check for alternate digital outputs → True ; alternate waveform → False
#                         # → see # NOTE: 2023-10-07 21:35:39 - DONE ?!?
#                     # self._runData_.monitorProtocol = protocol
#                     self._runData_.currentProtocol = protocol
#                     self._runData_.newEpisode = False
#                     self.processTrackingProtocol(protocol)
#                 else:
#                     raise ValueError(f"First run protocol has unexpected clamp mode: {protocol.clampMode()} instead of {self._runData_.clampMode}")
#                 
#             else:
#                 # if protocol != self._runData_.monitorProtocol:
#                 if protocol != self._runData_.currentProtocol:
#                     if self._runData_.newEpisode:
#                         if self._runData_.currentEpisodeName is None:
#                             self._runData_.currentEpisodeName = protocol.name
#                         if self._runData_.currentProtocolIsConditioning:
#                             self._runData_.conditioningProtocols.append(protocol)
#                         else:
#                             self._runData_.monitoringProtocols.append(protocol)
#                             
#             if self._runData_.currentProtocol.nSweeps == 2:
#                 # if not self._monitorProtocol_.alternateDigitalOutputStateEnabled:
#                 if not self._runData_.currentProtocol.alternateDigitalOutputStateEnabled:
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
#             if protocol == self._runData_.currentProtocol:
#                 adc = protocol.inputConfiguration(self._runData_.adcChannel)
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
#                     self._data_[self._runData_.currentEpisodeName][pndx].segments.append(abfRun.segments[k])
#                     if isinstance(self._presynaptic_triggers_[self._runData_.currentEpisodeName][pndx], TriggerEvent):
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
#                     cnames = [c.name for c in viewer.signalCursors]
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
#                             Rbase_cursor = viewer.signalCursor("Rbase")
#                             coords = ((Rbase_cursor.x - Rbase_cursor.xwindow/2) * pq.s, (Rbase_cursor.x + Rbase_cursor.xwindow/2) * pq.s)
#                             Idc = np.mean(adcSignal.time_slice(*coords))
#                                         
#                             self._results_["DC"].append(Idc)
#                             
#                             Rs_cursor = viewer.signalCursor("Rs")
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
#                             Rin_cursor = viewer.signalCursor("Rin")
#                             coords = ((Rin_cursor.x - Rin_cursor.xwindow/2) * pq.s, (Rin_cursor.x + Rin_cursor.xwindow/2) * pq.s)
#                             Irin = np.mean(adcSignal.time_slice(*coords))
#                                 
#                             Rin = (self._mbTestAmplitude_ / (Irin-Idc)).rescale(pq.MOhm)
#                             
#                             self._results_["Rin"].append(Rin)
#                             
#                             
#                         Ipsc_base_cursor = viewer.signalCursor("PSCBase")
#                         coords = ((Ipsc_base_cursor.x - Ipsc_base_cursor.xwindow/2) * pq.s, (Ipsc_base_cursor.x + Ipsc_base_cursor.xwindow/2) * pq.s)
#                         
#                         IpscBase = np.mean(adcSignal.time_slice(*coords))
#                         
#                         Ipsc0Peak_cursor = viewer.signalCursor("PSC0Peak")
#                         coords = ((Ipsc0Peak_cursor.x - Ipsc0Peak_cursor.xwindow/2) * pq.s, (Ipsc0Peak_cursor.x + Ipsc0Peak_cursor.xwindow/2) * pq.s)
#                         
#                         Ipsc0Peak = np.mean(adcSignal.time_slice(*coords))
#                         
#                         Ipsc0 = Ipsc0Peak - IpscBase
#                         
#                         self._results_[pndx]["Response0"].append(Ipsc0)
#                         
#                         if self._presynaptic_triggers_[pndx].size > 1:
#                             Ipsc1Peak_cursor = viewer.signalCursor("PSC1Peak")
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
    
    @singledispatchmethod
    def processProtocol(self, protocol):
        # TODO: 2024-02-17 15:44:56
        # support for CEDProtocol (class not yet written)
        # generic ephys protocol support (in the distant future, when using NI DAQ devices)
        if not isinstance(protocol, ElectrophysiologyProtocol):
            raise TypeError(f"Expecting an ElectrophysiologyProtocol; instead, got a {type(protocol).__name__}")
        
        raise NotImplementedError(f"{type(protocol).__name__} protocols are not yet supported")
        
    @processProtocol.register(pab.ABFProtocol)
    def _(self, protocol:pab.ABFProtocol):
        self.print(f"{self.__class__.__name__}.processProtocol ({printStyled(protocol.name)})")
        
        # NOTE: 2024-02-18 15:58:07
        # this sets up a pathways "layout", a dict:
        #   recording source ↦ dict: int ↦ dict, where
        #                           int:  pathway index (in the sequence of source-specific pathways)
        #                           dict: int:sweep ↦ sequence of measures
        #   
        
        pathwaysLayout = dict() # ← the function needs to return this
        
        
        # sourceDACs = [s.dac for s in self._runData_.sources]
        # group pathways by their sources
        # 
        # NOTE: 2024-02-17 13:46:53
        # this uses quite a few function calls; might be cheaper/faster to use 
        # @ NOTE: 2024-02-17 13:47:29, as sources ARE supplied by _runData_
        # sources = unique([p.source for p in self._runData_.pathways])
        # pathways = [[p for p in self._runData_.pathways if p.source == s] for s in sources]
        
        
        # NOTE: 2024-02-17 14:14:17
        # Clampex supports stimulation of up to TWO distinct synaptic pathways
        # (i.e. via axonal inputs) for one recording source (cell or field),
        # using the 'alternative digital outputs' mechanism. 
        # The run should have an even number of sweeps — ideally, just two,
        # and a trial MAY consist of several runs (thus, the ABF file will 
        # store the sweep-by-sweep AVERAGE signals, here resulting in a neo.Block
        # with the same number of sweeps per run).
        #
        # (this is clearly less flexible than CED's Signal software)
        #
        # Of course, one can configure an odd number of sweeps (e.g., 3) per
        # run, but in this case, the last sweep will be a supplementary record
        # of the "main" pathway (i.e., the first of the two stimulated pathways)
        # whereas the second pathway would end up with fewer stimulations...
        #
        # NOTE: 2024-02-17 13:51:25
        # if there are more than one pathway associated with this source, 
        # the following SOFT requirements should be met:
        #
        # 1 alternative digital outputs enabled, to allow temporal (sweep-wise)
        #   separation of pathway responses: responses in both pathways are 
        #   recorded through the same electrode; therefore, stimulating them 
        #   in alternate sweeps is the only practical solution to distinguish
        #   them)
        #
        #   NOTE: this applies to tracking (or monitoring) protocols; in contrast,
        #   conditioning protocols, by definition, affect only a single pathway 
        #   (otherwise there would be no justification for recording from a 
        #   second pathway).
        #
        #   Technically, conditioning may also affect supplemetary pathways (e.g.
        #   a "weak" associative or cooperative pathway) but these are not 
        #   typically being monitored for plasticity; if they were, this would
        #   would not be possible with a single Clampex protocol.
        #
        #   To develop this idea: in Clampex, one would have to configure
        #   distinct protocols to record any one of, say, three pathways; 
        #   these protocols would then be interleaved in a sequence, such that
        #   the three pathways would be recorded separately in the same order,
        #   over and over again; furthermore, this would preclude any "auto-averaging" 
        #   (i.e., each of these protocols would consist of one run per trial, 
        #   ideally with one sweep per run, dedicated entirely to the pathway concerned)
        #   and the protocol should have alternateDigitalOutputStateEnabled False.
        #
        #   ### TODO: 2024-02-17 22:56:15
        #   To accommodate this, we must avoid setting up a new episode when the 
        #   ABF protocol has changed (see processAbfFile(…)); instead a new episode
        #   must be initiated manually through the LTPOnline API; also augment
        #   the API to configure averaging !
        #   ###
        #
        #
        # 2 protocol should have an even number of sweeps per run ⇒ even number
        #   of sweeps per trial recorded in the ABF file ⟹
        #   ⋆ main path (path 0) on even-numbered sweeps (0, 2, etc)
        #   ⋆ alternate path (path 1) on odd-numbered sweeps (1, 3, etc)
        #
        #   NOTE: an odd number of sweeps implies that the last sweep carries 
        #   data for the main path (path 0)
        #
        #   e.g. for three sweeps per run, sweeeps 0 and 2 carry path 0, whereas
        #   sweep 1 carries path 1
        #
        # 3 alternative waveforms DISABLED to allow the membrane test to be
        #   be performed (via DAC command signal) in every sweep; if this WAS
        #   enabled, then analog commands would be send via the DAC channel 
        #   where the alternative digital stimulation pattern is defined;
        #   since this DAC is NOT connected to the recording electrode for this
        #   source, any analog commands emitted by this DAC would end up elsewhere
        #
        #   (REMEMBER: One DAC channel per electrode ≡ 1 DAC channel per recording source)
        #
        #       — this is a direct consequence of the uninspired way in 
        #       which Clampex configures digital outputs in their protocol 
        #       editor GUI: in reality the DIG outputs are NEVER sent through 
        #       a DAC so they should have created a separate dialog outside 
        #       the WAVEFORM tabs
        #
        # The above prerequisites also have the consequencess below, regarding 
        #   the use of "supplementary" DACs (with higher index):
        # • if a supplementary DAC also defines epochs wih DIG enabled, these
        #   will be included in the alternative DIG pattern (inluding any
        #   additional DIG output channels) — this is NOT what you may intend.
        #
        #   the only possible advantage I can see is triggering a 3ʳᵈ party 
        #   device e.g. photoactivation/uncaging; the DISadvantage is that ALL
        #   extra DIG outputs will be subject to the same pattern...
        #
        # • if a supplementary DAC defines epochs for analog command waveforms,
        #   this DAC should have an index higher than all DACs used to deliver 
        #   amplifier commands (i.e., ≥ 2); this DAC can only be used to send 
        #   TTL-emulating waveforms to 3ʳᵈ party devices
        #
        #   In such cases, alternative waveforms should be ENABLED, waveform
        #   output in the "alternative" DAC should be DISABLED, and waveform
        #   output in the supplementary (higher index) DAC should be ENABLED. 
        #   This situation will result in:
        #   ∘ a membrane test (for the clamped recorded source) being 
        #   applied ONLY during the "main" pathway stimulation (which is fine,
        #   since one may argue that the "alternative" pathway records from
        #   the same source or cell anyway, so applying a membrane test there
        #   is redundant)
        #   ∘ create room for configuring emulated TTLs in the supplementary
        #       DAC (with higher index) to trigger a 3ʳᵈ party device ONLY
        #       during the "alternative" pathway stimulation
        
        # this channel is the one whhere DIG outputs are configured; it MAY BE
        # dinstict from the source.dac !!!
        # activeDAC = protocol.activeDACChannel
        activeDAC = protocol.getDAC() # this is the `digdac` in processTrackingProtocol
        
        # these are the protocol's DACs where digital output is emitted during the recording
        # the active DAC is one of these by definition
        digOutDacs = tuple(filter(lambda x: x.digitalOutputEnabled, (protocol.getDAC(k) for k in range(protocol.nDACChannels))))
        
        self.print(f"   activeDAC: {printStyled(activeDAC.name)}, digOutDacs: {printStyled([d.name for d in digOutDacs])}")
        
        # will be empty if len(digOutDacs ) == 0
        mainDIGOut = protocol.digitalOutputs(alternate=False)
        
        # this is an empty set when alternateDigitalOutputStateEnabled is False;
        # also, will be empty if len(digOutDacs ) == 0
        altDIGOut = protocol.digitalOutputs(alternate=True)
        
        self.print(f"   mainDIGOut: {printStyled(mainDIGOut)}, altDIGOut: {printStyled(altDIGOut)}")
        
        crosstalk = False # to be determined below
        
        # NOTE: 2024-02-19 18:25:43 Allow this below because one may not have DIG usage
        # if len(digOutDacs) == 0:
        #     raise ValueError("The protocol indicates there are no DAC channels with digital output enabled")
        
        # digOutDACIndex = digOutDacs[0].number
        
        for src in self._runData_.sources:
            # this below maps pathway index to dict sweep index ↦ synaptic pathway
            self.print(f"   -----------------")
            self.print(f"   processing source {printStyled(src.name)}")
            pathwaysLayout[src] = dict()
            # TODO: 2024-02-17 23:13:20
            # below pathways are identified by the DIG channel used to stimulate;
            # must adapt code to identify paths where stimulus is delivered via
            # a DAC through emulated TTLs !!!
            # But for now, see NOTE: 2024-02-18 08:58:24
            
            # NOTE: 2024-02-17 22:36:56 REMEMBER !:
            # in a tracking protocol, distinct pathway in the same recording 
            # source have the same clamp mode!
            #
            # these are pathways defined for this particular source
            # pathways = [p for p in self._runData_.pathways if p.source == src]
            
            pathways = src.pathways
            
            # no pathways defined in this source - surely an error in the 
            # arguments to the LTPOnline call but can never say for sure
            # therefore move on to the next source
            if len(pathways) == 0:
                continue
            
            adc = protocol.getADC(src.adc)
            dac = protocol.getDAC(src.dac)
            
            self.print(f"   source adc: {printStyled(adc.name, 'yellow')}, dac: {printStyled(dac.name, 'yellow')}")
            
            if dac != activeDAC:
                if not protocol.alternateDigitalOutputStateEnabled:
                    raise ValueError(f"Alternative digital outputs must be enabled in the protocol when digital outputs are configured on DAC index {activeDAC.physicalIndex} and command waveforms are sent through DAC index {src.dac}")
                   
            clampMode = protocol.getClampMode(adc, activeDAC)
            
            self.print(f"   data recorded in {printStyled(clampMode.name, 'yellow')}")
            
            # figure out which of the pathways use a DIG or a DAC channel for TTLs;
            # of these figure out which are ACTUALLY used in the protocol
            # NOTE: 2024-02-17 16:37:26
            # this should be configured in the protocol, in any case
            # as noted above, a DIG output MAY be also used to trigger 3ʳᵈ party device
            #
            
            # as noted above, additional DIG outputs MAY be used to trigger 3ʳᵈ party device
            # furthermore, this is an empty set when the protocol does not enable
            # alternate digital outputs; 
            #
            
            mainDigPathways = list() # empty if len(digOutDacs ) == 0
            altDigPathways  = list() # empty if len(digOutDacs ) == 0 or protocol.alternateDigitalOutputStateEnabled is False;
            dacPathways     = list() # empty if no passed sources have stimulus on any of the DACs
            pathwaysToStore = dict() # the above, to store in _runData_.recordedPathways between runs
            
            for k, p in enumerate(pathways):
                if p.stimulus.dig:
                    # assert p.source.dac in [c.physicalIndex for c in digOutDacs], f"The DAC channel ({p.source.dac}) for pathway {k} does not appear to have DIG outputs enabled"
                    assert dac in digOutDacs, f"The DAC channel ({dac.physicalIndex}) for pathway {k} does not appear to have DIG outputs enabled"
                    
                    if p.stimulus.channel in mainDIGOut:
                        mainDigPathways.append((k, p))
                        
                    elif p.stimulus.channel in altDIGOut:
                        altDigPathways.append((k, p))
                        
                elif p.stimulus.channel in protocol.physicalDACIndexes:
                    dacPathways.append((k, p))
                    
            # total number of pathways recorded in this protocol; it should be ≤ total number of pathways in _runData_
            # NOTE: 2024-02-19 18:30:22 TODO: consider NOT pre-populating the pathways field in _runData_
            # but rather parse the sources here and populate with pathways as necessary.
            nPathways = len(mainDigPathways) + len(altDigPathways) + len(dacPathways)
            
            assert nPathways <= 2, "A Clampex protocol does NOT support recording from more than two pathways"
            
            if nPathways == 0:
                # no pathways recorded in this protocol (how likely that is ?!?)
                continue
            
            # If you have just one amplifier, you can record from as many sources as 
            #   there are channels in the amplifier, for example:
            #   • just one source for AxoPatch
            #   • maximum two sources for MultiClamp
            # 
            # More amplifiers can allow simultaneous recording from more sources,
            # provided that the ADC/DACs are appropriately configured and here is
            # no overlap with any TTL-emulating DACs.
            #
            # When the source records from more than one pathway (i.e. more than one pathway for the SAME source)
            # there should be a temporal separation of sweeps per pathway, so that
            # synaptic responses recorded through the SAME ADC can be distinguished.
            #
            # This can be achieved in two ways:
            #
            # 1) the alternate stimulation approach → allows up to TWO pathways per source
            # (one can use this approach for a single pathway, but then it will 
            #  result in wasteful "empty" sweeps: the non-existent "alternate" pathway 
            #   does not generate any responses, yet it will be recorded)
            #   1.1) uses temporal separation through alternate sweeps in the same run
            #
            #   1.2) can be used for up to two pathways:
            #       1.2.a) either two "digital" pathways ⇒ protocol has:
            #           • alternateDigitalOutputStateEnabled ≡ True
            #           • "main" digital pattern set
            #           • "alternate" digital pattern set
            #           • alternateDACOutputStateEnabled — irrelevant
            #
            #       1.2.b) one "digital" and one "dac" pathway ⇒ protocol has:
            #           • alternateDigitalOutputStateEnabled ≡ True
            #           • "main" digital pattern set
            #           • "alternate" digital pattern NOT set
            #           • alternateDACOutputStateEnabled ≡ True
            #
            #       1.2.c) two "dac" pathways - impossible in Clampex
            #
            #   1.3) the protocol should have an even number sweeps per run,
            #       ideally only two (higher sweep index just repeat the 
            #       measurements unnecessarily and confound the issue of 
            #       averaged results - to keep it simple, we expect such protocol
            #       to produce only two sweeps)
            #           
            # 2) single-sweep approach → use ONE pathway per protocol, and configure
            #   as many protocols as there are pathways.
            #
            #   2.1) averaging will be turned off in Clampex ⟹ ABF files contain
            #       immediate data, which may be averaged offline (TODO: pass arguments to the LTPOnline)
            #       and data should be grouped by pathway, post-hoc
            
            # see above: a protocol DOES NOT support monitoring more than
            # two pathwys
            # if there are two pathwys, then they should be stimulated
            # alternatively, and the protocol should (ideally) have an even number 
            # of sweeps per run; since it does NOT really make sense to have
            # more than TWO sweeps (because we just repeat the protocol 𝒏
            # times, for 𝒏 files) we actually ENFORCE THIS precondition:
            
            syn_stim_digs = list()
            syn_stim_dacs = list()
            
            if nPathways == 2:
                assert len(mainDigPathways) == 1, "There must be at least one digitally triggered pathway in the protocol"
                syn_stim_digs.append(mainDigPathways[0][1].stimulus.channel)
                
                assert len(altDigPathways) == 1 or len(dacPathways) == 1, "There can be only one other pathway, triggered either digtially, or via DAC-emulated TTLs"
                if len(altDigPathways) == 1:
                    # two alternative digitally stimulated pathways — the most
                    # common case
                    assert protocol.alternateDigitalOutputStateEnabled, "For two digitally-stimulated pathways the alternative digital output state must be enabled in the protocol"
                    syn_stim_digs.append(altDigPathways[0][1].stimulus.channel)
                elif len(dacPathways) == 1:
                    # one digital and one DAC pathway 
                    assert protocol.alternateDigitalOutputStateEnabled and protocol.alternateDACOutputStateEnabled, "For a digitally stimulated pathway and one triggered by emulated TTLs the protocol must have both alternative digital outputs and alternative DAC outputs enabled"
                    # furthermore, the stimulation DAC for this pathway must have a higher index than
                    # the active DAC channel, and furthermore, the active DAC channel must also be
                    # the same as the source's DAC channel (the one sending analog commands)
                    assert activeDAC == dac, "Active DAC channel must be the same as used for analog command"
                    assert dacPathways[0][1].stimulus.channel > activeDAC.physicalIndex, "The pathway triggerd by DAC-emulated TTLs must use a higher DAC index than that of the primary pathway"
                    
                    
            # elif nPathways == 1: # alternative pathways do not exist here
            else: # alternative pathways do not exist here; nPathways ≡ 1 
                if len(mainDigPathways):
                    syn_stim_digs.append(mainDigPathways[0][1].stimulus.channel)
                    
                elif len(dacPathways):
                    syn_stim_dacs.append(dacPathways[0][1].stimulus.channel)
                    
            
            self.print(f"   digital channels for synaptic stimulation: {printStyled(syn_stim_digs, 'yellow')}")
            self.print(f"   DAC channels for synaptic stimulation via emulated TTLs: {printStyled(syn_stim_dacs, 'yellow')}")
            
            # figure out the epochs that define synaptic stimulations
            
            # figure out the membrane test epochs for voltage clamp, set up LocationMeasures for this
            # we use the source's DAC channel - which may also be the activeDAC
            # although this is not necessary.
            # furthermore, these epochs should exist in eitgher voltage-or current clamp
            # if they do not, we just imply do not provide corresponding measurmements
            #
            # also, these are COMMON for all the pathways in the source
            mbTestEpochs = list(filter(lambda x: x.epochType in (pab.ABFEpochType.Step, pab.ABFEpochType.Pulse) \
                                                and not any(x.hasDigitalOutput(d) for d in (syn_stim_digs)) \
                                                and x.firstLevel !=0 and x.deltaLevel == 0 and x.deltaDuration == 0, 
                                    dac.epochs))
            
            if len(mbTestEpochs) == 0:
                if clampMode in (ClampMode.VoltageClamp, ClampMode.CurrentClamp):
                    scipywarn("No membrane test epoch appears to have been defined", out = self._stdout_)
                membraneTestEpoch = None
                testAmplitude = None
                testStart = None
                testDuration = None
                
            else:
                membraneTestEpoch = mbTestEpochs[0]
                testAmplitude = membraneTestEpoch.firstLevel
                testStart = dac.getEpochRelativeStartTime(membraneTestEpoch, 0)
                testDuration = membraneTestEpoch.firstDuration
                
                self.print(f"   membraneTestEpoch: {printStyled(membraneTestEpoch.letter)} ({printStyled(membraneTestEpoch.number)}) with:")
                self.print(f"       amplitude: {printStyled(testAmplitude)}")
                self.print(f"       start: {printStyled(testStart)}")
                self.print(f"       duration: {printStyled(testDuration)}")
                self.print(f"       -----")
                
            # NOTE: 2024-02-20 23:42:12
            # figure out where this epoch occurs:
            # if testStart + testDuration < dac TODO 2024-02-19 22:59:46
            # → done per each pathway, below
                
            # ⇒ expect the protocol to have as many sweeps as pathways in this source
            
            # Can there be a contigency where this does not hold?
            #
            # say you record from a patched cell through one electrode (→ one source)
            # and simultaneously also record field responses in the same slice — obviously, 
            # using a second electrode → a second source, with its own ADC/DAC pair;
            #
            # each source defines its own pair of pathways: technically, they might be stimulating
            # the same pair of distinct axonal bundles, via digital channels or DAC channels for TTL emulation
            #
            # if you used the alternative stimulation approach, you would then be 
            #   recording from TWO pathways per run — hence you'd need TWO sweeps 
            #
            # bottom line: the protocol should provide at least as many sweeps 
            #   as the maximum number of patwhays stimulated by it 
            
            # assert protocol.nSweeps >= nPathways, f"Not enough sweeps ({protocol.nSweeps}) for {nPathways} pathways"
            
            # in a multi-pathway protocol, the "main" digital pathways are always
            # delivered on the even-numbered sweeps: 0, 2, etc.
            #
            for k, p in mainDigPathways:
                self.print(f"   processing pathway {printStyled(k)} ({printStyled(p.name)}) with synaptic simulation via DIG {printStyled(p.stimulus.channel)}")
                # to store location measures for this pathway:
                # str (name) ↦ dict("measure" ↦ LocationMeasure, "args" ↦ tuple of extra arguments passed to LocationMeasure)
                pathwayMeasures = dict() 
                
                
                # NOTE: for the moment, I do not expect to have more than one such epoch
                # WARNING we require a membrane test epoch in voltage clamp;
                # in current clamp this is not mandatory as we may be using field recordings
                # locate sweeps and epochs where the pathway's digital stimulus is emitted
                # we need the active DAC here (which is the one where DIG output is enabled)
                # 
                # the sweep(s) returned here is (are) also the sweep(s) where we carry out measurements
                # NOTE: 2024-02-20 23:45:58
                # if there are more than one sweeps, this is likely a crosstalk protocol
                # to be confirmed by the number of stimuli on each path way and
                # the order of pathways in the protocol
                sweepsEpochsForDig = protocol.getDigitalChannelUsage(p.stimulus.channel, activeDAC)
                
                
                # NOTE: 2024-02-20 08:41:09
                # this is to check the sweepsEpochsForDig approach against the
                # approach in processTrackingProtocol; consider removing:
                # synStimEpochs below only takes digital TTL-emitting epochs
                # for synaptic stimulation
                # since I now strive to support DAC-emulated TTL as well, I
                # prefer the name `digStimEpochs`
                synTrainStimEpochs = list(filter(lambda x: len(x.getTrainDigitalOutputChannels("all"))>0, 
                                    activeDAC.epochs))
                
                synPulseStimEpochs = list(filter(lambda x: len(x.getPulseDigitalOutputChannels("all"))>0, 
                                    activeDAC.epochs))
                
                synStimEpochs = synTrainStimEpochs + synPulseStimEpochs
                
                
                ee = ", ".join([f"{e.letter} ({e.number})" for e in synStimEpochs])
                self.print(f"       synaptic stimulation epochs: {printStyled(ee)}")
                
                self.print(f"       DIG channel {printStyled(p.stimulus.channel)} active in sweeps {printStyled([sed[0] for sed in sweepsEpochsForDig])}")
                
                
                assert all((e in synStimEpochs) for e in sweepsEpochsForDig[0][1]), f"Epochs inconsistencies for pathway {k}"
                # assert all(i==j for i, j in zip(sweepsEpochsForDig[0][1], synStimEpochs)) f"Epochs inconsistencies for pathway {k}"
                
                if len(sweepsEpochsForDig) == 0:
                    raise RuntimeError(f"The specified DIG channel {p.stimulus.channel} appears to be disabled in all sweeps")
                
                if len(sweepsEpochsForDig) > 1:
                    # TODO: Check for crosstalk
                    pass
                    # raise RuntimeError(f"The specified DIG channel {p.stimulus.channel} appears to be active in more than one sweep ({k[0] for k in sweepsEpochsForDig})")
                
                
                responseBaselineDuration = self._runData_.responseBaselineDuration
                
                digStimEpochs = sweepsEpochsForDig[0][1] # a list with epochs that emit on the SAME digital channel
                
                if len(digStimEpochs) == 0:
                    raise RuntimeError(f"No digital stimulation epochs found in the protocol, for pathway {k} in source {src}")
                
                # if len(digStimEpochs) > 1:
                    # below, this is contentious: what if the user decided to 
                    # use more than one epoch to emulate a digital TTL train?
                    # so better use them all
                    # scipywarn(f"For pathway {k} in source {src} there are {len(digStimEpochs)} in the protocol; will use the first one")
                    
                firstDigStimEpoch = digStimEpochs[0]
                
                # collection of unique digital channels used for stimulation on THIS pathway
                stimDIG = unique(list(itertools.chain.from_iterable(e.getUsedDigitalOutputChannels("all") for e in digStimEpochs)))
                
                # now, figure out start & duration for signal baseline and for synaptic response baseline(s)
                # we compute: 
                # signalBaselineStart, signalBaselineDuration, responseBaselineStart, responseBaselineDuration
                if isinstance(membraneTestEpoch, pab.ABFEpoch):
                    if testStart + testDuration < dac.getEpochRelativeStartTime(firstDigStimEpoch, 0):
                        # membrane test occurs BEFORE digital simulation epochs,
                        # possibly with intervening epochs (for response baselines)
                        if testStart == 0:
                            signalBaselineStart = 0*pq.s
                            signalBaselineDuration = testStart
                            
                        else:
                            # need to fnd out these, as the epochs table may start at a higher epoch index
                            initialEpochs = list(filter(lambda x: dac.getEpochRelativeStartTime(x, 0) + x.firstDuration <=  dac.getEpochRelativeStartTime(membraneTestEpoch, 0) \
                                                                and x.firstDuration > 0 and x.deltaDuration == 0, 
                                                            dac.epochs))
                            if len(initialEpochs):
                                # baseline epochs are initial epochs where no analog command is sent out
                                # (e.g. they are not set)
                                baselineEpochs = list(filter(lambda x: x.firstLevel == 0 and x.deltaLevel == 0, initialEpochs))
                                if len(baselineEpochs):
                                    signalBaselineStart = dac.getEpochRelativeStartTime(baselineEpochs[0], 0)
                                    signalBaselineDuration = baselineEpochs[0].firstDuration
                                else:
                                    signalBaselineStart = 0*pq.s
                                    signalBaselineDuration = dac.getEpochRelativeStartTime(initialEpochs[0], 0)
                            else:
                                signalBaselineStart = max(testStart -2 * dac.holdingTime, 0*pq.s)
                                signalBaselineDuration = max(dac.holdingTime, testDuration)
                                
                        # any epochs intervening between membrane test and digStimEpochs
                        # and between consecutive digStimEpochs - 
                        # (do we really care ?!? just use line below:)
                        # however, keep the code just in case the user did provide baseline epochs intervening
                        # between mb test and first stim and between consecutive stims
                        #
                        digStimStarts = [activeDAC.getEpochRelativeStartTime(e)  - responseBaselineDuration for e in digStimEpochs]
                        
                        ff = lambda x: dac.getEpochRelativeStartTime(x, 0) + x.firstDuration
                        responseBaselineEpochs = list(filter(lambda x: x.firstLevel == 0 and x.deltaLevel == 0 and x.firstDuration >= responseBaselineDuration \
                                                                    and dac.getEpochRelativeStartTime(x, 0) > testStart + testDuration \
                                                                    and any([ff(x) <= digStimStarts[0]] + [ff(x) > digStimStarts[k-1] and ff(x) <= digStimStarts[k] for k in range(1, len(digStimStarts))]),
                                                            dac.epochs))
                        # if len(digStimEpochs) > 1:
                        # else:
                        #     responseBaselineEpochs = list(filter(lambda x: x.firstLevel == 0 and x.deltaLevel == 0 and x.firstDuration >= responseBaselineDuration \
                        #                                                 and dac.getEpochRelativeStartTime(x, 0) > testStart + testDuration \
                        #                                                 and any(dac.getEpochRelativeStartTime(x, 0) + x.firstDuration <= activeDAC.getEpochRelativeStartTime(digStimEpochs[0], 0)) - responseBaselineDuration,
                        #                                         dac.epochs))
                        
                        if len(responseBaselineEpochs):
                            responseBaselineStarts = [dac.getEpochRelativeStartTime(e, 0) for e in responseBaselineEpochs]
                        
                        else:
                            # CAUTION 2024-02-21 00:49:16
                            # what if the responses are closer in time than responseBaselineDuration ?!?
                            responseBaselineStarts = digStimStarts
                            # responseBaselineStarts = activeDAC.getEpochRelativeStartTime(digStimEpochs[0], 0) - 2 * responseBaselineDuration
                            
                    elif testStart > activeDAC.getEpochRelativeStartTime(digStimEpochs[-1], 0) + digStimEpochs[-1].firstDuration:
                        # mb test delivered AFTGER the last digital simulation epoch 
                        # ideally, somwehere towards the end of the sweep, 
                        # hopefully AFTER synaptic responses have decayed to baseline
                        #
                        # in this case, best is to use the first epoch before the
                        # digStimEpochs (if any), or the dac holding, as signal baseline (DC)
                        #
                            
                        initialEpochs = list(filter(lambda x: dac.getEpochRelativeStartTime(x, 0) + x.firstDuration <=  activeDAC.getEpochRelativeStartTime(digStimEpochs[0], 0) \
                                                            and x.firstDuration > 0 and x.deltaDuration == 0, 
                                                        dac.epochs))
                
                        if len(initialEpochs):
                            # there are epochs before digStimEpochs - are any of these baseline-like?
                            baselineEpochs = list(filter(lambda x: x.firstLevel == 0 and x.deltaLevel == 0, initialEpochs))
                            if len(baselineEpochs):
                                signalBaselineStart = dac.getEpochRelativeStartTime(baselineEpochs[0], 0)
                                signalBaselineDuration = baselineEpochs[0].firstDuration
                            else:
                                signalBaselineStart = 0 * pq.s
                                signalBaselineDuration = dac.getEpochRelativeStartTime(initialEpochs[0], 0)
                                
                        else:
                            # no epochs before the membrane test (odd, but can be allowed...)
                            signalBaselineStart = max(activeDAC.getEpochRelativeStartTime(digStimEpochs[0], 0) - 2 * dac.holdingTime, 0*pq.s)
                            signalBaselineDuration = max(dac.holdingTime, digStimEpochs[0].firstDuration)
                    
                        # Now, determine the response baseline for this scenario.
                        digStimStarts = [activeDAC.getEpochRelativeStartTime(e)  - responseBaselineDuration for e in digStimEpochs]
                        
                        ff = lambda x: dac.getEpochRelativeStartTime(x, 0) + x.firstDuration

                        responseBaselineEpochs = list(filter(lambda x: x.firstLevel == 0 and x.deltaLevel == 0 and x.firstDuration >= responseBaselineDuration \
                                                                    and dac.getEpochRelativeStartTime(x, 0) > testStart + testDuration \
                                                                    and any([ff(x) <= digStimStarts[0]] + [ff(x) > digStimStarts[k-1] and ff(x) <= digStimStarts[k] for k in range(1, len(digStimStarts))]),
                                                            dac.epochs))

                        # responseBaselineEpochs = list(filter(lambda x: x.firstLevel == 0 and x.deltaLevel == 0 and x.firstDuration >= responseBaselineDuration \
                        #                                             and dac.getEpochRelativeStartTime(x, 0) > testStart + testDuration \
                        #                                             and dac.getEpochRelativeStartTime(x, 0) + x.firstDuration <= activeDAC.getEpochRelativeStartTime(digStimEpochs[0], 0) - responseBaselineDuration,
                        #                                     dac.epochs))
                        
                        if len(responseBaselineEpochs):
                            # take the last one
                            responseBaselineStarts = [dac.getEpochRelativeStartTime(e, 0) for e in responseBaselineEpochs]
                        
                        else:
                            responseBaselineStarts = digStimStarts
                            # responseBaselineStart = activeDAC.getEpochRelativeStartTime(digStimEpochs[0], 0) - 2 * self._runData_.responseBaselineDuration
                            
                    else:
                        raise RuntimeError(f"Cannnot determine response baseline")
                    
                    # TODO: 2024-02-20 16:24:00
                    # generate location measures for membrane test
                    
                    if clampMode == ClampMode.VoltageClamp:
                        dataCursorDC  = DataCursor(signalBaselineStart + signalBaselineDuration/2, signalBaselineDuration)
                        dataCursorRs  = DataCursor(testStart - 0.0025*pq.s, 0.005*pq.s)
                        # last 10 ms before end of test, window of 5 ms
                        dataCursorRin = DataCursor(testStart + testDuration - 0.01 * pq.s, 0.005*pq.s)
                        mbTestLocationMeasure = ephys.membraneTestVClampMeasure(dataCursorDC, dataCursorRs, dataCursorRin)
                        pathwayMeasures["VClampMembraneTest"] = {"measure":mbTestLocationMeasure,
                                                                 "args": (testAmplitude)}
                        self.print(f"payhwayMeasures: {printStyled(pathwayMeasures)}")
                    elif clampMode == ClampMode.CurrentClamp:
                        pass #TODO 2024-02-27 16:18:25
                    
                else:
                    # no membrane test epoch configured (e.g. field recording)
                    # ⇒ response baseline same as signal baseline
                    #
                    signalBaselineStart = self._runData_.signalBaselineStart
                    signalBaselineDuration = dac.getEpochRelativeStartTime(synStimEpochs[0],0)
                    responseBaselineStarts = [self._runData_.signalBaselineStart]
                    # responseBaselineDuration = signalBaselineDuration
                
                # NOTE: 2024-02-27 16:24:08
                # now, record the patwhay entry
                recorded_pathway_entry = f"{src.name}_{p.name}"
                if recorded_pathway_entry not in self._runData_.recordedPathways:
                    self._runData_.recordedPathways[recorded_pathway_entry] = p
                    
                # NOTE: 2024-02-27 16:25:58
                # now, determine the measurements
                # we need access to the ABF run data here
                    
                # FIXME 2024-02-20 16:22:05 in the above:
                # 1) what to do with paired pulses?
                # 2) generate location measures for the membrane test (if any)
                # 3) figure out contigency for crosstalk
                
                # commented out for now
                # pathwaysLayout[src][k][sweepsEpochsForDig[0][0]] = pathwayMeasures
                
                    
                
                # TODO 2024-02-18 23:23:55 finish this up
                
                
                
                
#             if len(pathways) > 1:
#                 if len(pathways) > 2 and protocol.nSweeps > 1:
#                     raise RuntimeError(f"In experiments with more than two pathways, the ABF protocol must record one sweep at a time")
#                 
#                 if len(pathways) == 2:
#                     # special case
#                     # and protocol.alternateDigitalOutputStateEnabled:
#                     # protocol handles two pathways
#                     
#                     # figure out which is the "main" and which is the "alternate" pathway
#                     # True is the main, False is the alternate; most typical would be
#                     # [True, False] here
#                     pathsLayout = [p.stimulus.channel in mainDIGOut and p.stimulus.channel not in altDIGOut for p in pathways]
#                     
#                     # map sweep index in the protocol to pathway data; first element
#                     # is main path (path 0), second is the alternate path (path 1);
#                     # (adapts automatically to requirement 2∘)
#                     pathwaySegments = [range(0, protocol.nSweeps, 2), range(1, protocol.nSweeps, 2)]
#                     
#                 else:
#                     # protocol handles just one pathway of however many
#                     pathsLayout = [p.stimulus.channel in mainDIGOut for p in pathways]
#                     pathwaySegments = [range(protocol.nSweeps) if pathsLayout[k] else None for k in range(len(pathways))]
#                     
#                         
#             else: 
#                 # unique pathway is also the main pathway
#                 pathsLayout = [True] 
#                 # all sweeps in the trial record from the same (unique, main) path
#                 pathwaySegments = [range(protocol.nSweeps)]
#                 
#             adc = protocol.getADC(src.adc)
#             dac = protocol.getDAC(src.dac)
            
#             clampMode = protocol.getClampMode(adc, dac)
#             
#             for pathway in pathways:
#                 pathway.clampMode = clampMode
                
            # now, find out relevant epochs and triggers
            
#             for pathway, segmentRange in zip(pathways, pathwaySegments):
#                 pathway.clampMode = clampMode
#                 
#                 self.processPathway(pathway, protocol, segmentRange)

    def processPathway(self, pathway:SynapticPathway, protocol:pab.ABFProtocol):
        return # for now...
        # adc is a ABFInputConfiguration
        # adc = protocol.inputConfiguration(pathway.source.adc)
        
        # dac is a ABFOutputConfiguration
#         dac = protocol.outputConfiguration(pathway.source.dac)
#         
#         pathway.clampMode = protocol.getClampMode(adc, dac)
        
        synStimEpochs = list()
        mbTestEpochs = list()
        # pathway.electrodeMode = ElectrodeMode.Field if pathway.clampMode == 
        if isinstance(pathway.stimulus, SynapticStimulus):
            
            # Get the index of channel emitting digital command (TTL) train or pulse;
            # this can be either:
            # • a DIG channel → 
            #   ∘ the train or pulse are set in an ABFEpoch configured for the 
            #       DAC with index `pathway.dac` 
            #   ∘ `pathway.stimulus.channel` is the index of the DIG out in the 
            #       bit word of the ABFEpoch
            #   ∘ when `pathway` shares the `dac` with another pathway, the two
            #       distinct TTL commands are sent as "alternative" digital outputs
            #       ⟹ 
            #           ⋆ "alternateDigitalOutputStateEnabled" is True for this `dac`
            #           ⋆ the protocol must define a even number of sweeps
            #       
            # • a DAC channel (TTL emulation) →
            #   ∘ the TTL command is set in an ABFEpoch conigured for the DAC 
            #       with index `pathway.stimulus.channel`
            #
            # We use the `pathway.stimulus.dig` boolean flag to distinguish the 
            # two possibilities.
            
            # below, digDAC is a ABFOutputConfiguration; digNdx is the index of
            # the true digital output channel, or None
            if pathway.stimulus.dig:    
                # protocol uses a true digital command
                digDAC = protocol.outputConfiguration(pathway.source.dac) 
                digNdx = pathway.stimulus.channel
                
                # since it is difficult to test here if this pathway shares the 
                # dac with another one, we interrogate of the dac uses 
                # alternative digital outputs
                
            else: 
                # protocol emulates a digital command in a DAC
                digDAC = protocol.outputConfiguration(pathway.stimulus.channel) 
                digNdx = None
                
            # NOTE: 2024-02-17 09:27:41
            # find out which DAC defines an epoch for the digital train or pulse;
            # ideally, this is the dac specified in the pathway
            
            
            
            # TODO: 2024-02-16 22:54:29
            # simplify this gymnastics, given that the DIG channel is already
            # specified in the pathway.
            
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
                raise ValueError("The protocol indicates there are no DAC channels with digital output enabled")
            
            digOutDACIndex = digOutDacs[0].number
            
            if digOutDACIndex != dac:
                if not protocol.alternateDigitalOutputStateEnabled:
                    raise ValueError(f"Digital outputs are enabled on DAC {digOutDACIndex} and command waveforms are sent via DAC {dac}, but alternative digital outputs are disabled in the protocol")
            
                assert protocol.nSweeps % 2 == 0, "For alternate DIG pattern the protocol is expected to have an even number of sweeps"
    

            # DAC where dig out is enabled;
            # when alt dig out is enabled, this stores the main dig pattern
            # (the dig pattern sent out on even sweeps 0, 2, 4, etc)
            # whereas the "main" dac retrieved above stores the alternate digital pattern
            # (the dig pattern set out on odd sweeps, 1,3, 5, etc)
            
            digdac = protocol.outputConfiguration(digOutDACIndex)
            
            if len(digdac.epochs) == 0:
                raise ValueError("DAC with digital outputs has no epochs!")
            
            digEpochsTable = digdac.getEpochsTable(0)
            dacEpochsTable = dac.getEpochsTable(0)
            
            digEpochsTable_reduced = digEpochsTable.loc[[i for i in digEpochsTable.index if not i.startswith("Digital Pattern")], :]
            dacEpochsTable_reduced = dacEpochsTable.loc[[i for i in dacEpochsTable.index if not i.startswith("Digital Pattern")], :]
            
            digEpochsTableAlt = None
            digEpochsTableAlt_reduced = None
            
            if digOutDACIndex != dac:
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
                digEpochsTableAlt = digdac.getEpochsTable(1)
                digEpochsTableAlt_reduced = digEpochsTableAlt.loc[[i for i in digEpochsTableAlt.index if not i.startswith("Digital Pattern")], :]
                assert(np.all(digEpochsTable_reduced == dacEpochsTable_reduced)), "Epochs table mismatch between DAC channels"
                assert(np.all(digEpochsTableAlt_reduced == dacEpochsTable_reduced)), "Epochs table mismatch between DAC channels with alternate digital outputs"
            
            
            # Locate the presynaptic triggers epoch
            # first try and find epochs with digital trains
            # there should be only one such epoch, sending at least one TTL pulse per train
            #
            synStimEpochs = list(filter(lambda x: len(x.getTrainDigitalOutputChannels("all"))>0, digdac.epochs))
            
            # ideally there is only one such epoch
            if len(synStimEpochs) > 1:
                scipywarn(f"There are {len(synStimEpochs)} in the protocol; will use the first one", out = self._stdout_)
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
                synStimEpochs = list(filter(lambda x: len(x.getPulseDigitalOutputChannels("all"))>0, digdac.epochs))
            
                if len(synStimEpochs) == 0:
                    raise ValueError("There are no epochs sending digital triggers")
                
            # store these for later
            stimDIG = unique(synStimEpochs[0].getUsedDigitalOutputChannels("all"))
            assert pathway.stimulus.channel in stimDIG
        
#         mbTestEpochs = list(filter(lambda x: x.epochType in (pab.ABFEpochType.Step, pab.ABFEpochType.Pulse) \
#                                             and not any(x.hasDigitalOutput(d) for d in stimDIG) \
#                                             and x.firstLevel !=0 and x.deltaLevel == 0 and x.deltaDuration == 0, 
#                                 dac.epochs))
        
        mbTestEpochs = list(filter(lambda x: x not in synStimEpochs and x.epochType in (pab.ABFEpochType.Step, pab.ABFEpochType.Pulse) \
                                            and x.firstLevel !=0 and x.deltaLevel == 0 and x.deltaDuration == 0, 
                                dac.epochs))
        
        if len(mbTestEpochs) == 0:
            # NOTE: 2024-02-16 22:59:25
            # allow for absence of membrane test epochs
            # if self._clampMode_ == ephys.ClampMode.VoltageClamp:
            #     raise ValueError("No membrane test epoch appears to have been defined")
            membraneTestEpoch = None
            
        else:
            membraneTestEpoch = mbTestEpochs[0]
        
        if membraneTestEpoch is None:
            mbTestAmplitude = None
            mbTestStart = None
            mbTestDuration = None
            signalBaselineStart = 0 * pq.s
            signalBaselineDuration = dac.getEpochRelativeStartTime(synStimEpochs[0], 0)
            responseBaselineStart = signalBaselineStart
            responseBaselineDuration = signalBaselineDuration
        else:
            mbTestAmplitude = membraneTestEpoch.firstLevel
        
            mbTestStart = dac.getEpochRelativeStartTime(membraneTestEpoch, 0)
            mbTestDuration = membraneTestEpoch.firstDuration
            
    # TODO: 2024-02-16 23:03:34
    # carry on with code from processTrackingProtocol @ NOTE: 2024-02-16 23:04:22
        
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
        
        digEpochsTable = digdac.getEpochsTable(0)
        dacEpochsTable = dac.getEpochsTable(0)
        
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
            digEpochsTableAlt = digdac.getEpochsTable(1)
            digEpochsTableAlt_reduced = digEpochsTableAlt.loc[[i for i in digEpochsTableAlt.index if not i.startswith("Digital Pattern")], :]
            assert(np.all(digEpochsTable_reduced == dacEpochsTable_reduced)), "Epochs table mismatch between DAC channels"
            assert(np.all(digEpochsTableAlt_reduced == dacEpochsTable_reduced)), "Epochs table mismatch between DAC channels with alternate digital outputs"
        
        
        # Locate the presynaptic triggers epoch
        # first try and find epochs with digital trains
        # there should be only one such epoch, sending at least one TTL pulse per train
        #
        
        synStimEpochs = list(filter(lambda x: len(x.getTrainDigitalOutputChannels("all"))>0, 
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
            synStimEpochs = list(filter(lambda x: len(x.getPulseDigitalOutputChannels("all"))>0, 
                                        digdac.epochs))
        
            # synStimEpochs = list(filter(lambda x: any(x.hasDigitalPulse(d) for d in stimDIG), 
            #                             digdac.epochs))
            if len(synStimEpochs) == 0:
                raise ValueError("There are no epoch sending digital triggers")
            
        # store these for later
        stimDIG = unique(synStimEpochs[0].getUsedDigitalOutputChannels("all"))
            
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
            self._signalBaselineDuration_ = dac.getEpochRelativeStartTime(synStimEpochs[0], 0)
            self._responseBaselineStart_ = self._signalBaselineStart_
            self._responseBaselineDuration_ = self._signalBaselineDuration_
        else:
            self._mbTestAmplitude_ = self._membraneTestEpoch_.firstLevel
        
            self._mbTestStart_ = dac.getEpochRelativeStartTime(self._membraneTestEpoch_, 0)
            self._mbTestDuration_ = self._membraneTestEpoch_.firstDuration
        
            # NOTE: 2024-02-16 23:04:22
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
            if dac.getEpochRelativeStartTime(self._membraneTestEpoch_, 0) + self._membraneTestEpoch_.firstDuration < digdac.getEpochRelativeStartTime(synStimEpochs[0], 0):
                # membrane test is delivered completely sometime BEFORE triggers
                #
                
                if self._mbTestStart_ == 0:
                    # membrane test is at the very beginning of the sweep (but always 
                    # after the holding time; odd, but allowed...)
                        
                    self._signalBaselineStart_ = 0 * pq.s
                    self._signalBaselineDuration_ = dac.getEpochRelativeStartTime(self._membraneTestEpoch_, 0)
                    
                else:
                    # are there any epochs definded BEFORE mb test?
                    initialEpochs = list(filter(lambda x: dac.getEpochRelativeStartTime(x, 0) + x.firstDuration <=  dac.getEpochRelativeStartTime(self._membraneTestEpoch_, 0) \
                                                        and x.firstDuration > 0 and x.deltaDuration == 0, 
                                                    dac.epochs))
                    
                    if len(initialEpochs):
                        baselineEpochs = list(filter(lambda x: x.firstLevel == 0 and x.deltaLevel == 0, initialEpochs))
                        if len(baselineEpochs):
                            self._signalBaselineStart_ = dac.getEpochRelativeStartTime(baselineEpochs[0], 0)
                            self._signalBaselineDuration_ = baselineEpochs[0].firstDuration
                        else:
                            self._signalBaselineStart_ = 0 * pq.s
                            self._signalBaselineDuration_ = dac.getEpochRelativeStartTime(initialEpochs[0], 0)
                            
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
                                                            and dac.getEpochRelativeStartTime(x, 0) > self._mbTestStart_ + self._mbTestDuration_ \
                                                            and dac.getEpochRelativeStartTime(x, 0) + x.firstDuration <= digdac.getEpochRelativeStartTime(synStimEpochs[0], 0) - self._responseBaselineDuration_,
                                                    dac.epochs))
                
                if len(responseBaselineEpochs):
                    # take the last one
                    self._responseBaselineStart_ = dac.getEpochRelativeStartTime(responseBaselineEpochs[-1], 0)
                
                else:
                    self._responseBaselineStart_ = digdac.getEpochRelativeStartTime(synStimEpochs[0], 0) - 2 * self._responseBaselineDuration_
                    
                
                    
            elif dac.getEpochRelativeStartTime(self._membraneTestEpoch_, 0) > digdac.getEpochRelativeStartTime(synStimEpochs[-1], 0) + synStimEpochs[-1].firstDuration:
                # membrane test delivered somwehere towards the end of the sweep, 
                # surely AFTER the triggers (and hopefully when the synaptic responses
                # have decayed...)
                #
                # in this case, best is to use the first epoch before the synStimEpochs (if any)
                # or the dac holding
                #
                initialEpochs = list(filter(lambda x: dac.getEpochRelativeStartTime(x, 0) + x.firstDuration <=  digdac.getEpochRelativeStartTime(synStimEpochs[0], 0) \
                                                    and x.firstDuration > 0 and x.deltaDuration == 0, 
                                                dac.epochs))
                
                if len(initialEpochs):
                    # there are epochs before synStimEpochs - are any of these baseline-like?
                    baselineEpochs = list(filter(lambda x: x.firstLevel == 0 and x.deltaLevel == 0, initialEpochs))
                    if len(baselineEpochs):
                        self._signalBaselineStart_ = dac.getEpochRelativeStartTime(baselineEpochs[0], 0)
                        self._signalBaselineDuration_ = baselineEpochs[0].firstDuration
                    else:
                        self._signalBaselineStart_ = 0 * pq.s
                        self._signalBaselineDuration_ = dac.getEpochRelativeStartTime(initialEpochs[0], 0)
                        
                else:
                    # no epochs before the membrane test (odd, but can be allowed...)
                    self._signalBaselineStart_ = max(digdac.getEpochRelativeStartTime(synStimEpochs[0], 0) - 2 * dac.holdingTime, 0*pq.s)
                    self._signalBaselineDuration_ = max(dac.holdingTime, synStimEpochs[0].firstDuration)
            
                # Now, determine the response baseline for this scenario.
                responseBaselineEpochs = list(filter(lambda x: x.firstLevel == 0 and x.deltaLevel == 0 and x.firstDuration >= self._responseBaselineDuration_ \
                                                            and dac.getEpochRelativeStartTime(x, 0) > self._mbTestStart_ + self._mbTestDuration_ \
                                                            and dac.getEpochRelativeStartTime(x, 0) + x.firstDuration <= digdac.getEpochRelativeStartTime(synStimEpochs[0], 0) - self._responseBaselineDuration_,
                                                    dac.epochs))
                
                if len(responseBaselineEpochs):
                    # take the last one
                    self._responseBaselineStart_ = dac.getEpochRelativeStartTime(responseBaselineEpochs[-1], 0)
                
                else:
                    self._responseBaselineStart_ = digdac.getEpochRelativeStartTime(synStimEpochs[0], 0) - 2 * self._responseBaselineDuration_
        #
        # 2) create trigger events
        #
        for path in range(protocol.nSweeps):
            pndx = f"path{path}"
            pathEpochs = sorted(synStimEpochs, key = lambda x: dac.getEpochRelativeStartTime(x, path))
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
            self._landmarks_["Rs"] = [dac.getEpochRelativeStartTime(self._membraneTestEpoch_), 
                                      self._responseBaselineDuration_]
            self._landmarks_["Rin"] = [dac.getEpochRelativeStartTime(self._membraneTestEpoch_) + self._membraneTestEpoch_.firstDuration - 2 * self._responseBaselineDuration_,
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
                self._landmarks_["VmTest"] = [dac.getEpochRelativeStartTime(self._membraneTestEpoch_),
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
                 locationMeasures: typing.Optional[typing.Sequence[LocationMeasure]] = None,
                 episodeName: str = "baseline",
                 # episodeName: typing.Union[str, RecordingEpisode] = "baseline",
                 useEmbeddedProtocol:bool=True,
                 trackingClampMode:typing.Union[int, ephys.ClampMode] = ephys.ClampMode.VoltageClamp,
                 conditioningClampMode:typing.Union[int, ephys.ClampMode] = ephys.ClampMode.CurrentClamp,
                 baselineDuration:pq.Quantity = 5 * pq.ms,
                 steadyStateIClampMbTestDuration = 0.05 * pq.s,
                 useSlopeInIClamp:bool = True,
                 signalBaselineStart:typing.Optional[pq.Quantity] = 0 * pq.s,
                 signalBaselineDuration:typing.Optional[pq.Quantity] = None,
                 emitterWindow:typing.Optional[QtWidgets.QMainWindow] = None,
                 directory:typing.Optional[typing.Union[str, pathlib.Path]] = None,
                 autoStart:bool=False, # NOTE: change to True when done coding TODO
                 parent=None,
                 simulate = None,
                 out: typing.Optional[io.TextIOBase] = None):
        """
        
        """
        
        super().__init__(parent=parent)
        
        self._stdout_ = out
        
        self._running_ = False
        self._sources_ = None # preallocate
        # self._locationMeasures_ = locationMeasures
        
        # self._currentEpisodeName_ = episodeName if isinstance(episodeName, str) and len(episodeName.strip()) else "baseline"
        
        # self._currentEpisode_ = RecordingEpisode(name=self._currentEpisodeName_)
        # self._schedule_ = RecordingSchedule(name=" ".join([os.path.basename(os.getcwd()), str(datetime.datetime.now())]))
        
        # self._schedule_.addEpisode(self._currentEpisode_)
        
        self._sources_ = self._check_sources_(*args)
        # NOTE: 2024-02-16 10:56:58
        # having enforced sources with unique names and physical ADC indexes
        # above, the synaptic pathways generated below should be unique
        # More importantly, the SynapticPathway originated from the same source
        # CAN share ADC indexes; however, the ADC indexes across sources MUST be
        # distinct
        self._pathways_ = list(itertools.chain.from_iterable([s.pathways for s in self._sources_]))
        
        # episode = RecordingEpisode(name = episodeName if isinstance(episodeName, str) and len(episodeName.strip()) else "baseline", 
        #                             # protocol = self._runData_.currentProtocol,
        #                             sources = self._sources_,
        #                             pathways = self._pathways_,
        #                             beginFrame = 0)
        #                             # beginFrame=self._runData_.sweeps,
        #                             # begin=abfRun.rec_datetime)
        
        # add first episode in all pathways
        for pathway in self._pathways_:
            pathway.schedule = RecordingSchedule(name=" ".join([os.path.basename(os.getcwd()), str(datetime.datetime.now())]))
            pathway.schedule.addEpisode(RecordingEpisode(name = episodeName if isinstance(episodeName, str) and len(episodeName.strip()) else "baseline", 
                                    pathways = [pathway],
                                    beginFrame = 0))
        
        # self._runData_ = DataBag(pathways = self._pathways_,
        # source still needed to group pathways by sources !!! (saves a few iterations)
        #
        # below:
        # 'pathways' are the pathways as parsed from the sources
        # 'recordedPathways' are the pathays ACTUALLY found in the protocol(s)
        #   taken from the ABF files, hence updated with each abf run; 
        #   this is a dict: (TODO?) source_name+pathway_name ↦ pathway
        #                                                      
        #   
        
        
        self._runData_ = DataBag(sources = self._sources_,
                                 pathways = self._pathways_,
                                 recordedPathways = dict(),
                                 # episodeName = self._currentEpisodeName_,
                                 currentProtocol = None,
                                 # currentEpisode = episode,
                                 sweeps = 0,
                                 # data = self._data_,
                                 # newEpisode = True,
                                 # episodes = dict(), # map episode name to data
                                 abfRunTimesMinutes = list(),
                                 abfRunDeltaTimesMinutes = list(),
                                 # steadyStateIClampMbTestDuration = steadyStateIClampMbTestDuration,
                                 # trackingClampMode = trackingClampMode,
                                 # conditioningClampMode = conditioningClampMode,
                                 signalBaselineStart = signalBaselineStart,
                                 signalBaselineDuration = signalBaselineDuration,
                                 useSlopeInIClamp = useSlopeInIClamp,
                                 responseBaselineDuration = baselineDuration,
                                 locationMeasures = locationMeasures,
                                 # currentProtocolIsConditioning = False,
                                 useEmbeddedProtocol = useEmbeddedProtocol)
        
        
        # TODO: 2024-01-08 00:04:55 FIXME
        # FINALIZE THIS !!!
        #
        
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
                                                             self._runData_,
                                                             self._viewers_,
                                                             self._stdout_)
        
        self._simulation_ = None
        
        self._simulatorThread_ = None
        
        self._doSimulation_ = False
        
        self._simulator_params_ = dict(files=None, timeout=_LTPFilesSimulator_.defaultTimeout)
        
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
            self._simulatorThread_ = _LTPFilesSimulator_(self, self._simulator_params_, self._stdout_)
            self._simulatorThread_.simulationDone.connect(self._slot_simulationDone)
            self._abfSupplierThread_ = _LTPOnlineSupplier_(self, self._abfRunBuffer_,
                                        self._emitterWindow_, self._watchedDir_,
                                        simulator = self._simulatorThread_,
                                        out = self._stdout_)
            
        else:
            self._abfSupplierThread_ = _LTPOnlineSupplier_(self, self._abfRunBuffer_,
                                        self._emitterWindow_, self._watchedDir_,
                                        out = self._stdout_)
        
        self._abfSupplierThread_.abfRunReady.connect(self._abfProcessorThread_.processAbfFile,
                                                     QtCore.Qt.QueuedConnection)
        
        if autoStart:
            self._abfSupplierThread_.start()
            self._abfProcessorThread_.start()
            self._running_ = True

    def __del__(self):
        # we need to check attribute existence to cover the case when we delete
        # an incompletely initialized object
        if hasattr(self, "_running_") and self._running_:
            self.stop()
        try:
            if hasattr(self, "_viewers_"):
                for viewer in self._viewers_.values():
                    viewer.close()
                    
            if hasattr(self, "_emitterWindow_") and self._emitterWindow_.isDirectoryMonitored(self._watchedDir_):
                self._emitterWindow_.enableDirectoryMonitor(self._watchedDir_, False)
                
            if hasattr(self, "_simulatorThread_") and isinstance(self._simulatorThread_, _LTPFilesSimulator_):
                self._simulatorThread_.requestInterruption()
                self._simulatorThread_.quit()
                self._simulatorThread_.wait()
                self._simulatorThread_.deleteLater()
            
            if hasattr(self, "_abfSupplierThread_") and hasattr(self, "_abfProcessorThread_"):
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
            
    def _check_sources_(self, *args):
        """Verifies consistency of recording sources:
        Requirements are either hard (•) or soft (∘); unmet soft requirements
        will cause adjustments to be made to the sources; unmed hard requirements
        will raise exceptions
        Distinct sources require:
        • distinct ADC
        • distinct DAC
        • distinct SynapticStimulus configurations
        ∘ distinct name
        ∘ when several sources have SynapticStimulus configured, these SynapticStimulus
            must have distinct names across all the sources
        """
        # print(f"{self.__class__.__name__}._check_sources_: args = {args}")
        if len(args) == 0:
            raise ValueError("I must have at least one RecordingSource defined")
            # self._sources_ = None
            # TODO: 2024-01-04 22:19:44 
            # write code to infer RecordingSource from first ABF file (in _LTPOnlineFileProcessor_)
            # NOTE: 2024-02-12 08:46:34
            # this is difficult due to ambiguities when two ADCs are used, e.g.,
            # when recording secondary amplifier output as well (useful to infer
            # the command signal waveforms when the protocol is not accessible)

        if not all(isinstance(a, RecordingSource) for a in args):
            raise TypeError(f"Expecting one or more RecordingSource objects")
        
        dupsrc = duplicates(args, indices=True)
        
        if len(dupsrc):
            raise ValueError(f"Duplicate sources detected in 'args': {dupsrc}")
    
        # parse sources from args; make sure there are identical names
        dupNames = duplicates([a.name for a in args], indices=True)

        if len(dupNames):
            warnings.warn("The sources do not have unique names; names will be adapted.")
            snames = list()
            _sources = list()
            for src in args:
                if src.name not in snames:
                    snames.append(src.name)
                    _sources.append(src)
                    
                else:
                    # adapt name to avoid duplicates; since an ephys.RecordingSource is 
                    # an immutable named tuple, we use its _replace method to create
                    # a copy with a new name
                    new_name = utilities.counter_suffix(src.name, snames)
                    snames.append(new_name)
                    _sources.append(src._replace(name=new_name))
                    
            # now use these as args
            args = _sources
                    
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
        syndacs = set(itertools.chain.from_iterable(s.syn_dac for s in args))
        
        # DACs used to emulate TTLs for other purposes
        ttldacs = set(itertools.chain.from_iterable(s.out_dac_triggers for s in args))
        
        # DACs used to emit waveforms other than clamping
        # these should REALLY be distinct from ttldacs
        cmddacs = set(itertools.chain.from_iterable(s.other_outputs for s in args))
        
        # DIGs used for synaptic stimulation
        syndigs = set(itertools.chain.from_iterable(s.syn_dig for s in args))
        
        # DIGs used to trigger anything other than synapses
        digs = set(itertools.chain.from_iterable(s.out_dig_triggers for s in args))
        
        
        # 1. all sources must have a primary ADC
        if any(s.adc is None for s in args):
            raise ValueError("All source must specify a primary ADC input")
        
        adcs, snames  = list(zip(*[(s.adc, s.name) for s in args]))
        
        # 2. primary ADCs cannot be shared among sources
        dupadcs     = duplicates(adcs)  # sources must have distinct main ADCs
        if len(dupadcs):
            raise ValueError(f"Sharing of primary ADCs ({dupadcs}) among sources is forbidden")
        
        # 3. source names should be unique
        dupnames = duplicates(snames)
        if len(dupnames):
            raise ValueError(f"RecordingSource objects must have distinct names; instead got the following duplicates ({dupnames})")
            
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
        
        clamped_sources = [s for s in args if s.clamped]
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
        
        # 6. in each RecordingSource, the SynapticStimulus objects must have unique names 
        # and channels, but OK to share across sources
        
        for k, s in enumerate(args):
            if isinstance(s.syn, typing.Sequence):
                assert len(set(s_.name for s_ in s.syn)) == len(s.syn), f"{k}ᵗʰ source ({s.name}) has duplicate names for SynapticStimulus"
        
        #
        #### END   Checks
        
        return args
        
    def print(self, msg):
        if isinstance(self._stdout_, io.TextIOBase):
            print(msg, file = self._stdout_)
        else:
            print(msg)
               
    @pyqtSlot()
    def slot_doWork(self):
        self.start()
        
    @pyqtSlot()
    def _slot_simulationDone(self):
        self.print(f"\n{self.__class__.__name__}.run: {colorama.Fore.YELLOW}{colorama.Style.BRIGHT}Simulation done!{colorama.Style.RESET_ALL}\n")
        self.stop()
        
    @property
    def running(self) -> bool:
        return self._running_
    
    @property
    def currentEpisodes(self) -> dict:
        """List of the most recent episodes across pathways"""
        return [p.schedule.episodes[-1] for p in self._runData_.pathways]
        # return dict((s, dict((p.name, p.schedule.episodes[-1]) for p in self._runData_.pathways if p.source == s)) for s in self._runData_.sources)
    
    def newEpisode(self, val:str, etype: typing.Union[RecordingEpisodeType, str, int] = RecordingEpisodeType.Tracking,
                   pathway:typing.Optional[typing.Union[SynapticPathway, int, str, typing.Sequence[SynapticPathway], typing.Sequence[int], typing.Sequence[str]]] = None):
        if len(self._runData_.pathways) == 0:
            scipywarn("No pathways are defined", out = self._stdout_)
            return
        
        if not isinstance(val, str) or len(val.strip()) == 0:
            return
        
        if isinstance(pathway, (list, tuple)):
            if all(isinstance(p, int) for p in pathway):
                invalid = [(k, p) for k, p in enumerate(pathway) if p < 0 or p >= len(self._runData_.pathways)]
                if len(invalid):
                    raise ValueError(f"The following elements in the sequence of path indexes are invalid for {len(self._runData_.pathways)} pathways: {' '.join([f'element {k}: path {l}' for k,l in invalid])}")
                
                pathway = [self._runData_.pathways[k] for k in pathway]
                
            elif all (isinstance(p, str) for p in pathway):
                pnames = [p.name for p in self._runData_.pathways]
                
                invalid = [(k,p) for k, p in enumerate(pathway) if p not in pnames]
                
                if len(invalid):
                    raise ValueError(f"The following path names do not exist: {' '.join([f'element {k}: path {l}' for k,l in invalid])}")
                
                pathway = [self._runData_pathways[pnames.index(p)] for p in pathway]
                
            elif not all(isinstance(p, SynapticPathway) for p in pathway):
                raise TypeError("'pathway' expected to be a sequence of SynapticPathway, or int indexes, or str names")
        
        elif isinstance(pathway, int):
            if pathway < 0 or pathway >= len(self._runData_.pathways):
                raise ValueError(f"Invalid pathway index {pathway} for {len(self._runData_.pathways)} pathway(s)")
            
            pathway = self._runData_.pathways[pathway]
            
        elif isinstance(pathway, str):
            pnames = [p.name for p in self._runData_.pathways]
            if pathway not in pnames:
                raise ValueError(f"Pathway {pathway} not found")
            
            pathway = self._runData_.pathways[pnames.index(pathway)]
            
        elif not isinstance(pathway, SynapticPathway):
            raise TypeError(f"'pathway' expected to be a SynapticPathway, int index or str name, or a sequence of these; instead, got {type(pathway).__name__}")
        
        # from here onwards, `pathway` is either a SynapticPathway, or a list of SynapticPathway objects
        
        if isinstance(etype, int):
            if etype not in RecordingEpisodeType.values():
                raise ValueError(f"Invalid episode type {etype}")
            etype = RecordingEpisodeType(etype) # will raise ValueError if etype is invalid
            
        elif isinstance(etype, str):
            if etype.capitalize() not in RecordingEpisodeType.names():
                raise ValueError(f"Invalid episode type {etype}")
            etype = RecordingEpisodeType.type(etype)
            
        elif not isinstance(etype, RecordingEpisodeType):
            raise TypeError(f"'etype' expected to be a RecordingEpisodeType, a str or an int; instead, got {type(etype).__name__}")
        
        
        if isinstance(pathway, SynapticPathway):
            if pathway not in self._runData_.pathways:
                scipywarn(f"Pathway {pathway.name} not found", out=self._stdout_)
                return
            
            names = unique(e.name for e in pathway.schedule.episodes)
            episodeName = counter_suffix(val, names)
            lastFrame = max(e.endFrame for e in pathway.schedule.episodes)
            
            pathway.schedule.addEpisode(RecordingEpisode(etype, 
                                                         name = episodeName, 
                                                         pathways = [pathway],
                                                         beginFrame  = lastFrame + 1,
                                                         endFrame = lastFrame + 1))
            
        else:
            names = unique(list(itertools.chain.from_iterable([[e.name for e in p.schedule.episodes] for p in pathway])))
            episodeName = counter_suffix(val, names)
            
            for p in pathway:
                lastFrame = max(e.endFrame for e in p.schedule.episodes)
                p.schedule.addEpisode(RecordingEpisode(etype,
                                                       name = episodeName if isinstance(episodeName, str) and len(episodeName.strip()) else "baseline", 
                                                       pathways = [p], 
                                                       beginFrame = lastFrame+1,
                                                       endFrame = lastFrame + 1))
            
        
    def pause(self):
        """Pause the simulation.
        Does nothing when LTPOnline is running in normal mode (i.e. is waiting for
        files produced by the acquisition software).
        """
        if self._doSimulation_ and isinstance(self._simulatorThread_, _LTPFilesSimulator_):
            self._simulatorThread_.requestInterruption()
        
    def resume(self):
        """Resumes simulation, if there are files left in the simulation stack.
        Does nothing when LTPOnline is running in normal mode (i.e. is waiting for
        files produced by the acquisition software).
        
        """
        if self._doSimulation_ and isinstance(self._simulatorThread_, _LTPFilesSimulator_):
            self._simulatorThread_.resume()
        
        
    def stop(self):
        if self._doSimulation_ and isinstance(self._simulatorThread_, _LTPFilesSimulator_):
            self._simulatorThread_.requestInterruption()
            self._simulatorThread_.quit()
            self._simulatorThread_.wait()
            
        # NOTE: 2024-02-09 08:14:30
        # this will never occur
        # if isinstance(self._abfSupplierThread_, FileStatChecker):
        #     self._abfSupplierThread_.abfListener.stop()
            
            
        self._abfSupplierThread_.quit()
        self._abfSupplierThread_.wait()
        self._abfProcessorThread_.quit()
        self._abfProcessorThread_.wait()
        
        if self._emitterWindow_.isDirectoryMonitored(self._watchedDir_):
            self._emitterWindow_.enableDirectoryMonitor(self._watchedDir_, False)
            
        self.resultsReady.emit(self._runData_)
        
        self._running_ = False
        
        if self._doSimulation_:
            wf.assignin(self._runData_, "rundata")
        
        
        
    def reset(self, *args):
        if len(args):
            self._check_sources_(args)
        # self._monitorProtocol_ = None
        # self._conditioningProtocol_ = None
        
#         self._data_["baseline"]["path0"].segments.clear()
#         self._data_["baseline"]["path1"].segments.clear()
#         self._data_["chase"]["path0"].segments.clear()
#         self._data_["chase"]["path1"].segments.clear()
#         self._data_["conditioning"]["path0"].segments.clear()
#         self._data_["conditioning"]["path1"].segments.clear()
#         
#         if self._clampMode_ == ephys.ClampMode.VoltageClamp:
#             self._results_ = {"path0": {"Response0":[], "Response1":[], "PairedPulseRatio":[]},
#                               "path1": {"Response0":[], "Response1":[], "PairedPulseRatio":[]},
#                               "DC": [], "Rs":[], "Rin":[], }
#             
#             self._landmarks_ = {"Rbase":[self._signalBaselineStart_, self._signalBaselineDuration_], 
#                                 "Rs":[None, None], 
#                                 "Rin":[None, None], 
#                                 "PSCBase":[None, None],
#                                             
#                                 "PSC0Peak":[None, None], 
#                                 "PSC1Peak":[None, None]}
#     
#         else:
#             self._results_ = {"path0": {"Response0":[], "Response1":[], "PairedPulseRatio":[]},
#                               "path1": {"Response0":[], "Response1":[], "PairedPulseRatio":[]},
#                               "tau":[], "Rin":[], "Cap":[], }
#             
#             if self._useSlopeInIClamp_:
#                 self._landmarks_ = {"Base":[self._signalBaselineStart_, self._signalBaselineDuration_], 
#                                     "VmTest":[None, None], 
#                                     "PSP0Base":[None, None],
#                                     "PSP0Peak":[None, None],
#                                     "PSP1Base":[None, None],
#                                     "PSP1Peak":[None, None]}
#             else:
#                 self._landmarks_ = {"Base":[self._signalBaselineStart_, self._signalBaselineDuration_], 
#                                     "VmTest":[None, None], 
#                                     "PSPBase":[None, None],
#                                     "PSP0Peak":[None, None],
#                                     "PSP1Peak":[None, None]}
        
                
        for viewer in self._viewers_.values():
            viewer.clear()
            
        return True
            

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

# def make2PathwaysLTPSource(name:str, adc:int=0, dac:int=0, dig0:int=0, dig1:int=1):
#     """Factory function for a RecordingSource in two pathways LTP.
#     
#     Named parameters:
#     -----------------
#     adc, dac: int, index of the ADC and DAC channels used in the experiment
#     
#     """
#     assert all(isinstance(v, int) for v in (adc, dac, dig0, dig1)), "The `adc`, `dac`, `dig0`, `dig1` parameters must be of type int"
#     assert dig0 != dig1, "In two pathway experiments the digital stimulation channels must be distinct"
#     
#     digs = (dig0, dig1)
#     if any(d < 0 for d in digs):
#         raise ValueError(f"All digital channels must be >= 0; got {digs} instead")
#     
#     
#     synStims = [SynapticStimulus(f"path{k}", digs[k]) for k in range(len(digs))]
#     
#     return RecordingSource(name, 0, 0, synStims)
#     

