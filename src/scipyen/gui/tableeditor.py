# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later


"""
@author Cezar M. Tigaret
    Code solutions inspired from qtpandas (Matthias Ludwig - Datalyze Solutions) and 
    code solutions by eyllanesc on stackoverflow

NOTE: 2023-11-17 12:09:18 TODO:
copy/paste entire selection, not just row/column names ⇐ in TableEditorWidget
"""
#### BEGIN core python modules
from __future__ import print_function

import os, inspect, warnings, traceback, datetime, typing, sys
#### END core python modules

#### BEGIN 3rd party modules
import pandas as pd
import quantities as pq
#import xarray as xa
import numpy as np
import neo
from core.vigra_patches import vigra

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import Signal, Slot, Property
# from qtpy.QtCore import Signal, Slot, QEnum, Property
from qtpy.uic import loadUiType as __loadUiType__
# from PyQt5 import QtCore, QtGui, QtWidgets
# from PyQt5.QtCore import Signal, Slot, QEnum, Q_FLAGS, Property
# from PyQt5.uic import loadUiType as __loadUiType__

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
from gui.scipyenviewer import ScipyenViewer #, ScipyenFrameViewer
from gui.widgets import tableeditorwidget
from gui.widgets.tableeditorwidget import TableEditorWidget
from gui import quickdialog
# from . import resources_rc
# from . import icons_rc
#### END pict.gui modules

#### BEGIN pict.iolib modules
import iolib.pictio as pio
#### END pict.iolib modules


# NOTE: 2022-12-25 23:08:51
# needed for the new plugins framework
__scipyen_plugin__ = None

class TableEditor(ScipyenViewer):
    """Viewer/Editor for tabular data
    """
    # TODO: 2022-11-25 15:11:59
    # inherit from WorkspaceGuiMixin for messages and data I/O
    # TODO: 2019-09-09 22:40:36
    # implement plotting -- via the plots module
    sig_activated               = Signal(int)
    closeMe                     = Signal(int)
    signal_window_will_close    = Signal()
    
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
            
    @Slot(bool)
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
        
    @Slot()
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
            
    @Slot()
    def slot_resizeAllColumnsAndRowsToContents(self):
        signalBlockers = [QtCore.QSignalBlocker(v) for v in (self.tableView.horizontalHeader(), self.tableView.verticalHeader())]
        self.tableView.horizontalHeader().resizeSections(QtWidgets.QHeaderView.ResizeToContents)
        self.tableView.verticalHeader().resizeSections(QtWidgets.QHeaderView.ResizeToContents)
                
                
    @Slot()
    def slot_resizeAllColumnsToContents(self):
        signalBlockers = [QtCore.QSignalBlocker(v) for v in (self.tableView.horizontalHeader(), self.tableView.verticalHeader())]
        self.tableView.horizontalHeader().resizeSections(QtWidgets.QHeaderView.ResizeToContents)
        
    @Slot()
    def slot_resizeAllRowsToContents(self):
        signalBlockers = [QtCore.QSignalBlocker(v) for v in (self.tableView.horizontalHeader(), self.tableView.verticalHeader())]
        self.tableView.verticalHeader().resizeSections(QtWidgets.QHeaderView.ResizeToContents)
        
    @Slot()
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
        
    @Slot()
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
    
