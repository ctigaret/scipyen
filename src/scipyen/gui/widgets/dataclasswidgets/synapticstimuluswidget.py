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

from ephys import ephys_pathways
from ephys.ephys_pathways import SynapticStimulusChannel
from core import qtutils
from core.prog import scipywarn
from gui import guiutils
from gui.widgets.dataclasswidgets.dataclasswidget import DataClassWidget

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

try:
    from gui.widgets.dataclasswidgets.synapticstimuluswidget_ui import Ui_SynapticStimulusChannelWidget

except:
    Ui_SynapticStimulusChannelWidget, QWidget = loadUiType(
        os.path.join(__module_path__, "synapticstimuluswidget.ui")
        )

class SynapticStimulusChannelWidget(Ui_SynapticStimulusChannelWidget, DataClassWidget, QtWidgets.QWidget):
    sig_valueChanged = Signal(object, name="sig_valueChanged")

    defaultName: str = "stim"
    defaultChannel: int = 0
    defaultDigital: bool = True
    _objectTypes_ = (SynapticStimulusChannel, )
    _objectType_ = SynapticStimulusChannel

    def __init__(self, parent:typing.Optional[QtWidgets.QWidget] = None,
                 obj: typing.Optional[SynapticStimulusChannel] = None,
                 **kwargs):
        if isinstance(parent, self._objectTypes_):
            obj_ = parent
            if isinstance(obj, QtWidgets.QWidget):
                parent = obj
            else:
                parent = None

            obj = obj_

        if not isinstance(obj, self._objectTypes_):
            self._name_ = "Stim"
            self._channel_ = 0
            self._digital_ = Tribool()
            self._make_value_()
        else:
            self._data_ = obj
            self._name_ = self._data_.name
            self._channel_ = self._data_.channel
            self._digital_ = self._data_.dig

        QtWidgets.QWidget.__init__(self, parent)
        DataClassWidget.__init__(self, parent=parent, **kwargs)
        Ui_SynapticStimulusChannelWidget.__init__(self)
        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)
        super()._configureUI_() # DataClassWidget!
        # self.nameLineEdit.undoAvailable=True
        # self.nameLineEdit.redoAvailable=True
        # self.nameLineEdit.setClearButtonEnabled(True)
        # self.nameLineEdit.setToolTip("Name of the stimulus")
        # self.nameLineEdit.setWhatsThis("Name of the stimulus")
        # self.nameLineEdit.setStatusTip("Name of the stimulus")
        # if isinstance(self._name_, str) and len(self._name_.strip()):
        #     self.nameLineEdit.setText(self._name_)
        # self.nameLineEdit.textChanged.connect(self._slot_nameChanged)

        self.nameDescriptionWidget.symbol="stimulus"
        self.outputChannelSpinBox.setToolTip("Output channel index")
        self.outputChannelSpinBox.setWhatsThis("Output channel index")
        self.outputChannelSpinBox.setStatusTip("Output channel index")
        self.outputChannelSpinBox.setMinimum(0)
        if isinstance(self._channel_, int) and self._channel_ >= 0:
            self.outputChannelSpinBox.setValue(self._channel_)
        self.outputChannelSpinBox.valueChanged.connect(self._slot_outputChannelChanged)

        self.isDigitalCheckBox.setToolTip("Is digital channel")
        self.isDigitalCheckBox.setWhatsThis("Is digital channel")
        self.isDigitalCheckBox.setStatusTip("Is digital channel")
        if isinstance(self._digital_, bool):
            self.isDigitalCheckBox.setChecked(self._digital_ is True)
        self.isDigitalCheckBox.toggled.connect(self._slot_isDigitalChanged)

        self.createObjectPushButton.setText("")
        self.createObjectPushButton.setIcon(guiutils.getIcon("list-add"))
        self.createObjectPushButton.setToolTip("Create Stimulus")
        self.createObjectPushButton.setWhatsThis("Create Stimulus")
        self.createObjectPushButton.setStatusTip("Create Stimulus")

        self.createObjectPushButton.clicked.connect(self._slot_new)
        self.createObjectPushButton.setEnabled(self._data_ is None)

    @Slot(bool)
    def _slot_isDigitalChanged(self, val: bool):
        self._digital_ = val is True
        if not isinstance(self._data_ , SynapticStimulusChannel):
            self._make_value_()
        else:
            self._data_.dig = self._digital_

        if isinstance(self._data_ , SynapticStimulusChannel):
            self.sig_valueChanged.emit(self.value())

    @Slot(int)
    def _slot_outputChannelChanged(self, val:int):
        self._channel_ = val

        if not isinstance(self._data_ , SynapticStimulusChannel):
            self._make_value_()

        else:
            self._data_.channel = self._channel_

        if isinstance(self._data_ , SynapticStimulusChannel):
            self.sig_valueChanged.emit(self.value())

    @Slot()
    def _slot_new(self):
        self._make_value_()

    def _make_value_(self):
        if (isinstance(self._name_, str) and
            isinstance(self._channel_, int) and
            isinstance(self._digital_, bool)
            ):
            self._data_ = SynapticStimulusChannel(
                name=self._name_, channel=self._channel_, dig=self._digital_
                )
        else:
            self._data_ = SynapticStimulusChannel()

        self.createObjectPushButton.setEnabled(self._data_ is None)

    def setValue(self, val:typing.Optional[SynapticStimulusChannel] = None):
        if isinstance(val, SynapticStimulusChannel):
            self._name_ = val.name
            self._channel_ = val.channel
            self._digital_ = val.dig is True

            with qtutils.SignalBlocker(
                    (
                        self.nameDescriptionWidget,
                        self.outputChannelSpinBox,
                        self.isDigitalCheckBox
                    )
                ):
                self.nameDescriptionWidget.dataName = self._name_
                self.outputChannelSpinBox.setValue(self._channel_)
                self.isDigitalCheckBox.setChecked(self._digital_ is True)

    def value(self) -> SynapticStimulusChannel:
        return self._data_



