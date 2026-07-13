# -*- coding: utf-8 -*-
# $Id: datatreeeditor.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
New data viewer widget, based on datatreemodel
"""
from __future__ import print_function

import os, sys
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
from core import prog
from core.prog import safewrapper
from core import strutils

from gui.delegates import PythonItemDelegate
from gui.workspacegui import WorkspaceGuiMixin
from gui.itemmodels.roles import * #noqa
from gui.itemmodels.datatreemodel import DataTreeModel
from gui import quickdialog

if "darwin" in sys.platform:
    altKeyDescr = "<Option>"
    ctrlKeyDescr = "<Command>"
else:
    altKeyDescr = "<ALT>"
    ctrlKeyDescr = "<CTRL>"

class DataTreeView(QtWidgets.QTreeView, WorkspaceGuiMixin):
    sig_itemDoubleClicked = Signal(QtGui.QStandardItem, name="sig_itemDoubleClicked")
    sig_dataChanged = Signal(QtCore.QModelIndex, QtCore.QModelIndex, name="sig_dataChanged")
    sig_modelDataChanged = Signal(name = "sig_modelDataChanged")
    def __init__(self: typing.Self, *args, **kwargs):
        # print(f"{self.__class__.__name__}.__init__")
        parent = kwargs.pop("parent", None)
        super().__init__(parent=parent)
        WorkspaceGuiMixin.__init__(self, parent=parent)

        self._readOnly_ = False
        self._defaultEditTriggers_ = self.editTriggers()

        initialExpandDepth = kwargs.pop("initialExpandDepth", 1)
        self._showCallables_: bool = kwargs.get("showCallables", False)
        self._showValuesOnly_: bool = kwargs.get("showValuesOnly", True)

        assert isinstance(initialExpandDepth, int) and initialExpandDepth >=0, f"Invalid value for 'initialExpandDepth': expecting an int >=0 ; got {initialExpandDepth} instead"
        self._initialExpandDepth_: int = initialExpandDepth

        autoResizeColumns = kwargs.pop("autoResizeColumns", {0,1})
        assert (isinstance(autoResizeColumns, set) and all((isinstance(v, int) and v in range(3)) for v in autoResizeColumns)), f"Invalid value for 'autoResizeColumns'; expecting a set of ints, each in range(3); instead, got {autoResizeColumns}"
        self.autoResizeColumns: set[int] = kwargs.pop("autoResizeColumns", set())

        # self._alwaysSortRows_: bool = False

        # NOTE: 2026-03-31 22:47:04
        self.setTextElideMode(QtCore.Qt.ElideMiddle)

        # NOTE: 2026-04-01 10:41:46
        self.setExpandsOnDoubleClick(False)
        # print(f"\n\t-> initialising sourceModel")
        self.sourceModel = DataTreeModel(showMethods = self._showCallables_,
                                       valuesOnly = self._showValuesOnly_,
                                       parent=self)

        self.sourceModel.dataChanged.connect(self.sig_dataChanged)
        if hasattr(self.sourceModel, "sig_modelDataChanged"):
            self.sourceModel.sig_modelDataChanged.connect(self.sig_modelDataChanged)

        self.proxyModel = QtCore.QSortFilterProxyModel(self)
        self.proxyModel.setSourceModel(self.sourceModel)

        super().setModel(self.proxyModel)
        self.setSortingEnabled(True)

        self._defaultDelegate_ = self.itemDelegate()
        self._delegate_ = PythonItemDelegate(parent = self)
        self._dragStartPosition_: typing.Optional[QtCore.QPoint] = None

        self._currentExpansionDepth_: int = 0

        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        # TODO implement dragging from here to the workspace
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        self.setDragEnabled(True)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested[QtCore.QPoint].connect(
            self.slot_customContextMenuRequested
            )

        self.sig_itemDoubleClicked[QtGui.QStandardItem].connect(self.slot_itemDoubleClicked)
        self.expanded.connect(self._slot_indexExpanded)
        self.collapsed.connect(self._slot_indexCollapsed)

        self.setAlternatingRowColors(True)
        self.setItemDelegate(self._delegate_)

        self._scipyenMainWindow_ = self._scipyenWindow_

        if self._scipyenMainWindow_ is None:
            allWindows = list(
                            filter(
                                    lambda w: "ScipyenWindow" in type(w).__name__,
                                    QtWidgets.QApplication.topLevelWidgets()
                                    )
                            )
            if len(allWindows):
                self._scipyenMainWindow_ = allWindows[0]

    @property
    def initialExpandDepth(self) -> int:
        return self._initialExpandDepth_

    @initialExpandDepth.setter
    def initialExpandDepth(self, val:int):
        assert isinstance(val, int) and val >= 0, f"Invalid value for 'initialExpandDepth': expecting an int >=0 ; got {val} instead"
        self._initialExpandDepth_ = val

    @property
    def currentExpansionDepth(self) -> int:
        return self._currentExpansionDepth_

    @safewrapper
    def _exportPathsToClipboard_(self, item_paths):
        if self._scipyenMainWindow_ is None:
            return

        if len(item_paths) > 1:
            if bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier):
                QtWidgets.QApplication.clipboard().setText(",\n".join(["""%s""" % i for i in item_paths]))
                # self._scipyenMainWindow_.app.clipboard().setText(",\n".join(["""%s""" % i for i in item_paths]))
            else:
                QtWidgets.QApplication.clipboard().setText(", ".join(["""%s""" % i for i in item_paths]))
                # self._scipyenMainWindow_.app.clipboard().setText(", ".join(["""%s""" % i for i in item_paths]))

        elif len(item_paths) == 1:
            QtWidgets.QApplication.clipboard().setText(item_paths[0])
            # self._scipyenMainWindow_.app.clipboard().setText(item_paths[0])

    def _editExternally_(self, obj:object, name:str, askForParams:bool):
        from gui.mainwindow import VTH
        # print(f"{self.__class__.__name__}._editExternally_({type(obj).__name__}, {name}, {askForParams})")
        # if "ScipyenWindow" not in type(self.scipyenMainWindow).__name__:
        if self._scipyenMainWindow_ is None:
            return

        handler_specs = VTH.get_handler_spec(type(obj))

        tableEdit = list(filter(lambda x: "TableEditor" in x, handler_specs))
        dataTreeEdit = list(filter(lambda x: "DataTreeViewer" in x, handler_specs))
        textEdit = list(filter(lambda x: "TextViewer" in x, handler_specs))

        winType = None

        if len(tableEdit) == 1:
            winType = tableEdit[0][0]

        elif len(dataTreeEdit) == 1:
            winType = dataTreeEdit[0][0]

        elif len(textEdit) == 1:
            winType = textEdit[0][0]

        # print(f"\twinType = {winType}")

        if winType:
            if not self._scipyenMainWindow_.viewObject(obj, name, winType=winType,
                                    newWindow=True,
                                    askForParams=askForParams):
                self._showInConsole_(obj)

    @Slot()
    @safewrapper
    def slot_expandAll(self):
        self.expandAll()
        self.resizeColumnToContents(0)

    @Slot(QtGui.QStandardItem)
    def slot_itemDoubleClicked(self: typing.Self, item:QtGui.QStandardItem):
        from gui.datatreeviewer import DataTreeViewer
        askForParams = bool(
            QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier)

        if not self.model:
            return

        if item.column() == 0:
            readOnly = item.data(ReadOnlyRole) is True # noqa
            obj = self.sourceModel.getDataObjectForLeaf(item)
            if obj is None:
                return
            name = item.data(QtCore.Qt.DisplayRole)
            if item.data(ObjectDataEditExternallyRole) is True: # noqa
                self._editExternally_(obj, name, askForParams)

            else:
                self.readOnly = readOnly
                if isinstance(self.parent(), DataTreeViewer):
                    self.parent().view(obj, doc_title = name)
                else:
                    self._showInConsole_(obj)

    @Slot()
    @safewrapper
    def slot_copyPaths(self: typing.Self):
        if self._scipyenMainWindow_ is None:
            return

        item_paths = self.getSelectedPaths()
        self._exportPathsToClipboard_(item_paths)

    @Slot()
    def slot_exportToConsole(self: typing.Self):
        if self._scipyenMainWindow_ is None:
            return

        item_paths = self.getSelectedPaths()
        self._exportPathsToClipboard_(item_paths)
        self._scipyenMainWindow_.console.paste()

    @Slot()
    @safewrapper
    def slot_resizeFitColumns(self):
        for col in range(self.model.columnCount()):
            self.resizeColumnToContents(col)

    @Slot(QtCore.QModelIndex)
    def _slot_indexExpanded(self, index: QtCore.QModelIndex):
        # print(f"{self.__class__.__name__}._slot_indexExpanded(index={index})")
        column = index.column()
        self.resizeColumnToContents(column)
        if column < (self.sourceModel.columnCount()-1):
            self.resizeColumnToContents(column+1)

        depth = 0
        parent = index
        while parent.isValid():
            depth += 1
            parent = parent.parent()

        # print(f"{self.__class__.__name__}._slot_indexExpanded -> epxansion depth = {depth}")

        if depth > self._currentExpansionDepth_:
            self._currentExpansionDepth_ = depth


        # print(f"{self.__class__.__name__}._slot_indexExpanded -> {type(item)}")

    @Slot(QtCore.QModelIndex)
    def _slot_indexCollapsed(self, index: QtCore.QModelIndex):
        column = index.column()
        self.resizeColumnToContents(column)
        if column < (self.sourceModel.columnCount()-1):
            self.resizeColumnToContents(column+1)

        depth = 0
        parent = index
        while parent.isValid():
            depth += 1
            parent = parent.parent()

        # print(f"{self.__class__.__name__}._slot_indexCollapsed -> depth = {depth}")
        if depth-1 > self._currentExpansionDepth_:
            self._currentExpansionDepth_ = depth-1


        # item = self.sourceModel.itemFromIndex(index)
    @Slot()
    @safewrapper
    def slot_collapseAll(self):
        sigBlock = QtCore.QSignalBlocker(self) # noqa
        self.collapseAll()

    @Slot(QtCore.QPoint)
    @safewrapper
    def slot_customContextMenuRequested(self, point):
        # print(f"{self.__class__.__name__}.slot_customContextMenuRequested")
        from gui.mainwindow import VTH

        # FIXME/TODO copy to system clipboard? - what mime type? JSON data?
        if self._scipyenMainWindow_ is None:
            return

        items = self.selectedItems()
        if len(items) == 0:
            return

        cm = QtWidgets.QMenu("Data operations", self)
        cm.setToolTipsVisible(True)

        copyItemData = cm.addAction("Send to workspace")
        _tip = "Create a reference in the workspace (press and hold SHIFT to assign full path as name)"
        copyItemData.setToolTip(_tip)
        copyItemData.setStatusTip(_tip)
        copyItemData.setWhatsThis("Binds the selected object to a new symbol in the workspace")
        copyItemData.triggered.connect(self.slot_exportToWorkspace)

        copyItemPath = cm.addAction("Copy path(s)")
        _tip = "Copy the access path to this object as a string, to system's clipboard."
        copyItemPath.triggered.connect(self.slot_copyPaths)
        copyItemPath.setToolTip(_tip)
        copyItemPath.setStatusTip(_tip)
        copyItemPath.setWhatsThis(_tip + " When more than one object is selected, the paths will be comma-separated. Press and hold CTRL to have each path on a separate line of text.")

        sendToConsole = cm.addAction("Send path(s) to console")
        _tip = "Write the access path to this object as a Python statement, ready to execute (press ENTER)."
        sendToConsole.triggered.connect(self.slot_exportToConsole)
        sendToConsole.setToolTip(_tip)
        sendToConsole.setStatusTip(_tip)
        sendToConsole.setWhatsThis(_tip + " When more than one object is selected, the paths will be comma-separated. Press and hold CTRL to have each path on a separate line of text.")

        # NOTE: 2025-05-28 13:28:36
        # to keep it simple, restrict the option viewing the selected item, to
        # the case where a single item is selected
        if len(items) == 1:
            names, objects =  self.exportDataForItems(items)
            if len(objects) == 0:
                return
            obj = objects[0]
            name = names[0]
            self._obj_to_view_ = (obj, name)

            viewItemData = cm.addAction("View/Edit")
            viewItemData.setToolTip(f"View using generic DataTreeViewer; press {altKeyDescr} to use a new viewer window; press {ctrlKeyDescr} to prompt for configuration dialog ")
            viewItemData.setStatusTip(f"View using generic DataTreeViewer; press {altKeyDescr} to use a new viewer window; press {ctrlKeyDescr} to prompt for configuration dialog ")
            viewItemData.setWhatsThis(f"View using generic DataTreeViewer; press {altKeyDescr} to use a new viewer window; press {ctrlKeyDescr} to prompt for configuration dialog ")
            viewItemData.triggered.connect(self.slot_viewItem)

            if not issubclass(type(obj), QtWidgets.QWidget):
                handler_specs = VTH.get_handler_spec(type(obj))
                if len(handler_specs):
                    specialViewMenu = cm.addMenu("View with")
                    for handler_spec in handler_specs:
                        action = specialViewMenu.addAction(handler_spec[1])
                        action.setToolTip(f"View using {handler_spec[1]}; press {altKeyDescr} to use a new viewer window; press {ctrlKeyDescr} to prompt for configuration dialog ")
                        action.setStatusTip(f"View using {handler_spec[1]}; press {altKeyDescr} to use a new viewer window; press {ctrlKeyDescr} to prompt for configuration dialog ")
                        action.setWhatsThis(f"View using {handler_spec[1]}; press {altKeyDescr} to use a new viewer window; press {ctrlKeyDescr} to prompt for configuration dialog ")
                        action.triggered.connect(self.slot_autoSelectViewer)

            cm.addSeparator()
            viewInConsoleAction = cm.addAction("Display in console")
            viewInConsoleAction.setToolTip("Display in console")
            viewInConsoleAction.setStatusTip("Display in console")
            viewInConsoleAction.setWhatsThis("Display in console")

            viewInConsoleAction.triggered.connect(
                self.slot_showInConsole)

        # TODO: 2022-10-11 13:45:44
        # use itemAt (point) to get the index of the item, then if index is in
        # the leaf column, check if the value is editable (and constraints)
        # • editable values are, POD types (numeric scalars, strings, bool)
        # if editable then enable this menu action
        # • contemplate editing of other data (elements in expanded lists,
        # expanded dicts, elements of numpy arrays and their subclasses)
        # editItemData = cm.addAction("Edit")
        # editItemData.setToolTip("Edit value")
        # editItemData.setStatusTip("Edit value")
        # editItemData.setWhatsThis("Edit value")
        # editItemData.tiggered.connect(self.slot_editItemData)

        cm.popup(self.mapToGlobal(point), copyItemData)

    @Slot()
    @safewrapper
    def slot_autoSelectViewer(self):
        from gui.mainwindow import VTH

        if "ScipyenWindow" not in type(self.scipyenWindow).__name__:
            return

        if len(self._obj_to_view_) < 2:
            return

        if self._obj_to_view_[0] is dataclasses.MISSING or len(self._obj_to_view_[1].strip()) == 0:
            return

        if len(self._obj_to_view_) == 3:
            newWindow = self._obj_to_view_[2] is True

        else:
            newWindow = bool(
                QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.AltModifier)

        if len(self._obj_to_view_) == 4:
            askForParams = self._obj_to_view_[3] is True

        else:
            askForParams = bool(
                QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier)

        variable, varname = self._obj_to_view_[:2]
        # newWindow = bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.AltModifier)
        # askForParams = bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier)
        #
        # variable, varname = self._obj_to_view_

        action = self.sender()
        actionName = action.text().replace("&", "")
        handler_specs = VTH.get_handler_spec(type(variable))
        # print(f"{self.__class__.__name__}.slot_autoSelectViewer: hanler_specs -> {handler_specs}")
        if len(handler_specs):
            viewers = [spec[0] for spec in handler_specs if spec[1] == actionName]

            if len(viewers):
                viewer = viewers[0]

                if not self.scipyenWindow.viewObject(variable, varname, winType=viewer,
                                       newWindow=newWindow,
                                       askForParams=askForParams):
                    self._showInConsole_(variable)
        else:
            self._showInConsole_(variable)

        self._obj_to_view_ = (dataclasses.MISSING, "")

    @Slot()
    @safewrapper
    def slot_showInConsole(self):
        if self.scipyenWindow is None or "ScipyenWindow" not in type(self.scipyenWindow).__name__:
            return

        if self._obj_to_view_[0] is dataclasses.MISSING or len(self._obj_to_view_[1].strip()) == 0:
            return

        variable, varname = self._obj_to_view_[:2]
        self._showInConsole_(variable)
        self._obj_to_view_ = (dataclasses.MISSING, "")

    @Slot()
    @safewrapper
    def slot_exportToWorkspace(self: typing.Self):
        fullPathAsName = bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier)

        if self._scipyenMainWindow_ is None:
            return

        items = self.selectedItems()

        if len(items) == 0:
            return

        names, objects  = self.exportDataForItems(items, fullPathAsName=fullPathAsName)

        if len(objects) == 1:
            dlg = quickdialog.QuickDialog(self, "Copy to workspace")
            labelString = "Warning: The current variable name starts with an underscore ('_'), and therefore it will be hidden in the workspace viewer."
            namePrompt = quickdialog.StringInput(dlg, "Data name:")
            namePrompt.valueChanged[str].connect(dlg._slot_valueChanged)
            namePrompt.variable.setClearButtonEnabled(True)
            namePrompt.variable.redoAvailable=True
            namePrompt.variable.undoAvailable=True
            hiddenWarningLabel = QtWidgets.QLabel(labelString, self)
            hiddenWarningLabel.setVisible(False)
            dlg.addCallback(lambda s: hiddenWarningLabel.setVisible(s.startswith("_")))
            dlg.addWidget(hiddenWarningLabel, 0, QtCore.Qt.AlignLeft)

            if strutils.isnumber(names[0][0]):
                namePrompt.setText(f"data_{names[0]}")
            else:
                namePrompt.setText(names[0])
            dlg.adjustSize()

            if dlg.exec() == QtWidgets.QDialog.Accepted:
                newVarName = namePrompt.text()

                self._scipyenMainWindow_.assignToWorkspace(newVarName, objects[0], check_name=False)

        else:
            for name, obj in zip(names, objects):
                self._scipyenMainWindow_.assignToWorkspace(name, obj, check_name=False)

    @Slot()
    @safewrapper
    def slot_viewItem(self: typing.Self):
        from gui.datatreeviewer import DataTreeViewer
        # from core.utilities import get_nested_value
        # print(f"{self.__class__.__name__}.slot_viewItem")
        # print(f"\t{self._obj_to_view_}")
        # if self.scipyenWindow is None or "ScipyenWindow" not in type(self.scipyenWindow).__name__:
        if self._scipyenMainWindow_ is None:
            return

        if len(self._obj_to_view_) < 2:
            return

        if self._obj_to_view_[0] is dataclasses.MISSING or len(self._obj_to_view_[1].strip()) == 0:
            return

        if len(self._obj_to_view_) == 3:
            newWindow = self._obj_to_view_[2] is True

        else:
            newWindow = bool(
                QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.AltModifier)

        if len(self._obj_to_view_) == 4:
            askForParams = self._obj_to_view_[3] is True

        else:
            askForParams = bool(
                QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier)

        variable, varname = self._obj_to_view_[:2]

        if newWindow:
            if not self._scipyenMainWindow_.viewObject(variable, varname, winType=self.__class__,
                                    newWindow=True,
                                    askForParams=askForParams):
                self._showInConsole_(variable)
        else:
            if isinstance(variable, tuple(self.viewer_for_types.keys())):
                if isinstance(self.parent(), DataTreeViewer):
                    self.parent().view(variable, doc_title = varname)
                else:
                    self._showInConsole_(variable)
            else:
                self._showInConsole_(variable)

        self._obj_to_view_ = (dataclasses.MISSING, "")

    def _showInConsole_(self, obj):
        # if "ScipyenWindow" not in type(self.scipyenWindow).__name__:
        if self._scipyenMainWindow_ is None:
            return

        try:
            # NOTE 2025-05-28 14:22:51
            # as the object may not exist in the workspace, it gets assigned
            # there first, under a special (hidden) name, executed, and finally
            # deleted (i.e. the special (hidden) symbol is removed from the
            # workspace)
            self._scipyenMainWindow_.assignToWorkspace("____", obj)
            self._scipyenMainWindow_.console.execute("____", interactive=False)
            self._scipyenMainWindow_.console.execute("del ____", hidden=True, interactive=False)
        except:
            traceback.print_exc()

    def setModel(self: typing.Self, model: QtCore.QAbstractItemModel):
        r"""Overrides QtCore.QAbstractItemModel.setModel() to disallow changing the model"""
        pass

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.sourceModel._modelData_ is None:
            painter = QtGui.QPainter(self.viewport())
            painter.save()
            col = self.palette().placeholderText().color()
            painter.setPen(col)
            fm = self.fontMetrics()
            elided_text = fm.elidedText(
                "No data", QtCore.Qt.ElideRight, self.viewport().width()
            )
            painter.drawText(self.viewport().rect(), QtCore.Qt.AlignCenter, elided_text)
            painter.restore()

    # @prog.timefunc
    def _setupChildDataItem_(self: typing.Self, item: QtGui.QStandardItem): #,
                             # objData: typing.Optional[typing.Any] = None):
        r"""Sets up the editor widgets for the items in the tree model.

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

        model = self.sourceModel
        # model = self.model()
        # index = item.index()
        objData = item.data(ObjectDataRole) # noqa
        objType = item.data(ObjectTypeRole) # noqa

        if item.column() == 0 and item.hasChildren():
            for row in range(item.rowCount()):
                childItem = item.child(row, 0)
                infoItem = item.child(row, 2)
                if row == 0:
                    hasEditorWidgetChild = childItem.data(StandaloneEditorWidgetRole) # noqa
                    if hasEditorWidgetChild is True:
                        flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable
                        # NOTE: 2026-04-01 11:03:24
                        # this sets the child in row 0 to span all columns
                        self.setFirstColumnSpanned(0, self.proxyModel.mapFromSource(item.index()), True)
                        # self.setFirstColumnSpanned(0, item.index(), True)

                        # self.setItemDelegateForColumn(childItem.column(), self._delegate_)
                        # self.setItemDelegateForRow(childItem.row(), self._delegate_)
                        childItem.setFlags(flags)

                        # childIndex = item.child(0).index()
                        # ### BEGIN 2026-04-01 10:52:25 Too slow, but working; DO NOT DELETE
                        #

                        if hasattr(model, "_inlineTables_") and model._inlineTables_:
                            # print(f"{self.__class__.__name__}._setupChildDataItem_ for _inlineTables_")
                            editorWidget = self._delegate_.createWidget(objData,
                                                                        choices = list(),
                                                                        inModel = False,
                                                                        parent = self)
                            # if self.model().readOnly or item.data(ReadOnlyRole) is True:
                            if model.readOnly or item.data(ReadOnlyRole) is True:
                                if hasattr(editorWidget,  "readOnly") and type(editorWidget).readOnly.__name__ == "property":
                                    editorWidget.readOnly = True
                                elif hasattr(editorWidget, "setReadOnly") and isinstance(type(editorWidget).setReadOnly, (types.FunctionType, types.MethodType)):
                                    editorWidget.setReadOnly(True)

                            self.setIndexWidget(self.proxyModel.mapFromSource(childItem.index()), editorWidget)
                            # self.setIndexWidget(childItem.index(), editorWidget)

                        # ### END   2026-04-01 10:52:25 Too slow, but working; DO NOT DELETE

                        continue

                self._setupChildDataItem_(childItem)

                if infoItem:
                    self._setupChildDataItem_(infoItem) #, objData)

        elif item.column() == 2:
            signalBlocker = QtCore.QSignalBlocker(self.model()) # noqa
            parentItem = item.parent()
            if parentItem:
                objItem = parentItem.child(item.row(), 0)
                objType = objItem.data(ObjectTypeRole) # noqa

    # @prog.timefunc
    def setData(self: typing.Self, obj: object,
                name: typing.Optional[str] = None,
                showPrivate: bool = False,
                valuesOnly: bool = True,
                inlineTables: bool = False,
                introspect: bool = False):
        # print(f"{self.__class__.__name__}.setData({type(obj)})")
        # signalBlocker = QtCore.QSignalBlocker(self.model()) #noqa
        # model = self.model()

        # print(f"\n\tcall self.sourceModel.beginResetModel()")
        # NOTE: 2026-06-28 11:51:12
        # I think I need these here to notify the viewer.
        self.sourceModel.beginResetModel()
        # print(f"\n\tcall self.sourceModel.endResetModel()")
        self.sourceModel.endResetModel()
        self.sourceModel.populateModel(obj, rootTitle=name,
                                       showPrivate=showPrivate,
                                       introspect=introspect,
                                       inlineTables=inlineTables,
                                       valuesOnly=valuesOnly)
        self.sourceModel.readOnly = self.readOnly
        if self.readOnly:
            self.setItemDelegate(self._defaultDelegate_)
            self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        else:
            self.setItemDelegate(self._delegate_)
            self.setEditTriggers(self._defaultEditTriggers_)

        # WARNING: 2026-06-28 11:45:39
        # DO NOT call begin/endResetMdoel on the proxyModel here
        # see also WARNING: 2026-06-28 11:43:14 in itemmodels.datatreemodel.DataTreeModel
        self.proxyModel.setSourceModel(self.sourceModel)

        root = self.sourceModel.invisibleRootItem()
        if root.hasChildren():
            # NOTE: 2026-02-08 15:23:06
            # there is exactly one of these and it is the visible "root" of the
            # tree; all of objects "internals" are child rows of it.
            objItem = root.child(0,0)
            self._setupChildDataItem_(objItem)
            if self._initialExpandDepth_ == 0 and self._currentExpansionDepth_ == 0:
                self.collapseAll()
            else:
                self.expandToDepth(max(self._initialExpandDepth_, self._currentExpansionDepth_-1))

            for col in self.autoResizeColumns:
                if col >=0 and col < 3:
                    self.resizeColumnToContents(col)

            # self.proxyModel.setDynamicSortFilter(False)
            # self.proxyModel.setSourceModel(self.sourceModel)
            self.proxyModel.sort(-1)
            # self.proxyModel.setDynamicSortFilter(True)

    def setRootName(self, value: str):
        # print(f"{self.__class__.__name__}.setRootName({value})")
        if not isinstance(value, str) or len(value.strip()) == 0:
            return
        self.sourceModel.beginResetModel()
        self.sourceModel.topObjectItem.setData(value, QtCore.Qt.DisplayRole)
        self.sourceModel.endResetModel()
        if self._initialExpandDepth_ == 0:
            self.collapseAll()
        else:
            self.expandToDepth(self._initialExpandDepth_)

        for col in self.autoResizeColumns:
            if col >=0 and col < 3:
                self.resizeColumnToContents(col)
        self.proxyModel.sort(-1)

    @property
    def hasData(self) -> bool:
        return self.sourceModel._modelData_ is not None
        # return self.model()._modelData_ is not None

    @property
    def data(self) -> object:
        return self.sourceModel._modelData_
        # return self.model()._modelData_

    @property
    def readOnly(self: typing.Self) -> bool:
        return self._readOnly_

    @readOnly.setter
    def readOnly(self: typing.Self, val: bool):
        self._readOnly_ = val is True
        # self.model().readonly = self._readOnly_
        if isinstance(self.sourceModel, DataTreeModel):
            self.sourceModel.readOnly = self._readOnly_
        if self._readOnly_:
            self.setItemDelegate(self._defaultDelegate_)
            self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        else:
            self.setItemDelegate(self._delegate_)
            self.setEditTriggers(self._defaultEditTriggers_)
        # TODO: 2026-02-09 12:50:43
        # set all editors in column 1 to readOnly
        # set all delegates in column 2 to readOnly
        # WARNING: delegates are handled by the viewer owner of this model!

    def selectedItems(self: typing.Self) -> typing.Sequence:
        return list(
                        filter(lambda i: i.column() == 0,
                               map(
                                   # lambda i: self.model().itemFromIndex(i),
                                   lambda i: self.sourceModel.itemFromIndex(self.proxyModel.mapToSource(i)),
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
                                    self.sourceModel.getDataObjectForLeaf(i)
                                    # self.model().getDataObjectForLeaf(i)
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

        l_getName = lambda i: self.sourceModel.getPathForLeaf(i) if fullPathAsName else i.data(QtCore.Qt.DisplayRole) # noqa
        # l_getName = lambda i: self.model().getPathForLeaf(i) if fullPathAsName else i.data(QtCore.Qt.DisplayRole) # noqa
        # l_getName = lambda i: self.sourceModel.getPathForLeaf(self.proxyModel.mapToSource(i)) if fullPathAsName else i.data(QtCore.Qt.DisplayRole) # noqa

        selection = list(
                        map(
                            lambda i: (
                                        l_getName(i),
                                        self.sourceModel.getDataObjectForLeaf(i)
                                        # self.sourceModel.getDataObjectForLeaf(self.proxyModel.maptoSource(i))
                                        # self.model().getDataObjectForLeaf(i)
                                        ),
                            list(
                                filter(
                                    (
                                        lambda i: i.column() == 0
                                        and not i.data(StandaloneEditorWidgetRole) # noqa
                                        # and not self.proxyModel.mapToSource(i).data(StandaloneEditorWidgetRole) # noqa
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
        if self._initialExpandDepth_ == 0:
            self.collapseAll()
        else:
            self.expandToDepth(self._initialExpandDepth_)
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
        showPrivate = what.get("showPrivate", False)
        valuesOnly = what.get("valuesOnly", True)
        inlineTables = what.get("inlineTables", False)
        introspect = what.get("introspect", False)

        self.setData(data, root_title, showPrivate, valuesOnly, inlineTables, introspect)

    def clear(self: typing.Self):
        # self.sourceModel.beginResetModel()
        self.sourceModel.clear()
        # self.sourceModel.endResetModel()

    def mouseDoubleClickEvent(self: typing.Self, evt: QtGui.QMouseEvent):
        pos = evt.position().toPoint()
        index = self.proxyModel.mapToSource(self.indexAt(pos))
        item = self.sourceModel.itemFromIndex(index)
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

