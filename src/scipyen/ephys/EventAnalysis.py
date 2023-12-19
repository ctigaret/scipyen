# -*- coding: utf-8 -*-
import os, typing, math, datetime, logging, traceback, warnings, inspect
from numbers import (Number, Real,)
# from itertools import chain

from IPython.core.magic import (Magics, magics_class, line_magic,
                                cell_magic, line_cell_magic,
                                needs_local_scope)

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

from core.scipyen_config import (markConfigurable, get_config_file)

from core.quantities import (arbitrary_unit, check_time_units, units_convertible,
                            unit_quantity_from_name_or_symbol, str2quantity)

# from core.datatypes import UnitTypes
from core.strutils import numbers2str
from ephys import membrane

import ephys.ephys as ephys

from core.prog import safeWrapper

from core.workspacefunctions import get_symbol_in_namespace

from core.sysutils import adapt_ui_path

from gui import quickdialog as qd
import gui.scipyenviewer as scipyenviewer
from gui.scipyenviewer import ScipyenFrameViewer
# import gui.signalviewer as sv
# from gui.signalviewer import SignalCursor as SignalCursor
import gui.signalviewer as sv
from gui.cursors import (SignalCursor, SignalCursorTypes)
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
from gui.pyqtgraph_patch import pyqtgraph as pg
from gui.pyqtgraph_symbols import (spike_Symbol, 
                                    event_Symbol, event_dn_Symbol, 
                                    event2_Symbol, event2_dn_Symbol)


import iolib.pictio as pio

__module_path__ = os.path.abspath(os.path.dirname(__file__))

__Ui_EventDetectWindow__, __QMainWindow__ = __loadUiType__(os.path.join(__module_path__, "EventDetectWindow.ui"))

