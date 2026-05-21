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
import functools
from functools import singledispatchmethod
from collections import deque, UserDict, OrderedDict
from dataclasses import MISSING
import weakref
import math # noqa
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
from core.datatypes import (is_namedtuple, TypeEnum) # noqa
from core.prog import (scipywarn, timefunc, processtimefunc)
from core import taxonbridge
from core import bgbridge as bgbridge

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

# from core.workspacefunctions import (validate_varname, user_workspace)

from core.utilities import unique

from core.prog import (safewrapper, safeguiwrapper, print_styled, qVariants,
                       is_hashable)

from core.traitcontainers import (DataBag, DataBagTraitsObserver,)

from core.scipyendataclasses import isDataclass

# from gui.widgets.simpletablewidget import SimpleTableWidget
# from gui.widgets.tableeditorwidget import (TableEditorWidget,
#                                            TabularDataModel,)
# from gui.pictgui import WorkerThread
# from gui.widgets.small_widgets import QuantitySpinBox, ComplexSpinBox
# from gui.delegates import PythonItemDelegate
# from gui.workspacegui import GuiMessages, WorkspaceGuiMixin
from gui.itemmodels.roles import *

from core.datatypes import PODS

NOTMEMOIZED = (
    tuple,
    type(None),
    type(MISSING),
    type(pd.NA),
    type,
    np.ndarray,
    types.ModuleType,
    pkgutil.ModuleInfo,
    typing.Callable,
    types.FunctionType,
    np.ufunc,
    functools.partial
)

# PODS = (
#     bool,
#     int,
#     float,
#     complex,
#     bytes,
#     bytearray,
#     str,
#     np.integer,
#     np.floating,
#     np.complexfloating,
# )

# NOTE 2026-02-05 17:48:51 TODO/FIXME
# look at:
# QItemEditorFactory
# QItemEditorCreatorBase
# QStandardItemEditorCreator
# use QTreeView with QStyledItemDelegate subclass and QStandardItem

