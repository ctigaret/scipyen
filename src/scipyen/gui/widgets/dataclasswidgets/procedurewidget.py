# -*- coding: utf-8 -*-
# $Id: procedurewidget.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""

import sys, os, typing, types, warnings, math, cmath, datetime # noqa
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, )
from qtpy.QtCore import (Signal, Slot)#, Property,)
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6 # noqa
    from PySide6 import Shiboken # noqa
    from PySide6.QtCore import (Signal, Slot, Property,)
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


# from core.prog import scipywarn
# from core import scipyen_quantities as scq
from core import scipyendataclasses as sdc
from gui.widgets.dataclasswidgets.dataclasswidget import DataClassWidget

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

Ui_ProcedureWidget, _ = loadUiType(
    os.path.join(__module_path__, "procedurewidget.ui")
    )

class ProcedureWidget(Ui_ProcedureWidget, DataClassWidget):
    _objectTypes_ = (sdc.Procedure, )
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
            obj = sdc.Procedure()

        self._data_ = obj

        self._procedureTypeNames_ = list(sdc.ProcedureType.names())

        DataClassWidget.__init__(self, parent=parent, **kwargs)

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)

        super()._configureUI_()

        ndx = self._procedureTypeNames_.index(self._data_.procedureType.name)
        self.typeComboBox.addItems(self._procedureTypeNames_)
        self.typeComboBox.setCurrentIndex(ndx)
        self.typeComboBox.currentIndexChanged.connect(self._slot_procedureTypeChanged)

    def value(self) -> sdc.Procedure:
        return self._data_

    def setValue(self, val: sdc.Procedure):
        if not isinstance(val, sdc.Procedure):
            val = sdc.Procedure()

        self._data_ = val

        sb = QtCore.QSignalBlocker(self.typeComboBox)
        ndx = self._procedureTypeNames_.index(self._data_.procedureType)
        self.typeComboBox.setCurrentIndex(ndx)

    @Slot(int)
    def _slot_procedureTypeChanged(self, val: int):
        self._data_.procedureType = sdc.ProcedureType[self._procedureTypeNames_[val]]
        self.sig_valueChanged.emit(self._data_)


