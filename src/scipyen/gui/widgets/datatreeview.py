# -*- coding: utf-8 -*-
# $Id: datatreeview.py $
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later
    
r"""
"""
from __future__ import print_function

import os, warnings, types, traceback, itertools, inspect, dataclasses, numbers
import pathlib
import datetime
import fractions, decimal
import pkgutil
import typing
import enum
from collections import deque
import dataclasses
from dataclasses import MISSING
import math
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



# from pyqtgraph import (DataTreeWidget, TableWidget, )

import neo
if neo.__version__ >= '0.13.0':
    from neo.core.objectlist import ObjectList as NeoObjectList
import quantities as pq
import numpy as np
import scipy
import pandas as pd
import vigra
#### END 3rd party modules

#### BEGIN pict.core modules
import core.datatypes as datatypes

import imaging.axiscalibration
from imaging.axiscalibration import AxesCalibration

import imaging.scandata
from imaging.scandata import (ScanData, AnalysisUnit)

from core.triggerprotocols import TriggerProtocol
from core.triggerevent import (DataMark, TriggerEvent, TriggerEventType)

import core.datasignal as datasignal
from core.datasignal import (DataSignal, IrregularlySampledDataSignal)

import core.datazone as datazone
from core.datazone import (DataZone, Interval)

from core import xmlutils, strutils

from core.workspacefunctions import (validate_varname, user_workspace)

#from core.utilities import (get_nested_value, set_nested_value, counter_suffix, )

from core.utilities import (NestedFinder, unique)

from core.prog import (safewrapper, safeguiwrapper, print_styled)

from core.traitcontainers import (DataBag, DataBagTraitsObserver,)

from gui.widgets.tablewidget import SimpleTableWidget
from gui.widgets.tableeditorwidget import (TableEditorWidget, TabularDataModel,)
from gui.pictgui import WorkerThread

NOTMEMOIZED = (tuple, type(None), type(MISSING), type(pd.NA), type, np.ndarray, types.ModuleType, pkgutil.ModuleInfo)
PODS = (bool, int, float, bytes, bytearray, str)

class DataTreeModel(QtCore.QAbstractTableModel):
    sig_editCompleted = Signal([pd.DataFrame], [pd.Series], [np.ndarray], name="sig_editCompleted")
    sig_modelDataChanged = Signal(name="sig_modelDataChanged")

    def __init__(self, data=None, parent=None):
        super(DataTreeModel, self).__init__(parent=parent)


class DataTreeView(QtWidgets.QTreeView):
    def __init__(self, , *args, **kwargs):
        parent = kwargs.pop("parent", None)
        super().__init__(parent=parent)
