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
# import pyqtgraph as pg
import pandas as pd

from iolib import pictio as pio
import core.neoutils as neoutils
import core.workspacefunctions as wf
import core.signalprocessing as sigp
import core.curvefitting as crvf
import core.models as models

from core.datasignal import DataSignal

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
from gui.itemslistdialog import ItemsListDialog
from gui.workspacegui import (GuiMessages, WorkspaceGuiMixin)
from gui.widgets.modelfitting_ui import ModelParametersWidget
from gui.widgets.spinboxslider import SpinBoxSlider
from gui.widgets.metadatawidget import MetaDataWidget
from gui.widgets import small_widgets
from gui.widgets.small_widgets import QuantitySpinBox
from gui import guiutils
from gui.tableeditor import TableEditor


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
    
    _default_sampling_rate_ = 1e4 * pq.Hz
    
    _default_template_file = os.path.join(os.path.dirname(get_config_file()),"mPSCTemplate.h5" )
    
    def __init__(self, ephysdata=None, clearOldPSCs=False, ephysViewer:typing.Optional[sv.SignalViewer]=None, parent:(QtWidgets.QMainWindow, type(None)) = None, win_title="mPSC Detect", **kwargs):
        # NOTE: 2022-11-05 14:54:24
        # by default, frameIndex is set to all available frames - KISS
        self.threadpool = QtCore.QThreadPool()
        self._toolbars_locked_ = True
        self._clear_detection_flag_ = clearOldPSCs == True
        self._mPSC_detected_ = False
        self._data_var_name_ = None
        
        # NOTE: 2022-11-20 11:36:08
        # For each segment in data, if there are spike trains with mPSC time
        # stamps, store them here - see membrane.batch_mPSC() for how such a 
        # spike train is identified
        # Here, each element in _undo_buffer_ is a possibly empty list of 
        # spike trains (in case detection was run cumulatively, without 
        # replacement). WARNING: this is a plain Python list, NOT a 
        # neo.spiketrainlist.SpikeTrainList (which is the type of the segment's
        # `spiketrains` attribute)
        # self._undo_buffer_ = list()
        
        # Holds only one round of undos
        # this list hasone element for each segment in data.
        # When detection is performed in a segment, any PSC_detection spiketrain 
        # that exists in the segment is copied to the buffer's element 
        # corresponding to that segment, for it to be recalled when an "undo" 
        # operation is triggered
        self._undo_buffer_= list() # FIXME 2022-11-21 17:49:05
        
        
        self._use_template_ = False
        self._mPSC_template_ = None
        
        self._data_ = None
        self._detection_signal_name_ = None
        self._detection_epochs_ = list()
        self._signal_index_ = 0
        
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
        self._detected_mPSCs_ = list()
        self._waveform_frames = 0
        self._currentWaveformIndex_ = 0
        
          # 
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

        # NOTE: 2022-11-10 09:25:48 DO NOT DELETE:
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
        # self._configureUI_ - reimplemented here
        # self.loadSettings - reimplemented here
        # self.setData → self._set_data_, reimplemented here
        # ↓
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
            self._ephysViewer_.sig_newEpochInData.connect(self._slot_newEpochGenerated)
            self._ephysViewer_.sig_axisActivated.connect(self._slot_newSignalViewerAxisSelected)
            self.linkToViewers(self._ephysViewer_)
        else:
            self._init_ephysViewer_()
            
        if self._data_ is not None:
            self._ephysViewer_.plot(self._data_)
            
        # NOTE: 2022-11-05 15:09:59
        # will stay hidden until a waveform (either a mPSC model realisation or 
        # a template mPSC) or a sequence of detetected minis becomes available
        self._waveFormViewer_ = sv.SignalViewer(win_title="mPSC waveform", 
                                                parent=self, configTag="WaveformViewer")
        
        self._waveFormViewer_.sig_closeMe.connect(self._slot_waveFormViewer_closed)
        
        self._detected_mPSCViewer_ = sv.SignalViewer(win_title="Detected mPSCs", 
                                                     parent=self, configTag="mPSCViewer")
        
        self._detected_mPSCViewer_.sig_closeMe.connect(self._slot_detected_mPSCViewer_closed)
        
        self._detected_mPSCViewer_.frameChanged.connect(self._slot_mPSCViewer_frame_changed)
        
        self._reportWindow_ = TableEditor(win_title = "mPSC Detect", parent=self)
        self._reportWindow_.setVisible(False)
        
        self._set_data_(ephysdata)
        
        # self._detectWorker_ = pgui.ProgressThreadWorker(self._detect_all_)
        self._detectController_ = pgui.ProgressThreadController(self._detect_all_)
        self._detectController_.sig_ready.connect(self._slot_detectThread_ready)
        
        # NOTE: 2022-11-05 23:08:01
        # this is inherited from WorkspaceGuiMixin therefore it needs full
        # initialization of WorkspaceGuiMixin instance
        # self._data_var_name_ = self.getDataSymbolInWorkspace(self._data_)
        
        # self.resize(-1,-1)
        
    def _configureUI_(self):
        # print(f"{self.__class__.__name__}._configureUI_ start...")
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
        
        # NOTE: assign config values in loadSettings, not here
        # self.paramsWidget.setParameters(self._params_initl_,
        #                                 lower = self._params_lower_,
        #                                 upper = self._params_upper_,
        #                                 names = self._params_names_,
        #                                 refresh = True)
        
        self.paramsWidget.spinStep = 1e-4
        self.paramsWidget.spinDecimals = 4
        
        self.paramsWidget.sig_parameterChanged[str, str].connect(self._slot_modelParameterChanged)
        self.paramsWidget.sig_badBounds[str].connect(self._slot_badBounds)
        self.paramsWidget.sig_infeasible_x0[str].connect(self._slot_infeasible_x0s)
        
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
        self.actionOpenEphysData.triggered.connect(self._slot_openEphysDataFile)
        self.actionImportEphysData.triggered.connect(self._slot_importEphysData)
        self.actionSaveEphysData.triggered.connect(self._slot_saveEphysData)
        self.actionExportEphysData.triggered.connect(self._slot_exportEphysData)
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
        self.actionDetect_in_current_sweep.triggered.connect(self._slot_detectCurrentSweep)
        # self.actionValidate_in_current_sweep.triggered.connect(self._slot_validateSweep)
        self.actionUndo_current_sweep.triggered.connect(self._slot_undoCurrentSweep)
        
        # self.actionDetect.triggered.connect(self._slot_detect)
        # TODO/FIXME 2022-11-26 09:10:33 for testing
        self.actionDetect.triggered.connect(self._slot_detect_thread_)
        
        # self.actionValidate
        self.actionUndo.triggered.connect(self._slot_undoDetection)
        self.actionView_results.triggered.connect(self.slot_showReportWindow)
        self.actionSave_results.triggered.connect(self._slot_saveResults)
        self.actionExport_results.triggered.connect(self._slot_exportPSCresult)
        self.actionSave_mPSC_trains.triggered.connect(self._slot_savePSCtrains)
        self.actionExport_mPSC_trains.triggered.connect(self._slot_exportPSCtrains)
        self.actionSave_mPSC_waves.triggered.connect(self._slot_savePSCwaves)
        self.actionExport_mPSC_waves.triggered.connect(self._slot_exportPSCwaves)
        self.actionClear_results.triggered.connect(self._slot_clearResults)
        self.actionUse_default_location_for_persistent_mPSC_template.toggled.connect(self._slot_useDefaultTemplateLocation)
        self.actionChoose_persistent_mPSC_template_file.triggered.connect(self._slot_choosePersistentTemplateFile)
        self.actionLock_toolbars.setChecked(self._toolbars_locked_ == True)
        self.actionLock_toolbars.triggered.connect(self._slot_lockToolbars)
        # signal & epoch comboboxes
        self.signalNameComboBox.currentTextChanged.connect(self._slot_newTargetSignalSelected)
        self.signalNameComboBox.currentIndexChanged.connect(self._slot_newTargetSignalIndexSelected)
        self.epochComboBox.currentTextChanged.connect(self._slot_epochComboBoxSelectionChanged)
        # self.epochComboBox.currentIndexChanged.connect(self._slot_new_mPSCEpochIndexSelected)
        
        self.use_mPSCTemplate_CheckBox.setChecked(self._use_template_ == True)
        self.use_mPSCTemplate_CheckBox.stateChanged.connect(self._slot_use_mPSCTemplate)
        
        self.clearPreviousDetectionCheckBox.setChecked(self._clear_detection_flag_ == True)
        self.clearPreviousDetectionCheckBox.stateChanged.connect(self._slot_setClearDetectionFlag_)
        
        self.plot_mPSCWaveformPushButton.clicked.connect(self._slot_plot_mPSCWaveForm)
        
        self.durationSpinBox.setValue(self._mPSCduration_)
        
        if self._toolbars_locked_:
            for toolbar in (self.mainToolBar, self.detectionToolBar):
                toolbar.setFloatable(not self._toolbars_locked_)
                toolbar.setMovable(not self._toolbars_locked_)
                
        self.metaDataWidget.sig_valueChanged.connect(self._slot_metaDataChanged)
        
        self.accept_mPSCcheckBox.setEnabled(False)
        self.accept_mPSCcheckBox.stateChanged.connect(self._slot_set_mPSC_accept)
        # self.reFitPushButton.clicked.connect(self._slot_refit_mPSC)
        
        # print(f"{self.__class__.__name__}._configureUI_ end...")
        
    def loadSettings(self):
        """Overrides ScipyenViewer.loadSettings
        Applies values from config to correspondong widgets.
        """
        # NOTE: 2022-11-25 08:54:43
        # call this method AFTER _configureUI_
        
        # NOTE: 2022-11-25 08:55:10
        # below call the superclass method to kickoff loading of window settings
        # (Qt configurables)
        super(WorkspaceGuiMixin, self).loadSettings()
        
        # asign values to input widgets, but first block any signal they might
        # emit
        ww = (self.paramsWidget, 
              self.durationSpinBox,
              self.clearPreviousDetectionCheckBox,
              self.use_mPSCTemplate_CheckBox)
        
        sigblock = [QtCore.QSignalBlocker(w) for w in ww]
        
        # 1) assign values from config to paramsWidget
        # p0 = self.mPSCParametersInitial
        # l0 = self.mPSCParametersLowerBounds
        # u0 = self.mPSCParametersUpperBounds
        # names, values = zip(*[(k,v) for k,v in p0.items()])
        # lower, upper = zip(*[(l0[k], u0[k]) for k in names])
