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
from core import qtutils
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
        self.biometricsEditor = None


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
        self.taxonSpeciesLineEdit.sig_textChanged.connect(self._slot_selectTaxon)

        self.taxonDetailsToolButton.clicked.connect(self._slot_showTaxonDetails)

        self.subSpeciesLineEdit.setText(f"{self._data_.subspecies}")
        self.subSpeciesLineEdit.lazy = True
        self.subSpeciesLineEdit.sig_textChanged.connect(self._slot_setSubSpecies)

        self.strainLineEdit.setText(f"{self._data_.strain}")
        self.strainLineEdit.lazy = True
        self.strainLineEdit.sig_textChanged.connect(self._slot_setStrain)

        self.facilityIDLineEdit.setText(f"{self._data_.ID}")
        self.facilityIDLineEdit.lazy = True
        self.facilityIDLineEdit.sig_textChanged.connect(self._slot_setFacilityID)

        # self.toggleBiometricsToolButton.clicked.connect(self._slot_editBiometrics)
        self.toggleBiometricsToolButton.toggled.connect(self._slot_toggleBiometricsEditor)

        # self._collapsibleChildren_["biometricsEditor"] = self.biometricsEditor

        self.sig_uiConfigured.emit()

    def closeEvent(self, evt):
        if isinstance(self.taxonDetailsViewer, QtWidgets.QWidget) and qtutils.isQObjectAlive(self.taxonDetailsViewer):
            self.taxonDetailsViewer.close()
            self.taxonDetailsViewer.deleteLater()
            self.taxonDetailsViewer = None

        if isinstance(self.biometricsEditor, QtWidgets.QWidget) and qtutils.isQObjectAlive(self.biometricsEditor):
            self.biometricsEditor.close()
            self.biometricsEditor.deleteLater()
            self.biometricsEditor = None


        super().closeEvent(evt)
        evt.accept()

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

        sigBlocker = QtCore.QSignalBlocker(self.taxonSpeciesLineEdit) # noqa
        self.taxonSpeciesLineEdit.setText(taxon_name)
        self.taxonSpeciesLineEdit.setToolTip(common_name)

        self.sig_valueChanged.emit(self._data_)

    @Slot(bool)
    def _slot_toggleBiometricsEditor(self, val: bool):
        if val is True:
            self._slot_editBiometrics()
        else:
            if isinstance(self.biometricsEditor, DataClassWidget) and qtutils.isQObjectAlive(self.biometricsEditor):
                self.biometricsEditor.collapse(False)

    @Slot(object)
    def _slot_biometricsChanged(self, value: object):
        if isinstance(value, sdc.Biometrics):
            self._data_.biometrics = value
        else:
            self._data_.biometrics = sdc.Biometrics()

        self.sig_valueChanged.emit(self._data_)

    @Slot(str)
    def _slot_selectTaxon(self, value: str):
        # print(f"{self.__class__.__name__}._slot_selectTaxon({value})")
        # method called below will also emmit sig_valueChanged
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
    def _slot_editBiometrics(self):
        from gui.widgets.dataclasswidgets.biometricswidget import BiometricsWidget
        anchoringWidget = self.provideAnchoringWidget()
        # anchoringWidget = self._anchoringWidget_ if (isinstance(self._anchoringWidget_, QtWidgets.QWidget) and self.overrideAnchor) else self if self.parent() is None else None
        if isinstance(self.biometricsEditor, QtWidgets.QWidget) and qtutils.isQObjectAlive(self.biometricsEditor):
            if not isinstance(self.biometricsEditor, BiometricsWidget):
                self.biometricsEditor.close()
                self.biometricsEditor.deleteLater()
                self.biometricsEditor = None

                self.biometricsEditor = self._setupCollapsibleChild_(
                    BiometricsWidget,
                    "biometricsEditor",
                    self._slot_biometricsChanged,
                    self.toggleBiometricsToolButton,
                    anchoringWidget,
                    self._data_.biometrics,
                    objSymbol="biometrics"
                    )

            # self.biometricsEditor = BiometricsWidget(anchoringWidget=anchoringWidget)
            self.biometricsEditor.setWindowTitle("Biometrics")
            # self.biometricsEditor.sig_valueChanged.connect(self._slot_biometricsChanged)
            # self.biometricsEditor.sig_closing.connect(self._slot_biometricsEditorClosing)
            # self.biometricsEditor.sig_collapsed.connect(self._slot_biometricsEditorCollapsed)

        # self._collapsibleChildren_["biometricsEditor"] = self.biometricsEditor,

        # self.biometricsEditor.setValue(self._data_.biometrics, objSymbol="biometrics")

        if not self.biometricsEditor.isVisible():
            self.biometricsEditor.show()

    # @Slot()
    # def _slot_biometricsEditorCollapsed(self):
    #     sb = QtCore.QSignalBlocker(self.toggleBiometricsToolButton) # noqa
    #     self.toggleBiometricsToolButton.setChecked(False)
    #
    # @Slot()
    # def _slot_biometricsEditorClosing(self):
    #     sb = QtCore.QSignalBlocker(self.toggleBiometricsToolButton) # noqa
    #     self.toggleBiometricsToolButton.setChecked(False)

    @Slot()
    def _slot_showTaxonDetails(self):
        # print(f"{self.__class__.__name__}._slot_showTaxonDetails")
        # win_title = f"Taxon Details of {getattr(self._data_, 'name', type(self._data_).__name__)}"
        doc_title =  "taxon"
        if taxonbridge.hasTaxoniq and isinstance(self._data_.taxon, taxonbridge.Taxon):
            if not isinstance(self.taxonDetailsViewer, datatreeviewer.DataTreeViewer):
                self.taxonDetailsViewer= datatreeviewer.DataTreeViewer(
                    parent=self,
                    doc_title=doc_title,
                    # title="Detailed view"
                    )
                self.taxonDetailsViewer.autoRaise = False

                self.taxonDetailsViewer.view(self._data_.taxon,
                                             doc_title = doc_title,
                                             name=doc_title)
                # self.taxonDetailsViewer.winTitle = win_title
                self.taxonDetailsViewer.sig_modelDataChanged.connect(self._slot_detailsChanged)

            else:
                self.taxonDetailsViewer.view(self._data_.taxon,
                                             doc_title = doc_title,
                                             name = doc_title)
                self.taxonDetailsViewer.winTitle = doc_title
                self.taxonDetailsViewer.docTitle = doc_title
                self.taxonDetailsViewer.slot_refreshDataDisplay()

            self.taxonDetailsViewer.show()

    @Slot()
    def _slot_detailsChanged(self):
        r"""Overrides DataClassWidget._slot_detailsChanged.
    Captures changes in the data tree viewer (details viewer)
    """
        sigBlockers = list(
            map(
                lambda w: QtCore.QSignalBlocker(w),
                (
                    self.nameDescriptionWidget,
                    self.dataExchangeWidget,
                    self.taxonSpeciesLineEdit,
                    self.subSpeciesLineEdit,
                    self.strainLineEdit,
                    self.facilityIDLineEdit,
                    self.biometricsEditor,
                )
               )
        )

        self.nameDescriptionWidget.dataName = self._data_.name
        self.nameDescriptionWidget.dataDescription = self._data_.description

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

        self.subSpeciesLineEdit.setText(f"{self._data_.subspecies}")
        self.strainLineEdit.setText(f"{self._data_.strain}")
        self.facilityIDLineEdit.settext(f"{self._data_.ID}")

        self.biometricsEditor.setValue(self._data_.biometrics)

        self.sig_valueChanged.emit(self._data_)

    def value(self) -> sdc.Organism:
        return self._data_

    def setValue(self, value: typing.Optional[sdc.Organism]=None, **kwargs):
        if isinstance(value, sdc.Organism):
            self._data_ = value
        else:
            self._data_ = sdc.Organism()

        super().setValue(self._data_, **kwargs)


        sigBlockers = list(
                            map(
                                    lambda w: QtCore.QSignalBlocker(w),
                                    (
                                        # self.nameDescriptionWidget,
                                        # self.dataExchangeWidget,
                                        self.taxonSpeciesLineEdit,
                                        self.subSpeciesLineEdit,
                                        self.strainLineEdit,
                                        self.facilityIDLineEdit,
                                        # self.biometricsEditor,
                                    # self.typeComboBox
                                    )
                                )
                            )

        taxon = self._data_.taxon

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

        if isinstance(self.biometricsEditor, DataClassWidget):
            sb = QtCore.QSignalBlocker(self.biometricsEditor) # noqa
            self.biometricsEditor.setValue(self._data_.biometrics, objSymbol="biometrics")

    def _isTaxoniqTaxon(self, obj) -> bool:
        return taxonbridge.isTaxoniqTaxon(obj)
        # return (taxonbridge.hasTaxoniq and isinstance(obj, taxonbridge.Taxon)
        #         and "taxoniq" in type(obj).__module__)
