from __future__ import print_function

import os, warnings, types, traceback, itertools, inspect, dataclasses, numbers
from collections import deque
from dataclasses import MISSING
import math
#### END core python modules

#### BEGIN 3rd party modules
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__

from pyqtgraph import (DataTreeWidget, TableWidget, )
#from pyqtgraph.widgets.TableWidget import _defersort

import neo
import quantities as pq
import numpy as np
import pandas as pd
#### END 3rd party modules

#### BEGIN pict.core modules
import core.datatypes as dt

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

from core.prog import (safeWrapper, safeGUIWrapper, )

from core.traitcontainers import (DataBag, DataBagTraitsObserver,)

from gui.widgets.tablewidget import SimpleTableWidget
from gui.widgets.tableeditorwidget import (TableEditorWidget, TabularDataModel,)

SINGLETONS = (tuple(), None, math.inf, math.nan, np.inf, np.nan, MISSING, pd.NA)

class InteractiveTreeWidget(DataTreeWidget):
    """Extends pyqtgraph.widgets.DataTreeWidget.
    
    Enables the following:
    
    1. Support for custom context menu to pyqtgraph.DataTreeWidget.
    
    2. Use Scipyen gui.tableeditor.TableEditorWidget instead of 
        pyqtgraph.TableWidget
    
    3. Support for any key type, as long as it is hashable.
    
    4. Support for circular references to hierarchical data objects (subsequent
        references ot the same object are NOT traversed; instead, a path to the 
        first encountered reference - in depth-first order - is displayed)
    
    """
    def __init__(self, *args, **kwargs):
        """
        Keyword parameters (selective list):
        ------------------------------------
        useTableEditor:bool, default is False; 
            When True, use TableEditorWidget, else use SimpleTableWidget
        """
        self._visited_ = dict()
        self._use_TableEditor_ = kwargs.pop("useTableEditor", False)
        self.top_title = "/"
        self._last_active_item_ = None
        self._last_active_item_column_ = 0
        self.has_dynamic_private = False
        self._private_data_ = None
        self._supported_data_types_ = kwargs.pop("supported_data_types", tuple())
        if not isinstance(self._supported_data_types_, tuple) or not all(isinstance(v, type) for v in self._supported_data_types_):
            self._supported_data_types_ = tuple()
        # super(InteractiveTreeWidget, self).__init__(*args, **kwargs)
        DataTreeWidget.__init__(self, *args, **kwargs)
        self.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerItem)
        self.setColumnCount(3)
        self.setHeaderLabels(['key / index', 'type', 'value / info'])
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.headerItem().setToolTip(0, "Key or index of child data.\nThe type of the key or index is shown in their tooltip.")
        self.headerItem().setToolTip(1, "Type of child data mapped to a key or index.\nAdditional type information is shown in their tooltip.")
        self.headerItem().setToolTip(2, "Value of child data, or its length\n(when data is a nested collection).\nNumpy arrays ar displayed as a table")
        
        
        self.itemClicked.connect(self._slot_setLastActive)
        
    def _makeTableWidget_(self, data):
        if self._use_TableEditor_:
            widget = TableEditorWidget(parent=self)
            signalBlocker = QtCore.QSignalBlocker(widget.tableView)
            widget.tableView.model().setModelData(data)
            widget.readOnly=True
        else:
            widget = SimpleTableWidget()
            widget.setData(data)
            
        widget.setMaximumHeight(200)
        
        return widget
    
    @pyqtSlot(QtWidgets.QTreeWidgetItem, int)
    def _slot_setLastActive(self, item, column):
        # print(f"{self.__class__.__name__}<{self.parent().windowTitle()}, {self.parent().parent().windowTitle()}> _slot_setLastActive item {item.data(0,QtCore.Qt.DisplayRole)}")
        self._last_active_item_ = item.data(0,QtCore.Qt.DisplayRole)
        self._last_active_item_column_ = column
        
    def setSupportedDataTypes(self, types:tuple):
        if isinstance(types, tuple) and len(types):
            self._supported_data_types_ = types
    
    def setData(self, data, predicate=None, top_title:str = "", dataTypeStr = None, hideRoot=False):
        """data should be a dictionary."""
        # print(f"{self.__class__.__name__}<{self.parent().windowTitle()}, {self.parent().parent().windowTitle()}> set data")
        self._visited_.clear()
        self.predicate = predicate
        self._private_data_, self.has_dynamic_private = self._parse_data_(data)
        
        if len(top_title.strip()) == 0:
            self.top_title = "/"
        else:
            self.top_title = top_title
            
        # NOTE: 2022-12-15 23:25:05
        # super().setData(data) # calls self.buildTree(...), which then calls self.parse(...)
        self.clear()
        self.widgets = []
        self.nodes = {}
        #              data, parent,                   predicate,           hideRoot
        self.buildTree(self._private_data_, self.invisibleRootItem(), typeStr = dataTypeStr, predicate=predicate, hideRoot=hideRoot)
        self.expandToDepth(3)
        self.resizeColumnToContents(0)
        
        self.topLevelItem(0).setText(0, self.top_title)
        
        # print(f"{self.__class__.__name__}<{self.parent().windowTitle()}, {self.parent().parent().windowTitle()}> last item {self._last_active_item_} column {self._last_active_item_column_}")
        if isinstance(self._last_active_item_, str) and len(self._last_active_item_.strip()) and \
            self._last_active_item_column_ < self.columnCount():
                items = self.findItems(self._last_active_item_, QtCore.Qt.MatchExactly, 0)
                if len(items) > 0:
                    # print(f"{self.__class__.__name__}<{self.parent().windowTitle()}, {self.parent().parent().windowTitle()}> last items {[i.data(0, QtCore.Qt.DisplayRole) for i in items]}")
                    item = items[0]
                    index = self.indexFromItem(item, self._last_active_item_column_)
                    target = self.itemFromIndex(index)
                    self.scrollToItem(target, self._last_active_item_column_)
                    target.setSelected(True)
                    self.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)
                    
    def _parse_data_(self, data):
        mro = inspect.getmro(type(data))
        if all(t not in self._supported_data_types_ for t in mro) and not inspect.isroutine(data) and data is not None:
            return dt.inspect_members(data, self.predicate), True
        else:
            return data, False
        
    def buildTree(self, data:object, parent:QtWidgets.QTreeWidgetItem, name:str="", nameTip:str="", typeStr = None, predicate=None, hideRoot:bool=False, path:tuple=()):
        """
        Overrides pyqtgraph.DataTreeWidget.buildTree()
        
        Positional parameters:
        ----------------------
        data: ideally, a dict; when not a dict, its __dict__ attribute will be
            used, instead.
            
        parent: the parent tree widget item (a.k.a 'node')
        
        Named parameters:
        -----------------
        name:str; default is the empty string ("")
        nameTip:str; default is the empty string ("")
        hideRoot:bool; default is False
        path: tuple; default is the empty tuple
        
        """
        #from pyqtgraph.python2_3 import asUnicode
        
        # NOTE: 2021-07-24 13:15:38
        # throughout this function 'node' is a QtWidgets.QTreeWidgetItem
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
        
        # NOTE: 2022-03-04 08:47:45
        # 'node' is a QTreeWidgetItem
        # when called by super(self).setData() this is set to either:
        #
        # (a) the parent item, if hideRoot is True (when this method is called from
        #   the parent item is the tree widget's invisible root item)
        #
        # (b) an item constructed on a string list for the three columns, added
        # to the 'parent' node passed to this method call
        #
        if hideRoot:
            node = parent 
        else:
            node = QtWidgets.QTreeWidgetItem([name, "", ""])
            parent.addChild(node)
            
        # print(f"{self.__class__.__name__}.buildTree: predicate = {predicate}")
        
        # record the path to the node so it can be retrieved later
        # (this is used by the tree widget)
        
        # NOTE: 2021-08-15 14:41:32
        # self.nodes is a dict
        # path is a tuple (as index branch path) - this is immutable, hence 
        # hashable, hence usable as dict key
        self.nodes[path] = node
        
        typeStr_, desc, children, widget, typeTip = self.parse(data, predicate=predicate)
        
        if not isinstance(typeStr, str) or len(typeStr.strip()) == 0:
            typeStr = typeStr_
        
        # NOTE: 2022-03-04 09:04:50
        # nameTip is NOT set when this method is called by super().setData()
        # hence it will have the default value (an empty string)
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
                widget = QtWidgets.QPlainTextEdit(str(data))
                widget.setMaximumHeight(200)
                widget.setReadOnly(True)
        
        # Add widget to new subnode
        if widget is not None:
            self.widgets.append(widget)
            subnode = QtWidgets.QTreeWidgetItem(["", "", ""])
            node.addChild(subnode)
            self.setItemWidget(subnode, 0, widget)
            self.setFirstItemColumnSpanned(subnode, True)
            
        # recurse to children
        for key, child_data in children.items():
            if isinstance(key, type):
                keyrepr = f"{key.__module__}.{key.__name__}"
                keytip = str(key)
                #keytip = asUnicode(key)
                
            elif type(key).__name__ == "instance":
                keyrepr = key.__class__.__name__
                keytip = str(key)
                #keytip = asUnicode(key)
                
            else:
                keyrepr = str(key)
                #keyrepr = asUnicode(key)
                keytip = type(key).__name__
                
            keyTypeTip = "key / index type: %s" % keytip
            self.buildTree(child_data, node, keyrepr, keyTypeTip, predicate=predicate, path=path+(keyrepr,))

    def parse(self, data, predicate=None, typeStr=None):
        """
        Overrides pyqtgraph.DataTreeWidget.parse()
        
        Returns:
        ========
        • typeStr - a string representation of the data type
        • description  - a short string representation
        • a dict of sub-objects (children) to be parsed further
        • optional widget to display as sub-node
        • typeTip: a string indicating the type of the key (for dict data) or of
            the index (for sequences, this is always an int, except for namedtuples
            where it can be a str)
        
        CHANGELOG (most recent first):
        ------------------------------
        
        2022-03-04 10:00:57:
        TableEditorWidget or SimpleTableWidget selectable at initialization
        TableEditorWidget is enabled by default
        
        NOTE: 2021-10-18 14:03:13
        SimpleTableWidget DEPRECATED in favour of tableeditor.TableEditorWidget
                
        NOTE: 2020-10-11 13:48:51
        override superclass parse to use SimpleTableWidget instead
        
        """
        from pyqtgraph.widgets.DataTreeWidget import HAVE_METAARRAY
        from collections import OrderedDict
        #from pyqtgraph.python2_3 import asUnicode
        from core.datatypes import is_namedtuple
        
