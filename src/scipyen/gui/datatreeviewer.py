# -*- coding: utf-8 -*-
# $Id: ${datatreeviewer} $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later


r"""
Qt-based viewer window for dict and subclasses.

Replaces DataViewer
"""

# TODO: 2026-02-09 12:45:17 FIXME
# CLEAR UP THE IMPORTS AND OTHER STUFF COPIED OVER FROM DATAVIEWER

#### BEGIN core python modules
from __future__ import print_function

import os, sys, warnings, types, traceback, itertools, inspect
import typing, dataclasses, numbers
#### END core python modules

#### BEGIN 3rd party modules
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
import pandas as pd
import vigra
#### END 3rd party modules

#### BEGIN pict.core modules
import core.datatypes

import imaging.axiscalibration
from imaging.axiscalibration import AxesCalibration

import imaging.scandata
from imaging.scandata import (ScanData, AnalysisUnit)

from core.triggerprotocols import TriggerProtocol
from core.triggerevent import (TriggerEvent, TriggerEventType)

import core.datasignal
from core.datasignal import (DataSignal, IrregularlySampledDataSignal)

from core import xmlutils, strutils

from core.workspacefunctions import validate_varname

from core.utilities import NestedFinder

from core.prog import (safewrapper, safeguiwrapper, scipywarn)

from core.traitcontainers import (DataBag, DataBagTraitsObserver,)
from core.scipyendataclasses import ScipyenDataclass
from core.scipyen_config import markConfigurable

#### END pict.core modules

#### BEGIN pict.gui modules
# from gui.tableeditor import (TableEditorWidget, TabularDataModel,)

# from gui.widgets.interactivetreewidget import InteractiveTreeWidget
# from gui.widgets.tablewidget import SimpleTableWidget
# from gui.widgets.tableeditorwidget import (TableEditorWidget, TabularDataModel)
from gui.scipyenviewer import ScipyenViewer #, ScipyenFrameViewer
from gui import quickdialog
from gui.pictgui import WorkerThread
from gui.widgets.datatreeview import DataTreeView
from gui.itemmodels.roles import *


# from . import resources_rc
# from . import icons_rc
#### END pict.gui modules

if "darwin" in sys.platform:
    altKeyDescr = "<Option>"
    ctrlKeyDescr = "<Command>"
else:
    altKeyDescr = "<ALT>"
    ctrlKeyDescr = "<CTRL>"



# NOTE: 2022-12-25 23:08:51
# needed for the new plugins framework
# This plugins does not install a custom menu, but DOES provide a viewer type
# hence we flag it using __scipyen_plugin__ (we could have defined
# init_scipyen_plugin instead, to return an empty dict)
__scipyen_plugin__ = None

