# -*- coding: utf-8 -*-
# $Id: recordingepisodewidget.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""

# import sys
import os
import typing
# import types
# import warnings
# import math
# import cmath
# import numbers
import datetime
# import traceback
# import numpy as np
# import quantities as pq
import neo
# from tribool import Tribool


import qtpy # noqa
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, ) # noqa
from qtpy.QtCore import (Signal, Slot, Property,) # noqa
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
except: # noqa
    __has_qtdbus__ = False

from ephys import ephys
from ephys import ephys_pathways
from ephys import ephys_protocol
from core import datatypes # noqa
from core import desktoputils
from core import strutils
from core import qtutils
from core import scipyendataclasses as sdc
from core.prog import scipywarn # noqa
from iolib import pictio as pio # noqa
from gui import (guiutils, interact) # noqa

from gui.widgets.dataclasswidgets.dataclasswidget import DataClassWidget

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

try:
    from gui.widgets.recordingepisodewidget_ui import Ui_RecordingEpisodeWidget

except:
    Ui_RecordingEpisodeWidget, QWidget = loadUiType(
        os.path.join(__module_path__, "recordingepisodewidget.ui")
        )

T = ephys_pathways.RecordingEpisode

class RecordingEpisodeWidget(Ui_RecordingEpisodeWidget, DataClassWidget):
    sig_trialsChanged = Signal(name="sig_trialsChanged")
    sig_protocolChanged = Signal(name="sig_protocolChanged")
    sig_newObjectCreated = Signal(object, name="sig_newObjectCreated")

    _objectType_ = ephys_pathways.RecordingEpisode
    _objectTypes_ = (ephys_pathways.RecordingEpisode, )

    recordingEpisodeTypeNames = list(ephys_pathways.RecordingEpisodeType.names())

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None,
                 obj: typing.Optional[T] = None,
                 **kwargs):
        # print(f"{self.__class__.__name__}.__init__(parent={parent}, obj={obj})")
        super(Ui_RecordingEpisodeWidget, self).__init__()
        if isinstance(parent, (ephys_pathways.RecordingEpisode,
                               neo.Block, typing.Sequence)):
            obj_ = parent
            if isinstance(obj, QtWidgets.QWidget):
                parent = obj
            else:
                parent = None

            obj = obj_

        if not isinstance(obj, self._objectTypes_):
            self._name_ = "Episode"
            self._episodeType_ = ephys_pathways.RecordingEpisodeType.Tracking
            self._begin_ = datetime.datetime.now()
            self._end_ = datetime.datetime.now()
            self._beginFrame_ = 0
            self._nFrames_ = 0
            self._protocol_ = None
            self._procedure_ = sdc.Procedure()
            self._description_ = ""
            self._make_value_()
        else:
            self._data_ = obj
            self._name_ = self._data_.name
            self._episodeType_ = self._data_.type
            self._begin_ = self._data_.begin
            self._end_ = self._data_.end
            self._beginFrame_ = self._data_.beginFrame
            self._nFrames_ = self._data_.nFrames
            self._protocol_ = self._data_.protocol
            self._procedure_ = self._data_.procedure
            self._description_ = self._data_.description

        DataClassWidget.__init__(self, parent=parent, **kwargs)
        self._configureUI_()


    def _configureUI_(self):
        self.setupUi(self)
        super()._configureUI_() # DataClassWidget!

        self.protocolViewer = None
        self.procedureEditor = None

        self.nameDescriptionWidget.nameLineEdit.setToolTip("Name of the recording source")
        self.nameDescriptionWidget.nameLineEdit.setWhatsThis("Name of the recording source")
        self.nameDescriptionWidget.nameLineEdit.setStatusTip("Name of the recording source")
        self.nameDescriptionWidget.symbol = "recordingEpisode"

        if isinstance(self._protocol_, ephys_protocol.ElectrophysiologyProtocol):
            self.protocolNameLabel.setText(self._protocol_.name)
        else:
            self.protocolNameLabel.setText("")

        self.previewProtocolToolButton.clicked.connect(self.slot_viewProtocolDetails)

        for text in self.recordingEpisodeTypeNames:
            self.episodeTypeComboBox.addItem(text)

        currentEpisodeTypeNdx = self.recordingEpisodeTypeNames.index(self._episodeType_.name)
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
            self.episodeEndDateTimeEdit.setDateTime(qtutils.datetime2Qt(self._end_))

        self.episodeEndDateTimeEdit.dateTimeChanged.connect(self._slot_endDateTimeChanged)

        self.firstFrameSpinBox.setToolTip("Index of the first frame (sweep) in data")
        self.firstFrameSpinBox.setWhatsThis("Index of the first frame (sweep) in data")
        self.firstFrameSpinBox.setStatusTip("Index of the first frame (sweep) in data")
        self.firstFrameSpinBox.setMinimum(0)

        if isinstance(self._beginFrame_, int) and self._beginFrame_ >= 0:
            self.firstFrameSpinBox.setValue(self._beginFrame_)

        self.firstFrameSpinBox.valueChanged.connect(self._slot_firstFrameChanged)

        self.nFramesSpinBox.setMinimum(0)

        if isinstance(self._nFrames_, int) and self._nFrames_ >= 0:
            self.nFramesSpinBox.setValue(self._nFrames_)

        self.nFramesSpinBox.valueChanged.connect(self._slot_nFramesChanged)

        self.toggleProcedureEditor.toggled.connect(self._slot_toggleProcedureEditor)

        self.createObjectPushButton.setText("")
        self.createObjectPushButton.setIcon(guiutils.getIcon("list-add"))
        self.createObjectPushButton.setToolTip("Create Recording Episode")
        self.createObjectPushButton.setWhatsThis("Create Recording Episode")
        self.createObjectPushButton.setStatusTip("Create Recording Episode")

        self.createObjectPushButton.clicked.connect(self._slot_new)

    @Slot(bool)
    def _slot_toggleProcedureEditor(self, val: bool):
        if val is True:
            self._slot_showProcedureWidget()
        else:
            if isinstance(self.procedureEditor, DataClassWidget) and qtutils.isQObjectAlive(self.procedureEditor):
                self.procedureEditor.collapse(False)

    def _makeProcedureEditor(self, data):
        from gui.widgets.dataclasswidgets.procedurewidget import SimpleProcedureWidget
        anchoringWidget = self.provideAnchoringWidget()
        self.procedureEditor = self._setupCollapsibleChild_(
            SimpleProcedureWidget,
            "procedureEditor",
            self._slot_procedureChanged,
            self.toggleProcedureEditor,
            anchoringWidget,
            not desktoputils.is_wayland(),
            data,
            objSymbol="procedure"
            )

    @Slot()
    def _slot_showProcedureWidget(self):
        from gui.widgets.dataclasswidgets.procedurewidget import SimpleProcedureWidget
        if isinstance(self.procedureEditor, QtWidgets.QWidget) and qtutils.isQObjectAlive(self.procedureEditor):
            if not isinstance(self.procedureEditor, SimpleProcedureWidget):
                self._removeAnchoringCollapsibleWidget_(self.procedureEditor)
                self._makeProcedureEditor(self._data_.procedure)

            else:
                self.procedureEditor.setValue(self._data_.procedure,
                                              objSymbol="procedure")

            # print(f"{self.__class__.__name__}.)_slot_showProcedureWidget self._data_.procedure -> {self._data_.procedure}")

        else:
            self._makeProcedureEditor(self._data_.procedure)

        if isinstance(self._data_.procedure.name, str) and len(self._data_.procedure.name.strip()):
            self.procedureEditor.setWindowTitle(f"Procedure: {self._data_.procedure.name} ({self._data_.procedure.procedureType.name})")
        else:
            self.procedureEditor.setWindowTitle(f"Procedure: {self._data_.procedure.procedureType.name}")

        self.procedureEditor.show()

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

    @Slot(int)
    def _slot_firstFrameChanged(self, val: int):
        self._beginFrame_ = val
        if not isinstance(self._data_, ephys_pathways.RecordingEpisode):
            self._make_value_()
        else:
            self._data_.beginFrame = self._beginFrame_

        self.sig_valueChanged.emit(self.value())

    @Slot(int)
    def _slot_nFramesChanged(self, val: int):
        self._nFrames_ = val
        if not isinstance(self._data_, ephys_pathways.RecordingEpisode):
            self._make_value_()
        else:
            self._data_.nFrames = self._nFrames_

        self.sig_valueChanged.emit(self.value())

    @Slot()
    def slot_viewProtocolDetails(self):
        from gui import datatreeviewer
        if self._protocol_ is None:
            return

        doc_title = self._protocol_.name
        if not isinstance(self.protocolViewer, datatreeviewer.DataTreeViewer):
            topWindow = self.getHighestAncestor()
            if topWindow is self:
                appWindow = None
            else:
                appWindow = topWindow

            self.protocolViewer = datatreeviewer.DataTreeViewer(
                parent=self,
                doc_title=doc_title,
                appWindow = appWindow,
                )

            self.protocolViewer.autoRaise = False

            self.protocolViewer.view(self._protocol_, doc_title = doc_title, name=doc_title)
            self.protocolViewer.readOnly = True
            self.protocolViewer.showIntrospection = True
        else:
            self.protocolViewer.view(self._protocol_, doc_title = doc_title, name=doc_title)
            self.protocolViewer.readOnly = True
            self.protocolViewer.showIntrospection = True
            self.protocolViewer.docTitle = doc_title
            self.protocolViewer.slot_refreshDataDisplay()

        self.protocolViewer.show()

    @Slot(str)
    @Slot(int)
    def _slot_episodeTypeChanged(self, val: int | str):
        if isinstance(val, int) and val >=0 and val < len(self.recordingEpisodeTypeNames):
            val = self.recordingEpisodeTypeNames[val]

        if isinstance(val, str):
            if val in self.recordingEpisodeTypeNames:
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

    @Slot(object)
    def _slot_procedureChanged(self, value: sdc.Procedure):
        if not isinstance(value, sdc.Procedure):
            value = sdc.Procedure()
        self._procedure_ = value
        self._make_value_()
        self.sig_valueChanged.emit(self.value())

    @Slot()
    def _slot_new(self):
        self._make_value_()
        self.sig_newObjectCreated.emit(self._data_)

    def _make_value_(self):
        self._data_ = ephys_pathways.RecordingEpisode(
            name=self._name_,
            protocol = self._protocol_,
            episodeType = self._episodeType_,
            description = self._description_,
            procedure = self._procedure_
            )

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

        with qtutils.SignalBlocker(self.protocolNameLabel):
            if isinstance(self._protocol_, ephys.ElectrophysiologyProtocol):
                self.protocolNameLabel.setText(self._protocol_.name)
            else:
                self.protocolNameLabel.setText("")

        self.sig_protocolChanged.emit()

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

        with qtutils.SignalBlocker(self.episodeBeginDateTimeEdit):
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

        with qtutils.SignalBlocker(self.episodeEndDateTimeEdit):
            self.episodeEndDateTimeEdit.setDateTime(qtutils.datetime2Qt(self._end_))

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

        with qtutils.SignalBlocker(self.firstFrameSpinBox):
            self.firstFrameSpinBox.setValue(self._beginFrame_)

    @property
    def lastFrame(self) -> int:
        return self._nFrames_

    @lastFrame.setter
    def lastFrame(self, val: int):
        if not isinstance(val, int):
            raise TypeError(f"Expecting an int,; instead got a {type(val).__name__}")
        if val < 0:
            raise ValueError(f"Expecting a positive value; got {val} instead")

        self._nFrames_ = val

        if not isinstance(self._data_, ephys_pathways.RecordingEpisode):
            self._make_value_()
        else:
            self._data_.nFrames = self._nFrames_

        with qtutils.SignalBlocker(self.nFramesSpinBox):
            self.nFramesSpinBox.setValue(self._nFrames_)

    def setValue(self, val: typing.Optional[ephys_pathways.RecordingEpisode] = None):
        from gui import datatreeviewer
        # print(f"{self.__class__.__name__}.setValue({val}) <{type(val).__name__}>")
        if isinstance(val, ephys_pathways.RecordingEpisode):
            self._data_ = val
            self._name_ = self._data_.name
            self._beginFrame_ = self._data_.beginFrame
            self._nFrames_ = self._data_.nFrames
            self._begin_ = self._data_.begin
            self._end_ = self._data_.end
            self._episodeType_ = self._data_.type
            if isinstance(self._data_.stimulusLayout, ephys_pathways.PathwaysStimulationLayout):
                if (isinstance(self.stimulusLayoutViewer, datatreeviewer.DataTreeViewer)
                    and self.stimulusLayoutViewer.isVisible()
                    and qtutils.isQObjectAlive(self.stimulusLayoutViewer)
                    ):
                    doc_title = self._data_.stimulusLayout.source.name
                    self.stimulusLayoutViewer.view(self._data_.stimulusLayout,
                                                   doc_title = doc_title,
                                                   name=doc_title)

                    self.stimulusLayoutViewer.docTitle = doc_title
                    self.stimulusLayoutViewer.slot_refreshDataDisplay()
            self._stimulusLayout_ = self._data_.stimulusLayout

            if isinstance(self._data_.protocol, ephys_protocol.ElectrophysiologyProtocol):
                if (isinstance(self.protocolViewer, datatreeviewer.DataTreeViewer)
                    and self.protocolViewer.isvisible()
                    and qtutils.isQObjectAlive(self.protocolViewer)
                    ):
                    doc_title = self._data_._protocol_.name
                    self.protocolViewer.view(self._protocol_, doc_title = doc_title, name=doc_title)
                    self.protocolViewer.docTitle = doc_title
                    self.protocolViewer.slot_refreshDataDisplay()

                self.protocolNameLabel.setText(self._data_._protocol_.name)
            else:
                self.protocolNameLabel.setText("")

            self._protocol_ = self._data_.protocol

        elif val is None:
            self._name_ = "Episode"
            self._blocks_ = list()
            self._episodeType_ = ephys_pathways.RecordingEpisodeType.Tracking
            self._begin_ = datetime.datetime.now()
            self._end_ = datetime.datetime.now()
            self._beginFrame_ = 0
            self._nFrames_ = 0
            self._protocol_ = None
            self._stimulusLayout_ = None
            if (isinstance(self.stimulusLayoutViewer, datatreeviewer.DataTreeViewer)
                and qtutils.isQObjectAlive(self.stimulusLayoutViewer)
                ):
                self.stimulusLayoutViewer.close()
                self.stimulusLayoutViewer.deleteLater()
                self.stimulusLayoutViewer = None

            if (isinstance(self.protocolViewer, datatreeviewer.DataTreeViewer)
                and qtutils.isQObjectAlive(self.protocolViewer)
                ):
                self.protocolViewer.close()
                self.protocolViewer.deleteLater()
                self.protocolViewer = None

            self.protocolNameLabel.setText("")

        else:
            raise TypeError(f"Expecting a RecordingEpisode or None; instead got a {type(val).__name__}")

        with qtutils.SignalBlocker(
                                    (
                                        # self.nameLineEdit,
                                        self.episodeBeginDateTimeEdit,
                                        self.episodeEndDateTimeEdit,
                                        self.firstFrameSpinBox,
                                        self.nFramesSpinBox,
                                        self.episodeTypeComboBox,
                                    )
                                ):
            # self.nameLineEdit.setText(self._name_)
            self.episodeBeginDateTimeEdit.setDateTime(qtutils.datetime2Qt(self._begin_))
            self.episodeEndDateTimeEdit.setDateTime(qtutils.datetime2Qt(self._end_))
            self.firstFrameSpinBox.setValue(self._beginFrame_)
            self.nFramesSpinBox.setValue(self._nFrames_)
            self.protocolNameLabel.setText(self._protocol_.name if isinstance(self._protocol_, ephys.ElectrophysiologyProtocol) else "")
            self.trialsInfoLabel.setText(f"{len(self._blocks_)} {strutils.pluralize('Trial', len(self._blocks_))}")


            currentEpisodeTypeNdx = self.recordingEpisodeTypeNames.index(self._episodeType_.name)

            self.episodeTypeComboBox.setCurrentIndex(currentEpisodeTypeNdx)

    def value(self) -> ephys_pathways.RecordingEpisode:
        return self._data_

