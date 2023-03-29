#### BEGIN core python modules
from __future__ import print_function

import os, inspect, warnings, traceback, datetime, typing
#### END core python modules

#### BEGIN 3rd party modules
import pandas as pd
import quantities as pq
#import xarray as xa
import numpy as np
import neo
import vigra

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.pylab as plb
import matplotlib.mlab as mlb
#### END 3rd party modules

#### BEGIN pict.core modules
#from core.patchneo import *
import core.datatypes as dt

import core.strutils as strutils
from core.strutils import str2float

from core.prog import (safeWrapper, )

from core.triggerevent import (DataMark, MarkType, TriggerEvent, TriggerEventType)
from core.triggerprotocols import TriggerProtocol
from core.datazone import DataZone

import core.datasignal
from core.datasignal import (DataSignal, IrregularlySampledDataSignal,)
from core.datatypes import array_slice

#### END pict.core modules

#### BEGIN pict.gui modules
from gui.scipyenviewer import ScipyenViewer #, ScipyenFrameViewer
from gui import quickdialog
from gui import resources_rc
#### END pict.gui modules

#### BEGIN pict.iolib modules
import iolib.pictio as pio
#### END pict.iolib modules

__module_path__ = os.path.abspath(os.path.dirname(__file__))

__module_name__ = os.path.splitext(os.path.basename(__file__))[0]

