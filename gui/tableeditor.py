# -*- coding: utf-8 -*-
"""
@author Cezar M. Tigaret
    Code solutions inspired from qtpandas (Matthias Ludwig - Datalyze Solutions) and 
    code solutions by eyllanesc on stackoverflow

"""
#### BEGIN core python modules
from __future__ import print_function

import os, inspect, warnings, traceback, datetime
#### END core python modules

#### BEGIN 3rd party modules
import pandas as pd
#import xarray as xa
import numpy as np
import neo
import vigra

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__

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

from core.triggerprotocols import TriggerProtocol
from core.triggerprotocols import (TriggerEvent, TriggerEventType,)

import core.datasignal
from core.datasignal import (DataSignal, IrregularlySampledDataSignal,)

#### END pict.core modules

#### BEGIN pict.gui modules
from .scipyenviewer import ScipyenViewer #, ScipyenFrameViewer
from . import quickdialog
from . import resources_rc
#### END pict.gui modules

#### BEGIN pict.iolib modules
import iolib.pictio as pio
#### END pict.iolib modules


__module_path__ = os.path.abspath(os.path.dirname(__file__))

__module_name__ = os.path.splitext(os.path.basename(__file__))[0]

Ui_TableEditor, QMainWindow = __loadUiType__(os.path.join(__module_path__, "tableeditor.ui"))

class MetaHeaderView(QtWidgets.QHeaderView):
    #Re: How to edit Horizontal Header Item in QTableWidget, on QtCentre
    # WARNING do not use yet
    def __init__(self,orientation,parent=None):
        super(MetaHeaderView, self).__init__(orientation,parent)
        self.setMovable(True)
        self.setClickable(True)
        # This block sets up the edit line by making setting the parent
        # to the Headers Viewport.
        self.line = QtWidgets.QLineEdit(parent=self.viewport())  #Create
        self.line.setAlignment(QtCore.Qt.AlignTop) # Set the Alignmnet
        self.line.setHidden(True) # Hide it till its needed
        # This is needed because I am having a werid issue that I believe has
        # to do with it losing focus after editing is done.
        self.line.blockSignals(True)
        self.sectionedit = 0
        # Connects to double click
        self.sectionDoubleClicked.connect(self.editHeader)
        self.line.editingFinished.connect(self.doneEditing)

    def doneEditing(self):
        # This block signals needs to happen first otherwise I have lose focus
        # problems again when there are no rows
        self.line.blockSignals(True)
        self.line.setHidden(True)
        oldname = self.model().dataset.field(self.sectionedit)
        newname = str(self.line.text())
        self.model().dataset.changeFieldName(oldname, newname)
        self.line.setText('')
        self.setCurrentIndex(QtCore.QModelIndex())

    def editHeader(self,section):
        # This block sets up the geometry for the line edit
        edit_geometry = self.line.geometry()
        edit_geometry.setWidth(self.sectionSize(section))
        edit_geometry.moveLeft(self.sectionViewportPosition(section))
        self.line.setGeometry(edit_geometry)

        self.line.setText(self.model().dataset.field(section).name)
        self.line.setHidden(False) # Make it visiable
        self.line.blockSignals(False) # Let it send signals
        self.line.setFocus()
        self.line.selectAll()
        self.sectionedit = section

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
        #self._modelDataRowHeaders = None
        #self._modelDataColumnHeaders = None
        
        # NOTE: 2018-11-10 10:58:09
        # how many columns & rows are actually displayed
        #self._displayedColumns = 0
        self._displayedRows_ = 0
        
        self._viewers_ = list()
        
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
        #print("TabularDataModel data, index row: %d; col %d; role %s" % (modelIndex.row(), modelIndex.column(), role))
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
        #return self._displayedRows_
    
        #if parentIndex.isValid():
            #return 0
            
        #if self._modelData_ is None:
            #return 0
        
        #if isinstance(self._modelData_, (pd.DataFrame, pd.Series, np.ndarray)):
            #return self._modelData_.shape[0]
        
        #else:
            #return 0 #  NOTE: 2018-11-10 11:26:48 TODO nested lists ?!?
        
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
            
            if isinstance(data, np.ndarray) and data.ndim > 2:
                raise TypeError("cannot support numpy array data with more than two dimensions")
            
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
                self._modelData_ = data
                if data.ndim:
                    self._modelRows_ = data.shape[0]
                    
                    if data.ndim > 1:
                        self._modelColumns_ = data.shape[1]
                    
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
        
    @property
    def views(self):
        return self._viewers_
            
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
                    
            elif isinstance(self._modelData_, (neo.AnalogSignal, neo.IrregularlySampledSignal, DataSignal, IrregularlySampledDataSignal)):
                if orientation == QtCore.Qt.Horizontal: # horizontal (columns) header
                    if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.AccessibleTextRole):
                        if section == 0:
                            if isinstance(self._modelData_, (neo.IrregularlySampledSignal, IrregularlySampledDataSignal)):
                                return QtCore.QVariant("%s (%s)" % (self._modelData_.domain_name, self._modelData_.domain.dimensionality))
                                                       
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

            elif isinstance(self._modelData_, (neo.AnalogSignal, neo.IrregularlySampledSignal, DataSignal, IrregularlySampledDataSignal)):
                if col == 0:
                    ret = self._modelData_.times[row]
                    ret_type = type(ret).__name__
                    
                else:
                    ret = self._modelData_[row, col-1]
                    ret_type = type(ret).__name__
                    
            elif isinstance(self._modelData_, np.ndarray):
                ret = self._modelData_[row, col]
                
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
            
