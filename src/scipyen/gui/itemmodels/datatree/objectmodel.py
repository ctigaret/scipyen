# $Id: datatreemodel.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

# from __future__ import print_function

import os # noqa
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

import qtpy # noqa
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, ) # noqa
from qtpy.QtCore import (Signal, Slot, Property,) # noqa
__has_PySide6__ = False
__has_PyQt6__ = False
# __has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    # import PySide6
    # from PySide6 import Shiboken
    # from PySide6.QtCore import (Signal, Slot, Property,)
    # from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True

    # from qtpy import sip
    # from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    # __has_sip__ = True

try:
    from pyqtgraph.widgets.DataTreeWidget import HAVE_METAARRAY
except Exception: # noqa
    HAVE_METAARRAY = None

HAS_MESHIO = False
try:
    import meshio
    HAS_MESHIO = True
except: # noqa
    pass

# from pyqtgraph import (DataTreeWidget, TableWidget, )

import neo # noqa
if neo.__version__ >= '0.13.0':
    from neo.core.objectlist import ObjectList as NeoObjectList
import quantities as pq # noqa
import numpy as np
import scipy
import pandas as pd
import vigra
import meshio
from treelib import Tree, Node
# ### END 3rd party modules

from core.qtutils import qVariant #, QVariantType #, qVariants, fromQVariant, isQObjectAlive)
import core.datatypes as datatypes # noqa
from core.datatypes import (is_namedtuple, TypeEnum)
from core.prog import (scipywarn, timefunc, processtimefunc)  # noqa
from core import taxonbridge
from core import bgbridge
from core.triggerprotocols import TriggerProtocol # noqa
from core.triggerevent import (DataMark, TriggerEvent, TriggerEventType) # noqa
import core.datasignal as datasignal # noqa
from core.datasignal import (DataSignal, IrregularlySampledDataSignal) # noqa
import core.datazone as datazone # noqa
from core.datazone import (DataZone, Interval)
from core import xmlutils, strutils # noqa
from core import scipyen_quantities as scq
from core.utilities import unique
from core.prog import (safewrapper, safeguiwrapper, print_styled, # noqa
                       is_hashable)
from core.traitcontainers import (DataBag, DataBagTraitsObserver,) # noqa
from core.scipyendataclasses import (isDataclass, getField, getFieldOrProperty)
from core.datatypes import PODS

from ephys import ephys_protocol

# print(f"has brain globe: {bgbridge.hasBrainGlobe}")

# NOTE: 2026-02-07 09:14:19 FIXME/TODO
# to break cycling dependencies in systems.PrairieView, which needs this for the
# importer gui, MOVE the latter to a separate module
from systems.PrairieView import *

from imaging import vigrautils # noqa
import imaging.axiscalibration
from imaging.axiscalibration import (
    AxesCalibration,
    AxisCalibrationData,
    ChannelCalibrationData,
)
from imaging.axisutils import (axisTypeStrings, # noqa
                               getValueForAxisType,
                               getNameForAxisType)
import imaging.scandata # noqa
from imaging.scandata import (ScanData, AnalysisUnit) # noqa

from gui.itemmodels.roles import *

from gui.itemmodels.datatree import objectnode as onode
from gui.itemmodels.datatree.objectnode import ObjectNode, ObjectInfo


NOTMEMOIZED = (
    tuple,
    type(None),
    type(MISSING),
    type(pd.NA),
    type,
    np.ndarray,
    np.bool,
    np.complexfloating,
    np.floating,
    np.integer,
    np.ufunc,
    types.ModuleType,
    pkgutil.ModuleInfo,
    typing.Callable,
    types.FunctionType,
    functools.partial
)


FUNCTION_TYPES = (
    types.FunctionType,
    types.BuiltinFunctionType,
    types.MethodType,
    types.BuiltinMethodType
    )

NOTINTROSPECTABLE = PODS + (types.ModuleType, pkgutil.ModuleInfo) + FUNCTION_TYPES

