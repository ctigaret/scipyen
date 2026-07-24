# -*- coding: utf-8 -*-
# $Id: chemicalsynapsewidget.py $
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
from qtpy.QtCore import (Signal, Slot)#), Property,)
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

    from qtpy import sip # noqa
    from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True

from core import scipyendataclasses as sdc
from gui.widgets.dataclasswidgets.dataclasswidget import DataClassWidget

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

Ui_ChemicalSynapseWidget, QWidget = loadUiType(
    os.path.join(__module_path__, "chemicalsynapsewidget.ui")
    )

class ChemicalSynapseWidget(Ui_ChemicalSynapseWidget, DataClassWidget):
    _objectTypes_ = (sdc.ChemicalSynapse, )

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
            obj = sdc.ChemicalSynapse()

        self._data_ = obj

        self._morphoTypes_ = list(sdc.ChemicalSynapseMorphologicalType.names())

        self._functionalTypes_ = list(sdc.ChemicalSynapseFunctionalType.names())

        self._transmitters_ = list(sdc.Neurotransmitter.names())

        DataClassWidget.__init__(self, parent=parent, **kwargs)

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)
        super()._configureUI_()

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
        ndx = self._transmitters_.index(self._data_.transmitter.name)
        self.neurotransmitterComboBox.setCurrentIndex(ndx)
        self.neurotransmitterComboBox.currentIndexChanged.connect(self._slot_transmitterChanged)

        self.retrogradeCheckBox.setChecked(self._data_.retrograde is True)
        self.retrogradeCheckBox.toggled.connect(self._slot_retrogradeChanged)

        self.presynapticCompartmentWidget.setValue(self._data_.presynaptic, isAttribute=True)
        self.presynapticCompartmentWidget.nameDescriptionWidget.symbol = f"{self.dataExchangeWidget.objectSymbolLabel.text()}.presynaptic"
        self.presynapticCompartmentWidget.sig_valueChanged.connect(self._slot_presynaptiChanged)

        self.postsynapticCompartmentWidget.setValue(self._data_.postsynaptic, isAttribute=True)
        self.postsynapticCompartmentWidget.nameDescriptionWidget.symbol = f"{self.dataExchangeWidget.objectSymbolLabel.text()}.postynaptic"
        self.postsynapticCompartmentWidget.sig_valueChanged.connect(self._slot_postsynapticChanged)

        self.sig_uiConfigured.emit()

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

    def value(self) -> sdc.ChemicalSynapse:
        return self._data_

    def setValue(self, val: sdc.ChemicalSynapse, *args, **kwargs):
        if not isinstance(val, self._objectTypes_):
            raise TypeError(f"Expecting one of  {self._objectTypes_}; instead, got a {type(val).__name__}")

        self._data_ = val
        super().setValue(self._data_, **kwargs)
        self._isAttribute_ = kwargs.get("isAttribute", False)

        sigBlockers = list(map(lambda w: QtCore.QSignalBlocker(w),
                               (
                                   # self.dataExchangeWidget,
                                   # self.nameDescriptionWidget,
                                   # self.editParentToolButton,
                                   self.synapseMorhpologicalTypeComboBox,
                                   self.synapseFunctionalTypeComboBox,
                                   self.retrogradeCheckBox,
                                   self.presynapticCompartmentWidget,
                                   self.postsynapticCompartmentWidget
                                )
                               ))

        # self.dataExchangeWidget.setValue(self._data_)
        #
        # self.nameDescriptionWidget.dataName = self._data_.name
        # self.nameDescriptionWidget.dataDescription = self._data_.description

        for t in self._functionalTypes_:
            self.synapseFunctionalTypeComboBox.addItem(t)
        ndx = self._functionalTypes_.index(self._data_.functionalType.name)
        self.synapseFunctionalTypeComboBox.setCurrentIndex(ndx)

        for t in self._transmitters_:
            self.neurotransmitterComboBox.addItem(t)
        ndx = self._transmitters_.index(self._data_.transmitter.name)
        self.neurotransmitterComboBox.setCurrentIndex(ndx)

        self.retrogradeCheckBox.setChecked(self._data_.retrograde is True)

        self.presynapticCompartmentWidget.setValue(self._data_.presynaptic, isAttribute=True)
        self.presynapticCompartmentWidget.nameDescriptionWidget.symbol = f"{self.dataExchangeWidget.objectSymbolLabel.text()}.presynaptic"

        self.postsynapticCompartmentWidget.setValue(self._data_.postsynaptic, isAttribute=True)
        self.postsynapticCompartmentWidget.nameDescriptionWidget.symbol = f"{self.dataExchangeWidget.objectSymbolLabel.text()}.postynaptic"

        self.sig_valueChanged.emit(self._data_)


