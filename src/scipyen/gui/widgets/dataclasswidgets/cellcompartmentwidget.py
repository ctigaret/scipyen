# -*- coding: utf-8 -*-
# $Id: cellcompartmentwidget.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""

import sys, os, typing, types, warnings, math, cmath, datetime # noqa
from functools import singledispatchmethod
# import numbers
# import dataclasses
# import numpy as np
# import quantities as pq
# import pandas as pd
# import neo
# from tribool import Tribool

# import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, )
from qtpy.QtCore import (Signal, Slot) #, Property,)
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6# noqa
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

# from core import scipyen_quantities as scq
# from core import strutils
# from core.datatypes import UnitTypes, GENOTYPES

# from core import workspacefunctions as wsf
# from gui.widgets.small_widgets import QuantitySpinBox, QuantityChooserWidget
# from gui.widgets.datatreeview import DataTreeView

# from core.prog import scipywarn
from core import scipyendataclasses as sdc
# from core import scipyen_quantities as scq
# from gui import guiutils, textviewer, datatreeviewer
# from gui.widgets import small_widgets as smw
from gui.widgets.dataclasswidgets.dataclasswidget import DataClassWidget
# from gui.workspacegui import WorkspaceGuiMixin
# from iolib import pictio as pio

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

Ui_CellCompartmentWidget, _ = loadUiType(
    os.path.join(__module_path__, "cellcompartmentwidget.ui")
    )

class CellCompartmentWidget(Ui_CellCompartmentWidget, DataClassWidget):
    _objectTypes_ = (sdc.CellCompartment, sdc.UltrastructureElement)

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
            self._data_ =  self._objectTypes_[0]()
        else:
            self._data_ = obj

        self._entityTypeNames_ = self._getEntityTypes_(self._data_)

        DataClassWidget.__init__(self, parent=parent, **kwargs)

        self._configureUI_()

    @singledispatchmethod
    def _getEntityTypes_(self, obj) -> list[str]:
        raise NotImplementedError(f"{type(obj).__name__} objects are not supported")

    @_getEntityTypes_.register(sdc.NeuronCompartment)
    def __getEntityTypes__(self, obj: sdc.NeuronCompartment) -> list[str]:
        return list(sdc.NeuronCompartmentType.__members__.keys())
        # return list(sdc.NeuronCompartmentType.names())

    @_getEntityTypes_.register(sdc.CellCompartment)
    def __getEntityTypes__(self, obj: sdc.CellCompartment) -> list[str]: # noqa
        return list(sdc.CellCompartmentType.__members__.keys())

    @_getEntityTypes_.register(sdc.ChemicalSynapseUltrastructureElement)
    def __getEntityTypes__(self, obj: sdc.ChemicalSynapseUltrastructureElement) -> list[str]: # noqa
        return list(sdc.ChemicalSynapseUltrastructureElementType.__members__.keys())

    @_getEntityTypes_.register(sdc.UltrastructureElement)
    def __getEntityTypes__(self, obj: sdc.UltrastructureElement) -> list[str]: # noqa
        return list(sdc.UltrastructureElementType.__members__.keys())

    def _configureUI_(self):
        self.setupUi(self)

        super()._configureUI_()

        for s in self._entityTypeNames_:
            self.typeComboBox.addItem(s)

        ndx = self._entityTypeNames_.index(self._data_.compartmentType.name)
        self.typeComboBox.setCurrentIndex(ndx)
        self.typeComboBox.currentIndexChanged.connect(self._slot_compartmentTypeChanged)

        self.sig_uiConfigured.emit()

    def value(self) -> sdc.CellCompartment:
        r"""Overrides DataClassWidget.value()"""
        return self._data_

    def setValue(self, val: sdc.CellCompartment, *args, **kwargs):
        r"""Overrides DataClassWidget.setValue()"""
        # print(f"{self.__class__.__name__}.setValue({val})")
        if not isinstance(val, self._objectTypes_):
            raise TypeError(f"Expecting one of  {self._objectTypes_}; instead, got a {type(val).__name__}")

        self._data_ = val
        super().setValue(self._data_, **kwargs)

        sigBlockers = list(map(lambda w: QtCore.QSignalBlocker(w),
                               (
                                   # self.dataExchangeWidget,
                                   # self.nameDescriptionWidget,
                                   self.editParentToolButton,
                                   self.typeComboBox,
                                )
                            )
                        )


        # self.dataExchangeWidget.setValue(self._data_)
        #
        # self.nameDescriptionWidget.dataName = self._data_.name
        # self.nameDescriptionWidget.dataDescription = self._data_.description

        if isinstance(self._data_, sdc.NeuronCompartment):
            self._entityTypeNames_ = list(sdc.NeuronCompartmentType.names())
        else:
            self._entityTypeNames_ = list(sdc.CellCompartmentType.names())

        self.typeComboBox.clear()

        for s in self._entityTypeNames_:
            self.typeComboBox.addItem(s)

        ndx = self._entityTypeNames_.index(self._data_.compartmentType.name)
        self.typeComboBox.setCurrentIndex(ndx)

        self.sig_valueChanged.emit(self._data_)

    @Slot(int)
    def _slot_compartmentTypeChanged(self, val:int):
        cTypes = sdc.NeuronCompartmentType if isinstance(self._data_, sdc.NeuronCompartment) else sdc.CellCompartmentType
        self._data_.compartmentType = cTypes[self._entityTypeNames_[val]]
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
                                self.typeComboBox
                                )))

        self.nameDescriptionWidget.dataName = self._data_.name
        self.nameDescriptionWidget.dataDescription = self._data_.description

        ndx = self._entityTypeNames_.index(self._data_.compartmentType.name)
        self.typeComboBox.setCurrentIndex(ndx)

        self.sig_valueChanged.emit(self._data_)


