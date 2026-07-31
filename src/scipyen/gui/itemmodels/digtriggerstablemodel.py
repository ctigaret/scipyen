# -*- coding: utf-8 -*-
# $Id: digtriggerstablemodel.py $
# SPDX-FileCopyrightText: 2023 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""Table model for digital triggers
"""
# NOTE: 2026-06-09 18:16:55
# perhaps reductant with parts of TabularDataModel
# TODO/FIXME clear this out

#### BEGIN core python modules
from __future__ import print_function

import os, inspect, warnings, traceback, datetime, typing, numbers, enum
from functools import singledispatch
from collections import deque
#### END core python modules

#### BEGIN 3rd party modules
import qtpy # noqa
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, )
from qtpy.QtCore import (Signal, Slot, Property,)
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6 # noqa
    from PySide6 import Shiboken # noqa
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


import pandas as pd
import quantities as pq
#import xarray as xa
import numpy as np
import neo
from neo.core.objectlist import ObjectList as NeoObjectList
from core.vigra_patches import vigra

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.pylab as plb
import matplotlib.mlab as mlb
#### END 3rd party modules

#### BEGIN pict.core modules
#from core.patchneo import *
import core.datatypes

import core.utilities as utilities
import core.strutils as strutils
from core.strutils import str2float
from core.prog import (safewrapper, scipywarn)
from core.triggerevent import (DataMark, MarkType, TriggerEvent, TriggerEventType)
from core.marktrain import MarkTrain
from core.triggerprotocols import (TriggerProtocol, TriggerProtocolList)
from core.datazone import DataZone
import core.datasignal
from core.datasignal import (DataSignal, IrregularlySampledDataSignal,)
import core.datatypes as dt
from core.datatypes import array_slice
from core.sysutils import adapt_ui_path
from core import scipyen_quantities as scq
from core import neoutils
from core.qtutils import qVariant

#### END pict.core modules

from ephys import ephys


#### BEGIN pict.gui modules
from gui.scipyenviewer import ScipyenViewer #, ScipyenFrameViewer
from gui import quickdialog
from gui.delegates import PythonItemDelegate
from gui.widgets.tabledataview import TableDataView
from gui.itemmodels.roles import *
# from gui import resources_rc
# from gui import icons_rc
#### END pict.gui modules

#### BEGIN pict.iolib modules
import iolib.pictio as pio
#### END pict.iolib modules


__module_name__ = os.path.splitext(os.path.basename(__file__))[0]

class DIGTriggersTableModel(QtCore.QAbstractTableModel):
    model_columns = ["DIG Channel", "Type", "Name", "Labels", "Sweep(s)", "Used"]

    sig_editCompleted = Signal(str, name="sig_editCompleted")

    def __init__(self, triggers:typing.Optional[typing.Sequence]=None, parent=None):
        super().__init__(parent)

        for k, col in enumerate(self.model_columns):
            self.setHeaderData(k, QtCore.Qt.Horizontal, qVariant(col))

        # self.headerDataChanged.emit()
        self.immutability = {"columns": [0, 4], "joint": False}

        self.beginResetModel()
        self._data_ = list(triggers) if isinstance(triggers, typing.Sequence) else list()
        self.endResetModel()

    def rowCount(self, parent:QtCore.QModelIndex = QtCore.QModelIndex()):
        return len(self._data_)

    def columnCount(self, parent:QtCore.QModelIndex = QtCore.QModelIndex()):
        return len(self.model_columns)

    def headerData(self, section:int, orientation:QtCore.Qt.Orientation,
                   role:QtCore.Qt.ItemDataRole = QtCore.Qt.DisplayRole) -> qVariant:

        if len(self._data_) == 0:
            return qVariant()

        if role not in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.ToolTipRole, QtCore.Qt.AccessibleTextRole):
            return qVariant()

        if orientation == QtCore.Qt.Horizontal: # column header
            return qVariant(self.model_columns[section])

        else: # vertical (rows) header
            return qVariant("%d" % section)

    def data(self, index:QtCore.QModelIndex, role:QtCore.Qt.ItemDataRole = QtCore.Qt.DisplayRole):
        if self._data_ is None:
            return qVariant()

        if not index.isValid():
            return qVariant()

        if len(self._data_) == 0 or not all ((isinstance(p, typing.Sequence) for p in self._data_)):
            return qVariant()

        if role not in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.ToolTipRole, QtCore.Qt.AccessibleTextRole, QtCore.Qt.AccessibleDescriptionRole):
            return qVariant()

        # rows: one for each defined protocol
        row = index.row()

        if row >= len(self._data_) or row < 0:
            return qVariant()

        # columns:                                  editor proxy widget
        # 0: int = DIG channel index                None
        # 1: str: trigger event type name           combo box
        # 2: str: trigger event name                line edit
        # 3: str: trigger event label               line edit
        # 4: tuple[int]: sweeps where it occurs     line edit
        # 5: bool: use this trigger event           checkbox

        col = index.column()

        if col < 0 or col >= len(self.model_columns):
            return qVariant()

        trigger_data = self._data_[row]

        dig = trigger_data[0]
        event = trigger_data[1][0]
        used = trigger_data[2][0]
        sweeps = trigger_data[3]

        if col == 0: # digital channel
            val = dig
            tip = qVariant(f"DIG Channel {val}")

        elif col == 1: # trigger event type name
            val = event.type.name
            tip = qVariant(f"Type: {val}")

        elif col == 2: # name
            val = event.name
            tip = qVariant(f"Name: {val}")

        elif col == 3: # labels
            val = ", ".join(list(map(lambda x: str(x), event.labels)))
            tip = qVariant(f"Labels: {val}")

        elif col == 4: # sweeps where it occurs
            val = ", ".join(list(map(lambda x: str(x), sweeps)))
            tip = qVariant(f"Sweeps where emitted: {val}")

        elif col == 5: # use this trigger event
            val = used
            tip = qVariant("Used" if val else "Not used")
        else:
            val = None
            tip = qVariant()

        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.UserRole):
            return qVariant() if val is None else qVariant(val)

        elif role in (QtCore.Qt.ToolTipRole, QtCore.Qt.AccessibleDescriptionRole):
            return tip

        elif role in (QtCore.Qt.UserRole, ):
            return qVariant(val)

        elif role == QtCore.Qt.EditRole:
            return val

    def setData(self, modelIndex, value, role = QtCore.Qt.EditRole) -> bool:
        row = modelIndex.row()
        col = modelIndex.column()

        if col == 0: # no editing of DIG channel index
            return False

        if row >= len(self._data_):
            return False

        if col >= len(self.model_columns):
            return False

        if role != QtCore.Qt.EditRole:
            return False

        try:
            if isinstance(value, qVariant) or hasattr(value, "value"):
                pyvalue = value.value()

            else:
                pyvalue = value

            te_data = list(self._data_[row])

            # print(f"{self.__class__.__name__}.setData: te_data: {te_data}")

            event = te_data[1][0]

            if col == 1: # trigger event type
                event.event_type = TriggerEventType[pyvalue]

            elif col == 2: # event name
                event.name = pyvalue

            elif col == 3: # labels
                event.setLabels(pyvalue)

            elif col == 5: # in use
                te_data[2] = (pyvalue,)

            self._data_[row] = tuple(te_data)

            # print(f"{self.__class__.__name__}.setData: _data_ = {self._data_}")

        except:
            traceback.print_exc()
            return False

    def flags(self, index:QtCore.QModelIndex):
        return QtCore.Qt.ItemIsEditable | super().flags(index)

    @property
    def modelData(self) -> list:
        return self._data_

    @modelData.setter
    def modelData(self, value:typing.Optional[typing.Sequence]):
        self.beginResetModel()
        self._data_ = list(value) if isinstance(value, typing.Sequence) else list()
        self.endResetModel()

    def populateModel(self, data:list):
        try:
            self.beginResetModel()
            self._data_ = data
            self.endResetModel()
            self.headerDataChanged.emit(QtCore.Qt.Vertical, 0, len(data))

        except:
            traceback.print_exc()

    def sourceData(self) -> list:
        return self._data_

