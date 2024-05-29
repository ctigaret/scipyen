# -*- coding: utf-8 -*-

#### BEGIN core python modules
import os, sys, traceback, inspect, numbers, warnings, pathlib, time, io
import datetime
import functools, itertools, more_itertools
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

from qtpy import QtCore, QtGui, QtWidgets, QtXml
from qtpy.QtCore import Signal, Slot
from qtpy.uic import loadUiType as __loadUiType__ 
# from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml
# from PyQt5.QtCore import Signal, Slot
# from PyQt5.uic import loadUiType as __loadUiType__ 

#### END 3rd party modules

#### BEGIN pict.core modules
import core.workspacefunctions as wf
from core.workspacefunctions import (user_workspace, validate_varname, 
                                     get_symbol_in_namespace, assignin)
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
from core.prog import (safeWrapper, AttributeAdapter, with_doc, 
                       printStyled, scipywarn)
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
                            safe_identity_test,
                            eq,
                            sp_set_loc,
                            normalized_index,
                            unique,
                            duplicates,
                            GeneralIndexType,
                            counter_suffix,
                            yyMdd,
                            NestedFinder)

from core.scipyen_config import (markConfigurable)


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
from gui.cursors import (SignalCursor, DataCursor, SignalCursorTypes)
from gui.workspacegui import (DirectoryFileWatcher, FileStatChecker, 
                              WorkspaceGuiMixin)
from gui import scipyen_colormaps as colormaps
#### END pict.gui modules

#### BEGIN pict.iolib modules
import iolib.pictio as pio
#### END pict.iolib modules

from ephys.ephys_protocol import ElectrophysiologyProtocol
import ephys.ephys as ephys
from ephys.ephys import (ClampMode, ElectrodeMode, LocationMeasure,
                         RecordingSource, RecordingEpisode, RecordingEpisodeType,
                         RecordingSchedule,
                         SynapticStimulus, SynapticPathway, SynapticPathwayType,
                         AuxiliaryInput, AuxiliaryOutput,
                         synstim, auxinput, auxoutput, 
                         amplitudeMeasure, chordSlopeMeasure, durationMeasure)

import ephys.membrane as membrane


LTPOptionsFile = os.path.join(os.path.dirname(__file__), "options", "LTPOptions.pkl")
optionsDir     = os.path.join(os.path.dirname(__file__), "options")

__module_path__ = os.path.abspath(os.path.dirname(__file__))
# __ui_path__ = adapt_ui_path(__module_path__,"LTPWindow.ui")
__ui_path__ = adapt_ui_path(__module_path__,"LTPOnline.ui")
    
if os.environ["QT_API"] in ("pyqt5", "pyside2"):
    __UI_LTPWindow__, __QMainWindow__ = __loadUiType__(__ui_path__, 
                                                    from_imports=True, 
                                                    import_from="gui") #  so that resources can be imported too
else:
    __UI_LTPWindow__, __QMainWindow__ = __loadUiType__(__ui_path__) #  so that resources can be imported too

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
    • `auxin` and `auxout`, and by default are set to 'None'.
    • `path0name` and `path1name`: both strings -- custom names for the two pathways
        ∘ by default, these are set to 'path0' and 'path1', respectively
        ∘ when given, they should be different
    
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
    
    p0name = kwargs.get("path0name", 'path0')
    p1name = kwargs.get("path1name", 'path1')
        
    syn     = (SynapticStimulus(p0name, path0), SynapticStimulus(p1name, path1)) 
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
    
    simulationDone = Signal(name = "simulationDone")
    
    supplyFile = Signal(pathlib.Path, name = "supplyFile")
    
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

            # print(f"{self.__class__.__name__}._simulationTimeOut_ = {self._simulationTimeOut_}")
            
            files = simulation.get("files", None)
            
            directory = simulation.get("dir" , None)
            
            if not (isinstance(directory, str) and os.path.isdir(directory)) or not (isinstance(directory, pathlib.Path) and directory.is_dir()):
                directory = os.getcwd()
            
            if not isinstance(files, (list, tuple)) or len(files) == 0 or not all(isinstance(v, (str, pathlib.Path)) for v in files):
                files = None
            
        if files is None:
            self.print(f"{self.__class__.__name__}:\n Looking for ABF files in directory: ({directory}) ...")
            files = os.listdir(directory)
            # files = subprocess.run(["ls"], capture_output=True).stdout.decode().split("\n")
            # print(f" Found {len(files)} ABF files")
        
        if isinstance(files, list) and len(files) > 0 and all(isinstance(v, (str, pathlib.Path)) for v in files):
            simFilesPaths = list(filter(lambda x: x.is_file() and x.suffix == ".abf", [pathlib.Path(v) for v in files]))
            
            if len(simFilesPaths):
                self.print(f"... found {(len(simFilesPaths))} ABF files")
                # NOTE: 2024-01-08 17:45:21
                # bound to introduce some delay, but needs must, for simulation purposes
                # print(f" Sorting {len(simFilesPaths)} ABF data based on recording time ...")
                self._simulationFiles_ = sorted(simFilesPaths, key = lambda x: pio.loadAxonFile(x).rec_datetime)
                # print(" ... done.")
                
        if len(self._simulationFiles_) == 0:
            self.print(f" No Axon binary files (ABF) were supplied, and no ABFs were found in current directory ({os.getcwd()})")
               
    def print(self, msg):
        if isinstance(self._stdout_, io.TextIOBase):
            print(msg, file = self._stdout_)
        else:
            print(msg)
               
    def run(self):
        self._simulationCounter_ = 0
        for k,f in enumerate(self._simulationFiles_):
            # self.print(f"\n****\n{self.__class__.__name__}.run: simulation counter {self._simulationCounter_}\n reading file {k}: {colorama.Fore.RED}{colorama.Style.BRIGHT}{f}{colorama.Style.RESET_ALL}")
            self.simulateFile()
            if self.isInterruptionRequested():
                self.print(f"\n{self.__class__.__name__}.run: {printStyled('Interruption requested', 'yellow', False)}\n")
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
                # self.print(f"\n****\n{self.__class__.__name__}.run: simulation counter {self._simulationCounter_}\n reading file {k}: {colorama.Fore.RED}{colorama.Style.BRIGHT}{f}{colorama.Style.RESET_ALL} for simulation counter {self._simulationCounter_}")
                self.simulateFile()
                if self.isInterruptionRequested():
                    self.print(f"\n{self.__class__.__name__}.run: {printStyled('Interruption requested', 'yellow', False)}\n")
                    break
                QtCore.QThread.sleep(int(self._simulationTimeOut_/1000)) # seconds!
                
            if k < (len(self._simulationFiles_)-1):
                self._paused_ = True
                
            else:
                self.simulationDone.emit()
                
    @Slot()
    def simulateFile(self):
        if self._simulationCounter_ >= len(self._simulationFiles_):
            self.simulationDone.emit()
            return
        
        self._simulatedFile_ = self._simulationFiles_[self._simulationCounter_]
        self._simulationCounter_ += 1
        
        self.supplyFile.emit(self._simulatedFile_)
        
        
class _LTPOnlineSupplier_(QtCore.QThread):
    """Monitors files output by electrophysiology acquisition software in a directory.
        
        New files output to the directory are then fed into _LTPOnlineFileProcessor_
        
    
    WARNING: Currently this only supports ABF file output from Clampex™, and ONLY
        for Clampex protocols generating auto-averaged data (i.e., it relies on 
        intermediate, temporary, '*.rsv' files being output into the monitored
        directory). The ABF file is supplied to the online file procssor once the
        corresponding *.rsv file has been deleted by Clampex.
        
    """
    abfTrialReady = Signal(pathlib.Path, name="abfTrialReady")
    stopTimer = Signal(name="stopTimer")
    
    def __init__(self, parent: QtCore.QObject,
                 abfTrialBuffer: collections.deque, 
                 emitterWindow: QtCore.QObject,
                 directory: pathlib.Path,
                 simulator: typing.Optional[_LTPFilesSimulator_] = None,
                 out: typing.Optional[io.TextIOBase] = None):
        """
        """
        QtCore.QThread.__init__(self, parent)
        self._abfTrialBuffer_ = abfTrialBuffer
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
        """Callback needed by DirectoryFileWatcher. Does nothing here..."""
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

        # self.print(f"{self.__class__.__name__}._setupPendingAbf_:")
        # self.print(f"\tfiles queue: {self._filesQueue_}")

        if len(self._filesQueue_) < 2:
            return

        latestFile = self._filesQueue_[-1]
        # self.print(f"\tlatest file: {latestFile}")

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

        # self.print(f"\tpending: {self._pending_}")
        # self.print(f"\tqueue: {self._filesQueue_}")
            
    def print(self, msg):
        if isinstance(self._stdout_, io.TextIOBase):
            print(msg, self._stdout_)
        else:
            print(msg)
               
    def run(self):
        if isinstance(self._simulator_, _LTPFilesSimulator_):
            self._simulator_.start()
        else:
            # starts directory monitor and captures newly created files
            if not self._emitterWindow_.isDirectoryMonitored(self._watchedDir_):
                self._emitterWindow_.enableDirectoryMonitor(self._watchedDir_, True)
    
    @Slot()
    def quit(self):
        if isinstance(self._simulator_, _LTPFilesSimulator_):
            if self._simulator_.isRunning():
                self._simulator_.requestInterruption()
                self._simulator_.quit()
                self._simulator_.wait()
                
        if self._emitterWindow_.isDirectoryMonitored(self._watchedDir_):
            self._emitterWindow_.enableDirectoryMonitor(self._watchedDir_, False)

        super().quit()

    @Slot(pathlib.Path)
    def _simulateFile_(self, value):
        # print(f"{self.__class__.__name__}._simulateFile_: {value}")
        
        self.supplyFile(value)
            
    def supplyFile(self, abfFile:pathlib.Path):
        """Callback called by FileStatChecker"""
        # print(f"{self.__class__.__name__}.supplyFile to buffer: abfFile {abfFile.name}\n")
        self._abfListener_.reset()
        self.abfTrialReady.emit(abfFile)
        
    @property
    def abfListener(self) -> FileStatChecker:
        return self._abfListener_
    
    @property
    def watchedDirectory(self) -> pathlib.Path:
        return self._watchedDir_
    
    @watchedDirectory.setter
    def watchedDirectory(self, val:pathlib.Path) -> None:
        self._dirMonitor_.directory = val
        self._watchedDir_ = self._dirMonitor_.directory
    

class _LTPOnlineFileProcessor_(QtCore.QThread):
    """Helper class for LTPOnline.
        Provides a thread for the analysis of a single Clampex trial. 
        
        Also used in simulation mode.
        
    """
    sig_xtalk = Signal(bool, name="sig_xtalk")
    sig_processingFile = Signal(object, name="sig_processingFile")
    
    # TODO: 2024-03-03 22:09:16
    # detect triggers and add trigger events to the pathway blocks?
    # maybe ...
    
    # NOTE: 2024-02-08 15:05:35
    # for each source in _runData_.sources, determine the relationships between
    # a DAC, input signal (logical ADC) and stimulus channels
    #
    # CAUTION: all ADC/DAC signals indexes in a source are PHYSICAL indexes
    #
    # also, each paths have "equal" until an induction protocol is supplied,
    # which will determine the identity of test and control pathways
    #
    def __init__(self, parent:QtCore.QObject, emitter,
                 abfBuffer:collections.deque,
                 abfTrialData:dict,
                 out: typing.Optional[io.TextIOBase] = None):
        QtCore.QThread.__init__(self, parent)
        
        self._emitter_ = emitter
        self._abfTrialBuffer_ = abfBuffer
        self._runData_ = abfTrialData
        self._stdout_ = out
        
        # maps source
        self._monitor_protocols_ = dict()
        
        
    def print(self, msg:object):
        if isinstance(self._stdout_, io.TextIOBase):
            print(msg, file=self._stdout_)
        else:
            print(msg)
            
    def genEpisode(self, episodeType, episodeName):
        return RecordingEpisode(episodeType, name=episodeName)
        