Ui_TableEditorWidget, QWidget = __loadUiType__(os.path.join(__module_path__, "tableeditorwidget.ui"))

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
    
    #def __init__(self, model:typing.Optional[QtCore.QAbstractTableModel]=None, 
                 #parent:typing.Optional[QtWidgets.QMainWindow]=None) -> None:
    def __init__(self, parent:typing.Optional[QtWidgets.QMainWindow]=None) -> None:
        super().__init__(parent=parent)
        
        self._dataModel_ = TabularDataModel(parent=self)
        
        # NOTE: 2021-10-18 09:32:45
        # ### BEGIN keep this  - you may re-enable the possibility to use custom tabular
        # data models
        
        #if model is None:
            #self._dataModel_ = TabularDataModel(parent=self)
            
        #else:
            #self._dataModel_ = model
        # ### END keep this ...
        
        self._configureUI_()
        
        # NOTE: 2021-08-16 17:22:20
        # By default, this is defined in the .ui file as:
        # QtWidgets.QAbstractItemView.DoubleClicked |
        # QtWidgets.QAbstractItemView.EditKeyPressed |
        # QtWidgets.QAbstractItemView.AnyKeyPressed
        self._defaultEditTriggers_ = self.tableView.editTriggers()
        
        self._data_ = None
        
        self._slicingAxis_ = None
        
        self._currentSlice_ = 0
        
    def setData(self, data:(pd.DataFrame, pd.Series, neo.core.baseneo.BaseNeo,
                       neo.AnalogSignal, neo.IrregularlySampledSignal,
                       neo.Epoch, neo.Event, neo.SpikeTrain,
                       DataSignal, IrregularlySampledDataSignal,
                       TriggerEvent, TriggerProtocol,
                       np.ndarray, vigra.VigraArray, vigra.filters.Kernel1D, vigra.filters.Kernel2D), *args, **kwargs):
        
        self._data_ = data
        
        if isinstance(data, np.ndarray):
            if data.ndim > 2:
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
                return
        
        self.prevSliceToolbutton.setEnabled(False)
        self.nextSliceToolButton.setEnabled(False)
        self._dataModel_.setModelData(self._data_)
        
    @pyqtSlot()
    def _slot_prevSlice(self):
        if isinstance(self._data_, np.ndarray) and self._data_.ndim > 2:
            if self.currentSlice > 0:
                self.currentSlice = self.currentSlice - 1
        
    @pyqtSlot()
    def _slot_nextSlice(self):
        if isinstance(self._data_, np.ndarray) and self._data_.ndim > 2:
            if self.currentSlice <= self._data_.shape[self._slicingAxis_] -1 :
                self.currentSlice = self.currentSlice + 1
        
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
        self.tabelView.setModel(self._dataModel_)
        
    @property
    def readOnly(self):
        return self.tableView.editTriggers() == QtWidgets.QAbstractItemView.NoEditTriggers
    
    @readOnly.setter
    def readOnly(self, val:bool):
        if val:
            self.tableView.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        else:
            self.tableView.setEditTriggers(self._defaultEditTriggers_)
            
    def setEditTriggers(self, val):
        """See documentation for QtWidgets.QAbstractItemView.setEditTriggers()
        """
        self.tableView.setEditTriggers(val)
            
    def _configureUI_(self):
        self.setupUi(self)
        self.tableView.setSortingEnabled(False)
        self.tableView.setModel(self._dataModel_)
        #self._dataModel_.signal_rowsPopulated[int].connect(self.slot_rowsReceived)
        #self._dataModel_.signal_columnsPopulated[int].connect(self.slot_columnsReceived)
        
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
        #self.tableView.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        #self.tableView.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.tableView.verticalHeader().setResizeContentsPrecision(0) 
        
        self.tableView.verticalHeader().setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tableView.verticalHeader().customContextMenuRequested[QtCore.QPoint].connect(self.slot_vertical_header_context_menu_request)
        
        
        self.tableView.setAlternatingRowColors(True)
        #self.tableView.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.tableView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tableView.customContextMenuRequested[QtCore.QPoint].connect(self.slot_table_context_menu_requested)

        self.resizeColumnsToolButton.clicked.connect(self.slot_resizeAllColumnsToContents)
        self.resizeRowsToolButton.clicked.connect(self.slot_resizeAllRowsToContents)
        
        self.prevSliceToolbutton.setEnabled(False)
        self.prevSliceToolbutton.clicked.connect(self._slot_prevSlice)
        self.nextSliceToolButton.setEnabled(False)
        self.nextSliceToolButton.clicked.connect(self._slot_nextSlice)
        
    @pyqtSlot()
    def slot_resizeAllColumnsToContents(self):
        #print("TableEditorWidget slot_resizeAllColumnsToContents")
        signalBlockers = [QtCore.QSignalBlocker(v) for v in (self.tableView.horizontalHeader(), self.tableView.verticalHeader())]
        self.tableView.horizontalHeader().resizeSections(QtWidgets.QHeaderView.ResizeToContents)
        
    @pyqtSlot()
    def slot_resizeAllRowsToContents(self):
        signalBlockers = [QtCore.QSignalBlocker(v) for v in (self.tableView.horizontalHeader(), self.tableView.verticalHeader())]
        self.tableView.verticalHeader().resizeSections(QtWidgets.QHeaderView.ResizeToContents)
        
    @pyqtSlot(QtCore.QPoint)
    @safeWrapper
    def slot_horizontal_header_context_menu_request(self, pos):
        #print("horizontal header context menu at pos %s" % pos)
        #print("clicked column %s" % self.tableView.columnAt(pos.x()))
        
        self.selectedColumnIndex = self.tableView.columnAt(pos.x())
        
        cm = QtWidgets.QMenu("Column Menu", self.tableView)
        copyColumnTitleAction = cm.addAction("Copy column name")
        copyColumnTitleAction.triggered.connect(self.slot_copyColumnName)
        
        resizeColumnToContentsAction = cm.addAction("Resize to contents")
        resizeColumnToContentsAction.triggered.connect(self.slot_resizeSelectedColumnsToContents)
        
        resizeAllColumsToContextAction = cm.addAction("Resize All Columns To Contents")
        
        resizeAllColumsToContextAction.triggered.connect(self.slot_resizeAllColumnsToContents)
        #copyColumnContents = cm.addAction("Copy column data")
        
        cm.exec(self.tableView.mapToGlobal(pos))
        
    @pyqtSlot(QtCore.QPoint)
    @safeWrapper
    def slot_vertical_header_context_menu_request(self, pos):
        self.selectedRowIndex = self.tableView.rowAt(pos.x())
        
        cm = QtWidgets.QMenu("Row Menu", self.tableView)
        copyColumnTitleAction = cm.addAction("Copy row name")
        copyColumnTitleAction.triggered.connect(self.slot_copyRowName)
        
        resizeRowToContentsAction = cm.addAction("Resize to contents")
        resizeRowToContentsAction.triggered.connect(self.slot_resizeSelectedRowsToContents)
        
        resizeAllRowsToContextAction = cm.addAction("Resize All Rows To Contents")
        
        resizeAllRowsToContextAction.triggered.connect(self.slot_resizeAllRowsToContents)
        
        cm.exec(self.tableView.mapToGlobal(pos))
        
    @pyqtSlot()
    @safeWrapper
    def slot_copyColumnName(self):
        if not isinstance(self.selectedColumnIndex, int):
            return
        
        #columnName = self.tableView.horizontalHeaderItem(self.selectedColumnIndex).text()
        
        # NOTE: 2018-11-28 23:38:29
        # this is a QtCore.QVariant that wraps a python str
        columnName = self.tableView.model().headerData(self.selectedColumnIndex, QtCore.Qt.Horizontal).value()
        
        QtWidgets.QApplication.instance().clipboard().setText(columnName)
        
    @pyqtSlot()
    @safeWrapper
    def slot_copyRowName(self):
        if not isinstance(self.selectedRowIndex, int):
            return
        
        rowName = self.tableView.verticalheaderItem(self.selectedRowIndex).text()
        
        QtWidgets.QApplication.instance().clipboard().setText(rowName)
        
    @pyqtSlot(QtWidgets.QTableWidgetItem)
    @safeWrapper
    def slot_tableEdited(self, item):
        # TODO code for xarray.DataArray
        # TODO code for multi-indexed pandas data frames
        # TODO code for as_type(...) for pandas data -- e.g. categorical
        col = item.column()
        row = item.row()
        value = item.text()
        
        if isinstance(self._data_, pd.DataFrame):
            colHeaderText = self.tableView.horizontalHeaderItem(col).text()
            
            if colHeaderText not in self._data_.columns:
                raise RuntimeError("%s not found in data columns!" % colHeaderText)
            
            columnDType = self._data_[colHeaderText].dtype
            
            if np.can_cast(eval(value), columnDType):
                if columnDType == np.dtype("bool"):
                    if value.lower().strip() in ("true, t, 1"):
                        value = "True"
                        
                    elif value.lower().strip() in ("false, f, 0"):
                        value = False
                        
                # CAUTION here
                data_value = np.array(eval(value), dtype=columnDType)
                
                self._data_.loc[self._data_.index[row], colHeaderText] = data_value
                
            else:
                raise RuntimeError("cannot cast %s to %s" % (value, columnDType))
            
            
        elif isinstance(self._data_, pd.Series):
            dataDType = self._data_.dtype
            
            if np.can_cast(eval(value), dataDType):
                data_value = np.array(eval(value), dtype=dataDType)
            
                self._data_.loc[self._data_.index[row]] = data_value
            
        elif isinstance(self._data_, np.ndarray):
            dataDType = self._data_.dtype
            
            if np.can_cast(eval(value), dataDType):
                data_value = np.array(eval(value), dtype=dataDType)
                
                if self._data_.ndim == 3:
                    self._data_[row,col,self.frameNo] = data_value
                    
                elif self._data_.ndim == 2:
                    self._data_[row,col] = data_value
                    
                elif self._data_.ndim == 1:
                    self._data_[row] = data_value
           
            else:
                raise RuntimeError("cannot cast %s to %s" % (value, dataDType))
            
    @pyqtSlot()
    @safeWrapper
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

    @pyqtSlot()
    @safeWrapper
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
        
    @pyqtSlot()
    @safeWrapper
    def slot_copySelection(self):
        modelIndexes = self.tableView.selectedIndexes()
        selected_text = list()
        previous = modelIndexes[0]
        #selected_text.append(self._dataModel_.data(previous).toString())
        selected_text.append(str(self._dataModel_.data(previous).value()))
        
        for modelIndex in modelIndexes[1:]:
            #data = self._dataModel_.data(modelIndex).toString()
            data = str(self._dataModel_.data(modelIndex).value())
            if modelIndex.row() != previous.row():
                selected_text.append("\n")
                
            elif modelIndex.column() != previous.column():
                selected_text.append("\t")
            
            selected_text.append(data)
            
            previous = modelIndex
            
        QtGui.QGuiApplication.clipboard().setText("".join(selected_text))
    
    @pyqtSlot(QtCore.QPoint)
    @safeWrapper
    def slot_table_context_menu_requested(self, pos):
        #print("table_context_menu at pos %s" % pos)
        
        cm = QtWidgets.QMenu("Cell menu", self.tableView)
        copySelectedAction = cm.addAction("Copy")
        
        copySelectedAction.triggered.connect(self.slot_copySelection)

        cm.popup(self.tableView.mapToGlobal(pos), copySelectedAction)

