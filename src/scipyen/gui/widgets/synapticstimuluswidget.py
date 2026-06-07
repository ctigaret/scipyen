# -*- coding: utf-8 -*-
# $Id: synapticstimuluswidget.py $
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

from ephys.ephys import SynapticStimulus
from core.prog import scipywarn
from gui import guiutils

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

Ui_SynapticStimulusWidget, QWidget = loadUiType(
    os.path.join(__module_path__, "synapticstimuluswidget.ui")
    )

class SynapticStimulusWidget(Ui_SynapticStimulusWidget, QWidget):
    sig_valueChanged = Signal(SynapticStimulus, name="sig_valueChanged")

    defaultName: str = "stim"
    defaultChannel: int = 0
    defaultDigital: bool = True

    def __init__(self, parent:typing.Optional[QtWidgets.QWidget] = None,
                 obj: typing.Optional[SynapticStimulus] = None):

        if not isinstance(parent, QtWidgets.QWidget):
            if obj is None and isinstance(parent, SynapticStimulus):
                obj = parent
            parent = None

        QWidget.__init__(self, parent=parent)

        if not isinstance(obj, SynapticStimulus): # and obj is not None:
            # scipywarn(f"This widget does not support objects of type {type(obj).__name__}")
            self._data_ = None
        else:
            self._data_ = obj

        if self._data_ is not None:
            self._name_ = self._data_.name
            self._channel_ = self._data_.channel
            self._digital_ = self._data_.dig

        else:
            self._name_ = None
            self._channel_ = None
            self._digital_ = Tribool()

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)
        self.nameLineEdit.undoAvailable=True
        self.nameLineEdit.redoAvailable=True
        self.nameLineEdit.setClearButtonEnabled(True)
        self.nameLineEdit.setToolTip("Name of the stimulus")
        self.nameLineEdit.setWhatsThis("Name of the stimulus")
        self.nameLineEdit.setStatusTip("Name of the stimulus")
        if isinstance(self._name_, str) and len(self._name_.strip()):
            self.nameLineEdit.setText(self._name_)
        self.nameLineEdit.textChanged.connect(self._slot_nameChanged)

        self.outputChannelSpinBox.setToolTip("Output channel index")
        self.outputChannelSpinBox.setWhatsThis("Output channel index")
        self.outputChannelSpinBox.setStatusTip("Output channel index")
        self.outputChannelSpinBox.setMinimum(0)
        self.outputChannelSpinBox.valueChanged.connect(self._slot_outputChannelChanged)

        self.isDigitalCheckBox.setToolTip("Is digital channel")
        self.isDigitalCheckBox.setWhatsThis("Is digital channel")
        self.isDigitalCheckBox.setStatusTip("Is digital channel")
        if isinstance(self._digital_, bool):
            self.isDigitalCheckBox.setChecked(self._digital_ is True)
        self.isDigitalCheckBox.toggled.connect(self._slot_isDigitalChanged)

        self.createStimulusPushButton.setText("")
        self.createStimulusPushButton.setIcon(guiutils.getIcon("list-add"))
        self.createStimulusPushButton.setToolTip("Create stimulus")
        self.createStimulusPushButton.setWhatsThis("Create stimulus")
        self.createStimulusPushButton.setStatusTip("Create stimulus")

        self.createStimulusPushButton.clicked.connect(self._slot_new)

    @Slot(str)
    def _slot_nameChanged(self, val:str):
        self._name_ = val
        self._make_value_()
        if isinstance(self._data_ , SynapticStimulus):
            self.sig_valueChanged.emit(self.value())

    @Slot(bool)
    def _slot_isDigitalChanged(self, val: bool):
        self._digital_ = val is True
        self._make_value_()
        if isinstance(self._data_ , SynapticStimulus):
            self.sig_valueChanged.emit(self.value())

    @Slot(int)
    def _slot_outputChannelChanged(self, val:int):
        self._channel_ = val
        self._make_value_()
        if isinstance(self._data_ , SynapticStimulus):
            self.sig_valueChanged.emit(self.value())

    @Slot()
    def _slot_new(self):
        self._make_value_()

    def _make_value_(self):
        if (isinstance(self._name_, str) and
            isinstance(self._channel_, int) and
            isinstance(self._digital_, bool)
            ):
            self._data_ = SynapticStimulus(self._name_, self._channel_, self._digital_)

    def setValue(self, val:typing.Optional[SynapticStimulus] = None):
        if isinstance(val, SynapticStimulus):
            self._name_ = val.name
            self._channel_ = val.channel
            self._digital_ = val.dig is True

            sigBlock = list(map(
                                lambda w: QtCore.QSignalBlocker(w),
                                (self.nameLineEdit,
                                 self.outputChannelSpinBox,
                                 self.isDigitalCheckBox)
                                )
                            )

            self.nameLineEdit.setText(self._name_)
            self.outputChannelSpinBox.setValue(self._channel_)
            self.isDigitalCheckBox.setChecked(self._digital_ is True)

    def value(self) -> SynapticStimulus:
        return self._data_



