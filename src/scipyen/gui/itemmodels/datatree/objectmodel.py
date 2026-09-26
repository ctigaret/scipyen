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
# import inspect
# import dataclasses
# import numbers
import pathlib
# import datetime
# import fractions
# import decimal
import pkgutil
import typing
# import enum
import functools
from functools import singledispatchmethod  # noqa: F401
from collections import deque #, UserDict, OrderedDict
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

import numpy as np  # noqa: I001
import pandas as pd
from treelib import Tree #, Node
# ### END 3rd party modules

from core.qtutils import qVariant #, QVariantType #, qVariants, fromQVariant, isQObjectAlive)
import core.datatypes as datatypes # noqa
# from core.datatypes import (is_namedtuple, TypeEnum)
from core.prog import (scipywarn, timefunc, processtimefunc)  # noqa
# from core import taxonbridge
# from core import bgbridge
from core.triggerprotocols import TriggerProtocol # noqa
from core.triggerevent import (DataMark, TriggerEvent, TriggerEventType) # noqa
import core.datasignal as datasignal # noqa
from core.datasignal import (DataSignal, IrregularlySampledDataSignal) # noqa
import core.datazone as datazone # noqa
from core import xmlutils, strutils # noqa
from core.prog import (safewrapper, safeguiwrapper, print_styled, # noqa
                       is_hashable)
from core.traitcontainers import (DataBag, DataBagTraitsObserver,) # noqa
# from core.scipyendataclasses import (isDataclass, getField, getFieldOrProperty)
from core.datatypes import PODS

# from ephys import ephys_protocol

# print(f"has brain globe: {bgbridge.hasBrainGlobe}")

