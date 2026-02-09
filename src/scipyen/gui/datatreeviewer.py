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
from collections import deque
from dataclasses import MISSING
import math
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

from core.prog import (safewrapper, safeguiwrapper, )

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
from gui.widgets import datatreeview
from datatreeview import DataTreeModel, DataTreeView

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
    _sig_setTreeWidgetData_ = Signal(dict, name="_sig_setTreeWidgetData_")

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

        super().__init__(data=data, parent=parent, win_title=win_title, doc_title = doc_title, ID=ID, *args, **kwargs)

    def _configureUI_(self):
        self.treeView = DataTreeView(parent = self,
                                     supported_data_types = tuple(self.viewer_for_types),
                                     readOnly = self._readOnly_)

        self.treeView.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        # TODO implement dragging from here to the workspace
        self.treeView.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        self.treeView.setDragEnabled(True)

        self.treeView.customContextMenuRequested[QtCore.QPoint].connect(self.slot_customContextMenuRequested)

        # NOTE: 2025-03-12 13:25:01 treeView ultimately inherits from QTreeWidget
        # and itemDoubleClicked is a Signal emitted by QTreeWidget
        self.treeView.itemDoubleClicked[QtWidgets.QTreeWidgetItem, int].connect(self.slot_itemDoubleClicked)

        self.setCentralWidget(self.treeView)
        self._sig_setTreeWidgetData_.connect(self.treeView.slot_setData)
        # self.treeView.update() # force drawing placeholder text ?!?

        self.toolBar = QtWidgets.QToolBar("Main", self)
        self.toolBar.setObjectName("%s_Main_Toolbar" % self.__class__.__name__)

        refreshAction = self.toolBar.addAction(QtGui.QIcon.fromTheme("view-refresh"), "Refresh")
        refreshAction.triggered.connect(self.slot_refreshDataDisplay)

        collapseAllAction = self.toolBar.addAction(QtGui.QIcon.fromTheme("collapse-all"), "Collapse All")
        collapseAllAction.triggered.connect(self.slot_collapseAll)

        expandAllAction = self.toolBar.addAction(QtGui.QIcon.fromTheme("expand-all"), "Expand All")
        expandAllAction.triggered.connect(self.slot_expandAll)

        # increaseWidgetHeight

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
