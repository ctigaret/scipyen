# -*- coding: utf-8 -*-
# $Id: tabulardatamodel.py $
# SPDX-FileCopyrightText: 2023 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""Table model, for tabular-like data
"""


#### BEGIN core python modules
from __future__ import print_function

import os, inspect, warnings, traceback, datetime, typing, types, numbers, enum # noqa
from functools import (singledispatch, singledispatchmethod) # noqa
from collections import deque
import dataclasses
#### END core python modules

#### BEGIN 3rd party modules
import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, ) # noqa
from qtpy.QtCore import (Signal, Slot, Property,) # noqa
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6
    from PySide6 import Shiboken # noqa
    # from PySide6.QtCore import (Signal, Slot, Property,)
    from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True

    from qtpy import sip
    from qtpy.uic import loadUiType # noqa
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True


import pandas as pd
import quantities as pq
#import xarray as xa
import numpy as np
import neo
from neo.core.objectlist import ObjectList as NeoObjectList
from core.vigra_patches import vigra
from imaging import vigrautils

import matplotlib as mpl # noqa
import matplotlib.pyplot as plt # noqa
import matplotlib.pylab as plb # noqa
import matplotlib.mlab as mlb # noqa
#### END 3rd party modules

#### BEGIN pict.core modules
#from core.patchneo import *
from core import datatypes

import core.utilities as utilities # noqa
import core.strutils as strutils # noqa
from core.strutils import str2float # noqa

from core.prog import (safewrapper, scipywarn)

from core.triggerevent import (DataMark, MarkType, TriggerEvent, TriggerEventType) # noqa
from core.marktrain import MarkTrain
from core.triggerprotocols import (TriggerProtocol, TriggerProtocolList) # noqa
from core.datazone import DataZone

import core.datasignal # noqa
from core.datasignal import (DataSignal, IrregularlySampledDataSignal,) # noqa
import core.datatypes as dt
from core.datatypes import array_slice # noqa
from core.sysutils import adapt_ui_path # noqa
from core import scipyen_quantities as scq
from core import neoutils # noqa
from ephys import (ephys, ephys_pathways)

#### END pict.core modules

#### BEGIN pict.gui modules
from gui.delegates import PythonItemDelegate # noqa
from gui.itemmodels.roles import * # noqa
#### END pict.gui modules

#### BEGIN pict.iolib modules
# import iolib.pictio as pio
#### END pict.iolib modules

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
    sig_modelPopulated = Signal(name="sig_modelPopulated")

    def __init__(self, data=None, parent=None):
        super(TabularDataModel, self).__init__(parent=parent)

        self._is_vigra_filter_kernel_:bool = False
        self._original_data_:typing.Any = None
        self._modelData_:typing.Any= None
        self._modelDataRows_:int = 0
        self._modelDataRowIndexName_: str | None = None
        # self._modelDataRowIndexName_: str = "Index"
        self._modelDataColumns_:int = 0
        self._modelDataColumnHeaders_: typing.Optional[
            typing.Union[typing.Mapping, typing.Sequence]
            ] = None
        self._immutability_:dict = {"columns": list(), "rows": list(), "joint":False}
        self._rowBatchSize_:int = 10
        self._columnBatchSize_:int = 10
        self._canAddRemoveRows_:bool = False
        self._canAddRemoveColumns_:bool = False

        # NOTE: 2026-06-07 10:58:03
        # flag showing if editing an object externally is allowed
        #
        self._useExternalDataEditor_: bool = False

        # NOTE: 2018-11-10 10:58:09
        # how many columns & rows are actually displayed
        self._displayedColumns_:int = 0
        self._displayedRows_:int = 0

        self.populateModel(data)

    #### BEGIN lazy (paged) display
    #
    def canFetchMore(self, parentIndex:QtCore.QModelIndex) -> bool:
        return False if parentIndex.isValid() else self._displayedRows_ < self._modelDataRows_ or self._displayedColumns_ < self._modelDataColumns_

    def fetchMore(self, parentIndex:QtCore.QModelIndex):
        if parentIndex.isValid():
            return

        startRow:int = self._displayedRows_
        startColumn:int = self._displayedColumns_

        remainingRows = self._modelDataRows_ - startRow
        remainingColumns = self._modelDataColumns_ - startColumn

        rowsToFetch = min(self._rowBatchSize_, remainingRows)
        columnsToFetch = min(self._columnBatchSize_, remainingColumns)

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

        except Exception as e: # noqa
            traceback.print_exc()

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if self._modelData_ is None:
            return QtCore.QVariant()

        return self._getHeaderData_(section, orientation, role)

    def rowCount(self, parentIndex:QtCore.QModelIndex = QtCore.QModelIndex()):
        r"""Number of rows the model currently handles.
        This may be less than the notional "rows" in the data
        """
        nRows = self._displayedRows_ if self._displayedRows_ <= self._modelDataRows_ else self._modelDataRows_
        return 0 if parentIndex.isValid() else nRows
        # return 0 if parentIndex.isValid() else self._displayedRows_

    def columnCount(self, parentIndex:QtCore.QModelIndex = QtCore.QModelIndex()):
        return 0 if parentIndex.isValid() else self._displayedColumns_

    #### BEGIN editable items
    #
    def flags(self, modelIndex:QtCore.QModelIndex):
        if not modelIndex.isValid():
            return QtCore.Qt.ItemIsEnabled

        return QtCore.Qt.ItemIsEditable | super().flags(modelIndex)

    def setData(self: typing.Self, modelIndex: QtCore.QModelIndex,
                value: object, role=QtCore.Qt.EditRole) -> bool:
        r"""Set a new data with the specified role, at the specified model index in this model.
    Overrides QtCore.QAbstractTableModel.setData
    """
        if self._modelData_ is None:
            return False

        row = modelIndex.row()
        col = modelIndex.column()

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
    def insertRow(self, row: int, row_value: object, parent: QtCore.QModelIndex) -> bool:
        # print(f"{self.__class__.__name__}.insertRows: row {row}, count {count}, parent {parent}")
        # # if self._modelData_ is None:
        # #     return False
        if not datatypes.is_iterable(self._modelData_):
            return False

        if row < 0 or row > len(self._modelData_):
            return False

        self.beginInsertRows(parent, row, row+1)
        try:
            self._insertDataRow_(self._modelData_, row, row_value)
        except: # noqa
            traceback.print_exc()
        finally:
            self.endInsertRows()

        self.fetchMore(parent)
        return True

    def appendRow(self, data: typing.Optional[object] = None) -> bool:
        if self._modelData_ is None:
            return

        return self.insertRow(self.rowCount(), data, QtCore.QModelIndex())

    def removeRow(self, row: int, parent: QtCore.QModelIndex) -> bool:
        # BUG 2026-06-12 23:32:29 FIXME
        # when removing intermediate rows the vertical header does NOT update its sections
        # to reflect the reduced number of rows
        if not datatypes.is_iterable(self._modelData_):
            return False

        if row < 0 or row > len(self._modelData_):
            return False

        if row < self._modelDataRows_: # -1:
            row1 = row
        else:
            row1 = row+1

        # print(f"{self.__class__.__name__}.removeRow({row}) -> row1 = {row1}")
        self.beginRemoveRows(parent, row, row1)

        if isinstance(self._modelData_, pd.DataFrame):
            self._modelData_ = self._modelData_.drop(self._modelData_.index[row])
            self._modelDataRows_ = self._modelData_.shape[0]
        else:
            del(self._modelData_[row])
            self._modelDataRows_ = len(self._modelData_)

        self.endRemoveRows()
        # self._displayedRows_ = 0
        # self.fetchMore(parent)
        return True

    @singledispatchmethod
    def _insertDataRow_(self, mdata, row: int, obj: object = None) -> bool:
        scipywarn(f"Cannnot add rows to {type(mdata).__name__}")
        return False

    @_insertDataRow_.register(pd.DataFrame)
    def __insertDataRow__(self, mdata: pd.DataFrame,
                       row: int,
                       obj: typing.Optional[pd.DataFrame] = None) -> bool: # noqa

        if row == self.rowCount():
            if issubclass(mdata.index.dtype.type, (float, int, complex, np.floating, np.complexfloating, np.integer)):
                δndx = mdata.index[-1] - mdata.index[-2]
                newIndex = pd.Index([mdata.index[-1] + δndx], name = mdata.index.name)
            else:
                newIndex = pd.Index([f"row {mdata.index.size+1}"], name = mdata.index.name)

            try:
                if obj is None:
                    obj = pd.DataFrame(dict(zip(mdata.columns, tuple((pd.NA, )) * mdata.shape[1])), index = newIndex)

                elif isinstance(obj, typing.Sequence):
                    obj = pd.DataFrame(dict(zip(mdata.columns, obj)), index = newIndex)
                else:
                    return False

                self._modelData_ = pd.concat((mdata, obj))

            except: # noqa
                traceback.print_exc()
                return False

        else:
            if issubclass(mdata.index.dtype.type, (float, int, complex, np.floating, np.complexfloating, np.integer)):
                δndx = mdata.index[row] - mdata.index[row-1]
                newIndex = pd.Index([mdata.index[row] + δndx], name = mdata.index.name)
            else:
                newIndex = pd.Index([f"row {row+1}"], name = mdata.index.name)
            try:
                if obj is None:
                    obj = pd.DataFrame(dict(zip(mdata.columns, tuple((pd.NA, )) * mdata.shape[1])), index = newIndex).T

                elif isinstance(obj, typing.Sequence):
                    obj = pd.DataFrame(dict(zip(mdata.columns, obj)), index = newIndex).T

                else:
                    return False

                temp = mdata.T
                temp.insert(row, obj.columns[0], obj, allow_duplicates = True)
                self._modelData_ = temp.T

            except: # noqa
                traceback.print_exc()
                return False

        self._modelDataRows_ = self._modelData_.shape[0]
        self._original_data_ = self._modelData_
        self._canAddRemoveRows_ = True
        self._canAddRemoveColumns_ = False

        return True

    @_insertDataRow_.register(ephys_pathways.SynapticPathwayList)
    @_insertDataRow_.register(ephys_pathways.AuxiliaryInputList)
    @_insertDataRow_.register(ephys_pathways.AuxiliaryOutputList)
    @_insertDataRow_.register(ephys_pathways.SynapticStimulusChannelList)
    @_insertDataRow_.register(TriggerProtocolList)
    def __insertDataRow__(self, mdata: typing.Union[
        ephys_pathways.SynapticPathwayList,
        ephys_pathways.AuxiliaryInputList,
        ephys_pathways.AuxiliaryOutputList,
        ephys_pathways.SynapticStimulusChannelList,
        ], # noqa
        row: int,
        obj: typing.Optional[ephys_pathways.SynapticPathway] = None) -> bool:
        if obj is None:
            if isinstance(mdata, ephys_pathways.SynapticPathwayList):
                obj = ephys_pathways.SynapticPathway()
            elif isinstance(mdata, ephys_pathways.AuxiliaryInputList):
                obj = ephys_pathways.AuxiliaryInput()
            elif isinstance(mdata, ephys_pathways.AuxiliaryOutputList):
                obj = ephys_pathways.AuxiliaryOutput()
            elif isinstance(mdata, ephys_pathways.SynapticStimulusChannelList):
                obj = ephys_pathways.SynapticStimulusChannel()
            elif isinstance(mdata, TriggerProtocolList):
                obj = TriggerProtocol()

        if not isinstance(obj, (ephys_pathways.SynapticPathway,
                                ephys_pathways.AuxiliaryInput,
                                ephys_pathways.AuxiliaryOutput,
                                ephys_pathways.SynapticStimulusChannel,
                                TriggerProtocol
                                )
                        ):
            return False

        if row == self.rowCount():
            self._modelData_.append(obj)
        else:
            temp = list(self._modelData_)
            temp.insert(row, obj)
            self._modelData_ = type(self._modelData_)(temp)

        self._modelDataRows_ = len(self._modelData_)
        self._original_data_ = self._modelData_
        self._canAddRemoveRows_ = True
        self._canAddRemoveColumns_ = False

        return True

    @_insertDataRow_.register(list)
    @_insertDataRow_.register(deque)
    def __insertDataRow__(self, mdata: typing.Sequence, # noqa
                       row: int, # noqa
                       obj: typing.Optional[object] = None) -> bool:
        if len(mdata):
            if all(isinstance(o, ephys_pathways.RecordingSource) for o in mdata):
                if obj is None:
                    obj = ephys_pathways.RecordingSource()

                if not isinstance(obj, ephys_pathways.RecordingSource):
                    scipywarn(f"A RecordingSource object was expected; instead, got a {type(obj).__name__}")
                    return False

            elif all(isinstance(o, typing.Sequence) for o in mdata):
                if isinstance(obj, typing.Sequence):
                    if len(obj) != len(mdata[-1]):
                        scipywarn(f"Expecting a sequence of {len(mdata[-1])} objects")
                        return False

                else:
                    scipywarn(f"Expecting a sequence of {len(mdata[-1])} objects")
                    return False

            else:
                if all(
                    isinstance(d,
                                    (int, float, str, bool,
                                    np.integer, np.floating, np.complexfloating,
                                    np.character, np.bool,
                                    pq.Quantity)
                                )
                    for d in mdata
                    ):
                    if not isinstance(obj, ((int, float, str, bool,
                                    np.integer, np.floating, np.complexfloating,
                                    np.character, np.bool,
                                    pq.Quantity, types.NoneType))):
                        return False

        else:
            return False

        if row == self.rowCount():
            self._modelData_.append(obj)
        else:
            self._modelData_.insert(row, obj)

        self._modelDataRows_ = len(self._modelData_)
        self._original_data_ = self._modelData_
        self._canAddRemoveRows_ = True
        self._canAddRemoveColumns_ = False

        return True

    #### END resizable model

    #### END item data handling

    @Slot(object)
    def populateModel(self, data):
        from core import datatypes
        from imaging import vigrautils

        # print(f"{self.__class__.__name__}.populateModel({type(data).__name__})")
        # ### BEGIN Define timer to debug
        # #
        # timer = QtCore.QElapsedTimer()
        # timer.start()
        #
        # ### END   Define timer debug

        self.beginResetModel()
        try:
            self._is_vigra_filter_kernel_ = False
            self._original_data_ = data

            self._makeModelData_(data)
            self._displayedRows_ = 0
            self._displayedColumns_ = 0

            if self._modelData_ is None:
                self.headerDataChanged.emit(QtCore.Qt.Vertical, 0, 0)
                self.headerDataChanged.emit(QtCore.Qt.Horizontal, 0, 0)

            else:
                self.headerDataChanged.emit(QtCore.Qt.Horizontal, 0, self._modelDataColumns_)
                self.headerDataChanged.emit(QtCore.Qt.Vertical, 0, self._modelDataRows_)

        except Exception as e:
            traceback.print_exc()

        self.endResetModel()

        if "Edit" in self._modelDataColumnHeaders_.values():
            self._useExternalDataEditor_ = True

        self.sig_modelPopulated.emit()


        # ### BEGIN report timing
        #
        # print(f"{self.__class__.__name__}.populateModel({type(data).__name__}) took {timer.elapsed()} milliseconds")
        #
        # ### END   report timing

    @Slot()
    def _slot_dataEditedExternally(self):
        pass

    # def rowOps(self, row:object):
    #     if not self._canAddRemoveRows_:
    #         return

        # if isinstance()

    # def colOps()

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
                            if isinstance(self._modelDataColumnHeaders_, dict) and len(self._modelDataColumnHeaders_):
                                return QtCore.QVariant(self._modelDataColumnHeaders_[section])
                            else:
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
                            if (
                                isinstance(self._modelDataColumnHeaders_, dict)
                                # and len(self._modelDataColumnHeaders_)
                                and section < len(self._modelDataColumnHeaders_)
                                ):
                                return QtCore.QVariant(self._modelDataColumnHeaders_[section])
                            else:
                                return QtCore.QVariant(str(self._modelData_.columns[section]))
                            # return QtCore.QVariant(str(self._modelData_.columns[section]))

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
                            # ret = " ".join(["%s" % v for v in self._modelData_.index.names] + ["(%s)" % self._modelData_.iloc[section,:].dtype])
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
                            if section < self._modelData_.index.size:
                                return QtCore.QVariant(str(self._modelData_.index[section]))
                            else:
                                return QtCore.QVariant()

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

                            if section < self._modelData_.index.size:
                                return QtCore.QVariant(ret)
                            else:
                                return QtCore.QVariant()

                        else:
                            return QtCore.QVariant()

                    else:
                        return QtCore.QVariant()

            elif isinstance(self._modelData_, pd.Series):
                if orientation == QtCore.Qt.Horizontal: # horizontal (column) headers
                    if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.AccessibleTextRole):
                        if isinstance(self._modelDataColumnHeaders_, dict) and len(self._modelDataColumnHeaders_):
                            return QtCore.QVariant(self._modelDataColumnHeaders_[section])
                        else:
                            return QtCore.QVariant(str(self._modelData_.columns[section]))
                        # return QtCore.QVariant(str(self._modelData_.name))

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
                            if section < self._modelData_.index.size:
                                return QtCore.QVariant(str(self._modelData_.index[section]))
                            else:
                                return QtCore.QVariant()

                        elif role in (QtCore.Qt.ToolTipRole, QtCore.Qt.AccessibleDescriptionRole):
                            try:
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

                            except: # noqa
                                return QtCore.QVariant()

                            # if section < self._modelData_.index.size:
                            #     return QtCore.QVariant(ret)
                            # else:
                            #     return QtCore.QVariant()

                        else:
                            return QtCore.QVariant()

                    elif isinstance(self._modelData_.index, pd.Index):
                        if section < self._modelData_.index.size:
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

                    else:
                        return QtCore.QVariant()

            elif isinstance(self._modelData_, TriggerProtocolList):
                if orientation == QtCore.Qt.Horizontal: # horizontal (columns) header
                    if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.AccessibleTextRole):
                        if (isinstance(self._modelDataColumnHeaders_, dict)
                            and len(self._modelDataColumnHeaders_)
                            and section in range(self._modelDataColumns_)):
                            return QtCore.QVariant(self._modelDataColumnHeaders_[section])
                        else:
                            return QtCore.QVariant()
                    else:
                        return QtCore.QVariant()
                else:
                    if section < len(self._modelData_):
                        return QtCore.QVariant(f"{section}")
                    else:
                        return QtCore.QVariant()

            elif isinstance(self._modelData_, NeoObjectList):
                if orientation == QtCore.Qt.Horizontal: # horizontal (columns) header
                    if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.AccessibleTextRole):
                        # for horizontal header, section number is the column number
                        if (isinstance(self._modelDataColumnHeaders_, dict)
                            and len(self._modelDataColumnHeaders_)):
                            colhead = self._modelDataColumnHeaders_[section]
                            return QtCore.QVariant(colhead)
                        else:
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
                        try:
                            if len(self._modelData_):
                                if self._modelDataColumnHeaders_[section].lower() == "edit":
                                    tip = "Double-click in the desired row to edit the object represented in the row"
                                else:
                                    tip = type(getattr(self._modelData_[0], self._modelDataColumnHeaders_[section])).__name__
                                return QtCore.QVariant(f"{tip}")
                            else:
                                return QtCore.QVariant()
                        except:
                            traceback.print_exc()
                            return QtCore.QVariant()

                    else:
                        return QtCore.QVariant()

                else: # vertical (rows) headers
                    if section < len(self._modelData_):
                        return QtCore.QVariant(f"{section}")
                    else:
                        return QtCore.QVariant()
                    # return QtCore.QVariant(f"{section}")

            elif isinstance(self._modelData_, np.ndarray):
                if role in (QtCore.Qt.DisplayRole, QtCore.Qt.AccessibleTextRole):
                    lbl = f"{section}"
                    if orientation == QtCore.Qt.Horizontal:
                        if (isinstance(self._modelDataColumnHeaders_, dict)
                            and len(self._modelDataColumnHeaders_)
                            and section in self._modelDataColumnHeaders_
                            ):
                            return QtCore.QVariant(self._modelDataColumnHeaders_[section])
                        else:
                            if isinstance(self._modelData_, pq.Quantity):
                                lbl = f"{scq.getUnitFamily(self._modelData_.units)} ({self._modelData_.units.dimensionality})"

                    else:
                        if section < self._modelData_.shape[0]:
                            return QtCore.QVariant(lbl)
                        else:
                            return QtCore.QVariant()

                elif role in (QtCore.Qt.ToolTipRole, QtCore.Qt.AccessibleDescriptionRole):
                    if orientation == QtCore.Qt.Horizontal:
                        lbl = "%s" % self._modelData_[:,section].dtype
                        if isinstance(self._modelData_, pq.Quantity):
                            lbl += f" ({self._modelData_.units.dimensionality})"
                        return QtCore.QVariant(lbl)

                    else:
                        if section < self._modelData_.shape[0]:
                            return QtCore.QVariant("%s" % self._modelData_[section,:].dtype)
                        else:
                            return QtCore.QVariant()

                else:
                    return QtCore.QVariant()

            elif isinstance(self._modelData_,
                                (
                                    typing.Sequence,
                                    ephys_pathways.SynapticPathwayList,
                                    ephys_pathways.AuxiliaryInputList,
                                    ephys_pathways.AuxiliaryOutputList,
                                    ephys_pathways.SynapticStimulusChannelList,
                                )
                            ):
                if role in (QtCore.Qt.DisplayRole, QtCore.Qt.AccessibleTextRole):
                    # lbl = f"{section}"
                    if orientation == QtCore.Qt.Horizontal:
                        if (isinstance(self._modelDataColumnHeaders_, dict)
                            and len(self._modelDataColumnHeaders_)):
                            if section in self._modelDataColumnHeaders_:
                                return QtCore.QVariant(f"{self._modelDataColumnHeaders_[section]}")
                            else:
                                return  QtCore.QVariant(f"{section}")
                        else:
                            return  QtCore.QVariant(f"{section}")
                    else:
                        if section < len(self._modelData_):
                            return QtCore.QVariant(f"{section}")
                        else:
                            return QtCore.QVariant()

                elif role in (QtCore.Qt.ToolTipRole, QtCore.Qt.AccessibleDescriptionRole):
                    return QtCore.QVariant(f"{section}")

                else:
                    return QtCore.QVariant()

            else:
                return QtCore.QVariant()

        except (IndexError, ):
            return QtCore.QVariant()

        # print(f"{self.__class__.__name__}._getHeaderData_ took {timer.elapsed()} milliseconds")

    def _getModelData_(self, row, col, role = QtCore.Qt.DisplayRole) -> QtCore.QVariant:
        r"""Retrieves tabular data associated with row & column, given the item role.

    """
        try:
            if role not in (ObjectDataRole, QtCore.Qt.DisplayRole, # noqa
                            QtCore.Qt.EditRole, QtCore.Qt.ToolTipRole,
                            QtCore.Qt.AccessibleTextRole):
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

            elif isinstance(self._modelData_, TriggerProtocolList):
                protocol = self._modelData_[row]
                val = getattr(protocol, self._modelDataColumnHeaders_[col])
                if isinstance(val, enum.Enum):
                    disp = f"{val.name}"
                elif isinstance(val, neo.Event):
                    disp = f"{val.times}"
                else:
                    disp = f"{val}"

                ret = val if role in (ObjectDataRole, QtCore.Qt.EditRole) else disp # noqa

            elif isinstance(self._modelData_, (
                                                ephys_pathways.SynapticPathwayList,
                                                ephys_pathways.AuxiliaryInputList,
                                                ephys_pathways.AuxiliaryOutputList,
                                                ephys_pathways.SynapticStimulusChannelList,
                                               )
                            ):
                obj = self._modelData_[row]
                attribute = self._modelDataColumnHeaders_[col]
                if attribute.lower() != "edit":
                    val = getattr(obj, attribute)
                    if isinstance(val, enum.Enum):
                        disp = f"{val.name}"
                    else:
                        disp = f"{val}"
                    ret = val if role in (ObjectDataRole, QtCore.Qt.EditRole) else disp
                else:
                    return QtCore.QVariant()

            elif isinstance(self._modelData_, typing.Sequence):
                if all(isinstance(d, ephys_pathways.RecordingSource) for d in self._modelData_):
                    obj = self._modelData_[row]
                    attribute = self._modelDataColumnHeaders_[col]
                    if attribute.lower() == "edit":
                        return QtCore.QVariant()
                    else:
                        val = getattr(obj, attribute)
                        if isinstance(val, enum.Enum):
                            disp = f"{val.name}"
                        else:
                            disp = f"{val}"
                        ret = val if role in (ObjectDataRole, QtCore.Qt.EditRole) else disp # noqa

                else:
                    rowObj = self._modelData_[row]
                    if isinstance(rowObj, typing.Sequence):
                        val = rowObj[col]
                    else:
                        val = rowObj

                    if isinstance(val, enum.Enum):
                        disp = f"{val.name}"
                    else:
                        disp = f"{val}"
                    ret = val if role in (ObjectDataRole, QtCore.Qt.EditRole) else disp # noqa

            elif isinstance(self._modelData_, neo.core.dataobject.DataObject):
                if col == 0:
                    val = self._modelData_.times[row]
                else:
                    if self._modelData_.ndim > 1:
                        val = self._modelData_[row, col-1]
                    else:
                        val = self._modelData_[row]

                if isinstance(val, datetime.datetime):
                    ret = val if role == QtCore.Qt.EditRole else ret.isoformat(" ")

                else: # by default, value is a Quantity, here
                    ret = val if role == QtCore.Qt.EditRole else f"{val.magnitude}"

            elif isinstance(self._modelData_, np.ndarray):
                # NOTE: 2026-06-06 16:05:25 this MAY be a general (generic) Quantity array, too!
                if self._modelData_.ndim  == 0: # e.g. pq object
                    val = np.atleast_1d(self._modelData_)[row]

                elif self._modelData_.ndim > 1:
                    val = self._modelData_[row, col]

                else:
                    val = self._modelData_[row]


                if isinstance(val, datetime.datetime):
                    ret = val if role == QtCore.Qt.EditRole else ret.isoformat(" ")

                else: # allow for python Quantity arrays, here
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
                try:
                    pyvalue = value.value()
                except: # noqa
                    # traceback.print_exc()
                    pyvalue = value.value # for PODS this "comes out" directly !?

            else:
                pyvalue = value

            return self._setValueInModelData_(self._modelData_, pyvalue, row, col)

        except Exception as e: # noqa
            traceback.print_exc()
            return False

    @singledispatchmethod
    def _makeModelData_(self, data):
        scipywarn(f"{type(data).__name__} data are not supported yet")
        self._modelData_ = data
        self._original_data_ = data
        self._modelDataRows_ = 0
        self._modelDataColumns_ = 0
        self._canAddRemoveRows_ = False
        self._canAddRemoveColumns_ = False
        self._modelDataColumnHeaders_ = dict()
        # self._modelDataRowIndexName_ = "Index"

    @_makeModelData_.register(types.NoneType)
    def __makeModelData__(self, data: types.NoneType):
        self._modelData_ = data
        self._original_data_ = data
        self._modelDataRows_ = 0
        self._modelDataColumns_ = 0
        self._canAddRemoveRows_ = False
        self._canAddRemoveColumns_ = False
        self._modelDataColumnHeaders_ = dict()

    @_makeModelData_.register(pd.DataFrame)
    def __makeModelData__(self, data: pd.DataFrame): # noqa
        self._modelData_ = data
        self._modelDataRows_ = data.shape[0]
        self._modelDataColumns_ = data.shape[1]

        if isinstance(self._modelData_.columns, (pd.MultiIndex, pd.Index)):
            self._modelDataColumnHeaders_ = dict(
                tuple(
                    map(
                        lambda x: (x[0], f"{x[1]}"),
                        enumerate(data.columns)
                        )
                    )
                )

        # self._modelDataColumnHeaders_ = dict(enumerate(data.columns))
        self._canAddRemoveColumns_ = True
        self._canAddRemoveRows_ = True
        self._modelDataRowIndexName_ = self._modelData_.index.name or "Index"

    @_makeModelData_.register(pd.Series)
    def __makeModelData__(self, data: pd.Series): # noqa
        self._modelData_ = data
        self._modelDataRows_ = data.shape[0]
        self._modelDataColumns_ = 1
        self._modelDataColumnHeaders_ = {0: data.name}
        self._canAddRemoveRows_ = True
        self._canAddRemoveColumns_ = False
        self._modelDataRowIndexName_ = "Index"

    @_makeModelData_.register(pd.Index)
    def __makeModelData__(self, data: pd.Index): # noqa
        self._modelData_ = data
        self._modelDataRows_ = data.shape[0]
        self._modelDataColumns_ = 1
        self._modelDataColumnHeaders_ = {0: "Index or Column"}
        self._canAddRemoveRows_ = True
        self._canAddRemoveColumns_ = False
        self._modelDataRowIndexName_ = "Index"

    @_makeModelData_.register(vigra.filters.Kernel1D)
    @_makeModelData_.register(vigra.filters.Kernel2D)
    def __makeModelData__(self, data: vigra.filters.Kernel1D | vigra.filters.Kernel2D): # noqa
        self._modelData_ = vigrautils.kernel2array(data)
        self._modelDataRows_ = data.shape[0]
        self._modelDataColumns_ = 1 if isinstance(data, vigra.filters.Kernel1D) else 2
        self._modelDataColumnHeaders_ = {0: "Sample"} if isinstance(data, vigra.filters.Kernel1D) else {0: "X", 1: "Y"}
        self._is_vigra_filter_kernel_  = True
        self._original_data_ = data
        self._canAddRemoveRows_ = False
        self._canAddRemoveColumns_ = False
        self._modelDataRowIndexName_ = "Index"

    @_makeModelData_.register(TriggerProtocolList)
    def __makeModelData__(self, data: TriggerProtocolList): # noqa
        self._modelData_ = data
        self._original_data_ = data
        self._modelDataRows_ = len(data)
        # self._is_vigra_filter_kernel_ = 0
        self._canAddRemoveRows_ = True
        self._canAddRemoveColumns_ = False

        self._modelDataColumnHeaders_ = dict(
            tuple(
                map(
                    lambda x: (x[0], f"{x[1]}"),
                    enumerate(("name", "presynaptic", "postsynaptic", "photostimulation",
                        "acquisition", "imagingDelay" ,"segments")
                    ))
                )
            )
        self._modelDataColumns_ = len(self._modelDataColumnHeaders_)
        self._modelDataRowIndexName_ = "Index"

    @_makeModelData_.register(ephys_pathways.SynapticPathwayList)
    def __makeModelData__(self, data: ephys_pathways.SynapticPathwayList): # noqa
        self._modelData_ = data
        self._original_data_ = data
        self._modelDataRows_ = len(data)
        # self._is_vigra_filter_kernel_ = 0
        self._canAddRemoveRows_ = True
        self._canAddRemoveColumns_ = False

        names = list(map(lambda f: f.name, dataclasses.fields(ephys_pathways.SynapticPathway))) + ["Edit"]

        # NOTE: 2026-06-07 21:38:40 see NOTE: 2026-06-07 21:36:23
        self._modelDataColumnHeaders_ = dict(
            tuple(
                map(
                    lambda x: (x[0], f"{x[1]}"),
                    enumerate(("name", "adc", "dac",
                                "electrodeMode", "pathwayType", "Edit")
                    ))
                )
            )
        self._modelDataColumns_ = len(self._modelDataColumnHeaders_)
        self._modelDataRowIndexName_ = "Index"

    @_makeModelData_.register(ephys_pathways.AuxiliaryInputList)
    def __makeModelData__(self, data: ephys_pathways.AuxiliaryInputList): # noqa
        self._modelData_ = data
        self._original_data_ = data
        self._modelDataRows_ = len(data)
        # self._is_vigra_filter_kernel_ = 0
        self._canAddRemoveRows_ = True
        self._canAddRemoveColumns_ = False

        # NOTE: 2026-06-07 21:36:23
        # Only display (and allow editing) the relevant fields:
        # name & adc; give option to edit the entire object via an "Edit"
        # column
        self._modelDataColumnHeaders_ = dict(
            tuple(
                map(
                    lambda x: (x[0], f"{x[1]}"),
                    enumerate(("name", "adc", "Edit"))
                    )
                )
            )
        self._modelDataColumns_ = len(self._modelDataColumnHeaders_)
        self._modelDataRowIndexName_ = "Index"

    @_makeModelData_.register(ephys_pathways.AuxiliaryOutputList)
    def __makeModelData__(self, data: ephys_pathways.AuxiliaryOutputList): # noqa
        self._modelData_ = data
        self._original_data_ = data
        self._modelDataRows_ = len(data)
        # self._is_vigra_filter_kernel_ = 0
        self._canAddRemoveRows_ = True
        self._canAddRemoveColumns_ = False

        # NOTE: 2026-06-07 21:37:08 see NOTE: 2026-06-07 21:36:23
        self._modelDataColumnHeaders_ = dict(
            tuple(
                map(
                    lambda x: (x[0], f"{x[1]}"),
                    enumerate(("name", "channel", "Edit"))
                    )
                )
            )
        self._modelDataColumns_ = len(self._modelDataColumnHeaders_)
        self._modelDataRowIndexName_ = "Index"

    @_makeModelData_.register(ephys_pathways.SynapticStimulusChannelList)
    def __makeModelData__(self, data: ephys_pathways.SynapticStimulusChannelList): # noqa
        self._modelData_ = data
        self._original_data_ = data
        self._modelDataRows_ = len(data)
        # self._is_vigra_filter_kernel_ = 0
        self._canAddRemoveRows_ = True
        self._canAddRemoveColumns_ = False

        # NOTE: 2026-06-07 21:38:07 see NOTE: 2026-06-07 21:36:23
        self._modelDataColumnHeaders_ = dict(
            tuple(
                map(
                    lambda x: (x[0], f"{x[1]}"),
                    enumerate(("name", "channel", "dig"))
                    )
                )
            )
        self._modelDataColumns_ = len(self._modelDataColumnHeaders_)
        self._modelDataRowIndexName_ = "Index"

    @_makeModelData_.register(np.ndarray)
    def __makeModelData__(self, data: np.ndarray): # noqa
        # trying to streamline this
        # NOTE: 2025-11-23 09:45:45 FIXME/TODO - TOO SLOW!
        # lazy display alleviates this to some degree (see self.fetchMore(…))
        self._canAddRemoveRows_ = True
        self._canAddRemoveColumns_ = True

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

                domain = getattr(data, "times", None)
                domain_name = getattr(data, "domain_name", scq.getUnitFamily(domain))
                if len(domain_name) == 0:
                    # domain_name = f"{domain.dimensionality}"
                    domain_name = f"{scq.unitSymbol(domain)}"
                else:
                    # domain_name += f" ({domain.dimensionality})"
                    domain_name += f" ({scq.unitSymbol(domain)})"

                if data.ndim > 1:
                    # include domain as the first column
                    self._modelDataColumns_ = data.shape[1] + 1 # this shows data.times as column 0

                    channel_names = None
                    if len(data.array_annotations):
                        if "channel_names" in data.array_annotations:
                            channel_names = list(
                                map(
                                    lambda n: f"{n}",
                                    data.array_annotations["channel_names"]
                                    )
                                )
                        elif "channel_ids" in data.array_annotations:
                            channel_names = list(
                                map(
                                    lambda i: f"{i}",
                                    data.array_annotations["channel_ids"]
                                    )
                                )

                    if channel_names is None:
                        channel_names = list(map(lambda i: f"Channel {i}", range(data.shape[1])))

                    channel_names = list(map(lambda kc: f"{channel_names[kc]} ({data[:,kc].dimensionality})",
                                                range(len(channel_names))))
                    headers = [domain_name, ] + channel_names

                    self._modelDataColumnHeaders_ = dict(
                            (
                                tuple(map(lambda x: (x[0]+1, x),
                                            enumerate(headers))
                                    )
                            )
                        )

                    self._modelDataRowIndexName_ = domain_name

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
                        # see NOTE: 2025-09-27 11:06:52 in gui/delegates.py
                        self.immutableColumns = [0]
                        # below, allow editing t_start
                        self.immutableRows = range(1,self._modelDataRows_)
                        self.jointImmutability = True
                        # self._modelDataRowIndexName_ = f"{scq.unitFamilyName(data.times)} ({scq.unitSymbol(data.times)})"

                else: # e.g. case of spiketrains:
                    self._modelDataColumns_ = 1 if isinstance(data, neo.SpikeTrain) else 2
                    if isinstance(data, neo.SpikeTrain):
                        headers = [domain_name ]
                    else:
                        channel_names = None
                        if len(data.array_annotations):
                            if "channel_names" in data.array_annotations:
                                channel_names = list(
                                    map(
                                        lambda n: f"{n}",
                                        data.array_annotations["channel_names"]
                                        )
                                    )
                            elif "channel_ids" in data.array_annotations:
                                channel_names = list(
                                    map(
                                        lambda i: f"{i}",
                                        data.array_annotations["channel_ids"]
                                        )
                                    )

                        if channel_names is None:
                            channel_names = [f"Channel 0 ({data.dimensionality})"]

                        headers = [domain_name, ] + channel_names

                    self._modelDataColumnHeaders_ = dict(
                            (
                                tuple(map(lambda x: (x[0]+1, x),
                                            enumerate(headers))
                                    )
                            )
                        )

                    self._modelDataRowIndexName_ = domain_name

            else:
                self._modelDataRows_ = 1
                self._modelDataColumns_ = 1
                self._modelDataColumnHeaders_ = {0: f"{scq.getUnitFamily(data)} ({data.units.dimensionality})"}
                self._modelDataRowIndexName_ = "Index"

                # self._canAddRemoveColumns_ = True

            self._modelData_ = data

        else: # "plain" numpy arrays and "generic" Quantity arrays
            if data.ndim > 2:
                if all (v == 1 for v in data.shape[2:]):
                    self._modelData_ = np.squeeze(data).reshape((data.shape[0], np.prod(data.shape[1:])))
                else:
                    raise ValueError("Arrays with more than two dimensions and with non-singleton dimensions higher than 2 are not supported")
            else:
                self._modelData_ = data

            self._modelDataRowIndexName_ = "Index"

            if self._modelData_.ndim:
                self._modelDataRows_ = self._modelData_.shape[0]
                if self._modelData_.ndim > 1:
                    self._modelDataColumns_ = self._modelData_.shape[1]
                    if isinstance(self._modelData_, pq.Quantity):
                        self._modelDataColumnHeaders_ = dict(
                                tuple(
                                    map(
                                        lambda x: (x, f"{scq.getUnitFamily(data)} ({self._modelData_.units.dimensionality})"),
                                        range(self._modelData_.shape[1])
                                        )
                                    )
                            )

                else:
                    self._modelDataColumns_ = 1
                    if isinstance(self._modelData_, pq.Quantity):
                        self._modelDataColumnHeaders_ = {0: f"{scq.getUnitFamily(data)} ({data.units.dimensionality})"}
            else:
                self._modelDataRows_ = 1
                self._modelDataColumns_ = 1
                if isinstance(self._modelData_, pq.Quantity):
                    self._modelDataColumnHeaders_ = {0: f"{scq.getUnitFamily(data)} ({data.units.dimensionality})"}


    @_makeModelData_.register(list)
    @_makeModelData_.register(tuple)
    @_makeModelData_.register(deque)
    def __makeModelData__(self, data: typing.Sequence): # noqa
        if len(data):
            if all(isinstance(d, ephys_pathways.RecordingSource) for d in data):
                self._modelData_ = data
                self._original_data_ = data
                self._modelDataRows_ = len(data)
                self._canAddRemoveRows_ = True
                self._canAddRemoveColumns_ = False
                # self._is_vigra_filter_kernel_ = 0
                # NOTE: 2026-06-07 21:38:07 see NOTE: 2026-06-07 21:36:23
                self._modelDataColumnHeaders_ = dict(
                    tuple(
                        map(
                            lambda x: (x[0], f"{x[1]}"),
                            enumerate(("name", "adc", "dac", "electrodeMode", "Edit"))
                            )
                        )
                    )
                self._modelDataColumns_ = len(self._modelDataColumnHeaders_)

            elif all(isinstance(d, typing.Sequence) for d in data):
                # NOTE: 2026-06-07 21:59:50 Row-major !!!
                # i.e., access is data[row][column] ≡ data[y][x]
                assert all(len(d) == len(data[0]) for d in data[1:]), "Sequences with non-rectangular shape are not supported"

                assert datatypes.is_homogeneous_sequence(data), "Only sequences homogeneous in their element types are supported"

                # if any(any(isinstance(d_, typing.Sequence) for d_ in d) for d in data):
                #     raise ValueError("Only 2D nested sequences are supported")

                self._modelData_ = data
                self._original_data_ = data
                self._modelDataColumns_ = len(data[0])
                self._modelDataRows_ = len(data)

                self._modelDataColumnHeaders_ = dict(
                    tuple(
                        map(
                            lambda x: (x, f"{x}"),
                            range(self._modelDataColumns_)
                            )
                        )
                    )
                self._canAddRemoveRows_ = True
                self._canAddRemoveColumns_ = True

                if isinstance(data, tuple):
                    self.immutableRows = range(self._modelDataRows_)
                    self.immutableColumns = range(self._modelDataColumns_)
                    self._canAddRemoveColumns_ = False

                else:
                    self.immutableRows = list(
                        map(
                            lambda x: x[0],
                            filter(
                                lambda x: isinstance(x[1], tuple),
                                enumerate(data)
                                )
                            )
                        )
                    self._canAddRemoveColumns_ = False

            else:
                if all(
                    isinstance(d,
                                    (int, float, str, bool,
                                    np.integer, np.floating, np.complexfloating,
                                    np.character, np.bool,
                                    pq.Quantity)
                                    )
                    for d in data
                    ):

                    self._modelData_ = data
                    self._original_data_ = data
                    self._modelDataColumns_ = 1
                    self._modelDataRows_ = len(data)

                    self._modelDataColumnHeaders_ = dict(
                        tuple(
                            map(
                                lambda x: (x, f"{x}"),
                                range(self._modelDataColumns_)
                                )
                            )
                        )
                    self._canAddRemoveRows_ = True
                    self._canAddRemoveRows_ = True

                else:
                    scipywarn("Unsupported sequence element types")
                    self._modelDataColumns_ = 0
                    self._modelDataRows_ = 0
                    self._modelDataColumnHeaders_ = dict()
                    self._modelData_ = None
                    self._original_data_ = None

        else:
            self._modelDataColumns_ = 0
            self._modelDataRows_ = 0
            self._modelDataColumnHeaders_ = dict()
            self._modelData_ = data
            self._original_data_ = data
            self._canAddRemoveRows_ = True
            self._canAddRemoveRows_ = True

        self._modelDataRowIndexName_ = "Index"

    @singledispatchmethod
    def _setValueInModelData_(self, mdata, pyvalue, row, col) -> bool:
        scipywarn(f"Unsupported model data {type(mdata).__name__}")
        return False

    @_setValueInModelData_.register(pd.DataFrame)
    def __setValueInModelData__(self, mdata: pd.DataFrame, pyvalue, row, col) -> bool:
        if row >= mdata.shape[0]:
            return False

        mdata.iloc[row, col] = pyvalue
        return True

    @_setValueInModelData_.register(pd.Series)
    def __setValueInModelData__(self, mdata: pd.Series, pyvalue, row, col) -> bool: # noqa
        if row >= mdata.shape[0]:
            return False

        mdata.iloc[row] = pyvalue
        return True

    @_setValueInModelData_.register(neo.dataobject.DataObject)
    def __setValueInModelData__(self, mdata: neo.dataobject.DataObject, pyvalue, row, col) -> bool: # noqa
        if row >= mdata.shape[0]:
            return False

        if isinstance(mdata, neo.SpikeTrain) and col > 0:
            return False

        if col >= mdata.shape[1] + 1:
            # because the signal's domain is on column 0, what is shown
            # here has one extra column
            return False

        if col == 0:
            if isinstance(mdata, (neo.AnalogSignal, DataSignal)) :
                # for analog signals only t_start can be edited
                if row == 0:
                    # allow setting t_start
                    if isinstance(pyvalue, pq.Quantity):
                        if pyvalue.units != mdata.times.units:
                            raise ValueError(f"Expecting value units of {mdata.times.units}; got ({pyvalue.units}) instead")

                        mdata.t_start = pyvalue
                        return True

                    elif isinstance(pyvalue, (float, int, complex)):
                        mdata.t_start = pyvalue * mdata.units
                        return True
                    else:
                        scipywarn(f"Expecting a float or a Quantity in {mdata.times.units}; got {type(pyvalue).__name__} instead")
                        return False
                else:
                    return False

            else:
                if isinstance(pyvalue, pq.Quantity):
                    if pyvalue.units != mdata.times.units:
                        scipywarn(f"Expecting value units of {mdata.times.units}; got ({pyvalue.units}) instead")
                        return False

                    mdata.times[row] = pyvalue
                    return True

                elif isinstance(pyvalue, (float, int, complex)):
                    mdata.times[row] = pyvalue * mdata.units
                    return True
                else:
                    scipywarn(f"Expecting a float or a Quantity in {mdata.times.units}; got {type(pyvalue).__name__} instead")
                    return False

        else:
            if isinstance(pyvalue, pq.Quantity):
                if pyvalue.units != mdata.units:
                    scipywarn(f"Expecting value units of {mdata.units}; got ({pyvalue.units}) instead")
                    return False

                mdata[row, col-1] = pyvalue
                return True

            elif isinstance(pyvalue, (float, int, complex)):
                mdata[row, col-1] = pyvalue * mdata.units
                return True
            else:
                scipywarn(f"Expecting a float or a Quantity in {mdata.units}; got {type(pyvalue).__name__} instead")
                return False


    @_setValueInModelData_.register(np.ndarray)
    def __setValueInModelData__(self, mdata: np.ndarray, pyvalue, row, col) -> bool: # noqa
        if row >= mdata.shape[0]:
            return False
        if mdata.ndim == 1:
            mdata[row] = pyvalue
        elif mdata.ndim == 2:
            mdata[row, col] = pyvalue

        if self._is_vigra_filter_kernel_:
            self._original_data_ = vigrautils.kernelfromarray(mdata)

        return True

    @_setValueInModelData_.register(TriggerProtocolList)
    def __setValueInModelData__(self, mdata: TriggerProtocolList, pyvalue, row, col) -> bool: # noqa
        if row >= len(mdata):
            return False
        protocol = mdata[row]

        attr = self._modelDataColumnHeaders_[col]

        setattr(protocol, attr, pyvalue)

        return True

    @_setValueInModelData_.register(ephys_pathways.SynapticPathwayList)
    @_setValueInModelData_.register(ephys_pathways.AuxiliaryInputList)
    @_setValueInModelData_.register(ephys_pathways.AuxiliaryOutputList)
    @_setValueInModelData_.register(ephys_pathways.SynapticStimulusChannelList)
    def __setValueInModelData__(self, mdata: typing.Union[ # noqa
                                                ephys_pathways.SynapticPathwayList,
                                                ephys_pathways.AuxiliaryInputList,
                                                ephys_pathways.AuxiliaryOutputList,
                                                ephys_pathways.SynapticStimulusChannelList,
                                                ], pyvalue, row, col) -> bool:
        if row >= len(mdata):
            return False

        old_obj = mdata[row]

        attr = self._modelDataColumnHeaders_[col]

        if isinstance(old_obj, ephys_pathways.SynapticPathway):
            params = {
                "name": old_obj.name,
                "adc": old_obj.adc,
                "dac": old_obj.dac,
                "stimulus": old_obj.stimulus,
                "electrode": old_obj.electrodeMode,
                "pathType": old_obj.pathwayType,
                "schedule": old_obj.schedule,
                "measurements": old_obj.measurements,
                }

        elif isinstance(old_obj, ephys_pathways.AuxiliaryInput):
            params = {
                "name": old_obj.name,
                "adc": old_obj.adc,
                "cmd": old_obj.cmd
                }

        elif isinstance(old_obj, ephys_pathways.AuxiliaryOutput):
            params = {
                "name": old_obj.name,
                "channel": old_obj.channel,
                "digttl": old_obj.digttl
                }

        elif isinstance(old_obj, ephys_pathways.SynapticStimulusChannel):
            params = {
                "name": old_obj.name,
                "channel": old_obj.channel,
                "dig": old_obj.dig
                }

        else:
            return False

        if attr.lower() != "edit":
            old_val = getattr(old_obj, attr)
            if isinstance(old_obj, ephys_pathways.SynapticPathway):
                if attr == "electrodeMode":
                    attr = "electrode"
                elif attr == "pathwayType":
                    attr = "pathType"
            if isinstance(old_val, enum.Enum):
                if isinstance(pyvalue, int):
                    params[attr] = type(old_val)(pyvalue)
                elif isinstance(pyvalue, str):
                    params[attr] = type(old_val)[pyvalue]
            else:
                params[attr] = pyvalue

        new_obj = type(old_obj)(**params)

        mdata[row] = new_obj

        return True

    @_setValueInModelData_.register(list)
    @_setValueInModelData_.register(deque)
    def __setValueInModelData__(self, mdata: list | deque, pyvalue, row, col) -> bool: # noqa
        if all(isinstance(o, ephys_pathways.RecordingSource) for o in mdata):
            old_obj = mdata[row]
            attr = self._modelDataColumnHeaders_[col]
            params = {
                "name":old_obj.name, "adc":old_obj.adc,
                "dac":old_obj.dac, "electrodeMode":old_obj.electrodeMode
                }
            if attr.lower() != "edit":
                old_val = getattr(old_obj, attr)
                print(f"'{attr}' -> {old_val} ({type(old_val)})")
                if isinstance(old_val, enum.Enum):
                    if isinstance(pyvalue, int):
                        params[attr] = type(old_val)(pyvalue)
                    elif isinstance(pyvalue, str):
                        params[attr] = type(old_val)[pyvalue]
                else:
                    params[attr] = pyvalue
            new_obj = type(old_obj)(**params)
            mdata[row] = new_obj
            return True
        else:
            try:
                mdata[row][col] = pyvalue
            except:
                traceback.print_exc()
                return False
        return True

    @property
    def sourceData(self):
        r"""Access to the source data behind this model.
    """
        if self._is_vigra_filter_kernel_:
            return self._original_data_
        return self._modelData_

    @property
    def immutability(self) -> dict:
        r"""Mapping row & col indexes where cell contents CANNOT be altered.
    E.g.: {"columns": [2,3], "rows": [0,1], "joint":False}
    """
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
        r"""Indexes of columns where the contents CANNOT be changed"""
        return self._immutability_["columns"]

    @immutableColumns.setter
    def immutableColumns(self, value:typing.Sequence[int]):
        self._immutability_["columns"] = value

    @property
    def immutableRows(self) -> typing.Sequence[int]:
        r"""Indexes of rows where the contents CANNOT be changed"""
        return self._immutability_["rows"]

    @immutableRows.setter
    def immutableRows(self, value:typing.Sequence[int]):
        self._immutability_["rows"] = value

    @property
    def canAlterRows(self) -> bool:
        return self._canAddRemoveRows_

    @canAlterRows.setter
    def canAlterRows(self, val: bool):
        self._canAddRemoveRows_ = val is True

    @property
    def canAlterColumns(self) -> bool:
        return self._canAddRemoveColumns_

    @canAlterColumns.setter
    def canAlterColumns(self, val: bool):
        self._canAddRemoveColumns_ = val is True

@singledispatch
def _appendRow_(self,
             obj: object, row: object, in_place: bool = False) -> object:
    r"""Appends a row of data to the object"""
    raise NotImplementedError(f"Object of type {type (obj).__name__} are not supported")

@_appendRow_.register(pd.DataFrame)
def __appendRow__(obj: pd.DataFrame,
      row: typing.Union[typing.Sequence, pd.Series],
      in_place: bool = False) -> pd.DataFrame:
    if isinstance(row, (pd.Series, np.ndarray)):
        assert(row.size == len(obj.columns)), f"Mismatch between the number of row elements ({row.size}) and target columns ({len(obj.columns)})"
        assert row.ndim==1, f"Wrong row dimensionality ({row.ndim}); should be 1"
        row = tuple(row)

    if isinstance(row, typing.Sequence):
        assert len(row) == len(obj.columns), f"Mismatch between the number of row elements ({len(row)}) and target columns ({len(obj.columns)})"

        for k, col in enumerate(obj.columns):
            dtype = obj[col].dtype
            rtype = type(row[k])
            if np.dtype(rtype) is not dtype:
                raise TypeError(f"Row element {k} expected to resolve to {dtype}; got {rtype.__name__} instead")

    else:
        raise TypeError(f"Row expected a pd.Series or a sequence of objects; got {type(row).__name__} instead")

    ret = obj if in_place else obj.copy()
    ret.loc[len(obj)] = row

    return ret

@_appendRow_.register(pd.Series)
@_appendRow_.register(pd.Index)
def __appendRow__(obj: typing.Union[pd.Series, pd.Index],
      row: typing.Union[dt.Number, str, pq.Quantity],
      in_place: bool = False) -> pd.Series | pd.Index:
    if isinstance(row, np.ndarray):
        if row.size > 1:
            raise ValueError("Can only add a scalar object")
        row = tuple(row)

    elif isinstance(row, typing.Sequence):
        if len(row) > 1:
            raise ValueError("Can only add a scalar object")

    else:
        row = (row,)

    dtype = obj.dtype
    rtype = type(row[0])
    # print(f"{rtype} -> {np.dtype(rtype)}")
    if np.dtype(rtype) is not dtype:
        raise TypeError(f"Row data expected to resolve to {dtype}; got {rtype.__name__} instead")

    ret = obj if in_place else obj.copy()
    ret.loc[len(obj)] = row[0]

    return ret

@_appendRow_.register(np.ndarray)
@_appendRow_.register(pq.Quantity)
def __appendRow__(obj: typing.Union[pq.Quantity, np.ndarray],
      row: typing.Union[typing.Sequence[pq.Quantity], pq.Quantity],
      in_place: bool = False) -> typing.Union[pq.Quantity, np.ndarray]:

    if isinstance(obj, pd.Quantity):
        units = obj.units
        obj = obj.magnitude

        if isinstance(row, pq.Quantity):
            if row.units != units:
                if scq.unitsConvertible(row, units):
                    row = row.rescale(units)
                else:
                    raise TypeError(f"Row units ({row.units}) are incompatible with target's units ({units})")

        row = row.magnitude

    assert row.ndim == obj.ndim, f"Mismatch between dimensions: for row ({row.ndim}) vs target ({obj.ndim})"

    try:
        if obj.ndim == 0:
            # NOTE: 2026-03-08 10:24:58
            # in_place does not make sense here , as concatenation of dimensionless
            # arrays is non-sensical; hence both obj and row MUST be converted
            # to 1D arrays
            ret = np.concat((np.atleast_1d(obj.magnitude), np.atleast_1d(row.magnitude)))

        else:
            ret = np.concat((obj.magnitude, row.magnitude), axis=0)

        if isinstance(obj, pq.Quantity):
            return ret * obj.units

        return ret
    except:
        # traceback.print_exc()
        raise

@_appendRow_.register(neo.IrregularlySampledSignal)
@_appendRow_.register(IrregularlySampledDataSignal)
def __appendRow__(obj: typing.Union[neo.IrregularlySampledSignal,
                        IrregularlySampledDataSignal],
      row: typing.Union[neo.IrregularlySampledSignal,
                        IrregularlySampledDataSignal],
      in_place: bool = False) -> typing.Union[neo.IrregularlySampledSignal,
                                              IrregularlySampledDataSignal]:
    r"""Concnatenates irregular signals on their domain axis"""
    if type(row) is not type(obj):
        raise TypeError(f"Row expected to be {type(obj).__name__}; got {type(row).__name__} instead")

    assert row.size == 1, f"Row must contain a single data point; instead, got {row.size}"

    domainUnits = obj.times.units
    rowDomainUnits = row.times.units

    if rowDomainUnits != domainUnits:
        if not scq.unitsConvertible(rowDomainUnits, domainUnits):
            raise TypeError(f"Incompatible domain units between row ({rowDomainUnits}) and target ({domainUnits})")
        row.times = row.times.rescale(domainUnits)

    ret = obj.concatenate(row, allow_overlap=True)
    ret.file_origin = ""

    return ret

@_appendRow_.register(neo.Epoch)
@_appendRow_.register(DataZone)
def __appendRow__(obj: typing.Union[neo.Epoch, DataZone],
      row: typing.Union[neo.Epoch, DataZone],
      in_place:bool=False) -> typing.Union[neo.Epoch, DataZone]:
    if type(row) is not type(obj):
        raise TypeError(f"Row expected to be {type(obj).__name__}; got {type(row).__name__} instead")

    assert row.size == 1, f"Row must contain a single data point; instead, got {row.size}"

    objTimes = obj.times
    rowTimes = row.times

    objDurations = obj.durations
    rowDurations = row.durations

    domainUnits = objTimes.units
    rowDomainUnits = rowTimes.units

    if rowDomainUnits != domainUnits:
        if not scq.unitsConvertible(rowDomainUnits, domainUnits):
            raise TypeError(f"Incompatible domain units between row ({rowDomainUnits}) and target ({domainUnits})")
        rowTimes = rowTimes.rescale(domainUnits)

    if rowDurations.units != objDurations.units:
        if not scq.unitsConvertible(rowDuration.units, objDurations.units):
            raise TypeError(f"Incompatible domain units between row ({rowDurations.units}) and target ({objDurations.units})")

        rowDurations = rowDurations.rescale(objDurations.units)

    times = np.concatenate((objTimes, rowTimes), axis=0) * objTimes.units

    durations = np.concatenate((objDurations, rowDurations), axis=0) * objDurations.units

    labels = np.concatenate((obj.labels, row.labels), axis=0)

    return type(obj)(times = times, durations = durations, labels = labels,
                     name = obj.name, description = obj.description,
                     file_origin = "",
                     array_annotations = obj.array_annotations,
                     **obj.annotations)

@_appendRow_.register(neo.Event)
@_appendRow_.register(DataMark)
@_appendRow_.register(TriggerEvent)
def __appendRow__(obj: typing.Union[neo.Event, DataMark, TriggerEvent],
      row: typing.Union[neo.Event, DataMark, TriggerEvent],
      in_place:bool=False) -> typing.Union[neo.Event, DataMark, TriggerEvent]:
    if type(row) is not type(obj):
        raise TypeError(f"Row expected to be {type(obj).__name__}; got {type(row).__name__} instead")

    assert row.size == 1, f"Row must contain a single data point; instead, got {row.size}"

    # NOTE: 2026-03-08 22:19:12
    # using neo.Event.merge is enticing, but the code below ensures the row is
    # appended
    # return obj.merge(row)

    objTimes = obj.times
    rowTimes = row.times

    if isinstance(obj, (TriggerEvent, DataMark)):
        assert (row.type == obj.type), "Incompatible trigger event type"

    domainUnits = objTimes.units
    rowDomainUnits = rowTimes.units

    if rowDomainUnits != domainUnits:
        if not scq.unitsConvertible(rowDomainUnits, domainUnits):
            raise TypeError(f"Incompatible domain units between row ({rowDomainUnits}) and target ({domainUnits})")
        rowTimes = rowTimes.rescale(domainUnits)

    times = np.concatenate((objTimes, rowTimes), axis=0) * objTimes.units

    labels = np.concatenate((obj.labels, row.labels), axis=0)

    ret = type(obj)(times = times, labels = labels,
                     name = obj.name, description = obj.description,
                     file_origin = "",
                     array_annotations = obj.array_annotations,
                     **obj.annotations)

    if isinstance(obj, (DataMark, TriggerEvent)):
        ret.type = obj.type

    return ret

@_appendRow_.register(neo.AnalogSignal)
@_appendRow_.register(DataSignal)
def __appendRow__(obj: typing.Union[neo.AnalogSignal, DataSignal],
      row: typing.Union[np.ndarray, pq.Quantity],
      in_place=False) -> neo.AnalogSignal | DataSignal:
    if not isinstance(row, [pq.Quantity, np.ndarray]):
        raise TypeError(f"Row expected to be a Quantity or a numpy array; got {type(row).__name__} instead")

    if row.ndim == 0:
        if obj.shape[1] > 1:
            raise ValueError(f"Not enough data points; expected {obj.shape[1]}")

    elif row.ndim == 1:
        if row.size != obj.shape[1]:
            raise ValueError(f"Mismatch in data points; expected {obj.shape[1]}, got {row.size} instead")

    elif row.ndim > 2:
        raise ValueError(f"Unexpected row shape ({row.shape})")

    if isinstance(row, pq.Quantity) and row.units != obj.units:
        if not scq.unitsConvertible(row, obj):
            raise TypeError(f"Incompatible units: expecting {obj.units}; got {row.units} instead")

        row = row.rescale(obj.units)

    sampling_rate = obj.sampling_rate

    objData = obj.magnitude
    rowData = row.magnitude if isinstance(row, pq.Quantity) else row

    if rowData.ndim < 2:
        rowData = np.atleast_2d(rowData)

    newData = np.concatenate((objData, rowData), axis=0) * obj.units

    ret = type(obj)(newData, units = newData.units, t_start = obj.t_start,
                    sampling_rate = obj.sampling_rate,
                    name = obj.name, description = obj.description,
                    file_origin = "",
                    array_annotations = obj.array_annotations,
                    **obj.annotations)

    return ret

@_appendRow_.register(neo.SpikeTrain)
@_appendRow_.register(MarkTrain)
def __appendRow__(obj: typing.Union[neo.SpikeTrain, MarkTrain],
      row: typing.Union[neo.SpikeTrain, MarkTrain], in_place = False) -> typing.Union[neo.SpikeTrain, MarkTrain]:
    if not isinstance(row, type(obj)):
        raise TypeError(f"Row expected to be a {type(obj).__name__}; instead got a {type(row).__name__}")

    assert(row.size == 1), "Expecting exactly one timestamp"
    assert(row.left_sweep == obj.left_sweep), "Both argument must have the same 'left_sweep'"

    # NOTE: 2026-03-08 22:21:00 see NOTE: 2026-03-08 22:19:12
    # return obj.merge(row)

    times = obj.times
    waveforms = obj.waveforms

    time = row.times
    waves = row.waveforms

    if time.units != times.units:
        if not scq.unitsConvertible(time, times):
            raise TypeError(f"Incompatible domain units: row ({time.units}) vs target ({times.units})")

        time = time.rescale(times.units)

    newTimes = np.concatenate(
        (np.atleast_1d(times.magnitude),
         np.atleast_1d(time.magnitude)), axis=0) * times.units

    if waveforms is None:
        if isinstance(wave, np.ndarray):
            shape = (obj.size, ) + wave.shape[0:2]
            full_waveforms = np.concatenate((np.full(shape, np.nan), wave), axis=0)
        else:
            full_waveforms = None

    else:
        full_waveforms = np.concatenate((waveforms, wave), axis=0)

    t_stop = np.max(obj.t_stop, row.t_stop)
    t_start = np.min(obj.t_start, row.t_start)

    return neo.SpikeTrain(newTimes, t_stop, units = newTimes.units,
                          sampling_rate = obj.sampling_rate,
                          t_start = t_start,
                          waveforms = full_waveforms,
                          left_sweep = obj.left_sweep,
                          file_origin = "",
                          array_annotations = obj.array_annotations,
                          **obj.annotations)

@_appendRow_.register(TriggerProtocolList)
def __appendRow__(obj: TriggerProtocolList, row: TriggerProtocol, in_place: bool = False):
    if not isinstance(row, TriggerProtocol):
        raise TypeError(f"Cannot add {type(row).__name__}")

    if in_place:
        obj += row
        return obj

    else:
        ret = TriggerProtocolList(obj._items)
        ret += row
        return ret





