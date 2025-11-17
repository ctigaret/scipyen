# -*- coding: utf-8 -*-
# $Id: datatreemodel.py $
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later
    
r"""
"""
import sys, os, typing
from qtpy import QtCore, QtGui, QtWidgets, QtSvg
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__
from core.prog import safeWrapper
from core.sysutils import adapt_ui_path

__module_path__ = os.path.abspath(os.path.dirname(__file__))

import os, warnings, types, traceback, itertools, inspect, dataclasses, numbers
import pathlib
import datetime
import fractions, decimal
import typing
import enum
from collections import deque
import dataclasses
from dataclasses import MISSING
import math
from functools import singledispatch
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
from pyqtgraph.widgets.DataTreeWidget import HAVE_METAARRAY
#### END 3rd party modules

#### BEGIN pict.core modules
import core.datatypes as datatypes
from core.datatypes import (is_namedtuple, TypeEnum)

import imaging.axiscalibration
from imaging.axiscalibration import (AxesCalibration, AxisCalibrationData, ChannelCalibrationData)

import imaging.scandata
from imaging.scandata import (ScanData, AnalysisUnit)
from imaging.axisutils import axisTypeStrings

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

from systems.PrairieView import (PVObject,PVScan, PVSequence, PVFrame, PVSystemConfiguration,
                                PVStateShard, PVStateValue, PVIndexedValue, PVSubIndexedValue, 
                                PVSubIndexedValueList, PVLinescanDefinition)
        

NOTMEMOIZED = (tuple, type(None), type(MISSING), type(pd.NA), type, np.ndarray)
PODS = (bool, int, float, bytes, bytearray, str, complex, fractions.Fraction, decimal.Decimal, numbers.Number)

class DataTreeModel(QtCore.QAbstractItemModel):
    # NOTE: 2025-11-16 21:36:49
    # use UserRole to store the element data type (Python side)
    # use EditRole to store the element data object (Python side)
    
    # NOTE: 2025-11-16 22:00:26 FIXME/TODO
    # should data to be displayed/edited in special widgets be considered as
    # having ONE child ?!?
    #
    # See interactivetreewidget.InteractiveTreeWidget.parse(…)

    def __init__(self, data:typing.Any, parent:typing.Optional[QtCore.QObject]=None):
        super().__init__(parent)
        rootDataItems = list(map(QtCore.QVariant(v), ["Object", "Type", "Value/Information"]))
        self._rootItem_ = DataTreeItem(rootDataItems)
        
        self._editable_items_:bool = False
        
        self._introspect_:bool=False
        
        self._data_ = None # TODO 2025-11-16 21:02:59 FIXME
        self.has_dynamic_private = False
        self._private_data_ = None
        self._introspectPredicate_ = None
        self._showPrivateMembers_ = False
        
        self._setupModelData(data, self._rootItem_)
        
    def flags(self, index:QtCore.QModelIndex) -> QtCore.Qt.ItemFlag:
        flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsEnabled
        if self._editable_items_:
            flags |= QtCore.Qt.ItemIsEditable
            
        return flags
    
    def index(self, row:int, column:int, parent:QtCore.QModelIndex) -> QtCore.QModelIndex:
        r"""The model index at given row & column of parent.
    Returns an invalid model index if no such index exists in the model.
    """
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()

        parentItem = parent.internalPointer() is parent.isValid() else self._rootItem_
        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        
        return QtCore.QModelIndex()
    
    def parent(self, index:QtCore.QModelIndex) -> QtCore.QModelIndex:
        # TODO 2025-11-17 22:06:48 FIXME
        if not index.isValid():
            return QtCore.QModelIndex()
        childItem = index.internalPointer()
        parentItem = childItem.parentItem()

        return self.createIndex(parentItem.row(), 0, parentItem) if parentItem != self._rootItem_ else QtCore.QModelIndex()
    
    def data(self, index:QtCore.QModelIndex, role:int = QtCore.Qt.DisplayRole) -> QtCore.QVariant:
        return QtCore.QVariant() # TODO 2025-11-16 21:02:36 FIXME
    
    def setData(self, index:QtCore.QModelIndex, value:QtCore.QVariant, 
                role:int = QtCore.Qt.EditRole) -> bool: # TODO 2025-11-16 21:08:14 FIXME
        # TODO 2025-11-16 21:08:52 FIXME 
        # on the next line, consider all roles (i.e. empty list) as the 3ʳᵈ parameter
        self.dataChanged.emit(index, index, [role]) 
        return True
        
    def headerData(self, section:int, orientation:QtCore.Qt.Orientation, 
                   role:int = QtCore.Qt.DisplayRole) -> QtCore.QVariant:
        if orientation == QtCore.Qt.Horizontal:
            if section == 0:
                return QtCore.QVariant("Object")
            elif section == 1:
                return QtCore.QVariant("Type")
            elif section == 2:
                return QtCore.QVariant("Value/Information")
            else:
                return QtCore.QVariant()
        else:
            return QtCore.QVariant()
        
    def setHeaderData(self, section:int, orientation:QtCore.Qt.Orientation,
                      value:QtCore.QVariant, role:int = QtCore.Qt.EditRole) -> bool:
        # NOTE: 2025-11-16 21:11:19 
        # Never change headers here
        return False
        
    def rowCount(self, parent:QtCore.QModelIndex) -> int:
        # data = self.data(parent, QtCore.Qt.EditRole)
        # return self._getChildrenCount(data)
        if parent.column() > 0:
            return 0
        parentItem = parent.internalPointer() if parent.isValid() else self._rootItem_
        return parentItem.childCount()
    
    def columnCount(self, parent:QtCore.QModelIndex) -> int:
        # return 3
        if parent.isValid():
            return parent.internalPointer().columnCount()
        return self._rootItem_.columnCount()
        
    
    def hasChildren(self, parent:QtCore.QModelIndex = QtCore.QModelIndex()) -> bool:
        return self.rowCount(parent) > 0
        # use self.rowCount(parent) > 0