#     def _parseABFProtocolOutputs(self, protocol:pab.ABFProtocol):
#         # NOTE: 2024-02-17 14:14:17
#         # Clampex supports stimulation of up to TWO distinct synaptic pathways
#         # (i.e. via axonal inputs) for one recording source (cell or field),
#         # using the 'alternative digital outputs' mechanism. 
#         # The run should have an even number of sweeps — ideally, just two,
#         # and a trial MAY consist of several runs (thus, the ABF file will 
#         # store the sweep-by-sweep AVERAGE signals, here resulting in a neo.Block
#         # with the same number of sweeps per run).
#         #
#         # (this is clearly less flexible than CED's Signal software)
#         #
#         # Of course, one can configure an odd number of sweeps (e.g., 3) per
#         # run, but in this case, the last sweep will be a supplementary record
#         # of the "main" pathway (i.e., the first of the two stimulated pathways)
#         # whereas the second pathway would end up with fewer stimulations...
#         #
#         # NOTE: 2024-02-17 13:51:25
#         # if there are more than one pathway associated with this source, 
#         # the following SOFT requirements should be met:
#         #
#         # 1 alternative digital outputs enabled, to allow temporal (sweep-wise)
#         #   separation of pathway responses: responses in both pathways are 
#         #   recorded through the same electrode; therefore, stimulating them 
#         #   in alternate sweeps is the only practical solution to distinguish
#         #   them)
#         #
#         #   NOTE: this applies to tracking (or monitoring) protocols; in contrast,
#         #   conditioning protocols, by definition, affect only a single pathway 
#         #   (otherwise there would be no justification for recording from a 
#         #   second pathway).
#         #
#         #   Technically, conditioning may also affect supplemetary pathways (e.g.
#         #   a "weak" associative or cooperative pathway) but these are not 
#         #   typically being monitored for plasticity; if they were, this would
#         #   would not be possible with a single Clampex protocol.
#         #
#         #   To develop this idea: in Clampex, one would have to configure
#         #   distinct protocols to record any one of, say, three pathways; 
#         #   these protocols would then be interleaved in a sequence, such that
#         #   the three pathways would be recorded separately in the same order,
#         #   over and over again; furthermore, this would preclude any "auto-averaging" 
#         #   (i.e., each of these protocols would consist of one run per trial, 
#         #   ideally with one sweep per run, dedicated entirely to the pathway concerned)
#         #   and the protocol should have alternateDigitalOutputStateEnabled False.
#         #
#         #   ### TODO: 2024-02-17 22:56:15
#         #   To accommodate this, we must avoid setting up a new episode when the 
#         #   ABF protocol has changed (see processAbfFile(…)); instead a new episode
#         #   must be initiated manually through the LTPOnline API; also augment
#         #   the API to configure averaging !
#         #   ###
#         #
#         #
#         # 2 protocol should have an even number of sweeps per run ⇒ even number
#         #   of sweeps per trial recorded in the ABF file ⟹
#         #   ⋆ main path (path 0) on even-numbered sweeps (0, 2, etc)
#         #   ⋆ alternate path (path 1) on odd-numbered sweeps (1, 3, etc)
#         #
#         #   NOTE: an odd number of sweeps implies that the last sweep carries 
#         #   data for the main path (path 0)
#         #
#         #   e.g. for three sweeps per run, sweeeps 0 and 2 carry path 0, whereas
#         #   sweep 1 carries path 1
#         #
#         # 3 alternative waveforms DISABLED to allow the membrane test to be
#         #   be performed (via DAC command signal) in every sweep; if this WAS
#         #   enabled, then analog commands would be send via the DAC channel 
#         #   where the alternative digital stimulation pattern is defined;
#         #   since this DAC is NOT connected to the recording electrode for this
#         #   source, any analog commands emitted by this DAC would end up elsewhere
#         #
#         #   (REMEMBER: One DAC channel per electrode ≡ 1 DAC channel per recording source)
#         #
#         #       — this is a direct consequence of the uninspired way in 
#         #       which Clampex configures digital outputs in their protocol 
#         #       editor GUI: in reality the DIG outputs are NEVER sent through 
#         #       a DAC so they should have created a separate dialog outside 
#         #       the WAVEFORM tabs
#         #
#         # The above prerequisites also have the consequencess below, regarding 
#         #   the use of "supplementary" DACs (with higher index):
#         # • if a supplementary DAC also defines epochs wih DIG enabled, these
#         #   will be included in the alternative DIG pattern (inluding any
#         #   additional DIG output channels) — this is NOT what you may intend.
#         #
#         #   the only possible advantage I can see is triggering a 3ʳᵈ party 
#         #   device e.g. photoactivation/uncaging; the DISadvantage is that ALL
#         #   extra DIG outputs will be subject to the same pattern...
#         #
#         # • if a supplementary DAC defines epochs for analog command waveforms,
#         #   this DAC should have an index higher than all DACs used to deliver 
#         #   amplifier commands (i.e., ≥ 2); this DAC can only be used to send 
#         #   TTL-emulating waveforms to 3ʳᵈ party devices
#         #
#         #   In such cases, alternative waveforms should be ENABLED, waveform
#         #   output in the "alternative" DAC should be DISABLED, and waveform
#         #   output in the supplementary (higher index) DAC should be ENABLED. 
#         #   This situation will result in:
#         #   ∘ a membrane test (for the clamped recorded source) being 
#         #   applied ONLY during the "main" pathway stimulation (which is fine,
#         #   since one may argue that the "alternative" pathway records from
#         #   the same source or cell anyway, so applying a membrane test there
#         #   is redundant)
#         #   ∘ create room for configuring emulated TTLs in the supplementary
#         #       DAC (with higher index) to trigger a 3ʳᵈ party device ONLY
#         #       during the "alternative" pathway stimulation
#         
#         # this channel is the one where DIG outputs are configured; it MAY BE
#         # distinct from the source.dac !!!
#         activeDAC = protocol.getDAC() # this is the `digdac` in processTrackingProtocol
#         
#         # these are the protocol's DACs where digital output is emitted during the recording
#         # the active DAC is one of these by definition
#         # WARNING: do NOT confuse with DACs that emulate TTLs
#         digOutDacs = protocol.digitalOutputDACs
# 
#         # will be an empty set if len(digOutDacs ) == 0
#         mainDIGOut = protocol.digitalOutputs(alternate=False)
#         
#         # this is an empty set when alternateDigitalOutputStateEnabled is False;
#         # also, will be empty if len(digOutDacs ) == 0
#         altDIGOut = protocol.digitalOutputs(alternate=True)
#         
#         return activeDAC, digOutDacs, mainDIGOut, altDIGOut
    
    @safeWrapper
    @Slot(pathlib.Path)
    def processAbfFile(self, abfFile:pathlib.Path):
        """Reads and ABF protocol from the ABF file and analyses the data
        """
        # NOTE: 2024-03-03 09:18:08
        # we rely completely on parsing the ABF protocol, given the ABF trial files
        # furthermore, we assume:
        # • the recording starts with a tracking protocol, which must be the same
        #   for both baseline and chase (i.e. BEFORE and AFTER pathway conditioning)
        # • we measure synaptic responses and membrane test parameters ONLY in 
        #   ABF trials recorded using this tracking protocol 
        # • ABF trials recorded with other protocols are ignored; this includes
        #   cross-talk trials and the pathway conditioning trial
        
        self.print(f"\n{self.__class__.__name__}.processAbfFile {printStyled(abfFile, 'yellow', True)}")
        
        self.sig_processingFile.emit(abfFile)

        try:
            currentAbfTrial = pio.loadAxonFile(str(abfFile))
            protocol = pab.ABFProtocol(currentAbfTrial)
            # self.print(f"\twith protocol {colorama.Fore.RED}{colorama.Style.BRIGHT}{protocol.name}{colorama.Style.RESET_ALL}\n")
            opMode = protocol.acquisitionMode # 
            if isinstance(opMode, (tuple, list)): # FIXED 2024-03-08 22:32:14, see pyabfbridge.py NOTE: 2024-03-08 22:33:34 and NOTE: 2024-03-08 22:32:29
                opMode = opMode[0]

            if opMode != pab.ABFAcquisitionMode.episodic_stimulation:
                scipywarn(f"In {currentAbfTrial.name}: File {abfFile} was not recorded in episodic stimulation mode and will be skipped")
                return

            # check that the number of sweeps actually stored in the ABF file/neo.Block
            # equals that advertised by the protocol
            # NOTE: mismatches can happen when trials are acquired very fast (i.e.
            # back to back) - in this case check the sequencing key in Clampex
            # and set an appropriate interval between successive trials !
            #
            # NOTE: 2024-03-03 09:27:52
            # soften the asssertion below, just skip the file
            # assert(protocol.nSweeps) == len(self._runData_.currentAbfTrial.segments), f"In {self._runData_.currentAbfTrial.name}: Mismatch between number of sweeps in the protocol ({protocol.nSweeps}) and actual sweeps in the file ({len(self._runData_.currentAbfTrial.segments)}); check the sequencing key?"
            #
            if len(currentAbfTrial.segments) != protocol.nSweeps:
                scipywarn(f"In {currentAbfTrial.name}: Mismatch between number of sweeps in the protocol ({protocol.nSweeps}) and actual sweeps in the file ({len(self._runData_.currentAbfTrial.segments)}); the ABF trial file {abfFile} will be skipped")
                return

            self._runData_.abfTrialTimesMinutes.append(currentAbfTrial.rec_datetime)
            deltaMinutes = (currentAbfTrial.rec_datetime - self._runData_.abfTrialTimesMinutes[0]).seconds/60
            self._runData_.abfTrialDeltaTimesMinutes.append(deltaMinutes)
            
            # NOTE: 2024-02-08 14:18:32
            # self._runData_.currentAbfTrial should be a neo.Block or None
            if isinstance(self._runData_.currentAbfTrial, neo.Block):
                # cache the previous trial
                self._runData_.prevAbfTrial = self._runData_.currentAbfTrial
            self._runData_.currentAbfTrial = currentAbfTrial
            
            # new episode requested via _runData_ ⇒
            # create a new episode here, using _runData_.newEpisodeOnNextRun
            if len(self._runData_.newEpisodeOnNextRun) == 2:
                if len(self._runData_.episodes):
                    #  NOTE: 2024-05-13 08:47:25
                    # finalize the previous episode
                    # the current protocol hasn't been processed yet, therefore
                    # sweeps from current trial haven't been distributed yet,
                    # across pathways.
                    self._runData_.episodes[-1].endFrame = self._runData_.sweeps - 1 if self._runData_.sweeps > 0 else 0
                    if isinstance(self._runData_.prevAbfTrial, neo.Block):
                        self._runData_.episodes[-1].end=self._runData_.prevAbfTrial.rec_datetime
                    else:
                        self._runData_.episodes[-1].end=self._runData_.currentAbfTrial.rec_datetime
                    
                eType, eName = self._runData_.newEpisodeOnNextRun
                episode = RecordingEpisode(eType, name=eName, protocol=protocol)
                episode.begin = currentAbfTrial.rec_datetime
                # NOTE: 2024-05-13 08:49:42
                # next episode starts with the next sweep (which hasn't been added yet)!
                episode.beginFrame = self._runData_.sweeps
                self._runData_.episodes.append(episode)
                self._runData_.newEpisodeOnNextRun = tuple() # invalidate the request
            
            if len(self._runData_.episodes) == 0:
                episode = RecordingEpisode(RecordingEpisodeType.Tracking, name=f"{RecordingEpisodeType.Tracking.name_0}")
                self._runData_.episodes.append(episode)
                
            else:
                episode = self._runData_.episodes[-1]
                epIndex = self._runData_.episodes.index(episode)
                
            # self.print(f"current episode ({printStyled(epIndex, 'yellow', True)}): {printStyled(self._runData_.episodes[-1].name, 'yellow', True)} ({printStyled(self._runData_.episodes[-1].type, 'yellow', True)})")
            # self.print(f"\tcurrent episode type decl: {printStyled(self._runData_.currentEpisodeType.name, 'yellow', True)}")
                
            # check that the protocol in the ABF file is the same as the current one
            # else create a new episode automatically
            #
            # upon first run, self._runData_.protocol is None
            if not isinstance(self._runData_.currentProtocol, pab.ABFProtocol):
                # self.print(f"{colorama.Fore.GREEN}{colorama.Style.BRIGHT}initial protocol{colorama.Style.RESET_ALL}: {protocol.name}")
                self._runData_.currentProtocol = protocol
                
            if protocol.name == self._runData_.currentProtocol.name:
                if protocol != self._runData_.currentProtocol:
                    scipywarn(f"Protocol {protocol.name} was changed — CAUTION")
                    self._runData_.currentProtocol = protocol
                    
            self.processProtocol(protocol)
                
            if self._runData_.resultsExported:
                self._runData_.resultsExported = False

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
        # self.print(f"{self.__class__.__name__}.processProtocol ({printStyled(protocol.name)})")
        
        if len(self._runData_.episodes) == 0:
            scipywarn("No episode has been defined")
            return
        
        currentEpisode = self._runData_.episodes[-1]
        
        # NOTE 24-02-17 14:14:17
        # ### BEGIN
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
        #
        # ### END
        
        # self.print(f"{self._runData_.currentAbfTrial.name} processProtocol: {printStyled(protocol.name, 'green', True)}")

        # The channel where DIG outputs are configured; it MAY BE distinct from
        # the DAC channel used by the source for command signals (source.dac) !!!
        #
        activeDAC = protocol.getDAC() # this is the `digdac` in processTrackingProtocol
        # self.print(f"\tactiveDAC: {printStyled(activeDAC.name, 'green', True)} (physical index {printStyled(activeDAC.physical, 'green', True)})")
        
        # The the protocol's DAC channels where digital output is emitted during
        # the recording; the active DAC is one of these by definition
        # WARNING: do NOT confuse with DACs that emulate TTLs
        #
        digOutDacs = protocol.digitalOutputDACs
        # self.print(f"\tDACs with DIG output defined (digOutDacs): {printStyled(tuple((d.name + ' (physical index ' + str(d.physical) + ')' for d in digOutDacs)),'green', True)}")
        
        # NOTE: 2024-05-08 09:57:21
        # ### BEGIN
        # 'mainDIGOut' is the set of digital channel indexes where the principal 
        # ("main") digital pattern is configured; empty set if len(digOutDacs ) == 0
        #
        # See also 'altDIGOut', below.
        #
        # WARNING: in a cross-talk protocol, both sets MIGHT contain the same
        # digital channels indexes — because for cross-talk, two of the pathways 
        # are stimulated in every sweep, but in different order (and/or combination,
        # when there are more than two pathways)
        #
        # Fortunately (?!) Clampex only allows up to two pathways stimulated alternatively
        # 
        # However this be circumvented when using single run per trial protocols
        # (and alternate them via sequencer loops)
        # ### END
        mainDIGOut = protocol.digitalOutputs(alternate=False)
        # self.print(f"\tdigital output channels for principal (main) stimulation pattern ({printStyled('mainDIGOut', 'green', True)}): {printStyled(mainDIGOut, 'green', True)}")
        
        # NOTE: 2024-05-08 09:58:11
        # 'altDIGOut' is the set of digital channel indexes where the "alternative"
        # digital pattern is configured; empty set when alternateDigitalOutputStateEnabled
        # is False or when len(digOutDacs ) == 0
        #
        altDIGOut = protocol.digitalOutputs(alternate=True)
        # self.print(f"\tdigital output channels for alternative pattern ({printStyled('altDIGOut', 'green', True)}): {printStyled(altDIGOut, 'green', True)}")

        # NOTE: 2024-02-19 18:25:43 Allow this below because one may not have DIG usage
        # if len(digOutDacs) == 0:
        #     raise ValueError("The protocol indicates there are no DAC channels with digital output enabled")
        
        # self.print(f"\tcurrent episode: {printStyled(self._runData_.currentEpisode, 'green', True)}, type {printStyled(self._runData_.currentEpisode.type.name, 'green', True)}")
        # self.print(f"\tcurrent episode type decl: {self._runData_.currentEpisodeType.name}")
            
        for src in self._runData_.sources:
            # self.print(f"\tsource (src): {printStyled(src.name, 'green', True)}")
            # self.print(f"   -----------------")
            # self.print(f"   processing source {printStyled(src.name)}")

            # NOTE: 2024-03-09 13:49:12
            # Two pathways can be stimulated alternatively, in one of two ways:
            # ('hard' prerequisites are indicated with '•'; soft preprequisites
            #   re indicated with '∘')
            #
            #   1) use the same monitoring Clampex protocol with two distinct 
            #       DIG channels to stimulate the pathways
            #   • alternateDigitalOutputStateEnabled is True
            #   ∘ alternateDACOutputStateEnabled is irrelevant
            #   • the "main" and the "alternate" DIG output are enabled on different
            #       DACs, which MUST be DACs 0 and 1 (using higher order DACs
            #       is not supported with alternateDigitalOutputStateEnabled and 
            #       messes up the alternance) - we cannot check this in pyabfbridge
            #
            #   2) use the same monitoring Clampex protocol with one DIG output 
            #       for one pathway and a DAC output for the other
            #   • alternateDigitalOutputStateEnabled is True
            #   • alternateDACOutputStateEnabled is True (!)
            #   • the DIG output must be configerd on one of DAC0 or DAC1 (making
            #       sure the digital outputs are enabled in Clampex protocol editor)
            #   • the DAC used to stimulate the other pathway must have index > 1
            #       (and NOT telegraphed, i.e. allowed to emit 5V ) - it goes without
            #       saying that this DAC cannot be used to send clamp commands !
            #   • the DAC used to stimulate the other pathway must have analog waveform enabled
            #
            #   In either case (1 or 2):
            #       • there are exactly two pathways (two dig paths or one dig and one dac paths)
            #       • the protocol generates two sweeps per trial (averaged or not, depending 
            #           on how many runs per trial) with each sweep recording from a
            #           distinct pathway.
            #
            #   3) use interlaved protocols, one for each pathway (this allows 
            #   monitoring more than two pathways, when it makes sense):
            #       • each protocol defines exactly ONE sweep
            #       • each protocol affects exactly one path
            #       • protocols use the same ADC/DAC pair hence the same clampMode
            #       • protocols are applied in succession, i.e.:
            #           path 0 ↦ protocol 0
            #           path 1 ↦ protocol 1
            #           path 2 ↦ protocol 2 etc
            # ----
            #
            
            # NOTE: 2024-05-06 00:31:02
            # Wee ned these in order to figure out details of synaptic pathways
            # (see below);  these are specific to the source
            adc = protocol.getADC(src.adc)
            dac = protocol.getDAC(src.dac)
            
            # NOTE: 2024-05-06 00:31:59
            # Generate the list of pathways according to the specified source
            #
            pathways = [pdict["pathway"] for key, pdict in self._runData_.results[src.name].items() if key not in ("DACPaths", "DIGPaths")]
            
            # self.print(f"declared pathways for source {printStyled(src.name, 'yellow', True)}: {printStyled(pathways)}")
            
            # NOTE: 2024-05-06 00:26:04
            # Now, figure out what these pathways are:
            # • how are they stimulated (i.e. via TTL output through DIG channels
            # or emulated via DAC)
            # • during which sweep are they stimulated (i.e., are they stimulated 
            # alternatively in interleaved sweeps, or not)
            #
            # if len(pathways) == 0:
            #     scipywarn(f"Ignoring source {src.name} which does not declare any pathways")
            #     continue
            
            # NOTE: 2024-02-17 22:36:56 REMEMBER !:
            # By definition, in a tracking protocol, all pathways in the same 
            # recording source have the same clamp mode!
            # 
            clampMode = protocol.getClampMode(adc, activeDAC)
            # self.print(f"\t\tadc: {printStyled(adc.name, 'yellow')}, dac: {printStyled(dac.name, 'yellow')}, clampMode: {printStyled(clampMode.name, 'yellow')}")
            # self.print(f"\t\tsource dac is the protocol's activeDAC: {printStyled(dac == activeDAC, 'yellow', True)}")
            
            # NOTE: 2024-03-09 22:56:22 
            # In a conditioning protocol, the dac is by definition the active DAC.
            # However, in Tracking mode, the dac might be a different one, in 
            # particular when there are two synaptic pathways stimulated alternatively.
            # NOTE: this is NOT because the protocol records via two DACs, but because
            # an alternative patwhay needs a second DAC to configure command waveforms and 
            # digital outputs separately form the 'main' — active — DAC.
            #
            if dac != activeDAC:
                if not protocol.alternateDigitalOutputStateEnabled:
                    scipywarn(f"In protocol {protocol.name} for source {src.name}: when the recording DAC {dac.physicalIndex} is different from the DAC where digital outputs are enabled ({activeDAC.physicalIndex}) alternative digital outputs should be enabled in the protocol; this ABF trial will be skipped.")
                    return
                
            # NOTE: 2024-03-09 13:46:05
            # Detect which pathways are declared by the source as using 
            # • digital outputs (dig_stim_pathways) or 
            # • DAC outputs (dac_stim_pathways)
            # in order to deliver synaptic stimulus
            #
            
            # NOTE: 2024-05-07 15:14:55
            # first, figure out what simulated pathways are defined in the protocol
            # then refine (i.e. keep only the paths ACTUALLY used in the source,
            # see NOTE: 2024-03-09 15:40:48 below)
            #
            
            # Pathways declared by the constructor of LTPOnline
            dac_stim_pathways, dig_stim_pathways = self._runData_.results[src.name]["DACPaths"], self._runData_.results[src.name]["DIGPaths"]
            
            # NOTE: 2024-03-09 15:11:20
            # figure out which of the cases below is met:
            # (see also NOTE: 2024-03-09 13:49:12)
            #
            # case 1:
            #   • source must define two dig_stim_pathways and zero dac_stim_pathways
            #   • protocol has alternate dig outputs enabled
            #   • protocol records two sweeps 
            #   • number of pathways stimulated by the protocol is exactly two
            #
            # case 2:
            #   • source defines one dig_pathway OR one dac_pathway
            #   • protocol records two sweeps
            #   • number of pathways stimulated by the protocol is exactly two
            #
            # case 3:
            #   • source defines any number of pathways
            #   • there are as many protocols as pathways
            #   • each protocol stimulates exactly one pathway
            #   • each protocol generates one sweep, which must NOT be averaged
            #       by the protocol
            #   • protocols must be iterated in the same order
            #   • each protocol is applied once in each iteration
            
            # NOTE: 2024-03-09 15:40:48
            # figure out which of the above pathways (NOTE: 2024-05-07 15:14:55) 
            # are actually used by the protocol
            #
            # start with dac-stimulated pathways first → find out which of the 
            # declared ones are actually used by the protocol
            #
            # from here onwards, dac_stim_pathways are those used in the protocol
            #
            # protocol_dac_stim_pathways = [p for p in dac_stim_pathways if len(protocol.getDAC(p[1].stimulus.channel).emulatesTTL) and protocol.getDAC(p[1].stimulus.channel) not in (dac, activeDAC)]
            protocol_dac_stim_pathways = [p for p in dac_stim_pathways if len(protocol.getDAC(p.stimulus.channel).emulatesTTL) and protocol.getDAC(p[1].stimulus.channel) not in (dac, activeDAC)]
            
            # do the same for dig-stimulated pathways:
            # the filter is simpler: the declares stimulsu channel for the pathway
            # is one of the main or alt DIG channels defined in the protocol
            # from here onward dig_stim_pathways are the pathways actually stimulated by the protocol
            # protocol_dig_stim_pathways = [p for p in dig_stim_pathways if p[1].stimulus.channel in mainDIGOut or altDIGOut]
            protocol_dig_stim_pathways = [p for p in dig_stim_pathways if p.stimulus.channel in mainDIGOut or altDIGOut]
            
            # This is the total number of pathways actually STIMULATED in the
            # protocol, given the sourcer 'src', via either DIG outputs 
            # (dig_stim_pathways) OR DAC-emulated TTLs (dac_stim_pathways)
            #
            nSrcStimPathways = len(protocol_dac_stim_pathways) + len(protocol_dig_stim_pathways)
            # self.print(f"\t\t{printStyled(nSrcStimPathways, 'green', True)} stimulated pathways (nSrcStimPathways)")
            # self.print(f"\t\tsource dig stim pathways: {printStyled(protocol_dig_stim_pathways, 'green', True)}")
            # self.print(f"\t\tsource dac stim pathways: {printStyled(protocol_dac_stim_pathways, 'green', True)}")
            
            # NOTE: 2024-05-07 14:43:35
            # ### BEGIN
            # Below, the concepts of "main" and "alternative" pathways are arbitrary
            # and used internally, here, to facilitate distinguishing between pathways
            # stimulated in an interleaved fashion (i.e., each pathway stimulated
            # during a separate sweep): there is always ONE main pathway, but there
            # can be 0, 1, or more alternative pathways stimulated in the protocol.
            #
            # This is derived from the way in whcih Clampex allows alternative DIG
            # stimulation via DIG channels.
            #
            # Practically, the "main" pathways are those stimulated
            #
            # Inthe typical case where alternative pathways are stimulated using
            # DIG channels, the "main" pathway is the one were the DIG output is
            # defined in the same UI tab as the DAC used to send command waveforms
            # to the cell (if any); the "alternative" DIG output pattern is then
            # defined in the UI tab of the next available DAC channel (although 
            # this does not imply any relationship between that DAC channel and 
            # the "alternative" DIG channel used.)
            #
            # The "main" stimulated pathway is ALWAYS a DIG stimulated one, unless
            # unless only DAC TTL-emulation is used.
            #
            # In a mixed scenario (DIG AND DAC stimulations) the "main" pathway is 
            # the one stimulated via DIG channels.
            #
            
            # list of alternative pathways (each sweep can only stimulate one pathway
            # in a given source; stimulation of additional pathways can only occur
            # in interlaved mode — i.e., each pathway is stimulated during a separate
            # sweep)
            #
            # ### END
            #
            altPathways = list()
            
            if nSrcStimPathways == 0:
                scipywarn(f"Protocol {protcol.name} does not seem to monitor any of the pathways declares in source {src.name}")
                continue
            
            
            if nSrcStimPathways == 1:
                # When there is a single pathway simulated in the protocol, this 
                # is by definition the 'main' pathway.
                #
                mainPathways = protocol_dig_stim_pathways if len(protocol_dig_stim_pathways) else protocol_dac_stim_pathways
                
            elif nSrcStimPathways == 2:
                if len(protocol_dac_stim_pathways) == 0:
                    # both main and alternative stimulated pathways are stimulated
                    # via DIG channels
                    
                    # BUG 2024-05-08 09:54:45 FIXME
                    # in a xtalk protocol, both main and alt DIG out have the same two channels
                    # hence the partitioning below WILL NOT work, i.e. mainPathways will be empty !!!
                    # mainPathways, altPathways = [list(x) for x in more_itertools.partition(lambda x: x[1].stimulus.channel in mainDIGOut, dig_stim_pathways)]
                    #
                    # NOTE: 2024-05-08 10:11:15
                    # we therefore take a different approach: the code below is
                    # rather explicit, yet I'm sure it can be streamlined a bit...
                    # 
                    # DIG channel indexes used with the main but NOT the alternative
                    # pattern; an empty set when mainDIGOut is empty, or when
                    # mainDIGOut == altDIGOut
                    # 
                    mainOnly = mainDIGOut - altDIGOut
                    
                    # self.print(f"\t\tmainOnly: {printStyled(mainOnly, 'green', True)}")
                    
                    # DIG channel indexes used with the alternative but NOT the 
                    # main pattern; empty set when altDIGOut is empty, or when
                    # mainDIGOut == altDIGOut
                    #
                    altOnly = altDIGOut - mainDIGOut
                    # self.print(f"\t\taltOnly: {printStyled(altOnly, 'green', True)}")
                    
                    if len(mainDIGOut) > 0:
                        if len(mainOnly) == 0: # same channels in both mainDIGOut and altDIGOut
                            mainPathways = protocol_dig_stim_pathways
                        else:
                            # mainPathways = list(x for x in protocol_dig_stim_pathways if x[1].stimulus.channel in mainOnly)
                            mainPathways = list(x for x in protocol_dig_stim_pathways if x.stimulus.channel in mainOnly)
                    else:
                        mainPathways = list()
                        
                    if len(altDIGOut) > 0:
                        if len(altOnly) == 0:
                            altPathways = protocol_dig_stim_pathways
                        else:
                            # altPathways = list(x for x in protocol_dig_stim_pathways if x[1].stimulus.channel in altOnly)
                            altPathways = list(x for x in protocol_dig_stim_pathways if x.stimulus.channel in altOnly)
                    else:
                        altPathways = list()
                    
                elif len(protocol_dac_stim_pathways) == 1:
                    # one stim pathway (main) is DIG, the other (alternative) is DAC
                    if not protocol.alternateDACOutputStateEnabled:
                        scipywarn(f"Tracking mode: Alternate DAC outputs are disabled in protocol {protocol.name} yet source {src.name} declares pathway {dac_stim_pathways[0][1].name} to be stimulated with DAC-emulated TTLs")
                        continue
                        
                    mainPathways, altPathways = protocol_dig_stim_pathways, protocol_dac_stim_pathways
                    
                else: # one dac and one dig pathway
                    scipywarn(f"Tracking mode: In protocol {protocol.name}, for source {src.name}: at most one pathway should be declared as simulated via DAC-emulated TTLs")
                    continue
                    
                        
            else: # nSrcStimPathways > 2
                # NOTE: 2024-03-09 22:54:05
                # I think this is technically impossible in Clampex
                scipywarn(f"Tracking mode: Protocol {protocol.name} seems to be stimulating more than two pathways; This is not currently supported")
                continue
            
            
