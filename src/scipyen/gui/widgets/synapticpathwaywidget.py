# -*- coding: utf-8 -*-
# $Id: synapticpathwaywidget.py $
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

from ephys import (ephys, ephys_pathways)
from core.prog import scipywarn
from gui import guiutils

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

Ui_SynapticPathwayWidget, QWidget = loadUiType(
    os.path.join(__module_path__, "synapticpathwaywidget.ui")
    )


class SynapticPathwayWidget(Ui_SynapticPathwayWidget, QWidget):
    sig_valueChanged = Signal(object, name="sig_valueChanged")

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None,
                 obj: typing.Optional[ephys_pathways.SynapticPathway] = None):
        # print(f"{self.__class__.__name__}.__init__(parent={parent}, obj={obj})")

        if isinstance(parent, ephys_pathways.SynapticPathway):
            obj_ = parent
            if isinstance(obj, QtWidgets.QWidget):
                parent = obj
            else:
                parent = None

            obj = obj_


        QWidget.__init__(self, parent=parent)

        if not isinstance(obj, ephys_pathways.SynapticPathway):
            self._data_ = None
        else:
            self._data_ = obj

        # print(f"\tself._data_: {self._data_}")

        if isinstance(self._data_, ephys_pathways.SynapticPathway):
            self._name_ = self._data_.name
            self._adc_ = self._data_.adc
            self._dac_ = self._data_.dac
            self._stimulus_ = self._data_.stimulus
            self._electrode_ = self._data_.electrodeMode
            self._pathType_ = self._data_.pathwayType
            self._schedule_ = self._data_.schedule
            self._measurements_ = self._data_.measurements

        else:
            self._name_ = "pathway"
            self._adc_ = 0
            self._dac_ = 0
            self._stimulus_ = ephys_pathways.SynapticStimulusChannel()
            self._electrode_ = ephys.ElectrodeMode.Null
            self._pathType_ = ephys_pathways.SynapticPathwayType.Null
            self._schedule_ = ephys_pathways.RecordingSchedule()
            self._measurements_ = dict()
            self._make_value_()

        self._electrodeModeNames_ = list(ephys.ElectrodeMode.names())
        self._pathwayTypeNames_ = list(ephys_pathways.SynapticPathwayType.names())

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)

        self.nameLineEdit.undoAvailable=True
        self.nameLineEdit.redoAvailable=True
        self.nameLineEdit.setClearButtonEnabled(True)
        self.nameLineEdit.setToolTip("Name of the pathway")
        self.nameLineEdit.setWhatsThis("Name of the pathway")
        self.nameLineEdit.setStatusTip("Name of the pathway")

        if isinstance(self._name_, str) and len(self._name_.strip()):
            self.nameLineEdit.setText(self._name_)
        self.nameLineEdit.textChanged.connect(self._slot_nameChanged)

        self.adcSpinBox.setToolTip("Input channel index")
        self.adcSpinBox.setWhatsThis("Input channel index")
        self.adcSpinBox.setStatusTip("Input channel index")
        self.adcSpinBox.setMinimum(0)
        if isinstance(self._adc_, int) and self._adc_ >= 0:
            self.adcSpinBox.setValue(self._adc_)
        self.adcSpinBox.valueChanged.connect(self._slot_adcChanged)

        self.dacSpinBox.setToolTip("Input channel index")
        self.dacSpinBox.setWhatsThis("Input channel index")
        self.dacSpinBox.setStatusTip("Input channel index")
        self.dacSpinBox.setMinimum(0)
        if isinstance(self._dac_, int) and self._dac_ >= 0 :
            self.dacSpinBox.setValue(self._dac_)
        self.dacSpinBox.valueChanged.connect(self._slot_dacChanged)

        for text in self._electrodeModeNames_:
            self.electrodeModeComboBox.addItem(text)

        currentElectrodeModeNdx = self._electrodeModeNames_.index(self._electrode_.name)
        self.electrodeModeComboBox.setCurrentIndex(currentElectrodeModeNdx)

        # self.electrodeModeComboBox.currentIndexChanged.connect(self._slot_electrodeModeChanged)
        self.electrodeModeComboBox.currentTextChanged.connect(self._slot_electrodeModeChanged)

        for text in self._pathwayTypeNames_:
            self.pathTypeComboBox.addItem(text)

        currentPathwayTypeNdx = self._pathwayTypeNames_.index(self._pathType_.name)

        self.pathTypeComboBox.setCurrentIndex(currentPathwayTypeNdx)
        # self.pathTypeComboBox.currentIndexChanged.connect(self._slot_pathwayTypeChanged)
        self.pathTypeComboBox.currentTextChanged.connect(self._slot_pathwayTypeChanged)

        self.stimulusPushButton.clicked.connect(self._slot_editStimulus)

        self.createObjectPushButton.setText("")
        self.createObjectPushButton.setIcon(guiutils.getIcon("list-add"))
        self.createObjectPushButton.setToolTip("Create Synaptic Pathway")
        self.createObjectPushButton.setWhatsThis("Create Synaptic Pathway")
        self.createObjectPushButton.setStatusTip("Create Synaptic Pathway")

        self.createObjectPushButton.clicked.connect(self._slot_new)
        self.createObjectPushButton.setEnabled(self._data_ is None)

    @Slot(str)
    def _slot_nameChanged(self, val:str):
        self._name_ = val
        if not isinstance(self._data_, ephys_pathways.SynapticPathway):
            self._make_value_()
        else:
            self._data_.name = val

        self.sig_valueChanged.emit(self.value())

    @Slot(int)
    def _slot_adcChanged(self, val: int):
        self._adc_ = val
        if not isinstance(self._data_, ephys_pathways.SynapticPathway):
            self._make_value_()
        else:
            self._data_.adc = self._adc_

        self.sig_valueChanged.emit(self.value())

    @Slot(int)
    def _slot_dacChanged(self, val: int):
        self._dac_ = val
        if not isinstance(self._data_, ephys_pathways.SynapticPathway):
            self._make_value_()
        else:
            self._data_.dac = self._dac_

        self.sig_valueChanged.emit(self.value())

    @Slot(str)
    @Slot(int)
    def _slot_pathwayTypeChanged(self, val: int | str):
        if isinstance(val, int) and val >=0 and val < len(self._pathwayTypeNames_):
            val = self._pathwayTypeNames_[val]

        if isinstance(val, str):
            if val in self._pathwayTypeNames_:
                self._pathType_ = ephys_pathways.SynapticPathwayType[val]
            else:
                return
        else:
            return

        if not isinstance(self._data_, ephys_pathways.SynapticPathway):
            self._make_value_()
        else:
            self._data_.pathwayType = self._pathType_

        self.sig_valueChanged.emit(self.value())

    @Slot(str)
    @Slot(int)
    def _slot_electrodeModeChanged(self, val: int | str):
        if isinstance(val, int) and val >=0 and val < len(self._electrodeModeNames_):
            val = self._electrodeModeNames_[val]

        if isinstance(val, str):
            if val in self._electrodeModeNames_:
                self._electrode_ = ephys.ElectrodeMode[val]
            else:
                return
        else:
            return

        if not isinstance(self._data_, ephys_pathways.SynapticPathway):
            self._make_value_()
        else:
            self._data_.electrodeMode = self._electrode_

        self.sig_valueChanged.emit(self.value())

    @Slot()
    def _slot_new(self):
        self._make_value_()

    def _make_value_(self):
        self._data_ = ephys_pathways.SynapticPathway(self._name_, self._adc_, self._dac_,
                                      self._stimulus_, self._electrode_,
                                      self._pathType_, self._schedule_,
                                      self._measurements_)
        self.createObjectPushButton.setEnabled(self._data_ is None)

    @Slot()
    def _slot_editStimulus(self):
        from gui.delegates import ExternalEditorDelegate
        # print(f"{self.__class__.__name__}[{self.objectName()}]._slot_editStimulus: {self._stimulus_}")
        stimEditor = ExternalEditorDelegate(self._stimulus_, self)
        stimEditor.setObjectName("stimEditor")
        stimEditor.sig_valueChanged.connect(self._slot_stimulusChanged)
        stimEditor.slot_Launch()


    @Slot(object)
    def _slot_stimulusChanged(self, val):
        # print(f"{self.__class__.__name__}[{self.objectName()}]._slot_stimulusChanged({val})")
        if isinstance(val, ephys_pathways.SynapticStimulusChannel):
            self._stimulus_ = val
            self._make_value_()
            self.sig_valueChanged.emit(self._data_)


    @Slot(object)
    def slot_valueChanged(self, val):
        # print(f"{self.__class__.__name__}[{self.objectName()}].slot_valueChanged({val})")
        self._data_ = val
        # print(f"\t=>{self._data_}")

    def setValue(self, val: typing.Optional[ephys_pathways.SynapticPathway] = None):
        # print(f"{self.__class__.__name__}.setValue({val}) <{type(val).__name__}>")
        if isinstance(val, ephys_pathways.SynapticPathway):
            self._data_ = val
            self._name_ = self._data_.name
            self._adc_ = self._data_.adc
            self._dac_ = self._data_.dac
            self._stimulus_ = self._data_.stimulus
            self._electrode_ = self._data_.electrodeMode
            self._pathType_ = self._data_.pathwayType
            self._schedule_ = self._data_.schedule
            self._measurements_ = self._data_.measurements

            sigBlock = list(map(
                                lambda w: QtCore.QSignalBlocker(w),
                                (
                                    self.nameLineEdit,
                                    self.adcSpinBox,
                                    self.dacSpinBox,
                                    self.electrodeModeComboBox,
                                    self.pathTypeComboBox,
                                    self.stimulusPushButton,
                                    self.schedulePushButton,
                                    self.measurementsPushButton,
                                 )
                                )
                            )

            self.nameLineEdit.setText(self._name_)
            self.adcSpinBox.setValue(self._adc_)
            self.dacSpinBox.setValue(self._dac_)


            currentElectrodeModeNdx = self._electrodeModeNames_.index(self._electrode_.name)
            currentPathwayTypeNdx = self._pathwayTypeNames_.index(self._pathType_.name)

            self.electrodeModeComboBox.setCurrentIndex(currentElectrodeModeNdx)
            self.pathTypeComboBox.setCurrentIndex(currentPathwayTypeNdx)

    def value(self) -> ephys_pathways.SynapticPathway:
        return self._data_

