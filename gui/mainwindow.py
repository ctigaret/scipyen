# -*- coding: utf-8 -*-
"""Main window for the Scipyen application

CHANGELOG:
2020-02-17 12:57:24
    The file loaders in iolib.pictio now return the data and file metadata (where
    possible) as  distinct variables, by default. 
    This is reflected in the MainWindow by populating the workspace with more variables
    than might be expected:
    1) file data (named after the file name)
    2) extra variables, named after the file name with the suffix "_var_n", where 
    "n" is an integral counter (>=1) indicating the order of the variable in the
    tuple returned by the file loader.
    
    In particular:
        opening an axon binary file with iolib.pictio.loadAxonFile creates three
        variables in the workspace: 
            1) the data, named after the file
            2) a dictionary of axon metadata, named after the file with suffix "_var_1" appended
            3) a list of neo.Segments representing the protocol waveforms 
                (as stored inside the file), named after the file with suffix "_var_2" appended
                
    It may seem unelegant, but I have taken this decision to create the posibility
    to inspect the "metadata" stored by 3rd party software as standard.
        

"""
# TODO 2020-07-09 22:34:34 TODO TODO ??? What's that???
# use shell's API for variable management (e.g. shell.find_(...) etc) in relation 
# to mainWindow.history -- place this into workspacemodel module
#
# TODO STUDY:
# IPython/core/interactiveshell.py for InteractiveShell
# ipykernel/zmqshell.py for ZMQInteractiveShell
# ipykernel/inprocess/ipkernel.py for InProcessInteractiveshell
#
# TODO breadcrumbs navigation for the file system model & tree.

# NOTE: 2021-10-21 13:24:24
# all things imported below will be available in the user workspace
#### BEGIN core python modules
import faulthandler, importlib
import sys, os, types, atexit, re, inspect, gc, sip, io, warnings, numbers
import traceback, keyword, inspect, weakref, itertools, typing, functools, operator
import json
from pprint import pprint
from copy import copy, deepcopy
import collections
#from collections import ChainMap
from importlib import reload # I use this all too often !
#### END core python modules

#### BEGIN 3rd party modules
 # NOTE: 2021-08-17 16:52:16
 # get this via scipyen_config module aliased as scipyenconf
#import confuse

#### BEGIN Configurable objects with traitlets.config
# NOTE: 2021-08-23 11:02:10 
# ATTENTION do not import config directly, as it will override IPython's own 
# 'config' object
import traitlets
from traitlets.utils.bunch import Bunch
#### END Configurable objects with traitlets.config

#### BEGIN numerics & data visualization
import numpy as np
import numpy.ma as ma
import pywt # wavelets
import scipy
from scipy import io as sio
from scipy import stats

# for statistics
import statsmodels.api as sm
import statsmodels.formula.api as smf
import statsmodels.stats as sms
import statsmodels.regression as smr 
import patsy as pt
import pandas as pd # for DataFrame and Series
import pingouin as pn # nicer stats
import mpmath as mpm
import researchpy as rp # for use with DataFrames & stats
import joblib as jl # to use functions as pipelines: lightweight pipelining in Python
import sklearn as sk # machine learning, also nice plot_* functionality
import seaborn as sb # statistical data visualization

#print("mainwindow.py __name__ =", __name__)

#### BEGIN migration to pyqtgraph -- setup global parameters
# NOTE: 2019-01-24 21:40:45
import pyqtgraph as pg # used throughout - based on Qt5 
pg.Qt.lib = "PyQt5" # pre-empt the use of PyQt5
# TODO make this peristent  user-modifiable configuration
pg.setConfigOptions(background="w", foreground="k", editorCommand="kwrite")
#pg.setConfigOptions(editorCommand="kwrite")
#### END migration to pyqtgraph -- setup global parameters


#### BEGIN matplotlib modules
import matplotlib as mpl
mpl.use("Qt5Agg")
import matplotlib.pyplot as plt
# NOTE: 2021-08-17 12:17:08
# this is NOT recommended anymore
#import matplotlib.pylab as plb
import matplotlib.mlab as mlb

#### BEGIN configure matplotlib

#matplotlib.use("QtAgg")
# NOTE: 2019-07-29 18:25:30
# this does NOT seem to affect matplotlibrc therefore
# we use a customized matplotlibrc file in pict's directory
# to use Qt5Agg as backend and use SVG as default save format for figures
# NOTE: 2019-08-07 16:34:23 that doesn't seem to work either, hence we 
# call the matplotlib magic in console, at init, see NOTE: 2019-08-07 16:34:58
#mpl.rcParams['backend']='Qt5Agg'
# turn pyplot interactive ON
mpl.rcParams["savefig.format"] = "svg"
mpl.rcParams["xtick.direction"] = "in"
mpl.rcParams["ytick.direction"] = "in"
# NOTE: 2017-08-24 22:48:45 
plt.ion()

#### END configure matplotlib

#### END matplotlib modules
import quantities as pq
import xarray as xa

import h5py
import vigra
import neo
#### END numerics & data visualization

#### BEGIN jupyter
from jupyter_core.paths import jupyter_runtime_dir
#### END jupyter

#### BEGIN PyQt5 modules
from PyQt5 import (QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml, QtSvg,)
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty,)
from PyQt5.uic import loadUiType
#### END PyQt5 modules

#from IPython.lib.deepreload import reload as dreload

from IPython.core.history import HistoryAccessor
#from IPython.core.autocall import ZMQExitAutocall

from IPython.display import set_matplotlib_formats

from jupyter_client.session import Message

#### END 3rd party modules

#### BEGIN 2022-02-21 15:43:38 check if NEURON python is installed
neuron_spec = importlib.util.find_spec("neuron")
has_neuron = neuron_spec is not None
#### END

#### BEGIN scipyen core modules
#import core.prog as prog
import core.quantities as cq
from core.prog import (timefunc, timeblock, processtimefunc, processtimeblock,
                       Timer, safeWrapper, warn_with_traceback, get_properties)

from core.scipyenmagics import ScipyenMagics
# NOTE: 2017-04-16 09:48:15 
# these are also imported into the console in slot_initQtConsole(), so they are
# available directly in the console
from core.workspacefunctions import * 
from core import scipyen_config as scipyenconf
from core.scipyen_config import (markConfigurable, confuse, 
                                 saveWindowSettings, loadWindowSettings, )
from core.scipyen_config import scipyen_config as scipyen_settings
from core import plots as plots
from core import datatypes as dt
from core import neoutils
# also imports datetime & time; all become directly available in console, see 
# NOTE: 2017-04-16 09:48:15 above 
from core.datatypes import * 

import core.desktoputils as desktoputils
import core.xmlutils as xmlutils
import core.tiwt as tiwt
import core.signalprocessing as sigp
import core.curvefitting as crvf
import core.strutils as strutils
#import core.simulations as sim
import core.data_analysis as anl

from core.utilities import (summarize_object_properties,
                            standard_obj_summary_headers,
                            safe_identity_test, unique, index_of, gethash,
                            NestedFinder, normalized_index)

from core.prog import (safeWrapper, deprecation, iter_attribute,
                       filter_type, filterfalse_type, 
                       filter_attribute, filterfalse_attribute)

from core import prog

# NOTE: 2020-09-28 11:37:25
# ### BEGIN expose important data types
# The following data types, introduced by Scipyen, are important and therefore 
# should be available in the Scipyen Console namespace. We expose them by 
# importing here.
# Other important data types come from 3rd party packages and they can be accessed
# from their parent modules: 
# numpy (aliased as np; core module for numeric data processing)
# scipy (for signal processing etc on numpy data types),
# quantities (aliased as pq; for dimensional units),
# vigra (for VigraArray, AxisTags, AxisInfo), 
# vigra.filters (Kernel1D, Kernel2D),
# neo (for Block, Segment, AnalogSignal, etc), 
# pandas (aliased as pd; for DataFrame and Series), 
# seaborn (aliased as sb; for fancy plotting routines),
# pyqtgraph (aliased as pg; for efficient Qt-based plotting),
# matplotlib (aliased as mpl; for versatile plotting)
from core.traitcontainers import DataBag
from core.triggerprotocols import TriggerProtocol
from core.triggerevent import (DataMark, TriggerEvent, TriggerEventType, )

from core.datasignal import (DataSignal, IrregularlySampledDataSignal,)
from core.datazone import DataZone

# ### END expose important data types
#### END scipyen core modules

#### BEGIN scipyen iolib modules
#import iolib.pictio as pio
from iolib import pictio as pio
from iolib import h5io, jsonio
#import iolib.pictio as pio
#### END scipyen iolib modules

#### BEGIN scipyen gui modules
from . import dictviewer as dv
from . import imageviewer as iv
from . import matrixviewer as matview
from . import signalviewer as sv
from . import tableeditor as te
from . import textviewer as tv
from . import xmlviewer as xv
from . import pictgui as pgui
from . import resources_rc as resources_rc
from . import quickdialog as qd
from . import scipyenviewer
from . import consoles
from . import gui_viewers
from . import scipyen_colormaps as colormaps
from . import colorwidgets
from . import stylewidgets
from . import gradientwidgets

from .triggerdetectgui import guiDetectTriggers

from .workspacegui import (WorkspaceGuiMixin)
from .workspacemodel import WorkspaceModel

# qtconsole.styles and pygments.styles, respectively:
from gui.consoles import styles, pstyles 
#### END scipyen gui modules


#### BEGIN scipyen ephys modules
from ephys import (ephys, ltp, membrane, ivramp,)
#from ephys import *
#import ephys.ltp as ltp
#### END scipyen ephys modules

#### BEGIN scipyen systems modules
from systems import *
#### END scipyen systems modules

#### BEGIN scipyen imaging modules
from imaging import (imageprocessing as imgp, imgsim,)
from imaging import axisutils, vigrautils
from imaging.axisutils import (axisTypeFromString, 
                                axisTypeName,
                                axisTypeStrings,
                                axisTypeSymbol, 
                                axisTypeUnits,
                                dimEnum,
                                dimIter,
                                evalAxisTypeExpression,
                                getAxisTypeFlagsInt,
                                getNonChannelDimensions,
                                hasChannelAxis,
                                )
from imaging.axiscalibration import (AxesCalibration,
                                        AxisCalibrationData, 
                                        ChannelCalibrationData, 
                                        CalibrationData)

from imaging.scandata import (AnalysisUnit, ScanData,)

import imaging.CaTanalysis as CaTanalysis 
if CaTanalysis.LSCaTWindow not in gui_viewers:
    gui_viewers += [CaTanalysis.LSCaTWindow]
#if has_vigra:
    #from imaging import (imageprocessing as imgp, imgsim,)
    #from imaging import axisutils, vigrautils
    #from imaging.axisutils import (axisTypeFromString, 
                                   #axisTypeName,
                                   #axisTypeStrings,
                                   #axisTypeSymbol, 
                                   #axisTypeUnits,
                                   #dimEnum,
                                   #dimIter,
                                   #evalAxisTypeExpression,
                                   #getAxisTypeFlagsInt,
                                   #getNonChannelDimensions,
                                   #hasChannelAxis,
                                   #)
    #from imaging.axiscalibration import (AxesCalibration,
                                         #AxisCalibrationData, 
                                         #ChannelCalibrationData, 
                                         #CalibrationData)
    
    #from imaging.scandata import (AnalysisUnit, ScanData,)

    #import imaging.CaTanalysis as CaTanalysis 
    #if CaTanalysis.LSCaTWindow not in gui_viewers:
        #gui_viewers += [CaTanalysis.LSCaTWindow]
#### END scipyen imaging modules

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

_valid_varname__regex_ = '^[A-Za-z_][A-Za-z0-9_]{1,30}$'

_imported_modules__ = u'\n\nFor convenience, the following modules are imported (custom names indicated where appropriate):' +\
                    u'\n\nnumpy --> np\nmatplotlib --> mpl\nmatplotlib.pyplot --> plt\nmatplotlib.pylab --> plb\nmatplotlib.mlab --> mlb\n' +\
                    u'PyQt5.QtCore\nPyQt5.QtGui\ntypes\nsys\nos\n' +\
                    u'IPython.utils.ipstruct --> Struct'+\
                    u'\n\nAnd from the Pict package:\npictio --> pio\nsignalviewer --> sv\ndatatypes \nxmlutils' +\
                    u'\n\nTherefore ipython line magics such as %pylab or %mtplotlib, although still available, are not necessary anymore\n'



_info_banner_ = ["\n*** NOTE: ***"]
_info_banner_.append("User variables created in the console will become visible in the User variables tab in the main window.\n")
_info_banner_.append("The Pict main window GUI object is accessible from the console as `mainWindow` or `mainWindow` (an alias of mainWindow).\n")
_info_banner_.append("Except for user variables, if any of `mainWindow`, `mainWindow`, or loaded modules are deleted from the console workspace by calling del(...), they can be restored using the `Console/Restore Namespace` menu item.\n")
_info_banner_.append("The Workspace dock widget of the Pict main window shows variables shared between the console (the IPython kernel) and the Pict window, including modules imported manually at the console.\n")
_info_banner_.append("Several useful python modules are available in console as the following aliases:\n")
_info_banner_.append("Module: -> alias, where mentioned:")
_info_banner_.append("=================================")
_info_banner_.append("numpy -> np")
_info_banner_.append("matplotlib -> mpl")
_info_banner_.append("matplotlib.pyploy -> plt")
_info_banner_.append("matplotlib.pylab -> plb")
_info_banner_.append("matplotlib.matlab -> mlb")
_info_banner_.append("scipy")
_info_banner_.append("vigra")
_info_banner_.append("quantities -> pq")
_info_banner_.append("\n")
_info_banner_.append("The following modules are from PyQt5")
_info_banner_.append("============================================")
_info_banner_.append("QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml")
_info_banner_.append("\n")
_info_banner_.append("The following modules belong to pict package")
_info_banner_.append("============================================")
_info_banner_.append("signalviewer -> sv (*)   GUI for 1D signals + cursors")
_info_banner_.append("imageviewer -> iv (*)    GUI for images (VigraArray)")
_info_banner_.append("textviewer -> tv (*)     GUI for text data types")
_info_banner_.append("tableeditor --> te (*)   GUI for matrix data viewer")
_info_banner_.append("matrixviewer             GUI for matrix data viewer")
_info_banner_.append("pictgui -> pgui (*)      ancillary GUI stuff")
_info_banner_.append("pictio -> pio (*)        i/o functions")
_info_banner_.append("datatypes                new python quantities and data types")
_info_banner_.append("xmlutils                 GUI viewer for XML documents + utilities")
_info_banner_.append("ephys                 utilities for neo core objects")
_info_banner_.append("tiwt                     wavelet function + purelet denoise")
_info_banner_.append("ephys                    package with various electrophysiology routines")
_info_banner_.append("curvefitting -> crvf")
_info_banner_.append("signalprocessing -> sigp")
_info_banner_.append("imageprocessing -> imgp")
_info_banner_.append("strutils                 string utilities")
_info_banner_.append("plots                    matplotlib-based plotting routines")

def console_info():
    print("\n".join(_info_banner_))
    
# Form class,        Base class
__UI_MainWindow__, __QMainWindow__ = loadUiType(os.path.join(__module_path__,"mainwindow.ui"), from_imports=True, import_from="gui")

__UI_ScriptManagerWindow__, _ = loadUiType(os.path.join(__module_path__,"scriptmanagerwindow.ui"), from_imports=True, import_from="gui")

class WorkspaceViewer(QtWidgets.QTableView):
    """Inherits QTableView with customized drag & drop
    """
    def __init__(self, mainWindow=None, parent=None):
        super().__init__(parent=parent)
        
        self.dragStartPosition = QtCore.QPoint()
        
        self.mainWindow = mainWindow
        
    @safeWrapper
    def mousePressEvent(self, event):
        #print("WorkspaceViewer.mousePressEvent")
        if event.button() == QtCore.Qt.LeftButton:
            self.dragStartPosition = event.pos()
            
        event.accept()
        
    @safeWrapper
    def contextMenuEvent(self, event):
        #print("WorkspaceViewer.contextMenuEvent")
        #print(event.pos())
        self.customContextMenuRequested.emit(event.pos())
            
    @safeWrapper
    def mouseMoveEvent(self, event):
        #print("WorkspaceViewer.mouseMoveEvent")
        # NOTE: 2019-08-10 00:24:01
        # create QDrag objects for each dragged item
        # ignore the DropEvenmt mimeData in the console ()
        if event.buttons() & QtCore.Qt.LeftButton:
            if (event.pos() - self.dragStartPosition).manhattanLength() >= QtWidgets.QApplication.startDragDistance():
                indexList = [i for i in self.selectedIndexes() if i.column() == 0]
                
                if len(indexList) == 0:
                    return
                
                if not isinstance(self.mainWindow, ScipyenWindow):
                    return
                
                varNames = [self.mainWindow.workspaceModel.item(index.row(),0).text() for index in indexList]
                
                for varName in varNames:
                    drag = QtGui.QDrag(self)
                    mimData = QtCore.QMimeData()
                    mimeData.setText(varName)
                    drag.setMimeData(mimeData)
                    dropAction = drag.exec(QtCore.Qt.CopyAction)

# NOTE 2016-03-27 16:53:16
# the way multiple inheritance works in pyqt dictates that additional signals are 
# inerited only from the _FIRST_ superclass, which must also have the deepest 
# inheritance tree
#class WindowManager(ConfigurableQMainWindowMeta):
class WindowManager(__QMainWindow__):
    sig_windowRemoved = pyqtSignal(tuple, name="sig_windowRemoved")
    
    def __init__(self, config=None, parent=None, *args, **kwargs):
        super().__init__(parent)
        
        # gui_viewers defined in gui package (see gui/__init__.py)
        self.viewers = dict(map(lambda x: (x, list()), gui_viewers))
        # for matplotlib figures
        self.viewers[mpl.figure.Figure] = list()
        
        self.currentViewers = dict(map(lambda x: (x, None), gui_viewers))
        self.currentViewers[mpl.figure.Figure] = None
        
    @pyqtSlot(object)
    @safeWrapper
    def slot_windowActivated(self, obj):
        """Not used, but keep it
        """
        if isinstance(obj, (QtWidgets.QMainWindow, mpl.figure.Figure)):
            self._setCurrentWindow(obj)
    
    @pyqtSlot(int)
    @safeWrapper
    def slot_windowVariableDeleted(self, wid):
        # TODO
        viewer = self.sender()
        if not isinstance(viewer, QtWidgets.QMainWindow):
            return
        
        assert viewer.ID == wid
        
    @safeWrapper
    def handle_mpl_figure_click(self, evt):
        self._raiseWindow(evt.canvas.figure)
    
    @safeWrapper
    def handle_mpl_figure_enter(self, evt):
        self._setCurrentWindow(evt.canvas.figure)
        
    @safeWrapper
    def handle_mpl_figure_close(self, evt):
        """Removes the figure from the workspace and updates the workspace table.
        """
        fig_number = evt.canvas.figure.number
        fig_varname = "Figure%d" % fig_number
        plt.close(evt.canvas.figure)
        # NOTE: 2020-02-05 00:53:51
        # this also closes the figure window and removes it from self.currentViewers
        self.deRegisterViewer(evt.canvas.figure) # does not remove symbol from workspace
        
        # NOTE: now remove the figure variable name from user workspace
        ns_fig_names_objs = [x for x in self.shell.user_ns.items() if isinstance(x[1], mpl.figure.Figure) and x[1] is evt.canvas.figure]

        for ns_fig in ns_fig_names_objs:
            self.sig_windowRemoved.emit(ns_fig)
            #self.shell.user_ns.pop(ns_fig[0], None)
            #self.workspaceModel.update(from_console=False)
            
    @safeWrapper
    def _set_new_viewer_window_name_(self, winClass, name=None):
        """Sets up the name of a new window viewer variable in the workspace
        Should be called before initializing an instance of winClass.
        Can be bypassed by creating a viewer window instance directly in the 
        workspace by calling its constructor at the console.
        """
        # algorithm:
        # if name is a non-empty string, check if it is suitable as identifier,
        # and if it is already mapped to a variable in the workspace: 
        #   use validate_varname to get a version with a counter appended to it.
        #
        # if no name is given (name is either None, or an empty string), then
        # then compose the name based on the winClass name, append a counter based
        # on the number of viewers of winClass type, in self.viewers
        
        import keyword
        
        # NOTE: 2019-11-01 22:04:38
        # check winClass inherits from QtWidgets.QMainWindow, mpl.figure.Figure
        if not any([klass in winClass.mro() for klass in (scipyenviewer.ScipyenViewer, mpl.figure.Figure)]):
            raise ValueError("Unexpected window class %s" % winClass.__name__)
        
        # NOTE: 2019-11-01 22:04:47
        # check if winClass is one of the registered viewers
        # this makes NOTE 2019-11-01 22:04:38 redundant
        # TODO: mechanisms for registering new viewer types
        if winClass not in self.viewers:
            raise ValueError("Unexpected window class %s" % winClass.__name__)
        
        nViewers = len(self.viewers[winClass])
        
        if isinstance(name, str):
            if len(name.strip()):
                win_name = validate_varname(name, self.workspace)
            
            else:
                win_name = "%s_%d" % (winClass.__name__, nViewers)
                
        elif name is None:
            win_name = "%s_%d" % (winClass.__name__, nViewers)
        
        else:
            raise TypeError("name can be either a valid string or None")
            
        return win_name
            
    @safeWrapper
    def _newViewer(self, winClass, *args, **kwargs):
        """Factory method for a GUI Viewer or matplotlib figure.
        
        Parameters:
        -----------
        
        winClass : str, type, or sip.wrappertype
            The only acceptable type is mpl.figure.Figure (where mpl is an alias to matplotlib)
            
            The only acceptable sip.wrappertype objects are the viewer classes
            defined in the variable "gui_viewers" in the user workspace. These
            classes are:
            
            DataViewer, MatrixViewer, ImageViewer, SignalViewer, TableEditor, 
            TextViewer, XMLViewer.
            
            When a str the ony acceptable ones are the string verison of the 
            above (i.e. the value of their __name__ attribute).
            
        *args, **kwargs: passed directly to the constructor (__init__ function)
            of the winClass
            
        
        """
        # NOTE: 2021-07-08 14:52:44
        # called by ScipyenWindow.slot_newViewerMenuAction
        
        #print("WindowManager._newViewer winClass = %s" % winClass)
        #print("WindowManager._newViewer **kwargs", **kwargs)
        if isinstance(winClass, str) and len(winClass.replace("&","").strip()):
            wClass = winClass.replace("&","")
            
            if wClass not in [v.__name__ for v in gui_viewers]:
                raise ValueError("Unexpected viewer class name %s" % wClass)
            
            win_classes = [v for v in gui_viewers if v.__name__ == wClass]
            
            if len(win_classes):
                winClass = win_classes[0]
                
            else:
                raise ValueError("Unexpected viewer class name %s" % wClass)
            
        elif not isinstance(winClass, (type, sip.wrappertype)):
            raise TypeError("Expecting a type or sip.wrappertype; got %s instead" % type(winClass).__name__)
        
        else:
            if winClass not in self.viewers.keys():
                raise ValueError("Unexpected viewer class %s" % winClass.__name__)
            
        win_title = self._set_new_viewer_window_name_(winClass, name=kwargs.pop("win_title", None))
        
        #print("WindowManager._newViewer win_title = %s" % win_title)
        
        kwargs["win_title"] = win_title
        
        if "parent" not in kwargs:
            kwargs["parent"] = self
            
        # NOTE: 2021-07-08 08:41:41
        # do away with "pWin" in scipyen viewers; this is taken over by "parent"
        #if "pWin" not in kwargs:
            #kwargs["pWin"] = self
            
        if winClass is mpl.figure.Figure:
            fig_kwargs = dict()
            fig_init_params = inspect.signature(mpl.figure.Figure).parameters
            
            for key, val in kwargs.items():
                if key in fig_init_params:
                    fig_kwargs[key] = val
                    
            win = plt.figure(*args, **fig_kwargs)
            
            win.canvas.mpl_connect("button_press_event", self.handle_mpl_figure_click)
            win.canvas.mpl_connect("figure_enter_event", self.handle_mpl_figure_enter)
            
            win.canvas.mpl_connect("close_event", self.handle_mpl_figure_close)
            
            winId = int(win.number)
        
        else:
            win = winClass(*args, **kwargs)
            nViewers = len(self.viewers[winClass])
            win.ID = nViewers
            winId = win.ID
            win.sig_activated[int].connect(self.slot_setCurrentViewer)
            
        self.viewers[winClass].append(win)
        self.currentViewers[winClass] = win
        
        if winClass is mpl.figure.Figure:
            workspace_win_varname = "Figure%d" % win.number
            
        else:
            workspace_win_varname = strutils.str2symbol(win.winTitle)
            
        self.workspace[workspace_win_varname] = win
        
        self.workspaceModel.update()
        
        return win
    
    @safeWrapper
    def deRegisterViewer(self, win):
        """Removes references to the viewer window 'win' from the manager.
        
        Parameters:
        -----------
        
        win: a QMainWindow or matplotlib.figure.Figure instance
        
        ATTENTION: This function neither removes the viewer object from the 
        workspace, nor unbinds it from its symbol in the workspace!!!
        """
        if not isinstance(win, (QtWidgets.QMainWindow, mpl.figure.Figure)):
            return
        
        # NOTE: 2022-03-15 11:28:09
        # get_window_title is NOT a method of mpl Figue, but a DEPRECATED one
        # of its canvas (backend)
        #w_title = win.get_window_title() if isinstance(win, mpl.figure.Figure) else win.windowTitle()
        
        #print("WindowManager.deRegisterViewer %s %s" % (win.__class__, w_title))
        
        viewer_type = type(win)
        
        old_viewer_index = None
        
        if viewer_type in self.viewers.keys():
            if win in self.viewers[viewer_type]:
                old_viewer_index = self.viewers[viewer_type].index(win)
                self.viewers[viewer_type].remove(win)
            
        ## FIXME 2021-07-11 15:09:16
        ## this is problematic when deRegisterViewer is called during a closeEvent
        # and therefore land on a dead PyQt5 object which hasn't been garbage 
        # collected yet
        #if isinstance(win, mpl.figure.Figure):
            #plt.close(win) # also removes figure number from pyplot figure manager
            
        #else:
            #win.saveSettings()
            #win.close()
            
        if viewer_type in self.currentViewers:
            if len(self.viewers[viewer_type]) == 0:
                self.currentViewers[viewer_type] = None
            
            elif self.currentViewers[viewer_type] is win:
                if isinstance(old_viewer_index, int):
                    if old_viewer_index >= len(self.viewers[viewer_type]):
                        viewer_index = len(self.viewers[viewer_type]) - 1
                        
                    elif old_viewer_index == 0:
                        viewer_index = 0
                        
                    else:
                        viewer_index = old_viewer_index
                        
                    self.currentViewers[viewer_type] = self.viewers[viewer_type][viewer_index]
                
    def _raiseWindow(self, obj):
        """Sets obj to be the current window and raises it.
        Steals focus.
        """
        if not isinstance(obj, (scipyenviewer.ScipyenViewer, mpl.figure.Figure)):
            return
        
        self._setCurrentWindow(obj)
        
        if isinstance(obj, mpl.figure.Figure):
            plt.figure(obj.number)
            plt.get_current_fig_manager().canvas.activateWindow() # steals focus!
            plt.get_current_fig_manager().canvas.update()
            plt.get_current_fig_manager().canvas.draw_idle()
            obj.show() # steals focus!
            
        else:
            obj.activateWindow()
            obj.raise_()
            obj.setVisible(True)

    def _setCurrentWindow(self, obj):
        """Sets obj to be the current window without raising or focus stealing
        """
        if not isinstance(obj, (scipyenviewer.ScipyenViewer, mpl.figure.Figure)):
            return
        
        if type(obj) not in self.viewers.keys():
            self.viewers[type(obj)] = list()
            
        if obj not in self.viewers[type(obj)]:
            self.viewers[type(obj)].append(obj)

        self.currentViewers[type(obj)] = obj
        
        #if isinstance(obj, mpl.figure.Figure):
            #plt.figure(obj.number)
            ##plt.get_current_fig_manager().canvas.activateWindow() # steals focus!
            #plt.get_current_fig_manager().canvas.update()
            #plt.get_current_fig_manager().canvas.draw_idle()
            ##if isinstance(obj.canvas, QtWidgets.QWidget):
                ##obj.canvas.activateWindow()
                ##obj.canvas.raise_()
                ##obj.canvas.setVisible(True)
            ##obj.show() # steals focus!
            ##plt.show()
            
        #else:
            #obj.activateWindow()
            #obj.raise_()
            #obj.setVisible(True)
        
    @property
    def matplotlib_figures(self):
        """A list of figures managed by matplotlib.
        """
        return [plt.figure(i) for i in plt.get_fignums()]
    
    @property
    def managed_matplotlib_figures(self):
        """A list of figures managed by both matplotlib and self.
        """
        return [fig for fig in self.matplotlib_figures if fig in self.viewers[mpl.figure.Figure]]
    
    @pyqtSlot(int)
    @safeWrapper
    def slot_setCurrentViewer(self, wId):
        viewer = self.sender()
        viewer_type_name = type(viewer).__name__
        
        if not isinstance(viewer, QtWidgets.QMainWindow):
            return
        
        self._setCurrentWindow(viewer)
        