#             self.print(f"\t{printStyled(len(mainPathways), 'cyan', True)} mainPathways:")
#             for p in mainPathways:
#                 self.print(f"\t\t{printStyled(p.name, 'cyan', True)} ({printStyled(p.stimulus.channel, 'cyan', True)}, digital: {printStyled(p.stimulus.dig, 'cyan', True)})")
#                 
#             self.print(f"\t{printStyled(len(altPathways), 'cyan', True)} altPathways:")
#             for p in altPathways:
#                 self.print(f"\t\t{printStyled(p.name, 'cyan', False)} ({printStyled(p.stimulus.channel, 'cyan', False)}, digital: {printStyled(p.stimulus.dig, 'cyan', False)})")
            
            
            # allPathways = mainPathways + altPathways
            # self.print(f"\tall pathways ({printStyled(len(allPathways), 'red')}):")
            # for p in allPathways:
            #     self.print(f"\t\tpath {printStyled(p.name, 'red')} ({printStyled(p.stimulus.channel, 'red')}, digital: {printStyled(p.stimulus.dig, 'red')})")
            
            uniquePathways = unique(mainPathways + altPathways, idcheck=True)
            # self.print(f"\tunique pathways ({printStyled(len(uniquePathways), 'red')}):")
            # for p in uniquePathways:
            #     self.print(f"\t\tpath {printStyled(p.name, 'red')} ({printStyled(p.stimulus.channel, 'red')}, digital: {printStyled(p.stimulus.dig, 'red')})")
            
            for p in uniquePathways:
                if p not in currentEpisode.pathways and isinstance(p, SynapticPathway):
                    currentEpisode.pathways.append(p)
            
            # self.print("\tcurrentEpisode pathways:")
            # for p in currentEpisode.pathways:
            #     self.print(f"\t\tpath {printStyled(p.name, 'red')} ({printStyled(p.stimulus.channel, 'red')})")
            
            # NOTE: 2024-05-06 09:59:39
            # pathStimsBySweep below is a tuple of (sweep index, tuple of 
            # pathway indices in the sequence of unique pathways mainPathways + altPathways);
            # when the second element has more than one pathway index, and these
            # pathway indices are different, it indicates that there is a cross-talk
            # test stimulation of these pathways in that specific sweep
            # pathStimsBySweep = protocol.getPathwaysDigitalStimulationSequence([p[1] for p in unique(mainPathways + altPathways)], 
            #                                                                   indices=False)
            pathStimsBySweep = protocol.getPathwaysDigitalStimulationSequence(uniquePathways, indices=False)
            # self.print("\tpathway stimulation by sweep (pathStimsBySweep):")
            # for sweep_path in pathStimsBySweep:
            #     self.print(f"\tsweep: {printStyled(sweep_path[0], 'red')}:")
            #     for path in sweep_path[1]:
            #         self.print(f"\t\tpath {printStyled(path.name, 'red')} ({printStyled(path.stimulus.channel, 'red')})")
            
            # self.print(f"\t\tpathway stimulation by sweep (pathStimsBySweep): {printStyled(pathStimsBySweep, 'magenta', True)}")

            if len(self._runData_.currentAbfTrial.segments) != len(pathStimsBySweep):
                scipywarn(f"Mismatch between number of sweeps in the trial ({printStyled(len(self._runData_.currentAbfTrial.segments), 'yellow')}) and those in pathways by sweep ({printStyled(len(pathStimsBySweep), 'yellow')})")

            if currentEpisode.type & RecordingEpisodeType.Tracking: 
                # NOTE: 2024-03-09 07:51:17 tracking mode
                if any(len(x[1]) > 1 for x in pathStimsBySweep): # crosstalk?
                    # self.print("\t\tcrosstalk protocol.")
                    if len(currentEpisode.xtalk) == 0 or currentEpisode.xtalk != pathStimsBySweep:
                        # self.print("\t\tsetting new crosstalk episode")
                        if isinstance(self._runData_.prevAbfTrial, neo.Block):
                            currentEpisode.end = self._runData_.prevAbfTrial.rec_datetime
                        else:
                            currentEpisode.end = self._runData_.currentAbfTrial.rec_datetime
                            
                        # NOTE: 2024-05-13 08:41:50
                        # current sweep(s) haven't been added yet
                        # counter is 0-based, and frame selection is semi-open
                        # interval [beginFrame .. endFrame+1)!
                        currentEpisode.endFrame = self._runData_.sweeps - 1 if self._runData_.sweeps > 0 else 0
                        
                        xtalkEpisode = RecordingEpisode(currentEpisode.type,
                                                        name=f"{currentEpisode.type.name}_XTalk", 
                                                        begin = self._runData_.currentAbfTrial.rec_datetime,
                                                        beginFrame = self._runData_.sweeps)
                        xtalkEpisode.xtalk = pathStimsBySweep
                        xtalkEpisode.pathways = uniquePathways
                        self._runData_.episodes.append(xtalkEpisode)
                        currentEpisode = xtalkEpisode
                        self.sig_xtalk.emit(True)
                    
                else: # single path stimulation per sweep
                    # self.print("\t\tnormal tracking protocol")
                    if len(currentEpisode.xtalk) > 0 and self._runData_.pathStimsBySweep != pathStimsBySweep:
                        # self.print("\t\tnew tracking episode")
                        if isinstance(self._runData_.prevAbfTrial, neo.Block):
                            currentEpisode.end = self._runData_.prevAbfTrial.rec_datetime
                        else:
                            currentEpisode.end = self._runData_.currentAbfTrial.rec_datetime
                        
                        # NOTE: 2024-05-13 08:42:17
                        # see NOTE: 2024-05-13 08:41:50
                        currentEpisode.endFrame = self._runData_.sweeps - 1 if self._runData_.sweeps > 0 else 0
                        
                        newEpisode = RecordingEpisode(currentEpisode.type, 
                                                      name=f"{currentEpisode.type.name}",
                                                      begin = self._runData_.currentAbfTrial.rec_datetime,
                                                      beginFrame = self._runData_.sweeps)
                        newEpisode.pathways = uniquePathways
                        
                        self._runData_.episodes.append(newEpisode)
                        
                        currentEpisode = newEpisode
                        self.sig_xtalk.emit(False)
                        
                self._runData_.pathStimsBySweep = pathStimsBySweep
                    
                # TODO 2024-05-12 15:01:56 FIXME
                # refactor the code following distributeSweeps so that sweep 
                # distribution can happen after this top-level if/else clause
                self.distributeSweeps(src, adc)
                
                # NOTE: 2024-05-06 09:16:37
                # Figure out the epochs that define synaptic stimulations
                
                syn_stim_digs = list()
                syn_stim_dacs = list()
                
                # self.print(f"protocol: {printStyled(protocol.name, 'yellow')} {printStyled(len(mainPathways), 'yellow')} mainPathways: {printStyled(mainPathways, 'yellow')}")
                # self.print(f"protocol: {printStyled(protocol.name, 'yellow')} {printStyled(len(altPathways), 'yellow')} altPathways: {printStyled(altPathways, 'yellow')}")
                
                if nSrcStimPathways == 2:
                    if len(mainPathways) == 1:
                        # syn_stim_digs.append(mainPathways[0][1].stimulus.channel)
                        syn_stim_digs.append(mainPathways[0].stimulus.channel)
                        
                        if len(altPathways) == 1:
                            # two alternative digitally stimulated pathways — the most
                            # common case
                            if not protocol.alternateDigitalOutputStateEnabled:
                                scipywarn( f"In protocol {printStyled(protocol.name, 'red', True)}: For two digitally-stimulated pathways the alternative digital output state must be enabled")
                                continue
                            
                            syn_stim_digs.append(altPathways[0].stimulus.channel)
                            # syn_stim_digs.append(altPathways[0][1].stimulus.channel)
                        
                    else: # implies altPathways are the same (albeit in a different order?)
                        if all ((len(x[1]) <= 1 for x in pathStimsBySweep)):
                            scipywarn(f"In protocol {printStyled(protocol.name, 'red', True)}: There must be only one digitally triggered main pathway defined.")
                            continue
                        
                        # syn_stim_digs = list(p[1].stimulus.channel for p in mainPathways)
                        syn_stim_digs = list(p.stimulus.channel for p in mainPathways)
                    
                        
                    # TODO: 2024-03-10 21:28:46
                    # provide for altDacPathways as well
                        
                else: # nSrcStimPathways ≡ 1 ⟹ alternative pathways do not exist here; 
                    if len(mainPathways):
                        syn_stim_digs = list(p.stimulus.channel for p in mainPathways)
                        # syn_stim_digs = list(p[1].stimulus.channel for p in mainPathways)
                        # syn_stim_digs.append(mainPathways[0][1].stimulus.channel)
                            
                # self.print(f"\t\tdigital channels for synaptic stimulation (syn_stim_digs): {printStyled(syn_stim_digs, 'yellow', True)}")
                # self.print(f"\t\tDAC channels for synaptic stimulation via emulated TTLs (syn_stim_dacs): {printStyled(syn_stim_dacs, 'yellow', True)}")
                
                # NOTE: 2024-05-08 14:13:29
                # Figure out the membrane test epochs in order to set up LocationMeasures for
                # the membrane test; we use the source's DAC channel - which may also 
                # be the activeDAC, although this is not necessary.
                #
                # Furthermore, these epochs should exist in eitgher voltage-or current clamp;
                # if they do not, we just do not provide corresponding measurmements
                #
                # The membrane test epochs are COMMON for all the pathways in the source, 
                # because it is the source that gets manipulated (via the DAC)
                # ireespective of how many pathways are measured.
                #
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
                
                # in a multi-pathway protocol, the "main" digital pathways are always
                # delivered on the even-numbered sweeps: 0, 2, etc.
                
                
                # TODO/FIXME 2024-05-11 16:49:12 BUG
                # bring code for sweep selection and addition to pathway results here
                # from setMeasuresForPathway
                
                #
                # for k, p in mainPathways:
                for p in mainPathways:
                    # NOTE: 2024-03-01 13:50:58
                    # k is the pathway index; p is the pathway
                    # self.print(f"   processing main (dig) pathway {printStyled(k)} ({printStyled(p.name)}) with synaptic simulation via DIG {printStyled(p.stimulus.channel)}")
                    p.clampMode = clampMode
                    
                    # if "pathway_responses" not in self._runData_.results[src.name][p.name]:
                    #     self._runData_.results[src.name][p.name]["pathway_responses"] = \
                    #         neo.Block(name=f"{src.name} {p.name}")

                    self.setMeasuresForPathway(src, p, protocol,
                                                adc, dac, activeDAC, membraneTestEpoch,
                                                testStart, testDuration, testAmplitude,
                                                False)
                    
                    if len(self._runData_.episodes[-1].xtalk) == 0:
                        self.measurePathway(src, p, adc, False)

                for p in altPathways:
                    # self.print(f"   processing alt (dig) pathway {printStyled(k)} ({printStyled(p.name)}) with synaptic simulation via DIG {printStyled(p.stimulus.channel)}")
                    p.clampMode = clampMode

                    # if "pathway_responses" not in p.name not in self._runData_.results[src.name][p.name]:
                    #     self._runData_.results[src.name][p.name]["pathway_responses"] = \
                    #         neo.Block(name=f"{src.name} {p.name}")
                    
                    self.setMeasuresForPathway(src, p, protocol, 
                                                        adc, dac, activeDAC, membraneTestEpoch, 
                                                        testStart, testDuration, testAmplitude,
                                                        True)
                    
                    if len(self._runData_.episodes[-1].xtalk) == 0:
                        self.measurePathway(src, p, adc, True)
            
            else: # NOTE: 2024-05-05 14:42:13 conditioning protocol
                self._runData_.pathStimsBySweep = pathStimsBySweep
                if src.name not in self._runData_.conditioningProtocols:
                    self._runData_.conditioningProtocols[src.name] = dict()
                    
                # NOTE: 2024-03-08 22:55:02
                # altDIGOut MUST be empty here
                if len(altDIGOut):
                    scipywarn(f"Alternative digital outputs used in conditioning: {altDIGOut}")

                # NOTE: 2024-03-08 23:03:41
                # Figure out which pathway is being conditioned (test pathway)
                # and which not (control pathway)
                # Udate the viewers.
                for p in pathways:
                    if p.stimulus.dig:
                        # NOTE: 2024-05-12 14:57:26
                        # determine if this is the Test or Control pathway
                        if p.stimulus.channel in mainDIGOut:
                            p.pathwayType = SynapticPathwayType.Test
                            if p.name not in self._runData_.conditioningProtocols[src.name]:
                                self._runData_.conditioningProtocols[src.name][p.name] = list()
                                
                            if protocol.name not in [pr.name for pr in self._runData_.conditioningProtocols[src.name][p.name]]:
                                self._runData_.conditioningProtocols[src.name][p.name].append(protocol)
                                
                            # figure out which measure viewer has been set up; update the viewer title
                            measures = [(l,m) for l, m in self._runData_.results[src.name][p.name]["measures"].items() if l != "MembraneTest"]

                            if len(measures):
                                initResponseLabel = measures[0][0]
                                if isinstance(self._runData_.viewers[src.name][p.name][initResponseLabel], sv.SignalViewer):
                                    self._runData_.viewers[src.name][p.name][initResponseLabel].winTitle += f" {p.pathwayType.name}"
                                    
                        else:
                            p.pathwayType = SynapticPathwayType.Control
                            
                            measures = [(l,m) for l, m in self._runData_.results[src.name][p.name]["measures"].items() if l != "MembraneTest"]

                            if len(measures):
                                initResponseLabel = measures[0][0]
                                if isinstance(self._runData_.viewers[src.name][p.name][initResponseLabel], sv.SignalViewer):
                                    self._runData_.viewers[src.name][p.name][initResponseLabel].winTitle += f" {p.pathwayType.name}"
                                    
                self.distributeSweeps(src, adc)
    
    def distributeSweeps(self, src:RecordingSource, adc:pab.ABFInputConfiguration):
        """Distributes sweeps from the current trial by pathway.
        Each sweep is copied tot he neo.Block containing the synaptic responses 
        for the pathway stimulated in the original sweep in the current ABF trial
        """
        # NOTE: 2024-05-11 18:59:54
        # for xtalk protocol, the same principle applies:
        # fitst stimulated path in the sweep goes to that sweep
        currentEpisode = self._runData_.episodes[-1]
        # self.print("\t{self.__class__.__name__}.distributeSweeps: pathway stimulation by sweep (pathStimsBySweep):")
        # for sweep_path in self._runData_.pathStimsBySweep:
        #     self.print(f"\tsweep: {printStyled(sweep_path[0], 'red')}:")
        #     for path in sweep_path[1]:
        #         self.print(f"\t\tpath {printStyled(path.name, 'red')} ({printStyled(path.stimulus.channel, 'red')})")
            
        if currentEpisode.type & RecordingEpisodeType.Tracking:
            for sweep, paths in self._runData_.pathStimsBySweep:
                path = paths[0]
                assert path == self._runData_.results[src.name][path.name]["pathway"], printStyled("synaptic pathway mismatch between the protocol and pathway stimulation by sweep")
                block = self._runData_.results[src.name][path.name]["pathway_responses"]
                segment = self._runData_.currentAbfTrial.segments[sweep]
                sig = segment.analogsignals[adc.logicalIndex]
                segname = f"{src.name} {path.name}"
                if len(currentEpisode.xtalk):
                    segname += f" \u2192 {paths[1].name} Cross-talk"
                    
                seg = neo.Segment(index = len(block.segments), name=segname)
                
                seg.file_origin = self._runData_.currentAbfTrial.file_origin
                seg.file_datetime= self._runData_.currentAbfTrial.file_datetime
                seg.rec_datetime = self._runData_.currentAbfTrial.rec_datetime
                
                seg.analogsignals.append(sig)
                seg.annotations["ABFTrial"] = self._runData_.currentAbfTrial.name
                seg.annotations["ABFTrialSweep"] = sweep
                
                if len(currentEpisode.xtalk):
                    seg.annotations["Crosstalk"] = [p.stimulus.channel for p in paths]
                    
                block.segments.append(seg)
                
                for cursor in self._runData_.viewers[src.name][path.name]["pathway_viewer"].signalCursors:
                    cursor.show()
                    
                self._runData_.viewers[src.name][path.name]["pathway_viewer"].view(block)
                self._runData_.viewers[src.name][path.name]["pathway_viewer"].currentFrame = len(block.segments)-1
                
            # NOTE: 2024-05-13 08:37:09
            # one sweep added per pathway ⟹ episodes should each have self._runData_.sweeps
            self._runData_.sweeps += 1 
            
        elif currentEpisode.type & RecordingEpisodeType.Conditioning:
            # self.print(f"{self.__class__.__name__}.distributeSweeps for conditioning episode")
            # NOTE: 2024-05-13 08:37:33
            # add ALL conditioning sweeps in the conditioning block to the 
            # test pathway
            for sweep, paths in self._runData_.pathStimsBySweep:
                path = paths[0]
                assert path == self._runData_.results[src.name][path.name]["pathway"], printStyled("synaptic pathway mismatch between the protocol and pathway stimulation by sweep")
                block = self._runData_.results[src.name][path.name]["pathway_responses"]
                trialSegment = self._runData_.currentAbfTrial.segments[sweep]
                segment = neo.Segment(index = len(block.segments) + trialSegment.index)
                segment.name = f"{src.name} Conditioning {path.name} ({path.pathwayType.name})"
                segment.file_origin = self._runData_.currentAbfTrial.file_origin
                segment.file_datetime = self._runData_.currentAbfTrial.file_datetime
                segment.rec_datetime = self._runData_.currentAbfTrial.rec_datetime
                
                sig = trialSegment.analogsignals[adc.logicalIndex]
                segment.analogsignals.append(sig)
                segment.annotations["Conditioning_protocol"] = self._runData_.currentProtocol.name
                block.segments.append(segment)
                
                controlPaths = [p["pathway"] for k, p in self._runData_.results[src.name].items() if k not in ("DACPaths", "DIGPaths") and p["pathway"].pathwayType == SynapticPathwayType.Control]
                
                for cursor in self._runData_.viewers[src.name][path.name]["pathway_viewer"].signalCursors:
                    cursor.hide()
                    
                self._runData_.viewers[src.name][path.name]["pathway_viewer"].view(block)
                self._runData_.viewers[src.name][path.name]["pathway_viewer"].currentFrame = len(block.segments)-1
                
                # NOTE: 2024-05-13 08:39:24
                # also add same number of sweeps, but containing dummy signals, 
                # to the control pathway
                for p in controlPaths:
                    b = self._runData_.results[src.name][p.name]["pathway_responses"]
                    seg = neo.Segment(index = segment.index)
                    seg.name = f"{src.name} Conditioning {p.name} ({p.pathwayType.name})"
                    seg.file_origin = self._runData_.currentAbfTrial.file_origin
                    seg.file_datetime = self._runData_.currentAbfTrial.file_datetime
                    seg.rec_datetime = self._runData_.currentAbfTrial.rec_datetime
                    
                    new_sig = neo.AnalogSignal(np.full_like(sig, fill_value = 0.0), 
                                                unit = sig.units, t_start = sig.t_start,
                                                sampling_rate = sig.sampling_rate,
                                                name = f"{sig.name} (control pathway)")
                
                    seg.analogsignals.append(new_sig)
                    b.segments.append(seg)
                    
                    for cursor in self._runData_.viewers[src.name][p.name]["pathway_viewer"].signalCursors:
                        cursor.hide()
                        
                    self._runData_.viewers[src.name][p.name]["pathway_viewer"].view(b)
                    self._runData_.viewers[src.name][p.name]["pathway_viewer"].currentFrame = len(b.segments)-1
                
            self._runData_.sweeps += len(self._runData_.pathStimsBySweep)
                            
    def measurePathway(self, src: RecordingSource, p: SynapticPathway,
                       adc:pab.ABFInputConfiguration, isAlt:bool=False):
        measureTime = self._runData_.abfTrialDeltaTimesMinutes[-1] # needed below
        measures = self._runData_.results[src.name][p.name]["measures"]
        sweep = self._runData_.results[src.name][p.name]["pathway_responses"].segments[-1].annotations["ABFTrialSweep"]
        currentTrial = self._runData_.currentAbfTrial
        sig = currentTrial.segments[sweep].analogsignals[adc.logicalIndex]
        
        responseMeasures = [(measureLabel, m) for measureLabel, m in measures.items() if measureLabel != "MembraneTest"]
        
        mbTestMeasure = measures.get("MembraneTest", None)
        
        initResponse = None
        initResponseLabel = None
        pathViewer = self._runData_.viewers[src.name][p.name]["pathway_viewer"] 
        
        for kc, (measureLabel, measure) in enumerate(responseMeasures):
            measureFunctor = measure["measure"]
            locations = measure["locations"]
            # NOTE: 2024-05-13 16:53:01
            # measure on cursors, not locations, so that adjustments to cursor
            # positions are reflected in the measurements for the (next) sweep
            for l in locations:
                if pathViewer.signalCursor(l.name) is None:
                    pathViewer.addCursor(SignalCursorTypes.vertical, l, label_position = 0.85)
                    
            locationCursors = [pathViewer.signalCursor(l.name) for l in locations]
            
            args = measure["args"]
            
            # NOTE: 2024-05-13 17:12:19
            # now, use the signal cursors (NOT data cursors) to perform measurement
            locationMeasure = measureFunctor(*locationCursors, name=measure["name"])
            
            measureValues = locationMeasure(sig)
            
            measureVal = np.abs(measureValues[0])
            
            measurement = neo.IrregularlySampledSignal([measureTime], measureVal, 
                                                        units = measureVal.units, time_units = pq.min,
                                                        name = measureLabel)
            
            if measureLabel not in self._runData_.results[src.name][p.name]:
                self._runData_.results[src.name][p.name][measureLabel] = measurement
                
            else:
                values = np.vstack([self._runData_.results[src.name][p.name][measureLabel].magnitude, measurement.magnitude])
                times = np.vstack([self._runData_.results[src.name][p.name][measureLabel].times.magnitude, measurement.times.magnitude])
                self._runData_.results[src.name][p.name][measureLabel] = \
                    neo.IrregularlySampledSignal(times, values, units = measureVal.units, time_units = pq.min,
                                                        name = measureLabel)
                                                        # name = f"{measureLabel} {measureName}")
            if kc == 0:
                initResponse = self._runData_.results[src.name][p.name][measureLabel]
                initResponseLabel = measureLabel
            else:
                # calculate paired-pulse ratio
                ratio = self._runData_.results[src.name][p.name][measureLabel] / initResponse
                ratio.name = f"Paired-pulse ratio {kc+1}ᵗʰ / 1ˢᵗ"
                self._runData_.results[src.name][p.name][f"PPR {kc} 0"] = ratio
                
