# -*- coding: utf-8 -*-
# $Id: organismwidget.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""

import sys, os, typing, types, warnings, math, cmath # noqa
# import numbers
# import numpy as np
# import quantities as pq
import pandas as pd
# import neo
# from tribool import Tribool

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
from core import taxonbridge
from gui import datatreeviewer
from gui.widgets import small_widgets as smw
from gui.widgets.dataclasswidgets.dataclasswidget import DataClassWidget
from gui.workspacegui import WorkspaceGuiMixin
# from gui.widgets.datawidgetmixin import DataWidgetMixin

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

Ui_OrganismWidget, QWidget = loadUiType(
    os.path.join(__module_path__, "organismwidget.ui")
    )

class OrganismWidget(Ui_OrganismWidget, DataClassWidget):
    _objectTypes_ = (sdc.Organism, )

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None,
                 obj: typing.Optional[sdc.Biometrics] = None,
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
            self._data_ =  self._objectTypes_[0]()
        else:
            self._data_ = obj

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)

        self._taxonDetailsViewer_ = None

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


        taxon = self._data_.taxon
        if taxonbridge.hasTaxoniq and isinstance(taxon, taxonbridge.Taxon):
            taxon_name = taxon.scientific_name
            common_name = f"{taxon.common_name}, (species: {taxon_name})"
        elif isinstance(taxon,str):
            taxon_name = taxon
            common_name = taxon

        else:
            taxon_name = f"{pd.NA}"
            common_name = f"{pd.NA}"


        self.taxonSpeciesLineEdit.setText(taxon_name)
        self.taxonSpeciesLineEdit.setToolTip(common_name)
        self.taxonSpeciesLineEdit.sig_enterPressed.connect(self._slot_selectTaxon)

        if taxonbridge.hasTaxoniq and isinstance(taxon, taxonbridge.Taxon):
            self.taxonDetailsToolButton.clicked.connect(self._slot_showTaxonDetails)
        else:
            self.taxonDetailsToolButton.setEnabled(False)

        self.subSpeciesLineEdit.setText(f"{self._data_.subspecies}")
        self.subSpeciesLineEdit.sig_enterPressed.connect(self._slot_setSubSpecies)
        self.strainLineEdit.setText(f"{self._data_.strain}")
        self.strainLineEdit.sig_enterPressed.connect(self._slot_setStrain)
        self.facilityIDLineEdit.setText(f"{self._data_.ID}")
        self.facilityIDLineEdit.sig_enterPressed.connect(self._slot_setFacilityID)

        self.biometricsWidget.setValue(self._data_.biometrics)

    def setTaxon(self, value):
        if isinstance(val, taxonbridge.Taxon):
            self._data_.taxon = value

        elif isinstance(value, str) or value in (None, datalasses.MISSING, pd.NA):
            if taxonbridge.hasTaxoniq and isinstance(value, str):
                if value in taxonbridge.supported_species:
                    value = taxonbridge.Taxon(scientific_name=value)
                else:
                    value = taxonbridge.get_taxon(value)

            self._data_.taxon = value
        else:
            # scipywarn(f"Expecting a str, a Taxon, None, or MISSING; instead, got {type(value).__name__}")
            self._data_.taxon = pd.NA

        sigBlocker = QtCore.QSignalBlocker(self.taxonSpeciesLineEdit)

        if taxonbridge.hasTaxoniq and isinstance(self._data_.taxon, taxonbridge.Taxon):
            taxon_name = self._data_.taxon.scientific_name
            common_name = f"{self._data_.taxon.common_name}, (species: {taxon_name})"

        elif isinstance(self._data_.taxon,str):
            taxon_name = self._data_.taxon
            common_name = self._data_.taxon

        else:
            taxon_name = f"{pd.NA}"
            common_name = f"{pd.NA}"

        self.taxonSpeciesLineEdit.setText(taxon_name)
        self.taxonSpeciesLineEdit.setToolTip(common_name)

        self.sig_valueChanged.emit(self._data_)


    @Slot(str)
    def _slot_selectTaxon(self, value: str):
        self.setTaxon(value)

    @Slot(str)
    def _slot_setSubSpecies(self, value:str):
        if isinstance(value, str):
            self._data_.subspecies = value
        else:
            self._data_.subspecies = ""

        self.sig_valueChanged.emit(self._data_)

    @Slot(str)
    def _slot_setStrain(self, value: str):
        if isinstance(value, str):
            self._data_.strain = value
        else:
            self._data_.strain = ""

        self.sig_valueChanged.emit(self._data_)

    @Slot(str)
    def _slot_setFacilityID(self, value: str):
        if isinstance(value, str):
            self._data_.ID = value
        else:
            self._data_.ID = ""

        self.sig_valueChanged.emit(self._data_)



    @Slot()
    def _slot_showTaxonDetails(self):
        win_title = f"Taxon Details of {getattr(self._data_, 'name', type(self._data_).__name__)}"
        doc_title =  "taxon"
        if taxonbridge.hasTaxoniq and isinstance(self._data_.taxon, taxonbridge.Taxon):
            if not isinstance(self._taxonDetailsViewer_, datatreeviewer.DataTreeViewer):
                self._taxonDetailsViewer_= datatreeviewer.DataTreeViewer(
                    parent=self,
                    doc_title=doc_title,
                    title="Detailed view"
                    )
                self._taxonDetailsViewer_.autoRaise = False

                self._taxonDetailsViewer_.view(self._data_.taxon, doc_title = doc_title)
                self._taxonDetailsViewer_.sig_dataChanged.connect(self._slot_detailsChanged)

            else:
                sigBlock = QtCore.QSignalBlocker(self._taxonDetailsViewer_)
                self._taxonDetailsViewer_.winTitle = win_title
                self._taxonDetailsViewer_.docTitle = doc_title
                self._taxonDetailsViewer_.slot_refreshDataDisplay()

            self._taxonDetailsViewer_.show()

    @Slot()
    def _slot_detailsChanged(self):
        r"""Overrides DataClassWidget._slot_detailsChanged.
    Captures changes in the data tree viewer (details viewer)
    """
        # print(f"{self.__class__.__name__}._slot_detailsChanged")
        sigBlockers = list(map(lambda w: QtCore.QSignalBlocker(w),
                               (self.nameDescriptionWidget,
                                self.dataExchangeWidget,
                                self.taxonSpeciesLineEdit,
                                self.subSpeciesLineEdit,
                                self.strainLineEdit,
                                self.facilityIDLineEdit,
                                self.biometricsWidget,
                                # self.typeComboBox
                                )))

        self.nameDescriptionWidget.dataName = self._data_.name
        self.nameDescriptionWidget.dataDescription = self._data_.description

        taxon = self._data_.taxon
        if taxonbridge.hasTaxoniq and isinstane(taxon, taxonbridge.Taxon):
            taxon_name = taxon.scientific_name
            common_name = f"{taxon.common_name}, (species: {taxon_name})"
        elif isinstance(taxon,str):
            taxon_name = taxon
            common_name = taxon

        else:
            taxon_name = f"{pd.NA}"
            common_name = f"{pd.NA}"


        self.taxonSpeciesLineEdit.setText(taxon_name)
        self.taxonSpeciesLineEdit.setToolTip(common_name)

        self.subSpeciesLineEdit.setText(f"{self._data_.subspecies}")
        self.strainLineEdit.setText(f"{self._data_.strain}")
        self.facilityIDLineEdit.settext(f"{self._data_.ID}")

        self.biometricsWidget.setValue(self._data_.biometrics)

    def value(self) -> sdc.Organism:
        return self._data_

    def setValue(self, val:typing.Optional[sdc.Organism]=None):
        if isinstance(val, sdc.Organism):
            self._data_ = val
        else:
            self._data_ = sd.Organism()

        sigBlockers = list(map(lambda w: QtCore.QSignalBlocker(w),
                               (self.nameDescriptionWidget,
                                self.dataExchangeWidget,
                                self.taxonSpeciesLineEdit,
                                self.subSpeciesLineEdit,
                                self.strainLineEdit,
                                self.facilityIDLineEdit,
                                self.biometricsWidget,
                                # self.typeComboBox
                                )))

        self.nameDescriptionWidget.dataName = self._data_.name
        self.nameDescriptionWidget.dataDescription = self._data_.description

        taxon = self._data_.taxon
        if taxonbridge.hasTaxoniq and isinstance(taxon, taxonbridge.Taxon):
            taxon_name = taxon.scientific_name
            common_name = f"{taxon.common_name}, (species: {taxon_name})"
            self.taxonDetailsToolButton.setEnabled(True)
        elif isinstance(taxon,str):
            taxon_name = taxon
            common_name = taxon
            self.taxonDetailsToolButton.setEnabled(False)

        else:
            taxon_name = f"{pd.NA}"
            common_name = f"{pd.NA}"
            self.taxonDetailsToolButton.setEnabled(False)


        self.taxonSpeciesLineEdit.setText(taxon_name)
        self.taxonSpeciesLineEdit.setToolTip(common_name)

        self.subSpeciesLineEdit.setText(f"{self._data_.subspecies}")
        self.strainLineEdit.setText(f"{self._data_.strain}")
        self.facilityIDLineEdit.setText(f"{self._data_.ID}")

        self.biometricsWidget.setValue(self._data_.biometrics)
