"""
    This module contains:
    
    1) PlanarGraphics objects:
        Move (aliased to Point and Start)
        Line
        Arc
        ArcMove
        Cubic
        Cursor
        Quad
        Ellipse
        Rrect
        Path
        
    2) GraphicsObject 
    A GUI representation of PlanarGraphics objects in the Qt GraphicsView framework.
    
    3) Various generic GUI utilities: mostly dialogues
"""
# NOTE: 2018-04-15 10:34:03
# frameVisibility parameter in graphics object creation:
# only use it when creating a GraphicsObject from scratch; 
# ignore it when using a PlanarGraphics object (backend) to generate a GraphicsObject
# because the frames where the graphics object is visible are set by the frame-state
# associations of the backend

# TODO/FIXME 2018-02-11 22:11:38
# consider a single Point "class", with _qt_path_composition_call_ set to either
# moveTo or lineTo, depending on whether the Point is at the beginning of a (sub)path
# or not.
#
# Dedicate the Line "class" to a real line segment (x0,y0,x1,y1)
#
# I know this is highly likely to break backward compatibility with data already
# analysed  -- TODO: patch in appropriate code for conversion especially for
# unpickling old data
#
# TODO/FIXME define a pictgui.Geometry class for n-dimensional objects
# TODO subclasses: mesh, plane, cuboid, spheroid, pyramid, cylinder, 
# TODO              truncated_pyramid, truncated_cylinder
# TODO              torus, etc etc etc
# TODO read on Qt3D geometry
# TODO a very long shot !!!

#### BEGIN core python modules
# NOTE: use Python re instead of QRegExp
import sys, os, re, numbers, itertools, warnings, traceback
import typing
import math
from collections import ChainMap, namedtuple, defaultdict, OrderedDict
from enum import Enum, IntEnum
from abc import ABCMeta, ABC
from copy import copy


#### END core python modules

#### BEGIN 3rd party modules
#import vigra.pyqt.quickdialog as quickdialog
import pyqtgraph as pg
import numpy as np

from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__
#### END 3rd party modules

__module_path__ = os.path.abspath(os.path.dirname(__file__))

#print("pgui __name__", __name__, "__module_path__", __module_path__)

#### BEGIN pict.core modules
from core.utilities import safeWrapper
from core.traitcontainers import DataBag

#import datatypes as dt
#from datatypes import DataBag
#import signalprocessing as sgp

#import imageviewer as iv
#import utilities
#### END pict.core modules

#### BEGIN pict.gui modules
from . import quickdialog
from . import resources_rc

#### END pict.gui modules

#Ui_EditColorMapWidget, QWidget = __loadUiType__(os.path.join(__module_path__,"editcolormap2.ui"))

Ui_ItemsListDialog, QDialog = __loadUiType__(os.path.join(__module_path__,"itemslistdialog.ui"))

Ui_LinearRangeMappingWidget, QWidget = __loadUiType__(os.path.join(__module_path__, "linearrangemappingwidget.ui"))

def generateColorCycle():
    pass

def generateBrushCycle(color:typing.Optional[QtGui.QColor] = None, 
                       gradients: typing.Optional[QtGui.QGradient] = None,
                       images=None,
                       pixmaps=None,
                       styles=None):
    if isinstance(values, (tuple, list)):
        if all([isinstance(v, int)]) and len(value) == 4:
            # single value spec (R,G,B,A)
            brushes = itertools.cycle(QtGui.Brush(QtGui.QColor(*c)))
            
    pass

def generatePenCycle():
    pass

def genColorTable(cmap, ncolors=256):
    if cmap is None:
        return None
    x = np.arange(ncolors)
    cnrm = colors.Normalize(vmin=min(x), vmax=max(x))
    smap = cm.ScalarMappable(norm=cnrm, cmap=cmap)
    colortable = smap.to_rgba(x, bytes=True)
    return colortable
  
# NOTE: 2017-08-12 21:45:26
# quick and simple types to ferry coordinate information between QPainterPath
# and pict routines

# The QPainterPath element types are:
#
# MoveToElement         <-> (sub)path start point
#
# LineToElement         <-> line end point
#
# CurveToElement        <-> curve end point; the type of curve is given by the
#                           number of CurveToDataElement elements that follow it:
#                           one CurveToDataElement element => quadratic curve
#                           two CurveToDataElement elements => cubic curve
#
# CurveToDataElement    <-> a curve control point: must always follow either a 
#                           CurveToElement, or a CurveToDataElement 
#
# There can be at most two CurveToDataElement element after a CurveToElement,
# and no CurveToDataElement after a MoveToElement or a LineToElement (otherwise
# behaviour is unspecified).
#
# To simplify the generation of QPainterPath instances I create namedtuples for
# moveTo, lineTo, quadratic curves (curveTo point + 1 controlData point) and 
# cubic curves (curveTo point + 2 controlData points) in order to avoid confusing
# or undefined situations, as expained below.
#
# In a QPainterPath, the lineTo and curveTo elements only specify the
# END point of the path element, because its BEGIN point is given by the previous 
# element of the path.
#
# A moveTo element at the beginning of the path sets the BEGIN point of the path
# whereas if present anywhere else, it signifies a "jump" to a new, unconnected
# subpath. Hence, a path can have as many subpaths as moveTo elements it contains.
# 
# When a path is constructed, the default constructor already intializes a moveTo
# element with coordinates (0,0) so that any other element can be aded to the path,
# and therefore no QPainterPath instance begins without a moveTo element.
#
# Several QPainterPath methods allow the addition of curves segments to the path.
# These all boil down to constructing quadratic or cubic Bezier curves.
#
# A quadratic Bezier curve is represented by TWO path elements: ONE curveTo element
# followed by ONE curveData element (one control point).
#
# A cubic Bezier curve is represented by THREE path elements: ONE curveTo element
# followed by TWO curveData elements.
#
# Apparently situations like having a lineTo or moveTo element followed by 
# one or more controlData elements, or having a curveTo element followed by 0 or
# more than two controlData elements can result in undefined behavior. Therefore,
# a QPainterPath can never be constructed from a vector of QPainterPath.Element 
# objects, and the QPainterPath.Element objects only expose a read-only API.
#
# As a simple interface to the public API for QPainterPath composition, I provide
# data structures for (sub)path start points as moveTo points, line segments as 
# lineTo points (their origin is always the previous moveTo, lineTo or curveTo 
# point) and quadratic or cubic segments, respectively as (curveTo,controlData) 
# and (curveTo, controlData, controlData) tuples. 
#
# Moreover, the type name of these data structures mirrors the QPainterPath API
# for path composition, such that it can be used in generating string expressions
# to be "exec" from within python.


def __constrain_0_45_90__(p0, p1):
    delta = p1-p0
    
    if abs(delta.x()) < abs(delta.y()):
        p2 = QtCore.QPointF(p0.x(), p1.y())
        
    elif abs(delta.x()) > abs(delta.y()):
        p2 = QtCore.QPointF(p1.x(), p0.y())
        
    else:
        p2 = p1 #it's on diagonal
    
    return p2

def __constrain_square__(p0, p1):
    """Createds a copy of p1 constrained to a square locus with p0 at the diagonally opposite corner.
    To be used for forced circles (ellipse with bounding rect constrained at square)
    
    p0 = origin point => topLeft
    p1 = dynamic point (e.g. hover, move, press, release) => bottomRight
    
    Return a QPointF constrained to a square locus; the square has its opposite corner at p0.
    
    """
    x0 = p0.x()
    y0 = p0.y()
    x1 = 0
    y1 = 0
    
    
    dx = p1.x() - x0
    dy = p1.y() - y0
    
    if dx >= 0:
        if dy >= 0:
            d = max(dx, dy)
            x1 = x0 + d
            y1 = y0 + d
        else:
            d = max(dx, abs(dy))
            x1 = x0 + d
            y1 = y0 - d
    else:
        if dy >= 0:
            d = max(abs(dx), dy)
            x1 = x0 - d
            y1 = y0 + d
        else:
            d = max(abs(dx), abs(dy))
            x1 = x0 - d
            y1 = y0 - d
            
    return QtCore.QPointF(x1, y1)

class SelectablePlotItem(pg.PlotItem):
    itemClicked = pyqtSignal()
    
    def __init__(self, **kwargs):
        super(SelectablePlotItem, self).__init__(**kwargs)
        
    def mousePressEvent(self, ev):
        super(SelectablePlotItem, self).mousePressEvent(ev)
        self.itemClicked.emit()
        
class QuickDialogComboBox(QtWidgets.QFrame):
    """A combobox to use with a QuickDialog.
    
    The combobox is nothing fancy -- only accepts a list of text items
    """
    def __init__(self, parent, label):
        QtWidgets.QFrame.__init__(self, parent)
        parent.addWidget(self)
        
        self.label = QtWidgets.QLabel(label)
        self.variable = QtWidgets.QComboBox()
        
        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setSpacing(5)
        self._layout.addWidget(self.label)
        self._layout.addWidget(self.variable, 1)
        
        self.setLayout(self._layout)
        
    def setFocus(self):
        self.variable.setFocus()
        
    def setItems(self, textList):
        if not isinstance(textList, (tuple, list)):
            raise TypeError("Expecting a sequence; got %s instead" % type(textList).__name__ )
        
        if not all([isinstance(v, str) for v in textList]):
            raise TypeError("Expecting a sequence of strings")
        
        self.variable.clear()
        
        for text in textList:
            self.variable.addItem(text)
            
    def setValue(self, index):
        if isinstance(index, int) and index >= -1 and index < self.variable.model().rowCount():
            self.variable.setCurrentIndex(index)
            
    def setText(self, text):
        if isinstance(text, str):
            self.variable.setCurrentText(text)
            
    def value(self):
        return self.variable.currentIndex()
    
    def text(self):
        return self.variable.currentText()
    
    def connectTextChanged(self, slot):
        self.currentTextChanged[str].connect(slot)
        
    def connectIndexChanged(self, slot):
        """Connects the combobox currentIndexChanged signal.
        NOTE: this is an overlaoded signal, with to versions 
        (respectively, with a str and int argument).
        
        Therefore it is expected that the connected slot is also overloaded
        to accept a str or an int
        """
        self.variable.currentIndexChanged[str].connect(slot)
        
    def disconnect(self):
        self.variable.currentIndexChanged[str].disconnect()
        
class GuiWorkerSignals(QtCore.QObject):
    signal_finished = pyqtSignal()
    sig_error = pyqtSignal(tuple)
    signal_result = pyqtSignal(object)
    
    
class GuiWorker(QtCore.QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super(GuiWorker, self).__init__()
        
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        
        self.signals = GuiWorkerSignals()
        
    @pyqtSlot()
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            
        except:
            traceback.print_exc()

            exc_type, value = sys.exc_info()[:2]
            
            self.signals.sig_error.emit((exc_type, value, traceback.format_exc()))
            
        else:
            self.signals.signal_result.emit(result)  # Return the result of the processing
            self.signals.signal_finished.emit()  # Done
            
        finally:
            self.signals.signal_finished.emit()  # Done

class ProgressWorkerSignals(QtCore.QObject):
    """See Martin Fitzpatrick's tutorial on Multithreading PyQt applications with QThreadPool 
    https://martinfitzpatrick.name/article/multithreading-pyqt-applications-with-qthreadpool/
    
    Defines the signals available from a running worker thread.

    Supported signals are:

    signal_finished
        No data

    sig_error
        `tuple` (exctype, value, traceback.format_exc() )

    signal_result
        `object` data returned from processing, anything

    signal_progress
        `int` indicating % progress

    """
    
    signal_finished = pyqtSignal()
    sig_error = pyqtSignal(tuple)
    signal_result = pyqtSignal(object)
    signal_progress = pyqtSignal(int)
    signal_setMaximum = pyqtSignal(int)
    
class ProgressWorker(QtCore.QRunnable):
    """
    ProgressWorker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param fn:  The function callback to run on this worker thread. Supplied args and 
                     kwargs will be passed through to the runner.
                     
    :type fn: function
    
        The function is expected to execute a loop computation and its signature
        should contain an optional named parameter "progressSignal" of type 
        pyqtSignal, to be emitted after each iteration of the loop code.

    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function
    
    NOTE: the entire loop is executed in a separate thread and periodically
    signals its progress by emitting the progressSignal, connected to a 
    progressDialog in the main (GUI) thread.

    """
    def __init__(self, fn, progressDialog, *args, **kwargs):
        """
        fn: callable
        progressDialog: QtWidgets.QProgressDialog
        *args, **kwargs are passed to fn
        """
        super(ProgressWorker, self).__init__()
        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = ProgressWorkerSignals()
        self.pd = progressDialog
        
        if isinstance(self.pd, QtWidgets.QProgressDialog):
            self.pd.setValue(0)
            self.signals.signal_progress.connect(self.pd.setValue)
            self.signals.signal_setMaximum.connect(self.pd.setMaximum)
            self.kwargs['progressSignal'] = self.signals.signal_progress
            self.kwargs["setMaxSignal"] = self.signals.signal_setMaximum
            
        #else:
            #self.pd = None

        # Add the callback to our kwargs
        
        #print("ProgressWorker fn args", self.args)

    @pyqtSlot()
    def run(self):
        '''Initialise the runner function with passed args, kwargs.
        This is done by calling something like threadpool.start(worker)
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
            
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.sig_error.emit((exctype, value, traceback.format_exc()))
            
        else:
            self.signals.signal_result.emit(result)  # Return the result of the processing
            
        finally:
            self.signals.signal_finished.emit()  # Done

class PlanarGraphics(object):
    """Common ancestor of all planar graphic objects :classes:
    
    PlanarGraphics objects encapsulate two-dimensional, user-defined image 
    landmarks (ROIs and Cursors). They are displayed in an image window as 
    GraphicsObject objects ("frontends") that inherit from Qt QGraphicsObject
    :class: in the QGraphics framework. 
    
    Because they encapsulate 2D (planar) shapes, PlanarGraphics are designed to 
    be used with "image" or "volume" data (e.g., numpy arrays or derived array
    types such as vigra.VigraArray).
    
    PlanarGraphics are unaware of the shape of the data array. Instead, they
    associate a state descriptor ("state") with one or all "frames" in the 
    image/volume data.
    
    In ths context, a "frame" is understood to represent a "slice" of the data
    along its "Z" axis.
    
    The state descriptors ("states") of a PlanarGraphics object are collections 
    of numeric parameters that define the planar shape. The planar descriptors
    are members of the state objects and can be accessed by their name.
    
    Each PlanarGraphics :subclass: defines its own set of planar descriptors
    in the attribute "_planar_descriptors_".
    
    In addition, the state objects have a "z_frame" attribute indicating, for
    a PlanarGraphics defined a 3D data space, which data "frame" or "slice" along
    the "Z" axis this states resides in.
    
    a) A PlanarGraphics with a single "frameless" state (z_frame is None) is
        defined in all available data frames.
    
    b) A PlanarGraphics with "frame-linked" states (their z_frame attributes have
    DISTINCT values) is defined only in the those data frames specified by the
    z_frame atributes of its state.
    
    In a PlanarGraphics object there can be several frame-linked states, linked
    to distinct frame indices, but only ONE frameless state.
    
    PlanarGraphics objects can be serialized, hence saved (pickled) alongside 
    other python data. 
    
    By contrast, the GraphicsObject objects used for display ("frontends") are 
    volatile: they cannot be serialized (or pickled) and thus, are NOT meant to
    be saved. Instead, they are created and managed by GUI code for the purpose
    of displaying PlanarGraphics objects.
    
    
    
    
    # TODO: refine documentation
    
    All non-GUI planar graphic objects must inherit from this super-class. 
    See NOTE 1 "Sub-classing PlanarGraphics", below, for details.
    
    Since these objects encapsulate planar graphics, they are by defined 
    in a single image "frame" ("slice", "plane") by a set of descriptors. 
    
    The descriptors are the planar coordinates and/or primitives that define the
    planar graphic. The number and semantics of the descriptors depend on the 
    specific planar graphics type. To allow associations between a given frame
    and a specific set of values in the state descriptors, the objects contain
    a dictionary that map frame index numbers (integers) with state objects.
    
    A "state" is defined as the set of planar graphics descriptors. State objects
    are dataypes.DataBag objects with members names given by the _planar_descriptors_
    tuple. For example:
    ("x", "y", "w", "h") for Rectangle, or Ellipse, 
    ("x", "y") for a Line (see NOTE 3, below), 
    ("x", "y", "cx", "cy") for a quadratic curve, etc.
    
    By default, a planar graphics object state have a a state that is common to
    all image frames available in the data. Because at construction time the
    number of frames in data may be unknown, there is one single state object
    created at that stage.
    
    Alternatively, the user of a planar graphics object may choose to associate 
    specific descriptor values with particular frames in the data; this is done 
    through a dictionary ("states" property) that maps frame indices (int) 
    as keys, to state DataBag objects as values.
    
    By default states is an empty dictionary.
    
    To avoid ambiguities, whenever states is not empty, (i.e, the object 
    has frame-associated states) the commonState attribute is cleared of contents.
    
    Conversely, when commonState is populated with descriptors, the states
    attribute is emptied of its contents to indicate clearly that the planar 
    graphics object has the same state across all available frames in the data.
    
    * * *
    
    When using frame-associated states, the position and/or shape of the planar
    graphics object may change acrosss image data frames, depending on the type
    the planar graphic encapsulated by the object.
    
    For example, a rectangle is defined by its top-left apex coordinates (x, y),
    width and height. These descriptors (x, y, w, h) may have different values 
    across frames and therefore the rectangle may have different position, width 
    or height across frames. However it will still remain a renctagle.
    
    A polygon or path are defined by the planar (x,y) coordinates of the 
    individual apices. When these descriptors have different values across frames
    the graphics object will also have different position and /or shape across 
    the frames.
    
    Similarly for curvilinear graphics, when the frame-associated values of the 
    descriptor change, their shape will also change.

    * * * 
    
    NOTE 1: Sub-classing PlanarGraphics.
    
    Sub-classes need to define three :class: attributes:
    
    _planar_descriptors_: a tuple of str with the name of planar descriptors, 
        in the exact order they are expected for the parametric constructor.
        
        e.g., for a Rect:
        
        _planar_descriptors_ = ("x", "y", "w", "h", "z_frame")

        NOTE: "z_frame" refers to the frame in a data array with at leats 3 dimensions
        (where it indicates the data "slice" along its "Z" axis)
        
        These being _PLANAR_ obejcts, there is no "z" coordinate as such.
        
        However they can be used to represent regions/landmarks in 3 dimensions
        by storing shape descriptors associated with each data slice (on the "Z" 
        axis of the data).
        
        The name ("z_frame") is chosen to clearly indicate this, instead of plain 
        "z" which may create confusion: unlike "z_frame", the "x" and "y" descriptors
        CAN accept calibrated data (i.e. floating point values of microns, seconds
        or whatever units are there associated with an image axis).
        
        z_frame can only be an int (index of the data slice along the "Z" axis i.e.
        "frame") or None (in which case the PlanarGraphics has the same descriptor
        throughout the entire "Z" axis of the data).
        
        
    _graphics_object_type_: a GraphicsObjectType enum value
    
        e.g., for a Rect:
        
        _graphics_object_type_ = GraphicsObjectType.rectangle
        
    _qt_path_composition_call_: a str with the QPainterPath method name (callable) to be used when
        generating a QPainterPath from this object.
        
        e.g. for a Rect:
        
        _qt_path_composition_call_ = "addRect"
        
    The only exception to these rules is for Path :subclass: which do not have a 
    preset shape and hence:
    
    1) planar descriptors do not apply -- (hence is stays empty) 
    
    2) graphics object type is determined at runtime based on the graphic elements
       that compose the path
       
    3) the composition call is one of addPath or connectPath, and which one is
       chosen in the __call__() function based on named parameters
    
    This special case is dealt with specifically for Path planar graphics objects.
    
    Besides this, they only need a constructor of the form below, that calls
    :super-class: constructor:
    
    :def: __init__(self, *args, name=None, frameindex=[], currentframe=0):
        super().__init__(*args, name=name, frameindex=frameindex, currentframe=currentframe)
        
    And that's all folks!
    
    * * *
    
    NOTE 2: About pictgui.Path objects: -- what?
    
    * * * 
    
    NOTE 3: a Line encapsulates a LineTo painter path element, therefore it is 
    defined by the (x,y) coordinates of its DESTINATION point. This is because 
    Line is an element for both Path and Polygon construction.
    
    A stand-alone line can be obtained by constructing a Path with a Move and a Line
    element.
    
    """
    
    from core import datatypes as dt
    
    # TODO 2018-01-12 16:37:21
    # methods for retrieval of individual points or QPainterPath Elements as a sequence
    
    # NOTE: 2018-01-11 12:14:45
    # attribute with names of parameters for the parametric constructor
    # of the planar graphic object
    
    # ATTENTION: these must be present in the exact order in which they are passed
    # to the parametric form of the constructor
    _planar_descriptors_ = () 
    
    _graphics_object_type_ = None
    
    _qt_path_composition_call_ = ""
    
    # NOTE: properties (descriptor names) do not belong here
    _required_attributes_ = ("_states_", "_currentframe_", 
                             "_ID_", "_linked_objects_", 
                             "_check_frame_states_", "_check_state_")
    
    def _upgrade_API_(self):
        # NOTE: 2019-03-19 13:49:51
        # see TODO - make code more efficient 19c19.py
        
        import core.datatypes as dt
        
        def __upgrade_attribute__(old_name, new_name, attr_type, default):
            needs_must = False
            if not hasattr(self, new_name):
                needs_must = True
                
            else:
                attribute = getattr(self, new_name)
                
                if not isinstance(attribute, attr_type):
                    needs_must = True
                    
            if needs_must:
                if hasattr(self, old_name):
                    old_attribute = getattr(self, old_name)
                    
                    if isinstance(old_attribute, attr_type):
                        setattr(self, new_name, old_attribute)
                        delattr(self, old_name)
                        
                    else:
                        setattr(self, new_name, default)
                        delattr(self, old_name)
                        
                else:
                    setattr(self, new_name, default)
                    
        if hasattr(self, "apiversion") and isinstance(self.apiversion, tuple) and len(self.apiversion)>=2 and all(isinstance(v, numbers.Number) for v in self.apiversion):
            vernum = self.apiversion[0] + self.apiversion[1]/10
            
            if vernum >= 0.2:
                return
            
        default_state = DataBag()
        for d in self._planar_descriptors_:
            state[d] = 0
            
        # NOTE: 2019-07-22 09:07:46
        # make this np.nan rather than None, so we can handle it numerically
        state.z_frame = None
        
        __upgrade_attribute__("__states__", "_states_", list, list())
        __upgrade_attribute__("__frontends__", "_frontends_", list, list())
        __upgrade_attribute__("__ID__", "_ID_", type(None), None)
        __upgrade_attribute__("__currentstate__", "_currentstate_", DataBag, default_state)
        
        if isinstance(self, Path):
            __upgrade_attribute__("__objects__", "_objects_", list, list())
            __upgrade_attribute__("__position__", "_position_", tuple, (float(), float()))
            
            #objs = [o for o in self._objects_ if o._currentstate_ is not None]
            
            #self._objects_[:] = objs
            
        __upgrade_attribute__("__closed__", "_closed_", bool, False)
        __upgrade_attribute__("__linked_objects__", "_linked_objects_", dict, dict())
        __upgrade_attribute__("__currentframe__", "_currentframe_", int, 0)
        
        
        #__upgrade_attribute__("__graphics_object_type__", "_graphics_object_type_", GraphicsObjectType, self._graphics_object_type_)
        
        if hasattr(self, "_frontends_"):
            delattr(self, "_frontends_")
            
        self.apiversion = (0,2)
        
                
    def __init__(self, *args, graphicstype=None, closed=False, name=None, 
                 frameindex=[], currentframe=0, 
                 linked_objects=dict()):
        """Constructor.
        
        Var-positional parameters:
        =========================
        *args: either:
        
            1) sequence of planar descriptors specific to the PlanarGraphics 
                subclass; these will be stored in a common "state descriptor" 
                object (a datatypes.DataBag) or in frame-associated 
                state descriptor objects as detailed below.
            
            2) a PlanarGraphics object (copy constructor); all other parameters
                are ignored
        
        Named parameters: (common to all PlanarGraphics subclasses)
        ================
        
        "name": str (default None) = the ID of the new object; 
                when empty, the ID is assigned the name of the graphics type
            
        frameindex: list (default, empty): contains the frame indices where this
            object is visible/has states for; 
            
            When empty, this object is visible in ALL available frames and has a
            state descriptor common to all available states (i.e., changing its 
            coordinates in any frame is reflected in all other frames as well)
            
            When not empty, the object will be visible only in the frame indices
            specified here. 
                
        currentFrame: int, default is None; only used when frameindex is not empty, 
            
            If given and not in the frameindex, the object will be "invisible"
        
        graphicstype: a member of the GraphicsObjectType enum, or
                      a str = name of valid GraphicsObjectType enum member, or
                      an int = value of a GraphicsObjectType enum value, or
                      None (default)
                      
                      When None, the graphics type is determined by the PlanarGraphics
                      subclass constructor. For Cursor, graphicstype None generates a
                      crosshair_cursor.
                      
        closed: boolean, default False: only used for Path objects
        
        """
        
        import core.datatypes as dt
    
        self.apiversion = (0,2)
        
        self._states_ = list()
        self._frontends_ = list() # see NOTE: 2019-03-09 09:52:50
        self._ID_ = None
        
        # NOTE: 2018-02-09 17:35:42
        # maps a planar graphic object to a tuples of three elements:
        #   partial, args, kwargs
        # used for coordinate mappings between two planar graphics objects
        self._linked_objects_ = dict() # PlanarGraphics: (partial, args, kwargs)
        
        
        # NOTE: 2019-03-19 15:40:01
        # new API 19c19; keep z_frame out for backwards compatibility
        # add z_frame later, from frameindex
        shape_descriptors = [d for d in self._planar_descriptors_ if d != "z_frame"]
        
        self._currentframe_ = 0
        
        # NOTE: 2019-03-21 09:00:31
        # cache the current state - make if a default state right now, update below
        # making sure this is ALWAYS a reference to one member of self._states_
        self._currentstate_ = self.defaultState()
        
        #### BEGIN check graphicstype
        # normally this should be assigned by subclass __init__
        if not isinstance(graphicstype, (type(None), int, str, GraphicsObjectType)):
            raise TypeError("graphicstype expected to be None, an int, a str or a pictgui.GraphicsObjectType; got %s instead" % type(graphicstype).__name__)
        
        if graphicstype is not None:
            if not isinstance(graphicstype, GraphicsObjectType): # by definition any GraphicsObjectType object is in GraphicsObjectType
                # the only other acceptable types, beside NoneType and GraphicsObjectType are int and str, with conditions
                if isinstance(graphicstype, str):
                    if graphicstype in [t.name for t in GraphicsObjectType]:
                        graphicstype = GraphicsObjectType[graphicstype] # => a GraphicsObjectType value
                    
                    else:
                        raise ValueError("Unknown graphics type name %s" % graphicstype)
                    
                elif isinstance(graphicstype, int):
                    if graphicstype in [t.value for t in GraphicsObjectType]:
                        graphicstype = [f for f in GraphicsObjectType if t.value == graphicstype][0] # => a GraphicsObjectType value
                        
                    else:
                        raise ValueError("Unknown graphics type value %d" % graphicstype)
                        
                    
                else:
                    raise TypeError("Invalid graphics type; expecting a GraphicsObjectType type, name or value; got %s instead" % graphicstype)
                
                
        #### END check the graphicstype
        
        #### BEGIN check frameindex
        if isinstance(frameindex, (tuple, list, range)):
            if len(frameindex):
                if len(frameindex) == 1 and frameindex[0] is None:
                    frameindex.clear()
                    
        elif frameindex is None:
            frameindex = []
            
        else:
            raise TypeError("frameindex parameter expected to be a (possibly empty) sequence of int, or a range, or None; got %s instead " % type(frameindex).__name__)
        #### END check frameindex
    
        #### BEGIN NOTE: 2019-03-21 11:51:22 check currentframe
        if isinstance(currentframe, int):
            #if currentframe < 0: # 2020-09-04 10:31:46 FIXME allow -1
                #raise ValueError("current frame expected to be >= 0; got %d instead" % currentframe)
            
            if len(frameindex):
                if currentframe not in frameindex:
                    currentframe = frameindex[0]
                
                
        elif currentframe is None:
            if len(frameindex):
                currentframe = frameindex[0] # by default !
                
            else:
                currentframe = 0 # by default!
                
        else:
            raise TypeError("currentframe expected to be an int (>=0) or None; got %s instead" % type(currentframe).__name__)
        
        #### END check currentframe
        
        self._closed_ = False
        
        # NOTE: 2018-01-12 16:18:37
        # Path is itself a list of PlanarGraphics, each with their own common state
        # and framestates; these need to be kept in sync.
        
        #print(args)
        
        if len(args):
            if len(args) == 1:
                if isinstance(args[0], self.__class__): # COPY CONSTRUCTOR
                    # NOTE: COPY CONSTRUCTOR: first var-positional parameter has
                    # the same class as self
                    # ignores named parameters
                    # ATTENTION: does NOT copy object links!
                    
                    src = args[0].copy()
                    
                    self._ID_ = src._ID_
                    
                    self._graphics_object_type_ = src._graphics_object_type_
                    
                    self._states_.clear()
                    
                    for state in src._states_:
                        self._states_.append(state.copy())
                        
                    states_w_frame = [s for s in self._states_ if s.z_frame is not None]
                    
                    if len(states_w_frame):
                        self._states_[:] = states_w_frame
                        
                    else:
                        states_wo_frame = [s for s in self._states_ is s.z_frame is None]
                        self._states_[:] = [states_wo_frame[0]]
                        self._currentstate_ = self._states_[0]
                        
                    if src._currentframe_ in [s.z_frame for s in self._states_]:
                        ss = [state for state in self._states_ if state.z_frame == src._currentframe_]
                        self._currentstate_ = ss[0]
                        
                    else:
                        self._currentstate_ = self._states_[self._currentframe_]
                        
                    self._currentframe_ = self._currentstate_.z_frame

                    return # we're DONE here
                
                elif isinstance(args[0], (tuple, list)) and len(args[0]):
                    #print("PlanarGraphics.__init__ tuple c'tor", args)
                    # c'tor from a sequence of coefficients for 
                    # PlanarGraphics passed as a single var-pos parameter to __init__()
                    # Also:
                    #  c'tor from a single parameter which is a DataBag
                    #  used by self.copy()
                    if all([isinstance(v, numbers.Real) for v in args[0]]):
                        # contruct from sequence of planar descriptors
                        state = DataBag()
                        
                        for k, key in enumerate(shape_descriptors):
                            setattr(state, key, args[0][k])
                            
                        #assign frame states
                        if len(frameindex):
                            for k in range(len(frameindex)):
                                s = state.copy()
                                s.z_frame = frameindex[k]
                                self._states_.append(s)
                                
                            # see NOTE 2019-03-21 11:51:22 
                            # currentframe MAY be None !
                            
                            if currentframe in frameindex:
                                states = [s for s in self._states_ if s.z_frame == currentframe]
                                self._currentstate_ = states[0]
                                
                            else:
                                self._currentstate_ = self._states_[currentframe]
                            
                        else:
                            state.z_frame  = currentframe
                            self._states_.append(state)
                            self._currentstate_ = self._states_[0]
                            
                        #assign graphics type; set it to crosshair if a generic cursor type was requested
                        if isinstance(self, Cursor):
                            if graphicstype is None:# or not graphicstype & GraphicsObjectType.allCursorTypes:
                                self._graphics_object_type_ = GraphicsObjectType.crosshair_cursor

                            else:
                                self._graphics_object_type_ = graphicstype
                                
                    elif all([isinstance(v, DataBag) and self._check_state_(v) for v in args[0]]):
                        # construct from sequence of states
                        # NOTE: UNPICKLING sequence of states
                        # get the frame indices from the states, or from the frameindices if specified
                        states = args[0]

                        if len(frameindex):
                            if len(frameindex) != len(states):
                                raise ValueError("mismatch between number of states (%d) and frame indices (%d)" % (len(states), len(frameindex)))
                            
                            for k, s in enumerate(states):
                                s.z_frame = frameindex[k]
                                
                        else:
                            if len(states) > 1:
                                if any([getattr(s, "z_frame", None) is None for s in states]):
                                    # only allow z_frame None for a single-element sequence of states
                                    raise ValueError("All states in the sequence with more than one element must have a defined frame index")
                            
                            state_frames = [s.z_frame for s in states]
                            
                            if len(set(state_frames)) < len(state_frames):
                                raise ValueError("States sequence cannot contain states with the same z_frame value")
                            
                        self._states_[:] = states
                        
                        if currentframe in frameindex:
                            states = [s for s in self._states_ if s.z_frame == currentframe]
                            
                            if len(states):
                                self._currentstate_ = states[0]
                                
                            else:
                                self._currentstate_ = self._states_[0]
                                
                        elif currentframe is None:
                            self._currentstate_ = self._states_[0]
                            
                        if isinstance(self, Cursor):
                            if graphicstype is None:# or not graphicstype & GraphicsObjectType.allCursorTypes:
                                self._graphics_object_type_ = GraphicsObjectType.crosshair_cursor
                                
                            else:
                                self._graphics_object_type_ = graphicstype
                                
                elif isinstance(args[0], DataBag) and all ([hasattr(args[0], a) for a in shape_descriptors]):
                    # NOTE: constructor from a single state object (DataBag) 
                    # also used for UNPICKLING planar graphics object with single state
                    # 
                    # since the args[0] is a single DataBag, we assume it is a common state
                    # possibly with "soft" frame-state associations if frameindex is not empty
                    
                    self._states_.clear()
                    
                    if len(frameindex):
                        for frame in frameindex:
                            s = args[0].copy()
                            s.z_frame = frame
                            self._states_.append(s)
                            
                    else:
                        s = args[0].copy()
                        
                        if not hasattr(s, "z_frame"):
                            s.z_frame = None
                            
                        self._states_.append(s)
                            
                    # set the current state -- do we really need self._currentstate_?
                    if currentframe in frameindex:
                        states = [s for s in self._states_ if s.z_frame == currentframe]
                        
                        if len(states):
                            self._currentstate_ = states[0]
                            
                        else:
                            self._currentstate_ = self._states_[0]
                            
                    elif currentframe is None:
                        self._currentstate_ = self._states_[0]
                    
                    if isinstance(self, Cursor):
                        if graphicstype is None:# or not graphicstype & GraphicsObjectType.allCursorTypes:
                            self._graphics_object_type_ = GraphicsObjectType.crosshair_cursor
                                
                        else:
                            self._graphics_object_type_ = graphicstype
                                
                elif isinstance(args[0], dict) and len(args[0]) and self._check_frame_states_(args[0]):
                    # NOTE: UNPICKLING planar graphics object (element)
                    # according to old API
                    
                    # NOTE: 2019-03-19 16:16:23
                    # comment below obsolete
                    # with hard frame-state associations; 
                    # check the dict has the correct layout of coordinates
                    # althogh this might not be necessary, as this c'tor is called
                    # upon unpickling
                    
                    # NOTE: soft frame-state associations are serialzed with a 
                    # common state and a list of frames (frameindex)
                    
                    for k in args[0].keys():
                        s = args[0][k].copy()
                        s.z_frame = k
                        self._states_.append(s)
                        
                    if currentframe in frameindex:
                        states = [s for s in self._states_ if s.z_frame == currentframe]
                        
                        if len(states):
                            self._currentstate_ = states[0]
                            
                        else:
                            self._currentstate_ = self._states_[0]
                            
                    elif currentframe is None:
                        self._currentstate_ = self._states_[0]
                        
                    if isinstance(self, Cursor):
                        if graphicstype is None:# or not graphicstype & GraphicsObjectType.allCursorTypes:
                            self._graphics_object_type_ = GraphicsObjectType.crosshair_cursor
                                
                        else:
                            self._graphics_object_type_ = graphicstype
                                
                elif isinstance(args[0], str):
                    # PlanarGraphics of type "text"
                    state = DataBag()
                    state.text = args[0]
                    state.z_frame = None
                    #setattr(state, "text", args[0])
                    
                    if len(frameindex):
                        for k in range(len(frameindex)):
                            s = state.copy()
                            s.z_frame = frameindex[k]
                            self._states_.add(s)
                        
                    if currentframe in frameindex:
                        states = [s for s in self._states_ if s.z_frame == currentframe]
                        if len(states):
                            self._currentstate_ = states[0]
                            
                        else:
                            self._currentstate_ = self._states_[0]
                            
                    elif currentframe is None:
                        self._currentstate_ = self._states_[0]
                        
                    self._graphics_object_type_ = GraphicsObjectType.text
                    
                else:
                    return # -- what?
                    #raise TypeError("When there is a single var-positional parameter, it should be a %s, a dict, a datatypes.DataBag, or a tuple of PlanarGraphics or coordinate pairs; got %s instead" \
                        #% (self.__class__.__name__, args[0]))
                    
            else:
                # NOTE: many var-positional arguments -- scalars: their number, order and 
                # semantics are dictated by self._planar_descriptors_ when not empty
                # When constructing a Path, args must contain individual PlanarGraphics objects
                # for text PlanarGraphics there is only one shape descriptor in the sequence
                # of descriptors and is a str
                # NOTE shape descriptors are the planar_descriptors less z_frame
                
                if isinstance(self, Path):
                    raise TypeError("Cannot use parametric constructor to initaalise a Path")
                
                
                state = DataBag()
                
                self._states_ = []

                if len(args) != len(shape_descriptors):
                    raise RuntimeError("Expecting values for %d planar graphic descriptors %s as var-positional parameters; got %d instead" % 
                                        (len(shape_descriptors), tuple(shape_descriptors), len(args)))
                
                for k, key in enumerate(shape_descriptors):
                    if isinstance(self, Text) and k == 0: # for text PlanarGraphics there is ONE shape descriptor and is a str
                        if not isinstance(args[k], str):
                            raise TypeError("Text:  first argument must be a str; got %s instead" % type(args[k]).__name__)
                
                    elif not isinstance(args[k], numbers.Number):
                        raise TypeError("argument %d expected to be a number; got %s instead" % (k, type(args[k]).__name__))
                        
                    setattr(state, key, args[k])
                    
                if len(frameindex):
                    for f in frameindex:
                        s = state.copy()
                        s.z_frame = f
                        self._states_.append(s)
                        
                else:
                    state.z_frame = None
                    self._states_.append(state)
                    
                if currentframe in frameindex:
                    states = [s for s in self._states_ if s.z_frame == currentframe]
                    
                    if len(states):
                        self._currentstate_ = states[0]
                        
                    else:
                        self._currentstate_ = self._states_[0]
                        
                else:
                    self._currentstate_ = self._states_[0]
                
                if isinstance(self, Cursor):
                    if graphicstype is None:# or not graphicstype & GraphicsObjectType.allCursorTypes:
                        self._graphics_object_type_ = GraphicsObjectType.crosshair_cursor
                        
                    else:
                        self._graphics_object_type_ = graphicstype
                        
                else:
                    self._graphics_object_type_ = graphicstype
                        
        else: # no var-positional parameters given
            state = DataBag()
            state.z_frame = None
            
            # use default values for planar descriptors
            for p in shape_descriptors:
                state[p] = 0
                
            if len(frameindex):
                for k in range(len(frameindex)):
                    s = state.copy()
                    s.z_frame = frameindex(k)
                    self._states_.append(s)
                    
            else:
                self._states_.append(state)
            
                if len(frameindex):
                    for k in range(len(frameindex)):
                        s = state.copy()
                        s.z_frame = frameindex[k]
                        self._states_.append(s)
                    
            if currentframe in frameindex:
                states = [s for s in self._states_ if s.z_frame == currentframe]
                
                if len(states):
                    self._currentstate_ = states[0]
                    
                else:
                    self._currentstate_ = self._states_[0]
                    
            elif currentframe is None:
                self._currentstate_ = self._states_[0]
            
            self._graphics_object_type_ = graphicstype
        
        if isinstance(name, str) and len(name):
            self._ID_ = name
            
        else:
            if isinstance(self._graphics_object_type_, GraphicsObjectType):
                self._ID_ = self._graphics_object_type_.name
            else:
                self._ID_ = self.__class__.__name__
                
        if len(linked_objects):
            # TODO: deep copy
            self._linked_objects_.update(linked_objects)
            
    def __reduce__(self):
        shape_descriptors = [d for d in self._planar_descriptors_ if d != "z_frame"]
        
        if len(self._states_) == 1:
            state = [s for s in self._states_][0]
            return __new_planar_graphic__, (self.__class__,
                                         self._states_[0],
                                         self._ID_,
                                         [],
                                         self.currentFrame,
                                         self._graphics_object_type_,
                                         self.closed,
                                         self._linked_objects_.copy())
        elif len(self._states_) > 1:
            states = sorted(self._states_,
                            key = lambda x:x.z_frame)
            
            framedx = [s.z_frame for s in states]
            
            return __new_planar_graphic__, (self.__class__,
                                         states,
                                         self._ID_,
                                         [],
                                         self.currentFrame,
                                         self._graphics_object_type_,
                                         self.closed,
                                         self._linked_objects_.copy())
        
        else:
            state = DataBag()
            
            for d in shape_descriptors:
                state[d] = 0
                
            state.z_frame = None
            
            return __new_planar_graphic__, (self.__class__,
                                         state,
                                         self._ID_,
                                         [],
                                         None,
                                         self._graphics_object_type_,
                                         self.closed,
                                         self._linked_objects_.copy())
        
    def __str__(self):
        states_str = ""
        
        framestr = ""
        #print(len(self._states_))
        
        if len(self._states_) > 0:
            states = self._states_
            
            if not any([s.z_frame is None for s in states]):
                states = sorted(self._states_, key = lambda x: x.z_frame)
                
            for state in states:
                states_str = ", ".join(["%s=%s" % (key, state[key]) for key in self._planar_descriptors_])
                
            framestr = "frames %s" % ([s.z_frame for s in self._states_])
            
        return "%s:\n name: %s\n type: %s\n states: %s\n frames: %s\n current frame: %s" % (self.__repr__(),
                                                                                            self._ID_,
                                                                                            self.type,
                                                                                            states_str,
                                                                                            framestr,
                                                                                            self.currentFrame)
            
    #"def" __eq__(self, other):
        ## TODO
        

    def __call__(self, path=None, frame=None, closed=None, connected=False):
        """Returns a QtGui.QPainterPath object. 
        
        QPainterPath composition methods used here depend on the subclass of
        PlanarGraphics, and is specified by the _qt_path_composition_call_
        :class: attribute.
        
        moveTo(...)
        lineTo(...)
        cubicTo...()
        quadTo(...)
        arcTo(...)
        arcMoveTo(...)
        addEllipse(...)
        addRect(...)
        addPath(...) -- implicitly used when self is a Path
        
        Not generated here are:
        addPolygon(...)
        connectPath(...)
        
        """
        if path is None:
            path = QtGui.QPainterPath()
            
        if closed is None:
            closePath = self.closed
            
        elif isinstance(closed, bool):
            closePath = closed
            
        else:
            raise TypeError("closed expected to be a boolean or None; got %s instead" % type(closed).__name__)
        
        if frame is None:
            state = self.currentState # the common state or the state associated with current frame, if present
            
        else:
            state = self.getState(frame)
            
        #print("%s PlanarGraphics() state %s" % (self.name, state) )
            
        if state is None or len(state) == 0:
            return path
            
        if connected and path.elementCount() > 0:
            s = ["lineTo("]
            
        else:
            s = [self._qt_path_composition_call_+"("]
        
            
        #shape_descriptors = [d for d in self._planar_descriptors_ if d != "z_frame"]

        s += [",".join(["%f" % getattr(state, a) for a in self.shapeDescriptors])]

        s += [")"]
        
        #cmd = "".join(s)
        #print("cmd %s" % cmd )
        
        eval("path."+"".join(s))
        
        if closePath:
            path.lineTo(state.x, state.y)
        
        return path
            
    def __getattr__(self, name):
        """low-level read access to this objects's attributes
        """
        if name in self._planar_descriptors_:
            if self._currentstate_ is not None:
                return getattr(self._currentstate_, name)
            
        elif name in self.__dict__:
                return self.__dict__[name]
            
        elif name == "currentFrame":
            if isinstance(self._currentstate_, (tuple, list)): # ???
                self._currentstate_ = self._currentstate_[0]
            return self._currentstate_.z_frame
            
        else:
            raise AttributeError("%s objects do not have an attribute named '%s'" % (self.__class__.__name__, name))
        
    def __setattr__(self, name, value):
        """low-level write access to this object's attributes
        """
        
        if name in self._planar_descriptors_:
            setattr(self._currentstate_, name, value)
            
            self.updateLinkedObjects() # TODO move this out of __setattr__; let the caller take care of this
                    
        elif name in self._required_attributes_:
            self.__dict__[name] = value
            
        else:
            super().__setattr__(name, value)
            
    def _check_state_(self, value):
        import core.datatypes as dt
        
        if not isinstance(value, DataBag):
            return False
        
        shape_descriptors = [d for d in self._planar_descriptors_ if d != "z_frame"]
        
        return all([hasattr(value, a) for a in shape_descriptors])
            
    def _check_frame_states_(self, value):
        """Checks that the states in "value" are conformant.
        Applied _check_state_ or each element in value.
        
        Parameters:
        ===========
        
        A sequence of DataBag objects, or a mapping of int keys to DataBag 
        values.
        
        """
        if isinstance(value, (tuple, list)):
            return all([self._check_state_(v) for v in value])
            
        elif isinstance(value, dict):
            return all([isinstance(k, int) and self._check_state_(v) for (k, v) in value.items()])
        
        else:
            return False
        
    @property
    def pos(self):
        """The position of this object as a Qt QPointF.
        """
        position = self.position
        #print("PlanarGraphics.pos: position = (%s, %s)" % position)
        if any([p is None for p in position]):
            return QtCore.QPointF()
        
        return QtCore.QPointF(position[0], position[1])
    
    @pos.setter
    def pos(self, value):
        if isinstance(value, (QtCore.QPoint, QtCore.QPointF)):
            self.position = (value.x(), value.y())
            
        else:
            raise TypeError("Expecting a QPoint or QPointF; got %s instead" % type(value).__name__)
        
    
    @property
    def position(self):
        """The position of this object as (x,y) coordinates tuple.
        
        To change, assign a pair (x,y) of new coordinate values (a tuple), 
        a QPoint, or a QPointF object to this property.
        
        See "x" and "y" properties for what these coordinates mean.
        
        """
        #print("PlanarGraphics.position() for %s " % self)
        return (self.x, self.y)
    
    @position.setter
    def position(self, x):
        if isinstance(x, (tuple, list)) and len(x) == 2 and all([isinstance(v, numbers.Real) for v in x]):
            y = x[1]
            x = x[0]
            
        elif isinstance(x, (QtCore.QPoint, QtCore.QPointF)):
            y = x.y()
            x = x.x()
            
        else:
            raise TypeError("Expecting x,y a pair of real scalars, or just a Qt QPoint or QPointF")

        self.x = x[0]
        self.y = x[1]
        
        self.updateLinkedObjects()
        
    def translate(self, dx, dy):
        self.x += dx
        self.x += dy
        
    def point(self, frame=None):
        """Alias to qPoint()
        """
        return self.qPoint(frame=frame)
    
    def points(self, frame=None):
        """Alias to qPoints
        """
        return self.qPoints(frame=frame)
    
    def qPoints(self, frame=None):
        """Returns a list of QPointF objects.
        
        For primitive PlanarGraphics the points encapsulate the (x,y)
        coordinates of the "destination" point - typically the first point -
        for the current state. The current state is either the common state or
        the state associated with the current state.
        
        Special primitives (ArcTo, Ellipse, Rect, etc) that inherit from
        PlanarGraphics may need to override this function. 
        
        Path objects should override this to return a list of destination QPointF
        objects of its elements, with subpaths being unravelled.
        
        If a frame is given and there is no state associated with it, the points 
        in the list are null points (0,0)
        
        """
        if frame is None:
            state = self.currentState # the common state or the state associated with current frame, if present
            
        else:
            state = self.getState(frame)
                
            #if frame in self.frameIndices:
                #state = self.getState(frame)
                
            #else:
                #warnings.warn("%s.qPoints(): No state is associated with specified frame (%d)" % (self.__class__.__name__, frame), stacklevel=2)
                #return [QtCore.QPointF()]
        
        if state is None or len(state) == 0:
            warnings.warn("%s.qPoints(): Undefined state" % self.__class__.__name__, stacklevel=2)
            return [QtCore.QPointF()]
        
        return [QtCore.QPointF(state.x, state.y)]
        
    
    def qPoint(self, frame=None):
        """Returns the QPointF of the destination.
        For Path, returns the QPoint of its first element.
        
        This may be a null point if specified frame does not associate a state.
        
        Relies on qPoints, which should be overridden by :subclasses:
        
        """
        return self.qPoints(frame=frame)[0]
    
    @property
    def linkedObjects(self):
        return [obj for obj in self._linked_objects_.keys()]
    
    @property
    def objectLinks(self):
        """Directly exposes the _linked_objects_ dictionary
        """
        return self._linked_objects_
    
    @safeWrapper
    def unlinkFromObject(self, obj):
        """ Breaks the link between this PlanarGraphics (self) and obj.
        
        Obj is a PlanarGraphics object to which self is linked, and is present
        in self._linked_objects_.keys()
        
        CAUTION: the reverse link, if it exists, is untouched.
        
        """
        
        if obj in self._linked_objects_.keys():
            # NOTE: 2018-06-09 08:18:35
            # remove the link, but leave its frontends alone!
            # deletion of the now unlinked object, if ans when necessary,
            # must be done outside this function!
            # ATTENTION: ONE function -> ONE task
            
            self._linked_objects_.pop(obj, None)
            
    def clearObjectLinks(self):
        self._linked_objects_.clear()
    
    #"def" queryFrames(self, container):
        #if hasattr(container, "nFrames"
    
    @property
    def currentState(self):
        """Read-only.
        
        NOTE: even if this is a read-only property, the returned object is 
        mutable.
        
        """
        if len(self._states_) == 1 and self._states_[0].z_frame is None:
            self._currentstate_ = self._states_[0]
        
        return self._currentstate_ # always a reference to one of self._states_
        
    @property
    def currentFrame(self):
        """Gets/sets the frame index of the "current" state, or None for no current state
        
        For Path PlanarGraphics objects, returns the current frame of the first
        element (which should be the same as for all other elements in the Path)
        
        optional parameter:
        ==================
        value: int
        
        Sets the frame index in "value" as the "current" frame.
        When the PlanarGraphics object has frame-associate states, any changes to
        the planar graphic descriptors are applied to the state associated with the
        "current" frame index.
        
        For Path PlanarGraphics objects, the current frame for all its component 
        elements are set to this value.
                
        """
        #self._currentframe_ = self._currentstate_.z_frame
        
        #return self._currentframe_
        
        if self._currentstate_ is None:
            return None
    
        return self._currentstate_.z_frame
    
    @currentFrame.setter
    def currentFrame(self, value):
        """Sets the frame index in "value" as the "current" frame.
        
        Will select current state as the state having z_frame the same as value.
        
        If such a state is not found the current state is set to None.
        
        For PlanarGraphics Path objects, the current frame for all its component 
        elements are set to this value.
        
        """
        if not isinstance(value, (int, type(None))):
            raise TypeError("expecting an int or None; got %s instead" % type(value).__name__)
        
        if len(self._states_) > 1: # there cannot be any frameless states here
            states = [s for s in self._states_ if s.z_frame is value]
            
            if len(states):
                self._currentstate_ = states[0]
                
            else:
                self._currentstate_ = None
            
        else: # just one state:
            if value is None:
                # select the only state as its current state
                self._currentstate_ = self._states_[0]
                
            else:
                if self._states_[0].z_frame is None or self._states_[0].z_frame == value:
                    self._currentstate_ = self._states_[0]
                
                else:
                    self._currentstate_ = None
        
        #print("PlanarGraphics %s current frame set to %d: current state %s" % (type(self).__name__, value, self._currentstate_))
        
    @property
    def sortedStates(self):
        """A list of frame states, sorted by their z_frame attribute
        
        """
        if len(self._states_) > 1:
            return sorted(self._states_, key = lambda x:x.z_frame)
        
        else:
            return self._states_
        
    @property
    def states(self):
        """The underlying list of states
        
        """
        return self._states_
        
    @property
    def descriptors(self):
        """Returns a tuple of planar graphics descriptor names specific to this
        concrete subclass.
        Read-only; returns a tuple (immutable sequence)
        """
        return self._planar_descriptors_
    
    @property
    def shapeDescriptors(self):
        return [d for d in self._planar_descriptors_ if d != "z_frame"]
    
    @property
    def closed(self):
        return self._closed_
    
    @closed.setter
    def closed(self, value):
        if not isinstance(value, bool):
            raise TypeError("value expected to be a boolean; got %s instead" % type(value).__name__)
        
        self._closed_ = value
        
    def defaultState(self):
        """Returns a state conaining planar descriptors specific to this
        subclass.
        
        The descriptors have the default value of 0, except for the z_frame which is
        set to None
        
        """
        #print("PlanarGraphics.defaultState()")
        import core.datatypes as dt
        state = DataBag()
        for d in self._planar_descriptors_:
            state[d] = 0
            
        # NOTE: 2019-07-22 09:07:46
        # make this np.nan rather than None, so we can handle it numerically
        #state.z_frame = None
        state.z_frame = -1 # 2020-09-04 10:24:35 FIXME as a DataBag this is expected to be an Int trait
        #state.z_frame = np.nan
        
        return state
    
    def asControlPath(self, frame=None):
        """Returns a copy of this object as a Path object containing control points.
        
        The returned Path is composed of Move and Line elements only.
        
        Path objects and special graphics primitives (e.g., ArcTo, ArcMoveTo, 
        Ellipse, Rect, Cubic, Quad, etc) should override this function.
        
        """
        import core.datatypes as dt
        
        ret = Path()
        
        state = self.getState(frame)
        
        if state is None:
            return ret
        
        if isinstance(state, DataBag) and len(state)==0:
            ret.append(Move(state.x, state.y))
            # NOTE: 2018-04-20 16:08:03
            # override in a :subclass: 
            
        return ret
    
    def asPath(self, frame=None, closed=False):
        """Returns a COPY of this object's state as a Path, for the specified frame.
        
        The state is the one associated with the specified frame or with the 
        current state.
        
        """
        import core.datatypes as dt
        
        ret = Path()
        
        if frame is None:
            state = self.currentState
            
        else:
            state = self.getState(frame)
        
        if isinstance(state, DataBag) and len(state):
            ret.append(self.__class__(state.copy(), graphicstype = self._graphics_object_type_))
            
        return ret
    
    def convertToPath(self, closed=False): 
        """Creates a Path from all frame-state associations.
        """
        frame_states = self.states
        
        frame_ndx = self.frameIndices
        
        ret = self.asPath(frame=frame_ndx[0], closed=closed)
        
        for f in frame_ndx[1:]:
            frame_path = self.asPath(frame=f, closed=closed)
            
            ret.addState(frame_path.currentState, f)
            
        ret.currentFrame = self.currentFrame
        
        return ret
    
    def copy(self):
        """Calls copy constructor and returns the result.
        WARNING: linked objects are stored by reference
        """
        #print("PlanarGraphics.copy() frameIndices", self.frameIndices)
        
        #if isinstance(self, Path):
            #print("PlanarGraphics.copy() %s %s len(self) %d \n %s" % (self.type, self.name, len(self), self))
        
        #Path objects need special treatment here:
        
        if isinstance(self, Path):
            ret = self.__class__(self)
        
        else:
            ret = self.__class__(self.states, 
                                graphicstype=self._graphics_object_type_,
                                frameindex=self.frameIndices,
                                name=self._ID_,
                                closed=self.closed,
                                currentframe = self.currentFrame) # conforms with the new API
        
        ret._linked_objects_ = self._linked_objects_
        
        #if isinstance(self, Path):
            #print("PlanarGraphics.copy() returns: %s %s len(ret) %d \n %s" % (ret.type, ret.name, len(ret), ret))
            
        return ret
    
    #"def" appendStates(self, other, dest_frame_mapping=None, src_frame_mapping=None):
        #"""
        #dest_frame_mapping, src_frame_mapping:  dict.
        
            #Both are dictionaries with int keys (old state frames) mapped to int
            #values (new frame states).
            
            #dest_frame_mapping, src_frame_mapping are applied, respectively, for
            #the destination (self) and the object to be joined ("other")
                            
            #Must ensure neither of them have duplicate values (and also that values 
            #in src_frame_mapping do not duiplicate values in dest_frame_mapping).
        
        #Used when concatenating multi-frame image data along their frame axis, such that
        #the same PlanarGraphics will contain different states associated with diferent
        #frame sequences.
        
        #Returns a NEW object!
        
        #What this function does:
        #=======================
        #The states of the "other" are appended to the states of this object, 
        #and their frame links are adjusted.
        
        #In the default scenario, where both mapping parameters are None, the 
        #state of the other are appended such that their linked frame indices point
        #to frames beyonf the highest frame index in the states of thsi object.
        
        
        #Cursor objects can only join states with Cursor objects of with the same
        #:type: attribute
        
        #Non-Cursor PlanarGraphics objects can join states with another non-Cursor 
        #PlanarGraphics object, regardless of their :type: attribute. 
        
            #* if both objects have the same :type: attribute AND are of the same
            #PlanarGraphics :subclass:, the receiver ("self") will append the 
            #frame-state associations of the other (after adjusting for frame 
            #indices)
            
            #* if the objects have different :type: attribute and / or different
            #PlanarGraphics :subclass:, the receiver ("self") will be cast to a 
            #Path object then the states of the other will be appended.
                
        #The result is always a NEW PlanarGraphics object
        
        #NOTE: when either PlanarGraphics has a singe frameless state, its state
        #will be first linked to frame index 0. If this is not what is intended
        #then the PlanarGraphics object should contain as many states as there
        #are frames (i.e. linkFrames() should be called first).
        
        #"""
        ##check dest_frame_mapping, remap destination frames
        #if isinstance(dest_frame_mapping, dict): # this being a dict, there are no duplicate keys
            #if not all([isinstance(k, int) for k in dest_frame_mapping]):
                #raise TypeError("dest_frame_mapping keys must be int")
            
            #if any([k not in receiver_frames for k in dest_frame_mapping]):
                #raise ValueError("some keys in dest_frame_mapping are invalid frame indices for this object (%s)" % self name)
            
            ##new_receiver_frame_ndx = [v for v in dest_frame_mapping.values()]
        
            #if not all([isinstance(v, int) for v in dest_frame_mapping.values()]):
                #raise TypeError("dest_frame_mapping must contain only int values")
            
            #if any([v < 0 for v in dest_frame_mapping.values()]):
                #raise ValueError("dest_frame_mapping must contain only values >= 0")
            
            #if len(set(dest_frame_mapping.values())) != len(dest_frame_mapping):
                #raise ValueError("dest_frame_mapping contains duplicate values")
            
            #ret.remapFrameStateAssociations(dest_frame_mapping)
            
            ## refresh these two
            #receiver_states = sorted(ret._states_, key = lambda x: x.z_frame)
            
            #receiver_frames = [s.z_frame for s in receiver_states]
        
            
        #elif dest_frame_mapping is not None:
            #raise TypeError("dest_frame_mapping expected to be a dict or None; got %s instead" % type((dest_frame_mapping).__name__))
        
        #if isinstance(src_frame_mapping, dict):
            #if not all([isinstance(k, int) for k in src_frame_mapping]):
                #raise TypeError("src_frame_mapping keys must be int")
            
            #if any([k not in src_frames for k in src_frame_mapping]):
                #raise ValueError("src_frame_mapping contains invalid keys as original frame indices")
            
            ##new_receiver_frame_ndx = [v for v in src_frame_mapping.values()]
        
            #if not all([isinstance(v, int) for v in src_frame_mapping.values()):
                #raise TypeError("src_frame_mapping must contain only int values")
            
            #if any([v < 0 for v in src_frame_mapping.values()]):
                #raise ValueError("src_frame_mapping must contain only values >= 0")
            
            #if len(set(src_frame_mapping.values())) < len(src_frame_mapping):
                #raise ValueError("src_frame_mapping contains duplicate values")
            
        #elif src_frame_mapping is None:
            ## we neee to place these to "higher" frame index
            #tgt_frames = sorted(ret.states, key = lambda x:x.z_frame)
            
            #src_frames = sorted(src.states, key = lambda)
            #src_frame_mapping = dict()
            
        #else:
            #raise TypeError("src_frame_mapping expected to be a dict or None; got %s instead" % type((src_frame_mapping).__name__))
        
        ## now check that src_frame_mapping
        
        #if dest_frame_mapping is not None:
            #if not all([isinstance(m, (tuple, list)) for m in dest_frame_mapping]):
                #raise TypeError("dest_frame_mapping must contain tuple elements")
            
            #if not all([len(m)==2 and all([isinstance(m_, numbers.Integral) and m_ >= 0 for m_ in m]) for m in dest_frame_mapping]):
                #raise TypeError("dest_frame_mapping must contain tuple elements, with two integers >= 0")
            
            #if not all([m[0] in receiver_frames] for m in dest_frame_mapping):
                #raise ValueError("dest_frame_mapping maps from frame indices NOT found in self's frame-state associations")
            
            #ret.remapFrameStateAssociations(dest_frame_mapping)
            
        #if not isinstance(src_frame_mapping, (tuple, list, NoneType)):
            #raise TypeError("src_frame_mapping expected to be a sequence or None; got %s instead" % type((src_frame_mapping).__name__))
        
        #if src_frame_mapping is not None:
            #if not all([isinstance(m, (tuple, list)) for m in src_frame_mapping]):
                #raise TypeError("src_frame_mapping must contain tuple elements")
            
            #if not all([len(m)==2 and all([isinstance(m_, numbers.Integral) and m_ >= 0 for m_ in m]) for m in src_frame_mapping]):
                #raise TypeError("src_frame_mapping must contain tuple elements, with two integers >= 0")
            
            #if not all([m[0] in src_frames for m in src_frame_mapping]):
                #raise ValueError("src_frame_mapping maps from frame indices NOT found in other's frame-state associations")
            
            #other.remapFrameStateAssociations(src_frame_mapping)
            
        #if any([f in ret.frameIndices for f in other.frameIndices]):
            #raise RuntimeError("Tthere are clashes between frame indices in both objects: cannot associate the a frame to two states")
        
    def appendStates(self, other):
        """Joins the state descriptors of the "other" PlanarGraphics object to self.
        
        The "other" is copied internally, the frame indices in its states are 
        incremented by 1 + max frame in this object, then its states are appended
        to this object's state list. The other's states will appear as if linked
        to frames AFTER this object's frame indices.
        
        The joining of the states can be customized (e.g. frame index links can
        interleaved) by first calling remapFrameStateAssociations() on each object
        individually, before joining.
        
        Parameters:
        ==========
        other: PlanarGraphics object
        
        Returns:
        ========
         A new PlanarGraphics. This object stays unchanged.
        
        WARNING: the GUI frontends will be orphaned after casting to a Path object.
        """
        # NOTE: 2019-03-21 14:27:26
        # either self, or other, or both, may have a single state, and that state 
        # may have z_frame None
        
        ret = self.copy()
        
        if isinstance(ret, Cursor):
            if not isinstance(other, Cursor):
                raise TypeError("A Cursor can only join states with another Cursor; got %s instead" % type(other).__name__)
            
            if other.type != ret.type:
                raise ValueError("%s cannot join states with another cursor type (%s)" % (ret.type, other.type))
            
        else:
            if isinstance(other, Cursor):
                raise TypeError("%s object cannot join states with a Cursor" % type(self).__name__)
                
            if isinstance(ret, Path):
                if isinstance(other, Cursor):
                    raise TypeError("%s object cannot join states with a Cursor" % type(self).__name__)
                
                elif not isinstance(other, Path):
                    other = Path(other)
                
            else:
                if isinstance(other, Path):
                    ret = Path(ret)
                
        if any([isinstance(o, Path) for o in (ret, other)]):
            # NOTE: for Path this is not implemented
            #for o in ret:
                #pass
            
            
            return ret
        # NOTE: everything from here on works with non-Path PlanarGraphics
        
        if len(ret._states_) == 1 and ret._states_[0].z_frame is None:
            ret._states_[0].z_frame = 0
            
        #do the same for the other
        if len(other.states) == 1 and other.states[0].z_frame is None:
            other.framestates[0].z_frame = 1
        
        receiver_states = sorted(ret._states_, key = lambda x: x.z_frame)
        
        receiver_frames = [s.z_frame for s in receiver_states]
        
        past_the_post = max(receiver_frames) + 1
        
        for state in other.states:
            state.z_frame += past_the_post
        
        # NOTE: ret._currentstate_ stays the same
        
        ret._states_ += other.states
        
        return ret
            
        #elif isinstance(ret, PlanarGraphics):
            #if isinstance(other, Cursor):
                #raise TypeError("This %s object cannot join states with a Cursor object" % type(self).__name__)
            
            #if isinstance(ret, Path): # self is a Path, other is not
                #if not isinstance(other, Path):
                    #other = Path(other)
                    
                #ret.appendStates(other) # Path overrides this method
                    
            #elif isinstance(other, Path):
                #if not isinstance(ret, Path):
                    #ret = Path(ret)
                    
                #ret.appendStates(other) # Path overrides this method
            
            #elif ret.type == other.type:
                #ret._states_ += other.states
                
            #else: # generic case: convert to Path
                #ret = Path(ret)
                #other = Path(other)
                #ret.appendStates(other)
        
        #return ret
        
    @property
    def maxFrameIndex(self):
        """The largest frame index or None (for frameless state objects)
        """
        if len(self._states_):
            if len(self._states_) == 1:
                return self._states_[0].z_frame
            
            else:
                return max([s.z_frame for s in self._states_])
    
    def addState(self, state):
        """ Adds (inserts or appends) a state.
        
        Parameters:
        ===========
        
        state: datatypes.DataBag with members that must conform to the particular 
            PlanarGraphics subclass.
            
            In addition, it must have an attribute called "z_frame" with the value
            being an int or None. This attribute indicates to which data frame this
            state applies.
            
        Returns:
        ========
        
        The (possibly modifed) state that has been added (see the NOTE below).
            
        NOTE: The frame index to which the new state is associated may change 
                to a different value, depending on what the current states are,
                and on the value of its z_frame attribute. 
                
                When this happens, a copy of the "state" parameter will be appended
                so that its original is unchanged.
                
        This function should typically be invoked whenever a new frame is added
        to the data that associates this PlanarGraphics object.
        
        What this function does:
        ========================
        Below, a "frame" means a data slice along its "Z axis". 
        
        PlanarGraphics object encapsulate 2D shapes, and are designed to be used
        with data that can be interpreted as "image" or "volume", or with data
        that composes image or volume arrays (e.g. ScanData).
        
        A PlanarGraphics object is described by at least one "state": a collection
        of numeric parameters that define the shape fo the PlanarGraphics object.
        
        The "state" can be "linked" to a particular data "frame":
        
        a) A single "frameless" state defines the PlanarGraphics object in all
            available data frames
        
        b) A "frame-linked" state defines the PlanarGraphics for a specific data 
        frame.
        
        The data frame is indicated by its integral, 0-based index in the 
        collection of frames (e.g. the index of the data slice along the "Z" axis).
        
        A PlanarGraphics object can contain several frame-linked states, each 
        linked to a distinct data "frame", but only ONE frameless state.
        
        When a state is added to a PlanarGraphics:
            * if the PlanarGraphics has a frameless state:
                * if the new state is also frameless, it will REPLACE the existing 
                    frameless state;
                    
                * if the new state is frame-linked, the existing frameless state 
                    will be associated with a frame index virtually preceding that
                    of the added state; 
                    
                    e.g., if state.z_frame == 0 the old frameless state is linked
                    to frame index 0 and state.z_frame is set to 1 (but see NOTE)
                    
            * if the PlanarGraphics has a single frame-linked state(s):
                * if the new state is frameless, assign its z_frame attribute 
                    to the next larger virtual frame index then append it (see NOTE)
                    
                * if the new state is frame-linked, then INSERT current state so
                    that its z_frame will "fall before" any other state frames
                    larger that its frame (and adjust the z_frame values for those

        The new state is stored by reference, except when its own z_frame value 
        needs to be changed (see NOTE, above). To always store a copy, pass a
        a copy of the source state to this function.
        
        In a nutshell, if both this object only state and the new state are frameless,
        the new state will replace the old state; otherwise the new state, or a copy 
        of it, will be appended and the frame indices readjusted so that they point
        to new unique frame indices.
        
        
        """
        # NOTE: override this in Path 
        
        import bisect
        import core.datatypes as dt
        
        if not isinstance(state, DataBag):
            raise TypeError("state expected to be a datatypes.DataBag; got %s instead" % type(state).__name__)
        
        if not self._check_state_(state):                                       # make sure state complies with this planar type
            raise TypeError("state %s does not contain the required descriptors %s" % (state, self._planar_descriptors_))
        
        if not hasattr(state, "z_frame"):                                       # make sure state is conformant
            raise AttributeError("state is expected to have a z_frame attribute")
        
        # just in case self has NO states (shouldn't happen, though...)
        if len(self._states_) == 0:
            self._states_.append(state)
        
        elif len(self._states_) == 1:                                         # self has a single state
            if self._states_[0].z_frame is None:                              #   self has a frameless state
                if state.z_frame is None:                                       #   if new state is frameless then replace existing frameless state
                    self._states_[:] = [state]                                #   --> replace the current frameless state
                    self._currentstate_ = self._states_[0]                  #   --> update current state so that the old one is not left dangling
                    
                else:                                                           #   new frame-linked state added but existing state is frameless
                    self._currentstate_ = self._states_[0]                  #       make sure current state references the exising state; 
                                                                                #           changes to z_frame will always be reflected in current state,
                                                                                #           because it is a reference to one of the elements in self._states_
                    
                    if state.z_frame > 0:                                       # new state always gets the next frame, in this function
                        self._states_[0].z_frame = state.z_frame - 1
                        
                    else:
                        self._states_[0].z_frame = 0
                        state = state.copy()                                    # don't change the "state" parameter, make a copy of it
                        state.z_frame = 1
                    
                    self._states_.append(state)
                    
            else:                                                               # self has a single frame-linked frame =>

                if state.s_frame is None:                                       # new state is frameless => link this to the next largest frame then append
                    state = state.copy()                                        # don't change the "state" parameter, make a copy of it
                    state.z_frame  = self._states_[0].z_frame + 1             # leave current state as it is (it should be a ref to this single frame-linked state)
                    self._states_.append(state)
                    
                else:                                                           # new state is frame-linked and it may be linked ot the state of the current frame!
                    currentframe = self._currentstate_.z_frame                # in the following manipulations current state might also get its z_frame changed

                    frame_sorted_states = sorted(self._states_, 
                                                 key = lambda x: x.z_frame)
                    
                    state_frames = [s.z_frame for s in frame_sorted_states]     # same order as frame_sorted_states (i.e. ascending)
                    
                    insert_index = bisect.bisect_left(state_frames,
                                                     state.z_frame)             # find what frame index the new state should get
                    
                    for s in frame_sorted_states[insert_index:]:                # increment the z_frame for states in frame_sorted_states[insert_index:]
                        s.z_frame += 1                                          # i.e, with z_frame values that woudl be beyond the new frame of the inserted state
                        
                    self._states_.append(state)                               # append the new state
                    
                    self._currentstate_ = [s for s in self._states_ \
                                             if s.z_frame == currentframe][0]   # set current state a reference to the state linked to the cached current frame
                
        else:                                                                   # self has several (at least one) frame-linked states
            if state.z_frame is None:                                           # new state is frameless => assign next available frame then append it
                state = state.copy()                                            # don't change the "state" parameter, make a copy of it
                state.z_frame = max(state_frames) + 1                           # current state won't change here
                self._states_.append(state)
                
            else:                                                               # new state is frame-linked; its frame may point to the frame of the current state
                currentframe = self._currentstate_.z_frame                    # so cache that here
                
                frame_sorted_states = sorted(self._states_, 
                                            key = lambda x: x.z_frame)
                
                state_frames = [s.z_frame for s in frame_sorted_states]         # same order as frame_sorted_states
                insert_index = bisect.bisect_left(state_frames, state.z_frame)  # index into frame_sorted_states where the new state should go given its z_frame
                                                                                # 
                for s in frame_sorted_states[insert_index:]:                    # increment the states from frame_sorted_states[insert_index:] by 1
                    s.z_frame += 1
                    
                self._states_.append(state)                                   # append the new state
                
                self._currentstate_ = [s for s in self._states_ \
                                         if s.z_frame == currentframe]          # set current state a reference to the state linked to the cached current frame
                
        return state
    
    def updateLinkedObjects(self):
        """Must be called asynchronously.
        
        To avoid infinite recursion, do not calling this function from __setattr__()
        """
        #print("%s to update its linked objects" % self.name)
        
        if len(self._linked_objects_):
            for obj, mapping in self._linked_objects_.items():
                #print( "\t updating %s (%s)" % (obj.name, obj.type))
                obj.name = self.name
                obj.frameIndices = self.frameIndices
                    
                obj.currentFrame = self.currentFrame
                    
                if self.hasStateForFrame(self.currentFrame):
                    mapping[0](*mapping[1], **mapping[2])
                    
                obj.updateFrontends()
        
    @safeWrapper
    def updateFrontends(self):
        """To be called after manual changes to this objects' descriptors.
        
        To avoid infinite recursion, do not call this function from __setattr__()
        
        The front ends are GraphicsObject objects that represent this PlanarGraphics
        object in a QGraphicsScene -- in other words, its "visible" counterpart.
        
        """
        #print("updateFrontends START: ", type(self), self.type, self.name)
        #traceback.print_stack()
        
        #if len(self._frontends_):
            #print("PlanarGraphics.updateFrontends() backend: ", self.name)
            
        #print("PlanarGraphics.updateFrontends for %s, frontends:" % self.name, self._frontends_)
        
        #sigBlock = [QtCore.QSignalBlocker(f) for f in self._frontends_]
        
        #print("%s to update its frontends" % self.name)
        
        for f in self._frontends_:
            if f:
                #print( "\t updating frontend %s (%s)" % (f.name, f.type))
                #print("frontend", f)
                sigBlock = QtCore.QSignalBlocker(f)
                #print("PlanarGraphics.updateFrontends() frontend current name: ", f.name)
                if f.name != self.name: # check to avoid recurrence
                    old_name = f.name
                    f.name = self.name
                    #print("PlanarGraphics.updateFrontends() frontend new name: ", f.name)
                    #print("PlanarGraphics.updateFrontends() frontend parentWidget: ", f.parentwidget)
                    viewer = None
                    
                    if type(f.parentwidget).__name__ == "ImageViewer":
                        viewer = f.parentwidget.viewerWidget
                    elif type(f.parentwidget).__name__ == "GraphicsImageViewerWidget":
                        viewer = f.parentwidget
                        
                    if viewer is not None and hasattr(viewer, "_graphicsObjects"):
                        objDict = viewer._graphicsObjects[f.objectType]
                        #print(objDict)
                        old_f = objDict.pop(old_name, None)
                        objDict[self.name] = f
                        #objDict[self.name] = f
                    
                f.currentFrame = self.currentFrame
                
                x = self.x
                y = self.y
                
                #print("updateFrontends: x, y: %s, %s" % (self.x, self.y))
                
                if x is not None and y is not None:
                    super(GraphicsObject, f).setPos(x, y)

                f.setVisible(self.hasStateForFrame(f._currentframe_))
                
                f.redraw()
                
    def updateFrontend(self, f):
        """To be called after manual changes to this objects' descriptors.
        
        To avoid infinite recursion, do not calling this function from __setattr__()
        
        """
        #self.__locked__ = True
        
        if len(self._frontends_) and f in self._frontends_:
            #sigBlock = QtCore.QSignalBlocker(f)
            
            f._currentframe_ = self.currentFrame
            
            if len(self.frameIndices):
                f.setVisible(f._currentframe_ in self.frameIndices)
                
            else:
                f.setVisible(True)
                    
            f.setPos(self.x, self.y) # also calls __drawObject__() and update()
            
    def removeState(self, stateOrFrame):
        """Removes a state associated with a frame index or indices specified in "stateOrFrame".
        
        stateOrFrame must contain valid frame indices.
        
        Function does nothing if the PlanarGraphics object has a common state.
        
        Parameters:
        ==========
        stateOrFrame:   a DataBag (state), an in, OR
                        a sequence (tuple, list) of states or int (no mixed types!)
        
        """
        import core.datatypes as dt
        
        sorted_states = sorted(self._states_, key = lambda x:x.z_frame)
        
        sorted_fr_ndx = [s.z_frame for s in sorted_states]
        
        if isinstance(stateOrFrame, int):
            if stateOrFrame in sorted_fr_ndx:
                state = sorted_states[sorted_fr_ndx.index(stateOrFrame)]
                self._states_.remove(state)
                
            else:
                raise ValueError("No state found for frame %d" % stateOrFrame)
            
        elif isinstance(stateOrFrame, DataBag):
            if state in self._states_:
                self._states_.remove(state)
                
            else:
                raise ValueError("state %s not found" % state)
            
        elif isinstance(stateOrFrame, (tuple, list)) and len(stateOrFrame) > 0:
            if all([isinstance(v, int) for v in stateOrFrame]):
                valid_values = [v for v in stateOrFrame if v in sorted_fr_ndx]
                
                if len(valid_values):
                    states_to_remove = [[s for s in self._states_ if s.z_frame == v][0] for v in valid_values]
                
                    for state in states_to_remove:
                        self._states_.remove(state)
                        
                else:
                    raise ValueError("No states found for frames in %s" % stateOrFrame)
                
            elif all([isinstance(v, DataBag) for v in stateOrFrame]):
                for states in stateOrFrame:
                    if state in self._states_:
                        self._states_.remove(state)
                        
                    else:
                        raise ValueError("state %s not found" % state)
            
        else:
            raise TypeError("expecting an int, a DataBag, or a sequence of int or DataBag (no mixed types); got %s instead" % stateOrFrame)
        
    def setParameter(self, name, value, frame=None):
        """Sets the value of a named planar graphics descriptor.
        
        Parameters:
        ==========
        name: str = name of the planar descriptor; must be found among self._planar_descriptors_
        
        value: the new value of the named descriptor.
        
        frame: int or None (default is None)
            when specified, it will affect only the state associated with this 
            frame
        
        The name of the descriptor must be one present in self._planar_descriptors_
        and found in any of the decscriptor state objects (either the common state
        DataBag object, or in the frame-state associations dictionary).
        
        For Path PlanarGraphics objects, the function does nothing.
        To set the value of a named planar descriptor for a specific Path element,
        call this function on that specifc element,e.g.::
        
            p[x].setParameter(name, value, frame)
            
        where 'p' is a Path object and 'x' is the index of the Path element.
            
        """
        if name not in self._planar_descriptors_:
            raise KeyError("parameter %s does not exist" % name)
        
        if frame is None:
            setattr(self._currentstate_, name, value)
                
        else:
            if frame not in self.frameIndices:
                raise KeyError("frame %s does not exist" % frame)
            
            state = self.getState(frame)
            
            setattr(state, name, value)
            
    def hasStateForFrame(self, frame):
        """Returns True if there is a state linked ot this frame.
        
        Parameters:
        ===========
        
        frame : int, or None; the frame index for which the associated state is 
            sought
            
        Returns:
        =======
        
        True when frame is None, or:
             when there is a single frame-less state (regardless of "frame"), or:
             when frame is an int and there is a state wher z_frame == frame
             
             
        
        """
        # for a single frameless state, THIS is the state for any frame
        if frame is None:
            return True # although not technically true, this allows to get the fallback state
        
        elif isinstance(frame, int):
            if len(self._states_) == 1 and self._states_[0].z_frame is None:
                return True
            
            else:
                return frame in [s.z_frame for s in self._states_]
            
        else:
            raise TypeError("frame expected to be an int or None; got %s instead" % type(frame).__name__)
            
    def qGraphicsItem(self, pointSize=1, frame=None):
        """Generates a concrete QGraphicsItem instance using the 
        state descriptors for the current frame.
        
        This is to be used as shaped graphics item by GraphicsObject instances.
        
        Returns None for Cursor objects.
        
        Named parameters:
        =================
        pointSize:  float, default is 1; for Point objects the size of the 
                        circle representing a point.
                        
        frame: int, default is None; the index of the frame for which the 
            descriptor state is sought.
        
            When None, the state for the currentFrame (or the common state) 
                is used.
        
            Otherwise, the frame-associated state will be used.
                If the frame index has no state associated with it, the function
                issuies a warning and returns None
        
        NOTE:
        
        Path objects are used to describe the following plane graphics :
        
        * line: 
            prerequisites: len(self) == 2 and self is [Move, Line] 
        
            generates a QGraphicsLineItem
        
        * polyline: 
            prerequisites: len(self) is arbitrary and self is [Move, Line, Line, ..., Line]
                i.e. it has only Move and Line elements
                
                CAUTION: each Move element starts a new "subpath"
                
            generates a QGraphicsPathItem
                
        * polygon: 
            prerequisites: as for polyline, except that self.closed == True
            
            generates a QGraphicsPolygonItem
        
        * path: 
            prerequisites: len(self) is arbitrary and has arbitrary graphical 
                            element types EXCEPT for the first element (which is
                            always a Move object)
                            
            generates a QGraphicsPathItem
            
        WARNING: Path objects do not offer direct access to the planar descriptors
        as primitive PlanarGraphics do.
        
        For a primitive PlanarGraphics p, p.x, p.y, etc... accesses the descriptors 
        directly.
        
        For a Path p, p.x and p.y accesses the position of the entire Path (i.e.
        the minimum value of x and y, respectively, for all its elements).
        
        
            
        Path objects inherit from Python lists, and their elements can be ONLY
        primitive planar graphics as described below. 
            
        All other PlanarGraphics objects encapsulate primitives that can be 
        elements of a Path:
        
        Point, Start, Move: a point
        
            generate a QGraphicsEllipseItem (circle with diameter = pointSize)
            
        Line: a stand-alone line with origin implied at (0,0) in the coordinate 
            frame of a scene (an image)
            
            generates a QGraphicsLineItem
            
        Cubic, Quad
        
            generate a QGraphicsPathItem
        
        Arc, ArcMove: an ellipse arc (TODO)
        
            generate a QGraphicsPathItem
        
        Ellipse: an ellipse
        
            generates a QGraphicsEllipseItem
        
        Rect: a rectangle
        
            generates a QGraphicsRectItem
        
        """
        # NOTE: must be overridden in the concrete :subclass:
        
        if frame is None:
            state = self.currentState
            
        else:
            if not isinstance(frame, int):
                raise TypeError("%s.qGraphicsItem: frame expected to be an int or None; got %s instead" % (self.__class__.__name__, frame))
            
            state = self.getState(frame)
            
        if state is None or len(state) == 0:
            warnings.warn("%s.qGraphicsItem: undefined state" % self.__class__.__name__, stacklevel=2)
            return QtWidgets.QGraphicsPathItem()
        
        return QtWidgets.QGraphicsPathItem(self(path=None, frame=frame, closed=self.closed)) # by default, the most generic case
        
    def getObjectForFrame(self, frame):
        """Returns a COPY of this object using the state linked to the specified frame.
        
        Parameters:
        ===========
        
        frame: int, or None (for the frameless state)
        
        """
        if not isinstance(frame, (int, type(None))):
            raise TypeError("frame expected to be an int or None; got %s instead" % type(frame).__name__)
        
        ret = None
        
        state = self.getState(frame)
        
        ret = self.__class__(state, name="copy of %s for frame %s" % (self.name, frame))
        
        return ret
    
    def getState(self, frame=None):
        """Returns the state linked to the specified frame, or None.
        
        If frame is not linked to a state, returns None.
        
        If the object has a frame-less state, returns that state.
        
        To get access to the frame state of individual element of a Path, call:
        
            'p[x].getState(frame)'
            
        where 'p' is a Path object, 'x' is the index of the element in the 
        Path object, and p[x] is not a Path itself.
        
        Parameters:
        ===========
        
        frame : int, or None; the frame index for which the associated state is 
            sought.
            
            When frame is an int: 
                if self has one state:
                    returns this state if the state is frame-less OR 
                                        it is linked to the same frame index as "frame"
                    otherwise returns None
                    
                if self has many states (all are frame-linked):
                    returns the state linked to the specified frame if found, or None
                    
                    
            When frame is None:
                if self has one state: return that state
                
                if self has many states, returns the states linked with the current
                    frame
                    
        NOTE: is this PlanarGraphics is frameless it is easier/faster to get
            its state as self.states[0]
        
        Returns:
        =======
        
        a datatypes.DataBag object (the state for the specified frame), containing
            the planar descriptors specific for the PlanarGraphics type or None
            if there are several frame-linked states and the specified frame is 
            not linked to any of these.
        
        """
        if isinstance(frame, int):
            if len(self._states_) == 1:
                if self._states_[0].z_frame is None or self._states_[0].z_frame == frame:
                    return self._states_[0]
                
                else:
                    return
                
            elif len(self._states_) > 1:
                states = [s for s in self._states_ if s.z_frame == frame]
                
                if len(states):
                    return states[0]
                
                else:
                    return
                
            else:
                return
                
        elif frame is None:
            if len(self._states_) == 1:
                return self._states_[0]
            
            elif len(self._states_) > 1:
                states = [s for s in self._states_ if s.z_frame == self._currentframe_]
                
                if len(states):
                    return states[0]

                else:
                    return
                
            else:
                return
                    
    def setState(self, state):
        """Sets state non-Path PlanarGraphics objects.
        
        For Path objects, this function does nothing. To alter frame states for 
        an indivdual Path element, call setState on that specific Path element
        (Pathc objects implement python list API).
        
            'p[k].setState(value)'
            
        where 'p' is a Path object and 'k' is the index of the element in the 
        Path object.
        
        Parameters:
        =====================
        state: datatypes.DataBag object. Its member names must conform with the
            parametric descriptors of the planar graphics object.
            
            If state is a reference to an existing state, does nothing.
            
            If the state.z_frame is None it will REPLACE ALL states and thus
            render the PlanarGraphics object "frameless".
            
            Otherwise:
                If the PlanarGraphics has a single frameless state, that state
                will be replaced with this state
                
                Else, if the PlanarGraphics has frame-linked states, the new state will
                replace any existing state linked to the same frame index as 
                state.z_frame. Raises an error if such a state is not found.
            
            The state is stored by reference; if this is not what is intended,
            pass a copy of the original state to the function call.
            
        Returns:
        =======
        
        The state.
            
        """
        if state in self._states_:
            return state                                                        # nothing to do
        
        if not self._check_state_(state):                                       # make sure state complies with this planar type
            raise TypeError("state %s does not contain the required descriptors %s" % (state, self._planar_descriptors_))
        
        if not hasattr(state, "z_frame"):                                       # make sure state is conformant
            raise AttributeError("state is expected to have a z_frame attribute")
        
        if state.s_frame is None:                                               # wipe-out all states, replace with frameless state
            self._states_.clear()
            self._states_.append(state)
            self._currentstate_ = self._states_[0]
            
            return state
        
        if len(self._states_) == 1:                                           # a single state
            if self._states_[0].z_frame is not None:                          # block replacement by a state with different frame
                if state.z_frame != self._states_[0].z_frame:
                    raise KeyError("There is no state associated with frame %d; call addState instead" % state.z_frame)
                
            self._states_.clear()
            self._states_.append(state)
            
            self._currentstate_ = self._states_[0]
            
            return state
                
                                                                                # is there already an internal state for the same frame as the argument?
        sorted_frame_states = sorted(self._states_,
                                     key = lambda x: x.z_frame)
        
        sorted_frame_indices = [s.z_frame for s in sorted_frame_states]
        
        if state.z_frame in sorted_frame_indices:
            state_to_replace = sorted_frame_states[sorted_frame_indices.index(state.z_frame)]
            
            self._states_.remove(state_to_replace)
            
            self._states_.append(state)
            
            if self._currentstate_ == state_to_replace:
                self._currentstate_ = state
                
        else:
            raise KeyError("There is no state associated with frame %d; call addState instead" % state.z_frame)
        
        return state
    
    @staticmethod
    def getCurveLength(obj, prev=None):
        """Static version of PlanarGraphics.curveLength()
        Useful to apply it to a state, or a sequence of states (instead of PlanarGraphics)
        
        Parameters:
        ==========
        obj: 
            Either a datatypes.DataBag: the state of an elementary PlanarGraphics or a sequence
            of states of a Path.
            
            The function supports only states for Move, Line, Cubic, and Quad
            
            Or: a sequence (typle, list) of state DataBag (such as those from a Path)
            
            In either case, these are typically obtained by calling PlanarGraphics.getState()
            or Path.getState().
        
        prev: None (default) or a datatypes.DataBag: state of an elementary PlanarGraphics
            e.g., as returned by PlanarGraphics.getState()
            
        NOTE: the function cannot distinguish between states belonging to a Move and
        those belonging to a Line (they have the same planar descriptors). As a workaround
        call this function by passing the same state for obj and prev.
        
        WARNING: For a sequence of states, the function assumes the first state belongs
            to a Move PlanarGraphics.
        
        """
        from scipy import interpolate, spatial
        import core.datatypes as dt
        
        if prev is None:
            x0 = y0 = 0.
            
        elif isinstance(prev, DataBag):
            if not any([p in prev for p in ("x", "y", "cx", "cy", "c1x", "c1y", "c2x", "c2y", "z_frame")]):
                raise TypeError("Incompatible data for prev")
            
            x0 = prev.x
            y0 = prev.y
            
        else:
            raise TypeError("prev expected to be a datatypes.DataBag compatible with a PlanarGraphics, or None; got %s instead" % type(prev).__name__)
        
        
        if isinstance(obj, DataBag):
            if not any([p in obj for p in ("x", "y", "cx", "cy", "c1x", "c1y", "c2x", "c2y", "z_frame")]):
                raise TypeError("Incompatible data for obj")
            
            x1 = obj.x
            y1 = obj.y
            
            if all([p in obj for p in ("cx","cy")]): # state of a Quad
                self_xy = np.array([x1, y1])
                prev_xy = np.array([x0, y0])
                
                dx_dy = self_xy - prev_xy

                t = np.zeros((6,))
                t[3:] = 1.
                
                c = np.array([[x0, y0], [obj.cx, obj.cy], [x1, y1]])
                
                spline = interpolate.BSpline(t, c, 2, extrapolate=True)
                
                definite_integral = spline.integrate(0,1)
                defintegral_xy = np.array(definite_integral)
                rectified_xy = defintegral_xy + dx_dy
                
                return spatial.distance.euclidean(prev_xy, rectified_xy)
            

            elif all([p in obj for p in ("c1x", "c1y", "c2x", "c2y")]): # state of a Cubic
                self_xy = np.array([x1, y1])
                prev_xy = np.array([x0, y0])
                
                dx_dy = self_xy - prev_xy

                t = np.zeros((8,))
                t[4:] = 1.
                
                c = np.array([[x0, y0], [obj.c1x, obj.c1y], [obj.c2x, obj.c2y], [x1, y1]])
                
                spline = interpolate.BSpline(t, c, 3, extrapolate=True)

                definite_integral = spline.integrate(0,1)
                defintegral_xy = np.array(definite_integral)
                rectified_xy = defintegral_xy + dx_dy
                
                return spatial.distance.euclidean(prev_xy, rectified_xy)
            
            else: # state of a Move or Line
                return spatial.distance.euclidean([x1, y1], [x0, y0])
                
        elif isinstance(obj, (tuple, list)): # sequence of states from a Path
            if not all([isinstance(o, DataBag) for o in obj]):
                raise TypeError("The sequence must contain datatypes.DataBag objects")
            
            if any([not any([p in o for p in ("x", "y", "cx", "cy", "c1x", "c1y", "c2x", "c2y", "z_frame")]) for o in obj]):
                raise TypeError("The sequence contains incompatible datatypes.DataBag objects")
                
            element_curve_lengths = [curveLength(obj[0], prev=obj[0])]
            
            element_curve_lengths += [curveLength(o, obj[k-1]) for k, o in enumerate(obj)]
            
            return np.sum(element_curve_lengths), element_curve_lengths
        
        else:
            return 0
                
    def curveLength(self, prev=None):
        """Calculates the length of the curve represented by this PlanarGraphics
        TODO: implement for Rect, Ellipse, and Arc but with winding rule !
        
        Parameters:
        ==========
        prev: a PlanarGraphics or None (default): the PlanarGraphics point
            relative to which the curve length is calculated.
            
            Ignored for Path PlanarGraphics, but mandatory for the other supported
            PlanarGraphics subclasses (currently, Move, Line, Cubic, Quad).
            
            When None, the curveLength will be calculated relative to a 
                Move(0., 0.) instead.
        
        Returns:
        =======
        For Move: 0
        
        For Line: the Euclidean distance between this element's (x,y) coordinates
                and those of the previous element in "prev"
                    
        For Cubic, Quad: scalar float:  the length of the rectified form of the 
            curve i.e., a straight line segment with the same length as the 
            definite path integral of the curve from its origin (prev) to the end
            point.
            
        For Path:   a tuple with:
                        a float scalar: the sum of its element's curveLength()
                        a sequence with the individual elements' curveLength(),
                            in the order they are stored within the Path.
        
        NOTE 1: Except for Path, curve PlanarGraphics are defined by their 
        end point and control point(s) coordinates, if any.
        
        NOTE 2: Move objects occurring on a Path anywhere beyond its beginning
            signal a new subpath (with the last point on previous subpath not 
            connected to this subpath).
            
            For Move objects that begin a subpath one can supply the last object 
            of the previous subpath as "prev", to include the length of the "jump"
            between subpaths in the result.
            
    
        """
        from scipy import interpolate, spatial
        
        if isinstance(self, Move):
            if prev is None:
                return 0 # Move has 0 length
            
            else:
                # for Move that begins a subpath
                return spatial.distance.euclidean([self.x, self.y], [prev.x, prev.y])
        
        elif isinstance(self, Path):
            if all([isinstance(e, (Move, Line, Cubic, Quad)) for e in self]):
                # get a copy for the current frame
                path = self.asPath(self.currentFrame)
                
                element_curve_lengths = [path[0].curveLength()]
                
                element_curve_lengths += [p.curveLength(path[k-1]) for k, p in enumerate(path) if k > 0]
                
                return np.sum(element_curve_lengths), element_curve_lengths
                
            else:
                raise NotImplementedError("Function accepts Path containing only Move, Line, Cubic, and Quad elements")
            
        else:
            if not isinstance(prev, PlanarGraphics):
                raise TypeError("prev expected to be a PlanarGraphics for this element type (%s)" % self.type)
            
            if prev is None:
                prev = Move(0., 0.)
        
            if isinstance(self, Line):
                return spatial.distance.euclidean([self.x, self.y], [prev.x, prev.y])
            
            elif isinstance(self, Cubic):
                # parametric spline: (x,y) = f(u)
                self_xy = np.array([self.x, self.y])
                prev_xy = np.array([prev.x, prev.y])
                
                dx_dy = self_xy - prev_xy                      # prepare to "shift" the rectified spline
                                                                # so that it starts at the previous point
                
                t = np.zeros((8,))
                t[4:] = 1.
                
                c = np.array([[prev.x, prev.y], [self.c1x, self.c1y], [self.c2x, self.c2y], [self.x, self.y]])
                
                spline = interpolate.BSpline(t, c, 3, extrapolate=True)
                
                definite_integral = spline.integrate(0,1)
                
                #xx = np.array([prev.x, self.c1x, self.c2x, self.x])
                #yy = np.array([prev.y, self.c1y, self.c2y, self.y])
                
                #tck = [t, [xx, yy], 3]
                
                ### NOTE: 2019-03-29 15:17:05
                ### could also use:
                ## spline = interpolate.BSpline(tck[0], np.array(tck[1]).T, tck[2], extrapolate=True)
                ### then:
                ## definite_integral = spline.integrate(0,1, extrapolate=True)
                
                #definite_integral = interpolate.splint(0,1,tck) # spline as a straight line, with 0 origin:
                                                                 # end point x,y coords given origin at 0
                
                defintegral_xy = np.array(definite_integral)    # coordinates of the end point of a
                                                                # straight line having length equal to
                                                                # the definite integral in the 2D plane
                                                                # and origin at 0
                
                rectified_xy = defintegral_xy + dx_dy           # end point of spline as a straight line
                                                                # with origin at prev point
                
                return spatial.distance.euclidean(prev_xy, rectified_xy)
                
            elif isinstance(self, Quad):
                self_xy = np.array([self.x, self.y])
                prev_xy = np.array([prev.x, prev.y])

                dx_dy = self_xy - prev_xy                      # prepare to "shift" the rectified spline
                                                                # so that it starts at the previous point
                
                t = np.zeros((6,))
                t[3:] = 1.
                
                c = np.array([[prev.x, prev.y], [self.cx, self.cy], [self.x, self.y]])
                
                spline = interpolate.BSpline(t, c, 2, extrapolate=True)
                
                definite_integral = spline.integrate(0,1)
                
                #xx = np.array([prev.x, self.c1x, self.c2x, self.x])
                #yy = np.array([prev.y, self.c1y, self.c2y, self.y])
                
                #tck = [t, [xx, yy], 2]
                
                # see NOTE: 2019-03-29 15:17:05 for alternative
                # also, see marginal comments after NOTE: 2019-03-29 15:17:05
                
                #definite_integral = interpolate.splint(0,1,tck)
                
                defintegral_xy = np.array(definite_integral)
                
                rectified_xy = defintegral_xy + dx_dy
                
                return spatial.distance.euclidean(prev_xy, rectified_xy)
            
            else:
                raise NotImplementedError("Function is not implemented for %s PlanarGraphics" % self.type)

    def linkToObject(self, other, mappingFcn, *args, **kwargs):#, inverseFcn=None, reciprocal=False):
        """ Dynamic link between two PlanarGraphics objects.
        
        mappingFcn  = function that realises a mapping from one object's planar 
                        descriptors to another object's planar descriptors and
                        with the following MANDATORY signature:

                        mappingFcn(src, dest, *args, **kwargs)
                        
                        where:
                        
                        src, dest are distinct PlanarGraphics object;
                        
                        src and dest will be bound respectively, to self and 
                        "other" such that a functools partial will be generated 
                        and stored internally
            
        parameters:
            other: PlanarGraphics objects (must be different from each-other)
            
            *args, **kwargs
            
        NOTE: this may remove the previous mapping to other, if
        other is in this dictionary's keys()
        
        """    
        import functools
        #import inspect
        
        if other == self:
            raise ValueError("Cannot link object to itself")
        
        partialFcn = functools.partial(mappingFcn, self, other)

        # NOTE: 2018-02-09 17:35:42
        # as of now, PlanarGraphics objects are ALL hashable, including Path objects
        # this relies on the default Python hash() function
        self._linked_objects_[other] = (partialFcn, args, kwargs)
        #self._linked_objects_[other.name] = (mappingFcn, args, kwargs)
        
    def linkFrames(self, value):
        """Associates planar descriptor state values to frame indices.
        
        A planar descriptor state (datatypes.DataBag) can be:
        a) "frameless" when its z_frame attribute is None
        
        b) frame-linked when its z_frame attribute points to a frame index
        
        
        Positional parameter:
        =====================
        value: int, sequence of int, a dict (int->int) or None
        
        If value is None, or an empty sequence or a sequence with None:
            the current state (i.e the state linked to the current frame) becomes
            frameless (i.e., z_frame is set to None), and all other frame-linked
            states are removed
            
        If the value is a non-empty sequence of ints, or a range object:
            1) if there are frames already linked to states, these wil be excluded 
                (to avoid duplicates)
                
            2) copies of the current state will be linked to the new frames (after
                excluding as in (1)) and appended
                
        NOTE: this function simply calls self.frameIndices.setter
        
        """
        self.frameIndices = value
            
    def unlinkFrames(self):
        """Makes the current planar descriptor state common to all available data frames.
        DEPRECATED
        Same thing can be achieved by calling self.linkFrames([]) or self.linkFrames(None)
        
        """
        state = self._currentstate_
        state.z_frame = None
        self._states_[:] = [state]
        
    def propagateFrameState(self, state, destframes):
        """Propagates planar descriptor "state" to all frames in destframes.
        
        States linked to frames in destframes will be replaced with copies of 
        "state".
        
        Parameters:
        ==========
        state: DataBag - a state present in this object's states list
        
        destframes: a sequence of int, or None: frame indices where state is to 
                    be propagated
        
            If None, or empty, "state" will become a single, frameless state (i.e.
                present in all available data frames for the object)
        
        """
        if state not in self._states_:
            raise ValueError ("State %s not found" % state)
        
        
        target_states = sorted([s for s in self._states_ if s != state], 
                                key = lambda x: x.z_frame)
        
        if len(target_states) == 0:
            return
        
        target_frame_indices = [s.z_frame for s in target_states]
        
        if isinstance(destframes, (tuple, list)):
            if len(destframes):
                if not all([isinstance(f, int) for f in destframes]):
                    raise TypeError("destframes must contain only int values")
                
                if any([f not in target_frame_indices for f in destframes]):
                    raise ValueError("destframes contains frames indices not found in this object")
                
                if len(set(destframes)) < len(destframes):
                    raise ValueError("destframes must not contain duplicate values")
                
                for f in destframes:
                    target_state = target_states[target_frame_indices.index(f)]
                    
                    self._states_.remove(target_state)
                    self._states_.append(state.copy())
                    
            else: # empty destframes
                # use this state as a single state to all frames
                state.z_frame = None
                self._states_[:] = [state]
                
        elif destframes is None:
            state.z_frame = None
            self._states_[:] = [state]
            
        else:
            raise TypeError("destframes expected to be a (possibly empty) sequence opfr frame idnices, or None; got %s instead" % type(destframes).__name__)
            
                
        if setcurrent:
            self._currentframe_ = srcframe
                    
    def remapFrameStateAssociations(self, newmap):
        """Remaps the frame state associations.
        
        Set frame indices using a dictionary of (int -> int) mapping, where
        
        key is the old frame index and value is the new frame index
        
        Parameters:
        ===========
        newmap: sequence of (old_frame_index, new_frame_index) tuples, or a dictionary {old_frame_index: new_frame_index}
        
        Raises KeyError if any old_frame_index value is invalid (i.e. when there are no states with such z_frame value)
 
        Example:
        
        obj.remapFrameStateAssociations([m for m in zip(obj.frameIndices, new_frame_indices)])
        
        WARNING: Does NOT remap the frame-state associations for the linked objects.
        
        """
        if isinstance(newmap, (tuple, list)) and all([isinstance(v, (tuple, list)) and len(v)==2 and all([isinstance(k, int) for k in v]) for v in newmap]):
            newmap = dict(newmap)
            
        if not isinstance(newmap, dict):
            raise TypeError("newmap expected to be a dict; got %s instead" % type(newmap).__name__)
        
        if len(newmap) == 0:
            return
        
        if len(newmap) > len(self._states_):
            raise ValueError("new frame map has more entries (%d) than there are states (%d)" % (len(newmap), len(self._states_)))
        
        target_states = [s for s in self._states_ if s.z_frame in newmap.keys()]
        
        # this will implicitly change z_frame for current state also, if in this list
        if len(target_states):
            for state in target_states:
                state.z_frame = newmap[state.z_frame] # this should also affect self._currentstate_ (which is a reference)
                
        else:
            raise KeyError("new frame map does not point to existing states")
                    
    @property
    def name(self):
        return self._ID_
    
    @name.setter
    def name(self, value):
        if isinstance(value, str):
            if len(value.strip()):
                if self._ID_ != value: # check to avoid recurrence
                    self._ID_ = value
                    self.updateLinkedObjects()
                    self.updateFrontends()
            
        else:
            raise TypeError("name must be a str; got %s instead" % value)
        
    @property
    def sortedFrameIndices(self):
        if len(self._states_) == 1:
            return [self._states_[0].z_frame] # z_frame may be None so cannot sort
        
        else:
            return sorted([s.z_frame for s in self._states_]) # this may be an empty list
        
    @property
    def frameIndices(self):
        """A list of frame indices where frame-state associations occur.
        
        For Path PlanarGraphics objects, all elements of the Path have either 
        the same frame-state associations, or all have a common state.
        
        When there are no hard frame-state associations, this property is an empty
        list.
        
        optional parameter:
        ===================
        value: a sequence (tuple, list) of int
        
        Will replace the frame indices in the current frame-state associations
        with a new set of frame indices.
        
        To remove all frame indices (implicitly setting up a common state across 
        all avaliable frames) pass an empty list. The common state will the the 
        one formerly assigned ot the current frame.
        
        A planar graphics descriptor state is a datatypes.DataBag with its members
        being the planar descriptors specific to the concrete subclass. The values 
        of the planar descriptors are either common to all possible frames of a 3D 
        data array where the PlanarGraphics object would be used, or specific to 
        particular frame indices, if the object has frame-state associations.
        
        A frame-state association is a dictionary that maps frame indices (int)
        as keys, to descriptor states (datatypes.DataBag) as values.
        
        """
        # NOTE: 2019-07-22 09:05:04
        # z_frame is None by default!
        if len(self._states_) == 1:
            return [self._states_[0].z_frame]
        
        return sorted([s.z_frame for s in self._states_]) # this may be an empty list
        
    @frameIndices.setter
    def frameIndices(self, values):
        """Re-maps the frame indices in existing states as indicated by "values".
        
        If there are NO frame-associated states (i.e. there is only one frame)
        the function does nothing.
        
        Raises an error if any of the following situation arises:
        
        1) "values" parameter indicates more frame indices than the number of
        currently defined states.
        
        2) the "new" frame indices in "values" result in duplication of z_frame
        among existing states
        
        Parameters:
        ===========
        values: One of:
                1)  tuple or list or range
                1.a) their iteration must generate int values
                1.b) or may be [None] (a sequence with a single None element)
                1.c) or may be empty
                    
                2) a dict with int keys mapped to int values (old -> new frame index)
                
                3) a single int
                
                4) None
                
                Cases 1.b, 1.c, and 4 effectively remove the frame links of this object's states
                    
                Case 1 can expand or reduce the number of frame-linked states
                
                Case 2 operates atomically on states with links to specific frames
                    does not remove states.
                
                Neither case remove state-frames!
                    
        dict mapping old_frame to new_frame (all numeric scalars)
        
            The keys (old frame indices) select which state will get a new values 
            for its z_frame parameter.
        
        """
        import bisect
        
        #### BEGIN  use linkFrames code and make linkFrames call this function, or an alias
        # when values is either None, an empty iterable, (tuple, list, range, dict)
        # or an iterable that contains None, then automatically unlink all states
        # and make the current state frameless (universal) then ditch the other 
        # states
        
        if isinstance(self, Path): # FIXME: this won't be reached because the method is overridden in Path
            for o in self._objects_:
                o.frameIndices(value)
                
            return
        
        if values is None \
            or (isinstance(values, (tuple, list, range, dict)) \
                and (len(values)==0 or None in values)):                        # remove any framelinks;
                                                                                # leave a single frameless state
                                                                                # remove the other states
            state = self._currentstate_
            state.z_frame = None
            self._states_[:] = [state]
                
        elif isinstance(values, (tuple, list, range)):                          # a list of frames was specified
            if not all([isinstance(f, int) for f in values]):                   # check for int types
                raise TypeError("new frame indices expected to be a sequence of int, or a dictionary with int keys; got %s instead" % values)

            if any([f < 0 for f in values]):                                    # check for valid values
                raise ValueError("new frame indices must be >= 0")
            
            if len(set(values)) < len(values):                                  # check for uniqueness
                raise ValueError("duplicate new frame indices are not allowed")
                
            if len(self._states_) == 1:                                       # here there is a single state
                if self._states_[0].z_frame is None:                          # which is frameless
                    new_states = list()
                    
                    for f in values:                                            # generate new states for the frames
                        state = self._states_[0].copy()
                        state.z_frame = f
                        new_states.append(state)
                        
                    self._states_[:] = new_states
                    self._currentstate_ = self._states_[0]
                    
                else:                                                           # which is frame-linked
                    state = self._states_[0]                                  # also, this is normally the 
                                                                                # self._currentstate_ so we 
                                                                                # leave it alone
                    if state.z_frame in values:                                  # values already contain state's frame index
                        new_frame_values = [f for f in values \
                                            if f != self.z_frame]               # we then replicate this state for ALL OTHER frames
                        
                        for f in new_frame_values:                              # loop does nothing if new_frame_values is empty 
                            s = state.copy()                                    # is empty (thus avoid duplication)
                            s.z_frame = f
                            self._states_.append(s)
                            
            else:                                                               # case with several states
                current_frame_indices = [s.z_frame for s in self._states_]
                
                # this will expand
                new_frame_values = [f for f in values \
                                    if f not in current_frame_indices]          # skip states linked already linked to frames in values
                                                                                # so for instance if values include
                                                                                # the current state's frame
                                                                                # this will be unchanged
                                                                                
                frame_indices_to_drop = [f for f in current_frame_indices \
                                         if f not in values]                    # frame links to drop
                
                new_current_frame_link = None                                   # see below
                states_to_drop = list()
                
                if len(frame_indices_to_drop):
                    states_to_drop = [s for s in self._states_ \
                                      if s.z_frame in frame_indices_to_drop]    # this MAY contain the current state
                
                    if self._currentstate_ in states_to_drop:                 # find out which framek-linked state
                                                                                # should become current
                        new_current_frame_ndx = bisect.bisect_left(new_frame_values, 
                                                                    self._currentstate_.z_frame)    
                        #print(new_frame_values)
                        if len(new_frame_values):
                            if new_current_frame_ndx >= len(new_frame_values):
                                new_current_frame_link = new_frame_values[-1]
                                
                            else:
                                new_current_frame_link = new_frame_values[new_current_frame_ndx]
                                

                    
                for f in new_frame_values:                                      # duplicate currentstate, update z_frame then append
                    s = self._currentstate_.copy()
                    s.z_frame = f
                    self._states_.append(s)
                    
                for state in states_to_drop:                                    # drop extra states 
                    self._states_.remove(state)
                    
                if new_current_frame_link is not None:
                    new_current_state = [s for s in self._states_ \
                                         if s.z_frame == new_current_frame_link]
                    
                    if len(new_current_state):
                        self._currentstate_ = new_current_state[0]
                        
                    else:
                        self._currentstate_ = None                            # CAUTION
            
        # NOTE: using a mapping 
        # below, for a single frame-linked state this just changes its 
        # z_frame value but does not add extra frame-linked states
        elif isinstance(values, dict):                                           # explicit mapping old -> new frame
            if not all([isinstance(f, int) for f in values]):                   # check for int types of keys
                raise TypeError("new frame indices expected to be a sequence of int, or a dictionary with int keys; got %s instead" % values)

            if not all([isinstance(f, int) for f in values.values()]):          # check for int types of values
                raise TypeError("new frame indices expected to be a sequence of int, or a dictionary with int keys; got %s instead" % values)

            if any([f < 0 for f in values]):                                    # check for valid values of keys
                raise ValueError("new frame indices must be >= 0")
            
            if any([f < 0 for f in values.values()]):                           # check for valid values
                raise ValueError("new frame indices must be >= 0")
            
            if len(set(values.values())) < len(values):                         # check for uniqueness of values
                raise ValueError("duplicate new frame indices are not allowed") # NOTE this beign a dict its keys
                                                                                # are guaranteed to be unique
                
            if len(self._states_) == 1:                                       # single frameless state
                if self._states_[0].z_frame is None:                          # 
                    new_states = list()                                         # generate new states for the frames
                    
                    for f in values.values():                                   # use the values in the mapping regardless
                        state = self._states_[0].copy()                       # of their keys
                        state.z_frame = f
                        new_states.append(state)
                        
                    self._states_[:] = new_states
                    self._currentstate_ = self._states_[0]
                    
                else:                                                           # a single frame-linked state
                    state = self._states_[0]
                    if state.z_frame in values:                                 # do nothing if its frame is not
                        new_frame = values[state.z_frame]                       # in the dict keys
                        state.z_frame = new_frame
                        
            else:                                                               # case with several states
                # change z_frame in states, supply new states if necessary:
                # 1) which states require a change to z_frame attribute ?
                target_states = [s for s in self._states_ \
                                 if s.z_frame in values.keys()]
                
                # 2) which states do NOT require change in z-frame attribute?
                avoid_states = [s for s in self._states_ \
                                if s.z_frame not in values.keys()]
                
                # 3) z_frame values of the states that must be avoided (see 2)
                avoid_state_frames = [s.z_frame for s in avoid_states]
                
                # 4) avoid new frame values that might generate duplication of
                # frame links
                new_frame_map = dict([(k,v) for (k,v) in values.items() \
                                      if k not in avoid_state_frames])
                
                # 5) let user know the outcome of all of the above checks 
                # 5.a) no suitable mappings left
                if len(new_frame_map) == 0:
                    warnings.warn("No remapping posible after avoiding frame-link duplications", RuntimeWarning)
                    return
                
                # 5.b) some suitable mapping left
                if len(new_frame_map) < len(values):
                    warnings.warn("Some new frame remappings were discarded to avoid frame-link duplications", RuntimeWarning)
                    # re-select target states
                    target_states = [s for s in self._states_ \
                                     if s.z_frame in new_frame_map.keys()]
                
                # 6) FINALLY apply the mappings
                if len(target_states):
                    for k, s in enumerate(target_states):
                        new_frame = values[s.z_frame]
                        s.z_frame = new_frame
                        
                else:   # tehcnically this branch will never be reached
                    warnings.warn("State-frame links could not be remapped", RuntimeWarning)
                    
        elif isinstance(values, int):                                            # for just one frame link, if value is not a linked frame index already
            if values not in self.frameIndices:
                s = self._currentstate_.copy()
                s.z_frame = values
                self._states_.append(s)
                
        else:
            raise TypeError("Expecting an int, a possibly empty iterable (tupe, list, range) of int, a possibly empty dict ({int keys -> int values}) or just None; got %s instead" % type(values).__name__)

        #### END 
            
        #### BEGIN  old frameIndices() code; DO NOT DELETE
        #if not isinstance(values, (tuple, list, dict)):
            #raise TypeError("Expecting a sequence or a dict; got %s instead" % type(values).__name__)
        
        #if len(values) > len(self._states_):
            #if len(self._states_) > 1 or self._states_[0].z_frame is not None:
                #raise ValueError("Too many new frame indices (%d) for %d states" % (len(values), len(self._states_)))

        #if len(values) == 1 and values[0] is None:
            #values = []
        
        #if len(values):
            #if not all([isinstance(f, int) for f in values]):
                #raise TypeError("new frame indices expected to be a sequence of int, or a dictionary with int keys; got %s instead" % values)
            
            #if any([f < 0 for f in values]):
                #raise ValueError("new frame indices must be >= 0")
            
            #if isinstance(values, (tuple, list)):
                #if len(set(values)) < len(values):                                # check for uniqueness of values
                    #raise ValueError("duplicate new frame indices are not allowed")
                
                #if len(self._states_) > 1:
                    #states = sorted(self._states_, 
                                    #key=lambda x:x.z_frame)
                    
                    #currentstate = self._currentstate_.copy()
                    
                    #if len(values) >= len(states):
                        #for k,s in enumerate(states):                           # change frames for existing states, supply new states if necessary
                            #if s.z_frame != values[k]:
                                #s.z_frame = values[k]
                            
                        #for v in range(len(states), len(values)):
                            #s = currentstate.copy()                             # replicate current state to extra frame indices
                            #s.z_frame = values[k]
                            #self._states_.append(s)
                            
                    #else:                                                       # discard extra states
                        #for k, s in enumerate(states__[0:len(values)]):
                            #if s.z_frame != values[k]:
                                #s.z_frame = values[k]
                                
                        #for s in states[len(values):]:
                            #self._states_.remove(s)
                            
                    #if self._currentstate_ not in self._states_:            # now re-set the current state in case it was removed
                        #newstates = sorted(self._states_, 
                                           #key=lambda x:x.z_frame)
                        
                        #newstateframes = [s.z_frame for s in newstates]
                        
                        #new_current_frame = bisect.bisect_left(newstateframes, self._currentstate_.z_frame)
                        
                        #self._currentstate_ = newstates[newstateframes.index(new_current_frame)]
                        
                #else:
                    #state = self._states_[0].copy()                           # replicate the only state as necessary
                    #self._states_.clear()
                    #for k in values:
                        #s = state.copy()
                        #s.z_frame = k
                        #self._states_.append(s)
                        
                    #self._currentstate_ = self._states_[0]
                        
            #elif isinstance(values, dict): # remaps frames
                #if not all([isinstance(v, int) for v in values.values()]):
                    #raise TypeError("When a mapping, all values in the new frame indices dictionary are expected to be int")
                
                #if len(set(values.values())) < len(values.values()):
                    #raise ValueError("Duplicate frame values are not allowed")  # do not allow duplicates
                
                #if any([v < 0 for v in values.values()]):
                    #raise ValueError("new frame indices must be >= 0")
            
                ## if there are to be NO duplicates in the values.keys() (and they aren't
                ## because values a dict), and since no two states can have
                ## identical z_frame values it follows that len(values) cannot 
                ## be larger than len(self._states_)
                ## therefore the next line is redundant
                ##if len(values) >= len(self._states_):
                
                ## after remapping, the currentstate might be linked to a new frame index
                ## we let this happen
                
                ## change frames for existing states, supply new states if necessary:
                
                ## 1) find out which states require a change to z_frame attribute
                #target_states = [s for s in self._states_ \
                                 #if s.z_frame in values.keys()]
                
                ## 2) which states do NOT require change in z-frame attribute
                #avoid_states = [s for s in self._states_ \
                                #if s.z_frame not in values.keys()]
                
                ## 3) frames of the states that must be avoided
                #avoid_state_frames = [s.z_frame for s in avoid_states]
                
                ## 4) avoid new frame values that might generate duplication of frame links
                #new_frame_map = dict([(k,v) for (k,v) in values.items() \
                                      #if k not in avoid_state_frames])
                
                #if len(new_frame_map) == 0:
                    #warnings.warn("No remapping posible after avoiding frame-link duplications", RuntimeWarning)
                    #return
                
                #if len(new_frame_map) < len(values):
                    #warnings.warn("Some new frame remappings were discarded to avoid frame-link duplications", RuntimeWarning)
                    ## re-select target states
                    #target_states = [s for s in self._states_ \
                                     #if s.z_frame in new_frame_map.keys()]
                
                #if len(target_states):
                    #for k, s in enumerate(target_states):
                        #new_frame = values[s.z_frame]
                        #s.z_frame = new_frame
                        
                #else:
                    #warnings.warn("State-frame links could not be remapped")
                    
        #else: # erase frame information; retain current state as for all available frames
            #current_state = self.currentState.copy()
            #current_state.z_frame = None
            
            #self._states_[:] = [current_state]
            
        #### END old frameIndices() code; DO NOT DELETE

    @property
    def type(self):
        return self._graphics_object_type_
        
    @property
    def frontends(self):
        """A list of GraphicsObject front ends.
        This property is read-only, but its value (a list) is mutable..
        """
        return self._frontends_
    
    #@frontend.setter
    #"def" frontends(self, value):
        ## TODO/FIXME make sure this object is the __backend__ of value
        #if isinstance(value, GraphicsObject) and value.isGeometricShape:
            #if value.__backend__ == self:
                #self._frontend=value
                

    

# NOTE: 2017-11-24 21:33:20
# bring this up at module level - useful for other classes as well
class GraphicsObjectType(IntEnum):
    """Enumeration of all supported graphical object types.
    vertical_cursor     = 1     
    horizontal_cursor   = 2     
    crosshair_cursor    = 4     
    point_cursor        = 8     
    point               = 16    
    line                = 32    
    polyline            = 64
    rectangle           = 128   
    polygon             = 256   
    ellipse             = 512   
    quad                = 1024
    cubic               = 2048
    arc                 = 4096
    arcmove             = 8192
    path                = 16384 
    text                = 32768 
    
    lineCursorTypes     = vertical_cursor       | horizontal_cursor
    shapedCursorTypes   = lineCursorTypes       | crosshair_cursor
    allCursorTypes      = shapedCursorTypes     | point_cursor
    
    linearTypes         = line                  | polyline
    polygonTypes        = rectangle             | polygon 
    linearShapeTypes    = polygonTypes          | linearTypes
    arcTypes            = arc                   | arcmove
    curveTypes          = ellipse               | arcTypes
    basicShapeTypes     = linearShapeTypes      | curveTypes
    commonShapeTypes    = basicShapeTypes       | point
    geometricShapeTypes = commonShapeTypes      | path
    allShapeTypes       = geometricShapeTypes   | text    # all non-cursor types
    
    allObjectTypes      = allCursorTypes        | allShapeTypes
 
    move                = point
  
    """
    vertical_cursor     = 1     # 5 parameters (W, H, xWin, yWin, radius)
    horizontal_cursor   = 2     # 5 parameters (W, H, xWin, yWin, radius)
    crosshair_cursor    = 4     # 5 parameters (W, H, xWin, yWin, radius)
    point_cursor        = 8     # 5 parameters (W, H, xWin, yWin, radius)
    point               = 16    # QPainterPath              QPointF     <=> 2 coordinates (X,Y)
    line                = 32    # QGraphicsLineItem         QLineF      <=> 4 coordinates (X0, Y0, X1, Y1)
    polyline            = 64
    rectangle           = 128   # QGraphicsRectItem         QRectF      <=> 4 coordinates (X, Y, W, H) = closed
    polygon             = 256   # QGraphicsPolygonItem      QPolygonF   <=> sequence of QPointF <=> sequence of (X, Y) pairs
    ellipse             = 512   # QGraphicsEllipseItem      QRectF      <=> 4 coordinates (X, Y, W, H) = closed
    quad                = 1024
    cubic               = 2048
    arc                 = 4096
    arcmove             = 8192
    path                = 16384 #Path
    qtpath              = 32768 # QPainterPath
    text                = 65536 # QGraphicsSimpleTextItem               <=> str
    
    lineCursorTypes     = vertical_cursor       | horizontal_cursor
    shapedCursorTypes   = lineCursorTypes       | crosshair_cursor
    allCursorTypes      = shapedCursorTypes     | point_cursor
    
    linearTypes         = line                  | polyline
    polygonTypes        = rectangle             | polygon 
    linearShapeTypes    = polygonTypes          | linearTypes
    arcTypes            = arc                   | arcmove
    curveTypes          = ellipse               | arcTypes
    basicShapeTypes     = linearShapeTypes      | curveTypes
    commonShapeTypes    = basicShapeTypes       | point
    geometricShapeTypes = commonShapeTypes      | path
    allShapeTypes       = geometricShapeTypes   | text
    
    allObjectTypes      = allCursorTypes        | allShapeTypes

def __new_planar_graphic__(cls, states, name="", frameindex=[], currentframe=0, \
                        graphicstype=None, closed=False, linked_objects = dict(), \
                        position = (0,0)):
    """Will dispatch to sub-class c'tor.
    
    Positional parameters:
    =======================
    cls: the sub-class
    
    states: dictionary mapping frame index (int) keys to datatypes.DataBag state objects, 
            or a datatypes.DataBag state object, or a sequence (tuple, list) of 
            PlanarGraphics objects (for unpickling Path objects)
    
    name: the name (_ID_), a str
    
    """
    obj = cls(states, name=name, graphicstype=graphicstype, closed=closed, 
              currentframe=currentframe, frameindex=frameindex, 
              linked_objects=linked_objects)
    
    for (o, link) in linked_objects.items():
        obj._linked_objects_[o] = link
        
    if cls == Path:
        obj._position_ = position
    
    return obj

# to be able to read old pickles
_new_planar_graphic = __new_planar_graphic__
_new_planar_graphic_ = __new_planar_graphic__


#_new_planar_graphic = __new_planar_graphic__ # for backward compatiblity

class Move(PlanarGraphics):
    """Starting path point with coordinates x and y (float type).
    
    Corresponds to a QPainterPath.MoveToElement.
    
    When present, it initiates a new path (or subpath, if preceded by any other 
    path element or PlanarGraphics object).
    
    Start is an alias of Move in this module.
    """
    #_planar_descriptors_ = ("x", "y")
    _planar_descriptors_ = ("x", "y", "z_frame")
    
    _graphics_object_type_ = GraphicsObjectType.point
    
    _qt_path_composition_call_ = "moveTo"

    #"def" __init__(self, x, y, name=None, frameindex=[], currentframe=0):
    def __init__(self, *args, name=None, frameindex=[], currentframe=0, 
                 graphicstype=None, closed=False,
                 linked_objects=dict()):
        """Parameters: move to point coordinates (x,y)
        """
        super().__init__(*args, name=name, frameindex=frameindex, currentframe=currentframe,
                         graphicstype=GraphicsObjectType.point, closed=closed,
                         linked_objects=linked_objects)
        

    def points(self):
        return [QtCore.QPointF(self.x, self.y)]
    
    def point(self):
        return QtCore.QPointF(self.x, self.y)
    
    def qGraphicsItem(self, pointSize=0, frame = None):
        """Overrides PlanarGraphics.qGraphicsItem;
        Returns a circle
        """
        if frame is None:
            state = self.currentState
            
        else:
            if not isinstance(frame, int):
                raise TypeError("frame expected to be an int or None; got %s instead" % frame)

            if frame in self.frameIndices:
                state = self.getState(frame)
                
            else:
                warnings.warn("No state is associated with specified frame (%d)" % frame)
                return
            
        if state is None or len(state) == 0:
            warnings.warn("undefined state")
            return
            
        return QtWidgets.QGraphicsEllipseItem(QtCore.QRectF(state.x - pointSize/2,
                                                            state.y - pointSize/2,
                                                            pointSize, 
                                                            pointSize))

Start = Move

Point = Move
                              
class Line(PlanarGraphics):
    """End point of a linear path segment, with coordinates x and y (float type).
    
    Corresponds to a QPainterPath.LineToElement.
    
    When present at the beginning of a path, it ALWAYS starts at (0.0, 0.0). 
    
    Otherwise, its origin is the last point of the previous PlanarGraphics
    object (Move, Line, CubicCurve or QuadCurve element).
    
    """
    #_planar_descriptors_ = ("x", "y")
    _planar_descriptors_ = ("x", "y", "z_frame")
    
    # FIXME must revisit this: Line is in fact a point, isn't it?
    _graphics_object_type_ = GraphicsObjectType.point
    
    _qt_path_composition_call_ = "lineTo"

    #"def" __init__(self, x, y, name=None, frameindex=[], currentframe=0):
    def __init__(self, *args, name=None, frameindex=[], currentframe=0, graphicstype=None,
                 closed=False,
                 linked_objects=dict()):
        """Parameters: line to destination coordinates (x,y)
        """
        super().__init__(*args, name=name, frameindex=frameindex, currentframe=currentframe, 
                         graphicstype=GraphicsObjectType.point, closed=closed,
                         linked_objects=linked_objects)
        
    def qGraphicsItem(self, pointSize=0, frame = None):
        if frame is None:
            state = self.currentState
            
        else:
            if not isinstance(frame, int):
                raise TypeError("frame expected to be an int or None; got %s instead" % frame)

            if frame in self.frameIndices:
                state = self.getState(frame)
                
            else:
                warnings.warn("No state is associated with specified frame (%d)" % frame)
                return
            
        if state is None or len(state) == 0:
            warnings.warn("undefined state")
            return
            
        return QtWidgets.QGraphicsLineItem(QtCore.QLineF(QtCore.QPointF(0,0),
                                                         QtCore.QPointF(state.x, state.y)))

class Cubic(PlanarGraphics):
    """A cubic curve path segment
    
    Coordinates are,respectively, for the:
    first control point: x, y;
    second control point: x1, y1; 
    end point (destination): x2, y2.
    
    Corresponds to the triplet:
    (QPainterPath.CurveToElement, QPainterPath.CurveToDataElement, QPainterPath.CurveToDataElement).
    
    When present at the beginning of a path, it ALWAYS starts at (0.0, 0.0). 
    
    Otherwise, its origin is the previous PlanarGraphics
    object (Move, Line, CubicCurve or QuadCurve element).
    
    """
    _planar_descriptors_ = ("x", "y", "c1x", "c1y", "c2x","c2y", "z_frame")
    
    _graphics_object_type_ = GraphicsObjectType.cubic
    
    _qt_path_composition_call_ = "cubicTo"

    #"def" __init__(self, x, y, c1x, c1y, c2x, c2y, name=None, frameindex=[], currentframe=0):
    def __init__(self, *args, name=None, frameindex=[], currentframe=0, graphicstype=None,
                 closed=False,
                 linked_objects=dict()):
        """
        Parameters:
        x,y = cubic curve destination coordinates
        c1x, c1y = first control point coordinates
        c2x, c2y = second control point coordinates
        """
        super().__init__(*args, name=name, frameindex=frameindex, currentframe=currentframe,
                         graphicstype=GraphicsObjectType.cubic, closed=closed,
                         linked_objects=linked_objects)
        
    def controlPoints(self, frame=None):
        if frame is None:
            state = self.currentState
            
        else:
            state = self.getState(frame)
            
        if state is None or len(state) == 0:
            return tuple()
        
        return ((state.x, state.y), (state.c1x, state.c1y), (state.c2x, state.c2y))
    
    def asControlPath(self, frame=None):
        ret = Path()
        
        cp = self.controlPoints(frame)
        
        for k,p in enumerate(cp):
            if k == 0:
                ret.append(Move(p[0], p[1]))
                
            else:
                ret.append(Line(p[0], p[1]))
            
            
        return ret
    
    def fromControlPath(self, path, frame=None):
        if not isinstance(path, Path):
            raise TypeError("path expected ot be a pictgui.Path; got %s instead" % type(path).__name__)
        
        if len(path) != 3:
            raise ValueError("path expected to have four elements; got %d instead" % len(path))
        
        control_state = path.currentState
        
        if control_state is None or len(control_state) == 0:
            raise ValueError("path argument has undefined state")
        
        if frame is None:
            state = self.currentState
            
        else:
            state = self.getState(frame)
            
        if state is None or len(state) == 0:
            return
        
        state.x = path[0].x
        state.y = path[0].y
        
        state.c1x = path[1].x
        state.c1y = path[1].y
        
        state.c2x = path[2].x
        state.c2y = path[2].y
    
        self.updateFrontends()
        
    def qPoints(self, frame=None):
        cp = self.controlPoints(frame)
        
        if len(cp):
            return [QtCore.QPointF(cp[0][0], cp[0][1]),
                    QtCore.QPointF(cp[1][0], cp[1][1]), 
                    QtCore.QPointF(cp[2][0], cp[2][1])]
        
        else:
            return list()
        
    def translate(self, dx, dy):
        self.x += dx
        self.y += dy
        self.c1x += dx
        self.c1y += dy
        self.c2x += dx
        self.c2y += dy
        
    def makeBSpline(self, xy, extrapolate=True):
        """Creates a cubic BSpline object with origin at "xy"
        
        Parameters:
        ==========
        xy: array_like: the x0, y0 coordinates of the origin
        
        extrapolate: boolean, default True (see scipy.inteprolate.BSpline)
        
        """
        from scipy.interpolate import BSpline
        
        t = np.zeros((8,))
        t[4:] = 1.
        
        c = np.array([[xy[0], xy[1]], [self.c1x, self.c1y], [self.c2x, self.c2y], [self.x, self.y]])
        
        return BSpline(t, c, 3, extrapolate=extrapolate)
        
        
    #"def" qGraphicsItem(self, pointSize=0, frame = None):
        #if frame is None:
            #state = self.currentState
            
        #else:
            #if frame in self.frameIndices:
                #state = self.getState(frame)
                
            #else:
                #warnings.warn("No state is associated with specified frame (%d)" % frame)
                #return
        
        #ret = QtWidgets.QGraphicsPathItem(self())
        
class Quad(PlanarGraphics):
    """A quadratic curve path segment.
    
    Coordinates are, respectively, for the control point: x, y and for the end
    end point (destination): x1, y1.
    
    Corresponds to the tuple:
    (QPainterPath.CurveToElement, QPainterPath.CurveToDataElement).
    
    When present at the beginning of a path, it ALWAYS starts at (0.0, 0.0). 
    
    Otherwise, its origin is the previous PlanarGraphics
    object (Move, Line, CubicCurve or QuadCurve element).
    """
    _planar_descriptors_ = ("x", "y", "cx", "cy", "z_frame")
    
    _graphics_object_type_ = GraphicsObjectType.quad
    
    _qt_path_composition_call_ = "quadTo"

    #"def" __init__(self, x, y, cx, cy, name=None, frameindex=[]):
    def __init__(self, *args, name=None, frameindex=[], currentFrame=0, 
                 graphicstype=None, closed=False,
                 linked_objects=dict()):
        """
        Parameters:
        x,y = quad curve to point coordinates
        c11x, c1y = control point coordinates
        """
        super().__init__(*args, name=name, frameindex=frameindex, currentframe=currentframe, 
                         graphicstype=GraphicsObjectType.quad, closed=closed,
                         linked_objects=linked_objects)
    
    def controlPoints(self, frame=None):
        if frame is None:
            state = self.currentState
            
        else:
            state = self.getState(frame)
            
        if state is None or len(state) == 0:
            return tuple()
        
        return ((state.x, state.y), (state.cx, state.cy))
        
    def asControlPath(self, frame=None):
        ret = Path()
        cp = self.controlPoints(frame)
        
        # NOTE: FIXME shouldn't this be in inverse order?
        for k,p in enumerate(cp):
            if k == 0:
                ret.append(Move(p[0],p[1]))
                
            else:
                ret.append(Line(p[0],p[1]))
                
        return ret
    
    def fromControlPath(self, path, frame=None):
        if not isinstance(path, Path):
            raise TypeError("path expected ot be a pictgui.Path; got %s instead" % type(path).__name__)
        
        if len(path) != 2:
            raise ValueError("path expected to have four elements; got %d instead" % len(path))
        
        control_state = path.currentState
        
        if control_state is None or len(control_state) == 0:
            raise ValueError("path argument has undefined state")
        
        if frame is None:
            state = self.currentState
            
        else:
            state = self.getState(frame)
            
        if state is None or len(state) == 0:
            return
        
        state.x = path[0].x
        state.y = path[0].y
        
        state.cx = path[1].x
        state.cy = path[1].y
        
        self.updateFrontends()
        
    def translate(self, dx, dy):
        self.x += dx
        self.y += dy
        self.cx += dx
        self.cy += dy
        
    def qPoints(self, frame=None):
        cp = self.controlPoints(frame)
        
        if len(cp):
            return [QtCore.QPointF(cp[0][0], cp[0][1]),
                    QtCore.QPointF(cp[1][0], cp[1][1])]
        
        else:
            return list()
        
    def makeBSpline(self, xy, extrapolate=True):
        """Creates a cubic BSpline object with origin at "xy"
        
        Parameters:
        ==========
        xy: array_like: the x0, y0 coordinates of the origin
        
        extrapolate: boolean, default True (see scipy.inteprolate.BSpline)
        
        """
        from scipy.interpolate import BSpline
        
        t = np.zeros((6,))
        t[3:] = 1.
        
        c = np.array([[xy[0], xy[1]], [self.cx, self.cy], [self.x, self.y]])
        
        return BSpline(t, c, 2, extrapolate=extrapolate)
        
            
class Arc(PlanarGraphics):
    """Encapsulates parameters for QPainterPath.arcTo() function
    
    x, y, w, h specify the bounding rectangle;
    
    s and l specify the start angle and the sweep length, respectively.
    
    See documentation for QPainterPath.arcTo() function.
    
    When present at the beginning of a path, it ALWAYS starts at (0.0, 0.0). 
    
    Otherwise, its origin is the previous PlanarGraphics
    object (Move, Line, CubicCurve or QuadCurve element).
    """
    #_planar_descriptors_ = ("x", "y", "w", "h", "s", "l")
    
    # see NOTE: 2019-03-19 13:49:51
    _planar_descriptors_ = ("x", "y", "w", "h", "s", "l", "z_frame")
    
    _graphics_object_type_ = GraphicsObjectType.arc
    
    _qt_path_composition_call_ = "arcTo"
    
    def __init__(self, *args, name=None, frameindex=[], currentframe=0, graphicstype=None, 
                 closed=False, linked_objects=dict()):
        """
        Positional parameters:
        =======================
        x, y, w, h = bounding rectangle (top left (x, y) width and height)
        
        s = start angle (degrees, positive is CCW; negative is CW)
        
        l = sweep length (angle in degrees, positive is CCW; negative is CW)
        
        """
        super().__init__(*args, name=name, frameindex=frameindex, currentframe=currentframe, 
                         graphicstype=GraphicsObjectType.arc, closed=closed, linked_objects=linked_objects)
        
    def controlPoints(self, frame = None):
        """Returns the control points for this Arc, as a tuple.
        
        To be used for graphical manipulation of the arc.
        
        The control points are given as (x,y) pairs or Cartesian coordinates
        with the major axis of the arc's ellipse having a 0 angle, in the 
        following order:
        
        cp0: the origin of the enclosing rectangle (Move to)
        
        cp1: starting point of the arc (line to)
        
        cp2: the centre of the arc's ellipse (and enclosing rectangle) (line to)
        
        cp3: the end point of the arc (line to)
        
        """
        
        if frame is None:
            state = self.currentState
            
        else:
            state = self.getState(frame)
            
        if state is None or len(state) == 0:
            return tuple() # empty path
        
        if state.w > state.h:
            major_axis = state.w
            minor_axis = state.h
            #horizontal = True
            
        else:
            major_axis = state.h
            minor_axis = state.w
            #horizontal = False
            
        start_angle = state.s * np.pi/180
        sweep_angle = state.l * np.pi/180
        
        # cp0: top-left corner of the enclosing rectangle 
        cp0 = (state.x, state.y)
        
        # cp1: the first point on the arc (EXCLUDING the connection to the arc's ellipse centre)
        cp1 = (major_axis * np.cos(start_angle), minor_axis * np.sin(start_angle))
        
        # cp2: the centre of the arc's ellipse (same as the centre of its enclosing rectangle)
        cp2 = (state.x + w/2, state.y + h/2)
        
        # cp3: the last point on the arc (EXCLUDING any connection back to the centre)
        cp3 = (major_axis * np.cos(sweep_angle), minor_axis * np.sin(sweep_angle))
        
        return (cp0, cp1, cp2, cp3)
        
    def asControlPath(self, frame = None):
        """Returns the control points for this Arc, as a Path object
        
        To be used for graphical manipulation of the arc.
        
        The control points are given as (x,y) pairs or Cartesian coordinates
        with the major axis of the arc's ellipse having a 0 angle, in the 
        following order:
        
        cp0: the origin of the enclosing rectangle (Move to)
        
        cp1: starting point of the arc (line to)
        
        cp2: the centre of the arc's ellipse (and enclosing rectangle) (line to)
        
        cp3: the end point of the arc (line to)
        
        """
        
        ret = Path()
        
        cp = self.controlPoints(frame)
        
        for k, p in enumerate(cp):
            if k == 0:
                ret.append(Move(p[0],p[1]))
            
            else:
                ret.append(Line(p[0],p[1]))
        
        return ret
    
    def fromControlPath(self, path, frame=None):
        if not isinstance(path, Path):
            raise TypeError("path expected ot be a pictgui.Path; got %s instead" % type(path).__name__)
        
        if len(path) != 4:
            raise ValueError("path expected to have four elements; got %d instead" % len(path))
        
        control_state = path.currentState
        
        if control_state is None or len(control_state) == 0:
            raise ValueError("path argument has undefined state")
        
        if frame is None:
            state = self.currentState
            
        else:
            state = self.getState(frame)
            
        if state is None or len(state) == 0:
            return
        
        # cp0: top-left corner of the enclosing rectangle 
        # cp1: the first point on the arc (EXCLUDING the connection to the arc's ellipse centre)
        # cp2: the centre of the arc's ellipse (same as the centre of its enclosing rectangle)
        # cp3: the last point on the arc (EXCLUDING any connection back to the centre)
        state.x = control_state[0].x
        state.y = control_state[0].y
        
        state.w = (control_state[2].x - state.x) * 2
        state.h = (control_state[2].y - state.y) * 2
        
        if state.w > state.h:
            major_axis = state.w
            minor_axis = state.h
            
        else:
            major_axis = state.h
            minor_axis = state.w
            
            
        state.s = np.arctan(control_state[1].y * major_axis / (control_state[1].x * minor_axis)) * 180 / np.pi
        
        state.l = np.arctan(control_state[3].y * major_axis / (control_state[3].x * minor_axis)) * 180 / np.pi
        
        self.updateFrontends()
        
class ArcMove(PlanarGraphics):
    """Encapsulates parameters for QPainterPath.arcMoveTo() function

    x, y, w, h, specify the bounding rectangle;
    a specifies the start angle.
    
    NOTE: Since this is a move on an arc trajectory, there is NO sweep length
    
    See also documentation for QPainterPath.arcMoveTo() function.
    """
    #_planar_descriptors_ = ("x", "y", "w", "h", "a")
    
    # see # NOTE: 2019-03-19 13:49:51
    _planar_descriptors_ = ("x", "y", "w", "h", "a", "z_frame")
    
    _graphics_object_type_ = GraphicsObjectType.arcmove
    
    _qt_path_composition_call_ = "arcMoveTo"
    
    def __init__(self, *args, name=None, frameindex=[], currentframe=0, 
                 graphicstype=None, closed=False,
                 linked_objects=dict()):
        """
        Positional parameters:
        =====================
        x, y, w, h = bounding rectangle (top left (x,y), width and height)
        
        a = angle (degrees, positive is CCW; negative is CW)
        
        """
        super().__init__(*args, name=name, frameindex=frameindex, currentframe=currentframe, 
                         graphicstype=GraphicsObjectType.arcmove, closed=closed, 
                         linked_objects=linked_objects)
    
    def controlPoints(self, frame = None):
        """Returns the control points for this Arc, as a tuple.
        
        To be used for graphical manipulation of the arc.
        
        The control points are given as (x,y) pairs or Cartesian coordinates
        with the major axis of the arc's ellipse having a 0 angle, in the 
        following order:
        
        cp0: the origin of the enclosing rectangle (Move to)
        
        cp1: starting point of the arc (line to)
        
        cp2: the centre of the arc's ellipse (and enclosing rectangle) (line to)
        
        cp3: the end point of the arc (line to)
        
        """
        
        if frame is None:
            state = self.currentState
            
        else:
            state = self.getState(frame)
            
        if state is None or len(state) == 0:
            return tuple() # empty path
        
        if state.w > state.h:
            major_axis = state.w
            minor_axis = state.h
            #horizontal = True
            
        else:
            major_axis = state.h
            minor_axis = state.w
            #horizontal = False
            
        start_angle = state.a * np.pi/180
        
        # cp0: top-left corner of the enclosing rectangle 
        cp0 = (state.x, state.y)
        
        # cp1: the first point on the arc (EXCLUDING the connection to the arc's ellipse centre)
        cp1 = (major_axis * np.cos(start_angle), minor_axis * np.sin(start_angle))
        
        # cp2: the centre of the arc's ellipse (same as the centre of its enclosing rectangle)
        cp2 = (state.x + w/2, state.y + h/2)
        
        return (cp0, cp1, cp2)
        
    def asControlPath(self, frame = None):
        """Returns the control points for this ArcMove, as a Path object
        
        NOTE: Since this is a move on an arc trajectory, there is NO sweep length
        To be used for graphical manipulation of the arc.
        
        The control points are given as (x,y) pairs or Cartesian coordinates
        with the major axis of the arc's ellipse having a 0 angle, in the 
        following order:
        
        cp0: the origin of the enclosing rectangle (Move to)
        
        cp1: starting point of the arc (line to)
        
        cp2: the centre of the arc's ellipse (and enclosing rectangle) (line to)
        
        """
        
        ret = Path()
        
        cp = self.controlPoints(frame)
        
        for k, p in enumerate(cp):
            if k == 0:
                ret.append(Move(p[0],p[1]))
                
            else:
                ret.append(Line(p[0], p[1]))
        
        return ret
        
    def fromControlPath(self, path, frame=None):
        if not isinstance(path, Path):
            raise TypeError("path expected ot be a pictgui.Path; got %s instead" % type(path).__name__)
        
        if len(path) != 3:
            raise ValueError("path expected to have four elements; got %d instead" % len(path))
        
        control_state = path.currentState
        
        if control_state is None or len(control_state) == 0:
            raise ValueError("path argument has undefined state")
        
        if frame is None:
            state = self.currentState
            
        else:
            state = self.getState(frame)
            
        if state is None or len(state) == 0:
            return
        
        # cp0: top-left corner of the enclosing rectangle 
        # cp1: the first point on the arc (EXCLUDING the connection to the arc's ellipse centre)
        # cp2: the centre of the arc's ellipse (same as the centre of its enclosing rectangle)
        state.x = control_state[0].x
        state.y = control_state[0].y
        
        state.w = (control_state[2].x - state.x) * 2
        state.h = (control_state[2].y - state.y) * 2
        
        if state.w > state.h:
            major_axis = state.w
            minor_axis = state.h
            
        else:
            major_axis = state.h
            minor_axis = state.w
            
        state.a = np.arctan(control_state[1].y * major_axis / (control_state[1].x * minor_axis)) * 180 / np.pi
        
        self.updateFrontends()
        
class Ellipse(PlanarGraphics):
    """Encapsulates parameters for QPainterPath.addEllipse() function:
    
    x, y, w, h specify the coordinates of the bounding rectangle
    """
    #_planar_descriptors_ = ("x", "y", "w", "h")
    
    # see NOTE: 2019-03-19 13:49:51
    _planar_descriptors_ = ("x", "y", "w", "h", "z_frame")
    
    _graphics_object_type_ = GraphicsObjectType.ellipse
    
    _qt_path_composition_call_ = "addEllipse"
    
    #"def" __init__(self, x, y, w, h, name=None, frameindex=[], currentframe=0):
    def __init__(self, *args, name=None, frameindex=[], currentframe=0, graphicstype=None, 
                 closed=False,
                 linked_objects=dict()):
        """
        Parameters: 
        x, y, w, h = bounding rectangle (top left (x,y), width, height)
        """
        super().__init__(*args, name=name, frameindex=frameindex, currentframe=currentframe,
                         graphicstype=GraphicsObjectType.ellipse, closed=closed,
                         linked_objects=linked_objects)
        
    def controlPoints(self, frame=None):
        """Control points are the top-left and bottom right of the enclosing rectangle
        """
        # TODO use more detailed control points as for ArcTo 
        # NOTE: this would be an unnecessary complication
        if frame is None:
            state = self.currentState
            
        else:
            state = self.getState(frame)
            
        if state is None or len(state) == 0:
            return tuple()
        
        return ((state.x, state.y), (state.x + state.w, state.y + state.h))
    
    def asControlPath(self, frame=None):
        """Control path is a line along the first diagonal of the encolsing rectangle
        (top-left to bottom-right)
        """
        ret = Path()
        
        cp = self.controlPoints(frame)
        
        for k,p in enumerate(cp):
            if k == 0:
                ret.append(Move(p[0],p[1]))
            
            else:
                ret.append(Line(p[0],p[1]))
                
        return ret
        
    def fromControlPath(self, path, frame=None):
        if not isinstance(path, Path):
            raise TypeError("path expected ot be a pictgui.Path; got %s instead" % type(path).__name__)
        
        if len(path) != 2:
            raise ValueError("path expected to have four elements; got %d instead" % len(path))
        
        control_state = path.currentState
        
        if control_state is None or len(control_state) == 0:
            raise ValueError("path argument has undefined state")
        
        if frame is None:
            state = self.currentState
            
        else:
            state = self.getState(frame)
            
        if state is None or len(state) == 0:
            return
        
        state.x = path[0].x
        state.y = path[0].y
        
        state.w = path[1].x - state.x
        state.h = path[1].y - state.y
        
        self.updateFrontends()
        
        
    def qPoints(self, frame = None):
        """Returns the points (vertices) of the enclosing rectangle.
        
        If there is no associated state for the specified frame index returns an
        empty list.
        
        """
        if frame is None:
            state = self.currentState
            
        else:
            state = self.getState(frame)
            
        if state is None or len(state) == 0:
            return list()
            
        return [QtCore.QPointF(state.x, state.y), 
                QtCore.QPointF(state.x + state.w, state.y), 
                QtCore.QPointF(state.x + state.w, state.y + state.h),
                QtCore.QPointF(state.x, state.y + state.h)]
    
    def qGraphicsItem(self, pointSize=0, frame = None):
        if frame is None:
            state = self.currentState
            
        else:
            if not isinstance(frame, int):
                raise TypeError("frame expected to be an int or None; got %s instead" % frame)

            if frame in self.frameIndices:
                state = self.getState(frame)
                
            else:
                warnings.warn("No state is associated with specified frame (%d)" % frame)
                return
            
        if state is None or len(state) == 0:
            warnings.warn("undefined state")
            return
            
        return QtWidgets.QGraphicsEllipseItem(QtCore.QRectF(state.x, state.y,
                                                            state.w, state.h))

class Rect(PlanarGraphics):
    """Encapsulates parameters for QPainterPath.addRect() function:
    
    x, y, w, h specify the coordinates of the bounding rectangle
    """
    
    # NOTE: 2018-01-11 12:14:59
    # attributes with names of parameters for the parametric constructor
    # of the planar graphic object
    
    # ATTENTION: these must be present in the exact order in which they are passed
    # to the parametric form of the constructor
    #_planar_descriptors_ = ("x", "y", "w", "h")
    
    # see NOTE: 2019-03-19 13:49:51
    _planar_descriptors_ = ("x", "y", "w", "h", "z_frame")
    
    _graphics_object_type_ = GraphicsObjectType.rectangle
    
    _qt_path_composition_call_ = "addRect"

    def __init__(self, *args, name=None, frameindex=[], currentframe=0, graphicstype=None,
                 closed=False, linked_objects=dict()):
        """
        Positional parameters: 
        =====================
        
        x, y: top left coordinates (x,y) 
        
        w, h: width and height
        
        """
        super().__init__(*args, name=name, frameindex=frameindex, currentframe=currentframe, 
                         graphicstype=GraphicsObjectType.rectangle, closed=closed,
                         linked_objects=linked_objects)
        
    def controlPoints(self, frame=None):
        """Control points are the top-left and bottom right vertices
        """
        if frame is None:
            state = self.currentState
            
        else:
            state = self.getState(frame)
            
        if state is None or len(state) == 0:
            return tuple()
        
        return ((state.x, state.y), (state.x + state.w, state.y + state.h))
    
    def asControlPath(self, frame=None):
        """Control path is the diagonal from top-left to bottom-right
        """
        ret = Path()
        cp = self.controlPoints(frame)
        
        for k,p in enumerate(cp):
            if k == 0:
                ret.append(Move(p[0],p[1]))
                
            else:
                ret.append(Line(p[0],p[1]))
                
        return ret
    
    def fromControlPath(self, path, frame=None):
        if not isinstance(path, Path):
            raise TypeError("path expected ot be a pictgui.Path; got %s instead" % type(path).__name__)
        
        if len(path) != 2:
            raise ValueError("path expected to have four elements; got %d instead" % len(path))
        
        control_state = path.currentState
        
        if control_state is None or len(control_state) == 0:
            raise ValueError("path argument has undefined state")
        
        if frame is None:
            state = self.currentState
            
        else:
            state = self.getState(frame)
            
        if state is None or len(state) == 0:
            return
        
        state.x = path[0].x
        state.y = path[0].y
        
        state.w = path[1].x - state.x
        state.h = path[1].y - state.y
        
        self.updateFrontends()
        
    def qPoints(self, frame = None):
        """Returns the points (apices) of the rectangle.
        
        If there is no associated state for the frame index specified returns
        an empty list
        
        """
        
        if frame is None:
            state = self.currentState
            
        else:
            state = self.getState(frame)
            
        if state is None or len(state) == 0:
            warnings.warn("Rectangle: undefined state")
            return list()
            
        return [QtCore.QPointF(state.x, state.y), 
                QtCore.QPointF(state.x + state.w, state.y), 
                QtCore.QPointF(state.x + state.w, state.y + state.h),
                QtCore.QPointF(state.x, state.y + state.h)]
    
    def qGraphicsItem(self, pointSize=0, frame = None):
        if frame is None:
            state = self.currentState
            
        else:
            if not isinstance(frame, int):
                raise TypeError("frame expected to be an int or None; got %s instead" % frame)

            if frame in self.frameIndices:
                state = self.getState(frame)
                
            else:
                warnings.warn("No state is associated with specified frame (%d)" % frame)
                return
            
        if state is None or len(state) == 0:
            warnings.warn("undefined state")
            return
            
        return QtWidgets.QGraphicsRectItem(QtCore.QRectF(state.x, state.y,
                                                         state.w, state.h))
    
    def asCanonicalPath(self, frame=None, closed = False):
        ret = Path()
        
        if frame is None:
            state = self.currentState
        
        elif isinstance(frame, int):
            state = self.getState(frame)
            
        else:
            raise TypeError("'frame' parameter expected to be an int or None; got %s instead" % type(frame).__name__)
        
            
        if state is not None and len(state):
            ret.append(Move(state.x, state.y))
            ret.append(Line(state.x + state.w, state.y))
            ret.append(Line(state.x + state.w, state.y + state.h))
            ret.append(Line(state.x, state.y + state.h))
            
            if closed:
                ret.append(Line(state.x, state.y))
                
        return ret
    
    def convertToPath(self):
        frame_ndx = self.frameIndices()
        ret = self.asPath(frame=frame_ndx[0], closed=True)
        
        for f in frame_ndx[1:]:
            frame_path = self.asPath(frame=f, closed=True)
            
            #ret.addState(f, frame_path.currentState)
            ret.addState(frame_path.currentState, f)
            
        ret.currentFrame = self.currentFrame
            
        return ret
    
    def convertToCanonicalPath(self):
        frame_ndx = self.frameIndices()
        ret = self.asCanonicalPath(frame=frame_ndx[0], closed=True)
        
        for f in frame_ndx[1:]:
            frame_path = self.asCanonicalPath(frame=f, closed=True)
            
            #ret.addState(f, frame_path.currentState)
            ret.addState(frame_path.currentState, f)
            
        ret.currentFrame = self.currentFrame
            

#NOTE: Only Move, Line and Cubic correspond to QPainterPath.Element 
PathElements = (Move, Line, Cubic, Quad, Arc, ArcMove) # "tier 1" elements: primitives that can be called directly

LinearElements = (Move, Line)

CurveElements = (Cubic, Quad, Arc, ArcMove)

Tier2PathElements = (Ellipse, Rect) # can be used as parameters for the GraphicsObject c'tor

Tier3PathElements = () # TODO: connectPath, addPath, addRegion, addPolygon, addText

def checkboxDialogPrompt(parent, title, slist):
    if not all([isinstance(s, str) for s in slist]):
        raise TypeError("Expecting a list of strings for the last argument")
    dlg = quickdialog.QuickDialog(parent, title)
    dlg.addWidget(QtWidgets.QLabel(title, parent=dlg))
    group = quickdialog.VDialogGroup(dlg)
    
    checkboxes = [quickdialog.CheckBox(group, value) for value in slist]
    
    dlg.resize(dlg.minimumSize())
    
    if dlg.exec() == 1:
        return [w.isChecked() for w in checkboxes]
    
    else:
        return [True for w in checkboxes]
    
def printQPainterPath(p):
    s = []
    for k in range(p.elementCount()):
        element = p.elementAt(k)
        if p.elementAt(k).type == QtGui.QPainterPath.MoveToElement:
            s.append("moveTo(x=%g, y=%g)" % (element.x, element.y))
            
        elif p.elementAt(k).type == QtGui.QPainterPath.LineToElement:
            s.append("lineTo(x=%g, y=%g)" %(element.x, element.y))
            
        elif p.elementAt(k).type == QtGui.QPainterPath.CurveToElement: # this is the FIRST control point!
            c1 = p.elementAt(k+1)                                      # this is the SECOND control point!
            c2 = p.elementAt(k+2)                                      # this is the DESTINATION point !
            s.append("cubicTo(c1x=%g, c1y=%g, c2x=%g, c2y=%g, x=%g, y=%g)" %\
                (element.x, element.y, c1.x, c1.y, c2.x, c2.y, ))
            #s.append("cubicTo(c1x=%g, c1y=%g, c2x=%g, c2y=%g, x=%g, y=%g)" %\
                #(c1.x, c1.y, c2.x, c2.y, element.x, element.y))
            #self.append(Cubic(c1.x, c1.y, c2.x, c2.y, element.x, element.y))
            #self.append(Cubic(element.x, element.y, e1.x, e1.y, e2.x, e2.y))
            
        else: # do not parse curve to data elements
            s.append("controlPoint(x=%g, y=%g)" % (element.x, element.y)) 
    
    #s.append("]")
    
    return "[" + ", ".join(s) + "]"

class Cursor(PlanarGraphics):
    """Encapsulates the coordinates of a cursor:
    
    x, y, width, height, xwindow, ywindow, radius, name, type
    """
    
    #_planar_descriptors_ = ("x", "y", "width", "height", "xwindow", "ywindow", "radius")

    _planar_descriptors_ = ("x", "y", "width", "height", "xwindow", "ywindow", "radius", "z_frame")
    
    _graphics_object_type_ = GraphicsObjectType.vertical_cursor
    _qt_path_composition_call_ = None
    
    def __init__(self, *args, name=None, frameindex=[], currentframe=0, 
                 graphicstype=GraphicsObjectType.crosshair_cursor, closed=False,
                 linked_objects=dict()):
        """
        Keyword parameters:
        ===================
        x, y:               scalars, cursor position (in pixels)
        
        width, height:      scalars, size of cursor main axis (in pixels) or 
                            None 
        
        xwindow, ywindow:   scalars, size of cursor's window 
        
        radius:             scalar, cursor radius (for point cursors) 
        
        name:               str, this cursor's name
        
        graphicstype:         GraphicsObjectType enum value defining a cursor
                            (see pictgui.GraphicsObjectType)
        
        
        At most one of x or y can be None (which one is determined by its
        position in the parameter expression list or in the sequence).
        
        When width or height are None, they will use the full size of their 
        corresponding image axes.
        """
        super().__init__(*args, name=name, frameindex=frameindex, 
                         currentframe=currentframe, 
                         graphicstype=graphicstype, 
                         closed=closed, 
                         linked_objects=linked_objects)
        
        #print("Cursor.__init__", self)
        
        if len(linked_objects):
            self._linked_objects_.update(linked_objects)
        
        #print("Cursor %s init link_objects = %s: " % (self, linked_objects))
        
    def map_to_pc_on_path(self, other, path):
        x = int(self.x)
        
        if x < 0:
            # NOTE FIXME what to do here?
            return
        
        cPath = path.asPath()
        
        if all([isinstance(e, (Move, Line)) for e in cPath]):
            if len(cPath) == 2:
                # path encapsulates a single line segment
                dx = cPath[1].x - cPath[0].x
                dy = cPath[1].y - cPath[0].y
                
                l = math.sqrt(dx ** 2 + dy ** 2)
                
                nx = self.x / l
                
                p.x = dx * nx + cPath[0].x
                p.y = dy * nx + cPath[0].y
                
            elif len(cPath) > 2:
                # a polyline/polygon
                # there is the possibility that path is a point-by-point mapping
                # to the width spanned by the vertical cursor; in this case, path
                # HAS an element for every possible (int(v.x))
                if len(cPath) == int(v.width):
                    # it is simpler to pick up the path element at the index in the 
                    # path, that is given by the vertical cursor's x coordinate 
                    ## (taken as an int)
                    if x >= 0 and x < len(cPath):
                        p.x = cPath[x].x
                        p.y = cPath[x].y
                    
                
                #else:
                    ## CAUTION: this line can quickly become very expensive !!!
                    ## consider factoring this in the Path object
                    ## on the other hand, parametric curves (Quad, Cubic) doe not have a closed form!!!
                    #euclid_lengths = [math.sqrt((e1.x -  e0.x) ** 2 + (e1.y - e0.y) ** 2) for (e0,e1) in zip(path[:-1], path[1:])]
                
class Text(PlanarGraphics):
    """PlanarGraphics object encapsulating a string.
    WARNING Incomplete API
    TODO also adapt the GraphicsObject frontend to support this class!
    """
    #_planar_descriptors_ = ("text", "x", "y") 
    
    # see NOTE: 2019-03-19 13:49:51
    _planar_descriptors_ = ("text", "x", "y", "z_frame") 
    
    _graphics_object_type_ = GraphicsObjectType.text
    
    _qt_path_composition_call_ = ""
    
    _required_attributes_ = ("_ID_")
    
    def __init__(self, *args, name="Text", frameindex=[], currentframe=0, position = (0,0)):
        if not isinstance(text, str):
            raise TypeError("Expecting a str as first parameter; got %s instead" % type(text).__name__)
        
        self._currentframe_ = currentframe
        self._ID_ = name
        self._closed_ = False
        
        PlanarGraphics.__init__(self, *args, name=name, frameindex=frameindex, currentframe=currentframe,
                                graphicstype=GraphicsObjectType.text,
                                closed=False)
        
    @property
    def closed(self):
        return False
    
    def copy(self):
        ret = self.__class__(self)
        return ret
    
    def controlPoints(self, frame=None):
        return tuple()
    
    def fromControlPath(self, path, frame=None):
        pass
                
    def asControlPath(self, frame=None):
        return Path()
    
    def asPath(self, frame=None, closed=False):
        return Path()
    
    def qPoints(self, frame=None):
        if frame is None:
            state = self.currentState
            
        else:
            frame = self.getState(frame)
            
        if state and len(state):
            return [QtCore.QPointF(state.x, state.y)]
        
        else:
            return list()
        
class Path(PlanarGraphics):
    """Encapsulates a path composed of simple PlanarGraphics objects.
    
    Emulates a Python list. Path objects can be constructed from a sequence of
    PlanarGraphics elements. 
    
    Subpaths can only be concatenated. Attempting to nest a path in another 
    path effectively breaks the receiving path in two concatenated subpaths.
    
    NOTE: Differences from the list API:
    
    (1) Appending or inserting another Path effectively appends/inserts that 
    Path's elements to this one.
    
    This is distinct from the standard Python list API, where inserting a 
    list into another list generates a structure of nested lists.
    
    (2) the + operator (addition) appends the elements of the right hand operand 
    to the left hand operand, when the right hand operand is also a Path; 
    otherwise, it appends the right hand operand (a PlanarGraphics object not of
    Path type)
    
    (3) The fact that Path objects do not contain other Path objects has two 
    consequences:
        
        path.index(other) raises ValueError when "other" is a Path object
        
        path.count(other) returns 0 when "other" is a Path object

    NOTE: Notable similarities to the list API
    
    (1) Elements are inserted/added BY REFERENCE therefore they can be modified 
    from outside their container Path object.
    
    (2) slicing Path objects returns Path objects containing REFERENCES to the 
    elements in the source Path (NOT COPIES) -- these can be modified which has
    the side effect that they will also modify the original elements in the 
    source Path
    
    This is intended as it creates "views" in the original Path avoiding 
    unnecessary data copying. 
    
    For copy-like behavior call "copy()" member function on the view.
    
    In addition, has functions to access the path elements as a list of QPointF
    (the "destination" point to moveTo, lineTo, quadTo, cubicTo) and as a list 
    QPainterPath.ElementType.
    
    NOTE: A Path must always begin with a Move object, and cannot contain other
    Path objects. When a Path object "p1" is appended to, or inserted in a Path 
    object "p2", the elements of p1 are appended individually to p2.
    
    Path inherits from python list. When the insertion of a Path element into 
    another Path is attempted using list API (e.g. p1[3] = p2), the elements of
    p2 will be INSERTED in their order, at p1. This effectively is the equivalent
    of p1.insert(3, p2).
    
    
    The sequence of Path elements from a Move to the next Move (excluding) constitute
    a "sub-path". 
    
    Examples:
    
    To generate a polyline, construct a Path with Move, LineTo, LineTo, .... as 
    parameters
    
    NOTE: Mutability -- editing/transformation/translation/rotation/scaling
    
    All these operations are done through its graphical representation as
    a GraphicsObject of nonCursorTypes (in this module); currently, only editing
    is implemented.
    
    For translations, the shape itself is unaltered and its coordinates (relative 
    to the QGraphicsItem object) are also unchanged. After translation, the new 
    coordinates relativ to the QGraphicsScene are changed.
    
    Because "x" and "y" are too important for all PlanarGraphics (they indicate
    the graphics' position in the image), but a Path object does NOT have explicit
    planar descriptors, we explicitly implement these properties here
    
    """
    # NOTE: 2018-02-09 15:37:21
    # not inheriting from list anymore -- emulating sequence container instead
    
    # better this way, so that we can:
    
    # 1) hash() it -- we allow this object's identity to be the same even after 
    #   we manipulate it, in particular after we add, remove, or reverse the 
    #   order of its constituent elements
     
    # 2) we can implement the subset of list API that makes sense and leave out
    #   those methods that do not (e.g., i.e. min() max())
    
    
    # leave empty
    _planar_descriptors_ = () 
    
    _graphics_object_type_ = GraphicsObjectType.path
    
    _qt_path_composition_call_ = "addPath"
    
    _required_attributes_ = ("_ID_", "_linked_objects_", "_segment_lengths_, _objects_")

    def __init__(self, *args, name="path", frameindex=[], currentframe=0, 
                 graphicstype=None, closed=False,
                 linked_objects = dict(), position = (0,0)):
        
        # the actual list of primitives that compose this path;
        # each is a PlanarGraphics object (NOT a Path) and have their own
        # frame-state associations i.e. an element can be visible in a subset
        # of frames whereas other elements can be visibule in a disjoint subset
        # of frames
        # NOTE: 2019-07-22 08:39:51
        # FIXME at the moment len(path) and len(path.states) is the same
        # something's confused here
        self._objects_ = list()
        
        # fallback position for an empty path; will be returned if no data is
        # found when currentstate is queried
        # also serves as cached position
        # NOTE: TODO perhgaps, in the general case, this should hold the
        # min(x), min(y) coordinate of the convex hull of the path ?
        self._position_ = position
            
        # NOTE:  2018-02-11 21:02:35
        # # TODO!!!
        # cache of the euclidean lengths of its segments and contour lengths of its
        # shaped elements.
        self._segment_lengths_ = list() 
        
        #self._currentframe_ = currentframe
        #self._ID_ = name
        #self._closed_ = closed
        
        PlanarGraphics.__init__(self, (), name=name, frameindex=frameindex, currentframe=currentframe, 
                                graphicstype=graphicstype, closed=closed,
                                linked_objects = linked_objects)
        
        if len(args):
            if len(args) == 1:
                if isinstance(args[0], Path):
                    # copy c'tor
                    for a in args[0]:
                        self._objects_.append(a.copy())
                    
                    self._closed_ = args[0]._closed_
                    self._currentframe_ = args[0]._currentframe_
                    self._ID_ = args[0]._ID_
                    
                    self._position_ = args[0]._position_
                    
                    self._graphics_object_type_ = args[0]._graphics_object_type_
                    
                    #self._currentstate_ = self.currentState
                    
                    return
                        
                elif isinstance(args[0], PlanarGraphics):
                    self._objects_.append(args[0].copy())
                    self._position_ = (args[0].x, args[0].y)
                    
                elif isinstance(args[0], (tuple, list)) and len(args[0]):
                    # NOTE: clauses for c'tor based on an iterable passed as 
                    # arguments -- two subclauses:
                    if all([isinstance(p, PlanarGraphics) for p in args[0]]):
                        # NOTE: this clause builds a Path from an iterable of 
                        # PlanarGraphics passed as an unique var-positional parameter
                        # TODO check here that all PlanarGraphics are acceptable 
                        # (they originally needed to be PathElements of Tier2PathElements, only!)
                        #
                        # also used for unpickling
                        
                        #print("*****\nPath c'tor from sequence of %d planar graphics\n*****" % len(args[0]))
                        
                        #obj_list = [p.copy() for p in args[0]]
                        
                        for k, p in enumerate(args[0]):
                            pp = p.copy()
                            
                            #print("** Copy of element %d: %s" % (k, p))
                            
                            self._objects_.append(pp)
                            
                        # NOTE: 2018-01-20 09:56:56
                        # make sure Path begins with a Move
                        if not isinstance(self._objects_[0], Move):
                            self._objects_.insert(0, Move(0,0, frameindex=frameindex, currentframe=currentframe))
                            
                        if all([isinstance(e, (Move, Line)) for e in self._objects_]):
                            if len(self._objects_) == 2:
                                self._graphics_object_type_ = GraphicsObjectType.line
                            
                            else:
                                if self._closed_:
                                    self._graphics_object_type_ = GraphicsObjectType.polygon
                                
                                else:
                                    self._graphics_object_type_ = GraphicsObjectType.polyline
                            
                        else:
                            self._graphics_object_type_ = GraphicsObjectType.path
                            
                            
                        if len(self._objects_):
                            x = min([e.x for e in self._objects_ if isinstance(e, PlanarGraphics)])
                            #xx = [e.x for e in self._objects_ if isinstance(e, PlanarGraphics)]
                            #xx = [x for x in xx if x is not None]
                            #x = min(xx)
                            #if len(xx):
                                #x = min(xx)
                                
                            #else:
                                #x = 0
                            
                            y = min([e.y for e in self._objects_ if isinstance(e, PlanarGraphics)])
                            #yy = [e.y for e in self._objects_ if isinstance(e, PlanarGraphics)]
                            #yy = [y for y in yy if y is not None]
                            #if len(yy):
                                #y = min(yy)
                                
                            #else:
                                #y = 0
                            
                            self._position_ = (x,y)
                            
                        else:
                            self._position_ = (0,0)
                            
                    elif all([isinstance(c, (tuple, list)) and len(c) == 2 for c in args[0]]):
                        # NOTE: clause for c'tor of path from iterable of coordinate tuples
                        # e.g. as stored in image XML metadata, etc => Move (, Line) *
                        
                        self._objects_.append(Move(args[0][0], args[0][1], frameindex=frameindex, currentframe=currentframe))
                        
                        if len(args[0]) > 1:
                            for a in args[1:]:
                                self._objects_.append(Line(a[0], a[1], frameindex=frameindex, currentframe=currentframe))
                                
                        self._position_ = (min([o.x for o in self]), min([o.y for o in self]))
                        
                        self._graphics_object_type_ = GraphicsObjectType.path
                        
                elif isinstance(args[0], QtGui.QPainterPath):
                    for k in range(args[0].elementCount()):
                        if args[0].elementAt(k).type == QtGui.QPainterPath.MoveToElement:
                            element = args[0].elementAt(k)
                            self._objects_.append(Move(element.x, element.y, 
                                                         frameindex=frameindex, currentframe=currentframe))
                            
                        elif args[0].elementAt(k).type == QtGui.QPainterPath.LineToElement:
                            element = args[0].elementAt(k)
                            self._objects_.append(Line(element.x, element.y, 
                                                         frameindex=frameindex, currentframe=currentframe))
                            
                        elif args[0].elementAt(k).type == QtGui.QPainterPath.CurveToElement:
                            element = args[0].elementAt(k)  # 2nd control point
                            c1 = args[0].elementAt(k+1)     # destination point
                            c2 = args[0].elementAt(k+2)     # 1st control point
                            # NOTE: do not delete -- keep for reference
                            #self.append(Cubic(x=c1.x, y=c1.y, c1x=c2.x, c1y=c2.y, c2x=element.x, c2y=element.y, frameindex=frameindex, currentframe=currentframe))
                            self._objects_.append(Cubic(c1.x, c1.y, c2.x, c2.y, element.x, element.y, 
                                                          frameindex=frameindex, currentframe=currentframe))
                            
                        else: # do not parse "curve to data" elements, for now
                            continue 
                        
                    self._position_ = (min([o.x for o in self]), min([o.y for o in self]))
                    self._graphics_object_type_ = GraphicsObjectType.path
                    
            else:
                if all([isinstance(a, (PlanarGraphics, tuple, list)) for a in args]):
                    for k, a in enumerate(args):
                        if k == 0:
                            if isinstance(a, PlanarGraphics):
                                aa = a.copy()
                                aa._currentframe_ = currentframe

                                self._objects_.append(aa)
                                    
                            elif isinstance(a, (tuple, list)) and len(a) == 2:
                                if frameindex is None or self._currentframe_ is None:
                                    raise ValueError("frameindex or currentframe can be None only when first argument is a PlanarGraphics; got %s instead." % a)
                                
                                self._objects_.append(Move(a[0], a[1], 
                                                             frameindex=frameindex, currentframe=self._currentframe_))
                                
                        else: # k >  0
                            if isinstance(a, PlanarGraphics):
                                aa = a.copy()
                                
                                if aa.frameIndices != frameindex:
                                    aa.frameIndices = frameindex
                                
                                if len(frameindex) == 0 and self._currentframe_ != 0:
                                    self._currentframe_ = 0
                                    
                                if aa._currentframe_ != self._currentframe_:
                                    aa._currentframe_ = self._currentframe_ 
                                
                                self._objects_.append(aa)
                                
                            elif isinstance(a, (tuple, list)) and len(a) == 2:
                                self._objects_.append(Line(a[0], a[1], frameindex=frameindex, currentframe=self._currentframe_))
                                    
                            else:
                                raise TypeError("When constructing a Path, var-positional parameters must be PlanarGraphics objects or tuples of coordinates")
                            
                    self._position_ = (min([o.x for o in self]), min([o.y for o in self]))
                    
                    # NOTE: 2018-01-20 09:51:23
                    # make sure Path begins with a Move
                    if not isinstance(self._objects_[0], Move):
                        self._objects_.insert(0,Move(0,0, frameindex = frameindex, currentframe=currentframe))
                    
                    self._graphics_object_type_ = GraphicsObjectType.path
                    
        self._ID_ = name
        self._closed_ = closed
        
        for e in self._objects_:
            e._currentframe_ = currentframe
        
    def __reduce__(self):
        return __new_planar_graphic__, (self.__class__, 
                                        self._objects_, 
                                        self._ID_, 
                                        self.frameIndices, 
                                        self._currentframe_,
                                        self._graphics_object_type_, 
                                        self._closed_,
                                        self._linked_objects_.copy(),
                                        self._position_)
    
    def __repr__(self):
        ss = super(PlanarGraphics, self).__repr__()
        return ss
        #s = [super(PlanarGraphics, self).__repr__(), ":\n"]
        #s += ["["]
        #s += [", ".join([o.__repr__() for o in self])]
        #s += ["]"]
        
        #return "".join(s)
        
    def __str__(self):
        s = "\n ".join(["%d: %s" % (k, e.__str__()) for k,e in enumerate(self._objects_)])
        return "%s object:\n name %s\n path elements: \n %s" % (self.__class__, self._ID_, s)
        
    def __call__(self, path=None, frame=None, closed=None, connected=False):
        """Generates a QtGui.QPainterPath.
        
        Named parameters:
        =================
        path:   None (default) or a QtGui.QPainterPath to which a new painter path
                generated by this function will be appended
                
        frame:  None (default) or an int >= 0; the index of the frame for which to 
                generate a painter path.
                
                When None, the painter path will be generated from the current 
                state (which may be the state associated with the current frame
                of the common state).
                
                When an int, if frame is fpund among the frame state associations
                a painter path will be generated from the state associated with
                the specified frame. 
                
                If frame is NOT found among the frame-state associations then
                an empty painter path will be returned.
                
        closed: None (default) or a boolean; when a boolean, True or False will
                force the generated path to be closed or open, respectively
                
        connected: boolean (default, False); when True and the "path" parameter
                is not None the generated painter path will be connected to the
                specified "path" parameter unless the last point on the "path"
                is shared with the first point on the generated path
        
        
        """
        if path is None:
            path = QtGui.QPainterPath()
            
        if closed is None:
            closePath = self.closed
            
        elif isinstance(closed, bool):
            closePath = closed
            
        else:
            raise TypeError("closed expected to be a boolean or None; got %s instead" % type(closed).__name__)
        
        if len(self):
            for k, p in enumerate(self._objects_):
                # this calls the object's __call__ function
                path = p(path, frame, closed=False, connected = connected) # just add the "primitive" element to the path
                    
            if closePath:
                # NOTE: ALWAYS  operate on current state (be it the common one,
                # or the state associated with current frame)
                if frame is None:
                    state = self.currentState
                    
                else:
                    state = self.getState(frame)
                    
                if state and len(state):
                    path.lineTo(self._objects_[0].x, self._objects_[0].y) 
                
        return path
            
    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        
    def __getattr__(self, name):
        return super().__getattr__(name)
            
    def __setitem__(self, key, value):
        if not isinstance(value, PlanarGraphics):
            raise TypeError("Expecting a PlanarGraphics objects; got %s instead" % type(value).__name__)

        if isinstance(value, Path):
            for k, v in enumerate(value):
                self._objects_.insert(key+k, v)
                
        else:
            self._objects_.__setitem__(key, value)
            
    def __getitem__(self, key):
        """Implements self[key] list semantic
        
        When key is an int, returns the PlanarGraphics object at index key.
        
        When key is a slice returns a Path object containg the PlanarGraphics
        elements as extracted by the slice object.
        """
        if isinstance(key, (int, slice)):
            return self._objects_[key]
        
        else:
            raise TypeError(" expecting an int or a slice object; got %s instead" % type(key).__name__)

    def __len__(self):
        """Returns the number of PlanarGraphics elements in this Path object.
        """
        return len(self._objects_)
    
    def __add__(self, other):
        if not isinstance(other, PlanarGraphics):
            raise TypeError("Expecting a PlanarGraphics object; got %s instead" % type(other).__name__)
            
        ret = self.copy()

        if isinstance(other, Path):
            ret._objects_ += other._objects_
        
        else:
            ret._objects_.append(other)
            
        return ret
    
    def __iadd__(self, other):
        if not isinstance(other, PlanarGraphics):
            raise TypeError("Expecting a PlanarGraphics object; got %s instead" % type(other).__name__)
            
        if isinstance(other, Path):
            self._objects_ += other._objects_
            
        else:
            self._objects_.append(other)
            
        return self
            
    def __imul__(self, value):
        if not isinstance(value, int):
            raise TypeError("Expecting an int; got %s instead" % type(value).__name__)
        
        self._objects_.__imul__(value)
        
        return self
            
    def __mul__(self, value):
        if not isinstance(value, int):
            raise TypeError("Expecting an int; got %s instead" % type(value).__name__)
        
        ret = self.copy()
        
        ret._objects_.__mul__(value)
        
        return ret
    
    def __rmul__(self, value):
        if not isinstance(value, int):
            raise TypeError("Expecting an int; got %s instead" % type(value).__name__)
        
        ret = self.copy()
        
        ret._objects_.rmul__(value)
        
        return ret
    
    def __iter__(self, *args, **kwargs):
        """Returns a list_iterator
        """
        return self._objects_.__iter__(*args, **kwargs)
    
    def __reversed__(self):
        """Returns a list_reverseiterator
        """
        return self._objects_.__reversed__()
    
    def appendStates(self, other):
        """ Overrides PlanarGraphics.appendStates() to flag that Path objects does not support this method
        """
        raise NotImplementedError("Path objects do not support this function; use appendStates on individual Path elements")
        
    def append(self, other):
        """Paths are appended as nested subpaths.
        To append all elements of another path, use appendStates().
        
        Returns:
        =======
        self
        """
        if isinstance(other, PlanarGraphics):
            if not other.type & GraphicsObjectType.allCursorTypes:
                other = other.copy()
                
                self._objects_.append(other)
                
            else:
                raise TypeError("Expecting a non-cursor type; got %s instead" % other.type)
            
        else:
            raise TypeError("Expecting a PlanarGraphics object; got %s instead" % type(other).__name__)
        
        return self
            
    def count(self, other):
        if not isinstance(other, PlanarGraphics):
            raise TypeError("Expecting a PlanarGraphics object; got %s instead" % type(other).__name__)
            
        return self._objects_.count(other)
    
    def clear(self):
        self._objects_.clear()
        
    def pop(self, index):
        return self._objects_.pop(index)
    
    def extend(self, other):
        self.__iadd__(other)
        
    def translate(self, dx, dy):
        if len(self._objects_):
            states = self.getState(self.currentFrame)
            
            for s in states:
                s.x += dx
                s.y += dy
                
                if "cx" in s:
                    s.cx += dx
                    
                if "c1x" in s:
                    s.c1x += dx
                    
                if "c2x" in s:
                    s.c2x += dx
                
                if "cy" in s:
                    s.cy += dy
                    
                if "c1y" in s:
                    s.c1y += dy
                    
                if "c2y" in s:
                    s.c2y += dy
                
    def index(self, other, *where):
        if not isinstance(other, PlanarGraphics):
            raise TypeError("Expecting a PlanarGraphics object; got %s instead" % type(other).__name__)
        
        if isinstance(other, Path):
            raise ValueError("%s is not in list" % other)

        return self._objects_.index(other, *where)
            
    def insert(self, index, other):
        if isinstance(other, Path):
            if len(other):
                for k,o in enumerate(other):
                    self._objects_.insert(index+k, o)

        else:
            self._objects_.insert(index, other)
            
    def remove(self, other):
        self._objects_.remove(other)
        
    def reverse(self):
        """Reverses the order of the elements in this Path.
        """
        self._objects_.reverse()
        
    def _check_state_(self, states):
        import core.datatypes as dt
        
        if not isinstance(states, (tuple, list)):
            return False
        
        return all([isinstance(state, DataBag) and all([hasattr(state, a) for a in element._planar_descriptors_]) for (state, element) in zip(states, self._objects_)])
            
    def _check_frame_states_(self, value):
        if not isinstance(value, dict):
            return False
        
        return all([isinstance(k, int) and self._check_state_(state) for (k, state) in value.items()])
        
    def addState(self, state):
        """Adds a copy of state to each of its objects.
        Use with CAUTION.
        
        """
        import core.datatypes as dt
        
        if len(self._objects_) == 0:
            raise RuntimeError("This path object has no elements")
        
        if not isinstance(state, DataBag):
            raise TypeError("state expected to be a datatypes.DataBag; got %s instead" % type(state).__name__)
        
        if not self._check_state_(state):                                       # make sure state complies with this planar type
            raise TypeError("state %s does not contain the required descriptors %s" % (state, self._planar_descriptors_))
        
        if not hasattr(state, "z_frame"):                                       # make sure state is conformant
            raise AttributeError("state is expected to have a z_frame attribute")
        
        for element, state in zip(self._objects_, states):
            element.addState(state.copy())
            
    #def mergeStates(self, other):
        #"""Adds the states of other Path to this Path.
        
        #The other Path must:
        #a) have the same number of elements as this one
        
        #b) have elements with just one state
        
        #The links between state and frame indices are managed as in PlanarGraphics.addState()
        
        #"""
        #if not isinstance(other, Path):
            #raise TypeError("Expecting a Path PlanarGraphics; got %s instead" % type(other).__name__)
        
        #if len(other) != len(self):
            #raise ValueError("The other Path has a different length (%d) from this one (%d)" % (len(other), len(self)))
        
        #if any([len(o.states) > 1 for o in other]):
            #raise ValueError("Elements in the other Path must have one state each")
        
        #for k, o in enumerate(self):
            #o.addState(other[k].states[0])
            
    def subpath(self, n):
        """Returns the nth subpath as a Path object, or self when there are no subpaths
        
        NOTE: The returned Path object contains REFERENCES, NOT COPIES, of the
        corresponding elements in this object.
        
        Precondition: 0 <= n < subpathCount
        
        """
        if not isinstance(n, int):
            raise TypeError("Expecting an int; got %s instead" % type(n).__name__)
        
        if self.subpathCount == 0:
            return self
        
        if n < 0 or n >= self.subpathCount:
            raise ValueError("%d is not a valid subpath index" % n )
        
        pathStarts = [k for k,p in enumerate(self._objects_) if isinstance(p, Move)]
        
        if n == self.subpathCount - 1:
            path_slice = slice(pathStarts[n], pathStarts[n+1])
            
        else:
            path_slice = slice(pathStarts[n], len(self._objects_))
            
        return self._objects_[path_slice]
    
    def remapFrameStateAssociations(self, newmaps):
        """Overrides PlanarGraphics.remapFrameStateAssociations, for Path objects.
        
        Re-asssigns frame links to PlanarGraphics elements in the Path.
        
        Parameters:
        ==========
        
        newmaps = sequence of new state-frame mappings with one mapping for each
                    element of the path
                    
                    The sequence mength must be equal to the number of elements 
                    in this Path.
                    
                    If an element of this Path is not a Path, the corresponding
                    element in the sequence must be a dict 
                    (see PlanarGraphics.remapFrameStateAssociations() )
                    
                    If an element of the Path is itself a Path (i.e., nested Path)
                    then the corresponding element of the sequence must be another 
                    sequence like newmaps, with as many elements as there are 
                    elements in the nested Path.
                    
                Elements where the corresponding dictionary in the sequence is 
                empty are left untouched.
        
        """
        if not isinstance(newmaps, (tuple, list)):
            raise TypeError("expecting a sequence (tuple or list); got %s instead" % type(newmap).__name__)
        
        if not all([isinstance(v, (tuple, list, dict)) for v in newmaps]):
            raise TypeError("Expecting a sequence of dict or sequences")
        
        if len(newmaps) != len(self._objects_):
            raise ValueError("Expecting as many elements in newmaps as there are in this object (%d); got %d instead" % (len(self._objects_), len(newmaps)))
        
        for k, o in self._objects_:
            o.remapFrameStateAssociations(newmaps[k]) # deleagate to element's remapping function
            
        #if update:
            #self.updateFrontends()
        
    
    @property
    def components(self):
        """Read-only property: the list of components of this Path object.
        
        Being a list, is not immutable!
        """
        return self._objects_

    @property
    def subpathCount(self):
        """Returns the number of subpaths.
        
        This is the number of Move elements minus one. 
        
        """
        return len([p for p in self._objects_ if isinstance(p, Move)])-1
    
    @property
    def nestedSubpathCount(self):
        return len([p for p in self.__obj_map__ is isinstance(p, Path)])
    
    @property
    def position(self):
        if len(self._objects_):
            x = min([e.x for e in self._objects_])
            y = min([e.y for e in self._objects_])
            
        else:
            x = 0
            y = 0
        
        self._position_ = (x,y)
        
        return self._position_
            
    @property
    def pos(self):
        position = self.position
        
        if any([p is None for p in position]):
            return QtCore.QPointF()

        return QtCore.QPointF(position[0], position[1])
            
    @property
    def x(self):
        """The "x" coordinate of the current state of this path.
        
        This is the minimum of all x positions of its elements, in the current 
        state.
        
        Together with "y" property, this defines the position of the entire
        path, in the current descriptor state
        """
        if len(self._objects_):
            states = self.getState(self.currentFrame)
            #states = [s for s in self.asPath(self.currentFrame) if s is not None]
            
            if len(states):
                x = min([s.x for s in states])
                
            else:
                x = 0
            
        else:
            x = 0
            
        return x
        
    @x.setter
    def x(self, value):
        if len(self._objects_):
            states = self.getState(self.currentFrame)
            if len(states):
                old_x = min([s.x for s in states])
                
                delta_x = value - old_x
                
                
                # NOTE: 2018-01-20 22:30:22
                # shift all elements horizontally, by the distance between
                # current x coordinate and value
                #NOTE: 2019-03-28 14:37:22 make sure ALL points in a spline are translated
                for s in states:
                    s.x += delta_x
                    
                    if "cx" in s:
                        s.cx += delta_x
                        
                    if "c1x" in s:
                        s.c1x += delta_x
                        
                    if "c2x" in s:
                        s.c2x += delta_x
                    
        # this is a tuple !
        self._position_ = (value, self._position_[1]) # (x=value, y)
        
    @property
    def y(self):
        """The "y" coordinate of the current state of this path's first element.
        
        This is the minimum of all y positions of its elements, in the current 
        state.
        
        Together with "x" property, this defines the position of the entire
        path, in the current descriptor state
        """
        if len(self._objects_):
            states = self.getState(self.currentFrame)
            #states = [s for s in self.asPath(self.currentFrame) if s is not None]
            if len(states):
                y = min([s.y for s in states])
                
            else:
                y = 0
            
        else:
            y = 0
            
        return y
        
    @y.setter
    def y(self, value):
        if len(self._objects_):
            states = self.getState(self.currentFrame)
            #states = [s for s in self.getState(self.currentFrame) if s is not None]
            #states = [s for s in self.asPath(self.currentFrame) if s is not None]
            
            if len(states):
                old_y = min([s.y for s in states])
                delta_y = value - old_y
        
                # NOTE: 2018-01-20 22:33:12
                # shift all elements vertically, by the distance between
                # current y coordinate and value
                
                for s in states:
                    s.y += delta_y
                    
                    if "cy" in s:
                        s.cy += delta_y
                        
                    if "c1y" in s:
                        s.c1y += delta_y
                        
                    if "c2y" in s:
                        s.c2y += delta_y
                    
        # this is a tuple!
        self._position_ = (self._position_[0], value) # (x, y=value)
        
    @property
    def maxFrameIndex(self):
        max_obj_frame = [o.maxFrameIndex for o in self._objects_]
        
        return max(max_obj_frame)
            
        
    @property
    def elementsFrameIndices(self):
        """Sequence of nested lists of frame indices, one per element in this Path.
        
        Nested Paths are given as nested lists at a deeper level.
        
        """
        if len(self._objects_):
            return [e.frameIndices for e in self._objects_]
        
        else:
            return []
    
    @elementsFrameIndices.setter
    def elementsFrameIndices(self, value):
        """Parameter MUST be a sequence of nested sequences, of the same length as self.
        
        Parametrs:
        ==========
        value:  One of:
                1) a list of elements, each as per PlanarGraphics.frameIndices()
                2) just one element as per PlanarGraphics.frameIndices()
                3) an empty list
                4) the list [None]
                5) None
            
                Case (1) requires a list with as many elements as there are in 
                the Path and for setting the frameIndices propery of each path
                element ("atomically").
                
                In this case, elements that are empty lists will leave the 
                corresponding path elements unchanged.
                Elements that are [None] or None, will set the corresponding path
                element to have one frameless state.
                
                Cases (2) - (5) set the frameIndices of every eleMent to a common
                set of values as per PlanarGraphics.frameIndices()
        
        See PlanarGraphics.frameIndices setter for details at Path element level.
        
        In addition, Path elements that are themselves a Path (i.e. nested Paths) 
        expect the corresponding element to have a similar structure to "value".
        
        """
        
        if isinstance(value, (range, dict, int, type(None))): # apply this element-wise
            for element in self._objects_:
                element.frameIndices = value
                
        elif isinstance(value, (tuple, list)):
            if len(value) == 0 or None in value: # e,pty values or has None => go element-wise
                for element in self._objects_:
                    element.frameIndices = value
                    
            elif all([isinstance(v, int) for v in value]): # also element-wise
                for element in self._objects_:
                    element.frameIndices = value
                    
            else: # go "atomically"
                if len(value) != len(self._objects_):
                    raise ValueError("For Path, Expecting a sequence with %d elements; got %d instead" % (len(self._objects_), len(value)))
                
                for k, e in enumerate(self._objects_):
                    if not isinstance(value[k], (tuple, list, dict, range, type(None))):
                        raise TypeError("At value[%d]: Expecting a sequence of nested sequences or None; got %s instead" % (k, type(e).__name__))
                        
                    if value[k] is None:
                        continue
                    
                    else:
                        if len(value[k]) == 0:
                            continue
                        
                        e.frameIndices = value[k] # delegate to element's function
                        
        else:
            raise TypeError("Cannot set frame indices with this parameter: %s" % value)
                
    @property
    def frameIndices(self):
        """List of unique frame indices that are associated with a state.
            Read-only; to change frames in the elements' states use elementsFrameIndices
        """
        from core.utilities import unique
        
        if len(self._objects_):
            return unique([f for f in itertools.chain(*[e.frameIndices for e in self._objects_])])
            #frlist = [e.frameIndices for e in self._objects_]
            
            #return unique([f for f in itertools.chain(*frlist)])
            #frndx = np.array([e.frameIndices for e in self._objects_]).flatten()
            #return list(np.unique(frndx[!np.isnan(frndx)]))
        
        else:
            return []
    
    @frameIndices.setter
    def frameIndices(self, value):
        """Parameter MUST be a sequence of nested sequences, of the same length as self.
        
        Parametrs:
        ==========
        value:  One of:
                1) a list of elements, each as per PlanarGraphics.frameIndices()
                2) just one element as per PlanarGraphics.frameIndices()
                3) an empty list
                4) the list [None]
                5) None
            
                Case (1) requires a list with as many elements as there are in 
                the Path and such that it will set the frameIndices property for
                each path element.
                
                In this case, elements that are empty lists will leave the 
                corresponding path elements unchanged.
                Elements that are [None] or None, will set the corresponding path
                element to have one frameless state, based on the current state.
                
                Cases (2) - (5) set the frameIndices of every element to a common
                set of values as per PlanarGraphics.frameIndices()
        
        See PlanarGraphics.frameIndices setter for details at Path element level.
        
        In addition, Path elements that are themselves a Path (i.e. nested Paths) 
        expect the corresponding element to have a structure similar to that of
        "value".
        
        """
        
        if isinstance(value, (range, dict, int, type(None))): # apply this element-wise
            for element in self._objects_:
                element.frameIndices = value
                
        elif isinstance(value, (tuple, list)):
            if len(value) == 0 or None in value: # e,pty values or has None => go element-wise
                for element in self._objects_:
                    element.frameIndices = value
                    
            elif all([isinstance(v, int) for v in value]): # also element-wise
                for element in self._objects_:
                    element.frameIndices = value
                    
            else: # go "atomically"
                if len(value) != len(self._objects_):
                    raise ValueError("For Path, Expecting a sequence with %d elements; got %d instead" % (len(self._objects_), len(value)))
                
                for k, e in enumerate(self._objects_):
                    if not isinstance(value[k], (tuple, list, dict, range, type(None))):
                        raise TypeError("At value[%d]: Expecting a sequence of nested sequences or None; got %s instead" % (k, type(e).__name__))
                        
                    if value[k] is None:
                        continue
                    
                    else:
                        if len(value[k]) == 0:
                            continue
                        
                        e.frameIndices = value[k] # delegate to element's function
                        
        else:
            raise TypeError("Cannot set frame indices with this parameter: %s" % value)
                
    @property
    def type(self):
        if all([isinstance(e, (Move, Line)) for e in self._objects_]):
            if len(self._objects_) == 2:
                return GraphicsObjectType.line
            
            elif len(self._objects_) == 4:
                if self.closed:
                    return GraphicsObjectType.rectangle
                
                else:
                    return GraphicsObjectType.polyline
            
            else:
                if self.closed:
                    return GraphicsObjectType.polygon
                
                else:
                    return GraphicsObjectType.polyline

        return GraphicsObjectType.path
        
    @property
    def states(self):
        """Returns a list of lists of states (one list per element)
        """
        # FIXME should this not be a list of states (as paths) instead?
        # as it is right now it returns a list with as many elements as there are
        # elements in the path, which is confusing;
        # a path's state should return a single-state path corresponding to the
        # queried state
        uniqe_frames = self.frameIndices
        
        return [p.states for p in self._objects_]
        
    @property
    def indexedStates(self):
        return [(k, p.states) for k, p in enumerate(self._objects_)]
        
    @property
    def currentFrame(self):
        return self._objects_[0].currentFrame
        
    @currentFrame.setter
    def currentFrame(self, value):
        if not isinstance(value, int):
            raise TypeError("expecting an int; got %s instead" % type(value).__name__)
        
        for e in self._objects_:
            e.currentFrame = value
            
    #@property
    #"def" currentStateIndexed(self):
        #"""A list of (index, state) tuples.
        
        #"index" is the index of the element in this Path (taken as list) 
        #"state" is the index of the element of this Path object.
        
        #The states are taken from the PlanarGraphics elements that
        #compose this Path object, provided that they have a state
        #associated with the current frame. 
        
        #Elements that do NOT have a state given the current frame are skipped. 
        
        #In the extreme case where none of  this Path's elements have a defined 
        #state for the current frame, the returned list will be empty.
        
        #"""
        #return [(k, p.currentState) for k, p in enumerate(self._objects_) if p.currentState is not None] # may be empty
        
    @property
    def currentState(self):
        """ A list of states.
        
        As for the currentStateIndexed property, the states are taken from the
        PlanarGraphics elements that compose this Path object, provided that they
        have a state associated with the current frame. 
        
        Elements that do NOT have a state given the current frame are skipped. 
        
        In the extreme case where none of this Path's elements have a defined 
        state for the current frame, the returned list will be empty.
        
        """
        raise NotImplementedError("Path object do not support this method")
        #return [p.getState(self._currentframe_) for p in self._objects_] # may be empty
        
    @property
    def closed(self):
        return self._closed_
    
    @closed.setter
    def closed(self, value):
        if not isinstance(value, bool):
            raise TypeError("value expected to be a boolean; got %s instead" % type(value).__name__)
        
        if value:
            self.append(Line(self._objects_[0].x, self._objects_[0].y))
            
        else:
            # remove last element (break-up path)
            if self._objects_[-1].x == self._objects_[0].x and self._objects_[-1].y == self._objects_[0].y:
                del self._objects_[-1]
                
        self._closed_ = value
        
    def closePath(self):
        self.closed = True
        
    def openPath(self):
        self.closed = False
    
    def qGraphicsItem(self, pointSize=1, frame=None):
        path = self(path=None,frame=self.currentFrame, closed = self._closed_)
        
        return QtWidgets.QGraphicsPathItem(path)
    
    def qPoints(self, frame=None):
        if frame is None:
            state = self.currentState # the common state or the state associated with current frame, if present
            
        else:
            if frame in self.frameIndices:
                state = self.getState(frame)
                
            else:
                warnings.warn("%s.qPoints(): No state is associated with specified frame (%d)" % (self.__class__.__name__, frame), stacklevel=2)
                return [QtCore.QPointF()]
        
        if state is None or len(state) == 0:
            warnings.warn("%s.qPoints(): Undefined state" % self.__class__.__name__, stacklevel=2)
            return [QtCore.QPointF()]
        
        points = list()
        for e in self._objects_:
            points.append(e.qPoint())
                
        return points
        
    def setParameter(self, name, value, frame=None):
        raise NotImplementedError("Path objects do not support this method")
    
    def propagateFrameState(self, frame, destframes):
        """Propagate the states at specified frame, to destframes
        """
        
        for o in self:
            if isinstance(o, Path):
                o.propagateFrameState(frame, destframes)
                
            else:
                if frame in o.frameIndices:
                    state = o.getState(frame)
                    o.propagateFrameState(state, destframes)
                
    def hasStateForFrame(self, frame):
        return any([o.hasStateForFrame(frame) for o in self])
        
    def getObjectForFrame(self, frame):
        return self.asPath(frame)
    
    def asPath(self, frame=None, closed=False):
        """Returns a Path object containg COPIES of only those elements in self that have a state defined for the specified frame
        
        frame: int (frame index)
        
        """
        return Path([e.getObjectForFrame(frame) for e in self if e.hasStateForFrame(frame)])
        
        #if len(elements):
            #if allStates:
                #return Path(elements)
            
            #else:
                #ee = [e.getObjectForFrame(frame) for e in elements]
                #return Path(ee)
                    
    def getState(self, frame):
        """Returns a list of states that are defined for the specified frame.
        
        A state is defined for the specified frame if either:
        * its z_frame == frame
        * its z_frame is None
        
        The result is a list of state references.
        
        """
        states = [e.getState(frame) for e in self._objects_] # references
        states = [s for s in states if s is not None]
        
        return states
        #raise NotImplementedError("Path objects do not support this method; use asPath()")
    
    #def getFrameStateIndexed(self, frame):
        #return [(k, p.getState(frame)) for k,p in enumerate(self._objects_) if p.getState(state) is not None] # may be empty
        
    def removeState(self, value):
        for o in self._objects_:
            o.removeState(value)
        #raise NotImplementedError("Path objects do not support this method")
            
    def controlPoints(self, frame=None):
        ret = list()
        
        for o in self:
            ret += list(o.controlPoints(frame))
            
        return tuple(ret)
        
    def asControlPath(self, frame=None):
        """Returns a Path that represents a polyline connecting all control points.
        """
        ret = Path()
        
        cp = self.controlPoints(frame)
        
        for k, p in enumerate(cp):
            if k == 0:
                ret.append(Move(p[0],p[1]))
                
            else:
                ret.append(Line(p[0],p[1]))
        return ret
        
    def fromControlPath(self, path, frame=None):
        if not isinstance(path, Path):
            raise TypeError("path argument expected to be a Path; got %s instead" % type(path).__name__)
        
        if frame is None:
            state = self.currentState
            
        else:
            state = self.getState(frame)
        
        if state is None or len(state) == 0:
            return
        
        control_state = path.currentState
        
        if control_state is None or len(control_state) == 0:
            return
        
    def linkFrames(self, value):
        if not isinstance(value, (tuple, list)):
            raise TypeError("Path.linkFrame() expects a sequence")
        
        if len(value) != len(self._objects_):
            raise ValueError("Path.linkFrame() expects a sequence with as many elements as there are elements in the Path")
        
        for k,o in enumerate(self._objects_):
            if value[k] is not None and len(value[k]):
                o.linkFrames(value[k]) # o.linkFrame() may raise its own error.
    
    def objectForFrame(self, frame):
        """See PlanarGraphics.objectForFrame
        """
        if self.hasStateForFrame(frame):
            ret = Path()
            for p in self:
                ret.append(p.objectForFrame(frame))
            
            ret.name = "copy of %s for frame %d" % (self.name, frame)
                
        else:
            ret = None
            
        return ret
            
    def adoptPainterPath(self, p):
        """Re-composes this Path from a (possibly different) QPainterPath object.
        
        The (new) Path will be composed of Tier 1 primitives (MoveTo, LineTo and CubicTo)
        
        NOTE: This operates on the state of its elements, associated with the 
        current frame or on the common state, if no frame-state association exists
        """
        
        if not isinstance(p, QtGui.QPainterPath):
            raise TypeError("Expecting a QPainterPath; instead got %s" % (type(p).__name__))
        
        frameindex = self.frameIndices
        currentframe = self.currentFrame
        
        self.clear()
        
        #controlPoints = [None, None] # what's this for?
        
        for k in range(p.elementCount()): # does not parse CurveToDataElement objects
            if p.elementAt(k).type == QtGui.QPainterPath.MoveToElement:
                element = p.elementAt(k)
                self.append(Move(element.x, element.y, frameindex=frameindex, currentframe=currentframe))
                
            elif p.elementAt(k).type == QtGui.QPainterPath.LineToElement:
                element = p.elementAt(k)
                self.append(Line(element.x, element.y, frameindex=frameindex, currentframe=currentframe))
                
            elif p.elementAt(k).type == QtGui.QPainterPath.CurveToElement:
                element = p.elementAt(k)
                c1 = p.elementAt(k+1)
                c2 = p.elementAt(k+2)
                self.append(Cubic(x=c1.x, y=c1.y, c1x=c2.x, c1y=c2.y, c2x=element.x, c2y=element.y, frameindex=frameindex, currentframe=currentframe))
                
            #else: # do not parse curve to data elements
                #continue 

class MouseEventSink(QtCore.QObject):
    def __init__(self, *args, **kwargs):
        super(MouseEventSink, self).__init__(*args, **kwargs)
        
    def eventFilter(self, obj, evt):
        if evt.type() in (QtCore.QEvent.GraphicsSceneMouseDoubleClick, QtCore.QEvent.GraphicsSceneMousePress, QtCore.QEvent.GraphicsSceneMouseRelease, \
                          QtCore.QEvent.GraphicsSceneHoverEnter, QtCore.QEvent.GraphicsSceneHoverLeave, QtCore.QEvent.GraphicsSceneHoverMove, \
                          QtCore.QEvent.GraphicsSceneMouseMove):
            return True
        
        else:
            return False
            #return QtCore.QObject.eventFilter(obj, evt)
    
class Planar2QGraphicsManager(QtCore.QObject):
    """Each planar graphics object can be displayed by several graphics objects.
    e.g. one ROI or Cursor can be shown in several image windows.
    
    The planar descriptors of the planar graphics object can thus be manipulated
    in two ways:
    
    a) programmatically (by directly calling appropriate setter functions of the
        planar graphics object) -- in this case, ALL of the "connected" graphics
        objects used for displaying the planar graphics object need to be updated
        to reflect the new planar graphics object state, AVOIDING re-entrant
        code loops: the updaing of the graphics objects must not trigger a new
        update of the planar graphics object
        
    b) by GUI interaction with the any of the graphics objects used for displaying
        the planar graphics object -- in this case, the descriptors of the planar
        graphics object must be updated accordingly AVOIDING re-entrant code
        loops: i.e. when a graphics object has changed, the states of the 
        corresponding planar  graphics object must be updated, and this must be 
        reflected in all of the graphics objects used for display EXCEPT for the
        one that initiated the change.
        
    
    """
    sig_planar_changed = pyqtSignal(name="sig_planar_changed")
    
    def __init__(self, planarobject=None, grobject=None, parent=None):
        super(Planar2QGraphicsManager, self).__init__(parent=parent)
        
        if not isinstance(planarobject, (PlanarGraphics, type(None))):
            raise TypeError("planarobject expected to be a PlanarGraphics object or None; got %s instead" % type(planarobject).__name__)
        
        if not isinstance(grobject, (GraphicsObject, type(None))):
            raise TypeError("grobject expected to be a GraphicsObject or None; got %s instead" % type(grobject).__name__)
        
        # NOTE: 2019-03-09 10:44:55
        # one planar graphics object to many graphics objects: use the planarobject
        # as key to a set of graphics objects (ensure unique elements)
        
        # NOTE: 2019-03-09 10:47:01
        # should we accept ONLY ONE PlanarGraphics object in this ?
        # YES: KISS!!!
        self.__obj_map__ = dict()
        
        if isinstance(planarobject, PlanarGraphics):
            self.__obj_map__[planarobject] = set()
            
            if isinstance(grobject, GraphicsObject):
                self.__obj_map__[planarobject].add(grobject)
                
    def register(self, planarobject=None, grobject=None):
        if not isinstance(planarobject, (PlanarGraphics, type(None))):
            raise TypeError("planarobject expected to be a PlanarGraphics objetc or None; got %s instead" % type(planarobject).__name__)
        
        if not isinstance(grobject, (GraphicsObject, type(None))):
            raise TypeError("grobject expected to be a GraphicsObject or None; got %s instead" % type(grobject).__name__)
        
        if isinstance(planarobject, PlanarGraphics):
            if planarobject not in self.__obj_map__:
                self.__obj_map__[planarobject] = set()
                
            if isinstance(grobject, GraphicsObject):
                self.__obj_map__[planarobject].add(grobject)
                
    def deregister(self, planarobject, grobject=None):
        if not isinstance(planarobject, PlanarGraphics):
            raise TypeError("planarobject expected to be a PlanarGraphics; got %s instead" % type(planarobject).__name__)
        
        if not isinstance(grobject, (GraphicsObject, type(None))):
            raise TypeError("grobject expected to be a GraphicsObject or None; got %s instead" % type(grobject).__name__)
        
        if planarobject in self.__obj_map__: # implies self.__obj_map__ is not empty
            if isinstance(grobject, GraphicsObject) and grobject in self.__obj_map__[planarobject]:
                self.__obj_map__[planarobject].discard(grobject)
                
            elif grobject is None:
                self.__obj_map__.pop(planarobject, None)
        
    def slot_graphics_changed(self):
        # connect this to appropiate sgnal emitted by the graphics object
        pass
        
    def planar_changed_callback(self):
        # call this from the planar object
        pass
        
class GraphicsObject(QtWidgets.QGraphicsObject):
    """Graphical object that displays PlanarGraphics objects using Qt Framework classes.
    FIXME
    TODO Logic for building/editing ROIs is broken for ellipse -- why?
    TODO check cachedPath logic
    
    NOTE: 2019-03-09 10:05:30
    the correspondence between the display object and the PlanarGraphics object
    is to be managed by an instance of Planar2QGraphicsManager
        
    NOTE: 2018-01-17 21:56:23
    currentframe and framesVisibility __init__() parameters cached to be 
    available when exiting build mode (i.e., from within __finalizeShape__)
         
         
    TODO: when building a shape, by default the resulting backend has no frame-state
    association; we must then give the option to associate states with certain frame
        
        
    NOTE: 2018-01-19 09:49:04 DONE
    x and y properties correctly update self.backend x and y
    
    NOTE: 2018-01-19 17:04:36
    TODO: curent frame might have to be managed independently, to allow more flexibility
    on linked cursors:
    
        now, several GUI cursors (frontends) can be referenced by a common backend
        however, image viewer windows are not necessarily "linked" i.e., one may
        be able to view a different image frames in different windows.
        
        The issue is whaty happens when a window shows a frame for which backend 
        has descriptor state, but another window shows a frame where the (same)
        backend does NOT have a descriptor state. Clearly, in the latter, the cursor
        is NOT visible -- DONE. However, when changing frames in a window this also 
        sets the backend's currentFrame to that value
    
    NOTE: All the action in build mode happens in the mouse event handlers
    
    Encapsulates the GUI conterpart ("frontend") of the PlanarGraphics objects
    defined in this module. In turn the PlanarGraphics obejcts are the "backend" 
    of the GraphicsObject.
    
    The PlanarGraphics objects are in a one-to-many relationship with GraphicsObject
    objects: several GraphicsObject objects may subserve (i.e. graphically display)
    the same PlanarGraphics object. It follows that the same PlanarGraphics object
    may be displayed by several GraphicsObject objects, each in its own graphics 
    scene.
    
    The PlanarGraphics -- GraphicsObject entity can be constructed from both 
    directions:
    
    a) constructing a GraphicsObject parametrically (i.e. from planar descriptors 
    as per the __init__() signature of the GraphicsObject) generates a PlanarGraphics
    backend automatically
    
    b) constructing a PlanarGraphics object then displaying it in a scene (by 
    calling the appropriate addGraphicsObject method in ImageViewer) will generate
    a GraphicsObject frontend in that image viewer's scene.
    
    From the GUI, the user can manipulate the frontend directly (mouse and key
    strokes) whereas the backends can only be are manipulated indirectly (via their 
    frontends).
    
    
    
    The following graphical types are supported (see the GraphicsObjectType enumeration):

    vertical_cursor     = 1     
    horizontal_cursor   = 2     
    crosshair_cursor    = 4     
    point_cursor        = 8     
    point               = 16    
    line                = 32    
    polyline            = 64
    rectangle           = 128   
    polygon             = 256   
    ellipse             = 512   
    quad                = 1024
    cubic               = 2048
    arc                 = 4096
    arcmove             = 8192
    path                = 16384 
    text                = 32768 
    
    lineCursorTypes     = vertical_cursor       | horizontal_cursor
    shapedCursorTypes   = lineCursorTypes       | crosshair_cursor
    allCursorTypes      = shapedCursorTypes     | point_cursor
    
    linearTypes         = line                  | polyline
    polygonTypes        = rectangle             | polygon 
    linearShapeTypes    = polygonTypes          | linearTypes
    arcTypes            = arc                   | arcmove
    curveTypes          = ellipse               | arcTypes
    basicShapeTypes     = linearShapeTypes      | curveTypes
    commonShapeTypes    = basicShapeTypes       | point
    geometricShapeTypes = commonShapeTypes      | path
    allShapeTypes       = geometricShapeTypes   | text
    
    allObjectTypes      = allCursorTypes        | allShapeTypes
  
    Any combination of these flags can be used to determine the type of the
    GraphicsObject instance or its inclusion in the subsets above, using 
    logical AND (&).
    
    e.g. self.objectType & allCursorTypes returns > 0 if the object is a cursor type
    
    Non-cursor types are rendered by means of QAbstractGraphicsShapeItem. This means
    that except for text, path, point and line, the generated shaped are always closed
    (in particular the polygons).
    
    To generate open polygons use the "path" type with QPainterPaths to draw 
    an open polygon (in Qt a polygon is considered "open" if the two extreme 
    points have different coordinates).
        
    """
    
    nonCursorTypes      = GraphicsObjectType.allShapeTypes
    
    #allObjectTypes      = allCursorTypes                        | allShapeTypes
    
    #undefinedType       = 0
    
        
    # this is for Qt Graphics View Framework RTTI logic
    Type = QtWidgets.QGraphicsItem.UserType + GraphicsObjectType.allObjectTypes
    
    signalPosition = pyqtSignal(int, str, "QPointF", name="signalPosition")
    
    # used to notify the cursor manager (a graphics viewer widget) that this cursor has been selected
    selectMe = pyqtSignal(str, bool, name="selectMe") 
    
    signalGraphicsObjectPositionChange = pyqtSignal("QPointF", name="signalGraphicsObjectPositionChange")
    
    # it is up to the cursor manager (a graphics viewer widget) to decide what 
    # to do with this (i.e., what menu & actions to generate)
    requestContextMenu = pyqtSignal(str,QtCore.QPoint, name="requestContextMenu")
    
    signalROIConstructed = pyqtSignal(int, str, name="signalROIConstructed")
    
    signalBackendChanged = pyqtSignal(object, name="signalBackendChanged")
    
    signalIDChanged = pyqtSignal(str, name="signalIDChanged")
    

    # NOTE: 2017-08-08 22:57:15 TODO:
    # API change to allow various graphic object types
    # NOTE: regular shape items as in QAbstractGraphicsShapeItem derivatives:
    # QGraphicsLineItem - straight lines, or points (a <<VERY>> short line)
    # QGraphicsEllipseItem - ellipse, circle and arcs of ellipse or circle, or point (a <<VERY>> small circle)
    # QGraphicsRectItem - rectangle, square, point (a <<VERY>> small square)
    # QGraphicsPolygonItem -- polygons
    # QGraphicsPathItem --  any path
    #
    # Requirements for construction:
    # (these are for pre-defined cursors and ROIs, for 
    #  interactively defining a ROI, see notes for buildMode)
    #
    # for cursors (of any type) -- 6-tuple (width, height, radius, winX, winY, cursor_type)
    # for ellipse (including circles), rectangles (including squares): 5-tuple (x, y, width, height, shape_type)
    # for arcs: 6-tuple (x, y, width, height, startAngle, spanAngle) => pies
    # for lines: 5-tuple (x1, y1, x2, y2, shape_type)
    # for generic path: I could fallback to the datatypes.ScanROI contructor rules to generate a QPainterPath
    #
    # Drawing mechanisms:
    # TODO: __drawObject__ to delegate
    # for cursors -- TODO: __drawCursor__ should only contain code for cursor drawing
    # for other QAbstractGraphicsShapeItem objects:
    #                TODO: construct a member QAbstractGraphicsShapeItem object
    #                       use its path(), shape(), boundingRect() functions
    
    # NOTE: 2018-01-15 22:38:58
    # To align GraphicsObject API with PlanarGraphics API the following parameters
    # have been removed from the GraphicsObject c'tor, as being redundant: 
    # visibleInAllFrames
    # linkedToFrame
    #
    # When frameVisibility is an empty list, the GraphicsObject becomes visible 
    # in all available frames and its backend (a PlanarGraphics object) has a 
    # common status. Furthermore, in this case various planar descriptors have 
    # the same value in _ALL_ frames (as if linkedToFrame was False)
    #
    # Conversely, when frameVisibility is not empty, the GraphicsObject frontend
    # is visible ONLY in the frame indices listed there, and its PlanarGraphics
    # backend has frame-state associations. Implicitly, changing the value of 
    # planar graphic descriptors in one frame are reflected in that frame only
    # (as if linkedToFrame was True).
    #
    # To be able to modify planar descriptor values in a frame-specific manner,
    # then set frameVisibility to the list of _ALL_ frame indices in the data.
    
    def __setup_default_appearance__(self):
        self.defaultTextBackgroundBrush = QtGui.QBrush(QtCore.Qt.white, QtCore.Qt.SolidPattern)
        self.defaultBrush = QtGui.QBrush(QtCore.Qt.white, QtCore.Qt.SolidPattern)
        
        self.defaultTextPenWidth = 1
        
        self.defaultPenWidth = 1
        
        self.defaultPenStyle = QtCore.Qt.DashLine
        self.defaultSelectedPenStyle = QtCore.Qt.SolidLine
        
        self.defaultColor = QtCore.Qt.magenta
        self.defaultCBCursorColor = QtCore.Qt.red
        self.defaultLinkedCursorColor = QtCore.Qt.darkMagenta
        
        self.defaultTextPen   = QtGui.QPen(self.defaultColor, self.defaultTextPenWidth, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
        self.defaultTextBrush = QtGui.QBrush(self.defaultColor, QtCore.Qt.SolidPattern)

        self.defaultLinkedTextPen   = QtGui.QPen(self.defaultLinkedCursorColor, self.defaultTextPenWidth, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
        #self.defaultLinkedTextPen   = QtGui.QPen(QtCore.Qt.black, self.defaultTextPenWidth, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
        self.defaultLinkedTextBrush = QtGui.QBrush(self.defaultLinkedCursorColor, QtCore.Qt.SolidPattern)
        
        # NOTE: 2018-06-23 17:21:06
        # "CB stands for "CommonBackend"
        self.defaultCBTextPen = QtGui.QPen(self.defaultCBCursorColor, self.defaultTextPenWidth, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
        self.defaultCBTextBrush = QtGui.QBrush(self.defaultCBCursorColor, QtCore.Qt.SolidPattern)
        
        self.defaultTextFont = QtGui.QFont("sans-serif")
        
        self.defaultPen = QtGui.QPen(self.defaultColor)
        self.defaultPen.setStyle(self.defaultPenStyle)
        self.defaultPen.setWidth(self.defaultPenWidth)
        self.defaultPen.setCapStyle(QtCore.Qt.RoundCap)
        self.defaultPen.setJoinStyle(QtCore.Qt.RoundJoin)
        
        self.defaultSelectedPen = QtGui.QPen(self.defaultColor)
        self.defaultSelectedPen.setStyle(self.defaultSelectedPenStyle)
        self.defaultSelectedPen.setWidth(self.defaultPenWidth)
        self.defaultSelectedPen.setCapStyle(QtCore.Qt.RoundCap)
        self.defaultSelectedPen.setJoinStyle(QtCore.Qt.RoundJoin)
        
        self.defaultLinkedPen = QtGui.QPen(self.defaultLinkedCursorColor)
        self.defaultLinkedPen.setStyle(self.defaultPenStyle)
        self.defaultLinkedPen.setWidth(self.defaultPenWidth)
        self.defaultLinkedPen.setCapStyle(QtCore.Qt.RoundCap)
        self.defaultLinkedPen.setJoinStyle(QtCore.Qt.RoundJoin)
        
        self.defaultLinkedSelectedPen = QtGui.QPen(self.defaultLinkedCursorColor)
        self.defaultLinkedSelectedPen.setStyle(self.defaultSelectedPenStyle)
        self.defaultLinkedSelectedPen.setWidth(self.defaultPenWidth)
        self.defaultLinkedSelectedPen.setCapStyle(QtCore.Qt.RoundCap)
        self.defaultLinkedSelectedPen.setJoinStyle(QtCore.Qt.RoundJoin)
        
        self.defaultCBPen  = QtGui.QPen(self.defaultCBCursorColor)
        self.defaultCBPen.setStyle(self.defaultPenStyle)
        self.defaultCBPen.setWidth(self.defaultPenWidth)
        self.defaultCBPen.setCapStyle(QtCore.Qt.RoundCap)
        self.defaultCBPen.setJoinStyle(QtCore.Qt.RoundJoin)
        
        self.defaultCBSelectedPen = QtGui.QPen(self.defaultCBCursorColor)
        self.defaultCBSelectedPen.setStyle(self.defaultSelectedPenStyle)
        self.defaultCBSelectedPen.setWidth(self.defaultPenWidth)
        self.defaultCBSelectedPen.setCapStyle(QtCore.Qt.RoundCap)
        self.defaultCBSelectedPen.setJoinStyle(QtCore.Qt.RoundJoin)
    
    def __init__(self, 
                 parameters=None, 
                 pos=None, 
                 objectType=GraphicsObjectType.allShapeTypes,
                 currentFrame=0, 
                 visibleFrames = [], 
                 label=None, 
                 labelShowsPosition=True, 
                 showLabel=True,
                 parentWidget=None):
                 
        """
        Named parameters:
        =================
        
        objectType : one of the GraphicsObjectType enum values
                    default is GraphicsObject.allShapeTypes
                    
                    See table below for the types defines in this enum
                    
        parameters: see table below; default is None; 
                    
                    When None or an empty list:
                    (1) if objectType is nonCursorTypes this triggers the 
                        interactive drawing logic.
                        
                    (2) if objectType is a cursor type, raises an error
        
        "objectType":     Enum value: Type of "parameters" argument:
        ========================================================================
        vertical_cursor   1           numeric 5-tuple (W, H, xWin, yWin, radius)
        horizontal_cursor 2           numeric 5-tuple (W, H, xWin, yWin, radius)
        crosshair_cursor  4           numeric 5-tuple (W, H, xWin, yWin, radius)
        point_cursor      8           numeric 5-tuple (W, H, xWin, yWin, radius)
        point             16          numeric triple  (X, Y, radius)
        line              32          numeric 4-tuple (X0, Y0, X1, Y1) or QLineF
        rectangle         64          numeric 4-tuple (X,  Y,  W,  H)  or QRectF
        ellipse           128         numeric 4-tuple (X,  Y,  W,  H)  or QRectF
        polygon           256         sequence of numeric pairs (X, Y) or sequence of QPointF
        path              512         QPainterPath or a sequence of two-element tuples, where:
                                        element 0 is a str one of: "move", "start", "line", "curve", or "control"
                                        element 1 is a tuple of coordinates (x,y)
                                        
                                        each "curve" element MUST be followed by two "control" elements
                                            
        text              1024        str
        ========================================================================
        
        In addition, the GraphicsObject :class: also defines :class: members
        with values resulted from logical OR of various GraphicsObjectType members
        
        lineCursorTypes     = GraphicsObjectType.vertical_cursor    | GraphicsObjectType.horizontal_cursor
        shapedCursorTypes   = lineCursorTypes                       | GraphicsObjectType.crosshair_cursor
        allCursorTypes      = shapedCursorTypes                     | GraphicsObjectType.point_cursor
        
        polygonTypes        = GraphicsObjectType.rectangle          | GraphicsObjectType.polygon 
        linearShapeTypes    = polygonTypes                          | GraphicsObjectType.line
        basicShapeTypes     = linearShapeTypes                      | GraphicsObjectType.ellipse
        commonShapeTypes    = basicShapeTypes                       | GraphicsObjectType.point
        geometricShapeTypes = commonShapeTypes                      | GraphicsObjectType.path
        allShapeTypes       = geometricShapeTypes                   | GraphicsObjectType.text
        nonCursorTypes      = allShapeTypes
        
        allObjectTypes      = allCursorTypes                        | allShapeTypes
    
        pos:    QtCore.QPoint or QtCore.QPointF, or None; default is None, which places 
        it at the scene's (0,0) coordinate
        
        roiId: str or None (default is None): this sets a default ID for the object
                
                NOTE: when None, the object will get its ID from the type
                
                NOTE: this is NOT the variable name under which this object is
                bound in the caller's namespace
                
        label: str or None (defult): this is what may be shown as cursor label 
            (the default is to show its own ID, if given)
        
        currentFrame and visibleFrames -- used only for parametric c'tor
            
        """
        #NOTE: 2017-11-20 22:57:21
        # backend for non-cursor types is self._graphicsShapedItem
        # whereas in cursor typeself._graphicsShapedItem is None !!!
        
        super(QtWidgets.QGraphicsObject, self).__init__()
        
        
        if not isinstance(parentWidget, QtWidgets.QWidget) and type(parentWidget).__name__ != "GraphicsImageViewerWidget":
            raise TypeError("'parentWidget' expected ot be a GraphicsImageViewerWidget; got %s instead" % (type(self._parentWidget).__name__))
        
        self._parentWidget = parentWidget
        
        if not isinstance(objectType, (int, GraphicsObjectType)):
            raise TypeError("Second parameter must be an int or a GraphicsObjectType; got %s instead" % (type(objectType).__name__))
        
        self.__setup_default_appearance__()
        # NOT: 2017-11-24 22:30:00
        # assign this early
        # this MAY be overridden in __parse_parameters__
        self._objectType = objectType # an int or enum !!!
        
        # NOTE: this is the actual string used for label display; 
        # it may be suffixed with the position if labelShowsPosition is True
        self._displayStr= "" 
        self._ID_ = ""
            
        # check for frameVisibility parameter
        # execute this in the __parse_parameters__ function so that we can 
        # distinguish between the case where we construct a GraphicsObject from 
        # a PlanarGraphics backend (and therefore frame visibility is given by 
        # the backend's frame-state associations) and the case where we construct
        # a GraphicsObject parametrically (thus constructing a new backend from 
        # scratch, hence we need frameVisibility parameter to set up the backend's
        # frame-state associations)

        # see qt5 examples/widgets/painting/pathstroke/

        self._pointSize = 5
        self._c_penWidth = 1
        self._c_penStyle = QtCore.Qt.SolidLine
        
        # NOTE: 2018-01-17 15:33:58
        # used in buildMode or editMode; applies to non-cursor objects only
        #self._c_shape_point         = -1
        self._c_activePoint         = -1 # shape point editing - used in edit & build modes
        self._c_activeControlPoint  = -1 # path control point editing; valid values are 0 and 1
        self._control_points        = [None, None]  # used in curve (cubic, quad) segment building for path ROIs
        self._constrainedPoint      = None
        self._hover_point           = None    # because a null QPointF is still valid:
        self._movePoint             = False
        
        # CAUTION make sure this is empty after exit from build or edit modes
        # ATTENTION NO subpaths allowed in cached path (for the moment) = use only
        # non-path ("primitive") PlanarGraphics objects as elements
        # CAUTION this ALWAYS  has a commonState (i.e. we cache it for the currently
        # displayed frame)

        # exists throughtout the lifetime of self.
        # must not be empty
        # generated in the following circumstances:
        # 1) __finalizeShape__ after exit from build mode
        # 2) __parse_parameters__ when _objectType is not a cursor
        #   either when object is build parametrically, or when it is derived from
        #   a backend. 
        #   depending on _objectType, _cachedPath may contain a copy of the backend
        #   itself, or a "control" path (containing control points & lines)
        #   
        # WARNING the cached path can contain only Move, Line, Cubic and Quad objects !!!
        #   e.g., for a rectangle or ellipse, the control line (used in building & editing)
        #   is in fact the diagonal or one of the diameters, respectively
        
        self.__cachedPath__ = Path()
        
        self._shapeIsEditable       = False # control point editing
        self._movable               = True # moveable by mouse or keyboard
        self._editable              = True # switching to edit mode allowed
        self._transformable         = False # rotation & skewing
        self._buildMode             = False
        self._showlabel             = showLabel
        self._opaqueLabel = True
        self._curveBuild = False
        
        # NOTE: 2017-06-29 08:32:11
        # flags when a new position change sequence has begun (the previous 
        # sequence, if any, ended with a mouse release event)
        self._positionChangeHasBegun = False
        
        
        # NOTE: 2017-11-23 00:08:04
        # unlike non-cursor types, cursors are NOT back-ended by a QGraphicsItem
        # but rather directly painted by self.paint() method
        # the flag below toggles the cursor painting ON / OFF
        # TODO sync me with current frame cf self._frameindex
        self.__objectVisible__ = True
        
        self._labelShowsCoordinates = labelShowsPosition
        
        #self._x = 0
        #self._y = 0
        
        #self._width = None
        #self._height = None
        #self._xw = 0
        #self._yw = 0
        #self._r = 0
        self._wbarPos = QtCore.QPointF() # planar descriptor for cursor width bar; NOT stored in the backend
        
        # NOTE: 2017-06-28 17:19:20
        # used as a flag to know when itemChange has been called the first time
        # when object is a cursor type
        self._deltaPos = QtCore.QPointF()# NOT stored in the baskend

        # NOTE: 2017-06-30 13:52:03
        # used for linked cursors logic, when object if a cursor type
        self._oldPos = QtCore.QPointF() # NOT stored in the backend
        
        # elements of cursor types - do NOT use _graphicsShapedItem here
        # because the Qt GraphicsView system will be decorate its bounding rect 
        # when selected
        self._vline     = QtCore.QLineF() # vertical cursor line
        self._hline     = QtCore.QLineF() # horizontal cursor line
        self._hwbar     = QtCore.QLineF() # vertical cursor window line
        self._vwbar     = QtCore.QLineF() # horizontal cursor window line
        self._crect     = QtCore.QRectF() # point cursor central rect
        self._wrect     = QtCore.QRectF() # point and crosshair cursor window rect

        self._labelRect = QtCore.QRectF() # a Null rectangle!!!
        self._labelPos  = QtCore.QPointF()
        
        self.__backend__ = None

        self.__parse_parameters__(parameters, pos, visibleFrames, currentFrame)
        
        # ###
        # BEGIN ID and label management
        # ###
        
        # NOTE: bring names under a common value and KISS!
        # use same string for ID, label (the prefix of the display string) and backend name
        
        # if ID is given in the constructor, use it for self._ID_; else, generate it from object type
        #
        # if label is given in the constructor, use it for label, and for the ID !!!;
        #
        # else, if there is a backend and the backend has a name, use this as a label
        #
        # otherwise, use the ID for both label and backend name
        
        
        if isinstance(label, str) and len(label.strip()) > 0: 
            # label passed as __init__ parameter overrides => set name for backend too
            self._ID_ = label
            if self.__backend__ is not None:
                self.__backend__.name = self._ID_
                self.__backend__.updateLinkedObjects()
            
        else:
            # no label passed at __init__; 
            if self.__backend__ is not None and isinstance(self.__backend__.name, str) and len(self.__backend__.name.strip()):
                # if backend exists, use its name as ID
                self._ID_ = self.__backend__.name
                
            else:
                if isinstance(self._objectType, int):
                    try:
                        self._ID_ = GraphicsObjectType(self._objectType).name
                        
                    except:
                        self._ID_ = "graphics_object"
                        
                else:
                    self._ID_ = self._objectType.name
                    
        #if self.__backend__ is not None:
            #if self.__backend__.name is None or (isinstance(self.__backend__.name, str) and len(self.__backend__.name) == 0):
                #self.__backend__.name = self._ID_
                #self.__backend__.updateLinkedObjects()
                
        #self._displayStr= "" 
            
        # ###
        # END ID and label manageent
        # ###

        # NOTE: 2018-01-26 10:07:28
        # use a list of backends !!!
        self._linkedGraphicsObjects = list()
                
        self._isLinked = len(self._linkedGraphicsObjects)>0
        
        self._textPen               = self.defaultTextPen
        self._textBrush             = self.defaultTextBrush
        self._textBackgroundBrush   = self.defaultTextBackgroundBrush
        self._textCBPen             = self.defaultCBTextPen
        self._textCBBrush           = self.defaultCBTextBrush
        
        self._textFont              = self.defaultTextFont
        
        self._linkedTextPen         = self.defaultLinkedTextPen
        self._linkedTextBrush       = self.defaultLinkedTextBrush
        
        self._cursorPen             = self.defaultPen
        self._selectedCursorPen     = self.defaultSelectedPen
        
        self._linkedPen             = self.defaultLinkedPen
        self._linkedSelectedPen     = self.defaultLinkedSelectedPen
        
        self._cBPen                 = self.defaultCBPen
        self._cBSelectedPen         = self.defaultCBSelectedPen
        
        self._controlPointPen       = QtGui.QPen(QtGui.QColor(50, 100, 120, 200))
        self._controlPointBrush     = QtGui.QBrush(QtGui.QColor(200, 200, 210, 120))
        self._testBrush             = QtGui.QBrush(QtGui.QColor(100,100,105, 120))
        
        self._controlLinePen        = QtGui.QPen(QtGui.QBrush(QtCore.Qt.lightGray), 
                                                 1, QtCore.Qt.SolidLine)
        

        self.setFlags(QtWidgets.QGraphicsItem.ItemIsMovable                 | \
                      QtWidgets.QGraphicsItem.ItemIsFocusable               | \
                      QtWidgets.QGraphicsItem.ItemIsSelectable              | \
                      QtWidgets.QGraphicsItem.ItemSendsGeometryChanges      | \
                      QtWidgets.QGraphicsItem.ItemSendsScenePositionChanges)

        self.setAcceptHoverEvents(True)
        
        #self.setBoundingRegionGranularity(0.5)
        
        if self._objectType == GraphicsObjectType.crosshair_cursor:
            self.setBoundingRegionGranularity(0.5)
            
        #else:
            #self.setBoundingRegionGranularity(0.25)
        
        self.__drawObject__() 
                    
        self.update()
        
        if self.__backend__ is not None:
            self.setVisible(len(self.__backend__.frameIndices)==0 or self.__backend__.hasStateForFrame(self.__backend__.currentFrame))
        #self.setVisible(True)
        
        if self.__backend__ is not None:
            self.__backend__.frontends.append(self)
            
            for f in self.__backend__.frontends:
                if f != self:
                    self.signalGraphicsObjectPositionChange.connect(f.slotLinkedGraphicsObjectPositionChange)
                    f.signalGraphicsObjectPositionChange.connect(self.slotLinkedGraphicsObjectPositionChange)
                    
    def __parametric_constructor__(self, parameters, pos, frameindex=None, currentframe=0):
        # check frameindex and currentframe
        if isinstance(frameindex, (tuple, list)):
            # this can be an empty sequence!!!
            if len(frameindex)> 0:
                if len(frameindex) == 1 and frameindex[0] is None:
                    frameindex.clear()
                    
                elif not all([isinstance(a, numbers.Integral) and a >= 0 for a in frameindex]):
                    raise TypeError("visible frame indices must be non-negative integers")
        
        elif isinstance(frameindex, numbers.Integral):
            if frameindex < 0:
                raise ValueError("visible frame index cannot be negative")
            
            frameindex = [frameindex]
            
        elif frameindex is None:
            frameindex = []
            
        else:
            raise TypeError("Index of visible frames (frameindex) expected to be an int or a sequence of int, or None; got %s instead" % type(frameindex).__name__)
        
        self._frameindex = frameindex

        if not isinstance(currentframe, numbers.Integral):
            raise TypeError("currentframe expected to be an int got %s instead" % type(currentFrame).__name__)
        
        self._currentframe_ = currentframe
        
        if self._objectType & GraphicsObjectType.allCursorTypes:
            # parametric cursor c'tor
            if len(parameters) == 5 and all([isinstance(c, numbers.Number) for c in parameters]):
                if pos is None:
                    pos = QtCore.QPointF(0.,0.)
                
                self.__backend__ = Cursor(pos.x(),  
                                        pos.y(),
                                        float(parameters[0]),
                                        float(parameters[1]),
                                        float(parameters[2]), 
                                        float(parameters[3]), 
                                        float(parameters[4]), 
                                        frameindex=frameindex,
                                        name=self._objectType.name,
                                        currentframe=self._currentframe_,
                                        graphicstype=self._objectType)
                
                super().setPos(pos)
                
            else:
                raise ValueError("For parametric cursor construction, 'parameters' must be a sequence of five 5 numbers; instead got %d elements" % (len(parameters)))
                
        else: # parametric c'tor for non-cursor graphic objects
            if parameters is None or (isinstance(parameters, (tuple, list)) and len(parameters) == 0) \
                or (isinstance(parameters, Path) and len(parameters) == 0) or \
                self._objectType == GraphicsObjectType.allShapeTypes:
                # enters build mode
                self._buildMode = True # self.__backend__ will be built in __finalizeShape__() after exit from build mode

            elif isinstance(parameters, QtCore.QLineF):
                self._objectType = GraphicsObjectType.line
                self.__backend__ = Path(Move(parameters.p1().x(), parameters.p1().y()),
                            Line(parameters.p2().x(), parameters.p2().y()),
                            frameindex = self._frameindex,
                            currentframe = self._currentframe_)
    
                if self.__backend__.name is None or len(self.__backend__.name) == 0:
                    self.__backend__.name = self._objectType.name
                
                self.__cachedPath__ = self.__backend__.asPath()
                
            elif isinstance(parameters, QtCore.QRectF):
                # parametric construction from a QRectF
                self._objectType = GraphicsObjectType.rectangle
                
                self.__backend__ = Rect(parameters.topLeft().x(), 
                                        parameters.topLeft().y(), 
                                        parameters.width(), 
                                        parameters.height(), 
                                        name = self._objectType.name, 
                                        frameindex = self._frameindex, 
                                        currentframe=self._currentframe_)
                
                if self.__backend__.name is None or len(self.__backend__.name) == 0:
                    self.__backend__.name = self._objectType.name
                
                self.__cachedPath__ = self.__backend__.asPath()
                        
            elif isinstance(parameters, QtGui.QPolygonF):
                # parametric c'tor from a QPolygonF
                # NOTE: QPolygonF if a :typedef: for QPointF list (I think?)
                # this HAS to be done this way, becase QPolygonF is NOT a python iterable
                self._objectType = GraphicsObjectType.polygon
                self.__backend__ = Path()
                
                for k, p in enumerate(parameters):
                    if k == 0:
                        self.__backend__.append(Move(p.x(), p.y()))
                        
                    else:
                        self.__backend__.append(Line(p.x(), p.y()))
                        
                if self._frameindex is not None and len(self._frameindex):
                    self.__backend__.frameIndices = self._frameindex
                    self.__backend__.currentFrame = self._currentframe_
                
                if self.__backend__.name is None or len(self.__backend__.name) == 0:
                    self.__backend__.name = self._objectType.name
                
                self.__cachedPath__ = self.__backend__.asPath()
                
            elif isinstance(parameters, QtGui.QPainterPath):
                self._objectType = GraphicsObjectType.path
                
                self.__backend__ = Path()
                
                self.__backend__.adoptPainterPath(parameters)
                
                #if self._frameindex is not None and len(self._frameindex):
                self.__backend__.frameIndices = self._frameindex
                self.__backend__.currentFrame = self._currentframe_
                    
                if self.__backend__.name is None or len(self.__backend__.name) == 0:
                    self.__backend__.name = self._objectType.name
                
                self.__cachedPath__ = self.__backend__.asPath()
                
            elif isinstance(parameters, (tuple, list)):
                if all([isinstance(p, (QtCore.QPointF, QtCore.QPoint)) for p in parameters]):
                    # parametric c'tor from sequence of Qt points
                    self._objectType = GraphicsObjectType.polygon
                    
                    self.__backend__ = Path()
                    self.__backend__.append(Move(parameters[0].x(), parameters[0].y()))
                    
                    for c in parameters[1:]:
                        self.__backend__.append(Line(c.x(), c.y()))
                        
                    #if self._frameindex is not None and len(self._frameindex):
                    self.__backend__.frameIndices = self._frameindex
                    self.__backend__.currentFrame = self._currentframe_
                        
                    if self.__backend__.name is None or len(self.__backend__.name) == 0:
                        self.__backend__.name = self._objectType.name
                    
                    self.__cachedPath__ = self.__backend__.asPath()

                elif all([isinstance(p, (Start, Move, Line, Cubic, Quad, Arc, ArcMove)) for p in parameters]):
                    self.__backend__ = Path(parameters) # a copy c'tor
                    self._objectType = self.__backend__.type

                    if self._frameindex is not None and len(self._frameindex):
                        self.__backend__.frameIndices = self._frameindex
                        self.__backend__.currentFrame = self._currentframe_
                    
                    if self.__backend__.name is None or len(self.__backend__.name) == 0:
                        self.__backend__.name = self._objectType.name
                    
                    self.__cachedPath__ = self.__backend__.asPath()
                    
                elif all([isinstance(p, numbers.Number) for p in parameters]):
                    if self._objectType & (GraphicsObjectType.line | GraphicsObjectType.rectangle | GraphicsObjectType.ellipse):
                        if len(parameters) == 4:
                            # x0, y0, x1, y1; either a line, 
                            # or the line of a rectangle's diagonal
                            # or one of the diameters of an ellipse
                            # the above is determined by the passed object type argument
                            # to __init__
                            
                            # cachedPath stores the control line (a diagonal)
                            if self._objectType == GraphicsObjectType.line:
                                
                                self.__backend__ = Path(Move(parameters[0], parameters[1]), 
                                                        Line(parameters[2], parameters[3]))
                                
                            elif self._objectType == GraphicsObjectType.rectangle:
                                self.__backend__ = Rect(parameters[0], parameters[1], 
                                                    parameters[2] - parameters[0],
                                                    parameters[3] - parameters[1])
                                
                            else:
                                self.__backend__ = Ellipse(parameters[0], 
                                                        parameters[1], 
                                                        parameters[2] - parameters[0],
                                                        parameters[3] - parameters[1])

                            # override backend's frame-state associations & currentframe 
                            # ONLY if self._frameindex was set by __init__ parameter
                            #if self._frameindex is not None and len(self._frameindex):
                            self.__backend__.frameIndices = self._frameindex
                            self.__backend__.currentFrame = self._currentframe_
                            
                            if self.__backend__.name is None or len(self.__backend__.name) == 0:
                                self.__backend__.name = self._objectType.name
                    
                            self.__cachedPath__ = self.__backend__.asPath()
                            
                        else:
                            raise TypeError("For line, ellipse or rectangle, a sequence of four scalars were expected")
                            
                    elif self._objectType & GraphicsObjectType.point:
                        # parametric construction of a Point
                        # TODO 2017-11-25 00:16:35
                        # make it accept a pictgui.Point - TODO define this :class: !
                        if len(parameters) in (2,3):
                            x = parameters[0]
                            y = parameters[1]
                            
                            if len(parameters) == 3:
                                self._pointSize = parameters[2]

                            self.__backend__ = Move(parameters[0], parameters[1],
                                                frameindex = self._frameindex,
                                                currentframe=self._currentframe_)
                                
                            if self.__backend__.name is None or len(self.__backend__.name) == 0:
                                self.__backend__.name = self._objectType.name
                            
                            self.__cachedPath__ = self.__backend__.asPath()
                            
                        else:
                            raise TypeError("For a point, 'parameters' is expected to be a sequence of two (x,y) or three (x, y, radius) numbers; got %s instead" % (type(parameters).__name__))
                    
                    elif self._objectType & (GraphicsObjectType.polygon | GraphicsObjectType.polyline):
                        if len(parameters)%2:
                            raise TypeError("For polygons or polyline, the numeric parameters must be a sequence with an even number of elements (x0,y0,x1,y1,... etc)")
                            
                        self.__backend__ = Path()
                        
                        for k in range(0, len(parameters),2):
                            if k == 0:
                                self.__backend__.append(Move(parameters[k], parameters[k+1]))
                                
                            else:
                                self.__backend__.append(Line(parameters[k], parameters[k+1]))
                                
                        self.__backend__.frameIndices = self._frameindex
                        
                        self.__backend__.currentFrame = self._currentframe_
                            
                        if self.__backend__.name is None or len(self.__backend__.name) == 0:
                            self.__backend__.name = self._objectType.name
                        
                        self.__cachedPath__ = self.__backend__.asPath()
                            
                elif all([isinstance(p, (tuple, list)) and len(p) == 2 and all([isinstance(cc, numbers.Number) for cc in p]) for p in parameters]):
                    # parametric c'tor from (X,Y) pairs of scalar coordinates
                    # force polyline type -- if you want to build a rectangle se above
                    
                    self.__backend__ = Path()
                    self.__backend__.append(Move(parameters[0][0], parameters[0][1]))

                    for p in parameters[1:]:
                        self.__backend__.append(Line(p[0], p[1]))
                        
                    if self._objectType == GraphicsObjectType.polygon:
                        self.__backend__.closed = True
                        
                    else:
                        self._objectType = GraphicsObjectType.polyline
                    
                    #if self._frameindex is not None and len(self._frameindex):
                    self.__backend__.frameIndices = self._frameindex
                    self.__backend__.currentFrame = self._currentframe_
                    
                    if self.__backend__.name is None or len(self.__backend__.name) == 0:
                        self.__backend__.name = self._objectType.name
                    
                    self.__cachedPath__ = self.__backend__.asPath()
                        

    def __parse_parameters__(self, parameters, pos, frameindex = None, currentframe = 0):
        """Builds the graphics object and the planar graphic according to the following rules:
        
        1) parametric constructors:
        1.1) for cursors, build the backend from the supplied parameters
        1.2) for shaped objects, build the cached path the generate a backend from it
        
        2) construct from a planar graphic object:
        2.1) for cursors, use the planar graphics as backend
        2.2) for shaped objects, use the planar graphics as backend then generate
        a cached path from the state descriptor associated with the current frame
        (or from the common state descriptor)
        
        3) When function returnsthere shoud ALWAYS be a backend and, in the case
        of shaped objects, a cached path.
        
        3.1) The ONLY EXCEPTION this rule is for shaped objects construction with
        no parameters whatsoever: buildMode is invoked to generate a backend and 
        a cached path.
        
        frameindex and current frame are used ONLY when the graphics object is contructed
        parametrically (which also generates its own new backend);
        
        when the graphics object is contructed on an existing backend, frameindex 
        and currentframe parameters are ignored
        
        """
        # ###
        # BEGIN parse parameters
        # ###
        
        if isinstance(parameters, PlanarGraphics): 
            # parameters are the backend, so override self._objectType set in __init__
            self._objectType = parameters.type
            
        if pos is not None and not isinstance(pos, (QtCore.QPoint, QtCore.QPointF)):
            raise TypeError("When given, pos must be a QPoint or QPointF")
        
        # TODO 2017-11-25 00:15:21
        # set up backends when parameter is a pictgui primitive
        # link coordinate changes to the attributes of the backend
        
        if isinstance(parameters, (Cursor, Ellipse, Rect, Path, Text, str)):
            if isinstance(parameters, (Cursor, Ellipse, Rect, Path)):
                if isinstance(parameters, Path):
                    if len(parameters) == 0:
                        # allow empty Path objects => merge into build mode ?
                        self.__parametric_constructor__(parameters, pos, frameindex, currentframe)
                        #raise ValueError("received an empty Path object; cannot proceed")
                    
                    elif len(parameters) == 1:
                        # convert a 1-element Path into the primitive
                        if isinstance(parameters[0], (Move, Line)):
                            self._objectType = GraphicsObjectType.point
                            
                        else:
                            self._objectType = parameters[0].type
                            
                        self.__backend__ = parameters[0]
                        
                    else:
                        self._objectType = parameters.type # this will be one of line, rectangle, polygon, polyline, or path
                        self.__backend__ = parameters
                    
                else:
                    self.__backend__    = parameters # so that we reference this directly from this object
                    self._objectType = self.__backend__.type
                
                if not isinstance(parameters, Cursor):
                    self.__cachedPath__ = self.__backend__.asPath()
                
            elif isinstance(parameters, str): # TODO: move this to __parametric_constructor__
                    painter.drawText(parameters)
                    self.__backend__ = Text(parameters)
                    
                    self._objectType = GraphicsObjectType.text
                    
            else:
                raise TypeError("Inavlid 'parameters' type for backend-based construction: %s" % type(parameters).__name__)

            self._buildMode = False
                    
            self._frameindex = self.__backend__.frameIndices
            self._currentframe_ = self.__backend__.currentFrame
                
            if self.__backend__.name is None or len(self.__backend__.name) == 0:
                self.__backend__.name = self._objectType.name
                self.__backend__.updateLinkedObjects()
            
            if pos is None or (isinstance(pos, (QtCore.QPoint, QtCore.QPointF)) and pos.isNull()):
                if self.__backend__ is not None:
                    if self.__backend__.hasStateForFrame(self._currentframe_):
                        pos = self.__backend__.pos
                    else:
                        pos = QtCore.QPointF(0,0)
                    
                else:
                    pos = QtCore.QPointF(0,0)
                
            super().setPos(pos)
            
        else:
            self.__parametric_constructor__(parameters, pos, frameindex, currentframe)
        
            
        # ###
        # END parse parameters
        # ###
        
    def __str__(self):
        return "%s, type %s, ID %s, backend %s" \
            % (self.__repr__(), self._objectType.name, self._ID_, self.backend.__repr__())
            
    def __setDisplayStr__(self, value=None):
        """Constructs the label string
        """
        nameStr = ""
        
        if value is None:
            if self.__backend__ is None:
                nameStr = self._ID_
                
            else:
                nameStr = self.__backend__.name

        elif isinstance(value, str):
            nameStr = value
            
        else:
            raise TypeError("Expecting a string argument, or None; got %s instead" % (type(value).__name__))
        
        if self.__backend__ is not None and self.__backend__.hasStateForFrame(self._currentframe_):
            if not isinstance(self.__backend__, Path):
                stateDescriptor = self.__backend__.getState(self._currentframe_)

                if isinstance(stateDescriptor, list) and len(stateDescriptor):
                    stateDescriptor = stateDescriptor[0]
                    
                if stateDescriptor is not None and len(stateDescriptor):
                    if self._parentWidget is not None: # why this condition here?
                        if self._labelShowsCoordinates:
                            if self.objectType & GraphicsObjectType.allCursorTypes:
                                if self._objectType & GraphicsObjectType.vertical_cursor:
                                    nameStr += ": %g" % stateDescriptor.x
                                    
                                elif self._objectType == GraphicsObjectType.horizontal_cursor:
                                    nameStr += ": %g" % stateDescriptor.y
                                    
                                else:
                                    nameStr += ": %g, %g" % (stateDescriptor.x, stateDescriptor.y)
                            
        self._displayStr = nameStr
        
    @safeWrapper
    def __calculate_shape__(self):
        if self.__backend__ is not None:
            # non-cursor
            if self._buildMode or self.editMode:
                if self.__cachedPath__ is not None and len(self.__cachedPath__)> 0:
                    path.addPath(self.__cachedPath__())
                    
                    if len(self.__cachedPath__) > 1:
                        for k, element in enumerate(self.__cachedPath__):
                            path.addEllipse(element.x, element.y,
                                            self._pointSize * 2.,
                                            self._pointSize * 2.)
                            
                path.addRect(sc.sceneRect())
                
            path.addPath(self.__backend__())
                
            self.__setDisplayStr__()
                
            self.__updateLabelRect__()
            
            path.addRect(self._labelRect)
            
            if self.isSelected():
                if self._isLinked: # linked to other GraphicsObjects !!!
                    pen  = self._linkedSelectedPen
                    
                else:
                    pen = self._selectedCursorPen
                    
            else:
                if self._isLinked:# linked to other GraphicsObjects !!!
                    pen = self._linkedPen
                    #self._graphicsShapedItem.setPen(self._linkedPen)
                    
                else:
                    pen = self._cursorPen
                    
            pathStroker = QtGui.QPainterPathStroker(pen)
            
            return pathStroker.createStroke(path)
            
        else: 
            # no backend = this is in buildMode
            if self.__cachedPath__ is not None and len(self.__cachedPath__)> 0:
                pathStroker = QtGui.QPainterPathStroker(self._selectedCursorPen)
                
                path.addPath(pathStroker.createStroke(self.__cachedPath__()))

            path.addRect(sc.sceneRect())
            
            
        return path
    
            
    @safeWrapper
    def __updateLabelRect__(self):
        """Calculates label bounding rectangle
        """
        if len(self._displayStr) > 0:
            fRect = self._parentWidget.fontMetrics().boundingRect(self._displayStr)
            self._labelRect.setRect(fRect.x(), fRect.y(), fRect.width(), fRect.height())

        else:
            self._labelRect  = QtCore.QRectF() # a null rect
        
    def __finalizeShape__(self):
        """Creates the _graphicsShapedItem, an instance of QGraphicsItem.
        Used only by non-cursor types, after exit from build mode.
        Relies on self.__cachedPath__ which is a PlanarGraphics Path object. Therefore
        if makes inferences from self._objectType and the number of elements in
        self.__cachedPath__
        """
        if self._objectType & GraphicsObjectType.allCursorTypes:
            # NOTE: do NOT use _graphicsShapedItem for cursors !!!
            return
            
        else:#FIXME in build mode there is no __backend__; we create it here from the cached path
            #NOTE: for non-cursors, cachedPath is generated in build mode, or in
            #NOTE:  __parse_parameters__()
            if len(self.__cachedPath__):
                if self.__backend__ is None:
                    # NOTE: 2018-01-23 20:20:38
                    # needs to create particular backends for Rect and Ellipse
                    # because self.__cachedPath__ is a generic Path object
                    # (see __parse_parameters__)
                    if self._objectType == GraphicsObjectType.rectangle:
                        self.__backend__ = Rect(self.__cachedPath__[0].x,
                                             self.__cachedPath__[0].y,
                                             self.__cachedPath__[1].x-self.__cachedPath__[0].x,
                                             self.__cachedPath__[1].y-self.__cachedPath__[0].y)
                        
                    elif self._objectType == GraphicsObjectType.ellipse:
                        self.__backend__ = Ellipse(self.__cachedPath__[0].x,
                                                self.__cachedPath__[0].y,
                                                self.__cachedPath__[1].x-self.__cachedPath__[0].x,
                                                self.__cachedPath__[1].y-self.__cachedPath__[0].y)
                        
                        
                    else:
                        self.__backend__ = self.__cachedPath__.copy()
                        
                super().setPos(self.__backend__.pos)
                
                self._buildMode = False
                self._control_points = [None, None]
                
                self._hover_point = None
            
                self.signalROIConstructed.emit(self.objectType, self.name)
                
                if self.__backend__ is not None:
                    self.__backend__.frontends.append(self)
            
            else:
                # no cached path exists
                self.signalROIConstructed.emit(0, "")
        
        self.update()

    def __drawObject__(self):
        if self.__backend__ is None:
            return

        #if self.__backend__.currentFrame != self._currentframe_:
            #self.__backend__.currentFrame = self._currentframe_
        
        if len(self._displayStr) > 0:
            self.__setDisplayStr__(self._displayStr)
            
        else:
            self.__setDisplayStr__()
            
        if self.isCursor:
            self.__drawCursor__()
            
        else:
            self.__drawROI__()
            
    def __drawROI__(self):
        if self._buildMode:
            return
        
        self.__updateCachedPathFromBackend__() # to make sure control points stay within scene's rectangle

        self.update()
        
    def __drawCursor__(self):
        """Draws cursor
        """
        # NOTE: 2017-11-27 21:08:06
        # QPointF movedBy only used for crosshair cursors !!!
        #if not self.hasStateDescriptor:
            #return
        
        #state = self.__backend__.getState(self.__backend__.currentFrame)
        state = self.__backend__.currentState
        
        if state is None or len(state) == 0:
            return
        
        self.prepareGeometryChange() # inherited from QGraphicsObject
        
        try:
            #NOTE: 2018-01-16 22:20:38 API change:
            # do NOT store our own graphics descriptors any more; use backend properties
            # getters for the planar descriptors; 
            # ATTENTION backend descriptors are in scene coordinates; therefore they 
            # need to be mapped back on this item's coordinates
            # CAUTION: the reverse is NOT true in itemChange where "value" is already given
            # in scene coordinates, and therefore self._deltaPos is also in scene coordinates
            
            # the access to the backend's planar descriptors always reads values 
            # from the current descriptor state of the backend, that is, either the
            # common state, or the state associated with the current image frame 
            # (for a data "volume") is the backend has frame-state associations
            
            # NOTE: 2018-01-18 15:16:55
            # THAT'S THE CORRECT WAY !!!
            # main cursor lines:
            self._vline = QtCore.QLineF(self.mapFromScene(QtCore.QPointF(state.x, 0)), 
                                        self.mapFromScene(QtCore.QPointF(state.x, state.height)))
            
            self._hline = QtCore.QLineF(self.mapFromScene(QtCore.QPointF(0, state.y)), 
                                        self.mapFromScene(QtCore.QPointF(state.width, state.y)))
            
            # for vertical cursor ONLY
            if self._positionChangeHasBegun:
                newY = self._wbarPos.y() + self._deltaPos.y()
                
                if newY < 0:
                    newY = 0
                    
                elif newY > state.height-1:
                    newY = state.height-1
                    
                self._hwbar = QtCore.QLineF(self.mapFromScene(QtCore.QPointF(state.x - state.xwindow/2,
                                                                            newY)),
                                            self.mapFromScene(QtCore.QPointF(state.x + state.xwindow/2,
                                                                            newY)))
                
            else:
                self._hwbar = QtCore.QLineF(self.mapFromScene(QtCore.QPointF(state.x - state.xwindow/2,
                                                                            self._wbarPos.y())), 
                                            self.mapFromScene(QtCore.QPointF(state.x + state.xwindow/2,
                                                                            self._wbarPos.y())))
            
            # for horizontal cursor ONLY
            if self._positionChangeHasBegun:
                newX = self._wbarPos.x() + self._deltaPos.x()
                
                if newX < 0:
                    newX = 0
                    
                elif newX > state.width-1:
                    newX = state.width-1
                    
                self._vwbar = QtCore.QLineF(self.mapFromScene(QtCore.QPointF(newX, 
                                                                            state.y - state.ywindow/2)),
                                            self.mapFromScene(QtCore.QPointF(newX, 
                                                                            state.y + state.ywindow/2)))
                
            else:
                self._vwbar = QtCore.QLineF(self.mapFromScene(QtCore.QPointF(self._wbarPos.x(), 
                                                                            state.y - state.ywindow/2)),
                                            self.mapFromScene(QtCore.QPointF(self._wbarPos.x(), 
                                                                            state.y + state.ywindow/2)))
            
            # component of the point cursor (central rect)
            self._crect = QtCore.QRectF(self.mapFromScene(QtCore.QPointF(state.x - state.radius,
                                                                        state.y - state.radius)),
                                        self.mapFromScene(QtCore.QPointF(state.x + state.radius,
                                                                        state.y + state.radius)))
            
            # component of the point cursor and of the crosshair cursor (window rect)
            self._wrect = QtCore.QRectF(self.mapFromScene(QtCore.QPointF(state.x - state.xwindow/2,
                                                                        state.y - state.ywindow/2)),
                                        self.mapFromScene(QtCore.QPointF(state.x + state.xwindow/2,
                                                                        state.y + state.ywindow/2)))


            super().update()
            
        except Exception as exc:
            traceback.print_exc()
            print("in %s %s" % (self.objectType, self.name))
        
        
    @property
    def isLinked(self):
        self._isLinked = len(self._linkedGraphicsObjects) > 0
        return self._isLinked
    
    def isLinkedWith(self, other):
        return other.ID in self._linkedGraphicsObjects
        
    # NOTE: 2017-06-30 12:04:24
    # TODO: functions/event handlers to implement/overload:
    # TODO OPTIONAL: collidesWithItem()
    # TODO OPTIONAL: contains() -- relies on shape()
    # TODO OPTIONAL: focusInEvent, focusOutEvent hoverEnterEvent hoverLeaveEvent 
    # TODO OPTIONAL: keyReleaseEvent (to move it by keyboard)
    # TODO OPTIONAL: hoverMoveEvent -- optional
    
    def type(self):
        return GraphicsObject.Type
    
    @safeWrapper
    def getShapePathElements(self):
        if not self.hasStateDescriptor:
            return
        
        if self.objectType & GraphicsObjectType.allCursorTypes:
            return
        
        path = self.graphicsItem.shape() #  a QPainterPath with subpaths!
        
        elements = [path.elementAt(k) for k in range(path.elementCount())]
        
        # find subpaths: subpaths always begin with a moveTo element
        
        pathBreaks = [k for (k,e) in enumerate(elements) if e.type == QtGui.QPainterPath.MoveToElement]
        pathBreaks.append(len(elements))
        
        paths = [[e for e in elements[slice(pathBreaks[k], pathBreaks[k+1])]] for k in range(len(pathBreaks)-1)]
            
        return paths
    
        # NOTE: 2017-08-10 15:20:50

    @safeWrapper
    def __updateCachedPathFromBackend__(self):
        """No mapping transformations here, as the cached path is a copy of the
        __backend__'s state associated with the current frame.
        """
        if self.objectType & GraphicsObjectType.allCursorTypes:
            return
        
        sc = self.scene()
            
        if self.scene() is None:
            try:
                sc = self._parentWidget.scene
            except:
                return
        
        if sc is None:
            return
            
        pad = self._pointSize
        left = pad
        right = sc.width() - pad
        top = pad
        bottom =sc.height() - pad
        
        if self.__backend__ is None:
            return
        
        if isinstance(self.__backend__, (Ellipse, Rect)):
            self.__cachedPath__ = Path(Move(self.__backend__.x, self.__backend__.y),
                                    Line(self.__backend__.x + self.__backend__.w,
                                         self.__backend__.y + self.__backend__.h))
                                    
        elif isinstance(self.__backend__, Path):
            if self.__backend__.hasStateForFrame(self._currentframe_):
                self.__cachedPath__ = self.__backend__.asPath(self._currentframe_)
                
            else:
                self.__cachedPath__ = Path()
                
        else:
            self.__cachedPath__ = self.__backend__.asPath()
            
    def show(self):
        self.setVisible(True)
        
    def hide(self):
        self.setvibisle(False)
    
    #@safeWrapper
    def boundingRect(self):
        """Mandatory to get the bounding rectangle of this item
        """
        bRect = QtCore.QRectF()
        sc = self.scene()
        #if self.scene() is None:
            #sc = self.scene
        if sc is None:
            if self._parentWidget is not None:
                sc = self._parentWidget.scene
                
        if sc is None:
            return bRect #  return a null QRect!
            
        self.__setDisplayStr__(self._ID_)
            
        self.__updateLabelRect__()
        
        try:
            if self.objectType & GraphicsObjectType.allCursorTypes:
                # NOTE: 2018-01-25 22:06:25
                # this is required: what if this cursor is linked with one in another
                # window that shows a different frame, for which the backend has no
                # state descriptor?
                # seame check is done for non-cursor types, below
                state = self.__backend__.getState(self._currentframe_) 
                
                if state is not None and len(state):
                    if self.isVerticalCursor:
                        # QRectF(x,y,w,h)
                        bRect = self.mapRectFromScene(QtCore.QRectF(state.x - state.xwindow/2,
                                                                    0, 
                                                                    state.xwindow, 
                                                                    state.height))
                        
                    elif self.isHorizontalCursor:
                        bRect = self.mapRectFromScene(QtCore.QRectF(0, 
                                                                    state.y - state.ywindow/2,  
                                                                    state.width, 
                                                                    state.ywindow))
                        
                    elif self.isCrosshairCursor:
                        bRect =  self.mapRectFromScene(QtCore.QRectF(-state.width//2, 
                                                                    -state.height//2, 
                                                                    state.width, 
                                                                    state.height))
                        
                    else: # point cursor
                        bRect = self.mapRectFromScene(QtCore.QRectF(state.x - state.xwindow/2, 
                                                                    state.y - state.ywindow/2, 
                                                                    state.xwindow, 
                                                                    state.ywindow))

                    if not self._labelRect.isNull():
                        bRect |= self._labelRect # union
                        
                else:
                    bRect = QtCore.QRectF()
                        
            else:
                # not a cursor
                if self.__backend__ is not None and self.__backend__.hasStateForFrame(self._currentframe_) and self.__backend__() is not None:
                    #bRect = self.mapRectFromScene(self.__backend__().controlPointRect()) # relies on planar graphics's shape !!!!
                    bRect = self.mapRectFromScene(self.__backend__().boundingRect()) # relies on planar graphics's shape !!!!
                    
                    if self.editMode:
                        bRect |= self.mapRectFromScene(self.__cachedPath__().boundingRect())
                        
                else:
                    # no backend, or backend has no state
                    if self._buildMode:
                        # we need this to pick up mouse events from anywhere in the scene
                        bRect = sc.sceneRect()
                        
                    else:
                        bRect = QtCore.QRectF()
                        
                if not self._labelRect.isNull():
                    lrect = QtCore.QRectF(self._labelRect.topLeft(),
                                        self._labelRect.bottomRight())
                    
                    lrect.moveBottomLeft(bRect.center())
                    
                    bRect |= lrect # union
        except Exception as exc:
            traceback.print_exc()
            print("in %s %s frame %d" % (self.type, self.name, self.currentFrame))
        
                
        return bRect
    
    def toScenePath(self):
        """Returns a new pictgui.Path object or None if isCursor is True.
        
        This constructs a new pictgui.Path object. 
        
        To reflect the changes in this object's values in an existing
        pictgui.Path object, use direct access to the attributes of the latter.
        
        Coordinates are mapped to scene's coordinate system
        
        NOTE: This is not a reference to the backend Path object
        """
        #if not self.hasStateDescriptor:
            #return
        
        if not self.isCursor:
            if self.isText:
                # TODO FIXME ???
                raise NotImplementedError("Scene coordinates from text objects not yet implemented")
            
            if len(self.__cachedPath__ > 0):
                return Path([self.mapToScene(p) for p in self.__cachedPath__.qPoints()])
            
    def toSceneCursor(self):
        """Returns a new pictgui.Cursor object or None if isCursor is False.
        
        This constructs a new pictgui.Cursor object. 
        
        To reflect the changes in this object's values in an existing 
        pictgui.Cursor object use direct acces to the attributes of the latter.
        
        Coordinates are mapped to scene's coordinate system.
        
        NOTE: This does NOT return the reference to the backend Cursor object (which may exist)
        """
        #if not self.hasStateDescriptor:
            #return
        
        if self.isCursor:
            stateDescriptor = self.__backend__.getState(self._currentframe_)
            if stateDescriptor and len(stateDescriptor):
                p = self.mapToScene(QtCore.QPointF(self.__backend__.x, self.__backend__.y))
                return Cursor(self.name, p.x(), p.y(), self.__backend__.width, self.__backend__.height, self.__backend__.xwindow, self.__backend__.ywindow, self.__backend__.radius)
            
                #p = self.mapToScene(QtCore.QPointF(stateDescriptor.x, stateDescriptor.y))
                #return Cursor(self.name, p.x(), p.y(), stateDescriptor.width, stateDescriptor.height, stateDescriptor.xwindow, stateDescriptor.ywindow, stateDescriptor.radius)
            
    def getScenePosition(self):
        """Returns the position in the scene as x, y sequence
        FIXME
        """
        p = self.mapToScene(self.__backend__.pos)
            
        return p.x(), p.y()
            
            
    def getSceneCoordinates(self):
        """Returns the coordinates that define this shape in the scene.
        FIXME
        Coordinates are mapped to scene's coordinate system
        """
        # NOTE: 2017-11-21 23:07:07
        # DO NOT not rely on QPainterPath - pictgui.Path conversions here, 
        # because QPainterPath inserts all sorts of points & segments (something
        # to do with how they compute the rendering of the actual path)
        # 
        stateDescriptor = self.__backend__.getState(self._currentframe_)
        
        if len(stateDescriptor):
            if self.isCursor:
                p = self.mapToScene(QtCore.QPointF(self.__backend__.x, self.__backend__.y))
                ret = [p.x(), p.y(), self.__backend__.width, self.__backend__.height, self.__backend__.xwindow, self.__backend__.ywindow, self.__backend__.radius]

            else: #FIXME
                if isinstance(stateDescriptor, list):
                    pp = list()
                    for s in stateDescriptor:
                        if s:
                            pp.append([])
                        else:
                            pp.append(None)
                            
                pp = [self.mapToScene(p) for p in stateDescriptor.qPoints()]
                
                if self.isPoint:
                    ret = [pp[0].x(), pp[0].y()]
                    
                elif self.isLine:
                    ret = [pp[0].x(), pp[0].y(), pp[1].x(), pp[1].y()]
                
                elif self.isRectangle or self.isEllipse:
                    # the cached path is the diagonal/primary diameter line!
                    # return the x, y, width, height
                    ret = [pp[0].x(), pp[0].y(), pp1.x() - pp0.x(), pp1.y() - pp0.y()]
                    
                elif self.isPolygon:
                    ret = [[p.x(), p.y()] for p in pp]
                    
                elif self.isPath:
                    # TODO FIXME
                    raise NotImplementedError("Scene coordinates from path objects not yet implemented")
                
                elif self.isText:
                    # TODO FIXME ???
                    raise NotImplementedError("Scene coordinates from text objects not yet implemented")
                
        return ret
    
    @safeWrapper
    def shape(self):
        """ Used in collision detection, etc.
        Currently return a path made of this item's bounding rectangle.
        """
        path = QtGui.QPainterPath()
        
        sc = self.scene()
        
        if sc is None:
            if self._parentWidget is not None:
                sc = self._parentWidget.scene
                
        if sc is None:
            #path.addRect(QtCore.QRectF()) #  return a null QRect!
            return path
        
        if self.objectType & GraphicsObjectType.allCursorTypes:
            state = self.__backend__.getState(self._currentframe_)
            if state is not None and len(state):
                if self.isCrosshairCursor:
                    path.moveTo(state.x, -state.height//2 - self._deltaPos.y()) # BEGIN vertical line
                    path.lineTo(state.x, state.height//2 - self._deltaPos.y())  # END vertical line
                    path.moveTo(-state.width//2 - self._deltaPos.x(), state.y)  # BEGIN horizontal line
                    path.lineTo(state.width//2 - self._deltaPos.x(), state.y)   # END horizontal line
                    
                    self.__setDisplayStr__()
                        
                    self.__updateLabelRect__()
                    
                    path.addRect(self._labelRect)
                    
                else:
                    path.addRect(self.boundingRect()) # for cursors this is safe: it DOES NOT recurse infinitely
                
            return path
        
        else:
            
            if self.__backend__ is not None and self.__backend__.hasStateForFrame(self._currentframe_) and self.__backend__() is not None:
                path.addPath(self.mapFromScene(self.__backend__()))
                
                if self._objectType == GraphicsObjectType.line:
                    p0 = self.mapFromScene(QtCore.QPointF(self.__backend__[0].x, self.__backend__[0].y))
                    p1 = self.mapFromScene(QtCore.QPointF(self.__backend__[1].x, self.__backend__[1].y))
                    path.addRect(QtCore.QRectF(p0,p1))
                    
                elif self._objectType == GraphicsObjectType.path:
                    path.addRect(self.mapRectFromScene(self.__backend__().boundingRect()))
                
                if self.editMode:
                    if self.__cachedPath__ is not None and len(self.__cachedPath__)> 0:
                        path.addPath(self.mapFromScene(self.__cachedPath__()))
                        
                    if len(self.__cachedPath__) > 1:
                        for k, element in enumerate(self.__cachedPath__):
                            pt = self.mapFromScene(QtCore.QPointF(element.x, element.y))
                            path.addEllipse(pt, self._pointSize, self._pointSize)

                self.__setDisplayStr__()
                    
                self.__updateLabelRect__()
                
                lrect = QtCore.QRectF(self._labelRect.topLeft(),
                                      self._labelRect.bottomRight())
                
                lrect.moveBottomLeft(self.boundingRect().center())
                path.addRect(lrect)
                path.addRect(self.boundingRect())
                
                path.setFillRule(QtCore.Qt.WindingFill)
                
                return path
            
    
            else: 
                # either no backend (in build mode), or no state for current frame
                if self._buildMode:
                    if self.__cachedPath__ is not None and len(self.__cachedPath__)> 0:
                        path.addPath(self.__cachedPath__())
                    
                    path.addRect(sc.sceneRect()) # needed to find collisions with mouse
                
        return path
    
    def setPos(self, x, y=None):
        """Overloads QGraphicsItem.setPos()
        Parameters:
        ==========
        x: float or QtCore.QPointF when y is None
        y: float or None
        """
        # NOTE changes to backend ar done by itemChange()
        if self.objectType & GraphicsObjectType.allCursorTypes:
            if all([isinstance(v, numbers.Real) for v in (x,y)]):
                super().setPos(x,y)
                
            elif isinstance(x, QtCore.QPointF):
                super().setPos(x)
                
            elif isinstance(x, QtCore.QPoint):
                super().setPos(QtCore.QPointF(x))
                
            else:
                raise TypeError("Either x and y must be supplied as floats, or x must be a QPointF or QPoint")
            
        else:
            if all([isinstance(v, numbers.Real) for v in (x,y)]):
                super().setPos(x,y)
                
            elif isinstance(x, QtCore.QPointF):
                super().setPos(x)
                
            elif isinstance(x, QtCore.QPoint):
                super().setPos(QtCore.QPointF(x))
                
            else:
                raise TypeError("Either x and y must be supplied as floats, or x must be a QPointF or QPoint")
            
        self.redraw()
        
    def update(self):
        if self.scene(): # because it may by Null at construction
            self.scene().update(self.boundingRect())
            #self.scene().update(self.scene().sceneRect().x(), \
                                #self.scene().sceneRect().y(), \
                                #self.scene().sceneRect().width(), \
                                #self.scene().sceneRect().height())
            
            #for v in self.scene().views():
                #v.repaint(v.childrenRect())
            
        else:
            super().update()
        
    def redraw(self):
        self.__drawObject__()

        #if self._labelShowsCoordinates:
        self.__setDisplayStr__()
        self.__updateLabelRect__()

        self.update()
        
    #@safeWrapper
    def paint(self, painter, styleOption, widget):
        """Does the actual painting of the item.
        Also called by super().update() & scene.update()
        """
        try:
            if not self.__objectVisible__:
                return
            
            if not self._buildMode:
                if self.__backend__ is None:
                    return
                
                if not self.__backend__.hasStateForFrame(self.__backend__.currentFrame):
                    return
                
            self.__updateLabelRect__()
            
            if self._buildMode:
                painter.setPen(self._selectedCursorPen)
                textPen = self._textPen
                
            else:
                if self.isSelected(): # inherited from QGraphicsItem via QGraphicsObject
                    if self._isLinked:
                        painter.setPen(self._linkedSelectedPen)
                        textPen = self._linkedTextPen
                        
                    elif len(self.__backend__.frontends) > 0:
                        painter.setPen(self._cBSelectedPen)
                        textPen = self._textCBPen
                        
                    else:
                        painter.setPen(self._selectedCursorPen)
                        textPen = self._textPen
                        
                else:
                    if self._isLinked:
                        painter.setPen(self._linkedPen)
                        textPen = self._linkedTextPen
                        
                    elif len(self.__backend__.frontends) > 0:
                        painter.setPen(self._cBPen)
                        textPen = self._textCBPen
                        
                    else:
                        painter.setPen(self._cursorPen)
                        textPen = self._textPen

            labelPos = None         # NOTE: 2017-06-23 09:41:24
                                    # below I calculate a default label position
                                    # based on cursor type
                                    # this position will be then changed dynamically
                                    # according to the font metrics
                                    # when the painter becomes active
                                    
            painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing)
            
            if self.objectType & GraphicsObjectType.allCursorTypes:
                # NOTE: 2018-01-18 14:47:49
                # WARNING: DO NOT use _graphicsShapedItem to represent cursors,
                # because the Qt GraphicsView system renders its shape's bounding 
                # rect with a dotted line when item is selected.
                ### self._graphicsShapedItem.paint(painter, styleOption, widget)

                lines = None
                rects = None
                
                state = self.__backend__.getState(self.__backend__.currentFrame)
                
                if state is None or len(state) == 0:
                    return
                
                if self._objectType == GraphicsObjectType.vertical_cursor:
                    lines = [self._vline, self._hwbar]
                    
                    labelPos = self.mapFromScene(QtCore.QPointF(self.__backend__.x - self._labelRect.width()/2, 
                                                                self._labelRect.height()))

                elif self._objectType == GraphicsObjectType.horizontal_cursor:
                    lines = [self._hline, self._vwbar]
                    labelPos = self.mapFromScene(QtCore.QPointF(0, self.__backend__.height/2 - self._labelRect.height()/2))

                elif self._objectType == GraphicsObjectType.crosshair_cursor:
                    lines = [self._vline, self._hline]
                    labelPos = self.mapFromScene(QtCore.QPointF(self.__backend__.x  - self._labelRect.width()/2,
                                                self._labelRect.height()))
                    
                    rects = [self._wrect]
                        
                else: # point cursor
                    rects = [self._crect]
                    labelPos = self.mapFromScene(QtCore.QPointF(self.__backend__.x - self._labelRect.width()/2,
                                                self.__backend__.y - self._labelRect.height()))

                if lines is not None:
                    painter.drawLines(lines)
                    
                if rects is not None:
                    painter.drawRects(rects)
                    
            else:
                # non-cursor types
                # NOTE: FIXME be aware of undefined behaviours !!! (check flags and types)
                if self._buildMode: # this only makes sense for ROIs
                    if len(self.__cachedPath__) == 0: # nothing to paint !
                        return
                    
                    # NOTE: 2018-01-24 15:57:16 
                    # THE SHAPE IN BUILD MODE = cached path
                    # first draw the shape
                    painter.setPen(self._selectedCursorPen)
                    
                    if self.objectType & GraphicsObjectType.path:
                        painter.drawPath(self.__cachedPath__)
                        #painter.drawPath(self.__cachedPath__())
                        
                        if self._curveBuild and self._hover_point is not None:
                            if self._control_points[0] is not None:
                                path = QtGui.QPainterPath(self.__cachedPath__[-1].point())
                                
                                if self._control_points[1] is not None:
                                    path.cubicTo(self._control_points[0], 
                                                self._control_points[1], 
                                                self._hover_point)
                                    
                                else:
                                    path.quadTo(self._control_points[0], 
                                                self._hover_point)
                                    
                                painter.drawPath(path)
                                
                    if len(self.__cachedPath__) > 1:
                        if self.objectType & GraphicsObjectType.line:
                            painter.drawLine(self.__cachedPath__[-2].point(), 
                                            self.__cachedPath__[-1].point())
                            
                        elif self.objectType & GraphicsObjectType.rectangle:
                            painter.drawRect(QtCore.QRectF(self.__cachedPath__[-2].point(), 
                                                        self.__cachedPath__[-1].point()))
                            
                        elif self.objectType & GraphicsObjectType.ellipse:
                            painter.drawEllipse(QtCore.QRectF(self.__cachedPath__[-2].point(), 
                                                            self.__cachedPath__[-1].point()))
                            
                        elif self.objectType & GraphicsObjectType.polygon:
                            for k, element in enumerate(self.__cachedPath__):
                                if k > 0:
                                    painter.drawLine(self.__cachedPath__[k-1].point(), 
                                                    self.__cachedPath__[k].point())
                        

                    # NOTE: 2018-01-24 15:56:51 
                    # CONTROL POINTS AND LINES IN BUILD MODE
                    # now draw control points and lines
                    # draw control points
                    painter.setPen(self._controlPointPen) 
                    painter.setBrush(self._controlPointBrush)
                    
                    for k, element in enumerate(self.__cachedPath__):
                        painter.drawEllipse(element.x - self._pointSize,
                                            element.y - self._pointSize,
                                            self._pointSize * 2., 
                                            self._pointSize * 2.)
                        
                        if k > 0:
                            painter.drawLine(self.__cachedPath__[k-1].point(), 
                                            element.point())
                            
                    # NOTE: 2018-01-24 15:58:33 
                    # EXTRA CONTROL POINTS AND HOVER POINT IN BUILD MODE WHERE THEY EXIST
                    if self.objectType & GraphicsObjectType.path:
                        if self._control_points[0] is not None:
                            painter.drawEllipse(self._control_points[0].x() - self._pointSize,
                                                self._control_points[0].y() - self._pointSize,
                                                self._pointSize * 2., 
                                                self._pointSize * 2.)
                            
                            painter.drawLine(self.__cachedPath__[-1].point(), 
                                            self._control_points[0])
                            
                            if self._control_points[1] is not None:
                                painter.drawEllipse(self._control_points[1].x() - self._pointSize,
                                                    self._control_points[1].y() - self._pointSize,
                                                    self._pointSize * 2., 
                                                    self._pointSize * 2.)
                                
                                painter.drawLine(self._control_points[0], 
                                                self._control_points[1])
                                
                                if self._hover_point is not None:
                                    painter.drawEllipse(self._hover_point.x() - self._pointSize, 
                                                        self._hover_point.y() - self._pointSize, 
                                                        self._pointSize * 2., 
                                                        self._pointSize *2.)
                                    
                                    painter.drawLine(self._control_points[1], 
                                                    self._hover_point)
                                    
                                
                            else:
                                if self._hover_point is not None:
                                    painter.drawEllipse(self._hover_point.x() - self._pointSize, 
                                                        self._hover_point.y() - self._pointSize, 
                                                        self._pointSize * 2., 
                                                        self._pointSize *2.)
                                    
                                    painter.drawLine(self._control_points[0], 
                                                    self._hover_point)
                                    
                        elif self._hover_point is not None:
                            painter.drawEllipse(self._hover_point.x() - self._pointSize, 
                                                self._hover_point.y() - self._pointSize, 
                                                self._pointSize * 2., 
                                                self._pointSize *2.)
                            
                            painter.drawLine(self.__cachedPath__[-1].point(), 
                                            self._hover_point)
                        
                    elif self._hover_point is not None:
                        painter.drawEllipse(self._hover_point.x() - self._pointSize, 
                                            self._hover_point.y() - self._pointSize, 
                                            self._pointSize * 2., 
                                            self._pointSize *2.)
                        
                        painter.drawLine(self.__cachedPath__[-1].point(), 
                                        self._hover_point)

                        if self.objectType & GraphicsObjectType.line:
                            painter.drawLine(self.__cachedPath__[-1].point(), 
                                            self._hover_point)
                        
                        elif self.objectType & GraphicsObjectType.rectangle:
                            painter.drawRect(QtCore.QRectF(self.__cachedPath__[-1].point(), 
                                                        self._hover_point))
                            
                        elif self.objectType & GraphicsObjectType.ellipse:
                            painter.drawEllipse(QtCore.QRectF(self.__cachedPath__[-1].point(), 
                                                            self._hover_point))
                            
                        elif self.objectType & GraphicsObjectType.polygon:
                            painter.drawLine(self.__cachedPath__[-1].point(), 
                                            self._hover_point)

                    labelPos = self.boundingRect().center()
                    
                else:
                    # not in build mode
                    # NOTE: 2018-01-24 16:12:20
                    # DRAW SHAPE 
                    
                    # NOTE: 2018-01-24 16:12:43
                    # SELECT PEN & BRUSH FIRST
                    if self.isSelected():
                        if self._isLinked: # linked to other GraphicsObjects !!!
                            painter.setPen(self._linkedSelectedPen)
                            
                        elif self.sharesBackend:
                            painter.setPen(self._cBSelectedPen)
                            
                        else:
                            painter.setPen(self._selectedCursorPen)
                            
                    else:
                        if self._isLinked:# linked to other GraphicsObjects !!!
                            painter.setPen(self._linkedPen)
                            
                        elif self.sharesBackend:
                            painter.setPen(self._cBPen)
                            
                        else:
                            painter.setPen(self._cursorPen)
                            
                    if self.objectType & GraphicsObjectType.point:
                        if self._isLinked:# linked to other GraphicsObjects !!!
                            brush = QtGui.QBrush(self.defaultLinkedCursorColor)
                            
                        else:
                            brush = QtGui.QBrush(self.defaultColor)
                            
                        painter.setBrush(brush)
                            
                    # NOTE: 2018-01-24 16:13:03
                    # DRAW THE ACTUAL SHAPE
                    # NOTE: 2018-01-24 17:17:05
                    # WE SHOULD HAVE A __backend__ BY NOW
                    
                    #if self.__cachedPath__ is not None and len(self.__cachedPath__):
                    if self.__backend__ is not None:
                        if self._objectType == GraphicsObjectType.ellipse:
                            r_ = self.mapRectFromScene(self.__backend__.x,
                                                    self.__backend__.y,
                                                    self.__backend__.w,
                                                    self.__backend__.h)
                            
                            painter.drawEllipse(r_)

                        elif self._objectType == GraphicsObjectType.rectangle:
                            r_ = self.mapRectFromScene(self.__backend__.x,
                                                    self.__backend__.y,
                                                    self.__backend__.w,
                                                    self.__backend__.h)
                            
                            painter.drawRect(r_)
                                                                            
                        elif self._objectType == GraphicsObjectType.point:
                            p_ = self.mapFromScene(self.__backend__.x,
                                                self.__backend__.y)
                            
                            r_ = self.mapRectFromScene(self.__backend__.x,
                                                    self.__backend__.y,
                                                    self.__backend__.w,
                                                    self.__backend__.h)
                            
                            painter.drawPoint(p_)

                            painter.drawEllipse(r_)
                            
                        else: # general Path backend, including polyline, polygon
                            path = self.__backend__.asPath(frame=self._currentframe_)
                            
                            qpath = self.mapFromScene(path())
                            
                            painter.drawPath(qpath)
                            
                    labelPos = self.boundingRect().center()
                    
                    if self.editMode:
                        # NOTE: 2018-01-24 16:14:15
                        # CONTROL AND HOVER POINTS AND CONTROL LINES IN EDIT MODE
                        
                        painter.setPen(self._controlPointPen)
                        painter.setBrush(self._controlPointBrush)
                        
                        # ATTENTION for paths, curves have extra control points!
                        
                        if self.__cachedPath__ is not None and len(self.__cachedPath__) > 0:
                            if self.objectType & GraphicsObjectType.path:
                                for k, element in enumerate(self.__cachedPath__):
                                    if isinstance(element, Quad):
                                        pt = self.mapFromScene(QtCore.QPointF(element.x, element.y))
                                        cp = self.mapFromScene(QtCore.QPointF(element.cx, element.cy))
                                        
                                        painter.drawEllipse(cp.x() - self._pointSize, \
                                                            cp.y() - self._pointSize, \
                                                            self._pointSize * 2., self._pointSize * 2.)
                                        
                                        painter.drawEllipse(pt.x() - self._pointSize, \
                                                            pt.y() - self._pointSize, \
                                                            self._pointSize * 2., self._pointSize * 2.)
                                        
                                        painter.drawLine(self.mapFromScene(self.__cachedPath__[k-1].point()), cp)
                                        painter.drawLine(cp, pt)
                                        
                                    elif isinstance(element, Cubic):
                                        pt  = self.mapFromScene(QtCore.QPointF(element.x, element.y))
                                        cp1 = self.mapFromScene(QtCore.QPointF(element.c1x, element.c1y))
                                        cp2 = self.mapFromScene(QtCore.QPointF(element.c2x, element.c2y))
                                        
                                        painter.drawEllipse(cp1, self._pointSize, self._pointSize)
                                        
                                        painter.drawEllipse(cp2, self._pointSize, self._pointSize)
                                        
                                        painter.drawEllipse(pt,  self._pointSize, self._pointSize)
                                        
                                        painter.drawLine(self.mapFromScene(self.__cachedPath__[k-1].point()), cp1)
                                        
                                        painter.drawLine(cp1, cp2)
                                        painter.drawLine(cp2, pt)
                                        
                                    else:
                                        
                                        pt = self.mapFromScene(QtCore.QPointF(element.x, element.y))
                                        
                                        painter.drawEllipse(pt, self._pointSize, self._pointSize)
                                        
                            elif self._objectType & (GraphicsObjectType.rectangle | GraphicsObjectType.ellipse):
                                p0 = self.mapFromScene(QtCore.QPointF(self.__cachedPath__[0].x, self.__cachedPath__[0].y))
                                
                                p1 = self.mapFromScene(QtCore.QPointF(self.__cachedPath__[1].x, self.__cachedPath__[1].y))
                                    
                                painter.drawEllipse(p0, self._pointSize, self._pointSize)
                                painter.drawLine(p0,p1)
                                painter.drawEllipse(p1, self._pointSize, self._pointSize)
                                    
                            else:
                                for k, element in enumerate(self.__cachedPath__):
                                    pt = self.mapFromScene(QtCore.QPointF(element.x, element.y))
                                    
                                    painter.drawEllipse(pt, self._pointSize, self._pointSize)
                                    
                                    if k > 0:
                                        painter.drawLine(self.mapFromScene(self.__cachedPath__[k-1].point()), 
                                                        self.mapFromScene(element.point()))

            # CAUTION: DO NOT DELETE when commented-out 
            # this paints the boundingRect() and shape() of the thing when
            # debugging
            #### BEGIN DEBUGGING
            #painter.fillRect(self.boundingRect(), self._controlPointBrush)
            #painter.fillPath(self.shape(), self._testBrush)
            #painter.setPen(QtCore.Qt.darkRed)
            #painter.drawPath(self.shape())
            #### END DEBUGGING

            if self._showlabel:
                if len(self._displayStr) > 0 and labelPos is not None:
                    pen = painter.pen()
                    bgMode = painter.backgroundMode()
                    bg = painter.background()
                    
                    if self._opaqueLabel:
                        painter.setBackgroundMode(QtCore.Qt.OpaqueMode)
                        self._textBackgroundBrush.setStyle(QtCore.Qt.SolidPattern)
                        
                    else:
                        self._textBackgroundBrush.setStyle(QtCore.Qt.NoBrush)
                        
                    painter.setPen(textPen)
                        
                    painter.setBackground(self._textBackgroundBrush)
                        
                    painter.drawText(labelPos, self._displayStr)
                    
                    painter.setBackground(bg)
                    painter.setBackgroundMode(bgMode)
                    painter.setPen(pen)
            
        except Exception as exc:
            traceback.print_exc()
            print("in %s %s" % (self.objectType, self.name))
            
            
    @safeWrapper
    def itemChange(self, change, value):
        """Customizes the cursor movement by mouse or keyboard.
        
        1. For vertical/horizontal cursors: 
            1.1 restricts the movement of the _MAIN_ cursor line (the long line) 
                and label to the perpendicular direction; 
            1.2 allows the movement of the window bar along the direction of the
                _MAIN_ cursor line (basically, the window bar moves unrestricted)
            
        2. For crosshair cursors: 
            2.1 moves the center of the cursor but readjust the geometry of the 
                cursor lines such that they always span the entire image
            2.2 the label movement is restricted horizontally (label is attached
                to the vertical cursor line)
        
         1 & 2 achieved by partially restricting the new position and/or repainting.
         
        3. For non-cursors:
            just pudates the backen'd x and y coordinates (the effects of which
            depend on what the backend is) for the current frame
        """
        # TODO because this changes the backend, we must ensure the backend
        # in turn updates all OTHER frontends it may have !!!
        
        # NOTE: 2017-08-11 13:12:24
        #
        # trap here position changes for cursors (ONLY) so that we can constrain
        # the movement of their components:
        #
        # 1) for vertical cursors, the main line and label are only allowed to
        # move horizontally
        #
        # 2) for horizontal cursors, the main line and label are only allowed to 
        # move vertically;
        #
        # 3) for crosshair cursors, the main lines must be trimmed/grown at the 
        # opposite ends according the thir direction of move (such that the main
        # cursor lines always span the scene rectangle)
        #
        # 4) in addition, the window bars (small whiskers perpendicular to the 
        # main cursor line) are allowed to move in both orthogonal directions
        # i.e. allow vertical movement for the whiskers of a vertical cursor, 
        # and horizontal movement for the whiskers of a horizontal cursor
        
        #print("itemChange value: %s" % self.name, value)
        
        
        #NOTE: 2018-01-23 18:01:36
        # ATTENTION only check for backend when position changed
        # in buildmode there is neither __backend__ nor _graphicsShapedItem
        # if you return early without calling super().itemChange
        # the item wont be added to the scene when value is scene change!
        
        #print("self._deltaPos: ", self._deltaPos)
        
        if change == QtWidgets.QGraphicsItem.ItemPositionChange and self.scene():
            if self.__backend__ is None:
                return QtCore.QPoint()
            
            if not self.__backend__.hasStateForFrame(self._currentframe_) or\
                    not self.__objectVisible__:
                value = QtCore.QPointF()
                return value
            
            if self.objectType & GraphicsObjectType.allCursorTypes:
                # cursor types
                stateDescriptor = self.__backend__.getState(self.__backend__.currentFrame)
                
                if stateDescriptor is None or len(stateDescriptor) == 0:
                    return value
                
                # NOTE 2018-01-18 16:57:28
                # ATTENTION This is also called by self.setPos() (inherited)
                self._positionChangeHasBegun = True # flag used in __drawCursor__()
                
                newPos = value
                
                # vertical cursors
                if self._objectType == GraphicsObjectType.vertical_cursor:
                    if not self.pos().isNull():
                        self._deltaPos = (newPos - self.pos())

                    newPos.setY(self.pos().y()) # restrict movement to horizontal axis only
                    
                    if newPos.x() < 0:
                        newPos.setX(0.0)
                        
                    elif newPos.x() > self.__backend__.width:
                        newPos.setX(self.__backend__.width)

                # horizontal cursors
                elif self._objectType == GraphicsObjectType.horizontal_cursor:
                    if not self.pos().isNull():
                        self._deltaPos = (newPos - self.pos())

                    newPos.setX(self.pos().x()) # restrict movement to vertical axis only

                    if newPos.y() < 0:
                        newPos.setY(0.0)
                        
                    elif newPos.y() > self.__backend__.height:
                        newPos.setY(self.__backend__.height)

                # crosshair cursors
                elif self._objectType == GraphicsObjectType.crosshair_cursor:
                    if newPos.x() <= 0.0:
                        newPos.setX(0.0)
                        
                    if newPos.x() > self.__backend__.width:
                        newPos.setX(self.__backend__.width)

                    if newPos.y() <= 0.0:
                        newPos.setY(0.0)
                        
                    if newPos.y() > self.__backend__.height:
                        newPos.setY(self.__backend__.height)
                        
                    self._deltaPos = (newPos - QtCore.QPointF(self.__backend__.x, self.__backend__.y))
                    
                else: # point cursors
                    if newPos.x() <= 0.0:
                        newPos.setX(0.0)
                        
                    if newPos.x() > self.__backend__.width:
                        newPos.setX(self.__backend__.width)

                    if newPos.y() <= 0.0:
                        newPos.setY(0.0)
                        
                    if newPos.y() > self.__backend__.height:
                        newPos.setY(self.__backend__.height)
                        
                    self._deltaPos = (newPos - QtCore.QPointF(self.__backend__.x, self.__backend__.y))
                    
                # NOTE: 2018-01-18 15:44:28
                # CAUTION value is already in scene coordinates, so no mapping needed
                # here; 
                self.__backend__.x = newPos.x()
                self.__backend__.y = newPos.y()
                
            elif self._objectType & GraphicsObjectType.allShapeTypes:
                #non-cursor types
                self.__backend__.x = value.x()
                self.__backend__.y = value.y()
                
            self.__backend__.updateLinkedObjects()

            #self.__drawObject__()
            
            if self._labelShowsCoordinates:
                self.__setDisplayStr__()
                
                self.__updateLabelRect__()
                
            self.update()
            
            self.signalBackendChanged.emit(self.__backend__)
        
            self.signalGraphicsObjectPositionChange.emit(self.mapToScene(value - self._oldPos))
            
            self._oldPos = self.pos()
                
        # NOTE: 2017-08-11 13:19:28
        #
        # selection change is applied to all GraphicsObject types, not just cursors
        #
        elif change == QtWidgets.QGraphicsItem.ItemSelectedChange and self.scene() is not None:
            # NOTE: ZValue refers to the stack ordering of the graphics items in the scene
            # and it has nothing to do with frame visibility.
            if value:
                nItems = len(self.scene().items())
                self.setZValue(nItems+1)
                
            else:
                self.setZValue(0)
                
            self.selectMe.emit(self._ID_, value)
            
        elif change == QtWidgets.QGraphicsItem.ItemScenePositionHasChanged and self.scene() is not None:
            # NOTE: NOT used for now...
            pass

        elif change == QtWidgets.QGraphicsItem.ItemSceneHasChanged: # now self.scene() is the NEW scene
            self.__drawObject__()

        self._oldPos = self.pos()
            
        return super(GraphicsObject, self).itemChange(change, value)

    @safeWrapper
    def mousePressEvent(self, evt):
        """Mouse press event handler.
        
        In build mode, entered when the ROI type has not beed pre-determined at 
        __init__(), keyboard modifiers determine what type of ROI is being created
        when the first point is generated with a mouse press:
        
            SHIFT             => rectangle
            CTRL              => ellipse
            ALT               => path
            CTRL SHIFT        => polygon
            ALT CTRL SHIFT    => point
            anything else     => line   (default)
        
        When ROI type is path, CTRL + ALT modifier creates a subpath.
        
        When ROI type is path and we are in _curveBuild mode, CTRL + ALT modifiers
        create a second control point, to create a cubic Bezier curve.
        
        
        """
        self.setCursor(QtCore.Qt.ClosedHandCursor)
        
        if self._buildMode: # this is ALWAYS False for cursors
            self.setCursor(QtCore.Qt.CrossCursor)
            # NOTE: 2017-08-21 22:21:58
            # to avoid confusions, determine ONCE AND FOR ALL the object type 
            # according to key modifiers, at FIRST PRESS (i.e. when _cachedPath
            # is empty) as follows:
            #
            # SHIFT             => rectangle
            # CTRL              => ellipse
            # ALT               => path
            # CTRL SHIFT        => polygon
            # ALT CTRL SHIFT    => point
            # anything else     => line
            #
            #
            # When ROI type is not determined by the call to __init__(), we build
            # a line ROI by default; keyboard modifiers can change the type of ROI
            # being built.
            #
            
            #print("scenepos: ", evt.scenePos())
            #pressPos = evt.pos()
            
            if self.objectType == GraphicsObjectType.allShapeTypes and \
                len(self.__cachedPath__) == 0:
                # before adding first point, cheeck key modifiers and set
                # self._objectType accordingly
                
                # NOTE: 2018-01-23 22:41:05
                # ATTENTION: do not delete commented-out "mods" code -- for debugging
                
                mods = ""
                
                if evt.modifiers() == QtCore.Qt.ShiftModifier: 
                    ###SHIFT => rectangle
                    self._objectType = GraphicsObjectType.rectangle
                    mods = "shift"
                    
                elif evt.modifiers() == QtCore.Qt.ControlModifier: 
                    ###CTRL => ellipse
                    self._objectType = GraphicsObjectType.ellipse
                    mods = "ctrl"
                    
                elif evt.modifiers() ==  QtCore.Qt.AltModifier: 
                    ###ALT => path
                    self._objectType = GraphicsObjectType.path
                    mods = "alt"
                
                elif evt.modifiers() == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
                    ###CTRL+SHIFT => polygon
                    self._objectType = GraphicsObjectType.polygon
                    mods = "ctrl+shift"
                    
                elif evt.modifiers() == (QtCore.Qt.AltModifier | QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
                    ###ALt+CTRL+SHIFT => point
                    mods = "alt+=ctrl+shift"
                    self._objectType = GraphicsObjectType.point
                    
                else: 
                    if evt.modifiers() == QtCore.Qt.NoModifier:
                        mods = "none"
                        
                    ###anything else, or no modifiers => line
                    self._objectType = GraphicsObjectType.line
            
                #print("press at: ", evt.pos(), " mods: ", mods)
                
            if len(self.__cachedPath__) == 0:
                # add first point
                self.__cachedPath__.append(Move(evt.pos().x(), evt.pos().y()))
                
                if self.objectType & GraphicsObjectType.point:
                    # stop here if building just a point
                    self.__finalizeShape__()
                    
                #return
                
            else:
                #print("last press: ", evt.pos(), " hover point: ", self._hover_point)
                
                # there are previous points in the _cachedPath
                # check if evt.pos() is "over" the last point in the _cachedPath
                #d = QtCore.QLineF(evt.pos(), self.__cachedPath__[-1].point()).length()
                d = QtCore.QLineF(self._hover_point, self.__cachedPath__[-1].point()).length()
                
                # NOTE: self._constrainedPoint is set by mouse hover event handler
                # we set it to None after using it, here
                if d > 2 * self._pointSize: # press event fired far away from last point
                    if self.objectType & (GraphicsObjectType.line | GraphicsObjectType.rectangle | GraphicsObjectType.ellipse):
                        # does nothing is self.__cachedPath__ already has more than one point
                        if len(self.__cachedPath__) == 1:
                            # there is only one point prior to this one
                            
                            if self._constrainedPoint is not None and not self._constrainedPoint.isNull():
                                # append a constrained point is any
                                self.__cachedPath__.append(Line(self._constrainedPoint.x(), self._constrainedPoint.y()))
                                self._constrainedPoint = None
                                
                            else:
                                # else append this point
                                if self._hover_point is not None and not self._hover_point.isNull():
                                    
                                    self.__cachedPath__.append(Line(self._hover_point.x(), self._hover_point.y()))
                                    
                                else:
                                    self.__cachedPath__.append(Line(evt.pos().x(), evt.pos().y()))
                                
                            #print("to finalize: ", self.__cachedPath__)
                            
                            self.__finalizeShape__()
                            
                            #return
                        
                    elif self.objectType & GraphicsObjectType.polygon:
                        if self._constrainedPoint is not None:
                                self.__cachedPath__.append(Line(self._constrainedPoint.x(), self._constrainedPoint.y()))
                                self._constrainedPoint = None
                                
                        else:
                            self.__cachedPath__.append(Line(evt.pos().x(), evt.pos().y()))
                            
                        #self.update()
                        
                        #return
                    
                    elif self.objectType & GraphicsObjectType.path:
                        if self._curveBuild:
                            # self._curveBuild is set in mouse move event handler
                            if evt.modifiers() == (QtCore.Qt.ControlModifier | QtCore.Qt.AltModifier):
                                self._control_points[1] = evt.pos()

                            else:
                                if self._control_points[0] is not None:
                                    if self._control_points[1] is not None:
                                        self.__cachedPath__.append(Cubic(evt.pos().x(),
                                                                      evt.pos().y(),
                                                                      self._control_points[0].x(),
                                                                      self._control_points[0].y(),
                                                                      self._control_points[1].x(),
                                                                      self._control_points[1].y()))
                                        
                                        self._control_points[1] = None # cp has been used
                                        
                                    else:
                                        self.__cachedPath__.append(Quad(evt.pos().x(),
                                                                     evt.pos().y(),
                                                                     self._control_points[0].x(),
                                                                     self._control_points[0].y()))
                                        
                                    self._control_points[0] = None # cp has been used
                                    
                                    self._curveBuild = False
                                    
                        else:
                            if evt.modifiers() == (QtCore.Qt.ControlModifier | QtCore.Qt.AltModifier): # allow the creation of a subpath
                                self.__cachedPath__.append(Move(evt.pos().x(), evt.pos().y()))
                                
                            else:
                                if self._constrainedPoint is not None:
                                    self.__cachedPath__.append(Line(self._constrainedPoint.x(), self._constrainedPoint.y()))
                                    self._constrainedPoint = None
                                else:
                                    self.__cachedPath__.append(Line(evt.pos().x(), evt.pos().y()))

                else: # select the last point, possibly move it, if followed by mouse move
                    self._movePoint = True
            
            self.update() # force repaint, do not propagate event to superclass
            
            self.selectMe.emit(self._ID_, True)

        if self.editMode: # this is ALWAYS False for cursors
            # select a control point according to mouse event position
            # see qt5 examples/widgets/painting/pathstroke/pathstroke.cpp
            
            #if not self.hasStateDescriptor:
                #return
            
            distance = -1
            
            if self.__cachedPath__ is None or len(self.__cachedPath__) == 0:
                self.__cachedPath__ = self.__backend__.asPath(self._currentframe_) 
                self.__cachedPath__.frameIndices = [] # force current state into a common state

            for k, p in enumerate(self.__cachedPath__):
                #if isinstance(p, (Ellipse, Rect)):
                    ##FIXME what to do in case of a complex path containing rects, ellipses?
                    #d0 = QtCore.QLineF(evt.pos(), self.mapFromScene(p.points()[0])).length() # d = length of line between event pos and point pos
                    #d1 = QtCore.QLineF(evt.pos(), self.mapFromScene(p.points()[2])).length() # d = length of line between event pos and point pos
                    
                    #d = min(d0,d1)
                    
                    #if (distance < 0 and d <= 2 * self._pointSize) or d < distance:
                        #distance = d
                        #self._c_activePoint = k
                        
                        #if d == d0:
                            #self._c_shape_point = 0
                        #else:
                            #self._c_shape_point = 1
                            
                        #self._c_activeControlPoint = -1
                        
                if isinstance(p, Quad):
                    d = QtCore.QLineF(evt.pos(), self.mapFromScene(p.point())).length() # d = length of line between event pos and point pos
                    dc1 = QtCore.QLineF(evt.pos(), self.mapFromScene(QtCore.QPointF(p.cx, p.cy))).length()

                    self._c_shape_point = -1
                    
                    if dc1 < d:
                        if (distance <= 0 and dc1 <= 2 * self._pointSize) or dc1 < distance:
                            distance = dc1
                            self._c_activePoint = k
                            self._c_activeControlPoint = 0

                    else:
                        if (distance < 0 and d <= 2 * self._pointSize) or d < distance:
                            distance = d
                            self._c_activePoint = k
                            self._c_activeControlPoint = -1

                elif isinstance(p, Cubic):
                    d = QtCore.QLineF(evt.pos(), self.mapFromScene(p.point())).length() # d = length of line between event pos and point pos
                    dc1 = QtCore.QLineF(evt.pos(), self.mapFromScene(QtCore.QPointF(p.c1x, p.c1y))).length()
                    dc2 = QtCore.QLineF(evt.pos(), self.mapFromScene(QtCore.QPointF(p.c2x, p.c2y))).length()
                    #print("Cubic")
                    
                    self._c_shape_point = -1
                    
                    if dc1 < min(d, dc2):
                        if (distance <= 0 and dc1 <= 2 * self._pointSize) or dc1 < distance:
                            distance = dc1
                            self._c_activePoint = k
                            self._c_activeControlPoint = 0
                            
                    elif dc2 < min(d, dc1):
                        if (distance <= 0 and dc2 <= 2 * self._pointSize) or dc2 < distance:
                            distance = dc2
                            self._c_activePoint = k
                            self._c_activeControlPoint = 1
                            
                    elif d < min(dc1, dc2):
                        if (distance < 0 and d <= 2 * self._pointSize) or d < distance:
                            distance = d
                            self._c_activePoint = k
                            self._c_activeControlPoint = -1
                            
                    else:
                        if (distance < 0 and d <= 2 * self._pointSize) or d < distance:
                            distance = d
                            self._c_activePoint = k
                            self._c_activeControlPoint = -1

                else:
                    #print("Move or Line")
                    self._c_shape_point = -1
                    
                    d = QtCore.QLineF(evt.pos(), self.mapFromScene(p.point())).length() # d = length of line between event pos and point pos
                    if (distance < 0 and d <= 2 * self._pointSize) or d < distance:
                        distance = d
                        self._c_activePoint = k
                        self._c_activeControlPoint = -1
                        
            
            self.selectMe.emit(self._ID_, True)

            return

        super(GraphicsObject, self).mousePressEvent(evt)
        
        evt.accept()

    @safeWrapper
    def mouseMoveEvent(self, evt):
        """Mouse move event handler.
        
        In buildMode the type of ROI must have already been determined by the time
        this event is issued, either at __init__ or at the time of first mouse press event.
        
        Keyboard modifiers have the following effects (NOTE: they must be present
        throughout the sequence of mouse move events):
        
        CTRL:  => move in multiples of 45 degrees angles (snapping)
        
        SHIFT: => move on diagonal (e.g., for rectangles & ellipse, force them 
                  to be square and circle, respectively)
                  
        ALT:   => for path ROIs only, initiates the creation of a curved segment
                    (quadratic curve)

        """
        #print("mouse MOVE event position x: %g, y: %g"   % (evt.pos().x(), evt.pos().y()))
        #print("mouse MOVE event scene position x: %g, y: %g"   % (evt.scenePos().x(), evt.scenePos().y()))
        #print("mouse MOVE event from scene position x: %g, y: %g"   % (self.mapFromScene(evt.pos()).x(), self.mapFromScene(evt.pos()).y()))
        #print("mouse MOVE event to scene position x: %g, y: %g"   % (self.mapToScene(evt.pos()).x(), self.mapToScene(evt.pos()).y()))
        #print("MOVE")
        
        #print(self.__backend__.x)
        
        
        if self._buildMode: 
            #mods = "none" 
            # build mode exists only for non-cursors
            # if objectType is a path then generate a curve (mouse is pressed) otherwise behave as for hoverMoveEvent
            self.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
            
            currentPoint = evt.pos()
            
            if evt.modifiers() == QtCore.Qt.ControlModifier:
                mods = "ctrl"
                
                if len(self.__cachedPath__) > 0:
                    lastPoint = self.__cachedPath__[-1].point()
                    currentPoint = __constrain_0_45_90__(lastPoint, evt.pos())
                    
            elif evt.modifiers() == QtCore.Qt.ShiftModifier:
                mods = "shift"
                
                if len(self.__cachedPath__) > 0:
                    lastPoint = self.__cachedPath__[-1].point()
                    currentPoint = __constrain_square__(lastPoint, evt.pos())
                    
            elif evt.modifiers() == QtCore.Qt.AltModifier and self.objectType == GraphicsObjectType.path:
                mods ="alt"
                
                self._curveBuild = True # stays True until next mouse release or mouse press
                    
            #print("move at: ", evt.pos())
            #print("mods: ", mods)
            
            if self._movePoint:
                if len(self.__cachedPath__) > 0:
                    if isinstance(self.__cachedPath__[-1], Move):
                        self.__cachedPath__[-1] = Move(evt.pos().x(), evt.pos().y())
                        
                    elif isinstance(self.__cachedPath__[-1], Line):
                        self.__cachedPath__[-1] = Line(evt.pos().x(), evt.pos().y())
                        
                    elif isinstance(self.__cachedPath__[-1], Quad):
                        q = self.__cachedPath__[-1]
                        self.__cachedPath__[-1] = Quad(q.x1, q.y1, evt.pos().x(), evt.pos().y())
                        
                    elif isinstance(self.__cachedPath__[-1], Cubic): # because the path may have been "normalized"
                        c = self.__cachedPath__[-1]
                        self.__cachedPath__[-1] = Quad(c.x, c.y, c.x1, c.y1, evt.pos().x(), evt.pos().y())
                    
                
            else:
                self._hover_point = currentPoint
                self._control_points[0] = None # avoid confusion in paint()
                
            self.update()
            
            self.selectMe.emit(self._ID_, True)

            
            return

        else: #  NOT in build mode
            #if not self.hasStateDescriptor:
                #return
        
            self.setCursor(QtCore.Qt.ClosedHandCursor) # this is the windowing system mouse pointer !!!

            # NOTE: 2018-09-26 14:47:05
            # by design, editMode can only be True for non-cursors
            if self.editMode and self.__cachedPath__ is not None and len(self.__cachedPath__) \
                and self._c_activePoint >= 0 and self._c_activePoint < len(self.__cachedPath__):
                #self.prepareGeometryChange()
                element = self.__cachedPath__[self._c_activePoint]
                
                epos = self.mapToScene(evt.pos())
                
                if isinstance(element, Move):
                    self.__cachedPath__[self._c_activePoint] = Move(epos.x(), epos.y())
                    
                elif isinstance(element, Line):
                    self.__cachedPath__[self._c_activePoint] = Line(epos.x(), epos.y())
                    
                elif isinstance(element, Quad):
                    if self._c_activeControlPoint == 0:
                        self.__cachedPath__[self._c_activePoint] = Quad(cx=epos.x(), cy=epos.y(), \
                                                                    x=element.x, y=element.y, )
                        
                    else:
                        self.__cachedPath__[self._c_activePoint] = Quad(cx=element.cx, cy=element.cy, \
                                                                    x=epos.x(), y=epos.y())
                    
                elif isinstance(element, Cubic):
                    if self._c_activeControlPoint == 0:
                        self.__cachedPath__[self._c_activePoint] = Cubic(c1x=epos.x(), c1y=epos.y(), \
                                                                    c2x=element.c2x, c2y=element.c2y, \
                                                                    x=element.x, y=element.y, )
                        
                    elif self._c_activeControlPoint == 1:
                        self.__cachedPath__[self._c_activePoint] = Cubic(c1x=element.c1x, c1y=element.c1y, \
                                                                    c2x=epos.x(), c2y=epos.y(), \
                                                                    x=element.x, y=element.y)
                        
                    else:
                        self.__cachedPath__[self._c_activePoint] = Cubic(c1x=element.c1x, c1y=element.c1y, \
                                                                    c2x=element.c2x, c2y=element.c2y, \
                                                                    x=epos.x(), y=epos.y())
                        
                if self.__backend__ is not None:
                    self.__updateBackendFromCachedPath__()
                    self.signalBackendChanged.emit(self.__backend__)
            
                self.update() # calls paint() -- force repainting, do or propgate event to the superclass
                
                # NOTE: 2017-08-11 16:43:12
                # do NOT EVER call this here !!!
                # leave commented-out code as a reminder
                # ### super(GraphicsObject, self).mouseMoveEvent(evt)
                # ###
                #return

            elif self.canMove: # this will also change the position of the control points!
                # NOTE: itemChange changes the backend directly!, then
                # we call update
                if self.__backend__ is not None:
                    #self.__updateBackendFromCachedPath__() # just DON'T
                    self.signalBackendChanged.emit(self.__backend__)
                    
                    for f in self.__backend__.frontends:
                        if f != self:
                            f.redraw()
            
                self.signalPosition[int, str, "QPointF"].emit(self.objectType.value, self._ID_, self.pos())
                #self.__updateCachedPathFromBackend__()
                # NOTE 2017-08-12 13:22:26
                # this IS NEEDED for cursor movement by mouse !!!!
                # backend updating for cursors is dealt with in itemChange
                super(GraphicsObject, self).mouseMoveEvent(evt)

            
            self.selectMe.emit(self._ID_, True)

    @safeWrapper
    def mouseReleaseEvent(self, evt):
        """Mouse release event handler
        """
        #if not self.hasStateDescriptor:
            #return
            
        #print(self.__backend__.x)
        self._c_activePoint = -1 # restore this anyway!
        
        self.unsetCursor()
        
        if self._buildMode: # this is ALWAYS False for cursors
            # do something here ONLY if release is at some distance from most recent mouse press
            # NOTE: 2018-01-23 22:39:55
            # ATTENTION do not delete  -- for debugging
            mods = "" 
            if evt.modifiers() == QtCore.Qt.ShiftModifier:
                mods = "shift"
                
            elif evt.modifiers() == QtCore.Qt.ControlModifier: 
                mods = "ctrl"
                
            elif evt.modifiers() == QtCore.Qt.AltModifier: 
                mods ="alt"
                
            elif evt.modifiers() == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
                mods = "ctrl+shift"
                
            elif evt.modifiers() == (QtCore.Qt.AltModifier | QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
                mods = "alt+ctrl+shift"
                
            elif evt.modifiers() == QtCore.Qt.NoModifier:
                mods = "none"
                
            #print("release at: ", evt.pos(), " mods: ", mods)
            #print("obj type: ", self._objectType)
            
            if self._curveBuild:
                if self._control_points[1] is None: # we allow mod of 1st cp when there is no 2nd cp
                    self._control_points[0] = evt.pos()
                    
            self._hover_point = evt.pos()
            
            #super(GraphicsObject, self).mouseReleaseEvent(evt)
            self.update()
            return
            
        if self.canMove:
            # together with itemChange, this implements special treatment
            # of the object shape in the case of cursors (see notes in itemChange code)
            if self.objectType & GraphicsObjectType.allCursorTypes:
                stateDescriptor = self.__backend__.getState(self._currentframe_)
                
                if stateDescriptor is None or len(stateDescriptor) == 0:
                    return
                
                self._positionChangeHasBegun=False
                self._wbarPos += self._deltaPos
                    
                if self._wbarPos.x()< 0:
                    self._wbarPos.setX(0.0)
                    
                elif self._wbarPos.x() >= stateDescriptor.width:
                    self._wbarPos.setX(stateDescriptor.width-1)
                            
                if self._wbarPos.y()< 0:
                    self._wbarPos.setY(0.0)
                    
                elif self._wbarPos.y() >= stateDescriptor.height:
                    self._wbarPos.setY(stateDescriptor.height-1)
                
            self._oldPos = self.pos()
            self._deltaPos = QtCore.QPointF(0.0, 0.0)
            
        # NOTE: 2017-06-29 08:40:08# don't do this -- it disturbs the crosshair lines
        #self._deltaPos.setX(0)
        #self._deltaPos.setY(0)
        
            
        self.selectMe.emit(self._ID_, True)

        super(GraphicsObject, self).mouseReleaseEvent(evt)
        
        evt.accept()

    #@safeWrapper
    #"def" mouseDoubleClickEvent(self, evt):
        #"""Mouse double-click event handler - do I need this ???
        #"""
        ## TODO: bring up cursor properties dialog
        ## NOTE: if in buildMode, end ROI construction 
        #if self._buildMode:
            #self.__finalizeShape__()
            
        #self.selectMe.emit(self._ID_, True)

        #super(GraphicsObject, self).mouseDoubleClickEvent(evt)

    @safeWrapper
    def contextMenuEvent(self, evt):
        """
        #TODO: popup context menu => Edit, Link/Unlink, Remove
        """
        self.selectMe.emit(self._ID_, True)

        self.requestContextMenu.emit(self.ID, evt.screenPos())
        
        super(GraphicsObject, self).contextMenuEvent(evt)
        
        evt.accept()# so that this doesn't propagate to the underlying graphics items
        
    @safeWrapper
    def hoverEnterEvent(self, evt):
        if self._buildMode:
            self.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
            
        if self.editMode:
            d = [QtCore.QLineF(evt.pos(), self.mapFromScene(p)).length() for p in self.__cachedPath__.qPoints()]
            #print(d)
            #if self._objectType & (GraphicsObjectType.rectangle | GraphicsObjectType.ellipse):
                #d0 = QtCore.QLineF(evt.pos(), self.mapFromScene(self.__cachedPath__[0].points()[0])).length() # d = length of line between event pos and point pos
                #d1 = QtCore.QLineF(evt.pos(), self.mapFromScene(self.__cachedPath__[1].points()[2])).length() # d = length of line between event pos and point pos
            
                #d = [d0,d1]
                
            #else:
                #d = [QtCore.QLineF(evt.pos(), self.mapFromScene(p)).length() for p in self.__cachedPath__.qPoints()]
                
            if min(d) <= 2 * self._pointSize:
                self.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
                
            else:
                self.unsetCursor()

        self.update()
        
        super(GraphicsObject, self).hoverEnterEvent(evt)
        
    @safeWrapper
    def hoverMoveEvent(self, evt):
        """Hover move event handler.
        
        In buildMode the type of ROI must have already been determined by the time
        this event is issued, either at __init__ or at the time of first mouse press event.
        
        Keyboard modifiers here serve to constrain any moves (NOTE: they must be
        present throughout the sequence of hover move events):
        
        CTRL:  => move in multiples of 45 degrees angles (snapping)
        
        SHIFT: => move on diagonal (e.g., for rectangles & ellipse, force them 
                  to be square and circle, respectively)
                  
        """
        #print("HOVER MOVE position x %g, y %g" % (evt.pos().x(), evt.pos().y()))
        #print("HOVER")
        
        if self._buildMode:
            self.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
            
            currentPoint = evt.pos()
            
            #NOTE 2018-01-23 22:39:28
            # ATTENTION do not delete -- for debugging
            #mods = "" 
            #if evt.modifiers() == QtCore.Qt.ShiftModifier:
                #mods = "shift"
                
            #elif evt.modifiers() == QtCore.Qt.ControlModifier: 
                #mods = "ctrl"
                
            #elif evt.modifiers() == QtCore.Qt.AltModifier: 
                #mods ="alt"
                
            #elif evt.modifiers() == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
                #mods = "ctrl+shift"
                
            #elif evt.modifiers() == (QtCore.Qt.AltModifier | QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
                #mods = "alt+ctrl+shift"
                
            #elif evt.modifiers() == QtCore.Qt.NoModifier:
                #mods = "none"
                
            #if len(self.__cachedPath__):
                #print("hovermove at :", evt.pos(), " mods ", mods)
            
            if evt.modifiers() == QtCore.Qt.ControlModifier:
                if len(self.__cachedPath__) > 0:
                    lastPoint = self.__cachedPath__[-1].point()
                    d = QtCore.QLineF(currentPoint, lastPoint).length()
                    
                    if d > 2 * self._pointSize:
                        currentPoint = __constrain_0_45_90__(lastPoint, evt.pos())
                        self._constrainedPoint = currentPoint
                    
            elif evt.modifiers() == QtCore.Qt.ShiftModifier:
                if len(self.__cachedPath__) > 0:
                    lastPoint = self.__cachedPath__[-1].point()
                    d = QtCore.QLineF(currentPoint, lastPoint).length()
                    
                    if d > 2 * self._pointSize:
                        currentPoint = __constrain_square__(lastPoint, evt.pos())
                        self._constrainedPoint = currentPoint
                    
            self._hover_point = currentPoint

            self.update()
            
            # NOTE do not call super().hoverMoveEvent here
            
            return
            
        if self.editMode and self.__cachedPath__ is not None and len(self.__cachedPath__):
            d = [QtCore.QLineF(evt.pos(), self.mapFromScene(p)).length() for p in self.__cachedPath__.qPoints()]
            #if self._objectType & (GraphicsObjectType.rectangle | GraphicsObjectType.ellipse):
                #d0 = QtCore.QLineF(evt.pos(), self.mapFromScene(self.__cachedPath__[0].points()[0])).length() # d = length of line between event pos and point pos
                #d1 = QtCore.QLineF(evt.pos(), self.mapFromScene(self.__cachedPath__[0].points()[2])).length() # d = length of line between event pos and point pos
            
                #d = [d0,d1]
                
            #else:
                #d = [QtCore.QLineF(evt.pos(), self.mapFromScene(p)).length() for p in self.__cachedPath__.qPoints()]
            
            if min(d) <= 2 * self._pointSize:
                self.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
                
            else:
                self.unsetCursor()

        self.update()
        
        super(GraphicsObject, self).hoverMoveEvent(evt)
        
    @safeWrapper
    def hoverLeaveEvent(self, evt):
        self.unsetCursor()
        self.update()
        #print("hover leave position x %g, y %g" % (evt.pos().x(), evt.pos().y()))
        super(GraphicsObject, self).hoverLeaveEvent(evt)
            
    @safeWrapper
    def keyPressEvent(self, evt):
        # NOTE: 2017-06-29 08:44:34
        # "up" means move down (coordinates origin are top-left !!!)
        #if not self.hasStateDescriptor:
            #return
        
        if evt.key() == QtCore.Qt.Key_Delete:
            self.signalROIConstructed.emit(0, self.name) # deregisters self with parent and removes it
            
        if self._buildMode:
            # exit build mode here
            if evt.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                self.__finalizeShape__()

            elif evt.key() == QtCore.Qt.Key_Escape:
                self._buildMode = False
                #self._graphicsShapedItem = None
                self._constrainedPoint = None
                self._curveSegmentConstruction = False
                self._hover_point = None
                self.__cachedPath__.clear()
                self.update()
                self.signalROIConstructed.emit(0, self.name) # in order to deregister self with the caller
                
            return
        
        if self.editMode:
            # exit edit mode here
            if evt.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter, QtCore.Qt.Key_Escape):
                self.editMode = False
                self.__cachedPath__.clear()
        
        if not self.canMove:
            return
        
        if self.objectType & GraphicsObjectType.allCursorTypes:
            if not self.hasStateDescriptor:
                return
            stateDescriptor = self.__backend__.getState(self._currentframe_)
            #if stateDescriptor is None or len(stateDescriptor) == 0:
                #return
            
            if self._objectType == GraphicsObjectType.vertical_cursor:
                if evt.key() == QtCore.Qt.Key_Right:
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        self.moveBy(10.0,0.0)
                        
                    else:
                        self.moveBy(1.0,0.0)
                        
                elif evt.key() == QtCore.Qt.Key_Left:
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        self.moveBy(-10.0, 0.0)
                        
                    else:
                        self.moveBy(-1.0, 0.0)
                        
                elif evt.key() == QtCore.Qt.Key_Up:
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        self._wbarPos += QtCore.QPointF(0.0,-10.0)
                        
                    else:
                        self._wbarPos += QtCore.QPointF(0.0,-1.0)
                        
                    if self._wbarPos.y()< 0:
                        self._wbarPos.setY(0.0)
                        
                    elif self._wbarPos.y() > stateDescriptor.height-1:
                        self._wbarPos.setY(stateDescriptor.height-1)
                        
                    self.__drawObject__()

                elif evt.key() == QtCore.Qt.Key_Down:
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        self._wbarPos += QtCore.QPointF(0.0,10.0)
                        
                    else:
                        self._wbarPos += QtCore.QPointF(0.0,1.0)
                        
                    if self._wbarPos.y()< 0:
                        self._wbarPos.setY(0.0)
                        
                    elif self._wbarPos.y() > stateDescriptor.height-1:
                        self._wbarPos.setY(stateDescriptor.height-1)
                        
                    self.__drawObject__()
                
            elif self._objectType == GraphicsObjectType.horizontal_cursor:
                if evt.key() == QtCore.Qt.Key_Right:
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        self._wbarPos += QtCore.QPointF(10.0, 0.0)
                        
                    else:
                        self._wbarPos += QtCore.QPointF(1.0, 0.0)
                        
                    if self._wbarPos.x()< 0:
                        self._wbarPos.setX(0.0)
                        
                    elif self._wbarPos.x() > stateDescriptor.width-1:
                        self._wbarPos.setX(stateDescriptor.width-1)
                        
                    self.__drawObject__()
                    
                elif evt.key() == QtCore.Qt.Key_Left:
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        self._wbarPos += QtCore.QPointF(-10.0, 0.0)
                        
                    else:
                        self._wbarPos += QtCore.QPointF(-1.0, 0.0)
                        
                    if self._wbarPos.x()< 0:
                        self._wbarPos.setX(0.0)
                        
                    elif self._wbarPos.x() > stateDescriptor.width-1:
                        self._wbarPos.setX(stateDescriptor.width-1)
                        
                    self.__drawObject__()
                    
                elif evt.key() == QtCore.Qt.Key_Up:
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        self.moveBy(0.0,-10.0)
                        
                    else:
                        self.moveBy(0.0,-1.0)
                        
                elif evt.key() == QtCore.Qt.Key_Down:
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        self.moveBy(0.0,10.0)
                        
                    else:
                        self.moveBy(0.0,1.0)
                        
            elif self._objectType == GraphicsObjectType.crosshair_cursor:
                if evt.key() == QtCore.Qt.Key_Right:
                    moveX = 1.0
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        moveX = 10.0
                    
                    newX = self.pos().x() + moveX
                    
                    if newX > self.__backend__.width-1:
                        moveX = self.__backend__.width-1 - self.pos().x()
                    
                    #if newX > stateDescriptor.width-1:
                        #moveX = stateDescriptor.width-1 - self.pos().x()
                    
                    self.moveBy(moveX, 0.0)
                        
                elif evt.key() == QtCore.Qt.Key_Left:
                    moveX = -1.0
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        moveX = -10.0
                        
                    newX = self.pos().x() + moveX
                    
                    if newX < 0 :
                        moveX = 0 - self.pos().x()
                    
                    self.moveBy(moveX, 0.0)
                    
                elif evt.key() == QtCore.Qt.Key_Up:
                    moveY = -1.0
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        moveY = -10.0
                        
                    newY = self.pos().y() + moveY
                    
                    if newY < 0:
                        moveY = 0 - self.pos().y()
                        
                    self.moveBy(0.0, moveY)

                elif evt.key() == QtCore.Qt.Key_Down:
                    moveY = 1.0
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        moveY = 10.0
                        
                    newY = self.pos().y() + moveY
                    
                    if newY > self.__backend__.height-1:
                        moveY = self.__backend__.height-1 - self.pos().y
                        
                    #if newY > stateDescriptor.height-1:
                        #newY = stateDescriptor.height-1 - self.pos().y()
                        
                    self.moveBy(0.0, moveY)
                    #self.__backend__.y += moveY
                        
                if self.pos().x() < 0:
                    y = self.pos().y()
                    self.setPos(0, y)
                    
                elif self.pos().x() > self.__backend__.width-1:
                    y = self.pos().y()
                    self.setPos(self.__backend__.width-1, y)
                    
                #elif self.pos().x() > stateDescriptor.width-1:
                    #y = self.pos().y()
                    #self.setPos(stateDescriptor.width-1, y)
                    
                if self.pos().y() < 0:
                    x = self.pos().x()
                    self.setPos(x, 0)
                    
                elif self.pos().y() > self.__backend__.height-1:
                    x = self.pos().x()
                    self.setPos(x, self.__backend__.height-1)
                    
                #elif self.pos().y() > stateDescriptor.height-1:
                    #x = self.pos().x()
                    #self.setPos(x, stateDescriptor.height-1)
                    
            else:
                if evt.key() == QtCore.Qt.Key_Right:
                    moveX = 1.0
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        moveX = 10.0
                    
                    self.moveBy(moveX, 0.0)
                                        
                elif evt.key() == QtCore.Qt.Key_Left:
                    moveX = -1.0
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        moveX = -10.0
                        
                    self.moveBy(moveX, 0.0)
                        
                elif evt.key() == QtCore.Qt.Key_Up:
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        self.moveBy(0.0,-10.0)
                        
                    else:
                        self.moveBy(0.0,-1.0)
                        
                elif evt.key() == QtCore.Qt.Key_Down:
                    if evt.modifiers() & QtCore.Qt.ShiftModifier:
                        self.moveBy(0.0,10.0)
                        
                    else:
                        self.moveBy(0.0,1.0)
                        
                if self.pos().x() < 0:
                    y = self.pos().y()
                    self.setPos(0, y)
                    
                elif self.pos().x() > self.__backend__.width-1:
                    y = self.pos().y()
                    self.setPos(self.__backend__.width-1, y)
                    
                #elif self.pos().x() > stateDescriptor.width-1:
                    #y = self.pos().y()
                    #self.setPos(stateDescriptor.width-1, y)
                    
                if self.pos().y() < 0:
                    x = self.pos().x()
                    self.setPos(x, 0)
                    
                elif self.pos().y() > self.__backend__.height-1:
                    x = self.pos().x()
                    self.setPos(x, self.__backend__.height-1)
                    
                #elif self.pos().y() > stateDescriptor.height-1:
                    #x = self.pos().x()
                    #self.setPos(x, stateDescriptor.height-1)
                    
        else:
            # non-cursor types
            if evt.key() == QtCore.Qt.Key_Right:
                if evt.modifiers() & QtCore.Qt.ShiftModifier:
                    self.moveBy(10.0,0.0)
                    
                else:
                    self.moveBy(1.0,0.0)
                    
            elif evt.key() == QtCore.Qt.Key_Left:
                if evt.modifiers() & QtCore.Qt.ShiftModifier:
                    self.moveBy(-10.0,0.0)
                    
                else:
                    self.moveBy(-1.0, 0.0)
                    
            elif evt.key() == QtCore.Qt.Key_Up:
                if evt.modifiers() & QtCore.Qt.ShiftModifier:
                    self.moveBy(0.0, -10.0)
                    
                else:
                    self.moveBy(0.0,-1.0)

            elif evt.key() == QtCore.Qt.Key_Down:
                if evt.modifiers() & QtCore.Qt.ShiftModifier:
                    self.moveBy(0.0,10.0)
                    
                else:
                    self.moveBy(0.0,1.0)
                    
        self.__drawObject__()
        self.update()

        super(GraphicsObject, self).keyPressEvent(evt)
        
    def setDefaultAppearance(self):
        self._textPen                = self.defaultTextPen
        self._textBrush              = self.defaultTextBrush
        self._textBackgroundBrush    = self.defaultTextBackgroundBrush
        
        self._textFont           = self.defaultTextFont
        
        self._linkedTextPen      = self.defaultLinkedTextPen
        self._linkedTextBrush    = self.defaultLinkedTextBrush
        
        self._cursorPen          = self.defaultPen
        self._selectedCursorPen  = self.defaultSelectedPen
        
        self._linkedPen          = self.defaultLinkedPen
        self._linkedSelectedPen  = self.defaultLinkedSelectedPen
        
        self._cBPen              = self.defaultCBPen
        self._cBSelectedPen      = self.defaultCBSelectedPen
        
        self._opaqueLabel = True
        
        self._labelShowsCoordinates = False
        
        self.__drawObject__()
        
        self.update()
        
    def sharesBackendWith(self, other):
        return other in self.__backend__.frontends and self.__backend__ == other.backend
    
    @property
    def hasTransparentLabel(self):
        return not self._opaqueLabel
    
    def setTransparentLabel(self, value):
        self._opaqueLabel = not value
        
        self.redraw()
        #self.update()
        
    @property
    def sharesBackend(self):
        return len(self.__backend__.frontends) > 0
        
    #@property
    #"def" linked(self):
        #"""Returns a dict of GraphicsObject instances to which this object is linked with
        #"""
        #return self._linkedGraphicsObjects
        
                
    @pyqtSlot(int)
    @safeWrapper
    def slotFrameChanged(self, val):
        #print("slotFrameChanged")
        self._currentframe_ = val
        if self.__backend__ is not None:
            self.__backend__.currentFrame = val
            
            self.__backend__.updateLinkedObjects()
            
            self.setVisible(len(self.__backend__.frameIndices) > 0 or self.__backend__.hasStateForFrame(val))
            #self.setVisible(len(self.__backend__.frameIndices) == 0 or val in self.__backend__.frameIndices)
            
            if self.__objectVisible__:
                self.redraw()
            
            if len(self._linkedGraphicsObjects):
                for c in self._linkedGraphicsObjects.values():
                    if c != self:
                        c._currentframe_ = val
                        c.setVisible(len(c.__backend__.frameIndices) > 0 or c.__backend__.hasStateForFrame(val))
                        #c.setVisible(len(c.__backend__.frameIndices) == 0 or val in c.__backend__.frameIndices)
                        if c.__objectVisible__:
                            c.redraw()

    @pyqtSlot("QPointF")
    @safeWrapper
    def slotLinkedGraphicsObjectPositionChange(self, deltapos):
        """Catched signals emitted by linked graphics objects
        """
        other = self.sender()
        if self._currentframe_ == other._currentframe_:
            if self.hasStateDescriptor and other.hasStateDescriptor:
                
                self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, False)
                self.setFlag(QtWidgets.QGraphicsItem.ItemSendsScenePositionChanges, False)
                
                self.setPos(self.pos() + self.mapFromScene(deltapos))
                                    
                if self._labelShowsCoordinates:
                    self.__setDisplayStr__()
                    self.__updateLabelRect__()
                    
                self.update()
                    
                self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
                self.setFlag(QtWidgets.QGraphicsItem.ItemSendsScenePositionChanges, True)
        
    @property
    def visible(self):
        ret =  self.__objectVisible__ and super(GraphicsObject, self).isVisible()
            
        return ret
        
    @visible.setter
    def visible(self, value):
        if not isinstance(value, bool):
            raise TypeError("Expecting a bool value; got %s instead" % type(value).__name__)
        
        self.__objectVisible__ = value
        super(GraphicsObject, self).setVisible(value)
            
        self.update()
            
    def isVisible(self):
        ret =  self.__objectVisible__ and super(GraphicsObject, self).isVisible()
            
        return ret
        
    def setVisible(self, value):
        #print("%s setVisible %s in frame %d" % (self.ID, value, self._currentframe_))
        #if isinstance(value, bool):
        self.__objectVisible__ = value
        super(GraphicsObject, self).setVisible(value)
            
        self.update()
            
    @safeWrapper
    def __updateBackendFromCachedPath__(self):
        """Updates the backend primitive from this object, it being a ROI
        TODO/FIXME for now only supports Ellipse, Rect, and Path backends
        TODO expand for line, etc.
        NOTE: do not use for cursors !
        ATTENTION: does not work when __backend__ is None
        """
        if self.__cachedPath__ is None or len(self.__cachedPath__) == 0:
            return
        
        if self.__backend__ is None:
            self.__backend__ = self.__cachedPath__.copy()
        
        # this is a reference; modifying stateDescriptor attributes effectively
        # modified self.__backend__ state for _currentframe_
        #stateDescriptor = self.__backend__.getState(self._currentframe_)
        
        #if len(stateDescriptor):
        
        # NOTE: 2019-03-25 20:44:39
        # TODO code for all non-Cursor types!
        if isinstance(self.__backend__, (Ellipse, Rect)) and len(self.__cachedPath__) >= 2:
            if self.hasStateDescriptor:
                self.__backend__.x = self.__cachedPath__[0].x
                
                self.__backend__.y = self.__cachedPath__[0].y
                
                self.__backend__.w = self.__cachedPath__[1].x - self.__cachedPath__[0].x
                
                self.__backend__.h = self.__cachedPath__[1].y - self.__cachedPath__[0].y
                
                self.__backend__.updateLinkedObjects()
                
        elif isinstance(self.__backend__, Path):
            try:
                for k, element in enumerate(self.__cachedPath__):
                    self.__backend__[k].x = element.x
                    self.__backend__[k].y = element.y
                    
                self.__backend__.updateLinkedObjects()
                    
            except Exception as e:
                traceback.print_exc()
                    
    #@safeWrapper
    def removeFromWidget(self):
        """Call this to have the GraphicsObject remove itself from the GraphicsImageViewerWidget
        """
        if type(self.parentwidget).__name__ == "ImageViewer":
            #print("GraphicsObject.removeFromWidget %s from %s" % (self.name, self.parentwidget.windowTitle()))
            self.parentwidget.removeGraphicsObject(self.name)
            
        elif type(self.parentwidget).__name__ == "GraphicsImageViewerWidget":
            if isinstance(self.__backend__, Cursor):
                self.parentwidget.removeCursorByName(self.name)
                
            else:
                self.parentwidget.removeRoiByName(self.name)
        
        
    # NOTE: 2017-06-26 22:38:06 properties
    #
    
    @property
    def parentwidget(self):
        return self._parentWidget
    
    @property
    def showLabel(self):
        return self._showlabel
    
    @showLabel.setter
    def showLabel(self, value):
        self._showlabel=value
        self.update()
    
    @property
    def backend(self):
        """Read-only!
        The backend is set up at __init__ and it may be None.
        """
        return self.__backend__
    
    @property
    def cachedPath(self):
        """Read-only
        """
        return self.__cachedPath__
    
    # NOTE: 2017-11-22 23:49:35
    # new property: a list of frame indices where this object is visible
    # if list is empty, this implies the object is visible in ALL frames
    # be careful: is the list contains only a frame index that is never reached
    # the object will never become visible
    @property
    def frameVisibility(self):
        return self.__backend__.frameIndices
    
    @frameVisibility.setter
    def frameVisibility(self, value):
        """
        value: int, a list of int or a range
        
        Ignored for Path objects (this is determined by inidividual elements of the Path)
        
        see PlanarGraphics.frameIndices property documentation for details
        
        """
        #print("frameVisibility.setter %s" % value)
        if isinstance(value, numbers.Integral):
            value = [value]
            
        elif isinstance(value, range):
            value = [v for v in value]
        
        if not isinstance(value, list):
            return
        
        if not isinstance(self.__backend__, Path):
            self.__backend__.frameIndices = value
        
        self.__backend__.updateLinkedObjects()
        
        self.update()
        
        for f in self.__backend__.frontends:
            if f != self:
                f.redraw()
        
        if len(self._linkedGraphicsObjects):
            # NOTE: this is now a list of backends!
            for c in self._linkedGraphicsObjects:
                if c != self.__backend__:
                    c.frameIndices = value
                    
                    for f in c.frontends:
                        if f != self:
                            f.redraw()

    @property
    def currentFrame(self):
        return self._currentframe_
        
    @currentFrame.setter
    def currentFrame(self, value):
        #print("currentFrame.setter ", value)
        self._currentframe_ = value
        
    @property
    def currentBackendFrame(self):
        return self.__backend__.currentFrame
    
    @currentBackendFrame.setter
    def currentBackendFrame(self, value):
        #print("currentBackendFrame.setter ", value)
        self.__backend__.currentFrame=value
        self.__backend__.updateLinkedObjects()
        
    @property
    def hasStateDescriptor(self):
        return self.__backend__.hasStateForFrame(self._currentframe_)
        
    @property
    def name(self):
        """Alias to self.ID
        """
        return self.ID
    
    @name.setter
    def name(self, val):
        self.ID = val
    
    @property
    def ID(self):
        """Name of this GUI GraphicsObject.
        This is kept in sync with the backend.name property
        """
        return self._ID_
    
    @ID.setter
    def ID(self, value):
        if isinstance(value, str):
            if len(value.strip()):
                if self._ID_ != value: # check to avoid recurrence
                    self._ID_ = value
                    self.signalIDChanged.emit(self._ID_)
                    self.redraw()
                    
                    #self.__backend__.name = value

                    #for f in self.__backend__.frontends:
                        #if f != self and f.name != value:
                            #old_name = f.name
                            #f._ID_ = value
                            
                            #if f._parentWidget is not None:
                                #cDict = f._parentWidget._graphicsObjects[f.objectType]
                                #cDict.pop(old_name, None)
                                #cDict[value] = f
                                
                            #f.redraw()
                    
            else:
                raise ValueError("value expected to be a non-empty string")
            
        else:
            raise TypeError("value expected to be a non-empty string; got %s instead" % type(value).__name__)
        
    @property
    def linkedToFrame(self):
        """Read-only
        To change, one can only manipulate "framesVisibility" property
        """
        return len(self._frameindex)
    
    #"@linkedToFrame.setter"
    #"def" linkedToFrame(self, val):
        #if val:
            
        #self._linkToFrame = val

    @property
    def labelShowsPosition(self):
        """When True, the coordinates will be displayed next to its name, on the label
        """
        return self._labelShowsCoordinates
    
    @labelShowsPosition.setter
    def labelShowsPosition(self, value):
        self._labelShowsCoordinates = value
        self.redraw()
        #self.__drawObject__()
        #self.update()
        
        for f in self.__backend__.frontends:
            if f != self:
                f._labelShowsCoordinates = value
                f.redraw()

    #@property
    #"def" shapedItem(self):
        #"""Returns the underlying QAbstractGraphicsShapeItem or None if this is a cursor.
         #Same as self.graphicsItem()
        #"""
        #return self._graphicsShapedItem

    @property
    def x(self):
        """The x coordinate
        """
        return self.pos().x()
    
    @x.setter
    def x(self, val):
        y = self.pos().y()
        self.setPos(val,y)
        
        for c in self._linkedGraphicsObjects:
            if c != self.__backend__:
                c.x = val
                
                for f in c.frontends:
                    if f != self:
                        f.redraw()
                    
    @property
    def horizontalWindow(self):
        if not self.hasStateDescriptor:
            return
        
        if self._objectType & GraphicsObjectType.allCursorTypes:
            stateDescriptor = self.__backend__.getState(self._currentframe_)
            
            if stateDescriptor and len(stateDescriptor):
                return stateDescriptor.xwindow
    
    @horizontalWindow.setter
    def horizontalWindow(self, val):
        if not self.hasStateDescriptor:
            return
        
        if self._objectType & GraphicsObjectType.allCursorTypes:
            stateDescriptor = self.__backend__.getState(self._currentframe_)
            
            if stateDescriptor is not None and len(stateDescriptor):
                stateDescriptor.xwindow = val
                self.__backend__.updateLinkedObjects()
                self.redraw()
            
                for f in self.__backend__.frontends:
                    if f != self:
                        f.redraw()
        
                if len(self._linkedGraphicsObjects):
                    for c in self._linkedGraphicsObjects:
                        if c != self.__backend__:
                            c.xwindow = val
                            
                            for f in c.frontends:
                                if f != self:
                                    f.redraw()
                                
    @property
    def xwindow(self):
        """Alias for the "horizontalWindow" property
        """
        return self.horizontalWindow
    
    @xwindow.setter
    def xwindow(self, val):
        self.horizontalWindow = val
    
    @property
    def y(self):
        """The y coordinate
        """
        return self.pos().y()
    
    @y.setter
    def y(self, val):
        x = self.pos().x()
        self.setPos(x,val)
        
        if len(self._linkedGraphicsObjects):
            for c in self._linkedGraphicsObjects:
                if c != self.__backend__:
                    c.y = val
                    
                    for f in c.frontends:
                        if f != self:
                            f.redraw()
                    
    @property
    def verticalWindow(self):
        if not self.hasStateDescriptor:
            return
        
        if self._objectType & GraphicsObjectType.allCursorTypes:
            stateDescriptor = self.__backend__.getState(self._currentframe_)
            if stateDescriptor is not None and len(stateDescriptor):
                return stateDescriptor.ywindow
    
    @verticalWindow.setter
    def verticalWindow(self, val):
        if not self.hasStateDescriptor:
            return
        
        if self._objectType & GraphicsObjectType.allCursorTypes:
            stateDescriptor = self.__backend__.getState(self._currentframe_)
            
            if stateDescriptor is not None and len(stateDescriptor):
                stateDescriptor.ywindow = val
                self.__backend__.updateLinkedObjects()
                self.redraw()
                
                for f in self.__backend__.frontends:
                    if f != self:
                        f.redraw()
        
                if len(self._linkedGraphicsObjects):
                    for c in self._linkedGraphicsObjects:
                        if c != self.__backend__:
                            c.ywindow = val
                            
                            for f in c.frontends:
                                if f != self:
                                    f.redraw()
                                
    @property
    def ywindow(self):
        """ Alias for the "verticalWindow" property
        """
        return self.verticalWindow
    
    @ywindow.setter
    def ywindow(self, val):
        self.verticalWindow = val
        
    @property
    def radius(self):
        if not self.hasStateDescriptor:
            return
        
        if self._objectType & GraphicsObjectType.allCursorTypes:
            stateDescriptor = self.__backend__.getState(self._currentframe_)
            if stateDescriptor is not None and len(stateDescriptor):
                return stateDescriptor.radius
    
    @radius.setter
    def radius(self, val):
        if not self.hasStateDescriptor:
            return
        
        if self._objectType & GraphicsObjectType.allCursorTypes:
            stateDescriptor = self.__backend__.getState(self._currentframe_)
            if stateDescriptor is not None and len(stateDescriptor):
                stateDescriptor.radius = val
                self.redraw()
                self.__backend__.updateLinkedObjects()
                self.__backend__.updateFrontends()
                
                for f in self.__backend__.frontends:
                    if f != self:
                        f.redraw()
                
                if len(self._linkedGraphicsObjects):
                    for c in self._linkedGraphicsObjects:
                        if c != self.__backend__:
                            c.radius = val
                            
                            for f in c.frontends:
                                if f != self:
                                    f.redraw()
                            
                        if c.objectType & GraphicsObjectType.allCursorTypes and c != self:
                            if c.currentFrame == self.currentFrame:
                                if c in self.__backend__.frontends:
                                    c.redraw()
                                else:
                                    c.radius  = stateDescriptor.radius
                                    
    @property
    def color(self):
        return self.penColor
    
    @color.setter
    def color(self, qcolor):
        """Set both the pen and text color to the same value
        """
        if isinstance(qcolor, QtGui.QColor) and qcolor.isValid():
            self._cursorPen.setColor(qcolor)
            self._selectedCursorPen.setColor(qcolor)
            self._textPen.setColor(qcolor)
            self.update()
    
    @property
    def linkedColor(self):
        return self.penColor
    
    @linkedColor.setter
    def linkedColor(self, qcolor):
        """Set both the pen and text color to the same value
        """
        if isinstance(qcolor, QtGui.QColor) and qcolor.isValid():
            self._linkedPen.setColor(qcolor)
            self._linkedTextPen.setColor(qcolor)
            self._linkedSelectedPen.setColor(qcolor)
            self.update()
    
    @property
    def penColor(self):
        return self._cursorPen.color()
    
    @penColor.setter
    def penColor(self, qcolor):
        if isinstance(qcolor, QtGui.QColor) and qcolor.isValid():
            self._cursorPen.setColor(qcolor)
            self._selectedCursorPen.setColor(qcolor)
            self.update()
        
    @property
    def colorForSharedBackend(self):
        return self._cBPen.color()
    
    @colorForSharedBackend.setter
    def colorForSharedBackend(self, qcolor):
        #print("GraphicsObject.colorForSharedBackend", qcolor)
        if isinstance(qcolor, QtGui.QColor) and qcolor.isValid():
            #print("GraphicsObject.colorForSharedBackend", qcolor.name())
            self._cBPen.setColor(qcolor)
            self._cBSelectedPen.setColor(qcolor)
            self._textCBPen.setColor(qcolor)
            #print("colorForSharedBackend %s" % self.name)
            self.update()
        
    @property
    def linkedPenColor(self):
        return self._linkedPen.color()
    
    @linkedPenColor.setter
    def linkedPenColor(self, qcolor):
        if isinstance(qcolor, QtGui.QColor) and qcolor.isValid():
            self._linkedPen.setColor(qcolor)
            self._linkedSelectedPen.setColor(qcolor)
            self._linkedTextPen.setColor(qcolor)
            self.update()
        
    @property
    def textColor(self):
        return self._textPen.color()
    
    @textColor.setter
    def textColor(self, qcolor):
        if isinstance(qcolor, QtGui.QColor) and qcolor.isValid():
            self._textPen.setColor(qcolor)
            self.update()
        
    @property
    def linkedTextColor(self):
        return self._linkedTextPen.color()
    
    @linkedTextColor.setter
    def linkedTextColor(self, qcolor):
        if isinstance(qcolor, QtGui.QColor) and qcolor.isValid():
            self._linkedTextPen.setColor(qcolor)
            self.update()
        
    @property
    def textBackground(self):
        return self._textBackgroundBrush
    
    @textBackground.setter
    def textBackground(self, brush):
        self._textBackgroundBrush = brush
        self.__drawObject__
        self.update()
        
    @property
    def opaqueLabel(self):
        return self._opaqueLabel
    
    @opaqueLabel.setter
    def opaqueLabel(self, val):
        self._opaqueLabel = val
        self.__drawObject__
        self.update()
        
    @property
    def labelFont(self):
        return self._textFont
    
    @labelFont.setter
    def labelFont(self, font):
        self._textFont = font
        self.__drawObject__
        self.update()
        
    @property
    def buildMode(self):
        """Read-only
        """
        return self._buildMode
    
    @property
    def editMode(self):
        """When True, the shape of the object (non-cursor types) can be edited.
        Default if False.
        Editing is done via control points (GUI editing).
        
        """
        if self.objectType & GraphicsObjectType.allCursorTypes:
            return False
        
        return self._shapeIsEditable
    
    @editMode.setter
    def editMode(self, value):
        if self.objectType & GraphicsObjectType.allCursorTypes:
            return

        self._shapeIsEditable = value
        
        if self._shapeIsEditable:
            self.__updateCachedPathFromBackend__()
            
        self.update()
        
        
    @property
    def canMove(self):
        """Can this object be moved by mouse or keyboard.
        By default, all graphics object types can be moved.
        For ROI types, setting this to False also sets editMode to False.
        """
        return self._movable
    
    @canMove.setter
    def canMove(self, value):
        self._movable = value
        
        if not self._movable:
            self.editMode = False
        
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, value)
        
    @property
    def canEdit(self):
        return self._editable
    
    @canEdit.setter
    def canEdit(self, value):
        self._editable = value
        
        if not self._editable:
            self.editMode=False
        
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, value)
        
    @property
    def canTransform(self):
        """Can the object be transformed (rotated/scaled/skewed).
        By default, objects cannot be transformes, except for being moved
        around the scene (see "canMove").
        However, non-cursor objects can be rotated/scaled/skewed
        when this property is set to "True"
        """
        if self.objectType & GraphicsObjectType.allCursorTypes:
            return False
        
        return self._transformable
    
    @canTransform.setter
    def canTransform(self, value):
        if self.objectType & GraphicsObjectType.allCursorTypes:
            return
        
        self._transformable = value
        
    @property
    def autoLabel(self):
        return self._autoLabel
    
    @autoLabel.setter
    def autoLabel(self, value):
        if not isinstance(value, bool):
            raise TypeError("Boolean expected; got %s instead" % type(value).__name__)
        
        self._autoLabel = value
        self.__setDisplayStr__()

    # NOTE: 2017-06-26 22:48:53 
    # immutable properties
    # ###
    @property
    def objectType(self):
        return self._objectType
    
    @property
    def isCursor(self):
        return self._objectType & GraphicsObjectType.allCursorTypes
    
    @property
    def isLineCursor(self):
        return self._objectType & GraphicsObjectType.lineCursorTypes
    
    @property
    def isShapedCursor(self):
        return self._objectType & GraphicsObjectType.shapedCursorTypes
    
    @property
    def isVerticalCursor(self):
        return self._objectType == GraphicsObjectType.vertical_cursor
    
    @property
    def isHorizontalCursor(self):
        return self._objectType == GraphicsObjectType.horizontal_cursor
    
    @property
    def isCrosshairCursor(self):
        return self._objectType == GraphicsObjectType.crosshair_cursor
    
    @property
    def isPointCursor(self):
        return self._objectType == GraphicsObjectType.point_cursor
    
    @property
    def isShapeObject(self):
        """All non-cursor types
        """
        return self._objectType & GraphicsObjectType.allObjectTypes
    
    @property
    def isROI(self):
        return self._objectType & GraphicsObjectType.geometricShapeTypes
    
    @property
    def isPolygonal(self):
        return self._objectType & GraphicsObjectType.polygonTypes
    
    @property
    def isLinear(self):
        return self._objectType & GraphicsObjectType.linearShapeTypes
    
    @property
    def isBasicShape(self):
        return self._objectType & GraphicsObjectType.basicShapeTypes
    
    @property
    def isCommonShape(self):
        return self._objectType & GraphicsObjectType.commonShapeTypes
    
    @property
    def isGeometricShape(self):
        """Alias to self.isROI
        """
        return self.isROI

    @property
    def isPoint(self):
        return self._objectType == GraphicsObjectType.point
    
    @property
    def isPolygon(self):
        return self._objectType == GraphicsObjectType.polygon
    
    @property
    def isRectangle(self):
        return self._objectType == GraphicsObjectType.rectangle
    
    @property
    def isLine(self):
        return self._objectType == GraphicsObjectType.line
    
    @property
    def isEllipse(self):
        return self._objectType == GraphicsObjectType.ellipse
    
    @property
    def isPath(self):
        return self._objectType == GraphicsObjectType.path
    
    @property
    def isText(self):
        return self._objectType == GraphicsObjectType.text
    
    #@property
    #"def" graphicsItem(self):
        #"""Same as self.shapedItem()
        #"""
        #return self._graphicsShapedItem
    
class ColorMapList(QtWidgets.QListWidget):
    """
    DEPRECATED
    Use ItemsListDialog
    """
    def __init__(self, parent=None, itemsList=None):
        QtWidgets.QListWidget.__init__(self, parent)
        self.selectedColorMap = None
        
        if self.validateItems(itemsList):
            self.addItems(itemsList)
      
        self.itemClicked.connect(self.selectItem)
        self.itemDoubleClicked.connect(self.selectAndGo)
    
        # wrong:
        #self.connect(self, SIGNAL("itemClicked('qt.QListWidgetItem')"), self.mySlot);
    
    itemSelected = QtCore.pyqtSignal(str)


    def setItems(self, itemsList):
        if self.validateItems(itemsList):
            #self.itemsList = itemsList
            self.clear()
            self.addItems(itemsList)
  
  
# don't use validate as this overrides a QWidget method and breaks the dialog code below
    def validateItems(self, itemsList):
        if itemsList is None or not all([isinstance(x,(str,unicode)) for x in itemsList]):
            QtWidgets.QMessageBox.critical(None, "Error", QtCore.QString("Argument must be a list of string or unicode items."))
            return False
        return True

      
    def selectItem(self, item):
        self.selectedColorMap = item.text()
        self.itemSelected.emit(item.text()) # this is a QString !!!
        #print(item.text())

    
    def selectAndGo(self, item):
        self.selectedColorMap = item.text()
        self.itemSelected.emit(item.text())
        self.close()

class ItemsListDialog(QDialog, Ui_ItemsListDialog):
    itemSelected = QtCore.pyqtSignal(str)

    def __init__(self, parent = None, itemsList=None, title=None, preSelected=None, modal=False, selectmode=QtWidgets.QAbstractItemView.SingleSelection):
        super(ItemsListDialog, self).__init__(parent)
        self.setupUi(self)
        self.setModal(modal)
        self._selectedItemText_ = None
        self._pre_selected_text_ = None
        
        self.listWidget.setSelectionMode(selectmode)
    
        if title is not None:
            self.setWindowTitle(title)
    
        self.listWidget.itemClicked.connect(self.selectItem)
        self.listWidget.itemDoubleClicked.connect(self.selectAndGo)

        if isinstance(itemsList, (tuple, list)) and \
            all([isinstance(i, str) for i in itemsList]):
            
            if isinstance(preSelected, str) and preSelected in itemsList:
                self._pre_selected_text_ = preSelected
                
            self.setItems(itemsList)
      
    def validateItems(self, itemsList):
        # 2016-08-10 11:51:07
        # NOTE: in python3 all str are unicode
        if itemsList is None or isinstance(itemsList, list) and (len(itemsList) == 0 or not all([isinstance(x,(str)) for x in itemsList])):
            QtWidgets.QMessageBox.critical(None, "Error", "Argument must be a list of string or unicode items.")
            return False
        return True

    @property
    def selectionMode(self):
        return listWidget.selectionMode()
    
    @selectionMode.setter
    def selectionMode(self, selectmode):
        if not isinstance(selectmode, (int, QtWidgets.QAbstractItemView.SelectionMode)):
            raise TypeError("Expecting an int or a QtWidgets.QAbstractItemView.SelectionMode; got %s instead" % type(selectmode).__name__)
        
        if isinstance(selectmode, int):
            if selectmode not in range(5):
                raise ValueError("Invalid selection mode:  %d" % selectmode)
            
        self.listWidget.setSelectionMode(selectmode)
                
    def setItems(self, itemsList, preSelected=None):
        """Populates the list dialog with a list of strings :-)
        
        itemsList: a python list of python strings :-)
        """
        if self.validateItems(itemsList):
            self.listWidget.clear()
            self.listWidget.addItems(itemsList)
            
            #print(itemsList)
            
            longestItemNdx = np.argmax([len(i) for i in itemsList])
            longestItem = itemsList[longestItemNdx]
            
            if isinstance(preSelected, str) and preSelected in itemsList:
                self._pre_selected_text_ = preSelected
            
            if self._pre_selected_text_ in itemsList:
                # 'cause it may have been set up in c'tor
                ndx = itemsList.index(self._pre_selected_text_)
                
                self.listWidget.setCurrentRow(ndx)
            
            fm = QtGui.QFontMetrics(self.listWidget.font())
            w = fm.width(longestItem) * 1.1
            
            if self.listWidget.verticalScrollBar():
                w += self.listWidget.verticalScrollBar().sizeHint().width()
                
            #self.listWidget.setMinimumWidth(self.listWidget.sizeHintForColumn(0))
            self.listWidget.setMinimumWidth(w)
            #self.updateGeometry()

    
    def selectItem(self, item):
        self._selectedItemText_ = item.text()
        self.itemSelected.emit(str(item.text())) # this is a QString !!!
        
    @property
    def selectedItems(self):
        items = self.listWidget.selectedItems()
        
        if len(items):
            return [i.text() for i in items]
            
        else:
            return []
        
    @property
    def selectedItem(self):
        return self._selectedItemText_
    
    def selectAndGo(self, item):
        self._selectedItemText_ = item.text()
        self.itemSelected.emit(item.text())
        self.accept()
        
def simplifyPath(path, frame = None, max_adjacent_points = 5):
    """Simplifies a Path that consists of a long sequence of Move & Line points.
    
    The Path is simplified by removing sequence of points that differ in one coordinate
    only (and thus can be replaced by a single horizontal or vertical line).
    
    If necessary, sequences of adjacent points with different copordinates and 
    longer than max_adjacent_points are approximated by B-spline interpolation.
    
    See signalprocessing.simplify_2d_shape()
    
    Parameters:
    ===========
    path: Path without nested paths; must be composed only of Move and Line elements.
    
    frame: None (default) or an int: the index of the frame for which the (xy) 
        coordinates of the Path are to  be used.
        
        When None, the path's current frame will be used
        
    max_adjacent_points: int (default, 5) or None -- see signalprocessing.simplify_2d_shape()
    
    Returns:
    ========
    
    A new Path with adjacent points having at least one identical coordinate are
        removed.
        
    If max_adjacent_points is not None, sequences of adjacent points with different
        coordinates in the new path, that are longer than max_adjacent_points
        are replaced by B-spline approximations.
        
        
    
    """
    from core import signalprocessing as sgp
    
    if not isinstance(path, Path):
        raise TypeError("Expecting a pictgui.Path; got %s instead" % type(path).__name__)
    
    if not all([isinstance(o, (Move, Line)) for o in path]):
        raise TypeError("Expecting a Path composed exclusively of Move or Line objects")
    
    frameindices_array = np.array(path.frameIndices)
    
    if frame in frameindices_array.flatten():
        xy = np.array([(o.x, o.y) for o in path if o.z_frame in (frame, None, [])]) # to include those elements that have framelesss states
        
    elif frame is None:
        frame = path.currentFrame
        xy = np.array([(o.x, o.y) for o in path if o.z_frame == frame])
        
    else:
        raise ValueError("frame %s does not appear to be linked with thei object's states" % frame)
        

    xy_unique, xy_splines = sgp.simplify_2d_shape(xy, k=3)
    
    ret = Path()
        
    if len(xy_splines):
        
        #print("simplifyPath xy_splines[0]", xy_splines[0])
        
        # locate the xy spline segments, to create Cubic objects
        
        # 3D array: axis 0 = spline points: 2D array with xy row-wise:
        #                   size = n = number of splines found
        #           axis 1 = row vector of 4 cubic spline points
        #                   size = 4 : first, cp1, cp2, last point (i.e., cubicTo)
        #           axis 2 = the x & y coordinates of each of the spline points
        #                   size = 2
        spline_points_xy = np.array([np.array(i[0][1]).T for i in xy_splines])
        #print(spline_points_xy)
        
        # the first cubic spline point needs to exist in the new Path object
        # either as a Move or Line, 
        # then we append a Cubic constructed on the last point, cp 1 and cp2
        # as listed above
        
        # for each spline, get the indices of the points between (and including)
        # first and last spline point
        
        #print("simplifyPath spline_points_xy.shape", spline_points_xy.shape)
        
        first_last_spline_points = spline_points_xy[:, [0, -1], :]  # shape is (n,2,2)
                                                                    # n = number of splines
        
        # a list the len() of which equals n splines as above
        # its elements are tuples: spline index "k" and the arrays with indices 
        # into the xy array that belong to the "k"th spline segment
        spline_points_ndx_in_xy = [(k, 
                                    np.where( (xy_unique[:,0] >= np.min(first_last_spline_points[k,:,0])) \
                                           & (xy_unique[:,0] <= np.max(first_last_spline_points[k,:,0])) \
                                           & (xy_unique[:,1] >= np.min(first_last_spline_points[k,:,1])) \
                                           & (xy_unique[:,1] <= np.max(first_last_spline_points[k,:,1])) )[0]) \
                                    for k in range(first_last_spline_points.shape[0])]
        
        # in the above, some or all elements might be empty -- select the first 
        # and last point from non-empty ones
        spline_start_end = [(i[0], i[1][0], i[1][-1]) for i in spline_points_ndx_in_xy if len(i[1]) > 0]
        
        
        # go and build a new (hybrid) Path
        
        visited_splines = set()
        
        for k in range(xy_unique.shape[0]):
            if k == 0: # path always begins with a Move
                ret.append(Move(xy_unique[k,0], 
                                 xy_unique[k,1]))
                
            else:
                # is this k in a spline segment?
                spline_with_k = [i[0] for i in spline_start_end if k > i[1] and k <= i[2]] # unique index of spline which contains point k
                
                if len(spline_with_k):  # one spline segment found which contains this k
                                        # this is unique because a point's index can exist
                                        # in at most ONE spline segment (by definition)
                    spline_index = spline_with_k[0] # which is the spline that has k?
                    
                    # as soon as the first spline point was found,
                    # construct spline then remember the index of the visited 
                    # spline so that we do not end up constructing more splines
                    # for that segment
                    if spline_index not in visited_splines:
                        # c'truct Cubic on last point, cp1, cp2
                        ret.append(Cubic(spline_points_xy[spline_index][3][0],
                                        spline_points_xy[spline_index][3][1],
                                        spline_points_xy[spline_index][1][0],
                                        spline_points_xy[spline_index][1][1],
                                        spline_points_xy[spline_index][2][0],
                                        spline_points_xy[spline_index][2][1]))
                        
                        
                    else: # been in this spline before, so skip
                        continue
                    
                    visited_splines.add(spline_index)
                    
                else: # not in a spline segement --> append a Line
                    ret.append(Line(xy_unique[k,0],
                                     xy_unique[k,1]))
                    
    else:
        for k in range(xy_unique.shape[0]):
            if k == 0:
                element = Move(xy_unique[k,0], xy_unique[k,1])
                
            else:
                element = Line(xy_unique[k,0], xy_unique[k,1])

            ret.append(element)
                
            
    return ret
        
