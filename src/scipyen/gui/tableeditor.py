# -*- coding: utf-8 -*-
"""
@author Cezar M. Tigaret
    Code solutions inspired from qtpandas (Matthias Ludwig - Datalyze Solutions) and 
    code solutions by eyllanesc on stackoverflow

"""
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
import core.datatypes  

import core.strutils as strutils
from core.strutils import str2float

from core.prog import (safeWrapper, )

from core.triggerevent import (DataMark, MarkType, TriggerEvent, TriggerEventType)
from core.triggerprotocols import TriggerProtocol
from core.datazone import DataZone

import core.datasignal
from core.datasignal import (DataSignal, IrregularlySampledDataSignal,)
from core.datatypes import array_slice

from core.sysutils import adapt_ui_path

#### END pict.core modules

#### BEGIN pict.gui modules
from .scipyenviewer import ScipyenViewer #, ScipyenFrameViewer
from gui.widgets import tableeditorwidget
from gui.widgets.tableeditorwidget import TableEditorWidget
from . import quickdialog
from . import resources_rc
#### END pict.gui modules

#### BEGIN pict.iolib modules
import iolib.pictio as pio
#### END pict.iolib modules


# NOTE: 2022-12-25 23:08:51
# needed for the new plugins framework
__scipyen_plugin__ = None

# __module_path__ = os.path.abspath(os.path.dirname(__file__))
# 
# __module_name__ = os.path.splitext(os.path.basename(__file__))[0]
# 
# __ui_path__ = adapt_ui_path(__module_path__, "tableeditor.ui")
# 
# Ui_TableEditor, QMainWindow = __loadUiType__(__ui_path__)
# Ui_TableEditor, QMainWindow = __loadUiType__(os.path.join(__module_path__, "tableeditor.ui"))
# Ui_TableEditorWidget, QWidget = __loadUiType__(os.path.join(__module_path__, "widgets","tableeditorwidget.ui"))

