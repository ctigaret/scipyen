# -*- coding: utf-8 -*-
# $Id: biologicalsourcewidget.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""

import sys, os, typing, types, warnings, math, cmath # noqa
# import numbers
# import numpy as np
# import quantities as pq
# import pandas as pd
# import neo
# from tribool import Tribool
from functools import singledispatchmethod
import dataclasses

# import qtpy
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
except:
    __has_qtdbus__ = False

from core.prog import scipywarn # noqa
from core import qtutils
from core import scipyendataclasses as sdc
# from core import scipyen_quantities as scq
# from gui import guiutils, textviewer
# from gui.widgets import small_widgets as smw
from gui.widgets.dataclasswidgets.dataclasswidget import DataClassWidget
# from gui.workspacegui import WorkspaceGuiMixin
# from gui.widgets.datawidgetmixin import DataWidgetMixin
# from iolib import pictio as pio

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

        if not isinstance(obj, self._objectTypes_):
            self._data_ = self._objectTypes_[0]()
        else:
            self._data_ = obj

        DataClassWidget.__init__(self, parent=parent, **kwargs)

        self._bioSourceTypeNames_ = list(sdc.BioSourceType.names())

        self._specimenTypeNames_ = dict(
            map(
                lambda t: (t.__name__, t),
                self._data_.sourceSpecimenTypeMap[self._data_.sourceType]
                )
            )

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)

        super()._configureUI_()

        for text in self._bioSourceTypeNames_:
            self.bioSourceTypeComboBox.addItem(text)

        ndx = self._bioSourceTypeNames_.index(self._data_.sourceType.name)
        self.bioSourceTypeComboBox.setCurrentIndex(ndx)

        self.bioSourceTypeComboBox.currentIndexChanged.connect(self._slot_sourceTypeChanged)

        self.specimenWidget = None

        if isinstance(self._data_.specimen.name, str) and len(self._data_.specimen.name.strip()):
            spNameLabel = f"{self._data_.specimen.name} ({type(self._data_.specimen).__name__})"
        else:
            spNameLabel =f"({type(self._data_.specimen).__name__})"

        self.specimenNameLabel.setText(spNameLabel)

        self.editSpecimenToolButton.clicked.connect(self._slot_editSpecimen)

        self.replaceSpecimenToolButton.clicked.connect(self._slot_chooseNewSpecimenType)

    @Slot()
    def _slot_chooseNewSpecimenType(self):
        from gui.itemslistdialog import ItemsListDialog

        # spTypeNames = list(self._specimenTypeNames_.keys())
        spTypes = self._data_.sourceSpecimenTypeMap[self._data_.sourceType]
        spTypeNames = list(
                            map(
                                lambda t: t.__name__,
                                spTypes
                                )
                          )
        # if type(self._data_.specimen) in self._data_.specimenTypes:
        if type(self._data_.specimen) in spTypes:
            # ndx = self._data_.specimenTypes.index(type(self._data_.specimen))
            ndx = spTypes.index(type(self._data_.specimen))
            preSelected = spTypeNames[ndx]
        else:
            preSelected = spTypeNames[0]

        # print(f"{self.__class__.__name__}._slot_chooseNewSpecimenType -> preSelected = {preSelected}")

        dlg = ItemsListDialog(parent=self, itemsList=spTypeNames,
                              title="Create New Specimen",
                              preSelected=preSelected,
                              modal=True,
                              selectmode = QtWidgets.QAbstractItemView.SingleSelection)

        if dlg.exec() == 1:
            spTypeName = dlg.selection
            self._slot_newSpecimen(spTypeName)

    @Slot(str)
    def _slot_newSpecimen(self, value: str):
        if value in self._specimenTypeNames_:
            spType = self._specimenTypeNames_[value]
            newSpecimen = spType()
            self._slot_specimenChanged(newSpecimen)
            self._slot_editSpecimen

    @Slot()
    def _slot_detailsChanged(self):
        r"""Overrides DataClassWidget._slot_detailsChanged.
    Captures changes in the data tree viewer (details viewer)
    """
        sigBlockers = list(map(lambda w: QtCore.QSignalBlocker(w), # noqa
                               (self.nameDescriptionWidget,
                                self.dataExchangeWidget,
                                self.bioSourceTypeComboBox
                                )))

        self.nameDescriptionWidget.dataName = self._data_.name
        self.nameDescriptionWidget.dataDescription = self._data_.description

        ndx = self._bioSourceTypeNames_.index(self._data_.sourceType.name)
        self.bioSourceTypeComboBox.setCurrentIndex(ndx)

        self.sig_valueChanged.emit(self._data_)

    @Slot(int)
    def _slot_sourceTypeChanged(self, val:int):
        name = self._bioSourceTypeNames_[val]
        self._data_.sourceType = sdc.BioSourceType[name]

        self.sig_valueChanged.emit(self._data_)

    @Slot(object)
    def _slot_specimenChanged(self, value: object):
        # print(f"{self.__class__.__name__}._slot_specimenChanged({value})")
        if isinstance(value, self._data_.specimenTypes):
            self._data_.specimen = value
        else:
            spField = list(filter(lambda f: f.name=="specimen",
                                  dataclasses.fields(self._data_)))[0]
            self._data_.specimen = spField.default_factory()

        if isinstance(self._data_.specimen.name, str) and len(self._data_.specimen.name.strip()):
            spNameLabel = f"{self._data_.specimen.name} ({type(self._data_.specimen).__name__})"
        else:
            spNameLabel =f"({type(self._data_.specimen).__name__})"

        self.specimenNameLabel.setText(spNameLabel)

        self.sig_valueChanged.emit(self._data_)

    @Slot()
    def _slot_editSpecimen(self):
        if isinstance(self._data_.specimen, self._data_.specimenTypes):
            if isinstance(self.specimenWidget, QtWidgets.QWidget):
                self.specimenWidget.close()
                self.specimenWidget.deleteLater()
                self.specimenWidget = None

            self.specimenWidget = self._createSpecimenWidget_(self._data_.specimen)
            self.specimenWidget.sig_valueChanged.connect(self._slot_specimenChanged)
            self.specimenWidget.show()
            if isinstance(self._data_.specimen.name, str) and len(self._data_.specimen.name.strip()):
                self.specimenWidget.setWindowTitle(f"Specimen: {self._data_.specimen.name} ({type(self._data_.specimen).__name__})")
            else:
                self.specimenWidget.setWindowTitle(f"Specimen: {type(self._data_.specimen).__name__}")

    @singledispatchmethod
    def _createSpecimenWidget_(self, obj):
        raise NotImplementedError(f"Objects of type {type(obj)} are not supported")

    @_createSpecimenWidget_.register(sdc.Organism)
    def __createSpecimenWidget__(self, obj: sdc.Organism):
        from gui.widgets.dataclasswidgets.organismwidget import OrganismWidget
        return OrganismWidget(obj, objSymbol="specimen")

    @_createSpecimenWidget_.register(sdc.Organ)
    @_createSpecimenWidget_.register(sdc.Tissue)
    def __createSpecimenWidget__(self, obj: sdc.Organ): # noqa
        from gui.widgets.dataclasswidgets.organtissuewidgets import OrganWidget, TissueWidget
        if isinstance(obj, sdc.Tissue):
            return TissueWidget(obj, objSymbol="specimen")
        return OrganWidget(obj, objSymbol="specimen")

    @_createSpecimenWidget_.register(sdc.NervousSystem)
    def __createSpecimenWidget__(self, obj: sdc.NervousSystem): # noqa
        from gui.widgets.dataclasswidgets.nervoussystemwidget import NervousSystemWidget
        return NervousSystemWidget(obj, objSymbol="specimen")

    @_createSpecimenWidget_.register(sdc.Neuron)
    def __createSpecimenWidget__(self, obj: sdc.Neuron): # noqa
        from gui.widgets.dataclasswidgets.cellwidgets import NeuronWidget
        return NeuronWidget(obj, objSymbol="specimen")

    @_createSpecimenWidget_.register(sdc.Cell)
    def __createSpecimenWidget__(self, obj: sdc.Cell): # noqa
        from gui.widgets.dataclasswidgets.cellwidgets import CellWidget
        return CellWidget(obj, objSymbol="specimen")

    @_createSpecimenWidget_.register(sdc.NeuronCompartment)
    @_createSpecimenWidget_.register(sdc.CellCompartment)
    @_createSpecimenWidget_.register(sdc.ChemicalSynapseUltrastructureElement)
    @_createSpecimenWidget_.register(sdc.UltrastructureElement)
    def __createSpecimenWidget__(self, obj: sdc.CellCompartment): # noqa
        from gui.widgets.dataclasswidgets.cellcompartmentwidget import CellCompartmentWidget
        return CellCompartmentWidget(obj, objSymbol="specimen")

    @_createSpecimenWidget_.register(sdc.ChemicalSynapse)
    def __createSpecimenWidget__(self, obj: sdc.ChemicalSynapse): # noqa
        from gui.widgets.dataclasswidgets.chemicalsynapsewidget import ChemicalSynapseWidget
        return ChemicalSynapseWidget(obj, objSymbol="specimen")

    @_createSpecimenWidget_.register(sdc.BiologicalProduct)
    def __createSpecimenWidget__(self, obj: sdc.BiologicalProduct): # noqa
        from gui.widgets.dataclasswidgets.biologicalproductwidget import BiologicalProductWidget
        return BiologicalProductWidget(obj, objSymbol="specimen")

    def closeEvent(self, evt):
        if isinstance(self.specimenWidget, QtWidgets.QWidget) and qtutils.isQObjectAlive(self.specimenWidget):
            self.specimenWidget.close()
            self.specimenWidget.deleteLater()
            self.specimenWidget = None
        super().closeEvent(evt)
        evt.accept()

    def value(self) -> sdc.BiologicalSource:
        return self._data_

    def setValue(self, value: sdc.BiologicalSource, **kwargs):
        if not isinstance(value, sdc.BiologicalSource):
            self._data_ = sdc.BiologicalSource()
        else:
            self._data_ = value

        super().setValue(self._data_, **kwargs)

        sigBlockers = list(map(lambda w: QtCore.QSignalBlocker(w), # noqa
                               (
                                   self.bioSourceTypeComboBox,
                                   self.specimenNameLabel,
                                )
                               )
                        )

        ndx = self._bioSourceTypeNames_.index(self._data_.sourceType.name)
        self.bioSourceTypeComboBox.setCurrentIndex(ndx)
        if isinstance(self._data_.specimen.name, str) and len(self._data_.specimen.name.strip()):
            spNameLabel = f"{self._data_.specimen.name} ({type(self._data_.specimen).__name__})"
        else:
            spNameLabel =f"{type(self._data_.specimen).__name__}"

        self.specimenNameLabel.setText(spNameLabel)











