# -*- coding: utf-8 -*-
"""
Qt5-based viewer window for dict and subclasses
TODO
"""

#### BEGIN core python modules
from __future__ import print_function

import os, warnings, types, traceback, itertools
from collections import deque
#### END core python modules

#### BEGIN 3rd party modules
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__

from pyqtgraph import (DataTreeWidget, TableWidget, )
#from pyqtgraph.widgets.TableWidget import _defersort

import neo
import numpy as np
import pandas as pd
#### END 3rd party modules

#### BEGIN pict.core modules
import core.datatypes as dt

import imaging.axiscalibration
from imaging.axiscalibration import AxisCalibration

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

from core.prog import (safeWrapper, safeGUIWrapper, )

from core.traitcontainers import (DataBag, DataBagTraitsObserver,)

from gui.tableeditor import (TableEditorWidget, TabularDataModel,)

#### END pict.core modules

#### BEGIN pict.gui modules
from .scipyenviewer import ScipyenViewer #, ScipyenFrameViewer
from . import quickdialog
from . import resources_rc
#### END pict.gui modules

class ScipyenTableWidget(TableWidget): # TableWidget imported from pyqtgraph
    """Another simple table widget, which allows zero-based row/column indices.
    
    Really DEPRECATED.
    
    Kept for diversity and inclusion but gui.tableeditor.TableEditorWidget is
    much more useful. 
    
    """
    def __init__(self, *args, natural_row_index=False, natural_col_index=False, **kwds):
        self._pythonic_col_index = not natural_col_index
        self._pythonic_row_index = not natural_row_index
        super().__init__(*args, **kwds)
        
    def setData(self, data):
        super().setData(data)
        if isinstance(data, (np.ndarray, tuple, list, deque)):
            if self._pythonic_col_index:
                self.setHorizontalHeaderLabels(["%d"%i for i in range(self.columnCount())])
                
            if self._pythonic_row_index:
                self.setVerticalHeaderLabels(["%d"%i for i in range(self.rowCount())])
        
    def iterFirstAxis(self, data):
        """Overrides TableWidget.iterFirstAxis.
        
        Avoid exceptions when data is a dimesionless array.
        
        In the original TableWidget from pyqtgraph this method fails when data 
        is a dimesionless np.ndarray (i.e. with empty shape and ndim = 0).
        
        This kind of arrays unfortunately can occur when creating a numpy
        array (either directly in the numpy library, or in the python Quantities
        library):
        
        Example 1 - using python quantities:
        ------------------------------------
        
        In: import quantities as pq
        
        In: a = 1*pq.s
        
        In: a
        Out: array(1.)*s
        
        In: a.shape
        Out: ()
        
        In: a.ndim
        Out: 0
        
        In: a[0]
        IndexError: too many indices for array: array is 0-dimensional, but 1 were indexed
        
        Example 2 - directly creating a numpy array:
        --------------------------------------------
        
        In: b = np.array(1)
        
        In: b
        Out: array(1)
        
        In: b.shape
        Out: ()
        
        In: b.ndim
        Out: 0
        
        In: b[0]
        IndexError: too many indices for array: array is 0-dimensional, but 1 were indexed
        
        This will cause self.iterFirstAxis(a) to raise 
        IndexError: tuple index out of range
        
        
        HOWEVER, the value of the unique element of the array can be retrieved
        by using its "take" method:
        
        In: a.take(0)
        Out: 1.0
        
        In: b.take(0)
        Out: 1

        
        """
        if len(data.shape) == 0 or data.ndim == 0:
            yield(data.take(0))
            
        else:
            for i in range(data.shape[0]):
                yield data[i]