class DataTreeModel(QtGui.QStandardItemModel):
    r"""
    Hierarchical item model for Python objects.

    Currently only supports a subset of Python object types.
"""
    # TODO: 2026-02-12 23:36:43 FIXME
    # Harmonize with iolib.jsonio and iolib.h5io

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
    def _check_public_member_(x: object, y: typing.Optional[object] = None):
        return (not isinstance(x[0], str)
                or not x[0].startswith("_"))

    # @staticmethod
    # def _check_private_member_2_(x: object, y: object):
    #     return self._check_public_member_(x)

    def __init__(self: typing.Self, data: typing.Optional[typing.Any] = None,
                 dataName: str = None,
                 parent: typing.Optional[QtCore.QObject] = None,
                 **kwargs):
        super(DataTreeModel, self).__init__(0, 3, parent=parent)
        self._modelData_: typing.Optional[object] = None
        self._dataTypeStr_: str = ""
        self._visited_: dict = dict()
        # self._visited_: set = set()
        self._rootTitle_ = "/"
        self._hasDynamicPrivate_: bool = False
        self._privateData_: dict = None
        self._predicate_: types.FunctionType = None
        self._showPrivate_: bool = False
        self._hideRoot_: bool = False
        self._introspect_: bool = True
        self._topObjectItem_: typing.Optional[QtGui.QStandardItem] = None
        self._readOnly: bool = False

        self._supportedDataTypes_ = kwargs.pop("supportedTypes", tuple())
        if not isinstance(self._supportedDataTypes_, tuple) or not all(
            isinstance(v, type) for v in self._supportedDataTypes_
        ):
            self._supportedDataTypes_ = tuple()

        self._readOnly_ = kwargs.pop("readOnly", True)

        self._showMethods_ = kwargs.pop("showMethods", False)

        self._inlineTables_: bool = kwargs.pop("inlineTables", False)
        self._showValueAttributesOnly_ = kwargs.pop("valuesOnly", True)

        self.setHorizontalHeaderLabels(["Object", "Type", "Value / Information"])

    @property
    def topObjectItem(self: typing.Self) -> QtGui.QStandardItem | None:
        return self._topObjectItem_

    @property
    def inlineTables(self) -> bool:
        return self._inlineTables_

    @inlineTables.setter
    def inlineTables(self, val: bool):
        if val != self._inlineTables_:
            self._inlineTables_ = val is True
            obj = self._modelData_
            rootTitle = self._rootTitle_
            predicate = self._predicate_
            showPrivate = self._showPrivate_
            hideRoot = self._hideRoot_
            readOnly = self._readOnly_
            self.setModelData(obj, rootTitle, predicate, showPrivate,
                              hideRoot, readOnly)

    @property
    def readOnly(self: typing.Self) -> bool:
        return self._readOnly_

    @readOnly.setter
    def readOnly(self: typing.Self, val: bool):
        self._readOnly_ = val is True

    def _makeObjectRow_(self: typing.Self, obj: object, /,
                       objDict: dict, objKey: object,
                       objKeyType: type, visited:tuple=tuple()) -> tuple:

        typeName = objDict["objType"].__name__

        info = objDict["objInfo"]
        if isinstance(info, bool):
            info = f"{info}"

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
        item0.setData(objDict["objType"], ObjectTypeRole) # noqa
        item0.setData(objDict["objType"].__name__, QtCore.Qt.ToolTipRole)

        # NOTE: 2026-02-09 21:47:10
        # used to construct the acess path to the object for this item
        item0.setData(QtCore.QVariant(memberAccess), ObjectDataAccessRole) # noqa

        # NOTE: 2026-02-09 21:47:38
        # reference to the actual Python object
        item0.setData(QtCore.QVariant(obj), ObjectDataRole) # noqa

        # NOTE: 2026-02-09 21:47:57
        # reference to the object's binding in its parent: e.g. symbol of an
        # attribute or field, index (for sequences), key (for mappings)
        item0.setData(QtCore.QVariant(objKey), ObjectKeyRole) # noqa

        # NOTE: 2026-02-09 21:49:05
        # object "bindings" are are int for sequences, any hashable object type
        # (including str and int) for mappings, str for attributes & fields.
        #
        # iterators are NOT supported (they're used to yield elements of a
        # collection dynamically, anyway, and a reason for using them is a
        # "lazy" evaluation of the collection's contents - in itself for a good
        # reason) ; therefore, I apply the same philosophy here
        #
        item0.setData(QtCore.QVariant(objKeyType), ObjectKeyTypeRole) # noqa

        editExternally = objDict["objDataAsChild"] and QtCore.QVariant(not self._inlineTables_)
        item0.setData(editExternally, ObjectDataEditExternallyRole)

        if visited:
            typeName = visited[-1].__name__

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
        if visited:
            targetPath = visited[2]
            item2 = QtGui.QStandardItem(f"<reference to {targetPath}>")
        else:
            item2 = QtGui.QStandardItem(f"{info}")
            if isinstance(obj, pathlib.Path):
                item2.setData(obj, QtCore.Qt.EditRole)
            else:
                item2.setData(info, QtCore.Qt.EditRole)

            choices = objDict.get("choices", dict())
            item2.setData(choices, DataChoicesRole) # noqa


        flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable
        readOnlyFlags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsEnabled

        readOnly = objDict.get("readOnly", False)
        readOnlyChildren = objDict.get("readOnlychildren", False)

        palette = QtWidgets.QApplication.palette()
        font = QtWidgets.QApplication.font()
        brush = palette.brush(QtGui.QPalette.Active, QtGui.QPalette.Text)
        readOnlyFont = QtGui.QFont(font)
        readOnlyFont.setItalic(True)
        readOnlyBrush = palette.brush(QtGui.QPalette.Inactive, QtGui.QPalette.Text)

        for k, item in enumerate((item0, item1, item2)):
            item.setData(readOnly, ReadOnlyRole)
            item.setData(readOnlyChildren, ReadOnlyChildrenRole)
            if k == 2:
                if readOnly or (
                                    (
                                        objDict.get("indirect", False) is True
                                        or objDict.get("objDataAsChild", False) is True
                                    )
                                    and len(objDict.get("choices", dict())) == 0
                                ):
                    item.setData(readOnlyBrush, QtCore.Qt.ForegroundRole)
                    item.setData(readOnlyFont, QtCore.Qt.FontRole)
                    item.setFlags(readOnlyFlags)
                else:
                    item.setData(brush, QtCore.Qt.ForegroundRole)
                    item.setData(font, QtCore.Qt.FontRole)
                    item.setFlags(flags)
            else:
                # prohibit editing in columns 0 and 1
                item.setData(brush, QtCore.Qt.ForegroundRole)
                item.setData(font, QtCore.Qt.FontRole)
                item.setFlags(readOnlyFlags)

        return (item0, item1, item2)

    # @timefunc
    def setModelData(self, obj: object, rootTitle: str = "",
        predicate: typing.Optional[types.FunctionType] = None,
        showPrivate: bool = False,
        # dataTypeStr: typing.Optional[str] = None,
        hideRoot: bool = False,
        readOnly: bool = False,
        # introspect: bool = False
    ):
        # print(f"{self.__class__.__name__}.setModelData(obj: {type(obj).__name__})")
        self._visited_.clear()
        self._predicate_ = predicate
        self._showPrivate_ = showPrivate is True
        self._hideRoot_ = hideRoot is True
        self._readOnly_ = readOnly is True
        # self._introspect_ = introspect is True

        self._rootTitle_ = rootTitle if (
            isinstance(rootTitle, str)
            and len(rootTitle.strip())
            ) else "/"

        self._modelData_ = obj

        self.setHorizontalHeaderLabels(["Object", "Type", "Information or Value"])

        pData, objDict = self._parseObject_(obj, dict(),
                                            self._showPrivate_)

        self._privateData_ = pData

        self._buildTree_(self._privateData_, objDict, self._rootTitle_)

    def _buildTree_(self: typing.Self,
                    obj: object,
                    objDict: dict,
                    name: str = ""): #,
                    # path: tuple = tuple()):

        # 1. get the top object symbol, type and some information, as items to
        # go as the first (and only) top-level row in the model

        # print(f"{self.__class__.__name__}._buildTree_(obj: {type(obj).__name__})")
        self._topObjectItem_ = self._buildBranch_(self._privateData_,
                                                    objDict, name, str,
                                                    self.invisibleRootItem(),
                                                    0
                                                    )
        if self.readOnly:
            self._topObjectItem_.setData(self.readOnly, ReadOnlyRole) # noqa

    @singledispatchmethod
    def _buildBranch_(self: typing.Self, obj: object, objDict: dict,
                      objKey: object, objKeyType: type,
                      parentItem: QtGui.QStandardItem,
                      row: int) -> QtGui.QStandardItem:

        visited = tuple()
        objId = objDict["objId"]

        if not issubclass(
            type(obj), NOTMEMOIZED + PODS
        ):
            if objId in self._visited_ and objDict["objType"] == self._visited_[objId][-1]:
                visited = self._visited_[objId]

        rowItems = self._makeObjectRow_(obj, objDict, objKey, objKeyType, visited)

        objItem = rowItems[0]

        if objDict["objDataAsChild"] and self._inlineTables_:
            dataItem = QtGui.QStandardItem("")
            dataItem.setData(QtCore.QVariant(True), StandaloneEditorWidgetRole) # noqa
            # if not self._inlineTables_:
            #     dataItem.setData(QtCore.QVariant("Double-click to edit..."), QtCore.Qt.DisplayRole) # noqa
            #     dataItem.setData(QtCore.QVariant(obj), ObjectDataRole) # noqa
            objItem.insertRow(0, [dataItem])
        else:
            dataItem = rowItems[-1]
            if len(visited) == 0:
                dataItem.setData(QtCore.QVariant(obj), ObjectDataRole) # noqa

        accessType = objDict.get("accessType", None)

        objItem.setData(QtCore.QVariant(accessType), ObjectDataAccessTypeRole) # noqa

        if not parentItem:
            parentItem = self.invisibleRootItem()

        if parentItem:
            parentItem.insertRow(row, rowItems)
            if (not isinstance(obj, NOTMEMOIZED)
                and not issubclass(
                    type(obj), NOTMEMOIZED + PODS
                )
                and objId not in self._visited_):
                itemPath = f"{self._rootTitle_}{self.getPathForLeaf(objItem)}"
                self._memoize_(obj, itemPath, objDict)
                # self._memoize_(obj, itemPath, objDict["objType"], objId)

        return objItem

    @_buildBranch_.register(dict)
    @_buildBranch_.register(UserDict)
    @_buildBranch_.register(types.MappingProxyType)
    def __buildBranch_(self: typing.Self, obj: typing.Union[dict, types.MappingProxyType, UserDict],
          objDict: dict, objKey: object, objKeyType: type,
          parentItem: QtGui.QStandardItem, row: int) -> QtGui.QStandardItem:

        visited = tuple()

        objId = objDict["objId"]

        if not issubclass(
            type(obj), NOTMEMOIZED + PODS
        ):
            if objId in self._visited_ and objDict["objType"] == self._visited_[objId][-1]:
                visited = self._visited_[objId]

        rowItems = self._makeObjectRow_(obj, objDict, objKey, objKeyType, visited)

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

            pItem.setData(QtCore.QVariant(accessType), ObjectDataAccessTypeRole) # noqa

            if parentItem:
                parentItem.insertRow(row, rowItems)

                if not issubclass(
                    type(obj), NOTMEMOIZED + PODS
                ):
                    if objId not in self._visited_:
                        itemPath = f"{self._rootTitle_}{self.getPathForLeaf(pItem)}"
                        self._memoize_(obj, itemPath, objDict)

        if len(visited):
            return pItem

        # print(f"{self.__class__.__name__}._buildBranch_")
        for key, value in obj.items():
            # print(f"\tkey  {key} ->  {type(value)}")
            if isinstance(key, str):
                keyName = key
            else:
                keyName = f"{key}"

            # TODO/FIXME: 2026-03-28 17:13:47
            # try and read the object's options for this member ("value")
            # and create choices accordingly
            pValue, valDict = self._parseObject_(value, dict(), self._showPrivate_)

            if objDict["indirect"] and not self._showMethods_:
                # NOTE: 2026-05-05 22:33:51
                # DO show functions & method values in a dict-like object, where
                # "indirect" is False
                if valDict["objType"] in (types.FunctionType,
                                          types.BuiltinFunctionType,
                                          types.MethodType,
                                          types.BuiltinMethodType):
                    continue

            if self._showValueAttributesOnly_:
                if type in inspect.getmro(valDict["objType"]):
                    continue

            if objDict.get("readOnlyChildren", False) is True:
                valDict["readOnly"] = True

            self._buildBranch_(pValue, valDict, keyName, type(key), pItem, k)

            k += 1


        return pItem

    @property
    def showMethods(self) -> bool:
        return self._showMethods_

    @showMethods.setter
    def showMethods(self, val:bool):
        self._showMethods_ = val is True

    @property
    def showPrivateMembers(self) ->bool:
        return self._showPrivate_

    @showPrivateMembers.setter
    def showPrivateMembers(self, val:bool):
        self._showPrivate_ = val is True

    @property
    def showIntrospection(self) -> bool:
        return self._introspect_

    @showIntrospection.setter
    def showIntrospection(self, val: bool):
        self._introspect_ = val is True

    @property
    def showValuesOnly(self) -> bool:
        return self._showValueAttributesOnly_

    @showValuesOnly.setter
    def showValuesOnly(self, val:bool):
        self._showValueAttributesOnly_ = val is True

    def introspectable(self: typing.Self, obj: object) -> bool:
        mro = inspect.getmro(type(obj))
        return (all(t not in self._supportedDataTypes_ for t in mro)
                         and not inspect.isroutine(obj)
                         and not isinstance(obj, (types.ModuleType,
                                             pkgutil.ModuleInfo))
                         and obj is not None)

    def _memoize_(self, obj, path, objDict):
        objId = objDict["objId"]
        realtype = objDict["objType"]
        if objId not in self._visited_:
            idx = len(self._visited_)
            self._visited_[objId] = (idx, type(obj), path, realtype)

    @singledispatchmethod
    def _parseObject_(self: typing.Self, obj: object,
                      choices: dict = dict(),
                      includePrivateMembers: bool = False,
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

            "readOnly" ↦ flag indicating if the represented object can be edited
                in the datatreeview. Some object types are immutable by design
                (e.g., bytes, bytearray, tuple, frozenset) and therefore their
                contents cannot be edited.



            "isLeaf" ↦ flag to determine if the object represented in the item in
                column 0 is a "leaf", or has children



        """
        # TODO 2026-03-28 16:32:58
        # configuration file to determine if instances of some user-defined types
        # are also editable or not -> use it to deterine the readOnly flag, above
        indirect: bool = False
        tip: str = type(obj).__name__
        objDataAsChild: bool = False
        objType = type(obj)
        objId = id(obj)
        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()
        readOnly = False
        readOnlyChildren = False

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
                            self._check_public_member_,
                            pData.items()
                        )
                    )
                )
            else:
                readOnlyChildren = True

            n = len(pData)

            info = f"{n} {strutils.pluralize('member', n)}"
            tip = f"{type(obj).__name__} (dataclass)"
            indirect = True
            objDataAsChild = False
            memberAccess = (".",)
            accessType = "attribute"
            readOnly = False

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

        elif HAS_MESHIO and isinstance(obj, meshio.Mesh):
            pData = obj
            indirect=False,
            s = " × ".join(list(map(lambda x: f"{x}", obj.points.shape)))
            info = f"{obj.points.size} points ({s})"
            tip = type(obj).__name__
            objDataAsChild = False
            memberAccess = tuple()
            accessType = None
            readOnly = True
            readOnlyChildren = True

        elif self._introspect_ and self.introspectable(obj) :
            # print(f"{self.__class__.__name__}._parseObject_ introspecting")
            pData = datatypes.inspect_members(obj, self._predicate_)
            indirect = True
            if not includePrivateMembers:
                pData = dict(
                    list(
                        filter(
                            self._check_public_member_,
                            pData.items()
                        )
                    )
                )

            # indirect = True
            objDataAsChild = False

            n = len(pData)
            info = f"{n} {strutils.pluralize('member', n)}"
            # choices = dict()
            memberAccess = (".", )
            accessType = "attribute"
            readOnly = True
            readOnlyChildren = True

        else:
            pData = obj
            indirect = False
            info = f"{obj}"
            tip = f"{obj}"
            objDataAsChild = False
            memberAccess = tuple()
            accessType = None
            # choices = dict()
            # scipywarn(f"TODO: Support for objects of type {type(obj).__name__} awaits implementation. FIXME")
            # raise NotImplementedError(
            # f"Objects of type {type(obj).__name__} are not supported"
            # )

        return pData, {
            "indirect": indirect,
            "objDataAsChild": objDataAsChild,
            "objInfo": info,
            "memberAccess": memberAccess,
            "accessType": accessType,
            "objTip": tip,
            "objType": objType,
            "choices": choices,
            "readOnly": readOnly,
            "readOnlyChildren": readOnlyChildren,
            "objId": objId
            }

    @_parseObject_.register(type(None))
    @_parseObject_.register(type(MISSING))
    @_parseObject_.register(type(pd.NA))
    def __parseObject_(self: typing.Self, obj: typing.Union[type(None), type(MISSING), type(pd.NA)],
          choices: dict = dict(),
          _:bool = False) -> tuple:
        objType = type(obj)
        objId = id(obj)
        pData = obj
        indirect = False
        info = f"{obj}"
        tip = f"{obj}"
        objDataAsChild = False
        memberAccess = tuple()
        accessType = None
        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()

        # TODO/FIXME: 2026-03-28 16:57:15
        # mechanism to see if a new object of another type is acceptable here, in which case call a UI c'tor'
        readOnly = True
        readOnlyChildren = True

        return pData, {
            "indirect": indirect,
            "objDataAsChild": objDataAsChild,
            "objInfo": info,
            "memberAccess": memberAccess,
            "accessType": None,
            "objTip": tip,
            "objType": objType,
            "choices": choices,
            "readOnly": readOnly,
            "readOnlyChildren": readOnlyChildren,
            "objId": objId
            }

    @_parseObject_.register(datetime.datetime)
    @_parseObject_.register(datetime.date)
    @_parseObject_.register(datetime.time)
    @_parseObject_.register(datetime.timedelta)
    @_parseObject_.register(datetime.timezone)
    def __parseObject_(self: typing.Self, obj: typing.Union[datetime.datetime,
                                               datetime.date,
                                               datetime.time,
                                               datetime.timedelta,
                                               datetime.timezone],
          choices: dict = dict(),
          _:bool = False) -> tuple:

        objType = type(obj)
        objId = id(obj)
        pData = obj
        info = f"{obj}"
        tip = f"{obj}"
        objDataAsChild = False
        memberAccess = tuple()
        accessType = None
        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()
        readOnly = False

        return pData, {
            "indirect": False,
            "objDataAsChild": objDataAsChild,
            "objInfo": info,
            "objType": type(obj).__name__,
            "memberAccess": memberAccess,
            "accessType": accessType,
            "objTip": tip,
            "objType": objType,
            "choices": dict(),
            "readOnly": readOnly,
            "objId": objId
            }

    @_parseObject_.register(types.FunctionType)
    @_parseObject_.register(types.BuiltinFunctionType)
    @_parseObject_.register(types.MethodType)
    @_parseObject_.register(types.BuiltinMethodType)
    def __parseObject_(self: typing.Self, obj: typing.Union[types.FunctionType,
                                               types.BuiltinFunctionType,
                                               types.MethodType,
                                               types.BuiltinMethodType],
          choices: dict = dict(),
          _:bool = False) -> tuple:
        # print(f"{self.__class__.__name__}._parseObject_(obj: {type(obj)})")
        objType = type(obj)
        objId = id(obj)
        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()
        tip = f"{obj}"
        word = "Function" if isinstance(obj, (types.FunctionType, types.BuiltinFunctionType)) else "Method"
        try:
            # NOTE: 2026-05-01 09:24:50
            # because signature of builtin functions e.g. on PyQt side) cannot be inspected
            signature = f"{inspect.signature(obj)}"
        except:
            signature = ""
        info = f"{word} {obj.__qualname__}{signature} from module {obj.__module__}"

        return obj, {
            "indirect": False,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": tuple(),
            "accessType": None,
            "choices": choices,
            "readOnly": False, # TODO/FIXME
            "objId": objId
            }

    @_parseObject_.register(type)
    @_parseObject_.register(enum.EnumType)
    @_parseObject_.register(enum.Enum)
    @_parseObject_.register(enum.IntEnum)
    @_parseObject_.register(enum.Flag)
    @_parseObject_.register(TypeEnum)
    def __parseObject_(self: typing.Self, obj: typing.Union[type, enum.EnumType, enum.Enum,
                                               enum.Flag, TypeEnum],
          choices: dict = dict(),
          includePrivateMembers: bool = False) -> tuple:
        readOnly = True
        readOnlyChildren = True
        objType = type(obj)
        objId = id(obj)
        info = obj
        tip = str(obj)
        pData = obj
        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()
        memberAccess = tuple()
        accessType = None

        if isinstance(obj, (
            enum.EnumType, TypeEnum, enum.Enum, enum.IntEnum, enum.Flag)):
            memberAccess = (".", )
            accessType = "attribute"
            readOnly = False
            readOnlyChildren = False
            if isinstance(obj, (enum.Enum, enum.IntEnum, TypeEnum, enum.Flag)):
                info = obj.name
            if hasattr(obj, "__members__"):
                choices = dict(obj.__members__)
            elif hasattr(type(obj), "__members__"):
                choices = dict(type(obj).__members__)
            else:
                try:
                    # NOTE: 2026-02-13 17:45:45
                    # this only works for TypeEnum
                    #
                    choices = dict(zip(obj.names(), obj.values()))
                except:
                    scipywarn(f"Cannot access enumeration values for {type(obj).__name__}")
                    choices = dict()
                # readOnly = True

        return obj, {
            "indirect": False,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": memberAccess,
            "accessType": accessType,
            "choices": choices,
            "readOnly": readOnly,
            "readOnlyChildren": readOnlyChildren,
            "objId": objId
            }

    @_parseObject_.register(pkgutil.ModuleInfo)
    def __parseObject_(self: typing.Self, obj: pkgutil.ModuleInfo,
                choices: dict = dict(),
                includePrivateMembers: bool = False) -> tuple:
        objType = type(obj)
        objId = id(obj)
        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()
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
            "choices": choices,
            "readOnly": True,
            "readOnlyChildren": True,
            "objId": objId
            }

    @_parseObject_.register(bgbridge.Structure)
    def __parseObject_(self: typing.Self, obj: bgbridge.Structure,
                choices: dict = dict(),
                includePrivateMembers: bool = False) -> tuple:
        objType = type(obj)
        objId = id(obj)
        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()
        ndx = [
            i[1]
            for i in sorted(
                (str(k[0]), k[1])
                for k in zip(obj.keys(), range(len(obj)))
            )
        ]

        items = [i for i in obj.items()]
        pData = dict([items[k] for k in ndx])
        indirect = True
        info = f"{obj}"
        if not includePrivateMembers:
            pData = dict(
                list(
                    filter(
                        self._check_public_member_,
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
            "choices": choices,
            "readOnly": True,
            "readOnlyChildren": True,
            "objId": objId
            }

    @_parseObject_.register(taxonbridge.Taxon)
    def __parseObject_(self: typing.Self, obj: taxonbridge.Taxon,
            choices: dict  = dict(),
            includePrivateMembers: bool = False) -> tuple:
        objType = type(obj)
        objId = id(obj)
        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()
        pData = obj.__dict__
        indirect = True
        info = f"{obj}"
        if not includePrivateMembers:
            pData = dict(
                list(
                    filter(
                        self._check_public_member_,
                        pData.items()
                    )
                    )
                )

        pData["common_name"] = obj.common_name
        pData["rank"] = obj.rank
        pData["scientific_name"] = obj.scientific_name
        pData["url"] = obj.url
        pData["wikidata_id"] = obj.wikidata_id
        pData["wikidata_url"] = obj.wikidata_url

        tip = type(obj).__name__
        return pData, {
            "indirect": indirect,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".",),
            "accessType": "attribute",
            "choices": choices,
            "readOnly": True,
            "readOnlyChildren": True,
            "objId": objId
            }

    @_parseObject_.register(dict)
    @_parseObject_.register(types.MappingProxyType)
    @_parseObject_.register(UserDict)
    @_parseObject_.register(OrderedDict)
    def __parseObject_(self: typing.Self, obj: typing.Union[dict, types.MappingProxyType,
                                               UserDict],
            choices: dict = dict(),
            includePrivateMembers: bool = False) -> tuple:
        # CAUTION: 2026-02-13 21:54:18
        # this might be the private data, NOT the original model data!

        objId = id(obj)
        if obj is self._privateData_:
            objType = type(self._modelData_)
        else:
            objType = type(obj)

        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()

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
                        self._check_public_member_,
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
            "choices": choices,
            "readOnly": True,
            "readOnlyChildren": False,
            "objId": objId
            }

    @_parseObject_.register(list)
    @_parseObject_.register(tuple)
    @_parseObject_.register(deque)
    @_parseObject_.register(NeoObjectList)
    @_parseObject_.register(set)
    @_parseObject_.register(frozenset)
    def __parseObject_(self: typing.Self, obj: typing.Union[list, tuple, deque, set,
                                               NeoObjectList, frozenset],
            choices: dict = dict(),
            includePrivateMembers: bool = False) -> tuple:
        objId = id(obj)
        objType = type(obj)
        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()
        tip = objType.__name__
        readOnly = True
        readOnlyChildren = False

        if isinstance(obj, (tuple, frozenset)):
            readOnlyChildren = True

        if is_namedtuple(obj):
            pData = obj._asDict() if hasattr(obj, "_asDict") else obj._asdict()
            tip += "(namedtuple)"
            memberAccess = (".",)
            accessType = "attribute"
            readOnlyChildren = True

        elif isinstance(obj, os.stat_result):
            pData = dict(filter(lambda t: any(t[0].startswith(s) for s in ("n_", "st_")), inspect.getmembers(obj)))
            tip += "(stat result)"
            memberAccess = (".",)
            accessType = "attribute"
            readOnlyChildren = True

        else:
            pData = dict(enumerate(obj))
            memberAccess = ("[","]")
            accessType = "index"

        if not includePrivateMembers:
            pData = dict(
            list(
                    filter(
                        self._check_public_member_,
                        pData.items()
                    )
                )
            )
        # else:
        #     readOnly = True

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
            "choices": choices,
            "readOnly": readOnly,
            "readOnlyChildren": readOnlyChildren,
            "objId": objId
            }

    @_parseObject_.register(str)
    @_parseObject_.register(bytes)
    @_parseObject_.register(bytearray)
    def __parseObject_(self: typing.Self, obj: typing.Union[str, bytes, bytearray],
          choices: dict = dict(),
          _: bool = True) -> tuple:
        objId = id(obj)
        objType = type(obj)
        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()
        readOnly = False
        readOnlyChildren = False
        objDataAsChild = False
        tip = objType.__name__
        n = len(obj)
        if n > 100:
            info = (
                obj[:97] if isinstance(obj, str) else obj.decode()[:97]
            )
            info += "..."
            objDataAsChild = True
        else:
            info = obj if isinstance(obj, str) else obj.decode()

        if isinstance(obj, (bytes, bytearray)):
            readOnly = True
            readOnlyChildren = True

        return  obj, {
            "indirect": False,
            "objDataAsChild": objDataAsChild,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": tuple(),
            "accessType": None,
            "choices": choices,
            "readOnly": readOnly,
            "readOnlyChildren": readOnlyChildren,
            "objId": objId
            }

    @_parseObject_.register(pathlib.Path)
    def __parseObject_(self: typing.Self, obj: pathlib.Path,
          choices: dict = dict(),
          _: bool = True) -> tuple:
        objId = id(obj)
        objType = type(obj)
        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()
        # info = f"{obj}"
        info = obj.as_posix()
        tip = objType.__name__
        # pData = obj.as_posix()
        pData = obj
        # indirect = True
        indirect = False
        return  pData, {
            "indirect": indirect,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": tuple(),
            "accessType": None,
            "choices": choices,
            "readOnly": False,
            "objId": objId
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
    def __parseObject_(self: typing.Self, obj: typing.Union[bool, int, float, complex,
                                               fractions.Fraction,
                                               decimal.Decimal,
                                               numbers.Number,
                                               np.integer, np.floating,
                                               np.complexfloating],
          choices: dict = dict(),
          _: bool=True) -> tuple:
        objId = id(obj)
        objType = type(obj)
        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()
        tip = objType.__name__
        return obj, {
            "indirect": False, "objDataAsChild": False,
            "objInfo": obj,
            "objType": objType,
            "objTip": tip,
            "memberAccess": tuple(),
            "accessType": None,
            "choices": choices,
            "readOnly": False,
            "objId": objId
            }

    @_parseObject_.register(types.SimpleNamespace)
    def __parseObject_(self: typing.Self, obj: types.SimpleNamespace,
                choices: dict = dict(),
                includePrivateMembers: bool = False) -> tuple:
        objId = id(obj)
        objType = type(obj)
        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()
        pData = obj.__dict__
        if not includePrivateMembers:
            pData = dict(
            list(
                    filter(
                        self._check_public_member_,
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
            "choices": choices,
            "readOnly": True,
            "readOnlyChildren": False,
            "objId": objId
            }

    @_parseObject_.register(types.ModuleType)
    def __parseObject_(self: typing.Self, obj: types.ModuleType,
          choices: dict = dict(),
          includePrivateMembers: bool = False) -> tuple:
        objId = id(obj)
        objType = type(obj)
        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()
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
                                    self._check_public_member_,
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
            "choices": choices,
            "readOnly": True,
            "readOnlyChildren": True,
            "objId": objId
            }

    @_parseObject_.register(vigra.filters.Kernel1D)
    @_parseObject_.register(vigra.filters.Kernel2D)
    def __parseObject_(self: typing.Self, obj: typing.Union[vigra.filters.Kernel1D,
                                               vigra.filters.Kernel2D],
           choices: dict = dict(),
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

        objId = id(obj)
        objType = type(obj)
        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()
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
            "choices": choices,
            "readOnly": True, # pending a new widget for this
            "objId": objId
            }

    @_parseObject_.register(pd.DataFrame)
    @_parseObject_.register(pd.Series)
    @_parseObject_.register(pd.Index)
    def __parseObject_(self: typing.Self, obj: typing.Union[pd.DataFrame, pd.Series,
                                               pd.Index],
          choices: dict = dict(),
          _: bool = True) -> tuple:
        objId = id(obj)
        objType = type(obj)

        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()

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
            "choices": choices,
            "readOnly": True,
            "objId": objId
            }


    @_parseObject_.register(Interval)
    def __parseObject_(self: typing.Self, obj: Interval,
          choices: dict = dict(),
          _: bool = True) -> tuple:
        pData = {
                    "t0": obj.t0,
                    "t1": obj.t1,
                    "durations": obj.durations,
                    "extent": obj.extent,
                    "labels": obj.labels,
                    "annotations": obj.annotations,
                    "description": obj.description,
                }
        objId = id(obj)
        objType = type(obj)
        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()
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
            "choices": choices,
            "readOnly": False,
            "objId": objId
            }

    @_parseObject_.register(neo.Epoch)
    @_parseObject_.register(DataZone)
    def __parseObject_(self: typing.Self, obj: typing.Union[neo.Epoch, DataZone],
          choices: dict = dict(),
          _: bool = True) -> tuple:
        objId = id(obj)
        objType = type(obj)
        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()

        pData = {
                    "times": obj.times,
                    "durations": obj.durations,
                    "labels": obj.labels,
                    "annotations": obj.annotations,
                    "description": obj.description,
                }

        tip = type(obj).__name__
        n = obj.size
        klass = "Zone" if isinstance(obj, DataZone) else "Epoch"
        desc = strutils.pluralize('subinterval', n)
        info = f"{klass} '{obj.name}' with {n} {desc}"

        return pData, {
            "indirect": True,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": choices,
            "readOnly": False,
            "objId": objId
            }

    @_parseObject_.register(neo.Event)
    @_parseObject_.register(DataMark)
    @_parseObject_.register(TriggerEvent)
    def __parseObject_(self: typing.Self, obj: typing.Union[neo.Event, DataMark,
                                               TriggerEvent],
          choices: dict = dict(),
          _: bool = True) -> tuple:
        objId = id(obj)
        objType = type(obj)
        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()

        pData = {"times": obj.times, "labels": obj.labels}

        if isinstance(obj, (DataMark, TriggerEvent)):
            pData.update({"type": obj.type, "relative": obj.relative})

        pData.update({"annotations": obj.annotations, "description": obj.description})

        tip = type(obj).__name__

        klass = "TriggerEvent" if isinstance(obj, TriggerEvent) else "Mark" if isinstance(obj, DataMark) else tip

        n = obj.size
        desc = strutils.pluralize('subinterval', n)
        info = f"{klass} '{obj.name}' with {n} {desc}"

        return pData, {
            "indirect": True,
            "objDataAsChild": False,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": choices,
            "readOnly": False,
            "objId": objId
            }

    @_parseObject_.register(pq.Quantity)
    def __parseObject_(self: typing.Self, obj: pq.Quantity,
          choices: dict = dict(),
          _: bool=True) -> tuple:
        # print(f"{self.__class__.__name__}._parseObject_({type(obj).__name__})")
        objId = id(obj)
        objType = type(obj)
        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()

        readOnly = False
        tip = f"{scq.unitFamilyName(obj.units)} quantity"
        if isinstance(obj, pq.UnitQuantity):
            info = f"{obj} {scq.unitFamilyName(obj)}"
            objDataAsChild = False
        else:
            if obj.size <= 1:
                info = f"{obj}"
                objDataAsChild = False
            else:
                n = obj.size
                # s = " × ".join(list(map(lambda x: f"{x}", obj.shape))) if len(obj.shape) > 1 else f"{obj.shape}"
                info = f"Quantity array ({obj.units.dimensionality}) with {n} {strutils.pluralize('sample', n)}, shape: {obj.shape},  dtype {obj.dtype}."
                objDataAsChild = True
                readOnly = False

        objDict = {
            "indirect": False,
            "objDataAsChild": objDataAsChild,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": (".", ),
            "accessType": "attribute",
            "choices": choices,
            "readOnly": readOnly,
            "objId": objId
            }

        # print(f"\t-> {objDict}")

        return obj, objDict

    @_parseObject_.register(vigra.VigraArray)
    def __parseObject_(self: typing.Self, obj:vigra.VigraArray,
          choices: dict = dict(),
          _: bool = True) -> tuple:
        objId = id(obj)
        objType = type(obj)
        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()

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
            "choices": choices,
            "readOnly": True,
            "objId": objId
            }


    @_parseObject_.register(np.ndarray)
    def __parseObject_(self: typing.Self, obj: np.ndarray,
          choices: dict = dict(),
          _: bool = False) -> tuple:
        objId = id(obj)
        objType = type(obj)
        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()

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
            info = f"Array with {n} {samples}, shape {s}, dtype {obj.dtype}."

        return obj, {
            "indirect": False,
            "objDataAsChild": objDataAsChild,
            "objInfo": info,
            "objType": objType,
            "objTip": tip,
            "memberAccess": tuple(),
            "accessType": None,
            "choices": dict(),
            "readOnly": True,
            "objId": objId
            }

    @_parseObject_.register(vigra.AxisInfo)
    def __parseObject_(self: typing.Self, obj: vigra.AxisInfo,
          choices: dict = dict(),
          _: bool = False) -> tuple:
        objId = id(obj)
        objType = type(obj)
        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()

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
            "choices": choices,
            "readOnly": False,
            "objId": objId
            }

    @_parseObject_.register(vigra.AxisType)
    def __parseObject_(self: typing.Self, obj: vigra.AxisType,
          choices: dict = dict(),
          _: bool = False) -> tuple:
        # NOTE: 2026-02-08 22:54:09 TODO
        # Don't really want to edit this via GUI, so no member access for now
        objId = id(obj)
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
            "readOnly": False,
            "objId": objId
            }

    @_parseObject_.register(AxesCalibration)
    def __parseObject_(self: typing.Self, obj: AxesCalibration,
          choices: dict = dict(),
          _:bool=True) -> tuple:
        objId = id(obj)
        objType = type(obj)
        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()

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
            "choices": choices,
            "readOnly": False, # allow editin he content, unless specified otherwise by the caller
            "objId": objId
            }

    @_parseObject_.register(AxisCalibrationData)
    def __parseObject_(self: typing.Self, obj: AxisCalibrationData,
          choices: dict = dict(),
          _: bool = False) -> tuple:
        objId = id(obj)
        objType = type(obj)
        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()

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
            "choices": False,
            "readOnly": True,
            "objId": objId
            }

    @_parseObject_.register(ChannelCalibrationData)
    def __parseObject_(self: typing.Self, obj: ChannelCalibrationData,
          choices: dict = dict(),
          _: bool = False) -> tuple:
        objId =  id(obj)
        objType = type(obj)
        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()

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
            "choices": choces,
            "readOnly": False,
            "objId": objId
            }

    @_parseObject_.register(PVObject)
    def __parseObject_(self: typing.Self, obj: PVObject,
          choices: dict = dict(),
          _: bool = False) -> tuple:
        objId = id(obj)
        objType = type(obj)
        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()

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
            "choices": choices,
            "readOnly": False,
            "objId": objId
            }

    @_parseObject_.register(scipy.optimize.Bounds)
    def __parseObject_(self: typing.Self, obj: scipy.optimize.Bounds,
          choices: dict = dict(),
          _:bool = True) -> tuple:
        objId = id(obj)
        objType = type(obj)
        if not isinstance(choices, dict):
            if len(choices)> 0 and not all(isinstance(v, objType) for v in choices.values()):
                choices = dict()

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
            "choices": choices,
            "readOnly": False,
            "objId": objId
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
            return leaf.data(ObjectDataRole) # noqa

    def getPathForLeaf(self: typing.Self,
                       leaf: typing.Union[QtCore.QModelIndex,
                                          QtGui.QStandardItem],
                       pathOnly: bool = False,
                       # includeRoot:bool = False
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
        if item.data(StandaloneEditorWidgetRole): # noqa
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

            parentAccess = parentItem.data(ObjectDataAccessRole) # noqa
            bindingType = targetItem.data(ObjectKeyTypeRole) # noqa
            itemBinding = targetItem.data(ObjectKeyRole) # noqa
            # print(f"{self.__class__.__name__}._getPathForItemOrIndex_: bindingType for {targetItem.data(QtCore.Qt.DisplayRole)} -> {bindingType}")
            # print(f"{self.__class__.__name__}._getPathForItemOrIndex_: itemBinding -> {itemBinding}")

            if itemBinding:
                if len(parentAccess) == 1:
                    # print(f"{self.__class__.__name__}._getPathForItemOrIndex_ -> add access {parentAccess[0]}{itemBinding}")
                    path.append(f"{parentAccess[0]}{itemBinding}")

                elif len(parentAccess) == 2:
                    # print(f"{self.__class__.__name__}_getPathForItemOrIndex_: bindingType = {bindingType} for itemBinding {itemBinding}")
                    if bindingType is weakref.ReferenceType:
                        path.append(f"{parentAccess[0]}{itemBinding}{parentAccess[1]}")
                    else:
                        if bindingType is str:
                            iB = f"'{itemBinding}'"
                        else:
                            try:
                                iB = bindingType(itemBinding) # hedging my bets...
                            except:
                                iB = itemBinding


                        path.append(f"{parentAccess[0]}{iB}{parentAccess[1]}")

            path += self._getPathForItemOrIndex_(parentItem)

        elif item == self._topObjectItem_:
            # NOTE: 2026-02-10 12:26:33
            # this one is in column 0 by design
            path += [self._topObjectItem_.data(QtCore.Qt.DisplayRole)]

        return path

    def setData(self: typing.Self, modelIndex: QtCore.QModelIndex,
                value: object, role = QtCore.Qt.EditRole) -> bool:
        if self._modelData_ is None:
            return False
        # print(f"{self.__class__.__name__}.setData {value}\n\tfor index {modelIndex.data(QtCore.Qt.DisplayRole)},\n\trow {modelIndex.row()}\n")

        item = self.itemFromIndex(modelIndex)

        # print(f"{self.__class__.__name__}.setData: item at column {item.column()} -> edit data: {item.data(QtCore.Qt.EditRole)}")
        # print(f"{self.__class__.__name__}.setData: item at column {item.column()} -> read only: {item.data(ReadOnlyRole)}")

        if item.data(ReadOnlyRole) is True: # noqa
            return

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

        # if isinstance(value, (enum.Enum, enum.IntEnum, enum.Flag, TypeEnum)):
        #     print(f"setting value as {value}")

        # print(f"{self.__class__.__name__}.setData {value}\n\tfor objItem {objItem.data(QtCore.Qt.DisplayRole)},\n\trow {item.row()}\n")

        if item.column() == 2 and role == ObjectDataRole: # noqa
            parentItem = item.parent()
            if not parentItem:
                return False
            objItem = parentItem.child(item.row(), 0)

        objItem.setData(QtCore.QVariant(value), ObjectDataRole) # noqa

        path = self._getPathForItemOrIndex_(objItem)
        # print(f"\taccess to objItem: {path}")

        if path[-1] == self._topObjectItem_.data(QtCore.Qt.DisplayRole):
            path[-1] = "self._modelData_"

        accexpr = "".join(reversed(path))
        setexpr = accexpr + " = value"
        OK = False
        try:
            # print(f"{self.__class__.__name__}.setData: setexpr = {setexpr}")
            exec(setexpr)
            newVal = eval(accexpr)
            OK = True
        except:
            traceback.print_exc()
            pass

        if OK:
            objType = objItem.data(ObjectTypeRole) # noqa

            if objType is pathlib.Path and not isinstance(newVal, pathlib.Path):
                newVal = pathlib.Path(newVal)

            objItem.setData(newVal, ObjectDataRole) # noqa

            if item != objItem:
                if isinstance(newVal, (enum.Enum, enum.IntEnum, enum.Flag, TypeEnum)):
                    item.setData(QtCore.QVariant(newVal.name), QtCore.Qt.DisplayRole)
                elif isinstance(newVal, bool):
                    item.setData(QtCore.QVariant(str(newVal)), QtCore.Qt.DisplayRole)
                else:
                    item.setData(QtCore.QVariant(newVal), QtCore.Qt.DisplayRole)
                item.setData(newVal, ObjectDataRole) # noqa

            self.dataChanged.emit(modelIndex, modelIndex)
            self.sig_modelDataChanged.emit()

        return OK




