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
from __future__ import print_function

import sys, os, traceback, numbers, warnings, weakref, inspect, typing

import collections, itertools

from itertools import cycle
from operator import attrgetter, itemgetter, methodcaller
from enum import Enum, IntEnum

#### END core python modules

#### BEGIN 3rd party modules
from PyQt5 import QtCore, QtGui, QtWidgets, QtSvg
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.uic import loadUiType as __loadUiType__


import numpy as np
import pandas as pd
import pyqtgraph as pg
pg.Qt.lib = "PyQt5"
import quantities as pq
import matplotlib as mpl
from matplotlib import pyplot as plt
from matplotlib import cm, colors
import matplotlib.widgets as mpw
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import (FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar)

import neo

import vigra
#import vigra.pyqt # for quickdialog -- to phase out
#import vigra.pyqt.quickdialog as quickdialog
#import vigra.pyqt.quickdialog as quickdialog
#import vigra.pyqt.quickdialog as quickdialog
#import VigraQt; -- we can do away without it; some classes used by vigra.pyqt

#### END 3rd party modules

#### BEGIN pict.iolib modules
from iolib import pictio as pio
#### END pict.iolib modules

#### BEGIN pict.core modules
from core import datatypes as dt
import core.utilities as utilities
from core.utilities import safeWrapper
from core import neoutils as neoutils
from core import xmlutils, strutils
from core import neoevent, neoepoch
#from core.patchneo import *
from core.workspacefunctions import validateVarName

#### BEGIN pict.gui modules
#from . import imageviewer as iv
from . import pictgui as pgui
from . import quickdialog
#from .pictgui import GraphicsObjectType, GraphicsObject, PathElements, Tier2PathElements, SignalCursor, Path, Start, Move, Line, Cubic, Rect, Ellipse, Quad, Arc, ArcMove
from .scipyenviewer import ScipyenViewer, ScipyenFrameViewer
from .dictviewer import InteractiveTreeWidget, DataViewer
#### END pict.gui modules

# each spike is a small vertical line centered at 0.0, height of 1
if "spike" not in pg.graphicsItems.ScatterPlotItem.Symbols.keys():
    spike = QtGui.QPainterPath(QtCore.QPointF(0.0, -0.5))
    spike.lineTo(QtCore.QPointF(0.0, 0.5))
    spike.closeSubpath()
    pg.graphicsItems.ScatterPlotItem.Symbols["spike"] = spike

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
 
