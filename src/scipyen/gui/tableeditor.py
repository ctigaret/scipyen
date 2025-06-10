# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later


r"""
@author Cezar M. Tigaret
    Code solutions inspired from qtpandas (Matthias Ludwig - Datalyze Solutions) and 
    code solutions by eyllanesc on stackoverflow

NOTE: 2023-11-17 12:09:18 TODO:
copy/paste entire selection, not just row/column names ⇐ in TableEditorWidget
"""
#### BEGIN core python modules
from __future__ import print_function

import os, inspect, warnings, traceback, datetime, typing, sys
from functools import (singledispatch, singledispatchmethod)

#### END core python modules

#### BEGIN 3rd party modules
import pandas as pd
import quantities as pq
#import xarray as xa
import numpy as np
import neo
from core.vigra_patches import vigra

import qtpy
qtpy.API = os.environ["QT_API"]
if os.environ["QT_API"] == "pyside6":
    import PySide6
    from PySide6 import QtCore, QtGui, QtWidgets
    from PySide6.QtCore import Signal, Slot, Property
else:
    from qtpy import QtCore, QtGui, QtWidgets
    from qtpy.QtCore import Signal, Slot, Property

from qtpy.uic import loadUiType as __loadUiType__

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

from core.prog import (safewrapper, )

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
    r"""Viewer/Editor for tabular data
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
        self.toolBar.setMovable(False)
        self.toolBar.setVisible(True)
            
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
    @safewrapper
    def _slot_use_mpl_toggled_(self, value):
        self._use_matplotlib_ = value
            
    def _configureUI_(self):
        r"""Initializes and configures the GUI elements.
        """
        # NOTE: 2019-01-12 12:21:34
        # CAUTION: setting section resize mode policies to ResizeToContents has
        # a HUGE speed penalty for large data sets (~ 1k rows and tens of columns) 
        # A better alternative I guess is to resize to contents AFTER the table model
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
        self.plotMenu.setToolTip("Plot selected data")
        
        plot_Action = self.plotMenu.addAction("&Plot")
        
        plot_Action.triggered.connect(self.slot_plotSelectedData)
        
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
        
        plotDataAction = self.toolBar.addAction(QtGui.QIcon.fromTheme("labplot-xy-curve-segments"), "Plot Selected Data")
        plotDataAction.triggered.connect(self.slot_plotSelectedData)
        
        self.addToolBar(self.toolBar)
        self.toolBar.setVisible(True)
        self.toolBar.setMovable(False)
        
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
        
        if kwargs.get("show", True): # ??? won't work in wayland anyway
            self.activateWindow()
        
    def _viewData_(self):
        r"""Populates the tableWidget (a tableeditorwidget.TableEditorWidget).
        In turn, the tableWidget uses tableeditorwidget.TabularDataModel"""
        # TODO code for xarray.DataArray
        # TODO code to display categories for categorical data (like frame viewer in rkward)
        # FIXME what is the difference between pandas.Categorical and a series with dtype CategoricalDType?
        # NOTE: CategoricalDType is in pandas.core.dtypes.dtypes (quite deeply nested !!!)
        if self._data_ is None:
            return
        
        signalBlocker = QtCore.QSignalBlocker(self.tableView)
        
        self.tableWidget.setData(self._data_)
        
    @Slot()
    @safewrapper
    def slot_exportAsCSVFile(self):
        if self._data_ is None:
            return
        
        targetDir = os.getcwd()
        
        if len(self._docTitle_.strip()):
            targetDir  = os.path.join(targetDir, 
                                 self._docTitle_) + ".csv"
            
        if sys.platform.startswith("win32"):
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
    @safewrapper
    def slot_plotSelectedData(self):
        '''Plot table selection
        NOTE: 2019-09-06 10:30:36
        We default to matplotlib plotting.
        TODO implement pyqtgraph plotting as alternative
        '''
        
        # NOTE: 2019-09-06 10:44:22
        # we need _scipyenWindow_ to expose the matplotlib figure
        #print("slot_plotSelectedData", type(self._scipyenWindow_).__name__)
        if type(self._scipyenWindow_).__name__ != "ScipyenWindow":
            return
        
        modelIndexes = self.tableView.selectedIndexes()
        
        self.plotData()
        # self.plotData(modelIndexes, custom=False)
        
    # ### BEGIN don't delete yet
#     @Slot()
#     @safewrapper
#     def slot_customPlotSelectedColumns(self):
#         if type(self._scipyenWindow_).__name__ != "ScipyenWindow":
#             return
#         
#         modelIndexes = self.tableView.selectedIndexes()
#         
#         self.plotData(modelIndexes, custom=True)
    # ### END   don't delete yet
        
        
    @safewrapper
    def plotData(self, *args, **kwargs):
        r"""Plots selected data.
        
        For sparse selections, the selected cells are grouped by their column 
        index, creating as many 1D data vectors as the number of selected column
        indexes. These vectors are then plotted individually in the same plot window.
        
        This method uses matplotlib.pyplot interface.
        
        When called from the TableEditor menu, the function will generate plots
        using the pyplot default (line, no markers, default color palette, etc).
        
        For custom plot appearances you may either:
        1) call this method directly, passing options as *args and **kwargs
        2) call this method via the GUI ("Plot" menuitem), then use the tools of
        the newly shown matplotlib Figure tools to customize the plot.
        3) retrieve the selected data by calling getSelectedData() then use your
        own code to plot it.
        
        For full-column selection(s) each selected column supplies one data vector.
        These vectors are then plotted individually in the same plot window.
        
        The functions behaves in a way specific to the type of data shown in the
        table:
        
        • pandas DataFrame or Series:
            the domain of the plotted curves is taken from the index of the
            DataFrame or Series. NOTE: the index is shown as the vertical (row)
            header of the table.
        
        • neo DataObject, including BaseSignal
            the (usually, time) domain of the object is always shown in the first
            column of the table (column 0, the left-most), with higher index
            columns showing the signal's 'channels'.
        
            Selecting anything in column 0 will plot a data vector containing the 
            selected values, against their index in the column 0. 
    
            Selecting anything in columns with higher index will plot the selected
            values against the data in column 0 at the selected rows.
        
        • numpy array
            Generic array data is considered to contain column vectors, with the 
            domain being represented by the index of the data element in the column
            vector.
        
            Any selected data will be grouped per column index as above and plotted
            against the index of the data.
        
        NOTE: vigra filter kernels (1D, 2D) are first converted to numpy array
        before being used as model data for the table editor.
        
        NOTE: VigraArray are numpy arrays; for simplicity, the table editor does
        not currently take into account any AxisInfo objects associated with the 
        array. I might revisit this in the near future.
        
        """
        from core.prog import scipywarn
        from core import scipyen_quantities as scq
        
        data, column_headers = self.getSelectedData()
        
        if not isinstance(data, list) or len(data) == 0:
            scipywarn("Nothing to plot")
            return
        
        if len(data) != len(column_headers):
            scipywarn("Mistmatch between number of data vectors to plot and column headers")
            return
        
        # TODO: 2019-11-10 12:53:50
        # implement plotting with pyqtgraph
        if self._use_matplotlib_:
            fig = self._scipyenWindow_.newViewer(mpl.figure.Figure)
            
            plt.figure(fig.number) # make this the current figure
            
            if len(data) == 1:
                plt.plot(data[0][0], data[0][1], label=column_headers[0], *args, **kwargs)
                ylabel = column_headers[0]
                if isinstance(data[0][1], pq.Quantity):
                    ylabel += f" ({data[0][1].units.dimensionality})"
                    
                if isinstance(data[0][0], pq.Quantity):
                    xlabel = f"{scq.getUnitFamily(data[0][0].units)} ({data[0][0].units.dimensionality})"
                else:
                    xlabel = ""
                plt.gca().set_ylabel(ylabel)
                if len(xlabel.strip()):
                    plt.gca().set_xlabel(xlabel)
                
            else:
                data_units = list()
                multiple_data_units = False
                domain_units = list()
                multiple_domain_units = False
                
                for k,d in enumerate(data):
                    if isinstance(d[0], pq.Quantity):
                        domain_units.append(d[0].units)
                    else:
                        multiple_domain_units = True
                        domain_units.append(None)
                        
                    if isinstance(d[1], pq.Quantity):
                        data_units.append(d[1].units)
                    else:
                        data_units.append(None)
                        
                    if any(u is None for u in domain_units) or not all(scq.unitsConvertible(u, domain_units[0]) for u in domain_units):
                        xlabel = ""
                        domain_data = d[0]
                    else:
                        if isinstance(d[0], pq.Quantity):
                            domain_data = d[0].rescale(domain_units[0])
                        else:
                            domain_data = d[0]
                        xlabel = f"{scq.getUnitFamily(domain_units[0])} ({domain_units[0].dimensionality})"
                            
                    if any(u is None for u in data_units) or not all(scq.unitsConvertible(u, data_units[0]) for u in data_units):
                        ylabel = ""
                        column_data = d[1]
                    else:
                        if isinstance(d[1], pq.Quantity):
                            column_data = d[1].rescale(data_units[0])
                        else:
                            column_data = d[1]
                        ylabel = f"{scq.getUnitFamily(data_units[0])} ({data_units[0].dimensionality})"
                            
                    
                    plt.plot(domain_data, column_data, label=column_headers[k], *args, *kwargs)
                        
                plt.legend()
                
        else:
            scipywarn("Only matplotlib backend is supported, currently. Please set useMatplotlib to True.")
                        
    def getSelectedData(self) -> tuple:
        r"""Retrieves the selected data in the table.
        Returns a two lists:
        • 'data': a list of tuples of the form (x, y) where x and y are column vectors
        • 'column_headers': a list of str objects, one for each tuple in 'data'
        
        See documentation of plotData for what is returned, based on the selection.
        
        """
        
        # NOTE: 2025-03-31 23:21:51
        # model data can only be a pandas DataFrame, Series, or numpy 2D array
        # vigra filter kernels are converted to numpy arrays in the editor widget
        # from core.utilities import unique
        modelIndexes = self.tableView.selectedIndexes()
        if len(modelIndexes)==0: # bail out if there is no selection
            return list(), list()
        
        sourceData = self._dataModel_.sourceData
        
        if sourceData is None:
            return list(), list()

        data = list()
        
        # except for np.ndarray, the data is organized in columns, by definition,
        # for DataFrames an Series.
        # we implicitly extend this rule to np.ndarrays, to KISS
        #
        # iterate by column, the by row in each column
        ndx_rows_cols = tuple(map(lambda ndx: (ndx.row(), ndx.column()), modelIndexes))
        selected_columns_ordered = np.array(list(map(lambda x: x[1], sorted(ndx_rows_cols, key = lambda x: x[1]))))
        u_sel_cols = np.unique(selected_columns_ordered)
        
        if isinstance(sourceData, (pd.DataFrame, pd.Series)):
            column_headers = list(sourceData.columns[u_sel_cols])
        else:
            if isinstance(sourceData, neo.core.dataobject.DataObject):
                obj_name = getattr(sourceData, "name", "signal")
                array_annotations = getattr(sourceData, "array_annotations", dict())
                # careful here! signals are plotted with time (domain) values in column 0 and "channels" in columns 1 -> ...
                if 0 in u_sel_cols:
                    if u_sel_cols.size > 1:
                        data_cols = list(filter(lambda x: x!=0, u_sel_cols))
                        if len(array_annotations):
                            column_headers = list(map(lambda x: f"{obj_name} channel {sourceData.array_annotations_at_index(x-1)['channel_names']}", data_cols))
                        else:
                            column_headers = list(map(lambda x: f"{obj_name} channel {x-1}", data_cols))
                    else: # times column selected
                        column_headers = [self._dataModel_.__getHeaderData__(0, QtCore.Qt.Horizontal).value()]
                else:
                    if len(array_annotations):
                        column_headers = list(map(lambda x: f"{obj_name} channel {sourceData.array_annotations_at_index(x-1)['channel_names']}", u_sel_cols))
                    else:
                        column_headers = list(map(lambda x: f"{obj_name} channel {x-1}", u_sel_cols))
            else:
                column_headers = list(map(lambda x: f"column {x}", u_sel_cols))
        
        for column in u_sel_cols:
            # collect all model indexes for a given column
            # NOTE: only DataFrame and 2D numpy arrays can have more than one column!
            indexes_for_column = tuple(filter(lambda ndx: ndx.column() == column, modelIndexes))
            if len(indexes_for_column) == 0:
                continue # should never happem
            
            # order them by row
            selected_rows_for_column = np.array(list(map(lambda x: x.row(), sorted(indexes_for_column, key = lambda x: x.row()))))
            
            # are there any duplicates? how is this relevant?
            # by definition one cannot have duplicate rows in the same columns
            # u_sel_rows = np.unique(selected_rows_for_column)
            # has_duplicate_rows = u_sel_rows.size < selected_rows_for_column.size
            
            if np.all(np.ediff1d(selected_rows_for_column) == 1):
                # contiguous selection with respect to rows, within this particular column
                start, stop = np.min(selected_rows_for_column), np.max(selected_rows_for_column)
                
                if isinstance(sourceData, (pd.DataFrame, pd.Series)):
                    dd = sourceData.iloc[start:stop+1, column]
                    data.append((dd.index, dd)) # NOTE include the row index
                    
                else:#elif isinstance(sourceData,  np.ndarray):
                    # x = np.atleast_2d(np.arange(0, sourceData.shape[0])[start:stop+1]).T
                    # data.append((x, np.atleast_2d(sourceData[start:stop+1, column]).T))# NOTE include the row index
                    if isinstance(sourceData, neo.core.dataobject.DataObject):
                        if column == 0:
                            if len(u_sel_cols) > 1:
                                continue
                            x = np.atleast_2d(np.arange(0, sourceData.shape[0])[start:stop+1]).T
                            y = np.atleast_2d(sourceData.times[start:stop+1]).T
                            # print(f"x.shape: {x.shape}, y.shape: {y.shape}")
                            
                            data.append((x, y))
                        else:
                            x = np.atleast_2d(sourceData.times[start:stop+1]).T
                            y = np.atleast_2d(sourceData[start:stop+1, column-1])
                            # print(f"x.shape: {x.shape}, y.shape: {y.shape}")
                            data.append((x, y))
                    else:
                        x = np.atleast_2d(np.arange(0, sourceData.shape[0])[start:stop+1]).T
                        y = np.atleast_2d(sourceData[start:stop+1, column])
                        # print(f"x.shape: {x.shape}, y.shape: {y.shape}")
                        data.append((x, y))
                
            else: # sparse selection
                if isinstance(sourceData, (pd.DataFrame, pd.Series)):
                    data.append(sourceData.iloc[selected_rows_for_column, column]) # NOTE this will include the row index
                else:#elif isinstance(sourceData,  np.ndarray):
                    if isinstance(sourceData, neo.core.dataobject.DataObject):
                        if column == 0:
                            x = np.atleast_2d(selected_rows_for_column).T
                            y = np.atleast_2d(sourceData.times[selected_rows_for_column]).T
                            # print(f"x.shape: {x.shape}, y.shape: {y.shape}")
                            
                            data.append((x, y))
                        else:
                            x = np.atleast_2d(sourceData.times[selected_rows_for_column]).T # this is a quantity array
                            y = np.atleast_2d(np.array(list(map(lambda k: sourceData[k, column-1], selected_rows_for_column)))).T * sourceData[:,column-1].units
                            # print(f"x.shape: {x.shape}, y.shape: {y.shape}")
                            data.append((x, y))
                    else:
                        x = np.atleast_2d(selected_rows_for_column).T
                        y = np.atleast_2d(sourceData[selected_rows_for_column, column])
                        # print(f"x.shape: {x.shape}, y.shape: {y.shape}")
                        data.append((x, y))
                    
        return data, column_headers
                        
    @property
    def useMatplotlib(self):
        return self._use_matplotlib_
    
    @useMatplotlib.setter
    def useMatplotlib(self, value):
        if not isinstance(value, bool):
            raise TypeError("Expecting a bool scalar; got %s instead" % type(value).__name__)
        
        self._use_matplotlib_ = value
    
