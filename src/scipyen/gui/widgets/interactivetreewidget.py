# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""
# TODO: 2025-03-10 23:21:21
# implement editing function, where applicable
# NEEDS proxy editor widgets
from __future__ import print_function

import os, warnings, types, traceback, itertools, inspect, dataclasses, numbers
import pathlib
import datetime
import fractions, decimal
import pkgutil
import typing
import enum
from collections import deque
import dataclasses
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
import scipy
import pandas as pd
import vigra
#### END 3rd party modules

#### BEGIN pict.core modules
import core.datatypes as datatypes

import imaging.axiscalibration
from imaging.axiscalibration import AxesCalibration

import imaging.scandata
from imaging.scandata import (ScanData, AnalysisUnit)

from core.triggerprotocols import TriggerProtocol
from core.triggerevent import (DataMark, TriggerEvent, TriggerEventType)

import core.datasignal as datasignal
from core.datasignal import (DataSignal, IrregularlySampledDataSignal)

import core.datazone as datazone
from core.datazone import (DataZone, Interval)

from core import xmlutils, strutils

from core.workspacefunctions import (validate_varname, user_workspace)

#from core.utilities import (get_nested_value, set_nested_value, counter_suffix, )

from core.utilities import (NestedFinder, unique)

from core.prog import (safewrapper, safeguiwrapper, print_styled)

from core.traitcontainers import (DataBag, DataBagTraitsObserver,)

from gui.widgets.tablewidget import SimpleTableWidget
from gui.widgets.tableeditorwidget import (TableEditorWidget, TabularDataModel,)
from gui.pictgui import WorkerThread

NOTMEMOIZED = (tuple, type(None), type(MISSING), type(pd.NA), type, np.ndarray, types.ModuleType, pkgutil.ModuleInfo)
PODS = (bool, int, float, bytes, bytearray, str)