class TabularDataModel(QtCore.QAbstractTableModel):
    """
    Change log:
    NOTE  2018-11-25 01:24:39
    1. Read-only row/column headers
    2. Supports: 
        * 1D and 2D numpy arrays (by default one-dimensonal numpy arrays are
            displayed as column vectors)
        * pandas DataFrame and Series objects; header data supports MultiIndex
            axis index objects (see pandas Indexing API)

    WARNING use with caution
    """
    editCompleted = pyqtSignal([pd.DataFrame], [pd.Series], [np.ndarray], name="editCompleted")
    
    signal_rowsPopulated = pyqtSignal(int, name="signal_rowsPopulated")
    signal_columnsPopulated = pyqtSignal(int, name="signal_columnsPopulated")
    
    def __init__(self, data=None, parent=None):
        super(TabularDataModel, self).__init__(parent=parent)
        
        #if not isinstance(data, (pd.Series, pd.DataFrame, np.ndarray, type(None))):
            #raise TypeError("%s data is not yet supported" % type(data).name)
        
        #if isinstance(data, np.ndarray) and data.ndim > 2:
            #raise TypeError("cannot support numpy array data with more than two dimensions")
        
        self._modelData_ = None
        self._modelRows_ = 0
        self._modelColumns_ = 0
        
        # NOTE: 2018-11-10 10:58:09
        # how many columns & rows are actually displayed
        #self._displayedColumns = 0
        self._displayedRows_ = 0
        
        #self._viewers_ = list()
        
        self.setModelData(data)
        
    #### BEGIN paged display
    #def canFetchMore(self, parentIndex):
        #return True
        ##return self._displayedRows_ < self._modelRows_
        ##ret = self._displayedColumns < self._modelColumns_ or self._displayedRows_ < self._modelRows_
        ##print("displayed columns %d" % self._displayedColumns, "rows %d" % self._displayedRows_)
        ##print("canFetchMore: %s" % ret)
        ##return ret
        
    #def fetchMore(self, parentIndex):
        #remainingRows = self._modelRows_ - self._displayedRows_
        ##remainingColumns = self._modelColumns_ - self._displayedColumns
        ##print("remaining rows %d" % remainingRows, "columns %d" % remainingColumns)
        
        #rowsToFetch = min(10, remainingRows)
        ##columnsToFetch = min(2, remainingColumns)
        
        #if remainingRows > 0:
            #self.beginInsertRows(QtCore.QModelIndex(), self._displayedRows_, self._displayedRows_ + rowsToFetch -1)
            #self._displayedRows_ += rowsToFetch
            #self.endInsertRows()
            
            ##self.signal_rowsPopulated.emit(rowsToFetch)
            
        ##if remainingColumns > 0:
            ##self.beginInsertColumns(QtCore.QModelIndex(), self._displayedColumns, self._displayedColumns + columnsToFetch -1)
            ##self._displayedColumns += columnsToFetch
            ##self.endInsertColumns()
            
            ##self.signal_columnsPopulated.emit(columnsToFetch)
    
    #### END paged display
                
    #### BEGIN item data handling
    #### BEGIN read-only access
    def data(self, modelIndex, role=QtCore.Qt.DisplayRole):
        try:
            if self._modelData_ is None:
                return QtCore.QVariant()
            
            if not modelIndex.isValid():
                return QtCore.QVariant()
            
            row = modelIndex.row()
            col = modelIndex.column()
            
            if row >= self._modelRows_ or row < 0:
                return QtCore.QVariant()
            
            if col >= self._modelColumns_ or row < 0:
                return QtCore.QVariant()
            
            return self.__getModelData__(row, col, role)
            
        except Exception as e:
            traceback.print_exc()
            
    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        #print("TabularDataModel headerData")
        if self._modelData_ is None:
            return QtCore.QVariant()
        
        return self.__getHeaderData__(section, orientation, role)
        
    def rowCount(self, parentIndex=QtCore.QModelIndex()):
        #print("TabularDataModel rowCount")
        return self._modelRows_
        
    def columnCount(self, parentIndex=QtCore.QModelIndex()):
        #print("TabularDataModel columnCount")
        return self._modelColumns_
        
    #### END  read-only access
    
    #### BEGIN editable items
    def flags(self, modelIndex):
        #print("TabularDataModel flags")
        if not modelIndex.isValid():
            return QtCore.Qt.ItemIsEnabled
        
        return QtCore.Qt.ItemIsEditable | super().flags(modelIndex)
        #return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable
    
    def setData(self, modelIndex, value, role=QtCore.Qt.EditRole):
        if self._modelData_ is None:
            return False
        
        row = modelIndex.row()
        col = modelIndex.column()
        
        if row >= self._modelData_.shape[0]:
            return False
        
        if col >= self._modelData_.shape[1]:
            return False
            
        if role != QtCore.Qt.EditRole:
            return False
        
        if self._setDataValue_(value, row, col):
            self.dataChanged.emit(modelIndex, modelIndex)
            return True
        
        return False
        
    #### END editable items
    
    #### BEGIN resizable model
    
    #### END resizable model
    
    #### END item data handling

    def setModelData(self, data):
        #print("TabularDataModel setModelData")
        try:
            if not isinstance(data, (pd.Series, pd.DataFrame, np.ndarray, type(None))):
                raise TypeError("%s data is not yet supported" % type(data).__name__)
            
            #if isinstance(data, np.ndarray) and data.ndim > 2:
                #raise TypeError("cannot support numpy array data with more than two dimensions")
            
            self.beginResetModel()
            
            #self._modelData_ = data
            
            if isinstance(data, pd.DataFrame):
                self._modelData_ = data
                self._modelRows_ = data.shape[0]
                self._modelColumns_ = data.shape[1]
                #self._modelData_ = data.values
                #self._modelDataRowHeaders = data.index
                #self._modelDataColumnHeaders = data.columns
                
            elif isinstance(data, pd.Series):
                self._modelData_ = data
                self._modelRows_ = data.shape[0]
                self._modelColumns_ = 1
                #self._modelData_ = data.values
                #self._modelDataRowHeaders = data.index
                #self._modelDataColumnHeaders = data.name
                
            elif isinstance(data, pd.Index):
                self._modelData_ = data
                self._modelRows_ = data.shape[0]
                self._modelColumns_ = 1
                
            elif isinstance(data, (neo.AnalogSignal, neo.IrregularlySampledSignal, DataSignal, IrregularlySampledDataSignal)):
                if data.ndim:
                    self._modelRows_ = data.shape[0]
                    
                    if data.ndim > 1:
                        self._modelColumns_ = data.shape[1] + 1 # include domain as the first column
                    
                else:
                    self._modelRows_ = 1
                    self._modelColumns_ = 1
                
                #self._modelRows_ = data.shape[0]
                #self._modelColumns_ = data.shape[1] + 1 
                self._modelData_ = data
                
            elif isinstance(data, np.ndarray):
                if data.ndim > 2:
                    self._modelData_ = np.squeeze(data).reshape((data.shape[0], np.prod(data.shape[1:])))
                else:
                    self._modelData_ = data
                    
                if self._modelData_.ndim:
                        
                    self._modelRows_ = self._modelData_.shape[0]
                    
                    if self._modelData_.ndim > 1:
                        self._modelColumns_ = self._modelData_.shape[1]
                        
                    else:
                        self._modelColumns_ = 1
                    
                else:
                    self._modelRows_ = 1
                    self._modelColumns_ = 1
                
            elif data is None:
                self._modelData_ = data
                self._modelRows_ = 0
                self._modelColumns_ = 0
                
            #self._displayedColumns = 0
            self._displayedRows_ = 0
            
            self.endResetModel()
            
            #print("TabularDataModel setModelData %s" % type(self._modelData_).__name__)
            if self._modelData_ is None:
                self.headerDataChanged.emit(QtCore.Qt.Vertical, 0, 0)
                
            else:
                #self.headerDataChanged.emit(QtCore.Qt.Vertical, 0, self._modelData_.shape[0])
                self.headerDataChanged.emit(QtCore.Qt.Vertical, 0, self._modelRows_)
            
        except Exception as e:
            traceback.print_exc()
        
    #@property
    #def views(self):
        #return self._viewers_
            
    #def appendView()
    
    @safeWrapper
    def __getHeaderData__(self, section, orientation, role = QtCore.Qt.DisplayRole):
        try:
            if role not in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.ToolTipRole, QtCore.Qt.AccessibleTextRole):
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
                if orientation == QtCore.Qt.Horizontal:
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
                    
                else:
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
                    
            #elif isinstance(self._modelData_, (neo.AnalogSignal, neo.IrregularlySampledSignal, DataSignal, IrregularlySampledDataSignal)):
            elif isinstance(self._modelData_, neo.core.basesignal.BaseSignal):
                if orientation == QtCore.Qt.Horizontal: # horizontal (columns) header
                    if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.AccessibleTextRole):
                        if section == 0:
                            if isinstance(self._modelData_, (neo.IrregularlySampledSignal, IrregularlySampledDataSignal)):
                                domain_name = getattr(self._modelData_,"domain_name", None)
                                domain = getattr(self._modelData_, "domain", None)
                                if isinstance(domain_name, str) and isinstance(domain, pq.Quantity):
                                    dname = f"{domain_name} ({domain.dimensionality})" if len(domain_name.strip()) else "Sample index"
                                    return QtCore.QVariant(dname)
                                    #return QtCore.QVariant("%s (%s)" % (self._modelData_.domain_name, self._modelData_.domain.dimensionality))
                                else:
                                    return QtCore.QVariant("Sample")
                                                       
                            else:
                                return QtCore.QVariant("Time (%s)" % self._modelData_.times.dimensionality)
                            
                        else:
                            return QtCore.QVariant("%s (channel %d, %s)" % (self._modelData_.name, section-1, self._modelData_.dimensionality))
                        
                    elif role in (QtCore.Qt.ToolTipRole, QtCore.Qt.AccessibleDescriptionRole):
                        return QtCore.QVariant("%s" % self._modelData_[:,section].dtype)
                    
                    else:
                        return QtCore.QVariant()
                        
                else: # vertical (rows) header
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
                        return QtCore.QVariant("%s" % self._modelData_[:,section].dtype)
                        
                    else:
                        return QtCore.QVariant("%s" % self._modelData_[section,:].dtype)
                        
                else:
                    return QtCore.QVariant()
                
            else:
                return QtCore.QVariant()
            
            # NOTE: 2018-11-10 11:12:39 TODO nested lists !!!
                
        except (IndexError, ):
            return QtCore.QVariant()
        
    def __getModelData__(self, row, col, role = QtCore.Qt.DisplayRole):
        try:
            if role not in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.ToolTipRole, QtCore.Qt.AccessibleTextRole):
                return QtCore.QVariant()
                
            if isinstance(self._modelData_, pd.DataFrame):
                ret = self._modelData_.iloc[row,col]
                
                ret_type = type(ret).__name__

                if isinstance(ret, datetime.datetime):
                    ret = ret.isoformat(" ")
                
            elif isinstance(self._modelData_, pd.Series):
                ret = self._modelData_.iloc[row]
                
                ret_type = type(ret).__name__
                
                if isinstance(ret, datetime.datetime):
                    ret = ret.isoformat(" ")
                    
            elif isinstance(self._modelData_, pd.Index):
                ret = self._modelData_[row]
                
                ret_type = type(ret).__name__

                if isinstance(ret, datetime.datetime):
                    ret = ret.isoformat(" ")
                    
            elif isinstance(self._modelData_, (neo.AnalogSignal, neo.IrregularlySampledSignal, DataSignal, IrregularlySampledDataSignal)):
                if col == 0:
                    ret = self._modelData_.times[row]
                    ret_type = type(ret).__name__
                    
                else:
                    ret = self._modelData_[row, col-1]
                    ret_type = type(ret).__name__
                    
                if isinstance(ret, pq.Quantity):
                    ret = ret.magnitude
                    
            elif isinstance(self._modelData_, np.ndarray):
                if self._modelData_.ndim  == 0: # e.g. pq object
                    ret = np.atleast_1d(self._modelData_)[row]
                    
                elif self._modelData_.ndim > 1:
                    ret = self._modelData_[row, col]
                    
                else:
                    ret = self._modelData_[row]
                
                ret_type = type(ret).__name__

                if isinstance(ret, datetime.datetime):
                    ret = ret.isoformat(" ")
                
            else:
                return QtCore.QVariant()
                
            if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
                return QtCore.QVariant("%s" % ret)
            
            elif role in (QtCore.Qt.ToolTipRole, QtCore.Qt.AccessibleDescriptionRole):
                return QtCore.QVariant(ret_type)
            
            elif role in (QtCore.Qt.UserRole, ):
                return QtCore.QVariant(ret)
            
            else:
                return QtCore.QVariant()
            
        except (IndexError,):
            return QtCore.QVariant()
        
    def _setDataValue_(self, value, row, col):
        if self._modelData_ is None:
            return False
        
        if not isinstance(value, str):
            raise TypeError("Expecting a str, got %s instead" % type(value).__name__)
        
        # NOTE: 2018-11-22 11:11:43
        # don't delete this; contemplate using it at module/app level
        #old_qvariant_autoconv = sip.enableautoconversion(QtCore.QVariant, False)
        
        try:
            if isinstance(self._modelData_, pd.DataFrame):
                data_row = self._modelData_.index[row]
                data_col = self._modelData_.columns[col]
                
                current_value = self._modelData_.loc[data_row, data_col]
                
                if hasattr(current_value, "dtype"):
                    data_type = current_value.dtype.type
                    
                else:
                    data_type = type(current_value)
                
                #data_type = self._modelData_.loc[data_row, data_col].dtype
                #data_type = self._modelData_.iloc[row, col].dtype
                
                if isinstance(value, QtCore.QVariant) or hasattr(value, "value"):
                    pyvalue = value.value()
                    
                else:
                    pyvalue = value
                
                if data_type != object:
                    if isinstance(pyvalue, str):
                        if len(pyvalue.strip()) > 0:
                            data_value = pyvalue
                            
                        else:
                            data_value = None
                        
                    #else:
                data_value = data_type(data_value)
                    
                self._modelData_.at[data_row, data_col] = data_value
                #self._modelData_.set_value(data_row, data_col, data_value)
                
                #result = np.fromstring(value, dtype=data_type)
                #self._modelData_.loc[data_row, data_col] = result
                #self._modelData_.iloc[row, col] = result
                
            elif isinstance(self._modelData_, pd.Series):
                data_row = self._modelData_.index[row]
                current_value = self._modelData_.loc[row]
                if hasattr(current_value, "dtype"):
                    data_type = self._modelData_.loc[row].dtype.type
                    
                else:
                    data_type = type(current_value)
                #data_type = self._modelData_.iloc[row].dtype
                
                if isinstance(value, QtCore.QVariant) or hasattr(value, "value"):
                    pyvalue = value.value()
                    
                else:
                    pyvalue = value
                
                if data_type != object:
                    if isinstance(pyvalue, str):
                        if len(pyvalue.strip()) > 0:
                            data_value = pyvalue
                            
                        else:
                            data_value = None
                        
                    #else:
                data_value = data_type(data_value)
                        
                self._modelData_.at[data_row] = data_value
                        
                    
                #result = np.fromstring(value, dtype=data_type)
                #self._modelData_.iloc[row] = result
                
            elif isinstance(self._modelData_, np.ndarray):
                current_value = self._modelData_[row, col]
                if hasattr(current_value, "dtype"):
                    data_type = current_value.dtype.type
                else:
                    data_type = type(current_value)
                    
                if isinstance(value, QtCore.QVariant) or hasattr(value, "value"):
                    pyvalue = value.value()
                    
                else:
                    pyvalue = value
                
                if data_type != object:
                    if isinstance(pyvalue, str):
                        if len(pyvalue.strip()) > 0:
                            data_value = pyvalue
                            
                        else:
                            data_value = None
                        
                    #else:
                data_value = data_type(data_value)
                        
                self._modelData_[row, col] = data_value
                        
                #result = np.fromstring(value, dtype=data_type)
                #self._modelData_[row, col] = result
                
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
