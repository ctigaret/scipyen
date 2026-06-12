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
from collections import deque
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
from neo.core.objectlist import ObjectList as NeoObjectList
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
from core.triggerprotocols import TriggerProtocolList
from core.datazone import DataZone

import core.datasignal
from core.datasignal import (DataSignal, IrregularlySampledDataSignal,)
from core.datatypes import array_slice
from core.sysutils import adapt_ui_path
from core import scipyen_quantities as scq

#### END pict.core modules

#### BEGIN pict.gui modules
# from gui.scipyenviewer import ScipyenViewer #, ScipyenFrameViewer
from gui import (quickdialog, guiutils) # noqa
from gui.delegates import PythonItemDelegate
# from gui.widgets.tabledataview import TableDataView
from gui.itemmodels.tabulardatamodel import TabularDataModel
from gui.itemmodels.roles import * # noqa
# from gui import resources_rc
# from gui import icons_rc
#### END pict.gui modules

#### BEGIN pict.iolib modules
import iolib.pictio as pio
#### END pict.iolib modules

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__ui_path__ = adapt_ui_path(__module_path__, "tableeditorwidget.ui")

__module_name__ = os.path.splitext(os.path.basename(__file__))[0]

TabularType = typing.Union[pd.DataFrame, pd.Series, neo.core.baseneo.BaseNeo,
                           neo.AnalogSignal, neo.IrregularlySampledSignal,
                           neo.Epoch, neo.Event, neo.SpikeTrain,
                           DataSignal, IrregularlySampledDataSignal,
                           TriggerEvent, TriggerProtocolList,
                           np.ndarray, vigra.VigraArray,
                           vigra.filters.Kernel1D, vigra.filters.Kernel2D,
                           NeoObjectList, list, tuple, deque]

Ui_TableEditorWidget, QWidget = loadUiType(__ui_path__)

