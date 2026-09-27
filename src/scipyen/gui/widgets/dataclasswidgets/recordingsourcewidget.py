# -*- coding: utf-8 -*-
# $Id: recordingsourcewidget.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
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

from ephys import ephys
from ephys import ephys_pathways
from core import datatypes # noqa
from core import qtutils
from core.prog import scipywarn # noqa
from gui import guiutils
from gui.widgets.dataclasswidgets.dataclasswidget import DataClassWidget
# from gui.workspacegui import WorkspaceGuiMixin
# from iolib import pictio as pio

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

try:
    from gui.widgets.dataclasswidgets.recordingsourcewidget_ui import Ui_RecordingSourceWidget

except:
    Ui_RecordingSourceWidget, QWidget = loadUiType(
        os.path.join(__module_path__, "recordingsourcewidget.ui")
        )

T = ephys_pathways.RecordingSource

class RecordingSourceWidget(Ui_RecordingSourceWidget, DataClassWidget, QtWidgets.QWidget):
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

        if not isinstance(obj, self._objectTypes_):
            self._data_ = None
            self._name_ = "source"
            self._adc_ = 0
            self._dac_ = 0
            self._syn_ = ephys_pathways.SynapticStimulusChannelList(name=self._name_)
            self._auxin_ = ephys_pathways.AuxiliaryInputList()
            self._auxout_ = ephys_pathways.AuxiliaryOutputList()
            self._electrode_ = ephys.ElectrodeMode.Null
            self._pathways_ = ephys_pathways.SynapticPathwayList(name=self._name_)
            self._make_value_()
        else:
            self._data_ = obj
            self._name_ = self._data_.name
            self._adc_ = self._data_.adc
            self._dac_ = self._data_.dac
            self._syn_ = self._data_.syn
            self._auxin_ = self._data_.auxin
            self._auxout_ = self._data_.auxout
            self._electrode_ = self._data_.electrodeMode
            self._pathways_ = self._data_.pathways

        self._configureUI_()

    def default(self) -> T:
        self._name_ = "source"
        self._adc_ = 0
        self._dac_ = 0
        self._syn_ = ephys_pathways.SynapticStimulusChannelList(name=self._name_)
        self._auxin_ = ephys_pathways.AuxiliaryInputList()
        self._auxout_ = ephys_pathways.AuxiliaryOutputList()
        self._electrode_ = ephys.ElectrodeMode.Null
        self._pathways_ = ephys_pathways.SynapticPathwayList(name=self._name_)
        self._make_value_()
        return self._data_


    def _configureUI_(self):
        self.setupUi(self)
        super()._configureUI_() # DataClassWidget!

        self.nameDescriptionWidget.symbol="recordingSource"
        self.nameDescriptionWidget.setData(self._data_)
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

        for text in self._electrodeModeNames_:
            self.electrodeModeComboBox.addItem(text)

        currentElectrodeModeNdx = self._electrodeModeNames_.index(self._electrode_.name)
        self.electrodeModeComboBox.setCurrentIndex(currentElectrodeModeNdx)

        self.electrodeModeComboBox.currentTextChanged.connect(self._slot_electrodeModeChanged)

        self.auxInPushButton.clicked.connect(self._slot_editAuxIn)
        self.auxOutPushButton.clicked.connect(self._slot_editAuxOut)

        self.createObjectPushButton.setText("")
        self.createObjectPushButton.setIcon(guiutils.getIcon("document-new"))
        self.createObjectPushButton.setToolTip("Create Recording Source")
        self.createObjectPushButton.setWhatsThis("Create Recording Source")
        self.createObjectPushButton.setStatusTip("Create Recording Source")
        self.createObjectPushButton.clicked.connect(self._slot_new)

        self.stimulusListTable.isAutoResizeColumns = True
        self.stimulusListTable.setToolTip("Configured Stimulus Channels")
        self.stimulusListTable.setValue(self._syn_)
        self.stimulusListTable.autoResizeColumns()

        self.stimulusListTable.sig_indexRowColChanged.connect(self._slot_singleStimulusChannelChanged)#, type=QtCore.Qt.DirectConnection)
        self.stimulusListTable.sig_indexChanged.connect(self._slot_singleStimulusChannelChanged)#, type=QtCore.Qt.DirectConnection)
        self.stimulusListTable.sig_dataChanged.connect(self._slot_stimulusListChanged)
        self.stimulusListTable.sig_indexesChanged.connect(self._slot_stimulusListIndexesChanged)

        # self.synapticPathwaysTable.enforceReadOnly = True
        self.synapticPathwaysTable.isAutoResizeColumns = True
        self.synapticPathwaysTable.setToolTip("Configured Synaptic Pathways")
        self.synapticPathwaysTable.setValue(self._pathways_)
        self.synapticPathwaysTable.autoResizeColumns()

        self.synapticPathwaysTable.sig_indexRowColChanged.connect(self._slot_singleSynapticPathwayChanged)#, type=QtCore.Qt.DirectConnection)
        self.synapticPathwaysTable.sig_indexChanged.connect(self._slot_singleSynapticPathwayChanged)#, type=QtCore.Qt.DirectConnection)
        self.synapticPathwaysTable.sig_dataChanged.connect(self._slot_synapticPathwaysListChanged)

        self.createTwoPathwaysSourcePushButton.clicked.connect(self._slot_makeTwoPathwaysSource)

    @Slot(int)
    def _slot_adcChanged(self, val: int):
        self._adc_ = val
        if not isinstance(self._data_, self._objectType_):
            self._make_value_()
        else:
            self._data_.adc = self._adc_
            for pathway in self._data_pathways:
                pathway.adc = self._data_adc

        self.sig_valueChanged.emit(self.value())

    @Slot(int)
    def _slot_dacChanged(self, val: int):
        self._dac_ = val
        if not isinstance(self._data_, self._objectType_):
            self._make_value_()
        else:
            self._data_.dac = self._dac_
            for pathway in self._data_.pathways:
                pathway.dac = self._data_.dac

        self.sig_valueChanged.emit(self.value())

    @Slot(str)
    @Slot(int)
    def _slot_electrodeModeChanged(self, val: int | str):
        if isinstance(val, int) and val >=0 and val < len(self._electrodeModeNames_):
            val = self._electrodeModeNames_[val]

        if isinstance(val, str):
            if val in self._electrodeModeNames_:
                self._electrode_ = ephys.ElectrodeMode[val]
                if not isinstance(self._data_, self._objectType_):
                    self._make_value_()
                else:
                    self._data_.electrodeMode = self._electrode_
                    # NOTE: 2026-06-20 23:09:17 TODO
                    # delegate this to ephys_pathways.RecordingSource!
                    for pathway in self._data_.pathways:
                        pathway.electrodeMode = self._data_.electrodeMode

                self.sig_valueChanged.emit(self.value())
            else:
                return
        else:
            return

        if not isinstance(self._data_, self._objectType_):
            for pathway in self._pathways_:
                pathway.electrodeMode = self._data_.electrodeMode
            self._make_value_()
        else:
            self._data_.electrodeMode = self._electrode_
            for pathway in self._data_.pathways:
                pathway.electrodeMode = self._data_.electrodeMode

            self._pathways_ = self._data_.pathways
            sigBlock = QtCore.QSignalBlocker(self.synapticPathwaysTable) # noqa
            self.synapticPathwaysTable.setValue(self._data_.pathways)
            self.synapticPathwaysTable.autoResizeColumns()

        self.sig_valueChanged.emit(self.value())

    @Slot()
    def _slot_new(self):
        self._make_value_()
        self.sig_valueChanged.emit(self.value())

    def _make_value_(self):
        self._data_ = self._objectType_(name=self._name_, adc=self._adc_,
                                            dac=self._dac_, syn=self._syn_,
                                            auxin=self._auxin_,
                                            auxout=self._auxout_,
                                            electrodeMode = self._electrode_)

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
        editor.sig_valueChanged.connect(self._slot_auxInChanged)
        editor.slot_Launch()

    @Slot()
    def _slot_editAuxOut(self):
        from gui.delegates import ExternalEditorDelegate
        editor = ExternalEditorDelegate(self._auxout_, self)
        editor.setObjectName("auxOutEditor")
        editor.sig_valueChanged.connect(self._slot_auxOutChanged)
        editor.slot_Launch()

    @Slot(int, int)
    @Slot(QtCore.QModelIndex)
    def _slot_singleSynapticPathwayChanged(self, row: int | QtCore.QModelIndex,
                                           col: int | None = None):
        # print(f"{self.__class__.__name__}._slot_singleSynapticPathwayChanged({row}, {col})")
        if all(isinstance(v, int) for v in (row, col)):
            self._pendingPathwayChange_ = (row, col)
        else:
            self._pendingPathwayChange_ = row

    @Slot()
    def _slot_synapticPathwaysListChanged(self):
        # print(f"{self.__class__.__name__}._slot_synapticPathwaysListChanged")
        with qtutils.SignalBlocker((
                        self.stimulusListTable,
                        self.synapticPathwaysTable,
                        self.electrodeModeComboBox
                    )):
            widget = self.sender()
            if widget == self.synapticPathwaysTable:
                pathways = widget.value()
                if isinstance(pathways, ephys_pathways.SynapticPathwayList):
                    if len(pathways) == len(self._data_.pathways):
                        lastChangedPathwayNdx = None
                        changedAttrNdx = None
                        if isinstance(self._pendingPathwayChange_, tuple) and len(self._pendingPathwayChange_) == 2:
                            lastChangedPathwayNdx = self._pendingPathwayChange_[0]
                            changedAttrNdx = self._pendingPathwayChange_[1]
                            self._pendingPathwayChange_ = None

                        elif isinstance(self._pendingPathwayChange_, QtCore.QModelIndex):
                            lastChangedPathwayNdx = self._pendingPathwayChange_.row()
                            changedAttrNdx = self._pendingPathwayChange_.column()
                            self._pendingPathwayChange_ = None

                        if all(isinstance(v, int) for v in (lastChangedPathwayNdx, changedAttrNdx)):
                            if __has_PySide6__:
                                changedAttrName = widget.tableView.model().headerData(changedAttrNdx, QtCore.Qt.Horizontal)
                            else:
                                changedAttrName = widget.tableView.model().headerData(changedAttrNdx, QtCore.Qt.Horizontal).value()

                            if changedAttrName == "electrodeMode":
                                eMode = pathways[lastChangedPathwayNdx].electrodeMode
                                # print(f"\n\teMode -> {eMode}")
                                for p in pathways:
                                    if p.electrodeMode != eMode:
                                        p.electrodeMode = eMode

                                self._electrode_ = eMode
                                self._data_.electrodeMode = self._electrode_

                                currentElectrodeModeNdx = self._electrodeModeNames_.index(eMode.name)

                                self.electrodeModeComboBox.setCurrentIndex(currentElectrodeModeNdx)
                                self.synapticPathwaysTable.setValue(pathways) # to reflect ALL pathway changes
                                self.synapticPathwaysTable.autoResizeColumns()

                            # NOTE: 2026-08-31 09:53:35
                            # self._data_.syn does NOT update automatically!
                            self._data_.syn = ephys_pathways.SynapticStimulusChannelList(list(map(lambda p: p.stimulus, pathways)))
                            self._syn_ = self._data_.syn
                            self.stimulusListTable.setValue(self._data_.syn)
                            self.stimulusListTable.autoResizeColumns()

                    else:
                        # synchronise the stimulus list
                        for p in pathways:
                            if p.electrodeMode != self._electrode_:
                                p.electrodeMode = self._electrode_
                        newSyn = ephys_pathways.SynapticStimulusChannelList(list(map(lambda p: p.stimulus, pathways)))
                        self._data_.syn = newSyn
                        self._syn_ = self._data_.syn
                        self._pathways_ = pathways
                        self._data_.pathways = pathways
                        # blockers = list(map(lambda w: QtCore.QSignalBlocker(w), (self.stimulusListTable, self.synapticPathwaysTable)))
                        # to reflect changes in electrodeMode:
                        self.synapticPathwaysTable.setValue(self._data_.pathways)
                        self.synapticPathwaysTable.autoResizeColumns()
                        # to reflect changes in stimulus (when edited)
                        self.stimulusListTable.setValue(self._data_.syn)
                        self.stimulusListTable.autoResizeColumns()

                self.sig_valueChanged.emit(self._data_)

    @Slot(int, int)
    @Slot(QtCore.QModelIndex)
    def _slot_singleStimulusChannelChanged(self, row: int | QtCore.QModelIndex,
                                           col: int | None = None
                                           ):
        # print(f"{self.__class__.__name__}._slot_singleStimulusChannelChanged({row}, {col})")
        if all(isinstance(v, int) for v in (row, col)):
            self._pendingStimulusChange_ = (row, col)
        else:
            self._pendingStimulusChange_ = row

    @Slot(QtCore.QModelIndex, QtCore.QModelIndex)
    def _slot_stimulusListIndexesChanged(self, topLeft, bottomRight):
        if topLeft.row() == bottomRight.row():
            row = topLeft.row()
            self._data_.syn[row] = self.stimulusListTable.value()[row]
            self._syn_ = self._data_.syn
        self.sig_valueChanged.emit(self.value())

    @Slot(QtCore.QModelIndex, QtCore.QModelIndex)
    def _slot_pathwaysListIndexesChanged(self, topLeft, bottomRight):
        # print(f"{self.__class__.__name__}._slot_pathwaysListIndexesChanged")
        if topLeft.row() == bottomRight.row():
            row = topLeft.row()
            pathway = self.synapticPathwaysTable.value()[row]
            eMode = pathway.electrodeMode
            self._data_.pathways[row] = pathway
            for p in self._data_.pathways:
                p.electrodeMode = eMode
            self._electrode_ = eMode
            self._pathways_ = self._data_.pathways
            self._data_.syn = ephys_pathways.SynapticStimulusChannelList(list(map(lambda p: p.stimulus, self._data_.pathways)))
            self._syn_ = self._data_.syn

            currentElectrodeModeNdx = self._electrodeModeNames_.index(eMode.name)

            with qtutils.SignalBlocker((self.electrodeModeComboBox,
                                        self.synapticPathwaysTable,
                                        self.stimulusListTable)):
                self.electrodeModeComboBox.setCurrentIndex(currentElectrodeModeNdx)

                self.synapticPathwaysTable.setValue(self._data_.pathways) # to reflect ALL pathway changes
                self.synapticPathwaysTable.autoResizeColumns()

                self.stimulusListTable.setValue(self._data_.syn) # to reflect ALL stimulus changes
                self.stimulusListTable.autoResizeColumns()

            self.sig_valueChanged.emit(self.value())

    @Slot()
    def _slot_stimulusListChanged(self):
        # print(f"\n***\n\n{self.__class__.__name__}._slot_stimulusListChanged()")
        # print(f"\n\tdata.syn -> {len(self._data_.syn)};\n\tdata.pathways -> {len(self._data_.pathways)}")
        widget = self.sender()
        if widget == self.stimulusListTable:
            syn = widget.value()
            # looks like these need to be "called" - no-ops but otherwise somehow
            # the code still thinks there are fewer pathways
            # syn
            # self._data_.syn
            # self._data_.pathways
            # print(f"\n\tsyn -> {len(syn)};")
            if not isinstance(syn, ephys_pathways.SynapticStimulusChannelList):
                return

            if not isinstance(self._data_, self._objectType_):
                # print("\n\twill create new RecordingSource")
                self._syn_ = syn
                self._make_value_()

            else:
                # self._data_.syn = self._syn_
                # print(f"\n\tpendingStimChange: {self._pendingStimulusChange_}")
                if len(self._data_.pathways) == 0:
                    # print("\n\tadding new pathways")
                    self._data_.syn = syn
                    for stim in self._data_.syn:
                        pathway = ephys_pathways.SynapticPathway(stimulus = stim,
                                                                 name = f"{stim.name}_pathway",
                                                                 adc= self._data_.adc,
                                                                 dac = self._data_.dac,
                                                                 electrode = self._data_.electrodeMode
                                                                )
                        self._data_.pathways.append(pathway)

                else:
                    # print(f"syn has {len(syn)}; data.pathways has {len(self._data_.pathways)}")
                    if len(syn) < len(self._data_.pathways):
                        retainedPathways = ephys_pathways.SynapticPathwayList(list(filter(lambda p: p.stimulus in syn, self._data_.pathways)))
                        # print(f"\n\tretainedPathways -> {retainedPathways}")
                        self._data_.pathways = retainedPathways
                        # print(f"\n\tdata.pathways -> {self._data_.pathways}")
                        self._data_.syn = syn


                    elif len(syn) == len(self._data_.pathways):
                        if isinstance(self._pendingStimulusChange_, tuple) and len(self._pendingStimulusChange_) == 2:
                            stimNdx = self._pendingStimulusChange_[0]
                            # print(f"\n\tstimulus at {stimNdx} changed")
                            if stimNdx < len(self._data_.syn):
                                editedStim = syn[stimNdx]
                                # col = self._pendingStimulusChange_[1]
                                currentStim = self._data_.syn[stimNdx]
                                pp = list(filter(lambda p: p.stimulus == currentStim, self._data_.pathways))
                                if len(pp):
                                    for p in pp:
                                        p.stimulus = editedStim
                                self._data_.syn[stimNdx] = editedStim
                            self._pendingStimulusChange_ = None

                    elif len(syn) > len(self._data_.pathways):
                        for k in range(len(self._data_.pathways), len(syn)):
                            pathway = ephys_pathways.SynapticPathway(stimulus = syn[k],
                                                                    name = f"{syn[k].name}_pathway",
                                                                    adc= self._data_.adc,
                                                                    dac = self._data_.dac,
                                                                    electrode = self._data_.electrodeMode
                                                                    )
                            self._data_.pathways.append(pathway)

                self._syn_ = self._data_.syn
                self._pathways_ = self._data_.pathways

            with qtutils.SignalBlocker(self.synapticPathwaysTable):
                self.synapticPathwaysTable.setValue(self._data_.pathways)
                self.synapticPathwaysTable.autoResizeColumns()

            self.sig_valueChanged.emit(self._data_)

    @Slot(object)
    def _slot_auxInChanged(self, val: typing.Optional[ephys_pathways.AuxiliaryInputList] = None):
        if isinstance(val, ephys_pathways.AuxiliaryInputList):
            self._auxin_ = val
        else:
            self._auxin_ = ephys_pathways.AuxiliaryInputList()

        if not isinstance(self._data_, self._objectType_):
            self._make_value_()
        else:
            self._data_.auxin = self._auxin_

        self.sig_valueChanged.emit(self._data_)

    @Slot(object)
    def _slot_auxOutChanged(self, val: typing.Optional[ephys_pathways.AuxiliaryOutputList] = None):
        if isinstance(val, ephys_pathways.AuxiliaryOutputList):
            self._auxout_ = val
        else:
            self._auxout_ = ephys_pathways.AuxiliaryOutputList()

        if not isinstance(self._data_, self._objectType_):
            self._make_value_()
        else:
            self._data_.auxout = self._auxout_

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

        result = ephys_pathways.twoPathwaysSource(self._adc_, self._dac_,
                                                 path0stim=path0stim,
                                                 path1stim=path1stim,
                                                 name=self._name_,
                                                 electrodeMode = self._electrode_)
        self.setValue(result)
        self.sig_valueChanged.emit(self._data_)

    def setValue(self, val: T | None = None):
        # print(f"{self.__class__.__name__}.setValue({val}) <{type(val).__name__}>")
        if isinstance(val, self._objectType_):
            self._data_ = val
            self._name_ = self._data_.name
            self._adc_ = self._data_.adc
            self._dac_ = self._data_.dac
            self._syn_ = self._data_.syn
            self._auxin_ = self._data_.auxin
            self._auxout_ = self._data_.auxout
            self._electrode_ = self._data_.electrodeMode
            self._pathways_ = self._data_.pathways

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
            currentElectrodeModeNdx = self._electrodeModeNames_.index(self._electrode_.name)
            self.electrodeModeComboBox.setCurrentIndex(currentElectrodeModeNdx)

        self.stimulusListTable.setValue(self._data_.syn)
        self.stimulusListTable.autoResizeColumns()

        self.synapticPathwaysTable.setValue(self._data_.pathways)
        self.synapticPathwaysTable.autoResizeColumns()

    def value(self) -> T:
        return self._data_

