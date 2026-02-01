# -*- coding: utf-8 -*-
# $Id: datatreeeditor.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@gmail.com>
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

from imaging import vigrautils

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

from core.prog import (safewrapper, safeguiwrapper, print_styled, qVariants)

from core.traitcontainers import (DataBag, DataBagTraitsObserver,)

from gui.widgets.tablewidget import SimpleTableWidget
from gui.widgets.tableeditorwidget import (TableEditorWidget, TabularDataModel,)
from gui.pictgui import WorkerThread

NOTMEMOIZED = (tuple, type(None), type(MISSING), type(pd.NA), type, np.ndarray, types.ModuleType, pkgutil.ModuleInfo)
PODS = (bool, int, float, bytes, bytearray, str)

class DataTreeItem(object):

    # NOTE: 2026-02-01 14:46:39
    # Sicne a tree mode is a "hierarchical" data model, the children of a DataTreeItem
    # will each occupy a row counted from 0; rows are counted for 0  - do not confuse with
    # a table model where rows are a single collection of indices for the entire data model !
    def.__init__(self, data:typing.Sequence[QtCore.QVariant], parentItem:typing.Self) -> typing.Self:
        # super().__init__()
        self._itemData_ = data
        self._parentItem_ = parentItem
        self._childItems_:typing.List(typing.Self) = list()

    def appendChild(self, childItem:typing.Self):
        self._childItems_.append(childItem)

    def childCount(self) -> int:
        return len(self._childItems_)

    def columnCount(self) -> int: # should always be 3, right !? -> ["Object", "Type", "Value / Information"]
        return len(self._itemData_)

    def child(self, row:int) -> typing.Self | None:
        return self._childItems_[row] if row >= 0 and row < self.childCount() else None

    def data(self, col:int) -> QtCore.QVariant: # may be null (isNull() -> True)
        return self._itemData_[col] if col >= 0 and col < len(self._itemData_) else QtCore.QVariant()

    def parentItem(self) -> typing.Self | None:
        return self._parentItem_

    def row(self) -> int:
        r"""The row of this item, in the branch of its parent.

Returns:
========
* 0 if this item has no parent

* -1 of this item is ont found among its parent's children (technically should vener happen)

* the index of this item in the parent's children

"""
        if self._parentItem_ is None:
            return 0

        siblings = self._parentItem_._childItems_
        if self in siblings:
            return siblings.index(self)

        return -1

