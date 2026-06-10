# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later


import os, typing
import numbers
import itertools
import traceback
from collections import deque

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


import numpy as np
import quantities as pq
from neo import (Block, Segment,)

from core.scipyen_quantities import (arbitrary_unit, checkTimeUnits, unitsConvertible,
                            unitQuantityFromNameOrSymbol,quantity2str,)

from core.datatypes import UnitTypes

from core.traitcontainers import DataBag
from core.triggerevent import (TriggerEvent, TriggerEventType,)

from core.triggerprotocols import (TriggerProtocol,
                                   auto_detect_trigger_protocols,
                                   auto_define_trigger_events,
                                   detect_trigger_events,
                                   embed_trigger_protocol,
                                   embed_trigger_event,
                                   get_trigger_events,
                                   parse_trigger_protocols,
                                   remove_trigger_protocol,
                                   parse_trigger_protocols,)

from core.neoutils import (concatenate_blocks, get_events, remove_events,
                           check_ephys_data_collection, check_ephys_data)

from core.prog import scipywarn

from ephys.ephys import (ElectrophysiologyProtocol, getProtocol)

from core.strutils import numbers2str

from gui import quickdialog as qd
from gui.signalviewer import SignalViewer
from gui.delegates import PythonItemDelegate
from gui.itemmodels.digtriggerstablemodel import DIGTriggersTableModel

# TODO 2026-06-09 18:18:06 consider TabularDataModel FIXME

__module_path__ = os.path.abspath(os.path.dirname(__file__))

if os.environ["QT_API"] in ("pyqt5", "pyside2"):
    Ui_TriggerDetectWidget, QWidget = loadUiType(os.path.join(__module_path__, "widgets", "triggerdetect.ui"), from_imports=True, import_from="gui")
    Ui_ImportDIGTriggerWidget, _ = loadUiType(os.path.join(__module_path__, "widgets", "importDIGtrigger.ui"), from_imports=True, import_from="gui")
else:
    Ui_TriggerDetectWidget, QWidget = loadUiType(os.path.join(__module_path__, "widgets", "triggerdetect.ui"))
    Ui_ImportDIGTriggerWidget, _ = loadUiType(os.path.join(__module_path__, "widgets", "importDIGtrigger.ui"))


# class _DIGTriggersTable_(QtWidgets.QTableView):
class DIGTriggersWidget(QtWidgets.QWidget, Ui_ImportDIGTriggerWidget):
    r"""Helper class for curating digital trigger events in a recording protocol
 """
    def __init__(self, data:typing.Optional[list] = None, parent:typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)
        # {dig_index: [(event, ), (sweep indices)]}
        self._dataModel_ = DIGTriggersTableModel(parent=self)
        self._dataModel_.setObjectName("_dataModel_")
        self._configureUI_()

        self.setData(data)

    def _configureUI_(self):
        self.setupUi(self)
        self.tableView.setModel(self._dataModel_)
        self.tableView.horizontalHeaderVisible = True
        self.tableView.verticalHeaderVisible = True

        self.tableView.setSortingEnabled(False)
        self.tableView.horizontalHeader().setSectionsMovable(False)
        self.tableView.horizontalHeader().setResizeContentsPrecision(0)
        self.tableView.setAlternatingRowColors(True)

        self.tableView.verticalHeader().setSectionsMovable(False)
        self.tableView.verticalHeader().setResizeContentsPrecision(0)

        self._defaultEditTriggers_ = self.tableView.editTriggers()

        colChoices = {1: {"choices": list(TriggerEventType.names()), "editable": False}}
        self.tableView.setItemDelegate(PythonItemDelegate(parent=self,
                                                columnChoices = colChoices))

    def setData(self, value:typing.Sequence):
        self._data_ = list(value) if isinstance(value, typing.Sequence) else list()
        self._dataModel_.populateModel(self._data_)
        for col in (1,5):
            for row in range(self._dataModel_.rowCount()):
                self.tableView.openPersistentEditor(self._dataModel_.index(row, col))
        self.tableView.resizeColumnsToContents()

    def getRowNames(self, ndx:typing.Optional[typing.Union[int, typing.Sequence[int]]] = None,
                    quoted:bool=False, sep:str = "\t", asList:bool=False):
        if ndx is None:
            ndx = range(self.tableView.model().rowCount())

        elif isinstance(ndx, int):
            ndx = [ndx]

        elif isinstance(ndx, (list, tuple)):
            if len(ndx) == 0:
                ndx = range(self.tableView.model().rowCount())
            elif not all(isinstance(v, int) for v in ndx):
                raise TypeError(f"Invalid row indices specified. Expecting int, sequence of int or None; instead, got {ndx}")
        else:
            raise TypeError(f"Invalid row indices specified. Expecting int, sequence of int or None; instead, got {ndx}")

        values = [self.tableView.model().headerData(k, QtCore.Qt.Vertical).value() for k in ndx]
        # link = ", "
        if len(values) == 1:
            ret = f"'{values[0]}'" if quoted else values[0]

            if asList:
                ret = [ret]

        else:
            ret = [f"'{v}'" for v in values] if quoted else values
            if not asList:
                ret = sep.join(ret)

        return ret

    def getColumnNames(self, ndx:typing.Optional[typing.Union[int, typing.Sequence[int]]] = None,
                    quoted:bool=False, sep:str = ", ", asList:bool=False):
        if ndx is None:
            ndx = range(self.tableView.model().columnCount())

        elif isinstance(ndx, int):
            ndx = [ndx]

        elif isinstance(ndx, (list, tuple)):
            if len(ndx) == 0:
                ndx = range(self.tableView.model().columnCount())

            elif not all(isinstance(v, int) for v in ndx):
                raise TypeError(f"Invalid row indices specified. Expecting int, sequence of int or None; instead, got {ndx}")
        else:
            raise TypeError(f"Invalid row indices specified. Expecting int, sequence of int or None; instead, got {ndx}")

        values = [self.tableView.model().headerData(k, QtCore.Qt.Horizontal).value() for k in ndx]
        # link = ", "
        if len(values) == 1:
            ret = f"'{values[0]}'" if quoted else values[0]
            if asList:
                ret = [ret]
        else:
            ret = [f"'{v}'" for v in values] if quoted else values
            if not asList:
                ret = sep.join(ret)

        return ret