#         data = self.data(parent, QtCore.Qt.EditRole)
#         
#         return self._dataHasChildren_(data)
    
# ### BEGIN Use the superclass defaults
#
#     def insertRows(self, row:int, count:int, parent:QtCore.QModelIndex = QtCore.QModelIndex()) -> bool:
#         # TODO 2025-11-16 21:21:32 FIXME
#         return False
#     
#     def removeRows(self, row:int, count:int, parent:QtCore.QModelIndex = QtCore.QModelIndex()) -> bool:
#         # TODO 2025-11-16 21:21:32 FIXME
#         return False
#     
#     def insertColumns(self, column:int, count:int, parent:QtCore.QModelIndex = QtCore.QModelIndex()) -> bool:
#         # TODO 2025-11-16 21:21:32 FIXME
#         return False
#     
#     def removeColumns(self, column:int, count:int, parent:QtCore.QModelIndex = QtCore.QModelIndex()) -> bool:
#         # TODO 2025-11-16 21:21:32 FIXME
#         return False
#
# ### END   Use the superclass defaults
    
    def _getChildrenCount(self, data:typing.Any) -> int:
        if isinstance(data, type):
            return len(data.__members__) if isinstance(data, enum.EnumType) else 0
        
        elif isinstance(data, NestedFinder.nesting_types + (set, )):
            return len(data)
        
        elif isinstance(data, types.SimpleNamespace):
            return len(data.__dict__)
        
        elif isinstance(data, AxesCalibration):
            return len(data.calibrations)
        
        elif isinstance(data, AxisCalibrationData):
            return len(data.channels) if data.isChannels else 0
        
        elif isinstance(data, ChannelCalibrationData):
            return 0
        
        elif isinstance(data, PVObject):
            return len(data.as_dict())
        
        elif isinstance(data, Interval):
            # children = {"t0": data.t0, "t1": data.t1, "durations": data.durations, 
            #             "extent": data.extent, "labels": data.labels,
            #             "annotations": data.annotations,
            #             "description": data.description,
            #             }
            return 7
        
        elif isinstance(data, (neo.Epoch, DataZone)):
            # children = {"times": data.times, "durations": data.durations, 
            #             "labels": data.labels, "annotations": data.annotations,
            #             "description": data.description}
            return 5
        
        elif isinstance(data, (neo.Event, DataMark, TriggerEvent)):
            # children = {"times": data.times, "labels": data.labels}
            if isinstance(data, (DataMark, TriggerEvent)):
                # children.update({"type": data.type, "relative": data.relative})
                return 6
            # children.update({"annotations": data.annotations,
            #                     "description": data.description})
            return 4
        
        elif isinstance(data, scipy.optimize.Bounds):
            # children = {"lb": data.lb, "ub": data.ub, "keep_feasible": data.keep_feasible}
            return 3
            
        elif dataclasses.is_dataclass(data):
            return len(dataclasses.fields(data))
        
        else:
            if self.introspectionEnabled:
                return len(datatypes.inspect_members(data, self.introspectionPredicate))
            else:
                return False
        
    def _dataHasChildren_(self, data:typing.Any) -> bool:
        # FIXME 2025-11-16 22:19:49 TODO: use rowCount() on the representation QModelIndex
