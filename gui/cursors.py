# -*- coding: utf-8 -*-
"""Pyqtgraph-based cursors for signal viewers
"""
import collections, enum, numbers, typing

from PyQt5 import (QtCore, QtGui, QtWidgets,) 
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, )

# import pyqtgraph as pg
# pg.Qt.lib = "PyQt5"
from gui.pyqtgraph_patch import pyqtgraph as pg
from gui import guiutils as guiutils

import numpy as np
import quantities as pq

from core.prog import safeWrapper

class SignalCursorTypes(enum.Enum):
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
            
    @classmethod
    def getName(cls, value: tuple):
        """Inverse-lookup for name of a signal cursor type given its value.
        
        Returns None if no signal cursor type is mapped to this value.
        """
        if isinstance(value, (tuple, list)) and len(value) == 2 and all([isinstance(v, bool) for v in value]):
            value = tuple(value) # force cast to a tuple
            types = [c for c in cls if c.value == value]

            if len(types):
                return types[0].name
            

class CursorLine(pg.InfiniteLine):
    sig_double_clicked = pyqtSignal()
    
    def _init__(self, **kwargs):
        super().__init__(**kwargs)
        
    # def mouseClickevent(self, evt):
    #     self.sigClicked.emit(self, ev)
    #     if self.moving and ev.button() == QtCore.Qt.MouseButton.RightButton:
    #         ev.accept()
    #         self.setPos(self.startPosition)
    #         self.moving = False
    #         self.sigDragged.emit(self)
    #         self.sigPositionChangeFinished.emit(self)
    #     # if evt.button() == QtCore.Qt.MouseButton.RightButton:
            
        
    def mouseDoubleClickEvent(self, ev):
        if ev.button() == QtCore.Qt.LeftButton:
            ev.accept()
            self.sig_double_clicked.emit()
            
    def setHoverPen(self, *args, **kwargs):
        if self.mouseHovering:
            if isinstance(getattr(self, "label", None), pg.InfLineLabel):
                self.label.setColor(self.hoverPen.color())
            
        super().setHoverPen(*args, **kwargs)
        
    def setMouseHover(self, hover):
        if self.mouseHovering == hover:
            return
        self.mouseHovering = hover
        if hover:
            self.currentPen = self.hoverPen
        else:
            self.currentPen = self.pen
            
        if isinstance(getattr(self, "label", None), pg.InfLineLabel):
            self.label.setColor(self.currentPen.color())
        
        self.update()

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
    sig_lineContextMenuRequested = pyqtSignal(str, name = "sig_lineContextMenuRequested")
    
    sig_axisPositionChanged = pyqtSignal(tuple, name="sig_axisPositionChanged")

    default_precision = 3
    
    def __init__(self, plot_item:typing.Union[pg.PlotItem, pg.GraphicsScene], /, x:typing.Optional[typing.Union[numbers.Number, pq.Quantity]]=None, y:typing.Optional[typing.Union[numbers.Number, pq.Quantity]]=None, xwindow:float=0.0, ywindow:float=0.0, cursor_type:typing.Optional[typing.Union[str,SignalCursorTypes, tuple, list]] = None, cursorID:str="c", follower:bool=False, relative:bool=False, parent:typing.Optional[typing.Union[pg.GraphicsItem,pg.PlotItem, QtWidgets.QWidget]]=None, xBounds:typing.Optional[typing.Union[tuple, list, pq.Quantity, np.ndarray]]=None, yBounds:typing.Optional[typing.Union[tuple, list, pq.Quantity, np.ndarray]]=None, pen:typing.Optional[QtGui.QPen]=None, hoverPen:typing.Optional[QtGui.QPen]=None, linkedPen:typing.Optional[QtGui.QPen]=None, movable_label:bool=True, show_value:bool=False, precision:int=3, **kwargs):
        """ SignalCursor constructor.
            
            By default, this creates a crosshair cursor.
            
            Positional parameters:
            ======================
            
            plot_item: the axis (pyqtgraph.PlotItem) where the cursor resides, 
                        or a pyqtgraph.GraphicsScene
            
            Named parameters (key/value pairs):
            ===================================
            x: numeric or quantity scalar, or None (default) - the cursor's
                horizontal coordinate
            
            y: numeric or quantity scalar, or None (default) - the cursor's
                vertical coordinate
            
            xwindow, ywindow: float (default 0.0); horizontal and vertical 
                cursor windows
            
            cursor_type: str, SignalCursorTypes value, or a pair of bool flags 
                (as a list or tuple) specifying which cursor spine is present, 
                in the order vertical, horizontal, e.g.:
                (False, True)  -> horizontal cursor
                (True, False)  -> vertical cursor
                (True, True)   -> crosshair cursor
                (False, False) -> point cursor
            
            cursor_ID: str; optional, default is "c"
            
            relative:bool, optional, default is False
                
                Because the cursor's coordinates and in the axes domains, when 
                the plot item containing them changes data, the cursor MAY become
                invisible if its coordinates fall outside the new axes domains.
                
                This is the default behaviour.
            
                This flags, when True, indicates that the cursors should stay
                visible in the axes afte their domains have changed. This is to
                be achieved by the user of the cursor, based on this flag, since
                the cursor has no way of knowing that the axes domains are going
                to change, and what the new domains are going to be.
                
            follower:bool, default is False.
                When True, the cursor will follow the mouse pointer (a.k.a "dynamic"
                cursor).
            
            parent: 
            
            xBounds, yBounds: tuple, list, pq.Quantity, np.ndarray or None (the default)
                The min & max X and Y coordinates
    
            pen:typing.Optional[QtGui.QPen]=None
            
            hoverPen:typing.Optional[QtGui.QPen]=None
            
            linkedPen:typing.Optional[QtGui.QPen]=None
            
            movable_label:bool=True
            
            show_value:bool=False
            
            precision:int=3
            
        Var-keyword parameters:
        =======================
        (not used)
            
        """
        super(SignalCursor, self).__init__(parent=parent)
        
        # self._parent_widget_ = None
        
        # print(f"{self.__class__.__name__}.__init__ x = {x}, y = {y}, xBounds = {xBounds}, yBounds = {yBounds}")
        
        self._host_graphics_item_ = None
        
        if isinstance(plot_item, (pg.PlotItem, pg.GraphicsScene)):
            self._host_graphics_item_ = plot_item
            
        else:
            raise TypeError("plot_item expected to be a pyqtgraph.PlotItem object or a pyqtgraph.GraphicsScene object got %s instead" % type(plot_items).__name__)
            
        self._cursorId_ = None
        
        self._relative_to_axes_ = relative
        
        self._follows_mouse_ = follower
        
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
        
        # NOTE: 2023-01-14 14:01:17
        # valid ranges where the cursor lines can go
        # NOTE: 2023-01-14 14:01:24
        # will be configured by self.setBounds called from self._setup_
        self._x_range_ = None
        self._y_range_ = None
        
