# -*- coding: utf-8 -*-
'''Signal viewer: enhanced signal plotter

Plots a multi-frame 1D signal (i.e. a matrix where each column is a `frame'), one frame at a time. 

Data is plotted in a Qt4 matplotlib figure.

Frame browsing is enabled by a slider & spin box.

Usage examples:

1. From a regular python shell: 

    import signalviewer
    
    import numpy 
    
    dataLen = 256; # samples per frame
    
    # the absicssa (indpendent variable)
    x = numpy.linspace(0,1,dataLen) * 2. * numpy.pi
    
    # the ordinate (dependent variable, i.e. the `signal)
    y = numpy.zeros((dataLen, 3)); # numpy array with three column
                                   # vectors (signal `frames') of 
                                   # dataLen samples each
    
    # populate the data array with some values
    y[:,0] = x; 
    y[:,1] = numpy.sin(x)
    y[:,2] = numpy.cos(x)

    # create an instance of the signalviewer.SignalViewer class e.g.:
    
    sigView = signalviewer.SignalViewer();
    
    sigView.setData(x, y, 'k');
    
    sigView.show();
    
2. From IPython shell:

    import signalviewer
    
    ?signalviewer # to display this docstring
    
    %pylab qt4  # brings numpy functions in the workspace
                # see IPython documentation for details
                # hereafter, no need for the numpy prefix
                
    dataLen = 256;
    
    x = linspace(0,1,dataLen) * 2. * pi; 
    
    y = zeros((dataLen, 3));
    
    y[:,0] = x;
    y[:,1] = sin(x);
    y[:,2] = cos(x);
    
    sigView.setData(x, y, 'k')
    
    sigView.show();
    
3. As a standalone GUI application: it works but has no much functionality yet.
   For now it's just a demo of the SignalViewer class.

4. Dependencies:
python >= 3.4
matplotlib with Qt5Agg backend
PyQt5
vigra and built against python 3
boost C++ libraries built against python 3 (for building vigra against python3)
numpy (for python 3)
quantities (for python 3)
mpldatacursor (for python 3)

CHANGELOG
2020-02-17 14:01:06
    Fixed behaviour for plotting a list of neo.Segment objects

'''
#### BEGIN core python modules
#from __future__ import print_function

from pprint import pprint

import sys, os, traceback, numbers, warnings, weakref, inspect, typing, math

import collections
from collections.abc import Iterable
from functools import partial, singledispatch, singledispatchmethod
from itertools import (cycle, accumulate, chain, )
from operator import attrgetter, itemgetter, methodcaller
from enum import Enum, IntEnum
from dataclasses import MISSING

from traitlets import Bunch


#### END core python modules

#### BEGIN 3rd party modules
from PyQt5 import QtCore, QtGui, QtWidgets, QtSvg
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.uic import loadUiType as __loadUiType__


import numpy as np
import pandas as pd
from pandas import NA
# import pyqtgraph as pg
# pg.Qt.lib = "PyQt5"
from gui.pyqtgraph_patch import pyqtgraph as pg
from gui import guiutils as guiutils
import quantities as pq
import matplotlib as mpl
from matplotlib import pyplot as plt
from matplotlib import cm, colors
import matplotlib.widgets as mpw
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import (FigureCanvasQTAgg as FigureCanvas, 
                                                NavigationToolbar2QT as NavigationToolbar)

import neo

import vigra


from traitlets import Bunch

#### END 3rd party modules

#### BEGIN pict.iolib modules
from iolib import pictio as pio
#### END pict.iolib modules

#### BEGIN pict.core modules
import core.signalprocessing as sgp
from core import (xmlutils, strutils, neoutils, )
from core.neoutils import (get_non_empty_spike_trains,
                           get_non_empty_events,
                           normalized_signal_index,
                           check_ephys_data, 
                           check_ephys_data_collection,
                           set_relative_time_start,
                           segment_start,
                           )

from core.prog import safeWrapper
from core.datatypes import (array_slice, is_column_vector, is_vector, )

from core.utilities import (normalized_index, normalized_axis_index, 
                            normalized_sample_index,)
from core.datasignal import (DataSignal, IrregularlySampledDataSignal,)
from core.triggerprotocols import TriggerProtocol
# NOTE: 2021-11-13 16:27:30
# new types: DataMark and DataZone
from core.triggerevent import (TriggerEvent, TriggerEventType, DataMark)
from core.datazone import DataZone
from core.workspacefunctions import validate_varname
from core.scipyen_config import markConfigurable
from core.traitcontainers import DataBag

from core.strutils import InflectEngine


from imaging.vigrautils import kernel2array

from ephys import ephys as ephys
from ephys.ephys import cursors2epoch

#from core.patchneo import *

#### BEGIN pict.gui modules
#from . import imageviewer as iv
from . import pictgui as pgui
from . import quickdialog as qd
from . import scipyen_colormaps as colormaps

from .scipyenviewer import (ScipyenViewer, ScipyenFrameViewer,Bunch)
from .dictviewer import (InteractiveTreeWidget, DataViewer,)
from .cursors import SignalCursor
from gui.widgets.colorwidgets import ColorSelectionWidget, quickColorDialog
from gui.pictgui import GuiWorker
from gui.itemslistdialog import ItemsListDialog

#### END pict.gui modules

# each spike is a small vertical line centered at 0.0, height of 1
if "spike" not in pg.graphicsItems.ScatterPlotItem.Symbols.keys():
    spike = QtGui.QPainterPath(QtCore.QPointF(0.0, -0.5))
    spike.lineTo(QtCore.QPointF(0.0, 0.5))
    spike.closeSubpath()
    pg.graphicsItems.ScatterPlotItem.Symbols["spike"] = spike

if "event" not in pg.graphicsItems.ScatterPlotItem.Symbols.keys():
    spike = QtGui.QPainterPath(QtCore.QPointF(-0.1, 0.5))
    spike.lineTo(QtCore.QPointF(0.0, -0.5))
    spike.lineTo(QtCore.QPointF(0.1, 0.5))
    spike.closeSubpath()
    pg.graphicsItems.ScatterPlotItem.Symbols["event"] = spike

"""
canvas events in matplotlib:
DEPRECATED here
['resize_event',
 'draw_event',
 'key_press_event',
 'key_release_event',
 'button_press_event',
 'button_release_event',
 'scroll_event',
 'motion_notify_event',
 'pick_event',
 'idle_event',
 'figure_enter_event',
 'figure_leave_event',
 'axes_enter_event',
 'axes_leave_event',
 'close_event']
 
"""

__module_path__ = os.path.abspath(os.path.dirname(__file__))

Ui_SignalViewerWindow, QMainWindow = __loadUiType__(os.path.join(__module_path__,'signalviewer.ui'))

#class PlotWorker(QtCore.QObject):
    
    #pass
 
