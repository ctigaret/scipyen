# -*- coding: utf-8 -*-
# $Id: cellwidget.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""

import sys, os, typing, types, warnings, math, cmath, datetime # noqa
# from functools import singledispatchmethod
# import numbers
# import dataclasses
# import numpy as np
# import quantities as pq
# import pandas as pd
# import neo
# from tribool import Tribool

# import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, )
from qtpy.QtCore import (Signal, Slot)#, Property,)
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6 # noqa
    from PySide6 import Shiboken # noqa
    # from PySide6.QtCore import (Signal, Slot, Property,)
    from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True

    # from qtpy import sip
    from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True


from core.prog import scipywarn
# from core.sysutils import adapt_ui_path

# import core.bgbridge as bgbridge

from core import scipyen_quantities as scq
# from core import strutils
# from core.datatypes import UnitTypes, GENOTYPES

# from core import workspacefunctions as wsf
# from gui.widgets.small_widgets import QuantitySpinBox, QuantityChooserWidget
# from gui.widgets.datatreeview import DataTreeView

# from core.prog import scipywarn
from core import scipyendataclasses as sdc
# from core import scipyen_quantities as scq
# from gui import guiutils, textviewer, datatreeviewer
# from gui.textviewer import TextViewer
# from gui.widgets import small_widgets as smw
from gui.widgets.dataclasswidgets.dataclasswidget import DataClassWidget
# from gui.workspacegui import WorkspaceGuiMixin
# from iolib import pictio as pio

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

Ui_CellWidget, QWidget = loadUiType(
    os.path.join(__module_path__, "cellwidget.ui")
    )

Ui_NeuronWidget, QWidget = loadUiType(
    os.path.join(__module_path__, "neuronwidget.ui")
    )

class CellWidget(Ui_CellWidget, DataClassWidget):
    _objectTypes_ = (sdc.Cell, )

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None,
                 obj: typing.Optional[sdc.CellCompartment] = None,
                 **kwargs):

        if isinstance(parent, self._objectTypes_):
            obj_ = parent
            if isinstance(obj, QtWidgets.QWidget):
                parent = obj
            else:
                parent = None

            obj = obj_

        if not isinstance(obj, self._objectTypes_):
            obj = sdc.Cell()

        self._data_ = obj

        DataClassWidget.__init__(self, parent=parent, **kwargs)

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)

        super()._configureUI_()

        # self.dataExchangeWidget.setValue(self._data_)
        # self.dataExchangeWidget.sig_requestDataExport.connect(self._slot_dataExportRequested)
        # self.sig_dataExporting.connect(self.dataExchangeWidget.slot_exportData)
        # self.dataExchangeWidget.sig_requestDataSave.connect(self._slot_dataSaveRequested)
        # self.sig_dataSaving.connect(self.dataExchangeWidget.slot_saveData)
        # self.dataExchangeWidget.sig_requestDataCopy.connect(self._slot_dataCopyRequested)
        # self.sig_dataCopy.connect(self.dataExchangeWidget.slot_copyData)
        #
        # self.dataExchangeWidget.sig_requestNewObject.connect(self._slot_newObjectRequested)
        #
        # self.dataExchangeWidget.sig_dataLoaded.connect(self._slot_dataReceived)
        # self.dataExchangeWidget.sig_dataImported.connect(self._slot_dataReceived)
        #
        # self.nameDescriptionWidget.dataName = self._data_.name
        # self.nameDescriptionWidget.dataDescription = self._data_.description
        # self.nameDescriptionWidget.sig_nameChanged.connect(self._slot_dataNameChanged)
        # self.nameDescriptionWidget.sig_descriptionChanged.connect(self._slot_dataDescriptionChanged)
        # self.nameDescriptionWidget.sig_detailedViewRequest.connect(self._slot_viewDetails)
        # self.sig_detailedView.connect(self.nameDescriptionWidget.slot_viewDetails)
        # self.nameDescriptionWidget.sig_detailsChanged.connect(self._slot_detailsChanged)
        # self.sig_valueChanged.connect(self.nameDescriptionWidget._slot_dataChanged)
        # self.dataExchangeWidget.sig_symbolChanged.connect(self._slot_symbolChanged)

        self.editParentToolButton.clicked.connect(self._slot_editParent)

        self.cellTypeNameEdit.setText(f"{self._data_.cellType}")

        if isinstance(self._data_, sdc.Neuron):
            self.cellTypeNameEdit.setEnabled(False)
        else:
            self.cellTypeNameEdit.textChanged.connect(self._slot_cellTypeChanged)
        self.cellSubTypeNameEdit.setText(f"{self._data_.cellSubType}")
        self.cellSubTypeNameEdit.textChanged.connect(self._slot_cellSubTypeChanged)

    def value(self) -> sdc.Cell:
        return self._data_

    def setValue(self, val: sdc.Cell, *args, **kwargs):
        if not isinstance(val, self._objectTypes_):
            raise TypeError(f"Expecting one of  {self._objectTypes_}; instead, got a {type(val).__name__}")

        self._data_ = val
        self._isAttribute_ = kwargs.get("isAttribute", False)

        sigBlockers = list(map(lambda w: QtCore.QSignalBlocker(w),
                               (
                                   self.dataExchangeWidget,
                                   self.nameDescriptionWidget,
                                   self.editParentToolButton,
                                   self.cellTypeNameEdit,
                                   self.cellSubTypeNameEdit
                                )
                               ))

        self.dataExchangeWidget.setValue(self._data_)

        self.nameDescriptionWidget.dataName = self._data_.name
        self.nameDescriptionWidget.dataDescription = self._data_.description

        if not isinstance(self._data_, sdc.Neuron):
            self.cellTypeNameEdit.setText(f"{self._data_.cellType}")
        self.cellSubTypeNameEdit.setText(f"{self._data_.cellSubType}")

        self.sig_valueChanged.emit(self._data_)

    @Slot(str)
    def _slot_cellTypeChanged(self, val: str):
        self._data_.cellType = val

    @Slot(str)
    def _slot_cellSubTypeChanged(self, val: str):
        self._data_.cellSubType = val