#         if initResponseLabel not in self._runData_.viewers[src.name][p.name]:
#             self._runData_.viewers[src.name][p.name][initResponseLabel] = \
#                 sv.SignalViewer(parent=self._runData_.parentWindow, scipyenWindow = self._emitter_, 
#                                                     win_title = f"{src.name} {p.name} {initResponseLabel}")
#             
#             self._runData_.viewers[src.name][p.name][initResponseLabel].hideSelectors()
#             self._runData_.viewers[src.name][p.name][initResponseLabel].hideNavigator()
#             self._runData_.viewers[src.name][p.name][initResponseLabel].hideMainToolbar()
#             
#             x = self._runData_.screenGeometry.x()
#             
#             if isAlt:
#                 x += self._runData_.resultWindowSize[0]
#                 # x += int(self._runData_.resultWindowSize[0] * 1.1)
#                 
#             y = self._runData_.screenGeometry.y() + self._runData_.resultWindowSize[1]
#             
#             self._runData_.viewers[src.name][p.name][initResponseLabel].setGeometry(QtCore.QRect(x, y, self._runData_.resultWindowSize[0], self._runData_.resultWindowSize[1]))
            
        self._runData_.viewers[src.name][p.name][initResponseLabel].plot(self._runData_.results[src.name][p.name][initResponseLabel])
                
        if isinstance(mbTestMeasure, dict):
            measureFunctor = mbTestMeasure["measure"]
            locations = mbTestMeasure["locations"]
            args = mbTestMeasure["args"]
            
            # NOTE: 2024-05-13 17:14:02
            # see NOTE: 2024-05-13 16:53:01
            for l in locations:
                if pathViewer.signalCursor(l.name) is None:
                    pathViewer.addCursor(SignalCursorTypes.vertical, l, label_position = 0.85)
                    
            locationCursors = [pathViewer.signalCursor(l.name) for l in locations]
            
            # self.print(f"locationCursors {locationCursors}")
            
            locationMeasure = measureFunctor(*locationCursors, name=mbTestMeasure["name"])
            
            measureValues = locationMeasure(sig, *args)
            # print(f"measurePathway: measureValues = {measureValues}")
            
            if p.clampMode == ClampMode.VoltageClamp:
                _dc, _rs, _rin = measureValues
                # print(f"measurePathway: _dc = {_dc}, _rs = {_rs}, _rin = {_rin}")
                
                DC = neo.IrregularlySampledSignal([measureTime],[_dc], 
                                                    units = _dc.units,
                                                    time_units = pq.min,
                                                    name = "DC")
                
                Rs = neo.IrregularlySampledSignal([measureTime],[_rs], 
                                                    units = _rs.units,
                                                    time_units = pq.min,
                                                    name = "Rs")
                
                Rin = neo.IrregularlySampledSignal([measureTime],[_rin], 
                                                    units = _rin.units,
                                                    time_units = pq.min,
                                                    name = "Rin")
                
                # NOTE: 2024-05-13 17:14:46
                # create new irregular signals as needed (DC, Rs, Rin), or 
                # append to the existing ones
                #
                if "DC" not in self._runData_.results[src.name][p.name]:
                    self._runData_.results[src.name][p.name]["DC"] = DC
                else:
                    values = np.concatenate([self._runData_.results[src.name][p.name]["DC"].magnitude, DC.magnitude])
                    times = np.concatenate([self._runData_.results[src.name][p.name]["DC"].times.magnitude, DC.times.magnitude])
                    self._runData_.results[src.name][p.name]["DC"] = \
                        neo.IrregularlySampledSignal(times,values, 
                                                        units = DC.units,
                                                        time_units = DC.times.units,
                                                        name = "DC")
                
                if "Rs" not in self._runData_.results[src.name][p.name]:
                    self._runData_.results[src.name][p.name]["Rs"] = Rs
                else:
                    values = np.concatenate([self._runData_.results[src.name][p.name]["Rs"].magnitude, Rs.magnitude])
                    times = np.concatenate([self._runData_.results[src.name][p.name]["Rs"].times.magnitude, Rs.times.magnitude])
                    self._runData_.results[src.name][p.name]["Rs"] = \
                        neo.IrregularlySampledSignal(times,values, 
                                                        units = Rs.units,
                                                        time_units = Rs.times.units,
                                                        name = "Rs")
                    
                if "Rin" not in self._runData_.results[src.name][p.name]:
                    self._runData_.results[src.name][p.name]["Rin"] = Rin
                else:
                    values = np.concatenate([self._runData_.results[src.name][p.name]["Rin"].magnitude, Rin.magnitude])
                    times = np.concatenate([self._runData_.results[src.name][p.name]["Rin"].times.magnitude, Rin.times.magnitude])
                    self._runData_.results[src.name][p.name]["Rin"] = \
                        neo.IrregularlySampledSignal(times,values, 
                                                        units = Rin.units,
                                                        time_units = Rin.times.units,
                                                        name = "Rin")
                    
                if not isAlt:    
                    x = self._runData_.screenGeometry.x()
                    y = self._runData_.screenGeometry.y() + int(self._runData_.resultWindowSize[1] * 2.1)
                    
                    # self.print(f"common viewer for source measures: {printStyled(self._runData_.commonViewerForSourceMeasures, 'red', True)}")
                    
                    if self._runData_.commonViewerForSourceMeasures:
#                         if "SourceMeasures" not in self._runData_.viewers[src.name][p.name]:
#                             self._runData_.viewers[src.name][p.name]["SourceMeasures"] = \
#                                 sv.SignalViewer(parent=self._runData_.parentWindow, scipyenWindow = self._emitter_, 
#                                                             win_title = f"{src.name} {p.name} Source measures")
#                         
#                             self._runData_.viewers[src.name][p.name]["SourceMeasures"].hideSelectors()
#                             self._runData_.viewers[src.name][p.name]["SourceMeasures"].hideNavigator()
#                             self._runData_.viewers[src.name][p.name]["SourceMeasures"].hideMainToolbar()
#                             self._runData_.viewers[src.name][p.name]["SourceMeasures"].setGeometry(QtCore.QRect(x, y, self._runData_.resultWindowSize[0], self._runData_.resultWindowSize[1]))
                            
                        signals = [self._runData_.results[src.name][p.name]["Rs"],
                                    self._runData_.results[src.name][p.name]["Rin"],
                                    self._runData_.results[src.name][p.name]["DC"]]
                            
                        self._runData_.viewers[src.name][p.name]["SourceMeasures"].plot(signals)
                            
                            
                    else:
#                         if "DC" not in self._runData_.viewers[src.name][p.name]:
#                             self._runData_.viewers[src.name][p.name]["DC"] = \
#                                 sv.SignalViewer(parent=self._runData_.parentWindow, scipyenWindow = self._emitter_, 
#                                                             win_title = f"{src.name} {p.name} DC")
#                         
#                             self._runData_.viewers[src.name][p.name]["DC"].hideSelectors()
#                             self._runData_.viewers[src.name][p.name]["DC"].hideNavigator()
#                             self._runData_.viewers[src.name][p.name]["DC"].hideMainToolbar()
#                             self._runData_.viewers[src.name][p.name]["DC"].setGeometry(QtCore.QRect(x, y, self._runData_.resultWindowSize[0], self._runData_.resultWindowSize[1]))
                            
                        self._runData_.viewers[src.name][p.name]["DC"].plot(self._runData_.results[src.name][p.name]["DC"])
#                             
#                         if "Rs" not in self._runData_.viewers[src.name][p.name]:
#                             self._runData_.viewers[src.name][p.name]["Rs"] = \
#                                 sv.SignalViewer(parent=self._runData_.parentWindow, scipyenWindow = self._emitter_, 
#                                                             win_title = f"{src.name} {p.name} Rs")
#                             
#                             x += self._runData_.resultWindowSize[0]
#                             self._runData_.viewers[src.name][p.name]["Rs"].hideSelectors()
#                             self._runData_.viewers[src.name][p.name]["Rs"].hideNavigator()
#                             self._runData_.viewers[src.name][p.name]["Rs"].hideMainToolbar()
#                             self._runData_.viewers[src.name][p.name]["Rs"].setGeometry(QtCore.QRect(x, y, self._runData_.resultWindowSize[0], self._runData_.resultWindowSize[1]))
                            
                        self._runData_.viewers[src.name][p.name]["Rs"].plot(self._runData_.results[src.name][p.name]["Rs"])
                        
#                         if "Rin" not in self._runData_.viewers[src.name][p.name]:
#                             self._runData_.viewers[src.name][p.name]["Rin"] = \
#                                 sv.SignalViewer(parent=self._runData_.parentWindow, scipyenWindow = self._emitter_, 
#                                                             win_title = f"{src.name} {p.name} Rin")
#                         
#                             x += self._runData_.resultWindowSize[0]
#                             self._runData_.viewers[src.name][p.name]["Rin"].hideSelectors()
#                             self._runData_.viewers[src.name][p.name]["Rin"].hideNavigator()
#                             self._runData_.viewers[src.name][p.name]["Rin"].hideMainToolbar()
#                             self._runData_.viewers[src.name][p.name]["Rin"].setGeometry(x, y, self._runData_.resultWindowSize[0], self._runData_.resultWindowSize[1])
                            
                        self._runData_.viewers[src.name][p.name]["Rin"].plot(self._runData_.results[src.name][p.name]["Rin"])
                    
            else: # current clamp
                #TODO 2024-02-27 16:18:25
                scipywarn(f"measurePathway {p.name} in trial {currentTrial.name}: Current-clamp measurements not yet implemented")

    def setMeasuresForPathway(self, src: RecordingSource, p: SynapticPathway, 
                        protocol:pab.ABFProtocol,
                        adc, dac, activeDAC, membraneTestEpoch,
                        testStart, testDuration, testAmplitude,
                        isAlt):
        """Sets up measurements for synaptic pathways
        This should happen only once, and requires that subsequent ABF trials
        have the same protocol as the first ABFTrial
        """
        # NOTE: 2024-03-01 23:53:33 TODO / FIXME:
        # instead of returning pMeasures, why not apply measures directly and 
        # populate the results ?!?
        
        clampMode = p.clampMode # determined in processProtocol(…)
        
        # 1) figure out
        # • synaptic stimulation DAC epochs and synaptic stimulus timing(s)
        # • pathway-specific sweeps
        #
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
        
        if len(sweepsEpochsForDig) == 0:
            raise RuntimeError(f"The specified DIG channel {p.stimulus.channel} appears to be disabled in all sweeps")
        
        if len(sweepsEpochsForDig) > 1:
            # TODO: Check for crosstalk
            pass
            # raise RuntimeError(f"The specified DIG channel {p.stimulus.channel} appears to be active in more than one sweep ({k[0] for k in sweepsEpochsForDig})")

        
        # NOTE: 2024-03-03 21:09:09 DO NOT REMOVE - FYI:
        # ### BEGIN alternative way to collect ABF Epochs defining synaptic stimulation
        #
        # either as a train of stimuli