class SignalCursor(QtCore.QObject):
    """SignalCursor object.
    Covers either a SINGLE pyqtgraph.PlotItem (see crosshair.py in pyqtgraph/examples)
    or a pyqtgraph.GraphicsScene (with possibly multiple plot items)
    """
    # TODO: 2019-02-07 17:31:43
    # 1) implement cursors linking
    
    sig_cursorSelected = pyqtSignal(str, name="sig_cursorSelected") 
    sig_cursorDeselected = pyqtSignal(str, name="sig_cursorDeselected") 
    #sig_cursorMoved = pyqtSignal(str, float, float, name="sig_cursorMoved")
    sig_editMe = pyqtSignal(str, name="sig_editMe")
    sig_reportPosition = pyqtSignal(str, name="sig_reportPosition")
    #sig_reportDynamicPosition = pyqtSignal(str, name="sig_reportDynamicPosition")
    sig_doubleClicked = pyqtSignal(str, name = "sig_doubleClicked")
    
    sig_axisPositionChanged = pyqtSignal(tuple, name="sig_axisPositionChanged")

    #_cursorTypes_ = {(True, True):'crosshair', (True, False):'horizontal', (False,True):'vertical'}
    
    class SignalCursorTypes(Enum):
        """Enumeration of signal cursor types.
        """
        vertical    = (False, True)
        horizontal  = (True, False)
        crosshair   = (True, True)
        
        @classmethod
        def names(cls):
            """List of the signal cursor type names
            """
            return [c.name for c in cls]
        
        @classmethod
        def values(cls):
            """List with the values to which the signal cursor types are mapped.
            """
            return [c.value for c in cls]
        
        @classmethod
        def default(cls):
            """The default signal cursor type
            """
            return cls.crosshair
        
        @classmethod
        def types(cls):
            """List of the defined signal cursor types.
            """
            return list(cls)
        
        @classmethod
        def getType(cls, value: tuple):
            """Inverse-lookup: returns signal cursor type mapped to value.
            
            Returns None if no signal cursor type is mapped to this value.
            """
            if isinstance(value, (tuple, list)) and len(value) == 2 and all([isinstance(v, bool) for v in value]):
                value = tuple(value) # force cast to a tuple
                types = [c for c in cls if c.value == value]
                if len(types):
                    return types[0]
                
                #types_values = [tv for nv in zip(*[(c, c.value) for c in cls])]
                #types = types_values[0]
                #values = types_values[1]
                #if value in values:
                    #return types[values.index(value)]
        
        @classmethod
        def getName(cls, value: tuple):
            """Inverse-lookup for name of a signal cursor type given its value.
            
            Returns None if no signal cursor type is mapped to this value.
            """
            if isinstance(value, (tuple, list)) and len(value) == 2 and all([isinstance(v, bool) for v in value]):
                value = tuple(value) # force cast to a tuple
                types = [c for c in cls if c.value == value]
                #print(types)
                if len(types):
                    return types[0].name
                
                #names_values = [nv for nv in zip(*[(c.name, c.value) for c in cls])]
                #names = names_values[0]
                #values = names_values[1]
                #if value in values:
                    #return names[values.index(value)]
                
    def __init__(self, plot_item, x=None, y=None, xwindow=0.0, ywindow=0.0,
                 cursor_type = None, cursorID="c", follower=False, parent=None, 
                 xBounds=None, yBounds=None, 
                 pen=None, hoverPen=None, linkedPen=None,
                 **kwargs):
        
        super(SignalCursor, self).__init__(parent=parent)
        
        #print("SignalCursor.__init__ cursor_type", cursor_type)
        
        if not isinstance(parent, (SignalViewer, pg.PlotItem)):
            raise TypeError("parent object of a SignalCursor can only be a pyqtgraph PlotItem or a SignalViewer; got %s instead" % type(parent).__name__)
        
        self._parent_plot_window_ = None
        
        self._host_graphics_item_ = None
        
        if not isinstance(plot_item, (pg.PlotItem, pg.GraphicsScene)):
            raise TypeError("plot_item expected to be a pyqtgraph.PlotItem object or a pyqtgraph.GraphicsScene object got %s instead" % type(plot_items).__name__)
        
        self._host_graphics_item_ = plot_item
        
        #self.__is_single_axis__ = isinstance(self._host_graphics_item_, pg.GraphicsScene)
        
        if isinstance(parent, SignalViewer):
            self._parent_plot_window_ = parent
            
        elif isinstance(parent, (pg.PlotItem, pg.GraphicsScene)) and self._host_graphics_item_ is None:
            self._host_graphics_item_ = parent
            
        self._cursorId_ = None
        
        self._follows_mouse_ = False
        
        self._is_selected_ = False
        
        self._hl_ = None
        self._vl_ = None
        
        self._x_ = None
        self._y_ = None
        
        self._hWin_ = None
        self._vWin_ = None
        
        self._cursor_type_ = None
        
        self._default_pen_ = None
        
        if isinstance(pen, QtGui.QPen):
            self._pen_ = pen
            
        else:
            self._pen_ = None
        
        if isinstance(hoverPen, QtGui.QPen):
            self._hoverPen_ = hoverPen
            
        else:
            self._hoverPen_ = None
        
        if isinstance(linkedPen, QtGui.QPen):
            self._linkedPen_ = linkedPen
            
        else:
            self._linkedPen_ = None
        
        # valid ranges where the cursor lines can go
        self._x_range_ = None
        self._y_range_ = None
        
        if self._pen_ is None:
            self._pen_ = kwargs.pop("pen", None)
            
        if self._linkedPen_ is None:
            self._linkedPen_ = kwargs.pop("linkedPen", None)
            
        if self._hoverPen_ is None:
            self._hoverPen_ = kwargs.pop("hoverPen", None)
        
        # dict that maps PlotItem objects to SignalProxy objects -- only used for 
        # dynamic cursors
        self._signal_proxy_ = None
        
        self._linked_cursors_ = list()
        
        self._linked_ = False
        
        # for static cursors only (see InifiniteLine for the logic)
        # to make the lines move in concert
        self._dragging_ = False
        
        self._current_plot_item_ = None # for multi-axes cursors
        
        self._setup_(plot_item, x=x, y=y, xwindow=xwindow, ywindow=ywindow, 
                         cursor_type=cursor_type, cursorID=cursorID,
                         follower=follower, xBounds = xBounds, yBounds=yBounds,
                         **kwargs)
        
    def _setup_lines_(self, h, v, **kwargs):
        name = kwargs.get("name", self._cursor_type_)
            
        kwargs.pop("name", None)
        
        if self._follows_mouse_:
            pos = QtCore.QPointF()
            self._x_ = pos.x()
            self._y_ = pos.y()
            
        else:
            pos = QtCore.QPointF(self._x_, self._y_)
            
        scene = self.hostScene
        
        if h:
            if not isinstance(self._hl_, pg.InfiniteLine):
                self._hl_ = pg.InfiniteLine(pos=pos, 
                                              angle=0, 
                                              movable=not self._follows_mouse_, 
                                              name="%s_h" % name, 
                                              label=self._cursorId_,
                                              pen=self._pen_, 
                                              hoverPen = self._hoverPen_)
            
                if not self._follows_mouse_:
                    if self._cursor_type_ == "horizontal":
                        self._hl_.sigDragged.connect(self.slot_positionChanged)
                        self._hl_.sigPositionChanged.connect(self.slot_positionChanged)
                        self._hl_.sigPositionChangeFinished.connect(self.slot_positionChanged)
                        
            if isinstance(self._pen_, QtGui.QPen):
                self._hl_.setPen(self._pen_)
                
            elif isinstance(self._default_pen_, QtGui.QPen):
                self._pen_ = self._default_pen_
                self._hl_.setPen(self._pen_)
                
            else:
                self._default_pen_ = self._hl_.pen
                self._pen_ = self._hl_.pen
                
            if isinstance(self._hoverPen_, QtGui.QPen):
                self._hl_.setHoverPen(self._hoverPen_)
                
            else:
                self._hoverPen_ = self._hl_.hoverPen
                    
            self._hl_.setBounds(self._y_range_)
            
        else:
            self._hl_ = None
            
        #print("_setup_lines_ after hl xy", (self.x, self.y))
            
        if v:
            if not isinstance(self._vl_, pg.InfiniteLine):
                self._vl_ = pg.InfiniteLine(pos=pos, 
                                              angle=90, 
                                              movable=not self._follows_mouse_,
                                              name="%s_v" % name, 
                                              label=self._cursorId_,
                                              pen=self._pen_, 
                                              hoverPen = self._hoverPen_)
            
                if not self._follows_mouse_: 
                    if self._cursor_type_ == "vertical":
                        self._vl_.sigDragged.connect(self.slot_positionChanged)
                        self._vl_.sigPositionChanged.connect(self.slot_positionChanged)
                        self._vl_.sigPositionChangeFinished.connect(self.slot_positionChanged)
                        
            if isinstance(self._pen_, QtGui.QPen):
                self._vl_.setPen(self._pen_)
                
            elif isinstance(self._default_pen_, QtGui.QPen):
                self._pen_ = self._default_pen_
                self._vl_.setPen(self._pen_)
                
            else:
                self._default_pen_ = self._vl_.pen
                self._pen_ = self._vl_.pen
                
            if isinstance(self._hoverPen_, QtGui.QPen):
                self._vl_.setHoverPen(self._hoverPen_)
                
            else:
                self._hoverPen_ = self._vl_.hoverPen
                    
            self._vl_.setBounds(self._x_range_)
            
        else:
            self._vl_ = None
            
        if not isinstance(self._linkedPen_, QtGui.QPen):
            self._linkedPen_ = self._default_pen_
            
        if not self._follows_mouse_:
            scene.sigMouseMoved.connect(self._slot_mouse_event_)
            
    def _get_plotitem_data_bounds_(self, item):
        plotDataItems = [i for i in item.listDataItems() if isinstance(i, pg.PlotDataItem)]
        
        mfun = lambda x: -np.inf if x is None else x
        pfun = lambda x: np.inf if x is None else x
        
        xmin = min(map(mfun, [p.dataBounds(0)[0] for p in plotDataItems]))
        xmax = max(map(pfun, [p.dataBounds(0)[1] for p in plotDataItems]))
                
        ymin = min(map(mfun, [p.dataBounds(1)[0] for p in plotDataItems]))
        ymax = max(map(pfun, [p.dataBounds(1)[1] for p in plotDataItems]))
                
        #xmin = min([-np.inf if p.dataBounds(0)[0] is None else p.dataBounds(0)[0] for p in plotDataItems])
        #xmax = max([np.inf if p.dataBounds(0)[1] is None else p.dataBounds(0)[1] for p in plotDataItems])
        
        #ymin = min([-np.inf if p.dataBounds(1)[0] is None else p.dataBounds(1)[0] for p in plotDataItems])
        #ymax = max([np.inf if p.dataBounds(1)[1] is None else p.dataBounds(1)[1] for p in plotDataItems])
        
        return [[xmin, xmax], [ymin, ymax]]
        
    def _get_host_boundaries_(self, host):
        """Get the useful boundaries for cursor lines, from the host
        (unless they've been specified by caller)
        Boundaries returnes in same format as for PlotItem.viewRange()
        """
        if isinstance(host, pg.PlotItem):
            return self._get_plotitem_data_bounds_(host)
        
        elif isinstance(host, pg.GraphicsScene):
            # host is a graphics scene when the cursor is intended to span
            # NOTE 2019-02-07 17:14:27
            # several axes.
            # In this case, I cannot rely on data bounds (viewRange()[1]) 
            # because each data in the plot can have different scales;
            # so I have to rely on the plotitems' bounding rects
            # 
            # for best pracice, pre-determine the bounds in the caller, according
            # to the plot items layout, data boundaries and type of cursor
            # (vertical, horizontal or crosshair)
            pIs = [i for i in host.items() if isinstance(i, pg.PlotItem)]
            
            if len(pIs):
                # NOTE: 2019-02-07 17:25:24
                # the disadvantage of this apporoach is that we can now move the cursor
                # beyond the data boundaries, but then see NOTE 2019-02-07 17:14:27
                
                ## each range is [[xmin,xmax], [ymin,ymax]]
                #ranges = [self._get_plotitem_data_bounds_(p) for p in pIs]
                
                #xmin = min([rg[0][0] for rg in ranges])
                #xmax = 
                
                min_x = np.min([p.vb.boundingRect().x() for p in pIs])
                max_x = np.max([p.vb.boundingRect().x() + p.sceneBoundingRect().width() for p in pIs])
                
                min_y = np.min([p.vb.boundingRect().y() for p in pIs])
                max_y = np.max([p.vb.boundingRect().y() + p.sceneBoundingRect().height() for p in pIs])
                
                min_point = QtCore.QPointF(min_x, min_y)
                max_point = QtCore.QPointF(max_x, max_y)
                
            else:
                min_point = QtCore.QPointF(host.sceneRect().x(), host.sceneRect().y())
                
                max_point = QtCore.QPointF(host.sceneRect().x() + host.sceneRect().width(),
                                           host.sceneRect().y() + host.sceneRect().height())
                
            return [[min_point.x(), max_point.x()], [min_point.y(), max_point.y()]]
            
        else:
            raise TypeError("expecting a pyqtgraph.PlotItem or a pyqtgraph.GraphicsScene; got %s instead" % type(host).__name__)
        
    def _update_hline_position_(self, val, plotitem=None):
        if isinstance(self._host_graphics_item_, pg.PlotItem):
            self._hl_.setPos(val)
            self._y_ = self._hl_.getYPos()
            
        else:
            if plotitem is None:
                plotitem = self._current_plot_item_
                
            if self._current_plot_item_ is None:
                raise RuntimeError("Cannot determine the current plot item; consider calling self.setY(value, plotItem)")
            
            new_Y = plotItem.vb.mapViewToScene(QtCore.QPointF(0.0, val)).y()
            
            if self._hl_ is not None:
                self._hl_.setYPos(new_Y)
                self._y_ = self._hl_.getYPos()
                
    def _update_vline_position_(self, val, plotitem=None):
        if isinstance(self._host_graphics_item_, pg.PlotItem):
            self._vl_.setPos(val)
            self._x_ = self._vl_.getXPos()
            
        else:
            if plotitem is None:
                plotitem = self._current_plot_item_
                
            if self._current_plot_item_ is None:
                raise RuntimeError("Cannot determine the current plot item; consider calling self.setX(value, plotItem")
            
            new_X = plotItem.vb.mapViewToScene(QtCore.QPointF(val, 0.0)).x()
            
            if self._vl_ is not None:
                self._vl_.setXPos(new_X)
                self._x_ = self._vl_.getXPos()
                
    def _add_lines_to_host_(self):
        if self._cursor_type_ == "crosshair":
            pos = QtCore.QPointF(self._x_, self._y_)
            
        elif self._cursor_type_ == "horizontal":
            pos = QtCore.QPointF(0.0, self._y_)
            
        else:
            pos = QtCore.QPointF(self._x_, 0.0)
        
        if self._hl_ is not None:
            if isinstance(self._host_graphics_item_, pg.PlotItem):
                self._host_graphics_item_.addItem(self._hl_, ignoreBounds=True)
                
            else:
                self._host_graphics_item_.addItem(self._hl_)
            
        if self._vl_ is not None:
            if isinstance(self._host_graphics_item_, pg.PlotItem):
                self._host_graphics_item_.addItem(self._vl_, ignoreBounds=True)
            else:
                self._host_graphics_item_.addItem(self._vl_)

        if self._follows_mouse_:
            if isinstance(self._host_graphics_item_, pg.PlotItem):
                sig = self._host_graphics_item_.scene().sigMouseMoved
            
            else:
                sig = self._host_graphics_item_.sigMouseMoved
                
            self._signal_proxy_ = pg.SignalProxy(sig, rateLimit=60, slot=self._slot_mouse_moved_)
                
        else:
            if self._hl_ is not None:
                self._hl_.setPos(pos.y())
                    
            if self._vl_ is not None:
                self._vl_.setPos(pos.x())
                    
        #print("_add_lines_to_host_ xy", (self.x, self.y))
        
    @pyqtSlot()
    @pyqtSlot(object)
    @safeWrapper
    def slot_positionChanged(self, evt=None):
        self.sig_cursorSelected.emit(self._cursorId_)
        
        if self._hl_ is not None:
            self._y_ = self._hl_.getYPos()
            
        if self._vl_ is not None:
            self._x_ = self._vl_.getXPos()
            
        if self._cursor_type_ != "crosshair":
            self.sig_reportPosition.emit(self.ID)
            
    @pyqtSlot(tuple)
    @safeWrapper
    def slot_linkedPositionChanged(self, pos):
        signalBlockers = [QtCore.QSignalBlocker(c) for c in self._linked_cursors_]
        self.x = pos[0]
        self.y = pos[1]
        
    @pyqtSlot()
    @safeWrapper
    def _slot_line_selected_(self):
        if not self._follows_mouse_:
            self._is_selected_ = True
            self.sig_cursorSelected.emit(self.ID)
            
        
    @pyqtSlot(bool)
    @safeWrapper
    def slot_setSelected(self, val):
        if not self._follows_mouse_:
            if not isinstance(val, bool):
                self._is_selected_ = False
                
            else:
                self._is_selected_ = val
            
    def setBounds(self, host=None, xBounds=None, yBounds=None):
        if host is None:
            host = self._host_graphics_item_
            
        hostBounds = self._get_host_boundaries_(host) # [[xmin, xmax], [ymin, ymax]]
        
        if isinstance(xBounds, (tuple, list)) and len(xBounds) == 2:
            if all([isinstance(v, numbers.Number) for v in xBounds]):
                self._x_range_ = xBounds
                
            elif all([isinstance(v, pq.Quantity) and len(v) == 1 for v in xBounds]):
                self._x_range_  = [v.flatten().magnitude for v in xBounds]
                
        elif isinstance(xBounds, np.ndarray) and xBounds.ndim> 0 and len(xBounds) == 2:
            if isinstance(xBounds, pq.Quantity):
                xBounds = xBounds.flatten().magnitude
                
            self._x_range_ = [v for v in xBounds]
            
        elif xBounds is not None:
            raise TypeError("xBounds expected to be a sequence of two (possibly Quantity) scalars, or a numpy or Quantity array with two elements")
            
        else:
            self._x_range_ = hostBounds[0]
            
        if self._vl_ is not None:
            self._vl_.setBounds(self._x_range_)

        if isinstance(yBounds, (tuple, list)) and len(yBounds) == 2:
            if all([isinstance(v, numbers.Number) for v in yBounds]):
                self._y_range_ = yBounds
            
            elif all([isinstance(v, pq.Quantity) and len(v) == 1 for v in xBounds]):
                self._y_range_  = [v.flatten().magnitude for v in xBounds]
            
        elif isinstance(yBounds, np.ndarray) and yBounds.ndim> 0 and len(yBounds) == 2:
            if isinstance(yBounds, pq.Quantity):
                yBounds = yBounds.flatten().magnitude
                
            self._y_range_ = [v for v in yBounds]
            
        elif yBounds is not None:
            raise TypeError("yBounds expected to be a sequence of two (possibly Quantity) scalars, or a numpy or Quantity array with two elements")
            
        else:
            self._y_range_ = hostBounds[1]
            
        if self._hl_ is not None:
            self._hl_.setBounds(self._y_range_)
            
    def linkTo(self, *other):
        """ Bidirectionally link this cursor to at least another one of the same type.
        All other cursors will be linked to this one and to each other.
        For linked cursors, when one is moved by dx, dy, the linked cursor(s) is (are) 
        moved by the same distance.
        """
        for c in other:
            if self.cursorType != c.cursorType:
                print('Can link only to SignalCursor instance of the same type')
                return False
            
            if c not in self._linked_cursors_: # avoid "double" linking
                self._linked_cursors_.append(c)
                self.sig_axisPositionChanged[tuple].connect(c.slot_linkedPositionChanged)
            
            if self not in c._linked_cursors_: # avoid double linking
                c._linked_cursors_.append(self)
                s.sig_axisPositionChanged[tuple].connect(self.slot_linkedPositionChanged)
            
            for cc in other:
                if cc is not c and c not in cc._linked_cursors_:# avoid "double" linking
                    cc._linked_cursors_.append(c)
                    cc.sig_axisPositionChanged[tuple].connect(c.slot_linkedPositionChanged)
                    
                if len(cc._linked_cursors_) > 0:
                    cc.pen = self.linkedPen
                     
            if len(c._linked_cursors_) > 0:
                c.pen = c.linkedPen
                
        if len(self._linked_cursors_) > 0:
            self._linked_ = True
            
    def unlinkFrom(self, *other):
        ret = False
        
        if len(other) > 0:
            for c in other:
                if self.cursorType != c.cursorType:
                    print('Can link only to SignalCursor instance of the same type')
                    return ret
                
                if self in c._linked_cursors_:
                    c._linked_cursors_.remove(self)
                    c.sig_axisPositionChanged[tuple].disconnect(self.slot_linkedPositionChanged)
                    
                    ret = True
                    
                if c in self._linked_cursors_:
                    self._linked_cursors_.remove(c)
                    self.sig_axisPositionChanged[tuple].disconnect(c.slot_linkedPositionChanged)
                    ret = True
                
                if len(c._linked_cursors_) == 0:
                    c.pen = c._default_pen_
                    c._linked_ = False
                
            if len(self._linkedCursors) == 0:
                self.pen = self._default_pen_
                self._linked_ = False
                
            ret = len(self._linkedCursors) == 0
        
        else:
            if len(self._linked_cursors_) > 0:
                for c in self._linked_cursors_:
                    if self in c._linked_cursors_:
                        c._linked_cursors_.remove(self)
                        c.sig_axisPositionChanged[tuple].disconnect(self.slot_linkedPositionChanged)
                        
                    if len(c._linked_cursors_) == 0:
                        c.pen = c._default_pen_
                        c._linked_ = False
                
                self._linked_cursors_.clear()
                self.pen = self._default_pen_
                self._linked_ = False
                
            ret = True
            
        return ret
            
    def detach(self):
        if self._hl_ is not None:
            self._host_graphics_item_.removeItem(self._hl_)
            
        if self._vl_ is not None:
            self._host_graphics_item_.removeItem(self._vl_)
            
        if isinstance(self._signal_proxy_, pg.SignalProxy):
            self._signal_proxy_.disconnect()
            self._signal_proxy_ = None
            
    def attach(self, host, xBounds=None, yBounds=None, pos=None):
        """Attaches this cursor to a PlotItem or a GraphicsScene 
        (of the pyqtgraph framework)
        TODO allow the attaching to a scene a cursor formerly attached to a 
        plot item, aned vice-versa
        this means we have to compute appropriate position coordinates!
        """
        self.setBounds(host, xBounds=xBounds, yBounds=yBounds)
        
        if pos is None:
            if self._x_ is None:
                self._x_ = 0.0
                
            if self._y_ is None:
                self._y_ = 0.0
                
            
        elif isinstance(pos, (QtCore.QPoint, QtCore.QPointF)):
            self._x_ = float(val.x())
            self._y_ = float(val.y())
            
        elif isinstance(pos, (tuple, list)) and len(val) == 2 and all([isinstance(v, (number.Number, type(None))) for v in val]):
            self._x_ = val[0]
            self._y_ = val[1]
        
        else:
            raise TypeError("pos expected to be a QtCore.QPoint or QPointF or a pair of numbers or None")
        
        ctype_ndx = [v for v in SignalCursor._cursorTypes_.values()].index(self._cursor_type_)
        keys = [k for k in SignalCursor._cursorTypes_.keys()]

        show_lines = keys[ctype_ndx]
        
        self._host_graphics_item_ = host
            
        self._setup_lines_(*show_lines)
            
        self._add_lines_to_host_()
        
    def _setup_(self, host, cursor_type="crosshair", x=None, y=None, 
                  xwindow=None, ywindow=None, follower=False, cursorID=None, 
                  xBounds=None, yBounds=None, **kwargs):
        
        #print("SignalCursor._setup_ cursor_type %s" % cursor_type)
        
        show_lines = (False, False)
        
        if isinstance(cursor_type, str):
            if len(cursor_type) == 1:
                c_type_name = [name for name in SignalCursorTypes.names() if name.startswith(cursor_type)]
                if len(c_type_name):
                    cursor_type = SignalCursor.SignalCursorTypes[c_type_name[0]]
                    
                else:
                    cursor_type = None
                
            else:
                if cursor_type in SignalCursor.SignalCursorTypes.names():
                    cursor_type = SignalCursor.SignalCursorTypes[cursor_type]
                    
                else:
                    cursor_type = None
                
        elif isinstance(cursor_type, (tuple, list)) and len(cursor_type) == 2 and all([isinstance(b, bool) for c in cursor_type]):
            cursor_type = Signalcursor.SignalCursorTypes.getType(cursor_type) # this may return None
            
        elif not isinstance(cursor_type, SignalCursor.SignalCursorTypes):
            raise TypeError("cursor_type expectec to be a str, a tuple of two booleans or a SignalCursor.SignalCursorTypes; got %s instead" % type(cursor_type).__name__)
            
        # to avoid doubts, is cursor_type is None then fallback to the default (crosshair)
        if cursor_type is None:
            cursor_type = SignalCursor.SignalCursorTypes.crosshair
            
        # now we can set which lines are shown
        show_lines = cursor_type.value
        
        self._cursor_type_ = cursor_type
            
        #print("show_lines", show_lines)
        
        self.setBounds(host, xBounds=xBounds, yBounds=yBounds)
        
        if isinstance(x, numbers.Number):
            self._x_ = x
            
        elif isinstance(x, pq.Quantity):
            self._x_ = x.magnitude.flatten()[0]
            
        elif x is None:
            self._x_ = self._x_range_[0] + np.diff(self._x_range_)/2
            
        else:
            raise TypeError("x expected to be a number, python Quantity or None; got %s instead" % type(x).__name__)
            
        if isinstance(y, numbers.Number):
            self._y_ = y
            
        elif isinstance(y, pq.Quantity):
            self._y_ = y.magnitude.flatten()[0]
            
        elif y is None:
            self._y_ = self._y_range_[0] + np.diff(self._y_range_)/2
        
        else:
            raise TypeError("y expected to be a number, python Quantity or None; got %s instead" % type(y).__name__)
            
        if isinstance(xwindow, numbers.Number):
            self._hWin_ = xwindow
            
        elif isinstance(xwindow, pq.Quantity):
            self._hWin_ = xwindow.magnitude.flatten()[0]
            
        elif xwindow is None:
            self._hWin_ = 0.0
            
        else:
            raise TypeError("xwindow expected to be a number, python Quantity or None; got %s instead" % type(xwindow).__name__)
            
        if isinstance(ywindow, numbers.Number):
            self._vWin_ = ywindow
            
        elif isinstance(ywindow, pq.Quantity):
            self._vWin_ = ywindow.magnitude.flatten()[0]
            
        elif ywindow is None:
            self._vWin_ = 0.0
            
        else:
            raise TypeError("ywindow expected to be a number, python Quantity or None; got %s instead" % type(ywindow).__name__)
        
        if follower:
            if cursorID is None:
                cursorID = "d"
                
            elif isinstance(cursorID, str) and len(cursorID.strip()) == 0:
                cursorID = "d"
                
        else:
            if cursor_type == "crosshair":
                if cursorID is None:
                    cursorID = "c"
                    
                elif isinstance(cursorID, str) and len(cursorID.strip()) == 0:
                    cursorID = "c"
                    
            elif cursor_type == "horizontal":
                if cursorID is None:
                    cursorID = "h"
                    
                elif isinstance(cursorID, str) and len(cursorID.strip()) == 0:
                    cursorID = "h"
                    
                
            elif cursor_type == "vertical":
                if cursorID is None:
                    cursorID = "v"
                    
                elif isinstance(cursorID, str) and len(cursorID.strip()) == 0:
                    cursorID = "v"

        self._cursorId_ = cursorID
        
        self._follows_mouse_ = follower
        
        # NOTE: 2019-02-03 14:48:05
        # override default value of "movable"
        if isinstance(host, pg.GraphicsScene):
            kwargs["movable"] = not self._follows_mouse_
            
        else:
            kwargs["movable"] = False
        
        if "name" not in kwargs.keys():
            kwargs["name"] = self._cursor_type_

        self._setup_lines_(*show_lines, **kwargs)
        
        #print("_setup_ after _setup_lines_ xy", (self.x, self.y))
        
        self._add_lines_to_host_()
        #print("_setup_ after __add_lines_to_host__ xy", (self.x, self.y))
        
    def _interpret_scene_mouse_events_(self, scene=None):
        """
        """
        if scene is None or not isinstance(scene, pg.GraphicsScene):
            scene = self.hostScene
            
        if scene is None:
            return
        
        self._dragging_ = False
        
        if scene.dragItem is not None:
            if all([l is not None for l in (self._vl_, self._hl_)]):
                if scene.dragItem in (self._vl_, self._hl_):
                    self._dragging_ = True
                    
    @pyqtSlot(object)
    @safeWrapper
    def _slot_selected_in_scene_(self, evt):
        # NOTE: 2019-02-09 23:29:22
        # here, evt is a mouse event
        scene = self.hostScene
        
        items = scene.items(evt.pos())
        
        if (self.vline is not None and self.vline in items) or \
            (self.hline is not None and self.hline in items):
            self.sig_cursorSelected.emit(self.ID)
            
    @pyqtSlot(object)
    @safeWrapper
    def _slot_mouse_event_(self, evt):
        """Workaround to synchronize movement of BOTH lines when mouse is dragged in the scene.
        Calls _interpret_scene_mouse_events_ because to find out if any of the lines
        has been clicked on and if it's being dragged.
        """
        # NOTE: 2019-02-09 12:45:02
        # We cannot rely on sigDragged signal from the line we currently interact from
        # to inform the movement of the other line, because each of the cursor's 
        # lines have one of the coordinates set to 0.0 (being orthogonal)
        
        # ATTENTION: 2019-02-09 23:11:56
        # evt is a QtCore.QPointF, and NOT a mouse event object !!!
        
        scene = self.hostScene
        
        self._interpret_scene_mouse_events_(scene)
        
        if self._dragging_ and self._cursor_type_ == "crosshair":
            self.sig_cursorSelected.emit(self._cursorId_)

            if isinstance(evt, (tuple, list)):
                pos = evt[0] 
                
            else:
                pos = evt
                
            if isinstance(pos, (QtCore.QPointF, QtCore.QPoint)):
                self._update_lines_from_pos_(pos)
            
        else:
            if scene is not None and len(scene.clickEvents):
                #print("SignalCursor._slot_mouse_event_ scene.clickEvents", scene.clickEvents)
                mouseClickEvents = [e for e in scene.clickEvents if type(e).__name__ == "MouseClickEvent"]
                #print("SignalCursor._slot_mouse_event_ mouseClickEvents", mouseClickEvents)
                # NOTE: 2019-11-28 15:15:37
                # douyble-click events do not seem to be captured ?
                #print("SignalCursor._slot_mouse_event_ is double click", [e.double() for e in mouseClickEvents])
                
                if len(mouseClickEvents):
                    #print("SignalCursor._slot_mouse_event_ modifiers", mouseClickEvents[0].modifiers())
                    #print("SignalCursor._slot_mouse_event_ double", mouseClickEvents[0].double())
                    #print("SignalCursor._slot_mouse_event_ double", mouseClickEvents[0].button())
                    items = scene.items(evt)
                    
                    if any([i is not None and i in items for i in (self.vline, self.hline)]):
                        self.sig_cursorSelected.emit(self.ID)
                        
                        #print("SignalCursor._slot_mouse_event_", QtWidgets.QApplication.keyboardModifiers())
                        
                        if bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier):
                            self.sig_editMe.emit(self.ID)
                        
                        
                    #if self.vline is not None and self.vline in items:
                        #self.sig_cursorSelected.emit(self.ID)
                        
                    #if self.hline is not None and self.hline in items:
                        #self.sig_cursorSelected.emit(self.ID)
                    
                #if "MouseClickEvent" in str(scene.clickEvents[0]):
                    ##print("click %s" % scene.clickEvents[0])
                    #items = scene.items(evt)
                    
                    #if self.vline is not None and self.vline in items:
                        #self.sig_cursorSelected.emit(self.ID)
                        
                    #if self.hline is not None and self.hline in items:
                        #self.sig_cursorSelected.emit(self.ID)
                
            #try:
                #if len(scene.clickEvents):
                    #if "MouseClickEvent" in str(scene.clickEvents[0]):
                        ##print("click %s" % scene.clickEvents[0])
                        #items = scene.items(evt)
                        
                        #if self.vline is not None and self.vline in items:
                            #self.sig_cursorSelected.emit(self.ID)
                            
                        #if self.hline is not None and self.hline in items:
                            #self.sig_cursorSelected.emit(self.ID)
                    
            #except:
                #pass
                
    def _slot_mouse_moved_(self, evt):
        """Use only for dynamic cursors
        """
        # CAUTION
        # when activated by the scene sigMouseMoved signal, this carries the
        # mouse event's scenePos()
        if not self._follows_mouse_:
            return
        
        if isinstance(evt, (tuple, list)):
            pos = evt[0] 
            
        else:
            pos = evt

        self._update_lines_from_pos_(pos)
        
    def _update_lines_from_pos_(self, pos):
        # CAUTION
        # when activated by the scene sigMouseMoved signal, this carries the
        # mouse event's scenePos(); what if pos is NOT this but a point in 
        # other coordinate system?
        
        if isinstance(self._host_graphics_item_, pg.PlotItem):
            self._current_plot_item_ = self._host_graphics_item_
            
            if self._host_graphics_item_.sceneBoundingRect().contains(pos):
                mp = self._host_graphics_item_.vb.mapSceneToView(pos)
                
                di = [d for d in self._host_graphics_item_.items if isinstance(d, pg.PlotDataItem)]
                
                if len(di):
                    d = di[0]
                    
                    if mp.x() >= d.xData[0] and mp.x() <= d.xData[-1]:
                        if self._hl_ is not None:
                            self._hl_.setPos(mp.y())
                            self._y_ = mp.y()
                            
                        if self._vl_ is not None:
                            self._vl_.setPos(mp.x())
                            self._x_ = mp.x()
                            
                # NOTE: only report position when mouse is in the sceneBoundingRect
                self.sig_reportPosition.emit(self.ID)
                
        elif isinstance(self._host_graphics_item_, pg.GraphicsScene):
            # FIXME  2019-02-10 21:30:29
            # for multiaxes crosshair the horizontal line is stuck on top plot item
            if self._hl_ is not None:
                self._hl_.setPos(pos.y())
                self._y_ = pos.y()
                
            if self._vl_ is not None:
                self._vl_.setPos(pos.x())
                self._x_ = pos.x()
                
            self.sig_reportPosition.emit(self.ID)
            
        self.sig_axisPositionChanged.emit((self.x, self.y))
            
        # NOTE: this will cause re-entrant code!
        #if self._linked_ and len(self._linked_cursors_):
            #for c in self._linked_cursors_:
                ## CAUTION this may crash if no curent plot item is defined in C
                #c.x = self.x
                #c.y = self.y
            
    @property
    def hostScene(self):
        if isinstance(self._host_graphics_item_, pg.PlotItem):
            return self._host_graphics_item_.scene()
        
        else:
            return self._host_graphics_item_
        
    @property
    def scenePlotItems(self):
        """An ordered mapping (collections.OrderedDict) of PlotItems 
        The plot items are those available to this cursor in the parent widget.
        Returns a map of plot item (key) to its tuple of (x,y) coordinates in the scene (value).
        These would include the plot item host of the cursor (for single axis cursors).
        """
        # get a list of all plot items in the scene
        # CAUTION they may be hosted in different layouts!
        plotitems = [i for i in self.hostScene.items() if isinstance(i, pg.PlotItem)]
        
        # FIXME: we're assuming the cursors are in a SignalViewer window (the only one
        # that supports multi-axes cursors)
        # therefore we're returning a list of plot items sorted by their Y coordinate 
        # in the scene (as a SignalViewer will lay lot items vertically)
        
        # sort plot items by their row & column coordinate (i.e. x, and y coordinate)
        # NOTE: in the scene, coordinate (0, 0) is the TOP LEFT 
        pits = sorted(sorted(plotitems, key = lambda x: x.pos().y()), key=lambda x: x.pos().x())
        
        return collections.OrderedDict([(p, (p.pos().x(), p.pos().y())) for p in pits])
        
    @property
    def hostItem(self):
        """Read-only:
        The GraphicsItem that hosts this cursor.
        Currently, this is either a PlotItem, or a GraphicsScene
        """
        return self._host_graphics_item_
    
    @property
    def isSingleAxis(self):
        return isinstance(self._host_graphics_item_, pg.PlotItem)
    
    @property
    def isMultiAxis(self):
        return not self.isSingleAxis
    
    @property
    def vline(self):
        """Read-only
        """
        return self._vl_
    
    @property
    def hline(self):
        """Read-only
        """
        return self._hl_
    
    @property
    def pos(self):
        return QtCore.QPointF(self.x, self.y)
    
    @pos.setter
    def pos(self, val):
        if isinstance(val, (QtCore.QPoint, QtCore.QPointF)):
            self.x = float(val.x())
            self.y = float(val.y())
            
        elif isinstance(val, (tuple, list)) and len(val) == 2 and all([isinstance(v, (number.Number, type(None))) for v in val]):
            self.x = val[0]
            self.y = val[1]
            
    @property
    def parameters(self):
        """A tuple with cursor parameters.
        
        Vertical cursors: (x, xwindow, ID)
        
        Horizontal cursors: (y, ywindow, ID)
        
        Crosshair cursors: (x, xwindow, y, ywindow, ID)
        
        """
        if self.cursorType == SignalCursor.SignalCursorTypes.vertical:
            return (self.x, self.xwindow, self.ID)
        
        elif self.cursorType == SignalCursor.SignalCursorTypes.horizontal:
            return (self.y, self.ywindow, self.ID)
        
        else:
            return (self.x, self.xwindow, self.y, self.ywindow, self.ID)
        
    @property
    def x(self):
        """The X coordinate of the cursor in axes (PlotItem) data coordinates.
        For multi-axes cursors this will return the value in the "current" PlotItem
        (i.e., the plot where the cursor coordinates are mapped to a point in the
        plot item's view range)
        
        NOTE: To obtain the "y" data coordinate in another PlotItem (axes system)
        that is spanned by the cursor, call self.getX(plotitem)
        """
        if self._hl_ is None and self._vl_ is None:
            return self._x_
        
        if self._vl_ is not None:
            line = self._vl_
            
        else:
            line = self._hl_ # as last resort
        
        if isinstance(self._host_graphics_item_, pg.PlotItem):
            self._current_plot_item_ = self._host_graphics_item_
            return line.getXPos()
            
        else:
            pos = line.getPos() # NOTE: a pair of values, not a QtCore.QPoint/F
            
            plots = [p for p in self.scenePlotItems]
            
            if len(plots):
                # CAUTION this may return None !!!
                for plot in plots:
                    vrange = plot.vb.viewRange()[0]
                    plot_x = plot.vb.mapSceneToView(QtCore.QPointF(pos[0], pos[1])).x()
                    if plot_x >= vrange[0] and plot_x <= vrange[1]:
                        self._current_plot_item_ = plot
                        return plot_x
                    
            else:
                return line.getXPos() # up to the caller to do what it wants with this
    
    @x.setter
    def x(self, val):
        """Expects a value in a plotitem valid range
        """
        if isinstance(val, pq.Quantity):
            val = val.magnitude.flatten()[0]
            
        elif not isinstance(val, numbers.Number):
            raise TypeError("expected a numeric scalar value or a scalar python Quantity; got %s instead" % type(val).__name__)
        
        if self._vl_ is not None:
            self._update_vline_position_(val)
            
    def getX(self, plotitem = None):
        if isinstance(self._host_graphics_item_, pg.PlotItem):
            # so that we can also use this function with single axis cursors
            return self.x
            #return self._host_graphics_item_.vb.mapSceneToView(QtCore.QPointF(self.x, self.y)).x()
        
        else:
            if not isinstance(plotitem, pg.PlotItem):
                raise TypeError("For multi-axes cursors, a pg.PlotItem parameter was expected; got %s instead" % type(plotitem).__name__)
            
            vrange = plotitem.vb.viewRange()[0]
            
            if self._vl_ is not None:
                x = self._vl_.getXPos()
                
            elif self._hl_ is not None: # try this
                x = self._hl_.getXPos()
                
            else:
                x = self._x_ # very last resort; caller should check this
            
            return plotitem.vb.mapSceneToView(QtCore.QPointF(x, 0.0)).x()
            
    def setX(self, val, plotItem=None):
        """Sets the X coordinate of a line.
        
        The X coordinate is specified in axis coordinates
        
        For single-axes cursors, this simply sets the "x" property.
        
        For multi-axes cursor one must also specify the PlotItem in which the value is given
        
        """
        if isinstance(self.hostItem, pg.PlotItem):
            # so that we can also use this function with single axis cursors
            self.x = val
            
        else:
            if isinstance(val, pq.Quantity):
                val = val.magnitude.flatten()[0]
                
            elif not isinstance(val, numbers.Number):
                raise TypeError("expected a numeric scalar value or a scalar python Quantity; got %s instead" % type(val).__name__)
        
            if not isinstance(plotItem, pg.PlotItem):
                raise TypeError("For multi-axis cursor please also specify a PlotItem")
            
            if plotItem not in [p for p in self.scenePlotItems]:
                raise ValueError("Plot item %s not found in this cursor's scene" % plotItem)
            
            self._update_vline_position_(val, plotItem)
            
    @property
    def y(self):
        """The Y coordinate of the cursor in axes (PlotItem) data coordinates.
        For multi-axes cursors this will return the value in the "current" PlotItem
        (i.e., the plot where the cursor coordinates are mapped to a point in the
        plot item's view range)
        
        NOTE: To obtain the "y" data coordinate in another PlotItem (axes system)
        that is spanned by the cursor, call self.getY(plotitem)
        """
        if self._hl_ is None and self._vl_ is None:
            return self._y_
        
        if self._hl_ is not None:
            line = self._hl_
            
        else:
            line = self._vl_ # as last resort
        
        if isinstance(self._host_graphics_item_, pg.PlotItem):
            self._current_plot_item_ = self._host_graphics_item_
            return line.getYPos()
            
        else:
            pos = line.getPos() # NOTE: a pair of values, not a QtCore.QPoint/F
            
            plots = [p for p in self.scenePlotItems]
            
            if len(plots):
                # CAUTION this may return None !!!
                for plot in plots:
                    vrange = plot.vb.viewRange()[1]
                    plot_y = plot.vb.mapSceneToView(QtCore.QPointF(pos[0], pos[1])).y()
                    if plot_y >= vrange[0] and plot_y <= vrange[1]:
                        self._current_plot_item_ = plot
                        return plot_y
                    
            else:
                return line.getYPos() # up to the caller to do what it wants with this
                
    @y.setter
    def y(self, val):
        if isinstance(val, pq.Quantity):
            val = val.magnitude.flatten()[0]
            
        elif not isinstance(val, numbers.Number):
            raise TypeError("expected a numeric scalar value or a scalar python Quantity; got %s instead" % type(val).__name__)
        
        if self._hl_ is not None:
            self._update_hline_position_(val)
            
    def getY(self, plotitem=None):
        if isinstance(self._host_graphics_item_, pg.PlotItem):
            # so that we can also use this function with single axis cursors
            return self.y
            #return self._host_graphics_item_.vb.mapSceneToView(QtCore.QPointF(self.x, self.y)).y()
        
        else:
            if not isinstance(plotitem, pg.PlotItem):
                raise TypeError("For multi-axes cursors, a pg.PlotItem parameter was expected; got %s instead" % type(plotitem).__name__)
            
            vrange = plotitem.vb.viewRange()[0]
            
            if self._hl_ is not None:
                y = self._hl_.getYPos()
                
            elif self._vl_ is not None: # try this
                y = self._vl_.getYPos()
                
            else:
                y = self._y_ # very last resort; caller should check this
            
            return plotitem.vb.mapSceneToView(QtCore.QPointF(0.0, y)).y()
            
    def setY(self, val, plotItem=None):
        if isinstance(self.hostItem, pg.PlotItem):
            # so that we can also use this function with single axis cursors
            self.y = val
            
        else:
            if isinstance(val, pq.Quantity):
                val = val.magnitude.flatten()[0]
                
            elif not isinstance(val, numbers.Number):
                raise TypeError("expected a numeric scalar value or a scalar python Quantity; got %s instead" % type(val).__name__)
        
            if not isinstance(plotItem, pg.PlotItem):
                raise TypeError("For multi-axis cursor please also specify a PlotItem")
            
            if plotItem not in [p for p in self.scenePlotItems]:
                raise ValueError("Plot item %s not found in this cursor's scene" % plotItem)
            
            self._update_hline_position_(val, plotItem)
            
    @property
    def xwindow(self):
        return self._hWin_
    
    @xwindow.setter
    def xwindow(self, val):
        if isinstance(val, pq.Quantity):
            val = val.magnitude.flatten()[0]
            
        elif not isinstance(val, numbers.Number):
            raise TypeError("expected a numeric scalar value or a scalar python Quantity; got %s instead" % type(val).__name__)
        
        self._hWin_ = val
    
    @property
    def ywindow(self):
        return self._vWin_
    
    @ywindow.setter
    def ywindow(self, val):
        if isinstance(val, pq.Quantity):
            val = val.magnitude.flatten()[0]
            
        elif not isinstance(val, numbers.Number):
            raise TypeError("expected a numeric scalar value or a scalar python Quantity; got %s instead" % type(val).__name__)
        
        self._vWin_ = val
        
    @property
    def ID(self):
        return self._cursorId_
    
    @ID.setter
    def ID(self, val):
        if not isinstance(val, str):
            raise TypeError("expecting a string; got %s instead" % type(val).__name__)
        
        if len(val.strip()) == 0:
            warnings.Warning("New ID is empty")
            
        self._cursorId_ = val
        
    @property
    def defaultPen(self):
        return self._default_pen_
    
    @property
    def pen(self):
        """A QtGui.QPen
        """
        return self._pen_
    
    @pen.setter
    def pen(self, val):
        if not isinstance(val, QtGui.QPen):
            raise TypeError("expecting a QtGui.QPen; got a %s instead" % type(val).__name__)
        
        self._pen_ = val
        
        if self._hl_ is not None:
            self._hl_.setPen(self._pen_)
            
        if self._vl_ is not None:
            self._vl_.setPen(self.__pen)
            
    @property
    def linkedPen(self):
        return self._linkedPen_
    
    @linkedPen.setter
    def linkedPen(self, val):
        if not isinstance(val, QtGui.QPen):
            raise TypeError("expecting a QtGui.QPen; got a %s instead" % type(val).__name__)
        
        self._linkedPen_ = val
            
        if self._hl_ is not None:
            self._hl_.setPen(self._linkedPen_)
            
        if self._vl_ is not None:
            self._vl_.setPen(self._linkedPen_)
    
    @property
    def hoverPen(self):
        return self._hoverPen_
    
    @hoverPen.setter
    def hoverPen(self, val):
        if not isinstance(val, QtGui.QPen):
            raise TypeError("expecting a QtGui.QPen; got a %s instead" % type(val).__name__)
        
        self._hoverPen_ = val
        
        if self._hl_ is not None:
            self._hl_.setHoverPen(self._hoverPen_)
            
        if self._vl_ is not None:
            self._vl_.setHoverPen(self._hoverPen_)
    
    @property
    def cursorTypeName(self):
        return self.cursorType.name
    
    @property
    def cursorType(self):
        lines_tuple = (self._hl_ is not None, self._vl_ is not None)
        
        if self._cursor_type_ is None:
            self._cursor_type_ = SignalCursor.SignalCursorTypes.getType(lines_tuple)
            
        elif isinstance(self._cursor_type_, str):
            if self._cursor_type_ in SignalCursor.SignalCursorTypes.names():
                self._cursor_type_ = SignalCursor.SignalCursorTypes[self._cursor_type_]
            
            else:
                self._cursor_type_ = SignalCursor.SignalCursorTypes.getType(lines_tuple)

        elif not isinstance(self._cursor_type_, SignalCursor.SignalCursorTypes):
            self._cursor_type_ = SignalCursor.SignalCursorTypes.getType(lines_tuple)
            
        return self._cursor_type_
                
    @property
    def isSelected(self):
        return self._is_selected_
    
    @property
    def isDynamic(self):
        return self._follows_mouse_
    
    @property
    def isCrosshair(self):
        return self._vl_ is not None and self._hl_ is not None
    
    @property
    def isHorizontal(self):
        return self._hl_ is not None and self._vl_ is None
    
    
    @property
    def isVertical(self):
        return self._vl_ is not None and self._hl_ is None
            
    
