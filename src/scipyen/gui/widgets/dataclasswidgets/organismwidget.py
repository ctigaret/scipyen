# -*- coding: utf-8 -*-
# $Id: organismwidget.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""

import sys, os, typing, types, warnings, math, cmath # noqa
# import dataclasses
# import numbers
# import numpy as np
# import quantities as pq
import pandas as pd
# import neo
# from tribool import Tribool

# import qtpy # noqa
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, ) # noqa
from qtpy.QtCore import (Signal, Slot, Property,) # noqa
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
__has_qtdbus__ = False

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

    from qtpy import sip # noqa
    from qtpy.uic import loadUiType # noqa
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True

try:
    from qtpy import QtDBus # noqa
    __has_qtdbus__ = True
except: # noqa
    __has_qtdbus__ = False

# from core.prog import scipywarn
from core import scipyendataclasses as sdc
# from core import scipyen_quantities as scq # noqa
from core import taxonbridge
from gui import datatreeviewer
# from gui.widgets import small_widgets as smw
from gui.widgets.dataclasswidgets.dataclasswidget import DataClassWidget
# from gui.workspacegui import WorkspaceGuiMixin
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


        if not isinstance(obj, self._objectTypes_):
            self._data_ =  self._objectTypes_[0]()
        else:
            self._data_ = obj

        DataClassWidget.__init__(self, parent=parent, **kwargs)

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)

        super()._configureUI_()

        self.taxonDetailsViewer = None


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
        self.taxonSpeciesLineEdit.lazy = True
        self.taxonSpeciesLineEdit.sig_enterPressed.connect(self._slot_selectTaxon)

        self.taxonDetailsToolButton.clicked.connect(self._slot_showTaxonDetails)

        self.subSpeciesLineEdit.setText(f"{self._data_.subspecies}")
        self.subSpeciesLineEdit.lazy = True
        self.subSpeciesLineEdit.sig_enterPressed.connect(self._slot_setSubSpecies)

        self.strainLineEdit.setText(f"{self._data_.strain}")
        self.strainLineEdit.lazy = True
        self.strainLineEdit.sig_enterPressed.connect(self._slot_setStrain)

        self.facilityIDLineEdit.setText(f"{self._data_.ID}")
        self.facilityIDLineEdit.lazy = True
        self.facilityIDLineEdit.sig_enterPressed.connect(self._slot_setFacilityID)

        self.biometricsWidget.setValue(self._data_.biometrics)

    def setTaxon(self, value):
        # print(f"{self.__class__.__name__}.setTaxon({value})")
        taxon = pd.NA

        if self._isTaxoniqTaxon(value):
            taxon = value

        elif isinstance(value, str) and len(value.strip()):
            if taxonbridge.hasTaxoniq:
                if value in taxonbridge.supported_species:
                    taxon = taxonbridge.Taxon(scientific_name=value)
                else:
                    taxon = taxonbridge.get_taxon(value)

            else:
                taxon = value

        self._data_.taxon = taxon

        if self._isTaxoniqTaxon(self._data_.taxon):
            taxon_name = self._data_.taxon.scientific_name
            common_name = f"{self._data_.taxon.common_name}, (species: {taxon_name})"
            self.taxonDetailsToolButton.setEnabled(True)

        elif isinstance(self._data_.taxon, str):
            taxon_name = self._data_.taxon
            common_name = self._data_.taxon
            self.taxonDetailsToolButton.setEnabled(False)

        else:
            taxon_name = f"{pd.NA}"
            common_name = f"{pd.NA}"
            self.taxonDetailsToolButton.setEnabled(False)

        sigBlocker = QtCore.QSignalBlocker(self.taxonSpeciesLineEdit)
        self.taxonSpeciesLineEdit.setText(taxon_name)
        self.taxonSpeciesLineEdit.setToolTip(common_name)

        self.sig_valueChanged.emit(self._data_)


    @Slot(str)
    def _slot_selectTaxon(self, value: str):
        # print(f"{self.__class__.__name__}._slot_selectTaxon({value})")
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
        print(f"{self.__class__.__name__}._slot_showTaxonDetails")
        win_title = f"Taxon Details of {getattr(self._data_, 'name', type(self._data_).__name__)}"
        doc_title =  "taxon"
        if taxonbridge.hasTaxoniq and isinstance(self._data_.taxon, taxonbridge.Taxon):
            if not isinstance(self.taxonDetailsViewer, datatreeviewer.DataTreeViewer):
                self.taxonDetailsViewer= datatreeviewer.DataTreeViewer(
                    parent=self,
                    doc_title=doc_title,
                    title="Detailed view"
                    )
                self.taxonDetailsViewer.autoRaise = False

                self.taxonDetailsViewer.view(self._data_.taxon,
                                             doc_title = doc_title,
                                             name=doc_title)
                self.taxonDetailsViewer.winTitle = win_title
                self.taxonDetailsViewer.sig_modelDataChanged.connect(self._slot_detailsChanged)

            else:
                # sigBlock = QtCore.QSignalBlocker(self.taxonDetailsViewer)
                self.taxonDetailsViewer.view(self._data_.taxon,
                                             doc_title = doc_itle,
                                             name = doc_title)
                self.taxonDetailsViewer.winTitle = win_title
                self.taxonDetailsViewer.docTitle = doc_title
                self.taxonDetailsViewer.slot_refreshDataDisplay()

            self.taxonDetailsViewer.show()

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

    def setValue(self, val:typing.Optional[sdc.Organism]=None, **kwargs):
        self._objSymbol_ = kwargs.pop("objSymbol", None)
        if self._objSymbol_ is None or (isinstance(self._objSymbol_, str) and len(self._objSymbol_.strip()) == 0):
            objSymbols = self.getDataSymbolInWorkspace(value)
            if len(objSymbols) > 0:
                self._objSymbol_ = objSymbols[0]
            else:
                self._objSymbol_ = ""


        if isinstance(val, sdc.Organism):
            self._data_ = val
        else:
            self._data_ = sdc.Organism()

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

        self.dataExchangeWidget.setValue(self._data_, self._objSymbol_)
        self.nameDescriptionWidget.dataName = self._data_.name
        self.nameDescriptionWidget.dataDescription = self._data_.description

        taxon = self._data_.taxon

        # print(f"{self.__class__.__name__}.setValue -> taxon is a {type(self._data_.taxon)}")
        if self._isTaxoniqTaxon(taxon):
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

    def _isTaxoniqTaxon(self, obj) -> bool:
        return (taxonbridge.hasTaxoniq and isinstance(obj, taxonbridge.Taxon)
                and "taxoniq" in type(obj).__module__)