class ScriptManager(QtWidgets.QMainWindow, __UI_ScriptManagerWindow__, WorkspaceGuiMixin):
    signal_forgetScripts = pyqtSignal(object)
    signal_executeScript = pyqtSignal(str)
    signal_importScript = pyqtSignal(str)
    signal_pasteScript = pyqtSignal(str)
    signal_editScript = pyqtSignal(str)
    signal_openScriptFolder = pyqtSignal(str)
    signal_pythonFileReceived = pyqtSignal(str, QtCore.QPoint)
    signal_pythonFileAdded = pyqtSignal(str)
    
    
    # NOTE recently run scripts is managed by ScipyenWindow instance mainWindow
    # FIXME 2021-09-18 14:16:14 Change this so that it is managed instead by 
    # ScriptManager
    # We then need to connect pasting/dropping script file onto Scipyen mainWindow
    # or the internal console to script execution and adding of script file to
    # the internal scripts list  here.
    
    def __init__(self, parent=None):
        super(ScriptManager, self).__init__(parent)
        self.setupUi(self)
        WorkspaceGuiMixin.__init__(self, parent=parent)
        self._configureUI_()
        
        self.setWindowTitle("Scipyen Script Manager")
        
        self.loadSettings()
        
    def _configureUI_(self):
        addScript = self.menuScripts.addAction("Add scripts...")
        addScript.triggered.connect(self.slot_addScripts)
        self.scriptsTable.customContextMenuRequested[QtCore.QPoint].connect(self.slot_customContextMenuRequested)
        self.scriptsTable.cellDoubleClicked[int, int].connect(self.slot_cellDoubleClick)
        self.acceptDrops = True
        self.scriptsTable.acceptDrops = True
        
    def closeEvent(self, evt):
        self.saveSettings()
        
    def loadSettings(self):
        loadWindowSettings(self.qsettings, self)
            
    def saveSettings(self):
        saveWindowSettings(self.qsettings, self)
            
    def setData(self, scriptsDict):
        if not isinstance(scriptsDict, dict):
            return
        
        self.scriptsTable.clearContents()
        
        if len(scriptsDict) == 0:
            return
        
        self.scriptsTable.setRowCount(len(scriptsDict))
        
        for k, (key, value) in enumerate(scriptsDict.items()):
            script_item = QtWidgets.QTableWidgetItem(value)
            script_item.setToolTip(value)
            
            path_item = QtWidgets.QTableWidgetItem(key)
            path_item.setToolTip(key)
            
            self.scriptsTable.setItem(k, 0, script_item)
            self.scriptsTable.setItem(k, 1, path_item)
            
        self.scriptsTable.resizeColumnToContents(0)
        
    @safeWrapper
    def dropEvent(self, evt):
        if evt.mimeData().hasUrls():
            urls = evt.mimeData().urls()
            
            if len(urls) == 1 and (urls[0].isRelative() or urls[0].isLocalFile()) and os.path.isfile(urls[0].path()):
                # check if this is a python source file
                mimeType = QtCore.QMimeDatabase().mimeTypeForFile(QtCore.QFileInfo(urls[0].path()))
                
                if all([s in mimeType.name() for s in ("text", "python")]):
                    self.signal_pythonFileReceived.emit(urls[0].path(), evt.pos())
                    #return
            
        
            
    def clear(self):
        self.scriptsTable.clearContents()
        self.scriptsTable.setRowCount(0)
        
    def closeEvent(self, evt):
        self.saveSettings()
        evt.accept()
        self.close()
        
        evt.accept()
        
    @property
    def scriptsCount(self):
        return self.scriptsTable.rowCount()
    
    @property
    def scriptNames(self):
        return [self.scriptsTable.item(row, 0).text() for row in range(self.scriptsTable.rowCount())]
    
    @property
    def scriptFileNames(self):
        return [self.scriptsTable.item(row, 1).text() for row in range(self.scriptsTable.rowCount())]
        
        
    @pyqtSlot("QPoint")
    @safeWrapper
    def slot_customContextMenuRequested(self, pos):
        items = self.scriptsTable.selectedItems()
        
        cm = QtWidgets.QMenu("Open Scripts Manager", self)
        #actions = list()
        
        if len(items):
            if len(items) == 1:
                execItem = cm.addAction("Run")
                execItem.setToolTip("Execute selected script")
                execItem.triggered.connect(self.slot_executeScript)
                
                #actions.append(execItem)
                
                pasteItem = cm.addAction("Paste in Console")
                pasteItem.setToolTip("Paste script contents in console")
                pasteItem.triggered.connect(self.slot_teleportScript)
                
                #actions.append(pasteItem)
                
                editItem = cm.addAction("Edit")
                editItem.setToolTip("Edit script in system's default text editor")
                editItem.triggered.connect(self.slot_editScript)
                
                openFolderItem = cm.addAction("Open Containing Folder")
                openFolderItem.setToolTip("Open Containing Folder")
                openFolderItem.triggered.connect(self.slot_openScriptFolder)
                
            cm.addSeparator()
            
            delItems = cm.addAction("Forget")
            delItems.setToolTip("Forget selected scripts")
            delItems.triggered.connect(self.slot_forgetScripts)
            #actions.append(delItems)
            
            clearAction = cm.addAction("Forget All")
            clearAction.setToolTip("Forget All")
            clearAction.triggered.connect(self.slot_forgetAll)
        
        #actions.append(clearAction)
        cm.addSeparator()
        registerScript = cm.addAction("Add script...")
        registerScript.triggered.connect(self.slot_addScript)
        
        cm.popup(self.scriptsTable.mapToGlobal(pos))
            
    @pyqtSlot(int, int)
    @safeWrapper
    def slot_cellDoubleClick(self, row, col):
        item = self.scriptsTable.item(row,1)
        
        self.signal_executeScript.emit(item.text())
        
    @pyqtSlot()
    @safeWrapper
    def slot_addScript(self):
        targetDir = os.getcwd()
        fileName = QtWidgets.QFileDialog.getOpenFileName(self, caption=u"Run python script", filter="Python script (*.py)", directory = targetDir)
        
        if len(fileName) > 0:
            if isinstance(fileName, tuple):
                fileName = fileName[0] # NOTE: PyQt5 QFileDialog.getOpenFileName returns a tuple (fileName, filter string)
                
            #if isinstance(fileName, str) and len(fileName) > 0 and os.path.isfile(fileName):
                #self.signal_pythonFileAdded.emit(fileName)
            if pio.checkFileReadAccess(fileName):
                self.signal_pythonFileAdded.emit(fileName)
                #self._scripts.append(fileName)

    @pyqtSlot()
    @safeWrapper
    def slot_addScripts(self):
        targetDir = os.getcwd()
        
        # NOTE: returns a tuple (path list, filter)
        fileNames, fileFilter = QtWidgets.QFileDialog.getOpenFileNames(self, caption=u"Run python script", filter="Python script (*.py)", directory = targetDir)
        
        if pio.checkFileReadAccess(fileNames):
            for fileName in fileNames:
                self.signal_pythonFileAdded.emit(fileName)
            #self._scripts.extend(fileNames)
        
        
    @pyqtSlot()
    @safeWrapper
    def slot_forgetScripts(self):
        if len(self.scriptsTable.selectedItems()) == 0:
            return
        
        rows = list(set([i.row() for i in self.scriptsTable.selectedItems()]))
        
        items = [self.scriptsTable.item(r, 1).text() for r in rows]
        
        for r in rows:
            self.scriptsTable.removeRow(r)
        
        self.signal_forgetScripts.emit(items)
        
    @pyqtSlot()
    @safeWrapper
    def slot_forgetAll(self):
        items = [self.scriptsTable.item(r, 1).text() for r in range(self.scriptsTable.rowCount())]
        
        self.scriptsTable.clearContents()
        self.scriptsTable.setRowCount(0)
        
        self.signal_forgetScripts.emit(items)
        
    @pyqtSlot()
    @safeWrapper
    def slot_executeScript(self):
        if len(self.scriptsTable.selectedItems()) != 1:
            return
        
        row = [i.row() for i in self.scriptsTable.selectedItems()][0]
        
        item = self.scriptsTable.item(row, 1).text()
        
        self.signal_executeScript.emit(item)
        
    @pyqtSlot()
    @safeWrapper
    def slot_importAsModule(self):
        if len(self.scriptsTable.selectedItems()) != 1:
            return
        
        row = [i.row() for i in self.scriptsTable.selectedItems()][0]
        
        item = self.scriptsTable.item(row, 1).text()
        
        self.signal_importScript.emit(item)
        
        
    @pyqtSlot()
    @safeWrapper
    def slot_editScript(self):
        if len(self.scriptsTable.selectedItems()) != 1:
            return
        
        row = [i.row() for i in self.scriptsTable.selectedItems()][0]
        
        item = self.scriptsTable.item(row, 1).text()
        
        self.signal_editScript.emit(item)
        
    @pyqtSlot()
    @safeWrapper
    def slot_openScriptFolder(self):
        if len(self.scriptsTable.selectedItems()) != 1:
            return
        
        row = [i.row() for i in self.scriptsTable.selectedItems()][0]
        
        item = self.scriptsTable.item(row, 1).text()
        
        self.signal_openScriptFolder.emit(item)

    @pyqtSlot()
    @safeWrapper
    def slot_teleportScript(self):
        if len(self.scriptsTable.selectedItems()) != 1:
            return
        
        row = [i.row() for i in self.scriptsTable.selectedItems()][0]
        
        item = self.scriptsTable.item(row, 1).text()
        
        self.signal_pasteScript.emit(item)
        
        
# NOTE 2019-09-12 09:34:31
# Beginning to consolidate variable handling in the GUI framework
# TODO: make this configurable (a mime type-like mechanism?)
#class VTH(QtCore.QObject):
class VTH(object):
    """Variable Type Handler.
    Handles variable types
    TODO 2019-09-12 12:24:11
    Edit all gui viewer classes so that they advertise what variable types they
    support.
    """
    # NOTE:
    # actioName: a str or None
    #       name of the menu action as it will appear in the workspace context menu
    #       when an empty str or None, the action will NOT be added to the workspace context menu
    #       is to be displayed in console
    #
    #
    # types: a sequence (list, tuple) of types, possibly empty:
    #       when empty the action will NOT be added to the workspace context menu
    #       NOTE: when a tuple with a single element 'x', make sure it is passed as (x,)
    #       otherwise it will resolve to x itself !
    
    #default_handlers = dict(map(lambda x: (x, {"action":"Plot (matplotlib)",
                                           #"types": [np.ndarray, tuple, list]} if isinstance(x, mpl.figure.Figure) else {"action": x.view_action_name, "types": list(x.supported_types)}), gui_viewers))
    
    default_handlers = dict(map(lambda x: (x, {"action": x.view_action_name, "types": list(x.supported_types)}), gui_viewers))
    
    default_handlers[mpl.figure.Figure] = {"action":"Plot (matplotlib)",
                                           "types": [np.ndarray, tuple, list]}
    
    gui_handlers = deepcopy(default_handlers)

    @safeWrapper
    def register(viewerClass, dataTypes, actionName=None):
        """Modifies data handling by viewers or registers a new viewer type.
        Viewers are user-designed windows for data display.
        Parameters:
        ----------
        viewerClass: sip.wrappertype derived from gui.scipyenviewer.ScipyenViewer
                OR a python type derived from matplotlib.fiure.Figure.
        
        dataTypes: a python type or a sequence (tuple, list) of python types
        
        actionName: a non-empty str or None, the name of the menu action in the
            context menu of the Scipyen's workspace browser 
            
            When actionName is None, if the viewer is already registered its 
            action name is unchanged; for a new viewer, the action name will be
            set to "View".
        
        """
        if not inspect.isclass(viewerClass):
            raise TypeError("viewerClass must be a type, class or sip wrapper type; got %s instead" % type(viewerClass).__name__)
        
        if not isinstance(viewerClass, sip.wrappertype) and viewerClass is not mpl.figure.Figure:
            raise TypeError("%s has unsupported type (%s); expecting a sip.wrappertype or matplotlib Figure" % (viewerClass.__name__, type(viewerClass).__name__))
        
        if not isinstance(actionName, (str, type(None))):
            raise TypeError("actionName expected to be a str or None; got %s instead" % type(actionName).__name__)
        
        if viewerClass in gui_handlers:
            # viewer type is already registered; action name my be left unchanged
            if isinstance(actionName, str) and len(actionName.strip()):
                VTH.gui_handlers[viewerClass]["action"] = actionName
                
            if inspect.isclass(dataTypes):
                VTH.gui_handlers[viewerClass]["types"].append(dataTypes)
                
            elif isinstance(dataTypes, (tuple, list)):
                if not all([inspect.isclass(v) for v in dataTypes]):
                    raise TypeError("Expecting a sequence of types in 'dataTypes")
                
                d_types = [d for d in dataTypes if d not in VTH.gui_handlers[viewerClass]["types"]]
                VTH.gui_handlers[viewerClass]["types"] += d_types
                
            else:
                raise TypeError("'dataTypes' expected to be a type or a sequence of types")
                
        else:
            # registers a new viewer type
            if inspect.isclass(dataTypes):
                dataTypes = [dataTypes]
                
            elif isinstance(dataTypes, (tuple, list)) and not all([inspect.isclass(d) for d in dataTypes]):
                raise TypeError("Expecting a sequence of types in 'dataTypes")
            
            else:
                raise TypeError("'dataTypes' expected to be a type or a sequence of types")
            
            if actionName is None or (isinstance(actionName, str) and len(actionName.strip()) == 0):
                actionName = "View"
            
            VTH.gui_handlers[viewerClass] = {"action":actionName,
                                            "types":dataTypes}
            

    def registered_handlers():
        return [viewer for viewer in VTH.gui_handlers]
    
    def is_supported_type(obj_type, viewer_type):
        return obj_type in VTH.gui_handlers[viewer_type]["types"]
        
    def is_supported_ancestor_type(obj_type, viewer_type):
        return any([t in inspect.getmro(obj_type) for t in VTH.gui_handlers[viewer_type]["types"]])
        #return any([t in obj_type.mro() for t in VTH.gui_handlers[viewer_type]["types"]])
        
    def get_handlers_for_type(obj_type):
        #viewers = [viewer_type for viewer_type in VTH.gui_handlers.keys() if VTH.is_supported_type(obj_type, viewer_type)]
        #mro_viewers = [viewer_type for viewer_type in VTH.gui_handlers.keys() if VTH.is_supported_ancestor_type(obj_type, viewer_type)]
        
        viewers_types = [(viewer_type, VTH.gui_handlers[viewer_type]["types"]) for viewer_type in VTH.gui_handlers.keys() if VTH.is_supported_type(obj_type, viewer_type)]
        
        viewers_mro = [(viewer_type, VTH.gui_handlers[viewer_type]["types"]) for viewer_type in VTH.gui_handlers.keys() if VTH.is_supported_ancestor_type(obj_type, viewer_type)]
        
        viewer_priorities = list()
        
        for v_t in viewers_types:
            if obj_type in v_t[1]:
                for k, type_obj in enumerate(v_t[1]):
                    if obj_type is type_obj:
                        viewer_priorities.append((k, v_t[0]))
                        
            else: #  look for ancestor types only if the object type is not explicitly listed in the viewer's supported_types'
                for k, type_obj in enumerate(v_t[1]):
                    if type_obj in obj_type.mro():
                        viewer_priorities.append((k, v_t[0]))
                    
        if len(viewer_priorities):
            viewer_priorities = sorted(viewer_priorities, key=lambda x: x[0])
            
        n_direct = len(viewer_priorities)
        
        for v_t in viewers_mro:
            if obj_type in v_t[1]:
                for k, type_obj in enumerate(v_t[1]):
                    if obj_type is type_obj: # or type_obj in obj_type.mro():
                        if v_t[0] not in [v_[1] for v_ in viewer_priorities]:
                            viewer_priorities.append((n_direct+k, v_t[0]))
                        
            else: #  look for ancestor types only if the object type is not explicitly listed in the viewer's supported_types'
                for k, type_obj in enumerate(v_t[1]):
                    if type_obj in obj_type.mro():
                        if v_t[0] not in [v_[1] for v_ in viewer_priorities]:
                            viewer_priorities.append((n_direct+k, v_t[0]))
                    
        if len(viewer_priorities):
            viewer_priorities = sorted(viewer_priorities, key=lambda x: x[0])
            
        return viewer_priorities
    
    def get_view_actions(variable):
        #if isinstance(variable, (type, sip.wrappertype)):
        if inspect.isclass(variable):
            vartype = variable
        else:
            vartype = type(variable)
            
        if vartype in VTH.gui_handlers.keys():
            return 
            
        viewers_actions = [(key, value["action"]) for key, value in VTH.gui_handlers.items() if any([v in value["types"] for v in inspect.getmro(vartype)])]
        
        return viewers_actions

    def get_actionNames(variable):
        #if isinstance(variable, (type, sip.wrappertype)):
        if inspect.isclass(variable):
            vartype = variable
        else:
            vartype = type(variable)
            
        if vartype in VTH.gui_handlers.keys() or QtWidgets.QWidget in inspect.getmro(vartype):
            return 
            
        actionNames = [value["action"] for key, value in VTH.gui_handlers.items() if any([v in value["types"] for v in inspect.getmro(vartype)])]
        
        return actionNames
    
    def reset_all():
        """Resets all gui handlers to the default.
        This will remove any registered custom viewer!
        """
        VTH.gui_handlers = deepcopy(VTH.default_handlers)
        
    def reset_handler(viewerClass):
        """Resets the configuration for the built-in viewer types.
        Does nothing for user-designed viewer that have been registered manually.
        """
        if viewerClass in VTH.default_handlers:
            VTH.gui_handlers[viewerClass] = deepcopy(VTH.default_handlers[viewerClass])