#         
#         plu = {"Initial Value:":values, "Lower Bound:":lower, "Upper Bound:": upper}
#         
#         df = pd.DataFrame(plu, index = names)
        # self.paramsWidget.parameters = df
        # print(f"{self.__class__}.loadSettings:")
        # print(f"\t_params_initl_ = {self._params_initl_}")
        # print(f"\t_params_lower_ = {self._params_lower_}")
        # print(f"\t_params_upper_ = {self._params_upper_}")
        # print(f"\t_params_names_ = {self._params_names_}")
        self.paramsWidget.setParameters(self._params_initl_,
                                        lower = self._params_lower_,
                                        upper = self._params_upper_,
                                        names = self._params_names_,
                                        refresh = True)
        
        
        # 2) assign model duration from config
        self.durationSpinBox.setValue(self._mPSCduration_)
        
        # 3) set check boxes
        self.use_mPSCTemplate_CheckBox.setChecked(self._use_template_ == True)
        self.clearPreviousDetectionCheckBox.setChecked(self._clear_detection_flag_ == True)
        
    def _set_data_(self, *args, **kwargs):
        # called by super() initializer; 
        # UI widgets not yet initialized
        if len(args):
            data = args[0]
        else:
            data = kwargs.pop("data", None)
            
        if neoutils.check_ephys_data_collection(data): # and self._check_supports_parameter_type_(data):
            if isinstance(data, neo.Block):
                self._undo_buffer_ = [None for s in data.segments]
                self._result_ = [None for s in data.segments]
                # for k,s in enumerate(data.segments):
                #     # NOTE: 2022-11-20 11:54:02
                #     # store any existing spike trains with PSC time stamps
                #     # as a list, at the corresponding element in self._undo_buffer_
                #     # If there are none, just append an empty list to the cache!!!
                #     self._undo_buffer_[k] = self._get_previous_detection_(s)
                    
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
                
                # for k, segment in enumerate(self._data_.segments):
                #     self._result_[k] = self._get_previous_detection_(segment)
                            
            elif isinstance(data, neo.Segment):
                self._undo_buffer_ = [None]
                self._result_ = [None]
                if len(data.analogsignals):
                    time_units = data.analogsignals[0].times.units
                else:
                    time_units = pq.s
                    
                self.durationSpinBox.units = time_units
                
                self._data_ = data
                self._data_frames_ = 1
                self._frameIndex_ = range(self._data_frames_)
                self._number_of_frames_ = len(self._frameIndex_)
                # self._result_ = [self._get_previous_detection_(segment)]
                
            elif isinstance(data, (tuple, list)) and all(isinstance(v, neo.Segment) for v in data):
                self._undo_buffer_ = [None for s in data]
                self._result_ = [None for s in data]
                            
                if len(data[0].analogsignals):
                    time_units = data[0].analogsignals[0].times.units
                else:
                    time_units = pq.s
                    
                self.durationSpinBox.units = time_units
                self._data_ = data
                self._data_frames_ = len(self._data_)
                self._frameIndex_ = range(self._data_frames_)
                self._number_of_frames_ = len(self._frameIndex_)
                
                # for k,s in enumerate(self._data_):
                #     self._result_[k] = self._get_previous_detection_(s)
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
        
        description = getattr(self._data_, "desccription", "")
        
        self.metaDataWidget.dataDescription = description
        
        self._frames_spinBoxSlider_.setRange(0, self._number_of_frames_)
        
        self._plot_data()
        
        # self._frames_spinBoxSlider_
        
        # NOTE: 2022-11-05 23:52:11
        # self._ephysViewer_ is not yet available when _set_data_ is called from __init__()
        if isinstance(self._ephysViewer_, sv.SignalViewer):
            self._ephysViewer_.view(self._data_)
            
    def _generate_mPSCModelWaveform(self):
        if self.mPSCDuration is pd.NA or (isinstance(self.mPSCDuration, pq.Quantity) and self.mPSCDuration.magnitude <= 0):
            return
        
        segment = self._get_data_segment_()
        
        if isinstance(segment, neo.Segment):
            signal = self._get_selected_signal_(segment)
            if isinstance(signal, neo.AnalogSignal) and signal.size > 1:
                sampling_rate = signal.sampling_rate
            else:
                sampling_rate = self._default_sampling_rate_
        else:
            sampling_rate = self._default_sampling_rate_
        
        # NOTE: 2022-11-19 12:14:44
        # there should be no need to notify the user that the generated model
        # PSC waveform might have a different sampling rate than the signal 
        # where PSC are supposed to be detected; the model waveform is (re)created
        # every time we start a detection, using the signal;
        #
        # FIXME? there are two issues with the approach outlined above:
        #
        # 1. if the generated model waveform is saved to disk then used as a 
        #   template in another session - this is the same potential problem 
        #   with any template use → should check that the template sampling_rate
        #   matched that of the signal where the detection is done !!!
        #
        # 2. if the signals from a COLLECTION of segments do not have the 
        #   same sampling rate (technically this is possible, although unlikely
        #   to have occurred during an experiment, but rather when signals from
        #   separate/independent recordings with different sampling rates were 
        #   collected manually in one data block -  a contrived situation)
        #   
        #   In this case we need to notify the user that the template sampling
        #   rate does not match that of the signal where the detection is done,
        #   therefore the detection cannot continue.
        
        
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
        
        segment_epoch_names = [e.name for e in segment.epochs]
        epochnames = ["None"] + segment_epoch_names + ["Select..."]
        signalBlocker = QtCore.QSignalBlocker(self.epochComboBox)
        self.epochComboBox.clear()
        self.epochComboBox.addItems(epochnames)
        if len(self._detection_epochs_) == 1:
            if self._detection_epochs_[0] in segment_epoch_names:
                ndx = segment_epoch_names.index(self._detection_epochs_[0])
                self.epochComboBox.setCurrentIndex(ndx+1)
        
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
            if index in range(len(signames)) and index in range(len(segment.analogsignals)):
                # print(f"\n{self.__class__.__name__}.signalNameComboBox → current index {index}")
                self.signalNameComboBox.setCurrentIndex(index)
                self._signal_index_ = index
                
    def displayDetectedWaveform(self, index:int):
        self.currentWaveformIndex = index
        
        if isinstance(self._detected_mPSCViewer_, sv.SignalViewer):
            self._detected_mPSCViewer_.currentFrame = index
            self._indicate_mPSC_(self.currentWaveformIndex)
        
            
    def displayFrame(self):
        """Overloads ScipyenFrameViewer.displayFrame"""
        self._refresh_signalNameComboBox()
        self._refresh_epochComboBox()
        self._ephysViewer_.currentFrame = self.currentFrame
        
        self._detected_mPSCs_.clear()
        
        if self.currentFrame in range(-len(self._result_), len(self._result_)):
            frameResults = self._result_[self.currentFrame]
            # print(frameResults)
        
            if isinstance(frameResults, (tuple, list)) and len(frameResults) == 2:
                if isinstance(frameResults[1], (tuple, list)) and all(isinstance(s, neo.AnalogSignal) for s in frameResults[1]):
                    self._detected_mPSCs_ = frameResults[1]
            
        self._plot_detected_mPSCs()
        
    def clear(self):
        if isinstance(self._ephysViewer_,sv.SignalViewer):
            self._ephysViewer_.clear()
            self._ephysViewer_.close()
            self._ephysViewer_ = None
            
        if isinstance(self._waveFormViewer_,sv.SignalViewer):
            self._waveFormViewer_.clear()
            self._waveFormViewer_.close()
            self._waveFormViewer_ = None
            
        if isinstance(self._detected_mPSCViewer_,sv.SignalViewer):
            self._detected_mPSCViewer_.clear()
            self._detected_mPSCViewer_.close()
            self._detected_mPSCViewer_ = None
        self._undo_buffer_ = list()
        self._mPSC_detected_ = False
        self._detection_signal_name_ = None
        
        self._data_ = None
        self._data_var_name_ = None
        self._data_frames_ = 0
        self._frameIndex_ = []
        self._number_of_frames_ = 0
        
        self._mPSC_model_waveform_ = None
        self._mPSC_template_ = None
        self._template_file_ = self._default_template_file
        
        self._detected_mPSCs_ = list()
        self._result_ = list()
        self._undo_buffer_ = list()
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
                self._ephysViewer_.clear()
                self._ephysViewer_.close()
                self._ephysViewer_ = None
            else:
                self._ephysViewer_.refresh()
                
        if isinstance(self._waveFormViewer_, sv.SignalViewer):
            self._waveFormViewer_.clear()
            self._waveFormViewer_.close()
            
        self._waveFormViewer_= None
        
        if isinstance(self._detected_mPSCViewer_, sv.SignalViewer):
            self._detected_mPSCViewer_.clear()
            self._detected_mPSCViewer_.close()
            
        self._detected_mPSCViewer_= None
        
        # this one is also supposed to call saveSettings()
        super().closeEvent(evt)
        
    def _plot_model_(self):
        """Plots mPSC model waveform"""
        if not isinstance(self._waveFormViewer_, sv.SignalViewer):
            self._waveFormViewer_ = sv.SignalViewer(win_title="mPSC waveform", 
                                                    parent=self, configTag="WaveformViewer")
            self._waveFormViewer_.sig_closeMe.connect(self._slot_waveFormViewer_closed)
            
        waveform = self._get_mPSC_template_or_waveform_()
        
        if isinstance(waveform, (neo.AnalogSignal, DataSignal)):
            self._waveFormViewer_.view(waveform)
            
    def _plot_template_(self):
        """Plots mPSC template"""
        if not isinstance(self._waveFormViewer_, sv.SignalViewer):
            self._waveFormViewer_ = sv.SignalViewer(win_title="mPSC waveform", 
                                                    parent=self, configTag="WaveformViewer")
        
            self._waveFormViewer_.sig_closeMe.connect(self._slot_waveFormViewer_closed)

        if isinstance(self._mPSC_template_, neo.AnalogSignal):
            self._waveFormViewer_.view(self._mPSC_template_)
            
    def _init_ephysViewer_(self):
        self._ephysViewer_ = sv.SignalViewer(win_title=self._winTitle_, 
                                                parent=self, configTag="DataViewer")
        self._owns_viewer_ = True
        self._ephysViewer_.sig_closeMe.connect(self._slot_ephysViewer_closed)
        self._ephysViewer_.sig_newEpochInData.connect(self._slot_newEpochGenerated)
        self._ephysViewer_.sig_axisActivated.connect(self._slot_newSignalViewerAxisSelected)
        self.linkToViewers(self._ephysViewer_)
        
        
        
    def _plot_data(self):
        if self._data_ is not None:
            if not isinstance(self._ephysViewer_,sv.SignalViewer):
                self._init_ephysViewer_()
                
            self._ephysViewer_.view(self._data_)
            self._ephysViewer_.currentFrame = self.currentFrame
                
            self._refresh_signalNameComboBox()
            self._refresh_epochComboBox()
            
            self._plot_detected_mPSCs()
            
    def _plot_detected_mPSCs(self):
        # print(f"{self.__class__.__name__}._plot_detected_mPSCs")
        frameResult = self._result_[self.currentFrame]
        signalBlockers = (QtCore.QSignalBlocker(w) for w in (self._mPSC_spinBoxSlider_,
                                                            self.accept_mPSCcheckBox))
        if isinstance(frameResult, (tuple, list)):
            # WARNING: 2022-11-22 17:46:17
            # make sure self._detected_mPSCs_ is not a mere reference
            # to the list in frameResult! Create a NEW list !
            # self._detected_mPSCs_ = [neoutils.set_relative_time_start(s) for s in frameResult[1]]
            # self._detected_mPSCs_ = [s for s in frameResult[1]]
            self._detected_mPSCs_ = frameResult[1]
            
            if not isinstance(self._detected_mPSCViewer_, sv.SignalViewer):
                self._detected_mPSCViewer_ = sv.SignalViewer(win_title="Detected mPSCs", 
                                                            parent=self, configTag="mPSCViewer")

                self._detected_mPSCViewer_.sig_closeMe.connect(self._slot_detected_mPSCViewer_closed)

                self._detected_mPSCViewer_.frameChanged.connect(self._slot_mPSCViewer_frame_changed)
                
            # print(len(self._detected_mPSCs_))
            self._mPSC_spinBoxSlider_.setRange(0, len(self._detected_mPSCs_)-1)
            self._detected_mPSCViewer_.view(self._detected_mPSCs_)
            
            self.accept_mPSCcheckBox.setEnabled(True)
            self._indicate_mPSC_(self._detected_mPSCViewer_.currentFrame)
            
            
        else:
            if isinstance(self._detected_mPSCViewer_, sv.SignalViewer):
                self._mPSC_spinBoxSlider_.setRange(0, 0)
                self.accept_mPSCcheckBox.setEnabled(False)
                self._detected_mPSCViewer_.clear()
                
            if isinstance(self._ephysViewer_, sv.SignalViewer):
                self._ephysViewer_.removeTargetsOverlay(self._ephysViewer_.axes[self._signal_index_])
        
            
        # self._detected_mPSCViewer_.docTitle = "mPSCs"
            
        # self._indicate_mPSC_(self._detected_mPSCViewer_.currentFrame)
        
    def _indicate_mPSC_(self, waveindex):
        # print(f"_indicate_mPSC_ wave {waveindex} of {len(self._detected_mPSCs_)} waves")
        if not isinstance(self._ephysViewer_, sv.SignalViewer):
            return
        
        # self._detected_mPSCs_ = self._result_[self.currentFrame]
        
        if len(self._detected_mPSCs_) == 0:
            return
        
        
        segment = self._get_data_segment_()
        signal = segment.analogsignals[self._signal_index_]
        axis = self._ephysViewer_.axes[self._signal_index_]
        
        if waveindex not in range(-len(self._detected_mPSCs_),len(self._detected_mPSCs_)):
            waveindex = 0
        
        mPSC = self._detected_mPSCs_[waveindex]
        
        peak_time = mPSC.annotations.get("t_peak", None)
        
        waveR2 = mPSC.annotations["mPSC_fit"]["Rsq"]
        
        if mPSC.annotations.get("Accept", False):
            wavelabel = "R²=%.2f Accept" % waveR2
        else:
            wavelabel = "R²=%.2f Reject" % waveR2
            
        waxis = self._detected_mPSCViewer_.axis(0)
        self._detected_mPSCViewer_.removeLabels(waxis)
        [[x0,x1], [y0,y1]]  = waxis.viewRange()
        
        self._detected_mPSCViewer_.addLabel(wavelabel, 0, pos = (x0,y1), 
                                            color=(0,0,0), anchor=(0,1))
                
        # print(f"peak_time {peak_time}")
        
        if isinstance(self._mPSC_model_waveform_, neo.core.basesignal.BaseSignal):
            upward = sigp.is_positive_waveform(self._mPSC_model_waveform_)
        elif isinstance(self._mPSC_template_, neo.core.basesignal.BaseSignal):
            upward = sigp.is_positive_waveform(self._mPSC_template_)
        else:
            upward = False
        
        targetSize = 15
        # NOTE: 2022-11-23 21:47:29
        # below, the offset of the label to its target is given as (x,y) with
        # x positive left → right
        # y positive bottom → top (like the axis)
        targetLabelOffset = (0, -20) if upward else (0, 20)
        
        if isinstance(peak_time, pq.Quantity):
            peak_value = neoutils.get_sample_at_domain_value(signal, peak_time)
            self._ephysViewer_.removeTargetsOverlay(axis)
            valid = mPSC.annotations.get("Accept", False) == True
            signalBlocker = QtCore.QSignalBlocker(self.accept_mPSCcheckBox)
            self.accept_mPSCcheckBox.setChecked(valid)
            if valid:
                targetBrush = (255,0,0,50)
                targetLabelColor = (128,0,0,255)
            else:
                targetBrush = (0,0,255,50)
                targetLabelColor = (0,0,128,255)
                
            self._ephysViewer_.overlayTargets((float(peak_time),float(peak_value)),
                                                axis=axis, size=targetSize, 
                                                movable=False,
                                                brush=targetBrush, 
                                                label=f"{waveindex}",
                                                labelOpts = {"color":targetLabelColor,
                                                             "offset":targetLabelOffset})
            self._ephysViewer_.refresh()
       
    def _clear_detection_in_sweep_(self, segment:neo.Segment):
        mPSCtrains = [s for s in segment.spiketrains if s.annotations.get("source", None) == "PSC_detection"]
        for s in mPSCtrains:
            neoutils.remove_spiketrain(segment, s.name)
        
    def _get_previous_detection_(self, segment:neo.Segment):
        """ Checks if there are any PSC_detection spike trains in the segment
            Returns a (possibly empty) list of neo.SpikeTrain; not to be
            confused with a neo.SpikeTrainList.
        """
        if not isinstance(segment, neo.Segment):
            raise TypeError(f"Expecting a neo.Segment; got {type(segment).__name__} instead")
        
        mPSCtrains = [s for s in segment.spiketrains if s.annotations.get("source", None) == "PSC_detection"]
        
        if len(mPSCtrains):
            peak_times = mPSCtrains[0].annotations.get("peak_times", list())
            accepted = mPSCtrains[0].annotations.get("Accept", list())
            template = mPSCtrains[0].annotations.get("Template", list())
            
            if len(peak_times) == 0: # invalid data, so discard everything
                return
            
            signal_units = mPSCtrains[0].annotations.get("signal_units", None)
            
            if signal_units is None: # invalid data, so discard everything
                return
            mPSCtrain = mPSCtrains[0]
            if len(mPSCtrains)> 1:
                for s in mPSCtrains[1:]:
                    ptimes = s.annotations.get("peak_times", list())
                    if len(ptimes) == 0:
                        return
                    su = s.annotations.get("signal_units", None)
                    if su is None or su != signal_units:
                        return
                    
                    peak_times.extend(ptimes)
                    accpt = s.annotations.get("Accept", list())
                    accepted.extend(accpt)
                    tmpl = s.annotations.get("Template", list())
                    template.extend(tmpl)
                    
                    
                # NOTE:2022-11-22 12:48:54
                # collapse (merge) all mPSC spike trains in one, 
                # replace them with the merged result
                # WARNING there is no checking for duplicate time stamps !!!
                mPSCtrain = mPSCtrain.merge(mPSCtrains[1:])
                mPSCtrain.annotations["source"] = "PSC_detection"
                mPSCtrain.annotations["peak_times"] = peak_times
                mPSCtrain.annotations["signal_units"] = signal_units
                mPSCtrain.annotations["Accept"] = accepted
                mPSCtrain.annotations["Template"] = template
                
                for t in mPSCtrains[1:]:
                    neoutils.remove_spiketrain(segment, t.name)
        else:
            return None
                
        waves = mPSCtrain.waveforms
        # print(waves.shape)
        signal_units = mPSCtrain.annotations.get("signal_units", pq.pA)
        mini_waves = list()
        if waves.size > 0:
            for k in range(waves.shape[0]): # spike #
                wave = neo.AnalogSignal(waves[k,:,:],
                                        t_start = mPSCtrain[k],
                                        units = signal_units,
                                        sampling_rate = mPSCtrain.sampling_rate)
                wave.annotations["Accept"] = True
                mini_waves.append(wave)
            
        return (mPSCtrain, mini_waves)
        
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
    
    def _get_mPSC_template_or_waveform_(self, use_template:typing.Optional[bool]=None):
        # see NOTE: 2022-11-17 23:37:00 NOTE: 2022-11-11 23:04:37 NOTE: 2022-11-11 23:10:42
        if use_template is None:
            use_template = self._use_template_
            
        if use_template: # return the cached template if it exists
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
        
    def _cache_sweep_detection_(self, segment_index:typing.Optional[int]=None):
        if segment_index is None:
            segment_index = self.currentFrame
            
        
        
    def _detect_all_(self, waveform:typing.Optional[typing.Union[neo.AnalogSignal, DataSignal]]=None, **kwargs):
        """Detects mPSCs in all sweeps
        
        Parameters:
        ==========
        waveform: neo.AnalogSignal, DataSignal, or None
                    The model PSC or template (optional, default is None )
        
        Var-keyword parameters:
        =======================
        NOTE: These do not need to be passed explicitly to the call; tyipically
        they are supplied by an instance of pictgui.ProgressRunnableWorker.
        
        progressSignal: PyQt signal that will be emitted with each iteration
        
        progressUI: QtProgressDialog or None
        
        
        """
        if self._data_ is None:
            return
        
        progressSignal = kwargs.pop("progressSignal", None)
        setMaxSignal = kwargs.pop("setMaxSignal", None)
        progressUI = kwargs.pop("progressDialog", None)
        
        if waveform is None:
            waveform  = self._get_mPSC_template_or_waveform_()
            
        # make sure we have a clean slate in self._result_
        # any prev detection is to be stored in self._undo_buffer_
        # for k in self._result_:
        #     self._result_[k] = None

        for frame in self._frameIndex_: # NOTE: _frameIndex_ is in inherited from ScipyenFrameViewer
            segment = self._get_data_segment_(frame)
            prev_detect = self._get_previous_detection_(segment)
            self._undo_buffer_[frame] = prev_detect
            res = self._detect_sweep_(frame, waveform=waveform)
            if res is None:
                continue
            mPSCtrain, detection = res
            self._result_[frame] = (mPSCtrain, [s for s in detection])
            
            if self.clearPreviousDetectionCheckBox.isChecked():
                self._clear_detection_flag_ = True # to make sure this is up to date
                self._clear_detection_in_sweep_(segment)
                
            segment.spiketrains.append(mPSCtrain)
            
            if progressSignal is not None:
                progressSignal.emit(frame)
                
            # FIXME 2022-11-23 00:36:58
            # use the two-part model with QThread instead of QRunnable
            if hasattr(progressUI, "wasCanceled"):
                cncl = progressUI.wasCanceled()
                if cncl:
                    print("Aborted")
                    
                    return
                
        
        
    def _undo_sweep(self, segment_index:typing.Optional[int]=None):
        if segment_index is None:
            segment_index = self.currentFrame
            
        segment = self._get_data_segment_(segment_index)
        
        # clear detection results in the sweep; restore from undo buffer if present
        self._clear_detection_in_sweep_(segment)
        
        if segment_index not in range(-len(self._undo_buffer_), len(self._undo_buffer_)):
            return
        
        
        # restore the spiketrains as a spiketrainlist containing the current 
        # non-PSC-detection spike trains and whatever is stored in the cache 
        # for the current segment (ie., at segmentIndex = currentFrame index)
        
        prev_detect = self._undo_buffer_[segment_index]
            
        if isinstance(prev_detect, (tuple, list)):
            if len(prev_detect) == 2:
                if isinstance(prev_detect[0], neo.SpikeTrain) and prev_detect[0].annotations.get("source", None) == "PSC_detection":
                    segment.spiketrains.append(prev_detect[0])
          
        # also clear the result (if it exists)
        if segment_index in range(-len(self._result_), len(self._result_)):
            self._result_[segment_index] = None
            
    def _update_report_(self):
        if self._data_ is None:
            return
        
        results = self.result() 
        
        if results is None:
            return
        
        resultsDF = results[0]
        
        self._reportWindow_.view(resultsDF, doc_title = f"{self._data_.name} Results")
        self._reportWindow_.show()
        
        
                    
    def _detect_sweep_(self, segment_index:typing.Optional[int]=None, waveform=None):
        """ mPSC detection in a segment (a.k.a a sweep)
        
        Returns a tuple containing :
        • a spiketrain
        • a list of detected mPSC waveforms,
        
        If nothing was detected returns None.
        
        When detection was successful:
        • the spike train contains:
            ∘ timestamps of the onset of the detected mPSC waves
            ∘ associated mPSC waveform at the timestamp
        
        • the mPSC waveforms list contains the detected mPSCs.
        
            This one is for convenience, as the waveforms are also embedded in 
            the spike train described above. However, the embedded waveforms are 
            stored as a 3D numpy array, whereas in this list they are stored as 
            individual neo.AnalogSignal objects (with annotations) useful for 
            the validation process.
        
        NOTE For developers:
        The function is called by 
        • triggering `actionDetect_in_current_sweep` with the parameter `segment_index` 
            set to the value of `self.currentFrame`.
        • triggering `actionDetect` in a loop over all segments (with `segment_index`
            parameter set inside the loop)
        
        
        """
        
        # NOTE: 2022-11-22 08:57:22
        # • returns a spiketrain, a detection dict and the waveform used in detection
        # • does NOT ember the spiketrain in the analysed segment anymore - this 
        #   should be done in the caller, as necessary
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
                return
            
            start_times = detection["mini_starts"]
            peak_times  = detection["mini_peaks"]
            mini_waves  = detection["minis"]
            
            template = detection["waveform"]
            
        # NOTE: 2022-11-20 11:33:43
        # set this here
        if isinstance(self._data_, neo.Block):
            trname = f"{self._data_.name}_{segment.name}_PSCs"
        else:
            trname = f"{segment.name}_PSCs"
        
        if len(start_times):
            if isinstance(template, neo.core.basesignal.BaseSignal) and len(template.description.strip()):
                dstring += f" using {template.description}"
                
            mPSCtrain = neo.SpikeTrain(start_times, t_stop = signal.t_stop, units = signal.times.units,
                                    t_start = signal.t_start, sampling_rate = signal.sampling_rate,
                                    name = trname, description=dstring)
            
            mPSCtrain.annotations["peak_times"] = peak_times
            mPSCtrain.annotations["source"] = "PSC_detection"
            mPSCtrain.annotations["signal_units"] = signal.units
            
            if isinstance(template, neo.core.basesignal.BaseSignal):
                mPSCtrain.annotations["PSC_parameters"] = template.annotations["parameters"]
                mPSCtrain.annotations["datetime"] = datetime.datetime.now()
            
            # TODO revisit this design - you may want to avoid fitting.
            # if fit_waves: # fit wave is alwys True for the GUI code 
            model_params = self.paramsWidget.value()
            init_params = tuple(p.magnitude for p in model_params["Initial Value:"])
            lo = tuple(p.magnitude for p in model_params["Lower Bound:"])
            up = tuple(p.magnitude for p in model_params["Upper Bound:"])
            
            accepted = list()
            templates = list()
            
            for k,w in enumerate(mini_waves):
                # FIXME: 2022-11-25 00:50:11
                # when template is NOt a model where are the params taken from?
                fw = membrane.fit_mPSC(w, init_params, lo=lo, up=up)
                # fw = membrane.fit_mPSC(w, template.annotations["parameters"], lo=lo, up=up)
                fw.annotations["t_peak"] = mPSCtrain.annotations["peak_times"][k]
                fw.name = f"mPSC_{fw.name}_{k}"
                mini_waves[k] = fw
                accepted.append(fw.annotations["Accept"])
                templates.append(fw.annotations["mPSC_fit"]["template"])
                
            mPSCtrain_waves = np.concatenate([w.magnitude[:,:,np.newaxis] for w in mini_waves], axis=2)
            mPSCtrain.waveforms = mPSCtrain_waves.T
            mPSCtrain.annotations["Accept"] = accepted
            mPSCtrain.annotations["Template"] = templates
            
            return mPSCtrain, mini_waves
        
    @pyqtSlot(str)
    def _slot_badBounds(self, param):
        self.errorMessage("Model Parameters", f"Lower bound > upper bound for {param}")
        
    @pyqtSlot(str)
    def _slot_infeasible_x0s(self, param):
        self.errorMessage("Model Parameters", f"Initial value for {param} infeasible")
        
    @pyqtSlot(bool)
    def _slot_useDefaultTemplateLocation(self, value):
        if value:
            self.templateWaveFormFile = self._default_template_file
        else:
            self._slot_choosePersistentTemplateFile()
            
