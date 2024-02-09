# -*- coding: utf-8 -*-
'''Signal viewer: enhanced signal plotter

Plots a multi-frame 1D signal (i.e. a matrix where each column is a `frame'), one frame at a time. 

Data is plotted using Pyqtgraph framework

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

'''
#### BEGIN core python modules
#from __future__ import print_function

# NOTE: 2022-12-25 23:08:51
# needed for the new plugins framework
__scipyen_plugin__ = None

from pprint import pprint

import sys, os, traceback, numbers, warnings, weakref, inspect, typing, math

import collections
from collections.abc import Iterable
from functools import partial, singledispatch, singledispatchmethod
from itertools import (cycle, accumulate, chain, pairwise)
from operator import attrgetter, itemgetter, methodcaller
from enum import Enum, IntEnum
from dataclasses import MISSING

from traitlets import Bunch


#### END core python modules

#### BEGIN 3rd party modules
from PyQt5 import QtCore, QtGui, QtWidgets, QtSvg
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.uic import loadUiType as __loadUiType__

import math
import numpy as np
import pandas as pd
from pandas import NA
# import pyqtgraph as pg
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


#### END 3rd party modules

#### BEGIN pict.iolib modules
from iolib import pictio as pio
#### END pict.iolib modules

#### BEGIN pict.core modules
import core.signalprocessing as sgp
from core import (xmlutils, strutils, neoutils, )
import core.quantities as scq
from core.neoutils import (get_domain_name,
                           get_non_empty_spike_trains,
                           get_non_empty_events,
                           get_non_empty_epochs,
                           normalized_signal_index,
                           check_ephys_data, 
                           check_ephys_data_collection,
                           set_relative_time_start,
                           segment_start,
                           )

from core.prog import (safeWrapper, show_caller_stack, with_doc)
from core.datatypes import (array_slice, is_column_vector, is_vector, )

from core.utilities import (normalized_index, normalized_axis_index, 
                            normalized_sample_index, counter_suffix,
                            safe_identity_test)
from core.datasignal import (DataSignal, IrregularlySampledDataSignal,)
from core.triggerprotocols import TriggerProtocol
# NOTE: 2021-11-13 16:27:30
# new types: DataMark and DataZone
from core.triggerevent import (TriggerEvent, TriggerEventType, DataMark)
from core.datazone import (DataZone, Interval, intervals2epoch, epoch2cursors)
from core.workspacefunctions import validate_varname
from core.scipyen_config import markConfigurable
from core.traitcontainers import DataBag

from core.strutils import (InflectEngine, get_int_sfx)

from core.sysutils import adapt_ui_path

from imaging.vigrautils import kernel2array

from ephys import ephys as ephys
# from ephys.ephys import cursors2epoch

#from core.patchneo import *

#### BEGIN gui modules
#from . import imageviewer as iv
# pg.Qt.lib = "PyQt5"
from gui.pyqtgraph_patch import pyqtgraph as pg
from gui import guiutils as guiutils
from gui import pictgui as pgui
from gui import quickdialog as qd
from gui import scipyen_colormaps as colormaps

from gui.scipyenviewer import (ScipyenViewer, ScipyenFrameViewer,Bunch)
from gui.dictviewer import (InteractiveTreeWidget, DataViewer,)
from gui.cursors import (DataCursor, SignalCursor, SignalCursorTypes, cursors2epoch)
from gui.widgets.colorwidgets import ColorSelectionWidget, quickColorDialog
from gui.pictgui import GuiWorker
from gui.itemslistdialog import ItemsListDialog
from gui import guiutils # should also register the new symbols

#### END gui modules

SIGNAL_OBJECT_TYPES = (neo.AnalogSignal, neo.IrregularlySampledSignal,
                       DataSignal, IrregularlySampledDataSignal)

EVENT_OBJECT_TYPES = (neo.Event, DataMark, TriggerEvent)

EPOCH_OBJECT_TYPES = (neo.Epoch, DataZone) # NOTE: pyabf Epoch must be converted