class EventAnalysis(ScipyenFrameViewer, __Ui_EventDetectWindow__):
    sig_AbortDetection = pyqtSignal(name="sig_AbortDetection")
    # NOTE: this refers to the type of data where event detection is done.
    # The event waveform viewer only expects neo.AnalogSignal
    # viewer_for_types = (neo.Block, neo.Segment, type(None))
    viewer_for_types = tuple()
    
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
    
    _default_template_file = os.path.join(os.path.dirname(get_config_file()),"eventTemplate.h5" )
    
    # def __init__(self, ephysdata=None, clearOldPSCs=False, ephysViewer:typing.Optional[sv.SignalViewer]=None, parent:(QtWidgets.QMainWindow, type(None)) = None, win_title="Detect Events", **kwargs):
    def __init__(self, ephysdata=None, clearOldPSCs=False, ephysViewer:typing.Optional[sv.SignalViewer]=None, parent:(QtWidgets.QMainWindow, type(None)) = None, win_title=None, **kwargs):
        # NOTE: 2022-11-05 14:54:24
        # by default, frameIndex is set to all available frames - KISS
        self._toolbars_locked_ = True
        self._clear_detection_flag_ = clearOldPSCs == True
        self._mPSC_detected_ = False
        self._data_var_name_ = None
        self._last_used_file_save_filter_ = None
        self._last_used_file_open_filter_ = None
        self._displayed_detection_channel_ = 0
        
        self._currentTabIndex_ = 0
        
        self._current_detection_θ = list()
        
        self._all_waves_to_result_ = False
        
        self._align_waves_on_rise_ = False
        
        self._plots_all_waves_ = False
        
        # NOTE: 2022-11-20 11:36:08
        # For each segment in data, if there are spike trains with event time
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
        # When detection is performed in a segment, any Event_detection spiketrain 
        # that exists in the segment is copied to the buffer's element 
        # corresponding to that segment, for it to be recalled when an "undo" 
        # operation is triggered
        self._undo_buffer_= list()
        
        # a cache for targets used in identification the events in the current sweep
        self._targets_cache_ = list()
        
        self._use_template_ = False
        self._use_threshold_on_rsq_ = False
        self._rsq_threshold_ = 0.
        # self._accept_waves_cache_ = list() # a set for each segment
        self._overlayTemplateModel = False
        self._template_showing_ = False
        
        self._data_ = None
        self._filtered_data_ = None
        
        self._use_sliding_detection_=True
        
        # self._fs_ = None
        self._filter_type_ = "Butterworth"
        self._filter_function_ = None
        self._filter_signal_ = False
        self._extract_filtered_waves_ = False
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
        
        # the template file where a event template is stored across sessions
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
        # About event template files
        # The logic is as follows:
        # • by default at startup, the event template is read from the custom 
        #   template file, if it is accessible (NOTE: the template file is NOT
        #   actually read at __init__, but only when a detection is initiated,
        #   or when the waveform template is plotted)
        #
        # • else the event template is read from the default template file, if it
        #   is accessible;
        #
        # • else, there is no event template for the session.
        #
        # When the user MAKES a new template, or IMPORTS one from workspace:
        # • the event template will be stored in the default template file (overwriting it)
        #   ONLY IF the user chooses to do so by triggering the action "Set Default event Template"
        #
        # When the user OPENS (READS) an event template from a file in the file system
        # (other that the default template file):
        # • the name of THIS file is stored as the custom template file in the
        #   config
        #
        # • the event template will be stored in the default template file (overwriting it)
        #   ONLY IF the user chooses to do so by triggering the action "Set Default event Template"
        #
        # When the user triggers "Forget event template", then:
        #   ∘ the event template is cleared for the session and the template from
        #       the default template file is loaded (is available)
        #   ∘ the custom event template file name is removed from the config (i.e. is set to "")
        #   ∘ at the next session only the default event template may be available
        #
        # When the user triggers "Remove default event template", then:
        #   ∘ the default event template file is removed
        #   ∘ the event template of the session (if it exists) exists and can be 
        #       used until Forget event template is also triggered
        #
        # When there is no event template loaded in the session, AND Use event template
        # is checked, then the session will proceed as:
        # • load event template from the custom file, if present
        # • else load event template from the default file, if present
        # • else ask user to select a template from the workspace (if there is one)
        #   NOTE: this is a single neo.AnalogSignal named "event template" so it 
        #   would be easy to "fool" the app simply by renaming ANY neo.AnalogSignal
        #   in the workspace
        # • if no template is chosen form workspace (or there is None available)
        #   then user can choose a template file in the file system (not prompted;
        #   the user must take this action independently)
        #   
        #   if no template has been loaded (either because user has cancelled the
        #   dialogs, or whatever was loaded from the file system does NOT appear
        #   to be an event template) then Use event Template is automatically unckeched
        #   
        # When a event detect action is triggered, AND Use event template is checked
        #   proceed as above; if no templata has been loaded, then switch this 
        #   flag off and proceed with a synthetic waveform generated on the fly
        #
        #
        # when the user opens a event template from the file system, the name of 
        # THAT file is stored in the configuration as custom template file
        
        # 
        
        # temporarily holds the file selected in _slot_editPreferences
        # self._cached_template_file_ =  self._default_template_file
        
        # detected event waveform(s) to validate
        # can be a single neo.AnalogSignal, or, usually, a sequence of
        # neo.AnalogSignal objects
        # NOTE: when detection was made in a collection of segments (e.g. a Block)
        # the _detected_events_ will change with each segment !
        self._detected_events_ = list()
        self._aligned_waves_ = list()
        self._all_waves_ = list()
        self._waveform_frames = 0
        self._currentWaveformIndex_ = 0
        
          # 
        # NOTE: 2022-11-11 23:04:37
        # the event template is an average of selected waveforms, that have,
        # typically, been detected using cros-correlation with an event model waveform
        # The last event template used is stored in a file (by default, located 
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
        self._event_template_ = None
        
        # NOTE: 2022-11-11 23:10:42
        # the realization of the event model according to the parameters in the 
        # event Model Groupbox
        # this serves as a cache for detecting events in a collection of segments
        # (and thus to avoid generating a new waveform for every segment)
        # HOWEVER, it is recommended to re-create this waveform from parameters
        # every time a new detection starts (for a segment, when started manually
        # or before the first segment when detection is started for a collection 
        # of segments)
        
        self._event_model_waveform_ = None
        
        self._result_ = None

        # NOTE: 2022-11-10 09:25:48 DO NOT DELETE:
        # these three are set up by the super() initializer
        # self._data_frames_ = 0
        # self._frameIndex_ = range(self._data_frames_)
        # self._number_of_frames_ = len(self._frameIndex_)
        
        # NOTE: 2022-11-05 15:14:11
        # logic from TriggerDetectDialog: if this instance of EventAnalysis
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
        self._event_duration_ = self._default_duration_
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
        
        # self.winTitle = "Detect Events"
        
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
        # will stay hidden until a waveform (either a event model realisation or 
        # a template event) or a sequence of detetected minis becomes available
        self._waveFormViewer_ = sv.SignalViewer(win_title="Event waveform", 
                                                parent=self, configTag="WaveformViewer")
        
        self._waveFormViewer_.sig_closeMe.connect(self._slot_waveFormViewer_closed)
        
        self._detected_Events_Viewer_ = sv.SignalViewer(win_title="Detected Events", 
                                                     parent=self, configTag="mPSCViewer")
        
        self._detected_Events_Viewer_.sig_closeMe.connect(self._slot_detected_mPSCViewer_closed)
        
        self._detected_Events_Viewer_.frameChanged.connect(self._slot_eventsViewer_frame_changed)
        
        # NOTE: 2023-01-20 10:14:38
        # this MUST be def'ed here because of parent (self) needs its super() intialized too
        self._reportWindow_ = TableEditor(win_title = "Detection Result", parent=self)
        self._reportWindow_.setVisible(False)
        
        self._set_data_(ephysdata)

        # NOTE: 2022-11-26 21:41:50
        # using the QRunnable paradigm works, but can't abort'
        # self.threadpool = QtCore.QThreadPool()
        
        # NOTE: 2022-11-26 11:22:38
        # this works, but still needs to be made abortable
        # NOTE: 2023-06-29 21:35:06 API changed
        # ⇒ inappropriate for this case, don't use here.
        # # # # self._detectController_ = pgui.ProgressThreadController(self._detect_all_)
        # # # # self._detectController_.sig_ready.connect(self._slot_detectThread_ready)
        
        # NOTE: 2022-11-26 11:23:21
        # alternative from below:
        # https://realpython.com/python-pyqt-qthread/#using-qthread-to-prevent-freezing-guis
        self._detectThread_ = None
        self._detectWorker_ = None
        self._filterThread_ = None
        self._filterWorker_ = None
        self._alignThread_  = None
        self._alignWorker_  = None
        
        # NOTE: 2022-11-26 21:42:48
        # mutable control data for the detection loop, to communicate with the
        # worker thread
        self.loopControl = {"break":False}
        
        # NOTE: 2022-11-05 23:08:01
        # this is inherited from WorkspaceGuiMixin therefore it needs full
        # initialization of WorkspaceGuiMixin instance
        # self._data_var_name_ = self.getDataSymbolInWorkspace(self._data_)
        
        # self.resize(-1,-1)
        if not isinstance(self._event_template_, (neo.AnalogSignal, DataSignal)):
            self.useTemplateWaveForm = False
            self.use_eventTemplate_CheckBox.setEnabled(False)

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
        self._frames_spinBoxSlider_.range = range(0, self._number_of_frames_)
        self._frames_spinBoxSlider_.valueChanged.connect(self.slot_setFrameNumber) # slot inherited from ScipyenFrameViewer
        
        self._events_spinBoxSlider_.label = "Event:"
        self._events_spinBoxSlider_.setRange(0,0)
        self._events_spinBoxSlider_.valueChanged.connect(self._slot_setWaveFormIndex)
        
        self.durationSpinBox.setDecimals(self.paramsWidget.spinDecimals)
        self.durationSpinBox.setSingleStep(10**(-self.paramsWidget.spinDecimals))
        self.durationSpinBox.units = pq.s
        self.durationSpinBox.setRange(0*pq.s, 0.1*pq.s)
        self.durationSpinBox.setValue(self._event_duration_)
        self.durationSpinBox.valueChanged.connect(self._slot_modelDurationChanged)
        
        self.displayedDetectionChannelSpinBox.valueChanged.connect(self._slot_displayedDetectionChannelChanged)
        
        self.rsqThresholdDoubleSpinBox.setValue(self._rsq_threshold_)
        self.rsqThresholdDoubleSpinBox.valueChanged.connect(self._slot_rsqThresholdChanged)
        
        # actions (shared among menu and toolbars):
        self.actionOpenEphysData.triggered.connect(self._slot_openEphysDataFile)
        
        self.actionImportEphysData.triggered.connect(self._slot_importEphysData)
        
        self.actionSaveEphysData.triggered.connect(self._slot_saveEphysData)
        
        self.actionExportEphysData.triggered.connect(self._slot_exportEphysData)
        
        self.actionPlot_Data.triggered.connect(self._slot_plotData)
        self.actionPlot_detected_events.triggered.connect(self._slot_plot_detected_events_in_sweep_)
        self.actionPlot_all_events.triggered.connect(self._slot_plot_all_events)
        self.actionPlot_all_accepted_events.triggered.connect(self._slot_plot_all_accepted_events)
        self.actionPlot_aligned_event_waveforms.triggered.connect(self._plot_aligned_waves)
        self.actionPlot_aligned_event_waveforms.setEnabled(False)
        self.actionMake_Event_Detection_Epoch.triggered.connect(self._slot_make_mPSCEpoch)
        self.actionOpen_Event_Template.triggered.connect(self._slot_openTemplateFile)
        self.actionCreate_Event_Template.triggered.connect(self._slot_create_event_template)
        self.actionCreate_Event_Template.setEnabled(False)
        self.actionPlot_Event_template.triggered.connect(self._plot_template_)
        self.actionPlot_Event_template.setEnabled(False)
        self.actionPlot_events_for_template.triggered.connect(self._plot_aligned_waves)
        self.actionPlot_events_for_template.setEnabled(False)
        self.actionImport_Event_Template.triggered.connect(self._slot_importTemplate)
        self.actionSave_Event_Template.triggered.connect(self._slot_saveTemplateFile)
        self.actionSave_Event_Template.setEnabled(False)
        self.actionExport_Event_Template.triggered.connect(self._slot_exportTemplate)
        self.actionExport_Event_Template.setEnabled(False)
        self.actionRemember_Event_Template.triggered.connect(self._slot_storeTemplateAsDefault)
        self.actionRemember_Event_Template.setEnabled(False)
        self.actionForget_Event_Template.triggered.connect(self._slot_forgetTemplate)
        self.actionForget_Event_Template.setEnabled(False)
        self.actionDetect_in_current_sweep.triggered.connect(self._slot_detectCurrentSweep)
        self.actionClear_default.triggered.connect(self._slot_clearFactoryDefaultTemplateFile)
        self.actionChoose_persistent_event_template_file.triggered.connect(self._slot_choosePersistentTemplateFile)
        self.actionReset_to_factory.triggered.connect(self._slot_revertToFactoryDefaultTemplateFile)
        self.actionOverlay_Template_with_Model.triggered.connect(self._slot_setOverlayTemplateModel)
        self.actionLoad_default_event_Template.triggered.connect(self._slot_loadDefaultTemplate)
        self.actionLoad_last_used_event_template.triggered.connect(self._slot_loadLastUsedTemplate)
        self.actionUndo_current_sweep.triggered.connect(self._slot_undoCurrentSweep)
        self.actionAlign_event_waveforms.triggered.connect(self._slot_alignThread)
        
        # self.actionDetect.triggered.connect(self._slot_detect)
        self.actionDetect.triggered.connect(self._slot_detectThread)
        
        self.actionClose.triggered.connect(self._slot_Close)
        
        self.actionUndo.triggered.connect(self._slot_undoDetection)
        self.actionView_results.triggered.connect(self.slot_showReportWindow)
        self.actionSave_results.triggered.connect(self._slot_saveResults)
        self.actionExport_results.triggered.connect(self._slot_exportEventsTable)
        self.actionSave_event_trains.triggered.connect(self._slot_saveEventTrains)
        self.actionExport_event_trains.triggered.connect(self._slot_exportEventTrains)
        self.actionSave_event_waveforms.triggered.connect(self._slot_saveEventWaves)
        self.actionExport_event_waveforms.triggered.connect(self._slot_exportEventWaves)
        self.actionExport_aligned_waveforms.triggered.connect(self._slot_exportAlignedWaves)
        self.actionClear_results.triggered.connect(self._slot_clearResults)
        self.actionUse_default_location_for_persistent_event_template.triggered.connect(self._slot_useDefaultTemplateLocation)
        self.actionChoose_persistent_event_template_file.triggered.connect(self._slot_choosePersistentTemplateFile)
        self.actionLock_toolbars.setChecked(self._toolbars_locked_ == True)
        self.actionLock_toolbars.triggered.connect(self._slot_lockToolbars)
        self.actionMain_toolbar.triggered.connect(self._slot_setMainToolbarVisibility)
        self.mainToolBar.visibilityChanged.connect(self._slot_setMainToolbarVisibility)
        self.actionDetection_toolbar.triggered.connect(self._slot_setDetectionToolbarVisibility)
        self.detectionToolBar.visibilityChanged.connect(self._slot_setDetectionToolbarVisibility)
        self.actionTemplate_toolbar.triggered.connect(self._slot_setTemplateToolbarVisibility)
        self.templateToolBar.visibilityChanged.connect(self._slot_setTemplateToolbarVisibility)
        self.actionFilter_toolbar.triggered.connect(self._slot_setFilterToolbarVisibility)
        self.filterToolBar.visibilityChanged.connect(self._slot_setFilterToolbarVisibility)
        self.actionShow_all_toolbars.triggered.connect(self._slot_setToolBarsVisible)
        
        self.actionWaves_alignment_on_rising_phase.triggered.connect(self._slot_set_alignOnRisingPhase)
        # signal & epoch comboboxes
        self.signalNameComboBox.currentTextChanged.connect(self._slot_newTargetSignalSelected)
        self.signalNameComboBox.currentIndexChanged.connect(self._slot_newTargetSignalIndexSelected)
        self.epochComboBox.currentTextChanged.connect(self._slot_epochComboBoxSelectionChanged)
        # self.epochComboBox.currentIndexChanged.connect(self._slot_new_mPSCEpochIndexSelected)
        
        self.use_eventTemplate_CheckBox.setChecked(self._use_template_ == True)
        self.use_eventTemplate_CheckBox.stateChanged.connect(self._slot_use_mPSCTemplate)
        
        self.rsqThresholdCheckBox.setChecked(self._use_threshold_on_rsq_)
        self.rsqThresholdCheckBox.stateChanged.connect(self._slot_useThresholdOnRsquared)
        
        self.clearPreviousDetectionCheckBox.setChecked(self._clear_detection_flag_ == True)
        self.clearPreviousDetectionCheckBox.stateChanged.connect(self._slot_setClearDetectionFlag_)
        
        self.plot_eventWaveformToolButton.clicked.connect(self._slot_plot_mPSCWaveForm)
        self.exportModelWaveToolButton.clicked.connect(self._slot_exportModelWaveformToWorkspace)
        
        if self._toolbars_locked_:
            for toolbar in (self.mainToolBar, self.detectionToolBar):
                toolbar.setFloatable(not self._toolbars_locked_)
                toolbar.setMovable(not self._toolbars_locked_)
                
        self.metaDataWidget.sig_valueChanged.connect(self._slot_metaDataChanged)
        
        self.accept_eventCheckBox.setEnabled(False)
        self.accept_eventCheckBox.stateChanged.connect(self._slot_set_Event_accepted)
        self.makeUnitAmplitudePushButton.clicked.connect(self._slot_makeUnitAmplitudeModel)
        
        self.detectionThresholdSpinBox.setMinimum(0)
        self.detectionThresholdSpinBox.setMaximum(math.inf)
        self.detectionThresholdSpinBox.setMaximum(math.inf)
        self.detectionThresholdSpinBox.setDecimals(4)
        self.detectionThresholdSpinBox.setValue(self._detection_threshold_)
        self.detectionThresholdSpinBox.valueChanged.connect(self._slot_detectionThresholdChanged)
        # self.reFitPushButton.clicked.connect(self._slot_refit_Event_Waveform)
        
        
        self.removeDCCheckBox.stateChanged.connect(self._slot_set_removeDC)
        self.autoOffsetCheckBox.stateChanged.connect(self._slot_setAutoOffset)
        
        self.dcValueSpinBox.setMinimum(-math.inf*pq.pA)
        self.dcValueSpinBox.setMaximum(math.inf*pq.pA)
        self.dcValueSpinBox.setValue(self._dc_offset_)
        self.dcValueSpinBox.setDecimals(4)
        self.dcValueSpinBox.sig_valueChanged.connect(self._slot_DCOffsetChanged)
        
        self.noiseFilterCheckBox.stateChanged.connect(self._slot_set_useLowPassFilter)
        
        self.cutoffFrequencySpinBox.setMinimum(0*pq.Hz)
        self.cutoffFrequencySpinBox.setMaximum(math.inf*pq.Hz)
        self.cutoffFrequencySpinBox.setValue(self._noise_cutoff_frequency_)
        
        self.cutoffFrequencySpinBox.sig_valueChanged.connect(self._slot_cutoffFreqChanged)
        
        self.actionUseFilteredWaves.triggered.connect(self._slot_setUseFilteredWaves)
        
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
        
        self.actionView_detection.setIcon(QtGui.QIcon.fromTheme("tools-report-bug"))
        self.actionView_detection.triggered.connect(self._slot_previewDetectionTheta)
        
        self.actionAll_waves_to_result.triggered.connect(self._slot_set_allWavesToResult)
        
        self.actionRefit_wave.triggered.connect(self._slot_refit_Event_Waveform)
        
        # NOTE: 2023-01-31 08:37:50
        # the two slots below are inherited from WorkspaceGuiMixin
        self.actionSave_detection_prefs.triggered.connect(self.saveOptionsToUserFile)
        self.actionLoad_detection_prefs.triggered.connect(self.loadOptionsFromUserFile)
        
        for c in self.children():
            if isinstance(c, QtWidgets.QAction):
                if len(c.toolTip().strip()) == 0:
                    s = c.toolTip()
                else:
                    s = c.text()
                    c.setToolTip(s)
                    
                if len(c.statusTip().strip()) == 0:
                    c.setStatusTip(s)
                    
                if len(c.whatsThis().strip()) == 0:
                    c.setWhatsThis(s)
                    
        self._events_tally_label_ = QtWidgets.QLabel("Events: ", parent=self)
        self.statusBar().addPermanentWidget(self._events_tally_label_)
                    
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
              self.use_eventTemplate_CheckBox)
        
        sigblock = [QtCore.QSignalBlocker(w) for w in ww]
        
        # 1) assign values from config to paramsWidget
        self.paramsWidget.setParameters(self._params_initl_,
                                        lower = self._params_lower_,
                                        upper = self._params_upper_,
                                        names = self._params_names_,
                                        refresh = True)
        
        
        # 2) assign model duration from config
        self.durationSpinBox.setValue(self._event_duration_)
        
        # 3) set check boxes
        self.use_eventTemplate_CheckBox.setChecked(self._use_template_ == True)
        self.clearPreviousDetectionCheckBox.setChecked(self._clear_detection_flag_ == True)
        # self.actionAll_waves_to_result.setChecked(self._all_waves_to_result_ == True)
        
    def _set_data_(self, *args, **kwargs):
        # called by super() initializer; 
        # UI widgets not yet initialized
        if len(args):
            data = args[0]
        else:
            data = kwargs.pop("data", None)
            
        self._targets_cache_.clear()
        self._detected_events_ = list()
        self._aligned_waves_ = list()
        self._all_waves_ = list()
            
        sigBlock = QtCore.QSignalBlocker(self.displayedDetectionChannelSpinBox)
            
        if neoutils.check_ephys_data_collection(data): # and self._check_supports_parameter_type_(data):
            if isinstance(data, neo.Block):
                self._undo_buffer_ = [None for s in data.segments]
                self._result_ = [None for s in data.segments]
                # self._accept_waves_cache_ = [set() for s in data.segments]
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
                
                channels = [1]
                for k, segment in enumerate(self._data_.segments):
                    self._result_[k] = self._get_previous_detection_(segment)
                    if isinstance(self._result_[k], neo.core.spiketrainlist.SpikeTrainList):
                        channels.append(len(self._result_[k]))
                        
                max_channels = max(channels)
                self.displayedDetectionChannelSpinBox.setMaximum(max_channels)
                self._displayed_detection_channel_ = 0
                self.displayedDetectionChannelSpinBox.setValue(self._displayed_detection_channel_)
                            
            elif isinstance(data, neo.Segment):
                self._undo_buffer_ = [None]
                self._result_ = [None]
                # self._accept_waves_cache_ = [set()]
                
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
                if isinstance(self._result_[0], neo.core.spiketrainlist.SpikeTrainList):
                    self.displayedDetectionChannelSpinBox.setMaximum(len(self._result_[k]))
                    self._displayed_detection_channel_ = 0
                    self.displayedDetectionChannelSpinBox.setValue(self._displayed_detection_channel_)
                
            elif isinstance(data, (tuple, list)) and all(isinstance(v, neo.Segment) for v in data):
                self._undo_buffer_ = [None for s in data]
                self._result_ = [None for s in data]
                # self._accept_waves_cache_ = [set() for s in data]
                            
                if len(data[0].analogsignals):
                    time_units = data[0].analogsignals[0].times.units
                    signal_units = data[0].analogsignals[0].units
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
                
                channels = [1]
                for k,s in enumerate(self._data_):
                    self._result_[k] = self._get_previous_detection_(s)
                    if isinstance(self._result_[k], neo.core.spiketrainlist.SpikeTrainList):
                        channels.append(len(self._result_[k]))
                        
                max_channels = max(channels)
                self.displayedDetectionChannelSpinBox.setMaximum(max_channels)
                self._displayed_detection_channel_ = 0
                self.displayedDetectionChannelSpinBox.setValue(self._displayed_detection_channel_)
                    
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
        
        description = getattr(self._data_, "description", "")
        
        self.metaDataWidget.dataDescription = description
        
        self._frames_spinBoxSlider_.range = range(0, self._number_of_frames_)
        
        self._plot_data()
        
        total_evts, acc_evts = self._tally_events()
        self._report_events_tally(total_evts, acc_evts)
            
    def _generate_eventModelWaveform(self):
        if self.eventDuration is pd.NA or (isinstance(self.eventDuration, pq.Quantity) and self.eventDuration.magnitude <= 0):
            return
        
        segment = self._get_data_segment_()
        
        if isinstance(segment, neo.Segment):
            signal = self._get_selected_signal_(segment)
            if isinstance(signal, neo.AnalogSignal) and signal.size > 1:
                sampling_rate = signal.sampling_rate
            else:
                sampling_rate = self._default_sampling_rate_
        elif isinstance(self._event_template_, neo.AnalogSignal):
            sampling_rate = self._event_template_.sampling_rate
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
            
        self._event_model_waveform_ = membrane.PSCwaveform(init_params, 
                                             duration=self.eventDuration,
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
        if not self._template_showing_:
            try:
                if isinstance(self._detected_Events_Viewer_, sv.SignalViewer):
                    sigBlock = QtCore.QSignalBlocker(self._detected_Events_Viewer_)
                    sigBlockers = [QtCore.QSignalBlocker(w) for w in (self._detected_Events_Viewer_,
                                                                    self._ephysViewer_,
                                                                    self._frames_spinBoxSlider_)]
                    # print(f"displayDetectedWaveform {len(self._detected_Events_Viewer_.yData)} waves")
                    if index in range(-len(self._detected_Events_Viewer_.yData), len(self._detected_Events_Viewer_.yData)):
                        self._detected_Events_Viewer_.currentFrame = index
                        if self._plots_all_waves_:
                            segment_index = self._detected_Events_Viewer_.yData[index].segment.index
                            self._targets_cache_.clear()
                            self._ephysViewer_.currentFrame = segment_index
                            self.currentFrame = segment_index
                            # self._frames_spinBoxSlider_.setValue(segment_index)
                        
                    self._currentWaveformIndex_ = index
                    self._indicate_events_()
            except Exception as e:
                traceback.print_exc()
        
            
    def displayFrame(self):
        """Overloads ScipyenFrameViewer.displayFrame"""
        self._refresh_signalNameComboBox()
        self._refresh_epochComboBox()
        
        if self._ephysViewer_.yData is None:
            if isinstance(self._data_, (neo.Block, neo.Segment)):
                doctitle = self._data_.name
            else:
                doctitle = self.metaDataWidget.dataVarName
            self._ephysViewer_.view(self._data_, doc_title=doctitle)
            
        self._ephysViewer_.currentFrame = self.currentFrame
        
        # NOTE: 2022-11-27 13:49:44
        # DO NOT CALL clear() - it will clear the waves list in result, because 
        # they are a list stored by reference !!!
        # self._detected_events_.clear() 
        # DO THIS INSTEAD:- replace self._detected_events_ with a new empty list
        # self._detected_events_ = list()
        
        if self.currentFrame in range(-len(self._result_), len(self._result_)):
            if self._plots_all_waves_ and len(self._all_waves_):
                waves_in_current_frame = [w for w in self._all_waves_ if self._get_wave_segment_index_(w) == self.currentFrame]
                if len(waves_in_current_frame):
                    w = waves_in_current_frame[0]
                    events_frame = self._all_waves_.index(w)
                    self.eventsViewer.currentFrame = events_frame
                    return
                
            else:
                self._slot_plot_detected_events_in_sweep_()
        
    def clear(self):
        if isinstance(self._ephysViewer_,sv.SignalViewer):
            self._ephysViewer_.clear()
            self._ephysViewer_.close()
            self._ephysViewer_ = None
            
        if isinstance(self._waveFormViewer_,sv.SignalViewer):
            self._waveFormViewer_.clear()
            self._waveFormViewer_.close()
            self._waveFormViewer_ = None
            
        if isinstance(self._detected_Events_Viewer_,sv.SignalViewer):
            self._detected_Events_Viewer_.clear()
            self._detected_Events_Viewer_.close()
            self._detected_Events_Viewer_ = None
            
        self._mPSC_detected_ = False
        self._detection_signal_name_ = None
        
        self._data_ = None
        self._data_var_name_ = None
        self._filtered_data_ = None
        self._data_frames_ = 0
        self._frameIndex_ = []
        self._number_of_frames_ = 0
        
        self._event_model_waveform_ = None
        self._event_template_ = None
        self._template_file_ = self._default_template_file
        
        self._detected_events_ = list()
        self._aligned_waves_ = list()
        self._all_waves_ = list()
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
        self._event_duration_ = self._default_duration_
        self._targets_cache_.clear()
        
    @pyqtSlot()
    def _slot_Close(self):
        self.close()
        
    def closeEvent(self, evt):
        if isinstance(self._ephysViewer_, sv.SignalViewer):
            if self._owns_viewer_:
                self._ephysViewer_.clear()
                self._ephysViewer_.close()
                # self._ephysViewer_ = None
            else:
                self._ephysViewer_.refresh()
                
        if isinstance(self._waveFormViewer_, sv.SignalViewer):
            self._waveFormViewer_.clear()
            self._waveFormViewer_.close()
            
        # self._waveFormViewer_= None
        
        if isinstance(self._detected_Events_Viewer_, sv.SignalViewer):
            self._detected_Events_Viewer_.clear()
            self._detected_Events_Viewer_.close()
            
            
        self._reportWindow_.clear()
        self._reportWindow_.close()
            
        # self._detected_Events_Viewer_= None
        
        # this one is also supposed to call saveSettings()
        super().closeEvent(evt)
        
    def _enable_widgets(self, *widgets, enable:bool=True):
        for w in widgets:
            if isinstance(w, (QtWidgets.QWidget, QtWidgets.QAction)):
                w.setEnabled(enable==True)
                
    @safeWrapper
    def _fit_waves_(self, st:neo.SpikeTrain, **kwargs):#, template:typing.Union[neo.AnalogSignal, DataSignal]):
        """Fits the waveforms in the `st` SpikeTrain to the CB model.
        
        Returns the fitted waveforms.
        """
        
        model_params = self.paramsWidget.value()
        init_params = tuple(p.magnitude for p in model_params["Initial Value:"])
        lo = tuple(p.magnitude for p in model_params["Lower Bound:"])
        up = tuple(p.magnitude for p in model_params["Upper Bound:"])
            
        if self.useTemplateWaveForm and isinstance(self._event_template_, neo.AnalogSignal):
            template_fit = membrane.fit_Event(self._event_template_, init_params, lo, up)
            init_params = template_fit.annotations["event_fit"]["Coefficients"]
                
        minis = neoutils.extract_spike_train_waveforms(st, st.annotations["signal_units"], **kwargs)
        
        fitted_minis = list()
        
        segment = st.segment
        
        for kw, w in enumerate(minis):
            try:
                fw = membrane.fit_Event(w, init_params, lo=lo, up=up)
            except Exception as e:
                traceback.print_exc()
                excstr = traceback.format_exception(e)
                msg = f"Event {kw} in sweep {segment}:\n{excstr[-1]}"
                self.criticalMessage("Fitting event",
                                        "\n".join(excstr))
                return
            
            fitted_minis.append(fw)

        return fitted_minis
    
    def createPopupMenu(self):
        menu = super().createPopupMenu()
        currentActions = menu.actions()
        if len(currentActions):
            menu.insertAction(self.actionLock_toolbars, currentActions[0])
        else:
            menu.inseertAction(self.actionLock_toolbars, None)
            
        return menu
    
    def alignWaves(self, detectionChannel:typing.Optional[int]=None, on_rising:typing.Optional[bool]=None, **kwargs):
        """
        Aligns all detected event waveforms on their onset.
        This requires that the event waveforms have been fitted already.
        
        detectionChannel: int or None; the index of the signal channel
        
        on_rising: bool, optional, default is None
            This flag determines if the alignment id done on the time point of 
            the fastes rising phase of the waves (when True) or on their onset
            (when False)
        
            When None (the default) the value of the flag will be taken from
            the checked status of "Waves alignment on rising phase" option in 
            the settings menu.
        
        WARNING: Overwrites the spike train waveforms and modifies the spike
        train event metadata. There is NO undo.
        """
        if self._data_ is None:
            return
        
        if all(v is None for v in self._result_):
            return
        
        if not isinstance(on_rising, bool):
            on_rising = self.alignWavesOnRisingPhase
        
        loopControl = kwargs.pop("loopControl", None)
        progressSignal = kwargs.pop("progressSignal", None)
        finishedSignal = kwargs.pop("finishedSignal", None)
        resultSignal = kwargs.pop("resultSignal", None)
        threaded = kwargs.pop("threaded", False)
        trains = kwargs.pop("trains", None)
        
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
        # • calculate stop time: start time + event duration (from model parameters)
        #
        # • use the new start time and the calculated stop time to get time 
        #   slices from each signal ⇒ store them in the list of aligned waves
        #
        # • display the waves in the event waveform viewer
        #
        # • display their average in the event model viewer
        #
        # 
        
        if trains is None:
            result = self.result()
            
            if result is None:
                return
            
            table, trains, waves = result
        
        aligned_waves = list()
        
        if not threaded:
            self._enable_widgets(self.actionCreate_Event_Template,
                                self.actionPlot_events_for_template,
                                self.actionPlot_aligned_event_waveforms,
                                self.actionDetect,
                                self.actionUndo,
                                self.actionDetect_in_current_sweep,
                                self.actionUndo_current_sweep,
                                self.actionClear_results,
                                self.accept_eventCheckBox,
                                self.actionView_results,
                                self.actionExport_results,
                                self.actionSave_results,
                                self.use_eventTemplate_CheckBox,
                                self.actionCreate_Event_Template,
                                self.actionOpen_Event_Template,
                                self.actionImport_Event_Template,
                                enable=False)
        
        for k,train in enumerate(trains):
            alignment = self._make_aligned_waves_(train, by_max_rise = on_rising)
            if alignment is None:
                continue

            aligned_waveforms, wave_ndx = alignment
            aligned_waves.extend(aligned_waveforms)
            
            if isinstance(progressSignal, QtCore.pyqtBoundSignal):
                progressSignal.emit(k)
                
            if isinstance(loopControl, dict) and loopControl.get("break",  None) == True:
                break
            
        if len(aligned_waves):    
            self._aligned_waves_[:] = aligned_waves
            if not threaded:
                self._enable_widgets(self.actionCreate_Event_Template,
                                    self.actionPlot_events_for_template,
                                    self.actionPlot_aligned_event_waveforms,
                                    self.actionDetect,
                                    self.actionUndo,
                                    self.actionDetect_in_current_sweep,
                                    self.actionUndo_current_sweep,
                                    self.actionClear_results,
                                    self.accept_eventCheckBox,
                                    self.actionView_results,
                                    self.actionExport_results,
                                    self.actionSave_results,
                                    self.use_eventTemplate_CheckBox,
                                    self.actionCreate_Event_Template,
                                    self.actionOpen_Event_Template,
                                    self.actionImport_Event_Template,
                                    enable=True)
        
                self._plot_aligned_waves()
                
        else:
            self._aligned_waves_.clear()
            if not threaded:
                self._enable_widgets(self.actionCreate_Event_Template,
                                    self.actionPlot_events_for_template,
                                    self.actionPlot_aligned_event_waveforms,
                                    self.actionDetect,
                                    self.actionUndo,
                                    self.actionDetect_in_current_sweep,
                                    self.actionUndo_current_sweep,
                                    self.actionClear_results,
                                    self.accept_eventCheckBox,
                                    self.actionView_results,
                                    self.actionExport_results,
                                    self.actionSave_results,
                                    self.use_eventTemplate_CheckBox,
                                    self.actionCreate_Event_Template,
                                    self.actionOpen_Event_Template,
                                    self.actionImport_Event_Template,
                                    enable=True)
        
                if isinstance(self._detected_Events_Viewer_, sv.SignalViewer):
                    self._detected_Events_Viewer_.clear()
            
            
    def _extract_waves_(self, train, valid_only=False):
        """Extracts event waveforms from the train.
        Calls neoutils.extract_spike_train_waveforms then annotates the waveforms with information
        useful for event tagging in the plotted signal.
        """
        waves = neoutils.extract_spike_train_waveforms(train, train.annotations["signal_units"],
                                       prefix=train.annotations["signal_origin"])
        
        if valid_only:
            waves = [w for w in filter(lambda x: x.annotations.get("Accept", True)==True, waves)]
        
        for wave in waves:
            kw = wave.annotations["wave_index"]
            try:
                wave.annotate(channel_id = train.annotations["channel_id"],
                            amplitude = train.annotations["amplitude"][kw],
                            peak_time = train.annotations["peak_time"][kw],
                            event_fit = train.annotations["event_fit"][kw],
                            Accept = train.annotations["Accept"][kw],
                            signal_origin = train.annotations["signal_origin"],
                            Aligned = train.annotations["Aligned"],
                            using_template = train.annotations.get("using_template", False))
            except Exception as e:
                traceback.print_exc()
                excstr = traceback.format_exception(e)
                msg = f"Event {kw} in sweep {segment}:\n{excstr[-1]}"
                self.criticalMessage("Extract waves",
                                        "\n".join(excstr))
                return
                
        return waves

    def _make_aligned_waves_(self, train:neo.SpikeTrain, by_max_rise:bool=False):
        """
        Aligns detected event waveforms on the onset. 
        
        Only the accepted waveforms are used.
        
        Useful in order to create a event template waveform from their average,
        and for later analyses of the accepted waveforms(e.g. non-stationary
        fluctuation analysis. NOTE: For the latter, the waves should be extracted
        from a signal that has not been low-pass or band-pass filtered.
        
        Parameters:
        ===========
        train: the train with event waveforms
        
        Returns:
        ========
        A sequence of alignes waveforms (as neo.AnalogSignal objects) and a
        sequece of their indices in the original waveforms collection.
        
        Returns None when inappropriate data is passed to the call.
        
        """
        if self._data_ is None:
            return
        
        if all(v is None for v in self._result_):
            return
        
        segment = train.segment
        
        if train.waveforms is None:
            warnings.warn("No waveforms found in the spike train", category=RuntimeWarning)
            self.errorMessage(self.windowTitle(), "No waveforms found in the spike train")
            return
        
        accepted = train.annotations.get("Accept", None)
        # print(f"_make_aligned_waves_ accepted {accepted}")
        
        if accepted is None:
            warnings.warn("No accept flags were found in the spike train", category=RuntimeWarning)
            self.errorMessage(self.windowTitle(), "No accept flags were found in the spike train")
            return
        
        peak_times = train.annotations.get("peak_time", None)
        
        # print(f"_make_aligned_waves_ peak_times {peak_times}")
        
        if peak_times is None:
            return
        
        event_fit = train.annotations.get("event_fit", None)
        
        if event_fit is None:
            warnings.warn("The events waveforms do not appear to have been fitted", category=RuntimeWarning)
            self.errorMessage(self.windowTitle(), "The events waveforms do not appear to have been fitted")
            return
            
        signal_origin = train.annotations.get("signal_origin", None)
        
        # print(f"_make_aligned_waves_ signal_origin {signal_origin}")
        
        if signal_origin is None:
            warnings.warn("No signal origin found in the spike train", category=RuntimeWarning)
            self.errorMessage(self.windowTitle(), "No signal origin found in the spike train")
            return
        
        sig_ndx = neoutils.get_index_of_named_signal(segment, signal_origin, silent=True)
        
        # print(f"_make_aligned_waves_ sig_ndx {sig_ndx}")
        
        if isinstance(sig_ndx, (tuple, list)):
            if len(sig_ndx) == 0 or all(v is None for v in sig_ndx):
                warnings.warn(f"No signal named {signal_origin} is found in data", category=RuntimeWarning)
                self.errorMessage(self.windowTitle(), f"No signal named {signal_origin} is found in data")
                return
        
            sig_ndx = sig_ndx[0]
            
        elif not isinstance(sig_ndx, int):
            warnings.warn(f"No signal named {signal_origin} is found in data", category=RuntimeWarning)
            self.errorMessage(self.windowTitle(), f"No signal named {signal_origin} is found in data")
            return
        
        signal = segment.analogsignals[sig_ndx]
        
        processed = signal.annotations.get("filtered", False)
        
        if self.useFilteredWaves:
            if not processed:
                signal = self._process_signal_(signal, newFilter=True)
                
        else:
            signal = self._process_signal_(signal, dc_detrend_only=True)

        # get the original waveforms for their metadata
        waves = self._extract_waves_(train, valid_only = not self.allWavesToResult)
        
        if len(waves) == 0:
            return
        
        start_times = np.array([w.t_start for w in waves]) * waves[0].t_start.units
        peak_times = np.array([w.annotations["peak_time"] for w in waves]) * waves[0].t_start.units
        
        # save these for annotating the aligned waveforms - useful to indicate
        # where the peak is relative to the start of the aligned waveforms
        relative_peak_times = peak_times - start_times
        
        onset = np.array([w.annotations["event_fit"]["Coefficients"][2] for w in waves]) * waves[0].t_start.units
        
        wave_index = [w.annotations["wave_index"] for w in waves]
        segment_index = [w.segment.index for w in waves]
        
        aligned_waves = list()
        
        if by_max_rise:
            # print(f"_make_aligned_waves_ align on rising phase")
            # extract the time point of fastest rise time (max rise) in the wave;
            # in order to do that we need to smooth the wave first !
            # also, if the wave if "inward", then we take the argmin() !
            # fdata = [self._lowpass_filter_signal(self._deHum(w[:,0], float(w.sampling_rate)), makeFilter=True) for w in waves]
            
            # retrieve the fitted curve to figure out the max rise 
            fdata = [w[:,1] for w in waves] # requires fitted waves !!!
            # get the 1st order difference of the fitted curve: δy/δt
            fdiff = [sigp.ediff1d(w) for w in fdata] 
            ispos = [sigp.is_positive_waveform(w) for w in fdata]
            # The fastest rise is the maximum of δy/δt for positive waveforms -
            # i.e., outward PSCs - or the minimum of δy/δt, otherwise
            # Here we collect the sample indices correspondng to where the fastest
            # rise is (see above for definition of fastest rise)
            maxrise_samples = [w.argmax() if ispos[k] else w.argmin() for k, w in enumerate(fdiff)]
            # Times of fastest rise, relative to t_start, across all the waves:
            # the time values are the values of the time domain at the fastest 
            # rise samples determined above (`maxrise_samples`).
            maxrise_times = np.array([waves[k].times[t]-waves[k].t_start for k, t in enumerate(maxrise_samples)]) * waves[0].t_start.units
            # corrections ↦ array of differences between the maximum time value 
            # of the fastest rise across all waves and the time of the fastest 
            # tise in individual waveforms
            corrections = maxrise_times.max() - maxrise_times
            
            # calculate new start times for the waveforms:
            new_start_times = start_times - corrections
            
            stop_times = new_start_times + self._event_duration_
            
            for kw, wave_ndx in enumerate(wave_index):
                t0 = new_start_times[kw]
                t1 = stop_times[kw]
                # print(f"t0 = {t0} t1 = {t1}")
                aligned_wave = signal.time_slice(t0, t1)
                
                t_onset = t0 + onset[kw]
                
                baseline = signal.time_slice(t0, t_onset)
                dc = np.mean(baseline, axis=0)
                aligned_wave -= dc
                
                aligned_wave = neoutils.set_relative_time_start(aligned_wave)
                
                # no need to annotate the original start time: these ARE the train's
                # times attribute
                aligned_wave.annotate(channel_id = train.annotations["channel_id"],
                            amplitude = train.annotations["amplitude"][kw],
                            peak_time = train.annotations["peak_time"][kw], # keep the original peak time
                            event_fit = train.annotations["event_fit"][kw],
                            relative_peak_time = relative_peak_times[kw],
                            signal_origin = train.annotations["signal_origin"],
                            Accept = train.annotations["Accept"][kw],
                            Aligned = np.array([True]),
                            Alignment = "max rise",
                            wave_index = wave_ndx)
                
                aligned_waves.append(aligned_wave)
                
        else:
            # print(f"_make_aligned_waves_ align on onset")
            maxOnset = onset.max()
            onsetCorrections = maxOnset - onset
            new_start_times = start_times - onsetCorrections
            
            stop_times = new_start_times + self._event_duration_
        
            for kw, wave_ndx in enumerate(wave_index):
                t0 = new_start_times[kw]
                t1 = stop_times[kw]
                aligned_wave = signal.time_slice(t0, t1)
                t_onset = t0 + maxOnset
                baseline = signal.time_slice(t0, t_onset)
                dc = np.mean(baseline, axis=0)
                aligned_wave -= dc
                
                aligned_wave = neoutils.set_relative_time_start(aligned_wave)
                
                # no need to annotate the original start time: these ARE the train's
                # times attribute
                aligned_wave.annotate(channel_id = train.annotations["channel_id"],
                            amplitude = train.annotations["amplitude"][kw],
                            peak_time = train.annotations["peak_time"][kw], # keep the original peak time
                            event_fit = train.annotations["event_fit"][kw],
                            relative_peak_time = relative_peak_times[kw],
                            signal_origin = train.annotations["signal_origin"],
                            Accept = train.annotations["Accept"][kw],
                            Aligned = np.array([True]),
                            Alignment = "onset",
                            wave_index = wave_ndx)
                
                # if write_back:
                #     train.waveforms[wave_ndx,:,:] = aligned_wave.magnitude.T
    
                aligned_waves.append(aligned_wave)
            
        # if write_back:
        #     train.annotations["Aligned"] = True
            
        return aligned_waves, wave_index

    def _combine_model_and_template_(self):
        modelwave = self._get_event_template_or_waveform_(use_template=False)
        maxLen = max(modelwave.shape[0], self._event_template_.shape[0])
        maxChannels = modelwave.shape[1] + self._event_template_.shape[1]
        
        combinedWaves = np.full((maxLen, maxChannels), fill_value = np.nan)
        
        # print(combinedWaves.shape)
        
        combinedWaves[0:self._event_template_.shape[0],0:self._event_template_.shape[1]] = self._event_template_.magnitude
        combinedWaves[0:modelwave.shape[0],-1] = modelwave[:,0].flatten().magnitude
        
        merged = neo.AnalogSignal(combinedWaves, 
                                units = self._event_template_.units, 
                                t_start = 0*pq.s,
                                sampling_rate = self._event_template_.sampling_rate,
                                name = self._event_template_.name,
                                description = self._event_template_.description)
        merged.annotations.update(self._event_template_.annotations)
        # print(merged.shape)
        
        return merged
            
    def _plot_model_(self):
        """Plots event model waveform"""
        if not isinstance(self._waveFormViewer_, sv.SignalViewer):
            self._waveFormViewer_ = sv.SignalViewer(win_title="Event Waveform", 
                                                    parent=self, configTag="WaveformViewer")
            self._waveFormViewer_.sig_closeMe.connect(self._slot_waveFormViewer_closed)
            
        if len(self._waveFormViewer_.axes):
            self._waveFormViewer_.removeLabels(0)
        
        if self._overlayTemplateModel and self.useTemplateWaveForm and isinstance(self._event_template_, (neo.AnalogSignal, DataSignal)):
            merged = self._combine_model_and_template_()
            
            self._waveFormViewer_.view(merged, doc_title=merged.name)
            
        else:
            waveform = self._get_event_template_or_waveform_()
            
            if isinstance(waveform, (neo.AnalogSignal, DataSignal)):
                self._waveFormViewer_.view(waveform, doc_title=waveform.name)
            
    def _plot_template_(self):
        """Plots event template"""
        if not isinstance(self._waveFormViewer_, sv.SignalViewer):
            self._waveFormViewer_ = sv.SignalViewer(win_title="Event Waveform", 
                                                    parent=self, configTag="WaveformViewer")
        
            self._waveFormViewer_.sig_closeMe.connect(self._slot_waveFormViewer_closed)

        if len(self._waveFormViewer_.axes):
            self._waveFormViewer_.removeLabels(0)
        
        if isinstance(self._event_template_, (neo.AnalogSignal, DataSignal)):
            if self.overlayTemplateModel:
                merged = self._combine_model_and_template_()
                self._waveFormViewer_.view(merged, doc_title=merged.name)
            else:
                self._waveFormViewer_.view(self._event_template_, doc_title=self._event_template_.name)
                
            
            event_fit = self._event_template_.annotations.get("event_fit", None)
            
            waxis = self._waveFormViewer_.axis(0)
            
            if isinstance(event_fit, dict):
                waveR2 = event_fit.get("Rsq", None)
                if waveR2 is not None:
                    wavelabel = "R² = %.2f" % waveR2
                    
                [[x0,x1], [y0,y1]]  = waxis.viewRange()
                
                self._waveFormViewer_.addLabel(wavelabel, 0, pos = (x0,y1), 
                                               color=(0,0,0), anchor=(0,1))
                
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
            else:
                # NOTE: 2022-12-15 13:39:32
                # see NOTE: 2022-12-15 13:37:54
                receivers = self._ephysViewer_.receivers(self._ephysViewer_.sig_axisActivated)
                if receivers == 0:
                    self._ephysViewer_.sig_axisActivated.connect(self._slot_newSignalViewerAxisSelected)
                    
                # NOTE: 2022-12-15 13:41:33
                # see NOTE: 2022-12-15 13:38:13
                if self._ephysViewer_ not in self.linkedViewers:
                    self.linkToViewers(self._ephysViewer_)

            for ax in self._ephysViewer_.axes:
                self._ephysViewer_.removeTargetsOverlay(ax)
                
            self.displayFrame()
                
    @pyqtSlot()
    def _slot_previewDetectionTheta(self):
        if self._data_ is None:
            return
        if len(self._current_detection_θ) == 0:
            return
        
        segment = self._get_data_segment_(self.currentFrame)
        signal = self._get_selected_signal_(segment)
        
        epochs = [e for e in segment.epochs if e.name in self._detection_epochs_]
        if len(epochs):
            esigs = list()
            for epoch in epochs:
                esig = neoutils.get_time_slice(signal, epoch)
                # esig = neoutils.get_time_slice(signal, epochs[0])
                esig.segment = segment
                esig.description = ""
                esigs.append(esig)
                
            if len(esigs) == 1:
                sig = esigs[0]
                
            else:
                sig = esigs[0].concatenate(esigs[1:])
                
                
        else:
            sig = signal
            
        # if self.useFilteredWaves:
        if not signal.annotations.get("filtered", False):
            sig = self._process_signal_(sig, newFilter=True)
        
        segment = neo.Segment()
        segment.analogsignals.append(sig)
        segment.analogsignals.extend(self._current_detection_θ)
        
        if not isinstance(self._ephysViewer_, sv.SignalViewer):
            self._init_ephysViewer_()
        
        # NOTE: 2022-12-15 13:37:54
        # prevent messing up signal selection combo box
        receivers = self._ephysViewer_.receivers(self._ephysViewer_.sig_axisActivated)
        if receivers > 0:
            self._ephysViewer_.sig_axisActivated.disconnect()
        # NOTE: 2022-12-15 13:38:13
        # prevent messing up self.currentFrame
        self.unlinkViewer(self._ephysViewer_)
        
        self._ephysViewer_.plot(segment)
        
    @pyqtSlot()
    def _slot_previewFilteredSignal(self):
        if self._data_ is None:
            return
        segment = self._get_data_segment_(self.currentFrame)
        signal = self._get_selected_signal_(segment)
        
        epochs = [e for e in segment.epochs if e.name in self._detection_epochs_]
        if len(epochs):
            esigs = list()
            for epoch in epochs:
                esig = neoutils.get_time_slice(signal, epoch)
                # esig = neoutils.get_time_slice(signal, epochs[0])
                esig.segment = segment
                esig.description = ""
                esigs.append(esig)
            if len(esigs) == 1:
                sig = esigs[0]
                
            else:
                sig = esigs[0].concatenate(esigs[1:])
                
                
        else:
            sig = signal
            
            
        if signal.annotations.get("filtered", False):
            testsig = signal
        else:
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
            
        # NOTE: 2022-12-15 13:38:53
        # see NOTE: 2022-12-15 13:37:54 and NOTE: 2022-12-15 13:38:13
        receivers = self._ephysViewer_.receivers(self._ephysViewer_.sig_axisActivated)
        if receivers > 0:
            self._ephysViewer_.sig_axisActivated.disconnect()
        self.unlinkViewer(self._ephysViewer_)
        self._ephysViewer_.plot(testsig)
        
            
    def _plot_aligned_waves(self):
        if len(self._aligned_waves_) == 0:
            return
        self.accept_eventCheckBox.setEnabled(False)
        self._template_showing_ = True
        
        if not isinstance(self._detected_Events_Viewer_, sv.SignalViewer):
            self._detected_Events_Viewer_ = sv.SignalViewer(win_title="Detected events", 
                                                        parent=self, configTag="mPSCViewer")

            self._detected_Events_Viewer_.sig_closeMe.connect(self._slot_detected_mPSCViewer_closed)

            self._detected_Events_Viewer_.frameChanged.connect(self._slot_eventsViewer_frame_changed)
            
        if len(self._detected_Events_Viewer_.axes):
            self._detected_Events_Viewer_.removeLabels(0)
            
        QtCore.QTimer.singleShot(100, self._view_aligned_events_)
        
    def _view_aligned_events_(self):
        self._events_spinBoxSlider_.range = range(0, len(self._aligned_waves_))
        self._detected_Events_Viewer_.view(self._aligned_waves_, 
                                           doc_title="Aligned events",
                                           frameAxis=1)
        
    def _get_wave_segment_index_(self, wave):
        seg = getattr(wave, "segment", None)
        if isinstance(seg, neo.Segment):
            index = getattr(seg, "index", "None")
            return index
        
    def _slot_plot_all_events(self):
        if not isinstance(self._ephysViewer_, sv.SignalViewer):
            return
        
        if not isinstance(self._detected_Events_Viewer_, sv.SignalViewer):
            self._detected_Events_Viewer_ = sv.SignalViewer(win_title="Detected events", 
                                                        parent=self, configTag="mPSCViewer")

            self._detected_Events_Viewer_.sig_closeMe.connect(self._slot_detected_mPSCViewer_closed)

            self._detected_Events_Viewer_.frameChanged.connect(self._slot_eventsViewer_frame_changed)
        
        result = self.result(self.allWavesToResult)
        
        self._targets_cache_.clear()
        
        if result is not None:
            self._plots_all_waves_ = True
            table, trains, waves = result
            if len(waves) == 0:
                return
            self._all_waves_ = waves
            QtCore.QTimer.singleShot(100, self._view_all_events_)
            
    def _slot_plot_all_accepted_events(self):
        if not isinstance(self._ephysViewer_, sv.SignalViewer):
            return
        
        if not isinstance(self._detected_Events_Viewer_, sv.SignalViewer):
            self._detected_Events_Viewer_ = sv.SignalViewer(win_title="Detected events", 
                                                        parent=self, configTag="mPSCViewer")

            self._detected_Events_Viewer_.sig_closeMe.connect(self._slot_detected_mPSCViewer_closed)

            self._detected_Events_Viewer_.frameChanged.connect(self._slot_eventsViewer_frame_changed)
        
        result = self.result(False)
        
        self._targets_cache_.clear()
        
        if result is not None:
            self._plots_all_waves_ = True
            table, trains, waves = result
            if len(waves) == 0:
                return
            self._all_waves_ = waves
            
            QtCore.QTimer.singleShot(100, self._view_all_events_)
            
    def _view_all_events_(self):
        waves_in_current_frame = [w for w in self._all_waves_ if w.segment.index == self.currentFrame]
        waveIndex = self._all_waves_.index(waves_in_current_frame[0]) if len(waves_in_current_frame) else 0
        self._events_spinBoxSlider_.range = range(0, len(self._all_waves_))
        if len(self._detected_Events_Viewer_.axes):
            self._detected_Events_Viewer_.removeLabels(0)
            
        
        sigBlock = QtCore.QSignalBlocker(self._detected_Events_Viewer_)
        self._detected_Events_Viewer_.view(self._all_waves_, 
                                            doc_title="All events", 
                                            frameAxis=1)
        
        self._detected_Events_Viewer_.currentFrame = waveIndex
        self._events_spinBoxSlider_.setValue(waveIndex)
        
        self._indicate_events_(waves=self._all_waves_)
            
    def _slot_plot_detected_events_in_sweep_(self):
        if not isinstance(self._ephysViewer_, sv.SignalViewer):
            return
        
        frameResult = self._result_[self.currentFrame] # a spike train list or None !!!
        
        if not isinstance(frameResult, neo.core.spiketrainlist.SpikeTrainList) or len(frameResult) == 0:
            if isinstance(self._detected_Events_Viewer_, sv.SignalViewer):
                self._detected_Events_Viewer_.clearAxes()
                
            
            return
        
        signalBlockers = (QtCore.QSignalBlocker(w) for w in (self._events_spinBoxSlider_,
                                                             self.accept_eventCheckBox,
                                                             self.displayedDetectionChannelSpinBox,
                                                             self._ephysViewer_))
        self._template_showing_ = False
        self._targets_cache_.clear()
        
        self._plots_all_waves_ = False
        
        if isinstance(frameResult, neo.core.spiketrainlist.SpikeTrainList):
            nChannels = len(frameResult) # how many spike trains in there (one per channel)
            
            self.displayedDetectionChannelSpinBox.setMaximum(nChannels)
            self._displayed_detection_channel_ = self.displayedDetectionChannelSpinBox.value()
            
            if self._displayed_detection_channel_ >= len(frameResult):
                self._displayed_detection_channel_ = len(frameResult)-1
                
            elif self._displayed_detection_channel_ < 0:
                self._displayed_detection_channel_ = 0
                
            self.displayedDetectionChannelSpinBox.setValue(self._displayed_detection_channel_)
            
            train = frameResult[self._displayed_detection_channel_]
            
            if train.annotations.get("source", None) != "Event_detection":
                return
            
            sig_name = train.annotations.get("signal_origin", None)
            
            if not isinstance(sig_name, str) or len(sig_name.strip()) == 0:
                sig_name = train.name
            
            # print(f"*** {self.__class__.__name__}._slot_plot_detected_events_in_sweep_ extract waves ***")
            self._detected_events_ = self._extract_waves_(train)
            
            if len(self._detected_events_) == 0:
                return
            
            if not isinstance(self._detected_Events_Viewer_, sv.SignalViewer):
                self._detected_Events_Viewer_ = sv.SignalViewer(win_title="Detected events", 
                                                                parent=self, configTag="mPSCViewer")

                self._detected_Events_Viewer_.sig_closeMe.connect(self._slot_detected_mPSCViewer_closed)

                self._detected_Events_Viewer_.frameChanged.connect(self._slot_eventsViewer_frame_changed)
                
            sigBlock = QtCore.QSignalBlocker(self._detected_Events_Viewer_)
            
            self._events_spinBoxSlider_.range = range(0, len(self._detected_events_))
            
            self.accept_eventCheckBox.setEnabled(True)
            
            if len(self._detected_Events_Viewer_.axes):
                self._detected_Events_Viewer_.removeLabels(0)

            QtCore.QTimer.singleShot(100, self._view_frame_events)
            
        else:
            if isinstance(self._detected_Events_Viewer_, sv.SignalViewer):
                self._events_spinBoxSlider_.setRange(0, 0)
                self.accept_eventCheckBox.setEnabled(False)
                self._detected_Events_Viewer_.clear()
                
            if isinstance(self._ephysViewer_, sv.SignalViewer):
                self._ephysViewer_.removeTargetsOverlay(self._ephysViewer_.axes[self._signal_index_])
                
            self._detected_events_.clear()
            
    def _view_frame_events(self):
        self._detected_Events_Viewer_.view(self._detected_events_, 
                                            doc_title = f"Events in sweep {self.currentFrame}",
                                            frameAxis=1)
        self._indicate_events_()
            
    def _indicate_events_(self, waves=None):
        """Indicates detcted events inside the signal plot.
        """
        #### BEGIN debug call stack
        # print(f"_indicate_events_ call stack:")
        # stack = inspect.stack()
        # for s in stack:
        #     print(f"\t\tcaller {s.function} from {s.filename} at {s.lineno}")
        #### END debug call stack
        
        if not isinstance(self._detected_Events_Viewer_, sv.SignalViewer):
            return
        
        if not isinstance(self._ephysViewer_, sv.SignalViewer):
            return
        
        if not self._detected_Events_Viewer_.isVisible():
            self._detected_Events_Viewer_.setVisible(True)
        
        if not self._ephysViewer_.isVisible():
            self._ephysViewer_.setVisible(True)
            
        if self._detected_Events_Viewer_.yData is None:
            return
            
        sigBlockers = [QtCore.QSignalBlocker(w) for w in (self._ephysViewer_,
                                                          self._frames_spinBoxSlider_)]
        
        if waves is None:
            waves = self._detected_Events_Viewer_.yData
            
        if len(waves) == 0:
            raise ValueError("No waves!")
        
        waveindex = self._detected_Events_Viewer_.currentFrame
        
        current_wave = waves[waveindex]
        
        segment = current_wave.segment
        
        if not isinstance(segment, neo.Segment):
            raise ValueError(f"No segment for wave {waveindex}")
        
        frame_index = current_wave.segment.index
        
        sig_name = current_wave.annotations.get("signal_origin", None)
        # print(f"_indicate_events_ sig_name {sig_name}")
        if sig_name is None:
            return
        
        sig_channel = current_wave.annotations.get("channel_id", None)
        # print(f"_indicate_events_ sig_channel {sig_channel}")
        if sig_channel is None:
            return
        
        sig_index = neoutils.get_index_of_named_signal(current_wave.segment, sig_name, silent=True)
        # print(f"_indicate_events_ sig_index {sig_index}")
        if sig_index is None:
            return
        
        #### BEGIN decorate the event plot in the event viewer - add a text showing
        # whether the displayed wave is accepted, and its goodness of fit (R²)
        peak_time = current_wave.annotations["peak_time"]
        accepted = current_wave.annotations["Accept"]
        if isinstance(accepted, np.ndarray):
            accepted = accepted[0]
        
        frame_wave_index = current_wave.annotations["wave_index"]
        
        event_fit = current_wave.annotations["event_fit"]
        
        waveR2 = event_fit.get("Rsq", None)

        acctext = "Accept" if accepted else "Reject"
        
        accolor = (128,0,0) if accepted else (0,0,128)
        
        wavelabel = acctext
        
        if waveR2 is not None:
            wavelabel = "%s R² = %.2f" % (acctext, waveR2)
            
        waxis = self._detected_Events_Viewer_.axis(0) # the axis in the event viewer (always 0)
        
        self._detected_Events_Viewer_.removeLabels(waxis)
        
        [[x0,x1], [y0,y1]]  = waxis.viewRange()
        
        x_range = self._detected_Events_Viewer_._get_axis_data_X_range_(waxis)
        y_range = self._detected_Events_Viewer_._get_axis_data_Y_range_(waxis)
        
        labelpos = QtCore.QPointF(x0, y0)
        
        # NOTE: 2023-05-16 14:40:33
        # anchor (0,0) is upper-left
        # anchor (0,1) is lower-left
        # anchor (1,0) is upper-right
        # anchor (1,1) is lower-right
        anchor = (0,1)
        # anchor = (-1,1)
        self._detected_Events_Viewer_.addLabel(wavelabel, waxis, pos = labelpos, 
                                            color=accolor, anchor=anchor)
        
        #### END decorate the event plot in the event viewer
                
        #### BEGIN decorate the signal plot in ephys viewer - targets indicate
        # the detected events and whether they are accepted or not
        
        targetSize = 15 # TODO: 2022-11-27 13:44:45 make confuse configurable
        
        # target brush and label color for accepted waves
        acc_targetBrush = (255,0,0,50)
        acc_targetLabelColor = (128,0,0,255)
        
        # target brush and label color for rejected waves
        rej_targetBrush = (0,0,255,50)
        rej_targetLabelColor = (0,0,128,255)
                
        # NOTE: 2022-11-23 21:47:29
        # below, the offset of the label to its target is given as (x,y) with
        # x positive left → right
        # y positive bottom → top (like the axis)
        #
        # for upward waveforms, the target should go under the signal trace
        if isinstance(self._event_model_waveform_, neo.core.basesignal.BaseSignal):
            upward = sigp.is_positive_waveform(self._event_model_waveform_)
            
        elif isinstance(self._event_template_, neo.core.basesignal.BaseSignal):
            upward = sigp.is_positive_waveform(self._event_template_)
            
        else:
            upward = False
        
        # TODO: make confuse configurable
        targetLabelOffset = (0, -20) if upward else (0, 20)
        
        accepted_times = list()
        accepted_signal_values = list()
        rejected_times = list()
        rejected_signal_values = list()
        
        targets = list()
        
        # limit iteration to the waves in the current sweep - create targets only
        # for the current sweep !
        # current_frame_waves = [w for w in waves if w.segment.index == self._ephysViewer_.currentFrame]
        current_frame_waves = [w for w in filter(lambda x: x.segment.index == self._ephysViewer_.currentFrame, waves)]
        # print(f"_indicate_events_: {len(current_frame_waves)} waves in sweep {frame_index}")
        # NOTE: 2022-12-15 13:14:39
        # prevent plotting detection targets in the wrong axis
        signal = segment.analogsignals[sig_index]
        
        # get the axis where the signal is plotted
        axis = self._ephysViewer_.axes[sig_index]
        
        # clean the slate
        self._ephysViewer_.removeTargetsOverlay(axis)
        
        #### BEGIN prepare indicators for all waves in the current sweep
        # try to see if there are any targets in the cache so that we don't 
        # build again
        # the cache is emptied when displaying a wave had caused the ephys viewer
        # to jump frame.
        # print(f"_indicate_events_: _targets_cache_ has {len(self._targets_cache_)} targets")
        if len(self._targets_cache_) == 0:
            # no targets in cache ⇒ generate target items and store in cache
            for kw, w in enumerate(current_frame_waves):
                t = w.t_start
                # peak time
                pt = w.annotations["peak_time"]
                # get values in the original signal
                v = neoutils.get_sample_at_domain_value(signal, t) # value at t_start
                pv = neoutils.get_sample_at_domain_value(signal, pt) # value at peak
                
                if v.size > 1:
                    # in case the signal nas more than one channel
                    v = v[self.displayedDetectionChannel]
                    
                if pv.size>1:
                    pv = pv[self.displayedDetectionChannel]
                
                # symbols for the identified events - these are custom shapes defined
                # in gui.signalviewer and added to the dict below: 
                # pyqtgraph.graphicsItems.ScatterPlotItem.Symbols
                # 
                # they are available ONLY AFTER importing gui.signalviewer (done at 
                # the top of this module)!
                #
                # futhermore, the shape is pointing downward if peak value is below 
                # the value at t_start, else upward
                if pv < v:
                    symbol = "event2"
                else:
                    symbol = "event2_dn"
                y = v
                    
                acc = w.annotations.get("Accept", np.array([True]))
                if isinstance(acc, np.ndarray):
                    acc = acc[0]
                
                if acc == True:
                    brush = acc_targetBrush#[0:3] + (255,)
                    
                elif acc == False:
                    brush = rej_targetBrush#[0:3] + (255,)
                    
                target = pg.TargetItem((t, y), 
                                        size=int(targetSize*1.3),
                                        symbol = symbol,
                                        brush = brush,
                                        pen = pg.mkPen(brush, cosmetic=True),
                                        movable=False)
                
                targets.append(target)
                
            self._targets_cache_[:] = targets
        else:
            # retrieve target items from cache
            targets[:] = self._targets_cache_
        #### END prepare indicators for all waves in the current sweep

        #### BEGIN prepare indicator (target) for the currently shown wave 
        # this always changes with the currently shown wave
        if isinstance(peak_time, pq.Quantity):
            peak_value = neoutils.get_sample_at_domain_value(signal, peak_time)

            signalBlocker = QtCore.QSignalBlocker(self.accept_eventCheckBox)
            self.accept_eventCheckBox.setChecked(accepted)
            
            if accepted:
                targetBrush = acc_targetBrush
                targetLabelColor = acc_targetLabelColor
            else:
                targetBrush = rej_targetBrush
                targetLabelColor = rej_targetLabelColor
                
            # NOTE: 2022-12-20 12:49:45
            # waveindex is the index in the currently displayed collection of
            # waves; this is NOT NECESSARILY the actual index of the wave in the
            # spike train's waveforms - such is the case when only accepted waves
            # are displayed e.g., when Plot all waves action is triggered AND
            # All waves to results is unchecked.
            # To avoid confusion, we depict the index of the waves in the 
            # in the train's waveforms.
            current_target = pg.TargetItem((float(peak_time),float(peak_value)),
                                            size=targetSize,
                                            movable=False,
                                            brush=targetBrush,
                                            label=f"{frame_wave_index}",
                                            labelOpts={"color":targetLabelColor,
                                                       "offset":targetLabelOffset})
            
            targets.append(current_target)
        
        # store these in the cache, so we don't have to build with every frame 
        # change in the event viewer.
            
        #### END prepare indicator (target) for the currently shown wave 
        
        if len(targets):
            # WARNING: 2022-12-18 14:40:38
            # remeber to clear overlays before this call
            self._ephysViewer_.overlayTargets(*targets, axis=axis, clear=True)
            self._ephysViewer_.refresh()
        #### END decorate the signal plot in ephys viewer
        
    def _refit_wave(self):
        if self._data_ is None:
            warnings.warn(f"No data!")
            return
        
        # if len(self._detected_events_) == 0:
        #     return
        
        if not self._detected_Events_Viewer_.isVisible():
            return
        
        # WARNING: 2022-12-20 13:28:53
        # This is NOT NECESSARILY the index of the wave in the spike train! 
        # This is is the index of the wave in the currently displayed collection
        # of waves! For the former, see WARNING: 2022-12-20 13:29:57 below
        waveIndex = self._detected_Events_Viewer_.currentFrame
        
        waves = self._detected_Events_Viewer_.yData
        
        if waves is None:
            return
        
        wave = waves[waveIndex]
        
        # WARNING: 2022-12-20 13:29:57
        # THIS below is the index of the waveform in the spike train, NOT the 
        # index of the waveform in the currently displayed collection. For the
        # latter, see WARNING: 2022-12-20 13:28:53
        #
        # NOTE: we need this to correctly pinpoint the waveform in the train
        wave_index = wave.annotations["wave_index"]
        aligned = wave.annotations["Aligned"]
        
        segment = wave.segment
        frame_index = segment.index
        
        frameResult = self._result_[frame_index]
        
        if not isinstance(frameResult, neo.core.spiketrainlist.SpikeTrainList):
            warnings.warn(f"No result for sweep {self.currentFrame}")
            return
        
        if len(frameResult) == 0:
            return
        
        st = frameResult[self._displayed_detection_channel_]
        
        if isinstance(self._data_, neo.Block):
            data_segment = self._data_.segments[self.currentFrame]
            
        elif isinstance(self._data_, neo.Segment):
            data_segment = self._data_
            
        elif isinstance(self._data_, (tuple, list)) and all(isinstance(s, neo.Segment) for s in self._data_):
            segment = self._data_[self.currentFrame]

        else:
            warnings.warn(f"No segment!")
            
            return
        
        if st.segment is not data_segment:
            warnings.warn(f"Segment mismatch between spike train and data!")
            return
        
        if st.segment is not segment:
            warnings.warn(f"Segment mismatch between spike train and plotted event {waveIndex}!")
            return
        
        model_params = self.paramsWidget.value()
        init_params = tuple(p.magnitude for p in model_params["Initial Value:"])
        lo = tuple(p.magnitude for p in model_params["Lower Bound:"])
        up = tuple(p.magnitude for p in model_params["Upper Bound:"])
            
        if self.useTemplateWaveForm and isinstance(self._event_template_, neo.AnalogSignal):
            template_fit = membrane.fit_Event(self._event_template_, init_params, lo, up)
            init_params = template_fit.annotations["event_fit"]["Coefficients"]
                
        fw = membrane.fit_Event(wave, init_params, lo=lo, up=up)
        if self._use_threshold_on_rsq_:
            accept = fw.annotations["event_fit"]["Rsq"] >= self.rSqThreshold
        else:
            accept = True
            
        fw.annotate(Accept = accept)
        fw.annotate(Aligned = aligned)
        
            
        self._detected_Events_Viewer_.yData[waveIndex] = fw
        
        st.annotations["Accept"][wave_index] = accept
        st.annotations["event_fit"][wave_index] = fw.annotations["event_fit"]
        st.annotations["amplitude"][wave_index] = fw.annotations["amplitude"]
        
        # slot the (re-)fitted waveform signal into the correct index in the
        # spike train's waveforms
        st.waveforms[wave_index, :, :] = fw.magnitude[:,:,np.newaxis].T
        
        self._detected_Events_Viewer_.displayFrame()
        # self._detected_Events_Viewer_.refresh()
        self._targets_cache_.clear()
        # self._detected_Events_Viewer_.currentFrame = waveIndex
        self._indicate_events_()
       
    def _clear_detection_in_sweep_(self, segment:neo.Segment):
        mPSCtrains = [s for s in segment.spiketrains if s.annotations.get("source", None) == "Event_detection"]
        for s in mPSCtrains:
            neoutils.remove_spiketrain(segment, s.name)
        
    def _get_previous_detection_(self, segment:neo.Segment):
        """ Returns the segment's spiketrains or None.
        
        WARNING: The spike train list may not necessarily contain PSC spike
        trains; this will be sifted later as necessary.`
        """
        if not isinstance(segment, neo.Segment):
            raise TypeError(f"Expecting a neo.Segment; got {type(segment).__name__} instead")
        
        if len(segment.spiketrains):
            return segment.spiketrains  # a stl
        
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
    
    def _get_event_template_or_waveform_(self, use_template:typing.Optional[bool]=None):
        # see NOTE: 2022-11-17 23:37:00 NOTE: 2022-11-11 23:04:37 NOTE: 2022-11-11 23:10:42
        if use_template is None:
            use_template = self.useTemplateWaveForm
            
        if use_template: # return the cached template if it exists
            if isinstance(self._event_template_, (neo.AnalogSignal, DataSignal)):# and self._event_template_.name == "Event Template":
                return self._event_template_[:,0] # discard any possible fit channels
            else: # no template is loaded; get one from custom file or default file, or generate a synthetic waveform
                self._generate_eventModelWaveform()
                return self._event_model_waveform_
#                 template_OK = False
#                 if os.path.isfile(self._custom_template_file_):
#                     tpl = pio.loadFile(self._custom_template_file_)
#                     if isinstance(tpl, (neo.AnalogSignal, DataSignal)):# and tpl.name.startswith("Event_Template"):
#                         self._event_template_ = tpl
#                         return self._event_template_[:,0]# discard any possible fit channels
#                 
#                 if not template_OK and os.path.isfile(self._template_file_):
#                     tpl = pio.loadFile(self._template_file_)
#                     if isinstance(tpl, (neo.AnalogSignal, DataSignal)):# and tpl.name == "Event Template":
#                         self._event_template_ = tpl
#                         return self._event_template_[:,0] # discard any possible fit channels
#                 
#                 if not template_OK:
#                     signalBlocker = QtCore.QSignalBlocker(self.use_eventTemplate_CheckBox)
#                     self.use_eventTemplate_CheckBox.setChecked(False)
#                     self._use_template_ = False
                            
        else:
            self._generate_eventModelWaveform()
            return self._event_model_waveform_
        
    def _cache_sweep_detection_(self, segment_index:typing.Optional[int]=None):
        if segment_index is None:
            segment_index = self.currentFrame
            
        
    def _detect_all_(self, 
                     waveform:typing.Optional[typing.Union[neo.AnalogSignal, DataSignal]]=None, 
                     **kwargs) -> None:
        """Detects events in all sweeps
        
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
        finishedSignal = kwargs.pop("finishedSignal", None)
        resultSignal = kwargs.pop("resultSignal", None)
        
        if waveform is None:
            waveform  = self._get_event_template_or_waveform_()
            
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
                self.criticalMessage("Detect events in current sweep",
                                     "\n".join(excstr))
                return
                
            if not isinstance(res, neo.core.spiketrainlist.SpikeTrainList):
                continue
            
            self._result_[frame] = res
            
            if clear_prev_detection:
                self._clear_detection_in_sweep_(segment)
                
            segment.spiketrains = res
            
            if isinstance(progressSignal, QtCore.pyqtBoundSignal):
                progressSignal.emit(frame)
                
            if isinstance(loopControl, dict) and loopControl.get("break",  None) == True:
                break
                
    def _undo_sweep(self, segment_index:typing.Optional[int]=None):
        self._targets_cache_.clear()
        if segment_index is None:
            segment_index = self.currentFrame
            
        segment = self._get_data_segment_(segment_index)
        
        # clear detection results in the sweep; restore from undo buffer if present
        self._clear_detection_in_sweep_(segment)
        self._aligned_waves_.clear()
        
        if isinstance(self._ephysViewer_, sv.SignalViewer) and self._ephysViewer_.isVisible():
            self._ephysViewer_.removeTargetsOverlay()
        
        if segment_index not in range(-len(self._undo_buffer_), len(self._undo_buffer_)):
            return
        
        # restore the spiketrains as a spiketrainlist containing the current 
        # non-PSC-detection spike trains and whatever is stored in the cache 
        # for the current segment (ie., at segmentIndex = currentFrame index)
        
        prev_detect = self._undo_buffer_[segment_index]
            
        if isinstance(prev_detect, (tuple, list)):
            if len(prev_detect) == 2:
                if isinstance(prev_detect[0], neo.SpikeTrain) and prev_detect[0].annotations.get("source", None) == "Event_detection":
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
            stl = self._result_[sweep]
            if stl is None:
                return
            
            for st in stl:
                if isinstance(wave, int) and wave in range(-(st.shape[0]), st.shape[0]):
                    if self.useThresholdOnRsquared:
                        st.annotations["Accept"][wave] = st.annotations["event_fit"][wave]["Rsq"] >= self.rSqThreshold
                    else:
                        st.annotations["Accept"][wave] = True
                else:
                    for kw in range(st.shape[0]):
                        if self.useThresholdOnRsquared:
                            st.annotations["Accept"][kw] = st.annotations["event_fit"][kw]["Rsq"] >= self.rSqThreshold
                        else:
                            st.annotations["Accept"][kw] = True
                        
        else:    
            for k, stl in enumerate(self._result_):
                if stl is None:
                    continue
                
                for st in stl:
                    if st.annotations.get("event_fit", None) is None:
                        continue
                    if isinstance(wave, int) and wave in range(-(st.shape[0]), st.shape[0]):
                        if self.useThresholdOnRsquared:
                            st.annotations["Accept"][wave] = st.annotations["event_fit"][wave]["Rsq"] >= self.rSqThreshold
                        else:
                            st.annotations["Accept"][wave] = True
                    else:
                        for kw in range(st.shape[0]):
                            if self.useThresholdOnRsquared:
                                st.annotations["Accept"][kw] = st.annotations["event_fit"][kw]["Rsq"] >= self.rSqThreshold
                            else:
                                st.annotations["Accept"][kw] = True
                        
        self._plot_data()
        if self._reportWindow_.isVisible():
            self._update_report_()
            
    def _tally_events(self):
        if len(self._result_) == 0:
            return (0,0)
        
        nDetectedEvents = 0
        nAcceptedEvents = 0
        
        for k, frameResult in enumerate(self._result_):
            if not isinstance(frameResult, neo.core.spiketrainlist.SpikeTrainList) or len(frameResult) == 0:
                continue
            
            for st in frameResult:
                if st.annotations.get("source", None) != "Event_detection":
                    continue
            
                st_waves = self._extract_waves_(st, valid_only=False)
                nDetectedEvents += len(st_waves)
                
                accepted = len([w for w in st_waves if w.annotations.get("Accept", False)])
                nAcceptedEvents += accepted
                
        return (nDetectedEvents, nAcceptedEvents)
            
    def _report_events_tally(self, total, accepted=0):
        txt = f"Events: {total}"
        if total > 0:
            txt += f" (accepted: {accepted})"
        self._events_tally_label_.setText(txt)
        
                 
    def _update_report_(self):
        if self._data_ is None:
            if isinstance(getattr(self, "_reportWindow_", None), QtWidgets.QMainWindow):
                # NOTE: 2023-01-20 10:13:49
                # because this is called early from loadSettings (when setting up
                # whether to iinclude all waves or just accepted ones in the result)
                # and at that time, self is not fully initialized; notably, self._reportWindow_
                # does not yet exist
                # See NOTE: 2023-01-20 10:14:38 for why we cannot define 
                # self._reportWindow_ early in self.__init__
                if self._reportWindow_.isVisible():
                    self._reportWindow_.clear()
            return
        
        results = self.result() 
        
        if results is None:
            return
        
        resultsDF = results[0]
        
        self._reportWindow_.view(resultsDF, doc_title = f"{self._data_.name} Results")
        self._reportWindow_.show()
        
    @safeWrapper
    def _detect_sweep_(self, segment_index:typing.Optional[int]=None, waveform=None, output_detection=False):
        """ Event detection in a segment
        
        Returns a tuple containing :
        • a spiketrain
        • a list of detected event waveforms,
        
        If nothing was detected returns None.
        
        When detection was successful:
        • the spike train contains:
            ∘ timestamps of the onset of the detected event waves
            ∘ associated event waveform at the timestamp
        
        • the event waveforms list contains the detected events.
        
            This one is for convenience, as the waveforms are also embedded in 
            the spike train described above. However, the embedded waveforms are 
            stored as a 3D numpy array, whereas in this list they are stored as 
            individual neo.AnalogSignal objects (with annotations) useful for 
            the validation process.
        
        The function is called by 
        • triggering `actionDetect_in_current_sweep` with the parameter `segment_index` 
            set to the value of `self.currentFrame`.
        • triggering `actionDetect` in a loop over all segments (with `segment_index`
            parameter set inside the loop)
        
        NOTE: By design this extracts detected waveforms from the raw signal,
        even if detection is performed on a filtered copy of the signal if any
        filters are activated in the "Signal Processing" tab.
        
        """
        self._current_detection_θ.clear()
        self._aligned_waves_.clear()
        
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
            
        # print(f"_detect_sweep_ signal.name {signal.name}")
        
        if not isinstance(signal, neo.AnalogSignal):
            return
        
        epochs = [e for e in segment.epochs if e.name in self._detection_epochs_]
        
        if waveform is None:
            waveform  = self._get_event_template_or_waveform_()
            
        if "Event_template" in waveform.name:
            using_template = self._template_file_
            
        else:
            using_template = False
            
        method = "sliding" if self.useSlidingDetection else "cross-correlation"
        
        processed = signal.annotations.get("filtered", False)
        
        mPSCTrains = None
        
        try:
            if len(epochs):
                mini_waves = list()
                detections = list()
                all_θ = list()
                
                # detect events in individual signal epochs (allowing to define more
                # than one epoch in a signal)
                for epoch in epochs:
                    sig = signal.time_slice(epoch.times[0], epoch.times[0]+epoch.durations[0])
                    # NOTE: 2022-12-15 11:56:46
                    # _process_signal_ checks whether there is any filter enabled
                    # if there is then a filtered copy is passed to the events 
                    # detection function
                    # ATTENTION: This will result in waves extracted from the filtered
                    # version of the signal. This is certainly NOT desirable for
                    # non-stationary fluctation analysis. In such case, if the signal
                    # is beign filtered, then the option "Waves from filtered signal"
                    # must be switched off. Alternatively, run the detection directly
                    # on the raw signal (or at least a signal NOT smoothed).
                    
                    if not processed:
                        sig = self._process_signal_(sig, newFilter=True)
                        
                    if not self.useFilteredWaves:
                        quasi_raw = self._process_signal_(signal.time_slice(epoch.times[0], epoch.times[0]+epoch.durations[0]),
                                                        dc_detrend_only=True)
                        quasi_raw.name = signal.name
                    else:
                        quasi_raw = None
                        
                    detection = membrane.detect_Events(sig, waveform, 
                                                    useCBsliding = self.useSlidingDetection,
                                                    threshold = self._detection_threshold_,
                                                    outputDetection = output_detection,
                                                    raw_signal = quasi_raw)
                    
                    # print(f"detection {detection}")
                    
                    if detection is None:
                        continue
                    
                    if output_detection:
                        detection, thetas = detection
                        # print(f"{[type(t).__name__ for t in thetas]}")
                        all_θ.append(thetas)
                        
                    if not isinstance(detection, neo.core.spiketrainlist.SpikeTrainList):
                        continue
                    
                    # this below is a collection of spike train lists (one per epoch)!
                    # but each spiketrainlist should have up to the same max number 
                    # of spiketrains (i.e. as many as there are channels)
                    detections.append(detection) 
                
                # collate the detection spike trains into one single spike train
                if len(detections):
                    template = detections[0][0].annotations["waveform"]
                    # splice individual detections in each separate epoch; these
                    # individual epoch detections are SpikeTrainList objects, possibly
                    # with more than one SpikeTrain inside (one per channel)
                    max_channels = max(len(d) for d in detections)
                    stt = list() #  will hold spliced spike trains, one per channel
                    for kc in range(max_channels):
                        wave_names = list()
                        accept = list()
                        fits = list()
                        
                        st_ = [d[kc] for d in detections if kc < len(d)]
                        
                        if len(st_) == 0:
                            continue
                        
                        for t in st_:
                            wave_names.extend(t.annotations["wave_name"])
                            accept.extend(t.annotations["Accept"])
                            fits.extend(t.annotations["event_fit"])
                            
                        pt = np.concatenate([t.annotations["peak_time"].magnitude for t in st_], axis=0) * st_[0].units
                        
                        if any(len(v) == 0 for v in (wave_names, accept, fits, pt)):
                                continue
                            
                        θ_ = [t.annotations["θ"] for t in st_]
                        
                        # print(len(θ_), [type(t) for t in θ_])
                        # print(*θ_)
                        # print(type(*θ_))
                        st = neoutils.splice_signals(*st_)
                        st.name= "events"
                        st.segment = segment
                        
                        if len(θ_) > 1:
                            θ = neoutils.splice_signals(*θ_, times = signal.times)
                            θ.name = "events"
                        else:
                            θ = θ_[0]
                            
                        θ.description = f"Detection criterion ({method})"
                        
                        if not self.useSlidingDetection:
                            θmax = np.max(θ[~np.isnan(θ)])
                            θnorm = θ.copy()  # θ is a neo signal
                            θnorm = neo.AnalogSignal(sigp.scale_waveform(θnorm, 10, θmax),
                                                    units = θ.units, t_start = θ.t_start,
                                                    sampling_rate = θ.sampling_rate,
                                                    name = f"{θ.name}_scaled",
                                                    description = f"{θ.description} scaled to 10/{θmax}")
                        else:
                            θnorm = θ
                            
                        chids = signal.array_annotations.get("channel_ids", None)
                        
                        if chids is not None:
                            chid = chids[kc]
                            try:
                                chid = int(chid)
                            except:
                                chid = kc
                        else:
                            chid = kc
                            
                        # print(f"accept {accept}")
                        
                        if all(isinstance(v, bool) for v in accept):
                            accept = np.array(accept)
                            
                        elif all(isinstance(v, np.ndarray) for v in accept):
                            accept = np.concatenate(accept)
                            
                        else:
                            accept = np.full((st.shape[0],), fill_value = True, dtype=np.bool_)
                        
                        st.annotate(
                                    peak_time = pt, 
                                    wave_name = wave_names,
                                    waveform=template,
                                    event_fit = fits,
                                    θ = θ,
                                    θnorm = θnorm, 
                                    channel_id = chid,
                                    source = "Event_detection",
                                    signal_units = signal.units,
                                    signal_origin = signal.name,
                                    datetime = datetime.datetime.now(),
                                    Aligned = False,
                                    Accept = accept,
                                    segment_index = segment_index
                                    )
                        
                        stt.append(st)
                        
                    if len(stt):
                        mPSCTrains = neo.core.spiketrainlist.SpikeTrainList(items = stt,
                                                                            segment = segment) # spike train list, one train per channel
                        for st_ in mPSCTrains:
                            st_.segment = segment
                    else:
                        mPSCTrains = None
                    
                else:
                    mPSCTrains = None
                    
                if output_detection:
                    testθ = list()
                    for kc in range(signal.shape[1]):
                        channelθ = list()
                        for thetas in all_θ:
                            if kc < len(thetas):
                                channelθ.append(thetas[kc])
                                
                        if len(channelθ) == 0:
                            continue
                                
                        if len(channelθ) == 1:
                            θ = channelθ[0]
                            
                        else:
                            θ = neoutils.splice_signals(*channelθ, times = signal.times)
                            
                        self._current_detection_θ.append(θ)
                    
            else: # no epochs - detect in the whole signal
                # if self.useFilteredWaves:
                if not processed:
                    signal = self._process_signal_(signal, newFilter=True)

                if not self.useFilteredWaves:
                    quasi_raw = self._process_signal_(signal, dc_detrend_only=True)
                    quasi_raw.name = signal.name
                else:
                    quasi_raw = None
                    
                detection = membrane.detect_Events(signal, waveform, 
                                                useCBsliding = self.useSlidingDetection,
                                                threshold = self._detection_threshold_,
                                                outputDetection = output_detection,
                                                raw_signal = quasi_raw)
                
                if detection is None:
                    return
                
                if output_detection:
                    mPSCTrains, thetas = detection
                    self._current_detection_θ = thetas
                else:
                    mPSCTrains = detection

            if isinstance(mPSCTrains, neo.core.spiketrainlist.SpikeTrainList):
                mPSCTrains.segment = segment
                
                for st_ in mPSCTrains:
                    st_.segment = segment
                    st_.annotate(using_template = using_template,
                                signal_origin = signal.name)
                
                # now, fit the minis
                for st in mPSCTrains:
                    fitted_minis = self._fit_waves_(st, prefix = signal.name)
                    if isinstance(fitted_minis, Exception):
                        traceback.print_exc()
                        excstr = traceback.format_exception(fitted_minis)
                        msg = f"Event {kw} in sweep {segment}:\n{excstr[-1]}"
                        self.criticalMessage("Fitting event",
                                                "\n".join(excstr))
                        return 
                    if fitted_minis is None or len(fitted_minis) == 0:
                        continue
                    
                    st.annotations["amplitude"] = list()
                    
                    for kw, fw in enumerate(fitted_minis):
                        if self._use_threshold_on_rsq_:
                            accept = fw.annotations["event_fit"]["Rsq"] >= self.rSqThreshold
                            st.annotations["Accept"][kw] = accept
                        else:
                            st.annotations["Accept"][kw] = fw.annotations["Accept"]
                            
                        st.annotations["event_fit"][kw] = fw.annotations["event_fit"]
                        st.annotations["amplitude"].append(fw.annotations["amplitude"])

                    new_waves = np.concatenate([fw.magnitude[:,:,np.newaxis] for fw in fitted_minis], axis=2)
                    st.waveforms = new_waves.T
                
                return mPSCTrains
        
        except Exception as e:
            print(f"In sweep {segment_index}")
            traceback.print_exc()

    @pyqtSlot()
    def _slot_create_event_template(self):
        # FIXME 2022-12-14 18:54:04
        if len(self._aligned_waves_) == 0:
            return
        
        try:
            klass = type(self._aligned_waves_[0])
            merged = neoutils.concatenate_signals(*self._aligned_waves_)
            
            self._event_template_ = klass(merged.mean(axis=1),
                                          units = merged.units,
                                          t_start = merged.t_start,
                                          sampling_rate = merged.sampling_rate,
                                          name = "Event_template")
            
            self._event_template_.annotate(channel_id = self._aligned_waves_[0].annotations["channel_id"],
                                           signal_origin = self._aligned_waves_[0].annotations["signal_origin"],
                                           source = str(self.metaDataWidget.sourceID),
                                           cell = str(self.metaDataWidget.cell),
                                           field = str(self.metaDataWidget.field),
                                           age = str(self.metaDataWidget.age),
                                           sex = str(self.metaDataWidget.sex),
                                           genotype = str(self.metaDataWidget.genotype),
                                           dataname = str(self.metaDataWidget.dataName),
                                           datetime = datetime.datetime.now())
            
            self._event_template_.array_annotate(channel_names = self._aligned_waves_[0].array_annotations["channel_names"][0],
                                                channel_ids = self._aligned_waves_[0].array_annotations["channel_ids"][0],
                                                nADCNum = self._aligned_waves_[0].array_annotations["nADCNum"][0])
            
            model_params = self.paramsWidget.value()
            init_params = tuple(float(p) for p in model_params["Initial Value:"])
            lo = tuple(float(p) for p in model_params["Lower Bound:"])
            up = tuple(float(p) for p in model_params["Upper Bound:"])
            fw = membrane.fit_Event(self._event_template_, init_params, lo, up)
            
            self._event_template_ = fw
            for action in (self.actionSave_Event_Template,
                           self.actionExport_Event_Template,
                           self.actionRemember_Event_Template,
                           self.actionForget_Event_Template,
                           self.actionPlot_Event_template,
                           self.use_eventTemplate_CheckBox):
                action.setEnabled(isinstance(self._event_template_, (neo.AnalogSignal, DataSignal)))
            
            self._plot_template_()
            
        except Exception as e:
            traceback.print_exc()
            excstr = traceback.format_exception(e)
            self.criticalMessage("Make event template",
                                 "\n".join(excstr))
            
        
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
        waveform = self._get_event_template_or_waveform_(use_template = self._use_template_)
        if waveform is None:
            self.criticalMessage("Detect events in current sweep",
                                 "No event model waveform or template is available")
            self._report_events_tally(0)
            return
        
        segment = self._get_data_segment_(index=self.currentFrame)
        
        if isinstance(segment, neo.Segment):
            prev_detect = self._get_previous_detection_(segment)
            
            self._undo_buffer_[self.currentFrame] = prev_detect
                
            mPSCTrains = self._detect_sweep_(waveform=waveform, output_detection=True) # this is (mPSCtrains, waves)
            if mPSCTrains is None:
                return
            
            
            self._result_[self.currentFrame] = mPSCTrains
            

            # NOTE: 2022-11-20 11:30:15
            # remove the previous detection if the appropriate widget is checked,
            # REGARDLESS of whether anything was detected this time around, so that
            # the spiketrains reflect the results of the detection with the CURRENT
            # parameters
            if self.clearPreviousDetectionCheckBox.isChecked():
                self._clear_detection_flag_ = True # to make sure this is up to date
                self._clear_detection_in_sweep_(segment)
                
            # embed the spike train in the segment
            segment.spiketrains=mPSCTrains
            
            self._plot_data()
            total_evt, acc_evt = self._tally_events()
            self._report_events_tally(total_evt, acc_evt)
            
    @pyqtSlot()
    def _slot_undoCurrentSweep(self):
        """Restores current segment spiketrains to the state before last detection.
        TODO: update result
        """
        self._undo_sweep(self.currentFrame)
        self._plot_data()
        
        total_evts, acc_evts = self._tally_events()
        self._report_events_tally(total_evts, acc_evts)
            
    def _slot_saveResults(self):
        results = self.result()
        if results is None:
            return
        
        resultsDF, resultsTrains, resultsWaves = results
        
        fn, fl = self.chooseFile("Save events result table",
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
    def _slot_saveEventTrains(self):
        results = self.result()
        if results is None:
            return
        
        resultsDF, resultsTrains, resultsWaves = results
        
        fn, fl = self.chooseFile("Save event trains",
                                 fileFilter = ";;".join(["Pickle files (*.pkl)", "HDF5 Files (*.hdf)"]),
                                 single=True,
                                 save=True)
        
        if isinstance(fn, str) and len(fn.strip()):
            if fl == "Pickle files (*.pkl)":
                pio.savePickleFile(resultsTrains, fn)
                
            elif fl == "HDF5 Files (*.hdf)":
                pio.saveHDF5(resultsTrains, fn)
                
    @pyqtSlot()
    def _slot_saveEventWaves(self):
        results = self.result()
        if results is None:
            return
        
        resultsDF, resultsTrains, resultsWaves = results
        
        fn, fl = self.chooseFile("Save event waveforms",
                                 fileFilter = ";;".join(["Pickle files (*.pkl)", "HDF5 Files (*.hdf)"]),
                                 single=True,
                                 save=True)
        
        if isinstance(fn, str) and len(fn.strip()):
            if fl == "Pickle files (*.pkl)":
                pio.savePickleFile(resultsWaves, fn)
                
            elif fl == "HDF5 Files (*.hdf)":
                pio.saveHDF5(resultsWaves, fn)
                
    @pyqtSlot()
    def _slot_exportEventsTable(self):
        results = self.result()
        if results is None:
            return
        
        resultsDF, resultsTrains, resultsWaves = results
        
        varName = f"{self._data_.name}_events_table"
        
        self.exportDataToWorkspace(resultsDF, var_name=varName, title="Export events table to workspace")
        
    @pyqtSlot()
    def _slot_exportEventTrains(self):
        results = self.result()
        if results is None:
            return
        
        resultsDF, resultsTrains, resultsWaves = results
        
        varName = f"{self._data_.name}_event_trains"
        
        self.exportDataToWorkspace(resultsTrains, var_name=varName, title="Export mPSC trains to workspace")
        
    @pyqtSlot()
    def _slot_exportEventWaves(self):
        results = self.result()
        if results is None:
            return
        
        resultsDF, resultsTrains, resultsWaves = results
        
        varName = f"{self._data_.name}_event_waves"
        
        self.exportDataToWorkspace(resultsWaves, var_name=varName, title="Export mPSC waves to workspace")
        
    @pyqtSlot()
    def _slot_exportAlignedWaves(self):
        if not isinstance(self._aligned_waves_, (tuple, list)) or len(self._aligned_waves_) == 0:
            self.criticalMessage("Export aligned waveforms", "Must align the detected waves first!")
            return
        varName = f"{self._data_.name}_aligned_waves"
        self.exportDataToWorkspace(self._aligned_waves_, var_name=varName, title="Export aligned waveforms")
        
    @pyqtSlot()
    def slot_showReportWindow(self):
        self._update_report_()
        
    @pyqtSlot(bool)
    def _slot_setOverlayTemplateModel(self, value):
        self.overlayTemplateModel = value
        self._plot_model_()
        
    @pyqtSlot()
    def _slot_clearResults(self):
        self._targets_cache_.clear()
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
#     def _slot_detectionDone(self):
#         # NOTE: 2022-11-26 09:06:05
#         # QRunnable paradigm, see # NOTE: 2022-11-26 09:06:16
#         self._plot_data()
#         
#         total_evts, acc_evts = self._tally_events()
#         self._report_events_tally(total_evts, acc_evts)
        
    @pyqtSlot()
    def _slot_alignThread(self):
        if isinstance(self._data_, (neo.Block, neo.Segment)):
            vartxt = f"in {self._data_.name}"
        else:
            vartxt = ""

        if self._data_ is None:
            return
        
        if all(v is None for v in self._result_):
            return
        
        result = self.result()
        
        if result is None:
            return
        
        table, trains, waves = result
        
        progressDisplay = QtWidgets.QProgressDialog(f"Aligning event waveforms {vartxt}", 
                                                    "Abort", 
                                                    0, len(self._result_), 
                                                    self)
        progressDisplay.canceled.connect(self._slot_breakLoop)
        
        self._alignThread_ = QtCore.QThread()
        self._alignWorker_ = pgui.ProgressWorkerThreaded(self.alignWaves,
                                                         loopControl = self.loopControl,
                                                         threaded=True, trains = trains)
        
        self._alignWorker_.signals.signal_Progress.connect(progressDisplay.setValue)
        
        self._alignWorker_.moveToThread(self._alignThread_)
        self._alignThread_.started.connect(self._alignWorker_.run)
        self._alignWorker_.signals.signal_Finished.connect(self._alignThread_.quit)
        self._alignWorker_.signals.signal_Finished.connect(self._alignWorker_.deleteLater)
        self._alignWorker_.signals.signal_Finished.connect(self._alignThread_.deleteLater)
        self._alignWorker_.signals.signal_Finished.connect(lambda: progressDisplay.setValue(progressDisplay.maximum()))
        self._alignWorker_.signals.signal_Result[object].connect(self._slot_alignThread_ready)
        
        self._alignThread_.finished.connect(self._alignWorker_.deleteLater)
        self._alignThread_.finished.connect(self._alignThread_.deleteLater)
        
        self._enable_widgets(self.actionCreate_Event_Template,
                             self.actionPlot_events_for_template,
                             self.actionPlot_aligned_event_waveforms,
                             self.actionDetect,
                             self.actionUndo,
                             self.actionDetect_in_current_sweep,
                             self.actionUndo_current_sweep,
                             self.actionClear_results,
                             self.accept_eventCheckBox,
                             self.actionView_results,
                             self.actionExport_results,
                             self.actionSave_results,
                             self.use_eventTemplate_CheckBox,
                             self.actionCreate_Event_Template,
                             self.actionOpen_Event_Template,
                             self.actionImport_Event_Template,
                             enable=False)
        
        self._alignThread_.start()
        
    @pyqtSlot()
    def _slot_alignThread_ready(self):
        self.loopControl["break"] = False
        self._enable_widgets(self.actionCreate_Event_Template,
                             self.actionPlot_events_for_template,
                             self.actionPlot_aligned_event_waveforms,
                             self.actionDetect,
                             self.actionUndo,
                             self.actionDetect_in_current_sweep,
                             self.actionUndo_current_sweep,
                             self.actionClear_results,
                             self.accept_eventCheckBox,
                             self.actionView_results,
                             self.actionExport_results,
                             self.actionSave_results,
                             self.use_eventTemplate_CheckBox,
                             self.actionCreate_Event_Template,
                             self.actionOpen_Event_Template,
                             self.actionImport_Event_Template,
                             enable=True)
        
        self._plot_aligned_waves()
            
    @pyqtSlot()
    def _slot_detectThread(self):
        # NOTE: 2022-11-26 10:24:01 IT WORKS !!!
        if self._data_ is None:
            self.criticalMessage("Detect events",
                                 "No data!")
            return
            
        waveform = self._get_event_template_or_waveform_()
        
        if waveform is None:
            self.criticalMessage("Detect events",
                                 "No event waveform or template is available")
            return
        
        if isinstance(self._data_, (neo.Block, neo.Segment)):
            vartxt = f"in {self._data_.name}"
        else:
            vartxt = ""

        self._clear_detection_flag_ = self.clearPreviousDetectionCheckBox.isChecked() # to make sure this is up to date
            
        progressDisplay = QtWidgets.QProgressDialog(f"Detecting events {vartxt}", 
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
        
        self._detectWorker_.moveToThread(self._detectThread_)
        self._detectThread_.started.connect(self._detectWorker_.run) # see NOTE: 2022-11-26 16:56:19 below
        self._detectWorker_.signals.signal_Finished.connect(self._detectThread_.quit)
        self._detectWorker_.signals.signal_Finished.connect(self._detectWorker_.deleteLater)
        self._detectWorker_.signals.signal_Finished.connect(self._detectThread_.deleteLater)
        self._detectWorker_.signals.signal_Finished.connect(lambda : progressDisplay.setValue(progressDisplay.maximum()))
        self._detectWorker_.signals.signal_Result[object].connect(self._slot_detectThread_ready)
        
        self._detectThread_.finished.connect(self._detectWorker_.deleteLater)
        self._detectThread_.finished.connect(self._detectThread_.deleteLater)
        
        self._enable_widgets(self.actionDetect,
                             self.actionUndo,
                             self.actionDetect_in_current_sweep,
                             self.actionUndo_current_sweep,
                             self.actionClear_results,
                             self.accept_eventCheckBox,
                             self.actionView_results,
                             self.actionExport_results,
                             self.actionSave_results,
                             self.use_eventTemplate_CheckBox,
                             self.actionCreate_Event_Template,
                             self.actionOpen_Event_Template,
                             self.actionImport_Event_Template,
                             enable=False)
        
        self._detectThread_.start() # ↯ _detectThread_.started ↣ _detectWorker_.run NOTE: 2022-11-26 16:56:19
        
    @pyqtSlot(object)
    def _slot_detectThread_ready(self, result:object):
        """Called when threaded detection finished naturally or was interrupted.
        The parameter `result` is ignored.
        """
        # print(f"{self.__class__.__name__}._slot_detectThread_ready(result = {result})")
        self._plot_data()
        total_evts, acc_evts = self._tally_events()
        self._report_events_tally(total_evts, acc_evts)
        self._enable_widgets(self.actionDetect,
                             self.actionUndo,
                             self.actionDetect_in_current_sweep,
                             self.actionUndo_current_sweep,
                             self.actionClear_results,
                             self.accept_eventCheckBox,
                             self.actionView_results,
                             self.actionExport_results,
                             self.actionSave_results,
                             self.use_eventTemplate_CheckBox,
                             self.actionCreate_Event_Template,
                             self.actionOpen_Event_Template,
                             self.actionImport_Event_Template,
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
        self._targets_cache_.clear()
        if isinstance(self._data_, neo.Block):
            for k in range(len(self._data_.segments)):
                self._undo_sweep(k)
                
        elif isinstance(self._data_, neo.Segment):
            self._undo_sweep(0)
            
        elif isinstance(self._data_, (tuple, list)) and all(isinstance(s, neo.Segment) for s in self._data_):
            for k in range(len(self._data_)):
                self._undo_sweep(k)
                
        self._plot_data()
        
        total_evts, acc_evts = self._tally_events()
        self._report_events_tally(total_evts, acc_evts)
        
        self._update_report_()
            
    @pyqtSlot()
    def _slot_ephysViewer_closed(self):
        self.unlinkFromViewers(self._ephysViewer_)
        self._ephysViewer_ = None
        
    @pyqtSlot()
    def _slot_waveFormViewer_closed(self):
        self._waveFormViewer_ = None
        
    @pyqtSlot()
    def _slot_detected_mPSCViewer_closed(self):
        self._detected_Events_Viewer_ = None
        
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
        # self._get_event_template_or_waveform_()
        if self._use_template_ and isinstance(self._event_template_, (neo.AnalogSignal, DataSignal)):
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
        # maxVal = 100 if self.useSlidingDetection else 10
        # sigBlock = QtCore.QSignalBlocker(self.detectionThresholdSpinBox)
        # if self.detectionThresholdSpinBox.value() > maxVal:
        #     self.detectionThresholdSpinBox.setValue(maxVal)
        # self.detectionThresholdSpinBox.setMaximum(maxVal)
        
    
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
                
            if isinstance(data, (neo.AnalogSignal, DataSignal)):
                self._event_template_ = data
                self._plot_template_()
                # self.use_eventTemplate_CheckBox.setEnabled(True)
                self.lastUsedTemplateFile = fileName

                for action in (self.actionSave_Event_Template,
                            self.actionExport_Event_Template,
                            self.actionRemember_Event_Template,
                            self.actionForget_Event_Template,
                            self.actionPlot_Event_template,
                            self.use_eventTemplate_CheckBox):
                    action.setEnabled(isinstance(self._event_template_, (neo.AnalogSignal, DataSignal)))
                
    @pyqtSlot()
    def _slot_saveTemplateFile(self):
        if not isinstance(self._event_template_, (neo.AnalogSignal, DataSignal)):
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
                pio.saveHDF5(self._event_template_, fileName)
            else:
                pio.savePickleFile(self._event_template_, fileName)
                
            self.lastUsedTemplateFile = fileName
                
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
            
                
            self.setData(data)
            # self._set_data_(data)
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
            obj = objs[0]
            if isinstance(obj, (neo.AnalogSignal, DataSignal)):
                self._event_template_ = objs[0]
                self._plot_template_()
                for action in (self.actionSave_Event_Template,
                            self.actionExport_Event_Template,
                            self.actionRemember_Event_Template,
                            self.actionForget_Event_Template,
                            self.actionPlot_Event_template,
                            self.use_eventTemplate_CheckBox):
                    action.setEnabled(isinstance(self._event_template_, (neo.AnalogSignal, DataSignal)))
            
        
            
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
        if not isinstance(self._event_template_, (neo.AnalogSignal, DataSignal)):
            return
        
        # TODO: 2022-11-27 22:04:11
        # see TODO: 2022-11-27 22:03:10 and TODO 2022-11-27 22:03:34
        # if os.path.isfile(self.templateWaveFormFile):
        fn, ext = os.path.splitext(self.templateWaveFormFile)
        if "pkl" in ext:
            pio.savePickleFile(self._event_template_, self.templateWaveFormFile)
        else:
            pio.saveHDF5(self._event_template_, self.templateWaveFormFile)
                
    @pyqtSlot()
    def _slot_forgetTemplate(self):
        self._event_template_ = None
        for action in (self.actionSave_Event_Template,
                        self.actionExport_Event_Template,
                        self.actionRemember_Event_Template,
                        self.actionForget_Event_Template,
                        self.actionPlot_Event_template,
                        self.use_eventTemplate_CheckBox):
            action.setEnabled(isinstance(self._event_template_, (neo.AnalogSignal, DataSignal)))
     
    @pyqtSlot()
    def _slot_clearFactoryDefaultTemplateFile(self):
        if os.path.isfile(self._default_template_file):
            os.remove(self._default_template_file)
            
    @pyqtSlot()
    def _slot_makeUnitAmplitudeModel(self):
        α, β, x0, τ1, τ2 = [float(v) for v in self.eventModelParametersInitial.values()]
        
        β = models.get_CB_scale_for_unit_amplitude(β, τ1, τ2) # do NOT add x0 here because we only work on xx>=0
        
        init_params = [α * self._signal_units_, β * pq.dimensionless,
                       x0 * self._time_units_, 
                       τ1 * self._time_units_, τ2 * self._time_units_]
        
        lb = [float(v) for v in self.eventModelParametersLowerBounds.values()]
        ub = [float(v) for v in self.eventModelParametersUpperBounds.values()]
        
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
        
        if isinstance(data, (neo.AnalogSignal, DataSignal)):
            self._event_template_ = data
            self._plot_template_()
            for action in (self.actionSave_Event_Template,
                        self.actionExport_Event_Template,
                        self.actionRemember_Event_Template,
                        self.actionForget_Event_Template,
                        self.actionPlot_Event_template,
                        self.use_eventTemplate_CheckBox):
                action.setEnabled(isinstance(self._event_template_, (neo.AnalogSignal, DataSignal)))
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
            
            if isinstance(data, (neo.AnalogSignal, DataSignal)):
                self._event_template_ = data
                self._plot_template_()
                # self.use_eventTemplate_CheckBox.setEnabled(True)
        
                for action in (self.actionSave_Event_Template,
                            self.actionExport_Event_Template,
                            self.actionRemember_Event_Template,
                            self.actionForget_Event_Template,
                            self.actionPlot_Event_template,
                            self.use_eventTemplate_CheckBox):
                    action.setEnabled(isinstance(self._event_template_, (neo.AnalogSignal, DataSignal)))
                
            else:
                self.errorMessage("Load last used mPSC template",
                                 f"Template file {self.lastUsedTemplateFile} does not contain a signal")
                return
            
        else:
            self.errorMessage("Load last used mPSC template",
                             f"Template file {self.lastUsedTemplateFile} not found!")
            
        
    @pyqtSlot()
    def _slot_revertToFactoryDefaultTemplateFile(self):
        self.templateWaveFormFile = self._default_template_file
            
    @pyqtSlot()
    def _slot_exportTemplate(self):
        if not isinstance(self._event_template_, (neo.AnalogSignal, DataSignal)):
            return
        
        self.exportDataToWorkspace(self._event_template_, var_name = "Event_template")
            
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
        
    @pyqtSlot(bool)
    def _slot_set_alignOnRisingPhase(self, val):
        self.alignWavesOnRisingPhase = val == True
        
    @pyqtSlot(object)
    def _slot_cutoffFreqChanged(self, val):
        self.noiseCutoffFreq = val
        
    @pyqtSlot()
    def _slot_setUseFilteredWaves(self):
        self.useFilteredWaves = self.sender().isChecked()
        
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
        
    @pyqtSlot(bool)
    def _slot_set_allWavesToResult(self, value):
        self.allWavesToResult = value
        
    def _process_signal_(self, sig, newFilter:bool=False, dc_detrend_only:bool=False):
        if isinstance(sig, (neo.AnalogSignal, DataSignal)):
            fs = float(sig.sampling_rate)
        else:
            fs = float(self._default_sampling_rate_)
            
        ret = sig
        
        if ret.annotations.get("filtered", False):
            return ret
        
        if self._use_signal_linear_detrend_:
            ret = sigp.detrend(ret, axis=0, bp = [0, ret.shape[0]], type="linear")
            # processed=True

        if self._remove_DC_offset_:
            if self._use_auto_offset_:
                ret = sigp.remove_dc(ret)
            else:
                ret = sigp.remove_dc(ret, self._dc_offset_)
            # processed=True
            
        ret.name = sig.name
        
        if dc_detrend_only:
            return ret
        
        if self._humbug_:
            ret = self._deHum(ret, fs)
            ret.annotate(filtered=True)
            ret.name = sig.name
                
        if self._filter_signal_:
            ret = self._lowpass_filter_signal(ret, makeFilter=newFilter)
            ret.annotate(filtered=True)
            
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
                new_sig.annotate(filtered=True)
                        
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
    def _slot_set_Event_accepted(self):
        if not isinstance(self._detected_Events_Viewer_, sv.SignalViewer):
            return
        
        if not self._detected_Events_Viewer_.isVisible():
            self._detected_Events_Viewer_.setVisible(True)
            
        accept = self.sender().checkState() == QtCore.Qt.Checked
        
        
        waveIndex = self._detected_Events_Viewer_.currentFrame
        
        wave = self._detected_Events_Viewer_.yData[waveIndex]
        
        train_wave_index = wave.annotations["wave_index"] # index of wave in the train
        
        data_sweep = wave.segment.index
        
        frameResult = self._result_[data_sweep] # a spike train list !
        
        if not isinstance(frameResult, neo.core.spiketrainlist.SpikeTrainList):
            return
        
        if self._displayed_detection_channel_ not in range(len(frameResult)):
            return
        
        train = frameResult[self._displayed_detection_channel_]
        
        train.annotations["Accept"][train_wave_index] = accept
        
            # self._detected_Events_Viewer_.currentFrame = self.currentWaveformIndex`
            
        self._detected_Events_Viewer_.yData[waveIndex].annotations["Accept"] = accept
        
        self._targets_cache_.clear()
        
        
        # if len(self._detected_events_):
        #     if self._detected_events_[self.currentWaveformIndex].segment == train.segment:
        #         self._detected_events_[self.currentWaveformIndex].annotate(Accept=accept)
                    
            
        # • refresh mPSC indicator on the main data plot
        self._indicate_events_()
        # self._indicate_events_(self.currentFrame)
        # self._indicate_events_(self.currentWaveformIndex, self.currentFrame)
        #
        # • refresh the results table (DataFrame); to save time, we only do it
        #   if the report window is showing
        if self._reportWindow_.isVisible():
            self._update_report_()
            
        total_evts, acc_evts = self._tally_events()
        self._report_events_tally(total_evts, acc_evts)
        
# NOTE: 2022-11-27 14:44:37
# Not sure how useful this is; for fitting we use the initial values of the 
# model parameters, plus their lower & upper bounds. Tweaking these won't
# necessarily improve the accepting of a detected wave, but will almost surely
# have an impact on later detections because the new parameter intial values
# and bounds will be saved across sessions.
# FIXME DO NOT DELETE: may come back to this
    @pyqtSlot()
    def _slot_refit_Event_Waveform(self):
        """Not sure how refitting helps
        """
        self._refit_wave()
            
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
        self.eventDuration = self.durationSpinBox.value()
        self._plot_model_()
        
    @pyqtSlot(str ,str)
    def _slot_modelParameterChanged(self, row, column):
        if column == "Initial Value:":
            self.eventModelParametersInitial      = self.paramsWidget.parameters["Initial Value:"]
        elif column == "Lower Bound:":
            self.eventModelParametersLowerBounds  = self.paramsWidget.parameters["Lower Bound:"]
        elif column == "Upper Bound:":
            self.eventModelParametersUpperBounds  = self.paramsWidget.parameters["Upper Bound:"]
            
        self._plot_model_()
        
    @pyqtSlot(bool)
    def _slot_lockToolbars(self, value):
        self.toolbarsLocked = value
        
    @pyqtSlot(bool)
    def _slot_setToolBarsVisible(self, value):
        toolbars = (self.mainToolBar, self.detectionToolBar, self.templateToolBar, self.filterToolBar)
        for toolbar in toolbars:
            toolbar.setVisible(value == True)
            
        tbactions = (self.actionShow_all_toolbars, self.actionMain_toolbar,
                     self.actionDetection_toolbar, self.actionTemplate_toolbar,
                     self.actionFilter_toolbar)
        sigBlocks = [QtCore.QSignalBlocker(w) for w in tbactions]
        self.actionShow_all_toolbars.setChecked(all(t.isVisible() for t in toolbars))
        for k,t in enumerate(toolbars):
            tbactions[k+1].setChecked(t.isVisible())
            
        
    @pyqtSlot(bool)
    def _slot_setMainToolbarVisibility(self, value):
        self.mainToolBarVisible = value==True
        
        
    @pyqtSlot(bool)
    def _slot_setDetectionToolbarVisibility(self, value):
        self.detectionToolBarVisible = value==True
        
    @pyqtSlot(bool)
    def _slot_setTemplateToolbarVisibility(self, value):
        self.templateToolBarVisible = value==True
        
    @pyqtSlot(bool)
    def _slot_setFilterToolbarVisibility(self, value):
        self.filterToolBarVisible = value==True
        
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
        # NOTE: 2022-12-15 12:52:12
        # we re-use the viewer to plot filtered signal, θ, not just self._data_
        # hence we need to make sure we don't inadvertently affect the signal 
        # selection combobox
        if self._ephysViewer_.yData is not self._data_:
            return
        
        segment = self._get_data_segment_(self.currentFrame)
        
        if index in range(-len(segment.analogsignals), len(segment.analogsignals)):
            sig_name = segment.analogsignals[index].name
        else:
            sig_name = None
            
        if isinstance(sig_name, str):
            signalBlocker = QtCore.QSignalBlocker(self.signalNameComboBox)
            ndx = self.signalNameComboBox.findText(sig_name)
            if ndx == index:
                self.signalNameComboBox.setCurrentIndex(index)
                old_sig_index = self._signal_index_
                if self._signal_index_ != index:
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
            else:
                sigBlock = QtCore.QSignalBlocker(self.epochComboBox)
                self.epochComboBox.setCurrentIndex(0)
            
        elif value in segment_epoch_names:
            # print(f"_slot_epochComboBoxSelectionChanged selected: {value}")
            self._detection_epochs_.clear()
            self._detection_epochs_.append(value)
            
        elif value == "None":
            self._detection_epochs_.clear()
            
    @pyqtSlot(int)
    def _slot_eventsViewer_frame_changed(self, value):
        signal_blockers = [QtCore.QSignalBlocker(w) for w in (self._detected_Events_Viewer_,)]
        self._events_spinBoxSlider_.value = value
        
        if not self._template_showing_:
            try:
                # print(f"{len(self._detected_Events_Viewer_.yData)}, value = {value}")
                wave = self._detected_Events_Viewer_.yData[value]
                segment_index = wave.segment.index
                if isinstance(self._ephysViewer_, sv.SignalViewer) and self._ephysViewer_.isVisible():
                    if segment_index != self._ephysViewer_.currentFrame:
                        self._ephysViewer_.currentFrame = segment_index
                        self._targets_cache_.clear()
                        sigBlock = QtCore.QSignalBlocker(self._frames_spinBoxSlider_)
                        self._frames_spinBoxSlider_.setValue(segment_index)
                self._currentWaveformIndex_ = value
                QtCore.QTimer.singleShot(100, self._indicate_events_)
                # self._indicate_events_()
            except Exception as e:
                traceback.print_exc()
        
    @pyqtSlot(int)
    def _slot_setWaveFormIndex(self, value):
        """Sets the current frame for the events viewer from the main GUI.
        """
        if not isinstance(self._detected_Events_Viewer_, sv.SignalViewer):
            return
        waves = self._detected_Events_Viewer_.yData
        # print(f"_slot_setWaveFormIndex {len(waves)} waves")
        if value not in range(-len(waves), len(waves)):
            return
        sigBlock = QtCore.QSignalBlocker(self._detected_Events_Viewer_)
        self.displayDetectedWaveform(value)
            
    @pyqtSlot(int)
    def _slot_displayedDetectionChannelChanged(self, val:int):
        self.displayedDetectionChannel = val
        self._slot_plot_detected_events_in_sweep_()

    @property
    def currentWaveformIndex(self):
        return self._currentWaveformIndex_
    
    @currentWaveformIndex.setter
    def currentWaveformIndex(self, value):
        if isinstance(self._detected_Events_Viewer_, sv.SignalViewer):
            if value in range(-len(self._detected_Events_Viewer_.yData), len(self._detected_Events_Viewer_.yData)):
                self._currentWaveformIndex_ = value
        else:
            self._currentWaveformIndex_ = 0
            
    @property
    def displayedDetectionChannel(self):
        return self._displayed_detection_channel_
    
    @displayedDetectionChannel.setter
    def displayedDetectionChannel(self, val:int):
        self._displayed_detection_channel_ = int(val)
            
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
    def useFilteredWaves(self):
        return self._extract_filtered_waves_
    
    
    @markConfigurable("UseFilteredWaves", trait_notifier=True)
    @useFilteredWaves.setter
    def useFilteredWaves(self, value:bool):
        self._extract_filtered_waves_ = value == True
        sigBlock = QtCore.QSignalBlocker(self.actionUseFilteredWaves)
        self.actionUseFilteredWaves.setChecked(self._extract_filtered_waves_ == True)
        
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
    def allWavesToResult(self):
        return self._all_waves_to_result_
    
    @markConfigurable("ResultIncludesAllWaves", trait_notifier=True)
    @allWavesToResult.setter
    def allWavesToResult(self, val:bool):
        self._all_waves_to_result_ = val==True
        sigBlockers = [QtCore.QSignalBlocker(w) for w in (self.actionAll_waves_to_result,
                                                          self.actionPlot_all_events)]
        
        self.actionAll_waves_to_result.setChecked(self._all_waves_to_result_)
        if self._all_waves_to_result_:
            self.actionPlot_all_events.setText("Plot all event waveforms")
            self.actionPlot_all_events.setStatusTip("Plot all event waveforms")
            self.actionPlot_all_events.setWhatsThis("Plot all event waveforms")
        else:
            self.actionPlot_all_events.setText("Plot all accepted waveforms")
            self.actionPlot_all_events.setStatusTip("Plot all accepted waveforms")
            self.actionPlot_all_events.setWhatsThis("Plot all accepted waveforms")
            
        if isinstance(getattr(self, "_reportWindow_", None), QtWidgets.QMainWindow):
            if self._reportWindow_.isVisible():
                self._update_report_()
                
    @property
    def ephysViewer(self):
        return self._ephysViewer_
    
    @property
    def eventViewer(self):
        return self._detected_Events_Viewer_
    
    @property
    def eventsViewer(self):
        return self._detected_Events_Viewer_
    
    @property
    def waveformViewer(self):
        return self._waveFormViewer_
    
    @property
    def reportWindow(self):
        return self._reportWindow_
        
    @property
    def useTemplateWaveForm(self):
        return self._use_template_
    
    @markConfigurable("UseTemplateWaveForm", trait_notifier=True)
    @useTemplateWaveForm.setter
    def useTemplateWaveForm(self, value):
        # print(f"{self.__class__.__name__} @useTemplateWaveForm.setter value: {value}")
        self._use_template_ = value == True
        sigBlocker = QtCore.QSignalBlocker(self.use_eventTemplate_CheckBox)
        self.use_eventTemplate_CheckBox.setChecked(False)
            
    @property
    def alignWavesOnRisingPhase(self):
        return self._align_waves_on_rise_
    
    @markConfigurable("AlignWavesOnRisingPhase", trait_notifier=True)
    @alignWavesOnRisingPhase.setter
    def alignWavesOnRisingPhase(self, val:bool):
        self._align_waves_on_rise_ = val == True
        sigBlock = QtCore.QSignalBlocker(self.actionWaves_alignment_on_rising_phase)
        self.actionWaves_alignment_on_rising_phase.setChecked(self._align_waves_on_rise_)
    
    @property
    def overlayTemplateModel(self):
        return self._overlayTemplateModel
    
    @markConfigurable("OverlayTemplateModel", trait_notifier=True)
    @overlayTemplateModel.setter
    def overlayTemplateModel(self, value):
        self._overlayTemplateModel = value == True
        sigBlock = QtCore.QSignalBlocker(self.actionOverlay_Template_with_Model)
        self.actionOverlay_Template_with_Model.setChecked(self._overlayTemplateModel)
        
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
        self._clear_detection_flag_ = value == True

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
    def eventDuration(self):
        return self._event_duration_
    
    @markConfigurable("Event_Duration", trait_notifier=True)
    @eventDuration.setter
    def eventDuration(self, value):
        # print(f"{self.__class__.__name__} @eventDuration.setter value: {value}")
        self._event_duration_ = value
        # self.configurable_traits["Event_Duration"] = self._event_duration_

    @property
    def eventModelParametersInitial(self):
        """Initial parameter values
        """
        return dict(zip(self._params_names_, self._params_initl_))
    
    # NOTE: 2022-11-28 16:40:23
    # Bypass default trait notifier, since confuse / yaml cannot cope with a pandas Series
    @markConfigurable("eventModelParametersInitial") # , trait_notifier=True) bypass default mechanism!
    @eventModelParametersInitial.setter
    def eventModelParametersInitial(self, value:typing.Union[pd.Series, tuple, list, dict]):
        # print(f"{self.__class__.__name__} @eventModelParametersInitial.setter value: {value}")
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

        self.configurable_traits["eventModelParametersInitial"] = dict(zip(self._params_names_, self._params_initl_))
                
    @property
    def eventModelParametersLowerBounds(self):
        return dict(zip(self._params_names_, self._params_lower_))
    
    @markConfigurable("eventModelParametersLowerBounds")# , trait_notifier=True) see NOTE: 2022-11-28 16:40:23
    @eventModelParametersLowerBounds.setter
    def eventModelParametersLowerBounds(self, value:typing.Union[pd.Series, tuple, list, dict]):
        # print(f"{self.__class__.__name__} @eventModelParametersLowerBounds.setter value: {value}")
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
                
        self.configurable_traits["eventModelParametersLowerBounds"] = dict(zip(self._params_names_, self._params_lower_))
                
    @property
    def eventModelParametersUpperBounds(self):
        return dict(zip(self._params_names_, self._params_upper_))
    
    @markConfigurable("eventModelParametersUpperBounds") # , trait_notifier=True) see NOTE: 2022-11-28 16:40:23
    @eventModelParametersUpperBounds.setter
    def eventModelParametersUpperBounds(self, value:typing.Union[pd.Series, tuple, list, dict]):
        # print(f"{self.__class__.__name__} @eventModelParametersUpperBounds.setter value: {value}")
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
                
        self.configurable_traits["eventModelParametersUpperBounds"] = dict(zip(self._params_names_, self._params_upper_))
                
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
        
    @property
    def mainToolBarVisible(self):
        return self.mainToolBar.isVisible()
    
    @markConfigurable("MainToolBarVisible", conftype="Qt")
    @mainToolBarVisible.setter
    def mainToolBarVisible(self, value):
        if isinstance(value, str):
            value = value.lower() == "true"
            
        self.mainToolBar.setVisible(value == True)
        self.mainToolBar.setFloatable(not self._toolbars_locked_)
        self.mainToolBar.setMovable(not self._toolbars_locked_)
        
        sigBlock = QtCore.QSignalBlocker(self.actionMain_toolbar)
        self.actionMain_toolbar.setChecked(self.mainToolBar.isVisible())
        toolbars = (self.mainToolBar, self.detectionToolBar, self.templateToolBar, self.filterToolBar)
        sigBlock = QtCore.QSignalBlocker(self.actionShow_all_toolbars)
        self.actionShow_all_toolbars.setChecked(all(t.isVisible() for t in toolbars))
        
    @property
    def detectionToolBarVisible(self):
        return self.detectionToolBar.isVisible()
    
    @markConfigurable("DetectionToolBarVisible", conftype="Qt")
    @detectionToolBarVisible.setter
    def detectionToolBarVisible(self, value):
        if isinstance(value, str):
            value = value.lower() == "true"
            
        self.detectionToolBar.setVisible(value == True)
        self.detectionToolBar.setFloatable(not self._toolbars_locked_)
        self.detectionToolBar.setMovable(not self._toolbars_locked_)
        
        sigBlock = QtCore.QSignalBlocker(self.actionDetection_toolbar)
        self.actionDetection_toolbar.setChecked(self.detectionToolBar.isVisible())
        toolbars = (self.mainToolBar, self.detectionToolBar, self.templateToolBar, self.filterToolBar)
        sigBlock = QtCore.QSignalBlocker(self.actionShow_all_toolbars)
        self.actionShow_all_toolbars.setChecked(all(t.isVisible() for t in toolbars))
        
    @property
    def templateToolBarVisible(self):
        return self.templateToolBar.isVisible()
    
    @markConfigurable("TemplateToolBarVisible", conftype="Qt")
    @templateToolBarVisible.setter
    def templateToolBarVisible(self, value):
        if isinstance(value, str):
            value = value.lower() == "true"
            
        self.templateToolBar.setVisible(value == True)
        self.templateToolBar.setFloatable(not self._toolbars_locked_)
        self.templateToolBar.setMovable(not self._toolbars_locked_)
        
        sigBlock = QtCore.QSignalBlocker(self.actionTemplate_toolbar)
        self.actionTemplate_toolbar.setChecked(self.templateToolBar.isVisible())
        toolbars = (self.mainToolBar, self.detectionToolBar, self.templateToolBar, self.filterToolBar)
        sigBlock = QtCore.QSignalBlocker(self.actionShow_all_toolbars)
        self.actionShow_all_toolbars.setChecked(all(t.isVisible() for t in toolbars))
        
    @property
    def filterToolBarVisible(self):
        return self.filterToolBar.isVisible()
    
    @markConfigurable("FilterToolBarVisible", conftype="Qt")
    @filterToolBarVisible.setter
    def filterToolBarVisible(self, value):
        if isinstance(value, str):
            value = value.lower() == "true"
            
        self.filterToolBar.setVisible(value == True)
        self.filterToolBar.setFloatable(not self._toolbars_locked_)
        self.filterToolBar.setMovable(not self._toolbars_locked_)
        
        sigBlock = QtCore.QSignalBlocker(self.actionFilter_toolbar)
        self.actionFilter_toolbar.setChecked(self.filterToolBar.isVisible())
        toolbars = (self.mainToolBar, self.detectionToolBar, self.templateToolBar, self.filterToolBar)
        sigBlock = QtCore.QSignalBlocker(self.actionShow_all_toolbars)
        self.actionShow_all_toolbars.setChecked(all(t.isVisible() for t in toolbars))
        
        
    def modelWave(self):
        return self._get_event_template_or_waveform_(use_template = False)
    
    def templateWave(self):
        if isinstance(self._event_template_, neo.AnalogSignal) and self._event_template_.name == "Event Template":
            return self._event_template_
        
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
            # if isinstance(sig.name, str) and len(sig.name.strip()):
            #     name = f"{sig.name}_{self._filter_type_}"
            # else:
            #     name = f"{self._filter_type_}"
                
            ret.name = sig.name
            ret.description = sig.description
            # ret.description = f"{sig.description} Lowpass {self._filter_type_} cutoff {self._noise_cutoff_frequency_}"
            ann = sig.array_annotations
            for key in ann:
                val = ann[key]
                # if key == "channel_names":
                #     val = f"{ann[key]} filtered"
                # else:
                #     val = ann[key]
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
        
    def result(self, allWaves:typing.Optional[bool]=None):
        """Retrieve the detection result.
        
        Returns a tuple with three elements:
        
        • Events table (a pandas.DataFrame object)
            This contains the start time, peak time, fitted parameters and R² 
            goodness of fit for ALL detected event waveforms in the data regardless
            of whether they have been manually accepted or not (their accepted 
            status is indicated in the "Accept" column of the DataFrame object).
        
            The columns of the DataFrame object are:
        
           "Source", "Cell", "Field", "Age", "Sex", "Genotype" → with the values
                shown inthe top half of the event Detect window
        
            "Data": the name of the electrophysiology record used for detection
            "Date Time": date & time of detection
            "Accept": value of the Accept flag
            "Sweep": index of the sweep (data segment) where the event wave was 
                    detected
            "Wave": index of the event wave in the list of events in the sweep
                    (see above)
            "Start Time": start time of the event waveform including its initial
                baseline; these are NOT the times of the onset of the rising
                phase. The latter cann be calculated as start time + onset (see 
                below).
        
            "Peak Time": time of the event peak (for outward currents) or trough
                        (for inward currents)
            "Amplitude": amplitude of the event waveform,
            "Template": whether a template event was used in detection
            "Fit Amplitude": amplitue of the fitted curve
            "R²": goodnesss of fit
        
            The following are the fitted model parameters for each wave:
            "α": offset (DC component), 
            "β": scale, 
            "Onset (x₀)": onset of the 'rising' phase, 
            "Rise Time (τ₁)": rising phase time constant
            "Decay Time (τ₂)": decay phase time constant
        
        
        • event spiketrains (a list of neo.SpikeTrain objects), each containing
            the time stamps for the start of the events (one spike train per
            sweep of recording). The 'annotations' attributes of the spike train
            contains the peak times of the event waves (as an array), and the
            'waveforms' attribute contains the actual detected event waveforms.
        
        • the detected event waveforms (a list of one neo.AnalogSignal object 
            
            representing detected event waveform, with the membrane current in channel 0 and
            the fitted curve in channel 1)
        
        
        """
        if all(v is None for v in self._result_):
            return
        
        psc_trains = list()
        all_waves = list()
        channel_id = list()
        start_time = list()
        peak_time = list()
        amplitude = list()
        using_template = list()
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
        # current_index = list()
        source_id = list()
        cell_id = list()
        sex = list()
        genotype = list()
        age = list()
        datetime=list()
        dataname = list()
        field_id = list()
        tpl_used = list()
        
        if not isinstance(allWaves, bool):
            allWaves = self.allWavesToResult
        
        for k, frameResult in enumerate(self._result_):
            if not isinstance(frameResult, neo.core.spiketrainlist.SpikeTrainList) or len(frameResult) == 0:
                continue
            
            for st in frameResult:
                if st.annotations.get("source", None) != "Event_detection":
                    continue
                psc_trains.append(st)
                st_waves = self._extract_waves_(st, valid_only=not allWaves)
                for mini_wave in st_waves:
                    seg_index.append(mini_wave.segment.index)
                    accept.append(mini_wave.annotations["Accept"])
                    wave_index.append(mini_wave.annotations["wave_index"])
                    start_time.append(float(st[mini_wave.annotations["wave_index"]]))
                    channel_id.append(mini_wave.annotations["channel_id"])
                    peak_time.append(float(mini_wave.annotations["peak_time"]))
                    amplitude.append(float(mini_wave.annotations["amplitude"]))
                    fit_amplitude.append(float(mini_wave.annotations["event_fit"]["amplitude"]))
                    r2.append(float(mini_wave.annotations["event_fit"]["Rsq"]))
                    offset.append(float(mini_wave.annotations["event_fit"]["Coefficients"][0]))
                    scale.append(float(mini_wave.annotations["event_fit"]["Coefficients"][1]))
                    onset.append(float(mini_wave.annotations["event_fit"]["Coefficients"][2]))
                    tau_rise.append(float(mini_wave.annotations["event_fit"]["Coefficients"][3]))
                    tau_decay.append(float(mini_wave.annotations["event_fit"]["Coefficients"][4]))
                    source_id.append(self.metaDataWidget.sourceID)
                    cell_id.append(self.metaDataWidget.cell)
                    field_id.append(self.metaDataWidget.field)
                    age.append(self.metaDataWidget.age)
                    sex.append(self.metaDataWidget.sex)
                    genotype.append(self.metaDataWidget.genotype)
                    dataname.append(self.metaDataWidget.dataName)
                    datetime.append(self.metaDataWidget.analysisDateTime)
                    using_template.append(mini_wave.annotations.get("using_template", False))
                    
                if len(st_waves):
                    all_waves.extend(st_waves)
                
        if len(psc_trains) == 0:
            return
                
        res = {"Source":source_id, "Cell": cell_id, "Field": field_id,
               "Age": age, "Sex": sex, "Genotype":genotype, 
               "Data": dataname, "Date Time": datetime, "Accept":accept,
               "Sweep": seg_index, "Wave": wave_index, "Channel":channel_id,
               "Start Time": start_time, "Peak Time": peak_time, 
               "Amplitude": amplitude, "Fit Amplitude": fit_amplitude,
               "Rsq": r2, "α":offset, "β": scale, "x0": onset, "τ1": tau_rise, "τ2": tau_decay,
               "Template":using_template}
        
        res_df = pd.DataFrame(res)
        
#         total_evts = len(all_waves)
#         
#         if self.allWavesToResult:
#             acc_evts = len([w for w in all_waves if w.annotations.get("Accept", False)])
#         else:
#             acc_evts = total_evts
#             
#         self._report_events_tally(total_evts, acc_evts)
        
        return res_df, psc_trains, all_waves
    
    
def launch():
    try:
        win = mainWindow.newViewer(EventAnalysis, parent = mainWindow, win_title="Synaptic Events")
        win.show()
    except:
        traceback.print_exc()
        
        
def init_scipyen_plugin():
    return {"Applications|Synaptic Events Analysis":launch}


    
@magics_class
class EventAnalysisMagics(Magics):
    @line_magic
    @needs_local_scope
    def DetectMinis(self, line, local_ns):
        if len(line.strip()):
            data = local_ns.get(line, None)
        else:
            data = None
            
        mw = local_ns.get("mainWindow", None)
        
        if mw.__class__.__name__ == "ScipyenWindow":
            win = mw.newViewer(EventAnalysis, parent=mw, win_title="EventAnalysis")
            if isinstance(data,  neo.Block):
                win.view(data)
            else:
                win.show()
                
def load_ipython_extension(ipython):
    ipython.register_magics(EventAnalysisMagics)
    