#         
#         
#         synTrainStimEpochs = list(filter(lambda x: len(x.getTrainDigitalOutputChannels("all"))>0, 
#                             activeDAC.epochs))
#         
#         # or as a pulse (i.e., one stimulus per epoch)
#         synPulseStimEpochs = list(filter(lambda x: len(x.getPulseDigitalOutputChannels("all"))>0, 
#                             activeDAC.epochs))
#         
#         # collect the above together
#         synStimEpochs = synTrainStimEpochs + synPulseStimEpochs
#         
#         assert all((e in synStimEpochs) for e in sweepsEpochsForDig[0][1]), f"Epochs inconsistencies for pathway {p.name}"
#         
        # ### END   alternative way to collect ABF Epochs defining synaptic stimulation
        
        
        pathSweeps = [sed[0] for sed in sweepsEpochsForDig]
        
        s = pathSweeps[0]
        
        block = self._runData_.results[src.name][p.name]["pathway_responses"]   # generated in LTPOnline.__init__
        # viewer = self._runData_.viewers[src.name][p.name]["pathway_viewer"]     # generated in LTPOnline.__init__
        currentTrial = self._runData_.currentAbfTrial
        
        sig = currentTrial.segments[s].analogsignals[adc.logicalIndex]
        t0 = sig.t_start
        
        # ### BEGIN setup measures, if needed
        # FIXME 2024-05-08 15:06:34
        # crossTalk setting is wrong and not needed, really
        # crossTalk = False

        # NOTE: set up measures for the first run;
        # since we only measure during tracking protocols, all trials recorded
        # using this protocol use the same locations.
        #
        # The measurements themselves are done using SignalCursor objects in the
        # pathway response viewer windows (which are NOT serializable), with the
        # advantage that they can be adjusted by the user (and thus affecting the
        # measurement in ALL subsequent sweeps, NOT the current one)
        #
        # We store these measures with locations based on Datacursor objects, 
        # which are serializable (i.e. can be saved/pickled), on the implication
        # than ALL cursors in these measures are vertical cursors.
        #
        #
        if "measures" not in self._runData_.results[src.name][p.name]:
            pMeasures = dict()
            measureTime = self._runData_.abfTrialDeltaTimesMinutes[-1] # needed below

            holdingTime = protocol.holdingTime
            digStimEpochs = sweepsEpochsForDig[0][1] # a list with epochs that emit on the SAME digital channel

            if len(digStimEpochs) == 0:
                raise RuntimeError(f"No digital stimulation epochs found in the protocol, for pathway {k} in source {src}")

            # TODO: 2024-03-01 22:40:37 FIXME - sort out the commented below ↴
            # if len(digStimEpochs) > 1:
                # below, this is contentious: what if the user decided to
                # use more than one epoch to emulate a digital TTL train?
                # so better use them all
                # scipywarn(f"For pathway {k} in source {src} there are {len(digStimEpochs)} in the protocol; will use the first one")

            # NOTE: 2024-03-03 21:13:38
            # use first epoch with digital synaptic stimuli to infer which pathway
            # is stimulated in this Trial ⇒ might be a cross-talk Trial
            firstDigStimEpoch = digStimEpochs[0]

            # collection of unique digital channels used for stimulation on THIS pathway
            stimDIG = unique(list(itertools.chain.from_iterable(e.getUsedDigitalOutputChannels("all") for e in digStimEpochs)))

            if len(stimDIG) == 1:
                if stimDIG[0] != p.stimulus.channel:
                    scipywarn(f"Stimulus channel ({p.stimulus.channel}) for pathway {p.name} in source {src.name} is different from the {stimDIG[0]} used in the epochs {[e.letter for e in digStimEpochs]}")
                    # return

                # crossTalk = False
                
            elif len(stimDIG) == 2:
                if p.stimulus.channel not in stimDIG:
                    scipywarn(f"Stimulus channel ({p.stimulus.channel}) for pathway {p.name} in source {src.name} does not appear to be used in the epochs {[e.letter for e in digStimEpochs]}")
            
            # NOTE: 2024-03-01 23:03:01 below, main pattern is on even index sweeps, alternate pattern is on odd index sweeps
            # NOTE: 2024-03-01 23:04:48 also, a TTL train if present occurs in the first epoch in digStimEpochs
            # however, several digStimEpochs might be used if using TTL pulses
            isTTLtrain = firstDigStimEpoch.hasDigitalTrain(p.stimulus.channel, pathSweeps[0] % 2 == 1)
            
            if isTTLtrain:
                # here, NOTE that the epoch starts at the same time on both main and alternate sweep!
                # same holds for the relatiove pulse times within the train
                stimTimes = dac.getEpochRelativePulseTimes(firstDigStimEpoch, 0)
            
            else:
                isTTLpulses = all(e.hasDigitalPulse(p.stimulus.channel, pathSweeps[0] % 2 == 1) for e in digStimEpochs)
                if isTTLpulses:
                    stimTimes = list(itertools.chain.from_iterable([dac.getEpochRelativePulseTimes(e, 0) for e in digStimEpochs]))
                else:
                    # NOTE: 2024-03-01 23:30:21 should never get here
                    raise RuntimeError(f"Synaptic stimulation Epochs {[e.letter for e in digStimEpochs]} appear to not have either TTL train nor pulses")
                
            # 3) generate signal cursors in the signal viewer window, for synaptic response(s)
            # FIXME: 2024-03-02 23:59:49 TODO
            # no need to construct new DataCursor with every run!
            # merge with creation of signal cursors in the viewer window, below at NOTE 2024-03-03 00:00:40
            #
            # NOTE: 2024-03-01 23:34:52 
            # adjust for real sweep times
            if clampMode == ClampMode.VoltageClamp:
                labelPfx = "EPSC"
                
                # • for response baselines use 10 ms BEFORE stimulus with window of 3 ms
                # • for response amplitude use 10 ms AFTER stimulus, with window 3 ms
                # • cursors should be manually adjusted in the pathway responses windows
                #
                dataCursorsResponsesBase = [DataCursor(t0 + holdingTime + t - 0.01 * pq.s, 0.003 * pq.s, name=f"{labelPfx}{kt}Base") for kt, t in enumerate(stimTimes)]
                dataCursorsResponses = [DataCursor(t0 + holdingTime +t + 0.01 * pq.s, 0.003 * pq.s, name=f"{labelPfx}{kt}") for kt, t in enumerate(stimTimes)]
                
                locationMeasureFunctor = ephys.amplitudeMeasure
                measureUnits = sig.units
                
                measureName = "amplitude"
                
            else:
                labelPfx = "EPSP"
                
                # current clamp or no clamp (voltage-follower)
                # depending on useSlopeInIClamp we use baseline-amplitude or
                # chord slope
                
                if self._runData_.useSlopeInIClamp:
                    # we need TWO data cursors here, approximately placed on 10% and 90% of
                    # the (field) EPSP; since we don't know yet where these positions are,
                    # we take 5 ms and 10 ms AFTER the stimulus - they'd have to be
                    # adjusted on the signal viewer window for the pathway;
                    # cusros windows are 2 ms each
                    dataCursorsResponsesBase = [DataCursor(t0 + holdingTime + t + 0.005 * pq.s, 0.002 * pq.s, name=f"{labelPfx}{kt}Base") for kt, t in enumerate(stimTimes)]
                    dataCursorsResponses = [DataCursor(t0 + holdingTime + t + 0.01 * pq.s, 0.002 * pq.s, name=f"{labelPfx}{kt}") for kt, t in enumerate(stimTimes)]
                    
                    locationMeasureFunctor = ephys.chordSlopeMeasure
                    measureUnits = sig.units/sig.times.units # (e.g., mV/ms)
                    measureName = "slope"
                    
                else:
                    # do the same as for voltage clamp above.
                    dataCursorsResponsesBase = [DataCursor(t0 + holdingTime + t - 0.01 * pq.s, 0.003 * pq.s, name=f"{labelPfx}{kt}Base") for kt, t in enumerate(stimTimes)]
                    dataCursorsResponses = [DataCursor(t0 + holdingTime +t + 0.01 * pq.s, 0.003 * pq.s, name=f"{labelPfx}{kt}") for kt, t in enumerate(stimTimes)]
                    
                    locationMeasureFunctor = ephys.amplitudeMeasure
                    measureUnits = sig.units
                    measureName = "amplitude"
                    
            # NOTE 2024-03-03 00:00:40
            # create signal cursors if needed, then measure
            for kc, c in enumerate(dataCursorsResponsesBase):
                measureLabel = f"{labelPfx}{kc}"
                # if viewer.signalCursor(f"{measureLabel}Base") is None:
                #     viewer.addCursor(SignalCursorTypes.vertical, c, label_position=0.85)
                    # viewer.addCursor(SignalCursorTypes.vertical, c, label = f"{measureLabel}Base", label_position=0.85)
                    
                # if viewer.signalCursor(f"{measureLabel}") is None:
                #     viewer.addCursor(SignalCursorTypes.vertical, dataCursorsResponses[kc], label_position=0.85)
                    # viewer.addCursor(SignalCursorTypes.vertical, dataCursorsResponses[kc], label = f"{measureLabel}", label_position=0.85)
                    
                pMeasures[measureLabel] = {"measure": locationMeasureFunctor,
                                           # "locations": (viewer.signalCursor(f"{measureLabel}Base"),
                                           #              viewer.signalCursor(f"{measureLabel}")),
                                           "locations": (c,dataCursorsResponses[kc]),
                                           "args" : [],
                                           # "sweeps": pathSweeps, # redundant ?!?
                                           "name": measureName,
                                           }
                                        
            #  NOTE: 2024-03-02 11:23:55
            # 4) generate signal cursors in the signal viewer window, for 
            # the membrane test (if any)
            #
            #  NOTE: 2024-03-02 11:55:36 membraneTestEpoch and testStart are calculated in processProtocol
            #  because they are the same for both pathways (they are specific to the recording source)
            #
            if isinstance(membraneTestEpoch, pab.ABFEpoch):
                # self.print(f"testStart = {testStart}; testDuration = {testDuration}")
                if testStart + testDuration < dac.getEpochRelativeStartTime(firstDigStimEpoch, 0):
                    # membrane test occurs BEFORE digital simulation epochs,
                    # possibly with intervening epochs (for response baselines)
                    if testStart == 0:
                        signalBaselineStart = 0 * pq.s
                        
                    else:
                        # need to find out these, as the epochs table may start at a higher epoch index
                        initialEpochs = list(filter(lambda x: dac.getEpochRelativeStartTime(x, 0) + x.firstDuration <=  dac.getEpochRelativeStartTime(membraneTestEpoch, 0) \
                                                            and x.firstDuration > 0 and x.deltaDuration == 0, 
                                                        dac.epochs))
                        if len(initialEpochs):
                            # baseline epochs are initial epochs where no analog command is sent out
                            # (e.g. they are not set)
                            baselineEpochs = list(filter(lambda x: x.firstLevel == 0 and x.deltaLevel == 0, initialEpochs))
                            if len(baselineEpochs):
                                signalBaselineStart = dac.getEpochRelativeStartTime(baselineEpochs[0], 0)
                            else:
                                signalBaselineStart = 0*pq.s
                        else:
                            signalBaselineStart = max(testStart - 2 * dac.holdingTime, 0 * pq.s)
                            
                elif testStart > activeDAC.getEpochRelativeStartTime(digStimEpochs[-1], 0) + digStimEpochs[-1].firstDuration:
                    # mb test delivered AFTER the last digital simulation epoch 
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
                        else:
                            signalBaselineStart = 0 * pq.s
                            
                    else:
                        # no epochs before the membrane test (odd, but can be allowed...)
                        signalBaselineStart = max(activeDAC.getEpochRelativeStartTime(digStimEpochs[0], 0) - 2 * dac.holdingTime, 0 * pq.s)
                
                else:
                    raise RuntimeError("Membrane test appears to overlap with synaptic stimulation epochs")
                
                if clampMode == ClampMode.VoltageClamp:
                    # NOTE: 2024-05-13 16:54:41
                    # set up location measure for the first run; on subsequent
                    # runs we rely on signal cursor positions in the path viewer,
                    # possibly adjusted
                    #
                    dataCursorDC  = DataCursor(t0 + holdingTime + testStart - 0.0025 * sig.times.units, 
                                                0.005 * sig.times.units, 
                                                name="DC")
                    
                    dataCursorRs  = DataCursor(t0 + holdingTime + testStart, 
                                                0.005 * sig.times.units, 
                                                name="Rs")
                    
                    dataCursorRin = DataCursor(t0 + holdingTime + testStart + testDuration - 0.01 * sig.times.units, 
                                                0.005*sig.times.units, 
                                                name="Rin")
                    
                    
                    pMeasures["MembraneTest"] = {"measure": ephys.membraneTestVClampMeasure,
                                                 # "locations": (viewer.signalCursor("DC"), viewer.signalCursor("Rs"), viewer.signalCursor("Rin")),
                                                 "locations": (dataCursorDC, dataCursorRs, dataCursorRin),
                                                 "args": (testAmplitude,),
                                                 # "sweeps": pathSweeps,
                                                 "name": "MembraneTest",
                                                }
                elif clampMode == ClampMode.CurrentClamp:
                    #TODO 2024-02-27 16:18:25
                    scipywarn("setMeasuresForPathway: Current-clamp membrane test measurements not yet implemented")
                
            # store pathway measures for measurements
            self._runData_.results[src.name][p.name]["measures"] = pMeasures
            
        # ### END setup measures
        
        self.setupMeasurementViewers()
            
    def setupMeasurementViewers(self):
        pw = self._runData_.parentWindow
        x = self._runData_.screenGeometry.x()
        y = self._runData_.screenGeometry.height() - self._runData_.resultWindowSize[1] * len(self._runData_.results)
            
        for src_name, src_dict in self._runData_.results.items():
            for path_name, path_dict in src_dict.items():
                if path_name not in ("DIGPaths", "DACPaths"): 
                    measures = self._runData_.results[src_name][path_name].get("measures", None)
                    if measures is None:
                        continue
                    responseMeasures = [measureLabel for measureLabel in measures.keys() if measureLabel != "MembraneTest" and "Base" not in measureLabel and measureLabel.endswith("0")]
                    
                    for k, label in enumerate(responseMeasures):
                        if label not in self._runData_.viewers[src_name][path_name]:
                            self._runData_.viewers[src_name][path_name][label] = sv.SignalViewer(parent=pw, scipyenWindow = self._emitter_,
                                                                                                win_title=f"{src_name} {path_name} {label}",
                                                                                                configTag = f"OnlineLTP_{label}_Viewer_{path_name}")
                            self._runData_.viewers[src_name][path_name][label].setGeometry(QtCore.QRect(x + k*self._runData_.resultWindowSize[0], y, self._runData_.resultWindowSize[0], self._runData_.resultWindowSize[1]))
                            self._runData_.viewers[src_name][path_name][label].hideSelectors()
                            self._runData_.viewers[src_name][path_name][label].hideNavigator()
                            self._runData_.viewers[src_name][path_name][label].hideMainToolbar()
                            
                            x += self._runData_.resultWindowSize[0]
                            
                            
                    mbTestMeasure = measures.get("MembraneTest", None)
                    
                    if isinstance(mbTestMeasure, dict) and "locations" in mbTestMeasure and isinstance(mbTestMeasure["locations"], (tuple, list)):
                        if self._runData_.commonViewerForSourceMeasures:
                            if "SourceMeasures" not in self._runData_.viewers[src_name][path_name]:
                                self._runData_.viewers[src_name][path_name]["SourceMeasures"] = sv.SignalViewer(parent=pw, scipyenWindow = self._emitter_,
                                                                                                        win_title=f"{src_name} {path_name} {'Source measures'}")
                                
                                self._runData_.viewers[src_name][path_name]["SourceMeasures"].setGeometry(QtCore.QRect(x, y, self._runData_.resultWindowSize[0], self._runData_.resultWindowSize[1]))
                                self._runData_.viewers[src_name][path_name]["SourceMeasures"].hideSelectors()
                                self._runData_.viewers[src_name][path_name]["SourceMeasures"].hideNavigator()
                                self._runData_.viewers[src_name][path_name]["SourceMeasures"].hideMainToolbar()
                            
                        else:
                            for label in mbTestMeasure["locations"].keys():
                                if label not in self._runData_.viewers[src_name][path_name]:
                                    self._runData_.viewers[src_name][path_name][label] = sv.SignalViewer(parent=pw, scipyenWindow = self._emitter_,
                                                                                                        win_title=f"{src_name} {path_name} {label}")
                                    self._runData_.viewers[src_name][path_name][label].setGeometry(QtCore.QRect(x, y, self._runData_.resultWindowSize[0], self._runData_.resultWindowSize[1]))
                                    self._runData_.viewers[src_name][path_name][label].hideSelectors()
                                    self._runData_.viewers[src_name][path_name][label].hideNavigator()
                                    self._runData_.viewers[src_name][path_name][label].hideMainToolbar()
                                    
                                    x += self._runData_.resultWindowSize[0]
                                
            
            y += self._runData_.resultWindowSize[1]
        
        
        
        