"""
canvas events in matplotlib:
DEPRECATED here, but keep for reference
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
__ui_path__ = adapt_ui_path(__module_path__,'signalviewer.ui')

# Ui_SignalViewerWindow, QMainWindow = __loadUiType__(os.path.join(__module_path__,'signalviewer.ui'))
Ui_SignalViewerWindow, QMainWindow = __loadUiType__(__ui_path__)

class SignalViewer(ScipyenFrameViewer, Ui_SignalViewerWindow):
    """ A plotter for multi-sweep signals ("frames" or "segments"), with cursors.
    
        Python data types handled by SignalViewer as of 2019-11-23 11:30:23:
        --------------------------------------------------------------------
        NOTE: see also Glossary of terms, below
        
        neo.Block
        neo.Segment
        neo.AnalogSignal
        neo.IrregularlySampledSignal
        datasignal.DataSignal
        datasignal.IrregularlySampledDataSignal
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
        at regular intervals. In Scipyen, neo.AnalogSignal, datasignal.DataSignal,
        and numpy arrays (including Vigra Arrays) all represent regularly sampled
        signals.
        
        Irregularly sampled signals are generated by sampling analog data at 
        arbitrary points of the signal domain. These are represented by
        neo.IrregularlySampledSignal and datasignal.DataSignal.
        
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
    # NOTE: 2023-01-01 15:29:48
    # Radical API change:
    #
    # • Current approach using dynamically created PlotItems (and deleting them
    #   wich each data frame) does not quite cut it, because of issues with 
    #   delected C++ pointer (PlotItem instance) and with managing cursors linked
    #   to that PlotItem instance.
    #
    # • Instead, we need need to pre-determine the maximum number of PlotItems 
    #   based on the data type  - delegate to _parse_data_
    #   Axis selection form the GUI should then only set which PlotItem is visible
    #  
    #
    # • The number of axes should be set as follows:
    #
    #   ∘ for neo.Block: the maximum number of signals in all sweeps (analog AND
    #       irregular) + 2 (one axis for events, one for spike trains)
    #
    #   ∘ for a neo.Segment: the number of signals (analog + irregular)
    #       PLUS one axis for spike trains + 2 (see above)
    #
    #   ∘ for a sequence of Segments  - treat as for Block
    #
    #   ∘ for a sequence of signals (analog or irregular): the number of axes is
    #       the number of signals in the sequence, or 1 (one) is signals are to
    #       be shown as separate frames
    #
    #   ∘ for numpy arrays: number of axes is determined by the signalChannelAxis
    #       and frameAxis
    #
    #   ∘ for a sequence of numpy arrays: determined according to the signalChannelAxis
    #
    #   ∘ for a sequence of DataZone, DataMarker, events, epochs, spiketrains:
    #       one axis for eech of this type, per frame
    
    


    #dockedWidgetsNames = ["cursorsDockWidget"]

    sig_activated = pyqtSignal(int, name="sig_activated")
    sig_plot = pyqtSignal(dict, name="sig_plot")
    sig_newEpochInData = pyqtSignal(name="sig_newEpochInData")
    sig_axisActivated = pyqtSignal(int, name="sig_axisActivated")
    sig_frameDisplayReady = pyqtSignal(name="sig_frameDisplayReady")
    
    closeMe  = pyqtSignal(int)
    frameChanged = pyqtSignal(int)
    
    # TODO: 2019-11-01 22:43:50
    # implement viewing for all these
    viewer_for_types = {neo.Block: 99, 
                        neo.Segment: 99, 
                        neo.AnalogSignal: 99, 
                        DataSignal: 99, 
                        neo.IrregularlySampledSignal: 99,
                        IrregularlySampledDataSignal: 99,
                        neo.SpikeTrain: 99, 
                        neo.Event: 99,
                        neo.Epoch: 99, 
                        neo.core.spiketrainlist.SpikeTrainList:99,
                        neo.core.baseneo.BaseNeo: 99,
                        TriggerEvent: 99,
                        TriggerProtocol: 99,
                        vigra.filters.Kernel1D: 99, 
                        pq.Quantity: 99,
                        np.ndarray: 99,
                        tuple: 99, 
                        list: 99}
    
    # view_action_name = "Signal"
        
    defaultCursorWindowSizeX = 0.001
    defaultCursorWindowSizeY = 0.001
    
    defaultCursorLabelPrecision = SignalCursor.default_precision
    
    defaultCursorsShowValue = False
    defaultXAxesLinked = False
    defaultXGrid = False
    defaultYGrid = False
    

    mpl_prop_cycle = plt.rcParams['axes.prop_cycle']
    
    defaultLineColorsList = ["#000000"] + ["blue", "red", "green", "cyan", "magenta", "yellow"]  + mpl_prop_cycle.by_key()['color']
    #defaultLineColorsList = ["#000000"] + list((QtGui.QColor(c).name(QtGui.QColor.HexArgb) for c in ("blue", "red", "green", "cyan", "magenta", "yellow")))  + mpl_prop_cycle.by_key()['color']
    
    defaultOverlaidLineColorList = (mpl.colors.rgb2hex(mpl.colors.to_rgba(c, alpha=0.5)) for c in defaultLineColorsList)
        
    defaultSpikeColor    = mpl.colors.rgb2hex(mpl.colors.to_rgba("xkcd:navy"))
    defaultEventColor    = mpl.colors.rgb2hex(mpl.colors.to_rgba("xkcd:crimson"))
    defaultEpochColor    = mpl.colors.rgb2hex(mpl.colors.to_rgba("xkcd:coral"))
    
    defaultIrregularSignalSymbols = list(pg.graphicsItems.ScatterPlotItem.Symbols.keys())
    defaultIrregularSignalPen = None
    defaultIrregularSignalSymbolPenWidth = 1
    defaultIrregularSignalSymbolPenColor = "#000000"
    defaultIrregularSignalSymbolPen = pg.mkPen({"color":defaultIrregularSignalSymbolPenColor,
                                               "width":defaultIrregularSignalSymbolPenWidth})
    defaultIrregularSignalSymbolSize = 10
    defaultIrregularSignalSymbolColor = "#000000"
    defaultIrregularSignalSymbolBrush = pg.mkBrush(defaultIrregularSignalSymbolColor)
    
    
    default_antialias = True
    
    defaultCursorColors = Bunch({"crosshair":"#C173B088", "horizontal":"#B1D28F88", "vertical":"#ff007f88"})
    defaultLinkedCursorColors = Bunch({"crosshair":QtGui.QColor(defaultCursorColors["crosshair"]).darker().name(QtGui.QColor.HexArgb),
                                       "horizontal":QtGui.QColor(defaultCursorColors["horizontal"]).darker().name(QtGui.QColor.HexArgb),
                                       "vertical":QtGui.QColor(defaultCursorColors["vertical"]).darker().name(QtGui.QColor.HexArgb)})
    
    defaultCursorHoverColor = "red"

    def __init__(self, x: (neo.core.baseneo.BaseNeo, DataSignal, IrregularlySampledDataSignal, TriggerEvent, TriggerProtocol, vigra.filters.Kernel1D, np.ndarray, tuple, list, type(None)) = None, y: (neo.core.baseneo.BaseNeo, DataSignal, IrregularlySampledDataSignal, TriggerEvent, TriggerProtocol, vigra.filters.Kernel1D, np.ndarray, tuple, list, type(None)) = None, parent: (QtWidgets.QMainWindow, type(None)) = None, ID:(int, type(None)) = None, win_title: (str, type(None)) = None, doc_title: (str, type(None)) = None, frameIndex:(int, tuple, list, range, slice, type(None)) = None, frameAxis:(int, type(None)) = None, signalIndex:(str, int, tuple, list, range, slice, type(None)) = None, signalChannelAxis:(int, type(None)) = None, signalChannelIndex:(int, tuple, list, range, slice, type(None)) = None, irregularSignalIndex:(str, int, tuple, list, range, slice, type(None)) = None, irregularSignalChannelAxis:(int, type(None)) = None, irregularSignalChannelIndex:(int, tuple, list, range, slice, type(None)) = None, separateSignalChannels:bool = False, singleFrame:bool=False, interval:(tuple, list) = None, channelIndex:object = None, currentFrame:(int, type(None)) = None, plotStyle: str = "plot", nAxes:typing.Optional[int] = None,*args, **kwargs):
        """SignalViewer constructor.
        TODO: Write docstring!
        """
        super(QMainWindow, self).__init__(parent)
        
        self.threadpool = QtCore.QThreadPool()

        # NOTE: 2023-04-26 12:07:26
        # for each axis, the following has a tuple of offset, factor
        # where:
        # • offset is the difference between the view range leftmost point and
        #   the leftmost domain value
        # • factor is the ratio between the vew range and data domain range
        self._axes_X_view_offsets_scales_ = list()
        
        # a cache of x data bounds for all axes
        self._x_data_bounds_ = list()
        
        self._axes_X_view_ranges_ = list()
        
        # define these early
        self._xData_ = None
        self._yData_ = None
        
        self._var_notified_ = False
        
        self._cached_title = None
        
        self._show_legends_ = False
        self._ignore_empty_spiketrains_ = True
        self._common_axes_X_padding_ = 0.
        
        # self._axes_range_changed_manually_ = list()
        
        # NOTE: 2023-01-04 22:06:48
        # guard against replotting signals when there's no actual frame change
        # when True, ALL signals in the data "frame" are (re)plotted - subject to the signal selectors
        self._new_frame_ = True
        
        self._plot_names_ = dict() # maps item row position to name
        
        self._cursorWindowSizeX_ = self.defaultCursorWindowSizeX
        self._cursorWindowSizeY_ = self.defaultCursorWindowSizeY
        
        self._editCursorOnCreation_ = False
        
        self._crosshairSignalCursors_ = dict() # a dict of SignalCursors mapping str name to cursor object
        self._verticalSignalCursors_ = dict()
        self._horizontalSignalCursors_ = dict()
        self._cursorHoverColor_ = self.defaultCursorHoverColor
        self._data_cursors_ = collections.ChainMap(self._crosshairSignalCursors_, self._horizontalSignalCursors_, self._verticalSignalCursors_)
        # maps signal name with list of cursors
        # NOTE: 2019-03-08 13:20:50
        # map plot item index (int) with list of cursors
        # NOTE: 2023-01-01 22:48:10
        # map plot item inde (int) with a dict signame name ↦ cursor(s)
        # this seems like redudant information, but when deleting axes we may 
        # get a different PlotItem at the same index; knowing the original
        # plotitem's registered name we can re-attach the cursor to a new plotitem
        # showing the same signal name (even though it's not the same signal)
        #
        # There are some alternatives to avoid this:
        #
        # 1) Prepare a set number of axes based on data content, in _parse_data_().
        #
        #   The advantage is that the PlotItems are created ONCE for the life-time
        #   of a plot. When one signal is chosen among the available ones using
        #   the combo boxes, all we have to do is to alter the isVisible flag
        #   of the PlotItems we want to "hide".
        #
        #   The downside is that we need to have the whole data in advance which 
        #   may not be always feasible.
        #
        #   For data "streamed in" we would have to use a preset number of axes 
        #   to plot data as it arrives with the risk of ending up with unused
        #   PlotItems, or with not enough PlotItems, "down the road".
        #
        #   This may not seem to be a problem, when we know in advance how many
        #   signals are streamed in, BUT does not preclude dynamic changes to
        #   the streamed data.
        #
        # 2) Associate the cursors with the signal itself. This MAY work with
        #   signal objects, where the cursor(s) could be in principle contained 
        #   in a signal attribute.
        #
        #   The downside of this is that SignalCursor instances cannot be serialized
        #   (e.g., cannot be pickled) so this approach would require creating a
        #   cursor proxy structure (with coordinates, ID and cursor type) to be 
        #   stored with the signal (as one of its attribute) which would then
        #   have to be used to recreate the original SignalCursor in whatever 
        #   PlotItem the signal happens to be drawn at a later time. 
        #
        #   Aside from bloating the code even more that it already is, this 
        #   approach does not work for signal-like objects such as vigra Kernel 
        #   and numeric arrays.
        #
        # 3) cache any cursors are present in the PlotItem, linked with the 
        #   current plotitem index. This is what it is being done at the moment 
        #   (2023-01-01 23:09:27).
        #
        #   The down side is that, whgen selecting only one signal, the index of
        #   the signal's PlotItem is likely to change.
        #   For example, say you choose to plot only the 3rd signal in a segment 
        #   (initially shown in PlotItem index 2 with a cursor) and hide the other
        #   signals; then, the chosen signal will be plotted in a new PlotItem
        #   with index 0 ('cause you're only visualising one signal) hence the 
        #   cache won't help (because the cursor was cached linked to the index
        #   of the PlotItem and nothing else more specific)
        #
        #   If the cursors were also mapped to the signal's name, then it would 
        #   be easier to track down where to show the cursors if the index of
        #   the PlotItem with the visualised signal has changed.
        #
        #   The disadvantage is that we'd have to generate a signal name for every
        #   signal-like that is not actually a structured signal object (e.g. a 
        #   column in a numpy array). While this can be done automatically for
        #   numpy arrays, simply appending the column index in the array to some
        #   prefix (e.g. 'signal_0' etc) this approach will re-generate these names
        #   whenever we select a subset of the available signals to plot (and the 
        #   cursor will end up on a different signal!
        #
        #   Another disadvantage is when we plot several signals (one per frame)
        #   in the same PlotItem, or several segments from a collection and the 
        #   signals have different names (even if they have the same domain and 
        #   units). In this case the cursors could "disappear" from the PlotItem 
        #   after a cycle of changes in the plot items layout as above...
        #
        #
        
        self._cached_cursors_ = dict()
        
        # NOTE: 2023-01-01 22:56:20 see NOTE: 2023-01-01 22:48:10 point (1) above
        if isinstance(nAxes, int) and nAxes >= 0:
            self._n_signal_axes_ = nAxes
        else:
            self._n_signal_axes_ = None
            
        self._signal_axes_ = list()
        
        self._spiketrains_axis_ = None
        self._default_spiketrains_axis_name_ = "Spike trains"
        
        self._events_axis_ = None
        self._default_events_axis_name_ = "Events"
            
        self._target_overlays_ = dict()
        
        self._label_overlays_ = dict()
        
        self._legends_ = dict()
        
        self._frame_analog_map_ = dict()
        self._frame_irregs_map_ = dict()
        
        # NOTE: 2023-05-15 13:49:42 meta-indexing array
        # made this a numpy record array (recarray) with shape (nframes, 1)
        # the records are:
        # • for neo.Block or sequence of neo.Block: 'block' and 'segment'
        # • anything else: 'frame', where a  'frame' depends on data layout and 
        #   on the values of separateSignalChannels, separateChannelsIn
        # 
        # ATTENTION: Currently this is used ONLY when plotted data is a sequence
        # of blocks - although self._parse_data_ sets this array for all supported
        # data types; the intention is to make use of it in the future for
        # indexing in complex structured data  
        
        self._meta_index = None
        
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
        self.epoch_plot_options = dict()
        self._overlay_spikes_events_epochs_ = True
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
        
        
        #### BEGIN GUI signal selectors and options for compound neo objects
        
        # list of analog signal names selected from what is available in the current 
        # frame, using the combobox for analog signals
        # this includes signals in numpy arrays
        self.guiSelectedAnalogSignalEntries = list() # list of signal names
        
        # list of irregularly sampled signal names selected from what is available
        # in the current frame, using the combobox for irregularly sampled signals
        self.guiSelectedIrregularSignalEntries = list()
        
        self._plot_analogsignals_ = True
        self._plot_irregularsignals_ = True
        self._plot_spiketrains_ = True
        self._plot_events_ = True
        self._plot_epochs_ = True
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
        self._hovered_plot_item_ = None
        self._selected_plot_item_ = None
        self._selected_plot_item_index_ = -1
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
        self._xAxesLinked_ = self.defaultXAxesLinked
        self._xGridOn_ = self.defaultXGrid
        self._yGridOn_ = self.defaultYGrid
        self._cursorsDockWidget_enabled_ = True
        self._annotationsDockWidget_enabled_ = True
        
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
        
        if isinstance(y, tuple(self.viewer_for_types.keys())) or any([t in type(y).mro() for t in tuple(self.viewer_for_types.keys())]):
            self.setData(x, y, frameIndex=frameIndex, 
                            frameAxis=frameAxis, signalIndex=signalIndex,
                            signalChannelAxis=signalChannelAxis,
                            signalChannelIndex=signalChannelIndex,
                            irregularSignalIndex=irregularSignalIndex,
                            irregularSignalChannelAxis = irregularSignalChannelAxis,
                            irregularSignalChannelIndex = irregularSignalChannelIndex,
                            separateSignalChannels = separateSignalChannels,
                            singleFrame = singleFrame,
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
        from gui.dictviewer import DataViewer
        
        # NOTE: 2021-11-13 23:24:12
        # signal/slot connections & UI for pg.PlotItem objects are configured in
        # self._prepareAxes_()
        self.sig_frameDisplayReady.connect(self._slot_post_frameDisplay)
        
        self.sig_plot.connect(self._slot_plot_numeric_data_, type = QtCore.Qt.QueuedConnection)
        
        if self.viewerWidgetContainer.layout() is None:
            self.viewerWidgetContainer.setLayout(QtWidgets.QGridLayout(self.viewerWidgetContainer))
            
        self.viewerWidgetContainer.layout().setSpacing(0)
        self.viewerWidgetContainer.layout().setContentsMargins(0,0,0,0)
        
        
        # NOTE: 2023-02-10 09:45:26
        # export to SVG is broken; use the pyqtgraph's own export menu (right-click
        # on the graph)
        self.actionSVG.triggered.connect(self.slot_export_svg)
        self.actionTIFF.triggered.connect(self.slot_export_tiff)
        self.actionPNG.triggered.connect(self.slot_export_png)
        
        # self.menubar.setNativeMenuBar(True)
        
        # NOTE: 2023-04-26 09:30:14
        # menus & actions for cursors & epochs are now defined in the ui file - 
        # here we only connect their signals to appropriate slots
        
        #### BEGIN Cursor actions
        self.addVerticalCursorAction.triggered.connect(self.slot_addVerticalCursor)
        self.addHorizontalCursorAction.triggered.connect(self.slot_addHorizontalCursor)
        self.addCrosshairCursorAction.triggered.connect(self.slot_addCrosshairCursor)
        self.addDynamicVerticalCursorAction.triggered.connect(self.slot_addDynamicVerticalCursor)
        self.addDynamicHorizontalCursorAction.triggered.connect(self.slot_addDynamicHorizontalCursor)
        self.addDynamicCrosshairCursorAction.triggered.connect(self.slot_addDynamicCrosshairCursor)
        self.addMultiAxisVCursorAction.triggered.connect(self.slot_addMultiAxisVerticalCursor)
        self.addMultiAxisCCursorAction.triggered.connect(self.slot_addMultiAxisCrosshairCursor)
        self.addDynamicMultiAxisVCursorAction.triggered.connect(self.slot_addDynamicMultiAxisVerticalCursor)
        self.addDynamicMultiAxisCCursorAction.triggered.connect(self.slot_addDynamicMultiAxisCrosshairCursor)
        self.editAnyCursorAction.triggered.connect(self.slot_editCursor)
        self.editCursorAction.triggered.connect(self.slot_editSelectedCursor)
        self.removeCursorAction.triggered.connect(self.slot_removeCursor)
        self.removeSelectedCursorAction.triggered.connect(self.slot_removeSelectedCursor)
        self.removeAllCursorsAction.triggered.connect(self.slot_removeCursors)
        self.setCursorsShowValue.toggled.connect(self._slot_setCursorsShowValue)
        self.setCursorsLabelPrecisionAction.triggered.connect(self._slot_setCursorLabelPrecision)
        self.verticalCursorColorsAction.triggered.connect(self._slot_setVerticalCursorColors)
        self.horizontalCursorColorsAction.triggered.connect(self._slot_setHorizontalCursorColors)
        self.crosshairCursorColorsAction.triggered.connect(self._slot_setCrosshairCursorColors)
        self.cursorHoverColorAction.triggered.connect(self._slot_setCursorHoverColor)
        self.actionShow_Cursor_Edit_Dialog_When_Created.toggled.connect(self._slot_setEditCursorWhenCreated)
        self.actionVerticalCursorsFromEpochInCurrentAxis.triggered.connect(self._slot_makeVerticalCursorsFromEpoch)
        self.actionMultiAxisVerticalCursorsFromEpoch.triggered.connect(self._slot_makeMultiAxisVerticalCursorsFromEpoch)
        self.actionMultiAxisVerticalCursorsFromEpoch.setEnabled(False)# BUG/FIXME 2023-06-19 12:21:54
        #### END Cursor actions
        
        #### BEGIN Epoch actions
        self.epochsFromCursorsAction.triggered.connect(self.slot_cursorsToEpoch)
        self.epochFromSelectedCursorAction.triggered.connect(self.slot_cursorToEpoch)
        self.epochBetweenCursorsAction.triggered.connect(self.slot_epochBetweenCursors)
        self.epochsInDataFromCursorsAction.triggered.connect(self.slot_cursorsToEpochInData)
        self.epochInDataFromSelectedCursorAction.triggered.connect(self.slot_cursorToEpochInData)
        self.epochInDataBetweenCursors.triggered.connect(self.slot_epochInDataBetweenCursors)
        #### END Epoch actions
        
        self.actionLink_X_axes.toggled.connect(self._slot_setXAxesLinked)
        self.actionLink_X_axes.setEnabled(False)
        
        self.actionShow_X_grid.toggled.connect(self._slot_showXgrid)
        self.actionShow_X_grid.setEnabled(False)
        
        self.actionShow_Y_grid.toggled.connect(self._slot_showYgrid)
        self.actionShow_Y_grid.setEnabled(False)
        
        
        # the actual layout of the plot items (pyqtgraph framework)
        # its "layout" is a QtWidgets.QGraphicsGridLayout
        self.signalsLayout = pg.GraphicsLayout()
        self.signalsLayout.layout.setVerticalSpacing(0)

        styleHint = QtWidgets.QStyle.SH_DitherDisabledText
        
        # NOTE: 2023-04-26 08:41:30
        # goodbye to self.fig - one less symbol to worry about - just assign 
        # directly to self.viewerWidget
        self.viewerWidget = pg.GraphicsLayoutWidget(parent = self.viewerWidgetContainer) 
        self.viewerWidget.style().styleHint(styleHint)
        
        #self.viewerWidgetLayout.addWidget(self.viewerWidget)
        # self.viewerWidget = self.viewerWidget
        self.viewerWidgetContainer.layout().setHorizontalSpacing(0)
        self.viewerWidgetContainer.layout().setVerticalSpacing(0)
        self.viewerWidgetContainer.layout().contentsMargins().setLeft(0)
        self.viewerWidgetContainer.layout().contentsMargins().setRight(0)
        self.viewerWidgetContainer.layout().contentsMargins().setTop(0)
        self.viewerWidgetContainer.layout().contentsMargins().setBottom(0)
        self.viewerWidgetContainer.layout().addWidget(self.viewerWidget, 0,0)
    
        # NOTE: 2023-07-08 23:25:32
        # self.viewerWidget.ci is the central item of the viewer widgets (a 
        # pg.GraphicsLayoutWidget object) and contains the signalsLayout (a 
        # pg.GraphicsLayout object)
        # We set thsi centrsl item as the "main layout" of the signalviewer, to
        # which we add:
        # • a QLabel (plotTitleLabel) on the top (first) row)
        # • the signals layout on the second row
        self.mainLayout = self.viewerWidget.ci
        self.mainLayout.layout.setVerticalSpacing(0)
        self.mainLayout.layout.setHorizontalSpacing(0)
        
        self.plotTitleLabel = self.mainLayout.addLabel("", col=0, colspan=1)
        
        self.mainLayout.nextRow()
        self.mainLayout.addItem(self.signalsLayout)
        
        self._frames_spinBoxSlider_.label = "Sweep:"
        self._frames_spinBoxSlider_.setRange(0, self._number_of_frames_-1)
        self._frames_spinBoxSlider_.valueChanged.connect(self.slot_setFrameNumber) # slot inherited from ScipyenFrameViewer

        # FIXME/TODO? 2022-11-17 09:59:51
        # what's this for?
        # self.signalsMenu = QtWidgets.QMenu("Signals", self)
        
        self.analogSignalComboBox.clear()
        self.analogSignalComboBox.setCurrentIndex(0)
        # self.analogSignalComboBox.currentIndexChanged[int].connect(self.slot_analogSignalsComboBoxIndexChanged)
        self.analogSignalComboBox.activated[int].connect(self.slot_analogSignalsComboBoxIndexChanged)
        
        self.plotAnalogSignalsCheckBox.setCheckState(QtCore.Qt.Checked)
        self.plotAnalogSignalsCheckBox.stateChanged[int].connect(self._slot_plotAnalogSignalsCheckStateChanged_)
        
        self.irregularSignalComboBox.clear()
        self.irregularSignalComboBox.setCurrentIndex(0)
        # self.irregularSignalComboBox.currentIndexChanged[int].connect(self.slot_irregularSignalsComboBoxIndexChanged)
        self.irregularSignalComboBox.activated[int].connect(self.slot_irregularSignalsComboBoxIndexChanged)
        
        self.plotIrregularSignalsCheckBox.setCheckState(QtCore.Qt.Checked)
        self.plotIrregularSignalsCheckBox.stateChanged[int].connect(self._slot_plotIrregularSignalsCheckStateChanged_)
        
        self.plotSpikeTrainsCheckBox.setCheckState(QtCore.Qt.Checked)
        self.plotSpikeTrainsCheckBox.stateChanged[int].connect(self._slot_plotSpikeTrainsCheckStateChanged_)
        
        self.plotEventsCheckBox.setCheckState(QtCore.Qt.Checked)
        self.plotEventsCheckBox.stateChanged[int].connect(self._slot_plotEventsCheckStateChanged_)
        
        self.plotEpochsCheckBox.setCheckState(QtCore.Qt.Checked)
        self.plotEpochsCheckBox.stateChanged[int].connect(self._slot_plotEpochsCheckStateChanged_)
        
        #### BEGIN set up annotations dock widget
        #
        # NOTE: 2023-01-09 18:02:42
        # self.annotationsViewer and self.annotationsDockWidget are now defined 
        # in the ui file ("signalviewer.ui")
        #
        # NOTE: 2022-03-04 10:14:09 FIXME/TODO code to actually export to workspace
        #
        # self.annotationsViewer = InteractiveTreeWidget(self.annotationsDockWidget)
        self.annotationsViewer.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.annotationsViewer.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        self.annotationsViewer.setDragEnabled(True)
        self.annotationsViewer.setSupportedDataTypes(tuple(DataViewer.viewer_for_types))
        #### END set up annotations dock widget
        
        #### BEGIN set up coordinates dock widget - defined in the UI file
        # self.cursorsDockWidget s now defined in the ui file
        #### END set up coordinates dock widget
        
        #print("_configureUI_ sets up dock widget actions menu")
        self.docksMenu = QtWidgets.QMenu("Panels", self)
        
        self.showAnnotationsDockWidgetAction = self.docksMenu.addAction("Annotations")
        self.showAnnotationsDockWidgetAction.setCheckable(True)
        self.showAnnotationsDockWidgetAction.setObjectName("action_%s" % self.annotationsDockWidget.objectName())
        self.showAnnotationsDockWidgetAction.toggled.connect(self.slot_showAnnotationsDock)
        # self.showAnnotationsDockWidgetAction.triggered.connect(self.slot_showAnnotationsDock)
        
        self.showCursorsDockWidgetAction = self.docksMenu.addAction("Cursors")
        self.showCursorsDockWidgetAction.setCheckable(True)
        self.showCursorsDockWidgetAction.setObjectName("action_%s" % self.cursorsDockWidget.objectName())
        self.showCursorsDockWidgetAction.toggled.connect(self.slot_showCursorsDock)
        # self.showCursorsDockWidgetAction.triggered.connect(self.slot_showCursorsDock)
        
        # self.menubar.addMenu(self.docksMenu)
        self.menuSettings.addMenu(self.docksMenu)
        
        self.actionDetect_Triggers.triggered.connect(self.slot_detectTriggers)
        self.actionDetect_Triggers.setEnabled(False)
        
        self.actionRefresh.triggered.connect(self.slot_refreshDataDisplay)
        
        self.actionData_to_workspace.setIcon(QtGui.QIcon.fromTheme("document-export"))
        self.actionData_to_workspace.triggered.connect(self.slot_exportDataToWorkspace)
        
        self.actionShow_Legends.triggered.connect(self._slot_showLegends)
        
        self.actionIgnore_empty_spike_trains.triggered.connect(self._slot_setIgnoreEmptySpikeTrains)
        # self.actionShow_Legends.setEnabled(False)
        
    # ### BEGIN properties
    @property
    def dockWidgets(self):
        return dict(((name, w) for name, w in self.__dict__.items() if isinstance(w, QtWidgets.QDockWidget)))

    @property
    def signalAxes(self):
        """Read-only list of PlotItem objects dedicated to plotting signals
        """
        return self._signal_axes_
    
    def signalAxis(self, index:int):
        if not isinstance(index, int):
            raise TypeError(f"Expecting an int; instead, got a {type(index).__name__}")
        
        if index not in range(-len(self.signalAxes), len(self.signalAxes)):
            raise ValueError(f"Invalid index {index} for {len(self.signalAxes)} signal axes")
        
        return self.signalAxes[index]
    
    @property
    def eventsAxis(self):
        return self._events_axis_
    
    @property
    def spikeTrainsAxis(self):
        return self._spiketrains_axis_
    
    @property
    def commonAxesXPadding(self):
        return self._common_axes_X_padding_
    
    @markConfigurable("CommonXPadding", trait_notifier=True)
    @commonAxesXPadding.setter
    def commonAxesXPadding(self, value:float):
        self._common_axes_X_padding_ = value
        # self._align_X_range()
        
    @property
    def editCursorUponCreation(self):
        return self._editCursorOnCreation_
    
    @markConfigurable("EditCursorWhenCreated", "qt")
    @editCursorUponCreation.setter
    def editCursorUponCreation(self, value:bool):
        self._editCursorOnCreation_ = value == True
        sigBlocker = QtCore.QSignalBlocker(self.actionShow_Cursor_Edit_Dialog_When_Created)
        self.actionShow_Cursor_Edit_Dialog_When_Created.setChecked(self._editCursorOnCreation_)
    
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
    def showsLegends(self):
        return self._show_legends_
    
    @markConfigurable("ShowsLegends", trait_notifier=True)
    @showsLegends.setter
    def showsLegends(self, value:bool):
        self._show_legends_ = True
        sigBlock = QtCore.QSignalBlocker(self.actionShow_Legends)
        self.actionShow_Legends.setChecked(value==True)
        self.showLegends(self._show_legends_)
            
    @pyqtSlot(bool)
    def _slot_showLegends(self, value):
        self.showsLegends = value == True
        
    @pyqtSlot(bool)
    def _slot_setIgnoreEmptySpikeTrains(self, value):
        self.ignoreEmptySpikeTrains = value==True
        if self.yData is not None:
            self.displayFrame()
        
    @property
    def ignoreEmptySpikeTrains(self):
        return self._ignore_empty_spiketrains_
    
    @markConfigurable("IgnoreEmptySpikeTrains", trait_notifier=True)
    @ignoreEmptySpikeTrains.setter
    def ignoreEmptySpikeTrains(self, value):
        self._ignore_empty_spiketrains_ = value == True
        sigBlock = QtCore.QSignalBlocker(self.actionIgnore_empty_spike_trains)
        self.actionIgnore_empty_spike_trains.setChecked(self._ignore_empty_spiketrains_)
        
    @property
    def cursorLabelPrecision(self):
        return self._cursorLabelPrecision_
    
    @markConfigurable("CursorLabelPrecision")
    @cursorLabelPrecision.setter
    def cursorLabelPrecision(self, val:typing.Union[int, str]):
        if isinstance(val, str) and val=="auto":
            pi_precisions = [self.getAxis_xDataPrecision(ax) for ax in self.plotItems]
            val = min(pi_precisions)
        
        if not isinstance(val, int) or val < 0:
            val = self.defaultCursorLabelPrecision
            
        self._cursorLabelPrecision_ = int(val)
        
        for c in self.cursors:
            c.precision = self._cursorLabelPrecision_
            
        if isinstance(getattr(self, "configurable_traits", None), DataBag):
            self.configurable_traits["CursorLabelPrecision"] = self._cursorLabelPrecision_
            
    @property
    def xGrid(self) -> bool:
        return self._xGridOn_
    
    @markConfigurable("XGrid")
    @xGrid.setter
    def xGrid(self, value:bool):
        self._xGridOn_ = value == True
        signalBlocker = QtCore.QSignalBlocker(self.actionShow_X_grid)
        self.actionShow_X_grid.setChecked(self._xGridOn_)
            
        if isinstance(getattr(self, "configurable_traits", None), DataBag):
            self.configurable_traits["XGrid"] = self._xGridOn_
        
        self._showXGrid(self._xGridOn_)
        
    @property
    def yGrid(self) -> bool:
        return self._yGridOn_
    
    @markConfigurable("YGrid")
    @xGrid.setter
    def yGrid(self, value:bool):
        self._yGridOn_ = value == True
        signalBlocker = QtCore.QSignalBlocker(self.actionShow_Y_grid)
        self.actionShow_Y_grid.setChecked(self._yGridOn_)
            
        if isinstance(getattr(self, "configurable_traits", None), DataBag):
            self.configurable_traits["YGrid"] = self._yGridOn_
            
        self._showYGrid(self._yGridOn_)
        
    @property
    def annotationsDockWidgetEnabled(self) -> bool:
        return self._annotationsDockWidget_enabled_
    
    @markConfigurable("AnnotationsDock")
    @annotationsDockWidgetEnabled.setter
    def annotationsDockWidgetEnabled(self, val:bool):
        self._annotationsDockWidget_enabled_ = val==True
        
        sigBlocker = [QtCore.QSignalBlocker(w) for w in (self.showAnnotationsDockWidgetAction,
                                                            self.annotationsDockWidget)]
        
        if self._annotationsDockWidget_enabled_:
            self.annotationsDockWidget.show()
        else:
            self.annotationsDockWidget.hide()
            
        self.showAnnotationsDockWidgetAction.setChecked(self._annotationsDockWidget_enabled_)
        
    @property
    def cursorsDockWidgetEnabled(self) -> bool:
        return self._cursorsDockWidget_enabled_
    
    @markConfigurable("CursorsDock")
    @cursorsDockWidgetEnabled.setter
    def cursorsDockWidgetEnabled(self, val:bool):
        self._cursorsDockWidget_enabled_ = val==True
        
        sigBlocker = [QtCore.QSignalBlocker(w) for w in (self.showCursorsDockWidgetAction,
                                                            self.cursorsDockWidget)]
        
        if self._cursorsDockWidget_enabled_:
            self.cursorsDockWidget.show()
        else:
            self.cursorsDockWidget.hide()
            
        self.showCursorsDockWidgetAction.setChecked(self._cursorsDockWidget_enabled_)
        
    @property
    def xAxesLinked(self): 
        """This is True when all PlotItems but one have X axes linked"""
        return self._xAxesLinked_
    
    @markConfigurable("XAxesLinked")
    @xAxesLinked.setter
    def xAxesLinked(self, value):
        # print(f"{self.__class__.__name__}.xAxesLinked.setter value = {value}")
        setAllXLink = value == True
        signalBlocker = QtCore.QSignalBlocker(self.actionLink_X_axes)
        self.actionLink_X_axes.setChecked(setAllXLink)
        
        self._xAxesLinked_ = setAllXLink
        
        if isinstance(getattr(self, "configurable_traits", None), DataBag):
            self.configurable_traits["XAxesLinked"] = self._xAxesLinked_
            
        if len(self.axes):
            if self._xAxesLinked_:
                self.linkAllXAxes()
            else:
                self.unlinkAllXAxes()
            
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
    def _interpret_signal(self, obj, /, x=None, **kwargs):
        raise NotImplementedError(f"Plotting is not implemented for objects of type {type(x).__name__}")
#         ret = dict( x = None,
#                     y = None,
#                     dataAxis = 0,
#                     signalChannelAxis = kwargs.get("signalChannelAxis", 1),
#                     frameAxis = kwargs.get("frameAxis", None),
#                     frameIndex = kwargs.get("frameIndex", None),
#                     _data_frames_ = 0,
#                     _number_of_frames_ = 0,
#                     signalChannelIndex = kwargs.get("signalChannelIndex", None),
#                     irregularSignalChannelAxis = kwargs.get("irregularSignalChannelAxis", None),
#                     irregularSignalChannelIndex = kwargs.get("irregularSignalChannelIndex", None),
#                     separateSignalChannels = kwargs.get("separateSignalChannels", False),
#                     signalIndex = kwargs.get("signalIndex", None),
#                     irregularSignalIndex = kwargs.get("irregularSignalIndex", None),
#                     globalAnnotations = kwargs.get("globalAnnotations", None),
#                     )
#         
#         return ret
        
    
    @_interpret_signal.register(neo.Block)
    def _(self, obj:neo.Block, /, x, **kwargs):
        self._yData_ = obj
        self._cached_title = getattr(y, "name", None)
        
        # NOTE : 2022-01-17 14:17:23
        # if frameIndex was passed, then self._number_of_frames_ might turn
        # out to be different than self._data_frames_!
        self._data_frames_ = self._number_of_frames_ = len(self._yData_.segments)
        
        #### BEGIN NOTE 2019-11-24 22:32:46: 
        # no need for these so reset to None
        # but definitely used when self._yData_ is a signal, not a container of signals!
        self.dataAxis = 0 # data as column vectors
        self.signalChannelAxis = 1 
        self.irregularSignalChannelAxis = 1
        
        # not needed: every segment is a "frame"
        self.frameAxis = None
        
        # not needed: all signal channels plotted in the same signal axis
        self.signalChannelIndex = None
        self.irregularSignalChannelIndex = None
        
        # NOTE: set to None on purpose for Block
        self.separateSignalChannels = False
        #### END NOTE 2019-11-24 22:32:46: 

        #### BEGIN NOTE: 2019-11-22 08:37:38 
        # the following need checking inside _plotSegment_()
        # to adapting for the particular segment
        # NOTE: 2023-01-01 15:59:00 on their way out, see NOTE: 2023-01-01 15:29:48
        self.signalIndex  = signalIndex
        self.irregularSignalIndex  = irregularSignalIndex
        #### END NOTE: 2019-11-22 08:37:38 
        
        # NOTE: this is used when self._yData_ is a structured signal object,
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
        
        self._n_signal_axes_ = max(len(s.analogsignals) + len(s.irregularlysampledsignals) for s in self._yData_.segments)
        
                
    @_interpret_signal.register(neo.Segment)
    def _(self, obj:neo.Segment, /, x=None, **kwargs):
        # self._xData_ = None # NOTE: x can still be supplied externally
        self._yData_ = obj
        self._cached_title = getattr(y, "name", None)
        # self._plotEpochs_(clear=True)
        
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
        
        self._n_signal_axes_ = len(y.analogsignals) + len(y.irregularlysampledsignals)
        
        
    @_interpret_signal.register(neo.AnalogSignal)
    @_interpret_signal.register(DataSignal)
    def _(self,obj, /, x = None, **kwargs):
        self._yData_ = obj
        self._cached_title = getattr(y, "name", None)
        
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
        self.signalChannelIndex = normalized_sample_index(self._yData_.as_array(), self.signalChannelAxis, signalChannelIndex)
        
        self._data_frames_ = 1
        
        if frameAxis is None:
            self.frameAxis = None
            self._number_of_frames_ = 1
            self.frameIndex = range(self._number_of_frames_)

            self.separateSignalChannels = separateSignalChannels
            
        else:
            frameAxis = normalized_axis_index(self._yData_.as_array(), frameAxis)
            if frameAxis != self.signalChannelAxis:
                raise ValueError("For structured signals, frame axis and signal channel axis must be identical")
            
            self.frameAxis = frameAxis
            self.frameIndex = normalized_sample_index(self._yData_.as_array(), self.frameAxis, frameIndex)
            self._number_of_frames_ = len(self.frameIndex)
            self.separateSignalChannels = False
            
        self._n_signal_axes_ = self._yData_.shape[self.signalChannelAxis] if self.separateSignalChannels else 1
        
    @_interpret_signal.register(neo.IrregularlySampledSignal)
    @_interpret_signal.register(IrregularlySampledDataSignal)
    def _(self, obj, /, x=None, **kwargs):
        self._yData_ = obj
        self._cached_title = getattr(y, "name", None)
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
        
        if frameAxis is None:
            self.frameAxis = None
            self._number_of_frames_ = 1
            self.frameIndex = range(self._number_of_frames_)
            self.separateSignalChannels         = separateSignalChannels
            
        else:
            frameAxis = normalized_axis_index(self._yData_.as_array(), frameAxis)
            if frameAxis != self.signalChannelAxis:
                raise ValueError("For structured signals, frame axis and signal channel axis must be identical")
            
            self.frameAxis = frameAxis
            self.frameIndex = normalized_sample_index(self._yData_.as_array(), self.frameAxis, frameIndex)
            self._number_of_frames_ = len(self.frameIndex)
            self.separateSignalChannels  = False
            
        self._n_signal_axes_ = self._yData_.shape[self.signalChannelAxis] if self.separateSignalChannels else 1
        
    @_interpret_signal.register(neo.Epoch)
    @_interpret_signal.register(DataZone)
    def _(self, obj, /, x=None, **kwargs):
        self._yData_ = obj
        self._cached_title = getattr(y, "name", None)
        self.dataAxis = 0 # data as column vectors
        self.signalChannelAxis = 1
        self.frameIndex = range(1)
        self._number_of_frames_ = 1
        self._n_signal_axes_ = 0
        
        if self._docTitle_ is None or (isinstance(self._docTitle_, str) and len(self._docTitle_.strip()) == 0):
            #because these may be plotted as an add-on so we don't want to mess up the title
            if isinstance(y.name, str) and len(y.name.strip()) > 0:
                self._doctTitle_ = y.name
                
            else:
                self._docTitle_ = self._yData_.name
    
    @_interpret_signal.register(neo.Event)
    @_interpret_signal.register(DataMark)
    @_interpret_signal.register(TriggerEvent)
    def _(self, obj, /, x=None, **kwargs):
        self._yData_ = obj
        self._cached_title = getattr(y, "name", None)
        self.dataAxis = 0 # data as column vectors
        self.signalChannelAxis = 1
        self.frameIndex = range(1)
        self._number_of_frames_ = 1
        self._n_signal_axes_ = 0
    
    @_interpret_signal.register(TriggerProtocol)
    def _(self, obj, /, x=None, **kwargs):
        # TODO
        pass
    
    @_interpret_signal.register(neo.SpikeTrain)
    def _(self, obj, /, x=None, **kwargs):
        # TODO
        pass
    
    @_interpret_signal.register(neo.core.spiketrainlist.SpikeTrainList)
    def _(self, obj, /, x=None, **kwargs):
        self._n_signal_axes_ = 0
        # self._xData_ = None
        self._yData_ = obj
        self._cached_title = getattr(y, "name", None)
        self.dataAxis = 0 # data as column vectors
        self.signalChannelAxis = 1
        self.frameIndex = range(1)
        self._number_of_frames_ = 1
    
    
    @_interpret_signal.register(vigra.filters.Kernel1D)
    def _(self, obj:vigra.filters.Kernel1D, /, x=None, **kwargs):
        self._xData_, self._yData_ = kernel2array(obj)
        self._cached_title = "Vigra Kernel 1D"
        # self._plotEpochs_(clear=True)
        
        self.dataAxis = 0 # data as column vectors
        self.frameIndex = range(1)
        self.signalIndex = range(1)
        self._number_of_frames_ = 1
        
        self._n_signal_axes_ = 1

    @_interpret_signal.register(np.ndarray)
    def _(self, obj:np.ndarray, /, x=None, **kwargs):
        if x.ndim > 3:
            raise ValueError('Cannot plot data with more than 3 dimensions')

        ret = dict()
        ret["globalAnnotations"] = kwargs.get("globalAnnotations", None)
        
        frameAxis = kwargs.get("frameAxis", None)
        frameIndex = kwargs.get("frameIndex", None)
        signalChannelAxis = kwargs.get("signalChannelAxis", None)
        separateSignalChannels = kwargs.get("separateSignalChannels", False)
        
        if obj.ndim == 1: # one frame, one channel
            dataAxis = 0 # data as column vectors
            signalChannelAxis = None
            frameAxis = None
            frameIndex = range(1)
            signalChannelIndex = range(1)
            _number_of_frames_ = 1
            dataAxis = 0
            
        elif obj.ndim == 2:
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
        # print(f"_make_targetItem data = {data}")
        if isinstance(data, (tuple, list)):
            if len(data) == 3:
                kwargs["size"] = data[2]
                data = data[0:2]
                
            elif len(data) != 2:
                raise ValueError(f"data is expected to have two or three elements; got {len(data)} instead")

        return pg.TargetItem(data, **kwargs)
    
    def _clear_lris_(self):
        for k, ax in enumerate(self.axes):
            lris = [i for i in ax.items if isinstance(i, pg.LinearRegionItem)]
            
            if len(lris):
                for l in lris:
                    ax.removeItem(l)
                    
    
    @safeWrapper
    def _plot_discrete_entities_(self, /, entities:typing.Union[dict, list, neo.core.spiketrainlist.SpikeTrainList], 
                                 axis:pg.PlotItem, clear:bool=True, 
                                 adapt_X_range:bool=True, 
                                 minX:typing.Optional[float]=None, 
                                 maxX:typing.Optional[float]=None, 
                                 **kwargs):
        """For plotting events and spike trains on their own (separate) axis
        Epochs & DataZones are represented as regions between vertical lines 
        across all axes, and therefore they are not dealt with, here.
        adapt_X_range determines the x range (you may want to pass a custom one if needed)
        """
        #### BEGIN debug
        # stack = inspect.stack()
        # print(f"_plot_discrete_entities_")
        # for s in stack:
        #     print(f"\t\tcaller {s.function} from {s.filename} at {s.lineno}")
        #### END debug
        
        if len(entities) == 0:
            return
        
        try:
            # this is the PlotItem, not the array axis
            entities_axis = axis
                
            eventsSymbol = kwargs.pop("eventsSymbol", "event")
            eventsBrush = kwargs.pop("eventsBrush", QtGui.QBrush(QtGui.QColor("black")))
            eventsPen = kwargs.pop("eventsPen", QtGui.QPen(QtGui.QColor("black"),1))
            eventsPen.setCosmetic(True)
            
            eventsSymbolColors = cycle(self.defaultLineColorsList)
            
            spikeTrainSymbol = kwargs.pop("spikeTrainSymbol", "spike")
            symbolPen = QtGui.QPen(QtGui.QColor("black"),1)
            symbolPen.setCosmetic(True)
            
            symbolStyle = {"color": "black", 
                           "pen": eventsPen,
                           "brush": eventsBrush}
            
            labelStyle = {"color": "#000000"}
            
            height_interval = 1/len(entities)
            
            if isinstance(entities, dict):
                entities_list  = list(entities.values())
                
            else:
                entities_list = entities
            
            if all(isinstance(v, neo.Event) for v in entities_list):
                xdimstr = scq.shortSymbol(entities_list[0].times.units.dimensionality)
                if len(xdimstr):
                    xLabel = f"{get_domain_name(entities_list[0])} ({xdimstr})"
                else:
                    xLabel = f"{get_domain_name(entities_list[0])}"
                    
                yLabel = "Events"
                
                symbolStyle["symbol"] = eventsSymbol
                
                if len(entities_list) > 1:
                    symbolStyle["pen"] = cycle(self.defaultLineColorsList)
                    symbolStyle["color"] = cycle(self.defaultLineColorsList)
                    symbolStyle["brush"] = cycle(self.defaultLineColorsList)
                else:
                    symbolStyle["pen"] = symbolPen
                    symbolStyle["color"] = QtGui.QColor("black")
                    symbolStyle["brush"] = eventsBrush
                    
                
                self._plot_events_or_marks_(entities_list, entities_axis, 
                                            xLabel, yLabel, 
                                            minX, maxX, adapt_X_range, 
                                            height_interval, 
                                            symbolStyle,
                                            **labelStyle)
                
            elif all(isinstance(v, DataMark) for v in entities_list):
                xdimstr = scq.shortSymbol(entities_list[0].times.units.dimensionality)
                if len(xdimstr):
                    xLabel = f"{get_domain_name(entities_list[0])} ({xdimstr})"
                else:
                    xLabel = f"{get_domain_name(entities_list[0])}"
                    
                yLabel = "Triggers" if all(isinstance(v, TriggerEvent) for v in entities_list) else "Data marks"
                
                symbolStyle["symbol"] = eventsSymbol
                
                if len(entities_list) > 1:
                    symbolStyle["pen"] = cycle(self.defaultLineColorsList)
                    symbolStyle["color"] = cycle(self.defaultLineColorsList)
                
                self._plot_events_or_marks_(entities_list, entities_axis, 
                                            xLabel, yLabel, 
                                            minX, maxX, adapt_X_range, 
                                            height_interval, 
                                            symbolStyle,
                                            **labelStyle)
                
                
            
            elif all(isinstance(v, neo.SpikeTrain) for v in entities_list):
                entities_axis.clear()
                #### BEGIN debug
                # print(f"1704 plot spike train")
                # print(f"{self.__class__.__name__}._plot_discrete_entities_ stack trace:")
                # stack = inspect.stack()
                # for s in stack:
                #     print(f"\tcaller\t {s.function}")
                # traceback.print_stack(limit=8)
                #### ENBD debug
                
                for k_train, train in enumerate(entities_list):
                    data_name = getattr(train, "name", None)
                    data_name = data_name if isinstance(data_name, str) and len(data_name.strip()) else "%d" % k_train
                    
                    x = train.times.magnitude.flatten() # vector
                    y = np.full(x.shape, height_interval * k_train + height_interval/2) # column vector
                        
                    self._plot_numeric_data_(entities_axis, x, y, 
                                                symbol=spikeTrainSymbol,
                                                pen=None, name=data_name,
                                                symbolPen=QtGui.QPen(QtGui.QColor(next(eventsSymbolColors))),
                                                reusePlotItems=False)
                        
                xdimstr = scq.shortSymbol(entities_list[0].times.units.dimensionality)
                if len(xdimstr):
                    xLabel = f"{get_domain_name(entities_list[0])} ({xdimstr})"
                else:
                    xLabel = f"{get_domain_name(entities_list[0])}"
                    
                # xlabel = f"{get_domain_name(entities_list[0])} ({entities_list[0].times.units.dimensionality})"
                yLabel = "Spike Trains"
                entities_axis.setLabels(bottom = [xLabel])
                
                # NOTE: 2022-11-21 14:15:17
                # this will PREVENT the dispay of Y grid lines (not essential, because
                # the data plotted here has NO mangnitude information, unlike signals)
                # NOTE: 2023-01-17 09:42:11
                # move here because:
                # • the entities_axis may be a signal axis e.g. when target overlays 
                #   are destined to a signal axis (and we don't want to apply this
                #   to a signal axis)
                # • the same code is applied by _plot_events_or_marks_ to the 
                #   eventsAxis
                # entities_axis.axes[]
                entities_axis.axes["left"]["item"].setPen(None)
                entities_axis.axes["left"]["item"].setLabel(yLabel, **labelStyle)
                entities_axis.axes["left"]["item"].setStyle(showValues=False)
                
            elif all(isinstance(v, pg.TargetItem) for v in entities_list):
                # print(f"_plot_discrete_entities_ {len(entities_list)} entities")
                if clear:
                    self._clear_targets_overlay_(entities_axis)
                for entity in entities_list:
                    if entity not in entities_axis.items:
                        entities_axis.addItem(entity)
                return # job done here; return so we don't exec code further down'
            else:
                return
                
            
        except:
            traceback.print_exc()
            
    def _clear_targets_overlay_(self, axis):
        """Removes the targets overlay from this axis
            Cached targets are left in place
        """
        #### BEGIN debug
        # print(f"{self.windowTitle()} stack trace:")
        # stack = inspect.stack()
        # for s in stack:
        #     print(f"\tcaller\t {s.function}")
        # traceback.print_stack(limit=8)
        #### END debug
        axis, axNdx = self._check_axis_spec_ndx_(axis)
        items = [i for i in axis.items if isinstance(i, pg.TargetItem)]
        # print(f"{self.windowTitle()} _clear_targets_overlay_ {len(items)} targets")
        for i in items:
            axis.removeItem(i)
            
    def _clear_labels_overlay_(self, axis):
        axis, axNdx = self._check_axis_spec_ndx_(axis)
        items = [i for i in axis.items if isinstance(i, pg.TextItem)]
        for i in items:
            axis.removeItem(i)
        
    def _remove_legend(self, axis):
        axis, axNdx = self._check_axis_spec_ndx_(axis)
        items = [i for i in axis.items if isinstance(i, pg.LegendItem)]
        for i in items:
            axis.removeItem(i)
            
    def _check_axis_spec_ndx_(self, axis:typing.Optional[typing.Union[int, pg.PlotItem]]=None):
        if axis is None:
            axis = self.currentAxis
            axNdx = self.axes.index(axis)
            
        elif isinstance(axis, int):
            if axis not in range(-len(self.axes), len(self.axes)):
                raise ValueError(f"axis index {axis} is out of range for {len(self.axes)} axes")
            
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
            
        if self.annotationsViewer.isVisible():
            self.annotationsViewer.setData(self.dataAnnotations)
            
            if self.annotationsViewer.topLevelItemCount() == 1:
                self.annotationsViewer.topLevelItem(0).setText(0, "Data")
            
    def _gen_signal_ndx_name_map_(self, signals:typing.Union[tuple, list]):
        """Generates a mapping of entry_name ↦ (index , signal_name)
        """
        sig_ndx_names = list(map(lambda x: (x[0],x[1]) if isinstance(x[1], str) and len(x[1].strip()) else (x[0],f"Analog signal {x[0]}") , ((k,getattr(s, "name", f"Analog signal {k}")) for k,s in enumerate(signals))))
        
        # NOTE: 2023-01-17 11:57:46
        # map signal name suffixed with optional index in brackets, to
        # a tuple (index, signal name)
        # so that we can display mroe than one signal with the same name in
        # the chooser
        mapping = dict()
        
        taken = set()
        
        sep=":"
        
        for k, x in enumerate(sig_ndx_names):
            if x[1] in taken:
                entry_name = counter_suffix(x[1], taken, sep = sep)
            else:
                entry_name = x[1]
            
            taken.add(entry_name)
            
            base, ctr = get_int_sfx(entry_name, sep = sep)
            
            if isinstance(ctr, int) and ctr > 0:
                entry_name = " ".join([base, f"({ctr})"])
                
            # print(f"{self.__class__.__name__}._gen_signal_ndx_name_map_() signal {k}: sig_ndx_name = {x}; base = {base}; ctr = {ctr}; entry_name = {entry_name}")
                
            mapping[entry_name] = x
            
        return mapping
                
    def _populate_signal_chooser_(self, mapping, combo):
        """ Helper for the self._setup_signal_choosers_ method
        """
        sigBlock = QtCore.QSignalBlocker(combo)
        if len(mapping):
            entries = ["All"] + list(mapping.keys()) + ["Choose"]
            current_ndx = combo.currentIndex()
            if current_ndx < 0: # for empty combo this is -1
                current_ndx = 0
                
            current_txt = combo.currentText() # for empty combo this is ""
            
            if combo == self.analogSignalComboBox:
                signal_selection = self.guiSelectedAnalogSignalEntries
            else:
                signal_selection = self.guiSelectedIrregularSignalEntries
                
            selected_signals_for_frame = list()
                
            if len(signal_selection):
                selected_signals_for_frame = [i for i in signal_selection if i in mapping]
            else:
                selected_signals_for_frame = list()
                
            cname = "Analog" if combo == self.analogSignalComboBox else "Irregular"
            # print(f"{self.__class__.__name__}._populate_signal_chooser_ {cname} selected_signals_for_frame = {selected_signals_for_frame}")
                
            if len(selected_signals_for_frame)>1:
                new_ndx = len(entries)-1
                new_txt = entries[-1]
                combo.setCurrentIndex(new_ndx)

            else:
                if current_txt in entries:
                    new_ndx = entries.index(current_txt)
                    
                elif current_ndx < len(entries):
                    new_ndx = current_ndx
                    new_txt = entries[new_ndx]
                    
                else:
                    new_ndx = 0
            
                if new_ndx < 0:
                    new_ndx = 0
                    
                if new_ndx >= len(entries) - 1:
                    new_ndx = 0
                    
                combo.clear()
                combo.addItems(entries)
                combo.setCurrentIndex(new_ndx)
        else:
            combo.clear()
        
    def _setup_signal_choosers_(self, analog:typing.Optional[list] = None, 
                                irregular:typing.Optional[list] = None):
        """ Populates the GUI signal combo boxes based on the signals
        """
        # print(f"{len(analog) if isinstance(analog, (tuple, list)) else analog} analogs")
        if not isinstance(analog, (tuple, list)) or len(analog) == 0:
            self._frame_analog_map_.clear()
            
        else:
            self._frame_analog_map_ = self._gen_signal_ndx_name_map_(analog)
            
        self._populate_signal_chooser_(self._frame_analog_map_, self.analogSignalComboBox)
            
        # print(f"{len(irregular) if isinstance(irregular, (tuple, list)) else irregular} irregulars")
        if irregular is None or (isinstance(irregular, (tuple, list)) and len(irregular) == 0):
            self._frame_irregs_map_.clear()
            
        else:
            self._frame_irregs_map_ = self._gen_signal_ndx_name_map_(irregular)
            
        self._populate_signal_chooser_(self._frame_irregs_map_, self.irregularSignalComboBox)

    # ### END private methods
    
    def setDataDisplayEnabled(self, value):
        self.viewerWidget.setEnabled(value is True)
        self.viewerWidget.setVisible(value is True)
        
    def showEvent(self, evt):
        super().showEvent(evt)
        evt.accept()
            
    def overlayTargets(self, *args, axis:typing.Optional[typing.Union[int, pg.PlotItem]]=None, clear:bool=False, **kwargs):
        """Overlays "target" glyphs on the given axis, for the current frame.
        Targets are also added to an internal cache.
        
        Var-positional parameters (*args):
        ==================================
        A sequence of (x,y) coordinate pairs (numeric scalars) or (x,y, size)
        triplets (where x, y are float scalars in the axis' coordinate system
        and size is an int, default is 10).
        
        
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
        
        # print(f"overlayTargets {args}")
        
        # print(f"overlayTargets {len(args)} args")
        
        axis, axNdx = self._check_axis_spec_ndx_(axis)
        
        targetItems = list()
        
        for kc, coords in enumerate(args):
            # print(f"overlayTargets target {kc} is a {type(coords)}")
            if isinstance(coords, pg.TargetItem):
                targetItems.append(coords)
                
            elif isinstance(coords, (tuple, list, QtCore.QPointF, QtCore.QPoint, pg.Point)):
                targetItems.append(self._make_targetItem(coords, **kwargs))
        
        # targetItems = [self._make_targetItem(coords, **kwargs) for coords in args]
        
        cFrame = self.frameIndex[self.currentFrame]
        
        # NOTE: 2022-12-18 13:30:40
        # target overlays is a dict mapping frame index to a dict that maps
        # index of axis in the frame to a sequence of TargetItem objects
        
        if cFrame not in self._target_overlays_:
            self._target_overlays_[cFrame] = dict()
            
        if axNdx in self._target_overlays_[cFrame] and isinstance(self._target_overlays_[cFrame][axNdx], list):
            self._target_overlays_[cFrame][axNdx].extend(targetItems)
        else:
            self._target_overlays_[cFrame][axNdx] = targetItems
        
        # print(f"_target_overlays_ for axis {axNdx} in frame {cFrame}: {len(self._target_overlays_[cFrame][axNdx])}")
        self._plot_discrete_entities_(self._target_overlays_[cFrame][axNdx], axis, clear=clear)
        
    def removeTargetsOverlay(self, axis:typing.Optional[typing.Union[int, pg.PlotItem]]=None):
        """Remove targets overlaid in this axis.
        Target objects are also removed from the internal cache
        """
        
        cFrame = self.frameIndex[self.currentFrame]
        
        if axis is None:
            for axNdx, axis in enumerate(self.axes):
                if cFrame in self._target_overlays_:
                    if isinstance(self._target_overlays_[cFrame], dict):
                        if isinstance(self._target_overlays_[cFrame].get(axNdx, None), (tuple, list)):
                            self._target_overlays_[cFrame][axNdx].clear()
                        else:
                            self._target_overlays_[cFrame][axNdx] = list()
                
                self._clear_targets_overlay_(axis)
                
            
        else:
            axis, axNdx = self._check_axis_spec_ndx_(axis)
            
            if cFrame in self._target_overlays_:
                if isinstance(self._target_overlays_[cFrame], dict):
                    if isinstance(self._target_overlays_[cFrame].get(axNdx, None), (tuple, list)):
                        self._target_overlays_[cFrame][axNdx].clear()
                    else:
                        # self._target_overlays_[cFrame].pop(axNdx, None)
                        self._target_overlays_[cFrame][axNdx] = list()
                        
                    # if len(self._target_overlays_[cFrame]) == 0:
                    #     self._target_overlays_.pop(cFrame)
                        
            # cal this just in case we have overlays that escaped the cache mechanism
            self._clear_targets_overlay_(axis)
                
    def addLabel(self, text:str, axis:typing.Optional[typing.Union[int, pg.PlotItem]]=None, 
                 pos = None, **kwargs):
        """Add a pg.TextItem to the specified axis (pg.PlotItem)
        Parameters:
        ===========
        text: the label contents
        axis: axis index, PlotItem, or None (meaning the label will be added to
                the current axis)
        pos: the position of the label in axis coordinates
            When None, a null point (0,0) will be created 
        
        Var-keyword parameters:
        =======================
        Passed directly to pyqtgraph TextItem constructor, see below for details:
        https://pyqtgraph.readthedocs.io/en/latest/api_reference/graphicsItems/textitem.html
        
        color: typically, a tuple of int/float each in the range 0 ⋯ 256 ; default is (0,0,0)
        anchor: a tuple, default is (0,1)
        
        """
        #### BEGIN debug
        # print(f"{self.__class__.__name__}.addLabel(text={text})")
        # stack = inspect.stack()
        # show_caller_stack(stack)
        #### END debug
        axis, axNdx = self._check_axis_spec_ndx_(axis)
        
        if pos is None:
            pos = pg.Point(0,0)
            
        elif isinstance(pos, (tuple, list)) and len(pos) == 2:
            pos = pg.Point(*pos)
            
        elif isinstance(pos, (QtCore.QPoint, QtCore.QPointF)):
            pos = pg.Point(pos.x(), pos.y())
            
        elif not isinstance(pos, pg.Point):
            raise TypeError(f"pos expected a 2-tuple or number, QPoint, QPointF or pg.Point; got {type(pos).__name__} instead")
        
        # print(f"{self.__class__.__name__}.addLabel(text={text})")
        textItem = pg.TextItem(text, **kwargs)
        textItem.setPos(pos)
        
        cFrame = self.frameIndex[self.currentFrame]
        
        if cFrame not in self._label_overlays_:
            self._label_overlays_[cFrame] = dict()
            
        self._label_overlays_[cFrame][axNdx] = textItem
        
        axis.addItem(textItem, ignoreBounds=True)
        
    def showLegends(self, value:bool):
        if value == True:
            for axis in self.axes:
                self.addLegend(axis) # use default values
                
        else:
            for axis in self.axes:
                self.removeLegend(axis)
                
        self.refresh()
        
    @singledispatchmethod
    def addDataFrame(self, obj):
        """Adds a new data frame to the displayed data.
Automatically displays the last data frame.
The following table shows what this method supports:
    
Current data type   Added data type     Allowed     Resulting data type     Comments & side effects
===================================================================================================
None                neo.Block           ✓           same as new data        New data      
                                                                            'takes over'
                    neo.Segment         ✓           same as new data
    
                    neo signal-like¹    ✓           same as new data
    
                    NoneType            ✓                                   does nothing

neo.Block           neo.Block           ✓           list of neo.Block       Updates internal 
                                                                            variables (self._meta_index, etc)

                    neo.Segment         ✓           neo.Block               Segment added to 
                                                                            the current data segments
                                                                            CAUTION You may not want this
        
                    NoneType            ✓                                   does nothing
    
                    anything else       ❌
    
list of neo.Block   neo.Block           ✓           list of neo.Block       Appends data to
                                                                            current list; updates self._meta_index
                    NoneType            ✓                                   does nothing
    
                    anything else       ❌
    
neo.Segment         neo.Block           ❌
    
                    neo.Segment         ✓           list of neo.Segment
    
                    NoneType            ✓                                   does nothing
    
                    anything else       ❌
    
list of neo.Segment neo.Segment         ✓
    
                    NoneType            ✓                                   does nothing
    
                    anything else       ❌
    
anything else       anything else       ❌
        
                    NoneType            ✓                                   does nothing
    
=====================================================================================================
    
¹ neo.Analogsignal, neo.IrregularlySampledSignal, DataSignal and IrregularlySampledDataSignal

    """
        raise NotImplementedError(f"Objects of type {type(obj).__name__} are not supported")

    @addDataFrame.register(type(None))
    def _(self, obj=None):
        return
    
    @addDataFrame.register(neo.Block)
    def _(self, obj:neo.Block):
        if len(obj.segments) == 0:
            return
        
        if self.yData is None:
            self.setData(obj)
            return
            
        
        if isinstance(self.yData, neo.Block):
            newData = [self.yData, obj]
            
        elif isinstance(self.yData, (tuple, list)):
            if all(isinstance(v, neo.Block) for v in self.yData):
                newData = list(self.yData)
                newData.append(obj)
                
            else:
                warnings.warn(f"Cannot append {type(obj).__name__} to a sequence of {type(self.yData[0]).__name__}")
                return
            
        else:
            warnings.warn(f"Cannot add frame {type(obj).__name__} data to {type(self.yData).__name__}")
            return
            
        self._data_frames_ += len(obj.segments)
        
        self.frameIndex = normalized_index(self._data_frames_)
        
        self._number_of_frames_ = len(self.frameIndex)
        
        obj_signal_axes = max(len(s.analogsignals) + len(s.irregularlysampledsignals) for s in obj.segments)
        if obj_signal_axes != self._n_signal_axes_:
            self._n_signal_axes_ = max(self._n_signal_axes_, obj_signal_axes)
            self._setup_axes_()
        
        new_frame_meta_index = np.recarray((len(obj.segments),1),
                                           dtype = [('block', int), ('segment', int)])
        
        bk = len(newData)-1
        
        mIndex = np.array(list(((bk,sk) for sk in range(len(obj.segments)))))
        
        new_frame_meta_index = np.recarray((len(obj.segments), 1),
                                            dtype = [('block', int), ('segment', int)])
        
        new_frame_meta_index.block[:,0] = mIndex[:,0]
        new_frame_meta_index.segment[:,0] = mIndex[:,1]
        
        self._meta_index = np.concatenate((self._meta_index, new_frame_meta_index)).view(np.recarray)
        
        self._yData_ = newData
        
        self.actionDetect_Triggers.setEnabled(check_ephys_data_collection(self._yData_))
        
        self._frames_spinBoxSlider_.range = range(self._number_of_frames_)
        
        self.currentFrame = self._number_of_frames_ - 1
        
        # with self.observed_vars.observer.hold_trait_notifications():
        # if self.observed_vars.get("yData", None) is not None:
        #     self.observed_vars["yData"] = None
        self.observed_vars["yData"] = self._yData_
        

    @addDataFrame.register(neo.Segment)
    def _(self, obj:neo.Segment):
        if self.yData is None:
            self.setData(obj)
            return
    
        if isinstance(self.yData, neo.Block):
            self._yData_.segments.append(obj)
            
            self._data_frames_ = len(self._yData_.segments)
            self.frameIndex = normalized_index(self._data_frames_)
            self._number_of_frames_ = len(self._frameIndex_)
            
            self._meta_index = np.recarray((self._number_of_frames_, 1),
                                           dtype = [('block', int), ('segment', int)])
            
            self._meta_index.block[:,0] = 0
            self._meta_index.segment[:,0] = self.frameIndex
            
        else:
            if isinstance(self.yData, neo.Segment):
                newData = [self.yData, obj]
                
            elif isinstance(self.yData, (tuple, list)):
                if all(isinstance(v, neo.Segment) for v in self.yData):
                    newData = list(self.yData)
                    newData.append(obj)
                    
                else:
                    warnings.warn(f"Cannot append {type(obj).__name__} to a sequence of {type(self.yData[0]).__name__}")
                    return
                
            else:
                warnings.warn(f"Cannot add frame {type(obj).__name__} data to {type(self.yData).__name__}")
                return
            
            self.frameIndex = range(len(newData))
            self._data_frames_  = len(newData)
            
            self._number_of_frames_ = len(self.frameIndex)
            
            self._meta_index = np.recarray((self._number_of_frames_,1),
                                            dtype = [('frame', int)])
            
            self._meta_index.frame[:,0] = self.frameIndex
            
            self._yData_ = newData
            
        obj_signal_axes = len(obj.analogsignals) + len(obj.irregularlysampledsignals)
        if obj_signal_axes != self._n_signal_axes_:
            self._n_signal_axes_ = max(self._n_signal_axes_, obj_signal_axes)
            
            self._setup_axes_()
                
        if self.observed_vars.get("yData", None) is not None:
            self.observed_vars["yData"] = None
        self.observed_vars["yData"] = self._yData_
        
        self.actionDetect_Triggers.setEnabled(check_ephys_data_collection(self._yData_))

        self._frames_spinBoxSlider_.range = range(self._number_of_frames_)
        
        self.currentFrame = self._number_of_frames_ - 1
        
    def addLegend(self, axis:typing.Optional[typing.Union[int, pg.PlotItem]]=None, 
                  x:typing.Optional[numbers.Number]=30,
                  y:typing.Optional[numbers.Number]=30,
                  **kwargs):
        axis, axNdx = self._check_axis_spec_ndx_(axis)
        cFrame = self.frameIndex[self.currentFrame]
        
#         if not isinstance(x, numbers.Number):
#             minX, maxX = self._get_axis_data_X_range_(axis)
#             x = minX
#             
#         if not isinstance(y, numbers.Number):
#             minY, maxY = self._get_axis_data_Y_range_(axis)
#             y = maxY
        
        # make sure there is at most one legend here
        # if the axis already has one legend item, don't add
        # if the axis has more than one legend item, remove all but the first
        currentLegends = [i for i in axis.items if isinstance(i, pg.LegendItem)]
        if len(currentLegends):
            currentLegend = currentLegends[0]
            if len(currentLegends) > 1:
                for i in currentLegends[1:]:
                    axis.removeItem(i)
                    
            # now make sure this item is in the _legends_ cache
            # check if there is already a legend item here
            if isinstance(self._legends_.get(cFrame, None), dict):
                if isinstance(self._legends_[cFrame].get(axNdx, None), pg.LegendItem):
                    if self._legends_[cFrame][axNdx] == currentLegend:
                        return

        # for sanity, also check if there is a cached legend even if this is not
        # a chuild of the axis - in this case, just remove it
        if isinstance(self._legends_.get(cFrame, None), dict):
            self._legends_[cFrame].pop(axNdx, None)
            
        legendItem = axis.addLegend((x,y) ,**kwargs)
        
        if cFrame not in self._legends_:
            self._legends_[cFrame] = dict()
            
        self._legends_[cFrame][axNdx] = legendItem
        
    def removeLegend(self, axis:typing.Optional[typing.Union[int, pg.PlotItem]]=None):
        if axis not in range(-len(self.plotItems), len(self.plotItems)):
            return
        axis, axNdx = self._check_axis_spec_ndx_(axis)
        cFrame = self.frameIndex[self.currentFrame]
        if cFrame in self._legends_:
            if isinstance(self._legends_[cFrame], dict):
                self._legends_[cFrame].pop(axNdx, None)
                if len(self._legends_[cFrame]) == 0:
                    self._legends_.pop(cFrame)
                    
        self._remove_legend(axis)
        
    def removeLabels(self, axis:typing.Optional[typing.Union[int, pg.PlotItem]]=None):
        """ Removes ALL labels (TextItems) from the given axis
        """
        # if axis not in range(-len(self.plotItems), len(self.plotItems)):
        #     return
            
        axis, axNdx = self._check_axis_spec_ndx_(axis)
        cFrame = self.frameIndex[self.currentFrame]
        
        if cFrame in self._label_overlays_:
            if isinstance(self._label_overlays_[cFrame], dict):
                if isinstance(self._label_overlays_[cFrame].get(axNdx, None), (tuple, list)):
                    self._label_overlays_[cFrame][axNdx].clear()
                else:
                    # self._label_overlays_[cFrame].pop(axNdx)
                    self._label_overlays_[cFrame][axNdx] = list()
                    
                # if len(self._label_overlays_[cFrame]) == 0:
                #     self._label_overlays_.pop(cFrame)
                    
        # call this just in case we have overlays that escaped the cache mechanism
        self._clear_labels_overlay_(axis)
                
        
    def closeEvent(self, evt):
        """Override ScipyenViewer.closeEvent.
        Attempt to deal with situations where C/C++ objects are deleted before 
        their wrappers in pyqtgraph
        """
        # TODO/FIXME 2022-11-16 21:37:13
        # pgmembers = inspect.getmembers(self, lambda x: isinstance(x, (pg.GraphicsItem, pg.GraphicsView, QtWidgets.QWidget)))
        
        super().closeEvent(evt)
        evt.accept()

    def addCursors(self, /, *args, **kwargs):
        """Manually adds a set of cursors to the selected axes in the SignalViewer window.
        
        Requires at least one Axis object, therefore some data must be plotted first.
        
        Var-positional parameters (args):
        =================================
        Comma-separated coordinates, or numpy array of cursor coordinates:
                
        • for crosshair cursors the coordinates of ONE cursor must be
            given as (x,y) pair: comma-separated sequence of two-element tuples,
            of a float 2D numpy array with shape = (N,2) where N is the number 
            of cursors.

        • for vertical and horizontal cursors the coordinates must be
            given as a comma-separated sequence of floats, or a float numpy array
            with shape (N,) or (N,1) where N is the number of cursors.
        
        • alternatively, each "cursor" above can be specified by DataCursor objects.
                    
        Var-keyword arguments ("name=value" pairs):
        ===========================================
        cursorType: str or SignalCursorsTypes enum value
                    When a str it should be one of "c", "v", "h", respectively, 
                    for crosshair, vertical, horizontal cursors.
        
                    All cursors created with this method will have the same type
        
                    Optional, default is "c".

        xwindow = 1D sequence of floats with the horizontal extent of the cursor window
            (for crosshair and vertical cursors); must have as many elements as 
            coordinates supplied in the *where argument
        
        ywindow   = as above, for crosshair and horizontal cursors
        
        labels    = 1D sequence of str for cursor IDs; must have as many
            elements as supplied through the *where argument
            NOTE: the display of cursor values is controlled by 
            self.setCursorsShowValue property (and its checkbox in the settings 
            menu).`
        
        axis: int, or str, pyqtgraph.PlotItem, or None (default)
            ∘   When an int this is a valid axis index in the current instance 
                of ScipyenViewer (from top to bottom, 0 -> number of axes - 1)
            
            ∘   When a str, this can only be "all" or "a", meaning that the new 
                cursors will span all axes (multi-axis cursors)
        
            ∘   When None (default) the cursors will be created in the axis that
                is currently selected, or axis 0 is no axis is selected.
        
        """
        xwindow = kwargs.pop("xwindow", self.defaultCursorWindowSizeX)
        ywindow = kwargs.pop("ywindow", self.defaultCursorWindowSizeY)
        labels  = kwargs.pop("labels",  None)
        axis    = kwargs.pop("axis",    None)
        
        showEditor = kwargs.pop("editFirst", False)
        
        if len(self.plotItems) == 0:
            axis = self.signalsLayout.scene()

        if axis is None:
            axis = self._selected_plot_item_ if isinstance(self._selected_plot_item_, pg.PlotItem) else self.plotItems[0]
            
        elif isinstance(axis, pg.PlotItem):
            if axis not in self.plotItems:
                raise ValueError(f"Specificed axis {axis} is not found in this SignalViewer")
            
        elif isinstance(axis, int):
            if axis in range(len(self.plotItems)):
                axis = self.plotItems[axis]
            else:
                raise ValueError(f"Invalid axis index {axis} for {len(self.plotItems)} axes")
                
        elif isinstance(axis, (tuple, list)):
            if all(isinstance(v, int) for v in axis):
                if any(v not in range(len(self.plotItems))):
                    raise ValueError(f"Invalid axis indices {axis} for {len(self.plotItems)} axes")
                
            elif all(isinstance(v, pg.PlotItem) for v in axis):
                if any(v not in self.plotItems for v in axis):
                    raise ValueError("Not all specified axes sbelong to this SignalViewer")
                
            elif all(isinstance(v, str) for v in axis):
                names = [p.vb.name for p in self.plotItems]
                
                if any(v not in names for v in axis):
                    raise ValueError(f"Not all axes in {axis} belong to this SignalViewer with axes {names}")
                
                ndx = [names.index(v) for v in axis]
                
                axis = [self.plotItems[v] for v in ndx]
            
        elif isinstance(axis, str):
            if axis.lower() in ("all", "a"):
                axis = self.plotItems
                
            else:
                names = [p.vb.name for p in self.plotItems]
                
                if axis not in names:
                    raise ValueError(f"axis with name {axis} not found in this SignalViewer")
                
                ndx = names.index(axis)
                
                axis = self.plotItems[ndx]
            
        cursorType = kwargs.pop("cursorType", None)
        
        if cursorType is None:
            cursorType = kwargs.pop("type", "c")
            
        if isinstance(cursorType, str):
            if cursorType.lower() in ("h", "horiz", "horizontal"):
                cursorType = SignalCursorTypes.horizontal
            elif cursorType.lower() in ("v", "vert", "vertical"):
                cursorType = SignalCursorTypes.vertical
            elif cursorType.lower() in ("c", "cross", "crosshair"):
                cursorType = SignalCursorTypes.crosshair
                
            else:
                raise ValueError(f"{cursorType} not supported")
            
        elif not isinstance(cursorType, SignalCursorTypes):
            raise TypeError(f"Expecting cursorType a str or a gui.cursors.SignalCursorTypes; instead, got {type(cursorType).__name__}")
            
        
        if len(args) == 0: # no coordinates given
            x = y = None
            
        elif len(args) == 1: # a single object passed - figure it out
            if isinstance(args[0], np.ndarray):
                self._use_coords_sequence_(args[0], xwindow, ywindow, labels, axis, cursorType)
                return
                
            elif isinstance(args[0], (tuple, list)):
                x, y = self._addCursors_parse_coords_(args[0], cursorType)
                
            elif isinstance(args[0], DataCursor):
                self.addCursor(cursorType, args[0])
            
        elif isinstance(args, (tuple, list)):
            if all(isinstance(a, numbers.Number) for a in args):
                self._use_coords_sequence_(args, xwindow, ywindow, labels, axis, cursorType)
                return
            
            elif all(isinstance(a, DataCursor) for a in args):
                if len(args) > 2:
                    raise SyntaxError(f"Too many DataCursor objects passed: expecting at most two, got {len(args)}")
            
                

        self.addCursor(cursorType=cursorType, x=x, y=y, 
                       xwindow=xwindow, ywindow=ywindow,
                       label=labels, 
                       show_value = self.setCursorsShowValue.isChecked(),
                       axis = axis, 
                       editFirst = showEditor)
        
    
    def addCursor(self, cursorType: typing.Optional[typing.Union[str, SignalCursorTypes]] = None, 
                  x: typing.Optional[typing.Union[numbers.Number, DataCursor]] = None, 
                  y: typing.Optional[typing.Union[numbers.Number, DataCursor]] = None, 
                  xwindow: typing.Optional[numbers.Number] = None, 
                  ywindow: typing.Optional[numbers.Number] = None, 
                  xBounds: typing.Optional[numbers.Number] = None, 
                  yBounds: typing.Optional[numbers.Number] = None, 
                  label: typing.Optional[typing.Union[int, str, pg.PlotItem]] = None, 
                  follows_mouse: bool = False, 
                  axis: typing.Optional[int] = None, 
                  editFirst: bool=False,
                  **kwargs):
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
        precision = kwargs.pop("precision", self.cursorLabelPrecision)
        
        crsID = self._addCursor_(cursor_type = cursorType,
                                x = x, y = y, xwindow = xwindow, ywindow = ywindow,
                                xBounds = xBounds, yBounds = yBounds,
                                axis = axis, label=label,
                                follows_mouse=follows_mouse,
                                precision = precision,
                                editFirst = editFirst,
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
                    axis = index of the axis where the cursors are to be shown (default is 0)
        """
        xwindow = self.defaultCursorWindowSizeX
        ywindow = self.defaultCursorWindowSizeY
        labels  = None
        
        allowed_keywords = ["xwindow", "ywindow", "labels", "axis"]
        
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
                
            axis = kwargs.get("axis", 0)
                
                
        if len(where) == 1:
            where = where[0]
            
        self.slot_removeCursors()
        self.displayFrame()
        self.addCursors(*where, cursorType=cursorType, xwindow = xwindow, ywindow = ywindow, labels = labels, axis=axis)
        
    @safeWrapper
    def reportCursors(self):
        text = list()
        crn = sorted([(c,n) for c,n in self._data_cursors_.items()], key = lambda x: x[0])
        
        for cursors_name, cursor in crn:
            if isinstance(cursor, SignalCursor):
                cursor_label_text = "%s %s " % ("Dynamic", cursor.ID) if cursor.isDynamic else "%s" % cursor.ID
                #cursor_label_text = "%s %s " % ("Dynamic", cursor.ID) if cursor.isDynamic else "%s %s" % ("SignalCursor", cursor.ID)
                
                if cursor.isSingleAxis:
                    if cursor.hostItem.vb is not None and isinstance(cursor.hostItem.vb.name, str) and len(cursor.hostItem.vb.name.strip()):
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
                        
                        dataitems = cursor.hostItem.dataItems
                        
                        for kdata, dataitem in enumerate(dataitems):
                            data_x, data_y = dataitem.getData()
                            if x is None or data_x is None:
                                continue
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
                            plot_item_cursor_pos_text.append("X: %f (window: %f)" % (x, cursor.xwindow))
                            
                        if cursor.cursorTypeName in ("crosshair", "horizontal"):
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
        
    # ### BEGIN PyQt slots
    
    @pyqtSlot(int)
    @safeWrapper
    def slot_analogSignalsComboBoxIndexChanged(self, index):
        """Triggered by a change in Analog signal selection combo box.
    This combo box is self.analogSignalComboBox"""
        # FIXME: 2023-07-09 12:12:42
        # this signal is only triggered when the combo box selection has changed
        # if you wanted to choose signals again it won't be called, because the 
        # combo box index has not changed
        # NOTE: 
        if len(self._frame_analog_map_) == 0:
            return
        
        if index == 0: # "All" selected
            self.guiSelectedAnalogSignalEntries.clear()
            
        elif index == self.analogSignalComboBox.count()-1: # "Choose" selected
            
            available = [self.analogSignalComboBox.itemText(k) for k in range(1, self.analogSignalComboBox.count()-1)]
            
            preSelected = [i for i in self.guiSelectedAnalogSignalEntries if i in available]
            
            if len(preSelected) == 0:
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
                    self.guiSelectedAnalogSignalEntries[:] = sel_items[:]
                
                    
        else:
            self.guiSelectedAnalogSignalEntries = [self.analogSignalComboBox.currentText()]

        # NOTE: 2023-07-09 11:54:06
        # self._new_frame_ guards against replotting signals when there's no 
        # actual frame change
        # used by self._plot_signals_(…), self._plot_events_(…), self._plotSpikeTrains_(…)
        #
        self._new_frame_ = False 
        self.displayFrame()
        self._new_frame_ = True
        
    @pyqtSlot(int)
    def _slot_plotSpikeTrainsCheckStateChanged_(self, state):
        self._plot_spiketrains_ = state == QtCore.Qt.Checked
        self.displayFrame()
        
    @pyqtSlot(int)
    def _slot_plotEventsCheckStateChanged_(self, state):
        self._plot_events_ = state == QtCore.Qt.Checked
        self.displayFrame()
        
    @pyqtSlot(int)
    def _slot_plotEpochsCheckStateChanged_(self, state):
        self._plot_epochs_ = state == QtCore.Qt.Checked
        self.displayFrame()
        
    @pyqtSlot(int)
    @safeWrapper
    def _slot_plotAnalogSignalsCheckStateChanged_(self, state):
        self._plot_analogsignals_ = state == QtCore.Qt.Checked
        self.displayFrame()

    @pyqtSlot(int)
    @safeWrapper
    def _slot_plotIrregularSignalsCheckStateChanged_(self, state):
        self._plot_irregularsignals_ = state == QtCore.Qt.Checked
        self.displayFrame()
        
    @pyqtSlot(bool)
    @safeWrapper
    def slot_showCursorsDock(self, value:bool):
        self.cursorsDockWidgetEnabled = value==True
        # if value == True:
        #     self.cursorsDockWidget.show()
        # else:
        #     self.cursorsDockWidget.hide()
        
    @pyqtSlot(bool)
    @safeWrapper
    def slot_showAnnotationsDock(self, value:bool):
        self.annotationsDockWidgetEnabled = value == True
        # if value == True:
        #     self.annotationsDockWidget.show()
        # else:
        #     self.annotationsDockWidget.hide()
        
    @pyqtSlot()
    @safeWrapper
    def slot_detectTriggers(self):
        if isinstance(self._yData_, (neo.Block, neo.Segment)) or (isinstance(self._yData_, (tuple, list)) and all([isinstance(v, (neo.Block, neo.Segment)) for v in self._yData_])):
            from gui.triggerdetectgui import TriggerDetectDialog
            tdlg = TriggerDetectDialog(ephysdata=self._yData_, ephysViewer=self, parent=self)
            tdlg.open()
        
    @pyqtSlot(str)
    @safeWrapper
    def slot_reportCursorPosition(self, crsId = None):
        self.reportCursors()
        
    @pyqtSlot(int)
    @safeWrapper
    def slot_irregularSignalsComboBoxIndexChanged(self, index):
        """Triggered by a change in Irregular signal selection combo box.
    This combo box is self.irregularSignalComboBox"""
                
        if len(self._frame_irregs_map_) == 0 :
            return
        if index == 0:
            # "All" selected ⇒ display all signals
            self.guiSelectedIrregularSignalEntries.clear()
            
        elif index == self.irregularSignalComboBox.count()-1:
            # "Choose" ⇒ popup up dialog to select which signal to choose
            available = [self.irregularSignalComboBox.itemText(k) for k in range(1, self.irregularSignalComboBox.count()-1)]
            
            preSelected = [i for i in self.guiSelectedIrregularSignalEntries if i in available]
            if len(preSelected) == 0:
                preSelected = None

            dlg = ItemsListDialog(parent=self, 
                                       itemsList = available, 
                                       preSelected = preSelected,
                                       title="Select Irregular Signals to Plot", 
                                       modal=True,
                                       selectmode=QtWidgets.QAbstractItemView.ExtendedSelection)
            
            if dlg.exec() == 1:
                sel_items = dlg.selectedItemsText
                
                if len(sel_items):
                    self.guiSelectedIrregularSignalEntries[:] = sel_items[:]
                    
        else:
            self.guiSelectedIrregularSignalEntries = [self.irregularSignalComboBox.currentText()]
    
        # NOTE: 2023-07-09 12:00:58
        # guard against replotting signals when there's no actual frame change
        # see # NOTE: 2023-07-09 11:54:06
        self._new_frame_ = False 
        self.displayFrame()
        self._new_frame_ = True
         
    # ### END PyQt slots
    
    def var_observer(self, change):
        # print(f"\n{self.__class__.__name__}[{self.windowTitle()}].var_observer change = {change}")
#         if isinstance(newObj, neo.Block):
#             print(f"new: {newObj} name = {newObj.name}\n\t with segments = {newObj.segments}")
        
        if self.currentFrame not in self.frameIndex:
            self.currentFrame = self.frameIndex[-1] # ⇒ also calls self.displayFrame()
        else:
            self._new_frame_ = True # to force re-plotting data, see:
                                    # NOTE: 2023-01-04 22:14:55 - _plot_signals_()
                                    # NOTE: 2023-05-16 23:05:22 - _plot_signals_()
                                    # NOTE: 2023-05-16 23:04:37 - _plotEvents_()
                                    # NOTE: 2023-05-16 23:02:20 - _plotSpikeTrains_()
                                    
            self.displayFrame()
            # NOTE: BUG 2023-06-02 14:10:53
            # below crashes due to creation of GUI elements in a parent on a
            # different thread
            # worker = pgui.GuiWorker(self.displayFrame)
            # self.threadpool.start(worker)
            self._new_frame_ = False
        
        self._var_notified_ = True

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

        ct = self.signalCursor(id1).cursorType()
        
        other = list()
        
        for cid in ids:
            if not self._hasCursor_(cid):
                raise ValueError("SignalCursor %s not found" % cid)
            
            if self.signalCursor(cid).cursorType() != ct:
                raise ValueError("Cannot link cursors of different types")

            other.append(self.signalCursor(cid))
        
        self.signalCursor(id1).linkTo(*other)
            
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
        
        ct = self.signalCursor(id1).cursorType()
        
        if len(ids) == 1: 
            if isinstance(ids[0], str): # it is a cursor ID
                if not self._hasCursor_(ids[0]):
                    raise ValueError("SignalCursor %s not found" % ids[0])
                
                if self.signalCursor(id1).cursorType() != self.signalCursor(ids[0]).cursorType():
                    raise ValueError("Cursors of different types cannot be linked")
                    
                self.signalCursor(id1).unlinkFrom(self.signalCursor(ids[0]))
                
            elif isinstance(ids[0], tuple) or isinstance(ids[0], list):# this is a tuple or list of cursor IDs: we unlink id1 from each one, keep their link state unchanged
                other = list()
                for cid in ids[0]:
                    if not self._hasCursor_(cid):
                        raise ValueError("SignalCursor %s not found" % cid)
                    
                    if self.signalCursor(cid).cursorType() != ct:
                        raise ValueError("Cursors of different types cannot be linked")
                    
                    other.append(self.signalCursor(cid))
                
                self.signalCursor(id1).unlinkFrom(*other)
                
        elif len(ids) > 1: # a comma-seprated list of cursor IDs: unlink _ALL_ of them
            other = list()
            
            for cid in ids:
                if not self._hasCursor_(cid):
                    raise ValueError("SignalCursor %s not found " % cid)
                
                if self.signalCursor(cid).cursorType() != ct:
                    raise ValueError("Cursors of different types cannot be linked")
                
                other.append(self.signalCursor(cid))
            
            self.signalCursor(id1).unlinkFrom(*other)
            
            for c in other:
                c.unlink()
                
        else: # unlink ALL
            self.signalCursor(id1).unlink()

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
        
    def _addCursor_(self, cursor_type: typing.Union[str, SignalCursorTypes], 
                    x: typing.Optional[typing.Union[numbers.Number, pq.Quantity, DataCursor]] = None,
                    y: typing.Optional[typing.Union[numbers.Number, pq.Quantity, DataCursor]] = None, 
                    xwindow: typing.Optional[typing.Union[numbers.Number, pq.Quantity]] = None,
                    ywindow: typing.Optional[typing.Union[numbers.Number, pq.Quantity]] = None, 
                    xBounds: typing.Optional[tuple] = None,
                    yBounds: typing.Optional[tuple] = None,
                    axis: typing.Optional[typing.Union[int, str, pg.PlotItem, pg.GraphicsScene]] = None,
                    label:typing.Optional[str] = None, 
                    follows_mouse: bool = False, 
                    precision:typing.Optional[int] = None, 
                    editFirst: bool = False,
                    **kwargs) -> str:
        """Common landing zone for signal cursor creation methods.
        kwargs: var-keyword parameters for SignalCursor constructor (pen, etc)
        """
        # print(f"{self.__class__.__name__}_addCursor_ cursor_type = {cursor_type}, x = {x} ,y = {y}, xwindow = {xwindow}, ywindow = {ywindow},xBounds = {xBounds},yBounds = {yBounds}, axis={axis}, label= {label}, follows_mouse = {follows_mouse}")
        relative = kwargs.pop("relative", True)
        
        #### BEGIN Figure out cursors destination: axis or scene
        # NOTE: it seemingly makes no sense to add a cursors when there are no
        # plot items (axes); nevertheless the cursor can and should be added
        # to the GraphicsScene
        if len(self.signalsLayout.items) == 0:
            axis = self.signalsLayout.scene() # force adding to the pg.GraphicsScene when there are not plot items available
            
        elif axis is None:
            if self._selected_plot_item_ is None:
                axis = self.axis(0)
                
            else:
                axis = self._selected_plot_item_
            
        elif isinstance(axis, int):
            if axis < 0 or axis >= len(self.axes):
                raise ValueError("Invalid axis index %d for %d axes" % (axis, len(self.axes)))
            
            axis = self.axis(axis)
            
        elif isinstance(axis, str) and axis.lower().strip() in ("all", "a"):
            axis = self.signalsLayout.scene()
            
        elif not isinstance(axis, (pg.PlotItem, pg.GraphicsScene)):
            raise TypeError("axes expected to be an int, a str ('all' or 'a'), a pyqtgraph.PlotItem, a pyqtgraph.GraphicsScene, or None; got %s instead" % type(axes).__name__)
            
        #### END Figure out cursors destination: axis or scene
        
        if any(isinstance(v, DataCursor) for v in (x,y)):
            cursor_type = SignalCursorTypes.getType((isinstance(y, DataCursor), isinstance(x, DataCursor)))
            # print(f"{self.__class__.__name__}._addCursor_ (DataCursor): cursor_type = {cursor_type}")
        
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
            
        #### BEGIN check cursors coordinates
        if isinstance(axis, pg.PlotItem): # single-axis cursor - a.k.a cursor in axis
            if axis not in self.signalsLayout.items:
                return
            
            data_range = guiutils.getPlotItemDataBoundaries(axis)
            view_range = axis.viewRange()
            
            if x is None:
                x = view_range[0][0] + (view_range[0][1] - view_range[0][0])/2
            
            elif isinstance(x, pq.Quantity):
                x = float(x.magnitude.flatten()[0])
                
            elif not isinstance(x, (numbers.Number, DataCursor)):
                raise TypeError("Unexpected type for x coordinate: %s" % type(x).__name__)
            
            if xBounds is None:
                xBounds = data_range[0]
                # xBounds = view_range[0]
                
            if y is None:
                y = view_range[1][0] + (view_range[1][1] - view_range[1][0])/2
            
            elif isinstance(y, pq.Quantity):
                y = float(y.magnitude.flatten()[0])
            
            elif not isinstance(y, (numbers.Number, DataCursor)):
                raise TypeError("Unexpected type for y coordinate: %s" % type(y).__name__ )
            
            if yBounds is None:
                yBounds = data_range[1]
                # yBounds = view_range[1]
                
            # print(f"{self.__class__.__name__}._addCursor_ single-axis x = {x}")
            
        elif isinstance(axis, pg.GraphicsScene): # multi-axis cursor - a.k.a cursor in scene
            if axis is not self.signalsLayout.scene():
                return
            
            if len(self.signalsLayout.items) == 0:
                # there is no axis (plotitem) - never executed, see NOTE: 2023-01-14 23:23:06
                # warnings.warn("There is no axis in the viewer; have you plotted anything yet?\nThe cursor's coordinates will be reset when plotting")
                
                scene_rect = self.signalsLayout.scene().sceneRect()
                
                if xBounds is None:
                    xBounds = (scene_rect.x(), scene_rect.x() + scene_rect.width())
                
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
                
                if xBounds is None:
                    xBounds = [min_point.x(), max_point.x()]
                
                if yBounds is None:
                    yBounds = [min_point.y(), max_point.y()]
                
            if x is None:
                x = float(xBounds[0] + np.diff(xBounds)/2)
                # print(f"auto x = {x}")
                
            elif isinstance(x, pq.Quantity):
                x = float(x.magnitude.flatten()[0])
                
            elif not isinstance(x, (numbers.Number, DataCursor)):
                raise TypeError("Unexpected type for x coordinate: %s" % type(x).__name__)
            
            if y is None:
                # y = min_point.y() + (max_point.y() - min_point.y())/2.
                x = float(yBounds[0] + np.diff(yBounds)/2)
                
            elif isinstance(y, pq.Quantity):
                y = float(y.magnitude.flatten()[0])
                
            elif not isinstance(y, (numbers.Number, DataCursor)):
                raise TypeError("Unexpected type for y coordinate: %s" % type(y).__name__)
                    
            # print(f"{self.__class__.__name__}._addCursor_ multi-axis x = {x}")
            
        #### END check cursors coordinates
        
        if not isinstance(cursor_type, (str, SignalCursorTypes)):
            raise TypeError("cursor_type expected to be a str or a SignalCursorTypes; got %s instead" % type(cursor_type).__name__)

        if isinstance(cursor_type, SignalCursorTypes):
            cursor_type = cursor_type.name
        
        if cursor_type in ("vertical", "v", SignalCursorTypes.vertical):
            cursorDict = self._verticalSignalCursors_
            crsPrefix = "dv" if follows_mouse else "v"
            
            ywindow = 0.0
            pen = QtGui.QPen(QtGui.QColor(self.cursorColors["vertical"]), 1, QtCore.Qt.SolidLine)
            linkedPen = QtGui.QPen(QtGui.QColor(self.linkedCursorColors["vertical"]), 1, QtCore.Qt.SolidLine)
            pen.setCosmetic(True)
            linkedPen.setCosmetic(True)
            
        elif cursor_type in ("horizontal", "h", SignalCursorTypes.horizontal):
            cursorDict = self._horizontalSignalCursors_
            crsPrefix = "dh" if follows_mouse else "h"
            xwindow = 0.0
            pen = QtGui.QPen(QtGui.QColor(self.cursorColors["horizontal"]), 1, QtCore.Qt.SolidLine)
            linkedPen = QtGui.QPen(QtGui.QColor(self.linkedCursorColors["horizontal"]), 1, QtCore.Qt.SolidLine)
            pen.setCosmetic(True)
            linkedPen.setCosmetic(True)
            
        elif cursor_type in ("crosshair", "c", SignalCursorTypes.crosshair):
            cursorDict = self._crosshairSignalCursors_
            crsPrefix = "dc" if follows_mouse else "c"
            pen = QtGui.QPen(QtGui.QColor(self.cursorColors["crosshair"]), 1, QtCore.Qt.SolidLine)
            linkedPen = QtGui.QPen(QtGui.QColor(self.linkedCursorColors["crosshair"]), 1, QtCore.Qt.SolidLine)
            pen.setCosmetic(True)
            linkedPen.setCosmetic(True)
            
        else:
            raise ValueError("unsupported cursor type %s" % cursor_type)
        
        hoverPen = QtGui.QPen(QtGui.QColor(self._cursorHoverColor_), 1, QtCore.Qt.SolidLine)
        hoverPen.setCosmetic(True)
        
        nCursors = len(cursorDict)
        
        # print(f"{self.__class__.__name__}._addCursor_ crsPrefix = {crsPrefix}")
        
        if label is None:
            crsId = "%s%s" % (crsPrefix, str(nCursors))
            
        else:
            currentCursorLabels = cursorDict.keys()
            
            crsId = label
            
        if precision is None:
            if isinstance(axis, pg.PlotItem):
                precision = self.getAxis_xDataPrecision(axis)
                    
            else:
                if len(self.plotItems):
                    pi_precisions = [self.getAxis_xDataPrecision(ax) for ax in self.plotItems]
                    precision = min(pi_precisions)
                    
        cursor = SignalCursor(axis, 
                                   x = x, y = y, xwindow=xwindow, ywindow=ywindow,
                                   cursor_type = cursor_type,
                                   cursorID = crsId,
                                   linkedPen = linkedPen,
                                   pen = pen, 
                                   hoverPen=hoverPen,
                                   # parent = self, 
                                   parent = axis, 
                                   follower = follows_mouse, 
                                   relative = relative,
                                   xBounds = xBounds,
                                   yBounds = yBounds,
                                   precision = precision,
                                   **kwargs)
        
        cursorDict[crsId] = cursor
        
        cursorDict[crsId].sig_cursorSelected[str].connect(self.slot_selectCursor)
        cursorDict[crsId].sig_reportPosition[str].connect(self.slot_reportCursorPosition)
        cursorDict[crsId].sig_doubleClicked[str].connect(self.slot_editCursor)
        cursorDict[crsId].sig_lineContextMenuRequested[str].connect(self.slot_cursorMenu)
        cursorDict[crsId].sig_editMe[str].connect(self.slot_editCursor)
        
        if editFirst:
            crsId = self._editCursor_(crsId=crsId)
        
        return crsId
    
    def _editCursor_(self, crsId=None, choose=False):
        from core.utilities import counter_suffix
        
        if len(self._data_cursors_) == 0:
            return
        
        cursor = None
        
        if crsId is None:
            cursor = self.selectedDataCursor # get the selected cursor if no ID given
                
        else:
            cursor = self.signalCursor(crsId) # otherwise try to get cursor with given ID
            
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
                
        else: # creates a cursor? FIXME/TODO 2023-06-17 14:14:26
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
                cursor = self.signalCursor(crsId)
                initialID = crsId
                
            if cursor is None: # bail out
                return
            
            name = d.namePrompt.text() # when a name change is desired this would be different from the cursor's id
            
            if initialID is not None:
                if name is not None and len(name.strip()) > 0 and name != initialID: # change cursor id if new name not empty
                    cursorNames = [c.ID for c in self.cursors]
                    if name in cursorNames:
                        newName = counter_suffix(name, cursorNames, "")
                        
                        namedlg = qd.QuickDialog(self, f"A cursors named {name} already exists")
                        namedlg.addLabel(f"Rename {name}")
                        pw = qd.StringInput(namedlg, "To: ")
                        pw.variable.undoAvailable = True
                        pw.variable.redoAvailable = True
                        pw.variable.setClearButtonEnabled(True)
                        pw.setText(newName)
                        namedlg.addWidget(pw)
                        
                        if namedlg.exec() == 0:
                            return
                        else:
                            name = pw.text()
                            if name in cursorNames and name != initialID:
                                self.errorMessage("Edit cursor", f"Cursors must have unique names; reverting to the original ('{initialID}')")
                                name = initialID
                            
                    cursor.ID = name
                    
                    if cursor.isVertical:
                        self._verticalSignalCursors_.pop(initialID)
                        self._verticalSignalCursors_[cursor.ID] = cursor
                        
                    elif cursor.isHorizontal:
                        self._horizontalSignalCursors_.pop(initialID)
                        self._horizontalSignalCursors_[cursor.ID] = cursor
                        
                    else:
                        self._crosshairSignalCursors_.pop(initialID)
                        self._crosshairSignalCursors_[cursor.ID] = cursor
                        
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
        
        return cursor.ID if cursor else None
    
    def getAxis_xDataPrecision(self, axis):
        #pdis = [i for i in axis.items if isinstance(i, pg.PlotDataItem)]
        pXData = (i.xData[~np.isnan(i.xData) & ~np.isinf(i.xData)] for i in axis.items if isinstance(i, pg.PlotDataItem) and sgp.nansize(i.xData) > 1)
        
        # precisions = [int(abs(np.round(np.log10((np.diff(x)).mean())))) for x in pXData]
        precisions = [int(abs(np.round(np.log10(np.nanmean(np.diff(x)))))) for x in pXData]
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
        if self._yData_ is None:
            return
        
        if self._xData_ is None:
            var_name = getattr(self._yData_, "name", None)
            if not isinstance(var_name, str) or len(var_name.strip()) == 0:
                var_name = "data"
            
            self.exportDataToWorkspace(self._yData_, var_name)
            
        else:
            data = (self._xData_, self._yData_)
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
                        
                        self._scipyenWindow_.assignToWorkspace(newVarName, values[0], check_name=False)
                        
                        
                else:
                    for name, value in zip(item_paths, values):
                        newVarName = validate_varname(name, self._scipyenWindow_.workspace)
                        self._scipyenWindow_.assignToWorkspace(newVarName, value, check_name=False)
        
        
    @pyqtSlot()
    @safeWrapper
    def slot_addVerticalCursor(self, label = None, follows_mouse=False):
        return self._addCursor_("vertical", axis=self._selected_plot_item_, 
                                  label=label, follows_mouse=follows_mouse,
                                  show_value=self.setCursorsShowValue.isChecked(),
                                  editFirst = self.editCursorUponCreation)
    
    @pyqtSlot()
    @safeWrapper
    def slot_addHorizontalCursor(self, label=None, follows_mouse=False):
        return self._addCursor_("horizontal", axis=self._selected_plot_item_, 
                                  label=label, follows_mouse=follows_mouse,
                                  show_value=self.setCursorsShowValue.isChecked(),
                                  editFirst = self.editCursorUponCreation)
        
    @pyqtSlot()
    @safeWrapper
    def slot_addCrosshairCursor(self, label=None, follows_mouse=False):
        return self._addCursor_("crosshair", axis=self._selected_plot_item_, 
                                  label=label, follows_mouse=follows_mouse,
                                  show_value=self.setCursorsShowValue.isChecked(),
                                  editFirst = self.editCursorUponCreation)
    
    @pyqtSlot()
    @safeWrapper
    def slot_export_svg(self):
        if self.viewerWidget.scene() is None:
            return
        
        self._export_to_graphics_file_("svg")
        
    @pyqtSlot()
    @safeWrapper
    def slot_export_tiff(self):
        if self.viewerWidget.scene() is None:
            return
        
        self._export_to_graphics_file_("tiff")
        
    @pyqtSlot()
    @safeWrapper
    def slot_export_png(self):
        if self.viewerWidget.scene() is None:
            return
        
        self._export_to_graphics_file_("png")
        
    @safeWrapper
    def _export_to_graphics_file_(self, file_format):
        import pyqtgraph.exporters
        
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
        
        if sys.platform == "win32":
            options = QtWidgets.QFileDialog.Option.DontUseNativeDialog
            kw = {"options":options}
        else:
            kw = {}

        if self._scipyenWindow_ is not None:
            targetDir = self._scipyenWindow_.currentDir
            
            fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self,
                                                                caption="Export figure as %s" % caption_suffix,
                                                                filter = file_filter,
                                                                directory = targetDir,
                                                                **kw)
            
        else:
            fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self,
                                                                caption="Export figure as %s" % caption_suffix,
                                                                filter = file_filter, **kw)
            
        if len(fileName) == 0:
            return
        
        itemsrect = self.viewerWidget.scene().itemsBoundingRect()
        w = int(np.ceil(itemsrect.width()))
        h = int(np.ceil(itemsrect.height()))

        if file_format.strip().lower() == "svg":
            exporter = pyqtgraph.exporters.SVGExporter(self.viewerWidget.scene())
            exporter.parameters()["width"] = w
            exporter.parameters()["height"] = h
            exporter.parameters()["background"] = pg.mkColor(pg.getConfigOption("background"))
            exporter.parameters()["scaling stroke"] = True
            exporter.export(fileName)
            
#             generator = QtSvg.QSvgGenerator()
#             generator.setFileName(fileName)
#             generator.setSize(QtCore.QSize(w,h))
#             generator.setViewBox(itemsrect)
#             generator.setResolution(300)
#             
#             font = QtGui.QGuiApplication.font()
#             
#             painter = QtGui.QPainter()
#             painter.begin(generator)
#             painter.setFont(font)
#             self.viewerWidget.scene().render(painter, itemsrect, itemsrect)
#             painter.end()
        
        else:
            imgformat = QtGui.QImage.Format_ARGB32

            out = QtGui.QImage(w,h,imgformat)
            
            out.fill(pg.mkColor(pg.getConfigOption("background")))
            
            painter = QtGui.QPainter(out)
            self.viewerWidget.scene().render(painter, itemsrect, itemsrect)
            painter.end()
            
            out.save(fileName, file_format.strip().lower(), 100)
    
    @pyqtSlot()
    @safeWrapper
    def slot_addDynamicCrosshairCursor(self, label=None):
        return self._addCursor_("crosshair", item=self._selected_plot_item_, 
                                  label=label, follows_mouse=True, 
                                  editFirst = self.editCursorUponCreation)
    
    @pyqtSlot()
    @safeWrapper
    def slot_addDynamicVerticalCursor(self, label=None):
        return self._addCursor_("vertical", item=self._selected_plot_item_, 
                                  label=label, follows_mouse=True,
                                  editFirst = self.editCursorUponCreation)
    
    @pyqtSlot()
    @safeWrapper
    def slot_addDynamicHorizontalCursor(self, label=None):
        return self._addCursor_("horizontal", item=self._selected_plot_item_, 
                                  label=label, follows_mouse=True,
                                  editFirst = self.editCursorUponCreation)
    
    def _construct_multi_axis_vertical_(self, label=None, dynamic=False,
                                        editFirst = False):
        # print(f"{self.__class__.__name__}._construct_multi_axis_vertical_ label = {label}, dynamic = {dynamic}")
        # NOTE: 2020-02-26 14:37:50
        # code being migrated to _addCursor_()
        # with allowing for cursors to be added to an empty scene (i.e. with no
        # axes) on the condition that their coordinates must be reset once
        # something has been plotted
        if self.signalsLayout.scene() is not None:
            # ax_cx = self.axesWithLayoutPositions
            pIs = self.plotItems
            
            # NOTE: 2023-01-14 23:23:06
            # always expect at least one PlotItem present
            if len(pIs) == 0: #
                scene_rect = self.signalsLayout.scene().sceneRect()
                xbounds = (scene_rect.x(), scene_rect.x() + scene_rect.width())
                precision=None
            else:
                # pIs, _ = zip(*ax_cx)
                
                min_x_axis = np.min([p.viewRange()[0][0] for p in pIs])
                max_x_axis = np.max([p.viewRange()[0][1] for p in pIs])
                
                min_point = pIs[0].vb.mapViewToScene(QtCore.QPointF(min_x_axis, 0))
                max_point = pIs[0].vb.mapViewToScene(QtCore.QPointF(max_x_axis, 0))
                
                xbounds = [min_point.x(), max_point.x()]

                pi_precisions = [self.getAxis_xDataPrecision(ax) for ax in self.plotItems]
                precision = min(pi_precisions)
                
            return self._addCursor_("vertical", axis=self.signalsLayout.scene(), 
                                    label=label, follows_mouse=dynamic, xBounds=xbounds,
                                    precision=precision,
                                    editFirst=editFirst)
        
    
    @pyqtSlot()
    @safeWrapper
    def slot_addMultiAxisVerticalCursor(self, label=None):
        askForParams = bool(
            QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier)
        self._construct_multi_axis_vertical_(label=label, editFirst=askForParams)
        
    @pyqtSlot()
    @safeWrapper
    def slot_addDynamicMultiAxisVerticalCursor(self, label=None):
        self._construct_multi_axis_vertical_(label=label, dynamic=True,
                                             editFirst = self.editCursorUponCreation)
        
    def _construct_multi_axis_crosshair_(self, label=None, dynamic=False,
                                         editFirst=False):
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
                                    xBounds = xbounds, yBounds = ybounds,
                                    editFirst = editFirst)
        
        
    @pyqtSlot()
    @safeWrapper
    def slot_addMultiAxisCrosshairCursor(self, label=None):
        self._construct_multi_axis_crosshair_(label=label, 
                                              editFirst = self.editCursorUponCreation)
        
    @pyqtSlot()
    @safeWrapper
    def slot_addDynamicMultiAxisCrosshairCursor(self, label=None):
        self._construct_multi_axis_crosshair_(label=label, dynamic=True,
                                              editFirst = self.editCursorUponCreation)
        
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
        self._crosshairSignalCursors_.clear()
        self._horizontalSignalCursors_.clear()
        self._verticalSignalCursors_.clear()
        
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
        
            cursorComboBox = qd.QuickDialogComboBox(d, "Select cursor:")
            cursorComboBox.setItems([c for c in self._data_cursors_])
            cursorComboBox.setValue(0)
            
            d.cursorComboBox = cursorComboBox
            
            if d.exec() == QtWidgets.QDialog.Accepted:
                crsID = d.cursorComboBox.text()
                
        if crsID not in self._data_cursors_:
            return
        
        crs = None
        
        if crsID in self._crosshairSignalCursors_:
            crs = self._crosshairSignalCursors_.pop(crsID, None)

        elif crsID in self._horizontalSignalCursors_:
            crs = self._horizontalSignalCursors_.pop(crsID, None)

        elif crsID in self._verticalSignalCursors_:
            crs = self._verticalSignalCursors_.pop(crsID, None) 
            
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
    def slot_cursorMenu(self, crsId):
        # TODO ?
        return
        # print(f"{self.__class__.__name__} ({self.windowTitle()}) slot_cursorMenu RMB click on {crsId}")
        
    @pyqtSlot()
    @safeWrapper
    def _slot_makeVerticalCursorsFromEpoch(self):
            if isinstance(self._yData_, neo.Block):
                segments = self._yData_.segments
                
            elif isinstance(self._yData_, (tuple, list)) and all(isinstance(s, neo.Segment) for s in self._yData_):
                segments = self._yData_
                
            elif isinstance(self._yData_, neo.Segment):
                segments = [self._yData_]
                
            elif isinstance(self._yData_, neo.core.basesignal.BaseSignal):
                if self._yData_.segment is None:
                    return
                
                segments = [self._yData_.segment]
                
            else:
                return
            
            if len(segments) == 0:
                return
            
            epochs = segments[self.currentFrame].epochs
            
            if len(epochs) == 0:
                return
            
            epoch_names = [e.name for e in epochs]
            seldlg = ItemsListDialog(self, itemsList = epoch_names,
                                     title="Select epoch",
                                     selectmode = QtWidgets.QAbstractItemView.SingleSelection)
            ans = seldlg.exec_()
            if ans != QtWidgets.QDialog.Accepted:
                return
            
            selItems = seldlg.selectedItemsText
            
            if len(selItems) == 0:
                return
            
            else:
                selItem = selItems[0]
                
            selEpoch = [e for e in epochs if e.name == selItem]
            
            if len(selEpoch) == 0:
                warnings.warn(f"There's no epoch named {selItem}")
                return
            
            selEpoch = selEpoch[0]
            
            cursors = epoch2cursors(selEpoch, axis=self.currentAxis,
                                    signal_viewer = self)
            
    @pyqtSlot()
    @safeWrapper
    def _slot_makeMultiAxisVerticalCursorsFromEpoch(self):
            if isinstance(self._yData_, neo.Block):
                segments = self._yData_.segments
                
            elif isinstance(self._yData_, (tuple, list)) and all(isinstance(s, neo.Segment) for s in self._yData_):
                segments = self._yData_
                
            elif isinstance(self._yData_, neo.Segment):
                segments = [self._yData_]
                
            elif isinstance(self._yData_, neo.core.basesignal.BaseSignal):
                if self._yData_.segment is None:
                    return
                
                segments = [self._yData_.segment]
                
            else:
                return
            
            if len(segments) == 0:
                return
            
            epochs = segments[self.currentFrame].epochs
            
            if len(epochs) == 0:
                return
            
            epoch_names = [e.name for e in epochs]
            seldlg = ItemsListDialog(self, itemsList = epoch_names,
                                     title="Select epoch",
                                     selectmode = QtWidgets.QAbstractItemView.SingleSelection)
            ans = seldlg.exec_()
            if ans != QtWidgets.QDialog.Accepted:
                return
            
            selItems = seldlg.selectedItemsText
            
            if len(selItems) == 0:
                return
            
            else:
                selItem = selItems[0]
                
            selEpoch = [e for e in epochs if e.name == selItem]
            
            if len(selEpoch) == 0:
                warnings.warn(f"There's no epoch named {selItem}")
                return
            
            selEpoch = selEpoch[0]
            
            cursors = epoch2cursors(selEpoch, axis=self.signalsLayout.scene(),
                                    signal_viewer = self)
            
    @pyqtSlot(str)
    @pyqtSlot(bool)
    @safeWrapper
    def slot_editCursor(self, crsId=None, choose=False):
        self._editCursor_(crsId, choose)
    
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
            
        c = self.signalCursor(cid)
            
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
#     
#     def testGlobalsFcn(self, workspace):
#         """workspace is a dict as returned by globals() 
#         """
#         exec("a=np.eye(3)", workspace)
        
        
    @pyqtSlot()
    @safeWrapper
    def slot_cursorsToEpoch(self):
        """Creates a neo.Epoch from existing cursors and exports it to the workspace.
        The epoch is NOT embedded in the plotted data.
        """
        scipyenWindow = self.scipyenWindow
        
        if scipyenWindow is None:
            return
            
        vertAndCrossCursors = collections.ChainMap(self._crosshairSignalCursors_, self._verticalSignalCursors_)
        
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
            
            cursors = [self.signalCursor(name) for name in selItems]
            
            if len(cursors) == 0:
                return
            
        
        else:
            cursors = [c for c in vertAndCrossCursors.values()]
            
        if hasattr(self._yData_, "name") and isinstance(self._yData_.name, str) and len(self._yData_.name.strip()):
            name = "%s_Epoch" % self._yData_.name
            
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
            scipyenWindow.assignToWorkspace(name, epoch)
            
        # if scipyenWindow is not None:
                
    @pyqtSlot()
    @safeWrapper
    def slot_cursorsToEpochInData(self):
        """Creates a neo.Epoch from current vertical/crosshair cursors.
        The Epoch is embedded in the plotted data.
        """
        vertAndCrossCursors = collections.ChainMap(self._crosshairSignalCursors_, self._verticalSignalCursors_)
        
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
            
            cursors = [self.signalCursor(name) for name in selItems]
            
#             print(cursors)
#             
            if len(cursors) == 0:
                return
            
            cursors.sort(key=attrgetter('x'))
            
            # else:
            #     cursors = [c for c in vertAndCrossCursors.values()]
                    
        if hasattr(self._yData_, "name") and isinstance(self._yData_.name, str) and len(self._yData_.name.strip()):
            name = "%s_Epoch" % self._yData_.name
            
        else:
            name ="Epoch"
        
        if isinstance(self._yData_, (neo.Block, neo.Segment)) or (isinstance(self._yData_, (tuple, list)) and all([isinstance(s, neo.Segment) for s in self._yData_])):
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
        vertAndCrossCursors = collections.ChainMap(self._crosshairSignalCursors_, self._verticalSignalCursors_)
        
        if len(vertAndCrossCursors) == 0:
            return
        
        if isinstance(self._yData_, (neo.Block, neo.Segment)) or (isinstance(self._yData_, (tuple, list)) and all([isinstance(s, neo.Segment) for s in self._yData_])):
            d = qd.QuickDialog(self, "Make Epoch From SignalCursor:")
            d.promptWidgets = list()
            d.namePrompt = qd.StringInput(d, "Name:")
            
            d.epoch_name = "Epoch"
            
            if hasattr(self._yData_, "name") and isinstance(self._yData_.name, str) and len(self._yData_.name.strip()):
                d.epoch_name = f"{self._yData_.name}_Epoch"
            
            if isinstance(self.selectedDataCursor, SignalCursor) and self.selectedDataCursor.cursorType in (SignalCursorTypes.vertical, SignalCursorTypes.crosshair):
                cursor = self.selectedDataCursor
                cursorNameField = None
                d.namePrompt.setText(f"{d.epoch_name} from {cursor.ID}")
                
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
                else:
                    name = d.epoch_name
                    
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
        vertAndCrossCursors = collections.ChainMap(self._crosshairSignalCursors_, self._verticalSignalCursors_)
        
        if len(vertAndCrossCursors) < 2:
            a = 2 - len(vertAndCrossCursors)
            QtWidgets.QMessageBox.warning(self,"Attach epoch to data",
                                          f"Please add {a} vertical or crosshair {InflectEngine.plural('cursor', a)} first")
            return
        
        if isinstance(self._yData_, (neo.Block, neo.Segment)):
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
                
                c1 = self.signalCursor(c1ID)
                c2 = self.signalCursor(c2ID)
                
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
            
        c = self.signalCursor(cid)
                
        if not isinstance(c, SignalCursor):
            return
        
        if c.cursorType not in (SignalCursorTypes.vertical, SignalCursorTypes.crosshair):
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
        scipyenWindow = self.scipyenWindow
        
        if scipyenWindow is None:
            return
            
        vertAndCrossCursors = collections.ChainMap(self._crosshairSignalCursors_, self._verticalSignalCursors_)
        
        if len(vertAndCrossCursors) == 0:
            return
        
        d = qd.QuickDialog(self, "Make Epoch From SignalCursor:")
        d.promptWidgets = list()
        d.namePrompt = qd.StringInput(d, "Name:")
        
        d.epoch_name = "Epoch"
        
        if hasattr(self._yData_, "name") and isinstance(self._yData_.name, str) and len(self._yData_.name.strip()):
            d.epoch_name = "%s_Epoch"
        
        if isinstance(self.selectedDataCursor, SignalCursor) and self.selectedDataCursor.cursorType in (SignalCursorTypes.vertical, SignalCursorTypes.crosshair):
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
                scipyenWindow.assignToWorkspace(name, epoch)
                
    
    @pyqtSlot()
    @safeWrapper
    def slot_epochBetweenCursors(self):
        scipyenWindow = self.scipyenWindow
        
        if scipyenWindow is None:
            return
            
        vertAndCrossCursors = collections.ChainMap(self._crosshairSignalCursors_, self._verticalSignalCursors_)
        
        if len(vertAndCrossCursors) < 2:
            a = 2 - len(vertAndCrossCursors)
            QtWidgets.QMessageBox.warning(self,"Attach epoch to data",
                                          f"Please add {a} vertical or crosshair {InflectEngine.plural('cursor', a)} first")
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
        c2Combo.setValue(1)
        
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
            
            c1 = self.signalCursor(c1ID)
            c2 = self.signalCursor(c2ID)
            
            if c1 is None or c2 is None:
                return
            
            epoch = self.epochBetweenCursors(c1, c2, name)
            
            if epoch is not None:
                name=epoch.name
                if name is None:
                    name = "epoch"
                    
                scipyenWindow.assignToWorkspace(name, epoch)
        
    @safeWrapper
    def cursorsToEpoch(self, *cursors, name:typing.Optional[str] = None, 
                       embed:bool = False, 
                       all_segments:bool = True, 
                       relative_to_segment_start:bool=False, 
                       overwrite:bool = False):
        """Creates a neo.Epoch from a list of vertical cursors.
        
        Each cursor contributes to one epoch interval with duration equal to the 
        cursor's xwindow, and time equal to cursor's x - xindow/2
        
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
            cursors = [c for c in collections.ChainMap(self._crosshairSignalCursors_, self._verticalSignalCursors_).values()]
        
            if len(cursors) == 0:
                raise ValueError("This functions requires at least one vertical or crosshair cursor to be defined")
            
            cursors.sort(key=attrgetter('x')) # or key = lambda x: x.x
                
        else:
            if any([c.cursorType not in (SignalCursorTypes.vertical, SignalCursorTypes.crosshair) for c in cursors]):
                raise ValueError("Expecting only vertical or crosshair cursors")
            
        
                
        if name is None or (isinstance(name, str) and len(name.strip())) == 0:
            if hasattr(self._yData_, "name") and isinstance(self._yData_.name, str) and len(self._yData_.name.strip()):
                name = "%_Epoch" % self._yData_.name
                
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
            if isinstance(self._yData_, neo.Block):
                segments = self._yData_.segments
                
            elif isinstance(self._yData_, (tuple, list)) and all(isinstance(s, neo.Segment) for s in self._yData_):
                segments = self._yData_
                
            elif isinstance(self._yData_, neo.Segment):
                segments = [self._yData_]
                
            elif isinstance(self._yData_, neo.core.basesignal.BaseSignal):
                if self._yData_.segment is None:
                    return
                
                segments = [self._yData_.segment]
                
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
                    intervals = [Interval(s_start + rel_starts[i], cursors[i].xwindow*s_start.units, cursors[i].name, True) for i in range(len(cursors))]
                    seg_epoch = intervals2epoch(*intervals, name=name)
                    epochs.append(seg_epoch)
                    if embed:
                        if overwrite:
                            seg.epochs = [seg_epoch]
                        else:
                            seg.epochs.append(seg_epoch)
                            
                self.displayFrame()
                
                return epochs
                
        if isinstance(self._yData_, neo.Block):
            t_units = self._yData_.segments[self.frameIndex[self._current_frame_index_]].t_start.units
            
        elif isinstance(self._yData_, (tuple, list)) and all(isinstance(s, neo.Segment) for s in self._yData_):
            t_units = self._yData_[self.frameIndex[self._current_frame_index_]].t_start.units
            
        elif isinstance(self._yData_, neo.Segment):
            t_units = self._yData_.t_start.units
            
        elif isinstance(self._yData_, neo.core.basesignal.BaseSignal):
            if self._yData_.segment is None:
                
                return
            t_units = self._yData_.times[0].units
            
        else:
            t_units = pq.s # reasonable default (although not necessarily always applicable !!!)
        
        # returns a neo.Epoch or a DataZone depending on the _yData_ units
        epoch = cursors2epoch(*cursors, name=name, sort=True, units = t_units,
                              durations=True)
        
        if embed:
            if isinstance(self._yData_, neo.Block):
                if len(self._yData_.segments) == 0:
                    warnings.warn("Plotted data is a neo.Block without segments")
                    #return epoch
                
                elif len(self._yData_.segments) == 1:
                    if overwrite:
                        self._yData_.segments[0].epochs = [epoch]
                    else:
                        self._yData_.segments[0].epochs.append(epoch)
                    
                else:
                    if all_segments:
                        for ndx in self.frameIndex:
                            if overwrite:
                                self._yData_.segments[ndx].epochs = [epoch]
                                
                            else:
                                self._yData_.segments[ndx].epochs.append(epoch)
                            
                    else:
                        if overwrite:
                            self._yData_.segments[self.frameIndex[self._current_frame_index_]].epochs = [epoch]
                        else:
                            self._yData_.segments[self.frameIndex[self._current_frame_index_]].epochs.append(epoch)
                            
            elif isinstance(self._yData_, (tuple, list)) and all([isinstance(s, neo.Segment) for s in self._yData_]):
                if len(self._yData_) == 0:
                    warnings.warn("Plotted data is an empty sequence!")
                
                elif len(self._yData_) == 1:
                    if overwrite:
                        self._yData_[0].epochs = [epoch]
                    else:
                        self._yData_[0].epochs.append(epoch)
                    
                else:
                    if all_segments:
                        for ndx in self.frameIndex:
                            if overwrite:
                                self._yData_[ndx].epochs = [epoch]
                                
                            else:
                                self._yData_[ndx].epochs.append(epoch)
                            
                    else:
                        if overwrite:
                            self._yData_[self.rameIndex[self._current_frame_index_]].epochs = [epoch]
                        else:
                            self._yData_[self.rameIndex[self._current_frame_index_]].epochs.append(epoch)
                            
            elif isinstance(self._yData_, neo.Segment):
                if overwrite:
                    self._yData_.epochs = [epoch]
                    
                else:
                    self._yData_.epochs.append(epoch)
                    
            elif isinstance(self._yData_, neo.core.basesignal.BaseSignal):
                if hasattr(self._yData_, "segment") and isinstance(self._yData_.segment, neo.Segment):
                    if overwrite:
                        self._yData_.segment.epochs = [epoch]
                    else:
                        self._yData_.segment.epocha.append(epoch)
                        
            else:
                warnings.warn("Epochs can only be embeded in neo.Segment objects (either stand-alone, collected in a tuple or list, or inside a neo.Block)")
                
            self.displayFrame()
                
        return epoch
    
#     def cursorToEpoch(self, crs=None, name=None):
#         """Creates a neo.Epoch from a single cursor
#         DEPRECATED superceded by the new cursorsToEpoch
#         """
#         if crs is None:
#             return
#         
#         if crs.isHorizontal:
#             return
#         
#         if name is None:
#             d = qd.QuickDialog(self, "Make Epoch From SignalCursor:")
#             d.promptWidgets = list()
#             d.promptWidgets.append(qd.StringInput(d, "Name:"))
#             #d.promptWidgets.append(vigra.pyqt.qd.StringInput(d, "Name:"))
#             d.promptWidgets[0].setText("Epoch from "+crs.ID)
#             
#             if d.exec() == QtWidgets.QDialog.Accepted:
#                 txt = d.promptWidgets[0].text()
#                 if txt is not None and len(txt)>0:
#                     name=txt
#                     
#             else:
#                 return
#             
#         return cursors2epoch(crs, name=name)
        
    def epochBetweenCursors(self, c0:typing.Union[SignalCursor, str], c1:typing.Union[SignalCursor, str], name:typing.Optional[str]=None, label:typing.Optional[str]=None, embed:bool = False, all_segments:bool = True, relative_to_segment_start:bool=False, overwrite:bool = False):
        """ Creates a neo.Epoch between two vertical cursors.
        The Epoch contains a single interval starting at the location of the
        first cursor, and with duration determined by the location of the second 
        cursors (the cursors are sorted in ascending order of their X axis location)
        
        Parameters:
        ==========
        c0, c1: SignalCursor objects or cursir IDs (str)
        
        name: name of the resulting Epoch
        
        label: interval's label
        
        embed: When True, the created Epoch will be appended to the frame's data
                (only when this data is a neo.Segment)
        
        all_segments: When True, creates epochs for all data segments (frames)
        
        relative_to_segment_start: When True, the epoch interval will have 
            coordinates set relative to the start of the data segment.
        
            When `all_segments` is True, and the data segments have different
            domain origin (e.g. t_start) this parameter should also be set to 
            True, otherwise the Epoch interval may fall outside the segment's
            domain.
        
            Default is False.
        
        
        Returns: 
        ========
        A neo.Epoch with one interval.
        
        To copy this Epoch to other segments manually (with adjusted interval
        coordinates if necessary) just create new Epochs manually.
        
        """
        
        if c0.isHorizontal or c1.isHorizontal:
            return
        
        cursors = sorted([c0, c1], key=attrgetter('x'))
        
        if not isinstance(name, str) or len(name.strip()) == 0:
            if hasattr(self._yData_, "name") and isinstance(self._yData_.name, str) and len(self._yData_.name.strip()):
                name = f"{self._yData_.name}_Epoch"
            else:
                name = "Epoch"
                
        if all_segments and relative_to_segment_start:
            if isinstance(self._yData_, neo.Block):
                segments = self._yData_.segments
            elif isinstance(self._yData_, (tuple, list)) and all(isinstance(s, neo.Segment) for s in self._yData_):
                segments = self._yData_
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
        if isinstance(self._yData_, neo.Block):
            t_units = self._yData_.segments[self.frameIndex[self._current_frame_index_]].t_start.units
        elif isinstance(self._yData_, (tuple, list)) and all(isinstance(s, neo.Segment) for s in self._yData_):
            t_units = self._yData_[self.frameIndex[self._current_frame_index_]].t_start.units
        elif isinstance(self._yData_, neo.Segment):
            t_units = self._yData_.t_start.units
        elif isinstance(self._yData_, neo.core.basesignal.BaseSignal):
            if self._yData_.segment is None:
                return
            t_units = self._yData_.times[0].units
        else:
            t_units = pq.s # reasonable default (although not necessarily always applicable !!!)
            
        if scq.check_time_units(t_units):
            factory = neo.Epoch
        else:
            factory = DataZone
        
        epoch = factory(times = np.array([cursors[0].x]), durations = np.array([cursors[1].x - cursors[0].x]),
                          units = t_units, labels = np.array([f"From {cursors[0].name} to {cursors[1].name}"]),
                          name = name)
        
        if embed:
            if isinstance(self._yData_, neo.Block):
                if len(self._yData_.segments) == 0:
                    warnings.warn("Plotted data is a neo.Block without segments")
                    #return epoch
                
                elif len(self._yData_.segments) == 1:
                    if overwrite:
                        self._yData_.segments[0].epochs = [epoch]
                    else:
                        self._yData_.segments[0].epochs.append(epoch)
                    
                else:
                    if all_segments:
                        for ndx in self.frameIndex:
                            if overwrite:
                                self._yData_.segments[ndx].epochs = [epoch]
                                
                            else:
                                self._yData_.segments[ndx].epochs.append(epoch)
                            
                    else:
                        if overwrite:
                            self._yData_.segments[self.frameIndex[self._current_frame_index_]].epochs = [epoch]
                        else:
                            self._yData_.segments[self.frameIndex[self._current_frame_index_]].epochs.append(epoch)
                            
            elif isinstance(self._yData_, (tuple, list)) and all([isinstance(s, neo.Segment) for s in self._yData_]):
                if len(self._yData_) == 0:
                    warnings.warn("Plotted data is an empty sequence!")
                
                elif len(self._yData_) == 1:
                    if overwrite:
                        self._yData_[0].epochs = [epoch]
                    else:
                        self._yData_[0].epochs.append(epoch)
                    
                else:
                    if all_segments:
                        for ndx in self.frameIndex:
                            if overwrite:
                                self._yData_[ndx].epochs = [epoch]
                                
                            else:
                                self._yData_[ndx].epochs.append(epoch)
                            
                    else:
                        if overwrite:
                            self._yData_[self.rameIndex[self._current_frame_index_]].epochs = [epoch]
                        else:
                            self._yData_[self.rameIndex[self._current_frame_index_]].epochs.append(epoch)
                            
            elif isinstance(self._yData_, neo.Segment):
                if overwrite:
                    self._yData_.epochs = [epoch]
                    
                else:
                    self._yData_.epochs.append(epoch)
                    
            elif isinstance(self._yData_, neo.core.basesignal.BaseSignal):
                if hasattr(self._yData_, "segment") and isinstance(self._yData_.segment, neo.Segment):
                    if overwrite:
                        self._yData_.segment.epochs = [epoch]
                    else:
                        self._yData_.segment.epocha.append(epoch)
                        
            else:
                warnings.warn("Epochs can only be embeded in neo.Segment objects (either stand-alone, collected in a tuple or list, or inside a neo.Block)")
                
            self.displayFrame()
                
        return epoch
    
    def setPlotStyle(self, val):
        if val is None:
            self.plotStyle = "plot"
        elif isinstance(val, str):
            self.plotStyle = val
        else:
            raise ValueError("Plot style must be a string with a valid matplotlib drawing function")
            
        self.displayFrame()
        
    @safeWrapper
    def setAxisTickFont(self, value: (QtGui.QFont, type(None)) = None):
        for item in self.plotItems:
            for ax_dict in item.axes.values():
                ax_dict["item"].setStyle(tickFont=value)
                
    @safeWrapper
    def _parse_data_(self, x, y, frameIndex, frameAxis, 
                     signalChannelAxis, signalIndex, signalChannelIndex, 
                     irregularSignalIndex, irregularSignalChannelAxis, irregularSignalChannelIndex, 
                     separateSignalChannels, separateChannelsIn, singleFrame) -> typing.Tuple[bool, typing.Any, typing.Any, int]:
        """Sets up the data model.
        Interprets the data passed in 'x' and 'y' structure and sets up internal
        (state) variables to enable plotting of different types of objects.
        
        These objects can be:
        
        1) numpy arrays and specialized objects derived from
        numpy arrays such as quantities, neo signals (which are derived from 
        quantities), vigra arrays, but also vigra kernels, and python sequences 
        of numbers.
        
        2) containers of (1) (at the moment only containers from 
        neo library are supported, e.g.Block and Segment)
        
        TODO: Pandas dataframes and series
        
        
        """
        
        # NOTE: 2023-06-02 12:45:48
        # also return n_signal_axes instead of setting it up directly
        # so that n_signal_axes can be monitored
        
        # see NOTE: 2023-01-01 15:29:48 - Radical API change

        # default param values
        
        # by default, all signal channels are plotted on the same axis
        # when below is True, then plot each channel on a separate axis
        self.separateSignalChannels = False 
        
        if separateChannelsIn in ("axes", "frames"):
            self.separateChannelsIn = separateChannelsIn
        else:
            self.separateChannelsIn = "axes"
        
        # by default, all signals are column vectors (i.e. defined along dimension or axis 0)
        self.signalChannelAxis = 1 
        self.dataAxis = 0 # data as column vectors
        
        self.singleFrame = False
        
        self._cached_title = ""
            
        if isinstance(y, neo.baseneo.BaseNeo):
            self.globalAnnotations = {type(y).__name__ : y.annotations}
        
        if isinstance(y, neo.core.Block):
            x = None
            self._cached_title = getattr(y, "name", None)
            
            # NOTE : 2022-01-17 14:17:23
            # if frameIndex was passed, then self._number_of_frames_ might turn
            # out to be different than self._data_frames_!
            self._data_frames_ = self._number_of_frames_ = len(y.segments)
            
            #### BEGIN NOTE 2019-11-24 22:32:46: 
            # no need for these so reset to None
            # but definitely used when y is a signal, not a container of signals!
            self.dataAxis = 0 # data as column vectors
            self.signalChannelAxis = 1 
            self.irregularSignalChannelAxis = 1
            
            # not needed: every segment is a "frame"
            self.frameAxis = None
            
            # not needed: all signal channels plotted in the same signal axis
            self.signalChannelIndex = None
            self.irregularSignalChannelIndex = None
            
            # NOTE: set to None on purpose for Block
            self.separateSignalChannels = False
            #### END NOTE 2019-11-24 22:32:46: 

            #### BEGIN NOTE: 2019-11-22 08:37:38 
            # the following need checking inside _plotSegment_()
            # to adapting for the particular segment
            # NOTE: 2023-01-01 15:59:00 on their way out, see NOTE: 2023-01-01 15:29:48
            self.signalIndex  = signalIndex
            self.irregularSignalIndex  = irregularSignalIndex
            #### END NOTE: 2019-11-22 08:37:38 
            
            # NOTE: this is used when self._yData_ is a structured signal object,
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
            
            _n_signal_axes_ = 0 if len(y.segments) == 0 else max(len(s.analogsignals) + len(s.irregularlysampledsignals) for s in y.segments)
            # self._n_signal_axes_ = 0 if len(y.segments) == 0 else max(len(s.analogsignals) + len(s.irregularlysampledsignals) for s in y.segments)
            
            self._meta_index = np.recarray((self._number_of_frames_, 1),
                                           dtype = [('block', int), ('segment', int)])
            
            self._meta_index.block[:,0] = 0
            self._meta_index.segment[:,0] = self.frameIndex
            
            #### BEGIN NOTE: 2019-11-21 23:09:52 
            # TODO/FIXME handle self.plot_start and self.plot_start
            # each segment (sweep, or frame) can have a different time domain
            # so when these two are specified it may result in an empty plot!!!
            #### END NOTE: 2019-11-21 23:09:52 

        elif isinstance(y, neo.core.Segment):
            # a segment is ALWAYS plotted in a single frame, with all signals in 
            # their own axes (i.e. PlotItem objects)
            
            x = None
            self._cached_title = getattr(y, "name", None)
            
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
            
            _n_signal_axes_ = len(y.analogsignals) + len(y.irregularlysampledsignals)
            # self._n_signal_axes_ = len(y.analogsignals) + len(y.irregularlysampledsignals)
            
            self._meta_index = np.recarray((self._number_of_frames_,1),
                                           dtype=[("frame", int)])
            
            self._meta_index.frame[:,0] = self.frameIndex
            
        elif isinstance(y, (neo.core.AnalogSignal, DataSignal)):
            x = None
            self._cached_title = getattr(y, "name", None)
            
            # NOTE: no need for these as there is only one signal
            self.signalIndex = None
            self.irregularSignalIndex = None
            self.irregularSignalChannelIndex = None
            
            # treat these as a 2D numpy array, but with the following conditions:
            # • signalChannelAxis is always 1
            # • frameAxis is None, or 1: the data itself has only one logical "frame"
            #   ∘ frameAxis == None:
            #       □ self.separateSignalChannels == True:
            #           ⋆ self.separateChannelsIn == "axes" → plot each channel in its own axis, use a single frame for all channels
            #           ⋆ self.separateChannelsIn != "axes" → plot each channel in its own frame, one axis per frame
            #       □ self.separateSignalChannels == False → plot all channels in a single frame, single axis
            #   ∘ frameAxis == 1:
            #   
            # • signal domain is already present, although it can be overridden
            #   by user-supplied "x" data
            
            self.dataAxis = 0 # data as column vectors
            
            if not isinstance(frameAxis, (int, type(None))):
                raise TypeError("For AnalogSignal and DataSignal, frameAxis must be an int or None; got %s instead" % type(frameAxis).__name__)

            self.signalChannelAxis = 1
            self.signalChannelIndex = normalized_sample_index(y.as_array(), self.signalChannelAxis, signalChannelIndex)
            
            self._data_frames_ = 1
            
            if frameAxis is None:
                # all signal's channels plotted on the same frame, or on separate
                # frames IF self.separateSignalChannels is True
                self.frameAxis = None
                self._number_of_frames_ = 1

                self.separateSignalChannels = separateSignalChannels
                
                if self.separateSignalChannels:
                    # each channel to be plotted separately; this can be
                    # a) separate axes in the same frame
                    # b) single axis, in separate frames
                    if self.separateChannelsIn == "axes":
                        # separate axes, same frame (one frame) (case 'a')
                        self._number_of_frames_ = 1
                        self.frameIndex = range(self._number_of_frames_)
                        _n_signal_axes_ = y.shape[self.signalChannelAxis]
                        # self._n_signal_axes_ = y.shape[self.signalChannelAxis]
                        
                        self._meta_index = np.recarray((self._number_of_frames_,1), dtype=[('frame', int)])
                        self._meta_index.frame[:,0] = self.frameIndex
                        
                    else:
                        # separate frames, one axis per frame (case 'b')
                        self._number_of_frames_ = y.shape[1]
                        self.frameIndex = range(self._number_of_frames_)
                        _n_signal_axes_ = 1
                        # self._n_signal_axes_ = 1
                        
                        self._meta_index = np.recarray((self._number_of_frames_,1), dtype=[('frame', int)])
                        self._meta_index.frame[:,0] = self.frameIndex
                        
                        
                else:
                    # all channels in one axis, single frame
                    _n_signal_axes_ = 1  
                    # self._n_signal_axes_ = 1  
                    self._number_of_frames_ = 1
                    self.frameIndex = range(self._number_of_frames_)
                    
                    self._meta_index = np.recarray((self._number_of_frames_,1), dtype=[('frame', int)])
                    self._meta_index.frame[:,0] = self.frameIndex
                
            else:
                # frameAxis can only be '1' here
                # this forces plotting one signal channel per axis, one axis 
                # per frame
                # ⇒ implies separate signal channels is True
                frameAxis = normalized_axis_index(y.as_array(), frameAxis)
                
                if frameAxis != self.signalChannelAxis:
                    raise ValueError("For structured signals, frame axis and signal channel axis must be identical")
                
                self.frameAxis = frameAxis
                self.frameIndex = normalized_sample_index(y.as_array(), self.frameAxis, frameIndex)
                self._number_of_frames_ = len(self.frameIndex)
                
                self.separateSignalChannels = False
                _n_signal_axes_ = 1
                # self._n_signal_axes_ = 1
                
                self._meta_index = np.recarray((self._number_of_frames_,1), dtype=[('frame', int)])
                self._meta_index.frame[:,0] = self.frameIndex
                
        elif isinstance(y, (neo.core.IrregularlySampledSignal,  IrregularlySampledDataSignal)):
            x = None
            self._cached_title = getattr(y, "name", None)
            self.dataAxis = 0 # data as column vectors
            self.signalChannelAxis = 1
            
            self._number_of_frames_ = 1
            self._data_frames_ = 1
            
            self.signalIndex = None
            self.irregularSignalIndex  = None
            self.signalChannelIndex    = None
            
            self.irregularSignalChannelIndex    = irregularSignalChannelIndex
            
            if frameAxis is None:
                self.frameAxis = None
                self.separateSignalChannels  = separateSignalChannels
                
                if self.separateSignalChannels:
                    if self.separateChannelsIn == "axes":
                        self._number_of_frames_ = 1
                        self.frameIndex = range(self._number_of_frames_)
                        _n_signal_axes_ = y.shape[self.signalChannelAxis]
                        # self._n_signal_axes_ = y.shape[self.signalChannelAxis]
                        self._meta_index = np.recarray((self._number_of_frames_,1), dtype=[('frame', int)])
                        self._meta_index.frame[:,0] = self.frameIndex
                        
                        
                    else:
                        self._number_of_frames_ = y.shape[1]
                        self.frameIndex = range(self._number_of_frames_)
                        _n_signal_axes_ = 1
                        # self._n_signal_axes_ = 1
                        self._meta_index = np.recarray((self._number_of_frames_,1), dtype=[('frame', int)])
                        self._meta_index.frame[:,0] = self.frameIndex
                        
                else:
                    self._number_of_frames_ = 1
                    self.frameIndex = range(self._number_of_frames_)
                    _n_signal_axes_ = 1
                    # self._n_signal_axes_ = 1
                    self._meta_index = np.recarray((self._number_of_frames_,1), dtype=[('frame', int)])
                    self._meta_index.frame[:,0] = self.frameIndex
                    
                
            else:
                # ⇒ implies separate signal channels is True
                frameAxis = normalized_axis_index(y.as_array(), frameAxis)
                if frameAxis != self.signalChannelAxis:
                    raise ValueError("For structured signals, frame axis and signal channel axis must be identical")
                
                self.frameAxis = frameAxis
                self.frameIndex = normalized_sample_index(y.as_array(), self.frameAxis, frameIndex)
                self._number_of_frames_ = len(self.frameIndex)
                self.separateSignalChannels  = False
                _n_signal_axes_ = 1
                # self._n_signal_axes_ = 1
                self._meta_index = np.recarray((self._number_of_frames_,1), dtype=[('frame', int)])
                self._meta_index.frame[:,0] = self.frameIndex
                
        elif isinstance(y, (neo.core.SpikeTrain, neo.core.spiketrainlist.SpikeTrainList)): # plot a SpikeTrain independently of data
            # NOTE: 2023-01-01 18:17:26
            # use a single spike_train_axis
            _n_signal_axes_ = 0
            # self._n_signal_axes_ = 0
            x = None
            self._cached_title = getattr(y, "name", None)
            self.dataAxis = 0 # data as column vectors
            self.signalChannelAxis = 1
            self._number_of_frames_ = 1
            self.frameIndex = range(self._number_of_frames_)
            self._meta_index = np.recarray((self._number_of_frames_,1), dtype=[('frame', int)])
            self._meta_index.frame[:,0] = self.frameIndex
                        
        elif isinstance(y, (neo.core.Event, DataMark, TriggerEvent)): # plot an event independently of data
            x = None
            self._cached_title = getattr(y, "name", None)
            self.dataAxis = 0 # data as column vectors
            self.signalChannelAxis = 1
            self._number_of_frames_ = 1
            self.frameIndex = range(self._number_of_frames_)
            _n_signal_axes_ = 0
            # self._n_signal_axes_ = 0
            self._meta_index = np.recarray((self._number_of_frames_,1), dtype=[('frame', int)])
            self._meta_index.frame[:,0] = self.frameIndex
        
        elif isinstance(y, (neo.core.Epoch, DataZone)): # plot an Epoch independently of data
            x = None
            self._cached_title = getattr(y, "name", None)
            self.dataAxis = 0 # data as column vectors
            self.signalChannelAxis = 1
            self._number_of_frames_ = 1
            self.frameIndex = range(self._number_of_frames_)
            _n_signal_axes_ = 0
            # self._n_signal_axes_ = 0
            self._meta_index = np.recarray((self._number_of_frames_,1), dtype=[('frame', int)])
            self._meta_index.frame[:,0] = self.frameIndex
            
            if self._docTitle_ is None or (isinstance(self._docTitle_, str) and len(self._docTitle_.strip()) == 0):
                # because these may be plotted as an add-on so we don't want to mess up the title
                if isinstance(y.name, str) and len(y.name.strip()) > 0:
                    self._doctTitle_ = y.name
                    
                else:
                    self._docTitle_ = y.__class__.__name__
        
        elif isinstance(y, vigra.filters.Kernel1D):
            x, y = kernel2array(y)
            self._cached_title = "Vigra Kernel 1D"
            
            self.dataAxis = 0 # data as column vectors
            self.frameAxis = None
            self._number_of_frames_ = 1
            self.frameIndex = range(self._number_of_frames_)
            self.signalIndex = range(1)
            _n_signal_axes_ = 1
            # self._n_signal_axes_ = 1
            self._meta_index = np.recarray((self._number_of_frames_,1), dtype=[('frame', int)])
            self._meta_index.frame[:,0] = self.frameIndex
            
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
            # NOTE: 2023-01-18 09:59:55 About the "X" domain for arrays
            # to keep things simple we only support a vector "X" domain, to be 
            # the same for all channels in the array (for arrays with 2 or 3
            # dimensions) - things may change in the future
            # 
            if not issubclass(y.dtype.type, np.number):
                self.criticalMessage(f"Set data ({y.__class__.__name__})", f"Cannot plot arrays with dtype {y.dtype.type.__name__}")
                return False, None, None, 0
            
            if y.ndim > 3: 
                self.criticalMessage(f"Set data ({y.__class__.__name__})", f"Cannot plot data with {y.ndim} dimensions")
                return False, None, None, 0
            
            if y.ndim < 1:
                self.criticalMessage(f"Set data ({y.__class__.__name__})", "Cannot plot a scalar")
                return False, None, None, 0
            
            # self._xData_ = None
            # self._yData_ = y
            self._cached_title = "Numpy array"
            
            if y.ndim == 1: # one frame, one channel
                self.dataAxis = 0 # data as column vectors; there is only one axis
                self.signalChannelAxis = None
                self.frameAxis = None
                self._number_of_frames_ = 1
                self.frameIndex = range(self._number_of_frames_)
                self.signalChannelIndex = range(1)
                self.separateSignalChannels = False
                _n_signal_axes_ = 1
                # self._n_signal_axes_ = 1
                
                self._meta_index = np.recarray((self._number_of_frames_,1), dtype=[('frame', int)])
                self._meta_index.frame[:,0] = self.frameIndex
                
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
                        signalChannelAxis = 1 # by default we consider channels as column vectors
                        
                else:
                    if isinstance(y, vigra.VigraArray):
                        if isinstance(signalChannelAxis, str) and signalChannelAxis.lower().strip() != "c":
                                warnings.warn("Channel axis index is specificed by non-canonical axis key %s" % signalChannelAxis)
                                
                        elif isinstance(signalChannelAxis, vigra.AxisInfo):
                            if signalChannelAxis.key.lower().strip() != "c":
                                warnings.warn("Channel axis index is specificed by non-canonical axis key %s" % signalChannelAxis)
                                
                    signalChannelAxis = normalized_axis_index(y, signalChannelAxis)
                    
                self.signalChannelAxis = signalChannelAxis
                
                self.dataAxis = 1 if self.signalChannelAxis == 0 else 0
                
                self.signalChannelIndex = normalized_sample_index(y, self.signalChannelAxis, signalChannelIndex)
                
                self.separateSignalChannels = separateSignalChannels
                
                if frameAxis is None:
                    if self.separateSignalChannels:
                        if y.shape[self.signalChannelAxis] > 10:
                            self.frameAxis = self.signalChannelAxis
                            self._data_frames_ = y.shape[self.frameAxis]
                            self._number_of_frames_ = y.shape[self.frameAxis]
                            self.frameIndex = range(self._number_of_frames_)
                            _n_signal_axes_ = 1
                            # self._n_signal_axes_ = 1
                            self._meta_index = np.recarray((self._number_of_frames_,1), dtype=[('frame', int)])
                            self._meta_index.frame[:,0] = self.frameIndex
                        else:
                            self.frameAxis = None
                            self._data_frames_ = 1
                            self._number_of_frames_ = 1
                            _n_signal_axes_ = y.shape[self.signalChannelAxis]
                            # self._n_signal_axes_ = y.shape[self.signalChannelAxis]
                            
                        
                        self.frameIndex = range(self._number_of_frames_)
                        self._meta_index = np.recarray((self._number_of_frames_,1), dtype=[('frame', int)])
                        self._meta_index.frame[:,0] = self.frameIndex
                        
                    else:
                        self.frameAxis = None
                        self._data_frames_ = 1
                        self._number_of_frames_ = 1
                        _n_signal_axes_ = 1
                        # self._n_signal_axes_ = 1
                            
                        self.frameIndex = range(self._number_of_frames_)
                        
                        self._meta_index = np.recarray((self._number_of_frames_,1), dtype=[('frame', int)])
                        self._meta_index.frame[:,0] = self.frameIndex
                    
                    
                else:
                    # for 2D arrays, specifying a frameAxis forces the plotting 
                    # of one channel per frame
                    frameAxis = normalized_axis_index(y, frameAxis)
                    
                    # NOTE: 2019-11-22 14:24:16
                    # for a 2D array it does not make sense to have frameAxis
                    # different from signalChannelAxis
                    if frameAxis != self.signalChannelAxis:
                        self.criticalMessage(f"Set data ({y.__class__.__name__})", "For 2D arrays, frame axis index %d must be the same as the channel axis index (%d)" % (frameAxis, self.signalChannelAxis))
                        return False, None, None, 0
                    
                    self.frameAxis = frameAxis
                    
                    self.frameIndex = normalized_sample_index(y, self.frameAxis, frameIndex)
                    
                    self._number_of_frames_ = len(self.frameIndex)
                    
                    _n_signal_axes_ = 1 
                    # self._n_signal_axes_ = 1 
                    
                    self._meta_index = np.recarray((self._number_of_frames_,1), dtype=[('frame', int)])
                    self._meta_index.frame[:,0] = self.frameIndex
                
            elif y.ndim == 3: 
                # NOTE: 2019-11-22 13:33:27
                # both frameAxis and signalChannelAxis SHOULD be specified
                #
                # for 3D arrays there will be several frames, each frame with
                # • one axis if separateSignalChannels is False
                # • several axes if SeparateSignalChannels is True
                #
                # NOTE: 2022-12-13 22:22:16
                # below, we assume the following
                #   0         1        2
                # frame   → channel → data
                # data    → frame   → channel
                # channel → data    → frame
                if isinstance(signalChannelAxis, int) and signalChannelAxis not in range(-1*(y.ndim), y.ndim):
                    self.criticalMessage(f"Set data ({y.__class__.__name__})", f"signalChannelAxis {signalChannelAxis} out of range for array with {y.ndim} dimensions")
                    return False, None, None, 0
                
                if isinstance(frameAxis, int) and frameAxis not in range(-1*(y.ndim), y.ndim):
                    self.criticalMessage(f"Set data ({y.__class__.__name__})", f"frameAxis {frameAxis} out of range for array with {y.ndim} dimensions")
                    return False, None, None, 0
                
                if signalChannelAxis is None:
                    if frameAxis is None:
                        # data on highest dim
                        frameAxis = 0
                        signalChannelAxis = 1
                        
                    elif frameAxis == 0:
                        # as above
                        signalChannelAxis = 1
                        
                    elif frameAxis == 1:
                        # data on lowest dim
                        signalChannelAxis = 2
                        
                    else:
                        # data on 2nd dim
                        signalChannelAxis = 0
                        
                elif frameAxis is None:
                    if signalChannelAxis == 0:
                        frameAxis = 2
                        
                    elif signalChannelAxis == 1:
                        frameAxis = 0
                        
                    elif signalChannelAxis == 2:
                        frameAxis = 1
                        
                elif frameAxis == signalChannelAxis:
                    self.criticalMessage(f"Set data ({y.__class__.__name__})", f"frameAxis and signalChannelAxis cannot have the same index {frameAxis}")
                    return False, None, None, 0
                    # raise TypeError("For 3D arrays the frame axis must be specified")
                
                
                frameAxis = normalized_axis_index(y, frameAxis)
                
                signalChannelAxis = normalized_axis_index(y, signalChannelAxis)
                
                if frameAxis  ==  signalChannelAxis:
                    self.criticalMessage(f"Set data ({y.__class__.__name__})", "For 3D arrays the index of the frame axis must be different from the index of the signal channel axis")
                
                self.frameAxis = frameAxis
                
                self.signalChannelAxis = signalChannelAxis
                
                axes = set([k for k in range(y.ndim)])
                
                axes.remove(self.frameAxis)
                axes.remove(self.signalChannelAxis)
                
                self.frameIndex = normalized_sample_index(y, self.frameAxis, frameIndex)
                
                self._number_of_frames_ = len(self.frameIndex)

                self.signalChannelIndex = normalized_sample_index(y, self.signalChannelAxis, signalChannelIndex)
                
                self.dataAxis = list(axes)[0]

                # NOTE: 2019-11-22 14:15:46
                # diplayframe() needs to decide whether to plot all channels 
                # in the frame as overlaid curves in one plot item (when 
                # separateSignalChannels is False) or in a column of plot items
                # (when separateSignalChannels is True)
                self.separateSignalChannels = separateSignalChannels
                
                _n_signal_axes_ = y.shape[self.signalChannelAxis] if self.separateSignalChannels else 1 
                # self._n_signal_axes_ = y.shape[self.signalChannelAxis] if self.separateSignalChannels else 1 
                
                self._meta_index = np.recarray((self._number_of_frames_,1), dtype=[('frame', int)])
                self._meta_index.frame[:,0] = self.frameIndex
                
            if x is not None:
                if isinstance(x, (tuple, list)):
                    if len(x) != y.shape[self.dataAxis]:
                        self.criticalMessage(f"Set data ({y.__class__.__name__})", "The supplied signal domain (x) must have the same size as the data axis %s" % self.dataAxis)
                        return False, None, None, 0    
                    
                    x = np.array(x)
                    
                elif isinstance(x, np.ndarray):
                    if not is_vector(x):
                        self.criticalMessage(f"Set data ({y.__class__.__name__})", "The supplied signal domain (x) must be a vector")
                        return False, None, None, 0
                    
                    if len(x) != y.shape[self.dataAxis]:
                        self.criticalMessage(f"Set data ({y.__class__.__name__})", "The supplied signal domain (x) must have the same size as the data axis %s" % self.dataAxis)
                        return False, None, None, 0
                    
                    if not is_column_vector(x):
                        x = x.T # x left unchanged if 1D
                        
                else:
                    self.criticalMessage(f"Set data ({y.__class__.__name__})", "Signal domain (x) must be None, a Python iterable of scalars or a numpy array (vector)")
            else:
                x = None
                
        elif isinstance(y, (tuple, list)) or hasattr(y, "__iter__"): # second condition to cover things like neo.SpikeTrainList (v >= 0.10.0)
            if len(y) == 0:
                self.clear()
                return False, None, None
            # python sequence of stuff to plot
            # TODO 2020-03-08 11:05:06
            # code for sequence of neo.SpikeTrain, and sequence of neo.Event
            self.separateSignalChannels         = separateSignalChannels
            self.singleFrame                    = singleFrame # ??? force all arrays in a sequence as a multiaxis single frame
            
            if self.singleFrame:
                self.separateSignalChannels = False # avoid any confusions
                
            self.signalChannelAxis              = signalChannelAxis 

            if np.all([isinstance(i, vigra.filters.Kernel1D) for i in y]):
                self.signalChannelAxis = 1 
                self.signalIndex = 1
                self.dataAxis = 0
                if frameAxis is None:
                    if self.separateSignalChannels:
                        _n_signal_axes_ = len(y)
                        # self._n_signal_axes_ = len(y)
                        self._number_of_frames_ = 1
                        self.frameIndex = range(self._number_of_frames_)
                    else:
                        self._number_of_frames_ = len(y)
                        self.frameIndex = range(self._number_of_frames_)
                        _n_signal_axes_ = 1
                        # self._n_signal_axes_ = 1
                else:
                    self._number_of_frames_ = len(y)
                    self.frameIndex = range(self._number_of_frames_)
                    _n_signal_axes_ = 1
                    # self._n_signal_axes_ = 1
                    self.separateSignalChannels = False
                
                xx, yy = zip(*list(map(kernel2array, y)))
                
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
                    
                y = yy
                self._cached_title = "Vigra Kernel1D objects"
                
                _n_signal_axes_ = 1
                # self._n_signal_axes_ = 1
                
                self._meta_index = np.recarray((self._number_of_frames_,1), dtype=[('frame', int)])
                self._meta_index.frame[:,0] = self.frameIndex
                
            elif all([isinstance(i, neo.Segment) for i in y]):
                # NOTE: 2019-11-30 09:35:42 
                # treat this as the segments attribute of a neo.Block
                # a segment is ALWAYS plotted in a single frame 
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
                
                x = None
                self._cached_title = "Neo segments"
                
                self.signalIndex                    = signalIndex
                self.irregularSignalIndex           = irregularSignalIndex
                
                _n_signal_axes_ = max(len(s.analogsignals) + len(s.irregularlysampledsignals) for s in y)
                # self._n_signal_axes_ = max(len(s.analogsignals) + len(s.irregularlysampledsignals) for s in y)
                
                self._meta_index = np.recarray((self._number_of_frames_,1),
                                               dtype = [('frame', int)])
                
                self._meta_index.frame[:,0] = self.frameIndex
                
            elif all([isinstance(i, neo.Block) for i in y]):
                # NOTE 2021-01-02 11:31:05
                # treat this as a sequence of segments, but do NOT concatenate
                x = None
                self.frameAxis = None
                self.dataAxis = 0
                self.signalChannelAxis = 1 
                self.signalChannelIndex = None
                self.irregularSignalChannelAxis = None
                self.irregularSignalChannelIndex = None
                self.separateSignalChannels = False
                self._data_frames_ = tuple(accumulate((len(b.segments) for b in y)))[-1]
                self.frameIndex = range(self._data_frames_)
                self._number_of_frames_ = len(self.frameIndex)
                self.signalIndex                    = signalIndex
                self.irregularSignalIndex           = irregularSignalIndex
                self._cached_title = "Neo blocks"
                
                _n_signal_axes_ = max(max(len(s.analogsignals) + len(s.irregularlysampledsignals) for s in b.segments) for b in y if len(b.segments))
                # self._n_signal_axes_ = max(max(len(s.analogsignals) + len(s.irregularlysampledsignals) for s in b.segments) for b in y if len(b.segments))
                
                mIndex = np.array(list(chain.from_iterable([[(bk,sk) for sk in range(len(b.segments))] for bk,b in enumerate(y) if len(b.segments)])))
                
                self._meta_index = np.recarray((mIndex.shape[0], 1), dtype=[('block', int), ('segment', int)])
                
                self._meta_index.block[:,0] = mIndex[:,0]
                self._meta_index.segment[:,0] = mIndex[:,1]
                
            elif all([isinstance(i, SIGNAL_OBJECT_TYPES) for i in y]):
                # NOTE: 2019-11-30 09:42:27
                # Treat this as a segment, EXCEPT that each signal is plotted
                # in its own frame. This is because in a generic container
                # there can be signals with different domains (e.g., t_start
                # & t_stop).
                # If signals must be plotted on stacked axes in the same 
                # frame then either collect them in a segment, or merge them
                # them in a 3D numpy array.
                self.dataAxis = 0
                self.signalChannelAxis = 1
                
                # NOTE: `2023-01-02 17:27:47
                # allow plotting all signals stacked in the same frame;
                # CAUTION: the risk is of too many signals (and PlotItems) in one frame

                # NOTE: 2023-01-18 08:33:13
                # for very large lists of signals, passing frameAxis None will
                # result in too many plotItems being created
                #
                # To avoid this, we set an arbitrary limit of 10 signals in the
                # collection, beyond which we automatically revert to one signal
                # per frame by setting frameAxis to 1
                #
                # The user may still overrride this - at their own risk - by 
                # passing a frameAxis int value different than 1 (one)
                
                if len(y) > 10:
                    if frameAxis is None:
                        frameAxis = 1
                    elif frameAxis != 1:
                        # for the sake of flexibility
                        frameAxis is None
                    
                # below, frameAxis None means all in one frame, many PlotItems
                # frameAxis not None means each in its own frame, one PlotItem per
                # frame
                if frameAxis is None:
                    self.frameAxis = None
                    self.frameIndex = range(1)
                    self._number_of_frames_ = 1
                    _n_signal_axes_ = len(y)
                    # self._n_signal_axes_ = len(y)
                    # NOTE: 2023-01-17 21:28:34
                    # When all signals in the collection are plotted in the same
                    # frame, using separateSignalChannels is cumbersome (albeit
                    # possible); to keep things simple, we preempt this here
                    self.separateSignalChannels = False
                    
                else:
                    # one signal per frame; this allows plotting channels in their
                    # own (separate) axes in one frame
                    self.frameAxis = 1
                    self.frameIndex = range(len(y))
                    self._number_of_frames_ = len(self.frameIndex)
                    self._data_frames_ = len(y)
                    
                    if self.separateSignalChannels:
                        _n_signal_axes_ = max(sig.shape[1] for sig in y)
                        # self._n_signal_axes_ = max(sig.shape[1] for sig in y)
                        
                    else:
                        _n_signal_axes_ = 1
                        # self._n_signal_axes_ = 1
                    
                self._meta_index = np.recarray((self._number_of_frames_, 1),
                                                dtype=[('frame', int)])
                self._meta_index.frame[:,0] = self.frameIndex
                
                self.signalIndex = 0 # FIXME is this needed anywhere?
                
                x = None
                self._cached_title = "Neo signals"
                
            elif all([isinstance(i, (neo.Event, DataMark)) for i in y]):
                x = None
                self._cached_title = "Events and marks"
                self.dataAxis = 0
                self.signalChannelAxis = 1
                self.frameIndex = range(1)
                self._number_of_frames_ = 1
            
                _n_signal_axes_ = 0
                # self._n_signal_axes_ = 0
                
                self._meta_index = np.recarray((self._number_of_frames_,1), dtype=[('frame', int)])
                self._meta_index.frame[:,0] = self.frameIndex

            elif all(isinstance(i, (neo.Epoch, DataZone)) for i in y):
                x = None
                self._cached_title = "Epochs and zones"
                self.dataAxis = 0
                self.signalChannelAxis = 1
                self.frameIndex = range(1)
                self._number_of_frames_ = 1
                _n_signal_axes_ = 1
                # self._n_signal_axes_ = 1
            
                self._meta_index = np.recarray((self._number_of_frames_,1), dtype=[('frame', int)])
                self._meta_index.frame[:,0] = self.frameIndex
                
            elif all([isinstance(i, neo.SpikeTrain) for i in y]):
                x = None
                self.dataAxis = 0
                self.signalChannelAxis = 1
                self._plotEpochs_(y)
                self.frameIndex = range(1)
                self._number_of_frames_ = 1
                self._cached_title = "Spike trains"
                _n_signal_axes_ = 0
                # self._n_signal_axes_ = 0
            
                self._meta_index = np.recarray((self._number_of_frames_,1), dtype=[('frame', int)])
                self._meta_index.frame[:,0] = self.frameIndex
                
            elif all([isinstance(i, np.ndarray) for i in y]):
                if not all(i.ndim <= 2 for i in y):
                    self.criticalMessage(f"Set data ({y.__class__.__name__})", f"Cannot plot sequences containing arrays with more than two dimensions")
                    return False, None, None, 0
                    
                if signalChannelAxis is None:
                    signalChannelAxis = 1 # the default
                    
                elif signalChannelAxis not in (0,1):
                    self.criticalMessage(f"Set data ({y.__class__.__name__})", f"signalChannelAxis expected an int () or 1) or None")
                    return False, None, None, 0
                    
                self.signalChannelAxis = signalChannelAxis
                self.dataAxis = 1 if self.signalChannelAxis == 0 else 0
                    
                self.frameIndex = range(len(y))
                self._number_of_frames_ = len(self.frameIndex)
                self.signalIndex = 1

                if x is not None:
                    # x might be a single 1D array (or 2D array with 2nd 
                    # axis a singleton), or a list of such arrays
                    # in this case force x as a list also!
                    if isinstance(x, np.ndarray):
                        if x.ndim  == 2:
                            if x.shape[1] > 1: # TODO use is_vector()
                                raise TypeError("for 'x', the 2nd axis of a 2D array must have shape of 1")
                            
                    elif isinstance(x,(tuple, list)) and \
                        not all([isinstance(x_, np.ndarray) and x_.ndim <= 2 for x_ in x]):
                            raise TypeError("'x' has incompatible shape %s" % self._xData_.shape)

                    else:
                        raise TypeError("Invalid x specified")
                    
                self._meta_index = np.recarray((self._number_of_frames_,1), dtype=[('frame', int)])
                self._meta_index.frame[:,0] = self.frameIndex
                
                self._cached_title = "Numpy arrays"
                # FIXME - in progress 2023-01-19 08:17:25
                _n_signal_axes_ = max(list(map(lambda x: 1 if x.ndim == 1 or not self.separateSignalChannels else x.shape[self.signalChannelAxis], y)))
                # self._n_signal_axes_ = max(list(map(lambda x: 1 if x.ndim == 1 or not self.separateSignalChannels else x.shape[self.signalChannelAxis], y)))
                
            else:
                self.criticalMessage(f"Set data ({y.__class__.__name__})", 
                                     "Can only plot a list of 1D vigra filter kernels, 1D/2D numpy arrays, or neo-like signals")
                return False, None, None, 0
            
        else:
            self.criticalMessage(f"Set data ({y.__class__.__name__})", 
                                 f"Plotting is not implemented for {type(y).__name__} data types")
            return False, None, None, 0
        
        return True, x, y, _n_signal_axes_
    
    @with_doc(_parse_data_, use_header=True)
    @safeWrapper
    def _set_data_(self, x,  y = None, doc_title:(str, type(None)) = None, 
                   frameAxis:(int, str, vigra.AxisInfo, type(None)) = None, 
                   signalChannelAxis:(int, str, vigra.AxisInfo, type(None)) = None, 
                   frameIndex:(int, tuple, list, range, slice, type(None)) = None, 
                   signalIndex:(str, int, tuple, list, range, slice, type(None)) = None, 
                   signalChannelIndex:(int, tuple, list, range, slice, type(None)) = None, 
                   irregularSignalIndex:(str, int, tuple, list, range, slice, type(None)) = None, 
                   irregularSignalChannelAxis:(int, type(None)) = None, 
                   irregularSignalChannelIndex:(int, tuple, list, range, slice, type(None)) = None, 
                   separateSignalChannels:bool = False, separateChannelsIn:str="axes", 
                   singleFrame:bool=False, 
                   interval:(tuple, list, neo.Epoch, type(None)) = None, 
                   plotStyle:str = "plot", showFrame:int = None, 
                   *args, **kwargs):
        """Sets up internal variables and triggers plotting.
Does the behind the scene work of self.setData(...)
"""
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
            dataOK, x, y, n_axes = self._parse_data_( x = x, y = y, 
                                        frameIndex = frameIndex, 
                                        frameAxis = frameAxis,
                                        signalIndex = signalIndex, 
                                        signalChannelAxis = signalChannelAxis,
                                        signalChannelIndex = signalChannelIndex,
                                        irregularSignalIndex = irregularSignalIndex,
                                        irregularSignalChannelAxis = irregularSignalChannelAxis,
                                        irregularSignalChannelIndex = irregularSignalChannelIndex,
                                        separateSignalChannels = separateSignalChannels,
                                        separateChannelsIn = separateChannelsIn,
                                        singleFrame = singleFrame)
            
            # print(f"self._set_data_ dataOK = {dataOK}")
            
            if dataOK:
                self._clear_lris_() # remove gremlins (i.e. any epochs LinearRegionItem)
                
                # NOTE: 2023-06-02 13:09:25
                # to avoid flicker, set up axes ONLY if data demands a different
                # number of axes
                if n_axes != self._n_signal_axes_:
                    self._setup_axes_(n_axes) # also assigns n_axes to self._n_signal_axes_
                    
                if isinstance(showFrame, int):
                    if showFrame < 0:
                        showFrame = 0
                        
                    elif showFrame > self._number_of_frames_:
                        showFrame = self._number_of_frames_ - 1
                        
                    self._current_frame_index_ = showFrame
                    
                else:
                    if self._current_frame_index_ not in self.frameIndex:
                        self._current_frame_index_ = self.frameIndex[-1]
                        
                if isinstance(plotStyle, str):
                    self.plotStyle = plotStyle
                    
                elif isinstance(style, str):
                    self.plotStyle = style
                    
                self._frames_spinBoxSlider_.range = range(self._number_of_frames_)
                self._frames_spinBoxSlider_.setValue(self._current_frame_index_)
                
                # NOTE: 2022-11-01 10:37:06
                # overwrites self.docTitle set by self._parse_data_
                if isinstance(doc_title, str) and len(doc_title.strip()):
                    self.docTitle = doc_title
                else:
                    self.docTile = self._cached_title
                
                self._xData_ = x
                self._yData_ = y

                self.actionDetect_Triggers.setEnabled(check_ephys_data_collection(self._yData_))
                            
                self.observed_vars["xData"] = self._xData_
                self.observed_vars["yData"] = self._yData_
                
                # NOTE: 2023-06-02 11:02:18
                # force plotting when the new data is the same as the existing
                # one, (and therefore the above two lines did not issue a 
                # a notification)
                #
                # TODO: 2023-06-02 11:08:08
                # contemplate placing _var_notified_ and _new_frame_ in the 
                # observed_var
                
                if not self._var_notified_:
                    # NOTE: 2023-07-09 11:56:22
                    # see also NOTE: 2023-07-09 11:54:06
                    # force replotting the data
                    self._new_frame_ = True
                    self.displayFrame()
                    self._new_frame_ = False
                else:
                    self._var_notified_ = False
                
                self.frameChanged.emit(self._current_frame_index_)
                
            else:
                warnings.warn(f"Could not parse the data x: {x}, y: {y}")
                return
            

        except Exception as e:
            traceback.print_exc()
            
    @with_doc(_set_data_, use_header=True)
    @safeWrapper
    def setData(self, x, /, y = None, doc_title:(str, type(None)) = None,
                frameAxis:(int, str, vigra.AxisInfo, type(None)) = None,
                signalChannelAxis:(int, str, vigra.AxisInfo, type(None)) = None,
                frameIndex:(int, tuple, list, range, slice, type(None)) = None,
                signalIndex:(str, int, tuple, list, range, slice, type(None)) = None,
                signalChannelIndex:(int, tuple, list, range, slice, type(None)) = None,
                irregularSignalIndex:(str, int, tuple, list, range, slice, type(None)) = None,
                irregularSignalChannelAxis:(int, type(None)) = None,
                irregularSignalChannelIndex:(int, tuple, list, range, slice, type(None)) = None,
                separateSignalChannels:bool = False, separateChannelsIn:str="axes",
                singleFrame:bool=False, interval:(tuple, list, neo.Epoch, type(None)) = None,
                plotStyle:str = "plot", get_focus:bool = False,
                showFrame = None, *args, **kwargs):
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
    datasignal.DataSignal) frameAxis may be used to plot the signal's
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
    datasignal.DataSignal).
    
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
        
        # print(f"{self.__class__.__name__}.setData(x={type(x).__name__}, y={type(y).__name__})")
        
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
            
        
        uiParamsPrompt = kwargs.pop("uiParamsPrompt", False) # ?!?
        
        if uiParamsPrompt:
            # TODO 2023-01-18 08:48:13 - finalize self._ui_getViewParams
            # this is to open up dialog for parameters
            pass
            # print(f"{self.__class__.__name__}.setData uiParamsPrompt")
            
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
                        separateChannelsIn = separateChannelsIn,
                        singleFrame=singleFrame,
                        interval = interval,
                        plotStyle = plotStyle,
                        showFrame = showFrame,
                        **kwargs)
        
        if not self.isVisible():
            self.setVisible(True)
            
        if get_focus:
            self.activateWindow()
            
    def _ui_getViewParams(self, doc_title, frameAxis, signalChannelAxis,
                          frameIndex, signalIndex, signalChannelIndex,
                          irregularSignalIndex, irregularSignalChannelAxis, 
                          irregularSignalChannelIndex,
                          separateSignalChannels, separatechannelsIn,singleFrame):
        """ Parameters to prompt for (via quickdialog.StringInput unless specified):
        NOTE 1: below, a value of None can be specified as the string "None"
        NOTE 2: a bool value can be specified as "frue" or "false" (case-insensitive)
            or as an int (0, or 1)
        doc_title: str
        frameAxis: int or None
        signalChannelAxis: int, str, or None  NOTE: cannot supply vigra.AxisInfo;
        frameIndex: int, tuple, list, range, slice, None
        signalIndex: str, int, tuple, list, range, slice, None
        signalChannelIndex: int, tuple, list, range, slice, None
        irregularSignalIndex: str, int, tuple, list, range, slice, None
        irregularSignalChannelAxis: int, None
        irregularSignalChannelIndex: int, tuple, list, range, slice, None
        separateSignalChannels: bool ← CheckBox
        separateChannelsIn: "axes" "frames" ← HChoice
        singleFrame:bool ← CheckBox
        get_focus: bool ← CheckBox
        showFrame: int or None
        
        
    """
        # WARNING: not supported: 
        # plotStyle: str NOTE: for now, only "plot" is supported
        # interval
        d = qd.QuickDialog(self, "View parameters")
        d.promptWidgets = []
        doc_title_prompt = qd.StringInput(d, "Data name")
        doc_title_prompt.variable.setClearButtonEnabled(True)
        doc_title_prompt.variable.redoAvailable = True
        doc_title_prompt.variable.undoAvailable = True
        d.promptWidgets.append(doc_title_prompt)
        
        doc_title_prompt.setText(doc_title)
        frameAxis_prompt = qd.StringInput(d, "Frame axis")
        frameAxis_prompt.variable.setClearButtonEnabled(True)
        frameAxis_prompt.variable.redoAvailable = True
        frameAxis_prompt.variable.undoAvailable = True
        d.promptWidgets.append(frameAxis_prompt)
        
        # TODO 2023-08-27 15:10:03 finalize me !!!
            
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
        
        # print(f"{self.__class__.__name__}.currentFrame missing = {missing}")
        
        if missing or (val not in self.frameIndex):
            self.setDataDisplayEnabled(False)
            return
        else:
            self.setDataDisplayEnabled(True)
            
        val = int(val)
        
        # to force re-plotting spike trains, 
        # see NOTE: 2023-01-04 22:14:55,
        # NOTE: 2023-05-16 23:04:37,
        # NOTE: 2023-05-16 23:05:22
        # NOTE: 2023-05-16 23:02:20
        # NOTE: 2023-07-09 11:54:06
        self._new_frame_ = self._current_frame_index_ != val
        self._current_frame_index_ = val
        
        # NOTE: 2018-09-25 23:06:55
        # recipe to block re-entrant signals in the code below
        # cleaner than manually connecting and re-connecting
        # and also exception-safe
        
        signalBlocker = QtCore.QSignalBlocker(self._frames_spinBoxSlider_)
        self._frames_spinBoxSlider_.setValue(self._current_frame_index_)

        self.displayFrame()
        
        if self._new_frame_:
            self.frameChanged.emit(self._current_frame_index_)

    @property
    def plotItemsWithLayoutPositions(self):
        """ A zipped list of tuples (PlotItem, grid coordinates).
        Aliased to the axesWithLayoutPositions property
        
        This includes the signal axes, and the events and spiketrains axes.
        
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
        """A tuple of PlotItems.
        This includes the signal axes, and the events and spiketrains axes
        """
        px = self.plotItemsWithLayoutPositions
        
        if len(px):
            ret, _ = zip(*px)
            
        else:
            ret = tuple()
        
        return ret
    
    @property
    def axesWithLayoutPositions(self):
        """Alias to self.plotItemsWithLayoutPositions property (syntactic sugar)
        """
        return self.plotItemsWithLayoutPositions
    
    @property
    def axes(self):
        """The tuple of axes (PlotItem objects) for current frame
        
        Alias to self.plotItems property
        """
        return self.plotItems
    
    @safeWrapper
    def plotItem(self, index: int):
        """Returns the axis (PlotItem) at the specified index.
        
        Does the same thing as self.axis(index) but with the overhead of 
        iterating over the items in self.signalsLayout (a pg.GraphicsLayout).
        
        Raises an exception if index is not valid.
        """
        return self.axes[index]
    
    def axis(self, index:typing.Union[int, str]):
        """Calls self.plotItem(index) -- syntactic sugar
        """
        if isinstance(index, str):
            axnames = [ax.vb.name for ax in self.axes]
            if index not in axnames:
                raise ValueError(f"An axis named {index} does not exist in this viewer")
            
            index = axnames.index(index)
        
        if not isinstance(index, int):
            raise TypeError(f"Axis index expected to be an int or str; nstead, got {type(index).__name__} ")

        return self.plotItem(index)
    
    @property
    def yData(self):
        return self._yData_
    
    @yData.setter
    def yData(self, value):
        self.setData(self._xData_, value)
        
    @property
    def xData(self):
        return self._xData_
    
    @xData.setter
    def xData(self, value):
        self.setData(value, self._yData_)
        
    @property
    def data(self):
        """Tuple X data, Y data.
        X data may be None, depending on the type of Y data
        """
        return self.xData, self.yData
    
    @data.setter
    def data(self, value:tuple):
        """Calls self.setData (x,y) and default values for the other parameters.
        See self.setData (aliased to self.plot and to self.view) for details.
        """
        if isinstance(value, tuple):
            if len(value) == 2:
                try:
                    self.setData(*value)
                except:
                    traceback.print_exc()
                    raise TypeError(f"Could not parse X data type ({type(value[0]).__name__}) or Y data type ({type(value[1]).__name__})")
            else:
                raise ValueError(f"Expecting a 2-tuple; got {len(value)}-tuple instead")
            
        else:
            raise TypeError(f"Expecting a 2-tuple; got {type(value).__name__} instead")
            
    
    @property
    def selectedPlotItem(self):
        """Alias to currentPlotItem"""
        return self.currentPlotItem
    
    @selectedPlotItem.setter
    def selectedPlotItem(self, index):
        self.currentPlotItem = index
        
    @property
    def currentPlotItem(self):
        """Reference to the selected (current) axis (PlotItem).
        
        The setter counterpart sets the current plot item to be a reference to
        the PlotItem with the specified index.
        """
        return self._selected_plot_item_
    
    @currentPlotItem.setter
    def currentPlotItem(self, index: typing.Union[int, pg.PlotItem, str]):
        """Sets the current plot item to the one at the specified index.
        
        Index: int index or a plotitem
        """
        plotitems_coords = self.axesWithLayoutPositions # a reference, so saves computations
        
        if len(plotitems_coords) == 0:
            #QtWidgets.QMessageBox.critical(self, "Set current axes:", "Must plot something first!")
            self._selected_plot_item_ = None
            self._selected_plot_item_index_ = -1
            return False
        
        plotitems, _ = zip(*plotitems_coords)
        
        if isinstance(index, int):
            if index not in range(len(plotitems)):
                warnings.warn(f"Expecting an int between 0 and {len(plotitems)}; got a {index}  instead")
                return
                # raise TypeError(f"Expecting an int between 0 and {len(plotitems)}; got a {index}  instead")
            
            self._selected_plot_item_ = plotitems[index]
            self._selected_plot_item_index_ = index
            
        elif isinstance (index, pg.PlotItem) and index in self.axes:
            self._selected_plot_item_ = index
            self._selected_plot_item_index_ = plotitems.index(index)
            
        elif isinstance(index, str):
            names = [ax.vb.name for ax in self.axes]
            if index not in names:
                return
            
            axindex = names.index(index)
            
            self._selected_plot_item_ = plotitems[axindex]
            self._selected_plot_item_index_ = axindex
            
        else:
            return
            
        self._setAxisIsActive(self._selected_plot_item_, True)
        self._statusNotifyAxisSelection(index)
        
        for ax in self.axes:
            if ax is not self._selected_plot_item_:
                self._setAxisIsActive(ax, False)
        
        # self.statusBar().showMessage(f"Selected axes: {index} ({self._plot_names_.get(index)})")
        
    @property
    def currentAxisIndex(self):
        return self._selected_plot_item_index_
    
    @currentAxisIndex.setter
    def currentAxisIndex(self, index:int):
        if index not in range(-len(self.axes), len(self.axes)):
            raise ValueError(f"index {index} out range for {len(self.axes)}")
        
        self.currentAxis = self.axes[index]
        
    @property
    def currentAxis(self):
        return self.currentPlotItem
    
    @currentAxis.setter
    def currentAxis(self, axis:typing.Union[int, pg.PlotItem, str]):
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
        
    def _statusNotifyAxisSelection(self, index=None) -> None:
        if index is None:
            index = self._selected_plot_item_index_
        elif not isinstance(index, int) or index not in range(len(self.axes)):
            return
        
        plot_name = self._plot_names_.get(index, "")
                
        if isinstance(plot_name, str) and len(plot_name.strip()):
            self.statusBar().showMessage(f"Selected axes: {index} ({plot_name})")
            
        else:
            self.statusBar().showMessage(f"Selected axes: {index}")
            
    def _setAxisIsActive(self, axis, active:False) -> None:
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
        
    def signalCursor(self, ID:str) -> SignalCursor:
        """Not to be confused with the Qt method self.cursor() !!!
        """
        if len(self._data_cursors_) and ID in self._data_cursors_:
            return self._data_cursors_[ID]
        
    # def signalCursor(self, ID:str) -> SignalCursor:
    #     return self.signalCursor(ID)
        
    def cursorWindow(self, crsID:str) -> numbers.Number:
        if self._hasCursor_(crsID):
            #print(crsID)
            return (self._data_cursors_[crsID].xwindow, self._data_cursors_[crsID].ywindow)
        else:
            raise Exception("SignalCursor %s not found" % crsID)
        
    def cursorX(self, crsID:str) -> numbers.Number:
        if self._hasCursor_(crsID):
            return self._data_cursors_[crsID].x
        else:
            return None
        
    def cursorY(self, crsID:str) -> numbers.Number:
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
    
    def getSignalCursors(self, cursorType:typing.Optional[typing.Union[str, SignalCursorTypes]]=None):
        """Returns the dictionary of SignalCursor objects with the specified type.
        All cursors with the same cursor type are stored in the same dictionary
        regardless whether they are atatched to a specific axis or not.
        Hence, no two cursors of the same type can have the same ID.
    """
        if cursorType is None:
            return self.cursors
        
        if isinstance(cursorType, str):
            cursorType = SignalCursorTypes.getType(cursorType)
            
        elif not isinstance(cursorType, SignalCursorTypes):
            raise TypeError(f"Expecting a SignalCursorTypes value or a SignalCursorTypes name (str); instead, got {type(cursorType).__name__}")
        
        attr = f"_{cursorType.name}SignalCursors_"
        
        return getattr(self, attr, dict())
    
    def getDataCursors(self, cursorType:typing.Optional[typing.Union[str, SignalCursorTypes]]):
        """ Calls self.getSignalCursors: 
        Returns a dictionary of SignalCursor objects with the specified type."""
        return self.getSignalCursors(cursorType)
    
    def getCursors(self, cursorType:typing.Optional[typing.Union[str, SignalCursorTypes]]):
        return self.getSignalCursors(cursorType)
    
    def registerCursor(self, cursor, cursorDict:typing.Optional[dict]=None, **kwargs):
        """Register externally-created cursors.
        """
        # TODO: 2023-06-12 23:11:50
        # Use for internally created cursors as well (to call from _addCursor_)
        if not isinstance(cursorDict, dict):
            cursorDict = self.getSignalCursors(cursor.cursorType)
            
        crsId = cursor.ID
        if crsId in cursorDict:
            warnings.warn(f"A {cursor.cursorType.name} cursor named {crsId} already exists")
            return
        
        if cursor in cursorDict.values():
            ndx = list(cursorDict.values()).index(cursor)
            existing = list(cursorDict.keys())[ndx]
            warnings.warn(f"This {cursor.cursorType.name} cursor is already registered as {existing} ")
            return
            
        pen = kwargs.get("pen", None)
        if isinstance(pen, QtGui.QPen):
            cursor.pen = pen
            
        hoverPen = kwargs.get("hoverPen", None)
        if isinstance(hoverPen, QtGui.QPen):
            cursor.hoverPen = hoverPen
            
        linkedPen = kwargs.get("linkedPen", None)
        if isinstance(linkedPen, QtGui.QPen):
            cursor.linkedPen = linkedPen
            
        showValue = kwargs.get("showValue", None)
        precision = kwargs.get("precision", None)
        
        if showValue:
            if isinstance(precision, int) and precision > 0:
                cursor.setShowValue(self._cursorsShowValue_, precision)
                
            else:
                cursor.setShowValue(self._cursorsShowValue_, self._cursorLabelPrecision_)
        else:
            if isinstance(precision, int) and precision > 0:
                cursor.precision = precision
            
        cursorDict[crsId] = cursor
        cursorDict[crsId].sig_cursorSelected[str].connect(self.slot_selectCursor)
        cursorDict[crsId].sig_reportPosition[str].connect(self.slot_reportCursorPosition)
        cursorDict[crsId].sig_doubleClicked[str].connect(self.slot_editCursor)
        cursorDict[crsId].sig_lineContextMenuRequested[str].connect(self.slot_cursorMenu)
        cursorDict[crsId].sig_editMe[str].connect(self.slot_editCursor)
        
        
        
        
    
    @property
    def verticalCursors(self):
        """List of vertical signal cursors
        """
        return [c for c in self._verticalSignalCursors_.values()]
    
    @property
    def horizontalCursors(self):
        """List of horizontal signal cursors
        """
        return [c for c in self._horizontalSignalCursors_.values()]
    
    @property
    def crosshairCursors(self):
        """List of croshair signal cursors
        """
        return [c for c in self._crosshairSignalCursors_.values()]
    
    @pyqtSlot(bool)
    def _slot_showXgrid(self, value:bool):
        self.xGrid = value
    
    @pyqtSlot(bool)
    def _slot_showYgrid(self, value:bool):
        self.yGrid = value
    
    @pyqtSlot(bool)
    def _slot_setXAxesLinked(self, value:bool):
        self.xAxesLinked = value == True
        
    @pyqtSlot(bool)
    def _slot_setEditCursorWhenCreated(self, value):
        # print(f"{self.__class__.__name__}._slot_setEditCursorWhenCreated {value}")
        self.editCursorUponCreation = value == True
            
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
    def _slot_plot_axis_x_range_changed(self, vb, x0x1):
        """Captures changes in the view range on the X axis.
        Triggered by PlotItem signal sigXRangeChanged.
        These changes are typically generated using a mouse button pressed in 
        a Plotitem (signal viewer "axis").
        
        """
        if not isinstance(vb, pg.ViewBox):
            return
        
        if not isinstance(x0x1, tuple) or len(x0x1) != 2:
            return
        
        vbAxes = [ax for ax in self.axes if ax.vb == vb]
        
        if len(vbAxes):
            vbAxis = vbAxes[0]
            
        else:
            return
        
        ax_ndx = self.axes.index(vbAxis)
        self._axes_X_view_ranges_[ax_ndx] = x0x1
        
        bounds = self._get_axis_data_X_range_(vbAxis)
        offset_scale = self._calculate_new_X_offset_scale_(bounds, x0x1)
        self._axes_X_view_offsets_scales_[ax_ndx] = offset_scale
        
        if self.currentFrame in self._cached_epochs_:
            if len(self._cached_epochs_[self.currentFrame]):
                self._plotEpochs_(from_cache=True)
                
    @pyqtSlot(object)
    def _slot_plot_axis_range_changed_manually(self, value:object):
        """Triggered by PlotItem's ViewBox sigRangeChangedManually signal"""
        vb = self.sender()
        
        
        if value in (pg.ViewBox.RectMode, pg.ViewBox.PanMode):
            mouseMode = value
        else:
            mouseMode = vb.state["mouseMode"]
            
        # print(f"{self.__class__.__name__} range changed manually in {mouseMode}")

        ax = [ax for ax in self.axes if ax.vb == vb]
        
        if len(ax) == 0:
            return
        
        ax = ax[0]
        ax.sigXRangeChanged.emit(vb, vb.viewRange()[0])
        # ax.sigXRangeChanged.emit(vb, (math.nan, math.nan))
        # ax.sigXRangeChanged.emit(None, None)
        
    @safeWrapper
    def refresh(self):
        """
        Refresh the display
        """
        for axis in self.axes:
            axis.update(axis.boundingRect())
        # self.displayFrame()
        
    @safeWrapper
    def displayFrame(self):
        """ Plots individual frame (data "sweep" or "segment")
        
        Implements gui.scipyenviewer.ScipyenFrameViewer.displayFrame
        
        Parameters:
        -----------
        new_data: optional, default is True
            By default this is called whenever new data has been passed to the
            signal viewer to be plotted.
        
            The exceptions are when there is only a change in axes' visibility
            but the data had not been changed. In this case it is recommended
            to pass new-data=False to avoid unnecessary function calls related
            to plotting the same data again
            
        
        Delegates plotting as follows:
        ------------------------------
        neo.Segment                     ↦ _plotSegment_ # needed to pick up which signal from segment
        neo.AnalogSignal                ↦ _plot_signal_
        neo.IrregularlySampledSignal    ↦ _plot_signal_
        neo.Epoch                       ↦ _plot_signal_
        neo.SpikeTrain                  ↦ _plot_signal_
        neo.Event                       ↦ _plot_signal_
        datasignal.DataSignal            ↦ _plot_signal_
        vigra.Kernel1D, vigra.Kernel2D  ↦ _plotNumpyArray_ 
            NOTE: These are converted to numpy.ndarray
        numpy.ndarray                   ↦ _plotNumpyArray_ 
            NOTE: This includes vigra.VigraArray and quantities.Quantity arrays
            The meta-information in VigarArray objects is ignored here.
        
        
        sequence (iterable)             ↦ _plotSequence_
            NOTE: The sequence can contain these types:
                neo.AnalogSignal, 
                neo.IrregularlySampledSignal, 
                datasignal.DataSignal, 
                np.ndarray
                vigra.filters.Kernel1D  (NOTE  this is converted to two numpy arrays)
        
        Anything else                   ↦ ignored
        
        """
        if self._yData_ is None:
            # print(f"{self.__class__.__name__} self._yData_ is None")
            self.clear()
            return
        
        self.currentFrameAnnotations = None
        
        # print(f"SignalViewer({self._winTitle_}).displayFrame {self.currentFrame}")
        
        self._plot_data_(self._yData_, *self.plot_args, **self.plot_kwargs)
        
        # NOTE: 2020-03-10 22:09:51
        # reselect an axis according to its index (if one had been selected before)
        # CAUTION: this may NOT be the same PlotItem object!
        # also makes sure we always have an axis selected
        if len(self.plotItems):
            if self._selected_plot_item_ is None:
                self._selected_plot_item_index_ = 0 # by default
                self._selected_plot_item_ =  self.plotItems[self._selected_plot_item_index_] 
                
            elif self._selected_plot_item_ not in self.plotItems:
                if self._selected_plot_item_index_ < 0: # this is prev index
                    self._selected_plot_item_index_ = 0
                    
                elif self._selected_plot_item_index_ >= len(self.plotItems):
                        self._selected_plot_item_index_ = len(self.plotItems) -1
                    
                self._selected_plot_item_ = self.plotItems[self._selected_plot_item_index_]
                
            else:
                self._selected_plot_item_index_ = self.plotItems.index(self._selected_plot_item_)
                
            self._setAxisIsActive(self._selected_plot_item_, True)
                    
        else:
            # have no axis selected as current, only when there are no axes
            # (pg.PlotItem objects)
            self._selected_plot_item_ = None
            self._selected_plot_item_index_ = -1
                    
        self._update_annotations_() # is this crashing the thread? -- No!
        
        # Check if cursors want to stay in axis or stay with the domain
        # and act accordingly
        mfun = lambda x: -np.inf if x is None else x
        pfun = lambda x: np.inf if x is None else x
        
        for k, ax in enumerate(self.axes):
            [[dataxmin, dataxmax], [dataymin, dataymax]] = guiutils.getPlotItemDataBoundaries(ax)
            
            for c in self.cursorsInAxis(k):
                if not c.staysInAxes:
                    continue
                
                if not c.isHorizontal:
                    relX = c.x - c.xBounds()[0]
                    c.setBounds()
                    c.x = dataxmin + relX
                    
                if not c.isVertical:
                    # print(f"{self.__class__.__name__}.displayFrame for cursor in axis {k}: cursor type {c.cursorType}, coordinates: {c.y}; bounds: {c.yBounds()}")
                    yBounds = c.yBounds()
                    relY = c.y - c.yBounds()[0]
                    c.setBounds()
                    c.y = dataymin+relY
                    
        # NOTE: 2022-11-22 11:49:47
        # Finally, check for target overlays
        
        try:
            cFrame = self.frameIndex[self.currentFrame]
        except:
            cFrame = self.frameIndex[0]
            
        for k, ax in enumerate(self.axes):
            if ax.isVisible():
                self._clear_targets_overlay_(ax)
                if cFrame in self._target_overlays_:
                    targetItems = self._target_overlays_[cFrame].get(k, list())
                    if len(targetItems):
                        for tgt in targetItems:
                            ax.addItem(tgt)
                    
                
        # NOTE: 2023-05-09 10:41:27 connected to _slot_post_frameDisplay
        # this also sets up axes lines visibility & tickmarks
        
        # cache these now (they may be overwritten in slots triggered by mouse
        # interactions in the plot item)
        # for kax, ax in enumerate(self.axes):
        #     bounds = self._get_axis_data_X_range_(ax)
        #     if any(np.isnan(v) for v in bounds):
        #         continue
        #     self._x_data_bounds_[kax] = bounds
        #     viewXrange = ax.vb.viewRange()[0]
        #     self._axes_X_view_ranges_[kax] = viewXrange
        #     offset, scale = self._calculate_new_X_offset_scale_(bounds, viewXrange)
        #     self._axes_X_view_offsets_scales_[kax] = (offset, scale)
            
        self.sig_frameDisplayReady.emit()
        
    def _calculate_new_X_offset_scale_(self, databounds:tuple, viewbounds:tuple,
                                       padding:typing.Optional[float] = 0.) -> tuple:
        """Calculates the X offset and X view scale given X data bounds and view range.
    Helper function returning a tuple (offset, scale) used in the _align_X_range
    """
        # print(f"{self.__class__.__name__}._calculate_new_X_offset_scale_ databounds = {databounds}, viewbounds = {viewbounds}")
        dspan = databounds[1]-databounds[0]
        vspan = viewbounds[1]-viewbounds[0]
        
        offset = databounds[0] - viewbounds[0] + padding
        scale = vspan/dspan if dspan != 0 else 1
        
        return offset,scale
        
    def _get_axis_X_view_state(self, ax:typing.Union[int, pg.PlotItem]) -> tuple:
        """Returns a tuple (offset, scale).
    When there is no data plottd in the item returns (None, None)"""
        if isinstance(ax, pg.PlotItem):
            if ax not in self.axes:
                raise ValueError(f"Axis {ax} not found in this viewer")
            ax_ndx = self.axes.index(ax)
            
        elif isinstance(ax, int):
            if ax not in range(self.axes):
                raise ValueError(f"Invalid axis index {ax} for {len(self.axes)} axes")
            
            ax_ndx = ax
            ax = self.axes[ax_ndx]
            
        else:
            raise TypeError(f"Invalid axis specification; expected an int or a PlotItem; got {type(ax).__name__} instead")
        
        xd0, xd1 = self._get_axis_data_X_range_(ax)
        dspan = xd1 - xd0
        # xv0, xv1 = ax.vb.viewRange()[0]
        xv0, xv1 = ax.vb.state["viewRange"][0]
        vspan = xv1 - xv0
        
        offset = xd0 - xv0
        scale = vspan/dspan if dspan != 0. else 1.
        
        return offset, scale
    
    def _get_axis_Y_view_state(self, ax:typing.Union[int, pg.PlotItem]) -> tuple:
        if isinstance(ax, pg.PlotItem):
            if ax not in self.axes:
                raise ValueError(f"Axis {ax} not found in this viewer")
            ax_ndx = self.axes.index(ax)
            
        elif isinstance(ax, int):
            if ax not in range(self.axes):
                raise ValueError(f"Invalid axis index {ax} for {len(self.axes)} axes")
            
            ax_ndx = ax
            ax = self.axes[ax_ndx]
            
        else:
            raise TypeError(f"Invalid axis specification; expected an int or a PlotItem; got {type(ax).__name__} instead")
        
        yd0, yd1 = self._get_axis_data_Y_range_(ax)
        dspan = yd1 - yd0
        
        yv0, yv1 = ax.vb.viewRange()[1]
        vspan = yv1 - yv0
        
        offset = yd0 - yv0
        scale = vspan/dspan if dspan != 0. else 1.
        
        return offset, scale
    
    def _get_axis_view_X_range(self, axis:typing.Union[int, pg.PlotItem]) -> tuple:
        if isinstance(axis, int):
            if axis not in range(len(self.axes)):
                raise ValueError(f"Invalid axis index {axis} for {len(self.axes)} axes")
            
            axis = self.axes[axis]
            
        elif isinstance(axis, pg.PlotItem):
            if axis not in self.axes:
                raise ValueError(f"Axis {axis} is not in this viewer")
            
        else:
            raise TypeError(f"Invalid axis specification; expected an int or a PlotItem; got {type(axis).__name__} instead")
        
        xv0, xv1 = axis.vb.viewRange()[0]
        
        return xv0, xv1
        
    def _get_axis_data_X_range_(self, axis:typing.Union[int, pg.PlotItem]) -> tuple:
        if isinstance(axis, int):
            if axis not in range(len(self.axes)):
                raise ValueError(f"Invalid axis index {axis} for {len(self.axes)} axes")
            
            axis = self.axes[axis]
            
        elif isinstance(axis, pg.PlotItem):
            if axis not in self.axes:
                raise ValueError(f"Axis {axis} is not in this viewer")
            
        else:
            raise TypeError(f"Invalid axis specification; expected an int or a PlotItem; got {type(axis).__name__} instead")
        
        pdis = [i for i in axis.items if isinstance(i, pg.PlotDataItem)]
        
        # print(f"{self.__class__.__name__}._get_axis_data_X_range_ axis {self.axes.index(axis)} : {len(pdis)} plot data items")
        
        if len(pdis):
            # xbounds0, xbounds1 = zip(*map(lambda i_ : i_.dataBounds(0), pdis))
            # NOTE: BUG
            # the 'dataBounds' method returns None, None if the pdi is not
            # visible!
            # NOTE: 2023-07-09 21:09:08
            # use dataRect() instead
            xbounds0, xbounds1 = zip(*map(lambda i_ : (i_.dataRect().x(), i_.dataRect().x() + i_.dataRect().width()), pdis))
            min_x = min(xbounds0)
            max_x = max(xbounds1)
            # print(f"\txbounds0 {xbounds0}, xbounds1 {xbounds1} min_x {min_x}, max_x {max_x}")
            # items_min_x, items_max_x = zip(*list((float(np.nanmin(i.xData)), float(np.nanmax(i.xData))) for i in pdis))
            
            # min_x = items_min_x[0] if isinstance(items_min_x, (tuple, list)) else items_min_x
            # max_x = items_max_x[0] if isinstance(items_max_x, (tuple, list)) else items_max_x
            
            # NOTE: 2023-07-07 13:17:42
            # when the axis (a pg.PlotItem) is not visibile, neither are its 
            # plot data items; in turn, then these are NOT visible, their dataBounds(…)
            # method returns None, None !!!
            if  min_x is None:
                min_x = math.nan
            if max_x is None:
                max_x =math.nan
            return min_x, max_x
            
        else:
            return math.nan, math.nan
        
    def _get_axis_data_Y_range_(self, axis:typing.Union[int, pg.PlotItem]) -> tuple:
        if isinstance(axis, int):
            if axis not in range(len(self.axes)):
                raise ValueError(f"Invalid axis index {axis} for {len(self.axes)} axes")
            
            axis = self.axes[axis]
            
        elif isinstance(axis, pg.PlotItem):
            if axis not in self.axes:
                raise ValueError(f"Axis {axis} is not in this viewer")
            
        else:
            raise TypeError(f"Invalid axis specification; expected an int or a PlotItem; got {type(axis).__name__} instead")
        
        pdis = [i for i in axis.items if isinstance(i, pg.PlotDataItem)]
        
        if len(pdis):
            ybounds0, ybounds1 = zip(*map(lambda i_ : i_.dataBounds(1), pdis))
            min_y = min(ybounds0)
            max_y = max(ybounds1)
            return min_y, max_y
