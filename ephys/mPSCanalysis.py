import os, typing, math
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
from core.scipyen_config import markConfigurable

from core.quantities import (arbitrary_unit, check_time_units, units_convertible,
                            unit_quantity_from_name_or_symbol, quantity2str,)
from core.datatypes import UnitTypes
from core.strutils import numbers2str
from ephys import membrane

import ephys.ephys as ephys

from core.prog import safeWrapper

from gui import quickdialog as qd
import gui.signalviewer as sv
from gui.signalviewer import SignalCursor as SignalCursor
import gui.pictgui as pgui
from gui.workspacegui import (GuiMessages, WorkspaceGuiMixin)
from gui.modelfittingui import ModelParametersWidget

import iolib.pictio as pio

__module_path__ = os.path.abspath(os.path.dirname(__file__))

class MPSCAnalysis(qd.QuickDialog, WorkspaceGuiMixin):
    """Mini-PSC analysis window ("app")
    Most of the GUI logic as in triggerdetectgui.TriggerDetectDialog
    """
    
    # NOTE: 2022-10-31 14:59:15
    # Fall-back defaults for mPSC parameters.
    #
    _default_model_units_  = pq.pA
    _default_time_units_   = pq.s
    
    _default_params_names_ = ("α", "β", "x₀", "τ₁", "τ₂")
    
    _default_params_initl_ = (0.*_default_model_units_, 
                              -1.*pq.dimensionless, 
                              0.01*_default_time_units_, 
                              0.001*_default_time_units_, 
                              0.01*_default_time_units_)
    
    _default_params_lower_ = (0.*_default_model_units_, 
                              -math.inf*pq.dimensionless, 
                              0.*_default_time_units_, 
                              1.0e-4*_default_time_units_, 
                              1.0e-4*_default_time_units_)
    _default_params_upper_ = (math.inf*_default_model_units_, 
                              0.*pq.dimensionless,  
                              math.inf*_default_time_units_,
                              0.01*_default_time_units_, 
                              0.01*_default_time_units_)
    
    _default_duration_ = 0.02*_default_time_units_
    
    def __init__(self, ephysdata=None, title:str="mPSC Detect", clearOldPSCs=False, parent=None, ephysViewer=None, **kwargs):
        self._dialog_title_ = title if len(title.strip()) else "mPSC Detect"
        super().__init__(parent=parent, title=self._dialog_title_)
        
        self._clear_events_flag_ = clearOldPSCs == True
        
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
        
        self._params_names_ = self._default_params_names_
        self._params_initl_ = self._default_params_initl_
        self._params_lower_ = self._default_params_lower_
        self._params_upper_ = self._default_params_upper_
        self._mPSCduration_ = self._default_duration_
        
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
        
        self.detectmPSCInFramePushButton.clicked.connect(self.slot_detect_in_frame)
        
        self.undoFramePushButton = QtWidgets.QPushButton(QtGui.QIcon.fromTheme("edit-undo"),
                                                         "Undo Frame", parent = self.buttons)
        
        self.undoFramePushButton.clicked.connect(self.slot_undo_frame)
        
        self.modelParametersPushButton = QtWidgets.QPushButton(QtGui.QIcon.fromTheme("configure"),
                                                               "Model Parameters", parent=self.buttons)
        
        self.modelParametersPushButton.clicked.connect(self.slot_edit_mPSCparameters)
        
        for k, button in enumerate((self.modelParametersPushButton,
                                   self.clearDetectionCheckBox,
                                   self.detectmPSCPushButton,
                                   self.undoDetectionPushButton,
                                   self.detectmPSCInFramePushButton,
                                   self.undoFramePushButton)):
            self.buttons.layout.insertWidget(k, button)

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
                        trains = [st for st in s.spiketrains if st.annotations.get("source", None)=="mPSC_detection"]
                        if len(trains):
                            self._cached_detection_.append(trains[0])
                        else:
                            self._cached_detection_.append(None)
                            
                self._ephys_ = value
                            
            elif isinstance(value, neo.Segment):
                if len(value.spiketrains):
                    trains = [st for st in value.spiketrains if st.annotations.get("source", None)=="mPSC_detection"]
                    if len(trains):
                        self._cached_detection_.append(trains[0])
                    else:
                        self._cached_detection_.append(None)
                            
                self._ephys_ = value
                
            elif isinstance(value, (tuple, list)) and all(isinstance(v, neo.Segment) for v in value):
                for s in value.segments:
                    if len(s.spiketrains):
                        trains = [st for st in s.spiketrains if st.annotations.get("source", None)=="mPSC_detection"]
                        if len(trains):
                            self._cached_detection_.append(trains[0])
                        else:
                            self._cached_detection_.append(None)
                            
                self._ephys_ = value
                            
            else:
                self.errorMessage(self._dialog_title_, f"Expecting a neo.Block, neo.Segment, or a sequence of neo.Segment objects; got {type(value).__name__} instead")
                return
            
        elif value is None:
            self._cached_detection_.clear()
            self._ephysViewer_.clear()
            self._ephysViewer_.setVisible(False)
            return
            
        else:
            self.errorMessage(self._dialog_title_, f"Expecting a neo.Block, neo.Segment, or a sequence of neo.Segment objects, or None; got {type(value).__name__} instead")
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
        if value == QtWidgets.QDialog.Accepted and not self.detected:
            self.detect_mPSC()
            
        if self._ephysViewer_.isVisible():
            if self._owns_viewer_:
                self._ephysViewer_.close()
            
            else:
                self._ephysViewer_.refresh()
                
        super().done(value)
        
    @pyqtSlot()
    def _slot_clearDetectionChanged(self):
        self.clearOldPSCs = self.clearDetectionCheckBox.selection()
        
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
                
    @pyqtSlot()
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
    def slot_edit_mPSCparameters(self):
        # α, β, x₀, τ₁ and τ₂ AND WAVEFORM_DURATION !!! 
        dlg = qd.QuickDialog(self, title="mPSC parameters")
        orientation = "vertical"
        paramsWidget = ModelParametersWidget(self.mPSCParametersInitial, 
                                             parameterNames = self.mPSCParametersNames,
                                             lower = self.mPSCParametersLowerBounds,
                                             upper = self.mPSCParametersUpperBounds,
                                             orientation=orientation, parent=dlg)
        
        vgroup = qd.VDialogGroup(dlg, validate=False)
        dgroup = qd.HDialogGroup(dlg, validate=False)

        w = QtWidgets.QLabel("Duration:", dgroup)
        dgroup.addWidget(w, alignment = QtCore.Qt.Alignment())
        wd = QtWidgets.QDoubleSpinBox(dgroup)
        wd.setMinimum(-math.inf)
        wd.setMaximum(math.inf)
        wd.setDecimals(paramsWidget.spinDecimals)
        wd.setSingleStep(paramsWidget.spinStep)
        wd.setValue(self.mPSCDuration.magnitude)
        dgroup.addWidget(wd, alignment=QtCore.Qt.Alignment())
        dgroup.addStretch(20)
        vgroup.addWidget(dgroup)
        dlg.addWidget(vgroup, alginment=QtCore.Qt.AlignTop)
        dlg.resize(-1,-1)
        
        dlg_result = dlg.exec()
        
        if dlg_result == QtWidgets.QDialog.Accepted:
            self.mPSCParametersInitial = paramsWidget.parameters["Initial Value:"]
            self.mPSCParametersLowerBounds = paramsWidget.parameters["Lower Bound:"]
            self.mPSCParametersUpperBounds = paramsWidget.parameters["Upper Bound:"]
            self.mPSCDuration = wd.value() * self._default_time_units_
                
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
        
    @property
    def clearOldPSCs(self):
        return self._clear_events_flag_
    
    @markConfigurable("ClearOldPSCsOnDetection")
    @clearOldPSCs.setter
    def clearOldPSCs(self, val):
        self._clear_events_flag_ = val == True
        if isinstance(getattr(self, "configurable_traits", None), DataBag):
            self.configurable_traits["ClearOldPSCsOnDetection"] = self._clear_events_flag_
            
    @property
    def mPSCParametersNames(self):
        return self._params_names_
    
    @markConfigurable("mPSCParametersNames")
    @mPSCParametersNames.setter
    def mPSCParametersNames(self, val):
        if isinstance(val, (tuple, list)) and all(isinstance(s, str) for s in val):
            self._params_names_ = val

            if isinstance(getattr(self, "configurable_traits", None), DataBag):
                self.configurable_traits["mPSCParametersNames"] = self._params_names_
            
    @property
    def mPSCParametersInitial(self):
        return self._params_initl_
    
    @markConfigurable("mPSCParametersInitial")
    @mPSCParametersInitial.setter
    def mPSCParametersInitial(self, val):
        if isinstance(val, (tuple, list)) and all(isinstance(s, str) for s in val):
            self._params_initl_ = val

            if isinstance(getattr(self, "configurable_traits", None), DataBag):
                self.configurable_traits["mPSCParametersInitial"] = self._params_initl_
                
    @property
    def mPSCParametersLowerBounds(self):
        return self._params_lower_
    
    @markConfigurable("mPSCParametersLowerBounds")
    @mPSCParametersLowerBounds.setter
    def mPSCParametersLowerBounds(self, val):
        if isinstance(val, (tuple, list)) and all(isinstance(s, str) for s in val):
            self._params_lower_ = val

            if isinstance(getattr(self, "configurable_traits", None), DataBag):
                self.configurable_traits["mPSCParametersLowerBounds"] = self._params_lower_
        else:
            raise TypeError("Expecting a sequence of scalar numbers for upper bounds")
                
                
    @property
    def mPSCParametersUpperBounds(self):
        return self._params_upper_
    
    @markConfigurable("mPSCParametersUpperBounds")
    @mPSCParametersUpperBounds.setter
    def mPSCParametersUpperBounds(self, val):
        if isinstance(val, (tuple, list)) and all(isinstance(s, Number) for s in val):
            self._params_upper_ = val
            
        elif val is None:
            self._params_upper_ = val

            if isinstance(getattr(self, "configurable_traits", None), DataBag):
                self.configurable_traits["mPSCParametersUpperBounds"] = self._params_upper_
                
        else:
            raise TypeError("Expecting a sequence of scalar numbers for upper bounds")
                
    @property
    def mPSCDuration(self):
        return self._mPSCduration_
    
    @markConfigurable("mPSCDuration")
    @mPSCDuration.setter
    def mPSCDuration(self, val):
        self._mPSCduration_ = val
        if isinstance(getattr(self, "configurable_traits", None), DataBag):
            self.configurable_traits["mPSCDuration"] = self._mPSCduration_
            
    def detect_mPSCs_inFrame(self):
        self.detected = False
        if self._ephys_ is None:
            return
        
    def detect_mPSC(self):
        if self._ephys_ is None:
            self.detected = False
            return
        
        
    def _restore_(self):
        if isinstance(self._ephys_, neo.Block):
            segments = self._ephys_.segments
        elif isinstance(self._ephys_, (tuple, list)) and all(isinstance(v, neo.Segment) for v in self._ephys_):
            segments = self._ephys_
        elif isinstance(self._ephys_, neo.Segment):
            segments = [self._ephys_]
        else:
            return
        
        if len(self._cached_detection_) == len(segments):
            for k, s in enumerate(segments):
                stt = [ks for ks,st in enumerate(s.spiketrains) if s.name.endswith("_PSC")]
                if len(stt):
                    neoutils.remove_spiketrain(s, stt)
                    
                if isinstance(self._cached_detection_[k], neo.SpikeTrain):
                    s.spiketrains.append(self._cached_detection_[k])
                    
            self.detected = False
                        
    def _restore_frame_(self):
        if isinstance(self._ephys_, neo.Block):
            segments = self._ephys_.segments
        elif isinstance(self._ephys_, (tuple, list)) and all(isinstance(v, neo.Segment) for v in self._ephys):
            segments = self._ephys_
        elif isinstance(self._ephys_, neo.Segment):
            segments = [self._ephys_]
        else:
            return
        
        if len(self._cached_detection_) == len(segments) and self._currentFrame_ in range(len(segments)):
            segment = segments[self._currentFrame_]
            stt = [k for k,st in enumerate(segment.spiketrains) if s.name.endswith("_PSCs")]
            if len(stt):
                neoutils.remove_spiketrain(segment, stt)

            if isinstance(self._cached_detection_[self._currentFrame_], neo.SpikeTrain):
                segment.spiketrains.append(self._cached_detection_[self._currentFrame_])
                