#         self._x_range_ = xBounds
#         self._y_range_ = yBounds
#         
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
        
        # for static cursors only (see InfiniteLine for the logic)
        # to make the lines move in concert
        self._dragging_ = False
        
        self._current_plot_item_ = None # for multi-axes cursors
        self._movable_label_ = movable_label
        self._show_value_ = show_value
        self._value_precision_ = precision if isinstance(precision, int) and precision > 0 else self.default_precision
        
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
            
        # print(f"{self.__class__.__name__}._setup_lines_ pos = {pos}")
            
        scene = self.hostScene
        
        if h:
            # set up the horizontal InfiniteLine
            if not isinstance(self._hl_, pg.InfiniteLine):
                if self._cursor_type_ == SignalCursorTypes.horizontal:
                    label = "%s {value:.%d}" % (self._cursorId_, self._value_precision_) if self._show_value_ else self._cursorId_
                else:
                    label = None
                
                self._hl_ = CursorLine(pos=pos, 
                                        angle=0, 
                                        bounds = self._y_range_,
                                        movable=not self._follows_mouse_, 
                                        name="%s_h" % name, 
                                        label=label,
                                        labelOpts = {"movable": self._movable_label_},
                                        pen=self._pen_, 
                                        hoverPen = self._hoverPen_)
                
                self._hl_.sig_double_clicked.connect(self.slot_line_doubleClicked)
                self._hl_.sigClicked.connect(self.slot_line_Clicked)
            
                if not self._follows_mouse_:
                    if self._cursor_type_ == SignalCursorTypes.horizontal:
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
            
            self._hl_.addMarker("<|>", 0)
            self._hl_.addMarker("<|>", 1)
            
            if isinstance(getattr(self._hl_, "label", None), pg.InfLineLabel):
                self._hl_.label.setColor(self._pen_.color())
            
        else:
            self._hl_ = None
            
        if v:
            # set up the vertical InfiniteLine
            if not isinstance(self._vl_, pg.InfiniteLine):
                label = "%s: {value:.%d}" % (self._cursorId_, self._value_precision_) if self._show_value_ else self._cursorId_
                #print(self._value_precision_)
                self._vl_ = CursorLine(pos=pos, 
                                        angle=90, 
                                        bounds = self._x_range_,
                                        movable=not self._follows_mouse_,
                                        name="%s_v" % name, 
                                        label=label,
                                        labelOpts={"movable": self._movable_label_},
                                        pen=self._pen_, 
                                        hoverPen = self._hoverPen_)
                
                # print(f"{self.__class__.__name__}._setup_lines__vl_.pos = {self._vl_.pos()}")
                
                self._vl_.sig_double_clicked.connect(self.slot_line_doubleClicked)
                self._vl_.sigClicked.connect(self.slot_line_Clicked)
            
                if not self._follows_mouse_: 
                    if self._cursor_type_ == SignalCursorTypes.vertical:
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

            self._vl_.addMarker("^", 0)
            self._vl_.addMarker("v", 1)
            
            if isinstance(getattr(self._vl_, "label", None), pg.InfLineLabel):
                self._vl_.label.setColor(self._pen_.color())
            
        else:
            self._vl_ = None
            
        if not isinstance(self._linkedPen_, QtGui.QPen):
            self._linkedPen_ = self._default_pen_
            
        if not self._follows_mouse_:
            scene.sigMouseMoved.connect(self._slot_mouse_event_)
            
    def _set_cursor_pen_(self, pen):
        if self._hl_ is not None:
            self._hl_.setPen(pen)
            if isinstance(self._hl_.label, pg.InfLineLabel):
                self._hl_.label.setColor(pen.color())
        
        if self._vl_ is not None:
            self._vl_.setPen(pen)
            if isinstance(self._vl_.label, pg.InfLineLabel):
                self._vl_.label.setColor(pen.color())
        
        self.update()
            
    def _get_host_boundaries_(self, host):
        """Get the useful boundaries for cursor lines, from the host.
        Boundaries are returned in the same format as from PlotItem.viewRange()
        
        NOTE: 2022-11-21 22:04:49
        Unless there is data plotted, this function does not rely on 
        PlotItem.viewRange(), because this usually extends outside of the data 
        domain and range, and thus would allow a cursor to fall outside the 
        data...
        
        One should always check cursor's boundaries and coordinates against the 
        data domain and range.
        
        """
        if isinstance(host, pg.PlotItem):
            # NOTE: 2022-11-21 16:11:36
            # Unless there is data plotted, this does not rely on PlotItem.viewRange()  
            # because this extends outside of the data domain and data range which
            # would allow a cursor to fall outside the data...
            return guiutils.getPlotItemDataBoundaries(host)
            # return self._get_plotitem_data_bounds_(host)
        
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
        """Called by programmatically setting the "y" coordinate 
        """
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
        """Called by programmatically setting "x" coordinate 
        """
        if isinstance(self._host_graphics_item_, pg.PlotItem):
            self._vl_.setPos(val)
            self._x_ = self._vl_.getXPos()
            # print(f"{self.ID} _update_vline_position_ val = {val}, self._x_ = {self._x_}")
            
        else:
            if plotitem is None:
                plotitem = self._current_plot_item_
                
            if self._current_plot_item_ is None:
                raise RuntimeError("Cannot determine the current plot item; consider calling self.setX(value, plotItem")
            
            new_X = plotItem.vb.mapViewToScene(QtCore.QPointF(val, 0.0)).x()
            
            # print(f"{self.ID} _update_vline_position_ val = {val}, new_X = {newX}")
            if self._vl_ is not None:
                self._vl_.setXPos(new_X)
                self._x_ = self._vl_.getXPos()
                
    def _add_lines_to_host_(self):
        if self._cursor_type_ == SignalCursorTypes.crosshair:
            pos = QtCore.QPointF(self._x_, self._y_)
            
        elif self._cursor_type_ == SignalCursorTypes.horizontal:
            pos = QtCore.QPointF(0.0, self._y_)
            
        else:
            pos = QtCore.QPointF(self._x_, 0.0)
            
        # print(f"{self.__class__.__name__}._add_lines_to_host_ pos = {pos}")
        
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
                
    def _update_labels_(self):
        for l in (self._hl_, self._vl_):
            if isinstance(l, pg.InfiniteLine):
                if isinstance(getattr(l, "label", None), pg.InfLineLabel):
                    if self._show_value_:
                        format_str = "%s: {value:.%d}" % (self._cursorId_, self._value_precision_)
                        l.label.setFormat(format_str)
                    else:
                        l.label.setFormat(self._cursorId_)
                        
    def update(self):
        for l in (self._hl_, self._vl_):
            if isinstance(l, pg.InfiniteLine):
                l.update()
                if isinstance(getattr(l, "label", None), pg.InfLineLabel):
                    l.label.update()
        # if isinstance(self._vl_, pg.InfiniteLine):
        #     self._vl_.update()
        #     if isinstance(self._vl_.label, pg.InfLineLabel):
        #         self._vl_.label.update()
        # if isinstance(self._hl_, pg.InfiniteLine):
        #     self._hl_.update()
        #     if isinstance(self._hl_.label, pg.InfLineLabel):
        #         self._hl_.label.update()

    def setMovableLabels(self, value):
        for l in (self._hl_, self._vl_):
            if isinstance(l, pg.InfiniteLine):
                if isinstance(getattr(l, "label", None), pg.InfLineLabel):
                    l.label.setmovable(value==True)
                
    def setShowValue(self, val:bool, precision:typing.Optional[int]=None):
        if isinstance(precision, int):
            if precision < 0:
                raise ValueError("Precision must be >= 0; got %d instead" % precision)
        
            self._value_precision_ = precision
            
        elif precision is not None:
            raise TypeError("Precision must be an int >= 0 or None; got %s instead" % precision)
        
        self._show_value_ = val==True
        self._update_labels_()
        
    def setPrecision(self, val):
        if not isinstance(val, int) or val < 0:
            raise TypeError("Precision must be an int > = 0; got %s instead" % val)
        
        self._value_precision_ = val
        
    @property
    def precision(self):
        return self._value_precision_
    
    @precision.setter
    def precision(self, val):
        if not isinstance(val, int) or val < 0:
            raise TypeError("Precision must be an int > = 0; got %s instead" % val)
        self._value_precision_ = val
        self._update_labels_()
        
    @property
    def showsValue(self):
        return self._show_value_
    
    @showsValue.setter
    def showsValue(self, value:bool):
        self._show_value_ = value == True
        self._update_labels_()
                    
    @pyqtSlot()
    @pyqtSlot(object)
    @safeWrapper
    def slot_positionChanged(self, evt=None):
        self.sig_cursorSelected.emit(self._cursorId_)
        
        if self._hl_ is not None:
            self._y_ = self._hl_.getYPos()
            
        if self._vl_ is not None:
            self._x_ = self._vl_.getXPos()
            
        if self._cursor_type_ != SignalCursorTypes.crosshair:
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
            
    def setBounds(self, host:typing.Optional[pg.GraphicsItem]=None, xBounds:typing.Optional[typing.Union[tuple, list, pq.Quantity, np.ndarray]]=None, yBounds:typing.Optional[typing.Union[tuple, list, pq.Quantity, np.ndarray]]=None):
        """ Sets the X and Y allowed range for the cursor lines
        """
        # NOTE: 2023-01-14 14:04:31
        # this is also called from __init__-> _setup_ so the xBounds and yBounds
        # parameters passed to __init__ land here
        # sets _x_range_ and _y_range
        if host is None:
            host = self._host_graphics_item_
            
        hostBounds = self._get_host_boundaries_(host) # [[xmin, xmax], [ymin, ymax]]
        
        # set bounds for vertical line:
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

        # set bounds for horizontal line:
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
            
    def yBounds(self):
        if self._hl_ is not None:
            return self._hl_.maxRange
        
    def xBounds(self):
        if self._vl_ is not None:
            return self._vl_.maxRange
            
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
            
    @safeWrapper
    def detach(self):
        if self._hl_:
            self._host_graphics_item_.removeItem(self._hl_)
            
        if self._vl_:
            self._host_graphics_item_.removeItem(self._vl_)
            
        self._host_graphics_item_ = None
            
        if isinstance(self._signal_proxy_, pg.SignalProxy):
            #self._signal_proxy_.disconnect()
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
        
        # ctype_ndx = [v for v in SignalCursorTypes.values()].index(self._cursor_type_)
        # keys = [k for k in SignalCursorTypes.keys()]
        # # ctype_ndx = [v for v in SignalCursor._cursorTypes_.values()].index(self._cursor_type_)
        # # keys = [k for k in SignalCursor._cursorTypes_.keys()]
        # 
        # show_lines = keys[ctype_ndx]
        
        show_lines = self._cursor_type_.value
        
        self._host_graphics_item_ = host
            
        self._setup_lines_(*show_lines)
            
        self._add_lines_to_host_()
        
    def _setup_(self, host:pg.GraphicsItem, cursor_type:typing.Union[str,SignalCursorTypes, tuple, list]="crosshair", x:typing.Optional[typing.Union[numbers.Number, pq.Quantity]]=None, y:typing.Optional[typing.Union[numbers.Number, pq.Quantity]]=None, xwindow:typing.Optional[float]=None, ywindow:typing.Optional[float]=None, follower:bool=False, cursorID:typing.Optional[str]=None, xBounds:typing.Optional[typing.Union[tuple, list, pq.Quantity, np.ndarray]]=None, yBounds:typing.Optional[typing.Union[tuple, list, pq.Quantity, np.ndarray]]=None, **kwargs):
        """See docstring for __init__
        """
        #print("SignalCursor._setup_ cursor_type %s" % cursor_type)
        
        show_lines = (False, False)
        
        if isinstance(cursor_type, str):
            if len(cursor_type) == 1:
                c_type_name = [name for name in SignalCursorTypes.names() if name.startswith(cursor_type)]
                if len(c_type_name):
                    cursor_type = SignalCursorTypes[c_type_name[0]]
                    
                else:
                    cursor_type = None
                
            else:
                if cursor_type in SignalCursorTypes.names():
                    cursor_type = SignalCursorTypes[cursor_type]
                    
                else:
                    cursor_type = None
                
        elif isinstance(cursor_type, (tuple, list)) and len(cursor_type) == 2 and all([isinstance(b, bool) for c in cursor_type]):
            cursor_type = Signalcursor.SignalCursorTypes.getType(cursor_type) # this may return None
            
        elif not isinstance(cursor_type, SignalCursorTypes):
            raise TypeError("cursor_type expected to be a str, a tuple of two booleans or a SignalCursorTypes; got %s instead" % type(cursor_type).__name__)
            
        # to avoid doubts, is cursor_type is None then fallback to the default (crosshair)
        if cursor_type is None:
            cursor_type = SignalCursorTypes.crosshair
            
        # now we can set which lines are shown
        show_lines = cursor_type.value
        
        self._cursor_type_ = cursor_type
            
        # will set self._x_range_ and self._y_range
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
        
        if cursorID is None or (isinstance(cursorID, str) and len(cursorID.strip())==0):
            # by now self._cursor_type_ is a SignalCursorTypes value
            if self._cursor_type_ == SignalCursorTypes.crosshair:
                cursorID = "dc" if follower else "c"
                
            elif self._cursor_type_ == SignalCursorTypes.horizontal:
                cursorID = "dh" if follower else "h"
        
            else:
                cursorID = "dv" if follower else "v"
        
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
            
        # print(f"{self.__class__.__name__}._setup_ _x_ = {self._x_} _y_ = {self._y_}")

        self._setup_lines_(*show_lines, **kwargs)
        
        # print(f"{self.__class__.__name__} in _setup_ after _setup_lines_ _x_ = {self._x_} _y_ = {self._y_}")
        
        self._add_lines_to_host_()
        
        # print(f"{self.__class__.__name__} in _setup_ after _add_lines_to_host_ _x_ = {self._x_} _y_ = {self._y_}")
        
    def _interpret_scene_mouse_events_(self, scene=None):
        """for crosshair only
        """
        if scene is None or not isinstance(scene, pg.GraphicsScene):
            scene = self.hostScene
            
        if scene is None:
            return
        
        self._dragging_ = False
        
        if self._cursor_type_ == SignalCursorTypes.crosshair:
            if scene.dragItem in (self._vl_, self._hl_):
                self._dragging_ = True
                #print("_interpret_scene_mouse_events_ _dragging_", self._dragging_)
        
    @pyqtSlot(object)
    @safeWrapper
    def _slot_selected_in_scene_(self, evt):
        # NOTE: 2019-02-09 23:29:22
        # here, evt is a mouse event, NOT a QPointF!
        scene = self.hostScene
        
        items = scene.items(evt.pos())
        
        if (self.vline is not None and self.vline in items) or \
            (self.hline is not None and self.hline in items):
            self.sig_cursorSelected.emit(self.ID)
            
    @pyqtSlot(object, object)
    def slot_line_Clicked(self, obj, evt):
        # print(f"{self.__class__.__name__}.slot_line_Clicked evt {evt}")
        # print(f"host item {self._host_graphics_item_}")
        if evt.button() == QtCore.Qt.MouseButton.RightButton:
            self.sig_lineContextMenuRequested.emit(self.ID)
            
    @pyqtSlot()
    def slot_line_doubleClicked(self):
        self.sig_doubleClicked.emit(self.ID)
            
    @pyqtSlot(object)
    @safeWrapper
    def _slot_mouse_event_(self, evt):
        """Workaround to synchronize movement of BOTH lines when mouse is dragged in the scene.
        Calls _interpret_scene_mouse_events_ in order to find out if any of the lines
        has been clicked on and if it's being dragged.
        """
        # NOTE: 2019-02-09 12:45:02
        # We cannot rely on sigDragged signal from the line we currently interact 
        # with, in order to inform the movement of the other line, because each 
        # of the cursor's lines have one of the coordinates set to 0.0 (being 
        # orthogonal)
        
        # ATTENTION: 2019-02-09 23:11:56
        # evt is a QtCore.QPointF, and NOT a mouse event object !!!
        
        scene = self.hostScene
        
        
        self._interpret_scene_mouse_events_(scene)
        
        if self._dragging_ and self._cursor_type_ == SignalCursorTypes.crosshair:
            self.sig_cursorSelected.emit(self._cursorId_)

            if isinstance(evt, (tuple, list)): # ???
                pos = evt[0] 
                
            else:
                pos = evt
                
            if isinstance(pos, (QtCore.QPointF, QtCore.QPoint)):
                self._update_lines_from_pos_(pos)
            
        else:
            if scene is not None and len(scene.clickEvents):
                mouseClickEvents = [e for e in scene.clickEvents if type(e).__name__ == "MouseClickEvent"]
                
                if len(mouseClickEvents):
                    items = scene.items(evt)
                    
                    if any([i is not None and i in items for i in (self.vline, self.hline)]):
                        self.sig_cursorSelected.emit(self.ID)
                        
                        if bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier):
                            self.sig_editMe.emit(self.ID)
                        
                        
                
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
                    
                    #if self.cursorType == SignalCursorTypes.crosshair:
                        #print("mp", mp)
                    
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
            if self._hl_:
                self._hl_.setPos(pos.y())
                self._y_ = pos.y()
                
            if self._vl_:
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
        if self.cursorType == SignalCursorTypes.vertical:
            return (self.x, self.xwindow, self.ID)
        
        elif self.cursorType == SignalCursorTypes.horizontal:
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
    def name(self):
        """Alias ot self.ID"""
        return self._cursorId_
    
    @name.setter
    def name(self, val):
        self.ID = val # might throw errors there
        
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
        self._update_labels_()
        
    @property
    def defaultPen(self):
        return self._default_pen_
    
    @property
    def isLinked(self):
        return self._linked_
        
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
        
        if self._linked_:
            self._set_cursor_pen_(self._linkedPen_)

        else:
            self._set_cursor_pen_(self._pen_)
    
    @property
    def linkedPen(self):
        return self._linkedPen_
    
    @linkedPen.setter
    def linkedPen(self, val):
        if not isinstance(val, QtGui.QPen):
            raise TypeError("expecting a QtGui.QPen; got a %s instead" % type(val).__name__)
        
        self._linkedPen_ = val
        
        if self._linked_:
            self._set_cursor_pen_(self._linkedPen_)

        else:
            self._set_cursor_pen_(self._pen_)
    
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
            
        self.update()
    
    @property
    def cursorTypeName(self):
        return self.cursorType.name
    
    @property
    def movable(self):
        return any([l.movable if isinstance(l, pg.InfiniteLine) else False for l in (self._hl_, self._vl_)])
    
    @movable.setter
    def movable(self, value:bool):
        for l in (self._hl_, self._vl_):
            if isinstance(l, pg.InfiniteLine):
                l.setMovable(value==True)
                if isinstance(getattr(l, "label", None), pg.InfLineLabel):
                    l.label.setMovable(value==True)
    
    @property
    def followsMouse(self):
        return self._follows_mouse_
    
    @followsMouse.setter
    def followsMouse(self, value:bool):
        self._follows_mouse_ = value == True
        
        # for l in (self._hl_, self._vl_):
        #     if isinstance(l, pg.InfiniteLine):
        #         l.setMovable(self._follows_mouse_)
        #         if isinstance(getattr(l,"label", None), pg.InfLineLabel):
        #             l.label.setMovable(self._movable_label_)
        
        if self.ID is None or (isinstance(self.ID, str) and len(self.ID.strip())==0):
            # by now self._cursor_type_ is a SignalCursorTypes value
            if self._cursor_type_ == SignalCursorTypes.crosshair:
                self.ID = "dc" if self._follows_mouse_ else "c"
                
            elif self._cursor_type_ == SignalCursorTypes.horizontal:
                self.ID = "dh" if self._follows_mouse_ else "h"
        
            else:
                self.ID = "dv" if self._follows_mouse_ else "v"
                
        for l in (self._hl_, self._vl_):
            if isinstance(l, pg.InfiniteLine):
                if self._follows_mouse_:
                    l.sigDragged.disconnect(self.slot_positionChanged)
                    l.sigPositionChanged.disconnect(self.slot_positionChanged)
                    l.sigPositionChangeFinished.disconnect(self.slot_positionChanged)
                else:                    
                    l.sigDragged.connect(self.slot_positionChanged)
                    l.sigPositionChanged.connect(self.slot_positionChanged)
                    l.sigPositionChangeFinished.connect(self.slot_positionChanged)
                    self.hostScene.sigMouseMoved.connect(self._slot_mouse_event_)
        
        # self._cursorId_ = cursorID
        
    @property
    def staysInAxes(self):
        return self._relative_to_axes_
    
    @staysInAxes.setter
    def staysInAxes(self, value:bool):
        self._relative_to_axes_ = value == True
        
    @property
    def cursorType(self):
        lines_tuple = (self._hl_ is not None, self._vl_ is not None)
        
        if self._cursor_type_ is None:
            self._cursor_type_ = SignalCursorTypes.getType(lines_tuple)
            
        elif isinstance(self._cursor_type_, str):
            if self._cursor_type_ in SignalCursorTypes.names():
                self._cursor_type_ = SignalCursorTypes[self._cursor_type_]
            
            else:
                self._cursor_type_ = SignalCursorTypes.getType(lines_tuple)

        elif not isinstance(self._cursor_type_, SignalCursorTypes):
            self._cursor_type_ = SignalCursorTypes.getType(lines_tuple)
            
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
            
    