class LTPOnline(QtCore.QObject):
    """On-line analysis for synaptic plasticity experiments
    """
    # TODO: update episodes in the pathway's schedule
    # TODO: decide if:
    # 1) "guestimating" episode type form the first run, OR
    # 2)  expect the user to manually enter data (i.e. tracking vs xtalk vs 
    # conditioning vs tracking again)
    #
    # What this entails (fields of runData):
    # option (1):
    #   • on first trial:
    #       ∘ currentEpisode = None
    #       ∘ episodeType = Tracking (the default — anything else doesn't make sense here)
    #       ∘ pathways unknown — WARNING if first run file is a conditioning one
    #           it will mis-set all the subsequent parameters
    #       ∘ protocol unknown
    #           ⋄ to be inferred from the ABF trial
    #           ⋄ set up pathway measures
    #
    #   • on subsequent trials:
    #       ∘ test against protocol from previous trial
    #       ∘ must find a way to infer whether this is a conditioning trial — difficult
    #
    # option (2)
    #   • start in tracking mode
    #   • use con/coff to signal conditioning
        
    resultsReady = Signal(object, name="resultsReady")
    
    _instance = None # singleton pattern
    
    def __new__(cls, *args,
                 episodeName: str = "baseline",
                 useEmbeddedProtocol:bool=True,
                 useSlopeInIClamp:bool = True,
                 emitterWindow:typing.Optional[QtWidgets.QMainWindow] = None,
                 directory:typing.Optional[typing.Union[str, pathlib.Path]] = None,
                 autoStart:bool=False, # NOTE: change to True when done coding TODO
                 parent=None,
                 simulate = None,
                 timeout = None,
                 out: typing.Optional[io.TextIOBase] = None,
                 locationMeasures: typing.Optional[typing.Sequence[LocationMeasure]] = None,
                 commonViewerForSourceMeasures:bool=True,
                 ):
        # implementation of singleton pattern ?!?
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, episodeName,
                 useEmbeddedProtocol, useSlopeInIClamp, emitterWindow,
                 directory, autoStart, parent, simulate, timeout, out,
                 locationMeasures, commonViewerForSourceMeasures)
            
        return cls._instance

    def __init__(self, *args,
                 episodeName: str = "baseline",
                 useEmbeddedProtocol:bool=True,
                 useSlopeInIClamp:bool = True,
                 emitterWindow:typing.Optional[QtWidgets.QMainWindow] = None,
                 directory:typing.Optional[typing.Union[str, pathlib.Path]] = None,
                 autoStart:bool=False, # NOTE: change to True when done coding TODO
                 parent=None,
                 simulate = None,
                 timeout = None,
                 out: typing.Optional[io.TextIOBase] = None,
                 locationMeasures: typing.Optional[typing.Sequence[LocationMeasure]] = None,
                 commonViewerForSourceMeasures:bool=True,
                 ):
        """
        
        """
        # NOTE: 2024-03-03 10:31:16
        # user-defined location measures are NOT used (for now)
        super().__init__(parent=parent)
        
        self._useEmbeddedProtocol = useEmbeddedProtocol
        self._useSlopeInIClamp=  useSlopeInIClamp
        self._autoStart = autoStart
        self._stdout_ = out
        self._timeout = timeout
        self._commonViewerForSourceMeasures = commonViewerForSourceMeasures
        
        self._running_ = False
        # self._sources_ = None # preallocate
        self._locationMeasures_ = locationMeasures
        
        self._sources_ = self._check_sources_(*args)
        # if len(self._sources_) != 1:
        #     raise RuntimeError(f"Expecting EXACTLY ONE SOURCE; instead, got {len(self._sources_)}")
        
        # NOTE: 2024-03-03 22:10:02 TODO (maybe)
        # curently not used, but reserve for the future...
        self._presynaptic_triggers_ = dict()

        # ### BEGIN set up emitter window and viewers
        #
        # NOTE: 2023-10-07 11:20:22
        # _emitterWindow_ needed here, to set up viewers
        wsp = wf.user_workspace()
        
        if emitterWindow is None:
            self._emitterWindow_ = wsp["mainWindow"]

        else:
            self._emitterWindow_ = emitterWindow
            
        if type(self._emitterWindow_).__name__ != 'ScipyenWindow':
            raise ValueError(f"Expecting an instance of ScipyenWindow; instead, got {type(emitterWindow).__name__}")

        self._screen_ = self._emitterWindow_.desktopScreen
        self._titlebar_height_ = QtWidgets.QApplication.style().pixelMetric(QtWidgets.QStyle.PM_TitleBarHeight)
        self._screenGeometry_ = self._screen_.geometry()
        self._viewerWinWidth  = 750
        self._viewerWinHeight = 450
        self._resultWinWidth  = 400
        self._resultWinHeight = 300

        if directory is None:
            self._watchedDir_ = pathlib.Path(self._emitterWindow_.currentDir).absolute()
            
        elif isinstance(directory, str):
            self._watchedDir_ = pathlib.Path(directory)

        elif isinstance(directory, pathlib.Path):
            self._watchedDir_ = directory
            
        else:
            raise TypeError(f"'directory' expected to be a str, a pathlib.Path, or None; instead, got {type(directory).__name__}")
        
        self._viewers_ = dict()
        
        self._results_ = dict()
        
        self._parentWindow_ = parent if isinstance(parent, QtWidgets.QWidget) else None
        
        # NOTE: 2024-05-10 13:32:25
        # populate pathways straight away
        self._parse_sources_()
        
        self._setup_rundata_()
        
        self._abfTrialBuffer_ = collections.deque()
        
        self._abfProcessorThread_ = _LTPOnlineFileProcessor_(self,
                                                             self._emitterWindow_,
                                                             self._abfTrialBuffer_,
                                                             self._runData_,
                                                             self._stdout_)
        
        # self._simulation_ = None
        
        self._simulatorThread_ = None
        
        self._setup_simulation_params(simulate)
        
        if self._doSimulation_:
            # print(f"Simulator parameters: {self._simulator_params_}")
            self._simulatorThread_ = _LTPFilesSimulator_(self, self._simulator_params_, 
                                                         self._stdout_)
            self._simulatorThread_.simulationDone.connect(self._slot_simulationDone)
            self._abfSupplierThread_ = _LTPOnlineSupplier_(self, self._abfTrialBuffer_,
                                        self._emitterWindow_, self._watchedDir_,
                                        simulator = self._simulatorThread_,
                                        out = self._stdout_)
            
            if not autoStart:
                cdir = self._simulator_params_.get("dir", self._watchedDir_)
                # self.print(f"\nCall start() method of this LTPOnline instance to simulate a Clampex experiment using ABF files in {cdir}.\n")
        
        else:
            self._abfSupplierThread_ = _LTPOnlineSupplier_(self, self._abfTrialBuffer_,
                                        self._emitterWindow_, self._watchedDir_,
                                        out = self._stdout_)
            # if not autoStart:
            #     self.print(f"\nCall start() method of this LTPOnline instance to listen to ABF files generated by Clampex in {self._watchedDir_}.\n")
        
        self._abfSupplierThread_.abfTrialReady.connect(self._abfProcessorThread_.processAbfFile,
                                                     QtCore.Qt.QueuedConnection)
        
        if autoStart:
            self._abfSupplierThread_.start()
            self._abfProcessorThread_.start()
            self._running_ = True

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

        # print(args)
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
        if isinstance(self._stdout_, io.StringIO):
            print(msg, file = self._stdout_)
            
        elif isinstance(self._stdout_, io.TextIOBase):
            print(msg, file = self._stdout_)
        else:
            print(msg)
            
    def showViewers():
        if hasattr(self, "_viewers_"):
            for src in self._sources_:
                source_viewers = self._viewers_.get(src.name, None)
                if isinstance(source_viewers, dict) and len(source_viewers):
                    path_viewers = [v for v in source_viewers.values() if isinstance(v, dict) and len(v)]
                    for path_viewers_dict in path_viewers:
                        for name, viewer in path_viewers_dict.items():
                            if isinstance(viewer, QtWidgets.QMainWindow):
                                viewer.show()
                                
    def closeViewers(self):
        if hasattr(self, "_viewers_"):
            for src in self._sources_:
                source_viewers = self._viewers_.get(src.name, None)
                if isinstance(source_viewers, dict) and len(source_viewers):
                    path_viewers = [v for v in source_viewers.values() if isinstance(v, dict) and len(v)]
                    for path_viewers_dict in path_viewers:
                        for name, viewer in path_viewers_dict.items():
                            if isinstance(viewer, QtWidgets.QMainWindow):
                                viewer.close()
    def hideViewers(self):
        if hasattr(self, "_viewers_"):
            for src in self._sources_:
                source_viewers = self._viewers_.get(src.name, None)
                if isinstance(source_viewers, dict) and len(source_viewers):
                    path_viewers = [v for v in source_viewers.values() if isinstance(v, dict) and len(v)]
                    for path_viewers_dict in path_viewers:
                        for name, viewer in path_viewers_dict.items():
                            if isinstance(viewer, QtWidgets.QMainWindow):
                                viewer.hide()

    @Slot(SignalCursor)
    def slot_signalCursorPositionChanged(self, c:SignalCursor):
        """Updates the X coordinate of the location measure after a SignalCursors was adjusted by the user"""
        emitter = self.sender()
        for src_name, src_dict in self._viewers_.items():
            for path_name, path_dict in src_dict.items():
                if emitter == path_dict["pathway_viewer"]:
                    cmeasure = c.ID
                    baseMeasure = cmeasure.replace("Base", "")
                    if baseMeasure in self._results_[src_name][path_name]["measures"]:
                        locationNdx = 0 if "Base" in cmeasure else 1
                        dc = self._results_[src_name][path_name]["measures"][baseMeasure]["locations"][locationNdx]
                        if isinstance(dc, DataCursor):
                            dc.coord = c.x
                            dc.span = c.xwindow
                    
                    else:
                        mbTestMeasures = self._results_[src_name][path_name]["measures"].get("MembraneTest", dict())
                        if len(mbTestMeasures) and "locations" in mbTestMeasures and all(isinstance(v, DataCursor) for v in mbTestMeasures["locations"]):
                            mbTestLocs = [l.name for l in mbTestMeasures["locations"]]
                            if baseMeasure in mbTestLocs:
                                locationNdx = mbTestLocs.index(baseMeasure)
                                dc = mbTestLocs[locationNdx]
                                if isinstance(dc, DataCursor):
                                    dc.coord = c.x
                                    dc.span = c.xwindow
                    
               
    @Slot()
    def slot_doWork(self):
        self.start()
        
    @Slot()
    def _slot_simulationDone(self):
        self.print(f"\n{self.__class__.__name__}.run: {printStyled('Simulation done!', 'yellow', False)}\n")
        self.stop()
        
    @property
    def directory(self) -> pathlib.Path:
        return self._watchedDir_
    
    @directory.setter
    def directory(self, val:typing.Union[str, pathlib.Path]) -> None:
        if self.running:
            scipywarn("Cannot change directory while this LTPOnline instance is still running")
            return
        
        
        if isinstance(val, str) and len(val.strip()) and os.path.isdir(val):
            val = pathlib.Path(val)
            
        elif not isinstance(val, pathlib.Path):
            scipywarn(f"Expecting a string or a pathlib.Path; instead, got {type(val).__name__}")
            return
            
        val = val.absolute()
        
        if not val.is_dir():
            scipywarn(f"{val} is not a valid directory")
            return
        
        self._watchedDir_ = val
        
        self._abfSupplierThread_.watchedDirectory = self._watchedDir_
            
            
        
    @property
    def running(self) -> bool:
        return self._running_
    
    @property
    def viewers(self) -> dict:
        return self._viewers_
    
    @property
    def results(self) -> dict:
        return self._results_
    
    @property
    def sources(self) -> typing.Sequence:
        return self._sources_
    
    @property
    def runData(self) -> DataBag:
        return self._runData_
    
    @property
    def pathways(self) -> dict:
        return dict((src.name, dict((k, p["pathway"]) for k, p in self._results_[src.name].items())) for src in self._sources_)
    
    def newSource(self, val:RecordingSource) -> None:
        """Replaces currently defined recording source(s) with `val`.
        Does nothing if the instance of LTPOnline is still running
        CAUTION: Will reset the internal state!
        """
        
        if self.running:
            scipywarn("This instance of LTPOnline is still running; cannot alter the recording source.")
            return
        
        if not isinstance(val, RecordingSource):
            raise TypeError(f"Expecting a RecordingSource; instead, got a {type(val).__name__}")
        
        self.reset(force=False)
        
        self._sources_ = self._check_sources_(val)
        
        self._parse_sources_()
        
        self._setup_rundata_()
        
    def newEpisode(self, episodeType:typing.Optional[typing.Union[RecordingEpisodeType, int, str]] = None, 
                   episodeName:typing.Optional[str]=None):
        if isinstance(episodeType, (str, int)):
            episodeType = RecordingEpisodeType.type(episodeType)
        elif episodeType is None:
            episodeType = RecordingEpisodeType.Tracking
        elif not isinstance(episodeType, RecordingEpisodeType):
            scipywarn(f"Expecting a RecordingEpisodeType value, an int or a str")
            return
        ename = episodeName if isinstance(episodeName, str) and len(episodeName.strip()) else episodeType.name
        if len(self._runData_.episodes):
            epNames = [e.name for e in self._runData_.episodes]
            ename = counter_suffix(ename, epNames)
        self._runData_.newEpisodeOnNextRun = (episodeType,  ename)
    
    @property
    def conditioning(self) -> bool:
        """Query the operating state (conditioning mode).
        
        LTPOnline operates in tracking mode (default) or conditioning mode - these
        are mutually exclusive.
        
        In tracking mode the ABF files are interpreted as containing synaptic
        responses recorded before or after conditioning, and are measured. 
        
        In conditioning mode, the ABF files are interpreted as containing
        data recorded during conditioning (i.e. induction of plasticity), and no
        measurements are performed.
        
        The two modes are mutually exclusive: when in tracking mode, conditioning
        mode is False, and vice-versa.
        
        LTPOnline always starts in tracking mode (i.e., conditioning mode is False).
        The conditioning mode can only be switched ON or OFF manually, during an 
        experiment. There can be more than one occasion where conditioning mode
        is ON (in experiments where it makes sense, such as during field recording).
        
        The conditioning mode MUST be switched OFF after plasticity induction, in
        order for the LTPOnline instance to measurements on data from incoming files.
        
        The setter for this property accepts and integer, a string or a boolean:
            an int : 1 ↦ True, anything else ↦ False
            a str: 'on' (case insensitive) ↦ True, anything else ↦ False
            a bool
        
            ... anything else will raise an exception.
        
        NOTE: There is no 'tracking' property, as it is simply the negation of
        this property.
        
        See also the shorthand pseudo-properties c (queries the mode), 'con', 
        and 'coff'. The last two quickly toggle the conditioning mode from the 
        console.
    """
        if len(self._runData_.episodes):
            return self._runData_.episodes[-1].type & RecordingEpisodeType.Conditioning
        return False
    
    @conditioning.setter
    def conditioning(self, val:typing.Union[bool, str, int]):
        # we ONLY support Conditioning and Tracking as episode types
        if (isinstance(val, str) and val.lower() == "on") or (isinstance(val, int) and val==1) \
            or (isinstance(val, bool) and val == True):
            val = RecordingEpisodeType.Conditioning if self._runData_.drug is None else RecordingEpisodeType.Conditioning | RecordingEpisodeType.Drug
            
        else:
            val = RecordingEpisodeType.Tracking if self._runData_.drug is None else RecordingEpisodeType.Tracking | RecordingEpisodeType.Drug
            
        self.print(f"Next episode set to {printStyled(val.name, 'red', True)}")
        
        # set this in order to flag the _LTPOnlineFileProcessor_ that a new 
        # recording episode should be created on the next run
        # we do this to because the user KNOWS that the next run will be 
        # (tracking or conditioning)
        self._runData_.newEpisodeOnNextRun = (val, val.name)
            
    @property
    def con(self):
        """Switch conditioning mode ON"""
        self.conditioning = True
            
    @property
    def coff(self):
        """Switch conditioning mode OFF"""
        self.conditioning = False
        
    @property
    def c(self)->bool:
        """Query conditioning mode"""
        return self.conditioning
    
    @property
    def drug(self):
        return self._runData_.drug
    
    @drug.setter
    def drug(self, val:typing.Optional[str]):
        if isinstance(val, str):
            if len(val.strip()) == 0:
                val = None
                
        elif val is not None:
            scipywarn(f"'drug' expected to be a string or None; instead, got {drug}")
            
        self._runData_.drug = val
        
        if len(self._runData_.episodes):
            if self._runData_.drug is None:
                if self.conditioning:
                    self.newEpisode(RecordingEpisodeType.Conditioning)
                else:
                    self.newEpisode(RecordingEpisodeType.Tracking)
            else:
                if self.conditioning:
                    self.newEpisode(RecordingEpisodeType.Conditioning | RecordingEpisodeType.Drug, drug)
                else:
                    self.newEpisode(RecordingEpisodeType.Tracking | RecordingEpisodeType.Drug, drug)
    
    @property
    def xton(self):
        if len(self._runData_.episodes):
            etype = self._runData_.episodes[-1].type
        else:
            etype = RecordingEpisodeType.Tracking
            
        self._runData_.newEpisodeOnNextRun(etype, eype.name)
        
    @property
    def xtoff(self):
        if len(self._runData_.episodes):
            etype = self._runData_.episodes[-1].type
        else:
            etype = RecordingEpisodeType.Tracking
            
        self._runData_.newEpisodeOnNextRun(etype, eype.name)
        
    
    @property
    def p(self):
        self.pause()
        
    @property
    def r(self):
        self.resume()
        
    @property
    def s(self):
        self.start()
        
    @property
    def h(self):
        """Stops the LTP online app"""
        self.stop()
        
    @property
    def R(self):
        self.reset(force=True)
    
    def setTestPathway(self, srcIndex:int, pathwayIndex:int):
        """Flags the pathway at 'pathwayIndex' in the recording source at 'srcIndex' as a Test pathway.
        The Test pathway is where conditioning is applied.
        
        All other pathways in the source are set to "Control"
        """
        try:
            src = self._sources_[srcIndex]
            if src.name in self._runData_.results:
                src_dict = self._runData_.results[src.name]
                pdicts = [p for p in src_dict.values() if isinstance(p,  dict)]
                paths = sorted([p["pathway"] for p in pdicts if "pathway" in p], key = lambda x: x.name)
                
                for k, p in enumerate(paths):
                    p.pathwayType = SynapticPathwayType.Test if k == pathwayIndex else SynapticPathwayType.Control
                    measures = [(l,m) for l, m in self._runData_.results[src.name][p.name]["measures"].items() if l != "MembraneTest"]
                    if len(measures):
                        initResponseLabel = measures[0][0]
                        if isinstance(self._runData_.viewers[src.name][p.name][initResponseLabel], sv.SignalViewer):
                            self._runData_.viewers[src.name][p.name][initResponseLabel].winTitle += f" {p.pathwayType.name}"
                        
        except:
            traceback.print_exc()
        
    @property
    def hasResults(self) -> bool:
        path_results = itertools.chain.from_iterable([[(p.get("pathway_responses", None), p.get("measures", None), p) for p_name, p in s.items() if p_name not in ("DACPaths", "DIGPaths")]
                                                     for s in self._results_.values()])
        
        ret = any(isinstance(t[0], neo.Block) and len(t[0].segments) for t in path_results)
        
        if ret:
            # TODO: 2024-05-19 12:02:06
            # also check for analysis results
            ret &= all(isinstance(t[1], dict) and all(k in t[2] for k in list(t[1].keys()) if k != "MembraneTest") for t in path_results) # measures
            
        return ret
            
    
    def exportResults(self, normalize:typing.Optional[typing.Union[tuple, range]]=None, normalizeIndexes:bool=True):
        if self.running:
            scipywarn("LTPOnline is still running; call its stop() method first.")
            return
        
        # runTimesMinutes = np.array(self._runData_.abfTrialDeltaTimesMinutes)


        try:
            for src_name, src in self._results_.items():
                for p_name, path in src.items():
                    if p_name in ("DACPaths", "DIGPaths"):
                        continue
                    
                    pathwayType = path["pathway"].pathwayType
                    
                    path_responses = path["pathway_responses"]
                    if isinstance(path_responses, neo.Block):
                        path_responses.annotations["measures"] = dict()
                        path_responses.annotations["measures"].update(self._runData_.results[src_name][p_name]["measures"])
                        path_responses.annotations["PathwayType"] = pathwayType.name
                        
                    wf.assignin(path_responses, f"{src_name}_{p_name}_{pathwayType.name}_synaptic_responses")
                    
                    initialResponse = [(k, v) for k, v in path.items() if k in ("EPSC0", "EPSP0")]
                    if len(initialResponse):
                        runTimesMinutes = initialResponse[0][1].times.flatten()
                        pathway_result = {"RunTime (min)": runTimesMinutes}
                        if isinstance(normalize, tuple) and len(normalize) == 2:
                            if normalizeIndexes:
                                start = int(normalize[0])
                                stop = int(normalize[1])
                                if start < 0 or start >= runTimesMinutes.size:
                                    raise ValueError(f"Invalid start index for normalization {start}")
                                if stop < 0 or stop >= runTimesMinutes.size:
                                    raise ValueError(f"Invalid stop index for normalization {stop}")
                                
                                start, stop = min([start, stop]), max([start, stop])
                                
                                baselineSweeps = range(start, stop)
                                
                            else:
                                start = np.where(runTimesMinutes <= normalize[0])[0]
                                if start.size == 0:
                                    raise ValueError(f"Trial time {normalize[0]} not found")
                                start = int(start[-1])
                                
                                stop = np.where(runTimesMinutes < normalize[1])[0]
                                if stop.size == 0:
                                    raise ValueError(f"Trial time {normalize[1]} not found")
                                stop = int(stop[-1])
                                if stop < (runTimesMinutes.size-1):
                                    stop += 1
                                start, stop = min([start, stop]), max([start, stop])
                                    
                                baselineSweeps = range(start, stop)
                                
                        elif isinstance(normalize, range):
                            if normalize.start < 0 or normaize.start >= runTimesMinutes.size:
                                raise ValueError(f"Invalid start index for normalization {normalize.start}")
                            if normalize.stop < 0 or normaize.stop >= runTimesMinutes.size:
                                raise ValueError(f"Invalid start index for normalization {normalize.stop}")
                            
                            baselineSweeps = normalize
                            
                        else:
                            baselineSweeps = None
                            
                        if isinstance(baselineSweeps, range):
                            baselineAvg = initialResponse[0][1][baselineSweeps.start:baselineSweeps.stop].mean()
                            normalizedResponse = initialResponse[0][1].flatten()/baselineAvg
                            pathway_result[f"{initialResponse[0][0]}_norm"] = normalizedResponse
                    
                    fields = [k for k in path.keys() if k not in ("pathway_responses", "pathway", "measures", "ABFTrialSweep")]
                        
                    pathway_result.update(dict((k, path[k]) for k in fields))
                    dd = dict((k,v.flatten()) for k,v in pathway_result.items())
                    df = pd.DataFrame(dd, columns = list(dd.keys()), index = range(max(len(v) for v in dd.values())))
                    if pathwayType in (SynapticPathwayType.Test, SynapticPathwayType.Control):
                        ptype = f"{pathwayType.name}_"
                    else:
                        ptype = ""
                    wf.assignin(pathway_result, f"{src_name}_{p_name}_{ptype}results_dict")
                    wf.assignin(df, f"{src_name}_{p_name}_{ptype}results")
                
            self._runData_.resultsExported = True
        except:
            traceback.print_exc()
            
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
        # self.print(f"{self.__class__.__name__}.stop() called")
        if self._doSimulation_ and isinstance(self._simulatorThread_, _LTPFilesSimulator_):
            if self._simulatorThread_.isRunning():
                self._simulatorThread_.requestInterruption()
            self._simulatorThread_.quit()
            self._simulatorThread_.wait()
            # self._simulatorThread_.deleteLater()
            
        # NOTE: 2024-02-09 08:14:30
        # this will never occur
        # if isinstance(self._abfSupplierThread_, FileStatChecker):
        #     self._abfSupplierThread_.abfListener.stop()

        if isinstance(self._abfSupplierThread_, _LTPOnlineSupplier_):
            self._abfSupplierThread_.quit()
            self._abfSupplierThread_.wait()
            # self._abfSupplierThread_.deleteLater()
            
        if isinstance(self._abfProcessorThread_, _LTPOnlineFileProcessor_):
            self._abfProcessorThread_.quit()
            self._abfProcessorThread_.wait()
            # self._abfProcessorThread_.deleteLater()
        
        if self._emitterWindow_.isDirectoryMonitored(self._watchedDir_):
            self._emitterWindow_.enableDirectoryMonitor(self._watchedDir_, False)
            
        if len(self._runData_.episodes):
            if isinstance(self._runData_.currentAbfTrial, neo.Block):
                self._runData_.episodes[-1].end = self._runData_.currentAbfTrial.rec_datetime
                self._runData_.episodes[-1].endFrame = self._runData_.sweeps
            
        # self.resultsReady.emit(self._runData_)
        self.resultsReady.emit(self._results_)
        
        self._running_ = False
        
        if self._doSimulation_:
            wf.assignin(self._runData_, "rundata")

        # self.print("\nNow call the exportResults method of the LTPOnline instance")
        
    @property
    def threads(self):
        return (self._abfSupplierThread_, self._abfProcessorThread_, self._simulatorThread_)
            
    def closeViewers(self, clear:bool = False):
        if hasattr(self, "_viewers_"):
            for src in self._sources_:
                source_viewers = self._viewers_.get(src.name, None)
                if isinstance(source_viewers, dict) and len(source_viewers):
                    path_viewers = [v for v in source_viewers.values() if isinstance(v, dict) and len(v)]
                    for path_viewers_dict in path_viewers:
                        for name, viewer in path_viewers_dict.items():
                            if isinstance(viewer, QtWidgets.QMainWindow):
                                if clear:
                                    viewer.clear()
                                viewer.close()
        
    def _parse_sources_(self):
        if len(self._sources_) == 0:
            return
        
        if sys.platform == "win32":
            y = self._screenGeometry_.y() + self._titlebar_height_
        else:
            y = self._screenGeometry_.y()
        
        
        for src in self._sources_:
            pathways = src.pathways
            if len(pathways) == 0:
                scipywarn(f"Ignoring source {src.name} which does not declare any pathways")
                continue
                
            # NOTE: 2024-05-10 14:35:42
            # these two variables are ALWAYS present, as they are defined at 
            # source level (i.e., nothing to do with the actual protocol)
            # dac_stim_pathways, dig_stim_pathways = [list(x) for x in more_itertools.partition(lambda x: x[1].stimulus.dig, enumerate(pathways))]
            dac_stim_pathways, dig_stim_pathways = [list(x) for x in more_itertools.partition(lambda x: x.stimulus.dig, pathways)]
            # self.print(f"source {printStyled(src.name, 'green', True)}")
            # self.print(f"dig_stim_pathways: {printStyled(dig_stim_pathways, 'green', True)}")
            # self.print(f"dac_stim_pathways: {printStyled(dac_stim_pathways, 'green', True)}")
            # bad_dac_paths = [p for p in dac_stim_pathways if p[1].stimulus.channel in (dac.physicalIndex, activeDAC.physicalIndex)]
            bad_dac_paths = [p for p in dac_stim_pathways if p.stimulus.channel in (dac.physicalIndex, activeDAC.physicalIndex)]
        
            if len(bad_dac_paths):
                # scipywarn(f"The pathways {[p[1].name for p in bad_dac_paths]} in source {src.name} are incorrectly declared as using a recording DAC for stimulation; check how LTPOnline was invoked")
                scipywarn(f"The pathways {[p.name for p in bad_dac_paths]} in source {src.name} are incorrectly declared as using a recording DAC for stimulation; check how LTPOnline was invoked")
                continue
            
            self._results_[src.name] = dict()

            for k, p in enumerate(pathways):
                self._results_[src.name][p.name] = {"pathway": p,
                                                    "pathway_responses": neo.Block(name=f"{src.name} {p.name}")}
                
            self._results_[src.name]["DACPaths"] = dac_stim_pathways
            self._results_[src.name]["DIGPaths"] = dig_stim_pathways
            
        self._setup_pathway_viewers()
            
    def _setup_pathway_viewers(self):
        if len(self._sources_) == 0:
            return 
        
        if sys.platform == "win32":
            y = self._screenGeometry_.y() + self._titlebar_height_
        else:
            y = self._screenGeometry_.y()
            
        for src in self._sources_:
            self._viewers_[src.name] = dict()
            pathways = [p["pathway"] for p_name, p in self._results_[src.name].items() if p_name not in ("DACPaths", "DIGPaths")]
            
            for k, p in enumerate(pathways):
                self._results_[src.name][p.name] = {"pathway": p,
                                                    "pathway_responses": neo.Block(name=f"{src.name} {p.name}")}
                
                viewer = sv.SignalViewer(parent=self._parentWindow_, scipyenWindow = self._emitterWindow_,
                                            win_title = f"{src.name} {p.name} Synaptic Responses",
                                            configTag = f"OnlineLTP_Pathway_Viewer_{p.name}")
                viewer.sig_signalCursorPositionChanged[SignalCursor].connect(self.slot_signalCursorPositionChanged)
                viewer.hideSelectors()
                viewer.hideMainToolbar()
                viewer.showNavigator()
                # viewer.show()
                
                viewer.setGeometry(QtCore.QRect(self._screenGeometry_.x() + k * self._viewerWinWidth, y, 
                                                self._viewerWinWidth, self._viewerWinHeight))
                
                self._viewers_[src.name][p.name] = {"pathway_viewer": viewer}
        
            
    def _setup_simulation_params(self, simulate):
        self._doSimulation_ = False
        
        self._simulator_params_ = dict(files=None, timeout=_LTPFilesSimulator_.defaultTimeout, dir=None)
        
        if isinstance(simulate, dict):
            files = simulate.get("files", None)
            timeout = simulate.get("timeout", 2000) # ms
            directory = simulate.get("dir", self._watchedDir_)
            
            if isinstance(files, (tuple,list)) and len(files) > 0 and all(isinstance(v, str) for v in files):
                self._simulator_params_ = dict(files=files, timeout=self._timeout, dir=directory)
                self._doSimulation_ = True
                
            elif isinstance(directory, str) and os.path.isdir(directory):
                self._simulator_params_ = dict(files=files, timeout=timeout, dir=directory)
                self._doSimulation_ = True
                
            elif isinstance(directory, pathlib.Path) and directory.is_dir():
                self._simulator_params_ = dict(files=files, timeout=self._timeout, dir=directory)
                self._doSimulation_ = True
                
        elif isinstance(simulate, bool):
            self._doSimulation_ = simulate
            if isinstance(self._timeout, int):
                self._simulator_params_ = dict(files=None, timeout = int(self._timeout), dir=self._watchedDir_)
                
            
        elif isinstance(simulate, (int, float)):
            self._doSimulation_ = True
            self._timeout = int(simulate)
            self._simulator_params_ = dict(files=None, timeout = self._timeout, dir=self._watchedDir_)
            
    def _setup_rundata_(self):
        self._runData_ = DataBag(sources = self._sources_,
                                 currentAbfTrial = None,
                                 currentProtocol = None,
                                 prevAbfTrial = None,
                                 monitorProtocols = dict(), # maps src.name ↦ {path.name ↦ list of protocols}
                                 conditioningProtocols = dict(),
                                 sweeps = 0, # the number of analysed sweeps
                                 totalSweeps = 0, # the number of recorded sweeps
                                 viewers = self._viewers_,
                                 results = self._results_,
                                 abfTrialTimesMinutes = list(),
                                 abfTrialDeltaTimesMinutes = list(),
                                 useSlopeInIClamp = self._useSlopeInIClamp,
                                 useEmbeddedProtocol = self._useEmbeddedProtocol,
                                 resultsExported = True,
                                 # currentEpisodeType = RecordingEpisodeType.Tracking,
                                 # previousEpisodeType = None,
                                 pathStimsBySweep = tuple(),
                                 episodes = list(),
                                 newEpisodeOnNextRun = (RecordingEpisodeType.Tracking, None), # episode type, episode name
                                 drug = None, # or a suitable mnemonic string
                                 screenGeometry = self._screenGeometry_,
                                 resultWindowSize = (self._resultWinWidth, self._resultWinHeight),
                                 parentWindow = self._parentWindow_,
                                 commonViewerForSourceMeasures = self._commonViewerForSourceMeasures,
                                 )
        
            
    def _reset_state_(self, *args,
              episodeName: str = "baseline",
                 useEmbeddedProtocol:bool=True,
                 useSlopeInIClamp:bool = False,
                 directory:typing.Optional[typing.Union[str, pathlib.Path]] = None,
                 autoStart:bool=False,
                 simulate = None,
                 timeout = None,
                 out: typing.Optional[io.TextIOBase] = None,
                 locationMeasures: typing.Optional[typing.Sequence[LocationMeasure]] = None,
                 ):
        """Resets and optionally, starts the instance of LTPOnline"""
        if self.running:
            scipywarn("LTPOnline instance is still running; call its stop() method first")
            return
        
        self.closeViewers(True)
        
        self._viewers_.clear()
        
        if len(args):
            self._check_sources_(*args)
                
            
        self._results_.clear()
            
        self._runData_.sources = self._sources_
        self._runData_.currentProtocol = None
        self._runData_.sweeps = 0
        self._runData_.currentAbfTrial = None,
        self._runData_.abfTrialTimesMinutes = list()
        self._runData_.abfTrialDeltaTimesMinutes = list()
        self._runData_.useSlopeInIClamp = useSlopeInIClamp
        self._runData_.useEmbeddedProtocol = useEmbeddedProtocol
        self._runData_.monitorProtocols.clear()
        self._runData_.conditioningProtocols.clear()
        self._runData_.currentEpisodeType = RecordingEpisodeType.Tracking
        self._runData_.previousEpisodeType = RecordingEpisodeType.Tracking
        self._runData_.pathStimsBySweep = False
        
        self._stdout_ = out
        self._locationMeasures_ = locationMeasures
        self._abfTrialBuffer_ = collections.deque()
        
        # NOTE: 2024-03-03 22:10:02 TODO (maybe)
        # curently not used, but reserve for the future...
        self._presynaptic_triggers_ = dict()

        # ### BEGIN set up emitter window and viewers
        #
        # NOTE: 2023-10-07 11:20:22
        # _emitterWindow_ needed here, to set up viewers
        wsp = wf.user_workspace()

        newDir = None
        if directory is None:
            newDir = pathlib.Path(self._emitterWindow_.currentDir).absolute()
            
        elif isinstance(directory, str):
            newDir = pathlib.Path(directory)

        elif isinstance(directory, pathlib.Path):
            newDir = directory
            
        else:
            raise TypeError(f"'directory' expected to be a str, a pathlib.Path, or None; instead, got {type(directory).__name__}")
        
        # print(f"{self.__class__.__name__}._reset_state_:\n\tnewDir = {newDir};\n\tprev watched dir = {self._watchedDir_}")
        
        if newDir != self._watchedDir_:
            if self._emitterWindow_.isDirectoryMonitored(self._watchedDir_):
                # print(f"\n\tremoving {self._watchedDir_} from {self._emitterWindow_.__class__.__name__}.dirFileMonitor")
                self._emitterWindow_.enableDirectoryMonitor(self._watchedDir_, False)

        self._watchedDir_ = newDir
        if not self._emitterWindow_.isDirectoryMonitored(self._watchedDir_):
            # print(f"\n\tadding {self._watchedDir_} to {self._emitterWindow_.__class__.__name__}.dirFileMonitor")
            self._emitterWindow_.enableDirectoryMonitor(self._watchedDir_, True)

        if isinstance(self._simulatorThread_, QtCore.QThread):
            self._simulatorThread_.requestInterruption()
            self._simulatorThread_.quit()
            self._simulatorThread_.wait()
            self._simulatorThread_.deleteLater()
        
        self._simulatorThread_ = None
        self._setup_simulation_params(simulate)
        
        # self._doSimulation_ = False
        
        # self._simulator_params_ = dict(files=None, timeout=_LTPFilesSimulator_.defaultTimeout)
        
    def quit(self):
        self.reset(force=True)
        self.__del__()
        
    def reset(self, *args, episodeName: str = "baseline", force:bool=False) -> bool:
        
        if self.hasResults and not self._runData_.resultsExported and not force:
            scipywarn("There are unsaved results; call exportResults() first, or pass 'force=True' to this call")
            return False
        
        try:
            self._reset_state_(*args, episodeName=episodeName, useEmbeddedProtocol=self._useEmbeddedProtocol, 
                            useSlopeInIClamp=self._useSlopeInIClamp, directory=self._watchedDir_, 
                            autoStart=self._autoStart, # NOTE: change to True when done coding TODO
                            simulate=self._simulator_params_, timeout=self._timeout, out=self._stdout_,
                            locationMeasures=self._locationMeasures_)

            self._abfProcessorThread_ = _LTPOnlineFileProcessor_(self,
                                                                self._emitterWindow_,
                                                                self._abfTrialBuffer_,
                                                                self._runData_,
                                                                self._stdout_)
            # self._setup_simulation_params(simulate)

            if self._doSimulation_:
                self._simulatorThread_ = _LTPFilesSimulator_(self, self._simulator_params_, self._stdout_)
                self._simulatorThread_.simulationDone.connect(self._slot_simulationDone)
                self._abfSupplierThread_ = _LTPOnlineSupplier_(self, self._abfTrialBuffer_,
                                            self._emitterWindow_, self._watchedDir_,
                                            simulator = self._simulatorThread_,
                                            out = self._stdout_)
                
                if not self._autoStart:
                    cdir = self._simulator_params_.get("dir", os.getcwd())
                    # self.print(f"\nCall start() method of this LTPOnline instance to simulate a Clampex experiment using ABF files in {cdir}.\n")

            else:
                self._abfSupplierThread_ = _LTPOnlineSupplier_(self, self._abfTrialBuffer_,
                                            self._emitterWindow_, self._watchedDir_,
                                            out = self._stdout_)
                # if not autoStart:
                #     self.print("\nCall start() method of this LTPOnline instance to listen to ABF files generated by Clampex in the current directory.\n")

            self._exported_results_ = True
            self._abfSupplierThread_.abfTrialReady.connect(self._abfProcessorThread_.processAbfFile,
                                                        QtCore.Qt.QueuedConnection)
            if self._autoStart:
                self._abfSupplierThread_.start()
                self._abfProcessorThread_.start()
                self._running_ = True
            
            # self._log_
            
            return True
        except:
            msgBuf = io.StringIO()
            traceback.print_exc(file=msgBuf)
            scipywarn(f"Could not reset\n{msgBuf.getvalue()}")
            return False
            
    def start(self):
        """Starts the instance of LTPOnline.
        To change parameters, first call `reset` with new arguments and, if needed,
        call `start` again.
        """
        if self._running_:
            # self.print("Already started")
            return

        self._abfSupplierThread_.start()
        self._abfProcessorThread_.start()
        
        # if self._doSimulation_:
        #     self.print("Starting simulation\n\n")
        # else:
        #     self.print(f"Monitoring directory {self._watchedDir_}\n\n")
        
        self._running_ = True
        self._runData_.resultsExported = False
        
    def kill(self):
        self.stop()
        # if self._instance.running:
        #     scipywarn(f"An instance of {self.__class__.__name__} is still running; call the stop() method on that instance first")
        #     return
        self._state_()
        self._instance = None
        self.__del__()
            

