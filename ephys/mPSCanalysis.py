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
import pandas as pd

import core.neoutils as neoutils
import core.workspacefunctions as wf
import core.signalprocessing as sigp
import core.curvefitting as crvf
import core.models as models
from core.traitcontainers import DataBag
from core.scipyen_config import (markConfigurable, get_config_file)

from core.quantities import (arbitrary_unit, check_time_units, units_convertible,
                            unit_quantity_from_name_or_symbol, str2quantity)

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
from gui.modelfitting_ui import ModelParametersWidget
from gui import guiutils

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
    
    _default_params_names_ = ["α", "β", "x₀", "τ₁", "τ₂"]
    
    _default_params_initl_ = [0.*_default_model_units_, 
                              -1.*pq.dimensionless, 
                              0.005*_default_time_units_, 
                              0.001*_default_time_units_, 
                              0.01*_default_time_units_]
    
    _default_params_lower_ = [0.*_default_model_units_, 
                              -math.inf*pq.dimensionless, 
                              0.*_default_time_units_, 
                              1.0e-4*_default_time_units_, 
                              1.0e-4*_default_time_units_]
    
    _default_params_upper_ = [math.inf*_default_model_units_, 
                              0.*pq.dimensionless,  
                              math.inf*_default_time_units_,
                              0.01*_default_time_units_, 
                              0.01*_default_time_units_]
    
    _default_duration_ = 0.02*_default_time_units_
    
    _default_template_file = os.path.join(os.path.dirname(get_config_file()),"mPSCTemplate.h5" )
    
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
        
        self._use_template_ = False
        
        self._model_waveform_ = None
        
        self._template_file_ = self._default_template_file
        
        
        # TODO: 2022-11-01 17:46:50
        # replace this with the one from ephysdata
        # this requires the following settings:
        # • ID or index of the signal whwere detection takes place
        # • name (or index) of the epoch (if any) where detection is being made
        self._waveform_sampling_rate = 1e4*pq.Hz # to be replaced with the one from data
        
        # TODO: 2022-10-28 11:47:43
        # save/restore parameters , lower & upper in user_config, under model name
        # needs modelfitting.py done & dusted
        
        # self._params_units_ = tuple(x.units.dimensionality for x in self._params_initl_)
        self.waveFormDisplay = sv.SignalViewer(win_title="mPSC waveform", parent=self)#.mainGroup)
        
        if not isinstance(ephysViewer, sv.SignalViewer):
            self._ephysViewer_ = sv.SignalViewer(win_title=self._dialog_title_)
            self._owns_viewer_ = True
            
        else:
            self._ephysViewer_ = ephysViewer
            self._owns_viewer_ = False
            
        self._ephysViewer_.frameChanged[int].connect(self._slot_ephysFrameChanged)
        
        # NOTE: 2022-11-03 22:55:52 
        #### BEGIN these shouldn't be allowed to change
        self._params_names_ = self._default_params_names_
        #### END these shouldn't be allowed to change
        
        self._params_initl_ = self._default_params_initl_
        self._params_lower_ = self._default_params_lower_
        self._params_upper_ = self._default_params_upper_
        self._mPSCduration_ = self._default_duration_
        
        self.loadSettings()
                
        # parse ephysdata parameter
        self._set_ephys_data_(ephysdata)
        
        self._configureUI_()
        
        self.resize(-1,-1)
        
        
    def _configureUI_(self):
        self.mainGroup = qd.VDialogGroup(self)
        
        self.paramsGroup = qd.VDialogGroup(self.mainGroup)
        self.paramsGroupBox = QtWidgets.QGroupBox("mPSC Model", self.paramsGroup)
        self.paramsGroupLayout = QtWidgets.QGridLayout(self.paramsGroupBox)
        
        self.paramsWidget = ModelParametersWidget(self._params_initl_, 
                                        parameterNames = self._params_names_,
                                        lower = self._params_lower_,
                                        upper = self._params_upper_,
                                        orientation="vertical", parent=self.paramsGroupBox)
        
        # NOTE: ModelParametersWidget is by design generic; however, for models 
        # where parameters cannot be zero (i.e., they are factors of denominators)
        # their corresponding spin boxes' minimum values must be constrained to
        # avoid 0; in particular for the mPSC model, both time constants MUST be
        # strictly positive; hence, setting the minimum spin box value to the 
        # value of the spinStep seems like a good idea
        
        self.paramsWidget.getSpinBox("τ₁", "Initial Value:").setMinimum(self.paramsWidget.spinStep)
        self.paramsWidget.getSpinBox("τ₁", "Lower Bound:").setMinimum(self.paramsWidget.spinStep)
        self.paramsWidget.getSpinBox("τ₁", "Upper Bound:").setMinimum(self.paramsWidget.spinStep)
        
        self.paramsWidget.getSpinBox("τ₂", "Initial Value:").setMinimum(self.paramsWidget.spinStep)
        self.paramsWidget.getSpinBox("τ₂", "Lower Bound:").setMinimum(self.paramsWidget.spinStep)
        self.paramsWidget.getSpinBox("τ₂", "Upper Bound:").setMinimum(self.paramsWidget.spinStep)
        
        self.paramsWidget.sig_parameterChanged[str, str].connect(self._slot_modelParameterChanged)
        
        self.paramsGroupLayout.addWidget(self.paramsWidget, 0, 0, 4, 4)
        
        self.durationLabel = QtWidgets.QLabel("Duration:", parent=self.paramsGroupBox)
        self.durationSpinBox = QtWidgets.QDoubleSpinBox(self.paramsGroupBox)
        self.durationSpinBox.setMinimum(-math.inf)
        self.durationSpinBox.setMaximum(math.inf)
        self.durationSpinBox.setDecimals(self.paramsWidget.spinDecimals)
        self.durationSpinBox.setSingleStep(self.paramsWidget.spinStep)
        self.durationSpinBox.setValue(self.mPSCDuration.magnitude)
        self.durationSpinBox.valueChanged.connect(self._slot_modelDurationChanged)
        if isinstance(self.mPSCDuration, pq.Quantity):
            self.durationSpinBox.setSuffix(f" {self.mPSCDuration.dimensionality}")
        else:
            self.durationSpinBox.setSuffix(" ")
            
        t = self.durationSpinBox.text()
        mWidth = guiutils.get_text_width(t)
        self.durationSpinBox.setMinimumWidth(mWidth + 3*mWidth//10)
        
        self.plotWaveFormButton = QtWidgets.QPushButton("Plot model")
        self.plotWaveFormButton.clicked.connect(self._slot_plot_model)
        
        self.paramsGroupLayout.addWidget(self.durationLabel,4, 0, 1, 1)
        self.paramsGroupLayout.addWidget(self.durationSpinBox,4, 1, 1, 2)
        self.paramsGroupLayout.addWidget(self.plotWaveFormButton, 4, 3, 1, 1)
        
        self.paramsGroup.addWidget(self.paramsGroupBox)
        
        self.mainGroup.addWidget(self.paramsGroup)

        self.templateGroup = qd.VDialogGroup(self)
        self.templateGroupBox = QtWidgets.QGroupBox("Use mPSC Template", self.templateGroup)
        self.templateGroupBox.setCheckable(True)
        self.templateGroupBox.setChecked(self._use_template_)
        self.templateGroupBox.clicked.connect(self._slot_useTemplateWaveForm)
        self.templateGroupBoxLayout = QtWidgets.QGridLayout(self.templateGroupBox)
        
        self.loadTemplatePushButton = QtWidgets.QPushButton(QtGui.QIcon.fromTheme("template"),
                                                  "Load...", 
                                                  parent = self.templateGroupBox)
        self.loadTemplatePushButton.setToolTip("Load a mPSC template from workspace")
        self.loadTemplatePushButton.setWhatsThis("Load a mPSC template from workspace")
        self.loadTemplatePushButton.setStatusTip("Load a mPSC template from workspace")
        self.loadTemplatePushButton.clicked.connect(self._slot_loadTemplate)
        
        self.loadTemplateFilePushButton = QtWidgets.QPushButton(QtGui.QIcon.fromTheme("document-new-from-template"),
                                                      "Open file...", 
                                                      parent = self.templateGroupBox)
        self.loadTemplateFilePushButton.setToolTip("Load a mPSC template from a file")
        self.loadTemplateFilePushButton.setWhatsThis("Load a mPSC template from a file.\nThe file must contain a single AnalogSignal, and can be a pickle (*.pkl), axon text file (*.atf) or binary (*.abf) file")
        self.loadTemplateFilePushButton.setStatusTip("Load a mPSC template from a file")
        self.loadTemplateFilePushButton.clicked.connect(self._slot_openTemplate)
        
        self.forgetTemplatePushButton = QtWidgets.QPushButton(QtGui.QIcon.fromTheme("delete"),
                                                    "Forget current",
                                                    parent = self.templateGroupBox)
        
        self.forgetTemplatePushButton.setToolTip("Forget olsd mPSC template")
        self.forgetTemplatePushButton.setWhatsThis("Forget olsd mPSC template.\nA new template must be loaded from workspace or a file")
        self.forgetTemplatePushButton.setStatusTip("Forget olsd mPSC template")
        self.forgetTemplatePushButton.clicked.connect(self._slot_forgetTemplate)
        
        self.createTemplatePushButton = QtWidgets.QPushButton(QtGui.QIcon.fromTheme("document-save-as-template"),
                                                              "Store",
                                                              parent = self.templateGroupBox)
        self.createTemplatePushButton.setToolTip("Create a new template from the mPSC waveform")
        self.createTemplatePushButton.setWhatsThis("Create a new template from the mPSC waveform")
        self.createTemplatePushButton.setStatusTip("Create a new template from the mPSC waveform")
        self.createTemplatePushButton.clicked.connect(self._slot_createTemplate)
        
        
        #### BEGIN settings widgets group: contains settings widgets (buttons & checkboxes)
        self.settingsWidgetsGroup = qd.HDialogGroup(self.mainGroup)
        
        self.clearDetectionCheckBox = qd.CheckBox(self.settingsWidgetsGroup, "Clear previous detection")
        self.clearDetectionCheckBox.setIcon(QtGui.QIcon.fromTheme("edit-clear-history"))
        self.clearDetectionCheckBox.setChecked(self._clear_events_flag_ == True)
        self.clearDetectionCheckBox.stateChanged.connect(self._slot_clearDetectionChanged)
        
        # self.useTemplateWaveFormCheckBox = qd.CheckBox(self.settingsWidgetsGroup, "Use mPSC template")
        # self.useTemplateWaveFormCheckBox.setIcon(QtGui.QIcon.fromTheme("template"))
        # self.useTemplateWaveFormCheckBox.setChecked(self._use_template_)
        # self.useTemplateWaveFormCheckBox.stateChanged.connect(self._slot_useTemplateWaveForm)
        
        self.settingsWidgetsGroup.addWidget(self.clearDetectionCheckBox)
        # self.settingsWidgetsGroup.addWidget(self.useTemplateWaveFormCheckBox)
        
        self.mainGroup.addWidget(self.settingsWidgetsGroup)
        #### END settings widgets group: contains settings widgets (buttons & checkboxes)
        
        #### BEGIN group for detection in frame: detect in frame & undo frame detection
        self.frameDetectionGroup = qd.HDialogGroup(self.mainGroup)
        self.frameDetectionGroupBox = QtWidgets.QGroupBox("Detect in sweep", self.frameDetectionGroup)
        
        self.frameDetectionLayout = QtWidgets.QHBoxLayout(self.frameDetectionGroupBox)
        self.detectmPSCInFramePushButton = QtWidgets.QPushButton(QtGui.QIcon.fromTheme("edit-find"),
                                                                 "Detect", parent=self.frameDetectionGroupBox)
        self.detectmPSCInFramePushButton.clicked.connect(self.slot_detect_in_frame)
        
        self.undoFramePushButton = QtWidgets.QPushButton(QtGui.QIcon.fromTheme("edit-undo"),
                                                         "Undo", parent = self.frameDetectionGroupBox)
        self.undoFramePushButton.clicked.connect(self.slot_undo_frame)
        
        self.frameDetectionLayout.addWidget(self.detectmPSCInFramePushButton)
        self.frameDetectionLayout.addWidget(self.undoFramePushButton)
        self.frameDetectionGroup.addWidget(self.frameDetectionGroupBox)
        
        self.mainGroup.addWidget(self.frameDetectionGroup)
        #### END group for detection in frame: detect in frame & undo frame detection
            
        #### BEGIN Group for mPSC detection in whole data
        self.detectionGroup = qd.HDialogGroup(self.mainGroup)
        self.detectionGroupBox = QtWidgets.QGroupBox("Detect in data", self.detectionGroup)
        self.detectionGroupLayout = QtWidgets.QHBoxLayout(self.detectionGroupBox)
        self.detectmPSCPushButton = QtWidgets.QPushButton(QtGui.QIcon.fromTheme("edit-find"),
                                                          "Detect", parent=self.detectionGroupBox)
        self.detectmPSCPushButton.clicked.connect(self.slot_detect)
        
        self.undoDetectionPushButton = QtWidgets.QPushButton(QtGui.QIcon.fromTheme("edit-undo"),
                                                             "Undo", parent=self.detectionGroupBox)
        self.undoDetectionPushButton.clicked.connect(self.slot_undo)
        
        self.detectionGroupLayout.addWidget(self.detectmPSCPushButton)
        self.detectionGroupLayout.addWidget(self.undoDetectionPushButton)
        
        self.detectionGroup.addWidget(self.detectionGroupBox)
        
        
        self.mainGroup.addWidget(self.detectionGroup)
        #### END Group for mPSC detection in whole data
        
        self.addWidget(self.mainGroup)
        
        self.buttons.OK.setIcon(QtGui.QIcon.fromTheme("dialog-ok-apply"))
        self.buttons.Cancel.setIcon(QtGui.QIcon.fromTheme("dialog-cancel"))
        
        self.statusBar = QtWidgets.QStatusBar(parent=self)
        self.addWidget(self.statusBar)
        
        self.setWindowModality(QtCore.Qt.NonModal)
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
        
    def _load_template(self):
        tpl = self.importWorkspaceData(neo.AnalogSignal,
                                        title="Import mPSC Template",
                                        single=True)
        
        if len(tpl) and isinstance(tpl[0], neo.AnalogSignal):
            self._template_ = tpl[0]
            if os.path.isfile(self._template_file_):
                pio.saveHDF5(self._template_, self._template_file_)
            return True
            
        self._template_ = None
        
        return False
        
    def _open_template_file(self, fileName:typing.Optional[str]):
        # NOTE: 2022-11-03 16:50:03
        # chooseFile is defined in FileIOGui and inherited via WorkspaceGuiMixin
        
        if not isinstance(fileName, str) or len(fileName.strip()) or not os.path.isfile(fileName):
            fileName, fl = self.chooseFile("Choose mPSC Template", "Pickle Files (*.pkl);;Axon text files (*.atf);; Axon binary files (*.abf)")
        
            if len(fileName.strip()) == 0:
                return False
        
        data = pio.loadFile(fileName)
        
        if isinstance(data, neo.AnalogSignal):
            self._template_ = data
            
            if os.path.isfile(self._template_file_):
                pio.saveHDF5(self._template_, self._template_file_)
            
            return True
        else:
            self.criticalMessage("The chosen file does not contain an Analog Signal")
            return False
        
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
        
    def _plot_template_(self):
        if isinstance(self._template_, neo.AnalogSignal):
            self.waveFormDisplay.plot(self._template_)
            
    def _plot_model_(self):
        if isinstance(self._template_, neo.AnalogSignal) and self._use_template_:
            self.waveFormDisplay.plot(self._template_)
        else:
            self._model_waveform_ = membrane.PSCwaveform(self._params_initl_,
                                                        duration = self.mPSCDuration,
                                                        sampling_rate = self._waveform_sampling_rate)
            
            self.waveFormDisplay.plot(self._model_waveform_)
            
    @pyqtSlot()
    def _slot_plot_model(self):
        self._plot_model_()
        
    @pyqtSlot()
    def accept(self):
        super().accept()
        
    @pyqtSlot()
    def reject(self):
        super().reject()
        
    @pyqtSlot(int)
    def done(self, value):
        """PyQt slot called by self.accept() and self.reject() (see QDialog).
        Also closes the dialog (equivalent of QWidget.close()).
        """
        if value == QtWidgets.QDialog.Accepted and not self.detected:
            self.detect_mPSCs()
            
        if self._ephysViewer_.isVisible():
            if self._owns_viewer_:
                self._ephysViewer_.close()
            
            else:
                self._ephysViewer_.refresh()
                
        if self.waveFormDisplay.isVisible():
            self.waveFormDisplay.close()
            
        self.saveSettings()
                
        super().done(value)
        
    @pyqtSlot()
    def _slot_useTemplateWaveForm(self):
        val = self.useTemplateWaveFormCheckBox.selection()
        self._use_template_ = val==True
        if self._use_template_:
            if self._template_ is None:
                self._use_template_ =  self._open_template_file(self._template_file_) or self._load_template()
                    
            signalBlocker = QtCore.QSignalBlocker(self.useTemplateWaveFormCheckBox)
            self.useTemplateWaveFormCheckBox.setChecked(isinstance(self._template_, neo.AnalogSignal))
            
    @pyqtSlot()
    def _slot_loadTemplate(self):
        self._load_template()
        
    @pyqtSlot()
    def _slot_openTemplate(self):
        self._open_template_file()
        
    @pyqtSlot()
    def _slot_forgetTemplate(self):
        self._template_ = None
        if os.path.isfile(self._template_file_):
            os.remove(self._template_file_)
        
        signalBlocker = QtCore.QSignalBlocker(self.useTemplateWaveFormCheckBox)
        self.useTemplateWaveFormCheckBox.setChecked(isinstance(self._template_, neo.AnalogSignal))
        
    @pyqtSlot()
    def _slot_createTemplate(self):
        if isinstance(self._template_, neo.AnalogSignal):
            if os.path.isfile(self._template_file_):
                pio.saveHDF5(self._template_, self._template_file_)
        
         
                    
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
        
        self.detect_mPSCs_inFrame()
        
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
                
    @pyqtSlot(float)
    def _slot_modelDurationChanged(self, value):
        self.mPSCDuration = self.durationSpinBox.value() * self._default_time_units_
        self._plot_model_()
        
    # @pyqtSlot()
    # def _slot_modelParametersChanged(self):
    #     # α, β, x₀, τ₁ and τ₂ AND WAVEFORM_DURATION !!! 
    #     #### BEGIN debug - comment out when done
    #     # print(f"{self.__class__.__name__}._slot_modelParametersChanged ...")
    #     #### END debug - comment out when done
    #     # NOTE / FIXME: 2022-11-02 22:00:22 these are pd.Series, neither list, nor tuple
    #     # They will be converted to lists by their corresponding setter methods
    #     # e.g.0@ mPSCParametersInitial.setter, etc
    #     self.mPSCParametersInitial      = self.paramsWidget.parameters["Initial Value:"]
    #     self.mPSCParametersLowerBounds  = self.paramsWidget.parameters["Lower Bound:"]
    #     self.mPSCParametersUpperBounds  = self.paramsWidget.parameters["Upper Bound:"]
    #     self.mPSCDuration               = self.durationSpinBox.value() * self._default_time_units_
    #     self._plot_model_()
    #     #### BEGIN debug - comment out when done
    #     # print(f"DONE {self.__class__.__name__}._slot_modelParametersChanged\n\n")
    #     #### END debug - comment out when done
        
    @pyqtSlot(str, str)
    def _slot_modelParameterChanged(self, row, column):
        if column == "Initial Value:":
            self.mPSCParametersInitial      = self.paramsWidget.parameters["Initial Value:"]
        elif column == "Lower Bound:":
            self.mPSCParametersLowerBounds  = self.paramsWidget.parameters["Lower Bound:"]
        elif column == "Upper Bound:":
            self.mPSCParametersUpperBounds  = self.paramsWidget.parameters["Upper Bound:"]
            
        self._plot_model_()
        
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
        # allow rerun detection
        # self.detectmPSCPushButton.setEnabled(not self._mPSC_detected_)
        
    @property
    def mPSCTemplate(self):
        return self._template_
    
    @mPSCTemplate.setter
    def mPSCTemplate(self, value:typing.Optional[typing.Union[neo.AnalogSignal, typing.Sequence[neo.AnalogSignal]]]=None):
        if isinstance(value, neo.AnalogSignal):
            self._template_ = value
            self._plot_template_(self._template_)
            
        elif isinstance(value, (tuple, list)) and all(isinstance(v, neo.AnalogSignal) for v in value):
            self._template_ = value
            self._plot_template_(self._template_)
            
        elif value is None:
            self._template_ = value
            self.waveFormDisplay.clear()
        
    @property
    def ephysdata(self):
        return self._ephys_
    
    @ephysdata.setter
    def ephysdata(self, value):
        self._set_ephys_data_(value)
        
    @property
    def useTemplateWaveForm(self):
        return self._use_template_
    
    @markConfigurable("UseTemplateWaveform")
    @useTemplateWaveForm.setter
    def useTemplateWaveForm(self, value):
        self._use_template_ = value == True
        
    @property
    def templateWaveFormFile(self):
        return self._template_file_
    
    @markConfigurable("templateWaveFormFile")
    @templateWaveFormFile.setter
    def templateWaveFormFile(self, value:str):
        import os
        if isinstance(value, str) and os.path.isfile(value):
            self._template_file_ = value
            
        else:
            self._template_file_ = self._default_template_file
        
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
    def mPSCParametersInitial(self):
        """Initial parameter values
        """
        return dict(zip(self._params_names_, self._params_initl_))
    
    @markConfigurable("mPSCParametersInitial")
    @mPSCParametersInitial.setter
    def mPSCParametersInitial(self, val:typing.Union[pd.Series, tuple, list, dict]):
        if isinstance(val, (pd.Series, tuple, list, dict)):
            if len(val) != len(self._default_params_initl_):
                val = self._default_params_initl_
                
            elif isinstance(val, pd.Series):
                val = list(val)
                
            if isinstance(val, (tuple, list)):
                if all(isinstance(s, pq.Quantity) for s in val):
                    self._params_initl_ = [v for v in val]
                    
                elif all(isinstance(v, str) for v in val):
                    self._params_initl_ = list(str2quantity(v) for v in val)

                else:
                    raise TypeError("Expecting a sequence of scalar quantities or their str representations")
                
            elif isinstance(val, dict):
                assert set(val.keys()) == set(self._params_names_), f"Argument keys for initial values must match parameters names {self._params_names_}"
                
                for k, v in val.items():
                    self._params_initl_[self._params_names_.index(k)] = v
            
        elif val in (None, np.nan, math.nan):
            raise TypeError(f"Initial parameter values cannot be {val}")
        
        else:
            raise TypeError(f"Expecting a sequence of scalar quantities (or their str representations) for initial values; instead, got {type(val).__name__}:\n {val}")

        if isinstance(getattr(self, "configurable_traits", None), DataBag):
            self.configurable_traits["mPSCParametersInitial"] = dict(zip(self._params_names_, self._params_initl_))
                
    @property
    def mPSCParametersLowerBounds(self):
        return dict(zip(self._params_names_, self._params_lower_))
    
    @markConfigurable("mPSCParametersLowerBounds")
    @mPSCParametersLowerBounds.setter
    def mPSCParametersLowerBounds(self, val:typing.Union[pd.Series, tuple, list, dict]):
        if isinstance(val, (pd.Series, tuple, list, dict)):
            if len(val) not in (1, len(self._default_params_initl_)):
                val = self._default_params_lower_
                # raise ValueError(f"Expecting 1 or {len(self._default_params_initl_)} lower bounds; instead, got {len(val)}")
            
        if isinstance(val, pd.Series):
            val = list(val)
        
        if isinstance(val, (tuple, list)):
            if all(isinstance(v, pq.Quantity) for v in val):
                self._params_lower_ = [v for v in val]
                
            elif all(isinstance(v, str) for v in val):
                self._params_lower_ = list(str2quantity(v) for v in val)
                
            else:
                raise TypeError("Expecting a sequence of scalar quantities or their str representations")
            
        elif isinstance(val, dict):
            assert set(val.keys()) == set(self._params_names_), f"Argument keys for lower bounds must match parameters names {self._params_names_}"
            
            for k, v in val.items():
                self._params_lower_[self._params_names_.index(k)] = v
            
        elif val in (None, np.nan, math.nan):
            self._params_lower_ = val
            
        else:
            raise TypeError(f"Expecting a sequence of scalar quantities, str representations of scalar quantiities, or one of None, math.nan, np.nan, for the lower bounds; instead, got {type(val).__name__}:\n {val}")
                
        if isinstance(getattr(self, "configurable_traits", None), DataBag):
            self.configurable_traits["mPSCParametersLowerBounds"] = dict(zip(self._params_names_, self._params_lower_))
                
    @property
    def mPSCParametersUpperBounds(self):
        return dict(zip(self._params_names_, self._params_upper_))
    
    @markConfigurable("mPSCParametersUpperBounds")
    @mPSCParametersUpperBounds.setter
    def mPSCParametersUpperBounds(self, val:typing.Union[pd.Series, tuple, list, dict]):
        if isinstance(val, (pd.Series, tuple, list, dict)):
            if len(val) not in (1, len(self._default_params_initl_)):
                val = self._default_params_upper_
            
            elif isinstance(val, pd.Series):
                val = list(val)
            
            if isinstance(val, (tuple, list)):
                if all(isinstance(v, pq.Quantity) for v in val):
                    self._params_upper_ = [v for v in val]
                    
                elif all(isinstance(v, str) for v in val):
                    self._params_upper_ = list(str2quantity(v) for v in val)
                    
                else:
                    raise TypeError("Expecting a sequence of scalar quantities or their str representations")
                
            elif isinstance(val, dict):
                assert set(val.keys()) == set(self._params_names_), f"Argument keys for upper bounds must match parameters names {self._params_names_}"
                
                for k, v in val.items():
                    self._params_upper_[self._params_names_.index(k)] = v
            
        elif val in (None, np.nan, math.nan):
            self._params_upper_ = val

        else:
            raise TypeError(f"Expecting a sequence of scalar quantities, str representations of scalar quantiities, or one of None, math.nan, np.nan, for the upper bounds; instead, got {type(val).__name__}:\n {val}")
                
        if isinstance(getattr(self, "configurable_traits", None), DataBag):
            self.configurable_traits["mPSCParametersUpperBounds"] = dict(zip(self._params_names_, self._params_upper_))
                
    @property
    def mPSCDuration(self):
        return self._mPSCduration_
    
    @markConfigurable("mPSCDuration")
    @mPSCDuration.setter
    def mPSCDuration(self, val:typing.Union[str, pq.Quantity]):
        if isinstance(val, pq.Quantity):
            self._mPSCduration_ = val
            
        elif isinstance(val, str):
            self._mPSCduration_ = str2quantity(val)
            
        else:
            raise TypeError("Expecting a scalar quantity, or a str representation of a scalar quantity, for mPSCDuration")
        
        if isinstance(getattr(self, "configurable_traits", None), DataBag):
            self.configurable_traits["mPSCDuration"] = self._mPSCduration_
            # self.configurable_traits["mPSCDuration"] = quantity2str(self._mPSCduration_)
            
    def detect_mPSCs_inFrame(self):
        self.detected = False
        if self._ephys_ is None:
            return
        
    def detect_mPSCs(self):
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
                
