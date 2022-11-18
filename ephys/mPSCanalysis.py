# -*- coding: utf-8 -*-
import os, typing, math, datetime
from numbers import (Number, Real,)
from itertools import chain

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__

import numpy as np
import quantities as pq
import neo
import pyqtgraph as pg
import pandas as pd

from iolib import pictio as pio
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

from core.workspacefunctions import get_symbol_in_namespace

from gui import quickdialog as qd
import gui.scipyenviewer as scipyenviewer
from gui.scipyenviewer import ScipyenFrameViewer
import gui.signalviewer as sv
from gui.signalviewer import SignalCursor as SignalCursor
import gui.pictgui as pgui
from gui.pictgui import ItemsListDialog
from gui.workspacegui import (GuiMessages, WorkspaceGuiMixin)
from gui.widgets.modelfitting_ui import ModelParametersWidget
from gui.widgets.spinboxslider import SpinBoxSlider
from gui.widgets.metadatawidget import MetaDataWidget
from gui.widgets import small_widgets
from gui.widgets.small_widgets import QuantitySpinBox
from gui import guiutils

import iolib.pictio as pio

__module_path__ = os.path.abspath(os.path.dirname(__file__))

__Ui_mPSDDetectWindow__, __QMainWindow__ = __loadUiType__(os.path.join(__module_path__, "mPSCDetectWindow.ui"))

