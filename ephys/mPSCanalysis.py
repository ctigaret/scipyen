# -*- coding: utf-8 -*-
import os, typing, math, datetime, logging, traceback
from numbers import (Number, Real,)
from itertools import chain

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__

import numpy as np
import scipy
import quantities as pq
import neo
# import pyqtgraph as pg
import pandas as pd

from iolib import pictio as pio
import core.neoutils as neoutils
import ephys.ephys as ephys
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
    sig_AbortDetection = pyqtSignal(name="sig_AbortDetection")
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
    
    _default_detection_threshold_ = 0.
    
    _detection_threshold_linear_range_min_ = 0.
    
    _detection_threshold_linear_range_max_ = 100.
    
    _default_noise_cutoff_frequency_ = 5e2*pq.Hz
    
    _default_DC_offset_ = 0*pq.pA
    
    # _available_filters_ = ("Butterworth", "Hamming")
    _available_filters_ = ("Butterworth", "Hamming", "Remez low-pass")
    
    _default_template_file = os.path.join(os.path.dirname(get_config_file()),"mPSCTemplate.h5" )
    
    def __init__(self, ephysdata=None, clearOldPSCs=False, ephysViewer:typing.Optional[sv.SignalViewer]=None, parent:(QtWidgets.QMainWindow, type(None)) = None, win_title="mPSC Detect", **kwargs):
        # NOTE: 2022-11-05 14:54:24
        # by default, frameIndex is set to all available frames - KISS
        self._toolbars_locked_ = True
        self._clear_detection_flag_ = clearOldPSCs == True
        self._mPSC_detected_ = False
        self._data_var_name_ = None
        self._last_used_file_save_filter_ = None
        self._last_used_file_open_filter_ = None
        
        self._currentTabIndex_ = 0
        
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
        self._use_threshold_on_rsq_ = False
        self._rsq_threshold_ = 0.
        self._accept_waves_cache_ = list() # a set for each segment
        self._overlayTemplateModel = False
        self._mPSC_template_ = None
        self._template_showing_ = False
        
        self._data_ = None
        self._filtered_data_ = None
        
        self._use_sliding_detection_=True
        
        # self._fs_ = None
        self._filter_type_ = "Butterworth"
        self._filter_function_ = None
        self._filter_signal_ = False
        self._apply_filter_upon_detection = False
        self._remove_DC_offset_ = False
        self._use_auto_offset_ = True
        self._lowpass_ = None
        self._humbug_ = False
        self._dc_offset_ = self._default_DC_offset_
        self._noise_cutoff_frequency_ = self._default_noise_cutoff_frequency_
        self._use_signal_linear_detrend_ = False
        
        #### BEGIN TODO: 2022-12-11 00:52:38 
        # make the ones below GUI & configurable (maybe...)
        self._humbug_notch_freq_ = 50.0 
        # self._humbug_Q_ = 25.
        self._humbug_Q_ = 30.
        self._inner_detrend_points_ = list()
        #### END TODO: 2022-12-11 00:52:38 
        
        
        self._detection_signal_name_ = None
        self._detection_epochs_ = list()
        self._signal_index_ = 0
        
        # the template file where a mPSC template is stored across sessions
        # this is located in the Scipyen's config directory
        # (on Linux, this file is in $HOME/.config/Scipyen, and its name can be
        # configured by triggering the appropriate action in the Settings menu)
        # NOTE: this file name is NOT written in the config file !!! 
        # TODO: 2022-11-27 22:03:10
        # manage configuration options
        self._template_file_ = self._default_template_file
        
        # we can also remember a file elsewhere in the file system, other than
        # the one above. NOTE: this file name IS WRITTEN in the config.
        # TODO 2022-11-27 22:03:34
        # make configurable
        self._custom_template_file_ = ""
        
        # last used template file - a template file other than the default
        self._last_used_template_file_name = ""
        
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
        self._mPSCs_for_template_ = list()
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
        
        self._time_units_ = self._default_time_units_
        self._signal_units_ = self._default_model_units_
        self._params_initl_ = self._default_params_initl_
        self._params_lower_ = self._default_params_lower_
        self._params_upper_ = self._default_params_upper_
        self._mPSCduration_ = self._default_duration_
        self._detection_threshold_ = self._default_detection_threshold_
        
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

        # NOTE: 2022-11-26 21:41:50
        # using the QRunnable paradigm works, but can't abort'
        # self.threadpool = QtCore.QThreadPool()
        
        # NOTE: 2022-11-26 11:22:38
        # this works, but still needs to be made abortable
        # self._detectController_ = pgui.ProgressThreadController(self._detect_all_)
        # self._detectController_.sig_ready.connect(self._slot_detectThread_ready)
        
        # NOTE: 2022-11-26 11:23:21
        # alternative from below:
        # https://realpython.com/python-pyqt-qthread/#using-qthread-to-prevent-freezing-guis
        self._detectThread_ = None
        self._detectWorker_ = None
        self._filterThread_ = None
        self._filterWorker_ = None
        
        # NOTE: 2022-11-26 21:42:48
        # mutable control data for the detection loop, to communicate with the
        # worker thread
        self.loopControl = {"break":False}
        
        # NOTE: 2022-11-05 23:08:01
        # this is inherited from WorkspaceGuiMixin therefore it needs full
        # initialization of WorkspaceGuiMixin instance
        # self._data_var_name_ = self.getDataSymbolInWorkspace(self._data_)
        
        # self.resize(-1,-1)
        if not isinstance(self._mPSC_template_, neo.AnalogSignal):
            self._use_template_ = False
            self.use_mPSCTemplate_CheckBox.setEnabled(False)

#### BEGIN _configureUI_
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
        
        self.tabWidget.currentChanged.connect(self._slot_currentTabChanged)
        
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
        
        self.rsqThresholdDoubleSpinBox.setValue(self._rsq_threshold_)
        self.rsqThresholdDoubleSpinBox.valueChanged.connect(self._slot_rsqThresholdChanged)
        
        # actions (shared among menu and toolbars):
        self.actionOpenEphysData.triggered.connect(self._slot_openEphysDataFile)
        self.actionImportEphysData.triggered.connect(self._slot_importEphysData)
        self.actionSaveEphysData.triggered.connect(self._slot_saveEphysData)
        self.actionExportEphysData.triggered.connect(self._slot_exportEphysData)
        self.actionPlot_Data.triggered.connect(self._slot_plotData)
        self.actionPlot_detected_mPSCs.triggered.connect(self._plot_detected_mPSCs)
        self.actionMake_mPSC_Epoch.triggered.connect(self._slot_make_mPSCEpoch)
        self.actionOpen_mPSCTemplate.triggered.connect(self._slot_openTemplateFile)
        self.actionCreate_mPSC_Template.triggered.connect(self._slot_create_mPSC_template)
        self.actionPlot_mPSC_template.triggered.connect(self._plot_template_)
        self.actionPlot_mPSCs_for_template.triggered.connect(self._plot_waves_for_template)
        self.actionImport_mPSCTemplate.triggered.connect(self._slot_importTemplate)
        self.actionSave_mPSC_Template.triggered.connect(self._slot_saveTemplateFile)
        self.actionExport_mPSC_Template.triggered.connect(self._slot_exportTemplate)
        self.actionRemember_mPSC_Template.triggered.connect(self._slot_storeTemplateAsDefault)
        self.actionForget_mPSC_Template.triggered.connect(self._slot_forgetTemplate)
        self.actionDetect_in_current_sweep.triggered.connect(self._slot_detectCurrentSweep)
        self.actionClear_default.triggered.connect(self._slot_clearFactoryDefaultTemplateFile)
        self.actionChoose_persistent_mPSC_template_file.triggered.connect(self._slot_choosePersistentTemplateFile)
        self.actionReset_to_factory.triggered.connect(self._slot_revertToFactoryDefaultTemplateFile)
        self.actionOverlay_Template_with_Model.triggered.connect(self._slot_setOverlayTemplateModel)
        self.actionLoad_default_mPSC_Template.triggered.connect(self._slot_loadDefaultTemplate)
        self.actionLoad_last_used_mPSC_template.triggered.connect(self._slot_loadLastUsedTemplate)
        # self.actionValidate_in_current_sweep.triggered.connect(self._slot_validateSweep)
        self.actionUndo_current_sweep.triggered.connect(self._slot_undoCurrentSweep)
        
        # self.actionDetect.triggered.connect(self._slot_detect)
        # TODO/FIXME 2022-11-26 09:10:33 for testing
        self.actionDetect.triggered.connect(self._slot_detectThread)
        
        self.actionClose.triggered.connect(self._slot_Close)
        
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
        self.actionUse_default_location_for_persistent_mPSC_template.triggered.connect(self._slot_useDefaultTemplateLocation)
        # self.actionChoose_persistent_mPSC_template_file.triggered.connect(self._slot_choosePersistentTemplateFile)
        self.actionLock_toolbars.setChecked(self._toolbars_locked_ == True)
        self.actionLock_toolbars.triggered.connect(self._slot_lockToolbars)
        # signal & epoch comboboxes
        self.signalNameComboBox.currentTextChanged.connect(self._slot_newTargetSignalSelected)
        self.signalNameComboBox.currentIndexChanged.connect(self._slot_newTargetSignalIndexSelected)
        self.epochComboBox.currentTextChanged.connect(self._slot_epochComboBoxSelectionChanged)
        # self.epochComboBox.currentIndexChanged.connect(self._slot_new_mPSCEpochIndexSelected)
        
        self.use_mPSCTemplate_CheckBox.setChecked(self._use_template_ == True)
        self.use_mPSCTemplate_CheckBox.stateChanged.connect(self._slot_use_mPSCTemplate)
        
        self.rsqThresholdCheckBox.setChecked(self._use_threshold_on_rsq_)
        self.rsqThresholdCheckBox.stateChanged.connect(self._slot_useThresholdOnRsquared)
        
        self.clearPreviousDetectionCheckBox.setChecked(self._clear_detection_flag_ == True)
        self.clearPreviousDetectionCheckBox.stateChanged.connect(self._slot_setClearDetectionFlag_)
        
        self.plot_mPSCWaveformToolButton.clicked.connect(self._slot_plot_mPSCWaveForm)
        self.exportModelWaveToolButton.clicked.connect(self._slot_exportModelWaveformToWorkspace)
        
        if self._toolbars_locked_:
            for toolbar in (self.mainToolBar, self.detectionToolBar):
                toolbar.setFloatable(not self._toolbars_locked_)
                toolbar.setMovable(not self._toolbars_locked_)
                
        self.metaDataWidget.sig_valueChanged.connect(self._slot_metaDataChanged)
        
        self.accept_mPSCcheckBox.setEnabled(False)
        self.accept_mPSCcheckBox.stateChanged.connect(self._slot_set_mPSC_accept)
        self.makeUnitAmplitudePushButton.clicked.connect(self._slot_makeUnitAmplitudeModel)
        
        self.detectionThresholdSpinBox.setMinimum(0)
        self.detectionThresholdSpinBox.setMaximum(math.inf)
        self.detectionThresholdSpinBox.setValue(self._detection_threshold_)
        self.detectionThresholdSpinBox.valueChanged.connect(self._slot_detectionThresholdChanged)
        # self.reFitPushButton.clicked.connect(self._slot_refit_mPSC)
        
        
        self.removeDCCheckBox.stateChanged.connect(self._slot_set_removeDC)
        self.autoOffsetCheckBox.stateChanged.connect(self._slot_setAutoOffset)
        
        self.dcValueSpinBox.setMinimum(-math.inf*pq.pA)
        self.dcValueSpinBox.setMaximum(math.inf*pq.pA)
        self.dcValueSpinBox.setValue(self._dc_offset_)
        self.dcValueSpinBox.sig_valueChanged.connect(self._slot_DCOffsetChanged)
        
        self.noiseFilterCheckBox.stateChanged.connect(self._slot_set_useLowPassFilter)
        
        self.cutoffFrequencySpinBox.setMinimum(0*pq.Hz)
        self.cutoffFrequencySpinBox.setMaximum(math.inf*pq.Hz)
        self.cutoffFrequencySpinBox.setValue(self._noise_cutoff_frequency_)
        
        self.cutoffFrequencySpinBox.sig_valueChanged.connect(self._slot_cutoffFreqChanged)
        
        self.actionApply_with_detection.triggered.connect(self._slot_applyFilters_with_detection)
        
        self.filterTypeComboBox.clear()
        # self.filterTypeComboBox.addItems(["Butterworth", "Hamming"])
        self.filterTypeComboBox.addItems(self._available_filters_)
        self.filterTypeComboBox.currentTextChanged.connect(self._slot_filterTypeChanged)
        
        self.actionPreview_filtered_signal.triggered.connect(self._slot_previewFilteredSignal)
        
        self.linearDetrendCheckBox.setChecked(False)
        self.linearDetrendCheckBox.stateChanged.connect(self._slot_useSignalDetrend)
        
        self.deHumCheckBox.setChecked(False)
        self.deHumCheckBox.stateChanged.connect(self._slot_useHumbug)
        
        self.useSlidingDetectionCheckBox.setChecked(True)
        self.useSlidingDetectionCheckBox.stateChanged.connect(self._slot_set_useSlidingDetection)
        
        
        # self.noiseFilterCheckBox.stateChanged.connect(self._slot_filterData)
        # print(f"{self.__class__.__name__}._configureUI_ end...")
