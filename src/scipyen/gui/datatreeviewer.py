# __scipyen_plugin__
# $Id: ${datatreeviewer} $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later


r"""
Views the structure of an object.
Qt-based viewer window for dict and subclasses.
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
    # from PySide6 import Shiboken
    # from PySide6.QtCore import (Signal, Slot, Property,)
    from PySide6.QtUiTools import loadUiType # -- A-HA!
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
from core import bgbridge
from core import taxonbridge

#### END pict.core modules

#### BEGIN pict.gui modules
# from gui.tableeditor import (TableEditorWidget, TabularDataModel,)

# from gui.widgets.interactivetreewidget import InteractiveTreeWidget
# from gui.widgets.simpletablewidget import SimpleTableWidget
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

class DataTreeViewer(ScipyenViewer):
    r"""Replacement for DataViewer.
A lot of things copied from there, EXCEPT that it now uses
``DataTreeview`` and ``DataTreeModel`` from ``gui.widgets.datatreeview`` module.
"""
    # sig_activated = Signal(int)
    sig_activated = Signal()
    closeMe  = Signal(int)
    signal_window_will_close = Signal()
    _sig_setTreeViewData_ = Signal(dict, name="_sig_setTreeViewData_")

    # NOTE: 2022-11-20 22:09:07
    # reserved for future developmet of editing capabilities TODO
    sig_modelDataChanged = Signal(name = "sig_modelDataChanged")

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

    read_only_types = [
        bgbridge.BrainGlobeAtlas,
        bgbridge.Structure,
        taxonbridge.Taxon
        ]

    def __init__(self, data: typing.Optional[object] = None,
                 parent: typing.Optional[QtWidgets.QMainWindow] = None,
                 ID: typing.Optional[int] = None,
                 win_title: typing.Optional[str] = None,
                 doc_title: typing.Optional[str] = None,
                 useTableEditor: bool = True,
                 predicate: typing.Optional[typing.Any] = None,
                 readOnly: bool = True,
                 initialExpandDepth: int = 1,
                 autoResizeColumns: set[int] = {0,1},
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
        self._showIntrospection_: bool = kwargs.get("introspect", False)
        self._showCallables_: bool = kwargs.get("showCallables", False)
        self._showValuesOnly_: bool = kwargs.get("showValuesOnly", True)
        self._useTableEditor_ = useTableEditor
        self._readOnly_ = readOnly is True
        self._alwaysSortRows_: bool = False
        self._showInlineTables_: bool = False

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

        self._initialExpandDepth_: int = initialExpandDepth

        self._autoResizeColumns_: set[int] = autoResizeColumns

        super().__init__(data=data, parent=parent, win_title=win_title,
                         doc_title = doc_title, ID=ID, *args, **kwargs)

    def _configureUI_(self):
        self.fileMenu = QtWidgets.QMenu("File")
        self.menuBar().addMenu(self.fileMenu)
        # NOTE: 2026-03-07 08:56:37 TODO
        # add here file menu actions
        self.settingsMenu = QtWidgets.QMenu("Settings")
        self.menuBar().addMenu(self.settingsMenu)
        self.initialExpandToLevelAction = QtGui.QAction(
            QtGui.QIcon.fromTheme("expand"), "Auto-expand nodes", self)
        self.initialExpandToLevelAction.setMenuRole(QtGui.QAction.PreferencesRole)
        self.initialExpandToLevelAction.triggered.connect(self._slot_setInitialAutoExpandNodesLevel)
        self.settingsMenu.addAction(self.initialExpandToLevelAction)
        self.autoResizeColumnsAction = QtGui.QAction(
            QtGui.QIcon.fromTheme("resizecol"), "Auto-resize columns", self)
        self.autoResizeColumnsAction.setMenuRole(QtGui.QAction.PreferencesRole)
        self.autoResizeColumnsAction.triggered.connect(self._slot_setAutoResizeColumns)
        self.settingsMenu.addAction(self.autoResizeColumnsAction)
        # self.menuBar.addAction(self.settingsAction)
        self.treeView = DataTreeView(parent = self,
                                     supported_data_types = tuple(self.viewer_for_types),
                                     initialExpandDepth = self._initialExpandDepth_,
                                     autoResizeColumns = self._autoResizeColumns_)

        self.model = self.treeView.sourceModel
        self.model.sig_modelDataChanged.connect(self.sig_modelDataChanged)

        # NOTE: 2026-07-05 22:03:56 moved to datatreeview
        #
        # self.treeView.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        #
        # # TODO implement dragging from here to the workspace
        # self.treeView.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        # self.treeView.setDragEnabled(True)
        #
        # self.treeView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # self.treeView.customContextMenuRequested[QtCore.QPoint].connect(
        #     self.slot_customContextMenuRequested
        #     )
        #
        # self.treeView.setAlternatingRowColors(True)

        # self.treeView.expanded.connect(self._slot_indexExpanded)
        # self.treeView.collapsed.connect(self._slot_indexCollapsed)

        # NOTE: 2026-07-05 22:03:56 moved to datatreeview
        # NOTE: 2025-03-12 13:25:01 treeView ultimately inherits from QTreeWidget
        # and itemDoubleClicked is a Signal emitted by QTreeWidget
        # self.treeView.sig_itemDoubleClicked[QtGui.QStandardItem].connect(self.slot_itemDoubleClicked)

        self.setCentralWidget(self.treeView)
        self._sig_setTreeViewData_.connect(self.treeView.slot_setData)
        # self.treeView.update() # force drawing placeholder text ?!?

        self.toolBar = QtWidgets.QToolBar("Main", self)
        self.toolBar.setObjectName("%s_Main_Toolbar" % self.__class__.__name__)

        refreshAction = self.toolBar.addAction(
            QtGui.QIcon.fromTheme("view-refresh"), "Refresh")
        refreshAction.triggered.connect(self.slot_refreshDataDisplay)

        # self.alwaysSortAction = self.toolBar.addAction(
        #     QtGui.QIcon.fromTheme("sort-name"), "Always sort rows ascending")
        # self.alwaysSortAction.setCheckable(True)
        # self.alwaysSortAction.setChecked(True)
        # self.alwaysSortAction.toggled.connect(self.slot_alwaysSortRows)

        self.inlineTablesAction = self.toolBar.addAction(
            QtGui.QIcon.fromTheme("table"), "Inline Tables")
        self.inlineTablesAction.setCheckable(True)
        self.inlineTablesAction.setChecked(False)
        self.inlineTablesAction.toggled.connect(self.slot_setInlineTables)

        collapseAllAction = self.toolBar.addAction(
            QtGui.QIcon.fromTheme("collapse-all"), "Collapse All")
        collapseAllAction.triggered.connect(self.treeView.slot_collapseAll)

        expandAllAction = self.toolBar.addAction(
            QtGui.QIcon.fromTheme("expand-all"), "Expand All")
        expandAllAction.triggered.connect(self.treeView.slot_expandAll)

        resizeColumnsAction = self.toolBar.addAction(
            QtGui.QIcon.fromTheme("resizecol"), "Fit Columns Size to Contents")
        resizeColumnsAction.triggered.connect(self.treeView.slot_resizeFitColumns)

        self.showCallablesAction = self.toolBar.addAction(
            QtGui.QIcon.fromTheme("code-function"), "Show Function and Method Members")
        self.showCallablesAction.setCheckable(True)
        self.showCallablesAction.setChecked(False)

        self.showCallablesAction.toggled.connect(self.slot_showCallables)

        self.showValuesOnlyAction = self.toolBar.addAction(
            QtGui.QIcon.fromTheme("object"), "Show Value Objects Only")
        self.showValuesOnlyAction.setCheckable(True)
        self.showValuesOnlyAction.setChecked(False)

        self.showValuesOnlyAction.toggled.connect(self.slot_showValuesOnly)

        self.showPrivateMembersAction = self.toolBar.addAction(
            QtGui.QIcon.fromTheme("view-private"), "Show private members")
        self.showPrivateMembersAction.setCheckable(True)
        self.showPrivateMembersAction.setChecked(False)

        self.showPrivateMembersAction.toggled.connect(self.slot_showPrivateMembers)

        self.showIntrospectAction = self.toolBar.addAction(
            QtGui.QIcon.fromTheme("view-list-details"), "Introspect")
        self.showIntrospectAction.setCheckable(True)
        self.showIntrospectAction.setChecked(False)

        self.showIntrospectAction.toggled.connect(self.slot_showIntrospect)

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

    @Slot(bool)
    @safewrapper
    def slot_showCallables(self, value: bool):
        # print(f"{self.__class__.__name__},slot_showCallables({value})")
        self.model.showMethods = value is True
        self.slot_refreshDataDisplay()

    @Slot(bool)
    @safewrapper
    def slot_showValuesOnly(self, value: bool):
        self.showValuesOnly = value is True

    @Slot(bool)
    def slot_showPrivateMembers(self, value: bool):
        self.showPrivateMembers = value is True

    @Slot(bool)
    def slot_showIntrospect(self, value: bool):
        self.showIntrospection = value is True

    @Slot(bool)
    @safewrapper
    def slot_setInlineTables(self, value: bool):
        self.showInlineTables = value is True

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

    def setRootName(self, value: str):
        self._top_title_ = value
        if self._cache_index_ >= len(self._obj_cache_):
            self._cache_index_ = len(self._obj_cache_) - 1
        obj, name = self._obj_cache_[self._cache_index_]
        if name != self._top_title_:
            name = self._top_title_
            self._obj_cache_[self._cache_index_] = (obj, name)
        self.treeView.setRootName(value)

    def _set_data_(self, data:object, predicate=None, *args, **kwargs):
        r"""
        Displays new data
        """
        # print(f"{self.__class__.__name__}._set_data_({type(data)},\n\tkwargs = {kwargs})")
        self._readOnly_ = kwargs.get("readOnly", False) or isinstance(data, tuple(self.read_only_types))

        objName = kwargs.pop("name", None)

        if inspect.isfunction(predicate):
            self.predicate=predicate

        if data is not self._data_:
            # print("\n\tnew data")
            self._data_ = data
            self._dataTypeStr_ = type(self._data_).__name__
            if isinstance(objName, str) and len(objName.strip()):
                self._top_title_ = objName

            elif isinstance(self._docTitle_, str) and len(self._docTitle_.strip()):
                self._top_title_ = self._docTitle_

            else:
                self._top_title_ = "/"

            if self._check_cache_(self._data_, self._top_title_):
                # print(f"\n\tcache: {self._obj_cache_}")
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

        else:
            # print(f"\n\nsame data -> objName = {objName}; top title = {self._top_title_}")
            if isinstance(objName, str) and len(objName.strip()):
                if self._top_title_ != objName:
                    self._top_title_ = objName
                    self.treeView.setRootName(self._top_title_)


    def _populateTreeView_(self):
        if len(self._obj_cache_):
            if self._cache_index_ >= len(self._obj_cache_):
                self._cache_index_ = len(self._obj_cache_) - 1
            obj, name = self._obj_cache_[self._cache_index_]
            if name != self._top_title_:
                name = self._top_title_
                self._obj_cache_[self._cache_index_] = (obj, name)
            # print(f"{self.__class__.__name__}._populateTreeView_: name = {name}")
            self.update_title(doc_title = name, win_title=self._winTitle_)
            what = {"data": obj,
                    "predicate": self.predicate,
                    "root_title": name,
                    "readOnly": self.readOnly,
                    "showPrivate": self.showPrivateMembers,
                    "valuesOnly": self.showValuesOnly,
                    "inlineTables": self.showInlineTables,
                    "introspect": self.showIntrospection,
                    }
            # print(f"\n\temit self._sig_setTreeViewData_")
            self._sig_setTreeViewData_.emit(what)

    @Slot()
    def _slot_setInitialAutoExpandNodesLevel(self):
        d = quickdialog.QuickDialog(
            self, "Automatically expand nodes")
        w = quickdialog.SpinBox(d, "Expand to level:")
        w.setMinimum(0)
        w.setMaximum(2)
        w.setValue(self._initialExpandDepth_)
        d.addWidget(w)
        # d.resize(-1,-1)
        d.adjustSize()

        if d.exec():
            val = w.value()
            self.initialExpandDepth = val

    @Slot()
    def _slot_setAutoResizeColumns(self):
        d = quickdialog.QuickDialog(
            self, "Automatically resize columns")
        w = quickdialog.StringInput(d, "Comma-separated column indices:",
                                    allowEmptyString = True)
        w.setValue(", ".join(list(map(lambda v: f"{v}", self._autoResizeColumns_))))

        # d.resize(-1,-1)
        d.adjustSize()

        if d.exec():
            val = w.value()
            if len(val.strip()):
                indices = set(list(map(lambda s: eval(s), val.split(","))))
                self.autoResizeColumns = indices

            else:
                self.autoResizeColumns = set()

    @Slot()
    def _slot_treeViewPopulated(self):
        self._slot_update_title() # inherited from ScipyenViewer

    @Slot()
    @safewrapper
    def slot_refreshDataDisplay(self):
        worker = WorkerThread(self, self._populateTreeView_)
        worker.signals.signal_Finished.connect(self._slot_treeViewPopulated)
        worker.run()

#     @property
#     def docTitle(self):
#         return super().docTitle
#
#     @docTitle.setter
#     def docTitle(self, value: str | None):
#         super().docTitle = value
#         if isinstance(value, str) and len(value.strip()):
#             self.treeView.

    # @Slot()
    # @safewrapper
    # def slot_showInConsole(self):
    #     if self.scipyenWindow is None or "ScipyenWindow" not in type(self.scipyenWindow).__name__:
    #         return
    #
    #     if self._obj_to_view_[0] is dataclasses.MISSING or len(self._obj_to_view_[1].strip()) == 0:
    #         return
    #
    #     variable, varname = self._obj_to_view_[:2]
    #     self._showInConsole_(variable)
    #     self._obj_to_view_ = (dataclasses.MISSING, "")

    # @Slot(QtGui.QStandardItem)
    # def slot_itemDoubleClicked(self: typing.Self, item:QtGui.QStandardItem):
    #     # print(f"{self.__class__.__name__}.slot_itemDoubleClicked")
    #     askForParams = bool(
    #         QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier)
    #
    #     if not self.model:
    #         # print(f"\tno model")
    #         return
    #
    #     if item.column() == 0:
    #         readOnly = item.data(ReadOnlyRole) is True # noqa
    #         obj = self.treeView.sourceModel.getDataObjectForLeaf(item)
    #         if obj is None:
    #             return
    #         name = item.data(QtCore.Qt.DisplayRole)
    #         if item.data(ObjectDataEditExternallyRole) is True:
    #             # print(f"{self.__class__.__name__}.slot_itemDoubleClicked -> view externally")
    #             self._editExternally_(obj, name, askForParams)
    #
    #         else:
    #             # obj = self.treeView.model().getDataObjectForLeaf(item)
    #             # name = item.data(QtCore.Qt.DisplayRole)
    #             self.treeView.readOnly = readOnly
    #             self.view(obj, name)
    #             # if obj is not None:

    # @property
    # def alwaysSortRows(self) -> bool:
    #     return self._alwaysSortRows_
    #
    # @markConfigurable("AlwaysSortRows", "qt", trait_notifier = True)
    # @alwaysSortRows.setter
    # def alwaysSortRows(self, val: bool):
    #     if self._alwaysSortRows_ != val:
    #         self._alwaysSortRows_ = val is True
    #         sigBlock = QtCore.QSignalBlocker(self.alwaysSortAction)
    #         self.alwaysSortAction.setChecked(self._alwaysSortRows_)
    #         if self._alwaysSortRows_ != self.model.sortedRows:
    #             self.model.sortedRows = self._alwaysSortRows_
    #             self.slot_refreshDataDisplay()

    @property
    def showInlineTables(self) -> bool:
        return self._showInlineTables_

    @markConfigurable("ShowInlineTables", "qt", trait_notifier = True)
    @showInlineTables.setter
    def showInlineTables(self, val: bool):
        self._showInlineTables_ = val is True
        sigBlock = QtCore.QSignalBlocker(self.inlineTablesAction)
        self.inlineTablesAction.setChecked(self._showInlineTables_)
        if self._data_ is not None and val != self.model.inlineTables:
            self.model.inlineTables = self._showInlineTables_
            self.slot_refreshDataDisplay()
            # self.slot_setInlineTables(self._showInlineTables_)
            # self.showInlineTables = self._showInlineTables_

    @property
    def initialExpandDepth(self) -> int:
        return self._initialExpandDepth_

    @markConfigurable("InitialExpandDepth", "qt", trait_notifier=True)
    @initialExpandDepth.setter
    def initialExpandDepth(self, val: int):
        if val in range(3):
            self._initialExpandDepth_ = val
            self.treeView.initialExpandDepth = self._initialExpandDepth_
            self.treeView.update()
            # self.slot_refreshDataDisplay()

    @property
    def autoResizeColumns(self) -> set:
        return self._autoResizeColumns_

    @markConfigurable("AutoResizeColumns", "qt", trait_notifier = True)
    @autoResizeColumns.setter
    def autoResizeColumns(self,
                          val: typing.Union[set[int], str, typing.Sequence[int]]):
        indices = set()
        if isinstance(val, str):
            try:
                if len(val.strip()):
                    indices = set(list(map(lambda s: eval(s), val)))
                    if not all((isinstance(v, int) and v in range(3)) for v in indices):
                        scipywarn("Invalid indices: all must be integers in range 0-2 inclusive")
                        indices = set()
            except:
                traceback.print_exc()

        elif isinstance(val, (typing.Sequence, set)) and all((isinstance(v, int) and v in range(3)) for v in val):
            indices = set(val)

        self._autoResizeColumns_ = indices
        self.treeView.autoResizeColumns = self._autoResizeColumns_
        self.treeView.update()
        # self.slot_refreshDataDisplay()

    @property
    def readOnly(self: typing.Self) -> bool:
        return self._readOnly_

    @readOnly.setter
    def readOnly(self: typing.Self, val: bool):
        self._readOnly_ = val is True

    @property
    def showPrivateMembers(self) -> bool:
        return self._showPrivateMembers_

    @markConfigurable("ShowPrivateMembers", "Qt", trait_notifier = True)
    @showPrivateMembers.setter
    def showPrivateMembers(self, value: bool):
        self._showPrivateMembers_ = value is True
        if self.model.showPrivateMembers != self._showPrivateMembers_:
            self.model.showPrivateMembers = self._showPrivateMembers_
            self.slot_refreshDataDisplay()
        signalBlockers = QtCore.QSignalBlocker(self.showPrivateMembersAction) # noqa
        self.showPrivateMembersAction.setChecked(self._showPrivateMembers_)

    @property
    def showIntrospection(self) -> bool:
        return self._showIntrospection_

    @markConfigurable("IntrospectObjects", "Qt", trait_notifier = True)
    @showIntrospection.setter
    def showIntrospection(self, value: bool):
        self._showIntrospection_ = value is True
        if self.model.showIntrospection != self._showIntrospection_:
            self.model.showIntrospection = self._showIntrospection_
            self.slot_refreshDataDisplay()
        signalBlockers = QtCore.QSignalBlocker(self.showIntrospectAction) # noqa
        self.showIntrospectAction.setChecked(self._showIntrospection_)

    @property
    def showValuesOnly(self) -> bool:
        return self._showValuesOnly_

    @markConfigurable("ShowValuesOnly", "Qt", trait_notifier = True)
    @showValuesOnly.setter
    def showValuesOnly(self, val: bool):
        self._showValuesOnly_ = val is True
        if self.model.showValuesOnly != self._showValuesOnly_:
            self.model.showValuesOnly = val is True
            self.slot_refreshDataDisplay()
        signalBlockers = QtCore.QSignalBlocker(self.showValuesOnlyAction) # noqa
        self.showValuesOnlyAction.setChecked(self._showValuesOnly_)

        # if self._data_ is not None:
        #     self.slot_showValuesOnly(self._showValuesOnly_)


    @property
    def showCallables(self) -> bool:
        return self._showCallables_

    @markConfigurable("ShowCallables", "Qt", trait_notifier = True)
    @showCallables.setter
    def showCallables(self, value: bool):
        self._showCallables_ = value is True
        signalBlockers = QtCore.QSignalBlocker(self.showCallablesAction)
        self.showCallablesAction.setChecked(self._showCallables_)

        if self._data_ is not None:
            self.slot_showCallables(self._showCallables_)