class InteractiveTreeWidget(DataTreeWidget):
    """Extends pyqtgraph.widgets.DataTreeWidget with the following:
    1. Support for custom context menu to pyqtgraph.DataTreeWidget.
    2. Use Scipyen gui.tableeditor.TableEditorWidget instead of pyqtgraph.TableWidget
    3. Support for dict data with a mixture of key types (any hashable object)
    4. Support for circular references to hierarchical data objects (subsequent
        references ot the same object are NOT traversed; instead, a path to the 
        first encountered reference - in depth-first order - is displayed)
    
    """
    def __init__(self, *args, **kwargs):
        self._visited_ = dict()
        self.top_title = "/"
        super(InteractiveTreeWidget, self).__init__(*args, **kwargs)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.headerItem().setToolTip(0, "Key or index of child data.\nThe type of the key or index is shown in their tooltip.")
        self.headerItem().setToolTip(1, "Type of child data mapped to a key or index.\nAdditional type information is shown in their tooltip.")
        self.headerItem().setToolTip(2, "Value of child data, or its length\n(when data is a nested collection).\nNumpy arrays ar displayed as a table")
        
    def setData(self, data, top_title:str = ""):
        self._visited_.clear()
        if len(top_title.strip()) == 0:
            self.top_title = "/"
        else:
            self.top_title = top_title
        super().setData(data)
        #print(self.topLevelItemCount())
        #if self.topLevelItemCount() > 1 or len(top_title.strip()) == 0:
            #top_title = "/"
        self.topLevelItem(0).setText(0, self.top_title)
        #self.top_title = top_title
    
    def parse(self, data):#, visited=False):
        """
        Given any python object, return:
        * type
        * a short string representation
        * a dict of sub-objects to be parsed
        * optional widget to display as sub-node
        * NOTE 2021-07-24 14:13:10 CMT
        * keytype: the type of the key (for dict data) or of the index (for sequences)
            The latter is useful for namedtuples
            
        
        NOTE: 2020-10-11 13:48:51
        override superclass parse to use ScipyenTableWidget instead
        
        """
        from pyqtgraph.widgets.DataTreeWidget import HAVE_METAARRAY
        from pyqtgraph.pgcollections import OrderedDict
        from pyqtgraph.python2_3 import asUnicode
        from core.datatypes import is_namedtuple
        

        # defaults for all objects
        typeStr = type(data).__name__
        typeTip = ""
        
        if typeStr == "instance":
            typeStr += ": " + data.__class__.__name__
            typeTip = data.__class__.__name__
            
        elif typeStr == "type":
            typeStr = data.__name__
            typeTip = str(data)
            
        if is_namedtuple(data):
            typeTip = "(namedtuple)"
            
        widget = None
        desc = ""
        childs = {}
        
        #print("typeStr", typeStr, "typeTip", typeTip)
        
        # type-specific changes
        if isinstance(data, NestedFinder.nesting_types):
            if id(data) in self._visited_.keys():
                #print(self._visited_[id(data)])
                objtype = self._visited_[id(data)][0]
                path = "/".join(list(self._visited_[id(data)][1]))
                if len(path.strip()) == 0:
                    full_path = self.top_title
                else:
                    if self.top_title == "/":
                        full_path = "/" + path
                    else:
                        full_path = "/".join([self.top_title, path])
                desc = "<reference to %s at %s >" % (objtype, full_path)
            else:
                if isinstance(data, dict):
                    desc = "length=%d" % len(data)
                    if isinstance(data, OrderedDict):
                        childs = data
                        
                    else:
                        #childs = OrderedDict(sorted(data.items())) # does not support mixed key types!
                        # NOTE: 2021-07-20 09:52:34
                        # dict objects with mixed key types cannot be sorted
                        # therefore we resort to an indexing vector
                        ndx = [i[1] for i in sorted((str(k[0]), k[1]) for k in zip(data.keys(), range(len(data))))]
                        items = [i for i in data.items()]
                        childs = OrderedDict([items[k] for k in ndx])
                        
                elif isinstance(data, (list, tuple, deque)):
                    desc = "length=%d" % len(data)
                    # NOTE: 2021-07-24 14:57:02
                    # accommodate namedtuple types
                    if is_namedtuple(data):
                        childs = data._asdict()
                    else:
                        childs = OrderedDict(enumerate(data))
            
        elif HAVE_METAARRAY and (hasattr(data, 'implements') and data.implements('MetaArray')):
            childs = OrderedDict([
                ('data', data.view(np.ndarray)),
                ('meta', data.infoCopy())
            ])
            
        elif isinstance(data, pd.DataFrame):
            desc = "length=%d, columns=%d" % (len(data), len(data.columns))
            #model = TabularDataModel()
            #table = TableEditorWidget(model, self)
            #widget = table
            widget = TableEditorWidget(parent=self)
            signalBlocker = QtCore.QSignalBlocker(widget.tableView)
            widget.tableView.model().setModelData(data)
            widget.setMaximumHeight(200)
            widget.readOnly=True
            
        elif isinstance(data, pd.Series):
            desc = "length=%d, dtype=%s" % (len(data), data.dtype)
            #model = TabularDataModel()
            #table = TableEditorWidget(model, self)
            #widget = table
            widget = TableEditorWidget(parent=self)
            signalBlocker = QtCore.QSignalBlocker(widget.tableView)
            widget.tableView.model().setModelData(data)
            widget.setMaximumHeight(200)
            widget.readOnly=True
            
        elif isinstance(data, pd.Index):
            desc = "length=%d" % len(data)
            widget = TableEditorWidget(parent=self)
            signalBlocker = QtCore.QSignalBlocker(widget.tableView)
            widget.tableView.model().setModelData(data)
            widget.setMaximumHeight(200)
            widget.readOnly=True
            
            #widget = QtGui.QPlainTextEdit(asUnicode(data))
            #widget.setMaximumHeight(200)
            #widget.setReadOnly(True)
            
        elif isinstance(data, np.ndarray):
            desc = "shape=%s dtype=%s" % (data.shape, data.dtype)
            widget = TableEditorWidget(parent=self)
            signalBlocker = QtCore.QSignalBlocker(widget.tableView)
            widget.tableView.model().setModelData(data)
            widget.setMaximumHeight(200)
            widget.readOnly=True
            
            #table = ScipyenTableWidget()
            #table.setData(data)
            #table.setMaximumHeight(200)
            #widget = table
            
        elif isinstance(data, types.TracebackType):  ## convert traceback to a list of strings
            frames = list(map(str.strip, traceback.format_list(traceback.extract_tb(data))))
            widget = QtGui.QPlainTextEdit(asUnicode('\n'.join(frames)))
            widget.setMaximumHeight(200)
            widget.setReadOnly(True)
            
        else:
            desc = asUnicode(data)
        
        return typeStr, desc, childs, widget, typeTip
    
    def buildTree(self, data, parent, name="", nameTip = "", hideRoot=False, path=()):
        from pyqtgraph.python2_3 import asUnicode
        
        # NOTE: 2021-07-24 13:15:38
        # throughout this function 'node' is a QtGui.QTreeWidgetItem
        # the root node is named after the symbol of the nested data structure
        # shown by DataViewer, or by _docTitle_, hence it is always a str
        #
        # Child nodes are either dict keys, or int indices in iterables; this 
        # can lead to confusion e.g., between different types of dict keys that 
        # are represented by similar str for display purpose.
        #
        # For example, a dict key "2" (a str) and a dict key 2 (an int) are both
        # represented as the str "2" (both str and int are hashable, hence they
        # can be used as dict keys). 
        #
        # Consider the contrived example of a dict with two key/value pairs:
        # 
        # contrived = {2:"text", "2": "another text"}
        #
        # Since the keys appear identical in the InteractiveTreeWidget (as the 
        # str '2') a user who wants to retrieve the value "text" from the dict 
        # s/he has no way to know whether to type 'contrived[2]' (the correct
        # choice in this example) or 'contrived["2"]' unless they try first, 
        # with a 50% chance to get the wrong value
        #
        # For this reason we endow the 'key/index' column with a tooltip stating
        # the type of the key (e.g. str or int, in this case)
        #
        # The only exception to this is the root node where the "name" is always
        # "str"
        
        # NOTE: 2021-08-15 14:43:54
        # node is a QTreeWidgetItem constructed on three strings, each one to
        # be displayed in its corresponding column, as follows:
        # string 0 -> "key/index" column: 'name' (displayed key or index)
        # string 1 -> "type"      column: data type
        # string 2 -> "value"     column: a description string:
        #                           length (for collections)
        #                           value  (for str)
        #                           etc
        if hideRoot:
            node = parent
        else:
            node = QtGui.QTreeWidgetItem([name, "", ""])
            parent.addChild(node)
        
        # record the path to the node so it can be retrieved later
        # (this is used by DiffTreeWidget)
        
        # NOTE: 2021-08-15 14:41:32
        # self.nodes is a dict
        # path is a tuple (as index branch path) - this is hashable hence usable
        # as dict key
        self.nodes[path] = node
        
        typeStr, desc, childs, widget, typeTip = self.parse(data)
        
        node.setToolTip(0, nameTip)
        node.setText(1, typeStr)
        node.setToolTip(1, typeTip)
        node.setText(2, desc)
        
        if isinstance(data, NestedFinder.nesting_types):
            if id(data) not in self._visited_.keys():
                self._visited_[id(data)] = (typeStr, path)
            
        # Truncate description and add text box if needed
        if len(desc) > 100:
            desc = desc[:97] + '...'
            if widget is None:
                widget = QtGui.QPlainTextEdit(asUnicode(data))
                widget.setMaximumHeight(200)
                widget.setReadOnly(True)
        
        # Add widget to new subnode
        if widget is not None:
            self.widgets.append(widget)
            subnode = QtGui.QTreeWidgetItem(["", "", ""])
            node.addChild(subnode)
            self.setItemWidget(subnode, 0, widget)
            self.setFirstItemColumnSpanned(subnode, True)
            
        # recurse to children
        for key, data in childs.items():
            if isinstance(key, type):
                keyrepr = key.__name__
                keytip = asUnicode(key)
                
            elif type(key)._name__ == "instance":
                keyrepr = key.__class__.__name__
                keytip = asUnicode(key)
                
            else:
                keyrepr = asUnicode(key)
                keytip = type(key).__name__
                
            keyTypeTip = "key / index type: %s" % keytip
            self.buildTree(data, node, keyrepr, keyTypeTip, path=path+(key,))

        
