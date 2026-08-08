# __scipyen_plugin__
# $Id: ${curvefittingtool} $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later


r""" Curve fitting plugin
"""

# TODO: 2026-02-09 12:45:17 FIXME
# CLEAR UP THE IMPORTS AND OTHER STUFF COPIED OVER FROM DATAVIEWER

#### BEGIN core python modules
from __future__ import print_function

import os, sys, warnings, types, traceback, itertools, inspect
import typing, dataclasses, numbers
#### END core python modules

#### BEGIN 3rd party modules
import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, )
from qtpy.QtCore import (Signal, Slot, Property,)
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
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

    from qtpy import sip
    from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True

# __has_qtdbus__ = False
# try:
#     from qtpy import QtDBus
#     __has_qtdbus__ = True
# except:
#     __has_qtdbus__ = False

# from pyqtgraph import (DataTreeWidget, TableWidget, )

import neo
if neo.__version__ >= '0.13.0':
    from neo.core.objectlist import ObjectList as NeoObjectList
import quantities as pq
import numpy as np
import pandas as pd
import vigra
# BEGIN matplotlib modules
import matplotlib as mpl

if __has_PyQt6__ or __has_PySide6__: # still doesn't seem to work properly? see NOTE: 2025-06-22 22:38:23 in ScipyenWindow.newViewer(…)
    mpl.use("qtagg")
else:
    mpl.use("qt5agg")

from matplotlib._pylab_helpers import Gcf as Gcf
import matplotlib.mlab as mlb
import matplotlib.pyplot as plt

# ### BEGIN NOTE: 2026-05-05 23:00:47
# these below not needed because they are exec'ed at mainwindow load?
# mpl.rcParams["savefig.format"] = "svg"
# mpl.rcParams["xtick.direction"] = "in"
# mpl.rcParams["ytick.direction"] = "in"
# mpl.rcParams["svg.fonttype"]="none"

# # NOTE: 2017-08-24 22:48:45
# # required to enable interaction with matplotlib plots
# plt.ion()
# ### END   NOTE: 2026-05-05 23:00:47

# END configure matplotlib
#### END 3rd party modules

#### BEGIN scipyen.core modules
from core import datatypes

import imaging.axiscalibration
from imaging.axiscalibration import AxesCalibration

import imaging.scandata
from imaging.scandata import (ScanData, AnalysisUnit)

from core.triggerprotocols import TriggerProtocol
from core.triggerevent import (TriggerEvent, TriggerEventType)

import core.datasignal
from core.datasignal import (DataSignal, IrregularlySampledDataSignal)

from core import (
    xmlutils, strutils, neoutils
    )

from core.workspacefunctions import validate_varname

from core.utilities import NestedFinder

from core.prog import (safewrapper, safeguiwrapper, scipywarn)

from core.traitcontainers import (DataBag, DataBagTraitsObserver,)
from core.scipyendataclasses import ScipyenDataclass
from core.scipyen_config import markConfigurable

#### END scipyen.core modules

#### BEGIN scipyen.gui modules
from gui.workspacegui import WorkspaceGuiMixin
from gui.scipyenviewer import ScipyenViewer #, ScipyenFrameViewer
from gui.signalviewer import SignalViewer
from gui import quickdialog
from gui.itemslistdialog import ItemsListDialog
from gui.pictgui import WorkerThread
# from gui.widgets.datatreeview import DataTreeView
from gui.itemmodels.roles import *
from gui.widgets.modelfittingwidget import ModelFittingWidget

from core import models
from core import curvefitting as crvf


# from . import resources_rc
# from . import icons_rc
#### END scipyen.gui modules

if "darwin" in sys.platform:
    altKeyDescr = "<Option>"
    ctrlKeyDescr = "<Command>"
else:
    altKeyDescr = "<ALT>"
    ctrlKeyDescr = "<CTRL>"

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

try:
    from gui.curvefittingtool_ui import Ui_CurveFittingWindow

except:
    _curvefittingwindow_ui_file = "curvefittingtool.ui"

    if __has_PyQt6__ or __has_PySide6__:
        # Form class,        Base class
        Ui_CurveFittingWindow, _ = loadUiType(os.path.join(__module_path__, _curvefittingwindow_ui_file))

    else:
        # Form class,        Base class
        Ui_CurveFittingWindow, _ = loadUiType(os.path.join(__module_path__, _curvefittingwindow_ui_file),
                                                        from_imports=True, import_from="gui")


