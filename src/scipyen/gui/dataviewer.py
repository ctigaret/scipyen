# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later


r"""
Qt5-based viewer window for dict and subclasses
"""

#### BEGIN core python modules
from __future__ import print_function

import os, sys, warnings, types, traceback, itertools, inspect
import typing, dataclasses, numbers
from collections import deque
from dataclasses import MISSING
import math
#### END core python modules

#### BEGIN 3rd party modules
from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import Signal, Slot, Property

from pyqtgraph import (DataTreeWidget, TableWidget, )

import neo
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

#from core.utilities import (get_nested_value, set_nested_value, counter_suffix, )

from core.utilities import NestedFinder

from core.prog import (safewrapper, safeguiwrapper, )

from core.traitcontainers import (DataBag, DataBagTraitsObserver,)
from core.scipyendataclasses import ScipyenDataclass

# from gui.tableeditor import (TableEditorWidget, TabularDataModel,)

from gui.widgets.interactivetreewidget import InteractiveTreeWidget
from gui.widgets.tablewidget import SimpleTableWidget
from gui.widgets.tableeditorwidget import (TableEditorWidget, TabularDataModel)

#### END pict.core modules

#### BEGIN pict.gui modules
from gui.scipyenviewer import ScipyenViewer #, ScipyenFrameViewer
from gui import quickdialog

# from . import resources_rc
# from . import icons_rc
#### END pict.gui modules

# NOTE: 2022-12-25 23:08:51
# needed for the new plugins framework
# This plugins does not install a custom menu, but DOES provide a viewer type
# hence we flag it using __scipyen_plugin__ (we could have defined
# init_scipyen_plugin instead, to return an empty dict)
__scipyen_plugin__ = None