#             items_min_y, items_max_y = zip(*list((float(np.nanmin(i.yData)), float(np.nanmax(i.yData))) for i in pdis))
#             
#             min_y = items_min_y[0] if isinstance(items_min_y, (tuple, list)) else items_min_y
#             max_y = items_max_y[0] if isinstance(items_max_y, (tuple, list)) else items_max_y
#             
#             return min_y, max_y
            
        else:
            return math.nan, math.nan
        
    def _get_axis_view_Y_range(self, axis:typing.Union[int, pg.PlotItem]) ->tuple:
        if isinstance(axis, int):
            if axis not in range(len(self.axes)):
                raise ValueError(f"Invalid axis index {axis} for {len(self.axes)} axes")
            
            axis = self.axes[axis]
            
        elif isinstance(axis, pg.PlotItem):
            if axis not in self.axes:
                raise ValueError(f"Axis {axis} is not in this viewer")
            
        else:
            raise TypeError(f"Invalid axis specification; expected an int or a PlotItem; got {type(axis).__name__} instead")
        
        yv0, yv1 = axis.vb.viewRange()[1]
        
        return yv0, yv1
    
    @pyqtSlot()
    def _slot_post_frameDisplay(self):
        self._align_X_range()
        self._update_axes_spines_()
        
        
    def _align_X_range(self, padding:typing.Optional[float] = None):
        """ Maintains an X view range for frames with different X data bounds.
    Necessary to recreate a view range to an axis relative to the axis' X data.
        
    This is intended for the particular case where the X domain in each 'frame' 
    starts at different values (e.g. sweep 0 starts at time 0 s, sweep 1 starts
    at 5 s etc). In this case "zooming" in on a signal feature in sweep 0 would 
    set a view range (in PyQtGraph) falling outside the domain of sweep 1, and so
    on.
        
    This unwanted effect can be prevented by recalculating the X range of the 
    view based on the current X bounds and the previous view range, via two
    intermediate values which are independent of the actual sweep X domain:
    • offset (the difference between the data X start and the view range X start)
    • scale (> 1 if the view range is larger that the X data range).
    
    WARNING: Works best - and is useful- when X data ranges for the plotted 
    curves in distinct frames are similar, if not identical, even though they 
    start at distinct values.
    
    CAUTION: For best result ensure all axes (Plotitem objects) in the SignalViewer
    are linked.
        
        """
        if len(self.axes) == 0:
            return
        
        # if len(self.signalAxes) == 0:
        #     refAxes = self.axes
        # else:
        #     refAxes = self.signalAxes
            
        # print(f"{self.__class__.__name__}._align_X_range {len(self._x_data_bounds_)}")
        self._x_data_bounds_ = [self._get_axis_data_X_range_(ax) for ax in self.axes]
        # if len(self._x_data_bounds_) == 0:
        #     self._x_data_bounds_ = [self._get_axis_data_X_range_(ax) for ax in self.axes]
            # self._x_data_bounds_ = [self._get_axis_data_X_range_(ax) for ax in refAxes]
            
        # print(f"{self.__class__.__name__}._align_X_range x data bounds {list(zip([self.axes.index(ax) for ax in self.axes] ,self._x_data_bounds_))}")
            
        for ax in self.axes:
            ax.vb.updateViewRange(True, True)
        
        
        # print(f"{self.__class__.__name__}._align_X_range axeslinked = {self.xAxesLinked}")
        if self.xAxesLinked: # ← True when ALL axes but one are linked on X (either pairwise or to a common target)
            # if any(ax.vb.autoRangeEnabled()[0] for ax in self.signalAxes):
            if any(ax.vb.autoRangeEnabled()[0] for ax in self.axes):
                return
            # NOTE: 2023-07-10 10:55:57 FIXME/TODO
            # still have to figure to figure out this contingency below:
            # selecting to show just plot items without autoranging
            # does not respect the view range previously set by the link target !!!
            
