# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""Main window for the Scipyen application


"""
#
# TODO enable drag&drop from history to outside of the Scipyen (e.g.
# a text editor, desktop file manager etc)


# NOTE: 2021-10-21 13:24:24
# all things imported below will be available in the user workspace

# BEGIN import modules
# BEGIN core python modules
import sys
import os
import types
import atexit
import re
import inspect
import gc
import io
import warnings
import numbers
import faulthandler
import importlib
# NOTE: 2024-09-26 12:16:28
# I wrap reload with scipyen_plugin_loader.reload, further below
# from importlib import reload  # I use this all too often !
import subprocess
import platform
import traceback
import keyword
import inspect
import weakref
import itertools, more_itertools # NOTE: 2024-09-26 12:44:08 this is not a core python but might as well be!
import typing
import functools
import operator
import json
import pathlib
from pprint import pprint
from copy import copy, deepcopy
import collections
from collections import deque, ChainMap
import cmath

# END core python modules

# BEGIN 3rd party modules

# BEGIN PyQtxxx
import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, )
from qtpy.QtCore import (Signal, Slot, Property,)
__has_PySide6__ = False
__has_PyQt6__ =False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6
    from PySide6 import Shiboken
    # from PySide6.QtCore import (Signal, Slot, Property,)
    from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True
    from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    
__has_qtdbus__ = False
try:
    from qtpy import QtDBus
    __has_qtdbus__ = True
except:
    __has_qtdbus__ = False

# BEGIN About QStyle plugins
# WARNING: 2024-09-26 15:44:57
#
# A PtQtxxx stack pulled from PyPi or conda-forge, it is likely ot have a limited
# set of Qt styles available. In this case, there is nothing much that can be done. 
# Simply "copying" the style libraries available on the your platform won't do, 
# as this may crash Scipyen because they belong to a different build.
#
# The alternative is to build an environment locally (see install.sh) which
# WILL inolve building a local PyQt wheel. Incidentally, this will also build
# the vigra libraries loclly, from sources. Howeverm this option has its limitations
# due to embedded dependencies on the host platform.
#
# 
#
# END About QStyle plugins

# BEGIN pyqtdarktheme - recommended for Windows
# hasQDarkTheme = False
# try:
#     import qdarktheme
#     hasQDarkTheme = True
# except:
#     pass

# END pyqtdarktheme

# BEGIN qdarkstyle is another possibility (for windows)
# based entirely on style sheets
# hasQDarkStyle = False

# try:
#     import qdarkstyle
#     hasQDarkStyle = True
# except:
#     hasQDarkStyle = False

# END qdarkstyle

# END PyQtxxx

# BEGIN jupyter, ipython, qtconsole et al
from jupyter_client.session import Message
# from IPython.display import set_matplotlib_formats
from IPython.core.history import HistoryAccessor
from jupyter_core.paths import jupyter_runtime_dir
from qtconsole.svg import save_svg, svg_to_clipboard, svg_to_image
# from IPython.lib.deepreload import reload as dreload

# from IPython.core.autocall import ZMQExitAutocall

# BEGIN Configurable objects with traitlets.config
# NOTE: 2021-08-23 11:02:10
# ATTENTION do not import config directly, as it will override IPython's own
# 'config' object
import traitlets
from traitlets.utils.bunch import Bunch

# END Configurable objects with traitlets.config

# END jupyter, ipython, qtconsole et al

# BEGIN numerics & data visualization
# BEGIN data types & numerics
# NOTE: 2024-09-26 12:36:36
# vigra is imported via my own vigra_patches module
import numpy as np
import numpy.ma as ma
import pywt  # wavelets
import scipy
from scipy import io as sio
from scipy import stats
import sympy
import shapely
import neo
if neo.__version__ >= '0.13.0':
    from neo.core.objectlist import ObjectList as NeoObjectList
    
else:
    NeoObjectList = list # alias for backward compatibility :(
import h5py
import xarray as xa
import quantities as pq
# END data types & numerics

# BEGIN statistics, plotting and visualization (other than pyqtgraph)
# NOTE: 2024-09-26 12:40:27
# ptqtgraph is imported via gui.pyqtgraph_patch

import statsmodels.api as sm
import statsmodels.formula.api as smf
import statsmodels.stats as sms
import statsmodels.regression as smr
import patsy as pt
import pandas as pd  # for DataFrame and Series
import pingouin as pn  # nicer stats
import mpmath as mpm
#import researchpy as rp  # for use with DataFrames & stats -- not here ?!?
import joblib as jl  # to use functions as pipelines: lightweight pipelining in Python
import sklearn as sk  # machine learning, also nice plot_* functionality
import seaborn as sb  # statistical data visualization
# print("mainwindow.py __name__ =", __name__)

# BEGIN matplotlib modules
import matplotlib as mpl
if __has_PyQt6__ or __has_PySide6__: # still doesn't seem to work properly? see NOTE: 2025-06-22 22:38:23 in ScipyenWindow.newViewer(…)
    mpl.use("qtagg")
else:
    mpl.use("qt5agg")
from matplotlib._pylab_helpers import Gcf as Gcf
import matplotlib.mlab as mlb
import matplotlib.pyplot as plt

# BEGIN configure matplotlib
# NOTE: 2024-05-02 10:47:43
# the  next line is obsolete as os.environ["QT_API"] should take care of it ?
# mpl.use("Qtagg")
# mpl.use("Qt5Agg") #
# NOTE: 2021-08-17 12:17:08
# this is NOT recommended anymore
# import matplotlib.pylab as plb

mpl.rcParams["savefig.format"] = "svg"
mpl.rcParams["xtick.direction"] = "in"
mpl.rcParams["ytick.direction"] = "in"
mpl.rcParams["svg.fonttype"]="none"

# NOTE: 2017-08-24 22:48:45
# required to enable interaction with matplotlib plots
plt.ion()

# END configure matplotlib

# END matplotlib modules

# END statistics, plotting and visualization (other than pyqtgraph)

import colorama # for console output styles
# END numerics & data visualization

# END 3rd party modules

# BEGIN scipyen modules
from core import qtutils
from core import datazone
from core import datatypes
from core import basescipyen
from core import neoutils
from core import prog
from core import pyabfbridge as pab
from core import scipyen_plugin_loader
from core import scipyen_config as scipyenconf
from core import utilities
from core import (bgbridge, taxonbridge)

from core.basescipyen import BaseScipyenData

from core.datazone import (DataZone, Interval, 
                           intervals2cursors, intervals2epoch,
                           epoch2cursors, epoch2intervals)

from core.datasignal import (DataSignal, IrregularlySampledDataSignal,)
from core.datatypes import *

from core.prog import (safewrapper, deprecation, iter_attribute,
                       filter_type, filterfalse_type,
                       filter_attribute, filterfalse_attribute,
                       timefunc, timeblock, processtimefunc, 
                       processtimeblock, Timer, scipywarn, warn_with_traceback, 
                       get_properties, print_styled)

# NOTE: 2024-01-30 22:00:13
# use our own warning - OK for scipyen console
warnings.showwarning = prog.showwarning

from core.triggerevent import (DataMark, TriggerEvent, TriggerEventType, )
from core.triggerprotocols import TriggerProtocol
from core.traitcontainers import DataBag

from core.utilities import (summarize_object_properties,
                            augment_obj_prop_dict,
                            standard_obj_summary_headers,
                            safe_identity_test, unique, index_of, 
                            gethash, NestedFinder, normalized_index,
                            reverse_mapping_lookup)

import core.curvefitting as crvf
import core.data_analysis as anl
import core.desktoputils as desktoputils
import core.scipyen_quantities as cq
import core.strutils as strutils
from core.strutils import counter_suffix
import core.signalprocessing as sigp
import core.sysutils as sysutils
import core.tiwt as tiwt
import core.utilities as utilities
import core.xmlutils as xmlutils

from core.scipyen_config import (markConfigurable, confuse,
                                 saveWindowSettings, loadWindowSettings, )
from core.scipyen_config import scipyen_config as scipyen_settings
from core.scipyenmagics import ScipyenMagics
from core.strutils import InflectEngine
from core.scipyen_plugin_loader import reload
from core.vigra_patches import vigra
from core.workspacefunctions import *

from plots import plots as plots


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

from imaging import axisutils, vigrautils
from imaging import (imageprocessing as imgp, imgsim,)
from imaging.scandata import (AnalysisUnit, ScanData,)
from imaging.axiscalibration import (AxesCalibration,
                                     AxisCalibrationData,
                                     ChannelCalibrationData,
                                     CalibrationData)
from ephys import (ephys, membrane)
from systems import *

from gui.guiutils import (get_font_style, get_font_weight, treeWidgetItems)


from . import interact
from . import scipyen_colormaps as colormaps
from . import consoles
from . import scipyenviewer
from . import quickdialog as qd
# from . import resources_rc #as resources_rc
# from . import icons_rc
from . import pictgui as pgui
from . import xmlviewer as xv
from . import textviewer as tv
from . import tableeditor as te
from . import signalviewer as sv
from . import matrixviewer as matview
from . import imageviewer as iv
from . import dataviewer as dv
# from gui.pythonhelpwidget import PythonHelpWidget

from .consoles import styles, pstyles
from .cursors import (SignalCursor, SignalCursorTypes,DataCursor, 
                    cursors2epoch, cursors2intervals)
from .interact import (getInput, getInputs, packInputs, selectWSData)
from .itemslistdialog import ItemsListDialog
from .menuproxy import MenuProxy
from .triggerdetectgui import guiDetectTriggers
from .widgets import gradientwidgets
from .widgets import stylewidgets
from .widgets import colorwidgets
from .workspacegui import (WorkspaceGuiMixin, DirectoryObserver)
from .workspacemodel import WorkspaceModel
                    

from iolib import h5io, jsonio, network, navigation
from iolib import pictio as pio


from core.pyqtgraph_patch import pyqtgraph as pg

# from gui.cursors import (DataCursor, SignalCursor, SignalCursorTypes)
# END scipyen modules


# END import modules





# BEGIN 2022-02-21 15:43:38 check if NEURON python is installed
neuron_spec = importlib.util.find_spec("neuron")
has_neuron = neuron_spec is not None
# END

# BEGIN GUI themes according to platform (incomplete...)

# if sys.platform.startswith("linux"):
# END

# BEGIN scipyen core modules
# NOTE: 2017-04-16 09:48:15
# these are also imported into the console in slot_initQtConsole(), so they are
# available directly in the console
# also imports datetime & time; all become directly available in console, see
# NOTE: 2017-04-16 09:48:15 above

# import core.simulations as sim


# END scipyen core modules

# NOTE: 2025-01-07 12:37:46
# part of the singleton design pattern for main window
# see also traitlets.config.SingletonConfigurable
# SMW = typing.TypeVar("SMW", bound = "ScipyenWindow") # type variable representing the ScipyenWindow class


__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]
__scipyendir__ = os.path.dirname(__module_path__)


if "darwin" in sys.platform:
    altKeyDescr = "<Option>"
    ctrlKeyDescr = "<Command>"
else:
    altKeyDescr = "<ALT>"
    ctrlKeyDescr = "<CTRL>"


# BEGIN NOTE: 2022-04-07 22:39:44
# the code below supplemets the table of IPython's core completer latex symbols
# with extra unicode characters from Julia
# HOWEVER, Python 3 only supports a subset of these, for variable names (a.k.a
# identifiers)
# for example, the following are invalid variable names: 'a₀' or 'α₀', although
# they MAY be used in documetation; on the other hand the following ARE valid:
# 'a0', 'a_0', 'α0', or 'α_0'
# Since Unicode support is guaranteed in jupyter qtconsole (plain python REPL
# relies on the capabilities of the terminal) it is preferable to avoid using
# this code. There is no harm in using it, other than the annoyance of finding
# out that your fancy unicode identifier is not a valid identifier (the latex
# symbols tables in IPytyon.core.completer module is already filtered to allow
# only uncode glyphs acceptable in Python variable names)
##

# END NOTE: 2022-04-07 22:39:44

_valid_varname__regex_ = '^[A-Za-z_][A-Za-z0-9_]{1,30}$'

# _imported_modules__ = u'\n\nFor convenience, the following modules are imported (custom names indicated where appropriate):' +\
#     u'\n\nnumpy --> np\nmatplotlib --> mpl\nmatplotlib.pyplot --> plt\nmatplotlib.pylab --> plb\nmatplotlib.mlab --> mlb\n' +\
#     u'QtCore\nQtGui\ntypes\nsys\nos\n' +\
#     u'IPython.utils.ipstruct --> Struct' +\
#     u'\n\nAnd from the Pict package:\npictio --> pio\nsignalviewer --> sv\ndatatypes \nxmlutils' +\
#     u'\n\nTherefore ipython line magics such as %pylab or %mtplotlib, although still available, are not necessary anymore\n'

__is_pyinstaller_bundled__ = getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")

def checkVersion():
    verstr = None
    p = pathlib.Path(__scipyendir__)
    if p.parent.name == "src":
        # NOTE: 2025-05-21 21:50:37
        # This figures out if scipyen is being run off a local git repository; if it
        # does, then outputs a brief message about the git branch being used and its 
        # status (modified, or not, etc)
        # Then sets out a dynamic version based on the git branch, etc
        # NOTE: this code was previously in the scipyen.py launcher script
        try:
            repoDir = p.parent.parent
            if sysutils.checkGitRepo(repoDir, "Scipyen"):
                verstr = sysutils.getUnbuiltVersion(p)
                
        except:
            traceback.print_exc()
            
    if verstr is None:
        try:
            if __is_pyinstaller_bundled__:
                version_file = pathlib.Path(sys._MEIPASS).parent / "VERSION"
            else:
                version_file = pathlib.Path(__scipyendir__)/"VERSION"
                
            if version_file.exists():
                verstr = version_file.read_text(encoding="utf-8").strip("\n").strip()
        except:
            traceback.print_exc()
    
    return verstr
    
__verstr__ = checkVersion()

_qt_version_ = f"{QtCore.qVersion()}"
_qt_python_verstr_ = f"PySide6 {PySide6.__version__}" if __has_PySide6__ else f"{'PyQt6' if __has_PyQt6__ else 'PyQt5'} {qtpy.PYQT_VERSION}"
_scipyen_console_banner_ = f"Scipyen {__verstr__} internal console ({_qt_python_verstr_}, Qt {_qt_version_})\n" if isinstance(__verstr__, str) and len(__verstr__.strip()) else f"Scipyen internal console ({_qt_python_verstr_}, Qt {_qt_version_})\n"

# # # try:
# # #     # from setuptools_scm import get_version
# # #     # __version__ = get_version(root='..', relative_to=__file__)
# # # except:
# # #     traceback.print_exc()
# # #     _scipyen_console_banner_ = "Scipyen internal console\n"

_info_banner_ = ["\n*** NOTE: ***"]
_info_banner_.append(
    "User variables created in the console will become visible in the User variables tab in the main window.\n")
_info_banner_.append(
    "The Scipyen's main GUI window is accessible from the console as `mainWindow`.\n")
#_info_banner_.append("Except for user variables, if any of `mainWindow`, loaded modules are deleted from the console workspace by calling del(...), they can be restored using the `Console/Restore Namespace` menu item.\n")
_info_banner_.append("The Workspace dock widget of the Scipyen main window shows name space symbols ('bindings' of objects) in one of the following namespaces:.\n")
_info_banner_.append("\t'Internal': this is the 'user' namespace accessible directly in Scipyen's Console.\n")
_info_banner_.append("\t'kernel X', where 'X' is an integer ≥ 0: the 'user' namespace in an External Console.\n")
_info_banner_.append("In either case, the symbols of variables or modules that were, respectivly, creatd or imported during start up are HIDDEN, and can be revealed by calling 'dir' in the console frontend of the respective Jupyter process.\n")
_info_banner_.append("NOTE: An 'External console' operates in a completely independent Jupyter process, with its own, independent, namespace. \n")
_info_banner_.append("This process can be launched (and managed) by Scipyen (i.e. 'local'), or started independently ('remote'). The latter can be accessed via a 'connection' file\n")
_info_banner_.append("In Scipyen, there is a limited provision to copy simple objects across namespaces\n")
_info_banner_.append(
    "Here is a selection of useful python modules available in console (either the internal, Scipyen's console or an External console using a local Jupyter process)\n")
_info_banner_.append("Module: -> alias, where mentioned:")
_info_banner_.append("=================================")
_info_banner_.append("numpy -> np")
_info_banner_.append("matplotlib -> mpl")
_info_banner_.append("matplotlib.pyplot -> plt")
_info_banner_.append("matplotlib.matlab -> mlb")
_info_banner_.append("scipy")
_info_banner_.append("vigra")
_info_banner_.append("quantities -> pq")
_info_banner_.append("pyqtgraph -> pg")
_info_banner_.append("neo")
_info_banner_.append("\n")
_info_banner_.append("The following modules are from the underlying Qt framework")
_info_banner_.append("============================================")
_info_banner_.append("QtCore, QtGui, QtWidgets, QtXml")
# _info_banner_.append("QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml")
_info_banner_.append("\n")
_info_banner_.append("The following modules belong to Scipyen")
_info_banner_.append("============================================")
_info_banner_.append("signalviewer -> sv (*)   GUI for 1D signals + cursors")
_info_banner_.append("imageviewer -> iv (*)    GUI for images (VigraArray)")
_info_banner_.append("textviewer -> tv (*)     GUI for text data types")
_info_banner_.append("tableeditor --> te (*)   GUI for matrix data viewer")
_info_banner_.append("matrixviewer             GUI for matrix data viewer")
_info_banner_.append("pictgui -> pgui (*)      ancillary GUI stuff")
_info_banner_.append("pictio -> pio (*)        i/o functions")
_info_banner_.append(
    "datatypes                new python quantities and data types")
_info_banner_.append(
    "xmlutils                 GUI viewer for XML documents + utilities")
_info_banner_.append(
    "ephys                    electrophysiology routines")
_info_banner_.append(
    "tiwt                     wavelet functions + purelet denoise")
_info_banner_.append("curvefitting -> crvf")
_info_banner_.append("signalprocessing -> sigp")
_info_banner_.append("imageprocessing -> imgp")
_info_banner_.append("strutils                 string utilities")
_info_banner_.append(
    "plots                    matplotlib-based plotting routines")


def console_info():
    print("\n".join(_info_banner_))
    
# BUG: 2025-01-22 00:01:41 FIXME:
# WARNING: 2025-01-22 08:55:40 RESOLVED
# in scipyen.py by importing this module AFTER the QApplication is initialized
# see NOTE: 2025-01-22 08:56:42
# QWidget: Must construct a QApplication before a QWidget
from iolib.navigation import navigator

_mainwindow_ui_file = "mainwindow.ui"

if __has_PyQt6__ or __has_PySide6__:
    # Form class,        Base class
    __UI_MainWindow__, __QMainWindow__ = loadUiType(os.path.join(__module_path__, _mainwindow_ui_file))

    __UI_ScriptManagerWindow__, _ = loadUiType(os.path.join(__module_path__, "scriptmanagerwindow.ui"))

    __UI_AboutLicense__, _ = loadUiType(os.path.join(__module_path__, "AboutDialog.ui"))

else:
    # Form class,        Base class
    __UI_MainWindow__, _ = loadUiType(os.path.join(__module_path__, _mainwindow_ui_file), 
                                                    from_imports=True, import_from="gui")

    __UI_ScriptManagerWindow__, _ = loadUiType(os.path.join(__module_path__, "scriptmanagerwindow.ui"), 
                                               from_imports=True, import_from="gui")
    
    __UI_AboutLicense__, _ = loadUiType(os.path.join(__module_path__, "AboutDialog.ui"),
                                        from_imports=True, import_from="gui")

class WorkspaceViewer(QtWidgets.QTableView):
    r"""Inherits QTableView with customized drag & drop
    """

    def __init__(self, mainWindow=None, parent=None):
        super().__init__(parent=parent)

        self.dragStartPosition = QtCore.QPoint()

        self.mainWindow = mainWindow

    @safewrapper
    def mousePressEvent(self, event):
        # print("WorkspaceViewer.mousePressEvent")
        if event.button() == QtCore.Qt.LeftButton:
            self.dragStartPosition = event.pos()

        event.accept()

    @safewrapper
    def contextMenuEvent(self, event):
        # print("WorkspaceViewer.contextMenuEvent")
        # print(event.pos())
        self.customContextMenuRequested.emit(event.pos())

    @safewrapper
    def mouseMoveEvent(self, event):
        # print("WorkspaceViewer.mouseMoveEvent")
        # NOTE: 2019-08-10 00:24:01
        # create QDrag objects for each dragged item
        # ignore the DropEvent mimeData in the console ()
        if event.buttons() & QtCore.Qt.LeftButton:
            if (event.pos() - self.dragStartPosition).manhattanLength() >= QtWidgets.QApplication.startDragDistance():
                indexList = [i for i in self.selectedIndexes()
                             if i.column() == 0]

                if len(indexList) == 0:
                    return

                if not isinstance(self.mainWindow, ScipyenWindow):
                    return

                varNames = [self.mainWindow.workspaceModel.item(
                    index.row(), 0).text() for index in indexList]

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
# class WindowManager(ConfigurableQMainWindowMeta):

class ScriptManager(QtWidgets.QMainWindow, __UI_ScriptManagerWindow__, WorkspaceGuiMixin):
    signal_forgetScripts = Signal(object)
    signal_executeScript = Signal(str)
    signal_importScript = Signal(str)
    signal_pasteScript = Signal(str)
    signal_editScript = Signal(str)
    signal_openScriptFolder = Signal(str)
    signal_pythonFileReceived = Signal(str, QtCore.QPoint)
    signal_pythonFileAdded = Signal(str)
    signal_scriptManagerClosed = Signal()

    # NOTE recently run scripts is managed by ScipyenWindow instance mainWindow
    # FIXME 2021-09-18 14:16:14 Change this so that it is managed instead by
    # ScriptManager
    # We then need to connect pasting/dropping script file onto Scipyen mainWindow
    # or the internal console to script execution and adding of script file to
    # the internal scripts list  here.

    def __init__(self, parent=None, scipyenWindow=None):
        super(ScriptManager, self).__init__(parent)
        self.setupUi(self)
        WorkspaceGuiMixin.__init__(self, parent=parent,scipyenWindow=scipyenWindow)
        self._configureUI_()

        self.setWindowTitle("Scipyen Script Manager")

        self.loadSettings()

    def _configureUI_(self):
        addScript = self.menuScripts.addAction("Add scripts...")
        addScript.triggered.connect(self.slot_addScripts)
        self.scriptsTable.customContextMenuRequested[QtCore.QPoint].connect(
            self.slot_customContextMenuRequested)
        self.scriptsTable.cellDoubleClicked[int, int].connect(
            self.slot_cellDoubleClick)
        self.scriptsTable.setSortingEnabled(True)
        # self.scriptsTable.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.acceptDrops = True
        self.scriptsTable.acceptDrops = True

    def closeEvent(self, evt):
        self.saveSettings()
        evt.accept()
        self.close()

        evt.accept()
        # self.signal_scriptManagerClosed.emit()

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
            # print(f"ScriptManager.setData {k}: key={key}, value={value}")
            path_item = QtWidgets.QTableWidgetItem(key)
            path_item.setToolTip(key)

            script_item = QtWidgets.QTableWidgetItem(value)
            script_item.setToolTip(value)

            self.scriptsTable.setItem(k, 0, script_item)
            self.scriptsTable.setItem(k, 1, path_item)

        # self.scriptsTable.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.scriptsTable.resizeColumnToContents(0)

    @safewrapper
    def dragEnterEvent(self, event):
        event.acceptProposedAction()
        event.accept()

    @safewrapper
    def dropEvent(self, evt):
        if evt.mimeData().hasUrls():
            urls = evt.mimeData().urls()
            for url in urls:
                if (url.isRelative() or url.isLocalFile()) and os.path.isfile(url.path()):
                    # check if this is a python source file
                    mimeType = QtCore.QMimeDatabase().mimeTypeForFile(QtCore.QFileInfo(url.path()))
                    # print(mimeType.name())
                    if all([s in mimeType.name() for s in ("text", "python")]):
                        self.signal_pythonFileAdded.emit(url.path())

            # if len(urls) == 1 and (urls[0].isRelative() or urls[0].isLocalFile()) and os.path.isfile(urls[0].path()):
                # check if this is a python source file
                # mimeType = QtCore.QMimeDatabase().mimeTypeForFile(QtCore.QFileInfo(urls[0].path()))
                # print(mimeType.name())
                # if all([s in mimeType.name() for s in ("text", "python")]):
                    # self.signal_pythonFileAdded.emit(urls[0].path())

        evt.accept()

    def clear(self):
        self.scriptsTable.clearContents()
        self.scriptsTable.setRowCount(0)
        
    @property
    def scriptsCount(self):
        return self.scriptsTable.rowCount()

    @property
    def scriptNames(self):
        return [self.scriptsTable.item(row, 0).text() for row in range(self.scriptsTable.rowCount())]

    @property
    def scriptFileNames(self):
        return [self.scriptsTable.item(row, 1).text() for row in range(self.scriptsTable.rowCount())]

    @Slot("QPoint")
    @safewrapper
    def slot_customContextMenuRequested(self, pos):
        items = self.scriptsTable.selectedItems()

        cm = QtWidgets.QMenu("Open Scripts Manager", self)
        # actions = list()

        if len(items):
            if len(items) == 1:
                execItem = cm.addAction("Run")
                execItem.setToolTip("Execute selected script")
                execItem.triggered.connect(self.slot_executeScript)

                # actions.append(execItem)

                pasteItem = cm.addAction("Paste in Console")
                pasteItem.setToolTip("Paste script contents in console")
                pasteItem.triggered.connect(self.slot_teleportScript)

                # actions.append(pasteItem)

                editItem = cm.addAction("Edit")
                editItem.setToolTip(
                    "Edit script in system's default text editor")
                editItem.triggered.connect(self.slot_editScript)

                openFolderItem = cm.addAction("Open Containing Folder")
                openFolderItem.setToolTip("Open Containing Folder")
                openFolderItem.triggered.connect(self.slot_openScriptFolder)

            cm.addSeparator()

            delItems = cm.addAction("Forget")
            delItems.setToolTip("Forget selected scripts")
            delItems.triggered.connect(self.slot_forgetScripts)
            # actions.append(delItems)

            clearAction = cm.addAction("Forget All")
            clearAction.setToolTip("Forget All")
            clearAction.triggered.connect(self.slot_forgetAll)

        # actions.append(clearAction)
        cm.addSeparator()
        registerScript = cm.addAction("Add script...")
        registerScript.triggered.connect(self.slot_addScript)

        cm.popup(self.scriptsTable.mapToGlobal(pos))

    @Slot(int, int)
    @safewrapper
    def slot_cellDoubleClick(self, row, col):
        item = self.scriptsTable.item(row, 1)

        self.signal_executeScript.emit(item.text())

    @Slot()
    @safewrapper
    def slot_addScript(self):
        targetDir = os.getcwd()
        fileFilter = "Python script (*.py)"
        fileName = self.chooseFile(caption=u"Add python script",
                                   fileFilter="Python script (*.py)",
                                   targetDir=targetDir)

        # print(f"ScriptManager.slot_addScript fileName: { fileName}" )

        if isinstance(fileName, tuple):
            # NOTE: PyQt5 QFileDialog.getOpenFileName returns a tuple (fileName, filter string)
            fileName, fileFilter = fileName

        if pio.checkFileReadAccess(fileName):
            mime_file_type = pio.getMimeAndFileType(fileName)
            # print(f"ScriptManager.slot_addScript {mime_file_type}")
            # for s in mime_file_type:
            # print(f"ScriptManager.slot_addScript s: {s}, type: {type(s).__name__}")
            if any("python" in s for s in mime_file_type if isinstance(s, str)):
                self.signal_pythonFileAdded.emit(fileName)

            elif any("text" in s for s in mime_file_type if isinstance(s, str)) and os.path.splitext(fileName)[-1] == ".py":
                self.signal_pythonFileAdded.emit(fileName)

    @Slot()
    @safewrapper
    def slot_addScripts(self):
        targetDir = os.getcwd()

        # NOTE: returns a tuple (path list, filter)
        # fileNames, fileFilter = QtWidgets.QFileDialog.getOpenFileNames(self, caption=u"Run python script", filter="Python script (*.py)", directory = targetDir)

        fn, fl = self.chooseFile(caption=u"Add python scripts",
                                 filter="Python script (*.py)",
                                 targetDir=targetDir,
                                 single=False)

        if pio.checkFileReadAccess(fn):
            for fileName in fn:
                mft = pio.getMimeAndFileType(fileName)
                if any("python" in s for s in mft):
                    self.signal_pythonFileAdded.emit(fileName)

    @Slot()
    @safewrapper
    def slot_forgetScripts(self):
        if len(self.scriptsTable.selectedItems()) == 0:
            return

        rows = list(set([i.row() for i in self.scriptsTable.selectedItems()]))

        items = [self.scriptsTable.item(r, 1).text() for r in rows]

        for r in rows:
            self.scriptsTable.removeRow(r)

        self.signal_forgetScripts.emit(items)

    @Slot()
    @safewrapper
    def slot_forgetAll(self):
        items = [self.scriptsTable.item(r, 1).text()
                 for r in range(self.scriptsTable.rowCount())]

        self.scriptsTable.clearContents()
        self.scriptsTable.setRowCount(0)

        self.signal_forgetScripts.emit(items)

    @Slot()
    @safewrapper
    def slot_executeScript(self):
        if len(self.scriptsTable.selectedItems()) != 1:
            return

        row = [i.row() for i in self.scriptsTable.selectedItems()][0]

        item = self.scriptsTable.item(row, 1).text()

        self.signal_executeScript.emit(item)

    @Slot()
    @safewrapper
    def slot_importAsModule(self):
        if len(self.scriptsTable.selectedItems()) != 1:
            return

        row = [i.row() for i in self.scriptsTable.selectedItems()][0]

        item = self.scriptsTable.item(row, 1).text()

        self.signal_importScript.emit(item)

    @Slot()
    @safewrapper
    def slot_editScript(self):
        if len(self.scriptsTable.selectedItems()) != 1:
            return

        row = [i.row() for i in self.scriptsTable.selectedItems()][0]

        item = self.scriptsTable.item(row, 1).text()

        self.signal_editScript.emit(item)

    @Slot()
    @safewrapper
    def slot_openScriptFolder(self):
        if len(self.scriptsTable.selectedItems()) != 1:
            return

        row = [i.row() for i in self.scriptsTable.selectedItems()][0]

        item = self.scriptsTable.item(row, 1).text()

        self.signal_openScriptFolder.emit(item)

    @Slot()
    @safewrapper
    def slot_teleportScript(self):
        if len(self.scriptsTable.selectedItems()) != 1:
            return

        row = [i.row() for i in self.scriptsTable.selectedItems()][0]

        item = self.scriptsTable.item(row, 1).text()

        self.signal_pasteScript.emit(item)
        
# NOTE 2019-09-12 09:34:31
# Beginning to consolidate variable handling in the GUI framework
# TODO: make this configurable (a mime type-like mechanism?)
# class VTH(QtCore.QObject):
class VTH(object):
    r"""Variable Type Handler.
    Centralized the handling of Python object types with Scipyen viewers.
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

    default_handlers = {mpl.figure.Figure: {"action": "Plot (matplotlib)",
                                            "types": {np.ndarray: 99, tuple: 99, list: 99}}}

    gui_handlers = deepcopy(default_handlers)

    def get_handler_spec(obj):
        r"""Returns a list of specifications for handling `varget_handler_speciable`.

        If `obj` is a type registered with VTH, or `obj` is an
        instance of a type registered with VTH, or a unary predicate (see ``prog.is_predicate``),
        returns a 3-tuple:
        (viewer type, action name, priority), where:

            • viewer type is the Scipyen viewer class suitable to view the type

            • action name (str) - the name of the menu action for viewing the
                obj (in the workspace viewer context menu)

            • priority (int) - used when several viewer types can handle the 
                same obj name; the viewer class with the highest priority
                for the given type is used first

        The returned list is sorted by descending order of priority and ascending
        order of action name.

        """
        if inspect.isclass(obj) or isinstance(obj, type):
            objtype = obj
        else:
            objtype = type(obj)
            
        # if isinstance(obj, str):
        #     print(obj[:10])

        # NOTE: 2026-01-16 11:02:34
        # skip types and Qt widgets as there is no need to handle these: 
        # types are described at the console, and widgets — well, they just show themselves ⌣
        if objtype in VTH.gui_handlers.keys() or QtWidgets.QWidget in inspect.getmro(objtype):
            return list()

        objtypemro = inspect.getmro(objtype)
        act_np = set()

        for k, v in VTH.gui_handlers.items():
            v_types = list(filter(lambda x: isinstance(x, type), v["types"].keys()))
            v_predicates = list(filter(lambda x: prog.is_predicate(x), v["types"].keys()))
            # print(f"VTH.get_handler_spec: v_types = {v_types}, v_predicates = {v_predicates}")
            # if len(v_predicates):
                # print(f"\tv_predicates for {k} = {v_predicates}")
            
            for vpred in v_predicates:
                # print(f"\t\t{vpred}() -> {vpred(obj)}")
                if vpred(obj):
                    # print(f"\t\t\tadding{(k, v['action'],  v['types'][vpred])}")
                    #           viewer type,   action name   priority
                    act_np.add((k,             v["action"],  v["types"][vpred]))
                    
            for vtype in objtypemro:
                if vtype in v_types:
                    if len(v_predicates):
                        for vpred in v_predicates:
                            # print(f"\t\tvtype: {vtype} -> {vpred}() -> {vpred(obj)}")
                            if vpred(obj):
                                # print(f"\t\t\tadding{(k, v['action'],  v['types'][vpred])}")
                                #           viewer type,   action name   priority
                                act_np.add((k,             v["action"],  v["types"][vtype]))
                    else:
                        #           viewer type,   action name   priority
                        # print(f"\t\t\tvtype: {vtype} -> adding{(k, v['action'],  v['types'][vtype])}")
                        act_np.add((k,             v["action"],  v["types"][vtype]))
                    
        if len(act_np):
            # print(f"act_np = {act_np}")
            # sort in ascending order by action name, and in descending order by
            # priority
            actions = sorted(sorted(list(act_np), key=lambda x: x[1]), key=lambda x: x[2], reverse=True)
            return actions

        return list()

    def reset_all():
        r"""Resets all gui handlers to the default.
        This will remove any registered custom viewer!
        """
        VTH.gui_handlers = deepcopy(VTH.default_handlers)

    def reset_handler(viewerClass):
        r"""Resets the configuration for the built-in viewer types.
        Does nothing for user-designed viewer that have been registered manually.
        """
        if viewerClass in VTH.default_handlers:
            VTH.gui_handlers[viewerClass] = deepcopy(
                VTH.default_handlers[viewerClass])

class AboutDialog(QtWidgets.QDialog, __UI_AboutLicense__):
    def __init__(self, txt, parent, aboutSuffix:typing.Optional[str] = None):
        QtWidgets.QDialog.__init__(self, parent)
        self._configureUI_()
        
        self.textBrowser.setHtml(txt)
        wintitle = f"About {aboutSuffix}"
        self.setWindowTitle(wintitle)
        self.show()
        
    def _configureUI_(self):
        self.setupUi(self)
        self.textBrowser.anchorClicked.connect(self.slot_openLink)
        
    @Slot(QtCore.QUrl)
    def slot_openLink(self, link:QtCore.QUrl):
        # print(f"{self.__class__.__name__}.slot_openLink: {link.scheme()}")
        if link.scheme() == "scipyen":
            # NOTE: 2025-06-02 16:42:38
            # this below needs to take into account the casefolding in Urls
            cmd = link.toString().replace("scipyen://", "")
            # print(f"cmd: {cmd}")
            method = getattr(self.parent(), cmd, None)
            if inspect.ismethod(method):
                try:
                    method.__call__()
                except:
                    traceback.print_exc()
        elif not link.isRelative():
            QtGui.QDesktopServices.openUrl(link)
                
        
class ScipyenWindow(QtWidgets.QMainWindow, __UI_MainWindow__, WorkspaceGuiMixin):
    ''' Main pict GUI window
    '''
    _instance = None
    workspaceChanged = Signal()
    startPluginLoad = Signal()
    sig_refreshRecentFilesMenu = Signal()
    sig_windowRemoved = Signal(tuple, name="sig_windowRemoved")
    sig_splashMessage = Signal(str, name = "sig_splashMessage")
    
    sig_changedDirectory = Signal(str, name="sig_changedDirectory")
    sig_newItemsInMonitoredDir = Signal(tuple, name="sig_newItemsInMonitoredDir")
    sig_itemsRemovedFromMonitoredDir = Signal(tuple, name="sig_itemsRemovedFromMonitoredDir")
    sig_itemsChangedInMonitoredDir = Signal(tuple, name="sig_itemsChangedInMonitoredDir")

    # TODO: 2021-11-26 17:23:45 To add:
    # saveFile, runScript, showObj, sysOpen, editor
    #
    _export_methods_ = (("slot_importPrairieView", "importPrairieView"),
                        ("openFile", "openFile"),
                        ("openFile", "openFile"),
                        ("slot_selectWorkDir", "selectWorkingDirectory"),
                        ("slot_showScriptsManagerWindow", "scritpsManager"),
                        )

    # class attribute
    pluginActions:list = []

    defaultShellCacheSize:int = 10000
    
    _defaultUIFont:QtGui.QFont = QtWidgets.QApplication.font()
    
    _useDefaultQApplicationFont:bool = True
    
    _defaultIconSize_:int = 16
    
    _defaultNewNavigatorLook_:bool = False
    
    _defaultUseNativeMenuBar:bool = True

    _instance = None # NOTE: Singleton design pattern
    
    @classmethod
    def _walk_mro(cls) -> typing.Generator[typing.Self, None, None]:
        r"""Walk the cls.mro() for parent classes that are also singletons

        For use in instance()
        """
        # NOTE: Singleton design pattern
        # NOTE: 2025-01-07 12:42:39
        # see traitlets.config.SingletonConfigurable
        for subclass in cls.mro():
            if (
                issubclass(cls, subclass)
                and issubclass(subclass, typing.Self)
                # and issubclass(subclass, SMW)
                # and subclass != SMW
                and subclass != typing.Self
            ):
                yield subclass

    @classmethod
    def initialized(cls:typing.Self) -> bool:
        # NOTE: Singleton design pattern
        return hasattr(cls, "_instance" and isinstance(cls._instance, cls))

    @classmethod
    def instance(cls:typing.Self, *args, **kwargs) -> typing.Self:
        # if __has_PyQt6__:
        #     return
        # NOTE: Singleton design pattern
        if cls._instance is None:
            inst = cls(*args, **kwargs)
            for subclass in cls._walk_mro():
                subclass._instance = inst
        if hasattr(cls, "_instance") and isinstance(cls._instance, cls):
            return cls._instance
        else:
            raise RuntimeError(f"Incompatible sibling of '{cls.__name__}' is already instantiated as singleton: {type(cls._instance).__name__}")

    # NOTE: 2016-04-17 16:11:56
    # argument and return variable parsing moved to _installPluginFunction_
    def _inputPrompter_(self, n_outputs=0, arg_types=None, arg_names=None, arg_defaults=None, var_args=None, kw_args=None):
        '''
        Decorator to prompt user with a dialog for the arguments that are to be 
        dispatched to function f.

        Parameters:

        See Python Wiki / PythonDecoratorLibrary / Creating well behaved decorators
        '''

        # print(n_outputs)
        def fs(a, b):
            return ''.join((a, b))

        def prompt_f(f):
            '''
            Does the actual function call of the wrapped plugin function
            '''
            # print(f"_inputPrompter_ {f.__module__}.{f.__name__} arg_types: {arg_types}")
            try:
                if arg_types is not None and ((isinstance(arg_types, (tuple, list)) and len(arg_types)) or isinstance(arg_types, type)):
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
                            dictargs = [[interpret_str(j.strip()) for j in i.split(
                                '=')] for i in varstr.split(',')]
                            print(len(dictargs))
                            dct = dict()

                            for k, e in enumerate(dictargs):
                                if len(e) == 2:
                                    dict[e[0]] = e[1]
                                else:
                                    print(
                                        "expected key=value pair at element %d in keyword list" % k)

                            return dict()

                        # prepare the dialog
                        d = qd.QuickDialog(self, "Enter Arguments")
                        d.promptWidgets = []
                        d.varPromptWidget = None
                        d.kwPromptWidget = None
                        d.returnWidgets = []
                        args = []

                        for (a, b, c) in zip(arg_types, arg_names, arg_defaults):
                            if isinstance(a, type):
                                if a.__name__ in ('int', 'long'):
                                    widgetClass = qd.IntegerInput
                                elif a.__name__ == 'float':
                                    widgetClass = qd.FloatInput
                                elif a.__name__ == 'str':
                                    widgetClass = qd.StringInput
                                elif a.__name__ == 'bool':
                                    widgetClass = qd.CheckBox
                                else:
                                    widgetClass = qd.InputVariable

                                promptWidget = widgetClass(
                                    d, b + " (" + a.__name__ + ")")

                                if c is not None:
                                    if isinstance(a, type):
                                        if a.__name__ in ("int", "long", "float"):
                                            promptWidget.setValue(str(c))
                                        elif a.__name__ == "str":
                                            promptWidget.setText(c)
                                        elif a.__name__ == "bool":
                                            promptWidget.setChecked(c)

                            elif isinstance(a, str) and a == '~':
                                # this means the function expects a variable selected
                                # in the workspace table
                                # therefore we don't need a prompt widget for it
                                promptWidget = None  # so that argument parsing below works
                                pass
                            else:
                                raise ValueError(
                                    "Incorrect input type was supplied")

                            d.promptWidgets.append(promptWidget)

                        if var_args is not None:
                            d.varPromptWidget = qd.InputVariable(
                                d, "Variadic arguments: ")

                        if kw_args is not None:
                            d.kwPromptWidget = qd.InputVariable(
                                d, "Keyword arguments: ")

                        if n_outputs > 0:
                            d.addLabel('Return variable names:')
                            ret_names = map(
                                fs, ['var '] * n_outputs, map(str, range(n_outputs)))
                            suggested_ret_names = map(
                                fs, ['var_'] * n_outputs, map(str, range(n_outputs)))

                            print("type of ret_names: ", type(ret_names))

                            rt_nm = [i for i in ret_names]

                            srt_nm = [i for i in suggested_ret_names]

                            for k in range(n_outputs):
                                widget = qd.OutputVariable(d, rt_nm[k])
                                widget.setText(srt_nm[k])
                                d.returnWidgets.append(widget)

                        if d.exec_() == 0:
                            return  # don't call anything, just return nothing

                        # NOTE: 2016-04-15 03:19:05
                        # deal with positional arguments
                        for (a, b) in zip(arg_types, d.promptWidgets):
                            if isinstance(a, type) and b is not None:
                                if a.__name__ in ('int', 'float', 'long'):
                                    if len(b.text()) == 0:
                                        return  # in case field was empty
                                    args.append(b.value())
                                elif a.__name__ == 'bool':
                                    args.append(b.selection())
                                elif a.__name__ == 'str':
                                    if b.text() == "None":
                                        args.append(None)
                                    elif b.text() == '~':
                                        selVarName = self.getCurrentVarName()
                                        if selVarName is not None:
                                            args.append(
                                                self.workspace[selVarName])
                                        else:
                                            args.append(None)
                                    else:
                                        args.append(b.text())
                                else:
                                    args.append(self.workspace[b.text()])

                            # b SHOULD be None here
                            elif isinstance(a, str) and a == '~' and b is None:
                                selVarName = self.getCurrentVarName()
                                if selVarName is not None:
                                    args.append(self.workspace[selVarName])

                            else:
                                raise TypeError(
                                    "incorrect parameter type in type list")

                        # NOTE: 2016-04-15 03:19:30
                        # deal with variadic arguments
                        if (var_args is not None and len(d.varPromptWidget.text()) > 0):
                            vastrlist = d.varPromptWidget.text().split('.')
                            valist = [interpret_str(i.strip())
                                      for i in vastrlist]
                            args = args + valist

                        # NOTE: 2016-04-15 03:20:00
                        # deal with keyword arguments
                        if (kw_args is not None and len(d.kwPromptWidget.text()) > 0):
                            kwargs = parsekw(d.kwPromptWidget.text())
                            # no need to return anything here
                            ret = f(*args, **kwargs)
                        else:
                            ret = f(*args)  # no need to return anything here

                        # NOTE: 2016-04-15 03:20:13
                        # finally, deal with return variables
                        if (n_outputs > 0 and ret is not None):
                            if type(ret) in (tuple, list):
                                for k in range(len(ret)):
                                    var_name = d.returnWidgets[k].text()
                                    # self.workspace[var_name] = ret[k]
                                    self.workspaceModel.bindObjectInNamespace(var_name, ret[k])
                            else:
                                var_name = d.returnWidgets[0].text()
                                # self.workspace[var_name] = ret
                                self.workspaceModel.bindObjectInNamespace(var_name, ret)

                        # NOTE: 2016-04-17 22:18:05
                        # do this always: functions that do not return but take mutable arguments
                        # from the workspace may result in these arguments being modified and
                        # we'd like this to be seen in the workspace table
                        #
                        # and do it from within inner_f
                        # self.workspaceModel.update()
                        # NOTE: 2016-04-17 16:26:33
                        # inner_f does not need to return anything

                else:
                    def inner_f():
                        if n_outputs > 0:
                            d = qd.QuickDialog(
                                self, "Enter Return Variable Names")
                            d.returnWidgets = []
                            ret_names = map(
                                fs, ['var '] * n_outputs, map(str, range(n_outputs)))
                            suggested_ret_names = map(
                                fs, ['var_'] * n_outputs, map(str, range(n_outputs)))
                            for k in range(n_outputs):
                                widget = qd.OutputVariable(d, ret_names[k])
                                widget.setText(suggested_ret_names[k])
                                d.returnWidgets.append(widget)
                            d.adjustSize()
                            
                            if d.exec_() == 0:
                                return  # don't call anything, just return nothing

                        ret = f()

                        if (n_outputs > 0 and ret is not None):
                            if type(ret) in (tuple, list):
                                for k in range(len(ret)):
                                    var_name = d.returnWidgets[k].text()
                                    # self.workspace[var_name] = ret[k]
                                    self.workspaceModel.bindObjectInNamespace(var_name, ret[k])
                            else:
                                var_name = d.returnWidgets[0].text()
                                # self.workspace[var_name] = ret
                                self.workspaceModel.bindObjectInNamespace(var_name, ret)

                        # NOTE: 2016-04-17 22:18:05
                        # do this always: functions that do not return but take mutable arguments
                        # from the workspace may result in these arguments being modified and
                        # we'd like this to be seen
                        #
                        # and do it from within inner_f
                        # self.workspaceModel.update()

                        # NOTE: 2016-04-17 16:27:01
                        # inner_f does not need to return anything

                inner_f.__name__ = f.__name__
                inner_f.__doc__ = f.__doc__
                inner_f.__dict__.update(f.__dict__)

                return inner_f

            except Exception as e:
                traceback.print_exc()

        return prompt_f

    # NOTE: 2016-04-17 16:14:18
    # argument parsing code moved to _installPluginFunction_ in order to keep
    # this decorator small: this decorator should only do this: DECORATE
    def slot_wrapPluginFunction(self, f, n_outputs=0, arg_types=None, arg_names=None, arg_default=None, var_args=None, kw_args=None):
        '''
        Defines a new slot for plugins functionality.
        Connected to the `triggered` signal of dynamic QActions for plugins.
        '''
        # NOTE: 2016-04-17 16:16:52 moved to _installPluginFunction_
        # NOTE:2016-04-17 15:39:03 in python 3 use inspect.getfullargspec(f)
        # argSpec = inspect.getfullargspec(f)
        # kwa = argSpec.keywords

        # NOTE: 2016-04-17 16:18:18 to reflect new code layout
        @Slot()
        @self._inputPrompter_(n_outputs, arg_types, arg_names, arg_default, var_args, kw_args)
        def sw_f(*arg_types, **kw_args):
            return f(*arg_types, **kw_args)

        sw_f.__name__ = f.__name__
        sw_f.__doc__ = f.__doc__
        sw_f.__dict__.update(f.__dict__)

        if hasattr(f, '__annotations__'):
            sw_f.__setattr__('__annotations__', getattr(f, '__annotations__'))

        # print(f"slot_wrapPluginFunction in @self._inputPrompter_ {f.__module__}.{f.__name__} arg_types {arg_types} kw_args {kw_args}")
        return sw_f
    
    # NOTE: 2025-01-10 22:44:49 WARNING Subclassing ScipyenWindow
    # Made this into a singleton class - such that there is only one instance
    # alive at any time; however, this behaviour propagates to its subclasses 
    # also (if any)
    
    # NOTE: 2025-06-20 23:27:26 WARNING
    # this crashes in PyQt6!
    if not __has_PyQt6__:
        def __new__(cls:typing.Self, parent: typing.Optional[QtWidgets.QWidget] = None, *args, **kwargs) -> typing.Self:
            if not hasattr(cls, "_instance") or not isinstance(cls._instance, cls):
                if __has_PyQt6__:
                    cls._instance = super(ScipyenWindow, cls).__new__(cls, parent)
                else:
                    cls._instance = super(ScipyenWindow, cls).__new__(cls, parent, *args, **kwargs)
                
            # print(f"\t{cls.__name__}._instance = {cls._instance}")
            
            return cls._instance
    
    # @processtimefunc
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None, *args, **kwargs):
        r"""Scipyen's main window initializer (constructor).

        Parameters:
        ===========
        app: QtWidgets.QApplication. The Qt application instance. 
            This instance runs the main GUI event loop and therefore there can 
            be only one throughout a Scipyen session (i.e., is a 'singleton').

            All Scipyen facilities (or 'apps', e.g., LSCaT, LTP, both internal 
            and external consoles, etc.) run under this event loop, which should
            not be confused with the IPython's REPL that runs with each console.

        settings: confuse.LazyConfig Optional (default is None) 
            The database containing non-Qt configuration data, global to Scipyen.
            This is where configurable objects (including facilities or 'apps')
            store their non-Qt related settings.

        parent: QtWidgets.QWidget or None (default).
        
        Var-keyword parameters:
        -----------------------
        splash: instance of gui.splash.ScipyenSplashWidget
            WARNING: Buggy - if using it, then expect to not see a native menu bar
            in the global menu app, in KDE; in such case it is best to switch OFF
            "Use Native Menu Bar" in the settings menu.
        """
        # BUG: 2025-07-01 10:47:08 FIXME
        # even if the code is here, I'm actually NOT using a splash screen as it
        # (currently) prevents the native menu bar from being shown
        
        from gui.splash import ScipyenSplashWidget
        if sys.platform.startswith("win32") or os.name == "nt" or platform.uname().system == "Windows":
            myparent = None
        else:
            myparent=self
            
        super().__init__(parent)
        WorkspaceGuiMixin.__init__(self, parent=myparent)
        
        self.__version__ = __verstr__

        # NOTE: singleton design pattern
        # see traitlets.config.SingletonConfigurable
        self.__class__._instance = self  
        
        # NOTE: 2023-01-08 16:14:26 - set this early !
        # the global singleton instance of the QApplication running Scipyen
        self.app = QtWidgets.QApplication.instance()
        
        # NOTE: 2025-07-01 09:41:01
        # DO NOT call this now -> it will mess up the native menu bar (i.e. it won't
        # be visible) - not sure why...
        # self.app.processEvents()
        
        splash = kwargs.get("splash", None)
        if isinstance(splash, ScipyenSplashWidget):
            self.sig_splashMessage[str].connect(splash._slot_showMessage, QtCore.Qt.QueuedConnection)

        # gui_viewers defined in gui package (see gui/__init__.py)
        # self.viewers = dict(map(lambda x: (x, list()), gui_viewers))
        # for matplotlib figures
        # self.viewers[mpl.figure.Figure] = list()
        
        # NOTE: 2024-05-31 13:12:31
        # This is a dictionary mapping viewer class (key) ↦ list of instances of viewr class in the workspace
        self.viewers = {mpl.figure.Figure: list()}

        # self.currentViewers = dict(map(lambda x: (x, None), gui_viewers))
        # self.currentViewers[mpl.figure.Figure] = None

        self.currentViewers = {mpl.figure.Figure: None}
        
        # self._pyinstaller_bundled_ = kwargs.pop("pyinstaller_bundled", False)
        self._pyinstaller_bundled_ = getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")
        
        # NOTE: 2022-12-25 10:41:12
        # a mapping of plugin_module ↦ {plugin_module_function ↦ QAction}
        self._ui_plugins_ = dict()
        
        self._userenv_varname_ = "USERPROFILE" if sys.platform.startswith("win32") else "HOME"
        self._user_home_ = os.getenv(self._userenv_varname_)
        
        # NOTE: 2024-05-29 13:07:37
        # additional top plugin directory, where users can place their own plugins
        # (in addition to self._scipyendir_)
        self._default_scipyen_user_plugins_dir = os.path.join(self._user_home_, "scipyen_plugins")
        
        self._user_plugins_dir = self._default_scipyen_user_plugins_dir
        # self._external_HDF5_viewer: str = str()         # NOTE: 2025-03-24 21:35:03 NOT USED

        self._font = QtGui.QFont(self._defaultUIFont)
        self._workspaceViewerFont = QtGui.QFont(self._defaultUIFont)
        self._commandHistoryFont = QtGui.QFont(self._defaultUIFont)
        
        
        # BEGIN configurables; for each of these we define a read-write property
        # decorated with markConfigurable
        self._recentFiles = collections.OrderedDict()
        self._recentDirectories = collections.deque()
        self._fileSystemFilterHistory = collections.deque()
        self._lastFileSystemFilter = str()
        self._recentVariablesList = collections.deque()
        self._lastVariableFind = str()
        self._commandHistoryFinderList = collections.deque()
        self._lastCommandFind = str()
        # self._recentScripts = list()
        self._recentScripts = deque()
        self._recent_scripts_dict_ = dict()
        self._showFilesFilter = False
        self._console_docked_ = False
        self._script_manager_autolaunch = False
        self._auto_remove_viewers_ = False
        self._wspace_headers_ = [k for k in standard_obj_summary_headers if k != "Icon"]
        
        self._useSystemDefaultFont:bool = self._useDefaultQApplicationFont
        
        self._useLastHistoryCommandSearch_:bool = False
        
        self._useNativeMenuBar:bool = self._defaultUseNativeMenuBar
        
        # ### END configurables, but see NOTE:2022-01-28 23:16:57 below

        self.navPrevDir = collections.deque()
        self.navNextDir = collections.deque()
        self._currentDir_ = None
        self._nMaxWatchedDirectories_ = 1
        self._nMaxWatchedFiles_= 1
        # self._isDirWatching_ = False
        self._fileSystemChanged_ = False
        self._changesInWatchedDir_ = False
        self._monitoredDirsCache_ = dict()
        
        self.sig_splashMessage.emit("Scipyen is initializing, please wait...")
        
        # self.__version__ = checkVersion() 
        
        # ### BEGIN long comment - wrap it for KDE's Kate
        # NOTE: 2023-05-27 22:00:37
        # self._init_QtConsole_ will asign to self.workspace a reference to the 
        # user's shell namespace that the user has direct access to, inside the 
        # Console.
        #
        # The contents of the workspace are "observed" by the workspaceModel so
        # that the addition/removal or modification of objects in the workspace
        # are reflected in the workspace viewer.
        # 
        # To ensure that the workspace viewer is automatically updated when an 
        # object is added to/modified/removed from the user workspace, call
        # 'workspaceModel.bindObjectInNamespace(...)' - see the docstring of that
        # method for details.
        #
        # Unless an object in the workspace is 'hidden' to the viewer, it is 
        # monitored by the workspace model and changes usually reflected in the 
        # workspace viewer.
        #
        # EXCEPTIONS to this 'rule' are the cases of objects that do not need to
        # be monitored and do not need to be shown in the workspace viewer
        #
        # One can bypass this rule as there is no reinforcement implemented.
        #
        # The above rule applies to code run inside the GUI (i.e., NOT executed
        # in the console), where this interception is not implemented.
        # ### END   long comment
        self.workspace = dict() 
        
        self._nonInteractiveVars_ = dict()
        self.console = None
        self.ipkernel = None
        self.shell = None
        self.historyAccessor = None

        self._scipyenEditor = "kate"
        self._overrideSystemEditor = False

        self.external_console = None

        self._maxRecentFiles = 10  # TODO: make this user-configurable
        self._maxRecentDirectories = 10  # TODO: make this user-configurable

        # export the code editor to the pyqtgraph framework
        pg.setConfigOptions(editorCommand=self._scipyenEditor)

        # NOTE: 2021-08-17 12:29:29
        # directory where scipyen is installed; it is aliased in the workspace
        # to the  'scipyen_topdir' symbol
        self._scipyendir_ = os.path.dirname(__module_path__)

        # BEGIN - to revisit
        # cached file name for python source (for loading or running)
        self._temp_python_filename_ = None

        self._copy_varnames_quoted_ = False

        self._copy_varnames_separator_ = " "
        # END - to revisit
        
        # BUG 2025-07-15 22:23:18
        # calling this here (or anywhere below the __init__ call stack) prevents
        # the global appmenu from registering properly with the dbus service
        # (or messes it up so that the global menu doesn't show)
        # QtGui.QGuiApplication.processEvents() 
        self.sig_splashMessage.emit("Initializing the user interface...")

        # NOTE: 2021-08-17 12:38:41 see also NOTE: 2021-08-17 10:05:20 in scipyen.py
        # self._default_GUI_style = self.app.style()
        self._current_GUI_style_name = "Default"
        self._prev_gui_style_name = self._current_GUI_style_name
        
        # NOTE: 2016-04-15 23:58:08
        # place holders for the tree widget item holding the commands in the
        # current session, in the command history tree widget
        self.currentSessionTreeWidgetItem = None

        self.fileSystemModel = QtWidgets.QFileSystemModel(parent=self)
        self.fileSystemModel.setReadOnly(False)
        self.fileSystemModel.setNameFilterDisables(False)

        self.currentVarItem = None
        self.currentVarItemName = None

        # NOTE: 2021-08-17 12:45:10 TODO
        # to be used with _run_loop_process_, which at the moment is not used
        # anywhere - keep available as app-wide threadpool for various sub-apps
        self.threadpool = QtCore.QThreadPool()

        self._winFlagsCache_ = self.windowFlags()
                
        if isinstance(getattr(self, "configurable_traits", None), DataBag):
            self.configurable_traits["RecentScripts"] = self._recentScripts

        self._lockedToolBar:bool = True
        self._guiIconSize_ = self._defaultIconSize_
        self._workspaceIconSize_ = self._defaultIconSize_
        self._fileSystemIconSize_ = self._defaultIconSize_
        self._newNavigatorLook_ = self._defaultNewNavigatorLook_
        self._fileNamesFiltersHides_:bool = False
        self._toolButtonStyle_:int = QtCore.Qt.ToolButtonFollowStyle.value
        
        self._configureUI_()

        self._scriptManager_ = ScriptManager(parent=myparent)
            
        self._scriptManager_.signal_executeScript[str].connect(
            self._slot_runPythonScriptFromManager)
        self._scriptManager_.signal_importScript[str].connect(
            self._slot_importPythonScriptFromManager)
        self._scriptManager_.signal_pasteScript[str].connect(
            self._slot_pastePythonScriptFromManager)
        self._scriptManager_.signal_forgetScripts[object].connect(
            self._slot_forgetScripts_)
        self._scriptManager_.signal_editScript[str].connect(
            self.slot_systemEditScript)
        self._scriptManager_.signal_openScriptFolder[str].connect(
            self.slot_systemOpenParentFolder)
        self._scriptManager_.signal_pythonFileReceived[str, QtCore.QPoint].connect(
            self.slot_handlePythonTextFile)
        self._scriptManager_.signal_pythonFileAdded[str].connect(self._slot_scriptFileAddedInManager)
        self._scriptManager_.signal_scriptManagerClosed.connect(self._slot_scriptManagerClosed)

        # NOTE: 2023-06-04 10:49:56
        # for debugging only; comment out for relese
        # self.shell.events.register("pre_run_cell", self.workspaceModel.preRunCell)


        # NOTE:2022-01-28 23:16:57
        # when collections are modified directly (instead of setting via
        # property setter, see  NOTE:FIXME:2022-01-28 23:11:59) the
        # configurable_traits are NOT populated/notified!
        # Hence I need to force this here
        
        self._defaultTbIconSize = self.toolBar.iconSize()
        self._defaultTbButtonStyle = self.toolBar.toolButtonStyle() # a Qt.ToolButtonStyle

        # NOTE: 2025-06-21 16:49:12
        # variables I think depend on all GUI bits being initialized in setupUi
        self._tbIconSize:QtCore.QSize = self.toolBar.iconSize()
        self._tbButtonStyle:QtCore.Qt.ToolButtonStyle = self.toolBar.toolButtonStyle()

        # -----------------
        # connect widget actions through signal/slot mechanism
        # NOTE: 2017-07-04 16:28:52
        # do not delete: this is the first code where self.cwd is defined & initiated!
        self.cwd = os.getcwd()

        # finally, inject references to self and the workspace into relevant
        # NOTE: 2024-05-29 14:04:11
        # plugin modules already have this injected by slot_loadPlugins
        ws_aware_modules = (membrane, pgui, sigp, imgp, crvf, plots)
        # ws_aware_modules = (pgui, sigp, imgp, crvf, plots)

        for m in ws_aware_modules:
            # NOTE: 2022-12-23 10:47:39
            # some modules provide plugin functionality which will trigger these
            # injections -- see slot_loadPlugins
            if not hasattr(m, "mainWindow"):
                m.__dict__["mainWindow"] = self

            if not hasattr(m, "workspace"):
                m.__dict__["workspace"] = self.workspace

        
        sigBlock = QtCore.QSignalBlocker(self.actionUse_system_default_font)
        self.actionUse_system_default_font.setChecked(self._useSystemDefaultFont)
        self.sig_splashMessage.emit("Initializing Scipyen Console...")
        
        self._init_QtConsole_() # also instantiates self.shell, etc

        self.sig_splashMessage.emit("Initializing User Workspace...")

        # NOTE: 2025-06-24 21:49:54
        # update this NOW, see NOTE: 2025-06-24 21:49:03
        self._nonInteractiveVars_.update([i for i in self.workspace.items()])
        
        # NOTE: 2025-06-24 21:57:40
        # WorkspaceModel needs the shell's user_ns hence it has to be instantiated
        # AFTER _init_QtConsole_()
        self.workspaceModel = WorkspaceModel(self.shell, parent=self,
                                             user_ns_hidden = self.workspace,
                                             mpl_figure_close_callback=self.handle_mpl_figure_close,
                                             mpl_figure_click_callback=self.handle_mpl_figure_click,
                                             mpl_figure_enter_callback=self.handle_mpl_figure_enter)
        
        self.workspaceModel.workingDir.connect(self._slot_workdirChangedInConsole)
        
        self.shell.events.register("pre_execute", self.workspaceModel.preExecute)
        # self.shell.events.register("post_execute", self.workspaceModel.post_execute)
        self.shell.events.register("post_run_cell", self.workspaceModel.postRunCell)
        
        self.workspaceModel.user_ns_hidden.update(self._nonInteractiveVars_)
        # self.translator = QtCore.QTranslator(self)
        # holds references to workspace objects that should NOT be visibile in
        # the workspace viewer - this includes viewer classes
        self.user_ns_hidden = self.workspaceModel.user_ns_hidden
        
        self.workspaceModel.enableInternalVariableObserver(True)
        
        # NOTE: 2025-06-24 22:05:04
        # used to be called from self._configureUI_, but not anymore
        self.workspaceView.setModel(self.workspaceModel)
        self.workspaceView.selectionModel().selectionChanged[QtCore.QItemSelection, QtCore.QItemSelection].connect(self.slot_selectionChanged)
        self.workspaceModel.itemChanged.connect(self.slot_variableItemNameChanged)
        self.workspaceModel.modelContentsChanged.connect(self.slot_updateWorkspaceView)
        
        self._shell_automagics:bool = True
        
        self.sig_splashMessage.emit("Loading Saved Settings...")

        # With all UI elements and their signal-slot connections in place we can
        # now apply stored settings, including the 'state' of the ScipyenWindow
        # object (which is an instance of QMainWindow)
        #
        self.loadSettings()
        
        self.sig_splashMessage.emit("Loading User Plugins...")

        # NOTE: 2024-05-29 13:04:00
        # Asynchronously launch the plugin loading mechanism
        self.startPluginLoad.emit()

        self._updateConsolesEditor()

        # self.helpWidget = None
        self.pythonHelpWindow = None

        self.console.show()
        # NOTE: 2021-10-18 11:28:25
        # The following must be called when console has become visible!
        self.console.consoleWidget.set_pygment(self.console.consoleWidget._console_pygment)
        
        if self._script_manager_autolaunch:
            self._showScriptsManagerWindow()
            
        self.sig_splashMessage.emit("Done!")

        self.show()
        
        # ### BEGIN global menu stuff -- see also self._deregister_menuBar_, self._restore_menuBar_, self.getAppMenu and self._slot_visibility_changed
        self._app_menu_ = None
        self._wm_id_ = int(self.winId())
        self._globalMenuServiceName_ = None
        self._dbusAppMenuInterface_ = None
        self._dbusInterface_ = None
        self._dbusSessionBus_ = None
        self._dbusUniqueName_ = None
        if not QtWidgets.QApplication.instance().testAttribute(QtCore.Qt.AA_DontUseNativeMenuBar):
            if desktoputils.is_kde() or desktoputils.is_gnome() and __has_qtdbus__:
                self._dbusSessionBus_ = QtDBus.QDBusConnection.sessionBus() # also a QDBusConnection
                self._dbusUniqueName_ = self._dbusSessionBus_.baseService() # a str, empty if NOT connected to dbus dameon
                appMenuServiceNames = list(name for name in self._dbusSessionBus_.interface().registeredServiceNames().value() if "AppMenu" in name)
                if len(appMenuServiceNames):
                    self._globalMenuServiceName_ = appMenuServiceNames[0]
                    self._dbusAppMenuInterface_ = QtDBus.QDBusInterface(self._globalMenuServiceName_, "/" + self._globalMenuServiceName_.replace(".", "/"),
                                                  self._globalMenuServiceName_, QtDBus.QDBusConnection.sessionBus(), self)
                    self._dbusAppMenuInterface_.setTimeout(100)
                # TODO 2025-06-30 23:47:57 finalize me !!!
#                 if isinstance(self._dbusUniqueName_, str) and len(self._dbusUniqueName_.strip()):
#                     
#                     self._dbusInterface_ = QtDBus.QDBusInterface()
                    
                
                    
                    # NOTE: 2025-06-30 22:56:02
                    # self._dbusSessionBus_.interface() -> QDBusConnectionInterface
                    # self._dbusSessionBus_.name() -> str: 'qt_default_session_bus' 
                    # self._dbusAppMenuInterface_.interface() -> 'com.canonical.AppMenu.Registrar'
                    # self._dbusAppMenuInterface_.connection() -> QDBusconnection
                    # self._dbusAppMenuInterface_.connection().baseService() -> str: "unique connection name"
                    #    = the name of the session bus where the MenuBar is registered
                    #   in Qt D-bus viewer this looks like:
                    #   :1.134 and in its methods tree there is a MenuBar/2/ 4/ 5/ etc...
                    #   --> Same as self._dbusSessionBus_.baseService()
                    # self._dbusAppMenuInterface_.children()[0] -> QDBusServiceWatcher:
                    #   serviceWatcher.watchedServices() -> ['com.canonical.AppMenu.Registrar'] -- A-HA...
                    # dbusinterface.baseService() -> str: 'qt_default_session_bus' (ALWAYS this?)
                    # dbusinterface.interface() is the QtDBus.QDBusConnection.sessionBus().interface()
#                     self._dbusAppMenuInterface_.setTimeout(1000)
#                     if __has_PyQt6__ or __has_PySide6__:
#                         v = int(self.winId())
#                     else:
#                         v = QtCore.QVariant(int(self.winId()))
#                         
#                         if not v.convert(QtCore.QVariant.UInt): # NOTE: 2023-01-08 23:10:14 MUST convert to UInt
#                             return
#                         
#                     result = self._dbusAppMenuInterface_.call("RegisterWindow", v, QtDBus.QDBusObjectPath(f"/{self.applicationName}/{self.__class__.__name__}/MenuBar")).arguments()
#                     print(f"{self.__class__.__name__}._init__ DBus register window: result -> {result}")
                            
            # BUG 2025-07-01 23:17:12 FIXME
            # this returns None whe using a QSPlashScreen!
            # self._app_menu_ = self.getAppMenu()
            
        self.windowHandle().visibilityChanged.connect(self._slot_visibility_changed)
        # ### END   global menu stuff -- see also self._deregister_menuBar_, self._restore_menuBar_, self.getAppMenu and self._slot_visibility_changed

        # NOTE: 2025-06-30 08:36:52
        # uncomment this to show the menubar in the main window
        # self.menuBar().setNativeMenuBar(False)

    # ### BEGIN Properties and slots connected to properties
    
    @property
    def shellAutomagic(self) -> bool:
        return self._shell_automagics
    
    @markConfigurable("ShellAutomagic")
    @shellAutomagic.setter
    def shellAutomagic(self, val:bool):
        self._shell_automagics = val == True
        if self.console:
            self.console.shellAutomagic = self._shell_automagics
            
        signalBlock = QtCore.QSignalBlocker(self.actionUseShellAutomagic)
        self.actionUseShellAutomagic.setChecked(self.console.shellAutomagic)
        
    @Slot(bool)
    def _slot_UseShellAutomagic(self, val:bool):
        self.shellAutomagic = val == True
        
    @property
    def hideFilesWhenFiltering(self) -> bool:
        return self._fileNamesFiltersHides_
    
    @markConfigurable("HideFilteredFileNames", "Qt")
    @hideFilesWhenFiltering.setter
    def hideFilesWhenFiltering(self, val:bool):
        self._fileNamesFiltersHides_ = val==True
        self.fileSystemModel.setNameFilterDisables(not self._fileNamesFiltersHides_)
        sigBlock = [QtCore.QSignalBlocker(w) for w in (self.actionHide_Filtered_out_File_Names, self.hideFilteredOutnamesToolButton)]
        self.actionHide_Filtered_out_File_Names.setChecked(self._fileNamesFiltersHides_)
        self.hideFilteredOutnamesToolButton.setChecked(self._fileNamesFiltersHides_)
        
    @Slot(bool)
    def _slot_hideFilteredFileNames(self, val:bool):
        self.hideFilesWhenFiltering = val==True
    
    @property
    def useNewNavigatorLook(self) -> bool:
        return self._newNavigatorLook_
    
    @markConfigurable("UseNewNavigatorLook", "Qt")
    @useNewNavigatorLook.setter
    def useNewNavigatorLook(self, val:bool):
        self._newNavigatorLook_ = val == True
        self.navigator.newLook = self._newNavigatorLook_
        signalBlocker = QtCore.QSignalBlocker(self.actionUse_New_Navigator_Look)
        self.actionUse_New_Navigator_Look.setChecked(self.navigator.newLook)
        
    @Slot(bool)
    def _slot_newNavigatorLook(self, val:bool) -> None:
        self.useNewNavigatorLook = val == True
    
    @property
    def useNativeMenuBar(self) -> bool:
        return self._useNativeMenuBar
    
    @markConfigurable("UseNativeMenuBar", "Qt")
    @useNativeMenuBar.setter
    def useNativeMenuBar(self, val:bool) -> None:
        self._useNativeMenuBar = val == True
        signalBlocker = QtCore.QSignalBlocker(self.actionUse_Native_Menu_Bar)
        self.actionUse_Native_Menu_Bar.setChecked(self._useNativeMenuBar == True)
        self.menuBar().setNativeMenuBar(self._useNativeMenuBar)
        
    @Slot(bool)
    def _slot_useNativeMenuBar(self, val:bool) -> None:
        self.useNativeMenuBar = val == True
    
    @property
    def desktopScreen(self) -> QtGui.QScreen:
        myGeom = self.geometry() # a QtCore.QRect
        screens = QtGui.QGuiApplication.screens()
        primaryScreen = QtGui.QGuiApplication.primaryScreen()
        # NOTE: 2024-03-02 23:05:29
        # verify this by changing your desktop screens layout
        if len(screens) > 1:
            screenGeoms = [s.geometry() for s in screens]
            xscreen = [myGeom.x() >= s.x() + s.width() for s in screenGeoms]
            yscreen = [myGeom.y() >= s.y() + s.height() for s in screenGeoms]
            screenNdx = [k for k in range(len(screens)) if all([not xscreen[k] , not yscreen[k]])][0]
            return screens[screenNdx]
        
        return primaryScreen

    @property
    def userHome(self) -> str:
        return self._user_home_
    
    @property
    def userHomeEnvironmentVariable(self) -> str:
        return self._userenv_varname_
    
    @property
    def scipyenSettings(self):
        return self._scipyen_settings_

    @scipyenSettings.setter
    def scipyenSettings(self, value):
        self._scipyen_settings_ = value
        # self.workspace["scipyen_settings"] = self._scipyen_settings_
        self.workspaceModel.bindObjectInNamespace("scipyen_settings", self._scipyen_settings_,
                                    hidden=True)
        
    @property
    def applicationName(self)->str:
        return self.app.applicationName()
    
    @property
    def pluginNames(self) -> tuple:
        r"""Tuple of names of currently loaded plugins.
        These include all Scipyen plugins (either in the Scipyen code tree or
        in the user-defined plugins directory) regardless if whether they define 
        a UI menu or not.
        See also the following attributes, properties or methods:
        • plugins
        • pluginModules
        • UIPlugins
        • UIPluginMenus
        • UIPluginNames
        • getMenusForUIPlugin
        """
        return tuple(scipyen_plugin_loader.loaded_plugins.keys())
    
    @property
    def pluginModules(self) -> tuple:
        r"""Tuple of currently loaded plugin modules.
        These include all Scipyen plugins (either in the Scipyen code tree or
        in the user-defined plugins directory) regardless if whether they define 
        a UI menu or not.
        See also the following attributes, properties or methods:
        • plugins
        • pluginNames
        • UIPlugins
        • UIPluginMenus
        • UIPluginNames
        • getMenusForUIPlugin
        """
        return tuple(scipyen_plugin_loader.loaded_plugins.values())
    
    @property
    def plugins(self) -> dict:
        r"""Mapping of module name ↦ plugin module for currently loaded plugins.
        These include all Scipyen plugins (either in the Scipyen code tree or
        in the user-defined plugins directory) regardless if whether they define 
        a UI menu or not.
        See also the following attributes, properties or methods:
        • pluginModules
        • pluginNames
        • UIPlugins
        • UIPluginMenus
        • UIPluginNames
        • getMenusForUIPlugin
        """
        return scipyen_plugin_loader.loaded_plugins
    
    @property
    def UIPlugins(self) -> dict:
        r"""Loaded Scipyen "UI" plugins.
        These are the Scipyen plugins that define a UI menu (i.e. define the 
        function `init_scipyen_plugin` to generate a UI menu hieracrhy), regardless 
        of where their files are located (either in the Scipyen code tree or in
        the user-defined plugins directory).
        For a collection of ALL plugin modules, see `plugins` property.
        See also the following attributes, properties or methods:
        • plugins
        • pluginModules
        • pluginNames
        • UIPluginMenus
        • UIPluginNames
        • getMenusForUIPlugin
        """
        return self._ui_plugins_
    
    @property
    def UIPluginNames(self) -> tuple:
        r"""Names of loaded Scipyen "UI" plugins
        See also the following attributes, properties or methods:
        • plugins
        • pluginModules
        • pluginNames
        • UIPlugins
        • UIPluginMenus
        • UIPluginNames
        • getMenusForUIPlugin
        """
        return tuple(x.__name__ for x in self._ui_plugins_.keys())
    
    @property
    def UIPluginMenus(self) -> dict:
        r"""Mapping of UI plugins name ↦ mapping of [menu path ↦ plugin function]
        See also the following attributes, properties or methods:
        • plugins
        • pluginModules
        • pluginNames
        • UIPlugins
        • UIPluginNames
        • getMenusForUIPlugin
        """
        return dict((k.__name__, dict((self._crawl_plugin_UI_menu(act), l.__name__) for l,act in v.items())) for k,v in  self._ui_plugins_.items())
        
#     @property
#     def externalHDF5Viewer(self) -> str:
#         # NOTE: 2025-03-24 21:35:03 NOT USED
#         return self._external_HDF5_viewer
#         
#     @markConfigurable("ExternalHDF5Viewer", trait_notifier=True)
#     @externalHDF5Viewer.setter
#     def externalHDF5Viewer(self, value:typing.Optional[str] = None):
#         # NOTE: 2025-03-24 21:35:03 NOT USED
#         if isinstance(val, str) and len(val.strip()):
#             self._external_HDF5_viewer = val
#         else:
#             self._external_HDF5_viewer = str()
        
    @property
    def userPluginsDirectory(self) -> str:
        return self._user_plugins_dir
    
    @markConfigurable("UserPluginsDirectory", trait_notifier=True)
    @userPluginsDirectory.setter
    def userPluginsDirectory(self, val:typing.Union[str, pathlib.Path]):
        if isinstance(val, pathlib.Path):
            val = str(a)
            
        elif not isinstance(val, str) or len(val.strip()) == 0:
            val = self._default_scipyen_user_plugins_dir
            
        self._user_plugins_dir = val
        
    @property
    def showFullNavigatorPath(self)-> bool:
        return self.navigator.showFullPath()
    
    @markConfigurable("ShowFullNavigatorPath", "Qt")
    @showFullNavigatorPath.setter
    def showFullNavigatorPath(self, value:bool):
        self.navigator.setShowFullPath(value is True)
        
    @property
    def navigatorEditable(self)->bool:
        return self.navigator.isUrlEditable()
    
    @markConfigurable("NavigatorIsEditable", "Qt")
    @navigatorEditable.setter
    def navigatorEditable(self, value:bool):
        self.navigator.setUrlEditable(value is True)

    @property
    def toolBarLocked(self) -> bool:
        return not self.toolBar.isMovable()
    
    @markConfigurable("ToolBarLocked", "Qt")
    @toolBarLocked.setter
    def toolBarLocked(self, val:bool):
        self._lockedToolBar = val is True
        signalBlocker = QtCore.QSignalBlocker(self.lockToolBarAction)
        self.lockToolBarAction.setChecked(self._lockedToolBar)
        self.toolBar.setMovable(not self._lockedToolBar)
        
    @Slot(bool)
    def _slot_changeToolBarLockedState(self, val:bool):
        # print(f"{self.__class__.__name__}._slot_changeToolBarLockedState(val={val})")
        self.toolBarLocked = val is True
        
    @property
    def toolBarIconSize(self) -> QtCore.QSize:
        return self.toolBar.iconSize() # QMainWindow API
    
    @markConfigurable("ToolbarIconSize", "Qt")
    @toolBarIconSize.setter
    def toolBarIconSize(self, val:QtCore.QSize):
        # print(f"{self.__class__.__name__}.toolBarIconSize.setter(val = {val})")
        self._tbIconSize = val
        self.toolBar.setIconSize(val)
        signalBlocker = QtCore.QSignalBlocker(self.toolBarIconSizeActionGroup)
        if self._tbIconSize == self._defaultTbIconSize:
            self.defaultToolBarIconSizeAction.setChecked(True)
        elif self._tbIconSize == QtCore.QSize(16,16):
            self.smallToolBarIconSizeAction.setChecked(True)
        elif self._tbIconSize == QtCore.QSize(22,22):
            self.mediumToolBarIconSizeAction.setChecked(True)
        elif self._tbIconSize == QtCore.QSize(32,32):
            self.largeToolBarIconSizeAction.setChecked(True)
        elif self._tbIconSize == QtCore.QSize(48, 48):
            self.hugeToolBarIconSizeAction.setChecked(True)
        else:
            for action in [self.defaultToolBarIconSizeAction, self.smallToolBarIconSizeAction,
                       self.mediumToolBarIconSizeAction, self.largeToolBarIconSizeAction,
                       self.hugeToolBarIconSizeAction]:
                action.setChecked(False)
        ww = list(filter(lambda w: isinstance(w, QtWidgets.QMainWindow), self.app.allWidgets()))
        for w in ww:
            toolbars = w.findChildren(QtWidgets.QToolBar)
            for b in toolbars:
                b.setIconSize(val)
            
    @Slot(QAction)
    def _slot_setToolBarIconSize(self, val:QAction):
        # signalBlocker = QtCore.QSignalBlocker(self.toolBarIconSizeActionGroup)
        if val == self.defaultToolBarIconSizeAction:
            self.toolBarIconSize = self._defaultTbIconSize
        elif val == self.smallToolBarIconSizeAction:
            self.toolBarIconSize = QtCore.QSize(16,16)
        elif val == self.mediumToolBarIconSizeAction:
            self.toolBarIconSize = QtCore.QSize(22,22)
        elif val == self.largeToolBarIconSizeAction:
            self.toolBarIconSize = QtCore.QSize(32,32)
        elif val == self.hugeToolBarIconSizeAction:
            self.toolBarIconSize = QtCore.QSize(48,48)
            
    @property
    def toolBarButtonStyle(self) -> QtCore.Qt.ToolButtonStyle:
        return self.toolBar.toolButtonStyle()
    
    @markConfigurable("ToolButtonStyle", "Qt")
    @toolBarButtonStyle.setter
    def toolBarButtonStyle(self, val:QtCore.Qt.ToolButtonStyle):
        self._tbButtonStyle = val
        self.toolBar.setToolButtonStyle(val)
        signalBlocker = QtCore.QSignalBlocker(self.toolBarIconSizeActionGroup)
        if self._tbButtonStyle == self._defaultTbButtonStyle:
            self.defaultToolBarToolButtonStyleAction.setChecked(True)
        elif self._tbButtonStyle == QtCore.Qt.ToolButtonIconOnly:
            self.iconsOnlyToolBarToolButtonStyleAction.setChecked(True)
        elif self._tbButtonStyle == QtCore.Qt.ToolButtonTextOnly:
            self.textOnlyToolBarToolButtonStyleAction.setChecked(True)
        elif self._tbButtonStyle == QtCore.Qt.ToolButtonTextBesideIcon:
            self.textUnderIconsToolBarToolButtonStyleAction.setChecked(True)
        
    @Slot(QAction)
    def _slot_setToolBarToolButtonStyle(self, val:QAction):
        if val == self.defaultToolBarToolButtonStyleAction:
            self.toolBarButtonStyle = self._defaultTbButtonStyle
        elif val == self.iconsOnlyToolBarToolButtonStyleAction:
            self.toolBarButtonStyle = QtCore.Qt.ToolButtonIconOnly
        elif val == self.textOnlyToolBarToolButtonStyleAction:
            self.toolBarButtonStyle = QtCore.Qt.ToolButtonTextOnly
        elif val == self.textAlongsideIconsToolBarToolButtonStyleAction:
            self.toolBarButtonStyle = QtCore.Qt.ToolButtonTextBesideIcon
        elif val == self.textUnderIconsToolBarToolButtonStyleAction:
            self.toolBarButtonStyle = QtCore.Qt.ToolButtonTextUnderIcon
    
    @Slot()
    def _slot_workSpaceIconSize(self):
        icon_sizes = {"Small":16, "Medium":22, "Large":32, "Huge":48}
        texts = list(map(lambda i: f"{i[0]} ({i[1]}×{i[1]})", icon_sizes.items()))
        dlg = qd.QuickDialog(self, "Set Icon Size", True, False)
        cb = qd.QuickDialogComboBox(dlg, "Icon Size:")
        dlg.addWidget(cb)
        cb.setItems(texts)
        currentIS = self.fileSystemTreeView.iconSize().width()
        
        if currentIS not in icon_sizes.values():
            if currentIS <= 16:
                currentIS = 16
            elif currentIS <= 22:
                currentIS = 22
            elif currentIS <= 32: 
                currentIS = 32
            else:
                currentIS = 48
        selected = list(icon_sizes.values()).index(currentIS)
            
        cb.setCurrentIndex(selected)
        
        # dlg.resize(-1,-1)
        dlg.adjustSize()
        
        if dlg.exec() > 0:
            # newVal = icon_sizes[cb.value()]
            newVal = list(icon_sizes.values())[cb.value()]
            
        else:
            newVal = currentIS
            
        self.workSpaceIconSize = newVal
        
    @property
    def workSpaceIconSize(self) -> int:
        self._workspaceIconSize_ = self.workspaceView.iconSize().width()
        return self._workspaceIconSize_
    
    def _set_workspace_icon_Size(self, val:int):
        iconSize = QtCore.QSize(val, val)
        self.workspaceView.setIconSize(iconSize)
        
    @markConfigurable("WorkSpaceViewIconSize", "Qt")
    @workSpaceIconSize.setter
    def workSpaceIconSize(self, val:int):
        val = int(val)
        if val not in [16,22,32,48]:
            if val <= 16:
                val = 16
            elif val <= 22:
                val = 22
            elif val <= 32: 
                val = 32
            else:
                val = 48
        self._workspaceIconSize_ = val
        self._set_workspace_icon_Size(val)

    @Slot()
    def _slot_fileSystemIconSize(self):
        icon_sizes = {"Small":16, "Medium":22, "Large":32, "Huge":48}
        texts = list(map(lambda i: f"{i[0]} ({i[1]}×{i[1]})", icon_sizes.items()))
        dlg = qd.QuickDialog(self, "Set Icon Size", True, False)
        cb = qd.QuickDialogComboBox(dlg, "Icon Size:")
        dlg.addWidget(cb)
        cb.setItems(texts)
        currentIS = self.fileSystemTreeView.iconSize().width()
        
        if currentIS not in icon_sizes.values():
            if currentIS <= 16:
                currentIS = 16
            elif currentIS <= 22:
                currentIS = 22
            elif currentIS <= 32: 
                currentIS = 32
            else:
                currentIS = 48
        selected = list(icon_sizes.values()).index(currentIS)
            
        cb.setCurrentIndex(selected)
        
        # dlg.resize(-1,-1)
        dlg.adjustSize()
        
        if dlg.exec() > 0:
            # newVal = icon_sizes[cb.value()]
            newVal = list(icon_sizes.values())[cb.value()]
            
        else:
            newVal = currentIS
            
        self.fileSystemIconSize = newVal
        
    @property
    def fileSystemIconSize(self) -> int:
        self._fileSystemIconSize_ = self.fileSystemTreeView.iconSize().width()
        return self._fileSystemIconSize_
    
    def _set_filesystem_icon_size(self, val:int):
        iconSize = QtCore.QSize(val, val)
        self.fileSystemTreeView.setIconSize(iconSize)
        
    @markConfigurable("FileSystemViewerIconSize", "Qt")
    @fileSystemIconSize.setter
    def fileSystemIconSize(self, val:int):
        val = int(val)
        if val not in [16,22,32,48]:
            if val <= 16:
                val = 16
            elif val <= 22:
                val = 22
            elif val <= 32: 
                val = 32
            else:
                val = 48
        self._fileSystemIconSize_ = val
        self._set_filesystem_icon_size(val)
    
    @Slot()
    def _slot_configureIconSize(self):
        # icon_sizes = [16, 22, 32, 48]
        # texts = [f"{k}x{k}" for k in icon_sizes]
        icon_sizes = {"Small":16, "Medium":22, "Large":32, "Huge":48}
        texts = list(map(lambda i: f"{i[0]} ({i[1]}×{i[1]})", icon_sizes.items()))
        dlg = qd.QuickDialog(self, "Set Icon Size", True, False)
        cb = qd.QuickDialogComboBox(dlg, "Icon Size:")
        dlg.addWidget(cb)
        cb.setItems(texts)
        currentIS = self.iconSize().width()
        
        if currentIS not in icon_sizes.values():
            if currentIS <= 16:
                currentIS = 16
            elif currentIS <= 22:
                currentIS = 22
            elif currentIS <= 32: 
                currentIS = 32
            else:
                currentIS = 48
        # print(f"currentIS = {currentIS}")
        # print(f"ndx = {icon_sizes.index(currentIS)}")
        selected = list(icon_sizes.values()).index(currentIS)
            
        cb.setCurrentIndex(selected)
        
        # dlg.resize(-1,-1)
        dlg.adjustSize()
        
        if dlg.exec() > 0:
            # newVal = icon_sizes[cb.value()]
            newVal = list(icon_sizes.values())[cb.value()]
            
        else:
            newVal = currentIS
            
        self.guiIconSize = newVal
        
    @property
    def toolButtonStyle(self) -> int:
        return self._toolButtonStyle_
    
    @markConfigurable("ToolButtonStyle", "Qt")
    @toolButtonStyle.setter
    def toolButtonStyle(self, val:int):
        self._toolButtonStyle_ = val
        self._set_toolButtonStyle(self._toolButtonStyle_)
        
    def _set_toolButtonStyle(self, val:QtCore.Qt.ToolButtonStyle|int|str):
        r"""Sets a tool button style globally, NOT per toolbar"""
        # print(f"{self.__class__.__name__}._set_toolButtonStyle({val}:{type(val)})")
        if isinstance(val, QtCore.Qt.ToolButtonStyle):
            val = val.value
        if isinstance(val, str):
            stylesDict = dict((i.name, i) for i in QtCore.Qt.ToolButtonStyle)
            if val not in stylesDict:
                scipywarn(f"invalid argument: {val} ({type(val)})")
                return
            val = stylesDict[val]
        elif isinstance(val, int):
            stylesDict = dict((i.value, i) for i in QtCore.Qt.ToolButtonStyle)
            if val not in stylesDict:
                scipywarn(f"invalid argument: {val} ({type(val)})")
                return
            val = stylesDict[val]
        elif not isinstance(val, QtCore.Qt.ToolButtonStyle):
            scipywarn(f"invalid argument: {val} ({type(val)})")
            return
        
        ww = list(filter(lambda w: isinstance(w, (QtWidgets.QMainWindow, QtWidgets.QDockWidget)), self.app.allWidgets()))
        for w in ww:
            if isinstance(w, QtWidgets.QMainWindow):
                w.setToolButtonStyle(val)
                
        self.toolBarButtonStyle = val
        
    @Slot()
    def _slot_configureToolButtonStyle(self):
        dlg = qd.QuickDialog(self, "Set tool button style across Scipyen")
        styleChoice = qd.Choice(dlg, "Select style", vertical=True)
        dlg.adjustSize()
        styleDict = dict()
        for item in QtCore.Qt.ToolButtonStyle:
            styleChoice.addButton(item.name, item.value)
            styleDict[item.value] = item.name
        styleChoice.selectButton(self._toolButtonStyle_)
        if dlg.exec():
            self._toolButtonStyle_ = styleChoice.selection()
            self._set_toolButtonStyle(self._toolButtonStyle_)
        
        
        
    @property
    def guiIconSize(self) -> int:
        return self._guiIconSize_
    
    def _set_icon_Size(self, val:int):
        iconSize = QtCore.QSize(val, val)
        ww = list(filter(lambda w: isinstance(w, (QtWidgets.QMainWindow, QtWidgets.QDockWidget)), self.app.allWidgets()))
        for w in ww:
            if isinstance(w, QtWidgets.QMainWindow):
                w.setIconSize(iconSize)
            if __has_PySide6__:
                btns = w.findChildren(QtWidgets.QToolButton) + w.findChildren(QtWidgets.QPushButton)
            else:
                btns = w.findChildren((QtWidgets.QToolButton, QtWidgets.QPushButton))
            for b in btns:
                b.setIconSize(iconSize)
            
    @markConfigurable("GUIIconsize", "Qt")
    @guiIconSize.setter
    def guiIconSize(self, val:int):
        # print(f"{self.__class__.__name__}.guiIconSize = {val}")
        val = int(val)
        if val not in [16,22,32,48]:
            if val <= 16:
                val = 16
            elif val <= 22:
                val = 22
            elif val <= 32: 
                val = 32
            else:
                val = 48
        self._guiIconSize_ = val
        
        self._set_icon_Size(val)
        
    @property
    def scriptManager(self) -> ScriptManager | None:
        return self._scriptManager_
    
    @property
    def scriptsManager(self) -> ScriptManager | None:
        return self.scriptManager

    @property
    def consoleDocked(self):
        return self._console_docked_

    @markConfigurable("ConsoleDocked", "Qt")
    @consoleDocked.setter
    def consoleDocked(self, value):
        self._console_docked_ = value is True

    @property
    def autoRemoveViewers(self):
        return self._auto_remove_viewers_

    @markConfigurable("AutoRemoveViewers", "Qt", default=False, value_type=bool)
    @autoRemoveViewers.setter
    def autoRemoveViewers(self, value):
        # print(f"autoRemoveViewers.setter: value = {value}")
        if isinstance(value, str):
            value = value.lower() == "true"

        self._auto_remove_viewers_ = value == True

        sigBlock = QtCore.QSignalBlocker(self.actionAuto_delete_viewer)
        self.actionAuto_delete_viewer.setChecked(self._auto_remove_viewers_)

    @property
    def maxRecentFiles(self):
        return self._maxRecentFiles

    @markConfigurable("MaxRecentFiles", "Qt")
    @maxRecentFiles.setter
    def maxRecentFiles(self, val: int):
        if isinstance(val, int) and val >= 0:
            self._maxRecentFiles = val

    @property
    def shellCacheSize(self) -> int:
        return self.shell.cache_size

    @markConfigurable("ShellCacheSize")
    @shellCacheSize.setter
    def shellCacheSize(self, val:int):
        if val < 20:
            val = 0

        if val < 0:
            val = self.defaultShellCacheSize

        self.shell.cache_size = val

    @property
    def guiStyle(self):
        return self._current_GUI_style_name

    @markConfigurable("WidgetStyle", "qt", default="Default")
    @guiStyle.setter
    def guiStyle(self, val: str):
        if not isinstance(val, str) or val not in self._available_Qt_style_names_:
            return
        
        self._do_apply_style(val)

        self._current_GUI_style_name = val
        
        # NOTE: 2024-09-26 12:58:23 deal with the icons
        # on Linux the recommended way is to install the light & dark versions of 
        # a freedesktop-compliant icon theme (I prefer breeze, but that's a matter
        # of taste); this can be done in one of two ways:
        # a) install system-wide -- check the documentation of your linux distribution
        #
        # The icon themes should end up in /usr/share/icons
        # the theme itself is a directory containing a Index.theme file and a 
        # prescribed set of folders containing appropriately named subfolders 
        # and image files, see documentation on freedesktop.org).
        #   
        #
        # Using 'breeze' and example:
        # In debian-based distros this usually entails:
        # sudo apt install breeze
        # sudo apt install breeze-dark
        # (which will also bring about the corresponding Qt style libraries)
        #
        # Now you may want to ensure they match the Qt version used by Scipyen (PyQt5)
        #
        # b) install for youself (as an end-user) - using your own
        # desktop customization software provded by the platform, or manually 
        # (see below)
        #
        # Similar to above (but not identical) the icon theme(s) should end up in
        # $HOME/.local/share/icons
        #
        # CAUTION: The icon files MUST follow the freedesktop.org icon theme
        # specification! Downloading any light/dark version of icon files from
        # the web just won't do!
        #
        # Good examples are found at https://www.opendesktop.org/browse?cat=132
        #
        # "Full" icon themes (i.e. where both light and dark versions are avaliable):
        #   Breeze, KDE-Story, Vortex, Chameleon, Round-Chameleon, Wings, Uos,
        # Ars, Relax, Gradient, Flight, Infinity
        #
        # Download then extract the archive in $HOME/.local/share/icons
        #
        # NOTE: 2024-09-26 13:11:11
        # this is NOT needed if running in an environment (virtualenv or conda) 
        # where the PyQt5 stack was built locally, during the creation of the
        # environment, because the appropriate "hooks" to the local platform
        # were there
        # 
        # TODO: 2024-09-26 13:12:17 FIXME: how to make the distinction between
        # the case where PyQt5 was pulled from pypi or conda channel, vs having
        # been built locally?
        
        # QtCore.QCoreApplication.instance().property("_qdarktheme_use_setup_style") is True:


        # themePaths = QtGui.QIcon.themeSearchPaths()
        # WARNING: 2025-03-04 10:42:14
        # does NOT report correctly when using qdarktheme!
        windowColor = QtWidgets.QApplication.palette().color(QtGui.QPalette.Window)
        _,_,v,_ = windowColor.getHsv()
        themeName="breeze" if v > 128 else "breeze-dark"
        QtGui.QIcon.setThemeName(themeName)
        # if v > 128:
        #     QtGui.QIcon.setThemeName("breeze")
        # else:
        #     QtGui.QIcon.setThemeName("breeze-dark")


        # if sys.platform.startswith("win32"):
        #     if hasQDarkTheme:
        #         QtGui.QIcon.setThemeName("breeze-dark")

    @property
    def scriptManagerAutoLaunch(self):
        self._script_manager_autolaunch = self._scriptManager_.isVisible() and not self._scriptManager_.isMinimized()
        return self._script_manager_autolaunch

    @markConfigurable("ScriptManagerAutoLaunch", "qt")
    @scriptManagerAutoLaunch.setter
    def scriptManagerAutoLaunch(self, val: typing.Union[bool, str]):
        if isinstance(val, str):
            val = True if val.lower() == "true" else False

        self._script_manager_autolaunch = True
        sigblock = QtCore.QSignalBlocker(self.actionAuto_launch_Script_Manager)
        self.actionAuto_launch_Script_Manager.setChecked(val)

        if not val is True:
        #     self._showScriptsManagerWindow()
        # else:
            self._scriptManager_.close()


    @property
    def maxRecentDirectories(self):
        return self._maxRecentDirectories

    @markConfigurable("MaxRecentDirectories", "Qt", default=10)
    @maxRecentDirectories.setter
    def maxRecentDirectories(self, val: int):
        # NOTE: _recentDirectories stores them as most recent first !
        if isinstance(val, int) and val >= 0:
            self._maxRecentDirectories = val
            
        if len(self._recentDirectories) > self._maxRecentDirectories:
            keep = list(self._recentDirectories)[:self._maxRecentDirectories]
            self._recentDirectories.clear()
            self._recentDirectories.extend(keep)
            self._refreshRecentDirectoriesMenu_()
            # self._refreshRecentDirsComboBox_()
            

    @property
    def recentFiles(self):
        return self._recentFiles

    @markConfigurable("RecentFiles", "Qt", default=10)
    @recentFiles.setter
    def recentFiles(self, val: typing.Optional[typing.Union[collections.OrderedDict, tuple, list]] = None):
        if isinstance(val, collections.OrderedDict):
            if not all(isinstance(v, dict) and "loader" in v and "timestamp" in v for v in val.values()):
                return
            items = tuple(filter(lambda v: pathlib.Path(v[0]).exists(), sorted(val.items(), key = lambda x: x[1]["timestamp"], reverse=True)))
            
            self._recentFiles = val.__class__(items)
        # elif isinstance(val, (tuple, list)):
        #     self._recentFiles = collections.OrderedDict(
        #         zip(val, ["vigra"] * len(val)))
        else:
            self._recentFiles = collections.OrderedDict()

        self._slot_refreshRecentFilesMenu_()

    @property
    def recentDirectories(self):
        return self._recentDirectories

    @markConfigurable("RecentDirectories", "Qt")
    @recentDirectories.setter
    def recentDirectories(self, val: typing.Optional[typing.Union[collections.deque, list, tuple]] = None):
        if isinstance(val, (collections.deque, list, tuple)):
            self._recentDirectories = collections.deque(val)
        else:
            self._recentDirectories = collections.deque()

        if len(self._recentDirectories) == 0:
            self._recentDirectories.appendleft(os.getcwd())

        path = pathlib.Path(self._recentDirectories[0])
        if not path.is_dir():
            path = pathlib.Path(self._user_home_)
        url = QtCore.QUrl(path.as_uri())
        self.navigator.setLocationUrl(url)
        self.navigator.urlChanged.emit(url)
        # if isinstance(self.navigator, navigator.UrlNavigator):
        #     path = pathlib.Path(self._recentDirectories[0])
        #     if not path.is_dir():
        #         path = pathlib.Path(self._user_home_)
        #     url = QtCore.QUrl(path.as_uri())
        #     self.navigator.setLocationUrl(url)
        #     self.navigator.urlChanged.emit(url)
        # else: # NOTE: 2025-03-31 15:15:12 DEPRECATED branch TODO REMOVE
        #     self.slot_changeDirectory(self._recentDirectories[0])  # alse refreshes gui
            

    @property
    def fileSystemFilterHistory(self):
        return self._fileSystemFilterHistory

    @markConfigurable("RecentFileSystemFilters", "Qt")
    @fileSystemFilterHistory.setter
    def fileSystemFilterHistory(self, val: typing.Optional[typing.Union[collections.deque, list, tuple]] = None):
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
    def lastFileSystemFilter(self):
        return self._lastFileSystemFilter

    @markConfigurable("LastFileSystemFilter", "Qt")
    @lastFileSystemFilter.setter
    def lastFileSystemFilter(self, val: typing.Optional[str] = None):
        if isinstance(val, str):
            self._lastFileSystemFilter = val
        else:
            self._lastFileSystemFilter = str()
            
        if len(self._lastFileSystemFilter) > 0 and len(self._lastFileSystemFilter.strip()) == 0:
            self._lastFileSystemFilter = str()

        self.fileSystemFilter.setCurrentText(self._lastFileSystemFilter)
        
        if len(self._lastFileSystemFilter) > 0:
            self.fileSystemModel.setNameFilters(self._lastFileSystemFilter.split())
        else:
            self.fileSystemModel.setNameFilters(list())

    @property
    def showFileSystemFilter(self):
        return self._showFilesFilter

    @markConfigurable("FilesFilterVisible", "Qt")
    @showFileSystemFilter.setter
    def showFileSystemFilter(self, val: typing.Optional[typing.Union[bool, str, int]] = None):
        if isinstance(val, str) and val.strip().lower() == "true":
            val = True
        elif isinstance(val, int) and val > 0:
            val = True

        self._showFilesFilter = val is True

        self.filesFilterFrame.setVisible(self._showFilesFilter)
        
        # signalBlockers = [QtCore.QSignalBlocker(w) for w in (self.toggleFilesFilterToolBtn, self.hideFilesFilterToolBtn)]
        signalBlocker = QtCore.QSignalBlocker(self.toggleFilesFilterToolBtn)
        
        self.toggleFilesFilterToolBtn.setChecked(self._showFilesFilter)
        
    @property
    def uiFontFamily(self) -> str:
        return self._font.family()
    
    @markConfigurable("UIFontFamily", "Qt")
    @uiFontFamily.setter
    def uiFontFamily(self, val:str):
        self._font.setFamily(val)
        self._updateFont()
    
    @property
    def uiFontPointSize(self) -> int:
        return int(self._font.pointSize())
    
    @markConfigurable("UIFontPointSize", "Qt")
    @uiFontPointSize.setter
    def uiFontPointSize(self, val:int):
        self._font.setPointSize(val)
        self._updateFont()
    
    @property
    def uiFontStyle(self) -> int:
        if __has_PyQt6__ or __has_PySide6__:
            return int(self._font.style().value)
        return int(self._font.style())
    
    @markConfigurable("UIFontStyle", "Qt")
    @uiFontStyle.setter
    def uiFontStyle(self, val:int):
        self._font.setStyle(get_font_style(val))
        self._updateFont()
    
    @property
    def uiFontWeight(self) -> int:
        return int(self._font.weight())
    
    @markConfigurable("UIFontWeight", "Qt")
    @uiFontWeight.setter
    def uiFontWeight(self, val:int):
        self._font.setWeight(get_font_weight(val))
        self._updateFont()
    
    @property
    def workspaceFontFamily(self) -> str:
        return self._workspaceViewerFont.family()
    
    @markConfigurable("WorkspaceFontFamily", "Qt")
    @workspaceFontFamily.setter
    def workspaceFontFamily(self, val:str):
        self._workspaceViewerFont.setFamily(val)
        self._updateWorkspaceItemsFont()
    
    @property
    def workspaceFontPointSize(self) -> int:
        return int(self._workspaceViewerFont.pointSize())
    
    @markConfigurable("WorkspaceFontPointSize", "Qt")
    @workspaceFontPointSize.setter
    def workspaceFontPointSize(self, val:int):
        self._workspaceViewerFont.setPointSize(int(val))
        self._updateWorkspaceItemsFont()
    
    @property
    def workspaceFontStyle(self) -> int:
        if __has_PyQt6__ or __has_PySide6__:
            return int(self._workspaceViewerFont.style().value)
        return int(self._workspaceViewerFont.style())
    
    @markConfigurable("WorkspaceFontStyle", "Qt")
    @workspaceFontStyle.setter
    def workspaceFontStyle(self, val:int):
        self._workspaceViewerFont.setStyle(get_font_style(val))
        self._updateWorkspaceItemsFont()
    
    @property
    def workspaceFontWeight(self) -> int:
        return int(self._workspaceViewerFont.weight())
        
    @markConfigurable("WorkspaceFontWeight", "Qt")
    @workspaceFontWeight.setter
    def workspaceFontWeight(self, val:int):
        self._workspaceViewerFont.setWeight(get_font_weight(val))
        self._updateWorkspaceItemsFont()
    
    @property
    def historyFontFamily(self) -> str:
        return self._commandHistoryFont.family()
    
    @markConfigurable("HistoryFontFamily", "Qt")
    @historyFontFamily.setter
    def historyFontFamily(self, val:str):
        self._commandHistoryFont.setFamily(val)
        self._updateHistoryViewFont()
    
    @property
    def historyFontPointSize(self) -> int:
        return int(self._commandHistoryFont.pointSize())
    
    @markConfigurable("HistoryFontPointSize", "Qt")
    @historyFontPointSize.setter
    def historyFontPointSize(self, val:int):
        self._commandHistoryFont.setPointSize(val)
        self._updateHistoryViewFont()
    
    @property
    def historyFontStyle(self) -> int:
        if __has_PyQt6__ or __has_PySide6__:
            return int(self._commandHistoryFont.style().value)
        return int(self._commandHistoryFont.style())
    
    @markConfigurable("HistoryFontStyle", "Qt")
    @historyFontStyle.setter
    def historyFontStyle(self, val:int):
        self._commandHistoryFont.setStyle(get_font_style(val))
        self._updateHistoryViewFont()
    
    @property
    def historyFontWeight(self) -> int:
        return int(self._commandHistoryFont.weight())
    
    @markConfigurable("HiatoryFontWeight", "Qt")
    @historyFontWeight.setter
    def historyFontWeight(self, val:int):
        self._commandHistoryFont.setWeight(get_font_weight(val))
        self._updateHistoryViewFont()
        
    @property
    def version(self):
        return self.__version__
        
    @property
    def useSystemFont(self) -> bool:
        return self._useSystemDefaultFont
    
    @markConfigurable("UseSystemFont", "Qt")
    @useSystemFont.setter
    def useSystemFont(self, val:bool):
        self._useSystemDefaultFont = val == True
        self._updateWorkspaceItemsFont()
        self._updateHistoryViewFont()
        
    def _updateFont(self):
        font = self._defaultUIFont if self._useSystemDefaultFont else self._font
        self.setFont(font)
        
    def _updateWorkspaceItemsFont(self):
        font = self._defaultUIFont if self._useSystemDefaultFont else self._workspaceViewerFont
        self.workspaceModel.font = font
        
    def _updateHistoryViewFont(self):
        font = self._defaultUIFont if self._useSystemDefaultFont else self._commandHistoryFont
        for item in treeWidgetItems(self.historyTreeWidget):
            for col in range(item.columnCount()):
                item.setFont(col, font)
        
        # NOTE: 2025-04-30 10:04:57
        # moved to gui.guiutils.treeWidgetItems()
        # it = QtWidgets.QTreeWidgetItemIterator(self.historyTreeWidget)
        # while isinstance(it.value(), QtWidgets.QTreeWidgetItem):
        #     item = it.value()
        #     for col in range(item.columnCount()):
        #         item.setFont(col, font)
        #     it += 1 # advance the iterator
        
    @property
    def currentDir(self) -> str | pathlib.Path:
        return self.currentDirectory
    
    @currentDir.setter
    def currentDir(self, value):
        self.currentDirectory = value

    @property
    def currentDirectory(self) -> str | pathlib.Path:
        return self._currentDir_
    
    @currentDirectory.setter
    def currentDirectory(self, value:typing.Union[str, pathlib.Path]):
        self._currentDir_ = value
        
    @property
    def currentLocation(self) -> QtCore.QUrl:
        r"""URL of the current location (as shown in the navigator)
        CAUTION: currently this is the same as the url of the current directory
        but in the future it may point to a non-local file system location
        (as support is being implemented — WORK IN PROGRESS) 
        Therefore it always pays to check the result!
        """
        # normally, this should be the same location as pointed to by
        # self._currentDir_, EXCEPT when the url is a remote one — WORK IN PROGRESS
        return self.navigator.locationUrl()
        
    @property
    def currentUrl(self) -> QtCore.QUrl:
        r"""
        URL of the current (working) file system directory.
        CAUTION: In the (unlikely) situaiton the self._curentDir_ attribute is
        NOT properly set, it will return the URL opf the location of the 
        navigator — WORK IN PROGRESS
        Therefore it always pays to check the result!
        """
        if isinstance(self._currentDir_, str):
            return QtCore.QUrl(pathlib.Path(self._currentDir_).as_uri())
        
        elif isinstance(self._currentDir_, pathlib.Path):
            return QtCore.QUrl(self._currentDir_.as_uri())
        
        else:
            return self.currentLocation
        
        
    @property
    def monitoredDirectories(self):
        return self.dirFileMonitor.directories()

    def isDirectoryMonitored(self, directory:typing.Optional[typing.Union[str, pathlib.Path]]=None):
        # print(f"{self.__class__.__name__}.isDirectoryMonitored {directory}")
        if directory is None:
            # print(f"\t{self.__class__.__name__}.isDirectoryMonitored {pathlib.Path(self.currentDir).absolute()}")
            return str(pathlib.Path(self.currentDir).absolute()) in self.dirFileMonitor.directories()

        if not isinstance(directory, (str, pathlib.Path)):
            return False

        if isinstance(directory, str):
            directory = pathlib.Path(directory)

        if not directory.exists() or not directory.is_dir():
            return False

        return str(directory) in self.dirFileMonitor.directories()
    
#     @property
#     def maximumWatchedFiles(self):
#         return self._nMaxWatchedFiles_
#     
#     @markConfigurable("NMaxWatchedFiles", "Qt")
#     @maximumWatchedFiles.setter
#     def maximumWatchedFiles(self, value:int):
#         if not isinstance(value, int):
#             raise TypeError(f"Expecting and int; instead got {type(value).__name__}")
#         if value < 0:
#             value = 0
#             
#         self._nMaxWatchedFiles_ = value
# 
#     @property
#     def maximumWatchedDirectories(self):
#         return self._nMaxWatchedDirectories_
#     
#     @markConfigurable("NMaxWatchedDirectories", "Qt")
#     @maximumWatchedDirectories.setter
#     def maximumWatchedDirectories(self, value:int):
#         if not isinstance(value, int):
#             raise TypeError(f"Expecting and int; instead got {type(value).__name__}")
#         if value < 0:
#             value = 0
#             
#         self._nMaxWatchedDirectories_= value

    @property
    def variableSearches(self) -> collections.deque:
        return self._recentVariablesList

    @markConfigurable("VariableSearch", "Qt")
    @variableSearches.setter
    def variableSearches(self, val: typing.Optional[typing.Union[collections.deque, list, tuple]] = None):
        if isinstance(val, (collections.deque, list, tuple)):
            self._recentVariablesList = collections.deque(val)
            # self._recentVariablesList = collections.deque(sorted((s for s in val)))

        else:
            self._recentVariablesList = collections.deque()

        if len(self._recentVariablesList):
            self.varNameFilterFinderComboBox.clear()
            for item in self._recentVariablesList:
                self.varNameFilterFinderComboBox.addItem(item)

        self.varNameFilterFinderComboBox.setCurrentText("")

    @property
    def lastVariableSearch(self):
        return self._lastVariableFind

    @markConfigurable("LastVariableSearch", "Qt")
    @lastVariableSearch.setter
    def lastVariableSearch(self, val: typing.Optional[str] = None):
        if isinstance(val, str):
            self._lastVariableFind = val
        else:
            self._lastVariableFind = str()
            
    @property
    def useLastHistoryCommandSearch(self) -> bool:
        return self._useLastHistoryCommandSearch_
    
    @markConfigurable("UseLastHistoryCommandSearch", "Qt")
    @useLastHistoryCommandSearch.setter
    def useLastHistoryCommandSearch(self, val:bool):
        self._useLastHistoryCommandSearch_ = val == True
        signalBlocker = QtCore.QSignalBlocker(self.useLastHistoryCommandSearchAction)
        self.useLastHistoryCommandSearchAction.setChecked(self._useLastHistoryCommandSearch_)
        
    @Slot(bool)
    def _slot_toggleUseLastHistoryCommandSearch(self, val:bool):
        oldVal = self._useLastHistoryCommandSearch_
        self.useLastHistoryCommandSearch = val == True
        
        if oldVal == val:
            return
        
        if oldVal:
            self.commandHistoryFinderComboBox.setCurrentText("")
            original_selection_mode = self.historyTreeWidget.selectionMode()
            self.historyTreeWidget.reset()
            topLevelItem = self.historyTreeWidget.topLevelItem(self.historyTreeWidget.topLevelItemCount()-1)
            self.historyTreeWidget.setSelectionMode(original_selection_mode)
            self.historyTreeWidget.scrollToItem(topLevelItem)
        else:
            self.commandHistoryFinderComboBox.setCurrentIndex(0)
        

    @property
    def commandSearches(self):
        return self._commandHistoryFinderList

    @markConfigurable("CommandSearch", "Qt")
    @commandSearches.setter
    def commandSearches(self, val: typing.Optional[typing.Union[collections.deque, list, tuple]] = None):
        if isinstance(val, (collections.deque, list, tuple)):
            self._commandHistoryFinderList = collections.deque(val)
            # self._commandHistoryFinderList = collections.deque(sorted((s for s in val)))

        else:
            self._commandHistoryFinderList = collections.deque()

        if len(self._commandHistoryFinderList):
            self.commandHistoryFinderComboBox.clear()
            for item in self._commandHistoryFinderList:
                self.commandHistoryFinderComboBox.addItem(item)
                
            if self.useLastHistoryCommandSearch:
                self.commandHistoryFinderComboBox.setCurrentIndex(0)
            else:
                self.commandHistoryFinderComboBox.setCurrentText("")
                original_selection_mode = self.historyTreeWidget.selectionMode()
                self.historyTreeWidget.reset()
                topLevelItem = self.historyTreeWidget.topLevelItem(self.historyTreeWidget.topLevelItemCount()-1)
                self.historyTreeWidget.setSelectionMode(original_selection_mode)
                self.historyTreeWidget.scrollToItem(topLevelItem)


    @property
    def lastCommandSearch(self):
        return self._lastCommandFind

    @property
    def scipyenEditor(self):
        return self._scipyenEditor
    
    @property
    def scipyenDir(self):
        return self._scipyendir_

    @markConfigurable("ScipyenEditor", "Qt")
    @scipyenEditor.setter
    def scipyenEditor(self, val: typing.Optional[str] = None):
        if isinstance(val, str) and len(val.strip()):
            self._scipyenEditor = val
        else:
            self._scipyenEditor = ""
            
        self._updateConsolesEditor()
        # self._updateConsolesEditor(False)

    @property
    def overrideSystemEditor(self):
        return self._overrideSystemEditor

    @markConfigurable("OvererideSystemEditor", "Qt")
    @overrideSystemEditor.setter
    def overrideSystemEditor(self, val: bool = False):
        self._overrideSystemEditor = val is True
        sigBlock = QtCore.QSignalBlocker(
            self.actionUse_system_s_default_code_editor)
        self.actionUse_system_s_default_code_editor.setChecked(
            not self._overrideSystemEditor)
        
        self._updateConsolesEditor()

    @markConfigurable("LastCommandSearch", "Qt")
    @lastCommandSearch.setter
    def lastCommandSearch(self, val: typing.Optional[str] = None):
        if isinstance(val, str):
            self._lastCommandFind = val
        else:
            self._lastCommandFind = str()

    @property
    def recentScripts(self):
        return self._recentScripts

    # NOTE:FIXME/TODO 2022-01-30 00:05:47
    # Until I figure out a proper contents-observing traitType for Python
    # collections like list, deque, dict, I stick with Qt configable here.
    # @markConfigurable("RecentScripts", trait_notifier=True)
    @markConfigurable("RecentScripts", "Qt")
    @recentScripts.setter
    def recentScripts(self, val: typing.Optional[typing.Union[collections.deque, list, tuple]] = None):
        # print(f"ScipyenWindow.recentScripts.setter {val}")
        if isinstance(val, (collections.deque, list, tuple)):
            self._recentScripts = collections.deque((s for s in val if os.path.isfile(s)))
            # self._recentScripts = list((s for s in val if os.path.isfile(s)))

        else:
            # self._recentScripts = list()
            self._recentScripts = collections.deque()

        # NOTE:2022-01-28 23:16:57
        # obsolete; this is added to configurable_traits at __init__, AFTER
        # WorkspaceGuiMixin (ScipyenConfigurable) initialization
        # albeit this mechanism it NOT currently used until I figure out a nice
        # way to notify changes in the contents of list, deque, dict via the
        # DataBag & traitlets.TraitType framework.
        #

        # if isinstance(getattr(self, "configurable_traits", None), DataBag):
            # self.configurable_traits["RecentScripts"] = self._recentScripts

        self._refreshRecentScriptsMenu_()

    # ### END   Properties and slots connected to properties
    
    @Slot(object)
    @safewrapper
    def slot_windowActivated(self, obj):
        r"""Not used, but keep it
        """
        if isinstance(obj, (QtWidgets.QMainWindow, mpl.figure.Figure)):
            self.setCurrentWindow(obj)

    @Slot(int)
    @safewrapper
    def slot_windowVariableDeleted(self, wid):
        # TODO
        viewer = self.sender()
        if not isinstance(viewer, QtWidgets.QMainWindow):
            return

        assert viewer.ID == wid
        
    def requestActivate(self):
        r"""workaround wayland"""
        if os.getenv("XDG_SESSION_TYPE").lower() == "wayland":
            return
        super().requestActivate()
        
    def activateWindow(self):
        # print(f"{self.__class__.__name__}.activateWindow")
        #super().activateWindow()
        if sys.platform== "win32":
            self.windowHandle().raise_()
        else:
            if os.getenv("XDG_SESSION_TYPE").lower() == "wayland":
                return
            super().activateWindow()
            
    # ### BEGIN Global menu stuff - see also BEGIN  global menu stuff - END  global menu stuff block in __init__
    #
    def getAppMenu(self):
        # BUG 2025-07-01 23:17:12 FIXME
        # this returns None whe using a QSPlashScreen!
        if self.menuBar().isNativeMenuBar() and self._globalMenuServiceName_ == "com.canonical.AppMenu.Registrar":
            # dbusinterface = QtDBus.QDBusInterface(self._globalMenuServiceName_, "/" +  self._globalMenuServiceName_.replace(".", "/") + self._globalMenuServiceName_.replace(".", "/"),
            #                                       self._globalMenuServiceName_)
            # dbusinterface.setTimeout(100)
            if __has_PyQt6__ or __has_PySide6__:
                v = int(self.winId())
            else:
                v = QtCore.QVariant(int(self.winId()))
                
                if not v.convert(QtCore.QVariant.UInt): # NOTE: 2023-01-08 23:10:14 MUST convert to UInt
                    return
            # NOTE: 2023-01-08 22:58:38
            # When all OK, result should be a list with:
            # • str: address of the connection on DBus (e.g.: ':1.383')
            # • str: The path to the object which implements the com.canonical.dbusmenu interface.
            #           (e.g., /MenuBar/4') as a str (NOT QDBusObjectPath!) 
            #
            #       If you use QDBusViewer, the address points to /MenuBar/x 
            #       where x is an int >= 1, and it has the following interfaces:
            #       ∘ com.canonical.dbusmenu (AHA!)
            #       ∘ the next three are generic and present on all objects on DBus
            #           ▷ org.freedesktop.DBus.Properties
            #           ▷ org.freedesktop.DBus.Introspectable
            #           ▷ org.freedesktop.DBus.Peer
            #
            result = self._dbusAppMenuInterface_.call("GetMenuForWindow", v).arguments()
        
            print(f"{self.__class__.__name__}.getAppMenu: result -> {result}")
            if len(result) == 1: # oops!
                # warnings.warn(result[0])
                return
        
                # address, objpath = result
        
            return result
        else:
            return self.menuBar()
            
    def _deregister_menuBar_(self):
        if not self.menuBar().isNativeMenuBar() :
            return
        if self._app_menu_ is not None and self._globalMenuServiceName_ == "com.canonical.AppMenu.Registrar" and isintance(self._dbusAppMenuInterface_, QtDBus.QDBusInterface):
            self._dbusAppMenuInterface_.setTimeout(100)
            
            if __has_PyQt6__ or __has_PySide6__:
                old_v = int(self._wm_id_)
            else:
                old_v = QtCore.QVariant(self._wm_id_)
                if not old_v.convert(QtCore.QVariant.UInt):
                    return
                
            reply = self._dbusAppMenuInterface_.call("UnregisterWindow", old_v)
                
    def _restore_menuBar_(self):
        r"""Hack to restore the window's menubar in the desktop's global menu.
        
        Only necessary when running Scipyen in a windowing system / desktop
        environment that provides such service, such as GNOME AND KDE on UN*X.
        
        """
        if not self.menuBar().isNativeMenuBar() :
            return self.menuBar()
        
        currentAppMenu = self.getAppMenu()
        
        if self._app_menu_ is None:
            # nothing to restore
            return
        
        if currentAppMenu is None:
            if self._globalMenuServiceName_ == "com.canonical.AppMenu.Registrar" and isintance(self._dbusAppMenuInterface_, QtDBus.QDBusInterface):
                # service_name = self._globalMenuServiceName_
                # service_path = "/com/canonical/AppMenu/Registrar"
                # interface = "com.canonical.AppMenu.Registrar"
                # dbusinterface = QtDBus.QDBusInterface(service_name, service_path,
                #                                     interface)
                self._dbusAppMenuInterface_.setTimeout(100)
                
                old_v = QtCore.QVariant(self._wm_id_)
                new_v = QtCore.QVariant(int(self.winId()))
                
                if old_v.convert(QtCore.QVariant.UInt) and new_v.convert(QtCore.QVariant.UInt):
                    # deregister old WM window ID, then register the new one
                    # to the same DBus object path (i.e. dbusmenu instance)
                    dereg_reply = self._dbusAppMenuInterface_.call("UnregisterWindow", old_v)
                    newreg_reply = self._dbusAppMenuInterface_.call("RegisterWindow", new_v, QtDBus.QDBusObjectPath(self.menubar[1]))

    @Slot(QtGui.QWindow.Visibility)
    def _slot_visibility_changed(self, val):
        if self.menuBar().isNativeMenuBar() and hasattr(self, "_wm_id_") and self._wm_id_ != int(self.winId()):
            if self._globalMenuServiceName_ == "com.canonical.AppMenu.Registrar":
                self._restore_menuBar_()

    #
    # ### END   Global menu stuff - see also BEGIN  global menu stuff - END  global menu stuff block in __init__
    
    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.LanguageChange:
            self.retranslateUi(self)
        super(ScipyenWindow, self).changeEvent(event)

    @safewrapper
    def handle_mpl_figure_click(self, evt):
        # print(f"{self.__class__.__name__}.handle_mpl_figure_click evt.canvas.figure: {evt.canvas.figure} ({evt.canvas.figure.number})")
        self.raiseWindow(evt.canvas.figure)

    @safewrapper
    def handle_mpl_figure_enter(self, evt):
        r""" DEPRECATED """
        pass
        # self.setCurrentWindow(evt.canvas.figure)

    @safewrapper
    def handle_mpl_figure_close(self, evt):
        r"""Removes the figure from the workspace and updates the workspace table.
        Triggered by closing the figure window by clicking its close button
        """
        # NOTE: FIXME/BUG 2023-06-07 09:00:40
        # because of troubles/issues related to the double-management of mpl figs
        # (here and in Gcf) the general phylosophy SHOULD be to register all figs
        # with the Gcf, then remove them on closing, regardless of the autoRemoveViewers
        # settings
        fig = evt.canvas.figure
        plt.close(fig) # this removes fig from Gcf.figs
        self.deRegisterWindow(fig) # this just removes the reference to figure in self.viewers and self.currentViewers
        
        fig_var_name = self.workspaceModel.getDisplayableVarnamesForVar(self.workspace, fig)
        if len(fig_var_name):
            for name in fig_var_name:
                self.workspaceModel.unbindFromNamespace(name)
                
    @safewrapper
    def newViewer(self, winClass, *args, **kwargs):
        r"""Factory method for a GUI Viewer or matplotlib figure.

        Parameters:
        -----------

        winClass : str, type, or sip.wrappertype, or Shiboken.Object (for PySide6)
            The only acceptable type is mpl.figure.Figure (where mpl is an alias to matplotlib)

            The only acceptable sip.wrappertype objects are the ones loaded by 
            slot_loadPlugins:

            DataViewer, MatrixViewer, ImageViewer, SignalViewer, TableEditor, 
            TextViewer, XMLViewer.

            When a str the ony acceptable ones are the string verison of the 
            above (i.e. the value of their __name__ attribute).

        *args, **kwargs: passed directly to the constructor (__init__ function)
            of the winClass

        Returns:
        ========

        The viewer instance; NOTE: this instance is also created in the workspace
        as a "top-level" viewer.

        """
        # NOTE: 2021-07-08 14:52:44
        # called by ScipyenWindow.slot_newViewerMenuAction

        # print(f"{self.__class__.__name__}.newViewer winClass = {winClass} (arg type = {type(winClass).__name__})")
        # print("WindowManager.newViewer **kwargs", **kwargs)
        # print(f"{self.__class__.__name__}: newViewer({winClass})")
        if isinstance(winClass, str) and len(winClass.replace("&", "").strip()):
            wClass = winClass.replace("&", "")
            

            if wClass not in list(v.__name__ for v in self.viewers):
                raise ValueError(f"Unexpected viewer class name{wClass}")

            win_classes = list(filter(lambda x: x.__name__ == wClass, self.viewers))

            if len(win_classes):
                winClass = win_classes[0]

            else:
                raise ValueError(f"Unexpected viewer class name {wClass}")

        else:
            if winClass not in self.viewers:# or winClass != mpl.figure.Figure or not issubclass(winClass, QtWidgets.QMainWindow):
                raise ValueError(f"Unexpected viewer class {winClass.__name__}")

        if winClass is mpl.figure.Figure:
            fig_kwargs = dict()
            fig_init_params = inspect.signature(mpl.figure.Figure).parameters

            for key, val in kwargs.items():
                if key in fig_init_params:
                    fig_kwargs[key] = val
                    
            # NOTE: 2025-06-22 22:38:23
            # looks like I still need to to this, here...
            if __has_PyQt6__ or __has_PySide6__:
                mpl.use("qtagg")
            else:
                mpl.use("qt5agg") # this seems to be the default...
                
            win = plt.figure(*args, **fig_kwargs)

            workspace_win_varname = f"Figure{win.number}"

        else:
            win_title = kwargs.pop("win_title", winClass.__name__)
            # print(f"{self.__class__.__name__}.newViewer: win_title = {win_title}, counter_suffix = {counter_suffix}")
            if win_title[0].isupper():
                wt = win_title[0].lower()
                if len(win_title) > 1:
                    wt += win_title[1:]
                win_title = wt # + f": {win_title}"

            # print(f"{self.__class__.__name__}.newViewer for win_title = {win_title}")
            
            # kwargs["win_title"] = win_title
            if "parent" not in kwargs:
                kwargs["parent"] = self # needed on X11 platform, but not on Wayland,
                                        # see NOTE: 2024-04-17 11:53:29 in scipyenviewer.py
                
            win = winClass(*args, **kwargs)
            # print(f"{self.__class__.__name__}.newViewer for {winClass.__name__} win = {win}")

            variables = dict([item for item in self.shell.user_ns.items(
                ) if item[0] not in self.user_ns_hidden and not item[0].startswith("_")])

            # NOTE: 2024-08-25 16:20:55 FIXME ?
            # not sure why all these lines of code below are needed, especially
            # the condition on listedWindows...
            varnames = reverse_mapping_lookup(variables, win)
            # print(f"{self.__class__.__name__}.newViewer for {winClass.__name__} varnames = {varnames}")
            
            listedWindows = [self.workspace[n] for n in varnames if isinstance(self.workspace[n], winClass)]
            # print(f"{self.__class__.__name__}.newViewer for {winClass.__name__} listedWindows = {listedWindows}")

            if win not in listedWindows:
                win_title, counter_suffix = validate_varname(win_title, self.workspace, return_counter=True)
                
            # print(f"{self.__class__.__name__}.newViewer for {winClass.__name__} win_title = {win_title}")
            
            workspace_win_varname = strutils.str2symbol(win_title)
            workspace_win_varname = workspace_win_varname[0].lower()+workspace_win_varname[1:]
            
            win.ID = counter_suffix
            # win.winTitle = workspace_win_varname
            win.winTitle = workspace_win_varname + f": {winClass.__name__}"
            

        self.registerWindow(win)  # required !
        self.workspaceModel.bindObjectInNamespace(workspace_win_varname, win)

        return win
    
    def _updateConsolesEditor(self, target:typing.Optional[str]=None):
        if isinstance(target, str):
            if target.lower() == "internal":
                console_objects = [self.console]
            elif target.lower() == "external":
                console_objects = [self.external_console]
            else:
                console_objects = [self.console, self.external_console]
        else:
            console_objects = [self.console, self.external_console]
        
        for console in console_objects:
            if isinstance(console, (consoles.ScipyenConsole, consoles.ExternalIPython)):
                if isinstance(console.active_frontend, consoles.ConsoleWidget):
                    # NOTE: 2025-04-06 17:28:19
                    # for the %edit magic:
                    if self.overrideSystemEditor and isinstance(self.scipyenEditor, str): # allow empty string to wipe out the editor
                        console.active_frontend.editor = self.scipyenEditor
                    else:
                        # normally this might set up in jupyer configuration files,
                        # so do not override it
                        if len(console.active_frontend.editor.strip()) == 0:
                            if isinstance(desktoputils.DEFAULT_EDITOR, str) and len(desktoputils.DEFAULT_EDITOR.strip()):
                                console.active_frontend.editor = desktoputils.DEFAULT_EDITOR
                            
                            
    def _adopt_mpl_figure(self, fig: mpl.figure.Figure):
        r"""Gives a FigureCanvasQTAgg to fig.
        To be used only with mpl Figure created directly from their c'tor, i.e.,
        lacking the "manager" or a "number" atributes.
        
        NOTE: This will also 'register' them with the Gcf
        
        """
        if not isinstance(fig, mpl.figure.Figure):
            return
        
        backend_mod = None
        backend_super_class = mpl.backend_bases._Backend
        # NOTE: 2023-01-29 16:14:04
        # for mpl figures created manually
        # add a manager backend to the figure - we FORCE the use of the
        # qt5agg backend throughout
        # -- code from matplotlib.pyplot.switch_backend
        #
        # print(f"{self.__class__.__name__}._adopt_mpl_figure ({fig}, number {fig.number})")
        import matplotlib.cbook as cbook
        # NOTE: 2024-06-03 13:41:00
        # with mpl api change cbook has lost _backend_module_name
        # the condition below I think is correct
        if hasattr(mpl, "_version") and hasattr(mpl._version, "version") and int(mpl._version.version.split('.')[1]) < 9:
            backend_mod = importlib.import_module(cbook._backend_module_name(mpl.rcParams["backend"]))
            # backend_mod = importlib.import_module(cbook._backend_module_name("Qt5Agg"))
            # backend_class = mpl.backend_bases._Backend
            # class backend_mod(mpl.backend_bases._Backend):
            #     locals().update(vars(backend_mod))
                
        else: # assume the latest mpl and keep fingers crossed
            backend_name = mpl.get_backend()
            
            candidate_backend_module_names = list(filter(lambda x: backend_name.lower() in x, mpl.backends.__dict__.keys()))
            
            if len(candidate_backend_module_names):
                backend_mod = mpl.backends.__dict__.get(candidate_backend_module_names[0], None)
                
            
        if backend_mod is None:
            scipywarn(f"{self.__class__.__name__}._adopt_mpl_figure - cannot establish the backend used")
            return
            
        class backend_mod(backend_super_class):
            locals().update(vars(backend_mod))
            
        if getattr(fig.canvas, "manager", None) is None:
            # print(f"{self.__class__.__name__}._adopt_mpl_figure - no canvas")
            
            # NOTE: for debugging 2023-10-24 13:24:26
            # return fig
        
            new_figure_manager = getattr(backend_mod, "new_figure_manager", None)

            if new_figure_manager is None:
                # only try to get the canvas class if have opted into the new scheme
                canvas_class = backend_mod.FigureCanvas

                def new_figure_manager_given_figure(num, figure):
                    return canvas_class.new_manager(figure, num)

                def new_figure_manager(num, *args, FigureClass=Figure, **kwargs):
                    fig = FigureClass(*args, **kwargs)
                    return new_figure_manager_given_figure(num, fig)

                def draw_if_interactive():
                    if matplotlib.is_interactive():
                        manager = _pylab_helpers.Gcf.get_active()
                        if manager:
                            manager.canvas.draw_idle()

                backend_mod.new_figure_manager_given_figure = new_figure_manager_given_figure
                backend_mod.new_figure_manager = new_figure_manager
                backend_mod.draw_if_interactive = draw_if_interactive

            plt_fig_nums = list(Gcf.figs.keys())
            num = 1
            if len(plt_fig_nums) > 0:
                missing_ndx = set(k for k in range(max(plt_fig_nums))
                                if k not in plt_fig_nums and k > 0)
                if len(missing_ndx):
                    num = min(missing_ndx)
                else:
                    num = max(plt_fig_nums) + 1

            fig.canvas.manager = backend_mod.new_figure_manager_given_figure(
                num, fig)
            
            Gcf._set_new_active_manager(fig.canvas.manager)
            fig.number = num
            Gcf.figs[num] = fig.canvas.manager

        fig.canvas.mpl_connect("button_press_event",
                                self.handle_mpl_figure_click)
        
        fig.canvas.mpl_connect("figure_enter_event",
                                self.handle_mpl_figure_enter)

        fig.canvas.mpl_connect("close_event", self.handle_mpl_figure_close)

        # NOTE: 2023-01-27 22:43:23
        # install and event filter on the mpl figure's window - assumes Qt5 backend
        # this will capture activation & ficus events to set this figure instance
        # as the current one in Scipyen's window manager, AND ALSO in pylab
        #
        # this has the same effect as
        evtFilter = WindowEventFilter(fig, parent=self)
        # NOTE: 2023-01-29 16:28:50
        # We assume matplotlib Qt5Agg backend is used throughout Scipyen;
        # there may be figures created via the constructor, that will not
        # have a manager
        fig.canvas.manager.window.installEventFilter(evtFilter)

        return fig

    def registerWindow(self, win):
        if not isinstance(win, (QtWidgets.QMainWindow, mpl.figure.Figure)):
            return

        winClass = type(win)
        
        # print(f"{self.__class__.__name__}.registerWindow(win: {winClass})")

        if winClass is mpl.figure.Figure:
            win = self._adopt_mpl_figure(win)

        else:
            if isinstance(getattr(win, "sig_activated", None), QtCore.SignalInstance):
                win.sig_activated[int].connect(self.slot_setCurrentViewer)
            else:
                winEvtFilter = WindowEventFilter(win, parent=self)
                win.installEventFilter(winEvtFilter)

            if getattr(win, "appWindow", None) is not self:
                win.setParent(self)

        if winClass not in self.viewers:
            self.viewers[winClass] = list()

        if win not in self.viewers[winClass]:
            self.viewers[winClass].append(win)
            
        self.currentViewers[winClass] = win
        
        return win

    @safewrapper
    def deRegisterWindow(self, win):
        r"""Removes references to the viewer window 'win' from the manager.

        Parameters:
        -----------

        win: a QMainWindow or matplotlib.figure.Figure instance

        ATTENTION: This function neither removes the viewer object from the 
        workspace, nor unbinds it from its symbol in the workspace!!!
        """
        # print(f"\n***\n{self.__class__.__name__}.deRegisterWindow({type(win).__name__})")
        if not isinstance(win, (QtWidgets.QMainWindow, mpl.figure.Figure)):
            return
        
        # print(f"{self.__class__.__name__}.deRegisterWindow: {win}")

        viewer_type = type(win)

        old_viewer_index = None

        if viewer_type in self.viewers.keys():
            # print(f"{self.__class__.__name__}.deRegisterWindow: {viewer_type.__name__} found in self.viewers.keys()")
            if win in self.viewers[viewer_type]:
                # print(f"{self.__class__.__name__}.deRegisterWindow: {win} found in self.viewers[{viewer_type.__name__}]")
                old_viewer_index = self.viewers[viewer_type].index(win)
                # print(f"{self.__class__.__name__}.deRegisterWindow: old_viewer_index = {old_viewer_index}")
                self.viewers[viewer_type].remove(win)

        # print(f"{self.__class__.__name__}.deRegisterWindow: viewers left: {len(self.viewers[viewer_type])}")
        

        if viewer_type in self.currentViewers:
            # print(f"{self.__class__.__name__}.deRegisterWindow: currentViewers[{viewer_type.__name__}]  = {self.currentViewers[viewer_type]}")
            # print(f"{self.__class__.__name__}.deRegisterWindow: {viewer_type.__name__} found in self.currentViewers")
            
            if self.currentViewers[viewer_type] is win:
                self.currentViewers[viewer_type] = None
                
            if len(self.viewers[viewer_type]):
                self.currentViewers[viewer_type] = self.viewers[viewer_type][-1]
            
    def raiseWindow(self, obj):
        r"""Sets obj to be the current window and raises it.
        Steals focus.
        """
        # WARNING: 2025-03-24 21:40:05 FIXME
        # Doesn't work in wayland
        
        # print(f"{self.__class__.__name__}.raiseWindow ({obj})")
        if not isinstance(obj, (scipyenviewer.ScipyenViewer, mpl.figure.Figure)):
            return

        self.setCurrentWindow(obj)

        if isinstance(obj, mpl.figure.Figure):
            # if not isinstance()
            if obj.canvas.manager is not None:
                if getattr(obj, "number", None) is not None:
                    plt.figure(obj.number)
                plt.get_current_fig_manager().canvas.activateWindow()  # steals focus!
                plt.get_current_fig_manager().canvas.update()
                plt.get_current_fig_manager().canvas.draw_idle()
                obj.show()  # steals focus!

        else:
            if os.getenv("XDG_SESSION_TYPE").lower() != "wayland":
                obj.activateWindow()
                obj.raise_()
            obj.setVisible(True)

    def setCurrentWindow(self, obj):
        r"""Sets obj to be the current window without raising or focus stealing.
        Handles both QMainWindow and matplotlib Figure objects
        """
        if not isinstance(obj, (scipyenviewer.ScipyenViewer, mpl.figure.Figure)):
            return

        if type(obj) not in self.viewers.keys():
            self.viewers[type(obj)] = list()

        if obj not in self.viewers[type(obj)]:
            self.viewers[type(obj)].append(obj)

        if isinstance(obj, mpl.figure.Figure):
            if hasattr(obj, "number"):
                plt.figure(obj.number)

        self.currentViewers[type(obj)] = obj

    @property
    def matplotlib_figures(self):
        r"""A list of figures managed by matplotlib.
        """
        return [plt.figure(i) for i in plt.get_fignums()]

    @property
    def managed_matplotlib_figures(self):
        r"""A list of figures managed by both matplotlib and self.
        """
        return [fig for fig in self.matplotlib_figures if fig in self.viewers[mpl.figure.Figure]]

    @Slot(int)
    @safewrapper
    def slot_setCurrentViewer(self, wId):
        r""" Delegates to self.setCurrentWindow 
            Only meant for QMainWindow instances
        """
        viewer = self.sender()
        viewer_type_name = type(viewer).__name__

        if not isinstance(viewer, QtWidgets.QMainWindow):
            return

        self.setCurrentWindow(viewer)

    # BEGIN PyQt slots

    @Slot()
    def _slot_chooseCodeEditor(self):
        d = qd.QuickDialog(self, "Choose code editor")
        editorNameInput = qd.StringInput(
            d, "Editor name (e.g., 'kate' or 'kwrite')")
        editorNameInput.setValue(self.scipyenEditor)
        d.editorNameInput = editorNameInput
        d.adjustSize()
        if d.exec() == QtWidgets.QDialog.Accepted:
            self.scipyenEditor = d.editorNameInput.text()

    @Slot(bool)
    def _slot_setOverrideSystemEditor(self, val):
        self.overrideSystemEditor = val == False

    @Slot()
    def slot_launchExternalRunningIPython(self):
        self._init_ExternalIPython_(new="connection")

    @Slot()
    @safewrapper
    def slot_launchExternalIPython(self):
        self._init_ExternalIPython_()

    @Slot()
    @safewrapper
    def slot_launchExternalNeuronIPython(self):
        self._init_ExternalIPython_(new="neuron")

    @Slot()
    @safewrapper
    def slot_launchExternalRunningIPythonNeuron(self):
        self._init_ExternalIPython_(new="neuron_ext")

    @Slot()
    @safewrapper
    def slot_initQtConsole(self):
        needs_init = False
        if not isinstance(self.console, consoles.ScipyenConsole):
            needs_init = True
            self._init_QtConsole_()

        self.shell.events.register("pre_execute", self.workspaceModel.preExecute)
        # self.shell.events.register("post_execute", self.workspaceModel.post_execute)
        self.shell.events.register("post_run_cell", self.workspaceModel.postRunCell)

        self.slot_changeDirectory(self.recentDirectories[0])
        self.console.show()
        if needs_init:
            self.console.consoleWidget.set_pygment(self.console.consoleWidget._console_pygment)
        

    # END   PyQt slots

    # BEGIN Methods

    def _set_recentScripts_(self, value):
        pass

    @safewrapper
    def _init_ExternalIPython_(self, new: str = ""):
        r"""External IPython launcher.

        If no External IPython console instance exists, launches an instance
        of External IPython console (running external kernels as separate processes).

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

            "neuron_ext": launches neuron in an external, existing, kernel
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
        from core.extipyutils_client import (nrn_ipython_initialization_cmd,
                                             cmd_foreign_shell_ns_hidden_listing)
        from functools import partial
        # print("_init_ExternalIPython_ new", new)

        if not isinstance(self.external_console, consoles.ExternalIPython):
            # NOTE: 2021-01-30 13:52:58
            # there is no running ExternalIPython instance
            if isinstance(new, str) and new in ("connection", "neuron_ext"):
                if sys.platform.startswith("win32"):
                    options = QtWidgets.QFileDialog.Option.DontUseNativeDialog
                    kw = {"options":options}
                else:
                    kw = {}
                    
                connection_file, file_type = QtWidgets.QFileDialog.getOpenFileName(self,
                                                                                   "Connect to Existing Kernel",
                                                                                   jupyter_runtime_dir(),
                                                                                   "Connection file (*.json)",
                                                                                   **kw)
                if not connection_file:
                    return

                self.external_console = consoles.ExternalIPython.launch(
                    existing=connection_file)

            else:
                # NOTE: 2021-01-15 14:50:32
                # this will automatically start a (remote) IPython kernel
                self.external_console = consoles.ExternalIPython.launch()

            # NOTE: 2024-09-20 23:40:49
            # bind a reference to the external console in our workspace
            # useful to get to it diretly in Scipyen's console
            self.workspaceModel.bindObjectInNamespace("external_console", 
                                                      self.external_console,
                                                      hidden=True)
            
            # NOTE: 2024-09-20 23:41:42
            # what's this for ?!?
            # self.external_console.window.sig_kernel_count_changed[int].connect(self._slot_remote_kernel_count_changed)

            # NOTE: 2021-01-15 14:46:07
            # any value of new other than "neuron" or "neuron_ext" is ignored 
            # when the console is first initiated
            if isinstance(new, str):
                if new == "neuron":
                    self.external_console.execute(nrn_ipython_initialization_cmd,
                                                  silent=True,
                                                  store_history=False)

                elif new == "neuron_ext":
                    self.external_console.window.start_neuron_in_current_tab()

            self.external_console.window.sig_shell_msg_received[object].connect(
                self._slot_ext_krn_shell_chnl_msg_recvd)
            self.external_console.window.sig_kernel_disconnect[dict].connect(
                self._slot_ext_krn_disconnected)
            self.external_console.window.sig_kernel_restart[dict].connect(
                self._slot_ext_krn_restart)
            self.external_console.window.sig_kernel_stopped_channels[dict].connect(
                self._slot_ext_krn_stop)
                    
            # NOTE: 2024-09-20 23:45:25
            # OK, we now need to get a list of hidden variable names in the foreign kernel
            # 
            ns = self.external_console.window.find_tab_title(self.external_console.window.active_frontend)
            self.external_console.execute(cmd_foreign_shell_ns_hidden_listing(namespace=ns))

        else:
            # NOTE: 2021-01-30 13:53:37
            # an instance of ExternalIPython is already running, but the kernel
            # may have been stopped (and therefore connection is gone) and the
            # window closed
            frontend_factory = None
            # print("\texternal console exists")
            if self.external_console.window.active_frontend is None:
                # NOTE: 2021-01-30 13:54:46
                # console instance exists but does not have an active frontend anymore
                # therefore kill the running kernel (if any and running) and start
                # with clean slate
                if (self.external_console.kernel_manager is not None):
                    # kill the current (existing) kernel
                    try:
                        if hasattr(self.external_console.kernel_manager, "is_alive") and self.external_console.kernel_manager.is_alive():
                            self.external_console.kernel_manager.shutdown_kernel(
                                now=True, restart=False)
                    except Exception as e:
                        traceback.print_exc()

                frontend_factory = self.external_console.window.create_tab_with_new_frontend

                if isinstance(new, str):
                    if new == "connection":
                        # will ask for an existing kernel
                        frontend_factory = self.external_console.window.create_tab_with_existing_kernel

                    elif new == "neuron":
                        frontend_factory = partial(self.external_console.window.create_tab_with_new_frontend,
                                                   code=nrn_ipython_initialization_cmd,
                                                   silent=True, store_history=False)

                    elif new == "neuron_ext":
                        frontend_factory = self.external_console.window.create_tab_with_existing_kernel
                        frontend_factory = partial(self.external_console.window.create_tab_with_existing_kernel,
                                                   code=nrn_ipython_initialization_cmd,
                                                   silent=True, store_history=False)

            else:
                # print("\t* active frontend exists")
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
                                                   code=nrn_ipython_initialization_cmd,
                                                   silent=True, store_history=False)

            if frontend_factory is not None:
                if frontend_factory():
                    self.external_console.window.setVisible(True)
                    ns = self.external_console.window.find_tab_title(self.external_console.window.active_frontend)
                    self.external_console.execute(cmd_foreign_shell_ns_hidden_listing(namespace=ns))
                    if isinstance(new, str) and str == "neuron_ext":
                        self.external_console.window.start_neuron_in_current_tab()
                        
        self._updateConsolesEditor("external")

    # END   Methods

    @safewrapper
    def _init_QtConsole_(self):
        r"""Starts an interactive IPython shell with a QtConsole frontend.

        The shell runs an embedded ("InProcess") IPython kernel with an event 
        loop run by the Scipyen QApplication instance.

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
        command line, respectively, as the "console", "shell" and "ipkernel" 
        symbols, and as Scipyen's main window attributes with the same names 
        (hence, accessible in the console as "mainWindow.shell", 
        "mainWindow.console" and "mainwindow.ipkernel").

        The Scipyen's user workspace is the same as the shell's namespace
        (self.ipkernel.shell.user_ns).
        
        However, shell.kernel.user_ns is None!
        
        """
        
        # NOTE: 2025-06-24 21:43:22
        # Here, user's workspace is shell.user_ns, shell.kernel.user_ns,
        # which is None
        

        # creates a Qt console with an embedded ipython kernel
        # i.e. a QtInProcessKernelManager
        #
        # NOTE: 2018-10-08 10:48:46
        # the code inside pict is executed in its own QApplication loop
        # whereas code entered in this console is executed in the ipython kernel
        # which therefore has to be "embedded" in the QApplication

        # At any time there can be only ONE master event loop,
        #
        # In this case, that's the QApplication event loop

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
        # Both will generate preExecute and post_execute IPython events, HOWEVER:
        #
        # * console.execute(str) always executes the expression in str inside the
        #   console's shell/kernel; code will be echoed to the console UNLESS
        #   the hidden=True is also passed after the str parameter
        #
        # * shell.run_cell(str) does the same as console.execute with hidden=False
        #   (the extression in str is always echoed; there is no "hidden" parameter
        #   to run_cell(...))

        if not isinstance(self.console, consoles.ScipyenConsole):
            self.console = consoles.ScipyenConsole(scipyenWindow=self, banner=_scipyen_console_banner_)
            # self.console = consoles.ScipyenConsole(parent=self)
            self.console.executed.connect(self.slot_updateHistory)
            self.console.executed.connect(self.slot_updateCwd)

            self.ipkernel = self.console.consoleWidget.ipkernel
            self.shell = self.ipkernel.shell
            
            self.shell.cache_size = self.defaultShellCacheSize
            self.stdout = self.ipkernel.stdout

            # NOTE: 2019-08-03 17:03:03
            # ### BEGIN populate the command history widget
            
            # this is always 1 immediately after initialization
            self.executionCount = self.ipkernel.shell.execution_count

            # access history database independently of the shell
            self.historyAccessor = HistoryAccessor()
            # should not interfere with the history

            hist = self.historyAccessor.search('*')

            # session number
            sessionNo = None

            # Sequence of QTreeWidgetItem objects holding the statements in the
            # history
            items = list()
            
            # NOTE: 2025-04-29 11:08:04
            # customize font appearance on history tree items
            font = self._defaultUIFont if self._useSystemDefaultFont else self._commandHistoryFont

            # populate the items list
            # • create session QTreeWidgetItem (one for each session in history);
            # • create QTreeWidgetItem for each statement in history, make it a 
            #   child of the corresponding session QTreeWidgetItem;
            # • apply custom font to all QTreeWidgetItem objects.
            for session, line, inline in hist:
                if sessionNo is None or sessionNo != session:
                    sessionNo = session  # cache the session
                    sessionInfo = self.historyAccessor.get_session_info(sessionNo)
                    sessionItem = QtWidgets.QTreeWidgetItem(self.historyTreeWidget, self._historySessionInfo_(sessionNo))
                    for col in range(sessionItem.columnCount()):
                        sessionItem.setFont(col, font)
                    items.append(sessionItem)

                lineItem = QtWidgets.QTreeWidgetItem(sessionItem, self._historyLineInfo_(line, inline))
                for col in range(lineItem.columnCount()):
                    lineItem.setFont(col, font)
                items.append(lineItem)

            # create a session QTreeWidgetItem for the current session and label
            # it as "Current"
            self.currentSessionTreeWidgetItem = QtWidgets.QTreeWidgetItem(
                self.historyTreeWidget, ["Current"])

            # appent the current session QTreeWidgetItem to items
            items.append(self.currentSessionTreeWidgetItem)

            # NOTE: 2017-03-21 22:55:57 much better!
            # For the console to process a drop event with contents dragged from
            # history tree widget, I ignore the QMimeData (see consoles module) 
            # and just paste whatever text was selected in the history tree widget
            # as text into the console window ('buffer'). The user needs to press
            # "Return" or "Enter" to execute the statement. This is the same approach
            # as the one used for dropping a text from an external source, and is
            # deliberate: there is not guarantee that the etxt is syntactically correct
            # or that it will be executed without error. The user has to place the 
            # console text cursor after the dropped text, which will help them identify
            # issues with the pasted code before pressing "Enter" for the code to 
            # be executed.
            
            self.console.historyItemsDropped.connect(self.slot_pasteHistorySelection)
            
            # this ensures that whatever text is dragged onto the console from the
            # workspace, only the variable name (symbol) in the workspace is seen
            # by the console (and hence, presing Enter will typically display or
            # ``repl`` that variable in the console window)
            self.console.workspaceItemsDropped.connect(self.slot_pasteWorkspaceSelection)
            
            # this ensures that any file system item (folder, file) dropped onto
            # the console triggers a change of working directory (if a folder) or
            # the loading of that file in the workspace uing the default file loader
            # defined in the pictio module.
            self.console.fileSystemItemsDropped.connect(self.slot_openSelectedFileItems)
            
            # effectively delegates the loading of file system url (see above) 
            # from the console to the code in ScipyenWindow.
            self.console.loadUrls[object, bool, QtCore.QPoint].connect(self.slot_loadDroppedURLs)
            
            # as above
            self.console.pythonFileReceived[str, QtCore.QPoint].connect(self.slot_handlePythonTextFile)
            
            # self.console.sig_shell_msg_received[object].connect(self._slot_int_krn_shell_chnl_msg_recvd)

            # ### BEGIN Populate historyTreeWidget with the ipython history
            # NOTE: 2025-04-29 11:32:25 this WILL capture past sessions in the
            # external ipyton console; this is because all that is IPython history 
            # is stored in the same local database file in the user's home directory
            self.historyTreeWidget.insertTopLevelItems(0, items)
            
            self.historyTreeWidget.scrollToItem(self.currentSessionTreeWidgetItem)
            
            self.historyTreeWidget.setCurrentItem(self.currentSessionTreeWidgetItem)
            self.historyTreeWidget.resizeColumnToContents(0)
            # ### END   Populate historyTreeWidget with the ipython history

            # NOTE: until input has been enetered at the console, this is the LAST session on record NOT the current one!
            self.currentSessionID = self.historyAccessor.get_last_session_id()

            self.selectedSessionID = None

            # ### END   populate the command history widget
            
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
            #
            # see NOTE: 2023-05-27 22:00:37 about manipulating variables in the 
            # workspace and updating the workspace model automatically
            #
            # see NOTE: 2025-06-24 21:43:22
            self.workspace = self.ipkernel.shell.user_ns

            # NOTE: 2023-05-27 22:19:46
            # The assignments below are meant to bypass the variable observer in 
            # the workspace model; hence these objects are bound directly to
            # symbols in the workspace
            #
            # Of course one could have achieved the same thing by calling
            # 
            # 'self workspaceModel.bindObjectInNamespace(name, obj, hidden=True)'
            #
            # instead of the direct assignment 'self.workspace[name] = obj' as
            # below
            #

            # NOTE: 2025-06-23 18:41:04
            # consider using shell API e.g.:
            # • "push": shell.push(variables, interactive=True) 
            #       pass interactive=False for "hidden" variables?
            # NOTE: 2020-11-12 12:51:36
            # used by %scipyen_debug line magic
            self.workspace["SCIPYEN_DEBUG"] = False

            self.workspace['mainWindow'] = self
            # self.workspace["scipyenDefaultSettings"] = self.scipyenDefaultSettings

            # NOTE: 2016-03-20 20:50:42 -- WRONG!
            # get_ipython() returns an instance of the interactive shell, NOT the kernel
            self.workspace['ipkernel'] = self.ipkernel
            self.workspace['kernel'] = self.ipkernel
            # useful for testing functionality; remove upon release
            self.workspace['console'] = self.console
            # alias to self.ipkernel.shell
            self.workspace["shell"] = self.shell
            self.workspace["scipyen_settings"] = self._scipyen_settings_
            self.workspace["scipyen_user_settings"] = self._user_settings_src_
            self.workspace["scipyen_user_settings_file"] = self._user_settings_file_
            self.workspace["scipyen_topdir"] = self._scipyendir_
            self.workspace["external_console"] = self.external_console
            self.workspace["user_home_environment_var"] = self._userenv_varname_
            self.workspace["user_home"] = self._user_home_

            # NOTE 2020-07-09 11:36:34
            # Override ExitAutocall objects in this kernel in order to let the
            # ScipyenMagics "exit" and "quit" to take over.
            # By default, self.workspace["exit"] and self.workspace["quit"] are
            # the same ExitAutocall object; see IPython.core.autocall module for
            # details
            #
            # The point of all this is that we can quit the Scipyen application when
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
            # this will have to be called as %exit line magic (i.e. automagic doesn't seem to work in this case)
            # see also NOTE 2020-07-09 11:36:34
            self.ipkernel.shell.register_magics(ScipyenMagics)

            # NOTE: 2020-11-29 15:57:08
            # this imports current module and all of its contents in the user 
            # workspace as well

            impcmd = ' '.join(
                ['from', "".join(["gui.", __module_file_name__]), 'import *'])

            self.ipkernel.shell.run_cell(impcmd)

            self.ipkernel.shell.run_cell("h5py.enable_ipython_completer()")

            # hide the variables added to the workspace so far (e.g., ipkernel,
            # console, shell, and imported modules) so that they don't show in
            # the workspace browser (the tree view in the User variables pane)
            # ATTENTION but there is a catch: this does NOT prevent the user from
            # assigning a variable to a symbol bound to one of these variables
            # -- effectively "overwriting" them.

            # NOTE: 2025-06-24 21:49:03
            # the line below work better if called AFTER _init_QtConsole_()
            # self._nonInteractiveVars_.update([i for i in self.workspace.items()])

            # --------------------------
            # finally, customize console window title and show it
            # -------------------------
            self.console.setWindowTitle(u'Scipyen Console')

        # self.console.show()
        # # NOTE: 2021-10-18 11:28:25
        # # The following must be called when console has become visible!
        # self.console.consoleWidget.set_pygment(self.console.consoleWidget._console_pygment)
        
        self._updateConsolesEditor("internal")
        
        self.actionUseShellAutomagic.setChecked(self.console.shellAutomagic)
        
    @Slot()
    @safewrapper
    def _slot_helpOnConsole_(self):
        # NOTE: 2016-03-20 21:18:32 REMEMBER:
        # to run code inside the console and use the console as stdout,
        # call console.execute(...)
        #
        # calling console.ipkernel.shell.run_cell(...) uses the system stdio
        #
        #
        # FIXME -- why does it appear to execute only ONE print command?
        self.console.execute("console_info()")

    @Slot()
    def slot_refreshView(self):
        if self.activeDockWidget is self.dockWidgetFileSystem:
            # self.slot_updateCwd()
            self._updateFileSystemView_(self.currentDir, False)
            
        elif self.activeDockWidget is self.dockWidgetHistory:
            # only update history if something has indeed been executed
            if self.console is not None and self.ipkernel.shell.execution_count > self.executionCount:
                self.executionCount = self.ipkernel.shell.execution_count
                self._updateHistoryView_(self.executionCount-1, self.console.consoleWidget.history_tail(1)[0])
        else:
            self.workspaceModel.update()

    # NOTE: 2016-03-26 17:07:17
    # as a workaround for the problem in NOTE: 2016-03-26 17:01:32
    @Slot()
    @safewrapper
    def slot_updateWorkspaceView(self):
        r"""
        Cosmetic update of the workspace viewer
        • sorts according to 1st column contents
        • resizes 1st column to its contents
        """
        self._sortWorkspaceViewFirstColumn_()
        self._resizeWorkspaceViewFirstColumn_()

    @Slot()
    def slot_updateWorkspaceModel(self):
        r""" pyplot commands may produce or close a figure; we need to reflect this!
        """
        # NOTE: 2019-11-20 12:22:17
        # self.workspaceModel.update() triggers the signal
        # WorkspaceModel.modelContentsChanged which is connected to the slot
        # self.slot_updateWorkspaceView(); in turn this will sort column 0
        # and resize its contents.
        # This is because workspaceModel doesn't "know" anything about workspaceView.
        
        self.workspaceModel.preExecute()
        self.workspaceModel.postRunCell(Bunch(success=True))
        
        # timer = QtCore.QTimer()
        # timer.timeout.connect(self.workspaceModel.update)
        # timer.start(0)

    @Slot()
    def slot_updateCwd(self):
        r"""Connected to console.executed signal
        Makes sure that a cd (change directory) command run at the console
        is reflected in throughout Scipyen.
        """
        # NOTE: 2025-02-13 14:32:40 WARNING
        # do NOT call slot_changeDirectory here -> circular loop!
        if self.cwd != os.getcwd():
            oldCwd = self.cwd
            newCwd = os.getcwd()
            self.cwd = newCwd
            # NOTE: 2025-02-13 14:38:57
            # update the navigator
            try:
                self.navPrevDir.appendleft(oldCwd)

            except:
                pass
            
            url = QtCore.QUrl(pathlib.Path(newCwd).absolute().as_uri())
            self.navigator.setLocationUrl(url)
            
            self._set_recentDirectory_(self.cwd)
            self._updateFileSystemView_(self.cwd, False)

    def slot_updateHistory(self):
        r""" Slot to update the history tree widget once a command has been entered at the console
        This occurs only for the current session
        """
        # NOTE: 2017-03-19 21:26:37 self.console.history_tail stores only the
        # NOTE: command line input to the console (interactive input)
        # NOTE: so it's OK to connect this to console's executed slot
        # NOTE: however pressing ENTER (and thus firing the executed signal)
        # NOTE: will only generate an empty string; in this case, the console's
        # NOTE: history_tail will how historic commands because nothing is appended
        # NOTE: to it -- we therefore must check that (1) the execution count is > 1
        # NOTE: and that is has been updated after the last ENTER press
        # print("execution count in slot_updateHistory: ", self.ipkernel.shell.execution_count)

        # only update history if something has indeed been executed
        if self.console is not None and self.ipkernel.shell.execution_count > self.executionCount:
            self.executionCount = self.ipkernel.shell.execution_count
            self._updateHistoryView_(self.executionCount-1, self.console.consoleWidget.history_tail(1)[0])
            # self._updateHistoryView_(self.executionCount-1, self.console.history_tail(1)[0])

    def _updateHistoryView_(self, lineno, val):
        font = self._defaultUIFont if self._useSystemDefaultFont else self._commandHistoryFont
        
        mustUpdateSessionID = self.currentSessionTreeWidgetItem.childCount() == 0

        item = QtWidgets.QTreeWidgetItem(
            self.currentSessionTreeWidgetItem, [repr(lineno), val])
        for col in range(item.columnCount()):
            item.setFont(col, font)

        self.historyTreeWidget.addTopLevelItem(item)
        self.historyTreeWidget.scrollToItem(item)
        self.historyTreeWidget.setCurrentItem(item)

        if mustUpdateSessionID:
            self.currentSessionID = self.historyAccessor.get_last_session_id()

    def removeWorkspaceSymbol(self, name: str):
        r"""Remove a binding from the workspace.

        Given 'name' a symbol bound to a variable in the workspace, this method
        removes that binding (and its representation in the "User Variables"
        tab of Scipyen's main window).

        Equivalent of removing that binding by calling `del` at the console.

        """
        # NOTE: 2023-05-28 00:13:40
        # With the current workspaceModel implementation since 2023-05-28 this
        # function appears redundant. However, it is not, as it allows code outside
        # the main Scipyen window to remove user data from the workspace.
        self.workspaceModel.unbindFromNamespace(name) # single-shot

    def removeFromWorkspace(self, value: typing.Any, by_name: bool = True):#, update: bool = True):
        r"""Removes an object from the workspace via Context menu Delete action.

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

        Named parameters:
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
        # NOTE: 2025-07-17 11:37:57 WARNING
        # Do NOT DELETE this method definition - this is called by subclasses of scipyenviewer for removing
        # themselves from workspace upon closing
        # FIXME might want to redesign so that it is not being called anymore
        # possibly redundant with self.removeWorkspaceSymbol
        if by_name:
            if isinstance(value, str):
                r = self.workspace.unbindFromNamespace(value) # one-shot
        else:
            objects = [(name, obj)
                       for (name, obj) in self.workspace.items() if obj is value]
            
            if len(objects):
                for o in objects:
                    self.workspaceModel.unbindFromNamespace(o[0])

        self.workspaceModel.currentItem = None

    @safewrapper
    def getCurrentVarName(self):
        signalBlockers = [QtCore.QSignalBlocker(self.workspaceView),
                          QtCore.QSignalBlocker(self.workspaceModel),
                          QtCore.QSignalBlocker(self.workspaceView.selectionModel())]

        varname = getattr(self, "currentVarItemName", None)

        if varname is None:
            indexList = self.workspaceView.selectedIndexes()

            if len(indexList) != 1:
                return

            item, varname = self._getWorkspaceVarItemAndName_(indexList[0])

            if varname is None or isinstance(varname, str) and len(varname.strip()) == 0:
                return

            if varname not in self.workspace.keys():
                return

        return varname

    def assignToWorkspace(self, name: str, val: object, check_name:bool = True) -> bool:
        r"""Binds a Python object to a symbol in the user workspace.
        
        Parameters:
        ----------
        name (str): the symbol whch will be bound to the object
        
        val (object): the object which will be bound to the symbol given by `name`
        
        check_name (bool): optional, default is True; checks if the symbol in 
            `name` already exists in the workspace, AND is bound to a user¹
            variable. If `name` is found, the function prompts the user to choose
            to rename, overwrite, or cancel.
        
            WARNING This does NOT apply to system (hidden) symbols, see below.
        
        Returns:
        -------
        True is assignment is successful, False otherwise.
        
        WARNING:
        
        If the symbol is already bound to a system variable² the function will 
        display a critical message and returns False.
        
        -----------
        NOTE: 
        
        ¹ User variables are symbol ↦ object bindings created during a Scipyen
        session and ARE visible in Scipyen's workspace viewer table (`User Variables`)
        
        ² System variables are symbol ↦ objects bindings in the workspace created
        during Scipyen's start up. These are generated by `import` statements
        (e.g. modules, functions, data variables) or loaded from data files.
        
        To avoid clutter, the system variables are HIDDEN from Scipyen's workspace 
        viewer table, but their symbols can be listed by running the command `dir()` 
        at Scipyen's console, which displays ALL the symbols present in the user 
        workspace at the time the `dir()` command is run.
        
    """
        if name in self.workspaceModel.user_ns_hidden.keys():
            t = type(self.workspaceModel.user_ns_hidden[name])
            self.criticalMessage("Assign in workspace", f"The name {name} would overwrite a system {t.__name__} variable.\n Please choose a different name!")
            return False
        
        if check_name is True:
            # validate name against existing user (visible) variables
            newVarNameOK = validate_varname(name, self.workspace)
            
            # if len(newVarNameOK) == 0:
            #     return
            
            if newVarNameOK != name:
                if __has_PyQt6__ or __has_PySide6__:
                    qbox = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Question,
                                                "Assign object in workspace",
                                                f"An object named '{name}' exists in the workspace.\nDo you wish to rename, overwrite or cancel?",
                                                # QtWidgets.QMessageBox.StandardButton(QtWidgets.QMessageBox.Cancel),
                                                QtWidgets.QMessageBox.Cancel,
                                                parent = self)
                else:
                    qbox = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Question,
                                                "Assign object in workspace",
                                                f"An object named '{name}' exists in the workspace.\nDo you wish to rename, overwrite or cancel?",
                                                QtWidgets.QMessageBox.StandardButtons(QtWidgets.QMessageBox.Cancel),
                                                parent = self)
                qbox.addButton("Rename", QtWidgets.QMessageBox.YesRole) # → returns 0
                qbox.addButton("Overwrite", QtWidgets.QMessageBox.AcceptRole) # → returns 1
                qbox.setDefaultButton(QtWidgets.QMessageBox.Cancel)
                
                btn = qbox.exec()
                
                if btn == 0: # ⇒ should rename
                    dlg = qd.QuickDialog(self, "Rename object")
                    dlg.addLabel(f"Rename {name}")
                    pw = qd.StringInput(dlg, "To :")
                    pw.variable.undoAvailable = True
                    pw.variable.redoAvailable = True
                    pw.variable.setClearButtonEnabled(True)
                    pw.setText(newVarNameOK)
                    dlg.addWidget(pw)
                    
                    if dlg.exec() == 0: # this is rejection ; we were asked to rename the object; if dlg is rejected then goodbyeif it d
                        return False
                    else:
                        name = pw.text()
                        
                elif btn != 1: # → 1 is OK to overwrite, anything else returns
                    return False
                
        self.workspaceModel.bindObjectInNamespace(name, val)
        
        return True

    @Slot()
    @safewrapper
    def slot_newViewer(self):
        r"""Slot for opening a list of viewer types (currently not used)
        """
        # viewer_type_names = [v.__name__ for v in gui_viewers]
        viewer_type_names = list(v.__name__ for v in self.viewers)
        dlg = ItemsListDialog(parent=self, itemsList=viewer_type_names,
                              title="Viewer type", modal=True)
        dlg.adjustSize()
        if dlg.exec() == 1:
            seltxt = dlg.selectedItemsText
            if len(seltxt) == 0:
                return

            selected_viewer_type_name = seltxt[0]

            win = self.newViewer(selected_viewer_type_name)  # , name=win_name)

    @Slot()
    @safewrapper
    def slot_newViewerMenuAction(self):
        r"""Slot for creating new viewer directly from Windows/Create New menu
        """
        win = self.newViewer(self.sender().text()
                             )  # inherited: WindowManager.newViewer

    @Slot(QtCore.QPoint)
    @safewrapper
    def slot_historyContextMenuRequest(self, point):
        cm = QtWidgets.QMenu("Selected history", self)
        executeHistorySelection = cm.addAction("Execute")
        executeHistorySelection.setToolTip("Execute selected lines")
        executeHistorySelection.triggered.connect(self._execHistorySelection_)
        historyToConsoleAction = cm.addAction("Send to console")
        historyToConsoleAction.setToolTip("Send code to Scipyen's console")
        historyToConsoleAction.triggered.connect(self._historyToConsole_)
        copyHistorySelection = cm.addAction("Copy")
        copyHistorySelection.setToolTip("Copy selected history to clipboard")
        copyHistorySelection.triggered.connect(self._copyHistorySelection_)
        saveHistorySelection = cm.addAction("Save...")
        saveHistorySelection.setToolTip("Save selected history to file")
        saveHistorySelection.triggered.connect(self._saveHistorySelection_)
        cm.popup(self.historyTreeWidget.mapToGlobal(point), copyHistorySelection)
        
    def _getHistoryTreeWidgetSessionCode_(self, item: QtWidgets.QTreeWidgetItem, /, 
                                asString:bool=True,
                                lineNumbers:bool=False,
                                withHeader:bool = False,
                                skipEmpty:bool=False):
        r"""Gets the line codes from a selected session in the history tree widget.
    This method does NOT access IPython history database.
    """
        sessionNo = int(item.text(0))
        sessionInfoText = item.text(1)
        getChildText = lambda c: (c.text(0), c.text(1)) if lineNumbers else c.text(1)
        ret = tuple(map(lambda k: getChildText(item.child(k)), range(item.childCount())))
        if len(ret) == 0 and skipEmpty:
            return tuple()
        
        if asString:
            ret = tuple(map(lambda t: f"{t[0]}: {t[1]}" if lineNumbers else f"{t}", ret))
            if withHeader:
                ret = (f"#\n# Session {sessionNo}: {sessionInfoText}\n#", ) + ret
                
        return ret
        
    def _getCodesForCurrentSession_(self, /, 
                                asString:bool=True, lineNumbers:bool=False,
                                withHeader:bool=False,
                                skipEmpty:bool=False) -> typing.Union[str, typing.Sequence[str]]:
        r"""Access 'Current' session in the historyTreeWidget"""
        items = tuple(filter(lambda i: i.text(0) == "Current", treeWidgetItems(self.historyTreeWidget)))
        
        if len(items) == 0:
            return tuple()
        
        currentSessionItem = items[0]
        
        getChildText = lambda c: (c.text(0), c.text(1)) if lineNumbers else c.text(1)
        
        ret = tuple(map(lambda k: getChildText(currentSessionItem.child(k)), range(currentSessionItem.childCount())))
        
        if len(ret) == 0 and skipEmpty:
            return tuple()
        
        if asString:
            ret = tuple(map(lambda t: f"{t[0]}: {t[1]}" if lineNumbers else f"{t}", ret))
            if withHeader:
                now = datetime.datetime.now()
                startDateTime = f"{now.date().isoformat()} {now.time().isoformat()}"
                
                ret = (f"#\n# Current session: {startDateTime} - \n#", ) + ret
        
        return ret
            
    def _getHistoryBlockAsCode_(self, magic:typing.Optional[str]=None, /, lineNumbers:bool = False,
                                skipEmptySessions:bool=False,
                                withHeader:bool=False,
                                suggestTitle:bool=False,
                                newLineAtEnd:bool=True) -> str:
        r"""Generates a string by concatenating commands from the history.
    Commands are selected in the Command History tree widget.
        
    Where there is NO selection, the entire IPython history is converted to a large
    string with session headers followed by command code lines in that session.
        
    The session headers contain the session number, start date & time, and the 
    stp date & time, and are commented. 
        
    The current session header contains the name "Current session" followed by
    the start date & time.
        
    Dates and times are in ISO format.

    The resulting string can be pasted directly into the console, or saved as a 
    python script file (*.py)
        
    Optionally, lines of code are adorned by line numbers (for publishing purposes).
        
    Optionally, empty sessions maye be skipped (i.e. sessions where no code was
    executed at the console).
        
    This method accesses the IPyton history database.
        
    Parameters:
    ==========
    magic: optional, a mime type magic string when the code is to be "exported"
        via drag and drop
        WARNING: code for this is NOT finalized yet 
        
    Keyword Parameters:
    ===================
    lineNumbers: default is False; when True, prepend the line number to each line
        of code. Line numbers start at 1 in every session
        
    skipEmptySessions: default is False; when True, empty sessions (including the 
        current one) will be skipped from the output
        
    Returns:
    ========
    A string, or a tuple of strings (code, proposed title) if `suggestTitle` is True
        
"""
        # TODO: 2025-04-30 11:49:34 FIXME
        # finalize the drag mime type and the use of magic - is it still needed?
        #
        # NOTE: 2025-04-30 11:39:37
        # magic is any mime 'magic' string to prepend to the selection list
        cmd = ""
        selectedItems = self.historyTreeWidget.selectedItems()

        if magic is None:
            selectionList = []
        else:
            selectionList = [magic]

        if len(selectedItems) == 0:
            ret = self._getFullHistoryAsCode_(magic, lineNumbers = lineNumbers,
                                              withHeader = withHeader,
                                              skipEmptySessions = skipEmptySessions,#
                                              newLineAtEnd = newLineAtEnd)
            
            if suggestTitle:
                ret = (ret, "Full Command History")
                
            return ret
        
        pastSessions = list() # cache past sesion infos
        
        if len(selectedItems) == 1: #  single item was selected
            if selectedItems[0].parent() is None:  # a session node was selected; returns
                if selectedItems[0].text(0) == "Current": # returns current session
                    # sessionNo = self.currentSessionID
                    
                    selectionList += list(self._getCodesForCurrentSession_(asString=True,
                                                                 lineNumbers = lineNumbers,
                                                                 withHeader = withHeader,
                                                                 skipEmpty = skipEmptySessions))
                    
                    if magic is None:
                        ret = "\n".join(selectionList)
                    else:
                        ret = " ".join(selectionList)
                        
                    if newLineAtEnd:
                        ret += "\n"
                        
                    if suggestTitle:
                        ret = (ret, "Current session")
                        
                    return ret
                    
                else: # returns selected session
                    # sessionNo = int(selectedItems[0].text(0))
                    selectionList += list(self._getHistoryTreeWidgetSessionCode_(selectedItems[0],
                                                                        asString=True,
                                                                        lineNumbers = lineNumbers,
                                                                        withHeader = withHeader,
                                                                        skipEmpty = skipEmptySessions))
                    if magic is None:
                        ret = "\n".join(selectionList)
                    else:
                        ret = " ".join(selectionList)
                        
                    if newLineAtEnd:
                        ret += "\n"
                        
                    if suggestTitle:
                        ret = (ret, f"Session {selectedItems[0].text(0)}")
                        
                    return ret
                    
            elif selectedItems[0].columnCount() > 1:  # a command node was selected
                #  check-out its parent session number
                if isinstance(selectedItems[0].parent(), QtWidgets.QTreeWidgetItem)\
                        and selectedItems[0].parent().text(0) == "Current":
                    sessionNo = self.currentSessionID

                else:
                    sessionNo = int(selectedItems[0].parent().text(0))
                    parent = selectedItems[0].parent()
                    sname = parent.text(0)
                    if sname not in pastSessions:
                        pastSessions.append(sname)
                        if withHeader:
                            ptxt = f"#\n#{sname}: {parent.text(1)}\n#"
                            selectionList.append(ptxt)
                    
                text = f"{selectedItems[0].text(0)}: {selectedItems[0].text(1)}" if lineNumbers else selectedItems[0].text(1)
                selectionList.append(text)
                
                if newLineAtEnd:
                    selectionList.append("\n")

            else:  # not sure we'll ever reach this
                return

            self.selectedSessionID = sessionNo

        else:
            # allow for items to be selected disjoint from their sessions
            # when selection crosses sessions

            # but leave selectedSessionID unchanged
            self.selectedSessionID = self.currentSessionID

            sessionNo = None
            
            for item in selectedItems:
                parent = item.parent()

                if parent is None:              # this is a session item
                    # do append session header for tractability
                    if withHeader:
                        # but only if requested
                        selectionList.append(f"#\n#{item.text(0)}: {item.text(1)}\n")
                    continue                    # move on to the next
                
                # and its parent is a session item
                ptxt = parent.text(0)
                if ptxt not in pastSessions:
                    if ptxt != "Current":
                        pastSessions.append(ptxt)
                        if withHeader:
                            selectionList.append(f"#\n#{ptxt}: {parent.text(1)}\n#")

                if ptxt != "Current":           # in fact a historic session item
                    sessionNo = int(ptxt)       # so get its session number

                else:
                    # make sure we get back to the curent session ID
                    sessionNo = self.currentSessionID

                lineNo = int(item.text(0))
                
                lineText = f"{lineNo}: {item.text(1)}" if lineNumbers else item.text(1)
                
                selectionList.append(lineText)

        if magic is None:
            cmd = "\n".join(selectionList)

        else:
            cmd = " ".join(selectionList)
            
        if newLineAtEnd:
            cmd += "\n"

        if suggestTitle:
            if len(pastSessions) == 1:
                return (cmd, f"Session {pastSessions[0]}")
            else:
                return (cmd, "Command History")
            
        return cmd

    def _copyHistorySelection_(self):
        cmd = self._getHistoryBlockAsCode_(suggestTitle=False, 
                                           newLineAtEnd=False)
        if isinstance(cmd, str) and len(cmd.strip()):
            if not cmd.endswith("\n"):
                cmd += "\n"
            self.app.clipboard().setText(cmd)

        else:
            self.app.clipboard().clear()  # don't leave gremlins
            
    def _getFullHistoryAsCode_(self,magic=None, /,  
                            lineNumbers:bool = False, 
                            withHeader:bool = False,
                            skipEmptySessions:bool=False,
                            newLineAtEnd:bool=True):
        r"""Outputs ALL command history resident in IPython's database.
    """
        hhs = self.historyAccessor.search('*')
        
        sessions_with_codes = tuple(hhs)
        
        ret = self.questionMessage("Save history", f"Save the entire history ({len(sessions_with_codes)} lines)?")
        
        if ret != QtWidgets.QMessageBox.Yes:
            return cmd 
        
        maxSession = max(map(lambda sc: sc[0], sessions_with_codes))
        
        codes = tuple(map(lambda s: self._getCodesForHistorySession_(sessions_with_codes, s, 
                                                                        withHeader=withHeader, 
                                                                        lineNumbers=lineNumbers,
                                                                        skipEmpty = skipEmptySessions), 
                            range(1,maxSession+1)))
        
        if skipEmptySessions:
            codes = tuple(filter(lambda c: len(c) > 0, codes))
        
        # append the current session
        current_code = self._getCodesForCurrentSession_(asString = True, 
                                                    lineNumbers = lineNumbers,
                                                    withHeader = withHeader,
                                                    skipEmpty = skipEmptySessions)
        if not (skipEmptySessions and len(current_code) == 0):
            codes += (current_code, )
        
        codes = itertools.chain.from_iterable(codes)
        
        if magic is None: # what is magic?
            cmd = "\n".join(codes)
        else:
            cmd = " ".join(codes) + " "
            
        if newLineAtEnd:
            cmd += "\n"
        
        return cmd

    def _historySessionInfo_(self, session:int, /, asString:bool=False) -> typing.Union[str, typing.Sequence[str]] | None:
        r"""Create a QTreeWidgetItem with session info.
        The QTreeWidgetItem is owned by self.historyTreeWidget.
        Alternatively, outputs a string for saving to file.
    
        WARNING: This method accesses the IPython history database
        """
        sessionInfo = self.historyAccessor.get_session_info(session)
        if sessionInfo is None: # this is / should be the current session
            sessionInfo = ("Current session", datetime.datetime.now(), None)
            # return "" if asString else list()
        
        if isinstance(sessionInfo[1], datetime.datetime):
            startDateTime = f"{sessionInfo[1].date().isoformat()} {sessionInfo[1].time().isoformat()}"
        else:
            startDateTime = ""

        if isinstance(sessionInfo[2], datetime.datetime):
            stopDateTime = f"{sessionInfo[2].date().isoformat()} {sessionInfo[2].time().isoformat()}"
        else:
            stopDateTime = ""

        sessionTimes = " "

        if len(startDateTime):
            sessionTimes = f"{startDateTime} - "
            if len(stopDateTime):
                sessionTimes = f"{startDateTime} - {stopDateTime}"

        elif len(stopDateTime):
            sessionTimes = f" - {stopDateTime}"

        sessionInfoText = f"{sessionInfo[0]}"
        
        if asString:
            return f"#\n# Session {sessionInfoText}: {sessionTimes}\n#"

        return [sessionInfoText, sessionTimes]
     
    def _historyLineInfo_(self, line:int, inline:str, /, 
                          asString:bool = False, lineNumbers:bool = True) -> typing.Union[str, list[str]]:
        r"""Returns the lines of code in a history session.
    
        WARNING: This method accesses the IPython history database.
    
    """
        if asString:
            if lineNumbers:
                return f"{line}: {inline}"
            else:
                return inline
            
        return [repr(line), inline]
    
    def _getCodesForHistorySession_(self, session_codes, session:int, /, 
                                    withHeader:bool=False,
                                    lineNumbers:bool=False,
                                    skipEmpty:bool=False) -> tuple[str]:
        r"""Merges session info and code lines for a sesion in history.
    
    Relies on session_codes created by accesing the IPython history database.
    """
        codes = tuple(map(lambda sc: self._historyLineInfo_(*sc[1:], asString=True, lineNumbers = lineNumbers),
                          filter(lambda sc: sc[0] == session, session_codes)))
        
        if len(codes) == 0 and skipEmpty:
            return tuple()
        
        if withHeader:
            sessionHeader = self._historySessionInfo_(session, asString=True)
            codes = (sessionHeader, ) + codes
                
        return codes
    
    @Slot()
    def _historyToConsole_(self):
        cmd, title = self._getHistoryBlockAsCode_(suggestTitle=True, skipEmptySessions=True,
                                                  withHeader=False, newLineAtEnd=False)
        if isinstance(cmd, str) and len(cmd.strip()):
            self.console.widget.writeText(cmd)
        
    @Slot()
    def _execHistorySelection_(self):
        cmd, title = self._getHistoryBlockAsCode_(suggestTitle=True, skipEmptySessions=True,
                                                  withHeader=False, newLineAtEnd=False)
        if isinstance(cmd, str) and len(cmd.strip()):
            self.statusBar().showMessage("Working...")
            currentMouseCursor = self.cursor()
            self.setCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
            try:
                # NOTE: 2025-09-26 21:44:21 
                # pasting a line or cell magic without the preceding '%' or '%%'
                # will NOT be interpreted as magic by consoleWidget.execute(…)
                # therefore I need to see if the first word in a line is a IPython magic name;
                # if it is, then prepend '%' or '%%' as appropriate
                #
                # the downside of this approach is that an identifier which HAPPENS 
                # to be the same as that of an IPython magic will always be interpreted
                # as a magic even at the command line (unless automagic is OFF)
                
                # A way to avoid this confusion is to turn automagic OFF in 
                # the console; however, this will only work for the commands 
                # added to history AFTER the turn off, and not before.
                #
                # The best way is to avoid using magic names as identifiers for
                # python objects
                
                # NOTE that I only do this when the code is executed directly; 
                # pasting it to the console first gives the opportunity to correct
                # by manually prepending '%' or '%%' as appropriate
                
                if self.shell.magics_manager.auto_magic:
                    cmd_lines = cmd.split("\n")
                    for k, cmd_line in enumerate(cmd_lines):
                        words = cmd_line.split(" ")
                        if words[0] in self.shell.magics_manager.magics["line"].keys():
                            words[0] = "%"+words[0]
                        elif words[0] in self.shell.magics_manager.magics["cell"].keys():
                            words[0] = "%%"+words[0]
                            
                        new_cmd_line = " ".join(words)
                        
                        cmd_lines[k] = new_cmd_line
                    cmd = "\n".join(cmd_lines)
                    
                self.console.consoleWidget.execute(cmd, hidden=False, interactive=False)
                
                self.executionCount = self.ipkernel.shell.execution_count
                self._updateHistoryView_(
                    self.executionCount-1, self.ipkernel.shell.history_manager.input_hist_raw[-1])
            except:
                traceback.print_exc()
                self.setCursor(currentMouseCursor)
                raise()
            self.statusBar().showMessage("Done!")
            self.setCursor(currentMouseCursor)
                    
    @Slot()
    def _saveHistorySelection_(self):
        # print(f"{self.__class__.__name__}._saveHistorySelection_")
        cmd, title = self._getHistoryBlockAsCode_(suggestTitle=True, skipEmptySessions=True,
                                                  withHeader=True)

        if isinstance(cmd, str) and len(cmd.strip()):
            fn, _ = self.chooseFile(caption="Save selected history to file",
                                    save=True,
                                    fileName=title,
                                    fileFilter="Python source code (*.py);;Text Files (*.txt);;All files (*.*)")#,
                                    # initialFilter="Python source code")
            if len(fn.strip()):
                pio.saveText(cmd+"\n", fn)
                # with open(fn, mode="wt") as destfile:
                
    def _slot_CommandFromHistory_received(self, cmd):
        if isinstance(cmd, str) and len(cmd.strip()):
            fn, _ = self.chooseFile(caption="Save selected history to file",
                                    save=True,
                                    fileName=title,
                                    fileFilter="Python source code (*.py);;Text Files (*.txt);;All files (*.*)")#,
                                    # initialFilter="Python source code")
            if len(fn.strip()):
                pio.saveText(cmd+"\n", fn)
        
    @Slot()
    def _slot_PythonHelp(self):
        # # from guiutils import testme
        from gui.pythonhelpwidget import PythonHelpWindow
        if not isinstance(self.pythonHelpWindow, QtWidgets.QMainWindow):
            self.pythonHelpWindow = PythonHelpWindow(shell=self.shell, parent=self)
        self.pythonHelpWindow.show()
        
    def runPythonHelpGUI(self, cmd:str):
        from gui.pythonhelpwidget import PythonHelpWindow
        if not isinstance(self.pythonHelpWindow, QtWidgets.QMainWindow):
            self.pythonHelpWindow = PythonHelpWindow(shell=self.shell, parent=self)
        self.pythonHelpWindow.show()
        self.pythonHelpWindow.help(cmd)
        

    @Slot(QtCore.QModelIndex)
    @safewrapper
    def slot_variableItemPressed(self, ndx):
        r"""Triggered by single-click of lmb in workspace viewer.
        """
        self.currentVarItem, self.currentVarItemName = self._getWorkspaceVarItemAndName_(
            ndx)
        try:
            obj = self.workspace[self.currentVarItemName]
            if isinstance(obj, (scipyenviewer.ScipyenViewer, mpl.figure.Figure)):
                self.setCurrentWindow(obj)
        except:
            pass

    @Slot(QtCore.QModelIndex)
    @safewrapper
    def slot_variableItemActivated(self, ndx):
        r"""Called by double-click of left mouse button on item in workspace
        """
        # headers = [k for k in standard_obj_summary_headers if k != "Icon"]
        source_ns = self.workspaceModel.item(
            ndx.row(), self._wspace_headers_.index("Workspace")).text()

        if source_ns != "Internal":  # avoid standard menu for data in remote kernels
            # TODO separate menu for variables in remote namespaces
            return # TODO 2025-06-24 22:17:01 FIXME -> copy variable to usr w'space or display in external console?

        self.currentVarItem, self.currentVarItemName = self._getWorkspaceVarItemAndName_(ndx)

        try:
            obj = self.workspace[self.currentVarItemName]

            if QtWidgets.QWidget in inspect.getmro(type(obj)):
                if isinstance(obj, QtWidgets.QMainWindow) and obj.isMinimized():
                    obj.showNormal()
                else:
                    obj.show()

            if isinstance(obj, (scipyenviewer.ScipyenViewer, mpl.figure.Figure)):
                self.raiseWindow(obj)

            else:
                askForParams = bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier)
                
                newWindow = bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.AltModifier)

                if not self.viewVar(self.currentVarItemName, newWindow=newWindow, 
                                    askForParams=askForParams):
                    # if no handler exists, then view (display) object in console
                    self.console.execute(self.currentVarItemName)
                    
        except:
            pass

    def _getWorkspaceVarItemAndName_(self, index: QtCore.QModelIndex):
        if index.column() == 0:
            item = self.workspaceModel.itemFromIndex(index)
        else:
            item = self.workspaceModel.item(index.row(), 0)

        varname = item.text()

        return item, varname

    def showVariable(self, name: str, newWindow: bool = True, viewerType=None):
        r"""Shows obj in a suitable new window
        """
        obj = self.workspace.get(name, None)
        if obj is None:
            self.console.execute(name)

        if QtWidgets.QWidget in inspect.getmro(type(obj)):
            obj.show()
            return

        if isinstance(obj, (scipyenviewer.ScipyenViewer, mpl.figure.Figure)):
            self.raiseWindow(obj)

        else:
            if not self.viewVar(name, newWindow=newWindow, winType=viewerType):
                # view (display) object in console is no handler exists
                self.console.execute(name)

    @safewrapper
    def _genExternalVarContextMenu(self, indexList, cm):
        if not cm.isEmpty():
            cm.addSeparator()
        copyVarToInternal = cm.addAction("Copy to Internal Workspace")
        copyVarToInternal.setToolTip(
            "Copies selected variable to the internal user workspace.\nCAUTION: Existing variables with the same name will be overwritten")
        copyVarToInternal.setStatusTip(
            "Copies selected variable to the internal user workspace.\nCAUTION: Existing variables with the same name will be overwritten")
        copyVarToInternal.setWhatsThis(
            "Copies selected variable to the internal user workspace.\nCAUTION: Existing variables with the same name will be overwritten")
        copyVarToInternal.triggered.connect(self._slot_copyFromExternalWS)

    @safewrapper
    def _genInternalVarContextMenu(self, indexList, cm):
        if not cm.isEmpty():
            cm.addSeparator()

        namestr = InflectEngine.plural('name', len(indexList))

        copyVarNames = cm.addAction(f"Copy {namestr}")
        copyVarNames.setToolTip(
            f"Copy variable {namestr} to clipboard.\nPress SHIFT to quote the {namestr}; press CTRL to have one name per line")
        copyVarNames.setStatusTip(
            f"Copy variable {namestr} to clipboard.\nPress SHIFT to quote the {namestr}; press CTRL to have one name per line")
        copyVarNames.setWhatsThis(
            f"Copy variable {namestr} to clipboard.\nPress SHIFT to quote the {namestr}; press CTRL to have one name per line")
        copyVarNames.triggered.connect(self.slot_copyWorkspaceSelection)
        copyVarNames.hovered.connect(self._slot_showActionStatusMessage_)

        varNamesToConsole = cm.addAction(f"Send {namestr} to console")
        varNamesToConsole.setToolTip(
            f"Copy & paste variable {namestr} directly to console.\nPress SHIFT to quote the {namestr}; press CTRL to have one name per line")
        varNamesToConsole.setStatusTip(
            f"Copy & paste variable {namestr} directly to console.\nPress SHIFT to quote the {namestr}; press CTRL to have one name per line")
        varNamesToConsole.setWhatsThis(
            f"Copy & paste variable {namestr} directly to console.\nPress SHIFT to quote the {namestr}; press CTRL to have one name per line")
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

            varName = self.workspaceModel.item(indexList[0].row(), 0).text()
            obj = self.workspace[varName]
            varType = type(obj)

            if QtWidgets.QWidget in inspect.getmro(varType):
                action = cm.addAction("Show")
                action.setToolTip("Show this viewer's window")
                action.setStatusTip("Show this viewer's window")
                action.setWhatsThis("Show this viewer's window")
                action.triggered.connect(obj.show)
                if isinstance(obj, scipyenviewer.ScipyenViewer):
                    close_action = cm.addAction("Close")
                    close_action.setToolTip(
                        "Closes this viewer's window then removes it from workspace")
                    close_action.setStatusTip(
                        "Closes this viewer's window then removes it from workspace")
                    close_action.setWhatsThis(
                        "Closes this viewer's window then removes it from workspace")
                    close_action.triggered.connect(obj.close)

                delVars = cm.addAction("Delete")
                delVars.setToolTip("Delete selected variables")
                delVars.setStatusTip("Delete selected variables")
                delVars.setWhatsThis("Delete selected variables")
                delVars.triggered.connect(self.slot_deleteSelectedWorkspaceObjects)
                delVars.hovered.connect(self._slot_showActionStatusMessage_)
                cm.addSeparator()
                clearWs = cm.addAction("Clear Workspace")
                clearWs.setToolTip(
                    "Remove all variables from the internal workspace")
                clearWs.setStatusTip(
                    "Remove all variables from the internal workspace")
                clearWs.setWhatsThis(
                    "Remove all variables from the internal workspace")
                clearWs.triggered.connect(self._slot_clearInternalWorkspace)
                clearWs.hovered.connect(self._slot_showActionStatusMessage_)
                return

            else:
                # handler_specs = VTH.get_handler_spec(varType)
                handler_specs = VTH.get_handler_spec(obj)
                if len(handler_specs):
                    specialViewMenu = cm.addMenu("View with")
                    for handler_spec in handler_specs:
                        action = specialViewMenu.addAction(handler_spec[1])
                        action.setToolTip(
                            f"View using {handler_spec[1]}; press {altKeyDescr} to use a new viewer window; press {ctrlKeyDescr} to prompt for configuration dialog ")
                        action.setStatusTip(
                            f"View using {handler_spec[1]}; press {altKeyDescr} to use a new viewer window; press {ctrlKeyDescr} to prompt for configuration dialog ")
                        action.setWhatsThis(
                            f"View using {handler_spec[1]}; press {altKeyDescr} to use a new viewer window; press {ctrlKeyDescr} to prompt for configuration dialog ")
                        action.triggered.connect(self.slot_autoSelectViewer)

                    if "DataViewer" not in [h[0].__name__ for h in handler_specs]:
                        act = specialViewMenu.addAction("DataViewer")
                        act.setToolTip(
                            f"View using generic DataViewer; press {altKeyDescr} to use a new viewer window; press {ctrlKeyDescr} to prompt for configuration dialog ")
                        act.setStatusTip(
                            f"View using generic DataViewer; press {altKeyDescr} to use a new viewer window; press {ctrlKeyDescr} to prompt for configuration dialog ")
                        act.setWhatsThis(
                            f"View using generic DataViewer; press {altKeyDescr} to use a new viewer window; press {ctrlKeyDescr} to prompt for configuration dialog ")
                        act.triggered.connect(self.slot_useDataViewer)

                else:
                    act1 = cm.addAction("Show in DataViewer")
                    act1.setToolTip(
                        f"View using generic DataViewer; press {altKeyDescr} to use a new viewer window; press {ctrlKeyDescr} to prompt for configuration dialog ")
                    act1.setStatusTip(
                        f"View using generic DataViewer; press {altKeyDescr} to use a new viewer window; press {ctrlKeyDescr} to prompt for configuration dialog ")
                    act1.setWhatsThis(
                        f"View using generic DataViewer; press {altKeyDescr} to use a new viewer window; press {ctrlKeyDescr} to prompt for configuration dialog ")
                    act1.triggered.connect(self.slot_useDataViewer)

        else:
            # several variables selected
            viewVars = cm.addAction("View")
            # always goes to new window
            viewVars.triggered.connect(self.slot_viewSelectedVariables)
            viewVars.setToolTip(
                f"Show variables in default viewer; press {altKeyDescr} to use a new viewer window; press {ctrlKeyDescr} to prompt for configuration dialog ")
            viewVars.setStatusTip(
                f"Show variables in default viewer; press {altKeyDescr} to use a new viewer window; press {ctrlKeyDescr} to prompt for configuration dialog ")
            viewVars.setWhatsThis(
                f"Show variables in default viewer; press {altKeyDescr} to use a new viewer window; press {ctrlKeyDescr} to prompt for configuration dialog ")
            viewVars.hovered.connect(self._slot_showActionStatusMessage_)

        viewInConsoleAction = cm.addAction("Display in console")
        viewInConsoleAction.setToolTip("Display variable(s) in console")
        viewInConsoleAction.setStatusTip("Display variable(s) in console")
        viewInConsoleAction.setWhatsThis("Display variable(s) in console")
        viewInConsoleAction.triggered.connect(
            self.slot_consoleDisplaySelectedVariables)
        viewInConsoleAction.hovered.connect(
            self._slot_showActionStatusMessage_)

        cm.addSeparator()

        varnames = [self.workspaceModel.item(
            indexList[k].row(), 0).text() for k in range(len(indexList))]

        pickleVars = cm.addAction("Save (pickle)")
        pickleVars.setToolTip("Save selected variables as Pickle files.\nWARNING: Do not use pickle for long-term data storage!")
        pickleVars.setStatusTip("Save selected variables as Pickle files.\nWARNING: Do not use pickle for long-term data storage!")
        pickleVars.setWhatsThis("Save selected variables as Pickle files.\nWARNING: Do not use pickle for long-term data storage!")
        pickleVars.triggered.connect(self.slot_pickleSelectedVariables)
        pickleVars.hovered.connect(self._slot_showActionStatusMessage_)

        saveVars = cm.addAction("Export as HDF5")
        saveVars.setToolTip("Export selected variables as HDF5 files")
        saveVars.setStatusTip("Export selected variables as HDF5 files")
        saveVars.setWhatsThis("Export selected variables as HDF5 files")
        saveVars.triggered.connect(self.slot_exportSelectedVariablesToHDF5)
        # saveVars.triggered.connect(self.slot_saveSelectedVariables)
        saveVars.hovered.connect(self._slot_showActionStatusMessage_)

        if all([isinstance(self.workspace[v], (pd.DataFrame, pd.Series, neo.basesignal.BaseSignal, neo.SpikeTrain, np.ndarray))] for v in varnames):
            if not any([isinstance(self.workspace[v], np.ndarray) and self.workspace[v].ndim > 2 for v in varnames]):
                exportCSVAction = cm.addAction(
                    "Export as CSV")
                exportCSVAction.triggered.connect(self.slot_multiExportToCsv)
                exportCSVAction.setToolTip(
                    "Export as comma-separated ASCII files")
                exportCSVAction.setStatusTip(
                    "Export as comma-separated ASCII file")
                exportCSVAction.setWhatsThis(
                    "Export as comma-separated ASCII file")
                exportCSVAction.hovered.connect(
                    self._slot_showActionStatusMessage_)
                
        if all([isinstance(self.workspace[v], str) for v in varnames]):
            exportTextAction = cm.addAction("Save as plain text file")
            exportTextAction.triggered.connect(self.slot_exportSelectedVariablesText)
            if all([strutils.is_html(self.workspace[v]) for v in varnames]):
                exportHTMLAction = cm.addAction("Save as HTML file")
                exportHTMLAction.triggered.connect(self.slot_exportSelectedVariablesAsHTML)
            elif all([strutils.is_svg(self.workspace[v]) for v in varnames]):
                exportXMLAction = cm.addAction("Save as SVG file")
                exportXMLAction.triggered.connect(self.slot_exportSelectedVariablesAsSVG)
            elif all([strutils.is_markdown(self.workspace[v]) for v in varnames]):
                exportXMLAction = cm.addAction("Save as Markdown file")
                exportXMLAction.triggered.connect(self.slot_exportSelectedVariablesAsMarkdown)
            elif all([strutils.is_ReST(self.workspace[v]) for v in varnames]):
                exportXMLAction = cm.addAction("Save as ReStructuredText file")
                exportXMLAction.triggered.connect(self.slot_exportSelectedVariablesAsReST)
            elif all([strutils.is_xml(self.workspace[v]) for v in varnames]):
                exportXMLAction = cm.addAction("Save as XML file")
                exportXMLAction.triggered.connect(self.slot_exportSelectedVariablesAsXML)

        delVars = cm.addAction("Delete")
        delVars.setToolTip("Delete selected variables")
        delVars.setStatusTip("Delete selected variables")
        delVars.setWhatsThis("Delete selected variables")
        delVars.triggered.connect(self.slot_deleteSelectedWorkspaceObjects)
        delVars.hovered.connect(self._slot_showActionStatusMessage_)

        if len(self.workspaceModel.foreign_namespaces) > 0 and self.external_console is not None:
            ns = self.external_console.window.find_tab_title(
                self.external_console.window.active_frontend)
            cm.addSeparator()
            copyVarToActiveExternalNamespace = cm.addAction(
                "Copy to %s namespace" % ns)
            copyVarToActiveExternalNamespace.setToolTip(
                "Copies selected variable to the namespace of the active external kernel namespace (currently %s)" % ns)
            copyVarToActiveExternalNamespace.setStatusTip(
                "Copies selected variable to the namespace of the active external kernel namespace (currently %s)" % ns)
            copyVarToActiveExternalNamespace.setWhatsThis(
                "Copies selected variable to the namespace of the active external kernel namespace (currently %s)" % ns)
            copyVarToActiveExternalNamespace.triggered.connect(
                self._slot_copyToExternalWS)

        cm.addSeparator()
        clearWs = cm.addAction("Clear Workspace")
        clearWs.setToolTip("Remove all variables from the internal workspace")
        clearWs.setStatusTip(
            "Remove all variables from the internal workspace")
        clearWs.setWhatsThis(
            "Remove all variables from the internal workspace")
        clearWs.triggered.connect(self._slot_clearInternalWorkspace)
        clearWs.hovered.connect(self._slot_showActionStatusMessage_)

    @Slot("QPoint")
    @safewrapper
    def slot_workspaceViewContextMenuRequest(self, point):
        r"""
        Contex menu requested by workspace viewer
        """
        indexList = self.workspaceView.selectedIndexes()

        if len(indexList) == 0:
            cm = QtWidgets.QMenu("Workspace", self)
            cm.setToolTipsVisible(True)
            clearWs = cm.addAction("Clear Workspace")
            clearWs.setToolTip(
                "Remove all variables from the internal workspace")
            clearWs.setStatusTip(
                "Remove all variables from the internal workspace")
            clearWs.setWhatsThis(
                "Remove all variables from the internal workspace")
            clearWs.triggered.connect(self._slot_clearInternalWorkspace)
            clearWs.hovered.connect(self._slot_showActionStatusMessage_)

            cm.popup(self.workspaceView.mapToGlobal(point))

            return

        # internal_var_indices = [ndx for ndx in indexList
        #                         if self.workspaceModel.item(ndx.row(), standard_obj_summary_headers.index("Workspace")).text() == "Internal"]
        internal_var_indices = [ndx for ndx in indexList
                                if self.workspaceModel.item(ndx.row(), self._wspace_headers_.index("Workspace")).text() == "Internal"]

        external_var_indices = [
            ndx for ndx in indexList if ndx not in internal_var_indices]

        cm = QtWidgets.QMenu("Selected variables", self)
        cm.setIcon(QtGui.QIcon.fromTheme("object"))
        cm.setToolTipsVisible(True)

        if len(internal_var_indices):
            self._genInternalVarContextMenu(internal_var_indices, cm)

        if len(external_var_indices):
            self._genExternalVarContextMenu(external_var_indices, cm)

        cm.popup(self.workspaceView.mapToGlobal(point))

    @Slot(QtCore.QItemSelection, QtCore.QItemSelection)
    @safewrapper
    def slot_selectionChanged(self, selected, deselected):
        r"""Selection change in the workspace viewer
        """
        if not selected.isEmpty():
            modelIndex = selected.indexes()[0]

            # source_ns = self.workspaceModel.item(
            #     modelIndex.row(), standard_obj_summary_headers.index("Workspace")).text()
            source_ns = self.workspaceModel.item(modelIndex.row(), self._wspace_headers_.index("Workspace")).text()
            if source_ns != "Internal":  # avoid standard menu for data in remote kernels
                # TODO separate menu for variables in remote namespaces
                return

            self.currentVarItem, self.currentVarItemName = self._getWorkspaceVarItemAndName_(
                modelIndex)
            obj = self.workspace[self.currentVarItemName]

        else:
            self.currentVarItemName = None
            self.currentVarItem = None

    @Slot("QStandardItem*")
    @safewrapper
    def slot_variableItemNameChanged(self, item):
        r"""Called when itemChanged was emitted by workspaceModel.
        Conected to workspace model `itemChanged` signal.

        Typically this is called after a variable has been renamed following an
        "Edit" key press (which on Unix/KDE and Windows is usually "F2").

        For the case when the variable name is changed via its context menu see 
        slot_renameWorkspaceVar().

        CAUTION: this is also called when variables are re-created!

        """
        # NOTE: 2025-07-06 14:59:01
        # workaround from this interfering with workspaceModel.updateRow() - signal temporarily disconnected inside workspaceModel.updateRowForVariable2
        item_data = f"'{item.data(QtCore.Qt.DisplayRole)}'"
        item_text = item.text()
        item_column = item.column()
        # print(f"{print_styled(f'{self.__class__.__name__}.slot_variableItemNameChanged(item: {item_data} with text: \'{item_text}\' in column {item_column})', color='green')}")
        signalBlockers = [QtCore.QSignalBlocker(self.workspaceView),
                          QtCore.QSignalBlocker(self.workspaceModel),
                          QtCore.QSignalBlocker(self.workspaceView.selectionModel())]

        if item.column() > 0:
            # only accept changes in the first (0th) column which contains
            # the variable name
            return

        originalVarName = self.getCurrentVarName()
        newVarName = item_text # item.text()

        # print(f"{print_styled(f'\n\toriginalVarname: {originalVarName}\n\tnewVarName: {newVarName}', color='green')}")
        # this is the new text (i.e. AFTER name change)
        if originalVarName is None:
            return

        if len(originalVarName.strip()) == 0:
            return
        
        if originalVarName == newVarName:
            return

        obj = self.workspace[originalVarName]

        varType = type(obj)

        if isinstance(varType, (scipyenviewer.ScipyenViewer, QtWidgets.QWidget)):
            start_counter = 0
        else:
            start_counter = 1

        varNames = list(self.workspace.keys())

        if newVarName in self.workspace:
            obj_ = self.workspace[newVarName] # what for ?!?

        if len(newVarName.strip()) == 0:  # prevent accidental deletion
            self.workspaceModel.itemChanged.disconnect(self.slot_variableItemNameChanged)
            item.setText(originalVarName)
            self.currentVarItem = item
            self.currentVarItemName = originalVarName
            self.workspaceModel.itemChanged.connect(self.slot_variableItemNameChanged)
            return

        if newVarName != originalVarName:
            if any(s in self.workspace for s in (originalVarName, newVarName)):
                data = self.workspace.pop(originalVarName, None)
                newVarName = validate_varname(
                    newVarName, self.workspace, start_counter=1)
                self.workspace[newVarName] = obj
                if isinstance(obj, (scipyenviewer.ScipyenViewer, QtWidgets.QWidget)):
                    obj.winTitle = newVarName
                item.setText(newVarName)
                self.workspaceModel.update()
                self.currentVarItem = item
                self.currentVarItemName = newVarName
                self.workspaceView.sortByColumn(0, QtCore.Qt.AscendingOrder)

    @Slot()
    @safewrapper
    def slot_renameWorkspaceVar(self):
        r""" Renames workspace variables through GUI Menu action.

        Called when "Rename" menu item is called from the context menu of an 
        workspace item.

        For the case when the variable name is changed through pressing system's 
        "rename" key (e.g., F2 in KDE) see slot_variableItemNameChanged()

        Presents a dialog prompting for a new variable name.
        """
        indexList = self.workspaceView.selectedIndexes()

        if len(indexList) != 1:
            return

        item, varName = self._getWorkspaceVarItemAndName_(indexList[0])

        # varName = self.workspaceModel.item(indexList[0].row(),0).text()

        dlg = qd.QuickDialog(self, "Rename variable")
        dlg.addLabel("Rename '%s'" % varName)
        pw = qd.StringInput(dlg, "To :")
        pw.variable.undoAvailable = True
        pw.variable.redoAvailable = True
        pw.variable.setClearButtonEnabled(True)
        pw.setText(varName)
        dlg.addWidget(pw)
        dlg.adjustSize()
        
        if dlg.exec() == 0:
            return

        newVarName = pw.text()

        if newVarName == varName:
            return

        newVarNameOK = validate_varname(newVarName, self.workspace)

        if newVarNameOK != newVarName:
            btn = QtWidgets.QMessageBox.question(
                self, "Rename variable", "Variable %s will be renamed to %s. Accept?" % (newVarName, newVarNameOK))

            if btn == QtWidgets.QMessageBox.No:
                return
            
        obj = self.workspace[varName]
        if isinstance(obj, (scipyenviewer.ScipyenViewer, QtWidgets.QWidget)):
            obj.winTitle = newVarName
            
        self.workspaceModel.rebindObjectInNamespace(varName, newVarNameOK)
        
    def saveSelectedVariables(self, saver:typing.Callable):
        indexList = self.workspaceView.selectedIndexes()
        if len(indexList) == 0:
            return
        varSet = set()
        for i in indexList:
            varSet.add(self.workspaceModel.item(i.row(), 0).text())
        varNames = sorted([n for n in varSet])
        self.setCursor(QtCore.Qt.WaitCursor)
        try:
            for n in varNames:
                if not isinstance(self.workspace[n], (QtWidgets.QWidget)):
                    saver(self.workspace[n], n)
            self.unsetCursor()
        except Exception as e:
            traceback.print_exc()
            self.unsetCursor()
        
    @Slot()
    def slot_exportSelectedVariablesToHDF5(self):
        self.saveSelectedVariables(pio.saveHDF5)

    @Slot()
    @safewrapper
    def slot_saveSelectedVariables(self):
        if bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier):
            saver = pio.saveHDF5
        else:
            saver = pio.savePickleFile
            
        self.saveSelectedVariables(saver)
        
    @Slot()
    @safewrapper
    def slot_pickleSelectedVariables(self):
        saver = pio.savePickleFile
        self.saveSelectedVariables(saver)

    @Slot()
    @safewrapper
    def slot_deleteSelectedWorkspaceObjects(self):
        r"""Removes objects from the workspace.
        Triggered by:
        • workspace viewer context menu Delete action.
        • keyvboard Delete shortcut (key sequence 'Delete')

        Variables are selected by their workspace names (symbols) using the 
        Workspace viewer GUI.
        """
        # print(f"{self.__class__.__name__}.slot_deleteSelectedWorkspaceObjects")
        indexList = self.workspaceView.selectedIndexes()

        if len(indexList) == 0:
            return
        
        # print(f"{self.__class__.__name__}.slot_deleteSelectedWorkspaceObjects {indexList}")
        
        
        msgBox = QtWidgets.QMessageBox()
        msgBox.setIcon(QtWidgets.QMessageBox.Warning)
        msgBox.setInformativeText("This operation cannot be undone!")
        msgBox.setStandardButtons(
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

        msgBox.setDefaultButton(QtWidgets.QMessageBox.No)
        
        if len(indexList) > 1:
            varNames = list()

            varSet = set((self.workspaceModel.getVarName(i) for i in indexList))

            varNames = sorted(varSet)

            prompt = "Delete %d selected variables?" % len(varSet)
            wintitle = "Delete variables"
            msgBox.setDetailedText("\n".join(varNames))
            
            msgBox.setWindowTitle(wintitle)
            msgBox.setText(prompt)
            
            self.retranslateUi(msgBox)

            ret = msgBox.exec()

            if ret == QtWidgets.QMessageBox.No:
                return

            # NOTE: 2023-05-30 18:08:26
            # remove stuff and update workspace model/viewer asynchronously: 
            # instead of calling workspaceModel.unbindFromNamespace, we:
            # 1) first, "remove" objects directly from the workspace (in reality
            # this unbinds the 'varName' symbol from the object it is bound to,
            # in the workspace; the objects still exist on the heapm but will hbe
            # garbage-collected when their reference count drops to zero);
            # 2) the call workspaceMode.update to reflect the changes in the 
            # workspace viewer; the unbound objects will be referenced in the
            # loop below (to check if they're GUI components) and possibly 
            # somewhere else; the reference(s) below go out of scope when this
            # function returns; when no other references exist (including somewhere
            # else) the arbage collector will destroy them
            #
            # It is important to check of the symbol of the o
            #
            
            windows = list(filter(lambda n: isinstance(self.workspace[n], QtWidgets.QMainWindow), varNames))
            for w in windows:
                obj = self.workspace[w]
                obj.close()
                self.deRegisterWindow(obj)
                
                
            figures = list(filter(lambda n: isinstance(self.workspace[n], mpl.figure.Figure), varNames))
            for f in figures:
                obj = self.workspace[f]
                if self.autoRemoveViewers and hasattr(f, "manager") or hasattr(f, "number"):
                    plt.close(obj)
                self.deRegisterWindow(obj)
                
            # for n in varNames:
            #     obj = self.workspace[n]
            #     if isinstance(obj, (QtWidgets.QMainWindow, mpl.figure.Figure)):
            #         if isinstance(obj, mpl.figure.Figure):
            #             # also removes obj.number from plt.get_fignums()
            #             if self.autoRemoveViewers and hasattr(obj, "manager") or hasattr(obj, "number"):
            #                 plt.close(obj)
            # 
            #         else:
            #             obj.close()
            # 
            #         # does not remove its symbol for workspace - this has already been removed by delete action
            #         self.deRegisterWindow(obj)

                # self.removeWorkspaceSymbol(n)
                
            self.workspaceModel.unbindFromNamespace(varNames)

            self.currentVarItem = None
            self.currentVarItemName = None

            # self.workspaceModel.update() # is this still required?
        else:
            varName = self.workspaceModel.getVarName(indexList[0])

            prompt = "Delete '%s'?" % varName
            wintitle = "Delete variable"
            msgBox.setWindowTitle(wintitle)
            msgBox.setText(prompt)

            ret = msgBox.exec()

            if ret == QtWidgets.QMessageBox.No:
                return
            
            obj = self.workspace[varName]
            
            if isinstance(obj, (QtWidgets.QMainWindow, mpl.figure.Figure)):
                if isinstance(obj, mpl.figure.Figure):
                    # also removes obj.number from plt.get_fignums()
                    plt.close(obj)

                else:
                    obj.close()

                # does not remove its symbol for workspace - this has already been removed by delete action
                self.deRegisterWindow(obj)
        
            self.workspaceModel.unbindFromNamespace(varName) # single shot


    @Slot(bool)
    @safewrapper
    def slot_dockWidgetVisibilityChanged(self, val):
        if val is True:
            self.activeDockWidget = self.sender()

    @Slot(QtWidgets.QDockWidget)
    @safewrapper
    def slot_dockWidgetActivated(self, w):
        self.activeDockWidget = w

    @Slot()
    @safewrapper
    def slot_copyWorkspaceSelection(self):
        # NOTE: check out keyboard modifier WHEN this slot is called
        indexList = [i for i in self.workspaceView.selectedIndexes()
                     if i.column() == 0]

        if len(indexList) == 0:
            return

        # wscol = standard_obj_summary_headers.index("Workspace")
        wscol = self._wspace_headers_.index("Workspace")

        if bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier):
            varnames = ["'%s'" % self.workspaceModel.item(i.row(), 0).text(
            ) for i in indexList if self.workspaceModel.item(i.row(), wscol).text() == "Internal"]

        else:
            varnames = [self.workspaceModel.item(i.row(), 0).text(
            ) for i in indexList if self.workspaceModel.item(i.row(), wscol).text() == "Internal"]

        if bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier):
            self.app.clipboard().setText(",\n".join(varnames))

        else:
            self.app.clipboard().setText(", ".join(varnames))

    @Slot()
    @safewrapper
    def slot_copyWorkspaceSelectionQuoted(self):
        r"""
        DEPRECATED
        """
        warnings.warn("DEPRECATED", DeprecationWarning)

        indexList = [i for i in self.workspaceView.selectedIndexes()
                     if i.column() == 0]
        if len(indexList) == 0:
            return

        # wscol = standard_obj_summary_headers.index("Workspace")
        wscol = self._wspace_headers_.index("Workspace")

        varNames = list()

        for i in indexList:
            if self.workspaceModel.item(i.row(), wscol).text() == "Internal":
                varNames.append("'%s'" %
                                self.workspaceModel.item(i.row(), 0).text())

        self.app.clipboard().setText(", ".join(varNames))

    @Slot()
    @safewrapper
    def slot_pasteHistorySelection(self):
        self._copyHistorySelection_()
        # by default this will paste the contents of the Cliboard, not the X11 selection
        self.console.paste()

    @Slot()
    @safewrapper
    def slot_pasteWorkspaceSelection(self):
        self.slot_copyWorkspaceSelection()
        self.console.paste()

    @Slot()
    @safewrapper
    def slot_pasteQuotedWorkspaceSelection(self):
        r"""
        DEPRECATED
        """
        warnings.warn("DEPRECATED", DeprecationWarning)

        self.slot_copyWorkspaceSelectionQuoted()
        self.console.paste()

    @Slot("QTreeWidgetItem*", int)
    @safewrapper
    def slot_historyItemSelected(self, item, col):
        r"""Triggered by selecting an item in the Command History list.
        Typically, this occurs after a single click on the item.
        """
        # only accept session items here (for now)
        # session items have parent None

        # print(item.text(0))
        if item.parent() is None:
            if col == 0:  # a session line selected
                if item.text(0) == "Current":
                    self.selectedSessionID = self.currentSessionID

                else:
                    self.selectedSessionID = int(item.text(0))

        else:  # a command line is selected
            if isinstance(item.parent().text(0), str):  # False if col1 selected
                if item.parent().text(0) == "Current":
                    self.selectedSessionID = self.currentSessionID

                else:
                    self.selectedSessionID = int(item.parent().text(0))

            else:
                self.selectedSessionID = self.currentSessionID

        # print("slot_historyItemSelected selected session", self.selectedSessionID)

    @Slot("QTreeWidgetItem*", int)
    @safewrapper
    def slot_historyItemActivated(self, item, col):
        r"""Triggered by activating an item in the Command History list.
        Typically, this occurs as a resuld of a double-click on the item.
        """
        # NOTE: 2017-03-19 22:54:55#
        # this DOES NOT re-create the output
        # NOTE: I guess I can live with this for now...

        # print("slot_historyItemActivated")
        parent = item.parent()
        sessionNo = self.currentSessionID

        # print(parent)

        if parent is None:                      # this is a session item
            return                              # we don't care about it

        # now, this IS a statement item and we care about it
        # its parent can only be a session item
        ptxt = parent.text(0)
        if ptxt != "Current":                   # maybe a historic session number
            # if so then get its session number
            sessionNo = int(parent.text(0))

        # get its line number (execution number)
        lineno = int(item.text(0))
        cmd = item.text(1)                # get its actual statement

        # print(cmd)

        backSession = self.currentSessionID - sessionNo

        currentMouseCursor = self.cursor()
        self.statusBar().showMessage("Working...")
        self.setCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        try:
            # TODO: explore constructing a command like %hist %rerun %recall line magics
            # TODO: I'd need to store the line number as well, somehow, in the history tree widget
            # TODO: in which case the history tree would have the items on 3 columns (session, line no, code)
            # TODO: and these would be executed by self.ipkernel.shell.run_line_magic('recall', ...)
            # NOTE: until then, we send the item's text to the shell by calling
            # NOTE: self.ipkernel.shell.run_cell(cmd, store_history=True, silent=False, shell_futures=True)
            # NOTE: see code comments in self.slot_initQtConsole()
            # self.ipkernel.shell.run_cell(
            #     cmd, store_history=True, silent=False, shell_futures=True)
            #
            # NOTE: 2025-05-05 17:26:15
            # Not sure about the above malarkey... What's wrong with this one below?
            self.console.consoleWidget.execute(cmd, hidden=False, interactive=False)
            # NOTE: 2017-03-19 21:15:48 while this DOES go to the ipython's history
            # NOTE: it DOES NOT go to the self.console.history_tail therefore calling the slot_updateHistory slot
            # NOTE: to avoid console.history and Scipyen's history going out of sync
            # NOTE: therefore I need to update Scipyen's history manually
            self.executionCount = self.ipkernel.shell.execution_count
            self._updateHistoryView_(
                self.executionCount-1, self.ipkernel.shell.history_manager.input_hist_raw[-1])
        except:
            traceback.print_exc()
            self.setCursor(currentMouseCursor)
            raise()
        self.statusBar().showMessage("Done!")
        self.setCursor(currentMouseCursor)
        # self.statusBar().clearMessage()

    @Slot()
    def slot_Quit(self):
        self.close()
            

    def closeEvent(self, evt):
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
        
        openWindows =list(filter(lambda x: isinstance(x, QtWidgets.QMainWindow) and x not in (self, self.console), 
                                 self.workspace.values()))
        
        for w in openWindows:
            w.close()

        # open_windows = ((name, obj) for (name, obj) in self.workspace.items() if isinstance(obj, QtWidgets.QWidget))
        # for win in open_windows:
        #     if win[1] is not self:
        #         win[1].close()

        # see NOTE: 2024-04-17 11:53:29 in scipyenviewer.py
        if sys.platform.startswith("win32") or os.getenv("XDG_SESSION_TYPE").lower() == "wayland":
            QtWidgets.QApplication.closeAllWindows()
        # QtWidgets.QApplication.closeAllWindows()
            
        evt.accept()

    def saveWindowSettings(self):
        gname, pfx = saveWindowSettings(
            self.qsettings, self, group_name=self.__class__.__name__)

    # @processtimefunc
    def loadSettings(self):
        r"""Overrides ScipyenConfigurable.loadSettings()"""
        super(WorkspaceGuiMixin, self).loadSettings()  # inherited from ScipyenConfigurable

    def loadWindowSettings(self):
        # print("%s.loadWindowSettings" % self.__class__.__name__)
        gname, prefix = loadWindowSettings(
            self.qsettings, self, group_name=self.__class__.__name__)

    # @processtimefunc
    def _configureUI_(self):
        ''' Collect file menu actions & submenus that are built in the UI file. This should be 
            done before loading the plugins.
        '''
        self.setupUi(self)
        # NOTE: 2021-04-15 10:12:33 TODO
        # allow user to choose app style interactively --

        # list of available syle names
        # NOTE: 2023-03-29 14:08:58 CT - selecting bb10 bright & dark styles crashes the GUI - not sure why
        self._available_Qt_style_names_ = [
            s for s in QtWidgets.QStyleFactory.keys() if not s.startswith("bb10")]

        # ### BEGIN Menus and actions
        #
        self.actionSet_Icon_Size.triggered.connect(self._slot_configureIconSize) # slot inherited from WorkspaceGuiMixin
        self.actionGUI_Style.triggered.connect(self._slot_set_Application_style)
        self.actionSet_user_plugins_directory.triggered.connect(self._slot_set_Users_Plugins_directory)
        self.actionFile_SystemIconSize.triggered.connect(self._slot_fileSystemIconSize)
        self.actionWorkspaceIconSize.triggered.connect(self._slot_workSpaceIconSize)
        # self.actionConfigure_external_HDF_viewer.triggered.connect(self._slot_set_ExternalHDF5Viewer)
        self.actionAuto_launch_Script_Manager.toggled.connect(self._slot_set_scriptManagerAutoLaunch)
        self.actionAuto_delete_viewer.triggered.connect(self._slot_setAutoRemoveViewers)
        
        self.actionUse_system_default_font.toggled.connect(self._slot_setUseDefaultFont)
        self.actionWorkplaceFont.triggered.connect(self._slot_chooseWorkplaceFont)
        self.actionCommandHistoryFont.triggered.connect(self._slot_chooseHistoryFont)
        
        # ### BEGIN scripts menu
        # NOTE: 2024-09-21 14:55:07
        # menuScripts is now def'ed in the ui file
        # self.menuScripts = QtWidgets.QMenu("Scripts", self)
        # self.menubar.insertMenu(self.menuHelp.menuAction(), self.menuScripts)
        self.actionScriptRun = QAction(QtGui.QIcon.fromTheme("system-run"), "Run...", self)
        self.actionScriptRun.triggered.connect(self.slot_runPythonScript)
        self.menuScripts.addAction(self.actionScriptRun)
        self.actionScriptToConsole = QAction(QtGui.QIcon.fromTheme("scriptnew"), "To Console...", self)
        self.actionScriptToConsole.triggered.connect(self.slot_pastePythonScript)
        self.menuScripts.addAction(self.actionScriptToConsole)
        self.menuScripts.addSeparator()
        self.recentScriptsMenu = QtWidgets.QMenu("Recent Scripts", self)
        self.recentScriptsMenu.setIcon(QtGui.QIcon.fromTheme("document-open-recent"))
        self.menuScripts.addMenu(self.recentScriptsMenu)
        self.menuScripts.addSeparator()
        self.actionManageScripts = QAction(QtGui.QIcon.fromTheme("scriptnew"), "Script Manager", self)
        self.actionManageScripts.triggered.connect(self.slot_showScriptsManagerWindow)
        self.menuScripts.addAction(self.actionManageScripts)
        # ### END scripts menu

        # ### BEGIN Applications menu
        # self.menuApplications = QtWidgets.QMenu("Applications", self) # NOTE: 2024-09-26 12:02:54 def'ed in the ui file
        self.menuApplications.setTearOffEnabled(True)
        self.menuApplications.setToolTipsVisible(True)
        self.menubar.insertMenu(self.menuHelp.menuAction(), self.menuApplications)
        # ### END   Applications menu
        
        # ### BEGIN Help menu
        # self.testPythonHelpAction = QAction(QtGui.QIcon.fromTheme("help-contextual"), "Python help", self)
        # self.testPythonHelpAction.triggered.connect(self._slot_PythonHelp)
        # self.menuHelp.addAction(self.testPythonHelpAction)
        self.actionPython_help.triggered.connect(self._slot_PythonHelp)
        
        self.whatsThisAction = QtWidgets.QWhatsThis.createAction(self)
        self.whatsThisAction.setIcon(QtGui.QIcon.fromTheme("help-whatsthis"))
        self.menuHelp.addSeparator()
        self.menuHelp.addAction(self.whatsThisAction)
        # ### END   Help menu
        
        self.actionQuit.triggered.connect(self.slot_Quit)
        
        self.actionOpen_System_Terminal.triggered.connect(self.slot_openCurrentDirInSystemTerminal)

        self.actionConsole = QAction(QtGui.QIcon.fromTheme("scriptnew"), "Scipyen Console", self)
        
        self.actionConsole.triggered.connect(self.slot_initQtConsole)
        self.menuConsoles.addAction(self.actionConsole)

        if not self._pyinstaller_bundled_:
            self.actionExternalIPython = QAction(QtGui.QIcon.fromTheme("scriptnew"), "External IPython", self)
        
            self.actionExternalIPython.triggered.connect(self.slot_launchExternalIPython)
        
            self.menuConsoles.addAction(self.actionExternalIPython)

            if has_neuron:
                self.actionExternalNrnIPython = QAction(
                    QtGui.QIcon.fromTheme("scriptnew"), "External IPython for NEURON", self)
                self.actionExternalNrnIPython.triggered.connect(
                    self.slot_launchExternalNeuronIPython)
                self.menuConsoles.addAction(self.actionExternalNrnIPython)

            self.menuWith_Running_Kernel = QtWidgets.QMenu("With Running Kernel", self)
            self.menuWith_Running_Kernel.setIcon(QtGui.QIcon.fromTheme("run-build"))
            
            self.menuConsoles.addMenu(self.menuWith_Running_Kernel)
            
            self.actionRunning_IPython = QAction(
                QtGui.QIcon.fromTheme("scriptnew"), "Choose kernel ...", self)
            
            self.actionRunning_IPython.triggered.connect(
                self.slot_launchExternalRunningIPython)
            
            self.menuWith_Running_Kernel.addAction(self.actionRunning_IPython)

            if has_neuron:
                self.actionRunning_IPython_for_Neuron = QAction(
                    QtGui.QIcon.fromTheme("scriptnew"), "Choose kernel and launch NEURON", self)
                
                self.actionRunning_IPython_for_Neuron.triggered.connect(
                    self.slot_launchExternalRunningIPythonNeuron)
                
                self.menuWith_Running_Kernel.addAction(
                    self.actionRunning_IPython_for_Neuron)

        # self.actionRestore_Workspace.triggered.connect(self.slot_restoreWorkspace)
        self.actionHelp_On_Console.triggered.connect(self._slot_helpOnConsole_)

        self.actionOpen.triggered.connect(self.slot_openFiles)
        self.actionView_Data.triggered.connect(self.slot_viewSelectedVar)
        self.actionDisplay_In_Console.triggered.connect(self.slot_consoleDisplaySelectedVariables)
        self.actionView_Data_New_Window.triggered.connect(self.slot_viewSelectedVarInNewWindow)
        self.actionReload_Plugins.triggered.connect(self.slot_reloadPlugins)
        self.actionSave.triggered.connect(self.slot_saveFile)
        self.actionChange_Working_Directory.triggered.connect(self.slot_selectWorkDir)
        # self.actionSave_pickle.triggered.connect(self.slot_saveSelectedVariables)

        # NOTE: 2017-07-07 22:14:40
        # Shortcut to delete selected items in workspaceView
        # thanks to QtCentre forum (J-P Nurmi)

        self.keyDeleteStuff = QShortcut(
            QtGui.QKeySequence(QtGui.QKeySequence.Delete), self)
        self.keyDeleteStuff.activated.connect(self.slot_keyDeleteStuff)

        # NOTE: File menu - some actions defined in mainwindow.ui
        self.actionImport_PrairieView_data.triggered.connect(self.slot_importPrairieView)
        self.recentFilesMenu = QtWidgets.QMenu("Open recent...", self)
        self.recentFilesMenu.setIcon(QtGui.QIcon.fromTheme("document-open-recent"))
        # self.menuFile.insertMenu(self.actionOpen, self.recentFilesMenu)
        self.menuFile.insertMenu(self.menuImport.menuAction(), self.recentFilesMenu)

        # NOTE: 2025-01-24 22:22:20 switch to UrlNavigatorMenu
        # self.recentDirectoriesMenu = QtWidgets.QMenu("Recent Working Directories", self)
        self.recentDirectoriesMenu = navigator.UrlNavigatorMenu("Recent Working Directories", self)
        self.recentDirectoriesMenu.mouseButtonClicked.connect(self.slot_recentDirActivated)
        # self.recentDirectoriesMenu.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.recentDirectoriesMenu.setIcon(QtGui.QIcon.fromTheme("folder-open-recent"))
        
        self.menuFile.insertMenu(self.actionReload_Plugins, self.recentDirectoriesMenu)
        self.menuFile.insertSeparator(self.actionReload_Plugins)

        self.menuFile.insertSeparator(self.actionQuit)
        
        self.actionAbout.triggered.connect(self._slot_about)
        self.actionAbout_Components.triggered.connect(self._slot_aboutComponents)
        self.actionAbout_Qt.triggered.connect(self._slot_about_qt)
        self.actionLicense.triggered.connect(self._slot_showLicense)
        
        # NOTE: 2016-05-02 12:22:21 -- refactoring plugin codes
        self.startPluginLoad.connect(self.slot_loadPlugins)
        
        self.sig_refreshRecentFilesMenu.connect(self._slot_refreshRecentFilesMenu_)


        self.newViewersMenu = QtWidgets.QMenu("New", self)
        self.newViewersMenu.setIcon(QtGui.QIcon.fromTheme("window-new"))
        self.newViewersMenu.setTearOffEnabled(True)
        self.newViewersMenu.setToolTipsVisible(True)
        self.newViewersMenu.addAction(QtGui.QIcon.fromTheme("window"),"Figure", lambda: self.newViewer(mpl.figure.Figure))
        self.menuViewers.addMenu(self.newViewersMenu)
        #
        # ### END   Menus and actions
        
        # ### BEGIN Toolbar
        #
        
        # add new viewers menu as toolbar action, too
        self.newViewersAction = self.toolBar.addAction(QtGui.QIcon.fromTheme("window-new"), "New Viewer")
        self.newViewersAction.setMenu(self.newViewersMenu)
        self.consolesAction = self.toolBar.addAction(QtGui.QIcon.fromTheme("akonadiconsole"), "Consoles")
        # this one is defined in the ui file mainwindow.ui
        self.consolesAction.setMenu(self.menuConsoles)
        self.scriptsAction = self.toolBar.addAction(QtGui.QIcon.fromTheme("dialog-scripts"), "Scripts")
        self.scriptsAction.setMenu(self.menuScripts)
        self.settingsAction = self.toolBar.addAction(QtGui.QIcon.fromTheme("settings-configure"), "Settings")
        self.settingsAction.setMenu(self.menuSettings)
        self.applicationsAction = self.toolBar.addAction(QtGui.QIcon.fromTheme("homerun"), "Applications")
        self.applicationsAction.setMenu(self.menuApplications)
        self.refreshViewAction = self.toolBar.addAction(QtGui.QIcon.fromTheme("view-refresh"), "Refresh Active View")
        self.refreshViewAction.triggered.connect(self.slot_refreshView)
        self.actionHide_Filtered_out_File_Names.setChecked(self._fileNamesFiltersHides_)
        self.actionHide_Filtered_out_File_Names.toggled.connect(self._slot_hideFilteredFileNames)
        self.hideFilteredOutnamesToolButton.setChecked(self._fileNamesFiltersHides_)
        self.hideFilteredOutnamesToolButton.toggled.connect(self._slot_hideFilteredFileNames)
        # NOTE: 2024-06-01 18:08:54
        # 'whats this' action should be the last action added to the toolbar
        self.helpTbAction = self.toolBar.addAction(QtGui.QIcon.fromTheme("help-contents"), "Help")
        self.helpTbAction.setMenu(self.menuHelp)
        # self.toolBar.addAction(self.whatsThisAction)

        tbactions = (self.newViewersAction, self.consolesAction,
                     self.scriptsAction, self.applicationsAction, 
                     self.helpTbAction, self.settingsAction)
        
        if __has_PyQt6__ or __has_PySide6__:
            tw = (w for w in itertools.chain(*(a.associatedObjects()
                for a in tbactions)) if w is not self.toolBar)
        else:
            tw = (w for w in itertools.chain(*(a.associatedWidgets()
                for a in tbactions)) if w is not self.toolBar)
            
        for w in tw:
            w.setPopupMode(QtWidgets.QToolButton.InstantPopup)
            
        if __has_PyQt6__ or __has_PySide6__:
            self.tbOpen = [w for w in self.actionOpen.associatedObjects() if isinstance(w, QtWidgets.QToolButton)][0]
        else:
            self.tbOpen = [w for w in self.actionOpen.associatedWidgets() if isinstance(w, QtWidgets.QToolButton)][0]
            
        self.tbOpen.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        self.tbOpen.setMenu(self.recentFilesMenu)
        
        if __has_PyQt6__ or __has_PySide6__:
            self.tbChDir = [w for w in self.actionChange_Working_Directory.associatedObjects() if isinstance(w, QtWidgets.QToolButton)][0]
        else:
            self.tbChDir = [w for w in self.actionChange_Working_Directory.associatedWidgets() if isinstance(w, QtWidgets.QToolButton)][0]

        self.tbChDir.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        self.tbChDir.setMenu(self.recentDirectoriesMenu)
        
        self.actionUse_Native_Menu_Bar.setChecked(self._useNativeMenuBar)
        self.actionUse_Native_Menu_Bar.toggled.connect(self._slot_useNativeMenuBar)
        
        self.actionUse_New_Navigator_Look.setChecked(self._newNavigatorLook_)
        self.actionUse_New_Navigator_Look.toggled.connect(self._slot_newNavigatorLook)
        
        self.actionUseShellAutomagic.toggled.connect(self._slot_UseShellAutomagic)

        self.lockToolBarAction = QAction(QtGui.QIcon.fromTheme("lock-symbolic"), "Lock Toolbar Positions", self)
        self.lockToolBarAction.setCheckable(True)
        self.lockToolBarAction.setChecked(self._lockedToolBar)
        self.lockToolBarAction.toggled[bool].connect(self._slot_changeToolBarLockedState)
        
        # ### BEGIN toolbar button style
        #
        self.toolBarToolButtonStyleActionGroup = QActionGroup(self)
        self.toolBarToolButtonStyleActionGroup.setExclusive(True)
        self.defaultToolBarToolButtonStyleAction = QAction("Default", self.toolBarToolButtonStyleActionGroup)
        self.iconsOnlyToolBarToolButtonStyleAction = QAction("Icons Only", self.toolBarToolButtonStyleActionGroup)
        self.textOnlyToolBarToolButtonStyleAction = QAction("Text Only", self.toolBarToolButtonStyleActionGroup)
        self.textAlongsideIconsToolBarToolButtonStyleAction = QAction("Text Alongside Icons", self.toolBarToolButtonStyleActionGroup)
        self.textUnderIconsToolBarToolButtonStyleAction = QAction("Text Under Icons", self.toolBarToolButtonStyleActionGroup)
        self.toolBarToolButtonStyleActionGroup.setEnabled(True)
        self.toolBarToolButtonStyleActionGroup.triggered[QAction].connect(self._slot_setToolBarToolButtonStyle)
        
        self.actionTool_Button_Style.triggered.connect(self._slot_configureToolButtonStyle)
        #
        # ### END   toolbar button style
        
        # ### BEGIN toolbar icon size
        #
        self.toolBarIconSizeActionGroup = QActionGroup(self)
        self.toolBarIconSizeActionGroup.setExclusive(True)
        self.defaultToolBarIconSizeAction = QAction("Default", self.toolBarIconSizeActionGroup)
        self.defaultToolBarIconSizeAction.setChecked(True)
        self.smallToolBarIconSizeAction = QAction("Small (16×16)", self.toolBarIconSizeActionGroup)
        self.mediumToolBarIconSizeAction = QAction("Medium (22×22)", self.toolBarIconSizeActionGroup)
        self.largeToolBarIconSizeAction = QAction("Large (32×32)", self.toolBarIconSizeActionGroup)
        self.hugeToolBarIconSizeAction = QAction("Huge (48×48)", self.toolBarIconSizeActionGroup)
        self.toolBarIconSizeActionGroup.setEnabled(True)
        self.toolBarIconSizeActionGroup.triggered[QAction].connect(self._slot_setToolBarIconSize)
        #
        # ### END   toolbar icon size
        
        #
        # ### END   Toolbar

        # BEGIN do not delete: action for presenting a list of viewer types to choose from
        # self.menuViewer.addSeparator()
        # self.actionNewViewer = self.menuViewer.addAction("New...")
        # self.actionNewViewer.triggered.connect(self.slot_newViewer)
        # END do not delete: action for presenting a list of viewer types to choose from


        # ### BEGIN Dock widgets and their children
        #
        self.setDockNestingEnabled(True)


        # ### BEGIN workspace view
        #
        
        self.workspaceView.setShowGrid(False)
        
        # ### BEGIN
        # NOTE: 2025-06-24 22:03:52
        # Next two lines henceforth called AFTER workspaceModel initialization, which is AFTER
        # self._init_QtConsole_, which now is AFTER self._configureUI_()
        # furthermore, workspaceView.selectionModel() REQUIRES the presence of a 
        # item model for the workspaceView
        # ### END
        # self.workspaceView.setModel(self.workspaceModel)
        # self.workspaceView.selectionModel().selectionChanged[QtCore.QItemSelection, QtCore.QItemSelection].connect(self.slot_selectionChanged)
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
        # TODO 2024-07-21 23:30:05
        # make this configurable (and locale-dependent?)
        self.workspaceView.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignLeft)

        # NOTE: 2025-06-24 22:09:00 see NOTE: 2025-06-24 22:03:52
        # self.workspaceModel.itemChanged.connect(self.slot_variableItemNameChanged)
        # self.workspaceModel.modelContentsChanged.connect(self.slot_updateWorkspaceView)
        
        self.copyVarnameToolBtn.clicked.connect(self.slot_copyWorkspaceSelection)
        self.sendVarnameToConsoleToolBtn.clicked.connect(self.slot_pasteWorkspaceSelection)
        self.renameVarnameToolBtn.clicked.connect(self.slot_renameWorkspaceVar)
        self.displayVariableToolBtn.setMenu(self.menuSelected_Image_or_Volume)
        self.saveVariableToolBtn.clicked.connect(self.slot_saveSelectedVariables)
        self.removeSelectedVarsToolBtn.clicked.connect(self.slot_deleteSelectedWorkspaceObjects)
        self.clearWorkspaceToolBtn.clicked.connect(self._slot_clearInternalWorkspace)
        # self.actionDisplay_In_Console.triggered.connect(self.slot_consoleDisplaySelectedVariables)
        
        self.dockWidgetWorkspace.visibilityChanged[bool].connect(
            self.slot_dockWidgetVisibilityChanged)

        # filter/select variable names combo
        self.varNameFilterFinderComboBox.lineEdit().setPlaceholderText("Select variable by expression e.g. 'data*' ...")
        self.varNameFilterFinderComboBox.currentTextChanged[str].connect(
            self.slot_filterSelectVarNames)

        self.varNameFilterFinderComboBox.lineEdit().returnPressed.connect(self.slot_addVarNameToFinderHistory)
        self.varNameFilterFinderComboBox.currentIndexChanged[int].connect(self.slot_filterSelectVarNamesIndexChanged)
        self.varNameFilterFinderComboBox.lineEdit().setClearButtonEnabled(True)
        self.varNameFilterFinderComboBox.lineEdit().undoAvailable = True
        self.varNameFilterFinderComboBox.lineEdit().redoAvailable = True

        self.removeVarNameFromFinderListAction = QAction(QtGui.QIcon.fromTheme("edit-delete"),
                                                                   "Remove item from list",
                                                                   self.varNameFilterFinderComboBox.lineEdit())

        self.removeVarNameFromFinderListAction.triggered.connect(
            self.slot_removeVarNameFromFinderHistory)

        self.varNameFilterFinderComboBox.lineEdit().addAction(self.removeVarNameFromFinderListAction,
                                                              QtWidgets.QLineEdit.TrailingPosition)
        #
        # ### END workspace view


        # ### BEGIN file system view,  navigation widgets & actions
        #
        
        # self.fileSystemTreeView.setUniformRowHeights(True) # set in the ui file
        self.fileSystemTreeView.setModel(self.fileSystemModel)
        self.fileSystemTreeView.setAlternatingRowColors(True)
        self.fileSystemTreeView.activated[QtCore.QModelIndex].connect(
            self.slot_fileSystemItemActivated)
        self.fileSystemTreeView.collapsed[QtCore.QModelIndex].connect(
            self.slot_resizeFileTreeViewFirstColumn)
        self.fileSystemTreeView.expanded[QtCore.QModelIndex].connect(
            self.slot_resizeFileTreeViewFirstColumn)
        self.fileSystemTreeView.customContextMenuRequested[QtCore.QPoint].connect(
            self.slot_fileSystemContextMenuRequest)
        self.fileSystemTreeView.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.fileSystemTreeView.setRootIsDecorated(True)
        self.fileSystemTreeView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)        
        # self.fileSystemTreeView.setHorizontalScrollBarPolicy(
        #     QtCore.Qt.ScrollBarAlwaysOn)        

        self.fileSystemModel.directoryLoaded[str].connect(self.slot_resizeFileTreeColumnForPath)
        
        self.fileSystemModel.rootPathChanged[str].connect(self.slot_rootPathChanged)
        
        self.fileSystemModel.dataChanged[QtCore.QModelIndex, QtCore.QModelIndex, "QVector<int>"].connect(self.slot_fileSystemDataChanged)

        self.dirFileMonitor = QtCore.QFileSystemWatcher(parent = self)
        self.dirFileMonitor.directoryChanged.connect(self._slot_monitoredDirectoryContentsChanged)
        # self.dirFileMonitor.fileChanged.connect(self._slot_monitoredFileChanged)
        
        self.navigator.urlChanged[QtCore.QUrl].connect(self.slot_chDirUrl)
        if sys.platform.startswith("win32"):
            target = os.environ['USERPROFILE']
        else:
            target = os.environ['HOME']
        self.navigator.setHomeUrl(QtCore.QUrl(pathlib.Path(target).as_uri()))
        self.navigator.newLook = self.useNewNavigatorLook
        # self.navigator.newWindowRequested.connect()

        self.fileSystemFilter.lineEdit().setClearButtonEnabled(True)
        self.fileSystemFilter.lineEdit().setPlaceholderText("Enter file name filter...")

        self.removeFileFilterFromListAction = QAction(QtGui.QIcon.fromTheme("edit-delete"),
                                                                "Remove this filter from history",
                                                                self.fileSystemFilter.lineEdit())

        self.removeFileFilterFromListAction.setToolTip("Remove this filter from history")

        self.removeFileFilterFromListAction.triggered.connect(self.slot_removeFileFilterFromHistory)

        self.clearFileFilterListAction = QAction(QtGui.QIcon.fromTheme("final_activity"),
                                                           "Clear filter list",
                                                           self.fileSystemFilter.lineEdit())

        self.clearFileFilterListAction.setToolTip("Clear file filter history")

        self.clearFileFilterListAction.triggered.connect(self.slot_clearFileFilterHistory)

        self.fileSystemFilter.lineEdit().addAction(self.removeFileFilterFromListAction,
                                                   QtWidgets.QLineEdit.TrailingPosition)

        self.fileSystemFilter.currentTextChanged[str].connect(self.slot_setFileNameFilter)

        self.dirHomeBtn.released.connect(self.slot_goToHomeDir)
        self.dirUpBtn.released.connect(self.slot_goToParentDir)
        self.dirBackBtn.released.connect(self.slot_goToPrevDir)
        self.dirFwdBtn.released.connect(self.slot_goToNextDir)
        # self.selDirBtn.released.connect(self.slot_selectDir)
        self.selDirBtn.released.connect(self.slot_selectWorkDir)
        self.selDirBtn.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        self.selDirBtn.setMenu(self.recentDirectoriesMenu)
        
        # NOTE: 2023-09-28 12:13:22
        self.openTermBtn.released.connect(self.slot_openCurrentDirInSystemTerminal)
        self.systemOpenFolderBtn.released.connect(self.slot_systemOpenCurrentFolder)
        self.systemOpenParentFolderBtn.released.connect(self.slot_systemOpenParentFolder2)
        
        self.toggleFilesFilterToolBtn.toggled.connect(self.slot_showFilesFilter)
        self.hideFilesFilterToolBtn.released.connect(self.slot_hideFilesFilter)


        # ### END   file system view,  navigation widgets & actions
        
        # ### BEGIN Command history
        #
        # ### BEGIN command history view
        #
        # NOTE: Upon launch it will get populated with Scipyen's history, during
        # the execution of self._init_QtConsole_()
        # So its resizeColumnToContents(0) method needs to be called once, in there.
        #
        # A new item (row) will be added with every statement executed at the 
        # console, REGARDLESS of whether the execution was succesful or not.
        #
        self.historyTreeWidget.setHeaderLabels(["Session & Line:", "Session Date & Time or Expression:"])
        self.historyTreeWidget.itemActivated[QtWidgets.QTreeWidgetItem, int].connect(self.slot_historyItemActivated)
        self.historyTreeWidget.customContextMenuRequested[QtCore.QPoint].connect(self.slot_historyContextMenuRequest)
        self.historyTreeWidget.itemClicked[QtWidgets.QTreeWidgetItem, int].connect(self.slot_historyItemSelected)
        self.historyTreeWidget.resizeColumnToContents(0)
        
        #
        # ### END command history view
        
        
        self.historyCommandsExecuteToolButton.clicked.connect(self._execHistorySelection_)
        self.historyCommandsToConsoleToolButton.clicked.connect(self._historyToConsole_)
        self.saveHistoryToolbutton.clicked.connect(self._saveHistorySelection_)
        self.copyHistoryCommands.clicked.connect(self._copyHistorySelection_)
        
        # ### BEGIN command history filters
        # filter/select commands from history combo
        #
        
        # self.commandHistoryFinderComboBox.currentTextChanged[str].connect(self.slot_findCommand) # heep this - will revisit
        self.commandHistoryFinderComboBox.currentIndexChanged[int].connect(self.slot_commandHistoryFinderIndexChanged)
        self.commandHistoryFinderComboBox.lineEdit().setPlaceholderText("Find expression ...")
        self.commandHistoryFinderComboBox.lineEdit().returnPressed.connect(self.slot_addCommandFindToHistory)
        self.commandHistoryFinderComboBox.lineEdit().setClearButtonEnabled(True)
        self.commandHistoryFinderComboBox.lineEdit().undoAvailable = True
        self.commandHistoryFinderComboBox.lineEdit().redoAvailable = True

        self.removeItemFromCommandFinderListAction = QAction(QtGui.QIcon.fromTheme("edit-delete"),
                                                                       "Remove item from list",
                                                                       self.commandHistoryFinderComboBox.lineEdit())

        self.removeItemFromCommandFinderListAction.triggered.connect(
            self.slot_removeItemFromCommandFinderHistory)
        
        self.useLastHistoryCommandSearchAction = QAction(QtGui.QIcon.fromTheme("document-open-recent"),
                                                         "Show Last Command Search at Startup",
                                                         self)
        self.menuSettings.addAction(self.useLastHistoryCommandSearchAction)
        
        self.useLastHistoryCommandSearchAction.setCheckable(True)
        self.useLastHistoryCommandSearchAction.setChecked(False)
        self.useLastHistoryCommandSearchAction.toggled.connect(self._slot_toggleUseLastHistoryCommandSearch)

        
        self.commandHistoryFinderComboBox.lineEdit().addAction(self.removeItemFromCommandFinderListAction,
                                                        QtWidgets.QLineEdit.TrailingPosition)
        #
        # ### END command history filters
        
        #
        # ### END   Command history

        # ### BEGIN console dock — NOT USED !
        #
        self.consoleDockWidget = QtWidgets.QDockWidget("Console", self, objectName="consoleDockWidget")
        self.consoleDockWidget.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)
        self.consoleDockWidget.setFeatures(QtWidgets.QDockWidget.DockWidgetMovable | QtWidgets.QDockWidget.DockWidgetFloatable)
        # self.consoleDockWidget.setFeatures(QtWidgets.QDockWidget.AllDockWidgetFeatures)# NOTE 2024-05-02 12:21:54 deprecated even in Qt 5 !!!
        self.consoleDockWidget.setVisible(False)
        
        #
        # ### END   console dock — NOT USED !
        
        #
        # ### END   Dock widgets  and their children

        # ### BEGIN miscellaneous
        #
        self.actionChoose_code_editor.triggered.connect(self._slot_chooseCodeEditor)
        self.actionUse_system_s_default_code_editor.triggered.connect(self._slot_setOverrideSystemEditor)

        self.activeDockWidget = self.dockWidgetWorkspace

        # NOTE: 2016-03-20 14:49:05
        # Quit the Qt app when Scipyen main window is closed
        self.app.destroyed.connect(self.slot_Quit)

        self.sig_windowRemoved.connect(self.slot_windowRemoved)
        
        self.setWindowTitle("Scipyen")
        # 
        # ### END   miscellaneous
 
        # NOTE: 2021-08-17 12:36:49 TODO custom icon ?
        # see also NOTE: 2021-08-17 10:06:24 in scipyen.py
        icon = QtGui.QIcon.fromTheme("pythonbackend")
        # self.setWindowIcon(icon) # this doesn't work? -- next line does
        QtWidgets.QApplication.setWindowIcon(icon)
        
        # NOTE: 2025-11-28 20:49:40
        # use QueuedConnection to eliminate flicker on recent directories menu 
        # after selecting a directory
        self.sig_changedDirectory.connect(self._slot_set_recentDirectory, type=QtCore.Qt.QueuedConnection)

    @Slot()
    @safewrapper
    def slot_keyDeleteStuff(self):
        if self.workspaceView.hasFocus():
            self.slot_deleteSelectedWorkspaceObjects()

    @Slot()
    @safewrapper
    def slot_goToHomeDir(self):
        self.navigator.goHome()
        
    @Slot()
    @safewrapper
    def slot_goToParentDir(self):
        self.navigator.goUp()

    @Slot()
    @safewrapper
    def slot_goToPrevDir(self):
        self.navigator.goBack()

    @Slot()
    @safewrapper
    def slot_goToNextDir(self):
        self.navigator.goForward()

    @Slot()
    @safewrapper
    def slot_systemOpenCurrentFolder(self):
        targetDir = self.fileSystemModel.rootPath()
        self.slot_systemOpenFileOrFolder(targetDir)
        
    @Slot()
    def _slot_launchSystemTerminal(self):
        dest = str(pathlib.Path(self.currentDir))
        terminal = desktoputils.get_system_terminal_executable()
        if sys.platform.startswith("win32"):
            subprocess.run(["start", terminal, "/k", "pushd", dest], shell=True)
        elif sys.platform.startswith("linux"):
            # subprocess.run(["xterm", "-e", "'cd", dest, "&&", "/bin/bash'"], shell=True)
            if terminal == "konsole":
                # subprocess.run([terminal, "--subprocess", "--workdir", dest], shell=True)
                subprocess.run([terminal, "--separate", "--workdir", dest, "&"], shell=True)
            elif terminal == "xterm":
                subprocess.run([terminal, "-e", "'cd", dest, "&&", "/bin/bash'"], shell=True)
            else:
                warnings.warn(f"Launching {terminal} is not yet supported")
                
        else:
            warnings.warn(f"Launching a terminal on {sys.platform} is not yet supported")
        
    @Slot()
    def _slot_createNewFolder(self):
        selectedItems = [item for item in self.fileSystemTreeView.selectedIndexes()
                         if item.column() == 0]
        if len(selectedItems) != 1:
            return
        item = selectedItems[0]
        # parent = item.parent()
        info = item.data(QtGui.QFileSystemModel.FileInfoRole)
        if not info.exists() or not info.isDir() or not info.isWritable():
            return
        
        folder = QtCore.QDir()
        
        folderName = "New folder"
        
        d = qd.QuickDialog(self, "Create New Folder")
        folderNameInput = qd.StringInput(d, "New folder name:")
        folderNameInput.setValue(folderName)
        
        
    @Slot()
    @safewrapper
    def slot_openCurrentDirInSystemTerminal(self):
        terminalLauncher = QtCore.QTimer(self)
        terminalLauncher.singleShot(0, self._slot_launchSystemTerminal)
        # terminalLauncher.setSingleShot(True)
        # terminalLauncher.timeout.connect(self._slot_launchSystemTerminal)
        terminalLauncher.deleteLater()
        
    @Slot()
    @safewrapper
    def slot_systemOpenSelectedFiles(self):
        r"""Opens selected file(s) or directory/ies in the system application"""
        selectedItems = [item for item in self.fileSystemTreeView.selectedIndexes()
                         if item.column() == 0]  # list of QModelIndex

        for item in selectedItems:
            self.slot_systemOpenFileOrFolder(
                self.fileSystemModel.filePath(item))

    @safewrapper
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
            self._recentFiles[item] = {"loader":loader, "timestamp": datetime.datetime.now()}
        else:
            recFNames = sorted(self._recentFiles.items(), key=lambda x: x[1]["timestamp"], reverse=True)

            if item not in recFNames:
                if len(self._recentFiles) == self._maxRecentFiles:
                    self._recentFiles.pop(recFNames[-1][0], None)

                self._recentFiles[item] = {"loader":loader, "timestamp":datetime.datetime.now()}

            elif self._recentFiles[item]["loader"] != loader:
                self._recentFiles[item]["loader"] = loader
                self._recentFiles[item]["timestamp"] = datetime.datetime.now()
                
            items = tuple(filter(lambda v: pathlib.Path(v[0]).exists(), sorted(self._recentFiles.items(), key = lambda x: x[1]["timestamp"], reverse=True)))
            self._recentFiles = self._recentFiles.__class__(items)
        # NOTE: 2023-05-27 23:50:19
        # This function may be called from another thread hence it cannot be
        # expected to modify the UI in self (which lives in the current thread)
        # Therefore the actual menu refresh has got to be done asynchronously in
        # the current thread, as opposed to the running thread which is executing
        # this function. Hence, I use the signal/slot mechanism.
        self.sig_refreshRecentFilesMenu.emit()

    @Slot()
    def _slot_refreshRecentFilesMenu_(self):
        '''Recreates the Recent Files submenu of the File menu; each recent file
        gets a QAction with the 'triggered' slot connected to self.slot_loadRecentFile.
        '''
        self.recentFilesMenu.clear()
        
        if len(self._recentFiles) > 0:
            if self._maxRecentFiles > 10:
                clearAction = self.recentFilesMenu.addAction(QtGui.QIcon.fromTheme("edit-clear-history"),
                    "Clear Recent Files List")
                clearAction.triggered.connect(self._clearRecentFiles_)
                self.recentFilesMenu.addSeparator()
                
            try:
                for item in self._recentFiles.keys():
                    itemName = pathlib.Path(item).name
                    itemText = f"{itemName} [{item}]"
                    action = self.recentFilesMenu.addAction(itemText)
                    action.triggered.connect(self.slot_loadRecentFile)
            except:
                traceback.print_exc()

            if self._maxRecentFiles <= 10:
                self.recentFilesMenu.addSeparator()
                clearAction = self.recentFilesMenu.addAction(QtGui.QIcon.fromTheme("edit-clear-history"),
                    "Clear Recent Files List")
                clearAction.triggered.connect(self._clearRecentFiles_)


    def _clearRecentFiles_(self):
        self._recentFiles.clear()
        self._slot_refreshRecentFilesMenu_()

    def _refreshRecentDirs_(self):
        self._refreshRecentDirectoriesMenu_()
        # self._refreshRecentDirsComboBox_()

    def _refreshRecentDirectoriesMenu_(self):
        self.recentDirectoriesMenu.clear()

        if len(self.recentDirectories) > 0:
            if self._maxRecentDirectories > 10:
                clearDirAction = self.recentDirectoriesMenu.addAction(QtGui.QIcon.fromTheme("edit-clear-history"),
                    "Clear Recent Directories List")
                clearDirAction.triggered.connect(self._clearRecentDirectories_)
                self.recentDirectoriesMenu.addSeparator()
                
            self._initRecentDirsMenu_(self.recentDirectoriesMenu, 0)
                
    def _initRecentDirsMenu_(self, menu: QtWidgets.QMenu, startIndex:int):
        from gui import guiutils
        menu.setLayoutDirection(QtCore.Qt.LeftToRight)
        maxIndex = startIndex + 30
        nDirs = len(self._recentDirectories)
        lastIndex = min(nDirs-1, maxIndex)
        
        dirsNames = list(self._recentDirectories)[startIndex : lastIndex]
        
        dirsActions = list(map(lambda x: QAction(guiutils.csqueeze(x.replace('&', '&&'), 60), self), dirsNames))
        for action in dirsActions:
            action.triggered.connect(self._slot_recentDirActionTriggered)

        if self.currentDirectory in dirsNames:
            currentIndex = dirsNames.index(self.currentDirectory)
            font = QtGui.QFont(dirsActions[currentIndex].font())
            font.setBold(True)
            dirsActions[currentIndex].setFont(font)
            
        for k,i in enumerate(range(startIndex, lastIndex)):
            dirsActions[k].setData(i)
            dirsActions[k].setText(dirsNames[k])
            # dirsActions[k].triggered.connect(self.slot_changeLocation)
            menu.addAction(dirsActions[k])
            
        if nDirs > maxIndex:
            menu.addSeparator()
            nextDirsMenu = navigator.UrlNavigatorMenu("More", menu)
            nextDirsMenu.mouseButtonClicked.connect(self.slot_recentDirActivated)
            self._initRecentDirsMenu_(nextDirsMenu, maxIndex)
            menu.addMenu(nextDirsMenu)
        
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

            if any([f not in self._recent_scripts_dict_.keys() for f in self._scriptManager_.scriptFileNames]) \
                    or any([f not in self._scriptManager_.scriptFileNames for f in self._recent_scripts_dict_.keys()]):
                self._scriptManager_.setData(self._recent_scripts_dict_)

        else:
            if len(self._scriptManager_.scriptFileNames):
                self._scriptManager_.clear()

    @safewrapper
    def dragEnterEvent(self, event):
        event.acceptProposedAction()
        event.accept()

    @safewrapper
    def dropEvent(self, event):
        self.statusbar.showMessage(
            "Load file or change directory. SHIFT to also change to file's parent directory")
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if __has_PyQt6__ or __has_PySide6__:
                self.slot_loadDroppedURLs(urls, event.modifiers() == QtCore.Qt.ShiftModifier, event.pos())
            else:
                self.slot_loadDroppedURLs(urls, event.keyboardModifiers() == QtCore.Qt.ShiftModifier, event.pos())

        event.accept()

        self.statusbar.clearMessage()
        
    @safewrapper
    def createPopupMenu(self) -> QtWidgets.QMenu:
        r"""Extend toolbar popup menu with style options"""
        menu = super().createPopupMenu()
        menu.addSection("Toolbar Settings")
        # text position
        textPositionMenu = menu.addMenu("Text Position")
        for action in [self.defaultToolBarToolButtonStyleAction,
                       self.iconsOnlyToolBarToolButtonStyleAction,
                       self.textOnlyToolBarToolButtonStyleAction,
                       self.textAlongsideIconsToolBarToolButtonStyleAction,
                       self.textUnderIconsToolBarToolButtonStyleAction]:
            textPositionMenu.addAction(action)
        # icon size
        iconSizeMenu = menu.addMenu("Icon Size")
        for action in [self.defaultToolBarIconSizeAction, self.smallToolBarIconSizeAction,
                       self.mediumToolBarIconSizeAction, self.largeToolBarIconSizeAction,
                       self.hugeToolBarIconSizeAction]:
            iconSizeMenu.addAction(action)
        menu.addAction(self.lockToolBarAction)
            
        return menu
        

    @Slot(object, bool, QtCore.QPoint)
    @safewrapper
    def slot_loadDroppedURLs(self, urls, chdirs, pos):
        # print(f"{self.__class__.__name__}.slot_loadDroppedURLs")
        if isinstance(urls, (tuple, list)) and all([isinstance(url, QtCore.QUrl) for url in urls]):
            if len(urls) == 1 and (urls[0].isRelative() or urls[0].isLocalFile()) and os.path.isfile(urls[0].path()):
                # check if this is a python source file
                mimeType = QtCore.QMimeDatabase().mimeTypeForFile(
                    QtCore.QFileInfo(urls[0].path()))

                if all([s in mimeType.name() for s in ("text", "python")]):
                    self.slot_handlePythonTextFile(urls[0].path(), pos)
                    return
                
            # NOTE: 2024-02-04 10:22:37
            # deal with directories first; when several are dropped just navigate 
            # to the most recent one.
            
            valid_urls = [u for u in urls if u.isValid() and (u.isRelative() or u.isLocalFile())]
            
            if len(valid_urls) == 0:
                scipywarn(f"{self.__class__.__name__}.slot_loadDroppedURLs: Remote URLs not yet supported") #, NotImplemented)
                
            url_dirs = [u.path() for u in valid_urls if os.path.isdir(u.path()) or (os.path.isfile(u.path()) and chdirs) ]
            
            target_dir = None
            
            if len(url_dirs):
                target_dir = url_dirs[-1]
                
            file_urls = [u for u in valid_urls if os.path.isfile(u.path())]
            file_paths = [u.path() for u in file_urls]
            self.loadFiles(file_paths, self._openSelectedFileItemsThreaded, updateUi=False)
            
            if target_dir and os.path.isdir(target_dir):
                url = QtCore.QUrl(pathlib.Path(target_dir).as_uri())
                self.navigator.setLocationUrl(url)
                self.navigator.urlChanged.emit(url)

    @Slot(QtCore.QPoint)
    @safewrapper
    def slot_fileSystemContextMenuRequest(self, point):
        r"""Pops up a context menu for the File System viewer.
        NOTE: The context menu only appears if the collection of selected items
        contains only items pointing to regular files.
    """
        cm = QtWidgets.QMenu("Selected Items", self)

        selectedItems = [item for item in self.fileSystemTreeView.selectedIndexes()
                         if item.column() == 0]  # list of QModelIndex

        action_0 = None
        create_new = None
        copy_action = None
        move_action = None
        trash_action = None
        remove_action = None
        rename_action = None
        open_link_target_action = None

        scripts = set()
        spreads = set()

        if len(selectedItems):
            fileNames = set([self.fileSystemModel.filePath(i)
                            for i in selectedItems])

            # print("fileNames", fileNames)

            if not all(pio.checkFileReadAccess(f) for f in fileNames):
                return
            
            openFileObjects = cm.addAction("Open")
            openFileObjects.triggered.connect(self.slot_openSelectedFileItems)

            # for f in fileNames:
            #     if pio.checkFileReadAccess(f):
            #         mime_file_type = pio.getMimeAndFileType(f)


            spreads = set([f for f in fileNames if pio.is_spreadsheet(f)])
            scripts = set([f for f in fileNames if pio.is_python_source(f)])

            if len(fileNames - spreads) == 0:
                importAsDataFrame = cm.addAction("Open as DataFrame")
                importAsDataFrame.triggered.connect(self.slot_importDataFrame)

            if len(fileNames - scripts) == 0:
                addToScriptManager = cm.addAction("Add to Script Manager")
                addToScriptManager.triggered.connect(
                    self._slot_cm_AddPythonScriptToManager)

            fileNamesToConsole = cm.addAction("Send Name(s) to Console")
            fileNamesToConsole.triggered.connect(self._sendFileNamesToConsole_)

            cm.addSeparator()
            openFilesInSystemApp = cm.addAction("Open With Default Application")
            openFilesInSystemApp.triggered.connect(self.slot_systemOpenSelectedFiles)

            action_0 = openFileObjects
            
        if len(selectedItems) == 1:
            item = selectedItems[0]
            info = item.data(QtGui.QFileSystemModel.FileInfoRole)
            cm.addSeparator()
            if info.exists() and info.isDir() and info.isWritable():
                createNewFolderAction = cm.addAction("Create New Folder")
                createNewFolderAction.triggered.connect(self._slot_createNewFolder)
                
            
            parent = item.parent()
            
            while self.fileSystemModel.rootPath() != self.fileSystemModel.filePath(parent):
                parent = parent.parent()
                
            rootItem = parent
            
            if self.fileSystemModel.permissions(item.parent()) & QtCore.QFileDevice.WriteOwner:
                pass
            
            
            
            # for f in fileNames:
                
            

        cm.addSeparator()
        openParentFolderInSystemApp = cm.addAction(
            "Open Parent Folder In File Manager")
        openParentFolderInSystemApp.triggered.connect(
            self.slot_systemOpenParentFolderForSelectedItems)

        openFolderInFileManager = cm.addAction(
            "Open This Folder In File Manager")
        openFolderInFileManager.triggered.connect(
            self.slot_systemOpenCurrentFolder)

        if action_0 is None:
            action_0 = openParentFolderInSystemApp

        cm.popup(self.fileSystemTreeView.mapToGlobal(point), action_0)

    @Slot()
    @safewrapper
    def slot_addVarNameToFinderHistory(self):
        varTxt = self.varNameFilterFinderComboBox.lineEdit().text()
        if len(varTxt.strip()) > 0 :
            if varTxt not in self._recentVariablesList:
                self._recentVariablesList.appendleft(varTxt)
            self._lastVariableFind = varTxt
            self.slot_filterSelectVarNames(varTxt)
            
    @Slot(int)
    def slot_filterSelectVarNamesIndexChanged(self, val:int):
        varTxt = self.varNameFilterFinderComboBox.itemText(val)
        if len(varTxt.strip()) > 0 :
            self._lastVariableFind = varTxt
            self.slot_filterSelectVarNames(varTxt)

    # NOTE: 2017-08-03 08:44:34
    # TODO/FIXME decide on the match; basically works with match2
    # TODO add to varname history and save/restore from configuration file
    # TODO: find a way to filter displayed variable names -- low pripriy as we don't
    # overpopulate the variable browser yet
    @Slot(str)
    @safewrapper
    def slot_filterSelectVarNames(self, val):
        r"""Select variables in workspace viewer, according to name filter.
        """
        if __has_PyQt6__ or __has_PySide6__:
            matchRegExFlag = QtCore.Qt.MatchRegularExpression
        else:
            matchRegExFlag = QtCore.Qt.MatchRegExp

        match = QtCore.Qt.MatchContains | \
            QtCore.Qt.MatchCaseSensitive | \
            QtCore.Qt.MatchWrap | \
            QtCore.Qt.MatchRecursive | \
            matchRegExFlag

        # BEGIN other matching options - dont work as well
        # match = QtCore.Qt.MatchContains | \
        # QtCore.Qt.MatchCaseSensitive | \
        # QtCore.Qt.MatchWildcard | \
        # QtCore.Qt.MatchWrap | \
        # QtCore.Qt.MatchRecursive

        # match = QtCore.Qt.MatchWildcard| \
        # QtCore.Qt.MatchCaseSensitive | \
        # QtCore.Qt.MatchWrap | \
        # QtCore.Qt.MatchRecursive

        # END other matching options - dont work as well

        itemList = self.workspaceModel.findItems(val, match)

        self.workspaceView.selectionModel().clearSelection()

        if len(itemList) > 0:
            for i in itemList:
                self.workspaceView.selectionModel().select(
                    i.index(), QtCore.QItemSelectionModel.Select)
                
            self.workspaceView.scrollTo(self.workspaceView.model().indexFromItem(itemList[-1]))

    @Slot()
    @safewrapper
    def slot_removeVarNameFromFinderHistory(self):
        currentNdx = self.varNameFilterFinderComboBox.currentIndex()
        varTxt = self.varNameFilterFinderComboBox.itemText(currentNdx)
        if varTxt in self._recentVariablesList:
            self._recentVariablesList.remove(varTxt)

        self.varNameFilterFinderComboBox.removeItem(currentNdx)
        self.varNameFilterFinderComboBox.lineEdit().setClearButtonEnabled(True)

    # NOTE: 2019-10-17 21:36:39
    # TODO: find a way to filter command display (grey out the ones NOT
    # filtered for) -- a higher priority than for slot_filterSelectVarNames ,since here
    # we have A LOT of commands in the history
    # TODO: if the above task is successfully completed, then also find
    # out how to filter or select by session number


    @Slot(int)
    def slot_commandHistoryFinderIndexChanged(self, val:int):
        cmdTxt = self.commandHistoryFinderComboBox.itemText(val)
        if len(cmdTxt.strip()) > 0:
            self.lastCommandFind = cmdTxt
            self.slot_findCommand(cmdTxt)
            
    @Slot(str)
    @safewrapper
    def slot_findCommand(self, val:str):
        r"""Finds command in the history tree based on glob search.

        TODO option to search in a selected session only

        FIXME: 2022-12-04 11:32:06 Too slow !!!!
        """
        from fnmatch import translate
        # FIXME TODO find across sessions
        # search in the selected session (click on session number)

        if len(val):
            p = re.compile(translate(val))

        else:
            p = None

        if p is None:
            return
        # selected_children = list()
        
        mostRecentItem = None

        original_selection_mode = self.historyTreeWidget.selectionMode()

        self.historyTreeWidget.setSelectionMode(
            QtWidgets.QAbstractItemView.MultiSelection)

        try:
            self.historyTreeWidget.reset()
            for k in range(self.historyTreeWidget.topLevelItemCount()):
                topLevelItem = self.historyTreeWidget.topLevelItem(k)

                childCount = topLevelItem.childCount()

                # for c in range(childCount):
                #     child = self.historyTreeWidget.topLevelItem(k).child(c)
                #     child.setSelected(False)

                items_text_list = list(zip(
                    *[(topLevelItem.child(k).text(0), topLevelItem.child(k).text(1)) for k in range(childCount)]))

                if len(items_text_list) == 2:
                    found_text = [s for s in filter(p.match, items_text_list[1])]

                    within_session_indices = [int(items_text_list[0][items_text_list[1].index(s)]) for s in found_text]

                    selected_children = [topLevelItem.child(k-1) for k in within_session_indices if topLevelItem.child(k-1) is not None]

                    if len(selected_children):
                        topLevelItem.setExpanded(True)
                        mostRecentItem = topLevelItem

                        for item in selected_children:
                            item.setSelected(True)
                            
                    else:
                        topLevelItem.setExpanded(False)

                else:
                    topLevelItem.setExpanded(False)

            # else:
            #     topLevelItem.setExpanded(False)

            self.historyTreeWidget.setSelectionMode(original_selection_mode)
            
            if mostRecentItem:
                self.historyTreeWidget.scrollToItem(mostRecentItem)

        except:
            self.historyTreeWidget.setSelectionMode(original_selection_mode)

    @Slot()
    @safewrapper
    def slot_addCommandFindToHistory(self):
        cmdTxt = self.commandHistoryFinderComboBox.lineEdit().text()
        if len(cmdTxt.strip()) > 0:
            if cmdTxt not in self._commandHistoryFinderList:
                self._commandHistoryFinderList.appendleft(cmdTxt)
            self.lastCommandFind = cmdTxt
            self.slot_findCommand(cmdTxt)

    @Slot()
    @safewrapper
    def slot_removeItemFromCommandFinderHistory(self):
        currentNdx = self.commandHistoryFinderComboBox.currentIndex()
        cmdTxt = self.commandHistoryFinderComboBox.itemText(currentNdx)
        if cmdTxt in self._commandHistoryFinderList:
            self._commandHistoryFinderList.remove(cmdTxt)

        self.commandHistoryFinderComboBox.removeItem(currentNdx)
        self.commandHistoryFinderComboBox.lineEdit().setClearButtonEnabled(True)

    # @Slot()
    # @safewrapper
    # def slot_removeDirFromHistory(self):
    #     signalBlocker = QtCore.QSignalBlocker(self.navigator)
    #     currentNdx = self.navigator.currentIndex()
    #     dirTxt = self.navigator.itemText(currentNdx)
    #     if dirTxt in self.recentDirectories:
    #         self.recentDirectories.remove(dirTxt)
    # 
    #     self.navigator.removeItem(currentNdx)
    #     self.navigator.lineEdit().setClearButtonEnabled(True)

    # @Slot()
    # @safewrapper
    # def slot_clearRecentDirList(self):
    #     signalBlocker = QtCore.QSignalBlocker(self.navigator)
    #     self._clearRecentDirectories_()
    #     self.navigator.clear()

    @Slot()
    @safewrapper
    def slot_removeFileFilterFromHistory(self):
        currentNdx = self.fileSystemFilter.currentIndex()
        filterTxt = self.fileSystemFilter.itemText(currentNdx)

        signalBlocker = QtCore.QSignalBlocker(self.fileSystemFilter)

        if filterTxt in self.fileSystemFilterHistory:
            self.fileSystemFilterHistory.remove(filterTxt)

        self.fileSystemFilter.removeItem(currentNdx)
        self.fileSystemFilter.lineEdit().setClearButtonEnabled(True)

    @Slot()
    @safewrapper
    def slot_clearFileFilterHistory(self):
        signalBlocker = QtCore.QSignalBlocker(self.fileSystemFilter)
        self.fileSystemFilterHistory.clear()
        self.fileSystemFilter.clear()
        self.fileSystemFilter.lineEdit().setClearButtonEnabled(True)

    @Slot(str)
    @safewrapper
    def slot_setFileNameFilter(self, val):
        if len(val) == 0:
            self.fileSystemModel.setNameFilters([])
            self.lastFileSystemFilter = ""
            if "" not in self.fileSystemFilterHistory:
                self.fileSystemFilterHistory.appendleft("")

        else:
            # print("file filter %s" % val)
            self.fileSystemModel.setNameFilters(val.split())

            # and len(self.fileSystemFilterHistory) < 10:
            if val not in self.fileSystemFilterHistory:
                self.fileSystemFilterHistory.appendleft(val)

            self.lastFileSystemFilter = val

    @Slot(QtCore.QModelIndex)
    @safewrapper
    def slot_resizeFileTreeViewFirstColumn(self, ndx):
        self._resizeFileColumn_()

    @Slot(str)
    @safewrapper
    def slot_resizeFileTreeColumnForPath(self, path):
        self._resizeFileColumn_()

    def _resizeFileColumn_(self):
        self.fileSystemTreeView.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff)
        self.fileSystemTreeView.resizeColumnToContents(0)
        self.fileSystemTreeView.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAsNeeded)
        # self.fileSystemTreeView.setHorizontalScrollBarPolicy(
        #     QtCore.Qt.ScrollBarAlwaysOn)

    def _resizeWorkspaceViewFirstColumn_(self):
        self.workspaceView.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff)
        self.workspaceView.resizeColumnToContents(0)
        self.workspaceView.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAsNeeded)

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
        self.workspaceView.sortByColumn(sortSection, sortOrder)
        self.workspaceView.setSortingEnabled(True)

    @Slot(QtCore.QModelIndex)
    @safewrapper
    def slot_fileSystemItemActivated(self, ndx):
        r""" 
        Triggered by double-click on an item in the file system tree view.
        Double-clicking an item in self.fileSystemTreeView emits the 'activated' 
        signal which is connected to this slot
        """
        if self.fileSystemModel.isDir(ndx):
            # if this is a directory then chdir to it
            path = pathlib.Path(self.fileSystemModel.filePath(ndx))
            if not path.is_dir():
                scipywarn(f"The path {print_styled(path, 'yellow')} does not exist. is it a mount point or a remote place?")
                return

            # print(f"{self.__class__.__name__}.slot_fileSystemItemActivated: path = {path}")
            url = QtCore.QUrl(path.as_uri())
            self.navigator.setLocationUrl(url)
            self.navigator.urlChanged.emit(url)

        else:
            self.loadFiles([self.fileSystemModel.filePath(ndx)], 
                           self._openSelectedFileItemsThreaded)
            
    @Slot(QtCore.QUrl)
    @safewrapper
    def slot_chDirUrl(self, val:QtCore.QUrl):
        # print(f"{self.__class__.__name__}.slot_chDirUrl({val})")
        path = desktoputils.urlToPath(val)
        s = path.as_posix()
        self.slot_chDirString(s)

    @Slot(str)
    @safewrapper
    def slot_chDirString(self, val):
        # print(f"{self.__class__.__name__}.slot_chDirString({val})")
        if "://" in val:
            protocol, target = val.split("://")
        else:
            target = val
        # print("ScipyenWindow.slot_chDirString: \nval = %s; \nprotocol = %s; \ntarget = %s" % (val, protocol, target))
        self.slot_changeDirectory(target)
        
    @Slot(QAction, QtCore.Qt.MouseButton)
    def slot_recentDirActivated(self, action:QAction, button:QtCore.Qt.MouseButton):
        r"""Used when recent directories menu is actioned from a tool button"""
        from gui import guiutils
        index = action.data() 
        # print(f"{self.__class__.__name__}.slot_recentDirActivated: index = {index}")
        if index < 0 or index >= len(self._recentDirectories):
            return
        path = pathlib.Path(self._recentDirectories[index]).absolute() #.resolve()   # the path to the subdirectory pointed to by the action
        self._recentDirectoryActioned(path)
                
    def _recentDirectoryActioned(self, path:pathlib.Path):
        if path.exists():
            url = QtCore.QUrl(path.as_uri())
            self.navigator.setLocationUrl(url)
            self.navigator.urlChanged.emit(url)
        else:
            p = pathlib.Path(path)
            while not p.exists():
                if p == p.parent:
                    break
                p = p.parent
            if p.exists():
                url = QtCore.QUrl(p.as_uri())
                self.navigator.setLocationUrl(url)
                self.navigator.urlChanged.emit(url)
            else:
                txt = p.as_posix()
                
                elided = guiutils.get_elided_text(f"Inaccessible directory: {txt}", self.width(), QtCore.Qt.ElideMiddle)
                self.statusBar().showMessage(elided)
                self.errorMessage("Navigation", f"Inaccessible recent directory:\n{txt}")
        

    @Slot()
    @safewrapper
    def slot_changeDirectory(self, targetDir:str=None):
        r"""Convergence for all directory navigation in ScipyenWindow"""
        # print(f"MainWindow.slot_changeDirectory(targetDir = {targetDir})")
        if targetDir is None:
            if isinstance(self.sender(), QAction):
                targetDir = str(self.sender().text())

        if isinstance(targetDir, str) and "&" in targetDir:
            # NOTE: 2017-03-04 16:08:17 because for whatever reason Qt also
            # returns the shortcut indicator character '&'
            targetDir = targetDir.replace('&', '')

        if targetDir is None or (isinstance(targetDir, str) and len(targetDir.strip()) == 0) or not os.path.exists(targetDir):
            targetDir = os.getenv(
                "USERPROFILE") if sys.platform.startswith("win32") else os.getenv("HOME")

        if targetDir is not None and targetDir != "" and os.path.exists(targetDir):
            if os.path.isfile(targetDir):
                targetDir = os.path.dirname(targetDir)

            try:
                self.navPrevDir.appendleft(os.getcwd())

            except:
                pass
            
            if sys.platform.startswith("win32"):
                targetDir = targetDir.replace("\\", "/")
                targetDir = rf"{targetDir}"

            if self.ipkernel is not None and self.shell is not None and self.console is not None:
                # print(''.join(["cd '", targetDir, "'"]))
                # if sys.platform.startswith("linux"):
                # self.console.execute(''.join(["cd '", targetDir, "'"]), hidden=True)
                # else:
                # self.console.execute(''.join(["os.chdir('", targetDir, "')"]), hidden=False)

                self.console.execute(
                    ''.join(["os.chdir('", targetDir, "')"]), hidden=True)

            if self.external_console:
                self.external_console.execute("".join(["os.chdir('", targetDir, "')"]))

            self._updateFileSystemView_(targetDir, True)
            self.currentDirectory = targetDir
            mpl.rcParams["savefig.directory"] = targetDir
            self.setWindowTitle("Scipyen %s" % targetDir)

            self.sig_changedDirectory.emit(targetDir)

    def _slot_workdirChangedInConsole(self, targetDir):
        self._updateFileSystemView_(targetDir, cd=True)

    def _updateFileSystemView_(self, targetDir, cd=True):
        if self.fileSystemModel.rootPath() == targetDir:
            return
        self.fileSystemModel.setRootPath(targetDir)
        self.fileSystemTreeView.scrollTo(self.fileSystemModel.index(targetDir))
        if cd:
            self.fileSystemTreeView.setRootIndex(
                self.fileSystemModel.index(targetDir))
        else:
            self.fileSystemTreeView.setCurrentIndex(
                self.fileSystemModel.index(targetDir))
        self.fileSystemTreeView.sortByColumn(0, QtCore.Qt.AscendingOrder)
        # NOTE 2017-07-04 15:59:38
        # for this to work one has to set horizontalScrollBarPolicy
        # to ScrollBarAlwaysOff (e.g in QtDesigner)
        self._resizeFileColumn_()
        
    @Slot(str)
    def _slot_set_recentDirectory(self, targetDir:str):
        self._set_recentDirectory_(targetDir)
        
    @Slot()
    def _slot_recentDirActionTriggered(self):
        r"""Needed for recent directory action in recent directories menu when 
        shown as a submenu of File menu"""
        action = self.sender()
        index = action.data() 
        # print(f"{self.__class__.__name__}._slot_recentDirActionTriggered: index = {index}")
        if index < 0 or index >= len(self._recentDirectories):
            return
        path = pathlib.Path(self._recentDirectories[index]).absolute() #.resolve()   # the path to the subdirectory pointed to by the action
        self._recentDirectoryActioned(path)
        

    @safewrapper
    def _set_recentDirectory_(self, newDir):
        if newDir in self.recentDirectories:
            # move newDir to top of stack
            if newDir != self.recentDirectories[0]:
                self.recentDirectories.remove(newDir)
                self.recentDirectories.appendleft(newDir)
                # self._refreshRecentDirs_()

        else:
            # add Newdir,
            if len(self.recentDirectories) > self._maxRecentDirectories:
                self.recentDirectories.pop()

            self.recentDirectories.appendleft(newDir)

        self._refreshRecentDirs_()

    @safewrapper
    def _sendFileNamesToConsole_(self, *args):
        # print(args)
        selectedItems = [item for item in self.fileSystemTreeView.selectedIndexes(
        ) if not self.fileSystemModel.isDir(item)]  # list of QModelIndex

        nItems = len(selectedItems)
        if nItems == 0:
            return

        itemNames = [
            '"'+self.fileSystemModel.filePath(item)+'"' for item in selectedItems]

        self.app.clipboard().setText(',\n'.join(itemNames))
        self.console.paste()

    @Slot()
    @safewrapper
    def slot_importPrairieView(self):
        # from systems.PrairieView import PrairieViewImporter # PrairieView already imported as module
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

    @Slot(int)
    @safewrapper
    def _slot_prairieViewImportGuiDone(self, value):
        # TODO 2025-03-10 17:47:21 
        # move to a PV loader in systems, an out of ScipyenWindow code
        # if value == QtWidgets.QDialog.Accepted:
        if value:
            dlg = self.sender()
            if dlg is not None:
                self.assignToWorkspace(dlg.scanDataVarName, dlg.scandata)

    @Slot()
    @safewrapper
    def slot_importDataFrame(self):
        selectedItems = [item for item in self.fileSystemTreeView.selectedIndexes()
                         if item.column() == 0 and not self.fileSystemModel.isDir(item)]  # list of QModelIndex

        if len(selectedItems) == 0:
            return

        fileNames = [self.fileSystemModel.filePath(i) for i in selectedItems]
        
        self.loadFiles(fileNames, self._openSelectedFileItemsThreaded,
                       ioReaderFn = pio.importDataFrame)

    @Slot()
    @safewrapper
    def slot_openSelectedFileItems(self):
        r"""Opens files via (triggered from) context menu in File system browser"""
        selectedItems = [self.fileSystemModel.filePath(item) for item in self.fileSystemTreeView.selectedIndexes()
                         if item.column() == 0 and not self.fileSystemModel.isDir(item)]  # list of QModelIndex

        nItems = len(selectedItems)

        if nItems == 0:
            return False
        
        # NOTE: 2023-07-12 11:52:30
        # self.loadFiles is inherited from WorkspaceGuiMixin
        # creates a pgui.LoopWorkerThread that runs a file loading loop 
        # in a separate thread. The actual file loading loop is executed by 
        # self._openSelectedFileItemsThreaded. 
        #
        # In turn, self._openSelectedFileItemsThreaded calls self.loadDiskFile
        # on each file in the selectedItems
        #
        # The WorkspaceView is populated with the object created as a result of
        # self.loadDiskFile(…), depending on the value of the updateUi parameter
        # below, either:
        # • after each file has been read (updateUi = True):
        #   Data is placed in the workspace via the method workspaceModel.bindObjectInNamespace();
        #   This will trigger an update of the workspaceModel for each iteration
        #   of the loop - the PROBLEM is that the iteration speed slows down with
        #   the number of files (number of iterations) - because the execution
        #   time scales UP with the number of items in the workspace
        #
        # • after the worker thread that runs the loop has emitted a signal_Result
        #   Data is placed DIRECTLY in the workspace ⇒ this is faster, but needs 
        #   a separate post-hoc update to the workspaceModel; 
        #   NOTE: as of 2023-05-29 23:12:25 this does NOT block the UI anymore
        #   and the whole process is now more swift
        #

        # NOTE: 2023-07-12 11:40:44
        # Now THIS works like a charm...
        # NOTE: 2023-07-12 11:50:19
        # this below using updateUi=False <feels> faster
        # NOTE: 2023-10-02 10:51:01
        # self.loadFiles defined in WorkspaceGuiMixin (inherited by this class)
        # which then calls self._openSelectedFileItemsThreaded in a separate 
        # GUI thread.
        # print(f"{self.__class__.__name__}.slot_openSelectedFileItems")
        self.loadFiles(selectedItems, 
                       self._openSelectedFileItemsThreaded, updateUi=False)
        # self.loadFiles(selectedItems, 
        #                self._openSelectedFileItemsThreaded, updateUi=True)
        
        return True
        
    @safewrapper
    def _saveSelectedObjectsThreaded(self, saveFn: typing.Callable):
        # TODO: replicate the logic in _openSelectedFileItemsThreaded
        # click into pickling etc.
        pass

    @safewrapper
    def _openSelectedFileItemsThreaded(self, **kwargs):
        r"""
        Pass this as fileLoaderFn argument to self.loadFiles inherited from WorkspaceGuiMixin.
        """
        # print(f"{self.__class__.__name__}._openSelectedFileItemsThreaded called")
        filePaths = kwargs.pop("filePaths", None)
        
        if not isinstance(filePaths, (tuple, list)) or len(filePaths) == 0: 
            return
        
        loopControl = kwargs.pop("loopControl", None)
        progressSignal = kwargs.pop("progressSignal", None)
        # print(f"{self.__class__.__name__}._openSelectedFileItemsThreaded progressSignal = {progressSignal}")
        # finishedSignal = kwargs.pop("finishedSignal", None)
        # resultSignal = kwargs.pop("resultSignal", None)
        # print(f"{self.__class__.__name__}._openSelectedFileItemsThreaded resultSignal = {resultSignal}")
        canceledSignal = kwargs.pop("canceledSignal", None)
        ioReader = kwargs.pop("ioReader", None)
        separateWorkspaceViewUpdate = kwargs.pop("updateAfter", False) == True
        updateUi = kwargs.pop("updateUi", True)
        
        if not isinstance(ioReader, typing.Callable):
            ioReader=None
        
        addToRecent = len(filePaths) == 1
        
        OK = True
        
        # self.updateUiWithFileLoad is def'ed in WorkspaceGuiMixin
        self.updateUiWithFileLoad = updateUi 
        
        canceled = False
        
        for k, item in enumerate(filePaths):
            # print(f"{self.__class__.__name__}._openSelectedFileItemsThreaded ({k}, {item})")
            try:
                OK &= self.loadDiskFile(item, fileReader=ioReader, addToRecent=addToRecent, 
                                        updateUi=updateUi) # places the loaded data DIRECTLY into self.workspace
                
                if OK and isinstance(progressSignal, QtCore.SignalInstance):
                    # print(f"{self.__class__.__name__}._openSelectedFileItemsThreaded loaded ({k}, {item})")
                    progressSignal.emit(k)
                        
            except:
                traceback.print_exc()
                continue
                    
            if isinstance(loopControl, dict) and loopControl.get("break", None) == True:
                if isinstance(canceledSignal, QtCore.SignalInstance):
                    canceledSignal.emit()
                break
                
        return OK
            
    @Slot(bool)
    @safewrapper
    def slot_showFilesFilter(self, val):
        self.showFileSystemFilter = val is True

    @Slot()
    @safewrapper
    def slot_hideFilesFilter(self):
        self.showFileSystemFilter=False

    @Slot(str)
    @safewrapper
    def _slot_runPythonScriptFromManager(self, fileName):
        if os.path.isfile(fileName):
            self._temp_python_filename_ = fileName
            self._slot_runPythonSource()

    @Slot(str)
    @safewrapper
    def _slot_importPythonScriptFromManager(self, fileName):
        if os.path.isfile(fileName):
            self._temp_python_filename_ = fileName
            self._slot_importPythonModule()

    @Slot(str)
    @safewrapper
    def slot_systemEditScript(self, fileName):
        if os.path.exists(fileName) and os.path.isfile(fileName):
            if self.overrideSystemEditor:
                try:
                    subprocess.run([self.scipyenEditor, fileName])
                except:
                    traceback.print_exc()
                    url = QtCore.QUrl.fromLocalFile(fileName)
                    QtGui.QDesktopServices.openUrl(url)
            else:
                url = QtCore.QUrl.fromLocalFile(fileName)
                QtGui.QDesktopServices.openUrl(url)

    @Slot(str)
    @safewrapper
    def slot_systemOpenFileOrFolder(self, fileName):
        r"""Opens fileName with the associated system application."""
        if isinstance(fileName, str) and len(fileName.strip()):
            if os.path.exists(fileName):
                url = QtCore.QUrl.fromLocalFile(fileName)
                QtGui.QDesktopServices.openUrl(url)

        elif isinstance(fileName, QtCore.QUrl) and fileName.isValid() and fileName.isLocalFile():
            QtGui.QDesktopServices.openUrl(fileName)

    @Slot(object)
    @safewrapper
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

    @Slot()
    @safewrapper
    def slot_systemOpenParentFolderForSelectedItems(self):
        selectedItems = [item for item in self.fileSystemTreeView.selectedIndexes()
                         if item.column() == 0]  # list of QModelIndex

        parentFolders = unique([os.path.dirname(
            self.fileSystemModel.filePath(item)) for item in selectedItems])

        for folder in parentFolders:
            self.slot_systemOpenFileOrFolder(folder)
            
    @Slot()
    @safewrapper
    def slot_systemOpenParentFolder2(self):
        r"""Opens the parent directory of the current directory, in system app"""
        dest = str(pathlib.Path(self.currentDir).parent)
        # print(f"{self.__class__.__name__}.slot_systemOpenParentFolder2: dest = {dest}")
        if os.path.exists(dest):
            # print(f"\t{self.__class__.__name__} OK")
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(f"file://{dest}"))

    @Slot(str)
    @safewrapper
    def slot_systemOpenParentFolder(self, fileName):
        if isinstance(fileName, str):
            if os.path.exists(fileName):
                QtGui.QDesktopServices.openUrl(QtCore.QUrl("file://%s" % os.path.dirname(fileName)))

        elif isinstance(fileName, QtCore.QUrl) and fileName.isValid() and fileName.isLocalFile():
            if fileName.isRelative():
                url = QtCore.QUrl.resolved(fileName)

            else:
                url = fileName

            # u_fileName = url.fileName()
            u_path = url.adjusted(QtCore.QUrl.RemoveFilename)  # .path()
            QtGui.QDesktopServices.openUrl(u_path)

    @Slot(str)
    @safewrapper
    def _slot_pastePythonScriptFromManager(self, fileName):
        if os.path.isfile(fileName):
            self._temp_python_filename_ = fileName
            self._slot_python_code_to_console()

    @Slot()
    @safewrapper
    def _slot_runRecentPythonScript_(self):
        if isinstance(self.sender(), QAction):
            s_name = str(self.sender().text())

            if "&" in s_name:
                s_name = s_name.replace("&", "")

            s_paths = [
                key for key, value in self._recent_scripts_dict_.items() if value == s_name]

            if len(s_paths) == 0:
                warnings.warn("Path for script %s not found" % s_name)
                return

            if len(s_paths) > 1:
                warnings.warn(
                    "Script %s is mapped to multiple files; the first in list will be used" % s_name)

            if os.path.isfile(s_paths[0]):
                self._temp_python_filename_ = s_paths[0]

                if bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier):
                    self._slot_python_code_to_console()
                else:
                    self._slot_runPythonSource()

    @Slot()
    @safewrapper
    def slot_pastePythonScript(self, fileName=None):
        if not isinstance(fileName, str) or len(fileName) == 0:
            targetDir = self.recentDirectories[0]
            if sys.platform.startswith("win32"):
                options = QtWidgets.QFileDialog.Option.DontUseNativeDialog
                kw = {"options":options}
            else:
                kw = {}
            if targetDir is not None and targetDir != "" and os.path.exists(targetDir):
                fileName = QtWidgets.QFileDialog.getOpenFileName(
                    self, caption=u"Run python script", filter="Python script (*.py)", directory=targetDir,
                    **kw)
            else:
                fileName = QtWidgets.QFileDialog.getOpenFileName(
                    self, caption=u"Run python script", filter="Python script (*.py)", **kw)

        if len(fileName) > 0:
            if isinstance(fileName, tuple):
                # NOTE: QFileDialog.getOpenFileName returns a tuple (fileName, filter string)
                fileName = fileName[0]

            if isinstance(fileName, str) and len(fileName) > 0 and os.path.isfile(fileName):
                # TODO check if this is a legitimate ASCII file containing python code
                self._run_python_source_code_(fileName, paste=True)
                # self._temp_python_filename_ = fileName
                # self._slot_python_code_to_console()

                if fileName not in self.recentScripts:
                    self.recentScripts.appendleft(fileName)
                    self._refreshRecentScriptsMenu_()

                else:
                    if fileName != self.recentScripts[0]:
                        self.recentScripts.remove(fileName)
                        self.recentScripts.appendleft(fileName)
                        self._refreshRecentScriptsMenu_()

    @Slot()
    @safewrapper
    def slot_showScriptsManagerWindow(self):
        self._showScriptsManagerWindow()

    def _showScriptsManagerWindow(self):
        self._scriptManager_.setData(self._recent_scripts_dict_)
        self._scriptManager_.setVisible(True)
        self._scriptManager_.showNormal()
        # self._script_manager_autolaunch = True

    @Slot()
    @safewrapper
    def slot_runPythonScript(self, fileName=None):
        if not isinstance(fileName, str) or len(fileName) == 0:
            targetDir = self.recentDirectories[0]
            if sys.platform.startswith("win32"):
                options = QtWidgets.QFileDialog.Option.DontUseNativeDialog
                kw = {"options":options}
            else:
                kw = {}

            if targetDir is not None and targetDir != "" and os.path.exists(targetDir):
                fileName = QtWidgets.QFileDialog.getOpenFileName(
                    self, caption=u"Run python script", filter="Python script (*.py)", directory=targetDir,
                    **kw)
            else:
                fileName = QtWidgets.QFileDialog.getOpenFileName(
                    self, caption=u"Run python script", filter="Python script (*.py)", **kw)

        if len(fileName) > 0:
            if isinstance(fileName, tuple):
                # NOTE: QFileDialog.getOpenFileName returns a tuple (fileName, filter string)
                fileName = fileName[0]

            if isinstance(fileName, str) and len(fileName) > 0 and os.path.isfile(fileName):
                # TODO check if this is a legitimate ASCII file containing python code
                self._run_python_source_code_(fileName, paste=False)

                if fileName not in self.recentScripts:
                    if isinstance(self.recentScripts, deque):
                        self.recentScripts.appendleft(fileName)
                    else:
                        rscripts = deque(self.recentScripts)
                        rscripts.appendleft(fileName)
                        self.recentScripts = rscripts
                        # self.recentScripts.insert(0, fileName)
                        
                    self._refreshRecentScriptsMenu_()

                else:
                    if fileName != self.recentScripts[0]:
                        self.recentScripts.remove(fileName)
                        self.recentScripts.appendleft(fileName)
                        self._refreshRecentScriptsMenu_()

    @Slot(str, QtCore.QPoint)
    @safewrapper
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
            registerWithManager.triggered.connect(
                self._slot_registerPythonSource_)

            # NOTE 2019-09-14 09:22:54
            # FIXME there are some cavetas to this
            # cm.addSeparator()

            # importAsModule = cm.addAction("Import As Module")
            # importAsModule.triggered.connect(self._slot_importPythonModule)

            cm.popup(self.sender().mapToGlobal(pos), loadAsText)

    @safewrapper
    def loadFile(self, fName):
        r""" Entrypoint into the file reading system, for calls from file system tree view
        Called by: 
            self.slot_fileSystemItemActivated
    
        Delegates to self.loadDiskFile(file_name, fileReader)
        """
        self.loadDiskFile(fName)

    @Slot()
    @safewrapper
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
        if isinstance(action, QAction):
            itemText = str(action.text()).replace('&', '')
            pathPart = itemText.split('[')[-1]
            fName = pathPart.split(']')[0]
            fileReader = self.recentFiles[fName]["loader"]

            self.loadDiskFile(fName, fileReader=fileReader, addToRecent=False)

    @Slot(str)
    @safewrapper
    def slot_rootPathChanged(self, newPath):
        pass
        # print("MainWindow new root path", newPath)

    @safewrapper
    def slot_selectWorkDir(self, *args):
        targetDir = self.recentDirectories[0]
        caption = "Select Working Directory"
        if sys.platform.startswith("win32"):
            options = QtWidgets.QFileDialog.Option.DontUseNativeDialog
            kw = {"options":options}
        else:
            kw = {}
        if targetDir is not None and targetDir != "" and os.path.exists(targetDir):
            dirName = str(QtWidgets.QFileDialog.getExistingDirectory(
                self, caption=caption, directory=targetDir, **kw))
            # dirName = str(QtWidgets.QFileDialog.getExistingDirectory(self, caption=u'Select Working Directory', directory=targetDir))
        else:
            dirName = str(QtWidgets.QFileDialog.getExistingDirectory(
                self, caption=caption, **kw))
            # dirName = str(QtWidgets.QFileDialog.getExistingDirectory(self, caption=u'Select Working Directory'))

        if len(dirName) > 0:
            self.slot_changeDirectory(dirName)

    @safewrapper
    def loadDiskFile(self, fName:str, fileReader:typing.Optional[typing.Callable]=None, 
                     addToRecent:bool=True, updateUi:bool=True):
        r"""Reads data from a file.
        Common landing point for local data input from the file system.
        Called by various slots connected to File menu actions. 
        
        Various file types are handled by the fileReader (see below).
        Currently, there is support for plain text file, Axon files, pickle, hdf5
        and various image file formats supported by the Vigra libraries (via the 
        vigranumpy package)
        
        TODO: suport for matlab, CED Signal and CED Spike files, etc


        Arguments:

        fName -- fully qualified data file name

        fileReader -- (optional, default is None) a str that specifies a specialized
            file reader function in the iolib.pictio module

            When None, this functions uses functions in Scipyen's pictio module 
            to find a suitable fileReader for the file

            NOTE: For image files, this only reads the image pixel data. Vigra
            library has a good capacity parsing pixel types, but not any image
            metadata (such as OME XML documents, see bioformats).
        
            TODO: 2023-05-27 14:32:19
            Try to use bioformats functionality (requires some kind of java bridge
            for this) - tried that before but was problematic.
        
        addToRecent:bool, default is True
            When True, add the fName to the list of recently open files
            WARNING: Should be set to False when loading a large batch of files
        
        updateUi:bool, default is True
            When True, the workspace viewer will be updated immediately.
        
            WARNING: May be set to False when loading a large batch of files,
            but the workspace viewer will be updated in a second stage and this
            currently blocks the UI during the workspace.
        
            CAUTION: When False, one should call self.workspaceModel.update()
        

        """

        # 2016-08-15 16:20:24
        # TODO: give the user the possibility to open image data and image metadata SEPARATELY
        # for now, they are returned both, for convenience

        try:
            (bName, fileExt) = os.path.splitext(os.path.basename(fName))

            # NOTE: 2017-06-21 15:59:41
            # fix insane file names
            bName = strutils.str2symbol(bName)

            # print("loadDiskFile", fName)
            # print("to assign to ", bName)

            if fileReader is None:
                fileReader = pio.getLoaderForFile(fName)

            # print(f"\n{self.__class__.__name__}.loadDiskFile: fileReader = {fileReader}, updateUi = {updateUi}")
            if fileReader is None:
                return False

            try:
                data = fileReader(fName)
                # print(f"{self.__class__.__name__}.loadDiskFile: data = {data}")
                if data is not None:
                    if updateUi:
                        # the line below updates workspaceViewer ui
                        self.workspaceModel.bindObjectInNamespace(bName, data)
                    else:
                        self.workspace[bName] = data
            except:
                return False

            if addToRecent:
                self._addRecentFile_(fName, fileReader)

            ret = True

        except Exception as e:
            traceback.print_exc()
            excInfo = sys.exc_info()
            tbStrIO = io.StringIO()

            # traceback.print_exception(excInfo[0], excInfo[1], excInfo[2], file=tbStrIO)

            excStr = tbStrIO.getvalue()

            tbStrIO.close()

            excStr.replace(":", ":\n")

            excStr.replace("File ", "\nFile ")

            excStr.replace("in ", "\nin ")

            excStr.replace(")", ")\n")

            errMsgDlg = QtWidgets.QErrorMessage(self)

            errMsgDlg.setWindowTitle(excInfo[0].__name__)
            errMsgDlg.showMessage(excStr)  # python3 way
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

    @Slot()
    @safewrapper
    def slot_saveFile(self):
        r"""Saves data to HDF5 or pickle file(s).

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
            varname = self.workspaceModel.item(
                selectedItems[0].row(), 0).text()

            if type(self.workspace[varname]).__name__ == 'VigraArray':
                # NOTE: 2024-06-01 16:52:57
                # special case because we can export data to image file types
                fileFilters = list()
                fileFilters.append("Pickle (*pkl)")
                fileFilters.append("HDF5 (*.h5)")
                imageFileFilters = list()
                imageFileFilters.append('All Image Types (' + ' '.join([''.join(i) for i in zip('*' * len(
                    pio.SUPPORTED_IMAGE_TYPES), '.' * len(pio.SUPPORTED_IMAGE_TYPES), pio.SUPPORTED_IMAGE_TYPES)]) + ')')
                imageFileFilters.extend(
                    ['{I} (*.{i})'.format(I=i.upper(), i=i) for i in pio.SUPPORTED_IMAGE_TYPES])
                fileFilters.extend(imageFileFilters)
                fileFilt = ';;'.join(fileFilters)

                targetDir = self.recentDirectories[0]

                if sys.platform.startswith("win32"):
                    options = QtWidgets.QFileDialog.Option.DontUseNativeDialog
                    kw = {"options":options}
                else:
                    kw = {}

                if targetDir is not None and targetDir != "" and os.path.exists(targetDir):
                    fileName, file_flt = QtWidgets.QFileDialog.getSaveFileName(
                        self, caption=u'Save/Export to Image File', filter=fileFilt, directory=targetDir,
                        **kw)

                else:
                    fileName, file_flt = QtWidgets.QFileDialog.getSaveFileName(
                        self, caption=u'Save/Export to Image File', filter=fileFilt,
                        **kw)

                if len(fileName) > 0:
                    data = self.workspace[varname]
                    if file_flt in imageFileFilters:
                        if self._saveImageFile_(data, fileName):
                            self._addRecentFile_(fileName)

                    else:
                        if file_flt.startswith("HDF5"):
                            pio.saveHDF5(data, fileName)

                        else:
                            pio.savePickleFile(data, fileName)

            else:
                fileFilters = list()
                fileFilters.append("Pickle (*.pkl)")
                fileFilters.append("HDF5 (*.h5)")
                fileFilt = ';;'.join(fileFilters)
                targetDir = self.recentDirectories[0]

                if sys.platform.startswith("win32"):
                    options = QtWidgets.QFileDialog.Option.DontUseNativeDialog
                    kw = {"options":options}
                else:
                    kw = {}

                if targetDir is not None and targetDir != "" and os.path.exists(targetDir):
                    fileName, file_flt = QtWidgets.QFileDialog.getSaveFileName(
                        self, caption=u'Save/Export as', filter=fileFilt, directory=targetDir,
                        **kw)

                else:
                    fileName, file_flt = QtWidgets.QFileDialog.getSaveFileName(
                        self, caption=u'Save/Export as', filter=fileFilt,
                        **kw)

                if len(fileName) > 0:
                    data = self.workspace[varname]
                    if file_flt.startswith("HDF5"):
                        pio.saveHDF5(data, fileName)

                    elif file_flt.startswith("Pickle"):
                        pio.savePickleFile(data, fileName)
                            
                    else:
                        file_type = "unspecified"
                        if len(file_flt) == 0:
                            ext = pathlib.Path(fileName).suffix
                            if len(ext):
                                file_type = pio.getMimeAndFileType(f"*{ext}")[0]
                                
                        else:
                            file_type = pio.getMimeAndFileType(file_flt.replace('(', '').replace(')', ''))[0]
                            
                        if file_type is None:
                            file_type = "unspecified"
                            
                        self.errorMessage("Save as...",f"I don't know how to save to {type(data).__name__} data to {file_type} file type")
                        return
        else:
            self.slot_saveSelectedVariables() # saves as HDF5 by default

    # NOTE: 2016-04-01 11:09:49
    # file dialog filtered on all supported image file formats
    # check is selected file format supported by vigra and use vigra impex to open
    # else use bioformats to open
    # NOTE: 2016-04-01 11:48:52
    # use list comprehension to construct filter
    # @_workspaceModifier # NOTE: 2016-05-02 20:46:58 not used anymore here

    @Slot()
    @safewrapper
    def openFile(self):
        '''Slot to which File Open typically connects to.
        # TODO: merge with file openers for the fileSystemTreeView
        Prompts user to choose a file using a File Open dialog
        '''
        # 2016-08-11 13:48:19
        # NOTE: the API for getOpenFileName has changed for Qt 5
        # If you want multiple filters, separate them with ';;', for example:
        # "Images (*.png *.xpm *.jpgui);;Text files (*.txt);;XML files (*.xml)"

        from core.utilities import make_file_filter_string

        if self.slot_openSelectedFileItems():
            return

        (allImageTypesFilter, individualImageTypeFilters) = make_file_filter_string(
            pio.SUPPORTED_IMAGE_TYPES, 'All Image Types')

        allMimeTypes = ";;".join([i[0] + " (" + i[1] + ") " for i in zip(
            pio.mimetypes.types_map.values(), pio.mimetypes.types_map.keys())])

        filesFilterString = ';;'.join(
            ["All file types (*.*)", allImageTypesFilter, individualImageTypeFilters, allMimeTypes])

        targetDir = self.recentDirectories[0]

        if sys.platform.startswith("win32"):
            options = QtWidgets.QFileDialog.Option.DontUseNativeDialog
            kw = {"options":options}
        else:
            kw = {}

        if targetDir is not None and targetDir != "" and os.path.exists(targetDir):
            fileName = QtWidgets.QFileDialog.getOpenFileName(
                self, caption=u'Open File', filter=filesFilterString, directory=targetDir, **kw)

        else:
            fileName = QtWidgets.QFileDialog.getOpenFileName(
                self, caption=u'Open File', filter=filesFilterString, **kw)

        if len(fileName) > 0:

            if isinstance(fileName, tuple):
                # NOTE: QFileDialog.getOpenFileName returns a tuple (fileName, filter string)
                fileName = fileName[0]

            # print("fileName: ", fileName)

            if isinstance(fileName, str) and len(fileName) > 0:
                if self.loadDiskFile(fileName):
                    self._addRecentFile_(fileName)
                    self.workspaceModel.update()

    # NOTE: 2016-04-01 12:18:23
    # keep this as we may want to enforce the use of BioFormats for opening files
    # @_workspaceModifier # NOTE: 2016-05-02 20:46:45 decorator not used anymore here
    #
    # 2016-08-11 14:13:24
    # NOTE: see NOTE above loadImageFile(self):
    # @Slot()
    # def loadBioFormatsImageFile(self):
        # '''Slot to which an item in the File typically connects to.

        # Prompts user to choose a file using a File Open dialog.

        # '''
        # from utilities import make_file_filter_string

        # (allImageTypesFilter, individualImageTypeFilters) = make_file_filter_string(bf.READABLE_FORMATS, 'BioFormats Image Types')

        # filesFilterString = ';;'.join([allImageTypesFilter, individualImageTypeFilters])

        # bf_extensions = bf.READABLE_FORMATS

        # targetDir = self.recentDirectories[0]

        # if targetDir is not None and targetDir != "" and os.path.exists(targetDir):
            # fileName = QtWidgets.QFileDialog.getOpenFileName(self, caption=u'Open Image File Using BioFormats', filter=filesFilterString, directory=targetDir)
        # else:
            # fileName = QtWidgets.QFileDialog.getOpenFileName(self, caption=u'Open Image File Using BioFormats', filter=filesFilterString)

        # if len(fileName) > 0:
            # if isinstance(fileName, tuple):
                # fileName = fileName[0] # NOTE: QFileDialog.getOpenFileName returns a tuple (fileName, filter string)

            # if isinstance(fileName, str) and len(fileName) > 0:
                # if self.loadDiskFile(fileName, True):
                    # self._addRecentFile_(fileName, "bioformats")
                    # self.workspaceModel.update()

    @Slot()
    @safewrapper
    def slot_openFiles(self):
        r"""Opening of several files via (triggered from) the 'File/Open' menu action.
        """
        from core.utilities import make_file_filter_string

        # FIXME: 2023-05-27 14:51:46
        # the below becomes a threaded version, therefore we need to move the code 
        # that is coming past it, to the function that processes the result of the 
        # file loading thread
        # selectedItems = [self.fileSystemModel.filePath(item) for item in self.fileSystemTreeView.selectedIndexes()
        #                  if item.column() == 0 and not self.fileSystemModel.isDir(item)]  # list of QModelIndex
        # if len(selectedItems):
        if self.slot_openSelectedFileItems():
            return

        (allImageTypesFilter, individualImageTypeFilters) = make_file_filter_string(
            pio.SUPPORTED_IMAGE_TYPES, 'All Image Types')

        allMimeTypes = ";;".join([i[0] + " (" + i[1] + ") " for i in zip(
            pio.mimetypes.types_map.values(), pio.mimetypes.types_map.keys())])

        filesFilterString = ';;'.join(
            ["All file types (*.*)", allImageTypesFilter, individualImageTypeFilters, allMimeTypes])

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

            # self.workspaceModel.update()

    @Slot()
    @safewrapper
    def _slot_openNamedFile_(self):
        r"""Called by slot_handlePythonTextFile"""
        # TODO: 2023-05-27 14:43:34
        # unformization of I/O, inclusion with future breadcrumbs navigation
        # framework (in progress)
        if isinstance(self._temp_python_filename_, str) and len(self._temp_python_filename_.strip()) and os.path.isfile(self._temp_python_filename_):
            self.loadFile(self._temp_python_filename_)
            self._temp_python_filename_ = None

    @Slot()
    @safewrapper
    def _slot_python_code_to_console(self):
        if isinstance(self._temp_python_filename_, str) and len(self._temp_python_filename_.strip()) and os.path.isfile(self._temp_python_filename_):
            self._run_python_source_code_(
                self._temp_python_filename_, paste=True)

            if self._temp_python_filename_ not in self.recentScripts:
                self.recentScripts.appendleft(self._temp_python_filename_)
                self._refreshRecentScriptsMenu_()

            else:
                if self._temp_python_filename_ != self.recentScripts[0]:
                    self.recentScripts.remove(self._temp_python_filename_)
                    self.recentScripts.appendleft(self._temp_python_filename_)
                    self._refreshRecentScriptsMenu_()

    @Slot()
    @safewrapper
    def _slot_gui_worker_done_(self):
        QtWidgets.QApplication.setOverrideCursor(self._defaultCursor)

    @Slot(object)
    @safewrapper
    def _slot_gui_worker_result_(self, val):
        print("ScipyenWindow._slot_gui_worker_result_", val)
        pass

    @Slot(object)
    @safewrapper
    def _slot_forgetScripts_(self, o):
        if isinstance(o, str):
            if o in self.recentScripts:
                self.recentScripts.remove(o)

        elif isinstance(o, (tuple, list)) and all([isinstance(v, str) for v in o]):
            for v in o:
                self.recentScripts.remove(v)

        self._refreshRecentScriptsMenu_()

    @Slot()
    @safewrapper
    def _slot_dockConsole(self):
        if self.console is not None:
            self.consoleDockWidget.setWidget(self.console)
            self.console.show()
            self.consoleDockWidget.setVisible(True)
            self._console_docked_ = True

    @Slot()
    @safewrapper
    def _slot_undockConsole(self):
        # FIXME 2021-11-26 18:37:40
        if self.console is not None:
            self.consoleDockWidget.layout().removeWidget(self.console)
            self.console.setVisible(True)
            self.consoleDockWidget.setVisible(False)
            self._console_docked_ = False

    @Slot()
    @safewrapper
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

    @Slot()
    @safewrapper
    def _slot_copyToExternalWS(self):
        from core.extipyutils_client import cmd_copy_to_foreign
        # get the model indices of the selected workspace model items
        indexList = [i for i in self.workspaceView.selectedIndexes()
                     if i.column() == 0]
        if len(indexList) == 0:
            return
        # headers = [k for k in standard_obj_summary_headers if k != "Icon"]
        wscol = self._wspace_headers_.index("Workspace")
        varnames = [self.workspaceModel.item(i.row(), 0).text() for i in indexList if self.workspaceModel.item(i.row(), wscol).text() == "Internal"]
        ns = self.external_console.window.find_tab_title(self.external_console.window.active_frontend)
        for varname in varnames:
            # print("_slot_copyToExternalWS: varname = %s , data = %s" % (varname, self.workspace[varname]))
            self.external_console.execute(cmd_copy_to_foreign(varname, self.workspace[varname]),
                                          where=ns)

        self.external_console.execute(
            cmd_foreign_shell_ns_listing(namespace=ns))

    @Slot()
    @safewrapper
    def _slot_copyFromExternalWS(self):
        from core.utilities import standard_obj_summary_headers
        from core.extipyutils_client import cmd_copies_from_foreign

        # get the model indices of the selected workspace model items
        indexList = [i for i in self.workspaceView.selectedIndexes()
                     if i.column() == 0]
        if len(indexList) == 0:
            return

        # headers = [k for k in standard_obj_summary_headers if k != "Icon"]
        wscol = self._wspace_headers_.index("Workspace")

        # deal with those that belong to an external workspace
        for ns in self.workspaceModel.foreign_namespaces:
            varnames = [self.workspaceModel.item(i.row(), 0).text() for i in indexList if self.workspaceModel.item(i.row(), wscol).text() == ns]

            if len(varnames):
                self.external_console.execute(
                    cmd_copies_from_foreign(*varnames), where=ns)

            # wsname = ns.replace("_", " ")
            # varnames = [self.workspaceModel.item(i.row(),0).text() for i in indexList if self.workspaceModel.item(i.row(), wscol).text() == wsname]

            # if len(varnames):
                # self.external_console.execute(cmd_copies_from_foreign(*varnames),
                # where = wsname)

    @Slot(object)
    def _slot_int_krn_shell_chnl_msg_recvd(self, msg):
        if msg["msg_type"] == "execute_reply":
            pass

    @Slot(object)
    @safewrapper
    def _slot_ext_krn_shell_chnl_msg_recvd(self, msg:dict):
        r"""Parses the message received from the external kernel.
        The function processes <action>_reply messages emitted from the external
        kernel, via the kernel's shell 'channel' or 'socket', in reply to an
        <action>_request message sent by the client (e.g. console.execute(…))
        
        Here, `action` is one of 'execute', 'kernel_info', 'is_complete'
        
        Parameters:
        ===========
        msg — the received message (kernel's reply) — the key:str ↦ value mapping
        below:
        
        'header',           ↦   mapping:
                                'msg_id'    ↦ str — typically UUID, unique per message
                                'msg_type'  ↦ str — one of:
                                            'execute_reply', 
                                            'kernel_info_reply'
                                            'is_complete_reply'
                                'username'  ↦ str — platform user name
                                'session'   ↦ str — typically UUID, unique per session
                                            NOTE: this identifies the kernel process
                                'date'      ↦ datetime.datetime (ISO 8601 timestamp)
                                'version'   ↦ str — major.minor e.g. 5.3
                                            (message protocol version: verison of
                                            the Jupyter message specification used)
                                
        'msg_id',           ↦   exposed from 'header' (¹)
        
        'msg_type',         ↦   exposed from 'header' (¹)
        
        'parent_header',    ↦   mapping — copy of the header of the message that 
                                caused the current message, or empty.
                                Not empty in *_reply messages.
        
        'metadata',         ↦   mapping — information about the message that is 
                                not part of the 'content'
                                Can be used as information store about requests &
                                replies (e.g. infomration about request or execution
                                context)
        
        'content',          ↦   mapping — THE BODY OF THE MESSAGE, depends on msg_type:
        
                                'status'    ↦ str: "ok" | "error" | "abort"
                                            present in ALL _reply messages
                all '*_reply' messages:
                        when 'status' is 'error':
                                'ename'     ↦ str — exception name
                                'evalue'    ↦ str — exception value
                                'traceback' ↦ list[str] — traceback frames as strings
        
                        when 'status' is 'abort' (being deprecated):
                                ⋆ same as 'error' but without error information:
                                no 'ename', 'evalue', 'traceback'
        
                'execute_reply' messages:
                        regardless of 'status':
                                'execution_count' ↦ int
        
                        when 'status' == 'ok':
                                'payload' ↦ list[dict]³
                                'user_expressions' ↦ dict — the result for the 
                                    'user_expressions' in the preceding 
                                        'execute_request' message.
        
        'buffers',          ↦   list — additional binary buffers associated with 
                                a message.
                                Typically empty, this is not officially used by 
                                IPython except for IPython Parallel `apply` and 
                                some ipywidgets `comm` messages.
        
        'workspace_name',   ↦   str — the "name" of the external console "tab" or
                                frontend (²)
                                Provides a a means to identify which external
                                process is being used; also gives the name of the 
                                workspace for the variable symbols displayed in
                                Scipyen workspace viewer.
                                
        
        'connection_file'   ↦   str — the json connection file used by the external
                                kernel for communication and messaging with the
                                frontend (²)
                                Further means to identify kernel ↔ frontend
                                communication in Scipyen.
                                
        FOOTNOTES:
        ¹ Python implementation of the protocol;
        ² Introduced by Scipyen, and valid only for Scipyen sessions
        ³ Considered deprecated in IPython, but no replacement implemented.
            A "payload" dict is :
                'source' ↦ str, one of: 'page', 'set_next_input', 'edit_magic',
                                        'ask_exit'
        
        """
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
                                             cmd_foreign_shell_ns_hidden_listing,
                                             )

        if self.external_console.window.tab_widget.count() == 0:
            # only listen to kernels that have a frontend
            return

        # ATTENTION: 2021-01-30 14:13:28
        # only use for debugging
        # if msg["connection_file"] in self.external_console.window.connections:
            # if self.external_console.window.connections[msg["connection_file"]]["master"] is None:
            # print("external kernel via %s" % msg["connection_file"])
            # print("\t", msg)
            
        # print(f"{self.__class__.__name__}._slot_ext_krn_shell_chnl_msg_recvd:\n\tmessage keys =\n\t{list(msg.keys())}")
            
        ns_name = msg["workspace_name"]
        internal_ns_name = ns_name.replace(" ", "_") # internal representation of namespace name to avoid confusing the foreign_namespaces in workspace model
        
        header = msg["header"]
        
        # print(f"{self.__class__.__name__}._slot_ext_krn_shell_chnl_msg_recvd {msg['msg_type']} from workspace: '{ns_name}' -> {msg['content']['status']}")
        # print(f"\theader: {header}")

        connections = list(filter(lambda x: x[1]["name"] == ns_name, self.external_console.window.connections.items()))
        
        if len(connections) < 1:
            return
        
        connection = connections[0]
        connection_file = connection[0]
        msg_connection_file = msg.get('connection_file', None)
        # print(f"\tconnection_file\n\t\tfrom console: {connection_file}\n\t\tfrom message: {msg_connection_file}\n\tidentical: {connection_file == msg_connection_file}")
        
        # print(f"\t{msg['msg_type']}: {msg['content']['status']}")
        if msg['content']['status'] == 'error':
            scipywarn(f"Error {msg['content']['ename']}: {msg['content']['evalue']}")
            return
        elif msg['content']['status'] == "abort":
            scipywarn(f"Aborted in {msg['workspace_name']}")
            return
        
        if msg["msg_type"] == "execute_reply":
            vardict = unpack_shell_channel_data(msg)
            # print(f"\t\tvardict: {len(vardict)}")

            if len(vardict):
                # print(f"\t\tgot vardict with ({len(vardict)}) key ↦ value mappings:")
                # dict with properties of variables in external kernel namespace
                prop_dicts = dict(
                    [(key, val) for key, val in vardict.items() if key.startswith("properties_of_")])
                # print(f"\t\tproperty mappings: {list(prop_dicts.keys())}")

                ns_hidden_listing = dict(
                    [(key, val) for key, val in vardict.items() if key.startswith("hidden_ns_listing_of_")])
                # print(f"\t\t{len(ns_hidden_listing)} hidden listing")
                # print(f"\t\thidden_ns_listing: {list(ns_hidden_listing.keys())}")
                
                if len(ns_hidden_listing):
                    # print(f"{self.__class__.__name__}._slot_ext_krn_shell_chnl_msg_recvd:\n\tns_hidden_listing:\n\t{ns_hidden_listing}")
                    user_ns_hidden_vars = ns_hidden_listing[f"hidden_ns_listing_of_{ns_name}"]
                    self.workspaceModel.updateForeignNamespace(ns_name, connection_file, user_ns_hidden_vars, hidden=True)
                else:
                    self.workspaceModel.updateForeignNamespace(ns_name, connection_file, {'user_ns':dict()}, hidden=True)
                    
                # dict with listing of contents of the external kernel namespace
                ns_listings = dict(
                    [(key, val) for key, val in vardict.items() if key.startswith("ns_listing_of_")])
                
                # print(f"\t\tns_listings: {list(ns_listings.keys())}")
                
                # print(f"\t\t{len(ns_listings)} var listing")
                
                if len(ns_listings):
                    for key, val in ns_listings.items():
                        ns_name = key.replace("ns_listing_of_", "")
                        if ns_name == msg["workspace_name"]: # is this check really necessary? FIXME 2024-09-21 17:31:14
                            if isinstance(val, dict):
                                self.workspaceModel.updateForeignNamespace(ns_name, msg["connection_file"], val, hidden=False)
                                for varname in self.workspaceModel.getForeignNamespaceSymbols(ns_name, "current"):
                                    # print(f"\t\t\tquerying properties for {varname}")
                                    self.external_console.execute(cmds_get_foreign_data_props(varname,
                                                                                                namespace=msg["workspace_name"]),
                                                                    where=msg["parent_header"]["session"])

                            
                if len(prop_dicts):
                    # print("\t\t\t processing properties dicts")
                    for key, value in prop_dicts.items():
                        if value["Workspace"]["display"] == "Internal":
                            value["Workspace"] = {"display": ns_name,
                                                  "tooltip": f"Location: namespace of {ns_name}"}

                        # NOTE: 2024-09-21 14:28:31
                        # Icon objects cannot be shuttled so we need to insert them here
                        # (on the client side we removed the Icon property)
                        value = augment_obj_prop_dict(value)

                        for propname in value.keys():
                            if propname != "Icon":
                                value[propname]["tooltip"] = value[propname]["tooltip"].replace(
                                    "Internal", ns_name)
                            
                    self.workspaceModel.updateFromExternal(prop_dicts)


        elif msg["msg_type"] == "kernel_info_reply":
            # print(f"\t=> query namespace listing")
            if ns_name not in self.workspaceModel.foreign_namespaces:
                self.workspaceModel.updateForeignNamespace(ns_name, msg["connection_file"], tuple(), hidden=False)
            # evoke an execute_reply message containing namespace listing of visible variables
            self.external_console.execute(cmd_foreign_shell_ns_listing(namespace=msg["workspace_name"]),
                                          where=msg["parent_header"]["session"])
            
        elif msg['msg_type'] == "complete_reply":
            # print(f"\tTODO")
            pass

        elif msg["msg_type"] == "is_complete_reply": 
            # code completeness
            # refresh the listing to see if anything changed
            # print(f"\t-> refresh ns listing")
            # will evoke an execute_reply message containing namespace lisiting of visible variables
            self.external_console.execute(cmd_foreign_shell_ns_listing(namespace=msg["workspace_name"]),
                                          where=msg["parent_header"]["session"])
            
        elif msg["msg_type"] == "history_reply":
            # request history from a kernel
            # print(f"\tTODO")
            pass
            
        elif msg["msg_type"] == "inspect_reply":
            # introspection
            # print(f"\tTODO")
            pass
            
        else:
            # print(f"\tTODO")
            pass
            
        # print("***\n")

    def execute_in_external_console(self, call, where=None):
        self.external_console.execute(call, where=where)

    @Slot(dict)
    @safewrapper
    def _slot_ext_krn_disconnected(self, cdict):
        # print("mainWindow: _slot_ext_krn_disconnected %s" % cdict)
        signalBlocker = QtCore.QSignalBlocker(self.external_console.window)
        self.workspaceModel.removeForeignNamespace(cdict)

    @Slot(dict)
    @safewrapper
    def _slot_ext_krn_stop(self, conndict):
        print("mainWindow: _slot_ext_krn_stop %s" % conndict)
        signalBlocker = QtCore.QSignalBlocker(self.external_console.window)
        self.workspaceModel.removeForeignNamespace(conndict)

    @Slot(dict)
    @safewrapper
    def _slot_ext_krn_restart(self, conndict):
        # print("mainWindow: _slot_ext_krn_restart %s" % conndict)
        from core.extipyutils_client import cmd_foreign_shell_ns_listing

        ns_name = conndict["name"]

        signalBlocker = QtCore.QSignalBlocker(self.external_console.window)

        self.external_console.execute(
            cmd_foreign_shell_ns_listing(namespace=ns_name))

    @safewrapper
    def _import_python_module_file_(self, fileName):
        import importlib.util
        import sys

        moduleName = strutils.str2symbol(os.path.splitext(fileName)[0])

        spec = importlib.util.spec_from_file_location(moduleName, fileName)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        sys.modules[moduleName] = module

    @Slot(str)
    def _slot_scriptFileAddedInManager(self, fileName):
        self._temp_python_filename_ = fileName
        self._slot_registerPythonSource_()

    @Slot()
    def _slot_clearInternalWorkspace(self):
        varNames = self.workspaceModel.getDisplayedVariableNames()
        prompt = self.tr("Remove all variables from the workspace?")
        wintitle = self.tr("Delete variables")
        msgBox = QtWidgets.QMessageBox()

        msgBox.setWindowTitle(wintitle)
        msgBox.setIcon(QtWidgets.QMessageBox.Warning)
        msgBox.setText(prompt)
        msgBox.setInformativeText(self.tr("This operation cannot be undone!"))
        msgBox.setStandardButtons(
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        msgBox.setDefaultButton(QtWidgets.QMessageBox.No)

        ret = msgBox.exec()
        if ret == QtWidgets.QMessageBox.No:
            return

        for n in varNames:
            obj = self.workspace[n]
            if isinstance(obj, (QtWidgets.QMainWindow, mpl.figure.Figure)):
                # print("%s.slot_deleteSelectedWorkspaceObjects %s: %s" % (self.__class__.__name__, n, obj.__class__.__name__))
                if isinstance(obj, mpl.figure.Figure):
                    # also removes obj.number from plt.get_fignums()
                    plt.close(obj)

                else:
                    obj.close()

                # does not remove its symbol for workspace - this has already been removed by delete action
                self.deRegisterWindow(obj)
                # super().deRegisterWindow(obj)

            # self.removeWorkspaceSymbol(n)
            self.workspace.pop(n, None)

        # self.workspaceModel.currentItem = None
        self.currentVarItem = None

        self.workspaceModel.update()

    @Slot()
    def _slot_cm_AddPythonScriptToManager(self):
        selectedItems = [item for item in self.fileSystemTreeView.selectedIndexes()
                         if item.column() == 0 and not self.fileSystemModel.isDir(item)]  # list of QModelIndex

        if len(selectedItems) == 0:
            return

        fileNames = [self.fileSystemModel.filePath(i) for i in selectedItems]

        for f in fileNames:
            self._slot_scriptFileAddedInManager(f)

    @Slot()
    def _slot_scriptManagerClosed(self):
        self.scriptManagerAutoLaunch = False

    @Slot(bool)
    def _slot_set_scriptManagerAutoLaunch(self, val):
        self.scriptManagerVisible = val
        
    @Slot()
    @safewrapper
    def _slot_registerPythonSource_(self):
        if isinstance(self._temp_python_filename_, str) and len(self._temp_python_filename_.strip()) and os.path.isfile(self._temp_python_filename_):
            if self._temp_python_filename_ not in self.recentScripts:
                # NOTE:2022-01-28 23:11:59
                # this bypasses self.recentScript.setter therefore this will NOT
                # be saved in the config
                # see solution at NOTE:2022-01-28 23:16:57
                #
                self.recentScripts.appendleft(self._temp_python_filename_)
                # self.recentScripts.insert(0, self._temp_python_filename_)
                self._refreshRecentScriptsMenu_()

            else:
                if self._temp_python_filename_ != self.recentScripts[0]:
                    rscripts = [s for s in self.recentScripts if s !=
                                self._temp_python_filename_]
                    rscripts.insert(0, self._temp_python_filename_)
                    self.recentScripts = rscripts

                # if self._temp_python_filename_ != self.recentScripts[0]:
                    # self.recentScripts.remove(self._temp_python_filename_)
                    # self.recentScripts.appendleft(self._temp_python_filename_)
                    # self._refreshRecentScriptsMenu_()

            self._temp_python_filename_ = None

    @Slot()
    @safewrapper
    def _slot_runPythonSource(self):
        if isinstance(self._temp_python_filename_, str) and len(self._temp_python_filename_.strip()) and os.path.isfile(self._temp_python_filename_):
            self._run_python_source_code_(self._temp_python_filename_, 
                                          paste=False)

            if self._temp_python_filename_ not in self.recentScripts:
                self.recentScripts.insert(0, self._temp_python_filename_)
                self._refreshRecentScriptsMenu_()

            else:
                if self._temp_python_filename_ != self.recentScripts[0]:
                    self.recentScripts.remove(self._temp_python_filename_)
                    self.recentScripts.insert(0, self._temp_python_filename_)

            self._temp_python_filename_ = None

    def _run_python_source_code_(self, fileName, paste=False):
        bfn = os.path.basename(fileName)
        msg = f"Sending {bfn} to console" if paste else f"Running {bfn} in console"
        self.statusbar.showMessage(msg)
        if os.path.isfile(fileName):
            if paste:
                text = pio.loadFile(fileName)
                # NOTE: 2022-10-29 14:05:19
                # code is pasted on the console, so you need to press <Enter>
                self.console.writeText(text)

            else:
                fname = os.path.splitext(fileName)[0]

                if sys.platform.startswith("win32"):
                    cmd = f'run -i -n -t "{fname}"'
                else:
                    cmd = f"run -i -n -t '{fname}'"

                try:
                    self.workspaceModel.preExecute()
                    self.console.centralWidget().clear_last_input()
                    self.console.centralWidget()._flush_pending_stream()
                    self.console.execute(cmd, hidden=True, interactive=True)
                    self.workspaceModel.postRunCell(Bunch(success=True))

                except:
                    traceback.print_exc()

                # NOTE: 2022-10-29 13:59:16
                # This is required so that we have an input prompt ready at the console,
                # after execution, bypassing the need to press <Esc> key to get back to
                # the input prompt. The side effect is that we can see any console output
                # issued during the execution of code, which would have dissapeared after
                # <Esc> key press - and THAT'S A GOOD THING
                self.console.centralWidget()._show_interpreter_prompt()
                
        self.statusbar.showMessage("Done!")

    @Slot(bool)
    def _slot_setAutoRemoveViewers(self, value):
        self.autoRemoveViewers = value == True

    @Slot(str)
    @safewrapper
    def _slot_test_gui_style(self, val: str):
        self._prev_gui_style_name = self._current_GUI_style_name
        self._do_apply_style(val)
        
    @Slot(bool)
    @safewrapper
    def _slot_setUseDefaultFont(self, val:bool):
        self.useSystemFont = val==True
        self.actionCommandHistoryFont.setEnabled(not self.useSystemFont)
        self.actionWorkplaceFont.setEnabled(not self.useSystemFont)
            
        
    @Slot()
    @safewrapper
    def _slot_chooseWorkplaceFont(self):
        currentFont = self._commandHistoryFont
        selectedFont = self.selectFont(currentFont)
        if isinstance(selectedFont, QtGui.QFont):
            self._workspaceViewerFont = selectedFont
            self._updateWorkspaceItemsFont()
    
    @Slot()
    @safewrapper
    def _slot_chooseHistoryFont(self):
        currentFont = self._commandHistoryFont
        selectedFont = self.selectFont(currentFont)
        if isinstance(selectedFont, QtGui.QFont):
            self._commandHistoryFont = selectedFont
            self._updateHistoryViewFont()

    def _do_apply_style(self, val:str):
        if val == "Default":
            styleProxy = MenuProxy(QtWidgets.QApplication.style())
            self.app.setStyle(styleProxy)
            # self.app.setStyle(QtWidgets.QApplication.style())
            # self._current_GUI_style_name = "Default"
        else:
            qtStyle = QtWidgets.QStyleFactory.create(val)
            qtPalette = qtStyle.standardPalette()
            styleProxy = MenuProxy(qtStyle)
            self.app.setPalette(qtPalette)
            self.app.setStyle(styleProxy)
#             if hasQDarkTheme and val.startswith("Qt"):
#                 #theme = val.replace("PyQtDarkTheme_", "")
#                 theme = val.replace("Qt", "").lower()
#                 qdarktheme.setup_theme(theme)
#             elif hasQDarkStyle and val.startswith("QDarkStyle"):
#                 if val == "QDarkstyle Dark":
#                     self.app.setStyleSheet(qdarkstyle.load_stylesheet(palette = qdarkstyle.dark.palette.DarkPalette))
#                 else:
#                     self.app.setStyleSheet(qdarkstyle.load_stylesheet(palette = qdarkstyle.light.palette.LightPalette))
#
#                 styleProxy = MenuProxy(QtWidgets.QApplication.style())
#                 self.app.setStyle(styleProxy)
#             else:
#                 qtStyle = QtWidgets.QStyleFactory.create(val)
#                 qtPalette = qtStyle.standardPalette()
#                 styleProxy = MenuProxy(qtStyle)
#
#                 # NOTE: 2024-09-26 14:54:59 HACK
#                 # remove traces of qdarktheme from the app
#                 # undoes the HACK in qdarktheme.setup_theme
#                 qdarkstyleprop = "_qdarktheme_use_setup_style"
#                 props = self.app.dynamicPropertyNames()
#                 if qdarkstyleprop in (bytes(p).decode() for p in props):
#                     self.app.setProperty(qdarkstyleprop, False)
#
                # self.app.setPalette(qtPalette)
                # self.app.setStyle(styleProxy)

    @Slot()
    @safewrapper
    def _slot_set_ExternalHDF5Viewer(self):
        # NOTE: 2025-03-24 21:35:03 NOT USED
        caption = "Path to external HDF5 Viewer executable"
        kw = dict()
        if sys.platform.startswith("win32"):
            kw = {"options":QtWidgets.QFileDialog.Option.DontUseNativeDialog}
            
        hdf5Viewer = str(QtWidgets.QFileDialog.getExistingDirectory(
            self, caption=caption, directory = pathlib.Path.home().as_posix(), **kw))
        
        if len(fileName) > 0:
            self.externalHDF5Viewer = fileName
    
    @Slot()
    @safewrapper
    def _slot_set_Users_Plugins_directory(self):
        targetDir = self._user_plugins_dir
        caption = "Select users plugins top directory"
        if sys.platform.startswith("win32"):
            options = QtWidgets.QFileDialog.Option.DontUseNativeDialog
            kw = {"options":options}
        else:
            kw = {}
        if targetDir is not None and targetDir != "" and os.path.exists(targetDir):
            dirName = str(QtWidgets.QFileDialog.getExistingDirectory(
                self, caption=caption, directory=targetDir, **kw))
        else:
            dirName = str(QtWidgets.QFileDialog.getExistingDirectory(
                self, caption=caption, **kw))

        if len(dirName) > 0:
            self.userPluginsDirectory = dirName
            
        self.slot_reloadPlugins()
            
        # self.informationMessage_static(text=f"Restart Scipyen to load plugins from {self.userPluginsDirectory}")

    @Slot()
    @safewrapper
    def _slot_about(self) -> None:
        vrs = f"{self.__version__}"
        if self._pyinstaller_bundled_:
            build_file = pathlib.Path(sys._MEIPASS).parent / "BUILD"
            if build_file.exists():
                buildstr = build_file.read_text(encoding="utf-8").strip("\n").strip()
                vrs += f"\nPyInstaller Bundle:\n{buildstr}"
            else:
                vrs += " (PyInstaller Bundle)"
                
        txt = ["Scipyen (Scientific Python Environment for Neuroscience)",
               f"Version:  {vrs}",
               "",
               "Authors:",
               "",
               "Cezar M. Tigaret"]
        
        QtWidgets.QMessageBox.about(self, "About Scipyen", "\n".join(txt))
        
    @Slot()
    def _slot_about_qt(self)->None:
        QtWidgets.QMessageBox.aboutQt(self, "Scipyen and Qt")
        
    
    @Slot()
    def _slot_showLicense(self) -> None:
        txt = pio.loadTextFile(os.path.join(self._scipyendir_, "doc", "AboutLicense.html"))
        d = AboutDialog(txt, self, "License")
        # d.show()
    
    @Slot()
    @safewrapper
    def _slot_aboutComponents(self) -> None:
        from helpsystem import helputils
        txt = helputils.info_scipyen_components(self.workspace)
        d = AboutDialog(txt, self, "Software Components")
        
    @Slot()
    @safewrapper
    def _slot_set_Application_style(self):
        from .itemslistdialog import ItemsListDialog
        themeslist = ["Default"] + self._available_Qt_style_names_
        #if hasQDarkTheme:
            #qdarkthemes = [
                #f"PyQtDarkTheme_{t}" for t in qdarktheme.get_themes()]

            #themeslist.extend(qdarkthemes)

        d = ItemsListDialog(self, itemsList=["Default"] + self._available_Qt_style_names_,
                            title="Choose Application GUI Style",
                            preSelected=self._current_GUI_style_name)

        d.itemSelected.connect(self._slot_test_gui_style)

        a = d.exec()

        if a == QtWidgets.QDialog.Accepted:
            sel = d.selectedItemsText
            if len(sel):
                style = sel[0]

            self.guiStyle = style

        else:
            self.guiStyle = self._prev_gui_style_name

    @Slot(tuple)
    def slot_windowRemoved(self, name_obj):
        self.shell.user_ns.pop(name_obj[0], None)
        self.workspaceModel.update()

    @Slot()
    @safewrapper
    def _slot_showActionStatusMessage_(self):
        action = self.sender()
        if isinstance(action, QAction):
            action.showStatusText(self)
            
    @Slot()
    @safewrapper
    def slot_exportSelectedVariablesText(self):
        indexList = self.workspaceView.selectedIndexes()

        if len(indexList) == 0:
            return

        item, varname = self._getWorkspaceVarItemAndName_(indexList[0])

        items, varnames = zip(
            *list(self._getWorkspaceVarItemAndName_(index) for index in indexList))
        
        if all([isinstance(self.workspace[v], str) for v in varnames]):
            for v in varnames:
                o = self.workspace[v]
                if strutils.is_html(o):
                    filename = "".join([v, ".html"])
                else:
                    filename = "".join([v, ".txt"])
                pio.saveText(o, filename)
        
    @Slot()
    @safewrapper
    def slot_exportSelectedVariablesAsHTML(self):
        indexList = self.workspaceView.selectedIndexes()

        if len(indexList) == 0:
            return

        item, varname = self._getWorkspaceVarItemAndName_(indexList[0])

        items, varnames = zip(
            *list(self._getWorkspaceVarItemAndName_(index) for index in indexList))
        
        if all([isinstance(self.workspace[v], str) for v in varnames]):
            for v in varnames:
                o = self.workspace[v]
                filename = "".join([v, ".html"])
                pio.saveText(o, filename)
        
    @Slot()
    @safewrapper
    def slot_exportSelectedVariablesAsMarkdown(self):
        indexList = self.workspaceView.selectedIndexes()

        if len(indexList) == 0:
            return

        item, varname = self._getWorkspaceVarItemAndName_(indexList[0])

        items, varnames = zip(
            *list(self._getWorkspaceVarItemAndName_(index) for index in indexList))
        
        if all([isinstance(self.workspace[v], str) for v in varnames]):
            for v in varnames:
                o = self.workspace[v]
                filename = "".join([v, ".md"])
                pio.saveText(o, filename)
        
    @Slot()
    @safewrapper
    def slot_exportSelectedVariablesAsReST(self):
        indexList = self.workspaceView.selectedIndexes()

        if len(indexList) == 0:
            return

        item, varname = self._getWorkspaceVarItemAndName_(indexList[0])

        items, varnames = zip(
            *list(self._getWorkspaceVarItemAndName_(index) for index in indexList))
        
        if all([isinstance(self.workspace[v], str) for v in varnames]):
            for v in varnames:
                o = self.workspace[v]
                filename = "".join([v, ".rst"])
                pio.saveText(o, filename)
        
    @Slot()
    @safewrapper
    def slot_exportSelectedVariablesAsSVG(self):
        indexList = self.workspaceView.selectedIndexes()

        if len(indexList) == 0:
            return

        item, varname = self._getWorkspaceVarItemAndName_(indexList[0])

        items, varnames = zip(
            *list(self._getWorkspaceVarItemAndName_(index) for index in indexList))
        
        if all([isinstance(self.workspace[v], str) for v in varnames]):
            for v in varnames:
                o = self.workspace[v]
                filename = "".join([v, ".svg"])
                pio.saveText(o, filename)
        

    @Slot()
    @safewrapper
    def slot_exportSelectedVariablesAsXML(self):
        indexList = self.workspaceView.selectedIndexes()

        if len(indexList) == 0:
            return

        item, varname = self._getWorkspaceVarItemAndName_(indexList[0])

        items, varnames = zip(
            *list(self._getWorkspaceVarItemAndName_(index) for index in indexList))
        
        if all([isinstance(self.workspace[v], str) for v in varnames]):
            for v in varnames:
                o = self.workspace[v]
                filename = "".join([v, ".xml"])
                pio.saveText(o, filename)

    @Slot()
    @safewrapper
    def slot_multiExportToCsv(self):
        indexList = self.workspaceView.selectedIndexes()

        if len(indexList) == 0:
            return

        item, varname = self._getWorkspaceVarItemAndName_(indexList[0])

        items, varnames = zip(
            *list(self._getWorkspaceVarItemAndName_(index) for index in indexList))
        # varnames = [self.workspaceModel.item(indexList[k].row(),0).text() for k in range(len(indexList))]

        # if all([isinstance(self.workspace[v], (dict, pd.DataFrame, pd.Series, neo.basesignal.BaseSignal, neo.SpikeTrain))] for v in varnames):
        if all([isinstance(self.workspace[v], (pd.DataFrame, pd.Series, neo.basesignal.BaseSignal, neo.SpikeTrain, np.ndarray))] for v in varnames):
            if not any([isinstance(self.workspace[v], np.ndarray) and self.workspace[v].ndim > 2 for v in varnames]):
                for v in varnames:
                    filename = "".join([v, ".csv"])
                    pio.writeCsv(self.workspace[v], fileName=filename)

    @Slot()
    @safewrapper
    def slot_exportToCsv(self):
        indexList = self.workspaceView.selectedIndexes()

        if len(indexList) == 0:
            return

        item, varname = self._getWorkspaceVarItemAndName_(indexList[0])

        if varname is None or len(varname.strip()) == 0:
            return

        # if not isinstance(self.workspace[varname], (pd.Series, pd.DataFrame, np.ndarray, dict)):
        if not isinstance(self.workspace[varname], (pd.Series, pd.DataFrame, neo.basesignal.BaseSignal, neo.SpikeTrain, np.ndarray)):
            return

        if isinstance(self.workspace[varname], np.ndarray) and self.workspace[varname].ndim > 2:
            return

        fileFilter = "CSV files (*.csv)"

        filename = "".join([varname, ".csv"])

        if sys.platform.startswith("win32"):
            options = QtWidgets.QFileDialog.Option.DontUseNativeDialog
            kw = {"options":options}
        else:
            kw = {}

        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self,
                                                            caption="Export to CSV",
                                                            filter=fileFilter,
                                                            directory=os.path.join(self.currentDir, filename),
                                                            **kw)

        if len(filename.strip()) > 0:
            pio.writeCsv(self.workspace[varname], fileName=filename)

    @Slot()
    def slot_useDataViewer(self):
        # if bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier):
        if bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.AltModifier):
            newWindow = True

        else:
            newWindow = False

        # varname = self.workspaceModel.currentItemName
        varname = self.currentVarItemName

        if varname is None:
            indexList = self.workspaceView.selectedIndexes()

            if len(indexList) == 0:
                return

            item, varname = self._getWorkspaceVarItemAndName_(indexList[0])

            if varname is None or isinstance(varname, str) and len(varname.strip()) == 0:
                return

            if varname not in self.workspace.keys():
                return

        variable = self.workspace[varname]
        vartype = type(variable)

        viewers = [v for v in self.viewers.keys() if v.__name__ ==
                   "DataViewer"]

        if len(viewers):
            viewer = viewers[0]
            if not self.viewObject(variable, varname,
                                   winType=viewer,
                                   newWindow=newWindow):
                self.console.execute(varname)
        else:
            self.console.execute(varname)

    @Slot()
    def slot_showInConsole(self):
        # if bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier):
        #     newWindow = True
        # 
        # else:
        #     newWindow = False

        # varname = self.workspaceModel.currentItemName
        varname = self.currentVarItemName

        if varname is None:
            indexList = self.workspaceView.selectedIndexes()

            if len(indexList) == 0:
                return

            item, varname = self._getWorkspaceVarItemAndName_(indexList[0])

            if varname is None or isinstance(varname, str) and len(varname.strip()) == 0:
                return

            if varname not in self.workspace.keys():
                return

            self.currentVarItem = item
            self.currentVarItemName = varname

        self.console.execute(varname)

    @Slot()
    @safewrapper
    def slot_autoSelectViewer(self):
        newWindow = bool(
            QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.AltModifier)
        askForParams = bool(
            QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier)

        # print(f"{self.__class__.__name__}.slot_autoSelectViewer askForParams = {askForParams}")

        # varname = self.workspaceModel.currentItemName
        varname = self.currentVarItemName

        if varname is None:
            indexList = self.workspaceView.selectedIndexes()

            if len(indexList) == 0:
                return

            item, varname = self._getWorkspaceVarItemAndName_(indexList[0])

            # varname = self.workspaceModel.item(indexList[0].row(),0).text()

            if varname is None or isinstance(varname, str) and len(varname.strip()) == 0:
                return

            if varname not in self.workspace.keys():
                return

            self.currentVarItem = item
            self.currentVarItemName = varname

        action = self.sender()
        actionName = action.text().replace("&", "")

        variable = self.workspace[varname]
        vartype = type(variable)

        # handler_specs = VTH.get_handler_spec(vartype)
        handler_specs = VTH.get_handler_spec(variable)
        # FIXME/BUG: 2022-12-26 22:17:07
        # this can easily get buggered if the user decides to set an action
        # name other than the viewer class name
        if len(handler_specs):
            viewers = [spec[0]
                       for spec in handler_specs if spec[1] == actionName]

            if len(viewers) == 0:
                self.console.execute(varname)

            else:
                viewer = viewers[0]

                if not self.viewObject(variable, varname, winType=viewer,
                                       newWindow=newWindow,
                                       askForParams=askForParams):
                    self.console.execute(varname)
        else:
            self.console.execute(varname)

    @Slot()
    @safewrapper
    def slot_viewSelectedVar(self):
        # if bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier):
        if bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.AltModifier):
            self.slot_viewSelectedVarInNewWindow()
            return

        varname = self.currentVarItemName

        if varname is None:
            indexList = self.workspaceView.selectedIndexes()

            if len(indexList) == 0:
                return

            item, varname = self._getWorkspaceVarItemAndName_(indexList[0])

            if varname is None:
                return

            self.currentVarItem = item
            self.currentVarItemName = varname

        # if not self.viewVar(varname, newWindow=False, useSignalViewerForNdArrays=useSignalViewerForNdArrays):
        if not self.viewVar(varname, newWindow=False):
            self.console.execute(varname)

    @Slot()
    @safewrapper
    def slot_viewSelectedVariables(self):
        indexList = self.workspaceView.selectedIndexes()
        if len(indexList) == 0:
            return

        varNames = list()

        for i in indexList:
            item, varname = self._getWorkspaceVarItemAndName_(i)
            if not self.viewVar(varname, True):
                self.console.execute(varname)

    @Slot()
    @safewrapper
    def slot_consoleDisplaySelectedVariables(self):
        indexList = self.workspaceView.selectedIndexes()

        if len(indexList) == 0:
            return

        items, varnames = zip(
            *list(self._getWorkspaceVarItemAndName_(i) for i in indexList))
        # varnames = [self.workspaceModel.item(i.row(),0).text() for i in indexList]

        for varname in varnames:
            self.console.execute(varname)

    @Slot()
    @safewrapper
    def slot_viewNDarray(self):
        r"""Displays ndarray in a TableEditor
        """
        # if bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier):
        if bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.AltModifier):
            self.slot_viewNDarrayNewWindow()
            return

        varname = self.getCurrentVarName()

        if varname is None:  # workspaceModel dit not pick it up, try to get it from workspaceView
            indexList = self.workspaceView.selectedIndexes()

            if len(indexList) == 0:
                return

            varname = self.workspaceModel.item(indexList[0].row(), 0).text()

            if varname is None:
                return

        if isinstance(self.workspace[varname], np.ndarray):
            if self.workspace[varname].ndim in (1, 2):
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
                # NOTE: to avoid clash with python's raise PyQt uses "raise_()"
                winDict[winId].raise_()

    @Slot()
    @safewrapper
    def slot_viewNDarrayNewWindow(self):
        r"""Displays ndarray in a new  TableEditor
        """
        varname = self.getCurrentVarName()
        if varname is None:
            return

        winDict = self.tableEditorWindows

        self.slot_newTableEditorWindow()
        winId = self.currentTableEditorWindowID
        winDict[winId].view(self.workspace[varname])
        winDict[winId].setTitle(varname)

    @Slot()
    @safewrapper
    def slot_viewSelectedVarInNewWindow(self):
        # if bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier):
        # useSignalViewerForNdArrays = True

        # else:
        # useSignalViewerForNdArrays = False

        varname = self.getCurrentVarName()

        if not self.viewVar(varname, newWindow=True):
            # will raise exception if varname not in workspace
            self.console.execute(varname)

    # , useSignalViewerForNdArrays=True):
    def viewVar(self, varname, newWindow=False, winType=None, 
                askForParams=False):
        r"""Displays a variable in the workspace.
        The variable is selected by its name
        """
        # print("ScipyenWindow.viewVar, newWindow:", newWindow)
        if varname in self.workspace.keys():
            if varname is None:
                return False

            obj = self.workspace[varname]

            # NOTE: 2022-12-22 09:59:02
            # The following three checks are here to avoid launching a viewer for a
            # scalar numpy array or nuemric object, or for a sequence with one element
            #
            if isinstance(obj, np.ndarray):
                if obj.size < 2 or obj.ndim == 0:
                    return False

            if isinstance(obj, numbers.Number):
                return False

            if isinstance(obj, (tuple, list, deque)) or hasattr(obj, "__iter__") or hasattr(obj, "__len__"):
                if len(obj) < 1:
                    return False

            return self.viewObject(obj, varname,
                                   winType=winType,
                                   newWindow=newWindow,
                                   askForParams=askForParams)

        return False
    
    # @Slot(QtCore.QModelIndex, QtCore.QModelIndex, "QVector<int>")
    @Slot()
    def slot_fileSystemDataChanged(self, *args, **kwargs): # TODO 2023-09-27 22:43:52 revisit this
        # print(f"{self.__class__.__name__}.slot_fileSystemDataChanged args {args} kwargs {kwargs}" )
        self._fileSystemChanged_ = True

    @safewrapper
    def enableDirectoryMonitor(self, directory:typing.Optional[typing.Union[str, pathlib.Path]]=None,
                             on:bool=True):
        # NOTE: 2023-09-27 18:02:22
        # unlink this from directory navigation in Scipyen
        # specify the directory to listen to...
        #
        # as a side effect, we allow watching multiple directories, so we should be careful !
        #
        if isinstance(directory, bool):
            on = directory
            directory = None

        if directory is None:
            directory = self.currentDir

        # NOTE: 2023-09-27 21:17:06
        # make sure we operate on pathlib.Path objects
        #
        if not isinstance(directory, (str, pathlib.Path)):
            raise TypeError(f"Expecting a directory; instead, got {type(directory).__name__}")

        if isinstance(directory, str):
            directory = pathlib.Path(directory)

        if not directory.exists() or not directory.is_dir():
            raise ValueError(f"The specified directory {directory} does not exist")

        if not directory.is_absolute():
            directory = directory.absolute()

        # print(f"{self.__class__.__name__}.enableDirectoryMonitor directory = {directory}; will monitor = {on}" )

        if not on: # => remove this directory from the monitoring system & return
            watchedDirs = self.dirFileMonitor.directories()
            # NOTE: this is if we decide to watch several directories
            if str(directory) in watchedDirs:
                self.dirFileMonitor.removePath(str(directory))
                
            self._monitoredDirsCache_.pop(str(directory), None)
            
            return
            
        if str(directory) in self.dirFileMonitor.directories():
            # do nothing if directory already watched
            scipywarn(f"{self.__class__.__name__}.enableDirectoryMonitor: The directory {print_styled(directory, 'yellow', True)} is already being watched")
        
        else:
            watchedDirs = self.dirFileMonitor.directories()
            if len(watchedDirs) > self._nMaxWatchedDirectories_:
                wDir = pathlib.Path(watchedDirs[0])
                self.dirFileMonitor.removePath(watchedDirs[0])
                self._monitoredDirsCache_.pop(wDir, None)
                
            
            # NOTE: 2023-09-27 22:10:44
            # we MUST use a dict, to capture the stat of each entry at the moment of caching!!!
            # NOTE: 2025-01-07 20:14:58 WARNING: will fail if not enough permissions !!!!
            self._monitoredDirsCache_[directory] = dict((entry, entry.stat()) for entry in directory.glob('*'))
            # self._monitoredDirsCache_[directory] = set(directory.glob('*'))
                
            
            self.dirFileMonitor.addPath(str(directory))

    def watchCurrentDirectory(self):
        if not self._isDirWatching_:
            return
        
        if self.currentDir in self.dirFileMonitor.directories():
            # do nothing if directory already watched
            scipywarn(f"{self.__class__.__name__}.watchCurrentDirectory: The directory {print_styled(self.currentDir, 'yellow', True)} is already being watched")
        
        else:
            # remove prev watched directory from the file system watcher
            # add current directory to the file system watcher
            watchedDirs = self.dirFileMonitor.directories()
            if len(watchedDirs) > self._nMaxWatchedDirectories_:
                self.dirFileMonitor.removePath(watchedDirs[0])
                
            self.dirFileMonitor.addPath(self.currentDir)
                
    @safewrapper
    @Slot()
    def _slot_monitoredFileChanged(self, *args, **kwargs):
        print(f"{self.__class__.__name__}._slot_monitoredFileChanged:\n\targs = {args}\n\t kwargs = {kwargs}\n\n")
        
    
    @safewrapper
    @Slot()
    def _slot_monitoredDirectoryContentsChanged(self, *args, **kwargs):
        r"""Called when the contents of the monitored directories have changed:
        
        • when a new file was created in the directory 
            to see this, call 'touch somefile' in a shell, to see this
        
        • when an existing file has changed (size, time stamp, etc
            to see this call 'touch somefile' in a shell once again
        
        • when an existing file has been removes 
            to see this, call 'rm somefile' in a shell to see this - WARNING be
            careful with this one
        
        In addition, the second case above will ALSO trigger the fileSystemModel
        to emit dataChanged signal, here connected to the slot_fileSystemDataChanged.
        
        Connected to self.dirFileMonitor.directoryChanged() slot
        
        WARNING: Will fail if user does nto have necessary permissions on this directory
        
    """
        #print(f"{self.__class__.__name__}._slot_monitoredDirectoryContentsChanged (from dirFileMonitor) *args {args}, **kwargs {kwargs}")
        directories = utilities.unique([pathlib.Path(d) for d in self.dirFileMonitor.directories()])
        
        for d in directories:
            if d in self._monitoredDirsCache_:
                currentItems = set(d.glob('*'))
                cachedItems = set(self._monitoredDirsCache_[d].keys())
                removedItems = cachedItems - currentItems
                newItems = currentItems - cachedItems
                changedItems = tuple(i[0] for i in self._monitoredDirsCache_[d].items() if i[0] in currentItems and i[0].stat() != i[1])
                
                if len(removedItems):
                    # txt = f"{self.__class__.__name__}._slot_monitoredDirectoryContentsChanged removedItems = {removedItems}\n"
                    # self.console.writeText(txt)
                    for i in removedItems:
                        self._monitoredDirsCache_[d].pop(i, None)
                        
                    self.sig_itemsRemovedFromMonitoredDir.emit(tuple(i for i in removedItems))
                    
                if len(newItems):
                    # txt = f"{self.__class__.__name__}._slot_monitoredDirectoryContentsChanged newItems = {newItems}\n"
                    # self.console.writeText(txt)
                    for i in newItems:
                        self._monitoredDirsCache_[d][i] = i.stat()
                        
                    self.sig_newItemsInMonitoredDir.emit(tuple(i for i in newItems))
                    
                if len(changedItems):
                    # txt = f"{self.__class__.__name__}._slot_monitoredDirectoryContentsChanged changedItems = {changedItems}\n"
                    # self.console.writeText(txt)
                    self.sig_itemsChangedInMonitoredDir.emit(changedItems)
                    for i in changedItems:
                        self._monitoredDirsCache_[d][i] = i.stat()
                
            

    def viewObject(self, obj, objname, winType=None, 
                   newWindow=False, askForParams=False):
        r"""Actually displays a python object in user's workspace.
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

        askForParams when true, prompts a dialog with viewing parameters
    (NOTE: this is viwer-specific and not fully implemented)
        """
        # TODO: 2025-05-28 14:48:40
        # implement viewing coniguration dialog for various viewers
        # currently this is only partially implemented for SignalViewer
        # TODO: accommodate new viewer types - nearly DONE via VTH

        # NOTE: 2022-12-22 09:59:02
        # The following three checks are here to avoid launching a viewer for a
        # scalar numpy array or nuemric object, or for a sequence with one element

        if isinstance(obj, np.ndarray):
            if (obj.size < 2 or obj.ndim == 0):
                return False

        if isinstance(obj, numbers.Number):
            return False

        if isinstance(obj, (tuple, list, deque)) or hasattr(obj, "__iter__") or hasattr(obj, "__len__"):
            try:
                if len(obj) < 1:
                    return False
            except:
                return False    

        if isinstance(winType, str) and winType in [v.__name__ for v in self.viewers.keys()]:
            if winType not in self.viewers.keys():
                raise ValueError("Unknown viewer type %s" % winType)

            winType = [v for v in self.viewers.keys()
                       if v.__name__ is winType][0]

        elif inspect.isclass(winType) and winType in self.viewers.keys():
            if winType not in self.viewers.keys():
                raise ValueError("Unknown viewer type %s" % winType.__name__)

        elif winType is None:
            # handler_specs = VTH.get_handler_spec(type(obj))
            handler_specs = VTH.get_handler_spec(obj)
            # print(viewers_type_list)
            if len(handler_specs) == 0:
                return False

            winType = handler_specs[0][0]

        else:
            return False
        
        # print(f"{self.__class__.__name__}.viewObject winType = {winType.__name__}")

        if len(self.viewers[winType]) == 0 or newWindow:
            # print(f"{self.__class__.__name__}.viewObject make new")
            
            win = self.newViewer(winType)
        else:
            win = self.currentViewers[winType]

            # is this win shown in the workspace viewer?
            # BUG 2023-09-16 08:59:37
            # when the workspace viewer is populated asynchronously, the below
            # query may happen before the variable name was displayed in 
            # workpace viewer, thus causing an increment (and a reasignment of symbols)
            # listedVarNames = self.workspaceModel.getDisplayedVariableNames()
            # listedWindows = [self.workspace[n] for n in listedVarNames if type(self.workspace[n]) == winType]
            
            variables = dict([item for item in self.shell.user_ns.items(
                ) if item[0] not in self.user_ns_hidden and not item[0].startswith("_")])
            
            varnames = reverse_mapping_lookup(variables, win)
            
            listedWindows = [self.workspace[n] for n in varnames if type(self.workspace[n]) == winType]
            
            if win not in listedWindows:
                # create a binding in the workspace
                win_title = winType.__name__
                win_title, counter_suffix = validate_varname(win_title, self.workspace, return_counter=True)
                self.workspace[win_title] = win
                self.workspaceModel.update()
                

        if win is None:
            return False

        win.show()  # generic way also works for maplotlib figure

        if isinstance(win, mpl.figure.Figure):
            plt.figure(win.number)  # select the mpl figure
            if askForParams:
                dlg = qd.QuickDialog(self, "Plot")
                chkb = qd.CheckBox(dlg, "Clear previous plot")
                # dlg.resize(QtCore.QSize(-1, -1))
                dlg.adjustSize()
                ret = dlg.exec_()
                if ret == 1:
                    if chkb.selection():
                        plt.clf()

            if isinstance(obj, neo.core.basesignal.BaseSignal):
                neoutils.plot_neo(obj, win)

            elif isinstance(obj, vigra.VigraArray):
                plt.plot(np.arange(obj.shape[0]), np.array(obj))
            else:
                plt.plot(obj)

            win.canvas.draw_idle()
            if isinstance(win.canvas, QtWidgets.QWidget):
                win.canvas.activateWindow()

        else:
            # , varname=objname)
            win.setData(obj, doc_title=objname, uiParamsPrompt=askForParams)
            win.activateWindow()

        return True

    def _run_loop_process_(self, fn, process_name, *args, **kwargs):
        # TODO: 2022-12-23 00:24:19
        # see EventAnalysis in scipyen_plugins for a working approach !
        # TODO : 2021-08-17 12:43:35
        # check where it is used (currently nowhere, but potentially when running
        # plugins)
        # possibly move to core.prog
        if isinstance(process_name, str) and len(process_name.strip()):
            title = "%s..." % process_name

        else:
            title = "Processing..."

        # print("_run_loop_process_ args", args)

        pdlg = QtWidgets.QProgressDialog(title, "Cancel", 0, 1000, self)

        worker = pgui.ProgressWorkerRunnable(fn, pdlg, *args, **kwargs)
        worker.signals.signal_Finished.connect(pdlg.reset)
        worker.signals.signal_Result.connect(self.slot_loop_process_result)

        if worker is not None:
            self.threadpool.start(worker)

    @Slot(object)
    @safewrapper
    def slot_loop_process_result(self, obj, name=""):
        if isinstance(name, str) and len(name.strip()):
            self.workspaceModel.bindObjectInNamespace(name, obj)
            # self.workspace[name] = obj

        else:
            self.workspaceModel.bindObjectInNamespace("result", obj)
            # self.workspace["result"] = obj

        # self.workspaceModel.update()
        # self.workspaceModel.update(from_console=False)

        self.workspaceChanged.emit()

    def _removeMenu_(self, menu):
        parentMenuOrMenuBar = menu.parent()
        if parentMenuOrMenuBar is not None:  # parent should never be None, but let's check anyway
            parentMenuOrMenuBar.removeAction(menu.menuAction())
            if type(parentMenuOrMenuBar).__name__ == "QMenu":
                if parentMenuOrMenuBar.title() != "Plugins":
                    self._removeMenu_(parentMenuOrMenuBar)

    @Slot()
    @safewrapper
    # do we "unload", "offload", or simply "forget" them?
    def slot_offloadPlugins(self):
        '''
        Removes the (sub)menus and menu items created by loading plugins.
        The only use, really, is when called by slot_reloadPlugins().
        The plugin code itself is recompiled (and reloaded) by the scipyen_plugin_loader
        if necessary.
        '''
        # NOTE: 2022-12-25 10:52:58
        # this does NOT remove the module from sys.modules!
        if len(self._ui_plugins_):
            parents = list()
            for module, moduleDict in self._ui_plugins_.items():
                if isinstance(moduleDict, dict) and len(moduleDict) > 0:
                    for func, action in moduleDict.items():
                        if inspect.isfunction(func) and isinstance(action, QAction):
                            parentMenuOrMenuBar = action.parent()
                            if isinstance(parentMenuOrMenuBar, QtWidgets.QMenu):
                                parents.append(parentMenuOrMenuBar)
                                # parentMenuOrMenuBar.removeAction(action)
                    moduleDict.clear()

            for p in parents:
                self._removeMenu_(p)

            self._ui_plugins_.clear()
            scipyen_plugin_loader.loaded_plugins.clear()  # need to clear this, too

    @Slot()
    @safewrapper
    def slot_reloadPlugins(self):
        self.slot_offloadPlugins()
        self.slot_loadPlugins()

    # TODO/FIXME 2016-04-03 00:14:47
    # make forceRecompile a configuration variable !!!
    @Slot()
    @safewrapper
    def slot_loadPlugins(self):
        ''' Asynchronously search and load of Scipyen 'plugins'
        Scipyen 'plugins' are modules in Scipyen package tree that advertise 
        module-level functions callable through for graphical user interface 
        (i.e., menus in the Scipyen Main Window).
        For details, see the documentation of the core.scipyen_plugin_loader 
        module.
        '''
        # scipywarn("plugin loading has been temporarily disabled")
        # return
        # print(f"{self.__class__.__name__}.slot_loadPlugins")
        # if self._pyinstaller_bundled_:
        #     scipyen_plugin_loader.find_bytecode_plugins()
        # else:
        #     scipyen_plugin_loader.find_plugins(self._scipyendir_, self._scipyendir_)  # calls os.walk
        scipyen_plugin_loader.find_plugins(self._scipyendir_, self._scipyendir_)  # calls os.walk
        scipyen_plugin_loader.find_plugins(self.userPluginsDirectory, self._scipyendir_, True)  # calls os.walk
        

        # NOTE: 2016-04-15 11:53:08
        # let the plugin loader just load plugin module code
        # and do the plugin initialization here

        if len(scipyen_plugin_loader.loaded_plugins) > 0:
            viewers = list()  # list of (name, class) tuples
            for module_name, module in scipyen_plugin_loader.loaded_plugins.items():
                # print(f"{self.__class__.__name__}.slot_loadPlugins: {module_name}, {module}")
                # maps module name to the tuple (module file, menu dict)
                # menu dict in turn maps a menu tree structure (a '|'-separated string) to a function defined in the plugin
                # NOTE: 2022-12-23 09:06:36
                # inject references to self and the workspace into the module,
                # as module attributes; see also NOTE: 2022-12-23 10:47:39
                # see also NOTE: 2024-05-29 14:04:11 gui/mainwindow.py
                if not hasattr(module, "mainWindow"):
                    module.__dict__["mainWindow"] = self

                if not hasattr(module, "workspace"):
                    module.__dict__["workspace"] = self.workspace

                # NOTE 2022-12-25 21:10:52
                # inspect the module for any Viewer classes and register them
                # Do this independently of installing self advertised menus (see
                # below)
                viewerClasses = list(filter(lambda x: inspect.isclass(x[1]) and prog.is_class_defined_in_module(
                    x[1], module) and self._isScipyenViewerClass_(x[1]), inspect.getmembers(module)))
                # print(f"viewer classes {viewerClasses} in module {module}")
                for viewerClass in viewerClasses:
                    self._register_viewer_class_(*viewerClass)
                    viewers.append(viewerClass)

                # NOTE: 2022-12-23 09:02:02
                # allow plugins to be intialized without advertising a menu for
                # the main window; hence, only install menus for those plugins
                # that provide a menu path via their init_scipyen_plugin
                # 
                #
                if inspect.isfunction(getattr(module, "init_scipyen_plugin", None)):
                    # NOTE: 2022-12-25 21:10:19
                    # create/update the menus as provided by the plugin module
                    menudict = collections.OrderedDict([(module.__name__, (module.__file__, module.init_scipyen_plugin()))])
                    if len(menudict) > 0:
                        # if __has_PySide6__:
                        #     print(f"slot_loadPlugins menus for {module.__name__}, menu dict: {menudict}")
                        for (k, v) in menudict.items():
                            # v[0] is the module.__file__ 
                            # we restrict to regular plugin files, by REQUIRING that
                            # this is a file TODO: 2024-05-29 17:15:26 check it exists !
                            if (isinstance(k, str) and len(k) > 0):
                                pluginMenuActions = self.installPluginMenuPySide6(k, v) if __has_PySide6__ else self.installPluginMenu(k, v)
                                # print(f"{self.__class__.__name__}.slot_loadPlugins pluginMenuActions = {pluginMenuActions}")
                                if len(pluginMenuActions):
                                    self._cachePluginActions_(module, pluginMenuActions)
                            else:
                                raise TypeError("Incompatible Plugin Key")

                    if inspect.isfunction(getattr(module, "load_ipython_extension", None)):
                        module.load_ipython_extension(self.ipkernel.shell)
                        
                    # NOTE: 2024-05-31 14:14:00
                    # make this plugin available at the console
                    # WARNING this is likely to create symbols bound to the same object
                    mname = module_name.split('.')[-1]
                    if mname not in self.workspace:
                        self.workspaceModel.bindObjectInNamespace(mname, module, hidden=True)

            if len(viewers):
                sortedViewers = sorted(viewers, key=lambda x: x[0])
                newViewerActions = self.newViewersMenu.actions()
                if len(newViewerActions) == 0:
                    for v in sortedViewers:
                        self.newViewersMenu.addAction(QtGui.QIcon.fromTheme("window"),
                            v[0], self.slot_newViewerMenuAction)
                else:
                    actions = self.newViewersMenu.actions()
                    labels = sorted(list(action.text() for action in actions))
                    extended = sorted(labels + list(v[0] for v in sortedViewers))
                    beforeAction = None
                    beforeActionLabel = None
                    for v in sortedViewers:
                        ndx = extended.index(v[0])
                        if ndx < (len(extended)-1):
                            beforeActionLabel = extended[ndx+1]

                            if beforeActionLabel in labels:
                                beforeNdx = labels.index(beforeActionLabel)
                                beforeAction = actions[beforeNdx]
                                newAction = QAction(QtGui.QIcon.fromTheme("window"),v[0])
                                newAction.triggered.connect(
                                    self.slot_newViewerMenuAction)
                                self.newViewersMenu.insertAction(
                                    beforeAction, newAction)
                            else:
                                self.newViewersMenu.addAction(QtGui.QIcon.fromTheme("window"),
                                    v[0], self.slot_newViewerMenuAction)

        # NOTE: 2016-04-03 00:25:00 - do NOT delete - keep for future reference
        # (i.e., don't make this mistake again...)
        # calling this seems to make the qt app close -- why?
        # NOTE: FIXED 2016-04-03 01:03:53 -- we call this asynchronously,
        # via Qt signal/slot mechanism (main window emits startPluginLoad at end of __init__)
        # dw = os.walk(path)

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
        if __has_PySide6__:
            if qtutils.isQObjectAlive(parent):
                parentAM = list(map(lambda a: (a.text().replace('&', ''), a.menu()), filter(lambda a: qtutils.isQObjectAlive(a), parent.actions())))
                if len(parentAM):
                    parentActionLabels, parentActionMenus = zip(*parentAM)
                
                # parentActionLabels = [i.text().replace('&', '')
                #                     for i in parent.actions()]
                # parentActionMenus = [i.menu() for i in parent.actions()]

                    if itemText in parentActionLabels:
                        return parentActionMenus[parentActionLabels.index(itemText)]
        else:
                parentAM = list(map(lambda a: (a.text().replace('&', ''), a.menu()), parent.actions()))
                if len(parentAM):
                    parentActionLabels, parentActionMenus = zip(*parentAM)
                    if itemText in parentActionLabels:
                        return parentActionMenus[parentActionLabels.index(itemText)]
                

    def _installPluginFunction_(self, f: types.FunctionType, menuItemLabel: str, 
                                parentMenu: QtWidgets.QMenu, 
                                before: typing.Optional[QAction] = None, 
                                n_outputs=None, inArgTypes=None):
        ''' Creates a QAction for calling the module-level function `f`.
        Implements the actual logic of installing individual plugin functions 
        advertised by the init_scipyen_plugin function defined in the plugin module.

        The function 'f' is wrapped in a slot that will be connected to the 
        triggered() signal emited by the appropriate menu item.

        Parameters:
        ===========
        f: the module-level function object to be called by a dynamically-created 
            menu action

        menuItemLabel: str, the text of the menu action

        parentMenu: the QMenu where the QAction will be created.

        before: QAction. Optional, default is None.
            When present, the new action will be inserted in the parent menu 
                before this one (useufl to have the actions sorted e.g., by name)
            When None (the default) the new action willl be appended to the end
                of the parnet menu

        '''
        # if "simple_plugin" in f.__module__:
        #     print(f"{self.__class__.__name__}._installPluginFunction_:")
        #     print(f"\t f = {f}")
        #     print(f"\t menuItemLabel = {menuItemLabel}")
        #     print(f"\t parentMenu = {parentMenu}")
        #     print(f"\t before = {before}")
        # NOTE: TODO: in python 3: use inspect.getfullargspec(f)
        # to parse *args, **kwargs syntax !!!
        argSpec = inspect.getfullargspec(f)

        arg_names = argSpec.args
        arg_defaults = argSpec.defaults
        var_args = argSpec.varargs

        kw_args = argSpec.varkw

        # NOTE: 2016-04-17 15:49:08 funcargs are mostly useful to get return annotation if present
        # I found inspect.getfullargspec (or better, inspect.getfullargspec in python 3) more
        # useful to get positional argument list
        if (n_outputs is None or inArgTypes is None):
            if hasattr(f, '__annotations__'):
                sig = inspect.signature(f)

                if inArgTypes is None:
                    # arg_param_names = sig.parameters.keys() #not very useful to get the parameter types !!!

                    # NOTE: 2016-04-17 16:32:00
                    # this will raise KeyError if annotations is incomplete;
                    # however if an annotation is badly formed (e.g. it has a
                    # list or tuple, or None, or anything else in ) the _inputPrompter_
                    # will raise ValueError on the input Type
                    inArgTypes = [f.__annotations__[i]
                                  for i in argSpec.args]  # simple !

                    # print(f"_installPluginFunction_ {f.__module__}.{f.__name__} inArgTypes {inArgTypes}")

                if (n_outputs is None or n_outputs == 0):
                    try:
                        ra = sig.return_annotation
                        if ra != sig.empty:
                            if isinstance(ra, str):
                                n_outputs = 1
                            elif isinstance(ra, (tuple, list)):
                                n_outputs = len(sig.return_annotation)
                            else:
                                raise ValueError(
                                    'Incompatible value in return annotation')
                        else:
                            n_outputs = 0
                    finally:
                        n_outputs = 0
                        # pass

        # NOTE 2016-04-17 16:06:29 code taken from prompt_f in _inputPrompter_
        # and from slot_wrapPluginFunction decorator, in order to keep the
        # decorator's code small and tractable
        if inArgTypes is not None and (isinstance(inArgTypes, (tuple, list)) and len(inArgTypes) > 0) or (isinstance(inArgTypes, type) or (isinstance(inArgTypes, str) and inArgTypes == '~')):
            # cover the case where argument type is given as a single type
            if isinstance(inArgTypes, type):
                arg_types = (inArgTypes,)
            elif type(inArgTypes) is str and inArgTypes == '~':
                arg_types = (inArgTypes,)
            else:  # leave it as a tuple
                arg_types = inArgTypes

        else:
            arg_types = inArgTypes

        if (arg_defaults is not None and len(arg_names) > len(arg_defaults)):
            defs = [None for k in range(len(arg_names))]
            defs[(len(arg_names)-len(arg_defaults)):] = arg_defaults
            arg_defaults = defs
            del defs

        elif arg_defaults is None:
            arg_defaults = [None for k in range(len(arg_names))]

        if isinstance(before, QAction):
            newAction = QAction(menuItemLabel)
            parentMenu.insertAction(before, newAction)
        else:
            newAction = parentMenu.addAction(menuItemLabel)
            
        if parentMenu == self.menuBar():
            parentMenu.update()

        newAction.triggered.connect(self.slot_wrapPluginFunction(
            f, n_outputs, arg_types, arg_names, arg_defaults, var_args, kw_args))

        return newAction
    
    def installPluginMenuPySide6(self, pname, v):
        '''Installs a GUI menu for the  plugin named pname.

        Parameters:
        ===========

        pname: the plugin's module name

        v: a tuple (module file, pluign menu dict), where:
            module file (v[0]) — string wih the absolute pathname of the plugin module source file
            plugin menu dict (v[1]) — mapping of key ↦ value:, a module-level function or a 
            tuple of functions.

            When v[1] is a mapping (i.e., dict-like) the key ↦ value are as 
            follows:

            • key is a menu path represented either as a single string 
                containing names of menu tree items texts separated by '|' 
                (from left to right: top menu rooted at the menu bar, to the 
                deepest submenu, rooted at the menu bar of the Scipyen main window)

                Example: "File|Open|Special" will:

                1) generate a "File" menu in the menu bar (if it does 
                    not exist)

                2) add a submenu "Open" (if it does not exist)

                3.a) if the key is maped to a module-level function (see
                    below) then adds a menu item (action - basically a 
                    QAction) named "Special" which will, when
                    triggered, will call the module-level function
                    to which this key is mapped.

                3.b) if the key is mapped to a sequence of module-level
                    functions defined in the plugin's module, then adds
                    a submenu named "Special", which will be populated 
                    with QActions each bearing the name of the function
                    in the sequence (and when triggered will call that
                    function)

            • value is either:
                ∘ a single module-level function defined inside the 
                plugin's module; this function will be executed when the 
                menu action created using the last menu item name element
                in the 'key' is triggered.

                ∘ a sequence of module-level functions defined inside the
                plugin's module; in this case, the last menu item element in 
                the key will generate a deep submenu populated with QActions
                named after the names of the functions in this sequence.

                When v[1] is a module-level function, this function must be
                defined in the plugin's module and a QAction triggering it will 
                be created directly inside the menu bar (i.e., top level). This
                QAction will be named after the function's name.

                When v[1] is a sequence (tuple, list) of module-level functions, 
                these functions must be defined in the plugin's module and a 
                QAction will be created for each function at top level (i.e. 
                directly in the menu bar). The function will give the name of 
                the associated QAction which will call the function when 
                triggered.

            NOTE: This mapping is supplied by the init_scipyen_plugin()
            function defined inside the plugin's module. If such function
            does NOT exist, then the plugin, although loaded, will not
            be accessible via menu items in the main window's menu bar.

        '''
        from gui import guiutils
        pluginMenuActions = list()
        
        # menuBarTree = guiutils.getMenuActionsTree(self.menuBar())
        
        # if "simple_plugin" in v[0]:
        #     print(f"{self.__class__.__name__}.installPluginMenu: v[1] = {v[1]}")

        if isinstance(v[1], dict) and len(v[1]) > 0:  # the nested dict
            # the plugin's init_scipyen_plugin function outputs a mapping
            # of a str or sequence of str, to a function or sequence of functions
            # there can be more than one such mappings
            for mp, ff in v[1].items():
                menuPathList = list()
                # iterate over keys #print(mp)
                if isinstance(mp, str) and len(mp.strip()) > 0:
                    menuPathList = mp.split('|')
                else:
                    continue
                
                pMenu = self.menuBar()
                for k, p in enumerate(menuPathList):
                    action = self._findAction_(pMenu, p)
                    if action: # action found pMenu[0]
                        if action.menu(): # action has menu
                            # if p is the last in menuPath, then create action directly
                            # else, create submenu
                            pass
                        else:
                            # if p is the last in menuPathList, then ...
                            pass
                        
                        
                    # actionNames = list(map(lambda a: a.text().replace("&", ""), self.menuBar().actions()))
                    # if p in actionNames:
                    #     action = 
                    # if p in menuBarTree:
                    #     action, branch = menuBarTree[p]
                        
                        
                
#                 # ### BEGIN legacy pyqt5 code
# 
#                 parentMenu = self.menuBar()
#                 currentMenu = None
# 
#                 for item in menuPathList:
#                     currentMenu = self._locateMenuByItemText_(parentMenu, item)
#                     # ok = False
#                     # try:
#                     #     currentMenu = self._locateMenuByItemText_(parentMenu, item)
#                     #     ok = True
#                     # except:
#                     #     currentMenu = None
#                     #     traceback.print_exc()
#                     # if not ok:
#                     #     continue
#                     if qtutils.isQObjectAlive(parentMenu):
#                         siblingActionLabels = list(map(lambda a: a.text().replace('&', ''), filter(lambda a: qtutils.isQObjectAlive(a), parentMenu.actions())))
#                         # print(f"item {item}, siblingActionLabels: {siblingActionLabels}")
#                         if currentMenu is None:
#                             # last item is the menu item (action)
#                             if item == menuPathList[-1]:
#                                 if item in siblingActionLabels:  # avoid name clashes
#                                     item = ' '.join(
#                                         [item, "(", ff.__module__, ")"])
# 
#                                 beforeAction = None
#                                 beforeActionLabel = None
#                                 if parentMenu != self.menuBar():
#                                     actionLabels = [item] + siblingActionLabels
#                                     actionLabels = sorted(actionLabels)
#                                     ndx = actionLabels.index(item)
#                                     if ndx < (len(actionLabels) - 1):
#                                         beforeActionLabel = actionLabels[ndx+1]
# 
#                                     if isinstance(beforeActionLabel, str) and beforeActionLabel in siblingActionLabels:
#                                         beforeNdx = siblingActionLabels.index(
#                                             beforeActionLabel)
#                                         beforeAction = parentMenu.actions()[
#                                             beforeNdx]
#                                         
#                                 # else:
#                                 #     parentMenu.
# 
#                                 if inspect.isfunction(ff):
#                                     menuAction = self._installPluginFunction_(
#                                         ff, item, parentMenu, before=beforeAction)
#                                     # if "simple_plugin" in v[0]:
#                                     #     print(f"menuAction: {menuAction}")
#                                     if isinstance(menuAction, QAction):
#                                         pluginMenuActions.append((menuAction, ff))
# 
#                                 elif isinstance(ff, (tuple, list)):
#                                     if len(ff) > 1:
#                                         newMenu = parentMenu.addMenu(item)
#                                         for f in ff:
#                                             if inspect.isfunction(f):
#                                                 menuAction = self._installPluginFunction_(
#                                                     f, f.__name__, newMenu)
#                                                 if isinstance(menuAction, QAction):
#                                                     pluginMenuActions.append(
#                                                         (menuAction, f))
#                                             else:
#                                                 raise TypeError(
#                                                     "function object expected")
#                                     else:
#                                         menuAction = self._installPluginFunction_(
#                                             ff[0], item, parentMenu)
#                                         if isinstance(menuAction, QAction):
#                                             pluginMenuActions.append(
#                                                 (menuAction, ff[0]))
# 
#                                 else:
#                                     raise TypeError(
#                                         " a function object or a list of function objects was expected")
#                             else:
#                                 parentMenu = parentMenu.addMenu(item)
#                                 continue
#                         else:
#                             continue
# 
#                     else:
#                         if qtutils.isQObjectAlive(currentMenu):
#                             parentMenu = currentMenu
#                         else:
#                             continue
#                 # ### END   legacy pyqt5 code
        # else:
        #     # the plugin's init_scipyen_plugin function does not advertise a
        #     # menupath ⇒ use the plugin module name as submenu of a canonical
        #     # Plugins menu
        #     ff = v[1]
        #     pluginsMenu = self._locateMenuByItemText_(
        #         self.menuBar(), "Plugins")
        #     if pluginsMenu is None:
        #         pluginsMenu = self.menuBar().addMenu("Plugins")
        # 
        #     # if 'function' in type(v[1]).__name__:
        #     if inspect.isfunction(ff):
        #         newMenu = pluginsMenu.addMenu(pname)
        # 
        #         menuAction = self._installPluginFunction_(
        #             ff, ff.__name__, newMenu)
        #         if isinstance(menuAction, QAction):
        #             pluginMenuActions.append((menuAction, ff))
        # 
        #     elif isinstance(ff, (tuple, list)):
        #         newMenu = pluginsMenu.addMenu(pname)
        #         if len(ff) == 1:
        #             # if 'function' in type(ff[0]).__name__:
        #             if inspect.isfunction(ff[0]):
        #                 menuAction = self._installPluginFunction_(
        #                     ff[0], ff[0].__name__, newMenu)
        #                 if isinstance(menuAction, QAction):
        #                     pluginMenuActions.append((menuAction, ff[0]))
        #             else:
        #                 raise TypeError("function object expected")
        # 
        #         elif len(ff) > 1:
        #             for f in ff:
        #                 # if 'function' in type(f).__name__:
        #                 if inspect.isfunction(f):
        #                     menuAction = self._installPluginFunction_(
        #                         f, f.__name__, newMenu)
        #                     if isinstance(menuAction, QAction):
        #                         pluginMenuActions.append((menuAction, f))
        #                 else:
        #                     raise TypeError("function object expected")

        return pluginMenuActions
    
    def _findAction_(self, w:QtWidgets.QWidget, name:str):
        actions = w.actions()
        if len(actions) == 0:
            return
        
        actionNames = list(map(lambda a: a.text().replace("&",""), actions))
        if name in actionNames:
            return(actions[actionNames.index(name)])
        
    
    def _createSubMenuOrAction_(self, parent:typing.Union[QtWidgets.QMenuBar, QtWidgets.QMenu],
                    name:str, asMenu:bool=False, before:typing.Optional[QAction]=None,
                    ) -> QAction | QtWidgets.QMenu | None:
        if not isinstance(parent, (QtWidgets.QMenuBar, QtWidgets.QMenu)):
            return
        
        if isinstance(parent, QtWidgets.QMenuBar):
            menu = QtWidgets.QMenu(name, self)
            if isinstance(before, QAction):
                action = parent.insertMenu(before, menu)
            else:
                action = parent.addMenu(menu)
                
            return menu
        
        else:
            if asMenu:
                menu = QtWidgets.QMenu(name, self)
                if isinstance(before, QAction):
                    action = parent.insertMenu(before, menu)
                else:
                    action = parent.addMenu(menu)
                return menu
            else:
                action = QAction()

    def installPluginMenu(self, pname, v):
        '''Installs a GUI menu for the  plugin named pname.

        Parameters:
        ===========

        pname: the plugin's module name

        v: a tuple with two elements:
            v[0] is a string wih the absolute pathname of the plugin module
            v[1] is a mapping of key ↦ value, a module-level function or a 
            tuple of functions.

            When v[1] is a mapping (i.e., dict-like) they key ↦ value are as 
            follows:

            • key is a menu path represented either as a single string 
                containing names of menu tree items texts separated by '|' 
                (from left to right: top menu to the deepest submenu, and 
                 rooted at the menu bar of the Scipyen main window)

                Example: "File|Open|Special" will:

                1) generate a "File" menu in the menu bar (if it does 
                    not exist)

                2) add a submenu "Open" (if it does not exist)

                3.a) if the key is maped to a module-level function (see
                    below) then adds a menu item (action - basically a 
                    QAction) named "Special" which will, when
                    triggered, will call the module-level function
                    to which this key is mapped.

                3.b) if the key is mapped to a sequence of module-level
                    functions defined in the plugin's module, then adds
                    a submenu named "Special", which will be populated 
                    with QActions each bearing the name of the function
                    in the sequence (and when triggered will call that
                    function)

            • value is either:
                ∘ a single module-level function defined inside the 
                plugin's module; this function will be executed when the 
                menu action created using the last menu item name element
                in the 'key' is triggered.

                ∘ a sequence of module-level functions defined inside the
                plugin's module; in this case, the last kenu item element in 
                the key will generate a deep submenu populated with QActions
                named after the names of the functions in this sequence.

                When v[1] is a module-level function, this function must be
                defined in the plugin's module and a QAction triggering it will 
                be created directly inside the menu bar (i.e., top level). This
                QAction will be named after the function's name.

                When v[1] is a sequence (tuple, list) of module-level functions, 
                these functions must be defined in the plugin's module and a 
                QAction will be created for each function at top level (i.e. 
                directly in the menu bar). The function will give the name of 
                the associated QAction which will call the function when 
                triggered.

            NOTE: This mapping is supplied by the init_scipyen_plugin()
            function defined inside the plugin's module. If such function
            does NOT exist, then the plugin, although loaded, will not
            be accessible via menu items in the main window's menu bar.

        '''
        pluginMenuActions = list()
        
        # if "simple_plugin" in v[0]:
        #     print(f"{self.__class__.__name__}.installPluginMenu: v[1] = {v[1]}")

        if isinstance(v[1], dict) and len(v[1]) > 0:  # the nested dict
            # the plugin's init_scipyen_plugin function outputs a mapping
            # of a str or sequence of str, to a function or sequence of functions
            # there can be more than one such mappings
            for mp, ff in v[1].items():
                # iterate over keys #print(mp)
                if isinstance(mp, str) and len(mp.strip()) > 0:
                    menuPathList = mp.split('|')
                else:
                    continue

                parentMenu = self.menuBar()
                currentMenu = None

                for item in menuPathList:
                    currentMenu = self._locateMenuByItemText_(parentMenu, item)
                    # ok = False
                    # try:
                    #     currentMenu = self._locateMenuByItemText_(parentMenu, item)
                    #     ok = True
                    # except:
                    #     currentMenu = None
                    #     traceback.print_exc()
                    # if not ok:
                    #     continue
                    siblingActionLabels = list(map(lambda a: a.text().replace('&', ''), parentMenu.actions()))
                    # print(f"item {item}, siblingActionLabels: {siblingActionLabels}")
                    if currentMenu is None:
                        # last item is the menu item (action)
                        if item == menuPathList[-1]:
                            if item in siblingActionLabels:  # avoid name clashes
                                item = ' '.join(
                                    [item, "(", ff.__module__, ")"])

                            beforeAction = None
                            beforeActionLabel = None
                            if parentMenu != self.menuBar():
                                actionLabels = [item] + siblingActionLabels
                                actionLabels = sorted(actionLabels)
                                ndx = actionLabels.index(item)
                                if ndx < (len(actionLabels) - 1):
                                    beforeActionLabel = actionLabels[ndx+1]

                                if isinstance(beforeActionLabel, str) and beforeActionLabel in siblingActionLabels:
                                    beforeNdx = siblingActionLabels.index(
                                        beforeActionLabel)
                                    beforeAction = parentMenu.actions()[
                                        beforeNdx]
                                    
                            # else:
                            #     parentMenu.

                            if inspect.isfunction(ff):
                                menuAction = self._installPluginFunction_(
                                    ff, item, parentMenu, before=beforeAction)
                                # if "simple_plugin" in v[0]:
                                #     print(f"menuAction: {menuAction}")
                                if isinstance(menuAction, QAction):
                                    pluginMenuActions.append((menuAction, ff))

                            elif isinstance(ff, (tuple, list)):
                                if len(ff) > 1:
                                    newMenu = parentMenu.addMenu(item)
                                    for f in ff:
                                        if inspect.isfunction(f):
                                            menuAction = self._installPluginFunction_(
                                                f, f.__name__, newMenu)
                                            if isinstance(menuAction, QAction):
                                                pluginMenuActions.append(
                                                    (menuAction, f))
                                        else:
                                            raise TypeError(
                                                "function object expected")
                                else:
                                    menuAction = self._installPluginFunction_(
                                        ff[0], item, parentMenu)
                                    if isinstance(menuAction, QAction):
                                        pluginMenuActions.append(
                                            (menuAction, ff[0]))

                            else:
                                raise TypeError(
                                    " a function object or a list of function objects was expected")
                        else:
                            parentMenu = parentMenu.addMenu(item)
                            continue
                    else:
                        parentMenu = currentMenu
                        continue
        else:
            # the plugin's init_scipyen_plugin function does not advertise a
            # menupath ⇒ use the plugin module name as submenu of a canonical
            # Plugins menu
            ff = v[1]
            pluginsMenu = self._locateMenuByItemText_(
                self.menuBar(), "Plugins")
            if pluginsMenu is None:
                pluginsMenu = self.menuBar().addMenu("Plugins")

            # if 'function' in type(v[1]).__name__:
            if inspect.isfunction(ff):
                newMenu = pluginsMenu.addMenu(pname)

                menuAction = self._installPluginFunction_(
                    ff, ff.__name__, newMenu)
                if isinstance(menuAction, QAction):
                    pluginMenuActions.append((menuAction, ff))

            elif isinstance(ff, (tuple, list)):
                newMenu = pluginsMenu.addMenu(pname)
                if len(ff) == 1:
                    # if 'function' in type(ff[0]).__name__:
                    if inspect.isfunction(ff[0]):
                        menuAction = self._installPluginFunction_(
                            ff[0], ff[0].__name__, newMenu)
                        if isinstance(menuAction, QAction):
                            pluginMenuActions.append((menuAction, ff[0]))
                    else:
                        raise TypeError("function object expected")

                elif len(ff) > 1:
                    for f in ff:
                        # if 'function' in type(f).__name__:
                        if inspect.isfunction(f):
                            menuAction = self._installPluginFunction_(
                                f, f.__name__, newMenu)
                            if isinstance(menuAction, QAction):
                                pluginMenuActions.append((menuAction, f))
                        else:
                            raise TypeError("function object expected")

        return pluginMenuActions
    
    def _crawl_plugin_UI_menu(self, act:QAction) -> str:
        if not isinstance(act, QAction):
            return str()
        menu_path = deque()
        
        menu_path.append(act.text().replace('&', ''))
        
        while act is not None:
            act = act.parent()
            if isinstance(act, QtWidgets.QMenu):
                menu_path.appendleft(act.title().replace('&',''))
                
            else:
                break
            
        return " / ".join(menu_path)
    
    def getPluginModule(self, plugin_name:str) -> typing.Optional[types.ModuleType]:
        if plugin_name not in self.pluginNames:
            scipwarn(f"Plugin module {print_styled(plugin_name, 'red', True)} not found")
            return 
        
        found = [m for m in self.pluginModules if m.__name__ == plugin_name]
        # print(f"{self.__class__.__name__}.getPluginModule: found {len(found)} modules with name {plugin_name}")
        if len(found):
            return found[0]
    
    def getMenusForUIPlugin(self, plugin_name:str) -> tuple:
        r"""Returns the menu path ↦ plugin function mappigns for the specified module.
        For information about installed plugins see the following attributes,
        properties or methods:
        • plugins
        • pluginModules
        • pluginNames
        • UIPlugins
        • UIPluginMenus
        • UIPluginNames
        """
        if not isinstance(plugin_name, str) or len(plugin_name.strip()) == 0:
            return
        
        if plugin_name not in self.UIPluginNames:
            scipywarn(f"The module named {plugin_name} is not a loaded UI plugin")
            return
        
        plugins_ui = tuple(tuple(f"{self._crawl_plugin_UI_menu(iv)} -> {ik.__name__}" for ik,iv in i.items()) for k,i in self._ui_plugins_.items() if plugin_name == k.__name__)
        
        return plugins_ui if len(plugins_ui)>1 else plugins_ui[0]
        

    def _cachePluginActions_(self, pluginModule, pluginMenuActions):
        if inspect.ismodule(pluginModule):
            if pluginModule not in self._ui_plugins_:
                self._ui_plugins_[pluginModule] = dict()

            for (menuAction, pluginFunction) in pluginMenuActions:
                self._ui_plugins_[pluginModule][pluginFunction] = menuAction

    def _isScipyenViewerClass_(self, x: typing.Type):
        if not inspect.isclass(x):
            warnings.warn(f"Expecting a class; got {type(x).__name__} instead")
            return False
        return scipyenviewer.ScipyenViewer in inspect.getmro(x)

    def _register_viewer_class_(self, name: str, x: typing.Type):
        if not inspect.isclass(x):
            warnings.warn(f"Expecting a class; got {type(x).__name__} instead")
            return False
        
        # print(f"{self.__class__.__name__}._register_viewer_class_({name}, {x})")

        # NOTE: 2022-12-25 21:43:43
        # the check if this is a ScipyenViewer descendant is done in _isScipyenViewerClass_
        # gui_viewers.add(x)
        self.workspaceModel.bindObjectInNamespace(name, x, hidden=True)
        # self.user_ns_hidden[name] = x
        # self.workspace[name] = x
        self.viewers[x] = list()
        self.currentViewers[x] = None
        # NOTE: 2022-12-25 23:17:47
        # to prevent re-sorting the newViewersMenu each time, a new view action
        # is added in slot_loadPlugins

        # FIXME/TODO: 2022-12-31 12:39:25
        # what if the viewer is already registered?
        if hasattr(x, "viewer_for_types"):
            action_name = getattr(x, "view_action_name", None)
            if not isinstance(action_name, str) or len(action_name.strip()) == 0:
                action_name = x.__name__

            if isinstance(x.viewer_for_types, dict) and len(x.viewer_for_types):
                for k,v in x.viewer_for_types.items():
                    if (isinstance(k, type) or prog.is_predicate(k)) and isinstance(v, int):
                            VTH.default_handlers[x] = {
                                "action": action_name, "types": x.viewer_for_types}
                            VTH.gui_handlers[x] = {
                                "action": action_name, "types": x.viewer_for_types}
                            
                # if all(isinstance(k, type) and isinstance(v, int) for k, v in x.viewer_for_types.items()):
                #     VTH.default_handlers[x] = {
                #         "action": action_name, "types": x.viewer_for_types}
                #     VTH.gui_handlers[x] = {
                #         "action": action_name, "types": x.viewer_for_types}

            elif isinstance(x.viewer_for_types, (tuple, list)) and len(x.viewer_for_types) and all((isinstance(v, type) or prog.is_predicate(v)) for v in x.viewer_for_types):
                viewer_for_types = dict((t, 0) for t in x.viewer_for_types)
                VTH.default_handlers[x] = {
                    "action": action_name, "types": viewer_for_types}
                VTH.gui_handlers[x] = {
                    "action": action_name, "types": viewer_for_types}
                
    def _qt_checkPermissions(self, Qt):
        pass
                

class WindowEventFilter(QtCore.QObject):
    def __init__(self, mpl_fig, parent=None):
        super().__init__(parent=parent)
        self.fig = mpl_fig
        if isinstance(parent, ScipyenWindow):
            self.scipyenWindow = parent
        else:
            self.scipyenWindow = None

    def eventFilter(self, obj: QtCore.QObject, evt: QtCore.QEvent):
        if evt.type() in (QtCore.QEvent.FocusIn, QtCore.QEvent.WindowActivate, QtCore.QEvent.Show):
            if self.scipyenWindow is not None:
                if isinstance(self.fig, (mpl.figure.Figure, QtWidgets.QMainWindow)):
                    self.scipyenWindow.raiseWindow(self.fig)

        return False  # do not block the event; pass it on to obj