class SignalViewer(ScipyenFrameViewer, Ui_SignalViewerWindow):
    """ A plotter for multi-sweep signals ("frames" or "segments"), with cursors.
    
        Python data types handled by SignalViewer as of 2019-11-23 11:30:23:
        --------------------------------------------------------------------
        NOTE: see also Glossary of terms, below
        
        neo.Block
        neo.Segment
        neo.AnalogSignal
        neo.IrregularlySampledSignal
        datatypes.DataSignal
        datatypes.IrregularlySampledDataSignal
        vigra.Kernel1D 
        
        1D numpy arrays - these represent a single-channel signal with shape (n,)
            where n is the number of samples;
            the signal "domain" (time, space, etc, analogous to the definition 
            domain of a mathematical function) may be given as "x" or will be
            generated as an index array of the data samples.
            
        2D numpy arrays - represent a collection of 1D signals (signal "channels"),
            as either column or row vectors.
            
            The actual layout of the signal channels is specified by the 
            "signalChannelAxis" parameter which, when None, will be assigned the
            value of 1 (by default, axis 1 is considered the "channel" axis)
            
            signalChannelAxis - specifies the index of the axis along which the
                "channels" are defined:
            
            signalChannelAxis == 0          => channels are row vectors
            signalChannelAxis == 1 or None  => channels are column vectors
            
            The layout of the plot is specified by "frameAxis" and 
            "separateSignalChannels":
            
            if frameAxis is None:
                if separateSignalChannels is False:
                    all channels are plotted overlaid in the same axes system 
                    (henceforth a PyQtGraph plotItem) in a single "frame"
                    
                else:
                    each channel is plotted in its own plotItem; plot items are
                    stacked in a column in a single "frame"
                    
            elif frameAxis == signalChannelAxis:
                each channel is plotted in its own plotItem, one item per frame
                
            else:
                raise Exception
                
        3D numpy arrays - considered as a collection of multi-channel signals
            with frames.
            
            Data layout is defined by "signalChannelAxis" and "frameAxis", which 
            must be distinct, and not None. 
            
            The layout of the plot is determined by "frameAxis" and 
            "separateSignalChannels".
            
        Glossary of terms:
        ------------------
        Signal: array of numeric data.
            Contains at least one "signal channel" (sub-arrays). 
            
            May contain metadata describing the semantic of the array axes,
            sampling resolution, etc (e.g. vigra.VigraArray).
            
            The signal's domain is NOT considered to be contained in the array,
            i.e. it is assumed to exist in a separate numeric array.
            
            The simplest and typical example of a signal is a numpy.ndarray, 
            which is interpreted to have at least one channel, and arranged in 
            at least one frame, depending on the value of "frameAxis" and 
            "signalChannelAxis" parameters passed to the setData() function.
            
        Signal channel: sub-array of numeric data, with the same length as the
            signal to which it belongs. Channels are defined along one of the 
            array's axes.
            
        Frame: Collection of data plotted together at any one time. Semantically
            represents data collected in the same recording epoch.
            Synonims: sweep, segment.
            
            For numpy array signals, a frame is a sub-array with the same 
            length and number of channels as the signal. For structured signal
            collections (see below) a frame may contain a collection of different
            signal types.
            
        Structured signal objects: "elaborated" types that encapsulate a signal
            together with the signal's domain, and possible metadata with
            signal and domain units, sampling frequency and calibration.
            
            The signal's domain is as an attribute that either resolves to a 
            numeric array of the same length as the signal, or is dynamically 
            calculated by a method of the signal object.
            
            Examples: 
            AnalogSignal, IrregularlySampledSignal and their equivalents in the 
            datatypes module: DataSignal and IrregularlySampledDataSignal.
            
            Other signal-like objects that fall in this category are:
            
            * from the neo package (SpikeTrain, Epoch, Event)
            * from the pandas package (numeric Series and DataFrame)
            * from in the datatypes module (TriggerEvent).
            
        Structured signal collection: even more elaborated types containing
            signals organized in frames and by type.
            
            Examples (from neo package): Segment, Block, Unit, ChannelIndex
            
        Regularly sampled signals are signals generated by sampling analog data
        at regular intervals. In Scipyen, neo.AnalogSignal, datatypes.DataSignal,
        and numpy arrays (including Vigra Arrays) all represent regularly sampled
        signals.
        
        Irregularly sampled signals are generated by sampling analog data at 
        arbitrary points of the signal domain. These are represented by
        neo.IrregularlySampledSignal and datatypes.DataSignal.
        
       ChannelIndex, Unit -- see the documentation of neo package

            
    CHANGELOG
    =========
    NOTE: 2019-02-11 13:52:30
    heavily based on pyqtgraph package
    
    TODO: ability to use the modifiable LinearRegionItem objects to edit epochs 
    in neo.Segment data (if / when plotted)
    
    For now, LinearRegionItems only illustrate the epochs, but do not modify them
    
    TODO: write the documentation
          
    """
    #dockedWidgetsNames = ["coordinatesDockWidget"]

    sig_activated = pyqtSignal(int, name="sig_activated")
    sig_plot = pyqtSignal(dict, name="sig_plot")
    sig_newEpochInData = pyqtSignal(name="sig_newEpochInData")
    sig_axisActivated = pyqtSignal(int, name="sig_axisActivated")
    
    closeMe  = pyqtSignal(int)
    frameChanged = pyqtSignal(int)
    
    # TODO: 2019-11-01 22:43:50
    # implement viewing for all these
    supported_types = (neo.Block, neo.Segment, 
                       neo.AnalogSignal, DataSignal, 
                       neo.IrregularlySampledSignal,
                       IrregularlySampledDataSignal,
                       neo.SpikeTrain, 
                       neo.Event,
                       neo.Epoch, 
                       neo.core.baseneo.BaseNeo,
                       TriggerEvent,
                       TriggerProtocol,
                       vigra.filters.Kernel1D, 
                       pq.Quantity,
                       np.ndarray,
                       tuple, list)
    
    view_action_name = "Signal"
        
    defaultCursorWindowSizeX = 0.001
    defaultCursorWindowSizeY = 0.001
    
    defaultCursorLabelPrecision = SignalCursor.default_precision
    
    defaultCursorsShowValue = False

    mpl_prop_cycle = plt.rcParams['axes.prop_cycle']
    
    defaultLineColorsList = ["#000000"] + ["blue", "red", "green", "cyan", "magenta", "yellow"]  + mpl_prop_cycle.by_key()['color']
    #defaultLineColorsList = ["#000000"] + list((QtGui.QColor(c).name(QtGui.QColor.HexArgb) for c in ("blue", "red", "green", "cyan", "magenta", "yellow")))  + mpl_prop_cycle.by_key()['color']
    
    defaultOverlaidLineColorList = (mpl.colors.rgb2hex(mpl.colors.to_rgba(c, alpha=0.5)) for c in defaultLineColorsList)
        
    defaultSpikeColor    = mpl.colors.rgb2hex(mpl.colors.to_rgba("xkcd:navy"))
    defaultEventColor    = mpl.colors.rgb2hex(mpl.colors.to_rgba("xkcd:crimson"))
    defaultEpochColor    = mpl.colors.rgb2hex(mpl.colors.to_rgba("xkcd:coral"))
    
    default_antialias = True
    
    defaultCursorColors = Bunch({"crosshair":"#C173B088", "horizontal":"#B1D28F88", "vertical":"#ff007f88"})
    defaultLinkedCursorColors = Bunch({"crosshair":QtGui.QColor(defaultCursorColors["crosshair"]).darker().name(QtGui.QColor.HexArgb),
                                       "horizontal":QtGui.QColor(defaultCursorColors["horizontal"]).darker().name(QtGui.QColor.HexArgb),
                                       "vertical":QtGui.QColor(defaultCursorColors["vertical"]).darker().name(QtGui.QColor.HexArgb)})
    
    defaultCursorHoverColor = "red"

    def __init__(self, x: (neo.core.baseneo.BaseNeo, DataSignal, IrregularlySampledDataSignal, TriggerEvent, TriggerProtocol, vigra.filters.Kernel1D, np.ndarray, tuple, list, type(None)) = None, y: (neo.core.baseneo.BaseNeo, DataSignal, IrregularlySampledDataSignal, TriggerEvent, TriggerProtocol, vigra.filters.Kernel1D, np.ndarray, tuple, list, type(None)) = None, parent: (QtWidgets.QMainWindow, type(None)) = None, ID:(int, type(None)) = None, win_title: (str, type(None)) = None, doc_title: (str, type(None)) = None, frameIndex:(int, tuple, list, range, slice, type(None)) = None, frameAxis:(int, type(None)) = None, signalIndex:(str, int, tuple, list, range, slice, type(None)) = None, signalChannelAxis:(int, type(None)) = None, signalChannelIndex:(int, tuple, list, range, slice, type(None)) = None, irregularSignalIndex:(str, int, tuple, list, range, slice, type(None)) = None, irregularSignalChannelAxis:(int, type(None)) = None, irregularSignalChannelIndex:(int, tuple, list, range, slice, type(None)) = None, separateSignalChannels:bool = False, interval:(tuple, list) = None, channelIndex:object = None, currentFrame:(int, type(None)) = None, plotStyle: str = "plot", *args, **kwargs):
        """SignalViewer constructor.
        """
        super(QMainWindow, self).__init__(parent)
        
        # define these early
        self.xData = None
        self.yData = None
        
        #self.threadpool = QtCore.QThreadPool()
        
        self._plot_names_ = dict() # maps item row position to name
        
        self._cursorWindowSizeX_ = self.defaultCursorWindowSizeX
        self._cursorWindowSizeY_ = self.defaultCursorWindowSizeY
        
        self.crosshairSignalCursors = dict() # a dict of SignalCursors mapping str name to cursor object
        self.verticalSignalCursors = dict()
        self.horizontalSignalCursors = dict()
        self._cursorHoverColor_ = self.defaultCursorHoverColor
        self._data_cursors_ = collections.ChainMap(self.crosshairSignalCursors, self.horizontalSignalCursors, self.verticalSignalCursors)
        # maps signal name with list of cursors
        # NOTE: 2019-03-08 13:20:50
        # map plot item index (int) with list of cursors
        self._cached_cursors_ = dict()
        
        self._target_overlays_ = dict()
        
        self._label_overlays_ = dict()
        
        # NOTE: 2017-05-10 22:57:30
        # these are linked cursors in the same window
        self.linkedCrosshairCursors = []
        self.linkedHorizontalCursors = []
        self.linkedVerticalCursors = []
        
        #### BEGIN data layout attributes
        # see _set_data_ for their use
        # NOTE: self._number_of_frames_ is defined in ScipyenFrameViewer
        self.frameAxis = None
        #self._frameIndex_ = None
        
        # data axis for numpy arrays - ionly used to plot numpy arrays
        self.dataAxis = None
        
        # index into neo.ChannelIndex objects (if any)
        # ATTENTION: 2019-11-21 21:42:29
        # ATTENTION 2021-10-03 12:54:13
        # neo.ChanelIndex is deprecated in 0.9.0 and out in 0.10.0
        # NOT to be confused with signal data channels, see NOTE: 2019-11-21 21:40:38
        #self.channelIndex = None
        
        # if given, specifies which regularly sampled signals to plot; it may be
        # overrridden by self.channelIndex when self.channelIndex is a neo.ChannelIndex
        self.signalIndex = None
        
        # NOTE: 2019-11-21 21:40:38
        # signalChannel* and irregularSignalChannel* attributes refer to actual 
        # signal data "channels" i.e. 1D slice view of the data array; 
        # ATTENTION: 2019-11-21 21:41:48
        # NOT to be confused with neo.ChannelIndex objects!
        # if given, specifies which axis defined the "channel" axis
        self.signalChannelAxis = None
        self.signalChannelIndex = None
        
        self.irregularSignalIndex = None
        self.irregularSignalChannelAxis = None
        self.irregularSignalChannelIndex = None
        
        #### END  data layout attributes
        
        #### BEGIN attributes controlling neo object representations
        
        #### BEGIN metadata for neo and datatypes objects
        self.dataAnnotations = dict()
        self.globalAnnotations = None
        self.currentFrameAnnotations = None
        self.currentSignalAnnotations = None
        #self.nonSignalAnnotations = None
        #### END metadata for neo and datatypes objects
        
        #### BEGIN selective representation of neo objects components
        
        # NOTE: 2020-03-09 13:56:32 self._cached_epochs_
        # needed for replotting neo.Epoch/DataZone object after rescaling the 
        # axis; 
        # maps frame index to a list of neo.Epochs
        # frames without epochs are absent from the map
        self._cached_epochs_ = dict()
        self._plotted_analogsignal_index = list() # which analog signals do we actually plot?
        self._plotted_irregularsignal_index = list() # which irregular signals do we actually plot?

        #### END selective representation of neo objects components
        
        #### BEGIN options for neo objects
        self.plotSpikesAsEvents   = False
        self.plotEventsAsSpikes   = False
        self.plotEpochsAsEvents   = False
        self._overlay_spikes_events_epochs_ = True
        self.epoch_plot_options = dict()
        # NOTE: 2019-04-28 18:03:20
        # contrary to online documentation for pyqtgraph 0.10.0, the source code
        # indicates that LinearRegionItem constructor only accepts "brush";
        # "pen" must be delivered direcly to the LinearRegionItem's lines (the
        # item's "lines" attribute)
        # also, there is no mention of "hoverBrush" or "hoverPen" anywhere in the
        # source code for LinearRegionItem or its superclass UIGraphicsItem
        # in fact, hovering just modifes the brush by doubling its alpha value
        self.epoch_plot_options["epoch_pen"] = None 
        self.epoch_plot_options["epoch_brush"] = None
        
        # for future use, maybe (see NOTE: 2019-04-28 18:03:20)
        self.epoch_plot_options["epoch_hoverPen"] = None
        self.epoch_plot_options["epoch_hoverBrush"] = None
        
        self.epoch_plot_options["epochs_color_set"] = [(255, 0, 0, 50),
                                                       (0, 255, 0, 50),
                                                       (0, 0, 255, 50),
                                                       (255, 255, 0, 50),
                                                       (255, 0, 255, 50),
                                                       (0, 255, 255, 50)]
        
        #self.train_plot_options = dict()
        
        # NOTE: 2019-04-28 18:03:20
        # contrary to online documentation for pyqtgraph 0.10.0, the source code
        # indicates that LinearRegionItem constructor only accepts "brush";
        # "pen" must be delivered direcly to the LinearRegionItem's lines (the
        # item's "lines" attribute)
        # also, there is no mention of "hoverBrush" or "hoverPen" anywhere in the
        # source code for LinearRegionItem or its superclass UIGraphicsItem
        # in fact, hovering just modifes the brush by doubling its alpha value
        #self.train_plot_options["train_pen"] = None 
        #self.train_plot_options["train_brush"] = None
        
        ## for future use, maybe (see NOTE: 2019-04-28 18:03:20)
        #self.train_plot_options["train_hoverPen"] = None
        #self.train_plot_options["train_hoverBrush"] = None
        
        #self.train_plot_options["trains_color_set"] = [(255, 0, 0, 50),
                                                       #(0, 255, 0, 50),
                                                       #(0, 0, 255, 50),
                                                       #(255, 255, 0, 50),
                                                       #(255, 0, 255, 50),
                                                       #(0, 255, 255, 50)]
        
        #### BEGIN GUI signal selectors and options for compound neo objects
        #self.guiSelectedSignals = list() # signal indices in collection
        
        # list of analog signal names selected from what is available in the current 
        # frame, using the combobox for analog signals
        # this includes signals in numpy arrays
        self.guiSelectedSignalNames = list() # list of signal names sl
        
        #self.guiSelectedIrregularSignals = list() # signal indices in collection
        # list of irregularly sampled signal names selected from what is available
        # in the current frame, using the combobox for irregularly sampled signals
        self.guiSelectedIrregularSignalNames = list()
        
        self._plot_analogsignals_ = True
        self._plot_irregularsignals_ = True
        #### END GUI signal selectors and options for compound neo objects
        #### END options for neo objects
        #### END attributes controlling neo object representations
        
        # NOTE: 2021-01-07 14:52:44 
        # Defined in ScipyenFrameViewer and set to 0 (zero) by default
        #self._current_frame_index_ = 0
        
        #### BEGIN interval plotting
        self.plot_start = None
        self.plot_stop = None
        #### END interval plotting
        
        #### BEGIN plot items management
        self._focussed_plot_item_ = None
        self._current_plot_item_ = None
        self._current_plot_item_index_ = -1
        #### END plot items management
        
        self._mouse_coordinates_text_ = ""
        self._cursor_coordinates_text_  = ""
        
        #### BEGIN generic plot options
        #self.default_antialias = True
        
        self.antialias = self.default_antialias
        
        self.default_axis_tick_font = None
        
        self.axis_tick_font = self.default_axis_tick_font
        
        self.selectedDataCursor = None
        
        self._cursorColors_ = self.defaultCursorColors
        self._linkedCursorColors_ = self.defaultLinkedCursorColors
        self._cursorLabelPrecision_ = self.defaultCursorLabelPrecision
        self._cursorsShowValue_ = self.defaultCursorsShowValue
        #### END generic plot options
        
        # NOTE: 2021-08-25 09:42:54
        # ScipyenFrameViewer initialization - also does the following:
        # 1) calls self._configureUI_() overridden here:
        #   1.1) sets up the UI defined in the .ui file (setupUi)
        #
        # 3) calls self.loadSettings inherited from 
        # ScipyenViewer <- WorkspaceGuiMixin <- ScipyenConfigurable
        
        # NOTE: 2022-01-17 11:48:04
        # call super().__init__ with data set to None explicitly; this will 
        # initialize the ancestors but will avoid calling super().setData(...)
        # We then call self.setData(...) below, tailored for SignalViewer.
        super().__init__(data=None, parent=parent, ID=ID, win_title=win_title, 
                         doc_title=doc_title, *args, **kwargs)
        
        self.observed_vars = DataBag(allow_none=True, mutable_types=True)
        
        self.observed_vars.verbose = True
        self.observed_vars.observe(self.var_observer)
        
        if isinstance(y, self.supported_types) or any([t in type(y).mro() for t in self.supported_types]):
            self.setData(x, y, frameIndex=frameIndex, 
                            frameAxis=frameAxis, signalIndex=signalIndex,
                            signalChannelAxis=signalChannelAxis,
                            signalChannelIndex=signalChannelIndex,
                            irregularSignalIndex=irregularSignalIndex,
                            irregularSignalChannelAxis = irregularSignalChannelAxis,
                            irregularSignalChannelIndex = irregularSignalChannelIndex,
                            separateSignalChannels = separateSignalChannels,
                            interval = interval,
                            channelIndex = channelIndex,
                            currentFrame = currentFrame,
                            plotStyle = plotStyle,
                            *args, **kwargs)
        
    def _configureUI_(self):
        """
        
        NOTE: 2022-11-21 10:55:41
        Brief description of the organisation of plot axes in the UI (to be completed):
        
        • all plots are contained in a pyqtgraph.GraphicsLayoutWidget which is 
            contained in the generic QWidget self.viewerWidgetContainer
        
        • each "axis" is a pq.PlotItem; some relevant attributes :
            ∘ vb → a pq.ViewBox
        • the axes are contained in 
            ∘ contained in self.signalsLayout - a pg.GraphicsLayout()
            ∘ 
        
        
        FIXME/TODO 2022-11-17 10:00:15
        Move all UI definition to the designer UI file:
        As it currently stands, this is a hotch-potch of widget creations with
        both designer UI and manually added code.
        
        The up side is that the designer UI allows more tractable code and automates
        sharing of actions between widgets (e.g. menus, toolbars, comboboxes)
        
        The down side (especially for toolbars) is that we will have to create 
        some icons of our own (as stock icon themes do not provide everything we 
        need).
        
        See signalviewer_2.ui file which goes some way towards that.
        
        BUG/FIXME/TODO 2022-11-17 10:05:21
        An annoying bug is the disappearance of the menubar and its menus) when
        the window is closed and then shown again (the underlying objectis still
        alive) in the KDE desktop, when KDE operates the global menu service.
        
        """
        self.setupUi(self)
        
        # NOTE: 2021-11-13 23:24:12
        # signal/slot connections & UI for pg.PlotItem objects are configured in
        # self._prepareAxes_()
        
        self.sig_plot.connect(self._slot_plot_numeric_data_thr_, type = QtCore.Qt.QueuedConnection)
        
        if self.viewerWidgetContainer.layout() is None:
            self.viewerWidgetContainer.setLayout(QtWidgets.QGridLayout(self.viewerWidgetContainer))
            
        self.viewerWidgetContainer.layout().setSpacing(0)
        self.viewerWidgetContainer.layout().setContentsMargins(0,0,0,0)
        
        self.actionSVG.triggered.connect(self.slot_export_svg)
        self.actionTIFF.triggered.connect(self.slot_export_tiff)
        self.actionPNG.triggered.connect(self.slot_export_png)
        
        self.cursorsMenu = QtWidgets.QMenu("Cursors", self)
        self.epochsMenu = QtWidgets.QMenu("Epochs", self)
        
        # self.menubar.setNativeMenuBar(True)

        self.menubar.addMenu(self.cursorsMenu)
        self.menubar.addMenu(self.epochsMenu)
        
        self.addCursorsMenu = QtWidgets.QMenu("Add Cursors", self)
        self.addMultiAxesCursorMenu = QtWidgets.QMenu("Multi-axis", self)
        
        self.cursorsMenu.addMenu(self.addCursorsMenu)
        
        self.addCursorsMenu.addMenu(self.addMultiAxesCursorMenu)
        
        self.addVerticalCursorAction = self.addCursorsMenu.addAction("Vertical")
        self.addVerticalCursorAction.triggered.connect(self.slot_addVerticalCursor)
        
        self.addHorizontalCursorAction = self.addCursorsMenu.addAction("Horizontal")
        self.addHorizontalCursorAction.triggered.connect(self.slot_addHorizontalCursor)
        
        self.addCrosshairCursorAction = self.addCursorsMenu.addAction("Crosshair")
        self.addCrosshairCursorAction.triggered.connect(self.slot_addCrosshairCursor)
        
        self.addCursorsMenu.addSeparator()
        
        self.addDynamicVerticalCursorAction = self.addCursorsMenu.addAction("Dynamic Vertical")
        self.addDynamicVerticalCursorAction.triggered.connect(self.slot_addDynamicVerticalCursor)
        
        self.addDynamicHorizontalCursorAction = self.addCursorsMenu.addAction("Dynamic Horizontal")
        self.addDynamicHorizontalCursorAction.triggered.connect(self.slot_addDynamicHorizontalCursor)
        
        self.addDynamicCrosshairCursorAction = self.addCursorsMenu.addAction("Dynamic Crosshair")
        self.addDynamicCrosshairCursorAction.triggered.connect(self.slot_addDynamicCrosshairCursor)
        
        self.addMultiAxisVCursorAction = self.addMultiAxesCursorMenu.addAction("Vertical")
        self.addMultiAxisVCursorAction.triggered.connect(self.slot_addMultiAxisVerticalCursor)
        
        self.addMultiAxisCCursorAction = self.addMultiAxesCursorMenu.addAction("Crosshair")
        self.addMultiAxisCCursorAction.triggered.connect(self.slot_addMultiAxisCrosshairCursor)
        
        self.addMultiAxesCursorMenu.addSeparator()
        
        self.addDynamicMultiAxisVCursorAction = self.addMultiAxesCursorMenu.addAction("Dynamic Vertical")
        self.addDynamicMultiAxisVCursorAction.triggered.connect(self.slot_addDynamicMultiAxisVerticalCursor)
        
        self.addDynamicMultiAxisCCursorAction = self.addMultiAxesCursorMenu.addAction("Dynamic Crosshair")
        self.addDynamicMultiAxisCCursorAction.triggered.connect(self.slot_addDynamicMultiAxisCrosshairCursor)
        
        self.editCursorsMenu = QtWidgets.QMenu("Edit Cursor", self)
        
        self.editAnyCursorAction = self.editCursorsMenu.addAction("Choose...")
        self.editAnyCursorAction.triggered.connect(self.slot_editCursor)
        
        self.editCursorAction = self.editCursorsMenu.addAction("Selected...")
        self.editCursorAction.triggered.connect(self.slot_editSelectedCursor)
        
        self.cursorsMenu.addMenu(self.editCursorsMenu)
        
        self.removeCursorsMenu = QtWidgets.QMenu("Remove cursors", self)
        
        self.removeCursorAction = self.removeCursorsMenu.addAction("Remove a cursor...")
        self.removeCursorAction.triggered.connect(self.slot_removeCursor)
        
        self.removeSelectedCursorAction = self.removeCursorsMenu.addAction("Remove selected cursor")
        self.removeSelectedCursorAction.triggered.connect(self.slot_removeSelectedCursor)
        
        self.removeAllCursorsAction = self.removeCursorsMenu.addAction("Remove all cursors")
        self.removeAllCursorsAction.triggered.connect(self.slot_removeCursors)
        
        self.cursorsMenu.addMenu(self.removeCursorsMenu)
        
        self.cursorsMenu.addSeparator()
        
        self.setCursorsShowValue = self.cursorsMenu.addAction("Cursors show value")
        self.setCursorsShowValue.setCheckable(True)
        self.setCursorsShowValue.setChecked(self._cursorsShowValue_)
        self.setCursorsShowValue.toggled.connect(self._slot_setCursorsShowValue)
        
        self.setCursorsLabelPrecision = self.cursorsMenu.addAction("Cursor label precision...")
        self.setCursorsLabelPrecision.triggered.connect(self._slot_setCursorLabelPrecision)
        
        self.cursorsColorsMenu = QtWidgets.QMenu("Cursor colors")
        self.verticalCursorColorsAction = self.cursorsColorsMenu.addAction("Vertical cursor colors")
        self.verticalCursorColorsAction.triggered.connect(self._slot_setVerticalCursorColors)
        self.horizontalCursorColorsAction = self.cursorsColorsMenu.addAction("Horizontal cursor colors")
        self.horizontalCursorColorsAction.triggered.connect(self._slot_setHorizontalCursorColors)
        self.crosshairCursorColorsAction = self.cursorsColorsMenu.addAction("Crosshair cursor colors")
        self.crosshairCursorColorsAction.triggered.connect(self._slot_setCrosshairCursorColors)
        self.cursorHoverColorAction = self.cursorsColorsMenu.addAction("Cursors hover color")
        self.cursorHoverColorAction.triggered.connect(self._slot_setCursorHoverColor)
        
        self.cursorsMenu.addMenu(self.cursorsColorsMenu)
        
        self.makeEpochsMenu = QtWidgets.QMenu("Make Epochs")
        
        self.epochsFromCursorsAction = self.makeEpochsMenu.addAction("From Cursors")
        self.epochsFromCursorsAction.triggered.connect(self.slot_cursorsToEpoch)
        self.epochsFromCursorsAction.setEnabled(self._scipyenWindow_ is not None)
        
        self.epochFromSelectedCursorAction = self.makeEpochsMenu.addAction("Selected SignalCursor to Epoch")
        self.epochFromSelectedCursorAction.triggered.connect(self.slot_cursorToEpoch)
        self.epochFromSelectedCursorAction.setEnabled(self._scipyenWindow_ is not None)
        
        self.epochBetweenCursorsAction = self.makeEpochsMenu.addAction("Epoch Between Two Cursors")
        self.epochBetweenCursorsAction.triggered.connect(self.slot_epochBetweenCursors)
        self.epochBetweenCursorsAction.setEnabled(self._scipyenWindow_ is not None)
        
        self.makeEpochsInDataMenu = QtWidgets.QMenu("Make Epochs in Data")
        
        self.epochsInDataFromCursorsAction = self.makeEpochsInDataMenu.addAction("From Cursors")
        self.epochsInDataFromCursorsAction.triggered.connect(self.slot_cursorsToEpochInData)
        
        self.epochInDataFromSelectedCursorAction = self.makeEpochsInDataMenu.addAction("From Selected SignalCursor")
        self.epochInDataFromSelectedCursorAction.triggered.connect(self.slot_cursorToEpochInData)
        
        self.epochInDataBetweenCursors = self.makeEpochsInDataMenu.addAction("Between Two Cursors")
        self.epochInDataBetweenCursors.triggered.connect(self.slot_epochInDataBetweenCursors)
        
        # self.cursorsMenu.addSeparator()
        
        self.epochsMenu.addMenu(self.makeEpochsMenu)
        self.epochsMenu.addMenu(self.makeEpochsInDataMenu)
        
        # the actual layout of the plot items (pyqtgraph framework)
        self.signalsLayout = pg.GraphicsLayout()
        self.signalsLayout.layout.setVerticalSpacing(0)

        self.fig = pg.GraphicsLayoutWidget(parent = self.viewerWidgetContainer) 
        styleHint = QtWidgets.QStyle.SH_DitherDisabledText
        self.fig.style().styleHint(styleHint)
        
        #self.viewerWidgetLayout.addWidget(self.fig)
        self.viewerWidget = self.fig
        self.viewerWidgetContainer.layout().setHorizontalSpacing(0)
        self.viewerWidgetContainer.layout().setVerticalSpacing(0)
        self.viewerWidgetContainer.layout().contentsMargins().setLeft(0)
        self.viewerWidgetContainer.layout().contentsMargins().setRight(0)
        self.viewerWidgetContainer.layout().contentsMargins().setTop(0)
        self.viewerWidgetContainer.layout().contentsMargins().setBottom(0)
        self.viewerWidgetContainer.layout().addWidget(self.viewerWidget, 0,0)
    
        self.mainLayout = self.fig.ci
        self.mainLayout.layout.setVerticalSpacing(0)
        self.mainLayout.layout.setHorizontalSpacing(0)
        
        self.plotTitleLabel = self.mainLayout.addLabel("", col=0, colspan=1)
        
        self.mainLayout.nextRow()
        self.mainLayout.addItem(self.signalsLayout)
        
        self.framesQSlider.setMinimum(0)
        self.framesQSlider.setMaximum(0)
        self.framesQSlider.valueChanged.connect(self.slot_setFrameNumber)
        
        self._frames_slider_ = self.framesQSlider
        
        self.framesQSpinBox.setKeyboardTracking(False)
        self.framesQSpinBox.setMinimum(0)
        self.framesQSpinBox.setMaximum(0)
        self.framesQSpinBox.valueChanged.connect(self.slot_setFrameNumber)
        
        self._frames_spinner_ = self.framesQSpinBox
        
        # FIXME/TODO? 2022-11-17 09:59:51
        # what's this for?
        # self.signalsMenu = QtWidgets.QMenu("Signals", self)
        
        self.selectSignalComboBox.clear()
        self.selectSignalComboBox.setCurrentIndex(0)
        self.selectSignalComboBox.currentIndexChanged[int].connect(self.slot_analogSignalsComboBoxIndexChanged)
        
        self.plotAnalogSignalsCheckBox.setCheckState(QtCore.Qt.Checked)
        self.plotAnalogSignalsCheckBox.stateChanged[int].connect(self.slot_plotAnalogSignalsCheckStateChanged)
        
        self.selectIrregularSignalComboBox.clear()
        self.selectIrregularSignalComboBox.setCurrentIndex(0)
        self.selectIrregularSignalComboBox.currentIndexChanged[int].connect(self.slot_irregularSignalsComboBoxIndexChanged)
        
        self.plotIrregularSignalsCheckBox.setCheckState(QtCore.Qt.Checked)
        self.plotIrregularSignalsCheckBox.stateChanged[int].connect(self.slot_plotIrregularSignalsCheckStateChanged)
        
        #### BEGIN set up annotations dock widget
        #print("_configureUI_ sets up annotations dock widget")
        self.annotationsDockWidget = QtWidgets.QDockWidget("Annotations", self, objectName="annotationsDockWidget")
        self.annotationsDockWidget.setWindowTitle("Annotations")
        self.annotationsDockWidget.setFeatures(QtWidgets.QDockWidget.DockWidgetClosable | QtWidgets.QDockWidget.DockWidgetMovable | QtWidgets.QDockWidget.DockWidgetFloatable)
        
        self.annotationsViewer = InteractiveTreeWidget(self.annotationsDockWidget)
        self.annotationsViewer.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.annotationsViewer.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        self.annotationsViewer.setDragEnabled(True)
        
        # NOTE: 2022-03-04 10:14:09 FIXME/TODO code to actually export to workspace
        # items selected in the annotations viewer
        #self.annotationsViewer.customContextMenuRequested[QtCore.QPoint].connect(self.slot_annotationsContextMenuRequested)
        
        self.annotationsDockWidget.setWidget(self.annotationsViewer)
        
        #print("_configureUI_ sets up annotations dock widget action")
        #### END set up annotations dock widget
        
        #### BEGIN set up coordinates dock widget
        #print("_configureUI_ sets up coordinates dock widget")
        self.coordinatesDockWidget.setWindowTitle("Cursors")
        
        #print("_configureUI_ sets up coordinates dock widget action")
        
        #self.coordinatesDockWidget.visibilityChanged[bool].connect(self._slot_dock_visibility_changed_)
        #### END set up coordinates dock widget
        
        #print("_configureUI_ sets up dock widget actions menu")
        self.docksMenu = QtWidgets.QMenu("Panels", self)
        
        self.showAnnotationsDockWidgetAction = self.docksMenu.addAction("Annotations")
        self.showAnnotationsDockWidgetAction.setObjectName("action_%s" % self.annotationsDockWidget.objectName())
        self.showAnnotationsDockWidgetAction.triggered.connect(self.slot_showAnnotationsDock)
        
        self.showCoordinatesDockWidgetAction = self.docksMenu.addAction("Cursors")
        self.showCoordinatesDockWidgetAction.setObjectName("action_%s" % self.coordinatesDockWidget.objectName())
        self.showCoordinatesDockWidgetAction.triggered.connect(self.slot_showCoordinatesDock)
        
        self.menubar.addMenu(self.docksMenu)
        
        self.actionDetect_Triggers.triggered.connect(self.slot_detectTriggers)
        self.actionDetect_Triggers.setEnabled(False)
        
        self.actionRefresh.triggered.connect(self.slot_refreshDataDisplay)
        
        self.actionData_to_workspace.setIcon(QtGui.QIcon.fromTheme("document-export"))
        self.actionData_to_workspace.triggered.connect(self.slot_exportDataToWorkspace)
        
    # ### BEGIN properties
    @property
    def dockWidgets(self):
        return dict(((name, w) for name, w in self.__dict__.items() if isinstance(w, QtWidgets.QDockWidget)))
        
    @property
    def visibleDocks(self):
        return dict(((name, w.isVisible()) for name, w in self.__dict__.items() if isinstance(w, QtWidgets.QDockWidget)))
    
    @markConfigurable("VisibleDocks", "qt")
    @visibleDocks.setter
    def visibleDocks(self, val):
        if isinstance(val, dict):
            dw = self.dockWidgets
            for k, v in val.items():
                if k in dw:
                    dw[k].setVisible(v is True) # just to make sure v is a bool
                    
    @property
    def cursorLabelPrecision(self):
        return self._cursorLabelPrecision_
    
    @markConfigurable("CursorLabelPrecision")
    @cursorLabelPrecision.setter
    def cursorLabelPrecision(self, val:typing.Union[int, str]):
        if isinstance(val, str) and val=="auto":
            pi_precisions = [self.get_axis_xData_precision(ax) for ax in self.plotItems]
            val = min(pi_precisions)
        
        if not isinstance(val, int) or val < 0:
            val = self.defaultCursorLabelPrecision
            
        self._cursorLabelPrecision_ = int(val)
        
        for c in self.cursors:
            c.precision = self._cursorLabelPrecision_
            
        if isinstance(getattr(self, "configurable_traits", None), DataBag):
            self.configurable_traits["CursorLabelPrecision"] = self._cursorLabelPrecision_
            
    @property
    def cursorsShowValue(self):
        return self._cursorsShowValue_
    
    @markConfigurable("CursorsShowValue")
    @cursorsShowValue.setter
    def cursorsShowValue(self, val):
        self._cursorsShowValue_ = val == True
        signal_blocker = QtCore.QSignalBlocker(self.setCursorsShowValue)
        self.setCursorsShowValue.setChecked(self._cursorsShowValue_)
        for c in self.cursors:
            c.setShowValue(self._cursorsShowValue_, self._cursorLabelPrecision_)
            
        if isinstance(getattr(self, "configurable_traits", None), DataBag):
            self.configurable_traits["CursorsShowValue"] = self._cursorsShowValue_
            
    @property
    def cursorWindowSizeX(self):
        return self._cursorWindowSizeX_
    
    @markConfigurable("CursorXWindow")
    @cursorWindowSizeX.setter
    def cursorWindowSizeX(self, val):
        self._cursorWindowSizeX_ = val
        for c in self.cursors:
            c.xwindow = val
        if isinstance(getattr(self, "configurable_traits", None), DataBag):
            self.configurable_traits["CursorXWindow"] = self._cursorWindowSizeX_
            
    @property
    def cursorWindowSizeY(self):
        return self._cursorWindowSizeY_
    
    @markConfigurable("CursorYWindow")
    @cursorWindowSizeY.setter
    def cursorWindowSizeY(self, val):
        self._cursorWindowSizeY_ = val
        for c in self.cursors:
            c.ywindow = val
        if isinstance(getattr(self, "configurable_traits", None), DataBag):
            self.configurable_traits["CursorYWindow"] = self._cursorWindowSizeY_
            
    @property
    def cursorColors(self):
        return self._cursorColors_
    
    @cursorColors.setter
    def cursorColors(self, val:dict):
        if isinstance(val, dict) and all((s in val for s in ("crosshair", "horizontal", "vertical"))):
            self.crosshairCursorColor = QtGui.QColor(val["crosshair"]).name(QtGui.QColor.HexArgb)
            self.horizontalCursorColor = QtGui.QColor(val["horizontal"]).name(QtGui.QColor.HexArgb)
            self.verticalCursorColor = QtGui.QColor(val["vertical"]).name(QtGui.QColor.HexArgb)

    @property
    def crosshairCursorColor(self):
        return self._cursorColors_["crosshair"]
    
    @markConfigurable("CrosshairCursorColor", trait_notifier=True)
    @crosshairCursorColor.setter
    def crosshairCursorColor(self, val:str):
        self._set_cursors_color(val, "crosshair")
                
    @property
    def horizontalCursorColor(self):
        return self._cursorColors_["horizontal"]
    
    @markConfigurable("HorizontalCursorColor")
    @horizontalCursorColor.setter
    def horizontalCursorColor(self, val:str):
        self._set_cursors_color(val, "horizontal")
                
    @property
    def verticalCursorColor(self):
        return self._cursorColors_["vertical"]
    
    @markConfigurable("VerticalCursorColor")
    @verticalCursorColor.setter
    def verticalCursorColor(self, val:str):
        self._set_cursors_color(val, "vertical")
        
    @property
    def linkedCursorColors(self):
        return self._linkedCursorColors_
    
    @linkedCursorColors.setter
    def linkedCursorColors(self, val:dict):
        if isinstance(val, dict) and all((s in val for s in ("crosshair", "horizontal", "vertical"))):
            self.linkedCrosshairCursorColor = QtGui.QColor(val["crosshair"]).name(QtGui.QColor.HexArgb)
            self.linkedHorizontalCursorColor = QtGui.QColor(val["horizontal"]).name(QtGui.QColor.HexArgb)
            self.linkedVerticalCursorColor = QtGui.QColor(val["vertical"]).name(QtGui.QColor.HexArgb)
            
    @property
    def linkedCrosshairCursorColor(self):
        return self._linkedCursorColors_["crosshair"]
    
    @markConfigurable("LinkedCrosshairCursorColor", trait_notifier=True)
    @linkedCrosshairCursorColor.setter
    def linkedCrosshairCursorColor(self, val:str):
        self._set_cursors_color(val, "crosshair", True)
            
    @property
    def linkedHorizontalCursorColor(self):
        return self._linkedCursorColors_["horizontal"]
    
    @markConfigurable("LinkedHorizontalCursorColor", trait_notifier=True)
    @linkedHorizontalCursorColor.setter
    def linkedHorizontalCursorColor(self, val:str):
        self._set_cursors_color(val, "horizontal", True)
    
    @property
    def linkedVerticalCursorColor(self):
        return self._linkedCursorColors_["vertical"]
    
    @markConfigurable("LinkedVerticalCursorColor", trait_notifier=True)
    @linkedVerticalCursorColor.setter
    def linkedVerticalCursorColor(self, val:str):
        self._set_cursors_color(val, "vertical", True)

    @property
    def cursorHoverColor(self):
        return self._cursorHoverColor_
    
    @markConfigurable("CursorHoverColor")
    @cursorHoverColor.setter
    def cursorHoverColor(self, val:str):
        self._set_cursors_color(val, "hover")
        
    # ### END properties
    
    # ### BEGIN private methods
    
    @singledispatchmethod
    @safeWrapper
    def _interpret_signal(self, x, **kwargs):
        raise NotImplementedError(f"Plotting is not implemented for objects of type {type(x).__name__}")
        ret = dict( x = None,
                    y = None,
                    dataAxis = 0,
                    signalChannelAxis = kwargs.get("signalChannelAxis", 1),
                    frameAxis = kwargs.get("frameAxis", None),
                    frameIndex = kwargs.get("frameIndex", None),
                    _data_frames_ = 0,
                    _number_of_frames_ = 0,
                    signalChannelIndex = kwargs.get("signalChannelIndex", None),
                    irregularSignalChannelAxis = kwargs.get("irregularSignalChannelAxis", None),
                    irregularSignalChannelIndex = kwargs.get("irregularSignalChannelIndex", None),
                    separateSignalChannels = kwargs.get("separateSignalChannels", False),
                    signalIndex = kwargs.get("signalIndex", None),
                    irregularSignalIndex = kwargs.get("irregularSignalIndex", None),
                    globalAnnotations = kwargs.get("globalAnnotations", None),
                    )
        
        return ret
        
    
    @_interpret_signal.register(neo.Block)
    def _(self, x:neo.Block, **kwargs):
        #### BEGIN NOTE: 2019-11-21 23:09:52 
        # TODO/FIXME handle self.plot_start and self.plot_start
        # each segment (sweep, or frame) can have a different time domain
        # so when these two are specified it may result in an empty plot!!!
        #### END NOTE: 2019-11-21 23:09:52 
        ret = dict( x = None,
                    y = x,
                    dataAxis = 0,
                    frameAxis = None,
                    frameIndex = normalized_index(len(x.segments), kwargs.get("frameIndex", None)),
                    dataFrames_ = len(x.segments),
                    signalChannelAxis = 1,
                    signalChannelIndex = None,
                    irregularSignalChannelAxis = 1,
                    irregularSignalChannelIndex = None,
                    separateSignalChannels = False,
                    signalIndex = kwargs.get("signalIndex", None),
                    irregularSignalIndex = kwargs.get("irregularSignalIndex", None),
                    globalAnnotations = {type(x).__name__ : x.annotations},
                    )
        ret["_number_of_frames_"] = len(ret["frameIndex"])
        
        return ret
                
    @_interpret_signal.register(neo.Segment)
    def _(self, x:neo.Segment, **kwargs):
        ret = dict( x = None,
                    y = x,
                    dataAxis = 0,
                    frameAxis = None,
                    frameIndex = range(1),
                    _data_frames_ = 1,
                    _number_of_frames_ = 1,
                    signalChannelAxis = 1,
                    signalChannelIndex = None,
                    irregularSignalChannelAxis = 1,
                    irregularSignalChannelIndex = None,
                    separateSignalChannels = False,
                    signalIndex = kwargs.get("signalIndex", None),
                    irregularSignalIndex = kwargs.get("irregularSignalIndex", None),
                    globalAnnotations = {type(x).__name__ : x.annotations},
                    docTitle = None
                    )
        
        return ret
    
    @_interpret_signal.register(neo.core.dataobject.DataObject)
    def _(self, x:neo.core.dataobject.DataObject, **kwargs):
        if isinstance(x, neo.ImageSequence):
            raise NotImplementedError("Cannot plot neo.ImageSequence; use ImageViewer instead")
        ret = dict( x = None,
                    y = x,
                    dataAxis = 0,
                    frameAxis = kwargs.get("frameAxis", None),
                    signalChannelAxis = 1,
                    signalChannelIndex = None,
                    irregularSignalChannelAxis = 1,
                    irregularSignalChannelIndex = None,
                    signalIndex = None,
                    irregularSignalIndex = None,
                    globalAnnotations = {type(x).__name__ : x.annotations},
                    docTitle = None
                    )
        # print("SignalViewer._interpret_signal", type(x))
        if isinstance(x, (neo.core.basesignal.BaseSignal, neo.SpikeTrain, neo.Event, neo.Epoch, DataMark, DataZone)):
            ret["signalChannelAxis"] = 1
            ret["signalChannelIndex"] = normalized_sample_index(x.as_array(), ret["signalChannelAxis"], kwargs.get("signalChannelIndex", None))
        else:
            ret["irregularSignalChannelAxis"] = 1
            ret["irregularSignalChannelIndex"] = normalized_sample_index(x.as_array(), ret["irregularSignalChannelAxis"], kwargs.get("irregularSignalChannelIndex", None))
            
        ret["separateSignalChannels"] = kwargs.get("separateSignalChannels", False)
                    
        if not isinstance(ret["frameAxis"], (int, type(None))):
            raise TypeError("For neo-style signals, frameAxis must be an int or None; got %s instead" % type(ret.frameAxis).__name__)
        
        if ret.frameAxis is None:
            ret["_data_frames_"] = 1
            ret["_number_of_frames_"] = 1
            ret["frameIndex"] = range(ret["_number_of_frames_"])
            
        else:
            if ret["frameAxis"] != (ret["signalChannelAxis"] if isinstance(x, (neo.AnalogSignal, DataSignal)) else ret["irregularSignalChannelAxis"]):
                raise ValueError("For neo-style signals, frame axis and signal channel axis must be identical")
            
            ret["_data_frames_"] = x.as_array().shape[1]
            ret["frameAxis"] = normalized_axis_index(x.as_array(), ret["frameAxis"])
            ret["frameIndex"] = normalized_sample_index(x.as_array(), ret["frameAxis"], kwargs.get("frameIndex", None))
            ret["_number_of_frames_"] = len(ret.frameIndex)
            
        return ret
    
    @_interpret_signal.register(vigra.filters.Kernel1D)
    def _(self, x:vigra.filters.Kernel1D, **kwargs):
        xx, yy = kernel2array(x)
        ret = dict( x = xx,
                    y = yy,
                    dataAxis = 0,
                    signalChannelAxis = 1,
                    frameAxis = None,
                    frameIndex = range(1),
                    _data_frames_ = 0,
                    _number_of_frames_ = 1,
                    signalChannelIndex = kwargs.get("signalChannelIndex", None),
                    irregularSignalChannelAxis = kwargs.get("irregularSignalChannelAxis", None),
                    irregularSignalChannelIndex = kwargs.get("irregularSignalChannelIndex", None),
                    separateSignalChannels = kwargs.get("separateSignalChannels", False),
                    signalIndex = range(1),
                    irregularSignalIndex = None,
                    globalAnnotations = kwargs.get("globalAnnotations", None),
                    )
        
        return ret
    
    @_interpret_signal.register(np.ndarray)
    def _(self, x:np.ndarray, **kwargs):
        if x.ndim > 3:
            raise ValueError('Cannot plot data with more than 3 dimensions')
        
        y = x
        
        x = kwargs.get("x_data", None)
            
        ret = dict()
        ret["globalAnnotations"] = kwargs.get("globalAnnotations", None)
        
        frameAxis = kwargs.get("frameAxis", None)
        frameIndex = kwargs.get("frameIndex", None)
        signalChannelAxis = kwargs.get("signalChannelAxis", None)
        separateSignalChannels = kwargs.get("separateSignalChannels", False)
        
        if y.ndim == 1: # one frame, one channel
            dataAxis = 0 # data as column vectors
            signalChannelAxis = None
            frameAxis = None
            frameIndex = range(1)
            signalChannelIndex = range(1)
            _number_of_frames_ = 1
            dataAxis = 0
            
        elif y.ndim == 2:
            if not isinstance(frameAxis, (int, str, vigra.AxisInfo, type(None))):
                raise TypeError("Frame axis must be None, or an int (vigra arrays also accept str or AxisInfo); got %s instead" % type(frameAxis))
            
            if not isinstance(signalChannelAxis, (int, str, vigra.AxisInfo, type(None))):
                raise TypeError("Signal channel axis must be None, or an int (vigra arrays also accept str or AxisInfo); got %s instead" % type(signalChannelAxis))
            
            if signalChannelAxis is None:
                if isinstance(y, vigra.VigraArray):
                    # this is the only case where we allow for signalChannelAxis
                    # to be omitted from the call parameters (for array with 
                    # at least 2D)
                    if y.channelIndex == y.ndim: # no real channel axis
                        # take columns as signal channels (consider y as
                        # an horizontal vector of column vectors)
                        signalChannelAxis = 1
                    else:
                        signalChannelAxis = y.channelIndex
                else:
                    raise TypeError("signalChannelAxis must be specified when plotting numpy arrays")
                
            else:
                if isinstance(y, vigra.VigraArray):
                    if isinstance(signalChannelAxis, str) and signalChannelAxis.lower().strip() != "c":
                            warnings.warn("Channel axis index is specificed by non-canonical axis key %s" % signalChannelAxis)
                            
                    elif isinstance(signalChannelAxis, vigra.AxisInfo):
                        if signalChannelAxis.key.lower().strip() != "c":
                            warnings.warn("Channel axis index is specificed by non-canonical axis key %s" % signalChannelAxis)
                            
                signalChannelAxis = normalized_axis_index(y, signalChannelAxis)
                
            ret["signalChannelAxis"] = signalChannelAxis
            
            ret["dataAxis"] = 1 if signalChannelAxis == 0 else 0
            
            ret["signalChannelIndex"] = normalized_sample_index(y, signalChannelAxis, signalChannelIndex)
            
            ret["separateSignalChannels"] = separateSignalChannels
            
            if frameAxis is None:
                ret["frameAxis"] = None
                ret["_data_frames_"] = 1
                ret["_number_of_frames_"] = 1
                ret[frameIndex] = range(ret["_number_of_frames_"])
                
                # NOTE: 2019-11-22 12:25:42
                # _plotNumpyArray_() decides whether to plot all channels overlaid in
                # one plotItem, or plot each channel in its own plotItem
                # with plot items stacked in a column in one frame
                    
            else:
                # for 2D arrays, specifying a frameAxis forces the plotting 
                # of one channel per frame
                frameAxis = normalized_axis_index(y, frameAxis)
                
                # NOTE: 2019-11-22 14:24:16
                # for a 2D array it does not make sense to have frameAxis
                # different from signalChannelAxis
                if frameAxis != signalChannelAxis:
                    raise ValueError("For 2D arrays, frame axis index %d must be the same as the channel axis index (%d)" % (frameAxis, signalChannelAxis))
                
                ret["frameAxis"] = frameAxis
                
                ret["frameIndex"] = normalized_sample_index(y, frameAxis, frameIndex)
                
                ret["_number_of_frames_"] = len(["frameIndex"])
                
                # NOTE: displayframe() should now disregard separateSignalChannels
            
        elif y.ndim == 3: 
            # NOTE: 2019-11-22 13:33:27
            # both frameAxis and signalChannelAxis MUST be specified
            #
            if frameAxis is None:
                raise TypeError("For 3D arrays the frame axis must be specified")
            
            if signalChannelAxis is None:
                raise TypeError("for 3D arrays the signal channel axis must be specified")
            
            frameAxis = normalized_axis_index(y, frameAxis)
            signalChannelAxis = normalized_axis_index(y, signalChannelAxis)
            
            if frameAxis  ==  signalChannelAxis:
                raise ValueError("For 3D arrays the index of the frame axis must be different from the index of the signal channel axis")
            
            ret["frameAxis"] = frameAxis
            ret["signalChannelAxis"] = signalChannelAxis
            
            axes = set([k for k in range(y.ndim)])
            
            axes.remove(frameAxis)
            axes.remove(signalChannelAxis)
            
            ret["frameIndex"] = normalized_sample_index(y, frameAxis, frameIndex)
            
            ret["_number_of_frames_"] = len(ret["frameIndex"])

            ret[signalChannelIndex] = normalized_sample_index(y, signalChannelAxis, signalChannelIndex)
            
            ret["dataAxis"] = list(axes)[0]

            # NOTE: 2019-11-22 14:15:46
            # diplayframe() needs to decide whether to plot all channels 
            # in the frame as overlaid curves in one plot item (when 
            # separateSignalChannels is False) or in a column of plot items
            # (when separateSignalChannels is True)
            ret["separateSignalChannels"] = separateSignalChannels
            
        if x is None:
            xx = np.linspace(0, y.shape[ret["dataAxis"]], y.shape[ret["dataAxis"]], 
                            endpoint=False)[:, np.newaxis]
                
            ret["x"] = xx
            
        else:
            if isinstance(x, (tuple, list)):
                if len(x) != y.shape[ret["dataAxis"]]:
                    raise TypeError("The supplied signal domain (x) must have the same size as the data axis %s" % dataAxis)
                
                ret["x"] = np.array(x)
                
            elif isinstance(x, np.ndarray):
                if not is_vector(x):
                    raise TypeError("The supplied signal domain (x) must be a vector")
                
                if len(x) != y.shape[ret["dataAxis"]]:
                    raise TypeError("The supplied signal domain (x) must have the same size as the data axis %s" % dataAxis)
                    
                if is_column_vector(x):
                    ret["x"] = x
                    
                else:
                    ret["x"] = x.T # x left unchanged if 1D
                    
            else:
                raise TypeError("Signal domain (x) must be None, a Python iterable of scalars or a numpy array (vector)")
        
        ret["y"] = y
        
        return ret
    
    def _make_targetItem(self, data:typing.Union[tuple, list, QtCore.QPointF, QtCore.QPoint, pg.Point], **kwargs):
        """Generates a pg.TargetItem
        Parameters:
        ==========
        data: pair of coordinates (in the axis coordinate system), 
            QPointF, QPoint or pg.Point
        
        Var-keyword parameters:
        ======================
        These are passed directly to the pg.TargetItem constructor,
        see pyqtgraph documentation for details
        
        See also https://pyqtgraph.readthedocs.io/en/latest/api_reference/graphicsItems/targetitem.html
        """
        
        return pg.TargetItem(data, **kwargs)
    
    def _clear_lris_(self):
        for k, ax in enumerate(self.axes):
            lris = [i for i in ax.items if isinstance(i, pg.LinearRegionItem)]
            
            if len(lris):
                for l in lris:
                    ax.removeItem(l)
                    
    def _prep_entity_dict_(self, obj, elem_types):
        entities = dict()
        
        if isinstance(obj, elem_types):
            name = getattr(obj, "name", None)
            if isinstance(name, str) and len(name.strip()):
                entities[name] = obj
            else:
                entities[0] = obj
            
        elif hasattr(obj, "__iter__"): # e.g. tuple, list, neo.SpikeTrainList
            if all(isinstance(e, elem_types) for e in obj):
                for k, e in enumerate(obj):
                    name = getattr(e, "name", None)
                    if isinstance(name, str) and len(name.strip()):
                        entities[name] = e
                    else:
                        entities[k] = e
            else:
                raise TypeError(f"Elements of the interable expected to be {elem_types} ")
            
        else:
            raise TypeError(f"Expecting an object of {elem_types} type or an iterable containing such objects; got {tyoe(obj).__name__} instead")
                        
        return entities
    
    @safeWrapper
    def _plot_discrete_entities_(self, /, entities:typing.Union[dict, list], axis:typing.Optional[int]=None, **kwargs):
        """For plotting events and spike trains on their own (separate) axis
        Epochs & DataZones are represented as regions between vertical lines 
        across all axes, and therefore they are not dealt with, here.
        """
        if len(entities) == 0:
            return
        
        try:
            if len(self.axes) == 0:
                self._prepareAxes_(1)
                if axis is None or isinstance(axes, int) and axis != 0:
                    axis = 0
                    
            if not isinstance(axis, int):
                axis = 0 # (by default)
                
            else:
                if axis < 0 or axis >= len(self.axes):
                    raise ValueError(f"Wrong axis index {axis} for {len(self.axes)} axes")
            
            # this is the PlotItem, not the array axis
            entities_axis = self.signalsLayout.getItem(axis, 0)
                
            symbolcolors = cycle(self.defaultLineColorsList)
            symbolPen = QtGui.QPen(QtGui.QColor("black"),1)
            symbolPen.setCosmetic(True)
            
            labelStyle = {"color": "#000000"}
            
            height_interval = 1/len(entities)
            
            if isinstance(entities, dict):
                entities_list  = list(entities.values())
                
            else:
                entities_list = entities
            
            if all(isinstance(v, (neo.Event, DataMark)) for v in entities_list):
                max_len =  max((len(event.times) for event in entities_list))
                xx = [np.full((1,max_len), np.nan) for event in entities_list]
                    
                yy = list()
                
                for k_event, event in enumerate(entities_list):
                    if hasattr(event, "type"):
                        data_name = event.type.name
                        
                    elif hasattr(event, "name"):
                        data_name= event.name
                        
                    else:
                        data_name=" "
                        
                    if isinstance(data_name, str):
                        if data_name == "presynaptic":
                            data_name = "pre"
                            
                        elif data_name == "postsynaptic":
                            data_name = "post"
                            
                        elif data_name == "photostimulation":
                            data_name = "photo"
                            
                        elif "imaging" in data_name:
                            data_name = "img"
                    
                    if len(event.times):
                        xx[k_event][:,:len(event.times)] = np.atleast_2d(event.times)[:]
                        yy.append(np.full(xx[k_event].shape, height_interval * k_event + height_interval/2))
                        
                xx_ = np.concatenate(xx).T
                yy_ = np.concatenate(yy).T
                
                if yy_.shape[1] > 10:
                    self.sig_plot.emit(self._make_sig_plot_dict_(entities_axis,
                                            xx_, yy_,
                                            pen=None,
                                            name=data_name,
                                            symbol="event", 
                                            symbolcolorcycle=symbolcolors))
                else:
                    self._plot_numeric_data_(entities_axis, xx_, yy_,
                                            pen=None, name=data_name,
                                            symbol="event", 
                                            symbolcolorcycle=symbolcolors)
                
                yLabel = "Events"
                # entities_axis.axes["left"]["item"].setPen(None)
                # entities_axis.axes["left"]["item"].setLabel(yLabel, **labelStyle)
                # entities_axis.axes["left"]["item"].setStyle(showValues=False)
                
            elif all(isinstance(v, neo.SpikeTrain) for v in entities_list):
                trains_x_list = list()
                trains_y_list = list()
                
                for k_train, train in enumerate(entities_list):
                    data_name = getattr(train, "name", None)
                    data_name = data_name if isinstance(data_name, str) and len(data_name.strip()) else "%d" % k_train
                    
                    x = train.times.magnitude.flatten() # column vector
                    y = np.full(x.shape, height_interval * k_train + height_interval/2) # column vector
                    
                    trains_x_list.append(x)
                    trains_y_list.append(y)
                    
                    xx_ = np.concatenate(trains_x_list, axis=np.newaxis)
                    yy_ = np.concatenate(trains_y_list, axis=np.newaxis)
                    
                    #print("spiketrains xx_.shape", xx_.shape, "yy_.shape", yy_.shape, "self.dataAxis", self.dataAxis, "self.signalChannelAxis", self.signalChannelAxis)
                    
                    #if yy_.ndim > 1 and yy_.shape[1] > 10:
                    if yy_.ndim > 1 and yy_.shape[self.signalChannelAxis] > 10:
                        self.sig_plot.emit(self._make_sig_plot_dict_(entities_axis, xx_, yy_, symbol="spike",
                                                pen=None, name=data_name,
                                                symbolPen=QtGui.QPen(QtGui.QColor(next(symbolcolors)))))
                    else:
                        self._plot_numeric_data_(entities_axis, xx_, yy_, symbol="spike",
                                                pen=None, name=data_name,
                                                symbolPen=QtGui.QPen(QtGui.QColor(next(symbolcolors))))
                        
                yLabel = "Spike Trains"
                # entities_axis.axes["left"]["item"].setPen(None)
                # entities_axis.axes["left"]["item"].setLabel("Spike Trains", **labelStyle)
                # entities_axis.axes["left"]["item"].setStyle(showValues=False)
                
            elif all(isinstance(v, pg.TargetItem) for v in entities_list):
                self._clear_targets_overlay_(entities_axis)
                for entity in entities_list:
                    if entity not in entities_axis.items:
                        entities_axis.addItem(entity)
                return # job done here; return so we don't exec code further down'
            else:
                return
                
            # NOTE: 2022-11-21 14:15:17
            # this will PREVENT the dispay of Y grid lines (not essential, because
            # the data plotted here has NO mangnitude information, unlike signals)
            entities_axis.axes["left"]["item"].setPen(None)
            entities_axis.axes["left"]["item"].setLabel(yLabel, **labelStyle)
            entities_axis.axes["left"]["item"].setStyle(showValues=False)
            
        except:
            traceback.print_exc()
            
    def _clear_targets_overlay_(self, axis):
        """Removes the targets overlay from this axis
            Cached targets are left in place
        """
        axis, axNdx = self._check_axis_spec_ndx_(axis)
        items = [i for i in axis.items if isinstance(i, pg.TargetItem)]
        for i in items:
            axis.removeItem(i)
            
    def _clear_labels_overlay(self, axis):
        axis, axNdx = self._check_axis_spec_ndx_(axis)
        items = [i for i in axis.items if isinstance(i, pg.TextItem)]
        for i in items:
            axis.removeItem(i)
        
                
            
    def _check_axis_spec_ndx_(self, axis:typing.Optional[typing.Union[int, pg.PlotItem]]=None):
        if axis is None:
            axis = self.currentAxis
            axNdx = self.axes.index(axis)
            
        elif isinstance(axis, int):
            if axis not in range(-len(self.axes), len(self.axes)):
                raise ValueError(f"axis index {axis} ir out of range for {len(self.axes)} axes")
            
            axNdx = axis
            axis = self.axes[axis]
            
        elif isinstance(axis, pg.PlotItem):
            if axis not in self.axes:
                raise ValueError(f"axis {axis} not found in this viewer")
            axNdx = self.axes.index(axis)
            
        else:
            raise TypeError(f"axis expected to be an int or pg.PlotItem; got {type(axis).__name__} instead.")
        
        return axis, axNdx
        
    def _update_annotations_(self, data=None):
        self.dataAnnotations.clear()
        
        if isinstance(self.globalAnnotations, dict):
            self.dataAnnotations.update(self.globalAnnotations)
            
        if isinstance(self.currentFrameAnnotations, dict):
            self.dataAnnotations.update(self.currentFrameAnnotations)
            
        if isinstance(self.currentSignalAnnotations, dict):
            self.dataAnnotations.update(self.currentSignalAnnotations)
            
        if isinstance(data, (tuple, list)):
            self.dataAnnotations = [self.dataAnnotations, data[:]]
            
        elif isinstance(data, dict):
            self.dataAnnotations.update(data)
            
        self.annotationsViewer.setData(self.dataAnnotations)
            
        if self.annotationsViewer.topLevelItemCount() == 1:
            self.annotationsViewer.topLevelItem(0).setText(0, "Data")
        
    def _setup_signal_choosers_(self, analog = None, irregular = None):
        """TODO/FIXME - where's the BUG?'
        """
        from core.utilities import unique
        sigBlock = [QtCore.QSignalBlocker(widget) for widget in (self.selectSignalComboBox, self.selectIrregularSignalComboBox)]
        
        if analog is None or (isinstance(analog, (tuple, list)) and len(analog) == 0):
            self.selectSignalComboBox.clear()
            
        elif isinstance(analog, np.ndarray):
            self.selectSignalComboBox.clear()
            self.selectIrregularSignalComboBox.clear()

        else:
            current_ndx = self.selectSignalComboBox.currentIndex()
            current_txt = self.selectSignalComboBox.currentText()
            
            sig_names = ["All"] +  unique([s.name if hasattr(s, "name") and isinstance(s.name, str) and len(s.name.strip()) else f"Analog signal {k}" for k, s in enumerate(analog)]) + ["Choose"]
            
            if current_txt in sig_names:
                new_ndx = sig_names.index(current_txt)
                #new_txt = current_txt
                
            elif current_ndx < len(sig_names):
                new_ndx = current_ndx
                new_txt = sig_names[new_ndx]
                
            else:
                new_ndx = 0
                
            if new_ndx < 0:
                new_ndx = 0
                
            self.selectSignalComboBox.clear()
            self.selectSignalComboBox.addItems(sig_names)
            self.selectSignalComboBox.setCurrentIndex(new_ndx)
            
        if irregular is None or (isinstance(irregular, (tuple, list)) and len(irregular) == 0):
            self.selectIrregularSignalComboBox.clear()
            
        else:
            current_ndx = self.selectIrregularSignalComboBox.currentIndex()
            current_txt = self.selectIrregularSignalComboBox.currentText()
            
            sig_names = ["All"] +  unique([s.name if isinstance(s.name, str) and len(s.name.strip()) else "Irregularly sampled signal %d" % k for k, s in enumerate(irregular)]) + ["Choose"]
            
            if current_txt in sig_names:
                new_ndx = sig_names.index(current_txt)
                new_txt = current_txt
                
            elif current_ndx < len(sig_names):
                new_ndx = current_ndx
                new_txt = sig_names[new_ndx]
                
            else:
                new_ndx = 0
            
            if new_ndx < 0:
                new_ndx = 0
                
            self.selectIrregularSignalComboBox.clear()
            self.selectIrregularSignalComboBox.addItems(sig_names)
            self.selectIrregularSignalComboBox.setCurrentIndex(new_ndx)
            
        # if all([seq is None or (isinstance(seq, (tuple, list)) and len(seq)==0) for seq in (analog, irregular)]):
        #     return
        

    # ### END private methods
    
    def setDataDisplayEnabled(self, value):
        self.viewerWidget.setEnabled(value is True)
        self.viewerWidget.setVisible(value is True)
        
    def showEvent(self, evt):
        # print(f"{self.__class__.__name__} ({self.winTitle}) showEvent")
        # print(f"{self.__class__.__name__} ({self.winTitle}) menubar visible: {self.menuBar().isVisible()}")
        # for (mname, menu) in (("cursors menu", self.cursorsMenu), 
        #                       ("epochs menu",self.epochsMenu)):
        #     print(f"{mname} is visible: {menu.isVisible()}")
        
        super().showEvent(evt)
        evt.accept()
            
    def overlayTargets(self, *args, axis:typing.Optional[typing.Union[int, pg.PlotItem]]=None, **kwargs):
        """Overlays "target" glyphs on the given axis, for the current frame.
        Targets are also added to an internal cache.
        
        Var-positional parameters (*args):
        ==================================
        A sequence of (x,y) coordinate pairs (numeric scalars) or (x,y, size)
        triplets (where x, y are float scalars in the axis' coordinate system
        and size is an int, default is 10)
        
        Named parameters:
        =================
        axis: int or PlotItem; when an int, this is the index of the axis in 
                the axes collection of the viewer
            This is optional (default is the currently selected axis)
        
        Var-keyword parameters:
        =======================
        Passed directly to PyQtGraph TargetItem constructor, see:
        
        https://pyqtgraph.readthedocs.io/en/latest/api_reference/graphicsItems/targetitem.html
        
        for details.
        """
        if len(args) == 0:
            return
        
        axis, axNdx = self._check_axis_spec_ndx_(axis)
        
        targetItems = [self._make_targetItem(*args, **kwargs)]
        cFrame = self.frameIndex[self.currentFrame]
        
        if cFrame not in self._target_overlays_:
            self._target_overlays_[cFrame] = dict()
            
        self._target_overlays_[cFrame][axNdx] = targetItems
        
        self._plot_discrete_entities_(self._target_overlays_[cFrame][axNdx], axNdx)
        
    def removeTargetsOverlay(self, axis:typing.Optional[typing.Union[int, pg.PlotItem]]=None):
        """Remove targets overlaid in this axis.
        Target objects are also removed from the internal cache
        """
        axis, axNdx = self._check_axis_spec_ndx_(axis)
        cFrame = self.frameIndex[self.currentFrame]
        
        if cFrame in self._target_overlays_:
            if isinstance(self._target_overlays_[cFrame], dict):
                if isinstance(self._target_overlays_[cFrame].get(axNdx, None), (tuple, list)):
                    self._target_overlays_[cFrame][axNdx].clear()
                else:
                    self._target_overlays_[cFrame][axNdx] = list()
                    
        # cal this just in case we have overlays that escaped the cache mechanism
        self._clear_targets_overlay_(axis)
                
    def addLabel(self, text:str, axis:typing.Optional[typing.Union[int, pg.PlotItem]]=None, pos = None, **kwargs):
        """Add a pg.TextItem to the specified axis (pg.PlotItem)
        Parameters:
        ===========
        text: the label contents
        axis: axis index, PlotItem, or None (meaning the label will be added to
                the current axis)
        
        Var-keyword parameters:
        =======================
        Passed directly to pyqtgraph TextItem constructor, see below for details:
        https://pyqtgraph.readthedocs.io/en/latest/api_reference/graphicsItems/textitem.html
        """
        axis, axNdx = self._check_axis_spec_ndx_(axis)
        
        if pos is None:
            pos = pg.Point(0,0)
            
        elif isinstance(pos, (tuple, list)) and len(pos) == 2:
            pos = pg.Point(*pos)
            
        elif isinstance(pos, (QtCore.QPoint, QtCore.QPointF)):
            pos = pg.Point(pos.x(), pos.y())
            
        elif not isinstance(pos, pg.Point):
            raise TypeError(f"pos expected a 2-tuple or number, QPoint, QPointF or pg.Point; got {type(pos).__name__} instead")
        
        textItem = pg.TextItem(text, **kwargs)
        textItem.setPos(pos)
        
        cFrame = self.frameIndex[self.currentFrame]
        
        if cFrame not in self._label_overlays_:
            self._label_overlays_[cFrame] = dict()
            
        self._label_overlays_[cFrame][axNdx] = textItem
        
        axis.addItem(textItem)
        
    def removeLabels(self, axis:typing.Optional[typing.Union[int, pg.PlotItem]]=None):
        """ Removes ALL labels (TextItems) from the given axis
        """
        pass
        
        axis, axNdx = self._check_axis_spec_ndx_(axis)
        cFrame = self.frameIndex[self.currentFrame]
        
        if cFrame in self._label_overlays_:
            if isinstance(self._label_overlays_[cFrame], dict):
                if isinstance(self._label_overlays_[cFrame].get(axNdx, None), (tuple, list)):
                    self._label_overlays_[cFrame][axNdx].clear()
                else:
                    self._label_overlays_[cFrame][axNdx] = list()
                    
        # cal this just in case we have overlays that escaped the cache mechanism
        self._clear_labels_overlay(axis)
                
        
    def closeEvent(self, evt):
        """Override ScipyenViewer.closeEvent.
        Attempt to deal with situations where C/C++ objects are deleted before 
        their wrappers in pyqtgraph
        """
        # TODO/FIXME 2022-11-16 21:37:13
        pgmembers = inspect.getmembers(self, lambda x: isinstance(x, (pg.GraphicsItem, pg.GraphicsView, QtWidgets.QWidget)))
        
        super().closeEvent(evt)
        evt.accept()

    def addCursors(self, cursorType="c", *where, **kwargs):
        """Manually adds a set of cursors to the selected axes in the SignalViewer window.
        
        Requires at least one Axis object, therefore some data must be plotted first.
        
        Parameters:
        ===========
        cursorType : string, one of "c" for crosshair, "v" for vertical, "h" for horizontal cursors
                    -- optional (default is "c")
                    
        where      : comma-separated list or a single sequence of cursor coordinates:
                    for crosshair cursors, the coordinates are given as a two-element tuple
                    for vertical and horizontal cursors, the coordinates are floats
                    and are defined along the horizontal and vertical axis, respectively
                    
        Var-keyword arguments ("name=value" pairs):
        ===========================================
        xwindow = 1D sequence of floats with the horizontal extent of the cursor window
            (for crosshair and vertical cursors); must have as many elements as 
            coordinates supplied in the *where argument
        
        ywindow   = as above, for crosshair and horizontal cursors
        
        labels    = 1D sequence of str for cursor IDs; must have as many
            elements as supplied through the *where argument
        
        axis: int, or str, pyqtgraph.PlotItem, or None (default)
            ∘   When an int this is a valid axis index in the current instance 
                of ScipyenViewer (from top to bottom, 0 -> number of axes - 1)
            
            ∘   When a str, this can only be "all" or "a", meaning that the new 
                cursors will span all axes (multi-axis cursors)
        
            ∘   When None (default) the cursors will be created in the axis that
                is currently selected, or axis 0 is no axis is selected.
        
        NOTE: the display of cursor values is controlled by self.setCursorsShowValue
        check box
        """
        
        def _addCursors_parse_coords_(coords):
            if isinstance(coords, (tuple, list)) and all([isinstance(v, numbers.Number) for v in coords]):
                if len(coords) == 1:
                    if cursorType in ("v", "vertical", "Vertical", 
                                      "c", "crosshair", "Crosshair", 
                                      SignalCursor.SignalCursorTypes.vertical,
                                      SignalCursor.SignalCursorTypes.crosshair):
                        x = coords[0]
                        y = None
                        
                    elif cursorType in ("h", "horizontal", "Horizontal", 
                                        SignalCursor.SignalCursorTypes.horizontal):
                        y = coords[0]
                        x = None
                        
                elif len(coords) == 2:
                    x,y = coords # distribute coordinates to individual values
                
                else:
                    raise ValueError(f"Invalid coordinates specified: {coords}")
                
            elif isinstance(coords, (pq.Quantity, np.ndarray)):
                if coords.size == 1:
                    if cursorType in ("v", "vertical", "Vertical", 
                                      "c", "crosshair", "Crosshair", 
                                      SignalCursor.SignalCursorTypes.vertical,
                                      SignalCursor.SignalCursorTypes.crosshair):
                        if len(coords.shape)==0: # scalar
                            x = coords
                            
                        else:
                            x = coords[0] # array with 1 element
                            
                        y = None
                        
                    elif cursorType in ("h", "horizontal", "Horizontal", 
                                        SignalCursor.SignalCursorTypes.horizontal):
                        if len(coords.shape) == 0: # scalar
                            y = coords
                            
                        else:
                            y = coords[0] # 1-element array
                            
                        x = None
                        
                elif coords.size == 2:
                    x,y = coords # distribute to individual values
                    
                else:
                    raise ValueError(f"Invalid coordinates specified: {coords}")
                        
            elif isinstance(coords, numbers.Number):
                if cursorType in ("v", "vertical", "Vertical", 
                                  "c", "crosshair", "Crosshair", 
                                  SignalCursor.SignalCursorTypes.vertical,
                                  SignalCursor.SignalCursorTypes.crosshair):

                    x = coords
                    y = None
                    
                elif cursorType in ("h", "horizontal", "Horizontal", 
                                    SignalCursor.SignalCursorTypes.horizontal):

                    x = None
                    y = coords
                        
                
            else:
                raise ValueError(f"Invalid coordinates specification: {coords}")
            
            return x,y
        
        
        def _use_coords_sequence_(seq, xw, yw, lbls, ax):
            """Adds cursors based on a sequence of cursor coordinates
            """
            for (k, coords) in enumerate(seq):
                x, y = _addCursors_parse_coords_(coords)
            
                if isinstance(xw, (tuple, list, np.ndarray)):
                    if len(xw) != len(seq):
                        raise ValueError("number of elements mismatch between xwindow and where")
                    wx = xw[k]
                    
                elif isinstance(xw, numbers.Number):
                    wx = xw
                        
                if isinstance(yw, (tuple, list, np.ndarray)):
                    if len(xw) != len(seq):
                        raise ValueError("number of elements mismatch between ywindow and where")
                    wy = yw[k]
                    
                elif isinstance(yw, numbers.Number):
                    wy = yw
                    
                if isinstance(lbls, (tuple, list)) and all([isinstance(v, str) for v in lbls]):
                    if len(lbls) != len(seq):
                        raise ValueError("number of elements mismatch between labels and where")
                    
                    lbl = lbls[k]
                    
                elif isinstance(lbls, np.ndarray) and "str" in labels.dtype.name:
                    if len(lbls) != len(seq):
                        raise ValueError("number of elements mismatch between labels and where")
                    lbl = lbls[k]
                    
                elif isinstance(lbls, str):
                    lbl = lbls
                    
                if isinstance(ax, (int, pg.PlotItem, str)):
                    self.addCursor(cursorType=cursorType, x=x, y=y, xwindow=wx, ywindow=wy,
                                label=lbl, show_value = self.setCursorsShowValue.isChecked(),
                                axis=ax)
                    
                elif isinstance(ax, (tuple, list)) and all(isinstance(a, (int, pg.PlotItem)) for a in ax):
                    if len(ax) != len(seq):
                        raise ValueError(f"number of axes ({len(ax)}) should be the same as the number of cursors ({len(seq)})")
                    
                    self.addCursor(cursorType=cursorType, x=x, y=y, xwindow=wx, ywindow=wy,
                                label=lbl, show_value = self.setCursorsShowValue.isChecked(),
                                axis=ax[k])

        xwindow = kwargs.pop("xwindow", self.defaultCursorWindowSizeX)
        ywindow = kwargs.pop("ywindow", self.defaultCursorWindowSizeY)
        labels  = kwargs.pop("labels",  None)
        axis    = kwargs.pop("axis",    None)
        
               
        if len(where) == 0: # no coordinates given
            x = y = None
            
        elif len(where) == 1: # a single object passed - figure it out
            if isinstance(where[0], np.ndarray):
                _use_coords_sequence_(where[0], xwindow, ywindow, labels, axis)
                return
                
            x, y = _addCursors_parse_coords_(where[0])
            
        elif isinstance(where, (tuple, list, np.ndarray)):
            _use_coords_sequence_(where, xwindow, ywindow, labels, axis)
            return

        self.addCursor(cursorType=cursorType, x=x, y=y, 
                       xwindow=xwindow, ywindow=ywindow,
                       label=labels, 
                       show_value = self.setCursorsShowValue.isChecked(),
                       axis = axis)
        
    
    def addCursor(self, cursorType: typing.Union[str, SignalCursor.SignalCursorTypes] = "c", x: typing.Optional[numbers.Number] = None, y: typing.Optional[numbers.Number] = None, xwindow: typing.Optional[numbers.Number] = None, ywindow: typing.Optional[numbers.Number] = None, xBounds: typing.Optional[numbers.Number] = None, yBounds: typing.Optional[numbers.Number] = None, label: typing.Optional[typing.Union[int, str, pg.PlotItem]] = None, follows_mouse: bool = False, axis: typing.Optional[int] = None, **kwargs):
        """ Add a cursor to the selected axes in the signal viewer window.

        When no data has been plotted, the cursor is created in the scene.
        
        Arguments:
        cursorType: str, one of "c", "v" or "h" respectively, for 
                    crosshair, vertical or horizontal cursors; default is "c"
                    
        where: None, float (for vertical or horizontal cursors) or 
                    two-element sequence of floats for crosshair cursors
                    when None, the cursor will be placed in the middle of the
                    selected axis
                    
        xwindow: None or float with the horizontal size of the cursor window;
                    this is ignored for horizontal cursors
                    
        ywindow: as xwindow; ignored for vertical cursors
        
        label: None, or a str; is None, the cursor will be assigned an ID 
                    composed of "c", "v", or "h", followed by the current cursor
                    number of the same type.
                    
        axis: None (default), int, the str "all" or "a" (case-insensitive), or
            a pyqtgraph.PlotItem object.
            
            Indicates the axis (or PlotItem) where the cursor will be created.
            
            When there are no axes yet the cursor will be created by default in
            the scene, and wil behave like a multi-axis cursor.
            WARNING the coordinates won't make much sense unless in this case,
            unless they are given in the scene coordinates. 
            
            None (the default) indicates that the cursor will be created in
            the selected axis (which by default is the top axis at index 0).
            
            Axis "a" or "all" indicates a cursor that spans all axes 
            (multi-axis cursor). 
            
            When "axis" is a pyqtgraph.PlotItem, it must be one of the axes
            that belong to this instance of SignalViewer.
                
        
        It is recommended to pass arguments as keyword arguments for predictable
            behavior.
        
        
        """
        # NOTE: 2020-02-26 14:23:40
        # creates the cursor DIRECTLY at the specified coordinates
        kwargs["show_value"] = self._cursorsShowValue_ == True
        
        crsID = self._addCursor_(cursor_type = cursorType,
                                x = x, y = y, xwindow = xwindow, ywindow = ywindow,
                                xBounds = xBounds, yBounds = yBounds,
                                axis = axis, label=label,
                                follows_mouse=follows_mouse,
                                precision = self.cursorLabelPrecision,
                                **kwargs)
        
        self.slot_selectCursor(crsID)
        
    @safeWrapper
    def keyPressEvent(self, keyevt):
        if keyevt.key() in (QtCore.Qt.Key_Escape, QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace):
            # removes dynamic cursor -- practically one can only have at most one 
            # dynamic cursor at any time
            if len(self._data_cursors_):
                for c in [c for c in self._data_cursors_.values() if c.isDynamic]:
                    self.slot_removeCursor(c.ID)
                    
                self._cursor_coordinates_text_=""
                self._update_coordinates_viewer_()
                #self.dynamicCursorStatus.clear()
                
    @safeWrapper
    def setupCursors(self, cursorType="c", *where, **kwargs):
        """Removes whatever cursors are already there then add new ones from the arguments.
        cursorType "c" (default), "h" or "v"
        *where = a sequence of X coordinates
        Requires at least one Axis object, therefore some data must be plotted first.
        
        Arguments:
        cursorType : string, one of "c" for crosshair, "v" for vertical, "h" for horizontal cursors
                    -- optional (default is "c")
                    
        where      : comma-separated list or a sequence of cursor coordinates:
                        * for crosshair cursors, the coordinates are given as two-element tuples;
                        * for vertical and horizontal cursors, the coordinates are floats
                    
        keyword arguments ("name=value" pairs):
                    xwindow = 1D sequence of floats with the horizontal extent of the cursor window
                        (for crosshair and vertical cursors); must have as many elements as 
                        coordinates supplied in the *where argument
                    ywindow   = as above, for crosshair and horizontal cursors
                    labels         = 1D sequence of str for cursor IDs; must have as many
                        elements as supplied through the *where argument
        """
        xwindow = self.defaultCursorWindowSizeX
        ywindow = self.defaultCursorWindowSizeY
        labels  = None
        
        allowed_keywords = ["xwindow", "ywindow", "labels"]
        
        if len(kwargs) > 0:
            
            for key in kwargs.keys():
                if key not in allowed_keywords:
                    raise ValueError("Illegal keyword argument %s" % key)
            
            if "xwindow" in kwargs.keys():
                xwindow = kwargs["xwindow"]
                
            if "ywindow" in kwargs.keys():
                ywindow = kwargs["ywindow"]
                
            if "labels" in kwargs.keys():
                labels = kwargs["labels"]
                
        
                
        if len(where) == 1:
            where = where[0]
            
        self.slot_removeCursors()
        self.displayFrame()
        #self._plotOverlayFrame_()
        self.addCursors(cursorType, where, xwindow = xwindow, ywindow = ywindow, labels = labels)
        
    @safeWrapper
    def reportCursors(self):
        text = list()
        crn = sorted([(c,n) for c,n in self._data_cursors_.items()], key = lambda x: x[0])
        
        for cursors_name, cursor in crn:
            if isinstance(cursor, SignalCursor):
                cursor_label_text = "%s %s " % ("Dynamic", cursor.ID) if cursor.isDynamic else "%s" % cursor.ID
                #cursor_label_text = "%s %s " % ("Dynamic", cursor.ID) if cursor.isDynamic else "%s %s" % ("SignalCursor", cursor.ID)
                
                if cursor.isSingleAxis:
                    if isinstance(cursor.hostItem.vb.name, str) and len(cursor.hostItem.vb.name.strip()):
                        cursor_label_text += " (%s):" % cursor.hostItem.vb.name
                    
                    text.append(cursor_label_text)
                    
                    x = cursor.getX()
                    y = cursor.getY()
                    
                    cursor_pos_text = list()
                    
                    if cursor.cursorTypeName in ("crosshair", "vertical"):
                        cursor_pos_text.append("X: %f (window: %f)" % (x, cursor.xwindow))
                        
                    if cursor.cursorTypeName in ("crosshair", "horizontal"):
                        cursor_pos_text.append("Y: %f (window: %f)" % (y, cursor.ywindow))
                        
                    text.append("\n".join(cursor_pos_text))
                        
                    if cursor.cursorTypeName in ("vertical", "crosshair"): 
                        # reporting of data value where cursor INTERSECTS data 
                        # only makes sense for vertical & crosshair cursor types
                        data_text = []
                        
                        #if isinstance(cursor.hostItem, pg.PlotItem) and x is not np.nan:
                        dataitems = cursor.hostItem.dataItems
                        
                        for kdata, dataitem in enumerate(dataitems):
                            data_x, data_y = dataitem.getData()
                            ndx = np.where(data_x >= x)[0]
                            
                            if len(ndx):
                                if len(dataitems) > 1:
                                    data_text.append("Y (%d/%d): %f" % (kdata, len(dataitems), data_y[ndx[0]]))
                                    
                                else:
                                    data_text.append("Y: %f" % data_y[ndx[0]])
                                    
                        if len(data_text) > 0:
                            text.append("\n".join(data_text))
                            
                else:
                    text.append(cursor_label_text)
                    
                    plot_item_texts = []
                    
                    for plotitem in self.plotItems:
                        plot_item_text = list()
                        
                        plot_item_cursor_pos_text = list()
                        
                        if isinstance(plotitem.vb.name, str) and len(plotitem.vb.name.strip()):
                            plot_item_cursor_pos_text.append("%s:"% plotitem.vb.name)
                            
                        x = cursor.getX(plotitem)
                        y = cursor.getY(plotitem)
                        
                        if cursor.cursorTypeName in ("crosshair", "vertical"):
                            #plot_item_cursor_pos_text.append("X: %f" % x)
                            plot_item_cursor_pos_text.append("X: %f (window: %f)" % (x, cursor.xwindow))
                            
                        if cursor.cursorTypeName in ("crosshair", "horizontal"):
                            #plot_item_cursor_pos_text.append("Y: %f" % y)
                            plot_item_cursor_pos_text.append("Y: %f (window: %f)" % (y, cursor.ywindow))
                            
                        plot_item_text.append("\n".join(plot_item_cursor_pos_text))
                        
                        if cursor.cursorTypeName in ("vertical", "crosshair"): 
                            # reporting of data value where cursor INTERSECTS data 
                            # only makes sense for vertical & crosshair cursor types
                            data_text = []
                            
                            dataitems = plotitem.dataItems
                            
                            if len(dataitems) > 0:
                                for kdata, dataitem in enumerate(dataitems):
                                    data_x, data_y = dataitem.getData()
                                    
                                    ndx = np.where(data_x >= x)[0]
                                    
                                    if len(ndx):
                                        data_text.append("Y (%d/%d): %f" % (kdata, len(dataitems), data_y[ndx[0]]))
                                        
                            if len(data_text) > 0:
                                plot_item_text.append("\n".join(data_text))
                                
                        if len(plot_item_text) > 1:
                            plot_item_texts.append("\n".join(plot_item_text))
                            
                        elif len(plot_item_text) == 1:
                            plot_item_texts.append(plot_item_text[0])
                            
                    if len(plot_item_texts) > 1:
                        text.append("\n".join(plot_item_texts))
                        
                    elif len(plot_item_texts) == 1:
                        text.append(plot_item_texts[0])
                    
        if len(text) > 0:
            self._cursor_coordinates_text_ = "\n".join(text)
            
        else:
            self._cursor_coordinates_text_ = ""
    
        self._update_coordinates_viewer_()
        
    #def setupLTPCursors(self, LTPOptions, pathway, axis=None):
        #""" Convenience function for setting up cursors for LTP experiments:
        
        #Arguments:
        #==========
        
        #LTPOptions: a dict with the following mandatory key/value pairs:
        
            #{'Average': {'Count': 6, 'Every': 6},

            #'Cursors': 
                #{'Labels':  ['Rbase',
                            #'Rs',
                            #'Rin',
                            #'EPSC0base',
                            #'EPSC0Peak',
                            #'EPSC1base',
                            #'EPSC1peak'],

                #'Pathway0': [0.06,
                            #0.06579859882206893,
                            #0.16,
                            #0.26,
                            #0.273,
                            #0.31,
                            #0.32334583993039734],

                #'Pathway1': [5.06,
                            #5.065798598822069,
                            #5.16,
                            #5.26,
                            #5.273,
                            #5.31,
                            #5.323345839930397],

                #'Windows': [0.01, 0.003, 0.01, 0.01, 0.005, 0.01, 0.005]},

            #'Pathway0': 0,

            #'Pathway1': 1,

            #'Reference': 5,

            #'Signals': ['Im_prim_1', 'Vm_sec_1']}
            
        #pathway: int = the pathway for which the cursors are shown: can be 0 or 1
        
        #axis: optional default None: an int index into the axis receiving the cursors
            #(when None, the fist axis i.e. at index 0, is chosen)
        #"""
        #if axis is not None:
            #if isinstance(axis, int):
                #if axis < 0 or axis >= len(self.axesWithLayoutPositions):
                    #raise ValueError("When specified, axis must be an integer between 0 and %d" % len(self.axesWithLayoutPositions))
                
                #self.currentAxis = axis
                
            #else:
                #raise ValueError("When specified, axis must be an integer between 0 and %d" % len(self.axesWithLayoutPositions))
            
        
        #self.setupCursors("v", LTPOptions["Cursors"]["Pathway%d"%pathway])
            
    # ### BEGIN PyQt slots
    @pyqtSlot(int)
    @safeWrapper
    def slot_analogSignalsComboBoxIndexChanged(self, index):
        if index == 0:
            self.guiSelectedSignalNames.clear()
            
        elif index == self.selectSignalComboBox.count()-1:
            self.guiSelectedSignalNames.clear()
            # TODO call selection dialog
            
            current_txt = self.selectSignalComboBox.currentText()
            
            available = [self.selectSignalComboBox.itemText(k) for k in range(1, self.selectSignalComboBox.count()-1)]
            
            if current_txt in available:
                preSelected = current_txt
                
            else:
                preSelected = None
                
            dlg = ItemsListDialog(parent=self,
                                       itemsList = available,
                                       preSelected=preSelected,
                                       title="Select Analog Signals to Plot",
                                       modal = True,
                                       selectmode = QtWidgets.QAbstractItemView.ExtendedSelection)
            
            if dlg.exec() == 1:
                sel_items = dlg.selectedItemsText
                
                if len(sel_items):
                    self.guiSelectedSignalNames[:] = sel_items[:]
                    
        else:
            self.guiSelectedSignalNames = [self.selectSignalComboBox.currentText()]

        self.displayFrame()
        
    @pyqtSlot(int)
    @safeWrapper
    def slot_plotAnalogSignalsCheckStateChanged(self, state):
        if state == QtCore.Qt.Checked:
            self._plot_analogsignals_ = True
            
        else:
            self._plot_analogsignals_ = False
            
    @pyqtSlot(int)
    @safeWrapper
    def slot_plotIrregularSignalsCheckStateChanged(self, state):
        if state == QtCore.Qt.Checked:
            self._plot_irregularsignals_ = True
            
        else:
            self._plot_irregularsignals_ = False
            
        self.displayFrame()
        
    @pyqtSlot()
    @safeWrapper
    def slot_showCoordinatesDock(self):
        self.coordinatesDockWidget.show()
        
    @pyqtSlot()
    @safeWrapper
    def slot_showAnnotationsDock(self):
        self.annotationsDockWidget.show()
        
    @pyqtSlot()
    @safeWrapper
    def slot_detectTriggers(self):
        if isinstance(self.yData, (neo.Block, neo.Segment)) or (isinstance(self.yData, (tuple, list)) and all([isinstance(v, (neo.Block, neo.Segment)) for v in self.yData])):
            from gui.triggerdetectgui import TriggerDetectDialog
            tdlg = TriggerDetectDialog(ephysdata=self.yData, ephysViewer=self, parent=self)
            tdlg.open()
        
    @pyqtSlot(str)
    @safeWrapper
    def slot_reportCursorPosition(self, crsId = None):
        self.reportCursors()
        
    @pyqtSlot(str)
    @safeWrapper
    def slot_reportCursorPosition2(self, crsId = None):
        cursor = None
        
        if crsId is not None:
            cursor = self.dataCursor(crsId)
        
        if cursor is None:
            cursor = self.sender()
        
        if isinstance(cursor, SignalCursor):
            text = []
            
            if cursor.isDynamic:
                cursor_label_text = "Dynamic %s" % cursor.ID
                    
            else:
                cursor_label_text = "SignalCursor %s" % cursor.ID
                
            if cursor.isSingleAxis:
                if isinstance(cursor.hostItem.vb.name, str) and len(cursor.hostItem.vb.name.strip()):
                    cursor_label_text += " in %s:" % cursor.hostItem.vb.name
                
                text.append(cursor_label_text)
                
                x = cursor.getX()
                y = cursor.getY()
                
                cursor_pos_text = list()
                
                if cursor.cursorTypeName in ("crosshair", "vertical"):
                    cursor_pos_text.append("X: %f" % x)
                    
                if cursor.cursorTypeName in ("crosshair", "horizontal"):
                    cursor_pos_text.append("Y: %f" % y)
                    
                text.append("\n".join(cursor_pos_text))
                    
                if cursor.cursorTypeName in ("vertical", "crosshair"): 
                    # data value reporting only makes sense for vertical cursor types
                    data_text = []
                    
                    #if isinstance(cursor.hostItem, pg.PlotItem) and x is not np.nan:
                    dataitems = cursor.hostItem.dataItems
                    
                    for kdata, dataitem in enumerate(dataitems):
                        data_x, data_y = dataitem.getData()
                        ndx = np.where(data_x >= x)[0]
                        if len(ndx):
                            if len(dataitems) > 1:
                                data_text.append("Y (%d/%d): %f" % (kdata, len(dataitems), data_y[ndx[0]]))
                                
                            else:
                                data_text.append("Y: %f" % data_y[ndx[0]])
                                
                    if len(data_text) > 1:
                        text.append("\n".join(data_text))
                        
                    else:
                        text.append(data_text[0])
                                
            else:
                text.append(cursor_label_text)
                
                plot_item_texts = []
                
                for plotitem in self.plotItems:
                    plot_item_text = list()
                    
                    plot_item_cursor_pos_text = list()
                    
                    if isinstance(plotitem.vb.name, str) and len(plotitem.vb.name.strip()):
                        plot_item_cursor_pos_text.append("%s:"% plotitem.vb.name)
                        
                    x = cursor.getX(plotitem)
                    y = cursor.getY(plotitem)
                    
                    if cursor.cursorTypeName in ("crosshair", "vertical"):
                        plot_item_cursor_pos_text.append("X: %f" % x)
                        
                    if cursor.cursorTypeName in ("crosshair", "horizontal"):
                        plot_item_cursor_pos_text.append("Y: %f" % y)
                        
                    plot_item_text.append("\n".join(plot_item_cursor_pos_text))
                    
                    if cursor.cursorTypeName in ("vertical", "crosshair"): 
                        # data value reporting only makes sense for vertical cursor types
                        data_text = []
                        
                        dataitems = plotitem.dataItems
                        
                        if len(dataitems) > 0:
                            for kdata, dataitem in enumerate(dataitems):
                                data_x, data_y = dataitem.getData()
                                
                                ndx = np.where(data_x >= x)[0]
                                
                                if len(ndx):
                                    data_text.append("Y (%d/%d): %f" % (kdata, len(dataitems), data_y[ndx[0]]))
                                    
                        if len(data_text) > 0:
                            plot_item_text.append("\n".join(data_text))
                            
                    if len(plot_item_text) > 1:
                        plot_item_texts.append("\n".join(plot_item_text))
                        
                    elif len(plot_item_text) == 1:
                        plot_item_texts.append(plot_item_text[0])
                        
                if len(plot_item_texts) > 1:
                    text.append("\n".join(plot_item_texts))
                    
                elif len(plot_item_texts) == 1:
                    text.append(plot_item_texts[0])
                    
            if len(text) > 1:
                self._cursor_coordinates_text_ = "\n".join(text)
                
            elif len(text) == 1:
                self._cursor_coordinates_text_ = text[0]
                
            else:
                self._cursor_coordinates_text_ = ""
        
            self._update_coordinates_viewer_()
            
        else:
            self._cursor_coordinates_text_ = ""
            
    @pyqtSlot(int)
    @safeWrapper
    def slot_irregularSignalsComboBoxIndexChanged(self, index):
        if index == 0:
            self.guiSelectedIrregularSignalNames.clear()
            
        elif index == self.selectIrregularSignalComboBox.count()-1:
            self.guiSelectedIrregularSignalNames.clear()
            
            current_txt = self.selectIrregularSignalComboBox.currentText()
        
            available = [self.selectIrregularSignalComboBox.itemText(k) for k in range(1, self.selectIrregularSignalComboBox.count()-1)]
            
            if current_txt in available:
                preSelected = current_txt
                
            else:
                preSelected=None
            
            dlg = ItemsListDialog(parent=self, 
                                       itemsList = available, 
                                       preSelected = preSelected,
                                       title="Select Irregular Signals to Plot", 
                                       modal=True,
                                       selectmode=QtWidgets.QAbstractItemView.ExtendedSelection)
            
            if dlg.exec() == 1:
                sel_items = dlg.selectedItemsText
                
                if len(sel_items):
                    self.guiSelectedIrregularSignalNames[:] = sel_items[:]
                    
        else:
            self.guiSelectedIrregularSignalNames = [self.selectIrregularSignalComboBox.currentText()]
    
        self.displayFrame()
         
    # ### END PyQt slots
    
    def var_observer(self, change):
        self.displayFrame()
        

    def linkCursors(self, id1, *ids):
        """ Bidirectionally links cursors of the same type.
        Linked cursors move together when either of them is moved by the user.
        Supports single-axis static cursors (which can only be "dragged" around).
        The axes need not be the same, HOWEVER:
        
        a) linked cursors MUST have the same type
        
        b) for horizontal cursors
        """
        
        if len(ids) == 0:
            raise ValueError("Link to what?")
        
        if not self._hasCursor_(id1):
            raise ValueError("SignalCursor %s not found" % id1)

        ct = self.dataCursor(id1).cursorType()
        
        other = list()
        
        for cid in ids:
            if not self._hasCursor_(cid):
                raise ValueError("SignalCursor %s not found" % cid)
            
            if self.dataCursor(cid).cursorType() != ct:
                raise ValueError("Cannot link cursors of different types")

            other.append(self.dataCursor(cid))
        
        self.dataCursor(id1).linkTo(*other)
            
    def unlinkCursors(self, id1=None, *ids):
        """Unlinks several linked cursors.
        
        Either cursor may still be individually linked to other cursors of the same type.
        """
        
        if id1 is None: # just unlink ALL linked cursors from any link they may have
            for c in self._data_cursors_.values():
                c.unlink()
                
            return
        
        if not self._hasCursor_(id1):
            raise ValueError("SignalCursor %s not found" % id1)
        
        ct = self.dataCursor(id1).cursorType()
        
        if len(ids) == 1: 
            if isinstance(ids[0], str): # it is a cursor ID
                if not self._hasCursor_(ids[0]):
                    raise ValueError("SignalCursor %s not found" % ids[0])
                
                if self.dataCursor(id1).cursorType() != self.dataCursor(ids[0]).cursorType():
                    raise ValueError("Cursors of different types cannot be linked")
                    
                self.dataCursor(id1).unlinkFrom(self.dataCursor(ids[0]))
                
            elif isinstance(ids[0], tuple) or isinstance(ids[0], list):# this is a tuple or list of cursor IDs: we unlink id1 from each one, keep their link state unchanged
                other = list()
                for cid in ids[0]:
                    if not self._hasCursor_(cid):
                        raise ValueError("SignalCursor %s not found" % cid)
                    
                    if self.dataCursor(cid).cursorType() != ct:
                        raise ValueError("Cursors of different types cannot be linked")
                    
                    other.append(self.dataCursor(cid))
                
                self.dataCursor(id1).unlinkFrom(*other)
                
        elif len(ids) > 1: # a comma-seprated list of cursor IDs: unlink _ALL_ of them
            other = list()
            
            for cid in ids:
                if not self._hasCursor_(cid):
                    raise ValueError("SignalCursor %s not found " % cid)
                
                if self.dataCursor(cid).cursorType() != ct:
                    raise ValueError("Cursors of different types cannot be linked")
                
                other.append(self.dataCursor(cid))
            
            self.dataCursor(id1).unlinkFrom(*other)
            
            for c in other:
                c.unlink()
                
        else: # unlink ALL
            self.dataCursor(id1).unlink()

    #"def" selectCursor(self, ID):
        #self.slot_selectCursor(ID)
        
    @pyqtSlot(object)
    def slot_varModified(self, obj):
        """Connected to _scipyenWindow_.workspaceModel.varModified signal
        """
        self.displayFrame()
        
    @pyqtSlot()
    @safeWrapper
    def slot_refreshDataDisplay(self):
        if self._scipyenWindow_ is None:
            return
        
        self.displayFrame()
        
        # if self._data_var_name_ is not None and self._data_var_name_ in self._scipyenWindow_.workspace.keys():
        #     self.setData(self._scipyenWindow_.workspace[self._data_var_name_], self._data_var_name_)
            
        # if self.yData in self._scipyenWindow_.workspace.values():
        #     self.setData(self._scipyenWindow_.workspace[self._data_var_name_], self._data_var_name_)
            

    def _hasCursor_(self, crsID): #  syntactic sugar
        if len(self._data_cursors_) == 0:
            return False
        
        return crsID in self._data_cursors_
    
    def _gui_chose_cursor_color_(self, cursortype:str):
        if cursortype in ("crosshair", "horizontal", "vertical"):
            title = "%s cursor color" % cursortype.capitalize()
            prop_normal = inspect.getattr_static(self, f"{cursortype}CursorColor")
            prop_linked = inspect.getattr_static(self, f"linked{cursortype.capitalize()}CursorColor")
            
            ret = quickColorDialog(parent = self, title = title,
                                   labels = {"Normal":colormaps.qcolor(prop_normal.fget(self)),
                                             "Linked":colormaps.qcolor(prop_linked.fget(self))}
                                   )
                                   
            if len(ret):
                #print("ret")
                #pprint(ret)
                prop_normal.fset(self, ret.Normal.name)
                prop_linked.fset(self, ret.Linked.name)

        elif cursortype == "hover":
            title = "Cursor hover color"
            prop = inspect.getattr_static(self, "cursorHoverColor")
            ret = quickColorDialog(parent = self, title = title,
                                   labels = {"Color":colormaps.qcolor(prop.fget(self))}
                                   )
            
            if len(ret):
                prop.fset(self, ret.Color.name)
        else:
            raise ValueError("Unknown cursor type %s" % cursortype)
    
    def _set_cursors_color(self, val:typing.Any, cursortype:str, linked:bool=False):
        """ Common color setter code for cursors, called by propery setters
        
        Allowed cursortype values are: 'crosshair', 'horizontal', 'vertical' and 
        'hover', in which case this changes the hover color for all cursors.
        
        The hover color is the color of the cursor when hovered by the mouse.
        
        linked: Changes the color of the normal (when False, the default) or 
        linked cursors (when True) os the specified type.
            Ignored when cursortype is 'hover'
        
        """
        name, color = colormaps.get_name_color(val)
        
        #print(f"_set_cursors_color {cursortype} (linked: {linked}): {name}")
        
        if cursortype in ("crosshair", "horizontal", "vertical"):
            cursorColorDict = self._linkedCursorColors_ if linked else self._cursorColors_
            ctype = cursortype.capitalize()
            lnk = "Linked" if linked else ""
            #print(f"_set_cursors_color for {lnk} {ctype}: color {color.name()} (named: {name})")
            cursors = getattr(self, f"{cursortype}Cursors")
            traitname = f"{lnk}{ctype}CursorColor"
            cursorColorDict[cursortype] = name
            
        elif cursortype == "hover":
            #print(f"_set_cursors_color for hover: color {color.name()} (named: {name})")
            cursors = self.cursors
            traitname = "CursorHoverColor"
            self._cursorHoverColor_ = name
        
        else:
            raise ValueError(f"Unknown cursor type {cursortype}")
        
        #print(f"_set_cursors_color for {cursortype}: name {name} color {color}; traitname {traitname}")
        
        
        for cursor in cursors:
            if cursortype == "hover":
                pen = cursor.hoverPen
                pen.setColor(color)
                cursor.hoverPen = pen
            else:
                pen = cursor.linkedPen if linked else cursor.pen
                pen.setColor(color)
                if linked:
                    cursor.linkedPen = pen
                else:
                    cursor.pen = pen
        
        if isinstance(getattr(self, "configurable_traits", None), DataBag):
            self.configurable_traits[traitname] = name
        
    def _addCursor_(self, cursor_type: typing.Union[str, SignalCursor.SignalCursorTypes], x: typing.Union[numbers.Number, pq.Quantity, type(None)] = None, y: typing.Union[numbers.Number, pq.Quantity, type(None)] = None, xwindow: typing.Union[numbers.Number, pq.Quantity, type(None)] = None, ywindow: typing.Union[numbers.Number, pq.Quantity, type(None)] = None, xBounds: typing.Union[tuple, type(None)] = None, yBounds: typing.Union[tuple, type(None)] = None, axis: typing.Optional[typing.Union[int, str, pg.PlotItem, pg.GraphicsScene]] = None, label:typing.Optional[str] = None, follows_mouse: bool = False, precision:typing.Optional[int]=None, **kwargs):
        """Creates a cursor.
        kwargs: var-keyword parameters for SignalCursor constructor (pen, etc)
        """
        #print("_addCursor_ x,y", x, y)
        
        if xwindow is None:
            xwindow = self.defaultCursorWindowSizeX
            
        elif isinstance(xwindow, pq.Quantity):
            xwindow = float(xwindow.magnitude.flatten()[0])
            
        elif not isinstance(xwindow, numbers.Number):
            raise TypeError("Unexpected type for xwindow: %s" % type(xwindow).__name__)
            
        if ywindow is None:
            ywindow = self.defaultCursorWindowSizeY
            
        elif isinstance(ywindow, pq.Quantity):
            ywindow = float(ywindow.magnitude.flatten()[0])
            
        elif not isinstance(ywindow, numbers.Number):
            raise TypeError("Unexpected type for ywindow: %s" % type(ywindow).__name__)
            
        #### BEGIN Figure out cursors destination: axis or scene
        # NOTE: it seemingly makes no sense to add a cursors when there are no
        # plot items (axes); nevertheless the cursor can and should be added
        # to the GraphicsScene
        if len(self.signalsLayout.items) == 0:
            axis = self.signalsLayout.scene() # a pg.GraphicsScene
            
        elif axis is None:
            if self._current_plot_item_ is None:
                axis = self.axis(0)
                
            else:
                axis = self._current_plot_item_
            
        elif isinstance(axis, int):
            if axis < 0 or axis >= len(self.axes):
                raise ValueError("Invalid axis index %d for %d axes" % (axis, len(self.axes)))
            
            axis = self.axis(axis)
            
        elif isinstance(axis, str) and axis.lower().strip() in ("all", "a"):
            axis = self.signalsLayout.scene()
            
        elif not isinstance(axis, (pg.PlotItem, pg.GraphicsScene)):
            raise TypeError("axes expected to be an int, a str ('all' or 'a'), a pyqtgraph.PlotItem, a pyqtgraph.GraphicsScene, or None; got %s instead" % type(axes).__name__)
            
        #### END Figure out cursors destination: axis or scene
        
        #### BEGIN check cursors coordinates
        if isinstance(axis, pg.PlotItem):
            if axis not in self.signalsLayout.items:
                return
            
            # NOTE: don't use viewRange unless there is no data plotted
            # guiutils.getPlotItemDataBoundaries retrieved the actual data 
            # boundaries if there is any dtaa plotted, else returns the stock
            # axis.viewRange()
            view_range = guiutils.getPlotItemDataBoundaries(axis)
