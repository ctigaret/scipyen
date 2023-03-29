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

# from gui.tableeditor import (TableEditorWidget, TabularDataModel,)

from gui.widgets.interactivetreewidget import InteractiveTreeWidget
from gui.widgets.tablewidget import SimpleTableWidget
from gui.widgets.tableeditorwidget import (TableEditorWidget, TabularDataModel)

#### END pict.core modules

#### BEGIN pict.gui modules
from .scipyenviewer import ScipyenViewer #, ScipyenFrameViewer
from . import quickdialog
from . import resources_rc
#### END pict.gui modules

# NOTE: 2022-12-25 23:08:51
# needed for the new plugins framework
# This plugins does not install a custom menu, but DOES provide a viewer type
# hence we flag it using __scipyen_plugin__ (we could have defined
# init_scipyen_plugin instead, to return an empty dict)
__scipyen_plugin__ = None

# SINGLETONS = (tuple(), None, math.inf, math.nan, np.inf, np.nan, MISSING, pd.NA)

# class SimpleTableWidget(TableWidget): # TableWidget imported from pyqtgraph
#     """Another simple table widget, which allows zero-based row/column indices.
#     
#     gui.tableeditor.TableEditorWidget does that too, and more, but is too slow. 
#     
#     In contrast, pyqtgraph's TableWidget is much more efficient
#     
#     """
#     def __init__(self, *args, natural_row_index=False, natural_col_index=False, **kwds):
#         self._pythonic_col_index = not natural_col_index
#         self._pythonic_row_index = not natural_row_index
#         super().__init__(*args, **kwds)
#         
#     def setData(self, data):
#         super().setData(data)
#         #if isinstance(data, neo.core.dataobject.DataObject):
#             
#         if isinstance(data, (np.ndarray, tuple, list, deque)):
#             if self._pythonic_col_index:
#                 self.setHorizontalHeaderLabels(["%d"%i for i in range(self.columnCount())])
#                 
#             if self._pythonic_row_index:
#                 self.setVerticalHeaderLabels(["%d"%i for i in range(self.rowCount())])
#                 
#         elif isinstance(data, pd.Series):
#             self.setHorizontalHeaderLabels(["%s"%i for i in data.index])
#             self.setVerticalHeaderLabels([data.name])
#             
#         elif isinstance(data, pd.DataFrame):
#             self.setHorizontalHeaderLabels(["%s"%i for i in data.index])
#             self.setVerticalHeaderLabels([data.columns])
#             
#         elif isinstance(data, pd.Index):
#             self.setHorizontalHeaderLabels(["%s"%i for i in data])
#             
#         
#     def iterFirstAxis(self, data):
#         """Overrides TableWidget.iterFirstAxis.
#         
#         Avoid exceptions when data is a dimesionless array.
#         
#         In the original TableWidget from pyqtgraph this method fails when data 
#         is a dimesionless np.ndarray (i.e. with empty shape and ndim = 0).
#         
#         This kind of arrays unfortunately can occur when creating a numpy
#         array (either directly in the numpy library, or in the python Quantities
#         library):
#         
#         Example 1 - using python quantities:
#         ------------------------------------
#         
#         In: import quantities as pq
#         
#         In: a = 1*pq.s
#         
#         In: a
#         Out: array(1.)*s
#         
#         In: a.shape
#         Out: ()
#         
#         In: a.ndim
#         Out: 0
#         
#         In: a[0]
#         IndexError: too many indices for array: array is 0-dimensional, but 1 were indexed
#         
#         Example 2 - directly creating a numpy array:
#         --------------------------------------------
#         
#         In: b = np.array(1)
#         
#         In: b
#         Out: array(1)
#         
#         In: b.shape
#         Out: ()
#         
#         In: b.ndim
#         Out: 0
#         
#         In: b[0]
#         IndexError: too many indices for array: array is 0-dimensional, but 1 were indexed
#         
#         This will cause self.iterFirstAxis(a) to raise 
#         IndexError: tuple index out of range
#         
#         
#         HOWEVER, the value of the unique element of the array can be retrieved
#         by using its "take" method:
#         
#         In: a.take(0)
#         Out: 1.0
#         
#         In: b.take(0)
#         Out: 1
# 
#         
#         """
#         if len(data.shape) == 0 or data.ndim == 0:
#             yield(data.take(0))
#             
#         else:
#             for i in range(data.shape[0]):
#                 yield data[i]