class ScipyenWindow(WindowManager, __UI_MainWindow__, WorkspaceGuiMixin):
    ''' Main pict GUI window
    '''
    # NOTE: 2021-08-23 10:36:14 WindowManager inherits from __QMainWindow__ which
    # is QtWidgets.QMainWindow
    workspaceChanged = pyqtSignal()
    
    _instance = None
    
    # TODO: 2021-11-26 17:23:45 To add:
    # saveFile, runScript, showObj, sysOpen, editor
    # 
    _export_methods_ = (("slot_importPrairieView", "importPrairieView"),
                        ("openFile", "openFile"),
                        ("openFile", "openFile"),
                        ("slot_selectWorkDir", "selectWorkingDirectory"),
                        ("slot_showScriptsManagerWindow", "scritpsManager"),
                        )
    
    @classmethod
    def initialized(cls):
        return hasattr(cls, "_instance" and isinstance(cls._instance, cls))
        
    @classmethod
    def instance(cls):
        if hasattr(cls, "_instance"):
            return cls._instance
    
    pluginActions = []
    
    # NOTE: 2016-04-17 16:11:56
    # argument and return variable parsing moved to _installPluginFunction_
    def _inputPrompter_(self, nOutputs=0, in_types=None, arg_names=None, arg_defaults=None, var_args=None, kw_args=None):
        '''
        Decorator to prompt user with a dialog for the arguments that are to be 
        dispatched to function f.
        
        Parameters:
        
        See Python Wiki / PythonDecoratorLibrary / Creating well behaved decorators
        '''
        
        #print(nOutputs)
        def fs(a, b):
            return ''.join((a,b))
        
        def prompt_f(f):
            '''
            Does the actual function call of the wrapped plugin function
            '''
            
            try:
                
                if in_types is not None:# and ((type(in_types) in (tuple, list) and len(in_types) > 0) or (type(in_types) is type)):
                    def inner_f():
                        def interpret_str(varstr):
                            try:
                                ret = int(varstr)
                            except:
                                try:
                                    ret = float(varstr)
                                except:
                                    ret = varstr
                                    
                            print(ret)
                            return ret
                        
                        def parsekw(varstr):
                            print(varstr)
                            dictargs = [[interpret_str(j.strip()) for j in i.split('=')] for i in varstr.split(',')]
                            print(len(dictargs))
                            dct = dict()
                            
                            for k,e in enumerate(dictargs):
                                if len(e) == 2:
                                    dict[e[0]] = e[1]
                                else:
                                    print("expected key=value pair at element %d in keyword list" % k)
                                    
                            return dict()
                            
                        # prepare the dialog (see vigra.pyqt.QuickDialog)
                        #d = vigra.pyqt.quickdialog.QuickDialog(self, "Enter Arguments")
                        d = qd.QuickDialog(self, "Enter Arguments")
                        d.promptWidgets=[]
                        d.varPromptWidget = None
                        d.kwPromptWidget = None
                        d.returnWidgets=[]
                        args = []
                        
                        for (a,b,c) in zip(in_types, arg_names, arg_defaults):
                            if isinstance(a, type):
                                if a.__name__ in ('int', 'long'):
                                    widgetClass = qd.IntegerInput
                                    #widgetClass = vigra.pyqt.quickdialog.IntegerInput
                                elif a.__name__ == 'float':
                                    widgetClass = qd.FloatInput
                                    #widgetClass = vigra.pyqt.qd.FloatInput
                                elif a.__name__ == 'str':
                                    widgetClass = qd.StringInput
                                    #widgetClass = vigra.pyqt.quickdialog.StringInput
                                elif a.__name__ == 'bool':
                                    widgetClass = qd.CheckBox
                                    #widgetClass = vigra.pyqt.quickdialog.CheckBox
                                else:
                                    widgetClass = qd.InputVariable
                                    #widgetClass = vigra.pyqt.quickdialog.InputVariable

                                promptWidget = widgetClass(d, b + " (" + a.__name__ +")")

                                if c is not None:
                                    if isinstance(a, type):
                                        if a.__name__ in ("int", "long", "float"):
                                            promptWidget.setValue(str(c))
                                        elif a.__name__ == "str":
                                            promptWidget.setText(c)
                                        elif a.__name__ == "bool":
                                            promptWidget.setChecked(c)

                            elif isinstance(a, str) and a=='~':
                                # this means the function expects a variable selected 
                                # in the workspace table
                                # therefore we don't need a prompt widget for it
                                promptWidget = None # so that argument parsing below works
                                pass
                            else:
                                raise ValueError("Incorrect input type was supplied")

                            d.promptWidgets.append(promptWidget)
                            
                        if var_args is not None:
                            d.varPromptWidget = qd.InputVariable(d, "Variadic arguments: ")
                            #d.varPromptWidget = vigra.pyqt.quickdialog.InputVariable(d, "Variadic arguments: ")
                            
                        if kw_args is not None:
                            d.kwPromptWidget = qd.InputVariable(d, "Keyword arguments: ")
                            #d.kwPromptWidget = vigra.pyqt.quickdialog.InputVariable(d, "Keyword arguments: ")
                            
                        if nOutputs > 0:
                            d.addLabel('Return variable names:')
                            ret_names = map(fs, ['var '] * nOutputs, map(str, range(nOutputs)))
                            suggested_ret_names = map(fs, ['var_'] * nOutputs, map(str, range(nOutputs)))
                            
                            print("type of ret_names: ", type(ret_names))
                            
                            rt_nm = [i for i in ret_names]
                            
                            srt_nm = [i for i in suggested_ret_names]
                            
                            for k in range(nOutputs):
                                widget = qd.OutputVariable(d, rt_nm[k])
                                #widget = vigra.pyqt.quickdialog.OutputVariable(d, rt_nm[k])
                                widget.setText(srt_nm[k])
                                d.returnWidgets.append(widget)
                        
                        if d.exec_() == 0:
                            return # don't call anything, just return nothing
                        
                        # NOTE: 2016-04-15 03:19:05
                        # deal with positional arguments
                        for (a,b) in zip(in_types, d.promptWidgets):
                            if isinstance(a, type) and b is not None:
                                if a.__name__ in ('int', 'float', 'long'):
                                    if len(b.text()) == 0:
                                        return # in case field was empty
                                    args.append(b.value())
                                elif a.__name__ == 'bool':
                                    args.append(b.selection())
                                elif a.__name__ == 'str':
                                    if b.text() == "None":
                                        args.append(None)
                                    elif b.text() == '~':
                                        selVarName = self.getCurrentVarName()
                                        if selVarName is not None:
                                            args.append(self.workspace[selVarName])
                                        else:
                                            args.append(None)
                                    else:
                                        args.append(b.text())
                                else:
                                    args.append(self.workspace[b.text()])
                                    
                            elif isinstance(a, str) and a == '~' and b is None: # b SHOULD be None here
                                selVarName = self.getCurrentVarName()
                                if selVarName is not None:
                                    args.append(self.workspace[selVarName])

                            else:
                                raise TypeError("incorrect parameter type in type list")
                                
                        # NOTE: 2016-04-15 03:19:30
                        # deal with variadic arguments
                        if (var_args is not None and len(d.varPromptWidget.text()) > 0):
                            vastrlist = d.varPromptWidget.text().split('.')
                            valist = [interpret_str(i.strip()) for i in vastrlist]
                            args = args + valist
                            
                        # NOTE: 2016-04-15 03:20:00
                        # deal with keyword arguments
                        if (kw_args is not None and len(d.kwPromptWidget.text()) > 0):
                            kwargs = parsekw(d.kwPromptWidget.text())
                            ret = f(*args, **kwargs) # no need to return anything here
                        else:
                            ret = f(*args) # no need to return anything here
                        
                        # NOTE: 2016-04-15 03:20:13
                        # finally, deal with return variables
                        if (nOutputs > 0 and ret is not None):
                            if type(ret) in (tuple, list):
                                for k in range(len(ret)):
                                    var_name = d.returnWidgets[k].text()
                                    self.workspace[var_name]=ret[k]
                            else:
                                var_name = d.returnWidgets[0].text()
                                self.workspace[var_name] = ret
                                
                        # NOTE: 2016-04-17 22:18:05
                        # do this always: functions that do not return but take mutable arguments
                        # from the workspace may result in these arguments being modified and
                        # we'd like this to be seen in the workspace table
                        #
                        # and do it from within inner_f
                        self.workspaceModel.update()
                        # NOTE: 2016-04-17 16:26:33 
                        # inner_f does not need to return anything

                else:
                    def inner_f():
                        if nOutputs > 0:
                            d = qd.QuickDialog(self, "Enter Return Variable Names")
                            #d = vigra.pyqt.quickdialog.QuickDialog(self, "Enter Return Variable Names")
                            d.returnWidgets=[]
                            ret_names = map(fs, ['var '] * nOutputs, map(str, range(nOutputs)))
                            suggested_ret_names = map(fs, ['var_'] * nOutputs, map(str, range(nOutputs)))
                            for k in range(nOutputs):
                                widget = qd.OutputVariable(d, ret_names[k])
                                #widget = vigra.pyqt.quickdialog.OutputVariable(d, ret_names[k])
                                widget.setText(suggested_ret_names[k])
                                d.returnWidgets.append(widget)

                            if d.exec_() == 0:
                                return # don't call anything, just return nothing

                        ret = f()

                        if (nOutputs > 0 and ret is not None):
                            if type(ret) in (tuple, list):
                                for k in range(len(ret)):
                                    var_name = d.returnWidgets[k].text()
                                    self.workspace[var_name]=ret[k]
                            else:
                                var_name = d.returnWidgets[0].text()
                                self.workspace[var_name] = ret

                        # NOTE: 2016-04-17 22:18:05
                        # do this always: functions that do not return but take mutable arguments
                        # from the workspace may result in these arguments being modified and
                        # we'd like this to be seen
                        #
                        # and do it from within inner_f
                        self.workspaceModel.update()

                        # NOTE: 2016-04-17 16:27:01
                        # inner_f does not need to return anything

                inner_f.__name__ = f.__name__
                inner_f.__doc__ = f.__doc__
                inner_f.__dict__.update(f.__dict__)
                
                return inner_f
            
            except Exception as e:
                print(str(e))

        return prompt_f
    
    # NOTE: 2016-04-17 16:14:18
    # argument parsing code moved to _installPluginFunction_ ini order to keep
    # this decorator small: this decorator should only do this: DECORATE
    def slot_wrapPluginFunction(self, f, nReturns = 0, argumentTypes = None, \
                                argumentNames=None, argumentDefaults=None, \
                                variadicArguments=None, keywordArguments=None):
        '''
        Defines a new slot for plugins functionality
        '''
        #from PyQt5.QtCore import pyqtSlot
            
        # NOTE: 2016-04-17 16:16:52 moved to _installPluginFunction_
        ## NOTE:2016-04-17 15:39:03 in python 3 use inspect.getfullargspec(f)
        #argSpec = inspect.getfullargspec(f)
        #kwa = argSpec.keywords


        # NOTE: 2016-04-17 16:18:18 to reflect new code layout
        @pyqtSlot()
        @self._inputPrompter_(nReturns, argumentTypes, argumentNames, argumentDefaults, variadicArguments, keywordArguments)
        def sw_f(*argumentTypes, **keywordArguments):
            return f(*argumentTypes, **keywordArguments)
        
        sw_f.__name__ = f.__name__
        sw_f.__doc__ = f.__doc__
        sw_f.__dict__.update(f.__dict__)
        
        if hasattr(f, '__annotations__'):
            sw_f.__setattr__('__annotations__', getattr(f, '__annotations__'))
        
        return sw_f

    #@processtimefunc
    def __init__(self, app:QtWidgets.QApplication, 
                 parent:typing.Optional[QtWidgets.QWidget]=None,
                 *args, **kwargs) -> None:
        """Scipyen's main window initializer (constructor).
        
        Parameters:
        ===========
        app: QtWidgets.QApplication. The PyQt5 application instance. 
            This instance runs the main GUI event loop and therefore there can 
            be only one throughout a Scipyen session (i.e., is a 'singleton').
            
            All Scipyen facilities (or 'apps', e.g., LSCaT, LTP, both internal 
            and external consoles, etc.) run under this event loop, which should
            not be confused with the IPython's REPL that runs with each console.
        
        settings: confuse.LazyConfig Optional (default is None) 
            The database containing non-Qt configuration data, global to Scipyen.
            This is where configurable objects (including facilities or 'apps')
            store their non-Qt related settings.
        
        parent: QtWidgets.QWidget.
        """
        super().__init__(parent) # 2016-08-04 17:39:06 NOTE: QMainWindow python3 way
        self.app = app
        
        #### BEGIN configurables; for each of these we define a read-write property
        # decorated with markConfigurable
        self._recentFiles               = collections.OrderedDict()
        self._recentDirectories         = collections.deque()
        self._fileSystemFilterHistory   = collections.deque()
        self._lastFileSystemFilter      = str()
        self._recentVariablesList       = collections.deque()
        self._lastVariableFind          = str()
        self._commandHistoryFinderList  = collections.deque()
        self._lastCommandFind           = str()
        #self._recentScripts             = collections.deque()
        self._recentScripts             = list()
        self._recent_scripts_dict_      = dict()
        self._showFilesFilter           = False
        self._console_docked_           = False
        
        # ### END configurables, but see NOTE:2022-01-28 23:16:57 below
        
        self.navPrevDir                 = collections.deque()
        self.navNextDir                 = collections.deque()
        self.currentDir                 = None
        self.workspace                  = dict()
        self._nonInteractiveVars_       = dict()
        self.console                    = None
        self.ipkernel                   = None
        self.shell                      = None
        self.historyAccessor            = None
        
        #self.scipyenEditor              = "kwrite"
        
        self.external_console           = None
        
        self._maxRecentFiles = 10 # TODO: make this user-configurable
        self._maxRecentDirectories = 100 # TODO: make this user-configurable
    
        #pg.setConfigOptions(editorCommand=self.scipyenEditor)
        
        #self._default_scipyen_settings_ = defaults
        
        # NOTE: 2021-08-17 13:09:38
        # passed from scipyen.main(), this is 
        # confuse.LazyConfig("Scipyen", "scipyen_defaults")
        # and is aliased in the workspace as 'scipyen_settings'
        # NOTE: 2021-09-09 12:00:19
        # obsoletes NOTE: 2021-08-17 13:09:38; imported directly from core.scipyen_config
        # From console, the user configuration file name is accessed as 
        # scipyen_settings.user_config_path()
        # --> $HOME/.config/Scipyen/config.yaml
        # WARNING this has nothing to do with %config magic in IPython (available
        # in Scipyen's consoles)
        #self._scipyen_settings_         = scipyen_settings 
        
        # NOTE: Qt GUI settings in $HOME/.config/Scipyen/Scipyen.conf
        # this can only be accessed once the Qt application is instantiated in
        # order for its organizationName and applicationName to be set
        # Since the ScipyenWindow instance is the first Scipyen object that
        # comes alive, the qsettings must be set up here and not rely on what is
        # inherited from ScipyenConfigurable (indirectly via WorkspaceGuiMixin)
        #self.qsettings = QtCore.QSettings(QtCore.QCoreApplication.organizationName(),
                                          #QtCore.QCoreApplication.applicationName())
        #self.qsettings                   = QtCore.QSettings("Scipyen", "Scipyen")

        # NOTE: 2021-08-17 12:29:29
        # directory where scipyen is installed
        # aliased in the workspace as 'scipyen_topdir'
        self._scipyendir_ = os.path.dirname(__module_path__) 
                
        #### BEGIN - to revisit
        self._temp_python_filename_   = None # cached file name for python source (for loading or running)
        
        #self._save_settings_guard_ = False
        
        self._copy_varnames_quoted_ = False
        
        self._copy_varnames_separator_ = " "
        #### END - to revisit
        
                # NOTE: 2021-08-17 12:38:41 see also NOTE: 2021-08-17 10:05:20 in scipyen.py
        #self._default_GUI_style = self.app.style()
        self._current_GUI_style_name = "Default"
        self._prev_gui_style_name = self._current_GUI_style_name
        
        #self._setup_console_pygments_()
        
        
        #self._defaultCursor = QtGui.QCursor(QtCore.Qt.ArrowCursor)
        
        # NOTE: WARNING 2021-09-16 14:32:03
        # this must be called AFTER all class and instance attributes used in the 
        # configurables mechanism have been defined, and BEFORE self._configureUI_()
        # This is so that GUI widgets members of the ScipyenWindow instance have
        # been themselves initialized
        self.setupUi(self)
        
        WorkspaceGuiMixin.__init__(self, parent=self)#, settings=settings)
        self.scriptsManager = ScriptManager(parent=self)
        self.scriptsManager.signal_executeScript[str].connect(self._slot_runPythonScriptFromManager)
        self.scriptsManager.signal_importScript[str].connect(self._slot_importPythonScriptFromManager)
        self.scriptsManager.signal_pasteScript[str].connect(self._slot_pastePythonScriptFromManager)
        self.scriptsManager.signal_forgetScripts[object].connect(self._slot_forgetScripts_)
        self.scriptsManager.signal_editScript[str].connect(self.slot_systemEditScript)
        self.scriptsManager.signal_openScriptFolder[str].connect(self.slot_systemOpenParentFolder)
        self.scriptsManager.signal_pythonFileReceived[str, QtCore.QPoint].connect(self.slot_handlePythonTextFile)
        self.scriptsManager.signal_pythonFileAdded[str].connect(self._slot_scriptFileAddedInManager)
        
        # NOTE: 2016-04-15 23:58:08
        # place holders for the tree widget item holding the commands in the 
        # current session, in the command history tree widget
        self.currentSessionTreeWidgetItem = None
        
        # NOTE: 2018-10-07 21:12:14
        # (re)initialize self.workspace, self._nonInteractiveVars_, 
        # self.ipkernel, self.console and self.shell so it must be called before
        # setting the workspace model
        self._init_QtConsole_() 
        
        self.fileSystemModel            = QtWidgets.QFileSystemModel(parent=self)
        
        self.workspaceModel             = WorkspaceModel(self.shell, parent=self,
                                                         mpl_figure_close_callback=self.handle_mpl_figure_close,
                                                         mpl_figure_click_callback=self.handle_mpl_figure_click,
                                                         mpl_figure_enter_callback=self.handle_mpl_figure_enter)
        
        self.sig_windowRemoved.connect(self.slot_windowRemoved) # signal inherited from WindowManager
        
        # NOTE: 2020-10-22 13:30:54
        # self._nonInteractiveVars_ is updated in _init_QtConsole_()
        self.workspaceModel.user_ns_hidden.update(self._nonInteractiveVars_)
        self.user_ns_hidden = self.workspaceModel.user_ns_hidden
        
        self.shell.events.register("pre_execute", self.workspaceModel.pre_execute)
        self.shell.events.register("post_execute", self.workspaceModel.post_execute)
        
        #self.workspaceModel.windowVariableDeleted[int].connect(self.slot_windowVariableDeleted)
        
        # NOTE: 2021-01-06 17:22:45
        # a lot of things happen up to here which depend on an initialized bare-bones
        # UI; hence setupUi must be called early (where it is right now), and
        # _configureUI_ must be called NOW; this will initialize additional UI
        # elements and signal-slot connections NOT defined in the *.ui file
        self._configureUI_()
        
        # NOTE:2022-01-28 23:16:57
        # when collections are modified directly (instead of setting via
        # property setter, see  NOTE:FIXME:2022-01-28 23:11:59) the 
        # configurable_traits are NOT populated/notified!
        # Hence I need to force this here
        
        if isinstance(getattr(self, "configurable_traits", None), DataBag):
            self.configurable_traits["RecentScripts"] = self._recentScripts
            
        # With all UI and their signal-slot connections in place we can now
        # apply stored settings, including the 'state' of the ScipyenWindow object
        #  (a QMainWindow instance)
        #
        self.loadSettings()
        
        self.activeDockWidget = self.dockWidgetWorkspace
        
        
        # NOTE: 2021-08-17 12:36:49 TODO custom icon ?
        # see also NOTE: 2021-08-17 10:06:24 in scipyen.py
        icon = QtGui.QIcon.fromTheme("python")
        #self.setWindowIcon(icon) # this doesn't work? -- next line does
        QtWidgets.QApplication.setWindowIcon(icon)

        # -----------------
        # connect widget actions through signal/slot mechanism
        # NOTE: 2017-07-04 16:28:52
        # do not delete: this is the first code where self.cwd is defined & initiated!
        self.cwd = os.getcwd()
        
        # NOTE: 2016-03-20 14:49:05
        # we also need to quit the app when Pict main window is closed
        self.app.destroyed.connect(self.slot_Quit)
        
        # NOTE: 2017-07-04 16:10:14 -- NOT NEEDED ANYMORE
        # for this to work one has to set horizontalScrollBarPolicy
        # to ScrollBarAlwaysOff (e.g in QtDesigner)
        #self._resizeFileColumn_()
        
        # NOTE: 2016-04-15 12:18:04
        # TODO/FIXME also import the plugins in the pict / ipkernel scopes
        
        # NOTE: 2016-04-15 14:25:23
        # all this does is to make these guys visible in the workspace browser -- do we really want this?
        # clearly not, since the workspace is the user_ns namespace of the ipython kernel, where all 
        # free variables are held (plus bits added by ipython)
        #if len(pict_plugin_loader.loaded_plugins) > 0:
            #self.workspace.update(dict(pict_plugin_loader.loaded_plugins))
            
        ##print("ScipyenWindow initialized")
        
        # NOTE: 2018-02-22 13:36:17
        # FIXME: 2021-08-17 12:41:57 TODO Sounds contrived - check is really needed
        # and, if not, then remove
        # finally, inject self into relevant modules:
        #for m in (ltp, ivramp, membrane, epsignal, CaTanalysis, pgui, sigp, imgp, crvf, plots):
        self_aware_modules = (ltp, ivramp, membrane, CaTanalysis, pgui, sigp, imgp, crvf, plots)
        #if has_vigra:
            #self_aware_modules = (ltp, ivramp, membrane, CaTanalysis, pgui, sigp, imgp, crvf, plots)
        #else:
            #self_aware_modules = (ltp, ivramp, membrane, pgui, sigp, crvf, plots)
            
        for m in self_aware_modules:
            m.__dict__["mainWindow"] = self
            m.__dict__["workspace"] = self.workspace
            
        # NOTE: 2021-08-17 12:45:10 TODO
        # currently used in _run_loop_process_, which at the moment is not used 
        # anywhere - keep available as app-wide threadpool for various sub-apps
        self.threadpool = QtCore.QThreadPool()
        
        self.__class__._instance = self # FIXME: what's this for?!? - flag as singleton?
        
    #### BEGIN Properties
    @property
    def scipyenSettings(self):
        return self._scipyen_settings_
    
    @scipyenSettings.setter
    def scipyenSettings(self, value):
        self._scipyen_settings_ = value
        self.workspace["scipyen_settings"] = self._scipyen_settings_
        
    @property
    def consoleDocked(self):
        return self._console_docked_
    
    @markConfigurable("ConsoleDocked", "Qt")
    @consoleDocked.setter
    def consoleDocked(self, value):
        self._console_docked_ = value is True
        
        
    @property
    def maxRecentFiles(self) -> int:
        return self._maxRecentFiles
    
    @markConfigurable("MaxRecentFiles", "Qt")
    @maxRecentFiles.setter
    def maxRecentFiles(self, val:int):
        if isinstance(val, int) and val >= 0:
            self._maxRecentFiles = val
            
    @property
    def guiStyle(self) -> str:
        return self._current_GUI_style_name
    
    @markConfigurable("WidgetStyle", "qt", default="Default")
    @guiStyle.setter
    def guiStyle(self, val:str) -> None:
        if not isinstance(val, str) or val not in self._available_Qt_style_names_:
            return
        
        if val =="Default":
            self.app.setStyle(QtWidgets.QApplication.style())
        else:
            self.app.setStyle(val)
            
        self._current_GUI_style_name = val
            
    @property
    def maxRecentDirectories(self) -> int:
        return self._maxRecentDirectories
    
    @markConfigurable("MaxRecentDirectories", "Qt", default=10)
    @maxRecentDirectories.setter
    def maxRecentDirectories(self, val:int):
        if isinstance(val, int) and val >= 0:
            self._maxRecentDirectories = val
        
    @property
    def recentFiles(self) -> collections.OrderedDict:
        return self._recentFiles
    
    @markConfigurable("RecentFiles", "Qt", default=10)
    @recentFiles.setter
    def recentFiles(self, val:typing.Optional[typing.Union[collections.OrderedDict, tuple, list]]=None) -> None:
        if isinstance(val, collections.OrderedDict):
            self._recentFiles = val
        elif isinstance(val, (tuple, list)):
            self._recentFiles = collections.OrderedDict(zip(val, ["vigra"] * len(val)))
        else:
            self._recentFiles = collections.OrderedDict()
            
        self._refreshRecentFilesMenu_()
            
    @property
    def recentDirectories(self) -> collections.deque:
        return self._recentDirectories
    
    @markConfigurable("RecentDirectories", "Qt")
    @recentDirectories.setter
    def recentDirectories(self, val:typing.Optional[typing.Union[collections.deque, list, tuple]]=None) -> None:
        if isinstance(val, (collections.deque, list, tuple)):
            self._recentDirectories = collections.deque(val)
        else:
            self._recentDirectories = collections.deque()
            
        if len(self._recentDirectories) == 0:
            self._recentDirectories.appendleft(os.getcwd())
            
        self.slot_changeDirectory(self._recentDirectories[0]) # alse refreshes gui
            
    @property
    def fileSystemFilterHistory(self) -> collections.deque:
        return self._fileSystemFilterHistory
    
    @markConfigurable("RecentFileSystemFilters", "Qt")
    @fileSystemFilterHistory.setter
    def fileSystemFilterHistory(self, 
                                val:typing.Optional[typing.Union[collections.deque, list, tuple]] = None) -> None:
        if isinstance(val, (collections.deque, list, tuple)):
            self._fileSystemFilterHistory = collections.deque(val)
            
        else:
            self._fileSystemFilterHistory = collections.deque()
            
        if len(self._fileSystemFilterHistory):
            self.fileSystemFilter.clear()
            for item in self._fileSystemFilterHistory:
                if isinstance(item, str):
                    self.fileSystemFilter.addItem(item)
            
    @property
    def lastFileSystemFilter(self) -> str:
        return self._lastFileSystemFilter
    
    @markConfigurable("LastFileSystemFilter", "Qt")
    @lastFileSystemFilter.setter
    def lastFileSystemFilter(self, val:typing.Optional[str] = None) -> None:
        if isinstance(val, str):
            self._lastFileSystemFilter = val
        else:
            self._lastFileSystemFilter = str()
            
        self.fileSystemFilter.setCurrentText(self._lastFileSystemFilter)
        self.fileSystemModel.setNameFilters(self._lastFileSystemFilter.split())
        
    @property
    def showFileSystemFilter(self) -> bool:
        return self._showFilesFilter
    
    @markConfigurable("FilesFilterVisible", "Qt")
    @showFileSystemFilter.setter
    def showFileSystemFilter(self, val:typing.Optional[typing.Union[bool, str, int]]=None) -> None:
        if isinstance(val, str) and val.strip().lower() == "true":
            val = True
        elif isinstance(val, int) and val > 0:
            val = True
            
        self._showFilesFilter = val is True
        
        self.filesFilterFrame.setVisible(self._showFilesFilter)
            
    @property
    def variableSearches(self) -> collections.deque:
        return self._recentVariablesList
    
    @markConfigurable("VariableSearch", "Qt")
    @variableSearches.setter
    def variableSearches(self, 
                         val:typing.Optional[typing.Union[collections.deque, list, tuple]] = None) -> None:
        if isinstance(val, (collections.deque, list, tuple)):
            self._recentVariablesList = collections.deque(val)
            #self._recentVariablesList = collections.deque(sorted((s for s in val)))
            
        else:
            self._recentVariablesList = collections.deque
            
        if len(self._recentVariablesList):
            self.varNameFilterFinderComboBox.clear()
            for item in self._recentVariablesList:
                self.varNameFilterFinderComboBox.addItem(item)
                
        self.varNameFilterFinderComboBox.setCurrentText("")
    
    @property
    def lastVariableSearch(self) -> str:
        return self._lastVariableFind
    
    @markConfigurable("LastVariableSearch", "Qt")
    @lastVariableSearch.setter
    def lastVariableSearch(self, val:typing.Optional[str]=None) -> None:
        if isinstance(val, str):
            self._lastVariableFind = val
        else:
            self._lastVariableFind = str()
            
    @property
    def commandSearches(self) -> collections.deque:
        return self._commandHistoryFinderList
    
    @markConfigurable("CommandSearch", "Qt")
    @commandSearches.setter
    def commandSearches(self, 
                        val:typing.Optional[typing.Union[collections.deque, list, tuple]] = None) -> None:
        if isinstance(val, (collections.deque, list, tuple)):
            self._commandHistoryFinderList = collections.deque(val)
            #self._commandHistoryFinderList = collections.deque(sorted((s for s in val)))
            
        else:
            self._commandHistoryFinderList = collections.deque()
            
        if len(self._commandHistoryFinderList):
            self.commandFinderComboBox.clear()
            for item in self._commandHistoryFinderList:
                self.commandFinderComboBox.addItem(item)
                
        self.commandFinderComboBox.setCurrentText("")
            
    @property
    def lastCommandSearch(self) -> str:
        return self._lastCommandFind
    
    @markConfigurable("LastCommandSearch", "Qt")
    @lastCommandSearch.setter
    def lastCommandSearch(self, val:typing.Optional[str]=None) -> None:
        if isinstance(val, str):
            self._lastCommandFind = val
        else:
            self._lastCommandFind = str()
            
    #def recentScripts(self) -> collections.deque:
    @property
    def recentScripts(self) -> list:
        return self._recentScripts
    
    # NOTE:FIXME/TODO 2022-01-30 00:05:47
    # Until I figure out a proper contents-observing traitType for Python
    # collections like list, deque, dict, I stick with Qt configable here.
    #@markConfigurable("RecentScripts", trait_notifier=True)
    @markConfigurable("RecentScripts", "Qt")
    @recentScripts.setter
    def recentScripts(self, 
                         val:typing.Optional[typing.Union[collections.deque, list, tuple]] = None) -> None:
        #print(f"ScipyenWindow.recentScripts.setter {val}")
        if isinstance(val, (collections.deque, list, tuple)):
            #self._recentScripts = collections.deque((s for s in val if os.path.isfile(s)))
            self._recentScripts = list((s for s in val if os.path.isfile(s)))
            
        else:
            self._recentScripts = list()
            #self._recentScripts = collections.deque()
            
        # NOTE:2022-01-28 23:16:57 
        # obsolete; this is added to configurable_traits at __init__, AFTER
        # WorkspaceGuiMixin (ScipyenConfigurable) initialization
        # albeit this mechanism it NOT currently used until I figure out a nice
        # way to notify changes in the contents of list, deque, dict via the 
        # DataBag & traitlets.TraitType framework.
        #
        
        #if isinstance(getattr(self, "configurable_traits", None), DataBag):
            #self.configurable_traits["RecentScripts"] = self._recentScripts
            
        self._refreshRecentScriptsMenu_()
    
    #### END   Properties
    
    #### BEGIN PyQt slots
    
    @pyqtSlot()
    def slot_launchExternalRunningIPython(self):
        self._init_ExternalIPython_(new="connection")
        
    @pyqtSlot()
    @safeWrapper
    def slot_launchExternalIPython(self):
        self._init_ExternalIPython_()
        
    @pyqtSlot()
    @safeWrapper
    def slot_launchExternalNeuronIPython(self):
        self._init_ExternalIPython_(new="neuron")
        
    @pyqtSlot()
    @safeWrapper
    def slot_launchExternalRunningIPythonNeuron(self):
        self._init_ExternalIPython_(new="neuron_ext")
        
    @pyqtSlot()
    @safeWrapper
    def slot_initQtConsole(self):
        self._init_QtConsole_()
        
        self.shell.events.register("pre_execute", self.workspaceModel.pre_execute)
        self.shell.events.register("post_execute", self.workspaceModel.post_execute)
        
        self.slot_changeDirectory(self.recentDirectories[0])
        
    #### END   PyQt slots
    
    #### BEGIN Methods
    
    def _set_recentScripts_(self, value):
        pass
    
    @safeWrapper
    def _init_ExternalIPython_(self, new:str = ""):
        """External IPython launcher.
        
        If no External IPython console instance exists, launches an instance
        of External IPytyhon console (running external kernels as separate processes).
        
        When parameter "new" is "neuron" the console initializes the NEURON python
        environment in the console.
        
        If an External IPython console instance is already running, it raises the
        external console window and, according to value of the "new" parameter 
        (see below) it may create a new tab.
        
        Parameters:
        -----------
        new : str (optional, default is "") 
            Allowed values are:
            
            "master":   creates a new tab with a client connected to a new, local, 
                        kernel process
                        
            "slave":    creates a new tab with a client connected to an existing
                        local kernel started in a separate process: this will be
                        the one running behind the currently active master tab
                        of the External IPython Console
                        
            "connection": asks for a kernel connection (json) file then creates 
                        a new tab with a client connected to the (possibly remote) 
                        kernel via the specified connection file.
                        
                        Useful to open a console (tab) connected to a remote kernel
                        e.g. started by a jupyter notebook or jupyterlab server.
                        
                        Requires a running notebook (preferred if using bokeh)
                        or jupyterlab server (themeable).
                        
            "neuron"    : creates a new tab with a client connected to a new, local, 
                        kernel process then initializes NEURON python environment.
                        
                        If no ExternalIPython console exists, launches an instance
                        of ExternalIPython console and starts NEURON.
                        
            "neuron_ext": launches neuron in an external kernel
                        Useful in combination with jupyter notebook or jupyterlab.
                        
                        Requires a running notebook (preferred if using bokeh)
                        or jupyterlab server (themeable).
                        
                        
                        
            
        """
        # TODO: 2021-01-17 11:08:38 Contemplate:
        # special case(s) of remote kernel connections where we also start the
        # remote kernel itself (e.g. jupyter notebook, jupyterlab)
        # use asynchronous approach to:
        # 1. start remote kernel
        # 2. once started, automatically import useful libraries such as bokeh etc
        # 3. make this in two flavours, one of them with NEURON environment
        from core.extipyutils_client import nrn_ipython_initialization_cmd
        from functools import partial
        #print("_init_ExternalIPython_ new", new)
        
        if not isinstance(self.external_console, consoles.ExternalIPython):
            # NOTE: 2021-01-30 13:52:58
            # there is no running ExternalIPython instance
            if isinstance(new, str) and new in ("connection", "neuron_ext"):
                connection_file, file_type = QtWidgets.QFileDialog.getOpenFileName(self,
                                                            "Connect to Existing Kernel",
                                                            jupyter_runtime_dir(),
                                                            "Connection file (*.json)")
                if not connection_file:
                    return
                
                self.external_console = consoles.ExternalIPython.launch(existing=connection_file)
                
            else:
                # NOTE: 2021-01-15 14:50:32
                # this will automatically start a (remote) IPython kernel
                self.external_console = consoles.ExternalIPython.launch()
                
            self.workspace["external_console"] = self.external_console
            self.workspaceModel.user_ns_hidden.update({"external_console":self.external_console})
            #self.external_console.window.sig_kernel_count_changed[int].connect(self._slot_remote_kernel_count_changed)
            
            # NOTE: 2021-01-15 14:46:07
            # any value of new other than "neuron" or "neuron_ext" is ignored when the console 
            # is first initiated
            if isinstance(new, str):
                if new == "neuron":
                    self.external_console.execute(nrn_ipython_initialization_cmd,
                                                silent=True,
                                                store_history=False)
                    
                elif new == "neuron_ext":
                    self.external_console.window.start_neuron_in_current_tab()

                
            self.external_console.window.sig_shell_msg_received[object].connect(self._slot_ext_krn_shell_chnl_msg_recvd)
            self.external_console.window.sig_kernel_disconnect[dict].connect(self._slot_ext_krn_disconnected)
            self.external_console.window.sig_kernel_restart[dict].connect(self._slot_ext_krn_restart)
            self.external_console.window.sig_kernel_stopped_channels[dict].connect(self._slot_ext_krn_stop)
            
        else:
            # NOTE: 2021-01-30 13:53:37
            # an instance of ExternalIPython is already running
            frontend_factory = None
            #print("\texternal console exists")
            if self.external_console.window.active_frontend is None:
                # NOTE: 2021-01-30 13:54:46
                # console instance exists but does not have an active frontend anymore
                # therefore kill the running kernel (if any and running) and start 
                # with clean slate
                if (self.external_console.kernel_manager is not None):
                    # kill the current (existing) kernel
                    try:
                        if hasattr(self.external_console.kernel_manager, "is_alive") and self.external_console.kernel_manager.is_alive():
                            self.external_console.kernel_manager.shutdown_kernel(now=True, restart=False)
                    except Exception as e:
                        traceback.print_exc()
                    
                frontend_factory = self.external_console.window.create_tab_with_new_frontend
                
                if isinstance(new, str):
                    if new == "connection":
                        # will ask for an existing kernel
                        frontend_factory = self.external_console.window.create_tab_with_existing_kernel
                        
                    elif new == "neuron":
                        frontend_factory = partial(self.external_console.window.create_tab_with_new_frontend,
                                                   code = nrn_ipython_initialization_cmd,
                                                   silent=True, store_history=False)
                        
                    elif new == "neuron_ext":
                        frontend_factory = self.external_console.window.create_tab_with_existing_kernel
                        frontend_factory = partial(self.external_console.window.create_tab_with_existing_kernel,
                                                   code = nrn_ipython_initialization_cmd,
                                                   silent = True, store_history = False)
                        
            else:
                #print("\t* active frontend exists")
                if isinstance(new, str):
                    if new == "master" or len(new.strip()) == 0:
                        frontend_factory = self.external_console.window.create_tab_with_new_frontend
                        
                    elif new == "slave":
                        frontend_factory = self.external_console.window.create_tab_with_current_kernel
                        
                    elif new == "connection":
                        frontend_factory = self.external_console.window.create_tab_with_existing_kernel
                        
                    elif new == "neuron":
                        frontend_factory = partial(self.external_console.window.create_tab_with_new_frontend,
                                                   code=nrn_ipython_initialization_cmd,
                                                   silent=True, store_history=False)
                        
                    elif new == "neuron_ext":
                        frontend_factory = partial(self.external_console.window.create_tab_with_existing_kernel,
                                                   code = nrn_ipython_initialization_cmd,
                                                   silent=True, store_history=False)

            if frontend_factory is not None:
                if frontend_factory():
                    self.external_console.window.setVisible(True)
                    if isinstance(new, str) and str == "neuron_ext":
                        self.external_console.window.start_neuron_in_current_tab()

    #### END   Methods
    
        
    @safeWrapper
    def _init_QtConsole_(self):
        """Starts an interactive IPython shell with a QtConsole frontend.
        
        The shell runs an embedded ("InProcess") IPython kernel with an event 
        loop run by the Scipyen QApplication instance (PyQt5).
        
        The shell's namespace becomes the user's workspace where the user data
        is temporarily assigned to symbols, and its contents are listed
        in the "User Variables" tab. 
        
        The user data consists of objects that are either loaded from files, 
        generated from statements typed at the command line (in the shell) or by
        code run via the GUI (under certain circumstances), and modules loaded
        manually by the user via 'import' statements.
        
        In addition, the user's workspace contains 'hidden' data: objects and
        modules that were, respectively, created and imported during Scipyen
        startup, plus volatile variables (symbols starting with underscore). 
        These are 'hidden' from the workspace viewer ('User Variables' tab) but
        can be revealed witht h e 'dir()' command in the shell.
        
        Scipyen's main window can be accessed from the shell directly as 
        "mainWindow".
        
        NOTE: Important objects in the user workspace:
        The workspace also contains the following objects:
        
        Symbol      Reference (is bound) to:                    Other references
        ========================================================================
        mainWindow  Scipyen main application window
        
        console     The console window                          mainWindow.console
        
        shell       The interactive IPython shell               mainWindow.shell
        
        ipkernel    The InProcess kernel backend of the shell   mainWindow.ipkernel
        kernel      alias to ipkernel
        
        scipyen_settings
                    The confuse.LazyConfig object with custom
                    non-gui configuration for Scipyen saved in
                    'config_dir'/config.yaml.
                    On machines runninx Linux, 'config_dir' is
                    $HOME/.config/Scipyen
                    
        scipyen_topdir
                    The top directory tree if scipyen.
                    By default this is the same as the directory of the package
                    default configuration file ("config_default.yaml").
                    
                    If this file does not exist, or is empty, then this is the 
                    parent directory of the one containing the mainwindow module.
                    
                    NOTE: this can also be displayed by the line magics
                        %appdir and %scipyendir
        
        
        
        The console, the shell and the kernel are accessbile directly from the 
        command line as the "console", "shell" and "ipkernel" symbols, and as 
        Scipyen's main window attributes with the same names ("mainWindow.shell",
        "mainWindow.console" and "mainwindow.ipkernel").
        
        
        . These are
        references to the console,
        
        The shell and the kernel are bound, respetively to the "shell" and 
        "ipkernel" attributes of Scipyen's main window ("mainWindow" object in 
        the shell's namespace). 
        
        The Scipyen's user workspace is the same as the shell's namespace
        (self.ipkernel.shell.user_ns)
        The shell namespace is the same as the user's workspace.
        """

        # creates a Qt console with an embedded ipython kernel
        # i.e. a QtInProcessKernelManager
        #
        # NOTE: 2018-10-08 10:48:46
        # the code inside pict is executed in its own QApplication loop
        # whereas code entered in this console is executed in the ipython kernel
        # which therefore has to be "embedded" in the QApplication
        
        # At any time there can be only ONE master event loop,
        #
        # In this case, that's the QApplication event loop (PyQt5)
        
        
        # Also, all free (user) variables are stored in this kernel's namespace
        # which is also referenced as instance variable 'self.workspace' of ScipyenWindow
        
        # The ipython kernel itself is referenced as the instance variable
        # self.ipkernel
        
        # Furthermore, the console "shell"  is accessible as self.ipkernel.shell
        # aliased ot the instance variable self.shell
        #
        # Its user namespase (user_ns) is referenced as self.workspace (see below)
        
        # For convenience, the ipkernel, console and the shell are also aliased 
        # into the workspace
        
        # NOTE: 2018-10-08 10:48:53
        # About self.console.execute(...) vs self.shell.run_cell(...):
        #
        # Both will generate pre_execute and post_execute IPython events, HOWEVER:
        #
        # * console.execute(str) always executes the expression in str inside the 
        #   console's shell/kernel; code will be echoed to the console UNLESS
        #   the hidden=True is also passed after the str parameter
        #
        # * shell.run_cell(str) does the same as console.execute with hidden=False
        #   (the extression in str is always echoed; there is no "hidden" parameter
        #   to run_cell(...))
        
        if not isinstance(self.console, consoles.ScipyenConsole):
            self.console = consoles.ScipyenConsole(parent=self)
            self.console.executed.connect(self.slot_updateHistory)
            self.console.executed.connect(self.slot_updateCwd)
            
            self.ipkernel = self.console.consoleWidget.ipkernel
            self.shell = self.ipkernel.shell
        
            self.executionCount = self.ipkernel.shell.execution_count # this is always 1 immediately after initialization

            self.historyAccessor = HistoryAccessor() # access history database independently of the shell
                                                    # should not interfere with the history 


            # NOTE: 2019-08-03 17:03:03
            # populate the command history widget
            hist = self.historyAccessor.search('*')

            sessionNo = None
            
            items = list()

            for session, line, inline in hist:
                if sessionNo is None or sessionNo != session:
                    sessionNo = session  #cache the session
                    sessionItem = QtWidgets.QTreeWidgetItem(self.historyTreeWidget, [repr(sessionNo)])
                    items.append(sessionItem)

                lineItem = QtWidgets.QTreeWidgetItem(sessionItem, [repr(line), inline])
                items.append(lineItem)

            self.currentSessionTreeWidgetItem = QtWidgets.QTreeWidgetItem(self.historyTreeWidget, ["Current"])
            
            items.append(self.currentSessionTreeWidgetItem)
            
            #NOTE: 2017-03-21 22:55:57 much better!
            # connect signals emitted by the console when processing a drop event
            self.console.historyItemsDropped.connect(self.slot_pasteHistorySelection) 
            self.console.workspaceItemsDropped.connect(self.slot_pasteWorkspaceSelection)
            self.console.loadUrls[object, bool, QtCore.QPoint].connect(self.slot_loadDroppedURLs)
            self.console.pythonFileReceived[str, QtCore.QPoint].connect(self.slot_handlePythonTextFile)

            self.historyTreeWidget.insertTopLevelItems(0, items)
            self.historyTreeWidget.scrollToItem(self.currentSessionTreeWidgetItem)
            self.historyTreeWidget.setCurrentItem(self.currentSessionTreeWidgetItem)

            #NOTE: until input has been enetered at the console, this is the LAST session on record NOT the current one!
            self.currentSessionID = self.historyAccessor.get_last_session_id()
            
            self.selectedSessionID = None

            # ------------------------------
            # set up a` COMMON workspace
            # ------------------------------
            #
            # NOTE: 2016-03-20 14:29:16
            # populate kernel namespace with the imports from this current module 
            #
            # this effectively is the second time they're being imported, but this time
            # in the ipkernel environment
            # __module_file_name__ is "pict" so we take all its contents into the kernel
            # namespace (they're just references to those objects)
            self.workspace = self.ipkernel.shell.user_ns
            
            # NOTE: 2020-11-12 12:51:36
            # used by %scipyen_debug line magic
            self.workspace["SCIPYEN_DEBUG"] = False 
            
            self.workspace['mainWindow'] = self
            #self.workspace["scipyenDefaultSettings"] = self.scipyenDefaultSettings

            # NOTE: 2016-03-20 20:50:42 -- WRONG!
            # get_ipython() returns an instance of the interactive shell, NOT the kernel
            self.workspace['ipkernel'] = self.ipkernel
            self.workspace['kernel'] = self.ipkernel
            self.workspace['console'] = self.console # useful for testing functionality; remove upon release
            self.workspace["shell"] = self.shell # alias to self.ipkernel.shell
            self.workspace["scipyen_settings"] = self._scipyen_settings_
            self.workspace["scipyen_user_settings"] = self._user_settings_src_
            self.workspace["scipyen_user_settings_file"] = self._user_settings_file_
            self.workspace["scipyen_topdir"] = self._scipyendir_
            self.workspace["external_console"] = self.external_console
            
            #print("exit" in self.ipkernel.shell.user_ns)
            
            # NOTE 2020-07-09 11:36:34
            # Override ExitAutocall objects in this kernel in order to let the 
            # ScipyenMagics "exit" and "quit" to take over.
            # By default, self.workspace["exit"] and self.workspace["quit"] are
            # the same ExitAutocall object; see IPython.core.autocall module for 
            # details
            #
            # The point of all this is that we quit the Scipyen application when
            # either "exit" or "quit" are entered in the internal Scipyen Console
            #
            self.workspace["_exit_kernel_"] = self.workspace["exit"]
            self.workspace.pop("exit", None)
            self.workspace["_quit_kernel_"] = self.workspace["quit"]
            self.workspace.pop("quit", None)
            
            for method in self._export_methods_:
                func = getattr(self, method[0], None)
                name = method[1]
                if func is not None:
                    self.workspace[name] = func
            
            # TODO/FIXME 2019-08-04 11:06:16
            # this does not override ipython's exit: 
            # this will have to be called as %exit line magic (i.e. automagic doesn't work)
            self.ipkernel.shell.register_magics(ScipyenMagics) 
            
            # NOTE: 2020-11-29 15:57:08
            # this imports current module in the user workspace as well
            
            impcmd = ' '.join(['from', "".join(["gui.", __module_file_name__]), 'import *'])
            
            self.ipkernel.shell.run_cell(impcmd)
            
            self.ipkernel.shell.run_cell("h5py.enable_ipython_completer()")
            #if has_hdf5:
                #self.ipkernel.shell.run_cell("h5py.enable_ipython_completer()")
            
            # hide the variables added to the workspace so far (e.g., ipkernel,
            # console, shell, and imported modules) so that they don't show in 
            # the workspace browser (the tree view in the User variables pane)
            # ATTENTION but there is a catch: this does NOT prevent the user from
            # assigning a variable to a symbol bound to one of these variables
            # -- effectively "overwriting" them.
            
            self._nonInteractiveVars_.update([i for i in self.workspace.items()])

            # --------------------------
            # finally, customize console window title and show it
            # -------------------------
            self.console.setWindowTitle(u'Scipyen Console')

        self.console.show()
        # NOTE: 2021-10-18 11:28:25
        # The following must be called when console has bocome visible!
        self.console.consoleWidget.set_pygment(self.console.consoleWidget._console_pygment) 
        
    # NOTE: 2016-03-20 21:18:32
    # to run code inside the console and use the console as stdout, 
    # call console.execute(...)
    #
    # calling console.ipkernel.shell.run_cell(...) uses the system stdio
    # 
    #
    # FIXME -- why does it appear to execute only ONE print command?
    @pyqtSlot()
    @safeWrapper
    def _helpOnConsole_(self):
        self.console.execute("console_info()")
        
    @pyqtSlot()
    def slot_refreshView(self):
        if self.activeDockWidget is self.dockWidgetFileSystem:
            #self.slot_updateCwd()
            self._updateFileSystemView_(self.currentDir, False)
        elif self.activeDockWidget is self.dockWidgetHistory:
            if self.console is not None and self.ipkernel.shell.execution_count > self.executionCount: # only update history if something has indeed been executed
                self.executionCount = self.ipkernel.shell.execution_count
                self._updateHistoryView_(self.executionCount-1, self.console.consoleWidget.history_tail(1)[0])
        else:
            self.workspaceModel.update()
    
    # NOTE: 2016-03-26 17:07:17
    # as a workaround for the problem in NOTE: 2016-03-26 17:01:32
    @pyqtSlot()
    @safeWrapper
    def slot_updateWorkspaceView(self):
        self._sortWorkspaceViewFirstColumn_()
        self._resizeWorkspaceViewFirstColumn_()
        
    @pyqtSlot()
    def slot_updateWorkspaceModel(self):
        """ pyplot commands may produce or close a figure; we need to reflect this!
        """
        # NOTE: 2019-11-20 12:22:17
        # self.workspaceModel.update() triggers the signal
        # WorkspaceModel.modelContentsChanged which is connected to the slot
        # self.slot_updateWorkspaceView(); in turn this will sort column 0
        # and resize its contents. 
        # This is because workspaceModel doesn't "know" anything about workspaceView.
        self.workspaceModel.update() # emits WorkspaceModel.modelContentsChanged via var_observer
        
    @pyqtSlot()
    def slot_updateCwd(self):
        if self.cwd != os.getcwd():
            self.cwd = os.getcwd()
            self._setRecentDirectory_(self.cwd)
            self._updateFileSystemView_(self.cwd, False)
            #self.fileSystemTreeView.scrollTo(self.fileSystemModel.index(self.cwd))
            #self.fileSystemTreeView.setCurrentIndex(self.fileSystemModel.index(self.cwd))
            self._resizeFileColumn_()
            self._refreshRecentDirsComboBox_()
            
    def slot_updateHistory(self):
        """ Slot to update the history tree widget once a command has been entered at the console
        This occurs only for the current session
        """
        #NOTE: 2017-03-19 21:26:37 self.console.history_tail stores only the 
        #NOTE: command line input to the console (interactive input)
        #NOTE: so it's OK to connect this to console's executed slot
        #NOTE: however pressing ENTER (and thus firing the executed signal)
        #NOTE: will only generate an empty string; in this case, the console's
        #NOTE: history_tail will how historic commands because nothing is appended
        #NOTE: to it -- we therefore must check that (1) the execution count is > 1
        #NOTE: and that is has been updated after the last ENTER press
        #print("execution count in slot_updateHistory: ", self.ipkernel.shell.execution_count)
        
        if self.console is not None and self.ipkernel.shell.execution_count > self.executionCount: # only update history if something has indeed been executed
            self.executionCount = self.ipkernel.shell.execution_count
            self._updateHistoryView_(self.executionCount-1, self.console.consoleWidget.history_tail(1)[0])
            #self._updateHistoryView_(self.executionCount-1, self.console.history_tail(1)[0])

    def _updateHistoryView_(self, lineno, val):
        mustUpdateSessionID = self.currentSessionTreeWidgetItem.childCount() == 0

        item = QtWidgets.QTreeWidgetItem(self.currentSessionTreeWidgetItem, [repr(lineno), val])

        self.historyTreeWidget.addTopLevelItem(item)
        self.historyTreeWidget.scrollToItem(item)
        self.historyTreeWidget.setCurrentItem(item)
        
        if mustUpdateSessionID:
            self.currentSessionID = self.historyAccessor.get_last_session_id()

    # NOTE: 2016-03-25 09:43:58
    # inspired from stock IPython/core/magic/namespaces.py
    #@classmethod
    def _listWorkspaceVars_(self, param_s=None):
        '''Prepares a list of variable names to be displayed in the workspace widget.
        The optional param_s argument is a str containing space-separated type names
        to indicate what variable type(s) should be displayed.
        DEPRECATED - functionality taken over by workspacemodel module
        
        '''
        # NOTE: 2017-08-24 15:50:46
        # special case when "_" variables are matplotlib.figure.Figure instances
        # created with plt commands (functions) but NOT assigned to unbound variables
        # I'm relying on pyplot's own figure manager: no two figures can have the same number
        hidden_mpl_figure_names = [i for i in self.workspace.keys() if i.startswith("_") and isinstance(self.workspace[i], mpl.figure.Figure)]
        
        #print(hidden_mpl_figure_names)
            
        if len(hidden_mpl_figure_names) > 0:
            for n in hidden_mpl_figure_names:
                if hasattr(self.workspace[n], "number"):
                    newVarName = "Figure%d" % (self.workspace[n].number)
                else:
                    p = self.workspace[n].canvas.parent()
                    parents=list()
                    while p is not None:
                        parents.append(p)
                        p = p.parent()

                    wtitle = parents[-1].windowTitle()
                    
                    if wtitle is None or len(wtitle) == 0:
                        suffix = n
                    else:
                        suffix = "_%s" % wtitle
                    
                    newVarName = "figure%s" % suffix
                
                self.workspace[newVarName] = self.workspace[n]
                self.workspace.pop(n, None)
                
                #cmd = "".join([newVarName, "=", n, "; del(", n, ")"])
                #self.console.execute(cmd, hidden=True)


        varnames = [i for i in self.workspace 
               if (not i.startswith('_') and i not in self._nonInteractiveVars_.keys() and type(i) is not types.ModuleType)]


        # NOTE: 2016-04-16 00:12:26
        # why does the above NOT prevent the display of a module created at the console 
        # (e.g. after a call like m = types.ModuleType(), m is listed there, when
        # it really shouldn't)

        #if not varnames:
            #return None

        if len(varnames) > 0 and param_s is not None:
            typelist = param_s.split()
            if typelist:
                typeset = set(typelist)
                varnames = [i for i in varnames if type(self.workspace[i]).__name__ in typeset]

        #if not varnames:
            #return None

        return varnames
    
    def removeFromWorkspace(self, value:typing.Any, by_name:bool=True, update:bool=True) -> None:
        """Removes an object from the workspace via GUI operations.
        
        By default, the object to be removed is specified by the symbol (name)
        to which the object is bound in the workspace. 

        However, this function also allows the direct removal of an object's
        references that exist in the workspace (NOTE that the object may still
        exist outside the workspace).
        
        Parameters:
        ----------
        value: any type.
            Typically (when 'by_name' is True, see below) this is the str symbol, 
            in the workspace, to which the object is bound
            
        Named parametsrs:
        ----------------
        by_name: bool, optional; default is True
            Used when value is a str, to indicate that it represents the symbol
            of the object to be removed from in the workspace.
            
            This is the typical (and expected) usage.
            
            When False, 'value' is an object which has at least one reference in
            in the workspace, bound to some identifiable symbol there, or a 
            reference to an object in the workspace.
            
        update: bool, optional; default is True;
            When True, the workspace viewer will be updated immediately after the
            successful removel of the variable.
            
            When False, the workspace viewer update will be deferred until the 
            update() method of the workspace model is called explicitly. This
            allows batch removal of several variables without potentially
            expensive updates of the workspace viewer after each variable.
            
        """
        if isinstance(value, str) and by_name:
            #print(f"---\nScipyenWindow.removeFromWorkspace {value}")
            self.workspace.pop(value, None)
            
        else:
            # inverse lookup the key mapped to this value - will remove ALL
            # references to value that exist in the workspace
            objects = [(name, obj) for (name, obj) in self.workspace.items() if obj is value]
            if len(objects):
                for o in objects:
                    self.workspace.pop(o[0], None)
                    
        if update:
            self.workspaceModel.update()
        
        self.workspaceModel.currentItem = None
        
    @safeWrapper
    def getCurrentVarName(self):
        signalBlockers = [QtCore.QSignalBlocker(self.workspaceView),
                          QtCore.QSignalBlocker(self.workspaceModel),
                          QtCore.QSignalBlocker(self.workspaceView.selectionModel())]
        
        varname = self.workspaceModel.currentItemName
        
        if varname is None:
            indexList = self.workspaceView.selectedIndexes()
            
            #if len(indexList) == 0:
            if len(indexList) != 1:
                return
            
            varname = self.workspaceModel.item(indexList[0].row(),0).text()
            
            if varname is None or isinstance(varname, str) and len(varname.strip()) == 0:
                return
            
            if varname not in self.workspace.keys():
                return
            
        #print("MainWindow.getCurrentVarName", varname)
        
        return varname

    def assignToWorkspace(self, name:str, val:object, from_console:bool = False):
        self.workspace[name] = val
        self.workspaceModel.update()
        
    @pyqtSlot()
    @safeWrapper
    def slot_newViewer(self):
        """Slot for opening a list of viewer types (no used)
        """
        viewer_type_names = [v.__name__ for v in gui_viewers]
        dlg = pgui.ItemsListDialog(parent=self, itemsList=viewer_type_names,
                                   title="Viewer type", modal=True)
        
        if dlg.exec() == 1:
            seltxt = dlg.selectedItemsText
            if len(seltxt) == 0:
                return
            
            selected_viewer_type_name = seltxt[0]
            
            win = self._newViewer(selected_viewer_type_name)# , name=win_name)
            
    @pyqtSlot()
    @safeWrapper
    def slot_newViewerMenuAction(self):
        """Slot for creating new viewer directly from Windows/Create New menu
        """
        win = self._newViewer(self.sender().text()) # inherited: WindowManager._newViewer
        
    @pyqtSlot(QtCore.QPoint)
    @safeWrapper
    def slot_historyContextMenuRequest(self, point):
        cm = QtWidgets.QMenu("Selected history", self)
        copyHistorySelection = cm.addAction("Copy")
        copyHistorySelection.setToolTip("Copy selected history to clipboard")
        copyHistorySelection.triggered.connect(self._copyHistorySelection_)
        cm.popup(self.historyTreeWidget.mapToGlobal(point), copyHistorySelection)
        saveHistorySelection = cm.addAction("Save...")
        saveHistorySelection.setToolTip("Save selected history to file")
        saveHistorySelection.triggered.connect(self._saveHistorySelection_)
        
    @pyqtSlot()
    @safeWrapper
    def slot_launchTest(self):
        pass
        #from ephys.membrane import analyse_AP_depol_series
        
        #varname = self.getCurrentVarName()
        
        #if varname is None:
            #return
        
        #data = self.workspace[varname]
        
        #if isinstance(data, neo.Block):
            #args = (data,)
            #kwargs = dict()
            #self._run_loop_process_(analyse_AP_depol_series, None, *args, **kwargs)
    
    @pyqtSlot()
    @safeWrapper
    def slot_launchCaTAnalysis(self):
        lscatWindow = self._newViewer(CaTanalysis.LSCaTWindow, parent=self, win_title="LSCaT")
        #lscatWindow = CaTanalysis.LSCaTWindow(parent=self, win_title="LSCaT")
        lscatWindow.show()
        
    def _getHistoryBlockAsCommand_(self, magic=None):
        cmd = ""
        selectedItems = self.historyTreeWidget.selectedItems()
        
        if magic is None:
            selectionList = []
        else:
            selectionList = [magic]
            
        if len(selectedItems) == 0:
            return cmd
        
        #### BEGIN do not delete -- revisit this
        if len(selectedItems) == 1:
            if selectedItems[0].parent() is None: # a session node was selected
                if selectedItems[0].text(0) == "Current":
                    sessionNo = self.currentSessionID
                    
                else:
                    sessionNo = int(selectedItems[0].text(0))
                    
                # when a "Node" is selected, get the entire list of selected children
                selectionList += [selectedItems[0].child(k).text(1) for k in range(selectedItems[0].childCount())]
                
            elif selectedItems[0].columnCount() > 1:     #  a command node was selected
                                                         #  check-out its parent session number
                if isinstance(selectedItems[0].parent(), QtWidgets.QTreeWidgetItem)\
                    and selectedItems[0].parent().text(0) == "Current":
                    sessionNo = self.currentSessionID
                    
                else:
                    sessionNo = int(selectedItems[0].parent().text(0))
                    
                selectionList.append(selectedItems[0].text(1))
                    
            else: # not sure we'll ever reach this
                return
            
            self.selectedSessionID = sessionNo
                    
        else:
            # allow for items to be selected disjoint from their sessions
            # when selection crosses sessions
            
            # but leave selectedSessionID unchanged
            self.selectedSessionID = self.currentSessionID
            
            for item in selectedItems:
                parent = item.parent()

                if parent is None:              # this is a session item
                    continue                    # move on to the next

                ptxt = parent.text(0)           # and its parent is a session item
                
                if ptxt != "Current":           # in fact a historic session item 
                    sessionNo = int(ptxt)       # so get its session number
                    
                else:
                    sessionNo = self.currentSessionID # make sure we get back to the curent session ID

                lineNo = int(item.text(0))

                if magic is None:
                    selectionList.append(item.text(1)) # append the command itself
                    #cmd = "\n".join(selectionList) + "\n"
                    
                else:
                    if sessionNo != self.currentSessionID:
                        selectionList.append("%s/%s" % (sessionNo, repr(lineNo)))
                    else:
                        selectionList.append(repr(lineNo))
                        
                    #cmd = " ".join(selectionList) + "\n"
                    
        if magic is None:
            cmd = "\n".join(selectionList) + "\n"
            
        else:
            cmd = " ".join(selectionList) + "\n"
            
        #### END
            #sessionNo = self.currentSessionID


        #for item in selectedItems:
            #parent = item.parent()

            #if parent is None:              # this is a session item
                #continue                    # move on to the next

            #ptxt = parent.text(0)           # and its parent is a session item
            
            #if ptxt != "Current":           # in fact a historic session item 
                #sessionNo = int(ptxt)       # so get its session number
            #else:
                #sessionNo = self.currentSessionID # make sure we get back to the curent session ID

            #lineNo = int(item.text(0))

            #if magic is None:
                #selectionList.append(item.text(1)) # append the command itself
                #cmd = "\n".join(selectionList) + "\n"
            #else:
                #if sessionNo != self.currentSessionID:
                    #selectionList.append("%s/%s" % (sessionNo, repr(lineNo)))
                #else:
                    #selectionList.append(repr(lineNo))
                #cmd = " ".join(selectionList) + "\n"
            
        #print(cmd)
        return cmd
    
    def _copyHistorySelection_(self):
        cmd = self._getHistoryBlockAsCommand_()
        #print(cmd)
        if isinstance(cmd, str) and len(cmd.strip()):
            self.app.clipboard().setText(cmd+"\n")
            
        else:
            self.app.clipboard().clear() # don't leave gremlins
            
    def _saveHistorySelection_(self):
        cmd = self._getHistoryBlockAsCommand_()
        
        if isinstance(cmd, str) and len(cmd.strip()):
            fn, _ = self.chooseFile(caption = "Save selected history to file",
                                    save=True,
                                    fileFilter="Python source code (*.py);;Text Files (*.txt);;All files (*.*)")
            if len(fn.strip()):
                pio.saveText(cmd+"\n", fn)
                #with open(fn, mode="wt") as destfile:
                    
                    
        
    @pyqtSlot(QtCore.QModelIndex)
    @safeWrapper
    def slot_variableItemPressed(self, ndx):
        #print("ScipyenWindow.slot_variableItemPressed %s", ndx)
        self.workspaceModel.currentItem = self.workspaceModel.item(ndx.row(),0)
        self.workspaceModel.currentItemName = self.workspaceModel.item(ndx.row(),0).text()
        item = self.workspace[self.workspaceModel.currentItemName]
        if isinstance(item, (scipyenviewer.ScipyenViewer, mpl.figure.Figure)):
            self._setCurrentWindow(item)
    
    @pyqtSlot(QtCore.QModelIndex)
    @safeWrapper
    def slot_variableItemActivated(self, ndx):
        """Called by double-click of left mouse button on item in workspace
        """
        source_ns = self.workspaceModel.item(ndx.row(), standard_obj_summary_headers.index("Workspace")).text()
        
        if source_ns != "Internal": # avoid standard menu for data in remote kernels
            #TODO separate menu for variables in remote namespaces
            return
        
        self.workspaceModel.currentItem = self.workspaceModel.item(ndx.row(),0)
        self.workspaceModel.currentItemName = self.workspaceModel.item(ndx.row(),0).text()
        
        item = self.workspace[self.workspaceModel.currentItemName]
        
        if QtWidgets.QWidget in inspect.getmro(type(item)):
            item.show()
        
        if isinstance(item, (scipyenviewer.ScipyenViewer, mpl.figure.Figure)):
            self._raiseWindow(item)
            
        else:
            newWindow = bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier)
            
            if not self.viewVar(self.workspaceModel.currentItemName, newWindow=newWindow):
                # view (display) object in console is no handler exists
                self.console.execute(self.workspaceModel.currentItemName)
                
    @safeWrapper
    def _genExternalVarContextMenu(self, indexList, cm):
        if not cm.isEmpty():
            cm.addSeparator()
        copyVarToInternal = cm.addAction("Copy to Internal Workspace")
        copyVarToInternal.setToolTip("Copies selected variable to the internal user workspace.\nCAUTION: Existing variables with the same name will be overwritten")
        copyVarToInternal.setStatusTip("Copies selected variable to the internal user workspace.\nCAUTION: Existing variables with the same name will be overwritten")
        copyVarToInternal.setWhatsThis("Copies selected variable to the internal user workspace.\nCAUTION: Existing variables with the same name will be overwritten")
        copyVarToInternal.triggered.connect(self._slot_copyFromExternalWS)
                
    @safeWrapper
    def _genInternalVarContextMenu(self, indexList, cm):
        if not cm.isEmpty():
            cm.addSeparator()
            
        copyVarNames = cm.addAction("Copy name(s)")
        copyVarNames.setToolTip("Copy variable names to clipboard.\nPress SHIFT to quote the names; press CTRL to have one name per line")
        copyVarNames.setStatusTip("Copy variable names to clipboard.\nPress SHIFT to quote the names; press CTRL to have one name per line")
        copyVarNames.setWhatsThis("Copy variable names to clipboard.\nPress SHIFT to quote the names; press CTRL to have one name per line")
        copyVarNames.triggered.connect(self.slot_copyWorkspaceSelection)
        copyVarNames.hovered.connect(self._slot_showActionStatusMessage_)
    
        varNamesToConsole = cm.addAction("Send name(s) to console")
        varNamesToConsole.setToolTip("Copy & paste variable names directly to console.\nPress SHIFT to quote the names; press CTRL to have one name per line")
        varNamesToConsole.setStatusTip("Copy & paste variable names directly to console.\nPress SHIFT to quote the names; press CTRL to have one name per line")
        varNamesToConsole.setWhatsThis("Copy & paste variable names directly to console.\nPress SHIFT to quote the names; press CTRL to have one name per line")
        varNamesToConsole.triggered.connect(self.slot_pasteWorkspaceSelection)
        varNamesToConsole.hovered.connect(self._slot_showActionStatusMessage_)
        
        if len(indexList) == 1:
            # one variable selected
            renameVar = cm.addAction("Rename")
            renameVar.setToolTip("Rename variable")
            renameVar.setStatusTip("Rename variable")
            renameVar.setWhatsThis("Rename variable")
            renameVar.triggered.connect(self.slot_renameWorkspaceVar)
            renameVar.hovered.connect(self._slot_showActionStatusMessage_)

            varName = self.workspaceModel.item(indexList[0].row(),0).text()
            
            varType = type(self.workspace[varName])
            
            actionNames = VTH.get_actionNames(varType)
            
            if actionNames is None:
                return
            
            #cm.addSeparator()
            
            specialViewMenu = cm.addMenu("View")
            
            if QtWidgets.QWidget in inspect.getmro(varType):
                action = specialViewMenu.addAction("Show")
                action.triggered.connect(self.workspace[varName].show)
                
            else:
                for actionName in VTH.get_actionNames(varType):
                    action = specialViewMenu.addAction(actionName)
                    action.triggered.connect(self.slot_autoSelectViewer)
                
        else:
            # several variables selected
            viewVars = cm.addAction("View")
            viewVars.triggered.connect(self.slot_viewSelectedVariables) # always goes to new window
            viewVars.setToolTip("Show variables in default viewer windows")
            viewVars.setStatusTip("Show variables in default viewer windows")
            viewVars.setWhatsThis("Show variables in default viewer windows")
            viewVars.hovered.connect(self._slot_showActionStatusMessage_)
            
        viewInConsoleAction = cm.addAction("Display in console")
        viewInConsoleAction.setToolTip("Display variable(s) in console")
        viewInConsoleAction.setStatusTip("Display variable(s) in console")
        viewInConsoleAction.setWhatsThis("Display variable(s) in console")
        viewInConsoleAction.triggered.connect(self.slot_consoleDisplaySelectedVariables)
        viewInConsoleAction.hovered.connect(self._slot_showActionStatusMessage_)
        
        cm.addSeparator()
        
        varnames = [self.workspaceModel.item(indexList[k].row(),0).text() for k in range(len(indexList))]
        
        if all([isinstance(self.workspace[v], (pd.DataFrame, pd.Series, neo.basesignal.BaseSignal, neo.SpikeTrain, np.ndarray))] for v in varnames):
            if not any([isinstance(self.workspace[v], np.ndarray) and self.workspace[v].ndim > 2 for v in varnames]):
                exportCSVAction = cm.addAction("Export selected variables to CSV")
                exportCSVAction.triggered.connect(self.slot_multiExportToCsv)
                exportCSVAction.setToolTip("Export variables as separate comma-separated ASCII files")
                exportCSVAction.setStatusTip("Export variables as comma-separated ASCII file")
                exportCSVAction.setWhatsThis("Export variables as comma-separated ASCII file")
                exportCSVAction.hovered.connect(self._slot_showActionStatusMessage_)

        saveVars = cm.addAction("Save as HDF5")
        saveVars.setToolTip("Save selected variables as HDF5 files")
        saveVars.setStatusTip("Save selected variables as HDF5 files")
        saveVars.setWhatsThis("Save selected variables as HDF5 files")
        saveVars.triggered.connect(self.slot_saveSelectedVariables)
        saveVars.hovered.connect(self._slot_showActionStatusMessage_)
        
        pickleVars = cm.addAction("Save as Pickle")
        pickleVars.setToolTip("Save selected variables as Pickle files")
        pickleVars.setStatusTip("Save selected variables as Pickle files")
        pickleVars.setWhatsThis("Save selected variables as Pickle files")
        pickleVars.triggered.connect(self.slot_pickleSelectedVariables)
        pickleVars.hovered.connect(self._slot_showActionStatusMessage_)
        
        delVars = cm.addAction("Delete")
        delVars.setToolTip("Delete selected variables")
        delVars.setStatusTip("Delete selected variables")
        delVars.setWhatsThis("Delete selected variables")
        delVars.triggered.connect(self.slot_deleteSelectedVars)
        delVars.hovered.connect(self._slot_showActionStatusMessage_)
        
        if len(self.workspaceModel.foreign_namespaces) > 0 and self.external_console is not None:
            ns = self.external_console.window.find_tab_title(self.external_console.window.active_frontend)
            cm.addSeparator()
            copyVarToActiveExternalNamespace = cm.addAction("Copy to %s namespace" % ns)
            copyVarToActiveExternalNamespace.setToolTip("Copies selected variable to the namespace of the active external kernel namespace (currently %s)" % ns)
            copyVarToActiveExternalNamespace.setStatusTip("Copies selected variable to the namespace of the active external kernel namespace (currently %s)" % ns)
            copyVarToActiveExternalNamespace.setWhatsThis("Copies selected variable to the namespace of the active external kernel namespace (currently %s)" % ns)
            copyVarToActiveExternalNamespace.triggered.connect(self._slot_copyToExternalWS)
        
    @pyqtSlot("QPoint")
    @safeWrapper
    def slot_workspaceViewContextMenuRequest(self, point):
        """
        Contex menu requested by workspace viewer
        """
        indexList = self.workspaceView.selectedIndexes()
        
        if len(indexList) == 0:
            return
        
        internal_var_indices = [ndx for ndx in indexList \
            if self.workspaceModel.item(ndx.row(), standard_obj_summary_headers.index("Workspace")).text() == "Internal"]
        
        external_var_indices = [ndx for ndx in indexList if ndx not in internal_var_indices]
            
        cm = QtWidgets.QMenu("Selected variables", self)
        cm.setToolTipsVisible(True)
        
        if len(internal_var_indices):
            self._genInternalVarContextMenu(internal_var_indices, cm)
            
        if len(external_var_indices):
            self._genExternalVarContextMenu(external_var_indices, cm)
        
        cm.popup(self.workspaceView.mapToGlobal(point))#, copyVarNames)
        #cm.popup(self.workspaceView.mapToGlobal(point), cm.actions()[0])
        
    @pyqtSlot(QtCore.QItemSelection, QtCore.QItemSelection)
    @safeWrapper
    def slot_selectionChanged(self, selected, deselected):
        """Selection change in the workspace viewer
        """
        if not selected.isEmpty():
            modelIndex = selected.indexes()[0]
            
            source_ns = self.workspaceModel.item(modelIndex.row(), standard_obj_summary_headers.index("Workspace")).text()
            if source_ns != "Internal": # avoid standard menu for data in remote kernels
                #TODO separate menu for variables in remote namespaces
                return

            if modelIndex.column()==0:
                self.workspaceModel.currentItem = self.workspaceModel.itemFromIndex(modelIndex)
                self.workspaceModel.currentItemName = self.workspaceModel.itemFromIndex(modelIndex).text()
                
            else:
                row = modelIndex.row()
                self.workspaceModel.currentItem = self.workspaceModel.item(row,0)
                self.workspaceModel.currentItemName = self.workspaceModel.item(row,0).text()
                
            item = self.workspace[self.workspaceModel.currentItemName]
            
        else:
            self.workspaceModel.currentItemName = ""
            self.workspaceModel.currentItem = None
            self.workspaceModel.itemChanged.connect(self.slot_variableItemNameChanged)

        #print("ScipyenWindow slot_selectionChanged: currentVarName %s" % self.workspaceModel.currentItemName)

    @pyqtSlot("QStandardItem*")
    @safeWrapper
    def slot_variableItemNameChanged(self, item):
        """Called when itemChanged was emitted by workspaceModel.
        
        Typically this is called after a variable has been renamed following an
        "Edit" key press (which on Unix/KDE and Windows is usually "F2").
        
        For the case when the variable name is changed via its context menu see 
        slot_renameWorkspaceVar().
        
        CAUTION: this is also called when variables are re-created!
        
        """
        signalBlockers = [QtCore.QSignalBlocker(self.workspaceView),
                          QtCore.QSignalBlocker(self.workspaceModel),
                          QtCore.QSignalBlocker(self.workspaceView.selectionModel())]
        
        if item.column() > 0:
            # only accept changes in the first (0th) column which contains
            # the variable name
            return
        
        originalVarName = self.getCurrentVarName()
        # this is the new text (i.e. AFTER name change)
        if originalVarName is None:
            return
        
        if len(originalVarName.strip()) == 0:
            return
        
        newVarName = item.text()
        #print("slot_variableItemNameChanged old", originalVarName, "new", newVarName)
            
        if len(newVarName.strip()) == 0: # no change, really; prevent accidental deletion
            self.workspaceModel.itemChanged.disconnect(self.slot_variableItemNameChanged)
            item.setText(originalVarName)
            self.workspaceModel.itemChanged.connect(self.slot_variableItemNameChanged)
            return
        
        if newVarName != originalVarName:
            if originalVarName in self.workspace:
                data = self.workspace.pop(originalVarName)
                self.workspace[newVarName] = data
                self.workspaceModel.update()
                
            # NOTE: 2017-09-22 21:57:23
            # check newVarName for sanity
            # FIXME 2021-10-03 22:21:36 
            
            #newVarNameOK = validate_varname(newVarName, self.workspace)
            
            #if newVarNameOK != newVarName: # also update the item's text
                #self.workspaceModel.itemChanged.disconnect(self.slot_variableItemNameChanged)
                #item.setText(newVarNameOK)
                #self.workspaceModel.itemChanged.connect(self.slot_variableItemNameChanged)
                
            #data = self.workspace.pop(originalVarName, None)
            
            ##print("slot_variableItemNameChanged old", originalVarName, "new", newVarName, "new2", newVarNameOK)
            
            #if data is None:
                #return
            
            #self.workspace[newVarNameOK] = data
            #self.workspaceModel.update()
                
    @pyqtSlot()
    @safeWrapper
    def slot_renameWorkspaceVar(self):
        """ Renames workspace variables through GUI Menu action.
        
        Called when "Rename" menu item is called from the context menu of an 
        workspace item.
        
        For the case when the variable name is changed through pressing system's 
        "rename" key (e.g., F2 in KDE) see slot_variableItemNameChanged()
        
        Presents a dialog prompting for a new variable name.
        """
        indexList = self.workspaceView.selectedIndexes()
        
        if len(indexList) != 1:
            return
        
        varName = self.workspaceModel.item(indexList[0].row(),0).text()
        
        dlg = qd.QuickDialog(self, "Rename variable")
        dlg.addLabel("Rename '%s'" % varName)
        pw = qd.StringInput(dlg, "To :")
        pw.variable.undoAvailable=True
        pw.variable.redoAvailable=True
        pw.variable.setClearButtonEnabled(True)
        pw.setText(varName)
        dlg.addWidget(pw)
        
        if dlg.exec() == 0:
            return
        
        newVarName = pw.text()
        
        if newVarName == varName:
            return
        
        newVarNameOK = validate_varname(newVarName, self.workspace)
        
        if newVarNameOK != newVarName:
            btn = QtWidgets.QMessageBox.question(self, "Rename variable", "Variable %s will be renamed to %s. Accept?" % (newVarName, newVarNameOK))
            
            if btn == QtWidgets.QMessageBox.No:
                return
            
        self.workspace[newVarNameOK] = self.workspace[varName]
        self.workspace.pop(varName, None)
        self.workspaceModel.update()
        
        # NOTE: 2021-08-21 22:27:34 DO NOT DELETE - alternative way
        #cmd = "".join([newVarNameOK, "=", varName, "; del(", varName,")"])
        #self.console.execute(cmd, hidden=True)
        
        
    @pyqtSlot()
    @safeWrapper
    def slot_saveSelectedVariables(self):
        indexList = self.workspaceView.selectedIndexes()
        
        if len(indexList) == 0:
            return
        
        varSet = set()
        
        for i in indexList:
            varSet.add(self.workspaceModel.item(i.row(),0).text())
            
        varNames = sorted([n for n in varSet])
            
        self.setCursor(QtCore.Qt.WaitCursor)
        
        try:
            #QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
            
            for n in varNames:
                if not isinstance(self.workspace[n], (QtWidgets.QWidget)):
                    pio.saveHDF5(self.workspace[n], n)
                    #pio.savePickleFile(self.workspace[n], n)
                    
            #QtWidgets.QApplication.restoreOverrideCursor()
            self.unsetCursor()
            
        except Exception as e:
            traceback.print_exc()
            #QtWidgets.QApplication.restoreOverrideCursor()
            self.unsetCursor()
            
    @pyqtSlot()
    @safeWrapper
    def slot_pickleSelectedVariables(self):
        indexList = self.workspaceView.selectedIndexes()
        
        if len(indexList) == 0:
            return
        
        varSet = set()
        
        for i in indexList:
            varSet.add(self.workspaceModel.item(i.row(),0).text())
            
        varNames = sorted([n for n in varSet])
            
        self.setCursor(QtCore.Qt.WaitCursor)
        
        try:
            #QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
            
            for n in varNames:
                if not isinstance(self.workspace[n], (QtWidgets.QWidget)):
                    #pio.saveHDF5(self.workspace[n], n)
                    pio.savePickleFile(self.workspace[n], n)
                    
            #QtWidgets.QApplication.restoreOverrideCursor()
            self.unsetCursor()
            
        except Exception as e:
            traceback.print_exc()
            #QtWidgets.QApplication.restoreOverrideCursor()
            self.unsetCursor()
            
    def _workspaceItem_to_varName(self, index:QtCore.QModelIndex):
        v = self.workspaceModel.item(index.row(), 0).text()
        
        return v if v in self.workspace.keys() else None
            
    @pyqtSlot()
    @safeWrapper
    def slot_deleteSelectedVars(self):
        """Batch-removes variables from the workspace.
        
        Variables are selected by their workspace names (symbols) using the 
        Workspace viewer GUI.
        """
        indexList = self.workspaceView.selectedIndexes()
        
        if len(indexList) == 0:
            return
        
        varNames = list()
        
        varSet = set((self._workspaceItem_to_varName(i) for i in indexList))
        
        #for i in indexList:
            #varSet.add(self.workspaceModel.item(i.row(),0).text())
            
        varNames = sorted(varSet)# Python 3.8+ facility? NOTE 2022-03-14 16:52:48 in Python3.10 sets are sorted already?
        #varNames = [v for v in sorted([n for n in varSet]) if v in self.workspace.keys()]
        #varNames = [v for v in sorted(unique([n for n in varSet])) if v in self.workspace.keys()]
            
        msgBox = QtWidgets.QMessageBox()
        
        if len(indexList) == 1:
            prompt = "Delete '%s'?" % varNames[0]
            wintitle = "Delete variable"
            
        else:
            prompt = "Delete %d selected variables?" % len(varSet)
            wintitle = "Delete variables"
            msgBox.setDetailedText("\n".join(varNames))
            
        msgBox.setWindowTitle(wintitle)
        msgBox.setIcon(QtWidgets.QMessageBox.Warning)
        msgBox.setText(prompt)
        msgBox.setInformativeText("This operation cannot be undone!")
        msgBox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        msgBox.setDefaultButton(QtWidgets.QMessageBox.No)
        
        ret = msgBox.exec()
        
        if ret == QtWidgets.QMessageBox.No:
            return
        
        #print(f"***\nScipyenWindow.slot_deleteSelectedVars varNames = {varNames}")
        
        for n in varNames:
            obj = self.workspace[n]
            if isinstance(obj, (QtWidgets.QMainWindow, mpl.figure.Figure)):
                #print("%s.slot_deleteSelectedVars %s: %s" % (self.__class__.__name__, n, obj.__class__.__name__))
                if isinstance(obj, mpl.figure.Figure):
                    plt.close(obj) # also removes obj.number from plt.get_fignums()
                    
                else:
                    obj.close()
                    #obj.closeEvent(QtGui.QCloseEvent())
                self.deRegisterViewer(obj) # does not remove its symbol for workspace - this has already been removed by delete action
                
            #self.removeFromWorkspace(n, by_name=True, update=True)
            self.removeFromWorkspace(n, by_name=True, update=False)
            #self.workspace.pop(n, None)
            
        self.workspaceModel.currentItem = None
        
        self.workspaceModel.update()
        
    @pyqtSlot(bool)
    @safeWrapper
    def slot_dockWidgetVisibilityChanged(self, val):
        if val is True:
            self.activeDockWidget=self.sender()
        
        
    @pyqtSlot(QtWidgets.QDockWidget)
    @safeWrapper
    def slot_dockWidgetActivated(self, w):
        self.activeDockWidget = w
        
    @pyqtSlot()
    @safeWrapper
    def slot_copyWorkspaceSelection(self):
        # NOTE: check out keyboard modifier WHEN this slot is called
        indexList = [i for i in self.workspaceView.selectedIndexes() if i.column() == 0]
        
        if len(indexList) == 0:
            return
        
        wscol = standard_obj_summary_headers.index("Workspace")
        
        if bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier):
            varnames = ["'%s'" % self.workspaceModel.item(i.row(),0).text() for i in indexList if self.workspaceModel.item(i.row(),wscol).text() == "Internal"]
            
        else:
            varnames = [self.workspaceModel.item(i.row(),0).text() for i in indexList if self.workspaceModel.item(i.row(),wscol).text() == "Internal"]
            
        if bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier):
            self.app.clipboard().setText(",\n".join(varnames))
            
        else:
            self.app.clipboard().setText(", ".join(varnames))
        
    @pyqtSlot()
    @safeWrapper
    def slot_copyWorkspaceSelectionQuoted(self):
        """
        DEPRECATED
        """
        warnings.warn("DEPRECATED", DeprecationWarning)
        
        
        indexList = [i for i in self.workspaceView.selectedIndexes() if i.column() == 0]
        if len(indexList) == 0:
            return

        wscol = standard_obj_summary_headers.index("Workspace")
        
        varNames = list()
        
        for i in indexList:
            if self.workspaceModel.item(i.row(),wscol).text() == "Internal":
                varNames.append("'%s'" % self.workspaceModel.item(i.row(),0).text())
            
        self.app.clipboard().setText(", ".join(varNames))
        
    @pyqtSlot()
    @safeWrapper
    def slot_pasteHistorySelection(self):
        self._copyHistorySelection_()
        self.console.paste() # by default this will paste the contents of the Cliboard, not the X11 selection
        
    @pyqtSlot()
    @safeWrapper
    def slot_pasteWorkspaceSelection(self):
        self.slot_copyWorkspaceSelection()
        #if quoted:
            #self.slot_copyWorkspaceSelectionQuoted()
        #else:
            #self.slot_copyWorkspaceSelection()
            
        self.console.paste()
        
    @pyqtSlot()
    @safeWrapper
    def slot_pasteQuotedWorkspaceSelection(self):
        """
        DEPRECATED
        """
        warnings.warn("DEPRECATED", DeprecationWarning)
        
        self.slot_copyWorkspaceSelectionQuoted()
        self.console.paste()
        

    @pyqtSlot("QTreeWidgetItem*", int)
    @safeWrapper
    def slot_historyItemSelected(self, item, col):
        # only accept session items here (for now)
        # session items have parent None
        
        #print(item.text(0))
        if item.parent() is None:
            if col == 0: # a session line selected
                if item.text(0) == "Current":
                    self.selectedSessionID = self.currentSessionID
                    
                else:
                    self.selectedSessionID = int(item.text(0))
                
        else: #  a command line is selected
            if isinstance(item.parent().text(0), str): # False if col1 selected
                if item.parent().text(0) == "Current":
                    self.selectedSessionID = self.currentSessionID
                    
                else:
                    self.selectedSessionID = int(item.parent().text(0))
                    
            else:
                self.selectedSessionID = self.currentSessionID
                
        #print("slot_historyItemSelected selected session", self.selectedSessionID)

    @pyqtSlot("QTreeWidgetItem*", int)
    @safeWrapper
    def slot_historyItemActivated(self, item, col):
        #print("slot_historyItemActivated")
        parent = item.parent()
        sessionNo = self.currentSessionID
        
        #print(parent)

        if parent is None:                      # this is a session item
            return                              # we don't care about it
        
        # now, this IS a statement item and we care about it
        ptxt = parent.text(0)                   # its parent can only be a session item
        if ptxt != "Current":                   # maybe a historic session number
            sessionNo = int(parent.text(0))     # if so then get its session number
    
        lineno = int(item.text(0))              # get its line number (execution number)
        cmd = item.text(1)                # get its actual statement
        
        #print(cmd)
        
        backSession = self.currentSessionID - sessionNo

        #TODO: explore constructing a command like %hist %rerun %recall line magics
        #TODO: I'd need to store the line number as well, somehow, in the history tree widget
        #TODO: in which case the history tree would have the items on 3 columns (session, line no, code)
        #TODO: and these would be executed by self.ipkernel.shell.run_line_magic('recall', ...)
        #NOTE: until then, we send the item's text to the shell by calling
        #NOTE: self.ipkernel.shell.run_cell(cmd, store_history=True, silent=False, shell_futures=True)
        #NOTE: see code comments in self.slot_initQtConsole()
        self.ipkernel.shell.run_cell(cmd, store_history = True, silent=False, shell_futures=True)
        #NOTE: 2017-03-19 21:15:48 while this DOES go to the ipython's history
        #NOTE: it DOES NOT go to the self.console.history_tail therefore calling the slot_updateHistory slot
        #NOTE: won't work hence -- basically, console.history and shell history go out of sync
        #NOTE: therefore we need to update OUR history manually
        self.executionCount = self.ipkernel.shell.execution_count
        self._updateHistoryView_(self.executionCount-1, self.ipkernel.shell.history_manager.input_hist_raw[-1])
        self.workspaceModel.update()
        
        #NOTE: 2017-03-19 22:54:55 also this DOES NOT re-create the output
        #NOTE: I guess I can live with this for now...

    @pyqtSlot()
    def slot_Quit(self):
        self.close()
        
    def closeEvent(self, evt):
        #open_windows = ((name, obj) for (name, obj) in self.workspace.items() if isinstance(obj, QtWidgets.QWidget))
        if self.external_console is not None:
            self.external_console.window.closeEvent(evt)
            if not evt.isAccepted():
                return
            self.external_console = None
            self.workspace["external_console"] = None
            self.workspaceModel.user_ns_hidden["external_console"] = None
            
        if self.console is not None:
            self.console.kernel_manager.shutdown_kernel()
            self.console.close()
            self.console = None
            
        plt.close("all")

        self.saveSettings()
        
        #self.app.closeAllWindows()
        #open_windows = (obj for obj in self.workspace.values() if isinstance(obj, QtWidgets.QWidget) and type(obj) not in VTH.gui_handlers and obj.isVisible())
        
        #for o in open_windows:
            #o.close()
        
            
        evt.accept()
        
    #def saveSettings(self):
        #self.saveWindowSettings()
        #self.saveAppSettings()
        
    #def saveAppSettings(self):
        #pass
        
    def saveWindowSettings(self):
        gname, pfx = saveWindowSettings(self.qsettings, self, group_name = self.__class__.__name__)
        
        #### NOTE: user-defined gui handlers (viewers) for variable types, or user-changed
        # configuration of gui handlers
        # FIXME 2021-07-17 22:55:17 
        # Not written to Scipyen.conf -- WHY ??? because nested groups aren't
        # supported by QSettings
        self.qsettings.beginGroup("Custom_GUI_Handlers")
        for viewerClass in VTH.gui_handlers.keys():
            pfx = viewerClass.__name__
            
            if viewerClass not in VTH.default_handlers.keys():
                # store user-defines handlers
                self.qsettings.setValue("%s_action" % pfx, VTH.gui_handlers[viewerClass]["action"])
                
                if isinstance(VTH.gui_handlers[viewerClass]["types"], type):
                    type_names = [VTH.gui_handlers[viewerClass]["types"]._name__]
                    
                else:
                    type_names = [t.__name__ for t in VTH.gui_handlers[viewerClass]["types"]] 
                    
                self.qsettings.setValue("%s_types" % pfx, type_names)
                
            else:
                # store customizations for built-in handlers:
                default_action_name = VTH.default_handlers[viewerClass]["action"]
                default_types = VTH.default_handlers[viewerClass]["types"]
                
                if VTH.gui_handlers[viewerClass]["types"] != default_types:
                    if isinstance(VTH.gui_handlers[viewerClass]["types"], type):
                        type_names = [VTH.gui_handlers[viewerClass]["types"].__name__]
                        
                    else:
                        type_names = [t.__name__ for t in VTH.gui_handlers[viewerClass]["types"]]
                        
                    self.qsettings.setValue("%s_types" % pfx, VTH.gui_handlers[viewerClass]["types"])
                
                if VTH.gui_handlers[viewerClass]["action"] is not default_action_name:
                    self.qsettings.setValue("%s_action" % pfx, VTH.gui_handlers[viewerClass]["action"])
        
        self.qsettings.endGroup()
        
    #@processtimefunc
    def loadSettings(self):
        """Overrides ScipyenConfigurable.loadSettings()"""
        super(WorkspaceGuiMixin, self).loadSettings() # inherited from ScipyenConfigurable
        
    def loadWindowSettings(self):
        #print("%s.loadWindowSettings" % self.__class__.__name__)
        gname, prefix = loadWindowSettings(self.qsettings, self, group_name = self.__class__.__name__)
        
        
        self.qsettings.beginGroup("Custom_GUI_Handlers")
        
        for viewerClass in VTH.gui_handlers.keys():
            pfx = viewerClass.__name__
            
            if viewerClass not in VTH.default_handlers.keys():
                action = self.qsettings.value("%s_action" % pfx, "View")
                type_names_list = self.qsettings.value("%s_types" % pfx, ["type(None)"])
                types = [eval(t_name) for t_name in type_names_list]
                if len(types) == 0:
                    continue
                VTH.register(viewerClass, types, actionName=action)
        
        # FIXME: 2019-11-03 22:56:20 -- inconsistency
        # what if a viewer doesn't have any types defined?
        # by default it would be skipped from the auto-menus, but
        # if one uses VTH.register() then types must be defined!
        #for viewerGroup in self.qsettings.childGroups():
            #customViewer = [v for v in VTH.gui_handlers.keys() if v.__name__ == viewerGroup]
            #if len(customViewer):
                #viewerClass = customViewer[0]
                #self.qsettings.beginGroup(viewerGroup)
                #if "action" in self.qsettings.childKeys():
                    #action = self.qsettings.value("action", "View")
                    
                #if "types" in self.qsettings.childKeys():
                    #type_names_list = self.qsettings.value("types", ["type(None)"])
                    #types = [eval(t_name) for t_name in type_names_list]
                    
                #if len(types) == 0: # see FIXME: 2019-11-03 22:56:20
                    #self.qsettings.endGroup()
                    #continue
                
                #VTH.register(viewerClass, types, actionName=action)
                #self.qsettings.endGroup()
            
        self.qsettings.endGroup()
    
    #@processtimefunc
    def _configureUI_(self):
        ''' Collect file menu actions & submenus that are built in the UI file. This should be 
            done before loading the plugins.
        '''
        
        # NOTE: 2021-04-15 10:12:33 TODO
        # allow user to choose app style interactively -- 
        
        # list of available syle names
        self._available_Qt_style_names_ = QtWidgets.QStyleFactory.keys()
        self.actionGUI_Style.triggered.connect(self._slot_set_Application_style)

        # NOTE: 2016-05-02 14:26:58
        # add HERE a "Recent Files" submenu to the menuFile

        # NOTE: 2017-11-10 14:17:11 TODO
        # factor-out the following (BEGIN ... END) in a plugin-like framework
        # BEGIN
        
        # NOTE: 2017-11-11 21:30:58 add this as a menu command, and open it in a
        # separate window, rather than tabbed window, which is more useful for
        # small screens (e.g.,laptops)
        
        self.applicationsMenu = QtWidgets.QMenu("Applications", self)
        self.menubar.insertMenu(self.menuHelp.menuAction(), self.applicationsMenu)
        
        self.CaTAnalysisAction = QtWidgets.QAction("LSCaT (CaT Analysis)", self)
        self.CaTAnalysisAction.triggered.connect(self.slot_launchCaTAnalysis)
        self.applicationsMenu.addAction(self.CaTAnalysisAction)
        
        self.analyseAPtrainsAction = QtWidgets.QAction("test", self)
        self.analyseAPtrainsAction.triggered.connect(self.slot_launchTest)
        self.applicationsMenu.addAction(self.analyseAPtrainsAction)
        
        self.whatsThisAction = QtWidgets.QWhatsThis.createAction(self)
        
        self.menuHelp.addAction(self.whatsThisAction)
        
        #self.tabWidget.addTab(self.lscatWindow, "CaT Analysis")
        # END
        
        #self.tabWidget.setCurrentIndex(0)
        
        # NOTE:2019-08-06 15:21:23
        # this will mess up filesFilterFrame visibility!
        #self.app.lastWindowClosed.connect(self.slot_Quit)
        
        self.actionQuit.triggered.connect(self.slot_Quit)
        
        self.actionConsole = QtWidgets.QAction("Scipyen Console")
        self.actionConsole.triggered.connect(self.slot_initQtConsole)
        self.menuConsoles.addAction(self.actionConsole)
        
        self.actionExternalIPython = QtWidgets.QAction("External IPython")
        self.actionExternalIPython.triggered.connect(self.slot_launchExternalIPython)
        self.menuConsoles.addAction(self.actionExternalIPython)
        
        if has_neuron:
            self.actionExternalNrnIPython = QtWidgets.QAction("External IPython for NEURON")
            self.actionExternalNrnIPython.triggered.connect(self.slot_launchExternalNeuronIPython)
            self.menuConsoles.addAction(self.actionExternalNrnIPython)
        
        self.menuWith_Running_Kernel = QtWidgets.QMenu("With Running Kernel", self)
        self.menuConsoles.addMenu(self.menuWith_Running_Kernel)
        self.actionRunning_IPython = QtWidgets.QAction("Choose kernel ...")
        self.actionRunning_IPython.triggered.connect(self.slot_launchExternalRunningIPython)
        self.menuWith_Running_Kernel.addAction(self.actionRunning_IPython)
        
        if has_neuron:
            self.actionRunning_IPython_for_Neuron = QtWidgets.QAction("Choose kernel and launch NEURON")
            self.actionRunning_IPython_for_Neuron.triggered.connect(self.slot_launchExternalRunningIPythonNeuron) 
            self.menuWith_Running_Kernel.addAction(self.actionRunning_IPython_for_Neuron)
        
        #self.actionRestore_Workspace.triggered.connect(self.slot_restoreWorkspace)
        self.actionHelp_On_Console.triggered.connect(self._helpOnConsole_)
        
        self.actionOpen.triggered.connect(self.slot_openFiles)
        #self.actionOpen.triggered.connect(self.openFile)
        #self.actionOpen_Files.triggered.connect(self.slot_openFiles)
        self.actionView_Data.triggered.connect(self.slot_viewSelectedVar)
        self.actionView_Data_New_Window.triggered.connect(self.slot_viewSelectedVarInNewWindow)
        self.actionReload_Plugins.triggered.connect(self.slot_reloadPlugins)
        self.actionSave.triggered.connect(self.slot_saveFile)
        self.actionChange_Working_Directory.triggered.connect(self.slot_selectWorkDir)
        #self.actionSave_pickle.triggered.connect(self.slot_saveSelectedVariables)
        
        # NOTE: 2017-07-07 22:14:40
        # Shortcut to delete selected items in workspaceView
        # thanks to QtCentre forum (J-P Nurmi)
        
        self.keyDeleteStuff = QtWidgets.QShortcut(QtGui.QKeySequence(QtGui.QKeySequence.Delete), self)
        self.keyDeleteStuff.activated.connect(self.slot_keyDeleteStuff)
        
        # NOTE: File menu - some actions defined in mainwindow.ui
        self.actionImport_PrairieView_data.triggered.connect(self.slot_importPrairieView)
        self.recentFilesMenu = QtWidgets.QMenu("Recent Files", self)
        self.menuFile.insertMenu(self.actionQuit, self.recentFilesMenu)
        
        self.recentDirectoriesMenu = QtWidgets.QMenu("Recent Directories", self)
        self.menuFile.insertMenu(self.actionQuit, self.recentDirectoriesMenu)
        
        self.menuFile.insertSeparator(self.actionQuit)
        
        # ### BEGIN scripts menu
        self.menuScripts = QtWidgets.QMenu("Scripts", self)
        self.menubar.insertMenu(self.menuHelp.menuAction(), self.menuScripts)
        self.actionScriptRun = QtWidgets.QAction("Run...", self)
        self.actionScriptRun.triggered.connect(self.slot_runPythonScript)
        self.menuScripts.addAction(self.actionScriptRun)
        self.actionScriptToConsole = QtWidgets.QAction("To Console...", self)
        self.actionScriptToConsole.triggered.connect(self.slot_pastePythonScript)
        self.menuScripts.addAction(self.actionScriptToConsole)
        self.menuScripts.addSeparator()
        self.recentScriptsMenu = QtWidgets.QMenu("Recent Scripts", self)
        self.menuScripts.addMenu(self.recentScriptsMenu)
        self.menuScripts.addSeparator()
        self.actionManageScripts = QtWidgets.QAction("Script Manager")
        self.actionManageScripts.triggered.connect(self.slot_showScriptsManagerWindow)
        self.menuScripts.addAction(self.actionManageScripts)
        
        #### END scripts menu
        
        # NOTE: 2016-05-02 12:22:21 -- refactoring plugin codes
        #self.startPluginLoad.connect(self.slot_loadPlugins)
        #self.startPluginLoad.emit()
        
        #### BEGIN custom workspace viewer DO NOT DELETE
        
        # NOTE: 2019-08-11 00:01:11
        # replace the workspace viewer in the designer UI file with the derived one
        # WARNING work in progress, don't use yet
        #self.workspaceView = WorkspaceViewer(self)
        #self.workspaceView.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        #self.workspaceView.setAlternatingRowColors(True)
        
        #self.workspaceView.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked | 
                                           #QtWidgets.QAbstractItemView.EditKeyPressed |
                                           #QtWidgets.QAbstractItemView.AnyKeyPressed)
        
        ##self.workspaceView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        
        #self.workspaceView.setAcceptDrops(True)
        #self.workspaceView.setDragEnabled(True)
        #self.workspaceView.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)
        #self.workspaceView.setDefaultDropAction(QtCore.Qt.IgnoreAction)
        
        
        #self.dockWidgetWorkspace.setWidget(self.workspaceView)
        #self.workspaceView.show()
        
        #### END custom workspace viewer DO NOT DELETE
        
        #### BEGIN workspace view
        self.workspaceView.setShowGrid(False)
        self.workspaceView.setModel(self.workspaceModel)
        self.workspaceView.selectionModel().selectionChanged[QtCore.QItemSelection, QtCore.QItemSelection].connect(self.slot_selectionChanged)
        # NOTE 2021-07-28 14:26:09 
        # avoid editing by db-click
        self.workspaceView.setEditTriggers(QtWidgets.QAbstractItemView.EditKeyPressed)
        self.workspaceView.activated[QtCore.QModelIndex].connect(self.slot_variableItemActivated)
        # NOTE: 2021-07-28 14:41:38
        # taken care of by selectionChanged?
        self.workspaceView.pressed[QtCore.QModelIndex].connect(self.slot_variableItemPressed)
        self.workspaceView.customContextMenuRequested[QtCore.QPoint].connect(self.slot_workspaceViewContextMenuRequest)
        
        # NOTE: 2019-12-01 13:30:02
        # is seems that for Qt > 5.12 setSortingEnabled must be set to False so 
        # that programmatic sorting by calling sortByColumn() actually works!
        # when set to True then sorting only works by manually clicking on the 
        # column's header (which gets a sorting indicator widget and its colunm
        # becomes sortable by click)
        self.workspaceView.setSortingEnabled(False)
        self.workspaceView.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.workspaceView.setSortingEnabled(True)
        self.workspaceView.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.workspaceView.horizontalHeader().setStretchLastSection(False)

        self.workspaceModel.itemChanged.connect(self.slot_variableItemNameChanged)
        self.workspaceModel.modelContentsChanged.connect(self.slot_updateWorkspaceView)
        #### END workspace view
        
        #### BEGIN command history view
        self.historyTreeWidget.setHeaderLabels(["Session, line:", "Statement:"])
        self.historyTreeWidget.itemActivated[QtWidgets.QTreeWidgetItem, int].connect(self.slot_historyItemActivated)
        self.historyTreeWidget.customContextMenuRequested[QtCore.QPoint].connect(self.slot_historyContextMenuRequest)
        self.historyTreeWidget.itemClicked[QtWidgets.QTreeWidgetItem, int].connect(self.slot_historyItemSelected)
        
        #### END command history view
        self.setWindowTitle("Scipyen")
        
        self.newViewersMenu = QtWidgets.QMenu("Create New", self)
        for v in gui_viewers:
            self.newViewersMenu.addAction(v.__name__, self.slot_newViewerMenuAction)
        self.menuViewers.addMenu(self.newViewersMenu)
        
        # add new viewers menu as toolbar action, too
        self.newViewersAction = self.toolBar.addAction(QtGui.QIcon.fromTheme("window-new"), "New Viewer")
        self.newViewersAction.setMenu(self.newViewersMenu)
        self.consolesAction = self.toolBar.addAction(QtGui.QIcon.fromTheme("utilities-terminal"), "Consoles")
        self.consolesAction.setMenu(self.menuConsoles) # this one is defined in the ui file mainwindow.ui
        self.scriptsAction = self.toolBar.addAction(QtGui.QIcon.fromTheme("dialog-scripts"), "Scripts")
        self.scriptsAction.setMenu(self.menuScripts)
        self.applicationsAction = self.toolBar.addAction(QtGui.QIcon.fromTheme("homerun"), "Applications")
        self.applicationsAction.setMenu(self.applicationsMenu)
        self.refreshViewAction = self.toolBar.addAction(QtGui.QIcon.fromTheme("view-refresh"), "Refresh Active View")
        self.refreshViewAction.triggered.connect(self.slot_refreshView)
        
        tbactions = (self.newViewersAction, self.consolesAction, self.scriptsAction, self.applicationsAction)
        tw = (w for w in itertools.chain(*(a.associatedWidgets() for a in tbactions)) if w is not self.toolBar)
        
        for w in tw:
            w.setPopupMode(QtWidgets.QToolButton.InstantPopup)
            
        #### BEGIN do not delete: action for presenting a list of viewer types to choose from
        #self.menuViewer.addSeparator()
        #self.actionNewViewer = self.menuViewer.addAction("New...")
        #self.actionNewViewer.triggered.connect(self.slot_newViewer)
        #### END do not delete: action for presenting a list of viewer types to choose from
        
        #### BEGIN Dock widgets management - it is good to know which one is on top
        self.dockWidgetWorkspace.visibilityChanged[bool].connect(self.slot_dockWidgetVisibilityChanged)
        
        #### BEGIN file system view,  navigation widgets & actions
        self.fileSystemTreeView.setModel(self.fileSystemModel)
        self.fileSystemTreeView.setAlternatingRowColors(True)
        self.fileSystemTreeView.activated[QtCore.QModelIndex].connect(self.slot_fileSystemItemActivated)
        self.fileSystemTreeView.collapsed[QtCore.QModelIndex].connect(self.slot_resizeFileTreeViewFirstColumn)
        self.fileSystemTreeView.expanded[QtCore.QModelIndex].connect(self.slot_resizeFileTreeViewFirstColumn)
        self.fileSystemTreeView.customContextMenuRequested[QtCore.QPoint].connect(self.slot_fileSystemContextMenuRequest)
        self.fileSystemTreeView.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.fileSystemTreeView.setRootIsDecorated(True)
        
        self.fileSystemModel.directoryLoaded[str].connect(self.slot_resizeFileTreeColumnForPath)
        self.fileSystemModel.rootPathChanged[str].connect(self.slot_rootPathChanged)
        #self.fileSystemModel.dataChanged[QtCore.QModelIndex, QtCore.QModelIndex, "QVector<int>"].connect(self.slot_fileSystemDataChanged)

        self.directoryComboBox.lineEdit().setClearButtonEnabled(True)
        
        self.removeRecentDirFromListAction = QtWidgets.QAction(QtGui.QIcon.fromTheme("edit-delete"), \
                                                        "Remove this path from list", \
                                                        self.directoryComboBox.lineEdit())
        
        self.removeRecentDirFromListAction.setToolTip("Remove this path from history")
        
        self.removeRecentDirFromListAction.triggered.connect(self.slot_removeDirFromHistory)
        
        self.clearRecentDirListAction = QtWidgets.QAction(QtGui.QIcon.fromTheme("final_activity"), \
                                                        "Clear history of visited paths", \
                                                        self.directoryComboBox.lineEdit())
        
        self.clearRecentDirListAction.setToolTip("Clear history of visited paths")
        
        self.clearRecentDirListAction.triggered.connect(self.slot_clearRecentDirList)
        
        self.directoryComboBox.lineEdit().addAction(self.removeRecentDirFromListAction, \
                                                    QtWidgets.QLineEdit.TrailingPosition)
        
        self.directoryComboBox.activated[str].connect(self.slot_chDirString)

        self.fileSystemFilter.lineEdit().setClearButtonEnabled(True)
        
        self.removeFileFilterFromListAction = QtWidgets.QAction(QtGui.QIcon.fromTheme("edit-delete"), \
                                                    "Remove this filter from history", \
                                                    self.fileSystemFilter.lineEdit())
        
        self.removeFileFilterFromListAction.setToolTip("Remove this filter from history")
        
        self.removeFileFilterFromListAction.triggered.connect(self.slot_removeFileFilterFromHistory)
        
        self.clearFileFilterListAction = QtWidgets.QAction(QtGui.QIcon.fromTheme("final_activity"), \
                                                    "Clear filter list", \
                                                    self.fileSystemFilter.lineEdit())
        
        self.clearFileFilterListAction.setToolTip("Clear file filter history")
        
        self.clearFileFilterListAction.triggered.connect(self.slot_clearFileFilterHistory)
        
        self.fileSystemFilter.lineEdit().addAction(self.removeFileFilterFromListAction, \
                                        QtWidgets.QLineEdit.TrailingPosition)
        
        
        self.fileSystemFilter.currentTextChanged[str].connect(self.slot_setFileNameFilter)
        
        self.dirHomeBtn.released.connect(self.slot_goToHomeDir)
        self.dirUpBtn.released.connect(self.slot_goToParentDir)
        self.dirBackBtn.released.connect(self.slot_goToPrevDir)
        self.dirFwdBtn.released.connect(self.slot_goToNextDir)
        #self.selDirBtn.released.connect(self.slot_selectDir)
        self.selDirBtn.released.connect(self.slot_selectWorkDir)
        
        self.viewFilesFilterToolBtn.released.connect(self.slot_showFilesFilter)
        self.hideFilesFilterToolBtn.released.connect(self.slot_hideFilesFilter)
        
        # filter/select variable names combo
        self.varNameFilterFinderComboBox.currentTextChanged[str].connect(self.slot_filterSelectVarNames)
        
        self.varNameFilterFinderComboBox.lineEdit().returnPressed.connect(self.slot_addVarNameToFinderHistory)
        self.varNameFilterFinderComboBox.lineEdit().setClearButtonEnabled(True)
        self.varNameFilterFinderComboBox.lineEdit().undoAvailable = True
        self.varNameFilterFinderComboBox.lineEdit().redoAvailable = True
        
        self.removeVarNameFromFinderListAction = QtWidgets.QAction(QtGui.QIcon.fromTheme("edit-delete"), \
                                                                    "Remove item from list", \
                                                                    self.varNameFilterFinderComboBox.lineEdit())
        
        self.removeVarNameFromFinderListAction.triggered.connect(self.slot_removeVarNameFromFinderHistory)
        
        self.varNameFilterFinderComboBox.lineEdit().addAction(self.removeVarNameFromFinderListAction,
                                                              QtWidgets.QLineEdit.TrailingPosition)
        
        #### END file system view,  navigation widgets & actions
        
        #### BEGIN command history filters
        # filter/select commands from history combo
        self.commandFinderComboBox.currentTextChanged[str].connect(self.slot_findCommand)

        self.commandFinderComboBox.lineEdit().returnPressed.connect(self.slot_addCommandFindToHistory)
        self.commandFinderComboBox.lineEdit().setClearButtonEnabled(True)
        self.commandFinderComboBox.lineEdit().undoAvailable = True
        self.commandFinderComboBox.lineEdit().redoAvailable = True
        
        self.removeItemFromCommandFinderListAction = QtWidgets.QAction(QtGui.QIcon.fromTheme("edit-delete"), \
                                                                        "Remove item from list",\
                                                                        self.commandFinderComboBox.lineEdit())
        
        self.removeItemFromCommandFinderListAction.triggered.connect(self.slot_removeItemFromCommandFinderHistory)
        
        self.commandFinderComboBox.lineEdit().addAction(self.removeItemFromCommandFinderListAction, \
                                                        QtWidgets.QLineEdit.TrailingPosition)
        
        #### END command history filters
        
        #### BEGIN console dock
        self.consoleDockWidget = QtWidgets.QDockWidget("Console", self, objectName="consoleDockWidget")
        self.consoleDockWidget.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)
        self.consoleDockWidget.setFeatures(QtWidgets.QDockWidget.AllDockWidgetFeatures)
        self.consoleDockWidget.setVisible(False)
        #### END console dock
        #### END Dock widgets management
    @pyqtSlot()
    @safeWrapper
    def slot_keyDeleteStuff(self):
        if self.workspaceView.hasFocus():
            self.slot_deleteSelectedVars()
        
    @pyqtSlot()
    @safeWrapper
    def slot_goToHomeDir(self):
        if sys.platform == "win32":
            self.slot_changeDirectory(os.environ['USERPROFILE'])
        else:
            self.slot_changeDirectory(os.environ['HOME'])
        
    @pyqtSlot()
    @safeWrapper
    def slot_goToParentDir(self):
        #print(self.currentDir)
        if self.currentDir is None:
            self.slot_changeDirectory()
        else:
            self.slot_changeDirectory(os.path.dirname(os.path.abspath(self.currentDir)))
    
    @pyqtSlot()
    @safeWrapper
    def slot_goToPrevDir(self):
        if len(self.navPrevDir) > 0:
            self.navNextDir.appendleft(self.navPrevDir[0])
            prevDir = self.navPrevDir.popleft()
            self.slot_changeDirectory(prevDir)
            
    @pyqtSlot()
    @safeWrapper
    def slot_goToNextDir(self):
        if len(self.navNextDir) > 0:
            self.navPrevDir.appendleft(self.navNextDir[0])
            nextDir = self.navNextDir.popleft()
            self.slot_changeDirectory(nextDir)
            
    @pyqtSlot()
    @safeWrapper
    def slot_systemOpenCurrentFolder(self):
        targetDir = self.fileSystemModel.rootPath()
        self.slot_systemOpenFileOrFolder(targetDir)
        
    @pyqtSlot()
    @safeWrapper
    def slot_systemOpenSelectedFiles(self):
        selectedItems = [item for item in self.fileSystemTreeView.selectedIndexes() \
                         if item.column() == 0]# list of QModelIndex
        
        for item in selectedItems:
            self.slot_systemOpenFileOrFolder(self.fileSystemModel.filePath(item))
        
    @safeWrapper
    def _addRecentFile_(self, item, loader=None):
        '''Add the fully qualified file path 'item' as a key to the dictionary of
        recently opened files. The key is mapped to 'loader' which is a callable
        which takes a string argument containing the fully qualified file name and 
        returns the loaded data (for example one of the file loader function defined
        in the pictio module) or None, in which case the pictio.loadFile will sort out
        how to open the file.
        
        
        # NOTE: 2017-06-29 21:49:39
        Pictio now uses the mimetypes module
        '''
        if self._recentFiles is None:
            self._recentFiles = collections.OrderedDict()

        if len(self._recentFiles) == 0:
            self._recentFiles[item] = loader
        else:
            recFNames = list(self._recentFiles.keys())

            if item not in recFNames:
                if len(self._recentFiles) == self._maxRecentFiles:
                    del(self._recentFiles[recFNames[-1]])

                self._recentFiles[item] = loader
                
            elif self._recentFiles[item] != loader:
                self._recentFiles[item] = loader

        self._refreshRecentFilesMenu_()
        
        #targetDir = os.path.dirname(item)
        
        #self._setRecentDirectory_(targetDir)

    def _refreshRecentFilesMenu_(self):
        '''Recreates the Recent Files submenu of the File menu; each recent file
        gets a QAction with the 'triggered' slot connected to self.slot_loadRecentFile.
        '''
        self.recentFilesMenu.clear()
        
        if len(self._recentFiles) > 0:
            for item in self._recentFiles.keys():
                action = self.recentFilesMenu.addAction(item)
                action.triggered.connect(self.slot_loadRecentFile)
                
            self.recentFilesMenu.addSeparator()
            clearAction = self.recentFilesMenu.addAction("Clear Recent Files List")
            clearAction.triggered.connect(self._clearRecentFiles_)
            
    def _refreshRecentDirsComboBox_(self):
        self.directoryComboBox.clear()
        if len(self._recentDirectories) > 0:
            for item in self._recentDirectories:
                self.directoryComboBox.addItem(item)
        
        self.directoryComboBox.setCurrentIndex(0)
        
    def _clearRecentFiles_(self):
        self._recentFiles.clear()
        self._refreshRecentFilesMenu_()
        
    def _refreshRecentDirs_(self):
        self._refreshRecentDirectoriesMenu_()
        self._refreshRecentDirsComboBox_()
        
    def _refreshRecentDirectoriesMenu_(self):
        self.recentDirectoriesMenu.clear()
        
        if len(self.recentDirectories) > 0:
            for item in self.recentDirectories:
                action = self.recentDirectoriesMenu.addAction(item)
                action.setText(item)
                action.triggered.connect(self.slot_changeDirectory)
                
            self.recentDirectoriesMenu.addSeparator()
            clearDirAction = self.recentDirectoriesMenu.addAction("Clear Recent Directories List")
            clearDirAction.triggered.connect(self._clearRecentDirectories_)
            
    def _clearRecentDirectories_(self):
        self._recentDirectories.clear()
        self._refreshRecentDirs_()
        
    def _refreshRecentScriptsMenu_(self):
        self.recentScriptsMenu.clear()
        self._recent_scripts_dict_.clear()
        
        if len(self.recentScripts) > 0:
            for s in self.recentScripts:
                s_name = os.path.basename(s)
                self._recent_scripts_dict_[s] = s_name
                ss = rf"{s_name}"
                action = self.recentScriptsMenu.addAction(ss)
                action.setText(ss)
                action.setToolTip(s)
                action.setStatusTip(s)
                action.triggered.connect(self._slot_runRecentPythonScript_)
                
            if any([f not in self._recent_scripts_dict_.keys() for f in self.scriptsManager.scriptFileNames]) \
                or any([f not in self.scriptsManager.scriptFileNames for f in self._recent_scripts_dict_.keys()]):
                self.scriptsManager.setData(self._recent_scripts_dict_)
                
        else:
            if len(self.scriptsManager.scriptFileNames):
                self.scriptsManager.clear()

    @safeWrapper
    def dragEnterEvent(self, event):
        event.acceptProposedAction()
        event.accept()
        
    @safeWrapper
    def dropEvent(self, event):
        self.statusbar.showMessage("Load file or change directory. SHIFT to also change to file's parent directory")
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            self.slot_loadDroppedURLs(urls, event.keyboardModifiers() == QtCore.Qt.ShiftModifier, event.pos())
            
        event.accept()
            
        self.statusbar.clearMessage()
        
    @pyqtSlot(object, bool, QtCore.QPoint)
    @safeWrapper
    def slot_loadDroppedURLs(self, urls, chdirs, pos):
        if isinstance(urls, (tuple, list)) and all([isinstance(url, QtCore.QUrl) for url in urls]):
            if len(urls) == 1 and (urls[0].isRelative() or urls[0].isLocalFile()) and os.path.isfile(urls[0].path()):
                # check if this is a python source file
                mimeType = QtCore.QMimeDatabase().mimeTypeForFile(QtCore.QFileInfo(urls[0].path()))
                
                if all([s in mimeType.name() for s in ("text", "python")]):
                    self.slot_handlePythonTextFile(urls[0].path(), pos)
                    return
                
            for url in urls:
                if url.isValid():
                    if url.isRelative() or url.isLocalFile():
                        path = url.path()
                        if os.path.isdir(path):
                            self.slot_changeDirectory(path)
                            
                        elif os.path.isfile(path):
                            if chdirs:
                                self.slot_changeDirectory(os.path.dirname(path))
                                
                            self.loadFile(path)
                            
                        else:
                            warnings.warn("ScipyenWindow.slot_loadDroppedURLs: I don't know how to handle %s" % path)
                    else:
                        warnings.warn("ScipyenWindow.slot_loadDroppedURLs: Remote URLs not yet supported", NotImplemented)
    @pyqtSlot(QtCore.QPoint)
    @safeWrapper
    def slot_fileSystemContextMenuRequest(self, point):
        cm = QtWidgets.QMenu("Selected Items", self)
        
        selectedItems = [item for item in self.fileSystemTreeView.selectedIndexes() \
                         if item.column() == 0]# list of QModelIndex
        
        action_0 = None
        
        if len(selectedItems):
            fileNames = [self.fileSystemModel.filePath(i) for i in selectedItems]
            
            openFileObjects = cm.addAction("Open")
            openFileObjects.triggered.connect(self.slot_openSelectedFileItems)
            
            if all([any([s in pio.getMimeAndFileType(f)[0] for s in ("spreadsheet", "excel", "csv", "tab-separated-values")]) for f in fileNames]):
                importAsDataFrame = cm.addAction("Open as DataFrame")
                importAsDataFrame.triggered.connect(self.slot_importDataFrame)
            
            fileNamesToConsole = cm.addAction("Send Name(s) to Console")
            fileNamesToConsole.triggered.connect(self._sendFileNamesToConsole_)
            
            cm.addSeparator()
            openFilesInSystemApp = cm.addAction("Open With Default Application")
            openFilesInSystemApp.triggered.connect(self.slot_systemOpenSelectedFiles)
            
            action_0 = openFileObjects
            
        
        openParentFolderInSystemApp = cm.addAction("Open Parent Folder In File Manager")
        openParentFolderInSystemApp.triggered.connect(self.slot_systemOpenParentFolderForSelectedItems)
        
        openFolderInFileManager = cm.addAction("Open This Folder In File Manager")
        openFolderInFileManager.triggered.connect(self.slot_systemOpenCurrentFolder)
        
        if action_0 is None:
            action_0 = openParentFolderInSystemApp
            
        cm.popup(self.fileSystemTreeView.mapToGlobal(point), action_0)
        
    @pyqtSlot()
    @safeWrapper
    def slot_addVarNameToFinderHistory(self):
        varTxt = self.varNameFilterFinderComboBox.lineEdit().text()
        if len(varTxt) > 0 and varTxt not in self.recentVariablesList:
            self.recentVariablesList.appendleft(varTxt)
            self.lastVariableFind = varTxt
        
    # NOTE: 2017-08-03 08:44:34
    # TODO/FIXME decide on the match; basically works with match2
    # TODO add to varname history and save/restore from configuration file
    # TODO: find a way to filter displayed variable names -- low pripriy as we don't 
    # overpopulate the variable browser yet
    @pyqtSlot(str)
    @safeWrapper
    def slot_filterSelectVarNames(self, val):
        """Select variables in workspace viewer, according to name filter.
        """
        match = QtCore.Qt.MatchContains | \
                QtCore.Qt.MatchCaseSensitive | \
                QtCore.Qt.MatchWrap | \
                QtCore.Qt.MatchRecursive | \
                QtCore.Qt.MatchRegExp
        
        #### BEGIN other matching options - dont work as well
        #match = QtCore.Qt.MatchContains | \
                #QtCore.Qt.MatchCaseSensitive | \
                #QtCore.Qt.MatchWildcard | \
                #QtCore.Qt.MatchWrap | \
                #QtCore.Qt.MatchRecursive
            
        #match = QtCore.Qt.MatchWildcard| \
                #QtCore.Qt.MatchCaseSensitive | \
                #QtCore.Qt.MatchWrap | \
                #QtCore.Qt.MatchRecursive
                
        #### END other matching options - dont work as well
        
        
        itemList = self.workspaceModel.findItems(val, match)
        
        self.workspaceView.selectionModel().clearSelection()
        
        if len(itemList) > 0:
            for i in itemList:
                self.workspaceView.selectionModel().select(i.index(), QtCore.QItemSelectionModel.Select)
            
    @pyqtSlot()
    @safeWrapper
    def slot_removeVarNameFromFinderHistory(self):
        currentNdx = self.varNameFilterFinderComboBox.currentIndex()
        varTxt = self.varNameFilterFinderComboBox.itemText(currentNdx)
        if varTxt in self.recentVariablesList:
            self.recentVariablesList.remove(varTxt)
            
        self.varNameFilterFinderComboBox.removeItem(currentNdx)
        self.varNameFilterFinderComboBox.lineEdit().setClearButtonEnabled(True)

                
    # NOTE: 2019-10-17 21:36:39
    # TODO: find a way to filter command display (grey out the ones NOT
    # filtered for) -- a higher priority than for slot_filterSelectVarNames ,since here
    # we have A LOT of commands in the history
    # TODO: if the above task is successfully completed, then also find 
    # out how to filter or select by session number
    @pyqtSlot(str)
    @safeWrapper
    def slot_findCommand(self, val):
        """Finds command in history tree based on glob search.
        
        Works across sessions.
        
        TODO option to search in a selected session only
        """
        from fnmatch import translate
        # FIXME TODO find across sessions
        # search in the selected session (click on session number)
        
        if len(val):
            p = re.compile(translate(val))
            
        else:
            p = None
            
        #selected_children = list()
        
        original_selection_mode = self.historyTreeWidget.selectionMode()
        
        self.historyTreeWidget.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        
        try:
            for k in range(self.historyTreeWidget.topLevelItemCount()):
                topLevelItem = self.historyTreeWidget.topLevelItem(k) 
                
                childCount = topLevelItem.childCount()
                
                for c in range(childCount):
                    child = self.historyTreeWidget.topLevelItem(k).child(c)
                    child.setSelected(False)
                    
                    
                if p is not None:
                    items_text_list = list(zip(*[(topLevelItem.child(k).text(0), topLevelItem.child(k).text(1)) for k in range(childCount)]))
                    
                    if len(items_text_list) == 2:
                        found_text = [s for s in filter(p.match, items_text_list[1])]
                        
                        within_session_indices = [int(items_text_list[0][items_text_list[1].index(s)]) for s in found_text]
                        
                        selected_children = [topLevelItem.child(k-1) for k in within_session_indices if topLevelItem.child(k-1) is not None]
                        
                        if len(selected_children):
                            topLevelItem.setExpanded(True)
                        
                        else:
                            topLevelItem.setExpanded(False)

                        for item in selected_children:
                            item.setSelected(True)
                            
                    else:
                        topLevelItem.setExpanded(False)
                        
                else:
                    topLevelItem.setExpanded(False)
                    
            self.historyTreeWidget.setSelectionMode(original_selection_mode)
            
        except:
            self.historyTreeWidget.setSelectionMode(original_selection_mode)
        
            
    @pyqtSlot()
    @safeWrapper
    def slot_addCommandFindToHistory(self):
        cmdTxt = self.commandFinderComboBox.lineEdit().text()
        if len(cmdTxt) > 0 and cmdTxt not in self._commandHistoryFinderList:
            self._commandHistoryFinderList.appendleft(cmdTxt)
            self.lastCommandFind = cmdTxt
    
    
    @pyqtSlot()
    @safeWrapper
    def slot_removeItemFromCommandFinderHistory(self):
        currentNdx = self.commandFinderComboBox.currentIndex()
        cmdTxt = self.commandFinderComboBox.itemText(currentNdx)
        if cmdTxt in self._commandHistoryFinderList:
            self._commandHistoryFinderList.remove(cmdTxt)
            
        self.commandFinderComboBox.removeItem(currentNdx)
        self.commandFinderComboBox.lineEdit().setClearButtonEnabled(True)
    
    @pyqtSlot()
    @safeWrapper
    def slot_removeDirFromHistory(self):
        signalBlocker = QtCore.QSignalBlocker(self.directoryComboBox)
        currentNdx = self.directoryComboBox.currentIndex()
        dirTxt = self.directoryComboBox.itemText(currentNdx)
        if dirTxt in self.recentDirectories:
            self.recentDirectories.remove(dirTxt)
            
        self.directoryComboBox.removeItem(currentNdx)
        self.directoryComboBox.lineEdit().setClearButtonEnabled(True)
        
    @pyqtSlot()
    @safeWrapper
    def slot_clearRecentDirList(self):
        signalBlocker = QtCore.QSignalBlocker(self.directoryComboBox)
        self._clearRecentDirectories_()
        self.directoryComboBox.clear()
    
    @pyqtSlot()
    @safeWrapper
    def slot_removeFileFilterFromHistory(self):
        currentNdx = self.fileSystemFilter.currentIndex()
        filterTxt = self.fileSystemFilter.itemText(currentNdx)
        
        signalBlocker = QtCore.QSignalBlocker(self.fileSystemFilter)
        
        if filterTxt in self.fileSystemFilterHistory:
            self.fileSystemFilterHistory.remove(filterTxt)
        
        self.fileSystemFilter.removeItem(currentNdx)
        self.fileSystemFilter.lineEdit().setClearButtonEnabled(True)
        
    @pyqtSlot()
    @safeWrapper
    def slot_clearFileFilterHistory(self):
        signalBlocker = QtCore.QSignalBlocker(self.fileSystemFilter)
        self.fileSystemFilterHistory.clear()
        self.fileSystemFilter.clear()
        self.fileSystemFilter.lineEdit().setClearButtonEnabled(True)
        

    @pyqtSlot(str)
    @safeWrapper
    def slot_setFileNameFilter(self, val):
        if len(val) == 0:
            self.fileSystemModel.setNameFilters([])
            self.lastFileSystemFilter=""
            if "" not in self.fileSystemFilterHistory:
                self.fileSystemFilterHistory.appendleft("")
            
        else:
            #print("file filter %s" % val)
            self.fileSystemModel.setNameFilters(val.split())
            
            if val not in self.fileSystemFilterHistory: # and len(self.fileSystemFilterHistory) < 10:
                self.fileSystemFilterHistory.appendleft(val)
                
            self.lastFileSystemFilter=val
        
    @pyqtSlot(QtCore.QModelIndex)
    @safeWrapper
    def slot_resizeFileTreeViewFirstColumn(self, ndx):
        self._resizeFileColumn_()
    
    @pyqtSlot(str)
    @safeWrapper
    def slot_resizeFileTreeColumnForPath(self, path):
        self._resizeFileColumn_()
    
    def _resizeFileColumn_(self):
        self.fileSystemTreeView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.fileSystemTreeView.resizeColumnToContents(0)
        self.fileSystemTreeView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        
    def _resizeWorkspaceViewFirstColumn_(self):
        self.workspaceView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.workspaceView.resizeColumnToContents(0)
        self.workspaceView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        
    def _sortWorkspaceViewFirstColumn_(self):
        # NOTE: 2019-12-01 13:41:41 
        # preserve the sort order and section as chosen by the user
        sortOrder = None
        sortSection = 0
        
        if self.workspaceView.horizontalHeader().isSortIndicatorShown():
            try:
                sortSection = self.workspaceView.horizontalHeader().sortIndicatorSection()
                sortOrder = self.workspaceView.horizontalHeader().sortIndicatorOrder()
            except:
                sortSection = 0
                sortOrder = QtCore.Qt.AscendingOrder
                
        if not isinstance(sortOrder, QtCore.Qt.SortOrder):
            sortOrder = QtCore.Qt.AscendingOrder
            
        self.workspaceView.setSortingEnabled(False)
        self.workspaceView.sortByColumn(sortSection,sortOrder)
        self.workspaceView.setSortingEnabled(True)
        
    
    @pyqtSlot(QtCore.QModelIndex)
    @safeWrapper
    def slot_fileSystemItemActivated(self, ndx):
        """ Signal activated from self.fileSystemTreeView is connected to this.
        Triggered by double-click on an item in the file system tree view.
        """
        #print(self.fileSystemModel.filePath(ndx))
        if self.fileSystemModel.isDir(ndx):
            # if this is a directory then chdir to it
            self.slot_changeDirectory(self.fileSystemModel.filePath(ndx))
            
        else:
            # if this is a regular file then try to load (open) it
            self.loadFile(self.fileSystemModel.filePath(ndx))
            
    @pyqtSlot(str)
    @safeWrapper
    def slot_chDirString(self, val):
        if "://" in val:
            protocol, target = val.split("://")
        else:
            target = val
        #print("ScipyenWindow.slot_chDirString: \nval = %s; \nprotocol = %s; \ntarget = %s" % (val, protocol, target))
        self.slot_changeDirectory(target)
        
    @pyqtSlot()
    @safeWrapper
    def slot_changeDirectory(self, targetDir=None):
        #print(f"MainWindow.slot_changeDirectory(targetDir = {targetDir})")
        if targetDir is None:
            if isinstance(self.sender(), QtWidgets.QAction):
                targetDir = str(self.sender().text())
                
                
        if isinstance(targetDir, str) and "&" in targetDir:
            # NOTE: 2017-03-04 16:08:17 because for whatever reason PyQt5 also 
            # returns the shortcut indicator character '&'
            targetDir = targetDir.replace('&','') 
                
        if targetDir is None or (isinstance(targetDir, str) and len(targetDir.strip()) == 0) or not os.path.exists(targetDir):
            targetDir = os.getenv("USERPROFILE") if sys.platform == "win32" else os.getenv("HOME")
        
        if targetDir is not None and targetDir != "" and os.path.exists(targetDir):
            if os.path.isfile(targetDir):
                targetDir = os.path.dirname(targetDir)
                
            try:
                self.navPrevDir.appendleft(os.getcwd())
                
            except:
                pass

            if sys.platform == "win32":
                targetDir = targetDir.replace("\\", "/")
                targetDir = rf"{targetDir}"

            #print(f"MainWindow.slot_changeDirectory targetDir = {targetDir}")

            if self.ipkernel is not None and self.shell is not None and self.console is not None:
                #print(''.join(["cd '", targetDir, "'"]))
                #if sys.platform == "linux":
                    #self.console.execute(''.join(["cd '", targetDir, "'"]), hidden=True)
                #else:
                    #self.console.execute(''.join(["os.chdir('", targetDir, "')"]), hidden=False)

                self.console.execute(''.join(["os.chdir('", targetDir, "')"]), hidden=True)

                #self.console.execute(''.join(["cd '", targetDir, "'"]), hidden=True if sys.platform=="linux" else False)

            if self.external_console:
                self.external_console.execute("".join(["os.chdir('", targetDir,"')"]))
                
            self._setRecentDirectory_(targetDir)
            
            self._updateFileSystemView_(targetDir, True)
            
            #self.fileSystemModel.setRootPath(targetDir)
            #self.fileSystemTreeView.scrollTo(self.fileSystemModel.index(targetDir))
            #self.fileSystemTreeView.setRootIndex(self.fileSystemModel.index(targetDir))
            #self.fileSystemTreeView.sortByColumn(0, QtCore.Qt.AscendingOrder)

            self.currentDir = targetDir
            self.currentDirLabel.setText(targetDir)
            mpl.rcParams["savefig.directory"] = targetDir
            self.setWindowTitle("Scipyen %s" % targetDir)
            
    def _updateFileSystemView_(self, targetDir, cd=True):
        self.fileSystemModel.setRootPath(targetDir)
        self.fileSystemTreeView.scrollTo(self.fileSystemModel.index(targetDir))
        if cd:
            self.fileSystemTreeView.setRootIndex(self.fileSystemModel.index(targetDir))
        else:
            self.fileSystemTreeView.setCurrentIndex(self.fileSystemModel.index(targetDir))
        self.fileSystemTreeView.sortByColumn(0, QtCore.Qt.AscendingOrder)
        # NOTE 2017-07-04 15:59:38
        # for this to work one has to set horizontalScrollBarPolicy
        # to ScrollBarAlwaysOff (e.g in QtDesigner)
        self._resizeFileColumn_()
        
            
    @safeWrapper
    def _setRecentDirectory_(self, newDir):
        if newDir in self.recentDirectories:
            # move newDir to top of stack
            if newDir != self.recentDirectories[0]:
                self.recentDirectories.remove(newDir)
                self.recentDirectories.appendleft(newDir)
                #self._refreshRecentDirs_()
                
        else:
            # add Newdir, 
            if len(self.recentDirectories) == self._maxRecentDirectories:
                self.recentDirectories.pop()

            self.recentDirectories.appendleft(newDir)
            
        self._refreshRecentDirs_()
        
    @safeWrapper
    def _sendFileNamesToConsole_(self, *args):
        #print(args)
        selectedItems = [item for item in self.fileSystemTreeView.selectedIndexes() if  not self.fileSystemModel.isDir(item)]# list of QModelIndex
        
        nItems = len(selectedItems)
        if nItems == 0:
            return
        
        itemNames = ['"'+self.fileSystemModel.filePath(item)+'"' for item in selectedItems]
        
        self.app.clipboard().setText(',\n'.join(itemNames))
        self.console.paste()
        
    @pyqtSlot()
    @safeWrapper
    def slot_importPrairieView(self):
        #from systems.PrairieView import PrairieViewImporter # PrairieView already imported as module
        # NOTE: 2021-04-18 12:25:11
        # must absolutely pass reference to self as parent so that in Qt/C++ side
        # pvimp object is owned by self; otherwise, the garbage collector will
        # free its memory allocation when it goes out of scope at the end of this
        # function - see also scipyen systems.PrairieView.PrairieViewImporter
        # constructor
        pvimp = PrairieView.PrairieViewImporter(parent=self)
        # NOTE: 2021-04-18 12:27:23
        # one can also directly set pvimp.auto_export = True to automatically
        # export the generated ScanData directly to workspace and thus avoiding 
        # the extra slot below
        pvimp.finished[int].connect(self._slot_prairieViewImportGuiDone)
        pvimp.open()
        
    @pyqtSlot(int)
    @safeWrapper
    def _slot_prairieViewImportGuiDone(self, value):
        #if value == QtWidgets.QDialog.Accepted:
        if value:
            dlg = self.sender()
            if dlg is not None:
                self.assignToWorkspace(dlg.scanDataVarName, dlg.scandata)
        
    @pyqtSlot()
    @safeWrapper
    def slot_importDataFrame(self):
        selectedItems = [item for item in self.fileSystemTreeView.selectedIndexes() \
                         if item.column() == 0 and not self.fileSystemModel.isDir(item)]# list of QModelIndex
        
        if len(selectedItems) == 0:
            return
        
        fileNames = [self.fileSystemModel.filePath(i) for i in selectedItems]
        
        nItems = len(fileNames)
        
        if nItems == 1:
            self.loadDiskFile(fileNames[0], pio.importDataFrame)
            
        else:
            progressDlg = QtWidgets.QProgressDialog("Opening files...", "Abort", 0, nItems, self)
            
            progressDlg.setWindowModality(QtCore.Qt.WindowModal)
            
            for (k, item) in enumerate(selectedItems):
                if (self.loadDiskFile(self.fileSystemModel.filePath(item)), pio.importDataFrame):
                    progressDlg.setValue(k)
                    
                else:
                    progressDlg.cancel()
                    progressDlg.reset()
                    
                if progressDlg.wasCanceled():
                    break
                    
            if progressDlg.value == 0:
                return False
                    
            progressDlg.setValue(nItems)
        
        self.workspaceModel.update()
        
        return True
         
    @pyqtSlot()
    @safeWrapper
    def slot_openSelectedFileItems(self):
        selectedItems = [item for item in self.fileSystemTreeView.selectedIndexes() \
                         if item.column() == 0 and not self.fileSystemModel.isDir(item)]# list of QModelIndex
        
        
        nItems = len(selectedItems)

        if nItems == 0:
            return False
        
        # NOTE: 2018-09-27 10:11:49
        # prevent user interaction when only one item (which may take a while to
        # load especially if it is a big file)
        
        if nItems == 1:
            #QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
            self.setCursor(QtCore.Qt.WaitCursor)
            
            self.loadDiskFile(self.fileSystemModel.filePath(selectedItems[0]))
            
            #QtWidgets.QApplication.restoreOverrideCursor()
            self.unsetCursor()
            
        else:
            progressDlg = QtWidgets.QProgressDialog("Opening files...", "Abort", 0, nItems, self)
            
            progressDlg.setWindowModality(QtCore.Qt.WindowModal)
            
            for (k, item) in enumerate(selectedItems):
                # NOTE: 2020-10-27 09:28:35
                # do not add batch-loaded files to list of recent files - speed
                # things up
                if (self.loadDiskFile(self.fileSystemModel.filePath(item), addToRecent=False)):
                    progressDlg.setValue(k)
                    
                else:
                    progressDlg.cancel()
                    progressDlg.reset()
                    
                if progressDlg.wasCanceled():
                    break
                    
            if progressDlg.value == 0:
                return False
                    
            progressDlg.setValue(nItems)
        
        self.workspaceModel.update()
        
        return True
    
    @pyqtSlot()
    @safeWrapper
    def slot_showFilesFilter(self):
        self.filesFilterFrame.setVisible(True)
        
    @pyqtSlot()
    @safeWrapper
    def slot_hideFilesFilter(self):
        self.filesFilterFrame.setVisible(False)
        
    @pyqtSlot(str)
    @safeWrapper
    def _slot_runPythonScriptFromManager(self, fileName):
        if os.path.isfile(fileName):
            self._temp_python_filename_ = fileName
            self._slot_runPythonSource()
            
    @pyqtSlot(str)
    @safeWrapper
    def _slot_importPythonScriptFromManager(self, fileName):
        if os.path.isfile(fileName):
            self._temp_python_filename_ = fileName
            self._slot_importPythonModule()
            
    @pyqtSlot(str)
    @safeWrapper
    def slot_systemEditScript(self, fileName):
        if os.path.exists(fileName) and os.path.isfile(fileName):
            url = QtCore.QUrl.fromLocalFile(fileName)
            QtGui.QDesktopServices.openUrl(url)
            #QtGui.QDesktopServices.openUrl(QtCore.QUrl("file://%s" % fileName))
        
    @pyqtSlot(str)
    @safeWrapper
    def slot_systemOpenFileOrFolder(self, fileName):
        if isinstance(fileName, str) and len(fileName.strip()):
            if os.path.exists(fileName):
                url = QtCore.QUrl.fromLocalFile(fileName)
                QtGui.QDesktopServices.openUrl(url)
                
        elif isinstance(fileName, QtCore.QUrl) and fileName.isValid() and fileName.isLocalFile():
            QtGui.QDesktopServices.openUrl(fileName)
            
    @pyqtSlot(object)
    @safeWrapper
    def slot_systemOpenUrl(self, urlobj):
        if isinstance(urlobj, QtCore.QUrl) and urlobj.isValid():
            if urlobj.isRelative():
                url = QtCore.QUrl.resolved(urlobj)
                QtGui.QDesktopServices.openUrl(url)
                
            else:
                QtGui.QDesktopServices.openUrl(urlobj)
                
        elif isinstance(urlobj, str) and len(urlobj.strip()):
            url = QtCore.QUrl(urlobj)
            if url.isValid():
                QtGui.QDesktopServices.openUrl(url)
            
    @pyqtSlot()
    @safeWrapper
    def slot_systemOpenParentFolderForSelectedItems(self):
        selectedItems = [item for item in self.fileSystemTreeView.selectedIndexes() \
                         if item.column() == 0]# list of QModelIndex
        
        parentFolders = unique([os.path.dirname(self.fileSystemModel.filePath(item)) for item in selectedItems])
        
        for folder in parentFolders:
            self.slot_systemOpenFileOrFolder(folder)
            
    @pyqtSlot(str)
    @safeWrapper
    def slot_systemOpenParentFolder(self, fileName):
        if isinstance(fileName, str):
            if os.path.exists(fileName):
                QtGui.QDesktopServices.openUrl(QtCore.QUrl("file://%s" % os.path.dirname(fileName)))
                #if os.path.isfile(fileName):
                    #QtGui.QDesktopServices.openUrl(QtCore.QUrl("file://%s" % os.path.dirname(fileName)))
                    
                #else:
                    #QtGui.QDesktopServices.openUrl(QtCore.QUrl("file://%s" % fileName))
                    
        elif isinstance(fileName, QtCore.QUrl) and fileName.isValid() and fileName.isLocalFile():
            if fileName.isRelative():
                url = QtCore.QUrl.resolved(fileName)
                
            else:
                url = fileName
                
            #u_fileName = url.fileName()
            u_path = url.adjusted(QtCore.QUrl.RemoveFilename)#.path()
            QtGui.QDesktopServices.openUrl(u_path)
                
        
    @pyqtSlot(str)
    @safeWrapper
    def _slot_pastePythonScriptFromManager(self, fileName):
        if os.path.isfile(fileName):
            self._temp_python_filename_ = fileName
            self._slot_python_code_to_console()
        
    @pyqtSlot()
    @safeWrapper
    def _slot_runRecentPythonScript_(self):
        if isinstance(self.sender(), QtWidgets.QAction):
            s_name = str(self.sender().text())
            
            if "&" in s_name:
                s_name = s_name.replace("&", "")
                
            s_paths = [key for key,value in self._recent_scripts_dict_.items() if value == s_name]
            
            if len(s_paths) == 0:
                warnings.warn("Path for script %s not found" % s_name)
                return
            
            if len(s_paths) > 1:
                warnings.warn("Script %s is mapped to multiple files; the first in list will be used" % s_name)
            
            if os.path.isfile(s_paths[0]):
                self._temp_python_filename_ = s_paths[0]
            
                if bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier):
                    self._slot_python_code_to_console()
                else:
                    self._slot_runPythonSource()
        
    @pyqtSlot()
    @safeWrapper
    def slot_pastePythonScript(self, fileName=None):
        if not isinstance(fileName, str) or len(fileName) == 0:
            targetDir = self.recentDirectories[0]
            if targetDir is not None and targetDir != "" and os.path.exists(targetDir):
                fileName = QtWidgets.QFileDialog.getOpenFileName(self, caption=u"Run python script", filter="Python script (*.py)", directory = targetDir)
            else:
                fileName = QtWidgets.QFileDialog.getOpenFileName(self, caption=u"Run python script", filter="Python script (*.py)")
            
        if len(fileName) > 0:
            if isinstance(fileName, tuple):
                fileName = fileName[0] # NOTE: PyQt5 QFileDialog.getOpenFileName returns a tuple (fileName, filter string)
                
            if isinstance(fileName, str) and len(fileName) > 0 and os.path.isfile(fileName):
                # TODO check if this is a legitimate ASCII file containing python code
                self._run_python_source_code_(fileName, paste=True)
                #self._temp_python_filename_ = fileName
                #self._slot_python_code_to_console()
                
                if fileName not in self.recentScripts:
                    self.recentScripts.appendleft(fileName)
                    self._refreshRecentScriptsMenu_()
                    
                else:
                    if fileName != self.recentScripts[0]:
                        self.recentScripts.remove(fileName)
                        self.recentScripts.appendleft(fileName)
                        self._refreshRecentScriptsMenu_()
                        
    @pyqtSlot()
    @safeWrapper
    def slot_showScriptsManagerWindow(self):
        self.scriptsManager.setData(self._recent_scripts_dict_)
        self.scriptsManager.setVisible(True)
        #self.scriptsManager.exec_()
        
    @pyqtSlot()
    @safeWrapper
    def slot_runPythonScript(self, fileName=None):
        if not isinstance(fileName, str) or len(fileName) == 0:
            targetDir = self.recentDirectories[0]
            
            if targetDir is not None and targetDir != "" and os.path.exists(targetDir):
                fileName = QtWidgets.QFileDialog.getOpenFileName(self, caption=u"Run python script", filter="Python script (*.py)", directory = targetDir)
            else:
                fileName = QtWidgets.QFileDialog.getOpenFileName(self, caption=u"Run python script", filter="Python script (*.py)")
            
        if len(fileName) > 0:
            if isinstance(fileName, tuple):
                fileName = fileName[0] # NOTE: PyQt5 QFileDialog.getOpenFileName returns a tuple (fileName, filter string)
                
            if isinstance(fileName, str) and len(fileName) > 0 and os.path.isfile(fileName):
                # TODO check if this is a legitimate ASCII file containing python code
                self._run_python_source_code_(fileName, paste=False)
                
                if fileName not in self.recentScripts:
                    self.recentScripts.appendleft(fileName)
                    self._refreshRecentScriptsMenu_()
                    
                else:
                    if fileName != self.recentScripts[0]:
                        self.recentScripts.remove(fileName)
                        self.recentScripts.appendleft(fileName)
                        self._refreshRecentScriptsMenu_()
                        
    @pyqtSlot(str, QtCore.QPoint)
    @safeWrapper
    def slot_handlePythonTextFile(self, path, pos):
        if os.path.isfile(path):
            self._temp_python_filename_ = path
            
            cm = QtWidgets.QMenu("Handle python source file", self.sender())
            
            loadAsText = cm.addAction("Load As Text")
            loadAsText.triggered.connect(self._slot_openNamedFile_)
            
            loadInBuffer = cm.addAction("Send To Console")
            loadInBuffer.triggered.connect(self._slot_python_code_to_console)
            
            runAsPython = cm.addAction("Run")
            runAsPython.triggered.connect(self._slot_runPythonSource)
            
            cm.addSeparator()
            
            registerWithManager = cm.addAction("Register")
            registerWithManager.triggered.connect(self._slot_registerPythonSource_)
            
            
            # NOTE 2019-09-14 09:22:54
            # FIXME there are some cavetas to this
            #cm.addSeparator()
            
            #importAsModule = cm.addAction("Import As Module")
            #importAsModule.triggered.connect(self._slot_importPythonModule)
            
            cm.popup(self.sender().mapToGlobal(pos), loadAsText)
        
    @safeWrapper
    def loadFile(self, fName):
        """ Entrypoint into the file reading system, for calls from file system tree view
        Called by: 
            self.slot_fileSystemItemActivated
            
        Delegates to self.loadDiskFile(file_name, fileReader)
        """
        if self.loadDiskFile(fName):
            #self._addRecentFile_(fName, fileReader) # done inside loadDiskFile
            self.workspaceModel.update()
            
    #@safeWrapper
    #def saveVariables(self):
        #pass
            
    @pyqtSlot()
    @safeWrapper
    def slot_loadRecentFile(self):
        '''
        Common slot for any action in Recent Files submenu.
        The item text (as is appears in the GUI) is the fully qualified path name
        of the file.
        The function uses this text to obtain the opening mode from self.recentFiles
        dictionary, then delegates to self.loadDiskFile. The opening mode is used 
        inside self.loadDiskFile to select the appropriate file opening code.
        '''
        action = self.sender()
        if isinstance(action, QtWidgets.QAction):
            fName = str(action.text()).replace('&','')
            fileReader = self.recentFiles[fName]

            if self.loadDiskFile(fName, fileReader):
                self.workspaceModel.update()
                
    @pyqtSlot(str)
    @safeWrapper
    def slot_rootPathChanged(self, newPath):
        pass
        #print("MainWindow new root path", newPath)
                
    @safeWrapper
    def slot_selectWorkDir(self):
        targetDir = self.recentDirectories[0]
        caption = "Select Working Directory"
        if targetDir is not None and targetDir != "" and os.path.exists(targetDir):
            dirName = str(QtWidgets.QFileDialog.getExistingDirectory(self, caption=caption, directory=targetDir))
            #dirName = str(QtWidgets.QFileDialog.getExistingDirectory(self, caption=u'Select Working Directory', directory=targetDir))
        else:
            dirName = str(QtWidgets.QFileDialog.getExistingDirectory(self, caption=caption))
            #dirName = str(QtWidgets.QFileDialog.getExistingDirectory(self, caption=u'Select Working Directory'))
            
        if len(dirName) > 0:
            self.slot_changeDirectory(dirName)
            
    @safeWrapper
    def loadDiskFile(self, fName, fileReader=None, addToRecent=True):
        """Common delegate for reading data from a file.
        
        Currently only opens image files and axon "ABF files". 
        TODO: pickle, hdf5, matlab, etc
        
        Called by various slots connected to File menu actions. 
        
        Arguments:
        
        fName -- fully qualified data file name
        
        fileReader -- (optional, default is None) a str that specifies a specialized
            file reader function in the iolib.pictio module
            
            reader (currently, only "vigra" or "bioformats"), or a 
            boolean, where a value of False chooses the vigra impex 
            library, whereas True chooses the bioformats library.
            
            When None, this functions assumes that an image is to be loaded.
            TODO: Guess file type for other data file types as well.
            
            The file reader is chosen between vigra and bioformats,
            according to the file extension. TODO: use other readers as well.
            
            Other planned readers are hdf5, pickle, matlab, 
            
            NOTE: For image files, this only reads the image pixels. Currently, image metadata 
            is only read through the bioformats library (as OME XML document)
            
            TODO: Supply other possible image readers?
    
        
        """
        
        # 2016-08-15 16:20:24
        # TODO: give the user the possibility to open image data and image metadata SEPARATELY
        # for now, they are returned both, for convenience
        
        try:
            (bName, fileExt) = os.path.splitext(os.path.basename(fName))
            
            # NOTE: 2017-06-21 15:59:41
            # fix insane file names 
            bName = strutils.str2symbol(bName)
            
            #print("loadDiskFile", fName)
            #print("to assign to ", bName)
            
            
            if fileReader is None:
                fileReader = pio.getLoaderForFile(fName)
                
            #print("fileReader", fileReader)
            
            if fileReader is None:
                return False
            
            reader_signature = inspect.signature(fileReader)
            
            # NOTE: 2020-02-18 12:24:38
            # return_types is inspect.Signature.empty when the function has no
            # annotated return signature; otherwise, is a:
            # a) type - when the function returns a variable of determined type 
            #   (this includes NoneType)
            # b) sequence
            #   all elements are types when the function returns either:
            #   b.1) a sequence of variables, each with a determined type
            #   b.2) a single variable with one of several possible types
            #   SOME of its elements are sequences of types => the function
            #   returns a sequence of variables, SOME of which can have one of
            #   several possible types (contained in the sequence elements of the
            #   return_types)
            return_types = reader_signature.return_annotation
            
            #print("return_types", return_types)
            
            data = fileReader(fName)
            
            #print("loaded data", data)
            
            if return_types is inspect.Signature.empty:
                # no return annotation
                self.workspace[bName] = data
                
            else:
                # see NOTE: 2020-02-18 12:24:38
                if isinstance(return_types, type): 
                    # case (a) in NOTE: 2020-02-18 12:24:38
                    if type(data) != return_types:
                        warnings.warn("Unexpected return type (%s); expecting %s from %s" % (type(data).__name__, type(return_types).__name__, fileReader))
                        
                    self.workspace[bName] = data
                    
                else:
                    if isinstance(return_types, (tuple, list)):
                        if isinstance(data, (tuple, list)):
                            # case (b) in NOTE: 2020-02-18 12:24:38
                            if len(return_types) != len(data):
                                warnings.warn("Unexpected number of return variables (%d); expecting %d from %s" % (len(data), len(return_types), fileReader))
                                self.workspace[bName] = data
                                
                            else:
                                for k,d in enumerate(data):
                                    if isinstance(return_types[k], type):
                                        if type(data[k]) != return_types[k]:
                                            warnings.warn("Unexpected return type (%s) for %dth variable; expecting %s, in %s" % (type(data[k]).__name__, k, type(return_types[k]).__name__, fileReader))
                                            self.workspace[bName] = data
                                            break
                                            
                                    elif isinstance(return_types[k], (tuple, list)) and all([isinstance(rt, type) for rt in return_types[k]]):
                                        if type(data[k]) not in return_types[k]:
                                            warnings.warn("Unexpected return type (%s) for %dth variable; expecting %s, in %s" % (type(data[k]).__name__, k, str(return_types[k]), fileReader))
                                            self.workspace[bName] = data
                                            break
                                            
                                    else:
                                        warnings.warn("Cannot interpret the return signature of %s" % fileReader)
                                        self.workspace[bName] = data
                                        break
                                        
                                    if k == 0:
                                        self.workspace[bName] = data[k]
                                    else:
                                        name = "%s_%s_%d" % (bName, "var", k)
                                        self.workspace[name] = data[k]
                                        
                        else:
                            if type(data) not in return_types[0]:
                                # TODO / FIXME
                                warnings.warn("Data type %s is not listed in the return signature of %s" % (type(data), fileReader))
                                
                            self.workspace[bName] = data
                                        
            if addToRecent:
                self._addRecentFile_(fName, fileReader)
            
            ret = True
            
        except Exception as e:
            traceback.print_exc()
            excInfo = sys.exc_info()
            tbStrIO = io.StringIO()

            #traceback.print_exception(excInfo[0], excInfo[1], excInfo[2], file=tbStrIO)
            
            excStr = tbStrIO.getvalue()
            
            tbStrIO.close()
            
            excStr.replace(":", ":\n")
            
            excStr.replace("File ", "\nFile ")
            
            excStr.replace("in ", "\nin ")
            
            excStr.replace(")", ")\n")
            
            errMsgDlg = QtWidgets.QErrorMessage(self)

            errMsgDlg.setWindowTitle(excInfo[0].__name__)
            errMsgDlg.showMessage(excStr) # python3 way
            ret = False

        return ret
    
    def _saveImageFile_(self, data, fName):
        try:
            pio.saveImageFile(data, fName)
            ret = True
            
        except Exception as e:
            errMsgDlg = QtWidgets.QErrorMessage(self)
            errMsgDlg.setWindowTitle("Exception")
            errMsgDlg.showMessage(e.message)
            ret = False

        return ret
    
    @pyqtSlot()
    @safeWrapper
    def slot_saveFile(self):
        """Saves data to file.
        
        If one variable is selected in the workspace, opens a dialog to save it
        to a specific file type e.g., VigraArrays are saved as images or volumes
        (according to their dimensions, see pictio.saveImageFile),
        other data types are saved as a Python pickle file i.e., are serialized.
            
            
        If more than one variable is selected, then calls slot_saveSelectedVariables
        where all selected vars are serialised individually to pickle files.
        
        TODO If no variable is selected then offer to save the workspace contents to
        a HDF5 file (as a dict!!!)
            
            
        
        """
        selectedItems = self.workspaceView.selectedIndexes()
        
        if len(selectedItems) == 0:
            return
        
        elif len(selectedItems) == 1:
            # make sure we get the data in the first column (the variable name) 
            varname = self.workspaceModel.item(selectedItems[0].row(),0).text()
            
            if type(self.workspace[varname]).__name__ == 'VigraArray':
                fileFilters = list()
                fileFilters.append("HDF5 (*.h5)")
                imageFileFilters = list()
                imageFileFilters.append('All Image Types ('+ ' '.join([''.join(i) for i in zip('*' * len(pio.SUPPORTED_IMAGE_TYPES), '.' * len(pio.SUPPORTED_IMAGE_TYPES), pio.SUPPORTED_IMAGE_TYPES)]) + ')')
                imageFileFilters.extend(['{I} (*.{i})'.format(I=i.upper(), i=i) for i in pio.SUPPORTED_IMAGE_TYPES])
                fileFilters.extend(imageFileFilters)
                fileFilters.append("Pickle (*pkl)")
                fileFilt = ';;'.join(fileFilters)
                
                #fileFilt = 'All Image Types (' + ' '.join([''.join(i) for i in zip('*' * len(pio.SUPPORTED_IMAGE_TYPES), '.' * len(pio.SUPPORTED_IMAGE_TYPES), pio.SUPPORTED_IMAGE_TYPES)]) + ');;' +\
                            #';;'.join('{I} (*.{i});;'.format(I=i.upper(), i=i) for i in pio.SUPPORTED_IMAGE_TYPES)
                
                targetDir = self.recentDirectories[0]
                
                if targetDir is not None and targetDir != "" and os.path.exists(targetDir):
                    fileName, file_flt = str(QtWidgets.QFileDialog.getSaveFileName(self, caption=u'Save Image File', filter=fileFilt, directory = targetDir))
                    
                else:
                    fileName, file_flt = str(QtWidgets.QFileDialog.getSaveFileName(self, caption=u'Save Image File', filter=fileFilt))

                if len(fileName) > 0:
                    data = self.workspace[varname]
                    if file_flt in imageFileFilters:
                        if self._saveImageFile_(data, fileName):
                            self._addRecentFile_(fileName)
                            
                    else:
                        if file_flt.startswith("HDF5"):
                            pio.saveHDF(data, varname)
                        
                        else:
                            pio.savePickleFile(data,varname)
                        
                        
            else:
                fileFilters = list()
                fileFilters.append("HDF5 (*.h5)")
                fileFilters.append("Pickle (*pkl)")
                fileFilt = ';;'.join(fileFilters)
                targetDir = self.recentDirectories[0]
                
                if targetDir is not None and targetDir != "" and os.path.exists(targetDir):
                    fileName, file_flt = str(QtWidgets.QFileDialog.getSaveFileName(self, caption=u'Save Image File', filter=fileFilt, directory = targetDir))
                    
                else:
                    fileName, file_flt = str(QtWidgets.QFileDialog.getSaveFileName(self, caption=u'Save Image File', filter=fileFilt))


                if len(fileName) > 0:
                    data = self.workspace[varname]
                    if file_flt.startswith("HDF5"):
                        pio.saveHDF5(data, varname)
                    
                    else:
                        pio.savePickleFile(data,varname)
                #errMsgDlg = QtWidgets.QErrorMessage(self)
                #errMsgDlg.setWindowTitle("Not implemented for this variable type")
                #errMsgDlg.showMessage("Not implemented for this variable type")
                
        
        else:
            self.slot_saveSelectedVariables()
        
            
    # NOTE: 2016-04-01 11:09:49
    # file dialog filtered on all supported image file formats
    # check is selected file format supported by vigra and use vigra impex to open
    # else use bioformats to open
    # NOTE: 2016-04-01 11:48:52
    # use list comprehension to construct filter
    #@_workspaceModifier # NOTE: 2016-05-02 20:46:58 not used anymore here
    @pyqtSlot()
    @safeWrapper
    def openFile(self):
        '''Slot to which File Open typically connects to.
        # TODO: merge with file openers for the fileSystemTreeView
        Prompts user to choose a file using a File Open dialog
        '''
        # 2016-08-11 13:48:19
        # NOTE: the API for getOpenFileName has changed for Qt 5
        #If you want multiple filters, separate them with ';;', for example:
        #"Images (*.png *.xpm *.jpgui);;Text files (*.txt);;XML files (*.xml)"
        
        from core.utilities import make_file_filter_string
        
        if self.slot_openSelectedFileItems():
            return
        
        (allImageTypesFilter, individualImageTypeFilters) = make_file_filter_string(pio.SUPPORTED_IMAGE_TYPES, 'All Image Types')

        allMimeTypes = ";;".join([i[0] + " (" + i[1] + ") " for i in zip(pio.mimetypes.types_map.values(), pio.mimetypes.types_map.keys())])
        
        filesFilterString = ';;'.join(["All file types (*.*)", allImageTypesFilter, individualImageTypeFilters, allMimeTypes])
                
        targetDir = self.recentDirectories[0]
        
        if targetDir is not None and targetDir != "" and os.path.exists(targetDir):
            fileName = QtWidgets.QFileDialog.getOpenFileName(self, caption=u'Open File', filter=filesFilterString, directory=targetDir)
            
        else:
            fileName = QtWidgets.QFileDialog.getOpenFileName(self, caption=u'Open File', filter=filesFilterString)

        if len(fileName) > 0:
            
            if isinstance(fileName, tuple):
                fileName = fileName[0] # NOTE: PyQt5 QFileDialog.getOpenFileName returns a tuple (fileName, filter string)
                
            #print("fileName: ", fileName)
                
            if isinstance(fileName, str) and len(fileName) > 0:
                if self.loadDiskFile(fileName):
                    self._addRecentFile_(fileName)
                    self.workspaceModel.update()
                
    # NOTE: 2016-04-01 12:18:23
    # keep this as we may want to enforce the use of BioFormats for opening files
    #@_workspaceModifier # NOTE: 2016-05-02 20:46:45 decorator not used anymore here
    #
    # 2016-08-11 14:13:24
    # NOTE: see NOTE above loadImageFile(self):
    #@pyqtSlot()
    #def loadBioFormatsImageFile(self):
        #'''Slot to which an item in the File typically connects to.
        
        #Prompts user to choose a file using a File Open dialog.

        #'''
        #from utilities import make_file_filter_string
        
        #(allImageTypesFilter, individualImageTypeFilters) = make_file_filter_string(bf.READABLE_FORMATS, 'BioFormats Image Types')

        #filesFilterString = ';;'.join([allImageTypesFilter, individualImageTypeFilters])
                
        #bf_extensions = bf.READABLE_FORMATS
        
      
        #targetDir = self.recentDirectories[0]
        
        #if targetDir is not None and targetDir != "" and os.path.exists(targetDir):
            #fileName = QtWidgets.QFileDialog.getOpenFileName(self, caption=u'Open Image File Using BioFormats', filter=filesFilterString, directory=targetDir)
        #else:
            #fileName = QtWidgets.QFileDialog.getOpenFileName(self, caption=u'Open Image File Using BioFormats', filter=filesFilterString)
        
        #if len(fileName) > 0:
            #if isinstance(fileName, tuple):
                #fileName = fileName[0] # NOTE: PyQt5 QFileDialog.getOpenFileName returns a tuple (fileName, filter string)
                
            #if isinstance(fileName, str) and len(fileName) > 0:
                #if self.loadDiskFile(fileName, True):
                    #self._addRecentFile_(fileName, "bioformats")
                    #self.workspaceModel.update()

    @pyqtSlot()
    @safeWrapper
    def slot_openFiles(self):
        """Allows the opening of several files, as opposed to openFile.
        """
        from core.utilities import make_file_filter_string
        
        if self.slot_openSelectedFileItems():
            return
        
        (allImageTypesFilter, individualImageTypeFilters) = make_file_filter_string(pio.SUPPORTED_IMAGE_TYPES, 'All Image Types')

        allMimeTypes = ";;".join([i[0] + " (" + i[1] + ") " for i in zip(pio.mimetypes.types_map.values(), pio.mimetypes.types_map.keys())])
        
        filesFilterString = ';;'.join(["All file types (*.*)", allImageTypesFilter, individualImageTypeFilters, allMimeTypes])
                
        targetDir = self.recentDirectories[0]
        
        if isinstance(targetDir, str) and len(targetDir) and os.path.isdir(targetDir):
            fileNames, _ = self.chooseFile(caption=u'Open Files', fileFilter=filesFilterString,
                                           single=False, targetDir=targetDir)
            
        else:
            fileNames, _ = self.chooseFile(caption=u'Open Files', fileFilter=filesFilterString,
                                           single=False, targetDir=None)
        
        if len(fileNames) > 0:
            for fileName in fileNames:
                if isinstance(fileName, str) and len(fileName) > 0:
                    if not self.loadDiskFile(fileName):
                        return
                 
            self.workspaceModel.update()
                
    @pyqtSlot()
    @safeWrapper
    def _slot_openNamedFile_(self):
        if isinstance(self._temp_python_filename_, str) and len(self._temp_python_filename_.strip()) and os.path.isfile(self._temp_python_filename_):
            self.loadFile(self._temp_python_filename_)
            self._temp_python_filename_ = None
            
    @pyqtSlot()
    @safeWrapper
    def _slot_python_code_to_console(self):
        if isinstance(self._temp_python_filename_, str) and len(self._temp_python_filename_.strip()) and os.path.isfile(self._temp_python_filename_):
            self._run_python_source_code_(self._temp_python_filename_, paste=True)
            
            if self._temp_python_filename_ not in self.recentScripts:
                self.recentScripts.appendleft(self._temp_python_filename_)
                self._refreshRecentScriptsMenu_()
                
            else:
                if self._temp_python_filename_ != self.recentScripts[0]:
                    self.recentScripts.remove(self._temp_python_filename_)
                    self.recentScripts.appendleft(self._temp_python_filename_)
                    self._refreshRecentScriptsMenu_()
                    
    @pyqtSlot()
    @safeWrapper
    def _slot_gui_worker_done_(self):
        QtWidgets.QApplication.setOverrideCursor(self._defaultCursor)
        
    @pyqtSlot(object)
    @safeWrapper
    def _slot_gui_worker_result_(self, val):
        print("ScipyenWindow._slot_gui_worker_result_", val)
        pass
            
    @pyqtSlot(object)
    @safeWrapper
    def _slot_forgetScripts_(self, o):
        if isinstance(o, str):
            if o in self.recentScripts:
                self.recentScripts.remove(o)
                
        elif isinstance(o, (tuple, list)) and all([isinstance(v, str) for v in o]):
            for v in o:
                self.recentScripts.remove(v)
                
        self._refreshRecentScriptsMenu_()
        
    @pyqtSlot()
    @safeWrapper
    def _slot_dockConsole(self):
        if self.console is not None:
            self.consoleDockWidget.setWidget(self.console)
            self.console.show()
            self.consoleDockWidget.setVisible(True)
            self._console_docked_ = True
            
    @pyqtSlot()
    @safeWrapper
    def _slot_undockConsole(self):
        # FIXME 2021-11-26 18:37:40
        if self.console is not None:
            self.consoleDockWidget.layout().removeWidget(self.console)
            self.console.setVisible(True)
            self.consoleDockWidget.setVisible(False)
            self._console_docked_ = False
            
    @pyqtSlot()
    @safeWrapper
    def _slot_importPythonModule(self):
        if isinstance(self._temp_python_filename_, str) and len(self._temp_python_filename_.strip()) and os.path.isfile(self._temp_python_filename_):
            self._import_python_module_file_(self._temp_python_filename_)
        
            if self._temp_python_filename_ not in self.recentScripts:
                self.recentScripts.appendleft(self._temp_python_filename_)
                self._refreshRecentScriptsMenu_()
                
            else:
                if self._temp_python_filename_ != self.recentScripts[0]:
                    self.recentScripts.remove(self._temp_python_filename_)
                    self.recentScripts.appendleft(self._temp_python_filename_)
                    self._refreshRecentScriptsMenu_()
                
            self._temp_python_filename_ = None
            
    @pyqtSlot()
    @safeWrapper
    def _slot_copyToExternalWS(self):
        from core.extipyutils_client import cmd_copy_to_foreign
        # get the model indices of the selected workspace model items
        indexList = [i for i in self.workspaceView.selectedIndexes() if i.column() == 0]
        if len(indexList) == 0:
            return
        wscol = standard_obj_summary_headers.index("Workspace")
        varnames = [self.workspaceModel.item(i.row(),0).text() for i in indexList if self.workspaceModel.item(i.row(), wscol).text() == "Internal"]
        ns = self.external_console.window.find_tab_title(self.external_console.window.active_frontend)
        for varname in varnames:
            #print("_slot_copyToExternalWS: varname = %s , data = %s" % (varname, self.workspace[varname]))
            self.external_console.execute(cmd_copy_to_foreign(varname, self.workspace[varname]),
                                          where = ns)
            
        self.external_console.execute(cmd_foreign_shell_ns_listing(namespace=ns))
    
    @pyqtSlot()
    @safeWrapper
    def _slot_copyFromExternalWS(self):
        from core.utilities import standard_obj_summary_headers
        from core.extipyutils_client import cmd_copies_from_foreign
        
        # get the model indices of the selected workspace model items
        indexList = [i for i in self.workspaceView.selectedIndexes() if i.column() == 0]
        if len(indexList) == 0:
            return
    
        wscol = standard_obj_summary_headers.index("Workspace")
        
        # deal with those that belong to an external workspace
        for ns in self.workspaceModel.foreign_namespaces:
            varnames = [self.workspaceModel.item(i.row(),0).text() for i in indexList if self.workspaceModel.item(i.row(), wscol).text() == ns]
            
            if len(varnames):
                self.external_console.execute(cmd_copies_from_foreign(*varnames), where = ns)
    
            #wsname = ns.replace("_", " ")
            #varnames = [self.workspaceModel.item(i.row(),0).text() for i in indexList if self.workspaceModel.item(i.row(), wscol).text() == wsname]
            
            #if len(varnames):
                #self.external_console.execute(cmd_copies_from_foreign(*varnames),
                                              #where = wsname)
    
    @pyqtSlot(object)
    @safeWrapper
    def _slot_ext_krn_shell_chnl_msg_recvd(self, msg):
        # TODO 2020-07-13 00:45:57
        # when the kernel first comes alive get initial ns listing, store in
        # workspace model, filter out names of hidden vars in the list;
        # if any remains, populate workspace table (call updateFromExternal())
        # then after each execute_reply get a new dir() listing and compare
        # with the stored; any new var -> call props and populate in workspace table
        # (call updateFromExternal())
        # any removed var - remove row from workspace table (create method
        # removeFromExternal)
        #
        # NOTE: the databags in the workspace do not observe the contents of the
        # variable names list - so append or insert or del(...) won't work
        # but they will react when a new list replaces the old one
        # because lists work by reference, the next idiom won't work either:
        # a = DataBag()
        # a.observe(lambda x: print(x), "change") 
        # a.a = [1,2,3]
        # a.a = [4.5.6] # -> notifies
        # b = a.a # -> a REFERENCE to a.a
        # b.append(400) # -> a.a now contains 400 but no notification
        # a.a -> [4,5,6,400]
        #
        # but the following idiom DOES work:
        # b = list(a.a) # could in principle be generalized to b = type(a.a)(a.a)
        #               # for built-in types only ?!? but also for user-defined
        #               # types if they have a copy-constructor defined
        # b.append(1000) # a is unchanged
        # a.a = b -> notifies
        #
        from core.extipyutils_client import (unpack_shell_channel_data, 
                                             cmds_get_foreign_data_props,
                                             cmd_foreign_shell_ns_listing,
                                             )
        
        #print("_slot_ext_krn_shell_chnl_msg_recvd")
        #print("\ttab:", msg["workspace_name"], "\n\ttype:", msg["msg_type"], "\n\tstatus:", msg["content"]["status"])
        #print("\tuser_expressions:", msg["content"].get("user_expressions", {}))
        
        if self.external_console.window.tab_widget.count() == 0:
            # only listen to kernels that have a frontend 
            return
        
        #print("mainWindow._slot_ext_krn_shell_chnl_msg_recvd:\n\tsession ID =", 
              #msg["parent_header"]["session"], 
              #"\n\tworkspace =", msg["workspace_name"],
              #"\n")
        
        #print("mainwindow\n\t_slot_ext_krn_shell_chnl_msg_recvd msg type", msg["msg_type"])
        
        #print("\nmainwindow shell channel message received")
        #print("\tmessage type:", msg["msg_type"])
        #print("\tvia connection file:", msg["connection_file"])
        
        # ATTENTION: 2021-01-30 14:13:28
        # only use for debugging
        #if msg["connection_file"] in self.external_console.window.connections:
            #if self.external_console.window.connections[msg["connection_file"]]["master"] is None:
                #print("external kernel via %s" % msg["connection_file"])
                #print("\t", msg)
        
        if msg["msg_type"] == "execute_reply":
            #print("\n\t** execute_reply from %s" % msg["workspace_name"])
            #print("\n****** execute_reply from %s\n"% msg["workspace_name"], msg, "\n*****\n")
            vardict = unpack_shell_channel_data(msg)
            
            #print("\n\t** len(vardict) =",  len(vardict))
            #print("\n\t** vardict =",  vardict)
            
            if len(vardict):
                # dict with properties of variables in external kernel namespace
                prop_dicts = dict([(key, val) for key, val in vardict.items() if key.startswith("properties_of_")])
                
                # dict with listing of contents of the external kernel namespace
                ns_listings = dict([(key, val) for key, val in vardict.items() if key.startswith("ns_listing_of_")])
                
                # this is needed here so that they don't clutter our own namespace
                for key in prop_dicts.keys():
                    vardict.pop(key, None)
                    
                for key in ns_listings.keys():
                    vardict.pop(key, None)
                    
                # now vardict only has variables shuttled (via pickle) from the
                # external kernel namespace into our own
                    
                self.workspace.update(vardict)
                self.workspaceModel.update()
                #self.workspaceModel.update(from_console=False)
                
                if len(prop_dicts):
                    #print("mainWindow: len(prop_dicts)", len(prop_dicts))
                    for key, value in prop_dicts.items():
                        if value["Workspace"]["display"] == "Internal":
                            value["Workspace"] = {"display":msg["workspace_name"], 
                                                  "tooltip":"Location: %s kernel namespace" % msg["workspace_name"]}
                            
                        for propname in value.keys():
                            value[propname]["tooltip"] = value[propname]["tooltip"].replace("Internal", msg["workspace_name"])
                        
                    self.workspaceModel.updateFromExternal(prop_dicts)
                
                if len(ns_listings):
                    #print("ns_listings =", ns_listings)
                    for key, val in ns_listings.items():
                        ns_name = key.replace("ns_listing_of_","")
                        #ns_name = key.replace("ns_listing_of_","").replace(" ", "_")
                        #print("\n\t.... ns_name", ns_name, "val", val)
                        if ns_name == msg["workspace_name"]:
                            if isinstance(val, dict):
                                self.workspaceModel.update_foreign_namespace(ns_name, msg["connection_file"], val)
                                if ns_name in self.workspaceModel.foreign_namespaces:
                                    for varname in self.workspaceModel.foreign_namespaces[ns_name]["current"]:
                                        self.external_console.execute(cmds_get_foreign_data_props(varname, 
                                                                                                  namespace=msg["workspace_name"]),
                                                                        where = msg["parent_header"]["session"])
                            
        elif msg["msg_type"] == "kernel_info_reply":
            #print("\n\t** kernel_info_reply from %s" % msg["workspace_name"])
            #print("\n****** kernel_info_reply from %s\n" % msg["workspace_name"], msg, "\n********\n")
            # usually sent when right after the kernel started - we use this as
            # a signal that the kernel has been started, by which we trigger
            # an initial directory listing.
            # it seems this is only sent whe a new connection is established to
            # the kernel (via a new connection file); opening a slave tab again
            # 
            #pass
            #self.external_console.execute(cmd_foreign_shell_ns_listing(namespace=msg["workspace_name"].replace(" ", "_")),
            self.external_console.execute(cmd_foreign_shell_ns_listing(namespace=msg["workspace_name"]),
                                          where = msg["parent_header"]["session"])
            
        elif msg["msg_type"] == "is_complete_reply":
            #print("\n\t** is_complete_reply from %s" % msg["workspace_name"])
            #print("\n****** is_complete_reply from %s\n"% msg["workspace_name"], msg, "\n********\n")
            self.external_console.execute(cmd_foreign_shell_ns_listing(namespace=msg["workspace_name"]),
                                          where = msg["parent_header"]["session"])
                    
    def execute_in_external_console(self, call, where=None):
        self.external_console.execute(call, where=where)
        
    @pyqtSlot(dict)
    @safeWrapper
    def _slot_ext_krn_disconnected(self, cdict):
        #print("mainWindow: _slot_ext_krn_disconnected %s" % cdict)
        signalBlocker = QtCore.QSignalBlocker(self.external_console.window)
        self.workspaceModel.remove_foreign_namespace(cdict)
        
    @pyqtSlot(dict)
    @safeWrapper
    def _slot_ext_krn_stop(self, conndict):
        #print("mainWindow: _slot_ext_krn_stop %s" % conndict)
        signalBlocker = QtCore.QSignalBlocker(self.external_console.window)
        self.workspaceModel.remove_foreign_namespace(conndict)
        
    @pyqtSlot(dict)
    @safeWrapper
    def _slot_ext_krn_restart(self, conndict):
        #print("mainWindow: _slot_ext_krn_restart %s" % conndict)
        from core.extipyutils_client import cmd_foreign_shell_ns_listing
        
        ns_name = conndict["name"]
        
        signalBlocker = QtCore.QSignalBlocker(self.external_console.window)
        
        self.external_console.execute(cmd_foreign_shell_ns_listing(namespace=ns_name))
        
    @safeWrapper
    def _import_python_module_file_(self, fileName):
        import importlib.util
        import sys
        
        moduleName = strutils.str2symbol(os.path.splitext(fileName)[0])
        
        spec = importlib.util.spec_from_file_location(moduleName, fileName)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        sys.modules[moduleName] = module
        
    @pyqtSlot(str)
    def _slot_scriptFileAddedInManager(self, fileName):
        self._temp_python_filename_ = fileName
        self._slot_registerPythonSource_()
        
    @pyqtSlot()
    @safeWrapper
    def _slot_registerPythonSource_(self):
        if isinstance(self._temp_python_filename_, str) and len(self._temp_python_filename_.strip()) and os.path.isfile(self._temp_python_filename_):
            if self._temp_python_filename_ not in self.recentScripts:
                # NOTE:2022-01-28 23:11:59
                # this bypasses self.recentScript.setter therefore this will NOT
                # be saved in the config
                # see solution at NOTE:2022-01-28 23:16:57
                # 
                #self.recentScripts.appendleft(self._temp_python_filename_)
                self.recentScripts.insert(0,self._temp_python_filename_)
                self._refreshRecentScriptsMenu_()
                
            else:
                if self._temp_python_filename_ != self.recentScripts[0]:
                    rscripts = [s for s in self.recentScripts if s != self._temp_python_filename_]
                    rscripts.insert(0, self._temp_python_filename_)
                    self.recentScripts = rscripts
                
                #if self._temp_python_filename_ != self.recentScripts[0]:
                    #self.recentScripts.remove(self._temp_python_filename_)
                    #self.recentScripts.appendleft(self._temp_python_filename_)
                    #self._refreshRecentScriptsMenu_()
                
            self._temp_python_filename_ = None
            
    @pyqtSlot()
    @safeWrapper
    def _slot_runPythonSource(self):
        if isinstance(self._temp_python_filename_, str) and len(self._temp_python_filename_.strip()) and os.path.isfile(self._temp_python_filename_):
            
            #worker = pgui.ProgressWorker(self._run_python_source_code_, None, self._temp_python_filename_, {'paste': False})
            
            #self.threadpool.start(worker)
            
            self._run_python_source_code_(self._temp_python_filename_, paste=False)

            if self._temp_python_filename_ not in self.recentScripts:
                self.recentScripts.insert(0,self._temp_python_filename_)
                #self.recentScripts.appendleft(self._temp_python_filename_)
                self._refreshRecentScriptsMenu_()
                
            else:
                if self._temp_python_filename_ != self.recentScripts[0]:
                    self.recentScripts.remove(self._temp_python_filename_)
                    self.recentScripts.insert(0,self._temp_python_filename_)
                    #self.recentScripts.appendleft(self._temp_python_filename_)
                    #self._refreshRecentScriptsMenu_()
                    
            self._temp_python_filename_ = None
            
    def _run_python_source_code_(self, fileName, paste=False):
        bfn = os.path.basename(fileName)
        msg = f"Sending {bfn} to console" if paste else f"Running {bfn} in console"
        self.statusbar.showMessage(msg)
        if os.path.isfile(fileName):
            if paste:
                text = pio.loadFile(fileName)
                self.console.writeText(text)
                
            else:
                fname = os.path.splitext(fileName)[0]
                cmd = "run -i -n -t '%s'" % fname
            
                try:
                    self.console.execute(cmd, hidden=True, interactive=True)
                
                except:
                    traceback.print_exc()
                    
        self.statusbar.showMessage("Done!")
        
    @pyqtSlot(str)
    @safeWrapper
    def _slot_test_gui_style(self, val:str)->None:
        self._prev_gui_style_name = self._current_GUI_style_name
        
        if val == "Default":
            self.app.setStyle(QtWidgets.QApplication.style())
            self._current_GUI_style_name = "Default"
        else:
            self.app.setStyle(val)
            self._current_GUI_style_name = val
            
    @pyqtSlot()
    @safeWrapper
    def _slot_set_Application_style(self):
        from gui.pictgui import ItemsListDialog
        d = ItemsListDialog(self, itemsList = ["Default"] + self._available_Qt_style_names_,
                            title="Choose Application GUI Style",
                            preSelected = self._current_GUI_style_name)
        
        d.itemSelected.connect(self._slot_test_gui_style)
        
        a = d.exec()
        
        if a == QtWidgets.QDialog.Accepted:
            sel = d.selectedItemsText
            if len(sel):
                style = sel[0]
                
            self.guiStyle = style
                
        else:
            self.guiStyle = self._prev_gui_style_name

    @pyqtSlot(tuple)
    def slot_windowRemoved(self, name_obj):
        self.shell.user_ns.pop(name_obj[0], None)
        self.workspaceModel.update()
                
    @pyqtSlot()
    @safeWrapper
    def _slot_showActionStatusMessage_(self):
        action = self.sender()
        if isinstance(action, QtWidgets.QAction):
            action.showStatusText(self)
        
    @pyqtSlot()
    @safeWrapper
    def slot_multiExportToCsv(self):
        indexList = self.workspaceView.selectedIndexes()
        
        if len(indexList) == 0:
            return
        
        varnames = [self.workspaceModel.item(indexList[k].row(),0).text() for k in range(len(indexList))]
        
        #if all([isinstance(self.workspace[v], (dict, pd.DataFrame, pd.Series, neo.basesignal.BaseSignal, neo.SpikeTrain))] for v in varnames):
        if all([isinstance(self.workspace[v], (pd.DataFrame, pd.Series, neo.basesignal.BaseSignal, neo.SpikeTrain, np.ndarray))] for v in varnames):
            if not any([isinstance(self.workspace[v], np.ndarray) and self.workspace[v].ndim > 2 for v in varnames]):
                for v in varnames:
                    filename = "".join([v, ".csv"])
                    pio.writeCsv(self.workspace[v], fileName=filename)
            
    @pyqtSlot()
    @safeWrapper
    def slot_exportToCsv(self):
        indexList = self.workspaceView.selectedIndexes()
        
        if len(indexList) == 0:
            return
        
        varname = self.workspaceModel.item(indexList[0].row(),0).text()
        
        if varname is None or len(varname.strip()) == 0:
            return

        #if not isinstance(self.workspace[varname], (pd.Series, pd.DataFrame, np.ndarray, dict)):
        if not isinstance(self.workspace[varname], (pd.Series, pd.DataFrame, neo.basesignal.BaseSignal, neo.SpikeTrain, np.ndarray)):
            return
        
        if isinstance(self.workspace[varname], np.ndarray) and self.workspace[varname].ndim > 2:
            return

        fileFilter = "CSV files (*.csv)"
        
        filename = "".join([varname, ".csv"])
        
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self,
                                                            caption = "Export to CSV",
                                                            filter=fileFilter,
                                                            directory=os.path.join(self.currentDir, filename))
        
        if len(filename.strip()) > 0:
            pio.writeCsv(self.workspace[varname], fileName=filename)
            
    @pyqtSlot()
    @safeWrapper
    def slot_autoSelectViewer(self):
        if bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier):
            newWindow = True
            
        else:
            newWindow = False
            
        varname = self.workspaceModel.currentItemName
        
        if varname is None:
            indexList = self.workspaceView.selectedIndexes()
            
            if len(indexList) == 0:
                return
            
            varname = self.workspaceModel.item(indexList[0].row(),0).text()
            
            if varname is None or isinstance(varname, str) and len(varname.strip()) == 0:
                return
            
            if varname not in self.workspace.keys():
                return
        
        action = self.sender()
        actionName = action.text().replace("&","")
        
        variable = self.workspace[varname]
        vartype = type(variable)
        
        viewers_actions = VTH.get_view_actions(vartype)
        
        if len(viewers_actions):
            viewers = [va[0] for va in viewers_actions if va[1] == actionName]
            
            if len(viewers) == 0:
                self.console.execute(varname)
                
            else:
                viewer = viewers[0]
                
                if not self.viewObject(variable, varname, winType = viewer, newWindow=newWindow):
                    self.console.execute(varname)
        else:
            self.console.execute(varname)
            
    @pyqtSlot()
    @safeWrapper
    def slot_viewSelectedVar(self):
        if bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier):
            self.slot_viewSelectedVarInNewWindow()
            return
        
        varname = self.workspaceModel.currentItemName
        
        if varname is None:
            indexList = self.workspaceView.selectedIndexes()
            
            if len(indexList) == 0:
                return
            
            varname = self.workspaceModel.item(indexList[0].row(),0).text()
            
            if varname is None:
                return
            
        #if not self.viewVar(varname, newWindow=False, useSignalViewerForNdArrays=useSignalViewerForNdArrays):
        if not self.viewVar(varname, newWindow=False):
            self.console.execute(varname)
            
    @pyqtSlot()
    @safeWrapper
    def slot_viewSelectedVariables(self):
        indexList = self.workspaceView.selectedIndexes()
        if len(indexList) == 0:
            return
        
        varNames = list()
        
        for i in indexList:
            varname = self.workspaceModel.item(i.row(),0).text()
            if not self.viewVar(varname, True):
                self.console.execute(varname)
        
    @pyqtSlot()
    @safeWrapper
    def slot_consoleDisplaySelectedVariables(self):
        indexList = self.workspaceView.selectedIndexes()
        
        if len(indexList) == 0:
            return
        
        varnames = [self.workspaceModel.item(i.row(),0).text() for i in indexList]
        
        for varname in varnames:
            self.console.execute(varname)
            
    @pyqtSlot()
    @safeWrapper
    def slot_viewNDarray(self):
        """Displays ndarray in a TableEditor
        """
        if bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier):
            self.slot_viewNDarrayNewWindow()
            return
        
        varname = self.getCurrentVarName()

        if varname is None: # workspaceModel dit not pick it up, try to get it from workspaceView
            indexList = self.workspaceView.selectedIndexes()
            
            if len(indexList) == 0:
                return
            
            varname = self.workspaceModel.item(indexList[0].row(),0).text()
            
            if varname is None:
                return
        
        if isinstance(self.workspace[varname], np.ndarray):
            if self.workspace[varname].ndim in (1,2):
                winDict = self.tableEditorWindows
                
                # create a tableEditor if none is present
                if len(winDict) == 0:
                    self.slot_newTableEditorWindow()

                winId = self.currentTableEditorWindowID
                
                # re-use existing viewer window
                winDict[winId].view(self.workspace[varname])
                winDict[winId].show()
                if winDict[winId].isMinimized():
                    winDict[winId].showNormal()
                winDict[winId].raise_() # NOTE: to avoid clash with python's raise PyQt uses "raise_()"
    
    @pyqtSlot()
    @safeWrapper
    def slot_viewNDarrayNewWindow(self):
        """Displays ndarray in a new  TableEditor
        """
        varname = self.getCurrentVarName()
        if varname is None:
            return
        
        winDict = self.tableEditorWindows
        
        self.slot_newTableEditorWindow()
        winId = self.currentTableEditorWindowID
        winDict[winId].view(self.workspace[varname])
        winDict[winId].setTitle(varname)
        
    @pyqtSlot()
    @safeWrapper
    def slot_viewSelectedVarInNewWindow(self):
        #if bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier):
            #useSignalViewerForNdArrays = True
            
        #else:
            #useSignalViewerForNdArrays = False
            
        varname = self.getCurrentVarName()
        if varname is None:
            return
        
        #if not self.viewVar(varname, newWindow=True, useSignalViewerForNdArrays=useSignalViewerForNdArrays):
        if not self.viewVar(varname, newWindow=True):
            self.console.execute(varname)
        
    def viewVar(self, varname, newWindow=False, winType=None): #, useSignalViewerForNdArrays=True):
        """Displays a variable in the workspace.
        The variable is selected by its name
        """
        #print("ScipyenWindow.viewVar, newWindow:", newWindow)
        if varname in self.workspace.keys():
            return self.viewObject(self.workspace[varname], varname, 
                                   winType=winType,
                                   newWindow=newWindow)
        
        return False
    
    def viewObject(self, obj, objname, winType=None, newWindow=False):
        """Actually displays a python object in user's workspace
        Delegates to appropriate viewer according to object type, creates a new
        viewer if necessary.
        Call this function when the intention is to display variables that are 
        NOT in user's workspace.
        
        Parameters:
        ------------
        obj: a python variable
        
        objname: str, the symbol name used in the viewer's window title (this is 
                not necessarily the symbol bound to the object in the workspace)
                    
        newWindow: bool (default False). When False, displays the object in the
                currently active viewer window, is a suitable one exists, or
                creates a new one.
                
                When True, displays the object in a new instance of a suitable viewer.
                
        useSignalViewerForNdArrays when true, plot signals in signal viewer
        """
        # TODO: accommodate new viewer types - nearly DONE via VTH
        
        if isinstance(winType, str) and winType in [v.__name__ for v in self.viewers.keys()]:
            if winType not in self.viewers.keys():
                raise ValueError("Unknown viewer type %s" % winType)
            
            winType = [v for v in self.viewers.keys() if v.__name__ is winType][0]
            
        elif inspect.isclass(winType) and winType in self.viewers.keys():
            if winType not in self.viewers.keys():
                raise ValueError("Unknown viewer type %s" % winType.__name__)
                
        elif winType is None:
            viewers_type_list = VTH.get_handlers_for_type(type(obj))
            
            if len(viewers_type_list) == 0:
                return False
            
            winType = viewers_type_list[0][1]
            
        else:
            return False
        
        if len(self.viewers[winType]) == 0 or newWindow:
            win = self._newViewer(winType)
            
        else:
            win = self.currentViewers[winType]
            
        if win is None:
            return False
            
        win.show() # generic way also works for maplotlib figure

        if isinstance(win, mpl.figure.Figure):
            plt.figure(win.number)
            if isinstance(obj, neo.core.basesignal.BaseSignal) and hasattr(obj, "times"):
                plt.plot(obj.times, obj)
                times_units_str = obj.times.units.dimensionality.string
                xlabel = "" if times_units_str == "dimensionless" else f"{cq.name_from_unit(obj.times.units)} ({obj.times.units.dimensionality.string})"
                name = obj.name
                if name is None or len(name.strip()) == 0:
                    name = cq.name_from_unit(obj.units.dimensionality.string)
                ylabel = f"{name} ({obj.units.dimensionality.string})"
                plt.xlabel(xlabel)
                plt.ylabel(ylabel)
                if isinstance(objname, str) and len(objname.strip()):
                    plt.title(objname)
            else:
                plt.plot(obj)
                
            if isinstance(win.canvas, QtWidgets.QWidget):
                win.canvas.activateWindow()
           
        else:
            win.setData(obj, doc_title=objname) # , varname=objname)
            win.activateWindow()
    
        return True
            
    def _removeMenu_(self, menu):
        if len(menu.actions()) == 0:
            parentMenuOrMenuBar = menu.parent()
            if parentMenuOrMenuBar is not None: # parent should never be None, but let's check anyway
                parentMenuOrMenuBar.removeAction(menu.menuAction())
                if type(parentMenuOrMenuBar).__name__ == "QMenu": 
                    if parentMenuOrMenuBar.title() != "Plugins":
                        self._removeMenu_(parentMenuOrMenuBar)
            
    @pyqtSlot()
    @safeWrapper
    def slot_offloadPlugins(self): # do we "unload", "offload", or simply "forget" them?
        '''
        Removes the (sub)menus and menu items created by loading plugins.
        The only use, really, is when called by slot_reloadPlugins().
        The plugin code itself is recompiled (and reloaded) by the pict_plugin_loader
        '''
        if len(self.pluginActions) > 0:
            for action in self.pluginActions:
                parentMenuOrMenuBar = action.parent()
                if parentMenuOrMenuBar is not None: # parent should never be None, but let's check anyway
                    parentMenuOrMenuBar.removeAction(action)
                    if type(parentMenuOrMenuBar).__name__ == "QMenu":
                        if parentMenuOrMenuBar.title() != "Plugins": # check if menu left empy, chances are it is created by the plugin => remove it
                            self._removeMenu_(parentMenuOrMenuBar)

        plugins_members = self.plugins.__dict__.keys()
        
        for m in plugins_members:
            if isinstance(self.plugins.__dict__[m], types.ModuleType):
                del(self.plugins.__dict__[m])


    @pyqtSlot()
    @safeWrapper
    def slot_reloadPlugins(self):
        self.slot_offloadPlugins()
        self.slot_loadPlugins()

    # TODO/FIXME 2016-04-03 00:14:47
    # make forceRecompile a configuration variable !!!
    @pyqtSlot()
    @safeWrapper
    def slot_loadPlugins(self):
        ''' See pict_plugin_loader docstring
        '''
        #print("   slot_loadPlugins")
        self.plugins = types.ModuleType('plugins','Contains pict plugin modules with their publicized callback functions')
        pict_plugin_loader.find_plugins(__module_path__)
        
        # NOTE: 2016-04-15 11:53:08
        # let the plugin loader just load plugin module code
        # and do the plugin initialization here
        
        if len(pict_plugin_loader.loaded_plugins) > 0:
            for p in pict_plugin_loader.loaded_plugins.values():
                menudict = collections.OrderedDict([(p.__name__, (p.__file__, p.init_pict_plugin()) )])
                #menudict = p.init_pict_plugin()
                if len(menudict) > 0:
                    for (k,v) in menudict.items():
                        if (isinstance(k, str) and len(k)>0):
                            self._installPlugin_(k,v)
                        else:
                            raise TypeError("Incompatible Plugin Key")
                        
        #print("   done slot_loadPlugins")

        # NOTE: 2016-04-03 00:25:00
        # calling this seems to make the qt app close -- why?
        # NOTE: FIXED 2016-04-03 01:03:53 -- we call this asynchrnously, 
        # via Qt signal/slot mechanism
        #dw = os.walk(path)
        
    # FIXME: 2016-04-03 16:34:19
    # not sure this will be very efficient when we will iterate through many plugins;
    # I guess ImageJ approch is better, in that all plugins are rooted in the 
    # "Plugins" menu in the menubar and then the menu path corresponds to the 
    # actual subdirectory path of the plugin file (or a virtual path if plugin is
    # a jar file)
    def _locateMenuByItemText_(self, parent, itemText):
        '''
        Looks for (and returns) a QMenu labeled with itemText,
        in the parent widget which can be (typically) another QMenu or the
        QMenuBar.
        
        Returns None if:
        (a) the parent does not contain a menuitem with given itemText
        (b) the parent does have an action with given itemText, 
            but the action does not have a menu (i.e. it is a leaf of the
            menu tree)
        (c) itemText is the empty string ('') because it denotes a separator
        '''
        #parentActions = parent.actions()
        parentActionLabels = [str(i.text()) for i in parent.actions()]
        parentActionMenus = [i.menu() for i in parent.actions()]
        
        if itemText in parentActionLabels:
            ret = parentActionMenus[parentActionLabels.index(itemText)]
        else:
            ret = None

        return ret

    def _installPluginFunction_(self, f, menuItemLabel, parentMenu, nReturns=None, inArgTypes=None):
        '''
        Implements the actual logic of installing individual plugin functions 
        advertised by the init_pict_plugin function defined in the plugin module.
        
        The function 'f' is wrapped in a slot that will be connected to the 
        triggered() signal emited by the appropriate menu item.
        
        Furthermore the plugin module that advertises this function is imported 
        inside the pseudo-module self.plugins -- "pseudo" because this is a
        ypes.ModuleType ere is no
        python source file for it and is created at runtime, but otherwise it is just a types.ModuleType. 
        
        There, each plugin is also installed also as a pseudo-module: a types.ModuleType where 
        
        '''
        # NOTE: TODO: in python 3: use inspect.getfullargspec(f) 
        # to parse *args, **kwargs syntax !!!
        argSpec       = inspect.getfullargspec(f)
        
        arg_names    = argSpec.args
        arg_defaults = argSpec.defaults
        var_args     = argSpec.varargs
        
        kw_args      = argSpec.varkw
            
        # NOTE: 2016-04-17 15:49:08 funcargs are mostly useful to get return annotation if present
        # I found inspect.getfullargspec (or better, inspect.getfullargspec in python 3) more
        # useful to get positional argument list
        if (nReturns is None or inArgTypes is None):
            if hasattr(f, '__annotations__'):
                sig = inspect.signature(f)

                if inArgTypes is None:
                    #arg_param_names = sig.parameters.keys() #not very useful to get the parameter types !!!

                    # NOTE: 2016-04-17 16:32:00
                    # this will raise KeyError if annotations is incomplete;
                    # however if an annotation is badly formed (e.g. it has a 
                    # list or tuple, or None, or anything else in ) the _inputPrompter_
                    # will raise ValueError on the input Type
                    inArgTypes = [f.__annotations__[i] for i in argSpec.args] # simple !

                if (nReturns is None or nReturns == 0):
                    try:
                        ra = sig.return_annotation
                        if ra != sig.empty:
                            if isinstance(ra, str):
                                nReturns = 1
                            elif isinstance(ra, (tuple, list)):
                                nReturns = len(sig.return_annotation)
                            else:
                                raise ValueError('Incompatible value in return annotation')
                        else:
                            nReturns = 0
                    finally:
                        pass
        
        # NOTE 2016-04-17 16:06:29 code taken from prompt_f in _inputPrompter_
        # and from slot_wrapPluginFunction decorator, in order to keep the 
        # deocrator's code small and tractable
        #
        #   if is None, or is a nonempty (tuple or list) or is a type or the string '~'
        if inArgTypes is not None and ((type(inArgTypes) in (tuple, list) and len(inArgTypes) > 0) or (type(inArgTypes) is type) or (type(inArgTypes) is str and inArgTypes == '~')):
            if type(inArgTypes) is type: # cover the case where argument type is given as a single type
                inTypes = (inArgTypes,)
            elif type(inArgTypes) is str and inArgTypes == '~':
                inTypes= (inArgTypes,)
            else: # leave it as a tuple
                inTypes = inArgTypes
                
            #if (arg_defaults is not None and len(arg_names) > len(arg_defaults)):
                #defs = [None] * len(arg_names)
                #defs[(len(arg_names)-len(arg_defaults)):] = arg_defaults
                #arg_defaults = defs
                #del defs
            #elif arg_defaults is None:
                #arg_defaults = [None] * len(arg_names)
                    
        else:
            inTypes = inArgTypes
        
        if (arg_defaults is not None and len(arg_names) > len(arg_defaults)):
            defs = [None] * len(arg_names)
            defs[(len(arg_names)-len(arg_defaults)):] = arg_defaults
            arg_defaults = defs
            del defs
        elif arg_defaults is None:
            arg_defaults = [None] * len(arg_names)
                    
        newAction = parentMenu.addAction(menuItemLabel)
        self.pluginActions.append(newAction)
        newAction.triggered.connect(self.slot_wrapPluginFunction(f, nReturns, inTypes, arg_names, arg_defaults, var_args, kw_args))

        # Ideally, these functions might not be visible as free functions in the
        # console environment, but rather as member(s) of a subenvironment (module-like)
        # named in a simple fashion (to minime keystrokes, thus to facilitate their call
        # from the console).
        
        # On the other hand, their naming should reconcile possible name clashes
        # e.g., different plugin advertise functions with the same name (and signature, maybe).
        
        # A simple way would be to reference the plugin module in the global environment
        # of the console -- how? -- but NOT in the user_ns namespace, so that they do
        # not clutter the workspace window unnnecessarily. Alternatively we could 
        # alter the workspace model such that the workspace window does not display 
        # function objects. This however is not really desiable, as it would also hide 
        # functions defined by the user at the console, and thus deteaf the purpose
        # of having a console in the first place (i.e. quick code prototyping)
        
        # One option would be to "re-import" the plugin module in the console
        # environment as we did for __all__ in slot_initQtConsole. This could be done 
        # here if the console and the ipkernel are initialized, or could  be done
        # inside slot_initQtConsole function.
        
        # The drawback is that this will also expose functions defined inside the plugin
        # module, but not advertised by the init_pict_plugin function, which may 
        # or may not be desirable.
        
        # Another option is to create "pseudo-modules" (types.ModuleType)
        # and populate them with the function object(s) advertised by the 
        # fully fledged plugin module
        
        # NOTE: 2016-04-16 10:05:48
        # at this point we cannot change f.__name__ (it having been already 
        # registered with a menuitem so if it has a weird / nonconformant name 
        # e.g. with spaces or illegal characters the following code will fail.
        # It if the responsibility of the plugin author to ensure that the 
        # advertised functions have sane names
        
        if f.__module__ not in self.plugins.__dict__.keys():
            # inside self.plugins, create a pseudo-module for the function's
            # plugin,if not already there
            icmd = ''.join(["self.plugins.",f.__module__," = types.ModuleType('",f.__module__,"')"])
            exec(icmd)
            
            # by the way the original (fully fledged) module should already be
            # in sys (because the module has been loaded with imp.load_module by 
            # pict_plugin_loader therefore the next check is redundant, and the 
            # lines inside the 'if' block below might as well be taken out of it
            if f.__module__ in sys.modules.keys():
                self.plugins.__dict__[f.__module__].__doc__ = sys.modules[f.__module__].__doc__
                self.plugins.__dict__[f.__module__].__package__ = sys.modules[f.__module__].__package__
                self.plugins.__dict__[f.__module__].__file__ = None
            
        # now "install" the function in this pseudo-module corresponding to
        # the plugin module that defined the function
        icmd = ''.join(["self.plugins.",f.__module__,".",f.__name__," = f"])
        exec(icmd)
        
    def _parsePluginFunctionDict_(self, d, menuOrItemLabel, parentMenu):
        '''
        Parses a plugin functions dictionary and installs the functions in the appropriate menu paths
        '''
        if len(d) > 1: # more than one function defined
            newMenu = parentMenu.addMenu(menuOrItemLabel)
            for (f, fargs) in d.items():
                self._installPluginFunction_(f, f.__name__, newMenu, *fargs)
                
        elif len(d) == 1:
            self._installPluginFunction_(dd.keys()[0], menuOrItemLabel, parentMenu, *d.values()[0])
            
    def _run_loop_process_(self, fn, process_name, *args, **kwargs):
        # TODO : 2021-08-17 12:43:35
        # check where it is used (currently nowhere, but potentially when running
        # plugins) 
        # possibly move to core.prog
        if isinstance(process_name, str) and len(process_name.strip()):
            title = "%s..." % process_name
            
        else:
            title = "Processing..."
            
        #print("_run_loop_process_ args", args)
            
        pdlg = QtWidgets.QProgressDialog(title, "Cancel", 0,1000, self)
        
        worker = pgui.ProgressWorker(fn, pdlg, *args, **kwargs)
        worker.signals.signal_finished.connect(pdlg.reset)
        worker.signals.signal_result.connect(self.slot_loop_process_result)
            
        if worker is not None:
            self.threadpool.start(worker)
    
    @pyqtSlot(object)
    @safeWrapper
    def slot_loop_process_result(self, obj, name=""):
        if isinstance(name, str) and len(name.strip()):
            self.workspace[name] = obj
            
        else:
            self.workspace["result"] = obj
            
        self.workspaceModel.update()
        #self.workspaceModel.update(from_console=False)
            
        self.workspaceChanged.emit()
        
        
    def _installPlugin_(self, pname, v):
        '''Installs the plugin named pname according to the information in v 
        
        NOTE:   v[0] is a string wih the absolute pathname of the plugin module
        
                v[1] is a plugin info dict as advertised by the init_pict_plugin 
                     function in the plugin module, where the keys are srings
                     describing a menu path, and the values are either dictionaries
                     mapping function objects to number of return variables and 
                     parameter types, or just function object (or sequence of ...).
                     In the latter case, if the functions take arguments and/or
                     return something, the functions should have an __annotations__
                     attribute.
                     
        
        See pict_plugin_loader docstring for details about v[1]
        '''
        
        if len(v[1]) > 0: # the nested dict
            for mp in v[1]: # iterate over keys #print(mp)
                if mp is not None and isinstance(mp, str) and len(mp) > 0:
                    menuPathList = mp.split('|')
                    ff = v[1][mp]

                    parentMenu = self.menuBar()
                    currentMenu = None

                    for item in menuPathList:
                        currentMenu = self._locateMenuByItemText_(parentMenu, item)
                        siblingActionLabels = [str(i.text()) for i in parentMenu.actions()]

                        if currentMenu is None:
                            if item == menuPathList[-1]:
                                if item in siblingActionLabels: # avoid name clashes
                                    item  = ' '.join([item, "(",ff.__module__,")"])

                                if 'function' in type(ff).__name__:
                                    self._installPluginFunction_(ff, item, parentMenu)

                                elif isinstance(ff, list):
                                    if len(ff)>1:
                                        newMenu = parentMenu.addMenu(item)
                                        for f in ff:
                                            if 'function' in type(f).__name__:
                                                self._installPluginFunction_(f, f.__name__, newMenu)
                                            else:
                                                raise TypeError("function object expected")
                                    else:
                                        self._installPluginFunction_(ff[0], item, parentMenu)

                                elif isinstance(ff, dict):
                                    self._parsePluginFunctionDict_(collections.OrderedDict(ff), item, parentMenu)

                                else:
                                    raise TypeError(" a function object or a list of function objects was expected")
                            else:
                                parentMenu = parentMenu.addMenu(item)
                                continue

                        else:
                            parentMenu = currentMenu

                else: #  plugin module does not advertise any menu path => use plugin module name as submenu of a canonical Plugins menu
                    pluginsMenu = self._locateMenuByItemText_(self.menuBar(), "Plugins")
                    if pluginsMenu is None:
                        pluginsMenu = self.menuBar().addMenu("Plugins")

                    if 'function' in type(ff).__name__:
                        newMenu = pluginsMenu.addMenu(pname)
                        self._installPluginFunction_(ff, ff.__name__, newMenu)
                    elif isinstance(ff, list):
                        newMenu = pluginsMenu.addMenu(pname)
                        if len(ff) == 1:
                            if 'function' in type(ff[0]).__name__:
                                self._installPluginFunction_(ff[0], ff[0].__name__, newMenu)
                            else:
                                raise TypeError("function object expected")
                        elif len(ff) > 1:
                            for f in ff:
                                if 'function' in type(f).__name__:
                                    self._installPluginFunction_(f, f.__name__, newMenu)
                                else:
                                    raise TypeError("function object expected")
                    elif isinstance(ff, dict):
                        self._parsePluginFunctionDict_(collections.OrderedDict(ff), pname, pluginsMenu)
        else:
            raise ValueError("empty nested dict in plugin info")
    