#             pdis = [i for i in axis.listDataItems() if isinstance(i, pg.PlotDataItem)]
#             if len(pdis) == 0:
#                 view_range = axis.viewRange() #  [[xmin, xmax], [ymin, ymax]]
#             else:
#                 
            
            
            if x is None:
                x = view_range[0][0] + (view_range[0][1] - view_range[0][0])/2
            
            elif isinstance(x, pq.Quantity):
                x = float(x.magnitude.flatten()[0])
                
            elif not isinstance(x, numbers.Number):
                raise TypeError("Unexpected type for x coordinate: %s" % type(x).__name__)
            
            if xBounds is None:
                xBounds = view_range[0]
                
            if y is None:
                y = view_range[1][0] + (view_range[1][1] - view_range[1][0])/2
            
            elif isinstance(y, pq.Quantity):
                y = float(y.magnitude.flatten()[0])
            
            elif not isinstance(y, numbers.Number):
                raise TypeError("Unexpected type for y coordinate: %s" % type(y).__name__ )
            
            if yBounds is None:
                yBounds = view_range[1]
            
        elif isinstance(axis, pg.GraphicsScene):
            # generate a multi-axis cursor
            # when there are several axes the cursor that spans them all
            if axis is not self.signalsLayout.scene():
                return
            
            if len(self.signalsLayout.items) == 0:
                # there is no axis (plotitem)
                warnings.warn("There is no axis in the viewer; have you plotted anything yet?\nThe cursor's coordinates will be reset when plotting")
                
                scene_rect = self.signalsLayout.scene().sceneRect()
                
                if x is None:
                    x = scene_rect.width()/2
                    
                elif isinstance(x, pq.Quantity):
                    x = float(x.magnitude.flatten()[0])
                    
                elif not isinstance(x, numbers.Number):
                    raise TypeError("Unexpected type for x coordinate: %s" % type(x).__name__)
                
                if xBounds is None:
                    xBounds = (scene_rect.x(), scene_rect.x() + scene_rect.width())
                
                if y is None:
                    y = scene_rect.height()/2
                    
                elif isinstance(y, pq.Quantity):
                    y = float(y.magnitude.flatten()[0])
                    
                elif not isinstance(y, numbers.Number):
                    raise TypeError("Unexpected type for y coordinate: %s" % type(y).__name__)
                
                if yBounds is None:
                    yBounds = (scene_rect.y(), scene_rect.y() + scene_rect.height())
                
            else:
                pIs = self.plotItems
                
                min_x_axis = np.min([p.viewRange()[0][0] for p in pIs])
                max_x_axis = np.max([p.viewRange()[0][1] for p in pIs])
                
                topAxis_y_max = pIs[0].viewRange()[1][1]
                bottomAxis_y_min = pIs[-1].viewRange()[1][0]
            
                min_point = pIs[0].vb.mapViewToScene(QtCore.QPointF(min_x_axis,topAxis_y_max ))
                max_point = pIs[-1].vb.mapViewToScene(QtCore.QPointF(max_x_axis, bottomAxis_y_min))
                
                if x is None:
                    x = min_point.x() + (max_point.x() - min_point.x())/2.
                    
                elif isinstance(x, pq.Quantity):
                    x = float(x.magnitude.flatten()[0])
                    
                elif not isinstance(x, numbers.Number):
                    raise TypeError("Unexpected type for x coordinate: %s" % type(x).__name__)
                
                if y is None:
                    y = min_point.y() + (max_point.y() - min_point.y())/2.
                    
                elif isinstance(y, pq.Quantity):
                    y = float(y.magnitude.flatten()[0])
                    
                elif not isinstance(y, numbers.Number):
                    raise TypeError("Unexpected type for y coordinate: %s" % type(y).__name__)
                    
                if xBounds is None:
                    xBounds = [min_point.x(), max_point.x()]
                
                if yBounds is None:
                    yBounds = [min_point.y(), max_point.y()]
                
        #### END check cursors coordinates
        
        if not isinstance(cursor_type, str):
            raise TypeError("cursor_type expected to be a str; got %s instead" % type(cursor_type).__name__)
        
        if isinstance(cursor_type, SignalCursor.SignalCursorTypes):
            cursor_type = cursor_type.name
        
        if cursor_type in ("vertical", "v", SignalCursor.SignalCursorTypes.vertical):
            cursorDict = self.verticalSignalCursors
            crsPrefix = "v"
            
            ywindow = 0.0
            pen = QtGui.QPen(QtGui.QColor(self.cursorColors["vertical"]), 1, QtCore.Qt.SolidLine)
            linkedPen = QtGui.QPen(QtGui.QColor(self.linkedCursorColors["vertical"]), 1, QtCore.Qt.SolidLine)
            pen.setCosmetic(True)
            linkedPen.setCosmetic(True)
            
        elif cursor_type in ("horizontal", "h", SignalCursor.SignalCursorTypes.horizontal):
            cursorDict = self.horizontalSignalCursors
            crsPrefix = "h"
            xwindow = 0.0
            pen = QtGui.QPen(QtGui.QColor(self.cursorColors["horizontal"]), 1, QtCore.Qt.SolidLine)
            linkedPen = QtGui.QPen(QtGui.QColor(self.linkedCursorColors["horizontal"]), 1, QtCore.Qt.SolidLine)
            pen.setCosmetic(True)
            linkedPen.setCosmetic(True)
            
        elif cursor_type in ("crosshair", "c", SignalCursor.SignalCursorTypes.crosshair):
            cursorDict = self.crosshairSignalCursors
            crsPrefix = "c"
            pen = QtGui.QPen(QtGui.QColor(self.cursorColors["crosshair"]), 1, QtCore.Qt.SolidLine)
            linkedPen = QtGui.QPen(QtGui.QColor(self.linkedCursorColors["crosshair"]), 1, QtCore.Qt.SolidLine)
            pen.setCosmetic(True)
            linkedPen.setCosmetic(True)
            
        else:
            raise ValueError("unsupported cursor type %s" % cursor_type)
        
        hoverPen = QtGui.QPen(QtGui.QColor(self._cursorHoverColor_), 1, QtCore.Qt.SolidLine)
        hoverPen.setCosmetic(True)
        
        nCursors = len(cursorDict)
        
        if label is None:
            crsId = "%s%s" % (crsPrefix, str(nCursors))
            
        else:
            crsId = label
            
        if isinstance(axis, pg.PlotItem):
            precision = self.get_axis_xData_precision(axis)
                
        else:
            pi_precisions = [self.get_axis_xData_precision(ax) for ax in self.plotItems]
            precision = min(pi_precisions)
            
        cursorDict[crsId] = SignalCursor(axis, 
                                   x = x, y = y, xwindow=xwindow, ywindow=ywindow,
                                   cursor_type = cursor_type,
                                   cursorID = crsId,
                                   linkedPen = linkedPen,
                                   pen = pen, 
                                   hoverPen=hoverPen,
                                   parent = self, 
                                   follower = follows_mouse, 
                                   relative = True,
                                   xBounds = xBounds,
                                   yBounds = yBounds,
                                   precision = precision,
                                   **kwargs)
        
        cursorDict[crsId].sig_cursorSelected[str].connect(self.slot_selectCursor)
        cursorDict[crsId].sig_reportPosition[str].connect(self.slot_reportCursorPosition)
        cursorDict[crsId].sig_doubleClicked[str].connect(self.slot_editCursor)
        cursorDict[crsId].sig_editMe[str].connect(self.slot_editCursor)
        
        return crsId
    
    def get_axis_xData_precision(self, axis):
        #pdis = [i for i in axis.items if isinstance(i, pg.PlotDataItem)]
        pXData = (i.xData[~np.isnan(i.xData)] for i in axis.items if isinstance(i, pg.PlotDataItem) and sgp.nansize(i.xData) > 1)
        
        precisions = [int(abs(np.round(np.log10((np.diff(x)).mean())))) for x in pXData]
        if len(precisions):
            return min(precisions)
            
        return SignalCursor.default_precision
        

    @pyqtSlot((QtCore.QPoint))
    @safeWrapper
    def slot_annotationsContextMenuRequested(self, point):
        if self._scipyenWindow_ is None: 
            return
        
        # NOTE: 2022-03-04 10:05:14
        # annotations viewer is dictviewer.InteractiveTreeWidget
        indexList = self.annotationsViewer.selectedIndexes()
        
        if len(indexList) == 0:
            return
        
        cm = QtWidgets.QMenu("Data operations", self)
        
        copyItemData = cm.addAction("Copy to workspace")
        copyItemData.triggered.connect(self.slot_exportAnnotationDataToWorkspace)
        
        cm.popup(self.annotationsViewer.mapToGlobal(point), copyItemData)
        
    @pyqtSlot()
    @safeWrapper
    def slot_exportAnnotationDataToWorkspace(self):
        if self._scipyenWindow_ is None:
            return
        
        items = self.annotationsViewer.selectedItems()
        
        if len(items) == 0:
            return
        
        self._export_data_items_(items)
        
    @pyqtSlot()
    def slot_exportDataToWorkspace(self):
        if self.yData is None:
            return
        
        if self.xData is None:
            var_name = getattr(self.yData, "name", None)
            if not isinstance(var_name, str) or len(var_name.strip()) == 0:
                var_name = "data"
            
            self.exportDataToWorkspace(self.yData, var_name)
            
        else:
            data = (self.xData, self.yData)
            var_name ="data"
            self.exportDataToWorkspace(data, var_name)
        
        
        
    @safeWrapper
    def _export_data_items_(self, items):
        from core.utilities import get_nested_value
        if self._scipyenWindow_ is None:
            return
        
        values = list()
        
        item_paths = list()
        
        if isinstance(self.dataAnnotations, (dict, tuple, list)):
            for item in items:
                item_path = list()
                item_path.append(item.text(0))
                
                parent = item.parent()
                
                while parent is not None:
                    item_path.append(parent.text(0))
                    parent = parent.parent()
                
                item_path.reverse()
                
                value = get_nested_value(self.dataAnnotations, item_path[1:]) # because 1st item is the insivible root name
                
                values.append(value)
                
                item_paths.append(item_path[-1])
                
            if len(values):
                if len(values) == 1:
                    dlg = qd.QuickDialog(self, "Copy to workspace")
                    namePrompt = qd.StringInput(dlg, "Data name:")
                    
                    newVarName = strutils.str2symbol(item_paths[-1])
                    
                    namePrompt.variable.setClearButtonEnabled(True)
                    namePrompt.variable.redoAvailable=True
                    namePrompt.variable.undoAvailable=True
                    
                    namePrompt.setText(newVarName)
                    
                    if dlg.exec() == QtWidgets.QDialog.Accepted:
                        newVarName = validate_varname(namePrompt.text(), self._scipyenWindow_.workspace)
                        
                        self._scipyenWindow_.assignToWorkspace(newVarName, values[0])
                        
                        
                else:
                    for name, value in zip(item_paths, values):
                        newVarName = validate_varname(name, self._scipyenWindow_.workspace)
                        self._scipyenWindow_.assignToWorkspace(newVarName, value)
        
        
    @pyqtSlot()
    @safeWrapper
    def slot_addVerticalCursor(self, label = None, follows_mouse=False):
        return self._addCursor_("vertical", axis=self._current_plot_item_, 
                                  label=label, follows_mouse=follows_mouse,
                                  show_value=self.setCursorsShowValue.isChecked())
    
    @pyqtSlot()
    @safeWrapper
    def slot_addHorizontalCursor(self, label=None, follows_mouse=False):
        return self._addCursor_("horizontal", axis=self._current_plot_item_, 
                                  label=label, follows_mouse=follows_mouse,
                                  show_value=self.setCursorsShowValue.isChecked())
        
    @pyqtSlot()
    @safeWrapper
    def slot_addCrosshairCursor(self, label=None, follows_mouse=False):
        return self._addCursor_("crosshair", axis=self._current_plot_item_, 
                                  label=label, follows_mouse=follows_mouse,
                                  show_value=self.setCursorsShowValue.isChecked())
    
    @pyqtSlot()
    @safeWrapper
    def slot_export_svg(self):
        if self.fig.scene() is None:
            return
        
        self._export_to_graphics_file_("svg")
        
    @pyqtSlot()
    @safeWrapper
    def slot_export_tiff(self):
        if self.fig.scene() is None:
            return
        
        self._export_to_graphics_file_("tiff")
        
    @pyqtSlot()
    @safeWrapper
    def slot_export_png(self):
        if self.fig.scene() is None:
            return
        
        self._export_to_graphics_file_("png")
        
    @safeWrapper
    def _export_to_graphics_file_(self, file_format):
        if not isinstance(file_format, str) or file_format.strip().lower() not in ("svg", "tiff", "png"):
            raise ValueError("Unsupported export file format %s" % file_format)
        
        if file_format.strip().lower() == "svg":
            file_filter = "Scalable Vector Graphics Files (*.svg)"
            caption_suffix = "SVG"
            
        elif file_format.strip().lower() == "tiff":
            file_filter = "TIFF Files (*.tif)"
            caption_suffix = "TIFF"
            
        elif file_format.strip().lower() == "png":
            file_filter = "Portable Network Graphics Files (*.png)"
            caption_suffix = "PNG"
            
        else:
            raise ValueError("Unsupported export file format %s" % file_format)
        
        if self._scipyenWindow_ is not None:
            targetDir = self._scipyenWindow_.currentDir
            
            fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self,
                                                                caption="Export figure as %s" % caption_suffix,
                                                                filter = file_filter,
                                                                directory = targetDir)
            
        else:
            fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self,
                                                                caption="Export figure as %s" % caption_suffix,
                                                                filter = file_filter)
            
        if len(fileName) == 0:
            return
        
        if file_format.strip().lower() == "svg":
            generator = QtSvg.QSvgGenerator()
            generator.setFileName(fileName)
            
            generator.setSize(QtCore.QSize(int(self.fig.scene().width()), int(self.fig.scene().height())))
            generator.setViewBox(QtCore.QRect(0, 0, int(self.fig.scene().width()), int(self.fig.scene().height())))
            generator.setResolution(300)
            
            font = QtGui.QGuiApplication.font()
            
            painter = QtGui.QPainter()
            painter.begin(generator)
            painter.setFont(font)
            self.fig.scene().render(painter)
            painter.end()
        
        else:
            out = QtGui.QImage(int(self.fig.scene().width()), int(self.fig.scene().height()))
            
            out.fill(QtGui.QColor(pg.getConfigOption("background")))
            
            painter = QtGui.QPainter(out)
            self.fig.scene().render(painter)
            painter.end()
            
            out.save(fileName, file_format.strip().lower(), 100)
    
    @pyqtSlot()
    @safeWrapper
    def slot_addDynamicCrosshairCursor(self, label=None):
        return self._addCursor_("crosshair", item=self._current_plot_item_, 
                                  label=label, follows_mouse=True)
    
    @pyqtSlot()
    @safeWrapper
    def slot_addDynamicVerticalCursor(self, label=None):
        return self._addCursor_("vertical", item=self._current_plot_item_, 
                                  label=label, follows_mouse=True)
    
    @pyqtSlot()
    @safeWrapper
    def slot_addDynamicHorizontalCursor(self, label=None):
        return self._addCursor_("horizontal", item=self._current_plot_item_, 
                                  label=label, follows_mouse=True)
    
    def _construct_multi_axis_vertical_(self, label=None, dynamic=False):
        # NOTE: 2020-02-26 14:37:50
        # code being migrated to _addCursor_()
        # with allowing for cursors to be added to an empty scene (i.e. with no
        # axes) on the condition that their coordinates must be reset once
        # something has been plotted
        if self.signalsLayout.scene() is not None:
            ax_cx = self.axesWithLayoutPositions
            
            if len(ax_cx) == 0:
                return
            
            pIs, _ = zip(*ax_cx)
            
            min_x_axis = np.min([p.viewRange()[0][0] for p in pIs])
            max_x_axis = np.max([p.viewRange()[0][1] for p in pIs])
            
            min_point = pIs[0].vb.mapViewToScene(QtCore.QPointF(min_x_axis, 0))
            max_point = pIs[0].vb.mapViewToScene(QtCore.QPointF(max_x_axis, 0))
            
            xbounds = [min_point.x(), max_point.x()]

            return self._addCursor_("vertical", axis=self.signalsLayout.scene(), 
                                    label=label, follows_mouse=dynamic, xBounds=xbounds)
        
    
    @pyqtSlot()
    @safeWrapper
    def slot_addMultiAxisVerticalCursor(self, label=None):
        self._construct_multi_axis_vertical_(label=label)
        
    @pyqtSlot()
    @safeWrapper
    def slot_addDynamicMultiAxisVerticalCursor(self, label=None):
        self._construct_multi_axis_vertical_(label=label, dynamic=True)
        
    def _construct_multi_axis_crosshair_(self, label=None, dynamic=False):
        # NOTE: 2020-02-26 14:39:09
        # see  NOTE: 2020-02-26 14:37:50
        if self.signalsLayout.scene() is not None:
            ax_cx = self.axesWithLayoutPositions
            if len(ax_cx) == 0:
                return
            
            pIs, _ = zip(*ax_cx)
            
            min_x_axis = np.min([p.viewRange()[0][0] for p in pIs])
            max_x_axis = np.max([p.viewRange()[0][1] for p in pIs])
            
            topAxis_y_max = pIs[0].viewRange()[1][1]
            bottomAxis_y_min = pIs[-1].viewRange()[1][0]
            
            # scene coordinate system is upside-down!
            min_point = pIs[0].vb.mapViewToScene(QtCore.QPointF(min_x_axis,topAxis_y_max ))
            max_point = pIs[-1].vb.mapViewToScene(QtCore.QPointF(max_x_axis, bottomAxis_y_min))
            
            xbounds = [min_point.x(), max_point.x()]

            ybounds = [min_point.y(), max_point.y()]
            
            return self._addCursor_("crosshair", axis=self.signalsLayout.scene(), 
                                    label=label, follows_mouse=dynamic, 
                                    xBounds = xbounds, yBounds = ybounds)
        
        
    @pyqtSlot()
    @safeWrapper
    def slot_addMultiAxisCrosshairCursor(self, label=None):
        self._construct_multi_axis_crosshair_(label=label)
        
    @pyqtSlot()
    @safeWrapper
    def slot_addDynamicMultiAxisCrosshairCursor(self, label=None):
        self._construct_multi_axis_crosshair_(label=label, dynamic=True)
        
    @safeWrapper
    def removeCursors(self):
        """Remove all signal cursors
        """
        self.slot_removeCursors()
        
    @safeWrapper
    def removeActiveCursor(self):
        self.slot_removeSelectedCursor()
        
    @safeWrapper
    def removeCursor(self, crsID=None):
        self.slot_removeCursor(crsID)

    @pyqtSlot()
    @safeWrapper
    def slot_removeCursors(self):
        #if len(self._data_cursors_) == 0:
            #return
        # FIXME 2017-10-09 22:52:28 what do we do with these?!?
        #axes, _ = zip(*self.axesWithLayoutPositions)
        axes = self.plotItems
        
        for crs in self._data_cursors_.values():
            crs.detach()
        
        self._data_cursors_.clear()
        self.crosshairSignalCursors.clear()
        self.horizontalSignalCursors.clear()
        self.verticalSignalCursors.clear()
        
        self.selectedDataCursor = None
        self._cursor_coordinates_text_ = ""
        self._update_coordinates_viewer_()
        
    @pyqtSlot()
    @safeWrapper
    def slot_removeCursor(self, crsID=None):
        if len(self._data_cursors_) == 0:
            return
        
        if not isinstance(crsID, str):
            d = qd.QuickDialog(self, "Choose cursor to remove")
            #d = vigra.pyqt.qd.QuickDialog(self, "Choose cursor to remove")
        
            cursorComboBox = qd.QuickDialogComboBox(d, "Select cursor:")
            cursorComboBox.setItems([c for c in self._data_cursors_])
            cursorComboBox.setValue(0)
            
            d.cursorComboBox = cursorComboBox
            
            if d.exec() == QtWidgets.QDialog.Accepted:
                crsID = d.cursorComboBox.text()
                
        if crsID not in self._data_cursors_:
            return
        
        crs = None
        
        if crsID in self.crosshairSignalCursors:
            crs = self.crosshairSignalCursors.pop(crsID, None)

        elif crsID in self.horizontalSignalCursors:
            crs = self.horizontalSignalCursors.pop(crsID, None)

        elif crsID in self.verticalSignalCursors:
            crs = self.verticalSignalCursors.pop(crsID, None) 
            
        # now, also remove its line2D objects from the axes
        if crs is not None:
            crs.detach()
            
        self._cached_cursors_.clear()
            
        # in case a manual request was made and this happens to be the selected cursor
        if isinstance(self.selectedDataCursor, SignalCursor):
            if self.selectedDataCursor.ID == crsID:
                self.selectedDataCursor = None
                self.slot_reportCursorPosition(None)
                
            else:
                self.slot_reportCursorPosition(self.selectedDataCursor.ID)
            
        else:
            self.slot_reportCursorPosition(None)
            #self.slot_reportCursorPosition(self.selectedDataCursor.ID)
            
        self._cursor_coordinates_text_=""
        self._update_coordinates_viewer_()

    @pyqtSlot()
    @safeWrapper
    def slot_removeSelectedCursor(self):
        if len(self._data_cursors_) == 0:
            return
        
        if isinstance(self.selectedDataCursor, SignalCursor):
            self.slot_removeCursor(self.selectedDataCursor.ID)
            self.selectedDataCursor = None
    
        self._cursor_coordinates_text_=""
        self._update_coordinates_viewer_()

    @pyqtSlot(str)
    @safeWrapper
    def slot_selectCursor(self, crsID=None):
        #print("SignalViewer.slot_selectCursor", crsID)
        if len(self._data_cursors_) == 0:
            return
        
        if crsID is None:
            if not isinstance(self.sender(), SignalCursor):
                return
            
            cursor = self.sender()
            crsID = cursor.ID
            
            if not crsID in self._data_cursors_: # make sure this is a cursor we know about
                return
            
            self.selectedDataCursor = cursor
            cursor.slot_setSelected(True) #  to update its appearance
            
            
        else:
            if crsID in self._data_cursors_ and not self._data_cursors_[crsID].isSelected:
                self.selectedDataCursor = self._data_cursors_[crsID]
                self._data_cursors_[crsID].slot_setSelected(True)
                
        for cid in self._data_cursors_:
            if cid != crsID:
                self._data_cursors_[cid].slot_setSelected(False)
                
        if isinstance(self.selectedDataCursor, SignalCursor):
            self.slot_reportCursorPosition(self.selectedDataCursor.ID)
                
    @pyqtSlot(str)
    @safeWrapper
    def slot_deselectCursor(self, crsID=None):
        if len(self._data_cursors_) == 0:
            return
        
        if crsID is None:
            if not isinstance(self.sender(), SignalCursor):
                return
            
            cursor = self.sender()
            crsID = cursor.ID
            
            if not crsID in self._data_cursors_: # make sure this is a cursor we know about
                return
            
            self.selectedDataCursor = None
            cursor.slot_setSelected(False)
            
        else:
            if crsID in self._data_cursors_:
                cursor = self._data_cursors_[crsID]
                cursor.slot_setSelected(False)
                
                self.selectedDataCursor = None
                
    @pyqtSlot(str)
    @pyqtSlot(bool)
    @safeWrapper
    def slot_editCursor(self, crsId=None, choose=False):
        if len(self._data_cursors_) == 0:
            return
        
        cursor = None
        
        if crsId is None:
            cursor = self.selectedDataCursor # get the selected cursor if no ID given
                
        else:
            cursor = self.dataCursor(crsId) # otherwise try to get cursor with given ID
            
        # if neither returned a valid cursor, then 
        if cursor is None:
            if not choose:
                cursor = self.sender() # use the sender() only when not choosing
            
            if not isinstance(cursor, SignalCursor): # but if sender is not a cursor then force making a choice
                cursor = None
                choose = True
        
        if cursor is not None: # we actually did get a cursor in the end, 
            if crsId is None:
                crsId = cursor.ID # make sure we also have its id
                
        initialID = crsId
                
        if choose:
            d = qd.QuickDialog(self, "Edit cursor")
            cursorComboBox = qd.QuickDialogComboBox(d, "Select cursor:")
            cursorComboBox.setItems([c for c in self._data_cursors_])
            
            d.cursorComboBox = cursorComboBox
            
            d.cursorComboBox.connectIndexChanged(partial(self._slot_updateCursorEditorDlg_, d=d))
        
        else:
            d = qd.QuickDialog(self, "Edit cursor %s" % crsId)
        
        namePrompt = qd.StringInput(d, "Name:")
        namePrompt.variable.setClearButtonEnabled(True)
        namePrompt.variable.redoAvailable=True
        namePrompt.variable.undoAvailable=True
        
        d.namePrompt = namePrompt
       
        if cursor is not None:
            if cursor.cursorTypeName in ("vertical", "crosshair"):
                promptX = qd.FloatInput(d, "X coordinate:")
                promptX.variable.setClearButtonEnabled(True)
                promptX.variable.redoAvailable=True
                promptX.variable.undoAvailable=True

                d.promptX = promptX
            
                promptXWindow = qd.FloatInput(d, "Horizontal window size:")
                promptXWindow.variable.setClearButtonEnabled(True)
                promptXWindow.variable.redoAvailable=True
                promptXWindow.variable.undoAvailable=True

                d.promptXWindow = promptXWindow
            
            if cursor.cursorTypeName in ("horizontal", "crosshair"):
                promptY = qd.FloatInput(d, "Y coordinate:")
                promptY.variable.setClearButtonEnabled(True)
                promptY.variable.redoAvailable=True
                promptY.variable.undoAvailable=True

                d.promptY = promptY
            
                promptYWindow = qd.FloatInput(d, "Vertical window size:")
                promptYWindow.variable.setClearButtonEnabled(True)
                promptYWindow.variable.redoAvailable=True
                promptYWindow.variable.undoAvailable=True

                d.promptYWindow = promptYWindow
                
        else:
            promptX = qd.FloatInput(d, "X coordinate:")
            promptX.variable.setClearButtonEnabled(True)
            promptX.variable.redoAvailable=True
            promptX.variable.undoAvailable=True

            d.promptX = promptX
        
            promptXWindow = qd.FloatInput(d, "Horizontal window size:")
            promptXWindow.variable.setClearButtonEnabled(True)
            promptXWindow.variable.redoAvailable=True
            promptXWindow.variable.undoAvailable=True

            d.promptXWindow = promptXWindow
            
            promptY = qd.FloatInput(d, "Y coordinate:")
            promptY.variable.setClearButtonEnabled(True)
            promptY.variable.redoAvailable=True
            promptY.variable.undoAvailable=True

            d.promptY = promptY
        
            promptYWindow = qd.FloatInput(d, "Vertical window size:")
            promptYWindow.variable.setClearButtonEnabled(True)
            promptYWindow.variable.redoAvailable=True
            promptYWindow.variable.undoAvailable=True

            d.promptYWindow = promptYWindow
                
        if not isinstance(crsId, str): # populate dialog fields w/ data
            crsId = [c for c in self._data_cursors_.keys()][0]
            
        d.staysInAxesCheckBox = qd.CheckBox(d, "Stays in axis")
        d.followMouseCheckBox = qd.CheckBox(d, "Follow Mouse")
        d.showsValueCheckBox = qd.CheckBox(d, "Label shows value")
        
        self._slot_updateCursorEditorDlg_(crsId, d)
            
        if d.exec() == QtWidgets.QDialog.Accepted:
            if choose: # choose cursor as per dialog; otherwise cursor is set above
                crsId = cursorComboBox.text() 
                cursor = self.dataCursor(crsId)
                initialID = crsId
                
            if cursor is None: # bail out
                return
            
            name = d.namePrompt.text() # whe a name change is desired this would be different from the cursor's id
            
            if initialID is not None:
                if name is not None and len(name.strip()) > 0 and name != initialID: # change cursor id if new name not empty
                    cursor.ID = name
                    
                    if cursor.isVertical:
                        self.verticalSignalCursors.pop(initialID)
                        self.verticalSignalCursors[cursor.ID] = cursor
                        
                    elif cursor.isHorizontal:
                        self.horizontalSignalCursors.pop(initialID)
                        self.horizontalSignalCursors[cursor.ID] = cursor
                        
                    else:
                        self.crosshairSignalCursors.pop(initialID)
                        self.crosshairSignalCursors[cursor.ID] = cursor
                        
            if cursor.isVertical:
                cursor.x = d.promptX.value()
                cursor.xwindow = d.promptXWindow.value()
                
            elif cursor.isHorizontal:
                cursor.y = d.promptY.value()
                cursor.ywindow = d.promptYWindow.value()
                
            else:
                cursor.x = d.promptX.value()
                cursor.xwindow = d.promptXWindow.value()
                cursor.y = d.promptY.value()
                cursor.ywindow = d.promptYWindow.value()
                
            cursor.staysInAxes  = d.staysInAxesCheckBox.isChecked()
            cursor.followsMouse = d.followMouseCheckBox.isChecked()
            cursor.showsValue   = d.showsValueCheckBox.isChecked()
            
        if hasattr(d, "cursorComboBox"):
            d.cursorComboBox.disconnect()
                
        del d
    
    @pyqtSlot(str)
    @safeWrapper
    def _slot_updateCursorEditorDlg_(self, cid, d):
        if not isinstance(cid, str) or len(cid.strip()) == 0:
            if hasattr(d, "cursorComboBox"):
                if d.cursorComboBox.variable.count() == 0:
                    return
                
                else:
                    cid = d.cursorComboBox.variable.currentText()
                    
                    if len(cid) == 0:
                        cid = d.cursorComboBox.variable.itemText(0)
            
        c = self.dataCursor(cid)
            
        if not isinstance(c, SignalCursor):
            return
        
        if hasattr(d, "namePrompt"):
            d.namePrompt.setText(cid)
        
        if c.cursorType == "vertical":
            if hasattr(d, "promptX"):
                d.promptX.variable.setEnabled(True)
                d.promptX.setValue(c.x)
                
            if hasattr(d, "promptXWindow"):
                d.promptXWindow.variable.setEnabled(True)
                d.promptXWindow.setValue(c.xwindow)
                
            if hasattr(d, "promptY"):
                d.promptY.setValue(np.nan)
                d.promptY.variable.setEnabled(False)
                
            if hasattr(d, "promptYWindow"):
                d.promptYWindow.setValue(np.nan)
                d.promptYWindow.variable.setEnabled(False)
            
        elif c.cursorType == "horizontal":
            if hasattr(d, "promptX"):
                d.promptX.setValue(np.nan)
                d.promptX.variable.setEnabled(False)
                
            if hasattr(d, "promptXWindow"):
                d.promptXWindow.setValue(np.nan)
                d.promptXWindow.variable.setEnabled(False)
                
            if hasattr(d, "promptY"):
                d.promptY.variable.setEnabled(True)
                d.promptY.setValue(c.y)
                
            if hasattr(d, "promptYWindow"):
                d.promptYWindow.variable.setEnabled(True)
                d.promptYWindow.setValue(c.ywindow)
                
            
        else: # , ("crosshair"):
            if hasattr(d, "promptX"):
                d.promptX.variable.setEnabled(True)
                d.promptX.setValue(c.x)
                
            if hasattr(d, "promptXWindow"):
                d.promptXWindow.variable.setEnabled(True)
                d.promptXWindow.setValue(c.xwindow)
                
            if hasattr(d, "promptY"):
                d.promptY.variable.setEnabled(True)
                d.promptY.setValue(c.y)
                
            if hasattr(d, "promptYWindow"):
                d.promptYWindow.variable.setEnabled(True)
                d.promptYWindow.setValue(c.ywindow)
                
        if hasattr(d, "followMouseCheckBox"):
            d.followMouseCheckBox.setChecked(c.followsMouse)
            
        if hasattr(d, "staysInAxesCheckBox"):
            d.staysInAxesCheckBox.setChecked(c.staysInAxes)
            
        if hasattr(d, "showsValueCheckBox"):
            d.showsValueCheckBox.setChecked(c.showsValue)
            
    @pyqtSlot()
    @safeWrapper
    def slot_editSelectedCursor(self):
        if isinstance(self.selectedDataCursor, SignalCursor):
            self.slot_editCursor(crsId=self.selectedDataCursor.ID, choose=False)
    
    def testGlobalsFcn(self, workspace):
        """workspace is a dict as returned by globals() 
        """
        exec("a=np.eye(3)", workspace)
        
        
    @pyqtSlot()
    @safeWrapper
    def slot_cursorsToEpoch(self):
        """Creates a neo.Epoch from existing cursors and exports it to the workspace.
        The epoch is NOT embedded in the plotted data.
        """
        vertAndCrossCursors = collections.ChainMap(self.crosshairSignalCursors, self.verticalSignalCursors)
        
        if len(vertAndCrossCursors) == 0:
            QtWidgets.QMessageBox.warning(self,"Attach epoch to data",
                                          "No vertical or croshair cursors found")
            return
        
        elif len(vertAndCrossCursors) > 1:
            # dialog to select cursors
            if isinstance(self.selectedDataCursor, SignalCursor) and self.selectedDataCursor in vertAndCrossCursors.values():
                cseldlg = ItemsListDialog(self, itemsList = [c.name for c in vertAndCrossCursors.values()],
                                            title="Select cursors", 
                                            selectmode = QtWidgets.QAbstractItemView.ExtendedSelection,
                                            preSelected=self.selectedDataCursor.name)
            else:
                cseldlg = ItemsListDialog(self, itemsList = [c.name for c in vertAndCrossCursors.values()],
                                            title="Select cursors",
                                            selectmode = QtWidgets.QAbstractItemView.ExtendedSelection)
            ans = cseldlg.exec_()
            
            if ans != QtWidgets.QDialog.Accepted:
                return
            
            selItems = cseldlg.selectedItemsText
            
            if len(selItems) == 0:
                return
            
            cursors = [self.dataCursor(name) for name in selItems]
            
            if len(cursors) == 0:
                return
            
        
        else:
            cursors = [c for c in vertAndCrossCursors.values()]
            
        if self._scipyenWindow_ is not None:
            if hasattr(self.yData, "name") and isinstance(self.yData.name, str) and len(self.yData.name.strip()):
                name = "%s_Epoch" % self.yData.name
                
            else:
                name = "Epoch"
                
            d = qd.QuickDialog(self, "Make Epoch From Cursors:")
            d.promptWidgets = list()
            d.promptWidgets.append(qd.StringInput(d, "Name:"))
            d.promptWidgets[0].setText(name)
            
            d.promptWidgets[0].variable.setClearButtonEnabled(True)
            d.promptWidgets[0].variable.redoAvailable = True
            d.promptWidgets[0].variable.undoAvailable = True
            
            if d.exec() == QtWidgets.QDialog.Accepted:
                txt = d.promptWidgets[0].text()
                if isinstance(txt, str) and len(txt.strip()):
                    name=txt
                    
            cursors.sort(key=attrgetter('x')) # or key = lambda x: x.x

            epoch = self.cursorsToEpoch(*cursors, name=name, embed=False)
            
            if epoch is not None:
                self._scipyenWindow_.assignToWorkspace(name, epoch)
                
    @pyqtSlot()
    @safeWrapper
    def slot_cursorsToEpochInData(self):
        """Creates a neo.Epoch from current vertical/crosshair cursors.
        The Epoch is embedded in the plotted data.
        """
        vertAndCrossCursors = collections.ChainMap(self.crosshairSignalCursors, self.verticalSignalCursors)
        
        if len(vertAndCrossCursors) == 0:
            QtWidgets.QMessageBox.warning(self,"Attach epoch to data",
                                          "No vertical or croshair cursors found")
            return
        
        elif len(vertAndCrossCursors) > 1:
            # dialog to select cursors
            if isinstance(self.selectedDataCursor, SignalCursor) and self.selectedDataCursor in vertAndCrossCursors.values():
                cseldlg = ItemsListDialog(self, itemsList = [c.name for c in vertAndCrossCursors.values()],
                                               title="Select cursors", 
                                               selectmode = QtWidgets.QAbstractItemView.ExtendedSelection,
                                               preSelected=self.selectedDataCursor.name)
            else:
                cseldlg = ItemsListDialog(self, itemsList = [c.name for c in vertAndCrossCursors.values()],
                                                title="Select cursors",
                                                selectmode = QtWidgets.QAbstractItemView.ExtendedSelection)
            ans = cseldlg.exec_()
            
            if ans != QtWidgets.QDialog.Accepted:
                return
            
            selItems = cseldlg.selectedItemsText
            
            if len(selItems) == 0:
                return
            
            cursors = [self.dataCursor(name) for name in selItems]
            