class TreeDataModel(QtCore.QAbstractTableModel):
    r"""

General rule for delegate:
* the ones that occupy a single row go to column 2 of CURRENT item:
    * QCheckBox
    * QSpinBox
    * QuantitySpinBox
    * ComplexSpinBox
    * QLineEdit

* the ones that take-up moe screen estate need expanding and therefore go in column 0 OF CHILD item:
    * QTextEdit
    * table editor widget

* mapping *keys* are **not** editable (yet); these are all **hashable** objects.
    HOWEVER: thee may be a case to modify a mapping's structure by changing the "key", although
        may be dubious / to contemplate renaming str or int keys

1) POD objects, str, bytes and bytearray:

name (symbol) -> type -> value/information — NO CHILDREN
                         delegate in column 2 according to data type:
                                bool -> QCheckBox
                                int -> QSpinBox
                                float -> QuantitySpinBox
                                complex -> ComplexSpinBox
                                str -> QLineEdit or QTextEditq
                                bytes/bytearray -> QLineEdit or TextEdit ONLY WHEN it makes sense...

                                anything else: QLabel with object repr

2) numpy arrays:
2.1) generic numpy arrays
name (symbol) -> type -> value/information — NO CHILDREN if data size <= 1
                         delegate in column 2 according to array dtype:
                                bool -> QCheckBox
                                int -> QSpinBox
                                float -> QuantitySpinBox
                                complex -> ComplexSpinBox
                                str -> QLineEdit
                                anything else: QLabel with object repr
    |
    CHILDREN (if data size > 1)
        delegate in column 0 = table editor widget

2.2) special numpy array cases:
2.2.1) vigra.VigraArray
name (symbol) -> type -> value/information
                         delegate in column 2 else according to array dtype if data.size <= 1:
                                    bool -> QChecBox (is this even possible in a VigraArray? Theoretically, yes but would be converted to float wheb writing to files)
                                    int -> QSpinBox,
                                    float -> QuantitySpinBox
                                    complex -> ComplexSpinBox
                                    str -> QLineEdit (is this even possible in a VigraArray?)
                                    anything else: QLabel
    |
    CHILDREN:
        -> AxisInfo name (symbol) -> type ("AxisInfo") -> value
                |
                CHILDREN: attributes of axis info
        ⋮
        -> as above for each AxisInfo

        -> (if data.size > 1) table editor widget delegate in column 0

2.2.2) struct arrays - not supported yet, treat as POD with QLabel as delegate for column 3

2.2.3) neo.data objects
name (symbol) -> type -> value/information
                         delegate in column 3 else according to array dtype if data.size <= 1:
                                    bool -> QChecBox (is this even possible in a VigraArray? Theoretically, yes but would be converted to float wheb writing to files)
                                    int -> QSpinBox,
                                    float -> QuantitySpinBox
                                    complex -> ComplexSpinBox
                                    str -> QLineEdit (is this even possible in a VigraArray?)
                                    anything else: QLabel
    |
    CHILDREN:
    -> array data delegate for column 0:  table editor widget if data.size > 0, else according to dtype:
                                    int -> QSpinBox,
                                    float -> QuantitySpinBox
                                    complex -> ComplexSpinBox
                                    str -> QLineEdit
                                    anything else: QLabel

3) For Pyton collections:
3.1) dict, mappings
name(symbol) -> type -> value/information
    |
    CHILDREN:
        -> name(symbol)     -> type         -> value/information — MAYBE CHILDREN, see 1-3)
            string repr         dict item       dict item value
            of dict key         value type

            tooltip: key type

3.2) sequences (tuple, list, deque)

"""
    sig_editCompleted = Signal([pd.DataFrame], [pd.Series], [np.ndarray], name="sig_editCompleted")
    sig_modelDataChanged = Signal(name="sig_modelDataChanged")

    def __init__(self, data:typing.Optional[typing.Any]=None, dataName:str=None,
                 parent:typing.Optional[QtCore.QObject]=None,
                 **kwargs):
        super(TreeDataModel, self).__init__(parent=parent)
        self._supported_data_types_ = kwargs.pop("supported_data_types", tuple())
        if not isinstance(self._supported_data_types_, tuple) or not all(isinstance(v, type) for v in self._supported_data_types_):
            self._supported_data_types_ = tuple()
        self._modelDataColumns_:int = 3
        self._modelDataRows_:int = 0
        self._displayedColumns_:int = 3
        self._displayedRows_:int = 0
        self._rootItem_:DataTreeItem(qVariants(["Object", "Type", "Value / Information"]))))

        if isinstance(dataName, str) and len(dataName.strip()):
            self._dataName_ = dataName
        else:
            self._dataName_ = f"{data}"

        self._modelData_ = data

        self.setModelData(self._modelData_, name = self._dataName_)

    def data(self, modelIndex:QtCore.QModelIndex,
             role:QtCore.Qt.ItemDataRole = QtCore,Qt.DisplayRole) -> QtCore.QVariant: # TODO
        if self._modelData_ is None:
            return QtCore.QVariant()

        if not modelIndex.isValid():
            return QtCore.QVariant()

        # avoid calling internalPointer() -> it will CRASH!
        # instad, rely on the modelIndex's API, knowing that the model index only
        # has data for column 0 (one index per column)
        return modelIndex.data(0, role)


    def canFetchMore(self, parentIndex:QtCore.QModelIndex) -> bool:
        return False if parentIndex.isValid() else self._displayedRows_ < self._modelDataRows_ or self._displayedColumns_ < self._modelDataColumns_

    def fetchMore(self, parentIndex:QtCore.QModelIndex):
        if parentIndex.isValid():
            return

    def setModelData(self, data:typing.Any, name:str="",
                     showPrivate:bool=False, predicate=None,
                     top_title:str = "/", dataTypeStr:str=""): # TODO


        pass


class DataTreeEditor(QtWidgets.QTreeView):
    def __init__(self, , *args, **kwargs):
        parent = kwargs.pop("parent", None)
        super().__init__(parent=parent)