class TableEditor(ScipyenViewer, Ui_TableEditor):
    """Viewer/Editor for tabular data
    """
    # TODO: 2019-09-09 22:40:36
    # implement plotting -- via the plots module
    sig_activated               = pyqtSignal(int)
    closeMe                     = pyqtSignal(int)
    signal_window_will_close    = pyqtSignal()
    
    # TODO 2019-11-01 22:57:01
    # finish implementing all these
    supported_types = (pd.DataFrame, pd.Series, neo.core.baseneo.BaseNeo,
                       neo.AnalogSignal, neo.IrregularlySampledSignal,
                       neo.Epoch, neo.Event, neo.SpikeTrain,
                       DataSignal, IrregularlySampledDataSignal,
                       TriggerEvent, TriggerProtocol,
                       np.ndarray, vigra.VigraArray, vigra.filters.Kernel1D, vigra.filters.Kernel2D)
    
    view_action_name = "Table"
    
    def __init__(self, data: (object, type(None)) = None, parent: (QtWidgets.QMainWindow, type(None)) = None, 
                 pWin: (QtWidgets.QMainWindow, type(None))= None, ID:(int, type(None)) = None,
                 win_title: (str, type(None)) = None, doc_title: (str, type(None)) = None,
                 *args, **kwargs) -> None:
        super().__init__(data=data, parent=parent, pWin=pWin, win_title=win_title, doc_title = doc_title, ID=ID, *args, **kwargs) # calls _configureUI_ and loadSettings

        self.selectedColumnIndex      = None
        self.selectedRowIndex         = None
        
        # FIXME: 2019-11-10 12:51:34
        # for now all plots use matplotlib; 
        # TODO: 2019-11-10 12:51:39
        # impletement pyqtgraph plotting as alternative
        self._use_matplotlib_         = True
        
        if self._data_ is not None:
            self._viewData_()
            
            self.show()
        
    def _save_viewer_settings_(self):
        if type(self._scipyenWindow_).__name__ == "ScipyenWindow":
            self.qsettings.setValue("/".join([self.__class__.__name__, "UseMatplotlib"]), "%s" % self._use_matplotlib_)
            
    def _load_viewer_settings_(self):
        if type(self._scipyenWindow_).__name__ == "ScipyenWindow":
            use_mpl = self.qsettings.value("/".join([self.__class__.__name__, "UseMatplotlib"]), True)
            
            if isinstance(use_mpl, bool):
                self._use_matplotlib_ = use_mpl
                
            elif isinstance(use_mpl, str) and use_mpl == "True":
                self._use_matplotlib_ = True
                
            else:
                self._use_matplotlib_ = False
                
        if hasattr(self, "_use_mpl_action_"):
            self._use_mpl_action_.setChecked(self._use_matplotlib_)
            
    @pyqtSlot(bool)
    @safeWrapper
    def _slot_use_mpl_toggled_(self, value):
        self._use_matplotlib_ = value
            
    def _configureUI_(self):
        """Initializes and configures the GUI elements.
        """
        # NOTE: 2019-01-12 12:21:34
        # CAUTION: setting section resize mode policies to ResizeToContents has
        # a HUGE speed penalty for large data sets (~ 1k rows and tens of columns) 
        # A better alternative I guess is to resize ot contents AFTER the table model
        # data has been (re)loaded, or just resize manually e.g. via a menu action.
        # CAUTION
        self.setupUi(self) # initialize the GUI elements defined in the *.ui file
        #self.framesSlider.setMinimum(0)
        #self.framesSlider.setMaximum(0)
        #self.framesSlider.valueChanged.connect(self.slot_setFrameNumber)
        
        #self.framesSpinBox.setKeyboardTracking(False)
        #self.framesSpinBox.setMinimum(0)
        #self.framesSpinBox.setMaximum(0)
        #self.framesSpinBox.valueChanged.connect(self.slot_setFrameNumber)
        
        self.fileMenu = self.menuBar().addMenu("&File")
        csvExportAction = self.fileMenu.addAction("&Export As CSV...")
        csvExportAction.triggered.connect(self.slot_exportAsCSVFile)
        self.viewMenu = self.menuBar().addMenu("&View")
        resizeCandH_Action = self.viewMenu.addAction("Resize Columns And Rows to Content")
        resizeCandH_Action.triggered.connect(self.slot_resizeAllColumnsAndRowsToContents)
        
        self.plotMenu = self.menuBar().addMenu("&Plot")
        self.plotMenu.setToolTipsVisible(True)
        self.plotMenu.setToolTip("Plot selected columns")
        
        plot_Action = self.plotMenu.addAction("&Plot")
        
        plot_Action.triggered.connect(self.slot_plotSelectedColumns)
        
        # TODO see plots module
        #plot_Action_Custom = self.plotMenu.addAction("PlotCustom...")
        
        # NOTE: 2019-09-06 13:08:00
        # TODO see plots module
        #plot_Action_Custom.triggered.connect(self.slot_customPlotSelectedColumns)
        
        # NOTE: 2019-09-06 10:31:32
        # stick to matplotlib for now
        # TODO implement pyqtgraph plotting as alternative
        #self._use_mpl_action_ = self.plotMenu.addAction("&Use matplotlib")
        #self._use_mpl_action_.setCheckable(True)
        #self._use_mpl_action_.setChecked(self._use_matplotlib_)
        #self._use_mpl_action_.toggled[bool].connect(self._slot_use_mpl_toggled_)
        
        #self._dataModel_.setModelData(self._data_)
        
        self.tableView.setSortingEnabled(False)

        self._dataModel_ = TabularDataModel(parent=self)
        
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
        
        #self.tableView.itemChanged[QtWidgets.QTableWidgetItem].connect(self.slot_tableEdited, type=QtCore.Qt.QueuedConnection)
        self.toolBar = QtWidgets.QToolBar("Main", self)
        self.toolBar.setObjectName("TableEditor_Main_Toolbar")
        
        refreshAction = self.toolBar.addAction(QtGui.QIcon(":/images/view-refresh.svg"), "Refresh")
        refreshAction.triggered.connect(self.slot_refreshDataDisplay)
        
        self.addToolBar(self.toolBar)
        
    def clear(self):
        pass # what's this for? do I really need it?
    
    def _set_data_(self, data:(pd.DataFrame, pd.Series, neo.core.baseneo.BaseNeo,
                       neo.AnalogSignal, neo.IrregularlySampledSignal,
                       neo.Epoch, neo.Event, neo.SpikeTrain,
                       DataSignal, IrregularlySampledDataSignal,
                       TriggerEvent, TriggerProtocol,
                       np.ndarray, vigra.VigraArray, vigra.filters.Kernel1D, vigra.filters.Kernel2D), *args, **kwargs):
        
        if type(data) not in self.supported_types or not any([t in type(data).mro() for t in self.supported_types]):
            raise TypeError("%s cannot handle data type %s" % (type(self).__name__, type(data).__name__))
        
        if isinstance(data, np.ndarray):
            if data.ndim > 2:
                raise ValueError("Numpy arrays with more than two dimensions are not supported")
            
        self._data_ = data
        
        self._viewData_()
        
        if kwargs.get("show", True):
            self.activateWindow()
        
    def _viewData_(self):
        # TODO code for xarray.DataArray
        # TODO code to display categories for categorical data (like frame viewer in rkward)
        # FIXME what is the difference between pandas.Categorical and a series with dtype CategoricalDType?
        # NOTE: CategoricalDType is in pandas.core.dtypes.dtypes (quite deeply nested !!!)
        if self._data_ is None:
            return
        
        signalBlocker = QtCore.QSignalBlocker(self.tableView)
        
        self._dataModel_.setModelData(self._data_)
    
    @pyqtSlot()
    @safeWrapper
    def slot_exportAsCSVFile(self):
        if self._data_ is None:
            return
        
        targetDir = os.getcwd()
        
        if len(self._docTitle_.strip()):
            targetDir  = os.path.join(targetDir, 
                                 self._docTitle_) + ".csv"
            
        #print(targetDir)
        
        filePath, _ = QtWidgets.QFileDialog.getSaveFileName(self, 
                                                            caption = "Save CSV Document", 
                                                            directory = targetDir,
                                                            filter="CSV files (*.csv)")
        
        if len(filePath) > 0:
            pio.writeCsv(self._data_, filePath)
            
        QtWidgets.QApplication.setOverrideCursor(self._defaultCursor)
                        
            
    @pyqtSlot()
    def slot_resizeAllColumnsAndRowsToContents(self):
        signalBlockers = [QtCore.QSignalBlocker(v) for v in (self.tableView.horizontalHeader(), self.tableView.verticalHeader())]
        self.tableView.horizontalHeader().resizeSections(QtWidgets.QHeaderView.ResizeToContents)
        self.tableView.verticalHeader().resizeSections(QtWidgets.QHeaderView.ResizeToContents)
                
                
    @pyqtSlot()
    def slot_resizeAllColumnsToContents(self):
        signalBlockers = [QtCore.QSignalBlocker(v) for v in (self.tableView.horizontalHeader(), self.tableView.verticalHeader())]
        self.tableView.horizontalHeader().resizeSections(QtWidgets.QHeaderView.ResizeToContents)
        
    @pyqtSlot()
    def slot_resizeAllRowsToContents(self):
        signalBlockers = [QtCore.QSignalBlocker(v) for v in (self.tableView.horizontalHeader(), self.tableView.verticalHeader())]
        self.tableView.verticalHeader().resizeSections(QtWidgets.QHeaderView.ResizeToContents)
        
    @pyqtSlot()
    @safeWrapper
    def slot_plotSelectedColumns(self):
        '''Plot table selection
        NOTE: 2019-09-06 10:30:36
        We default to matplotlib plotting.
        TODO implement pyqtgraph plotting as alternative
        '''
        
        # NOTE: 2019-09-06 10:44:22
        # we need _scipyenWindow_ to expose the matplotlib figure
        #print("slot_plotSelectedColumns", type(self._scipyenWindow_).__name__)
        if type(self._scipyenWindow_).__name__ != "ScipyenWindow":
            return
        
        modelIndexes = self.tableView.selectedIndexes()
        
        self._plot_model_data_(modelIndexes, custom=False)
        
    @pyqtSlot()
    @safeWrapper
    def slot_customPlotSelectedColumns(self):
        if type(self._scipyenWindow_).__name__ != "ScipyenWindow":
            return
        
        modelIndexes = self.tableView.selectedIndexes()
        
        self._plot_model_data_(modelIndexes, custom=True)
        
        
    @safeWrapper
    def _plot_model_data_(self, modelIndexes, custom=False):
        from core.utilities import unique
        if len(modelIndexes)==0: # bail out if there is no selection
            return
        
        (ndx_k, ndx_rows, ndx_columns) = [k for k in zip(*[(k, ndx.row(), ndx.column()) for k, ndx in enumerate(modelIndexes)])]
        
        # NOTE: 2019-09-06 10:16:28
        # find out how many columns the selection spans
        selected_column_indices = unique(ndx_columns)
        
        n_columns = len(selected_column_indices)
        
        # NOTE: 2019-09-06 10:23:17
        # arrange selected model indexes by column
        
        model_index_list = list()
        
        # select model indexes by their columns => list of models with same column
        for column in selected_column_indices:
            column_index = [kc for kc, c in enumerate(ndx_columns) if c == column]
            column_model_list = [modelIndexes[ndx_k[k]] for k in column_index]
            
            sorted_column_model_list = sorted(column_model_list, key=lambda x: x.row())
            
            model_index_list.append(sorted_column_model_list)
            
        if len(model_index_list) == 0:
            return
            
        # bail out if there are different numbers of selected model indexes in different columns
        if not all([len(l) == len(model_index_list[0]) for l in model_index_list]):
            return
    
        # NOTE: 2019-09-06 10:47:17
        # generate data to plot
        column_headers = ["%s" % self._dataModel_.__getHeaderData__(k, QtCore.Qt.Horizontal).value() for k in selected_column_indices]
        
        data = list()
        
        nan = np.nan
        
        for l in model_index_list:
            column_data = np.array([str2float("%s" % self._dataModel_.__getModelData__(ndx.row(), ndx.column()).value()) for ndx in l], dtype="float64")
            
            data.append(column_data)
            
        #fig = self._scipyenWindow_._newMatplotLibFigure()
        #fig = self._scipyenWindow_.__register_viewer_window__(fig, name=self._docTitle_)
        
        # TODO: 2019-11-10 12:53:50
        # implement plotting with pyqtgraph
        if self._use_matplotlib_:
            fig = self._scipyenWindow_._newViewer(mpl.figure.Figure)
            
            plt.figure(fig.number) # make this the current figure
            
            if len(data) == 1:
                #plot_data = data[0]
                plt.plot(data[0])
                plt.gca().set_ylabel(column_headers[0])
                
            else:
                if custom:
                    pass # TODO
                else:
                    plot_data = np.concatenate([np.atleast_2d(d).T for d in data], axis=1)
                
                    lines = plt.plot(plot_data)
            
    @property
    def useMatplotlib(self):
        return self._use_matplotlib_
    
    @useMatplotlib.setter
    def useMatplotlib(self, value):
        if not isinstance(value, bool):
            raise TypeError("Expecting a bool scalar; got %s instead" % type(value).__name__)
        
        self._use_matplotlib_ = value
    
    @pyqtSlot(QtCore.QPoint)
    @safeWrapper
    def slot_table_context_menu_requested(self, pos):
        #print("table_context_menu at pos %s" % pos)
        
        cm = QtWidgets.QMenu("Cell menu", self.tableView)
        copySelectedAction = cm.addAction("Copy")
        
        copySelectedAction.triggered.connect(self.slot_copySelection)

        cm.popup(self.tableView.mapToGlobal(pos), copySelectedAction)

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
        
    #@pyqtSlot()
    #@safeWrapper
    #def slot_refreshDataDisplay(self):
        #"""Overriden due to special identity tests for pandas objects and numpy arrays
        #"""
        #if isinstance(self._data_, (pd.DataFrame, pd.Series, np.ndarray)):
            #workspace_data = [x for x in self._scipyenWindow_.workspace.values() if type(x) is type(self._data_)]
            
            #if isinstance(self._data_, np.ndarray):
                #if not any([np.array_equal(self._data_, x) for x in workspace_data]):
                    
            
    
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
            
        
