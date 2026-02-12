# -*- coding: utf-8 -*-
# $Id: datatreeeditor.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

from __future__ import print_function

import os
# import warnings
import types
import traceback
# import itertools
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
from collections import deque, UserDict
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

HAS_MESHIO = False
try:
    import meshio
    HAS_MESHIO = True
except:
    pass

# from pyqtgraph import (DataTreeWidget, TableWidget, )

import neo
if neo.__version__ >= '0.13.0':
    from neo.core.objectlist import ObjectList as NeoObjectList
import quantities as pq
import numpy as np
import scipy
import pandas as pd
import vigra
import meshio
# ### END 3rd party modules

import core.datatypes as datatypes
from core.datatypes import (is_namedtuple, TypeEnum)
from core.prog import scipywarn
from core import taxonbridge
from core import bgbridge
# print(f"has brain globe: {bgbridge.hasBrainGlobe}")

# NOTE: 2026-02-07 09:14:19 FIXME/TODO
# to break cycling dependencies in systems.PrairieView, which needs this for the
# importer gui, MOVE the latter to a separate module
from systems.PrairieView import *

from imaging import vigrautils

import imaging.axiscalibration

from imaging.axiscalibration import (
    AxesCalibration,
    AxisCalibrationData,
    ChannelCalibrationData,
)

from imaging.axisutils import (axisTypeStrings,
                               getValueForAxisType,
                               getNameForAxisType)

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

from core.prog import (safewrapper, safeguiwrapper, print_styled, qVariants,
                       is_hashable)

from core.traitcontainers import (DataBag, DataBagTraitsObserver,)

from core.scipyendataclasses import isDataclass

from gui.widgets.tablewidget import SimpleTableWidget
from gui.widgets.tableeditorwidget import (TableEditorWidget,
                                           TabularDataModel,)
from gui.pictgui import WorkerThread
from gui.widgets.small_widgets import QuantitySpinBox, ComplexSpinBox
from gui.delegates import PythonItemDelegate
from gui.workspacegui import GuiMessages, WorkspaceGuiMixin
from gui.itemmodels.roles import *

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