#### END _configureUI_        
        
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
                self._accept_waves_cache_ = [set() for s in data.segments]
                # for k,s in enumerate(data.segments):
                #     # NOTE: 2022-11-20 11:54:02
                #     # store any existing spike trains with PSC time stamps
                #     # as a list, at the corresponding element in self._undo_buffer_
                #     # If there are none, just append an empty list to the cache!!!
                #     self._undo_buffer_[k] = self._get_previous_detection_(s)
                    
                self._data_ = data
                
                if len(self._data_.segments) and len(self._data_.segments[0].analogsignals):
                    time_units = self._data_.segments[0].analogsignals[0].times.units
                    signal_units = self._data_.segments[0].analogsignals[0].units
                    # sampling_rate = self._data_.segments[0].analogsignals[0].sampling_rate
                    # self.noiseCutoffFreq = sampling_rate/4
                    
                else:
                    time_units = self._default_time_units_
                    signal_units = self._default_model_units_
                    
                self._time_units_ = time_units
                self._signal_units_ = signal_units
                    
                self.durationSpinBox.units = self._time_units_
                self.dcValueSpinBox.units = self._signal_units_
                
                # NOTE: 2022-11-05 14:50:26
                # although self._data_frames_ and self._number_of_frames_ end up
                # having the same value they are distinct entities and the three 
                # lines below illustrate how to set them up
                self._data_frames_ = len(self._data_.segments)
                self._frameIndex_ = range(self._data_frames_)
                self._number_of_frames_ = len(self._frameIndex_)
                
                for k, segment in enumerate(self._data_.segments):
                    self._result_[k] = self._get_previous_detection_(segment)
                    if self._result_[k] is not None:
                        for kw, w in enumerate(self._result_[k][1]):
                            if w.annotations["Accept"] == True:
                                self._accept_waves_cache_[k].add(kw) 
                            
            elif isinstance(data, neo.Segment):
                self._undo_buffer_ = [None]
                self._result_ = [None]
                self._accept_waves_cache_ = [set()]
                
                if len(data.analogsignals):
                    time_units = data.analogsignals[0].times.units
                    signal_units = data.analogsignals[0].units
                    # sampling_rate = data.analogsignals[0].sampling_rate
                    # self.noiseCutoffFreq = sampling_rate/4
                else:
                    time_units = self._default_time_units_
                    signal_units = self._default_model_units_
                    
                self._time_units_ = time_units
                self._signal_units_ = signal_units
                    
                self.durationSpinBox.units = self._time_units_
                self.dcValueSpinBox.units = self._signal_units_
                
                self._data_ = data
                self._data_frames_ = 1
                self._frameIndex_ = range(self._data_frames_)
                self._number_of_frames_ = len(self._frameIndex_)
                self._result_ = [self._get_previous_detection_(segment)]
                if self._result_[0] is not None:
                    for kw, w in enumerate(self._result_[1]):
                        if w.annotations["Accept"] == True:
                            self._accept_waves_cache_[0].add(kw) 
                
            elif isinstance(data, (tuple, list)) and all(isinstance(v, neo.Segment) for v in data):
                self._undo_buffer_ = [None for s in data]
                self._result_ = [None for s in data]
                self._accept_waves_cache_ = [set() for s in data]
                            
                if len(data[0].analogsignals):
                    time_units = data[0].analogsignals[0].times.units
                    signal_units = data[0].analogsignals[0].units
                    # sampling_rate = data[0].analogsignals[0].sampling_rate
                    # self.noiseCutoffFreq = sampling_rate/4
                else:
                    time_units = self._default_time_units_
                    signal_units = self._default_model_units_
                    
                self._time_units_ = time_units
                self._signal_units_ = signal_units
                    
                self.durationSpinBox.units = self._time_units_
                self.dcValueSpinBox.units = self._signal_units_
                
                self._data_ = data
                self._data_frames_ = len(self._data_)
                self._frameIndex_ = range(self._data_frames_)
                self._number_of_frames_ = len(self._frameIndex_)
                
                for k,s in enumerate(self._data_):
                    self._result_[k] = self._get_previous_detection_(s)
                    if self._result_[k] is not None:
                        for kw, w in enumerate(self._result_[k][1]):
                            if w.annotations["Accept"] == True:
                                self._accept_waves_cache_[k].add(kw) 
                    
            else:
                self.errorMessage(self.windowTitle(), f"Expecting a neo.Block, neo.Segment, or a sequence of neo.Segment objects; got {type(data).__name__} instead")
                return
            
        elif data is None:
            # WARNING: passing None clears the viewer
            self.clear()
            return
            
        else:
            self.errorMessage(self.windowTitle(), f"Expecting a neo.Block, neo.Segment, or a sequence of neo.Segment objects, or None; got {type(data).__name__} instead")
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
        elif isinstance(self._mPSC_template_, neo.AnalogSignal):
            sampling_rate = self._mPSC_template_.sampling_rate
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
        init_params = tuple(float(p.magnitude) for p in model_params["Initial Value:"])
            
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
        
        # NOTE: 2022-11-27 13:49:44
        # DO NOT CALL clear() - it will clear the waves list in result, because 
        # they are a list stored by reference !!!
        # self._detected_mPSCs_.clear() 
        # DO THIS INSTEAD:- replace self._detected_mPSCs_ with a new empty list
        self._detected_mPSCs_ = list()
        
        if self.currentFrame in range(-len(self._result_), len(self._result_)):
            frameResults = self._result_[self.currentFrame]
            # print(frameResults)
        
            if isinstance(frameResults, (tuple, list)) and len(frameResults) == 2:
                if isinstance(frameResults[1], (tuple, list)) and all(isinstance(s, neo.AnalogSignal) for s in frameResults[1]):
                    self._detected_mPSCs_ = frameResults[1]
            
        # segment = self._get_data_segment_(self.currentFrame)
        # signal = self._get_selected_signal_(segment)
        
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
        self._accept_waves_cache_ = list()
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
        
    @pyqtSlot()
    def _slot_Close(self):
        self.close()
        
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
        
    def _enable_widgets(self, *widgets, enable:bool=True):
        for w in widgets:
            if isinstance(w, (QtWidgets.QWidget, QtWidgets.QAction)):
                w.setEnabled(enable==True)
                
    def alignWaves(self):
        """
        Aligns detected mPSC waveforms on the onset. 
        Useful in order to create a mPSC template waveform from their average.
        """
        if self._data_ is None:
            return
        
        if all(v is None for v in self._result_):
            return
        
        # NOTE: 2022-11-27 14:21:41 The logic is a follows:
        #
        # • only work on accepted waveforms
        #
        # • retrieve the wave start time (form the beggining of the recording);
        #
        # • take the fitted onset of the wave (this is ALWAYS relative to the
        #   start of the waveform)
        #
        # • use the longest onset across waves
        #
        # • readjust the start time such that there is the same delay between
        #   start time and the onset
        #
        # • calculate stop time: start time + mPSC duration (from model parameters)
        #
        # • use the new start time and the calculated stop time to get time 
        #   slices from each signal ⇒ store them in the list of aligned waves
        #
        # • display the waves in the mPSC waveform viewer
        #
        # • display their average in the mPSC model viewer
        #
        # 
        
        waves_list = list() # holds aligned waves
        
        sweep_index = list()
        wave_index = list()
        start_times = list()
        peak_times = list()
        onset = list()
        
        for k, frameResult in enumerate(self._result_):
            if frameResult is None:
                continue
            
            # st = frameResult[0]
            # wave_index = list()
            for kw, w in enumerate(frameResult[1]):
                if w.annotations["Accept"] == True:
                    start_times.append(w.t_start)
                    peak_times.append(w.annotations["t_peak"])
                    onset.append(w.annotations["mPSC_fit"]["Coefficients"][2])
                    wave_index.append(kw)
                    sweep_index.append(k)
                    
        if len(onset):
            maxOnset = max(onset) * start_times[0].units
            onsetCorrection = [maxOnset - v*start_times[0].units for v in onset]
            new_start_times = [start_times[k] - onsetCorrection[k] for k in range(len(start_times))]
            stop_times = [v + self._mPSCduration_ for v in new_start_times]
            
            for k,sweep_ndx in enumerate(sweep_index):
                segment = self._get_data_segment_(sweep_ndx)
                signal = self._get_selected_signal_(segment)
                    
                wave_ndx = wave_index[k]
                t0 = new_start_times[k]
                t1 = stop_times[k]
                wave = signal.time_slice(t0, t1)
                # 1) Remove the DC component - signal average beween t0 and onset
                t_onset = t0+maxOnset
                baseline = signal.time_slice(t0, t_onset)
                dc = np.mean(baseline, axis=0)
                wave -= dc
                # 2) set relatime time start to 0
                # wave = neoutils.set_relative_time_start(wave[:,0])
                waves_list.append(neoutils.set_relative_time_start(wave[:,0]))
                
        # print(len(waves_list))
        if len(waves_list):
            self._mPSCs_for_template_[:] = waves_list
            self._mPSC_template_ = ephys.average_signals(*waves_list)
            self._mPSC_template_.description = "Average mPSC Waveform"
            self._mPSC_template_.name ="mPSC Template"
            dataOriginName = self.metaDataWidget.value()["Name"]
            dateTime = datetime.datetime.now()
            dateTimeStr = dateTime.strftime("%d_%m_%Y_%H_%M_%S")
            if not isinstance(dataOriginName, str) or len(dataOriginName.strip()) == 0:
                if isinstance(self._data_, (tuple, list)) and all(isinstance(v, neo.Segment) for v in self._data_):
                    dataOriginName = f"List of segments {dateTimeStr}"
                else:
                    dataOriginName = f"Averaged mPSC template {dateTimeStr}"
            
            self._mPSC_template_.annotations.update({"datetime":dateTime,
                                                     "data_origin":dataOriginName})
            
            
            self._plot_waves_for_template()
            self._plot_template_()
            
            
    def _plot_model_(self):
        """Plots mPSC model waveform"""
        if not isinstance(self._waveFormViewer_, sv.SignalViewer):
            self._waveFormViewer_ = sv.SignalViewer(win_title="mPSC waveform", 
                                                    parent=self, configTag="WaveformViewer")
            self._waveFormViewer_.sig_closeMe.connect(self._slot_waveFormViewer_closed)
            
        if self._overlayTemplateModel and isinstance(self._mPSC_template_, neo.AnalogSignal):
            modelwave = self._get_mPSC_template_or_waveform_(use_template = False)
            maxLen = max(modelwave.shape[0], self._mPSC_template_.shape[0])
            combinedWaves = np.full((maxLen, 2), fill_value = np.nan)
            combinedWaves[0:self._mPSC_template_.shape[0],0] = self._mPSC_template_[:,0].flatten().magnitude
            combinedWaves[0:modelwave.shape[0],1] = modelwave[:,0].flatten().magnitude
            merged = neo.AnalogSignal(combinedWaves, 
                                      units = self._mPSC_template_.units, 
                                      t_start = 0*pq.s,
                                      sampling_rate = self._mPSC_template_.sampling_rate,
                                      name = self._mPSC_template_.name,
                                      description = self._mPSC_template_.description)
            merged.annotations.update(self._mPSC_template_.annotations)
            self._waveFormViewer_.view(merged)
        else:
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
            if self.overlayTemplateModel:
                modelwave = self._get_mPSC_template_or_waveform_(use_template = False)
                maxLen = max(modelwave.shape[0], self._mPSC_template_.shape[0])
                combinedWaves = np.full((maxLen, 2), fill_value = np.nan)
                combinedWaves[0:self._mPSC_template_.shape[0],0] = self._mPSC_template_[:,0].flatten().magnitude
                combinedWaves[0:modelwave.shape[0],1] = modelwave[:,0].flatten().magnitude
                merged = neo.AnalogSignal(combinedWaves, 
                                        units = self._mPSC_template_.units, 
                                        t_start = 0*pq.s,
                                        sampling_rate = self._mPSC_template_.sampling_rate,
                                        name = self._mPSC_template_.name,
                                        description = self._mPSC_template_.description)
                merged.annotations.update(self._mPSC_template_.annotations)
                self._waveFormViewer_.view(merged)
            else:
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
            
    @pyqtSlot()
    def _slot_previewFilteredSignal(self):
        if self._data_ is None:
            return
        segment = self._get_data_segment_(self.currentFrame)
        signal = self._get_selected_signal_(segment)
        
        epochs = [e for e in segment.epochs if e.name in self._detection_epochs_]
        if len(epochs):
            sig = neoutils.get_time_slice(signal,epochs[0])
            sig.segment = segment
            sig.description = ""
        else:
            sig = signal
            
            
        klass = signal.__class__
        
        processed = self._process_signal_(sig, newFilter=True)
        processed.segment = segment
        
        if not any((self._use_signal_linear_detrend_, self._remove_DC_offset_,
                   self._humbug_, self._filter_signal_)):
            processed.name = f"{sig.name}_copy"
            descr = f"Copy of {sig.name}"
        else:
            descr = f"{sig.description} filtered with {self._filter_type_}, cutoff: {self._noise_cutoff_frequency_}"
            
        testsig = sig.merge(processed)
        testsig.description = descr
        
        if not isinstance(self._ephysViewer_,sv.SignalViewer):
            self._init_ephysViewer_()
            
        self._ephysViewer_.plot(testsig)
        
            
    def _plot_waves_for_template(self):
        if len(self._mPSCs_for_template_):
            self.accept_mPSCcheckBox.setEnabled(False)
            self._template_showing_ = True
            
            if not isinstance(self._detected_mPSCViewer_, sv.SignalViewer):
                self._detected_mPSCViewer_ = sv.SignalViewer(win_title="Detected mPSCs", 
                                                            parent=self, configTag="mPSCViewer")

                self._detected_mPSCViewer_.sig_closeMe.connect(self._slot_detected_mPSCViewer_closed)

                self._detected_mPSCViewer_.frameChanged.connect(self._slot_mPSCViewer_frame_changed)
                
            self._detected_mPSCViewer_.removeLabels(0)
            self._mPSC_spinBoxSlider_.setRange(0, len(self._mPSCs_for_template_)-1)
            self._detected_mPSCViewer_.view(self._mPSCs_for_template_)
            
            
    def _plot_detected_mPSCs(self):
        # print(f"{self.__class__.__name__}._plot_detected_mPSCs")
        frameResult = self._result_[self.currentFrame]
        signalBlockers = (QtCore.QSignalBlocker(w) for w in (self._mPSC_spinBoxSlider_,
                                                            self.accept_mPSCcheckBox))
        self._template_showing_ = False
        
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
        
        currentSweepDetection = self._result_[self.currentFrame]
        if currentSweepDetection is None:
            return
        
        self._detected_mPSCs_ = self._result_[self.currentFrame][1]
        
        if len(self._detected_mPSCs_) == 0:
            return
        
        
        segment = self._get_data_segment_()
        signal = segment.analogsignals[self._signal_index_]
        axis = self._ephysViewer_.axes[self._signal_index_]
        
        if waveindex not in range(-len(self._detected_mPSCs_),len(self._detected_mPSCs_)):
            waveindex = 0
        
        mPSC = self._detected_mPSCs_[waveindex]
        
        peak_time = mPSC.annotations.get("t_peak", None)
        
        waveR2 = mPSC.annotations["mPSC_fit"].get("Rsq", None)
        
        if waveR2 is not None:
            if mPSC.annotations.get("Accept", False):
                wavelabel = "R²=%.2f Accept" % waveR2
            else:
                wavelabel = "R²=%.2f Reject" % waveR2
                
        else:
            if mPSC.annotations.get("Accept", False):
                wavelabel = "Accept"
            else:
                wavelabel = "Reject"
                
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
        
        targetSize = 15 # TODO: 2022-11-27 13:44:45 make confuse configurable
        
        # NOTE: 2022-11-23 21:47:29
        # below, the offset of the label to its target is given as (x,y) with
        # x positive left → right
        # y positive bottom → top (like the axis)
        # TODO: make confuse configurable
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
            mPSCtrain = mPSCtrains[0]
            peak_times = mPSCtrain.annotations.get("peak_times", list())
            accepted = mPSCtrain.annotations.get("Accept", list())
            template = mPSCtrain.annotations.get("Template", list())
            
            if len(peak_times) == 0: # invalid data, so discard everything
                return
            
            signal_units = mPSCtrain.annotations.get("signal_units", None)
            
            if signal_units is None: # invalid data, so discard everything
                return
            
            psc_params = mPSCtrain.annotations.get("PSC_parameters", None)
            psc_fits = mPSCtrain.annotations.get("mPSC_fit", [])
            
            signal_origin =  mPSCtrain.annotations.get("signal_origin", None)
            segment_origin = mPSCtrain.annotations.get("segment_origin", None)
            data_origin = mPSCtrain.annotations.get("data_origin", None)
            
            
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
                mPSCtrain.annotations["signal_origin"] = signal_origin
                mPSCtrain.annotations["segment_origin"] = segment_origin
                mPSCtrain.annotations["data_origin"] = data_origin
                mPSCtrain.annotations["PSC_parameters"] = psc_params # may be None !
                mPSCtrain.annotations["mPSC_fit"] = psc_fits # a list, which may be empty
                
                for t in mPSCtrains[1:]:
                    neoutils.remove_spiketrain(segment, t.name)
                    
            waves = mPSCtrain.waveforms
            
            # print(waves.shape)
            signal_units = mPSCtrain.annotations.get("signal_units", pq.pA)
            mini_waves = list()
            if waves.size > 0:
                for k in range(waves.shape[0]): # spike #
                    wave = neo.AnalogSignal(waves[k,:,:].T,
                                            t_start = mPSCtrain[k],
                                            units = signal_units,
                                            sampling_rate = mPSCtrain.sampling_rate)
                    
                    wave.annotations["amplitude"] = sigp.waveform_amplitude(wave[:,0])
                    
                    if len(accepted) == waves.shape[0]:
                        wave.annotations["Accept"] = accepted[k]
                    else:
                        wave.annotations["Accept"] = True
                        
                    # assign a peak time to each wave; if not present in 
                    # the minis train, calculate it NOW
                    if len(peak_times) == waves.shape[0]:
                        wave.annotations["t_peak"] = peak_times[k]
                    else:
                        if sigp.is_positive_waveform(wave):
                            peakfunc = np.argmax
                        else:
                            peakfunc = np.argmin
                        p_time = wave.times[peakfunc(wave[:.0])]
                        
                        wave.annotations["t_peak"] = p_time
                        
                    if len(psc_fits) == waves.shape[0]:
                        wave.annotations["mPSC_fit"] = psc_fits[k]
                        
                    mini_waves.append(wave)
                
                # if peak times not present in trhe minis train, add them
                # NOW
                if len(peak_times) == len(mini_waves):
                    peak_times = [w.annotations["t_peak"] for w in mini_waves]
                    mPSCtrain.annotations["peak_times"] = peak_times
                    
                
            return (mPSCtrain, mini_waves)
            
        else:
            return None
                
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
        NOTE: These do not need to be passed explicitly to the call; they are
        supposed to be supplied by an instance of a worker in the pictgui 
        module (e.g. ProgressWorkerRunnable, or ProgressWorkerThreaded)
        
        progressSignal: PyQt signal that will be emitted with each iteration
        
        progressUI: QtWidgets.QProgressDialog or None
        
        
        """
        if self._data_ is None:
            return
        
        clear_prev_detection = kwargs.pop("clearLastDetection", True)
        loopControl = kwargs.pop("loopControl", None)
        progressSignal = kwargs.pop("progressSignal", None)
        finished = kwargs.pop("finished", None)
        # setMaxSignal = kwargs.pop("setMaxSignal", None)
        # canceled = kwargs.pop("canceled", None)
        # progressUI = kwargs.pop("progressDialog", None)
        
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
            try:
                res = self._detect_sweep_(frame, waveform=waveform)
            except Exception as exc:
                traceback.print_exc()
                excstr = traceback.format_exception(exc)
                msg = f"In sweep{frame}:\n{excstr[-1]}"
                self.criticalMessage("Detect mPSCs in current sweep",
                                     excstr)
                return
                
            if res is None:
                continue
            
            mPSCtrain, detection = res
            
            self._result_[frame] = (mPSCtrain, [s for s in detection])
            
            if clear_prev_detection:
                self._clear_detection_in_sweep_(segment)
                
            segment.spiketrains.append(mPSCtrain)
            
            if isinstance(progressSignal, QtCore.pyqtBoundSignal):
                progressSignal.emit(frame)
                
            if isinstance(loopControl, dict) and loopControl.get("break",  None) == True:
                break
                
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
            
    def _apply_Rsq_threshold(self, value:float, sweep:int=None, wave:int=None):
        if self._data_ is None:
            return
        
        if all(v is None for v in self._result_):
            return 
        
        if isinstance(sweep, int) and sweep in range(-self.nFrames, self.nFrames):
            result = self._result_[sweep]
            if result is None:
                return
            
            st = result[0]
            
            if isinstance(st, (tuple, list)) and all(isinstance(v, neo.SpikeTrain) for v in st):
                if len(st) > 1:
                    # merge spike trains
                    train = st[0].merge(st[1:])
                else:
                    train = st[0]
                    
                result[0] = train
                st = train
                    
            if isinstance(wave, int) and wave in range(-len(st), len(st)):
                w = result[1][wave]
                if self.useThresholdOnRsquared:
                    w.annotations["Accept"] = w.annotations["mPSC_fit"]["Rsq"] >= self.rSqThreshold
                else:
                    if kw in self._accept_waves_cache_[k]:
                        w.annotations["Accept"] = True
                        
                st.annotations["Accept"][wave] = w.annotations["Accept"]
                
            else:
                for kw, w in enumerate(result[1]):
                    if self.useThresholdOnRsquared:
                        w.annotations["Accept"] = w.annotations["mPSC_fit"]["Rsq"] >= self.rSqThreshold
                    else:
                        if kw in self._accept_waves_cache_[k]:
                            w.annotations["Accept"] = True
                        else:
                            w.annotations["Accept"] = False
                            
                    st.annotations["Accept"][kw] = w.annotations["Accept"]

            
        
        for k, result in enumerate(self._result_):
            if result is None:
                continue
            
            st = result[0]
            
            if isinstance(st, (tuple, list)) and all(isinstance(v, neo.SpikeTrain) for v in st):
                if len(st) == 1:
                    psc_trains.append(st[0])
                else:
                    # merge spike trains
                    train = st[0].merge(st[1:])
                    result[0] = train
                    
            for kw, w in enumerate(result[1]):
                if self.useThresholdOnRsquared:
                    w.annotations["Accept"] = w.annotations["mPSC_fit"]["Rsq"] >= self.rSqThreshold
                else:
                    if kw in self._accept_waves_cache_[k]:
                        w.annotations["Accept"] = True
                    else:
                        w.annotations["Accept"] = False

        self._plot_data()
        if self._reportWindow_.isVisible():
            self._update_report_()
                 
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
        dataOriginName = self.metaDataWidget.value()["Name"]
        dateTime = datetime.datetime.now()
        dateTimeStr = dateTime.strftime("%d_%m_%Y_%H_%M_%S")

        if not isinstance(dataOriginName, str) or len(dataOriginName.strip()) == 0:
            if isinstance(self._data_, (tuple, list)) and all(isinstance(v, neo.Segment) for v in self._data_):
                dataOriginName = f"List of segments {dateTimeStr}"
            else:
                dataOriginName = f"Data {dateTimeStr}"

        # NOTE: 2022-11-22 08:57:22
        # • returns a spiketrain, a detection dict and the waveform used in detection
        # • does NOT ember the spiketrain in the analysed segment anymore - this 
        #   should be done in the caller, as necessary
        if segment_index is None:
            segment_index = self.currentFrame
            
        segment = self._get_data_segment_(segment_index)
        
        if isinstance(segment.name, str) and len(segment.name.strip()):
            segmentName = segment.name
        else:
            segmentName = f"segment_index"
        
        if not isinstance(segment, neo.Segment):
            return
        
        if isinstance(self._data_, neo.Block):
            dstring = f"PSCs detected in {self._data_.name } segment {segment.name}"
        else:
            dstring = f"PSCs detected in segment {segment.name}"
        
        signal = self._get_selected_signal_(segment)
        
        if isinstance(signal.name, str) and len(signal.name.strip()):
            signalName = signal.name
        else:
            signalName = f"Signal {segment.analogsignals.index(signal)}"
        
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
            detections = list()
            for epoch in epochs:
                sig = signal.time_slice(epoch.times[0], epoch.times[0]+epoch.durations[0])
                if self.filterDataUponDetection:
                    sig = self._process_signal_(sig, newFilter=True)
                detection = membrane.detect_mPSC(sig, waveform, 
                                                 useCBsliding = self.useSlidingDetection,
                                                 threshold = self._detection_threshold_)
                if detection is None:
                    continue
                
                detections.append(detection)
                
                template = detection[0].annotations["waveform"]
                
#                 mini_waves.extend(detection["minis"][0])
#                 mini_starts.append(detection["mini_starts"][0])
#                 mini_peaks.append(detection["mini_peaks"][0])
#                 
#             print(f"with epochs: mini_starts {mini_starts}; mini_peaks {mini_peaks}")
#             if len(mini_starts) and len(mini_starts):
#                 start_times = np.hstack(mini_starts) * mini_starts[0][0].units
#                 peak_times = np.hstack(mini_peaks) * mini_peaks[0][0].units
#                 
#             print(f"with epochs: start_times {start_times}, peak_times {peak_times}")
            
            if len(detections):
                # splice individual detections in each separate epoch; these
                # individual epoch detections are SpikeTrainList objects, possibly
                # with more than one SpikeTrain inside (one per channel)
                max_channels = max(len(d) for d in detections)
                stt = list() #  will lhold spliced spike trains, one per channel
                for kc in range(max_channels):
                    st = neoutils.splice_signals(*[d[kc] for d in detections])
                    pt = np.concatenate([t.annotations["peak_times"].magnitude for t in [d[kc] for d in detections]], axis=0) * detections[0][0].units
                    st.annotations["peak_times"] = pt
                    θ = neoutils.splice_signals(*[d[kc].annotations["θ"]] for d in detections)
                    θmax = np.max(θ[~np.isnan(θ)])
                    θnorm = θ.copy()  # θ is a neo signal
                    θnorm = sigp.scale_signal(θ, 10, θmax)
                    st.annotations["θ"] = θ
                    st.annotations["θ_norm"] = θ_norm
                    stt.append(st)
                    
            
        else: # no epochs - detect in the whole signal
            if self.filterDataUponDetection:
                signal = self._process_signal_(signal, newFilter=True)
            detection = membrane.detect_mPSC(signal, waveform)
            if detection is None:
                return
            
            # print(f"detection {detection}")
            
#             start_times = detection["mini_starts"][0]
#             peak_times  = detection["mini_peaks"][0]
#             mini_waves  = detection["minis"][0]
#             
#             print(f"no epochs: start_times {start_times}; peak_times {peak_times}")
            # NOTE: 2022-11-27 21:05:07
            # this is ALWAYS a waveform !!!
            template = detection[0].annotations["waveform"]
            
        # NOTE: 2022-11-20 11:33:43
        # set this here
        if isinstance(self._data_, neo.Block):
            trname = f"{self._data_.name}_{segment.name}_PSCs"
        else:
            trname = f"{segment.name}_PSCs"
        
        mPSCTrains = list()
        wave_collection = list()
        
        for k, start_timestamps in enumerate(start_times):
            if isinstance(template, neo.core.basesignal.BaseSignal) and len(template.description.strip()):
                dstring += f" using {template.description}"
                
            mPSCtrain = neo.SpikeTrain(start_timestamps, t_stop = signal.t_stop, units = signal.times.units,
                                    t_start = signal.t_start, sampling_rate = signal.sampling_rate,
                                    name = trname, description=dstring)
            
            mPSCtrain.annotations["peak_times"] = peak_times[k]
            mPSCtrain.annotations["source"] = "PSC_detection"
            mPSCtrain.annotations["signal_units"] = signal.units
            mPSCtrain.annotations["signal_origin"] = signalName
            mPSCtrain.annotations["segment_origin"] = segmentName
            mPSCtrain.annotations["data_origin"] = dataOriginName
            mPSCtrain.annotations["datetime"] = datetime.datetime.now()
            
            # NOTE: 2022-11-27 21:04:08
            # this is always True, but only a model-generated waveform has the 
            # model parameters in its annotations
            if isinstance(template, neo.core.basesignal.BaseSignal):
                mPSCtrain.annotations["PSC_parameters"] = template.annotations.get("parameters", None)
            
            model_params = self.paramsWidget.value()
            init_params = tuple(p.magnitude for p in model_params["Initial Value:"])
            lo = tuple(p.magnitude for p in model_params["Lower Bound:"])
            up = tuple(p.magnitude for p in model_params["Upper Bound:"])
            
            accepted = list()
            templates = list()
            mPSC_fits = list()
            
            # fit the template then use the fitted params to fit the detected mPSCs
            # if using a template
            template_init_params = None
            
            # NOTE: 2022-11-28 17:10:56 
            # FIX for FIXME: 2022-11-25 00:50:11:
            # 1) The template is first fitted with the model params (initial,
            # lower & upper bounds) using the values from the parameters 
            # fields in the app window ⇒ template_fit
            #
            # 2) The result of the template fit is then used to provide initial
            #  parameters `template_init_params` for fitting detected putative 
            # mPSCs individually in the loop below
            #
            # TODO: 2022-11-28 17:15:49
            # consider taking this calculation out of this method, or better,
            # cache the template_init_params so that they are re-used inside the 
            # loop in self._detect_all_
            #
            if self._use_template_ and isinstance(self._mPSC_template_, neo.AnalogSignal):
                template_fit = membrane.fit_mPSC(self._mPSC_template_, init_params, lo, up)
                template_init_params = template_fit.annotations["mPSC_fit"]["Coefficients"]
                
            for kw,w in enumerate(mini_waves[k]):
                # FIXME: 2022-11-25 00:50:11
                # when template is Not a model where are the params taken from?
                # FIXED, see NOTE: 2022-11-28 17:10:56
                if self._use_template_ and template_init_params is not None:
                    fw = membrane.fit_mPSC(w, template_init_params, lo=lo, up=up)
                    sigblock = QtCore.QSignalBlocker(self.paramsWidget)
                    self.paramsWidget.setParameters(template_init_params,
                                                lower = [float(v) for v in lo],
                                                upper = [float(v) for v in up],
                                                names = self._params_names_,
                                                refresh = True)
                
                    # fw = membrane.fit_mPSC(w, self._mPSC_template_)
                else:
                    fw = membrane.fit_mPSC(w, init_params, lo=lo, up=up)
                # fw = membrane.fit_mPSC(w, template.annotations["parameters"], lo=lo, up=up)
                fw.annotations["t_peak"] = mPSCtrain.annotations["peak_times"][kw]
                fw.name = f"mPSC_{fw.name}_{kw}"
                mini_waves[k][kw] = fw
                mPSC_fits.append(fw.annotations["mPSC_fit"])
                
                if self._use_threshold_on_rsq_:
                    fw.annotations["Accept"] = fw.annotations["mPSC_fit"]["Rsq"] >= self.rSqThreshold
                
                if fw.annotations["Accept"]:
                    self._accept_waves_cache_[segment_index].add(k)
                
                accepted.append(fw.annotations["Accept"])
                templates.append(fw.annotations["mPSC_fit"]["template"]) # flag indicating if a template or a model was used
                
            mPSCtrain_waves = np.concatenate([w.magnitude[:,:,np.newaxis] for w in mini_waves[k]], axis=2)
            mPSCtrain.waveforms = mPSCtrain_waves.T
            mPSCtrain.annotations["Accept"] = accepted
            mPSCtrain.annotations["Template"] = templates
            mPSCtrain.annotations["mPSC_fit"] = mPSC_fits
            
            mPSCtrains.append(mPSCtrain)
            wave_collection.append[mini_waves[k]]
            
        return mPSCtrains, wave_collection
        
    @pyqtSlot()
    def _slot_create_mPSC_template(self):
        self.alignWaves()
        if isinstance(self._mPSC_template_, neo.AnalogSignal):
            self.use_mPSCTemplate_CheckBox.setEnabled(True)
        
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
            
    @pyqtSlot()
    def _slot_useDefaultTemplateLocation(self):
        self.templateWaveFormFile = self._default_template_file
            
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
            try:
                detection_result = self._detect_sweep_(waveform=waveform)
                
            except Exception as exc:
                traceback.print_exc()
                execstr = traceback.format_exception(exc)
                msg = execstr[-1]
                self.criticalMessage("Detect mPSCs in current sweep",
                                     msg)
                return
            
            if detection_result is None:
                return
            
            mPSCtrains, detection = self._detect_sweep_(waveform=waveform)
            # NOTE: 2022-11-22 17:47:15
            # see WARNING: 2022-11-22 17:46:17
            #### BEGIN FIXME 2022-12-12 08:53:19
            # adapt for multi-channel detection (see membrane.extract_minis)
            self._result_[self.currentFrame] = (mPSCtrains, [s for s in detection])
            
            if len(detection):
                # NOTE: 2022-11-22 17:47:33
                # see WARNING: 2022-11-22 17:46:17
                self._detected_mPSCs_ = [s for s in detection]
            else:
                # NOTE: see NOTE: 2022-11-27 13:49:44
                # self._detected_mPSCs_.clear()
                self._detected_mPSCs_ = list()
            #### END FIXME 2022-12-12 08:53:19
                

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
        
    @pyqtSlot(bool)
    def _slot_setOverlayTemplateModel(self, value):
        self.overlayTemplateModel = value
        self._plot_model_()
        
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
            
        self._plot_data()
            
        
#     @pyqtSlot()
#     def _slot_detect(self):
#         if self._data_ is None:
#             self.criticalMessage("Detect mPSC in current sweep",
#                                  "No data!")
#             return
#     
#             
#         waveform = self._get_mPSC_template_or_waveform_()
#         if waveform is None:
#             self.criticalMessage("Detect mPSC in current sweep",
#                                  "No mPSC waveform or template is available")
#             return
#         
#         if isinstance(self._data_, (neo.Block, neo.Segment)):
#             vartxt = f"in {self._data_.name}"
#         else:
#             vartxt = ""
#             
#         progressDisplay = QtWidgets.QProgressDialog(f"Detecting mPSCS {vartxt}", "Abort", 0, self._number_of_frames_, self)
# 
#         
#         # NOTE: 2022-11-26 09:06:16
#         #### BEGIN using QRunnable paradigm
#         # NOTE: 2022-11-25 22:15:47
#         # this cannot abort
#         worker = pgui.ProgressWorkerRunnable(self._detect_all_, progressDisplay)
#         
#         worker.signals.signal_Finished.connect(progressDisplay.reset)
#         worker.signals.signal_Result[object].connect(self._slot_detectionDone)
#         # NOTE: 2022-11-25 22:16:15 see NOTE: 2022-11-25 22:15:47
#         self.threadpool.start(worker)
#         #### END using QRunnable paradigm
#         
    @pyqtSlot()
    def _slot_detectionDone(self):
        # NOTE: 2022-11-26 09:06:05
        # QRunnable paradigm, see # NOTE: 2022-11-26 09:06:16
        self._plot_data()
        
    @pyqtSlot()
    def _slot_detectThread(self):
        # NOTE: 2022-11-26 10:24:01 IT WORKS !!!
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

        self._clear_detection_flag_ = self.clearPreviousDetectionCheckBox.isChecked() # to make sure this is up to date
            
        progressDisplay = QtWidgets.QProgressDialog(f"Detecting mPSCS {vartxt}", 
                                                    "Abort", 
                                                    0, self._number_of_frames_, 
                                                    self)
        
        # NOTE: 2022-11-26 21:48:56 - This is CRUCIAL:
        # the canceled signal from the progress dialog MUST be outside of the 
        # loop inside the worker thread; we control the loop execution using the 
        # mutable self.loopControl which we change in a  slot connected to the 
        # progressDialog.canceled() signal.
        # 
        # Throughout, progressDisplay (a GUI object) stays in the main thread
        # and in the main event loop) while the execution of the detection loop
        # (_detect_all_) takes place inside a QThread (self._detectThread_).
        #
        # To the loop execution can be stopped from OUTSIDE its thread, using a 
        # shared variable `self.loopControl`
        #
        # Here, self.loopControl is a dict with the mapping "break" ↦ False
        # This mapping is changed to "break" ↦ True in `self._slot_breakLoop`
        # called when progressDisplay.canceled() is emitted in the main thread.
        #
        # Because self.loopControl is shared with the worker thread, it is polled
        # at every loop cycle, thus breaking the loop when "break" ↦ True; once
        # the loop breaks, and the function executing the loop returns early,
        # causing the worker thread to finish naturally BEFORE the entire loop
        # has run its course.
        #
        # Of course, self.loopControl can be a bool instead of a dict with a
        # mapping to a bool. However, using a dict to wrap various flags is a 
        # generalizable paradigm (one can send other control data to the
        # worker thread, as long as the data is not an immutable state)
        #
        # To update the progress from INSIDE the worker thread, we use 
        # the worker's progress signal (here, `worker.signals.signal_Progress`)
        # connected to `progressDisplay.setValue` slot. 
        #
        # The function executing the loop (the worker function) needs the 
        # following parameters, for this mechanism to work:
        # • a reference to the self.loopControl loop control flag
        #
        # • a reference to a signal that, when emitted, increments (or sets) the 
        #   value in the progressDisplay; this should be emitted by the worker
        #   function after each cycle in the loop
        #
        # • a reference to a signal that should be emitted right before the 
        #   worker function returns; when emitted, it should cause the worker 
        #   thread to quit
        #
        # • any other var-positional, named and var-keyword parameters
        #
        # These parameters are NOT passed to the working function directly, but 
        # only indirectly via the `worker``instance of ProgressWorkerThreaded, 
        # and therefore they are supplied to its constructor
        #
        # In particular, the ProgressWorkerThreaded provides the incrementing
        # and the execution finished signals
        progressDisplay.canceled.connect(self._slot_breakLoop)
        
        # NOTE: 2022-11-26 11:24:32 see NOTE: 2022-11-26 11:22:38
        # self._detectController_.setProgressDialog(progressDisplay)
        # self._detectController_.sig_start.emit()
        
        # NOTE: 2022-11-26 11:24:51 see NOTE: 2022-11-26 11:23:21
        self._detectThread_ = QtCore.QThread()
        self._detectWorker_ = pgui.ProgressWorkerThreaded(self._detect_all_,
                                                        loopControl = self.loopControl,
                                                        clearLastDetection=self._clear_detection_flag_)
        self._detectWorker_.signals.signal_Progress.connect(progressDisplay.setValue)
        
        # self._detectWorker_ = pgui.ProgressWorkerThreaded(self._detect_all_, 
        #                                                 progressDisplay, 
        #                                                 clearLastDetection=self._clear_detection_flag_)
        
        self._detectWorker_.moveToThread(self._detectThread_)
        self._detectThread_.started.connect(self._detectWorker_.run) # see NOTE: 2022-11-26 16:56:19 below
        self._detectWorker_.signals.signal_Finished.connect(self._detectThread_.quit)
        self._detectWorker_.signals.signal_Finished.connect(self._detectWorker_.deleteLater)
        self._detectWorker_.signals.signal_Finished.connect(self._detectThread_.deleteLater)
        self._detectWorker_.signals.signal_Finished.connect(lambda : progressDisplay.setValue(progressDisplay.maximum()))
        self._detectWorker_.signals.signal_Result[object].connect(self._slot_detectThread_ready)
        
        # self._detectWorker_.signals.signal_Canceled.connect(self._detectThread_.quit)
        # self._detectWorker_.signals.signal_Canceled.connect(self._detectWorker_.deleteLater)
        
        self._detectThread_.finished.connect(self._detectWorker_.deleteLater)
        self._detectThread_.finished.connect(self._detectThread_.deleteLater)
        
        # progressDisplay.setValue(0) # causes the progres dialog to show imemdiately
        
        self._enable_widgets(self.actionDetect,
                             self.actionUndo,
                             self.actionDetect_in_current_sweep,
                             self.actionUndo_current_sweep,
                             self.actionClear_results,
                             self.accept_mPSCcheckBox,
                             self.actionView_results,
                             self.actionExport_results,
                             self.actionSave_results,
                             self.use_mPSCTemplate_CheckBox,
                             self.actionCreate_mPSC_Template,
                             self.actionOpen_mPSCTemplate,
                             self.actionImport_mPSCTemplate,
                             enable=False)
        
        self._detectThread_.start() # ↯ _detectThread_.started ↣ _detectWorker_.run NOTE: 2022-11-26 16:56:19
        
    @pyqtSlot(object)
    def _slot_detectThread_ready(self, result:object):
        """Called when threaded detection finished naturally or was interrupted.
        The parameter `result` is ignored.
        """
        # print(f"{self.__class__.__name__}._slot_detectThread_ready(result = {result})")
        self._plot_data()
        self._enable_widgets(self.actionDetect,
                             self.actionUndo,
                             self.actionDetect_in_current_sweep,
                             self.actionUndo_current_sweep,
                             self.actionClear_results,
                             self.accept_mPSCcheckBox,
                             self.actionView_results,
                             self.actionExport_results,
                             self.actionSave_results,
                             self.use_mPSCTemplate_CheckBox,
                             self.actionCreate_mPSC_Template,
                             self.actionOpen_mPSCTemplate,
                             self.actionImport_mPSCTemplate,
                             enable=True)
        
        self.loopControl["break"] = False
        
    @pyqtSlot(object)
    def _slot_filterThread_ready(self, obj):
        self._plot_data()
        self.loopControl["break"] = False
        
        
    @pyqtSlot()
    def _slot_breakLoop(self):
        """To be connected to the `canceled` signal of a progress dialog.
        Modifies the loopControl variable to interrrup a worker loop gracefully.
        """
        self.loopControl["break"] = True
        
    @pyqtSlot()
    def _slot_undoDetection(self):
        """Restores spiketrains before detection, in all data.
        TODO: update results
        """
        if isinstance(self._data_, neo.Block):
            for k in range(len(self._data_.segments)):
                self._undo_sweep(k)
                
        elif isinstance(self._data_, neo.Segment):
            self._undo_sweep(0)
            
        elif isinstance(self._data_, (tuple, list)) and all(isinstance(s, neo.Segment) for s in self._data_):
            for k in range(len(self._data_)):
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
    def _slot_useThresholdOnRsquared(self, value):
        self.useThresholdOnRsquared = value == QtCore.Qt.Checked
        if self.useThresholdOnRsquared:
            self._apply_Rsq_threshold(self.rSqThreshold, self.currentFrame, self.currentWaveformIndex)
    
    @pyqtSlot(int)
    def _slot_set_useSlidingDetection(self, value):
        self.useSlidingDetection = value == QtCore.Qt.Checked
    
    @pyqtSlot(int)
    def _slot_use_mPSCTemplate(self, value):
        self.useTemplateWaveForm = value == QtCore.Qt.Checked
        
    @pyqtSlot(int)
    def _slot_setClearDetectionFlag_(self, value):
        # TODO: 2022-11-18 10:12:34 
        # make configurable
        self.clearOldPSCs = value == QtCore.Qt.Checked
        
    @pyqtSlot()
    def _slot_saveEphysData(self):
        if self._data_ is None:
            return
        
        fileFilters = ["Pickle files (*.pkl)", "HDF5 Files (*.hdf)"]
        
        if self._last_used_file_save_filter_ in fileFilters:
            fileFilters = [self._last_used_file_save_filter_] + [f for f in fileFilters if f != self._last_used_file_save_filter_]
            
        fileName, fileFilter = self.chooseFile(caption="Save electrophysiology data",
                                               single=True,
                                               save=True,
                                               fileFilter=";;".join(fileFilters))
        
        # print(f"{self.__class__.__name__} _slot_saveEphysData fileFilter = {fileFilter}, type = {type(fileFilter).__name__}")
        if isinstance(fileFilter, str) and len(fileFilter.strip()):
            self.lastUsedFileSaveFilter = fileFilter
            
        if isinstance(fileName, str) and len(fileName.strip()):
            if "HDF5" in fileFilter:
                pio.saveHDF5(self._data_, fileName)
            else:
                pio.savePickleFile(self._data_, fileName)
                
    @pyqtSlot()
    def _slot_openTemplateFile(self):
        fileFilters = ["Pickle files (*.pkl)", "HDF5 Files (*.hdf)"]
        # NOTE 2022-11-27 22:16:24
        # we only operate with pickle and HDF5 files for template
        # so we use _last_used_file_save_filter_ for that purpose (KISS)
        if self._last_used_file_save_filter_ in fileFilters:
            fileFilters = [self._last_used_file_save_filter_] + [f for f in fileFilters if f != self._last_used_file_save_filter_]
            
        fileName, fileFilter = self.chooseFile(caption="Open mPSC template file",
                                               single=True,
                                               save=False,
                                               fileFilter=";;".join(fileFilters))
        
        if isinstance(fileName, str) and os.path.isfile(fileName):
            if "HDF5" in fileFilter:
                data = pio.loadHDF5File(fileName)
            elif "Pickle" in fileFilter:
                data = pio.loadPickleFile(fileName)
            else:
                return
                
            if isinstance(data, neo.AnalogSignal):
                self._mPSC_template_ = data
                self._plot_template_()
                self.use_mPSCTemplate_CheckBox.setEnabled(True)
                self.lastUsedTemplateFile = fileName
                
            # if isinstance(self._mPSC_template_, neo.AnalogSignal):
        
    @pyqtSlot()
    def _slot_saveTemplateFile(self):
        if not isinstance(self._mPSC_template_, neo.AnalogSignal):
            return
        
        fileFilters = ["Pickle files (*.pkl)", "HDF5 Files (*.hdf)"]
        if self._last_used_file_save_filter_ in fileFilters:
            fileFilters = [self._last_used_file_save_filter_] + [f for f in fileFilters if f != self._last_used_file_save_filter_]
            
        fileName, fileFilter = self.chooseFile(caption="Save mPSC template",
                                               single=True,
                                               save=True,
                                               fileFilter=";;".join(fileFilters))
        
        if isinstance(fileName, str) and len(fileName.strip()):
            if "HDF5" in fileFilter:
                pio.saveHDF5(self._mPSC_template_, fileName)
            else:
                pio.savePickleFile(self._mPSC_template_, fileName)
                
    @pyqtSlot()
    def _slot_openEphysDataFile(self):
        fileFilters = ["Axon files (*.abf)", "Pickle files (*.pkl)", "HDF5 Files (*.hdf)"]
        if self._last_used_file_open_filter_ in fileFilters:
            fileFilters = [self._last_used_file_open_filter_] + [f for f in fileFilters if f != self._last_used_file_open_filter_]
            
        
        fileName, fileFilter = self.chooseFile(caption="Open electrophysiology file",
                                               single=True,
                                               save=False,
                                               fileFilter=";;".join(fileFilters))
        
        # print(f"{self.__class__.__name__} _slot_openEphysDataFile fileFilter = {fileFilter}, type = {type(fileFilter).__name__}")
        if isinstance(fileFilter, str) and len(fileFilter.strip()):
            self.lastUsedFileOpenFilter = fileFilter
        
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
    def _slot_importTemplate(self):
        objs = self.importWorkspaceData(neo.AnalogSignal,
                                         title="Import mPSC Template",
                                         single=True,
                                         with_varName=True)
        
        if objs is None:
            return
        
        if len(objs) == 1:
            self._mPSC_template_ = objs[0]
            self._plot_template_()
            
        if isinstance(self._mPSC_template_, neo.AnalogSignal):
            self.use_mPSCTemplate_CheckBox.setEnabled(True)
        
            
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
    def _slot_storeTemplateAsDefault(self):
        """Stores mPSC template in the default template file"""
        if not isinstance(self._mPSC_template_, neo.AnalogSignal):
            return
        
        # TODO: 2022-11-27 22:04:11
        # see TODO: 2022-11-27 22:03:10 and TODO 2022-11-27 22:03:34
        if os.path.isfile(self.templateWaveFormFile):
            fn, ext = os.path.splitext(self.templateWaveFormFile)
            if "pkl" in ext:
                pio.savePickleFile(self._mPSC_template_, self.templateWaveFormFile)
            else:
                pio.saveHDF5(self._mPSC_template_, self.templateWaveFormFile)
                
    @pyqtSlot()
    def _slot_forgetTemplate(self):
        self._mPSC_template_ = None
        
    @pyqtSlot()
    def _slot_clearFactoryDefaultTemplateFile(self):
        if os.path.isfile(self._default_template_file):
            os.remove(self._default_template_file)
            
    @pyqtSlot()
    def _slot_makeUnitAmplitudeModel(self):
        α, β, x0, τ1, τ2 = [float(v) for v in self.mPSCParametersInitial.values()]
        
        β = models.get_CB_scale_for_unit_amplitude(β, τ1, τ2) # do NOT add x0 here because we only work on xx>=0
        
        init_params = [α * self._signal_units_, β * pq.dimensionless,
                       x0 * self._time_units_, 
                       τ1 * self._time_units_, τ2 * self._time_units_]
        
        lb = [float(v) for v in self.mPSCParametersLowerBounds.values()]
        ub = [float(v) for v in self.mPSCParametersUpperBounds.values()]
        
        sigBlock = QtCore.QSignalBlocker(self.paramsWidget)
        
        self.paramsWidget.setParameters(init_params,
                                        lower = lb,
                                        upper = ub,
                                        names = self._params_names_,
                                        refresh = True)
        
        self._plot_model_()
            
#     @pyqtSlot()
#     def _slot_chooseDefaultTemplateFile(self):
#         fileFilters = ["Pickle files (*.pkl)", "HDF5 Files (*.hdf)"]
#         # NOTE 2022-11-27 22:16:24
#         # we only operate with pickle and HDF5 files for template
#         # so we use _last_used_file_save_filter_ for that purpose (KISS)
#         if self._last_used_file_save_filter_ in fileFilters:
#             fileFilters = [self._last_used_file_save_filter_] + [f for f in fileFilters if f != self._last_used_file_save_filter_]
#             
#         fileName, fileFilter = self.chooseFile(caption="Open mPSC template file",
#                                                single=True,
#                                                save=False,
#                                                fileFilter=";;".join(fileFilters))
#         
#         if isinstance(fileName, str) and os.path.isfile(fileName):
#             self.customDefaultTemplateFile = fileName

    @pyqtSlot(int)
    def _slot_currentTabChanged(self, val):
        if val >= 0:
            self.currentTabIndex = val
            

    @pyqtSlot()
    def _slot_loadDefaultTemplate(self):
        if os.path.isfile(self.customDefaultTemplateFile):
            template_file = self.customDefaultTemplateFile
        elif os.path.isfile(self._template_file_):
            template_file = self._template_file_
        else:
            self.errorMessage("Load default mPSC template",
                              "No default template file was found.\nCreate a template and save as one of the defaults")
            return
        
        fn, ext = os.path.splitext(template_file)
            
        if "pkl" in ext:
            data = pio.loadPickleFile(template_file)
        elif any(s in ext for s in ("h5", "hdf5")):
            data = pio.loadHDF5File(template_file)
        else:
            self.errorMessage("Load default mPSC template",
                              f"Check the template file name; expecting a pickle or a HDF5 file, but got {template_file} instead")
            return
        
        if isinstance(data, neo.AnalogSignal):
            self._mPSC_template_ = data
            self._plot_template_()
            self.use_mPSCTemplate_CheckBox.setEnabled(True)
        else:
            self.errorMessage("Load default mPSC template",
                              "Default template file does not contain a signal")
            
            
    @pyqtSlot()
    def _slot_loadLastUsedTemplate(self):
        if os.path.isfile(self.lastUsedTemplateFile):
            fn, ext = os.path.splitext(self.lastUsedTemplateFile)
            if "pkl" in ext:
                data = pio.loadPickleFile(self.lastUsedTemplateFile)
            elif any(s in ext for s in ("h5", "hdf5")):
                data = pio.loadHDF5File(self.lastUsedTemplateFile)
            else:
                self.errorMessage("Load last used mPSC template",
                                f"Check the template file name; expecting a pickle or a HDF5 file, but got {self.lastUsedTemplateFile} instead")
                return
            
            if isinstance(data, neo.AnalogSignal):
                self._mPSC_template_ = data
                self._plot_template_()
                self.use_mPSCTemplate_CheckBox.setEnabled(True)
                
            else:
                self.errorMessage("Load last used mPSC template",
                                 f"Template file {self.lastUsedTemplateFile} does not contain a signal")
                return
            
        else:
            self.errorMessage("Load last used mPSC template",
                             f"Template file {self.lastUsedTemplateFile} not found!")
            
        
    @pyqtSlot()
    def _slot_revertToFactoryDefaultTemplateFile(self):
        self._template_file_ = self._default_template_file
            
    @pyqtSlot()
    def _slot_exportTemplate(self):
        if not isinstance(self._mPSC_template_, neo.AnalogSignal):
            return
        
        self.exportDataToWorkspace(self._mPSC_template_, var_name = "mPSC_template")
            
    @pyqtSlot()
    def _slot_exportEphysData(self):
        if self._data_ is None:
            return
        
        self.exportDataToWorkspace(self._data_, var_name=self.metaDataWidget.dataVarName)
    
    @pyqtSlot()
    def _slot_exportModelWaveformToWorkspace(self):
        modelWave = self.modelWave()
        self.exportDataToWorkspace(modelWave, var_name = "modelWaveform")
    
    @pyqtSlot()
    def _slot_plotData(self):
        if self._data_ is not None:
            self._plot_data()
            
    @pyqtSlot()
    def _slot_useSignalDetrend(self):
        value = self.sender().checkState() == QtCore.Qt.Checked
        self.useSignalDetrend = value
        
    @pyqtSlot()
    def _slot_useHumbug(self):
        value = self.sender().checkState() == QtCore.Qt.Checked
        self.useHumbug = value
            
    @pyqtSlot()
    def _slot_set_removeDC(self):
        removeDC = self.sender().checkState() == QtCore.Qt.Checked
        self.removeDCOffset = removeDC
        
    @pyqtSlot()
    def _slot_setAutoOffset(self):
        value = self.sender().checkState() == QtCore.Qt.Checked
        self.useAutoOffset = value
        
        
    @pyqtSlot(object)
    def _slot_DCOffsetChanged(self, val):
        self.signalDCOffset = val
        
    @pyqtSlot()
    def _slot_set_useLowPassFilter(self):
        val = self.sender().checkState() == QtCore.Qt.Checked
        self.useLowPassFilter = val
        filterType = self.filterTypeComboBox.currentText()
        
        
    @pyqtSlot(object)
    def _slot_cutoffFreqChanged(self, val):
        self.noiseCutoffFreq = val
        
    @pyqtSlot()
    def _slot_applyFilters_with_detection(self):
        self.filterDataUponDetection = self.sender().isChecked()
        
    @pyqtSlot()
    def _slot_filterData(self):
        if self._data_ is None:
            self.criticalMessage("Detect mPSC in current sweep",
                                 "No data!")
            return
            
        if isinstance(self._data_, (neo.Block, neo.Segment)):
            vartxt = f"in {self._data_.name}"
        else:
            vartxt = ""

        progressDisplay = QtWidgets.QProgressDialog(f"Filtering data {vartxt}", 
                                                    "Abort", 
                                                    0, self._number_of_frames_, 
                                                    self)
        
        progressDisplay.canceled.connect(self._slot_breakLoop)
        self._filterThread_ = QtCore.QThread()
        self._filterWorker_ = pgui.ProgressWorkerThreaded(self._filter_all_,
                                                        loopControl = self.loopControl,
                                                        clearLastDetection=self._clear_detection_flag_)
        self._filterWorker_.signals.signal_Progress.connect(progressDisplay.setValue)
        
        self._filterWorker_.moveToThread(self._filterThread_)
        self._filterThread_.started.connect(self._filterWorker_.run) # see NOTE: 2022-11-26 16:56:19 below
        self._filterWorker_.signals.signal_Finished.connect(self._filterThread_.quit)
        self._filterWorker_.signals.signal_Finished.connect(self._filterWorker_.deleteLater)
        self._filterWorker_.signals.signal_Finished.connect(self._filterThread_.deleteLater)
        self._filterWorker_.signals.signal_Finished.connect(lambda : progressDisplay.setValue(progressDisplay.maximum()))
        self._filterWorker_.signals.signal_Result[object].connect(self._slot_filterThread_ready)
        self._filterThread_.finished.connect(self._filterWorker_.deleteLater)
        self._filterThread_.finished.connect(self._filterThread_.deleteLater)
        
        self._filterThread_.start()
        
    def _process_signal_(self, sig, newFilter:bool=False):
        if isinstance(sig, (neo.AnalogSignal, DataSignal)):
            fs = float(sig.sampling_rate)
        else:
            fs = float(self._default_sampling_rate_)
            
        ret = sig
        
        # processed=False
        
        if self._use_signal_linear_detrend_:
            ret = sigp.detrend(ret, axis=0, bp = [0, ret.shape[0]], type="linear")
            # processed=True

        if self._remove_DC_offset_:
            if self._use_auto_offset_:
                ret = sigp.remove_dc(ret)
            else:
                ret = sigp.remove_dc(ret, self._dc_offset_)
            # processed=True
            
        if self._humbug_:
            ret = self._deHum(ret, fs)
                
        if self._filter_signal_:
            ret = self._lowpass_filter_signal(ret, makeFilter=newFilter)
            # processed=True
            
        # if processed:
        #     name = getattr(ret, "name", None)
        #     if isinstance(name, str) and len(name.strip()):
        #         ret.name = f"processed_{name}"
        #     else:
        #         ret.name = "processed"
            
        return ret
        
    def _filter_all_(self, **kwargs):
        if self._data_ is None:
            return
        
        if not any(self._remove_DC_offset_, self._filter_signal_):
            return
        
        signal_index = self.signalNameComboBox.currentIndex()
        
        new_segments = list()
        
        for frame in self.frameIndex:
            segment = self._get_data_segment_(frame)
            new_seg = neo.Segment(name=segment.name)
            
            for k in range(len(segment.analogsignals)):
                signal = segment.analogsignals[k]
                if k == signal_index:
                    new_sig = self._process_signal_(neoutils.make_neo_object(signal))
                else:
                    new_sig = neoutils.make_neo_object(signal)
                    
                new_sig.segment = new_seg
                        
                new_seg.analogsignals.append(new_sig)
                
            new_segments.append(new_seg)
            
            if isinstance(progressSignal, QtCore.pyqtBoundSignal):
                progressSignal.emit(frame)
                
            if isinstance(loopControl, dict) and loopControl.get("break",  None) == True:
                break
            
        if isinstance(self._data_, neo.Block):
            self._filtered_data_ = neo.Block()
            for s in new_segments:
                s.block = self._filtered_data_
                self._filtered_data_.segments.append(s)
            
        elif isinstance(self._data_, neo.Segment):
            self._filtered_data_ = new_segments[0]
            
        elif isinstance(self._data_, (tuple, list)) and all(isinstance(s, neo.Segment) for s in self._data_):
            self._filtered_data_ = new_segments
        
    @pyqtSlot()
    def _slot_set_mPSC_accept(self):
        if len(self._detected_mPSCs_) == 0:
            return
        
        if self.currentWaveformIndex not in range(-len(self._detected_mPSCs_),
                                                  len(self._detected_mPSCs_)):
            return
        
        # accept = value == QtCore.Qt.Checked
        accept = self.sender().checkState() == QtCore.Qt.Checked
        
        # NOTE: 2022-11-27 14:38:05
        # the waves in self._detected_mPSCs_ are a reference to the detection
        # result; chaging their annotations will affect the data in there
        # but not in the psc train, so we need to set them both here.
        #
        # On the other hand, the results table HAS TO be updated manually.
        # (it is a DataFrame storing plain values, NOT references)
        #
        # • store previous accepted result in cache
        #
        if accept:
            self._accept_waves_cache_[self.currentFrame].add(self.currentWaveformIndex)
        else:
            if self.currentWaveformIndex in self._accept_waves_cache_[self.currentFrame]:
                self._accept_waves_cache_[self.currentFrame].remove(self.currentWaveformIndex)
        #
        # • update the Accept state in the wave annotations
        self._detected_mPSCs_[self.currentWaveformIndex].annotations["Accept"] = accept
        #
        # • update the Accept state for the corresponding time stamp in the mPSC
        #   spike train
        train = self._result_[self.currentFrame][0]
        
        train.annotations["Accept"][self.currentWaveformIndex] = accept
        #
        # • refresh mPSC indicator on the main data plot
        self._indicate_mPSC_(self.currentWaveformIndex)
        #
        # • refresh the results table (DataFrame); to save time, we only do it
        #   if the report window is showing
        if self._reportWindow_.isVisible():
            self._update_report_()
        
# NOTE: 2022-11-27 14:44:37
# Not sure how useful this is; for fitting we use the initial values of the 
# model parameters, plus their lower & upper bounds. Tweaking these won't
# necessarily improve the accepting of a detected wave, but will almost surely
# have an impact on later detections because the new parametyer intial values
# and bounds will be saved across sessions.
# FIXME DO NOT DELETE: may come back to this
#     @pyqtSlot()
#     def _slot_refit_mPSC(self):
#         """Not sure how refitting helps
#         """
#         self._detected_mPSCs_ = self._result_[self.currentFrame][1]
#         
#         if len(self._detected_mPSCs_) == 0:
#             return
#         
#         
#         if self.currentWaveformIndex not in range(-len(self._detected_mPSCs_),
#                                                   len(self._detected_mPSCs_)):
#             return
#         
#         # print(f"{self.__class__.__name__}._slot_refit_mPSC: currentWaveformIndex = {self.currentWaveformIndex}")
#         
#         mini = self._detected_mPSCs_[self.currentWaveformIndex]
#         
#         w = mini[:,0]
#         model_params = self.paramsWidget.value()
#         init_params = tuple(p.magnitude for p in model_params["Initial Value:"])
#         lo = tuple(p.magnitude for p in model_params["Lower Bound:"])
#         up = tuple(p.magnitude for p in model_params["Upper Bound:"])
#         w = membrane.fit_mPSC(w, init_params, lo=lo, up=up)
#         w.annotations["t_peak"]=mini.annotations["t_peak"]
#         # don;t change accept state here, do it manually in gui if fitting got better
#         w.annotations["Accept"]=mini.annotations["Accept"]
#         w.name = mini.name
#         
#         # print(f"{self.__class__.__name__}._slot_refit_mPSC: w.annotations = {w.annotations}")
#         
#         # self._detected_mPSCs_[self.currentWaveformIndex] = fw
#         
#         self._indicate_mPSC_(self.currentWaveformIndex)
        
        
        
            
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
    def _slot_rsqThresholdChanged(self, value:float):
        self.rSqThreshold = self.rsqThresholdDoubleSpinBox.value()
        if self.useThresholdOnRsquared:
            self._apply_Rsq_threshold(self.rSqThreshold)
            
    @pyqtSlot(float)
    def _slot_detectionThresholdChanged(self, value:float):
        self.detectionThreshold = value
        
    @pyqtSlot(float)
    def _slot_modelDurationChanged(self, value:float):
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
    def _slot_filterTypeChanged(self, val:str):
        if val in self._available_filters_:
            self.filterType = val
            
    
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
        if not self._template_showing_:
            self._currentWaveformIndex_ = value
            self._indicate_mPSC_(self.currentWaveformIndex)
        
        # NOTE: avoid this because currentFrame setter in SignalViewer emits
        # frameChanged, causing infinite recursion
        # self.displayDetectedWaveform(value)
        
            
    @pyqtSlot(int)
    def _slot_setWaveFormIndex(self, value):
        if self._template_showing_:
            if value not in range(-len(self._mPSCs_for_template_), len(self._detected_mPSCs_)):
                return
        else:
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
    def lastUsedFileSaveFilter(self):
        return self._last_used_file_save_filter_
    
    @markConfigurable("FileSaveFilter", trait_notifier=True)
    @lastUsedFileSaveFilter.setter
    def lastUsedFileSaveFilter(self, value:str):
        # FIXME/BUG 2022-11-26 17:34:21 called twice, second time with the type of value
        # print(f"{self.__class__.__name__}. @lastUsedFileSaveFilter.setter value = {value}")
        self._last_used_file_save_filter_ = value
        
    @property
    def lastUsedTemplateFile(self):
        return self._last_used_template_file_name
    
    @markConfigurable("LastUsedTemplateFile")#, trait_notifier=True)
    @lastUsedTemplateFile.setter
    def lastUsedTemplateFile(self, value):
        if os.path.isfile(value):
            self._last_used_template_file_name = value
            self.configurable_traits["LastUsedTemplateFile"] = self._last_used_template_file_name
        
    @property
    def customDefaultTemplateFile(self):
        return self._custom_template_file_
    
    @markConfigurable("CustomDefaultTemplateFile")
    @customDefaultTemplateFile.setter
    def customDefaultTemplateFile(self, value):
        if os.path.isfile(value):
            self._custom_template_file_ = value
            self.configurable_traits["CustomDefaultTemplateFile"] = self._custom_template_file_
            
    @property
    def currentTabIndex(self):
        return self._currentTabIndex_
    
    @markConfigurable("CurrentTabIndex", "Qt", value_type=int)
    @currentTabIndex.setter
    def currentTabIndex(self, val:int):
        if val >= 0:
            self._currentTabIndex_ = val
            sigBlock = QtCore.QSignalBlocker(self.tabWidget)
            self.tabWidget.setCurrentIndex(val)
    
    @property
    def lastUsedFileOpenFilter(self):
        return self._last_used_file_open_filter_
    
    @markConfigurable("FileOpenFilter", trait_notifier=True)
    @lastUsedFileOpenFilter.setter
    def lastUsedFileOpenFilter(self, value:str):
        # FIXME/BUG: 2022-11-26 17:35:08 see FIXME/BUG 2022-11-26 17:34:21 
        # print(f"{self.__class__.__name__}. @lastUsedFileOpenFilter.setter value = {value}")
        self._last_used_file_open_filter_ = value
        
    @property
    def useThresholdOnRsquared(self):
        return self._use_threshold_on_rsq_
            
    @markConfigurable("UseThresholdOnRsquared", trait_notifier=True)
    @useThresholdOnRsquared.setter
    def useThresholdOnRsquared(self, value):
        self._use_threshold_on_rsq_ = value == True
        signalBlock = QtCore.QSignalBlocker(self.rsqThresholdCheckBox)
        self.rsqThresholdCheckBox.setChecked(self._use_threshold_on_rsq_)
        
    @property
    def filterDataUponDetection(self):
        return self._apply_filter_upon_detection
    
    
    @markConfigurable("ApplyFiltersUponDetection", trait_notifier=True)
    @filterDataUponDetection.setter
    def filterDataUponDetection(self, value:bool):
        self._apply_filter_upon_detection = value == True
        sigBlock = QtCore.QSignalBlocker(self.actionApply_with_detection)
        self.actionApply_with_detection.setChecked(self._apply_filter_upon_detection == True)
        
    @property
    def removeDCOffset(self):
        return self._remove_DC_offset_
    
    @markConfigurable("RemoveSignalDCOffset", trait_notifier=True)
    @removeDCOffset.setter
    def removeDCOffset(self, val:bool):
        self._remove_DC_offset_ = val == True
        sigBlock = QtCore.QSignalBlocker(self.removeDCCheckBox)
        self.removeDCCheckBox.setChecked(self._remove_DC_offset_)
        self.autoOffsetCheckBox.setEnabled(self._remove_DC_offset_)
        for w in (self.offsetLabel, self.dcValueSpinBox):
            w.setEnabled(not self._use_auto_offset_)
        
        # self.noiseFilterCheckBox.setEnabled(self._filter_signal_ == True or self._remove_DC_offset_ == True)
        if self.actionLive_filter_preview.isChecked():
            self._slot_previewFilteredSignal()
        
    @property
    def useAutoOffset(self):
        return self._use_auto_offset_
    
    @markConfigurable("UseAutoDCOffset", trait_notifier=True)
    @useAutoOffset.setter
    def useAutoOffset(self, val:bool):
        self._use_auto_offset_ = val == True
        sigBlock = QtCore.QSignalBlocker(self.autoOffsetCheckBox)
        self.autoOffsetCheckBox.setChecked(self._use_auto_offset_)
        for w in (self.offsetLabel, self.dcValueSpinBox):
            w.setEnabled(not self._use_auto_offset_)
        if self.actionLive_filter_preview.isChecked():
            self._slot_previewFilteredSignal()
        
    @property
    def signalDCOffset(self):
        return self._dc_offset_
    
    @markConfigurable("SignalDCOffset", trait_notifier=True)
    @signalDCOffset.setter
    def signalDCOffset(self, val):
        self._dc_offset_ = val
        sigBlock = QtCore.QSignalBlocker(self.dcValueSpinBox)
        self.dcValueSpinBox.setValue(val)
        if self.actionLive_filter_preview.isChecked():
            self._slot_previewFilteredSignal()
            
    @property
    def noiseCutoffFreq(self):
        return self._noise_cutoff_frequency_
    
    @markConfigurable("NoiseFrequencyCutoff",trait_notifier=True)
    @noiseCutoffFreq.setter
    def noiseCutoffFreq(self, val):
        self._noise_cutoff_frequency_ = val
        # print(f"NoiseFrequencyCutoff = {val}")
        sigBlock = QtCore.QSignalBlocker(self.cutoffFrequencySpinBox)
        self.cutoffFrequencySpinBox.setValue(self._noise_cutoff_frequency_)
        if self.actionLive_filter_preview.isChecked():
            self._slot_previewFilteredSignal()
        
    @property
    def useLowPassFilter(self):
        return self._filter_signal_
    
    @markConfigurable("LowPassFilterSignal", trait_notifier=True)
    @useLowPassFilter.setter
    def useLowPassFilter(self, val:bool):
        self._filter_signal_ = val == True
        sigBlock = QtCore.QSignalBlocker(self.noiseFilterCheckBox)
        self.noiseFilterCheckBox.setChecked(self._filter_signal_ == True)
        for w in (self.freqCutoffLabel, self.cutoffFrequencySpinBox):
            w.setEnabled(self._filter_signal_ == True)
            
        # self.noiseFilterCheckBox.setEnabled(self._filter_signal_ == True or self._remove_DC_offset_ == True or self._use_signal_linear_detrend_ == True)
        if self.actionLive_filter_preview.isChecked():
            self._slot_previewFilteredSignal()
            
    @property
    def useSignalDetrend(self):
        return self._use_signal_linear_detrend_
    
    @markConfigurable("UseLinearDetrend", trait_notifier=True)
    @useSignalDetrend.setter
    def useSignalDetrend(self, value:bool):
        self._use_signal_linear_detrend_ = value == True
        sigBlock = QtCore.QSignalBlocker(self.linearDetrendCheckBox)
        self.linearDetrendCheckBox.setChecked(self._use_signal_linear_detrend_)
        
    @property
    def useHumbug(self):
        return self._humbug_
    
    @markConfigurable("UseHumbug", trait_notifier=True)
    @useHumbug.setter
    def useHumbug(self, val):
        self._humbug_ = val == True
        sigBlock = QtCore.QSignalBlocker(self.deHumCheckBox)
        self.deHumCheckBox.setChecked(self._humbug_)
        
    @property
    def useSlidingDetection(self):
        return self._use_sliding_detection_
    
    @markConfigurable("UseSlidingDetection", trait_notifier=True)
    @useSlidingDetection.setter
    def useSlidingDetection(self, value:bool):
        self._use_sliding_detection_ = value == True
        sigBlocker = QtCore.QSignalBlocker(self.useSlidingDetectionCheckBox)
        self.useSlidingDetectionCheckBox.setChecked(self._use_sliding_detection_)
        
    @property
    def rSqThreshold(self):
        return self._rsq_threshold_
    
    @markConfigurable("RsquaredThreshold")# , trait_notifier=True)
    @rSqThreshold.setter
    def rSqThreshold(self, value:float):
        if isinstance(value, float) and value >=0. and value <= 1.:
            self._rsq_threshold_ = value
            signalBlocker = QtCore.QSignalBlocker(self.rsqThresholdDoubleSpinBox)
            self.rsqThresholdDoubleSpinBox.setValue(self._rsq_threshold_)
            self.configurable_traits["RsquaredThreshold"] = value
        
    @property
    def useTemplateWaveForm(self):
        return self._use_template_
    
    @markConfigurable("UseTemplateWaveForm", trait_notifier=True)
    @useTemplateWaveForm.setter
    def useTemplateWaveForm(self, value):
        # print(f"{self.__class__.__name__} @useTemplateWaveForm.setter value: {value}")
        self._use_template_ = value == True
        # if isinstance(getattr(self, "configurable_traits", None), DataBag):
        #     self.configurable_traits["UseTemplateWaveForm"] = self._use_template_
            
    @property
    def overlayTemplateModel(self):
        return self._overlayTemplateModel
    
    @markConfigurable("OverlayTemplateModel", trait_notifier=True)
    @overlayTemplateModel.setter
    def overlayTemplateModel(self, value):
        self._overlayTemplateModel = value == True
        
    @property
    def templateWaveFormFile(self):
        return self._template_file_
    
    @markConfigurable("TemplateWaveFormFile", trait_notifier=True)
    @templateWaveFormFile.setter
    def templateWaveFormFile(self, value:str):
        # print(f"{self.__class__.__name__} @templateWaveFormFile.setter value: {value}")
        import os
        if isinstance(value, str) and os.path.isfile(value):
            self._template_file_ = value
            
        else:
            self._template_file_ = self._default_template_file
    
    @property
    def clearOldPSCs(self):
        return self._clear_detection_flag_
    
    @markConfigurable("ClearOldPSCsOnDetection", trait_notifier=True)
    @clearOldPSCs.setter
    def clearOldPSCs(self, value):
        # print(f"{self.__class__.__name__} @clearOldPSCs.setter value: {value}")
        self._clear_detection_flag_ = value == True
        # self.configurable_traits["ClearOldPSCsOnDetection"] = self._clear_detection_flag_
        # if isinstance(getattr(self, "configurable_traits", None), DataBag):

    @property
    def detectionThreshold(self):
        return self._detection_threshold_
    
    @markConfigurable("DetectionThreshold")
    @detectionThreshold.setter
    def detectionThreshold(self, value:float):
        if self.useSlidingDetection:
            if value < 0.:
                value = 0
            
        else:
            if value < self._detection_threshold_linear_range_min_:
                value = self._detection_threshold_linear_range_min_
                
            if value > self._detection_threshold_linear_range_max_:
                value = self._detection_threshold_linear_range_max_
            
            
        self._detection_threshold_ = value
        self.configurable_traits["DetectionThreshold"] = value
        
        sigBlock = QtCore.QSignalBlocker(self.detectionThresholdSpinBox)
        if self.useSlidingDetection:
            self.detectionThresholdSpinBox.setMinimum(0)
            self.detectionThresholdSpinBox.setMaximum(math.inf)
            self.detectionThresholdSpinBox.setToolTip("Sliding detection threshold [0 .. Inf]")
        else:
            self.detectionThresholdSpinBox.setMinimum(self._detection_threshold_linear_range_min_)
            self.detectionThresholdSpinBox.setMaximum(self._detection_threshold_linear_range_max_)
            self.detectionThresholdSpinBox.setToolTip(f"Cross-correlation relative threshold [{self._detection_threshold_linear_range_min_} .. {self._detection_threshold_linear_range_max_}]")
            
        if value != self.detectionThresholdSpinBox.value():
            self.detectionThresholdSpinBox.setValue(self._detection_threshold_)

    @property
    def mPSCDuration(self):
        return self._mPSCduration_
    
    @markConfigurable("mPSC_Duration", trait_notifier=True)
    @mPSCDuration.setter
    def mPSCDuration(self, value):
        # print(f"{self.__class__.__name__} @mPSCDuration.setter value: {value}")
        self._mPSCduration_ = value
        # self.configurable_traits["mPSC_Duration"] = self._mPSCduration_

    @property
    def mPSCParametersInitial(self):
        """Initial parameter values
        """
        return dict(zip(self._params_names_, self._params_initl_))
    
    # NOTE: 2022-11-28 16:40:23
    # Bypass default traut_nptofoer, since confuse / yaml cannot cope with a pandas Series
    @markConfigurable("mPSCParametersInitial") # , trait_notifier=True) bypass default mechanism!
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
    
    @markConfigurable("mPSCParametersLowerBounds")# , trait_notifier=True) see NOTE: 2022-11-28 16:40:23
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
                
    @property
    def mPSCParametersUpperBounds(self):
        return dict(zip(self._params_names_, self._params_upper_))
    
    @markConfigurable("mPSCParametersUpperBounds") # , trait_notifier=True) see NOTE: 2022-11-28 16:40:23
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
                
    @property
    def filterType(self):
        return self._filter_type_
    
    @markConfigurable("FilterType", trait_notifier=True)
    @filterType.setter
    def filterType(self, val:str):
        if val in self._available_filters_:
            self._filter_type_ = val
            ndx = self._available_filters_.index(val)
            sigBlock = QtCore.QSignalBlocker(self.filterTypeComboBox)
            self.filterTypeComboBox.setCurrentIndex(ndx)

        if self.actionLive_filter_preview.isChecked():
            self._slot_previewFilteredSignal()
            
            # self._make_filter(self._filter_type_)
            
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
        for toolbar in (self.mainToolBar, self.detectionToolBar, self.templateToolBar, self.filterToolBar):
            toolbar.setFloatable(not self._toolbars_locked_)
            toolbar.setMovable(not self._toolbars_locked_)
            
        signalBlocker = QtCore.QSignalBlocker(self.actionLock_toolbars)
        self.actionLock_toolbars.setChecked(self._toolbars_locked_)
        
    def modelWave(self):
        return self._get_mPSC_template_or_waveform_(use_template = False)
    
    def templateWave(self):
        if isinstance(self._mPSC_template_, neo.AnalogSignal) and self._mPSC_template_.name == "mPSC Template":
            return self._mPSC_template_
        
    def _deHum(self, sig, fs):
        fn = fs/2
        notch = scipy.signal.iirnotch(self._humbug_notch_freq_, self._humbug_Q_, fs=fs)
        notchsos = scipy.signal.tf2sos(*notch)
        if isinstance(sig, (neo.AnalogSignal, DataSignal)):
            ret = sigp.sosfilter(sig, notchsos)
            # ret = scipy.signal.sosfiltfilt(notchsos, sig.magnitude, axis=0)
            klass = sig.__class__
            # name = sig.name
            # if isinstance(name, str) and len(name.strip()):
            #     name = f"{name}_{de}"
            # else:
            #     name = f"{self._filter_type_}"
            ret = klass(ret, units = sig.units, t_start =  sig.t_start,
                                sampling_rate = sig.sampling_rate,
                                name=sig.name, 
                                description = sig.description)
            ann = sig.array_annotations
            for key in ann:
                ret.array_annotations[key] = ann[key]
        else:
            ret = scipy.signal.sosfiltfilt(notchsos, sig, axis=0)
            
        return ret
        
    def _lowpass_filter_signal(self, sig, makeFilter:bool=False, fs=None):
        if self._lowpass_ is None or makeFilter == True:
            if fs is None:
                fs = float(self._default_sampling_rate_)
            self._make_lowpass(sig, fs)

        if isinstance(sig, (neo.AnalogSignal, DataSignal)):
            ret = sigp.sosfilter(sig, self._lowpass_)
            if isinstance(sig.name, str) and len(sig.name.strip()):
                name = f"{sig.name}_{self._filter_type_}"
            else:
                name = f"{self._filter_type_}"
                
            ret.name = name
            ret.description = f"{sig.description} Lowpass {self._filter_type_} cutoff {self._noise_cutoff_frequency_}"
            ann = sig.array_annotations
            for key in ann:
                if key == "channel_names":
                    val = f"{ann[key]} filtered"
                else:
                    val = ann[key]
                ret.array_annotations[key] = val
            
        else:
            ret = sigp.sosfilter(self._lowpass_, sig, axis=0)
                
        return ret
    
    def _make_lowpass(self, sig, fs=None):
        if isinstance(sig, (neo.AnalogSignal, DataSignal)):
            fs = float(sig.sampling_rate)
            
        elif not isinstance(fs, float):
            raise TypeError("For numpy arrays, sampling frequency (fs) must be specified")
        
        if self._filter_type_ == "Butterworth":
            self._make_butterworth(fs)
            
        elif self._filter_type_ == "Hamming":
            self._make_hamming(fs)
            
        else:
            self._make_remez(fs)
        
    def _make_butterworth(self, fs):
        lporder = scipy.signal.buttord(float(self._noise_cutoff_frequency_),
                                       1.25 * float(self._noise_cutoff_frequency_),
                                       1, 50, fs=fs)
        
        lowpass = scipy.signal.butter(*lporder, btype="lowpass", 
                                      fs=fs, output="sos")
        
        self._lowpass_ = lowpass
        
    def _make_hamming(self, fs):
        fn = fs/2
        fc = float(self._noise_cutoff_frequency_)
        fw = fc/2
        ntaps = int(50 * fs / (22 * fw))
        if ntaps % 2 == 0:
            ntaps += 1
        
        lowpass = scipy.signal.firwin(ntaps, fc,
                                      window="hamming", pass_zero="lowpass",
                                      fs=fs)
        
        self._lowpass_ = scipy.signal.tf2sos(lowpass, [1])
        
    def _make_remez(self, fs):
        fn = fs/2
        fc = float(self._noise_cutoff_frequency_)
        fw = fc/2
        ntaps = int(50 * fs / (22 * fw))
        # ntaps = int(50 * fs / (22 * float(self._noise_cutoff_frequency_)* 0.5))
        if ntaps % 2 == 0:
            ntaps += 1
            
        lowpass = scipy.signal.remez(ntaps, [0, fc, fc+fw, fn], [1,0], fs=fs)
        
        # self._lowpass_ = lowpass
        self._lowpass_ = scipy.signal.tf2sos(lowpass, [1])
        
    def result(self):
        """Retrieve the detection result.
        The result is output as a tuple with three elements:
        
        • mPSC table (a pandas.DataFrame object)
            This contains the start time, peak time, fitted parameters and R² 
            goodness of fit for ALL detected mPSC waveforms in the data regardless
            of whether they have been manually accepted or not (their accepted 
            status is indicated in the "Accept" column of the DataFrame object).
        
            The columns of the DataFrame object are:
        
           "Source", "Cell", "Field", "Age", "Sex", "Genotype" → with the values
                shown inthe top half of the mPSC Detect window
        
            "Data": the name of the electrophysiology record used for detection
            "Date Time": date & time of detection
            "Accept": value of the Accept flag
            "Sweep": index of the sweep (data segment) where the mPSC wave was 
                    detected
            "Wave": index of the mPSC wave in the list of mPSCs in the sweep
                    (see above)
            "Start Time": start time of the mPSC waveform including its initial
                baseline; these are NOT the times of the onset of the rising
                phase. The latter cann be calculated as start time + onset (see 
                below).
        
            "Peak Time": time of the mPSC peak (for outward currents) or trough
                        (for inward currents)
            "Amplitude": amplitude of the mPSC waveform,
            "Template": whether a template mPSC was used in detection
            "Fit Amplitude": amplitue of the fitted curve
            "R²": goodnesss of fit
        
            The following are the fitted model parameters for each wave:
            "α": offset (DC component), 
            "β": scale, 
            "Onset (x₀)": onset of the 'rising' phase, 
            "Rise Time (τ₁)": rising phase time constant
            "Decay Time (τ₂)": decay phase time constant
        
        
        • mPSC spiketrains (a list of neo.SpikeTrain objects), each containing
            the time stamps for the start of the mPSCs (one spike train per
            sweep of recording). The 'annotations' attributes of the spike train
            contains the peak times of the mPSC waves (as an array), and the
            'waveforms' attribute contains the actual detected mPSC waveforms.
        
        • the detected mPSC waveforms (a list of one neo.AnalogSignal object 
            
            representing detected mPSC waveform, with the membrane current in channel 0 and
            the fitted curve in channel 1)
        
        
        """
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
                # NOTE: 2022-11-27 14:18:08
                # this should be equal to the corresponding time stamp in the 
                # psc train for the parent sweep, but no programmatic checks
                # are made (although the train's times ARE set to be the 
                # detection start times, see self._detect_sweep_)
                start_time.append(float(w.t_start)) 
                peak_time.append(float(w.annotations["t_peak"]))
                amplitude.append(float(w.annotations["amplitude"]))
                from_template.append(w.annotations["mPSC_fit"]["template"])
                fit_amplitude.append(float(w.annotations["mPSC_fit"]["amplitude"]))
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
               "R²": r2, "α":offset, "β": scale, "Onset (x₀)": onset, "Rise Time (τ₁)": tau_rise, "Decay Time (τ₂)": tau_decay}
        
        res_df = pd.DataFrame(res)
        
        return res_df, psc_trains, all_waves
    
    
