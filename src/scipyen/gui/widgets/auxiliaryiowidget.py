# -*- coding: utf-8 -*-
# $Id: auxiliaryinputwidget.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""

import sys, os, typing, types, warnings, math, cmath
import numbers
import numpy as np
import quantities as pq
import neo
from tribool import Tribool

import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, )
from qtpy.QtCore import (Signal, Slot, Property,)
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
__has_qtdbus__ = False

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

try:
    from qtpy import QtDBus
    __has_qtdbus__ = True
except:
    __has_qtdbus__ = False

from ephys.ephys import AuxiliaryInput, AuxiliaryOutput
from core.prog import scipywarn
from gui import guiutils

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

Ui_AuxiliaryInputWidget, QWidgetIn = loadUiType(
    os.path.join(__module_path__, "auxiliaryinputwidget.ui")
    )
Ui_AuxiliaryOutputWidget, QWidgetOut = loadUiType(
    os.path.join(__module_path__, "auxiliaryoutputwidget.ui")
    )

class AuxiliaryInputWidget(Ui_AuxiliaryInputWidget, QWidgetIn):
    sig_valueChanged = Signal(object, name="sig_valueChanged")

    defaultName: str = "aux_in"
    defaultChannel: int = 0
    defaultCmd: Tribool = Tribool()

    def __init__(self, parent:typing.Optional[QtWidgets.QWidget] = None,
                 obj: typing.Optional[AuxiliaryInput] = None):

        # if not isinstance(parent, QtWidgets.QWidget):
        #     if obj is None and isinstance(parent, AuxiliaryInput):
        #         obj = parent
        #     parent = None

        QWidget.__init__(self, parent=parent)

        if not isinstance(obj, AuxiliaryInput): # and obj is not None:
            # scipywarn(f"This widget does not support objects of type {type(obj).__name__}")
            self._data_ = None
        else:
            self._data_ = obj

        if self._data_ is not None:
            self._name_ = self._data_.name
            self._channel_ = self._data_.adc
            self._command_ = self._data_.cmd

        else:
            self._name_ = None
            self._channel_ = None
            self._command_ = None

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)
        self.nameLineEdit.undoAvailable=True
        self.nameLineEdit.redoAvailable=True
        self.nameLineEdit.setClearButtonEnabled(True)
        self.nameLineEdit.setToolTip("Name of the input")
        self.nameLineEdit.setWhatsThis("Name of the input")
        self.nameLineEdit.setStatusTip("Name of the input")
        if isinstance(self._name_, str) and len(self._name_.strip()):
            self.nameLineEdit.setText(self._name_)
        self.nameLineEdit.textChanged.connect(self._slot_nameChanged)

        self.channelSpinBox.setToolTip("Input channel index")
        self.channelSpinBox.setWhatsThis("Input channel index")
        self.channelSpinBox.setStatusTip("Input channel index")
        self.channelSpinBox.setMinimum(0)
        self.channelSpinBox.valueChanged.connect(self._slot_outputChannelChanged)

        self.isCommandCheckBox.setToolTip("Is proxy for a clamping command, TTL or any other waveform")
        self.isCommandCheckBox.setWhatsThis("Is proxy for a clamping command, TTL or any other waveform")
        self.isCommandCheckBox.setStatusTip("Is proxy for a clamping command, TTL or any other waveform")
        if isinstance(self._command_, Tribool):
            if self._command_.value is True:
                self.isCommandCheckBox.setCheckedState(Qt.Checked)
            elif self._command_.value is False:
                self.isCommandCheckBox.setCheckedState(Qt.Unchecked)
            else:
                self.isCommandCheckBox.setCheckedState(Qt.PartiallyChecked)
        self.isCommandCheckBox.toggled.connect(self._slot_isCommandChanged)

        self.createObjectPushButton.setText("")
        self.createObjectPushButton.setIcon(guiutils.getIcon("list-add"))
        self.createObjectPushButton.setToolTip("Create AuxiliaryInput")
        self.createObjectPushButton.setWhatsThis("Create AuxiliaryInput")
        self.createObjectPushButton.setStatusTip("Create AuxiliaryInput")

        self.createObjectPushButton.clicked.connect(self._slot_new)

    @Slot(str)
    def _slot_nameChanged(self, val:str):
        self._name_ = val
        self._make_value_()
        if isinstance(self._data_ , AuxiliaryInput):
            self.sig_valueChanged.emit(self.value())

    @Slot(bool)
    @Slot(QtCore.Qt.CheckState)
    def _slot_isCommandChanged(self, val: bool | QtCore.Qt.CheckState):
        if isinstance(val, bool):
            val = Tribool(val)

        else:
            if val == QtCore.Checked:
                val = Tribool(True)
            elif val == QtCore.Unchecked:
                val = Tribool(False)
            else:
                val = Tribool()

        self._command_ = val
        self._make_value_()
        if isinstance(self._data_ , AuxiliaryInput):
            self.sig_valueChanged.emit(self.value())

    @Slot(int)
    def _slot_outputChannelChanged(self, val:int):
        self._channel_ = val
        self._make_value_()
        if isinstance(self._data_ , AuxiliaryInput):
            self.sig_valueChanged.emit(self.value())

    @Slot()
    def _slot_new(self):
        self._make_value_()

    def _make_value_(self):
        if (isinstance(self._name_, str) and
            isinstance(self._channel_, int) and
            isinstance(self._command_, Tribool)
            ):
            self._data_ = AuxiliaryInput(self._name_, self._channel_, self._command_)

    def setValue(self, val:typing.Optional[AuxiliaryInput] = None):
        if isinstance(val, AuxiliaryInput):
            self._name_ = val.name
            self._channel_ = val.channel
            self._command_ = val.dig

            sigBlock = list(map(
                                lambda w: QtCore.QSignalBlocker(w),
                                (self.nameLineEdit,
                                 self.channelSpinBox,
                                 self.isCommandCheckBox)
                                )
                            )

            self.nameLineEdit.setText(self._name_)
            self.channelSpinBox.setValue(self._channel_)
            self.isCommandCheckBox.setChecked(self._command_ is True)

    def value(self) -> AuxiliaryInput:
        return self._data_