class InteractiveTreeWidget(QtWidgets.QTreeWidget):
    r"""QTreeWidget that enables:
    
    1. Support for custom context menu.
    
    2. Use Scipyen gui.tableeditor.TableEditorWidget
    
    3. Support for any key type, as long as it is hashable.
    
    4. Support for circular references to hierarchical data objects (subsequent
        references ot the same object are NOT traversed; instead, a path to the 
        first encountered reference - in depth-first order - is displayed)

    Inspired by pyqtgraph.widget.DataTreeWidget (originally, a subclass of it)

    NOTE: 2025-11-23 08:22:37 
    CHANGELOG:
    Up to mid March 2025: subclass of pyqtgraph.widget.DataTreeWidget
    After that: direct subclass of QtWidgets.QTreeWidget
    
    """
    # NOTE: 2025-05-24 22:21:05
    # child widgets are either None, TableEditorWidget, SimpleTableWidget, or QPlainTextEdit
    
    _default_widget_height_ = 200
    
    def __init__(self, *args, **kwargs):
        r"""
        Keyword parameters (selective list):
        ------------------------------------
        useTableEditor:bool, default is False; 
            When True, use TableEditorWidget, else use SimpleTableWidget
        """
        parent =  kwargs.pop("parent", None)
        super().__init__(parent=parent)
        self._ready_:bool = False

        self._use_TableEditor_ = kwargs.pop("useTableEditor", False)
        self._supported_data_types_ = kwargs.pop("supported_data_types", tuple())
        if not isinstance(self._supported_data_types_, tuple) or not all(isinstance(v, type) for v in self._supported_data_types_):
            self._supported_data_types_ = tuple()
        self._visited_ = dict() #{}
        # self._visited_ = list()
        self.top_title = "/"
        self._last_active_item_ = None
        self._last_active_item_column_ = 0
        self.has_dynamic_private = False
        self._private_data_ = None
        # DataTreeWidget.__init__(self, *args, **kwargs)
        self.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerItem)
        self.setAlternatingRowColors(True)
        self.setColumnCount(3)
        self.setHeaderLabels(['Object', 'Type', 'Value / Information'])
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.headerItem().setToolTip(0, "Key or index of child data.\nThe type of the key or index is shown in their tooltip.")
        self.headerItem().setToolTip(1, "Type of child data mapped to a key or index.\nAdditional type information is shown in their tooltip.")
        self.headerItem().setToolTip(2, "Value of child data, or its length\n(when data is a nested collection).\nNumpy arrays ar displayed as a table")
        
        self._widget_height_ = self._default_widget_height_
        self.setUniformRowHeights(False)
        
        self.itemClicked.connect(self._slot_setLastActive)
        
        self._widgetsWithSelection_ = set()
        
        self._scipyenWindow_ = None
        self.predicate = None
        self.showPrivate = False
        
        
        #  NOTE: 2025-06-26 21:29:48
        # list of (QtCore.QModelIndex, QtWidgets.QWidget) tuples, where the QTreeWidgetItem associates a QWidget
        self._widgetIndexes_ = list()
        
        ws = user_workspace()
        
        if ws is not None:
            self._scipyenWindow_ = ws["mainWindow"]
            
        else:
            frame_records = inspect.getouterframes(inspect.currentframe())
            for (n,f) in enumerate(frame_records):
                if "ScipyenWindow" in f[0].f_globals:
                    if __has_PyQt6__:
                        self._scipyenWindow_ = f[0].f_globals["ScipyenWindow"]
                    else:
                        self._scipyenWindow_ = f[0].f_globals["ScipyenWindow"].instance()
                    break
                
        self.update()
        
    def _makeTableWidget_(self, data):
        if self._use_TableEditor_:
            # ### BEGIN Timing for debugging
            #
            # timer = QtCore.QElapsedTimer()
            widget = TableEditorWidget(parent=self, readOnly=True)
            signalBlocker = QtCore.QSignalBlocker(widget.tableView)
            
            # timer.start()
            # NOTE: 2025-11-23 08:55:27
            # next line is equivalent to widget._dataModel_.setModelData(data)
            widget.setData(data)
            # print(f"↓{self.__class__.__name__}._makeTableWidget_ for {type(data).__name__}: setting table model data took {timer.elapsed()} milliseconds")
            #
            # ### END   Timing for debugging
            # widget.readOnly=True
            # don't delete; may be useful
            # widget.sig_selectionChanged.connect(self._slot_tableEditorWidgetSelectionChanged)
        else:
            widget = SimpleTableWidget()
            widget.setData(data)
            
        widget.setMaximumHeight(self._widget_height_)
        
        return widget
    
    def paintEvent(self, event:QtGui.QPaintEvent):
        r"""Paints a placeholder text when there is no data"""
        super().paintEvent(event)
        if self._ready_ and self.model() is not None and self.model().rowCount() > 0:
            return
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

    def getWidgetSelection(self, widget:QtWidgets.QWidget) -> list:
        r"""Returns a list of selected QModelIndex objects from widgets
        asociated with tree items.
        The caller should deal with these accordingly.
    """
        if isinstance(widget, TableEditorWidget):
            return widget.tableView.selectedIndexes()
        elif isinstance(widget, SimpleTableWidget):
            return widget.selectedIndexes()
        elif isinstance(widget, (QtWidgets.QPlainTextEdit, QtWidgets.QTextEdit)):
            # NOTE: 2025-05-25 12:10:02
            # QTextBrowser inherits from QTextEdit
            textCursor = widget.textCursor()
            if QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier:
                selectedText = textCursor.selection().toPlainText()
            else:
                selectedText = textCursor.selectedText()
                
            if len(selectedText) == 0:
                return list()
            else:
                return [selectedText]
            
        else:
            return list()
    
    @Slot(QtWidgets.QTreeWidgetItem, int)
    def _slot_setLastActive(self, item, column):
        # print(f"{self.__class__.__name__}<{self.parent().windowTitle()}, {self.parent().parent().windowTitle()}> _slot_setLastActive item {item.data(0,QtCore.Qt.DisplayRole)}")
        self._last_active_item_ = item.data(0,QtCore.Qt.DisplayRole)
        self._last_active_item_column_ = column
        
    @Slot()
    def _slot_treeBuilt(self):
        self.expandToDepth(3)
        self.resizeColumnToContents(0)
        
        self.topLevelItem(0).setText(0, self.top_title)
        
        self._ready_ = True
        
        # print(f"{self.__class__.__name__}<{self.parent().windowTitle()}, {self.parent().parent().windowTitle()}> last item {self._last_active_item_} column {self._last_active_item_column_}")
        if isinstance(self._last_active_item_, str) and len(self._last_active_item_.strip()) and \
            self._last_active_item_column_ < self.columnCount():
                items = self.findItems(self._last_active_item_, QtCore.Qt.MatchExactly, 0)
                if len(items) > 0:
                    # print(f"{self.__class__.__name__}<{self.parent().windowTitle()}, {self.parent().parent().windowTitle()}> last items {[i.data(0, QtCore.Qt.DisplayRole) for i in items]}")
                    item = items[0]
                    index = self.indexFromItem(item, self._last_active_item_column_)
                    target = self.itemFromIndex(index)
                    if __has_PyQt6__ or __has_PySide6__:
                        self.scrollToItem(target)#, self._last_active_item_column_)
                    else:
                        self.scrollToItem(target, self._last_active_item_column_)
                    target.setSelected(True)
                    self.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)
        
    @Slot()
    def _slot_tableEditorWidgetSelectionChanged(self):
        widget = self.sender()
        indexes = widget.tableView.selectedIndexes()
        # print(f"{self.__class__.__name__}._slot_tableEditorWidgetSelectionChanged: {len(indexes)} selected")
        if widget in self._widgetsWithSelection_:
            if len(indexes) == 0:
                self._widgetsWithSelection_.remove(widget)
                
            else:
                pass # for now
            # TODO 2025-05-24 22:56:01 
            # finalize me - see tableeditorwidget
            # also implement similar things in SimpleTableWidget, or get rid of that class
            # also see if matrixviewer can be consolidated/merged in tableeditorwidget
        else:
            if len(indexes):
                self._widgetsWithSelection_.add(widget)
        # print(f"{self.__class__.__name__}._slot_tableEditorWidgetSelectionChanged: {len(self._widgetsWithSelection_)} widgets with selection")
        
    def setSupportedDataTypes(self, types:tuple):
        if isinstance(types, tuple) and len(types):
            self._supported_data_types_ = types
            
    @Slot(dict)
    def slot_setData(self, what:dict):
        data = what.get("data", None)
        predicate = what.get("predicate", None)
        showPrivate = what.get("showPrivate", None)
        top_title = what.get("top_title", "")
        dataTypeStr = what.get("dataTypeStr", None)
        hideRoot = what.get("hideRoot", False)
        
        self.setData(data, predicate=predicate, showPrivate=showPrivate,
                     top_title=top_title, dataTypeStr=dataTypeStr,
                     hideRoot=hideRoot)
            
    def setData(self, data, predicate=None, showPrivate:bool=False,
                top_title:str = "", dataTypeStr = None, hideRoot=False):
        r"""data should be a dictionary."""
        # print(f"{self.__class__.__name__}<{self.parent().windowTitle()}, {self.parent().parent().windowTitle()}> set data")
        self._visited_.clear()
        self.predicate = predicate
        self.showPrivate = showPrivate
        
        # NOTE: 2025-06-28 13:55:20
        # self._private_data_ is used to build the tree model; it can be the
        # 'data' itself, OR a mapping representation of its members.
        # 'has_dynamic_private' is False in the former case, and True in the latter
        self._private_data_, self.has_dynamic_private = self._parse_data_(data)
        if self.has_dynamic_private and not self.showPrivate:
            self._private_data_ = dict(list(filter(lambda x: not x[0].startswith("_"), self._private_data_.items())))
        
        if len(top_title.strip()) == 0:
            self.top_title = "/"
        else:
            self.top_title = top_title
            
        # NOTE: 2022-12-15 23:25:05
        # super().setData(data) # calls self.buildTree(...), which then calls self.parse(...)
        self.clear()
        # self.widgets = []
        self.nodes = {}
        
        # NOTE: 2025-11-24 16:46:02
        # ### BEGIN  DECIDE on one:
        #
        # Either this:
        #
