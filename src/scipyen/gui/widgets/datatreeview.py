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

try:
    from pyqtgraph.widgets.DataTreeWidget import HAVE_METAARRAY
except Exception:
    HAVE_METAARRAY = None


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
from imaging.axiscalibration import (
    AxesCalibration,
    AxisCalibrationData,
    ChannelCalibrationData,
)
from imaging.axisutils import axisTypeStrings

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

from core.utilities import (NestedFinder,
                            get_nested_value, set_nested_value,
                            unique)

from core.prog import (safewrapper, safeguiwrapper, print_styled, qVariants)

from core.traitcontainers import (DataBag, DataBagTraitsObserver,)

from core.scipyendataclasses import isDataclass

from gui.widgets.tablewidget import SimpleTableWidget
from gui.widgets.tableeditorwidget import (TableEditorWidget,
                                           TabularDataModel,)
from gui.pictgui import WorkerThread
from gui.widgets.small_widgets import QuantitySpinBox, ComplexSpinBox
from gui.delegates import PythonItemDelegate
from gui.workspacegui import GuiMessages

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
    try:
        from pyqtgraph.widgets.DataTreeWidget import HAVE_METAARRAY
    except Exception:
        HAVE_METAARRAY = None

    from core.datatypes import (is_namedtuple, TypeEnum)

    # NOTE: 2026-02-07 09:14:19 FIXME/TODO
    # these MUST be imported here to avoid cycling dependencies in
    # systems.PrairieView which needs this for the importer gui
    # (although, te latter should really go into a separate module to break the
    # cycle - TODO/FIXME 2026-02-07 09:15:32)
    from systems.PrairieView import (
        PVObject,
        PVScan,
        PVSequence,
        PVFrame,
        PVSystemConfiguration,
        PVStateShard,
        PVStateValue,
        PVIndexedValue,
        PVSubIndexedValue,
        PVSubIndexedValueList,
        PVLinescanDefinition,
    )


    mappingTypes = (dict, types.MappingProxyType)
    sequenceTypes = (typing.Sequence, tuple, list, deque, bytes)
    iterableCollectionTypes = sequenceTypes + mappingTypes

    sig_editCompleted = Signal([pd.DataFrame], [pd.Series], [np.ndarray], name="sig_editCompleted")
    sig_modelDataChanged = Signal(name="sig_modelDataChanged")

    _check_private_member_ = lambda x: (not isinstance(x[0], str)
                                        or not x[0].startswith("_"))

    def __init__(self: typing.Self, data: typing.Optional[typing.Any] = None,
                 dataName: str = None,
                 parent: typing.Optional[QtCore.QObject] = None,
                 **kwargs):
        super(DataTreeModel, self).__init__(0, 3, parent=parent)
        self._data_: typing.Optional[object] = None
        self._dataTypeStr_: str = ""
        self._visited_: dict = dict()
        self._rootTitle_ = "/"
        self._hasDynamicPrivate_: bool = False
        self._privateData_: dict = None
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
        self,
        obj: object,
        rootTitle: str = "",
        predicate: typing.Optional[types.FunctionType] = None,
        showPrivate: bool = False,
        dataTypeStr: typing.Optional[str] = None,
        hideRoot: bool = False,
    ):
        print(f"{self.__class__.__name__}.setModelData(obj: {type(obj).__name__})")
        self._visited_.clear()
        self._predicate_ = predicate
        self._showPrivate_ = showPrivate
        self._hideRoot_ = hideRoot

        (self._privateData_,
         self._hasDynamicPrivate_) = self._parseData_(obj, self._showPrivate_)

        self._data_ = obj
        self._dataTypeStr_ = dataTypeStr

        self._rootTitle_ = rootTitle if len(rootTitle.strip()) else "/"

        self._buildTree_(self._privateData_, self._rootTitle_)

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

    # @singledispatchmethod
    # def _getObjInfo_(self: typing.Self, obj: object) -> tuple:
    #     tip = type(obj).__name__
    #     if obj in (None, MISSING, pd.NA):
    #         info = f"{obj}"
    #         tip  = str(obj)
    #
    #     elif isDataclass(obj):
    #         datafields = dataclasses.fields(obj)
    #         n = len(datafields)
    #         info = f"{n} {strutils.pluralize('field', n)}"
    #         tip += " (dataclass)"
    #
    #     else:
    #         raise NotImplementedError(
    #         f"Objects of type {type(obj).__name__} are not supported"
    #         )
    #
    #     return info, tip

    # @_getObjInfo_.register(str)
    # @_getObjInfo_.register(bytes)
    # @_getObjInfo_.register(bytearray)
    # def _(self: typing.Self, obj: typing.Union[str, bytes, bytearray]) -> tuple:
    #     tip = type(obj).__name__
    #     n = len(obj)
    #     if n > 100:
    #         info = (
    #             obj[:97] if isinstance(obj, str) else obj.decode()[:97]
    #         )
    #         info += "..."
    #     else:
    #         info = obj if isinstance(obj, str) else obj.decode()
    #
    #     return info, tip

    # @_getObjInfo_.register(bool)
    # @_getObjInfo_.register(int)
    # @_getObjInfo_.register(float)
    # @_getObjInfo_.register(complex)
    # @_getObjInfo_.register(np.integer)
    # @_getObjInfo_.register(np.floating)
    # @_getObjInfo_.register(np.complexfloating)
    # def _(self: typing.Self,
    #       obj: typing.Union[bool, int, float, complex,
    #                         np.integer, np.floating,
    #                         np.complexfloating]) -> tuple:
    #     return f"{obj}", type(obj).__name__

    # @_getObjInfo_.register(list)
    # @_getObjInfo_.register(tuple)
    # @_getObjInfo_.register(deque)
    # @_getObjInfo_.register(set)
    # def _(self: typing.Self, obj: typing.Union[list, tuple, deque,
    #                                            set]) -> tuple:
    #     n = len(obj)
    #     tip = type(obj).__name__
    #     if is_namedtuple(obj):
    #         tip += " (namedtuple)"
    #     return f"{n} {strutils.pluralize('element', n)}", tip

    # @_getObjInfo_.register(dict)
    # def _(self: typing.Self, obj: dict) -> tuple:
    #     n = len(obj)
    #     return (f"{len(obj)} key / value {strutils.pluralize('pair', n)}",
    #             type(obj).__name__)

    # @_getObjInfo_.register(types.SimpleNamespace)
    # def _(self: typing.Self, obj: types.SimpleNamespace) -> tuple:
    #     d = obj.__dict__
    #     n = len(d)
    #     return f"{n} {strutils.pluralize('element', n)}", type(obj).__name__

    # @_getObjInfo_.register(pq.UnitQuantity)
    # @_getObjInfo_.register(pq.Quantity)
    # def _(self:typing.Self, obj: pq.Quantity) -> tuple:
    #     tip = scq.unitFamilyName(obj.units)
    #     if isinstance(pq.UnitQuantity):
    #         info = f"{obj} {scq.unitFamilyName(obj)}"
    #     else:
    #         if obj.size <= 1:
    #             info = f"{obj}"
    #         else:
    #             n = obj.size
    #             s = obj.shape
    #             info = f"Quantity array ({obj.units.dimensionality}) with {n} {strutils.pluralize('samples', n)}, shape {s}, and dtype {obj.dtype}"
    #
    #     return info, tip

    # @_getObjInfo_.register(np.ndarray)
    # def _(self: typing.Self, obj: np.ndarray) -> tuple:
    #     n = obj.size
    #     s = obj.shape
    #     if obj.size <= 1:
    #         info = f"{obj}"
    #     else:
    #         info = f"Array with {n} {strutils.pluralize('samples', n)}, shape {s}, and dtype {obj.dtype}"
    #
    #     return info, type(obj).__name__

    # @_getObjInfo_.register(vigra.filters.Kernel1D)
    # @_getObjInfo_.register(vigra.filters.Kernel2D)
    # def _(self: typing.Self,
    #       obj: typing.Union[vigra.filters.Kernel1D,
    #                         vigra.filters.Kernel2D]) -> tuple:
    #
    #     if isinstance(obj, vigra.filters.Kernel1D):
    #         n = int(obj.size())
    #         info = f"with {n} {strutils.pluralize('sample', n)}"
    #     else:
    #         h = int(obj.height())
    #         w = int(obj.width())
    #         info = f"with {h} × {w} {strutils.pluralize('sample', h*w)}"
    #
    #     return info, type(obj).__name__

    def _buildTree_(self: typing.Self,
                    obj: object,
                    name: str = "",
                    keyType: type = str,
                    nameTip: str = "",
                    typeStr: typing.Optional[str] = None,
                    # predicate: typing.Optional[types.FunctionType] = None,
                    # hideRoot: bool = False,
                    path: tuple = tuple()):

        # 1. get the top object symbol, type and some information, as items to
        # go as the first (and only) top-level row in the model

        # print(f"{self.__class__.__name__}._buildTree_(obj: {type(obj).__name__})")
        if isinstance(self._privateData_, dict):
            self._buildBranch_(self._privateData_, name,
                               self.invisibleRootItem(), 0)

    @singledispatchmethod
    def _buildBranch_(self: typing.Self,
                      obj: object,
                      objName: str,
                      parentItem: QtGui.QStandardItem,
                      row: int):
        # print(f"{self.__class__.__name__}._buildBranch_(obj: {type(obj).__name__})")
        rowItems = self._makeRowItems_(obj, objName)
        parentItem.insertRow(row, rowItems)

    @_buildBranch_.register(dict)
    def _(self: typing.Self, obj: dict, objName: str,
          parentItem: QtGui.QStandardItem, row: int):
        # print(f"{self.__class__.__name__}._buildBranch_(obj: {type(obj).__name__})")
        rowItems = self._makeRowItems_(obj, objName)
        parentItem.insertRow(row, rowItems)
        pItem = rowItems[0]
        k = 0
        for key, value in obj.items():
            if isinstance(key, str):
                vName = key
            else:
                vName = f"{key}"
            self._buildBranch_(value, vName, pItem, k)
            k += 1

    def _introspectable_(self: typing.Self, obj: object) -> bool:
        return (all(t not in self._supportedDataTypes_ for t in mro)
                         and not inspect.isroutine(obj)
                         and not isinstance(obj, (types.ModuleType,
                                             pkgutil.ModuleInfo))
                         and obj is not None)

    def _parseData(self: typing.Self, obj: object,
                   includePrivateMembers: bool = True) -> tuple:
        # NOTE: 2025-06-28 13:57:28
        # generate a mapping representation of obj's members upon which
        # the tree model is built
        # for dataclasses, use their fields
        # for non-dict classes inspect their members, allowing to ignore the
        # "private" members, i.e., those bound to symbols starting with
        # underscore ('_')
        pData, asPrivate = self._parseObj_(obj)
        if isinstance(pData, dict) and not includePrivateMembers:
            pData = dict(
                list(
                    filter(
                        self._check_private_member_,
                        pData.items()
                    )
                )
            )

        return pData, asPrivate

    @singledispatchmethod
    def _parseObj_(self, obj: object,
                   includePrivateMembers: bool = True) -> tuple:
        r"""
Returns:
========
a tuple: (parsed data, info dict), where *info dict* contains the mapping:

    "asPrivate" ↦ bool
        When ``True`` this flag the the object is represented by way of a private
        mapping (``self._privateData_``)

    dictwill trigger creation of sub-branches representing
        the structure in private data (a dict)
    ""

    """
        mro = inspect.getmro(type(obj))
        asPrivate: bool = False
        tip: str = type(obj).__name__
        hasChildren: bool = False

        print(f"{self.__class__.__name__}._parseObj_(obj: {tip})")

        if obj in (None, MISSING, pd.NA):
            pData = obj
            asPrivate = False
            info = f"{obj}"
            tip = f"{obj}"
            hasChildren: bool = False

        elif isDataclass(obj):
            datafields = dataclasses.fields(obj)
            try:
                fieldnames = list(map(lambda f: f.name, datafields))
                membernames = list(data.__dict__.keys())
                childnames = list(sorted(unique(membernames + fieldnames)))
                pData = dict(map(lambda c: (c, getattr(data, c)), childnames))
            except:
                traceback.print_exc()
                print(
                    f"{print_styled(f'for {type(data).__name__} data', color='red')}"
                )
                pData = dict(map(lambda x: (x.name, getattr(obj, x.name)), datafields))

            if not includePrivateMembers:
                pData = dict(
                    list(
                        filter(
                            self._check_private_member_,
                            pData.items()
                        )
                    )
                )

            n = len(pData)

            info = f"{n} {strutils.pluralize('member', n)}"
            tip = f"{type(obj).__name__} (dataclass)"
            asPrivate = True
            hasChildren: bool = True

        elif self.HAVE_METAARRAY and (
                hasattr(obj, "implements") and obj.implements("MetaArray")
            ):
            # NOTE: 2026-02-07 09:16:25 FIXME/TODO
            # either break the cycling import dependency at
            # NOTE: 2026-02-07 09:14:19 FIXME/TODO, or make sure to refer to
            # HAVE_METAARRAY int he self's namespace, where it is defined
            #
            # WARNING: 2026-02-07 09:18:42 Do the same with PrairieView object
            #
            pData = dict(
                    [("data", obj.view(np.ndarray)), ("meta", obj.infoCopy())]
                )
            asPrivate = True
            hasChildren: True
            info = ""

        elif self._introspectable_(obj) :
            pData = datatypes.inspect_members(obj, self._predicate_)
            if not includePrivateMembers:
                pData = dict(
                    list(
                        filter(
                            self._check_private_member_,
                            pData.items()
                        )
                    )
                )

            asPrivate = True
            hasChildren = True

            n = len(pData)
            info = f"{n} {strutils.pluralize('member', n)}"

        else:
            raise NotImplementedError(
            f"Objects of type {type(obj).__name__} are not supported"
            )
            # pData = obj
            # asPrivate = False
            # info = ""

        return pData, asPrivate, hasChildren, info, tip

    @_parseObj_.register(type)
    def _(self: typing.Self, obj: type,
                   includePrivateMembers: bool = True) -> tuple:
        info = f"Type object: {obj.__name__}"
        tip = str(obj)
        pData = obj
        return pData, False, False, info, tip

    @_parseObj_.register(dict)
    def _(self: typing.Self, obj: dict,
                   includePrivateMembers: bool = True) -> tuple:
        if not includePrivateMembers:
            pData = dict(
                list(
                    self._check_private_member_,
                    obj.items())
                    )
                )
        else:
            pData = obj

        n = len(pData)
        info = f"{len(obj)} key / value {strutils.pluralize('pair', n)}"
        tip = type(obj).__name__
        return obj, False, True, info, tip

    @_parseObj_.register(list)
    @_parseObj_.register(tuple)
    @_parseObj_.register(deque)
    @_parseObj_.register(set)
    def _(self: typing.Self,
          obj: typing.Union[list, tuple, deque, set],
                   includePrivateMembers: bool = True) -> tuple:

        tip = type(obj).__name__

        if is_namedtuple(obj):
            pData = obj._asDict()
            tip += "(namedtuple)"
        else:
            pData = dict(enumerate(obj))

        if not includePrivateMembers:
            pData = dict(
            list(
                    filter(
                        self._check_private_member_,
                        pData.items()
                    )
                )
            )

        n = len(pData)
        info = f"{n} {strutils.pluralize('element', n)}"

        return pData, True, True, info, tip

    @_parseObj_.register(str)
    @_parseObj_.register(bytes)
    @_parseObj_.register(bytearray)
    def _(self: typing.Self, obj: typing.Union[str, bytes, bytearray],
          _: bool = True) -> tuple:
        tip = type(obj).__name__
        n = len(obj)
        if n > 100:
            info = (
                obj[:97] if isinstance(obj, str) else obj.decode()[:97]
            )
            info += "..."
        else:
            info = obj if isinstance(obj, str) else obj.decode()

        return  obj, False, False, info, tip

    @_parseObj_.register(bool)
    @_parseObj_.register(int)
    @_parseObj_.register(float)
    @_parseObj_.register(complex)
    @_parseObj_.register(fractions.Fraction)
    @_parseObj_.register(decimal.Decimal)
    @_parseObj_.register(numbers.Number)
    @_parseObj_.register(np.integer)
    @_parseObj_.register(np.floating)
    @_parseObj_.register(np.complexfloating)
    def _(self: typing.Self,
          obj: typing.Union[bool, int, float, complex,
                            fractions.Fraction,
                            decimal.Decimal,
                            numbers.Number,
                            np.integer, np.floating, np.complexfloating],
          _: bool=True) -> tuple:

        return obj, False, False, f"{obj}", type(obj).__name__

    @_parseObj_.register(types.SimpleNamespace)
    def _(self: typing.Self, obj: types.SimpleNamespace,
                   includePrivateMembers: bool = True) -> tuple:
        pData = obj.__dict__
        if not includePrivateMembers:
            pData = dict(
            list(
                    filter(
                        self._check_private_member_,
                        pData.items()
                    )
                )
            )

        n = len(pData)
        info = f"{n} {strutils.pluralize('element', n)}"
        tip = type(obj).__name__
        return pData, True, True, info, tip

    @_parseObj_.register(types.ModuleType)
    def _(self: typing.Self, obj: types.ModuleType,
          includePrivateMembers: bool = True) -> tuple:
        tip = type(obj).__name__

        if hasattr(obj, "__name__"):
            mname = f" {obj._name__}"
        else:
            mname = ""

        if hasattr(obj, "__file__"):
            mfile = " from file " + obj.__file__
        else:
            mfile = ""

        mname = getattr(obj, "__name__", None)
        info = f"Module{mname}{mfile}"

        pData = obj.__dict__

        if not includePrivateMembers:
            pData = dict(
            list(
                    filter(
                        self._check_private_member_,
                        pData.items()
                    )
                )
            )

        return pData, True, True, info, tip

    @_parseObj_.register(vigra.filters.Kernel1D)
    @_parseObj_.register(vigra.filters.Kernel2D)
    def_(self: typing.Self,
         obj: typing.Union[vigra.filters.Kernel1D, vigra.filters.Kernel2D],
         _: bool = True) -> tuple:
        if isinstance(obj, vigra.filters.Kernel1D):
            n = int(obj.size())
            info = f"with {n} {strutils.pluralize('sample', n)}"
        else:
            h = int(obj.height())
            w = int(obj.width())
            info = f"with {h} × {w} {strutils.pluralize('sample', h*w)}"

        return obj, False, False, info, type(obj).__name__

    @_parseObj_.register(pd.DataFrame)
    @_parseObj_.register(pd.Series)
    @_parseObj_.register(pd.Index)
    def _(self: typing.Self,
          obj: typing.Union[pd.DataFrame, pd.Series, pd.Index],
          _: bool = True) -> tuple:
        nrows = len(obj)
        if isinstance(obj, pd.DataFrame):
            ncols = len(obj.columns)
            rows = strutils.pluralize('row', nrows)

            cols = strutils.pluralize('column', ncols)

            info = f"{nrows} {rows} × {ncols} {cols}"

        elif isinstance(obj, pd.Series):
            rows = strutils.pluralize('row', nrows)
            info = f"{nrows} {rows}, dtype = {obj.dtype}"

        else:
            rows = strutils.pluralize('element', nrows)
            info = f"{nrows} {rows}"

        tip = type(obj).__name__
        return obj, False, False, info, tip


    @_parseObj_.register(Interval)
    def _(self: typing.Self, obj: Interval) -> tuple:
        pData = {
                    "t0": obj.t0,
                    "t1": obj.t1,
                    "durations": obj.durations,
                    "extent": obj.extent,
                    "labels": obj.labels,
                    "annotations": obj.annotations,
                    "description": obj.description,
                }
        n = len(obj)
        desc = strutils.pluralize('subinterval', n)
        info = f"Interval '{obj.name}' with {len(obj)} {desc}"
        return pData, True, True, info, type(obj).__name__

    @_parseObj_.register(neo.Epoch)
    @_parseObj_.register(DataZone)
    def _(self: typing.Self, obj: typing.Union[neo.Epoch, DataZone]) -> tuple:
        pData = {
                    "times": obj.times,
                    "durations": obj.durations,
                    "labels": obj.labels,
                    "annotations": obj.annotations,
                    "description": obj.description,
                }

        n = len(obj)
        klass = "Zone" if isinstance(obj, DataZone) else Epoch
        desc = strutils.pluralize('subinterval', n)
        info = f"{klass} '{obj.name}' with {len(obj)} {desc}"
        return pData, True, True, info, type(obj).__name__

    @_parseObj_.register(neo.Event)
    @_parseObj_.register(DataMark)
    @_parseObj_.register(TriggerEvent)
    def _(self: typing.Self,
          obj: typing.Union[neo.Event, DataMark, TriggerEvent]) -> tuple:
        pData = {"times": obj.times, "labels": obj.labels}

        if isinstance(obj, (DataMark, TriggerEvent)):
            pData.update({"type": obj.type, "relative": obj.relative})

        pData.update({"annotations": obj.annotations, "description": obj.description})

        klass = "Mark" if isinstance(obj, DataMark) else tip

        tip = type(obj).__name__
        desc = strutils.pluralize('subinterval', n)
        info = f"{klass} '{obj.name}' with {len(obj)} {desc}"

        return pData, True, True, info, tip

    @_parseObj_.register(pq.Quantity)
    def _(self: typing.Self, obj: pq.Quantity, _: bool=True) -> tuple:
        tip = scq.unitFamilyName(obj.units)
        if isinstance(pq.UnitQuantity):
            info = f"{obj} {scq.unitFamilyName(obj)}"
        else:
            if obj.size <= 1:
                info = f"{obj}"
            else:
                n = obj.size
                s = obj.shape
                info = f"Quantity array ({obj.units.dimensionality}) with {n} {strutils.pluralize('samples', n)}, shape {s}, and dtype {obj.dtype}"

        return obj, False, False, info, tip

    @_parseObj_.register(vigra.VigraArray)
    def _(self: typing.Self, obj:vigra.VigraArray, _: bool = True) -> tuple:
        n = obj.size
        s = obj.shape
        samples = strutils.pluralize('samples', n)
        if obj.size <= 1:
            info = f"{obj}"
        else:
            info = f"Vigra Array with {n} {samples}, shape {s}, and dtype {obj.dtype}"

        pData = dict(enumerate(obj.axistags))

        return pData, True, True, info, type(obj.__name__)

    @_parseObj_.register(np.ndarray)
    def _(self: typing.Self, obj: np.ndarray, _: bool = True) -> tuple:
        n = obj.size
        s = obj.shape
        samples = strutils.pluralize('samples', n)
        if obj.size <= 1:
            info = f"{obj}"
        else:
            info = f"Array with {n} {samples}, shape {s}, and dtype {obj.dtype}"

        return obj, False, False, info, type(obj).__name__

    @_parseObj_.register(AxesCalibration)
    def _(self: typing.Self, obj: AxesCalibration, _:bool=True) -> tuple:
        pData = dict(enumerate(obj.calibrations))
        n = len(pData)
        info = f"{n} {strutils.pluralize('calibration', n)}"
        tip = type(obj).__name__

        return pData, True,, True, info, tip

    @_parseObj_.register(AxesCalibrationData)
    def _(self: typing.Self, obj: AxesCalibrationData) -> tuple:
        tip = type(obj).__name__
        asPrivate = False
        hasChildren = False
        if obj.isChannels:
            pData = dict(enumerate(obj.channels))
            asPrivate = True
            hasChildren = True
        else:
            pData = obj

        return pData, asPrivate, hasChildren, info, tip

    @_parseObj_.register(ChannelCalibrationData)
    def _(self: typing.Self,
          obj: ChannelCalibrationData, _: bool = True) -> tuple:
        tip = f"{type(obj).__name__}"
        info = " ".join(
            [
                tip,
                "with name:",
                f"'{obj.name}'",
                "index:",
                f"{obj.index}",
                "acquisition index:",
                f"{obj.acquisition_index}",
            ]
        )

            return obj, False, False, info, tip

    @_parseObj_.register(self.PVObject)
    def _(self: typing.Self, obj: self.PVObject) -> tuple:
        tip = type(obj).__name__
        info = tip
        if isinstance(obj, PVScan):
            info = f"{data_attributes}"

        elif isinstance(obj, PVSequence):
            nframes = len(obj.frames)
            info = f"{obj.attributes['sequencetypename']} with {nframes} {strutils.pluralize('frame', nframes)}"

        elif isinstance(obj, PVFrame):
            info = f"Channels: {obj.channels}"

        elif isinstance(obj, (PVSystemConfiguration, PVIndexedValue, PVSubIndexedValue)):
            if (
                hasattr(obj, "description")
                and isinstance(obj.description, str)
                and len(obj.description.strip())
                ):
                info = data.description

        return obj.as_dict(), True, True, info, tip

    @_parseObj_.register(scipy.optimize.Bounds)
    def _(self: typing.Self,
          obj: scipy.optimize.Bounds, _:bool = True) -> tuple:
        tip = type(obj).__name__
        pData = {
                    "lb": obj.lb,
                    "ub": obj.ub,
                    "keep_feasible": obj.keep_feasible,
                }
        info = ""
        return pData, True, True, info, tip







class DataTreeView(QtWidgets.QTreeView):
    def __init__(self, *args, **kwargs):
        parent = kwargs.pop("parent", None)
        super().__init__(parent=parent)
