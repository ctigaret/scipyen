# -*- coding: utf-8 -*-
# $Id: chemicalsynapsewidget.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""

import sys, os, typing, types, warnings, math, cmath, datetime # noqa
from functools import singledispatchmethod
import numbers
import dataclasses
import numpy as np
import quantities as pq
import pandas as pd
import neo
from tribool import Tribool

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


from core.prog import safewrapper, scipywarn, print_styled
from core.sysutils import adapt_ui_path

import core.bgbridge as bgbridge

from core import scipyen_quantities as scq
from core import strutils
from core.datatypes import UnitTypes, GENOTYPES

from core import workspacefunctions as wsf
from gui.widgets.small_widgets import QuantitySpinBox, QuantityChooserWidget
from gui.widgets.datatreeview import DataTreeView

from core.prog import scipywarn # noqa
from core import scipyendataclasses as sdc
from core import scipyen_quantities as scq
from gui import guiutils, textviewer, datatreeviewer
from gui.textviewer import TextViewer
from gui.widgets import small_widgets as smw
from gui.widgets.dataclasswidgets.dataclasswidget import DataClassWidget
from gui.workspacegui import WorkspaceGuiMixin
from iolib import pictio as pio

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

Ui_ChemicalSynapseWidget, QWidget - loadUiType(
    os.path.join(__module_path__, "chemicalsynapsewidget.ui")
    )

class ChemicalSynapseWidget(Ui_ChemicalSynapseWidget, DataClassWidget):
    sig_valueChanged = Signal(object, name="sig_valueChanged")
    sig_dataSaving = Signal(object, name="sig_dataSaving")
    sig_dataExporting = Signal(object, name="sig_dataExporting")
    sig_dataCopy = Signal(object, name="sig_dataCopy")

    _objectTypes_ = (sdc.ChemicalSynapse, )

    def __init__(self, , parent: typing.Optional[QtWidgets.QWidget] = None,
                 obj: typing.Optional[sdc.CellCompartment] = None,
                 **kwargs):

        if isinstance(parent, self._objectTypes_):
            obj_ = parent
            if isinstance(obj, QtWidgets.QWidget):
                parent = obj
            else:
                parent = None

            obj = obj_

        DataClassWidget.__init__(self, parent=parent)

        if not isinstance(obj, self._objectTypes_):
            obj = sdc.ChemicalSynapse()

        self._data_ = obj

        self._morphoTypes_ = list(sdc.ChemicalSynapseMorphologicalType.names())

        self._functionalTypes_ = list(sdc.ChemicalSynapseFunctionalType.names())

        self._transmitters_ = list(sdc.Neurotrasmitters.names())

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)
        self.dataExchangeWidget.setValue(self._data_)
        self.dataExchangeWidget.sig_requestDataExport.connect(self._slot_dataExportRequested)
        self.sig_dataExporting.connect(self.dataExchangeWidget.slot_exportData)
        self.dataExchangeWidget.sig_requestDataSave.connect(self._slot_dataSaveRequested)
        self.sig_dataSaving.connect(self.dataExchangeWidget.slot_saveData)
        self.dataExchangeWidget.sig_requestDataCopy.connect(self._slot_dataCopyRequested)
        self.sig_dataCopy.connect(self.dataExchangeWidget.slot_copyData)

        self.dataExchangeWidget.sig_requestNewObject.connect(self._slot_newObjectRequested)

        self.dataExchangeWidget.sig_dataLoaded.connect(self._slot_dataReceived)
        self.dataExchangeWidget.sig_dataImported.connect(self._slot_dataReceived)

        self.nameDescriptionWidget.dataName = self._data_.name
        self.nameDescriptionWidget.dataDescription = self._data_.description
        self.nameDescriptionWidget.sig_nameChanged.connect(self._slot_dataNameChanged)
        self.nameDescriptionWidget.sig_descriptionChanged.connect(self._slot_dataDescriptionChanged)
        self.nameDescriptionWidget.sig_detailedViewRequest.connect(self._slot_viewDetails)
        self.sig_detailedView.connect(self.nameDescriptionWidget.slot_viewDetails)

        for t in self._morphoTypes_:
            self.synapseMorhpologicalTypeComboBox.addItem(t)
        ndx = self._morphoTypes_.index(self._data_.morphologicalType.name)
        self.synapseMorhpologicalTypeComboBox.setCurrentIndex(ndx)
        self.synapseMorhpologicalTypeComboBox.currentIndexChanged.connect(self._slot_morphologicalTypeChanged)

        for t in self._functionalTypes_:
            self.synapseFunctionalTypeComboBox.addItem(t)
        ndx = self._functionalTypes_.index(self._data_.functionalType.name)
        self.synapseFunctionalTypeComboBox.setCurrentIndex(ndx)
        self.synapseFunctionalTypeComboBox.currentIndexChanged.connect(self._slot_functionalTypeChanged)

        for t in self._transmitters_:
            self.neurotransmitterComboBox.addItem(t)
        ndx = self._transmitters_.index(self._data_.transmitter)
        self.neurotransmitterComboBox.setCurrentIndex(ndx)
        self.neurotransmitterComboBox.currentIndexChanged.connect(self._slot_transmitterChanged)

        self.retrogradeCheckBox.setChecked(self._data_.retrograde is True)
        self.retrogradeCheckBox.toggled.connect(self._slot_retrogradeChanged)

        self.presynapticCompartmentWidget.sig_valueChanged.connect(self._slot_presynaptiChanged)
        self.postsynapticCompartmentWidget.sig_valueChanged.connect(self._slot_postsynapticChanged)

    @Slot(int)
    def _slot_morphologicalTypeChanged(self, val:int):
        self._data_.morphologicalType = sdc.ChemicalSynapseMorphologicalType[self._morphoTypes_[val]]
        self.sig_valueChanged.emit(self._data_)

    @Slot(int)
    def _slot_functionalTypeChanged(self, val: int):
        self._data_.functionalType = sdc.ChemicalSynapseFunctionalType[self._functionalTypes_[val]]
        self.sig_valueChanged.emit(self._data_)

    @Slot(int)
    def _slot_transmitterChanged(self, val: int):
        self._data_.transmitter = sdc.Neurotrasmitters[self._transmitters_[val]]
        self.sig_valueChanged.emit(self._data_)

    @Slot(bool)
    def _slot_retrogradeChanged(self, val: bool):
        self._data_.retrograde = val is True
        self.sig_valueChanged.emit(self._data_)

    @Slot(object)
    def _slot_presynaptiChanged(self, val):
        self._data_.presynaptic = val
        self.sig_valueChanged.emit(self._data_)

    @Slot(object)
    def _slot_postsynapticChanged(self, val):
        self._data_.postsynaptic = val
        self.sig_valueChanged.emit(self._data_)

    # @Slot()
    # def _slot_viewDetails(self):
    #     if not isinstance(self._data_, self._objectTypes_):
    #         return
    #     varName = self.dataExchangeWidget.varName
    #     self.sig_detailedView.emit(self._data_, varName)