#                 # get the axis which is auto-range enabled on X
#                 # autoXaxes = [ax for ax in self.axes if ax.vb.autoRangeEnabled()[0]]
#                 
#                 xLinkAxes = list()
#                 xLinks = [ax.vb.linkedView(0) for ax in self.axes if isinstance(ax.vb.linkedView(0), pg.ViewBox)]
#                 if len(xLinks): # is this guaranteed to happen ?!?
#                     xLinkAxes = list(set([[_ax for _ax in self.axes if _ax.vb == xLink][0] for xLink in xLinks]))
#                     
#                 # figure out the following:
#                 # • if an axis is auto-ranged on X ⇒ continue; else:
#                 #   ∘ if an axis is X-linked to a target, get the target's viewXrange
#                 #       and apply it to the axis; else:
#                 #   ∘ get the topmost X-link target viewX range and apply it to 
#                 #       the axis
#                 
#                 for kax, ax in enumerate(self.axes):
#                     if ax.vb.autoRangeEnabled()[0]: # ← skip axes auto-ranged on X
#                         continue
#                     bounds = self._get_axis_data_X_range_(ax)
#                     if any(np.isnan(v) for v in bounds): # ← no data
#                         continue
#                     xLink = ax.vb.linkedView(0)
#                     if not isinstance(xLink, pg.ViewBox):
#                         # get the topmost xLink if this is NOT a linked axis
#                         # (might happen when individual axes are manually unlinked
#                         # but self._xAxesLinked_ is not updated, yet there still
#                         # are at least one link target in the axes)
#                         xLinkNdx = min([self.axes.index(a) for a in xLinkAxes])
#                         xLinkAxis = self.axes[xLinkNdx]
#                         xLink = xLinkAxis.vb
#                         
#                     xLinkViewXrange = xLink.viewRange()[0]
#                     xLinkAxes = [a for a in self.axes if a.vb == xLink]
#                     if len(xLinkAxes) == 0:
#                         continue # shouldn't happen
#                     xLinkAxis = xLinkAxes[0]
#                     xLinkAxNdx = self.axes.index(xLinkAxis)
#                     xLinkXBounds = self._get_axis_data_X_range_(xLinkAxis)
#                     print(f"{kax} bounds {bounds} link {xLinkAxNdx} link X bounds {xLinkXBounds} link Xview {xLinkViewXrange} ")
#                     offset, scale = self._axes_X_view_offsets_scales_[xLinkAxNdx]
#                     if any(np.isnan(v) for v in (offset, scale)):
#                         offset, scale = self._calculate_new_X_offset_scale_(xLinkXBounds, xLinkViewXrange)
#                     x0,x1 = bounds
#                     dx1 = x1-x0
#                     new_vx0 = x0 - offset
#                     new_view_dx = dx1 * scale
#                     new_vx1 = new_vx0 + new_view_dx
#                     print(f"offset = {offset}, scale = {scale}, dx1 = {dx1}, new_vx0 = {new_vx0}, new_view_dx = {new_view_dx}, new_vx1 = {new_vx1}")
#                     ax.vb.setXRange(new_vx0, new_vx1, padding=0., update=True)
#                     self._axes_X_view_ranges_[kax] = (new_vx0, new_vx1)
#                 return
                
        # NOTE: 2023-10-05 08:46:25
        # another poss workaround to try: use the first visible signal axis
        #
        visibleSignalAxes = [ax for ax in self.signalAxes if ax.isVisible()]
        
        if len(visibleSignalAxes):
            refAxis = visibleSignalAxes[0]
        else:
            refAxis = None
        
        for kax, ax in enumerate(self.axes):
            # if ax not in self.signalAxes:
            #     continue
            # NOTE: 2023-07-10 10:51:10
            # this loop OK when auto-ranging is disabled across plot items
            # such as in the case of mouse interaction
            # still a BUG when showing a linked plot item without its link
            # target
            # having them linked still messes up the display of linked plot item
            # (not target) in isolation
            # WORKAROUND: for this to work the link target MUST ALSO BE VISIBLE
            # NOTE: 2023-07-09 21:17:19
            # this returns the actual data X bounds (see NOTE: 2023-07-09 21:09:08)
            current_X_bounds = self._get_axis_data_X_range_(ax)
            # print(f"{self.__class__.__name__}._align_X_range: axis {kax} current X bounds = {current_X_bounds}")
            if any(np.isnan(v) for v in current_X_bounds): # ← no data !
                continue
            
            xLinkAxis = None
            xLinkAxisNdx = None
            xLinkXBounds = None
            xLinkViewXrange = None
            xLink = ax.vb.linkedView(0)
            if isinstance(xLink, pg.ViewBox):
                aa = [a for a in self.axes if a.vb == xLink]
                # if xLink.isVisible():
                #     aa = [a for a in self.axes if a.vb == xLink]
                # else:
                #     # continue
                #     if isinstance(refAxis, pg.PlotItem):
                #         aa = [refAxis]
                    
                ax.vb.blockLink(True)
                xLink.blockLink(True)
                
                if len(aa):
                    xLinkAxis = aa[0]
                    xLinkAxisNdx = self.axes.index(xLinkAxis)
                    xLinkXBounds = self._get_axis_data_X_range_(ax)
                    xLinkViewXrange = xLink.viewRange()[0]
                        
            current_viewXrange = ax.vb.viewRange()[0] if xLinkViewXrange is None else xLinkViewXrange
            
            offset, scale = self._axes_X_view_offsets_scales_[kax] # if xLinkAxisNdx is None else self._axes_X_view_offsets_scales_[xLinkAxisNdx] # ← set by _slot_plot_axis_x_range_changed
            view_dx = current_viewXrange[1] - current_viewXrange[0]
            x0,x1 = current_X_bounds if xLinkXBounds is None else xLinkXBounds
            dx1 = x1-x0
            new_vx0 = x0 - offset
            new_view_dx = dx1 * scale
            new_vx1 = new_vx0 + new_view_dx
            
            if any(a!=b for a,b in zip(current_viewXrange, (new_vx0, new_vx1))):
                # print(f"{self.__class__.__name__}._align_X_range: Axis {kax} ({ax.vb.name}) view range from {current_viewXrange} to: {new_vx0, new_vx1}")
                ax.vb.setXRange(new_vx0, new_vx1, padding = 0., update=True)
                if isinstance(xLink, pg.ViewBox):
                    ax.vb.blockLink(False)
                    xLink.blockLink(False)
                self._axes_X_view_ranges_[kax] = (new_vx0, new_vx1)

    def _update_axes_spines_(self):
        visibleAxes = [ax for ax in self.axes if ax.isVisible()]
        
        if len(visibleAxes) == 0:
            return
        
        for k, ax in enumerate(self.axes):
            if k > 0:
                ndx = k-1
                prev_ax = None
                while ndx >= 0:
                    prev_ax = self.axes[ndx]
                    if prev_ax.isVisible():
                        break
                    ndx -= 1
                    if ndx < 0:
                        break
                
                if prev_ax is None or not prev_ax.isVisible():
                    continue
                
                sameLabel = ax.getAxis("bottom").labelText == prev_ax.getAxis("bottom").labelText

                prev_ax.getAxis("bottom").showLabel(not sameLabel)
                prev_ax.getAxis("bottom").setStyle(showValues=False)

                # ax.getAxis("left").setWidth(60)
                
                # if ax in axes_with_X_overlap: # also hide axis values if same boundaries
                #     prev_ax.getAxis("bottom").setStyle(showValues=False)
        
        visibleAxes[-1].getAxis("bottom").showLabel(True)
        visibleAxes[-1].getAxis("bottom").setStyle(showValues = True)
        
    @safeWrapper
    def _plotSpikeTrains_(self, trains:typing.Optional[typing.Union[neo.SpikeTrain, neo.core.spiketrainlist.SpikeTrainList, tuple, list]] = None, clear:bool = False, plotLabelText = None, **kwargs):
        """Common landing zone for SpikeTrainList or collection of SpikeTrain.
        Actual plotting delegated to _plot_discrete_entities_.
        """
        # plot all spike trains stacked in a single axis
        if self._plot_spiketrains_:
            if isinstance(trains, neo.SpikeTrain):
                if self.ignoreEmptySpikeTrains and len(trains) == 0:
                    self.spikeTrainsAxis.setVisible(False)
                    return
                    
                obj_ = [trains]
            
            elif self.ignoreEmptySpikeTrains:
                obj_ = get_non_empty_spike_trains(trains)
            else:
                obj_ = trains
                
            if len(obj_):
                # NOTE: 2023-05-16 23:02:20:
                # is this is a new frame, then call the actual function (_plot_discrete_entities_)
                # otherwise, just set the entities axis visible
                if self._new_frame_:
                    self._plot_discrete_entities_(obj_, axis=self._spiketrains_axis_, **kwargs)
                    
                    self._spiketrains_axis_.update()
                    
                self.spikeTrainsAxis.setVisible(True)
            else:
                self.spikeTrainsAxis.setVisible(False)
        else:
            self.spikeTrainsAxis.setVisible(False)
                

    @safeWrapper
    def _plotEvents_(self, events: typing.Optional[typing.Union[typing.Sequence[neo.Event], typing.Sequence[DataMark]]] = None, 
                     plotLabelText=None, **kwargs):
        """ Common landing zone for Event/DataMark plotting 
        Delegates further to _plot_discrete_entities_
        """
        if self._plot_events_:
            if self._new_frame_: # NOTE: 2023-05-16 23:04:37
                self._events_axis_.clear()
                if events is None or isinstance(events, (tuple, list)) and len(events) == 0:
                    self._events_axis_.setVisible(False)
                    return
                # kwargs["adapt_X_range"] = True
                minX = kwargs.pop("minX", None)
                maxX = kwargs.pop("maxX", None)
                
                self._plot_discrete_entities_(events, axis=self._events_axis_, minX = minX, maxX = maxX, **kwargs)
                self._events_axis_.update() 
                
            self._events_axis_.setVisible(True)
                
        else:
            self._events_axis_.setVisible(False)
            
        # events_dict = self._prep_entity_dict_(events, (neo.Event, DataMark))
        

    def _plot_epoch_data_(self, epoch:neo.Epoch, **kwargs):
        """ Plots the time intervals defined in a single neo.Epoch or DataZone """
        brush = kwargs.pop("brush", self.epoch_plot_options["epoch_brush"])
        
        x0 = epoch.times.flatten().magnitude
        x1 = x0 + epoch.durations.flatten().magnitude
        
        # brush = next(brushes)
        
        for k in range(len(self.axes)):
            self.axes[k].update() # to update its viewRange()
            
            regions = [v for v in zip(x0,x1)]
            
            lris = [pg.LinearRegionItem(values=value, 
                                        brush=brush, 
                                        orientation=pg.LinearRegionItem.Vertical, 
                                        movable=False, **kwargs) for value in regions]
            
            for kl, lri in enumerate(lris):
                self.axes[k].addItem(lri)
                lri.setZValue(10)
                lri.setVisible(True)
                lri.setRegion(regions[kl])
    

    def _plot_epochs_sequence_(self, *args, **kwargs):
        """Plots data from a sequence of neo.Epochs.
        Epochs is always a non-empty sequence (tuple or list) of neo.Epochs
        We keep this as a nested function to avoid calling it directly. Thus
        there is no need to check if the epochs argument is the same as 
        self._yData_ (or contained within)
        """
        
        # print(f"SignalViewer._plot_epochs_sequence_ {args}")
        
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
            brush = next(brushes)
            self._plot_epoch_data_(epoch, brush)