class TableEditorWidget(QWidget, Ui_TableEditorWidget):
    r"""Uses TableDataView as the UI"""
    # TODO 2019-11-01 22:57:01
    # finish implementing all these
    viewer_for_types = (pd.DataFrame, pd.Series, neo.core.baseneo.BaseNeo,
                       neo.AnalogSignal, neo.IrregularlySampledSignal,
                       neo.Epoch, neo.Event, neo.SpikeTrain,
                       DataSignal, IrregularlySampledDataSignal,
                       TriggerEvent, TriggerProtocolList,
                       np.ndarray, vigra.VigraArray, vigra.filters.Kernel1D, vigra.filters.Kernel2D)

    view_action_name = "Table"

    sig_selectionChanged = Signal(name="sig_selectionChanged")
    sig_dataChanged = Signal(name="sig_dataChanged")
    sig_valueChanged = sig_dataChanged

    def __init__(self, parent:typing.Optional[QtWidgets.QMainWindow]=None,
                 readOnly:bool=True, enforceFloat:bool=False,
                 enforceReadOnly:bool=False) -> None:
        super().__init__(parent=parent)
        # FIXME: 2025-11-23 09:58:38 next line is DEPRECATED
        self._is_vigra_filter_kernel_:bool = False # needed in future implementations of editing functionality
        self._selectedIndexes_ = list()
        self._readOnly_:bool = readOnly is True
        self._enforceFloat_:bool = enforceFloat is True
        self._enforceReadOnly_:bool = False

        # NOTE: 2021-10-18 09:32:45
        # ### BEGIN keep this  - you may re-enable the possibility to use other custom tabular
        # data models

        #if model is None:
            #self._dataModel_ = TabularDataModel(parent=self)

        #else:
            #self._dataModel_ = model
        # ### END keep this ...

        self._dataModel_ = TabularDataModel(parent=self)

        self._configureUI_()

        self._dataModel_.sig_modelPopulated.connect(self._slot_modelPopulated)

        self._defaultItemDelegate_ = self.tableView.itemDelegate()
        self._editItemDelegate_ = PythonItemDelegate(parent=self, enforceFloat = self._enforceFloat_)

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

    def setValue(self: typing.Self, value: TabularType, *args, **kwargs):
        self.setData(value, *args, **kwargs)

    def value(self):
        return self._data_

    def _slot_modelPopulated(self):
        # print(f"{self.__class__.__name__}._slot_modelPopulated")
        if isinstance(self._dataModel_, TabularDataModel):
            if (isinstance(self._dataModel_._modelDataRowIndexName_, str) and
                len(self._dataModel_._modelDataRowIndexName_.strip())
                ):
                self.tableView.setCornerButtonEnabled(True)
                # print(f"{self.__class__.__name__}.setData: corner label -> {self._dataModel_._modelDataRowIndexName_}")
                self.tableView.setCornerLabel(self._dataModel_._modelDataRowIndexName_)


    def setData(self, data: TabularType, *args, **kwargs):
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
        # self.tableView.reset()
        # oldColumnCount = self.tableView.horizontalHeader().count()

        if (getattr(data, "shape", (0,0))[0] > 10
            or (isinstance(data, (typing.Sequence, NeoObjectList)) and len(data) > 10)
            ):
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
            self._dataModel_.populateModel(self._data_[array_slice(self._data_, {self._slicingAxis_:self._currentSlice_})])

            self.prevSliceToolbutton.setEnabled(True)
            self.nextSliceToolButton.setEnabled(True)

        else:
            self.prevSliceToolbutton.setEnabled(False)
            self.nextSliceToolButton.setEnabled(False)
            self._dataModel_.populateModel(self._data_)

        # NOTE: 2025-11-23 19:53:14 FIXME 2026-06-10 07:38:59
        # to show bool cell data as checkboxes
        for row in range(self._dataModel_.rowCount()):
            for col in range(self._dataModel_.columnCount()):
                index = self._dataModel_.index(row, col)
                indexData = index.data(ObjectDataRole)
                if indexData is None:
                    indexData = index.data(QtCore.Qt.EditRole)
                if isinstance(indexData, bool):
                    self.tableView.openPersistentEditor(index)

                if hasattr(self._dataModel_, "_modelDataColumnHeaders_"):
                    if self._dataModel_._modelDataColumnHeaders_[col].lower() == "edit":
                        self.tableView.openPersistentEditor(index)

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

                    self._dataModel_.populateModel(self._data_[array_slice(self._data_, {self._slicingAxis_:self._currentSlice_})])

    def clear(self):
        self._dataModel_ = TabularDataModel(parent=self)
        self.tableView.setModel(self._dataModel_)

    # @property
    # def model(self) -> QtCore.QAbstractTableModel:
    #     r"""The underlying QtCore.QAbstractTableModel or type derived from it"""
    #     self._dataModel_ = self.tableView.model()
    #     return self._dataModel_
    #
    # @model.setter
    # def model(self, md:QtCore.QAbstractTableModel|None):
    #     self._dataModel_ = md
    #     self.tableView.setModel(self._dataModel_)
    #     if hasattr(self._dataModel_, "sig_modelDataChanged") and isinstance(type(self._dataModel_).sig_modelDataChanged, Signal):
    #         self._dataModel_.sig_modelDataChanged.connect(self.sig_dataChanged) # connect signal to signal directly

    # @property
    # def dataModel(self) -> QtCore.QAbstractTableModel:
    #     r"""Same as self.model"""
    #     return self.model
    #
    # @dataModel.setter
    # def dataModel(self, val: QtCore.QAbstractTableModel):
    #     self.model = val


    @property
    def enforceFloat(self) -> bool:
        return self._enforceFloat_

    @enforceFloat.setter
    def enforceFloat(self, val:bool):
        self._enforceFloat_ = val == True
        if not self.readOnly and isinstance(self.tableView.itemDelegate(), PythonItemDelegate):
            self.tableView.itemDelegate().enforceFloat = self._enforceFloat_

    @property
    def enforceReadOnly(self) -> bool:
        return self._enforceReadOnly_

    @enforceReadOnly.setter
    def enforceReadOnly(self, val:bool):
        self._enforceReadOnly_ = val == True

        sigBlocker = QtCore.QSignalBlocker(self.setEditableToolButton)
        if self._enforceReadOnly_:
            self.readOnly = True
            self.setEditableToolButton.setChecked(False)
            self.setEditableToolButton.setEnabled(False)
            self.setEditableToolButton.setIcon(QtGui.QIcon.fromTheme("object-locked"))
            self.setEditableToolButton.setToolTip("Editing disabled; set enforceReadOnly to True to enable this switch then then toggle to enable")


    @property
    def readOnly(self):
        return self._readOnly_
        # return self.tableView.editTriggers() == QtWidgets.QAbstractItemView.NoEditTriggers

    @readOnly.setter
    def readOnly(self, val:bool):
        self._readOnly_ = val == True
        signalBlocker = QtCore.QSignalBlocker(self.setEditableToolButton)
        if self._readOnly_:
            self.tableView.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self.tableView.setItemDelegate(self._defaultItemDelegate_)
            # NOTE:2026-03-08 09:38:02
            # don't change these: these depend on the type of the data represented
            # in the model
            # self.tableView.model.canAlterRows = False
            # self.tableVire.model.canAlterColumns = False
            self.setEditableToolButton.setIcon(QtGui.QIcon.fromTheme("object-locked"))
            self.setEditableToolButton.setToolTip("Editing disabled; toggle to enable")
        else:
            # NOTE:2026-03-08 09:38:02
            # don't change these: these depend on the type of the data represented
            # in the model
            # self.tableView.model.canAlterRows = True
            # self.tableVire.model.canAlterColumns = True
            self.tableView.setEditTriggers(self._defaultEditTriggers_)
            # self._editItemDelegate_.immutableRows = self.tableView.model().immutableRows
            # self._editItemDelegate_.immutableColumns = self.tableView.model().immutableColumns
            # self._editItemDelegate_.jointImmutability = self.tableView.model().jointImmutability
            self.tableView.setItemDelegate(self._editItemDelegate_)

            self.setEditableToolButton.setIcon(QtGui.QIcon.fromTheme("object-unlocked"))
            self.setEditableToolButton.setToolTip("Editing enabled; toggle to disable")

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

        if self._readOnly_:
            self.setEditableToolButton.setChecked(False)
            self.setEditableToolButton.setIcon(QtGui.QIcon.fromTheme("object-locked"))
            self.setEditableToolButton.setToolTip("Editing disabled; toggle to enable")

        else:
            self.setEditableToolButton.setChecked(True)
            self.setEditableToolButton.setIcon(QtGui.QIcon.fromTheme("object-unlocked"))
            self.setEditableToolButton.setToolTip("Editing enabled; toggle to disable")

        self.setEditableToolButton.toggled.connect(self._slot_setEditable)

    @Slot(bool)
    def _slot_setEditable(self, value:bool):
        self.readOnly = not value

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

    # @Slot()
    # def _slot_sendToExternalEditor(self):
    #     # NOTE: 2026-06-11 09:51:56
    #     # this is to update the external editor when parts of the row have changed
    #     # BUG 2026-06-11 10:39:20 FIXME
    #     from core import datatypes
    #     if self._readOnly_:
    #         return
    #
    #     model = self.tableView.model()
    #
    #     if (
    #         # hasattr(model, "_modelData_") and datatypes.is_iterable(model._modelData_)
    #         hasattr(self._editItemDelegate_, "_currentModelIndex_")
    #         and isinstance(self._editItemDelegate_._currentModelIndex_, QtCore.QModelIndex)
    #         and hasattr(self._editItemDelegate_, "_externalDataEditor_")
    #         and isinstance(self._editItemDelegate_._externalDataEditor_, QtWidgets.QWidget)
    #         and hasattr(self._editItemDelegate_._externalDataEditor_, "setValue")
    #         ):
    #
    #         # print(f"{self.__class__.__name__}._slot_sendToExternalEditor: self._currentModelIndex_ = {self._currentModelIndex_}, self._externalDataEditor_: {self._externalDataEditor_}")
    #         model = self._editItemDelegate_._currentModelIndex_.model()
    #         # print(f"\t-> had _modelData_: {hasattr(model, '_modelData_')}, is iterable({datatypes.is_iterable(model._modelData_)})")
    #         if (
    #             hasattr(model, "_modelData_")
    #             and datatypes.is_iterable(model._modelData_)
    #             ):
    #             row = self._editItemDelegate_._currentModelIndex_.row()
    #             # print(model._modelData_[row])
    #             self._editItemDelegate_._externalDataEditor_.setValue(model._modelData_[row])


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
    def slot_insertRow(self):
        model = self.tableView.model()
        if not isinstance(model, TabularDataModel) or not model.canAlterRows:
            return

        modelIndexes = self.tableView.selectedIndexes()
        if len(modelIndexes) == 0:
            row = model.rowCount()
        else:
            # insert a row just below the selection
            row = modelIndexes[-1].row()

        if row < (model.rowCount()-1):
            row = row+1

        if model.insertRow(row, None, QtCore.QModelIndex()):
            self._data_ = model._modelData_
            self.sig_dataChanged.emit()


    @Slot()
    def slot_removeRow(self):
        model = self.tableView.model()
        if not isinstance(model, TabularDataModel) or not model.canAlterRows:
            return

        modelIndexes = self.tableView.selectedIndexes()
        if len(modelIndexes) == 0:
            return

        # remove the last row of the selection
        row = modelIndexes[-1].row()
        print(f"{self.__class__.__name__}.slot_removeRow -> row = {row}")
        if model.removeRow(row, QtCore.QModelIndex()):
            self._data_ = model._modelData_
            self.sig_dataChanged.emit()

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
        copySelectedAction.setIcon(guiutils.getIcon("edit-copy"))
        copySelectedAction.triggered.connect(self.slot_copySelection)

        model = self.tableView.model()
        if isinstance(model, TabularDataModel) and model.canAlterRows:
            insertRowAction = cm.addAction("Insert row")
            insertRowAction.setIcon(guiutils.getIcon("insert-table-row"))
            insertRowAction.triggered.connect(self.slot_insertRow)

            removeRowAction = cm.addAction("Remove row")
            removeRowAction.setIcon(guiutils.getIcon("delete-table-row"))
            removeRowAction.triggered.connect(self.slot_removeRow)

        cm.popup(self.tableView.mapToGlobal(pos), copySelectedAction)