class ObjectModel(QtGui.QStandardItemModel):
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

    # _sig_branchLoaded = Signal(int, tuple, QtGui.QStandardItem, name="_sig_branchLoaded")

    sig_editCompleted = Signal([pd.DataFrame], [pd.Series], [np.ndarray], name="sig_editCompleted")
    sig_modelDataChanged = Signal(name="sig_modelDataChanged")

    # def _check_public_member_(x: object, y: object | None = None):
    @staticmethod
    def _check_public_member_(x: tuple):
        # return not (isinstance(x[0], str) and not x[0].startswith("_"))
        return (not isinstance(x[0], str) or not x[0].startswith("_"))

    def __init__(self: typing.Self, data: object | None = None,
                 dataName: str | None = None,
                 parent: QtCore.QObject | None = None,
                 **kwargs):
        super().__init__(0, 3, parent=parent)
        # print(f"{self.__class__.__name__}.__init__")
        # print(f"\n\tcall self.beginResetModel()")
        self._maxRows_ = 10
        self._tree_: Tree = Tree()
        self._rootNode_: ObjectNode | None = None
        self._modelData_: object | None = None
        self._rootTitle_ = "/" if not isinstance(dataName, str) or len(dataName.strip()) else dataName
        self._inlineTables_: bool = kwargs.pop("inlineTables", False)
        self._readOnly_: bool = kwargs.pop("readOnly", True)
        self._readOnlyChildren_: bool = kwargs.pop("readOnlyChildren", True)
        self._introspect_: bool = kwargs.pop("showIntrospection", True)
        self._predicate_: types.FunctionType | None = kwargs.pop("predicate", None)
        self._showPrivate_: bool = kwargs.pop("showPrivateMembers", False)
        self._showCallables_ = kwargs.pop("showCallables", False)
        self._showValueAttributesOnly_ = kwargs.pop("valuesOnly", True)
        self._supportedDataTypes_ = kwargs.pop("supportedTypes", ())
        if not isinstance(self._supportedDataTypes_, tuple) or not all(
            isinstance(v, type) for v in self._supportedDataTypes_
        ):
            self._supportedDataTypes_ = ()

        self.beginResetModel()
        # self._dataTypeStr_: str = ""
        # self._visited_: dict = {}
        # self._visited_: set = set()
        # self._hasDynamicPrivate_: bool = False
        # self._privateData_: dict | None = None
        # self._hideRoot_: bool = False
        # self._topObjectItem_: QtGui.QStandardItem | None = None


        # self._sortedRows_: bool = False


        # self._readOnly_ =



        self.setHorizontalHeaderLabels(["Object", "Type", "Information or Value"])

        self.endResetModel()

        # self._sig_branchLoaded.connect(self._slot_branchLoaded)

    # def canFetchMore(self, parentIndex: QtCore.QModelIndex) -> bool:
    #     return False if parentIndex.isValid() else parentIndex.rowCount() <

    @Slot(QtCore.QModelIndex)
    def slot_indexExpanded(self, index: QtCore.QModelIndex):
        if not index.isValid() or index.column() !=0:
            return

        item = self.itemFromIndex(index)

        # WARNING: 2026-09-22 23:23:51
        # This might need running in a separate thread
        # potential role for self.canFetchMore() and self.fetchMore()

        itemNode = item.data(ObjectDataRole)
        objectChildren = itemNode.objectInfo.children

        if len(objectChildren) == 0:
            # should NOT happen: child-less objectNodes shuld correspond to
            # items with rowCount==0
            return

        successors = itemNode.successors(self._tree_.identifier)

        # CAUTION: 2026-09-22 23:23:46
        # this is fragile -> better write a version of populateNode to take into account the ``item``
        if len(objectChildren) == item.rowCount() and len(objectChildren) == len(successors):
            return

        onode.populateNode(self._tree_, itemNode,
                           introspect=self.showIntrospection,
                           predicate=self._predicate_,
                           includePrivate=self.showPrivateMembers,
                           includeCallables=self.showCallables,
                           includeTypeMembers=not self.showValuesOnly,
                           choices={},
                           )

        # pre-allocates rows, but would this be compatible with
        # canFetchMore/fetchMore (if I decide to implement it)?
        item.setRowCount(len(objectChildren))

        # self.beginInsertRow()
        for row, node in enumerate(successors):
            childRow = self._makeRowForNode_(node)
            for col in range(len(childRow)):
                item.setChild(row, col, childRow[col])
        # self.endInsertRow()









    @property
    def maxRows(self) -> int:
        return self._maxRows_

    @maxRows.setter
    def maxRows(self, val:int):
        self._maxRows_ = max(val, 10)

    @property
    def topObjectItem(self: typing.Self) -> QtGui.QStandardItem | None:
        return self._topObjectItem_

    @property
    def topIndex(self) -> QtCore.QModelIndex:
        return self.indexFromItem(self.topObjectItem)

    @property
    def rootItem(self):
        return self.invisibleRootItem()

    @property
    def rootIndex(self):
        return self.indexFromItem(self.rootItem)

    @property
    def inlineTables(self) -> bool:
        return self._inlineTables_

    @inlineTables.setter
    def inlineTables(self, val: bool):
        if val != self._inlineTables_:
            self._inlineTables_ = val is True

    @property
    def readOnly(self: typing.Self) -> bool:
        return self._readOnly_

    @readOnly.setter
    def readOnly(self: typing.Self, val: bool):
        self._readOnly_ = val is True

    @property
    def readOnlyChildren(self: typing.Self) -> bool:
        return self._readOnlyChildren_

    @readOnlyChildren.setter
    def readOnlyChildren(self: typing.Self, val: bool):
        self._readOnlyChildren_ = val is True

    def _makeRowForNode_(self, objectNode: ObjectNode):#, parentItem: QtGui.QStandardItem) -> tuple:
        objectItem = QtGui.QStandardItem(objectNode.objectInfo.name)

        # might not need this
        objectItem.setData(qVariant(False), PopulatedChildrenRole)

        # definitely not needed, as this is the node's payload
        # the question is:
        # should this be the case for ALL nodes, or only
        # for the root node ? would the former use more memory?
        # objectItem.setData(qVariant(obj), ObjectDataRole)

        # NOTE: 2026-09-21 13:25:42
        # in the former case (store data as payload for each node)
        # • there is access directly to the data object
        # • payload is stored by reference so I'm inclined to stick with this
        #
        # in the latter case (store top object as payload to the root node only)
        #  • one must gain access to the rootNode up the hierarchy and build up
        # the access expression «on the fly»

        # objectItem.setData(qVariant(obj), objectNode)
        # objectItem.setData(qVariant(objectNode.objectInfo), ObjectDataRole) ## keep this slim
        # objectItem.setData(qVariant(objectNode.data), ObjectDataRole) ## this expects all Node instances to have a payload!
        objectItem.setData(qVariant(objectNode), ObjectDataRole) ## how about this !?

        objectItem.setData(objectNode.objectInfo.name, QtCore.Qt.DisplayRole)
        objectItem.setData(objectNode.objectInfo.objTip, QtCore.Qt.ToolTipRole)

        if objectNode.objectInfo.objDataAsChild:
            editExternally = not self._inlineTables_
            objectItem.setData(editExternally, ObjectDataEditExternallyRole)
            if self._inlineTables_:
                dataItem = QtGui.QStandardItem("")
                dataItem.setData(qVariant(True), StandaloneEditorWidgetRole)
                dataItem.setRowCount(0)

                objectItem.setRowCount(1)
                objectItem.setChild(0, dataItem)
                objectItem.setData(qVariant(1), ObjectChildrenCountRole)
            else:
                objectItem.setRowCount(0)
                objectItem.setData(qVariant(0), ObjectChildrenCountRole)

        else:
            nChildren = len(objectNode.objectInfo.children)
            objectItem.setRowCount(nChildren)
            objectItem.setData(qVariant(nChildren), ObjectChildrenCountRole)

        typeName = objectNode.objectInfo.objType.__name__ # check with ObjectNode and objectnode.populateNode if we use references or not
        # if isinstance(objectNode.objectInfo.referenceInfo, ObjectInfo):
        #     typeName = objectNode.objectInfo.referenceInfo.objType.__name__
        # else:
        #     typeName = objectNode.objectInfo.objType.__name__

        objectTypeItem = QtGui.QStandardItem(typeName)
        objectTypeItem.setData(typeName, QtCore.Qt.DisplayRole)
        objectTypeItem.setData(qVariant(0), ObjectChildrenCountRole)

        objectInfoValueItem = QtGui.QStandardItem(objectNode.objectInfo.objInfo)
        if isinstance(objectNode.data, pathlib.Path):
            if __has_PySide6__:
                objectInfoValueItem.setData(objectNode.data, ObjectDataRole) # expects Node payload
                # objectInfoValueItem.setData(obj, ObjectDataRole)
                objectInfoValueItem.setData(objectNode.objectInfo.objInfo, QtCore.Qt.EditRole)
            else:
                objectInfoValueItem.setData(objectNode.data, QtCore.Qt.EditRole) # expects Node payload
                # objectInfoValueItem.setData(obj, QtCore.Qt.EditRole)
        else:
            objectInfoValueItem.setData(objectNode.objectInfo.objInfo, QtCore.Qt.EditRole)

        objectInfoValueItem.setData(objectNode.objectInfo.choices, DataChoicesRole)
        objectInfoValueItem.setData(qVariant(0), ObjectChildrenCountRole)
        # also not needed? (stored in objectInfo)
        # objectItem.setData(qVariant(memberAccess), ObjectDataAccessRole)
        # objectItem.setData(qVariant(accessType), ObjectDataAccessTypeRole)

        flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable
        readOnlyFlags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsEnabled

        readOnly = objectNode.objectInfo.readOnly is True or self.readOnly
        readOnlyChildren = objectNode.objectInfo.readOnlyChildren is True or self.readOnly

        palette = QtWidgets.QApplication.palette()
        font = QtWidgets.QApplication.font()
        brush = palette.brush(QtGui.QPalette.Active, QtGui.QPalette.Text)
        readOnlyFont = QtGui.QFont(font)
        readOnlyFont.setItalic(True)
        readOnlyBrush = palette.brush(QtGui.QPalette.Inactive, QtGui.QPalette.Text)

        for k, item in enumerate((objectItem, objectTypeItem, objectInfoValueItem)):
            item.setData(readOnly, ReadOnlyRole) # star import from gui.itemmodels.roles
            item.setData(readOnlyChildren, ReadOnlyChildrenRole) # star import from gui.itemmodels.roles
            if k == 2:
                if readOnly or (
                                    (
                                        objectNode.objectInfo.indirect is True
                                        or objectNode.objectInfo.objDataAsChild is True
                                    )
                                    and len(objectNode.objectInfo.choices) == 0
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

        return (objectItem, objectTypeItem, objectInfoValueItem)

    # def _makeObjectRow_(self: typing.Self, objNode: ObjectNode, /,
    #                    objDict: dict, objKey: object,
    #                    objKeyType: type, visited:tuple=()) -> tuple:
    #     # NOTE: 2026-09-12 11:16:59
    #     # also sets the row count for the item in column 0
    #     # ATTENTION: make sure you don't do this twice!
    #
    #     typeName = objDict["objType"].__name__
    #
    #     info = objDict["objInfo"]
    #
    #     # if isinstance(info, (bool, np.floating, np.integer, np.complexfloating)):
    #     #     info = f"{info}"
    #
    #     memberAccess = objDict["memberAccess"]
    #     accessType = objDict.get("accessType", None)
    #
    #     if isinstance(objKey, str):
    #         objName = objKey
    #
    #     elif is_hashable(objKey):
    #         objName = f"{objKey}"
    #
    #     else:
    #         objName = ""
    #
    #     if len(objName.strip()) == 0:
    #         objName = "/"
    #
    #     # print(f"{self.__class__.__name__}._makeObjectRow_: objName -> {objName}")
    #
    #     objectItem = QtGui.QStandardItem(objName)
    #     objectItem.setData(qVariant(False), PopulatedChildrenRole)
    #     # NOTE: 2026-02-09 21:47:38
    #     # reference to the actual Python object
    #     objectItem.setData(qVariant(obj), ObjectDataRole)
    #
    #     objectItem.setData(objName, QtCore.Qt.DisplayRole)
    #     objectItem.setData(objDict["objType"], ObjectTypeRole)
    #     objectItem.setData(objDict["objType"].__name__, QtCore.Qt.ToolTipRole)
    #
    #     # NOTE: 2026-02-09 21:47:57
    #     # reference to the object's binding in its parent: i.e.
    #     # • the symbol of an attribute or field (↦ str),
    #     # • the index into sequences (↦ int),
    #     # • the key in a mapping (↦ a hashable)
    #     objectItem.setData(qVariant(objKey), ObjectKeyRole)
    #
    #     # NOTE: 2026-09-12 11:12:06
    #     # the type of the key inside the obj (str, int, or other hashable)
    #     objectItem.setData(qVariant(objKeyType), ObjectKeyTypeRole)
    #
    #     # NOTE: 2026-02-09 21:47:10
    #     # used to construct the acess path to the object for this item
    #     objectItem.setData(qVariant(memberAccess), ObjectDataAccessRole)
    #     objectItem.setData(qVariant(accessType), ObjectDataAccessTypeRole)
    #
    #     editExternally = objDict["objDataAsChild"] and not self._inlineTables_
    #     objectItem.setData(editExternally, ObjectDataEditExternallyRole) # star import from gui.itemmodels.roles
    #
    #     if objDict["objDataAsChild"] and self._inlineTables_:
    #         # NOTE: 2026-09-12 11:07:38
    #         # dataItem holds the widget for the object data (i.e. a table or text editor)
    #         dataItem = QtGui.QStandardItem("")
    #         dataItem.setData(qVariant(True), StandaloneEditorWidgetRole)
    #         dataItem.setRowCount(0)
    #
    #         objectItem.setRowCount(1)
    #         objectItem.setChild(0, dataItem)
    #         objectItem.setData(qVariant(1), ObjectChildrenCountRole)
    #
    #     elif len(visited):
    #         objectItem.setRowCount(0)
    #         objectItem.setData(qVariant(0), ObjectChildrenCountRole)
    #
    #     else:
    #         # NOTE: 2026-09-12 11:08:32
    #         # rows of objectItem to be populated within _buildBranch_(…)
    #         objectItem.setRowCount(objDict["nChildren"])
    #         objectItem.setData(qVariant(objDict["nChildren"]), ObjectChildrenCountRole)
    #
    #
    #     # NOTE: 2026-02-09 21:49:05
    #     # object "bindings" are are int for sequences, any hashable object type
    #     # (including str and int) for mappings, str for attributes & fields.
    #     #
    #     # iterators are NOT supported (they're used to yield elements of a
    #     # collection dynamically, anyway, and a reason for using them is a
    #     # "lazy" evaluation of the collection's contents - in itself for a good
    #     # reason) ; therefore, I apply the same philosophy here
    #     #
    #
    #     if len(visited):
    #         typeName = visited[-1].__name__
    #
    #     # for user's benefit — good to know the type of the object is represented
    #     # in this row.
    #     objectTypeItem = QtGui.QStandardItem(typeName)
    #     objectTypeItem.setData(typeName, QtCore.Qt.DisplayRole)
    #     objectTypeItem.setData(qVariant(0), ObjectChildrenCountRole)
    #     # either:
    #     #
    #     # a) display some object info for the user's benefit; this can be:
    #     #
    #     #   a.1) a string representation of the object's value — can be edited
    #     #        if required, see below
    #     #
    #     #   a.2) additional information such as size, shape, dtype, for tabular
    #     #       data (arrays, pandas objects) — these are editable via an editor
    #     #       in the first child of item 0 when needed, to be set up by the
    #     #       client user of this model
    #     #
    #     # b) offer a delegate editor widget so that user can modify the value
    #     #
    #     # "choices" goes as item data with objectDataRole for THIS item
    #     if visited:
    #         targetPath = visited[2]
    #         objectInfoValueItem = QtGui.QStandardItem(f"<reference to {targetPath}>")
    #
    #     else:
    #         objectInfoValueItem = QtGui.QStandardItem(f"{info}")
    #
    #         if isinstance(obj, pathlib.Path):
    #             if __has_PySide6__:
    #                 objectInfoValueItem.setData(obj, ObjectDataRole)
    #                 objectInfoValueItem.setData(info, QtCore.Qt.EditRole)
    #             else:
    #                 objectInfoValueItem.setData(obj, QtCore.Qt.EditRole)
    #         else:
    #             objectInfoValueItem.setData(info, QtCore.Qt.EditRole)
    #
    #         choices = objDict.get("choices", {})
    #         objectInfoValueItem.setData(choices, DataChoicesRole)
    #
    #     objectInfoValueItem.setData(qVariant(0), ObjectChildrenCountRole)
    #
    #     flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable
    #     readOnlyFlags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsEnabled
    #
    #     readOnly = objDict.get("readOnly", False) is True or self.readOnly
    #     readOnlyChildren = objDict.get("readOnlyChildren", False) is True or self.readOnly
    #
    #     palette = QtWidgets.QApplication.palette()
    #     font = QtWidgets.QApplication.font()
    #     brush = palette.brush(QtGui.QPalette.Active, QtGui.QPalette.Text)
    #     readOnlyFont = QtGui.QFont(font)
    #     readOnlyFont.setItalic(True)
    #     readOnlyBrush = palette.brush(QtGui.QPalette.Inactive, QtGui.QPalette.Text)
    #
    #     for k, item in enumerate((objectItem, objectTypeItem, objectInfoValueItem)):
    #         item.setData(readOnly, ReadOnlyRole) # star import from gui.itemmodels.roles
    #         item.setData(readOnlyChildren, ReadOnlyChildrenRole) # star import from gui.itemmodels.roles
    #         if k == 2:
    #             if readOnly or (
    #                                 (
    #                                     objDict.get("indirect", False) is True
    #                                     or objDict.get("objDataAsChild", False) is True
    #                                 )
    #                                 and len(objDict.get("choices", {})) == 0
    #                             ):
    #                 item.setData(readOnlyBrush, QtCore.Qt.ForegroundRole)
    #                 item.setData(readOnlyFont, QtCore.Qt.FontRole)
    #                 item.setFlags(readOnlyFlags)
    #
    #             else:
    #                 item.setData(brush, QtCore.Qt.ForegroundRole)
    #                 item.setData(font, QtCore.Qt.FontRole)
    #                 item.setFlags(flags)
    #         else:
    #             # prohibit editing in columns 0 and 1
    #             item.setData(brush, QtCore.Qt.ForegroundRole)
    #             item.setData(font, QtCore.Qt.FontRole)
    #             item.setFlags(readOnlyFlags)
    #
    #     return (objectItem, objectTypeItem, objectInfoValueItem)

    # @timefunc
    def populateModel(self, obj: object, rootTitle: str = "",
                        inlineTables: bool = False,
                        introspect: bool = False,
                        predicate: types.FunctionType | None = None,
                        showPrivate: bool = False,
                        callables: bool = False,
                        valuesOnly: bool = True,
                        choices: dict | None = None,
                        readOnly: bool = False,
                        readOnlyChildren: bool = False,
                        # hideRoot: bool = False,
                    ):
        # print(f"{self.__class__.__name__}.populateModel({type(obj)}, rootTitle: {rootTitle})")
        # print(f"\n\t-> call self.clear()")
        # ### BEGIN WARNING: 2026-06-28 11:43:14
        # this calls beginResetModel() ... endResetModel() already,
        # therefore it MUST NOT follow an isolated call to beginResetModel
        self.clear()
        # ### END   WARNING: 2026-06-28 11:43:14
        # print(f"\n\t-> call self.beginResetModel()")
        self.beginResetModel()
        # self._visited_.clear()
        # self._hideRoot_ = hideRoot is True
        self._introspect_ = introspect is True
        self._predicate_ = predicate
        self._showPrivate_ = showPrivate is True
        self._showCallables_ = callables is True,
        self._showValueAttributesOnly_ = valuesOnly is True
        self._inlineTables_ = inlineTables is True
        self._readOnly_ = readOnly is True
        self._readOnlyChildren_ = readOnlyChildren is True

        self._rootTitle_ = rootTitle if (
            isinstance(rootTitle, str)
            and len(rootTitle.strip())
            ) else "/"

        if (len(self._tree_.nodes)
            and isinstance(self._rootNode_, ObjectNode)
            and self._rootNode_.identifier in self._tree_):
            self._tree_.remove_node(self._rootNode_.identifier)

        if not isinstance(choices, dict):
            choices = {}

        self._rootNode_ = onode.createNode(obj, self._rootTitle_,
                                           storeData = True,
                                           introspect = self._introspect_,
                                           predicate = self._predicate_,
                                           includePrivate = self._showPrivate_,
                                           includeCallables = self._showCallables_,
                                           includeTypeMembers = not self._showValueAttributesOnly_,
                                           choices = choices,
                                           readOnly = self._readOnly_,
                                           readOnlyChildren = self._readOnly_)

        self._tree_.add_node(self._rootNode_)
        # print(f"\n\t-> assign to self._modelData_")
        self._modelData_ = self._rootNode_.data

        rowItems = self._makeRowForNode_(self._rootNode_)

        rootItem = self.invisibleRootItem()
        rootItem.setRowCount(1)
        rootItem.setColumnCount(3)

        for ki, item in enumerate(rowItems):
            rootItem.setChild(0, ki, item)


        # needs calling again because beginResetModel() was called
        self.setHorizontalHeaderLabels(["Object", "Type", "Information or Value"])

        # pData, objDict = self._parseObject_(obj, self._showPrivate_, {})

        self.setRowCount(1) #objDict["nChildren"])

        # self._privateData_ = pData

        # self._topObjectItem_ = self._buildTree_(self._privateData_, objDict, self._rootTitle_)

        # print(f"\n\t-> call self.endResetModel()")
        self.endResetModel()

    # def _buildTree_(self: typing.Self, obj: object, objDict: dict, name: str = "") -> QtGui.QStandardItem:
    #
    #     # 1. get the top object symbol, type and some information, as items to
    #     # go as the first (and only) top-level row in the model
    #
    #     # print(f"{self.__class__.__name__}._buildTree_(obj: {type(obj).__name__})")
    #     rootItem = self.invisibleRootItem()
    #     rootItem.setRowCount(1)
    #     item = self._buildBranch_(self._privateData_, objDict, name, str, rootItem, 0,
    #                               debug=False)
    #     if self.readOnly:
    #         item.setData(self.readOnly, ReadOnlyRole)
    #
    #     return item


    # @Slot(int, tuple, QtGui.QStandardItem)
    # def _slot_branchLoaded(self, row: int, items: tuple[QtGui.QStandardItem],
    #                        parentItem: QtGui.QStandardItem, ):
    #     parentItem.insertRow(row, items)

    # @singledispatchmethod
    # def _buildBranch_(self: typing.Self, obj: object, objDict: dict,
    #                   objKey: object, objKeyType: type,
    #                   parentItem: QtGui.QStandardItem,
    #                   row: int, debug: bool=False) -> QtGui.QStandardItem:
    #     # NOTE: 2026-09-12 11:06:13
    #     # parentItem row count MUST set before calling this method
    #     # NOTE: this might be done in _makeObjectRow_
    #
    #     if debug:
    #         print(f"_buildBranch_{type(obj)}(obj={obj}, objDict={objDict}, objKey={objKey}, objKeyType={objKeyType}, parentItem={parentItem.data(QtCore.Qt.DisplayRole)}, row={row})")
    #
    #     visited = ()
    #     objId = objDict["objId"]
    #     # print(f"{self.__class__.__name__}._buildBranch_{type(obj)} with ID: {objId}")
    #
    #     if self._is_memoized_(obj, objId, objDict):
    #         # print(f"\n\tfound visited: {visited}")
    #         visited = self._visited_[objId]
    #
    #     if debug:
    #         print(f"\tvisited: {visited}")
    #
    #     rowItems = self._makeObjectRow_(obj, objDict, objKey, objKeyType, visited)
    #
    #     objItem = rowItems[0] # objItem row count already set by _makeObjectRow_
    #
    #     for ki, item in enumerate(rowItems):
    #         parentItem.setChild(row, ki, item)
    #
    #     if len(visited):
    #         objItem.setRowCount(0)
    #         return objItem
    #
    #     if debug:
    #         print(f"\tparentItem.hasChildren: {parentItem.hasChildren()}")
    #
    #     if (
    #         self._can_memoize_(obj)
    #         and objId not in self._visited_
    #         ):
    #         itemPath = f"{self._rootTitle_}{self.getPathForLeaf(objItem)}"
    #         self._memoize_(obj, itemPath, objDict)
    #
    #     return objItem

    # @_buildBranch_.register(dict)
    # @_buildBranch_.register(UserDict)
    # @_buildBranch_.register(types.MappingProxyType)
    # @_buildBranch_.register(OrderedDict)
    # def __buildBranch_(self: typing.Self, obj: dict |types.MappingProxyType | UserDict | OrderedDict,
    #       objDict: dict, objKey: object, objKeyType: type,
    #       parentItem: QtGui.QStandardItem, row: int, debug: bool=False) -> QtGui.QStandardItem:
    #     # NOTE: 2026-09-12 11:29:44 WARNING
    #     # ALL objects represented as dict in self._privateData_ WILL be passed here
    #     #
    #
    #     if debug:
    #         print(f"_buildBranch_{type(obj)}(obj={obj}, objDict={objDict}, objKey={objKey}, objKeyType={objKeyType}, parentItem={parentItem.data(QtCore.Qt.DisplayRole)}, row={row})")
    #
    #     visited = ()
    #     objId = objDict["objId"]
    #
    #     # print(f"{self.__class__.__name__}._buildBranch_{type(obj)} with ID: {objId}")
    #
    #     if self._is_memoized_(obj, objId, objDict):
    #         # print(f"\n\tfound visited: {visited}")
    #         visited = self._visited_[objId]
    #
    #     rowItems = self._makeObjectRow_(obj, objDict, objKey, objKeyType, visited)
    #
    #     for ki, item in enumerate(rowItems):
    #         parentItem.setChild(row, ki, item)
    #
    #     objItem = rowItems[0]
    #
    #     if len(visited):
    #         # NOTE: 2026-09-10 14:46:36
    #         # if this was visited already then return it;
    #         # else, proceed with populating its own subtree (see NOTE: 2026-09-10 14:47:10)
    #         # self._sig_branchLoaded.emit(row, rowItems, parentItem)
    #         objItem.setRowCount(0)
    #         return objItem
    #
    #     # showInline = (objDict["objDataAsChild"] and not self._inlineTables_) or not objDict["objDataAsChild"]
    #
    #     if not objDict["objDataAsChild"]:
    #         # return objItem
    #         # NOTE: 2026-09-10 14:47:10
    #         # populate the object's subtree
    #
    #         # if objKey == "adcNames":
    #         #     print(f"adcNames {len(obj)}")
    #
    #         for k, (key, value) in enumerate(obj.items()):
    #             if isinstance(key, str):
    #                 keyName = key
    #
    #             else:
    #                 keyName = f"{key}"
    #
    #             # TODO/FIXME: 2026-03-28 17:13:47
    #             # try and read the object's options for this member ("value")
    #             # and create choices accordingly
    #             pValue, valDict = self._parseObject_(value, self._showPrivate_, {})
    #
    #             # if debug:
    #             #     print(f"\t{k} -> {key} -> {value} -> {pValue}")
    #
    #             if (objDict.get("readOnlyChildren", False) is True) or self.readOnly:
    #                 valDict["readOnly"] = True
    #
    #             # print(f"{self.__class__.__name__}._buildBranch_ for {key} in {objItem.data(QtCore.Qt.DisplayRole)}")
    #
    #             self._buildBranch_(pValue, valDict, keyName, type(key), objItem, k,
    #                                debug=False)
    #
    #             # if objKey == "adcNames":
    #             #     self._buildBranch_(pValue, valDict, keyName, type(key), objItem, k, debug=True)
    #             # else:
    #             #     self._buildBranch_(pValue, valDict, keyName, type(key), objItem, k)
    #
    #
    #     if (
    #         self._can_memoize_(obj)
    #         and objId not in self._visited_
    #         ):
    #         itemPath = f"{self._rootTitle_}{self.getPathForLeaf(objItem)}"
    #         self._memoize_(obj, itemPath, objDict)
    #
    #     # # NOTE: 2026-09-12 14:14:02
    #     # # now add this object to its parent, as child
    #     # if isinstance(parentItem, QtGui.QStandardItem):
    #     #     # parentItem.setRowCount(len(obj))
    #     #     # NOTE: 2026-09-10 14:45:25
    #     #     # FIRST populate the row of items (three columns),
    #     #     # THEN memoize if needed (and possible)
    #     #     for ki, item in enumerate(rowItems):
    #     #         parentItem.setChild(row, ki, item)
    #
    #
    #
    #     # self._sig_branchLoaded.emit(row, rowItems, parentItem)
    #
    #     return objItem

    @property
    def showCallables(self) -> bool:
        return self._showCallables_

    @showCallables.setter
    def showCallables(self, val:bool):
        self._showCallables_ = val is True

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

    # def _can_memoize_(self, obj) -> bool:
    #     # if isinstance(obj, str) and strutils.is_path(obj):
    #     #     return True
    #
    #     ret = (
    #         not isinstance(obj, NOTMEMOIZED + PODS)
    #         and not issubclass(type(obj), NOTMEMOIZED + PODS)
    #         )
    #
    #     return ret
    #
    # def _is_memoized_(self, obj, objId, objDict) -> bool:
    #     return (
    #         self._can_memoize_(obj)
    #         and objId in self._visited_
    #         and objDict["objType"] == self._visited_[objId][-1]
    #         )
    #
    # def _memoize_(self, obj, path, objDict):
    #     objId = objDict["objId"]
    #     realtype = objDict["objType"]
    #     if objId not in self._visited_:
    #         idx = len(self._visited_)
    #         self._visited_[objId] = (idx, type(obj), path, realtype)

    def itemChildren(self: typing.Self,
                     item: QtGui.QStandardItem) -> list:
        if not item.hasChildren():
            return []

        return [item.child(k, 0) for k in range(item.rowCount())]
        # return list(map(lambda k: item.child(k, 0), range(item.rowCount())))

    def getDataObjectForLeaf(self: typing.Self,
                             leaf: QtCore.QModelIndex | QtGui.QStandardItem,
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
                       leaf: QtCore.QModelIndex | QtGui.QStandardItem,
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
        indexOrItem: QtCore.QModelIndex | QtGui.QStandardItem
        ) -> typing.Sequence:
        if isinstance(indexOrItem, QtCore.QModelIndex):
            item = self.itemFromIndex(indexOrItem)
        else:
            item = indexOrItem

        path = []

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
        # Code below only makes sense for items in column 0; however, when an
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
                    # print(f"{self.__class__.__name__}_getPathForItemOrIndex_: bindingType = {bindingType} for itemBinding {itemBinding}")
                    if bindingType is weakref.ReferenceType:
                        path.append(f"{parentAccess[0]}{itemBinding}{parentAccess[1]}")
                    else:
                        if bindingType is str:
                            iB = f"'{itemBinding}'"
                        else:
                            try:
                                iB = bindingType(itemBinding) # hedging my bets...
                            except: # noqa
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

        if item.data(ReadOnlyRole) is True:
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

        if item.column() == 2 and role == ObjectDataRole:
            parentItem = item.parent()
            if not parentItem:
                return False
            objItem = parentItem.child(item.row(), 0)

        objItem.setData(qVariant(value), ObjectDataRole)

        path = self._getPathForItemOrIndex_(objItem)
        # print(f"\taccess to objItem: {path}")

        if path[-1] == self._topObjectItem_.data(QtCore.Qt.DisplayRole):
            path[-1] = "self._modelData_"

        accexpr = "".join(reversed(path))
        setexpr = accexpr + " = value"
        OK = False
        try:
            # print(f"{self.__class__.__name__}.setData: setexpr = {setexpr}")
            exec(setexpr) # noqa
            newVal = eval(accexpr)
            OK = True

        except: # noqa
            traceback.print_exc()

        if OK:
            objType = objItem.data(ObjectTypeRole)

            if objType is pathlib.Path and not isinstance(newVal, pathlib.Path):
                newVal = pathlib.Path(newVal)

            objItem.setData(newVal, ObjectDataRole)

            if item != objItem:
                if isinstance(newVal, (enum.Enum, enum.IntEnum, enum.Flag, TypeEnum)):
                    item.setData(qVariant(newVal.name), QtCore.Qt.DisplayRole)
                elif isinstance(newVal, bool):
                    item.setData(qVariant(str(newVal)), QtCore.Qt.DisplayRole)
                else:
                    item.setData(qVariant(newVal), QtCore.Qt.DisplayRole)
                item.setData(newVal, ObjectDataRole)

            self.dataChanged.emit(modelIndex, modelIndex)
            self.sig_modelDataChanged.emit()

        return OK

    def hasChildren(self, index:QtCore.QModelIndex) -> bool:
        # NOTE: 2026-09-10 12:06:10
        # the invisible root item has an invalid index (by default)
        # and calling self.itemFromIndex() on an invalid index returns None!
        item = self.itemFromIndex(index)
        if item:
            nChildren = item.data(ObjectChildrenCountRole)
            return isinstance(nChildren, int) and nChildren > 0

        elif index == self.invisibleRootItem().index():
            return self.invisibleRootItem().hasChildren()

        return False

#     def canFetchMore(self, parent: QtCore.QModelIndex) -> bool:
#         if not parent.isValid():
#             return False
#
#         item = self.itemFromIndex(parent)
#         if item.hasChildren():




    # @_generate_dict_.register(AxesCalibration)
    # def __generate_dict__(self, obj: AxesCalibration):
    #     pData = dict(enumerate(obj.calibrations))
    #     n = len(pData)
    #     return pData, n, n