class AuxiliaryOutputWidget(Ui_AuxiliaryOutputWidget, QWidgetOut):
    sig_valueChanged = Signal(object, name="sig_valueChanged")

    defaultName: str = "aux_out"
    defaultChannel: int = 0
    defaultCmd: Tribool = Tribool()

    def __init__(self, parent:typing.Optional[QtWidgets.QWidget] = None,
                 obj: typing.Optional[AuxiliaryOutput] = None):

        # if not isinstance(parent, QtWidgets.QWidget):
        #     if obj is None and isinstance(parent, AuxiliaryOutput):
        #         obj = parent
        #     parent = None

        QWidget.__init__(self, parent=parent)

        if not isinstance(obj, AuxiliaryOutput): # and obj is not None:
            # scipywarn(f"This widget does not support objects of type {type(obj).__name__}")
            self._data_ = None
        else:
            self._data_ = obj

        if self._data_ is not None:
            self._name_ = self._data_.name
            self._channel_ = self._data_.channel
            self._command_ = self._data_.digttl

        else:
            self._name_ = None
            self._channel_ = None
            self._command_ = None

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)
        self.nameLineEdit.undoAvailable=True
        self.nameLineEdit.redoAvailable=True
        self.nameLineEdit.setClearButtonEnabled(True)
        self.nameLineEdit.setToolTip("Name of the output")
        self.nameLineEdit.setWhatsThis("Name of the output")
        self.nameLineEdit.setStatusTip("Name of the output")
        if isinstance(self._name_, str) and len(self._name_.strip()):
            self.nameLineEdit.setText(self._name_)
        self.nameLineEdit.textChanged.connect(self._slot_nameChanged)

        self.channelSpinBox.setToolTip("Output channel index")
        self.channelSpinBox.setWhatsThis("Output channel index")
        self.channelSpinBox.setStatusTip("Output channel index")
        self.channelSpinBox.setMinimum(0)
        self.channelSpinBox.valueChanged.connect(self._slot_outputChannelChanged)

        self.isDigTTLCheckBox.setToolTip("Sends or emulates TTL or any other commands")
        self.isDigTTLCheckBox.setWhatsThis("Sends or emulates TTL or any other commands")
        self.isDigTTLCheckBox.setStatusTip("Sends or emulates TTL or any other commands")
        if isinstance(self._command_, Tribool):
            if self._command_.value is True:
                self.isDigTTLCheckBox.setCheckedState(Qt.Checked)
            elif self._command_.value is False:
                self.isDigTTLCheckBox.setCheckedState(Qt.Unchecked)
            else:
                self.isDigTTLCheckBox.setCheckedState(Qt.PartiallyChecked)
        self.isDigTTLCheckBox.toggled.connect(self._slot_isTTLChanged)

        self.createObjectPushButton.setText("")
        self.createObjectPushButton.setIcon(guiutils.getIcon("list-add"))
        self.createObjectPushButton.setToolTip("Create AuxiliaryOutput")
        self.createObjectPushButton.setWhatsThis("Create AuxiliaryOutput")
        self.createObjectPushButton.setStatusTip("Create AuxiliaryOutput")

        self.createObjectPushButton.clicked.connect(self._slot_new)

    @Slot(str)
    def _slot_nameChanged(self, val:str):
        self._name_ = val
        self._make_value_()
        if isinstance(self._data_ , AuxiliaryOutput):
            self.sig_valueChanged.emit(self.value())

    @Slot(bool)
    @Slot(QtCore.Qt.CheckState)
    def _slot_isTTLChanged(self, val: bool | QtCore.Qt.CheckState):
        if isinstance(val, bool):
            val = Tribool(val)

        else:
            if val == QtCore.Checked:
                val = Tribool(True)
            elif val == QtCore.Unchecked:
                val = Tribool(False)
            else:
                val = Tribool()

        self._command_ = val
        self._make_value_()
        if isinstance(self._data_ , AuxiliaryOutput):
            self.sig_valueChanged.emit(self.value())

    @Slot(int)
    def _slot_outputChannelChanged(self, val:int):
        self._channel_ = val
        self._make_value_()
        if isinstance(self._data_ , AuxiliaryOutput):
            self.sig_valueChanged.emit(self.value())

    @Slot()
    def _slot_new(self):
        self._make_value_()

    def _make_value_(self):
        if (isinstance(self._name_, str) and
            isinstance(self._channel_, int) and
            isinstance(self._command_, Tribool)
            ):
            self._data_ = AuxiliaryOutput(self._name_, self._channel_, self._command_)

    def setValue(self, val:typing.Optional[AuxiliaryOutput] = None):
        if isinstance(val, AuxiliaryOutput):
            self._name_ = val.name
            self._channel_ = val.channel
            self._command_ = val.digttl

            sigBlock = list(map(
                                lambda w: QtCore.QSignalBlocker(w),
                                (self.nameLineEdit,
                                 self.channelSpinBox,
                                 self.isDigTTLCheckBox)
                                )
                            )

            self.nameLineEdit.setText(self._name_)
            self.channelSpinBox.setValue(self._channel_)
            state = Qt.Checked if self._command_.value is True else Qt.Unchecked if self._command_.value is False else Qt.PartiallyChecked
            self.isDigTTLCheckBox.setCheckedState(state)

    def value(self) -> AuxiliaryOutput:
        return self._data_



