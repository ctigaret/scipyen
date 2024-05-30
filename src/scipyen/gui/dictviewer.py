# -*- coding: utf-8 -*-
"""
Qt5-based viewer window for dict and subclasses
"""

#### BEGIN core python modules
from __future__ import print_function

import os, warnings, types, traceback, itertools, inspect, dataclasses, numbers
from collections import deque
from dataclasses import MISSING
import math
#### END core python modules

#### BEGIN 3rd party modules
from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import Signal, Slot, Property
# from qtpy.QtCore import Signal, Slot, QEnum, Property
# from qtpy.uic import loadUiType as __loadUiType__

# from PyQt5 import QtCore, QtGui, QtWidgets
# from PyQt5.QtCore import Signal, Slot, QEnum, Q_FLAGS, Property
# # from PyQt5.uic import loadUiType as __loadUiType__

from pyqtgraph import (DataTreeWidget, TableWidget, )
#from pyqtgraph.widgets.TableWidget import _defersort

import neo
import quantities as pq
import numpy as np
import pandas as pd
#### END 3rd party modules

#### BEGIN pict.core modules
import core.datatypes  

import imaging.axiscalibration
from imaging.axiscalibration import AxesCalibration

# import imaging.scandata
# from imaging.scandata import (ScanData, AnalysisUnit)

from core.triggerprotocols import TriggerProtocol
from core.triggerevent import (TriggerEvent, TriggerEventType)

import core.datasignal
from core.datasignal import (DataSignal, IrregularlySampledDataSignal)

from core import xmlutils, strutils

from core.workspacefunctions import validate_varname

#from core.utilities import (get_nested_value, set_nested_value, counter_suffix, )

from core.utilities import NestedFinder

from core.prog import (safeWrapper, safeGUIWrapper, )

from core.traitcontainers import (DataBag, DataBagTraitsObserver,)

# from gui.tableeditor import (TableEditorWidget, TabularDataModel,)

from gui.widgets.interactivetreewidget import InteractiveTreeWidget
from gui.widgets.tablewidget import SimpleTableWidget
from gui.widgets.tableeditorwidget import (TableEditorWidget, TabularDataModel)

#### END pict.core modules

#### BEGIN pict.gui modules
from .scipyenviewer import ScipyenViewer #, ScipyenFrameViewer
from . import quickdialog

from . import resources_rc
# from . import icons_rc
#### END pict.gui modules

# NOTE: 2022-12-25 23:08:51
# needed for the new plugins framework
# This plugins does not install a custom menu, but DOES provide a viewer type
# hence we flag it using __scipyen_plugin__ (we could have defined
# init_scipyen_plugin instead, to return an empty dict)
__scipyen_plugin__ = None