# class TwoPathwaysOnlineLTP(QtWidgets.QMainWindow, WorkspaceGuiMixin, __UI_LTPWindow__):
# class TwoPathwaysOnlineLTP(WorkspaceGuiMixin, __UI_LTPWindow__):
class TwoPathwaysOnlineLTP(ScipyenViewer, __UI_LTPWindow__):
    
    help_text = ["Usage:",
                 "• Launch Clampex, use the 'File/Set data filenames' menuitem to set the destination to an empty working directory."
                 "• Using Scipyen's 'File System' tab navigate to the (empty) directory where Clampex outputs ABF files (see above)",
                 "• From Scipyen's toolbar/Applications launch 'SynapticPlasticity - online'"
                 "• Enter the relevant metadata in the fields at the top of the window",
                 "• IMPORTANT: Make sure the ADC, DAC and Path0/1 fields point to the same channels as used by Clampex protocols",
                 "  (Path names are arbitrary, but they should be relevant to the experiment)"
                 "",
                 "1. Acquire baseline synaptic responses",
                 "• Press 'Start' button in the Synaptic Plasticity window",
                 "• Start a tracking recording sequence using the Clampex Sequencing toolbar"
                 "• For Cross-talk testing, use Clampex sequencing window to stop acquisition, then start a cross-talk recording sequence using Clampex seuquencing toolbar",
                 " 𝑵𝑶𝑻𝑬: The tracking and cross-talk protocols MUST be defined such that:",
                 "  ∘ they stimulate two pathways alternatively, using DIGITAL output channels (DIG)",
                 "      □ the final trial saves TWO sweeps, one per pathway"
                 "      □ for cross-talk, each sweep has different ORDER in which the two pathways are stimulated"
                 "• You can alternate between tracking and cross-talk in this way, for any number of times.",
                 ""
                 "2. Apply conditoning to a single pathway",
                 "------------------------------",
                 "• Click on 'Conditionnig ON' button in Synaptic Plasticity window",
                 "• In Clampex:",
                 "  ∘ set up a new file name e.g. 'tbp', etc (choose something relevant)",
                 "  ∘ using Clampex sequencing toolbar, start a recording sequences with the conditoning protocol",
                 "• After conditoning, click 'Conditioning OFF' in Synaptic Plasticity window, then",
                 "  in Clampex: ",
                 "  ∘ set up the common nme for chase tracking"
                 "  ∘ start recording a tracking sequence using Clampex sequencing toolbar",
                 "",
                 "At the end of the experiment, press 'Stop' in the Synaptic Plasticity window.",
                 "Examine the results created in Scipyen workspace, export thenm as pickle files,",
                 "  and also export the DataFrame objects as *.csv files"
                 "",
                 "To start a new session, navigate Scipyen to another empty directory; ",
                 "Make sure you also set Clampex to output records in this new empty directory"]
    
    
    def __init__(self, simulate:bool=False, parent=None, **kwargs):
        self._default_ADC_index = 0
        self._default_DAC_index = 0
        self._default_path0_index = 0
        self._default_path1_index = 1
        self._default_path0_name = "Path 0"
        self._default_path1_name = "Path 1"
        
        self._ADC_index = self._default_ADC_index
        self._DAC_index = self._default_DAC_index
        
        self._path0_index = self._default_path0_index
        self._path0_name = self._default_path0_name
        
        self._path1_index = self._default_path1_index
        self._path1_name = self._default_path1_name
        
        self._metadata_ = DataBag()
        
        self._metadata_.name = f"Recording_{yyMdd()}"
        self._metadata_.annotations = {"Source": "AnimalID", "Cell": "Cell", "Field": "",
                                       "Genotype": "", "Sex": "", "Age": ""}
        
        self._metadata_.source = None
        self._metadata_.workdir = os.getcwd()
        
        self._onlineLTP_ = None
        
        self._pathSpinBoxBgDefaultColor = QtGui.QColor()
        self._darkUI = False
        
        self._running_ = False
        
        self._simulation_ = simulate
        
        self._winTitle_ = "Synaptic Plasticity - Two pathways"
        
        if self._simulation_: self._winTitle_ += " (Simulation)"
        
        self._logIO_ = io.StringIO() 
        
        self._oltp = None
        
        # super().__init__(self, parent=parent)
        # self._configureUi_()
        # self._configureUi_() # called by super().__init__
        # WorkspaceGuiMixin.__init__(self, parent=parent)
        super().__init__(data=None, parent=parent, win_title=self._winTitle_, **kwargs)
        # self.scipyenWindow.sig_changedDirectory.connect(self._slot_changedWorkingDirectory)
        # self.loadSettings()
        self._gen_source() # assigns to self._metadata_.source
        
    def _configureUI_(self):
        self.setupUi(self)
        self._pathSpinBoxBgDefaultColor = self.path0SpinBox.palette().color(QtGui.QPalette.Active, QtGui.QPalette.Window)
        
        self._darkUI = self._pathSpinBoxBgDefaultColor.getHsv()[2] < 128
        self._errorColor = colormaps.qcolor(f"{'#aa0000' if self._darkUI else '#ff0000'}")
        self._warningColor = colormaps.qcolor(f"{'#aa5500' if self._darkUI else '#ff5500'}")
        self._conditioningColor = colormaps.qcolor('#aa0000')
        
        self.ADCIndexSpinBox.valueChanged.connect(self._slot_adc_changed)
        self.DACIndexSpinBox.valueChanged.connect(self._slot_dac_changed)
        
        # self.path0SpinBox.setValue(0)
        self.path0SpinBox.valueChanged.connect(self._slot_path_channel_changed)
        # self.path1SpinBox.setValue(1)
        self.path1SpinBox.valueChanged.connect(self._slot_path_channel_changed)
        
        self.path0NameEdit.undoAvailable = True
        self.path0NameEdit.redoAvailable = True
        self.path0NameEdit.editingFinished.connect(self._slot_path_name_changed)
        
        self.path1NameEdit.undoAvailable = True
        self.path1NameEdit.redoAvailable = True
        self.path1NameEdit.editingFinished.connect(self._slot_path_name_changed)
        
        self.metaDataWidget.dataName = self._metadata_.name
        self.metaDataWidget.sourceID = self._metadata_.annotations["Source"]
        self.metaDataWidget.cell = self._metadata_.annotations["Cell"]
        
        self.metaDataWidget.sig_valueChanged.connect(self._slot_metaDataChanged)
        
        self.runningLabel = QtWidgets.QLabel("Idle", parent=self)
        self.statusBar().addPermanentWidget(self.runningLabel)
        
        self.startStopPushButton.clicked.connect(self._slot_startStop)
        
        self.conditioningPushButton.clicked.connect(self._slot_conditioningOnOff)
        
        self.showViewersToolButton.triggered.connect(self._slot_showViewers)
        
        self.defaultTrackingLabelPalette = self.TrackingConditioningLabel.palette()
        self.defaultTrackingLabelBgColor = self.defaultTrackingLabelPalette.color(self.TrackingConditioningLabel.backgroundRole())
        
        # self.exportResultsPushButton.clicked.connect(self._slot_exportResults)
        
        self.setWindowTitle(self._winTitle_)
        
        
    @property
    def ADCindex(self) -> int:
        return self._ADC_index
    
    @markConfigurable("ADCIndex", trait_notifier=True)
    @ADCindex.setter
    def ADCindex(self, val:int):
        if isinstance(val, int) and val >=0 :
            self._ADC_index = val
            signalBlock = QtCore.QSignalBlocker(self.ADCIndexSpinBox)
            self.ADCIndexSpinBox.setValue(self._ADC_index)
            # self.configurable_traits["ADCIndex"] = self._ADC_index
            
    @property
    def DACindex(self) -> int:
        return self._DAC_index
    
    @markConfigurable("DACIndex", trait_notifier=True)
    @DACindex.setter
    def DACindex(self, val:int):
        if isinstance(val, int) and val >=0 :
            self._DAC_index = val
            signalBlock = QtCore.QSignalBlocker(self.DACIndexSpinBox)
            self.DACIndexSpinBox.setValue(self._DAC_index)
            # self.configurable_traits["ADCIndex"] = self._ADC_index
            
    @property
    def path0Index(self) -> int:
        return self._path0_index
    
    @markConfigurable("Path0Index", trait_notifier=True)
    @path0Index.setter
    def path0Index(self, val:int):
        if isinstance(val, int) and val >=0:
            self._path0_index = val
            signalBlock = QtCore.QSignalBlocker(self.path0SpinBox)
            self.path0SpinBox.setValue(self._path0_index)
            p1val = self.path1SpinBox.value()
        
            p = self.path0SpinBox.palette()
            c = p.color(self.path0SpinBox.backgroundRole())
            
            p1 = self.path1SpinBox.palette()
            c1 = p.color(self.path1SpinBox.backgroundRole())
            
            if val == p1val:
                if c != self._errorColor:
                    if c1 != self._errorColor:
                        p1.setColor(self.path1SpinBox.backgroundRole(), self._errorColor)
                        self.path1SpinBox.setPalette(p1)
                    p.setColor(self.path0SpinBox.backgroundRole(), self._errorColor)
                    self.path0SpinBox.setPalette(p)
                    
            else:
                if c != self._pathSpinBoxBgDefaultColor:
                    if c1 != self._pathSpinBoxBgDefaultColor:
                        p1.setColor(self.path1SpinBox.backgroundRole(), self._pathSpinBoxBgDefaultColor)
                        self.path1SpinBox.setPalette(p1)
                    p.setColor(self.path0SpinBox.backgroundRole(), self._pathSpinBoxBgDefaultColor)
                    self.path0SpinBox.setPalette(p)
                    
                    
    @property
    def path1Index(self)->int:
        return self._path1_index
    
    @markConfigurable("Path1Index", trait_notifier=True)
    @path1Index.setter
    def path1Index(self, val:int):
        if isinstance(val, int) and val >=0:
            self._path1_index = val
            signalBlock = QtCore.QSignalBlocker(self.path1SpinBox)
            self.path1SpinBox.setValue(self._path1_index)
            p0val = self.path0SpinBox.value()
            
            p = self.path1SpinBox.palette()
            c = p.color(self.path1SpinBox.backgroundRole())
            
            p1 = self.path0SpinBox.palette()
            c1 = p.color(self.path0SpinBox.backgroundRole())
            
            if val == p0val:
                if c != self._errorColor:
                    if c1 != self._errorColor:
                        p1.setColor(self.path0SpinBox.backgroundRole(), self._errorColor)
                        self.path0SpinBox.setPalette(p1)
                    p.setColor(self.path1SpinBox.backgroundRole(), self._errorColor)
                    self.path1SpinBox.setPalette(p)
                    
            else:
                if c != self._pathSpinBoxBgDefaultColor:
                    if c1 != self._pathSpinBoxBgDefaultColor:
                        p1.setColor(self.path0SpinBox.backgroundRole(), self._pathSpinBoxBgDefaultColor)
                        self.path0SpinBox.setPalette(p1)
                    p.setColor(self.path1SpinBox.backgroundRole(), self._pathSpinBoxBgDefaultColor)
                    self.path1SpinBox.setPalette(p)
                    
                    
            
    @property
    def path0Name(self) -> str:
        return self._path0_name
    
    
    @markConfigurable("Path0Name", trait_notifier=True)
    @path0Name.setter
    def path0Name(self, val:str):
        if isinstance(val, str) and len(val.strip()):
            self._path0_name = val
            signalBlock = QtCore.QSignalBlocker(self.path0NameEdit)
            self.path0NameEdit.setText(self._path0_name)
            
        else:
            scipywarn(f"{self.__class__.__name__}.path0Name.setter expecting a non-empty str; instead got {val}")
        
    @property
    def path1Name(self) -> str:
        return self._path1_name
    
    
    @markConfigurable("Path1Name", trait_notifier=True)
    @path1Name.setter
    def path1Name(self, val:str):
        if isinstance(val ,str) and len(val.strip()):
            self._path1_name = val
            signalBlock = QtCore.QSignalBlocker(self.path1NameEdit)
            self.path1NameEdit.setText(self._path1_name)
        
        else:
            scipywarn(f"{self.__class__.__name__}.path1Name.setter expecting a non-empty str; instead got {val}")
        
        
    @Slot()
    def _slot_startStop(self):
        # print(f"{self.__class__.__name__}._slot_startStop()")
        ww = (self.metaDataWidget,  self.exportResultsPushButton,
              self.ADCIndexSpinBox, self.DACIndexSpinBox,
              self.path0SpinBox,    self.path0NameEdit,
              self.path1SpinBox,    self.path1NameEdit)
        # for w in ww:
        #     w.setEnabled(True)
        
        if isinstance(self._oltp, LTPOnline) and self._oltp.running:
            # print("\tstopping oltp...")
            self._oltp.stop()
            if self._oltp.hasResults and not self._oltp._runData_.resultsExported:
                self._oltp.exportResults()
            for thread in self._oltp.threads:
                if isinstance(thread, QtCore.QThread):
                    thread.quit()
                    thread.wait()
                    thread.deleteLater()
                thread = None
                
            self._oltp = None
            for w in ww:
                w.setEnabled(True)
            self.startStopPushButton.setText("Start")
            self.startStopPushButton.setStatusTip("Start monitoring Clampex output")
            self.startStopPushButton.setToolTip("Start monitoring Clampex output")
            self.startStopPushButton.setWhatsThis("Start monitoring Clampex output")
            self.conditioningPushButton.setEnabled(False)
            self.runningLabel.setText("Idle")
            
        else:
            self._oltp = LTPOnline(self._metadata_.source, directory = self.scipyenWindow.currentDir,
                                emitterWindow = self.scipyenWindow, simulate= self._simulation_,
                                parent=self)
                
            if isinstance(self._oltp._abfProcessorThread_, _LTPOnlineFileProcessor_):
                self._oltp._abfProcessorThread_.sig_xtalk.connect(self._slot_xtalk)
                self._oltp._abfProcessorThread_.sig_processingFile.connect(self._slot_processingFile)
        
            self._oltp.start()
            
            for w in ww:
                w.setEnabled(False)
                
            self.startStopPushButton.setText("Stop")
            self.startStopPushButton.setStatusTip("Stop monitoring Clampex output")
            self.startStopPushButton.setToolTip("Stop monitoring Clampex output")
            self.startStopPushButton.setWhatsThis("Stop monitoring Clampex output")
            self.conditioningPushButton.setEnabled(True)
            
            # print("\tstarting oltp...")
            self.runningLabel.setText("Running")
            
    @Slot(object)
    def _slot_processingFile(self, val:object):
        if isinstance(val, pathlib.Path):
            s = val.name
            
        elif isinstance(val, str) and os.path.isfile(val):
            s = os.path.basename(val)
        else:
            s = val
        self.statusBar().showMessage(f"Processing {s}")
            
    @Slot(str)
    def _slot_changedWorkingDirectory(self, val):
        if isinstance(self._oltp, LTPOnline) and self._oltp.running:
            return
        self.statusBar().showMessage(f"Work directory: {s}")
        # self.currentDirLabel.setText(f"Work directory: {self.scipyenWindow.currentDir}")
        # self._oltp.directory = val
        
    @Slot()
    def _slot_conditioningOnOff(self):
        if self._oltp.running:
            if self._oltp.conditioning:
                self._oltp.coff
                self.conditioningPushButton.setText("Conditioning ON")
                self.conditioningPushButton.setToolTip("Activate conditioning mode for subsequent trials")
                self.conditioningPushButton.setStatusTip("Activate conditioning mode for subsequent trials")
                self.conditioningPushButton.setWhatsThis("Activate conditioning mode for subsequent trials")
                # self.TrackingConditioningLabel.setPalette(self.defaultTrackingLabelPalette)
                self.TrackingConditioningLabel.setText("Tracking")
                color = self.defaultTrackingLabelBgColor
            else:
                self._oltp.con
                self.TrackingConditioningLabel.setText("Conditioning")
                self.conditioningPushButton.setText("Conditioning OFF")
                self.conditioningPushButton.setToolTip("Switch back to tracking mode for subsequent trials")
                self.conditioningPushButton.setStatusTip("Switch back to tracking mode for subsequent trials")
                self.conditioningPushButton.setWhatsThis("Switch back to tracking mode for subsequent trials")
                color = colormaps.qcolor("#aa0000")

            p = self.TrackingConditioningLabel.palette()
            p.setColor(self.TrackingConditioningLabel.backgroundRole(), color)
            self.TrackingConditioningLabel.setPalette(p)
        
    @Slot()
    def _slot_showViewers(self):
        if isinstance(self._oltp, LTPOnline):
            self._oltp.showViewers()
        
    # @Slot()
    # def _slot_exportResults(self):
    #     self._oltp.exportResults()
        
    @Slot()
    def _slot_metaDataChanged(self):
        # print(f"{self.__class__.__name__}._slot_metaDataChanged")
        if isinstance(self._oltp, LTPOnline) and self._oltp.running:
            return
        
        newData = False
        
        if not eq(self._metadata_.name, self.metaDataWidget.dataName):
            self._metadata_.name = self.metaDataWidget.dataName
            newData = True
            
        if not eq(self._metadata_.annotations["Source"], self.metaDataWidget.sourceID):
            # avoid pitfalls of pandas NAType
            self._metadata_.annotations["Source"] = self.metaDataWidget.sourceID
            newData = True
            
        if not eq(self._metadata_.annotations["Cell"], self.metaDataWidget.cell):
            self._metadata_.annotations["Cell"] = self.metaDataWidget.cell
            newData = True
            
        if not eq (self._metadata_.annotations["Field"], self.metaDataWidget.field):
            self._metadata_.annotations["Field"] = self.metaDataWidget.field
            newData = True
            
        if not eq(self._metadata_.annotations["Genotype"], self.metaDataWidget.genotype):
            self._metadata_.annotations["Genotype"] = self.metaDataWidget.genotype
            newData = True
            
        if not eq(self._metadata_.annotations["Sex"], self.metaDataWidget.sex):
            self._metadata_.annotations["Sex"] = self.metaDataWidget.sex
            newData = True
            
        if not eq(self._metadata_.annotations["Age"], self.metaDataWidget.age):
            self._metadata_.annotations["Age"] = self.metaDataWidget.age
            newData = True
            
        if newData:
            self._generate_recording_source()
            
            
    @Slot(int)
    def _slot_adc_changed(self, val:int):
        if val < 0 : 
            val = 0
            
        self.ADCindex = val
            
        self._generate_recording_source()
    
    @Slot(int)
    def _slot_dac_changed(self, val:int):
        if val < 0:
            val = 0
            
        self.DACindex = val

        self._generate_recording_source()
    
    @Slot(int)
    def _slot_path_channel_changed(self, val:int):
        w = self.sender()
        w1 = self.path1SpinBox if w == self.path0SpinBox else self.path0SpinBox