#         if issubclass(type(data), PODS):
#             return False
#         
#         if data in (dataclasses.MISSING, pd.NA, None):
#             return False
        
        if isinstance(data, type):
            return isinstance(data, enum.EnumType)
        
        elif HAVE_METAARRAY and (hasattr(data, 'implements') and data.implements('MetaArray')):
            return 2
        
        elif isinstance(data, NestedFinder.nesting_types + (set, )):
            return len(data) > 0
            # if issubclass(type(data), (dict, types.MappingProxyType)):
            
        elif HAVE_METAARRAY and (hasattr(data, 'implements') and data.implements('MetaArray')):
            return True
        
        elif isinstance(data, types.SimpleNamespace):
            return len(data.__dict__) > 0
        
        elif isinstance(data, AxesCalibration):
            return len(data.calibrations) > 0
        
        elif isinstance(data, AxisCalibrationData):
            return data.isChannels and len(data.channels) > 0
        
        elif isinstance(data, ChannelCalibrationData):
            return False
        
        elif isinstance(data, PVObject):
            return len(data.as_dict()) > 0
        
        elif isinstance(data, (Interval,neo.Epoch, DataZone, neo.Event, DataMark, TriggerEvent, scipy.optimize.Bounds)):
            return True
        
        elif dataclasses.is_dataclass(data):
            return len(dataclasses.fields(data)) > 0
        
        else:
            if self.introspectionEnabled:
                return len(datatypes.inspect_members(data, self.introspectionPredicate)) > 0
            return False
        
    def _setupModelData(self, data:typing.Any, rootItem:DataTreeItem):
        pass
        
    @property
    def editableItems(self) -> bool:
        return self._editable_items_
    
    @editableItems.setter
    def editableItems(self, val:bool):
        self._editable_items_ = val == True
        
    @property
    def introspectionEnabled(self) -> bool:
        return self._introspect_
    
    @introspectionEnabled.setter
    def introspectionEnabled(self, val:bool):
        self._introspect_ = val == True
        
    @property
    def introspectionPredicate(self):
        return self._introspectPredicate_
    
    @introspectionPredicate.setter
    def introspectionPredicate(self, val):
        self._introspectPredicate_ = val
        
    @property
    def showsPrivateMembers(self) -> bool:
        return self._showPrivateMembers_
    
    @showsPrivateMembers.setter
    def showsPrivateMembers(self, val:bool):
        self._showPrivateMembers_ = val == True
    
class DataTreeItem:
    r"""See Simple Tree Model example in Qt documentation.
    A DataTreeItem contains children (DataTreeItem objects) — one per row — and
item data (QVariant objects wrapping Python data), one per column.
    The hierarchy is established by DataTreeItem objects being children of a higher
level DataTreeItem; at the top of the hierarchy sits the "root" item.
"""
    def __init__(self, data:typing.List[QtCore.QVariant], parentItem:typing.Optional[typing.Self] = None):
        r"""DataTreeItem constructor
    Parameters:
    ===========
    data: list of QVariant objects — the item data stored in this DataTreeItem
    parentItem: the DataTreeItem, that has this DataTreeItem as a child
    """
        _childItems_:typing.List[typing.Self] = list()
        _itemData_:typing.List[QtCore.QVariant] = data
        _parentItem_:typing.Optional[typing.Self] = parentItem
        
    
    def appendChild(self, child:typing.Self):
        r"""Adds a DataTreeItem as a child of this object"""
        self._childItems_.append(child)
    
    def child(self, row:int) -> typing.Self | None:
        r"""Access the DataTreeItem child of this object, at index 'row'.
        Returns None when 'row' is out of range.
    """
        if row in range(len(self._childItems_)):
            return self._childItems_[row]
    
    def childCount(self) -> int:
        r"""How many DataTreeItem children does this object have.
    """
        return len(self._childItems_)
    
    def columnCount(self) -> int:
        r"""How many item data (QVariant objects) does this object have"""
        return len(self._itemData_)
    
    def data(self, column:int, role:QtCore.Qt.ItemDataRole=QtCore.Qt.DisplayRole) -> QtCore.QVariant:
        r"""Returns column data: the QVariant at index 'column'.
        Returns a QVariant() (empty) when 'column' is out of range
    """
        # TODO 2025-11-17 22:28:44 FIXME
        # set up item data (QVariant) for various item data roles!!!
        if column in range(len(self._itemData_)):
            return self._itemData_[column]
        return QtCore.QVariant()
    
    def row(self) -> int:
        r"""Index of this object in the list of children of its parent.
        Returns 0 if the parent is None, or -1 if this object is NOT a child of 
        its parent (unlikely, but there we go...)
    """
        if self._parentItem_ is None:
            return 0
        if self in self._parentItem_._childItems_:
            return self._parentItem_._childItems_.index(self)
        return -1
    
    def parentItem(self) -> typing.Self | None:
        return self._parentItem_
    
    
    
# @singledispatch # TODO 2025-11-16 21:59:00 implement this, if possible, replacing DataTreeModel._dataHasChildren_
# def data_has_children(obj:typing.Any) -> bool:
    