class DataViewer(ScipyenViewer):
    """Viewer for hierarchical (nesting) collection types.
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
                        neo.core.baseneo.BaseNeo:0,
                        ScanData:0, 
                        TriggerProtocol:0}
    
    # view_action_name = "Object"
    
    def __init__(self, data: (object, type(None)) = None, parent: (QtWidgets.QMainWindow, type(None)) = None, ID:(int, type(None)) = None,  win_title: (str, type(None)) = None, doc_title: (str, type(None)) = None, useTableEditor:bool = True, predicate = None, hideRoot:bool=False, *args, **kwargs):
        """
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
    
        hideRoot: When false (default) the root of the tree hierarchy is displayed.
    
        *args, **kwargs ⇒ passed on to ScipyenViewer superclass.
    
        """
        self._useTableEditor_ = useTableEditor
        
        if inspect.isfunction(predicate):
            self.predicate = predicate
        else:
            self.predicate=None
            
        self.hideRoot = hideRoot
        
        self._obj_cache_ = list()
        self._cache_index_ = 0
        
        self._top_title_ = ""
        
        self._dataTypeStr_ = None
        
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
        
    def _set_data_(self, data:object, predicate=None, hideRoot=False, *args, **kwargs):
        """
        Display new data
        # TODO 2019-09-14 10:16:03: NOTE: 2021-10-03 13:10:00 SCRAP THAT
        # expand this to other hierarchical containers including those in
        # the neo package (neo.Block, neo.Segment, neo.Unit, etc) and in the
        # datatypes module (ScanData)
        # FIXME you may want to override some of the pyqtgraph's DataTreeWidget
        # to treat other data types as well.
        # Solutions to be implemented in the InteractiveTreeWidget in this module
        """
        #if not isinstance(data, dict):
            #data = data.__dict__
        
        if inspect.isfunction(predicate):
            self.predicate=predicate
            
        self.hideRoot = hideRoot
        
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
                                    dataTypeStr=type(obj_tuple[1]).__name__, 
                                    # dataTypeStr=self._dataTypeStr_, 
                                    hideRoot=self.hideRoot)
            self.docTitle = obj_tuple[0]
            
            for k in range(self.treeWidget.topLevelItemCount()):
                self._collapse_expand_Recursive(self.treeWidget.topLevelItem(k), current=False)

    @Slot()
    @safeWrapper
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
            
        #if self.treeWidget.topLevelItemCount() == 1:
            #self.treeWidget.topLevelItem(0).setText(0, top_title)
            
        # for k in range(self.treeWidget.topLevelItemCount()):
        #     self._collapse_expand_Recursive(self.treeWidget.topLevelItem(k), current=False)
            #self._collapseRecursive_(self.treeWidget.topLevelItem(k), collapseCurrent=False)

    @Slot(QtWidgets.QTreeWidgetItem, int)
    @safeWrapper
    def slot_itemDoubleClicked(self, item, column):
        from core.utilities import get_nested_value
        if self._scipyenWindow_ is None:
            return
        
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
    @safeWrapper
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
        
        
    @safeWrapper
    def getSelectedPaths(self):
        items = self.treeWidget.selectedItems()
        
        if len(items) == 0:
            return
        
        item_paths = list()
        
        top_title = self.treeWidget.top_title
        
        if isinstance(self._data_, NestedFinder.nesting_types):
            for item in items:
                item_path = self._get_path_for_item_(item)
                
                expr = NestedFinder.paths2expression(self._data_, item_path)
                
                if len(top_title.strip()) > 0 and top_title not in (os.path.sep, "/"):
                    expr = top_title+expr
                
                item_paths.append(expr)
                
        return item_paths
        
    @safeWrapper
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
            
    @Slot()
    @safeWrapper
    def slot_collapseAll(self):
        for k in range(self.treeWidget.topLevelItemCount()):
            self._collapse_expand_Recursive(self.treeWidget.topLevelItem(k), current=False)

    
    @Slot()
    @safeWrapper
    def slot_expandAll(self):
        for k in range(self.treeWidget.topLevelItemCount()):
            self._collapse_expand_Recursive(self.treeWidget.topLevelItem(k), expand=True, current=False)
        
    @Slot()
    @safeWrapper
    def slot_copyPaths(self):
        if self._scipyenWindow_ is None:
            return
        
        item_paths = self.getSelectedPaths()
        self.exportPathsToClipboard(item_paths)

    @Slot()
    @safeWrapper
    def slot_exportItemPathToConsole(self):
        if self._scipyenWindow_ is None:
            return
        
        item_paths = self.getSelectedPaths()
        self.exportPathsToClipboard(item_paths)
        self._scipyenWindow_.console.paste()
                
    @Slot()
    @safeWrapper
    def slot_exportItemDataToWorkspace(self):
        """Exports data from currently selected items to the workspace.
        
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
    @safeWrapper
    def slot_editItemData(self):
        # TODO: 2022-10-11 13:45:35
        from core.utilities import get_nested_value
        pass
        items = self.treeWidget.selectedItems()
        
        if len(items) != 1:
            return
        
        
    @Slot()
    @safeWrapper
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
    
    
    @safeWrapper
    def _parse_item_(self, item):
        item_name = item.text(0)
        
        if len(item_name.strip()) == 0:
            return None
        
        item_type_str = item.toolTip(0).replace("key / index type: ", "")
        
        return item_name if (item_type_str == "str" or len(item_type_str.strip())==0) else eval("%s(%s)" % (item_type_str, item_name))
    
    @safeWrapper
    def _get_path_for_item_(self, item:QtWidgets.QTreeWidgetItem):#, as_expression:bool=True):
        """Returns a tree (indexing) path to item, as a list of 'nodes'.
        
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
            
        
        When as_expression if False:
        
            returns a list of item names that compose the indexing path with
            increasing nesting depth.
        
        """
        item_path = list()
        
        ndx = self._parse_item_(item)
        
        if ndx is not None:
            item_path.append(ndx)

        parent = item.parent()
        
        while parent is not None:
            if parent.parent() is not None:
                ndx = self._parse_item_(parent)
                if ndx is not None:
                    item_path.append(ndx)
                
            parent = parent.parent()

        item_path.reverse()
        
        return item_path
    
    @safeWrapper
    def _export_data_items_(self, items, fullPathAsName=False):
        """Export data displayed by their corresponding items, to workspace.
        
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
            path = self._get_path_for_item_(item)
            #print("\n_export_data_items_ path", path)
            
            if len(path) == 0:
                continue
            
            if fullPathAsName:
                # NOTE: 2021-08-17 09:35:10 the order is important:
                # 1) cannot modify path here because it will be used to get
                # the object -> use a temporary full path prepended with top 
                # level item if available
                #
                # 2) cannot get the object first then figure out the name because
                # NestedFinder.getvalue() consumes the path (so by the time name
                # is built the path will be empty)
                #
                # in either case we need a temporary list - I guess the runtime
                # penaly is minor
                top_title = self.treeWidget.top_title
                if isinstance(top_title, str) and len(top_title.strip()):
                    full_path = [p for p in path]
                    full_path.insert(0, top_title)
                    
                else:
                    full_path = path
                    
                name = strutils.str2symbol("_".join(["%s" % s for s in full_path]))
                
            else:
                name = strutils.str2symbol("%s" % path[-1])
                
            #print("name", name)
            src = self._obj_cache_[self._cache_index_][1]
            if self.treeWidget.has_dynamic_private:
                objs = [getattr(src,path[-1], None)]
            else:
                # objs = NestedFinder.getvalue(self._data_, path, single=True)
                objs = NestedFinder.getvalue(src, path, single=True)
            
            if len(objs) == 0:
                continue
            
            if len(objs) > 1:
                raise RuntimeError("More than one value was returned")
                
            names.append(name)
            objects += objs
                
        
        if len(objects) == 0:
            return
        
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
        
