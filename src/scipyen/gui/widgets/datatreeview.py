# -*- coding: utf-8 -*-
# $Id: datatreeeditor.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
New data viewer widget, based on datatreemodel
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
import pickle
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

from core.workspacefunctions import (validate_varname, user_workspace)

from gui.delegates import PythonItemDelegate
from gui.workspacegui import WorkspaceGuiMixin
from gui.itemmodels.roles import * #noqa
from gui.itemmodels.datatreemodel import DataTreeModel

class DataTreeView(QtWidgets.QTreeView, WorkspaceGuiMixin):
    sig_itemDoubleClicked = Signal(QtGui.QStandardItem, name="sig_itemDoubleClicked")
    def __init__(self: typing.Self, *args, **kwargs):
        parent = kwargs.pop("parent", None)
        initialExpandDepth = kwargs.pop("initialExpandDepth", 1)

        assert (initialExpandDepth >=0 and initialExpandDepth < 3), f"Invalid value for 'initialExpandDepth': expecting an int >=0 and < 3; got {initialExpandDepth} instead"
        self.initialExpandDepth: int = kwargs.pop("initialExpandDepth", 1)

        autoResizeColumns = kwargs.pop("autoResizeColumns", {0,1})
        assert (isinstance(autoResizeColumns, set) and all((isinstance(v, int) and v in range(3)) for v in autoResizeColumns)), f"Invalid value for 'autoResizeColumns'; expecting a set of ints, each in range(3); instead, got {autoResizeColumns}"
        self.autoResizeColumns: set[int] = kwargs.pop("autoResizeColumns", set())
        super().__init__(parent=parent)
        super().setModel(DataTreeModel())
        self._defaultDelegate_ = self.itemDelegate()
        self._delegate_ = PythonItemDelegate(parent = self)
        self._dragStartPosition_: typing.Optional[QtCore.QPoint] = None

    def setModel(self: typing.Self, model: QtCore.QAbstractItemModel):
        # disallow changing the model
        pass

    def _setupChildDataItem_(self: typing.Self, item: QtGui.QStandardItem,
                             objData: typing.Optional[typing.Any] = None):
        r"""Sets up the editor widgets for the items in the tree model.
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
        objData = item.data(ObjectDataRole) # noqa
        objType = item.data(ObjectTypeRole) # noqa

        if index.column() == 0 and item.hasChildren():
            for row in range(item.rowCount()):
                childItem = item.child(row, 0)
                infoItem = item.child(row, 2)
                if row == 0:
                    hasEditorWidgetChild = childItem.data(StandaloneEditorWidgetRole) # noqa
                    if hasEditorWidgetChild is True:
                        childIndex = item.child(0).index()
                        self.setFirstColumnSpanned(0, index, True)
                        # self.setItemDelegateForColumn(childIndex.column(), self._delegate_)
                        # self.setItemDelegateForRow(childIndex.row(), self._delegate_)
                        editorWidget = self._delegate_.createWidget(objData,
                                                                    choices = list(),
                                                                    inModel = False,
                                                                    parent = self)
                        # if (
                        #     item.data(ReadOnlyRole) is True # noqa
                        #     or self.model().readOnly
                        #     ):
                        if self.model().readOnly:
                            if hasattr(editorWidget,  "readOnly"):
                                editorWidget.readOnly = True
                        self.setIndexWidget(childIndex, editorWidget)
                        flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable
                        item.child(0).setFlags(flags)

                self._setupChildDataItem_(childItem)

                if infoItem:
                    self._setupChildDataItem_(infoItem, objData)

        elif index.column() == 2:
            # print(f"{self.__class__.__name__}._setupChildDataItem_ for column 2")
            # print(f"\tindex display: {index.data(QtCore.Qt.DisplayRole)}")
            # print(f"\tindex object data {index.data(ObjectDataRole)}")
            # print(f"\tindex row {index.row()}")
            signalBlocker = QtCore.QSignalBlocker(self.model()) # noqa
            # index = infoItem.index()
            # row = index.row()
            infoItem = model.itemFromIndex(index)
            parentItem = infoItem.parent()
            if parentItem:
                objItem = parentItem.child(infoItem.row(), 0)
                objType = objItem.data(ObjectTypeRole) # noqa

            # NOTE: 2026-02-12 14:58:10
            # inhibit editing for immutable collections - e.g. tuple, for now
            parentType = parentItem.data(ObjectTypeRole) # noqa
            # TODO 2026-02-12 14:59:32 to expand in parentheses as needed
            # if (
            #     (
            #         parentType in (tuple, frozenset)
            #         or parentItem.data(ReadOnlyRole) is True # noqa
            #         or objItem.data(ReadOnlyRole) is True # noqa
            #         )
            #     or self.model().readOnly
            #     ):
            if (
                (
                    parentType in (tuple, frozenset)
                    or infoItem.data(ReadOnlyRole) is True # noqa
                    )
                or self.model().readOnly
                ):
                flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

            else:
                self.setItemDelegateForColumn(index.column(), self._delegate_)
                self.setItemDelegateForRow(index.row(), self._delegate_)
                flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable

            infoItem.setFlags(flags)

    def setData(self: typing.Self, obj: object,
                name: typing.Optional[str] = None):
        signalBlocker = QtCore.QSignalBlocker(self.model()) #noqa
        # model = self.model()
        self.model().clear()
        self.model().setModelData(obj, name)
        root = self.model().invisibleRootItem()
        if root.hasChildren():
            # NOTE: 2026-02-08 15:23:06
            # there is exactly one of these and it is the visible "root" of the
            # tree; all of objects "internals" are child rows of it.
            objItem = root.child(0,0)
            self._setupChildDataItem_(objItem)
            if self.initialExpandDepth == 0:
                self.collapseAll()
            else:
                self.expandToDepth(self.initialExpandDepth)
            for col in self.autoResizeColumns:
                if col >=0 and col < 3:
                    self.resizeColumnToContents(col)

    @property
    def hasData(self) -> bool:
        return self.model()._modelData_ is not None

    @property
    def data(self) -> object:
        return self.model()._modelData_

    @property
    def readOnly(self: typing.Self) -> bool:
        return self._readOnly_

    @readOnly.setter
    def readOnly(self: typing.Self, val: bool):
        self._readOnly_ = val is True
        self.model().readonly = self._readOnly_
        # TODO: 2026-02-09 12:50:43
        # set all editors in column 1 to readOnly
        # set all delegates in column 2 to readOnly
        # WARNING: delegates are handled by the viewer owner of this model!

    def selectedItems(self: typing.Self) -> typing.Sequence:
        return list(
                        filter(lambda i: i.column() == 0,
                               map(
                                   lambda i: self.model().itemFromIndex(i),
                                   self.selectedIndexes()
                                   )
                               )
                    )

    def getDataForItems(
        self: typing.Self,
        items: typing.Sequence[QtGui.QStandardItem] = list()
        ) -> tuple:

        names, objects = zip(
            *list(
                    map(
                        lambda i: (
                                    i.data(QtCore.Qt.DisplayRole),
                                    self.model().getDataObjectForLeaf(i)
                                    ),
                        list(
                            filter(
                                (
                                    lambda i: i.column() == 0
                                    and not i.data(StandaloneEditorWidgetRole) # noqa
                                ),
                                items
                                )
                            )
                        )
                    )
            )

        return names, objects

    def exportDataForItems(self: typing.Self,
                           items: typing.Sequence[QtGui.QStandardItem] = list(),
                           fullPathAsName: bool = False,
                           pathOnly: bool = False) -> tuple:

        if pathOnly:
            fullPathAsName = True

        # l_pathToStr = lambda s: s.replace(".", "_").replace("[", "_").replace("]", "_") is isinstance(s, str) else ""

        l_getName = lambda i: self.model().getPathForLeaf(i) if fullPathAsName else i.data(QtCore.Qt.DisplayRole) # noqa

        selection = list(
                        map(
                            lambda i: (
                                        l_getName(i),
                                        self.model().getDataObjectForLeaf(i)
                                        ),
                            list(
                                filter(
                                    (
                                        lambda i: i.column() == 0
                                        and not i.data(StandaloneEditorWidgetRole) # noqa
                                    ),
                                    items
                                    )
                                )
                            )
                        )

        if len(selection):
            names, objects = zip(*selection)
        else:
            names = list()
            objects = list()

        if pathOnly:
            return names

        return names, objects

    def getSelectedPaths(self: typing.Self) -> typing.Sequence:
        items = self.selectedItems()
        if len(items) == 0:
            return list()

        return self.exportDataForItems(items, pathOnly = True)

    def update(self):
        super().update()
        if self.initialExpandDepth == 0:
            self.collapseAll()
        else:
            self.expandToDepth(self.initialExpandDepth)
        for col in self.autoResizeColumns:
            if col >=0 and col < 3:
                self.resizeColumnToContents(col)


    @Slot(object)
    def slot_setData(self: typing.Self, what: dict):
        r"""Preferred way to set the data in this viewer asynchronously.
    Parameters:
    ===========
    :what: a mapping
        "data"          ↦ the object to be represented in the hierarchical tree model
        "root-title"    ↦ the name (symbol) to appear as the "trunk" of the tree, to which the "data" is bound
                            When not a string, or when it is an empty string,
                            this symbol will be "/"
        "readOnly"      ↦ disable changing the values associated with the ``data``'s members

    """
        data = what.get("data", None)
        root_title = what.get("root_title", "")
        self.readOnly = what.get("readOnly", False)
        self.setData(data, root_title)

    def clear(self: typing.Self):
        self.model().clear()

    def mouseDoubleClickEvent(self: typing.Self, evt: QtGui.QMouseEvent):
        pos = evt.position().toPoint()
        index = self.indexAt(pos)
        item = self.model().itemFromIndex(index)
        if item.column() == 0:
            self.sig_itemDoubleClicked.emit(item)
        super().mouseDoubleClickEvent(evt)
        evt.setAccepted(True)

    def mousePressEvent(self: typing.Self, evt: QtGui.QMouseEvent):
        if evt.button() == QtCore.Qt.LeftButton:
            self._dragStartPosition_ = evt.pos()

        super().mousePressEvent(evt)
        evt.setAccepted(True)

    def mouseMoveEvent(self: typing.Self, evt: QtGui.QMouseEvent):
        # TODO: 2026-02-13 00:34:07 FINALIZE ME
        if evt.buttons() & QtCore.Qt.LeftButton:
            if isinstance(self._dragStartPosition_, QtCore.QPoint):
                items = self.selectedItems()
                if (
                    len(items)
                    and
                    (evt.pos() - self._dragStartPosition_).manhattanLength() >=  QtWidgets.QApplication.startDragDistance()
                    ):
                    drag = QtGui.QDrag(self)
                    mimeData = QtCore.QMimeData()

