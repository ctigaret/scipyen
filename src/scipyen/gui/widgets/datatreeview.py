# -*- coding: utf-8 -*-
# $Id: datatreeeditor.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later
    
r"""
.. note::

    NOTE: 2026-02-02 08:56:30

    Hitting a wall of bricks here...

    The only QModelIndex constructor API exposed in PyQt6 QModelIndex
    seems to be:

.. ::

    QModelIndex()
    QModelIndex(a0: QModelIndex)
    QModelIndex(a0: QPersistentModelIndex)


I.e., there seems to be no way I can generate a QModelIndex via, say,

.. ::

    QtCore.QModelIndex(row:int, column:int, data:typing.Any)

"""
from __future__ import print_function

import os
import warnings
import types
import traceback
import itertools
import inspect
import dataclasses
import numbers
import pathlib
import datetime
import fractions
import decimal
import pkgutil
import typing
import enum
from functools import (singledispatch, singledispatchmethod)
from collections import deque
from dataclasses import MISSING
import math
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
# ### END 3rd party modules

# ### BEGIN pict.core modules
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

from core import scipyen_quantities as scq

from core.workspacefunctions import (validate_varname, user_workspace)

# from core.utilities import (get_nested_value, set_nested_value,
#                               counter_suffix, )

from core.utilities import (NestedFinder, unique)

from core.prog import (safewrapper, safeguiwrapper, print_styled, qVariants)

from core.traitcontainers import (DataBag, DataBagTraitsObserver,)

from core.scipyendataclasses import isDataclass

from gui.widgets.tablewidget import SimpleTableWidget
from gui.widgets.tableeditorwidget import (TableEditorWidget, 
                                           TabularDataModel,)
from gui.pictgui import WorkerThread
from gui.delegates import PythonItemDelegate

NOTMEMOIZED = (
    tuple,
    type(None),
    type(MISSING),
    type(pd.NA),
    type,
    np.ndarray,
    types.ModuleType,
    pkgutil.ModuleInfo,
)

PODS = (
    bool,
    int,
    float,
    complex,
    bytes,
    bytearray,
    str,
    np.integer,
    np.floating,
    np.complexfloating,
)

# NOTE 2026-02-05 17:48:51 TODO/FIXME
# look at:
# QItemEditorFactory
# QItemEditorCreatorBase
# QStandardItemEditorCreator
# use QTreeView with QStyledItemDelegate subclass and QStandardItem

# ### BEGIN class DataTreeItem(object)

# class DataTreeItem(object):
# 
#     # NOTE: 2026-02-01 14:46:39
#     # Since a tree mode is a "hierarchical" data model, the children of a DataTreeItem
#     # will each occupy a row counted from 0; rows are counted for 0  - do not confuse with
#     # a table model where rows are a single collection of indices for the entire data model !
#     def __init__(self, data:typing.Sequence[QtCore.QVariant], parentItem:typing.Self, model:QtCore.QAbstractItemModel) -> typing.Self:
#         # super().__init__()
#         self._itemData_ = data # sequence of QVariant, one per column
#         self._parentItem_ = parentItem # this item occupies one ROW beneath the parent item; it is None for the root item
#         self._childItems_:typing.List(typing.Self) = list() # each DataTreeItem as a child of this one occupies one ROW beneath it
#         self._model_ = model
# 
#     def appendChild(self, childItem:typing.Self):
#         # all children are DataTreeItem objects, one per row
#         # so this one effectively adds one row beneath itself
#         self._childItems_.append(childItem)
# 
#     def childCount(self) -> int:
#         # how many rows beneath this item?
#         return len(self._childItems_)
# 
#     def columnCount(self) -> int: # should always be 3, right !? -> ["Object", "Type", "Value / Information"]
#         # one QVariant per column! -> how many QVariant in this row (and by implication, in its row)
#         return len(self._itemData_)
# 
#     def child(self, row:int) -> typing.Self | None:
#         # the DataTreeItem at specified row , or None
#         return self._childItems_[row] if row >= 0 and row < self.childCount() else None
# 
#     def data(self, column:int) -> QtCore.QVariant: # may be null (isNull() -> True)
#         # the QVariant at specified column
#         return self._itemData_[column] if column >= 0 and column < len(self._itemData_) else QtCore.QVariant()
# 
#     def parentItem(self) -> typing.Self | None:
#         # returns its parent or None; if this is the root, parent is always None
#         return self._parentItem_
# 
#     def row(self) -> int:
#         r"""The row of this item, in the branch of its parent.
# 
# Returns:
# ========
# * 0 if this item has no parent
# 
# * -1 of this item is not found among its parent's children (technically should vener happen)
# 
# * the index of this item in the parent's children
# 
# """
#         if self._parentItem_ is None:
#             return 0
# 
#         siblings = self._parentItem_._childItems_
#         if self in siblings:
#             # index of this item in the parent's children
#             return siblings.index(self)
# 
#         return -1
# 
# #     def index(self, column:int) -> QModelIndex:
# #         row = self.row()
# #         if row == -1 or column not in range(len(self._itemData_)):
# #             return QtCore.QModelIndex() # invalid model index
# #
# #         return QtCore.QModelIndex(row, column, None) # this API is NOT exposed to Python!

