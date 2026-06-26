# -*- coding: utf-8 -*-
# $Id: dataclasswidgets.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""

import sys, os, typing, types, warnings, math, cmath, datetime # noqa
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
from gui.workspacegui import WorkspaceGuiMixin
from iolib import pictio as pio

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

Ui_CellCompartmentWidget, _ = loadUiType(
    os.path.join(__module_path__, "cellcompartmentwidget.ui")
    )
class CellCompartmentWidget(Ui_CellCompartmentWidget, QtWidgets.QWidget):
    sig_valueChanged = Signal(object, name="sig_valueChanged")
    sig_dataSaving = Signal(object, name="sig_dataSaving")
    sig_dataExporting = Signal(object, name="sig_dataExporting")
    sig_dataCopy = Signal(object, name="sig_dataCopy")

    _objectTypes_ = (sdc.CellCompartment, )

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

        QtWidgets.QWidget.__init__(self, parent=parent)
        title = kwargs.pop("title", f"{type(obj).__name__} Widget")
        # self._boundSymbol_: str = kwargs.pop("symbol", "")
        # WorkspaceGuiMixin.__init__(self, parent=parent, title=title, **kwargs)

        if not isinstance(obj, self._objectTypes_):
            self._data_ =  sdc.CellCompartment()
        else:
            self._data_ = obj

        if isinstance(self._data_, sdc.NeuronCompartment):
            self._compartmentTypeNames_ = list(sdc.NeuronCompartmentType.names())
        else:
            self._compartmentTypeNames_ = list(sdc.CellCompartmentType.names())

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)
        self._detailsViewer_ = None
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

        self.editParentToolButton.clicked.connect(self._slot_editParent)
        self.viewDetailsToolButton.clicked.connect(self._slot_viewDetails)
        for s in self._compartmentTypeNames_:
            self.typeComboBox.addItem(s)
        ndx = self._compartmentTypeNames_.index(self._data_.compartmentType.name)
        self.typeComboBox.setCurrentIndex(ndx)
        self.typeComboBox.currentIndexChanged.connect(self._slot_compartmentTypeChanged)

    def value(self) -> sdc.CellCompartment:
        return self._data_

    def setValue(self, val: sdc.CellCompartment):
        # print(f"{self.__class__.__name__}.setValue({val})")
        if not isinstance(val, sdc.CellCompartment):
            raise TypeError(f"Expecting a CellCompartment or NeuronCompartment; instead, got a {type(val).__name__}")

        self._data_ = val

        sigBlockers = list(map(lambda w: QtCore.QSignalBlocker(w),
                               (
                                   self.dataExchangeWidget,
                                   self.nameDescriptionWidget,
                                   self.editParentToolButton,
                                   self.typeComboBox,
                                   self.dataTreeViewToolButton,
                                   self.dataExchangeWidget,
                                )
                            )
                        )


        self.dataExchangeWidget.setValue(self._data_)

        self.nameDescriptionWidget.dataName = self._data_.name
        self.nameDescriptionWidget.dataDescription = self._data_.description

        if isinstance(self._data_, sdc.NeuronCompartment):
            self._compartmentTypeNames_ = list(sdc.NeuronCompartmentType.names())
        else:
            self._compartmentTypeNames_ = list(sdc.CellCompartmentType.names())

        self.typeComboBox.clear()

        for s in self._compartmentTypeNames_:
            self.typeComboBox.addItem(s)

        ndx = self._compartmentTypeNames_.index(self._data_.compartmentType.name)
        self.typeComboBox.setCurrentIndex(ndx)

        self.sig_valueChanged.emit(self._data_)

    @Slot()
    def _slot_dataExportRequested(self):
        if isinstance(self._data_, self._objectTypes_):
            self.sig_dataExporting.emit(self._data_)

    @Slot()
    def _slot_newObjectRequested(self):
        self.setValue(type(self._data_)())

    @Slot()
    def _slot_dataCopyRequested(self):
        if isinstance(self._data_, self._objectTypes_):
            self.sig_dataCopy.emit(self._data_)

    @Slot()
    def _slot_dataSaveRequested(self):
        if isinstance(self._data_, self._objectTypes_):
            self.sig_dataSaving.emit(self._data_)

    @Slot(object)
    def _slot_dataReceived(self, obj):
        if isinstance(obj, self._objectTypes_):
            # print(f"{self.__class__.__name__}._slot_dataReceived({obj})")
            self.setValue(obj)

    @Slot(str)
    def _slot_dataNameChanged(self, val: str):
        self._data_.name = val
        self.sig_valueChanged.emit(self._data_)

    @Slot(str)
    def _slot_dataDescriptionChanged(self, val:str):
        self._data_.description = val
        self.sig_valueChanged.emit(self._data_)

    @Slot(int)
    def _slot_compartmentTypeChanged(self, val:int):
        cTypes = sdc.NeuronCompartmentType if isinstance(self._data_, sdc.NeuronCompartment) else sdc.CellCompartmentType
        self._data_.compartmentType = cTypes[self._compartmentTypeNames_[val]]
        self.sig_valueChanged.emit(self._data_)

    @Slot()
    def _slot_editParent(self):
        if hasattr(self._data_, "parent") and dataclasses.is_dataclass(self._data_.parent):
            parent = self._data_.parent
        elif hasattr(self._data_, "getParent"):
            try:
                parent = self._data_.getParent()
                if not dataclasses.is_dataclass(parent):
                    parent = None
            except:
                parent = None
        if parent is None:
            return

        # print(f"{self.__class__.__name__}._slot_editParent -> parent is:\n\n{parent}")

        # TODO: 2026-06-25 16:47:07 finalize me
        # what are the possible parents of the CellCompartment/NeuronCompartment
        # propose creating a new one (add create new button to these widgets)

    @Slot()
    def _slot_viewDetails(self):
        if not isinstance(self._data_, self._objectTypes_):
            return
        if not isinstance(self._detailsViewer_, datatreeviewer.DataTreeViewer):
            varName = self.dataExchangeWidget.varName
            self._detailsViewer_ = datatreeviewer.DataTreeViewer(
                parent=self,
                win_title=f"Details of {self._data_.name}" + (f" ({varName})" if len(varName.strip()) else ""),
                doc_title=f"{self._data_.name}" + (f" ({varName})" if len(varName.strip()) else ""),
                title="Detailed view"
                )
            self._detailsViewer_.view(self._data_)

            self._detailsViewer_.show()