#         
#         old_val = self._path1_index if w == self.path0SpinBox else self._path0_index
        
        if val < 0:
            val = 0
            
#         p = w.palette()
#         p1 = w1.palette()
#         
#         c = p.color(w.backgroundRole())
#         c1 = p1.color(w1.backgroundRole())
        
        if w == self.path0SpinBox:
            self.path0Index = val
            self.path1Index = w1.value()
        else:
            self.path0Index = w1.value()
            self.path1Index = val
            
        # if val == w1.value():
        #     if c != self._errorColor:
        #         if c1 != self._errorColor:
        #             p1.setColor(w1.backgroundRole(), self._errorColor)
        #             w1.setPalette(p1)
        #         p.setColor(w.backgroundRole(), self._errorColor)
        #         w.setPalette(p)
        # else:    
        #     if c != self._pathSpinBoxBgDefaultColor:
        #         if c1 != self._pathSpinBoxBgDefaultColor:
        #             p1.setColor(w1.backgroundRole(), self._pathSpinBoxBgDefaultColor)
        #             w1.setPalette(p1)
        #         p.setColor(w.backgroundRole(), self._pathSpinBoxBgDefaultColor)
        #         w.setPalette(p)
        
        self._generate_recording_source()
                
    @Slot(bool)
    def _slot_xtalk(self, val:bool):
        if val is True:
            self.TrackingConditioningLabel.setText("Tracking (cross-talk)")
            
        else:
            self.TrackingConditioningLabel.setText("Tracking")
                
    @Slot()
    def _slot_path_name_changed(self):
        w = self.sender()
        
        w1 = self.path1NameEdit if w == self.path0NameEdit else self.path0NameEdit
        
        p = w.palette()
        p1 = w1.palette()
        
        c = p.color(w.backgroundRole())
        c1 = p1.color(w1.backgroundRole())
        
        pathName = w.text()
        otherPathName =  w1.text()
        
        if pathName == otherPathName:
            if c != self._warningColor:
                if c1 != self._warningColor:
                    p1.setColor(w1.backgroundRole(), self._warningColor)
                    w1.setPalette(p1)
                p.setColor(w.backgroundRole(), self._warningColor)
                w.setPalette(p)
                
        else:
            if w == self.path0NameEdit:
                self.path0Name = pathName
                self.path1Name = w1.text()
            else:
                self.path0Name = w1.text()
                self.path1Name = pathName
                
            self._generate_recording_source()
            if c != self._pathSpinBoxBgDefaultColor:
                if c1 != self._pathSpinBoxBgDefaultColor:
                    p1.setColor(w1.backgroundRole(), self._pathSpinBoxBgDefaultColor)
                    w1.setPalette(p1)
                p.setColor(w.backgroundRole(), self._pathSpinBoxBgDefaultColor)
                w.setPalette(p)
                
    def closeEvent(self, evt):
        self.saveSettings()
        # print(f"{self.__class__.__name__}.closeEvent(…)")
        if isinstance(self._oltp, LTPOnline):
            if self._oltp.running:
                # print("\tstopping oltp...")
                self._oltp.stop()
                
            if self._oltp.hasResults and not self._oltp._runData_.resultsExported:
                # print("\toltp has results...")
                carryOn = self.questionMessage(self._winTitle_, "There are unsaved results. Continue?") == QtWidgets.QMessageBox.Yes
                if carryOn:
                    # print("\t\forcefully resetting oltp...")
                    self._oltp.reset(force=True)
                else:
                    evt.ignore()
                    return

        super().closeEvent(evt)
        # evt.accept()
                    
    def _generate_recording_source(self) -> RecordingSource:
        if isinstance(getattr(self, "_oltp", None), LTPOnline):
            if self._oltp.running:
                return
        
            if self._oltp.hasResults and not self._oltp.resultsExported:
                carryOn = self.questionMessage(self._winTitle_, "There are unsaved results. Continue?") == QtWidgets.QMessageBox.Yes
                if not carryOn:
                    return
                
        self._gen_source()
                
    def _gen_source(self):
        # adc = self.ADCIndexSpinBox.value()
        # dac = self.DACIndexSpinBox.value()
        # path0 = self.path0SpinBox.value()
        # path1 = self.path1SpinBox.value()
        # path0Name = self.path0NameEdit.text()
        # path1Name = self.path1NameEdit.text()
        adc = self._ADC_index
        dac = self._DAC_index
        path0 = self._path0_index
        path1 = self._path1_index
        path0Name = self._path0_name
        path1Name = self._path1_name
        # srcName = self._metadata_.annotations["Cell"]
        
        # print(self._metadata_.annotations["Cell"])
        # print(self._metadata_.name)
        
        # print(f"adc = {adc}, dac = {dac}, path0 = {path0} ({path0Name}), path1 = {path1} ({path1Name})")
        
        if isinstance(self._metadata_.annotations["Cell"], str) and len(self._metadata_.annotations["Cell"].strip()) > 0:
            srcName = self._metadata_.annotations["Cell"]
        else:
            if isinstance(self._metadata_.name, str) and len(self._metadata_.name.strip()) > 0:
                srcName = self._metadata_.name
            else:
                srcName = None
        
        if path0 == path1:
            scipywarn("Pathways must use distinct DIG channels")
            self.statusBar().showMessage("Pathways must use distinct DIG channels")
            return
            
        if path0Name == path1Name:
            scipywarn("Pathways should have distinct names")
            self.statusBar().showMessage("Pathways should have distinct names")
            return
        
        # print(f"srcName = {srcName}")

        if srcName is None:
            scipywarn("Name or Cell must be non-empty strings")
            self.statusBar().showMessage("Name or Cell must be non-empty strings")
            return
        
        src = twoPathwaysSource(adc, dac, path0, path1, srcName,
                                                   path0name = path0Name,
                                                   path1name = path1Name)
        # print(f"src = {src}")
        self._metadata_.source = src
        
        if isinstance(getattr(self, "_oltp", None), LTPOnline):
            self._oltp.newSource(self._metadata_.source)
        
                
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


def launch():
    try:
        win = mainWindow.newViewer(TwoPathwaysOnlineLTP, parent = mainWindow, win_title="Synaptic Plasticity")
        win.show()
    except:
        traceback.print_exc()
        
def init_scipyen_plugin():
    return {"Applications|SynapticPlasticity - online":launch}