# NOTE: 2026-02-07 09:14:19 FIXME/TODO
# to break cycling dependencies in systems.PrairieView, which needs this for the
# importer gui, MOVE the latter to a separate module
# from systems.PrairieView import *
#
# from imaging import vigrautils
# import imaging.axiscalibration
# from imaging.axiscalibration import (
#     AxesCalibration,
#     AxisCalibrationData,
#     ChannelCalibrationData,
# )
# from imaging.axisutils import (axisTypeStrings,
#                                getValueForAxisType,
#                                getNameForAxisType)
# import imaging.scandata
# from imaging.scandata import (ScanData, AnalysisUnit)

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
        self._visited_: set = set()
        # self._hasDynamicPrivate_: bool = False
        # self._privateData_: dict | None = None
        # self._hideRoot_: bool = False
        self._topObjectItem_: QtGui.QStandardItem | None = None


        # self._sortedRows_: bool = False


        # self._readOnly_ =



        self.setHorizontalHeaderLabels(["Object", "Type", "Information or Value"])

        self.endResetModel()

        # self._sig_branchLoaded.connect(self._slot_branchLoaded)

    # def canFetchMore(self, parentIndex: QtCore.QModelIndex) -> bool:
    #     return False if parentIndex.isValid() else parentIndex.rowCount() <

    @Slot(QtCore.QModelIndex)
    def _slot_indexExpanded_(self, index: QtCore.QModelIndex):
        if not index.isValid() or index.column() !=0:
            print(f"{self.__class__.__name__}._slot_indexExpanded_ index is invalid")
            return

        item = self.itemFromIndex(index)

        # WARNING: 2026-09-22 23:23:51
        # This might need running in a separate thread
        # potential role for self.canFetchMore() and self.fetchMore()

        itemNode = item.data(ObjectDataRole)
        # print(f"{self.__class__.__name__}._slot_indexExpanded_ itemNode = {itemNode}")

        assert isinstance(itemNode, ObjectNode), f"{item.data()} does not associate an ObjectNode"

        objectChildren = itemNode.objectInfo.children

        if len(objectChildren) == 0:
            # should NOT happen: child-less objectNodes should correspond to
            # items with rowCount==0
            return

        successors = itemNode.successors(self._tree_.identifier)

        # CAUTION: 2026-09-22 23:23:46
        # this is fragile -> better write a version of populateNode to take into account the ``item``
        if len(objectChildren) == item.rowCount() and len(objectChildren) == len(successors):
            return

        itemNode.populate(self._tree_,
                          introspect=self.showIntrospection,
                          predicate=self._predicate_,
                          includePrivate=self.showPrivateMembers,
                          includeCallables=self.showCallables,
                          includeTypeMembers=not self.showValuesOnly,
                          choices={},
                          readOnly=self.readOnly,
                          readOnlyChildren=self.readOnlyChildren,
                        )
        # print(f"\t=> {len(childNodes)} child nodes")

        # FIXME: 2026-09-24 11:58:27
        # for childNode in childNodes:
        #     if (
        #         isinstance(childNode.data, Node)
        #         and isinstance(self.topObjectItem.data(ObjectDataRole), Tree)
        #         and
        #         ):
        #         # NOTE: This Node might actually belong to a tree
        #         # If the tree is the data associated with the topObjectItem
        #         # then check if this childNode is contained by it and report
        #         # its successors
        #         subChildren = childNode.data.successors

        # pre-allocates rows, but would this be compatible with
        # canFetchMore/fetchMore (if I decide to implement it)?
        item.setRowCount(len(objectChildren))

        # self.beginInsertRow()
        for row, nid in enumerate(successors):
            node = self._tree_.nodes[nid]
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
    def rootItem(self) -> QtGui.QStandardItem:
        return self.invisibleRootItem()

    @property
    def rootIndex(self) -> QtCore.QModelIndex:
        return self.indexFromItem(self.rootItem)

    @property
    def rootNode(self) -> ObjectNode | None:
        return self._rootNode_

    @property
    def tree(self) -> Tree:
        return self._tree_

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

    def _updateRowForNode_(self, item:QtGui.QStandardItem, objectNode: ObjectNode):
        r"""Updates data representation based on the objectNode"""
        # print(f"{self.__class__.__name__}._updateRowForNode_(item = {item.data(QtCore.Qt.DisplayRole)} at row {item.row()}, col {item.column()}, objectNode = {objectNode})")
        if item.column() == 0:
            objectItem = item
            objectTypeItem = self.getItemSibling(item, 1)
            objectInfoValueItem = self.getItemSibling(item, 2)

        elif item.column() == 1:
            objectItem = self.getItemSibling(item, 0)
            objectTypeItem = item
            objectInfoValueItem = self.getItemSibling(item, 2)

        elif item.column() == 2:
            objectItem = self.getItemSibling(item, 0)
            objectTypeItem = self.getItemSibling(item, 1)
            objectInfoValueItem = item

        else:
            return

        objectItem.setData(qVariant(objectNode), ObjectDataRole)
        objectItem.setData(qVariant(objectNode.objectInfo), ObjectInfoRole)
        objectItem.setData(objectNode.objectInfo.name, QtCore.Qt.DisplayRole)
        objectItem.setData(objectNode.objectInfo.objTip, QtCore.Qt.ToolTipRole)

        if objectNode.objectInfo.objDataAsChild:
            editExternally = not self._inlineTables_
            objectItem.setData(editExternally, ObjectDataEditExternallyRole)

            if self._inlineTables_:
                dataItem = objectItem.child(0, 0)
                dataItem.setData(qVariant(True), StandaloneEditorWidgetRole)
                objectItem.setData(qVariant(1), ObjectChildrenCountRole)

            else:
                objectItem.setData(qVariant(0), ObjectChildrenCountRole)

        else:
            nChildren = len(objectNode.objectInfo.children)
            objectItem.setRowCount(nChildren)
            objectItem.setData(qVariant(nChildren), ObjectChildrenCountRole)

        typeName = objectNode.objectInfo.objType.__name__
        objectTypeItem.setData(typeName, QtCore.Qt.DisplayRole)
        objectTypeItem.setData(qVariant(0), ObjectChildrenCountRole)

        if isinstance(objectNode.data, pathlib.Path):
            if __has_PySide6__:
                objectInfoValueItem.setData(objectNode.data, ObjectDataRole) # expects Node payload
                objectInfoValueItem.setData(objectNode.objectInfo.objInfo, QtCore.Qt.EditRole)

            else:
                objectInfoValueItem.setData(objectNode.data, QtCore.Qt.EditRole) # expects Node payload
        else:
            objectInfoValueItem.setData(objectNode.objectInfo.objInfo, QtCore.Qt.EditRole)
            objectInfoValueItem.setData(objectNode.objectInfo.choices, DataChoicesRole)
            objectInfoValueItem.setData(qVariant(0), ObjectChildrenCountRole)

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

        indexes = []

        for itm in (objectItem, objectTypeItem, objectInfoValueItem):
            itm.setData(readOnly, ReadOnlyRole) # star import from gui.itemmodels.roles
            itm.setData(readOnlyChildren, ReadOnlyChildrenRole) # star import from gui.itemmodels.roles
            if itm.column() == 2:
                if readOnly or (
                                    (
                                        objectNode.objectInfo.indirect is True
                                        or objectNode.objectInfo.objDataAsChild is True
                                    )
                                    and len(objectNode.objectInfo.choices) == 0
                                ):
                    itm.setData(readOnlyBrush, QtCore.Qt.ForegroundRole)
                    itm.setData(readOnlyFont, QtCore.Qt.FontRole)
                    itm.setFlags(readOnlyFlags)

                else:
                    itm.setData(brush, QtCore.Qt.ForegroundRole)
                    itm.setData(font, QtCore.Qt.FontRole)
                    itm.setFlags(flags)
            else:
                # prohibit editing in columns 0 and 1
                itm.setData(brush, QtCore.Qt.ForegroundRole)
                itm.setData(font, QtCore.Qt.FontRole)
                itm.setFlags(readOnlyFlags)

            index = self.indexFromItem(itm)
            assert(index.isValid()), f"Invalid index for item {itm.data(QtCore.Qt.DisplayRole)} at {itm.row()}, {itm.column()}"
            indexes.append(index)

        self.dataChanged.emit(indexes[0], indexes[-1])

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

        objectItem.setData(qVariant(objectNode), ObjectDataRole) ## how about this !?
        objectItem.setData(qVariant(objectNode.objectInfo), ObjectInfoRole) ## how about this !?
        # objectItem.setData(qVariant(objectNode.data), QtCore.Qt.EditRole)
        # if objectNode.objectInfo.objKeyType is not str:
        #     objectItem.setData(f"'{objectNode.objectInfo.name}'", QtCore.Qt.DisplayRole)
        # else:
        #     objectItem.setData(objectNode.objectInfo.name, QtCore.Qt.DisplayRole)
        objectItem.setData(objectNode.objectInfo.name, QtCore.Qt.DisplayRole)

        objectItemTip = f"Key type: {objectNode.objectInfo.objKeyType.__name__} -> {objectNode.objectInfo.objTip} object"
        objectItem.setData(objectItemTip, QtCore.Qt.ToolTipRole)

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

        try:
            objectInfoValueItem = QtGui.QStandardItem(objectNode.objectInfo.objInfo)

        except: #noqa
            traceback.print_exc()
            objectInfoValueItem = QtGui.QStandardItem(objectNode.tag)

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
        # readOnlyBrush = palette.brush(QtGui.QPalette.Disabled, QtGui.QPalette.Text)

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
                    ):
        # print(f"{self.__class__.__name__}.populateModel({type(obj)}, rootTitle: {rootTitle})")
        # print(f"\n\t-> call self.clear()")
        # ### BEGIN WARNING: 2026-06-28 11:43:14
        # this calls beginResetModel() ... endResetModel() already,
        # therefore it MUST NOT follow an isolated call to beginResetModel
        # ### END   WARNING: 2026-06-28 11:43:14
        # print(f"\n\t-> call self.beginResetModel()")

        self.clear()

        # self._visited_.clear()
        # self._hideRoot_ = hideRoot is True
        self._introspect_ = introspect is True
        self._predicate_ = predicate
        self._showPrivate_ = showPrivate is True
        self._showCallables_ = callables is True
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
                                           readOnlyChildren = self._readOnly_,
                                           objKey=self._rootTitle_,
                                           objKeyType=type(self._rootTitle_))

        self._tree_.add_node(self._rootNode_)
        # print(f"\n\t-> assign to self._modelData_")
        self._modelData_ = self._rootNode_.data

        self.beginResetModel()
        rowItems = self._makeRowForNode_(self._rootNode_)

        rootItem = self.invisibleRootItem()
        rootItem.setRowCount(1)
        rootItem.setColumnCount(3)

        for ki, item in enumerate(rowItems):
            rootItem.setChild(0, ki, item)

        self._topObjectItem_ = rowItems[0]

        # line below needed because beginResetModel() was called
        self.setHorizontalHeaderLabels(["Object", "Type", "Information or Value"])

        self.setRowCount(1) #objDict["nChildren"])

        self.endResetModel()

    @property
    def showCallables(self) -> bool:
        return self._showCallables_

    @showCallables.setter
    def showCallables(self, val:bool):
        # print(f"{self.__class__.__name__}.showCallables({val})")
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
    def predicate(self) -> types.FunctionType | None:
        return self._predicate_

    @predicate.setter
    def predicate(self, value: types.FunctionType | None):
        self._predicate_ = value

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

    # def itemChildren(self: typing.Self,
    #                  item: QtGui.QStandardItem) -> list:
    #     if not item.hasChildren():
    #         return []
    #
    #     return [item.child(k, 0) for k in range(item.rowCount())]
        # return list(map(lambda k: item.child(k, 0), range(item.rowCount())))


    def getDataObjectForLeaf(self, leaf: QtCore.QModelIndex | QtGui.QStandardItem,
                             byPath: bool = False) -> object:
        if byPath:
            path = self._getPathForItemOrIndex_(leaf)
            path[-1] = "self._modelData_"
            accessExpr = "".join(list(reversed(path)))
            return eval(accessExpr)

        if isinstance(leaf, QtCore.QModelIndex):
            item = self.itemFromIndex(leaf)

        else:
            item = leaf

        node = item.data(ObjectDataRole)
        return node.data

    # def data(self, index = QtCore.QModelIndex, role: QtCore.Qt.ItemDataRole = QtCore.Qt.DisplayRole):
    #     if self._modelData_ is None:
    #         return qVariant()
    #
    #     if role in (QtCore.Qt.EditRole, ObjectDataRole):
    #         item = self.itemFromIndex(index)
    #
    #         if item.column() == 2 and role == ObjectDataRole:
    #             # make sure we work on the sibling in column 0
    #             parentItem = item.parent()
    #             if not parentItem:
    #                 return qVariant()
    #
    #             item = parentItem.child(item.row(), 0)
    #
    #         if role == QtCore.Qt.EditRole:
    #             return item.data(role)
    #
    #         node = item.data(ObjectDataRole)
    #
    #         return qVariant(node.data)
    #
    #     return super().data(index, role)

    def getMasterItem(self, item: QtGui.QStandardItem):
        if item.column() == 0:
            return item

        parentItem = item.parent()
        if parentItem:
            return parentItem.child(item.row(), 0)

    def getItemSibling(self, item: QtGui.QStandardItem, column: int) -> QtGui.QStandardItem | None:
        index = self.indexFromItem(item)
        if not index.isValid():
            return

        sibling = index.sibling(index.row(), column)

        if sibling.isValid():
            return self.itemFromIndex(sibling)

    def getMasterIndex(self, index: QtCore.QModelIndex) -> QtCore.QModelIndex:
        r"""The "master" index is the one in column 0, and associates the node with payload"""
        if not index.isValid():
            return QtCore.QModelIndex() # invalid index

        return index.sibling(index.row(), 0)

    def setData(self: typing.Self, modelIndex: QtCore.QModelIndex,
                value: object, role = QtCore.Qt.EditRole) -> bool:
        # print(f"{self.__class__.__name__}.setData({modelIndex}, {value}, {role})")
        if self._modelData_ is None:
            return False

        item = self.itemFromIndex(modelIndex)

        if role in (ObjectDataRole, QtCore.Qt.EditRole):
            if item.column() != 0:
                parentItem = item.parent()
                if not parentItem:
                    return False
                item = parentItem.child(item.row(), 0)

            node = item.data(ObjectDataRole)

            if item.data(ReadOnlyRole) is True or node is None or node.objectInfo.readOnly:
                return

            originalObjectInfo = node.objectInfo

            # NOTE: 2026-09-26 10:33:25
            # find nodes that share this object info - they point to references
            # to the original dataChanged
            # these do not exist unless  their parent node was expanded
            # sharedNodes = list(self.tree.filter_nodes(
            #     lambda n: n.objectInfo == originalObjectInfo and n != node))

            path = self._getPathForItemOrIndex_(item)
            # I think this should always be so
            path[-1] = "self._modelData_"

            accexpr = "".join(reversed(path))
            setexpr = accexpr + " = value"
            OK = False
            try:
                # print(f"{self.__class__.__name__}.setData: setexpr = {setexpr}")
                exec(setexpr) # noqa
                newVal = eval(accexpr)
                objectInfo = onode.parseObject(newVal, node.tag,
                                            introspect=self.showIntrospection,
                                            predicate=self.predicate,
                                            includePrivate=self.showPrivateMembers,
                                            includeCallables=self.showCallables,
                                            includeTypeMembers=not self.showValuesOnly,
                                            choices=node.objectInfo.choices,
                                            readOnly=self.readOnly,
                                            readOnlyChildren=self.readOnlyChildren,
                                            objKey=node.objectInfo.objKey,
                                            objKeyType=node.objectInfo.objKeyType)

                node.objectInfo = objectInfo
                node.data = newVal
                self._updateRowForNode_(item, node)
                self.dataChanged.emit(modelIndex, modelIndex)

                for sharedItem in filter(lambda i: i is not item,
                                      self.findItems("info", originalObjectInfo)):
                    sharedItemNode = sharedItem.data(ObjectDataRole)
                    sharedItemNode.objectInfo = objectInfo
                    sharedItemNode.data = newVal
                    self._updateRowForNode_(sharedItem, sharedItemNode)
                    sharedIndex = self.indexFromItem(sharedItem)
                    self.dataChanged.emit(sharedIndex, sharedIndex)

                OK = True
                self.sig_modelDataChanged.emit()

            except: # noqa
                traceback.print_exc()
                OK = False

            return OK

        else:
            try:
                item.setData(value, role)
                OK = True

            except: # noqa
                traceback.print_exc()
                OK = False

            return OK

    def getPathForLeaf(self: typing.Self,
                       leaf: QtCore.QModelIndex | QtGui.QStandardItem,
                       pathOnly: bool = False,
                       omitRoot: bool = False
                       ) -> str:
        r"""Returns the access path to the object behind the model index or item, as a string.
    Parameters:
    ===========
    :leaf: model index or item

    :pathOnly: when ``True``, returns the access path **up to** and *excluding** the object itself. Default is ``False``

    :omitRoot: when ``True``, returns the access path **excluding** the root object

    """
        path = self._getPathForItemOrIndex_(leaf)
        if len(path):
            if pathOnly:
                return "".join(list(reversed(path[1:])))
            elif omitRoot:
                return "".join(list(reversed(path[:-1])))
            return "".join(list(reversed(path)))
        return ""

    def _getParentNode_(self, item: QtGui.QStandardItem) -> ObjectNode | None:
        node = item.data(ObjectDataRole)

        if node.is_root():
            return

        parentNid = node.predecessor(self.tree.identifier)

        return self.tree.nodes[parentNid]

    def _getItemForNode(self, node: ObjectNode) -> QtGui.QStandardItem | None:
        if not isinstance(node, ObjectNode):
            raise TypeError(f"Expecting an ObjectNode; got a {type(node).__name__} instead")

        if not isinstance(self.tree, Tree):
            return

        if node.identifier not in self.tree:
            raise KeyError(f"Node with tag {node.tag} and identifier {node.identifier} does not exist")

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

        # ### BEGIN NOTE: 2026-02-10 12:22:40
        #
        # Code below only makes sense for items in column 0; however, when an
        # item on a higher column is passed, I need access to its sibling in
        # column 0
        if item.column() > 0:
            targetItem = self.getMasterItem(item)
            assert(targetItem is not None), f"Cannot get the targetItem for item {item.data(QtCore.Qt.DisplayRole)} at row {item.row()}, column {item.column()}"

        else:
            targetItem = item
        #
        # ### END   NOTE: 2026-02-10 12:22:40

        node = targetItem.data(ObjectDataRole)

        if node.identifier not in self.tree:
            return path

        if node==self.rootNode:
            path.append(node.tag)
            return path

        parentNode = None

        while node is not self.rootNode:
            parentNid = node.predecessor(self.tree.identifier)
            parentNode = self.tree.nodes[parentNid]
            parentAccess = parentNode.objectInfo.memberAccess
            bindingType = node.objectInfo.objKeyType
            objectBindingInParent = node.tag

            if len(parentAccess) == 1:
                path.append(f"{parentAccess[0]}{objectBindingInParent}")

            elif len(parentAccess) == 2:
                if bindingType is weakref.ReferenceType:
                    path.append(f"{parentAccess[0]}{objectBindingInParent}{parentAccess[1]}")

                else:
                    if bindingType is str:
                        oB = f"'{objectBindingInParent}'"
                    else:
                        try:
                            oB = bindingType(objectBindingInParent) # hedging my bets...
                        except: #noqa
                            oB = objectBindingInParent

                    path.append(f"{parentAccess[0]}{oB}{parentAccess[1]}")

            node = parentNode

        path.append(self.rootNode.tag)

        return path

    # NOTE: 2026-09-26 14:33:57
    # does not work from the "Qt side" when using the singledispatchmethod approach
    # @singledispatchmethod
    # def hasChildren(self, obj) -> bool:
    #     raise NotImplementedError()
    #
    # @hasChildren.register(QtCore.QModelIndex)
    def hasChildren(self, index:QtCore.QModelIndex) -> bool:
        # NOTE: 2026-09-10 12:06:10
        # the invisible root item has an invalid index (by default)
        # and calling self.itemFromIndex() on an invalid index returns None!
        item = self.itemFromIndex(index)
        if item:
            # return item.hasChildren()
            nChildren = item.data(ObjectChildrenCountRole)
            return isinstance(nChildren, int) and nChildren > 0

        elif index == self.invisibleRootItem().index():
            return self.invisibleRootItem().hasChildren()

        return False

    # NOTE: see NOTE: 2026-09-26 14:33:57
    # @hasChildren.register(QtGui.QStandardItem)
    # def _hasChildren_(self, item: QtGui.QStandardItem) -> bool:  # noqa: F811,RUF100
    #     return item.hasChildren()

    def _childrenOfItem_(self, item: QtGui.QStandardItem):
        r"""Generator for iterating through the existing child items.
    Reports the items in column 0 of the model.
    In this model, an item advertises its maximum number of children via the
    data associated with ObjectChildrenCountRole role. However, these children
    are displayed in the tree view ONLY when the item is expanded ("lazy loading").

    An item that has never been expanded since its creation, will therefore appear
    without any children even if item.hasChildren() is True, until the after the
    first time the item was expanded.


    """
        if isinstance(item, QtGui.QStandardItem):
            yield from (item.child(k, 0) for k in range(item.rowCount()))

    def findItems(self, property: str, value: object, mode: int = Tree.WIDTH):
        if property not in ("data", "info"):
            raise ValueError(f"Invalid property {property}; expected one of 'data' or 'info'")

        if property == "data":
            yield from filter(lambda i: i.data(ObjectDataRole).data is value,
                              self.objectItems(mode=mode))

        else:
            assert isinstance(value, ObjectInfo), f"When 'property' is 'info', value' is expected to be an ObjectInfo instance; instead got {type(value).__name__}"
            yield from filter(lambda i: i.data(ObjectInfoRole) == value,
                              self.objectItems(mode=mode))

    def objectItems(self, mode: int = Tree.WIDTH):
        r"""Iteates through the existing QStandardItem in the first column"""
        yield from self.filterObjectItems(mode=mode)

    def filterObjectItems(self, item: QtGui.QStandardItem | None = None, /,
                          mode: int = Tree.WIDTH,
                          filter: types.FunctionType | None = None):
        r"""Adapted from treelib.Tree.expand_tree(…)
    WARNING: filtering needs more work -- better apply a filter to the output of self.objectItems
    """
        #NOTE: this is too clever !
        # filter = (lambda x: True) if filter is None else filter
        # basicFilter = lambda x: isinstance(x, QtGui.QStandardItem)
        # filter = basicFilter if filter is None else (lambda x: basicFilter and filter(x))

        filter = (lambda x: True) if filter is None else filter
        # fltFn = (lambda x: isinstance(x, QtGui.QStandardItem)) if filter is None else (lambda x: isinstance(x, QtGui.QStandardItem) and filter(x))

        if not isinstance(item, QtGui.QStandardItem):
            item = self.topObjectItem

        if isinstance(item, QtGui.QStandardItem):
            if filter(item):
                yield item

            queue = [i for i in self._childrenOfItem_(item) if isinstance(i, QtGui.QStandardItem) and filter(i)]
            # queue = [i for i in self._childrenOfItem_(self.topObjectItem) if isinstance(i, QtGui.QStandardItem)]
            # queue = [i for i in self._childrenOfItem_(self.topObjectItem) if filter(i)]

            if mode in [Tree.WIDTH, Tree.DEPTH]:
                while(queue):
                    yield queue[0]
                    # expansion = [i for i in self._childrenOfItem_(queue[0]) if isinstance(i, QtGui.QStandardItem)]
                    expansion = [i for i in self._childrenOfItem_(queue[0]) if isinstance(i, QtGui.QStandardItem) and filter(i)]
                    # expansion = [i for i in self._childrenOfItem_(queue[0]) if filter(i)]

                    if mode is Tree.WIDTH:
                        queue = expansion + queue[1:]

                    elif mode is Tree.DEPTH:
                        queue = queue[1:] + expansion

            elif mode is Tree.ZIGZAG:
                stack_fw = []
                queue.reverse()
                stack = stack_bw = queue
                direction = False
                while stack:
                    # expansion = [i for i in self._childrenOfItem_(stack[0]) if isinstance(i, QtGui.QStandrdItem)]
                    expansion = [i for i in self._childrenOfItem_(stack[0]) if isinstance(i, QtGui.QStandrdItem) and filter(i)]
                    # expansion = [i for i in self._childrenOfItem_(stack[0]) if filter(i)]

                yield stack.pop(0)

                if direction:
                    expansion.reverse()
                    stack_bw = expansion + stack_bw
                else:
                    stack_fw = expansion + stack_fw

                if not stack:
                    direction = not direction
                    stack = stack_fw if direction else stack_bw

            else:
                raise ValueError(f"Unsupported traversal mode {mode}")


#     def canFetchMore(self, parent: QtCore.QModelIndex) -> bool:
#         if not parent.isValid():
#             return False
#
#         item = self.itemFromIndex(parent)
#         if item.hasChildren():