#             print(cursors)
#             
            if len(cursors) == 0:
                return
            
            cursors.sort(key=attrgetter('x'))
            
            # else:
            #     cursors = [c for c in vertAndCrossCursors.values()]
                    
        if hasattr(self.yData, "name") and isinstance(self.yData.name, str) and len(self.yData.name.strip()):
            name = "%s_Epoch" % self.yData.name
            
        else:
            name ="Epoch"
        
        if isinstance(self.yData, (neo.Block, neo.Segment)) or (isinstance(self.yData, (tuple, list)) and all([isinstance(s, neo.Segment) for s in self.yData])):
            #print("prompt me")
            d = qd.QuickDialog(self, "Attach epoch to data")

            d.epochNamePrompt = qd.StringInput(d, "Epoch Name:")
            d.epochNamePrompt.variable.setClearButtonEnabled(True)
            d.epochNamePrompt.variable.redoAvailable = True
            d.epochNamePrompt.variable.undoAvailable = True
            d.epochNamePrompt.setText(name)
            
                
            d.toAllSegmentsCheckBox = qd.CheckBox(d, "Embed in all segments")
            d.toAllSegmentsCheckBox.setChecked(True)
            
            d.sweepRelativeCheckBox = qd.CheckBox(d, "Relative to each segment start")
            d.sweepRelativeCheckBox.setChecked(True)
            
            d.overwriteEpochCheckBox = qd.CheckBox(d, "Overwrite existing epochs")
            d.overwriteEpochCheckBox.setChecked(False);
            
            if d.exec() == QtWidgets.QDialog.Accepted:
                txt = d.epochNamePrompt.text()
                if isinstance(txt, str) and len(txt.strip()):
                    name = txt

                toAllSegments    = d.toAllSegmentsCheckBox.isChecked()
                relativeSweep    = d.sweepRelativeCheckBox.isChecked()
                overwriteEpoch   = d.overwriteEpochCheckBox.isChecked()
                
                self.cursorsToEpoch(*cursors, name=name, embed=True,
                                    all_segments = toAllSegments,
                                    relative_to_segment_start = relativeSweep,
                                    overwrite = overwriteEpoch)

        else:
            QtWidgets.QMessageBox.warning(self,"Attach epoch to data", 
                                          "Epochs can only be embedded in neo.Block and neo.Segment data.")
            
    @pyqtSlot()
    @safeWrapper
    def slot_cursorToEpochInData(self):
        vertAndCrossCursors = collections.ChainMap(self.crosshairSignalCursors, self.verticalSignalCursors)
        
        if len(vertAndCrossCursors) == 0:
            return
        
        if isinstance(self.yData, (neo.Block, neo.Segment)) or (isinstance(self.yData, (tuple, list)) and all([isinstance(s, neo.Segment) for s in self.yData])):
            d = qd.QuickDialog(self, "Make Epoch From SignalCursor:")
            d.promptWidgets = list()
            d.namePrompt = qd.StringInput(d, "Name:")
            
            d.epoch_name = "Epoch"
            
            if hasattr(self.yData, "name") and isinstance(self.yData.name, str) and len(self.yData.name.strip()):
                d.epoch_name = "%s_Epoch"
            
            if isinstance(self.selectedDataCursor, SignalCursor) and self.selectedDataCursor.cursorType in (SignalCursor.SignalCursorTypes.vertical, SignalCursor.SignalCursorTypes.crosshair):
                cursor = self.selectedDataCursor
                cursorNameField = None
                d.namePrompt.setText("%s from %s" % (d.epoch_name, cursor.ID))
                
            else:
                d.cursorComboBox = qd.QuickDialogComboBox(d, "Select cursor:")
                d.cursorComboBox.setItems([c.ID for c in vertAndCrossCursors.values()])
                d.cursorComboBox.conextIndexChanged(partial(self._slot_update_cursor_to_epoch_dlg, d=d))
                
            
            d.toAllSegmentsCheckBox = qd.CheckBox(d, "Propagate to all segments")
            d.toAllSegmentsCheckBox.setChecked(True)
            
            d.sweepRelativeCheckBox = qd.CheckBox(d, "Relative to each segment start")
            d.sweepRelativeCheckBox.setChecked(False)
            
            d.overwriteEpochCheckBox = qd.CheckBox(d, "Overwrite existing epochs")
            d.overwriteEpochCheckBox.setChecked(True);
            
            if d.exec() == QtWidgets.QDialog.Accepted:
                txt = d.namePrompt.text()
                if isinstance(txt, str) and len(txt.strip()):
                    name=txt
                    
                toAllSegments  = d.toAllSegmentsCheckBox.isChecked()
                relativeSweep  = d.sweepRelativeCheckBox.isChecked()
                overwriteEpoch = d. overwriteEpochCheckBox.isChecked()
                
            self.cursorsToEpoch(self.selectedDataCursor, name=name, embed=True, 
                                all_segments = toAllSegments,
                                relative_to_segment_start = relativeSweep,
                                overwrite = overwriteEpoch)
            
            #self.displayFrame() # called by cursorsToEpoch when embed is True
            
        else:
            QtWidgets.QMessageBox.warning(self,"Attach epoch to data", "Epochs can only be embedded in neo.Block and neo.Segment data.\n\nPlease use actions in 'Make epochs' sub-menu")
    
    @pyqtSlot()
    @safeWrapper
    def slot_epochInDataBetweenCursors(self):
        vertAndCrossCursors = collections.ChainMap(self.crosshairSignalCursors, self.verticalSignalCursors)
        
        if len(vertAndCrossCursors) < 2:
            a = 2 - len(vertAndCrossCursors)
            QtWidgets.QMessageBox.warning(self,"Attach epoch to data",
                                          f"Please add {a} vertical or crosshair {InflectEngine.plural('cursor', a)} first")
            return
        
        if isinstance(self.yData, (neo.Block, neo.Segment)):
            d = qd.QuickDialog(self, "Make Epoch From Interval Between Cursors:")
            #d = vigra.pyqt.qd.QuickDialog(self, "Make Epoch From Interval Between Cursors:")
            # d.promptWidgets = list()
            
            d.namePrompt=qd.StringInput(d, "Name:")
            d.namePrompt.setText("Epoch")
            
            d.c1Combo = qd.QuickDialogComboBox(d, "Select first cursor:")
            d.c1Combo.setItems([c for c in vertAndCrossCursors])
            d.c1Combo.setValue(0)
            
            d.c2Combo = qd.QuickDialogComboBox(d, "Select second cursor")
            d.c2Combo.setItems([c for c in vertAndCrossCursors])
            d.c2Combo.setValue(1)
            
            d.toAllSegmentsCheckBox = qd.CheckBox(d, "Embed in all segments")
            d.toAllSegmentsCheckBox.setChecked(True)
            
            d.sweepRelativeCheckBox = qd.CheckBox(d, "Relative to each segment start")
            d.sweepRelativeCheckBox.setChecked(True)
            
            
            d.overwriteEpochCheckBox = qd.CheckBox(d, "Overwrite existing epochs")
            d.overwriteEpochCheckBox.setChecked(False);
            
            if d.exec() == QtWidgets.QDialog.Accepted:
                name = d.namePrompt.text()
                
                if name is None or len(name) == 0:
                    return
                
                # c1ID = d.c1Prompt.text()
                c1ID = d.c1Combo.text()
                
                if c1ID is None or len(c1ID) == 0:
                    return
                
                c2ID = d.c2Combo.text()
                
                if c2ID is None or len(c2ID) == 0:
                    return
                
                c1 = self.dataCursor(c1ID)
                c2 = self.dataCursor(c2ID)
                
                if c1 is None or c2 is None:
                    return
                
                toAllSegments   = d.toAllSegmentsCheckBox.isChecked()
                relativeSweep   = d.sweepRelativeCheckBox.isChecked()
                overwriteEpoch  = d.overwriteEpochCheckBox.isChecked()
                
                epoch = self.epochBetweenCursors(c1, c2, name=name, embed=True, 
                                                 all_segments = toAllSegments,
                                                 relative_to_segment_start = relativeSweep,
                                                 overwrite = overwriteEpoch)
                
                self.sig_newEpochInData.emit()
                
                self.displayFrame()
                
    @pyqtSlot()
    @safeWrapper
    def _slot_update_cursor_to_epoch_dlg(self, cid, d):
        if not isinstance(cid, str) or len(cid.strip()) == 0:
            if hasattr(d, "cursorComboBox"):
                if d.cursorComboBox.variable.count() == 0:
                    return
                
                else:
                    cid = d.cursorComboBox.variable.currentText()
                    
                    if len(cid) == 0:
                        cid = d.cursorComboBox.variable.itemText(0)
            
        c = self.dataCursor(cid)
                
        if not isinstance(c, SignalCursor):
            return
        
        if c.cursorType not in (SignalCursor.SignalCursorTypes.vertical, SignalCursor.SignalCursorTypes.crosshair):
            return
        
        self.selectedDataCursor = c
        
        if hasattr(d, "namePrompt"):
            if hasattr(d, "epoch_name"):
                d.namePrompt.setText("%s from %s" % (d.epoch_name, cid))
                
            else:
                d.namePrompt.setText("%s from %s" % ("Epoch", cid))
        
    
    @pyqtSlot()
    @safeWrapper
    def slot_cursorToEpoch(self):
        vertAndCrossCursors = collections.ChainMap(self.crosshairSignalCursors, self.verticalSignalCursors)
        
        if len(vertAndCrossCursors) == 0:
            return
        
        if self._scipyenWindow_ is not None:
            d = qd.QuickDialog(self, "Make Epoch From SignalCursor:")
            d.promptWidgets = list()
            d.namePrompt = qd.StringInput(d, "Name:")
            
            d.epoch_name = "Epoch"
            
            if hasattr(self.yData, "name") and isinstance(self.yData.name, str) and len(self.yData.name.strip()):
                d.epoch_name = "%s_Epoch"
            
            if isinstance(self.selectedDataCursor, SignalCursor) and self.selectedDataCursor.cursorType in (SignalCursor.SignalCursorTypes.vertical, SignalCursor.SignalCursorTypes.crosshair):
                cursor = self.selectedDataCursor
                cursorNameField = None
                d.namePrompt.setText("%s from %s" % (d.epoch_name, cursor.ID))
                
            else:
                d.cursorComboBox = qd.QuickDialogComboBox(d, "Select cursor:")
                d.cursorComboBox.setItems([c.ID for c in vertAndCrossCursors.values()])
                d.cursorComboBox.conextIndexChanged(partial(self._slot_update_cursor_to_epoch_dlg, d=d))
                
            
            if d.exec() == QtWidgets.QDialog.Accepted:
                txt = d.namePrompt.text()
                if isinstance(txt, str) and len(txt.strip()):
                    name=txt
                    
            epoch = self.cursorsToEpoch(self.selectedDataCursor, name=name)
            
            if epoch is not None:
                self._scipyenWindow_.assignToWorkspace(name, epoch)
                
    
    @pyqtSlot()
    @safeWrapper
    def slot_epochBetweenCursors(self):
        if self._scipyenWindow_ is None:
            return
        
        vertAndCrossCursors = collections.ChainMap(self.crosshairSignalCursors, self.verticalSignalCursors)
        
        if len(vertAndCrossCursors) == 0:
            self.criticalMessage("Make Epoch between cursors", "This operation needs two vertical or crosshair cursors")
            return
        
        d = qd.QuickDialog(self, "Make Epoch From Interval Between Cursors:")
        d.promptWidgets = list()
        namePrompt=qd.StringInput(d, "Name:")
        namePrompt.setText("Epoch")
   
        c1Combo = qd.QuickDialogComboBox(d, "Select first cursor:")
        c1Combo.setItems([c for c in vertAndCrossCursors])
        c1Combo.setValue(0)
        
        c2Combo = qd.QuickDialogComboBox(d, "Select second cursor")
        c2Combo.setItems([c for c in vertAndCrossCursors])
        c1Combo.setValue(1)
        
        # c1Prompt = qd.StringInput(d, "SignalCursor 1 ID:")
        # c2Prompt = qd.StringInput(d, "SignalCursor 2 ID:")
        
        d.promptWidgets.append(namePrompt)
        d.promptWidgets.append(c1Combo)
        d.promptWidgets.append(c2Combo)
        
        if d.exec() == QtWidgets.QDialog.Accepted:
            name = namePrompt.text()
            if name is None or len(name) == 0:
                return
            
            c1ID = c1Combo.text()
            
            if c1ID is None or len(c1ID) == 0:
                return
            
            c2ID = c2Combo.text()
            
            if c2ID is None or len(c2ID) == 0:
                return
            
            c1 = self.dataCursor(c1ID)
            c2 = self.dataCursor(c2ID)
            
            if c1 is None or c2 is None:
                return
            
            epoch = self.epochBetweenCursors(c1, c2, name)
            
            if epoch is not None:
                name=epoch.name
                if name is None:
                    name = "epoch"
                    
                self._scipyenWindow_.assignToWorkspace(name, epoch)
        
    @safeWrapper
    def cursorsToEpoch(self, *cursors, name:typing.Optional[str] = None, embed:bool = False, all_segments:bool = True, relative_to_segment_start:bool=False, overwrite:bool = False):
        """Creates a neo.Epoch from a list of cursors
        
        Parameters:
        ===========
        
        *cursors: a sequence of vertical or crosshair cursors; possibly empty
            If empty, then the function uses whatever verticval & crosshair cursors are
            defined in the viewer. If no such cursors exist, then raises ValueError.
            
            Ideally, cursors are sorted by their X coordinate in ascending order.
            
        name: str (optional, default is None) name of the generated epoch
            When None, the name is constructed based on the "name" attribute of the
                plotted data. If plotted data does not have a name, the epoch will
                be given the generic name "Epoch"
                
                
        embed: bool, default is False. When True, the generated epoch will be 
            embedded in the plotted data. This requires that the plotted data is 
            able to collect (embed) neo.Epoch objects. Currently, this functionality
            is present only in neo.Segments. Therefore, the epochs can be embedded
            ONLY when plotted data is:
            a neo.Block object,
            a sequence (tuple, list) of neo.Segment objects,
            a neo.Segment object.
            
            If that is not the case, yet "embed" is True, then the functions 
            issues a warning. The epoch is still generated and is returned by the 
            function.
            
        all_segments: bool, default is True. This parameter is used only when
            "embed" is True and the plotted data support embedding of neo.Epoch 
            objects (see above).
            
            When False, and plotted data is a neo.Block with more than one Segment
            or a sequence of Segment objects, then the epoch will be collected in 
            the "epochs" attribute of the currently plotted Segment.
            
            When True, then the generated Epoch will be collected in the "epochs"
            attribute of all the Segment objects in the data.
            
            This parameter is ignored when plotted data is a neo.Block with
            one segment, a sequence containing a single neo.Segment, or just a
            neo.Segment, and when the plotted data does not support Epochs.
            
        relative_to_segment_start:bool, default is False
            When the signals in the neo.Block data have different start times in
            each segment, creating an Epoch in ALl segments from cursors defined 
            in a segment will result in the epochs in ALL other segments falling 
            OUTSIDE the time domain of the signals there.
        
            To avoid this, set relative_to_segment_start to True.
        
            Alternatively, one can modify the data time domain beforehand e.g., 
            by calling set_relative_time_start() so that signals in ALL segments 
            have the same t_start.
            
        overwrite: bool, default is False. This parameter is used only when
            "embed" is True and data supports embedding of neo.Epoch objects 
            (see above).
            
            When True, all pre-existing Epoch objects are replaced by the generated
            Epoch.
            
            When False, the generated Epoch is appended to the "epochs" collections
            in the plotted data.
            
        """
        
        if len(cursors) == 0:
            cursors = [c for c in collections.ChainMap(self.crosshairSignalCursors, self.verticalSignalCursors).values()]
        
            if len(cursors) == 0:
                raise ValueError("This functions requires at least one vertical or crosshair cursor to be defined")
            
            cursors.sort(key=attrgetter('x')) # or key = lambda x: x.x
                
        else:
            if any([c.cursorType not in (SignalCursor.SignalCursorTypes.vertical, SignalCursor.SignalCursorTypes.crosshair) for c in cursors]):
                raise ValueError("Expecting only vertical or crosshair cursors")
                
        if name is None or (isinstance(name, str) and len(name.strip())) == 0:
            if hasattr(self.yData, "name") and isinstance(self.yData.name, str) and len(self.yData.name.strip()):
                name = "%_Epoch" % self.yData.name
                
            else:
                name = "Epoch"
            
        if all_segments and relative_to_segment_start:
            # NOTE: 2022-10-22 22:02:50 - NO WE DON'T !!!'
            # we need this to figure out the units of the cursor's x coordinate, 
            # taken ad the units of the signal plotted in the cursor's host axis 
            # (PlotItem)
            #
            # For multi-axes cursors, we use the currently-selected axis !!!
            # cursor_axes = [self.axes.index(c.hostItem) if isinstance(c.hostItem, pg.PlotItem) else self.axes.index(self.currentAxis) for c in cursors]
            
            # NOTE 2022-10-21 23:13:36
            # when calculating segment t_start we use the minimum of `t_start` 
            # of signals and spiketrains ONLY, to avoid any existing events or
            # epochs that are out of the signal domain, in each segment
            if isinstance(self.yData, neo.Block):
                segments = self.yData.segments
            elif isinstance(self.yData, (tuple, list)) and all(isinstance(s, neo.Segment) for s in self.yData):
                segments = self.yData
            elif isinstance(self.yData, neo.Segment):
                segments = [self.yData]
                
            elif isinstance(self.yData, neo.core.basesignal.BaseSignal):
                if self.yData.segment is None:
                    return
                
                segments = [self.yData.segment]
                
            else:
                return
            
            if len(segments) == 0:
                return
                
            seg_starts = [segment_start(s) for s in segments]
            if not all(ss == seg_starts[0] for ss in seg_starts):
                epochs = list()
                current_seg_start = segment_start(segments[self.currentFrame])
                
                rel_starts = [c.x * current_seg_start.units - current_seg_start for c in cursors]
                # print(f"SignalViewer.cursorsToEpoch: rel_starts: {rel_starts}")
                for k, seg in enumerate(segments):
                    s_start = seg_starts[k]
                    epoch_tuples = [(s_start + rel_starts[i], cursors[i].xwindow*s_start.units, cursors[i].name) for i in range(len(cursors))]
                    seg_epoch = cursors2epoch(*epoch_tuples, name=name)
                    epochs.append(seg_epoch)
                    if embed:
                        if overwrite:
                            seg.epochs = [seg_epoch]
                        else:
                            seg.epochs.append(seg_epoch)
                            
                self.displayFrame()
                
                return epochs
                
        # FIXME/TODO: 2022-10-23 23:57:00
        # use self.FrameIndex[self.currentFrame] instead (that is because we'd
        # be adapting this to multi-frame indices as in LSCaT !!!)
        if isinstance(self.yData, neo.Block):
            # t_units = self.yData.segments[self.currentFrame].t_start.units
            t_units = self.yData.segments[self.frameIndex[self._current_frame_index_]].t_start.units
        elif isinstance(self.yData, (tuple, list)) and all(isinstance(s, neo.Segment) for s in self.yData):
            # t_units = self.yData[self.currentFrame].t_start.units
            t_units = self.yData[self.frameIndex[self._current_frame_index_]].t_start.units
        elif isinstance(self.yData, neo.Segment):
            t_units = self.yData.t_start.units
        elif isinstance(self.yData, neo.core.basesignal.BaseSignal):
            if self.yData.segment is None:
                return
            t_units = self.yData.times[0].units
        else:
            t_units = pq.s # reasonable default (although not necessarily always applicable !!!)
        
        epoch = cursors2epoch(*cursors, name=name, sort=True, units = t_units)
        
        if embed:
            if isinstance(self.yData, neo.Block):
                if len(self.yData.segments) == 0:
                    warnings.warn("Plotted data is a neo.Block without segments")
                    #return epoch
                
                elif len(self.yData.segments) == 1:
                    if overwrite:
                        self.yData.segments[0].epochs = [epoch]
                    else:
                        self.yData.segments[0].epochs.append(epoch)
                    
                else:
                    if all_segments:
                        for ndx in self.frameIndex:
                            if overwrite:
                                self.yData.segments[ndx].epochs = [epoch]
                                
                            else:
                                self.yData.segments[ndx].epochs.append(epoch)
                            
                    else:
                        if overwrite:
                            self.yData.segments[self.frameIndex[self._current_frame_index_]].epochs = [epoch]
                        else:
                            self.yData.segments[self.frameIndex[self._current_frame_index_]].epochs.append(epoch)
                            
            elif isinstance(self.yData, (tuple, list)) and all([isinstance(s, neo.Segment) for s in self.yData]):
                if len(self.yData) == 0:
                    warnings.warn("Plotted data is an empty sequence!")
                
                elif len(self.yData) == 1:
                    if overwrite:
                        self.yData[0].epochs = [epoch]
                    else:
                        self.yData[0].epochs.append(epoch)
                    
                else:
                    if all_segments:
                        for ndx in self.frameIndex:
                            if overwrite:
                                self.yData[ndx].epochs = [epoch]
                                
                            else:
                                self.yData[ndx].epochs.append(epoch)
                            
                    else:
                        if overwrite:
                            self.yData[self.rameIndex[self._current_frame_index_]].epochs = [epoch]
                        else:
                            self.yData[self.rameIndex[self._current_frame_index_]].epochs.append(epoch)
                            
            elif isinstance(self.yData, neo.Segment):
                if overwrite:
                    self.yData.epochs = [epoch]
                    
                else:
                    self.yData.epochs.append(epoch)
                    
            elif isinstance(self.yData, neo.core.basesignal.BaseSignal):
                if hasattr(self.yData, "segment") and isinstance(self.yData.segment, neo.Segment):
                    if overwrite:
                        self.yData.segment.epochs = [epoch]
                    else:
                        self.yData.segment.epocha.append(epoch)
                        
            else:
                warnings.warn("Epochs can only be embeded in neo.Segment objects (either stand-alone, collected in a tuple or list, or inside a neo.Block)")
                
            self.displayFrame()
                
        return epoch
    
    def cursorToEpoch(self, crs=None, name=None):
        """Creates a neo.Epoch from a single cursor
        DEPRECATED superceded by the new cursorsToEpoch
        """
        if crs is None:
            return
        
        if crs.isHorizontal:
            return
        
        if name is None:
            d = qd.QuickDialog(self, "Make Epoch From SignalCursor:")
            d.promptWidgets = list()
            d.promptWidgets.append(qd.StringInput(d, "Name:"))
            #d.promptWidgets.append(vigra.pyqt.qd.StringInput(d, "Name:"))
            d.promptWidgets[0].setText("Epoch from "+crs.ID)
            
            if d.exec() == QtWidgets.QDialog.Accepted:
                txt = d.promptWidgets[0].text()
                if txt is not None and len(txt)>0:
                    name=txt
                    
            else:
                return
            
        return cursors2epoch(crs, name=name)
        
    def epochBetweenCursors(self, c0:SignalCursor, c1:SignalCursor, name:typing.Optional[str]=None, embed:bool = False, all_segments:bool = True, relative_to_segment_start:bool=False, overwrite:bool = False):
        if c0.isHorizontal or c1.isHorizontal:
            return
        
        cursors = sorted([c0, c1], key=attrgetter('x'))
        
        if not isinstance(name, str) or len(name.strip()) == 0:
            if hasattr(self.yData, "name") and isinstance(self.yData.name, str) and len(self.yData.name.strip()):
                name = f"{self.yData.name}_Epoch"
            else:
                name = "Epoch"
                
        if all_segments and relative_to_segment_start:
            if isinstance(self.yData, neo.Block):
                segments = self.yData.segments
            elif isinstance(self.yData, (tuple, list)) and all(isinstance(s, neo.Segment) for s in self.yData):
                segments = self.yData
            else:
                return
            
            seg_starts = [segment_start(s) for s in segments]
            if not all(ss == seg_starts[0] for ss in seg_starts):
                current_seg_start = segment_start(segments[self.currentFrame])
                
                rel_starts = [c.x * current_seg_start.units - current_seg_start for c in cursors]
                
                epochs = list()
                for k, seg in enumerate(segments):
                    s_start = seg_starts[k]
                    times = [s_start + rel_starts[i] for i in range(len(cursors))]
                    duration = times[1]-times[0]
                    seg_epoch = neo.Epoch(times = np.array([times[0]]), durations=np.array([duration]),
                                            units = times[0].units,
                                            labels = np.array([f"From {cursors[0].name} to {cursors[1].name}"]),
                                            name=name)
                    epochs.append(seg_epoch)
                    if embed:
                        if overwrite:
                            seg.epochs = [seg_epoch]
                        else:
                            seg.epochs.append(seg_epoch)
                            
                self.displayFrame()
                return epochs
            
        # FIXME/TODO: 2022-10-23 23:58:06
        # see FIXME/TODO: 2022-10-23 23:57:00
        if isinstance(self.yData, neo.Block):
            # t_units = self.yData.segments[self.currentFrame].t_start.units
            t_units = self.yData.segments[self.frameIndex[self._current_frame_index_]].t_start.units
        elif isinstance(self.yData, (tuple, list)) and all(isinstance(s, neo.Segment) for s in self.yData):
            # t_units = self.yData[self.currentFrame].t_start.units
            t_units = self.yData[self.frameIndex[self._current_frame_index_]].t_start.units
        elif isinstance(self.yData, neo.Segment):
            t_units = self.yData.t_start.units
        elif isinstance(self.yData, neo.core.basesignal.BaseSignal):
            if self.yData.segment is None:
                return
            t_units = self.yData.times[0].units
        else:
            t_units = pq.s # reasonable default (although not necessarily always applicable !!!)
        
        epoch = neo.Epoch(times = np.array([cursors[0].x]), durations = np.array([cursors[1].x - cursors[0].x]),
                          units = t_units, labels = np.array([f"From {cursors[0].name} to {cursors[1].name}"]),
                          name = name)
        
        if embed:
            if isinstance(self.yData, neo.Block):
                if len(self.yData.segments) == 0:
                    warnings.warn("Plotted data is a neo.Block without segments")
                    #return epoch
                
                elif len(self.yData.segments) == 1:
                    if overwrite:
                        self.yData.segments[0].epochs = [epoch]
                    else:
                        self.yData.segments[0].epochs.append(epoch)
                    
                else:
                    if all_segments:
                        for ndx in self.frameIndex:
                            if overwrite:
                                self.yData.segments[ndx].epochs = [epoch]
                                
                            else:
                                self.yData.segments[ndx].epochs.append(epoch)
                            
                    else:
                        if overwrite:
                            self.yData.segments[self.frameIndex[self._current_frame_index_]].epochs = [epoch]
                        else:
                            self.yData.segments[self.frameIndex[self._current_frame_index_]].epochs.append(epoch)
                            
            elif isinstance(self.yData, (tuple, list)) and all([isinstance(s, neo.Segment) for s in self.yData]):
                if len(self.yData) == 0:
                    warnings.warn("Plotted data is an empty sequence!")
                
                elif len(self.yData) == 1:
                    if overwrite:
                        self.yData[0].epochs = [epoch]
                    else:
                        self.yData[0].epochs.append(epoch)
                    
                else:
                    if all_segments:
                        for ndx in self.frameIndex:
                            if overwrite:
                                self.yData[ndx].epochs = [epoch]
                                
                            else:
                                self.yData[ndx].epochs.append(epoch)
                            
                    else:
                        if overwrite:
                            self.yData[self.rameIndex[self._current_frame_index_]].epochs = [epoch]
                        else:
                            self.yData[self.rameIndex[self._current_frame_index_]].epochs.append(epoch)
                            
            elif isinstance(self.yData, neo.Segment):
                if overwrite:
                    self.yData.epochs = [epoch]
                    
                else:
                    self.yData.epochs.append(epoch)
                    
            elif isinstance(self.yData, neo.core.basesignal.BaseSignal):
                if hasattr(self.yData, "segment") and isinstance(self.yData.segment, neo.Segment):
                    if overwrite:
                        self.yData.segment.epochs = [epoch]
                    else:
                        self.yData.segment.epocha.append(epoch)
                        
            else:
                warnings.warn("Epochs can only be embeded in neo.Segment objects (either stand-alone, collected in a tuple or list, or inside a neo.Block)")
                
            self.displayFrame()
                
        return epoch
    
        