#             # print(f"SignalViewer._plot_epochs_sequence_ epoch times {epoch.times} durations {epoch.durations}")
#             x0 = epoch.times.flatten().magnitude
#             x1 = x0 + epoch.durations.flatten().magnitude
#             
#             brush = next(brushes)
#             
#             for k in range(len(self.axes)):
#                 self.axes[k].update() # to update its viewRange()
#                 
#                 regions = [v for v in zip(x0,x1)]
#                 
#                 lris = [pg.LinearRegionItem(values=value, 
#                                             brush=brush, 
#                                             orientation=pg.LinearRegionItem.Vertical, 
#                                             movable=False) for value in regions]
#                 
#                 for kl, lri in enumerate(lris):
#                     self.axes[k].addItem(lri)
#                     lri.setZValue(10)
#                     lri.setVisible(True)
#                     lri.setRegion(regions[kl])
        
#     @safeWrapper
#     def _plotEpochs_(self, epochs: typing.Optional[typing.Union[neo.Epoch, DataZone, typing.Sequence]] = None, clear: bool = True, from_cache: bool = False, plotLabelText=None, **kwargs):
#         """Plots stand-alone epochs.
#         A neo.Epoch contains time intervals each defined by time and duration.
#         Epoch intervals are drawn using pyqtgraph.LinearRegionItem objects.
#         
#         Parameters:
#         ------------
#         
#         epochs: neo.Epoch or a sequence (tuple, or list) of neo.Epoch objects,
#             or None (default).
#             
#             The behaviour of this function depends on whether the signal viewer 
#             was set to plot standalone epoch data (i.e. epoch data NOT associated
#             with a neo Segment, or with anything else).
#             
#             FIXME: Standalone epoch data is an Epoch or sequence of Epoch objects
#             passed as the 'y' parameter to self.setData(...) function
#             (NOTE that self.setData is aliased to 'self.plot' and 'self.view').
#             
#             When the 'epochs' parameter is None or an empty sequence, the 
#             function plots the standalone epoch data, if it exists, or clears
#             any representations of previous epoch data from all axes.
#             
#         clear: bool, default is True.
#             When True, all representations of epochs data are cleared from the
#             axes, regardless if there exists standalone epoch data.
#             
#             Otherwise new epochs are added to the plot.
#             
#         from_cache: bool, default is False:
#             When True, plots internally cached epochs
#         
#         """
#         
#         # print(f"SignalViewer _plotEpochs_ epochs: {epochs}; cached: {self._cached_epochs_}")
#         
#         # BEGIN plot epochs from cache (containing standalone epoch data), if any and if requested
#         
#         if from_cache:
#             epoch_seq = self._cached_epochs_.get(self.currentFrame, None)
#             
#             # BEGIN plot epochs from cache: clear current displayed epoch if requested
#             # if epoch_seq is not None and clear:
#             if clear:
#                 for k, ax in enumerate(self.axes):
#                     lris = [i for i in ax.items if isinstance(i, pg.LinearRegionItem)]
#                     for l in lris:
#                         ax.removeItem(l)
#             
#             # END plot epochs from cache: clear current displayed epoch if requested
#             
#             self._plot_epochs_sequence_(*epoch_seq, **kwargs)
#                 
#             if not isinstance(self.docTitle, str) or len(self.docTitle.strip()) == 0:
#                 self.docTitle = "Epochs"
#                 
#             return
#                 
#         # END plot epochs from cache (containing standalone epoch data), if any and if requested
#             
#         # BEGIN plot supplied epoch
#         # BEGIN clear current epoch display if requested
#         if clear:
#             for k, ax in enumerate(self.axes):
#                 lris = [i for i in ax.items if isinstance(i, pg.LinearRegionItem)]
#                 for l in lris:
#                     ax.removeItem(l)
#         # END clear current epoch display if requested
#         
#         epoch_seq = list()
#         # END plot supplied epoch
#         
#         if epochs is None or len(epochs) == 0:
#             # None, an empty sequence of epochs or an empty epoch
#             if isinstance(self._yData_, neo.Epoch):
#                 # self._prepareAxes_(1) # use a brand new single axis
#                 epoch_seq = [self._yData_]
#                 
#             elif isinstance(self._yData_, typing.Sequence) and all([isinstance(y_, (neo.Epoch, DataZone)) for y_ in self._yData_]):
#                 # self._prepareAxes_(1) # use a brand new single axis
#                 epoch_seq = self._yData_
#                 
#         elif isinstance(epochs, (neo.Epoch, DataZone)):
#             epoch_seq = [epochs]
#             
#         elif isinstance(epochs, typing.Sequence):
#             if all([isinstance(e, (neo.Epoch, DataZone)) for e in epochs]):
#                 epoch_seq = epochs
#                 
#             else:
#                 # NOTE: 2020-10-27 09:19:26
#                 # some of these may be relics from old API (i.e., neoepoch.Epoch)
#                 # therefore we try to salvage them
#                 epoch_seq = list()
#                 
#                 for e in epochs:
#                     if isinstance(e, (neo.Epoch, DataZone)):
#                         epoch_seq.append(e)
#                         
#         else:
#             raise TypeError("Expecting a neo.Epoch or a Sequence of neo.Epoch objects; got %s instead" % type(epochs).__name__)
#         
#         if len(epoch_seq):
#             self._plot_epochs_sequence_(*epoch_seq, **kwargs)
#             
#             if self.currentFrame in self._cached_epochs_:
#                 if len(self._cached_epochs_[self.currentFrame]):
#                     if clear:
#                         self._cached_epochs_[self.currentFrame] = epoch_seq
#                         
#                     else:
#                         self._cached_epochs_[self.currentFrame] += epoch_seq
#                         
#             if not isinstance(self.docTitle, str) or len(self.docTitle.strip()) == 0:
#                 self.docTitle = "Epochs"
#                 
#         else:
#             # clear cache when no epochs were passed
#             self._cached_epochs_.pop(self.currentFrame, None)
#                     
#         if isinstance(plotLabelText, str) and len(plotLabelText.strip()):
#             self.plotTitleLabel.setText(plotLabelText, color = "#000000")
#             

    @singledispatchmethod
    def _plot_data_(self, obj, *args, **kwargs):
        raise NotImplementedError(f"Objects of type {type(obj).__name__} are not supported")
    
    @_plot_data_.register(neo.Block)
    def _(self, obj, *args, **kwargs):
        # NOTE: 2019-11-24 22:31:26
        # select a segment then delegate to _plotSegment_()
        # Segment selection is based on self.frameIndex, or on self.channelIndex
        # NOTE 2021-10-03 12:59:10 ChannelIndex is no more
        
        # print(f"{self.__class__.__name__}._plot_data_({type(self._yData_).__name__})")
        if len(obj.segments) == 0:
            return
        
        if self._current_frame_index_ not in self.frameIndex:
            return
        
        segmentNdx = self.frameIndex[self._current_frame_index_]
        
        if segmentNdx >= len(self._yData_.segments):
            # print(f"{self.__class__.__name__}._plot_data_({type(self._yData_).__name__}) no plot")
            return
        
        segment = obj.segments[segmentNdx]
        
        # NOTE: 2023-01-03 22:53:13 
        # singledispatchmethod here
        self._plot_data_(segment, *self.plot_args, **self.plot_kwargs) 
        
        self.currentFrameAnnotations = {type(segment).__name__ : segment.annotations}
    
    @_plot_data_.register(neo.Segment)
    def _(self, obj:neo.Segment, *args, **kwargs):
        """Plots a neo.Segment.
        Plots the signals (optionally the selected ones) present in a segment, 
        and the associated epochs, events, and spike trains.
        """
        analog = obj.analogsignals
        irregs = obj.irregularlysampledsignals
        spiketrains = get_non_empty_spike_trains(obj.spiketrains)
        events = get_non_empty_events(obj.events)
        epochs = get_non_empty_epochs(obj.epochs)
        plotTitle = kwargs.pop("plotTitle", getattr(obj, "name", "Segment"))
        
        self._plot_signals_(analog, irregs, *args, **kwargs)
        
        if len(events):
            self._plotEvents_(events, **kwargs)
        else:
            self.eventsAxis.setVisible(False)
            
        if len(spiketrains):
            self._plot_data_(spiketrains, *args, **kwargs)
        else:
            self.spikeTrainsAxis.setVisible(False)
            
        if self._plot_epochs_ and len(epochs):
            self._plot_data_(epochs)
        else:
            self._clear_lris_()
            
        # NOTE: 2023-01-16 22:59:30 TODO:
        # delegate this to _plot_signals_
        # where you should test for adjacent plotItems with the same labelText 
        # for their getAxis("bottom"); for contiguous runs of plotItems with 
        # identical x labels, set this label invisible except for the last plotItem
        # in the run
        #
        # do the same for irregular signal as well
        #
        # this is so that signals with different domains get their proper
        # x axis label
        #
        # in fact extend this idea to ALL axes
        visibleAxes = [i for i in self.signalAxes if i.isVisible()]
        
        seg_name = getattr(obj, "name", "")
        
        if not isinstance(plotTitle, str) or len(plotTitle.strip()) == 0:
            self.plotTitleLabel.setText(seg_name, color = "#000000")
                
        else:
            self.plotTitleLabel.setText(plotTitle, color = "#000000")
                
        if not isinstance(self.docTitle, str) or len(self.docTitle.strip()) == 0:
            self.docTitle = seg_name
            
        self.currentFrameAnnotations = {type(obj).__name__ : obj.annotations}
        
    @_plot_data_.register(neo.core.spiketrainlist.SpikeTrainList)
    def _(self, obj:neo.core.spiketrainlist.SpikeTrainList, *args, **kwargs):
        self._plotSpikeTrains_(obj)
        self.currentFrameAnnotations = {type(obj).__name__: [st.annotations for st in obj]}
                
    @_plot_data_.register(neo.SpikeTrain)
    def _(self, obj, *args, **kwargs):
        self._plotSpikeTrains_(obj)
        self.currentFrameAnnotations = {type(obj).__name__: obj.annotations}
        
    @_plot_data_.register(neo.AnalogSignal)
    @_plot_data_.register(neo.IrregularlySampledSignal)
    @_plot_data_.register(DataSignal)
    @_plot_data_.register(IrregularlySampledDataSignal)
    def _(self, obj, *args, **kwargs):
        if self.frameAxis == 1:
            if self._current_frame_index_ in self.frameIndex:
                ndx = self.frameIndex[self._current_frame_index_]
            else:
                self._current_frame_index_ = 0
                ndx = 0
            
            self._plot_signal_(obj[:,ndx], *args, **kwargs)
            annotations = getattr(obj[:,ndx], "annotations", dict())
            self.currentFrameAnnotations = {type(obj[:,ndx]).__name__: annotations}
        else:
            self._plot_signal_(obj, *args, **kwargs)
            self.currentFrameAnnotations = {type(obj).__name__: obj.annotations}
            
    @_plot_data_.register(neo.Epoch)
    @_plot_data_.register(DataZone)
    def _(self, obj, *args, **kwargs):
        """ Plots a single neo.Epoch 
        NOTE: a single Epoch MAY contain several time intervals.
        """
        clear_epochs = kwargs.get("clear", True)
        if clear_epochs:
            self._clear_lris_()
            
        epoch_pen = kwargs.pop("epoch_pen", self.epoch_plot_options["epoch_pen"])
        epoch_brush = kwargs.pop("epoch_brush", self.epoch_plot_options["epoch_brush"])
        epoch_hoverPen = kwargs.pop("epoch_hoverPen", self.epoch_plot_options["epoch_hoverPen"])
        epoch_hoverBrush = kwargs.pop("epoch_hoverBrush", self.epoch_plot_options["epoch_hoverBrush"])
        
        self._plot_epoch_data_(epoch, brush=epoch_brush, pen=epoch_pen,
                               hoverBrush=epoch_hoverBrush,
                               hoverPen = epoch_hoverPen)
        
        self.currentFrameAnnotations = {type(obj).__name__: obj.annotations}
        
    @_plot_data_.register(neo.Event)
    @_plot_data_.register(DataMark)
    def _(self, obj, *args, **kwargs):
        """Plot stand-alone events"""
        if len(obj) == 0:
            self._events_axis_.clear()
            self._events_axis_.setVisible(False)
        else:
            self._plotEvents_(obj)
            
        self.currentFrameAnnotations = {type(obj).__name__: obj.annotations}
            
    @_plot_data_.register(np.ndarray)
    def _(self, obj, *args, **kwargs):
        # print(f"{self.__class__.__name__}._plot_data_(obj<{type(obj).__name__}> dims: {obj.ndim})")
        try:
            if obj.ndim > 3:
                raise TypeError("Numpy arrays with more than three dimensions are not supported")

            if obj.ndim <= 1 :
                self._plotNumpyArray_(self._xData_, obj, self.signalAxis(0),
                                      *args, **kwargs)
                
            elif obj.ndim == 2 :
                if self.separateSignalChannels:
                    if self.frameAxis is None:
                        # for kchn, chNdx in enumerate(self.signalChannelIndex):
                        #     y_ = obj[array_slice(obj, {self.signalChannelAxis, chNdx})]
                        for k, ax in enumerate(self.signalAxes):
                            ndx = array_slice(obj, {self.signalChannelAxis: k})
                            self._plotNumpyArray_(self._xData_, obj[ndx], ax,
                                                  *args, **kwargs)
                            
                    elif self.frameAxis == self.signalChannelAxis:
                        if self._current_frame_index_ not in self.frameIndex:
                            return
                        ndx = array_slice(obj, {self.frameAxis: self._current_frame_index_})
                        self._plotNumpyArray_(self._xData_, obj[ndx],
                                              self.signalAxis(0), 
                                              *args, **kwargs)
                        
                else:
                    if self.frameAxis is None:
                        if self.signalChannelAxis == 0:
                            self._plotNumpyArray_(self._xData_, obj.T, self.signalAxis(0),
                                                *args, **kwargs)
                        else:
                            self._plotNumpyArray_(self._xData_, obj, self.signalAxis(0),
                                                *args, **kwargs)
                            
                        
                    else:
                        ndx = array_slice(obj, {self.frameAxis: self._current_frame_index_})
                        self._plotNumpyArray_(self._xData_, obj[ndx],
                                              self.signalAxis(0),
                                              *args, **kwargs)
                        
            else: # 3 dims
                slicer = {self.frameAxis: self._current_frame_index_}
                if self.separateSignalChannels:
                    for kchn, chNdx in enumerate(self.signalChannelIndex):
                        slicer[self.signalChannelAxis] = chNdx
                        self._plotNumpyArray_(self._xData_, obj[slicer],
                                              self.signalAxis(kchn),
                                              *args, **kwargs)
                else:
                    self._plotNumpyArray_(self._xData_, obj[slicer],
                                          self.signalAxis(0),
                                          *args, **kwargs)
                
        except Exception as e:
            traceback.print_exc()
            
        self.currentFrameAnnotations = dict()
            
    @_plot_data_.register(type(None))
    def _(self, obj, *args, **kwargs):
        pass
    
    @_plot_data_.register(tuple)
    @_plot_data_.register(list)
    def _(self, obj, *args, **kwargs):
        if len(obj) == 0:
            return False
        
        if self._current_frame_index_ not in self.frameIndex:
            return
        
        dataFrameNdx = self.frameIndex[self._current_frame_index_]
        
        if all([isinstance(y_, (DataSignal, 
                                neo.core.AnalogSignal, 
                                neo.core.IrregularlySampledSignal,
                                IrregularlySampledDataSignal)) for y_ in obj]):
            
            if self.frameAxis == 1:
                self._plot_signal_(obj[dataFrameNdx])
                self.currentFrameAnnotations = {type(obj[dataFrameNdx]).__name__: getattr(obj[dataFrameNdx], "annotations", dict())}
                return
            
            analog = [s for s in obj if isinstance(s, (neo.AnalogSignal, DataSignal))]
            
            analog_anns = [s.annotations for s in analog]
            
            irregs = [s for s in obj if isinstance(s, (neo.IrregularlySampledSignal, IrregularlySampledDataSignal))]
            
            irreg_anns = [s.annotations for s in irregs]
            
            self._plot_signals_(analog, irregs, *args, **kwargs)
            
            self.spikeTrainsAxis.setVisible(False)
            self.eventsAxis.setVisible(False)
            self.currentFrameAnnotations = {type(obj).__name__: {"analog": analog_anns, "irregs": irreg_anns}}
            
        elif all([isinstance(y_, (neo.Event, DataMark)) for y_ in obj]):
            self._plotEvents_(obj, *args, **kwargs)
            self.currentFrameAnnotations = {type(obj).__name__: [getattr(y_, "annotations", dict()) for y_ in obj]}
            
        elif all([isinstance(y_, (neo.core.Epoch, DataZone)) for y_ in obj]): 
            # print(f"{self.__class__.__name__}._plot_data_(obj<{type(obj).__name__}>)")
            clear_epochs = kwargs.get("clear", True)
            
            if clear_epochs:
                self._clear_lris_()
            
            epoch_pen = kwargs.pop("epoch_pen", self.epoch_plot_options["epoch_pen"])
            # epoch_brush = kwargs.pop("epoch_brush", self.epoch_plot_options["epoch_brush"])
            epoch_brush = kwargs.pop("epoch_brush", None)
            epoch_hoverPen = kwargs.pop("epoch_hoverPen", self.epoch_plot_options["epoch_hoverPen"])
            epoch_hoverBrush = kwargs.pop("epoch_hoverBrush", self.epoch_plot_options["epoch_hoverBrush"])
        
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
                    # warnings.warn("Invalid brush specification %s" % epoch_brush)
                    brushes = cycle([QtGui.QBrush(QtGui.QColor(*c)) for c in self.epoch_plot_options["epochs_color_set"]])
                    
            for epoch in obj:
                brush = next(brushes)
                self._plot_epoch_data_(epoch, brush=brush,**kwargs)
                
            self.currentFrameAnnotations = {type(obj).__name__: [getattr(y_, "annotations", dict()) for y_ in obj]}
            
        elif all([isinstance(y_, neo.Segment) for y_ in obj]):
            segment = obj[self.frameIndex[self._current_frame_index_]]
            self._plot_data_(segment, *args, **kwargs)
            self.currentFrameAnnotations = {type(obj).__name__: [getattr(y_, "annotations", dict()) for y_ in obj]}
            
        elif all([isinstance(y_, neo.Block) for y_ in obj]):
            frIndex = self.frameIndex[self._current_frame_index_]
            
            frame = self._meta_index[frIndex]
            
            (blockIndex, blockSegmentIndex) = int(frame.block), int(frame.segment)
            
            segment = obj[blockIndex].segments[blockSegmentIndex]
            
            plotTitle = "Block %d (%s), segment %d (%s)" % (blockIndex, obj[blockIndex].name,
                                                            blockSegmentIndex, segment.name)
            
            kwargs = dict()
            kwargs.update(self.plot_kwargs)
            kwargs["plotTitle"] = plotTitle
            
            self._plot_data_(segment, *args, **kwargs)
            
            self.currentFrameAnnotations = {type(obj).__name__: [getattr(y_, "annotations", dict()) for y_ in obj]}
            
        elif all(isinstance(y_, neo.SpikeTrain) for y_ in obj):
            self._plotSpikeTrains_(obj, *args, **kwargs)
            self.currentFrameAnnotations = {type(obj).__name__: [getattr(y_, "annotations", dict()) for y_ in obj]}
        
        else: # accepts sequence of np.ndarray (VigraKernel1D objects are converted to np arrays by _parse_data_)
            # FIXME - in progress 2023-01-19 08:17:18
            if not all(isinstance(v, np.ndarray) for v in obj):
                self.criticalMessage("Plot data:", "Incompatible element types in the sequence")
                return
            
            frIndex = self.frameIndex[self._current_frame_index_]
            
            if isinstance(self._xData_, (tuple ,list)):
                if len(self._xData_) != len(obj):
                    raise ValueError(f"X, Y Sequence length mismatch x: {len(self._xData_)}; obj: {len(obj)}")
                
            if self.frameAxis is None:
                if all(y.ndim == 1 for y in obj):
                    if self.separateSignalChannels:
                        for ky, y in enumerate(obj):
                            if isinstance(self._xData_, (tuple, list)):
                                x = self._xData_[ky]
                            else:
                                x = self._xData_
                                        
                            self._plotNumpyArray_(x, y, self.signalAxes[ky], *args, **kwargs)
                            
                        for ax in self.signalAxes[len(obj):]:
                            ax.setVisible(False)
                    else:
                        if isinstance(self._xData_, (tuple, list)):
                            x = self._xData_[frIndex]
                        else:
                            x = self._xData_
                            
                        self._plotNumpyArray_(x, obj[frIndex], self.signalAxes[0],
                                              *args, **kwargs)
                        
                    return True
                        
            y = obj[frIndex]
            
            if isinstance(self._xData_, (tuple, list)):
                x = self._xData_[frIndex]
            else:
                x = self._xData_
                
            if y.ndim == 1:
                self._setup_signal_choosers_(analog = [y])
                
                self._plotNumpyArray_(x,y, self.signalAxes[0],
                                    *args, **kwargs)
                
                # self.signalAxes[0].setVisible(True) # called by _plotNumpyArray_
                    
                for ax in self.signalAxes[1:]:
                    ax.setVisible(False)
            
            elif y.ndim == 2:
                if self.separateSignalChannels:
                    self._setup_signal_choosers_(analog = list(y[array_slice(y, {self.signalChannelAxis:k})] for k in range(y.shape[self.signalChannelAxis])))
                    # for k, ax in self.signalAxes:
                    for k in range(y.shape[self.signalChannelAxis]):
                        self._plotNumpyArray_(x, y[array_slice(y, {self.signalChannelAxis:k})],
                                            self.signalAxes[k]
                                            *args, **kwargs)
                        
                        # self.signalAxes[k].setVisible(True) # called by _plotNumpyArray_
                        
                    for ax in self.signalAxes[y.shape[self.signalChannelAxis]:]:
                        ax.setVisible(False)
                        
                else:
                    self._plotNumpyArray_(x, y, self.signalAxis(0), *args, **kwargs)
                    for ax in self.signalAxes[1:]:
                        ax.setVisible[False]
                    
            else:
                return False
            self.currentFrameAnnotations = {type(obj).__name__: dict()}
        return True
    
    def _register_plot_item_name_(self, plotItem, name):
        old_name = plotItem.vb.name
        if isinstance(old_name, str):
            self._unregister_plot_item_name_(plotItem, old_name)
            
        plotItem.register(name)
    
    def _unregister_plot_item_name_(self, plotItem, entry):
        vb = plotItem.getViewBox()
        if entry in pg.ViewBox.NamedViews:
            del pg.ViewBox.NamedViews[entry]
        vb.name = None
    
    def _signals_select_(self, signals, signalCBox):
        """Helper method for setting up the collection of selected signals to plot.
        Selection is based on the GUI combo box passed as 2nd parameter to the call.
        signals: collection of signals in a frame
        signalCBox: the combo box for selecting which signal to plot, in GUI
        """
        if signalCBox == self.analogSignalComboBox:
            guiSelection = self.guiSelectedAnalogSignalEntries
            mapping = self._frame_analog_map_
        else:
            guiSelection = self.guiSelectedIrregularSignalEntries
            mapping = self._frame_irregs_map_
            
        # cname = "Analog" if signalCBox == self.analogSignalComboBox else "Irregular"
        # print(f"{self.__class__.__name__}._signals_select_ {cname} guiSelection = {guiSelection}")
        
        selected_signals = list()
        selected_signal_names = list()
        selected_signal_ndx = list()
        selected_signal_axis_names = list()
        
        if len(guiSelection):
            selected_signal_axis_names = guiSelection
            selected_signal_ndx, selected_signal_names = zip(*list(mapping[k] for k in selected_signal_axis_names if k in mapping ))
            # selected_signal_ndx = [mapping[k][0] for k in guiSelection]
            if len(selected_signal_ndx):
                selected_signals = [signals[ndx] for ndx in selected_signal_ndx]
            else:
                selected_signals = signals[:]
                
            
        else:
            selected_signals[:] = signals[:]
            selected_signal_ndx = range(len(signals))
            selected_signal_names = list(x[1] for x in mapping.values())
            selected_signal_axis_names = list(mapping.keys())
        
        current_ndx = signalCBox.currentIndex() 
        current_txt = signalCBox.currentText()
        # print(f"{self.__class__.__name__}._signals_select_ {cname} current_ndx = {current_ndx}, current_txt = {current_txt}")
        
        return selected_signals, selected_signal_names, selected_signal_ndx, selected_signal_axis_names
    
    @safeWrapper
    def _plot_signals_(self, analog, irregs, *args, **kwargs):
        """Common landing zone for plotting collections (sequences) of signals.
        
        Signals are neo.AnalogSignal, DataSignal, neo.IrregularlySampledSignal
        and IrregularlySampledDataSignal objects.
        
        The collections are passed as part of a segment, or as standalone objects.
        
        NOTE: 2023-01-12 17:26:43
        To keep to code more manageable the possibility to plot each channel of 
        a multi-channel signal in its own frame or axis on the same frame has 
        been removed for multi channel signals when they are part of a collection.
        
        One channel - one axis is the golden rule here.
        
        """
        # print(f"{len(self.signalAxes)} signal axes, {len(analog)} analog, and {len(irregs)} irregs")
        if len(analog) + len(irregs) == 0:
            return None, None
        
        assert len(self.signalAxes) == len(analog) + len(irregs), "Mistmatch between number of signal axes and available signals"

        # NOTE: 2023-01-12 16:45:48
        # by convention, analog signals are plotted in order, BEFORE the 
        # irregularly sampled signals
        # 
        # so a mapping of signal index to axis index is used here for bookkeeping
        
        analog_ndx = range(len(analog))
        
        irregs_ndx = range(len(irregs))
        
        axes_ndx   = range(len(self.signalAxes))
        # say you have 5 analog signals and 3 irregularly sampled signals; this
        # means a total of eight signal axes
        
        # this gives somehting like {0: 0, 1: 1, 2: 2, 3: 3, 4: 4} (signal index ↦ axis index)
        analog_axes = dict(zip(analog_ndx, list(axes_ndx)[:len(analog_ndx)]))
        
        # this gives something like {0: 5, 1: 6, 2: 7} (signal index ↦ axis index)
        irregs_axes = dict(zip(irregs_ndx, list(axes_ndx)[len(analog_ndx):]))
        
        self._setup_signal_choosers_(analog = analog, irregular = irregs) 
        
        selected_analogs = list()
        selected_analog_names = list()
        selected_analog_ndx = list()
        
        selected_irregs = list()
        selected_irreg_names = list()
        selected_irreg_ndx = list()
        
        #### BEGIN plot regular (analog) signals
        # NOTE: update only those plotItems where a selected signal should be
        # all other plotItems are hidden
        if self._plot_analogsignals_: # flag set up by `Analog` checkbox
            selected_analogs, selected_analog_names, selected_analog_ndx, plotItemNames = self._signals_select_(analog, self.analogSignalComboBox)
            
            for k, signal in enumerate(analog):
                ax_ndx = analog_axes[k]
                plotItem = self.signalAxes[ax_ndx]
                if k in selected_analog_ndx:
                    plot_name_ndx = selected_analog_ndx.index(k)
                    # print(f"plotItemNames = {plotItemNames}")
                    plotItemName = plotItemNames[plot_name_ndx]
                    # NOTE: 2023-01-04 22:14:55
                    # avoid plotting if frame hasn't changed - just change plotItem's visibility
                    if self._new_frame_: 
                        sig_name = selected_analog_names[selected_analog_ndx.index(k)]
                        self._plot_signal_data_(signal, sig_name, plotItem, plotItemName, *args, **kwargs)
                        
                    plotItem.setVisible(True)
                    
                else:
                    plotItem.setVisible(False)
                    
        else: # hide all analog signal plotItems
            for ax_ndx in analog_axes.values():
                self.signalAxes[ax_ndx].setVisible(False)
        
        #### END plot regular (analog) signals
        
        #### BEGIN plot irregular signals
        if self._plot_irregularsignals_: # flag set up by `Irregular` checkbox
            selected_irregs, selected_irreg_names, selected_irreg_ndx, plotItemNames = self._signals_select_(irregs, self.irregularSignalComboBox)

            # kwargs["symbol"] = self.defaultIrregularSignalSymbols[0]
            kwargs["pen"] = None
            # kwargs["symbolPen"] = self.defaultIrregularSignalSymbolPen
            # kwargs["symbolBrush"] = self.defaultIrregularSignalSymbolBrush
            # kwargs["symbolSize"] = self.defaultIrregularSignalSymbolSize
            kwargs["pxMode"] = True
            
            for k, signal in enumerate(irregs):
                ax_ndx = irregs_axes[k]
                plotItem = self.signalAxes[ax_ndx]
                if k in selected_irreg_ndx:
                    plot_name_ndx = selected_irreg_ndx.index(k)
                    plotItemName = plotItemNames[plot_name_ndx]
                    if self._new_frame_: # NOTE: 2023-05-16 23:05:22
                        sig_name = selected_irreg_names[selected_irreg_ndx.index(k)]
                        self._plot_signal_data_(signal, sig_name, plotItem, plotItemName, *args, **kwargs)
            
                    plotItem.setVisible(True)
                else:
                    plotItem.setVisible(False)
        else:
            for ax_ndx in irregs_axes.values():
                self.signalAxes[ax_ndx].setVisible(False)

        #### END plot irregular signals
        
        # return minX, maxX # needed for events plotting - set the X range of their axis right
        
    @safeWrapper
    def _plotNumpyArrays_(self, x, y, plotLabelText = None, *args, **kwargs):
        """Plots several signals in one frame"""
        self._setup_signal_choosers_(analogs = [y]) # FIXME for a list of signals
        
        if not isinstance(y, (tuple, list)) or not all(isinstance(v, np.ndarray) for v in y):
            raise TypeError(f"_plotNumpyArrays_ expects a sequence (tuple, list) of numpy arrays")
        
        if isinstance (x, (tuple, list)):
            if len(x) not in (1,len(y)):
                raise ValueError(f"x sequence does not match y sequence")
            
        else:
            x = [x]
            
        for k, y_ in enumerate(y):
            if len(x) == 1:
                self._plotNumpyArray_(x[0], y_, self.plotItem(k))
                
            else:
                self._plotNumpyArray_(x[k], y_, self.plotItem(k))
            
        if isinstance(plotLabelText, str) and len(plotLabelText.strip()):
            self.plotTitleLabel.setText(plotLabelText, color = "#000000")
        else:
            self.plotTitleLabel.setText("", color = "#000000")
            
        if not isinstance(self.docTitle, str) or len(self.docTitle.strip()) == 0:
            self.docTitle = "Data arrays"
        
    @safeWrapper
    def _plotNumpyArray_(self, x, y, axis, plotLabelText = None, *args, **kwargs):
        """Plots a numpy array of up to two dimensions.
        Applies to quantity array and numeric numpy arrays.
        """
        if not isinstance(axis, pg.PlotItem):
            raise TypeError(f"axis expected to be a PlotItem; instead, got {type(axis).__name__}")
        # print(f"x: {x.shape}, y: {y.shape}")
        self._setup_signal_choosers_(analog=[y])
        
        plotDataItemName = kwargs.pop("name", None)
        
        if plotDataItemName is None:
            plotDataItemName = "Array signal"
            
        kwargs["name"] = plotDataItemName
        xlabel = kwargs.pop("xlabel", None)
        
        if xlabel is None or (isinstance(xlabel, str) and len(xlabel.strip()) == 0):
            xlabel = "Sample index"
            
        kwargs["xlabel"] = xlabel
        
        ylabel = kwargs.pop("ylabel", None)
        if ylabel is None or (isinstance(ylabel, str) and len(ylabel.strip()) == 0):
            ylabel = "Sample value"
            
        if isinstance(y, pq.Quantity):
            ydimstr = scq.shortSymbol(y.units.dimensionality)
            if len(ydimstr):
                ylabel = f"Sample value ({ydimstr})"
            else:
                ylabel = "Sample value"
                
            
        kwargs["ylabel"] = ylabel
        self._plot_numeric_data_(axis, x, y, *args, **kwargs)
        axis.setVisible(True)
            
        if isinstance(plotLabelText, str) and len(plotLabelText.strip()):
            self.plotTitleLabel.setText(plotLabelText, color = "#000000")
        
        if not isinstance(self.docTitle, str) or len(self.docTitle.strip()) == 0:
            self.docTitle = "Data array"
            
        axis.setVisible(True)
        
    @safeWrapper
    def _plot_signal_(self, signal, *args, **kwargs):
        """Plots individual signal objects.
        
        Signal objects are those defined in the Neuralensemble's neo package 
        (neo.AnalogSignal, neo.IrregularlySampledSignal), as well as datasignal
        module (datasignal.DataSignal, datasignal.IrregularlySampledDataSignal).
        
        Calls _setup_signal_choosers_, then determines how may axes are needed,
        depending on whether channels are plotted separately (and which ones, if
        indicated in arguments passed on to setData())
        
        """
        
        # NOTE: 2023-01-17 21:19:05
        # Called by self._plot_data_ when self._yData_ is a signal, or a sequence
        # of signals and self.frameAxis==1 (hence for plotting of each signal
        # in its own frame).
        
        # Data is then plotted in each axes (if more than one) from top to 
        # bottom iterating through channels (if required) by calling
        # _plot_numeric_data_()
        
        if signal is None:
            return
        
        if not isinstance(signal, neo.core.baseneo.BaseNeo):
            raise TypeError("_plot_signal_ expects an object from neo framework, or a datasignal.DataSignal or datasignal.IrregularlySampledDataSignal; got %s instead" % (type(signal).__name__))
            
        if isinstance(signal, (neo.AnalogSignal, DataSignal)):
            analog = [signal]
            irregs = None
        elif isinstance(signal, (neo.IrregularlySampledSignal, IrregularlySampledDataSignal)):
            analog = None
            irregs = [signal]
        else:
            raise TypeError(f"Expecting one of {SIGNAL_OBJECT_TYPES}; got {type(signal).__name__} instead")
        
        self._setup_signal_choosers_(analog=analog, irregular=irregs)
        
        sig_name = kwargs.pop("name", None)
        
        signal_name = getattr(signal, "name", "Signal")
        
        domain_name = neoutils.get_domain_name(signal)
        
        if isinstance(signal, (neo.IrregularlySampledSignal, IrregularlySampledDataSignal)):
            if signal.shape[1] > 1:
                kwargs["symbol"] = cycle(self.defaultIrregularSignalSymbols)
                kwargs["symbolColor"] = cycle(self.defaultLineColorsList)
            else:
                kwargs["symbol"] = self.defaultIrregularSignalSymbols[0]
                
            kwargs["pen"] = None
            kwargs["symbolPen"] = self.defaultIrregularSignalSymbolPen
            kwargs["symbolBrush"] = self.defaultIrregularSignalSymbolBrush
            kwargs["symbolSize"] = self.defaultIrregularSignalSymbolSize
            kwargs["pxMode"] = True
            
        if self.plot_start is not None:
            if self.plot_stop is not None:
                sig = signal.time_slice(self.plot_start, self.plot_stop)
                
            else:
                sig = signal.time_slice(self.plot_start, signal.t_stop)
                
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

            for (k, channel) in enumerate(chNdx):
                ch_name = sig.array_annotations.get("channel_names", None)
                if not isinstance(ch_name, np.ndarray):
                    ch_name = f"channel_{k}"
                else:
                    ch_name = ch_name[k]
                    
                    
                if isinstance(sig, (neo.AnalogSignal, DataSignal)) and not self._plot_analogsignals_:
                    self.signalAxis(k).setVisible(False)
                    return
                
                if isinstance(sig, (neo.IrregularlySampledSignal, IrregularlySampledDataSignal)) and not self._plot_irregularsignals_:
                    self.signalAxis(k).setVisible(False)
                    return
                
                kwargs["name"] = ch_name
                
                xdimstr = scq.shortSymbol(sig.t_start.units.dimensionality)
                if len(xdimstr):
                    xlabel="%s (%s)" % (domain_name, xdimstr)
                else:
                    xlabel="%s" % domain_name
                    
                ydimstr = scq.shortSymbol(sig.units.dimensionality)
                if len(ydimstr):
                    ylabel="%s (%s)\nchannel %d" % (signal_name, ydimstr, channel)
                else:
                    ylabel="%s \nchannel %d" % (signal_name, channel)
                
                self._plot_numeric_data_(self.signalAxis(k), 
                                         np.array(sig.times),
                                         np.array(sig[:,channel].magnitude),
                                         # name = ch_name,
                                         xlabel=xlabel,
                                         ylabel=ylabel, 
                                         *args, **kwargs)
                
                plot_name = f"{sig.name}_{ch_name}"
                if plot_name != self.signalAxis(k).vb.name:
                    self._register_plot_item_name_(self.signalAxis(k), plot_name)
                self.signalAxis(k).setVisible(True)
                    
        else:
            if isinstance(sig, (neo.AnalogSignal, DataSignal)) and not self._plot_analogsignals_:
                self.signalAxis(0).setVisible(False)
                return
            
            if isinstance(sig, (neo.IrregularlySampledSignal, IrregularlySampledDataSignal)) and not self._plot_irregularsignals_:
                self.signalAxis(0).setVisible(False)
                return
            
            # prepare channel names, for legend
            if sig.shape[1] > 1:
                if sig_name is None:
                    sig_name = [f"channel {k}" for k in range(sig.shape[1])]
                    
                elif isinstance(sig_name, str):
                    sig_name = [f"sig_name, channel {k}" for k in range(sig.shape[1])]
                    
                elif isinstance(sig_name, (tuple, list)) and all(isinstance(s, str) for s in sig_name):
                    if len(sig_name) < sig.shape[1]:
                        sig_name.extend([f"channel {k}" for k in range(len(sig_name, sig.shape[1]))])
                    elif len(sig_name) > sig.shape[1]:
                        sig_name = sig_name[:sig.shape[1]]
                        
                else:
                    sig_name = sig.name
                    
                kwargs["name"] = sig_name
                
            
            xdimstr = scq.shortSymbol(sig.times.units.dimensionality)
            if len(xdimstr):
                xlabel="%s (%s)" % (domain_name, xdimstr)
            else:
                xlabel="%s" % domain_name
                
            ydimstr = scq.shortSymbol(sig.units.dimensionality)
            if len(ydimstr):
                ylabel="%s (%s)" % (signal_name, ydimstr)
            else:
                ylabel="%s" % signal_name
                
            if sig.shape[1] > 10:
                # print("mt")
                    
                self.setCursor(QtCore.Qt.WaitCursor)
                self.sig_plot.emit(self._make_sig_plot_dict_(self.signalAxis(0), np.array(sig.times), 
                                       np.array(sig.magnitude), 
                                       # name=sig.name,
                                       xlabel=xlabel, 
                                       ylabel=ylabel, 
                                       *args, **kwargs))
            else:
                self._plot_numeric_data_(self.signalAxis(0), np.array(sig.times), 
                                        np.array(sig.magnitude), 
                                        # name=sig.name,
                                        ylabel=ylabel, 
                                        xlabel=xlabel, 
                                        *args, **kwargs)
                
            if sig.name != self.signalAxis(0).vb.name:
                self._register_plot_item_name_(self.signalAxis(0), sig.name)
                
            self.signalAxis(0).register(sig.name)
            self.signalAxis(0).setVisible(True)
                
        self.plotTitleLabel.setText("", color = "#000000")
        
        if not isinstance(self.docTitle, str) or len(self.docTitle.strip()) == 0:
            self.docTitle = signal_name
            
        # self._align_X_range()
        self._update_axes_spines_()
            
    def _make_sig_plot_dict_(self, plotItem:pg.PlotItem, 
                             x:np.ndarray, y:np.ndarray, 
                             xlabel:(str, type(None))=None,  ylabel:(str, type(None))=None, 
                             title:(str, type(None))=None, name:(str, type(None))=None, 
                             symbolColor:(cycle, type(None))=None, 
                             *args, **kwargs):
        return {"plotItem":plotItem, 
                "x": x, "y": y, 
                "xlabel": xlabel, "ylabel": ylabel,
                "title": title, "name": name, 
                "symbolColor": symbolColor,
                "args": args, "kwargs": kwargs}
                    
    @safeWrapper
    @pyqtSlot(dict)
    def _slot_plot_numeric_data_(self, data:dict):
        """For dict's keys and values see parameters of self._plot_numeric_data_
        For threading...
        """
        #print("_slot_plot_numeric_data_")
        self.statusBar().showMessage("Working...")
        
        plotItem            = data.pop("plotItem")
        x                   = data.pop("x")
        y                   = data.pop("y")
        xlabel              = data.pop("xlabel", None)
        ylabel              = data.pop("ylabel", None)
        title               = data.pop("title", None)
        name                = data.pop("name", None)
        symbolColor         = data.pop("symbolColor", None)
        args                = data.pop("args", tuple())
        kwargs              = data.pop("args", dict())

        # print(f"_slot_plot_numeric_data_ y.shape {y.shape}")
        self._plot_numeric_data_(plotItem,  x, y, xlabel, ylabel,
                                title, name, symbolColor, *args, **kwargs)
        
        self.setCursor(QtCore.Qt.ArrowCursor)
        self.statusBar().clearMessage()
        
    def _plot_events_or_marks_(self, entities_list, entities_axis, xLabel, yLabel, minX, maxX, adapt_X_range, height_interval, symbolStyle, **labelStyle):
        """ Helper method for self._plot_discrete_entities_(events or data marks)"""
        symbolColor = symbolStyle["color"]
        symbolPen = symbolStyle["pen"]
        symbolBrush = symbolStyle.get("brush", None)
        # symbol = symbolStyle["symbol"]
        # print(f"symbol = {symbol}")
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
            self.setCursor(QtCore.Qt.WaitCursor)
            self.sig_plot.emit(self._make_sig_plot_dict_(entities_axis, xx_, yy_,
                                                        pen=None, name = data_name,
                                                        symbol = "event", 
                                                        symbolColor = symbolColor,
                                                        symbolBrush = symbolBrush,
                                                        symbolPen   = symbolPen)
                                )
        else:
            self._plot_numeric_data_(entities_axis, xx_, yy_,
                                    pen=None, name=data_name,
                                    symbol = "event", 
                                    symbolColor = symbolColor,
                                    symbolBrush = symbolBrush,
                                    symbolPen   = symbolPen)
        
        # entities_axis.setLabel(bottom = xLabel, left = yLabel)
        entities_axis.axes["left"]["item"].setPen(None)
        entities_axis.axes["left"]["item"].setLabel(yLabel, **labelStyle)
        entities_axis.axes["left"]["item"].setStyle(showValues=False)
        entities_axis.axes["bottom"]["item"].setLabel(xLabel)
            
    def _plot_signal_data_(self, signal:typing.Union[neo.AnalogSignal, neo.IrregularlySampledSignal, DataSignal, IrregularlySampledDataSignal], 
                           plot_name:str, plotItem:pg.PlotItem, plotItemName:str, *args, **kwargs):
        """ Helper method for self._plot_signals_(…).
     (do not confuse with self._plot_signal_(…))"""
        # print(f"{self.__class__.__name__}._plot_signal_data_(signal<{type(signal).__name__}>) kwargs = {kwargs}")
        sig_channel_index = kwargs.pop("SignalChannelIndex", None)
        
        # print(f"{self.__class__.__name__}._plot_signal_data_ kwargs: {kwargs}")
        
        symbol = kwargs.get("symbol", None)
        symbolColor = kwargs.get("symbolColor", None)
        symbolBrush = kwargs.get("symbolBrush", None)
        
        if isinstance(signal, (neo.IrregularlySampledSignal, IrregularlySampledDataSignal)):
            if symbol is None:
                if signal.shape[1] > 1:
                    kwargs["symbol"] = cycle(self.defaultIrregularSignalSymbols)
                    kwargs["symbolColor"] = cycle(self.defaultLineColorsList)
                else:
                    kwargs["symbol"] = self.defaultIrregularSignalSymbols[0]
                
            if symbolColor is None:
                if signal.shape[1] > 1:
                    kwargs["symbolColor"] = cycle(self.defaultLineColorsList)
                    
            if symbolBrush is None:
                if signal.shape[1] > 1:
                    kwargs["symbolBrush"] = cycle(self.defaultLineColorsList)
                    # kwargs["symbolBrush"] = cycle([QtGui.QBrush(colormaps.qcolor(c)) for c in self.defaultLineColorsList])
        
        domain_name = get_domain_name(signal)
        
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
        
        xdimstr = scq.shortSymbol(sig.t_start.units.dimensionality)
        if len(xdimstr):
            xlabel = "%s (%s)" % (domain_name, xdimstr)
        else:
            xlabel = "%s" % domain_name
            
        ydimstr = scq.shortSymbol(signal.units.dimensionality)
        if len(ydimstr):
            ylabel = "%s (%s)" % (plot_name,ydimstr)
        else:
            ylabel = "%s" % plot_name
            
        if sig.shape[1] > 10:
            self.setCursor(QtCore.Qt.WaitCursor)
            self.sig_plot.emit(self._make_sig_plot_dict_(plotItem,
                                    sig.times,
                                    sig.magnitude,
                                    xlabel = xlabel,
                                    ylabel = ylabel,
                                    # name=plot_name,
                                    # symbol=None,
                                    **kwargs))
        else:
            self._plot_numeric_data_(plotItem,
                                    sig.times,
                                    sig.magnitude,
                                    xlabel = xlabel,
                                    ylabel = ylabel,
                                    # name=plot_name,
                                    # symbol=None,
                                    **kwargs)
            
        if plotItemName != plotItem.vb.name:
            self._register_plot_item_name_(plotItem, plotItemName)

        plotItem.axes["left"]["item"].setStyle(autoExpandTextSpace=False,
                                                autoReduceTextSpace=False)
        plotItem.update()
        
    @safeWrapper
    def _plot_numeric_data_(self, plotItem: pg.PlotItem, x:np.ndarray, y:np.ndarray, 
                            xlabel:(str, type(None))=None, ylabel:(str, type(None))=None, 
                            title:(str, type(None))=None, # name:(str, type(None))=None, 
                            reusePlotItems:bool = True, *args, **kwargs):
                            # symbolColor:(cycle, type(None))=None, 
        """ The workhorse that does the actual plotting of signals
        Common landing zone for many of the self._plot_* methods
        
        Parameters:
        ----------
        x, y, : np.ndarray (domain and signal)
            Data to be plotted: x and y must be 1D or 2D numpy arrays with compatible 
            dimensions.
            
        xlabel, ylabel: str ; optional (defult is None) 
            Labels for the X and Y axis, respectively
        
        title:str, optional, default is None
            When present, will be displayd at the top of the  PlotItem where the
            data is plotted; can be in HTML format
                
        reusePlotItems:bool, default is True, meaning that existing PlotDataItem will
            be reused to plot the data channels, new PlotDataItems will be added
            if necessry, and excess PlotDataItems (if they exist) will be removed.
            
            When False, new PlotDataItems will be added to the axis (PlotItem)
            - useful to plot several data arrays without overwriting exising
            plots (e.g. inside a loop), when the arrays cannot be conatenated 
            in a single matrix due to shape constraints. NOTE: In this case you 
            should clear the plotitem (the axis) beforehand.
            
        args, kwargs: additional parameters for PlotItem.plot() function (and
            indirectly PlotDataItem constructor and methods).
            See pyqtgraph PlotItem.plot() and pyqtgrapg PlotDataItem
    
            symbol
            pen
            symbolPen
            
        
        Returns
        ------
        a pyqtgraph.PlotItem where the data was plotted
        
        """
        # print(f"{self.__class__.__name__}._plot_numeric_data_ kwargs: {kwargs}")
        
        # ATTENTION: y is a numpy arrays here; x is either None, or a numpy array
        
        # ### BEGIN debug
        # stack = inspect.stack()
        # for s in stack:
        #     print(f"\tcaller\t {s.function} at line {s.lineno}")
        # ### END debug
        
        y = np.atleast_1d(y)
        
        if y.ndim > 2:
            raise TypeError("y expected to be an array with up to 2 dimensions; for %s dimensions instead" % y.ndim)
        
        # print(f"_plot_numeric_data_: y dims = {y.ndim}")
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

        # NOTE: 2021-09-09 18:30:20
        # when symbol is present we don't draw the connection line
        symbolBrush = kwargs.get("symbolBrush", None)
        symbolColor = kwargs.get("symbolColor", None)
        color = kwargs.get("color", None)
        name = kwargs.get("name", None)
        
        pen = kwargs.get("pen", QtGui.QPen(QtGui.QColor("black"),1))
        if isinstance(pen, QtGui.QPen): # because the caller may have passed 'pen=None'
            pen.setCosmetic(True)
            
        symbolPen = kwargs.get("symbolPen",QtGui.QPen(QtGui.QColor("black"),1))
        if isinstance(symbolPen, QtGui.QPen):# because the caller may have passed 'symbolPen=None'
            symbolPen.setCosmetic(True)
        
        symbol = kwargs.get("symbol", None)
        if symbol is None:
            kwargs["pen"] = pen
            kwargs["symbolPen"] = None
            kwargs["symbol"] = None
                
        else:
            kwargs["pen"] = None
            kwargs["symbolPen"] = symbolPen
            # kwargs["symbol"] = symbol
        
        # NOTE: 2022-12-09 09:22:09
        # rewriting into a pg.PlotDataItem needs vector (array with shape (N,))
        # OR array with shape (N,2); 
        # "vectors" with shape (N,1) won't do
        plotDataItems = [i for i in plotItem.listDataItems() if isinstance(i, pg.PlotDataItem)]

        if y.ndim == 1:
            y_nan_ndx = np.atleast_1d(np.isnan(y))
            yy = y
            
            if isinstance(y, pq.Quantity):
                yy[y_nan_ndx] = -np.inf*y.units
            else:
                yy[y_nan_ndx] = -np.inf

            if x is not None:
                if x.ndim > 1:
                    xx = x[:,0]
                else:
                    xx = x
            else:
                xx = None
            
            # print(f"{self.__class__.__name__}._plot_numeric_data_ y.ndim == 1; plotdataitem kwargs {kwargs}")
            
            if reusePlotItems:
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
                        
            else:
                if xx is not None:
                    plotItem.plot(x=xx, y=yy, **kwargs)
                else:
                    plotItem.plot(y=yy, **kwargs)
        
        elif y.ndim == 2:
            colors = cycle(self.defaultLineColorsList)
            
            if reusePlotItems and y.shape[1] < len(plotDataItems):
                for item in plotDataItems[y.shape[1]:]:
                    plotItem.removeItem(item)
            
            for k in range(y.shape[1]):
                y_ = np.atleast_1d(y[array_slice(y, {1:k})].squeeze())
                
                # print("y_.shape", y_.shape)
                
                if y_.ndim ==2 and x.shape[0] == y_.shape[1]:
                    y_ = y_.T
                    
                if x is not None:
                    # if x.ndim == 2 and x.shape[1] == y.shape[self.signalChannelAxis]:
                    if x.ndim == 2 and x.shape[1] == y.shape[1]:
                        x_ = np.atleast_1d(x[:,k].squeeze())
                        
                    else:
                        x_ = np.atleast_1d(x.squeeze())
                        
                else:
                    x_ = None
                    
                y_nan_ndx = np.isnan(y_)
                yy = y_
                
                if isinstance(y_, pq.Quantity): # quantities are always np.dtype(float) ?!?
                    yy[y_nan_ndx] = -np.inf * y_.units
                else:
                    if yy.dtype == np.dtype(int):
                        yy = yy.astype(np.dtype(float))
                    yy[y_nan_ndx] = -np.inf
                    
                if x_ is not None:
                    xx = x_
                else:
                    xx = None
                
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
                    if isinstance(symbol, cycle):
                        kwargs["symbol"] = next(symbol)
                        
                    else:
                        kwargs["symbol"] = symbol
                    
                    if isinstance(symbolColor, cycle):
                        symbolPen = QtGui.QPen(QtGui.QColor(next(symbolColor)), 1)
                        symbolPen.setCosmetic(True)
                        kwargs["symbolPen"] = symbolPen
                        
                    else:
                        kwargs["symbolPen"] = symbolPen # same symbol pen as defined above!
                        
                    if isinstance(symbolBrush, cycle):
                        kwargs["symbolBrush"] = next(symbolBrush)
                        # kwargs["symbolBrush"] = QtGui.QBrush(colormaps.qcolor(next(symbolBrush)))
                        
                    else:
                        kwargs["symbolBrush"] = symbolBrush
                        
                    # elif isinstance(symbolBrush, QtGui.QBrush):
                    #     kwargs["symbolBrush"] = symbolBrush
                        
                        
                if reusePlotItems:
                    if k < len(plotDataItems):
                        plotDataItems[k].clear()
                        if xx is not None:
                            plotDataItems[k].setData(x = xx, y = yy, **kwargs)
                        else:
                            plotDataItems[k].setData(y = yy, **kwargs)
                        
                    else:
                        if xx is not None:
                            # print(f"kwargs = {kwargs}")
                            plotItem.plot(x = xx, y = yy, **kwargs)
                        else:
                            plotItem.plot(y = yy, **kwargs)
                            
                else:
                    if xx is not None:
                        plotItem.plot(x = xx, y = yy, **kwargs)
                    else:
                        plotItem.plot(y = yy, **kwargs)
        
        plotItem.setLabels(bottom = [xlabel], left=[ylabel])
        
        if isinstance(title, str) and len(title.strip()):
            plotItem.setTitle(title)
        
        if plotItem is self._selected_plot_item_:
            lbl = "<B>%s</B>" % self._selected_plot_item_.axes["left"]["item"].labelText
            self._selected_plot_item_.setLabel("left", lbl)
            
        else:
            lbl = plotItem.axes["left"]["item"].labelText
            
            if lbl.startswith("<B>") and lbl.endswith("</B>"):
                lbl = lbl[3 : lbl.find("</B>")]
                plotItem.setLabel("left", lbl)
        
        plotItem.replot() # must be called NOW, and NOT earlier !
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
            self.currentAxis = self.axes[0] if len(self.axes) else None
            
    def _showXGrid(self, value:bool):
        for ax in self.axes:
            ax.showGrid(x=value)
        
    def _showYGrid(self, value:bool):
        for ax in self.axes:
            ax.showGrid(y=value)
        
    def linkAllXAxes(self):
        """Link all PlotItem objects (a.k.a signal viewer 'axes') to the top one.
        The consequence is that all X axes are linked: a horizontal zoom on any 
    of them (e.g. using the mouse interaction) triggers an equivalent zoom 
    in the others.
        
    """
        # WARNING: 2023-07-09 12:21:01
        # linking an axis disables auto-ranging on that axis
        if len(self.axes) <= 1:
            return
        
        # NOTE: 2023-07-09 15:25:32
        # link all X axes ot the X axis of the top PlotItem (with index 0)
        # for ax in self.axes[1:]:
        #     ax.vb.setXLink(self.axes[0])

        # NOTE: 2023-07-10 12:21:29
        # this links all axes pairwise (2nd to first, 3rd to 2nd etc)
        for ax in pairwise(self.axes):
            ax[1].vb.setXLink(ax[0])
    
        # NOTE: 2023-07-09 14:28:00
        # this links axes pairwise except for the non-signal axes;
        # not sure this is the best approach