class DataTreeModel(QtGui.QStandardItemModel):
    r"""
"""
    # TODO 2026-02-08 22:49:01
    # Support for:
    # struct array, recarray
    # neo.BaseSignal
    # types in the datetime module - needs additions to PythonItemDelegate
    #
    #
    # FIXME handling of Enum / TypeEnum values -> trigger the use of a ComboBox!


    mappingTypes = (dict, types.MappingProxyType)
    sequenceTypes = (typing.Sequence, tuple, list, deque, bytes)
    iterableCollectionTypes = sequenceTypes + mappingTypes

    sig_editCompleted = Signal([pd.DataFrame], [pd.Series], [np.ndarray], name="sig_editCompleted")
    sig_modelDataChanged = Signal(name="sig_modelDataChanged")

    @staticmethod
    def _check_private_member_(x: object, y: typing.Optional[object] = None):
        return (not isinstance(x[0], str)
                or not x[0].startswith("_"))

    # @staticmethod
    # def _check_private_member_2_(x: object, y: object):
    #     return self._check_private_member_(x)

    def __init__(self: typing.Self, data: typing.Optional[typing.Any] = None,
                 dataName: str = None,
                 parent: typing.Optional[QtCore.QObject] = None,
                 **kwargs):
        super(DataTreeModel, self).__init__(0, 3, parent=parent)
        self._modelData_: typing.Optional[object] = None
        self._dataTypeStr_: str = ""
        self._visited_: dict = dict()
        self._rootTitle_ = "/"
        self._hasDynamicPrivate_: bool = False
        self._privateData_: dict = None
        self._predicate_: types.FunctionType = None
        self._showPrivate_: bool = False
        self._hideRoot_: bool = False
        self._introspect_: bool = False
        self._topObjectItem_: typing.Optional[QtGui.QStandardItem] = None

        self._supportedDataTypes_ = kwargs.pop("supportedTypes", tuple())
        if not isinstance(self._supportedDataTypes_, tuple) or not all(
            isinstance(v, type) for v in self._supportedDataTypes_
        ):
            self._supportedDataTypes_ = tuple()

        self._readOnly_ = kwargs.pop("readOnly", True)

        self.setHorizontalHeaderLabels(["Object", "Type", "Value / Information"])

    @property
    def topObjectItem(self: typing.Self) -> QtGui.QStandardItem | None:
        return self._topObjectItem_

    def setModelData(
        self,
        obj: object,
        rootTitle: str = "",
        predicate: typing.Optional[types.FunctionType] = None,
        showPrivate: bool = False,
        dataTypeStr: typing.Optional[str] = None,
        hideRoot: bool = False,
    ):
        # print(f"{self.__class__.__name__}.setModelData(obj: {type(obj).__name__})")
        self._visited_.clear()
        self._predicate_ = predicate
        self._showPrivate_ = showPrivate
        self._hideRoot_ = hideRoot

        self._rootTitle_ = rootTitle if len(rootTitle.strip()) else "/"

        self._modelData_ = obj

        pData, objDict = self._parseObject_(obj, self._showPrivate_)

        self._privateData_ = pData
        self._dataTypeStr_ = objDict["objType"]

        self._buildTree_(self._privateData_, objDict, self._rootTitle_)

    def _makeObjectRow_(self: typing.Self, obj: object, /,
                       objDict: dict, objKey: object,
                       objKeyType: type) -> tuple:

        typeName = objDict["objType"].__name__

        info = objDict["objInfo"]
        memberAccess = objDict["memberAccess"]

        if isinstance(objKey, str):
            objName = objKey

        elif is_hashable(objKey):
            objName = f"{objKey}"

        else:
            objName = ""

        if len(objName.strip()) == 0:
            objName = "/"

        # print(f"{self.__class__.__name__}._makeObjectRow_: objName -> {objName}")

        item0 = QtGui.QStandardItem(objName)
        item0.setData(objName, QtCore.Qt.DisplayRole)
        item0.setData(objDict["objType"], ObjectTypeRole)

        # NOTE: 2026-02-09 21:47:10
        # used to construct the acess path to the object for this item
        item0.setData(QtCore.QVariant(memberAccess), ObjectDataAccessRole)



        # NOTE: 2026-02-09 21:47:38
        # reference to the actual Python object
        item0.setData(QtCore.QVariant(obj), ObjectDataRole)

        # NOTE: 2026-02-09 21:47:57
        # reference to the object's binding in its parent: e.g. symbol of an
        # attribute or field, index (for sequences), key (for mappings)
        item0.setData(QtCore.QVariant(objKey), ObjectKeyRole)

        # NOTE: 2026-02-09 21:49:05
        # object "bindings" are are int for sequences, any hashable object type
        # (including str and int) for mappings, str for attributes & fields.
        #
        # iterators are NOT supported (they're used to yield elements of a
        # collection dynamically, anyway, and a reason for using them is a
        # "lazy" evaluation of the colleciton's contents - in itself for a good
        # reason) ; therefore, I apply the same philosophy here
        #
        item0.setData(QtCore.QVariant(objKeyType), ObjectKeyTypeRole)

        # for user's benefit — good to know the type of the object is represented
        # in this row.
        item1 = QtGui.QStandardItem(typeName)
        item1.setData(typeName, QtCore.Qt.DisplayRole)
        # either:
        #
        # a) display some object info for the user's benefit; this can be:
        #
        #   a.1) a string representation of the object's value — can be edited
        #        if required, see below
        #
        #   a.2) additional information such as size, shape, dtype, for tabular
        #       data (arrays, pandas objects) — these are editable via an editor
        #       in the first child of item 0 when needed, to be set up by the
        #       client user of this model
        #
        # b) offer a delegate editor widget so that user can modify the value
        #
        # "choices" goes as item data with objectDataRole for THIS item
        item2 = QtGui.QStandardItem(f"{info}")
        item2.setData(info, QtCore.Qt.EditRole)
        # NOTE: 2026-02-10 09:33:22
        # execute the code line below NOT here, but conditionally in
        # self._buildBranch_:
        # item2.setData(QtCore.QVariant(obj), ObjectDataRole)
        item2.setData(objDict.get("choices", dict()), DataChoicesRole)

        #
        flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsEnabled
        for item in (item0, item1, item2):
            item.setFlags(flags)

        return (item0, item1, item2)

    def _buildTree_(self: typing.Self,
                    obj: object,
                    objDict: dict,
                    name: str = ""): #,
                    # path: tuple = tuple()):

        # 1. get the top object symbol, type and some information, as items to
        # go as the first (and only) top-level row in the model

        # print(f"{self.__class__.__name__}._buildTree_(obj: {type(obj).__name__})")
        if isinstance(self._privateData_, dict):
            self._topObjectItem_ = self._buildBranch_(self._privateData_,
                                                      objDict, name, str,
                                                      self.invisibleRootItem(),
                                                      0
                                                     )

        else: # TODO 2026-02-08 00:37:05 URGENT
            pass

    @singledispatchmethod
    def _buildBranch_(self: typing.Self, obj: object, objDict: dict,
                      objKey: object, objKeyType: type,
                      parentItem: QtGui.QStandardItem,
                      row: int) -> QtGui.QStandardItem:
        # print(f"{self.__class__.__name__}._buildBranch_(obj: {type(obj).__name__})")
        rowItems = self._makeObjectRow_(obj, objDict, objKey, objKeyType)
        parentItem.insertRow(row, rowItems)
        objItem = rowItems[0]
        if objDict["objDataAsChild"]:
            # NOTE: 2026-02-08 09:52:28 TODO
            # use data item roles to:
            # 1) flag to the TreeView using this model, that this is a dataItem
            #   and therefore span the entire row (i.e, ALL columns)
            #
            # 2) flag to the TreeView using this model, that this needs an
            #   item delegate for tabular-like data (DataFrame, Series, Index,
            #   ndarray)
            #
            #   2.1) set this to read-only in usual circumstances
            #
            dataItem = QtGui.QStandardItem("")
            dataItem.setData(QtCore.QVariant(True), StandaloneEditorWidgetRole)
            objItem.insertRow(0, [dataItem])
        else:
            dataItem = rowItems[-1]
            dataItem.setData(QtCore.QVariant(obj), ObjectDataRole)

        accessType = objDict.get("accessType", None)

        objItem.setData(QtCore.QVariant(accessType), ObjectDataAccessTypeRole)

        if isinstance(accessType, str) and len(accessType.strip()):
            tooltip = f"{accessType}"
            if accessType == "attribute":
                tooltip += f" of {parentItem.data(QtCore.Qt.DisplayRole)}"
            else:
                tooltip += f" into {parentItem.data(QtCore.Qt.DisplayRole)}"

            objItem.setData(QtCore.QVariant(tooltip), QtCore.Qt.ToolTipRole)
            objItem.setData(QtCore.QVariant(tooltip), QtCore.Qt.StatusTipRole)
            objItem.setData(QtCore.QVariant(tooltip), QtCore.Qt.WhatsThisRole)

        return objItem

    @_buildBranch_.register(dict)
    @_buildBranch_.register(UserDict)
    @_buildBranch_.register(types.MappingProxyType)
    def _(self: typing.Self, obj: (dict, types.MappingProxyType, UserDict),
          objDict: dict, objKey: object, objKeyType: type,
          parentItem: QtGui.QStandardItem, row: int) -> QtGui.QStandardItem:

        rowItems = self._makeObjectRow_(obj, objDict, objKey, objKeyType)
        parentItem.insertRow(row, rowItems)
        pItem = rowItems[0]

        k = 0

        if objDict["objDataAsChild"]:
            # NOTE: 2026-02-08 09:53:31 TODO
            # see NOTE: 2026-02-08 09:52:28 TODO
            dataItem = QtGui.QStandardItem("")
            pItem.insertRow(0, [dataItem])
            k += 1

        else:
            accessType = objDict.get("accessType", None)

            pItem.setData(QtCore.QVariant(accessType), ObjectDataAccessTypeRole)

            if isinstance(accessType, str) and len(accessType.strip()):
                tooltip = f"{accessType}"
                if accessType == "attribute":
                    tooltip += f" of {parentItem.data(QtCore.Qt.DisplayRole)}"
                else:
                    tooltip += f" into {parentItem.data(QtCore.Qt.DisplayRole)}"

                pItem.setData(QtCore.QVariant(tooltip), QtCore.Qt.ToolTipRole)
                pItem.setData(QtCore.QVariant(tooltip), QtCore.Qt.StatusTipRole)
                pItem.setData(QtCore.QVariant(tooltip), QtCore.Qt.WhatsThisRole)

        for key, value in obj.items():
            if isinstance(key, str):
                keyName = key
            else:
                keyName = f"{key}"

            pValue, valDict = self._parseObject_(value, self._showPrivate_)
            self._buildBranch_(pValue, valDict, keyName, type(key), pItem, k)
            k += 1


        return pItem

    def _introspectable_(self: typing.Self, obj: object) -> bool:
        return (all(t not in self._supportedDataTypes_ for t in mro)
                         and not inspect.isroutine(obj)
                         and not isinstance(obj, (types.ModuleType,
                                             pkgutil.ModuleInfo))
                         and obj is not None)

    @singledispatchmethod
    def _parseObject_(self, obj: object,
                      includePrivateMembers: bool = False,
                      objBinding: typing.Optional[typing.Union[str, int]] = None,
                   ) -> tuple:
        r"""
Returns:
========
a tuple: (``parsedData``, ``infoDict``), where:

    ``parsedData`` if either ``obj`` itself, or a ``dict`` representation of it

    ``infoDict`` is the mapping:

    "indirect" ↦ bool
        When ``False``, ``self._privateData_`` attribute is ``obj`` itself, and
        ``obj`` is represented by a single row (the *object row*). The
        *object row* ia a child of the parent tree item, which is either the
        *invisibile root item* of the model or a row / branch representation of
        the container of ``obj``.

        When ``True`` this flag indicates that ``parsedData`` is in fact a
        ``dict`` representation of the object's structure. Members of ``obj``
        are to be represented as tree sub-branches (*member rows*) children of
        the *object row*. When ``includePrivateMembers`` is ``False`` (the default),
        private members of ``obj`` are excluded from this representation. All
        *member rows* follow a possible *data row* (see below).

    "objDataAsChild" ↦ bool
        When ``True``, the contents of ``obj`` should be displayed in a widget
        on its own, in the first row (*data row*) child (branch) of the *object row*.
        If, in addition, ``obj`` is represented indirectly by a ``dict``
        (``parsedData``, see above), all *member rows* **must** follow the
        *data row*.

    "objInfo" ↦ str
        When ``obj`` is a scalar number or singleton array, this is a string
        representaion of ``obj`` *value* and can be made editable, unless the
        model is configured to introspect all members of ``obj``.

        When ``obj`` is representable as a ``dict`` (see above) **or** the model
        is set up to introspect members of ``obj`` regardless of its type, then
        **objInfo** contains abrief description of ``obj`` (one line).

    "objType" ↦ str
        The type name of ``obj``.

    "objTip" ↦ str
        Contents of the UI tooltip to be shown when the *object row* is hovered.

    "memberAccess" ↦ typing.Tuple[str]

    "choices" ↦ dict, mapping name ↦ value - used in enums and enum-like objects
        where a combo box is appropriate for choosing a value from a predefined
        set; for all other object types, this will be empty.

    """
        # mro = inspect.getmro(type(obj))
        indirect: bool = False
        tip: str = type(obj).__name__
        objDataAsChild: bool = False
        objType = type(obj)
        choices = dict()

        # print(f"{self.__class__.__name__}._parseObject_(obj: {tip})")

        if isDataclass(obj):
            datafields = dataclasses.fields(obj)
            try:
                fieldnames = list(map(lambda f: f.name, datafields))
                membernames = list(obj.__dict__.keys())
                childnames = list(sorted(unique(membernames + fieldnames)))
                pData = dict(map(lambda c: (c, getattr(obj, c)), childnames))
            except:
                traceback.print_exc()
                print(
                    f"{print_styled(f'for {type(obj).__name__} data', color='red')}"
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
            indirect = True
            objDataAsChild = False
            memberAccess = (".",)
            accessType = "attribute"

        elif HAVE_METAARRAY and (
                hasattr(obj, "implements") and obj.implements("MetaArray")
            ):
            pData = dict(
                    [("data", obj.view(np.ndarray)), ("meta", obj.infoCopy())]
                )
            indirect = True
            objDataAsChild = False
            info = ""
            memberAccess = ("[", "]")
            accessType = "index"

        # elif self._introspect_ and self._introspectable_(obj) :
        #     pData = datatypes.inspect_members(obj, self._predicate_)
        #     if not includePrivateMembers:
        #         pData = dict(
        #             list(
        #                 filter(
        #                     self._check_private_member_,
        #                     pData.items()
        #                 )
        #             )
        #         )
        #
        #     indirect = True
        #     objDataAsChild = True
        #
        #     n = len(pData)
        #     info = f"{n} {strutils.pluralize('member', n)}"

        elif HAS_MESHIO and isinstance(obj, meshio.Mesh):
            pData = obj
            indirect=False,
            s = " × ".join(list(map(lambda x: f"{x}", obj.points.shape)))
            info = f"{obj.points.size} points ({s})"
            tip = type(obj).__name__
            objDataAsChild = False
            memberAccess = tuple()
            accessType = None

        else:
            pData = obj
            indirect = False
            info = f"{obj}"
            tip = f"{obj}"
            objDataAsChild = False
            memberAccess = tuple()
            accessType = None
            scipywarn(f"TODO: Support for objects of type {type(obj).__name__} awaits implementation. FIXME")
            # raise NotImplementedError(
            # f"Objects of type {type(obj).__name__} are not supported"
            # )

        return pData, {
            "indirect": indirect, "objDataAsChild": objDataAsChild,
            "objInfo": info,
            "objType": type(obj).__name__,
            "memberAccess": memberAccess,
            "accessType": accessType,
            "objTip": tip,
            "objType": objType,
            "choices": choices,
            }

    @_parseObject_.register(type(None))
    @_parseObject_.register(type(MISSING))
    @_parseObject_.register(type(pd.NA))
    def _(self: typing.Self, obj: (type(None), type(MISSING), type(pd.NA)),
          _:bool = False) -> tuple:
        objType = type(obj)
        pData = obj
        indirect = False
        info = f"{obj}"
        tip = f"{obj}"
        objDataAsChild = False
        memberAccess = tuple()
        accessType = None

        return pData, {
            "indirect": indirect,
            "objDataAsChild": objDataAsChild,
            "objInfo": info,
            "objType": type(obj).__name__,
            "memberAccess": memberAccess,
            "accessType": None,
            "objTip": tip,
            "objType": objType,
            "choices": dict(),
            }

    @_parseObject_.register(datetime.datetime)
    @_parseObject_.register(datetime.date)
    @_parseObject_.register(datetime.time)
    @_parseObject_.register(datetime.timedelta)
    @_parseObject_.register(datetime.timezone)
    def _(self: typing.Self, obj: (datetime.datetime, datetime.date,
                                   datetime.time,
                                   datetime.timedelta, datetime.timezone),
          _:bool = False) -> tuple:
        objType = type(obj)
        pData = obj
        indirect = False
        info = f"{obj}"
        tip = f"{obj}"
        objDataAsChild = False
        memberAccess = tuple()
        accessType = None

        return pData, {
            "indirect": indirect,
            "objDataAsChild": objDataAsChild,
            "objInfo": info,
            "objType": type(obj).__name__,
            "memberAccess": memberAccess,
            "accessType": accessType,
            "objTip": tip,
            "objType": objType,
            "choices": dict(),
            }

    @_parseObject_.register(types.FunctionType)
    @_parseObject_.register(types.MethodType)
    def _(self: typing.Self, obj: (types.FunctionType, types.MethodType),
          _:bool = False) -> tuple:
        objType = type(obj)
        tip = f"{obj}"
        word = "Fuction" if isinstance(obj, types.FunctionType) else "Method"
        info = f"{word} {obj.__qualname__}{inspect.signature(obj)} from module {obj.__module__}"

        return obj, {
            "indirect": False,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": tuple(),
            "accessType": None,
            "choices": dict(),
            }

    @_parseObject_.register(type)
    @_parseObject_.register(enum.EnumType)
    @_parseObject_.register(enum.Enum)
    @_parseObject_.register(TypeEnum)
    def _(self: typing.Self,
          obj: typing.Union[type, enum.EnumType, enum.Enum, TypeEnum],
          includePrivateMembers: bool = False) -> tuple:
        objType = type(obj)
        info = obj
        tip = str(obj)
        pData = obj
        choices = dict()
        memberAccess = tuple()
        accessType = None

        if isinstance(obj, (enum.EnumType, TypeEnum, enum.Enum)):
            memberAccess = (".", )
            accessType = "attribute"
            if isinstance(obj, (enum.Enum, TypeEnum)):
                info = obj.name
            if hasattr(obj, "__members__"):
                choices = dict(obj.__members__)
            else:
                try:
                    choices = dict(zip(obj.names(), obj.values()))
                    # choices = list(obj.names())
                except:
                    scipywarn(f"Cannot access enumeration values for {type(obj).__name__}")
                    choices = dict()

        return obj, {
            "indirect": False,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": memberAccess,
            "accessType": accessType,
            "choices": choices,
            }

    @_parseObject_.register(pkgutil.ModuleInfo)
    def _(self: typing.Self, obj: pkgutil.ModuleInfo,
                includePrivateMembers: bool = False) -> tuple:
        objType = type(obj)
        pData = dict(map(lambda f: (f, getattr(obj, f, None)), obj._fields))
        info = f"{len(pData)} fields"

        return obj, {
            "indirect": True,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".",),
            "accessType": "attribute",
            "choices": dict(),
            }

    @_parseObject_.register(taxonbridge.Taxon)
    def _(self: typing.Self, obj: taxonbridge.Taxon,
                includePrivateMembers: bool = False) -> tuple:
        objType = type(obj)
        pData = obj.__dict__
        indirect = True
        info = f"{obj}"
        if not includePrivateMembers:
            pData = dict(
                list(
                    filter(
                        self._check_private_member_,
                        pData.items()
                    )
                    )
                )

        tip = type(obj).__name__
        return pData, {
            "indirect": indirect,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".",),
            "accessType": "attribute",
            "choices": dict(),
            }

    @_parseObject_.register(dict)
    @_parseObject_.register(types.MappingProxyType)
    @_parseObject_.register(UserDict)
    def _(self: typing.Self, obj: (dict, types.MappingProxyType, UserDict),
                   includePrivateMembers: bool = False) -> tuple:
        objType = type(obj)
        # NOTE: 2021-07-20 09:52:34
        # dict objects with mixed key types cannot be sorted
        # therefore we resort to an indexing vector
        ndx = [
            i[1]
            for i in sorted(
                (str(k[0]), k[1])
                for k in zip(obj.keys(), range(len(obj)))
            )
        ]

        if isinstance(obj, UserDict):
            # print(f"{self.__class__.__name__}._parseObject_({type(obj)})")
            pData = obj
            indirect = False
        else:
            items = [i for i in obj.items()]
            pData = dict([items[k] for k in ndx])
            indirect = False

        if not includePrivateMembers:
            pData = dict(
                list(
                    filter(
                        self._check_private_member_,
                        pData.items()
                    )
                    )
                )

        n = len(pData) # CAUTION: this might include private members !!!
        info = f"{len(obj)} key / value {strutils.pluralize('pair', n)}"
        tip = type(obj).__name__

        return obj, {
            "indirect": indirect,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip":tip,
            "memberAccess": ("[", "]"),
            "accessType": "key",
            "choices": dict(),
            }

    @_parseObject_.register(list)
    @_parseObject_.register(tuple)
    @_parseObject_.register(deque)
    @_parseObject_.register(NeoObjectList)
    @_parseObject_.register(set)
    def _(self: typing.Self,
          obj: typing.Union[list, tuple, deque, set, NeoObjectList],
                   includePrivateMembers: bool = False) -> tuple:
        objType = type(obj)
        tip = objType.__name__

        if is_namedtuple(obj):
            pData = obj._asDict()
            tip += "(namedtuple)"
            memberAccess = (".",)
            accessType = "attribute"
        else:
            pData = dict(enumerate(obj))
            memberAccess = ("[","]")
            accessType = "index"

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

        return pData, {
            "indirect": True,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": memberAccess,
            "accessType": accessType,
            "choices": dict(),
            }

    @_parseObject_.register(str)
    @_parseObject_.register(bytes)
    @_parseObject_.register(bytearray)
    def _(self: typing.Self, obj: typing.Union[str, bytes, bytearray],
          _: bool = True) -> tuple:
        objType = type(obj)
        tip = objType.__name__
        n = len(obj)
        if n > 100:
            info = (
                obj[:97] if isinstance(obj, str) else obj.decode()[:97]
            )
            info += "..."
        else:
            info = obj if isinstance(obj, str) else obj.decode()

        return  obj, {
            "indirect": False,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": tuple(),
            "accessType": None,
            "choices": dict(),
            }

    @_parseObject_.register(pathlib.Path)
    def _(self: typing.Self, obj: pathlib.Path,
          _: bool = True) -> tuple:
        objType = type(obj)
        info = f"{obj}"
        tip = objType.__name__
        pData = obj.as_posix()
        indirect = True
        return  pData, {
            "indirect": indirect,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": tuple(),
            "accessType": None,
            "choices": dict()
            }

    @_parseObject_.register(bool)
    @_parseObject_.register(int)
    @_parseObject_.register(float)
    @_parseObject_.register(complex)
    @_parseObject_.register(fractions.Fraction)
    @_parseObject_.register(decimal.Decimal)
    @_parseObject_.register(numbers.Number)
    @_parseObject_.register(np.integer)
    @_parseObject_.register(np.floating)
    @_parseObject_.register(np.complexfloating)
    def _(self: typing.Self,
          obj: typing.Union[bool, int, float, complex,
                            fractions.Fraction,
                            decimal.Decimal,
                            numbers.Number,
                            np.integer, np.floating, np.complexfloating],
          _: bool=True) -> tuple:
        objType = type(obj)
        tip = objType.__name__
        return obj, {
            "indirect": False, "objDataAsChild": False,
            "objInfo": obj,
            "objType": objType,
            "objTip": tip,
            "memberAccess": tuple(),
            "accessType": None,
            "choices": dict(),
            }

    @_parseObject_.register(types.SimpleNamespace)
    def _(self: typing.Self, obj: types.SimpleNamespace,
                   includePrivateMembers: bool = False) -> tuple:
        objType = type(obj)
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
        info = f"{n} {strutils.pluralize('member', n)}"
        tip = type(obj).__name__
        return pData, {
            "indirect": True,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": dict(),
            }

    @_parseObject_.register(types.ModuleType)
    def _(self: typing.Self, obj: types.ModuleType,
          includePrivateMembers: bool = False) -> tuple:
        objType = type(obj)
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

        return pData, {
            "indirect": True,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": dict(),
            }

    @_parseObject_.register(vigra.filters.Kernel1D)
    @_parseObject_.register(vigra.filters.Kernel2D)
    def _(self: typing.Self,
           obj: typing.Union[vigra.filters.Kernel1D, vigra.filters.Kernel2D],
           _: bool = True) -> tuple:
        # ### BEGIN NOTE: 2026-02-08 21:20:00 TODO/FIXME
        #
        # enable representation of the kernel as: (think hard & choose one)
        #
        # for 1D kernels:
        # ===============
        #
        # REMEMBER: read-write access to the sample values for a 1D kernel is:
        # k1d[k] where k varies from [-s to s] where s is the kernel window,
        # e.g.
        #
        # .. ::
        #
        #   from matplotlib import pyplot as plt
        #
        #   g1d = vigra.filters.Kernel1D()
        #   g1d.initGaussian(1.0, 1.0, 2.0) # window = 2
        #   x,y = vigrautils.lernel2array(g1d)
        #   x
        #   array([-2, -1,  0,  1,  2])
        #   y
        #   array([0.0545, 0.2442, 0.4026, 0.2442, 0.0545])
        #
        #   g1d[-1] = 0.3
        #
        #   -> y = array([0.0545, 0.3, 0.4026, 0.2442, 0.0545])
        #
        #   plt.plot(x,y,'o')
        #
        #
        # (a) pd.Series -> TabeEditorWidget: probably the most intuitively
        #   accessible, but not straightforward as it involves an extra layer
        #  of bidirectional conversion
        #
        # (b) 2D np.ndarray, with sample indices in the 1st, *immutable* column,
        #   and sample values in the second -> TableEditorWidget
        #
        #   also requires bidirectional conversion, but the vigrautils can do the
        #   trick, and editing is done directly without need to convert indices.
        #
        # (c) as a dict mapping kernel_sample_index ↦ sample value
        #   {-2: 0.0545, -1: 0.2442, 0: 0.4026, 1: 0.2442, 2: 0.0545}
        #   -> delegate editor for each value
        #       this MAY seem straightforward, but unwieldy / cumbersome
        #       appearance for large kernels
        #
        #
        # for 2D kernels:
        # ===============
        #
        # Read-write access to the sample is of the form k2d[x,y]
        #
        # .. ::
        #
        #   from matplotlib import pyplot as plt
        #
        #   g2d = vigra.filters.Kernel2D()
        #   g2d.initDisk(1) # disk (averaging) kernel with radius 1
        #   x, y, z = vigrautils.kernel2array(g2d)
        #
        #   x
        #   -> array([[ 1,  0, -1],
        #             [ 1,  0, -1],
        #             [ 1,  0, -1]], shape=(3, 3)) # x coordinates of each column
        #
        #   y
        #   -> array([[ 1,  1,  1],
        #             [ 0,  0,  0],
        #             [-1, -1, -1]], shape=(3, 3)) # y coordinates of each row
        #
        #   z
        #   -> array([[0.1111, 0.1111, 0.1111],
        #             [0.1111, 0.1111, 0.1111],
        #             [0.1111, 0.1111, 0.1111]], shape=(3, 3)) # sample values
        #
        #   fig, ax = plt.subplots()
        #   ax.pcolormesh(x,y,z)
        #
        # I don't seem to have many options here: use ogrid option to get the
        #   x, y mesh coordinates and kernel sample values, then create a
        #   pd.DataFrame with column index the X array, roww index Y array
        #   and data, the sample values ... then use TableEditorWidget...
        #
        # TODO/FIXME: 2026-02-08 23:12:56
        # Better still, enable direct editing in
        # TableEditorWidget/TabularDataModel possibly via pd.DataFrame
        # FIXME/TODO
        #
        # ### END   NOTE: 2026-02-08 21:20:00 TODO/FIXME

        objType = type(obj)
        tip = type(obj).__name__
        if isinstance(obj, vigra.filters.Kernel1D):
            n = int(obj.size())
            info = f"with {n} {strutils.pluralize('sample', n)}"
            memberAccess = ("[","]")
            accessType = "index"
        else:
            h = int(obj.height())
            w = int(obj.width())
            info = f"with {h} × {w} {strutils.pluralize('sample', h*w)}"
            memberAccess = ("[", ",", "]")
            accessType = "indexes"

        return obj, {
            "indirect": False,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": memberAccess,
            "accessType": accessType,
            "choices": dict(),
            }

    @_parseObject_.register(pd.DataFrame)
    @_parseObject_.register(pd.Series)
    @_parseObject_.register(pd.Index)
    def _(self: typing.Self,
          obj: typing.Union[pd.DataFrame, pd.Series, pd.Index],
          _: bool = True) -> tuple:

        objType = type(obj)
        # NOTE: 2026-02-11 21:09:34
        # TableEditorWidget gives direct read-write access, so no direct access
        # required in this model
        memberAccess = tuple()

        # Don;t be fooled by the nomenclature; for a column index, this is the
        # number of columns
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

        return obj, {
            "indirect": False,
            "objDataAsChild": True,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": memberAccess,
            "accessType": None,
            "choices": dict(),
            }


    @_parseObject_.register(Interval)
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
        objType = type(obj)
        tip = type(obj).__name__
        n = len(obj)
        desc = strutils.pluralize('subinterval', n)
        info = f"Interval '{obj.name}' with {len(obj)} {desc}"

        return pData, {
            "indirect": True,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": dict(),
            }

    @_parseObject_.register(neo.Epoch)
    @_parseObject_.register(DataZone)
    def _(self: typing.Self, obj: typing.Union[neo.Epoch, DataZone]) -> tuple:
        objType = type(obj)
        pData = {
                    "times": obj.times,
                    "durations": obj.durations,
                    "labels": obj.labels,
                    "annotations": obj.annotations,
                    "description": obj.description,
                }

        tip = type(obj).__name__
        n = len(obj)
        klass = "Zone" if isinstance(obj, DataZone) else Epoch
        desc = strutils.pluralize('subinterval', n)
        info = f"{klass} '{obj.name}' with {len(obj)} {desc}"

        return pData, {
            "indirect": True,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": dict(),
            }

    @_parseObject_.register(neo.Event)
    @_parseObject_.register(DataMark)
    @_parseObject_.register(TriggerEvent)
    def _(self: typing.Self,
          obj: typing.Union[neo.Event, DataMark, TriggerEvent]) -> tuple:
        objType = type(obj)
        pData = {"times": obj.times, "labels": obj.labels}

        if isinstance(obj, (DataMark, TriggerEvent)):
            pData.update({"type": obj.type, "relative": obj.relative})

        pData.update({"annotations": obj.annotations, "description": obj.description})

        klass = "Mark" if isinstance(obj, DataMark) else tip

        tip = type(obj).__name__
        desc = strutils.pluralize('subinterval', n)
        info = f"{klass} '{obj.name}' with {len(obj)} {desc}"

        return pData, {
            "indirect": True,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": dict(),
            }

    @_parseObject_.register(pq.Quantity)
    def _(self: typing.Self, obj: pq.Quantity, _: bool=True) -> tuple:
        objType = type(obj)
        tip = f"{scq.unitFamilyName(obj.units)} quantity"
        if isinstance(obj, pq.UnitQuantity):
            info = f"{obj} {scq.unitFamilyName(obj)}"
            objDataAsChild = False
        else:
            if obj.size <= 1:
                info = obj
                objDataAsChild = False
            else:
                n = obj.size
                s = " × ".join(list(map(lambda x: f"{x}", obj.shape)))
                info = f"Quantity array ({obj.units.dimensionality}) with {n} {strutils.pluralize('samples', n)}; shape {s}; dtype {obj.dtype}."
                objDataAsChild = True

        return obj, {
            "indirect": False,
            "objDataAsChild": objDataAsChild,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": dict(),
            }

    @_parseObject_.register(vigra.VigraArray)
    def _(self: typing.Self, obj:vigra.VigraArray, _: bool = True) -> tuple:
        objType = type(obj)
        # NOTE: 2026-02-11 21:11:11
        # member access relates to metadata attributes (i.e., axistags);
        # the array data has read-write access to the underlying array via the
        # TableEditorWidget in the child item
        n = obj.size
        s = f"{obj.shape}"
        c = obj.channels
        axtags = ", ".join(list(map(lambda i: f"'{i.key}'", obj.axistags)))
        samples = strutils.pluralize('samples', n)
        objDataAsChild = False
        if obj.size <= 1:
            info = obj
        else:
            objDataAsChild = True
            info = f"Vigra Array with {n} {samples}; shape {s}; axistags: {axtags}; {c} channels; dtype {obj.dtype}."

        pData = dict(enumerate(obj.axistags))

        tip = type(obj).__name__

        return pData, {
            "indirect": True,
            "objDataAsChild": objDataAsChild,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": dict(),
            }


    @_parseObject_.register(np.ndarray)
    def _(self: typing.Self, obj: np.ndarray, _: bool = False) -> tuple:
        objType = type(obj)
        # TableEditorWidget gives read-write access to array data
        tip = type(obj).__name__
        n = obj.size
        shape = obj.shape
        s = f"{obj.shape}"
        samples = strutils.pluralize('sample', n)
        objDataAsChild = False
        if obj.size <= 1:
            info = obj
        else:
            objDataAsChild = True
            info = f"Array with {n} {samples}; shape {s}; dtype {obj.dtype}."

        return obj, {
            "indirect": False,
            "objDataAsChild": objDataAsChild,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": tuple(),
            "accessType": None,
            "choices": dict(),
            }

    @_parseObject_.register(vigra.AxisInfo)
    def _(self: typing.Self, obj: vigra.AxisInfo, _: bool = False) -> tuple:
        objType = type(obj)
        info = f"{type(obj).__name__} ({getNameForAxisType(obj.typeFlags)}) key {obj.key}"
        tip = type(obj).__name__
        pData = {"resolution": obj.resolution, "description": obj.description,
                 "typeFlags": obj.typeFlags}

        return pData, {
            "indirect": True,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": dict()
            }

    @_parseObject_.register(vigra.AxisType)
    def _(self: typing.Self, obj: vigra.AxisType, _: bool = False) -> tuple:
        # NOTE: 2026-02-08 22:54:09 TODO
        # Don't really want to edit this via GUI, so no member access for now
        objType = type(obj)
        tip = type(obj).__name__
        info = f"{tip}: {getNameForAxisType(obj)} ({getValueForAxisType(obj)})"

        return obj, {
            "indirect": False,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": tuple(),
            "accessType": None,
            "choices":  {vigra.AxisType.names},
            }

    @_parseObject_.register(AxesCalibration)
    def _(self: typing.Self, obj: AxesCalibration, _:bool=True) -> tuple:
        objType = type(obj)
        pData = dict(enumerate(obj.calibrations))
        n = len(pData)
        info = f"{n} {strutils.pluralize('calibration', n)}"
        tip = type(obj).__name__

        return pData, {
            "indirect": True,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": dict(),
            }

    @_parseObject_.register(AxisCalibrationData)
    def _(self: typing.Self, obj: AxisCalibrationData) -> tuple:
        objType = type(obj)
        tip = type(obj).__name__
        indirect = True
        objDataAsChild = False
        fields = dataclasses.fields(obj)
        fieldnames = list(map(lambda f: f.name, datafields))
        pData = dict(map(lambda c: (c, getattr(data, c)), filter(lambda f: f != "channel", fieldnames)))
        if not obj.isChannels:
            pData = dict(map(lambda c: (c, getattr(data, c)), filter(lambda f: f != "channel", fieldnames)))
            info = f"Axis calibration for axis {obj.index} (type {obj.type}; key {obj.key}); size {obj.size}"
        else:
            pData = dict(map(lambda c: (c, getattr(data, c)), fieldnames))
            c = len(obj.channels)
            info = f"Channel axis calibration with {c} {strutils.pluralize('channel', c)}"

        return pData, {
            "indirect": indirect,
            "objDataAsChild": objDataAsChild,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": dict(),
            }

    @_parseObject_.register(ChannelCalibrationData)
    def _(self: typing.Self,
          obj: ChannelCalibrationData, _: bool = True) -> tuple:
        objType = type(obj)
        tip = f"{type(obj).__name__}"
        fields = dataclasses.fields(obj)
        fieldnames = list(map(lambda f: f.name, datafields))
        pData = dict(map(lambda c: (c, getattr(data, c)), fieldnames))

        return pData, {
            "indirect": True,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": dict(),
            }

    @_parseObject_.register(PVObject)
    def _(self: typing.Self, obj: PVObject) -> tuple:
        objType = type(obj)
        tip = type(obj).__name__
        info = tip
        if isinstance(obj, PVScan):
            info = f"{obj.attributes}"

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

        return obj.as_dict(), {
            "indirect": True,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objtip": tip,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": dict(),
            }

    @_parseObject_.register(scipy.optimize.Bounds)
    def _(self: typing.Self,
          obj: scipy.optimize.Bounds, _:bool = True) -> tuple:
        objType = type(obj)
        tip = type(obj).__name__
        pData = {
                    "lb": obj.lb,
                    "ub": obj.ub,
                    "keep_feasible": obj.keep_feasible,
                }
        info = ""
        return pData, {
            "indirect": True,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip ,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": dict(),
            }

    def itemChildren(self: typing.Self,
                     item: QtGui.QStandardItem) -> typing.List:
        if not item.hasChildren():
            return list()

        return list(map(lambda k: item.child(k, 0), range(item.rowCount())))

    def getDataObjectForLeaf(self: typing.Self,
                             leaf: typing.Union[QtCore.QModelIndex,
                                                QtGui.QStandardItem],
                             byPath: bool = True,
                             ) -> object:

        if byPath:
            path = self._getPathForItemOrIndex_(leaf)
            # print(f"{self.__class__.__name__}.getDataObjectForLeaf: -> path = {path}")
            if len(path):
                if path[-1] == self._topObjectItem_.data(QtCore.Qt.DisplayRole):
                    path[-1] = "self._modelData_"

            accessExpr = "".join(list(reversed(path)))
            # print(f"{self.__class__.__name__}.getDataObjectForLeaf: -> accessExpr = {accessExpr}")
            return eval(accessExpr)

        else:
            return leaf.data(ObjectDataRole)

    def getPathForLeaf(self: typing.Self,
                       leaf: typing.Union[QtCore.QModelIndex,
                                          QtGui.QStandardItem],
                       pathOnly: bool = False,
                       ) -> str:
        path = self._getPathForItemOrIndex_(leaf)
        if len(path):
            if pathOnly:
                return "".join(list(reversed(path[1:])))
            return "".join(list(reversed(path)))
        return ""

    def _getPathForItemOrIndex_(
        self: typing.Self,
        indexOrItem: typing.Union[QtCore.QModelIndex,
                            QtGui.QStandardItem]
        ) -> typing.Sequence:
        if isinstance(indexOrItem, QtCore.QModelIndex):
            item = self.itemFromIndex(indexOrItem)
        else:
            item = indexOrItem

        path = list()

        if not item:
            # print(f"{self.__class__.__name__}._getPathForItemOrIndex_: invalid item {item}")
            return path

        # print(f"{self.__class__.__name__}._getPathForItemOrIndex_: {item.data(QtCore.Qt.DisplayRole)}")
        if item.data(StandaloneEditorWidgetRole):
            # print(f"\thas standalone widget: {item.data(StandaloneEditorWidgetRole)}")
            # NOTE: 2026-02-10 12:46:07
            # skip child items with standalone editor widget
            # use their parent instead
            # NOTE: 2026-02-10 12:24:40
            # by design, only items in column 0 have data associated with this
            # role
            item = item.parent()
            if item is None:
                return path

        # NOTE: 2026-02-10 12:22:40
        # Code below only makes sense for items in column 0; however, when an`
        # item on a higher column is passed, I need access to its sibling in
        # column 0

        parentItem = item.parent()

        if parentItem:
            # print(f"{self.__class__.__name__}._getPathForItemOrIndex_: parent of {item.data(QtCore.Qt.DisplayRole)} -> {parentItem.data(QtCore.Qt.DisplayRole)}")
            if item.column() == 0:
                targetItem = item
            else:
                # get the item's sibling in column 0
                targetItem = parentItem.child(item.row(), 0)

            parentAccess = parentItem.data(ObjectDataAccessRole)
            bindingType = targetItem.data(ObjectKeyTypeRole)
            itemBinding = targetItem.data(ObjectKeyRole)
            # print(f"{self.__class__.__name__}._getPathForItemOrIndex_: bindingType for {targetItem.data(QtCore.Qt.DisplayRole)} -> {bindingType}")
            # print(f"{self.__class__.__name__}._getPathForItemOrIndex_: itemBinding -> {itemBinding}")

            if itemBinding:
                if len(parentAccess) == 1:
                    # print(f"{self.__class__.__name__}._getPathForItemOrIndex_ -> add access {parentAccess[0]}{itemBinding}")
                    path.append(f"{parentAccess[0]}{itemBinding}")

                elif len(parentAccess) == 2:
                    if bindingType is str:
                        itemBinding = f"'{itemBinding}'"
                    else:
                        itemBinding = bindingType(itemBinding) # hedging my bets...

                    path.append(f"{parentAccess[0]}{itemBinding}{parentAccess[1]}")

            path += self._getPathForItemOrIndex_(parentItem)

        elif item == self._topObjectItem_:
            # NOTE: 2026-02-10 12:26:33
            # this one is in column 0 by design
            path += [self._topObjectItem_.data(QtCore.Qt.DisplayRole)]
        #
        # else:
        #     print(f"{self.__class__.__name__}._getPathForItemOrIndex_: no more parent for {item.data(QtCore.Qt.DisplayRole)}")


        return path

    def setData(self: typing.Self, modelIndex: QtCore.QModelIndex,
                value: object, role = QtCore.Qt.EditRole) -> bool:
        if self._modelData_ is None:
            return False

        item = self.itemFromIndex(modelIndex)

        # NOTE: 2026-02-10 09:18:53
        # don't change data for this kind of item; this is done directly by the
        # table editor delegate
        #
        # Also NOTE: I use avoid editing any item in column 0 as this refers to
        # the symbol, in the parent object, to which the child object is bound;
        # changing this symbol would effectively mean changing the structure of
        # the parent object (its "class") for regular objects, whereas for
        # collections, this would mean chaning the "keys" in a mapping or the
        # "indexes" in a sequence, etc. For collections, there IS a way to alter
        # the "keys" in a dictionary or the **order** of elements in a sequence,
        # but that is too convoluted to implement in this model and is beyond
        # its scope, anyway.
        #

        objItem = item

        if item.column() == 2 and role == ObjectDataRole:
            parentItem = item.parent()
            if not parentItem:
                return False
            objItem = parentItem.child(item.row(), 0)

        # print(f"{self.__class__.__name__}.setData {value} for objItem {objItem.data(QtCore.Qt.DisplayRole)} , row {item.row()}")
        objItem.setData(QtCore.QVariant(value), ObjectDataRole)
        path = self._getPathForItemOrIndex_(objItem)
        # print(f"\taccess to objItem: {path}")

        if path[-1] == self._topObjectItem_.data(QtCore.Qt.DisplayRole):
            path[-1] = "self._modelData_"

        accexpr = "".join(reversed(path))
        setexpr = accexpr + " = value"
        exec(setexpr)

        newVal = eval(accexpr)

        objType = objItem.data(ObjectTypeRole)

        if objType is pathlib.Path:
            newVal = pathlib.Path(newVal)

        objItem.setData(newVal, ObjectDataRole)

        if item != objItem:
            item.setData(QtCore.QVariant(newVal), QtCore.Qt.DisplayRole)
            item.setData(newVal, ObjectDataRole)

        self.dataChanged.emit(modelIndex, modelIndex)
        self.sig_modelDataChanged.emit()
        return True