#         if name is None:
#             d = qd.QuickDialog(self, "Make Epoch From The Interval Between Two Cursors:")
#             #d = vigra.pyqt.qd.QuickDialog(self, "Make Epoch From Interval Between Two Cursors:")
#             d.promptWidgets = list()
#             d.promptWidgets.append(qd.StringInput(d, "Name:"))
#             #d.promptWidgets.append(vigra.pyqt.qd.StringInput(d, "Name:"))
#             d.promptWidgets[0].setText("Epoch")
#             
#             if d.exec() == QtWidgets.QDialog.Accepted:
#                 txt = d.promptWidgets[0].text()
#                 if txt is not None and len(txt)>0:
#                     name=txt
#                     
#             else:
#                 return
        
        # return neo.Epoch(times = np.array([cursors[0].x])*pq.s,
        #                  durations = np.array([cursors[1].x - cursors[0].x]) * pq.s,
        #                  units = pq.s, labels=np.array(["From %s to %s" % (cursors[0].ID, cursors[1].ID)], dtype="S"),
        #                  name=name)
    
    def setPlotStyle(self, val):
        if val is None:
            self.plotStyle = "plot"
        elif isinstance(val, str):
            self.plotStyle = val
        else:
            raise ValueError("Plot style must be a string with a valid matplotlib drawing function")
            
        self.displayFrame()
        #self._plotOverlayFrame_()
        
    @safeWrapper
    def setAxisTickFont(self, value: (QtGui.QFont, type(None)) = None):
        for item in self.plotItems:
            for ax_dict in item.axes.values():
                ax_dict["item"].setStyle(tickFont=value)
                
    @safeWrapper
    def _parse_data_new_(self, x, y, frameIndex, frameAxis, signalChannelAxis, signalIndex, signalChannelIndex, irregularSignalIndex, irregularSignalChannelAxis, irregularSignalChannelIndex, separateSignalChannels):
        """Sets up the data model, essentially -- "interprets" the data 
        structure such that plotting of different types of objects containing
        numeric data sequences is made possible.
        
        These objects can be:
        
        1) numpy arrays and specialized objects derived from
        numpy arrays such as quantities, neo signals (which are derived from 
        quantities), vigra arrays, but also vigra kernels, and python sequences 
        of numbers.
        
        2) containers of (1) (at the moment only containers from 
        neo library are supported, e.g.Block and Segment)
        
        TODO: Pandas dataframes and series
        """
        if y is None:
            if x is not None:  # only the data variable Y is passed, 
                y = x
                x = None  # argument (X) and the expected Y will be None by default
                            # here we swap these two variables and we end up with X as None
                
            else:
                warngins.warn("I need something to plot")
                return False
            
        if isinstance(y, (tuple, list)) or hasattr(y, "__iter__"): # second condition to cover for new things like neo.SpikeTrainList (v >= 0.10.0)
            # python sequence of stuff to plot
            # TODO 2020-03-08 11:05:06
            # code for sequence of neo.SpikeTrain, and sequence of neo.Event
            self.separateSignalChannels         = separateSignalChannels
            self.signalChannelAxis              = signalChannelAxis 

            if np.all([isinstance(i, vigra.filters.Kernel1D) for i in y]):
                self._plotEpochs_(clear=True)
                self.frameIndex = range(len(y))
                self._number_of_frames_ = len(self.frameIndex)
                self.signalIndex = 1
                self.dataAxis = 0
                self.signalChannelAxis = 1 
                xx, yy = [kernel2array(i) for i in y]
                
                if x is None:
                    x = xx
                    
                else: 
                    # x might be a single 1D array (or 2D array with 2nd 
                    # axis a singleton), or a list of such arrays
                    # in this case force x as a list also!
                    if isinstance(x, np.ndarray):
                        if x.ndim  == 2:
                            # this effectively requires all arrays to have a common domain
                            if x.shape[1] > 1:
                                raise TypeError("When 'y' is a list, 'x' must be a vector")
                            
                    elif isinstance(x,(tuple, list)) and \
                        not all([isinstance(x_, np.ndarray) and x_.ndim <= 2 for x_ in x]):
                            raise TypeError("'x' has incompatible shape %s" % x.shape)
                                    
                    else:
                        raise TypeError("Invalid x specified")
                    
                self.xData = x
                    
                self.yData = yy
                
            elif all([isinstance(i, neo.Segment) for i in y]):
                # NOTE: 2019-11-30 09:35:42 
                # treat this as the segments attribute of a neo.Block
                #self.dataAnnotations = [{s.name: s.annotations} for s in y]
                self.frameIndex = range(len(y))
                self.frameAxis = None
                
                self._data_frames_ = len(y)
                self._number_of_frames_ = len(self.frameIndex)
                
                self.separateSignalChannels         = False
                
                self.dataAxis = 0
                self.signalChannelAxis = 1
                self.signalChannelIndex = None
                self.irregularSignalChannelAxis     = None
                self.irregularSignalChannelIndex    = None
                
                self.xData = None
                self.yData = y
                
                self.signalIndex                    = signalIndex
                self.irregularSignalIndex           = irregularSignalIndex
                
            elif all([isinstance(i, neo.Block) for i in y]):
                # NOTE 2021-01-02 11:31:05
                # treat this as a sequence of segments, but do NOT concatenate
                # the blocks!
                self.xData = None
                self.yData = y 
                self.frameAxis = None
                self.dataAxis = 0
                self.signalChannelAxis = 1 
                self.signalChannelIndex = None
                self.irregularSignalChannelAxis = None
                self.irregularSignalChannelIndex = None
                self.separateSignalChannels = False
                self._data_frames_ = tuple(accumulate((len(b.segments) for b in self.yData)))[-1]
                self.frameIndex = range(self._data_frames_)
                self._number_of_frames_ = len(self.frameIndex)
                self.signalIndex                    = signalIndex
                self.irregularSignalIndex           = irregularSignalIndex
                
            elif all([isinstance(i, (neo.core.AnalogSignal, neo.core.IrregularlySampledSignal,  
                                     DataSignal, IrregularlySampledDataSignal)) for i in y]):
                # NOTE: 2019-11-30 09:42:27
                # Treat this as a segment, EXCEPT that each signal is plotted
                # in its own frame. This is because in a generic container
                # there can be signals with different domains (e.g., t_start
                # & t_stop).
                # If signals must be plotted on stacked axes in the same 
                # frame then either collected them in a segment, or concatenate
                # them in a 3D numpy array.
                #self.dataAnnotations = [{s.name: s.annotations} for s in y]
                self.dataAxis = 0
                self.signalChannelAxis = 1
                self.frameAxis = None
                self.frameIndex = range(len(y))
                self._data_frames_ = len(y)
                self._number_of_frames_ = len(self.frameIndex)
                self.signalIndex = 0
                
                self.xData = None
                self.yData = y
                
            elif all([isinstance(i, (neo.Epoch, DataZone, neo.Event, DataMark)) for i in y]):
                #self.dataAnnotations = [{s.name: s.annotations} for s in y]
                self.yData = y
                self.dataAxis = 0
                self.signalChannelAxis = 1
                self.frameIndex = range(1)
                self._number_of_frames_ = 1
                self._plotEpochs_(self.yData) # why?
            
            elif all([isinstance(i, neo.SpikeTrain) for i in y]):
                #self.dataAnnotations = [{s.name: s.annotations} for s in y]
                self.yData = y
                self.dataAxis = 0
                self.signalChannelAxis = 1
                self._plotEpochs_(self.yData)
                self.frameIndex = range(1)
                self._number_of_frames_ = 1
            
            elif all([isinstance(i, np.ndarray) and i.ndim <= 2 for i in y]):
                if signalChannelAxis is None:
                    raise TypeError("signalChannelAxis must be specified for 2D arrays")
                
                self.signalChannelAxis = signalChannelAxis
                self.dataAxis = 1 if self.signalChannelAxis == 0 else 0
                    
                self._plotEpochs_(clear=True)
                self.frameIndex = range(len(y))
                self._number_of_frames_ = len(self.frameIndex)
                self.signalIndex = 1

                if x is None:
                    x = [np.linspace(0, y_.shape[self.dataAxis], y_.shape[self.dataAxis], endpoint=False)[:,np.newaxis] for y_ in y]
                    
                else: 
                    # x might be a single 1D array (or 2D array with 2nd 
                    # axis a singleton), or a list of such arrays
                    # in this case force x as a list also!
                    if isinstance(x, np.ndarray):
                        if x.ndim  == 2:
                            if x.shape[1] > 1:
                                raise TypeError("for 'x', the 2nd axis of a 2D array must have shape of 1")
                            
                    elif isinstance(x,(tuple, list)) and \
                        not all([isinstance(x_, np.ndarray) and x_.ndim <= 2 for x_ in x]):
                            raise TypeError("'x' has incompatible shape %s" % self.xData.shape)

                    else:
                        raise TypeError("Invalid x specified")
                    
                self.xData = x
                self.yData = y
            
            else:
                raise TypeError("Can only plot a list of 1D vigra filter kernels, 1D/2D numpy arrays, or neo-like signals")
            
        else:
            print("_parse_data_", type(y))
            dct = self._interpret_signal(y, x_data=x, 
                                         frameAxis=frameAxis,
                                         frameIndex=frameIndex,
                                         signalChannelAxis=signalChannelAxis,
                                         signalChannelIndex=signalChannelIndex,
                                         irregularSignalChannelAxis = irregularSignalChannelAxis,
                                         irregularSignalChannelIndex = irregularSignalChannelIndex,
                                         signalIndex = signalIndex,
                                         irregularSignalIndex = irregularSignalIndex,
                                         separateSignalChannels = separateSignalChannels
                                         )
            
            for k,v in dct.items():
                if k == "x_data":
                    self.xData = v
                else:
                    setattr(self, k, v)
            #raise TypeError("Plotting is not implemented for %s data types" % type(self.yData).__name__)
            
        return True

    @safeWrapper
    def _parse_data_old_(self, x, y, frameIndex, frameAxis, signalChannelAxis, signalIndex, signalChannelIndex, irregularSignalIndex, irregularSignalChannelAxis, irregularSignalChannelIndex, separateSignalChannels):
        """Sets up the data model, essentially -- "interprets" the data 
        structure such that plotting of different types of objects containing
        numeric data sequences is made possible.
        
        These objects can be:
        
        1) numpy arrays and specialized objects derived from
        numpy arrays such as quantities, neo signals (which are derived from 
        quantities), vigra arrays, but also vigra kernels, and python sequences 
        of numbers.
        
        2) containers of (1) (at the moment only containers from 
        neo library are supported, e.g.Block and Segment)
        
        TODO: Pandas dataframes and series
        """
        # default param values
        self.separateSignalChannels = False
        self.signalChannelAxis = 1
        self.dataAxis = 0 # data as column vectors
            
        if isinstance(y, neo.baseneo.BaseNeo):
            self.globalAnnotations = {type(y).__name__ : y.annotations}
        
        if isinstance(y, neo.core.Block):
            # self.xData = None # domain is contained in the signals inside the block
            self.yData = y
            self.docTitle = getattr(y, "name", None)
            
            # NOTE : 2022-01-17 14:17:23
            # if frameIndex was passed, then self._number_of_frames_ might turn
            # out to be different than self._data_frames_!
            self._data_frames_ = self._number_of_frames_ = len(self.yData.segments)
            
            #### BEGIN NOTE 2019-11-24 22:32:46: 
            # no need for these so reset to None
            # but definitely used when self.yData is a signal, not a container of signals!
            self.dataAxis = 0 # data as column vectors
            self.signalChannelAxis = 1 
            self.frameAxis = None
            self.signalChannelIndex = None
            self.irregularSignalChannelAxis = None
            self.irregularSignalChannelIndex = None
            self.separateSignalChannels = False
            #### END NOTE 2019-11-24 22:32:46: 

            #### BEGIN NOTE: 2019-11-22 08:37:38 
            # the following need checking inside _plotSegment_()
            # to adapting for the particular segment
            self.signalIndex  = signalIndex
            self.irregularSignalIndex  = irregularSignalIndex
            #### END NOTE: 2019-11-22 08:37:38 
            
            # NOTE: this is used when self.yData is a structured signal object,
            # but not for a block, channel index, or segment

            # NOTE: 2021-11-13 19:00:47
            # ChannelIndex is out of neo
                    
            # NOTE: 2022-01-17 14:18:30 see NOTE : 2022-01-17 14:17:23
            # SeparateSignalChannels only has effect when y is a single neo 
            # signal or a numpy ndarray. It is forcefully set to False for
            # neo.Block, neo.Segment, or sequence of neo.Segment, neo signals,
            # or numpy ndarray objects.
            # NOTE: As a reminder: when separateSignalChannels is True, each
            # channel will be plotted on a different axis system (i.e., in its
            # own pyqtgraph.plotItem); separateSignalChannels does NOT affect the
            # frames layout!
            self.frameIndex = normalized_index(self._data_frames_, frameIndex)
            self._number_of_frames_ = len(self.frameIndex)
            
            #### BEGIN NOTE: 2019-11-21 23:09:52 
            # TODO/FIXME handle self.plot_start and self.plot_start
            # each segment (sweep, or frame) can have a different time domain
            # so when these two are specified it may result in an empty plot!!!
            #### END NOTE: 2019-11-21 23:09:52 

        elif isinstance(y, neo.core.Segment):
            # self.xData = None # NOTE: x can still be supplied externally
            self.yData = y
            self.docTitle = getattr(y, "name", None)
            self._plotEpochs_(clear=True)
            
            # one segment is one frame
            self.frameAxis = None
            self._number_of_frames_ = 1
            self._data_frames_ = 1
            self.frameIndex = range(self._number_of_frames_) 
            
            # only used for individual signals
            self.dataAxis = 0 # data as column vectors
            self.signalChannelAxis = 1 
            self.signalChannelIndex = None
            
            # see NOTE: 2019-11-22 08:37:38  - the same principle applies
            self.signalIndex = signalIndex
            self.irregularSignalIndex = irregularSignalIndex
            
            self.irregularSignalChannelAxis = None
            self.irregularSignalChannelIndex = None
            self.separateSignalChannels = False
            
        elif isinstance(y, (neo.core.AnalogSignal, DataSignal)):
            # self.xData = None
            self.yData = y
            self.docTitle = getattr(y, "name", None)
            
            # NOTE: no need for these as there is only one signal
            self.signalIndex = None
            self.irregularSignalIndex = None
            self.irregularSignalChannelIndex = None
            # treat these as a 2D numpy array, but with the following conditions:
            # signalChannelAxis is always 1
            # frameAxis is 1 or None: the data itself has only one logical "frame"
            # but the signal's channels MAY be plotted one per frame, if frameAxis is one
            # signal domain is already present, although it can be overridden
            # by user-supplied "x" data
            
            self.dataAxis = 0 # data as column vectors
            
            if not isinstance(frameAxis, (int, type(None))):
                raise TypeError("For AnalogSignal and DataSignal, frameAxis must be an int or None; got %s instead" % type(frameAxis).__name__)

            self.signalChannelAxis = 1
            self.signalChannelIndex = normalized_sample_index(self.yData.as_array(), self.signalChannelAxis, signalChannelIndex)
            
            # dealt with by displayframe()
            self.separateSignalChannels = separateSignalChannels
            
            self._data_frames_ = 1
            
            if frameAxis is None:
                self.frameAxis = None
                self._number_of_frames_ = 1
                self.frameIndex = range(self._number_of_frames_)
                
            else:
                frameAxis = normalized_axis_index(self.yData.as_array(), frameAxis)
                if frameAxis != self.signalChannelAxis:
                    raise ValueError("For structured signals, frame axis and signal channel axis must be identical")
                
                self.frameAxis = frameAxis
                self.frameIndex = normalized_sample_index(self.yData.as_array(), self.frameAxis, frameIndex)
                self._number_of_frames_ = len(self.frameIndex)
                
        elif isinstance(y, (neo.core.IrregularlySampledSignal,  IrregularlySampledDataSignal)):
            # self.xData = None
            self.yData = y
            self.docTitle = getattr(y, "name", None)
            self.frameIndex = range(1)
            self.dataAxis = 0 # data as column vectors
            self.signalChannelAxis = 1
            #self.signalIndex = range(1)
            
            self._number_of_frames_ = 1
            self._data_frames_ = 1
            
            self.signalIndex = None
            self.irregularSignalIndex  = None
            self.signalChannelIndex    = None
            
            self.irregularSignalChannelIndex    = irregularSignalChannelIndex
            self.separateSignalChannels         = separateSignalChannels

        elif isinstance(y, neo.core.SpikeTrain): # plot a SpikeTrain independently of data
            # self.xData = None
            self.yData = y
            self.docTitle = getattr(y, "name", None)
            self.dataAxis = 0 # data as column vectors
            self.signalChannelAxis = 1
            self.frameIndex = range(1)
            self._number_of_frames_ = 1
            #self._plotSpikeTrains_(y) # let displayFrame do it
        
        elif isinstance(y, (neo.core.Event, DataMark )): # plot an event independently of data
            # self.xData = None
            self.yData = y
            self.docTitle = getattr(y, "name", None)
            self.dataAxis = 0 # data as column vectors
            self.signalChannelAxis = 1
            self.frameIndex = range(1)
            self._number_of_frames_ = 1
            #self._plotEvents_(y) # let displayFrame do it
            #NOTE: EventArray has been ditched as of neo v. 0.5.0
        
        elif isinstance(y, (neo.core.Epoch, DataZone)): # plot an Epoch independently of data
            #self.dataAnnotations.append({"Epoch %s" % y.name: y.annotations})
            #pass # delegated to displayFrame()
            # self.xData = None
            self.yData = y
            self.docTitle = getattr(y, "name", None)
            self.dataAxis = 0 # data as column vectors
            self.signalChannelAxis = 1
            self.frameIndex = range(1)
            self._number_of_frames_ = 1
            #self._plotEpochs_(self.yData) # let displayFrame do it
            
            if self._docTitle_ is None or (isinstance(self._docTitle_, str) and len(self._docTitle_.strip()) == 0):
                #because these may be plotted as an add-on so we don't want to mess up the title
                if isinstance(y.name, str) and len(y.name.strip()) > 0:
                    self._doctTitle_ = y.name
                    
                else:
                    self._docTitle_ = self.yData.name
        
        elif isinstance(y, vigra.filters.Kernel1D):
            self.xData, self.yData = kernel2array(y)
            self.docTitle = "Vigra Kernel 1D"
            self._plotEpochs_(clear=True)
            
            self.dataAxis = 0 # data as column vectors
            self.frameIndex = range(1)
            self.signalIndex = range(1)
            self._number_of_frames_ = 1
            
        elif isinstance(y, np.ndarray): # NOTE: this includes vigra.VigraArray, quantities.Quantity
            # NOTE 2021-11-14 12:39:57
            # a 'channel' is a data vector (usually, & not necesarily,
            # a column vector); even when plotted on the same axis
            # system, a large number of channels cann bring a huge 
            # performance penalty; therefore it is important to know
            # the data layout.
            #
            # For a 2d array (matrix), the signals (or signal channels) may be 
            # arranged either in vertical (column) or horizontal (row) vectors.
            # 
            # data as row vectors: 
            #   axis 0 is the 'channels' axis; 
            #   axis 1 is the 'data' axis:
            # 
            #           Data sample
            #           0   … n
            # row 0:    x₀₀ … x₀ₙ ↦ channel 0
            # row 1:    x₁₁ … x₁ₙ ↦ channel 1
            #
            # data as column vectors (the DEFAULT):
            #   axis 0 if the 'data' axis
            #   axis 1 is the 'channels' axis
            # 
            #           Channel
            #           0   … n
            # row 0:    x₀₀ … x₀ₙ ↦ data sample 0
            # row 1:    x₁₁ … x₁ₙ ↦ data sample 1
            #
            #
            # A 3D array is considered as being made of a series of 2D signals
            # which are "slices"
            #
            if y.ndim > 3: 
                raise ValueError('\nCannot plot data with more than 3 dimensions\n')
            
            self.xData = None
            self.yData = y
            self.docTitle = "Numpy array"
            
            if self.yData.ndim == 1: # one frame, one channel
                self.dataAxis = 0 # data as column vectors
                self.signalChannelAxis = None
                self.frameAxis = None
                self.frameIndex = range(1)
                self.signalChannelIndex = range(1)
                self._number_of_frames_ = 1
                self.dataAxis = 0 # there is only one axis
                self.separateSignalChannels = False
                
            elif self.yData.ndim == 2:
                if not isinstance(frameAxis, (int, str, vigra.AxisInfo, type(None))):
                    raise TypeError("Frame axis must be None, or an int (vigra arrays also accept str or AxisInfo); got %s instead" % type(frameAxis))
                
                if not isinstance(signalChannelAxis, (int, str, vigra.AxisInfo, type(None))):
                    raise TypeError("Signal channel axis must be None, or an int (vigra arrays also accept str or AxisInfo); got %s instead" % type(signalChannelAxis))
                
                if signalChannelAxis is None:
                    if isinstance(self.yData, vigra.VigraArray):
                        # this is the only case where we allow for signalChannelAxis
                        # to be omitted from the call parameters (for array with 
                        # at least 2D)
                        if self.yData.channelIndex == self.yData.ndim: # no real channel axis
                            # take columns as signal channels (consider self.yData as
                            # an horizontal vector of column vectors)
                            signalChannelAxis = 1
                        else:
                            signalChannelAxis = self.yData.channelIndex
                    else:
                        signalChannelAxis = 1 # by defult we consider channels as column vectors
                        
                        
                        # raise TypeError("signalChannelAxis must be specified when plotting numpy arrays")
                    
                else:
                    if isinstance(self.yData, vigra.VigraArray):
                        if isinstance(signalChannelAxis, str) and signalChannelAxis.lower().strip() != "c":
                                warnings.warn("Channel axis index is specificed by non-canonical axis key %s" % signalChannelAxis)
                                
                        elif isinstance(signalChannelAxis, vigra.AxisInfo):
                            if signalChannelAxis.key.lower().strip() != "c":
                                warnings.warn("Channel axis index is specificed by non-canonical axis key %s" % signalChannelAxis)
                                
                    signalChannelAxis = normalized_axis_index(self.yData, signalChannelAxis)
                    
                self.signalChannelAxis = signalChannelAxis
                
                self.dataAxis = 1 if self.signalChannelAxis == 0 else 0
                
                self.signalChannelIndex = normalized_sample_index(self.yData, self.signalChannelAxis, signalChannelIndex)
                
                self.separateSignalChannels = separateSignalChannels
                
                if frameAxis is None:
                    self.frameAxis = None
                    self._data_frames_ = 1
                    self._number_of_frames_ = 1
                    self.frameIndex = range(self._number_of_frames_)
                    
                    # NOTE: 2019-11-22 12:25:42
                    # _plotNumpyArray_() decides whether to plot all channels overlaid in
                    # one plotItem, or plot each channel in its own plotItem
                    # with plot items stacked in a column in one frame
                        
                else:
                    # for 2D arrays, specifying a frameAxis forces the plotting 
                    # of one channel per frame
                    frameAxis = normalized_axis_index(self.yData, frameAxis)
                    
                    # NOTE: 2019-11-22 14:24:16
                    # for a 2D array it does not make sense to have frameAxis
                    # different from signalChannelAxis
                    if frameAxis != self.signalChannelAxis:
                        raise ValueError("For 2D arrays, frame axis index %d must be the same as the channel axis index (%d)" % (frameAxis, self.signalChannelAxis))
                    
                    self.frameAxis = frameAxis
                    
                    self.frameIndex = normalized_sample_index(self.yData, self.frameAxis, frameIndex)
                    
                    self._number_of_frames_ = len(self.frameIndex)
                    
                    # NOTE: displayframe() should now disregard separateSignalChannels
                
            elif self.yData.ndim == 3: 
                # NOTE: 2019-11-22 13:33:27
                # both frameAxis and signalChannelAxis MUST be specified
                #
                if frameAxis is None:
                    raise TypeError("For 3D arrays the frame axis must be specified")
                
                if signalChannelAxis is None:
                    raise TypeError("for 3D arrays the signal channel axis must be specified")
                
                frameAxis = normalized_axis_index(self.yData, frameAxis)
                signalChannelAxis = normalized_axis_index(self.yData, signalChannelAxis)
                
                if frameAxis  ==  signalChannelAxis:
                    raise ValueError("For 3D arrays the index of the frame axis must be different from the index of the signal channel axis")
                
                self.frameAxis = frameAxis
                self.signalChannelAxis = signalChannelAxis
                
                axes = set([k for k in range(self.yData.ndim)])
                
                axes.remove(self.frameAxis)
                axes.remove(self.signalChannelAxis)
                
                self.frameIndex = normalized_sample_index(self.yData, self.frameAxis, frameIndex)
                
                self._number_of_frames_ = len(self.frameIndex)

                self.signalChannelIndex = normalized_sample_index(self.yData, self.signalChannelAxis, signalChannelIndex)
                
                self.dataAxis = list(axes)[0]

                # NOTE: 2019-11-22 14:15:46
                # diplayframe() needs to decide whether to plot all channels 
                # in the frame as overlaid curves in one plot item (when 
                # separateSignalChannels is False) or in a column of plot items
                # (when separateSignalChannels is True)
                self.separateSignalChannels = separateSignalChannels
                
            if x is not None:
                if isinstance(x, (tuple, list)):
                    if len(x) != self.yData.shape[self.dataAxis]:
                        raise TypeError("The supplied signal domain (x) must have the same size as the data axis %s" % self.dataAxis)
                    
                    self.xData = np.array(x)
                    
                elif isinstance(x, np.ndarray):
                    if not is_vector(x):
                        raise TypeError("The supplied signal domain (x) must be a vector")
                    
                    if len(x) != self.yData.shape[self.dataAxis]:
                        raise TypeError("The supplied signal domain (x) must have the same size as the data axis %s" % self.dataAxis)
                        
                    if is_column_vector(x):
                        self.xData = x
                        
                    else:
                        self.xData = x.T # x left unchanged if 1D
                        
                else:
                    raise TypeError("Signal domain (x) must be None, a Python iterable of scalars or a numpy array (vector)")
                
            self._plotEpochs_(clear=True)
                        
        elif isinstance(y, (tuple, list)) or hasattr(y, "__iter__"): # second condition to cover for new things like neo.SpikeTrainList (v >= 0.10.0)
            if len(y) == 0:
                self.clear()
                return
            # python sequence of stuff to plot
            # TODO 2020-03-08 11:05:06
            # code for sequence of neo.SpikeTrain, and sequence of neo.Event
            self.separateSignalChannels         = separateSignalChannels
            self.signalChannelAxis              = signalChannelAxis 

            if np.all([isinstance(i, vigra.filters.Kernel1D) for i in y]):
                self._plotEpochs_(clear=True)
                self.frameIndex = range(len(y))
                self._number_of_frames_ = len(self.frameIndex)
                self.signalIndex = 1
                self.dataAxis = 0
                self.signalChannelAxis = 1 
                xx, yy = [kernel2array(i) for i in y]
                
                if x is None:
                    x = xx
                    
                else: 
                    # x might be a single 1D array (or 2D array with 2nd 
                    # axis a singleton), or a list of such arrays
                    # in this case force x as a list also!
                    if isinstance(x, np.ndarray):
                        if x.ndim  == 2:
                            # this effectively requires all arrays to have a common domain
                            if x.shape[1] > 1:
                                raise TypeError("When 'y' is a list, 'x' must be a vector")
                            
                    elif isinstance(x,(tuple, list)) and \
                        not all([isinstance(x_, np.ndarray) and x_.ndim <= 2 for x_ in x]):
                            raise TypeError("'x' has incompatible shape %s" % x.shape)
                                    
                    else:
                        raise TypeError("Invalid x specified")
                    
                self.xData = x
                    
                self.yData = yy
                self.docTitle = "Vigra Kernel1D objects"
                
            elif all([isinstance(i, neo.Segment) for i in y]):
                # NOTE: 2019-11-30 09:35:42 
                # treat this as the segments attribute of a neo.Block
                #self.dataAnnotations = [{s.name: s.annotations} for s in y]
                self.frameIndex = range(len(y))
                self.frameAxis = None
                
                self._data_frames_ = len(y)
                self._number_of_frames_ = len(self.frameIndex)
                
                self.separateSignalChannels         = False
                
                self.dataAxis = 0
                self.signalChannelAxis = 1
                self.signalChannelIndex = None
                self.irregularSignalChannelAxis     = None
                self.irregularSignalChannelIndex    = None
                
                # self.xData = None
                self.yData = y
                self.docTitle = "Neo segments"
                
                self.signalIndex                    = signalIndex
                self.irregularSignalIndex           = irregularSignalIndex
                
            elif all([isinstance(i, neo.Block) for i in y]):
                # NOTE 2021-01-02 11:31:05
                # treat this as a sequence of segments, but do NOT concatenate
                # the blocks!
                # self.xData = None
                self.yData = y 
                self.frameAxis = None
                self.dataAxis = 0
                self.signalChannelAxis = 1 
                self.signalChannelIndex = None
                self.irregularSignalChannelAxis = None
                self.irregularSignalChannelIndex = None
                self.separateSignalChannels = False
                self._data_frames_ = tuple(accumulate((len(b.segments) for b in self.yData)))[-1]
                self.frameIndex = range(self._data_frames_)
                self._number_of_frames_ = len(self.frameIndex)
                self.signalIndex                    = signalIndex
                self.irregularSignalIndex           = irregularSignalIndex
                self.docTitle = "Neo blocks"
                
            elif all([isinstance(i, (neo.core.AnalogSignal, neo.core.IrregularlySampledSignal,  
                                     DataSignal, IrregularlySampledDataSignal)) for i in y]):
                # NOTE: 2019-11-30 09:42:27
                # Treat this as a segment, EXCEPT that each signal is plotted
                # in its own frame. This is because in a generic container
                # there can be signals with different domains (e.g., t_start
                # & t_stop).
                # If signals must be plotted on stacked axes in the same 
                # frame then either collected them in a segment, or concatenate
                # them in a 3D numpy array.
                #self.dataAnnotations = [{s.name: s.annotations} for s in y]
                self.dataAxis = 0
                self.signalChannelAxis = 1
                self.frameAxis = None
                self.frameIndex = range(len(y))
                self._data_frames_ = len(y)
                self._number_of_frames_ = len(self.frameIndex)
                self.signalIndex = 0
                
                # self.xData = None
                self.yData = y
                self.docTitle = "Neo signals"
                
            elif all([isinstance(i, (neo.Epoch, DataZone, neo.Event, DataMark)) for i in y]):
                #self.dataAnnotations = [{s.name: s.annotations} for s in y]
                self.yData = y
                self.docTitle = "Epochs and zones"
                self.dataAxis = 0
                self.signalChannelAxis = 1
                self.frameIndex = range(1)
                self._number_of_frames_ = 1
                self._plotEpochs_(self.yData) # why?
            
            elif all([isinstance(i, neo.SpikeTrain) for i in y]):
                #self.dataAnnotations = [{s.name: s.annotations} for s in y]
                self.yData = y
                self.dataAxis = 0
                self.signalChannelAxis = 1
                self._plotEpochs_(self.yData)
                self.frameIndex = range(1)
                self._number_of_frames_ = 1
            
            elif all([isinstance(i, np.ndarray) and i.ndim <= 2 for i in y]):
                if signalChannelAxis is None:
                    signalChannelAxis = 1 # the default
                    # raise TypeError("signalChannelAxis must be specified for 2D arrays")
                
                self.signalChannelAxis = signalChannelAxis
                self.dataAxis = 1 if self.signalChannelAxis == 0 else 0
                    
                self._plotEpochs_(clear=True)
                self.frameIndex = range(len(y))
                self._number_of_frames_ = len(self.frameIndex)
                self.signalIndex = 1

                # if x is None:
                #     x = [np.linspace(0, y_.shape[self.dataAxis], y_.shape[self.dataAxis], endpoint=False)[:,np.newaxis] for y_ in y]
                    
                if x is not None:
                    # x might be a single 1D array (or 2D array with 2nd 
                    # axis a singleton), or a list of such arrays
                    # in this case force x as a list also!
                    if isinstance(x, np.ndarray):
                        if x.ndim  == 2:
                            if x.shape[1] > 1:
                                raise TypeError("for 'x', the 2nd axis of a 2D array must have shape of 1")
                            
                    elif isinstance(x,(tuple, list)) and \
                        not all([isinstance(x_, np.ndarray) and x_.ndim <= 2 for x_ in x]):
                            raise TypeError("'x' has incompatible shape %s" % self.xData.shape)

                    else:
                        raise TypeError("Invalid x specified")
                    
                self.xData = x
                self.yData = y
                self.docTitle = "Numpy arrays"
            
            else:
                raise TypeError("Can only plot a list of 1D vigra filter kernels, 1D/2D numpy arrays, or neo-like signals")
            
        else:
            raise TypeError("Plotting is not implemented for %s data types" % type(self.yData).__name__)

        with self.observed_vars.hold_trait_notifications():
            self.observed_vars["x"] = self.xData
            self.observed_vars["y"] = self.yData
            
        return True
    
    _parse_data_ = _parse_data_old_
    
    @safeWrapper
    def _set_data_(self, x:(neo.core.baseneo.BaseNeo, DataSignal, IrregularlySampledDataSignal, TriggerEvent, TriggerProtocol, vigra.filters.Kernel1D, np.ndarray, tuple, list, type(None)),  y:(neo.core.baseneo.BaseNeo, DataSignal, IrregularlySampledDataSignal, TriggerEvent, TriggerProtocol, vigra.filters.Kernel1D, np.ndarray, tuple, list, type(None)) = None, doc_title:(str, type(None)) = None, frameAxis:(int, str, vigra.AxisInfo, type(None)) = None, signalChannelAxis:(int, str, vigra.AxisInfo, type(None)) = None, frameIndex:(int, tuple, list, range, slice, type(None)) = None, signalIndex:(str, int, tuple, list, range, slice, type(None)) = None, signalChannelIndex:(int, tuple, list, range, slice, type(None)) = None, irregularSignalIndex:(str, int, tuple, list, range, slice, type(None)) = None, irregularSignalChannelAxis:(int, type(None)) = None, irregularSignalChannelIndex:(int, tuple, list, range, slice, type(None)) = None, separateSignalChannels:bool = False, interval:(tuple, list, neo.Epoch, type(None)) = None, plotStyle:str = "plot", showFrame:int = None, *args, **kwargs):
        self.plot_start = None
        self.plot_stop = None
        
            
        self.epoch_plot_options["epoch_pen"] = kwargs.pop("epoch_pen", None)
        self.epoch_plot_options["epoch_brush"] = kwargs.pop("epoch_brush", None)
        self.epoch_plot_options["epoch_hoverPen"] = kwargs.pop("epoch_hoverPen", None)
        self.epoch_plot_options["epoch_hoverBrush"] = kwargs.pop("epoch_hoverBrush", None)
        
        self.plot_args = args
        self.plot_kwargs = kwargs

        if isinstance(interval, neo.Epoch):
            # NOTE: 2019-01-24 21:05:34
            # use only the first epoch in an Epoch array (if there are several elements)
            if len(interval) > 0:
                self.plot_start = interval.times[0]
                self.plot_stop = self.plot_start + interval.durations[0]
                
        elif isinstance(interval, (tuple, list)) and all([isinstance(t, (numbers.Real, pq.Quantity)) for t in interval]):
            self.plot_start = interval[0]
            self.plot_stop = interval[1]
            
        try:
            # remove gremlins from previous plot
            self._plotEpochs_(clear=True)
            self._cached_epochs_.pop(self.currentFrame, None)

            dataOK = self._parse_data_(x=x,
                                       y=y, 
                                       frameIndex=frameIndex, 
                                       frameAxis=frameAxis,
                                       signalIndex=signalIndex, 
                                       signalChannelAxis=signalChannelAxis,
                                       signalChannelIndex=signalChannelIndex,
                                       irregularSignalIndex=irregularSignalIndex,
                                       irregularSignalChannelAxis=irregularSignalChannelAxis,
                                       irregularSignalChannelIndex=irregularSignalChannelIndex,
                                       separateSignalChannels=separateSignalChannels)
            
            self.actionDetect_Triggers.setEnabled(check_ephys_data_collection(self.yData))
                        
            if isinstance(showFrame, int):
                if showFrame < 0:
                    showFrame = 0
                    
                elif showFrame > self._number_of_frames_:
                    showFrame = self._number_of_frames_ - 1
                    
                self._current_frame_index_ = showFrame
                    

            if plotStyle is not None and isinstance(plotStyle, str):
                self.plotStyle = plotStyle
                
            elif style is not None and isinstance(style, str):
                self.plotStyle = style
                
            self.framesQSlider.setMaximum(self._number_of_frames_ - 1)
            self.framesQSpinBox.setMaximum(self._number_of_frames_ - 1)

            self.framesQSlider.setValue(self._current_frame_index_)
            self.framesQSpinBox.setValue(self._current_frame_index_)
            
            self.nFramesLabel.setText("of %d" % self._number_of_frames_)
            
            if dataOK:
                self.displayFrame()
            else:
                warnings.warn(f"Could not parse the data x: {x}, y: {y}")
                return
            
            self._update_annotations_()
            
            # NOTE: 2022-11-01 10:37:06
            # overwrites self.docTitle set by self._parse_data_
            if isinstance(doc_title, str) and len(doc_title.strip()):
                self.docTitle = doc_title
                
            
            self.frameChanged.emit(self._current_frame_index_)

        except Exception as e:
            traceback.print_exc()
            
    @safeWrapper
    def setData(self, x:(neo.core.baseneo.BaseNeo, DataSignal, IrregularlySampledDataSignal, TriggerEvent, TriggerProtocol, vigra.filters.Kernel1D, np.ndarray, tuple, list, type(None)), /, y:(neo.core.baseneo.BaseNeo, DataSignal, IrregularlySampledDataSignal, TriggerEvent, TriggerProtocol, vigra.filters.Kernel1D, np.ndarray, tuple, list, type(None)) = None,doc_title:(str, type(None)) = None, frameAxis:(int, str, vigra.AxisInfo, type(None)) = None, signalChannelAxis:(int, str, vigra.AxisInfo, type(None)) = None, frameIndex:(int, tuple, list, range, slice, type(None)) = None, signalIndex:(str, int, tuple, list, range, slice, type(None)) = None, signalChannelIndex:(int, tuple, list, range, slice, type(None)) = None, irregularSignalIndex:(str, int, tuple, list, range, slice, type(None)) = None, irregularSignalChannelAxis:(int, type(None)) = None, irregularSignalChannelIndex:(int, tuple, list, range, slice, type(None)) = None, separateSignalChannels:bool = False, interval:(tuple, list, neo.Epoch, type(None)) = None, plotStyle:str = "plot", get_focus:bool = False, showFrame = None, *args, **kwargs):
        """Plot data in SignalViewer.
        
        Positional parameters:
        ----------------------
        x: data to plot.
    
            This can be either:
            • neo.core.baseneo.BaseNeo (i.e. all neo object types, AND 
                Scipyen types: DataSignal, IrregularlySampledDataSignal, 
                DataZone, DataMark, TriggerEvent, TriggerProtocol), 
        
            • vigra.filters.Kernel1D,
        
            • numpy ndarray
    
            • a sequence (tuple, list) of the types listed above, or
        
            • None
        
            With the exception of unspecialized ndarray (from the numpy package)
            and unspecialized Quantity arrays (from the quantities package) the 
            data objects of the types shown above typically supply their own data
            domain (e.g. the `times` attribute of neo objects) or the data domain
            is implicit (e.g. int he case of vigra Kernel1D objects).
        
            For unsepcialized numpy arrays and Quantity arrays the implicit data
            domain is the sample index, although it can be specifies in the `x`
            parameter.
        
            When the data to plot is passed separately as the `y` parameter (see
            below), then `x` represents the (custom) domain of the data,
        
            Explicit examples:
        
            sigview = SignalViewer() # create a SignalViewer object
        
            # Plot some data that specifies its own data domain (see above):
        
            sigview.plot(data)
        
            # Plot some numeric data that does NOT specify its own domain (e.g.,
            # an unspecialized numpy ndarray):
        
            sigview.plot(data) # uses the implicit domain i.e., the sample number
        
            # Alternatively, supply a domain created manually, e.g.:
        
            x_data = [k for k in range(len(data))]
        
            sigview.plot(x_data, data) # in this case, supply the custom-made
                domain, followed by the data to plot
        
        Named parameters:
        ------------------
        y: object (type as above) or None (default);
            When `y` is None, then `x` is used as the data to be plotted (possibly
            supplying its own domain, see above)
        
            Otherwise, `y` is considered to contain the data to be plotted, and
            `x` (which cannot be None) is the domain of the data.
            
            See above for examples.
            
        doc_title: str or None = name of the data (will also appear in the 
            window title).
        
            NOTE: neo data types usually supply their own data_name in their
            `name` attribute. In this case, data_name is taken from there, unless
            it is given here explicitly (thus overrulling the object `name`)
            
        frameAxis: int, str, vigra.AxisInfo or None (default)
            When plot data is a numpy array, it indicates the axis along which
            the data "frames" are defined
    
            NOTE: VigraArray objects are python wrappers to C++ arrays, with
            numpy array methods; they are "seen" by the Python interpreter as 
            specialized numpy arrays. For these objects, frameAxis may also be
            may also be specified as a string (axis "key") or AxisInfo object.
        
            See vigranumpy documentation for details.
                
            When plot data is a structured signal object (e.g. neo.AnalogSignal,
            datatypes.DataSignal) frameAxis may be used to plot the signal's
            channels in separate frames.
            
            The default (None) indicates that plot data should not be considered
            as organized in frames (unless it is a collection of signals, 
            see below).
                
            frameAxis is disregarded in the case of structured signal collections
            such as neo.Block (which already contains several data frames or 
            "segments") and neo.Segment (which encapsulates one frame).
            
        signalChannelAxis: int, str, vigra.AxisInfo or None (default) - indicates
            the axis along which the signal channels are defined.
            
            When None, it indicates that data is NOT organized in channels. This
            is useful for numpy arrays where a 2D array can represent a collection
            of several single-channel signals, instead of a single multi-channel
            signal.
            
            The typical type of this parameter is an int (for numpy arrays and 
            also for structured signal types).
            
            Vigra arrays can also accept str (axis "key") or AxisInfo objects.
            
            For neo.Block and neo.Segments, this parameter affects only the
            regularly sampled signals.
            
        irregularSignalChannelAxis: int, None (default) - the index of the axis
            along which the signal channels are defined. Only used for irregularly
            sampled signals.
        
        frameIndex: int, tuple, list, range, slice, or None (default) = selection
            of frame indices for plot data organized in frames.
            
            When None (default) all data frames will be plotted; the user can 
            navigate across the frames using the spinner and slider at the 
            bottom of the window.
            
        signalIndex: str, int, tuple, list, range, slice, None (default) = 
            selection of regularly signals to plot, from a structured signal collections 
            (neo.Block, neo.Segment), or iterables of structured signals.
            
            When None, all available signals in the collection will be plotted.
            
            Otherwise, signals to be plotted will be selected according to the
            type of signalIndex:
            a) int -- the integral index of the signals in the collection
            b) str -- the name of the signal -- applies to collections of neo 
                signals, datatypes signals, pandas Series and pandas DataFrame,
                or any array-like object with a "name" attribute.
            c) tuple/list  -- all elements must be int or str (if the signal
             has a "name" attribute)
             
            d) range, slice -- the range or slice object must resolve to a 
                sequence of integral indices, valid for the signal collection
                
            For neo.Segment and neo.Block, this parameters affects only the
            (sub)set of regularly sampled signals (neo.AnalogSignal, 
            datatypes.DataSignal).
            
        irregularSignalIndex: str, int, tuple, list, range, slice, None (default)
            used for neo.Block and neo.Segment - selects irregular signals for 
            plotting. Irregular signals are neo.IrregularlySampledSignal and
            datatpes.IrregularlySampledDataSignal
            
        signalChannelIndex: int, tuple, list, range, slice, None (default)
            selects a subset of signal channels. When None (default) all the
            available channels are plotted.
            
        irregularSignalChannelIndex: int, tuple, list, range, slice, None (default)
            selects a subset of signal channels, in irregularly sampled signals.
            When None (default) all the available channels are plotted.
            
        separateSignalChannels: bool, default False; When True, signal channels
            are plotted in separate axes and/or frames, depending on the data 
            layout.
            
        interval: tuple, list, neo.Epoch, None (default) -- pair of scalars or Python Quantity
            that specify the interval in the signal domain (start, stop) over 
            which the signal(s)  are to be plotted. 
            
            When None (default), the entire signals are plotted.
            
            CAUTION: When interval is not None, the functions assumes:
            a) that the two values in the pair are in increasing order
            b) that the interval falls within the domain of all signals in the 
                data
        
        channelIndex: DEPRECATED neo.ChannelIndex object, or None (default) - used to select
            which data channel to plot (NOT to be confused with signal channels)
        
        plotStyle: str, default is "plot" -- keyword reserved for development
        
        get_focus: bool - Flag to indicate if viewer is to be shown (i.e. made the 
            active window).
            
            Default is True. May be set to False to keep an already visible 
            viewer window in the background (useful when the windowing system of 
            the operating system does not implement a focus stealing mechanism)
            
        showFrame: int (optional default is None)
            When given, this is the index of the frame (among the frames available
            for display, see NOTE below) to be displayed upon plotting the new
            data.
            
            When None, the viewer automatically displays the first frame available
            
            NOTE: Data frames vs displayed frames.
            Commonly, the number of frames available for display equals the number
            of data frames; however, plotting can be restricted to a subset of
            the data frames by passing a frame selection in the 'frameIndex'
            parameter, described above.
                
        
        *args, **kwargs -- further parameters and keyword parameters passed on 
            to PyQtGraph plot function.
        
        When the data to plot is a structured signal collection, the parameter 
        supplied in *args and **kwargs apply to ALL individual plots for the 
        signals in the signal collection.
        
        """ 
        
        # NOTE: 2022-01-18 08:39:13
        # Intuitively, one would pass both 'x' (the data domain) and y (the data
        # itself) in order for the viewer to plot 'y' vs 'x' (similar to matplotlib 
        # plot API, etc). 
        # However, particular data types such as instances of neo.AnalogSignal
        # already 'embed' the data 'domain' (or the 'x') therefore only 'y' (the
        # instance of neo.AnalogSignal, in this example) needs be passed.
        # We generalize this and make 'x' optional; when 'y' is a more generic
        # sequence of numeric data (e.g., numpy ndarray, or even a list or tuple)
        # and None is passed for 'x', the domain 'x' implicitly is the running
        # sample number (the 'index') into the sequence 'y'.
        #
        # The following 4 lines try to guess whether only 'y' was passed
        if y is None:
            if x is not None:  # only the data variable Y is passed, 
                y = x
                x = None  # argument (X) and the expected Y will be None by default
                            # here we swap these two variables and we end up with X as None
                
            else:
                #warngins.warn("I need something to plot")
                return
            
        self._set_data_(x,y, 
                        doc_title = doc_title,
                        frameAxis = frameAxis, 
                        signalChannelAxis = signalChannelAxis,
                        frameIndex = frameIndex, 
                        signalIndex = signalIndex, 
                        SignalChannelIndex = signalChannelIndex,
                        irregularSignalIndex = irregularSignalIndex, 
                        irregularSignalChannelAxis = irregularSignalChannelAxis,
                        irregularSignalChannelIndex = irregularSignalChannelIndex,
                        separateSignalChannels = separateSignalChannels,
                        interval = interval,
                        plotStyle = plotStyle,
                        showFrame = showFrame,
                        **kwargs)
        
        if not self.isVisible():
            self.setVisible(True)
            
        if get_focus:
            self.activateWindow()
            
        ## NOTE: 2020-09-25 10:07:37
        ## Calls ScipyenViewer setData() which in turn delegates to self._set_data_()
        #super().setData(*args, **kwargs)
            
    @property
    def currentFrame(self):
        return self._current_frame_index_
    
    @currentFrame.setter
    def currentFrame(self, val:typing.Union[int, type(MISSING), type(NA), type(None), float]):
        """ Programmatically sets up the index of the displayed frame.
        CAUTION: emits self.frameChanged signal
        """
        missing = (isinstance(self._missing_frame_value_, (int, float)) and val == self._missing_frame_value_) or \
            self._missing_frame_value_ in (MISSING, NA) and val is self._missing_frame_value_
        
        if missing or val not in self.frameIndex:
            self.setDataDisplayEnabled(False)
            return
        else:
            self.setDataDisplayEnabled(True)
            
        self._current_frame_index_ = int(val)
        
        # NOTE: 2018-09-25 23:06:55
        # recipe to block re-entrant signals in the code below
        # cleaner than manually connecting and re-connecting
        # and also exception-safe
        
        signalBlockers = [QtCore.QSignalBlocker(widget) for widget in \
            (self.framesQSpinBox, self.framesQSlider)]
        
        self.framesQSpinBox.setValue(self._current_frame_index_)
        self.framesQSlider.setValue(self._current_frame_index_)


        self.displayFrame()
        self.frameChanged.emit(self._current_frame_index_)

    @property
    def plotItemsWithLayoutPositions(self):
        """ A zipped list of tuples (PlotItem, grid coordinates).
        Aliased to the axesWithLayoutPositions property
        
        The structure is derived from the dictionary
        pyqtgraph.graphicsItems.GraphicsLayout.GraphicsLayout.items:
        
        [   (PlotItem, [(row, col)]), 
            ...
        ]
        
        The elements in the zipped list are SORTED by the value of row (see above)
        in increasing order
        
        Read-only
        
        """
        items = [item for item in self.signalsLayout.items.items()] 
        return sorted(items, key=lambda x: x[1][0])
    
    @property
    def plotItems(self):
        px = self.plotItemsWithLayoutPositions
        
        if len(px):
            ret, _ = zip(*px)
            
        else:
            ret = list()
        
        return ret
    
    @property
    def axesWithLayoutPositions(self):
        """Alias to self.plotItemsWithLayoutPositions property (syntactic sugar)
        """
        return self.plotItemsWithLayoutPositions
    
    @property
    def axes(self):
        """The list of axes (PlotItem objects).
        
        Alias to self.plotItems property
        """
        return self.plotItems
    