#         if len(self.signalAxes):
#             for ax in pairwise(self.signalAxes):
#                 ax[1].vb.setXLink(ax[0])
#                 
#             nonSigAxes = list(filter(lambda x: x not in self.signalAxes, self.axes))
#             
#             for ax in nonSigAxes:
#                 ax.vb.setXLink(self.signalAxes[0])
#                 
#         else:
#             for ax in pairwise(self.axes):
#                 ax[1].vb.setXLink(ax[0])
        
        
    def unlinkAllXAxes(self):
        if len(self.axes) < 1:
            return
        
        for ax in self.axes:
            ax.vb.setXLink(None)
        
    def _setup_axes_(self, _n_signal_axes_:int) -> None:
        """Call this ONCE after parsing the data.
        In SignalViewer there are n + 2 pg.PlotItem¹ objects:
        n PlotItem to display signals
        1 PlotItem to display events (e.g. triggers, etc)
        1 PlotItem to display spiketrains
    
        The PlotItem objects are stacked vertically in a pg.GraphicsLayout, bound
        to the instance attribute `signalsLayout`, and associated with a
        pg.GraphicsLayoutWidget bound to the instance attribute `viewerWidget`.
        
        NOTE: neo.Epoch objects are displayed using Linear Region Items, in all 
            axes
        
        This function updates, creates when needed, and removes excess PlotItems
        dedicated to plotting signals, once a new data has been sent to the 
        instance of SignalViewer e.g. via `plot`, `view`, `setData` (`plot` and
        `view` are aliases to `setData`), or at initialization (`__init__`) which
        calls `setData`.
        
        Parameters:
        ===========
        _n_signal_axes_ the number of pg.PlotItem objects required for the data
            NOTE: There will always be one events ax
        The number of PlotItem objects needed to plot signals is stored in the 
        attribute `self._n_signal_axes_` which is set by `_parse_data_`.
        
        TODO: 2023-10-04 16:51:26
        If possble, insert horizontal splitters between axes so that the user may
        "squeeze" or "expand" a single axis vertically.
        --------
        ¹ PyQtGraph's PlotItem 
        """
        self._plot_names_.clear()
        nAxes = _n_signal_axes_ + 2 # how many axes the data requires?
        
        # set these up at earliest occasion
        self._axes_X_view_ranges_ = [[math.nan, math.nan] for k in range(nAxes)]
        self._x_data_bounds_ = [[math.nan, math.nan] for k in range(nAxes)]
        # self._axes_X_view_offsets_scales_ = [[math.nan, math.nan] for k in range(nAxes)]
        self._axes_X_view_offsets_scales_ = [[0., 1.] for k in range(nAxes)]

        # retrieve (cache) the events axis and ths spiketrains axis, if they exist
        # check if there are any plotitems in the layout and of these, is 
        # there an event axis and a spiketrains axis
        if len(self.plotItems) - len(self.signalAxes) >= 2:
            # if there are 2 more plotitems than signal axes, assign the 
            # last two to the events axis and spiketrains axis
            self._events_axis_, self._spiketrains_axis_ = self.plotItems[-2:]
            
        elif len(self.plotItems) - len(self.signalAxes) == 1:
            # if there is only only one plotitem more than existing signal axes
            # then assign it to the events axis
            self._events_axis_ = self.plotItems[-1]
            
        # WARNING 2023-01-17 10:46:04 
        # the last two slots in the layout are the events axis and
        # the spiketrains axis - must free up these slots and re-add them later
        # 
        # NOTE: 2023-01-17 10:44:37 
        # the events axis and the spiketrains axis will be added back
        # to the layout further down
        if isinstance(self._events_axis_, pg.PlotItem):
            self.signalsLayout.removeItem(self._events_axis_) # the events axis plot item is still alive!
            
        if isinstance(self._spiketrains_axis_, pg.PlotItem):
            self.signalsLayout.removeItem(self._spiketrains_axis_)
            
        if len(self.signalAxes) < _n_signal_axes_:
            # NOTE: 2023-05-09 13:00:18 - create axes as necessary
            # there are fewer signal axes than needed - create here as necessary
            
            for k, plotItem in enumerate(self.signalAxes):
                # re-use & update existing PlotItem objects
                plotname = f"signal_axis_{k}"
                self._register_plot_item_name_(plotItem, plotname)
                plotItem.setVisible(False)
                
            for k in range(len(self.signalAxes), _n_signal_axes_):
                # create new PlotItem objects as necessary, add to layout
                plotname = f"signal_axis_{k}"
                plotItem = pg.PlotItem(name = plotname)
                self.signalsLayout.addItem(plotItem, row=k, col=0)
                plotItem.sigXRangeChanged.connect(self._slot_plot_axis_x_range_changed)
                plotItem.vb.sigRangeChangedManually.connect(self._slot_plot_axis_range_changed_manually)
                plotItem.scene().sigMouseMoved[object].connect(self._slot_mouseMovedInPlotItem)
                plotItem.scene().sigMouseHover[object].connect(self._slot_mouseHoverInPlotItem)
                plotItem.setVisible(False)
                self._signal_axes_.append(plotItem)
                
                
        elif len(self.signalAxes) > _n_signal_axes_:
            # more signal axes than necessary
            for k in range(_n_signal_axes_):
                # re-use the ones that are still needed
                plotname = f"signal_axis_{k}"
                plotItem = self.signalAxes[k]
                self._register_plot_item_name_(plotItem, plotname)
                
            # remove the rest of them
            for plotItem in self.signalAxes[_n_signal_axes_:]:
                self._remove_axes_(plotItem)
                
            self._signal_axes_ = self._signal_axes_[:_n_signal_axes_]
                
        else: 
            # there already are as many PlotItems for signals as needed → reuse
            for k, plotItem in enumerate(self.signalAxes):
                plotname = f"signal_axis_{k}"
                self._register_plot_item_name_(plotItem, plotname)
                plotItem.setVisible(False)
                
        # NOTE: 2023-01-17 10:45:04
        # add the events axis back to the layout (after creating it, if needed)
        # see WARNING 2023-01-17 10:46:04 and NOTE: 2023-01-17 10:44:37 
        if not isinstance(self._events_axis_, pg.PlotItem):
            self._events_axis_ = pg.PlotItem(name=self._default_events_axis_name_)
            self._events_axis_.sigXRangeChanged.connect(self._slot_plot_axis_x_range_changed)
            self._events_axis_.vb.sigRangeChangedManually.connect(self._slot_plot_axis_range_changed_manually)
            if self._events_axis_.scene() is not None:
                self._events_axis_.scene().sigMouseMoved[object].connect(self._slot_mouseMovedInPlotItem)
                # self._events_axis_.scene().sigMouseHover[object].connect(self._slot_mouseHoverInPlotItem)
        
        if self._events_axis_ not in self.signalsLayout.items:
            self.signalsLayout.addItem(self._events_axis_, row = _n_signal_axes_, col=0)
            # self.signalsLayout.addItem(self._events_axis_, row=self._n_signal_axes_, col=0)
            self._events_axis_.scene().sigMouseMoved[object].connect(self._slot_mouseMovedInPlotItem)
            # self._events_axis_.scene().sigMouseHover[object].connect(self._slot_mouseHoverInPlotItem)
        
        # NOTE: 2023-01-17 10:45:24
        # add the spiketrains axis back to the layout (after creating it, if needed)
        # see WARNING 2023-01-17 10:46:04 and NOTE: 2023-01-17 10:44:37 
        if not isinstance(self._spiketrains_axis_, pg.PlotItem):
            self._spiketrains_axis_ = pg.PlotItem(name=self._default_spiketrains_axis_name_)
            self._spiketrains_axis_.sigXRangeChanged.connect(self._slot_plot_axis_x_range_changed)
            self._spiketrains_axis_.vb.sigRangeChangedManually.connect(self._slot_plot_axis_range_changed_manually)
            if self._spiketrains_axis_.scene() is not None:
                self._spiketrains_axis_.scene().sigMouseMoved[object].connect(self._slot_mouseMovedInPlotItem)
                # self._spiketrains_axis_.scene().sigMouseHover[object].connect(self._slot_mouseHoverInPlotItem)
                
            
            
        if self._spiketrains_axis_ not in self.signalsLayout.items:
            self.signalsLayout.addItem(self._spiketrains_axis_, row = _n_signal_axes_ + 1, col = 0)
            # self.signalsLayout.addItem(self._spiketrains_axis_, row = self._n_signal_axes_ + 1, col = 0)
            self._spiketrains_axis_.scene().sigMouseMoved[object].connect(self._slot_mouseMovedInPlotItem)
            # self._spiketrains_axis_.scene().sigMouseHover[object].connect(self._slot_mouseHoverInPlotItem)
            
        # NOTE: 2023-06-02 12:57:26
        # now, remember the (new) _n_signal_axes_:
        self._n_signal_axes_ = _n_signal_axes_
            
        # NOTE: 2023-10-04 13:38:53
        # suppress auto ranging on X in events and spike train axes
        
        if len(self.signalAxes):
            self._events_axis_.vb.enableAutoRange(self._events_axis_.vb.XAxis, enable=False)
            self._spiketrains_axis_.vb.enableAutoRange(self._spiketrains_axis_.vb.XAxis, enable=False)
            
        if self.signalsLayout.scene() is not None:
            self.signalsLayout.scene().sigMouseClicked.connect(self._slot_mouseClickSelectPlotItem)
            
        for plotItem in self.axes:
            self._clear_targets_overlay_(plotItem)
            self._clear_labels_overlay_(plotItem)
            plotItem.axes["left"]["item"].setStyle(autoExpandTextSpace=False,
                                                    autoReduceTextSpace=False,
                                                    maxTickLevel=2,
                                                    maxTextLevel=2)
            
            plotItem.axes["left"]["item"].setWidth(60)
            
            if plotItem in (self._events_axis_, self._spiketrains_axis_):
                # plotItem.showAxis("bottom", True)
                #                  left  top    right  bottom             left  top    right  bottom
                # plotItem.showAxes([True, False, False, True], showValues=[True, False, False, True])
                plotItem.setVisible(False)
                
        if len(self.axes):
            self.actionLink_X_axes.setEnabled(True)
            if self.xAxesLinked:
                self.linkAllXAxes()
            else:
                self.unlinkAllXAxes()
                
            self.actionShow_X_grid.setEnabled(True)
            self._slot_showXgrid(self.xGrid)
            self.actionShow_Y_grid.setEnabled(True)
            self._slot_showYgrid(self.yGrid)
            
        else:
            self.actionLink_X_axes.setEnabled(False)
            self.actionShow_X_grid.setEnabled(False)
            self.actionShow_Y_grid.setEnabled(False)
            
        
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
        
        if len(obj) and isinstance(obj[0], pg.PlotItem):
            self._hovered_plot_item_ = obj[0]
        else:
            self._hovered_plot_item_ = None
            
    @pyqtSlot(object)
    @safeWrapper
    def _slot_mouseMovedInPlotItem(self, pos):
        # pos is a QPointF
        # connected to a PlotItem's scene!
        # at this stage there should already be a _focussed_plot_item_
        # NOTE _hovered_plot_item_ is the PlotItem that is hovered by the mouse;
        # this is NOT necessarily the _selected_plot_item_, which is set after
        # a LMB click ! 
        if isinstance(self._hovered_plot_item_, pg.PlotItem):
            self._reportMouseCoordinatesInAxis_(pos, self._hovered_plot_item_)
                
        else:
            self._update_coordinates_viewer_()
            
    def _addCursors_parse_coords_(self, coords, cursorType):
        # print(f"{self.__class__.__name__}._addCursors_parse_coords_ coords {coords}")
        if isinstance(coords, (tuple, list)) and all([isinstance(v, numbers.Number) for v in coords]):
            if len(coords) == 1:
                if cursorType in ("v", "vertical", "Vertical", 
                                    "c", "crosshair", "Crosshair", 
                                    SignalCursorTypes.vertical,
                                    SignalCursorTypes.crosshair):
                    x = coords[0]
                    y = None
                    
                elif cursorType in ("h", "horizontal", "Horizontal", 
                                    SignalCursorTypes.horizontal):
                    y = coords[0]
                    x = None
                    
            elif len(coords) == 2:
                x,y = coords # distribute coordinates to individual values
                
            else:
                raise ValueError(f"Invalid coordinates specified - expecting at most two; instead, got  {coords}")
                    
            
        elif isinstance(coords, (pq.Quantity, np.ndarray)):
            if coords.size == 1:
                if cursorType in ("v", "vertical", "Vertical", 
                                    "c", "crosshair", "Crosshair", 
                                    SignalCursorTypes.vertical,
                                    SignalCursorTypes.crosshair):
                    if len(coords.shape)==0: # scalar
                        x = coords
                        
                    else:
                        x = coords[0] # array with 1 element
                        
                    y = None
                    
                elif cursorType in ("h", "horizontal", "Horizontal", 
                                    SignalCursorTypes.horizontal):
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
                                SignalCursorTypes.vertical,
                                SignalCursorTypes.crosshair):

                x = coords
                y = None
                
            elif cursorType in ("h", "horizontal", "Horizontal", 
                                SignalCursorTypes.horizontal):

                x = None
                y = coords
                    
        else:
            raise ValueError(f"Invalid coordinates specification: {coords}")
        
        return x,y
            
    def _use_coords_sequence_(self, seq, xw, yw, lbls, ax, cursorType):
        """Adds cursors based on a sequence of cursor coordinates
        """
        # print(f"_use_coords_sequence_ seq = {seq}, xw = {xw}, yw = {yw}, lbls = {lbls}, ax = {ax}")
        for (k, coords) in enumerate(seq):
            x, y = self._addCursors_parse_coords_(coords, cursorType)
        
            if isinstance(xw, (tuple, list, np.ndarray)):
                if len(xw) != len(seq):
                    raise ValueError("number of elements mismatch between xwindow and coordinates")
                wx = xw[k]
                
            elif isinstance(xw, numbers.Number):
                wx = xw
                    
            if isinstance(yw, (tuple, list, np.ndarray)):
                if len(xw) != len(seq):
                    raise ValueError("number of elements mismatch between ywindow and coordinates")
                wy = yw[k]
                
            elif isinstance(yw, numbers.Number):
                wy = yw
                
            if isinstance(lbls, (tuple, list)) and all([isinstance(v, str) for v in lbls]):
                if len(lbls) != len(seq):
                    raise ValueError("number of elements mismatch between labels and coordinates")
                
                lbl = lbls[k]
                
            elif isinstance(lbls, np.ndarray) and "str" in labels.dtype.name:
                if len(lbls) != len(seq):
                    raise ValueError("number of elements mismatch between labels and coordinates")
                lbl = lbls[k]
                
            elif isinstance(lbls, str):
                lbl = lbls
                
            else:
                n_existing_cursors = self.getSignalCursors(cursorType)
                lbl = f"{cursorType.name[0]}{len(n_existing_cursors)}"
                
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

    @safeWrapper
    def _reportMouseCoordinatesInAxis_(self, pos, plotitem):
        if isinstance(plotitem, pg.PlotItem):
            if plotitem.sceneBoundingRect().contains(pos):  
                plot_name = plotitem.vb.name
                
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
        
        if isinstance(focusItem, pg.ViewBox):
            plotitems, rc = zip(*self.axesWithLayoutPositions)
            
            focusedPlotItems = [i for i in plotitems if i.vb is focusItem]
            
            if len(focusedPlotItems):
                self._selected_plot_item_ = focusedPlotItems[0]
                plot_index = plotitems.index(self._selected_plot_item_)
                self._selected_plot_item_index_ = plot_index
                self._setAxisIsActive(self._selected_plot_item_, True)
                self._statusNotifyAxisSelection(plot_index)
                    
                for ax in self.axes:
                    if ax is not self._selected_plot_item_:
                        self._setAxisIsActive(ax, False)
                            
            else:
                self._selected_plot_item_ = None
                self._selected_plot_item_index_ = -1
                
                for ax in self.axes:
                    self._setAxisIsActive(ax, False)

        else:
            self._selected_plot_item_ = None
            self._selected_plot_item_index_ = -1

            for ax in self.axes:
                self._setAxisIsActive(ax, False)
            
    @safeWrapper
    def clearEpochs(self):
        self._plotEpochs_()
                
    @safeWrapper
    # def clear(self, keepCursors=False):
    def clear(self):
        """Clears the display
        """
        # TODO: cache cursors when keepCursors is True
        # at the moment do NOT pass keepCcursor other than False!
        # need to store axis index witht he cursors so that we can restore it ?!?
        # print(f"{self.__class__.__name__}.clear()")
        self._selected_plot_item_ = None
        self._selected_plot_item_index_ = -1
        self._hovered_plot_item_ = None
        
        for axis in self.axes:
            self.removeLegend(axis)
            self.removeLabels(axis)
            self.removeTargetsOverlay(axis)
        
        self.dataAnnotations.clear()
        self.annotationsViewer.clear()

        self.plotTitleLabel.setText("")
        
        for c in self._crosshairSignalCursors_.values():
            c.detach()
            
        for c in self._verticalSignalCursors_.values():
            c.detach()
            
        for c in self._horizontalSignalCursors_.values():
            c.detach()
            
        for clist in self._cached_cursors_.values():
            for c in clist:
                c.detach()
            
        self._crosshairSignalCursors_.clear() # a dict of SignalCursors mapping str name to cursor object
        self._verticalSignalCursors_.clear()
        self._horizontalSignalCursors_.clear()
        self._cached_cursors_.clear()
        
        self.linkedCrosshairCursors = []
        self.linkedHorizontalCursors = []
        self.linkedVerticalCursors = []