class DataViewer(ScipyenViewer):
    r"""Viewer for hierarchical (nesting) collection types.
    These can be: (nested) dictionaries, lists, tuples.
    Numpy arrays and pandas data types, although collection data types, are
    considered "leaf" objects.
    
    Changelog (most recent first):
    ------------------------------
    2022-03-04 09:33:49: the constructor gives the options to choose between
        TableEditorWidget and SimpleTableWidget as widget for displaying tabular
        data (data frames, series, arrays, matrices, signals, etc)
        TODO: make this user-selectable in the GUI
    2021-08-15 22:51:43: support for circular references to hierarchical data types
        e.g., a dict can contain a key mapped to itself
    2019: Uses InteractiveTreeWidget which inherits from pyqtgraph DataTreeWidget 
    and in turn inherits from QTreeWidget.
    """
    sig_activated = Signal(int)
    closeMe  = Signal(int)
    signal_window_will_close = Signal()
    
    # NOTE: 2022-11-20 22:09:07
    # reserved for future developmet of editing capabilities TODO
    sig_dataChanged = Signal(name = "sig_dataChanged")
    
    # TODO: 2019-11-01 22:44:34
    # implement viewing of other data structures (e.g., viewing their __dict__
    # for the generic case, )
    # viewer_for_types = {dict:99, 
    #                     list:99, 
    #                     tuple:99,
    #                     types.TracebackType:99,
    #                     pd.DataFrame:0,
    #                     pd.Series:0,
    #                     pd.Index:0,
    #                     neo.core.dataobject.DataObject:0,
    #                     pq.Quantity:0,
    #                     np.ndarray:0,
    #                     AxesCalibration:0,
    #                     neo.core.baseneo.BaseNeo:0,
    #                     TriggerProtocol:0}
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
    
    # view_action_name = "Object"
    
    def __init__(self, data: typing.Optional[object] = None, 
                 parent: typing.Optional[QtWidgets.QMainWindow] = None, 
                 ID: typing.Optional[int] = None,  
                 win_title: typing.Optional[str] = None, 
                 doc_title: typing.Optional[str] = None, 
                 useTableEditor:bool = True, 
                 predicate: typing.Optional[typing.Any] = None, 
                 # hideRoot:bool=False, 
                 *args, **kwargs):
        r"""
        Parameters:
        ===========
        data: a Python object
        parent: a QMainWindow, a QWidget, or None (default).
            When parent is the Scipyen main window this will be a "top level" viewer
    
        ID: int: the ID of the viewer's window (mainly useful for managing several
                top level isntances of the data viewer
    
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
        # hideRoot: When false (default) the root of the tree hierarchy is displayed.
        self._useTableEditor_ = useTableEditor
        
        if inspect.isfunction(predicate):
            self.predicate = predicate
        else:
            self.predicate=None
            
        # self.hideRoot = hideRoot
        
        self._obj_cache_ = list()
        self._cache_index_ = 0
        
        self._top_title_ = ""
        
        self._dataTypeStr_ = None
        
        # contains data selected from child widgets (table, and text widgets)
        self._subselections_ = list()
        
        super().__init__(data=data, parent=parent, win_title=win_title, doc_title = doc_title, ID=ID, *args, **kwargs)
        
    def _configureUI_(self):
        self.treeWidget = InteractiveTreeWidget(parent = self, 
                                                useTableEditor = self._useTableEditor_,
                                                supported_data_types = tuple(self.viewer_for_types))
        
        self.treeWidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        
        # TODO implement dragging from here to the workspace
        self.treeWidget.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        self.treeWidget.setDragEnabled(True)
        
        self.treeWidget.customContextMenuRequested[QtCore.QPoint].connect(self.slot_customContextMenuRequested)
        
        # NOTE: 2025-03-12 13:25:01 treeWidget ultimately inherits from QTreeWidget
        # and itemDoubleClicked is a Signal emitted by QTreeWidget
        self.treeWidget.itemDoubleClicked[QtWidgets.QTreeWidgetItem, int].connect(self.slot_itemDoubleClicked)
        
        self.setCentralWidget(self.treeWidget)
        
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
        
    # def _set_data_(self, data:object, predicate=None, hideRoot=False, *args, **kwargs):
    def _set_data_(self, data:object, predicate=None, *args, **kwargs):
        r"""
        Displays new data
        """
        if inspect.isfunction(predicate):
            self.predicate=predicate
            
        # self.hideRoot = hideRoot
        
        # print(f"{self.__class__.__name__}._set_data_ predicate = {self.predicate}")
        
        if data is not self._data_:
            # print(f"{self.__class__.__name__}._set_data_ data is a {type(data).__name__}")
            self._data_ = data
            self._dataTypeStr_ = type(self._data_).__name__
            self._top_title_ = self._docTitle_ if (isinstance(self._docTitle_, str) and len(self._docTitle_.strip())) else "/"
            
            self._obj_cache_.clear()
            self._cache_index_ = 0
            for w in (self.goFirst, self.goBack, self.goNext):
                w.setEnabled(False)
            
            self._obj_cache_.append((self._top_title_, self._data_))
            
            self._populate_tree_widget_()
            
            #if self.treeWidget.topLevelItemCount() == 1:
                #self.treeWidget.topLevelItem(0).setText(0, top_title)
                
            for k in range(self.treeWidget.topLevelItemCount()):
                self._collapse_expand_Recursive(self.treeWidget.topLevelItem(k), current=False)
                #self._collapseRecursive_(self.treeWidget.topLevelItem(k), collapseCurrent=False)
                
        if kwargs.get("show", True):
            self.activateWindow()
            
    def _populate_tree_widget_(self):
        self.treeWidget.clear()
        if len(self._obj_cache_):
            if self._cache_index_ >= len(self._obj_cache_):
                self._cache_index_ = len(self._obj_cache_) - 1
            obj_tuple = self._obj_cache_[self._cache_index_]
            self.treeWidget.setData(obj_tuple[1], 
                                    predicate = self.predicate, 
                                    top_title=obj_tuple[0], 
                                    dataTypeStr=type(obj_tuple[1]).__name__)#, 
                                    # dataTypeStr=self._dataTypeStr_, 
                                    # hideRoot=self.hideRoot)
            self.docTitle = obj_tuple[0]
            
            for k in range(self.treeWidget.topLevelItemCount()):
                self._collapse_expand_Recursive(self.treeWidget.topLevelItem(k), current=False)

    @Slot()
    @safewrapper
    def slot_refreshDataDisplay(self):
        self._top_title_ = self._docTitle_ if (isinstance(self._docTitle_, str) and len(self._docTitle_.strip())) else "/"
        
        if len(self._obj_cache_):
            self._obj_cache_[0] = (self._top_title_, self._data_)
            if len(self._obj_cache_) > 1:
                self._obj_cache_[1:] = []
                
        else:
            self._obj_cache_.append((self._top_title_, self._data_))
        
        self._cache_index_ = 0
        for w in (self.goFirst, self.goBack, self.goNext):
            w.setEnabled(False)
        self._populate_tree_widget_()
            
    @Slot(QtWidgets.QTreeWidgetItem, int)
    @safewrapper
    def slot_itemDoubleClicked(self, item, column):
        from core.utilities import get_nested_value
        if self._scipyenWindow_ is None:
            return
        
        # editor = self.treeWidget.openPersistentEditor(item, column)
        # print(f"{self.__class__.__name__}.slot_itemDoubleClicked: editor = {editor}")
        item_path = list()
        item_path.append(item.text(0))
        
        parent = item.parent()
        
        while parent is not None:
            item_path.append(parent.text(0))
            parent = parent.parent()
        
        item_path.reverse()
        # print(f"item_path {item_path}")
        # obj = get_nested_value(self._data_, item_path[1:]) # because 1st item is the insivible root name
        if self.treeWidget.has_dynamic_private:
            obj = getattr(self._obj_cache_[self._cache_index_][1], item_path[-1], None)
        else:
            obj = get_nested_value(self._obj_cache_[self._cache_index_][1], item_path[1:]) # because 1st item is the insivible root name
        
        objname = " > ".join(item_path)
        
        newWindow = bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier)
        
        # print(f"slot_itemDoubleClicked obj: {objname} =  {type(obj).__name__}")
        if obj is None:
            return
        
        if newWindow:
            self._scipyenWindow_.viewObject(obj, objname, 
                                        newWindow=newWindow)
            
        else:
            if objname in tuple(t[0] for t in self._obj_cache_):
                ndx = [k for k in range(len(self._obj_cache_)) if self._obj_cache_[k][0] == objname]
                if len(ndx):
                    self._cache_index_ = ndx[0]
                
            else:
                self._obj_cache_.append((objname, obj))
                self._cache_index_ = self._cache_index_ + 1
                
            for w in (self.goFirst, self.goBack):
                w.setEnabled(len(self._obj_cache_) > 1)
                
            self.goNext.setEnabled(self._cache_index_ < len(self._obj_cache_)-1)
            
            self._populate_tree_widget_()
            
    @Slot()
    def slot_goBack(self):
        self._cache_index_ = self._cache_index_ - 1
        
        if self._cache_index_ < 0:
            self._cache_index_ = 0
            
        elif self._cache_index_ >= len(self._obj_cache_):
            self._cache_index_ = len(self._obj_cache_) - 1
            
        self.goNext.setEnabled(self._cache_index_ < len(self._obj_cache_)-1)
        self.goBack.setEnabled(self._cache_index_ >0)
            
        self._populate_tree_widget_()
        
    @Slot()
    def slot_goFirst(self):
        self._cache_index_ = 0
        self._populate_tree_widget_()
        
    @Slot()
    def slot_goNext(self):
        self._cache_index_ = self._cache_index_ + 1
        if self._cache_index_ >= len(self._obj_cache_):
            self._cache_index_ = len(self._obj_cache_) - 1
            
        self.goNext.setEnabled(self._cache_index_ < len(self._obj_cache_)-1)   
        self.goBack.setEnabled(self._cache_index_ >0)
        self._populate_tree_widget_()
        
    @Slot(QtCore.QPoint)
    @safewrapper
    def slot_customContextMenuRequested(self, point):
        # FIXME/TODO copy to system clipboard? - what mime type? JSON data?
        if self._scipyenWindow_ is None: 
            return
        
        indexList = self.treeWidget.selectedIndexes()
        
        if len(indexList) == 0:
            return
        
        cm = QtWidgets.QMenu("Data operations", self)
        cm.setToolTipsVisible(True)
        
        copyItemData = cm.addAction("Copy value(s) to workspace")
        copyItemData.setToolTip("Copy value(s) to workspace (SHIFT to assign full path as name)")
        copyItemData.setStatusTip("Copy value(s) to workspace (SHIFT to assign full path as name)")
        copyItemData.setWhatsThis("Copy value(s) to workspace (SHIFT to assign full path as name)")
        copyItemData.triggered.connect(self.slot_exportItemDataToWorkspace)
        
        copyItemPath = cm.addAction("Copy path(s)")
        copyItemPath.triggered.connect(self.slot_copyPaths)
        
        sendToConsole = cm.addAction("Send path(s) to console")
        sendToConsole.triggered.connect(self.slot_exportItemPathToConsole)
        
        viewItemData = cm.addAction("View")
        viewItemData.setToolTip("View item in a separate window (SHIFT for a new window)")
        viewItemData.setStatusTip("View item in a separate window (SHIFT for a new window)")
        viewItemData.setWhatsThis("View item in a separate window (SHIFT for a new window)")
        viewItemData.triggered.connect(self.slot_viewItemDataInNewWindow)
        
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
        
        cm.popup(self.treeWidget.mapToGlobal(point), copyItemData)
        
        
    @safewrapper
    def getSelectedPaths(self):
        items = self.treeWidget.selectedItems()
        
        if len(items) == 0:
            return
        
        return self._export_data_items_(items, path_only=True)
        
#         item_paths = list()
#         
#         top_title = self.treeWidget.top_title
#         
#         for item in items:
#             try:
#                 path, accessList, direct = self._get_path_for_item_(item)
#             except:
#                 exc = sys.exception()
#                 msg = "".join(traceback.format_exception_only(exc))
#                 self.errorMessage(type(exc).__name__, msg)
#                 raise
#             
#             if len(path) == 0:
#                 continue
#             
#             if len(accessList) > 1:
#                 for k, statement, eAccess, oType, tType in enumerate(accessList):
#                     
#             
#             item_paths.apend(path)
#             
# #             if fullPathAsName:
# #                 # print(f"{self.__class__.__name__}_export_data_items_ full_path = {path}")
# #                 name = strutils.str2symbol("_".join(path))
# #                 
# #             else:
# #                 name = strutils.str2symbol(path[-1])
#            
#         
#         if isinstance(self._data_, NestedFinder.nesting_types):
#             for item in items:
#                 item_path = self._get_path_for_item_(item)
#                 
#                 expr = NestedFinder.paths2expression(self._data_, item_path)
#                 
#                 if len(top_title.strip()) > 0 and top_title not in (os.path.sep, "/"):
#                     expr = top_title+expr
#                 
#                 item_paths.append(expr)
#                 
#         elif dataclasses.is_dataclass(self._data_):
#             for item in items:
#                 item_path = self._get_path_for_item_(item)
#                 expr = NestedFinder.paths2expression(self._data_, item_path)
#                 if len(top_title.strip()) > 0 and top_title != ".":
#                     expr = top_title+expr
#                 item_paths.append(expr)
                
        return item_paths
        
    @safewrapper
    def exportPathsToClipboard(self, item_paths):
        # print(f"{self.__class__.__name__}.exportPathsToClipboard({item_paths})")
        if self._scipyenWindow_ is None:
            return
        
        if len(item_paths) > 1:
            if bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier):
                self._scipyenWindow_.app.clipboard().setText(",\n".join(["""%s""" % i for i in item_paths]))
            else:
                self._scipyenWindow_.app.clipboard().setText(", ".join(["""%s""" % i for i in item_paths]))
                
        elif len(item_paths) == 1:
            self._scipyenWindow_.app.clipboard().setText(item_paths[0])
            
    @Slot()
    @safewrapper
    def slot_collapseAll(self):
        for k in range(self.treeWidget.topLevelItemCount()):
            self._collapse_expand_Recursive(self.treeWidget.topLevelItem(k), current=False)

    
    @Slot()
    @safewrapper
    def slot_expandAll(self):
        for k in range(self.treeWidget.topLevelItemCount()):
            self._collapse_expand_Recursive(self.treeWidget.topLevelItem(k), expand=True, current=False)
        
    @Slot()
    @safewrapper
    def slot_copyPaths(self):
        if self._scipyenWindow_ is None:
            return
        
        item_paths = self.getSelectedPaths()
        self.exportPathsToClipboard(item_paths)

    @Slot()
    @safewrapper
    def slot_exportItemPathToConsole(self):
        if self._scipyenWindow_ is None:
            return
        
        item_paths = self.getSelectedPaths()
        self.exportPathsToClipboard(item_paths)
        self._scipyenWindow_.console.paste()
                
    @Slot()
    @safewrapper
    def slot_exportItemDataToWorkspace(self):
        r"""Exports data from currently selected items to the workspace.
        
        When a single item is selected, the user is presented with a Dialog to
        verify/modify the symbol (name) to which the data will be bound in the
        workspace.
        
        When multiple items are selected, the data will be exported directly to
        the workspace, bound to symbols (named) generated from the item name or 
        from the tree path (see below). If these symbols already exists, they will
        be re-bound to the new data (with the previously bounded data to be
        garbage collected by the python interpreter).
        
        The symbol (or name) of the data is created from the item's display str
        in the first column of the table widget (i.e. the key / index).
        
        If the key / index corresponds to a str key (or field name in the case of
        namedtuple objects) the symbol is named directly after the key.
        
        If the key / index is an int (as in the case of int index into sequences)
        the symbol is the string representation of the index prefixed with 'data_'.
        
        When SHIFT key is pressed, the symbol(s) are generated from the FULL path
        (from top level to the leaf item)
        
        NOTE 1: Multiple selections are possible by SHIFT + LMB click (contiguous)
        or CTRL + LMB click (discontiguous)
        
        NOTE 2: This does NOT export subarrays or slices of pandas objects.
        
        
        """
        fullPathAsName = bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier)
        
        if self._scipyenWindow_ is None:
            return
        
        items = self.treeWidget.selectedItems()
        
        if len(items) == 0:
            return
        
        self._export_data_items_(items, fullPathAsName=fullPathAsName)
        
    @Slot()
    @safewrapper
    def slot_editItemData(self):
        # TODO: 2022-10-11 13:45:35
        from core.utilities import get_nested_value
        pass
        items = self.treeWidget.selectedItems()
        
        if len(items) != 1:
            return
        
        
    @Slot()
    @safewrapper
    def slot_viewItemDataInNewWindow(self):
        from core.utilities import get_nested_value
        if self._scipyenWindow_ is None:
            return
        
        items = self.treeWidget.selectedItems()
        
        if len(items) == 0:
            return
        
        values = list()
        
        item_paths = list()
        
        full_item_paths = list()
        
        useSignalViewerForNdArrays = bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier)
        
        if isinstance(self._data_, (dict, tuple, list)):
            for item in items:
                item_path = list()
                item_path.append(item.text(0))
                
                parent = item.parent()
                
                while parent is not None:
                    item_path.append(parent.text(0))
                    parent = parent.parent()
                
                item_path.reverse()
                
                value = get_nested_value(self._data_, item_path[1:]) # because 1st item is the insivible root name
                
                values.append(value)
                
                item_paths.append(item_path[-1]) # object names
                
                full_item_paths.append(item_path)
                
            if len(values):
                if len(values) == 1:
                    obj = values[0]
                    #objname = strutils.str2symbol(item_paths[-1])
                    newWindow = bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier)
        
                    objname = " \u3009".join(full_item_paths[0])
                    
                    # NOTE: 2019-09-09 22:15:45
                    # cannot use the ScipyenWindow logic to fallback to showing
                    # the variable in console using "execute()" because the
                    # variable (or object) is NOT visible in user's workspace
                    # FIXME how to do this?
                    # WORKAROUND: for now, copy the variable to workspace and 
                    # go from there
                    self._scipyenWindow_.viewObject(obj, objname, 
                                                   newWindow=newWindow)
                    
                else:
                    for name, path, obj in zip(item_paths, full_item_paths, values):
                        objname = " > ".join(path)
                        self._scipyenWindow_.viewObject(obj, objname, 
                                                       newWindow=True)
    
    @safewrapper
    def _get_path_for_item_(self, item:QtWidgets.QTreeWidgetItem, 
                            external:bool = False):#, as_expression:bool=True):
        r"""Returns a tree (indexing) path to item, as a list of 'nodes'.
        
        This EXCLUDES the top level parent.
        
        Parameters:
        -----------
        item: QTreeWidgetItem
        
        as_expression:bool, optional (default is True)
        
        Returns:
        -------
        
        When as_expression is True (default):
        
            returns a str which can be eval()-ed AFTER prefixing it with the 
            name (symbol) bound to the top level hierarchical data collection 
            (which must exist in the namespace where eval() is called)
            
        
        When as_expression is False:
        
            returns a list of item names that compose the indexing path with
            increasing nesting depth.
        
        """
        from core.datatypes import is_namedtuple
        from core.datatypes import subarray_type_map
        self._subselections_.clear()
        
        leafSubSelection = list()
        widget = self.treeWidget.itemWidget(item, 0)
        
        if widget:
            # special case - this is a child item with a widget showing the 
            # contents of the data represented by the parent item!
            # ∴ the item's parent is the actual data we're after !
            leafSubSelection = self.treeWidget.getWidgetSelection(widget)
            pItem = item.parent()
            # element = pItem.data(0, QtCore.Qt.DisplayRole)
            # elementDataType = pItem.data(0, QtCore.Qt.UserRole)
            item = pItem # this is crucial 
            
        element = item.data(0, QtCore.Qt.DisplayRole)
        elementDataType = item.data(0, QtCore.Qt.UserRole)
        targetDataType = dataclasses.MISSING # gets the data type resulting from the accessor
            
        # print(f"{self.__class__.__name__}._get_path_for_item_: element = {element}")
        
        path_parts = [element] # the pathay from root to branch tip
        
        expr = [element] # elements of the expression used to access for the 
                         # object represented by the item;
                         # the access expression will be constructed with appropriate
                         # syntax for getitem getter, depening on the type of the parent
                         # object that contains or references the object represented
                         # by the item;
                         #
                         # if the dataViewer shows an object in the user namespace
                         # (most common situation) then one can simply call
                         # eval(accessexpr), where accessexpr is returned below
                         # as ``access``
                         
        p = item.parent()
        k: int = 0
        while p is not None:
            pdatatype = p.data(0, QtCore.Qt.UserRole)
            element = p.data(0, QtCore.Qt.DisplayRole)
            path_parts.append(element)
            expr.append(element)
            k += 1
            if pdatatype in (typing.Sequence, tuple, list, dict, deque, types.MappingProxyType):
                if is_namedtuple(pdatatype):
                    expr[k-1] = f".{expr[k-1]}"
                else:
                    expr[k-1] = f"[{expr[k-1]}]"
            else:
                expr[k-1] = f".{expr[k-1]}"
                
            p = p.parent()
                
        path_parts.reverse()
        expr.reverse()
        directAccess = True
        
        access = ("".join(expr) if external else "".join(expr[1:]) if len(expr)>1 else "", "", elementDataType, targetDataType)
        # print(f"access: {access}")
        
        if len(leafSubSelection):
            # contents can be EITHER a list of QModelIndex (from a table widget)
            # OR a list of strings
            # when a list of QModelIndex, we need to get their row & column
            # indexes (ATTENTION — these are in the context of the table widget)
            # and use them to construct access pathways for them
            
            # accessors for array-like data:
            # each accessor contains:
            # call: empty string, ".iloc" or ".as_array()"
            # row index: slice, or numpy array
            # col index: slice, or numpy array
            # higher index: Ellipsis or MISSING
            # row index, col index and Ellipsis to be packed between [] following the call
            # 
            elementAccess = list() 
            #
            accessList = list()
            # targetTypes = list()

            if isinstance(widget, (TableEditorWidget, SimpleTableWidget)) and (isinstance(s, QtCore.QModelIndex) for s in leafSubSelection):
                rowsSet = list(set(map(lambda i: i.row(), leafSubSelection)))
                
                cols_by_rows = dict((r, list(map(lambda i: i.column(), filter(lambda i: i.row() == r, leafSubSelection)))) for r in rowsSet)
                
                continuousRows = np.all(np.diff(list(cols_by_rows.keys()))==1)
                allContinuousColsPerRow = all(np.all(np.diff(cols)==1) for cols in cols_by_rows.values())
                minColsPerRow = list(map(lambda c: min(c), cols_by_rows.values()))
                maxColsPerRow = list(map(lambda c: max(c), cols_by_rows.values()))
                hasSameColumnRangeAcrossRows = allContinuousColsPerRow and np.all(np.diff(minColsPerRow) == 0) and np.all(np.diff(maxColsPerRow) == 0)
                hasContinuousSelection = continuousRows and hasSameColumnRangeAcrossRows
                
                if hasContinuousSelection:
                    firstRow = min(cols_by_rows.keys())
                    lastRow = max(cols_by_rows.keys())
                    # rowNdx = f"{slice(firstRow, lastRow+1)}"
                    rowNdx = slice(firstRow, lastRow+1)
                    firstCol = min(minColsPerRow)
                    lastCol = max(maxColsPerRow)
                    targetDataType = elementDataType
                    if issubclass(elementDataType, (pq.Quantity, pd.Series, pd.DataFrame)):
                        # just use the row indexing to get a signal slice of all channels
                        if firstCol == 0:
                            # CAUTION: first column (column 0) depicts the 
                            # signal's domain or row index of the Series/DataFrame !
                            # all continuous selection, here, implies that we take all
                            # channels => will generate a new signal when eval'ed
                            # elementAccess.append(f"[{rowNdx},:]")
                            elementAccess.append(("", rowNdx, slice(firstCol, lastCol+1), dataclasses.MISSING))
                        else:
                            # filter out column 0 (for the signal's domain) and 
                            # create colNdx to select channel data
                            # when eval'ed, will also generate a signal
                            channelCols = list(map(lambda cols: list(map(lambda c: c-1, cols)), cols_by_rows.values()))
                            # we know this is continuous and with same range across the rows
                            firstCol = min(list(map(lambda cols: min(cols), channelCols)))
                            lastCol = max(list(map(lambda cols: max(cols), channelCols)))
                            colNdx = f"{slice(firstCol, lastCol+1)}"
                            # elementAccess.append(f"[{rowNdx}, {colNdx}]")
                            elementAccess.append(("", rowNdx, colNdx, dataclasses.MISSING))
                    else: # generic ndarray or pd.Index
                        # colNdx = f"{slice(firstCol, lastCol+1)}"
                        colNdx = slice(firstCol, lastCol+1)
                        # elementAccess.append(f"[{rowNdx}, {colNdx}, ...]")
                        elementAccess.append(("", rowNdx, colNdx, Ellipsis))
                        
                else:
                    # use advanced indexing with integer arrays
                    rowNdx = np.array(list(cols_by_rows.keys()))
                    # if issubclass(elementDataType, (neo.core.dataobject.DataObject, pd.Series, pd.DataFrame)):        
                    if issubclass(elementDataType, pq.Quantity):
                        # filter out column 0 (for the signal's domain or the 
                        # row index of the Series/DataFrame) 
                        # create colNdx to select channel data
                        # when eval'ed, will also generate a signal
                        if issubclass(elementDataType, neo.core.dataobject.DataObject):
                            channelCols = list(map(lambda cols: list(map(lambda c: c-1, filter(lambda x: x>0, cols))), cols_by_rows.values()))
                            colNdx = np.array(channelCols).flatten()
                            hasDomainSelection = any(any(c==0 for c in cols) for cols in cols_by_rows.values())
                            if hasDomainSelection:
                                # elementAccess.append(f".as_array()[{rowNdx}, {colNdx}]") # include domain
                                elementAccess.append((".as_array()", rowNdx, colNdx, dataclasses.MISSING)) # include domain
                                if elementDataType in subarray_type_map:
                                    targetDataType = subarray_type_map[elementDataType]
                                else:
                                    targetDataType = pq.Quantity
                            else:
                                elementAccess.append((".as_array()", rowNdx, colNdx, dataclasses.MISSING))
                                # elementAccess.append(f".as_array()[{rowNdx}, {colNdx}]")
                                targetDataType = pq.Quantity
                        else:
                            elementAccess.append((".as_array()", rowNdx, colNdx, dataclasses.MISSING))
                            targetDataType = pq.Quantity
                            
                    elif issubclass(elementDataType, (pd.Series, pd.DataFrame)):
                        channelCols = list(map(lambda cols: list(map(lambda c: c-1, filter(lambda x: x>0, cols))), cols_by_rows.values()))
                        colNdx = np.array(channelCols).flatten()
                        # indexing is selected automatically, by rowNdx
                        elementAccess.append((".iloc", rowNdx, colNdx, dataclasses.MISSING))
                        # iloc syntax generates the return type dynamicslly (either DataFrame or Series)
                        targetDataType = dataclasses.MISSING 
                        # hasDomainSelection = any(any(c==0 for c in cols) for cols in cols_by_rows.values())
                        
                    else: # generic ndarray and pd.Index
                        channelCols = list(cols_by_rows.values())
                        colNdx = np.array(channelCols).flatten()
                        # colNdx = f"np.array({channelCols})"
                        elementAccess.append(("", rowNdx, colNdx, Ellipsis))
                        # elementAccess.append(f"[{rowNdx}, {colNdx}, ...]")
                        targetDataType = elementDataType

                for eAccess in elementAccess:
                    accessList.append((access[0], eAccess, elementDataType, targetDataType))
                directAccess = True
                
            elif isinstance(widget, (QtWidgets.QPlainTextEdit, QtWidgets.QTextEdit)) and all(isinstance(v, str) for v in leafSubSelection):
                self._subselections_.append("".join(leafSubSelection))
                accessList = [access]
                directAccess = False
        
        else:
            accessList = [access]
        # print(f"{self.__class__.__name__}._get_path_for_item_: path_parts = {path_parts}, expr = {expr}, access = {access}")
        return path_parts, accessList, directAccess
        
    @safewrapper
    def _export_data_items_(self, items:list[QtWidgets.QTreeWidgetItem], 
                            fullPathAsName:bool=False, path_only:bool=False):
        r"""Export data displayed by their corresponding items, to workspace.
        
        Parameters:
        ----------
        
        items: sequence of QTreeWidgetItem objects - typicaly, the selected 
            non-hidden QTreeWidgetItem items in the treeWidget.
            
        fullPathAsName: bool (optional, default is False)
            When True, each object described by the item in items will be bound
            to a symbol in the workspace formed from the concatenation of the
            indexing path elements from top level (root) to the the object being
            exported.
            
            When False, the exported objects will be bound to a symbol in the
            workspace, formed by the item's display text.
        
        """
        
        names = list()
        objects = list()
        
        for item in items:
            try:
                path, accessList, direct = self._get_path_for_item_(item, path_only)
            except:
                exc = sys.exception()
                msg = "".join(traceback.format_exception_only(exc))
                self.errorMessage(type(exc).__name__, msg)
                raise
            # print(f"{self.__class__.__name__}_export_data_items_ path = {path}, access = {accessList}")
            
            if len(path) == 0:
                continue
            
            if fullPathAsName:
                # print(f"{self.__class__.__name__}_export_data_items_ full_path = {path}")
                name = strutils.str2symbol("_".join(path))
                
            else:
                name = strutils.str2symbol(path[-1])
                
            #print("name", name)
            src = self._obj_cache_[self._cache_index_][1]
            
            try:
                if direct:
                    if len(accessList) > 1:
                        for k, statement, eAccess, oType, tType in enumerate(accessList):
                            # print(f"statement: {statement}, eAccess: {eAccess}, oType: {oType}, tType: {tType}")
                            if len(eAccess):
                                call, rowNdx, colNdx, hiNdx = eAccess
                                rNdx = f"np.array({list(rowNdx)})" if isinstance(rowNdx, np.ndarray) else f"{rowNdx}"
                                cNdx = f"np.array({list(colNdx)})" if isinstance(colNdx, np.ndarray) else f"{colNdx}"
                                accstmt = f"{call}[{rNdx}, {cNdx}]"
                                if hiNdx is not dataclasses.MISSING:
                                    if hiNdx == Ellipsis:
                                        hNdx = ", ..."
                                    elif isinstance(hiNdx, np.ndarray):
                                        hNdx = f"np.array({list(hiNdx)})"
                                    elif isinstance(hiNdx, slice):
                                        hNdx = f"{hiNdx}"
                                    accstmt = accstmt + f"{hNdx}"
                                if path_only:
                                    obj = f"{statement}{accstmt}"
                                else:
                                    obj = eval(f"src{statement}{accstmt}")
                                    # if issubclass(oType, pq.Quantity):
                                    if not isinstance(obj, oType):
                                        if tType is not dataclasses.MISSING:
                                            srcObj = eval(f"src{statement}")
                                            if tType is pq.Quantity and oType is pq.Quantity:
                                                obj = obj * srcObj.units
                                            elif tType in (IrregularlySampledDataSignal, neo.IrregularlySampledSignal):
                                                domain = srcObj.times[rowNdx]
                                                obj = tType(times = domain, signal=obj,
                                                            units = srcObj.units,
                                                            time_units = srcObj.times.units)
                            else:
                                if path_only:
                                    obj = f"{statement}"
                                else:
                                    obj = eval(f"src{statement}")
                            objects.append(obj)
                            # objects.append(eval(f"src{statement}"))
                            names.append(f"{name}_{k}")
                    else:
                        statement, eAccess, oType, tType = accessList[0]
                        # print(f"statement: {statement}, eAccess: {eAccess}, oType: {oType}, tType: {tType}")
                        if len(eAccess):
                            # unpack accessor elements
                            call, rowNdx, colNdx, hiNdx = eAccess
                            rNdx = f"np.array({list(rowNdx)})" if isinstance(rowNdx, np.ndarray) else f"{rowNdx}"
                            cNdx = f"np.array({list(colNdx)})" if isinstance(colNdx, np.ndarray) else f"{colNdx}"
                            accstmt = f"{call}[{rNdx}, {cNdx}]"
                            if hiNdx is not dataclasses.MISSING:
                                if hiNdx == Ellipsis:
                                    hNdx = ", ..."
                                elif isinstance(hiNdx, np.ndarray):
                                    hNdx = f"np.array({list(hiNdx)})"
                                elif isinstance(hiNdx, slice):
                                    hNdx = f"{hiNdx}"
                                accstmt = accstmt + f"{hNdx}"
                                
                            # print(f"accstmt: {accstmt}")
                            if path_only:
                                obj = f"{statement}{accstmt}"
                            else:
                                obj = eval(f"src{statement}{accstmt}")
                                
                                if not isinstance(obj, oType):
                                    if tType is not dataclasses.MISSING:
                                        srcObj = eval(f"src{statement}")
                                        if tType is pq.Quantity and oType is pq.Quantity:
                                            obj = obj * srcObj.units
                                        elif tType in (IrregularlySampledDataSignal, neo.IrregularlySampledSignal):
                                            domain = srcObj.times[rowNdx]
                                            obj = tType(times = domain, signal=obj,
                                                        units = srcObj.units,
                                                    time_units = srcObj.times.units)
                        else:
                            if path_only:
                                obj = f"{statement}"
                            else:
                                obj = eval(f"src{statement}")
                        objects.append(obj)
                        names.append(name)
                else:
                    if path_only:
                        if len(accessList) > 1:
                             for k, statement, eAccess, oType, tType in enumerate(accessList):
                                obj = f"{statement}"
                                objects.append(obj)
                                names.append(f"{name}_{k}")
                                
                        elif len(accessList) == 1:
                            statement, eAccess, oType, tType = accessList[0]
                            obj = f"{statement}"
                            objects.append(obj)
                            names.append(f"{name}_{k}")
                            
                    else:
                        if len(self._subselections_):
                            if len(self._subselections_) > 1:
                                for k, sel in self._subselections_:
                                    objects.append(sel)
                                    names.append(f"{name}_{k}")
                            else:
                                object.append(self._subselections_[0])
                                names.append(name)
            except:
                exc = sys.exception()
                # traceback.print_exc()
                msg = "".join(traceback.format_exception_only(exc))
                self.errorMessage(type(exc).__name__, msg)
                raise
            # names.append(name)
            # objects.append(obj)
            
        if len(objects) == 0:
            return
        
        if path_only:
            return objects
        
        if len(objects) == 1:
            dlg = quickdialog.QuickDialog(self, "Copy to workspace")
            namePrompt = quickdialog.StringInput(dlg, "Data name:")
            namePrompt.variable.setClearButtonEnabled(True)
            namePrompt.variable.redoAvailable=True
            namePrompt.variable.undoAvailable=True
            
            namePrompt.setText(names[0])
            
            if dlg.exec() == QtWidgets.QDialog.Accepted:
                newVarName = namePrompt.text()
                # FIXME 2021-10-03 22:17:29 this is really buggy!
                #newVarName = validate_varname(namePrompt.text(), self._scipyenWindow_.workspace)
                
                self._scipyenWindow_.assignToWorkspace(newVarName, objects[0], check_name=False)
                
        else:
            for name, obj in zip(names, objects):
                self._scipyenWindow_.assignToWorkspace(name, obj, check_name=False)

    def _collapse_expand_Recursive(self, item, expand=False, current=True):
        if expand:
            fn = self.treeWidget.expandItem
        else:
            fn = self.treeWidget.collapseItem
            
        for k in range(item.childCount()):
            self._collapse_expand_Recursive(item.child(k), expand=expand)
            
        if current:
            fn(item)
        
