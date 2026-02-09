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
# import scipy
import pandas as pd
# import vigra
# ### END 3rd party modules

# import core.datatypes as datatypes
# from core.datatypes import (is_namedtuple, TypeEnum)

# NOTE: 2026-02-07 09:14:19 FIXME/TODO
# to break cycling dependencies in systems.PrairieView, which needs this for the
# importer gui, MOVE the latter to a separate module
# from systems.PrairieView import *

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

# from core.triggerprotocols import TriggerProtocol
# from core.triggerevent import (DataMark, TriggerEvent, TriggerEventType)

# import core.datasignal as datasignal
# from core.datasignal import (DataSignal, IrregularlySampledDataSignal)

# import core.datazone as datazone
# from core.datazone import (DataZone, Interval)

# from core import xmlutils, strutils

# from core import scipyen_quantities as scq

from core.workspacefunctions import (validate_varname, user_workspace)

# from core.utilities import (NestedFinder,
#                             get_nested_value, set_nested_value,
#                             unique)

# from core.prog import (safewrapper, safeguiwrapper, print_styled, qVariants,
#                        is_hashable)

# from core.traitcontainers import (DataBag, DataBagTraitsObserver,)

# from core.scipyendataclasses import isDataclass

# from gui.widgets.tablewidget import SimpleTableWidget
# from gui.widgets.tableeditorwidget import (TableEditorWidget,
#                                            TabularDataModel,)
from gui.pictgui import WorkerThread
# from gui.widgets.small_widgets import QuantitySpinBox, ComplexSpinBox
from gui.delegates import PythonItemDelegate
from gui.workspacegui import GuiMessages, WorkspaceGuiMixin
from gui.itemmodels.roles import *
from gui.itemmodels.datatreemodel import DataTreeModel

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

class DataTreeView(QtWidgets.QTreeView, WorkspaceGuiMixin):
    def __init__(self: typing.Self, *args, **kwargs):
        parent = kwargs.pop("parent", None)
        super().__init__(parent=parent)
        super().setModel(DataTreeModel())
        self._delegate_ = PythonItemDelegate()
        self._defaultDelegate_ = self.itemDelegate()

    def setModel(self: typing.Self, model: QtCore.QAbstractItemModel):
        # disallow changing the model
        pass

    def _setupChildDataItem_(self: typing.Self, item: QtGui.QStandardItem,
                             objData: typing.Optional[typing.Any] = None):
        r"""Sets up the editor widgets for the items in the tree model.
For a given item:
    * if the child first row child on column 0 represents a hierarchical data
        structure, it simply becomes is a new branch point, with children representing its elements or members
        (fields, attributes, etc)

    * else if the contains tabular data (essentially,
        pandas or numpy array object) then it will iself gain a child item in
        column 0 that uses a TableEditorWidget (by way of PythonItemDelegate)
        for read-write access to elements of the data.

    * if the

    """
        # NOTE: 2026-02-09 21:41:40
        # Python sequence, mappings, and set types are treated as hierarchical data
        # structures. Nevertheless, there is a case for accessing sequences via a
        # list data model/view couple - I should revisit this. For now, I use a
        # use hierarchical representation throughout, where sequences and sets are
        # first transformed to a mapping (index ↦ value)
        #
        if not self.model():
            return

        model = self.model()
        index = item.index()
        if objData is None:
            objData = item.data(ObjectDataRole)
        if index.column() == 0 and item.hasChildren():
            for row in range(item.rowCount()):
                childItem = item.child(row, 0)
                infoItem = item.child(row, 2)
                if row == 0:
                    hasEditorWidgetChild = childItem.data(StandaloneEditorWidgetRole)
                    if hasEditorWidgetChild is True:
                        childIndex = item.child(0).index()
                        self.setFirstColumnSpanned(0, index, True)
                        # self.setFirstColumnSpanned(0, childIndex, True)
                        editorWidget = self._delegate_.createWidget(objData,
                                                                    list(),
                                                                    False,
                                                                    self)
                        # if isinstance(editorWidget, TableEditorWidget):
                        #     editorWidget.model.dataChanged.connect
                        # editorWidget.setData(objData)
                        self.setIndexWidget(childIndex, editorWidget)
                        flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable
                        item.child(0).setFlags(flags)

                self._setupChildDataItem_(childItem)
                if infoItem:
                    self._setupChildDataItem_(infoItem, objData)

        elif index.column() == 2:
            print(f"{self.__class__.__name__}._setupChildDataItem_: index row {index.row()}, column {index.column}, data {index.data(ObjectDataRole)}")
            # index = infoItem.index()
            row = index.row()
            infoItem = model.itemFromIndex(index)
            choices = infoItem.data(DataChoicesRole)
            # editorWidget = self._delegate_.createWidget(objData,
            #                                             choices,
            #                                             False,
            #                                             self)
            # self.setIndexWidget(index, editorWidget)
            #
            #
            self.setItemDelegateForColumn(index.column(), self._delegate_)
            self.setItemDelegateForRow(row, self._delegate_)
            flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable
            infoItem.setFlags(flags)


    def setData(self: typing.Self, obj: object,
                name: typing.Optional[str] = None):
        model = self.model()
        model.setModelData(obj, name)
        root = model.invisibleRootItem()
        if root.hasChildren():
            # NOTE: 2026-02-08 15:23:06
            # there is exactly one of these and it is the visible "root" of the
            # tree; all of objects "internals" are child rows of it.
            objItem = root.child(0,0)
            self._setupChildDataItem_(objItem)

    @property
    def readOnly(self: typing.Self) -> bool:
        return self._readOnly_

    @readOnly.setter
    def readOnly(self: typing.Self, val: bool):
        self._readOnly_ = val is True
        # TODO: 2026-02-09 12:50:43
        # set all editors in column 1 to readOnly
        # set all delegates in column 2 to readOnly
        # WARNING: delegates are handled by the viewer owner of this model!



