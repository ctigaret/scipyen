# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r""" """
# TODO: 2025-03-10 23:21:21
# implement editing function, where applicable
# NEEDS proxy editor widgets
from __future__ import print_function

import os, types, traceback, inspect, dataclasses, numbers, sys
import pathlib
import datetime
import fractions, decimal
import pkgutil
import typing
import enum
from collections import deque
from dataclasses import MISSING
import math

import qtpy
from qtpy import (
    QtCore,
    QtGui,
    QtWidgets,
    QtXml,
    QtSvg,
    QtNetwork,
)
from qtpy.QtCore import (
    Signal,
    Slot,
    Property,
)

__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6
    from PySide6 import Shiboken

    # from PySide6.QtCore import (Signal, Slot, Property,)
    from PySide6.QtUiTools import loadUiType  # -- A-HA!

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

if neo.__version__ >= "0.13.0":
    from neo.core.objectlist import ObjectList as NeoObjectList
import quantities as pq
import numpy as np
import scipy
import pandas as pd
import vigra

import core.datatypes as datatypes

import imaging.axiscalibration
from imaging.axiscalibration import (
    AxesCalibration,
    AxisCalibrationData,
    ChannelCalibrationData,
)
# from imaging.axiscalibration import AxesCalibration

import imaging.scandata
from imaging.scandata import ScanData, AnalysisUnit
from imaging.axisutils import axisTypeStrings

from core.triggerprotocols import TriggerProtocol
from core.triggerevent import DataMark, TriggerEvent, TriggerEventType

import core.datasignal as datasignal
from core.datasignal import DataSignal, IrregularlySampledDataSignal

import core.datazone as datazone
from core.datazone import DataZone, Interval

from core import xmlutils, strutils

from core.workspacefunctions import validate_varname, user_workspace

# from core.utilities import (get_nested_value, set_nested_value, counter_suffix, )

from core.utilities import NestedFinder, unique

from core.prog import safewrapper, safeguiwrapper, print_styled

from core.traitcontainers import (
    DataBag,
    DataBagTraitsObserver,
)

from gui.widgets.tablewidget import SimpleTableWidget
from gui.widgets.tableeditorwidget import TableEditorWidget

# from gui.widgets.tableeditorwidget import (TableEditorWidget, TabularDataModel,)
from gui.pictgui import WorkerThread
from gui.widgets.small_widgets import QuantitySpinBox, ComplexSpinBox
from gui.delegates import PythonItemDelegate
from gui.workspacegui import GuiMessages

NOTMEMOIZED = (
    tuple,
    type(None),
    type(MISSING),
    type(pd.NA),
    type,
    np.ndarray,
    types.ModuleType,
    pkgutil.ModuleInfo,
)
PODS = (
    bool,
    int,
    float,
    bytes,
    bytearray,
    str,
    np.floating,
    np.complexfloating,
    complex,
)