#         self.buildTree(self._private_data_, self.invisibleRootItem(), 
#                        keyType=str,typeStr=dataTypeStr, predicate=predicate,
#                        hideRoot=hideRoot)
#         
#         self.topLevelItem(0).setText(0, self.top_title)
        # self._slot_treeBuilt()
        
        #
        # OR this:
        #
        
        worker = WorkerThread(self, self.buildTree, self._private_data_, self.invisibleRootItem(),
                              keyType = str, typeStr = dataTypeStr, predicate=predicate, hideRoot=hideRoot)
        worker.signals.signal_Finished.connect(self._slot_treeBuilt)
        worker.run()
        
        #
        # ### END    DECIDE on one:
        
    def _parse_dataclass(self, data) -> tuple:
        datafields = dataclasses.fields(data)
        return dict(map(lambda x: (x.name, getattr(data, x.name)), datafields))
    
    def _parse_data_(self, data) -> tuple:
        r"""
        Returns a tuple (a, b), where:
        
        a: dict is the iterable container (a mapping or otherwise) upon which the 
            tree model is built.
            'a' can be the data itself, or a mapping representation of its members
            (i.e. a dictionary) generated using datatypes.inspect_members(…). This
            is similar, but not identical, to accessing the __dict__ attribute 
            of the data.
        
        b: flag indicating whether 'a' is the data itself or a mapping representation of its
            attributes (for any non-iterable object/container)
        
            'b' is True when the data itself is a container suitable for representation
            in a tree model
        
    """
        mro = inspect.getmro(type(data))
        if all(t not in self._supported_data_types_ for t in mro) and not inspect.isroutine(data) and not isinstance(data, (types.ModuleType, pkgutil.ModuleInfo)) and data is not None:
            # NOTE: 2025-06-28 13:57:28
            # generate a mapping representation of data's members upon which
            # the tree model is built
            return datatypes.inspect_members(data, self.predicate), True
        else:
            # NOTE: 2025-06-28 13:58:14
            # The data is suitable for direct representation by a tree model
            return data, False
        
    def memoize(self, obj, path):
        if id(obj) not in self._visited_:
            idx = len(self._visited_)
            self._visited_[id(obj)] = (idx, type(obj), path)
       
    def buildTree(self, data:object, parent:QtWidgets.QTreeWidgetItem,
                  name:str="", keyType:type=str, nameTip:str="", typeStr:typing.Optional[str] = None, 
                  predicate:typing.Optional[typing.Any]=None, 
                  hideRoot:bool=False, path:tuple=()):
        r"""Builds the tree hierarchy.
        Initially written to override pyqtgraph.DataTreeWidget.buildTree(), but now see NOTE: 2025-11-23 08:22:37
        
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
    
        WARNING:
        This function may call itself recursively if the data is a mapping collection !
        
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
        #   the parent item) is the tree widget's invisible root item
        #
        # (b) an item constructed on a string list for the three columns, added
        # to the 'parent' node passed to this method call
        #
        
        # print(f"{self.__class__.__name__}.buildTree: hideRoot = {hideRoot}")
        
        # if hideRoot:
        #     node = parent 
        # else:
        #     node = QtWidgets.QTreeWidgetItem([name, "", ""])
        #     node.setData(0, QtCore.Qt.UserRole, type(data))
        #     parent.addChild(node)
        
        # NOTE: 2025-05-26 19:36:29
        # data in user role:
        # column 0: type of the key (int or str) - except for the top child where key type is str
        # column 1: type of the data represented by the child
        node = QtWidgets.QTreeWidgetItem([name, "", ""])
        node.setData(1, QtCore.Qt.UserRole, type(data))
        node.setData(0, QtCore.Qt.UserRole, keyType) 
        parent.addChild(node)
            
        # print(f"{self.__class__.__name__}.buildTree: predicate = {predicate}")
        
        # record the path to the node so it can be retrieved later
        # (this is used by the tree widget)
        
        # NOTE: 2021-08-15 14:41:32
        # self.nodes is a dict
        # path is a tuple (as index branch path) - this is immutable, hence 
        # hashable, hence usable as dict key
        self.nodes[path] = node
        
        # NOTE: 2025-11-16 14:31:50
        # call self.parse(…) in order to get the type, descctiption, collection 
        # of children (if any), the widget (delegate?) to display this data and 
        # a couple of extra bits such as the tip indicating the data type, and 
        # whether to show the description in the same row as the parent node
        # or in a separate widget)
        
        # ### BEGIN Timing measures for debugging
        # 
        # timer = QtCore.QElapsedTimer()
        # timer.start()
        typeStr_, desc, children, widget, typeTip, showDescInParentNode = self.parse(data, path, predicate=predicate)
        # print(f"{self.__class__.__name__}.buildTree: parsing {typeStr_} data with {len(children)} children and {type(widget).__name__} widget took {(timer.elapsed() *pq.ms).rescale(pq.s)}")
        # print(f"{self.__class__.__name__}.buildTree: parsing {typeStr_} data with {len(children)} children and {type(widget).__name__} widget took {timer.elapsed()} milliseconds")
        #
        # ### END   Timing measures for debugging
        
        # print(f"{self.__class__.__name__}.buildTree for {type(data)} -> {len(children)} children")
        
        if not isinstance(typeStr, str) or len(typeStr.strip()) == 0:
            typeStr = typeStr_
        
        # NOTE: 2022-03-04 09:04:50
        # nameTip is NOT set when this method is called by super().setData()
        # hence it will have the default value (an empty string)
        node.setToolTip(0, nameTip)
        node.setText(1, typeStr)
        node.setToolTip(1, typeTip)
        if showDescInParentNode:
            node.setText(2, desc)
        
        # ### BEGIN About caching code
        
        # BUG: 2025-05-27 17:51:58 FIXME/TODO
        # without the caching code below this work well, BUT:
        # any container that is referenced as a member of itself will be prone
        # to infinite recursion!
        #
        # I considered weakrefs, but NOT all object in Scipyen/Python support
        # weak references!
        
        # NOTE: caching code works but is buggy, see BUG: 2025-05-27 17:32:09 FIXME/TODO
        # # limtations to the id() builtin
        # # needs self._visited_ as a dict !
        # I am using this because this bug is far less annoying than the one 
        # without caching (BUG: 2025-05-27 17:51:58 )
        # data_type = type(data)
        # if not issubclass(type(data), NOTMEMOIZED + PODS):
        #     # self.memoize(data)
        #     if id(data) not in self._visited_:
        #         idx = len(self._visited_)
        #         self._visited_[id(data)] = (idx, data_type, path)
                
        
        
        # NOTE: 2025-05-21 16:26:20 
        # why not applying this rule to other kinds of data as well?
        # if isinstance(data, NestedFinder.nesting_types):
        #     if id(data) not in self._visited_.keys():
        #         self._visited_[id(data)] = (typeStr, path)
        
        # BUG: 2025-05-27 17:51:14 this one breaks it all!
        # # needs self._visited_ as a list
        # data_type = type(data)
        # if data_type not in NOTMEMOIZED + PODS:
        #     if data not in self._visited_:
        #         self._visited_.append(data)
        
        # ### END   About caching code
        
        
        # Truncate description and add text box if needed
        # if len(desc) > 100:
        #     desc = desc[:97] + '...'
        #     if widget is None:
        #         widget = QtWidgets.QPlainTextEdit(str(data))
        #         widget.setMaximumHeight(200)
        #         widget.setReadOnly(True)
        
        # Add widget to new subnode
        # TODO 2025-09-21 22:33:30 
        # this seems like a good place to create/insert a delegate widget for data editing as appropriate
        # FIXME: this needs defining a model (currently this uses QAbstractItemModel)
        # TODO: the way to go seems to take out the parse() and buildTree() code and place it
        # into a custom TreeModel (to be created); other code to move there:
        # memoize(), getWidgetSelection(), _parse_data_(), _parse_dataclass(), _makeTableWidget_()
        # and maybe _slot_tableEditorWidgetSelectionChanged(), setSupportedDataTypes()
        if widget is not None:
            # NOTE: 2025-11-16 14:36:15
            # is a widget has been created by self.parse, use it as item widget
            # for the newly created subnode
            # 
            # self.widgets.append(widget)
            subnode = QtWidgets.QTreeWidgetItem(["", "", ""])
            node.addChild(subnode)
            self.setItemWidget(subnode, 0, widget)
            modelndx = self.indexFromItem(subnode)
            parentndx = self.indexFromItem(node)
            self.setFirstColumnSpanned(modelndx.row(), parentndx, True)
            # self.setFirstItemColumnSpanned(subnode, True) # obsolete !!!
            
        # NOTE: 2025-11-23 08:43:04
        # recurse into children (a dict)
        if isinstance(children, dict):
            for key, child_data in children.items():
                keyType = type(key)
                if isinstance(key, type):
                    keyrepr = f"{key.__module__}.{key.__name__}"
                    keytip = f"member type: {key}"
                    
                elif type(key).__name__ == "instance":
                    keyrepr = key.__class__.__name__
                    keytip = f"member type: {key}"
                    # keytip = str(key)
                    
                elif isinstance(data, types.SimpleNamespace):
                    keyrepr = f"{key}"
                    keytip = f"member type: {type(child_data).__name__}"
                    
                elif isinstance(data, scipy.optimize.Bounds):
                    keyrepr = f"{key}"
                    keytip = f"member type: {type(child_data).__name__}"
                    
                elif dataclasses.is_dataclass(data) and not isinstance(data, type):
                    keyrepr = f"{key}"
                    keytip = f"field type: {type(child_data).__name__}"
                    
                elif isinstance(data, (tuple, list, deque, typing.Sequence, dict, types.MappingProxyType)):
                    keyrepr = f"{key}"
                    keytip = f"index type: {type(key).__name__}" # this here is crucial; I want type of key not of what is mapped to it
                    
                else:
                    keyrepr = str(key)
                    keytip = f"object type: {type(key).__name__}"
                    
                #              data        parent, name, nameTip,
                self.buildTree(child_data, node, name=keyrepr, keyType = keyType, nameTip = keytip, 
                            predicate=predicate, path=path+(keyrepr,)) # so hideRoot is always False?

    def parse(self, data, path, predicate=None, typeStr=None) -> tuple:
        r"""Figures out if data is to be represented as a (sub)tree or a widget.
        
        Originally overrided pyqtgraph.DataTreeWidget.parse(), but now see NOTE: 2025-11-23 08:22:37 
        
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
        try:
            from pyqtgraph.widgets.DataTreeWidget import HAVE_METAARRAY
        except:
            HAVE_METAARRAY = None

        from core.datatypes import (is_namedtuple, TypeEnum)
        from imaging.axiscalibration import (AxesCalibration, AxisCalibrationData, ChannelCalibrationData)
        from imaging.axisutils import axisTypeStrings
        from systems.PrairieView import (PVObject,PVScan, PVSequence, PVFrame, PVSystemConfiguration,
                                        PVStateShard, PVStateValue, PVIndexedValue, PVSubIndexedValue, 
                                        PVSubIndexedValueList, PVLinescanDefinition)
        
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
        showDescInParentNode = True
        children = dict()
        
        
        # BUG: 2025-05-27 17:32:09 FIXME/TODO
        # checking for id() can have unexpected behaviour => object may be displayed as 
        # a reference to other object, when in fact it is not
        # NOTE: 2025-05-21 16:27:56 see NOTE: 2025-05-21 16:26:20 
        if not issubclass(type(data), NOTMEMOIZED + PODS): # or (isinstance(data, np.ndarray) and data.size<=1):
            # data_id = id(data)
            if id(data) in self._visited_:
                x = self._visited_.get(id(data), None)
                # print(x)
                if x is not None:
                    objtype = x[1]
                    path = "/".join(list(x[2]))
                    if len(path.strip()) == 0:
                        full_path = self.top_title
                    else:
                        if self.top_title == "/":
                            full_path = "/" + path
                        else:
                            full_path = "/".join([self.top_title, path])
                    desc = "<reference to %s at %s >" % (objtype.__name__, full_path)
                    return typeStr, desc, children, widget, typeTip, showDescInParentNode
            else:
                self.memoize(data, path)
                
        if data is None:
            typeStr = "(None)"
            return typeStr, desc, children, widget, typeTip, showDescInParentNode
        
        elif data is dataclasses.MISSING:
            desc = str(MISSING)
            return typeStr, desc, children, widget, typeTip, showDescInParentNode
        
        elif type(data) is type(pd.NA):
            desc = str(pd.NA)
            return typeStr, desc, children, widget, typeTip, showDescInParentNode
            
        # print(f"{self.__class__.__name__}.parse -> data_type: {data_type} ")
        try:
            if isinstance(data, type):
                desc = type(data).__name__
                if isinstance(data, enum.EnumType):
                    children = data.__members__

            if isinstance(data, pkgutil.ModuleInfo):
                desc = " ".join(["Fields:", "; ".join(list(map(lambda f: f" {f} = {getattr(data, f, None)}", data._fields)))])
                
            elif isinstance(data, NestedFinder.nesting_types + (set,)):
                # NOTE: 2025-05-21 16:15:26
                # here 'widget' is None — this will force the caller (i.e. buildTree)
                # to descend into the children of the data and build up a subtree
                if issubclass(type(data), (dict, types.MappingProxyType)):
                    # NOTE: 2025-05-21 16:17:37
                    # 'widget' is None, here
                    desc = "length=%d" % len(data)
                    # NOTE: 2021-07-20 09:52:34
                    # dict objects with mixed key types cannot be sorted
                    # therefore we resort to an indexing vector
                    ndx = [i[1] for i in sorted((str(k[0]), k[1]) for k in zip(data.keys(), range(len(data))))]
                    items = [i for i in data.items()]
                    children = dict([items[k] for k in ndx])
                        
                elif issubclass(type(data), (list, tuple, deque, set)):
                    # NOTE: 2025-05-21 16:17:37
                    # 'widget' is None, here
                    desc = "length=%d" % len(data)
                    # NOTE: 2021-07-24 14:57:02
                    # accommodate namedtuple types
                    if is_namedtuple(data):
                        children = data._asdict()
                    else:
                        children = dict(enumerate(data))
                        
                # else:
                #     print("fallthrough")
                
            elif HAVE_METAARRAY and (hasattr(data, 'implements') and data.implements('MetaArray')):
                # NOTE: 2025-05-21 16:17:37
                # 'widget' is None, here
                children = dict([
                    ('data', data.view(np.ndarray)),
                    ('meta', data.infoCopy())
                ])
            
            elif isinstance(data, types.SimpleNamespace):
                lbl = f"{data.__class__.__name__} object"
                desc = " ".join([lbl, "with", f"{len(data.__dict__)} members"])
                # NOTE: 2025-05-21 16:17:37
                # 'widget' is None, here
                children = data.__dict__
                
            elif isinstance(data, AxesCalibration):
                lbl = f"{data.__class__.__name__} object"
                desc = " ".join([lbl, "with", f"{len(data.calibrations)} axes"])
                children = dict(enumerate(data.calibrations))
                
            elif isinstance(data, AxisCalibrationData):
                lbl = f"{data.__class__.__name__} object"
                desc = " ".join([lbl, "with name (type):", f"'{data.name}' ('{axisTypeStrings(data.type, single=True)[0]})'"])
                if data.isChannels:
                    desc += f" and {len(data.channels)} channels"
                    children = dict(enumerate(data.channels))
                    
            elif isinstance(data, ChannelCalibrationData):
                lbl = f"{data.__class__.__name__} object"
                desc = " ".join([lbl, "with name:", f"'{data.name}'", "index:", f"{data.index}", "acquisition index:", f"{data.acquisition_index}"])
                
            elif isinstance(data, PVObject):
                lbl = f"{data.__class__.__name__} object"
                if isinstance(data, PVScan):
                    desc = " ".join([lbl, f"{data.attributes}"])
                    # children = {"State": data.state, "Sequences":data.sequences)
                elif isinstance(data, PVSequence):
                    desc = " ".join([lbl, f"Type: {data.attributes['sequencetypename']} with {len(data.frames)} frames"])
                    # children = {"State": data.state, "Frames": data.frames}
                elif isinstance(data, PVFrame):
                    desc = " ".join([lbl, f"Channels: {data.channels}"])
                    # children = dict("State": data.state)
                elif isinstance(data, (PVSystemConfiguration, PVIndexedValue, PVSubIndexedValue)):
                    if hasattr(data, "description") and isinstance(data.description, str) and len(data.description.strip()):
                        desc = " ".join([lbl, data.description])
                # elif isinstance(data, PVLinescanDefinition):
                    # desc = " ".join([lbl, data.description])
                    
                children = data.as_dict()
                
            elif isinstance(data, pd.DataFrame):
                desc = "length=%d, columns=%d" % (len(data), len(data.columns))
                widget = self._makeTableWidget_(data)
                
            elif isinstance(data, pd.Series):
                desc = "length=%d, dtype=%s" % (len(data), data.dtype)
                widget = self._makeTableWidget_(data)
                
            elif isinstance(data, pd.Index):
                desc = "length=%d" % len(data)
                widget = self._makeTableWidget_(data)
                
            elif isinstance(data, Interval):
                desc = f"Interval '{data.name}' with {len(data)} subinterval(s)"
                children = {"t0": data.t0, "t1": data.t1, "durations": data.durations, 
                            "extent": data.extent, "labels": data.labels,
                            "annotations": data.annotations,
                            "description": data.description,
                            }
                
            elif isinstance(data, (neo.Epoch, DataZone)):
                desc = f"{type(data).__name__} '{data.name}' with {len(data)} subinterval(s)"
                children = {"times": data.times, "durations": data.durations, 
                            "labels": data.labels, "annotations": data.annotations,
                            "description": data.description}
                
            elif isinstance(data, (neo.Event, DataMark, TriggerEvent)):
                desc = f"{type(data).__name__} '{data.name}' with {len(data)} mark(s)"
                children = {"times": data.times, "labels": data.labels}
                if isinstance(data, (DataMark, TriggerEvent)):
                    children.update({"type": data.type, "relative": data.relative})
                children.update({"annotations": data.annotations,
                                 "description": data.description})
                
            elif isinstance(data, neo.core.dataobject.DataObject):
                desc = "shape=%s dtype=%s" % (data.shape, data.dtype)
                if data.size == 1:
                    widget = QtWidgets.QLabel(str(data))
                else:
                    widget = self._makeTableWidget_(data)
                    
            elif isinstance(data, pq.Quantity):
                if data.ndim == 0 or (data.ndim == 1 and data.size <= 1):
                    desc = f"{data}"
                else:
                    desc = "shape=%s dtype=%s" % (data.shape, data.dtype)
                    if data.ndim < 3 or not any(v > 1 for v in data.shape[2:]):
                        widget = self._makeTableWidget_(data)
                    
            elif isinstance(data, pq.dimensionality.Dimensionality):
                desc = f"{data}"
                
            elif isinstance(data, np.ndarray):
                if data.size == 1:
                    desc = f"{data}"
                else:
                    desc = "shape=%s dtype=%s" % (data.shape, data.dtype)
                    if data.ndim < 3 or not any(v > 1 for v in data.shape[2:]):
                        widget = self._makeTableWidget_(data)
                    
            elif isinstance(data, (vigra.filters.Kernel1D, vigra.filters.Kernel2D)):
                widget = self._makeTableWidget_(data)
                    
            elif isinstance(data, (datetime.datetime, datetime.date, datetime.time, datetime.timedelta, datetime.timezone)):
                desc = f"{data}"
                
            elif isinstance(data, types.TracebackType):  ## convert traceback to a list of strings
                frames = list(map(str.strip, traceback.format_list(traceback.extract_tb(data))))
                widget = QtWidgets.QPlainTextEdit(str('\n'.join(frames)))
                widget.setMaximumHeight(200)
                widget.setReadOnly(True)
                
            elif isinstance(data, scipy.optimize.Bounds):
                children = {"lb": data.lb, "ub": data.ub, "keep_feasible": data.keep_feasible}
                
            elif isinstance(data, (str, bytes, bytearray)):
                if len(data)> 100:
                    _data = data[:97] if isinstance(data, str) else data.decode()[:97]
                    _data += "..."
                    desc = f"{type(data)} with {len(data)} elements"
                    txt = data if isinstance(data, str) else data.decode()
                    widget = QtWidgets.QPlainTextEdit(txt)
                    widget.setMaximumHeight(200)
                    widget.setReadOnly(True)
                else:
                    desc = data if isinstance(data, str) else data.decode()
                    
            elif isinstance(data, (bool, int, float, complex, fractions.Fraction, decimal.Decimal, numbers.Number)):
                desc = f"{data}"
                
            elif dataclasses.is_dataclass(data):
                datafields = dataclasses.fields(data)
                lbl = f"{data.__class__.__name__} object"
                desc = " ".join([lbl, "with", f"{len(datafields)} fields"])
                
                # NOTE: 2025-07-05 11:30:31
                # Some dataclasses, especially those inheriting from ScipyenDataclass
                # for example, ScanData,  may have dynamically generated properties, 
                # which will NOT be captured by the dataclasses.fields() function.
                # 
                # membernames = list(map(lambda m: m[0], filter(lambda m: not datatypes.is_routine(m[1]), inspect.getmembers(data))))
                try:
                    fieldnames = list(map(lambda f: f.name, datafields))
                    membernames = list(data.__dict__.keys())
                    childnames = list(sorted(unique(membernames + fieldnames)))
                    children = dict(map(lambda c: (c, getattr(data, c)), childnames))
                except:
                    traceback.print_exc()
                    print(f"{print_styled(f'for {type(data).__name__} data', color='red')}")
                    
                # children = dict(map(lambda x: (x.name, getattr(data, x.name)), datafields))
                
            elif isinstance(data, enum.Enum):
                desc = f"{data} ({data.name})"
                
            elif isinstance(data, pathlib.Path):
                desc = data.as_posix()

            elif isinstance(data, types.ModuleType):
                desc = data.__name__
            else:
                desc = type(data).__name__
                
            if widget and self._scipyenWindow_:
                if __has_PySide6__:
                    btns = self.findChildren(QtWidgets.QToolButton) + self.findChildren(QtWidgets.QPushButton)
                else:
                    btns = self.findChildren((QtWidgets.QToolButton, QtWidgets.QPushButton))
                
                for b in btns:
                    if b.iconSize() != self._scipyenWindow_.iconSize():
                        b.setIconSize(self._scipyenWindow_.iconSize())
                
            return typeStr, desc, children, widget, typeTip, showDescInParentNode
        
        except:
            # print(f"{self.__class__.__name__}.parse data type : {type(data).__name__}, data: {data}")
            raise
        