#     def axis(self, index: int):
#         """The axis (PlotItem) at the specified index.
#         
#         If index is not valid, returns None.
#         
#         """
#         try:
#             plotitem = self.signalsLayout.getItem(index,0)
#             
#         except:
#             pass
#         
#         return plotitem
    
    @safeWrapper
    def plotItem(self, index: int):
        """Returns the axis (PlotItem) at the specified index.
        
        Does the same thing as self.axis(index) but with the overhead of 
        iterating over the items in self.signalsLayout (a pg.GraphicsLayout).
        
        Raises an exception if index is not valid.
        """
        return self.axes[index]
    
    def axis(self, index):
        """Calls self.plotItem(index) -- syntactic sugar
        """
        return self.plotItem(index)
    
    @property
    def selectedPlotItem(self):
        """Alias to currentPlotItem"""
        return self.currentPlotItem
    
    @selectedPlotItem.setter
    def selectedPlotItem(self, index):
        self.selectedPlotItem = index
        
    @property
    def currentPlotItem(self):
        """Reference to the selected (current) axis (PlotItem).
        
        The setter counterpart sets the current plot item to be a reference to
        the PlotItem with the specified index.
        """
        return self._current_plot_item_
    
    @currentPlotItem.setter
    def currentPlotItem(self, index: typing.Union[int, pg.PlotItem]):
        """Sets the current plot item to the one at the specified index.
        
        Index: int index or a plotitem
        """
        plotitems_coords = self.axesWithLayoutPositions # a reference, so saves computations
        
        if len(plotitems_coords) == 0:
            #QtWidgets.QMessageBox.critical(self, "Set current axes:", "Must plot something first!")
            self._current_plot_item_ = None
            self._current_plot_item_index_ = -1
            return False
        
        plotitems, _ = zip(*plotitems_coords)
        
        if isinstance(index, int):
            if index not in range(len(plotitems)):
                raise TypeError(f"Expecting an int between 0 and {len(plotitems)}; got a {index}  instead")
        
        #system_palette = QtGui.QGuiApplication.palette()
        #default_border_color = self.axis(0).vb.border.color()
        
            self._current_plot_item_ = plotitems[index]
            self._current_plot_item_index_ = index
            
        elif isinstance (index, pg.PlotItem) and index in self.axes:
            self._current_plot_item_ = index
            self._current_plot_item_index_ = plotitems.index(index)
            
        else:
            return
            
        self._setAxisIsActive(self._current_plot_item_, True)
        self._statusNotifyAxisSelection(index)
        
        for ax in self.axes:
            if ax is not self._current_plot_item_:
                self._setAxisIsActive(ax, False)
        
        # self.statusBar().showMessage(f"Selected axes: {index} ({self._plot_names_.get(index)})")
        
    @property
    def currentAxisIndex(self):
        return self._current_plot_item_index_
    
    @currentAxisIndex.setter
    def currentAxisIndex(self, index:int):
        if index not in range(-len(self.axes), len(self.axes)):
            raise ValueError(f"index {index} out range for {len(self.axes)}")
        
        self.currentAxis = self.axes[index]
        
    @property
    def currentAxis(self):
        return self.currentPlotItem
    
    @currentAxis.setter
    def currentAxis(self, axis:typing.Union[int, pg.PlotItem]):
        self.currentPlotItem = axis
        
    @property
    def selectedAxis(self):
        """Alias to currentAxis"""
        return self.currentAxis
    
    @property
    def plotNames(self):
        """A dict of int keys mapped to axes names (str).
        The keys are the indices of the axes (with 0 being the first axis from 
        the top).
        The values (names) are the 'name' attribute (if it exists) of the plotted 
        signal in the corresponding axis, or an empty string
        """
        return self._plot_names_
    
    @selectedAxis.setter
    def selectedAxis(self, index):
        self.currentAxis = index
        
    def _statusNotifyAxisSelection(self, index=None):
        if index is None:
            index = self._current_plot_item_index_
        elif not isinstance(index, int) or index not in range(len(self.axes)):
            return
        
        plot_name = self._plot_names_.get(index, "")
                
        if isinstance(plot_name, str) and len(plot_name.strip()):
            self.statusBar().showMessage(f"Selected axes: {index} ({plot_name})")
            
        else:
            self.statusBar().showMessage(f"Selected axes: {index}")
            
    def _setAxisIsActive(self, axis, active:False):
        lblStyle = {"color":"#FF5500" if active else "#000000"}
        # activeAxBorderPen = QtGui.QPen(QtGui.QColor("#AAAAAA"))
        lbl = axis.axes["left"]["item"].labelText
        if active:
            if any([s not in lbl for s in ("<B>", "</B>")]):
                lbl = "<B>%s</B>" % lbl
                
            # axis.vb.border.setStyle(activeAxBorderPen)
            # print(f"{self.__class__.__name__}._setAxisIsActive {self.axes.index(axis)}")
            self.sig_axisActivated.emit(self.axes.index(axis))
        else:
            if lbl.startswith("<B>") and lbl.endswith("</B>"):
                lbl = lbl[3 : lbl.find("</B>")]
                
            # axis.vb.border.setStyle(QtCore.Qt.NoPen)
            
        axis.setLabel("left", lbl, **lblStyle)
        
    def dataCursor(self, ID):
        """Not to be confused with the Qt method self.cursor() !!!
        """
        if len(self._data_cursors_) and ID in self._data_cursors_:
            return self._data_cursors_[ID]
        
    def cursorWindow(self, crsID):
        if self._hasCursor_(crsID):
            #print(crsID)
            return (self._data_cursors_[crsID].xwindow, self._data_cursors_[crsID].ywindow)
        else:
            raise Exception("SignalCursor %s not found" % crsID)
        
    def cursorX(self, crsID):
        if self._hasCursor_(crsID):
            return self._data_cursors_[crsID].x
        else:
            return None
        
    def cursorY(self, crsID):
        if self._hasCursor_(crsID):
            return self._data_cursors_[crsID].y

    def selectedCursorWindow(self):
        if self.selectedDataCursor is not None:
            return (self._data_cursors_[self.selectedDataCursor.ID].xwindow, self._data_cursors_[self.selectedDataCursor.ID].ywindow)
        
    def cursorsInAxis(self, index=None):
        """Returns a list of SignalCursor objects in a PlotItem or spanning all plot items.
        
        List is empty if no cursor exists.
        
        index: None (default) or int
        
            when None, return the cursors in the selected PlotItem (if not None, else
                in the signals layout scene i.e., the vertical cursors that span all the plot items)
                
            when an int valid values are in the semi-open interval [-1, len(self.axesWithLayoutPositions) )
                when index  == -1 then returns the cursors that span all the plot items
                otherwise, returns the cursors in the PlotItem with the specified index
        
        """
        hostitem = None
        
        if index is None:
            if self.currentPlotItem is None:
                hostitem = self.signalsLayout.scene()
                
            else:
                hostitem = self.currentPlotItem
                
        elif isinstance(index, str) and index == "all":
            hostitem = self.signalsLayout.scene()
            
        elif isinstance(index, int):
            if index >=0:
                if index >= len(self.axesWithLayoutPositions):
                    raise ValueError("index must be between -1 and %d; got %d instead" % (len(self.axesWithLayoutPositions), index))
                
                hostitem = self.axis(index)
                
            else:
                hostitem = self.signalsLayout.scene()
                
        elif isinstance(index, pg.PlotItem):
            hostitem = index
            
        if hostitem is not None: # may be None if there is no scene, i.e. no plot item
            ret =  [c for c in self._data_cursors_.values() if c.hostItem is hostitem]
        
        else:
            ret = list()
            
        return ret
                   
    @property
    def verticalCursors(self):
        """List of vertical signal cursors
        """
        return [c for c in self.verticalSignalCursors.values()]
    
    @property
    def horizontalCursors(self):
        """List of horizontal signal cursors
        """
        return [c for c in self.horizontalSignalCursors.values()]
    
    @property
    def crosshairCursors(self):
        """List of croshair signal cursors
        """
        return [c for c in self.crosshairSignalCursors.values()]
    
    @pyqtSlot(bool)
    def _slot_setCursorsShowValue(self, val):
        self.cursorsShowValue = val is True
            
    @pyqtSlot()
    def _slot_setCursorLabelPrecision(self):
        dlg = qd.QuickDialog()
        wdg = QtWidgets.QSpinBox(parent=dlg)
        wdg.setValue(self.cursorLabelPrecision)
        dlg.addLabel("Precision")
        dlg.addWidget(wdg)
        if dlg.exec() > 0:
            val = wdg.value()
            
            self.cursorLabelPrecision = val
            
    @pyqtSlot()
    def _slot_setCursorHoverColor(self):
        self._gui_chose_cursor_color_("hover")
            
    @pyqtSlot()
    def _slot_setVerticalCursorColors(self):
        self._gui_chose_cursor_color_("vertical")
    
    @pyqtSlot()
    def _slot_setHorizontalCursorColors(self):
        self._gui_chose_cursor_color_("horizontal")
    
    @pyqtSlot()
    def _slot_setCrosshairCursorColors(self):
        self._gui_chose_cursor_color_("crosshair")

    @pyqtSlot(object, object)
    @safeWrapper
    def _slot_plot_axis_x_range_changed(self, x0, x1):
        """To update non-data items such as epochs
        """
        ax = self.sender()
        
        if self.currentFrame in self._cached_epochs_:
            if len(self._cached_epochs_[self.currentFrame]):
                self._plotEpochs_(from_cache=True)
                
    @safeWrapper
    def refresh(self):
        """
        Simply calls displayFrame().
        Since the data is held by reference, external changes ot the data will
        be automatically displayed
        """
        self.displayFrame()
        
    @safeWrapper
    def displayFrame(self):
        """ Plots individual frame (data "sweep" or "segment")
        
        Implements gui.scipyenviewer.ScipyenFrameViewer.displayFrame
        
        Delegates plotting as follows:
        
        neo.Segment                     -> _plotSegment_ # needed to pick up which signal from segment
        
        neo.AnalogSignal                -> _plotSignal_
        neo.IrregularlySampledSignal    -> _plotSignal_
        neo.Epoch                       -> _plotSignal_
        neo.SpikeTrain                  -> _plotSignal_
        neo.Event                       -> _plotSignal_
        datatypes.DataSignal            -> _plotSignal_
        vigra.Kernel1D, vigra.Kernel2D  -> _plotNumpyArray_ (after conversion to numpy.ndarray)
        numpy.ndarray                   -> _plotNumpyArray_ (including vigra.VigraArray and quantity arrays)
        
        sequence (iterable)             -> _plotSequence_
            The sequence can contain these types:
                neo.AnalogSignal, 
                neo.IrregularlySampledSignal, 
                datatypes.DataSignal, 
                np.ndarray
                vigra.filters.Kernel1D  -> NOTE  this is converted to two numpy arrays in plot()
        
        Anything else  (?)              -> _plot_numeric_data_
        
        """
        if self.yData is None:
            return
        
        self.currentFrameAnnotations = None
        
        # print(f"SignalViewer.displayFrame {self.yData}")
        
        #### BEGIN self.yData is a sequence of objects
        if isinstance(self.yData, (tuple, list)): 
            # a sequence of objects
            #
            # can be a sequence of signals, with "signal" being one of:
            # neo.AnalogSignal
            # neo.IrregularlySampledSignal
            # datatypes.DataSignal
            # numpy array (vector with shape (n,) or (n, 1)) or matrix (columns
            # vectors) shaped (n, m)
            # vigra.Kernel1D
            
            # NOTE: because the signals in the collection do not necessarily 
            # have a common "domain" (e.g. time domain, sampling rate, etc) each 
            # signal is considered to belong to its own hypothetical data "frame"
            # ("sweep", or "segment")
            #
            # when the 2nd dimension of the "signals" is non-singleton, the data
            # is interpreted as "multi-channel"
            #
            # vigra.Kernel1D are a special case, as they are converted on-the-fly
            # to a tuple of 1D arrays (x, y)
            #
            # see setData() for list of kernel1D, datatypes.DataSignal, and np.ndarrays
            #print("displayFrame: self.xData: ", self.xData)
            
            if all([isinstance(y_, (DataSignal, 
                                    neo.core.AnalogSignal, 
                                    neo.core.IrregularlySampledSignal,
                                    IrregularlySampledDataSignal)) for y_ in self.yData]):
                if self._current_frame_index_ in self.frameIndex:
                    ndx = self.frameIndex[self._current_frame_index_]
                else:
                    self._current_frame_index_ = 0
                    ndx = self._current_frame_index_
                    
                self._plotSignal_(self.yData[ndx], *self.plot_args, **self.plot_kwargs) # x is contained in the signal
                self.currentFrameAnnotations = {type(self.yData[ndx]).__name__: self.yData[ndx].annotations}
                
            elif all([isinstance(y_, (neo.core.Epoch, DataZone)) for y_ in self.yData]): 
                # plot Epoch(s) independently of data; there is a single frame
                
                epochs_start_end = np.array([(e[0], e[-1] + e.durations[-1]) for e in self.yData])
                x_min, x_max = (np.min(epochs_start_end[:,0]), np.max(epochs_start_end[:,1]))
                self._prepareAxes_(1)
                self._plotEpochs_(self.yData, **self.epoch_plot_options)
                self.axes[0].showAxis("bottom", True)
                
            elif all([isinstance(y_, neo.Segment) for y_ in self.yData]):
                segment = self.yData[self.frameIndex[self._current_frame_index_]]
                self._plotSegment_(segment, *self.plot_args, **self.plot_kwargs)
                self.currentFrameAnnotations = {type(segment).__name__ : segment.annotations}
                
            elif all([isinstance(y_, neo.Block) for y_ in self.yData]):
                frIndex = self.frameIndex[self._current_frame_index_]
                
                # NOTE: 2021-01-04 11:13:33
                # sequence-block-segment indexing array, e.g.:
                # array([[0, 0, 0],
                #        [1, 1, 0],
                #        [2, 2, 0]])

                # i.e. [[sequence index, block index, segment index in block]]:
                # column 0 = overall running index of Segment in "virtual" sequence
                # column 1 = running index of the Block
                # column 2 = running index of Segment in Block with current 
                #            running block index
                sqbksg = np.array([(q, *kg) for q, kg in enumerate(enumerate(chain(*((k for k in range(len(b.segments))) for b in self.yData))))])
                
                (blockIndex, blockSegmentIndex) = sqbksg[frIndex,1:]
                
                segment = self.yData[blockIndex].segments[blockSegmentIndex]
                
                plotTitle = "Block %d (%s), segment %d (%s)" % (blockIndex, self.yData[blockIndex].name,
                                                                blockSegmentIndex, segment.name)
                
                kwargs = dict()
                kwargs.update(self.plot_kwargs)
                kwargs["plotTitle"] = plotTitle
                
                self._plotSegment_(segment, *self.plot_args, **kwargs)
                
                self.currentFrameAnnotations = {type(segment).__name__ : segment.annotations}
                
            elif all(isinstance(y_, (neo.Event, DataMark)) for y_ in self.yData):
                self._plotEvents_(self.yData)
                
            elif all(isinstance(y_, neo.SpikeTrain) for y_ in self.yData):
                self._plotSpikeTrains_(self.yData)
            
            else: # accepts sequence of np.ndarray or VigraKernel1D objects
                self._setup_signal_choosers_(self.yData)
                
                if isinstance(self.xData, list):
                    self._plotNumpyArray_(self.xData[self._current_frame_index_], self.yData[self._current_frame_index_], *self.plot_args, **self.plot_kwargs)
                    
                else:
                    self._plotNumpyArray_(self.xData, self.yData[self._current_frame_index_], *self.plot_args, **self.plot_kwargs)
                    
        #### END self.yData is a sequence of objects
        
        #### BEGIN self.yData is a single object
        else:
            if isinstance(self.yData, neo.core.Block):
                # NOTE: 2019-11-24 22:31:26
                # select a segment then delegate to _plotSegment_()
                # Segment selection is based on self.frameIndex, or on self.channelIndex # NOTE 2021-10-03 12:59:10 ChannelIndex is no more
                if len(self.yData.segments) == 0:
                    return
                
                if self._current_frame_index_ not in self.frameIndex:
                    return
                
                segmentNdx = self.frameIndex[self._current_frame_index_]
                
                if segmentNdx >= len(self.yData.segments):
                    return
                
                segment = self.yData.segments[segmentNdx]
                
                self._plotSegment_(segment, *self.plot_args, **self.plot_kwargs) # calls _setup_signal_choosers_() and _prepareAxes_()
                
                self.currentFrameAnnotations = {type(segment).__name__ : segment.annotations}
                
            elif isinstance(self.yData, neo.core.Segment):
                # delegate straight to _plotSegment_()
                self._plotSegment_(self.yData, *self.plot_args, **self.plot_kwargs) # calls _setup_signal_choosers_() and _prepareAxes_()
                
            elif isinstance(self.yData, (neo.core.AnalogSignal, 
                                     DataSignal, 
                                     neo.core.IrregularlySampledSignal,
                                     IrregularlySampledDataSignal)):
                self._plotSignal_(self.yData, *self.plot_args, **self.plot_kwargs)

            elif isinstance(self.yData, (neo.core.Epoch, DataZone)): # plot an Epoch independently of data
                x_min, x_max = (self.yData[0], self.yData[-1] + self.yData.durations[-1])
                self._prepareAxes_(1)
                self._plotEpochs_(self.yData, **self.epoch_plot_options)
                self.axes[0].showAxis("bottom", True)
                
            elif isinstance(self.yData, (neo.Event, DataMark)):
                self._plotEvents_(self.yData)
                
            elif isinstance(self.yData, (neo.SpikeTrain)):
                self._plotSpikeTrains_(self.yData)

            elif isinstance(self.yData, np.ndarray):
                try:
                    if self.yData.ndim > 3:
                        raise TypeError("Numpy arrays with more than three dimensions are not supported")
                    
                    self._plotNumpyArray_(self.xData, self.yData, *self.plot_args, **self.plot_kwargs)
                    
                except Exception as e:
                    traceback.print_exc()
                    
            elif self.yData is None:
                pass
                
            # else:
            #     raise TypeError("Plotting of data of type %s not yet implemented" % str(type(self.yData)))
        #### END self.yData is a single object
            
        # NOTE: 2020-03-10 22:09:51
        # reselect an axis according to its index (if one had been selected before)
        # CAUTION: this may NOT be the same PlotItem object!
        # also makes sure we always have an axis selected
        if len(self.plotItems):
            if self._current_plot_item_ is None:
                self._current_plot_item_index_ = 0 # by default
                self._current_plot_item_ =  self.plotItems[self._current_plot_item_index_] 
                
            elif self._current_plot_item_ not in self.plotItems:
                if self._current_plot_item_index_ < 0: # this is prev index
                    self._current_plot_item_index_ = 0
                    
                elif self._current_plot_item_index_ >= len(self.plotItems):
                        self._current_plot_item_index_ = len(self.plotItems) -1
                    
                self._current_plot_item_ = self.plotItems[self._current_plot_item_index_]
                
            else:
                self._current_plot_item_index_ = self.plotItems.index(self._current_plot_item_)
                
            self._setAxisIsActive(self._current_plot_item_, True)
                    
        else:
            # have no axis selected as current, only when there are no axes
            # (pg.PlotItem objects)
            self._current_plot_item_ = None
            self._current_plot_item_index_ = -1
                    
        self._update_annotations_()
        
        # Check if cursors want to stay in axis or stay with the domain
        # and act accordingly
        mfun = lambda x: -np.inf if x is None else x
        pfun = lambda x: np.inf if x is None else x
        
        for k, ax in enumerate(self.axes):
            [[dataxmin, dataxmax], [dataymin, dataymax]] = guiutils.getPlotItemDataBoundaries(ax)
            
            # if k in self._cached_cursors_:
            #     for cursor in self._cached_cursors_[k]:
            #         if cursor.x < dataxmin or cursor.x > dataxmax:
            #             newX = 
                
            for c in self.cursorsInAxis(k):
                if not c.staysInAxes:
                    continue
                
                if not c.isHorizontal:
                    relX = c.x - c.xBounds()[0]
                    c.setBounds()
                    c.x = dataxmin + relX
                    
                if not c.isVertical:
                    relY = c.y - c.yBounds()[0]
                    c.setBounds()
                    c.y = dataymin+relY
                    
        # NOTE: 2022-11-22 11:49:47
        # Finally, check for target overlays
        try:
            cFrame = self.frameIndex[self.currentFrame]
        except:
            cFrame = self.frameIndex[0]
            
        if len(self.axes) and cFrame in self._target_overlays_:
            for axNdx, ax in enumerate(self.axes):
                self._clear_targets_overlay_(ax)
                targetItems = self._target_overlays_[cFrame].get(axNdx, list())
                if len(targetItems):
                    for tgt in targetItems:
                        ax.addItem(tgt)
                        
        if len(self.axes):
            self.axes[-1].showAxis("bottom", True)
            self.axes[-1].showAxes([True, False, False, True], showValues=[True, False, False, True])
            
            
                        
    @safeWrapper
    def _plotSpikeTrains_(self, trains:typing.Optional[typing.Union[neo.SpikeTrain, tuple, list]] = None, clear:bool = False, **kwargs):
        """Plots stand-alone spike trains.
        """
        if trains is None or clear:
            self._clear_lris_()
        
        if trains is None:
            return
        
        trains_dict = self._prep_entity_dict_(trains, neo.SpikeTrain)
        
        if len(trains_dict):
            if self.separateSignalChannels:
                self._prepareAxes_(len(trains_dict))
                for k,v in trains_dict.items():
                    self._plot_discrete_entities_({k:v}, **kwargs)
                    
            else:
                self._prepareAxes_(1)
                self._plot_discrete_entities_(trains_dict, **kwargs)
                
            self.axes[-1].showAxis("bottom", True)
            
    @safeWrapper
    def _plotEvents_(self, events: typing.Optional[typing.Union[neo.Event, DataMark, typing.Sequence]] = None, clear: bool = True, from_cache: bool = False, **kwargs):
        
        if events is None or clear:
            self._clear_lris_()
            #self._cached_events_.clear()
            
        if events is None:
            return
        
        events_dict = self._prep_entity_dict_(events, (neo.Event, DataMark))
        
        if len(events_dict):
            if self.separateSignalChannels:
                self._prepareAxes_(len(events_dict))
                for k,v in events_dict.items():
                    self._plot_discrete_entities_({k:v}, **kwargs)
            else:
                self._prepareAxes_(1)
                self._plot_discrete_entities_(events_dict, **kwargs)
                
            self.axes[-1].showAxis("bottom", True)
        
    def _plot_epochs_seq_(self, *args, **kwargs):
        """Does the actual plotting of epoch data.
        Epochs is always a non-empty sequence (tuple or list) of neo.Epochs
        We keep this as a nested function to avoid calling it directly. Thus
        there is no need to check if the epochs argument is the same as 
        self.yData (or contained within)
        """
        
        # print(f"SignalViewer._plot_epochs_seq_ {args}")
        
        if len(args) == 0:
            return
        
        epoch_pen = kwargs.pop("epoch_pen", self.epoch_plot_options["epoch_pen"])
        epoch_brush = kwargs.pop("epoch_brush", self.epoch_plot_options["epoch_brush"])
        epoch_hoverPen = kwargs.pop("epoch_hoverPen", self.epoch_plot_options["epoch_hoverPen"])
        epoch_hoverBrush = kwargs.pop("epoch_hoverBrush", self.epoch_plot_options["epoch_hoverBrush"])
        
        # plot LRIs in a different colour for each epoch; 
        # all LRIs that belong to the same epoch have the same colour.
        if epoch_brush is None:
            # no epoch brush specified
            if len(args) > 1:
                brushes = cycle([QtGui.QBrush(QtGui.QColor(*c)) for c in self.epoch_plot_options["epochs_color_set"]])
                
            else:
                brushes = cycle([QtGui.QBrush(QtGui.QColor(0,0,255,50))]) # what seems to be the default in LinearRegionItem
            
        else: # epoch brushes have been specified in one of several ways:
            if isinstance(epoch_brush, typing.Sequence):
                # a tuple or list of brush specs
                if all([isinstance(b, (QtGui.QColor, QtGui.QBrush, tuple, list)) for b in epoch_brush]):
                    brushes = cycle([QtGui.QBrush(QtGui.QColor(c)) if isinstance(c, (QtGui.QColor, QtGui.QBrush)) else QtGui.QBrush(QtGui.QColor(*c)) for c in epoch_brush])
                    
                else:
                    brushes = cycle([QtGui.QBrush(QtGui.QColor(*epoch_brush))])
                    
            elif isinstance(epoch_brush, QtGui.Color):
                # a single Qt Color
                brushes = cycle([QtGui.QBrush(epoch_brush)])
                
            elif isinstance(epoch_brush, QtGui.QBrush):
                # a single Qt Brush
                brushes = cycle([epoch_brush])
                
            else:
                warnings.warn("Invalid brush specification %s" % epoch_brush)
                brushes = cycle([None])
                
        for epoch in args:
            # print(f"SignalViewer._plot_epochs_seq_ epoch times {epoch.times} durations {epoch.durations}")
            x0 = epoch.times.flatten().magnitude
            x1 = x0 + epoch.durations.flatten().magnitude
            
            brush = next(brushes)
            
            for k in range(len(self.axes)):
                self.axes[k].update() # to update its viewRange()
                
                regions = [v for v in zip(x0,x1)]
                
                lris = [pg.LinearRegionItem(values=value, 
                                            brush=brush, 
                                            orientation=pg.LinearRegionItem.Vertical, 
                                            movable=False) for value in regions]
                
                for kl, lri in enumerate(lris):
                    self.axes[k].addItem(lri)
                    lri.setZValue(10)
                    lri.setVisible(True)
                    lri.setRegion(regions[kl])
        
    @safeWrapper
    def _plotEpochs_(self, epochs: typing.Optional[typing.Union[neo.Epoch, DataZone, typing.Sequence]] = None, clear: bool = True, from_cache: bool = False, **kwargs):
        """Plots epochs.
        A neo.Epoch contains time intervals each defined by time and duration.
        Epoch intervals are drawn using pyqtgraph.LinearRegionItem objects.
        
        Parameters:
        ------------
        
        epochs: neo.Epoch or a sequence (tuple, or list) of neo.Epoch objects,
            or None (default).
            
            The behaviour of this function depends on whether the signal viewer 
            was set to plot standalone epoch data (i.e. epoch data NOT associated
            with a neo Segment, or with anything else).
            
            FIXME: Standalone epoch data is an Epoch or sequence of Epoch objects
            passed as the 'y' parameter to self.setData(...) function
            (NOTE that self.setData is aliased to 'self.plot' and 'self.view').
            
            When the 'epochs' parameter is None or an empty sequence, the 
            function plots the standalone epoch data, if it exists, or clears
            any representations of previous epoch data from all axes.
            
        clear: bool, default is True.
            When True, all representations of epochs data are cleared from the
            axes, regardless if there exists standalone epoch data.
            
            Otherwise new epochs are added to the plot.
            
        from_cache: bool, default is False:
            When True, plots internally cached epochs
        
        """
        
        # print(f"SignalViewer _plotEpochs_ epochs: {epochs}; cached: {self._cached_epochs_}")
        
        # BEGIN plot epochs from cache (containing standalone epoch data), if any and if requested
        
        if from_cache:
            epoch_seq = self._cached_epochs_.get(self.currentFrame, None)
            
            # BEGIN plot epochs from cache: clear current displayed epoch if requested
            # if epoch_seq is not None and clear:
            if clear:
                for k, ax in enumerate(self.axes):
                    lris = [i for i in ax.items if isinstance(i, pg.LinearRegionItem)]
                    for l in lris:
                        ax.removeItem(l)
            
            # END plot epochs from cache: clear current displayed epoch if requested
            
            self._plot_epochs_seq_(*epoch_seq, **kwargs)
                
            return
        # END plot epochs from cache (containing standalone epoch data), if any and if requested
            
        # BEGIN plot supplied epoch
        # BEGIN clear current epoch display if requested
        if clear:
            for k, ax in enumerate(self.axes):
                lris = [i for i in ax.items if isinstance(i, pg.LinearRegionItem)]
                for l in lris:
                    ax.removeItem(l)
        # END clear current epoch display if requested
        
        epoch_seq = list()
        # END plot supplied epoch
        
        if epochs is None or len(epochs) == 0:
            # None, an empty sequence of epochs or an empty epoch
            if isinstance(self.yData, neo.Epoch):
                self._prepareAxes_(1) # use a brand new single axis
                epoch_seq = [self.yData]
                
            elif isinstance(self.yData, typing.Sequence) and all([isinstance(y_, (neo.Epoch, DataZone)) for y_ in self.yData]):
                self._prepareAxes_(1) # use a brand new single axis
                epoch_seq = self.yData
                
        elif isinstance(epochs, (neo.Epoch, DataZone)):
            epoch_seq = [epochs]
            
        elif isinstance(epochs, typing.Sequence):
            if all([isinstance(e, (neo.Epoch, DataZone)) for e in epochs]):
                epoch_seq = epochs
                
            else:
                # NOTE: 2020-10-27 09:19:26
                # some of these may be relics from old API (i.e., neoepoch.Epoch)
                # therefore we try to salvage them
                epoch_seq = list()
                
                for e in epochs:
                    if isinstance(e, (neo.Epoch, DataZone)):
                        epoch_seq.append(e)
                        
                    # elif type(e).__name__ == "Epoch":
                    #     epoch_seq.append(neo.Epoch(times=e.times,durations=e.durations,
                    #                                labels=e.labels, name=e.name,
                    #                                units=e.units, description=e.description,
                    #                                file_origin=e.file_origin,
                    #                                **e.annotations))
            
        else:
            raise TypeError("Expecting a neo.Epoch or a Sequence of neo.Epoch objects; got %s instead" % type(epochs).__name__)
        
        if len(epoch_seq):
            self._plot_epochs_seq_(*epoch_seq, **kwargs)
            
            if self.currentFrame in self._cached_epochs_:
                if len(self._cached_epochs_[self.currentFrame]):
                    if clear:
                        self._cached_epochs_[self.currentFrame] = epoch_seq
                        
                    else:
                        self._cached_epochs_[self.currentFrame] += epoch_seq
                        
        else:
            # clear cache when no epochs were passed
            self._cached_epochs_.pop(self.currentFrame, None)
                    
    @safeWrapper
    def _plotSegment_(self, seg, *args, **kwargs):
        """Plots a neo.Segment.
        Plots the signals (optionally the selected ones) present in a segment, 
        and the associated epochs, events, and spike trains.
        """
        # NOTE: 2021-10-03 12:55:21 ChannelIndex is OUT of neo
        
        # NOTE: 2021-01-02 11:54:50
        # allow custom plot title - handy e.g., for plotting segments from across
        # a list of blocks
        plotTitle = kwargs.pop("plotTitle", "")
        
        if not isinstance(seg, neo.Segment):
            raise TypeError("Expecting a neo.Segment; got %s instead" % type(seg).__name__)
        
        
        # NOTE: 2019-11-24 23:21:13#
        # 1) Select which signals to display
        self.signalIndex = normalized_signal_index(seg, self.signalIndex, ctype = neo.AnalogSignal)
        self.irregularSignalIndex = normalized_signal_index(seg, self.irregularSignalIndex, ctype = neo.IrregularlySampledSignal)
        analog = [seg.analogsignals[k] for k in self.signalIndex]
        irregs = [seg.irregularlysampledsignals[k] for k in self.irregularSignalIndex]
    
        # this updates the available choices in the comboboxes
        # any previous selection is kept, if still available
        self._setup_signal_choosers_(analog = analog, irregular = irregs) 
        
        # lists with signals and signal names for the ones that will be actually
        # plotted
        selected_analogs = list()
        selected_analog_names = list()
        selected_irregs = list()
        selected_irregs_names = list()
        
        # BEGIN prepate to plot regular (analog) signals
        if self._plot_analogsignals_:
            # now try to get the signal selections from the combo boxes
            current_ndx = self.selectSignalComboBox.currentIndex() 
            
            if current_ndx == 0: # "All" selected
                selected_analogs[:] = analog[:]
                
                for k, s in enumerate(analog):
                    if isinstance(s.name, str) and len(s.name.strip()):
                        selected_analog_names.append(s.name)
                        
                    else:
                        selected_analog_names.append("Analog signal %d" % k)
                
            elif current_ndx == self.selectSignalComboBox.count() - 1: # "Choose" selected
                # read the multiple choices previously set up by a dialog
                # selected_analogs = list()
                if len(self.guiSelectedSignalNames):
                    for k,s in enumerate(analog):
                        if isinstance(s.name, str) and len(s.name.strip()):
                            if s.name in self.guiSelectedSignalNames:
                                selected_analogs.append(s)
                                selected_analog_names.append(s.name)
                                
                        elif "Analog signal %d" % k in self.guiSelectedSignalNames:
                            selected_analogs.append(s)
                            selected_analog_names.append("Analog signal %d" % k)
                
            elif current_ndx > -1:
                selected_analogs = [analog[current_ndx-1]]
                s_name = selected_analogs[0].name
                
                if isinstance(s_name, str) and len(s_name.strip()):
                    selected_analog_names = [s_name]
                    
                else:
                    selected_analog_names = ["Analog signal %d" % (current_ndx-1, )]
        # END   prepate to plot regular (analog) signals
          
        # BEGIN prepate to plot irregular signals
        if self._plot_irregularsignals_:
            current_ndx = self.selectIrregularSignalComboBox.currentIndex()
            current_txt = self.selectIrregularSignalComboBox.currentText()
            
            if current_ndx == 0:
                selected_irregs[:] = irregs[:]
                
                for k,s  in enumerate(irregs):
                    if isinstance(s.name, str) and len(s.name.strip()):
                        selected_irregs_names.append(s.name)
                        
                    else:
                        selected_irregs_names.append("Irregularly sampled signal %d" % k)
                
            elif current_ndx == self.selectIrregularSignalComboBox.count() - 1:
                if len(self.guiSelectedIrregularSignalNames):
                    for k, s in enumerate(irregs):
                        if isinstance(s.name, str) and len(s.name.strip()):
                            if s.name in self.guiSelectedIrregularSignalNames:
                                selected_irregs.append(s)
                                selected_irregs_names.append(s.name)
                                
                        elif "Irregularly sampled signal %d" % k in self.guiSelectedIrregularSignalNames:
                            selected_irregs.append(s)
                            selected_irregs_names.append("Irregularly sampled signal %d" % k)
                            
            elif current_ndx > -1:
                selected_irregs = [irregs[current_ndx-1]]
                s_name = selected_irregs[0].name
                
                if isinstance(s_name, str) and len(s_name.strip()):
                    selected_irregs_names = [s_name]
                    
                else:
                    selected_irregs_names = ["Irregularly sampled signal %d" % (current_ndx-1,)]
        
        # END   prepate to plot irregular signals
        
        # BEGIN initial set up axes
        nAnalogAxes = len(selected_analogs) 
        
        nIrregAxes = len(selected_irregs)
        
        nRequiredAxes = nAnalogAxes + nIrregAxes
        # END   initial set up axes
        
        signames = selected_analog_names + selected_irregs_names # required for prepare axes and caching of cursors (see comments in _prepareAxes_())
        
        # BEGIN prepare to plot spike trains
        # NOTE: 2019-11-25 15:19:16
        # for segments we do not plot signals with their channels separate
        # if needed, then get a reference to the signal and plot it individually
        # with separateSignalChannels set to True
        spiketrains = get_non_empty_spike_trains(seg.spiketrains)
        if len(spiketrains):
            nRequiredAxes += 1
            signames += ["spike trains"]
        # END   prepare to plot spike trains
        
        # BEGIN prepare to plot events
        events = get_non_empty_events(seg.events)
        
        if isinstance(events, (tuple, list)) and len(events):
            nRequiredAxes += 1
            signames += ["events"]
        # END   prepare to plot events
           
        # BEGIN finalize set up axes
        self._prepareAxes_(nRequiredAxes, sigNames=signames)
        
        axes = self.plotItems
        # END   finalize set up axes
        
        kAx = 0
        
        #### BEGIN plot regular (analog) signals 
        for k, signal in enumerate(selected_analogs):
            signal_axis = self.signalsLayout.getItem(kAx,0)
            if isinstance(signal, neo.AnalogSignal):
                domain_name = "Time"
                
            else:
                domain_name = signal.domain_name # alternative is a DataSignal
                
            # apply whatever time slicing was required by arguments to setData()
            if self.plot_start is not None:
                if self.plot_stop is not None:
                    sig = signal.time_slice(self.plot_start, self.plot_stop)
                    
                else:
                    sig = signal.time_slice(self.plot_start, signal.t_top)
                    
            else:
                if self.plot_stop is not None:
                    sig = signal.time_slice(signal.t_start, self.plot_stop)
                    
                else:
                    sig = signal

            if isinstance(sig.name, str) and len(sig.name.strip()):
                sig_name = sig.name
                
            else:
                sig_name = "Analog signal %d" % k
            
            plotItem = self.signalsLayout.getItem(kAx,0)
            
            if sig.shape[1] > 10:
                self.sig_plot.emit(self._make_sig_plot_dict_(plotItem,
                                        sig.times,
                                        sig.magnitude,
                                        xlabel = "%s (%s)" % (domain_name, sig.t_start.units.dimensionality),
                                        ylabel = "%s (%s)" % (sig_name, signal.units.dimensionality),
                                        name=sig_name,
                                        symbol=None,
                                        **kwargs))
            else:
                self._plot_numeric_data_(plotItem,
                                        sig.times,
                                        sig.magnitude,
                                        xlabel = "%s (%s)" % (domain_name, sig.t_start.units.dimensionality),
                                        ylabel = "%s (%s)" % (sig_name, signal.units.dimensionality),
                                        name=sig_name,
                                        symbol=None,
                                        **kwargs)
            
            signal_axis.axes["left"]["item"].setStyle(autoExpandTextSpace=False,
                                               autoReduceTextSpace=False)
            signal_axis.update()
            kAx += 1
         
        #### END   plot regular (analog) signals
        
        #### BEGIN plot irregularly sampled signals
        for k, signal in enumerate(selected_irregs):
            signal_axis = self.signalsLayout.getItem(kAx,0)
            if isinstance(signal, neo.IrregularlySampledSignal):
                domain_name = "Time"
                
            else:
                domain_name = signal.domain_name # alternative is a IrregularlySampledDataSignal
        
            if self.plot_start is not None:
                if self.plot_stop is not None:
                    sig = signal.time_slice(self.plot_start, self.plot_stop)
                    
                else:
                    sig = signal.time_slice(self.plot_start, signal.t_top)
                    
            else:
                if self.plot_stop is not None:
                    sig = signal.time_slice(signal.t_start, self.plot_stop)
                    
                else:
                    sig = signal
                        
            plotItem = self.signalsLayout.getItem(kAx, 0)
            
            if sig.shape[1] > 10:
                self.sig_plot.emit(self._make_sig_plot_dict_(plotItem,
                                        sig.times,
                                        sig.magnitude,
                                        xlabel = "Time (%s)" % sig.t_start.units.dimensionality,
                                        ylabel = "%s (%s)" % (sig.name, signal.units.dimensionality),
                                        symbol = None,
                                        **kwargs))
            else:
                self._plot_numeric_data_(plotItem,
                                        sig.times,
                                        sig.magnitude,
                                        xlabel = "Time (%s)" % sig.t_start.units.dimensionality,
                                        ylabel = "%s (%s)" % (sig.name, signal.units.dimensionality),
                                        symbol = None,
                                        **kwargs)
            
            signal_axis.axes["left"]["item"].setStyle(autoExpandTextSpace=False,
                                               autoReduceTextSpace=False)
            signal_axis.update()
            kAx += 1
        
        #### END   plot irregularly sampled signals
        
        #### BEGIN plot spike trains
        if len(spiketrains):
            # plot all spike trains in this segment stacked in a single axis
            spike_train_axis = self.signalsLayout.getItem(kAx,0)
            
            # NOTE: 2022-11-29 23:09:46
            # try to see if we can set this to a smaller height; currently it has the same expanding policy as axes for signals
            spike_train_axis.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, 
                                                                 QtWidgets.QSizePolicy.Minimum, 
                                                                 QtWidgets.QSizePolicy.Frame))
            
            symbolcolors = cycle(self.defaultLineColorsList)
            symbolPen = QtGui.QPen(QtGui.QColor("black"),1)
            symbolPen.setCosmetic(True)
            
            
            labelStyle = {"color": "#000000"}
            
            height_interval = 1/len(spiketrains) 
            
            self._plot_discrete_entities_(spiketrains, axis=kAx, **kwargs)
            spike_train_axis.update()
            kAx +=1
                
        #### END plot spike trains
        
        #### BEGIN plot events
        if isinstance(events, (tuple, list)) and len(events):
            # plot all event arrays in this segment stacked in a single axis
            #print("_plotSegment_ events", kAx)
            event_axis = self.signalsLayout.getItem(kAx, 0)
            
            # NOTE: 2022-11-29 23:14:42 see NOTE: 2022-11-29 23:09:46
            event_axis.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, 
                                                           QtWidgets.QSizePolicy.Minimum, 
                                                           QtWidgets.QSizePolicy.Frame))
            
            symbolcolors = cycle(self.defaultLineColorsList)
            symbolPen = QtGui.QPen(QtGui.QColor("black"),1)
            symbolPen.setCosmetic(True)
            
            labelStyle = {"color": "#000000"}
            
            height_interval = 1/len(events)
            
            self._plot_discrete_entities_(events, axis=kAx, **kwargs)
            event_axis.update() 
            kAx +=1
            
        #### END plot events
        
        #### BEGIN plot epochs
        # common logic for stand-alone epochs and for epochs associated with
        # a neo.Segment
        self._plotEpochs_(seg.epochs)
        #### END plot epochs
        
        # hide X axis spine in all but the last signal axes only if all signals
        # in the segment share the domain
        
        for k_ax in range(0, kAx-1):
            plotitem = self.signalsLayout.getItem(k_ax,0)
            if isinstance(plotitem, pg.PlotItem):
                # self.signalsLayout.getItem(k_ax,0).hideAxis("bottom")
                # NOTE: 2022-11-21 13:32:52
                # completely hiding the bottom axis prevents grid display on X
                # because in PyQtGraph the grid is made of extended tickmarks;
                # therefore keep this axis showing, but without axis label and
                # without values attached to th tick marks
                self.signalsLayout.getItem(k_ax,0).getAxis("bottom").showLabel(False)
                self.signalsLayout.getItem(k_ax,0).getAxis("bottom").setStyle(showValues=False)
        
        if not isinstance(plotTitle, str) or len(plotTitle.strip()) == 0:
            if isinstance(seg.name, str) and len(seg.name.strip()):
                self.plotTitleLabel.setText(seg.name, color = "#000000")
                
            else:
                self.plotTitleLabel.setText("", color = "#000000")
                
        else:
            self.plotTitleLabel.setText(plotTitle, color = "#000000")
            
        
    @safeWrapper
    def _plotNumpyArray_(self, x, y, *args, **kwargs):
        """Called to plot a numpy array of up to three dimensions
        """