class CurveFittingTool(QtWidgets.QMainWindow, Ui_CurveFittingWindow, WorkspaceGuiMixin):
    viewer_for_types = tuple()
    def __init__(self, data: typing.Optional[np.ndarray] = None,
                 modelFunction:typing.Optional[typing.Callable] = None,
                 parent=None):
        super().__init__(parent=parent)
        super(Ui_CurveFittingWindow, self).__init__()
        WorkspaceGuiMixin.__init__(self, parent=parent)
        # self._fittingWidget_ = ModelFittingWidget(parent=self)
        if isinstance(data, np.ndarray) and datatypes.is_vector(data):
            self._data_ = data
        else:
            self._data_ = None

        self._modelFunctions_ = dict(map(lambda v: (v.title, v), filter(lambda i: models.isModelFunction(i), models.__dict__.values())))
        if models.isModelFunction(modelFunction):
            self._currentModelFunction_ = modelFunction
            if self._currentModelFunction_.title not in self._modelFunctions_:
                self._modelFunctions_[self._currentModelFunction_.title] = self._currentModelFunction_
        else:
            self._currentModelFunction_ = None

        self._configureUI_()

        self.setWindowTitle("Curve Fitting Tool")
        self.waveViewer = SignalViewer(parent=self, appWindow=self)

    def _configureUI_(self):
        self.setupUi(self)
        modelNames = list(self._modelFunctions_.keys())
        currentNdx = 0
        if models.isModelFunction(self._currentModelFunction_) and self._currentModelFunction_.title in self._modelFunctions_:
            currentNdx = modelNames.index(self._currentModelFunction_.title)
        self.modelFunctionsComboBox.addItems(modelNames)
        self.modelFunctionsComboBox.setCurrentIndex(currentNdx)
        self._currentModelFunction_ = self._modelFunctions_[modelNames[self.modelFunctionsComboBox.currentIndex()]]
        self.modelFunctionsComboBox.currentIndexChanged.connect(self._slot_modelFunctionChanged)

        # TODO 2026-05-06 10:48:08
        # code to open curve data from pickles, HDF5, spreadsheets
        # until this is ready, hide the openDataPushButton
        self.openDataPushButton.setVisible(False) # TODO TODO TODO

        self.importDataPushButton.clicked.connect(self._slot_importData)

        self.plotDataPushButton.setEnabled(isinstance(self._data_, np.ndarray))
        self.plotDataPushButton.clicked.connect(self._slot_plotSourceData)

        # self.fittingWidget = ModelFittingWidget(parent=self)
        # self.fittingWidget.waveViewer = self.waveViewer
        try:
            self.fittingWidget.setModel(self._currentModelFunction_)
        except:
            traceback.print_exc()
        self.fittingWidget.sig_waveformReady.connect(self._slot_plotWaveforms)
        if isinstance(self._data_, np.ndarray) and datatypes.is_vector(self._data_):
            self.fittingWidget.setData(self._data_)

    @Slot()
    def _slot_plotSourceData(self):
        if isinstance(self._data_, np.ndarray):
            self.waveViewer.view(self._data_)

    @Slot(object)
    def _slot_plotWaveforms(self, obj: np.ndarray):
        # print(f"{self.__class__.__name__}._slot_plotWaveforms({type(obj)})")
        if isinstance(self._data_, (neo.AnalogSignal, DataSignal)):
            if isinstance(obj, (neo.AnalogSignal, DataSignal)):
                curves = neoutils.concatenate_signals(self._data_, obj)
                # print(f"\n\tcurves ->
                if curves is not None:
                    self.waveViewer.view(curves)
        elif isinstance(self._data_, np.ndarray):
            if isinstance(obj, np.ndarray):
                curves = np.hstack([self._data_, obj])
                if curves is not None:
                    self.waveViewer.view(curves)
            elif isinstance(obj, (neo.AnalogSignal, DataSignal)):
                x = obj.times
                y = np.hstack([self._data_, obj.magnitude])
                curves = DataSignal(y, times = x, domain_units = x.units, units = obj.units)
                if curves is not None:
                    self.waveViewer.view(curves)

        else:
            self.waveViewer.view(obj)

    @Slot(int)
    def _slot_modelFunctionChanged(self, value: int):
        if value < len(self._modelFunctions_):
            self._currentModelFunction_ = self._modelFunctions_[list(self._modelFunctions_.keys())[value]]
            try:
                self.fittingWidget.setModel(self._currentModelFunction_)
            except:
                traceback.print_exc()

    @Slot()
    def _slot_importData(self):
        imported = self.importWorkspaceData(np.ndarray, predicate=datatypes.is_vector)
        if len(imported):
            self._data_ = imported[0]
            self.fittingWidget.setData(self._data_)
            self.plotDataPushButton.setEnabled(True)




def launch():
    try:
        win = mainWindow.newViewer(CurveFittingTool, parent = mainWindow,
                                   win_title="Curve Fitting Tool",
                                   varName="curveFittingToolWindow")
        win.show()
    except:
        traceback.print_exc()

def init_scipyen_plugin():
    return {"Applications|Curve Fitting Tool":launch}