class InteractiveTreeWidget(QtWidgets.QTreeWidget):
    r"""QTreeWidget that enables:


    1. Support for custom context menu.

    2. Use Scipyen gui.tableeditor.TableEditorWidget

    3. Support for any key type, as long as it is hashable.

    4. Support for circular references to hierarchical data objects (subsequent
        references ot the same object are NOT traversed; instead, a path to the
        first encountered reference - in depth-first order - is displayed)

    Inspired by pyqtgraph.widget.DataTreeWidget (originally, a subclass of it)


    """

    # NOTE: 2025-11-23 08:22:37
    # CHANGELOG:
    # Up to mid March 2025: subclass of pyqtgraph.widget.DataTreeWidget
    # After that: direct subclass of QtWidgets.QTreeWidget

    # NOTE: 2025-05-24 22:21:05
    # child widgets are either None, TableEditorWidget, SimpleTableWidget, or QPlainTextEdit

    _default_widget_height_ = 200

    # NOTE: 2026-02-03 14:29:21
    # ATTENTION this NEVER changes the object's structure (dict keys, sequence indices,
    # row/column indexes of dataframe/series field names of dataclasses and named tuples,
    # fields of structured arrays )
    #
    # However, these object CAN be manipulated at the console...
    #
    # So, this widget is ONLY concerned with the CONTENT (values) of the fields,
    # and NOT their symbols.

    #
    # NOTE: 2026-02-02 09:20:10
    # stand-in for QStyledItemDelegate:
    # until I get my head around a new DataTreeModel/Item/View beign worked on,
    # in the ``gui.widgets.datatreeview`` module
    #
    # a map of object type ↦ dict: editing widget class ↦ predicate
    #
    #   predicate is a unary function returning a bool, used to check the condition under
    # a specified widget is to be used with the given data type

    mappingTypes = (dict, types.MappingProxyType)
    sequenceTypes = (typing.Sequence, tuple, list, deque, bytes)
    iterableCollectionTypes = sequenceTypes + mappingTypes
    
    sig_valueChanged = Signal(object, object, name="sig_valueChanged")

    def __init__(self, *args, **kwargs):
        r"""
        Keyword parameters (selective list):
        ------------------------------------
        useTableEditor:bool, default is False;
            When True, use TableEditorWidget, else use SimpleTableWidget
        """
        parent = kwargs.pop("parent", None)
        super().__init__(parent=parent)
        self._ready_: bool = False

        # NOTE: 2025-06-28 14:02:36
        # list of tuple(obj:typing.Any, name:str), where
        # obj is the data itself (or a child) IF the data is a suported type
        # else it is the _private_data_ generated by self
        # self._obj_cache_ = list()
        # self._cache_index_ = 0
        self._data_ = None
        self._dataTypeStr_: str = ""

        # contains data selected from child widgets (table, and text widgets)
        self._subselections_ = list()

        self.nodes = {}  # path ↦ (node, widget)

        self._readOnly_: bool = kwargs.pop("readOnly", True)

        self._use_TableEditor_ = kwargs.pop("useTableEditor", False)
        self._supported_data_types_ = kwargs.pop("supported_data_types", tuple())
        if not isinstance(self._supported_data_types_, tuple) or not all(
            isinstance(v, type) for v in self._supported_data_types_
        ):
            self._supported_data_types_ = tuple()
        self._visited_ = dict()  # {}
        # self._visited_ = list()
        self.root_title = "/"
        self._last_active_item_ = None
        self._last_active_item_column_ = 0
        self.has_dynamic_private = False
        self._private_data_ = None
        # DataTreeWidget.__init__(self, *args, **kwargs)
        self.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerItem)
        self.setAlternatingRowColors(True)
        self.setColumnCount(3)
        self.setHeaderLabels(["Object", "Type", "Value / Information"])
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.headerItem().setToolTip(
            0,
            "Key or index of child data.\nThe type of the key or index is shown in their tooltip.",
        )
        self.headerItem().setToolTip(
            1,
            "Type of child data mapped to a key or index.\nAdditional type information is shown in their tooltip.",
        )
        self.headerItem().setToolTip(
            2,
            "Value of child data, or its length\n(when data is a nested collection).\nNumpy arrays ar displayed as a table",
        )

        self._widget_height_ = self._default_widget_height_
        self.setUniformRowHeights(False)

        if not self._readOnly_:
            self.itemClicked.connect(
                self._slot_setLastActive
            )  # not documented in Qt6 ?!?

        self._widgetsWithSelection_ = set()

        self._scipyenWindow_ = None
        self.predicate = None
        self.showPrivate = False
        self.hideRoot = False

        self._editor_nodes_dict_: dict = dict()

        #  NOTE: 2025-06-26 21:29:48
        # list of (QtCore.QModelIndex, QtWidgets.QWidget) tuples, where the QTreeWidgetItem associates a QWidget
        self._widgetIndexes_ = list()

        ws = user_workspace()

        if ws is not None:
            self._scipyenWindow_ = ws["mainWindow"]

        else:
            frame_records = inspect.getouterframes(inspect.currentframe())
            for n, f in enumerate(frame_records):
                if "ScipyenWindow" in f[0].f_globals:
                    if __has_PyQt6__:
                        self._scipyenWindow_ = f[0].f_globals["ScipyenWindow"]
                    else:
                        self._scipyenWindow_ = (
                            f[0].f_globals["ScipyenWindow"].instance()
                        )
                    break

        self._delegate_ = PythonItemDelegate()
        self._delegate_.sig_dataChanged.connect(self._slot_delegateDataChanged)

        self.update()

    # def _getEditor_(self, data) -> QtWidgets.QWidget | None:
    #     editor_dicts = list(filter(lambda v: v, map(lambda i: i[1] if i[0] in inspect.getmro(type(data)) else None, self._editors_.items())))
    #     if len(editor_dicts):
    #         editor_dict = editor_dicts[0]
    #         editors = list(filter(lambda v: v, map(lambda k: (k[0] if k[1](data) else None), editor_dict.items())))
    #         if len(editors):
    #             return editors[0]

    def _makeTableWidget_(self, data):
        if self._use_TableEditor_:
            # ### BEGIN Timing for debugging
            #
            # timer = QtCore.QElapsedTimer()
            widget = TableEditorWidget(parent=self, readOnly=True, enforceReadOnly=True)
            signalBlocker = QtCore.QSignalBlocker(
                widget.tableView
            )  # is this needed !?!

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

    def paintEvent(self, event: QtGui.QPaintEvent):
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

    def getWidgetSelection(self, widget: QtWidgets.QWidget) -> list:
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
        self._last_active_item_ = item.data(0, QtCore.Qt.DisplayRole)
        self._last_active_item_column_ = column

    @Slot(QtWidgets.QWidget)
    def _slot_delegateDataChanged(self, widget: QtWidgets.QWidget):
        path = self.getObjectPathForWidget(widget)
                
        # print(
        #     f"{self.__class__.__name__}._slot_delegateDataChanged: {self._delegate_._currentData_}, path = {path}"
        # )

        self.sig_valueChanged.emit(self._delegate_._currentData_, path)
        pass
    
    def getObjectPathForWidget(self, widget: QtWidgets.QWidget):
        paths = list(filter(lambda i: i is not None, map(lambda i: i[0] if widget in i[1] else None, self.nodes.items())))
        if len(paths):
            return paths[0]
    
    def getItemForWidget(self, widget: QtWidgets.QWidget) -> QtWidgets.QTreeWidgetItem | None:
        items = list(filter(lambda i: i is not None, map(lambda i: i[1][0] if widget in i[1] else None, self.nodes.items())))
        if len(items) == 1:
            return items[0]

    @Slot()
    def _slot_treeBuilt(self):
        print(f"{self.__class__.__name__}._slot_treeBuilt: self._readOnly_ = {self._readOnly_}")

        self.expandToDepth(3)
        self.resizeColumnToContents(0)

        self.topLevelItem(0).setText(0, self.root_title)


        self._ready_ = True

        # print(f"{self.__class__.__name__}<{self.parent().windowTitle()}, {self.parent().parent().windowTitle()}> last item {self._last_active_item_} column {self._last_active_item_column_}")
        if (
            isinstance(self._last_active_item_, str)
            and len(self._last_active_item_.strip())
            and self._last_active_item_column_ < self.columnCount()
        ):
            items = self.findItems(self._last_active_item_, QtCore.Qt.MatchExactly, 0)
            if len(items) > 0:
                # print(f"{self.__class__.__name__}<{self.parent().windowTitle()}, {self.parent().parent().windowTitle()}> last items {[i.data(0, QtCore.Qt.DisplayRole) for i in items]}")
                item = items[0]
                index = self.indexFromItem(item, self._last_active_item_column_)
                target = self.itemFromIndex(index)
                if __has_PyQt6__ or __has_PySide6__:
                    self.scrollToItem(target)  # , self._last_active_item_column_)
                else:
                    self.scrollToItem(target, self._last_active_item_column_)
                target.setSelected(True)
                self.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)

        self._setWidgetsEditableState_()

    @Slot()
    def _slot_tableEditorWidgetSelectionChanged(self):
        widget = self.sender()
        indexes = widget.tableView.selectedIndexes()
        # print(f"{self.__class__.__name__}._slot_tableEditorWidgetSelectionChanged: {len(indexes)} selected")
        if widget in self._widgetsWithSelection_:
            if len(indexes) == 0:
                self._widgetsWithSelection_.remove(widget)

            else:
                pass  # for now
            # TODO 2025-05-24 22:56:01
            # finalize me - see tableeditorwidget
            # also implement similar things in SimpleTableWidget, or get rid of that class
            # also see if matrixviewer can be consolidated/merged in tableeditorwidget
        else:
            if len(indexes):
                self._widgetsWithSelection_.add(widget)
        # print(f"{self.__class__.__name__}._slot_tableEditorWidgetSelectionChanged: {len(self._widgetsWithSelection_)} widgets with selection")

    def setSupportedDataTypes(self, types: tuple):
        if isinstance(types, tuple) and len(types):
            self._supported_data_types_ = types

    @Slot(dict)
    def slot_setData(self, what: dict):
        data = what.get("data", None)
        predicate = what.get("predicate", None)
        showPrivate = what.get("showPrivate", None)
        root_title = what.get("root_title", "")
        dataTypeStr = what.get("dataTypeStr", None)
        hideRoot = what.get("hideRoot", False)

        self.setData(
            data,
            predicate=predicate,
            showPrivate=showPrivate,
            root_title=root_title,
            dataTypeStr=dataTypeStr,
            hideRoot=hideRoot,
        )

    def _setupData_(self):
        self.clear()
        self.nodes = dict()
        self._visited_ = dict()
        print(f"{self.__class__.__name__}._setupData_: readOnly -> {self._readOnly_}")
        worker = WorkerThread(
            self,
            self.buildTree,
            self._private_data_,
            self.invisibleRootItem(),
            keyType=str,
            typeStr=self._dataTypeStr_,
            predicate=self.predicate,
            hideRoot=self.hideRoot,
            # readOnly=self._readOnly_,
        )
        worker.signals.signal_Finished.connect(self._slot_treeBuilt)
        worker.run()

    def setData(
        self,
        data,
        predicate=None,
        showPrivate: bool = False,
        root_title: str = "",
        dataTypeStr=None,
        hideRoot=False,
    ):
        r"""data should be a dictionary."""
        # print(f"{self.__class__.__name__}<{self.parent().windowTitle()}, {self.parent().parent().windowTitle()}> set data")
        self._visited_.clear()
        self.predicate = predicate
        self.showPrivate = showPrivate
        self.hideRoot = hideRoot

        # NOTE: 2025-06-28 13:55:20
        # self._private_data_ is used to build the tree model; it can be the
        # 'data' itself, OR a mapping representation of its members.
        # 'has_dynamic_private' is False in the former case, and True in the latter
        self._private_data_, self.has_dynamic_private = self._parse_data_(data)
        if self.has_dynamic_private and not self.showPrivate:
            self._private_data_ = dict(
                list(
                    filter(
                        lambda x: not x[0].startswith("_"), self._private_data_.items()
                    )
                )
            )

        self._data_ = data
        self._dataTypeStr_ = dataTypeStr

        if len(root_title.strip()) == 0:
            self.root_title = "/"
        else:
            self.root_title = root_title

        # NOTE: 2026-02-03 13:51:59
        # having decided to go with the WorkerThread option, I moved that code in
        # a separate method so that it can be called independently of self.setData()
        self._setupData_()

    def _parse_dataclass(self, data) -> tuple:
        datafields = dataclasses.fields(data)
        return dict(map(lambda x: (x.name, getattr(data, x.name)), datafields))

    def _parse_data_(self, data) -> tuple:
        r"""
        Returns a tuple (a, b), where:

        :a: dict; is the iterable container (a mapping or otherwise) upon which the
            tree model is built.
            'a' can be the data itself, or a mapping representation of its members
            (i.e. a dictionary) generated using datatypes.inspect_members(…). This
            is similar, but not identical, to accessing the __dict__ attribute
            of the data.

        :b: bool flag indicating whether 'a' is the data itself or a mapping
            representation of its attributes (for any non-iterable
            object/container)

            'b' is True when the data itself is a container suitable for
                representation in a tree model

        """
        mro = inspect.getmro(type(data))
        if (
            all(t not in self._supported_data_types_ for t in mro)
            and not inspect.isroutine(data)
            and not isinstance(data, (types.ModuleType, pkgutil.ModuleInfo))
            and data is not None
        ):
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

    def buildTree(
        self,
        data: object,
        parent: QtWidgets.QTreeWidgetItem,
        name: str = "",
        keyType: type = str,
        nameTip: str = "",
        typeStr: typing.Optional[str] = None,
        predicate: typing.Optional[typing.Any] = None,
        hideRoot: bool = False,
        # readOnly: bool = True,
        path: tuple = (),
    ):
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
        # NOTE: 2021-07-24 13:15:38
        # throughout this function 'node' is a QtWidgets.QTreeWidgetItem.
        #
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
        # column 0: type of the key (int or str) - except for the top child 
        # where key type is str
        # column 1: type of the data represented by the child
        node = QtWidgets.QTreeWidgetItem([name, "", ""])
        node.setData(1, QtCore.Qt.UserRole, type(data))
        node.setData(0, QtCore.Qt.UserRole, keyType)
        parent.addChild(node)

        # print(f"{self.__class__.__name__}.buildTree: predicate = {predicate}")

        # record the path to the node so it can be retrieved later
        # (this is used by the tree widget)

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
        (
            typeStr_,
            desc,
            children,
            widget,
            typeTip,
            showDescInParentNode,
            widgetColumn,
        ) = self.parse(data, path, predicate=predicate) # , readOnly=readOnly)
        # ### END   Timing measures for debugging

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

        # NOTE: caching code works but is buggy,
        # see BUG: 2025-05-27 17:32:09 FIXME/TODO
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
        # this seems like a good place to create/insert a delegate widget for 
        # data editing as appropriate
        # FIXME: this needs defining a model (currently this uses 
        # QAbstractItemModel)
        # TODO: the way to go seems to take out the parse() and buildTree() 
        # code and place it into a custom TreeModel (to be created); other code 
        # to move there:
        # memoize(), getWidgetSelection(), _parse_data_(), _parse_dataclass(), 
        # _makeTableWidget_() and maybe:
        # _slot_tableEditorWidgetSelectionChanged(), setSupportedDataTypes()
        #
        #

        if widget is not None:
            # NOTE: 2025-11-16 14:36:15
            # is a widget has been created by self.parse, use it as item widget
            # for the newly created subnode
            #
            # self.widgets.append(widget)

            # NOTE 2026-02-04 08:42:17
            # if parse(…) returns a widget for column 0, set this up as a
            #  SUBNODE that spans all three columns
            # else just set it up as widget to the CURRENT node, in the
            #  specified column
            if widgetColumn == 0:
                subnode = QtWidgets.QTreeWidgetItem(["", "", ""])
                node.addChild(subnode)
                # below, inherited from QTreeWidget;
                # the widget will go in column 0 of the child
                # Column 0 is really only for TableEditorWidget
                self.setItemWidget(subnode, 0, widget)
                modelndx = self.indexFromItem(subnode)
                parentndx = self.indexFromItem(node)
                self.setFirstColumnSpanned(modelndx.row(), parentndx, True)
                # if isinstance(widget, TableEditorWidget):
                #     widget.readOnly = self.readOnly
                # self.itemWidget(subnode, 0).setVisible(not readOnly)
            else:
                assert (
                    widgetColumn > 0 and widgetColumn <= 2
                ), f"Invalid widgetColumn specified ({widgetColumn}; should be 1 or 2)"

                self.setItemWidget(node, widgetColumn, widget)
                # self.itemWidget(node, widgetColumn).setVisible(not readOnly)

            # print(f"{self.__class__.__name__}.buildTree: path for widget: {path}")

        # NOTE: 2026-02-04 09:52:48
        # move here, and updated to store the tuple (node, widget); widget may be None
        # self.nodes is a dict
        # path is a tuple (as index branch path) - this is immutable, hence
        # hashable, hence usable as dict key
        #
        # TODO: 2026-02-05 12:02:11
        # shouldn't need another pointer to widget, here: widget can be accessed
        # via self.itemWidget(item:QTreeWidgetItem, column:int)
        self.nodes[path] = (node, widget)

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

                elif isinstance(
                    data,
                    (tuple, list, deque, typing.Sequence, dict,
                     types.MappingProxyType
                     ),
                ):
                    keyrepr = f"{key}"
                    # this here is crucial; I want type of key not type of what
                    # is mapped to it
                    keytip = f"index type: {type(key).__name__}"  

                else:
                    keyrepr = str(key)
                    keytip = f"object type: {type(key).__name__}"

                #              data        parent, name, nameTip,
                self.buildTree(
                    child_data,
                    node,
                    name=keyrepr,
                    keyType=keyType,
                    nameTip=keytip,
                    predicate=predicate,
                    # readOnly=readOnly,
                    path=path + (keyrepr,),
                )  # so hideRoot is always False?

    def parse(self, data: typing.Any, path: typing.Sequence, /,
              predicate: typing.Optional[types.FunctionType] = None, 
              typeStr: typing.Optional[str] = None,
              # readOnly: bool = True,
              ) -> tuple:
        r"""Figures out if data is to be represented as a (sub)tree or a widget.

        Returns:
        ========
        4-Tuple

        .. ::

            (typeStr: str, 
             desc: str, children: dict, 
             widget: QWidget, typeTip: str,
             showDescInParentNode: bool, 
             widgetColumn: int (0 or 2) 
            )


        • typeStr - a string representation of the data type

        • description  - a short string representation

        • a dict of sub-objects (children) to be parsed further

        • an optional widget to display/edit as sub-node (default is None)

        • typeTip — a string indicating the type of the key (for dict data) or

            of the index (for sequences, this is always an int, except for 

            namedtuples, where it can be a str)

        • showDescriptionInParentNode: bool

        • widgetColumn: index of column where the widget should go;

            can be only 0 or 2; when 0, the widget goes to a subnode; 
    
            when 2, the widget will go in the place of value/information 
            display, as a one-line editor

            therefore only a subset of widgets are allowed in the 3rd column
            (column 2)


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
        except Exception:
            HAVE_METAARRAY = None

        from core.datatypes import is_namedtuple, TypeEnum
        from systems.PrairieView import (
            PVObject,
            PVScan,
            PVSequence,
            PVFrame,
            PVSystemConfiguration,
            PVStateShard,
            PVStateValue,
            PVIndexedValue,
            PVSubIndexedValue,
            PVSubIndexedValueList,
            PVLinescanDefinition,
        )

        # print(f"{self.__class__.__name__}.parse(readOnly = {readOnly})")

        targetColumnForWidget = 0

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
        if not issubclass(
            type(data), NOTMEMOIZED + PODS
        ):  # or (isinstance(data, np.ndarray) and data.size<=1):
            # data_id = id(data)
            if id(data) in self._visited_:
                x = self._visited_.get(id(data), None)
                # print(x)
                if x is not None:
                    objtype = x[1]
                    path = "/".join(list(x[2]))
                    if len(path.strip()) == 0:
                        full_path = self.root_title
                    else:
                        if self.root_title == "/":
                            full_path = "/" + path
                        else:
                            full_path = "/".join([self.root_title, path])
                    desc = "<reference to %s at %s >" % (objtype.__name__, full_path)
                    return (
                        typeStr,
                        desc,
                        children,
                        widget,
                        typeTip,
                        showDescInParentNode,
                        targetColumnForWidget,
                    )
            else:
                self.memoize(data, path)

        if data is None:
            typeStr = "(None)"
            # return (
            #     typeStr,
            #     desc,
            #     children,
            #     widget,
            #     typeTip,
            #     showDescInParentNode,
            #     targetColumnForWidget,
            # )

        elif data is dataclasses.MISSING:
            desc = str(MISSING)
            # return (
            #     typeStr,
            #     desc,
            #     children,
            #     widget,
            #     typeTip,
            #     showDescInParentNode,
            #     targetColumnForWidget,
            # )

        elif type(data) is type(pd.NA):
            desc = str(pd.NA)
            # return (
            #     typeStr,
            #     desc,
            #     children,
            #     widget,
            #     typeTip,
            #     showDescInParentNode,
            #     targetColumnForWidget,
            # )

        # print(f"{self.__class__.__name__}.parse -> data_type: {data_type} ")
        try:
            if isinstance(data, type):
                desc = type(data).__name__
                if isinstance(data, enum.EnumType):
                    children = data.__members__

            if isinstance(data, pkgutil.ModuleInfo):
                desc = " ".join(
                    [
                        "Fields:",
                        "; ".join(
                            list(
                                map(
                                    lambda f: f" {f} = {getattr(data, f, None)}",
                                    data._fields,
                                )
                            )
                        ),
                    ]
                )

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
                    ndx = [
                        i[1]
                        for i in sorted(
                            (str(k[0]), k[1])
                            for k in zip(data.keys(), range(len(data)))
                        )
                    ]
                    items = [i for i in data.items()]
                    children = dict([items[k] for k in ndx])

                elif issubclass(type(data), (list, tuple, deque, set)):
                    # NOTE: 2025-05-21 16:17:37
                    # 'widget' is None, here — this will force the caller (i.e. buildTree)
                    # to descend into the children of the data and build up a subtree
                    desc = "length=%d" % len(data)
                    # NOTE: 2021-07-24 14:57:02
                    # accommodate namedtuple types
                    if is_namedtuple(data):
                        children = data._asdict()
                    else:
                        children = dict(enumerate(data))

            elif HAVE_METAARRAY and (
                hasattr(data, "implements") and data.implements("MetaArray")
            ):
                # NOTE: 2025-05-21 16:17:37
                # 'widget' is None, here
                children = dict(
                    [("data", data.view(np.ndarray)), ("meta", data.infoCopy())]
                )

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
                desc = " ".join(
                    [
                        lbl,
                        "with name (type):",
                        f"'{data.name}' ('{axisTypeStrings(data.type, single=True)[0]})'",
                    ]
                )
                if data.isChannels:
                    desc += f" and {len(data.channels)} channels"
                    children = dict(enumerate(data.channels))

            elif isinstance(data, ChannelCalibrationData):
                lbl = f"{data.__class__.__name__} object"
                desc = " ".join(
                    [
                        lbl,
                        "with name:",
                        f"'{data.name}'",
                        "index:",
                        f"{data.index}",
                        "acquisition index:",
                        f"{data.acquisition_index}",
                    ]
                )

            elif isinstance(data, PVObject):
                lbl = f"{data.__class__.__name__} object"
                if isinstance(data, PVScan):
                    desc = " ".join([lbl, f"{data.attributes}"])
                    # children = {"State": data.state, "Sequences":data.sequences)
                elif isinstance(data, PVSequence):
                    desc = " ".join(
                        [
                            lbl,
                            f"Type: {data.attributes['sequencetypename']} with {len(data.frames)} frames",
                        ]
                    )
                    # children = {"State": data.state, "Frames": data.frames}
                elif isinstance(data, PVFrame):
                    desc = " ".join([lbl, f"Channels: {data.channels}"])
                    # children = dict("State": data.state)
                elif isinstance(
                    data, (PVSystemConfiguration, PVIndexedValue, PVSubIndexedValue)
                ):
                    if (
                        hasattr(data, "description")
                        and isinstance(data.description, str)
                        and len(data.description.strip())
                    ):
                        desc = " ".join([lbl, data.description])
                # elif isinstance(data, PVLinescanDefinition):
                # desc = " ".join([lbl, data.description])

                children = data.as_dict()

            elif isinstance(data, pd.DataFrame):
                desc = "length=%d, columns=%d" % (len(data), len(data.columns))
                widget = self.delegate.createWidget(data, list(), False,self)
                widget.setMaximumHeight(self._widget_height_)
                targetColumnForWidget = 0

                # if readOnly:
                #     widget = self._makeTableWidget_(data)
                # else:
                #     widget = self.delegate.createWidget(data, list(), False, False, self)
                #     widget.setMaximumHeight(self._widget_height_)

            elif isinstance(data, pd.Series):
                desc = "length=%d, dtype=%s" % (len(data), data.dtype)
                widget = self.delegate.createWidget(data, list(), False, self)
                widget.setMaximumHeight(self._widget_height_)
                # if readOnly:
                #     widget = self._makeTableWidget_(data)
                # else:
                #     widget = self.delegate.createWidget(data, list(), False, self)
                #     widget.setMaximumHeight(self._widget_height_)
                targetColumnForWidget = 0

            elif isinstance(data, pd.Index):
                # NOTE: 2026-02-03 14:29:21
                # pd.Index should ALWAYS be read-only; however this branch is
                # executed for stand-alone OIOndex objects (i.e. NOT when part
                # of a DataFrame, when the widget is a TableEditorWidget which
                # NEVER changes the associated Index (be it row or column index)
                desc = "length=%d" % len(data)
                widget = self.delegate.createWidget(data, list(), False, self)
                widget.setMaximumHeight(self._widget_height_)
                # widget = self._makeTableWidget_(data)
                targetColumnForWidget = 0

            elif isinstance(data, Interval):
                desc = f"Interval '{data.name}' with {len(data)} subinterval(s)"
                children = {
                    "t0": data.t0,
                    "t1": data.t1,
                    "durations": data.durations,
                    "extent": data.extent,
                    "labels": data.labels,
                    "annotations": data.annotations,
                    "description": data.description,
                }

            elif isinstance(data, (neo.Epoch, DataZone)):
                desc = f"{type(data).__name__} '{data.name}' with {len(data)} subinterval(s)"
                children = {
                    "times": data.times,
                    "durations": data.durations,
                    "labels": data.labels,
                    "annotations": data.annotations,
                    "description": data.description,
                }

            elif isinstance(data, (neo.Event, DataMark, TriggerEvent)):
                desc = f"{type(data).__name__} '{data.name}' with {len(data)} mark(s)"
                children = {"times": data.times, "labels": data.labels}
                if isinstance(data, (DataMark, TriggerEvent)):
                    children.update({"type": data.type, "relative": data.relative})
                children.update(
                    {"annotations": data.annotations, "description": data.description}
                )

            elif isinstance(data, neo.core.dataobject.DataObject):
                desc = "shape=%s dtype=%s" % (data.shape, data.dtype)

                widget = self.delegate.createWidget(data, list(), False, self)
                widget.setMaximumHeight(self._widget_height_)
                targetColumnForWidget = 0

                # if self.readOnly:
                #     if data.size == 1:
                #         widget = QtWidgets.QLabel(str(data))
                #     else:
                #         widget = self._makeTableWidget_(data)
                #
                # else:
                #     widget = self.delegate.createWidget(data, list(), False, self)
                #     widget.setMaximumHeight(self._widget_height_)
                #     targetColumnForWidget = 0

            elif isinstance(data, pq.Quantity):
                # NOTE: 2026-02-03 14:27:22
                # these also include pq.UnitQuantity, so might install a QuantityChooserWidget
                if data.ndim == 0 or (data.ndim == 1 and data.size <= 1):
                    desc = f"{data}"
                else:
                    desc = "shape=%s dtype=%s" % (data.shape, data.dtype)

                column = 2 if (data.ndim == 0 or (data.ndim == 1 and data.size <= 1)) else 0
                widget = self.delegate.createWidget(data, list(), False, self)
                widget.setMaximumHeight(self._widget_height_)
                targetColumnForWidget = column

                # if readOnly:
                #     if data.ndim == 0 or (data.ndim == 1 and data.size <= 1):
                #         desc = f"{data}"
                #     else:
                #         desc = "shape=%s dtype=%s" % (data.shape, data.dtype)
                #         if data.ndim < 3 or not any(v > 1 for v in data.shape[2:]):
                #             widget = self._makeTableWidget_(data)
                #
                # else:
                #     column = 2 if (data.ndim == 0 or (data.ndim == 1 and data.size <= 1)) else 0
                #     widget = self.delegate.createWidget(data, list(), False, self)
                #     widget.setMaximumHeight(self._widget_height_)
                #     targetColumnForWidget = column

            elif isinstance(data, pq.dimensionality.Dimensionality):
                desc = f"{data}"

            elif isinstance(data, np.ndarray):
                if data.size == 1:
                    desc = f"{data}"
                else:
                    desc = "shape=%s dtype=%s" % (data.shape, data.dtype)

                column = 2 if (data.ndim == 0 or (data.ndim == 1 and data.size <= 1)) else 0
                widget = self.delegate.createWidget(data, list(), False, self)
                widget.setMaximumHeight(self._widget_height_)
                targetColumnForWidget = column
#
#                 if readOnly:
#                     if data.size == 1:
#                         desc = f"{data}"
#                     else:
#                         desc = "shape=%s dtype=%s" % (data.shape, data.dtype)
#                         if data.ndim < 3 or not any(v > 1 for v in data.shape[2:]):
#                             widget = self._makeTableWidget_(data)
#                 else:
#                     column = 2 if (data.ndim == 0 or (data.ndim == 1 and data.size <= 1)) else 0
#                     widget = self.delegate.createWidget(data, list(), False, self)
#                     widget.setMaximumHeight(self._widget_height_)
#                     targetColumnForWidget = column

            elif isinstance(data, (vigra.filters.Kernel1D, vigra.filters.Kernel2D)):
                widget = self.delegate.createWidget(data, list(), False, self)
                widget.setMaximumHeight(self._widget_height_)
                targetColumnForWidget = 0

                # if readOnly:
                #     widget = self._makeTableWidget_(data)
                # else:
                #     widget = self.delegate.createWidget(data, list(), False, self)
                #     widget.setMaximumHeight(self._widget_height_)
                #     targetColumnForWidget = 0

            elif isinstance(
                data,
                (
                    datetime.datetime,
                    datetime.date,
                    datetime.time,
                    datetime.timedelta,
                    datetime.timezone,
                ),
            ):
                # NOTE: 2026-02-03 14:22:50 TODO
                # read only for now; add QDateTimeEdit, QDateEdit and QTimeEdit to the delegate's createWidget
                # to enable changing these
                desc = f"{data}"

            elif isinstance(
                data, types.TracebackType
            ):  ## convert traceback to a list of strings
                # NOTE: 2026-02-03 14:23:50
                # ALWAYS READ-ONLY !!!
                frames = list(
                    map(str.strip, traceback.format_list(traceback.extract_tb(data)))
                )
                widget = QtWidgets.QPlainTextEdit(str("\n".join(frames)))
                widget.setMaximumHeight(200)
                widget.setReadOnly(True)
                targetColumnForWidget = 0

            elif isinstance(data, scipy.optimize.Bounds):
                children = {
                    "lb": data.lb,
                    "ub": data.ub,
                    "keep_feasible": data.keep_feasible,
                }

            elif isinstance(data, (str, bytes, bytearray)):
                if len(data) > 100:
                    _data = (
                        data[:97] if isinstance(data, str) else data.decode()[:97]
                    )
                    _data += "..."
                else:
                    desc = data if isinstance(data, str) else data.decode()

                if isinstance(data, (bytes, bytearray)):
                    # NOTE: 2026-02-03 14:24:47
                    # disable editing byte and bytearray types
                    # ALWAYS READ-ONLY
                    desc = f"{type(data)} with {len(data)} elements"
                    txt = data if isinstance(data, str) else data.decode()
                    widget = QtWidgets.QPlainTextEdit(txt)
                    widget.setMaximumHeight(self._widget_height_)
                    widget.setReadOnly(True)
                    targetColumnForWidget = 0
                else:
                    widget = self.delegate.createWidget(data, list(), False, self)
                    widget.setMaximumHeight(self._widget_height_)
                    targetColumnForWidget = 2

            elif isinstance(
                data,
                (
                    bool,
                    int,
                    float,
                    complex,
                    fractions.Fraction,
                    decimal.Decimal,
                    numbers.Number,
                ),
            ):
                desc = f"{data}"
                widget = self.delegate.createWidget(data, list(), False, self)
                targetColumnForWidget = 2

                # if readOnly:
                #     desc = f"{data}"
                # else:
                #     widget = self.delegate.createWidget(data, list(), False, self)
                #     targetColumnForWidget = 2

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
                    print(
                        f"{print_styled(f'for {type(data).__name__} data', color='red')}"
                    )

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
                    btns = self.findChildren(QtWidgets.QToolButton) + self.findChildren(
                        QtWidgets.QPushButton
                    )
                else:
                    btns = self.findChildren(
                        (QtWidgets.QToolButton, QtWidgets.QPushButton)
                    )

                for b in btns:
                    if b.iconSize() != self._scipyenWindow_.iconSize():
                        b.setIconSize(self._scipyenWindow_.iconSize())

            return (
                typeStr,
                desc,
                children,
                widget,
                typeTip,
                showDescInParentNode,
                targetColumnForWidget,
            )

        except:
            # print(f"{self.__class__.__name__}.parse data type : {type(data).__name__}, data: {data}")
            raise

    @property
    def delegate(self) -> QtWidgets.QStyledItemDelegate:
        r"""The instance of styled item delegate used.
        Read-only property

        """
        return self._delegate_

    @property
    def readOnly(self) -> bool:
        return self._readOnly_

    def _setWidgetsEditableState_(self):
        print(f"{self.__class__.__name__}._setWidgetsEditableState_: self._readOnly_ = {self._readOnly_}")
        for path, node_tuple in self.nodes.items():
            item = node_tuple[0]
            # first, check if there is an editor widget to column 2
            w = self.itemWidget(item, 2)
            if w:
                # hide one-liners in column 2 when read-only
                w.setVisible(not self._readOnly_)
            else:
                # set the editor in column 0 to read-only
                w = self.itemWidget(item,0)
                if isinstance(w, TableEditorWidget):
                    w.readOnly = self._readOnly
                elif isinstance(w, QtWidgets.QWidget):
                    w.setEnabled(not self._readOnly_)

    @readOnly.setter
    def readOnly(self, val: bool):
        self._readOnly_ = val == True
        self._setWidgetsEditableState_()

    def getObjectPathForItem(
        self, item: QtWidgets.QTreeWidgetItem, external: bool = False
    ) -> tuple:  # , as_expression:bool=True):
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
        from core.datatypes import is_namedtuple, TypeEnum, subarray_type_map
        from imaging.axiscalibration import (
            AxesCalibration,
            AxisCalibrationData,
            ChannelCalibrationData,
        )
        from imaging.axisutils import axisTypeStrings
        from systems.PrairieView import (
            PVObject,
            PVScan,
            PVSequence,
            PVFrame,
            PVSystemConfiguration,
            PVStateShard,
            PVStateValue,
            PVIndexedValue,
            PVSubIndexedValue,
            PVSubIndexedValueList,
            PVLinescanDefinition,
        )

        try:
            self._subselections_.clear()
            # print(f"\n{self.__class__.__name__}.getObjectPathForItem START")
            leafSubSelection = list()
            widget0 = self.itemWidget(item, 0)
            widget1 = self.itemWidget(item, 2)

            widget = None

            if widget0:
                widget = widget0

            elif widget1:
                widget = widget1

            # print(
            #     f"{self.__class__.__name__}.getObjectPathForItem: item = {item} -> widget = {widget} widget0 = {widget0}, widget1 = {widget1}"
            # )

            # TODO: 2025-05-26 20:53:08 FIXME
            # crunching through many model indexes is getting very slow, especially
            # for large tabular data
            # TODO: Consider using QItemSelection and QItemSelectionRange objects
            #
            if widget:
                # special case - this is a child item with a widget showing the
                # contents of the data represented by the parent item!
                # ∴ the item's parent is the actual data we're after !
                leafSubSelection = self.getWidgetSelection(widget)
                pItem = item.parent()
                # element = pItem.data(0, QtCore.Qt.DisplayRole)
                # elementDataType = pItem.data(0, QtCore.Qt.UserRole)
                item = pItem  # this is crucial

            element = item.data(0, QtCore.Qt.DisplayRole)
            parentIndexType = item.data(0, QtCore.Qt.UserRole)
            elementDataType = item.data(1, QtCore.Qt.UserRole)
            targetDataType = (
                dataclasses.MISSING
            )  # gets the data type resulting from the accessor

            # print(f"{self.__class__.__name__}.getObjectPathForItem: element = {element}, parentIndexType = {parentIndexType}, elementDataType = {elementDataType}")
            # if parentIndexType == pathlib.Path:
            #     element =
            path_parts = [element]  # the pathway from root to branch tip

            # elements of the expression used to access for the
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
            # expr = [f"{element}" if parentIndexType == str else element]
            expr = [element] if parentIndexType == str else [parentIndexType(element)]

            # print(f"{self.__class__.__name__}.getObjectPathForItem: first expr = {expr}")

            p = item.parent()
            k: int = 0
            while p is not None:
                pdatatype = p.data(1, QtCore.Qt.UserRole)
                pKeyType = p.data(0, QtCore.Qt.UserRole)
                element = p.data(0, QtCore.Qt.DisplayRole)
                # print(f"\t{self.__class__.__name__}.getObjectPathForItem: {k} pdatatype -> {pdatatype}, pKeyType -> {pKeyType}, element -> {element}")
                # path_parts.append(f"'{element}'" if pKeyType == str else element)
                path_parts.append(
                    f"'{element}'" if pKeyType == str else pKeyType(element)
                )
                # expr.append(f"'{element}'" if pKeyType == str else element)
                expr.append(element if pKeyType == str else pKeyType(element))
                # print(f"\t{self.__class__.__name__}.getObjectPathForItem: {k} expr -> {expr}")
                k += 1
                if pdatatype in self.iterableCollectionTypes or issubclass(
                    pdatatype, self.iterableCollectionTypes
                ):
                    # print(f"\t\t{self.__class__.__name__}.getObjectPathForItem: {k} parent is a iterableCollectionType")
                    if is_namedtuple(pdatatype):
                        expr[k - 1] = f".{expr[k-1]}"

                    elif pdatatype in self.mappingTypes or issubclass(
                        pdatatype, self.mappingTypes
                    ):
                        # print(f"\t\t{self.__class__.__name__}.getObjectPathForItem: {k} parent is a mapping")
                        expr[k - 1] = (
                            f"['{expr[k-1]}']"
                            if isinstance(expr[k - 1], str)
                            else f"[{pKeyType(expr[k-1])}]"
                        )

                    else:
                        expr[k - 1] = f"[{expr[k-1]}]"

                # elif issubclass(pdatatype, PVObject): # PrairieView objects
                elif pdatatype in (PVStateShard, PVStateValue):
                    expr[k - 1] = f"['{expr[k-1]}']"

                elif pdatatype == PVIndexedValue:
                    # expr[k-1] = f"['{expr[k-1]}'].value"
                    expr[k - 1] = ".value"

                elif pdatatype == PVSubIndexedValueList:
                    expr[k - 1] = f"[{expr[k-1]}].value"

                elif pdatatype == PVSubIndexedValue:
                    expr[k - 1] = ""

                else:
                    expr[k - 1] = f".{expr[k-1]}"

                p = p.parent()

            path_parts.reverse()
            expr.reverse()
            directAccess = True

            # print(f"{self.__class__.__name__}.getObjectPathForItem: expr -> {expr}")

            access = (
                (
                    "".join(expr)
                    if external
                    else "".join(expr[1:]) if len(expr) > 1 else ""
                ),
                "",
                elementDataType,
                targetDataType,
            )
            # print(f"{self.__class__.__name__}.getObjectPathForItem: access -> {access}")

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

                if isinstance(widget, (TableEditorWidget, SimpleTableWidget)) and (
                    isinstance(s, QtCore.QModelIndex) for s in leafSubSelection
                ):
                    rowsSet = list(set(map(lambda i: i.row(), leafSubSelection)))

                    cols_by_rows = dict(
                        (
                            r,
                            list(
                                map(
                                    lambda i: i.column(),
                                    filter(lambda i: i.row() == r, leafSubSelection),
                                )
                            ),
                        )
                        for r in rowsSet
                    )

                    continuousRows = np.all(np.diff(list(cols_by_rows.keys())) == 1)
                    allContinuousColsPerRow = all(
                        np.all(np.diff(cols) == 1) for cols in cols_by_rows.values()
                    )
                    minColsPerRow = list(map(lambda c: min(c), cols_by_rows.values()))
                    maxColsPerRow = list(map(lambda c: max(c), cols_by_rows.values()))
                    hasSameColumnRangeAcrossRows = (
                        allContinuousColsPerRow
                        and np.all(np.diff(minColsPerRow) == 0)
                        and np.all(np.diff(maxColsPerRow) == 0)
                    )
                    hasContinuousSelection = (
                        continuousRows and hasSameColumnRangeAcrossRows
                    )

                    if hasContinuousSelection:
                        firstRow = min(cols_by_rows.keys())
                        lastRow = max(cols_by_rows.keys())
                        # rowNdx = f"{slice(firstRow, lastRow+1)}"
                        rowNdx = slice(firstRow, lastRow + 1)
                        firstCol = min(minColsPerRow)
                        lastCol = max(maxColsPerRow)
                        targetDataType = elementDataType
                        if issubclass(
                            elementDataType, (pq.Quantity, pd.Series, pd.DataFrame)
                        ):
                            # just use the row indexing to get a signal slice of all channels
                            if firstCol == 0:
                                # CAUTION: first column (column 0) depicts the
                                # signal's domain or row index of the Series/DataFrame !
                                # all continuous selection, here, implies that we take all
                                # channels => will generate a new signal when eval'ed
                                # elementAccess.append(f"[{rowNdx},:]")
                                if issubclass(
                                    elementDataType, (pd.Series, pd.DataFrame)
                                ):
                                    elementAccess.append(
                                        (
                                            ".iloc",
                                            rowNdx,
                                            slice(firstCol, lastCol + 1),
                                            dataclasses.MISSING,
                                        )
                                    )
                                else:
                                    elementAccess.append(
                                        (
                                            "",
                                            rowNdx,
                                            slice(firstCol, lastCol + 1),
                                            dataclasses.MISSING,
                                        )
                                    )
                            else:
                                # filter out column 0 (for the signal's domain) and
                                # create colNdx to select channel data
                                # when eval'ed, will also generate a signal
                                channelCols = list(
                                    map(
                                        lambda cols: list(map(lambda c: c - 1, cols)),
                                        cols_by_rows.values(),
                                    )
                                )
                                # we know this is continuous and with same range across the rows
                                firstCol = min(
                                    list(map(lambda cols: min(cols), channelCols))
                                )
                                lastCol = max(
                                    list(map(lambda cols: max(cols), channelCols))
                                )
                                colNdx = f"{slice(firstCol, lastCol+1)}"
                                # elementAccess.append(f"[{rowNdx}, {colNdx}]")
                                if issubclass(
                                    elementDataType, (pd.Series, pd.DataFrame)
                                ):
                                    elementAccess.append(
                                        (".iloc", rowNdx, colNdx, dataclasses.MISSING)
                                    )
                                else:
                                    elementAccess.append(
                                        ("", rowNdx, colNdx, dataclasses.MISSING)
                                    )
                        else:  # generic ndarray or pd.Index
                            # colNdx = f"{slice(firstCol, lastCol+1)}"
                            colNdx = slice(firstCol, lastCol + 1)
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
                            if issubclass(
                                elementDataType, neo.core.dataobject.DataObject
                            ):
                                channelCols = list(
                                    map(
                                        lambda cols: list(
                                            map(
                                                lambda c: c - 1,
                                                filter(lambda x: x > 0, cols),
                                            )
                                        ),
                                        cols_by_rows.values(),
                                    )
                                )
                                colNdx = np.array(channelCols).flatten()
                                hasDomainSelection = any(
                                    any(c == 0 for c in cols)
                                    for cols in cols_by_rows.values()
                                )
                                if hasDomainSelection:
                                    # elementAccess.append(f".as_array()[{rowNdx}, {colNdx}]") # include domain
                                    elementAccess.append(
                                        (
                                            ".as_array()",
                                            rowNdx,
                                            colNdx,
                                            dataclasses.MISSING,
                                        )
                                    )  # include domain
                                    if elementDataType in subarray_type_map:
                                        targetDataType = subarray_type_map[
                                            elementDataType
                                        ]
                                    else:
                                        targetDataType = pq.Quantity
                                else:
                                    elementAccess.append(
                                        (
                                            ".as_array()",
                                            rowNdx,
                                            colNdx,
                                            dataclasses.MISSING,
                                        )
                                    )
                                    # elementAccess.append(f".as_array()[{rowNdx}, {colNdx}]")
                                    targetDataType = pq.Quantity
                            else:
                                elementAccess.append(
                                    (".as_array()", rowNdx, colNdx, dataclasses.MISSING)
                                )
                                targetDataType = pq.Quantity

                        elif issubclass(elementDataType, (pd.Series, pd.DataFrame)):
                            channelCols = list(
                                map(
                                    lambda cols: list(
                                        map(
                                            lambda c: c - 1,
                                            filter(lambda x: x > 0, cols),
                                        )
                                    ),
                                    cols_by_rows.values(),
                                )
                            )
                            colNdx = np.array(channelCols).flatten()
                            # indexing is selected automatically, by rowNdx
                            elementAccess.append(
                                (".iloc", rowNdx, colNdx, dataclasses.MISSING)
                            )
                            # iloc syntax generates the return type dynamicslly (either DataFrame or Series)
                            targetDataType = dataclasses.MISSING
                            # hasDomainSelection = any(any(c==0 for c in cols) for cols in cols_by_rows.values())

                        else:  # generic ndarray and pd.Index
                            channelCols = list(cols_by_rows.values())
                            colNdx = np.array(channelCols).flatten()
                            # colNdx = f"np.array({channelCols})"
                            elementAccess.append(("", rowNdx, colNdx, Ellipsis))
                            # elementAccess.append(f"[{rowNdx}, {colNdx}, ...]")
                            targetDataType = elementDataType

                    for eAccess in elementAccess:
                        accessList.append(
                            (access[0], eAccess, elementDataType, targetDataType)
                        )
                    directAccess = True

                elif isinstance(
                    widget, (QtWidgets.QPlainTextEdit, QtWidgets.QTextEdit)
                ) and all(isinstance(v, str) for v in leafSubSelection):
                    self._subselections_.append("".join(leafSubSelection))
                    accessList = [access]
                    directAccess = False

            else:
                accessList = [access]
            # print(f"{self.__class__.__name__}.getObjectPathForItem: path_parts = {path_parts}, expr = {expr}, access = {access}")
            return path_parts, accessList, directAccess, True
        except:
            # exc = sys.exception()
            # msg = "".join(traceback.format_exception_only(exc))
            # self.errorMessage(type(exc).__name__, msg)
            raise

    # TODO: 2026-02-04 16:47:14
    # move this to InteractiveTreeWidget
    # requires moving self._subselections_ to InteractiveTreeWidget as well
    @safewrapper
    def exportDataForItems(
        self,
        items: list[QtWidgets.QTreeWidgetItem],
        fullPathAsName: bool = False,
        path_only: bool = False,
    ) -> tuple[list]:
        r"""Export data displayed by their corresponding items, to workspace.

        Parameters:
        ----------

        items: sequence of QTreeWidgetItem objects - typicaly, the selected
            non-hidden QTreeWidgetItem items in self.

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
                path, accessList, direct, success = self.getObjectPathForItem(
                    item, path_only
                )
            except:
                exc = sys.exception()
                msg = "".join(traceback.format_exception_only(exc))
                GuiMessages.errorMessage_static(self, type(exc).__name__, msg)
                raise

            # print(f"\n{self.__class__.__name__}_export_data_items_ path = {path}, access -> {accessList}")

            if len(path) == 0:
                continue

            if fullPathAsName:
                # print(f"{self.__class__.__name__}_export_data_items_ full_path = {path}")
                name = strutils.str2symbol("_".join(path))

            else:
                name = strutils.str2symbol(path[-1])

            if self.has_dynamic_private:
                src = self._private_data_
            else:
                src = self._data_
                # src = self._obj_cache_[self._cache_index_][0] # ATTENTION: list of tuple(obj:typing.Any, name:str)

            try:
                if direct:
                    if len(accessList) > 1:
                        for k, statement, eAccess, oType, tType in enumerate(
                            accessList
                        ):
                            print(
                                f"statement: {statement}, eAccess: {eAccess}, oType: {oType}, tType: {tType}"
                            )
                            if len(eAccess):
                                call, rowNdx, colNdx, hiNdx = eAccess
                                rNdx = (
                                    f"np.array({list(rowNdx)})"
                                    if isinstance(rowNdx, np.ndarray)
                                    else f"{rowNdx}"
                                )
                                cNdx = (
                                    f"np.array({list(colNdx)})"
                                    if isinstance(colNdx, np.ndarray)
                                    else f"{colNdx}"
                                )
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
                                            if (
                                                tType is pq.Quantity
                                                and oType is pq.Quantity
                                            ):
                                                obj = obj * srcObj.units
                                            elif tType in (
                                                IrregularlySampledDataSignal,
                                                neo.IrregularlySampledSignal,
                                            ):
                                                domain = srcObj.times[rowNdx]
                                                obj = tType(
                                                    times=domain,
                                                    signal=obj,
                                                    units=srcObj.units,
                                                    time_units=srcObj.times.units,
                                                )
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
                        # print(f"{self.__class__.__name__}._export_data_items_: statement: {statement}, eAccess: {eAccess}, oType: {oType}, tType: {tType}")
                        if len(eAccess):
                            # unpack accessor elements
                            call, rowNdx, colNdx, hiNdx = eAccess
                            rNdx = (
                                f"np.array({list(rowNdx)})"
                                if isinstance(rowNdx, np.ndarray)
                                else f"{rowNdx}"
                            )
                            cNdx = (
                                f"np.array({list(colNdx)})"
                                if isinstance(colNdx, np.ndarray)
                                else f"{colNdx}"
                            )
                            accstmt = f"{call}[{rNdx}, {cNdx}]"
                            if hiNdx is not dataclasses.MISSING:
                                if hiNdx == Ellipsis:
                                    hNdx = ", ..."
                                elif isinstance(hiNdx, np.ndarray):
                                    hNdx = f"np.array({list(hiNdx)})"
                                elif isinstance(hiNdx, slice):
                                    hNdx = f"{hiNdx}"
                                accstmt = accstmt + f"{hNdx}"

                            # print(f"{self.__class__.__name__}._export_data_items_: accstmt: {accstmt}")
                            if path_only:
                                obj = f"{statement}{accstmt}"
                            else:
                                obj = eval(f"src{statement}{accstmt}")

                                if not isinstance(obj, oType):
                                    if tType is not dataclasses.MISSING:
                                        srcObj = eval(f"src{statement}")
                                        if (
                                            tType is pq.Quantity
                                            and oType is pq.Quantity
                                        ):
                                            obj = obj * srcObj.units
                                        elif tType in (
                                            IrregularlySampledDataSignal,
                                            neo.IrregularlySampledSignal,
                                        ):
                                            domain = srcObj.times[rowNdx]
                                            obj = tType(
                                                times=domain,
                                                signal=obj,
                                                units=srcObj.units,
                                                time_units=srcObj.times.units,
                                            )
                        else:
                            # print(f"{self.__class__.__name__}._export_data_items_: statement = {statement}")
                            if path_only:
                                obj = f"{statement}"
                            else:
                                obj = eval(f"src{statement}")
                        objects.append(obj)
                        names.append(name)
                else:
                    if path_only:
                        if len(accessList) > 1:
                            for k, statement, eAccess, oType, tType in enumerate(
                                accessList
                            ):
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
                                objects.append(self._subselections_[0])
                                names.append(name)
            except Exception:
                exc = sys.exception()
                # traceback.print_exc()
                msg = "".join(traceback.format_exception_only(exc))
                GuiMessages.errorMessage_static(self, type(exc).__name__, msg)
                raise

        if len(objects) == 0:
            return

        if path_only:
            return objects

        return objects, names

    @safewrapper
    def getSelectedPaths(self):
        items = self.selectedItems()
        if len(items) == 0:
            return
        return self.exportDataForItems(items, path_only=True)
        # return self._export_data_items_(items, path_only=True)

    def collapseExpandRecursive(self, item, expand=False, current=True):
        if expand:
            fn = self.expandItem
        else:
            fn = self.collapseItem

        for k in range(item.childCount()):
            self.collapseExpandRecursive(item.child(k), expand=expand)

        if current:
            fn(item)

    @Slot()
    def collapseTree(self):
        for k in range(self.topLevelItemCount()):
            self.collapseExpandRecursive(self.topLevelItem(k), current=False)

    @Slot()
    def expandTree(self):
        for k in range(self.topLevelItemCount()):
            self.collapseExpandRecursive(
                self.topLevelItem(k), expand=True, current=False
            )