#         print(f"{self.__class__.__name__} _plotNumpyArray_ call stack:")
#         for s in inspect.stack():
#             print(f"\t\t caller: {s.function}")
#         
#         print(f"{self.__class__.__name__} _plotNumpyArray_ y.ndim {y.ndim}")
        
        self._setup_signal_choosers_(y)
        
        if y.ndim == 1:
            self._prepareAxes_(1)
            self._plot_numeric_data_(self.plotItem(0), x, y, name="Analog signal", *args, **kwargs)
            #self.sig_plot.emit(self._make_sig_plot_dict_(self.plotItem(0), x, y, name="Analog signal", *args, **kwargs))
            
        elif y.ndim == 2:
            if self.frameAxis is None:
                if self.separateSignalChannels:
                    # plot each channel in one axis; all axes on the same frame
                    self._prepareAxes_(len(self.signalChannelIndex))
                    for kchn, chNdx in enumerate(self.signalChannelIndex):
                        y_ = y[array_slice(y, {self.signalChannelAxis:chNdx})]
                        if y_.shape[self.signalChannelAxis] > 10:
                            self.sigplot.emit(self._make_sig_plot_dict_(self.plotItem(kchn),
                                                    x, y_,
                                                    *args, **kwargs))
                        else:
                            self._plot_numeric_data_(self.plotItem(kchn),
                                                    x, y_,
                                                    *args, **kwargs)
                        
                else:
                    # plot everything in the same axis
                    self._prepareAxes_(1)
                    if y.shape[self.signalChannelAxis] > 10:
                        self.sig_plot.emit(self._make_sig_plot_dict_(self.plotItem(0), x, y, name="Analog signal", *args, **kwargs))
                    else:
                        self._plot_numeric_data_(self.plotItem(0), x, y, name="Analog signal", *args, **kwargs)
                    
            else:
                self._prepareAxes_(1) # one axis per frame: one channel per frame
                y_ = y[array_slice(y, {self.frameAxis:self.currentFrame})]
                if y_.shape[self.signalChannelAxis] > 10:
                    self.sig_plot.emit(self._make_sig_plot_dict_(self.plotItem(0), 
                                            x, y_,
                                            *args, **kwargs))
                else:
                        
                    self._plot_numeric_data_(self.plotItem(0), x, y_, *args, **kwargs)
                
        elif y.ndim == 3:
            # the number of frame is definitely > 1 and there are more than
            # one signal channel
            if self.separateSignalChannels:
                self._prepareAxes_(len(self.signalChannelIndex))
                for kchn, chNdx in enumerate(self.signalChannelIndex):
                    y_ = y[array_slice(y, {self.signalChannelAxis:chNdx})]
                    if y_.shape[self.signalChannelAxis] > 10:
                        self.sig_plot.emit(self._make_sig_plot_dict_(self.plotItem(kchn),
                                                x, y_, *args, **kwargs))
                    else:
                        self._plot_numeric_data_(self.plotItem(kchn),
                                                x, y_, *args, **kwargs)
                
            else:
                self._prepareAxes_(1)
                y_ = y[array_slice(y, {self.frameAxis:self.currentFrame})]
                if y_.shape[self.signalChannelAxis] > 10:
                    self.sig_plot.emit(self._make_sig_plot_dict_(self.plotItem(0), 
                                            x, y_, *args, **kwargs))
                else:
                    self._plot_numeric_data_(self.plotItem(0), 
                                            x, y_, *args, **kwargs)
                    
        else:
            raise TypeError("numpy arrays with more than three dimensions are not supported")
        
    @safeWrapper
    def _plotSignal_(self, signal, *args, **kwargs):
        """Plots individual signal objects.
        
        Called by self.displayFrame when self.yData is a signal, or a sequence
        of signals.
        
        Signal objects are those defined in the Neuralensemble's neo package 
        (neo.AnalogSignal, neo.IrregularlySampledSignal), and in the datatypes
        module (datatypes.DataSignal, datatypes.IrregularlySampledDataSignal).
        
        Calls _setup_signal_choosers_, then determines how may axes are needed,
        depending on whether channels are plotted separately (and which ones, if
        indicated in arguments passed on to setData())
        
        Data is then plotted in each axes (if more than one) from top to 
        bottom iterating through channels (if required) by calling
        _plot_numeric_data_()
        """
        if signal is None:
            return

        #if not isinstance(signal, (neo.core.baseneo.BaseNeo, DataSignal)):
        if not isinstance(signal, neo.core.baseneo.BaseNeo):
            raise TypeError("_plotSignal_ expects an object from neo framework, or a datatypes.DataSignal or datatypes.IrregularlySampledDataSignal; got %s instead" % (type(signal).__name__))
            
        self._setup_signal_choosers_(self.yData)
        
        signal_name = signal.name
        
        if isinstance(signal, (neo.AnalogSignal, neo.IrregularlySampledSignal)):
            domain_name = "Time"
            
        else:
            domain_name = signal.domain_name
                            
        if self.plot_start is not None:
            if self.plot_stop is not None:
                sig = signal.time_slice(self.plot_start, self.plot_stop)
                
            else:
                sig = signal.time_slice(self.plot_start, signal.t_top)
                
        else:
            if self.plot_stop is not None:
                sig = signal.time_slice(signal.t_start, self.plot_stop)
                
            else:
                sig = signal
                
        if self.separateSignalChannels:
            if self.signalChannelIndex is None:
                chNdx = range(sig.shape[1])
                
            elif isinstance(self.signalChannelIndex, (tuple, list, range)):
                chNdx = self.signalChannelIndex
                
            elif isinstance(self.signalChannelIndex, slice):
                chNdx = range(*self.signalChannelIndex.indices(sig.shape[1]))
                
            else:
                raise TypeError("Unexpected channel indexing type %s" % str(type(self.signalChannelIndex)))

            self._prepareAxes_(len(chNdx), sigNames = ["%s_channel%d" % (signal_name, c) for c in chNdx])
            
            for (k, channel) in enumerate(chNdx):
                self._plot_numeric_data_(self.axis(k), 
                                         np.array(sig.times),
                                         np.array(sig[:,channel].magnitude),
                                         xlabel="%s (%s)" % (domain_name, sig.t_start.units.dimensionality),
                                         ylabel="%s (%s)\nchannel %d" % (signal_name, sig.units.dimensionality, channel), 
                                         *args, **kwargs)
                    
        else:
            self._prepareAxes_(1, sigNames = [signal_name])
            if sig.shape[1] > 10:
                self.sig_plot.emit(self._make_sig_plot_dict_(self.axis(0), np.array(sig.times), 
                                       np.array(sig.magnitude), 
                                       ylabel="%s (%s)" % (signal_name, sig.units.dimensionality), 
                                       xlabel="%s (%s)" % (domain_name, sig.times.units.dimensionality), 
                                       *args, **kwargs))
            else:
                self._plot_numeric_data_(self.axis(0), np.array(sig.times), 
                                        np.array(sig.magnitude), 
                                        ylabel="%s (%s)" % (signal_name, sig.units.dimensionality), 
                                        xlabel="%s (%s)" % (domain_name, sig.times.units.dimensionality), 
                                        *args, **kwargs)
                
        self.docTitle = sig.name
            
    def _make_sig_plot_dict_(self,plotItem: pg.PlotItem, x:np.ndarray, y:np.ndarray, xlabel:(str, type(None))=None,  ylabel:(str, type(None))=None, title:(str, type(None))=None, name:(str, type(None))=None, symbolcolorcycle:(cycle, type(None))=None, *args, **kwargs):
        return {"plotItem":plotItem, 
                "x": x, "y": y, 
                "xlabel": xlabel, "ylabel": ylabel,
                "title": title, "name": name, 
                "symbolcolorcycle": symbolcolorcycle,
                "args": args, "kwargs": kwargs}
                    
    @safeWrapper
    @pyqtSlot(dict)
    def _slot_plot_numeric_data_thr_(self, data:dict):  
        """For dict's keys and values see parameters of self._plot_numeric_data_
        For threading...
        """
        #print("_slot_plot_numeric_data_thr_")
        self.statusBar().showMessage("Working...")
        
        plotItem            = data.pop("plotItem")
        x                   = data.pop("x")
        y                   = data.pop("y")
        xlabel              = data.pop("xlabel", None)
        #xunits              = data.pop("xunits", None)
        ylabel              = data.pop("ylabel", None)
        #yunits              = data.pop("yunits", None)
        title               = data.pop("title", None)
        name                = data.pop("name", None)
        symbolcolorcycle    = data.pop("symbolcolorcycle", None)
        args                = data.pop("args", tuple())
        kwargs              = data.pop("args", dict())

        self._plot_numeric_data_(plotItem,  x, y, xlabel, ylabel,
                                title, name, symbolcolorcycle, *args, **kwargs)
        
        #self._plot_numeric_data_(plotItem,  x, y, xlabel, xunits, ylabel, yunits,
                                #title, name, symbolcolorcycle, *args, **kwargs)
        
        self.statusBar().clearMessage()
        
    @safeWrapper
    def _plot_numeric_data_(self, plotItem: pg.PlotItem, x:np.ndarray, y:np.ndarray, xlabel:(str, type(None))=None, ylabel:(str, type(None))=None, title:(str, type(None))=None, name:(str, type(None))=None, symbolcolorcycle:(cycle, type(None))=None, *args, **kwargs):
        """ The workhorse that does the actual plotting of signals
        Parameters:
        ----------
        x, y, : np.ndarray (domain and signal)
            Data to be plotted: x and y must be 1D or 2D numpy arrays with compatible 
            dimensions.
            
        xlabel, ylabel: str ; optional (defult is None) 
            Labels for the X and Y axis, respectively
        
        name:str, optional, default is None
            The name associated with the PlotDataItem (individual curve or
            scatter plot), for use in the plot legend.
            
        title:str, optional, default is None
            When present, will be displayd at the top of the  PlotItem where the
            data is plotted; can be in HTML format
        
                
        symbolcolorcycle: itertools.cycle for colors ; optional, default is None
            Used when there are several channels for the Y data
            
        args, kwargs: additional parameters for PlotItem.plot() function (and
            indirectly PlotDataItem constructor and methods).
            See pyqtgraph PlotItem.plot() and pyqtgrapg PlotDataItem
    
            symbol
        
        Returns
        ------
        a pyqtgraph.PlotItem where the data was plotted
        
        """
        # ATTENTION: y is a numpy arrays here; x is either None, or a numpy array
        
        #traceback.print_stack(limit=8)
        
        y = np.atleast_1d(y)
        
        if y.ndim > 2:
            raise TypeError("y expected to be an array with up to 2 dimensions; for %s dimensions instead" % y.ndim)
        
        dataAxis = self.dataAxis if isinstance(self.dataAxis, int) else 0
        
        # NOTE: 2019-04-06 09:37:51 
        # there are issues with SVG export of curves containing np.nan
        if x is not None:
            x = np.atleast_1d(x)
            
            if x.ndim > 2:
                raise TypeError(f"x expected to be a vector or matrix; got an array with {x.ndim} dimensions instead")
            
            if x.ndim == 2:
                if x.shape[1] > 1 and x.shape[1] != y.shape[1]:
                    raise TypeError("x expected to  either a vector or an array with %d columns; got an array with %d columns instead" % x.shape[1])
        
            if x.shape[0] != y.shape[dataAxis]:
                raise ValueError(f"x and y have different sizes: {x.shape[0]} and {y.shape[dataAxis]} on their first axes")
                #x = x.squeeze()
            
        
