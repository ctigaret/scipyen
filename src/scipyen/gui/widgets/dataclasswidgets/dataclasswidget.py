# -*- coding: utf-8 -*-
# $Id: dataclasswidget.py $
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
from core import qtutils
from gui import guiutils, textviewer, datatreeviewer
from gui.textviewer import TextViewer
from gui.widgets import small_widgets as smw
from gui.workspacegui import WorkspaceGuiMixin
from iolib import pictio as pio

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

class DataClassWidget(QtWidgets.QWidget, WorkspaceGuiMixin):
    sig_valueChanged = Signal(object, name="sig_valueChanged")
    sig_dataSaving = Signal(object, name="sig_dataSaving")
    sig_dataExporting = Signal(object, name="sig_dataExporting")
    sig_dataCopy = Signal(object, name="sig_dataCopy")
    sig_detailedView = Signal(object, str, name="sig_detailedView")
    _objectTypes_ = tuple()

    def __init__(self, parent:typing.Optional[QtWidgets.QWidget] = None, **kwargs):
        isAttribute = kwargs.pop("isAttribute", False)
        QtWidgets.QWidget.__init__(self, parent=parent)
        self._isAttribute_: bool = isAttribute
        self._parentEditor_ = None
        WorkspaceGuiMixin.__init__(self, parent=parent, **kwargs)
        # self._customSymbol_: typing.Optional[str] = None

    def value(self) -> None:
        r"""Must override in subclasses"""
        pass

    def setValue(self, *args, **kwargs):
        r"""Must override in subclasses.
        Implementations must make sure it emits sig_valueChanged Qt signal.
    """
        pass

    @property
    def isAttribute(self) -> bool:
        return self._isAttribute_

    @isAttribute.setter
    def isAttribute(self, val: bool):
        self._isAttribute_ = val is True

    @Slot()
    def _slot_dataExportRequested(self):
        if (hasattr(self, "_data_")
            and hasattr(self, "_objectTypes_")
            and isinstance(self._data_, self._objectTypes_)):
            self.sig_dataExporting.emit(self._data_)

    @Slot()
    def _slot_newObjectRequested(self):
        if (hasattr(self, "_data_")
            and hasattr(self, "_objectTypes_")
            and isinstance(self._data_, self._objectTypes_)):
            self.setValue(type(self._data_)())

    @Slot()
    def _slot_dataCopyRequested(self):
        if (hasattr(self, "_data_")
            and hasattr(self, "_objectTypes_")
            and isinstance(self._data_, self._objectTypes_)):
            self.sig_dataCopy.emit(self._data_)

    @Slot()
    def _slot_dataSaveRequested(self):
        if (hasattr(self, "_data_")
            and hasattr(self, "_objectTypes_")
            and isinstance(self._data_, self._objectTypes_)):
            self.sig_dataSaving.emit(self._data_)

    @Slot(object)
    def _slot_dataReceived(self, obj):
        if (hasattr(self, "_data_")
            and hasattr(self, "_objectTypes_")
            and isinstance(self._data_, self._objectTypes_)):
            self.setValue(obj)

    @Slot(str)
    def _slot_dataNameChanged(self, val: str):
        if (hasattr(self, "_data_")
            and hasattr(self, "_objectTypes_")
            and isinstance(self._data_, self._objectTypes_)):
            self._data_.name = val
            self.sig_valueChanged.emit(self._data_)

    @Slot(str)
    def _slot_dataDescriptionChanged(self, val:str):
        # print(f"{self.__class__.__name__}._slot_dataDescriptionChanged({val})")
        if (hasattr(self, "_data_")
            and hasattr(self, "_objectTypes_")
            and isinstance(self._data_, self._objectTypes_)):
            self._data_.description = val
            self.sig_valueChanged.emit(self._data_)

    @Slot(str)
    def _slot_symbolChanged(self, val:str):
        from gui.widgets.dataclasswidgets import namedescriptionwidget
        if (hasattr(self, "nameDescriptionWidget")
            and isinstance(self.nameDescriptionWidget, namedescriptionwidget.NameDescriptionWidget)):
            self.nameDescriptionWidget._slot_symbolChanged(val)
        # pass

    @Slot()
    def _slot_viewDetails(self):
        from gui.widgets.dataclasswidgets import dataexchangewidget
        if (hasattr(self, "_data_")
            and hasattr(self, "_objectTypes_")
            and isinstance(self._data_, self._objectTypes_)
            and hasattr(self, "dataExchangeWidget")
            and isinstance(self.dataExchangeWidget, dataexchangewidget.DataExchangeWidget)):
            varName = self.dataExchangeWidget.varName
            self.sig_detailedView.emit(self._data_, varName)

    @Slot()
    def _slot_detailsChanged(self):
        r"""Must override in subclasses"""
        pass

    @Slot()
    def _slot_editParent(self):
        parent = None
        if (hasattr(self, "_data_")
            and hasattr(self, "_objectTypes_")
            and isinstance(self._data_, self._objectTypes_) and hasattr(self._data_, "parent") and dataclasses.is_dataclass(self._data_.parent)):
            parent = self._data_.parent

        # print(f"{self.__class__.__name__}._slot_editParent -> {parent}")

        if isinstance(self._parentEditor_, QtWidgets.QWidget) and qtutils.isQObjectAlive(self._parentEditor_):
            editor = self._createParentEditor_(parent)
            if type(editor) != type(self._parentEditor_):
                self._parentEditor_.close()
                self._parentEditor_.deleteLater()
                self._parentEditor_ = editor

        else:
            self._parentEditor_ = self._createParentEditor_(parent)

        self._parentEditor_.show()
        self._parentEditor_.setWindowTitle("Edit parent")


        # TODO: 2026-06-25 16:47:07 finalize me
        # what are the possible parents of the CellCompartment/NeuronCompartment
        # propose creating a new one (add create new button to these widgets)

    @singledispatchmethod
    def _createParentEditor_(self, obj):
        raise NotImplementedError(f"{type(obj)} objects are not supported")

    @_createParentEditor_.register(sdc.Neuron)
    def __createParentEditor(self, obj: sdc.Neuron):
        from gui.widgets.dataclasswidgets.cellwidget import NeuronWidget
        return NeuronWidget(obj)

    @_createParentEditor_.register(sdc.Cell)
    def __createParentEditor(self, obj: sdc.Cell):
        from gui.widgets.dataclasswidgets.cellwidget import CellWidget
        return CellWidget(obj)

    @_createParentEditor_.register(sdc.CellCompartment)
    def __createParentEditor(self, obj: sdc.CellCompartment):
        from gui.widgets.dataclasswidgets.cellcompartmentwidget import CellCompartmentWidget
        return CellCompartmentWidget(obj)

    @_createParentEditor_.register(sdc.Organism)
    def __createParentEditor(self, obj: sdc.Organism):
        from gui.widgets.dataclasswidgets.organismwidget import OrganismWidget
        return OrganismWidget(obj)

    @_createParentEditor_.register(sdc.Brain)
    def __createParentEditor(self, obj: sdc.Brain):
        from gui.widgets.dataclasswidgets.organtissuewidgets import BrainWidget
        return BrainWidget(obj)

    @_createParentEditor_.register(sdc.Organ)
    def __createParentEditor(self, obj: sdc.Organ):
        from gui.widgets.dataclasswidgets.organtissuewidgets import OrganWidget
        return OrganWidget(obj)

    @_createParentEditor_.register(sdc.Tissue)
    def __createParentEditor(self, obj: sdc.Tissue):
        from gui.widgets.dataclasswidgets.organtissuewidgets import TissueWidget
        return TissueWidget(obj)