class DataTreeViewer(ScipyenViewer):
    r"""Replacement for DataViewer.
A lot of things copied from there, EXCEPT that it now uses
``DataTreeview`` and ``DataTreeModel`` from ``gui.widgets.datareeview`` module.
"""
    sig_activated = Signal(int)
    closeMe  = Signal(int)
    signal_window_will_close = Signal()
    _sig_setTreeViewData_ = Signal(dict, name="_sig_setTreeViewData_")

    # NOTE: 2022-11-20 22:09:07
    # reserved for future developmet of editing capabilities TODO
    sig_dataChanged = Signal(name = "sig_dataChanged")

    # TODO: 2019-11-01 22:44:34
    # implement viewing of other data structures (e.g., viewing their __dict__
    # for the generic case, )
    viewer_for_types = {dict:99,
                        list:99,
                        tuple:99,
                        types.TracebackType:99,
                        pd.DataFrame:0,
                        pd.Series:0,
                        pd.Index:0,
                        neo.core.dataobject.DataObject:0,
                        pq.Quantity:0,
                        np.ndarray:0,
                        AnalysisUnit:0,
                        AxesCalibration:0,
                        # neo.core.baseneo.BaseNeo:0,
                        ScanData:0,
                        TriggerProtocol:0,
                        types.SimpleNamespace:0,
                        ScipyenDataclass:0}

    def __init__(self, data: typing.Optional[object] = None,
                 parent: typing.Optional[QtWidgets.QMainWindow] = None,
                 ID: typing.Optional[int] = None,
                 win_title: typing.Optional[str] = None,
                 doc_title: typing.Optional[str] = None,
                 useTableEditor:bool = True,
                 predicate: typing.Optional[typing.Any] = None,
                 readOnly: bool = True,
                 *args, **kwargs):
        r"""
        Parameters:
        ===========
        data: a Python object
        parent: a QMainWindow, a QWidget, or None (default).
            When parent is the Scipyen main window this will be a "top level" viewer

        ID: int: the ID of the viewer's window (mainly useful for managing several
                top level instances of the data viewer

        win_title: when specified, overrides the default window title

        doc_title: when specified, it will be combined with win_title to generate the
            actual window title

        useTableEditor: default is True → will use gui.tableeditor.TableEditor to
            display tabular data; else uses SimpleTableWidget defined in this
            module.

        predicate: a unary python function returning a bool, or None (default)
            When not None, this will effectively filter what contents are displayed
            in the dataviewer, based on the predicate.

            For example, see the 'is*' functions in Python's inspect module.
            Mostly useful with objects.


        *args, **kwargs ⇒ passed on to ScipyenViewer superclass.

        """
        self._showMethods_:bool=kwargs.get("showMethods", False)
        self._showPrivateMembers_:bool = kwargs.get("showPrivate", False)
        self._useTableEditor_ = useTableEditor
        self._readOnly_ = readOnly is True

        if inspect.isfunction(predicate):
            if not self._showMethods_:
                self.predicate = lambda x: predicate(x) and not inspect.ismethod(x)
            else:
                self.predicate = predicate
        else:
            if not self._showMethods_:
                self.predicate = lambda x: not inspect.ismethod(x)
            else:
                self.predicate = None

        # self.hideRoot = hideRoot

        # NOTE: 2025-06-28 14:02:36
        # list of tuple(obj:typing.Any, name:str), where
        # obj is the data itself (or a child) IF the data is a suported type
        # else it is the _private_data_ generated by the InteractiveTreeWidget
        self._obj_cache_ = list()
        self._cache_index_ = 0

        self._top_title_ = ""

        self._dataTypeStr_ = None

        # contains data selected from child widgets (table, and text widgets)
        self._subselections_ = list()

        self._obj_to_view_ = (dataclasses.MISSING, "")

        super().__init__(data=data, parent=parent, win_title=win_title,
                         doc_title = doc_title, ID=ID, *args, **kwargs)

    def _configureUI_(self):
        self.treeView = DataTreeView(parent = self,
                                     supported_data_types = tuple(self.viewer_for_types))
                                     # ,
                                     # readOnly = self._readOnly_)

        self.treeView.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        # TODO implement dragging from here to the workspace
        self.treeView.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        self.treeView.setDragEnabled(True)

        self.treeView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.treeView.customContextMenuRequested[QtCore.QPoint].connect(
            self.slot_customContextMenuRequested
            )

        self.treeView.setAlternatingRowColors(True)

        # NOTE: 2025-03-12 13:25:01 treeView ultimately inherits from QTreeWidget
        # and itemDoubleClicked is a Signal emitted by QTreeWidget
        self.treeView.sig_itemDoubleClicked[QtGui.QStandardItem].connect(self.slot_itemDoubleClicked)

        self.setCentralWidget(self.treeView)
        self._sig_setTreeViewData_.connect(self.treeView.slot_setData)
        # self.treeView.update() # force drawing placeholder text ?!?

        self.toolBar = QtWidgets.QToolBar("Main", self)
        self.toolBar.setObjectName("%s_Main_Toolbar" % self.__class__.__name__)

        refreshAction = self.toolBar.addAction(QtGui.QIcon.fromTheme("view-refresh"), "Refresh")
        refreshAction.triggered.connect(self.slot_refreshDataDisplay)

        collapseAllAction = self.toolBar.addAction(QtGui.QIcon.fromTheme("collapse-all"), "Collapse All")
        collapseAllAction.triggered.connect(self.slot_collapseAll)

        expandAllAction = self.toolBar.addAction(QtGui.QIcon.fromTheme("expand-all"), "Expand All")
        expandAllAction.triggered.connect(self.slot_expandAll)

        self.goFirst = self.toolBar.addAction(QtGui.QIcon.fromTheme("go-first-symbolic"), "First view")
        self.goFirst.triggered.connect(self.slot_goFirst)
        self.goFirst.setEnabled(False)

        self.goBack = self.toolBar.addAction(QtGui.QIcon.fromTheme("go-previous-symbolic"), "Previous")
        self.goBack.triggered.connect(self.slot_goBack)
        self.goBack.setEnabled(False)

        self.goNext = self.toolBar.addAction(QtGui.QIcon.fromTheme("go-next-symbolic"), "Next view")
        self.goNext.triggered.connect(self.slot_goNext)
        self.goNext.setEnabled(False)

        self.addToolBar(QtCore.Qt.TopToolBarArea, self.toolBar)

    @Slot(QtCore.QPoint)
    @safewrapper
    def slot_customContextMenuRequested(self, point):
        from gui.mainwindow import VTH

        # FIXME/TODO copy to system clipboard? - what mime type? JSON data?
        if self._scipyenWindow_ is None:
            return

        # indexList = self.treeView.selectedIndexes()
        # if len(indexList) == 0:
        #     return

        items = self.treeView.selectedItems()
        if len(items) == 0:
            return

        cm = QtWidgets.QMenu("Data operations", self)
        cm.setToolTipsVisible(True)

        copyItemData = cm.addAction("Copy value(s) to workspace")
        copyItemData.setToolTip("Copy value(s) to workspace (SHIFT to assign full path as name)")
        copyItemData.setStatusTip("Copy value(s) to workspace (SHIFT to assign full path as name)")
        copyItemData.setWhatsThis("Copy value(s) to workspace (SHIFT to assign full path as name)")
        copyItemData.triggered.connect(self.slot_exportToWorkspace)

        copyItemPath = cm.addAction("Copy path(s)")
        copyItemPath.triggered.connect(self.slot_copyPaths)

        sendToConsole = cm.addAction("Send path(s) to console")
        sendToConsole.triggered.connect(self.slot_exportToConsole)

        # NOTE: 2025-05-28 13:28:36
        # to keep it simple, restrict the option viewing the selected item, to
        # the case where a single item is selected
        if len(items) == 1:
            names, objects =  self.treeView.exportDataForItems(items)
            obj = objects[0]
            name = names[0]
            self._obj_to_view_ = (obj, name)

            viewItemData = cm.addAction("View")
            # viewItemData.setToolTip("View item in a separate window (SHIFT for a new window)")
            # viewItemData.setStatusTip("View item in a separate window (SHIFT for a new window)")
            # viewItemData.setWhatsThis("View item in a separate window (SHIFT for a new window)")
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

        cm.popup(self.treeView.mapToGlobal(point), copyItemData)

    @Slot()
    @safewrapper
    def slot_exportToWorkspace(self: typing.Self):
        fullPathAsName = bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier)

        if self._scipyenWindow_ is None:
            return

        items = self.treeView.selectedItems()

        if len(items) == 0:
            return

        names, objects  = self.treeView.exportDataForItems(items, fullPathAsName=fullPathAsName)

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

            namePrompt.setText(names[0])
            dlg.adjustSize()

            if dlg.exec() == QtWidgets.QDialog.Accepted:
                newVarName = namePrompt.text()

                self._scipyenWindow_.assignToWorkspace(newVarName, objects[0], check_name=False)

        else:
            for name, obj in zip(names, objects):
                self._scipyenWindow_.assignToWorkspace(name, obj, check_name=False)

    @Slot()
    @safewrapper
    def slot_copyPaths(self: typing.Self):
        if self._scipyenWindow_ is None:
            return

        item_paths = self.treeView.getSelectedPaths()
        self.exportPathsToClipboard(item_paths)

    @Slot()
    def slot_exportToConsole(self: typing.Self):
        if self._scipyenWindow_ is None:
            return

        item_paths = self.treeView.getSelectedPaths()
        self.exportPathsToClipboard(item_paths)
        self._scipyenWindow_.console.paste()

    @Slot()
    @safewrapper
    def slot_collapseAll(self):
        self.treeView.collapseAll()

    @Slot()
    @safewrapper
    def slot_expandAll(self):
        self.treeView.expandAll()
        self.treeView.resizeColumnToContents(0)
    @Slot()
    @safewrapper
    def slot_viewItem(self: typing.Self):
        # from core.utilities import get_nested_value
        if self.scipyenWindow is None or "ScipyenWindow" not in type(self.scipyenWindow).__name__:
            return

        if self._obj_to_view_[0] is dataclasses.MISSING or len(self._obj_to_view_[1].strip()) == 0:
            return

        newWindow = bool(
            QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.AltModifier)

        askForParams = bool(
            QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier)

        variable, varname = self._obj_to_view_

        if newWindow:
            if not self.scipyenWindow.viewObject(variable, varname, winType=self.__class__,
                                    newWindow=True,
                                    askForParams=askForParams):
                self._showInConsole_(variable)
        else:
            if isinstance(variable, tuple(self.viewer_for_types.keys())):
                self.view(variable, doc_title = varname)
            else:
                self._showInConsole_(variable)

        self._obj_to_view_ = (dataclasses.MISSING, "")

    @Slot(QtWidgets.QTreeWidgetItem, int)
    @safewrapper
    def slot_itemDoubleClicked(self, item, column):
        names, objects = self.treeView.exportDataForItems([item])
        obj = objects[0]
        name = names[0]
        self._obj_to_view_ = (obj, name)
        self.slot_viewItem()

    @Slot()
    @safewrapper
    def slot_autoSelectViewer(self):
        from gui.mainwindow import VTH

        if "ScipyenWindow" not in type(self.scipyenWindow).__name__:
            return

        if self._obj_to_view_[0] is dataclasses.MISSING or len(self._obj_to_view_[1].strip()) == 0:
            return

        newWindow = bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.AltModifier)
        askForParams = bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier)

        variable, varname = self._obj_to_view_

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

    @safewrapper
    def exportPathsToClipboard(self, item_paths):
        if self._scipyenWindow_ is None:
            return

        if len(item_paths) > 1:
            if bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier):
                self._scipyenWindow_.app.clipboard().setText(",\n".join(["""%s""" % i for i in item_paths]))
            else:
                self._scipyenWindow_.app.clipboard().setText(", ".join(["""%s""" % i for i in item_paths]))

        elif len(item_paths) == 1:
            self._scipyenWindow_.app.clipboard().setText(item_paths[0])

    def _showInConsole_(self, obj):
        if "ScipyenWindow" not in type(self.scipyenWindow).__name__:
            return
        try:
            # NOTE 2025-05-28 14:22:51
            # as the object may not exist in the workspace, it gets assigned
            # there first, under a special (hidden) name, executed, and finally
            # deleted (i.e. the special (hidden) symbol is removed from the
            # workspace)
            self.scipyenWindow.assignToWorkspace("____", obj)
            self.scipyenWindow.console.execute("____", interactive=False)
            self.scipyenWindow.console.execute("del ____", hidden=True, interactive=False)
        except:
            traceback.print_exc()

    @Slot()
    def slot_goBack(self):
        self._cache_index_ = self._cache_index_ - 1

        if self._cache_index_ < 0:
            self._cache_index_ = 0

        elif self._cache_index_ >= len(self._obj_cache_):
            self._cache_index_ = len(self._obj_cache_) - 1

        self.goNext.setEnabled(self._cache_index_ < len(self._obj_cache_)-1)
        self.goBack.setEnabled(self._cache_index_ > 0)

        worker = WorkerThread(self, self._populateTreeView_)
        worker.signals.signal_Finished.connect(self._slot_treeViewPopulated)
        worker.run()

    @Slot()
    def slot_goFirst(self):
        self._cache_index_ = 0
        self.goNext.setEnabled(self._cache_index_ < len(self._obj_cache_)-1)
        self.goBack.setEnabled(self._cache_index_ > 0)
        worker = WorkerThread(self, self._populateTreeView_)
        worker.signals.signal_Finished.connect(self._slot_treeViewPopulated)
        worker.run()

    @Slot()
    def slot_goNext(self):
        self._cache_index_ = self._cache_index_ + 1
        if self._cache_index_ >= len(self._obj_cache_):
            self._cache_index_ = len(self._obj_cache_) - 1

        self.goNext.setEnabled(self._cache_index_ < len(self._obj_cache_)-1)
        self.goBack.setEnabled(self._cache_index_ >0)
        worker = WorkerThread(self, self._populateTreeView_)
        worker.signals.signal_Finished.connect(self._slot_treeViewPopulated)
        worker.run()

    def _check_cache_(self, obj:typing.Any, name:str) -> bool:
        if isinstance(obj, np.ndarray):
            for (o,n) in self._obj_cache_:
                if isinstance(o, np.ndarray) and np.all(obj.flatten() == o.flatten()) and name == n:
                    return True
            return False

        elif isinstance(obj, (pd.Index, pd.DataFrame, pd.Series)):
            for (o,n) in self._obj_cache_:
                if isinstance(o, type(obj)) and np.all(obj == o) and name == n:
                    return True
            return False
        else:
            # print(f"{self.__class__.__name__}._check_cache_: obj is a {type(obj).__name__}, name: {name} ({type(name).__name__}))")
            for (o,n) in self._obj_cache_:
                if all(isinstance(o_, np.ndarray) for o_ in (o, obj)) and np.all(obj == o) and name ==n:
                    return True
                return False

    def _get_cache_index_(self, obj:typing.Any, name:str) -> int | None:
        if isinstance(obj, np.ndarray):
            for k, (o,n) in enumerate(self._obj_cache_):
                if isinstance(o, np.ndarray) and np.all(obj.flatten() == o.flatten()) and name == n:
                    return k
            return
        elif isinstance(obj, (pd.DataFrame, pd.Index, pd.Series)):
            for k, (o,n) in enumerate(self._obj_cache_):
                if isinstance(o, type(obj)) and np.all(obj == o) and name == n:
                    return k
            return
        else:
            if (obj, name) in self._obj_cache_:
                return self._obj_cache_.index((obj, name))

    def _set_data_(self, data:object, predicate=None, *args, **kwargs):
        r"""
        Displays new data
        """
        self.update()
        if inspect.isfunction(predicate):
            self.predicate=predicate

        if data is not self._data_:
            self._data_ = data
            self._dataTypeStr_ = type(self._data_).__name__
            self._top_title_ = self._docTitle_ if (isinstance(self._docTitle_, str) and len(self._docTitle_.strip())) else "/"

            if self._check_cache_(self._data_, self._top_title_):
                self._cache_index_ = self._get_cache_index_(self._data_, self._top_title_)

                if self._cache_index_ is None:
                    self._cache_index_ = 0
            else:
                self._obj_cache_.append((self._data_, self._top_title_))
                self._cache_index_ = len(self._obj_cache_)-1 if len(self._obj_cache_) > 0 else 0

            for w in (self.goFirst, self.goBack):
                w.setEnabled(len(self._obj_cache_) > 1)

            self.goNext.setEnabled(len(self._obj_cache_) > 1 and self._cache_index_ < len(self._obj_cache_)-1)

            worker = WorkerThread(self, self._populateTreeView_)
            worker.signals.signal_Finished.connect(self._slot_treeViewPopulated)
            worker.run()

        if kwargs.get("show", True):
            self.activateWindow()

    def _populateTreeView_(self):
        self.treeView.clear()
        if len(self._obj_cache_):
            if self._cache_index_ >= len(self._obj_cache_):
                self._cache_index_ = len(self._obj_cache_) - 1
            obj, name = self._obj_cache_[self._cache_index_]
            self.update_title(doc_title = name, win_title=self._winTitle_)
            what = {"data": obj, "predicate": self.predicate, "root_title": name,
                    "showPrivate": self._showPrivateMembers_,
                    "dataTypeStr": type(obj).__name__}
            self._sig_setTreeViewData_.emit(what)

    @Slot()
    def _slot_treeViewPopulated(self):
        self._slot_update_title()
        # self.treeView.collapseAll()
        self.treeView.expandToDepth(1)
        self.treeView.resizeColumnToContents(0)

    @Slot()
    @safewrapper
    def slot_refreshDataDisplay(self):
        worker = WorkerThread(self, self._populateTreeView_)
        worker.signals.signal_Finished.connect(self._slot_treeViewPopulated)
        worker.run()


    @Slot()
    @safewrapper
    def slot_showInConsole(self):
        if self.scipyenWindow is None or "ScipyenWindow" not in type(self.scipyenWindow).__name__:
            return

        if self._obj_to_view_[0] is dataclasses.MISSING or len(self._obj_to_view_[1].strip()) == 0:
            return

        variable, varname = self._obj_to_view_
        self._showInConsole_(variable)
        self._obj_to_view_ = (dataclasses.MISSING, "")

    @Slot(QtGui.QStandardItem)
    def slot_itemDoubleClicked(self: typing.Self, item:QtGui.QStandardItem):
        if item.column() == 0:
            obj = item.data(ObjectDataRole)
            name = item.data(QtCore.Qt.DisplayRole)
            if obj is not None:
                self.view(obj, name)


    # def mouseDoubleClickEvent(self: typing.Self, evt: QtGui.QMouseEvent):
    #     pos = evt.position().toPoint()
    #     index = self.indexAt(pos)
    #     item = self.treeView.model().itemFromIndex(index)
    #     if item.column() == 0:
    #         obj = index.data(ObjectDataRole)
    #         self.view(obj)
    #     super().mouseDoubleClickEvent(evt)
    #     evt.setAccepted(True)