class NeuronWidget(Ui_NeuronWidget, DataClassWidget):
    _objectTypes_ = (sdc.Neuron,)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None,
                 obj: typing.Optional[sdc.CellCompartment] = None,
                 **kwargs):

        if isinstance(parent, self._objectTypes_):
            obj_ = parent
            if isinstance(obj, QtWidgets.QWidget):
                parent = obj
            else:
                parent = None

            obj = obj_

        self._entityTypeNames_ = list(sdc.NeuronType.names())

        if not isinstance(obj, self._objectTypes_):
            obj = sdc.Neuron()

        self._data_ = obj

        DataClassWidget.__init__(self, parent=parent, **kwargs)

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)

        super()._configureUI_()

        # self.dataExchangeWidget.setValue(self._data_)
        # self.dataExchangeWidget.sig_requestDataExport.connect(self._slot_dataExportRequested)
        # self.sig_dataExporting.connect(self.dataExchangeWidget.slot_exportData)
        # self.dataExchangeWidget.sig_requestDataSave.connect(self._slot_dataSaveRequested)
        # self.sig_dataSaving.connect(self.dataExchangeWidget.slot_saveData)
        # self.dataExchangeWidget.sig_requestDataCopy.connect(self._slot_dataCopyRequested)
        # self.sig_dataCopy.connect(self.dataExchangeWidget.slot_copyData)
        #
        # self.dataExchangeWidget.sig_requestNewObject.connect(self._slot_newObjectRequested)
        #
        # self.dataExchangeWidget.sig_dataLoaded.connect(self._slot_dataReceived)
        # self.dataExchangeWidget.sig_dataImported.connect(self._slot_dataReceived)
        #
        # self.nameDescriptionWidget.dataName = self._data_.name
        # self.nameDescriptionWidget.dataDescription = self._data_.description
        # self.nameDescriptionWidget.sig_nameChanged.connect(self._slot_dataNameChanged)
        # self.nameDescriptionWidget.sig_descriptionChanged.connect(self._slot_dataDescriptionChanged)
        # self.nameDescriptionWidget.sig_detailedViewRequest.connect(self._slot_viewDetails)
        # self.sig_detailedView.connect(self.nameDescriptionWidget.slot_viewDetails)
        # self.nameDescriptionWidget.sig_detailsChanged.connect(self._slot_detailsChanged)
        # self.sig_valueChanged.connect(self.nameDescriptionWidget._slot_dataChanged)
        # self.dataExchangeWidget.sig_symbolChanged.connect(self._slot_symbolChanged)

        self.editParentToolButton.clicked.connect(self._slot_editParent)

        for s in self._entityTypeNames_:
            self.neuronTypeComboBox.addItem(s)

        ndx = self._entityTypeNames_.index(self._data_.cellSubType.name)
        self.neuronTypeComboBox.setCurrentIndex(ndx)
        self.neuronTypeComboBox.currentIndexChanged.connect(self._slot_neuronTypeChanged)

    def value(self) -> sdc.Neuron:
        return self._data_

    def setValue(self, val: sdc.Neuron, *args, **kwargs):
        if not isinstance(val, self._objectTypes_):
            raise TypeError(f"Expecting one of  {self._objectTypes_}; instead, got a {type(val).__name__}")

        self._data_ = val
        self._isAttribute_ = kwargs.get("isAttribute", False)

        sigBlockers = list(map(lambda w: QtCore.QSignalBlocker(w),
                               (
                                   self.dataExchangeWidget,
                                   self.nameDescriptionWidget,
                                   self.editParentToolButton,
                                   self.neuronTypeComboBox,
                                )
                               ))

        self.dataExchangeWidget.setValue(self._data_)

        self.nameDescriptionWidget.dataName = self._data_.name
        self.nameDescriptionWidget.dataDescription = self._data_.description

        ndx = self._entityTypeNames_.index(self._data_.cellSubType.name)
        self.neuronTypeComboBox.setCurrentIndex(ndx)

        self.sig_valueChanged.emit(self._data_)

    @Slot(int)
    def _slot_neuronTypeChanged(self, val: int):
        self._data_.cellSubType = sdc.NeuronType[self._entityTypeNames_[val]]
        self.sig_valueChanged.emit(self._data_)

    @Slot()
    def _slot_detailsChanged(self):
        r"""Overrides DataClassWidget._slot_detailsChanged.
    Captures changes in the data tree viewer (details viewer)
    """
        # print(f"{self.__class__.__name__}._slot_detailsChanged")
        sigBlockers = list(map(lambda w: QtCore.QSignalBlocker(w),
                               (self.nameDescriptionWidget,
                                self.dataExchangeWidget,
                                self.neuronTypeComboBox
                                )))

        self.nameDescriptionWidget.dataName = self._data_.name
        self.nameDescriptionWidget.dataDescription = self._data_.description

        ndx = self._entityTypeNames_.index(self._data_.cellSubType.name)
        self.neuronTypeComboBox.setCurrentIndex(ndx)

