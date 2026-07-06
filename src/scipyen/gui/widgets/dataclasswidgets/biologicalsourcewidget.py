# -*- coding: utf-8 -*-
# $Id: biologicalsourcewidget.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""

import sys, os, typing, types, warnings, math, cmath # noqa
import numbers
import numpy as np
import quantities as pq
import pandas as pd
import neo
from tribool import Tribool
from functools import singledispatchmethod

import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, ) # noqa
from qtpy.QtCore import (Signal, Slot, Property,) # noqa
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
__has_qtdbus__ = False

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

    from qtpy import sip # noqa
    from qtpy.uic import loadUiType # noqa
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True

try:
    from qtpy import QtDBus # noqa
    __has_qtdbus__ = True
except:
    __has_qtdbus__ = False

from core.prog import scipywarn # noqa
from core import scipyendataclasses as sdc
from core import scipyen_quantities as scq
# from gui import guiutils, textviewer
from gui.widgets import small_widgets as smw
from gui.widgets.dataclasswidgets.dataclasswidget import DataClassWidget
from gui.workspacegui import WorkspaceGuiMixin
# from gui.widgets.datawidgetmixin import DataWidgetMixin
from iolib import pictio as pio

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

Ui_BiologicalSourceWidget, QWidget = loadUiType(
    os.path.join(__module_path__, "biologicalsourcewidget.ui")
    )

class BiologicalSourceWidget(Ui_BiologicalSourceWidget, DataClassWidget):
    _objectTypes_ = (sdc.BiologicalSource, )

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None,
                 obj: typing.Optional[sdc.BiologicalSource] = None,
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
            self._data_ = self._objectTypes_[0]()
        else:
            self._data_ = obj

        self._bioSourceTypeNames_ = list(sdc.BioSourceType.names())

        self._specimenTypes_ = [
            sdc.Organism,
            sdc.Organ,
            sdc.Tissue,
            sdc.Cell,
            sdc.NeuronCompartment,
            sdc.CellCompartment,
            sdc.ChemicalSynapse,
            sdc.UltrastructureElement,
            sdc.ChemicalSynapseUltrastructureElement,
            sdc.ScipyenDataclass,
            # sdc.BiologicalProduct,
        ]

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)

        self.dataExchangeWidget.dataType = type(self._data_)
        self.dataExchangeWidget.sig_requestDataExport.connect(self._slot_dataExportRequested)
        self.sig_dataExporting.connect(self.dataExchangeWidget.slot_exportData)
        self.dataExchangeWidget.sig_requestDataSave.connect(self._slot_dataSaveRequested)
        self.sig_dataSaving.connect(self.dataExchangeWidget.slot_saveData)
        self.dataExchangeWidget.sig_requestDataCopy.connect(self._slot_dataCopyRequested)
        self.sig_dataCopy.connect(self.dataExchangeWidget.slot_copyData)
        self.dataExchangeWidget.sig_requestNewObject.connect(self._slot_newObjectRequested)
        self.dataExchangeWidget.sig_dataLoaded.connect(self._slot_dataReceived)
        self.dataExchangeWidget.sig_dataImported.connect(self._slot_dataReceived)
        self.dataExchangeWidget.sig_symbolChanged.connect(self._slot_symbolChanged)

        self.nameDescriptionWidget.dataName = self._data_.name
        self.nameDescriptionWidget.dataDescription = self._data_.description
        self.nameDescriptionWidget.sig_nameChanged.connect(self._slot_dataNameChanged)
        self.nameDescriptionWidget.sig_descriptionChanged.connect(self._slot_dataDescriptionChanged)
        self.nameDescriptionWidget.sig_detailedViewRequest.connect(self._slot_viewDetails)
        self.sig_detailedView.connect(self.nameDescriptionWidget.slot_viewDetails)
        self.nameDescriptionWidget.sig_detailsChanged.connect(self._slot_detailsChanged)
        self.sig_valueChanged.connect(self.nameDescriptionWidget._slot_dataChanged)

        for text in self._bioSourceTypeNames_:
            self.bioSourceTypeComboBox.addItem(text)

        ndx = self._bioSourceTypeNames_.index(self._data_.sourceType.name)
        self.bioSourceTypeComboBox.setCurrentIndex(ndx)

        self.bioSourceTypeComboBox.currentIndexChanged.connect(self._slot_sourceTypeChanged)

        self.specimenWidget = None

        self.showSpecimenToolButton.clicked.connect(self._slot_showSpecimen)


    @Slot(int)
    def _slot_sourceTypeChanged(self, val:int):
        name = self._bioSourceTypeNames_[val]
        self._data_.sourceType = sdc.BioSourceType[name]

        self.sig_valueChanged.emit(self._data_)

    @Slot()
    def _slot_showSpecimen(self):
        if isinstance(self._data_.specimen, self._specimenTypes_):
            self._specimenWidget_ = self._createWidget_(self._data_.specimen)
            self._specimenWidget_.show()

    @singledispatchmethod
    def _createWidget_(self, obj):
        raise NotImplementedError(f"Objects of type {type(obj)} are not supported")

    @_createWidget_.register(sdc.Organism)
    def __createWidget__(self, obj: sdc.Organism):
        from gui.widgets.dataclasswidgets.organismwidget import OrganismWidget
        return OrganismWidget(obj)

    @_createWidget_.register(sdc.Organ)
    @_createWidget_.register(sdc.Tissue)
    def __createWidget__(self, obj: sdc.Organ): # noqa
        from gui.widgets.dataclasswidgets.organtissuewidgets import OrganWidget
        return OrganWidget(obj)

    @_createWidget_.register(sdc.NervousSystem)
    def __createWidget__(self, obj: sdc.NervousSystem): # noqa
        from gui.widgets.dataclasswidgets.nervoussystemwidget import NervousSystemWidget
        return NervousSystemWidget(obj)

    @_createWidget_.register(sdc.Neuron)
    def __createWidget__(self, obj: sdc.Neuron): # noqa
        from gui.widgets.dataclasswidgets.cellwidget import NeuronWidget
        return NeuronWidget(obj)

    @_createWidget_.register(sdc.Cell)
    def __createWidget__(self, obj: sdc.Cell): # noqa
        from gui.widgets.dataclasswidgets.cellwidget import CellWidget
        return CellWidget(obj)

    @_createWidget_.register(sdc.NeuronCompartment)
    @_createWidget_.register(sdc.CellCompartment)
    @_createWidget_.register(sdc.ChemicalSynapseUltrastructureElement)
    @_createWidget_.register(sdc.UltrastructureElement)
    def __createWidget__(self, obj: sdc.CellCompartment): # noqa
        from gui.widgets.dataclasswidgets.cellcompartmentwidget import CellCompartmentWidget
        return CellCompartmentWidget(obj)

    @_createWidget_.register(sdc.ChemicalSynapse)
    def __createWidget__(self, obj: sdc.ChemicalSynapse): # noqa
        from gui.widgets.dataclasswidgets.chemicalsynapsewidget import ChemicalSynapseWidget
        return ChemicalSynapseWidget(obj)

    @_createWidget_.register(sdc.ScipyenDataClass)
    def __createWidget__(self, obj: sdc.ScipyenDataClass): # noqa
        from gui.widgets.dataclasswidgets.chemicalsynapsewidget import ChemicalSynapseWidget
        return ChemicalSynapseWidget(obj)










