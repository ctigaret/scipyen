# $Id: objectmodel.py $
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
# import functools
from functools import singledispatchmethod
from collections import deque, UserDict, OrderedDict
from dataclasses import MISSING
# import weakref
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
# ### END 3rd party modules

# from core.qtutils import qVariant #, QVariantType #, qVariants, fromQVariant, isQObjectAlive)
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

from gui.itemmodels.datatree.objectnode import (ObjectInfo, ObjectNode)

class ObjectModel(QtGui.QStandardItemModel):
    r"""FIXME/TODO Where possible, work with QStandardItem instead of QModelIndex!!!"""
    sig_rootPathChanged = Signal(name="sig_rootPathChanged") # -> rootPathChanged
    sig_objectLoaded = Signal(name="sig_objectLoaded") # -> directoryLoaded

    def __init__(self, parent: QtCore.QObject):
        super().__init__(0,3, parent=parent)
        self._nColumns_ = 3

        self._rootNode_ = objectnode.ObjectNode(dataclasses.MISSING,
                                                objectnode.ObjectInfo(name=""))

        # --- private model API ---
        self._setRootNode_: bool = False

    @singledispatchmethod
    def index(self, x, y, idx) -> QtCore.QModelIndex:
        raise NotImplementedError()

    @index.register(int)
    def _index_(self, row: int, column: int, parent: QtCore.QModelIndex) -> QtCore.QModelIndex:
        if (
            row < 0 or column < 0
            or row >= self.rowCount(parent)
            or column >= self.columnCount(parent)
            ):
            return QtCore.QModelIndex()

        parentNode = self.node(parent) if self.indexValid(parent) else self.rootNode # TODO

        i = self.translateVisibleLocation(parentNode, row)

        if i >= len(parentNode._visibleChildren_):
            return QtCore.QModelIndex()

        childName = parentNode._visibleChildren_[i]
        indexNode = parentNode.children[childName] # TODO

        # TODO/FIXME here I should deal with QStandardItem
        # so retrieve the QModelIndex via this emchanism (Python does not have
        # direct access to the "internal pointer" of the item or index)
        return super().sibling(row, column, index) # FIXME
        return self.createIndex(row, column, indexNode)  # FIXME switch to QStandardItem API

    @index.register(list)
    def _index_(self, path: list, column: int) -> QtCore.QModelIndex:  # noqa: F811
        # NOTE: 2026-09-16 23:15:05
        # see TODO: 2026-09-16 23:14:53 for why path needs to be a list
        node = self.node(path, False)
        return self.index(node, column) # TODO

    def sibling(self, row: int, colum: int, index: QtCore.QModelIndex) -> QtCore.QModelIndex:
        # FIXME: this is QModelIndex API -> won't work here, as QStandardItemModel does not provide this method
        # might even not be needed
        #
        if row == index.row() and column < self.columnCount(index.parent()):
            return super().sibling(row, column, index)
            # return self.createIndex(row, column, index.internalPointer()) # FIXME WILL CRAsH!


    def objectInfo(self, index: QtCore.QModelIndex) -> dict:
        return self.node(index).objectInfo() # TODO

    def columCount(self, parent: QtCore.QModelIndex) -> int:
        return 0 if parent.column() > 0 else self._nColumns_

    def rowCount(self, parent: QtCore.QModelIndex) -> int:
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            return len(self._root_._visibleChildren_) # TODO

        parentNode = self.node(parent) # TODO

        return len(parentNode._visibleChildren_) # TODO

    def canFetchMore(self, parent: QtCore.QModelIndex) -> bool:
        if not self._setRootPath_:
            return False

        indexNode = self.node(parent)
        return not indexNode._populatedChildren_ # TODO

    def fetchMore(self, parent: QtCore.QModelIndex):
        if not self._setRootPath_:
            return

        indexNode = self.node(parent) # TODO

        if indexNode._populatedChildren_:
            return

        indexNode._populatedChildren_ = True

        # TODO :
        # fileInfoGatherer -> self._objectParser_
        # filePath -> self.objectPath (method)
        self._objectParser_.list(self.objectPath(parent))

    def objectPath(self, index: QtCore.QModelIndex) -> str:
        pass

    def remove(self, index: QtCore.QModelIndex) -> bool: # TODO
        # NOTE: 2026-09-16 10:12:33 WARNING
        # block changing the structure of objects -> allow this only
        # for genuine dictionaries and SimpleNamespace objects
        fullPath = self.objectPath(index)
        node = self.node(index) # TODO

    @property
    def root(self) -> objectnode.ObjectNode:
        return self._rootNode_

    def setRootObject(self, obj, objName:str) -> QtCore.QModelIndex:
        if obj is dataclasses.MISSING:
            objName = ""

        self._rootNode_ = objectnode.ObjectNode(self._object_, objectnode.ObjectInfo(name=objName))

        # now, must populate the node

# ------ Private API ------

    @singledispatchmethod
    def node(self, obj, fetch:bool = False) -> objectnode.ObjectNode:
        r"""FINDS a node in the hierarchy"""
        raise NotImplementedError()

    @node.register(str)
    def _node_(self, objPath:tuple, fetch: bool = False) -> objectnode.ObjectNode:
        if len(objPath) == 0:
            return self._rootNode_

        if objPath in self._rootNode_.children:
            return self._rootNode_.children[objPath]

        # else:





        # if obj is dataclasses.MISSING:
        #     return objectnode.ObjectNode(obj, objectnode.ObjectInfo(name=""))

    @node.register(QtCore.QModelIndex)
    def _node_(self, index: QtCore.QModelIndex, _: bool = False) -> objectnode.ObjectNode:
        if not index.isValid():
            return self._rootNode_

        if index.column() > 0:
            index = index.siblingAtColumn(0)

        return index.data(ObjectNodeRole)

    @node.register(QtGui.QStandardItem)
    def _node_(self, item: QtGui.QStandardItem, _:bool=False) -> objectnode.ObjectNode:
        return self.node(self.indexFromItem(item))


    # @node.register(list)
    # def _node_(self, path:list, fetch: bool) -> objectnode.ObjectNode:  # noqa: F811
    #     # TODO: 2026-09-16 23:14:53
    #     # instead of a str, represent access path with a sequence of tuples
    #     # e.g. (member_access, member_name) where member_access is alsoa tuple, see datatreemodel
    #     if len(path) == 0:
    #         return self.root
    #
    #     index_ = QtCore.QModelIndex()
    #     parentNode = self.node(index_)
    #
    #     # TODO: finalize me


    def addNode(self, objectPath, objectInfo):
        node = objectnode.ObjectNode




