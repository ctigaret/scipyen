# -*- coding: utf-8 -*-
# $Id: tableeditorwidget.py $
# SPDX-FileCopyrightText: 2023 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""Table Editor widget and custom table model, for tabular-like data
"""


#### BEGIN core python modules
from __future__ import print_function

import os, inspect, warnings, traceback, datetime, typing
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
    

import pandas as pd
import quantities as pq
#import xarray as xa
import numpy as np
import neo
from core.vigra_patches import vigra

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.pylab as plb
import matplotlib.mlab as mlb
#### END 3rd party modules

#### BEGIN pict.core modules
#from core.patchneo import *
import core.datatypes  

import core.utilities as utilities
import core.strutils as strutils
from core.strutils import str2float

from core.prog import (safewrapper, scipywarn)

from core.triggerevent import (DataMark, MarkType, TriggerEvent, TriggerEventType)
from core.triggerprotocols import TriggerProtocol
from core.datazone import DataZone

import core.datasignal
from core.datasignal import (DataSignal, IrregularlySampledDataSignal,)
from core.datatypes import array_slice
from core.sysutils import adapt_ui_path
from core import scipyen_quantities as scq

#### END pict.core modules

#### BEGIN pict.gui modules
from gui.scipyenviewer import ScipyenViewer #, ScipyenFrameViewer
from gui import quickdialog
from gui.delegates import PythonItemDelegate
from gui.widgets.tabledataview import TableDataView
# from gui import resources_rc
# from gui import icons_rc
#### END pict.gui modules

#### BEGIN pict.iolib modules
import iolib.pictio as pio
#### END pict.iolib modules

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__ui_path__ = adapt_ui_path(__module_path__, "tableeditorwidget.ui")

__module_name__ = os.path.splitext(os.path.basename(__file__))[0]

Ui_TableEditorWidget, QWidget = loadUiType(__ui_path__)

class TableEditorWidget(QWidget, Ui_TableEditorWidget):
    # TODO 2019-11-01 22:57:01
    # finish implementing all these
    viewer_for_types = (pd.DataFrame, pd.Series, neo.core.baseneo.BaseNeo,
                       neo.AnalogSignal, neo.IrregularlySampledSignal,
                       neo.Epoch, neo.Event, neo.SpikeTrain,
                       DataSignal, IrregularlySampledDataSignal,
                       TriggerEvent, TriggerProtocol,
                       np.ndarray, vigra.VigraArray, vigra.filters.Kernel1D, vigra.filters.Kernel2D)
    
    view_action_name = "Table"
    
    sig_selectionChanged = Signal(name="sig_selectionChanged")
    sig_dataChanged = Signal(name="sig_dataChanged")
    
    def __init__(self, parent:typing.Optional[QtWidgets.QMainWindow]=None,
                 readOnly:bool=True) -> None:
        super().__init__(parent=parent)
        # FIXME: 2025-11-23 09:58:38 next line is DEPRECATED
        self._is_vigra_filter_kernel_:bool = False # needed in future implementations of editing functionality
        self._dataModel_ = TabularDataModel(parent=self)
        # self._dataModel_.sig_rowsPopulated.connect(self._slot_rowsPopulated)
        # self._dataModel_.sig_columnsPopulated.connect(self._slot_columnsPopulated)
        self._selectedIndexes_ = list()
        self._readOnly_:bool = readOnly == True
        
        # NOTE: 2021-10-18 09:32:45
        # ### BEGIN keep this  - you may re-enable the possibility to use other custom tabular
        # data models
        
        #if model is None:
            #self._dataModel_ = TabularDataModel(parent=self)
            
        #else:
            #self._dataModel_ = model
        # ### END keep this ...
        
        self._configureUI_()
        
        self._defaultItemDelegate_ = self.tableView.itemDelegate()
        self._editItemDelegate_ = PythonItemDelegate(parent=self)
        
        # NOTE: 2021-08-16 17:22:20
        # By default, this is defined in the .ui file as:
        # QtWidgets.QAbstractItemView.DoubleClicked |
        # QtWidgets.QAbstractItemView.EditKeyPressed |
        # QtWidgets.QAbstractItemView.AnyKeyPressed
        self._defaultEditTriggers_ = self.tableView.editTriggers()
        if self._readOnly_:
            self.tableView.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        else:
            # FIXME: 2025-11-23 10:23:31 is this too time-consuming?
            self.tableView.setItemDelegate(self._editItemDelegate_)
        
        self._data_ = None
        
        self._slicingAxis_ = None
        
        self._currentSlice_ = 0
        
        self._selectedRowIndex_ = None
        self._selectedColumnIndex_ = None
        
        if hasattr(self._dataModel_, "sig_modelDataChanged") and isinstance(type(self._dataModel_).sig_modelDataChanged, Signal):
            self._dataModel_.sig_modelDataChanged.connect(self.sig_dataChanged) # connect signal to signal directly
            
        # self.setData(None)
        
    def setData(self, data:(pd.DataFrame, pd.Series, neo.core.baseneo.BaseNeo,
                       neo.AnalogSignal, neo.IrregularlySampledSignal,
                       neo.Epoch, neo.Event, neo.SpikeTrain,
                       DataSignal, IrregularlySampledDataSignal,
                       TriggerEvent, TriggerProtocol,
                       np.ndarray, vigra.VigraArray, vigra.filters.Kernel1D, vigra.filters.Kernel2D), *args, **kwargs):
        r"""Called when this widget is part of TableEditor
    """
        from imaging import vigrautils
        # timer = QtCore.QElapsedTimer()
        # timer.start()
        if isinstance(data, (vigra.filters.Kernel1D, vigra.filters.Kernel2D)):
            data = vigrautils.kernel2array(data)
            self._is_vigra_filter_kernel_ = True
        else:
            self._is_vigra_filter_kernel_ = False
        
        self._data_ = data
        
        if getattr(data, "shape", (0,0))[0] > 10:
            # avoid auto-resizing rows for data with more than 10 rows — it is
            # resource consuming
            self.resizeRowsToolButton.setEnabled(False)
        
        if isinstance(data, np.ndarray) and data.ndim > 2:
            self._slicingAxis_ = kwargs.get("sliceaxis", None)
            if not isinstance(self._slicingAxis_, int) or self._slicingAxis_ < 0 or self._slicingAxis_ >= data.ndim:
                self._slicingAxis_ = 2
                
            if data.ndim > 3:
                new_shape = list(data.shape[0:self._slicingAxis_]) + [np.prod(data.shape[self._slicingAxis_:])]
                self._data_ = np.squeeze(data).reshape(tuple(new_shape))
                
            self._currentSlice_ = 0
            self._dataModel_.setModelData(self._data_[array_slice(self._data_, {self._slicingAxis_:self._currentSlice_})])
            
            self.prevSliceToolbutton.setEnabled(True)
            self.nextSliceToolButton.setEnabled(True)
        
        else:
            self.prevSliceToolbutton.setEnabled(False)
            self.nextSliceToolButton.setEnabled(False)
            self._dataModel_.setModelData(self._data_)
        
        # NOTE: 2025-11-23 19:53:14
        # to show bool cell data as checkboxes
        for row in range(self._dataModel_.rowCount()):
            for col in range(self._dataModel_.columnCount()):
                index = self._dataModel_.index(row, col)
                if isinstance(indexdata, bool):
                    self.tableView.openPersistentEditor(index)
#                 if self._immutability_["joint"]:
#                     immutable = col in self._immutability_["columns"] and row in self._immutability_["rows"]
#                 else:
#                     immutable = col in self._immutability_["columns"] or row in self._immutability_["rows"]
#                     
#                 if immutable:
#                     continue
#                 
#                 index = self._dataModel_.index(row, col)
#                 indexdata = self._dataModel_.data(index).value()
#                 if isinstance(indexdata, bool):
#                     self.tableView.openPersistentEditor(index)
                
    @Slot()
    def _slot_prevSlice(self):
        if isinstance(self._data_, np.ndarray) and self._data_.ndim > 2:
            if self.currentSlice > 0:
                self.currentSlice = self.currentSlice - 1
        
    @Slot()
    def _slot_nextSlice(self):
        if isinstance(self._data_, np.ndarray) and self._data_.ndim > 2:
            if self.currentSlice <= self._data_.shape[self._slicingAxis_] -1 :
                self.currentSlice = self.currentSlice + 1
        
    @property
    def selectedColumnIndex(self) -> typing.Optional[int]:
        r"""DEPRECATED"""
        # warnings.warn("This property is deprecated; please use self.selectedColumnIndexes")
        return self._selectedColumnIndex_
    
    @selectedColumnIndex.setter
    def selectedColumnIndex(self, val:int):
        self._selectedColumnIndex_ = val
        
    @property
    def selectedColumnIndexes(self) -> list:
        return utilities.unique([ndx.column() for ndx in self.tableView.selectedIndexes()])
    
    @property
    def selectedRowIndexes(self) -> list:
        return utilities.unique([ndx.row() for ndx in self.tableView.selectedIndexes()])
    
    @property
    def selectedRowIndex(self) -> typing.Optional[int]:
        r"""DEPRECATED"""
        return self._selectedRowIndex_
    
    @selectedRowIndex.setter
    def selectedRowIndex(self, val:int):
        self._selectedRowIndex_ = val
        
    @property
    def selectedIndexes(self):
        return self.tableView.selectedIndexes()
    
    @property
    def currentSlice(self):
        return self._currentSlice_
    
    @currentSlice.setter
    def currentSlice(self, val):
        if isinstance(self._data_, np.ndarray) and self._data_.ndim > 2:
            if isinstance(val, int):
                if val >=0 and val < self._data_.ndim:
                    self._currentSlice_ = val
                    if self._currentSlice_ == 0:
                        self.prevSliceToolbutton.setEnabled(False)
                        self.nextSliceToolButton.setEnabled(True)
                        
                    elif self._currentSlice_ >= self._data_.shape[self._slicingAxis_] - 1:
                        self.prevSliceToolbutton.setEnabled(True)
                        self.nextSliceToolButton.setEnabled(False)
                        
                    else:
                        self.prevSliceToolbutton.setEnabled(True)
                        self.nextSliceToolButton.setEnabled(True)
                        
                    self._dataModel_.setModelData(self._data_[array_slice(self._data_, {self._slicingAxis_:self._currentSlice_})])
                        
                        
    @property
    def model(self):
        return self.tableView.model()
    
    @model.setter
    def model(self, md):
        self._dataModel_ = md
        self.tableView.setModel(self._dataModel_)
        if hasattr(self._dataModel_, "sig_modelDataChanged") and isinstance(type(self._dataModel_).sig_modelDataChanged, Signal):
            self._dataModel_.sig_modelDataChanged.connect(self.sig_dataChanged) # connect signal to signal directly
        
    @property
    def readOnly(self):
        return self._readOnly_
        # return self.tableView.editTriggers() == QtWidgets.QAbstractItemView.NoEditTriggers
    
    @readOnly.setter
    def readOnly(self, val:bool):
        self._readOnly_ = val == True
        if self._readOnly_:
            self.tableView.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self.tableView.setItemDelegate(self._editItemDelegate_)
        else:
            self.tableView.setEditTriggers(self._defaultEditTriggers_)
            self.tableView.setItemDelegate(self._defaultItemDelegate_)
            
    def setEditTriggers(self, val):
        r"""See documentation for QtWidgets.QAbstractItemView.setEditTriggers()
        """
        self.tableView.setEditTriggers(val)
            
    def _configureUI_(self):
        self.setupUi(self)
        self.tableView.setSortingEnabled(False)
        self.tableView.setModel(self._dataModel_)
        
        self.tableView.horizontalHeader().setSectionsMovable(False)
        # NOTE: 2018-11-28 21:46:18
        # WARNING HUGE speed penalty when using ResizeToContents policy, for large
        # data sets (~1k rows and tens of columns)
        #self.tableView.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        #self.tableView.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        # NOTE: 2018-11-29 23:15:13
        # you may play with this by also setting the precision to be based only
        # on what is actually visible:
        self.tableView.horizontalHeader().setResizeContentsPrecision(0) 
        
        self.tableView.horizontalHeader().setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tableView.horizontalHeader().customContextMenuRequested[QtCore.QPoint].connect(self.slot_horizontal_header_context_menu_request)
        
        self.tableView.verticalHeader().setSectionsMovable(False)
        
        # see NOTE: 2018-11-28 21:46:18 and NOTE: 2018-11-29 23:15:13
        self.tableView.verticalHeader().setResizeContentsPrecision(0) 
        
        self.tableView.verticalHeader().setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tableView.verticalHeader().customContextMenuRequested[QtCore.QPoint].connect(self.slot_vertical_header_context_menu_request)
        
        
        self.tableView.setAlternatingRowColors(True)
        self.tableView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tableView.customContextMenuRequested[QtCore.QPoint].connect(self.slot_table_context_menu_requested)
        self.tableView.clicked[QtCore.QModelIndex].connect(self.slot_tableItemClicked)


        self.resizeColumnsToolButton.clicked.connect(self.slot_resizeAllColumnsToContents)
        self.resizeRowsToolButton.clicked.connect(self.slot_resizeAllRowsToContents)
        
        self.prevSliceToolbutton.setEnabled(False)
        self.prevSliceToolbutton.clicked.connect(self._slot_prevSlice)
        self.nextSliceToolButton.setEnabled(False)
        self.nextSliceToolButton.clicked.connect(self._slot_nextSlice)
        
    @Slot(QtCore.QModelIndex)
    def slot_tableItemClicked(self, index:QtCore.QModelIndex):
        self.sig_selectionChanged.emit()
        
    @Slot()
    def slot_resizeAllColumnsToContents(self):
        #print("TableEditorWidget slot_resizeAllColumnsToContents")
        signalBlockers = [QtCore.QSignalBlocker(v) for v in (self.tableView.horizontalHeader(), self.tableView.verticalHeader())]
        self.tableView.horizontalHeader().resizeSections(QtWidgets.QHeaderView.ResizeToContents)
        
    @Slot()
    def slot_resizeAllRowsToContents(self):
        signalBlockers = [QtCore.QSignalBlocker(v) for v in (self.tableView.horizontalHeader(), self.tableView.verticalHeader())]
        self.tableView.verticalHeader().resizeSections(QtWidgets.QHeaderView.ResizeToContents)
        
    @Slot(QtCore.QPoint)
    @safewrapper
    def slot_horizontal_header_context_menu_request(self, pos):
        #print("horizontal header context menu at pos %s" % pos)
        #print("clicked column %s" % self.tableView.columnAt(pos.x()))
        
        if len(self.selectedColumnIndexes) == 0:
            self.selectedColumnIndex = self.tableView.columnAt(pos.x())
        else:
            self.selectedColumnIndex = None
        
        cm = QtWidgets.QMenu("Column Menu", self.tableView)
        copyColumnTitleAction = cm.addAction("Copy column name")
        copyColumnTitleAction.triggered.connect(self.slot_copyColumnName)
        
        resizeColumnToContentsAction = cm.addAction("Resize to contents")
        resizeColumnToContentsAction.triggered.connect(self.slot_resizeSelectedColumnsToContents)
        
        resizeAllColumsToContextAction = cm.addAction("Resize All Columns To Contents")
        
        resizeAllColumsToContextAction.triggered.connect(self.slot_resizeAllColumnsToContents)
        
        cm.exec(self.tableView.mapToGlobal(pos))
        
    @Slot(QtCore.QPoint)
    @safewrapper
    def slot_vertical_header_context_menu_request(self, pos):
        if len(self.selectedRowIndexes) == 0:
            self.selectedRowIndex = self.tableView.rowAt(pos.x())
        else:
            self.selectedRowIndex = None
        
        cm = QtWidgets.QMenu("Row Menu", self.tableView)
        copyColumnTitleAction = cm.addAction("Copy row name")
        copyColumnTitleAction.triggered.connect(self.slot_copyRowName)
        
        resizeRowToContentsAction = cm.addAction("Resize to contents")
        resizeRowToContentsAction.triggered.connect(self.slot_resizeSelectedRowsToContents)
        
        resizeAllRowsToContextAction = cm.addAction("Resize All Rows To Contents")
        
        resizeAllRowsToContextAction.triggered.connect(self.slot_resizeAllRowsToContents)
        
        cm.exec(self.tableView.mapToGlobal(pos))
        
    @Slot()
    @safewrapper
    def slot_copyColumnName(self):
        quote = bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier)
        ret = ""
        if len(self.selectedColumnIndexes):
            ret = self.getColumnNames(self.selectedColumnIndexes, quoted=quote)
            # values = [self.tableView.model().headerData(ndx, QtCore.Qt.Horizontal).value() for ndx in self.selectedColumnIndexes]
            # link = ", "
            # colNames = link.join([f"'{v}'" for v in values]) if quote else link.join(values)
            # QtWidgets.QApplication.instance().clipboard().setText(colNames)
            
        elif isinstance(self.selectedColumnIndex, int):
            ret = self.getColumnNames(self.selectedColumnIndex, quoted=quote)
            # colName = self.tableView.model().headerData(self.selectedColumnIndex, QtCore.Qt.Horizontal).value()
            # if quote:
            #     colName = f"'{colName}'"
            # QtWidgets.QApplication.instance().clipboard().setText(colName)
        else:
            return 
        QtWidgets.QApplication.instance().clipboard().setText(ret)
        
    @Slot()
    @safewrapper
    def slot_copyRowName(self):
        quote = bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier)
        ret = ""
        if len(self.selectedRowIndexes):
            ret = self.getRowNames(self.selectedRowIndexes, quoted = quote)
            # values = [self.tableView.model().headerData(ndx, QtCore.Qt.Vertical).value() for ndx in self.selectedRowIndexes]
            # link = ", "
            # rowNames = link.join([f"'{v}'" for v in values]) if quote else link.join(values)
            # QtWidgets.QApplication.instance().clipboard().setText(rowNames)
            
        elif isinstance(self.selectedRowIndex, int):
            ret = self.getRowNames(self.selectedRowIndex, quoted = quote)
            # rowName = self.tableView.model().headerData(self.selectedRowIndex, QtCore.Qt.Vertical).value()
            # if quote:
            #     rowName = f"'{rowName}'"
        else:
            return 
            # QtWidgets.QApplication.instance().clipboard().setText(rowName)
        QtWidgets.QApplication.instance().clipboard().setText(ret)
            
    def getRowNames(self, ndx:typing.Optional[typing.Union[int, typing.Sequence[int]]] = None,
                    quoted:bool=False, sep:str = "\t", asList:bool=False):
        if ndx is None:
            ndx = range(self.tableView.model().rowCount())
        
        elif isinstance(ndx, int):
            ndx = [ndx]
        
        elif isinstance(ndx, (list, tuple)):
            if len(ndx) == 0:
                ndx = range(self.tableView.model().rowCount())
            elif not all(isinstance(v, int) for v in ndx):
                raise TypeError(f"Invalid row indices specified. Expecting int, sequence of int or None; instead, got {ndx}")
        else:
            raise TypeError(f"Invalid row indices specified. Expecting int, sequence of int or None; instead, got {ndx}")
        
        values = [self.tableView.model().headerData(k, QtCore.Qt.Vertical).value() for k in ndx]
        # link = ", "
        if len(values) == 1:
            ret = f"'{values[0]}'" if quoted else values[0]
            
            if asList:
                ret = [ret]
            
        else:
            ret = [f"'{v}'" for v in values] if quoted else values
            if not asList:
                ret = sep.join(ret)
                
        return ret
        
    def getColumnNames(self, ndx:typing.Optional[typing.Union[int, typing.Sequence[int]]] = None,
                    quoted:bool=False, sep:str = ", ", asList:bool=False):
        if ndx is None:
            ndx = range(self.tableView.model().columnCount())
        
        elif isinstance(ndx, int):
            ndx = [ndx]
        
        elif isinstance(ndx, (list, tuple)):
            if len(ndx) == 0:
                ndx = range(self.tableView.model().columnCount())
                
            elif not all(isinstance(v, int) for v in ndx):
                raise TypeError(f"Invalid row indices specified. Expecting int, sequence of int or None; instead, got {ndx}")
        else:
            raise TypeError(f"Invalid row indices specified. Expecting int, sequence of int or None; instead, got {ndx}")
        
        values = [self.tableView.model().headerData(k, QtCore.Qt.Horizontal).value() for k in ndx]
        # link = ", "
        if len(values) == 1:
            ret = f"'{values[0]}'" if quoted else values[0]
            if asList:
                ret = [ret]
        else:
            ret = [f"'{v}'" for v in values] if quoted else values
            if not asList:
                ret = sep.join(ret)
                
        return ret
        
    @Slot(int,int,int)
    def _slot_rowsPopulated(self, start:int, fetched:int, total:int):
        print(f"{self.__class__.__name__} fetched rows: {start}...{fetched}/{total}")
            
    @Slot(int,int,int)
    def _slot_columnsPopulated(self, start:int, fetched:int, total:int):
        print(f"{self.__class__.__name__} fetched columns: {start}...{fetched}/{total}")
            
    @Slot()
    @safewrapper
    def slot_resizeSelectedRowsToContents(self):
        if not isinstance(self.selectedRowIndex, int):
            return
        
        signalBlocker = QtCore.QSignalBlocker(self.tableView.verticalHeader())
        
        if len(self.tableView.selectionModel().selectedRows()) > 1:
            row_indices = [ndx.row() for ndx in self.tableView.selectionModel().selectedColumns()]
            
            for ndx in row_indices:
                sizeHint = max([self.tableView.sizeHintForRow(ndx), self.tableView.verticalHeader().sectionSizeHint(ndx)])
                #sizeHint = self.tableView.horizontalHeader().sectionSizeHint(ndx)
                self.tableView.verticalHeader().resizeSection(ndx, sizeHint)
                
        else:
            sizeHint = max([self.tableView.sizeHintForRow(self.selectedRowIndex), self.tableView.verticalHeader().sectionSizeHint(self.selectedRowIndex)])
            #sizeHint = self.tableView.horizontalHeader().sectionSizeHint(self.selectedColumnIndex)
            self.tableView.verticalHeader().resizeSection(self.selectedRowIndex, sizeHint)

    @Slot()
    @safewrapper
    def slot_resizeSelectedColumnsToContents(self):
        if not isinstance(self.selectedColumnIndex, int):
            return
        
        signalBlocker = QtCore.QSignalBlocker(self.tableView.horizontalHeader())
        
        if len(self.tableView.selectionModel().selectedColumns()) > 1:
            col_indices = [ndx.column() for ndx in self.tableView.selectionModel().selectedColumns()]
            
            for ndx in col_indices:
                sizeHint = max([self.tableView.sizeHintForColumn(ndx), self.tableView.horizontalHeader().sectionSizeHint(ndx)])
                #sizeHint = self.tableView.horizontalHeader().sectionSizeHint(ndx)
                self.tableView.horizontalHeader().resizeSection(ndx, sizeHint)
                
        else:
            sizeHint = max([self.tableView.sizeHintForColumn(self.selectedColumnIndex), self.tableView.horizontalHeader().sectionSizeHint(self.selectedColumnIndex)])
            #sizeHint = self.tableView.horizontalHeader().sectionSizeHint(self.selectedColumnIndex)
            self.tableView.horizontalHeader().resizeSection(self.selectedColumnIndex, sizeHint)
        
    @Slot()
    @safewrapper
    def slot_copySelection(self):
        # TODO: 2025-05-24 22:56:56
        # copy data from the actual data, not the model's representation!
        # i.e. if it's a Quantity, then return a Quantity, etc
        
        quote = bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier)
        withHeaders = bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.AltModifier)
        commasep = bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier)
        
        colsep = ", " if commasep else "\t"
        
        modelIndexes = self.tableView.selectedIndexes()
        
        if len(modelIndexes) == 0:
            return
        
        # TODO: 2025-05-24 22:53:10
        # 1) group modelIndexes by row
        # 2) in each row group, sort model indexes by column
        # 3) if smallest column is > 0, fill in with "\t" or ","
        # OR:
        # use the logic in withHeaders branch, below
        
        minRow = minCol = 0
        # don't delete - may be useful later?
        # minCol = min([m.column() for m in modelIndexes])
        # maxCol = max([m.column() for m in modelIndexes])
        # minRow = min([m.row() for m in modelIndexes])
        # maxRow = max([m.row() for m in modelIndexes])
        
        selected_text = list()
        previous = modelIndexes[0]
        #selected_text.append(self._dataModel_.data(previous).toString())
        
        data = str(self._dataModel_.data(previous, QtCore.Qt.EditRole).value())
        if quote:
            data = f"'{data}'"
        
        if withHeaders:
            # preallocate column & row names
            
            minCol = min([m.column() for m in modelIndexes])
            maxCol = max([m.column() for m in modelIndexes])
            minRow = min([m.row() for m in modelIndexes])
            maxRow = max([m.row() for m in modelIndexes])
            
            rowTexts = np.full((maxRow-minRow+2, maxCol-minCol+2), " ", dtype=object)
            
            column = previous.column()
            row = previous.row()
            
            colNdx = column-minCol+1
            rowNdx = row-minRow+1
            
            rowTexts[0,colNdx] = self.getColumnNames(column)
            
            rowTexts[rowNdx,0] = self.getRowNames(row)
            
            rowTexts[rowNdx,colNdx] = data
            
            for modelIndex in modelIndexes[1:]:
                data = str(self._dataModel_.data(modelIndex, QtCore.Qt.EditRole).value())
                if quote:
                    data = f"'{data}'"
                row = modelIndex.row()
                rowNdx = row-minRow+1
                col = modelIndex.column()
                colNdx = col-minCol+1
                
                if col != previous.column():
                    rowTexts[0,colNdx] = self.getColumnNames(col)
                    
                if row != previous.row():
                    rowTexts[rowNdx,0] = self.getRowNames(row) 
                    
                rowTexts[rowNdx,colNdx] = data
                
                previous = modelIndex
                
            for r_ in range(rowTexts.shape[0]):
                selected_text.append(colsep.join(rowTexts[r_,:]))
                selected_text.append("\n")
                    
        else:
            selected_text.append(data)
            
            for modelIndex in modelIndexes[1:]:
                data = str(self._dataModel_.data(modelIndex, QtCore.Qt.EditRole).value())
                if quote:
                    data = f"'{data}'"
                row = modelIndex.row()
                col = modelIndex.column()
                if row != previous.row():
                    selected_text.append("\n")
                    
                elif col != previous.column():
                    selected_text.append(colsep)
                
                selected_text.append(data)
                
                previous = modelIndex
            
        QtGui.QGuiApplication.clipboard().setText("".join(selected_text))
    
    @Slot(QtCore.QPoint)
    @safewrapper
    def slot_table_context_menu_requested(self, pos):
        #print("table_context_menu at pos %s" % pos)
        
        cm = QtWidgets.QMenu("Cell menu", self.tableView)
        copySelectedAction = cm.addAction("Copy")
        
        copySelectedAction.triggered.connect(self.slot_copySelection)

        cm.popup(self.tableView.mapToGlobal(pos), copySelectedAction)

class TabularDataModel(QtCore.QAbstractTableModel):
    r"""Table item model for tabular data in Scipyen.
    Scipyen can handle two types of tabular data:
    • numpy arrays:
        ∘ arrays of up to two dimensions are considered collection of column
            "vectors"; this means that the size of the array on the 1ˢᵗ axis (i.e.,
            axis 0) is the number of "notional" rows of the data, whereas the size
            of the array on the 2ⁿᵈ axis (i.e., axis 1), if present, is the number
            of "notional" columns
        
        ∘ for arrays with more than two dimensions, the model raises exception
            UNLESS the a "squeezed",two-dimensional, view, of the array is used
            (which can only be possible when all dimensions higher than 3 are 
            singleton., i.e., the array size is 1 on any axis k with k >= 2)
        
        ∘ these include Quantity arrays, and their specialized subclasses in the 
            'neo' package
        
    • pandas data structures (DataFrame, Series, Index)
    • vigra Kernel1D and Kernel2D, after conversion to numpy array
    
    CHANGELOG:
    NOTE 2025-11-21 09:43:33
        • enabled editing items, via a new PythonItemDelegate class
        • allows setting immutable (i.e. NOT editable items)
        
    NOTE  2018-11-25 01:24:39
    1. Read-only row/column headers
    2. Supports: 
        * 1D and 2D numpy arrays (by default one-dimensonal numpy arrays are
            displayed as column vectors)
        * pandas DataFrame and Series objects; header data supports MultiIndex
            axis index objects (see pandas Indexing API)

    WARNING use with caution
    """
    sig_editCompleted = Signal([pd.DataFrame], [pd.Series], [np.ndarray], name="sig_editCompleted")
    sig_modelDataChanged = Signal(name="sig_modelDataChanged")
    # NOTE: 2025-11-23 14:03:48 sig_rowsPopulated(startRow, count, total)
    sig_rowsPopulated = Signal(int, int, int, name="sig_rowsPopulated")
    sig_columnsPopulated = Signal(int, int, int, name="sig_columnsPopulated")
    
    def __init__(self, data=None, parent=None):
        super(TabularDataModel, self).__init__(parent=parent)
        
        #if not isinstance(data, (pd.Series, pd.DataFrame, np.ndarray, type(None))):
            #raise TypeError("%s data is not yet supported" % type(data).name)
        
        #if isinstance(data, np.ndarray) and data.ndim > 2:
            #raise TypeError("cannot support numpy array data with more than two dimensions")
        self._is_vigra_filter_kernel_:bool = False
        self._original_data_:typing.Any = None
        self._modelData_:typing.Any= None
        self._modelDataRows_:int = 0
        self._modelDataColumns_:int = 0
        self._immutability_:dict = {"columns": list(), "rows": list(), "joint":False}
        self._rowBatchSize_:int = 10
        self._columnBatchSize_:int = 10
        
        # self._immutableColumns_:typing.Sequence[int] = list()  # of column indexes
        # self._immutableRows_:typing.Sequence[int] = list()     # of row indexes
        
        # NOTE: 2018-11-10 10:58:09
        # how many columns & rows are actually displayed
        self._displayedColumns_:int = 0
        self._displayedRows_:int = 0
        
        self.setModelData(data)
        
    #### BEGIN lazy (paged) display
    #
    def canFetchMore(self, parentIndex:QtCore.QModelIndex) -> bool:
        return False if parentIndex.isValid() else self._displayedRows_ < self._modelDataRows_ or self._displayedColumns_ < self._modelDataColumns_
        # ret = False if parentIndex.isValid() else self._displayedRows_ < self._modelDataRows_ or self._displayedColumns_ < self._modelDataColumns_
        # print(f"{self.__class__.__name__}.canFetchMore -> {ret}")
        # return ret
    
        # if parentIndex.isValid():
        #     return False
        # return self._displayedRows_ < self._modelDataRows_
        # #return self._displayedRows_ < self._modelDataRows_
        # #ret = self._displayedColumns_ < self._modelDataColumns_ or self._displayedRows_ < self._modelDataRows_
        # #print("displayed columns %d" % self._displayedColumns_, "rows %d" % self._displayedRows_)
        # #print("canFetchMore: %s" % ret)
        # #return ret
        
    def fetchMore(self, parentIndex):
        if parentIndex.isValid():
            # print(f"{self.__class__.__name__}.fetchMore: parent is valid, nothing to fetch")
            return 
        
        startRow:int = self._displayedRows_
        startColumn:int = self._displayedColumns_
        
        remainingRows = self._modelDataRows_ - startRow
        remainingColumns = self._modelDataColumns_ - startColumn
        
        rowsToFetch = min(self._rowBatchSize_, remainingRows)
        columnsToFetch = min(self._columnBatchSize_, remainingColumns)
        # print(f"{self.__class__.__name__}.fetchMore: {rowsToFetch} rows and {columnsToFetch} columns to fetch")
        
        if rowsToFetch <= 0 and columnsToFetch <= 0:
            return
        
        if rowsToFetch > 0:
            self.beginInsertRows(QtCore.QModelIndex(), startRow, startRow + rowsToFetch -1)
            self._displayedRows_ += rowsToFetch
            self.endInsertRows()
            
        if columnsToFetch > 0:
            self.beginInsertColumns(QtCore.QModelIndex(), startColumn, startColumn + columnsToFetch -1)
            self._displayedColumns_ += columnsToFetch
            self.endInsertColumns()
        
        self.sig_rowsPopulated.emit(startRow, rowsToFetch, self._modelDataRows_)
        self.sig_columnsPopulated.emit(startColumn, columnsToFetch, self._modelDataColumns_)
            
    #
    #### END lazy (paged) display
                
    #### BEGIN item data handling
    #
    def data(self, modelIndex, role=QtCore.Qt.DisplayRole) -> QtCore.QVariant:
        try:
            if self._modelData_ is None:
                return QtCore.QVariant()
            
            if not modelIndex.isValid():
                return QtCore.QVariant()
            
            row = modelIndex.row()
            col = modelIndex.column()
            
            if row >= self._modelDataRows_ or row < 0:
                return QtCore.QVariant()
            
            if col >= self._modelDataColumns_ or row < 0:
                return QtCore.QVariant()
            
            return self._getModelData_(row, col, role)
            
        except Exception as e:
            traceback.print_exc()
            
    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if self._modelData_ is None:
            return QtCore.QVariant()
        
        return self._getHeaderData_(section, orientation, role)
        
    def rowCount(self, parentIndex:QtCore.QModelIndex = QtCore.QModelIndex()):
        r"""Number of rows the model currently handles.
        This may be less than the notional "rows" in the data 
        """
        return 0 if parentIndex.isValid() else self._displayedRows_
        
    def columnCount(self, parentIndex:QtCore.QModelIndex = QtCore.QModelIndex()):
        return 0 if parentIndex.isValid() else self._displayedColumns_
    
    #### BEGIN editable items
    #
    def flags(self, modelIndex):
        if not modelIndex.isValid():
            return QtCore.Qt.ItemIsEnabled
        
        # if self._readOnly_:
        #     return QtCore.Qt.ItemIsSelectable
        
        return QtCore.Qt.ItemIsEditable | super().flags(modelIndex)
    
        #return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable
    
    def setData(self, modelIndex, value, role=QtCore.Qt.EditRole):
        r"""Set a new data with the specified role, at the specified model index in this model"""
        if self._modelData_ is None:
            return False
        
        row = modelIndex.row()
        col = modelIndex.column()
        
        if row >= self._modelData_.shape[0]:
            return False
        
        if isinstance(self._modelData_, neo.core.dataobject.DataObject):
            if col >= self._modelData_.shape[1] + 1:
                return False
            
        elif col >= self._modelData_.shape[1]:
            return False
            
        if role not in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            return False
        
        if self._setDataValue_(value, row, col):
            # NOTE: This signal (inherited from Qt?) notifies the itemview (here, 
            # the tableView in the TableEditorWidget class) that the data for a
            # model index has changed. the view does what it pleases with it
            # (normally, updates the displayed data)
            #
            # This is really part of the internal model/view mechanism to trigger
            # a selective update in the view, for the data that has actually changed
            # thus avoiding unnecessary repaints in views that display large models
            #
            self.dataChanged.emit(modelIndex, modelIndex)
            
            # I should a similar mechanism to notify other viewers that share the same
            # underlying data — via Scipyen's workspacemodel — thus bypassing
            # the shortcomings of the DataBag trait notifier (which does NOT pick up
            # 'atomic' data changes in arrays, etc)
            # CAUTION/WARNING this only works for my own custom item models!
            self.sig_modelDataChanged.emit()
            return True
        
        return False
        
    #### END editable items
    
    #### BEGIN resizable model
    #
    #
    #### END resizable model
    
    #### END item data handling

    @Slot(object)
    def setModelData(self, data):
        #print("TabularDataModel setModelData")
        from imaging import vigrautils
        
        # ### BEGIN Define timer to debug
        # #
        # timer = QtCore.QElapsedTimer()
        # timer.start()
        #
        # ### END   Define timer debug
        try:
            
            if not isinstance(data, (pd.Series, pd.DataFrame, pd.Index, np.ndarray, vigra.filters.Kernel1D, vigra.filters.Kernel2D, type(None))):
                raise TypeError("%s data is not yet supported" % type(data).__name__)
            
            self.beginResetModel()
            
            # timer1 = QtCore.QElapsedTimer()
            # timer1.start()
            
            self._is_vigra_filter_kernel_ = False
            self._original_data_ = None
            
            if isinstance(data, pd.DataFrame):
                self._modelData_ = data
                self._modelDataRows_ = data.shape[0]
                self._modelDataColumns_ = data.shape[1]
                
            elif isinstance(data, pd.Series):
                self._modelData_ = data
                self._modelDataRows_ = data.shape[0]
                self._modelDataColumns_ = 1
                
            elif isinstance(data, pd.Index):
                self._modelData_ = data
                self._modelDataRows_ = data.shape[0]
                self._modelDataColumns_ = 1
                
            elif isinstance(data, (vigra.filters.Kernel1D, vigra.filters.Kernel2D)):
                self._modelData_ = vigrautils.kernel2array(data)
                self._modelDataRows_ = data.shape[0]
                self._modelDataColumns_ = 1
                self._is_vigra_filter_kernel_ = True
                self._original_data_ = data
                
            elif isinstance(data, np.ndarray):
                # trying to streamline this
                # NOTE: 2025-11-23 09:45:45 FIXME/TODO - TOO SLOW!
                if isinstance(data, neo.core.dataobject.DataObject):
                    # NOTE: 2025-09-27 10:38:00
                    # for regularly sampled signals (neo.AnalogSignal, DataSignal)
                    # signal domain (e.g. time) is a dynamic property, calculated
                    # from the t_start and sampling_period attributes of the signal 
                    # object; hence, individual data points in the domain cannot
                    # be edited; however, the entire domain IS mutable (by changing
                    # the two attributes mentioned above)
                    #
                    if data.ndim:
                        self._modelDataRows_ = data.shape[0]
                        
                        if data.ndim > 1:
                            # include domain as the first column
                            self._modelDataColumns_ = data.shape[1] + 1 
                            
                            if isinstance(data, (neo.AnalogSignal, DataSignal)):
                                # NOTE: 2025-09-27 11:05:05 see NOTE: 2025-09-27 10:38:00
                                # although the signal domain is shown as a regular column
                                # (column 0),  editing data points in this column is
                                # prevented, EXCEPT for the first data point - which is
                                # the t_start
                                #
                                # This may sound contrived, but the native Qt option would
                                # be to call setItemDelegateForColumn and setItemDelegateForRow
                                # with a custom delegate returning a null widget (i.e. None)
                                # but that is already baked in PythonItemDelegate class
                                self._immutableColumns_ = [0]
                                # below, allow editing t_start
                                self._immutableRows_ = range(1,self._modelDataRows_)
                            
                    else:
                        self._modelDataRows_ = 1
                        self._modelDataColumns_ = 1
                    
                    self._modelData_ = data
                    
                else: # "plain" numpy arrays
                    if data.ndim > 2:
                        if all (v == 1 for v in data.shape[2:]):
                            self._modelData_ = np.squeeze(data).reshape((data.shape[0], np.prod(data.shape[1:])))
                        else:
                            raise ValueError("Arrays with more than two dimensions and with non-singleton dimensions higher than 2 are not supported")
                    else:
                        self._modelData_ = data
                        
                    if self._modelData_.ndim:
                        self._modelDataRows_ = self._modelData_.shape[0]
                        if self._modelData_.ndim > 1:
                            self._modelDataColumns_ = self._modelData_.shape[1]
                        else:
                            self._modelDataColumns_ = 1
                    else:
                        self._modelDataRows_ = 1
                        self._modelDataColumns_ = 1
                
            elif data is None:
                self._modelData_ = data
                self._modelDataRows_ = 0
                self._modelDataColumns_ = 0
                
            self._displayedRows_ = 0
            
            # print(f"{self.__class__.__name__}.setModelData({type(data).__name__}) execution during model reset took {timer1.elapsed()} milliseconds")
            
            self.endResetModel()
            
            if self._modelData_ is None:
                self.headerDataChanged.emit(QtCore.Qt.Vertical, 0, 0)
                
            else:
                self.headerDataChanged.emit(QtCore.Qt.Vertical, 0, self._modelDataRows_)
            
        except Exception as e:
            traceback.print_exc()
            
        # ### BEGIN report timing
        #
        # print(f"{self.__class__.__name__}.setModelData({type(data).__name__}) took {timer.elapsed()} milliseconds")
        #
        # ### END   report timing
        
    @safewrapper
    def _getHeaderData_(self, section, orientation, role = QtCore.Qt.DisplayRole):
        # ### BEGIN Timing to debug
        #
        # timer = QtCore.QElapsedTimer()
        #
        # ### END   Timing to debug
        try:
            if role not in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, 
                            QtCore.Qt.ToolTipRole, QtCore.Qt.AccessibleTextRole,
                            QtCore.Qt.AccessibleDescriptionRole):
                return QtCore.QVariant()
                
            if isinstance(self._modelData_, pd.DataFrame):
                if orientation == QtCore.Qt.Horizontal: # column header
                    # NOTE: 2018-11-24 14:57:12
                    # axis indexes in pandas are instances of Index or one of its
                    # subclasses; so we need to check for its subclasses first
                    if isinstance(self._modelData_.columns, pd.MultiIndex):# MultiIndex is subclass of Index so catch it first
                        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.AccessibleTextRole):
                            # NOTE: 2018-11-27 21:32:16
                            # TODO: chech pandas API for other possibilities
                            return QtCore.QVariant(str(self._modelData_.columns[section]))
                        
                        elif role in (QtCore.Qt.ToolTipRole, QtCore.Qt.AccessibleDescriptionRole):
                            #if isinstance(self._modelData_.iloc[:,section], pd.core.arrays.categorical.CategoricalDtype):
                            if "%s" % self._modelData_.iloc[:,section].dtype == "category":
                                
                                if len(self._modelData_.iloc[:,section].cat.categories) > 6:
                                    ret = "\n".join(["%s" % v for v in self._modelData_.columns.names] + \
                                                    ["%d categories:" % len(self._modelData_.iloc[:,section].cat.categories)] + \
                                                    ["%s" % v for v in self._modelData_.iloc[:,section].cat.categories[0:3]] + \
                                                    ["..."] + \
                                                    ["%s" % v for v in self._modelData_.iloc[:,section].cat.categories[-3:]])
                                    
                                    
                                else:
                                    ret = "\n".join(["%s" % v for v in self._modelData_.columns.names] + \
                                                    ["categories:"] +\
                                                    ["%s" % v for v in self._modelData_.iloc[:,section].cat.categories])
                                    
                            else:
                                ret = "\n".join(["%s" % v for v in self._modelData_.columns.names] + ["(%s)" % self._modelData_.iloc[:,section].dtype])
                            
                            return QtCore.QVariant(ret)
                        
                        else:
                            return QtCore.QVariant()
                        
                    elif isinstance(self._modelData_.columns, pd.Index):
                        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.AccessibleTextRole):
                            return QtCore.QVariant(str(self._modelData_.columns[section]))

                        elif role in (QtCore.Qt.ToolTipRole, QtCore.Qt.AccessibleDescriptionRole):
                            #if isinstance(self._modelData_.iloc[:,section], pd.core.arrays.categorical.CategoricalDtype):
                            if "%s" % self._modelData_.iloc[:,section].dtype == "category":
                                if len(self._modelData_.iloc[:,section].cat.categories) > 6:
                                    ret = "\n".join(["%d categories:" % len(self._modelData_.iloc[:,section].cat.categories)] + \
                                                    ["%s" % v for v in self._modelData_.iloc[:,section].cat.categories[0:3]] + \
                                                    ["..."] + \
                                                    ["%s" % v for v in self._modelData_.iloc[:,section].cat.categories[-3:]])
                                    
                                else:
                                    ret = "\n".join(["categories:"] + \
                                                    ["%s" % v for v in self._modelData_.iloc[:,section].cat.categories])
                                #print(ret)
                                
                                return QtCore.QVariant(ret)
                                
                            else:
                                return QtCore.QVariant("%s" % self._modelData_.iloc[:, section].dtype)
                            
                        else:
                            return QtCore.QVariant()
                        
                    
                    else: # NOTE: 2018-11-22 23:16:45 could columns be anything else than Index?
                        return QtCore.QVariant()
                    
                else: # vertical (rows) header
                    if isinstance(self._modelData_.index, pd.MultiIndex):# MultiIndex is subclass of Index so catch it first
                        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.AccessibleTextRole):
                            return QtCore.QVariant(str(self._modelData_.index[section]))
                            
                        elif role in (QtCore.Qt.ToolTipRole, QtCore.Qt.AccessibleDescriptionRole):
                            #if isinstance(self._modelData_.iloc[section,:], pd.core.arrays.categorical.CategoricalDtype):
                            if "%s" % self._modelData_.iloc[section,:].dtype == "category":
                                if len(self._modelData_.iloc[section,:].cat.categories) > 6:
                                    ret = " ".join(["%s" % v for v in self._modelData_.index.names] + \
                                                ["%d categories:" % len(self._modelData_.iloc[section,:].cat.categories)] + \
                                                ["%s" % v for v in self._modelData_.iloc[section,:].cat.categories[0:3]] + \
                                                ["..."] +\
                                                ["%s" % v for v in self._modelData_.iloc[section,:].cat.categories[-3:]])

                                else:
                                    ret = " ".join(["%s" % v for v in self._modelData_.index.names] + \
                                                ["categories:"] + \
                                                ["%s" % v for v in self._modelData_.iloc[section,:].cat.categories])
                                
                            else:
                                ret = " ".join(["%s" % v for v in self._modelData_.index.names] + ["(%s)" % self._modelData_.iloc[section,:].dtype])
                                
                            return QtCore.QVariant(ret)

                        else:
                            return QtCore.QVariant()
                        
                    elif isinstance(self._modelData_.index, pd.Index):
                        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.AccessibleTextRole):
                            return QtCore.QVariant(str(self._modelData_.index[section]))
                            
                        elif role in (QtCore.Qt.ToolTipRole, QtCore.Qt.AccessibleDescriptionRole):
                            #if isinstance(self._modelData_.iloc[:,section], pd.core.arrays.categorical.CategoricalDtype):
                            if "%s" % self._modelData_.iloc[section,:].dtype == "category":
                                if len(self._modelData_.iloc[section,:].cat.category) > 6:
                                    ret = " ".join(["%d categories:" % len(self._modelData_.iloc[section,:].cat.categories)] + \
                                                    ["%s" % v for v in self._modelData_.iloc[section,:].cat.categories[0:3]] + \
                                                    ["..."] + \
                                                    ["%s" % v for v in self._modelData_.iloc[section,:].cat.categories[-3:]])

                                else:
                                    ret = " ".join(["categories:"] + \
                                                    ["%s" % v for v in self._modelData_.iloc[section,:].cat.categories])
                                
                            else:
                                ret = "%s" % self._modelData_.iloc[section,:].dtype # the type of the data row, not of its index !
                                
                            return QtCore.QVariant(ret)

                        else:
                            return QtCore.QVariant()
                        
                    else:
                        return QtCore.QVariant()
                        
            elif isinstance(self._modelData_, pd.Series):
                if orientation == QtCore.Qt.Horizontal: # horizontal (column) headers
                    if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.AccessibleTextRole):
                        return QtCore.QVariant(str(self._modelData_.name))
                        
                    elif role in (QtCore.Qt.ToolTipRole, QtCore.Qt.AccessibleDescriptionRole):
                        #if isinstance(self._modelData_.dtype, pd.core.arrays.categorical.CategoricalDtype):
                        if "%s" % self._modelData_.dtype == "category":
                            if len(self._modelData_.cat.categories) > 6:
                                ret = "\n".join(["%d categories:" % len(self._modelData_.cat.categories)] + \
                                                ["%s" % v for v in self._modelData_.cat.categories[0:3]] + \
                                                ["..."] + \
                                                ["%s" % v for v in self._modelData_.cat.categories[-3:]])

                            else:
                                ret = "\n".join(["categories:"] + \
                                                ["%s" % v for v in self._modelData_.cat.categories])
                            
                            return QtCore.QVariant(ret)
                        
                        else:
                            return QtCore.QVariant("%s" % self._modelData_.dtype)
                        
                    else:
                        return QtCore.QVariant()
                    
                else: # vertical (row) headers
                    if isinstance(self._modelData_.index, pd.MultiIndex): # MultiIndex is subclass of Index so catch it first
                        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.AccessibleTextRole):
                            return QtCore.QVariant(str(self._modelData_.index[section]))
                        
                        elif role in (QtCore.Qt.ToolTipRole, QtCore.Qt.AccessibleDescriptionRole):
                            #if isinstance(self._modelData_.iloc[section], pd.core.arrays.categorical.CategoricalDtype):
                            if "%s" % self._modelData_.iloc[section].dtype == "category":
                                if len(self._modelData_.iloc[section].cat.categories) > 6:
                                    ret = " ".join(["%s" % v for v in self._modelData_.index.names] +\
                                                   ["%d categories:" % len(self._modelData_.iloc[section].cat.categories)] + \
                                                   ["%s" % v for v in self._modelData_.iloc[section].cat.categories[0:3]] + \
                                                   ["..."] + \
                                                   ["%s" % v for v in self._modelData_.iloc[section].cat.categories[-3:]])

                                else:
                                    ret = " ".join(["categories:"] +\
                                                ["%s" % v for v in self._modelData_.iloc[section].cat.categories])
                                
                                return QtCore.QVariant(ret)
                            
                        else:
                            return QtCore.QVariant()
                        
                    elif isinstance(self._modelData_.index, pd.Index): 
                        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.AccessibleTextRole):
                            return QtCore.QVariant(str(self._modelData_.index[section]))
                            
                        elif role in (QtCore.Qt.ToolTipRole, QtCore.Qt.AccessibleDescriptionRole):
                            #if isinstance(self._modelData_.index[section], pd.core.arrays.categorical.CategoricalDtype):
                            if "%s" % self._modelData_.iloc[section].dtype == "category":
                                if len(self._modelData_.iloc[section].cat.categories) > 6:
                                    ret = " ".join(["%d categories:" % len(self._modelData_[section].cat.categories)] + \
                                                   ["%s" % v for v in self._modelData_[section].cat.categories[0:3]] + \
                                                   ["..."] + \
                                                   ["%s" % v for v in self._modelData_[section].cat.categories[-3:]])

                                else:
                                    ret = " ".join(["categories:"] + \
                                                ["%s" % v for v in self._modelData_[section].cat.categories])
                                
                                return QtCore.QVariant(ret)
                                
                            else:
                                return QtCore.QVariant("%s" % self._modelData_[section].dtype) # the type of data at [section]
                            
                        else:
                            return QtCore.QVariant()
                        
                    else:
                        return QtCore.QVariant()
                    
            elif isinstance(self._modelData_, neo.core.dataobject.DataObject):
                if orientation == QtCore.Qt.Horizontal: # horizontal (columns) header
                    if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.AccessibleTextRole):
                        # return QtCore.QVariant("%s (channel %d, %s)" % (self._modelData_.name, section, self._modelData_.dimensionality))
                        # for horizontal header, section number is the column number
                        if section == 0:
                            domain = getattr(self._modelData_, "times", None)
                            domain_name = getattr(self._modelData_,"domain_name", None)
                            if domain_name is None and domain is not None:
                                if isinstance(domain, pq.Quantity):
                                    domain_name = scq.getUnitFamily(domain)
                                    dname = f"{domain_name} ({domain.dimensionality})" if len(domain_name.strip()) else "Sample index"
                                    return QtCore.QVariant(dname)
                                else:
                                    return QtCore.QVariant("Sample")
                            else: 
                                return QtCore.QVariant("Sample")
                            
                        else:
                            return QtCore.QVariant("%s (channel %d, %s)" % (self._modelData_.name, section-1, self._modelData_.dimensionality))
                        
                    elif role in (QtCore.Qt.ToolTipRole, QtCore.Qt.AccessibleDescriptionRole):
                        return QtCore.QVariant("%s" % self._modelData_[:,section].dtype)
                    
                    else:
                        return QtCore.QVariant()
                        
                else: # vertical (rows) headers
                    if isinstance(self._modelData_, (neo.AnalogSignal, DataSignal)):
                        return QtCore.QVariant(self._modelData_.times[section])
                    else:
                        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.AccessibleTextRole):
                            return QtCore.QVariant("%s" % section)
                        
                        elif role in (QtCore.Qt.ToolTipRole, QtCore.Qt.AccessibleDescriptionRole):
                                
                            return QtCore.QVariant("%s" % self._modelData_[section,:].dtype)
                                
                        else:
                            return QtCore.QVariant()
            elif isinstance(self._modelData_, np.ndarray):
                if role in (QtCore.Qt.DisplayRole, QtCore.Qt.AccessibleTextRole):
                    return QtCore.QVariant("%s" % section)
                
                elif role in (QtCore.Qt.ToolTipRole, QtCore.Qt.AccessibleDescriptionRole):
                    if orientation == QtCore.Qt.Horizontal:
                        lbl = "%s" % self._modelData_[:,section].dtype
                        if isinstance(self._modelData_, pq.Quantity):
                            lbl += f" ({self._modelData_.units.dimensionality})"
                        return QtCore.QVariant(lbl)
                        
                    else:
                        return QtCore.QVariant("%s" % self._modelData_[section,:].dtype)
                        
                else:
                    return QtCore.QVariant()
                
            else:
                return QtCore.QVariant()
            
            # NOTE: 2018-11-10 11:12:39 TODO nested lists !!!
                
        except (IndexError, ):
            return QtCore.QVariant()
        
        # print(f"{self.__class__.__name__}._getHeaderData_ took {timer.elapsed()} milliseconds")
        
    def _getModelData_(self, row, col, role = QtCore.Qt.DisplayRole) -> QtCore.QVariant:
        try:
            if role not in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.ToolTipRole, QtCore.Qt.AccessibleTextRole):
                return QtCore.QVariant()
                
            if isinstance(self._modelData_, pd.DataFrame):
                val = self._modelData_.iloc[row,col]
                ret_type = type(val).__name__
                if isinstance(val, datetime.datetime):
                    ret = val if role == QtCore.Qt.EditRole else val.isoformat(" ")
                else:
                    ret = val if role == QtCore.Qt.EditRole else f"{val}"
                
            elif isinstance(self._modelData_, pd.Series):
                val = self._modelData_.iloc[row,col]
                ret_type = type(val).__name__
                if isinstance(val, datetime.datetime):
                    ret = val if role == QtCore.Qt.EditRole else val.isoformat(" ")
                else:
                    ret = val if role == QtCore.Qt.EditRole else f"{val}"

            elif isinstance(self._modelData_, pd.Index):
                if isinstance(self._modelData_, pd.RangeIndex):
                    val = self._modelData_[row]
                else:
                    # CAUTION 2025-05-25 09:09:00 
                    # when _modelData_ is the column index of a DataFrame, ``row`` 
                    # needs to be a column index!
                    val = self._modelData_.iloc[row,col]
                    
                ret_type = type(val).__name__
                
                if isinstance(val, datetime.datetime):
                    ret = val if role == QtCore.Qt.EditRole else val.isoformat(" ")
                else:
                    ret = val if role == QtCore.Qt.EditRole else f"{val}"
                    
            elif isinstance(self._modelData_, neo.core.dataobject.DataObject):
                if col == 0:
                    val = self._modelData_.times[row]
                else:
                    val = self._modelData_[row, col-1]
                    
                if isinstance(val, datetime.datetime):
                    ret = val if role == QtCore.Qt.EditRole else ret.isoformat(" ")
                else:
                    ret = val if role == QtCore.Qt.EditRole else f"{val.magnitude}"
                    
            elif isinstance(self._modelData_, np.ndarray):
                if self._modelData_.ndim  == 0: # e.g. pq object
                    val = np.atleast_1d(self._modelData_)[row]
                    
                elif self._modelData_.ndim > 1:
                    val = self._modelData_[row, col]
                    
                else:
                    val = self._modelData_[row]
                

                if isinstance(val, datetime.datetime):
                    ret = val if role == QtCore.Qt.EditRole else ret.isoformat(" ")
                else:
                    ret = val if role == QtCore.Qt.EditRole else f"{val.magnitude}" if isinstance(self._modelData_, pq.Quantity) else f"{val}"
                
            else:
                return QtCore.QVariant()
            
            ret_type = type(val).__name__
            
            if role == QtCore.Qt.EditRole:
                return QtCore.QVariant(val)
                
            elif role == QtCore.Qt.DisplayRole:
                return QtCore.QVariant("%s" % ret)
            
            elif role in (QtCore.Qt.ToolTipRole, QtCore.Qt.AccessibleDescriptionRole):
                return QtCore.QVariant(ret_type)
            
            elif role in (QtCore.Qt.UserRole, ):
                return QtCore.QVariant(val)
                # return val
            
            else:
                return QtCore.QVariant()
            
        except (IndexError,):
            return QtCore.QVariant()
        
    def _setDataValue_(self, value, row, col):
        r"""Sets the EditRole data for the row & column in the tabular model"""
        if self._modelData_ is None:
            return False
        
        try:
            if isinstance(value, QtCore.QVariant) or hasattr(value, "value"):
                pyvalue = value.value()
                
            else:
                pyvalue = value
                
            if isinstance(self._modelData_, pd.DataFrame):
                self._modelData_.at[data_row, data_col] = pyvalue
                
            elif isinstance(self._modelData_, pd.Series):
                self._modelData_.at[data_row] = pyvalue
                
            elif isinstance(self._modelData_, neo.dataobject.DataObject):
                if col == 0:
                    if isinstance(self._modelData_, (neo.AnalogSignal, DataSignal)) :
                        if row == 0:
                            # allow setting t_start
                            if isinstance(pyvalue, pq.Quantity):
                                if pyvalue.units != self._modelData_.times.units:
                                    raise ValueError(f"Expecting value units of {self._modelData_.times.units}; got ({pyvalue.units}) instead")
                                
                                self._modelData_.t_start = pyvalue
                                
                            elif isinstance(pyvalue, (float, int, complex)):
                                self._modelData_.t_start = pyvalue * self._modelData_.units
                            else:
                                raise TypeError(f"Expecting a float or a Quantity in {self._modelData_.times.units}; got {type(pyvalue).__name__} instead")
                        else:
                            return
                    else:
                        if isinstance(pyvalue, pq.Quantity):
                            if pyvalue.units != self._modelData_.times.units:
                                raise ValueError(f"Expecting value units of {self._modelData_.times.units}; got ({pyvalue.units}) instead")
                            
                            self._modelData_.times[row] = pyvalue
                            
                        elif isinstance(pyvalue, (float, int, complex)):
                            self._modelData_.times[row] = pyvalue * self._modelData_.units
                        else:
                            raise TypeError(f"Expecting a float or a Quantity in {self._modelData_.times.units}; got {type(pyvalue).__name__} instead")
                        
                else:
                    if isinstance(pyvalue, pq.Quantity):
                        if pyvalue.units != self._modelData_.units:
                            raise ValueError(f"Expecting value units of {self._modelData_.units}; got ({pyvalue.units}) instead")
                        
                        self._modelData_[row, col-1] = pyvalue
                        
                    elif isinstance(pyvalue, (float, int, complex)):
                        self._modelData_[row, col-1] = pyvalue * self._modelData_.units
                    else:
                            raise TypeError(f"Expecting a float or a Quantity in {self._modelData_.units}; got {type(pyvalue).__name__} instead")
                            
            elif isinstance(self._modelData_, np.ndarray):
                self._modelData_[row, col] = pyvalue
                if self._is_vigra_filter_kernel_:
                    self._original_data_ = vigrautils.kernelfromarray(self._modelData_)
                        
            else:
                return False
            
            return True
            
        except Exception as e:
            traceback.print_exc()
            return False
        
        # NOTE: 2018-11-22 11:11:43
        # don't delete this; contemplate using it at module/app level
        #sip.enableautoconversion(QtCore.QVariant, old_qvariant_autoconv)
            
        return False
    
    @property
    def sourceData(self):
        r"""Access to the source data behind this model.
    """
        if self._is_vigra_filter_kernel_:
            return self._original_data_
        return self._modelData_
    
    @property
    def immutability(self) -> dict:
        return self._immutability_
    
    @immutability.setter
    def immutability(self, value:dict):
        # d = {"columns":list(), "rows": list(), "joint":False}
        if not isinstance(value, dict):
            self._immutability_ = {"columns":list(), "rows": list(), "joint":False}
        else:
            if "columns" in value and isinstance(value["columns"], typing.Sequence):
                if len(value["columns"]) == 0 or not all(isinstance(v, int) for v in value["columns"]):
                    self._immutability_["columns"] = list()
                    
                else:
                    self._immutability_["columns"] = list(value["columns"])
                    
            if "rows" in value and isinstance(value["rows"], typing.Sequence):
                if len(value["rows"]) == 0 or not all(isinstance(v, int) for v in value["rows"]):
                    self._immutability_["rows"] = list()
                    
                else:
                    self._immutability_["rows"] = list(value["rows"])
                    
            if "joint" in value:
                if isinstance(value["joint"], bool):
                    self._immutability_["value"] = value["joint"]
                else:
                    self._immutability_["value"] = False
    
    @property
    def jointImmutability(self) -> bool:
        return self._immutability_["joint"]
    
    @jointImmutability.setter
    def jointImmutability(self, value:bool):
        self._immutability_["joint"] = value == True
    
    @property
    def immutableColumns(self) -> typing.Sequence[int]:
        return self._immutability_["columns"]
    
    @immutableColumns.setter
    def immutableColumns(self, value:typing.Sequence[int]):
        self._immutability_["columns"] = value
        
    @property
    def immutableRows(self) -> typing.Sequence[int]:
        return self._immutability_["rows"]
    
    @immutableRows.setter
    def immutableRows(self, value:typing.Sequence[int]):
        self._immutability_["rows"] = value