#         if not keepCursors:
#             self._crosshairSignalCursors_.clear() # a dict of SignalCursors mapping str name to cursor object
#             self._verticalSignalCursors_.clear()
#             self._horizontalSignalCursors_.clear()
#             self._cached_cursors_.clear()
#             
#             self.linkedCrosshairCursors = []
#             self.linkedHorizontalCursors = []
#             self.linkedVerticalCursors = []
        
        self.signalNo = 0
        self.frameIndex = [0]
        self.signalIndex = 1 # NOTE: 2017-04-08 23:00:48 in effect number of signals /frame !!!
        
        self.guiSelectedAnalogSignalEntries.clear()
        
        self.guiSelectedIrregularSignalEntries.clear()
        
        self._yData_ = None
        self._xData_ = None
        
        self.plot_start = None
        self.plot_stop = None
        
        self._clear_lris_()
        # self._clear_targets_overlay_()
        # self._clear_labels_overlay_()
        
        self._number_of_frames_ = 0
        
        # NOTE: 2018-09-25 23:12:46
        # recipe to block re-entrant signals in the code below
        # cleaner than manually connecting and re-connecting
        # and also exception-safe
        
        signalBlockers = [QtCore.QSignalBlocker(widget) for widget in \
            (self.analogSignalComboBox, self.irregularSignalComboBox,
             self._frames_spinBoxSlider_)]
        
        self.analogSignalComboBox.clear()
        self.irregularSignalComboBox.clear()
        self._frames_spinBoxSlider_.setMinimum(0)
        self._frames_spinBoxSlider_.setMaximum(0)
        self.docTitle = None # to completely remove the data name from window title
        
        for p in self.plotItems:
            self._remove_axes_(p)
        
        # remove all PlotItems references
        self._signal_axes_.clear()
        self._events_axis_ = None 
        self._spiketrains_axis_ = None
        
    def clearAxes(self):
        self._clear_lris_()
        for ax in self.axes:
            self.removeTargetsOverlay(ax)
            ax.clear()
            ax.setVisible(False)
            

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
    def signalCursors(self):
        """Alias to cursors property
        """
        return self.cursors
    
    @property
    def selectedAxis(self):
        return self._selected_plot_item_
    
    # aliases to setData
    plot = setData
    view = setData
    
        
