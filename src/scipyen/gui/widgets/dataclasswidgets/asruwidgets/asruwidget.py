# -*- coding: utf-8 -*-
# $Id: asruwidget.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
TODO: 2026-07-17 10:15:32 FIXME
• in PPL widget: include a QCOmboBox to select one of the protocol(s) authorized on the PPL

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

Ui_ASRUWidget, QWidget = loadUiType(
    os.path.join(__module_path__, "asruwidget.ui")
    )

class ASRUWidget(Ui_ASRUWidget, DataClassWidget):
    _objectTypes_ = (sdc.PPL, sdc.PIL)

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
            obj = sdc.PIL()

        self._data_ = obj

        DataClassWidget.__init__(self, parent=parent, **kwargs)

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)

        super()._configureUI_()

        if isinstance(self._data_, sdc.PPL):
            pfx = "PPL"
        else:
            pfx = "PIL"

        self.licenseIDLabel.setText(f"{pfx} ID: ")
        self.holderNameLabel.setText(f"{pfx} Holder Name: ")
        self.holderEMailLabel.setText(f"{pfx} Holder e-mail: ")

        self.licenseIDLineEdit.lazy=True
        self.holderNameLineEdit.lazy=True
        self.holderEMailLineEdit.lazy=True

        self.licenseIDLineEdit.setText(self._data_.ID)
        self.holderNameLineEdit.setText(self._data_.holderName)
        self.holderEMailLineEdit.setText(self._data_.holderEmail)

        self.licenseIDLineEdit.sig_enterPressed.connect(self._slot_licenseIDChanged)
        self.holderNameLineEdit.sig_enterPressed.connect(self._slot_holderNameChanged)
        self.holderEMailLineEdit.sig_enterPressed.connect(self._slot_holderEmailChanged)


    @Slot(str)
    def _slot_licenseIDChanged(self, val: str):
        if not isinstance(val, str):
            val = ""

        self._data_.ID = val
        self.sig_valueChanged.emit(self._data_)

    @Slot(str)
    def _slot_holderNameChanged(self, val:str):
        if not isinstance(val, str):
            val = ""

        self._data_.holderName = val
        self.sig_valueChanged.emit(self._data)

    @Slot(str)
    def _slot_holderEmailChanged(self, val:str):
        if not isinstance(val, str):
            val = ""

        self._data_.holderEmail = val
        self.sig_valueChanged.emit(self._data)

    def value(self) -> sdc.PPL | sdc.PIL:
        return self._data_

    def setValue(self, value: sdc.PPL | sdc.PIL):
        if not isinstance(value, self._objectTypes_):
            self._data_ = sdc.PIL()

        self._data_ = value

        sbb = list( # noqa
            map(
                lambda w: QtCore.QSignalBlocker(w),
                (
                    self.licenseIDLineEdit,
                    self.holderNameLineEdit,
                    self.holderEMailLineEdit
                 )
                )
            )

        if isinstance(self._data_, sdc.PPL):
            pfx = "PPL"
        else:
            pfx = "PIL"

        self.licenseIDLabel.setText(f"{pfx} ID: ")
        self.holderNameLabel.setText(f"{pfx} Holder Name: ")
        self.holderEMailLabel.setText(f"{pfx} Holder e-mail: ")

        self.licenseIDLineEdit.setText(self._data_.ID)
        self.holderNameLineEdit.setText(self._data_.holderName)
        self.holderEMailLineEdit.setText(self._data_.holderEmail)

        self.sig_valueChanged.emit(self._data_)

