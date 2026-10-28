# $Id: recordingsourcewidget.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
Widget for UI interaction with a ephys_pathways.RecordingSource object
"""

import sys, os, typing, types, warnings, math, cmath # noqa
import numbers # noqa
import numpy as np # noqa
import quantities as pq # noqa
# import neo
from tribool import Tribool # noqa

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

    from qtpy import sip# noqa
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

from core import (
    datatypes,  # noqa
    qtutils,
)
from core.prog import scipywarn  # noqa
from ephys import ephys, ephys_pathways
from gui import guiutils  # noqa: F401
from gui.widgets.dataclasswidgets.dataclasswidget import DataClassWidget

# from gui.workspacegui import WorkspaceGuiMixin
# from iolib import pictio as pio

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

try:
    from gui.widgets.dataclasswidgets.recordingsourcewidget_ui import Ui_RecordingSourceWidget  # noqa: I001

except:  # noqa: E722
    Ui_RecordingSourceWidget, QWidget = loadUiType(
        os.path.join(__module_path__, "recordingsourcewidget.ui")
        )

T = ephys_pathways.RecordingSource

class RecordingSourceWidget(Ui_RecordingSourceWidget, DataClassWidget, QtWidgets.QWidget):
    # NOTE: 2026-10-27 14:15:18
    # general principlea:
    # 1. each child widget modifies DIRECTLY the corresponding component of self._data_
    #
    # 2. This widget is NOT about creating a NEW object of the same data class!
    # I.e, if you want a new RecordingSource, then create it somewhere else in your
    # code THEN pass it to this widget for editing via the UI!
    #
    # sig_valueChanged = Signal(object, name="sig_valueChanged")
    _objectType_ = ephys_pathways.RecordingSource
    _objectTypes_ = (ephys_pathways.RecordingSource, )

    def __init__(self, parent: QtWidgets.QWidget | None = None,
                 obj: T | None = None,
                 **kwargs):
        if isinstance(parent, self._objectTypes_):
            obj_ = parent
            if isinstance(obj, QtWidgets.QWidget):
                parent = obj
            else:
                parent = None

            obj = obj_

        QtWidgets.QWidget.__init__(self, parent)
        DataClassWidget.__init__(self, parent=parent, **kwargs)
        Ui_RecordingSourceWidget.__init__(self)

        self._electrodeModeNames_ = list(ephys.ElectrodeMode.names())

        self._pendingPathwayChange_ = None
        self._pendingStimulusChange_ = None
        self._electrode_ = ephys.ElectrodeMode.Null

        if not isinstance(obj, self._objectTypes_):
            self._data_ = self._objectType_(electrodeMode=self._electrode_) # use c'tor defaults!
            self._data_.name = "recordingSource"
            self._data_.syn.name = self._data_.name
            self._data_.pathways.name = self._data_.name
        else:
            self._data_ = obj

        self._configureUI_()

    def default(self) -> T:
        # self._name_ = "source"
        # self._adc_ = 0
        # self._dac_ = 0
        # self._syn_ = ephys_pathways.SynapticStimulusChannelList(name=self._name_)
        # self._auxin_ = ephys_pathways.AuxiliaryInputList()
        # self._auxout_ = ephys_pathways.AuxiliaryOutputList()
        # self._electrode_ = ephys.ElectrodeMode.Null
        # self._pathways_ = ephys_pathways.SynapticPathwayList(name=self._name_)
        self._reset_()
        return self._data_


    def _configureUI_(self):
        self.setupUi(self)
        super()._configureUI_() # DataClassWidget!

        self.nameDescriptionWidget.symbol=self.objectSymbol # inherited from dataclasswidget
        self.nameDescriptionWidget.setData(self._data_)
        self.adcSpinBox.setToolTip("Index of ADC (input) channel used for recording")
        self.adcSpinBox.setWhatsThis("Index of ADC (input) channel used for recording")
        self.adcSpinBox.setStatusTip("Index of ADC (input) channel used for recording")
        self.adcSpinBox.setMinimum(0)
        self.adcSpinBox.setValue(self._data_.adc)
        self.adcSpinBox.valueChanged.connect(self._slot_adcChanged)


        self.dacSpinBox.setToolTip("Input channel index")
        self.dacSpinBox.setWhatsThis("Input channel index")
        self.dacSpinBox.setStatusTip("Input channel index")
        self.dacSpinBox.setMinimum(0)
        self.dacSpinBox.setValue(self._data_.dac)
        self.dacSpinBox.valueChanged.connect(self._slot_dacChanged)

        for text in self._electrodeModeNames_:
            self.electrodeModeComboBox.addItem(text)

        currentElectrodeModeNdx = self._electrodeModeNames_.index(self._electrode_.name)
        self.electrodeModeComboBox.setCurrentIndex(currentElectrodeModeNdx)

        self.electrodeModeComboBox.currentTextChanged.connect(self._slot_electrodeModeChanged)

        self.auxInPushButton.clicked.connect(self._slot_editAuxIn)
        self.auxOutPushButton.clicked.connect(self._slot_editAuxOut)
        self.createObjectPushButton.clicked.connect(self._slot_new)
        self.createTwoPathwaysSourcePushButton.clicked.connect(self._slot_makeTwoPathwaysSource)

        self.stimulusListTable.isAutoResizeColumns = True
        self.stimulusListTable.setToolTip("Configured Stimulus Channels")
        self.stimulusListTable.setValue(self._data_.syn)
        self.stimulusListTable.autoResizeColumns()

        self.stimulusListTable.sig_indexRowColChanged.connect(self._slot_singleStimulusChannelChanged)#, type=QtCore.Qt.DirectConnection)
        self.stimulusListTable.sig_indexChanged.connect(self._slot_singleStimulusChannelChanged)#, type=QtCore.Qt.DirectConnection)
        self.stimulusListTable.sig_dataChanged.connect(self._slot_stimulusListChanged)
        self.stimulusListTable.sig_indexesChanged.connect(self._slot_stimulusListIndexesChanged)

        # self.synapticPathwaysTable.enforceReadOnly = True
        self.synapticPathwaysTable.isAutoResizeColumns = True
        self.synapticPathwaysTable.setToolTip("Configured Synaptic Pathways")
        self.synapticPathwaysTable.setValue(self._data_.pathways)
        self.synapticPathwaysTable.autoResizeColumns()

        self.synapticPathwaysTable.sig_indexRowColChanged.connect(self._slot_singleSynapticPathwayChanged)#, type=QtCore.Qt.DirectConnection)
        self.synapticPathwaysTable.sig_indexChanged.connect(self._slot_singleSynapticPathwayChanged)#, type=QtCore.Qt.DirectConnection)
        self.synapticPathwaysTable.sig_dataChanged.connect(self._slot_synapticPathwaysListChanged)

    @Slot(int)
    def _slot_adcChanged(self, val: int):
        self._data_.adc = val
        for pathway in self._data_.pathways:
            pathway.adc = self._data_adc

        self.sig_valueChanged.emit(self.value())

    @Slot(int)
    def _slot_dacChanged(self, val: int):
        self._data_.dac = val
        for pathway in self._data_.pathways:
            pathway.dac = self._data_.dac

        self.sig_valueChanged.emit(self.value())

    @Slot(str)
    @Slot(int)
    def _slot_electrodeModeChanged(self, val: int | str):
        if isinstance(val, int) and val >=0 and val < len(self._electrodeModeNames_):
            # CAUTION: 2026-10-27 15:00:38
            # when val is an int, it is the INDEX of the selected electrode mode name
            # in the combo box, NOT the int value of a specific ElectrodeMode enum value!!!
            val = self._electrodeModeNames_[val]

        if isinstance(val, str) and val in self._electrodeModeNames_:
            self._electrode_ = ephys.ElectrodeMode[val]
            pathwaysElectrodeModes = [p.electrodeMode for p in self._data_.pathways]
            if (any(eMode != self._electrode_ for eMode in pathwaysElectrodeModes)
                 and self.questionMessage("Electrode Mode Change", "This will set a new value to the eletrode mode in ALL pathways. Continue?") == QtWidgets.QMessageBox.Yes
                 ):
                for pathway in self._data_.pathways:
                    if pathway.electrodeMode != self._electrode_:
                        pathway.electrodeMode = self._electrode_

            with qtutils.SignalBlocker(self.synapticPathwaysTable):
                self.synapticPathwaysTable.setValue(self._data_.pathways)
                self.synapticPathwaysTable.autoResizeColumns()

            self.sig_valueChanged.emit(self.value())

    @Slot()
    def _slot_new(self):
        self._make_value_() # emits a new instance of self._data_ type

    def _reset_(self):
        self._data_ = self._objectType_()

    def _make_value_(self) -> ephys_pathways.RecordingSource:
        # NOTE: 2026-10-27 14:11:06
        # create a new RecordingSource using individual components from self._data_
        # This presupposes that any edit in an individual chillld widget found
        # its way to the corresponding attribute (field/member) of self._data_ !!!
        from copy import deepcopy
        ret = self._objectType_(name = self._data_.name,
                                 adc = self._data_.adc,
                                 dac = self._data_.dac,
                                 syn = deepcopy(self._data_.syn),
                                 auxin = deepcopy(self._data_.auxin),
                                 auxout = deepcopy(self._data_.auxout),
                                 electrodeMode = self._data_.electrodeMode,
                                 pathways = deepcopy(self._data_.pathways))

        self.sig_valueChanged.emit(ret)
        return ret

    @Slot()
    def _slot_editAuxIn(self):
        from gui.delegates import ExternalEditorDelegate
        editor = ExternalEditorDelegate(self._data_.auxin, self)
        editor.setObjectName("auxInEditor")
        editor.sig_valueChanged.connect(self._slot_auxInChanged)
        editor.slot_Launch()

    @Slot()
    def _slot_editAuxOut(self):
        from gui.delegates import ExternalEditorDelegate
        editor = ExternalEditorDelegate(self._data_.auxout, self)
        editor.setObjectName("auxOutEditor")
        editor.sig_valueChanged.connect(self._slot_auxOutChanged)
        editor.slot_Launch()

    @Slot(int, int)
    @Slot(QtCore.QModelIndex)
    def _slot_singleSynapticPathwayChanged(self, row: int | QtCore.QModelIndex,
                                           col: int | None = None):
        with qtutils.SignalBlocker(self.synapticPathwaysTable):
            if isinstance(row, QtCore.QModelIndex):
                col = row.column()
                row = row.row()

            self._pendingPathwayChange_ = (row, col)

    @Slot(QtCore.QModelIndex, QtCore.QModelIndex)
    def _slot_pathwaysListIndexesChanged(self, topLeft, bottomRight):
        # with qtutils.SignalBlocker((self.electrodeModeComboBox,
        #                             self.synapticPathwaysTable,
        #                             self.stimulusListTable)):
        #     # self.electrodeModeComboBox.setCurrentIndex(currentElectrodeModeNdx)
        #
        #     self.synapticPathwaysTable.setValue(self._data_.pathways) # to reflect ALL pathway changes
        #     self.synapticPathwaysTable.autoResizeColumns()
        #
        #     self.stimulusListTable.setValue(self._data_.syn) # to reflect ALL stimulus changes
        #     self.stimulusListTable.autoResizeColumns()

        self.sig_valueChanged.emit(self._data_)

        # if topLeft.row() == bottomRight.row():
        #     row = topLeft.row()
        #     pathway = self.synapticPathwaysTable.value()[row]
        #     eMode = pathway.electrodeMode
        #     self._data_.pathways[row] = pathway
        #     for p in self._data_.pathways:
        #         p.electrodeMode = eMode
        #
        #     pathStimsIDs = [id(p.stimulus) for p in self._data_.pathways]
        #
        #     excessStims = [stim for stim in self._data_.syn if id(stim) not in pathStimsIDs]
        #
        #     excessStimNdx = [self._data_syn.index(stim) for stim in excessStims]
        #
        #     for ndx in excessStimNdx:
        #         del self._data_.syn[ndx]
        #
        #     for pathway in self._data_.pathways:
        #         if id(pathway.stimulus) not in [id(stim) for stim in self._data_.syn]:
        #             self._data_.syn.append(pathway.stimulus)
        #
        #     # self._data_.syn = ephys_pathways.SynapticStimulusChannelList(p.stimulus for p in self._data_.pathways)
        #
        #     currentElectrodeModeNdx = self._electrodeModeNames_.index(eMode.name)
        #
        #     with qtutils.SignalBlocker((self.electrodeModeComboBox,
        #                                 self.synapticPathwaysTable,
        #                                 self.stimulusListTable)):
        #         # self.electrodeModeComboBox.setCurrentIndex(currentElectrodeModeNdx)
        #
        #         self.synapticPathwaysTable.setValue(self._data_.pathways) # to reflect ALL pathway changes
        #         self.synapticPathwaysTable.autoResizeColumns()
        #
        #         self.stimulusListTable.setValue(self._data_.syn) # to reflect ALL stimulus changes
        #         self.stimulusListTable.autoResizeColumns()
        #
        #     self.sig_valueChanged.emit(self._data_)

    @Slot()
    def _slot_synapticPathwaysListChanged(self):
        widget = self.sender()
        if widget == self.synapticPathwaysTable:
            pathways = widget.value()
            if not isinstance(pathways, ephys_pathways.SynapticPathwayList):
                return
            self._data_.pathways = pathways

            if not isinstance(self._data_.syn, ephys_pathways.SynapticStimulusChannelList):
                self._data_.syn = ephys_pathways.SynapticStimulusChannelList()

            self._syncStimListToPathways()
            self.sig_valueChanged.emit(self._data_)

    def _syncStimListToPathways(self):
        with qtutils.SignalBlocker((
                        self.stimulusListTable,
                        self.synapticPathwaysTable,
                        # self.electrodeModeComboBox
                    )):
            pathwayStimIDs = [id(p.stimulus) for p in self._data_.pathways]

            if len(self._data_.syn):
                excessStimNdx = [self._data_.syn.index(stim) for stim in self._data_.syn if id(stim) not in pathwayStimIDs]
                for ndx in excessStimNdx:
                    del self._data_.syn[ndx]

            for pathway in self._data_.pathways:
                if (
                    isinstance(pathway.stimulus, ephys_pathways.SynapticStimulusChannel)
                    and (
                        len(self._data_.syn) == 0
                        or id(pathway.stimulus) not in [id(stim) for stim in self._data_.syn]
                        )
                    ):
                    self._data_.syn.append(pathway.stimulus)

            self.stimulusListTable.setValue(self._data_.syn)
            self.stimulusListTable.autoResizeColumns()

    @Slot(int, int)
    @Slot(QtCore.QModelIndex)
    def _slot_singleStimulusChannelChanged(self, row: int | QtCore.QModelIndex,
                                           col: int | None = None
                                           ):
        with qtutils.SignalBlocker(self.stimulusListTable):
            if isinstance(row, QtCore.QModelIndex):
                col = row.column()
                row = row.row()

            self._pendingStimulusChange_ = (row, col)

    @Slot(QtCore.QModelIndex, QtCore.QModelIndex)
    def _slot_stimulusListIndexesChanged(self, topLeft, bottomRight):
        if topLeft.row() == bottomRight.row():
            row = topLeft.row()
            self._data_.syn[row] = self.stimulusListTable.value()[row]
        self.sig_valueChanged.emit(self._data_)

    @Slot()
    def _slot_stimulusListChanged(self):
        with qtutils.SignalBlocker((self.stimulusListTable, self.synapticPathwaysTable)):
            widget = self.sender()
            if widget == self.stimulusListTable:
                syn = widget.value()
                if not isinstance(syn, ephys_pathways.SynapticStimulusChannelList):
                    return
                self._data_.syn = syn

                if not isinstance(self._data_.pathways, ephys_pathways.SynapticPathwayList):
                    self._data_.pathways = ephys_pathways.SynapticPathwayList()

                self._syncPathwayListToStims()

                self.sig_valueChanged.emit(self._data_)

    def _syncPathwayListToStims(self):
        with qtutils.SignalBlocker((
                        self.stimulusListTable,
                        self.synapticPathwaysTable,
                        # self.electrodeModeComboBox,
                    )):

            if len(self._data_.syn) == 0:
                return  # nothing to synchronize - NOTE: pathways without a stimulus channel are acceptable!

            synIds = [id(obj) for obj in self._data_.syn]

            if len(self._data_.pathways) == 0:
                for stim in self._data_.syn:
                    pathway = ephys_pathways.SynapticPathway(stimulus = stim,
                                                                name = f"{stim.name}_pathway",
                                                                adc= self._data_.adc,
                                                                dac = self._data_.dac,
                                                                electrode = self._electrode_
                                                            )
                    self._data_.pathways.append(pathway)

            else:
                pathwayStimIDs = [id(p.stimulus) for p in self._data_.pathways]
                for stim in self._data_.syn:
                    if id(stim) not in pathwayStimIDs:
                        pathway = ephys_pathways.SynapticPathway(stimulus = stim,
                                                                    name = f"{stim.name}_pathway",
                                                                    adc= self._data_.adc,
                                                                    dac = self._data_.dac,
                                                                    electrode = self._electrode_
                                                                )
                        self._data_.pathways.append(pathway)


                # synIds = [id(obj) for obj in syn]
                # if len(syn) < len(self._data_.pathways):
                #     retainedPathways = [p for p in self._data_.pathways if id(p.stimulus) in synIds]
                #     # retainedPathways = ephys_pathways.SynapticPathwayList(p for p in self._data_.pathways if p.stimulus in syn) #list(filter(lambda p: p.stimulus in syn, self._data_.pathways)))
                #     # retainedPathways = ephys_pathways.SynapticPathwayList(list(filter(lambda p: p.stimulus in syn, self._data_.pathways)))
                #     self._data_.pathways = retainedPathways
                #     self._data_.syn = syn
                # elif len(syn) > len(self._data_.pathways):
                #     for k in range(len(self._data_.pathways), len(syn)):
                #         pathway = ephys_pathways.SynapticPathway(stimulus = syn[k],
                #                                                 name = f"{syn[k].name}_pathway",
                #                                                 adc= self._data_.adc,
                #                                                 dac = self._data_.dac,
                #                                                 electrode = self._data_.electrodeMode
                #                                                 )
                #         self._data_.pathways.append(pathway)

            self.synapticPathwaysTable.setValue(self._data_.pathways)
            self.synapticPathwaysTable.autoResizeColumns()


    @Slot(object)
    def _slot_auxInChanged(self, val: ephys_pathways.AuxiliaryInputList | None = None):
        if isinstance(val, ephys_pathways.AuxiliaryInputList):
            self._data_.auxin = val
        else:
            self._data_.auxin = ephys_pathways.AuxiliaryInputList()

        self.sig_valueChanged.emit(self._data_)

    @Slot(object)
    def _slot_auxOutChanged(self, val: ephys_pathways.AuxiliaryOutputList | None = None):
        if isinstance(val, ephys_pathways.AuxiliaryOutputList):
            self._data_.auxout = val
        else:
            self._data_.auxout = ephys_pathways.AuxiliaryOutputList()

        self.sig_valueChanged.emit(self._data_)

    @Slot(object)
    def slot_valueChanged(self, val):
        self._data_ = val

    @Slot()
    def _slot_makeTwoPathwaysSource(self):
        from gui import interact

        paths = interact.getInputs(path0=0, path1=1,
                                   dlg_title="Digital output channels for pathway stimulation",
                                   dlg_widget_orientation=QtCore.Qt.Horizontal,
                                   modal=True)
        if paths is None:
            return

        path0stim, path1stim = paths

        result = ephys_pathways.twoPathwaysSource(self._data_.adc, self._data_.dac,
                                                 path0stim=path0stim,
                                                 path1stim=path1stim,
                                                 name=self._data_.name,
                                                 electrodeMode = self._data_.electrodeMode)
        self.setValue(result)
        self.sig_valueChanged.emit(self._data_)

    def setValue(self, val: T | None = None):
        # print(f"{self.__class__.__name__}.setValue({val}) <{type(val).__name__}>")
        if isinstance(val, self._objectType_):
            self._data_ = val

        else:
            self._name_ = "source"
            self._adc_ = 0
            self._dac_ = 0
            self._syn_ = ephys_pathways.SynapticStimulusChannelList(name=self._name_)
            self._auxin_ = ephys_pathways.AuxiliaryInputList()
            self._auxout_ = ephys_pathways.AuxiliaryOutputList()
            self._electrode_ = ephys.ElectrodeMode.Null
            self._pathways_ = ephys_pathways.SynapticPathwayList(name=self._name_)
            self._make_value_()

        with qtutils.SignalBlocker(
            (
                self.nameDescriptionWidget,
                self.adcSpinBox,
                self.dacSpinBox,
                self.electrodeModeComboBox,
                self.auxOutPushButton,
                self.auxInPushButton,
                self.synapticPathwaysTable,
                self.stimulusListTable,
            )
            ):
            super().setValue(self._data_) # to populate the DataClassWidget fields
            self.adcSpinBox.setValue(self._data_.adc)
            self.dacSpinBox.setValue(self._data_.dac)
            currentElectrodeModeNdx = self._electrodeModeNames_.index(self._data_.electrodeMode.name)
            self.electrodeModeComboBox.setCurrentIndex(currentElectrodeModeNdx)

        self.stimulusListTable.setValue(self._data_.syn)
        self.stimulusListTable.autoResizeColumns()

        self.synapticPathwaysTable.setValue(self._data_.pathways)
        self.synapticPathwaysTable.autoResizeColumns()

    def value(self) -> T:
        return self._data_