#         print(f"{self.__class__.__name__}.parse data is a {type(data).__name__}")
#         
#         print(f"{self.__class__.__name__}.parse: predicate = {predicate}")

        # NOTE: 2022-12-30 11:37:05
        # allow pre-empting the type string (e.g. when passed a dict created
        # dynamically from an object of some type)
        if not isinstance(typeStr, str):
            # defaults for all objects; ho
            typeStr = type(data).__name__
            typeTip = ""
        else:
            typeTip = typeStr
        
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
        children = {}
        
        if data is None:
            typeStr = ""
            return typeStr, desc, children, widget, typeTip 
        
        elif data is dataclasses.MISSING:
            desc = str(MISSING)
            return typeStr, desc, children, widget, typeTip 
            
        
        # type-specific changes
        try:
            if isinstance(data, NestedFinder.nesting_types + (set,)):
                if data not in SINGLETONS and id(data) in self._visited_.keys():
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
                            children = data
                            
                        else:
                            # NOTE: 2021-07-20 09:52:34
                            # dict objects with mixed key types cannot be sorted
                            # therefore we resort to an indexing vector
                            ndx = [i[1] for i in sorted((str(k[0]), k[1]) for k in zip(data.keys(), range(len(data))))]
                            items = [i for i in data.items()]
                            children = OrderedDict([items[k] for k in ndx])
                            
                    elif isinstance(data, (list, tuple, deque, set)):
                        desc = "length=%d" % len(data)
                        # NOTE: 2021-07-24 14:57:02
                        # accommodate namedtuple types
                        if is_namedtuple(data):
                            children = data._asdict()
                        else:
                            children = OrderedDict(enumerate(data))
                
            elif HAVE_METAARRAY and (hasattr(data, 'implements') and data.implements('MetaArray')):
                children = OrderedDict([
                    ('data', data.view(np.ndarray)),
                    ('meta', data.infoCopy())
                ])
                
            elif isinstance(data, pd.DataFrame):
                desc = "length=%d, columns=%d" % (len(data), len(data.columns))
                widget = self._makeTableWidget_(data)
                
            elif isinstance(data, pd.Series):
                desc = "length=%d, dtype=%s" % (len(data), data.dtype)
                widget = self._makeTableWidget_(data)
                
            elif isinstance(data, pd.Index):
                desc = "length=%d" % len(data)
                widget = self._makeTableWidget_(data)
                
            elif isinstance(data, neo.core.dataobject.DataObject):
                desc = "shape=%s dtype=%s" % (data.shape, data.dtype)
                if data.size == 1:
                    widget = QtWidgets.QLabel(str(data))
                else:
                    widget = self._makeTableWidget_(data)
                    
            elif isinstance(data, pq.Quantity):
                desc = "shape=%s dtype=%s" % (data.shape, data.dtype)
                if data.size == 1:
                    widget = QtWidgets.QLabel(str(data))
                else:
                    widget = self._makeTableWidget_(data)
                    
            elif isinstance(data, np.ndarray):
                desc = "shape=%s dtype=%s" % (data.shape, data.dtype)
                widget = self._makeTableWidget_(data)
                
            elif isinstance(data, types.TracebackType):  ## convert traceback to a list of strings
                frames = list(map(str.strip, traceback.format_list(traceback.extract_tb(data))))
                widget = QtWidgets.QPlainTextEdit(str('\n'.join(frames)))
                widget.setMaximumHeight(200)
                widget.setReadOnly(True)
                
            elif isinstance(data, str):
                if len(data)> 100:
                    _data = data[:97] + "..."
                    desc = f"string with {len(data)} characters"
                    widget = QtWidgets.QPlainTextEdit(data)
                    widget.setMaximumHeight(200)
                    widget.setReadOnly(True)
                else:
                    desc = data
                
            else:
                # NOTE: 2022-12-30 14:26:46
                # Descending into the data's members is too prone for infinite recurson.
                # Hence, we STOP here (i.e. at first level).
                desc = str(data)
                
            return typeStr, desc, children, widget, typeTip 
        
        except:
            print(f"{self.__class__.__name__}.parse data type : {type(data).__name__}, data: {data}")
            raise
        