class MPSCAnalysis(ScipyenFrameViewer, __Ui_mPSDDetectWindow__):
    
    # NOTE: this refers to the type of data where mPSC detection is done.
    # The mPSC waveform viewer only expects neo.AnalogSignal
    supported_types = (neo.Block, neo.Segment, type(None))
    
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
    
    def __init__(self, ephysdata=None, clearOldPSCs=False, ephysViewer:typing.Optional[sv.SignalViewer]=None, parent:(QtWidgets.QMainWindow, type(None)) = None, win_title="mPSC Detect", **kwargs):
        # NOTE: 2022-11-05 14:54:24
        # by default, frameIndex is set to all available frames - KISS
        self.threadpool = QtCore.QThreadPool()
        
        self._clear_events_flag_ = clearOldPSCs == True
        self._mPSC_detected_ = False
        self._data_var_name_ = None
        self._cached_detection_ = None
        self._use_template_ = False
        self._mPSC_template_ = None
        
        self._data_ = None
        # self._detection_epoch_name_ = None
        self._detection_signal_name_ = None
        self._detection_epochs_ = list()
        
        # the template file where a mPSC template is stored across sessions
        # this is located in the Scipyen's config directory
        # (on Linux, this file is in $HOME/.config/Scipyen, and its name can be
        # con figured by triggering the appropriate action in the Settings menu)
        # NOTE: this file name is NOT written in the config file !!!
        self._template_file_ = self._default_template_file
        
        # we can also remember a file elsewhere in the file system, other than
        # the one above. NOTE: this file name IS WRITTEN in the config.
        self._custom_template_file_ = ""
        
        # NOTE: 2022-11-17 23:37:00 
        # About mPSC template files
        # The logic is as follows:
        # • by default at startup, the mPSC template is read from the custom 
        #   template file, if it is accessible (NOTE: the template file is NOT
        #   actually read at __init__, but only when a detection is initiated,
        #   or when the waveform template is plotted)
        #
        # • else the mPSC template is read from the default template file, if it
        #   is accessible;
        #
        # • else, there is no mPSC template for the session.
        #
        # When the user MAKES a new template, or IMPORTS one from workspace:
        # • the mPSC template will be stored in the default template file (overwriting it)
        #   ONLY IF the user chooses to do so by triggering the action "Set Default mPSC Template"
        #
        # When the user OPENS (READS) an mPSC template from a file in the file system
        # (other that the default template file):
        # • the name of THIS file is stored as the custom template file in the
        #   config
        #
        # • the mPSC template will be stored in the default template file (overwriting it)
        #   ONLY IF the user chooses to do so by triggering the action "Set Default mPSC Template"
        #
        # When the user triggers "Forget mPSC template", then:
        #   ∘ the mPSC template is cleared for the session and the template from
        #       the default template file is loaded (is available)
        #   ∘ the custom mPSC template file name is removed from the config (i.e. is set to "")
        #   ∘ at the next session only the default mPSC template may be available
        #
        # When the user triggers "Remove default mPSC template", then:
        #   ∘ the default mPSC template file is removed
        #   ∘ the mPSC template of the session (if it exists) exists and can be 
        #       used until Forget mPSC template is also triggered
        #
        # When there is no mPSC template loaded in the session, AND Use mPSC template
        # is checked, then the session will proceed as:
        # • load mPSC template from the custom file, if present
        # • else load mPSC template from the default file, if present
        # • else ask user to select a template from the workspace (if there is one)
        #   NOTE: this is a single neo.AnalogSignal named "mPSC template" so it 
        #   would be easy to "fool" the app simply by renaming ANY neo.AnalogSignal
        #   in the workspace
        # • if no template is chosen form workspace (or there is None available)
        #   then user can choose a template file in the file system (not prompted;
        #   the user must take this action independently)
        #   
        #   if no template has been loaded (either because user has cancelled the
        #   dialogs, or whatever was loaded from the file system does NOT appear
        #   to be an mPSC template) then Use mPSC Template is automatically unckeched
        #   
        # When a mPSC detect action is triggered, AND Use mPSC template is checked
        #   proceed as above; if no templata has been loaded, then switch this 
        #   flag off and proceed with a synthetic waveform generated on the fly
        #
        #
        # when the user opens a mPSC template from the file system, the name of 
        # THAT file is stored in the configuration as custom template file
        
        # 
        
        # temporarily holds the file selected in _slot_editPreferences
        # self._cached_template_file_ =  self._default_template_file
        
        # detected mPSC waveform(s) to validate
        # can be a single neo.AnalogSignal, or, usually, a sequence of
        # neo.AnalogSignal objects
        # NOTE: when detection was made in a collection of segments (e.g. a Block)
        # the _detected_mPSCs_ will change with each segment !
        self._detected_mPSCs_ = None
        self._waveform_frames = 0
        self._currentWaveformIndex_ = 0
        
        
        # NOTE: 2022-11-11 23:04:37
        # the mPSC template is an average of selected waveforms, that have,
        # typically, been detected using cros-correlation with a model mPSC
        # The last mPSC template used is stored in a file (by default, located 
        # the Scipyen's config directory) so that it can be used across sessions
        # This file will be overwritten at the end of each session, so any new 
        # template will replace the old one. This is for convenience, so that
        # the user gets their last used template at the start of a new session
        # (instead of searching for it in the file system, etc).
        # However, the app offers the possibility to save the template to a user
        # file, such that the user can choose form a collection of templates
        # at any time.
        #
        # See also NOTE: 2022-11-17 23:37:00 
        #
        self._mPSC_template_ = None
        
        # NOTE: 2022-11-11 23:10:42
        # the realization of the mPSC model according to the parameters in the 
        # mPSC Model Groupbox
        # this serves as a cache for detecting mPSCs in a collection of segments
        # (and thus to avoid generating a new waveform for every segment)
        # HOWEVER, it is recommended to re-create this waveform from parameters
        # every time a new detection starts (for a segment, when started manually
        # or before the first segment when detection is started for a collection 
        # of segments)
        
        self._mPSC_model_waveform_ = None
        
        self._result_ = None

        # NOTE: 2022-11-10 09:25:48
        # these three are set up by the super() initializer
        # self._data_frames_ = 0
        # self._frameIndex_ = range(self._data_frames_)
        # self._number_of_frames_ = len(self._frameIndex_)
        
        # NOTE: 2022-11-05 15:14:11
        # logic from TriggerDetectDialog: if this instance of MPSCAnalysis
        # uses its own viewer then self._own_ephys_viewer_ will be set to True
        # This allows re-using a SignalViewer that already exists in the 
        # workspace.
        # self._own_ephys_viewer_ = False # replacted with self._owns_viewer_ below
        
        # NOTE: 2022-11-03 22:55:52 
        #### BEGIN these shouldn't be allowed to change
        self._params_names_ = self._default_params_names_
        #### END these shouldn't be allowed to change
        
        self._params_initl_ = self._default_params_initl_
        self._params_lower_ = self._default_params_lower_
        self._params_upper_ = self._default_params_upper_
        self._mPSCduration_ = self._default_duration_
        
        # NOTE: 2022-11-10 09:22:35
        # the super initializer calls:
        # self._configureUI_ - overridden here
        # self.loadSettings - not overridden here
        # self.setData → self._set_data_
        # 
        # so data-dependent variables should be set in self._set_data_ and UI
        # widgets SHOULD be available
        super().__init__(data=ephysdata, win_title=win_title, 
                         doc_title=self._data_var_name_, parent=parent)
        
        self.winTitle = "mPSC Detect"
        
        # NOTE: 2022-11-05 23:48:25
        # must be executed here AFTER superclasses have been initialized,
        # but BEFORE _set_data_ which might call self.clear (expecting self._ephysViewer_)
        #
        if isinstance(ephysViewer, sv.SignalViewer):
            self._ephysViewer_ = ephysViewer
            self._owns_viewer_ = False
        else:
            self._ephysViewer_ = sv.SignalViewer(win_title=self._winTitle_, 
                                                 parent=self, configTag="DataViewer")
            self._owns_viewer_ = True
            
        self.linkToViewers(self._ephysViewer_)
        self._ephysViewer_.sig_newEpochInData.connect(self._slot_newEpochGenerated)
        self._ephysViewer_.sig_axisActivated.connect(self._slot_newSignalViewerAxisSelected)
            
        if self._data_ is not None:
            self._ephysViewer_.plot(self._data_)
            
        # NOTE: 2022-11-05 15:09:59
        # will stay hidden until a waveform (either a mPSC model realisation or 
        # a template mPSC) or a sequence of detetected minis becomes available
        self._waveFormViewer_ = sv.SignalViewer(win_title="mPSC waveform", 
                                                parent=self, configTag="WaveformViewer")
        
        self._detected_mPSCViewer_ = sv.SignalViewer(win_title="Detected mPSCs", 
                                                     parent=self, configTag="mPSCViewer")
        
        self.loadSettings()
        
        self._set_data_(ephysdata)
        
        # NOTE: 2022-11-05 23:08:01
        # this is inherited from WorkspaceGuiMixin therefore it needs full
        # initialization of WorkspaceGuiMixin instance
        # self._data_var_name_ = self.getDataSymbolInWorkspace(self._data_)
        
        self.resize(-1,-1)
        
    def _configureUI_(self):
        self.setupUi(self)
        
        # NOTE: 2022-11-08 22:55:24 Using custom widgets in Designer.
        # A) Via widget "promotion" in Designer, going through the steps below:
        #
        # A.1) Use a QWidget in lieu of your custom widget. 
        #
        #   This QWidget should be an instance of the nearest stock Qt SUPERCLASS
        #   of your custom widget. For example:
        #
        #   ∘ if your custom widget inherits from QWidget directly (e.g., was
        #     itself created using the Widget template in Designer) then use a 
        #     "generic" QWidget in Designer; this is the case of, e.g., the
        #     MetaDataWidget, ModelParametersWidget
        #
        #   ∘ if your widget is QuantitySpinBox (which inherits directly from
        #       QDoubleSpinBox) then use QDoubleSpinBox in Designer
        #
        #       (QuantitySpinBox code was generated manually)
        #       
        # A.2) Promote this place-holder QWidget to the actual widget type:
        #
        # A.2.1) Use the name of the custom widget class as promoted class name, 
        #       e.g. QuantitySpinBox
        #       or   ModelParametersWidget
        #
        # A.2.2) Use the fully qualified module name as header file (instead of an
        #   actual header file name) - one should be able to import this module
        #   inside a running Scipyen session.
        #
        #       Examples:
        #       ∘ gui.widgets.small_widgets for QuantitySpinBox
        #       ∘ gui.widgets.modelfitting_ui for ModelParametersWidget
        #
        # A.2.3) Set the "Global include" checkbox to True
        #
        # Advantages:
        #   • Requires NO extra UI defintion Python code in the Python module 
        #       that defines the custom class; this extra code is automatically
        #       generated by loadUiType function in PyQt5. The custom class MUST
        #       inherit from the Python class generated automatically by 
        #       loadUiType - see PyQt5 documentation for details.
        #   
        # Disadvantages:
        #   • Cannot pass custom parameter values to the custom widget intialization.
        #       In other words, your custom UI object type MUST accept a default
        #       __init__ syntax (see below)
        #   • "Fancy" __init__ for the custom widget won't work:
        #       one has to make sure the __init__ can work with only the bare 
        #       minimum parameters, which are passed on the Qt superclass.
        #
        #       These bare minimum parameters these are usually just "parent", 
        #       which must be the first positional parameter, and denotes the 
        #       parent widget of the custom widget. 
        #
        #       The loadUiType assigns automatically the "parent" based on the UI 
        #       form.
        #
        #       Extra parameters (to allow custom initialization) should be
        #       passed as (key,value) pairs, captured in the var-keyword
        #       parameter `kwargs`, or as named parameters with default values.
        #
        # B) Alternatively, use a generic QWidget as place-holder
        #   (if (A) doesn't work, but WARNING this is more cumbersome):
        # B.1) Use a "generic" QWidget in lieu of your custom widget
        #
        # B.2) Use this place-holder widget as a container, by writing code in 
        #   your custom UI class:
        #
        # B.2.1) Set its layout to, e.g., a grid layout 
        #
        # B.3) Construct an instance of your custom widget - make sure you bind
        # it to an atribute in self (parent class); set its parent to the 
        #       place-holder widget above
        #
        # B.4) Add the instance of the custom widget to the layout of the 
        #   place-holder
        #
        # Advantages:
        # • can pass custom parameter values to the constructor of the custom 
        #   widget, which is done in the Python class, NOT in the UI form
        #
        # Disadvantages:
        # • cumbersome to write code (and perhaps, more difficult to track/debug)
        #
        # Throughout, I use protocol (A) above in Designer UI forms
        #
        self.paramsWidget.setParameters(self._params_initl_,
                                        lower = self._params_lower_,
                                        upper = self._params_upper_,
                                        names = self._params_names_,
                                        refresh = True)
        
        self.paramsWidget.spinStep = 1e-4
        self.paramsWidget.spinDecimals = 4
        
        self.paramsWidget.sig_parameterChanged[str, str].connect(self._slot_modelParameterChanged)
        
        self._frames_spinBoxSlider_.label = "Sweep:"
        self._frames_spinBoxSlider_.setRange(0, self._number_of_frames_)
        self._frames_spinBoxSlider_.valueChanged.connect(self.slot_setFrameNumber) # slot inherited from ScipyenFrameViewer
        
        self._mPSC_spinBoxSlider_.label = "mPSC:"
        self._mPSC_spinBoxSlider_.setRange(0,0)
        self._mPSC_spinBoxSlider_.valueChanged.connect(self._slot_setWaveFormIndex)
        
        self.durationSpinBox.setDecimals(self.paramsWidget.spinDecimals)
        self.durationSpinBox.setSingleStep(10**(-self.paramsWidget.spinDecimals))
        self.durationSpinBox.units = pq.s
        self.durationSpinBox.setRange(0*pq.s, 0.1*pq.s)
        self.durationSpinBox.setValue(self._mPSCduration_)
        self.durationSpinBox.valueChanged.connect(self._slot_modelDurationChanged)
        
        # actions (shared among menu and toolbars):
        self.actionOpen.triggered.connect(self._slot_openEphysDataFile)
        self.actionImport.triggered.connect(self._slot_importEphysData)
        self.actionSave.triggered.connect(self._slot_saveEphysData)
        self.actionExport.triggered.connect(self._slot_exportEphysData)
        self.actionPlot_Data.triggered.connect(self._slot_plotData)
        self.actionMake_mPSC_Epoch.triggered.connect(self._slot_make_mPSCEpoch)
        # TODO: 2022-11-11 23:38:20
        # connections and slots for the actions below
        self.actionOpen_mPSCTemplate
        self.actionCreate_mPSC_Template
        self.actionImport_mPSCTemplate
        self.actionSave_mPSC_Template
        self.actionExport_mPSC_Template
        self.actionRemember_mPSC_Template
        self.actionForget_mPSC_Template
        self.actionDetect_in_current_sweep.triggered.connect(self._slot_detect_sweep)
        self.actionValidate_in_current_sweep
        self.actionUndo_current_sweep
        self.actionDetect
        self.actionValidate
        self.actionUndo
        self.actionView_results
        self.actionSave_results
        self.actionExport_results
        self.actionClear_results
        self.actionUse_default_location_for_persistent_mPSC_template.toggled.connect(self._slot_useDefaultTemplateLocation)
        self.actionChoose_persistent_mPSC_template_file.triggered.connect(self._slot_choosePersistentTemplateFile)
        # signal & epoch comboboxes
        self.signalNameComboBox.currentTextChanged.connect(self._slot_newTargetSignalSelected)
        self.signalNameComboBox.currentIndexChanged.connect(self._slot_newTargetSignalIndexSelected)
        self.epochComboBox.currentTextChanged.connect(self._slot_epochComboBoxSelectionChanged)
        # self.epochComboBox.currentIndexChanged.connect(self._slot_new_mPSCEpochIndexSelected)
        
        self.use_mPSCTemplate_CheckBox.setChecked(self._use_template_ == True)
        self.use_mPSCTemplate_CheckBox.stateChanged.connect(self._slot_use_mPSCTemplate)
        
        self.clearPreviousDetectionCheckBox.setChecked(self._clear_events_flag_ == True)
        self.clearPreviousDetectionCheckBox.stateChanged.connect(self._slot_set_clear_events_flag_)
        
        self.plot_mPSCWaveformPushButton.clicked.connect(self._slot_plot_mPSCWaveForm)
        
    def _set_data_(self, *args, **kwargs):
        # called by super() initializer; 
        # UI widgets not yet initialized
        if len(args):
            data = args[0]
        else:
            data = kwargs.pop("data", None)
            
        if neoutils.check_ephys_data_collection(data): # and self._check_supports_parameter_type_(data):
            self._cached_detection_ = list()
            
            if isinstance(data, neo.Block):
                for s in data.segments:
                    if len(s.spiketrains):
                        trains = [st for st in s.spiketrains if st.annotations.get("source", None)=="mPSC_detection"]
                        if len(trains):
                            self._cached_detection_.append(trains[0])
                        else:
                            self._cached_detection_.append(None)
                            
                self._data_ = data
                
                if len(self._data_.segments) and len(self._data_.segments[0].analogsignals):
                    time_units = self._data_.segments[0].analogsignals[0].times.units
                else:
                    time_units = pq.s
                    
                self.durationSpinBox.units = time_units
                        
                
                # NOTE: 2022-11-05 14:50:26
                # although self._data_frames_ and self._number_of_frames_ end up
                # having the same value they are distinct entities and the three 
                # lines below illustrate how to set them up
                self._data_frames_ = len(self._data_.segments)
                self._frameIndex_ = range(self._data_frames_)
                self._number_of_frames_ = len(self._frameIndex_)
                            
            elif isinstance(data, neo.Segment):
                if len(data.spiketrains):
                    trains = [st for st in data.spiketrains if st.annotations.get("source", None)=="mPSC_detection"]
                    if len(trains):
                        self._cached_detection_.append(trains[0])
                    else:
                        self._cached_detection_.append(None)
                            
                self._data_ = data
                self._data_frames_ = 1
                self._frameIndex_ = range(self._data_frames_)
                self._number_of_frames_ = len(self._frameIndex_)
                
            elif isinstance(data, (tuple, list)) and all(isinstance(v, neo.Segment) for v in data):
                for s in data.segments:
                    if len(s.spiketrains):
                        trains = [st for st in s.spiketrains if st.annotations.get("source", None)=="mPSC_detection"]
                        if len(trains):
                            self._cached_detection_.append(trains[0])
                        else:
                            self._cached_detection_.append(None)
                            
                self._data_ = data
                self._data_frames_ = len(self._data_)
                self._frameIndex_ = range(self._data_frames_)
                self._number_of_frames_ = len(self._frameIndex_)
                            
            else:
                self.errorMessage(self._dialog_title_, f"Expecting a neo.Block, neo.Segment, or a sequence of neo.Segment objects; got {type(data).__name__} instead")
                return
            
        elif data is None:
            # WARNING: passing None clears the viewer
            self.clear()
            return
            
        else:
            self.errorMessage(self._dialog_title_, f"Expecting a neo.Block, neo.Segment, or a sequence of neo.Segment objects, or None; got {type(data).__name__} instead")
            return
        
        vname = self.workspaceSymbolForData(self._data_)
        
        if isinstance(vname, str):
            self.metaDataWidget.dataVarName = vname
            
        name = getattr(self._data_, "name", "")
        
        self.metaDataWidget.dataName = name
        
        self._frames_spinBoxSlider_.setRange(0, self._number_of_frames_)
        
        self._plot_data()
        
        self._frames_spinBoxSlider_
        
        # NOTE: 2022-11-05 23:52:11
        # self._ephysViewer_ is not yet available when _set_data_ is called from __init__()
        if isinstance(self._ephysViewer_, sv.SignalViewer):
            self._ephysViewer_.view(self._data_)
            
    def _generate_mPSCModelWaveform(self):
        if self.mPSCDuration is pd.NA or (isinstance(self.mPSCDuration, pq.Quantity) and self.mPSCDuration.magnitude <= 0):
            return
        
        segment = self._get_data_segment_()
        if not isinstance(segment, neo.Segment):
            return
        
        signal = self._get_selected_signal_(segment)
        
        if isinstance(signal, neo.AnalogSignal) and signal.size > 1:
            sampling_rate = signal.sampling_rate
        else:
            sampling_rate = 1e4*pq.Hz
            
        model_params = self.paramsWidget.value()
        init_params = tuple(p.magnitude for p in model_params["Initial Value:"])
            
        self._mPSC_model_waveform_ = membrane.PSCwaveform(init_params, 
                                             duration=self.mPSCDuration,
                                             sampling_rate=sampling_rate)
        
    def _refresh_epochComboBox(self):
        if isinstance(self._data_, neo.Block):
            segment = self._data_.segments[self.currentFrame]
            
        elif isinstance(self._data_, (tuple,list)) and all(isinstance(s, neo.Segment) in self._data_):
            segment = self._data_[self.currentFrame]
            
        elif isinstance(self._data_, neo.Segment):#
            segment = self._data_
            
        else:
            return
        
        epochnames = ["None"] + [e.name for e in segment.epochs] + ["Select..."]
        signalBlocker = QtCore.QSignalBlocker(self.epochComboBox)
        self.epochComboBox.clear()
        self.epochComboBox.addItems(epochnames)
        
    def _refresh_signalNameComboBox(self, index:typing.Optional[int]=None):
        if isinstance(self._data_, neo.Block):
            segment = self._data_.segments[self.currentFrame]
        elif isinstance(self._data_, (tuple,list)) and all(isinstance(s, neo.Segment) in self._data_):
            segment = self._data_[self.currentFrame]
            
        elif isinstance(self._data_, neo.Segment):
            segment = self._data_
        else:
            return
        
        signames = [s.name for s in segment.analogsignals]
        self.signalNameComboBox.clear()
        signalBlockers = [QtCore.QSignalBlocker(w) for w in (self.signalNameComboBox, self._ephysViewer_)]
        if len(signames):
            self.signalNameComboBox.addItems(signames)
            if index in range(len(signames)):
                # print(f"\n{self.__class__.__name__}.signalNameComboBox → current index {index}")
                self.signalNameComboBox.setCurrentIndex(index)
            
    def displayFrame(self):
        """Overloads ScipyenFrameViewer.displayFrame"""
        self._refresh_signalNameComboBox()
        self._refresh_epochComboBox()
        # TODO: 2022-11-10 11:02:17
        # if there is detection in current segment:
        # code to refresh the detected mPSC window 
        #
        
    def loadSettings(self):
        """temporarily bypass non Qt settings - remove when done"""
        self.loadWindowSettings()
    
    def saveSettings(self):
        """temporarily bypass non Qt settings - remove when done"""
        self.saveWindowSettings()
        
    def clear(self):
        if isinstance(self._ephysViewer_,sv.SignalViewer):
            self._ephysViewer_.clear()
            self._ephysViewer_.setVisible(False)
        self._waveFormViewer_.clear()
        self._waveFormViewer_.setVisible(False)
        self._detected_mPSCViewer_.clear()
        self._detected_mPSCViewer_.setVisible(False)
        self._cached_detection_ = None
        self._mPSC_detected_ = False
        # self._detection_epoch_name_ = None
        self._detection_signal_name_ = None
        
        self._data_ = None
        self._data_var_name_ = None
        self._data_frames_ = 0
        self._frameIndex_ = []
        self._number_of_frames_ = 0
        
        self._mPSC_model_waveform_ = None
        self._mPSC_template_ = None
        self._template_file_ = self._default_template_file
        
        self._detected_mPSCs_ = None
        self._currentWaveformIndex_ = 0
        self._waveform_frames = 0
        self._frames_spinBoxSlider_.setRange(0, 0)
        self.signalNameComboBox.clear()
        self.epochComboBox.clear()
        self.metaDataWidget.clear()
        self._params_names_ = self._default_params_names_
        self._params_initl_ = self._default_params_initl_
        self._params_lower_ = self._default_params_lower_
        self._params_upper_ = self._default_params_upper_
        self._mPSCduration_ = self._default_duration_
        
    def closeEvent(self, evt):
        # if self._ephysViewer_.isVisible():
        if isinstance(self._ephysViewer_, sv.SignalViewer):
            if self._owns_viewer_:
                self._ephysViewer_.close()
                self._ephysViewer_ = None
            else:
                self._ephysViewer_.refresh()
                
        self._waveFormViewer_.close()
        self._waveFormViewer_= None
        self._detected_mPSCViewer_.close()
        self._detected_mPSCViewer_= None
                
        super().closeEvent(evt)
        
    def _plot_model_(self):
        """Plots mPSC model waveform"""
        if not isinstance(self._waveFormViewer_, sv.SignalViewer):
            self._waveFormViewer_ = sv.SignalViewer(win_title="mPSC waveform", 
                                                    parent=self, configTag="WaveformViewer")
        
        if isinstance(self._mPSC_model_waveform_, neo.AnalogSignal):
            self._waveFormViewer_.view(self._mPSC_model_waveform_)
            
    def _plot_template_(self):
        """Plots mPSC template"""
        if not isinstance(self._waveFormViewer_, sv.SignalViewer):
            self._waveFormViewer_ = sv.SignalViewer(win_title="mPSC waveform", 
                                                    parent=self, configTag="WaveformViewer")
        
        if isinstance(self._mPSC_template_, neo.AnalogSignal):
            self._waveFormViewer_.view(self._mPSC_template_)
            
        
    def _plot_data(self):
        if self._data_ is not None:
            if not isinstance(self._ephysViewer_,sv.SignalViewer):
                self._ephysViewer_ = sv.SignalViewer(win_title=self._winTitle_, parent=self)
                self._owns_viewer_ = True
                
            if self._ephysViewer_.y is None:
                self._ephysViewer_.view(self._data_)
            else:
                self._ephysViewer_.displayFrame()
                
            self._refresh_signalNameComboBox()
            self._refresh_epochComboBox()
            
    def _plot_detected_mPSCs(self):
        if self._result_ is None:
            return
            
    def _get_selected_signal_(self, segment):
        index = self.signalNameComboBox.currentIndex()
        if index in range(len(segment.analogsignals)):
            return segment.analogsignals[index]
        
    def _get_data_segment_(self, index:typing.Optional[int] = None):
        if index is None:
            index = self.currentFrame
            
        if isinstance(self._data_, neo.Block) and index in range(-len(self._data_.segments), len(self._data_.segments)):
            segment = self._data_.segments[index]
            
        elif isinstance(self._data_, (tuple, list)) and index in range(-len(self._data_), len(self._data_)):
            segment = self._data_[index]
            
        elif isinstance(self._data_, neo.Segment):
            segment = self._data_
            
        else:
            return
        
        return segment
    
    def _get_mPSC_template_or_waveform_(self):
        # see NOTE: 2022-11-17 23:37:00 NOTE: 2022-11-11 23:04:37 NOTE: 2022-11-11 23:10:42
        if self._use_template_: # return the cached template if it exists
            if isinstance(self._mPSC_template_, neo.AnalogSignal) and self._mPSC_template_.name == "mPSC Template":
                return self._mPSC_template_
            else: # no template is loaded; get one from custom file or default file, or generate a synthetic waveform
                template_OK = False
                if os.path.isfile(self._custom_template_file_):
                    tpl = pio.loadFile(self._custom_template_file_)
                    if isinstance(tpl, neo.AnalogSignal) and tpl.name == "mPSC Template":
                        self._mPSC_template_ = tpl
                        return self._mPSC_template_
                
                if not template_OK and os.path.isfile(self._template_file_):
                    tpl = pio.loadFile(self._template_file_)
                    if isinstance(tpl, neo.AnalogSignal) and tpl.name == "mPSC Template":
                        self._mPSC_template_ = tpl
                        return self._mPSC_template_
                
                if not template_OK:
                    signalBlocker = QtCore.QSignalBlocker(self.use_mPSCTemplate_CheckBox)
                    self.use_mPSCTemplate_CheckBox.setChecked(False)
                    self._use_template_ = False
                    self._generate_mPSCModelWaveform()
                    return self._mPSC_model_waveform_
                            
        else:
            self._generate_mPSCModelWaveform()
            return self._mPSC_model_waveform_
                    
    def _detect_sweep_(self, segment_index:typing.Optional[int]=None, waveform=None):
        """ Returns a collection of detected mPSCs and the template used
        If nothing was detected returns None, None
        """
        # TODO 2022-11-17 14:15:37
        segment = self._get_data_segment_(segment_index)
        if not isinstance(segment, neo.Segment):
            return
        
        if isinstance(self._data_, neo.Block):
            dstring = f"PSCs detected in {self._data_.name } segment {segment.name}"
        else:
            dstring = f"PSCs detected in segment {segment.name}"
        
        signal = self._get_selected_signal_(segment)
        
        if not isinstance(signal, neo.AnalogSignal):
            return
        
        epochs = [e for e in segment.epochs if e.name in self._detection_epochs_]
        
        start_times = list()
        peak_times  = list()
        mini_waves  = list()
        
        if waveform is None:
            waveform  = self._get_mPSC_template_or_waveform_()
        
        if len(epochs):
            mini_starts = list()
            mini_peaks = list()
            for epoch in epochs:
                sig = signal.time_slice(epoch.times[0], epoch.times[0]+epoch.durations[0])
                detection = membrane.detect_mPSC(sig, waveform)
                if detection is None:
                    continue
                
                template = detection["waveform"]
                mini_waves.extend(detection["minis"])
                mini_starts.append(detection["mini_starts"])
                mini_peaks.append(detection["mini_peaks"])
                if len(mini_starts) and len(mini_starts):
                    start_times = np.hstack(mini_starts) * mini_starts[0].units
                    peak_times = np.hstack(mini_peaks) * mini_peaks[0].units
                    
        else: # no epochs - detect in the whole signal
            detection = membrane.detect_mPSC(signal, waveform)
            if detection is None:
                return None, None
            
            start_times = detection["mini_starts"]
            peak_times  = detection["mini_peaks"]
            mini_waves  = detection["minis"]
            
            template = detection["waveform"]
                    
        if len(start_times):
            if isinstance(template, neo.core.basesignal.BaseSignal) and len(template.description.strip()):
                dstring += f" using {template.description}"
                
            if isinstance(self._data_, neo.Block):
                trname = f"{self._data_.name}_{segment.name}_PSCs"
            else:
                trname = f"{segment.name}_PSCs"
            
            mPSCtrain = neo.SpikeTrain(start_times, t_stop = signal.t_stop, units = signal.times.units,
                                    t_start = signal.t_start, sampling_rate = signal.sampling_rate,
                                    name = trname, description=dstring)
            
            mPSCtrain.annotations["peak_times"] = peak_times
            mPSCtrain.annotations["source"] = "PSC_detection"
            
            if isinstance(template, neo.core.basesignal.BaseSignal):
                mPSCtrain.annotations["PSC_parameters"] = template.annotations["parameters"]
                mPSCtrain.annotations["datetime"] = datetime.datetime.now()
            
            # TODO revisit this design - you may want to avoid fitting.
            # if fit_waves: # fit wave is alwys True for the GUI code 
            model_params = self.paramsWidget.value()
            init_params = tuple(p.magnitude for p in model_params["Initial Value:"])
            lo = tuple(p.magnitude for p in model_params["Lower Bound:"])
            up = tuple(p.magnitude for p in model_params["Upper Bound:"])
            
            for k,w in enumerate(mini_waves):
                fw = membrane.fit_mPSC(w, template.annotations["parameters"], lo=lo, up=up)
                mini_waves[k] = fw
                
            mPSCtrain_waves = np.concatenate([w.magnitude[:,:,np.newaxis] for w in mini_waves], axis=2)
            mPSCtrain.waveforms = mPSCtrain_waves.T
            if self.clearPreviousDetectionCheckBox.isChecked():
                self._clear_events_flag_ = True
                
            # print(f"clear prev {self._clear_events_flag_}")
            if self._clear_events_flag_:
                # remove old spike trains with mPSCs 
                neoutils.remove_spiketrain(segment, mPSCtrain.name)

            segment.spiketrains.append(mPSCtrain)
            
            return mini_waves, template
        
        else:
            return None, None
        
    @pyqtSlot(bool)
    def _slot_useDefaultTemplateLocation(self, val):
        if val:
            self.templateWaveFormFile = self._default_template_file
        else:
            self._slot_choosePersistentTemplateFile()
            
    @pyqtSlot()
    def _slot_detect_sweep(self):
        # refresh the template or waveform
        waveform = self._get_mPSC_template_or_waveform_()
        if waveform is None:
            self.criticalMessage("Detect mPSC in current sweep",
                                 "No mPSC waveform or template is available")
            return
        detection, template = self._detect_sweep_(waveform=waveform)
        self._result_ = (detection, template)
        self._plot_data()
        
        
    @pyqtSlot()
    def _slot_choosePersistentTemplateFile(self):
        targetDir = dirname(self.templateWaveFormFile)
        fn, fl = self.chooseFile("Choose persistent mPSC template file",
                                 fileFilter = ";;".join(["Pickle files (*.pkl)", "HDF5 Files (*.hdf)"]),
                                 single=True,
                                 save=True,
                                 targetDir=targetDir)
        
        if isinstance(fn, str) and len(fn.strip()):
            self.templateWaveFormFile = fn
            
    @pyqtSlot()
    def _slot_plot_mPSCWaveForm(self):
        self._get_mPSC_template_or_waveform_()
        if self._use_template_:
            self._plot_template_()
        else:
            self._plot_model_()
            
    @pyqtSlot(int)
    def _slot_use_mPSCTemplate(self, value):
        # TODO: 2022-11-18 10:12:34 
        # make configurable
        self._use_template_ = value == QtCore.Qt.Checked
        
    @pyqtSlot(int)
    def _slot_set_clear_events_flag_(self, value):
        # TODO: 2022-11-18 10:12:34 
        # make configurable
        self._clear_events_flag_ = value == QtCore.Qt.Checked
        
    @pyqtSlot()
    def _slot_saveEphysData(self):
        fileName, fileFilter = self.chooseFile(caption="Save electrophysiology data",
                                               single=True,
                                               save=True,
                                               fileFilter=";;".join(["Pickle files (*.pkl)", "HDF5 Files (*.hdf)"]))
        if isinstance(fileName, str) and len(fileName.strip()):
            if "HDF5" in fileFilter:
                pio.saveHDF5(self._data_, fileName)
            else:
                pio.savePickleFile(self._data_, fileName)
            
    @pyqtSlot()
    def _slot_openEphysDataFile(self):
        fileName, fileFilter = self.chooseFile(caption="Open electrophysiology file",
                                               single=True,
                                               save=False,
                                               fileFilter=";;".join(["Axon files (*.abf)", "Pickle files (*.pkl)", "HDF5 Files (*.hdf)"]))
        if isinstance(fileName, str) and os.path.isfile(fileName):
            if "Axon" in fileFilter:
                data = pio.loadAxonFile(fileName)
            elif "HDF5" in fileFilter:
                data = pio.loadHDF5File(fileName)
            elif "Pickle" in fileFilter:
                data = pio.loadPickleFile(fileName)
            else:
                return
                
            self._set_data_(data)
            self.metaDataWidget.dataVarName = os.path.splitext(os.path.basename(fileName))[0]
            name = getattr(self._data_, "name", "")
            self.metaDataWidget.dataName = name
            
            
    @pyqtSlot()
    def _slot_importEphysData(self):
        objs = self.importWorkspaceData([neo.Block, neo.Segment, tuple, list],
                                         title="Import electrophysiology",
                                         single=True,
                                         with_varName=True)
        
        if objs is None:
            return
        
        # NOTE: 2022-11-09 22:28:38
        # since with_varName is set to True in importWorkspaceData, objs is a
        # list of tuples (var_name, var_object)
        # also, since, single is passed as True, we only get one element in objs
        if len(objs) == 1:
            self._set_data_(objs[0][1]) # will raise exception if data is wrong
            self.metaDataWidget.dataVarName = objs[0][0]
            name = getattr(self._data_, "name", "")
            self.metaDataWidget.dataName = name
            
    @pyqtSlot()
    def _slot_exportEphysData(self):
        if self._data_ is not None:
            self.exportDataToWorkspace(self._data_, var_name=self.metaDataWidget.dataVarName)
    
    @pyqtSlot()
    def _slot_plotData(self):
        if self._data_ is not None:
            self._plot_data()
        
    @pyqtSlot(float)
    def _slot_modelDurationChanged(self, val):
        self.mPSCDuration = self.durationSpinBox.value()
        self._plot_model_()
        
    @pyqtSlot(str ,str)
    def _slot_modelParameterChanged(self, row, column):
        if column == "Initial Value:":
            self.mPSCParametersInitial      = self.paramsWidget.parameters["Initial Value:"]
        elif column == "Lower Bound:":
            self.mPSCParametersLowerBounds  = self.paramsWidget.parameters["Lower Bound:"]
        elif column == "Upper Bound:":
            self.mPSCParametersUpperBounds  = self.paramsWidget.parameters["Upper Bound:"]
            
        if not self._use_template_:
            # avoidn unneccessary replots when using the template
            self._plot_model_()
        
        
    @pyqtSlot()
    def _slot_make_mPSCEpoch(self):
        if self._data_ is None:
            return
        
        if isinstance(self._data_, (neo.Block, neo.Segment)) or \
            (isinstance(self, _data_, (tuple, list)) and all(isinstance(s, neo.Segment) for s in self._data_)):
            self._plot_data()
            
            # NOTE: 2022-11-10 23:10:25
            # the call below will emit sig_newEpochInData# from the viewer
            self._ephysViewer_.slot_epochInDataBetweenCursors()
            
    @pyqtSlot()
    def _slot_newEpochGenerated(self):
        "Necessary to capture Epoch creation directly in the viewer"
        self._refresh_epochComboBox()
        
    @pyqtSlot(int)
    def _slot_newSignalViewerAxisSelected(self, index:int):
        # print(f"{self.__class__.__name__}._slot_newSignalViewerAxisSelected {index}")
        signalBlocker = QtCore.QSignalBlocker(self.signalNameComboBox)
        self.signalNameComboBox.setCurrentIndex(index)
        
            
    @pyqtSlot(str)
    def _slot_newTargetSignalSelected(self, value):
        self._detection_signal_name_ = value
        seg = self._get_data_segment_()
        if isinstance(seg, neo.Segment):
            sig = self._get_selected_signal_(seg)
            if isinstance(sig, neo.AnalogSignal) and sig.size > 1:
                self.durationSpinBox.units = sig.times.units
        
    
    @pyqtSlot(int)
    def _slot_newTargetSignalIndexSelected(self, value):
        if value in range(len(self._ephysViewer_.axes)):
            signalBlockers = [QtCore.QSignalBlocker(w) for w in (self._ephysViewer_, self.signalNameComboBox)]
            self._ephysViewer_.currentAxis=value
    
    @pyqtSlot(str)
    def _slot_epochComboBoxSelectionChanged(self, value):
        # print(f"_slot_epochComboBoxSelectionChanged value: {value}")
        segment = self._get_data_segment_()
        
        # print(f"_slot_epochComboBoxSelectionChanged segment: {segment.name}")
        
        if not isinstance(segment, neo.Segment):
            return
        
        existing_epoch_names = [e.name for e in segment.epochs]
        # print(f"_slot_epochComboBoxSelectionChanged epoch names: {existing_epoch_names}")
        
        if value == "Select..." and len(existing_epoch_names):
            dialog = ItemsListDialog(parent=self, title="Select epoch(s)",
                                     itemsList = existing_epoch_names,
                                     selectmode=QtWidgets.QAbstractItemView.ExtendedSelection)
            
            # print(f"_slot_epochComboBoxSelectionChanged dialog: {dialog.__class__.__name__}")
            
            ans = dialog.exec()
            
            if ans == QtWidgets.QDialog.Accepted:
                self._detection_epochs_.clear()
                self._detection_epochs_ = [i for i in dialog.selectedItemsText]
            
        elif value in existing_epoch_names:
            # print(f"_slot_epochComboBoxSelectionChanged selected: {value}")
            
            self._detection_epochs_.clear()
            self._detection_epochs_.append(value)
            
        elif value == "None":
            self._detection_epochs_.clear()
            
    @pyqtSlot(int)
    def _slot_setWaveFormIndex(self, value):
        self.currentWaveformIndex = value
        
    @property
    def currentWaveformIndex(self):
        return self._currentWaveformIndex_
    
    @currentWaveformIndex.setter
    def currentWaveformIndex(self, value):
        self._currentWaveformIndex_ = value
        if self._waveFormViewer_.isVisible():
            if isinstance(self._detected_mPSCs_, neo.AnalogSignal):
                self._waveFormViewer_.view(self._detected_mPSCs_)
                self._currentWaveformIndex_ = 0
                
            elif isinstance(self._detected_mPSCs_, (tuple, list)) and all (isinstance(s, neo.AnalogSignal) for s in self._detected_mPSCs_):
                if self._currentWaveformIndex_ in range(len(self._detected_mPSCs_)):
                    self._waveFormViewer_.currentFrame = self._currentWaveformIndex_
        
    @property
    def useTemplateWaveForm(self):
        return self._use_template_
    
    @markConfigurable("UseTemplateWaveForm")
    @useTemplateWaveForm.setter
    def useTemplateWaveForm(self, value):
        self._use_template_ = value == True
        
    @property
    def templateWaveFormFile(self):
        return self._template_file_
    
    @markConfigurable("TemplateWaveFormFile")
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
    def mPSCDuration(self):
        return self._mPSCduration_
    
    @markConfigurable("mPSC_Duration")
    @mPSCDuration.setter
    def mPSCDuration(self, val):
        self._mPSCduration_ = val
        self.configurable_traits["mPSC_Duration"] = self._mPSCduration_

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
                