###class SignalViewer(QMainWindow, Ui_SignalViewerWindow):
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
    
    closeMe  = pyqtSignal(int)
    frameChanged = pyqtSignal(int)
    
    # TODO: 2019-11-01 22:43:50
    # implement viewing for all these
    supported_types = (neo.Block, neo.Segment, neo.AnalogSignal, 
                       neo.IrregularlySampledSignal, neo.SpikeTrain, neo.Event,
                       neo.Epoch, neo.core.baseneo.BaseNeo,
                        dt.DataSignal, dt.IrregularlySampledDataSignal,
                        dt.TriggerEvent,dt.TriggerProtocol,
                        vigra.filters.Kernel1D, np.ndarray,
                        tuple, list)
    
    view_action_name = "Signal"
        
    defaultCursorWindowSizeX = 0.001
    defaultCursorWindowSizeY = 0.001

    mpl_prop_cycle = plt.rcParams['axes.prop_cycle']
    defaultLineColorsList = ["#000000"] + ["b", "r", "g", "c", "m", "y"]  + mpl_prop_cycle.by_key()['color']
    defaultOverlaidLineColorList = [mpl.colors.to_rgba(c, alpha=0.5) for c in defaultLineColorsList]
        
    defaultSpikeColor    = mpl.colors.to_rgba("xkcd:navy")
    defaultEventColor    = mpl.colors.to_rgba("xkcd:crimson")
    defaultEpochColor    = mpl.colors.to_rgba("xkcd:coral")

    def __init__(self, 
                 x: (neo.core.baseneo.BaseNeo, dt.DataSignal, dt.IrregularlySampledDataSignal, dt.TriggerEvent,dt.TriggerProtocol, vigra.filters.Kernel1D, np.ndarray, tuple, list, type(None)) = None, 
                 y: (neo.core.baseneo.BaseNeo, dt.DataSignal, dt.IrregularlySampledDataSignal, dt.TriggerEvent,dt.TriggerProtocol, vigra.filters.Kernel1D, np.ndarray, tuple, list, type(None)) = None, 
                 parent: (QtWidgets.QMainWindow, type(None)) = None, 
                 pWin: (QtWidgets.QMainWindow, type(None))= None, 
                 ID:(int, type(None)) = None,
                 win_title: (str, type(None)) = None, 
                 doc_title: (str, type(None)) = None,
                 frameIndex:(int, tuple, list, range, slice, type(None)) = None, 
                 frameAxis:(int, type(None)) = None,
                 signalIndex:(str, int, tuple, list, range, slice, type(None)) = None,
                 signalChannelAxis:(int, type(None)) = None,
                 signalChannelIndex:(int, tuple, list, range, slice, type(None)) = None,
                 irregularSignalIndex:(str, int, tuple, list, range, slice, type(None)) = None, 
                 irregularSignalChannelAxis:(int, type(None)) = None,
                 irregularSignalChannelIndex:(int, tuple, list, range, slice, type(None)) = None, 
                 separateSignalChannels:bool = False, 
                 interval:(tuple, list) = None,
                 channelIndex:object = None,
                 currentFrame:(int, type(None)) = None,
                 plotStyle: str = "plot",
                 *args, **kwargs):
        """SignalViewer constructor.
        """
        if y is None:
            if x is not None:  # only the data variable Y is passed, 
                y = x
                x = None  # argument (X) and the expected Y will be None by default
                            # here we swap these two variables and we end up with X as None
                            
        super().__init__(data=y, parent=parent, pWin=pWin, ID=ID,
                         win_title=win_title, doc_title=doc_title,
                         frameIndex=frameIndex, *args, **kwargs)
        self.x = x
        self.y = y
        
        self._plot_names_ = dict() # maps item row position to name
        
        self.crosshairSignalCursors = dict() # a dict of SignalCursors mapping str name to cursor object
        self.verticalSignalCursors = dict()
        self.horizontalSignalCursors = dict()
        self._data_cursors_ = collections.ChainMap(self.crosshairSignalCursors, self.horizontalSignalCursors, self.verticalSignalCursors)
        # NOTE: 2017-05-10 22:57:30
        # these are linked cursors in the same window
        self.linkedCrosshairCursors = []
        self.linkedHorizontalCursors = []
        self.linkedVerticalCursors = []
        
        #### BEGIN data layout attributes
        # see _set_data_ for their use
        # NOTE: self._number_of_frames_ is defined in ScipyenFrameViewer
        self.frameAxis = None
        self.frameIndex = None
        
        # index into neo.ChannelIndex objects (if any)
        # ATTENTION: 2019-11-21 21:42:29
        # NOT to be confused with signal data channels, see NOTE: 2019-11-21 21:40:38
        self.channelIndex = None
        
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
        
        # maps signal name with list of cursors
        # NOTE: 2019-03-08 13:20:50
        # map plot item index (int) with list of cursors
        self._cached_cursors_ = dict()
        #### BEGIN selective representation of neo objects components
        
        # NOTE: 2020-03-09 13:56:32
        # maps frame index to a list of neo.Epochs
        # frames without epochs are absent from the map
        self._cached_epochs_ = dict()
        self._shown_spike_trains_ = dict()
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
        
        self.train_plot_options = dict()
        
        # NOTE: 2019-04-28 18:03:20
        # contrary to online documentation for pyqtgraph 0.10.0, the source code
        # indicates that LinearRegionItem constructor only accepts "brush";
        # "pen" must be delivered direcly to the LinearRegionItem's lines (the
        # item's "lines" attribute)
        # also, there is no mention of "hoverBrush" or "hoverPen" anywhere in the
        # source code for LinearRegionItem or its superclass UIGraphicsItem
        # in fact, hovering just modifes the brush by doubling its alpha value
        self.train_plot_options["train_pen"] = None 
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
        self.guiSelectedSignalNames= list() # list of signal names sl
        
        #self.guiSelectedIrregularSignals = list() # signal indices in collection
        # list of irregularly sampled signal names selected from what is available
        # in the current frame, using the combobox for irregularly sampled signals
        self.guiSelectedIrregularSignalNames = list()
        
        self._plot_analogsignals_ = True
        self._plot_irregularsignals_ = True
        #### END GUI signal selectors and options for compound neo objects
        #### END options for neo objects
        
        
        #### END attributes controlling neo object representations
        
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
        self.default_antialias = True
        
        self.antialias = self.default_antialias
        
        self.default_axis_tick_font = None
        
        self.axis_tick_font = self.default_axis_tick_font
        
        self.plotStyle = "plot"
        
        self.selectedDataCursor = None
        
        self.cursorColors = {"crosshair":"#C173B088", "horizontal":"#B1D28F88", "vertical":"#ff007f88"}
        #self.cursorColors = {"crosshair":"#C173B088", "horizontal":"#B1D28F88", "vertical":"#F2BB8888"}
        #self.linkedCursorColors = {"crosshair":"#B14F9A88", "horizontal":"#77B75388","vertical":"#F29B6888"}
        self.linkedCursorColors = {"crosshair":pg.mkColor(self.cursorColors["crosshair"]).darker(),
                                   "horizontal":pg.mkColor(self.cursorColors["horizontal"]).darker(),
                                   "vertical":pg.mkColor(self.cursorColors["vertical"]).darker()}
        #### END generic plot options
        
        if self.y is not None:
            if self.x is None:
                self._set_data_(y, frameIndex=frameIndex, 
                                frameAxis=frameAxis,
                                signalIndex=signalIndex,
                                signalChannelAxis=signalChannelAxis,
                                signalChannelIndex=signalChannelIndex,
                                separateSignalChannels=separateSignalChannels,
                                irregularSignalIndex=irregularSignalIndex,
                                irregularSignalChannelAxis=irregularSignalChannelAxis,
                                irregularSignalChannelIndex=irregularSignalChannelIndex,
                                interval=interval, 
                                channelIndex = channelIndex,
                                plotStyle = plotStyle, 
                                doc_title = doc_title,
                                *args, **kwargs)
                
            else:
                self._set_data_(x, y, frameIndex=frameIndex, 
                                frameAxis=frameAxis,
                                signalIndex=signalIndex,
                                signalChannelAxis=signalChannelAxis,
                                signalChannelIndex=signalChannelIndex,
                                separateSignalChannels=separateSignalChannels,
                                irregularSignalIndex=irregularSignalIndex,
                                irregularSignalChannelAxis=irregularSignalChannelAxis,
                                irregularSignalChannelIndex=irregularSignalChannelIndex,
                                interval=interval, 
                                channelIndex = channelIndex,
                                plotStyle = plotStyle, 
                                doc_title = doc_title,
                                *args, **kwargs)
                

    def _save_viewer_settings_(self):
        if type(self._scipyenWindow_).__name__ == "ScipyenWindow":
            for dw in self.dockWidgets:
                self.settings.setValue("/".join([self.__class__.__name__, dw[0]]), dw[1].isVisible())
            
    def _load_viewer_settings_(self):
        if type(self._scipyenWindow_).__name__ == "ScipyenWindow":
            for dw in self.dockWidgets:
                dock_visible=False
                
                dock_visibility = self.settings.value("/".join([self.__class__.__name__, dw[0]]), "false")
                
                if isinstance(dock_visibility, str):
                    dock_visible = dock_visibility.lower().strip() == "true"
                        
                elif(isinstance(dock_visibility, bool)):
                    dock_visible = dock_visibility
                    
                if dock_visible:
                    dw[1].setVisible(True)
                    dw[1].show()
                                
                else:
                    dw[1].hide()
                
    @property
    def dockWidgets(self):
        return [(name, win) for name, win in self.__dict__.items() if isinstance(win, QtWidgets.QDockWidget)]
                
    def __del__(self):
        #super(SignalViewer, self).__del__()
        self.linkedCrosshairCursors.clear()
        self.linkedHorizontalCursors.clear()
        self.linkedVerticalCursors.clear()
        self.crosshairSignalCursors.clear() # a dict of SignalCursors mapping str name to cursor object
        self.verticalSignalCursors.clear()
        self.horizontalSignalCursors.clear()
        self._data_cursors_.clear()
        
        self.y = None
        self.x = None
        self.oy = None
        self.ox = None
        
        self.overlays.clear()
        
        self._current_plot_item_= None
        self._focussed_plot_item_ = None
        
        self.canvas = None
        self.fig = None
        self.framesQSlider = None
        self.framesQSpinBox = None
        self.menuBar = None
        
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
        
    def _setup_signal_choosers_(self, analog:(tuple, list, type(None)) = None, irregular:(tuple, list, type(None)) = None):
        """
        """
        sigBlock = [QtCore.QSignalBlocker(widget) for widget in (self.selectSignalComboBox, self.selectIrregularSignalComboBox)]
        
        if analog is None or (isinstance(analog, (tuple, list)) and len(analog) == 0):
            self.selectSignalComboBox.clear()
            
        elif isinstance(analog, np.ndarray):
            self.selectSignalComboBox.clear()
            self.selectIrregularSignalComboBox.clear()
            # TODO (maybe) manage individual signals from the array
            #if analog.size > 0:
                #if analog.ndim == 1:
                    #sig_names = "Analog signal"
                    
                #elif analog.ndim  == 2:
                    #if self.frameAxis is None:
            
        else:
            #print(type(analog))
            current_ndx = self.selectSignalComboBox.currentIndex()
            current_txt = self.selectSignalComboBox.currentText()
            
            sig_names = ["All"] +  utilities.unique([s.name if isinstance(s.name, str) and len(s.name.strip()) else "Analog signal %d" % k for k, s in enumerate(analog)]) + ["Choose"]
            
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
                
            #print("_setup_signal_choosers_ analog new_ndx", new_ndx)
            
            self.selectSignalComboBox.clear()
            self.selectSignalComboBox.addItems(sig_names)
            self.selectSignalComboBox.setCurrentIndex(new_ndx)
            
        if irregular is None or (isinstance(irregular, (tuple, list)) and len(irregular) == 0):
            self.selectIrregularSignalComboBox.clear()
            
        else:
            current_ndx = self.selectIrregularSignalComboBox.currentIndex()
            current_txt = self.selectIrregularSignalComboBox.currentText()
            
            sig_names = ["All"] +  utilities.unique([s.name if isinstance(s.name, str) and len(s.name.strip()) else "Irregularly sampled signal %d" % k for k, s in enumerate(irregular)]) + ["Choose"]
            
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
            
        if all([seq is None or (isinstance(seq, (tuple, list)) and len(seq)==0) for seq in (analog, irregular)]):
            return

    def _configureGUI_ (self):
        self.setupUi(self)
        
        if self.viewerWidgetContainer.layout() is None:
            self.viewerWidgetContainer.setLayout(QtWidgets.QGridLayout(self.viewerWidgetContainer))
            
        self.viewerWidgetContainer.layout().setSpacing(0)
        self.viewerWidgetContainer.layout().setContentsMargins(0,0,0,0)
        
        self.actionSVG.triggered.connect(self.slot_export_svg)
        self.actionTIFF.triggered.connect(self.slot_export_tiff)
        self.actionPNG.triggered.connect(self.slot_export_png)
        
        self.cursorsMenu = QtWidgets.QMenu("Cursors", self)

        self.menubar.addMenu(self.cursorsMenu)
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
        
        self.editCursorsMenu = QtWidgets.QMenu("Edit SignalCursor", self)
        
        self.editAnyCursorAction = self.editCursorsMenu.addAction("Choose...")
        self.editAnyCursorAction.triggered.connect(self.slot_editCursor)
        
        self.editCursorAction = self.editCursorsMenu.addAction("Selected...")
        self.editCursorAction.triggered.connect(self.slot_editSelectedCursor)
        
        self.cursorsMenu.addMenu(self.editCursorsMenu)
        
        self.removeCursorsMenu = QtWidgets.QMenu("Remove cursors", self)
        
        self.removeCursorAction = self.removeCursorsMenu.addAction("Remove a cursor...")
        self.removeCursorAction.triggered.connect(self.slot_removeCursor)
        
        self.removeSelectedCursorAction = self.removeCursorsMenu.addAction("Remove Selected SignalCursor")
        self.removeSelectedCursorAction.triggered.connect(self.slot_removeSelectedCursor)
        
        self.removeAllCursorsAction = self.removeCursorsMenu.addAction("Remove All Cursors")
        self.removeAllCursorsAction.triggered.connect(self.slot_removeCursors)
        
        self.cursorsMenu.addMenu(self.removeCursorsMenu)
        
        self.epochsMenu = QtWidgets.QMenu("Make Epochs")
        
        self.epochsFromCursorsAction = self.epochsMenu.addAction("Cursors to Epochs")
        self.epochsFromCursorsAction.triggered.connect(self.slot_cursorsToEpoch)
        self.epochsFromCursorsAction.setEnabled(self._scipyenWindow_ is not None)
        
        self.epochFromSelectedCursorAction = self.epochsMenu.addAction("Selected SignalCursor to Epoch")
        self.epochFromSelectedCursorAction.triggered.connect(self.slot_cursorToEpoch)
        self.epochFromSelectedCursorAction.setEnabled(self._scipyenWindow_ is not None)
        
        self.epochBetweenCursorsAction = self.epochsMenu.addAction("Epoch Between Two Cursors")
        self.epochBetweenCursorsAction.triggered.connect(self.slot_epochBetweenCursors)
        self.epochBetweenCursorsAction.setEnabled(self._scipyenWindow_ is not None)
        
        self.epochsInDataMenu = QtWidgets.QMenu("Make Epochs in Data")
        
        self.epochsInDataFromCursorsAction = self.epochsInDataMenu.addAction("From All Cursors")
        self.epochsInDataFromCursorsAction.triggered.connect(self.slot_cursorsToEpochInData)
        
        self.epochInDataFromSelectedCursorAction = self.epochsInDataMenu.addAction("From Selected SignalCursor")
        self.epochInDataFromSelectedCursorAction.triggered.connect(self.slot_cursorToEpochInData)
        
        self.epochInDataBetweenCursors = self.epochsInDataMenu.addAction("Between Two Cursors")
        self.epochInDataBetweenCursors.triggered.connect(self.slot_epochInDataBetweenCursors)
        
        self.cursorsMenu.addMenu(self.epochsMenu)
        self.cursorsMenu.addMenu(self.epochsInDataMenu)
        
        # the actual layout of the plot items (pyqtgraph framework)
        self.signalsLayout = pg.GraphicsLayout()
        self.signalsLayout.layout.setVerticalSpacing(0)

        self.fig = pg.GraphicsLayoutWidget(parent = self.viewerWidgetContainer) 
        
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
        
        self.signalsMenu = QtWidgets.QMenu("Signals", self)
        
        self.selectSignalComboBox.clear()
        self.selectSignalComboBox.setCurrentIndex(0)
        self.selectSignalComboBox.currentIndexChanged[int].connect(self.slot_analogSignalsComboBoxIndexChanged)
        #self.selectSignalComboBox.currentIndexChanged[str].connect(self.slot_displayedSignalNameChoiceChanged)
        
        self.plotAnalogSignalsCheckBox.setCheckState(QtCore.Qt.Checked)
        self.plotAnalogSignalsCheckBox.stateChanged[int].connect(self.slot_plotAnalogSignalsCheckStateChanged)
        
        self.selectIrregularSignalComboBox.clear()
        self.selectIrregularSignalComboBox.setCurrentIndex(0)
        self.selectIrregularSignalComboBox.currentIndexChanged[int].connect(self.slot_irregularSignalsComboBoxIndexChanged)
        #self.selectIrregularSignalComboBox.currentIndexChanged[str].connect(self.slot_displayedIrregularSignalNameChoiceChanged)
        
        self.plotIrregularSignalsCheckBox.setCheckState(QtCore.Qt.Checked)
        self.plotIrregularSignalsCheckBox.stateChanged[int].connect(self.slot_plotIrregularSignalsCheckStateChanged)
        
        #### BEGIN set up annotations dock widget
        #print("_configureGUI_ sets up annotations dock widget")
        self.annotationsDockWidget = QtWidgets.QDockWidget("Annotations", self, objectName="annotationsDockWidget")
        self.annotationsDockWidget.setWindowTitle("Annotations")
        self.annotationsDockWidget.setFeatures(QtWidgets.QDockWidget.DockWidgetClosable | QtWidgets.QDockWidget.DockWidgetMovable | QtWidgets.QDockWidget.DockWidgetFloatable)
        
        self.annotationsViewer = InteractiveTreeWidget(self.annotationsDockWidget)
        self.annotationsViewer.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.annotationsViewer.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        self.annotationsViewer.setDragEnabled(True)
        self.annotationsViewer.customContextMenuRequested[QtCore.QPoint].connect(self.slot_annotationsContextMenuRequested)
        
        self.annotationsDockWidget.setWidget(self.annotationsViewer)
        
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.annotationsDockWidget)
        
        #print("_configureGUI_ sets up annotations dock widget action")
        #### END set up annotations dock widget
        
        #### BEGIN set up coordinates dock widget
        #print("_configureGUI_ sets up coordinates dock widget")
        self.coordinatesDockWidget.setWindowTitle("Cursors")
        
        #print("_configureGUI_ sets up coordinates dock widget action")
        
        #self.coordinatesDockWidget.visibilityChanged[bool].connect(self._slot_dock_visibility_changed_)
        #### END set up coordinates dock widget
        
        #print("_configureGUI_ sets up dock widget actions menu")
        self.docksMenu = QtWidgets.QMenu("Panels", self)
        
        #self.showAnnotationsDockWidgetAction = self.annotationsDockWidget.toggleViewAction()
        self.showAnnotationsDockWidgetAction = self.docksMenu.addAction("Annotations")
        self.showAnnotationsDockWidgetAction.setObjectName("action_%s" % self.annotationsDockWidget.objectName())
        #self.showAnnotationsDockWidgetAction.setCheckable(True)
        #self.showAnnotationsDockWidgetAction.setChecked(True)
        
        #self.showAnnotationsDockWidgetAction.toggled[bool].connect(self.slot_displayDockWidget)
        #self.showAnnotationsDockWidgetAction.triggered.connect(self.slot_displayDockWidget)
        #self.showAnnotationsDockWidgetAction = self.docksMenu.addAction("Annotations")
        #self.showAnnotationsDockWidgetAction.triggered.connect(self.slot_dockWidgetRequest)
        self.showAnnotationsDockWidgetAction.triggered.connect(self.slot_showAnnotationsDock)
        
        #self._show_dock_actions_[self.annotationsDockWidget.objectName()] = self.showAnnotationsDockWidgetAction

        #self.showCoordinatesDockWidgetAction = self.coordinatesDockWidget.toggleViewAction()
        self.showCoordinatesDockWidgetAction = self.docksMenu.addAction("Cursors")
        self.showCoordinatesDockWidgetAction.setObjectName("action_%s" % self.coordinatesDockWidget.objectName())
        #self.showCoordinatesDockWidgetAction.setCheckable(True)
        #self.showCoordinatesDockWidgetAction.setChecked(True)
        
        #self.showCoordinatesDockWidgetAction.toggled[bool].connect(self.slot_displayDockWidget)
        #self.showCoordinatesDockWidgetAction.changed.connect(self.slot_dockWidgetRequest)
        #self.showCoordinatesDockWidgetAction.triggered[bool].connect(self.slot_displayDockWidget)
        self.showCoordinatesDockWidgetAction.triggered.connect(self.slot_showCoordinatesDock)
        
        #self._show_dock_actions_[self.coordinatesDockWidget.objectName()] = self.showCoordinatesDockWidgetAction
        #for action in self._show_dock_actions_.values():
            #self.docksMenu.addAction(action)
            ##action.toggled[bool].connect(self.slot_displayDockWidget)
        
        ##print("_configureGUI_ adds dock widget actions menu to the menu bar")
        self.menubar.addMenu(self.docksMenu)
        ##print("_configureGUI_ widget actions menu added to the menu bar")
        
    def addCursor(self, cursorType: typing.Union[str, SignalCursor.SignalCursorTypes] = "c", 
                  x: typing.Optional[numbers.Number] = None,
                  y: typing.Optional[numbers.Number] = None,
                  xwindow: typing.Optional[numbers.Number] = None,
                  ywindow: typing.Optional[numbers.Number] = None, 
                  xBounds: typing.Optional[numbers.Number] = None,
                  yBounds: typing.Optional[numbers.Number] = None, 
                  label: typing.Optional[typing.Union[int, str, pg.PlotItem]] = None,
                  follows_mouse: bool = False, 
                  axis: typing.Optional[int] = None, 
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
        
        #print("SignalViewer.addCursor cursorType %s" % cursorType)
        
        crsID = self._addCursor_(cursor_type = cursorType,
                                x = x, y = y, xwindow = xwindow, ywindow = ywindow,
                                xBounds = xBounds, yBounds = yBounds,
                                axis = axis, label=label,
                                follows_mouse=follows_mouse,
                                **kwargs)
        
        self.slot_selectCursor(crsID)
        
        #return crsID
        
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
            
    def addCursors(self, cursorType="c", *where, **kwargs):
        """Add a set of cursors to the selected axes in the SignalViewer window.
        
        Requires at least one Axis object, therefore some data must be plotted first.
        
        Arguments:
        cursorType : string, one of "c" for crosshair, "v" for vertical, "h" for horizontal cursors
                    -- optional (default is "c")
                    
        where      : comma-separated list or a single sequence of cursor coordinates:
                    for crosshair cursors, the coordinates are given as a two-element tuple
                    for vertical and horizontal cursors, the coordinates are floats
                    
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
            
        if isinstance(where, (tuple, list, np.ndarray)):
            for (k, x) in enumerate(where):
                wx = xwindow
                wy = ywindow
                lbl = labels
                
                if isinstance(xwindow, (tuple, list, np.ndarray)):
                    wx = xwindow[k]
                        
                if isinstance(ywindow, (tuple, list, np.ndarray)):
                    wy = ywindow[k]
                    
                if isinstance(labels,(tuple, list, np.ndarray)):
                    lbl = labels[k]
                    
                self.addCursor(cursorType=cursorType, where=x, xwindow=wx, ywindow=wy, label=lbl)
                
        else:
            self.addCursor(cursorType=cursorType, where=where, xwindow=xwindow, ywindow=ywindow, label=labels)
    
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
                
            dlg = pgui.ItemsListDialog(parent=self,
                                       itemsList = available,
                                       preSelected=preSelected,
                                       title="Select Analog Signals to Plot",
                                       modal = True,
                                       selectmode = QtWidgets.QAbstractItemView.ExtendedSelection)
            
            if dlg.exec() == 1:
                sel_items = dlg.selectedItems
                
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
                    
        if len(text) > 0:
            self._cursor_coordinates_text_ = "\n".join(text)
            
        else:
            self._cursor_coordinates_text_ = ""
    
        self._update_coordinates_viewer_()
        
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
            
            dlg = pgui.ItemsListDialog(parent=self, 
                                       itemsList = available, 
                                       preSelected = preSelected,
                                       title="Select Irregular Signals to Plot", 
                                       modal=True,
                                       selectmode=QtWidgets.QAbstractItemView.ExtendedSelection)
            
            if dlg.exec() == 1:
                sel_items = dlg.selectedItems
                
                if len(sel_items):
                    self.guiSelectedIrregularSignalNames[:] = sel_items[:]
                    
        else:
            self.guiSelectedIrregularSignalNames = [self.selectIrregularSignalComboBox.currentText()]
    
        self.displayFrame()
         
    #@pyqtSlot(str)
    #@safeWrapper
    #def slot_displayedIrregularSignalNameChoiceChanged(self, name):
        #if name.lower() in ("all"):
            #self.guiSelectedIrregularSignals.clear()
            
        #elif name.lower() == "choose":
            #self.guiSelectedIrregularSignalNames.clear()
        ## TODO call GUI chooser dialog
            #self.guiSelectedIrregularSignalNames.clear()
            
            #current_txt = self.selectIrregularSignalComboBox.currentText()
        
            #available = [self.selectIrregularSignalComboBox.itemText(k) for k in range(1, self.selectIrregularSignalComboBox.count()-1)]
            
            #if current_txt in available:
                #preSelected = current_txt
                
            #else:
                #preSelected=None
            
            #dlg = pgui.ItemsListDialog(parent=self, 
                                       #itemsList = available, 
                                       #preSelected = preSelected,
                                       #title="Select Irregular Signals", 
                                       #modal=True,
                                       #selectmode=QtWidgets.QAbstractItemView.ExtendedSelection)
            
            #if dlg.exec() == 1:
                #sel_items = dlg.selectedItems()
                
                #if len(sel_items):
                    #self.guiSelectedIrregularSignalNames[:] = sel_items[:]
                    
        
        #else:
            #self.guiSelectedIrregularSignals = [name]
            
        #self.displayFrame()

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
        
    @pyqtSlot()
    @safeWrapper
    def slot_refreshDataDisplay(self):
        if self._scipyenWindow_ is None:
            return
        
        if self._data_var_name_ is not None and self._data_var_name_ in self._scipyenWindow_.workspace.keys():
            self.setData(self._scipyenWindow_.workspace[self._data_var_name_], self._data_var_name_)

    def _hasCursor_(self, crsID): #  syntactic sugar
        if len(self._data_cursors_) == 0:
            return False
        
        return crsID in self._data_cursors_
    
    
    def _addCursor_(self, cursor_type: typing.Union[str, SignalCursor.SignalCursorTypes], 
                    x: typing.Union[numbers.Number, pq.Quantity, type(None)] = None,
                    y: typing.Union[numbers.Number, pq.Quantity, type(None)] = None,
                    xwindow: typing.Union[numbers.Number, pq.Quantity, type(None)] = None,
                    ywindow: typing.Union[numbers.Number, pq.Quantity, type(None)] = None,
                    xBounds: typing.Union[tuple, type(None)] = None,
                    yBounds: typing.Union[tuple, type(None)] = None,
                    axis: typing.Optional[typing.Union[int, str, pg.PlotItem, pg.GraphicsScene]] = None,
                    label:typing.Optional[str] = None, 
                    follows_mouse: bool = False, **kwargs) -> str:
        """Creates a cursor.
        kwargs: var-keyword parameters for SignalCursor constructor (pen, etc)
        """
        
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
            
        #x = None
        #y = None

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
            
        if isinstance(axis, pg.PlotItem):
            if axis not in self.signalsLayout.items:
                return
            
            view_range = axis.viewRange() #  [[xmin, xmax], [ymin, ymax]]
            
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
                min_x_axis = np.min([p.viewRange()[0][0] for p in self.signalsLayout.items])
                max_x_axis = np.max([p.viewRange()[0][0] for p in self.signalsLayout.items])
                
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
                
        if not isinstance(cursor_type, str):
            raise TypeError("cursor_type expected to be a str; got %s instead" % type(cursor_type).__name__)
        
        if isinstance(cursor_type, SignalCursor.SignalCursorTypes):
            cursor_type = cursor_type.name
        
        #print("SignalViewer._addCursor_ cursor_type %s" % cursor_type)
        
        if cursor_type in ("vertical", "v", SignalCursor.SignalCursorTypes.vertical):
            cursorDict = self.verticalSignalCursors
            crsPrefix = "v"
            
            #xwindow = self.defaultCursorWindowSizeX
            ywindow = 0.0
            pen = pg.mkPen(pg.mkColor(self.cursorColors["vertical"]), style=QtCore.Qt.SolidLine)
            linkedPen = pg.mkPen(pg.mkColor(self.linkedCursorColors["vertical"]), style=QtCore.Qt.SolidLine)
            
        elif cursor_type in ("horizontal", "h", SignalCursor.SignalCursorTypes.horizontal):
            cursorDict = self.horizontalSignalCursors
            crsPrefix = "h"
            xwindow = 0.0
            #ywindow = self.defaultCursorWindowSizeY
            pen = pg.mkPen(pg.mkColor(self.cursorColors["horizontal"]), style=QtCore.Qt.SolidLine)
            linkedPen = pg.mkPen(pg.mkColor(self.linkedCursorColors["horizontal"]), style=QtCore.Qt.SolidLine)
            
        elif cursor_type in ("crosshair", "c", SignalCursor.SignalCursorTypes.crosshair):
            cursorDict = self.crosshairSignalCursors
            crsPrefix = "c"
            xwindow = self.defaultCursorWindowSizeX
            ywindow = self.defaultCursorWindowSizeY
            pen = pg.mkPen(pg.mkColor(self.cursorColors["crosshair"]), style=QtCore.Qt.SolidLine)
            linkedPen = pg.mkPen(pg.mkColor(self.linkedCursorColors["crosshair"]), style=QtCore.Qt.SolidLine)
            
        else:
            raise ValueError("unsupported cursor type %s" % cursor_type)
        
        nCursors = len(cursorDict)
        
        if label is None:
            crsId = "%s%s" % (crsPrefix, str(nCursors))
            
        else:
            crsId = label
            
        cursorDict[crsId] = SignalCursor(axis, 
                                   x = x, y = y, xwindow=xwindow, ywindow=ywindow,
                                   cursor_type = cursor_type,
                                   cursorID = crsId,
                                   linkedPen = linkedPen,
                                   pen = pen, 
                                   parent = self, 
                                   follower = follows_mouse, 
                                   xBounds = xBounds,
                                   yBounds = yBounds,
                                   **kwargs)
        
        cursorDict[crsId].sig_cursorSelected[str].connect(self.slot_selectCursor)
        cursorDict[crsId].sig_reportPosition[str].connect(self.slot_reportCursorPosition)
        cursorDict[crsId].sig_doubleClicked[str].connect(self.slot_editCursor)
        cursorDict[crsId].sig_editMe[str].connect(self.slot_editCursor)
        
        return crsId

    @pyqtSlot((QtCore.QPoint))
    @safeWrapper
    def slot_annotationsContextMenuRequested(self, point):
        if self._scipyenWindow_ is None: 
            return
        
        indexList = self.annotationsViewer.selectedIndexes()
        
        if len(indexList) == 0:
            return
        
        cm = QtWidgets.QMenu("Data operations", self)
        
        copyItemData = cm.addAction("Copy to workspace")
        copyItemData.triggered.connect(self.slot_exportItemDataToWorkspace)
        
        cm.popup(self.annotationsViewer.mapToGlobal(point), copyItemData)
        
    @pyqtSlot()
    @safeWrapper
    def slot_exportItemDataToWorkspace(self):
        if self._scipyenWindow_ is None:
            return
        
        items = self.annotationsViewer.selectedItems()
        
        if len(items) == 0:
            return
        
        self._export_data_items_(items)
        
    @safeWrapper
    def _export_data_items_(self, items):
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
                
                value = utilities.get_nested_value(self.dataAnnotations, item_path[1:]) # because 1st item is the insivible root name
                
                values.append(value)
                
                item_paths.append(item_path[-1])
                
            if len(values):
                if len(values) == 1:
                    dlg = quickdialog.QuickDialog(self, "Copy to workspace")
                    namePrompt = quickdialog.StringInput(dlg, "Data name:")
                    
                    newVarName = strutils.string_to_valid_identifier(item_paths[-1])
                    
                    namePrompt.variable.setClearButtonEnabled(True)
                    namePrompt.variable.redoAvailable=True
                    namePrompt.variable.undoAvailable=True
                    
                    namePrompt.setText(newVarName)
                    
                    if dlg.exec() == QtWidgets.QDialog.Accepted:
                        newVarName = validateVarName(namePrompt.text(), self._scipyenWindow_.workspace)
                        
                        self._scipyenWindow_._assignToWorkspace_(newVarName, values[0])
                        
                        
                else:
                    for name, value in zip(item_paths, values):
                        newVarName = validateVarName(name, self._scipyenWindow_.workspace)
                        self._scipyenWindow_._assignToWorkspace_(newVarName, value)
        
        
    @pyqtSlot()
    @safeWrapper
    def slot_addVerticalCursor(self, label = None, follows_mouse=False):
        return self._addCursor_("vertical", axis=self._current_plot_item_, 
                                  label=label, follows_mouse=follows_mouse)
    
    @pyqtSlot()
    @safeWrapper
    def slot_addHorizontalCursor(self, label=None, follows_mouse=False):
        return self._addCursor_("horizontal", axis=self._current_plot_item_, 
                                  label=label, follows_mouse=follows_mouse)
        
    @pyqtSlot()
    @safeWrapper
    def slot_addCrosshairCursor(self, label=None, follows_mouse=False):
        return self._addCursor_("crosshair", axis=self._current_plot_item_, 
                                  label=label, follows_mouse=follows_mouse)
    
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
            
            out.fill(pg.mkColor(pg.getConfigOption("background")))
            
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
            d = quickdialog.QuickDialog(self, "Choose cursor to remove")
            #d = vigra.pyqt.quickdialog.QuickDialog(self, "Choose cursor to remove")
        
            cursorComboBox = pgui.QuickDialogComboBox(d, "Select cursor:")
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
        from functools import partial
        #print("SignalViewer.slot_editCursor", crsId)
        
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
            d = quickdialog.QuickDialog(self, "Edit cursor")
            #d = vigra.pyqt.quickdialog.QuickDialog(self, "Edit cursor")
            cursorComboBox = pgui.QuickDialogComboBox(d, "Select cursor:")
            cursorComboBox.setItems([c for c in self._data_cursors_])
            
            d.cursorComboBox = cursorComboBox
            
            d.cursorComboBox.connectIndexChanged(partial(self._slot_update_cursor_editor_dlg_, d=d))
        
        else:
            d = quickdialog.QuickDialog(self, "Edit cursor %s" % crsId)
            #d = vigra.pyqt.quickdialog.QuickDialog(self, "Edit cursor %s" % crsId)
        
        namePrompt = quickdialog.StringInput(d, "Name:")
        #namePrompt = vigra.pyqt.quickdialog.StringInput(d, "Name:")
        namePrompt.variable.setClearButtonEnabled(True)
        namePrompt.variable.redoAvailable=True
        namePrompt.variable.undoAvailable=True
        
        d.namePrompt = namePrompt
        
        if cursor is not None:
            if cursor.cursorType in ("vertical", "crosshair"):
                promptX = quickdialog.FloatInput(d, "X coordinate:")
                #promptX = vigra.pyqt.quickdialog.FloatInput(d, "X coordinate:")
                promptX.variable.setClearButtonEnabled(True)
                promptX.variable.redoAvailable=True
                promptX.variable.undoAvailable=True

                d.promptX = promptX
            
                promptXWindow = quickdialog.FloatInput(d, "Horizontal window size:")
                #promptXWindow = vigra.pyqt.quickdialog.FloatInput(d, "Horizontal window size:")
                promptXWindow.variable.setClearButtonEnabled(True)
                promptXWindow.variable.redoAvailable=True
                promptXWindow.variable.undoAvailable=True

                d.promptXWindow = promptXWindow
            
            if cursor.cursorType in ("horizontal", "crosshair"):
                promptY = quickdialog.FloatInput(d, "Y coordinate:")
                #promptY = vigra.pyqt.quickdialog.FloatInput(d, "Y coordinate:")
                promptY.variable.setClearButtonEnabled(True)
                promptY.variable.redoAvailable=True
                promptY.variable.undoAvailable=True

                d.promptY = promptY
            
                promptYWindow = quickdialog.FloatInput(d, "Vertical window size:")
                #promptYWindow = vigra.pyqt.quickdialog.FloatInput(d, "Vertical window size:")
                promptYWindow.variable.setClearButtonEnabled(True)
                promptYWindow.variable.redoAvailable=True
                promptYWindow.variable.undoAvailable=True

                d.promptYWindow = promptYWindow
                
        else:
            promptX = quickdialog.FloatInput(d, "X coordinate:")
            #promptX = vigra.pyqt.quickdialog.FloatInput(d, "X coordinate:")
            promptX.variable.setClearButtonEnabled(True)
            promptX.variable.redoAvailable=True
            promptX.variable.undoAvailable=True

            d.promptX = promptX
        
            promptXWindow = quickdialog.FloatInput(d, "Horizontal window size:")
            #promptXWindow = vigra.pyqt.quickdialog.FloatInput(d, "Horizontal window size:")
            promptXWindow.variable.setClearButtonEnabled(True)
            promptXWindow.variable.redoAvailable=True
            promptXWindow.variable.undoAvailable=True

            d.promptXWindow = promptXWindow
            
            promptY = quickdialog.FloatInput(d, "Y coordinate:")
            #promptY = vigra.pyqt.quickdialog.FloatInput(d, "Y coordinate:")
            promptY.variable.setClearButtonEnabled(True)
            promptY.variable.redoAvailable=True
            promptY.variable.undoAvailable=True

            d.promptY = promptY
        
            promptYWindow = quickdialog.FloatInput(d, "Vertical window size:")
            #promptYWindow = vigra.pyqt.quickdialog.FloatInput(d, "Vertical window size:")
            promptYWindow.variable.setClearButtonEnabled(True)
            promptYWindow.variable.redoAvailable=True
            promptYWindow.variable.undoAvailable=True

            d.promptYWindow = promptYWindow
                
            
        if not isinstance(crsId, str): # populate dialog fields w/ data
            crsId = [c for c in self._data_cursors_.keys()][0]
            
        self._slot_update_cursor_editor_dlg_(crsId, d)
            
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
                #print(d.promptX.value(), d.promptXWindow.value())
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
                
        if hasattr(d, "cursorComboBox"):
            d.cursorComboBox.disconnect()
                
        del d
    
    @pyqtSlot(str)
    @safeWrapper
    def _slot_update_cursor_editor_dlg_(self, cid, d):
        #print("_slot_update_cursor_editor_dlg_ cid", cid)
        #print("_slot_update_cursor_editor_dlg_ dialog", d)
        
        if not isinstance(cid, str) or len(cid.strip()) == 0:
            if hasattr(d, "cursorComboBox"):
                if d.cursorComboBox.variable.count() == 0:
                    return
                
                else:
                    cid = d.cursorComboBox.variable.currentText()
                    
                    if len(cid) == 0:
                        cid = d.cursorComboBox.variable.itemText(0)
            
        c = self.dataCursor(cid)
            
        #print("_slot_update_cursor_editor_dlg_ cursor", c)
        
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
    def selectSignals(self, index=None):
        """
        TODO
        """
        if index is None:
            pass
        
        pass
        
    
    @pyqtSlot()
    @safeWrapper
    def slot_cursorsToEpoch(self):
        if self._scipyenWindow_ is not None:
            epoch = self.cursorsToEpoch()
            if epoch is not None:
                name = epoch.name
                if name is None:
                    name="epoch"
                    
                self._scipyenWindow_._assignToWorkspace_(name, epoch)
                
    @pyqtSlot()
    @safeWrapper
    def slot_cursorsToEpochInData(self):
        vertAndCrossCursors = collections.ChainMap(self.crosshairSignalCursors, self.verticalSignalCursors)
        
        if len(vertAndCrossCursors) == 0:
            return
        
        if isinstance(self.y, (neo.Block, neo.Segment)):
            d = quickdialog.QuickDialog(self, "Attach epoch to data")
            #d = vigra.pyqt.quickdialog.QuickDialog(self, "Attach epoch to data")
            d.promptWidgets = list()
            epochNamePrompt = quickdialog.StringInput(d, "Epoch Name:")
            #epochNamePrompt = vigra.pyqt.quickdialog.StringInput(d, "Epoch Name:")
            epochNamePrompt.variable.setClearButtonEnabled(True)
            epochNamePrompt.variable.redoAvailable = True
            epochNamePrompt.variable.undoAvailable = True
            
            if self.y.name is not None:
                epochNamePrompt.setText("%s_Epoch" % self.y.name)
            else:
                epochNamePrompt.setText("Epoch")
                
            d.promptWidgets.append(epochNamePrompt)
                
            toCurrentSegmentCheckBox = quickdialog.CheckBox(d, "Current segment only")
            #toCurrentSegmentCheckBox = vigra.pyqt.quickdialog.CheckBox(d, "Current segment only")
            toCurrentSegmentCheckBox.setChecked(False)
            
            d.promptWidgets.append(toCurrentSegmentCheckBox)
            
            overwriteEpochCheckBox = quickdialog.CheckBox(d, "Overwrite existing epochs")
            #overwriteEpochCheckBox = vigra.pyqt.quickdialog.CheckBox(d, "Overwrite existing epochs")
            overwriteEpochCheckBox.setChecked(True);
            
            d.promptWidgets.append(overwriteEpochCheckBox)
            
            if d.exec() == QtWidgets.QDialog.Accepted:
                epochName = epochNamePrompt.text()
                if epochName is None or len(epochName) == 0:
                    return
                
                toCurrentSegment = toCurrentSegmentCheckBox.isChecked()
                overwriteEpoch   = overwriteEpochCheckBox.isChecked()
                
            cursors = [c for c in vertAndCrossCursors.values()]
            
            cursors.sort(key=attrgetter('x'))
            
            x = np.array([c.x for c in cursors]) * pq.s
            d = np.array([c.xwindow for c in cursors]) * pq.s
            labels = np.array([c.ID for c in cursors], dtype="S")
            
            t = x - d/2
            
            epoch = neo.Epoch(times=t, durations=d, labels=labels, units=pq.s, name=epochName)
            
            if isinstance(self.y,neo.Block):
                if toCurrentSegment:
                    if overwriteEpoch:
                        self.y.segments[self.frameIndex[self._current_frame_index_]].epochs = [epoch]
                    else:
                        self.y.segments[self.frameIndex[self._current_frame_index_]].epochs.append(epoch)
                else:
                    if overwriteEpoch:
                        for ndx in self.frameIndex:
                            self.y.segments[ndx].epochs = [epoch]
                    else:
                        for ndx in self.frameIndex:
                            self.y.segments[ndx].epochs.append(epoch)
            else:
                if overwriteEpoch:
                    self.y.epochs = [epoch]
                else:
                    self.y.epochs.append(epoch)
                
            self.displayFrame()

        else:
            QtWidgets.QMessageBox.warning(self,"Attach epoch to data", "Epochs can only be embedded in neo.Block and neo.Segment data.\n\nPlease use actions in 'Make epochs' sub-menu")
            
    @pyqtSlot()
    @safeWrapper
    def slot_cursorToEpochInData(self):
        vertAndCrossCursors = collections.ChainMap(self.crosshairSignalCursors, self.verticalSignalCursors)
        
        if len(vertAndCrossCursors) == 0:
            return
        
        epoch = self.cursorToEpoch(self.selectedDataCursor)
        if epoch is not None:
            name = epoch.name
            if name is not None:
                name = "epoch"
                
        #pass
    
    @pyqtSlot()
    @safeWrapper
    def slot_epochInDataBetweenCursors(self):
        vertAndCrossCursors = collections.ChainMap(self.crosshairSignalCursors, self.verticalSignalCursors)
        
        if len(vertAndCrossCursors) == 0:
            return
        
        if isinstance(self.y, (neo.Block, neo.Segment)):
            d = quickdialog.QuickDialog(self, "Make Epoch From Interval Between Cursors:")
            #d = vigra.pyqt.quickdialog.QuickDialog(self, "Make Epoch From Interval Between Cursors:")
            d.promptWidgets = list()
            
            namePrompt=quickdialog.StringInput(d, "Name:")
            #namePrompt=vigra.pyqt.quickdialog.StringInput(d, "Name:")
            namePrompt.setText("Epoch")
            
            c1Prompt = quickdialog.StringInput(d, "SignalCursor 1:")
            c2Prompt = quickdialog.StringInput(d, "SignalCursor 2:")
            
            #c1Prompt = vigra.pyqt.quickdialog.StringInput(d, "SignalCursor 1:")
            #c2Prompt = vigra.pyqt.quickdialog.StringInput(d, "SignalCursor 2:")
            
            d.promptWidgets.append(namePrompt)
            d.promptWidgets.append(c1Prompt)
            d.promptWidgets.append(c2Prompt)
            
            toCurrentSegmentCheckBox = quickdialog.CheckBox(d, "Current segment only")
            #toCurrentSegmentCheckBox = vigra.pyqt.quickdialog.CheckBox(d, "Current segment only")
            toCurrentSegmentCheckBox.setChecked(False)
            
            d.promptWidgets.append(toCurrentSegmentCheckBox)
            
            overwriteEpochCheckBox = quickdialog.CheckBox(d, "Overwrite existing epochs")
            #overwriteEpochCheckBox = vigra.pyqt.quickdialog.CheckBox(d, "Overwrite existing epochs")
            overwriteEpochCheckBox.setChecked(True);
            
            d.promptWidgets.append(overwriteEpochCheckBox)
            
            if d.exec() == QtWidgets.QDialog.Accepted:
                name = namePrompt.text()
                
                if name is None or len(name) == 0:
                    return
                
                c1ID = c1Prompt.text()
                
                if c1ID is None or len(c1ID) == 0:
                    return
                
                c2ID = c2Prompt.text()
                
                if c2ID is None or len(c2ID) == 0:
                    return
                
                c1 = self.dataCursor(c1ID)
                c2 = self.dataCursor(c2ID)
                
                if c1 is None or c2 is None:
                    return
                
                toCurrentSegment = toCurrentSegmentCheckBox.isChecked()
                overwriteEpoch   = overwriteEpochCheckBox.isChecked()
                
                epoch = self.epochBetweenCursors(c1, c2, name)
                
                if epoch is not None:
                    name=epoch.name
                    if name is None:
                        name = "epoch"
                
                if isinstance(self.y, neo.Block):
                    if toCurrentSegment:
                        if overwriteEpoch:
                            self.y.segments[self.frameIndex[self._current_frame_index_]].epochs = [epoch]
                            
                        else:
                            self.y.segments[self.frameIndex[self._current_frame_index_]].epochs.append(epoch)
                    else:
                        if overwriteEpoch:
                            for ndx in self.frameIndex:
                                self.y.segments[ndx].epochs = [epoch]
                        else:
                            for ndx in self.frameIndex:
                                self.y.segments[ndx].epochs.append(epoch)
                else:
                    if overwriteEpoch:
                        self.y.epochs = [epoch]
                    else:
                        self.y.epochs.append(epoch)
                    
                self.displayFrame()
            #self._plotOverlayFrame_()
                
    
    @pyqtSlot()
    @safeWrapper
    def slot_cursorToEpoch(self):
        vertAndCrossCursors = collections.ChainMap(self.crosshairSignalCursors, self.verticalSignalCursors)
        
        if len(vertAndCrossCursors) == 0:
            return
        
        if self._scipyenWindow_ is not None:
            epoch = self.cursorToEpoch(self.selectedDataCursor)
            if epoch is not None:
                name = epoch.name
                if name is not None:
                    name = "epoch"
                
                self._scipyenWindow_._assignToWorkspace_(name, epoch)
    
    @pyqtSlot()
    @safeWrapper
    def slot_epochBetweenCursors(self):
        if self._scipyenWindow_ is None:
            return
        
        vertAndCrossCursors = collections.ChainMap(self.crosshairSignalCursors, self.verticalSignalCursors)
        
        if len(vertAndCrossCursors) == 0:
            return
        
        d = quickdialog.QuickDialog(self, "Make Epoch From Interval Between Cursors:")
        #d = vigra.pyqt.quickdialog.QuickDialog(self, "Make Epoch From Interval Between Cursors:")
        d.promptWidgets = list()
        namePrompt=quickdialog.StringInput(d, "Name:")
        #namePrompt=vigra.pyqt.quickdialog.StringInput(d, "Name:")
        namePrompt.setText("Epoch")
        c1Prompt = quickdialog.StringInput(d, "SignalCursor 1 ID:")
        c2Prompt = quickdialog.StringInput(d, "SignalCursor 2 ID:")
        #c1Prompt = vigra.pyqt.quickdialog.StringInput(d, "SignalCursor 1 ID:")
        #c2Prompt = vigra.pyqt.quickdialog.StringInput(d, "SignalCursor 2 ID:")
        d.promptWidgets.append(namePrompt)
        d.promptWidgets.append(c1Prompt)
        d.promptWidgets.append(c2Prompt)
        
        if d.exec() == QtWidgets.QDialog.Accepted:
            name = namePrompt.text()
            if name is None or len(name) == 0:
                return
            
            c1ID = c1Prompt.text()
            
            if c1ID is None or len(c1ID) == 0:
                return
            
            c2ID = c2Prompt.text()
            
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
                    
                self._scipyenWindow_._assignToWorkspace_(name, epoch)
        
    def cursorsToEpoch(self, name=None):
        """Creates a neo.Epoch from a list of cursors
        TODO: give the possibilty to select which cursors to use, via GUI
        """
        vertAndCrossCursors = collections.ChainMap(self.crosshairSignalCursors, self.verticalSignalCursors)
        
        if len(vertAndCrossCursors) == 0:
            return None
        
        if name is None:
            d = quickdialog.QuickDialog(self, "Make Epoch From Cursors:")
            #d = vigra.pyqt.quickdialog.QuickDialog(self, "Make Epoch From Cursors:")
            d.promptWidgets = list()
            d.promptWidgets.append(quickdialog.StringInput(d, "Name:"))
            #d.promptWidgets.append(vigra.pyqt.quickdialog.StringInput(d, "Name:"))
            d.promptWidgets[0].setText("Epoch")
            d.promptWidgets[0].variable.setClearButtonEnabled(True)
            d.promptWidgets[0].variable.redoAvailable = True
            d.promptWidgets[0].variable.undoAvailable = True
            
            if d.exec() == QtWidgets.QDialog.Accepted:
                txt = d.promptWidgets[0].text()
                if txt is not None and len(txt)>0:
                    name=txt
        
        cursors = [c for c in vertAndCrossCursors.values()]
        
        cursors.sort(key=attrgetter('x')) # or key = lambda x: x.x
        
        ret = neoutils.cursors2epoch(*cursors, name=name, sort=True)
        
        return ret
        
    def cursorToEpoch(self, crs=None, name=None):
        """Creates a neo.Epoch from a single cursor
        TODO: give the possibilty to choose the cursor via GUI
        """
        if crs is None:
            return
        
        if crs.isHorizontal:
            return
        
        if name is None:
            d = quickdialog.QuickDialog(self, "Make Epoch From SignalCursor:")
            #d = vigra.pyqt.quickdialog.QuickDialog(self, "Make Epoch From SignalCursor:")
            d.promptWidgets = list()
            d.promptWidgets.append(quickdialog.StringInput(d, "Name:"))
            #d.promptWidgets.append(vigra.pyqt.quickdialog.StringInput(d, "Name:"))
            d.promptWidgets[0].setText("Epoch from "+crs.ID)
            
            if d.exec() == QtWidgets.QDialog.Accepted:
                txt = d.promptWidgets[0].text()
                if txt is not None and len(txt)>0:
                    name=txt
                    
            else:
                return
            
        return neoutils.cursors2epoch(crs, name=name)
        
        #return neo.Epoch(times = np.array([crs.x-crs.xwindow/2]) * pq.s, \
                         #durations = np.array([crs.xwindow]) * pq.s, \
                         #units = pq.s, label = np.ndarray([crs.ID], dtype="S"), name=name)
    
    
    def epochBetweenCursors(self, c0, c1, name=None):
        if c0.isHorizontal or c1.isHorizontal:
            return
        
        clist = sorted([c0, c1], key=attrgetter('x'))
        
        if name is None:
            d = quickdialog.QuickDialog(self, "Make Epoch From Interval Between Two Cursors:")
            #d = vigra.pyqt.quickdialog.QuickDialog(self, "Make Epoch From Interval Between Two Cursors:")
            d.promptWidgets = list()
            d.promptWidgets.append(quickdialog.StringInput(d, "Name:"))
            #d.promptWidgets.append(vigra.pyqt.quickdialog.StringInput(d, "Name:"))
            d.promptWidgets[0].setText("Epoch")
            
            if d.exec() == QtWidgets.QDialog.Accepted:
                txt = d.promptWidgets[0].text()
                if txt is not None and len(txt)>0:
                    name=txt
                    
            else:
                return
        
        return neo.Epoch(times = np.array([clist[0].x])*pq.s,
                         durations = np.array([clist[1].x - clist[0].x]) * pq.s,
                         units = pq.s, labels=np.array(["From %s to %s" % (clist[0].ID, clist[1].ID)], dtype="S"), \
                         name=name)
    
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
    def setData(self,  
                x:(neo.core.baseneo.BaseNeo, dt.DataSignal, dt.IrregularlySampledDataSignal, dt.TriggerEvent,dt.TriggerProtocol, vigra.filters.Kernel1D, np.ndarray, tuple, list, type(None)), 
                y:(neo.core.baseneo.BaseNeo, dt.DataSignal, dt.IrregularlySampledDataSignal, dt.TriggerEvent,dt.TriggerProtocol, vigra.filters.Kernel1D, np.ndarray, tuple, list, type(None)) = None,
                doc_title:(str, type(None)) = None, 
                frameAxis:(int, str, vigra.AxisInfo, type(None)) = None,
                signalChannelAxis:(int, str, vigra.AxisInfo, type(None)) = None,
                frameIndex:(int, tuple, list, range, slice, type(None)) = None, 
                signalIndex:(str, int, tuple, list, range, slice, type(None)) = None,
                signalChannelIndex:(int, tuple, list, range, slice, type(None)) = None,
                irregularSignalIndex:(str, int, tuple, list, range, slice, type(None)) = None, 
                irregularSignalChannelAxis:(int, type(None)) = None,
                irregularSignalChannelIndex:(int, tuple, list, range, slice, type(None)) = None, 
                separateSignalChannels:bool = False, 
                interval:(tuple, list, neo.Epoch, type(None)) = None,
                unitIndex:object = None,
                channelIndex:object = None,
                plotStyle:str = "plot",
                show:bool = True,
                *args, **kwargs):
        """ Sets up the plot data and updates the plot.
        
        Plotting is executed by displayFrame().
        
                
        Positional parameters:
        ----------------------
        x: object = data to be plotted, or the data domain, if data is given 
            separately as "y"
            
        NOTE: 2019-11-24 09:49:59
        When both x and y are supplied, x will be ignored when y is a neo.Block.
        However, a supplied "x" can be used with signals in a collection such as
        neo.Segment an iterable of signals, or a numpy array. In this case x 
        should be conformant with the signal (i.e. have the same length as the
        signal).
        
        When x is not supplied, SignalViewer tries to create a signal domain
        as an undimensioned linear space based on the length of the signal.
        
        Named parameters (see Glossary of terms in SignalViewer doctring):
        ------------------------------------------------------------------
        y: object or None = data to be plotted; when None, then "x" is taken as 
            the plot data, and the data "domain" is calculated or extracted from
            it.
            
        doc_title: str or None = name of the data (will also appear in the window
            title)
            
        frameAxis: int, str, vigra.AxisInfo or None (default)
            When plot data is a numpy array, it indicates the axis along which
            the data "frames" are defined.
            
            For vigra.VigraArrays (which inherit from numpy.ndarray) frameAxis
            may also be specified as a string (axis "key") or AxisInfo object.
            See vigranumpy documentation for details.
                
            When plot data is a structured signal object (e.g. neo.AnalogSignal,
            datatypes.DataSignal) frameAxis may be used to plot the signal's
            channels in separate frames.
            
            The default (None) indicates that plot data should not be considered
            as organized in frames (unless it is a structured signal collection, 
            see below).
                
            frameAxis is disregarded in the case of structured signal collections
            such as neo.Block which already contains several data frames 
            (segments) and neo.Segment which encapsulates one frame.
            
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
        
        channelIndex: neo.ChannelIndex object, or None (default) - used to select
            which data channel to plot (NOT to be confused with signal channels)
        
        plotStyle: str, default is "plot" -- keyword reserved for development
        
        show: bool - Flag to indicate if viewer is to be shown (i.e. made the 
            active window).
            
            Default is True. May be set to False to keep an already visible 
            viewer window in the background (useful if the windowing system of 
            the operating system does not implement a focus stealing mechanism)
        
        *args, **kwargs -- further parameters and keyword parameters passed on 
            to PyQtGraph plot function.
        
        """ 
        self._set_data_(x, y, doc_title=doc_title, 
                        frameIndex=frameIndex,frameAxis=frameAxis,
                        signalIndex=signalIndex,
                        signalChannelAxis=signalChannelAxis,
                        irregularSignalIndex=irregularSignalIndex,
                        irregularSignalChannelAxis=irregularSignalChannelAxis,
                        irregularSignalChannelIndex=irregularSignalChannelIndex,
                        separateSignalChannels=separateSignalChannels,
                        interval=interval,
                        channelIndex=channelIndex,
                        plotStyle=plotStyle,
                        show=show,
                        *args, **kwargs)
    
    @safeWrapper
    def _set_data_(self, 
                   x:(neo.core.baseneo.BaseNeo, dt.DataSignal, dt.IrregularlySampledDataSignal, dt.TriggerEvent,dt.TriggerProtocol, vigra.filters.Kernel1D, np.ndarray, tuple, list, type(None)), 
                   y:(neo.core.baseneo.BaseNeo, dt.DataSignal, dt.IrregularlySampledDataSignal, dt.TriggerEvent,dt.TriggerProtocol, vigra.filters.Kernel1D, np.ndarray, tuple, list, type(None)) = None,
                   doc_title:(str, type(None)) = None, 
                   frameIndex:(int, tuple, list, range, slice, type(None)) = None, 
                   frameAxis:(int, type(None)) = None,
                   signalIndex:(str, int, tuple, list, range, slice, type(None)) = None,
                   signalChannelAxis:(int, type(None)) = None,
                   signalChannelIndex:(int, tuple, list, range, slice, type(None)) = None,
                   irregularSignalIndex:(str, int, tuple, list, range, slice, type(None)) = None, 
                   irregularSignalChannelAxis:(int, type(None)) = None,
                   irregularSignalChannelIndex:(int, tuple, list, range, slice, type(None)) = None, 
                   separateSignalChannels:bool = False, 
                   interval:(tuple, list, neo.Epoch, type(None)) = None,
                   channelIndex:(int, tuple, list, range, slice, type(None)) = None,
                   unitIndex: object = None,
                   plotStyle:str = "plot",
                   show:bool = True,
                   *args, **kwargs):
        """Data management function called by self.setData(...)
        
        Figures out data layout (channel, frames etc) then calls displayframe().
        """
        self.plot_start = None
        self.plot_stop = None
        
        self.epoch_plot_options["epoch_pen"] = kwargs.pop("epoch_pen", None)
        self.epoch_plot_options["epoch_brush"] = kwargs.pop("epoch_brush", None)
        self.epoch_plot_options["epoch_hoverPen"] = kwargs.pop("epoch_hoverPen", None)
        self.epoch_plot_options["epoch_hoverBrush"] = kwargs.pop("epoch_hoverBrush", None)
        
        self.train_plot_options["train_pen"] = kwargs.pop("train_pen", None)
        #self.train_plot_options["train_brush"] = kwargs.pop("train_brush", None)
        #self.train_plot_options["train_hoverPen"] = kwargs.pop("train_hoverPen", None)
        #self.train_plot_options["train_hoverBrush"] = kwargs.pop("train_hoverBrush", None)
        
        if isinstance(interval, neo.Epoch):
            # NOTE: 2019-01-24 21:05:34
            # use only the first epoch in an Epoch array (if there are several elements)
            if len(interval) > 0:
                self.plot_start = interval.times[0]
                self.plot_stop = self.plot_start + interval.durations[0]
                
        elif isinstance(interval, (tuple, list)) and all([isinstance(t, (numbers.Real, pq.Quantity)) for t in interval]):
            self.plot_start = interval[0]
            self.plot_stop = interval[1]
            
            # TODO: 2019-11-21 17:05:27
            # verify/adapt plot_start and plot_end (according) to the domain of the signal
            # we need to do this at plotting time
            
        try:
            # remove gremlins from previous plot
            self._plotEpochs_(clear=True)

            # NOTE: 2019-04-30 09:55:33
            # assign to x and y, BUT:
            # is an Epoch, SpikeTrain or Event array is passed AND there already
            # is an "y", don't assign to it (just overlay stuff)
            if y is None:
                if x is not None:  # only the data variable Y is passed, 
                    y = x
                    x = None  # argument (X) and the expected Y will be None by default
                                # here we swap these two variables and we end up with X as None
                    
                else:
                    warngins.warn("I need something to plot")
                    return
                
            if isinstance(y, neo.basesignal.BaseNeo):
                self.globalAnnotations = {type(y).__name__ : y.annotations}
            
            if isinstance(y, neo.core.Block):
                self.x = None # domain is contained in the signals inside the block
                self.y = y
                self._data_frames_ = len(self.y.segments)
                
                #### BEGIN NOTE 2019-11-24 22:32:46: 
                # no need for these so reset to None
                # but definitely used when self.y is a signal, not a container of signals!
                self.frameAxis = None
                self.signalChannelAxis = None 
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
                
                # NOTE: this is used when self.y is a structured signal object,
                # but not for a block, channel index, or segment

                # NOTE: 2019-11-24 11:57:29
                # ALTERNATIVE means of selecting which segments to plot.
                # If a neo.ChannelIndex index is specified, and its signals 
                # belong to self.y then the viewer should only plot those segments
                # that contain signals linked to the specified channel
                
                # ATTENTION do the same at _plotSegment_() stage
                if isinstance(channelIndex, neo.ChannelIndex) and channelIndex in self.y.channel_indexes:
                    # NOTE: 2019-11-24 21:48:37
                    # select segments & signals by neo channel index, but
                    # reject this channel index if it does not belong to y
                    # which is a neo.Block.
                    
                    # select segments containing signals linked with this channel
                    # index, AND belong to self.y !
                    channel_segments = [s for s in neoutils.get_segments_in_channel_index(channelIndex) if s.block is self.y]
                    
                    if len(channel_segments):
                        self.frameIndex = [self.y.segments.index(s) for s in channel_segments]
                        self._number_of_frames_ = len(self.frameIndex)
                        self.channelIndex = channelIndex
                        
                    else:
                        # no success: this channel index has nothing to do with self.y
                        warnings.warn("Channel index %s has no signals in this %s and will be ignored" % (self.channelIndex, type(self.y).__name__), RuntimeWarning)
                        
                        self.channelIndex = None
                        
                elif channelIndex is not None:
                    raise TypeError("channelIndex expected to be a neo.ChannelIndex or None; got %s instead" % type(channelIndex).__name__)
                        
                if self.channelIndex is None: # the above failed
                    self.frameIndex = utilities.normalized_index(self._data_frames_, frameIndex)
                    self._number_of_frames_ = len(self.frameIndex)
                    self.channelIndex = None
                
                #### BEGIN NOTE: 2019-11-21 23:09:52 
                # TODO/FIXME handle self.plot_start and self.plot_start
                # each segment (sweep, or frame) can have a different time domain
                # so when these two are specified it may result in an empty plot!!!
                #### END NOTE: 2019-11-21 23:09:52 

            elif isinstance(y, neo.core.Segment):
                #self.x = None # NOTE: x can still be supplied externally
                self.y = y
                self._plotEpochs_(clear=True)
                
                # one segment is one frame
                self.frameAxis = None
                self._number_of_frames_ = 1
                self._data_frames_ = 1
                self.frameIndex = range(self._number_of_frames_) 
                
                # see NOTE: 2019-11-22 08:37:38  - the same principle applies
                self.signalIndex = signalIndex
                self.irregularSignalIndex = irregularSignalIndex
                
                # only used for individual signals
                self.signalChannelAxis = None 
                self.signalChannelIndex = None
                self.irregularSignalChannelAxis = None
                self.irregularSignalChannelIndex = None
                self.separateSignalChannels = False
                
                self.channelIndex = channelIndex

            elif isinstance(y, neo.core.ChannelIndex):
                # TODO
                raise NotImplementedError("Plotting neo.core.ChannelIndex object is not yet implemented") 
                #NOTE: 2017-04-08 22:21:21 I need to think carefully about this
                # a ChannelIndex:
                # 1) groups all analog signals inside a block accross segments, OR
                # 2) indexes a SUBSET of the channels within an analogsignal, OR
                # 3) contains neo.core.Unit objects
                #self.frameIndex = range(1)
                #self._plotEpochs_(clear=True)
            
            elif isinstance(y, (neo.core.AnalogSignal,dt.DataSignal)):
                self.y = y
                
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
                
                if not isinstance(frameAxis, (int, type(None))):
                    raise TypeError("For AnalogSignal and DataSignal, frameAxis must be an int or None; got %s instead" % type(frameAxis).__name__)

                self.signalChannelAxis = 1
                self.signalChannelIndex = utilities.normalized_sample_index(self.y.as_array(), self.signalChannelAxis, signalChannelIndex)
                
                # dealt with by displayframe()
                self.separateSignalChannels = separateSignalChannels
                
                self._data_frames_ = 1
                
                if frameAxis is None:
                    self.frameAxis = None
                    self._number_of_frames_ = 1
                    self.frameIndex = range(self._number_of_frames_)
                    
                else:
                    frameAxis = utilities.normalized_axis_index(self.y.as_array(), frameAxis)
                    if frameAxis != self.signalChannelAxis:
                        raise ValueError("For structured signals, frame axis and signal channel axis must be identical")
                    
                    self.frameAxis = frameAxis
                    self.frameIndex = utilities.normalized_sample_index(self.y.as_array(), self.frameAxis, frameIndex)
                    self._number_of_frames_ = len(self.frameIndex)
                    
            elif isinstance(y, (neo.core.IrregularlySampledSignal, dt.IrregularlySampledDataSignal)):
                self.y = y
                self.frameIndex = range(1)
                #self.signalIndex = range(1)
                
                self._number_of_frames_ = 1
                self._data_frames_ = 1
                
                self.signalIndex = None
                self.irregularSignalIndex  = None
                self.signalChannelIndex    = None
                
                self.irregularSignalChannelIndex    = irregularSignalChannels
                self.separateSignalChannels         = separateSignalChannels

            elif isinstance(y, neo.core.Unit):
                raise NotImplementedError("Plotting neo.core.Unit objects is not yet implemented") 
                # TODO - see Epochs as example
                self.y = y
                self.frameIndex = range(1)
                self._number_of_frames_ = 1
                #self.overlays.clear() # tyaken from ancillary data in the Unit; TODO
            
            elif isinstance(y, neo.core.SpikeTrain): # plot a SpikeTrain independently of data
                # TODO - see Epochs as example
                self.y = y
                self._plotSpikeTrains_(y)
                self.frameIndex = range(1)
                self._number_of_frames_ = 1
                #self.overlays.append(self.y) # plotted as overlaid spike train
                #raise NotImplementedError("Plotting stand-alone neo.core.SpikeTrain objects is not yet implemented")
                
                #self.frameIndex = range(1)
                #self.signalIndex = range(1)
                #raise TypeError("Plotting neo.core.SpikeTrain objects is not yet implemented") 
                # TODO
            
            elif isinstance(y, neo.core.Event): # plot an event independently of data
                # TODO - see Epochs as example
                #self.overlays.append(self.y) # plotted as overlaid event
                raise NotImplementedError("Plotting stand-alone neo.core.Event objects is not yet implemented") 
                self.y = y
                self.frameIndex = range(1)
                self._number_of_frames_ = 1
                # TODO
                #NOTE: EventArray has been ditched as of neo v. 0.5.0
            
            elif isinstance(y, neo.core.Epoch): # plot an Epoch independently of data
                #self.dataAnnotations.append({"Epoch %s" % y.name: y.annotations})
                #pass # delegated to displayFrame()
                self.y = y
                self.frameIndex = range(1)
                self._number_of_frames_ = 1
                self._plotEpochs_(self.y)
                
                if self._docTitle_ is None or (isinstance(self._docTitle_, str) and len(self._docTitle_.strip()) == 0):
                    #because these may be plotted as an add-on so we don't want to mess up the title
                    if isinstance(title, str) and len(title.strip()) > 0:
                        self._doctTitle_ = title
                        
                    else:
                        self._docTitle_ = self.y.name
            
            #elif isinstance(y, vigra.VigraArray):
                #raise NotImplementedError("Plotting of vigra arrays is not yet implemented; try the ImageViewer in module 'iv'") 
                #self.frameIndex = range(1)
                #self._number_of_frames_ = 1
                # TODO -- treat this as a numpy ndarray
                
            elif isinstance(y, vigra.filters.Kernel1D):
                self.x, self.y = dt.vigraKernel1D_to_ndarray(self.y)
                self._plotEpochs_(clear=True)
                
                self.frameIndex = range(1)
                self.signalIndex = range(1)
                self._number_of_frames_ = 1
                
            elif isinstance(y, np.ndarray):
                # NOTE: 2019-11-22 12:29:43
                # this includes vigra.VigraArray
                self.y = y
                
                if self.y.ndim > 3: 
                    raise ValueError('\nCannot plot data with more than 3 dimensions\n')
                
                if self.y.ndim == 1: # one frame, one channel
                    self.frameAxis = None
                    self.frameIndex = range(1)
                    self.signalChannelIndex = range(1)
                    self._number_of_frames_ = 1
                    dataAxis = 0
                    
                elif self.y.ndim == 2:
                    if not isinstance(frameAxis, (int, str, vigra.AxisInfo, type(None))):
                        raise TypeError("Frame axis must be None, or an int (vigra arrays also accept str or AxisInfo); got %s instead" % type(frameAxis))
                    
                    if not isinstance(signalChannelAxis, (int, str, vigra.AxisInfo, type(None))):
                        raise TypeError("Signal channel axis must be None, or an int (vigra arrays also accept str or AxisInfo); got %s instead" % type(signalChannelAxis))
                    
                    if signalChannelAxis is None:
                        # by default we take columns as signal channels
                        signalChannelAxis = 1
                        
                    else:
                        if isinstance(self.y, vigra.VigraArray):
                            if isinstance(signalChannelAxis, str) and signalChannelAxis.lower().strip() != "c":
                                    warnings.warn("Channel axis index is specificed by non-canonical axis key %s" % signalChannelAxis)
                                    
                            elif isinstance(signalChannelAxis, vigra.AxisInfo):
                                if signalChannelAxis.key.lower().strip() != "c":
                                    warnings.warn("Channel axis index is specificed by non-canonical axis key %s" % signalChannelAxis)
                                    
                        signalChannelAxis = utilities.normalized_axis_index(self.y, signalChannelAxis)
                        
                    self.signalChannelAxis = signalChannelAxis
                    
                    dataAxis = 1 if self.signalChannelAxis == 0 else 0
                    
                    self.signalChannelIndex = utilities.normalized_sample_index(self.y, self.signalChannelAxis, signalChannelIndex)
                    
                    self.separateSignalChannels = separateSignalChannels
                    
                    #print("frameAxis", frameAxis)
                    
                    if frameAxis is None:
                        self.frameAxis = None
                        self._data_frames_ = 1
                        self._number_of_frames_ = 1
                        self.frameIndex = range(self._number_of_frames_)
                        
                        # NOTE: 2019-11-22 12:25:42
                        # _plotArray_() decides whether to plot all channels overlaid in
                        # one plotItem, or plot each channel in its own plotItem
                        # with plot items stacked in a column in one frame
                            
                    else:
                        # for 2D arrays, this forces plotting one channel per frame
                        frameAxis = utilities.normalized_axis_index(self.y, frameAxis)
                        
                        # NOTE: 2019-11-22 14:24:16
                        # for a 2D array it does not make sense to have frameAxis
                        # different from signalChannelAxis
                        if frameAxis != self.signalChannelAxis:
                            raise ValueError("For 2D arrays, frame axis index %d must be the same as the channel axis index (%d)" % (frameAxis, self.signalChannelAxis))
                        
                        self.frameAxis = frameAxis
                        
                        self.frameIndex = utilities.normalized_sample_index(self.y, self.frameAxis, frameIndex)
                        
                        self._number_of_frames_ = len(self.frameIndex)
                        #self._number_of_frames_ = self.y.shape[self.frameAxis]
                        
                        # displayframe() should now disregard separateSignalChannels
                    
                elif self.y.ndim == 3: 
                    # NOTE: 2019-11-22 13:33:27
                    # interpreted as several channels (axis 1) by several frames (axis 2) or vice-versa
                    # therefore both frameAxis and signalChannelAxis MUST be specified
                    #
                    if frameAxis is None:
                        raise TypeError("For 3D arrays the frame axis must be specified")
                    
                    if signalChannelAxis is None:
                        raise TypeError("for 3D arrays the signal channel axis must be specified")
                    
                    frameAxis = utilities.normalized_axis_index(self.y, frameAxis)
                    signalChannelAxis = utilities.normalized_axis_index(self.y, signalChannelAxis)
                    
                    if frameAxis  ==  signalChannelAxis:
                        raise ValueError("For 3D arrays the index of the frame axis must be different from the index of the signal channel axis")
                    
                    self.frameAxis = frameAxis
                    self.signalChannelAxis = signalChannelAxis
                    
                    axes = set([k for k in range(self.y.ndim)])
                    
                    axes.remove(self.frameAxis)
                    axes.remove(self.signalChannelAxis)
                    
                    self.frameIndex = utilities.normalized_sample_index(self.y, self.frameAxis, frameIndex)
                    
                    self._number_of_frames_ = len(self.frameIndex)

                    self.signalChannelIndex = utilities.normalized_sample_index(self.y, self.signalChannelAxis, signalChannelIndex)
                    
                    dataAxis = list(axes)[0]

                    # NOTE: 2019-11-22 14:15:46
                    # diplayframe() needs to decide whether to plot all channels 
                    # in the frame as overlaid curves in one plot item (when 
                    # separateSignalChannels is False) or in a column of plot items
                    # (when separateSignalChannels is True)
                    self.separateSignalChannels = separateSignalChannels
                    
                if x is None:
                    xx = np.linspace(0, self.y.shape[dataAxis], self.y.shape[dataAxis], 
                                    endpoint=False)[:, np.newaxis]
                        
                    self.x = xx
                    
                else:
                    if isinstance(x, (tuple, list)):
                        if len(x) != self.y.shape[dataAxis]:
                            raise TypeError("The supplied signal domain (x) must have the same size as the data axis %s" % dataAxis)
                        
                        self.x = np.array(x)
                        
                    elif isinstance(x, np.ndarray):
                        if not utilities.isVector(x):
                            raise TypeError("The supplied signal domain (x) must be a vector")
                        
                        if len(x) != self.y.shape[dataAxis]:
                            raise TypeError("The supplied signal domain (x) must have the same size as the data axis %s" % dataAxis)
                            
                        if utilities.isColumnVector(x):
                            self.x = x
                            
                        else:
                            self.x = x.T # x left unchanged if 1D
                            
                    else:
                        raise TypeError("Signal domain (x) must be None, a Python iterable of scalars or a numpy array (vector)")
                            
            elif isinstance(y, (tuple, list)):
                # pythonic sequence of stuff to plot
                # TODO 2020-03-08 11:05:06
                # code for sequence of neo.SpikeTrain, and sequence of neo.Event
                self.separateSignalChannels         = separateSignalChannels
                self.signalChannelAxis              = signalChannelAxis # only used for ndarrays, see below 

                if np.all([isinstance(i, vigra.filters.Kernel1D) for i in y]):
                    self._plotEpochs_(clear=True)
                    self.frameIndex = range(len(y))
                    self._number_of_frames_ = len(self.frameIndex)
                    self.signalIndex = 1
                    xx, yy = [dt.vigraKernel1D_to_ndarray(i) for i in y]
                    
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
                        
                    self.x = x
                        
                    self.y = yy
                    
                elif all([isinstance(i, neo.Segment) for i in y]):
                    # NOTE: 2019-11-30 09:35:42 
                    # treat this as the segments attribute of a neo.Block
                    #self.dataAnnotations = [{s.name: s.annotations} for s in y]
                    self.frameIndex = range(len(y))
                    self.frameAxis = None
                    self._data_frames_ = len(y)
                    self._number_of_frames_ = len(self.frameIndex)
                    
                    self.separateSignalChannels         = False
                    
                    self.signalChannelAxis = None
                    self.signalChannelIndex = None
                    self.irregularSignalChannelAxis     = None
                    self.irregularSignalChannelIndex    = None
                    
                    self.x = None
                    self.y = y
                    
                    self.signalIndex                    = signalIndex
                    self.irregularSignalIndex           = irregularSignalIndex
                    
                elif all([isinstance(i, (neo.core.AnalogSignal, neo.core.IrregularlySampledSignal, dt.DataSignal)) for i in y]):
                    # NOTE: 2019-11-30 09:42:27
                    # Treat this as a segment, EXCEPT that each signal is plotted
                    # in its own frame. This is because in a generic container
                    # there can be signals with different domains (e.g., t_start
                    # & t_stop).
                    # If signals must be plotted on stacked axes in the same 
                    # frame then either collected them in a segment, or concatenate
                    # them in a 3D numpy array.
                    #self.dataAnnotations = [{s.name: s.annotations} for s in y]
                    self.frameAxis = None
                    self.frameIndex = range(len(y))
                    self._data_frames_ = len(y)
                    self._number_of_frames_ = len(self.frameIndex)
                    self.signalIndex = 0
                    
                    self.x = None
                    self.y = y
                    
                elif all([isinstance(i, neo.Epoch) for i in y]):
                    #self.dataAnnotations = [{s.name: s.annotations} for s in y]
                    self.y = y
                    self._plotEpochs_(self.y)
                    self.frameIndex = range(1)
                    self._number_of_frames_ = 1
                
                elif all([isinstance(i, np.ndarray) and i.ndim <= 2 for i in y]):
                    self._plotEpochs_(clear=True)
                    self.frameIndex = range(len(y))
                    self._number_of_frames_ = len(self.frameIndex)
                    self.signalIndex = 1

                    if x is None:
                        x = [np.linspace(0, y_.shape[0], y_.shape[0], endpoint=False)[:,np.newaxis] for y_ in y]
                        
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
                                raise TypeError("'x' has incompatible shape %s" % self.x.shape)

                        else:
                            raise TypeError("Invalid x specified")
                        
                    self.x = x
                    self.y = y
                
                else:
                    raise TypeError("Can only plot a list of 1D vigra filter kernels or 1D/2D numpy arrays")
                
            else:
                raise TypeError("Plotting is not implemented for %s data types" % type(self.y).__name__)

            if isinstance(doc_title, str) and len(doc_title.strip()):
                self._docTitle_ = doc_title
                
            else:
                if isinstance(self.y, (neo.Block, neo.AnalogSignal, neo.IrregularlySampledSignal, neo.Segment, dt.DataSignal)) and (self.y.name is not None and len(self.y.name) > 0):
                    self._doctTitle_ = self.y.name
                    
                elif isinstance(self.y, (neo.Epoch, neo.SpikeTrain, neo.Event)):
                    if self._docTitle_ is None or (isinstance(self._docTitle_, str) and len(self._docTitle_.strip()) == 0):
                        #because these may be plotted as an add-on so we don't want to mess up the title
                        self._doctTitle_ = self.y.name
                        
                elif hasattr(self.y, "name") and isinstance(self.y.name, str):
                    self._doctTitle_ = self.y.name
                    
                else:
                    dataVarName = ""
                    
                    cframe = inspect.getouterframes(inspect.currentframe())[1][0]
                    try:
                        for (k,v) in cframe.f_globals.items():
                            if not type(v).__name__ in ("module","type", "function", "builtin_function_or_method"):
                                if v is self.y and not k.startswith("_"):
                                    dataVarName = k
                    finally:
                        del(cframe)
                        
                    self._docTitle_ = dataVarName
                    
            if isinstance(self._docTitle_, str) and len(self._docTitle_.strip()):
                self.setWindowTitle("%s - %s" % (self._winTitle_, self._docTitle_))
                
            else:
                self.setWindowTitle(self._winTitle_)
                
            self.plot_args = args
            self.plot_kwargs = kwargs

            if plotStyle is not None and isinstance(plotStyle, str):
                self.plotStyle = plotStyle
                
            elif style is not None and isinstance(style, str):
                self.plotStyle = style
                
            self.framesQSlider.setMaximum(self._number_of_frames_ - 1)
            self.framesQSpinBox.setMaximum(self._number_of_frames_ - 1)

            self.framesQSlider.setValue(self._current_frame_index_)
            self.framesQSpinBox.setValue(self._current_frame_index_)
            
            self.nFramesLabel.setText("of %d" % self._number_of_frames_)
            
            self.displayFrame()
            
            self._update_annotations_()

            if show:
                #self.setVisible(True)
                self.activateWindow()
                self.show()
            
        except Exception as e:
            traceback.print_exc()
            
    @property
    def currentFrame(self):
        return self._current_frame_index_
    
    @currentFrame.setter
    def currentFrame(self, val):
        """
        Emits self.frameChanged signal when not a guiClient
        """
        if not isinstance(val, int) or val not in self.frameIndex: 
            return
        
        # NOTE: 2018-09-25 23:06:55
        # recipe to block re-entrant signals in the code below
        # cleaner than manually docinenctign and re-connecting
        # and also exception-safe
        
        signalBlockers = [QtCore.QSignalBlocker(widget) for widget in \
            (self.framesQSpinBox, self.framesQSlider)]
        
        self.framesQSpinBox.setValue(val)
        self.framesQSlider.setValue(val)

        self._current_frame_index_ = val

        self.displayFrame()

    @property
    def plotItemsWithLayoutPositions(self) -> typing.List:
        """ A zipped list of tuples (PlotItem, grid coordinates).
        
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
    def plotItems(self) -> typing.List:
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
    def axes(self) -> typing.List:
        """The list of axes (PlotItem objects).
        
        Alias to self.plotItems property
        """
        return self.plotItems
    
    def axis(self, index: int) -> pg.PlotItem:
        """The axis (PlotItem) at the specified index.
        
        If index is not valid, returns None.
        
        """
        try:
            plotitem = self.signalsLayout.getItem(index,0)
            
        except:
            pass
        
        return plotitem
    
    @safeWrapper
    def plotItem(self, index: int) -> pg.PlotItem:
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
    def currentPlotItem(self) -> pg.PlotItem:
        """Reference to the selected (current) axis (PlotItem).
        
        The setter counterpart sets the current plot item to be a reference to
        the PlotItem with the specified index.
        """
        return self._current_plot_item_
    
    @currentPlotItem.setter
    def currentPlotItem(self, index: int):
        """Sets the current plot item to the one at the specified index.
        """
        plotitems_coords = self.axesWithLayoutPositions # a reference, so saves computations
        
        if len(plotitems_coords) == 0:
            #QtWidgets.QMessageBox.critical(self, "Set current axes:", "Must plot something first!")
            self._current_plot_item_ = None
            self._current_plot_item_index_ = -1
            return False
        
        plotitems, _ = zip(*plotitems_coords)
        
        if not isinstance(index, int):
            raise TypeError("Expecting an int; got a %s instead" % type(index).__name__)
        
        if index < 0 or index >= len(plotitems):
            raise ValueError("Expecting an int between 0 and %d inclusive; got %d" % (len(plotitems)-1, index))
        
        #system_palette = QtGui.QGuiApplication.palette()
        #default_border_color = self.axis(0).vb.border.color()
        
        self._current_plot_item_ = plotitems[index]
        self._current_plot_item_index_ = index
        lbl = "<B>%s</B>" % self._current_plot_item_.axes["left"]["item"].labelText
        self._current_plot_item_.setLabel("left", lbl)
        #self._current_plot_item_.vb.border.setStyle(QtCore.Qt.SolidLine)
        #self._current_plot_item_.vb.border.setColor(system_palette.highlight().color())
        
        for ax in self.axes:
            if ax is not self._current_plot_item_:
                lbl = ax.axes["left"]["item"].labelText
                
                if lbl.startswith("<B>") and lbl.endswith("</B>"):
                    lbl = lbl[3 : lbl.find("</B>")]
                    ax.setLabel("left", lbl)
                    
                #ax.vb.border.setStyle(QtCore.Qt.NoPen)
                #ax.vb.border.setColor(default_border_color)
        
        self.statusBar().showMessage("Selected axes: %d (%s)" % index, self._plot_names_.get(index))
        
    @property
    def currentAxis(self):
        return self.currentPlotItem
    
    @currentAxis.setter
    def currentAxis(self, index):
        self.currentPlotItem = index
    
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
            
        elif isinstance(index, int):
            if index >=0:
                if index >= len(self.axesWithLayoutPositions):
                    raise ValueError("index must be between -1 and %d; got %d instead" % (len(self.axesWithLayoutPositions), index))
                
                hostitem = self.axis(index)
                
            else:
                hostitem = self.signalsLayout.scene()
                
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
    
    #@safeWrapper
    #def _plotOverlayFrame_(self):
        ##print("_plotOverlayFrame_ %d" % self._current_frame_index_)
        #if self.oy is None or (type(self.oy).__name__ == "weakref" and self.oy() is None):
            ##print("no overlay")
            #return
        
        #if isinstance(self.oy, list):
            #if any([y is None or (type(y).__name__ == "weakref" and y() is None) for y in self.oy]):
                #return
            
            #if len(self.overlayFrameIndex) == 1:
                #if self.ox is not None:
                    #ox = self.ox[0]
                    
                #else:
                    #ox = None
                    
                #oy = self.oy[0]
                
            #else:
                #if self.ox is not None:
                    #ox = self.ox[self._current_frame_index_]
                    
                #else:
                    #ox = None
                    
                #oy = self.oy[self._current_frame_index_]
                
        #else:
            #oy = self.oy
            #ox = self.ox

        #if type(oy).__name__ == "weakref":
            #if isinstance(oy(), dt.DataSignal):
                #self._plotOverlaySignal_(oy().domain, oy(), *self.overlay_args, **self.overlay_kwargs)
            
            #elif isinstance(oy(), (neo.core.AnalogSignal, neo.core.IrregularlySampledSignal)):
                #self._plotOverlaySignal_(oy().times, oy(), *self.overlay_args, **self.overlay_kwargs)
                
            #elif isinstance(oy(), np.ndarray):
                #if ox is None:
                    #raise TypeError("x array None for numpy array data")
                
                #self._plotOverlaySignal_(ox(), oy(), *self.overlay_args, **self.overlay_kwargs)
                
        #else:
            #if isinstance(oy, dt.DataSignal):
                #self._plotOverlaySignal_(oy.domain, oy, *self.overlay_args, **self.overlay_kwargs)
                
            #elif isinstance(oy, (neo.core.AnalogSignal, neo.core.IrregularlySampledSignal)):
                #self._plotOverlaySignal_(oy.times, oy, *self.overlay_args, **self.overlay_kwargs)
                
            #elif isinstance(oy, np.ndarray):
                #if ox is None:
                    #raise TypeError("x array None for numpy array data")
                
                #self._plotOverlaySignal_(ox, oy, *self.overlay_args, **self.overlay_kwargs)
        
        #self.fig.canvas.draw()
            
    #@safeWrapper
    #def _plotOverlaySignal_(self, x, y, **kwargs):
        ##self.fig.add_subplot(self.nAxes,1,self.overlayAxes+1) # selects the axes if already existing
        ##self.fig.add_subplot(self.overlayAxes) # selects the axes if already existing
        
        #plot_kwargs = self.overlay_kwargs
        
        #if len(kwargs) > 0:
            #plot_kwargs.update(kwargs)
    
        #if y.ndim == 1:
            #nChannels = 1
        #else:
            #nChannels = y.shape[1]
            
        #if "color" not in plot_kwargs.keys():
            #if nChannels == 1:
                #plot_kwargs["color"] = self.defaultOverlaidLineColor
            #else:
                #plot_kwargs.pop("color", None) # fall back on color cycler
            
        #if "linewidth" not in plot_kwargs.keys():
            #plot_kwargs["linewidth"] = self.defaultOverlaidLineWidth
            
        #plot_kwargs["gid"] = "overlay"
            
        #lines = [line for line in self.fig.axes[self.overlayAxes].lines if line.get_gid() is not None and line.get_gid()=="overlay"]
        
        #if len(lines) == 0:
            #if nChannels > 1:
                #self.fig.axes[self.overlayAxes].set_prop_cycle("color", self.defaultOverlaidLineColorList)
                
            #lines = self.fig.axes[self.overlayAxes].plot(x, y, *self.overlay_args, **plot_kwargs)
            #self.fig.axes[self.overlayAxes].redraw_in_frame()
            
        #else:
            #if y.ndim == 1 and len(lines) > 1:
                #for l in lines:
                    #l.remove()
                    
                #del(lines)

                #self.fig.axes[self.overlayAxes].redraw_in_frame()
                #lines = self.fig.axes[overlayAxes].plot(x, y, *self.plot_args, **plot_kwargs)
                    
            #elif len(lines) != y.shape[1]:
                #for l in lines:
                    #l.remove()
                    
                #del(lines)
                
                #self.fig.axes[self.overlayAxes].redraw_in_frame()
                #lines = self.fig.axes[overlayAxes].plot(x, y, *self.plot_args, **plot_kwargs)
            
            #else:
                #for (k,l) in enumerate(lines):
                    #l.set_xdata(x)
                    #if y.ndim == 1:
                        #l.set_ydata(y)
                    #else:
                        #l.set_ydata(y[:,k])
                        
    
    @pyqtSlot(object, object)
    @safeWrapper
    def _slot_plot_axis_x_range_changed(self, x0, x1):
        """To update non-data items such as epochs
        """
        ax = self.sender()
        
        #print(x0,x1)
        
        #if len(ax.dataItems) == 0:
            #return
            
        if self.currentFrame in self._cached_epochs_:
            if len(self._cached_epochs_[self.currentFrame]):
                self._plotEpochs_(from_cache=True)
                
                
    @safeWrapper
    def displayFrame(self):
        """ Plots individual frame (data "sweep" or "segment")

        Delegates plotting as follows:
        
        neo.Segment                     -> _plotSegment_ # needed to pick up which signal from segment
        
        neo.AnalogSignal                -> _plotSignal_
        neo.IrregularlySampledSignal    -> _plotSignal_
        neo.Epoch                       -> _plotSignal_
        neo.SpikeTrain                  -> _plotSignal_
        neo.Event                       -> _plotSignal_
        datatypes.DataSignal            -> _plotSignal_
        vigra.Kernel1D, vigra.Kernel2D  -> _plotArray_ (after conversion to numpy.ndarray)
        numpy.ndarray                   -> _plotArray_ (including vigra.VigraArray)
        
        sequence (iterable)             -> _plotSequence_
            The sequence can contain these types:
                neo.AnalogSignal, 
                neo.IrregularlySampledSignal, 
                datatypes.DataSignal, 
                np.ndarray
                vigra.filters.Kernel1D          -> NOTE  this is converted to two numpy arrays in plot()
        
        Anything else  (?)                 -> _plot_numeric_data_
        
        """
        if self.y is None:
            return
        
        self.currentFrameAnnotations = None
        
        if isinstance(self.y, (tuple, list)): 
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
            #print("displayFrame: self.x: ", self.x)
            
            if all([isinstance(y_, (dt.DataSignal, 
                                    neo.core.AnalogSignal, 
                                    neo.core.IrregularlySampledSignal,
                                    dt.IrregularlySampledDataSignal)) for y_ in self.y]):
                self._plotSignal_(self.y[self._current_frame_index_], *self.plot_args, **self.plot_kwargs) # x is contained in the signal
                self.currentFrameAnnotations = {type(self.y[self._current_frame_index_]).__name__: self.y[self._current_frame_index_].annotations}
                
            elif all([isinstance(y_, neo.core.Epoch) for y_ in self.y]): 
                # plot an Epoch independently of data; there is a single frame
                self._plotEpochs_(self.y, **self.epoch_plot_options)
                
            elif all([isinstance(y_, neo.Segment) for y_ in self.y]):
                segment = self.y[self.frameIndex[self._current_frame_index_]]
                self._plotSegment_(segment, *self.plot_args, **self.plot_kwargs)
                self.currentFrameAnnotations = {type(segment).__name__ : segment.annotations}
            
            else: # accepts sequence of np.ndarray or VigraKernel1D objects
                self._setup_signal_choosers_(self.y)
                
                if isinstance(self.x, list):
                    self._plotArray_(self.x[self._current_frame_index_], self.y[self._current_frame_index_], *self.plot_args, **self.plot_kwargs)
                    
                else:
                    self._plotArray_(self.x, self.y[self._current_frame_index_], *self.plot_args, **self.plot_kwargs)
                    
        else:
            if isinstance(self.y, neo.core.Block):
                # NOTE: 2019-11-24 22:31:26
                # select a segment then delegate to _plotSegment_()
                # Segment selection is based on self.frameIndex, or on self.channelIndex
                if len(self.y.segments) == 0:
                    return
                
                if self._current_frame_index_ not in self.frameIndex:
                    return
                
                segmentNdx = self.frameIndex[self._current_frame_index_]
                
                if segmentNdx >= len(self.y.segments):
                    return
                
                segment = self.y.segments[segmentNdx]
                
                self._plotSegment_(segment, *self.plot_args, **self.plot_kwargs) # calls _setup_signal_choosers_() and _prepareAxes_()
                
                self.currentFrameAnnotations = {type(segment).__name__ : segment.annotations}
                
            elif isinstance(self.y, neo.core.Segment):
                # delegate straight to _plotSegment_()
                self._plotSegment_(self.y, *self.plot_args, **self.plot_kwargs) # calls _setup_signal_choosers_() and _prepareAxes_()
                
            elif isinstance(self.y, (neo.core.AnalogSignal, 
                                     dt.DataSignal, 
                                     neo.core.IrregularlySampledSignal,
                                     dt.IrregularlySampledDataSignal)):
                self._plotSignal_(self.y, *self.plot_args, **self.plot_kwargs)

            elif isinstance(self.y, neo.core.Epoch): # plot an Epoch independently of data
                self._plotEpochs_(self.y, **self.epoch_plot_options)

            elif isinstance(self.y, np.ndarray):
                try:
                    if self.y.ndim > 3:
                        raise TypeError("Numpy arrays with more than three dimensions are not supported")
                    
                    self._plotArray_(self.x, self.y, *self.plot_args, **self.plot_kwargs)
                    
                except Exception as e:
                    traceback.print_exc()
                    
            elif self.y is None:
                pass
                
            else:
                raise TypeError("Plotting of data of type %s not yet implemented" % str(type(self.y)))
            
        # NOTE: 2020-03-10 22:09:51
        # reselect an axis according to its index (if one had been selected before)
        # CAUTION: this may NOT be the same PlotItem object!
        # also makes sure we always have an axis selected
        print("start currentFrame", self.currentFrame)
        print("start current plot item", self._current_plot_item_)
        print("start current plot item index", self._current_plot_item_index_)
        print("number of axes: ", len(self.plotItems))
        
        if len(self.plotItems):
            if self._current_plot_item_ is None:
                print("no prev selected axis")
                self._current_plot_item_index_ = 0 # by default
                self._current_plot_item_ =  self.plotItems[self._current_plot_item_index_] 
                print("new current plot item", self._current_plot_item_)
                print("new current plot item index", self._current_plot_item_index_)
                
            elif self._current_plot_item_ not in self.plotItems:
                print("prev selected index", self._current_plot_item_index_)
                
                if self._current_plot_item_index_ < 0: # this is prev index
                    self._current_plot_item_index_ = 0
                    
                elif self._current_plot_item_index_ >= len(self.plotItems):
                        self._current_plot_item_index_ = len(self.plotItems) -1
                    
                self._current_plot_item_ = self.plotItems[self._current_plot_item_index_]
                
                print("reset current plot item", self._current_plot_item_)
                print("reset current plot item index", self._current_plot_item_index_)
                
            else:
                self._current_plot_item_index_ = self.plotItems.index(self._current_plot_item_)
                print("test index", self._current_plot_item_index_, "item", self._current_plot_item_)
                
            lbl = self._current_plot_item_.axes["left"]["item"].labelText
            
            if any([s not in lbl for s in ("<B>", "</B>")]):
                lbl = "<B>%s</B>" % lbl
                self._current_plot_item_.setLabel("left", lbl)

            for plotItem in self.plotItems:
                if plotItem is not self._current_plot_item_:
                    lbl = plotItem.axes["left"]["item"].labelText
                    
                    if lbl.startswith("<B>") and lbl.endswith("</B>"):
                        lbl = lbl[3 : lbl.find("</B>")]
                        plotItem.setLabel("left", lbl)
                    
        else:
            # have no axis selected as current, only when there are no axes
            # (pg.PlotItem objects)
            self._current_plot_item_ = None
            self._current_plot_item_index_ = -1
                    
        print("end current plot item", self._current_plot_item_)
        print("end current plot item index", self._current_plot_item_index_)
        print("***")
        
        self._update_annotations_()
        
    @safeWrapper
    def _plotSpikeTrains_(self, trains: typing.Optional[neo.SpikeTrain] = None, clear:bool = False, **kwargs):
        """Plots stand-alone spike trains.
        CAUTION: DO NOT use when plotting spike trains associated with a neo.Segment or neo.Unit!
        """
        if trains is None or clear:
            for k, ax in enumerate(self.axes):
                lris = [i for i in ax.items if isinstance(i, pg.LinearRegionItem)]
                
                if len(lris):
                    for l in lris:
                        ax.removeItem(l)
                        
        self._shown_spike_trains_.clear()
        
        if trains is None:
            return
            
        trains_dict = dict()
        
        if isinstance(trains, (tuple, list)):
            if all([isinstance(s, neo.SpikeTrain) for s in trains]):
                for k, t in enumerate(trains):
                    if t.name is None or (isinstance(t.name, str) and len(t.name.strip()==0)):
                        tag = k
                        
                    else:
                        tag = t.name
                        
                    trains_dict[tag] = t
                    
            else:
                raise TypeError("All elements in the 'trains' sequence mus be neo.SpikeTrain objects")
            
        elif isinstance(trains, neo.SpikeTrain):
            if trains.name is None or (isinstance(trains.name, str) and len(trains.name.strip()==0)):
                tag = 0
                
            else:
                tag = trains.name
                
            trains_dict[tag] = trains
            
        else:
            raise TypeError("Expecting a neo.SpikeTrain or a sequence (tuple, list) of neo.SpikeTrain objects; got %s instead" % type(trains).__name__)
        
        self._plot_trains_dict_(trains_dict, **kwargs)
        
    @safeWrapper
    def _plotEpochs_(self, 
                     epochs: typing.Optional[typing.Union[neo.Epoch, typing.Sequence]] = None, 
                     clear: bool = True,
                     from_cache: bool = False,
                     **kwargs):
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
            
            Standalone epoch data is an Epoch or sequence of Epoch objects
            passed as the 'y' parameter to self.setData(...) function
            (NOTE that self.setData is aliased to 'self.plot' and 'self.view').
            
            When the 'epochs' parameter is None or an empty sequence, the 
            function plots the standalone epoch data, is it exists, or clears
            any representations of previous epoch data from all axes.
            
        clear: bool, default is True.
            When True, all representations of epochs data are cleared from the
            axes, regardless if there exists standalone epoch data.
            
            Otherwise new epochs are added to the plot.
            
        from_cache: bool, default is False:
            When True, plots internally cached epochs
        
        """
        
        def _plot_epochs_seq_(*args, **kwargs):
            """Does the actual plotting of epoch data.
            Epochs is always a non-empty sequence (tuple or list) of neo.Epochs
            We keep this as a nested function to avoid calling it directly. Thus
            there is no need to check if the epochs argument is the same as 
            self.y (or contained within)
            """
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
                    warnings.warning("Invalid brush specification %s" % epoch_brush)
                    brushes = cycle([None])
                    
            # NOTE: 2020-03-09 12:09:40
            # unlike the online documentation, pg.LinearRegionItem constructor 
            # DOES NOT accept pen as argument
            #if epoch_pen is None:
                #if len(args) > 1:
                    #pens = cycle([QtGui.QPen(QtGui.QColor(*c).darker()) for c in self.epoch_plot_options["epochs_color_set"]])
                    
                #else:
                    #pens = cycle([QtGui.QPen(QtGui.QColor(0,0,255,50).darker())])
                    
            #else:
                #if isinstance(epoch_pen, tying.Sequence):
                    #if all([isinstance(b, (QtGui.QColor, QtGui.QBrush, tuple, list)) for b in epoch_pen]):
                        #pens = cycle([QtGui.QPen(QtGui.QColor(c)) if isinstance(c, (QtGui.QColor, QtGui.QBrush)) else QtGui.QPen(QtGui.QColor(*c) for c in epoch_pen)])
                        
                    #else:
                        #pens = cycle([QtGui.QPen(QtGui.QColor(*epoch_pen))])
                        
                #elif isinstance(epoch_pen, QtGui.QColor):
                    #pens = cycle([QtGui.QBrush(QtGui.QColor(epoch_pen))])
                    
                #elif isinstance(epoch_pen, QtGui.QBrush):
                    #pens = cycle([epoch_pen])
                    
                #elif isinstance(epoch_pen, QtGui.QPen):
                    #pens = cycle([epoch_pen])
                    
                #else:
                    #warnings.warning("Invalid pen specification %s" % epoch_pen)
                    
            # figure out the visible X range
            minX = list()
            maxX = list()
            
            visibleXRange = None
            
            for ax in self.axes:
                if len(ax.dataItems):
                    [x_min, x_max] = ax.viewRange()[0]
                    
                    minX.append(x_min)
                    maxX.append(x_max)
                    
            if len(minX) and len(minX) == len(maxX):
                visibleXRange = [min(minX), max(maxX)]
            
            for epoch in args:
                x0 = epoch.times.flatten().magnitude
                x1 = x0 + epoch.durations.flatten().magnitude
                
                if visibleXRange is not None:
                    x0_visible = (x0 >= visibleXRange[0]) & (x0 <  visibleXRange[1])
                    x1_visible = (x1 >  visibleXRange[0]) & (x1 <= visibleXRange[1])
                    
                    x_visible = x0_visible & x1_visible
                    
                else:
                    x_visible = np.full_like(x0, fill_value=True, dtype="bool")
                    
                #print("x_visible", x_visible)
                
                brush = next(brushes)
                
                # see NOTE: 2020-03-09 12:09:40
                #pen = next(pens)
                
                for k in range(len(self.axes)):
                    data_x_min = list()
                    data_x_max = list()
                    
                    regions = [v for v in zip(x0,x1)]
                    
                    lris = [pg.LinearRegionItem(values=value, 
                                                brush=brush, 
                                                orientation=pg.LinearRegionItem.Vertical, 
                                                movable=False, 
                                                bounds = visibleXRange) for value in regions]
                    
                    for kl, lri in enumerate(lris):
                        self.axes[k].addItem(lri)
                        lri.setZValue(10)
                        lri.setVisible(x_visible[kl])
                        lri.setRegion(regions[kl])
            
        # 1. clear existing LinearRegionItem objects.
        
        if from_cache:
            epoch_seq = self._cached_epochs_.get(self.currentFrame, None)
            
            if epoch_seq is not None:
                for k, ax in enumerate(self.axes):
                    lris = [i for i in ax.items if isinstance(i, pg.LinearRegionItem)]
                    for l in lris:
                        ax.removeItem(l)
            
                _plot_epochs_seq_(*epoch_seq, **kwargs)
                
            return
            
        if clear:
            for k, ax in enumerate(self.axes):
                lris = [i for i in ax.items if isinstance(i, pg.LinearRegionItem)]
                for l in lris:
                    ax.removeItem(l)
        
        #print("SignalViewer._plotEpochs_ epochs:", epochs)
        
        epoch_seq = None
        
        if epochs is None or len(epochs) == 0:
            # None, an empty sequence or empty epoch
            if isinstance(self.y, neo.Epoch):
                self._prepareAxes_(1) # use a brand new single axis
                epoch_seq = [self.y]
                
            elif isinstance(self.y, typing.Sequence) and all([isinstance(y_, neo.Epoch) for y_ in self.y]):
                self._prepareAxes_(1) # use a brand new single axis
                epoch_seq = self.y
                
        elif isinstance(epochs, neo.Epoch):
            epoch_seq = [epochs]
            
        elif isinstance(epochs, typing.Sequence) and all([isinstance(e, neo.Epoch) for e in epochs]):
            epoch_seq = epochs
            
        else:
            raise TypeError("Expecting a neo.Epoch or a Sequence of neo.Epoch objects; got %s instead" % type(epochs).__name__)
        
        if epoch_seq is not None:
            _plot_epochs_seq_(*epoch_seq, **kwargs)
            
            if self.currentFrame in self._cached_epochs_:
                if len(self._cached_epochs_[self.currentFrame]):
                    if clear:
                        self._cached_epochs_[self.currentFrame] = epoch_seq
                        
                    else:
                        self._cached_epochs_[self.currentFrame] += epoch_seq
                        
        else:
            self._cached_epochs_.pop(self.currentFrame, None)
                    
    @safeWrapper
    def _plot_trains_dict_(self, trains_dict, **kwargs):
        #from itertools import cycle
        
        if len(trains_dict) == 0:
            return
        
        try:
            if len(self.axes) == 0:
                self._prepareAxes_(1)
                
            spike_train_axis = self.signalsLayout.getItem(0,0)
            
            height_interval = 1/len(trains_dict)
            
            colors = cycle(self.defaultLineColorsList)
            labelStyle = {"color": "#000000"}

            trains_x_list = list()
            trains_y_list = list()
            
            for k_train, (tag, train) in enumerate(trains_dict.items()):
                data_name = tag if isinstance(tag, str) else "%d" % tag
                
                x = train.times.magnitude.flatten()
                y = np.full(x.shape, height_interval * k_train + height_interval/2)
                
                trains_x_list.append(x)
                trains_y_list.append(y)
                
            tr_x = np.concatenate(trains_x_list, axis=np.newaxis)
            tr_y = np.concatenate(trains_y_list, axis=np.newaxis)
            
            self._plot_numeric_data_(spike_train_axis,
                                        tr_x, tr_y, 
                                        symbol="spike",
                                        pen=None,
                                        name=data_name,
                                        symbolPen=pg.mkPen(pg.mkColor(next(colors))))
                
            spike_train_axis.axes["left"]["item"].setPen(None)
            spike_train_axis.axes["left"]["item"].setLabel("Spike Trains", **labelStyle)
            
        except Exception as e:
            traceback.print_exc()
            
    @safeWrapper
    def _plotSegment_(self, seg, **kwargs):
        """Plots a neo.Segment.
        Plots the signals (optionally the selected ones), and any epochs, events and
        spike trains associated woth the segment.
        """
        #from itertools import cycle
        
        if not isinstance(seg, neo.Segment):
            raise TypeError("Expecting a neo.Segment; got %s instead" % type(seg).__name__)
        
        
        # NOTE: 2019-11-24 23:21:13#
        # 1) Select which signals to display
        if isinstance(self.channelIndex, neo.ChannelIndex):
            # _set_data_() has already checked that this segment has signals 
            # linked in self.channelIndex
            # therefore at this stage, _plotSegment_() receives a segment that 
            # contains signals linked this channelIndex;
            # all we have to do is select those signals in the received segment
            # that are linked to this channelIndex
            analog = [s for s in seg.analogsignals if s in self.channelIndex.analogsignals]
            irregs = [s for s in seg.irregularlysampledsignals if s in channelIndex.irregularlysampledsignals]
            
        else:
            self.signalIndex = neoutils.normalized_data_index(seg, self.signalIndex, stype = neo.AnalogSignal)
            self.irregularSignalIndex = neoutils.normalized_data_index(seg, self.irregularSignalIndex, stype = neo.IrregularlySampledSignal)
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
        
        nAnalogAxes = len(selected_analogs) 
        
        nIrregAxes = len(selected_irregs)
        
        nAxes = nAnalogAxes + nIrregAxes
        
        signames = selected_analog_names + selected_irregs_names # required for prepare axes and caching of cursors (see comments in _prepareAxes_())
        
        # NOTE: 2019-11-25 15:19:16
        # for segments we do not plot signals with their channels separate
        # if needed, then get a reference to the signal and plot it individually
        # with separateChannels set to True
        spiketrains = neoutils.get_non_empty_spike_trains(seg.spiketrains)
        if len(spiketrains):
            nAxes += 1
            signames += ["spike trains"]
        
        events = neoutils.get_non_empty_events(seg.events)
        
        if isinstance(events, (tuple, list)) and len(events):
            nAxes += 1
            signames += ["events"]
            
        self._prepareAxes_(nAxes, sigNames=signames)
        
        axes = self.plotItems
        
        kAx = 0
        
        #### BEGIN plot analog signals 
        for k, signal in enumerate(selected_analogs):
            if isinstance(signal, neo.AnalogSignal):
                domain_name = "Time"
                
            else:
                domain_name = signal.domain_name # alternative is a dt.DataSignal
                
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
            
            self._plot_numeric_data_(plotItem,
                                     sig.times,
                                     sig.magnitude,
                                     xlabel = "%s (%s)" % (domain_name, sig.t_start.units.dimensionality),
                                     ylabel = "%s (%s)" % (sig_name, signal.units.dimensionality),
                                     name=sig_name,
                                     **kwargs)
            
            kAx += 1
         
        #### END plot analog signals
        
        #### BEGIN plot irregularly sampled signals
        for k, signal in enumerate(selected_irregs):
            if isinstance(signal, neo.IrregularlySampledSignal):
                domain_name = "Time"
                
            else:
                domain_name = signal.domain_name # alternative is a dt.IrregularlySampledDataSignal
        
            #print("_plotSegment_ irregular signal", signal.name, kAx)
            
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

            self._plot_numeric_data_(plotItem,
                                     sig.times,
                                     sig.magnitude,
                                     xlabel = "Time (%s)" % sig.t_start.units.dimensionality,
                                     ylabel = "%s (%s)" % (sig.name, signal.units.dimensionality),
                                     **kwargs)
            
            kAx += 1
        
        #### END plot irregularly sampled signals
        
        #### BEGIN plot spike trains
        if len(spiketrains):
            # plot all spike trains in this segment stacked in a single axis
            spike_train_axis = self.signalsLayout.getItem(kAx,0)
            
            symbolcolors = cycle(self.defaultLineColorsList)
            labelStyle = {"color": "#000000"}
            
            height_interval = 1/len(spiketrains) 
            
            trains_x_list = list()
            trains_y_list = list()
            
            for k_spike, spike_train in enumerate(spiketrains):
                if hasattr(spike_train, "name"):
                    data_name=spike_train.name
                else:
                    data_name="spikes"
                    
                x = spike_train.times.flatten()
                y = np.full(x.shape, height_interval * k_spike + height_interval/2)
                
                trains_x_list.append(x)
                trains_y_list.append(y)
                
            tr_x = np.concatenate(trains_x_list, axis=np.newaxis)
            tr_y = np.concatenate(trains_y_list, axis=np.newaxis)
            
            self._plot_numeric_data_(spike_train_axis,
                                        tr_x, tr_y, 
                                        symbol="spike",
                                        pen=None,
                                        name=data_name,
                                        symbolPen = pg.mkPen(color="k", cosmetic=True, width=1),
                                        symbolcolorcycle = symbolcolors)
                
            spike_train_axis.axes["left"]["item"].setPen(None)
            spike_train_axis.axes["left"]["item"].setLabel("Spike Trains", **labelStyle)

            kAx +=1
                
        #### END plot spike trains
        
        #### BEGIN plot events
        if isinstance(events, (tuple, list)) and len(events):
            # plot all event arrais in this segment stacked in a single axis
            #print("_plotSegment_ events", kAx)
            event_axis = self.signalsLayout.getItem(kAx, 0)
            
            symbolcolors = cycle(self.defaultLineColorsList)
            labelStyle = {"color": "#000000"}
            
            height_interval = 1/len(events)
            
            events_x_list = list()
            events_y_list = list()
            
            for k_event, event in enumerate(events):
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
                    
                x = event.times.flatten()
                
                if len(x):
                    events_x_list.append(x)

                    y = np.full(x.shape, height_interval * k_event + height_interval/2)
                    events_y_list.append(y)
            
            if len(events_x_list):
                ev_x = np.concatenate(events_x_list, axis=np.newaxis)
                ev_y = np.concatenate(events_y_list, axis=np.newaxis)
                
                self._plot_numeric_data_(event_axis,
                                            ev_x, ev_y, 
                                            symbol="spike", 
                                            pen=None, 
                                            name=data_name,
                                            symbolcolorcycle=symbolcolors)
                
            event_axis.axes["left"]["item"].setPen(None)
            event_axis.axes["left"]["item"].setLabel("Events", **labelStyle)
                
            kAx +=1
            
        #### END plot events
        
        #### BEGIN plot epochs
        # common logic for stand-alone epochs and for epochs associated with
        # a neo.Segment
        #print("SignalViewer._plotSegment_ => epochs:", seg.epochs)
        self._plotEpochs_(seg.epochs)
        #### END plot epochs
        
        # hide X axis spine in all but the last signal axes only if all signals
        # in the segment share the domain
        
        for k_ax in range(0, kAx-1):
            plotitem = self.signalsLayout.getItem(k_ax,0)
            if isinstance(plotitem, pg.PlotItem):
                self.signalsLayout.getItem(k_ax,0).hideAxis("bottom")
        
        if isinstance(seg.name, str) and len(seg.name.strip()):
            self.plotTitleLabel.setText(seg.name, color = "#000000")
            
        else:
            self.plotTitleLabel.setText("", color = "#000000")
            
        #try: # plot extra bits in the segment (spike trains, epochs, events arrays)
        #except Exception as e:
            #traceback.print_exc()
            
        self._current_plot_item_ = self.axis(0)
        #self._plotOverlayFrame_()
        
    @safeWrapper
    def _plotArray_(self, x, y, *args, **kwargs):
        """Called to plot a numpy array of up to three dimensions
        """
        #print("SignalViewer _plotArray_ y.ndim", y.ndim)
        self._setup_signal_choosers_(y)
        
        if y.ndim == 1:
            self._prepareAxes_(1)
            self._plot_numeric_data_(self.plotItem(0), x, y, name="Analog signal", *args, **kwargs)
            
        elif y.ndim == 2:
            #print("SignalViewer _plotArray_ frameAxis", self.frameAxis)
            #print("SignalViewer _plotArray_ number of frames", self._number_of_frames_)
            
            if self.frameAxis is None:
                if self.separateSignalChannels:
                    # plot each channel in one axis; all axes on the same frame
                    self._prepareAxes_(len(self.signalChannelIndex))
                    for kchn, chNdx in enumerate(self.signalChannelIndex):
                        self._plot_numeric_data_(self.plotItem(kchn),
                                                 x, y[utilities.arraySlice(y, {self.signalChannelAxis:chNdx})],
                                                 *args, **kwargs)
                        
                else:
                    # plot everything in the same axis
                    self._prepareAxes_(1)
                    self._plot_numeric_data_(self.plotItem(0), x, y, name="Analog signal", *args, **kwargs)
                    
            else:
                self._prepareAxes_(1) # one axis per frame: one channel per frame
                self._plot_numeric_data_(self.plotItem(0), 
                                         x, y[utilities.arraySlice(y, {self.frameAxis:self.currentFrame})],
                                         *args, **kwargs)
                
        elif y.ndim == 3:
            # the number of frame is definitely > 1 and there are more than
            # one signal channel
            if self.separateChannels:
                self._prepareAxes_(len(self.signalChannelIndex))
                for kchn, chNdx in enumerate(self.signalChannelIndex):
                    self._plot_numeric_data_(self.plotItem(kchn),
                                             x, y[utilities.arraySlice(y, {self.signalChannelAxis, chNdx})],
                                             *args, **kwargs)
                
            else:
                self._prepareAxes_(1)
                self._plot_numeric_data_(self.plotItem(0), 
                                         x, y[utilities.arraySlice(y, {self.frameAxis:self.currentFrame})],
                                         *args, **kwargs)
                
                
        else:
            raise TypeError("numpy arrays with more than three dimensions are not supported")
        
    @safeWrapper
    def _plotSignal_(self, signal, *args, **kwargs):
        """Plots individual signal objects.
        Signal objects are thiose defined in the Neuralensemble's neo package 
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

        #if not isinstance(signal, (neo.core.baseneo.BaseNeo, dt.DataSignal)):
        if not isinstance(signal, neo.core.baseneo.BaseNeo):
            raise TypeError("_plotSignal_ expects an object from neo framework, or a datatypes.DataSignal or datatypes.IrregularlySampledDataSignal; got %s instead" % (type(signal).__name__))
            
        self._setup_signal_choosers_(self.y)
        
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
                self._plot_numeric_data_(self.axis(k), np.array(sig.times),
                                           np.array(sig[:,channel].magnitude),
                                           xlabel="%s (%s)" % (domain_name, sig.t_start.units.dimensionality),
                                           ylabel="%s (%s)\nchannel %d" % (signal_name, sig.units.dimensionality, channel), 
                                           *args, **kwargs)
                    
        else:
            self._prepareAxes_(1, sigNames = [signal_name])
            
            self._plot_numeric_data_(self.axis(0), np.array(sig.times), 
                                       np.array(sig.magnitude), 
                                       ylabel="%s (%s)" % (signal_name, sig.units.dimensionality), 
                                       xlabel="%s (%s)" % (domain_name, sig.times.units.dimensionality), 
                                       *args, **kwargs)
                    

    @safeWrapper
    def _plot_numeric_data_(self, 
                            plotItem: pg.PlotItem, 
                            x:np.ndarray, 
                            y:np.ndarray,
                            xlabel:(str, type(None))=None, 
                            xunits: (str, pq.Quantity, type(None))=None,
                            ylabel:(str, type(None))=None, 
                            yunits:(str, pq.Quantity, type(None))=None,
                            title:(str, type(None))=None, 
                            name:(str, type(None))=None,
                            symbolcolorcycle:(itertools.cycle, type(None))=None,
                            *args, **kwargs):
        """ does the actual plotting of signals
        
        name is required for internal management of plot data items
        
        Returns a pyqtgraph.PlotItem where the data was plotted
        
        x and y must be 2D numpy arrays with compatible dimensions
        
        """
        # ATTENTION: x, y are both numpy arrays here !
        
        # NOTE: 2019-04-06 09:37:51 
        # there are issues with SVG export of curves containing np.nan
        
        if x.shape[0] != y.shape[0]:
            raise ValueError("x and y have different sizes on their first axes")
        
        if x.ndim > 2:
            raise TypeError("x expected to be a vector; got an array with %d dimensions instead" % x.ndim)
        
        if x.ndim == 2:
            if x.shape[1] > 1:
                raise TypeError("x expected to be a vector; got an array with %d columns instead" % x.shape[1])
    
            x = x.squeeze()
            
        if y.ndim > 2:
            raise TypeError("y expected to be an array with up to 2 dimensions; for %s dimensions instead" % y.ndim)
        
        cycle_line_colors = "pen" not in kwargs

        #pen = pg.mkPen(pg.mkColor("k"))
        symbolPen = kwargs.get("symbolPen",pg.mkPen(color="k", cosmetic=True, width=1))
        
        plotDataItems = [i for i in plotItem.listDataItems() if isinstance(i, pg.PlotDataItem)]
        
        if "name" not in kwargs:
            kwargs["name"]=name
            
        #if kwargs.get("pen", None) is None:
            #kwargs["pen"] = pen
            
        if "symbol" not in kwargs:
            kwargs["symbol"] = None
        
        if y.ndim == 1:
            y_nan_ndx = np.isnan(y)
            
            if any(y_nan_ndx):
                yy = y[~y_nan_ndx]
                xx = x[~y_nan_ndx]
                
            else:
                yy = y
                xx = x
                
            if xx.size == 0 or yy.size == 0: # nothing left to plot
                return
            
            # NOTE 2019-09-15 18:53:56:
            # FIXME find a way to circumvent clearing the plotItem in prepareAxes
            # beacuse it causes too much flicker
            # see NOTE 2019-09-15 18:53:40
            if len(plotDataItems):
                if len(plotDataItems) > 1:
                    for item in plotDataItems[1:]:
                        plotItem.removeItem(item)
                        
                plotDataItems[0].clear()
                plotDataItems[0].setData(x=xx, y=yy, **kwargs)
                
            else:
                plotItem.plot(x=xx, y=yy, **kwargs)
        
        elif y.ndim == 2:
            colors = cycle(self.defaultLineColorsList)
            
            if y.shape[1] < len(plotDataItems):
                for item in plotDataItems[y.shape[1]:]:
                    plotItem.removeItem(item)
            
            for k in range(y.shape[1]):
                y_ = y[:,k].squeeze()
                y_nan_ndx = np.isnan(y_)
                
                if any(y_nan_ndx):
                    yy = y_[~y_nan_ndx]
                    xx = x[~y_nan_ndx]
                    
                else:
                    yy = y_
                    xx = x
                
                if xx.size == 0 or yy.size == 0: # nothing left to plot
                    continue
                    
                if cycle_line_colors:
                    pen = pg.mkPen(pg.mkColor(next(colors)))
                    #pen.setColor(pg.mkColor(next(colors)))
                    kwargs["pen"] = pen
                    
                if isinstance(symbolcolorcycle, itertools.cycle):
                    symbolPen.setColor(pg.mkColor(next(symbolcolorcycle)))
                    kwargs["symbolPen"] = symbolPen
                    
                else:
                    if kwargs.get("symbolPen", None) is None:
                        kwargs["symbolPen"] = symbolPen
                    
                if k < len(plotDataItems):
                    plotDataItems[k].clear()
                    plotDataItems[k].setData(x = xx, y = yy, **kwargs)
                    
                else:
                    plotItem.plot(x = xx, y = yy, **kwargs)

        
        plotItem.setLabels(bottom = [xlabel], left=[ylabel])
        
        plotItem.setTitle(title)
        
        plotItem.replot()
        
        if self.axis_tick_font is not None:
            for ax in plotItem.axes.values():
                if ax["item"].isVisible():
                    pass
        
        plotItemCursors = self.cursorsInAxis(plotItem)
        
        for c in plotItemCursors:
            c.setBounds()
            
        if plotItem is self._current_plot_item_:
            lbl = "<B>%s</B>" % self._current_plot_item_.axes["left"]["item"].labelText
            self._current_plot_item_.setLabel("left", lbl)
            
        else:
            lbl = plotItem.axes["left"]["item"].labelText
            
            if lbl.startswith("<B>") and lbl.endswith("</B>"):
                lbl = lbl[3 : lbl.find("</B>")]
                plotItem.setLabel("left", lbl)
        
        return plotItem
           
    @safeWrapper
    def _prepareAxes_(self, nAxes, sigNames=list()):
        """sigNames: a sequence of str or None objects - either empty, or with as many elements as nAxes
        """
        plotitems = self.plotItems
        
        if not isinstance(sigNames, (tuple, list)):
            raise TypeError("Expecting sigNames to be a sequence; got %s instead" % type(sigNames).__name__)
        
        if len(sigNames):
            if len(sigNames) != nAxes:
                raise ValueError("mismatch between number of signal names in sigNames (%d) and the number of new axes (%d))" % (len(sigNames), nAxes))
            
            elif not all([isinstance(s, (str, type(None))) for s in sigNames]):
                raise TypeError("sigNames sequence must contain only strings, or None objects")
            
        else: # enforce naming of plot items!!!
            sigNames = ["signal_%d" % k for k in range(nAxes)]
            
        if nAxes == len(plotitems):
            #### requires as many axes as there already are
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
                            
            return
            
        if nAxes == 0:
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
                
            # FIXME there are issues in pyqtgraph when ViewBox objects are deleted from "outside"
            #if self.signalsLayout.scene() is not None:
                #self.signalsLayout.clear()
                
            for plotitem in plotitems:
                self.signalsLayout.removeItem(plotitem)
                
            self._plot_names_.clear()
                
            self.crosshairSignalCursors.clear()
            self.verticalSignalCursors.clear()
            self.horizontalSignalCursors.clear()
            
            self._cached_cursors_.clear()
            
        else:   # FIXME there are issues with ViewBox being deleted in pyqtgraph!
            if nAxes < len(plotitems):
                #### requires fewer axes than there currently are:
                # adapt existing plotitems then remove extra axes (plot items)
                
                #### BEGIN adapt existing plot items
                for k in range(nAxes): 
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
                for k in range(nAxes, len(plotitems)):
                    plotitem = self.signalsLayout.getItem(k, 0)
                    
                    if isinstance(plotitem, pg.PlotItem):# and plotitem in self.__plot_items__:
                        # are there any cursors in this plotitem?
                        cursors = self.cursorsInAxis(plotitem)
                        
                        if len(cursors):
                            for cursor in cursors:
                                cursor.detach() # option (b)

                            # see NOTE: 2019-03-08 13:20:50
                            self._cached_cursors_[k] = cursors
                                
                        self.signalsLayout.removeItem(plotitem)
                        self._plot_names_.pop(k, None)
                #### END remove extra plot items
                
            elif nAxes > len(plotitems):
                # requires more axes that there actually are:
                # adapt existing plotitems then add new axes
                
                #### BEGIN adapt existing plot items
                for k in range(len(plotitems)): # see NOTE: 2019-03-07 09:53:38
                    plotitem = self.signalsLayout.getItem(k, 0)
                    self._plot_names_[k] = sigNames[k]
                    
                    # clear cached cursors for these:
                    self._cached_cursors_.pop(k, None)
                    
                    # NOTE 2019-09-15 18:53:40:
                    # FIXME: this creates a nasty flicker but is we don't call
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
                for k in range(len(plotitems), nAxes):
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
                self.signalsLayout.scene().sigMouseClicked.connect(self.slot_mouseClickSelectPlotItem)
                
            if nAxes == 1:
                p = self.signalsLayout.getItem(0,0)
                #reattach multi-axes cursors
                for c in [c for c in self._data_cursors_.values() if c.isDynamic]:
                    c.detach()
                    c.attach(p)
                    
        # connect plot items scene hover events to report mouse cursor coordinates
        for p in self.axes:
            if p.scene():
                p.scene().sigMouseMoved[object].connect(self.slot_mouseMovedInPlotItem)
                p.scene().sigMouseHover[object].connect(self.slot_mouseHoverInPlotItem)
            
                
    @pyqtSlot(object)
    @safeWrapper
    def slot_mouseHoverInPlotItem(self, obj): 
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
            #self._focussed_plot_item_.vb.border.setStyle(QtCore.Qt.SolidLine)
            #self._focussed_plot_item_.vb.border.setColor(system_palette.highlight().color())
            
        else:
            self._focussed_plot_item_ = None
            
        #for ax in self.axes:
            #if ax is not self._focussed_plot_item_ and ax is not self._current_plot_item_:
                #ax.vb.border.setColor(default_border_color)
        
    @pyqtSlot(object)
    @safeWrapper
    def slot_mouseMovedInPlotItem(self, pos): # pos is a QPointF
        # connected to a PlotItem's scene!
        # at this stage there should already be a _focussed_plot_item_
        if isinstance(self._focussed_plot_item_, pg.PlotItem):
            self.reportMouseCoordinatesInAxis(pos, self._focussed_plot_item_)
                
        else:
            #self.mouseCursorCoordinateStatus.clear()
            #self._mouse_coordinates_text_ = ""
            self._update_coordinates_viewer_()
            
    @safeWrapper
    def reportMouseCoordinatesInAxis(self, pos, plotitem):
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
                #self._mouse_coordinates_text_ = ""
                self.statusBar().clearMessage()
                
            self._update_coordinates_viewer_()
    
    def _update_coordinates_viewer_(self):
        self.coordinatesViewer.setPlainText(self._cursor_coordinates_text_)
        #self.coordinatesViewer.setPlainText("\n".join([self._mouse_coordinates_text_,
                                                        #self._cursor_coordinates_text_]))
        
    @pyqtSlot(object)
    @safeWrapper
    def slot_mouseClickSelectPlotItem(self, evt):
        focusItem = self.sender().focusItem()
        
        if len(self.axes) == 0:
            return
        
        #system_palette = QtGui.QGuiApplication.palette()
        #default_border_color = self.axis(0).vb.border.color()
        
        if isinstance(focusItem, pg.ViewBox):
            plotitems, rc = zip(*self.axesWithLayoutPositions)
            #plotitems = self.plotItems
            
            focusedPlotItems = [i for i in plotitems if i.vb is focusItem]
            
            if len(focusedPlotItems):
                self._current_plot_item_ = focusedPlotItems[0]
                lbl = self._current_plot_item_.axes["left"]["item"].labelText
                if any([s not in lbl for s in ("<B>", "</B>")]):
                    lbl = "<B>%s</B>" % lbl
                    self._current_plot_item_.setLabel("left", lbl)

                plot_index = plotitems.index(self._current_plot_item_)
                self._current_plot_item_index_ = plot_index
                
                plot_row = rc[plot_index][0][0]
                
                plot_name = self._plot_names_.get(plot_row, "")
                
                if isinstance(plot_name, str) and len(plot_name.strip()):
                    self.statusBar().showMessage("Selected axes: %d (%s)" % (plotitems.index(self._current_plot_item_), plot_name))
                    
                else:
                    self.statusBar().showMessage("Selected axes: %d" % plotitems.index(self._current_plot_item_))
                    
                for ax in self.axes:
                    if ax is not self._current_plot_item_:
                        lbl = ax.axes["left"]["item"].labelText
                        
                        if lbl.startswith("<B>") and lbl.endswith("</B>"):
                            lbl = lbl[3 : lbl.find("</B>")]
                            ax.setLabel("left", lbl)
                            
            else:
                self._current_plot_item_ = None
                self._current_plot_item_index_ = -1
                
                for ax in self.axes:
                    lbl = ax.axes["left"]["item"].labelText
                    
                    if lbl.startswith("<B>") and lbl.endswith("</B>"):
                        lbl = lbl[3 : lbl.find("</B>")]
                        ax.setLabel("left", lbl)
                        
                    ax.vb.border.setStyle(QtCore.Qt.NoPen)

        else:
            self._current_plot_item_ = None
            self._current_plot_item_index_ = -1

            for ax in self.axes:
                lbl = ax.axes["left"]["item"].labelText
                
                if lbl.startswith("<B>") and lbl.endswith("</B>"):
                    lbl = lbl[3 : lbl.find("</B>")]
                    ax.setLabel("left", lbl)
                    
                ax.vb.border.setStyle(QtCore.Qt.NoPen)
                
        print("click curent item", self._current_plot_item_)
        print("click curent item index", self._current_plot_item_index_)
        print("***")
            
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
            self.signalsLayout.removeItem(p)

        self.plotTitleLabel.setText("")
        
        for c in self.crosshairSignalCursors.values():
            c.detach()
            
        for c in self.verticalSignalCursors.values():
            c.detach()
            
        for c in self.horizontalSignalCursors.values():
            c.detach()
            
        for c in self._cached_cursors_.values():
            c.detach()
            
        if not keepCursors:
            self.crosshairSignalCursors.clear() # a dict of SignalCursors mapping str name to cursor object
            self.verticalSignalCursors.clear()
            self.horizontalSignalCursors.clear()
            self._cached_cursors_.clear()
            
            self.linkedCrosshairCursors = []
            self.linkedHorizontalCursors = []
            self.linkedVerticalCursors = []
        
        #self._current_frame_index_ = 0
        self.signalNo = 0
        self.frameIndex = [0]
        self.signalIndex = 1 # NOTE: 2017-04-08 23:00:48 in effect number of signals /frame !!!
        
        #self.guiSelectedSignals.clear()
        self.guiSelectedSignalNames.clear()
        
        #self.guiSelectedIrregularSignals.clear()
        self.guiSelectedIrregularSignalNames.clear()
        
        self.y = None
        self.x = None
        
        self.plot_start = None
        self.plot_stop = None
        
        self._plotEpochs_()
        
        # NOTE: 2018-09-25 23:12:46
        # recipe to block re-entrant signals in the code below
        # cleaner than manually docinenctign and re-connecting
        # and also exception-safe
        
        signalBlockers = [QtCore.QSignalBlocker(widget) for widget in \
            (self.selectSignalComboBox, self.selectIrregularSignalComboBox)]
        
        self.selectSignalComboBox.clear()
        self.selectIrregularSignalComboBox.clear()
        
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
    
        