class TableEditor(ScipyenViewer):#, Ui_TableEditor):
    """Viewer/Editor for tabular data
    """
    # TODO: 2022-11-25 15:11:59
    # inherit from WorkspaceGuiMixin for messages and data I/O
    # TODO: 2019-09-09 22:40:36
    # implement plotting -- via the plots module
    sig_activated               = pyqtSignal(int)
    closeMe                     = pyqtSignal(int)
    signal_window_will_close    = pyqtSignal()
    
    # TODO 2019-11-01 22:57:01
    # finish implementing all these
    viewer_for_types = {pd.DataFrame: 99, 
                        pd.Series: 99, 
                        pd.Index: 99,
                        neo.AnalogSignal: 0, 
                        neo.IrregularlySampledSignal: 0,
                        neo.Epoch: 0, 
                        neo.Event: 0,
                        neo.SpikeTrain: 0,
                        DataSignal: 0, 
                        IrregularlySampledDataSignal: 0,
                        DataMark: 0,
                        DataZone: 0,
                        TriggerEvent: 0, 
                        TriggerProtocol: 0,
                        np.ndarray: 0, 
                        vigra.VigraArray: 0, 
                        vigra.filters.Kernel1D: 0,
                        vigra.filters.Kernel2D: 0}
    
    # view_action_name = "Table"
    
    def __init__(self, data: (object, type(None)) = None, 
                 parent: (QtWidgets.QMainWindow, type(None)) = None, 
                 ID:(int, type(None)) = None,
                 win_title: (str, type(None)) = None, doc_title: (str, type(None)) = None,
                 *args, **kwargs) -> None:
        super().__init__(data=data, parent=parent, win_title=win_title, doc_title = doc_title, ID=ID, *args, **kwargs) # calls _configureUI_ and loadSettings

        #self.tableWidget = TableEditorWidget()
        #self.setCentralWidget(self.tableWidget)
        
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
        
        self.fileMenu = self.menuBar().addMenu("&File")
        csvExportAction = self.fileMenu.addAction("&Save As CSV...")
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
        
        self.tableWidget = TableEditorWidget(parent=self)
        self._dataModel_ = self.tableWidget._dataModel_
        
        self.setCentralWidget(self.tableWidget)
        self.tableView = self.tableWidget.tableView
        
        ## NOTE: 2018-11-28 21:46:18
        ## WARNING HUGE speed penalty when using ResizeToContents policy, for large
        ## data sets (~1k rows and tens of columns)
        ##self.tableView.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        ##self.tableView.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        ## NOTE: 2018-11-29 23:15:13
        ## you may play with this by also setting the precision to be based only
        ## on what is actually visible:
        #self.tableView.horizontalHeader().setResizeContentsPrecision(0) 
        
        #self.tableView.horizontalHeader().setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        #self.tableView.horizontalHeader().customContextMenuRequested[QtCore.QPoint].connect(self.slot_horizontal_header_context_menu_request)
        
        #self.tableView.verticalHeader().setSectionsMovable(False)
        
        self.toolBar = QtWidgets.QToolBar("Main", self)
        self.toolBar.setObjectName("TableEditor_Main_Toolbar")
        
        refreshAction = self.toolBar.addAction(QtGui.QIcon.fromTheme("view-refresh"), "Refresh")
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
        
        if type(data) not in self.viewer_for_types or not any([t in type(data).mro() for t in self.viewer_for_types]):
            raise TypeError("%s cannot handle data type %s" % (type(self).__name__, type(data).__name__))
        
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
        
        self.tableWidget.setData(self._data_)
        
    @pyqtSlot()
    @safeWrapper
    def slot_exportAsCSVFile(self):
        if self._data_ is None:
            return
        
        targetDir = os.getcwd()
        
        if len(self._docTitle_.strip()):
            targetDir  = os.path.join(targetDir, 
                                 self._docTitle_) + ".csv"
            
        if sys.platform == "win32":
            options = QtWidgets.QFileDialog.Option.DontUseNativeDialog
            kw = {"options":options}
        else:
            kw = {}

        filePath, _ = QtWidgets.QFileDialog.getSaveFileName(self,
                                                            caption = "Save CSV Document", 
                                                            directory = targetDir,
                                                            filter="CSV files (*.csv)",
                                                            **kw)
        
        if len(filePath) > 0:
            pio.writeCsv(self._data_, filePath)
            
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
    
    #@pyqtSlot(QtCore.QPoint)
    #@safeWrapper
    #def slot_table_context_menu_requested(self, pos):
        ##print("table_context_menu at pos %s" % pos)
        
        #cm = QtWidgets.QMenu("Cell menu", self.tableView)
        #copySelectedAction = cm.addAction("Copy")
        
        #copySelectedAction.triggered.connect(self.slot_copySelection)

        #cm.popup(self.tableView.mapToGlobal(pos), copySelectedAction)

    #@pyqtSlot()
    #@safeWrapper
    #def slot_copySelection(self):
        #modelIndexes = self.tableView.selectedIndexes()
        #selected_text = list()
        #previous = modelIndexes[0]
        ##selected_text.append(self._dataModel_.data(previous).toString())
        #selected_text.append(str(self._dataModel_.data(previous).value()))
        
        #for modelIndex in modelIndexes[1:]:
            ##data = self._dataModel_.data(modelIndex).toString()
            #data = str(self._dataModel_.data(modelIndex).value())
            #if modelIndex.row() != previous.row():
                #selected_text.append("\n")
                
            #elif modelIndex.column() != previous.column():
                #selected_text.append("\t")
            
            #selected_text.append(data)
            
            #previous = modelIndex
            
        #QtGui.QGuiApplication.clipboard().setText("".join(selected_text))
    
    #@pyqtSlot()
    #@safeWrapper
    #def slot_resizeSelectedColumnsToContents(self):
        #if not isinstance(self.selectedColumnIndex, int):
            #return
        
        #signalBlocker = QtCore.QSignalBlocker(self.tableView.horizontalHeader())
        
        #if len(self.tableView.selectionModel().selectedColumns()) > 1:
            #col_indices = [ndx.column() for ndx in self.tableView.selectionModel().selectedColumns()]
            
            #for ndx in col_indices:
                #sizeHint = max([self.tableView.sizeHintForColumn(ndx), self.tableView.horizontalHeader().sectionSizeHint(ndx)])
                ##sizeHint = self.tableView.horizontalHeader().sectionSizeHint(ndx)
                #self.tableView.horizontalHeader().resizeSection(ndx, sizeHint)
                
        #else:
            #sizeHint = max([self.tableView.sizeHintForColumn(self.selectedColumnIndex), self.tableView.horizontalHeader().sectionSizeHint(self.selectedColumnIndex)])
            ##sizeHint = self.tableView.horizontalHeader().sectionSizeHint(self.selectedColumnIndex)
            #self.tableView.horizontalHeader().resizeSection(self.selectedColumnIndex, sizeHint)
        
        
    #@pyqtSlot()
    #@safeWrapper
    #def slot_resizeSelectedRowsToContents(self):
        #if not isinstance(self.selectedRowIndex, int):
            #return
        
        #signalBlocker = QtCore.QSignalBlocker(self.tableView.verticalHeader())
        
        #if len(self.tableView.selectionModel().selectedRows()) > 1:
            #row_indices = [ndx.row() for ndx in self.tableView.selectionModel().selectedColumns()]
            
            #for ndx in row_indices:
                #sizeHint = max([self.tableView.sizeHintForRow(ndx), self.tableView.verticalHeader().sectionSizeHint(ndx)])
                ##sizeHint = self.tableView.horizontalHeader().sectionSizeHint(ndx)
                #self.tableView.verticalHeader().resizeSection(ndx, sizeHint)
                
        #else:
            #sizeHint = max([self.tableView.sizeHintForRow(self.selectedRowIndex), self.tableView.verticalHeader().sectionSizeHint(self.selectedRowIndex)])
            ##sizeHint = self.tableView.horizontalHeader().sectionSizeHint(self.selectedColumnIndex)
            #self.tableView.verticalHeader().resizeSection(self.selectedRowIndex, sizeHint)
        
        
    #@pyqtSlot(QtCore.QPoint)
    #@safeWrapper
    #def slot_horizontal_header_context_menu_request(self, pos):
        ##print("horizontal header context menu at pos %s" % pos)
        ##print("clicked column %s" % self.tableView.columnAt(pos.x()))
        
        #self.selectedColumnIndex = self.tableView.columnAt(pos.x())
        
        #cm = QtWidgets.QMenu("Column Menu", self.tableView)
        #copyColumnTitleAction = cm.addAction("Copy column name")
        #copyColumnTitleAction.triggered.connect(self.slot_copyColumnName)
        
        #resizeColumnToContentsAction = cm.addAction("Resize to contents")
        #resizeColumnToContentsAction.triggered.connect(self.slot_resizeSelectedColumnsToContents)
        
        #resizeAllColumsToContextAction = cm.addAction("Resize All Columns To Contents")
        
        #resizeAllColumsToContextAction.triggered.connect(self.slot_resizeAllColumnsToContents)
        ##copyColumnContents = cm.addAction("Copy column data")
        
        #cm.exec(self.tableView.mapToGlobal(pos))
        
    
    #@pyqtSlot(QtCore.QPoint)
    #@safeWrapper
    #def slot_vertical_header_context_menu_request(self, pos):
        #self.selectedRowIndex = self.tableView.rowAt(pos.x())
        
        #cm = QtWidgets.QMenu("Row Menu", self.tableView)
        #copyColumnTitleAction = cm.addAction("Copy row name")
        #copyColumnTitleAction.triggered.connect(self.slot_copyRowName)
        
        #resizeRowToContentsAction = cm.addAction("Resize to contents")
        #resizeRowToContentsAction.triggered.connect(self.slot_resizeSelectedRowsToContents)
        
        #resizeAllRowsToContextAction = cm.addAction("Resize All Rows To Contents")
        
        #resizeAllRowsToContextAction.triggered.connect(self.slot_resizeAllRowsToContents)
        
        #cm.exec(self.tableView.mapToGlobal(pos))
        
    #@pyqtSlot()
    #@safeWrapper
    #def slot_copyColumnName(self):
        #if not isinstance(self.selectedColumnIndex, int):
            #return
        
        ##columnName = self.tableView.horizontalHeaderItem(self.selectedColumnIndex).text()
        
        ## NOTE: 2018-11-28 23:38:29
        ## this is a QtCore.QVariant that wraps a python str
        #columnName = self.tableView.model().headerData(self.selectedColumnIndex, QtCore.Qt.Horizontal).value()
        
        #QtWidgets.QApplication.instance().clipboard().setText(columnName)
        
    #@pyqtSlot()
    #@safeWrapper
    #def slot_copyRowName(self):
        #if not isinstance(self.selectedRowIndex, int):
            #return
        
        #rowName = self.tableView.verticalheaderItem(self.selectedRowIndex).text()
        
        #QtWidgets.QApplication.instance().clipboard().setText(rowName)
        

    #@pyqtSlot(QtWidgets.QTableWidgetItem)
    #@safeWrapper
    #def slot_tableEdited(self, item):
        ## TODO code for xarray.DataArray
        ## TODO code for multi-indexed pandas data frames
        ## TODO code for as_type(...) for pandas data -- e.g. categorical
        #col = item.column()
        #row = item.row()
        #value = item.text()
        
        #if isinstance(self._data_, pd.DataFrame):
            #colHeaderText = self.tableView.horizontalHeaderItem(col).text()
            
            #if colHeaderText not in self._data_.columns:
                #raise RuntimeError("%s not found in data columns!" % colHeaderText)
            
            #columnDType = self._data_[colHeaderText].dtype
            
            #if np.can_cast(eval(value), columnDType):
                #if columnDType == np.dtype("bool"):
                    #if value.lower().strip() in ("true, t, 1"):
                        #value = "True"
                        
                    #elif value.lower().strip() in ("false, f, 0"):
                        #value = False
                        
                ## CAUTION here
                #data_value = np.array(eval(value), dtype=columnDType)
                
                #self._data_.loc[self._data_.index[row], colHeaderText] = data_value
                
            #else:
                #raise RuntimeError("cannot cast %s to %s" % (value, columnDType))
            
            
        #elif isinstance(self._data_, pd.Series):
            #dataDType = self._data_.dtype
            
            #if np.can_cast(eval(value), dataDType):
                #data_value = np.array(eval(value), dtype=dataDType)
            
                #self._data_.loc[self._data_.index[row]] = data_value
            
        #elif isinstance(self._data_, np.ndarray):
            #dataDType = self._data_.dtype
            
            #if np.can_cast(eval(value), dataDType):
                #data_value = np.array(eval(value), dtype=dataDType)
                
                #if self._data_.ndim == 3:
                    #self._data_[row,col,self.frameNo] = data_value
                    
                #elif self._data_.ndim == 2:
                    #self._data_[row,col] = data_value
                    
                #elif self._data_.ndim == 1:
                    #self._data_[row] = data_value
           
            #else:
                #raise RuntimeError("cannot cast %s to %s" % (value, dataDType))
            
        