# class InteractiveTreeWidget(DataTreeWidget):
#     """Extends pyqtgraph.widgets.DataTreeWidget.
#     
#     Enables the following:
#     
#     1. Support for custom context menu to pyqtgraph.DataTreeWidget.
#     
#     2. Use Scipyen gui.tableeditor.TableEditorWidget instead of 
#         pyqtgraph.TableWidget
#     
#     3. Support for any key type, as long as it is hashable.
#     
#     4. Support for circular references to hierarchical data objects (subsequent
#         references ot the same object are NOT traversed; instead, a path to the 
#         first encountered reference - in depth-first order - is displayed)
#     
#     """
#     def __init__(self, *args, **kwargs):
#         """
#         Keyword parameters (selective list):
#         ------------------------------------
#         useTableEditor:bool, default is False; 
#             When True, use TableEditorWidget, else use SimpleTableWidget
#         """
#         self._visited_ = dict()
#         self._use_TableEditor_ = kwargs.pop("useTableEditor", False)
#         self.top_title = "/"
#         self._last_active_item_ = None
#         self._last_active_item_column_ = 0
#         self.has_dynamic_private = False
#         self._private_data_ = None
#         # super(InteractiveTreeWidget, self).__init__(*args, **kwargs)
#         DataTreeWidget.__init__(self, *args, **kwargs)
#         self.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerItem)
#         self.setColumnCount(3)
#         self.setHeaderLabels(['key / index', 'type', 'value / info'])
#         self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
#         self.headerItem().setToolTip(0, "Key or index of child data.\nThe type of the key or index is shown in their tooltip.")
#         self.headerItem().setToolTip(1, "Type of child data mapped to a key or index.\nAdditional type information is shown in their tooltip.")
#         self.headerItem().setToolTip(2, "Value of child data, or its length\n(when data is a nested collection).\nNumpy arrays ar displayed as a table")
#         
#         
#         self.itemClicked.connect(self._slot_setLastActive)
#         
#     def _makeTableWidget_(self, data):
#         if self._use_TableEditor_:
#             widget = TableEditorWidget(parent=self)
#             signalBlocker = QtCore.QSignalBlocker(widget.tableView)
#             widget.tableView.model().setModelData(data)
#             widget.readOnly=True
#         else:
#             widget = SimpleTableWidget()
#             widget.setData(data)
#             
#         widget.setMaximumHeight(200)
#         
#         return widget
#     
#     @pyqtSlot(QtWidgets.QTreeWidgetItem, int)
#     def _slot_setLastActive(self, item, column):
#         # print(f"{self.__class__.__name__}<{self.parent().windowTitle()}, {self.parent().parent().windowTitle()}> _slot_setLastActive item {item.data(0,QtCore.Qt.DisplayRole)}")
#         self._last_active_item_ = item.data(0,QtCore.Qt.DisplayRole)
#         self._last_active_item_column_ = column
#     
#     def setData(self, data, predicate=None, top_title:str = "", dataTypeStr = None, hideRoot=False):
#         """data should be a dictionary."""
#         # print(f"{self.__class__.__name__}<{self.parent().windowTitle()}, {self.parent().parent().windowTitle()}> set data")
#         self._visited_.clear()
#         self.predicate = predicate
#         self._private_data_, self.has_dynamic_private = self._parse_data_(data)
#         
#         # print(f"{self.__class__.__name__}.setData: {type(data).__name__}, dynamic: {self.has_dynamic_private}")
#         
#         if len(top_title.strip()) == 0:
#             self.top_title = "/"
#         else:
#             self.top_title = top_title
#             
#         # NOTE: 2022-12-15 23:25:05
#         # super().setData(data) # calls self.buildTree(...), which then calls self.parse(...)
#         self.clear()
#         self.widgets = []
#         self.nodes = {}
#         #              data, parent,                   predicate,           hideRoot
#         self.buildTree(self._private_data_, self.invisibleRootItem(), typeStr = dataTypeStr, predicate=predicate, hideRoot=hideRoot)
#         self.expandToDepth(3)
#         self.resizeColumnToContents(0)
#         
#         self.topLevelItem(0).setText(0, self.top_title)
#         
#         # print(f"{self.__class__.__name__}<{self.parent().windowTitle()}, {self.parent().parent().windowTitle()}> last item {self._last_active_item_} column {self._last_active_item_column_}")
#         if isinstance(self._last_active_item_, str) and len(self._last_active_item_.strip()) and \
#             self._last_active_item_column_ < self.columnCount():
#                 items = self.findItems(self._last_active_item_, QtCore.Qt.MatchExactly, 0)
#                 if len(items) > 0:
#                     # print(f"{self.__class__.__name__}<{self.parent().windowTitle()}, {self.parent().parent().windowTitle()}> last items {[i.data(0, QtCore.Qt.DisplayRole) for i in items]}")
#                     item = items[0]
#                     index = self.indexFromItem(item, self._last_active_item_column_)
#                     target = self.itemFromIndex(index)
#                     self.scrollToItem(target, self._last_active_item_column_)
#                     target.setSelected(True)
#                     self.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)
#                     
#     def _parse_data_(self, data):
#         # if type(data) not in list(DataViewer.viewer_for_types)[:-1] and not inspect.isroutine(data) and data is not None:
#         mro = inspect.getmro(type(data))
#         if all(t not in list(DataViewer.viewer_for_types) for t in mro) and not inspect.isroutine(data) and data is not None:
#             return dt.inspect_members(data, self.predicate), True
#         else:
#             return data, False
#         
#         
#     
#     def buildTree(self, data:object, parent:QtWidgets.QTreeWidgetItem, name:str="", nameTip:str="", typeStr = None, predicate=None, hideRoot:bool=False, path:tuple=()):
#         """
#         Overrides pyqtgraph.DataTreeWidget.buildTree()
#         
#         Positional parameters:
#         ----------------------
#         data: ideally, a dict; when not a dict, its __dict__ attribute will be
#             used, instead.
#             
#         parent: the parent tree widget item (a.k.a 'node')
#         
#         Named parameters:
#         -----------------
#         name:str; default is the empty string ("")
#         nameTip:str; default is the empty string ("")
#         hideRoot:bool; default is False
#         path: tuple; default is the empty tuple
#         
#         """
#         #from pyqtgraph.python2_3 import asUnicode
#         
#         # NOTE: 2021-07-24 13:15:38
#         # throughout this function 'node' is a QtWidgets.QTreeWidgetItem
#         # the root node is named after the symbol of the nested data structure
#         # shown by DataViewer, or by _docTitle_, hence it is always a str
#         #
#         # Child nodes are either dict keys, or int indices in iterables; this 
#         # can lead to confusion e.g., between different types of dict keys that 
#         # are represented by similar str for display purpose.
#         #
#         # For example, a dict key "2" (a str) and a dict key 2 (an int) are both
#         # represented as the str "2" (both str and int are hashable, hence they
#         # can be used as dict keys). 
#         #
#         # Consider the contrived example of a dict with two key/value pairs:
#         # 
#         # contrived = {2:"text", "2": "another text"}
#         #
#         # Since the keys appear identical in the InteractiveTreeWidget (as the 
#         # str '2') a user who wants to retrieve the value "text" from the dict 
#         # s/he has no way to know whether to type 'contrived[2]' (the correct
#         # choice in this example) or 'contrived["2"]' unless they try first, 
#         # with a 50% chance to get the wrong value
#         #
#         # For this reason we endow the 'key/index' column with a tooltip stating
#         # the type of the key (e.g. str or int, in this case)
#         #
#         # The only exception to this is the root node where the "name" is always
#         # "str"
#         
#         # NOTE: 2021-08-15 14:43:54
#         # node is a QTreeWidgetItem constructed on three strings, each one to
#         # be displayed in its corresponding column, as follows:
#         # string 0 -> "key/index" column: 'name' (displayed key or index)
#         # string 1 -> "type"      column: data type
#         # string 2 -> "value"     column: a description string:
#         #                           length (for collections)
#         #                           value  (for str)
#         #                           etc
#         
#         # NOTE: 2022-03-04 08:47:45
#         # 'node' is a QTreeWidgetItem
#         # when called by super(self).setData() this is set to either:
#         #
#         # (a) the parent item, if hideRoot is True (when this method is called from
#         #   the parent item is the tree widget's invisible root item)
#         #
#         # (b) an item constructed on a string list for the three columns, added
#         # to the 'parent' node passed to this method call
#         #
#         if hideRoot:
#             node = parent 
#         else:
#             node = QtWidgets.QTreeWidgetItem([name, "", ""])
#             parent.addChild(node)
#             
#         # print(f"{self.__class__.__name__}.buildTree: predicate = {predicate}")
#         
#         # record the path to the node so it can be retrieved later
#         # (this is used by the tree widget)
#         
#         # NOTE: 2021-08-15 14:41:32
#         # self.nodes is a dict
#         # path is a tuple (as index branch path) - this is immutable, hence 
#         # hashable, hence usable as dict key
#         self.nodes[path] = node
#         
#         typeStr_, desc, children, widget, typeTip = self.parse(data, predicate=predicate)
#         
#         if not isinstance(typeStr, str) or len(typeStr.strip()) == 0:
#             typeStr = typeStr_
#         
#         # NOTE: 2022-03-04 09:04:50
#         # nameTip is NOT set when this method is called by super().setData()
#         # hence it will have the default value (an empty string)
#         node.setToolTip(0, nameTip)
#         node.setText(1, typeStr)
#         node.setToolTip(1, typeTip)
#         node.setText(2, desc)
#         
#         if isinstance(data, NestedFinder.nesting_types):
#             if id(data) not in self._visited_.keys():
#                 self._visited_[id(data)] = (typeStr, path)
#             
#         # Truncate description and add text box if needed
#         if len(desc) > 100:
#             desc = desc[:97] + '...'
#             if widget is None:
#                 widget = QtWidgets.QPlainTextEdit(str(data))
#                 widget.setMaximumHeight(200)
#                 widget.setReadOnly(True)
#         
#         # Add widget to new subnode
#         if widget is not None:
#             self.widgets.append(widget)
#             subnode = QtWidgets.QTreeWidgetItem(["", "", ""])
#             node.addChild(subnode)
#             self.setItemWidget(subnode, 0, widget)
#             self.setFirstItemColumnSpanned(subnode, True)
#             
#         # recurse to children
#         for key, child_data in children.items():
#             if isinstance(key, type):
#                 keyrepr = f"{key.__module__}.{key.__name__}"
#                 keytip = str(key)
#                 #keytip = asUnicode(key)
#                 
#             elif type(key).__name__ == "instance":
#                 keyrepr = key.__class__.__name__
#                 keytip = str(key)
#                 #keytip = asUnicode(key)
#                 
#             else:
#                 keyrepr = str(key)
#                 #keyrepr = asUnicode(key)
#                 keytip = type(key).__name__
#                 
#             keyTypeTip = "key / index type: %s" % keytip
#             self.buildTree(child_data, node, keyrepr, keyTypeTip, predicate=predicate, path=path+(keyrepr,))
# 
#     def parse(self, data, predicate=None, typeStr=None):
#         """
#         Overrides pyqtgraph.DataTreeWidget.parse()
#         
#         Returns:
#         ========
#         • typeStr - a string representation of the data type
#         • description  - a short string representation
#         • a dict of sub-objects (children) to be parsed further
#         • optional widget to display as sub-node
#         • typeTip: a string indicating the type of the key (for dict data) or of
#             the index (for sequences, this is always an int, except for namedtuples
#             where it can be a str)
#         
#         CHANGELOG (most recent first):
#         ------------------------------
#         
#         2022-03-04 10:00:57:
#         TableEditorWidget or SimpleTableWidget selectable at initialization
#         TableEditorWidget is enabled by default
#         
#         NOTE: 2021-10-18 14:03:13
#         SimpleTableWidget DEPRECATED in favour of tableeditor.TableEditorWidget
#                 
#         NOTE: 2020-10-11 13:48:51
#         override superclass parse to use SimpleTableWidget instead
#         
#         """
#         from pyqtgraph.widgets.DataTreeWidget import HAVE_METAARRAY
#         from collections import OrderedDict
#         #from pyqtgraph.python2_3 import asUnicode
#         from core.datatypes import is_namedtuple
#         
# #         print(f"{self.__class__.__name__}.parse data is a {type(data).__name__}")
# #         
# #         print(f"{self.__class__.__name__}.parse: predicate = {predicate}")
# 
#         # NOTE: 2022-12-30 11:37:05
#         # allow pre-empting the type string (e.g. when passed a dict created
#         # dynamically from an object of some type)
#         if not isinstance(typeStr, str):
#             # defaults for all objects; ho
#             typeStr = type(data).__name__
#             typeTip = ""
#         else:
#             typeTip = typeStr
#         
#         if typeStr == "instance":
#             typeStr += ": " + data.__class__.__name__
#             typeTip = data.__class__.__name__
#             
#         elif typeStr == "type":
#             typeStr = data.__name__
#             typeTip = str(data)
#             
#         if is_namedtuple(data):
#             typeTip = "(namedtuple)"
#             
#         widget = None
#         desc = ""
#         children = {}
#         
#         if data is None:
#             typeStr = ""
#             return typeStr, desc, children, widget, typeTip 
#         
#         elif data is dataclasses.MISSING:
#             desc = str(MISSING)
#             return typeStr, desc, children, widget, typeTip 
#             
#         
#         # type-specific changes
#         try:
#             if isinstance(data, NestedFinder.nesting_types):
#                 if data not in SINGLETONS and id(data) in self._visited_.keys():
#                     objtype = self._visited_[id(data)][0]
#                     path = "/".join(list(self._visited_[id(data)][1]))
#                     if len(path.strip()) == 0:
#                         full_path = self.top_title
#                     else:
#                         if self.top_title == "/":
#                             full_path = "/" + path
#                         else:
#                             full_path = "/".join([self.top_title, path])
#                     desc = "<reference to %s at %s >" % (objtype, full_path)
#                 else:
#                     if isinstance(data, dict):
#                         desc = "length=%d" % len(data)
#                         if isinstance(data, OrderedDict):
#                             children = data
#                             
#                         else:
#                             # NOTE: 2021-07-20 09:52:34
#                             # dict objects with mixed key types cannot be sorted
#                             # therefore we resort to an indexing vector
#                             ndx = [i[1] for i in sorted((str(k[0]), k[1]) for k in zip(data.keys(), range(len(data))))]
#                             items = [i for i in data.items()]
#                             children = OrderedDict([items[k] for k in ndx])
#                             
#                     elif isinstance(data, (list, tuple, deque)):
#                         desc = "length=%d" % len(data)
#                         # NOTE: 2021-07-24 14:57:02
#                         # accommodate namedtuple types
#                         if is_namedtuple(data):
#                             children = data._asdict()
#                         else:
#                             children = OrderedDict(enumerate(data))
#                 
#             elif HAVE_METAARRAY and (hasattr(data, 'implements') and data.implements('MetaArray')):
#                 children = OrderedDict([
#                     ('data', data.view(np.ndarray)),
#                     ('meta', data.infoCopy())
#                 ])
#                 
#             elif isinstance(data, pd.DataFrame):
#                 desc = "length=%d, columns=%d" % (len(data), len(data.columns))
#                 widget = self._makeTableWidget_(data)
#                 
#             elif isinstance(data, pd.Series):
#                 desc = "length=%d, dtype=%s" % (len(data), data.dtype)
#                 widget = self._makeTableWidget_(data)
#                 
#             elif isinstance(data, pd.Index):
#                 desc = "length=%d" % len(data)
#                 widget = self._makeTableWidget_(data)
#                 
#             elif isinstance(data, neo.core.dataobject.DataObject):
#                 desc = "shape=%s dtype=%s" % (data.shape, data.dtype)
#                 if data.size == 1:
#                     widget = QtWidgets.QLabel(str(data))
#                 else:
#                     widget = self._makeTableWidget_(data)
#                     
#             elif isinstance(data, pq.Quantity):
#                 desc = "shape=%s dtype=%s" % (data.shape, data.dtype)
#                 if data.size == 1:
#                     widget = QtWidgets.QLabel(str(data))
#                 else:
#                     widget = self._makeTableWidget_(data)
#                     
#             elif isinstance(data, np.ndarray):
#                 desc = "shape=%s dtype=%s" % (data.shape, data.dtype)
#                 widget = self._makeTableWidget_(data)
#                 
#             elif isinstance(data, types.TracebackType):  ## convert traceback to a list of strings
#                 frames = list(map(str.strip, traceback.format_list(traceback.extract_tb(data))))
#                 widget = QtWidgets.QPlainTextEdit(str('\n'.join(frames)))
#                 widget.setMaximumHeight(200)
#                 widget.setReadOnly(True)
#                 
#             elif isinstance(data, str):
#                 if len(data)> 100:
#                     _data = data[:97] + "..."
#                     desc = f"string with {len(data)} characters"
#                     widget = QtWidgets.QPlainTextEdit(data)
#                     widget.setMaximumHeight(200)
#                     widget.setReadOnly(True)
#                 else:
#                     desc = data
#                 
#             else:
#                 # NOTE: 2022-12-30 14:26:46
#                 # Descending into the data's members is too prone for infinite recurson.
#                 # Hence, we STOP here (i.e. at first level).
#                 desc = str(data)
#                 
# #             elif isinstance(data, (type, numbers.Number, str, bytes, types.FrameType)) or dt.is_routine(data):
# #                 desc = str(data)
# #                 
# #             else:
# #                 children = dt.inspect_members(data, predicate)
#                     
#             return typeStr, desc, children, widget, typeTip 
#         except:
#             print(f"{self.__class__.__name__}.parse data type : {type(data).__name__}, data: {data}")
#             raise
        
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
    sig_activated = pyqtSignal(int)
    closeMe  = pyqtSignal(int)
    signal_window_will_close = pyqtSignal()
    
    # NOTE: 2022-11-20 22:09:07
    # reserved for future developmet of editing capabilities TODO
    sig_dataChanged = pyqtSignal(name = "sig_dataChanged")
    
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
            
            for k in range(self.treeWidget.topLevelItemCount()):
                self._collapse_expand_Recursive(self.treeWidget.topLevelItem(k), current=False)

    @pyqtSlot()
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
            
    @pyqtSlot()
    def slot_goBack(self):
        self._cache_index_ = self._cache_index_ - 1
        
        if self._cache_index_ < 0:
            self._cache_index_ = 0
            
        elif self._cache_index_ >= len(self._obj_cache_):
            self._cache_index_ = len(self._obj_cache_) - 1
            
        self.goNext.setEnabled(self._cache_index_ < len(self._obj_cache_)-1)
        self.goBack.setEnabled(self._cache_index_ >0)
            
        self._populate_tree_widget_()
        
    @pyqtSlot()
    def slot_goFirst(self):
        self._cache_index_ = 0
        self._populate_tree_widget_()
        
    @pyqtSlot()
    def slot_goNext(self):
        self._cache_index_ = self._cache_index_ + 1
        if self._cache_index_ >= len(self._obj_cache_):
            self._cache_index_ = len(self._obj_cache_) - 1
            
        self.goNext.setEnabled(self._cache_index_ < len(self._obj_cache_)-1)   
        self.goBack.setEnabled(self._cache_index_ >0)
        self._populate_tree_widget_()
        
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
            
    @pyqtSlot()
    @safeWrapper
    def slot_collapseAll(self):
        for k in range(self.treeWidget.topLevelItemCount()):
            self._collapse_expand_Recursive(self.treeWidget.topLevelItem(k), current=False)

    
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
    def slot_editItemData(self):
        # TODO: 2022-10-11 13:45:35
        from core.utilities import get_nested_value
        pass
        items = self.treeWidget.selectedItems()
        
        if len(items) != 1:
            return
        
        
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
        