class DataViewer(ScipyenViewer):
    """Viewer for hierarchical (nesting) collection types.
    These can be: (nested) dictionaries, lists, tuples.
    Numpy arrays and pandas data types, although collection data types, are
    considered "leaf" objects.
    
    Changelog:
    ---------
    2019: Uses InteractiveTreeWidget which inherits from pyqtgraph DataTreeWidget 
    and in turn inherits from QTreeWidget.
    2021-08-15 22:51:43: support for circular references to hierarchical data types
        e.g., a dict can contain a key mapped to itself
    """
    sig_activated = pyqtSignal(int)
    closeMe  = pyqtSignal(int)
    signal_window_will_close = pyqtSignal()
    
    # TODO: 2019-11-01 22:44:34
    # implement viewing of other data structures (e.g., viewing their __dict__
    # for the generic case, )
    supported_types = (dict, list, tuple,
                        AnalysisUnit,
                        AxisCalibration,
                        neo.core.baseneo.BaseNeo,
                        ScanData, 
                        TriggerProtocol)
    
    view_action_name = "Object"
    
    def __init__(self, data: (object, type(None)) = None, parent: (QtWidgets.QMainWindow, type(None)) = None, 
                 pWin: (QtWidgets.QMainWindow, type(None))= None, ID:(int, type(None)) = None,
                 win_title: (str, type(None)) = None, doc_title: (str, type(None)) = None,
                 *args, **kwargs) -> None:
        super().__init__(data=data, parent=parent, pWin=pWin, win_title=win_title, doc_title = doc_title, ID=ID, *args, **kwargs)
        
    def _configureUI_(self):
        self.treeWidget = InteractiveTreeWidget(parent = self)
        
        self.treeWidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        
        # TODO implement dragging from here to the workspace
        self.treeWidget.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        self.treeWidget.setDragEnabled(True)
        
        self.treeWidget.customContextMenuRequested[QtCore.QPoint].connect(self.slot_customContextMenuRequested)
        
        self.treeWidget.itemDoubleClicked[QtWidgets.QTreeWidgetItem, int].connect(self.slot_itemDoubleClicked)
        
        self.setCentralWidget(self.treeWidget)
        
        self.toolBar = QtWidgets.QToolBar("Main", self)
        self.toolBar.setObjectName("%s_Main_Toolbar" % self.__class__.__name__)
        
        #refreshAction = self.toolBar.addAction(QtGui.QIcon(":/images/view-refresh.svg"), "Refresh")
        refreshAction = self.toolBar.addAction(QtGui.QIcon.fromTheme("view-refresh"), "Refresh")
        refreshAction.triggered.connect(self.slot_refreshDataDisplay)
        
        collapseAllAction = self.toolBar.addAction(QtGui.QIcon.fromTheme("collapse-all"), "Collapse All")
        collapseAllAction.triggered.connect(self.slot_collapseAll)
        
        expandAllAction = self.toolBar.addAction(QtGui.QIcon.fromTheme("expand-all"), "Expand All")
        expandAllAction.triggered.connect(self.slot_expandAll)
        
        self.addToolBar(QtCore.Qt.TopToolBarArea, self.toolBar)
        
    def _set_data_(self, data:object, *args, **kwargs):
        """
        Display new data
        # TODO 2019-09-14 10:16:03:
        # expand this to other hierarchical containers including those in
        # the neo package (neo.Block, neo.Segment, neo.Unit, etc) and in the
        # datatypes module (ScanData)
        # FIXME you may want to override some of the pyqtgraph's DataTreeWidget
        # to treat other data types as well.
        # Solutions to be implemented in the InteractiveTreeWidget in this module
        """
        #print(data)
        
        if data is not self._data_:
            self._data_ = data
            
            top_title = self._docTitle_ if (isinstance(self._docTitle_, str) and len(self._docTitle_.strip())) else "/"
            
            self.treeWidget.setData(self._data_, top_title)
            
            #if self.treeWidget.topLevelItemCount() == 1:
                #self.treeWidget.topLevelItem(0).setText(0, top_title)
                
            for k in range(self.treeWidget.topLevelItemCount()):
                self._collapse_expand_Recursive(self.treeWidget.topLevelItem(k), current=False)
                #self._collapseRecursive_(self.treeWidget.topLevelItem(k), collapseCurrent=False)
                
        if kwargs.get("show", True):
            self.activateWindow()

    @pyqtSlot()
    @safeWrapper
    def slot_refreshDataDisplay(self):
        top_title = self._docTitle_ if (isinstance(self._docTitle_, str) and len(self._docTitle_.strip())) else "/"
        
        self.treeWidget.setData(self._data_, top_title)

        #if self.treeWidget.topLevelItemCount() == 1:
            #self.treeWidget.topLevelItem(0).setText(0, top_title)
            
        for k in range(self.treeWidget.topLevelItemCount()):
            self._collapse_expand_Recursive(self.treeWidget.topLevelItem(k), current=False)
            #self._collapseRecursive_(self.treeWidget.topLevelItem(k), collapseCurrent=False)

    @pyqtSlot(QtWidgets.QTreeWidgetItem, int)
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
        
        obj = get_nested_value(self._data_, item_path[1:]) # because 1st item is the insivible root name
        
        #objname = strutils.str2symbol(item_path[-1])
        objname = " > ".join(item_path)
        
        newWindow = bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier)
        
        #useSignalViewerForNdArrays = bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier)
        
        self._scipyenWindow_.viewObject(obj, objname, 
                                       newWindow=newWindow)
        
        
    @pyqtSlot(QtCore.QPoint)
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
        
        cm.popup(self.treeWidget.mapToGlobal(point), copyItemData)
        
    #@safeWrapper
    #def getSelectedPathsExpr(self):
        #items = self.treeWidget.selectedItems()
        
        #if len(items) == 0:
            #return
        
        #item_paths = list()
        
        #if isinstance(self._data_, NestedFinder.nesting_types):
            #finder = NestedFinder(self._data)
            
            #top_title = self.treeWidget.top_title
            
            ##if top_title in (os.path.sep, "/")
            
            #for item in items:
                #item_path = self._get_path_for_item_(item)
                
                #path_element_strings = list() if item_path[0] in (os.path.sep, "/") else [item_path[0]]
                
                #for ipath in item_path[1:]:
                    #path_element_strings.append("['"+ipath+"']")
                    
                #item_paths.append("".join(path_element_strings))
                
        #return item_paths
        
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
                #self._scipyenWindow_.app.clipboard().setText(",\n".join(item_paths))
            else:
                self._scipyenWindow_.app.clipboard().setText(", ".join(["""%s""" % i for i in item_paths]))
                #self._scipyenWindow_.app.clipboard().setText(", ".join(item_paths))
                
        elif len(item_paths) == 1:
            self._scipyenWindow_.app.clipboard().setText(item_paths[0])
            
    @pyqtSlot()
    @safeWrapper
    def slot_collapseAll(self):
        for k in range(self.treeWidget.topLevelItemCount()):
            self._collapse_expand_Recursive(self.treeWidget.topLevelItem(k), current=False)
            #self._collapseRecursive_(self.treeWidget.topLevelItem(k), collapseCurrent=False)

    
    @pyqtSlot()
    @safeWrapper
    def slot_expandAll(self):
        for k in range(self.treeWidget.topLevelItemCount()):
            self._collapse_expand_Recursive(self.treeWidget.topLevelItem(k), expand=True, current=False)
        
    @pyqtSlot()
    @safeWrapper
    def slot_copyPaths(self):
        if self._scipyenWindow_ is None:
            return
        
        item_paths = self.getSelectedPaths()
        self.exportPathsToClipboard(item_paths)

    @pyqtSlot()
    @safeWrapper
    def slot_exportItemPathToConsole(self):
        if self._scipyenWindow_ is None:
            return
        
        item_paths = self.getSelectedPaths()
        self.exportPathsToClipboard(item_paths)
        self._scipyenWindow_.console.paste()
                
    @pyqtSlot()
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
        
    @pyqtSlot()
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
    
    #@safeWrapper
    #def _get_path_for_item_0_(self, item):
        #"""WARNING: Result is not suitable as parameter to eval()
        #"""
        #item_path = list()
        #item_path.append(item.text(0))
        
        #parent = item.parent()
        
        #while parent is not None:
            #item_path.append(parent.text(0))
            #parent = parent.parent()
        
        #item_path.reverse()
        
        #return item_path
    
    @safeWrapper
    def _parse_item(self, item):
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
        
        ndx = self._parse_item(item)
        
        if ndx is not None:
            item_path.append(ndx)

        parent = item.parent()
        
        while parent is not None:
            if parent.parent() is not None:
                ndx = self._parse_item(parent)
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
            
            objs = NestedFinder.getvalue(self._data_, path, single=True)
            
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
                newVarName = validate_varname(namePrompt.text(), self._scipyenWindow_.workspace)
                
                self._scipyenWindow_.assignToWorkspace(newVarName, objects[0], from_console=False)
                
        else:
            for name, obj in zip(names, objects):
                self._scipyenWindow_.assignToWorkspace(name, obj, from_console=False)

    def _collapse_expand_Recursive(self, item, expand=False, current=True):
        if expand:
            fn = self.treeWidget.expandItem
        else:
            fn = self.treeWidget.collapseItem
            
        for k in range(item.childCount()):
            self._collapse_expand_Recursive(item.child(k), expand=expand)
            
        if current:
            fn(item)
        