class TriggerDetectWidget(QWidget, Ui_TriggerDetectWidget):
    r"""
    """

    sig_dataChanged = Signal()

    def __init__(self, ephys_start:typing.Union[numbers.Real, pq.Quantity]=0,
                 ephys_end:typing.Union[numbers.Real, pq.Quantity]=1, n_channels:int=0,
                 presyn:typing.Optional[typing.Union[dict, tuple, list]]=None,
                 postsyn:typing.Optional[typing.Union[dict, tuple, list]]=None,
                 photo:typing.Optional[typing.Union[dict, tuple, list]]=None,
                 imaging:typing.Optional[typing.Union[dict, tuple, list]]=None,
                 clear:bool=False, reltimes:bool=True,
                 parent:typing.Optional[QtWidgets.QWidget]=None):
        r"""
        Named parameters:
        -----------------
        parent: None (default) or a QWidgets.QMainWindow object
            When None, parent is set to be Scipyen's main application window

        presyn, postsyn, photo, imaging: None (default) or dict
            Options for presynaptic, postsynaptic, photostimulation, and
            imaging frame trigger events, respectively.

            When dict, they must contain the following fields (case-sensitive):
            "Channel": int
            "Name": str
            "DetectionBegin" : float or python suantity with time units
            "DetectionEnd": float or python suantity with time units

        ephys_start, ephys_end: None (default) or pq.Quantity in times units
            (e.g. pq.s)

        """
        super().__init__(parent)

        self._sig_start_  = ephys_start
        self._sig_stop_   = ephys_end
        self._n_channels_ = n_channels
        self._reltimes_   = reltimes


        self._configureUI_()

        self.setValues("pre", presyn)

        self.setValues("post", postsyn)

        self.setValues("photo", photo)

        self.setValues("imaging", imaging)

        #self.clearExisting = clear is True

    def _configureUI_(self):
        self.setupUi(self)
        self.presynNameLineEdit.redoAvailable=True
        self.presynNameLineEdit.undoAvailable=True

        self.postsynNameLineEdit.redoAvailable=True
        self.postsynNameLineEdit.undoAvailable=True

        self.photoNameLineEdit.redoAvailable=True
        self.photoNameLineEdit.undoAvailable=True

        self.imagingNameLineEdit.redoAvailable=True
        self.imagingNameLineEdit.undoAvailable=True

        self.reltimesCheckBox.setChecked(self._reltimes_)

        startRangeWidgets = [self.presynStartDoubleSpinBox,
                             self.postsynStartDoubleSpinBox,
                             self.photoStartDoubleSpinBox,
                             self.imagingStartDoubleSpinBox,
                             ]
        stopRangeWidgets = [self.presynStopDoubleSpinBox,
                            self.postsynStopDoubleSpinBox,
                            self.photoStopDoubleSpinBox,
                            self.imagingStopDoubleSpinBox]

        widgets = startRangeWidgets + stopRangeWidgets

        for w in widgets:
            w.units = pq.s
            w.rescaleOnUnitChange = True
            w.restrictToCurrentUnitFamily = True
            w.setDecimals(3)
            w.setSingleStep(0.001)

        self._update_channel_ranges_()
        self._update_time_ranges_()

    def setValues(self, target, src=None):
        r"""Populates the fields for the trigger event type corresponding to target
        """
        if target in ("pre", "presyn", "presynaptic"):
            groupBox        = self.presynGroupBox
            channelWidget   = self.presynChannelSpinBox
            nameWidget      = self.presynNameLineEdit
            startWidget     = self.presynStartDoubleSpinBox
            stopWidget      = self.presynStopDoubleSpinBox

        elif target in ("post", "postsyn", "postsynaptic"):
            groupBox        = self.postsynGroupBox
            channelWidget   = self.postsynChannelSpinBox
            nameWidget      = self.postsynNameLineEdit
            startWidget     = self.postsynStartDoubleSpinBox
            stopWidget      = self.postsynStopDoubleSpinBox

        elif target in ("photo", "photostim", "pstim", "phstim",
                        "photostimulation", "uncage", "uncaging",
                        "photoconv", "photoconversion"):
            groupBox        = self.photoGroupBox
            nameWidget      = self.photoNameLineEdit
            channelWidget   = self.photoChannelSpinBox
            startWidget     = self.photoStartDoubleSpinBox
            stopWidget      = self.photoStopDoubleSpinBox

        elif target in ("imaging", "frame", "imaging_frame", "imgframe"):
            groupBox        = self.imagingGroupBox
            channelWidget   = self.imagingChannelSpinBox
            nameWidget      = self.imagingNameLineEdit
            startWidget     = self.imagingStartDoubleSpinBox
            stopWidget      = self.imagingStopDoubleSpinBox

        elif target == "clear":
            if src is None: # toggle
                self.clearExisting = not self.clearExisting

            elif isinstance(src, bool):
                self.clearExisting = src
            else:
                raise TypeError("When target is 'clear', src is expected to be None or a bool")

            self.clearExistingEventsCheckBox.setChecked(QtCore.Qt.Checked if self.clearExisting else QtCore.Qt.Unchecked)

        else:
            warnings.warn("Unknown options targeted")
            return

        if src is None:
            groupBox.setChecked(False)
            return

        signalBlockers = [QtCore.QSignalBlocker(w) for w in (channelWidget,
                                                             nameWidget,
                                                             startWidget,
                                                             stopWidget)]

        channel = 0
        name = target
        start = self._sig_start_
        stop = self._sig_stop_

        if isinstance(src, dict):
            channel = src.get("Channel", 0)
            name = src.get("Name", target)
            start = src.get("DetectionBegin", self._sig_start_)
            stop = src.get("DetectionEnd", self._sig_stop_)

        elif isinstance(src, (tuple, list)) and len(src) in (2,3):
            channel = src[0]
            name = src[1]
            if len(src) == 3 and isinstance(src[2], (tuple, list)) and len(src[2]) == 2:
                start = src[2][0]
                stop = src[2][1]

        else:
            raise TypeError("Unexpected argument for src: %s" % src)


        if isinstance(channel, int):
            if channel < 0:
                channel = 0

            elif isinstance(self._n_channels_, int) and channel >= self._n_channels_:
                channel = self._n_channels_ - 1

        else:
            channels = 0


        if not isinstance(name, str) or len(name.strip()) == 0:
            name = target

        channelWidget.setValue(channel)
        nameWidget.setText(name)
        startWidget.setValue(self._check_time_value_("start", start))
        stopWidget.setValue(self._check_time_value_("stop", stop))

        groupBox.setChecked(True)

    @property
    def nChannels(self):
        return self._n_channels_

    @nChannels.setter
    def nChannels(self, value):
        if isinstance(value, numbers.Real):
            if value < 0:
                self._n_channels_ = 0

            else:
                self._n_channels_ = int(value)

            self._update_channel_ranges_()

    @property
    def signalStart(self):
        return self._sig_start_

    @signalStart.setter
    def signalStart(self, value):
        value = self._check_time_value_("start", value)
        if isinstance(value, pq.Quantity):
            if checkTimeUnits(value):
                value = float(value.rescale(pq.s).magnitude.flatten()[0])

            else:
                raise TypeError("Unexpected units for signal start: %s" % value.units.dimensionality)

        elif isinstance(value, numbers.Real):
            value = float(value)

        elif value is None:
            value = 0.

        else:
            raise TypeError("Unexpected type for signal start: %s" % type(value).__name__)

        self._sig_start_ = value

        self._sig_start_, self._sig_stop_ = np.sort([self._sig_start_, self._sig_stop_])

        self._update_time_ranges_()

    @property
    def signalStop(self):
        return self._sig_stop_

    @signalStop.setter
    def signalStop(self, value):
        value = self._check_time_value_("stop", value)

        self._sig_stop_ = value

        self._sig_start_, self._sig_stop_ = np.sort([self._sig_start_, self._sig_stop_])

        self._update_time_ranges_()

    @property
    def hasPresynapticTrigger(self):
        return self.presynGroupBox.isChecked()

    @property
    def hasPostsynapticTrigger(self):
        return self.postsynGroupBox.isChecked()

    @property
    def hasPhotostimulationTrigger(self):
        return self.photoGroupBox.isChecked()

    @property
    def hasImagingFrameTrigger(self):
        return self.imagingGroupBox.isChecked()

    @property
    def relTimes(self) -> bool:
        return self._reltimes_

    @relTimes.setter
    def relTimes(self, val:bool):
        sigBlock = QtCore.QSignalBlocker(self.reltimesCheckBox)
        self._reltimes_ = val==True
        self.reltimesCheckBox.setChecked(self._reltimes_)

    @property
    def presyn(self) -> tuple:
        r"""Tuple: ( signal index, label, (t_start, t_stop) ) as required for
        triggerprotocols.auto_define_trigger_events
        """
        if self.presynGroupBox.isChecked():
            return (self.presynChannelSpinBox.value(),
                    self.presynNameLineEdit.text(),
                    self.presynHiLogicCheckBox.isChecked(),
                    (self.presynStartDoubleSpinBox.value(),# * pq.s,
                     self.presynStopDoubleSpinBox.value()),# * pq.s,),
                    )

        return ()

    @presyn.setter
    def presyn(self, value):
        self.setValues("presyn", value)

    @property
    def presynapticOptions(self):
        if self.presynGroupBox.isChecked():
            return DataBag({"Channel": self.presynChannelSpinBox.value(),
                            "Name": self.presynNameLineEdit.text(),
                            "Hi": self.presynHiLogicCheckBox.isChecked(),
                            "DetectionBegin": self.presynStartDoubleSpinBox.value(),# * pq.s,
                            "DetectionEnd": self.presynStopDoubleSpinBox.value(),# * pq.s,
                            },
        allow_none=True)

    @property
    def postsyn(self):
        if self.postsynGroupBox.isChecked():
            return (self.postsynChannelSpinBox.value(),
                    self.postsynNameLineEdit.text(),
                    self.postsynHiLogicCheckBox.isChecked(),
                    (self.postsynStartDoubleSpinBox.value(),# * pq.s,
                     self.postsynStopDoubleSpinBox.value()),# * pq.s,),
                    )

        return ()

    @postsyn.setter
    def postsyn(self, value):
        self.setValues("postsyn", value)

    @property
    def postsynapticOptions(self):
        if self.postsynGroupBox.isChecked():
            return DataBag({"Channel": self.postsynChannelSpinBox.value(),
                            "Name": self.postsynNameLineEdit.text(),
                            "Hi": self.postsynHiLogicCheckBox.isChecked(),
                            "DetectionBegin": self.postsynStartDoubleSpinBox.value(),# * pq.s,
                            "DetectionEnd": self.postsynStopDoubleSpinBox.value(),# * pq.s,
                            },
        allow_none=True)

    @property
    def photo(self):
        if self.photoGroupBox.isChecked():
            return (self.photoChannelSpinBox.value(),
                    self.photoNameLineEdit.text(),
                    self.photoStimHiLogicCheckBox.isChecked(),
                    (self.photoStartDoubleSpinBox.value(),# * pq.s,
                     self.photoStopDoubleSpinBox.value()), # * pq.s,),
                    )

        return ()

    @photo.setter
    def photo(self, value):
        self.setValues("photo", value)

    @property
    def photostimulationOptions(self):
        if self.photoGroupBox.isChecked():
            return DataBag({"Channel": self.photoChannelSpinBox.value(),
                            "Name": self.photoNameLineEdit.text(),
                            "Hi": self.photoStimHiLogicCheckBox.isChecked(),
                            "DetectionBegin": self.photoStartDoubleSpinBox.value(),# * pq.s,
                            "DetectionEnd": self.photoStopDoubleSpinBox.value(),# * pq.s,
                            },
        allow_none=True)

    @property
    def imaging(self):
        if self.imagingGroupBox.isChecked():
            return (self.imagingChannelSpinBox.value(),
                    self.imagingNameLineEdit.text(),
                    self.imagingHiLogicCheckBox.isChecked(),
                    (self.imagingStartDoubleSpinBox.value(),# * pq.s,
                     self.imagingStopDoubleSpinBox.value()),# * pq.s,),
                    )

        return ()

    @imaging.setter
    def imaging(self, value):
        self.setValues("imaging", value)

    @property
    def imagingFrameOptions(self):
        if self.imagingGroupBox.isChecked():
            return DataBag({"Channel": self.imagingChannelSpinBox.value(),
                            "Name": self.imagingNameLineEdit.text(),
                            "Hi": self.imagingHiLogicCheckBox.isChecked(),
                            "DetectionBegin": self.imagingStartDoubleSpinBox.value(),# * pq.s,
                            "DetectionEnd": self.imagingStopDoubleSpinBox.value(), # * pq.s,
                            },
        allow_none=True)

    @Slot(int)
    @Slot(float)
    @Slot(str)
    def slot_paramValueChangedGui(self, value=None):
        self.sig_dataChanged.emit()

    def _check_time_value_(self, what, value):
        if what not in ("start", "stop"):
            raise ValueError("First argument expected to be either 'start' or 'stop'; got %s instead" % what)

        if isinstance(value, pq.Quantity):
            if value.size == 1:
                if checkTimeUnits(value):
                    value = value.rescale(pq.s)

                else:
                    raise TypeError("Wrong units for %s %s: %s" % (target, what, value.units.dimensionality))
            else:
                raise TypeError("%s value for %s must be a singleton; got %s instead" % (what, target, value))

            value = float(value.magnitude)

        elif isinstance(value, np.ndarray):
            if value.size != 1:
                raise TypeError("%s value for %s must be a singleton; got %s instead" % (what, target, value))

            value = float(value)

        elif isinstance(value, numbers.Real):
            value = float(value)

        elif value is None:
            if what == "start":
                value = 0.

            else:
                value = 1.

        else:
            raise TypeError("Unexpected %s value: %s" % (what, value))

        return value

    @Slot(int)
    def _slot_reltimesCheckBoxStateChanged(self, val:int):
        self._reltimes_ = val != QtCore.Qt.CheckState.Unchecked

    def _update_time_ranges_(self):
        startRangeWidgets = [self.presynStartDoubleSpinBox,
                             self.postsynStartDoubleSpinBox,
                             self.photoStartDoubleSpinBox,
                             self.imagingStartDoubleSpinBox,
                             ]
        stopRangeWidgets = [self.presynStopDoubleSpinBox,
                            self.postsynStopDoubleSpinBox,
                            self.photoStopDoubleSpinBox,
                            self.imagingStopDoubleSpinBox]

        widgets = startRangeWidgets + stopRangeWidgets

        signalBlockers = [QtCore.QSignalBlocker(w) for w in widgets]

        for w in widgets:
            w.setMinimum(self._sig_start_)
            w.setMaximum(self._sig_stop_)
            if w in startRangeWidgets:
                w.setValue(self._sig_start_)
            else:
                w.setValue(self._sig_stop_)

    def _update_channel_ranges_(self):
        widgets = (self.presynChannelSpinBox,
                   self.postsynChannelSpinBox,
                   self.photoChannelSpinBox,
                   self.imagingChannelSpinBox)

        signalBlockers = [QtCore.QSignalBlocker(w) for w in widgets]

        for w in widgets:
            w.setMinimum(0)
            if self._n_channels_ == 0:
                w.setMaximum(0)
            else:
                w.setMaximum(self._n_channels_ - 1)