#     @pyqtSlot()
#     def _slot_validateSweep(self):
#         segment = self._get_data_segment_()
#         if not isinstance(segment, neo.Segment):
#             return
#         
#         if self.currentFrame in range(-len(self._result_), len(self._result_)):
#             frameResults = self._result_[self.currentFrame]
#             
#             if isinstance(frameResults, (tuple, list)) and len(frameResults)== 2:
#                 waves = frameResults[1]
                
            
            
    @pyqtSlot()
    def _slot_detectCurrentSweep(self):
        # refresh the template or waveform
        waveform = self._get_mPSC_template_or_waveform_()
        if waveform is None:
            self.criticalMessage("Detect mPSC in current sweep",
                                 "No mPSC waveform or template is available")
            return
        
        segment = self._get_data_segment_(index=self.currentFrame)
        
        if isinstance(segment, neo.Segment):
            prev_detect = self._get_previous_detection_(segment) # tuple(spike trains, minis) or None
            
            self._undo_buffer_[self.currentFrame] = prev_detect #
                
            # NOTE: 2022-11-22 08:47:24
            # _detect_sweep_ returns a dict and an AnalogSignal but also has the 
            # side effect of embedding a spiketrain with the event time stamps in
            # the segment.
            detection_result = self._detect_sweep_(waveform=waveform)
            if detection_result is None:
                return
            mPSCtrain, detection = self._detect_sweep_(waveform=waveform)
            # NOTE: 2022-11-22 17:47:15
            # see WARNING: 2022-11-22 17:46:17
            self._result_[self.currentFrame] = (mPSCtrain, [s for s in detection])
            
            if len(detection):
                # NOTE: 2022-11-22 17:47:33
                # see WARNING: 2022-11-22 17:46:17
                self._detected_mPSCs_ = [s for s in detection]
            else:
                self._detected_mPSCs_.clear()
                

            # NOTE: 2022-11-20 11:30:15
            # remove the previous detection if the appropriate widget is checked,
            # REGARDLESS of whether anything was detected this time around, so that
            # the spiketrains reflect the results of the detection with the CURRENT
            # parameters
            if self.clearPreviousDetectionCheckBox.isChecked():
                self._clear_detection_flag_ = True # to make sure this is up to date
                self._clear_detection_in_sweep_(segment)
                
            # embed the spike train in the segment
            segment.spiketrains.append(mPSCtrain)
            
            self._plot_data()
            
    @pyqtSlot()
    def _slot_undoCurrentSweep(self):
        """Restores current segment spiketrains to the state before last detection.
        TODO: update result
        """
        self._undo_sweep(self.currentFrame)
        self._plot_data()
        
    @pyqtSlot()
    def _slot_saveResults(self):
        results = self.result()
        if results is None:
            return
        
        resultsDF, resultsTrains, resultsWaves = results
        
        fn, fl = self.chooseFile("Save mPSC result table",
                                 fileFilter = ";;".join(["Comma-separated values file (*.csv)","Pickle files (*.pkl)", "HDF5 Files (*.hdf)"]),
                                 single=True,
                                 save=True)
        
        if isinstance(fn, str) and len(fn.strip()):
            if fl == "Comma-separated values file (*.csv)":
                resultsDF.to_csv(fn, na_rep = "NA")
                
            elif fl == "Pickle files (*.pkl)":
                pio.savePickleFile(resultsDF, fn)
                
            elif fl == "HDF5 Files (*.hdf)":
                pio.saveHDF5(resultsDF, fn)
             
    @pyqtSlot()
    def _slot_savePSCtrains(self):
        results = self.result()
        if results is None:
            return
        
        resultsDF, resultsTrains, resultsWaves = results
        
        fn, fl = self.chooseFile("Save mPSC trains",
                                 fileFilter = ";;".join(["Pickle files (*.pkl)", "HDF5 Files (*.hdf)"]),
                                 single=True,
                                 save=True)
        
        if isinstance(fn, str) and len(fn.strip()):
            if fl == "Pickle files (*.pkl)":
                pio.savePickleFile(resultsTrains, fn)
                
            elif fl == "HDF5 Files (*.hdf)":
                pio.saveHDF5(resultsTrains, fn)
                
    @pyqtSlot()
    def _slot_savePSCwaves(self):
        results = self.result()
        if results is None:
            return
        
        resultsDF, resultsTrains, resultsWaves = results
        
        fn, fl = self.chooseFile("Save mPSC waves",
                                 fileFilter = ";;".join(["Pickle files (*.pkl)", "HDF5 Files (*.hdf)"]),
                                 single=True,
                                 save=True)
        
        if isinstance(fn, str) and len(fn.strip()):
            if fl == "Pickle files (*.pkl)":
                pio.savePickleFile(resultsWaves, fn)
                
            elif fl == "HDF5 Files (*.hdf)":
                pio.saveHDF5(resultsWaves, fn)
                
    @pyqtSlot()
    def _slot_exportPSCresult(self):
        results = self.result()
        if results is None:
            return
        
        resultsDF, resultsTrains, resultsWaves = results
        
        varName = f"{self._data_._name}_mPSC_table"
        
        self.exportDataToWorkspace(resultsDF, var_name=varName, title="Export mPSC table to workspace")
        
    @pyqtSlot()
    def _slot_exportPSCtrains(self):
        results = self.result()
        if results is None:
            return
        
        resultsDF, resultsTrains, resultsWaves = results
        
        varName = f"{self._data_._name}_mPSC_trains"
        
        self.exportDataToWorkspace(resultsTrains, var_name=varName, title="Export mPSC trains to workspace")
        
    @pyqtSlot()
    def _slot_exportPSCwaves(self):
        results = self.result()
        if results is None:
            return
        
        resultsDF, resultsTrains, resultsWaves = results
        
        varName = f"{self._data_._name}_mPSC_waves"
        
        self.exportDataToWorkspace(resultsWaves, var_name=varName, title="Export mPSC waves to workspace")
        
    @pyqtSlot()
    def slot_showReportWindow(self):
        self._update_report_()
        
    @pyqtSlot()
    def _slot_clearResults(self):
        if self._data_ is None:
            self._result_ = None
            self._undo_buffer_ = None
            
        elif isinstance(self._data_, neo.Block):
            self._undo_buffer_ = [None for s in self._data_.segments]
            self._result_ = [None for s in self._data_.segments]
            for s in self._data_.segments:
                self._clear_detection_in_sweep_(s)
                
            
        elif isinstance(self._data_, (tuple, list)) and all(isinstance(s, neo.Segment) for s in self._data_):
            self._undo_buffer_ = [None for s in self._data_]
            self._result_ = [None for s in self._data_]
            for s in self._data_:
                self._clear_detection_in_sweep_(s)
            
        elif isinstance(self._data_, neo.Segment):
            self._undo_buffer_ = [None]
            self._result_ = [None]
            self._clear_detection_in_sweep_(self._data_)
            
        else:
            self._result_ = None
            self._undo_buffer_ = None
            
        
    @pyqtSlot()
    def _slot_detect(self):
        if self._data_ is None:
            self.criticalMessage("Detect mPSC in current sweep",
                                 "No data!")
            return
    
            
        waveform = self._get_mPSC_template_or_waveform_()
        if waveform is None:
            self.criticalMessage("Detect mPSC in current sweep",
                                 "No mPSC waveform or template is available")
            return
        
        if isinstance(self._data_, (neo.Block, neo.Segment)):
            vartxt = f"in {self._data_.name}"
        else:
            vartxt = ""
            
        progressDisplay = QtWidgets.QProgressDialog(f"Detecting mPSCS {vartxt}", "Abort", 0, self._number_of_frames_, self)

        
        # NOTE: 2022-11-26 09:06:16
        #### BEGIN using QRunnable paradigm
        # NOTE: 2022-11-25 22:15:47
        # this cannot abort
        worker = pgui.ProgressRunnableWorker(self._detect_all_, progressDisplay)
        
        worker.signals.signal_finished.connect(progressDisplay.reset)
        worker.signals.signal_result[object].connect(self._slot_detectionDone)
        # NOTE: 2022-11-25 22:16:15 see NOTE: 2022-11-25 22:15:47
        self.threadpool.start(worker)
        #### END using QRunnable paradigm
        
    @pyqtSlot()
    def _slot_detectionDone(self):
        # NOTE: 2022-11-26 09:06:05
        # QRunnable paradigm, see # NOTE: 2022-11-26 09:06:16
        self._plot_data()
        
    @pyqtSlot()
    def _slot_detect_thread_(self):
        # TODO
        if self._data_ is None:
            self.criticalMessage("Detect mPSC in current sweep",
                                 "No data!")
            return
    
            
        waveform = self._get_mPSC_template_or_waveform_()
        if waveform is None:
            self.criticalMessage("Detect mPSC in current sweep",
                                 "No mPSC waveform or template is available")
            return
        
        if isinstance(self._data_, (neo.Block, neo.Segment)):
            vartxt = f"in {self._data_.name}"
        else:
            vartxt = ""
            
        progressDisplay = QtWidgets.QProgressDialog(f"Detecting mPSCS {vartxt}", "Abort", 0, self._number_of_frames_, self)
        self._detectController_.setProgressDialog(progressDisplay)
        self._detectController_.sig_start.emit()
        
    @pyqtSlot(object)
    def _slot_detectThread_ready(self, result:object):
        print(f"{self.__class__.__name__}._slot_detectThread_ready(result = {result})")
        self._plot_data()
        
    @pyqtSlot()
    def _slot_undoDetection(self):
        """Restores spiketrains before detection, in all data.
        TODO: update results
        """
        if isinstance(self._data_, neo.Block):
            for k in range(len(self._data_segments_)):
                self._undo_sweep(k)
                
        self._plot_data()
        
    @pyqtSlot()
    def _slot_ephysViewer_closed(self):
        self.unlinkFromViewers(self._ephysViewer_)
        self._ephysViewer_ = None
        
    @pyqtSlot()
    def _slot_waveFormViewer_closed(self):
        self._waveFormViewer_ = None
        
    @pyqtSlot()
    def _slot_detected_mPSCViewer_closed(self):
        self._detected_mPSCViewer_ = None
        
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
    def _slot_setClearDetectionFlag_(self, value):
        # TODO: 2022-11-18 10:12:34 
        # make configurable
        self.clearOldPSCs = value == QtCore.Qt.Checked
        
    @pyqtSlot()
    def _slot_saveEphysData(self):
        if self._data_ is None:
            return
        
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
        if self._data_ is None:
            return
        
        self.exportDataToWorkspace(self._data_, var_name=self.metaDataWidget.dataVarName)
    
    @pyqtSlot()
    def _slot_plotData(self):
        if self._data_ is not None:
            self._plot_data()
            
    @pyqtSlot()
    def _slot_set_mPSC_accept(self):
        if len(self._detected_mPSCs_) == 0:
            return
        
        if self.currentWaveformIndex not in range(-len(self._detected_mPSCs_),
                                                  len(self._detected_mPSCs_)):
            return
        
        # accept = value == QtCore.Qt.Checked
        accept = self.sender().checkState() == QtCore.Qt.Checked
        
        self._detected_mPSCs_[self.currentWaveformIndex].annotations["Accept"] = accept
        train = self._result_[self.currentFrame][0]
        train.annotations["Accept"][self.currentWaveformIndex] = accept
        self._indicate_mPSC_(self.currentWaveformIndex)
        if self._reportWindow_.isVisible():
            self._update_report_()
        
    @pyqtSlot()
    def _slot_refit_mPSC(self):
        
        self._detected_mPSCs_ = self._result_[self.currentFrame][1]
        
        if len(self._detected_mPSCs_) == 0:
            return
        
        
        if self.currentWaveformIndex not in range(-len(self._detected_mPSCs_),
                                                  len(self._detected_mPSCs_)):
            return
        
        # print(f"{self.__class__.__name__}._slot_refit_mPSC: currentWaveformIndex = {self.currentWaveformIndex}")
        
        mini = self._detected_mPSCs_[self.currentWaveformIndex]
        
        w = mini[:,0]
        model_params = self.paramsWidget.value()
        init_params = tuple(p.magnitude for p in model_params["Initial Value:"])
        lo = tuple(p.magnitude for p in model_params["Lower Bound:"])
        up = tuple(p.magnitude for p in model_params["Upper Bound:"])
        w = membrane.fit_mPSC(w, init_params, lo=lo, up=up)
        w.annotations["t_peak"]=mini.annotations["t_peak"]
        # don;t change accept state here, do it manually in gui if fitting got better
        w.annotations["Accept"]=mini.annotations["Accept"]
        w.name = mini.name
        
        # print(f"{self.__class__.__name__}._slot_refit_mPSC: w.annotations = {w.annotations}")
        
        # self._detected_mPSCs_[self.currentWaveformIndex] = fw
        
        self._indicate_mPSC_(self.currentWaveformIndex)
        
        
        
            
    @pyqtSlot()
    def _slot_metaDataChanged(self):
        if isinstance(self._data_, (neo.Block, neo.Segment)):
            self._data_.name = self.metaDataWidget.dataName
            self._data_.annotations["Source"] = self.metaDataWidget.sourceID
            self._data_.annotations["Cell"] = self.metaDataWidget.cell
            self._data_.annotations["Field"] = self.metaDataWidget.field
            self._data_.annotations["Genotype"] = self.metaDataWidget.genotype
            self._data_.annotations["Sex"] = self.metaDataWidget.sex
            self._data_.annotations["Age"] = self.metaDataWidget.age
            self._data_.annotations["analysis_datetime"] = self.metaDataWidget.analysisDateTime
            
        
    @pyqtSlot(float)
    def _slot_modelDurationChanged(self, value):
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
            
        self._plot_model_()
        
    @pyqtSlot(bool)
    def _slot_lockToolbars(self, value):
        self.toolbarsLocked = value
        
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
        self._signal_index_ = index
        
            
    @pyqtSlot(str)
    def _slot_newTargetSignalSelected(self, value:str):
        self._detection_signal_name_ = value
        seg = self._get_data_segment_()
        if isinstance(seg, neo.Segment):
            sig = self._get_selected_signal_(seg)
            if isinstance(sig, neo.AnalogSignal) and sig.size > 1:
                self.durationSpinBox.units = sig.times.units
        
    
    @pyqtSlot(int)
    def _slot_newTargetSignalIndexSelected(self, value:int):
        if value in range(len(self._ephysViewer_.axes)):
            signalBlockers = [QtCore.QSignalBlocker(w) for w in (self._ephysViewer_, self.signalNameComboBox)]
            self._ephysViewer_.currentAxis=value
            self._signal_index_ = value
    
    @pyqtSlot(str)
    def _slot_epochComboBoxSelectionChanged(self, value):
        # print(f"_slot_epochComboBoxSelectionChanged value: {value}")
        segment = self._get_data_segment_()
        
        # print(f"_slot_epochComboBoxSelectionChanged segment: {segment.name}")
        
        if not isinstance(segment, neo.Segment):
            return
        
        segment_epoch_names = [e.name for e in segment.epochs]
        # print(f"_slot_epochComboBoxSelectionChanged epoch names: {segment_epoch_names}")
        
        if value == "Select..." and len(segment_epoch_names):
            dialog = ItemsListDialog(parent=self, title="Select epoch(s)",
                                     itemsList = segment_epoch_names,
                                     selectmode=QtWidgets.QAbstractItemView.ExtendedSelection)
            
            # print(f"_slot_epochComboBoxSelectionChanged dialog: {dialog.__class__.__name__}")
            
            ans = dialog.exec()
            
            if ans == QtWidgets.QDialog.Accepted:
                self._detection_epochs_.clear()
                self._detection_epochs_ = [i for i in dialog.selectedItemsText]
            
        elif value in segment_epoch_names:
            # print(f"_slot_epochComboBoxSelectionChanged selected: {value}")
            self._detection_epochs_.clear()
            self._detection_epochs_.append(value)
            
        elif value == "None":
            self._detection_epochs_.clear()
            
    @pyqtSlot(int)
    def _slot_mPSCViewer_frame_changed(self, value):
        signal_blocker = QtCore.QSignalBlocker(self._mPSC_spinBoxSlider_)
        self._mPSC_spinBoxSlider_.value = value
        self._currentWaveformIndex_ = value
        self._indicate_mPSC_(self.currentWaveformIndex)
        
        # NOTE: avoid this because currentFrame setter in SignalViewer emits
        # frameChanged, causing infinite recursion
        # self.displayDetectedWaveform(value)
        
            
    @pyqtSlot(int)
    def _slot_setWaveFormIndex(self, value):
        if value not in range(-len(self._detected_mPSCs_), len(self._detected_mPSCs_)):
            return
        self.displayDetectedWaveform(value)

    @property
    def currentWaveformIndex(self):
        return self._currentWaveformIndex_
    
    @currentWaveformIndex.setter
    def currentWaveformIndex(self, value):
        if isinstance(self._detected_mPSCs_, (tuple ,list)):
            if value in range(-len(self._detected_mPSCs_), len(self._detected_mPSCs_)):
                self._currentWaveformIndex_ = value
                self._plot_detected_mPSCs()
        else:
            self._currentWaveformIndex_ = 0
    
    @property
    def useTemplateWaveForm(self):
        return self._use_template_
    
    @markConfigurable("UseTemplateWaveForm")
    @useTemplateWaveForm.setter
    def useTemplateWaveForm(self, value):
        print(f"{self.__class__.__name__} @useTemplateWaveForm.setter value: {value}")
        self._use_template_ = value == True
        if isinstance(getattr(self, "configurable_traits", None), DataBag):
            self.configurable_traits["UseTemplateWaveForm"] = self._use_template_
        
    @property
    def templateWaveFormFile(self):
        return self._template_file_
    
    @markConfigurable("TemplateWaveFormFile")
    @templateWaveFormFile.setter
    def templateWaveFormFile(self, value:str):
        print(f"{self.__class__.__name__} @templateWaveFormFile.setter value: {value}")
        import os
        if isinstance(value, str) and os.path.isfile(value):
            self._template_file_ = value
            
        else:
            self._template_file_ = self._default_template_file
    
    @property
    def clearOldPSCs(self):
        return self._clear_detection_flag_
    
    @markConfigurable("ClearOldPSCsOnDetection")
    @clearOldPSCs.setter
    def clearOldPSCs(self, value):
        # print(f"{self.__class__.__name__} @clearOldPSCs.setter value: {value}")
        self._clear_detection_flag_ = value == True
        self.configurable_traits["ClearOldPSCsOnDetection"] = self._clear_detection_flag_
        # if isinstance(getattr(self, "configurable_traits", None), DataBag):

    @property
    def mPSCDuration(self):
        return self._mPSCduration_
    
    @markConfigurable("mPSC_Duration")
    @mPSCDuration.setter
    def mPSCDuration(self, value):
        # print(f"{self.__class__.__name__} @mPSCDuration.setter value: {value}")
        self._mPSCduration_ = value
        self.configurable_traits["mPSC_Duration"] = self._mPSCduration_

    @property
    def mPSCParametersInitial(self):
        """Initial parameter values
        """
        return dict(zip(self._params_names_, self._params_initl_))
    
    @markConfigurable("mPSCParametersInitial")
    @mPSCParametersInitial.setter
    def mPSCParametersInitial(self, value:typing.Union[pd.Series, tuple, list, dict]):
        # print(f"{self.__class__.__name__} @mPSCParametersInitial.setter value: {value}")
        if isinstance(value, (pd.Series, tuple, list, dict)):
            if len(value) != len(self._default_params_initl_):
                value = self._default_params_initl_
                
            elif isinstance(value, pd.Series):
                value = list(value)
                
            if isinstance(value, (tuple, list)):
                if all(isinstance(s, pq.Quantity) for s in value):
                    self._params_initl_ = [v for v in value]
                    
                elif all(isinstance(v, str) for v in value):
                    self._params_initl_ = list(str2quantity(v) for v in value)

                else:
                    raise TypeError("Expecting a sequence of scalar quantities or their str representations")
                
            elif isinstance(value, dict):
                assert set(value.keys()) == set(self._params_names_), f"Argument keys for initial values must match parameters names {self._params_names_}"
                
                for k, v in value.items():
                    self._params_initl_[self._params_names_.index(k)] = v
            
        elif value in (None, np.nan, math.nan):
            raise TypeError(f"Initial parameter values cannot be {value}")
        
        else:
            raise TypeError(f"Expecting a sequence of scalar quantities (or their str representations) for initial values; instead, got {type(value).__name__}:\n {value}")

        self.configurable_traits["mPSCParametersInitial"] = dict(zip(self._params_names_, self._params_initl_))
        # if isinstance(getattr(self, "configurable_traits", None), DataBag):
                
    @property
    def mPSCParametersLowerBounds(self):
        return dict(zip(self._params_names_, self._params_lower_))
    
    @markConfigurable("mPSCParametersLowerBounds")
    @mPSCParametersLowerBounds.setter
    def mPSCParametersLowerBounds(self, value:typing.Union[pd.Series, tuple, list, dict]):
        # print(f"{self.__class__.__name__} @mPSCParametersLowerBounds.setter value: {value}")
        if isinstance(value, (pd.Series, tuple, list, dict)):
            if len(value) not in (1, len(self._default_params_initl_)):
                value = self._default_params_lower_
                # raise ValueError(f"Expecting 1 or {len(self._default_params_initl_)} lower bounds; instead, got {len(value)}")
            
        if isinstance(value, pd.Series):
            value = list(value)
        
        if isinstance(value, (tuple, list)):
            if all(isinstance(v, pq.Quantity) for v in value):
                self._params_lower_ = [v for v in value]
                
            elif all(isinstance(v, str) for v in value):
                self._params_lower_ = list(str2quantity(v) for v in value)
                
            else:
                raise TypeError("Expecting a sequence of scalar quantities or their str representations")
            
        elif isinstance(value, dict):
            assert set(value.keys()) == set(self._params_names_), f"Argument keys for lower bounds must match parameters names {self._params_names_}"
            
            for k, v in value.items():
                self._params_lower_[self._params_names_.index(k)] = v
            
        elif value in (None, np.nan, math.nan):
            self._params_lower_ = value
            
        else:
            raise TypeError(f"Expecting a sequence of scalar quantities, str representations of scalar quantiities, or one of None, math.nan, np.nan, for the lower bounds; instead, got {type(value).__name__}:\n {value}")
                
        self.configurable_traits["mPSCParametersLowerBounds"] = dict(zip(self._params_names_, self._params_lower_))
        # if isinstance(getattr(self, "configurable_traits", None), DataBag):
                
    @property
    def mPSCParametersUpperBounds(self):
        return dict(zip(self._params_names_, self._params_upper_))
    
    @markConfigurable("mPSCParametersUpperBounds")
    @mPSCParametersUpperBounds.setter
    def mPSCParametersUpperBounds(self, value:typing.Union[pd.Series, tuple, list, dict]):
        # print(f"{self.__class__.__name__} @mPSCParametersUpperBounds.setter value: {value}")
        if isinstance(value, (pd.Series, tuple, list, dict)):
            if len(value) not in (1, len(self._default_params_initl_)):
                value = self._default_params_upper_
            
            elif isinstance(value, pd.Series):
                value = list(value)
            
            if isinstance(value, (tuple, list)):
                if all(isinstance(v, pq.Quantity) for v in value):
                    self._params_upper_ = [v for v in value]
                    
                elif all(isinstance(v, str) for v in value):
                    self._params_upper_ = list(str2quantity(v) for v in value)
                    
                else:
                    raise TypeError("Expecting a sequence of scalar quantities or their str representations")
                
            elif isinstance(value, dict):
                assert set(value.keys()) == set(self._params_names_), f"Argument keys for upper bounds must match parameters names {self._params_names_}"
                
                for k, v in value.items():
                    self._params_upper_[self._params_names_.index(k)] = v
            
        elif value in (None, np.nan, math.nan):
            self._params_upper_ = value

        else:
            raise TypeError(f"Expecting a sequence of scalar quantities, str representations of scalar quantiities, or one of None, math.nan, np.nan, for the upper bounds; instead, got {type(value).__name__}:\n {value}")
                
        self.configurable_traits["mPSCParametersUpperBounds"] = dict(zip(self._params_names_, self._params_upper_))
        # if isinstance(getattr(self, "configurable_traits", None), DataBag):
                
    @property
    def toolbarsLocked(self):
        return self._toolbars_locked_
    
    @markConfigurable("ToolbarsLocked", conftype="Qt")
    @toolbarsLocked.setter
    def toolbarsLocked(self, value:typing.Union[str, bool]):
        # NOTE: required because the QSettings do store bools as str ("true"
        # or "false")
        # print(f"toolbarsLocked.setter value = {value}")
        if isinstance(value, str):
            value = value.lower() == "true"

        self._toolbars_locked_ = value == True
        # print(f"toolbarsLocked.setter _toolbars_locked_ {self._toolbars_locked_}")
        for toolbar in (self.mainToolBar, self.detectionToolBar):
            toolbar.setFloatable(not self._toolbars_locked_)
            toolbar.setMovable(not self._toolbars_locked_)
            
        signalBlocker = QtCore.QSignalBlocker(self.actionLock_toolbars)
        self.actionLock_toolbars.setChecked(self._toolbars_locked_)
        
    def result(self):
        if all(v is None for v in self._result_):
            return
        
        psc_trains = list()
        all_waves = list()
        
        start_time = list()
        peak_time = list()
        amplitude = list()
        from_template = list()
        fit_amplitude = list()
        r2 = list()
        offset = list()
        scale = list()
        onset = list()
        tau_rise = list()
        tau_decay = list()
        accept = list()
        seg_index = list()
        wave_index = list()
        source_id = list()
        cell_id = list()
        sex = list()
        genotype = list()
        age = list()
        datetime=list()
        dataname = list()
        field_id = list()
        
        for k, frameResult in enumerate(self._result_):
            if frameResult is None:
                continue
            st = frameResult[0]
            if isinstance(st, (tuple, list)) and all(isinstance(v, neo.SpikeTrain) for v in st):
                if len(st) == 1:
                    psc_trains.append(st[0])
                else:
                    # merge spike trains
                    train = st[0].merge(st[1:])
                    psc_trains.append(train)
                    
            elif isinstance(st, neo.SpikeTrain):
                psc_trains.append(st)
            else:
                continue
            
            for kw, w in enumerate(frameResult[1]): # mini waves
                all_waves.append(w)
                seg_index.append(k)
                wave_index.append(kw)
                start_time.append(w.t_start)
                peak_time.append(w.annotations["t_peak"])
                amplitude.append(w.annotations["amplitude"])
                from_template.append(w.annotations["mPSC_fit"]["template"])
                fit_amplitude.append(w.annotations["mPSC_fit"]["amplitude"])
                r2.append(w.annotations["mPSC_fit"]["Rsq"])
                offset.append(w.annotations["mPSC_fit"]["Coefficients"][0])
                scale.append(w.annotations["mPSC_fit"]["Coefficients"][1])
                onset.append(w.annotations["mPSC_fit"]["Coefficients"][2])
                tau_rise.append(w.annotations["mPSC_fit"]["Coefficients"][3])
                tau_decay.append(w.annotations["mPSC_fit"]["Coefficients"][4])
                accept.append(w.annotations["Accept"])
                source_id.append(self.metaDataWidget.sourceID)
                cell_id.append(self.metaDataWidget.cell)
                field_id.append(self.metaDataWidget.field)
                age.append(self.metaDataWidget.age)
                sex.append(self.metaDataWidget.sex)
                genotype.append(self.metaDataWidget.genotype)
                dataname.append(self.metaDataWidget.dataName)
                datetime.append(self.metaDataWidget.analysisDateTime)
                
        res = {"Source":source_id, "Cell": cell_id, "Field": field_id,
               "Age": age, "Sex": sex, "Genotype":genotype, 
               "Data": dataname, "Date Time": datetime, "Accept":accept,
               "Sweep": seg_index, "Wave": wave_index, "Start Time": start_time,
               "Peak Time": peak_time, "Amplitude": amplitude,
               "Template":from_template, "Fit Amplitude": fit_amplitude,
               "R²": r2, "α":onset, "β": scale, "Onset (x₀)": onset, "Rise Time (τ₁)": tau_rise, "Decay Time (τ₂)": tau_decay}
        
        res_df = pd.DataFrame(res)
        
        return res_df, psc_trains, all_waves
    
    