#         print(f"{self.__class__.__name__}._plot_numeric_data_ self.dataAxis {self.dataAxis}")
#         print(f"{self.__class__.__name__}._plot_numeric_data_ self.signalChannelAxis {self.signalChannelAxis}")
#         print(f"{self.__class__.__name__}._plot_numeric_data_ dataAxis {dataAxis}")
#         
        # NOTE: 2021-09-09 18:30:20
        # when symbol is present we don't draw the connection line
        symbol = kwargs.get("symbol", None)
        
        pen = kwargs.get("pen", QtGui.QPen(QtGui.QColor("black"),1))
        if isinstance(pen, QtGui.QPen): # because the caller may have passed 'pen=None'
            pen.setCosmetic(True)
            
        symbolPen = kwargs.get("symbolPen",QtGui.QPen(QtGui.QColor("black"),1))
        if isinstance(symbolPen, QtGui.QPen):# because the caller may have passed 'symbolPen=None'
            symbolPen.setCosmetic(True)
        
        if symbol is None:
            kwargs["pen"] = pen
            kwargs["symbolPen"] = None
            kwargs["symbol"] = None
                
        else:
            kwargs["pen"] = None
            kwargs["symbolPen"] = symbolPen
        
        plotDataItems = [i for i in plotItem.listDataItems() if isinstance(i, pg.PlotDataItem)]

        if "name" not in kwargs:
            kwargs["name"]=name
            
        if y.ndim == 1:
            y_nan_ndx = np.atleast_1d(np.isnan(y))
            
            if any(y_nan_ndx):
                yy = y[~y_nan_ndx]
                if x is not None:
                    xx = x[~y_nan_ndx,0]
                else:
                    xx =  None
                
            else:
                yy = y
                if x is not None:
                    if x.ndim > 1:
                        xx = x[:,0]
                    else:
                        xx = x
                else:
                    xx = None
                
            if yy.size == 0 or (xx is not None and xx.size == 0): # nothing left to plot
                return
            
            # print(f"{self.__class__.__name__}._plot_numeric_data_ y.ndim == 1; plotdataitem kwargs {kwargs}")
            # NOTE 2019-09-15 18:53:56:
            # FIXME find a way to circumvent clearing the plotItem in prepareAxes
            # beacuse it causes too much flicker
            # see NOTE 2019-09-15 18:53:40
            if len(plotDataItems):
                if len(plotDataItems) > 1:
                    for item in plotDataItems[1:]:
                        plotItem.removeItem(item)
                        
                plotDataItems[0].clear()
                if xx is not None:
                    plotDataItems[0].setData(x=xx, y=yy, **kwargs)
                else:
                    plotDataItems[0].setData(y=yy, **kwargs)
                
            else:
                if xx is not None:
                    plotItem.plot(x=xx, y=yy, **kwargs)
                else:
                    plotItem.plot(y=yy, **kwargs)
        
        elif y.ndim == 2:
            colors = cycle(self.defaultLineColorsList)
            
            if y.shape[1] < len(plotDataItems):
                for item in plotDataItems[y.shape[1]:]:
                    plotItem.removeItem(item)
            
            for k in range(y.shape[self.signalChannelAxis]):
                y_ = np.atleast_1d(y[array_slice(y, {self.signalChannelAxis:k})].squeeze())
                
                #print("y_.shape", y_.shape)
                
                if y_.ndim ==2 and x.shape[0] == y_.shape[1]:
                    y_ = y_.T
                    
                if x is not None:
                    if x.ndim == 2 and x.shape[1] == y.shape[self.signalChannelAxis]:
                        x_ = np.atleast_1d(x[:,k].squeeze())
                        
                    else:
                        x_ = np.atleast_1d(x.squeeze())
                        
                else:
                    x_ = None
                    
                y_nan_ndx = np.isnan(y_)
                
                if any(y_nan_ndx): # np.bool_ not iterable in numpy 1.21.2
                    yy = y_[~y_nan_ndx]
                    if x_ is not None:
                        xx = x_[~y_nan_ndx]
                    else:
                        xx = None
                    
                else:
                    yy = y_
                    xx = x_
                
                # if xx.size == 0 or yy.size == 0: # nothing left to plot
                if yy.size == 0 or (xx is not None and xx.size == 0):
                    continue
                    
                if symbol is None:
                    if isinstance(colors, cycle):
                        pen = QtGui.QPen(QtGui.QColor(next(colors)))
                        pen.setCosmetic(True)
                    
                        kwargs["pen"] = pen
                    else:
                        kwargs["pen"] = pen # same pen as defined above!
                    
                    kwargs["symbol"] = None
                    
                else:
                    kwargs["pen"] = None
                    
                    if isinstance(symbolcolorcycle, cycle):
                        symbolPen = QtGui.QPen(QtGui.QColor(next(symbolcolorcycle)), 1)
                        symbolPen.setCosmetic(True)
                        kwargs["symbolPen"] = symbolPen
                        
                    else:
                        kwargs["symbolPen"] = symbolPen # same symbol pen as defined above!
                        
                # print(f"{self.__class__.__name__}._plot_numeric_data_ y.ndim == 2; k = {k}; plotdataitem kwargs {kwargs}")
                if k < len(plotDataItems):
                    plotDataItems[k].clear()
                    if xx is not None:
                        plotDataItems[k].setData(x = xx, y = yy, **kwargs)
                    else:
                        plotDataItems[k].setData(y = yy, **kwargs)
                    
                else:
                    if xx is not None:
                        plotItem.plot(x = xx, y = yy, **kwargs)
                    else:
                        plotItem.plot(y = yy, **kwargs)

        
        plotItem.setLabels(bottom = [xlabel], left=[ylabel])
        
        plotItem.setTitle(title)
        
        plotItem.replot()
        
        if plotItem is self._current_plot_item_:
            lbl = "<B>%s</B>" % self._current_plot_item_.axes["left"]["item"].labelText
            self._current_plot_item_.setLabel("left", lbl)
            
        else:
            lbl = plotItem.axes["left"]["item"].labelText
            
            if lbl.startswith("<B>") and lbl.endswith("</B>"):
                lbl = lbl[3 : lbl.find("</B>")]
                plotItem.setLabel("left", lbl)
        
        return plotItem
    
    def _remove_axes_(self, plotItem:pg.PlotItem):
        cursors = self.cursorsInAxis(plotItem)
        k = self.axes.index(plotItem)
        if len(cursors):
            for cursor in cursors:
                cursor.detach() # option (b)

            # see NOTE: 2019-03-08 13:20:50
            self._cached_cursors_[k] = cursors
                            
        # plotItem.vb.close()
        plotItem.close()
        self.signalsLayout.removeItem(plotItem)
        if self.currentAxis == plotItem:
            self.currentAxis = self.axes[0]
           
    @safeWrapper
    def _prepareAxes_(self, nRequiredAxes, sigNames=list()):
        """sigNames: a sequence of str or None objects - either empty, or with as many elements as nRequiredAxes
        """
        plotitems = self.plotItems
        
        if not isinstance(sigNames, (tuple, list)):
            raise TypeError("Expecting sigNames to be a sequence; got %s instead" % type(sigNames).__name__)
        
        if len(sigNames):
            if len(sigNames) != nRequiredAxes:
                raise ValueError("mismatch between number of signal names in sigNames (%d) and the number of new axes (%d))" % (len(sigNames), nRequiredAxes))
            
            elif not all([isinstance(s, (str, type(None))) for s in sigNames]):
                raise TypeError("sigNames sequence must contain only strings, or None objects")
            
        else: # enforce naming of plot items!!!
            sigNames = ["signal_%d" % k for k in range(nRequiredAxes)]
            
        if nRequiredAxes == len(plotitems):
            #### requires as many axes as there already are;
            # number of axes not to be changed -- just update the names of the plotitems
            # see NOTE: 2019-03-07 09:53:38
            for k in range(len(plotitems)):
                plotitem = self.signalsLayout.getItem(k, 0)
                
                if isinstance(plotitem, pg.PlotItem):
                    plotDataItems = [i for i in plotitem.listDataItems() if isinstance(i, pg.PlotDataItem)]
                    
                    for plotdataitem in plotDataItems:
                        plotdataitem.clear()
                        
                    self._plot_names_[k] = sigNames[k]
                    
                    try:
                        plotitem.vb.unregister()
                        plotitem.vb.register(sigNames[k])
                        plotitem.vb.name=sigNames[k]
                        
                    except:
                        if plotitem.vb.name in plotitem.vb.NamedViews:
                            plotitem.vb.NamedViews.pop(plotitem.vb.name, None)
                            plotitem.vb.NamedViews[sigNames[k]] = plotitem.vb
                            plotitem.vb.updateAllViewLists()
                            sid = id(plotitem.vb)
                            plotitem.vb.destroyed.connect(lambda: plotitem.vb.forgetView(sid, name) if (plotitem.vb is not None and 'sid' in locals() and 'name' in locals()) else None)
                            
                    # deal with any cursors that may exist here:
                    cursors = self.cursorsInAxis(plotitem)
                    self._cached_cursors_[k] = cursors
                        
            return
            
        if nRequiredAxes == 0:
            # no axes required => clear all plots
            if len(plotitems):
                cursors = [c for c in self.crosshairSignalCursors.values()] + \
                          [c for c in self.verticalSignalCursors.values()] + \
                          [c for c in self.horizontalSignalCursors.values()]
                      
                for plotitem in plotitems:
                    for c in cursors:
                        c.detach()
            
            for clist in self._cached_cursors_.values(): # dict of lists of cursors!
                for c in clist:
                    c.detach()
                
            # FIXME there are issues in pyqtgraph when ViewBox objects are deleted from "outside" - maybe fixed already ?!?
            #if self.signalsLayout.scene() is not None:
                #self.signalsLayout.clear()
                
            for plotitem in plotitems:
                self._remove_axes_(plotitem)
                # self.signalsLayout.removeItem(plotitem)
                
            self._plot_names_.clear()
                
            self.crosshairSignalCursors.clear()
            self.verticalSignalCursors.clear()
            self.horizontalSignalCursors.clear()
            
            self._cached_cursors_.clear()
            
        else:   # FIXME there are issues with ViewBox being deleted in pyqtgraph! - maybe fixed already - ?!?
            if nRequiredAxes < len(plotitems):
                #### requires fewer axes than there currently are:
                # adapt existing plotitems then remove extra axes (plot items)
                
                #### BEGIN adapt existing plot items
                for k in range(nRequiredAxes): 
                    plotitem = self.signalsLayout.getItem(k, 0)
                    self._plot_names_[k] = sigNames[k]
                    # make sure no cached cursors exist for these plotitems
                    self._cached_cursors_.pop(k, None)
                    
                    # NOTE: 2019-03-07 09:53:38 change the name of plotitems to preserve
                    if isinstance(plotitem, pg.PlotItem):
                        plotDataItems = [i for i in plotitem.listDataItems() if isinstance(i, pg.PlotDataItem)]
                        
                        for plotdataitem in plotDataItems:
                            plotdataitem.clear()
                        
                        try:
                            plotitem.vb.unregister()
                            plotitem.vb.register(sigNames[k]) # always update this!
                            plotitem.vb.name=sigNames[k]
                            
                        except:
                            if plotitem.vb.name is not None:
                                if plotitem.vb.name in plotitem.vb.NamedViews:
                                    plotitem.vb.NamedViews.pop(plotitem.vb.name, None)
                                    plotitem.vb.NamedViews[sigNames[k]] = plotitem.vb
                                    plotitem.vb.updateAllViewLists()
                                    sid = id(plotitem.vb)
                                    plotitem.vb.destroyed.connect(lambda: plotitem.vb.forgetView(sid, name) if (plotitem.vb is not None and 'sid' in locals() and 'name' in locals()) else None)
                                    
                #### END adapt existing plot items          
                
                # NOTE: 2019-02-07 23:21:55
                # if fewer plot items are needed than they currenty exist,
                # remove the extra ones
                #
                # the consequence is that a signal plotted on a plot item at 
                # some position (index in the layout) may now be plotted on a
                # pre-existing plot item at a different position ("left behind")
                # that's allright until we have to manage the cursors of the plot
                # item(s) that are to be removed
                #
                # TODO there are two options:
                #
                # a) simple option: also lose the cursor registered with
                # the plotitem that will be removed
                #
                # b) cache the cursor and wait until a new plotitem is constructed,
                # to plot the data of a signal with the same name
                #
                # CAUTION: what if the name is the same
                # but it represents something else altogether? i.e.different scales etc
                #
                # Anyway, it is bad practice to have a neo.Block with segments 
                # that contain different numbers of signals in their fields (analogsignals,
                # irregularlysampledsignals, etc). However this can happen !
                #
                # So we would need to "detach" the cursor, then "attach" it to the new
                # plot item plotting a signal with same name when it comes back
                # -- pretty convoluted
                #
                # step-by-step:
                # 1. cache the cursors in the to-be-removed plot item by storing
                # references in a list, in a dictionare keyed on the signal's name
                # 2. when the signal's name become available again (in another segment)
                # then attached the cached cursors to the corresponding (new) plot item
                
                #### BEGIN remove extra plot items
                for k in range(nRequiredAxes, len(plotitems)):
                    plotitem = self.signalsLayout.getItem(k, 0)
                    
                    if isinstance(plotitem, pg.PlotItem):# and plotitem in self.__plot_items__:
                        # are there any cursors in this plotitem?
                        cursors = self.cursorsInAxis(plotitem)
                        
                        if len(cursors):
                            for cursor in cursors:
                                cursor.detach() # option (b)

                            # see NOTE: 2019-03-08 13:20:50
                            self._cached_cursors_[k] = cursors
                            
                        self._remove_axes_(plotitem)
                        self._plot_names_.pop(k, None)
                #### END remove extra plot items
                
            elif nRequiredAxes > len(plotitems):
                # requires more axes that there actually are:
                # adapt existing plotitems then add new axes
                
                #### BEGIN adapt existing plot items
                for k in range(len(plotitems)): # see NOTE: 2019-03-07 09:53:38
                    plotitem = self.signalsLayout.getItem(k, 0)
                    self._plot_names_[k] = sigNames[k]
                    
                    # clear cached cursors for these:
                    self._cached_cursors_.pop(k, None)
                    
                    # NOTE 2019-09-15 18:53:40:
                    # FIXME: this creates a nasty flicker but if we don't call
                    # it we'll get a nasty stacking of curves
                    plotitem.clear()
                    
                    # now update plotitem's registered namme
                    if isinstance(plotitem, pg.PlotItem):# and plotitem.vb.name is None:
                        try:
                            plotitem.vb.unregister()
                            plotitem.vb.register(sigNames[k])
                            plotitem.vb.name=sigNames[k]
                        except:
                            if plotitem.vb.name is not None:
                                if plotitem.vb.name in plotitem.vb.NamedViews:
                                    plotitem.vb.NamedViews.pop(plotitem.vb.name, None)
                                    plotitem.vb.NamedViews[sigNames[k]] = plotitem.vb
                                    plotitem.vb.updateAllViewLists()
                                    sid = id(plotitem.vb)
                                    plotitem.vb.destroyed.connect(lambda: plotitem.vb.forgetView(sid, name) if (plotitem.vb is not None and 'sid' in locals() and 'name' in locals()) else None)
                
                #### END adapt existing plot items
                
                #### BEGIN add more plotitems as required
                for k in range(len(plotitems), nRequiredAxes):
                    plotitem = self.signalsLayout.addPlot(row=k, col=0)
                    plotitem.register(sigNames[k])
                    self._plot_names_[k] = sigNames[k]
                    
                    plotitem.sigXRangeChanged.connect(self._slot_plot_axis_x_range_changed)
                    
                    # restore cached cursors if any
                    cursors = self._cached_cursors_.get(k, None)
                    
                    if isinstance(cursors, (tuple, list)) and len(cursors):
                        for c in cursors:
                            c.attach(plotitem)
                            
                #### END add more plotitems as required
                        
            p0 = None
            
            plotitems = sorted([i for i in self.signalsLayout.items.items()], key = lambda x: x[1][0])
            
            if len(plotitems):
                p0 = self.signalsLayout.getItem(0,0)
                
                if isinstance(p0, pg.PlotItem):
                    for k in range(1,len(plotitems)):
                        plotitem = self.signalsLayout.getItem(k,0) # why would this return None?
                        if isinstance(plotitem, pg.PlotItem):
                            plotitem.setXLink(p0)
                        
            # FIXME this shouldn't really be here? if it's already connected then what?
            if self.signalsLayout.scene() is not None:
                self.signalsLayout.scene().sigMouseClicked.connect(self._slot_mouseClickSelectPlotItem)
                
            if nRequiredAxes == 1:
                p = self.signalsLayout.getItem(0,0)
                #reattach multi-axes cursors
                for c in [c for c in self._data_cursors_.values() if c.isDynamic]:
                    c.detach()
                    c.attach(p)
                    
        # connect plot items scene hover events to report mouse cursor coordinates
        for p in self.axes:
            if p.scene():
                p.scene().sigMouseMoved[object].connect(self._slot_mouseMovedInPlotItem)
                p.scene().sigMouseHover[object].connect(self._slot_mouseHoverInPlotItem)
            
                
    @pyqtSlot(object)
    @safeWrapper
    def _slot_mouseHoverInPlotItem(self, obj): 
        """ Connected to a PlotItem's scene sigMouseHover signal.
        
        The signal does NOT report mouse position!
        
        obj should be a list of PlotItem objects, 
        technically with just one element
        """
        #print("mouse hover in", obj)
        
        if len(self.axes) == 0:
            return
        
        #system_palette = QtGui.QGuiApplication.palette()
        #default_border_color = self.axis(0).vb.border.color()
        
        if len(obj) and isinstance(obj[0], pg.PlotItem):
            self._focussed_plot_item_ = obj[0]
        else:
            self._focussed_plot_item_ = None
            
    @pyqtSlot(object)
    @safeWrapper
    def _slot_mouseMovedInPlotItem(self, pos): # pos is a QPointF
        # connected to a PlotItem's scene!
        # at this stage there should already be a _focussed_plot_item_
        if isinstance(self._focussed_plot_item_, pg.PlotItem):
            self._reportMouseCoordinatesInAxis_(pos, self._focussed_plot_item_)
                
        else:
            self._update_coordinates_viewer_()
            
    @safeWrapper
    def _reportMouseCoordinatesInAxis_(self, pos, plotitem):
        if isinstance(plotitem, pg.PlotItem):
            if plotitem.sceneBoundingRect().contains(pos):
                plots, rc = zip(*self.plotItemsWithLayoutPositions)
                
                if plotitem in plots:
                    plot_index = plots.index(plotitem)
                    
                    plot_row = rc[plot_index][0][0]
                    
                    plot_name = self._plot_names_.get(plot_row, "")
                    
                else:
                    plot_name = ""
                
                mousePoint = plotitem.vb.mapSceneToView(pos)
                
                x_text = "%f" % mousePoint.x()
                y_text = "%f" % mousePoint.y()
                
                display_text = "X: %s; Y: %s" % (x_text, y_text)
                
                self._mouse_coordinates_text_ = "%s:\n%s" % (plot_name, display_text)
                
                self.statusBar().showMessage(self._mouse_coordinates_text_)
                
            else:
                self.statusBar().clearMessage()
                
            self._update_coordinates_viewer_()
    
    def _update_coordinates_viewer_(self):
        self.coordinatesViewer.setPlainText(self._cursor_coordinates_text_)
        
    @pyqtSlot(object)
    @safeWrapper
    def _slot_mouseClickSelectPlotItem(self, evt):
        focusItem = self.sender().focusItem()
        
        if len(self.axes) == 0:
            return
        
        #system_palette = QtGui.QGuiApplication.palette()
        #default_border_color = self.axis(0).vb.border.color()
        
        if isinstance(focusItem, pg.ViewBox):
            plotitems, rc = zip(*self.axesWithLayoutPositions)
            
            focusedPlotItems = [i for i in plotitems if i.vb is focusItem]
            
            if len(focusedPlotItems):
                self._current_plot_item_ = focusedPlotItems[0]
                plot_index = plotitems.index(self._current_plot_item_)
                self._current_plot_item_index_ = plot_index
                self._setAxisIsActive(self._current_plot_item_, True)
                self._statusNotifyAxisSelection(plot_index)
                    
                for ax in self.axes:
                    if ax is not self._current_plot_item_:
                        self._setAxisIsActive(ax, False)
                            
            else:
                self._current_plot_item_ = None
                self._current_plot_item_index_ = -1
                
                for ax in self.axes:
                    self._setAxisIsActive(ax, False)

        else:
            self._current_plot_item_ = None
            self._current_plot_item_index_ = -1

            for ax in self.axes:
                self._setAxisIsActive(ax, False)
#                 lbl = ax.axes["left"]["item"].labelText
#                 
#                 if lbl.startswith("<B>") and lbl.endswith("</B>"):
#                     lbl = lbl[3 : lbl.find("</B>")]
#                     ax.setLabel("left", lbl)
#                     
#                 ax.vb.border.setStyle(QtCore.Qt.NoPen)
            
    @safeWrapper
    def clearEpochs(self):
        self._plotEpochs_()
                
    @safeWrapper
    def clear(self, keepCursors=False):
        """
        TODO: cache cursors when keepCursors is True
        at the moment do NOT pass keepCcursor other than False!
        need to store axis index witht he cursors so that we can restore it ?!?
        """
        #self.fig.clear() # both mpl.Figure and pg.GraphicsLayoutWidget have this method
        #print("SignalViewer.clear() %s" % self.windowTitle())
        self._current_plot_item_ = None
        self._current_plot_item_index_ = -1
        self._focussed_plot_item_ = None
        
        for p in self.plotItems:
            self._remove_axes_(p)
            # self.signalsLayout.removeItem(p)

        self.plotTitleLabel.setText("")
        
        for c in self.crosshairSignalCursors.values():
            c.detach()
            
        for c in self.verticalSignalCursors.values():
            c.detach()
            
        for c in self.horizontalSignalCursors.values():
            c.detach()
            
        for clist in self._cached_cursors_.values():
            for c in clist:
                c.detach()
            
        if not keepCursors:
            self.crosshairSignalCursors.clear() # a dict of SignalCursors mapping str name to cursor object
            self.verticalSignalCursors.clear()
            self.horizontalSignalCursors.clear()
            self._cached_cursors_.clear()
            
            self.linkedCrosshairCursors = []
            self.linkedHorizontalCursors = []
            self.linkedVerticalCursors = []
        
        self.signalNo = 0
        self.frameIndex = [0]
        self.signalIndex = 1 # NOTE: 2017-04-08 23:00:48 in effect number of signals /frame !!!
        
        self.guiSelectedSignalNames.clear()
        
        self.guiSelectedIrregularSignalNames.clear()
        
        self.yData = None
        self.xData = None
        
        self.plot_start = None
        self.plot_stop = None
        
        self._plotEpochs_()
        
        self._number_of_frames_ = 0
        
        # NOTE: 2018-09-25 23:12:46
        # recipe to block re-entrant signals in the code below
        # cleaner than manually docinenctign and re-connecting
        # and also exception-safe
        
        signalBlockers = [QtCore.QSignalBlocker(widget) for widget in \
            (self.selectSignalComboBox, self.selectIrregularSignalComboBox,
             self.framesQSlider, self.framesQSpinBox)]
        
        self.selectSignalComboBox.clear()
        self.selectIrregularSignalComboBox.clear()
        self.framesQSlider.setMinimum(0)
        self.framesQSlider.setMaximum(0)
        self.framesQSpinBox.setMinimum(0)
        self.framesQSpinBox.setMaximum(0)
        self.nFramesLabel.setText(f"of {self._number_of_frames_}")
        self.docTitle = None # to completely remove the data name from window title
        
    def setTitlePrefix(self, value):
        """Sets the window-specific prefix of the window title
        """
        if isinstance(value, str) and len(value.strip()) > 0:
            self._winTitle_ = value
        else:
            self._winTitle_ = "SignalViewer%d" % self._ID_

        if isinstance(self._docTitle_, str) and len(self._docTitle_.strip()) > 0:
            self.setWindowTitle("%s - %s" % (self._winTitle_, self._docTitle_))
        else:
            self.setWindowTitle(self._winTitle_)
    
            
    @property
    def cursors(self):
        """A list with all defined SignalCursors.
        ATTENTION: the list is NOT ordered.
        """
        return list(self._data_cursors_.values())
    
    @property
    def dataCursors(self):
        """Alias to cursors property
        """
        return self.cursors
    
    # aliases to setData
    plot = setData
    view = setData
    
        