class TriggerDetectDialog(qd.QuickDialog):
    sig_detectTriggers = Signal(name="sig_detectTriggers")
    sig_undoDetectTriggers = Signal(name="sig_undoDetectTriggers")

    def __init__(self, ephysdata:typing.Optional[typing.Any]=None,
                 title: str="Detect Trigger Events", clearEvents:bool=False,
                 ephysViewer:typing.Optional[SignalViewer]=None, parent:typing.Optional[QtWidgets.QWidget]=None,
                 **kwargs):

        self._clear_events_flag_ = clearEvents

        # NOTE: 2021-04-11 17:02:58
        # thsi only informs that the detection had been performed, NOT if any
        # events had been detected!
        self._triggers_detected_ = False # True does NOT imply trigger events had been detected!
        self._triggers_imported_ = False
        self._use_trigger_signals_flag_ = True
        self._undoStack_ = deque()
        self._ephysProtocol_ = None
        self._protocolTriggers_ = None

        self.triggerProtocols = list()

        # NOTE: 2025-10-23 22:54:26 I find these below utterly confusing - why are they False ?!?
        # print(f"{self.__class__.__name__}.__init__: ephysViewer is a SignalViewer: {isinstance(ephysViewer, SignalViewer)}")
        # print(f"{self.__class__.__name__}.__init__: ephysViewer type is SignalViewer: {type(ephysViewer) == SignalViewer}")

        super().__init__(parent=parent, title=title) # needs to be called BEFORE adding any QtWidget objects

        if isinstance(ephysViewer, SignalViewer) or type(ephysViewer).__name__ == "SignalViewer":
            self._ephysViewer_ = ephysViewer
            self._owns_viewer_ = False

        else:
            self._ephysViewer_ = SignalViewer(win_title = "Detect Trigger Events", parent=self)
            self._owns_viewer_ = True

        # self.eventDetectionWidget = TriggerDetectWidget(parent = self)
        # self.addWidget(self.eventDetectionWidget)

        self.detectionTabWidget = QtWidgets.QTabWidget(parent = self)
        self.detectionTabWidget.setObjectName("detectionTabWidget")
        self.eventDetectionWidget = TriggerDetectWidget()
        self.eventDetectionWidget.setObjectName("eventDetectionWidget")
        self.protocolTriggersWidget = DIGTriggersWidget()
        self.protocolTriggersWidget.setObjectName("protocolTriggersWidget")
        self.detectionTabWidget.addTab(self.eventDetectionWidget, "Trigger Signal Channels")
        self.detectionTabWidget.addTab(self.protocolTriggersWidget, "Recording Protocol")

        self.addWidget(self.detectionTabWidget)
        self.protocolTriggersWidget.setEnabled(False)
        self._ephysViewer_.frameChanged[int].connect(self._slot_ephysFrameChanged)

        self.clearEventsCheckBox = qd.CheckBox(self, "Clear existing")
        # self.inAllSegmentsCheckBox = qd.CheckBox(self, "All segments")
        self.inAllSegmentsCheckBox = self.eventDetectionWidget.allSegmentsCheckBox

        self.clearEventsCheckBox.setIcon(QtGui.QIcon.fromTheme("edit-clear-history"))
        self.clearEventsCheckBox.setChecked(self._clear_events_flag_)
        self.clearEventsCheckBox.stateChanged.connect(self._slot_clearEventsChanged)

        # self.detectTriggersPushButton = QtWidgets.QPushButton(QtGui.QIcon.fromTheme("edit-find"),
        #                                                       "Detect", parent=self.buttons)
        self.detectTriggersPushButton = self.eventDetectionWidget.detectPushButton

        # self.detectTriggersPushButton.setToolTip("Detect events from trigger signals")
        # self.detectTriggersPushButton.setStatusTip("Detect events from trigger signals")
        # self.detectTriggersPushButton.setWhatsThis("Detect events from trigger signals")

        self.detectTriggersPushButton.clicked.connect(self.slot_detect)

        self.importDIGTriggersPushButton = self.protocolTriggersWidget.importPushButton

        # self.importDIGTriggersPushButton = QtWidgets.QPushButton(QtGui.QIcon.fromTheme("document-import"),
        #                                                       "Import", parent=self.buttons)

        # self.importDIGTriggersPushButton.setToolTip("Import from recording protocol")
        # self.importDIGTriggersPushButton.setStatusTip("Import from recording protocol")
        # self.importDIGTriggersPushButton.setWhatsThis("Import from recording protocol")

        self.importDIGTriggersPushButton.clicked.connect(self.slot_import_from_protocol)

        self.undoTriggersPushButton = QtWidgets.QPushButton(QtGui.QIcon.fromTheme("edit-undo"),
                                                            "Undo", parent=self.buttons)
        self.undoTriggersPushButton.setEnabled(False)
        self.undoTriggersPushButton.clicked.connect(self.slot_undo)

        self.useTriggerSignalsCheckBox = QtWidgets.QCheckBox("Use protocol", parent=self.buttons)

        self.useTriggerSignalsCheckBox.setChecked(not self._use_trigger_signals_flag_)

        self.useTriggerSignalsCheckBox.stateChanged.connect(self._slot_useTriggerSignalsChanged)
        # NOTE: 2021-01-06 10:57:10
        # extend/reuse the Quickdialog's own button box => widgets nicely aligned
        # on the same row instead of occupying an additional row
        self.buttons.layout.insertWidget(0, self.clearEventsCheckBox)
        # self.buttons.layout.insertWidget(1, self.inAllSegmentsCheckBox)
        # self.buttons.layout.insertWidget(2, self.detectTriggersPushButton)
        # self.buttons.layout.insertWidget(1, self.importDIGTriggersPushButton)
        self.buttons.layout.insertWidget(1, self.useTriggerSignalsCheckBox)
        self.buttons.layout.insertWidget(2, self.undoTriggersPushButton)
        self.buttons.layout.insertStretch(3)

        # NOTE: 2021-01-06 11:14:37 also place fancy icons on quickdialog's standard buttons
        self.buttons.OK.setIcon(QtGui.QIcon.fromTheme("dialog-ok-apply"))
        self.buttons.Cancel.setIcon(QtGui.QIcon.fromTheme("dialog-cancel"))

        self.statusBar = QtWidgets.QStatusBar(parent=self)
        # self.addWidget(self.statusBar)
        self.layout.addWidget(self.statusBar)

        # self.setWindowModality(QtCore.Qt.WindowModal)
        self.setWindowModality(QtCore.Qt.NonModal)

        # parse ephysdata parameter
        self._ephys_= None

        self._set_ephys_data_(ephysdata)
        self.inAllSegmentsCheckBox.setEnabled((isinstance(self._ephys_, Block) and len(self._ephys_.segments)) or (isinstance(self._ephys_, typing.Sequence) and (all(isinstance(s, Segment) for s in self._ephys_) or all(isinstance(s, Block) for s in self._ephys_)) ))

        self.setSizeGripEnabled(True)
        # self.adjustSize()

    def _updateDetectionWidget_(self):
        self.protocolTriggersWidget.setEnabled(False)
        self.detectionTabWidget.setTabEnabled(1, False)

        if isinstance(self._ephysProtocol_, ElectrophysiologyProtocol) and isinstance(self._ephys_, Block):
            self._protocolTriggers_ = dict(map(lambda k: (k, self._ephysProtocol_.getDigitalTriggers(sweep=k, byDIGIndex=True)), range(len(self._ephys_.segments))))

            if len(self._protocolTriggers_):
                usedDIGs = list(set(itertools.chain.from_iterable(list(map(lambda i: i.keys(), self._protocolTriggers_.values())))))
                trigger_data = list(map(lambda d: (d, *list(zip(*list(itertools.chain.from_iterable(map(lambda v: map(lambda v: (v[1][0], True, v[0]), filter(lambda i: i[0] == d, v[1].items())), self._protocolTriggers_.items())))))), usedDIGs))

                self.protocolTriggersWidget.setData(trigger_data)
                self.protocolTriggersWidget.setEnabled(len(self.protocolTriggersWidget._data_) > 0)
                self.detectionTabWidget.setTabEnabled(1, len(self.protocolTriggersWidget._data_) > 0)

    def _set_ephys_data_(self, value):
        if check_ephys_data_collection(value, mix=False):
            # no mixing of types when ephysdata is a sequence ...
            self._ephys_ = value
            # self._cached_events_ = get_events(self._ephys_)
            self._ephysProtocol_ = getProtocol(self._ephys_)

            flat_events = get_events(self._ephys_, flat=True)

            if len(flat_events):
                nEvents = len(flat_events)
                nTriggers = len([t for t in flat_events if isinstance(t, TriggerEvent)])
                self.statusBar.showMessage("Data has %d events, of which %d are trigger events" % (nEvents, nTriggers))

            if self.isVisible():
                self._ephysViewer_.plot(self._ephys_)

            self._update_trigger_detect_ranges_(0)

            self._updateDetectionWidget_()

    def open(self):
        if self._ephys_:
            self._ephysViewer_.plot(self.ephysdata)
        super().open()

    def exec(self):
        if self._ephys_:
            self._ephysViewer_.plot(self.ephysdata)
        return super().exec()

    def closeEvent(self, evt):
        r"""for when the dialog is closed from the window's close button
        """
        # print("closeEvent owns viewer", self._owns_viewer_)
        if self._ephysViewer_.isVisible():
            if self._owns_viewer_:
                self._ephysViewer_.close()
            else:
                self._ephysViewer_.refresh()

        # NOTE: 2021-04-16 11:30:35
        # unbind the SignalViewer reference from this symbol, otherwise the garbage
        # collector will try to double-delete C++ objects (in pyqtgraph)
        if self._owns_viewer_:
            self._ephysViewer_ = None

        super().closeEvent(evt)

    @Slot()
    def accept(self):
        super().accept()

    @Slot()
    def reject(self):
        #print("reject owns viewer", self._owns_viewer_)
        super().reject()
        # NOTE: 2021-04-16 11:24:48 this calls done(QDialog.Rejected), which
        # does all the things commented below
        #if self._ephysViewer_.isVisible():
            #if self._owns_viewer_:
                #self._ephysViewer_.close()
            #else:
                #self._ephysViewer_.refresh()

    @Slot(int)
    def done(self, value):
        r"""PyQt slot called by self.accept() and self.reject() (see QDialog).
        In turn it closes the dialog (equivalent of QWidget.close()).
        """
        if value == QtWidgets.QDialog.Accepted:
            if self._use_trigger_signals_flag_:
                if not self.detected:
                    if len(self._undoStack_) == 0:
                        self.detect_triggers(False)
            else:
                if not self.imported:
                    if len(self._undoStack_) == 0:
                        self.import_triggers(False)
        else:
            if len(self._undoStack_):
                self._restore_events_(True)

        #print("done owns viewer", self._owns_viewer_)
        if self._ephysViewer_.isVisible():
            if self._owns_viewer_:
                self._ephysViewer_.close()

            else:
                # self._ephysViewer_.refresh()
                self._ephysViewer_.displayFrame()

        # NOTE: 2021-04-16 11:30:35
        # unbind the SignalViewer reference from this symbol, otherwise the garbage
        # collector will try to double-delete C++ objects (in pyqtgraph)
        #self._ephysViewer_ = None

        super().done(value)

    @Slot()
    def _slot_useTriggerSignalsChanged(self):
        self._use_trigger_signals_flag_ = not self.useTriggerSignalsCheckBox.isChecked()

    @Slot()
    def _slot_clearEventsChanged(self):
        self._clear_events_flag_ = self.clearEventsCheckBox.selection()

    @Slot(int)
    def _slot_ephysFrameChanged(self, value):
        if not self.eventDetectionWidget.relTimes:
            self._update_trigger_detect_ranges_(value)

    @Slot()
    def slot_import_from_protocol(self):
        self.import_triggers()

    @Slot()
    def slot_detect(self):
        if self._ephys_ is None:
            return

        self.detect_triggers()

        if self.isVisible():
            if self._ephysViewer_.isVisible() and  self._ephysViewer_.y:
                # self._ephysViewer_.refresh()
                self._ephysViewer_.displayFrame()
            else:
                self._ephysViewer_.plot(self.ephysdata)

    @Slot()
    def slot_undo(self):
        r"""Quickly restore the events - no fancy stuff
        """
        self._restore_events_()
        if self.isVisible():
            if self._ephysViewer_.isVisible() and self._ephysViewer_.y:
                # self._ephysViewer_.refresh()
                self._ephysViewer_.displayFrame()
            else:
                self._ephysViewer_.plot(self._ehys_)

        self.detected = False

    def _restore_events_(self, initial:bool=False):
        # print(f"{self.__class__.__name__}._restore_events_: cached events: {self._cached_events_}")
        # if len(self._cached_events_):
        if len(self._undoStack_) == 0:
            return

        self._cached_events_ = self._undoStack_[0] if initial else self._undoStack_[-1] # defer popping until events restoration was successful

        try:
            if isinstance(self._ephys_, Block):
                for k, s in enumerate(self._ephys_.segments):
                    remove_events(s)
                    s.events[:] = self._cached_events_[k][:]

            elif isinstance(self._ephys_, Segment):
                remove_events(self._ephys_)
                self._ephys_.events[:] = self._cached_events_[0][:]

            elif isinstance(self._ephys_, (tuple, list)):
                if all([isinstance(v, Block) for v in self._ephys_]):
                    for k, b in enumerate(self._ephys_):
                        for ks, s in enumerate(b.segments):
                            remove_events(s)
                            s.events[:] = self._cached_events_[k][ks][:]

                elif all([isinstance(v, Segment) for v in self._ephys_]):
                    for k, s in enumerate(self._ephys_):
                        remove_events(s)
                        s.events[:] = self._cached_events_[k][:]

            if not initial:
                self._undoStack_.pop() # might still clear the stack
        except:
            traceback.print_exc()

        self.undoTriggersPushButton.setEnabled(len(self._undoStack_) > 0 )

    @property
    def imported(self) -> bool:
        return self._triggers_imported_

    @imported.setter
    def imported(self, value:bool):
        self._triggers_imported_ = value == True

    @property
    def detected(self):
        return self._triggers_detected_

    @detected.setter
    def detected(self, val):
        self._triggers_detected_ = val
        # self.detectTriggersPushButton.setEnabled(not self._triggers_detected_)

    @property
    def ephysdata(self):
        return self._ephys_

    @ephysdata.setter
    def ephysdata(self, value):
        self._set_ephys_data_(value)

    @property
    def presyn(self):
        return self.eventDetectionWidget.presyn

    @property
    def postsyn(self):
        return self.eventDetectionWidget.postsyn

    @property
    def photo(self):
        return self.eventDetectionWidget.photo

    @property
    def imaging(self):
        return self.eventDetectionWidget.imaging

    def import_triggers(self, undoEnabled:bool=True):
        trigger_model_data = self.protocolTriggersWidget._dataModel_
        # print(f"{self.__class__.__name__}.import_triggers: trigger model data = {trigger_model_data.modelData}")
        imported_trigger_events = list(map(lambda row: (row[1][0], row[3]), filter(lambda row: row[2][0], trigger_model_data.modelData)))
        # print(f"{self.__class__.__name__}.import_triggers: used trigger events = {imported_trigger_events}")

        if undoEnabled:
            self._cached_events_ = get_events(self._ephys_) # cache all events, not just the trigger ones
            self._undoStack_.append(self._cached_events_)

        if len(imported_trigger_events):
            segments = self._get_segments_()
            clear_flag = "triggers" if self._clear_events_flag_ else False

            for (trigger_events, sweeps) in imported_trigger_events:
                tevent = trigger_events
                for sweep in sweeps:
                    try:
                        seg = segments[sweep]
                        if clear_flag == "triggers":
                            remove_events(seg, triggersOnly=True)
                        embed_trigger_event(tevent, seg)
                    except:
                        traceback.print_exc()
                        scipywarn(f"Event sweep {sweep} not present in data")
                        continue


            nEvents = len(get_trigger_events(self.ephysdata, flat=True))
            self.imported = nEvents > 0
            self._ephysViewer_.plot(self._ephys_)
            msg = f"{nEvents} triger events imported from protocol"
            # if not self.inAllSegmentsCheckBox.isChecked():
            #     msg += f" in frame {self._ephysViewer_.currentFrame}"
            self.statusBar.showMessage(msg)
            self.undoTriggersPushButton.setEnabled(len(self._undoStack_)>0)

    def detect_triggers(self, undoEnabled:bool=True):
        from functools import partial
        # NOTE: 2025-10-25 08:16:23
        # detaching trigger event detection from trigger protocol construction:
        # don't use protocols here, anymore; just detect trigger events
        if self._ephys_ is None or self._ephysViewer_ is None:
            self.detected=False
            return

        # tpars = {"presynaptic":         self.presyn,
        #          "postsynaptic":        self.postsyn,
        #          "photostimulation":    self.photo,
        #          "imaging_frame":       self.imaging}

        tpars = dict(filter(lambda v: len(v[1])>0, zip(("presynaptic", "postsynaptic", "photostimulation", "imaging_frame"),
                                                       (self.presyn, self.postsyn, self.photo, self.imaging))))


        if undoEnabled:
            self._cached_events_ = get_events(self._ephys_) # cache all events, not just the trigger ones
            self._undoStack_.append(self._cached_events_)

        # print(f"{self.__class__.__name__}.detect_triggers: cached events: {self._cached_events_}")

        # if any(map(lambda o: len(o)>0, (self.presyn, self.postsyn, self.photo, self.imaging))):
        if len(tpars):
            segments = self._get_segments_()

            # NOTE: 2021-03-21 14:29:27
            # only clear existing trigger events
            clear_flag = "triggers" if self._clear_events_flag_ else False

            # NOTE: 2025-10-25 08:25:43 this below moified from
            # triggerprotocols.auto_detect_trigger_protocols(…)

            for seg in segments:
                nSignals = len(seg.analogsignals)
                detected_events = list()
                for p_name, p_tuple in tpars.items():
                    if len(p_tuple) == 0:
                        continue
                    # print(f"{self.__class__.__name__}.detect_triggers: p_name = {p_name}, p_tuple = {p_tuple}")
                    signalIndex = p_tuple[0]

                    if signalIndex not in range(nSignals):
                        raise ValueError(f"Wrong signal index specified {signalIndex} for {nSignals} signals in segment {k}")

                    if len(p_tuple) >= 2: # skip empty trigger spec
                        use_lo_hi = True if len(p_tuple) == 2 else p_tuple[2]

                        if len(p_tuple) == 4:
                            if not isinstance(p_tuple[3], tuple) or len(p_tuple[3]) != 2 or (not all(isinstance(v_, pq.Quantity) and unitsConvertible(v_, pq.s) and v_.size==1 for v_ in p_tuple[3])):
                                raise ValueError(f"When specified, the third element in a {p_name} trigger specification must have exactly two scalar time quantities")
                            time_slice = p_tuple[3]
                        else:
                            time_slice = None

                    sig = seg.analogsignals[signalIndex]

                    if time_slice:
                        if self.eventDetectionWidget.relTimes:
                            t0, t1 = tuple(map(lambda v: v + seg.analogsignals[signalIndex].t_start, time_slice))
                        else:
                            t0, t1 = time_slice

                        sig = sig.time_slice(t0, t1)

                    te = detect_trigger_events(sig, TriggerEventType[p_name], use_lo_hi = p_tuple[2], label=p_tuple[1], name=p_tuple[1])
                    if isinstance(te, TriggerEvent):
                        detected_events.append(te)

                if len(detected_events):
                    if clear_flag == "triggers":
                        remove_events(seg, triggersOnly=True)
                    for te in detected_events:
                        embed_trigger_event(te, seg)


            nEvents = len(get_trigger_events(self.ephysdata, flat=True))
            self.detected = nEvents > 0

            self._ephysViewer_.plot(self._ephys_)
            msg = f"{nEvents} triger events detected"
            if not self.inAllSegmentsCheckBox.isChecked():
                msg += f" in frame {self._ephysViewer_.currentFrame}"
            self.statusBar.showMessage(msg)
            self.undoTriggersPushButton.setEnabled(len(self._undoStack_)>0)

    # def _get_segments_(self) -> typing.Tuple[list, int]:
    def _get_segments_(self) -> typing.Sequence[Segment]:
        if isinstance(self._ephys_, Block):
            if self._use_trigger_signals_flag_:
                if self.inAllSegmentsCheckBox.isChecked():
                    segments = list(self._ephys_.segments)
                else:
                    segments = [self._ephys_.segments[self._ephysViewer_.currentFrame]]
            else:
                segments = list(self._ephys_.segments)

        elif isinstance(self._ephys_, typing.Sequence):
            if all(isinstance(s, Segment) for s in self._ephys_):
                if self.inAllSegmentsCheckBox.isChecked():
                    segments = self._ephys_
                else:
                    segments = [self._ephys_[self._ephysViewer_.currentFrame]]

            elif all(isinstance(v, Block) for v in self._ephys_):
                segments = list(itertools.chain(*(b.segments for b in self._ephys_)))
                if not self.inAllSegmentsCheckBox.isChecked():
                    segments = [segments[self._ephysViewer_.currentFrame]]

            else:
                scipywarn(f"Expecting a homogeneous sequence of Blocks or Segments; instead, got a sequence of {set(map(lambda v: type(v).__name__), self._ephys_)}")
                segments = list()

        elif isinstance(self._ephys_, Segment):
            segments = [self._ephys_]

        else:
            segments = list()

        return segments #, len(segments)

    def _update_trigger_detect_ranges_(self, frameindex):
        if self._ephys_ is None:
            return

        segment = None

        if isinstance(self._ephys_, Block):
            if frameindex < 0 or frameindex >= len(self._ephys_.segments):
                raise ValueError("Incorrect frame index %s" % frameindex)

            segment = self._ephys_.segments[frameindex]

        elif isinstance(self._ephys_, Segment):
            segment = self._ephys_

        elif isinstance(self._ephys_, typing.Sequence):
            if all([isinstance(v, Block) for v in self._ephys_]):
                segments = list(itertools.chain(*(b.segments for b in self._ephys_)))
                segment = segments[frameindex]

            elif all([isinstance(v, Segment) for v in self._ephys_]):
                segment = self._ephys_[frameindex]

            else:
                return

        else:
            return

        if segment:
            # NOTE: 2025-10-25 13:49:16 only use regularly sampled signals
            nChannels = max([len(seg.analogsignals) for seg in self._ephys_.segments])
            # nChannels = max([len(seg.analogsignals) + len(seg.irregularlysampledsignals) for seg in self._ephys_.segments])
            self.eventDetectionWidget.nChannels = nChannels
            if self.eventDetectionWidget.relTimes:
                self.eventDetectionWidget.signalStart = 0.0 * pq.s
                self.eventDetectionWidget.signalStop = min([sig.t_stop - sig.t_start for sig in segment.analogsignals])
            else:
                self.eventDetectionWidget.signalStart = min([sig.t_start for sig in segment.analogsignals])
                self.eventDetectionWidget.signalStop = max([sig.t_stop for sig in segment.analogsignals])


def guiDetectTriggers(data:Block):
    if isinstance(data, Block) and len(data.segments):
        eventDetectionDialog = TriggerDetectDialog(ephysdata = data,
                                                   clearEvents = True)
        eventDetectionDialog.adjustSize()
        result = eventDetectionDialog.exec()

        if result == QtWidgets.QDialog.Accepted:
            return eventDetectionDialog.triggerProtocols

