# -*- coding: utf-8 -*-
# $Id: recordingepisodewidget.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""

import sys
import os
import typing
import types
import warnings
import math
import cmath
import numbers
import datetime
import traceback
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
    import PySide6 # noqa
    from PySide6 import Shiboken # noqa
    # from PySide6.QtCore import (Signal, Slot, Property,)
    from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True

    from qtpy import sip # noqa
    from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True

try:
    from qtpy import QtDBus # noqa
    __has_qtdbus__ = True
except:
    __has_qtdbus__ = False

from ephys import ephys
from ephys import ephys_pathways
from core import datatypes # noqa
from core.prog import scipywarn
from core import qtutils
from iolib import pictio as pio
from gui import (guiutils, interact)

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

Ui_RecordingEpisodeWidget, QWidget = loadUiType(
    os.path.join(__module_path__, "recordingepisodewidget.ui")
    )


class RecordingEpisodeWidget(Ui_RecordingEpisodeWidget, QWidget):
    sig_valueChanged = Signal(object, name="sig_valueChanged")

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None,
                 obj: typing.Optional[ephys_pathways.RecordingEpisode] = None):
        # print(f"{self.__class__.__name__}.__init__(parent={parent}, obj={obj})")

        if isinstance(parent, ephys_pathways.RecordingEpisode):
            obj_ = parent
            if isinstance(obj, QtWidgets.QWidget):
                parent = obj
            else:
                parent = None

            obj = obj_


        QWidget.__init__(self, parent=parent)

        if not isinstance(obj, ephys_pathways.RecordingEpisode):
            self._data_ = None
        else:
            self._data_ = obj

        self._recordingEpisodeNames_ = list(ephys_pathways.RecordingEpisodeType.names())

        if isinstance(self._data_, ephys_pathways.RecordingEpisode):
            self._name_ = self._data_.name
            self._blocks_ = self._data_.blocks
            self._episodeType_ = self._data_.type
            self._begin_ = self._data_.begin
            self._end_ = self._data_.end
            self._beginFrame_ = self._data_.beginFrame
            self._endFrame_ = self._data_.endFrame
            self._protocol_ = self._data_.protocol
            self._stimulusLayout_ = self._data_.stimulusLayout

        else:
            self._name_ = "Episode"
            self._blocks_ = list()
            self._episodeType_ = ephys_pathways.RecordingEpisodeType.Tracking
            self._begin_ = datetime.datetime.now()
            self._end_ = datetime.datetime.now()
            self._beginFrame_ = 0
            self._endFrame_ = 0
            self._protocol_ = None
            self._stimulusLayout_ = None

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

        for text in self._recordingEpisodeNames_:
            self.episodeTypeComboBox.addItem(text)

        currentEpisodeTypeNdx = self._recordingEpisodeNames_.index(self._episodeType_.name)
        self.episodeTypeComboBox.setCurrentIndex(currentEpisodeTypeNdx)
        self.episodeTypeComboBox.currentTextChanged.connect(self._slot_episodeTypeChanged)

        self.episodeBeginDateTimeEdit.setToolTip("Date/time for the start of episode")
        self.episodeBeginDateTimeEdit.setWhatsThis("Date/time for the start of episode")
        self.episodeBeginDateTimeEdit.setStatusTip("Date/time for the start of episode")
        if isinstance(self._begin_, datetime.datetime):
            self.episodeBeginDateTimeEdit.setDateTime(qtutils.datetime2Qt(self._begin_))

        self.episodeBeginDateTimeEdit.dateTimeChanged.connect(self._slot_beginDateTimeChanged)

        self.episodeEndDateTimeEdit.setToolTip("Date/time for the end of episode (inclusive)")
        self.episodeEndDateTimeEdit.setWhatsThis("Date/time for the end of episode (inclusive)")
        self.episodeEndDateTimeEdit.setStatusTip("Date/time for the end of episode (inclusive)")
        if isinstance(self._end_, datetime.datetime):
            self.episodeEndDateTimeEdit.setDateTime(qtutils.datetime2Qt(self._begin_))

        self.episodeEndDateTimeEdit.dateTimeChanged.connect(self._slot_endDateTimeChanged)

        self.firstFrameSpinBox.setToolTip("Index of the first frame (sweep) in data")
        self.firstFrameSpinBox.setWhatsThis("Index of the first frame (sweep) in data")
        self.firstFrameSpinBox.setStatusTip("Index of the first frame (sweep) in data")
        self.firstFrameSpinBox.setMinimum(0)
        if isinstance(self._beginFrame_, int) and self._beginFrame_ >= 0:
            self.firstFrameSpinBox.setValue(self._beginFrame_)

        self.firstFrameSpinBox.valueChanged.connect(self._slot_firstFrameChanged)

        self.lastFrameSpinBox.setToolTip("Input channel index")
        self.lastFrameSpinBox.setWhatsThis("Input channel index")
        self.lastFrameSpinBox.setStatusTip("Input channel index")
        self.lastFrameSpinBox.setMinimum(0)
        if isinstance(self._endFrame_, int) and self._endFrame_ >= 0:
            self.lastFrameSpinBox.setValue(self._endFrame_)
        self.lastFrameSpinBox.valueChanged.connect(self._slot_lastFrameChanged)

        self.createObjectPushButton.setText("")
        self.createObjectPushButton.setIcon(guiutils.getIcon("list-add"))
        self.createObjectPushButton.setToolTip("Create Recording Episode")
        self.createObjectPushButton.setWhatsThis("Create Recording Episode")
        self.createObjectPushButton.setStatusTip("Create Recording Episode")

        self.createObjectPushButton.clicked.connect(self._slot_new)
        self.createObjectPushButton.setEnabled(self._data_ is None)

        self.importTrialsToolButton.triggered.connect(self._slot_importTrials)
        self.openTrialsToolButton.triggered.connect(self._slot_loadTrials)
        self.trialsInfoLabel.setText(f"{len(self._blocks_)} Trials")

    @Slot(QtCore.QDateTime)
    def _slot_beginDateTimeChanged(self, val: QtCore.QDateTime):
        if isinstance(val, QtCore.QDateTime):
            self._begin_ = qtutils.datetimeFromQt(val)

        if not isinstance(self._data_, ephys_pathways.RecordingEpisode):
            self._make_value_()
        else:
            self._data_.begin = self._begin_

    @Slot(QtCore.QDateTime)
    def _slot_endDateTimeChanged(self, val: QtCore.QDateTime):
        if isinstance(val, QtCore.QDateTime):
            self._end_ = qtutils.datetimeFromQt(val)

        if not isinstance(self._data_, ephys_pathways.RecordingEpisode):
            self._make_value_()
        else:
            self._data_.end = self._end_

    @Slot(str)
    def _slot_nameChanged(self, val:str):
        if not isinstance(val, str) or len(val.strip()) == 0:
            val = "Episode"
        self._name_ = val
        if not isinstance(self._data_, ephys_pathways.RecordingEpisode):
            self._make_value_()
        else:
            self._data_.name = self._name_

        self.sig_valueChanged.emit(self.value())

    @Slot(int)
    def _slot_firstFrameChanged(self, val: int):
        self._beginFrame_ = val
        if not isinstance(self._data_, ephys_pathways.RecordingEpisode):
            self._make_value_()
        else:
            self._data_.beginFrame = self._beginFrame_

        self.sig_valueChanged.emit(self.value())

    @Slot(int)
    def _slot_lastFrameChanged(self, val: int):
        self._endFrame_ = val
        if not isinstance(self._data_, ephys_pathways.RecordingEpisode):
            self._make_value_()
        else:
            self._data_.endFrame = self._endFrame_

        self.sig_valueChanged.emit(self.value())

    @Slot(str)
    @Slot(int)
    def _slot_episodeTypeChanged(self, val: int | str):
        if isinstance(val, int) and val >=0 and val < len(self._recordingEpisodeNames_):
            val = self._recordingEpisodeNames_[val]

        if isinstance(val, str):
            if val in self._recordingEpisodeNames_:
                self._episodeType_ = ephys_pathways.RecordingEpisodeType[val]
            else:
                return
        else:
            return

        if not isinstance(self._data_, ephys_pathways.RecordingEpisode):
            self._make_value_()
        else:
            self._data_.type = self._episodeType_

        self.sig_valueChanged.emit(self.value())

    @Slot()
    def _slot_new(self):
        self._make_value_()

    def _make_value_(self):
        self._data_ = ephys_pathways.RecordingEpisode(blocks = self._blocks_,
                                                protocol = self._protocol_,
                                                name=self._name_,
                                                episodeType = self._episodeType_,
                                                stimulusLayout = self._stimulusLayout_,
                                                )
        self.createObjectPushButton.setEnabled(self._data_ is None)

    @Slot()
    def _slot_importTrials(self):
        self._importTrials()

    @Slot()
    def _slot_loadTrials(self):
        self._loadTrials()

    def _importTrials(self):
        ret = list()
        if isinstance(self._name_, str) and len(self._name_.strip()):
            ret = interact.selectWSData(f"{self._name_}_*",
                                        title = f"Select Trial Blocks for {
                                            self._name_
                                            }",
                                        single=False,
                                        var_type = neo.Block,
                                        retrieve_all = True,
                                        ) # noqa
        else:
            ret = interact.selectWSData(title = "Select Trial Blocks",
                                        single=False,
                                        var_type = neo.Block,
                                        retrieve_all = True,
                                        ) # noqa
        self.trials = ret

    def _loadTrials(self):
        from gui.workspacegui import FileIOGui
        if isinstance(self._name_, str) and len(self._name_.strip()):
            fileNameFilter = f"{self._name_}*.abf;{self._name_}*.pkl"
        else:
            fileNameFilter = "*.abf;*.pkl"
        files = FileIOGui.chooseFile_static(caption="Open trials",
                                            fileFilter = fileNameFilter,
                                            single=False)

        ret = list()
        try:
            if len(files):
                for f in files:
                    obj = pio.loadFile(f)
                    if isinstance(obj, neo.Block):
                        ret.append(obj)
        except: # noqa
            traceback.print_exc()

        self.trials = ret

    @property
    def trials(self) -> list:
        return self._blocks_

    @trials.setter
    def trials(self, val: list[neo.Block] | None):
        if (val is not None and not isinstance(val, typing.Sequence) and
            (len(val) > 0 and not all(isinstance(v, neo.Block) for v in val))):
            raise TypeError(f"Expecting a sequence of neo.Block trials or None; instead got a {type(val).__name__}")

        if val is None or (isinstance(val, typing.Sequence) and len(val) == 0):
            self._blocks_ = list()

        else:
            ret = list(sorted(val, key = lambda x: x.rec_datetime))

            if self.protocol is None:
                self.protocol = ephys.getProtocol(ret[0])
                if isinstance(self.protocol , ephys.ElectrophysiologyProtocol):
                    if not all(ephys.getProtocol(x) == self.protocol for x in ret[1:]):
                        scipywarn("All trials in an episode must have been recorded with the same protocol")

            else:
                protocol = ephys.getProtocol(ret[0])
                # allow chaning the protocol even when it was previously set
                if isinstance(self.protocol , ephys.ElectrophysiologyProtocol):
                    if not all(ephys.getProtocol(x) == self.protocol for x in ret[1:]):
                        scipywarn("All trials in an episode must have been recorded with the same protocol")
                    else:
                        self.protocol = protocol

            self._begin_ = ret[0].rec_datetime
            self._beginFrame_ = 0
            self._end_ = ret[-1].rec_datetime
            self._endFrame_ = len(ret)-1

        self.trialsInfoLabel.setText(f"{len(self._blocks_)} Trials")

    @property
    def protocol(self) -> ephys.ElectrophysiologyProtocol | None:
        return self._protocol_

    @protocol.setter
    def protocol(self, val: typing.Optional[ephys.ElectrophysiologyProtocol] = None):
        if not isinstance(val, ephys.ElectrophysiologyProtocol) and val is not None:
            raise TypeError(f"Expecting an ElectrophysiologyProtocol or None; instead got a {type(val).__name__}")

        self._protocol_ = val

        if not isinstance(self._data_, ephys_pathways.RecordingEpisode):
            self._make_value_()
        else:
            self._data_.protocol = self._protocol_

        sigBlock = QtCore.QSignalBlocker(self.protocolNameLabel)
        if isinstance(self._protocol_, ephys.ElectrophysiologyProtocol):
            self.protocolNameLabel.setText(self._protocol_.name)
        else:
            self.protocolNameLabel.setText("")

    @property
    def begin(self) -> datetime.datetime:
        return self._begin_

    @begin.setter
    def begin(self, val: datetime.datetime | None = None):
        if not isinstance(val, datetime.datetime) and val is not None:
            raise TypeError(f"Expecting a datetime object or None; instead, got a {type(val).__name__}")

        if val is None:
            val = datetime.datetime.now()

        self._begin_ = val

        if not isinstance(self._data_, ephys_pathways.RecordingEpisode):
            self._make_value_()
        else:
            self._data_.begin = self._begin_

        sigBlock = QtCore.QSignalBlocker(self.episodeBeginDateTimeEdit)
        self.episodeBeginDateTimeEdit.setDateTime(qtutils.datetime2Qt(self._begin_))

    @property
    def end(self) -> datetime.datetime:
        return self._end_

    @end.setter
    def end(self, val: datetime.datetime | None):
        if not isinstance(val, datetime.datetime) and val is not None:
            raise TypeError(f"Expecting a datetime object or None; instead, got a {type(val).__name__}")

        if val is None:
            val = datetime.datetime.now()

        self._end_ = val

        if not isinstance(self._data_, ephys_pathways.RecordingEpisode):
            self._make_value_()
        else:
            self._data_.end = self._end_

        sigBlock = QtCore.QSignalBlocker(self.episodeEndDateTimeEdit)
        self.episodeEndDateTimeEdit.setDateTime(qtutils.datetime2Qt(self._begin_))

    @property
    def firstFrame(self) -> int:
        return self._beginFrame_

    @firstFrame.setter
    def firstFrame(self, val: int):
        if not isinstance(val, int):
            raise TypeError(f"Expecting an int,; instead got a {type(val).__name__}")
        if val < 0:
            raise ValueError(f"Expecting a positive value; got {val} instead")

        self._beginFrame_ = val
        if not isinstance(self._data_, ephys_pathways.RecordingEpisode):
            self._make_value_()
        else:
            self._data_.beginFrame = self._beginFrame_

        sigBlock = QtCore.QSignalBlocker(self.firstFrameSpinBox)
        self.firstFrameSpinBox.setValue(self._beginFrame_)

    @property
    def lastFrame(self) -> int:
        return self._endFrame_

    @lastFrame.setter
    def lastFrame(self, val: int):
        if not isinstance(val, int):
            raise TypeError(f"Expecting an int,; instead got a {type(val).__name__}")
        if val < 0:
            raise ValueError(f"Expecting a positive value; got {val} instead")

        self._endFrame_ = val
        if not isinstance(self._data_, ephys_pathways.RecordingEpisode):
            self._make_value_()
        else:
            self._data_.endFrame = self._endFrame_

        sigBlock = QtCore.QSignalBlocker(self.lastFrameSpinBox)
        self.lastFrameSpinBox.setValue(self._endFrame_)


    # @Slot()
    # def _slot_editStimulus(self):
    #     from gui.delegates import ExternalEditorDelegate
    #     # print(f"{self.__class__.__name__}[{self.objectName()}]._slot_editStimulus: {self._syn_}")
    #     stimEditor = ExternalEditorDelegate(self._syn_, self)
    #     stimEditor.setObjectName("stimEditor")
    #     stimEditor.sig_valueChanged.connect(self._slot_stimulusChanged)
    #     stimEditor.slot_Launch()

    # @Slot()
    # def _slot_editAuxIn(self):
    #     from gui.delegates import ExternalEditorDelegate
    #     editor = ExternalEditorDelegate(self._auxin_, self)
    #     editor.setObjectName("auxInEditor")
    #     editor.sig_valueChanged.connect(self._slot_stimulusChanged)
    #     editor.slot_Launch()
    #
    # @Slot()
    # def _slot_editAuxOut(self):
    #     from gui.delegates import ExternalEditorDelegate
    #     editor = ExternalEditorDelegate(self._auxou_, self)
    #     editor.setObjectName("auxOutEditor")
    #     editor.sig_valueChanged.connect(self._slot_stimulusChanged)
    #     editor.slot_Launch()
    #
    # @Slot(object)
    # def _slot_stimulusChanged(self, val):
    #     # print(f"{self.__class__.__name__}[{self.objectName()}]._slot_stimulusChanged({val})")
    #     if isinstance(val, ephys_pathways.SynapticStimulusChannel):
    #         self._syn_ = val
    #         self._make_value_()
    #         self.sig_valueChanged.emit(self._data_)

    # @Slot(object)
    # def slot_valueChanged(self, val):
    #     self._data_ = val

    def setValue(self, val: typing.Optional[ephys_pathways.SynapticPathway] = None):
        print(f"{self.__class__.__name__}.setValue({val}) <{type(val).__name__}>")
        if isinstance(val, ephys_pathways.SynapticPathway):
            self._data_ = val
            self._name_ = self._data_.name
            self._adc_ = self._data_.adc
            self._endFrame_ = self._data_.dac
            self._syn_ = self._data_.syn
            self._auxin_ = self._data_.auxin
            self._auxout_ = self._data_.auxout
            self._electrode_ = self._data_.electrodeMode
            self._pathways_ = self._data_.pathways

            sigBlock = list(map(
                                lambda w: QtCore.QSignalBlocker(w),
                                (
                                    self.nameLineEdit,
                                    self.episodeBeginDateTimeEdit,
                                    self.lastFrameSpinBox,
                                    self.electrodeModeComboBox,
                                    self.pathTypeComboBox,
                                    self.stimulusPushButton,
                                    self.auxOutPushButton,
                                 )
                                )
                            )

            self.nameLineEdit.setText(self._name_)
            self.episodeBeginDateTimeEdit.setValue(self._adc_)
            self.lastFrameSpinBox.setValue(self._endFrame_)


            currentElectrodeModeNdx = self._recordingEpisodeNames_.index(self._electrode_.name)
            currentPathwayTypeNdx = self._pathwayTypeNames_.index(self._pathType_.name)

            self.electrodeModeComboBox.setCurrentIndex(currentElectrodeModeNdx)

    def value(self) -> ephys_pathways.RecordingEpisode:
        return self._data_

