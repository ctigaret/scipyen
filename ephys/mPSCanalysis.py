import os, typing
from numbers import (Number, Real,)
from itertools import chain

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType

import numpy as np
import quantities as pq
import neo
import pyqtgraph as pg

import core.neoutils as neoutils
import core.workspacefunctions as wf
import core.signalprocessing as sigp
import core.curvefitting as crvf
import core.models as models

from core.quantities import (arbitrary_unit, check_time_units, units_convertible,
                            unit_quantity_from_name_or_symbol,quantity2str,)
from core.datatypes import UnitTypes
from core.strutils import numbers2str
from core.ephys import membrane

import ephys.ephys as ephys

from core.prog import safeWrapper

from gui import quickdialog as qd
import gui.signalviewer as sv
from gui.signalviewer import SignalCursor as SignalCursor
import gui.pictgui as pgui
from gui.workspacegui import GuiMessages

import iolib.pictio as pio

__module_path__ = os.path.abspath(os.path.dirname(__file__))

class MPSCAnalysis(qd.QuickDialog, GuiMessages):
    """Mini-PSC analysis window ("app")
    Most of the GUI logic as in triggerdetectgui.TriggerDetectDialog
    """
    def __init__(self, ephysdata=None, title:str="mPSC Detect", clearEvents=False, parent=None, ephysViewer=None, **kwargs):
        self._dialog_title_ = title if len(title.strip()) else "mPSC Detect"
        super().__init__(parent=parent, title=self._dialog_title_)
        
        self._clear_events_flag_ = clearEvents
        
        self._mPSC_detected_ = False
        
        self._currentFrame_ = 0
        
        # NOTE: 2022-10-28 10:33:57
        # When not empty, this list must have as many elements as there are 
        # segments in self._ephys_.
        # Each element is either None (if no previous mPSC detection in that segment)
        # or a SpikeTrain with mPSC detection.
        #
        # A SpikeTrain with mPSC detection is identified by its annotations
        # containing a key "source" mapped to the str value "mPSC_detection"
        # (see membrane.batch_mPSC)
        self._cached_detection_ = list()
        
        self._ephys_= None
        
        self._template_ = None
        
        # TODO: 2022-10-28 11:47:43
        # save/restore parameters , lower & upper in user_config, under model name
        # needs modelfitting.py done & dusted
        self._model_initial_parameters_ = list()
        self._model_lower_bounds_ = list()
        self._model_upper_bounds_ = list()
        
        if not isinstance(ephysViewer, sv.SignalViewer):
            self._ephysViewer_ = sv.SignalViewer(win_title=self._dialog_title_)
            self._owns_viewer_ = True
            
        else:
            self._ephysViewer_ = ephysViewer
            self._owns_viewer_ = False
            
        self._ephysViewer_.frameChanged[int].connect(self._slot_ephysFrameChanged)
        
        self.clearDetectionCheckBox = qd.CheckBox(self, "Clear previous detection")
        self.clearDetectionCheckBox.setIcon(QtGui.QIcon.fromTheme("edit-clear-history"))
        self.clearDetectionCheckBox.stateChanged.connect(self._slot_clearDetectionChanged)
        
        self.detectmPSCPushButton = QtWidgets.QPushButton(QtGui.QIcon.fromTheme("edit-find"),
                                                          "Detect", parent=self.buttons)
        self.detectmPSCPushButton.clicked.connect(self.slot_detect)
        
        self.undoDetectionPushButton = QtWidgets.QPushButton(QtGui.QIcon.fromTheme("edit-undo"),
                                                             "Undo", parent=self.buttons)
        
        self.undoDetectionPushButton.clicked.connect(self.slot_undo)
        
        self.detectmPSCInFramePushButton = QtWidgets.QPushButton(QtGui.QIcon.fromTheme("edit-find"),
                                                                 "Detect in frame", parent=self.buttons)
        
        self.detectmPSCInFramePushButton.clicked.conenct(self.slot_detect_in_frame)
        
        self.undoFramePushButton = QtWidgets.QPushButton(QtGui.QIcon.fromTheme("edit-undo"),
                                                         "Undo Frame", parent = self.buttons)
        
        self.undoFramePushButton.clicked.connect(self.slot_undo_frame)
        
        self.modelParametersPushButton = QtWidgets.QPushButton(QtGui.QIcon.fromTheme("configure"),
                                                               "Model Parameters", parent=self.buttons)
        
        self.modelParametersPushButton.clicked.connect(self.slot_edit_parameters)
        
        for k, button in enumerate(self.modelParametersPushButton,
                                   self.clearEventsCheckBox,
                                   self.detectTriggersPushButton,
                                   self.undoTriggersPushButton,
                                   self.detectmPSCInFramePushButton,
                                   self.undoFramePushButton):
            self.buttons.layout.insertWidget(k, button)

        # self.buttons.layout.insertWidget(0, self.modelParametersPushButton)
        # self.buttons.layout.insertWidget(1, self.clearEventsCheckBox)
        # self.buttons.layout.insertWidget(2, self.detectTriggersPushButton)
        # self.buttons.layout.insertWidget(3, self.undoTriggersPushButton)
        # self.buttons.layout.insertWidget(4, self.detectmPSCInFramePushButton)
        # self.buttons.layout.insertWidget(5, self.undoFramePushButton)
        self.buttons.layout.insertStretch(3)
        
        self.buttons.OK.setIcon(QtGui.QIcon.fromTheme("dialog-ok-apply"))
        self.buttons.Cancel.setIcon(QtGui.QIcon.fromTheme("dialog-cancel"))
        
        self.statusBar = QtWidgets.QStatusBar(parent=self)
        self.addWidget(self.statusBar)
        
        self.setWindowModality(QtCore.Qt.NonModal)
        
        # parse ephysdata parameter
        self._set_ephys_data_(ephysdata)
        self.setSizeGripEnabled(True)
        
        
    def _set_ephys_data_(self, value):
        if neoutils.check_ephys_data_collection(value, mix=False):
            self._cached_detection_ = list()
            
            if isinstance(value, neo.Block):
                for s in value.segments:
                    if len(s.spiketrains):
                        trains = [st in s.spiketrains if st.annotations.get("source", None)=="mPSC_detection"]
                        if len(trains):
                            self._cached_detection_.append(trains[0])
                        else:
                            self._cached_detection_.append(None)
                            
                self._ephys_ = value
                            
            elif isinstance(value, neo.Segment):
                if len(value.spiketrains):
                    trains = [st in value.spiketrains if st.annotations.get("source", None)=="mPSC_detection"]
                    if len(trains):
                        self._cached_detection_.append(trains[0])
                    else:
                        self._cached_detection_.append(None)
                            
                self._ephys_ = value
                
            elif isinstance(value, (tuple, list)) and all(isinstance(v, neo.Segment) for v in value):
                for s in value.segments:
                    if len(s.spiketrains):
                        trains = [st in s.spiketrains if st.annotations.get("source", None)=="mPSC_detection"]
                        if len(trains):
                            self._cached_detection_.append(trains[0])
                        else:
                            self._cached_detection_.append(None)
                            
                self._ephys_ = value
                            
            else:
                self.errorMessage(self._dialog_title_, f"Expecting a neo.Block, neo.Segment, or a sequence of neo.Segment objects; got {type(value).__name__} instead")
                return
            
        else:
            self.errorMessage(self._dialog_title_, f"Expecting a neo.Block, neo.Segment, or a sequence of neo.Segment objects; got {type(value).__name__} instead")
            return
                
    def open(self):
        if self._ephys_:
            self._ephysViewer_.plot(self.ephysdata)
            self._currentFrame_ = self._ephysViewer_.currentFrame
            
        super().open()
        
    def exec(self):
        if self._ephys_:
            self._ephysViewer_.plot(self.ephysdata)
            self._currentFrame_ = self._ephysViewer_.currentFrame
            
        return super().exec()
    
    def closeEvent(self, evt):
        if self._ephysViewer_.isVisible():
            if self._owns_viewer_:
                self._ephysViewer_.close()
            else:
                self._ephysViewer_.refresh()
                
        super().closeEvent(evt)
        
    @pyqtSlot()
    def accept(self):
        super().accept()
        
    @pyqtSlot()
    def reject(self):
        super().reject()
        
    @pyqtSlot(int)
    def done(self, value):
        """Not sure about the utility of this one, here..."""
        if self._ephysViewer_.isVisible():
            if self._owns_viewer_:
                self._ephysViewer_.close()
            
            else:
                self._ephysViewer_.refresh()
                
        super().done(value)
        
    @pyqtSlot()
    def _slot_clearDetectionChanged(self):
        self._clear_events_flag_ = self.clearDetectionCheckBox.selection()
        
    @pyqtSlot(int)
    def _slot_ephysFrameChanged(self, value):
        """"""
        self._currentFrame_ = value
        
    @pyqtSlot()
    def slot_detect(self):
        if self._ephys_ is None:
            return
        
        self.detect_mPSCs()
        
        if self.isVisible():
            if self._ephysViewer_.isVisible() and  self._ephysViewer_.y:
                self._ephysViewer_.refresh()
            else:
                self._ephysViewer_.plot(self.ephysdata)
                
    @pystSlot()
    def slot_detect_in_frame(self):
        if self._ephys_ is None:
            return
        
        self.detect_mPSC_inFrame()
        
        if self.isVisible():
            if self._ephysViewer_.isVisible() and  self._ephysViewer_.y:
                self._ephysViewer_.refresh()
            else:
                self._ephysViewer_.plot(self.ephysdata)
                
                
    @pyqtSlot()
    def slot_undo(self):
        """Quickly restore the events - no fancy stuff
        """
        self._restore_()
        if self.isVisible():
            if self._ephysViewer_.isVisible() and self._ephysViewer_.y:
                self._ephysViewer_.refresh()
            else:
                self._ephysViewer_.plot(self._ehys_)
                
        self.detected = False
        
    @pyqtSlot()
    def slot_undo_frame(self):
        self._restore_frame()
        if self.isVisible():
            if self._ephysViewer_.isVisible() and self._ephysViewer_.y:
                self._ephysViewer_.refresh()
            else:
                self._ephysViewer_.plot(self._ehys_)
                
    @pyqtSlot()
    def slot_edit_parameters(self):
        dlg = qd.QuickDialog(self, title="mPSC parameters")
        # α, β, x₀, τ₁ and τ₂ AND WAVEFORM_DURATION !!! 
        
                
    @property
    def currentFrame(self):
        return self._currentFrame_
    
    @currentFrame.setter
    def currentFrame(self, value:int):
        self._currentFrame_ = value
                
    @property
    def detected(self):
        return self._mPSC_detected_
    
    @detected.setter
    def detected(self, value):
        self._mPSC_detected_ = value
        # NOTE: 2022-10-28 10:48:10
        # alloe rerun detection
        # self.detectmPSCPushButton.setEnabled(not self._mPSC_detected_)
        
    @property
    def ephysdata(self):
        return self._ephys_
    
    @ephysdata.setter
    def ephysdata(self, value):
        self._set_ephys_data_(value)
            
    def detect_mPSCs_inFrame(self):
        if self._ephys_ is None:
            self.detected = False
            return
        
    def detect_mPSC(self):
        if self._ephys_ is None:
            self.detected = False
            return
        
        
    def _restore_(self): # TODO/FIXME 2022-10-28 10:49:30
        if len(self._cached_events_):
            if isinstance(self._ephys_, Block):
                for k, s in enumerate(self._ephys_.segments):
                    s.events[:] = self._cached_events_[k][:]
                    
            elif isinstance(self._ephys_, Segment):
                self._ephys_.events[:] = self._cached_events_[0][:]
                
            elif isinstance(self._ephys_, (tuple, list)):
                if all([isinstance(v, Block) for v in self._ephys_]):
                    for k, b in enumerate(self._ephys_):
                        for ks, s in enumerate(b.segments):
                            s.events[:] = self._cached_events_[k][ks][:]
                            
                elif all([isinstance(v, Segment) for v in self._ephys_]):
                    for k, s in enumerate(self._ephys_):
                        s.events[:] = self._cached_events_[k][:]
                        
    def _restore_frame_(self): # TODO 2022-10-28 11:13:37
        pass
