# -*- coding: utf-8 -*-
# $Id: dataclasswidgets.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""

import sys, os, typing, types, warnings, math, cmath, datetime # noqa
import numbers
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
from gui import guiutils, textviewer
from gui.textviewer import TextViewer
from gui.widgets import small_widgets as smw
from gui.workspacegui import WorkspaceGuiMixin
from iolib import pictio as pio

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

Ui_CellCompartmentWidget, _ = loadUiType(
    os.path.join(__module_path__, "cellcompartmentwidget.ui")
    )
class CellCompartmentWidget(Ui_CellCompartmentWidget, QtWidgets.QWidget,
                            WorkspaceGuiMixin):
    sig_valueChanged = Signal(object, name="sig_valueChanged")
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
        self._boundSymbol_: str = kwargs.pop("symbol", "")
        WorkspaceGuiMixin.__init__(self, parent=parent, title=title, **kwargs)

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
        self.dataExchangeWidget.dataType = type(self._data_)
        self.objectSymbolWidget.setValue(self._boundSymbol_)

        self.editParentToolButton.clicked.connect(self._slot_editParent)
        for s in self._compartmentTypeNames_:
            self.typeComboBox.addItem(s)
        ndx = self._compartmentTypeNames_.index(self._data_.compartmentType.name)
        self.typeComboBox.setCurrentIndex(ndx)
        self.typeComboBox.currentIndexChanged.connect(self._slot_compartmentTypeChanged)

    def value(self) -> sdc.CellCompartment:
        return self._data_

    def setValue(self, val: sdc.CellCompartment):
        sigBlockers = list(map(lambda w: QtCore.QSignalBlocker(w),
                               (
                                   self.dataExchangeWidget,
                                   self.objectSymbolWidget,
                                   self.editParentToolButton,
                                   self.typeComboBox,
                                   self,dataTreeViewToolButton,

                                )
                            )
                        )


        self.dataExchangeWidget.dataType = type(self._data_)

        if isinstance(self._data_, sdc.NeuronCompartment):
            self._compartmentTypeNames_ = list(sdc.NeuronCompartmentType.names())
        else:
            self._compartmentTypeNames_ = list(sdc.CellCompartmentType.names())
        self.typeComboBox.clear()
        for s in self._compartmentTypeNames_:
            self.typeComboBox.addItem(s)
        ndx = self._compartmentTypeNames_.index(self._data_.compartmentType.name)
        self.typeComboBox.setCurrentIndex(ndx)




    @Slot(int)
    def _slot_compartmentTypeChanged(self, val:int):
        cTypes = sdc.CellCompartmentType if isinstance(self._data_, sdc.CellCompartment) else sdc.NeuronCompartmentType
        self._data_.compartmentType = cTypes[self._compartmentTypeNames_[val]]
        self.sig_valueChanged.emit(self._data_)

    @Slot()
    def _slot_editParent(self):
        parent = self._data_.getParent()
        if parent is None:
            return

        # TODO: 2026-06-25 16:47:07 finalize me
        # what are the possible parents of the CellCompartment/NeuronCompartment
        # propose creating a new one (add create new button to these widgets)