# ### END   class DataTreeItem(object)

# ### BEGIN class DataTreeItem(QtGui.QStandardItem)


class DataTreeItem(QtGui.QStandardItem):
    def __init__(self, *args, **kwargs):
        if len(args) == 1 and isinstance(args[0], str):
            super().__init__(args[0]) # item c'tor with a string



        else:
            raise TypeError("Expecting a str, or a QtGui.QIcon and str, or two int values")


# ### END   class DataTreeItem(QtGui.QStandardItem)

class DataTreeModel(QtGui.QStandardItemModel):
    r"""

Approach:

.. ::

    # d = dict(...)

    model = QtGui.QStandardItemModel(0,3)
    invisibleRootItem = model.invisibleRootItem()
    top_item0 = QtGui.QStandardItem("d")
    top_item1 = QtGui.QStandardItem(type(d).__name__)
    top_item2 = QtGui.QStandardItem(f"{len(d)}")
    invisibleRootItem.insertRow(0, [top_item0, top_item1, top_item2])
    parentItem = top_item0
    for k, (key, val) in enumerate(d.items()):
        item0 = QtGui.QStandardItem(key)
        item1 = QtGui.QStandardItem(type(val).__name__)
        item2 = QtGui.QStandardItem("a thing")
        parentItem.insertRow(k, [item0, item1, item2])

    treeView = QtWidgets.QTreeView()
    treeView.setModel(model)
    treeView.show()

"Root" item: should be populatd with tol-leve object info (the "data" object)

Depending on what data type is, add children to this root item

Have the model create items for each of the three columns
(see InteractiveTreeWidget) using 1st-level object info



General rule for delegate use in this model:
* the ones that occupy a single row go to column 2 of CURRENT item -> makes it easy to edit the object represented by the item
    * QCheckBox
    * QSpinBox
    * QuantitySpinBox
    * ComplexSpinBox
    * QLineEdit

* the ones that take-up more screen estate need expanding and therefore go in column 0 OF A CHILD of the item to be modified:
    * QTextEdit
    * table editor widget

* mapping *keys* are **not** editable, see the following note; these are all **hashable** objects.

* similarly, indexes in sequence-like collections are **not** editable

.. note::

    There may be a case to modify a mapping's structure by changing the "key" to which a value is mapped,
        BUT this may controversial:
        * would change the semantics of the mapping object (i.e. break expectations for the user(s) of that object - change API 'contract')
        * would be tricky to implement
        * would only apply to keys of a type for which we have item delegates in place: str (QLineEdit), int (QSpinBox)

1. POD objects, str, bytes and bytearray:

.. ::

    name (symbol) -> type -> value/information — NO CHILDREN
                            delegate in column 2 according to data type:
                                    bool -> QCheckBox
                                    int -> QSpinBox
                                    float -> QuantitySpinBox
                                    complex -> ComplexSpinBox
                                    str -> QLineEdit or QTextEditq
                                    bytes/bytearray -> QLineEdit or TextEdit ONLY WHEN it makes sense...

                                    anything else: QLabel with object repr

2. numpy arrays:

    1. generic numpy arrays

.. ::

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

    2. special numpy array cases:

        1. vigra.VigraArray

.. ::

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

            2. struct arrays - not supported yet, treat as POD with QLabel as delegate for column 3

            3. neo.data objects

.. ::

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
        -> array data delegate for column 0: table editor widget if data.size > 0, else according to dtype:
                                        int -> QSpinBox,
                                        float -> QuantitySpinBox
                                        complex -> ComplexSpinBox
                                        str -> QLineEdit
                                        anything else: QLabel

3. Standard Pyton collections:

    1. dict, mappings

.. ::

    name(symbol) -> type -> value/information
        |
        CHILDREN:
            -> name(symbol)     -> type         -> value/information — CHILDREN delegates on column 0 or ITEM delegate in column 2
                string repr         dict item       dict item value
                of dict key         value type

                tooltip: key type

    2. sequences (tuple, list, deque)

.. ::

    name(symbol) -> type -> value/information
        |
        CHILDREN:
            -> int key (index) -> type -> value/information — CHILDREN delegates on column 0 or ITEM delegate in column 2

"""
    mappingTypes = (dict, types.MappingProxyType)
    sequenceTypes = (typing.Sequence, tuple, list, deque, bytes)
    iterableCollectionTypes = sequenceTypes + mappingTypes

    sig_editCompleted = Signal([pd.DataFrame], [pd.Series], [np.ndarray], name="sig_editCompleted")
    sig_modelDataChanged = Signal(name="sig_modelDataChanged")

    def __init__(self: typing.Self, data: typing.Optional[typing.Any] = None,
                 dataName: str = None,
                 parent: typing.Optional[QtCore.QObject] = None,
                 **kwargs):
        super(DataTreeModel, self).__init__(0, 3, parent=parent)
        self._data_: typing.Optional[typing.Any] = None
        self._dataTypeStr_: str = ""
        self._visited_: dict = dict()
        self._rootTitle_ = "/"
        self._hasDynamicPrivate_: bool = False
        self._privateData_: typing.Mapping = None
        self._predicate_: types.FunctionType = None
        self._showPrivate_: bool = False
        self._hideRoot_: bool = False

        self._supportedDataTypes_ = kwargs.pop("supportedTypes", tuple())
        if not isinstance(self._supportedDataTypes_, tuple) or not all(
            isinstance(v, type) for v in self._supportedDataTypes_
        ):
            self._supportedDataTypes_ = tuple()

        self.setHorizontalHeaderLabels(["Object", "Type", "Value / Information"])


    def setModelData(
        self: typing.Self,
        data: typing.Any,
        predicate: typing.Optional[types.FunctionType] = None,
        showPrivate: bool = False,
        rootTitle: str = "",
        dataTypeStr: typing.Optional[str] = None,
        hideRoot: bool = False,
    ):
        self._visited_.clear()
        self._predicate_ = predicate
        self._showPrivate_ = showPrivate
        self._hideRoot_ = hideRoot

        self._privateData_,
        self._hasDynamicPrivate_ = self._parseData_(data, self._showPrivate_)

        self._data_ = data
        self._dataTypeStr_ = dataTypeStr

        self._rootTitle_ = rootTitle if len(rootTitle.strip()) else "/"

    def _makeRowItems_(self: typing.Self, obj: object, /,
                       objName: str = "", info: str = ""):

        if len(objName.strip()) == 0:
            objName = "/"

        typeName = type(obj).__name__

        if not isinstance(info, str) or len(info.strip()) == 0:
            info = self._getObjInfo_(obj)

        item0 = QtGui.QStandardItem(objName)
        item1 = QtGui.QStandardItem(typeName)
        item2 = QtGui.QStandardItem(info)

        return (item0, item1, item2)


    @singledispatchmethod
    def _getObjInfo_(self: typing.Self, obj: object) -> str:
        if obj in (None, MISSING, pd.NA):
            info = f"{obj}"

        elif isDataclass(obj):
            datafields = dataclasses.fields(data)
            n = len(datafields)
            info = f"{n} {strutils.pluralize('field', n)}"

        else:
            raise NotImplementedError(
            f"Objects of type {type(obj).__name__} are not supported"
            )

        return info

    @_getObjInfo_.register(type)
    def _(self: typing.Self, obj: type) -> str:
        return f"Type object: {obj.__name__}"

    @_getObjInfo_.register(str)
    @_getObjInfo_.register(bytes)
    @_getObjInfo_.register(bytearray)
    def _(self: typing.Self, obj: typing.Union[str, bytes, bytearray]) -> str:
        n = len(obj)
        if n > 100:
            info = (
                obj[:97] if isinstance(obj, str) else obj.decode()[:97]
            )
            info += "..."
        else:
            info = obj if isinstance(obj, str) else obj.decode()

        return info

    @_getObjInfo_.register(bool)
    @_getObjInfo_.register(int)
    @_getObjInfo_.register(float)
    @_getObjInfo_.register(complex)
    @_getObjInfo_.register(np.integer)
    @_getObjInfo_.register(np.floating)
    @_getObjInfo_.register(np.complexfloating)
    def _(self: typing.Self,
          obj: typing.Union[bool, int, float, complex,
                            np.integer, np.floating,
                            np.complexfloating]) -> str:
        return f"{obj}"

    @_getObjInfo_.register(list, tuple, deque, set)
    def _(self: typing.Self, obj: typing.Union[list, tuple, deque,
                                               set]) -> str:
        n = len(obj)
        return f"{n} {strutils.pluralize('element', n)}"

    @_getObjInfo_.register(typing.Mapping)
    def _(self: typing.Self, obj: typing.Mapping) -> str:
        n = len(obj)
        return f"{len(obj)} key / value {strutils.pluralize('pair', n)}"

    @_getObjInfo_.register(pq.UnitQuantity)
    @_getObjInfo_.register(pq.Quantity)
    def _(self:typing.Self, obj: pq.Quantity) -> str:
        if isinstance(pq.UnitQuantity):
            info = f"{obj} {scq.unitFamilyName(obj)}"
        else:
            if obj.size <= 1:
                info = f"{obj}"
            else:
                n = obj.size
                s = obj.shape
                info = f"Quantity array ({obj.units.dimensionality}) with {n} {strutils.pluralize('samples', n)}, shape {s}, and dtype {obj.dtype}"

        return info


    @_getObjInfo_.register(np.ndarray)
    def _(self: typing.Self, obj: np.ndarray) -> str:
        n = obj.size
        s = obj.shape
        if obj.size <= 1:
            info = f"{obj}"
        else:
            info = f"Array with {n} {strutils.pluralize('samples', n)}, shape {s}, and dtype {obj.dtype}"

        return info

    @_getObjInfo_.register(vigra.filters.Kernel1D)
    @_getObjInfo_.register(vigra.filters.Kernel2D)
    def _(self: typing.Self,
          obj: typing.Union[vigra.filters.Kernel1D,
                            vigra.filters.Kernel2D]) -> str:

        if isinstance(obj, vigra.filters.Kernel1D):
            n = int(obj.size())
            info = f"with {n} {strutils.pluralize('sample', n)}"
        else:
            h = int(obj.height())
            w = int(obj.width())
            info = f"with {h} × {w} {strutils.pluralize('sample', h*w)}"

        return info




    def _buildTree_(self: typing.Self,
                    data: object,
                    name: str = "",
                    keyType: type = str,
                    nameTip: str = "",
                    typeStr: typing.Optional[str] = None,
                    predicate: typing.Optional[types.FunctionType] = None,
                    hideRoot: bool = False,
                    path: tuple = tuple()):

        # 1. get the top object symbol, type and some information, as items to
        # go as the first (and only) top-level row in the model

        pass

    def _parseData_(self: typing.Self, data: typing.Any,
                    includePrivateMembers: bool = True) -> tuple:
        mro = inspect.getmro(type(data))
        flag = False

        # NOTE: 2025-06-28 13:57:28
        # generate a mapping representation of data's members upon which
        # the tree model is built
        # for dataclasses, use their fields
        # for non-dict classes inspect their members, allowing to ignore the
        # "private" members, i.e., those bound to symbols starting with
        # underscore ('_')
        if isDataclass(data):
            datafields = dataclasses.fields(data)
            pData = dict(map(lambda x: (x.name, getattr(data, x.name)), datafields))
            flag = True

        elif (
            all(t not in self._supportedDataTypes_ for t in mro)
            and not inspect.isroutine(data)
            and not isinstance(data, (types.ModuleType, pkgutil.ModuleInfo))
            and data is not None
        ):
            pData = datatypes.inspect_members(data, self.predicate)

            flag = True

        else:
            # NOTE: 2025-06-28 13:58:14
            # The data is suitable for direct representation by a tree model
            pData = data


        if not includePrivateMembers:
            pData = dict(
                list(
                    filter(
                        lambda x: not x[0].startswith("_"), pData.items()
                    )
                )
            )

        return pData, flag




    # def data(self, modelIndex: QtCore.QModelIndex,
    #          role: QtCore.Qt.ItemDataRole = QtCore.Qt.DisplayRole) -> QtCore.QVariant: # TODO 2026-02-01 21:31:55
    #     if self._modelData_ is None:
    #         return QtCore.QVariant()
    # 
    #     if not modelIndex.isValid():
    #         return QtCore.QVariant()
    # 
    #     # avoid calling internalPointer() -> it will CRASH!
    #     # instad, rely on the QModelIndex API, knowing that the all QModelIndex
    #     # in an item only has data for column 0 (the DataTreeItem can have 
    #     # several QModelIndex objects, one per column)
    #     return modelIndex.data(0, role)
    # 
    # def canFetchMore(self, parentIndex: QtCore.QModelIndex) -> bool:
    #     # TODO 2026-02-01 21:31:46
    #     return False if parentIndex.isValid() else self._displayedRows_ < self._modelDataRows_ or self._displayedColumns_ < self._modelDataColumns_
    # 
    # def fetchMore(self, parentIndex:QtCore.QModelIndex): 
    #     # TODO datetime2Qt
    #     if parentIndex.isValid():
    #         return
    # 
    # def flags(self, modelIndex: QtCore.QModelIndex) -> QtCore.Qt.ItemFlag:
    #     #  'ItemIsAutoTristate',
    #     #  'ItemIsDragEnabled',
    #     #  'ItemIsDropEnabled',
    #     #  'ItemIsEditable',
    #     #  'ItemIsEnabled',
    #     #  'ItemIsSelectable',
    #     #  'ItemIsUserCheckable',
    #     #  'ItemIsUserTristate',
    #     #  'ItemNeverHasChildren'
    # 
    #     return super().flags(modelIndex) if modelIndex.isValid() else QtCore.Qt.NoItemFlags # TODO 2026-02-01 21:31:43 — revisit this !!!
    # 
    # def setModelData(self, data: typing.Any, name: str = "",
    #                  showPrivate: bool = False, predicate = None,
    #                  top_title: str = "/", dataTypeStr: str = ""):
    #     # TODO 2026-02-01 21:32:05
    # 
    # 
    #     pass
    # 
    # def headerData(self, section: int, orientation: QtCore.Qt.Orientation,
    #                role:QtCore.Qt.ItemDataRole=QtCore.Qt.DisplayRole) -> QtCore.QVariant:
    #     # 'Horizontal',
    #     # 'Vertical'
    #     return self._rootItem_.data(section) if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole else QtCore.QVariant()
    # 
    # def index(self, row:int, column:int, parentIndex:QtCore.QModelIndex) -> QtCore.QModelIndex:
    #     # NOTE: 2026-02-01 21:59:46
    #     # There is no access to protected functions or signals for objects not created from Python;
    #     # this means one cannot call self.createIndex(…) here, and cannot override it!
    #     if not self.hasIndex(row, column, parent):
    #         return QtCore.QModelIndex() # invalid index
    # 
    #     # if parentIndex.isValid():
    #     #     return parentIndex.model().
    # 
    #     if parentIndex.isValid() and super().checkIndex(parentIndex):
    #         pass







class DataTreeView(QtWidgets.QTreeView):
    def __init__(self, *args, **kwargs):
        parent = kwargs.pop("parent", None)
        super().__init__(parent=parent)
