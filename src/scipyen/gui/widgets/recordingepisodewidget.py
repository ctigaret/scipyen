# -*- coding: utf-8 -*-
# $Id: recordingepisodewidget.py $
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

from ephys import ephys
from ephys import pathways
from core import datatypes
from core.prog import scipywarn
from gui import guiutils

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

Ui_RecordingEpisodeWidget, QWidget = loadUiType(
    os.path.join(__module_path__, "recordingepisodewidget.ui")
    )


class RecordingEpisodeWidget(Ui_RecordingEpisodeWidget, QWidget):
    sig_valueChanged = Signal(object, name="sig_valueChanged")

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None,
                 obj: typing.Optional[pathways.RecordingEpisode] = None):
        # print(f"{self.__class__.__name__}.__init__(parent={parent}, obj={obj})")

        if isinstance(parent, pathways.RecordingEpisode):
            obj_ = parent
            if isinstance(obj, QtWidgets.QWidget):
                parent = obj
            else:
                parent = None

            obj = obj_


        QWidget.__init__(self, parent=parent)

        if not isinstance(obj, pathways.RecordingEpisode):
            self._data_ = None
        else:
            self._data_ = obj

        self._recordingEpisodeNames_ = list(pathways.RecordingEpisodeType.names())

        if isinstance(self._data_, pathways.RecordingEpisode):
            self._name_ = self._data_.name
            self._blocks_ = self._data_.blocks
            self._type_ = self._data_._type_
            self._begin_ = self._data_._begin_
            self._end_ = self._data_._end_
            self._beginFrame_ = self._data_._beginFrame_
            self._endFrame_ = self._data_._endFrame_
            self._protocol_ = self._data_._protocol_

        else:
            self._name_ = "Episode"
            self._blocks_ = list()
            self._type_ = pathways.RecordingEpisodeType.Tracking
            self._begin_ = datetime.datetime.now()
            self._end_ = datetime.datetime.now()
            self._beginFrame_ = 0
            self._endFrame_ = 0
            self._protocol_ = None


        self._configureUI_()

        if self._data_ is None:
            self._make_value_()

    def _configureUI_(self):
        self.setupUi(self)

        self.nameLineEdit.undoAvailable=True
        self.nameLineEdit.redoAvailable=True
        self.nameLineEdit.setClearButtonEnabled(True)
        self.nameLineEdit.setToolTip("Name of the recording source")
        self.nameLineEdit.setWhatsThis("Name of the recording source")
        self.nameLineEdit.setStatusTip("Name of the recording source")

        if isinstance(self._name_, str) and len(self._name_.strip()):
            self.nameLineEdit.setText(self._name_)
        self.nameLineEdit.textChanged.connect(self._slot_nameChanged)

        if isinstance(self._protocol_, ephys.ElectrophysiologyProtocol):
            self.protocolNameLabel.setText(self._protocol_.name)
        else:
            self.protocolNameLabel.setText("")

        self.adcSpinBox.setToolTip("Index of ADC (input) channel used for recording")
        self.adcSpinBox.setWhatsThis("Index of ADC (input) channel used for recording")
        self.adcSpinBox.setStatusTip("Index of ADC (input) channel used for recording")
        self.adcSpinBox.setMinimum(0)
        if isinstance(self._adc_, int) and self._adc_ >= 0:
            self.adcSpinBox.setValue(self._adc_)
        self.adcSpinBox.valueChanged.connect(self._slot_adcChanged)

        self.dacSpinBox.setToolTip("Input channel index")
        self.dacSpinBox.setWhatsThis("Input channel index")
        self.dacSpinBox.setStatusTip("Input channel index")
        self.dacSpinBox.setMinimum(0)
        if isinstance(self._dac_, int) and self._dac_ >= 0:
            self.dacSpinBox.setValue(self._dac_)
        self.dacSpinBox.valueChanged.connect(self._slot_dacChanged)

        for text in self._recordingEpisodeNames_:
            self.electrodeModeComboBox.addItem(text)

        currentElectrodeModeNdx = self._recordingEpisodeNames_.index(self._electrode_.name)
        self.electrodeModeComboBox.setCurrentIndex(currentElectrodeModeNdx)

        # self.electrodeModeComboBox.currentIndexChanged.connect(self._slot_electrodeModeChanged)
        self.electrodeModeComboBox.currentTextChanged.connect(self._slot_electrodeModeChanged)

        self.stimulusPushButton.clicked.connect(self._slot_editStimulus)
        self.auxInPushButton.clicked.connect(self._slot_editAuxIn)
        self.auxOutPushButton.clicked.connect(self._slot_editAuxOut)

        self.createObjectPushButton.setText("")
        self.createObjectPushButton.setIcon(guiutils.getIcon("list-add"))
        self.createObjectPushButton.setToolTip("Create Recording Source")
        self.createObjectPushButton.setWhatsThis("Create Recording Source")
        self.createObjectPushButton.setStatusTip("Create Recording Source")

        self.createObjectPushButton.clicked.connect(self._slot_new)
        self.createObjectPushButton.setEnabled(self._data_ is None)

    @Slot(str)
    def _slot_nameChanged(self, val:str):
        self._name_ = val
        if not isinstance(self._data_, pathways.RecordingSource):
            self._make_value_()
        else:
            self._data_.name = val

        self.sig_valueChanged.emit(self.value())

    @Slot(int)
    def _slot_adcChanged(self, val: int):
        self._adc_ = val
        if not isinstance(self._data_, pathways.RecordingSource):
            self._make_value_()
        else:
            self._data_.adc = self._adc_

        self.sig_valueChanged.emit(self.value())

    @Slot(int)
    def _slot_dacChanged(self, val: int):
        self._dac_ = val
        if not isinstance(self._data_, pathways.RecordingSource):
            self._make_value_()
        else:
            self._data_.dac = self._dac_

        self.sig_valueChanged.emit(self.value())

    @Slot(str)
    @Slot(int)
    def _slot_electrodeModeChanged(self, val: int | str):
        if isinstance(val, int) and val >=0 and val < len(self._recordingEpisodeNames_):
            val = self._recordingEpisodeNames_[val]

        if isinstance(val, str):
            if val in self._recordingEpisodeNames_:
                self._electrode_ = ephys.ElectrodeMode[val]
            else:
                return
        else:
            return

        if not isinstance(self._data_, pathways.RecordingSource):
            self._make_value_()
        else:
            self._data_.electrodeMode = self._electrode_

        self.sig_valueChanged.emit(self.value())

    @Slot()
    def _slot_new(self):
        self._make_value_()

    def _make_value_(self):
        self._data_ = pathways.RecordingSource(name=self._name_, adc=self._adc_,
                                            dac=self._dac_, syn=self._syn_,
                                            auxin=self._auxin_,
                                            auxout=self._auxout_,
                                            electrodeMode = self._electrode_)
        self.createObjectPushButton.setEnabled(self._data_ is None)

    @Slot()
    def _slot_editStimulus(self):
        from gui.delegates import ExternalEditorDelegate
        # print(f"{self.__class__.__name__}[{self.objectName()}]._slot_editStimulus: {self._syn_}")
        stimEditor = ExternalEditorDelegate(self._syn_, self)
        stimEditor.setObjectName("stimEditor")
        stimEditor.sig_valueChanged.connect(self._slot_stimulusChanged)
        stimEditor.slot_Launch()

    @Slot()
    def _slot_editAuxIn(self):
        from gui.delegates import ExternalEditorDelegate
        editor = ExternalEditorDelegate(self._auxin_, self)
        editor.setObjectName("auxInEditor")
        editor.sig_valueChanged.connect(self._slot_stimulusChanged)
        editor.slot_Launch()

    @Slot()
    def _slot_editAuxOut(self):
        from gui.delegates import ExternalEditorDelegate
        editor = ExternalEditorDelegate(self._auxou_, self)
        editor.setObjectName("auxOutEditor")
        editor.sig_valueChanged.connect(self._slot_stimulusChanged)
        editor.slot_Launch()

    @Slot(object)
    def _slot_stimulusChanged(self, val):
        # print(f"{self.__class__.__name__}[{self.objectName()}]._slot_stimulusChanged({val})")
        if isinstance(val, pathways.SynapticStimulusChannel):
            self._syn_ = val
            self._make_value_()
            self.sig_valueChanged.emit(self._data_)

    @Slot(object)
    def slot_valueChanged(self, val):
        self._data_ = val

    def setValue(self, val: typing.Optional[pathways.SynapticPathway] = None):
        print(f"{self.__class__.__name__}.setValue({val}) <{type(val).__name__}>")
        if isinstance(val, pathways.SynapticPathway):
            self._data_ = val
            self._name_ = self._data_.name
            self._adc_ = self._data_.adc
            self._dac_ = self._data_.dac
            self._syn_ = self._data_.syn
            self._auxin_ = self._data_.auxin
            self._auxout_ = self._data_.auxout
            self._electrode_ = self._data_.electrodeMode
            self._pathways_ = self._data_.pathways

            sigBlock = list(map(
                                lambda w: QtCore.QSignalBlocker(w),
                                (
                                    self.nameLineEdit,
                                    self.adcSpinBox,
                                    self.dacSpinBox,
                                    self.electrodeModeComboBox,
                                    self.pathTypeComboBox,
                                    self.stimulusPushButton,
                                    self.auxOutPushButton,
                                 )
                                )
                            )

            self.nameLineEdit.setText(self._name_)
            self.adcSpinBox.setValue(self._adc_)
            self.dacSpinBox.setValue(self._dac_)


            currentElectrodeModeNdx = self._recordingEpisodeNames_.index(self._electrode_.name)
            currentPathwayTypeNdx = self._pathwayTypeNames_.index(self._pathType_.name)

            self.electrodeModeComboBox.setCurrentIndex(currentElectrodeModeNdx)

    def value(self) -> pathways.RecordingSource:
        return self._data_

