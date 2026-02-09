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
from gui.itemmodels.roles import *
# from gui import resources_rc
# from gui import icons_rc
#### END pict.gui modules

#### BEGIN pict.iolib modules
import iolib.pictio as pio
#### END pict.iolib modules

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__ui_path__ = adapt_ui_path(__module_path__, "tableeditorwidget.ui")

__module_name__ = os.path.splitext(os.path.basename(__file__))[0]

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

    # NOTE: 2026-02-01 22:47:01
    # we NEVER store any data in the QModelIndex instances, here...

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

    def fetchMore(self, parentIndex:QtCore.QModelIndex):
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
    def data(self, modelIndex:QtCore.QModelIndex,
             role:QtCore.Qt.ItemDataRole = QtCore.Qt.DisplayRole) -> QtCore.QVariant:
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
    def flags(self, modelIndex:QtCore.QModelIndex):
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
        # print(f"{self.__class__.__name__}.setData({modelIndex}, {value}, {role})")
        # print(f"\trow: {row}, col: {col} for model data with shape {self._modelData_.shape}")

        if role not in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            return False

        # if isinstance(self._modelData_, neo.core.dataobject.DataObject):
        #
        # elif self._modelData_.ndim < 2: or col  >= self._modelData_.shape[1]:
        #     return False

        # print(f"{self.__class__.__name__}.setData: role = {role}")

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
            # print(f"{self.__class__.__name__}.setData: _setDataValue_({value}, {row}, {col}) -> OK")
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
            self._original_data_ = data

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
                # lazy display alleviates this to some degree (see self.fetchMore(…))
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
                    lbl = f"{section}"
                    if orientation == QtCore.Qt.Horizontal:
                        if isinstance(self._modelData_, pq.Quantity):
                            lbl = f"{scq.getUnitFamily(self._modelData_.units)} ({self._modelData_.units.dimensionality})"
                    return QtCore.QVariant(lbl)

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

            # print(f"{self.__class__.__name__}._setDataValue_: row={row}, col={col} -> pyvalue={pyvalue}")

            if row >= self._modelData_.shape[0]:
                return False

            if isinstance(self._modelData_, pd.DataFrame):
                self._modelData_.iloc[row, col] = pyvalue
                # self._modelData_.at[row, col] = pyvalue
                # print(f"{self.__class__.__name__}._setDataValue_: self._modelData_.iloc[{row}, {col}] -> {self._modelData_.iloc[row, col]}")
                return True
                # self._modelData_.at[data_row, data_col] = pyvalue

            elif isinstance(self._modelData_, pd.Series):
                self._modelData_.iloc[row] = pyvalue
                # self._modelData_.at[row] = pyvalue
                return True
                # self._modelData_.at[data_row] = pyvalue

            elif isinstance(self._modelData_, neo.dataobject.DataObject):
                if col >= self._modelData_.shape[1] + 1:
                    # because the signal's domain is on column 0, what is shown
                    # here has one extra column
                    return False
                if col == 0:
                    if isinstance(self._modelData_, (neo.AnalogSignal, DataSignal)) :
                        # for analog signals only t_start can be edited
                        if row == 0:
                            # allow setting t_start
                            if isinstance(pyvalue, pq.Quantity):
                                if pyvalue.units != self._modelData_.times.units:
                                    raise ValueError(f"Expecting value units of {self._modelData_.times.units}; got ({pyvalue.units}) instead")

                                self._modelData_.t_start = pyvalue
                                return True

                            elif isinstance(pyvalue, (float, int, complex)):
                                self._modelData_.t_start = pyvalue * self._modelData_.units
                                return True
                            else:
                                scipywarn(f"Expecting a float or a Quantity in {self._modelData_.times.units}; got {type(pyvalue).__name__} instead")
                                return False
                        else:
                            return False
                    else:
                        if isinstance(pyvalue, pq.Quantity):
                            if pyvalue.units != self._modelData_.times.units:
                                scipywarn(f"Expecting value units of {self._modelData_.times.units}; got ({pyvalue.units}) instead")
                                return False

                            self._modelData_.times[row] = pyvalue
                            return True

                        elif isinstance(pyvalue, (float, int, complex)):
                            self._modelData_.times[row] = pyvalue * self._modelData_.units
                            return True
                        else:
                            scipywarn(f"Expecting a float or a Quantity in {self._modelData_.times.units}; got {type(pyvalue).__name__} instead")
                            return False

                else:
                    if isinstance(pyvalue, pq.Quantity):
                        if pyvalue.units != self._modelData_.units:
                            scipywarn(f"Expecting value units of {self._modelData_.units}; got ({pyvalue.units}) instead")
                            return False

                        self._modelData_[row, col-1] = pyvalue
                        return True

                    elif isinstance(pyvalue, (float, int, complex)):
                        self._modelData_[row, col-1] = pyvalue * self._modelData_.units
                        return True
                    else:
                        scipywarn(f"Expecting a float or a Quantity in {self._modelData_.units}; got {type(pyvalue).__name__} instead")
                        return False

            elif isinstance(self._modelData_, np.ndarray):
                if self._modelData_.ndim == 1:
                    self._modelData_[row] = pyvalue
                elif self._modelData_.ndim == 2:
                    self._modelData_[row, col] = pyvalue
                if self._is_vigra_filter_kernel_:
                    self._original_data_ = vigrautils.kernelfromarray(self._modelData_)

                return True
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
