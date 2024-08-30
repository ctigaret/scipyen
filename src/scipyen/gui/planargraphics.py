# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
2021-04-26 21:24:43
PlanarGraphics, GraphicsObject and ancillary code

NOTE: 2021-05-02 08:58:01
Overhaul of the API:
====================

Shapes and 2D primitives are represented by subclasses of PlanarGraphics.

PlanarGraphics (with the exception of Path) are constructed from numeric 
parameters, or collections of QtCore's QPoint(F), QRect(F), QLine(F).

Path is a special subtype of PlanarGraphics constructed from a sequence of 
PlanarGraphics EXCLUDING Cursor.

PlanarGraphics are visualized (i.e. rendered in a QGraphicsWidget) by means of a
GraphicsObject (derived from QGraphicsObject). The GraphicsObject is the 
'frontend' for the PlanarGraphics. The widget that renders the PlanarGraphics is
the 'renderer'.

A PlanarGraphics object may have several frontends (e.g. a Cursor, or a ROI
rendered simultaneously in several ImageViewer windows). Frontends are generated
by code inside the GUI object (either the QGraphicsWidget-derived object used to
display the frontends, or in the object that contains the QGraphicsWidget).

GraphicsObjects are constructed by the renderer using the PlanarGraphics object
they are supposed to render; this PlanarGraphics is the 'backend' of the 
GraphicsObject.

A GraphicsObject has EXACTLY one backend.

Issues to resolve:

1. How to make the backend aware of user-initiated changes in the numeric
descriptors (i.e., via GUI interactions in the renderer) and to propagate them
to the other frontends, WITHOUT CAUSING INFINITE RECURSION. 

In such cases the user interacts with the frontend (i.e. via the mouse or 
keyboard), and therefore, the backend can be updated from within the appropriate
event callback by the GraphicsObject.

It follows that, unless someone writes code to link GUI actions directly to 
changes in the values of the planar descriptors of a PlanarGraphics backend, 
such changes only occur programmatically.

When a backend planar descriptor value changes the backend must 'signal' the 
frontends to update (repaint) themselves. To avoid unnecessary paints, it is 
desirable not to send this 'signal' back to the same frontend that triggered the
changes from the GUI (if any). For this purpose, the backend needs to 'know' 
which frontend has caused the change in planar descriptors, or somehow the
'signal' received by the causing frontend must be ignored while executing the 
event callback (see above).

2. In 3D data, the PlanarGraphics may be associated with (i.e. rendered in) just
a subset of data 'frames' (or 'slices'), or may have different descriptor values
in some frames. 

The frontend must take account of this and paint itself as appropriate. This must
be done by the frontend reading the collection of 'states' in the backend, that
are 'renderable' in the 'current frame' (i.e. the data frame currently
displayed in the renderer).

This is also relevant for Issue # 1 above, when the changes in planar descriptor
values are actually brought only to the states renderable in the current frame.




"""

# NOTE: 2024-08-27 16:48:24 
# A brief incursion into shapely API — a bullet-list of library features,
# useful (✔), potentially useful (✓) and not useful (❌):
#
# (✔) fast
# (❌) geometries are immutable
# (✓) support of 2.5 D — somwehat awkward, requires copying the data for each specified frame
# (❌) no support for curves (cubic/quad), ellipse, or cursors as defined here
# (✔) support for geometry operations and lear referencinh methods (distance, interpolation etc) -> 
#   this is the most useful, but not enough to replace PlanarGraphics; however, 
#   I could use shapely objects as temporary intermediate objects to perform more
#   advanced functions.
# (✓) support for more types (LineString, LinearRing, Collections) -> potential
#   correspondence with Path objects defined here
#
# This library is clearly optimized for fast geometrical computations on linear
# graphical primitives and collections of such, but less so for interactive plotting
# and/or editing.

# NOTE: 2024-08-25 19:58:34
# the comment below is obsolete
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
# In a QPainterPath, the lineTo and curveTo elements only specify the
# end point of the path element, because the point where it begins is given by 
# the previous element of the path.
#
# A moveTo element at the beginning of the path sets the begin point of the path
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


#### BEGIN core python modules
# NOTE: use Python re instead of QRegExp
import sys, os, re, numbers, itertools, warnings, traceback
import typing
import math
from collections import (ChainMap, namedtuple, defaultdict, OrderedDict,)
from functools import (partial, partialmethod,)
from enum import (Enum, IntEnum,)
from abc import (ABC, abstractmethod,)# ABCMeta)
from copy import copy
#### END core python modules

#### BEGIN 3rd party modules
#from core.vigra_patches import vigra.pyqt.quickdialog as quickdialog
import numpy as np
import scipy
from traitlets import Bunch
from qtpy import QtCore, QtGui, QtWidgets, QtXml
from qtpy.QtCore import Signal, Slot, Property
#### END 3rd party modules

#### BEGIN core modules
from core.datatypes import (TypeEnum, )
from core.utilities import (reverse_mapping_lookup, reverse_dict, )
from core.traitcontainers import DataBag
from core.prog import (safeWrapper, deprecated,
                       timefunc, processtimefunc,filter_type)
#from core.utilities import (unique, index_of,)
from core.workspacefunctions import debug_scipyen
#### END core modules

#### BEGIN other gui stuff
from .painting_shared import (standardQtGradientTypes, standardQtGradientPresets,
                              g2l, g2c, g2r, gradientCoordinates, 
                              qPathElementCoordinates)

import gui.scipyen_colormaps as colormaps

from .scipyen_colormaps import ColorPalette
# WARNING do NOT import individual classes directly from shapely as they may be 
# overwritten in this module (e.g. Point)
# on the other hand, the individual shapely classes need imported individually in
# order for them to be registered (and theyr C/C++ library to be initialized)
# hence we use the shapes module as a wrapper to expose those classes w/o clashes 
# below
from gui import shapes 
#### END other gui stuff

__module_path__ = os.path.abspath(os.path.dirname(__file__))

# 
class PlanarGraphics(): pass
class Path(PlanarGraphics): pass


# NOTE: 2020-11-04 08:56:57
# for compatibility with more recent pickles
PlanarGraphicsState = GraphicsState = Bunch 

# NOTE: 2017-11-24 21:33:20
# bring this up at module level - useful for other classes as well
def __new_planar_graphic__(cls, states, name="", frameindex=[], currentframe=0, 
                        graphicstype=None, closed=False, linked_objects = dict(), 
                        position = (0,0)):
    """
    Will dispatch to sub-class c'tor.
    
    Positional parameters:
    =======================
    cls: the sub-class
    
    states: dictionary mapping frame index (int) keys to datatypes.Bunch state objects, 
            or a datatypes.Bunch state object, or a sequence (tuple, list) of 
            PlanarGraphics objects (for unpickling Path objects)
    
    name: the name (_ID_), a str
    
    """
    #print("__new_planar_graphic__: cls", cls)
    
    # NOTE: 2021-05-04 10:51:51 FIXME/TODO
    # do away with pictgui.Cursor - use specialized cursor subclasses
    # also do away with PlanarGraphicsType
    if cls.__name__ == "Cursor":
        cls = Cursor # avoid pictio.CustomUnipckler choosing matplotlib cursor class
    
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

class PlanarGraphicsType(TypeEnum):
    """Enumeration of all supported graphical object types.
    Type name             type value  QGraphicsItem               Planar Descriptors
    ===============================================================================
    vertical_cursor     = 1                                     x, y, width, height, xWin, yWin, radius
    horizontal_cursor   = 2                                     x, y, width, height, xWin, yWin, radius
    crosshair_cursor    = 4                                     x, y, width, height, xWin, yWin, radius
    point_cursor        = 8                                     x, y, width, height, xWin, yWin, radius
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
    
    lineTypes           = line                  | polyline
    linearTypes         = point                 | lineTypes
    polygonTypes        = rectangle             | polygon 
    linearShapeTypes    = polygonTypes          | linearTypes
    arcTypes            = arc                   | arcmove
    closedArcTypes      = ellipse               | arcTypes
    curveTypes          = quad                  | cubic
    basicShapeTypes     = linearShapeTypes      | closedArcTypes | curveTypes
    commonShapeTypes    = basicShapeTypes                                       # alias
    geometricShapeTypes = commonShapeTypes      | path
    allShapeTypes       = geometricShapeTypes   | text                          # all non-cursor types
    
    allObjectTypes      = allCursorTypes        | allShapeTypes
    allGraphicsTypes    = allObjectTypes
 
    move                = point                                                 # alias
  
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
    path                = 16384 # Path
    qtpath              = 32768 # QPainterPath
    text                = 65536 # QGraphicsSimpleTextItem               <=> str
    
    lineCursorTypes     = vertical_cursor       | horizontal_cursor
    shapedCursorTypes   = lineCursorTypes       | crosshair_cursor
    allCursorTypes      = shapedCursorTypes     | point_cursor
    
    lineTypes           = line                  | polyline
    linearTypes         = point                 | lineTypes
    polygonTypes        = rectangle             | polygon 
    linearShapeTypes    = polygonTypes          | linearTypes
    arcTypes            = arc                   | arcmove
    closedArcTypes      = ellipse               | arcTypes
    curveTypes          = quad                  | cubic
    basicShapeTypes     = linearShapeTypes      | closedArcTypes | curveTypes
    commonShapeTypes    = basicShapeTypes                                       # alias
    geometricShapeTypes = commonShapeTypes      | path
    allShapeTypes       = geometricShapeTypes   | text                          # all non-cursor types
    
    allObjectTypes      = allCursorTypes        | allShapeTypes
    allGraphicsTypes    = allObjectTypes
 
    move                = point                                                 # alias
  
GraphicsObjectType = PlanarGraphicsType

class PlanarGraphics():
    """Ancestor for all planar graphic object types in Scipyen imaging.
    
    PlanarGraphics objects encapsulate two-dimensional geometric shapes to be 
    used as landmarks (ROIs, and Cursors) on 2D images or frames (in this context
    a "frame" is a 2D "slice" of the data array along one of its axes; the axis 
    along which the data is slices into frames can be any of the three axes of a
    3D data; in contrast an "image" is a 2D data array with one frame). 
    
    The PlanarGraphics can represent a primitive shape (see below), a Cursor 
    (vertical, horizontal, crosshair, point), or a Path composed of primitive 
    shapes and/or subpaths.
    
    The primitive shapes defined in this module are: Move or Point, Line, Arc, 
    ArcMove, Cubic, Quad, Ellipse, Rectangle, emulating the QGraphicsObject 
    primitives.
    
    Planar graphics descriptors
    ===========================
    
    The graphics primitives and Cursor objects are described / defined by a set 
    of numeric parameters (or 'planar descriptors', e.g. position coordinates, 
    width and height of the bounding rectangle, angle, etc.). 
    
    The planar descriptors thus define a 2D graphics primitive specific to the 
    PlanarGraphics type and are listed in the "_planar_descriptors_" attribute.
    
    For example:
        ("x", "y", "w", "h") define a Rectangle or an Ellipse, 
        ("x", "y") define a Line, or a Move (see NOTE 2, below), 
        ("x", "y", "cx", "cy") for a quadratic curve, etc.

    See the documentation for the concrete shape and cursor types for details.
    
    The values for linear descriptors (position coordinates, and distances) are 
    interpreted as data samples (i.e., pixels) relative to the top left sample of
    the data frame : the pixel with (0,0) coordinates, or the "origin".
    
    Angular descriptor values are interpreted as radians, with 0 lying on the 
    horizontal axis and positive values going counter-clockwise.
    
    All 2D geometric primitives defined in this module inherit from PlanarGraphics.
    
    A PlanarGraphics object also has a "type" instance attribute (see 
    PlanarGraphicsType enum in this module); some PlanarGraphics classes support
    more than one PlanarGraphicsType value (e.g. Cursor).
    
    See NOTE 1 "Sub-classing PlanarGraphics", below, for details.
    
    PlanarGraphics are displayed by painting a corresponding GraphicsObject 
    ("frontend") over a data frame. The GraphicsObject "frontends" inherit from 
    the Qt QGraphicsObject (defined in the QGraphics framework of the Qt toolkit). 
    
    A PlanarGraphics object is callable. Calling an object as a function generates
    a QGraphics primitive for painting (i.e., displaying) the shape overlaid on
    an image, in the GUI. 
    
    To make this correspondence more "natural", the planar descriptors emulate 
    the parameters needed to construct a QGraphicsItem primitive (painter path element)
    (see the examples given above)
    
    PlanarGraphics objects can be serialized, hence saved (pickled) alongside 
    other python data. 
    
    By contrast, the GraphicsObject "frontends" used for display are temporary:
    they cannot be serialized (or pickled) and thus, are NOT meant to be saved.
    Instead, they are created and managed by GUI code for the purpose of
    displaying PlanarGraphics objects.
    
    The PlanarGraphics "state"
    ==========================
    
    In order for the shapes and cursors to be used with 3D data volumes, the 
    concrete values of their planar descriptors are allowed to vary from frame 
    to frame by collecting them in so-called planar graphics "states".
    
    The 'state' is an mapping with attributes named after the planar descriptors 
    specific for the actual shape (or cursor). They can be accessed and their 
    values modified using either attribute access ('dot' syntax), or "indexed" 
    access:
    
    For example,
    
                state.x = 10        # attribute access
    
    or
                state["x"] = 10     # indexed access
                
    In addition, a state object contains a 'z_frame' and an 'angle' attribute.
    
    The 'angle' attribute is related to the angle of rotation of the PlanarGraphics
    relative to the 2D Cartesian system of axes (x — horizontal, y — vertical).
    It is given as a float scalar, multiplier of math.pi, and can take any
    value between -2.0 and 2.0 (inclusive) with positive values representing a
    counter-clockwise rotation.
    
    The 'z_frame' attribute indicates the index of the notional frame of data¹, 
    if any, where that specific 'state' is visible. By default, this is None.
    'z_frame' emulates a "2.5D" geometry² as explained below:
    
    • when z_frame is None, the state is visible in all frames avaliable in the
      data
    
    • when z_frame is an int (or a float, which will be truncated to an int): 
        ∘ if z_frame >= 0 the state is visible ONLY in the frame with 
            index == z_frame, if that frame exists; for example, if z_frame == 3 
            and data has only three frames then the state will not be visible at
            all!
            
            Therefore, unless the data contains at least z_frame + 1 frames, the
            state will not be visible.
            
        ∘ if z_frame  < 0 the state applies to all frames EXCEPT the frame with
            index ==  -1 * z_frame - 1
    
    It follows that a PlanarGraphics 'state' object can be:
    
    (a) ubiquitous: 
        -----------
        • z_frame is None, and the state is visible in any data frame
        
    (b) frame-avoiding: 
        ---------------
        • z_frame < 0: the state is visible in all frames EXCEPT the one which
            has index equal to -1 × z_frame - 1 (if it exists)
        
    (c) single-frame: 
        -------------
        • z_frame >= 0: the state is visible ONLY in the frame which has
            index == z_frame (if it exists)
        
    The co-existence of states in a PlanarGraphics object is governed by the
    rules:
    
    Rule I: One frame - one state
    -----------------------------
    Any frame can associate AT MOST one state.
     
    Rule II. Ubiquitous states
    --------------------------
    An ubiquitous state is the ONLY state of a PlanarGraphics object.
    
    Corollaries:
    
    II.1) the PlanarGraphics object can have only one ubiquitous state, and
    
    II.2) the PlanarGraphics object can have only one state when that state is
        ubiquitous
        
    Rule III. Frame-avoiding states
    -------------------------------
    A frame-avoiding state ('fa_state') can co-exist with AT MOST one
    single-frame state ('sf_state') such that the two states satisfy:
    
        fa_state.z_frame == -1 * sf_state.z_frame - 1
        
    i.e., the frame where the fa_state is invisible is the same frame as
    the one where the singl-frame state is visible.
        
    This situation allows the PlanarGraphics object to have one state visible
    everywhere EXCEPT the frame which associates a specific 'state' object,
    possibly with distinct descriptor values.
        
    Corollaries:
    
    III.1) there can be only one frame-avoiding state in a PlanarGraphics object;
    
    III.2) a PlanarGraphics with a frame-avoding state can have at most two
        states, with the other state being a single-frame state;
        
    III.3) the single-frame state is drawn in the frame "avoided" by the 
        frame-avoding state;
            
    Rule IV. Single-frame states
    ----------------------------
    There can be any number of single-frame states.
    
    Corollaries:
    
    IV.1) A PlanarGraphics object with more than two states can have ONLY
        single-frame states.
        
    IV.2) By Rule I, all single_frame states have unique z_frame values
    
    NOTES: 
    ¹The natural domain of the PlanarGraphics is a 2D data set in a Cartesian
    coordinate system. For data that can be considered as being composed of 
    several 2D 'frames', each frame may associate the same planargraphics, or
    a slightly modified version of it.
    ²By associating a "state" with data frames, a PlanarGraphics object can take
    different values of its planar descriptors in distinct data frames (this is
    somewhat similar to the "ROIs" in Image/J). 
    See also https://en.wikipedia.org/wiki/2.5D
    
    Paths
    =====
    
        PlanarGraphics objects of different types can be "chained" together in a 
        list-like Path object, which supports iterable API.
    
    Frontends
    =========
    
        A PlanarGraphics object can have more than one frontend, when the same
        shape is intended to be painted synchronously in several GUI viewers.
        
        Each frontend is associated with one viewer, and all the frontends have
        a reference to the same PlanarGraphics object (the "backend").
        
        The viewers MUST display data arrays with the same shape, otherwise the 
        the behaviour is undefined.
        
    Linked objects
    ==============
    
        Linked PlanarGraphics are objects such that such that any changes in one
        object shape also bring about the same change in the linked objects shapes.
        
        The link can be direct, between PlanarGraphics objects with the same
        set of descriptors, or indirect - mediated by a transform function
        (e.g, a vertical cursor in a XT line-scan image linked to a ROI in an XY
        scene image).
        
        Furthermore, the link can be uni- or bi-directional.
    
    
    * * *
    
    NOTE 1: Sub-classing PlanarGraphics.
    
    Sub-classes need to define three :class: attributes:
    
    _planar_descriptors_: a tuple of str with the name of planar descriptors, 
        in the exact order they are expected for the parametric constructor.
        
        e.g., for a Rect:
        
        _planar_descriptors_ = ("x", "y", "w", "h")
        
    _planar_graphics_type_: a PlanarGraphicsType enum value
    
        e.g., for a Rect:
        
        _planar_graphics_type_ = PlanarGraphicsType.rectangle
        
    qt_path_composition_call: a str with the QPainterPath method name (callable) to be used when
        generating a QPainterPath from this object.
        
        e.g. for a Rect:
        
        qt_path_composition_call = "addRect"
        
    The only exception to these rules is for Path which does not have a predefined
    shape and hence:
    
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
    
    NOTE 2: a Line encapsulates a LineTo painter path element, therefore it is 
    defined by the (x,y) coordinates of its DESTINATION point. This is because 
    Line is an element for both Path and Polygon construction.
    
    A stand-alone line can be obtained by constructing a Path with a Move and a
    Line element.
    
    """
    
    # TODO 2018-01-12 16:37:21
    # methods for retrieval of individual points or QPainterPath Elements as a sequence
    
    # ### BEGIN :class: attributes
    # NOTE: 2018-01-11 12:14:45
    # attribute with names of parameters for the parametric constructor
    # of the planar graphic object
    
    # ATTENTION: these must be present in the exact order in which they are passed
    # to the parametric form of the constructor
    _planar_descriptors_ = () 
    
    _planar_graphics_type_ = None
    
    qt_path_composition_call = ""
    
    _default_label_ = ""
   
    # NOTE: properties (descriptor names) do not belong here
    _required_attributes_ = ("_states_", "_currentframe_", "_currentstates_",
                             "_ID_", "_linked_objects_",)
    
    #defaultLineColor = "white"
    #defaultLabelTextColor = "black"
    #defaultLabelBackgroundColor = "white"
    #defaultHoverColor = "red"
    #defaultControlBrushStyle = "SolidPattern"
    
    # ### END :class: attributes
    
    # ### BEGIN :class: methods
    
    @classmethod
    def validateDescriptors(cls, *args):
        return len(args) == len(cls._planar_descriptors_) and all([isinstance(v, numbers.Number, str) for v in args])
    
    @classmethod
    def validateState(cls, value):
        #print("PlanarGraphics (%s) validateState(%s: %s)" % (cls.__name__, value.__class__.__name__, value))
        #print("PlanarGraphics (%s) _planar_descriptors_: %s" % (cls.__name__, cls._planar_descriptors_))
        
        if not isinstance(value, Bunch):
            raise TypeError(f"Expecting a Bunch; got {type(value).__name__} instead")
        
        # if isinstance(value, DataBag):
        #     value = Bunch(dict(value).copy())
            
        all_keys = all([a in value.keys() for a in cls._planar_descriptors_])
        
        if all_keys:
            valid_descriptors = all([isinstance(value[d], (numbers.Number, str)) for d in cls._planar_descriptors_])

            # NOTE: 2021-04-30 16:45:56
            # z_frame IS NOT a planar descriptor but is required in the state data bag
            valid_z_frame = hasattr(value, "z_frame") and isinstance(value.z_frame, (int, type(None)))
            
            # NOTE: 2024-08-27 23:32:20
            # introducing 'angle'; by default this is 0
            valid_angle = hasattr(value, "angle") and isinstance(value.angle, float) and value.angle >= -2.0 and value.angle <= 2.0
            
            return valid_descriptors and valid_z_frame and valid_angle
        
        return all_keys
        
    @classmethod
    def validateStates(cls, value):
        """Checks that the states in "value" are conformant.
        Applied validateState or each element in value.
        
        Parameters:
        ===========
        
        A sequence of Bunch objects, or a mapping of int keys to Bunch objects.
        
        """
        if isinstance(value, (tuple, list)):
            return all([self.__class__.validateState(v) for v in value])
            
        elif isinstance(value, dict):
            return all([isinstance(k, int) and self.__class__.validateState(v) for (k, v) in value.items()])
        
        else:
            return False
        
    @classmethod
    def defaultState(cls):
        """Returns a state conaining planar descriptors specific to this
        subclass.
        
        The descriptors have the default value of 0, except for the z_frame 
        which is set to None
        
        """
        # NOTE: 2020-11-01 14:01:12
        # z_frame has special treatment; by default this is set to None so that
        # the object is visible in any frame
        state = Bunch(dict(zip(cls._planar_descriptors_, [0]*len(cls._planar_descriptors_))))
        state.z_frame = None
        state.angle = 0. # × math.pi
        return state
    
    @classmethod
    def copyConvertState(cls, src):
        """Use this to create a copy of a state generated from old API.
        """
        #If src does not have an attribute "z_frame" then it is given one, with
        #value None
        if not isinstance(src, dict):
            raise TypeError("Expecting a dict, got %s instead" % type(src).__name__)
        
        #print("\t%s.copyConvertState %s planar descriptors: %s" % (cls.__name__, cls.__name__, cls._planar_descriptors_))
        # accept objects created with older API
        # NOTE: 2020-11-01 14:23:16
        # z_frame has special treatment and it was absent in old APIs
        #descriptors = [d for d in cls._planar_descriptors_ if d != "z_frame"]
        
        ret = Bunch(dict((str(k), v) for k, v in src.items() if k in cls._planar_descriptors_))
        
        # now make sure it has a z_frame attribute
        if not hasattr(ret, "z_frame") or not isinstance(ret.z_frame, (int, type(None))):
            ret.z_frame = None
            
        if not hasattr(ret, "angle") or not isinstance(ret.angle, float) or ret.angle < -2.0 or ret.angle > 2.0:
            ret.angle = 0.0
            
        # NOTE: 2020-11-01 14:25:30
        # finally check that all mandatory descriptors are present in src
        # z_frame was introduced later in development and it can be set to None
        # here
        # NOTE: 2020-11-02 07:49:33
        # old API bugs resulted in some of these NOT being saved, so instead of 
        # raising an exception, we attribute default values to the missing ones
        # and hope for the best (!?!)
        for key in cls._planar_descriptors_:
            if key not in ret:
                # FIXME 2020-11-03 19:17:37 HOW?
                # some confusions/bugs in old pickled DataBags results in the constructors
                # above leaving attributes behind - i.e. NOT found in the final result - why?
                # for the life of me I cannot understand why...
                # so this should fix it
                if key in src:
                    ret[key] = src[key] 
                    
        # now remove any extra predictors that have nothing to do with this type
        # NOTE: now we DO need to take z_frame into account
        extra_keys = [k for k in ret if k not in list(cls._planar_descriptors_) + ["z_frame", "angle"]]
        
        for key in extra_keys:
            ret.__delitem__(key)
            
        if hasattr(src, "z_frame"):
            ret.z_frame = src.z_frame
        else:
            ret.z_frame = None
            
        if hasattr(src, "angle"):
            ret.angle = src.angle
        else:
            src.angle = 0.0
            
        return ret
    
    @classmethod
    def copyConvertStates(cls, *args):
        """Use this to convert states from old API
        """
        #print("\tPlanarGraphics (%s).copyConvertStates" % cls.__name__, args)
        return [s for s in map(cls.copyConvertState, args)]
    
    # ### END :class: methods
    
    # ### BEGIN static methods
    @staticmethod
    def findStateWithZFrame(states, frame):
        cs = [s for s in states if s.z_frame == frame]
        if len(cs):
            return cs[0]
        
    # ### END static methods
    
    def __init_from_descriptors__(self, *args, frameindex:typing.Optional[typing.Iterable]=[], currentframe:int=0) -> None:
        """This can (and should) be overloaded in subclasses
        """
        
        if len(args) != len(self.__class__._planar_descriptors_):
            raise ValueError("Expecting %d descriptors; got %d instead" % (len(self.__class__._planar_descriptors_), len(args)))
        
        self._states_ = [Bunch(dict(zip(self.__class__._planar_descriptors_, args)))]

        self._states_[0].z_frame = None
        self._states_[0].angle = 0.0
        
        self._applyFrameIndex_(frameindex)
        
        self._currentframe_ = currentframe
        
        self.checkStates()
        
    def __init_from_state__(self, state:dict, frameindex:typing.Optional[typing.Iterable]=[], currentframe:int=0):
        # this also checks for descriptor consistency including z_frame
        self._states_ = [self.__class__.copyConvertState(state)]
        
        if len(frameindex):
            self._applyFrameIndex_(frameindex)
            
        self._currentframe_ = currentframe
        
        self.checkStates()
        
    def __init_from_states__(self, *states, frameindex:typing.Optional[typing.Iterable]=[], currentframe:int=0):
        if all([isinstance(s, dict) for s in states]):
            # CAUTION these states may bring their own z_frame values
             # this also checks for descriptor consistency including z_frame
            self._states_ = self.__class__.copyConvertStates(*states)
            
            if len(self._states_) == 0:
                self._states_ = [self.__class__.defaultState()]
            
            if len(frameindex):
                self._applyFrameIndex_(frameindex)
                
            self._currentframe_ = currentframe
            
            self.checkStates()
            
        else:
            raise TypeError("Expecting a sequence of state dict-like objects; got %s instead" % states)
        
    def __init__(self, *args, graphicstype=None, closed:bool=False,
                 name:typing.Optional[str]=None, 
                 frameindex:typing.Optional[typing.Iterable]=[], 
                 currentframe:int=0, linked_objects:dict=dict()):
        """Constructor.
        
        Var-positional parameters:
        =========================
        *args: either:
            1) sequence of planar descriptors specific to the PlanarGraphics 
                subclass type, but WITHOUT the z_frame (which is specified via 
                the 'frameindex' parameter)
                
                The expected order is as specified in the _planar_descriptors_
                attribute.
                
            2) a sequence of PlanarGraphics objects (only for Path objects) 
            
            3) a PlanarGraphics object (copy constructor); 
            
        Named parameters: 
        =================
        
        These are common to all PlanarGraphics subclasses.
        
        name: str (default None) = the ID of the new object; 
                When an empty string or not a string, the ID is assigned the 
                first letter of the PlanarGraphics  subclass (in lower case).
                
                To avoid ambiguities, subclasses should override this rule (as
                the Cursor subclasses do); 
                however, it is highly recommended to pass a non-empty string here.
                
                The default naming rule is as follows:
                NOTE: 2021-05-10 11:28:52 implemented in the :class: attribute
                "_default_label_"
                
                PlanarGraphics: ""
                
                * for cursors:
                    CrosshairCursor:    "cc"
                    HorizontalCursor:   "hc"
                    PointCursor:        "pc"
                    VerticalCursor:     "vc"
                    Cursor:             "cr"
                    
                * for non-cursors:
                    Arc:                "a"
                    ArcMove:            "av"
                    Cubic:              "c"
                    Ellipse:            "e"
                    Line:               "l"
                    Move/Start/Point:   "m"
                    Path:               "p"
                        NOTE: for polylines and polygons this is overridden in
                        __init__, to "pl" and "pg"
                    Quad:               "q"
                    Rect:               "r"
                    Text:               "t"
                    
                
        frameindex: iterable (tuple, list, or range); default is empty: 
            indices of data frames associated with the PlanarGraphics' states.
            
            Only used when *args contains planar descriptors.
            
            ATTENTION:
            When *args specify several states, then frameindex can be either
            empty, or len(frameindex) MUST equal the number of states.
            
            When *args specify several states:
                * if frameindex is empty, the states will get z_frame values in the
                increasing order starting with 0 (all visible).
            
                * if frameindex is NOT empty, the states will get z_frame values 
                in the order given in frameindex:
                    - states with z_frame >= 0 are  visible in the frames with
                        index == z_frame
                        
                    - states with z_frame < 0 are invisible in the frame with 
                        index == -1 * z_frame -1.
                        
                    Therefore one must make sure that negative values in frameindex
                    do not resolve to positive index values that are already present
                    in frameindex.
            
            When *args specify a single state and frameindex is not empty, then
            the object will be augmented to contain as many states as len(frameindex)
            with the z_frame values set to the values of the indices contained
            in frameindex.
            
        currentFrame: int, default is None; only used when frameindex is not empty, 
            
            If given and not in the frameindex, the object will be "invisible"
        
        graphicstype: either:
            * a member of the PlanarGraphicsType enum, or
            * a str - the name of valid PlanarGraphicsType enum member, or
            * an int - the value of a PlanarGraphicsType enum value, or
            * None (default)
                      
            When None, the graphics type is determined by the PlanarGraphics
            subclass constructor. For Cursor, passing graphicstype None 
            generates a crosshair_cursor.
                    
        closed: boolean, default False: only used for Path objects
        
        """
        # NOTE: 2021-05-08 10:07:01 - automatic ID assignment rule
        # CAUTION: should be overruled in subclasses; better to assign a valid
        # non-empty string here
        if not isinstance(name, str) or len(name.strip()) == 0:
            name = self.__class__._default_label_

        #print("PlanarGraphics (%s).__init__ *args" % self.__class__.__name__, *args)
        
        #self.apiversion = (0,3)
            
        # NOTE: 2018-02-09 17:35:42
        # maps a planar graphic object to a tuples of three elements:
        #   partial, args, kwargs
        # used for coordinate mappings between two planar graphics objects
        self._linked_objects_ = dict() # PlanarGraphics: (partial, args, kwargs)
        
        self._frontends_ = list()
        
        self._states_ = list()
        
        self._currentstates_ = list()
        
        # NOTE: 2019-03-19 15:40:01
        # new API 19c19; keep z_frame out for backwards compatibility
        # add z_frame later, from frameindex
        shape_descriptors = [d for d in self._planar_descriptors_ if d != "z_frame"]
        
        # NOTE: 2019-03-21 09:00:31
        # cache the current state - make if a default state right now, update below
        # making sure this is ALWAYS a reference to one member of self._states_
        #self._currentstate_ = self.defaultState()
        
        #### BEGIN check and set graphicstype
        
        # NOTE: 2021-05-03 09:02:59
        # normally this should be set by the subclass attribute _planar_graphics_type_
        # however, it needs to be specified for Cursor objects - poor design...
        # print(f"{self.__class__.__name__}.__init__: graphicstype = {graphicstype}")
        if graphicstype is None:
            if isinstance(self, Cursor): # special treatment here
                self._planar_graphics_type_ = PlanarGraphicsType.crosshair_cursor
                    
            else:
                self._planar_graphics_type_ = self.__class__._planar_graphics_type_
        
        elif isinstance(graphicstype, (str, int)):
            graphicstype = PlanarGraphicsType.type(graphicstype)
            
        elif isinstance(graphicstype, PlanarGraphicsType):
            if isinstance(self, Cursor) and  graphicstype & PlanarGraphicsType.allCursorTypes == 0:
                expected_graphics_types = ["%s (%d)" % (t.name, t.value) for t in PlanarGraphicsType if "_cursor" in t.name.lower()]
                raise ValueError("For Cursor, 'graphicstype' is expected to be one of %s; got %s instead" % (expected_graphics_types,
                                                                                                graphicstype))
            elif graphicstype & PlanarGraphicsType.allShapeTypes == 0:
                expected_types = ["%s (%d)" % (t.name, t.value) for t in PlanarGraphicsType if "_cursor" not in t.name.lower()]
                raise ValueError("For Cursor, 'graphicstype' is expected to be one of %s; got %s instead" % (expected_types,
                                                                                                graphicstype))
            
        else:
            raise TypeError("graphicstype expected to be an int, a str, a pictgui.PlanarGraphicsType, or None; got %s instead" % type(graphicstype).__name__)
        
        self._planar_graphics_type_ = graphicstype
        
        # print(f"\t⇒: self._planar_graphics_type_ = {self._planar_graphics_type_}")
                
        #### END check and set graphicstype
        
        #### BEGIN NOTE: 2019-03-21 11:51:22 check currentframe
        
        if currentframe is None:
            currentframe = 0 # by default!
            
        elif not isinstance(currentframe, int):
            raise TypeError("currentframe expected to be an int (>=0) or None; got %s instead" % type(currentframe).__name__)
        
        elif currentframe < 0:
            currentframe = 0
        
        self._currentframe_ = currentframe
        
        #### END check currentframe
        
        if isinstance(name, str) and len(name):
            self._ID_ = name
            
        else:
            # NOTE: 2021-05-08 10:33:18 new automatic naming rule
            self._ID_ = self.__class__.__name__[0].lower()
            #if isinstance(self._planar_graphics_type_, PlanarGraphicsType):
                #self._ID_ = self._planar_graphics_type_.name
            #else:
                
        if not isinstance(self, Cursor):
            self._closed_ = closed
            
        else:
            self._closed_ = False
            
        # NOTE: 2018-01-12 16:18:37
        # Path is itself a list of PlanarGraphics, each with their own common state
        # and framestates; these need to be kept in sync.
        
        # ### BEGIN constructor code
        
        if len(args):
            if len(args) == 1:
                if isinstance(args[0], self.__class__): # COPY CONSTRUCTOR
                    # ### BEGIN copy c'tor
                    # also tries to fix historical inconsistencies in APIs
                    # NOTE: COPY CONSTRUCTOR: first var-positional parameter has
                    # the same class as self
                    # ignores named parameters
                    # ATTENTION: does NOT copy object links!
                    # CAUTION: ignores the following parameters:
                    #   graphicstype
                    #   closed
                    #   name
                    #   frameindex
                    #   linked_objects
                    
                    src = args[0].copy()
                    
                    self._ID_ = src._ID_
                    
                    self._closed_ = src._closed_
                    
                    self._planar_graphics_type_ = src._planar_graphics_type_
                    
                    # NOTE: this may or may NOT point to a valid z_frame;
                    # is does NOT matter here, but only at display time.
                    # ATTENTION current frame should be the z_frame of the 
                    # current state; the only exception is when the current state
                    # z_frame is None, in which case currentframe can have any value
                    # and is indepenent of currentstate
                    self._currentframe_ = src._currentframe_
                    
                    self._states_ = self.__class__.copyConvertStates(*src._states_)
                    
                    self.checkStates()
                    
                    return # we're DONE here
                
                    # ### END copy c'tor
                
                elif isinstance(args[0], (tuple, list)) and len(args[0]): # construct from descriptors
                    # construct from a single var-positional parameter, which is:
                    # * a sequence of coefficients (planar descriptors),
                    # * a sequence of PlanarGraphicsState/Bunch/dict

                    if all([isinstance(v, (numbers.Number, str)) for v in args[0]]):
                        self.__init_from_descriptors__(*args[0], 
                                                       frameindex=frameindex,
                                                       currentframe=currentframe)
                        
                    elif all([isinstance(v, dict) for v in args[0]]):
                        # construct from a sequence of states; 
                        # the states have already defined their frame visibility;
                        # if frameindex is given, this can be changed here
                        self.__init_from_states__(*args[0],
                                                          frameindex=frameindex,
                                                          currentframe=currentframe)
                    else:
                        raise TypeError("Expecting a sequence of planar descriptors or state dictionaries")
                    
                elif isinstance(args[0], dict): # construct from a state
                    # see NOTE: 2020-11-30 16:38:45 about frameindex
                    self.__init_from_states__(args[0], frameindex=frameindex, 
                                             currentframe=currentframe)
                        
            else:# NOTE: many var-positional arguments
                # When present, these can only be primitive types (scalars, str):
                # their number, order and semantics are specified by the
                # _planar_descriptors_ :class: attribute
                # When constructing a Path, args must contain individual PlanarGraphics objects
                # for text PlanarGraphics there is only one shape descriptor in the sequence
                # of descriptors and is a str
                # NOTE shape descriptors are the planar_descriptors less z_frame
                
                if isinstance(self, Path):
                    raise TypeError("Cannot use parametric constructor to initalise a Path")
                
                self.__init_from_descriptors__(*args, frameindex=frameindex,
                                               currentframe=currentframe)
            
        else: # no var-positional parameters given => plain (empty) PlanarGraphics
            if not isinstance(self, Path):
                self._states_ = [self.__class__.defaultState()]
                
                self._currentframe_ = currentframe
            
                self.checkStates()
                self._applyFrameIndex_(frameindex)
                
                if isinstance(self, Cursor):
                    if graphicstype is None:
                        self._planar_graphics_type_ = PlanarGraphicsType.crosshair_cursor
                        
                    else:
                        self._planar_graphics_type_ = graphicstype
                        
                else:
                    self._planar_graphics_type_ = graphicstype
                        
        # ### END constructor code

        if len(linked_objects):
            # TODO: deep copy
            self._linked_objects_.update(linked_objects)
            
    def _repr_pretty_(self, p, cycle):
        p.text(f"{self.__class__.__name__}: '{self.name}'")
        p.breakable()
        p.pretty(self._states_)
        p.text("\n")
        
            
    def __reduce__(self):
        shape_descriptors = [d for d in self._planar_descriptors_ if d != "z_frame"]
        
        if len(self._states_) == 0:
            states = [self.__class__.defaultState()]
            
        else:
            states = self._states_
        
        framedx = [s.z_frame for s in states]
        
        if isinstance(self, Path):
            return __new_planar_graphic__, (self.__class__,
                                            states,
                                            self._ID_,
                                            framedx,
                                            self.currentFrame,
                                            self._planar_graphics_type_,
                                            self.closed,
                                            self._linked_objects_.copy(),
                                            self._position_)
        
        elif isinstance(self, Cursor):
            return __new_planar_graphic__, (self.__class__,
                                         states,
                                         self._ID_,
                                         framedx,
                                         self.currentFrame,
                                         self._planar_graphics_type_,
                                         False,
                                         self._linked_objects_.copy())
        
        else:
            return __new_planar_graphic__, (self.__class__,
                                         states,
                                         self._ID_,
                                         framedx,
                                         self.currentFrame,
                                         self._planar_graphics_type_,
                                         self.closed,
                                         self._linked_objects_.copy())
        
    def __str__(self):
        states_str = ""
        
        #framestr = ""
        #print(len(self._states_))
        
        if len(self._states_) > 0:
            states = self._states_
            
            states_str = list()
            for state in states:
                states_str.append(", ".join(["%s=%s" % (key, state[key]) for key in self._planar_descriptors_] + ["z_frame=%s" % state.z_frame]))
                
            states_str = "\n\t".join(states_str)
                
        return "%s:\n\tstates:\n %s\n\tcurrent frame: %s" % (self.__repr__(),
                                                         states_str,
                                                         self.currentFrame)
            
    
    def __repr__(self):
        return " ".join([self.__class__.__name__, ", type:", getattr(self._planar_graphics_type_, "name", "None"), ", name:", self._ID_])

    def __call__(self, path:typing.Optional[QtGui.QPainterPath]=None, 
                 frame:typing.Optional[int]=None, 
                 closed:typing.Optional[bool]=None, 
                 connected:typing.Optional[bool]=False) -> QtGui.QPainterPath:
        """Returns a QtGui.QPainterPath object. 
        
        QPainterPath composition methods used here depend on the subclass of
        PlanarGraphics, and is specified by the 'qt_path_composition_call'
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
        
        NOTE: overwritten in Cursor & Path, which require special behaviour
        
        """
        if path is None:
            path = QtGui.QPainterPath()
            
        if closed is None:
            closePath = self.closed
            
        elif isinstance(closed, bool):
            closePath = closed
            
        else:
            raise TypeError("closed expected to be a boolean or None; got %s instead" % type(closed).__name__)
        
        if not isinstance(frame, int):
            frame = self.currentFrame
            
        state = self.getState(frame)
        
        if state:
            if isinstance(self, Move):
                if connected:
                    s = f"lineTo({state[self.shapeDescriptors[0]]},{state[self.shapeDescriptors[1]]})"
                else:
                    s = f"moveTo({state[self.shapeDescriptors[0]]},{state[self.shapeDescriptors[1]]})"
                eval(f"path.{s}")
                
                return path
                    
            origin = self.shapeDescriptors[:2]
            
            if isinstance(self, (Ellipse, Rect)):
                shapeDescriptors = self.shapeDescriptors
            # elif isinstance(self, (Line, Cubic, Quad)): # Live overrides this method
            elif isinstance(self, (Cubic, Quad)):
                shapeDescriptors = self.shapeDescriptors[2:]
            elif isinstance(self, (Arc, ArcMove)):
                shapeDescriptors = self.shapeDescriptors[2:4]
        
            if connected:
                s0 = f"lineTo({state[origin[0]]},{state[origin[1]]})"
            else:
                s0 = f"moveTo({state[origin[0]]},{state[origin[1]]})"
                
            eval(f"path.{s0}")
            
            s = [f"{self.qt_path_composition_call}("]
            
            s += [",".join(["%f" % state[a] for a in shapeDescriptors])]
            
            s+=[")"]
            
            eval(f"path.{''.join(s)}")
            
            if closePath:
                path.lineTo(state[origin[0]], state[origin[1]]) 
        
        return path

    def __getattr__(self, name):
        if name in self.__class__._planar_descriptors_:
            state = self.getState()
            if isinstance(state, dict):
                return state[name]
        
        else:
            return object.__getattribute__(self, name)
            
    def __setattr__(self, name, value):
        if name in self.__class__._planar_descriptors_:
            state = self.getState()
            if isinstance(state, Bunch):
                state[name]=value
            
        else:
            object.__setattr__(self, name, value)
            
    def checkStates(self):
        """Ensures consistency of states with respect to z_frame.
        
        A PlanarGraphics state can be:
        
        (a) ubiquitous: its z_frame attribute is None:
            * the state is represented (drawn) in all frames of the data 
            * there can only be one such state
            
        (b) frame-avoiding: the z_frame attribute is an int < 0
            * the state is represented in all frames EXCEPT the one which has
              index equal to -1 * z_frame - 1 (if it exists)
            
        (c) single-frame: the z_frame is an int >= 0
            * the state is represented ONLY in the frame with index == z_frame
              (if it exists)
            
        The co-existence of the states in a PlanarGraphics object is governed by
        three rules:
        
        Rule I. 
        -------
        An ubiquitous state is the ONLY state of the PlanarGraphics object.
        
            Corollaries:
            
            1) the PlanarGraphics object can have only one ubiquitous state, and
            
            2) no other states co-exist with an ubiquitous state
            
        Rule II. 
        --------
        A frame-avoiding state (fa_state) can co-exist with AT MOST one
        single-frame state and the two states must satisfy:
        
            fa_state.z_frame == -1 * sf_state.z_frame - 1
            
            where:
                fa_state is the frame-avoiding state, and
                sf_state is the single-frame state
        
            Corollaries:
        
            * there can be only one frame-avoiding state
            
            * a PlanarGraphics with a frame-avoding state can have at most two
              states, and the other state is single-frame
                
            * the single-frame state is drawn in the frame "avoided" by the 
              frame-avoding state
              
        Rule III. 
        ---------
        There can be any number of single-frame states.
            * A PlanarGraphics object with more than two states can have ONLY
              single-frame states.`
        
        Therefore, for any given frame, the ONLY state shown is determined as
        follows:
        
        1) Top priority: the state where z_frame is None
        
        1.1) If there is a state where z_frame is None, this state is KEPT and 
            all other states are DISCARDED.
        
        1.2) If there are several states where z_frame is None, ther first of 
            these is KEPT; all other states are DISCARDED,
        
        2) Next priority: the state where z_frame == -1 * frame_index -1
            There can be only ONE state with negative frame
            This state is shown in all frames except frame_index.
            There may be AT MOST ONE other state where z_frame == frame_index
            (and hence visible there)
        
        2.1) Can occur only when there is NO state where z_frame is None.
        
        3) Lowest priority in current frame: state where z_frame == frame_index
        
        NOTE: States are not sorted with respect to their z_frame value
        
        WARNING: This can be very expensive - only call it at construction
        """
        #print("PlanarGraphics (%s) checkStates: %d states: " % (self.__class__.__name__, len(self._states_)), self._states_)
        from core.utilities import unique
        if len(self._states_):
            # make sure the states conform to the planar descriptors
            states = [s for s in self._states_ if self.__class__.validateState(s)]
            
            #print("\tvalid states:", states)
            
            # 1) check for the existence of ubiquitous states
            ubiquitous_states = [s for s in states if s.z_frame is None]
            #print("\tubiquitous states:", ubiquitous_states)
            del ubiquitous_states[1:] # enforce singleton element - idiom works for empty lists too
            
            if len(ubiquitous_states):
                # if ubiquitous state found make it the only state then return
                self._states_[:] = ubiquitous_states
                return
            
            # 2) check the existence of frame-avoiding (fa) of single-frame (sf)
            # states 
            
            # make sure they are unique in z_frame value
            states = unique([s for s in states], key = lambda x: x.z_frame)

            # 2.1) find fa states - if found, make sure there is only one
            fa_states = [s for s in states if s.z_frame <  0]
            del fa_states[1:] # enforce singleton element - idiom works for empty lists too
            
            # 2.2) find sf states
            if len(fa_states):
                # if a fa state exists, keep the only sf state which doesn't 
                # conflict the fa frame in z_frame value (if found)
                sf_states = [s for s in states if s.z_frame == -fa_states[0].z_frame -1]
                
            else:
                sf_states = [s for s in states if s.z_frame >= 0]
                
            self._states_[:] = fa_states + sf_states
            
    @classmethod
    def isStateVisible(cls, state:Bunch, frame:int) -> bool:
        """Checks if state is visible in frame.
        """
        if not isinstance(state, Bunch):
            raise TypeError("Expecting a Bunch object; got %s instead" % type(state).__name__)

        if state.z_frame is None: # trivial: this is ALWAYS visible
            return True
        
        elif isinstance(state.z_frame, int):
            # state is visible in frame if:
            # a) frame >= 0, z_frame >= 0 and z_frame ==  frame
            # b) frame >= 0, z_frame <  0 and z_frame != -frame -1
            # c) frame <  0, z_frame >= 0 and z_frame != -frame -1
            # d) frame <  0, z_frame <  0 and z_frame !=  frame
            
            if frame >= 0: # check visibility in frame 
                if state.z_frame >= 0:
                    return state.z_frame ==  frame      # (a)
                        
                else:
                    return state.z_frame != -frame -1   # (b)
                
            else: # check for frame avoidance
                if state.z_frame >= 0:
                    return state.z_frame != -frame -1   # (c)
                
                else:
                    return state.z_frame !=  frame
            
        else:
            return False # shouldn't reach here
            
                    
    def _applyFrameIndex_(self, frameindex:typing.Optional[typing.Iterable]=[],
                            sort=False, none_last=False):
        """Reassigns the z_frame values.
        Use with CAUTION
        
        Parameters:
        ------------
        
        frameindex: iterable with int elements; optional , default is None
            When None or and iterable that is either empty or contains at least
            one None element, 
        
        sort: bool; optional, default is False
        
        none_last: bool; optional default is False
        
        """
        import math, bisect
        from core.utilities import unique
        # allows sorting by z_frames when None is amongst them
        # NOTE: however that by RULE I a state where z_frame is None is THE ONLY
        # state available
        none_place_holder = math.inf if none_last else -math.inf
        
        # NOTE: 2020-11-01 21:16:37
        # allow the specification of an empty frameindex as None
        if frameindex is None:
            frameindex = list()
            
        elif any([f is None for f in frameindex]): # another stupid bug
            frameindex = list()
            
        elif not isinstance(frameindex, (list, tuple, range)):
            raise TypeError("frameindex parameter expected to be a (possibly empty) sequence of int, or a range, or None; got %s instead " % type(frameindex).__name__)
            
        # NOTE: 2020-11-01 16:05:25
        # make sure frameindex is a unique sequence of numbers
        # unique also converts a range to a sequence of integers
        # sorted does nothing on lists from generated from range (for obvious
        # reasons)
        frameindex = unique(frameindex)
                      
        if sort:
            frameindex = sorted(frameindex, key = lambda x: x if x is not None else none_place_holder)
        
        # NOTE: 2020-11-01 16:07:37
        # check for absence of overlap between frame indices for visible and
        # invisible states
        # get indices of invisible states (z_frame < 0), converted to "real" 
        # frame indices (-1 * z_frame -1) --> these should resolve to 
        # indices >= 0 that are NOT included in the given frameindex, otherwise 
        # the visibility of the associated state(s) is ambiguous; 
        # NOTE: frameindex may contain None, for the state that is meant to
        # be visible in all frames
        f_inv = [-v-1 for v in frameindex if isinstance(v, int) and v < 0]
        
        f_ambiguous = [v for v in frameindex if v in f_inv]
        
        if len(f_ambiguous):
            raise ValueError("The state visibility for the following frame indices is ambiguous: %s" % f_ambiguous)
        
        if sort:
            states = self.sortedStates()
            
        else:
            states = self._states_
            
        if len(frameindex):
            # if there is ony one state, generate a sequence of states with 
            # same values but with defined z_frame attribute
            if len(states) == len(frameindex):
                # NOTE: 2020-11-01 18:01:41
                # In the ideal case, frameindex contains as many indices as
                # there are in self._states_. Each state in self._states_ 
                # gets the index in frameindex in order.
                #
                # This also applies to the case of a single state
                #
                # In addition, any state where z_frame is None should now
                # have a valid z_frame
                for k, f in enumerate(frameindex):
                    states[k].z_frame = f
                    
            else:
                if len(states) == 1:
                    # NOTE: 2020-11-01 18:01:36
                    # one can specify a single state and several frame indices
                    # to generate frame states with identical descriptor values
                    # for those frames
                    #
                    # again, this results in multiple states with valid z_frame
                    state = states[0]
                    s_states = list()
                    
                    for f in frameindex:
                        s = Bunch(state.copy())
                        s.z_frame = f
                        s_states.append(s)
                        
                    self._states_[:] = s_states[:]
                
                elif len(states) < len(frameindex):
                    for k, s in enumerate(states):
                        s.z_frame = frameindex[k]
                        
                    self._states_[:] = s_states[:]
                    
                elif len(states) > len(frameindex):
                    for k,  in enumerate(frameindex):
                        states[k].z_frame = f
                        
                    self._states_[:] = s_states[:]
                    
                    # NOTE: 2020-11-01 18:03:18
                    # for many states, there MUST be as many frame indices 
                    # as there are states (unless frameindex is empty, see 
                    # below)
                    #
                    #print("PlanarGraphics._applyFrameIndex_ in %s: frameindex =" % self.__class__.__name__, 
                          #frameindex)
                    #raise ValueError("Mismatch between the number of states (%d) and that of frame indices (%d)" % (len(self._states_), len(frameindex)))
        
            
    @property
    def pos(self) -> QtCore.QPointF:
        """The position of this object as a Qt QPointF.
        """
        position = self.position
        #print("PlanarGraphics.pos: position = (%s, %s)" % position)
        if any([p is None for p in position]):
            return QtCore.QPointF()
        
        return QtCore.QPointF(position[0], position[1])
    
    @pos.setter
    def pos(self, value:QtCore.QPointF):
        if not all(s in self._planar_descriptors_ for s in ("x", "y")):
            return
        
        if isinstance(value, (QtCore.QPoint, QtCore.QPointF)):
            self.position = (value.x(), value.y())
            
        else:
            raise TypeError("Expecting a QPoint or QPointF; got %s instead" % type(value).__name__)
        
    @property
    def position(self) -> tuple:
        """The position of this object as (x,y) coordinates tuple.
        
        To change, assign a pair (x,y) of new coordinate values (a tuple), 
        a QPoint, or a QPointF object to this property.
        
        See "x" and "y" properties for what these coordinates mean.
        
        """
        #print("PlanarGraphics.position() for %s " % self)
        if all(s in self._planar_descriptors_ for s in ("x", "y")):
            return (self.x, self.y)
        return (None, None)
    
    @position.setter
    def position(self, x, y=None):
        if not all(s in self._planar_descriptors_ for s in ("x", "y")):
            return
        
        if isinstance(x, (tuple, list)) and len(x) == 2 and all([isinstance(v, numbers.Real) for v in x]):
            self.x = x[0]
            self.y = x[1]
            
        elif isinstance(x, (QtCore.QPoint, QtCore.QPointF)):
            self.y = x.y()
            self.x = x.x()
            
        elif all(isinstance(v, numbers.Real) for v in (x,y)):
            self.x = x
            self.y = y
            
        else:
            raise TypeError("Expecting x,y two scalars a tulpe of scalars, or just a Qt QPoint or QPointF")

        #self.x = x[0]
        #self.y = x[1]
        
        self.updateLinkedObjects()
        
    def translate(self, dx, dy):
        descr = self.shapeDescriptors
        xDescr = [d for d in self.shapeDescriptors if "x" in d]
        yDescr = [d for d in self.shapeDescriptors if "y" in d]
        state = self.getState()
        if state:
            for x in xDescr:
                state[x] += dx
            for y in yDescr:
                state[y] += dy
            
        # BUG: 2024-08-25 09:04:30 FIXME
        # prone to infinite recursion and attribute error !
        
        # self.x += dx
        # self.x += dy
        
    def point(self, frame=None):
        """Alias to qPoint()
        """
        return self.qPoint(frame=frame)
    
    def points(self, frame:typing.Optional[int]=None):
        """Alias to qPoints
        """
        return self.qPoints(frame=frame)
    
    def qPoints(self, frame:typing.Optional[int]=None, inPath:bool=False):
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
        cp = self.controlPoints(frame, inPath)
        
        if len(cp):
            return list(map(lambda x: QtCore.QPointF(x[0], x[1]), cp))
        else:
            return list()
    
    def qPoint(self, frame:typing.Optional[int]=None, inPath:bool=False):
        """Returns the QPointF of the destination point in a PlanarGraphics primitive.
        For Path, Ellipse, Rect, Arc, ArcMove, returns the QPoint of its first element.
        
        This may be a null point if specified frame does not associate a state.
        
        Relies on qPoints, which should be overridden by :subclasses:
        
        """
        return self.qPoints(frame, inPath)[0]
    
    @property
    def currentState(self):
        """Read-only. Alias to self.getState()
        
        NOTE: even if this is a read-only property, the returned object is 
        mutable.
        
        """
        return self.getState()
        
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
        
        return self._currentframe_
        
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
        
        if value is None:
            value = 0
            
        self._currentframe_ = value
        
    @property
    def states(self):
        """The list of underlying states
        """
        return self._states_
    
    @property
    def sortedStates(self):
        """A list of frame states, sorted by their z_frame attribute
        States where z_frame is None are placed at the end of the list.
        
        NOTE: Does not verify the states' z_frame conformance with the three rules
        """
        import math

        if len(self._states_) > 1:
            return sorted(self._states_, key = lambda x: x.z_frame if (isinstance(x.z_frame, int) and x.z_frame >= 0) else -x.z_frame-1 if (isinstance(x.z_frame, int) and x.z_frame < 0) else math.inf)
        
        else:
            return self._states_
        
    def sortStates(self, none_last=True):
        """Sorts the states according to the value of z_frame attribute.
        
        States where z_frame is None are placed at the end of the list if none_last
        is True, or at the beginning otherwise.
        
        NOTE: A state where z_frame is None should be the ONLY state of the object.
        There can be at most ONE state (sate A) with z_frame < 0; when such a 
        state exists, then there can be at most ONE other state (state B) 
        with z_frame > 0 such that 
        
        state_A.z_frame == -1 * state_B.z_frame -1
        NOTE: Does not verify the states' z_frame conformance with the three rules
        """
        import math
        
        none_place_holder = math.inf if none_last else -math.inf
        
        if len(self._states_) > 1:
            states = sorted(self._states_, key = lambda x: x.z_frame if (isinstance(x.z_frame, int) and x.z_frame >= 0) else -x.z_frame-1 if (isinstance(x.z_frame, int) and x.z_frame < 0) else none_place_holder)
            self._states_[:] = states[:]
    
    @property
    def descriptors(self):
        """Tuple of planar graphics descriptor names specific to this
        concrete subclass.
        Read-only
        """
        return self.__class__._planar_descriptors_
    
    @property
    def shapeDescriptors(self):
        """Tuple of shape descriptor names.
        These are the 'descriptor' property, less "z_frame".
        Read-only
        """
        return tuple(d for d in self.__class__._planar_descriptors_ if d != "z_frame")
    
    @property
    def closed(self):
        return self._closed_
    
    @closed.setter
    def closed(self, value):
        if not isinstance(value, bool):
            raise TypeError("value expected to be a boolean; got %s instead" % type(value).__name__)
        
        self._closed_ = value
        
    def destination(self, frame:typing.Optional[int] = None) -> tuple:
        """(X,Y) coordinate pair for the last point of the PlanarGraphics"""
        cp = self.controlPoints(frame)
        return cp[-1]
        
    def controlPoints(self, frame:typing.Optional[int]=None, inPath:bool=False):
        """Returns the control points coordinates for the primitive.
        Coordnates are given for the state associated with a frame (if given) or
        with the current frame.
        Parameters:
        ==========
        frame: int, optional, default is None; when given, the method returns the 
            coordinate of the control points for the state associated with
            the specified frame (if such association exists); for a PlanarGraphics
            with no frame-state association, returns the coordinates in the
            "universal" state.
        inPath:bool, default is False.
            There is an important difference between the control points of a PlanarGraphics
            that belongs to a Path, versus a stand-alone. When a PlanarGraphics 
            belongs to a Path, and it not a Move primitive, its first point is also 
            the destination point of the previous PlanarGraphics of the Path,
            and therefore it would be returned twice when querying the points for
            PlanarGraphics of a Path. To avoid this, set inPath flag to True, to
            return only the "True" control points of the PlanarGraphics primitive.
        
            This applies for all primitives except cursors, Move, Text, and those 
            defined by a bounding rectangle (Arc, ArcMove, Ellipse, Rect) — thus, 
            these are: Line, Cubic, Quad.
        
            When inPath is False (default), then ALL "control" points are returned.
            (NOTE that for Cubic and Quad, the first point is not considered a
            control point for the corresponding elements of QPainterPath composition)
        
        
        """
        if isinstance(self, Cursor):
            raise NotImplementedError("Cursors do not have control points")
        
        if frame is None:
            state = self.currentState
            
        else:
            state = self.getState(frame)
            
        if state is None or len(state) == 0:
            return tuple()
        
        cp = tuple(map(lambda x: (getattr(state, x[0]), getattr(state, x[1])), 
                         itertools.islice(itertools.pairwise(self.shapeDescriptors), 0, None, 2)))
        
        if inPath and isinstance(self, (Line, Cubic, Quad)):
            cp = cp[1:]
            
        return cp
        
    def controlQPoints(self, frame:typing.Optional[int]=None, inPath:bool=False):
        if isinstance(self, Cursor):
            raise NotImplementedError("Cursors do not have control points")
        
        cp = self.controlPoints(frame, inPath)
        return tuple(map(lambda x: QtCore.QPointF(x[0], x[1]), cp))
        
    def controlPath(self, frame:typing.Optional[int]=None, inPath:bool=False):
        """Returns a copy of this object as a Path object containing control points.
        
        The returned Path is composed of Move and Line elements only.
        
        Path objects and special graphics primitives (e.g., ArcTo, ArcMove, 
        Ellipse, Rect, Cubic, Quad, etc) should override this function.
        
        """
        if isinstance(self, Cursor):
            raise NotImplementedError("Cursors do not have control path")
        
        ret = Path()
        cp = self.controlPoints(frame, inPath)
        for k, p in enumerate(cp):
            if k == 0:
                ret.append(Move(p[0], p[1]))
                
            else:
                ret.append(Line(cp[k-1][0], cp[k-1][1], p[0], p[1]))
            
        return ret
        
    def fromControlPath(self, path, frame:typing.Optional[int]=None):
        """Set this planar graphics' descriptor coordinates from a control Path.
        A control Path is a Path containing exclusively Move and Line primitives.
        Overwritten in Move, Arc, ArcMove
        """
        if not isinstance(path, Path):
            raise TypeError(f"path expected to be a pictgui.Path; got {type(path).__name__} instead" )
        
        # Move: 1 shape descriptor
        shapePoints = len(self.shapeDescriptors)//2
        
        if len(path) != shapePoints:
            raise ValueError(f"path expected to have {shapePoints} elements; got {len(path)} elements instead")

        if not all(isinstance(p, (Move, Line)) for p in path):
            raise ValueError("Expecting a path containing only Move and Line objects")

        control_state = path.currentState
        
        if control_state is None or len(control_state) == 0:
            raise ValueError("path argument has undefined state")
        
        if frame is None:
            state = self.currentState
            
        else:
            state = self.getState(frame)
            
        if state is None or len(state) == 0:
            return
        
        # NOTE: 2024-08-24 12:43:30 
        # What this does (breakdown of the comprehension below, for future reference)
        # <example for a Quad object, in pseudocode; '→' indicates the result of 
        # the comprehension if it was evaluated by wrapping it in a list constructor:
        #
        # 1) distributes the shape decriptors in a sequence of pairs:
        #   NOTE 2024-08-24 13:18:56
        #   itertools.pairwise([abcdef]) generates [ab, bc, cd, de, ef],
        #   but I want only [ab, cd, ef] therefore I feed this into itertools.islice
        #
        #   itertools.islice(itertools.pairwise(self.shapeDescriptors), 0, None, 2) 
        #   → [('c0x', 'c0y'), ('c1x', 'c1y'), ('c2x', 'c2y')]
        #
        # 2) 'extracts' the x, y coordinate pairs of the points on the path, where
        # x0,y0,x1,y1,x2,y2 are the coordinate values of the three points on the path:
        #
        #   map(lambda x: (x.x, x.y), path) 
        #   → [(x0, y0), (x1, y1), (x2, y2)]
        #
        # 3) pairs (zips) (1) with (2)
        #   → [(('c0x', 'c0y'), (x0, y0)), (('c1x', 'c1y'), (x1, y1)), (('c2x', 'c2y'), (x2, y2))]
        #    (note the nested tuples)
        #
        # 4) matches each shape descriptor with its value — steps:
        # 4.1) collate (3) in a single iterable (still pairwise):
        #   itertools.chain.from_iterable(zip(itertools.islice(itertools.pairwise(self.shapeDescriptors), 0, None, 2), map(lambda x: (x.x, x.y), path)))
        #   → [('c0x', 'c0y'),(x0, y0), ('c1x', 'c1y'), (x1, y1), ('c2x', 'c2y'), (x2, y2)]
        #
        # 4.2) orthogonalize the pairings:
        #   4.2.1) expand (unzip) (4.1) to generate two sequences:
        #       zip(*itertools.chain.from_iterable(zip(itertools.islice(itertools.pairwise(self.shapeDescriptors), 0, None, 2), map(lambda x: (x.x, x.y), path))))
        #       → [('c0x', x0, 'c1x', x1, 'c2x', x2), ('c0y', y0, 'c1y', y1, 'c2y', y2)]
        #
        #   4.2.2) chain (concatenate) the result from (4.2.1) to obtain an iterable 
        #   where each attribute and its corresponding value are interleaved:
        #       itertools.chain.from_iterable(<result of 4.2.1>)
        #       → ['c0x', x0, 'c1x', x1, 'c2x', x2, 'c0y', y0, 'c1y', y1, 'c2y', y2]
        #
        #   4.2.3 split the results of (4.2.2) into a sequence of (attribute, value) pairs:
        #       (see NOTE 2024-08-24 13:18:56 explaining why I feed pairwise into islice)
        #       itertools.islice(itertools.pairwise(<result of 4.2.2>), 0, None, 2)
        #       → [('c0x', x0),('c1x', x1),('c2x', x2),('c0y', y0),('c1y', y1),('c2y', y2)]  ⇇ orthogonalized version of (4.1)
        #
        # 4.3) apply the value to their attributes — 
        #   map(lambda x: setattr(state, x[0], x[1]), <result of 4.2.3>)
        # 
        #  NOTE: 2024-08-24 13:26:02 
        #  in the comprehesion below, map MUST be evaluated hence we wrap it in 
        #  a tuple constructor, even if the statement returns a tuple of None objects,
        #  which will be garbage collected
        #
        # tuple(map(lambda x: setattr(state, x[0], x[1]), itertools.islice(itertools.pairwise(itertools.chain.from_iterable(zip(*itertools.chain.from_iterable(zip(itertools.islice(itertools.pairwise(self.shapeDescriptors), 0, None, 2), map(lambda x: (x.x, x.y), path)))))), 0, None, 2)))
        tuple(map(lambda x: setattr(state, x[0], x[1]), itertools.islice(itertools.pairwise(itertools.chain.from_iterable(zip(*itertools.chain.from_iterable(zip(itertools.islice(itertools.pairwise(self.shapeDescriptors), 0, None, 2), map(lambda x: (x.x, x.y), control_state)))))), 0, None, 2)))
        
        self.updateFrontends()

    def convertToPath(self, closed=False): 
        """Creates a Path from all frame-state associations.
        """
        # TODO: 2024-08-24 20:38:29 FIXME
        # must revisit this — what does it do ?!?
        frame_states = self.states
        
        frame_ndx = self.frameIndices
        
        ret = self.objectForFrame(frame=frame_ndx[0], closed=closed)
        
        for f in frame_ndx[1:]:
            frame_path = self.objectForFrame(frame=f, closed=closed)
            
            ret.addState(frame_path.currentState, f)
            
        ret.currentFrame = self.currentFrame
        
        return ret
    
    def copy(self):
        """Calls copy constructor and returns the result.
        WARNING: linked objects are stored by reference
        """
        #Path objects need special treatment here:
        
        if "z_frame" not in self._planar_descriptors_:
            self._planar_descriptors_ = tuple([d for d in self._planar_descriptors_] + ["z_frame"])
        
        if isinstance(self, Path):
            ret = self.__class__(self)
        
        else:
            if not hasattr(self, "_states_"):
                # for old API there's nothing we can do here to rescue
                self._states_ = [self.__class__.defaultState()]
                
            states = self._states_
            ret = self.__class__(states, 
                                graphicstype=self._planar_graphics_type_,
                                frameindex=self.frameIndices,
                                name=self._ID_,
                                closed=self.closed,
                                currentframe = self.currentFrame) # conforms with the new API
        
        ret._linked_objects_ = self._linked_objects_
        
        return ret
        
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
        
        #if len(ret._states_) == 1 and ret._states_[0].z_frame < 0:
        if len(ret._states_) == 1 and ret._states_[0].z_frame is None:
            ret._states_[0].z_frame = 0
            
        #do the same for the other
        #if len(other.states) == 1 and other.states[0].z_frame < 0:
        if len(other.states) == 1 and other.states[0].z_frame is None:
            other.framestates[0].z_frame = 1
        
        receiver_states = sorted(ret._states_, key = lambda x: x.z_frame)
        
        receiver_frames = [s.z_frame for s in receiver_states]
        
        past_the_post = max(receiver_frames) + 1
        
        for state in other.states:
            state.z_frame += past_the_post
        
        # NOTE: ret._currentstates_ stays the same
        
        ret._states_ += other.states
        
        return ret
            
    @property
    def maxFrameIndex(self):
        """The largest frame index or None (for frameless state objects)
        """
        if len(self._states_):
            if len(self._states_) == 1:
                return self._states_[0].z_frame
            
            else:
                frames = [-s.z_frame - 1 if s.z_frame < 0 else s.z_frame for s in self._states_ if s.z_frame is not None]
                
                return max(frames) if len(frames) else None
                
    
    @deprecated
    def addState(self, state):
        """ Adds (inserts or appends) a state.
        DEPRECATED Please use setState instead
        Parameters:
        ===========
        
        state: traitlets.Bunch with members that must conform to the particular 
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
        
        return
        
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
                sigBlock = QtCore.QSignalBlocker(f)
                if f.name != self.name: # check to avoid recurrence
                    old_name = f.name
                    f.name = self.name
                    viewer = None
                    
                    if type(f.parentwidget).__name__ == "ImageViewer":
                        viewer = f.parentwidget.viewerWidget
                        
                    elif type(f.parentwidget).__name__ == "GraphicsImageViewerWidget":
                        viewer = f.parentwidget
                        
                    if viewer is not None and hasattr(viewer, "_graphicsObjects"):
                        objDict = viewer._graphicsObjects[f.objectType]
                        old_f = objDict.pop(old_name, None)
                        objDict[self.name] = f
                    
                f.currentFrame = self.currentFrame
                
                x = self.x
                y = self.y
                
                if x is not None and y is not None:
                    super(GraphicsObject, f).setPos(x, y)

                f.setVisible(self.hasStateForFrame(f._currentframe_))
                
                f.redraw()
                
    def updateFrontend(self, f):
        """To be called after manual changes to this objects' descriptors.
        
        To avoid infinite recursion, do not calling this function from __setattr__()
        
        """
        if len(self._frontends_) and f in self._frontends_:
            f._currentframe_ = self.currentFrame
            
            if len(self.frameIndices):
                f.setVisible(f._currentframe_ in self.frameIndices)
                
            else:
                f.setVisible(True)
                    
            f.setPos(self.x, self.y) # also calls _makeObject_() and update()
            
    def removeState(self, stateOrFrame):
        """Removes a state associated with a frame index or indices specified in "stateOrFrame".
        
        stateOrFrame must contain valid frame indices.
        
        Function does nothing if the PlanarGraphics object has a common state.
        
        Parameters:
        ==========
        stateOrFrame:   a Bunch (state), an int, OR
                        a sequence (tuple, list) of states or int (no mixed types!)
        
        """
        import core.datatypes  
        
        sorted_states = sorted(self._states_, key = lambda x:x.z_frame)
        
        sorted_fr_ndx = [s.z_frame for s in sorted_states]
        
        if isinstance(stateOrFrame, int):
            if stateOrFrame in sorted_fr_ndx:
                state = sorted_states[sorted_fr_ndx.index(stateOrFrame)]
                self._states_.remove(state)
                
            else:
                raise ValueError("No state found for frame %d" % stateOrFrame)
            
        elif isinstance(stateOrFrame, Bunch):
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
                
            elif all([isinstance(v, Bunch) for v in stateOrFrame]):
                for states in stateOrFrame:
                    if state in self._states_:
                        self._states_.remove(state)
                        
                    else:
                        raise ValueError("state %s not found" % state)
            
        else:
            raise TypeError("expecting an int, a Bunch, or a sequence of int or Bunch objects (no mixed types); got %s instead" % stateOrFrame)
        
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
        and found in any of the descriptor state objects.
        
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
            
    def hasStateForFrame(self, frame=None):
        """Returns True if there is a state is visible in frame.

        Parameters:
        ===========
        
        frame : int, or None; the frame index for which the associated state is 
            sought
            
        Returns:
        =======
        
        True when self.states contain a state that is visible in frame.
        
            The can be: 
            * an ubiquitous state
            * a single-frame state
            * a frame-avoiding state
        
        """
        state = self.getState(frame)
        return (state is not None) 
        
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
            
        if state is None: # or len(state) == 0:
            warnings.warn("%s.qGraphicsItem: undefined state" % self.__class__.__name__, stacklevel=2)
            return QtWidgets.QGraphicsPathItem()
        
        return QtWidgets.QGraphicsPathItem(self(path=None, frame=frame, closed=self.closed)) # by default, the most generic case
        
    def stateIndex(self, state:typing.Optional[typing.Union[Bunch, int]]= None, 
                           visible_only:bool=False) -> typing.Optional[int]:
        """Get the index of a state in this object's internal list of states.
        
        Parameters:
        ===========
        
        state: Bunch object (state), int or None (z_frame); default is None

        visible_only: bool (optional, default is False)
            
        Returns:
        =======
        
        An int or None.
        
        If 'state' is a Bunch which exists in the internal list of states,
            returns the index of the state in the list, else returns None.
            
        If 'state' is None:
            * returns the index of the current state
            in the internal list
            
        If 'state' is an int:
        
                * if 'state' < 0 returns the index of the frame-avoiding
                    state with state.z_frame == state, if found, or None.
                
                * if 'state' >= 0
                
                    * if visible_only is False (default) returns the index of the
                        single-frame state where state.z_frame == state or None.
                    
                    * if visible_only is True:
                        if there is a single-frame state where 
                        state.z_frame == state, returns its index (as above)
                        
                        otherwise, if there is a frame-avoding state visible in
                        the frame with index z_frame (i.e., the state where
                        state.z_frame != -state - 1), returns its index;
                        
                        otherwise, return None
                        
        NOTE: For any given frame index there can be only one state visible in 
        that frame.
        
        A state where state.z_frame is None is always visibile and is the ONLY 
        state state in the internal list, hence its index is always 0 (zero), 
        if it exists in the internal states list.
        
        Examples:
        ========
        
        stateIndex() -> the index of the current state
        
        stateIndex(state) -> the index of the 'state', or None if 'state' is 
            not present in the internal list of states
        
        stateIndex(z_frame=-1) -> index of the frame-avoding state with 
            state.z_frame == z_frame, or None if such state is not found.
            
        stateIndex(z_frame=1) -> index of the single-frame state where
            state.z_frame == 1, if found, or None.
            
        stateIndex(z_frame=1, visible_only=True) -> index of the 
            single-frame state with state.z_frame == 1 if found, OR
            
            index of the frame-avoiding state with state.z_frame != -2 if found, 
            
            OR None
            
        """
        from core.utilities import index_of
        
        if isinstance(state, int):
            state = self.getState(z_frame=state, return_visible=visible_only)
            
        elif state is None:
            state = self.getState()
            
        elif not isinstance(state, Bunch):
            raise TypeError(f"Expecting a state Bunch object, int or None; got {type(state).__name__} instead")
        
        if self.validateState(state):
            return index_of(self._states_, state, key = lambda x: x.z_frame)
                        
    def getState(self, frame:typing.Optional[int]=None,
                 visible:bool=True) -> typing.Optional[Bunch]:
        """Access the state according to their z_frame value.
        
        By definition, a primitive PlanarGraphics (i.e., NOT a Path) has only
        one state Bunch associated with a given frame (which, depending on its
        'z_frame' value, it may be visible in the frame, or not).
        
        Parameters:
        ----------
        frame: int, None (default) 
            ATTENTION: When frame is None, then the method will return the state
            associated with the current frame.
            
        visible: bool, optional (default is True):
            When True, returns the state that is visible in the specified frame 
            index, i.e. state.z_frame is one of: None, value of 'frame', or any 
            int < 0 and != -frame - 1.
            
            When False, returns the state which has state.z_frame == frame, or 
            None if no state exists with state.z_frame == frame.
            
        Returns:
        -------
        
        The state (Bunch) for the current frame or None.
        
        The Bunch state object can be:
        
        * the unique state with ubiquitous visibility (i.e., state.z_frame is None)
            - is such a state exists, it will be returned regardless of the 
                value of the 'frame' parameter, as it is the only state 
                available
                
        * the non-ubiquitous state that is visible in the frame with the index 
            specified by 'frame'; this state is either:
            
            - a single-frame state with state.z_frame == frame if it exists,
            
            or
            
            - the frame-avoiding state that would be visible in this frame, i.e.:
                
                state.z_frame != -1 * frame -1
            
        NOTE: It does not make sense to query for a state where 
        state.z_frame is None, since such a state, if it exists, is the only 
        state allowed.
        
        Hence, getState() called with frame having any acceptable value
        (either int or None) and return_visible=True (the default) will always
        return the ubiquitous state if it exists.
            
        Examples:
        ========
        1. self.getState() -> the state visible in the current frame, if existing,
            otherwise None
            
            The returned state's z_frame attribute is either
                None or an int >= 0 and equal to current_frame, or an int < 0
                and != -current_frame - 1
                
        2. self.getState(visible=False) -> the state where
            state.z_frame == current_frame
            
            or None if such a state does not exist.
            
            ATTENTION:
            In this case the function returns None even if there exists an
            ubiquitous state, or a frame-avoiding state that would be visible in 
            the frame with index frame.
            
        3. self.getState(frame=-3) -> the state 
        """
        if frame is None:
            frame = self._currentframe_
            
        if not isinstance(frame, int):
            raise TypeError("'frame' expected to be an int; got %s instead" % type(frame).__name__)
            
        if visible:
            states = list(s for s in self._states_ if self.__class__.isStateVisible(s, frame))
        else:
            states = list(s for s in self._states_ if s.z_frame in (frame, None))
            
        if states:
            return states[0]
            
    def setFrameIndex(self, state:typing.Optional[typing.Union[Bunch, int]]=None, 
                      new_frame:typing.Optional[int]=None,
                      check_visible:bool=True,
                      nFrames:typing.Optional[int]=None):
        """Sets the z_frame of an EXISTING state to a new value.
        
        Does nothing if the state does not exist in self.states
        
        Parameters:
        ----------
        state: Bunch state object or None
            when a Bunch, it must exist in the internal states list
            
            when None, the function operates on the current (visible) state.
                If there is no visible state in the current frame, then returns
                without effect.
                To avoid this, make sure a Bunch is pased as state parameter
                
        new_frame: int or None
            When None, set the z_frame value of the state to None:
                effectively, the state becomes ubiquitous
                
            Otherwise, set the z_frame value to the value of new_frame.
                If new_frame is < 0 the state becomes frame-avoiding; otherwise
                it becomes a single-frame state.
                
            To set the z_frame value to the current frame just pass 
            self.currentFrame here
            
        check_visible:bool, optional (default is True)
            Used when state is None; when True, operate on the state visible in
            the current frame; otherwise, operate in the state where
            z_frame == current frame, if it exists
                    
        NOTE: Might want to call self.checkStates() after executing this function.
        Since self.checkStates() can be expensive the decision to call it is left to 
        the user.
        """
        if state is None:
            if new_frame == self._currentframe_:
                return # no change needed here
            
            state = self.getState(visible=check_visible)
            if state is None: #no state found for current frame -> bye
                warnings.warn("There is no %sstate for frame %d", ("visible " if check_visible else "", self._currentframe_))
                return
            
        if isinstance(state, Bunch):
            if state not in self._states_: # state not found in self._states_ => quit
                warnings.warn("The state %d does not exist for this object" % state)
                return
            
        if state.z_frame == new_frame: # avoid stupid actions
            return
        
        # index of state to be modified, in the internal list
        state_ndx = self.stateIndex(state, visible_only = check_visible) 
        
        if new_frame is None:
            # make state ubiquitous; discard all other states
            state.z_frame = new_frame
            self._states_[:] = [state]
            return
            
        elif isinstance(new_frame, int):
            if new_frame >= 0:
                # state is to become a single-frame state
                # is there a state visible at new_frame?
                old_state = self.getState(new_frame)
                
                # old_state, if found, is either ubiquitous, frame-avoding or single-frame
                
                if old_state is not None:
                    if old_state.z_frame is None:
                        # old_state is ubiquitous => make it single-frame for new_frame
                        # incidentally, here old_state is state itself
                        state.z_frame = new_frame
                        self._states_[:] = [state]
                        return
                    
                    elif old_state.z_frame >= 0:
                        # old_state is single-frame state - will have to be
                        # removed
                        #
                        # if state is currently frame-avoiding, then old_state
                        # is single-frame; after this, self._states_ ends up 
                        # with just the modified state
                        #
                        # if state is single-frame, self._states_ ends up with
                        # one less state
                        ndx = self.stateIndex(old_state)
                        del self._states_[ndx]
                        state.z_frame = new_frame # now state is single-frame
                        return
                        
                    elif old_state.z_frame < 0:
                        # old_state a frame-avoiding state be visible at new-frame;
                        # by rule II, state is the only other state 
                        # present and is single-frame, unless old_state is state
                        if state.z_frame < 0:
                            # this must be the same as old_state; since this is
                            # also the only frame visible at new_frame make it 
                            # single-frame at new frame and consequently, the only
                            # state present
                            state.z_frame = new_frame
                            self._states_[:] = [state]
                            return
                        else: # state is currently single-frame
                            # state is single-frame and wants to become visible
                            # where the old (frame-avoiding) state was visible
                            # therefore we create single-frame copies of the old
                            # state that are visible in all the other frames 
                            # EXCEPT the frame it was originally avoiding, AND 
                            # the new frame
                            old_avoided_frame = -old_state.z_frame  - 1
                            
                            max_frame = max([old_avoided_frame, new_frame])
                            
                            if isinstance(nFrames, int):
                                if nFrames <= max_frame:
                                    nFrames = max_frame + 1
                                    
                            else:
                                nFrames = max_frame + 1
                                
                            new_states = list()
                            
                            for k in range(nFrames):
                                # copy old state to single-frame states visible
                                # in all BUT the originally avoided frame and the
                                # new frame
                                if k not in (old_avoided_frame, new_frame):
                                    s = Bunch(old_state.copy())
                                    s.z_frame = k
                                    new_states.append(s)
                                
                            # now update the state
                            state.z_frame = new_frame
                            new_states.append(state)
                            # and replace the states list
                            self._states_[:] = new_states
                            return
                        
                else: # there is no state visible at new_frame
                    # NOTE: 2020-11-30 16:26:11
                    # remember new_frame is >= 0 here and that the following
                    # cases fall under the branch above:
                    # either state.z_frame is None
                    # or state.z_frame < 0 and state.z_frame == -new_frame - 1
                    
                    # therefore:
                    state.z_frame = new_frame
                    return
                    #### BEGIN NOTE 2020-11-30 16:06:59: 
                    # The logic for this is justifed as follows:
                    #if state.z_frame < 0:
                        ## state is originally frame-avoiding and by implication
                        ## in this branch of code is the only state
                        ##
                        ## simply assign new_frame to state.z_frame and this will
                        ## become the only single-frame state in the object
                        ## (by implication the othee frames will be stateless)
                        #state.z_frame = new_frame
                        #return
                        
                        ## let avoided_frame = -state.z_frame - 1
                        ##
                        ##if new_frame == avoided_frame:
                            ## state wants to be visible in the frame it currently
                            ## avoids.
                            ## since there is no other state visible, we simply
                            ## turn this state from a frame-avoiding into
                            ## a single-frame state; is will still be the only 
                            ## state available to the object
                        
                        ##else:
                            ## state wants to be visible in a frame where it 
                            ## already was visible; so this situation should have
                            ## come up in the above branch; nevertheless, we are
                            ## transforming the state into a single-frame state;
                            
                    #else: # state is single-frame
                        ## since no other state is visible at the target new_frame
                        ## we just simply change its z_frame value to new_frame
                    #### END NOTE 2020-11-30 16:06:59: 
                        
                    
                    
            else: # new_frame < 0
                # state is to become a frame-avoiding state
                # if there is a state that is visible in the newly avoided frame
                # then keep it
                avoided_frame = -new_frame - 1
                old_state_ndx = self.stateIndex(avoided_frame)
                
                if old_state_ndx is not None:
                    # old_state is visible at the frame to be avoided
                    old_state = self._states_[old_state_ndx]
                
                    if old_state is state:
                        # if we turn state into a frame-avoding state, there 
                        # can be at most one extra single-frame state that was
                        # visible in the frame to be avoided; but here, this 
                        # extra state is the state itself, so once we turned it
                        # into a frame-avoding state, it remaines the only
                        # state available to the object
                        
                        state.z_frame = new_frame
                        self._states_[:] = [state]
                        return
                
                    #### BEGIN NOTE: 2020-11-30 16:24:02
                    #if old_state.z_frame >= 0:
                        ## single-frame state that is visible at the frame to be 
                        ## avoided by state; keep it and discard everything else
                        #state.z_frame = new_frame
                        #self._states_[:] = [state, old_state]
                        #return
                        
                    #else: 
                        ## old_state is a frame-avoiding state that is visible at
                        ## frame to be avoided therefore we need to make it
                        ## a single-frame state there
                        #old_state.z_frame = avoided_frame
                        ## then turn state into a frame-avoding state visible 
                        ## anywhere but avoided_frame
                        #state.z_frame = new_frame
                        ## and keep both state and old_state
                        #self._states_[:] = [state, old_state]
                        #return
                    #### END NOTE: 2020-11-30 16:24:02
                    
                    # collapsing the above NOTE: 2020-11-30 16:24:02 - see above
                    # for justification of logic
                    if old_state.z_frame < 0:
                        old_state.z_frame = avoided_frame
                        
                    state.z_frame = new_frame
                    self._states_[:] = [state, old_state]
                    return
                
                else: # no state is visible at the avoided frame
                    # since the state is turned into a frame-avoiding state, it
                    # should take over all the other visible states elsewhere
                    state.z_frame = new_frame
                    self._states_[:] = [state]
                    return
            
        else:
            raise TypeError("new_frame expected to be an int or None; got %sinstead" % type(new_frame).__name__)
        
                
    def setState(self, state:Bunch, frame:typing.Optional[int], nFrames:typing.Optional[int]=None):
        """Sets/adds a state
        
        For Path objects, this function does nothing. To alter frame states for 
        an indivdual Path element, call setState on that specific Path element
        (Path objects implement python list API).
        
            'p[k].setState(value)'
            
        where 'p' is a Path object and 'k' is the index of the element in the 
        Path object.
        
        Parameters:
        =====================
        state: datatypes.Bunch object. Its member names must conform with the
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
            
            NOTE: the PlanarGraphics object gets a copy of the state, so that 
            the original state (which is passed by reference to this function)
            remains unchanged (this is the 'frame' parameter - see blow - is used
            to 'set' the state's z_frame)
            
            If you want to preserve the state's z_frame, call:
            
            self.setState(state, state.z_frame)
            
            If you want to set a new state for current frame, call:
            
            self.setState(state, self._currentframe_)
            
            If you want the new state to be the unique state visible in all
            available frames, call:
            
            self.setState(state)
            
        frame: int or None; optional, default is None
            Sets the z_frame value for the state
        
            ATTENTION 
            When frame is None, the given state becomes the unique state of the 
                PlanarGraphics object, with ubiquitous visibility; all 
                pre-existing states are removed.
            
            When frame < 0, the state is set to be visible in all but the frame 
                with index == -1 * frame -1. 
                
                Thus means that ALL existing states, possibly with the exception
                of the state specifically visible in frame with 
                
                index == -1 * frame -1 
                
                if it exists, are removed and replaced by a the state given as 
                argument.
                
            When frame >= 0, the state will replace any existing state that is 
                visible in the frame with index == frame, or it is appended to 
                self.states.
                
                If there is a single state where z_frame = is None, this state
                will be set to be visible in ALL but the frame with index == frame
                
        nFrames: int or None; optional, default is None
            When given, it should be >= maximum of existing z_frame values in 
            self.states (including the z_frame of the new state)
            
            When None, existing states may be re-assigned to new frame indices
                in order to avoid frame clashes (i.e., frames where more than
                one state would be visible)
        
        Side effects:
        ------------
        The self._states_ collection is checked wrt consistency of the z_frame,
        redundant states are removed and the remaining ones are sorted before
        adding or replacing the state for the specified frame.
        
        If frame is None, state becomes the unique state of the PlanarGraphics,
        with visibility in all available frames.
            
        """
        from core.utilities import index_of
        # NOTE: 2020-11-13 12:43:53 re-write
        
        if not self.__class__.validateState(state):
            warnings.warn("State %s if not valid for this PlanarGraphics %s (%s)" % (state, self.__class__.__name__, self._planar_graphics_type_))
            return
        
        #NOTE: 2020-11-13 16:02:53
        # make sure they're consistent and sorted:
        # either:
        # (I)   one ubquious state
        # (II)  one frame-avoding state and maximum a single-frame state 
        #       (visible in the avoided frame)
        # (III) any number of single-frame states
        self.checkStates()
        
        # NOTE: 2020-11-13 13:02:19
        # allow frame to override state z_frame
        new_state = Bunch(state.copy())
        
        # NOTE: 2020-11-13 16:54:10
        # set this here so that we forget about this 'frame' variable
        new_state.z_frame = frame # this can be None
        
        
        # WARNING: 2020-11-13 16:56:05
        # from here on, state.z_frame has the value passed as argument 'frame'
        # CAUTION this may be None
        
        
        # NOTE: the type of z_frame is checked by validateState(...)
        if new_state.z_frame is None: # new state is ubiquitous
            # this implicitly removes all previous states
            self._states_[:] = [new_state]
            
        else: # new state is either signle-frame or frame-avoding
            if not isinstance(self._states_, list):
                self._states_ = list()
                
            if len(self._states_) == 0: # no previous states (shouldn't happen)
                # if there is no state, add this;
                # if there already exists only one state, replace it with this.
                self._states_[:] = [new_state]
                
            elif len(self._states_) == 1: # initially, only one state
                original_state = self._states_[0]
                if new_state.z_frame >= 0: # new state is single-frame
                    if original_state.z_frame is None: # original state is ubiquitous
                        # make this visible in ALL BUT state.z_frame
                        # then append the new state
                        original_state = self._states_[0]
                        target_frame = -new_state.z_frame - 1
                        original_state.z_frame = target_frame
                        self._states_[:] = [original_state, new_state]
                        
                    elif original_state.z_frame == new_state.z_frame: # same frame as new state
                        # found a single state for the same frame =>
                        # replace it with the new state
                        self._states_[0] == new_state
                        
                    elif original_state.z_frame < 0: # original state is frame-avoding
                        originally_avoided_frame = -original_state.z_frame  - 1
                        
                        if new_state.z_frame == originally_avoided_frame:
                            # new state wants to be visible in the frame avoided
                            # by the original state => all OK, just append the 
                            # new state
                            self._states_.append(new_state)
                            
                        else: # frame clash: 
                            # the new state and the original state would be
                            # visible in the same frame as the new state, which 
                            # by design is not allowed;
                            # therefore we replicate the original state
                            # for all the frames it needs to be seen - but this
                            # requires information about how many frames are 
                            # available -- hence we need nFrames
                            #
                            
                            max_frame = max([new_state.z_frame, originally_avoided_frame])
                            
                            if isinstance(nFrames, int) and nFrames >= 1:
                                if nFrames <= max_frame:
                                    nFrames = max_frame + 1
                                    
                            else: # we don't know how mnay frames:
                                nFrames = max_frame + 1
                                
                            new_frames = [k for k in range(nFrames) if k not in (new_state.z_frame, 
                                                                                 originally_avoided_frame)]
                            
                            converted_states = list()
                            
                            for k in new_frames:
                                s = Bunch(original_state.copy())
                                s.z_frame = k
                                converted_states.append(s)
                                
                            converted_states.append(new_state)
                                
                            self._states_[:] = converted_states[:]
                                    
                    else: #both original and new states are single-frame but linked to different frames
                        # just append the new state
                        self._states_.append(new_state)
                            
                else: # new_state is frame-avoiding
                    new_avoided_frame = -new_state.z_frame - 1
                    
                    if original_state.z_frame is None: # ubiquitous original state
                        # make this state visible in the new avoided frame
                        original_state.z_frame = new_avoided_frame
                        # then prepend the new frame-avoiding state
                        self._states_.insert(0, new_state)
                        
                    elif original_state.z_frame >= 0: # original state is single-frame
                        if original_state.z_frame == new_avoided_frame: # fits in OK
                            # there is a single state visible in the avoided frame
                            # the new state wants to avoid this frame, so OK, no
                            # problem, just prepend the new state
                            self._states_.insert(0, new_state)
                            
                        else: # frames clash:
                            # since the new state wants to be visible also in this 
                            # frame, it implicitly replaces the original state
                            # (which was visible ONLY in this frame)
                            self._states_[:] = [new_state]
                            
                    else: # original_state is also frame-avoiding
                        originally_avoided_frame = -original_state.z_frame - 1
                        max_frame = max([new_avoided_frame, originally_avoided_frame])
                            
                        
                        # two possibilities:
                        if original_state.z_frame == new_state.z_frame: # both new and original avoid the same frame
                            # a) OK, then just go ahead and replace original state
                            self._states_[:] = [new_state]
                            
                        else: # new and original states avoid different frames
                            # b) we need to replicate the original state and make
                            # it visible in ALL EXCEPT the frames avoided by both
                            # the original and the new state.
                            # therefore, we also need nFrames here
                            
                            if isinstance(nFrames, int):
                                if nFrames <= max_frame:
                                    nFrames = max_frame + 1
                                    
                            else: # we don't know how many frames:
                                nFrames = max_frame + 1 # take a guess
                                
                            new_frames = [k for k in range(nFrames) if k not in (new_avoided_frame,
                                                                                 originally_avoided_frame)]
                                
                            converted_states = list()
                            
                            for k in new_frames:
                                s = Bunch(original_state.copy())
                                s.z_frame = k
                                converted_states.append(s)
                                
                            converted_frames.append(new_state)
                            
                            self._states_[:] = converted_states[:]
                            
            else: # at least two states exist:
                # either one frame-avoiding and one single-frame or
                # many single-frame states
                
                max_frame = max([s.z_frame for s in self._states_ is s.z_frame is not None])
                
                if new_state.z_frame >= 0: #  new state is single-frame
                    # check if there is a frame-avoiding state
                    frame_avoiding_states = [s for s in self._states_ if s.z_frame < 0]
                    
                    if len(frame_avoiding_states):
                        # there may be at most one other state with z_frame >= 0
                        fa_state = frame_avoiding_states[0]
                        
                        avoided_frame = -fa_state.z_frame - 1
                        
                        max_frame = max([max_frame, new_state.z_frame])
                        
                        if isinstance(nFrames, int) and nFrames <= max_frame:
                            nFrames = max_frame + 1
                            
                        if new_state.z_frame == avoided_frame:
                            # check if avoided frame already has a state
                            # but leave the frame-avoiding state in place
                            original_states = [s for s in self._states_ if s.z_frame == avoided_frame]
                            
                            if len(original_states):
                                ndx = index_of(self._states_, original_states[0],
                                               key = lambda x: x.z_frame)
                                
                                if ndx is not None:
                                    self._states_[ndx] = new_state # done
                                    
                                else:
                                    # the avoided frame did not have a state before
                                    # so keep the 
                                    self._states_.append(new_state)
                                
                            else:
                                # new state gets added;
                                # the exising frame-avoiding state gets replicated
                                # to a collction of visible states in all other
                                # frame except the frame of new_state and the
                                # previously avoided
                                
                                new_frames = [k for k in range(max_frame) if k not in (new_state.z_frame,
                                                                                       avoided_frame)]
                                
                                converted_states = list()
                                for k in new_frames:
                                    s = Bunch(fa_state.copy())
                                    s.z_frame = k
                                    converted_states.append(s)
                                    
                                converted_states.append(new_state)
                                self._states_[:] = converted_states[:]
                            
                        else: # frame clash
                            # fa_state is set to be visible in the same frame as
                            # that of the new state; 
                            # therefore we need to replicate fa_state to a set 
                            # of states visible everywhere except the avoided 
                            # frame and the new_state.z_frame
                            # - and we need nFrames for this
                            
                            new_frames = [k for k in range(nFrames) if k not in (avoided_frame, 
                                                                                 new_state.z_frame)]
                            
                            
                            converted_states = list()

                            for k in new_frames:
                                s = Bunch(fa_state.copy())
                                s.z_frame = k
                                converted_states.append(s)
                                
                            converted_states.append(new_state)
                            
                            self._states_[:] = converted_states[:]
                            
                    else: # no frame-avoiding states - this should be easy
                        states_for_frame = [s for s in self._states_ is s.z_frame == new_state.z_frame]
                        
                        if len(states_for_frame):
                            ndx = index_of(self._states_, states_for_frame[0], key = lambda x: x.z_frame)
                            
                            if ndx is None:
                                self._states_.append(new_state)
                                
                            else:
                                self._states_[ndx] = new_state
                                
                        else:
                            self._states_.append(new_state)
                        
        
                else: # new state is frame-avoiding
                    # there may or may not be a signle-frame state for this avoided 
                    # frame, but it doesn't matter
                    new_avoided_frame = -new_state.z_frame -1
                    # check if there is another frame-avoiding state
                    fa_states = [s for s in self._states_ if s.z_frame < 0]
                    
                    if len(fa_states):
                        fa_state = fa_states[0]
                        
                        if new_state.z_frame == fa_state.z_frame: #just replace this one
                            ndx = index_of(self._states_, fa_state,
                                           key = lambda x: x.z_frame)
                            
                            if ndx is not None:
                                self._states_[ndx] = new_state
                                
                            else: # theoretically this is never reached
                                self._states_.append(new_frame)
                                
                        else:
                            s = Bunch(fa_state.copy())
                            s.z_frame = new_avoided_frame
                            self._states_[:] = [new_state, s]
                        
                    else:
                        states_for_avoided_frame = [s for s in self._states_ if s.z_frame == new_avoided_frame]
                        if len(states_for_avoided_frame):
                            s = states_for_avoided_frame[0]
                            self._states_[:] = [new_state, s]
                            
                        else:
                            self._states_[:] = [new_state]
                                
        self.checkStates()
        
    def objectForFrame(self, frame:typing.Optional[int]=None,
                       visible:typing.Optional[bool]=True) -> typing.Optional[object]:
        """Returns a new PlanarGraphics with frame-specific descriptors.
        
        In contrast with getState(frame) which returns the Bunch state object
        for the specified frame, this function constructs a new PlanarGraphics 
        object of same type as self, with a single state identical to the one 
        returned by getState().
        
        WARNING: The function returns a NEW object (not a reference to the 
        current one); hence any modifications to its descriptor values will NOT
        be reflected in the original.
        
        This is useful, e.g., for displaying a frame-specific PlanarGraphics 
        object cache, instead of the original object.
        """
        state = self.getState(frame, visible=visible)
        if state:
            ret = self.__class__(state)
            # NOTE: 2022-01-10 14:49:16# the below is REQUIRED because state may
            # be frame-specific
            ret.currentFrame = self.currentFrame 
            return ret
    
    @staticmethod
    def getCurveLength(obj, prev=None):
        """Static version of PlanarGraphics.curveLength()
        Useful to apply it to a state, or a sequence of states (instead of PlanarGraphics)
        TODO/FIXME 2024-08-22 10:08:40
        Rewrite to harmonize with the instance method curveLength()
        Parameters:
        ==========
        obj: 
            Either a datatypes.Bunch: the state of an elementary PlanarGraphics or a sequence
            of states of a Path.
            
            The function supports only states for Move, Line, Cubic, and Quad
            
            Or: a sequence (typle, list) of state Bunch (such as those from a Path)
            
            In either case, these are typically obtained by calling PlanarGraphics.getState()
            or Path.getState().
        
        prev: None (default) or a datatypes.Bunch: state of an elementary PlanarGraphics
            e.g., as returned by PlanarGraphics.getState()
            
        NOTE: the function cannot distinguish between states belonging to a Move and
        those belonging to a Line (they have the same planar descriptors). As a workaround
        call this function by passing the same state for obj and prev.
        
        WARNING: For a sequence of states, the function assumes the first state belongs
            to a Move PlanarGraphics.
        
        """
        from scipy import interpolate, spatial
        import core.datatypes  
        
        if prev is None:
            x0 = y0 = 0.
            
        elif isinstance(prev, Bunch):
            if not any([p in prev for p in ("x", "y", "cx", "cy", "c1x", "c1y", "c2x", "c2y", "z_frame")]):
                raise TypeError("Incompatible data for prev")
            
            x0 = prev.x
            y0 = prev.y
            
        else:
            raise TypeError("prev expected to be a datatypes.Bunch compatible with a PlanarGraphics, or None; got %s instead" % type(prev).__name__)
        
        
        if isinstance(obj, Bunch):
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
            if not all([isinstance(o, Bunch) for o in obj]):
                raise TypeError("The sequence must contain datatypes.Bunch objects")
            
            if any([not any([p in o for p in ("x", "y", "cx", "cy", "c1x", "c1y", "c2x", "c2y", "z_frame")]) for o in obj]):
                raise TypeError("The sequence contains incompatible datatypes.Bunch objects")
                
            element_curve_lengths = [curveLength(obj[0], prev=obj[0])]
            
            element_curve_lengths += [curveLength(o, obj[k-1]) for k, o in enumerate(obj)]
            
            return np.sum(element_curve_lengths), element_curve_lengths
        
        else:
            return 0
        
    def curveLength(self, prev=None, full:bool=False):
        """Calculates the length of the curve represented by this PlanarGraphics.
        Here, 'curve' has the general meaning of a 1D function y = f(x)
        
        Parameters:
        ==========
        prev: a PlanarGraphics or None (default): the PlanarGraphics point (NOT
            a Path, Elipse, or Rect) relative to which the curve length is
            calculated. This is because PlanarGraphics primitives like Arc, ArcMove,
            Line, Cubic and Quad are specified using destination points (or 
            bounding rectangles); not used for closed primitves like Rect or Ellipse.
            
            Ignored for Path PlanarGraphics, but mandatory for the other supported
            PlanarGraphics subclasses (currently, Move, Line, Cubic, Quad).
            
            For PlanarGraphics except Path, Rect, Ellipse, when `prev` is None, 
                the curveLength will be calculated relative to a Move(0., 0.).
        
        full: bool, default is False; when True, also returns the Encildean distance
            of the `prev`, but only for Line objects (FIXME - do we need this at all 
            and if so, why just for Lines?)
        
        Returns:
        =======
        A scalar (when full is False, the default) or a scalar and an array 
        (when full is True and this object is a Line):
        
        For Move: 0.
        
        For Line: the Euclidean distance between this element's (x,y) coordinates
                and (if `full` is True) those of the previous element in "prev"
                    
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
            return 0
        
        elif isinstance(self, Path):
            path = self.objectForFrame(self.currentFrame)
            
            # NOTE: a Path always starts with a Move, which has curveLength 0
            element_curve_lengths = [path[0].curveLength()]
            
            element_curve_lengths += [p.curveLength(path[k-1]) for k, p in enumerate(path) if k > 0]
            
            return np.sum(element_curve_lengths)
        
        else:
            if prev is None:
                prev = Move(0., 0.)
        
            if isinstance(self, Line):
                if prev is None:
                    prev = Move(0., 0.)
                return spatial.distance.euclidean([self.x, self.y], 
                                                  [prev.x, prev.y])
            
            elif isinstance(self, Cubic):
                # parametric spline: (x,y) = f(u)
                self_xy = np.array([self.x, self.y])
                prev_xy = np.array([prev.x, prev.y])
                
                dx_dy = self_xy - prev_xy                       # prepare to "shift" the rectified spline
                                                                # so that it starts at the previous point
                
                t = np.zeros((8,))
                t[4:] = 1.
                
                # NOTE: in Qt a cubic is a Bezier with 4 control points:
                # `start` (here this is `prev`)
                # cp 1
                # cp 2
                # `end` (here is the point at self.x, self.y)
                
                c = np.array([[prev.x, prev.y],
                              [self.c1x, self.c1y],
                              [self.c2x, self.c2y], 
                              [self.x, self.y]])
                
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

                dx_dy = self_xy - prev_xy                       # prepare to "shift" the rectified spline
                                                                # so that it starts at the previous point
                
                t = np.zeros((6,))
                t[3:] = 1.
                
                c = np.array([[prev.x, prev.y],
                              [self.cx, self.cy],
                              [self.x, self.y]])
                
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
            
            elif isinstance(self, Rect):
                return 2*self.w + 2*self.h
            
            elif isinstance(self, Ellipse):
                # approximates circumference using the ellipe function
                # (complete elliptic integral of the 2ⁿᵈ kind)
                a = self.w/2
                b = self.h/2
                
                a,b = max(a,b), min(a,b)    # just to avoid e_sq < 0, not that it would make a diference, numerically
                
                e_sq = 1. - b**2 / a**2     # eccentricity squared
                
                return 4 * a * scipy.special.ellipe(e_sq)
            
            elif isinstance(self, Arc):
                # BUG 2024-08-21 23:10:24 FIXME
                # incorrect x and y for Arc
                pr = spatial.distance.euclidean([self.x, self.y], [prev.x, prev.y])
                return self.l + pr # sweep length parameter for QPainterPath.arcTo()
                
            elif isinstance(self, ArcMove):
                return 0    # (as for Move)
                
            
            else:
                raise NotImplementedError("Function is not implemented for %s PlanarGraphics" % self.type)
            
    def interpolate(self, n:int, prev=None):
        """Interpolated coordinates for n points on the 'curve' of this object
        """
        
        if not isinstance(n, int):
            raise TypeError(f"Number of points must be an int; instead, got {type(n).__name__}")
        
        if n <= 1:
            raise ValueError(f"Cannot interpolate for less than two points ({n})!")
        
        if isinstance(self, Move):
            # does not make sense; just return the coordinates
            return self.x, self.y
        
        elif isinstance(self, Line):
            if prev is None:
                prev = Move(0., 0.)
                
            x = [prev.x, self.x]
            y = [prev.y, self.y]
            
            newX = np.linspace(x[0], x[-1], n)
            newY = np.interp(newX, x, y)
            
            return newX, newY
        
        elif isinstance(self, Cubic):
            # NOTE: 2024-08-22 13:18:33
            # self.x, self.y are the coordnates of the destination (last) point 
            # on the cubic, NOT its start; the start is prev.x prev.y!
            if prev is None:
                prev = Move(0., 0.)
            self_xy = np.array([self.x, self.y])
            prev_xy = np.array([prev.x, prev.y])

            t = np.zeros((8,))
            t[4:] = 1.
            
            c = np.array([[prev.x, prev.y],
                            [self.c1x, self.c1y],
                            [self.c2x, self.c2y], 
                            [self.x, self.y]])
            
            spline = interpolate.BSpline(t, c, 3, extrapolate=True)
            
            #  NOTE: 2024-08-22 13:53:16
            # interpolation on splines is done on NORMALIZED x coordinates where
            # 0 → `start` of the curve
            # 1 → `end` of the curve 
            # ⟹ an interpolating base [0..1] includes both curve ends
            
            
        elif isinstance(self, Quad):
            scipywarn("Quads do not suport interpolation yet")
            return self.x, self.y
        
        elif isinstance(self, (Ellipse, Rect, Arc, ArcMove)):
            scipywarn(f"{type(self).__name__} does not support interpolation yet")
            return self.x, self.y
        
        elif isinstance(self, Path):
            pass
            
            

    @property
    def isLinked(self):
        return len(self._linked_objects_) > 0
    
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
        
    def unlink(self):
        self.clearObjectLinks()
        
    def linkFrames(self, value):
        """Associates planar descriptor state values to frame indices.
        
        A planar descriptor state (datatypes.Bunch) can be:
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
        states = self._currentstates_
        for s in states:
            states.z_frame = None
        self._states_[:] = states[:]
        
    def propagateState(self, state, destframes):
        """Creates copies of "state" to all frames in destframes.
        TODO
        States linked to frames in destframes will be replaced with copies of 
        "state".
        
        Parameters:
        ==========
        state: Bunch - a state present in this object's states list
        
        destframes: a sequence of int, or None: frame indices where state is to 
                    be propagated
        
            If None, or empty, "state" will become a single, frameless state (i.e.
                present in all available data frames for the object)
        
        """
        if state not in self._states_:
            raise ValueError ("State %s not found" % state)
        
        
        if isinstance(destframes, (tuple, list)):
            if len(destframes):
                if not all([isinstance(f, int) for f in destframes]):
                    raise TypeError("destframes must contain only int values")
                
                #if any([f not in target_frame_indices for f in destframes]):
                    #raise ValueError("destframes contains frames indices not found in this object")
                
                if len(set(destframes)) < len(destframes):
                    raise ValueError("destframes must not contain duplicate values")
                
                for f in destframes:
                    target_state = target_states[target_frame_indices.index(f)]
                    
                    self._states_.remove(target_state)
                    self._states_.append(Bunch(state.copy()))
                    
            else: # empty destframes
                # use this state as a single state to all frames
                state.z_frame = None
                self._states_[:] = [state]
                
        elif destframes is None:
            state.z_frame = None
            self._states_[:] = [state]
            
        else:
            raise TypeError("destframes expected to be a (possibly empty) sequence opfr frame idnices, or None; got %s instead" % type(destframes).__name__)
            
                
        #if setcurrent:
            #self._currentframe_ = srcframe
                    
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
                state.z_frame = newmap[state.z_frame] # this should also affect self._currentstates_ (which is a reference)
                
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
        import math
        return sorted([s.z_frame for s in self._states_], 
                        key = lambda x: x if x is not None else -math.inf) # this may be an empty list
        
    @property
    def frameIndices(self):
        """A list of frame indices for the PlanarGraphics state.
        
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
        
        A planar graphics descriptor state is a datatypes.Bunch with its members
        being the planar descriptors specific to the concrete subclass. The values 
        of the planar descriptors are either common to all possible frames of a 3D 
        data array where the PlanarGraphics object would be used, or specific to 
        particular frame indices, if the object has frame-state associations.
        
        A frame-state association is a dictionary that maps frame indices (int)
        as keys, to descriptor states (datatypes.Bunch) as values.
        
        """
        
        return [s.z_frame for s in self._states_]
        
    @frameIndices.setter
    def frameIndices(self, values:typing.Optional[typing.Iterable]):
        """FIXME Re-assigns the z_frame values in existing states.
        
        Parameters:
        ===========
        values: The type of this parameter is one of the following:
        
            1) None
            
            2) a single int
            
            3) an iterable (e.g. tuple, list, range) with may:
            3.a) be empty;
            3.b) contain a single None element;
            3.c) contain int elements such that:
            3.c.1) all are >= 0, OR:
            3.c.2) it has one element < 0 and at most one other element >= 0
            
            4) a dict with int keys mapped to int values 
                (remaps old z_frame values to new z_frame values)
            
            The application of the new frame indices is subject to the three 
            rules (see the class documentation)
                    
        dict mapping old_frame to new_frame (all numeric scalars)
        
            The keys (old frame indices) select which state will get a new values 
            for its z_frame parameter.
            
        Effects:
        ========
        
        1) When value is None, an empty iterable, or an iterable with a single
         None element: 
         
            * the current state is set to be ubiquitous; all other states are
            discarded.
            
            * if the current state was previously invisible 
                (i.e., z_frame == -1 * current_frame - 1)
                then it will become visible
        
        2) When value is an int, or an interable with a single int element:
            
            if value  < 0 then the current state is set to be frame-avoiding,
                visible in ALL frames EXCEPT the frame index -value - 1
                
            if value >= 0 then the current state is set to be single-frame, 
                visible at frame index given by value
            
        
        This may remove states, or duplicate states.
            
        NOTE: 2020-11-02 08:54:48
        The parameters 'values' must be an iterable and should ideally have 
        (or yield) as many elements as there are states in the PlanarGraphics.
        
        If 'values' resolves to more frame indices than states, only the first
        len(states) indices are used.
        
        If 'values' supplies less than len(states) indices, then only the first
        len(values) states are affected.
        
        If there are NO frame-associated states (i.e. there is only one frame)
        the function does nothing.
        
        Raises an error if any of the following situation arises:
        
        1) "values" parameter indicates more frame indices than the number of
        currently defined states.
        
        2) the "new" frame indices in "values" result in duplication of z_frame
        among existing states
        
        
        """
        if isinstance(self, Path): # FIXME: this won't be reached because the method is overridden in Path
            for o in self._objects_:
                o.frameIndices = value
                
            return
        
        if values is None or ((isinstance(values, (tuple, list, range)) and (len(values)==0 ))): # trivial
            # copy whatever state is visible at the current frame index,
            # make it ubiquitous and dump the others
            state = self.getState(visible=True) # get visible state for current frame
            state.z_frame = None    # and make it ubiquitous
            self._states_[:] = [state]
                
            return 
        
        elif isinstance(values, (tuple, list, range)):
            # a sequence of frames was specified; these are the specific frame
            # indices where the object is to be visible (drawn)
            if not all([isinstance(f, int) for f in values]):
                # check for int types
                raise TypeError("new frame indices expected to be a sequence of int, or a dictionary with int keys; got %s instead" % values)

            if any([f < 0 for f in values]):
                # check for valid values
                raise ValueError("new frame indices must be >= 0")
            
            if len(set(values)) < len(values):
                # check for uniqueness
                raise ValueError("duplicate new frame indices are not allowed")
                
            if len(self._states_) == 1:
                # currently, there is a single state => duplicate it and make
                # the duplicates frame-specific for the indices in value;
                # dump the rest; 
                # NOTE: 2022-01-09 21:52:51
                # if current state is already frame-specific for current
                # frame don't duplicate, but use directly in the new list
                state = self._states_[0]
                if state.z_frame is None or state.z_frame not in values:
                    new_states = list()
                    
                    # generate new states for the frames: a copy of the initial
                    # ubiquitous state, for each frame index in value
                    for f in values: 
                        s = Bunch(state.copy())
                        s.z_frame = f
                        new_states.append(s)
                        
                    self._states_[:] = sorted(new_states, key = lambda x: x.z_frame)
                    
                else:  
                    # see NOTE: 2022-01-09 21:52:51
                    new_frame_values = [f for f in values if f != state.z_frame]
                    # we then replicate this state for ALL OTHER frames
                    
                    new_states = list()
                    new_states.append(state)
                    
                    for f in new_frame_values: 
                        # loop does nothing if new_frame_values is empty 
                        # => avoid duplication
                        s = Bunch(state.copy()    )
                        s.z_frame = f
                        new_states_.append(s)
                    
                    self._states_[:] = sorted(new_states, key = lambda x: x.z_frame)
                         
                return
                            
            else: 
                # case with several states
                # NOTE: 2022-01-09 21:46:32
                # copy whatever states are, or would be, visible at the frame
                # indices in value, make then frame index-specific, then
                # dump the others
                new_states = list()
                for f in values:
                    s = self.getState(f, visible=True)
                    if s:
                        ss = Bunch(s.copy())
                        ss.z_frame = f
                        new_states.append(ss)
                    
                self._states_[:] = sorted(new_states, key=lambda x: x.z_frame)
                
                return
            
        elif isinstance(values, dict):  
            # NOTE 2022-01-09 21:54:30: using a mapping
            # except for skip keys that do not point to a frame index with a visible frame
            if not all([isinstance(f, int) for f in values]): 
                # check for int types of keys
                raise TypeError("new frame indices expected to be a sequence of int, or a dictionary with int keys; got %s instead" % values)

            if not all([isinstance(f, int) for f in values.values()]):
                # check for int types of values
                raise TypeError("new frame indices expected to be a sequence of int, or a dictionary with int keys; got %s instead" % values)

            if len(set(values.values())) < len(values):
                # check that new frame indices (values) are unique)
                # NOTE this beign a dict, its keys are guaranteed to be unique
                raise ValueError("duplicate new frame indices are not allowed") 
                
            #if any([f < 0 for f in values]):
                ## check that old frame indices (keys) are valid
                #raise ValueError("new frame indices must be >= 0")
                
            new_specifics = [f for f in values.values() if f >= 0]
            new_avoiders = [f for f in values.values() if f < 0]
            if len(new_avoiders) > 1:
                raise ValueError("Cannot have more than one frame-avoiding state")
            
            if len(new_avoiders) == 1:
                fa_new = new_avoiders[0]
                if any (f == -fa_new-1 for f in new_specifics):
                    raise ValueError(f"New frame-avoiding index {fa} clashes with a frame-specific index in {new_specifics}")
                
            old_avoiders = [f for f in values if f < 0]
            if len(old_avoiders):
                if len(old_avoiders) > 1:
                    raise ValueError("Cannot expect more than one frame-avoiding states in the current states")
            
                #fa_old = old_avoiders[0]
                #if any(f == -fa_old-1 for f in new_avoiders):
                    #raise ValueError(f"New frame index for an old avoider at {fa_old} clashes with new frame indices {[f for f in values.values()]}")
                
            new_states = list()
            
            if len(self._states_) == 1: 
                # NOTE: 2022-01-09 22:04:25
                # bypass checks for visibility: the unique state may be frame-avoiding
                # but then we don't care here
                state = self._states_[0]
                for v in values.values():
                    s = Bunch(state.copy())
                    s.z_frame = v
                    new_states.append(s)
                    
            else:
                # cache states checked in NEITHER values' old indices, nor new
                # indices
                cached_states = list(s for s in self._states_ if s.z_frame not in values and s.z_frame not in values.values())
                new_states.extend(cached_states)
                for k, v in values.items():
                    if k < 0:
                        fa_state = list(s for s in self._states_ if s.z_frame == k)
                        if len(fa_state):
                            fa_state = fa_state[0]
                            s = Bunch(fa_state.copy())
                            s.z_frame = v
                            new_states.append(s)
                        
                    else:
                        state = self.getState(k, visible=True)
                        if state:
                            s = Bunch(state.copy())
                            s.z_frame = v
                            new_states.append(s)
                            
                self._states_[:] = sorted(new_states, key = lambda x: x.z_frame)
                    
        elif isinstance(values, int): 
            new_states = list()
            cached_states = list(s for s in self._states_ if s.z_frame not in values and s.z_frame not in values.values())
            new_states.extend(cached_states)
            current_state = self.getState(visible=False)
            if current_state:
                s = Bunch(current_state.copy())
                s.z_frame = values
                new_states.append(s)
            
            if len(new_states):
                self._states_[:] = sorted(new_states, key = lambda x: x.z_frame)
                
        else:
            raise TypeError("Expecting an int, a possibly empty iterable (tupe, list, range) of int, a possibly empty dict ({int keys -> int values}) or just None; got %s instead" % type(values).__name__)

    @property
    def type(self):
        return self._planar_graphics_type_
    
    @property
    def type_name(self):
        return self._planar_graphics_type_.name
        
    @property
    def frontends(self):
        """A list of GraphicsObject front ends.
        This property is read-only, but its value (a list) is mutable..
        """
        return self._frontends_
    
    @property
    def x(self) -> numbers.Number:
        state = self.currentState
        if state:
            return state.x if "x" in self.shapeDescriptors else self().boundingRect().x()
    
    @x.setter
    def x(self, val:numbers.Number):
        state = self.currentState
        if state:
            x_ = state.x if "x" in self.shapeDescriptors else self().boundingRect().x()
            dx = val - x_
            self.translate(dx, type(dx)(0))
            
    
        
    @property
    def y(self) -> numbers.Number:
        state = self.currentState
        if state:
            return state.y if "y" in self.shapeDescriptors else self().boundingRect().y()
        
    @y.setter
    def y(self, val:numbers.Number):
        state = self.currentState
        if state:
            y_ = state.y if "y" in self.shapeDescriptors else self().boundingRect().y()
            dy = val - y_
            self.translate(type(dy)(0), dy)

    #@frontend.setter
    #"def" frontends(self, value):
        ## TODO/FIXME make sure this object is the _backend_ of value
        #if isinstance(value, GraphicsObject) and value.isGeometricShape:
            #if value._backend_ == self:
                #self._frontend=value
                
    def toHDF5(self, group, name, oname, compression, chunks, track_order,
                       entity_cache):
        import h5py
        from iolib import h5io, jsonio
        
        cached_entity = h5io.getCachedEntity(entity_cache, self)
        
        if isinstance(cached_entity, h5py.Group):
            group[target_name] = cached_entity
            return cached_entity
        
        target_name, obj_attrs = h5io.makeObjAttrs(self, oname=oname)
        if isinstance(name, str) and len(name.strip()):
            target_name = name
        
        entity = group.create_group(target_name)
        h5io.storeEntityInCache(entity_cache, self, entity)
        entity.attrs.update(obj_attrs)
        entity.attrs.update({"__graphics_type_name__": self.type_name})
                
        if isinstance(self, Path):
            for k, o in enumerate(self):
                o_name = f"{k}_{type(o).__name__}"
                o.toHDF5(entity, o_name, o.name, compression, chunks, track_order, entity_cache)
                
            return entity
                
        entity.attr.update({"__graphics_descriptors__": h5io.make_attr(self.descriptors)})
        
        # NOTE: 2021-11-25 09:59:42
        # do NOT use the generic h5io.toHDF5 here, although states is
        # a list; thisns because we don't want to deeply nest the states' databags
        # as HDF5 Group objects; see NOTE: 2021-11-25 10:04:00 below
        #states_group = h5io.toHDF5(self.states, "states", self.name,
                                             #compression, chunbks, track_order,
                                             #entity_cache)
        
        # NOTE: 2021-11-25 10:04:00
        # make a HDF5 Group for the states list, then
        # for each state in the states list create an empty HDF5 Dataset, then
        # store the descriptor name/value pairs of the state as Dataset attrs
        states_group = entity.create_group("states")
        #h5io.storeEntityInCache(entity_cache, self.states, states_group)
        
        for k, state in enumerate(self.states):
            state_dset = states_group.create_dataset(f"state_{k}")
            state_dset.attrs.update(h5io.make_attr_dict(**state))
            
        return entity
        
        
class Cursor(PlanarGraphics):
    """Encapsulates the coordinates of a cursor:
    
    x, y, width, height, xwindow, ywindow, radius
    
    
    see Cursor.__init__() documentation for details
    
    """
    
    _planar_descriptors_ = ("x", "y", "width", "height", "xwindow", "ywindow", "radius")

    #_planar_descriptors_ = ("x", "y", "width", "height", "xwindow", "ywindow", "radius", "z_frame")
    
    _planar_graphics_type_ = PlanarGraphicsType.vertical_cursor
    
    qt_path_composition_call = None
    
    _default_label_ = "cr"

    def __init__(self, *args, name=None, frameindex=[], currentframe=0, 
                 graphicstype=PlanarGraphicsType.crosshair_cursor, closed=False,
                 linked_objects=dict()):
        """
        Variadic parameters:
        ====================
        x, y:               scalars, cursor position (in pixels) - coordinates 
                            are in the image space; this associates a coordinate
                            system with origin (0,0) at top left
        
        width, height:      scalars, size of cursor main axis (in pixels) or 
                            None 
        
        xwindow, ywindow:   scalars, size of cursor's window 
        
        radius:             scalar, cursor radius (for point cursors) 

        Keyword parameters:
        ===================
        These are common to all PlanarGraphics objects.
        
        name:               (optional, default is None) str, this cursor's name
                            When None, or an empty string, the cursor's name (or 
                            ID) will be the first letter of the :class: name
                            
        
        
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
            
    @abstractmethod
    def __call__(self, path:typing.Optional[QtGui.QPainterPath]=None, 
                frame:typing.Optional[int]=None, closed:typing.Optional[bool]=None,
                connected:typing.Optional[bool]=False) -> QtGui.QPainterPath:
        """Returns a QtGui.QPainterPath object. 
        In contrast with the other PlanarGraphics, 'closed' and 'connected'
        parameters are ignored here
        """
        if path is None:
            path = QtGui.QPainterPath()
        
        state = self.getState(frame)
        
        if state: # and len(state):
            if self.type is PlanarGraphicsType.vertical_cursor:
                path.addRect(QtCore.QRectF(state.x - state.xwindow/2, 0, 
                                           state.xwindow, state.height))
                    
            elif self.type is PlanarGraphicsType.crosshair_cursor:
                path.addRect(QtCore.QRectF(state.x - state.xwindow/2, 0, 
                                           state.xwindow, state.height))
                
                path.addRect(QtCore.QRectF(0, state.y - state.ywindow/2, 
                                           state.width, state.ywindow))
                
            elif self.type is PlanarGraphicsType.horizontal_cursor:
                path.addRect(QtCore.QRectF(0, state.y - state.ywindow/2, 
                                           state.width, state.ywindow))
                
            elif self.type is PlanarGraphicsType.point_cursor:
                path.addRect(QtCore.QRectF(state.x - state.xwindow/2, 
                                           state.y - state.ywindow/2, 
                                           state.xwindow, state.ywindow))
        return path
    
    def map_to_pc_on_path(self, other, path):
        x = int(self.x)
        
        if x < 0:
            # NOTE FIXME what to do here?
            return
        
        cPath = path.objectForFrame()
        
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

class VerticalCursor(Cursor):
    _planar_graphics_type_ = PlanarGraphicsType.vertical_cursor
    
    _default_label_ = "vc"
   
    def __init__(self, *args, name=None, frameindex=[], currentframe=0, 
                 linked_objects=dict(), **kwargs):
        super().__init__(*args, name=name, frameindex=frameindex, 
                         currentframe=currentframe, 
                         graphicstype=PlanarGraphicsType.vertical_cursor, 
                         closed=True, 
                         linked_objects=linked_objects)
        
    def __call__(self, path:typing.Optional[QtGui.QPainterPath]=None, 
                frame:typing.Optional[int]=None, closed:typing.Optional[bool]=None,
                connected:typing.Optional[bool]=False) -> QtGui.QPainterPath:
        """Returns a QtGui.QPainterPath object. 
        In contrast with the other PlanarGraphics, 'closed' and 'connected'
        parameters are ignored here
        """
        if path is None:
            path = QtGui.QPainterPath()
        
        state = self.getState(frame)
        
        if state: # and len(state):
            path.addRect(QtCore.QRectF(state.x - state.xwindow/2, 0, 
                                       state.xwindow, state.height))
        return path
        
class HorizontalCursor(Cursor):
    _planar_graphics_type_ = PlanarGraphicsType.horizontal_cursor

    _default_label_ = "hc"
   
    def __init__(self, *args, name=None, frameindex=[], currentframe=0, 
                 linked_objects=dict(), **kwargs):
        super().__init__(*args, name=name, frameindex=frameindex, 
                         currentframe=currentframe, 
                         graphicstype=PlanarGraphicsType.horizontal_cursor, 
                         closed=True, 
                         linked_objects=linked_objects)
        
    def __call__(self, path:typing.Optional[QtGui.QPainterPath]=None, 
                frame:typing.Optional[int]=None, closed:typing.Optional[bool]=None,
                connected:typing.Optional[bool]=False) -> QtGui.QPainterPath:
        """Returns a QtGui.QPainterPath object. 
        In contrast with the other PlanarGraphics, 'closed' and 'connected'
        parameters are ignored here
        """
        if path is None:
            path = QtGui.QPainterPath()
        
        state = self.getState(frame)
        
        if state: # and len(state):
            path.addRect(QtCore.QRectF(0, state.y - state.ywindow/2, 
                                       state.width, state.ywindow))
        
        return path
        
class CrosshairCursor(Cursor):
    _planar_graphics_type_ = PlanarGraphicsType.crosshair_cursor
    
    _default_label_ = "cc"
   
    def __init__(self, *args, name=None, frameindex=[], currentframe=0, 
                 linked_objects=dict(), **kwargs):
        super().__init__(*args, name=name, frameindex=frameindex, 
                         currentframe=currentframe, 
                         graphicstype=PlanarGraphicsType.crosshair_cursor, 
                         closed=True, 
                         linked_objects=linked_objects)

    def __call__(self, path:typing.Optional[QtGui.QPainterPath]=None, 
                frame:typing.Optional[int]=None, closed:typing.Optional[bool]=None,
                connected:typing.Optional[bool]=False) -> QtGui.QPainterPath:
        """Returns a QtGui.QPainterPath object. 
        In contrast with the other PlanarGraphics, 'closed' and 'connected'
        parameters are ignored here
        """
        if path is None:
            path = QtGui.QPainterPath()
        
        state = self.getState(frame)
        
        if state: # and len(state):
            path.addRect(QtCore.QRectF(state.x - state.xwindow/2, 0, 
                                       state.xwindow, state.height))
            path.addRect(QtCore.QRectF(0, state.y - state.ywindow/2, 
                                       state.width, state.ywindow))
        
        return path
        
class PointCursor(Cursor):
    _planar_graphics_type_ = PlanarGraphicsType.point_cursor
   
    _default_label_ = "pc"
   
    def __init__(self, *args, name=None, frameindex=[], currentframe=0, 
                 linked_objects=dict(), **kwargs):
        
        if not isinstance(name, str) or len(name.strip()) == 0:
            name = "pc"
        
        super().__init__(*args, name=name, frameindex=frameindex, 
                         currentframe=currentframe, 
                         graphicstype=PlanarGraphicsType.point_cursor, 
                         closed=True, 
                         linked_objects=linked_objects)
        
    def __call__(self, path:typing.Optional[QtGui.QPainterPath]=None, 
                frame:typing.Optional[int]=None, closed:typing.Optional[bool]=None,
                connected:typing.Optional[bool]=False) -> QtGui.QPainterPath:
        """Returns a QtGui.QPainterPath object. 
        In contrast with the other PlanarGraphics, 'closed' and 'connected'
        parameters are ignored here
        """
        if path is None:
            path = QtGui.QPainterPath()
        
        state = self.getState(frame)

        if state: # and len(state):
            path.addRect(QtCore.QRectF(state.x - state.xwindow/2, 
                                       state.y - state.ywindow/2, 
                                       state.xwindow, 
                                       state.ywindow))
        
        return path
        
class Arc(PlanarGraphics):
    """Encapsulates parameters for QPainterPath.arcTo() function.
        This is not an arc of a circle unless the bounding rectangle is a square.
    
    x, y, w, h: the bounding rectangle;
    
    s and l: specify the start angle and the sweep length, respectively.
    
    z_frame: if present, the data frame where this PlanarGraphics is present
    
    See documentation for QPainterPath.arcTo() function.
    
    When present at the beginning of a path, it ALWAYS starts at (0.0, 0.0). 
    
    Otherwise, its origin is the previous PlanarGraphics
    object (Move, Line, CubicCurve or QuadCurve element).
    """
    _planar_descriptors_ = ("x", "y", "w", "h", "s", "l")
    
    #_planar_descriptors_ = ("x", "y", "w", "h", "s", "l", "z_frame")
    
    _planar_graphics_type_ = PlanarGraphicsType.arc
    
    qt_path_composition_call = "arcTo"
    
    _default_label_ = "a"
    
    def __init__(self, *args, name=None, frameindex=[], currentframe=0, graphicstype=None, 
                 closed=False, linked_objects=dict()):
        """
        Positional parameters:
        =======================
        x, y, w, h = bounding rectangle (top left (x, y) width and height)
        
        s = start angle (degrees, positive is CCW; negative is CW)
        
        l = sweep length (angle in degrees, positive is CCW; negative is CW)
        
        z_frame = (when present) the data frame where this PlanarGraphics is visible
    
        """
        super().__init__(*args, name=name, frameindex=frameindex, currentframe=currentframe, 
                         graphicstype=PlanarGraphicsType.arc, closed=closed, linked_objects=linked_objects)
        
    def controlPoints(self, frame:typing.Optional[int] = None, inPath:bool=False):
        """Returns the control points for this Arc, as a tuple.
        
        To be used for graphical manipulation of the arc.
        Overrides PlanarGraphics.controlPoints(…)
        
        The control points are given as (x,y) pairs or Cartesian coordinates
        with the major axis of the arc's ellipse having a 0 angle, in the 
        following order:
        
        cp0: the origin of the enclosing rectangle (Move to)
        
        cp1: starting point of the arc (line to)
        
        cp2: the centre of the arc's ellipse (and enclosing rectangle) (line to)
        
        cp3: the end point of the arc (line to)
        
        """
        state = self.getState(frame)
            
        if state is None: # or len(state) == 0:
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
        
        if inPath:
            return (cp1, cp2, cp3)
        
        return (cp0, cp1, cp2, cp3)
    
    def controlPath(self, frame:typing.Optional[int] = None, inPath:bool=False):
        """Returns the control points for this Arc, as a Path object
        
        To be used for graphical manipulation of the arc.
        Overrides PlanarGraphics.controlPath(…)
        
        The control points are given as (x,y) pairs or Cartesian coordinates
        with the major axis of the arc's ellipse having a 0 angle, in the 
        following order:
        
        cp0: the origin of the enclosing rectangle (Move to)
        
        cp1: starting point of the arc (line to)
        
        cp2: the centre of the arc's ellipse (and enclosing rectangle) (line to)
        
        cp3: the end point of the arc (line to)
        
        """
        
        ret = Path()
        
        cp = self.controlPoints(frame, inPath)
        
        for k, p in enumerate(cp):
            if k == 0:
                ret.append(Move(p[0],p[1]))
            
            else:
                ret.append(Line(cp[k-1][0], cp[k-1][1], p[0], p[1]))
        
        return ret
    
    def fromControlPath(self, path:Path, frame:typing.Optional[int]=None):
        """Overrides PlanarGraphics.fromControlPath(…)"""
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
            
        if state is None: # or len(state) == 0:
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
        
    def qGraphicsItem(self, frame:typing.Optional[int]=None) -> typing.Optional[QtWidgets.QGraphicsItem]:
        obj = self.objectForFrame(frame, visible=True)
        if obj:
            path = self(frame=frame)
            return QtWidgets.QGraphicsPathItem(path)
        
    def shape(self, frame:typing.Optional[int] = None) -> shapes.Geometry:
        """Returns an empty point"""
        return shapes.Point()
            
        
class ArcMove(PlanarGraphics):
    """Encapsulates parameters for QPainterPath.arcMoveTo() function.
        NOTE: This does NOT create an arc curve, only "jumps" a point along an arc
        defined by the parameters below.
        Therefore, by defintion, it is never drawn and its curveLength is 0

    x, y, w, h, specify the bounding rectangle;
    a specifies the start angle.
    
    NOTE: Since this is a move on an arc trajectory, there is NO sweep length
    
    See also documentation for QPainterPath.arcMoveTo() function.
    """
    _planar_descriptors_ = ("x", "y", "w", "h", "a")
    
    _planar_graphics_type_ = PlanarGraphicsType.arcmove
    
    qt_path_composition_call = "arcMoveTo"
    
    _default_label_ = "av"
    
    def __init__(self, *args, name:str=None, frameindex:list=[], currentframe:int=0, 
                 graphicstype=None, closed:bool=False,
                 linked_objects:dict=dict()):
        """
        Positional parameters:
        =====================
        x, y, w, h = bounding rectangle (top left (x,y), width and height)
        
        a = angle (degrees, positive is CCW; negative is CW)
        
        """
        super().__init__(*args, name=name, frameindex=frameindex, currentframe=currentframe, 
                         graphicstype=PlanarGraphicsType.arcmove, closed=closed, 
                         linked_objects=linked_objects)
    
    def controlPoints(self, frame:typing.Optional[int] = None, inPath:bool=False):
        """Returns the control points for this Arc, as a tuple.
        
        To be used for graphical manipulation of the arc.
        
        Overrides this method in the superclass (PlanarGraphics).
        
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
            
        if state is None: # or len(state) == 0:
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
        
        if inPath:
            return (cp1, cp2)
        
        return (cp0, cp1, cp2)
    
    def controlPath(self, frame:typing.Optional[int] = None, inPath:bool=False):
        """Returns the control points for this ArcMove, as a Path object
        
        NOTE: Since this is a move on an arc trajectory, there is NO sweep length
        To be used for graphical manipulation of the arc.
        
        Overrides this method in the superclass (PlanarGraphics).

        The control points are given as (x,y) pairs or Cartesian coordinates
        with the major axis of the arc's ellipse having a 0 angle, in the 
        following order:
        
        cp0: the origin of the enclosing rectangle (Move to)
        
        cp1: starting point of the arc (line to)
        
        cp2: the centre of the arc's ellipse (and enclosing rectangle) (line to)
        
        """
        
        ret = Path()
        
        cp = self.controlPoints(frame, inPath)
        
        for k, p in enumerate(cp):
            if k == 0:
                ret.append(Move(p[0],p[1]))
                
            else:
                ret.append(Line(cp[k-1][0], cp[k-1][1], p[0], p[1]))
        
        return ret
        
    def fromControlPath(self, path:Path, frame:typing.Optional[int]=None):
        """Overrides this method in the superclass (PlanarGraphics)."""
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
            
        if state is None: # or len(state) == 0:
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
        
    def qGraphicsItem(self, frame:typing.Optional[int]=None) -> typing.Optional[QtWidgets.QGraphicsItem]:
        obj = self.objectForFrame(frame, visible=True)
        if obj:
            path = self(frame=frame)
            return QtWidgets.QGraphicsPathItem(path)

    def shape(self, frame:typing.Optional[int] = None) -> shapes.Geometry:
        """Returns an empty point"""
        return shapes.Point()
            
            
class Line(PlanarGraphics):
    """A linear path segment, with coordinates x and y (float type).
    
    Corresponds to a QPainterPath.LineToElement.
    """
    _planar_descriptors_ = ("x0", "y0", "x1", "y1")

    # NOTE: 2021-04-25 11:14:20 
    # Because lineTo is in fact stored as a single coordinate (x,y) pair,
    # if a Path starts with a line, the intial point on the path is implied to 
    # be a Move(0,0) point
    _planar_graphics_type_ = PlanarGraphicsType.line
    
    qt_path_composition_call = "lineTo"

    _default_label_ = "l"
   
    def __init__(self, *args, name=None, frameindex=[], currentframe=0, graphicstype=None,
                 closed=False,
                 linked_objects=dict()):
        """Parameters:
        x0, y0 = start point coordinates
        x1, y1 = end point coordinates
        """
        super().__init__(*args, name=name, frameindex=frameindex, currentframe=currentframe, 
                         graphicstype=PlanarGraphicsType.line, closed=closed,
                         linked_objects=linked_objects)
        
    def __call__(self, path:typing.Optional[QtGui.QPainterPath]=None, 
                 frame:typing.Optional[int]=None, 
                 closed:typing.Optional[bool]=None, 
                 connected:typing.Optional[bool]=False) -> QtGui.QPainterPath:
        if closed is None:
            closePath = self.closed
            
        elif isinstance(closed, bool):
            closePath = closed
            
        else:
            raise TypeError("closed expected to be a boolean or None; got %s instead" % type(closed).__name__)
        
        if not isinstance(frame, int):
            frame = self.currentFrame
            
        state = self.getState(frame)
        
        if not isinstance(path, QtGui.QPainterPath):
            path = QtGui.QPainterPath()

        if state:
            if path.length() == 0.:
                path.moveTo(state.x0, state.y0)
            path.lineTo(state.x1, state.y1)
                
        return path

    def qGraphicsItem(self, frame:typing.Optional[int] = None) -> typing.Optional[QtWidgets.QGraphicsItem]:
        """Call this only for a object that is visible in the specified frame"""
        qp = self.qPoints(frame)
        if len(qp) >= 2:
            return QtWidgets.QGraphicsLineItem(QtCore.QLineF(qp[0],qp[1]))
        
    def shape(self, frame:typing.Optional[int] = None) -> shapes.Geometry:
        return shapes.LineString(self.controlPoints(frame, False))
        
class Move(PlanarGraphics):
    """Starting path point with coordinates x and y (float type).
    
    Corresponds to a QPainterPath.MoveToElement.
    
    When present, it initiates a new path (or subpath, if preceded by any other 
    path element or PlanarGraphics object).
    
    Start is an alias of Move in this module.
    """
    _planar_descriptors_ = ("x", "y")
    
    _planar_graphics_type_ = PlanarGraphicsType.point
    
    qt_path_composition_call = "moveTo"

    _default_label_ = "m"
   
    #"def" __init__(self, x, y, name=None, frameindex=[], currentframe=0):
    def __init__(self, *args, name=None, frameindex=[], currentframe=0, 
                 graphicstype=None, closed=False,
                 linked_objects=dict()):
        """Parameters: move to point coordinates (x,y)
        """
        super().__init__(*args, 
                         name=name, 
                         frameindex=frameindex, 
                         currentframe=currentframe,
                         graphicstype=PlanarGraphicsType.point, 
                         closed=closed,
                         linked_objects=linked_objects)
        
    def controlPoints(self, frame:typing.Optional[int]=None, inPath:bool=False) -> tuple:
        state = self.getState(frame)
        
        if state: # and len(state):
            return ((state.x, state.y),)

        return tuple()
    
    def controlPath(self, frame:typing.Optional[int]=None, inPath:bool=False) -> Path:
        ret = Path()
        cp = self.controlPoints(frame, inPath)
        for k, p in enumerate(cp):
            ret.append(Move(p[0], p[1]))
            
        return ret
    
    def fromControlPath(self, path:Path, frame:typing.Optional[int]=None):
        if not isinstance(path, Path):
            raise TypeError(f"path expected to be a pictgui.Path; got {type(path).__name__} instead" )
        
        if len(path) == 0:
            return
        
        if not all(isinstance(p, (Move, Line)) for p in path):
            raise ValueError("Expecting a path containing only Move and Line objects")

        startElement = path[0]
        
        if frame is None:
            state = self.currentState
            control_state = startElement.currentState()
        else:
            state = self.getState(frame)
            control_state = startElement.getState(frame=frame, visible=True)
            
        if state is None or len(state) == 0:
            return
        
        if control_state is None or len(control_state) == 0:
            raise ValueError("path argument has undefined state")
            
        if all(d in startElement.shapeDescriptors for d in ("x", "y")):
            state.x = control_state.x
            state.y = control_state.y
        
    def qPoints(self):
        return [QtCore.QPointF(self.x, self.y)]
    
    def qPoint(self):
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
            
        if state is None: # or len(state) == 0:
            warnings.warn("undefined state")
            return
            
        return QtWidgets.QGraphicsEllipseItem(QtCore.QRectF(state.x - pointSize/2,
                                                            state.y - pointSize/2,
                                                            pointSize, 
                                                            pointSize))

Start = Move

Point = Move
                              
class Cubic(PlanarGraphics):
    """A cubic curve path segment
    
    Corresponds to the triplet:
    (QPainterPath.CurveToElement, QPainterPath.CurveToDataElement, QPainterPath.CurveToDataElement).
    
    """
    _planar_descriptors_ = ("c0x", "c0y", "c1x", "c1y", "c2x","c2y", "c3x", "c3y")
    
    _planar_graphics_type_ = PlanarGraphicsType.cubic
    
    qt_path_composition_call = "cubicTo"

    _default_label_ = "c"

    def __init__(self, *args, name=None, frameindex=[], currentframe=0, graphicstype=None,
                 closed=False,
                 linked_objects=dict()):
        """
        Parameters:
        c0x, c0y = start point coordinates
        c1x, c1y = first control point coordinates
        c2x, c2y = second control point coordinates
        c3x, c3y = cubic curve destination coordinates
        
        """
        super().__init__(*args, name=name, frameindex=frameindex, currentframe=currentframe,
                         graphicstype=PlanarGraphicsType.cubic, closed=closed,
                         linked_objects=linked_objects)
        
#     def __call__(self, path:typing.Optional[QtGui.QPainterPath]=None, 
#                  frame:typing.Optional[int]=None, 
#                  closed:typing.Optional[bool]=None, 
#                  connected:typing.Optional[bool]=False) -> QtGui.QPainterPath:
#         
#         if path is None:
#             path = QtGui.QPainterPath()
#             
#         if closed is None:
#             closePath = self.closed
#             
#         elif isinstance(closed, bool):
#             closePath = closed
#             
#         else:
#             raise TypeError("'closed' expected to be a boolean or None; got %s instead" % type(closed).__name__)
#         
#         if not isinstance(frame, int):
#             frame = self.currentFrame
#             
#         state = self.getState(frame)
#         
#         if state:
#             if connected:
#                 s0 = f"lineTo({state.c0x},{state.c0y})"
#             else:
#                 s0 = f"moveTo({state.c0x},{state.c0y})"
#                 
#             s = [self.qt_path_composition_call+"("]
#             
#             s += [",".join(["%f" % state[a] for a in self.shapeDescriptors[2:]])]
#             
#             s+=[")"]
#             
#             eval(f"path.{s0}")
#             eval(f"path.{''.join(s)}")
#             
#             if closePath:
#                 path.lineTo(state.c0x, state.c0y) 
#         
#         return path
        
#     @property
#     def x(self) -> numbers.Number:
#         return self().boundingRect().x()
#     
#     @x.setter
#     def x(self, val:numbers.Number):
#         dx = val - self().boundingRect().x()
#         self.translate(dx, type(dx)(0))
#         
#     @property
#     def y(self) -> numbers.Number:
#         return self().boundingRect().y()
#         
#     @y.setter
#     def y(self, val:numbers.Number):
#         dy = val - self().boundingRect().y()
#         self.translate(type(dy)(0), dy)
        
#     def controlPoints(self, frame=None):
#         if frame is None:
#             state = self.currentState
#             
#         else:
#             state = self.getState(frame)
#             
#         if state is None: # or len(state) == 0:
#             return tuple()
#         
#         return tuple(map(lambda x: (getattr(state, x[0]), getattr(state, x[1])), 
#                          itertools.islice(itertools.pairwise(self.shapeDescriptors), 0, None, 2)))
#         
#     def qPoints(self, frame:typing.Optional[int]=None):
#         cp = self.controlPoints(frame)
#         
#         if len(cp):
#             return list(map(lambda x: QtCore.QPointF(x[0], x[1]), cp))
#         else:
#             return list()
        
#     def controlPath(self, frame=None):
#         ret = Path()
#         
#         cp = self.controlPoints(frame)
#         
#         for k,p in enumerate(cp):
#             if k == 0:
#                 ret.append(Move(p[0], p[1]))
#                 
#             else:
#                 ret.append(Line(p[0], p[1]))
#             
#         return ret
    
#     def fromControlPath(self, path, frame=None):
#         """Updates from a control path.
#         A control path is a polyline Path object containing 3 or 4 control 
#         points (cp):
#         cp0 (optional:) - the first control point — this is typically a "virtual"
#             point (not supplied to the constructor) to accomodate the general case
#             where the point is actually the last one on the previous PlanarGraphics
#             in a Path
#         cp1, cp2 cp3 - the control points as per the constructor
#         
#         NOTE: that Cubic.controlPath always supplied a path composed of four points.
#         However, paths generated elsewhere can have only three points (cp1, cp2 and cp3)
#         as long as the caller is aware that hose three points are as stated here.
#         
#     """
#         if not isinstance(path, Path):
#             raise TypeError(f"'path' expected to be a pictgui.Path; got {type(path).__name__} instead")
#         
#         if len(path) != 4:
#             raise ValueError(f"'path' expected to have four elements; got {len(path)} elements instead")
#         
#         control_state = path.currentState
#         
#         if control_state is None or len(control_state) == 0:
#             raise ValueError("'path' argument has undefined state")
#         
#         if frame is None:
#             state = self.currentState
#             
#         else:
#             state = self.getState(frame)
#             
#         if state is None: # or len(state) == 0:
#             return
#         
#         # NOTE: 2024-08-24 13:29:28
#         # see NOTE: 2024-08-24 12:43:30 in quad.fromControlPath for a description
#         # of the algorithm in the comprehension below — Python is a gem!
#         tuple(map(lambda x: setattr(state, x[0], x[1]), itertools.islice(itertools.pairwise(itertools.chain.from_iterable(zip(*itertools.chain.from_iterable(zip(itertools.islice(itertools.pairwise(self.shapeDescriptors), 0, None, 2), map(lambda x: (x.x, x.y), path)))))), 0, None, 2)))
#         
#         self.updateFrontends()
        
    # def translate(self, dx, dy):
    #     # print(f"{self.__class__.__name__}.translate({dx}, {dy})")
    #     self.c0x += dx
    #     self.c0y += dy
    #     self.c1x += dx
    #     self.c1y += dy
    #     self.c2x += dx
    #     self.c2y += dy
    #     self.c3x += dx
    #     self.c3y += dy
    #     # print(f"\n → {self}")
        
    def shape(self, frame:typing.Optional[int] = None) -> shapes.Geometry:
        """Returns an empty point"""
        scipywarn("shapely does not support cubic splines")
        return shapes.Point()
    
    def makeBSpline(self, xy:typing.Optional[typing.Union[typing.Sequence[numbers.Number], Move, Point, Line]]=None, extrapolate=True):
        """Creates a cubic BSpline object with origin at "xy"
        
        Parameters:
        ==========
        xy: array_like: the x0, y0 coordinates of the origin
        
        extrapolate: boolean, default True (see scipy.inteprolate.BSpline)
        
        """
        from scipy.interpolate import BSpline
        
        t = np.zeros((8,))
        t[4:] = 1.
        
        if isinstance(xy, typing.Sequence) and len(xy) == 2 and all(isinstance(v, numbers.Number) for v in xy):
            cp0 = list(xy)
        elif isinstance(xy, (Move, Line, Point)):
            cp0 = [xy.x, xy.y]
        elif xy is None:
            cp0 = [0., 0.]
        else:
            raise TypeError(f"'xy' expected a Point, Move, Line, or a 2-sequence of numbers")
            
        c = np.array([cp0, [self.c1x, self.c1y], [self.c2x, self.c2y], [self.c3x, self.c3y]])
        
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
    
    """
    _planar_descriptors_ = ("c0x", "c0y", "c1x", "c1y", "c2x","c2y")
    
    _planar_graphics_type_ = PlanarGraphicsType.quad
    
    qt_path_composition_call = "quadTo"

    _default_label_ = "q"
   
    def __init__(self, *args, name=None, frameindex=[], currentframe=0, 
                 graphicstype=None, closed=False,
                 linked_objects=dict()):
        """
        Parameters:
        c0x, c0y = first point coordinates
        c1x, c1y = control point coordinates
        c2x, c2y = last point coordinates
        """
        super().__init__(*args, name=name, frameindex=frameindex, currentframe=currentframe, 
                         graphicstype=PlanarGraphicsType.quad, closed=closed,
                         linked_objects=linked_objects)
    
#     def __call__(self, path:typing.Optional[QtGui.QPainterPath]=None, 
#                  frame:typing.Optional[int]=None, 
#                  closed:typing.Optional[bool]=None, 
#                  connected:typing.Optional[bool]=False):
#         
#         if path is None:
#             path = QtGui.QPainterPath()
#             
#         if closed is None:
#             closePath = self.closed
#             
#         elif isinstance(closed, bool):
#             closePath = closed
#             
#         else:
#             raise TypeError("closed expected to be a boolean or None; got %s instead" % type(closed).__name__)
#         
#         if not isinstance(frame, int):
#             frame = self.currentFrame
#             
#         state = self.getState(frame)
#         
#         if state:
#             if connected:
#                 s0 = f"lineTo({state.c0x},{state.c0y})"
#             else:
#                 s0 = f"moveTo({state.c0x},{state.c0y})"
#                 
#             s = [self.qt_path_composition_call+"("]
#             
#             s += [",".join(["%f" % state[a] for a in self.shapeDescriptors[2:]])]
#             
#             s+=[")"]
#             
#             eval(f"path.{s0}")
#             eval(f"path.{''.join(s)}")
#             
#             if closePath:
#                 path.lineTo(state.c0x, state.c0y) 
#         
#         return path
        
#     @property
#     def x(self) -> numbers.Number:
#         return self().boundingRect().x()
#     
#     @x.setter
#     def x(self, val:numbers.Number):
#         dx = val - self().boundingRect().x()
#         self.translate(dx, type(dx)(0))
#         
#     @property
#     def y(self) -> numbers.Number:
#         return self().boundingRect().y()
#         
#     @y.setter
#     def y(self, val:numbers.Number):
#         dy = val - self().boundingRect().y()
#         self.translate(type(dy)(0), dy)
        
#     def controlPoints(self, frame=None):
#         if frame is None:
#             state = self.currentState
#             
#         else:
#             state = self.getState(frame)
#             
#         if state is None: # or len(state) == 0:
#             return tuple()
#         
#         return tuple(map(lambda x: (getattr(state, x[0]), getattr(state, x[1])), 
#                          itertools.islice(itertools.pairwise(self.shapeDescriptors), 0, None, 2)))
        
#     def controlPath(self, frame=None):
#         ret = Path()
#         cp = self.controlPoints(frame)
#         
#         for k,p in enumerate(cp):
#             if k == 0:
#                 ret.append(Move(p[0],p[1]))
#                 
#             else:
#                 ret.append(Line(p[0],p[1]))
#                 
#         return ret
    
#     def fromControlPath(self, path, frame=None):
#         if not isinstance(path, Path):
#             raise TypeError(f"path expected to be a pictgui.Path; got {type(path).__name__} instead" )
#         
#         if len(path) != 3:
#             raise ValueError(f"path expected to have three elements; got {len(path)} elements instead")
#         
#         control_state = path.currentState
#         
#         if control_state is None or len(control_state) == 0:
#             raise ValueError("path argument has undefined state")
#         
#         if frame is None:
#             state = self.currentState
#             
#         else:
#             state = self.getState(frame)
#             
#         if state is None or len(state) == 0:
#             return
#         
#         # NOTE: 2024-08-24 12:43:30 
#         # What this does (breakdown of the comprehension below, for future reference)
#         # <pseudocode; '→' indicates the result of the operation if it would be 
#         # evaluated by wrapping it in a list constructor>:
#         #
#         # 1) distributes the shape decriptors in a sequence of pairs:
#         #   NOTE 2024-08-24 13:18:56
#         #   itertools.pairwise([abcdef]) generates [ab, bc, cd, de, ef],
#         #   but we want only [ab, cd, ef] therefore we geed this into itertools.islice
#         #   itertools.islice(itertools.pairwise(self.shapeDescriptors), 0, None, 2) → [('c0x', 'c0y'), ('c1x', 'c1y'), ('c2x', 'c2y')]
#         #
#         # 2) 'extracts' the x, y coordinate pairs of the points on the path, where
#         # x0,y0,x1,y1,x2,y2 are the coordinate values of the three points on the path:
#         #   map(lambda x: (x.x, x.y), path) → [(x0, y0), (x1, y1), (x2, y2)]
#         #
#         # 3) pairs (zips) (1) with (2) → [(('c0x', 'c0y'), (x0, y0)),
#         #                                 (('c1x', 'c1y'), (x1, y1)),
#         #                                 (('c2x', 'c2y'), (x2, y2))]
#         #
#         # 4) matches each shape descriptor with its value — steps:
#         # 4.1) collate (3) in a single iterable (still pairwise):
#         #   itertools.chain.from_iterable(zip(itertools.islice(itertools.pairwise(self.shapeDescriptors), 0, None, 2), map(lambda x: (x.x, x.y), path)))
#         #   → [('c0x', 'c0y'),(x0, y0), ('c1x', 'c1y'), (x1, y1), ('c2x', 'c2y'), (x2, y2)]
#         #
#         # 4.2) orthogonalize the pairings:
#         #   4.2.1) expand (unzip) (4.1) to generate two sequences:
#         #       zip(*itertools.chain.from_iterable(zip(itertools.islice(itertools.pairwise(self.shapeDescriptors), 0, None, 2), map(lambda x: (x.x, x.y), path))))
#         #       → [('c0x', x0, 'c1x', x1, 'c2x', x2), ('c0y', y0, 'c1y', y1, 'c2y', y2)]
#         #
#         #   4.2.2) chain (concatenate) the result from (4.2.1) to obtain an iterable 
#         #   where each attribute and its corresponding value are interleaved:
#         #       itertools.chain.from_iterable(<result of 4.2.1>)
#         #       → ['c0x', x0, 'c1x', x1, 'c2x', x2, 'c0y', y0, 'c1y', y1, 'c2y', y2]
#         #
#         #   4.2.3 split the results of (4.2.2) into a sequence of (attribute, value) pairs:
#         #       (see NOTE 2024-08-24 13:18:56 explaining why I feed pairwise into islice)
#         #       itertools.islice(itertools.pairwise(<result of 4.2.2>), 0, None, 2)
#         #       → [('c0x', x0),('c1x', x1),('c2x', x2),('c0y', y0),('c1y', y1),('c2y', y2)]  ⇇ orthogonalized version of (4.1)
#         #
#         # 4.3) apply the value to their attributes — 
#         #   map(lambda x: setattr(state, x[0], x[1]), <result of 4.2.3>)
#         # 
#         #  NOTE: 2024-08-24 13:26:02 
#         #  in the comprehesion below, map MUST be evaluated hence we wrap it in 
#         #  a tuple constructor, even if the statement returns a tuple of None objects,
#         #  which will be garbage collected
#         #
#         tuple(map(lambda x: setattr(state, x[0], x[1]), itertools.islice(itertools.pairwise(itertools.chain.from_iterable(zip(*itertools.chain.from_iterable(zip(itertools.islice(itertools.pairwise(self.shapeDescriptors), 0, None, 2), map(lambda x: (x.x, x.y), path)))))), 0, None, 2)))
#         
#         self.updateFrontends()
        
    # def translate(self, dx, dy):
    #     self.c0x += dx
    #     self.c0y += dy
    #     self.c1x += dx
    #     self.c1y += dy
    #     self.c2x += dx
    #     self.c2y += dy
        
    def qPoints(self, frame=None, inPath:bool=False):
        cp = self.controlPoints(frame, inPath)
        
        if len(cp):
            return list(map(lambda x: QtCore.QPointF(x[0], x[1]), cp))
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
        
class Ellipse(PlanarGraphics):
    """Encapsulates parameters for QPainterPath.addEllipse() function:
    
    x, y, w, h specify the coordinates of the bounding rectangle
    """
    _planar_descriptors_ = ("x", "y", "w", "h")
    
    _planar_graphics_type_ = PlanarGraphicsType.ellipse
    
    qt_path_composition_call = "addEllipse"
    
    _default_label_ = "e"

    def __init__(self, *args, name=None, frameindex=[], currentframe=0, graphicstype=None, 
                 closed=False,
                 linked_objects=dict()):
        """
        Parameters: 
        x, y, w, h = bounding rectangle (top left (x,y), width, height)
        """
        super().__init__(*args, name=name, frameindex=frameindex, currentframe=currentframe,
                         graphicstype=PlanarGraphicsType.ellipse, closed=closed,
                         linked_objects=linked_objects)
        
#     def __call__(self, path:typing.Optional[QtGui.QPainterPath]=None, 
#                  frame:typing.Optional[int]=None, 
#                  closed:typing.Optional[bool]=None, 
#                  connected:typing.Optional[bool]=False) -> QtGui.QPainterPath:
#         if path is None:
#             path = QtGui.QPainterPath()
#             
#         if closed is None:
#             closePath = self.closed
#             
#         elif isinstance(closed, bool):
#             closePath = closed
#             
#         else:
#             raise TypeError("closed expected to be a boolean or None; got %s instead" % type(closed).__name__)
#         
#         if not isinstance(frame, int):
#             frame = self.currentFrame
#             
#         state = self.getState(frame)
#         
#         origin = self.shapeDescriptors[:2]
#         
#         if state:
#             if connected:
#                 s0 = f"lineTo({state[origin[0]]},{state[origin[1]]})"
#             else:
#                 s0 = f"moveTo({state[origin[0]]},{state[origin[1]]})"
#                 
#             eval(f"path.{s0}")
#             
#             s = [f"{self.qt_path_composition_call}("]
#             
#             s += [",".join(["%f" % state[a] for a in self.shapeDescriptors])]
#             
#             s+=[")"]
                
        
    def controlPoints(self, frame:typing.Optional[int]=None, inPath:bool=False):
        """Control points are the top-left and bottom right of the enclosing rectangle
        """
        # TODO use more detailed control points as for ArcTo 
        # NOTE: this would be an unnecessary complication
        if frame is None:
            state = self.currentState
            
        else:
            state = self.getState(frame)
            
        if state is None: # or len(state) == 0:
            return tuple()
        
        if inPath:
            return ((state.x + state.w, state.y + state.h),)
        
        return ((state.x, state.y), (state.x + state.w, state.y + state.h))
    
    
#     def controlPath(self, frame:typing.optional[int]=None):
#         """Control path is a line along the first diagonal of the enclosing rectangle
#         (top-left to bottom-right)
#         """
#         ret = Path()
#         
#         cp = self.controlPoints(frame)
#         
#         for k,p in enumerate(cp):
#             if k == 0:
#                 ret.append(Move(p[0],p[1]))
#             
#             else:
#                 ret.append(Line(p[0],p[1]))
#                 
#         return ret
        
    def fromControlPath(self, path:Path, frame=None):
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
            
        if state is None: # or len(state) == 0:
            return
        
        state.x = path[0].x
        state.y = path[0].y
        
        state.w = path[1].x - state.x
        state.h = path[1].y - state.y
        
        self.updateFrontends()
        
    def eccentricity(self, frame:typing.Optional[int] = None) -> float:
        if frame is None:
            state = self.currentState
            
        else:
            state = self.getState(frame)
            
        if state is None: # or len(state) == 0:
            return math.nan
        
        # calculate the center of the ellipse
        c0 = (state.x + state.w/2, state.y + state.h/2) 
        
        # FIXME: 2024-08-27 23:04:40
        # but what if the ellipse has been rotated?
        # answer: the orignal defining bounding rect in the statehas also been rotated!
        majorAxis, minorAxis = max(state.w, state.h), min(state.w, state.h)
        a = majorAxis/2
        b = minorAxis/2
        c = math.sqrt(a ** 2 - b ** 2)
        
        return c/a
    
        
    def shape(self, frame:typing.Optional[int] = None) -> shapes.Geometry:
        """Returns an empty point"""
        if frame is None:
            state = self.currentState
            
        else:
            state = self.getState(frame)
            
        if state is None: # or len(state) == 0:
            return shapes.Point() # empty shape
        
        # calculate the center of the ellipse
        c0 = (state.x + state.w/2, state.y + state.h/2) 
        majorAxis, minorAxis = max(state.w, state.h), min(state.w, state.h)
        a = majorAxis/2
        b = minorAxis/2
        c = math.sqrt(a ** 2 - b ** 2)
        
        scipywarn("shapely does not directly support ellipses")
        return shapes.Point()
    
        
    def qPoints(self, frame = None):
        """Returns the points (vertices) of the enclosing rectangle.
        
        If there is no associated state for the specified frame index returns an
        empty list.
        
        """
        if frame is None:
            state = self.currentState
            
        else:
            state = self.getState(frame)
            
        if state is None: # or len(state) == 0:
            return list()
            
        return [QtCore.QPointF(state.x, state.y), 
                QtCore.QPointF(state.x + state.w, state.y), 
                QtCore.QPointF(state.x + state.w, state.y + state.h),
                QtCore.QPointF(state.x, state.y + state.h)]
    
    def qGraphicsItem(self, pointSize=0, frame = None):
        state = self.getstate(frame)
            
        if state is None: # or len(state) == 0:
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
    _planar_descriptors_ = ("x", "y", "w", "h")
    
    _planar_graphics_type_ = PlanarGraphicsType.rectangle
    
    qt_path_composition_call = "addRect"

    _default_label_ = "r"
   
    def __init__(self, *args, name=None, frameindex=[], currentframe=0, graphicstype=None,
                 closed=False, linked_objects=dict()):
        """
        Positional parameters: 
        =====================
        
        x, y: top left coordinates (x,y) 
        
        w, h: width and height
        
        """
        super().__init__(*args, name=name, frameindex=frameindex, currentframe=currentframe, 
                         graphicstype=PlanarGraphicsType.rectangle, closed=closed,
                         linked_objects=linked_objects)
        
    def controlPoints(self, frame=None, inPath:bool=False):
        """Control points are the top-left and bottom right vertices
        """
        if frame is None:
            state = self.currentState
            
        else:
            state = self.getState(frame)
            
        if state is None: # or len(state) == 0:
            return tuple()
        
        if inPath:
            return ((state.x + state.w, state.y + state.h), )
        
        return ((state.x, state.y), (state.x + state.w, state.y + state.h))
    
    def controlPath(self, frame=None, inPath:bool=False):
        """Control path is the diagonal from top-left to bottom-right
        
        This is based on the state associated with the specified frame, or with
        the current frame when 'frame' is None
        
        Frame: an int or None (which signifies the current frame)
        
        When no state exists for the specified frame, returns an empty Path.
        """
        ret = Path()
        cp = self.controlPoints(frame, inPath)
        
        for k,p in enumerate(cp):
            if k == 0:
                ret.append(Move(p[0],p[1]))
                
            else:
                ret.append(Line(cp[k-1][0], cp[k-1][1],p[0],p[1]))
                
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
            
        if state is None: # or len(state) == 0:
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
            
        if state is None: # or len(state) == 0:
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
            
        if state is None: # or len(state) == 0:
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
        
            
        if state is not None: # and len(state):
            ret.append(Move(state.x, state.y))
            ret.append(Line(state.x, state.y, 
                            state.x + state.w, state.y))
            ret.append(Line(state.x + state.w, state.y, 
                            state.x + state.w, state.y + state.h))
            ret.append(Line(state.x + state.w, state.y + state.h,
                            state.x, state.y + state.h))
            
            if closed:
                ret.append(Line(state.x, state.y + state.h, 
                                state.x, state.y))
                
        return ret
    
    def convertToPath(self):
        frame_ndx = self.frameIndices()
        ret = self.objectForFrame(frame=frame_ndx[0], closed=True)
        
        for f in frame_ndx[1:]:
            frame_path = self.objectForFrame(frame=f, closed=True)
            
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
            
class Text(PlanarGraphics):
    """PlanarGraphics object encapsulating a string.
    WARNING Incomplete API
    TODO also adapt the GraphicsObject frontend to support this class!
    """
    _planar_descriptors_ = ("text", "x", "y") 
    
    _planar_graphics_type_ = PlanarGraphicsType.text
    
    qt_path_composition_call = ""
    
    _required_attributes_ = ("_ID_")
    
    _default_label_ = "t"
   
    @classmethod
    def defaultState(cls):
        return Bunch(text="", x=0, y=0, z_frame=None)
    
    def __init_from_descriptors__(self, *args, frameindex:typing.Optional[typing.Iterable]=[],
                                  currentframe:int=0) -> None:
        state = self.defaultState()
        
        if len(args) in (1,3):
            if isinstance(args[0], str):
                state["text"] = args[0]
                
            else:
                raise TypeError("First descriptor for Text is expected to be a str; got %s instead" % type(args[0]).__name__)
            
            if len(args) == 3:
                if all([isinstance(a, numbers.Number) for a in args[1:]]):
                    state["x"], state["y"] = args[1:]
                    
                else:
                    raise TypeError("Last two descriptors expected to be numbers; got %s instead" % (args[1:],))
                
        elif len(args) != 0:
            raise ValueError("Expecting zero, one or three descriptors; got %d instead" % len(args))
        
        self._states_ = [state]
            
        self._applyFrameIndex_(frameindex)
        self._currentframe_ = currentframe
        self.checkStates()
    
    def __init__(self, *args, name="Text", frameindex=[], currentframe=0, position = (0,0)):
        if not isinstance(text, str):
            raise TypeError("Expecting a str as first parameter; got %s instead" % type(text).__name__)
        
        self._currentframe_ = currentframe
        self._ID_ = name
        self._closed_ = False
        
        super().__init__(*args, name=name, frameindex=frameindex, currentframe=currentframe,
                                graphicstype=PlanarGraphicsType.text,
                                closed=False)
        
    def __call__(self, path:typing.Optional[QtGui.QPainterPath]=None, 
                 frame:typing.Optional[int]=None, 
                 closed:typing.Optional[bool]=None, 
                 connected:typing.Optional[bool]=False) -> QtGui.QPainterPath:
        """Returns path unaltered, or an empty path"""
        if path is None:
            path = QtGui.QPainterPath()
            
        return path
    
    @property
    def closed(self):
        return False
    
    def copy(self):
        ret = self.__class__(self)
        return ret
    
    def controlPoints(self, frame=None, inPath:bool=False):
        return tuple()
    
    def fromControlPath(self, path, frame=None):
        pass
                
    def controlPath(self, frame=None):
        return Path()
    
    def objectForFrame(self, frame=None, closed=False):
        return Path()
    
    def qPoints(self, frame=None):
        if frame is None:
            state = self.currentState
            
        else:
            frame = self.getState(frame)
            
        if state: # and len(state):
            return [QtCore.QPointF(state.x, state.y)]
        
        else:
            return list()
        
    # def qGraphicsItem(self, pointSize=0, frame = None):
        
class Path(PlanarGraphics):
    """Encapsulates a path composed of simple PlanarGraphics objects.
    
    Emulates a Python list. Path objects can be constructed from a sequence of
    PlanarGraphics elements. 
    
    NOTE: Differences from the list API: 
    TODO/FIXME: allow subpaths - effectively behave like a nested list of elmentary
    PlanarGraphics.
    
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
    
    # NOTE: 2020-11-02 08:05:51 Path on 3D data:
    # there are theoretically two ways to deal with this:
    #
    # 1) have a list of single-state PlanarGraphics for each frame - huge overhead!
    #
    # 2) have a single list of PlanarGraphics, each possibly with multiple states, 
    # and visibility decided on a frame-by-frame basis independently, by the value
    # of z_frame of those states.
    #
    # I am opting for method (2), where the Path holds the same number of graphics
    # across all frames, with the possibility that only a subset of them is shown
    # in any given frame, and a subset of them are visible in more than one frame.
    
    _planar_descriptors_ = () 
    
    _planar_graphics_type_ = PlanarGraphicsType.path
    
    qt_path_composition_call = "addPath"
    
    _default_label_ = "p"
   
    _required_attributes_ = ("_ID_", "_linked_objects_", "_segment_lengths_", 
                             "_objects_")

    def __init_from_planar_graphics_(self, *args, frameindex:typing.Optional[typing.Iterable]=[],
                                    currentframe:int=0) -> None:
        """
        Initialize Path from a sequence of PlanarGraphics objects.
        This is also used for unpickling
        """
        #print("Path.__init_from_planar_graphics_")
        for p in args:
            self._objects_.append(p.copy())
            
        obj = self._objects_[0]
        # make sure the Path starts with a Move
        if not isinstance(obj, Move):
            self._objects_.insert(0, Move(obj.x, obj.y, frameindex=frameindex, currentframe=currentframe))
            
    def __init__(self, *args, name:typing.Optional[str]="path", frameindex=[], currentframe:int=0, 
                 graphicstype=None, closed=False,
                 linked_objects = dict(), position = (0,0)):
        """
        Path constructor
        
        Parameters:
        -----------
        
        *args; 
            When this is empty, the Path will be initalized without elements.
            
            1. When args have just one element, this can be:
            
            1.1. a Path - in which case this function behaved like a copy constructor
            
            1.2. a PlanarGraphics other than a Path - the Path will be initialized 
            with this element. If the PlanarGraphics is NOT a Move element, a
            Move element will be prepended to the Path, with the coordinates, 
            frame index and current frame as specified by the named parameters
            (see below)
            
            1.3. a sequence (tuple or list) of numeric values used to construct
            PlanarGraphics objects.
                Currently, only Move and Line objects are supported by this syntax.
                
            1.4. a sequence (tuple or list) of PlanarGraphics objects (these can
            be Path objects themselves)
            
            2. When args is a sequence of parameters, these can be:

            2.1 A sequence of sequences of numeric values, each used to construct
            a PlanarGraphics object component of this path
            
            2.2 A sequence of PlanarGraphics objects (including another Path)
            
        
        
        """
        
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
        # found when currentstate is queried;  also serves as cached position
        # NOTE: TODO perhaps, in the general case, this should hold the
        # min(x), min(y) coordinate of the convex hull of the path ?
        self._position_ = position # will be overridden
            
        # NOTE:  2018-02-11 21:02:35
        # # TODO!!!
        # cache of the euclidean lengths of its segments and contour lengths of its
        # shaped elements.
        self._segment_lengths_ = list() 
        
        self._closed_ = closed
        
        self._ID_ = name
        
        if isinstance(name, str) and len(name.strip()):
            self._ID_ = name
        else:
            self._ID_ = self.__class__.__name__
        
        # NOTE: 2021-10-10 11:25:20
        # init super with no args
        PlanarGraphics.__init__(self, (), name=name, frameindex=frameindex, currentframe=currentframe, 
                                graphicstype=PlanarGraphicsType.path, closed=closed,
                                linked_objects = linked_objects)
        
        if len(args):
            if len(args) == 1: # construct Path from one argument in *args, which may be:
                if isinstance(args[0], Path): # a Path => copy constructor
                    # NOTE: 2021-04-26 11:52:53
                    # there should be no need to chack that Path starts with a 
                    # Move - this should have been taken care of when the original
                    # Path was constructed
                    for a in args[0]:
                        self._objects_.append(a.copy())
                    
                    self._closed_ = args[0]._closed_
                    self._currentframe_ = args[0]._currentframe_
                    self._ID_ = args[0]._ID_
                    
                    self._position_ = args[0]._position_
                    
                    self._planar_graphics_type_ = args[0]._planar_graphics_type_
                    
                    return
                        
                elif isinstance(args[0], PlanarGraphics): # construct a Path using one PlanarGraphics element
                    # NOTE: 2021-04-26 11:14:44
                    # alll Path object must begin with a Move. Thus, if args[0]
                    # is NOT a Move, a default Move(x,y) will be prepended, with
                    # x and y given by the tuple elements in the 'position'
                    # parameter (itself being by default, 0,0)
                    self._objects_.append(args[0].copy())
                    
                    if not isinstance(self._objects_[0], Move):
                        x_ = self._objects_[0].x
                        y_ = self._objects_[0].y
                        self._objects_.insert(0, Move(x_, y_,
                                                      frameindex=frameindex, 
                                                      currentframe=currentframe))
                        
                    if all([isinstance(e, (Move, Line)) for e in self._objects_]):
                        if self._closed_:
                            self._planar_graphics_type_ = PlanarGraphicsType.polygon
                        
                        else:
                            self._planar_graphics_type_ = PlanarGraphicsType.polyline
                        
                    else:
                        self._planar_graphics_type_ = PlanarGraphicsType.path
                        
                elif isinstance(args[0], (tuple, list)) and len(args[0]): 
                    # the sole parameter is a sequence: this can be case 1.3 or
                    # case 1.4 (although Path behaves like a list of PlanarGraphics,
                    # it is dealt with above, as a copy constructor)
                    # NOTE: clauses for c'tor based on an iterable passed as sole
                    # arguments -- two subclauses:
                    if all([isinstance(p, PlanarGraphics) for p in args[0]]):
                        # NOTE: case 1.4
                        self.__init_from_planar_graphics_(*args[0])
                        
                    elif all([isinstance(c, (tuple, list)) and len(c) == 2 for c in args[0]]):
                        # NOTE: case 1.3 iterable of coordinate tuples
                        # e.g. as stored in image XML metadata, etc => Move (, Line) *
                        
                        for k, a in enumerate(args[0]):
                            if k == 0:
                                self._objects_.append(Move(a[0], a[1],
                                                           frameindex=frameindex, currentframe=currentframe))
                            else:
                                self._objects_.append(Line(args[0][k-1][0],
                                                           args[0][k-1][1],
                                                           a[0], a[1],
                                                           frameindex=frameindex, currentframe=currentframe))
                        
#                         self._objects_.append(Move(args[0][0], args[0][1], frameindex=frameindex, currentframe=currentframe))
#                         
#                         for a in args[1:]:
#                             self._objects_.append(Line(a[0], a[1], frameindex=frameindex, currentframe=currentframe))
                                
                        x = min([o.x for o in self if o is not None])
                        y = min([o.y for o in self if o is not None])
                        
                        self._position_ = (x,y)
                        
                        self._planar_graphics_type_ = PlanarGraphicsType.path
                        
                elif isinstance(args[0], QtGui.QPainterPath):
                    for k in range(args[0].elementCount()):
                        if args[0].elementAt(k).type == QtGui.QPainterPath.MoveToElement:
                            element = args[0].elementAt(k)
                            self._objects_.append(Move(element.x, element.y, 
                                                       frameindex=frameindex, 
                                                       currentframe=currentframe))
                            
                        elif args[0].elementAt(k).type == QtGui.QPainterPath.LineToElement:
                            element = args[0].elementAt(k)
                            if k == 0:
                                self._objects_.append(Move(element.x, element.y,
                                                           frameindex=frameindex, 
                                                           currentframe=currentframe))
                            else:
                                prevCoords = self._objects_[-1].destination()
                                self._objects_.append(Line(prevCoords[0], prevCoords[1],
                                                           element.x, element.y,
                                                           frameindex=frameindex, 
                                                           currentframe=currentframe))
                            
                        elif args[0].elementAt(k).type == QtGui.QPainterPath.CurveToElement:
                            element = args[0].elementAt(k)  # 2nd control point
                            c1 = args[0].elementAt(k+1)     # destination point
                            c2 = args[0].elementAt(k+2)     # 1st control point
                            if k == 0:
                                self._objects_.append(Move(element.x, element.y,
                                                           frameindex=frameindex, 
                                                           currentframe=currentframe))
                            else:
                                prevCoords = self._objects_[-1].destination()
                            # NOTE: do not delete -- keep for reference
                            #self.append(Cubic(x=c1.x, y=c1.y, c1x=c2.x, c1y=c2.y, c2x=element.x, c2y=element.y, frameindex=frameindex, currentframe=currentframe))
                                self._objects_.append(Cubic(prevCoords[0], prevCoords[1],
                                                            c1.x, c1.y, 
                                                            c2.x, c2.y, 
                                                            element.x, element.y, 
                                                            frameindex=frameindex, 
                                                            currentframe=currentframe))
                            
                        else: # do not parse "curve to data" elements, for now
                            continue 
                        
                    x = min([o.x for o in self if o is not None])
                    y = min([o.y for o in self if o is not None])
                    self._position_ = (x,y)
                    self._planar_graphics_type_ = PlanarGraphicsType.path
                    
            else: # args has > 1 element -> sequence of:
                if all([isinstance(a, (PlanarGraphics, tuple, list)) for a in args]):
                    # PlanarGraphics or coordinate pairs
                    # print(f"@{self.__class__.__name__}.__init__ from {len(args)} var positional arguments")
                    for k, a in enumerate(args):
                        if isinstance(a, PlanarGraphics):
                            aa = a.copy()
                            
                            if aa.frameIndices != frameindex:
                                aa.frameIndices = frameindex
                            
                            if aa._currentframe_ != self._currentframe_:
                                aa._currentframe_ = self._currentframe_ 
                            
                            self._objects_.append(aa)
                                
                        elif isinstance(a, (tuple, list)):
                            #print("Path.__init__ coordinates %d: %s" % (k, a))
                            # FIXME: 2021-04-25 14:47:19 Shouldn't this go?
                            # It is convenient to construct a Path from a list of
                            # coordinate tuples (i.e., one per path element)...
                            # The problem is how to interpret these, since several
                            # subclasses of PlanarGraphics use the SAME number of
                            # coordinate/parameter values.
                            if len(a) == 2:
                                if k == 0:
                                    self._objects_.append(Move(a[0], a[1], 
                                                            frameindex=frameindex, 
                                                            currentframe=self._currentframe_))
                                else: # k >  0
                                    self._objects_.append(Line(args[k-1][0], args[k-1][1], a[0], a[1], 
                                                            frameindex=frameindex, 
                                                            currentframe=self._currentframe_))
                                            
                            else:
                                raise TypeError("When constructing a Path, var-positional parameters must be PlanarGraphics objects or tuples of coordinates")
                            
                    # NOTE: 2018-01-20 09:51:23
                    # make sure Path begins with a Move
                    if not isinstance(self._objects_[0], Move):
                        self._objects_.insert(0,Move(0,0, 
                                                     frameindex = frameindex, 
                                                     currentframe=currentframe))
                        
                    self._planar_graphics_type_ = PlanarGraphicsType.path
                    
        if len(self):
            for o in self._objects_:
                o._currentframe_ = currentframe
            
            xx = [o.x for o in self._objects_ if o is not None and o.x is not None]
            
            yy = [o.y for o in self._objects_ if o is not None and o.y is not None]
            
            x = min(xx) if len(xx) else None
            y = min(yy) if len(yy) else None

            self._position_ = (x,y) if all(v is not None for v in (x,y)) else (0.,0.)

    def __reduce__(self):
        return __new_planar_graphic__, (self.__class__, 
                                        self._objects_, 
                                        self._ID_, 
                                        self.frameIndices, 
                                        self._currentframe_,
                                        self._planar_graphics_type_, 
                                        self._closed_,
                                        self._linked_objects_.copy(),
                                        self._position_)
    
    def _repr_pretty_(self, p, cycle):
        if cycle:
            p.text(f"{self.__class__.__name__}")
        else:
            p.text(f"{self.__class__.__name__}:")
            p.breakable()
            if len(self._objects_) > 6:
                for k in range(3):
                    p.pretty(self._objects_[k])
                p.text("\n...\n")
                for k in range(2, len(self._objects_)):
                    p.pretty(self._objects_[k])
            else:
                for o in self._objects_:
                    p.pretty(o)
            p.text("\n")

    def __repr__(self):
        ss = super(PlanarGraphics, self).__repr__()
        return ss
        
    def __str__(self):
        s = "\n ".join(["%d: %s" % (k, e.__str__()) for k,e in enumerate(self._objects_)])
        return "%s object:\n name %s\n path elements: \n %s" % (self.__class__, self._ID_, s)
        
    def __call__(self, path:typing.Optional[QtGui.QPainterPath]=None, 
                frame:typing.Optional[int]=None, closed:typing.Optional[bool]=None,
                connected:typing.Optional[bool]=False):
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
            path = QtGui.QPainterPath() # => return empty QPainterPath
            
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
                    
            #print(f"path elements {path.elementCount()}")
            if closePath:
                # NOTE: ALWAYS  operate on current state (be it the common one,
                # or the state associated with current frame)
                if frame is None:
                    state = self.currentState
                    
                else:
                    state = self.getState(frame)
                    
                if state: # and len(state):
                    path.lineTo(self._objects_[0].x, 
                                self._objects_[0].y) 
                
        return path
            
    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        
    def __getattr__(self, name):
        try:
            return object.__getattribute__(self, name)
        except:
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
            if not other.type & PlanarGraphicsType.allCursorTypes:
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
                
                if "cx" in s:#.__class__._planar_descriptors_:
                    s.cx += dx
                    
                if "c1x" in s:#.__class__._planar_descriptors_:
                    s.c1x += dx
                    
                if "c2x" in s:#.__class__._planar_descriptors_:
                    s.c2x += dx
                
                if "cy" in s:#.__class__._planar_descriptors_:
                    s.y += dy
                    
                if "c1y" in s:#.__class__._planar_descriptors_:
                    s.c1y += dy
                    
                if "c2y" in s:#.__class__._planar_descriptors_:
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
        
    def validateState(self, states):
        if not isinstance(states, (tuple, list)):
            return False
        
        return all([isinstance(state, Bunch) and all([hasattr(state, a) for a in element._planar_descriptors_]) for (state, element) in zip(states, self._objects_)])
            
    def validateStates(self, value):
        if not isinstance(value, dict):
            return False
        
        return all([isinstance(k, int) and self.validateState(state) for (k, state) in value.items()])
        
    def addState(self, state):
        """Adds a copy of state to each of its objects.
        Use with CAUTION.
        
        """
        if len(self._objects_) == 0:
            raise RuntimeError("This path object has no elements")
        
        if not isinstance(state, Bunch):
            raise TypeError("state expected to be a datatypes.Bunch; got %s instead" % type(state).__name__)
        
        if not self.validateState(state): # make sure state complies with this planar type
            raise TypeError("state %s does not contain the required descriptors %s" % (state, self._planar_descriptors_))
        
        if not hasattr(state, "z_frame"): # make sure state is conformant
            raise AttributeError("state is expected to have a z_frame attribute")
        
        for element, state in zip(self._objects_, states):
            element.addState(state.copy())
            
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
    def density(self):
        """The density of elements in this path.
        This is defined as the ratio :
        len(path)/int(path.curveLength())
        
        An empty path has density 0 by definition; for numerical rasons,
        a path with curveLength() == 0 will also return 0 (so a path
        composed entirely of Move points will have density 0 because
        the 'curve' is not defined between Move points)
        
        NOTE: the above formula includes Move elements in the path
        
        WARNING: It only makes sense for paths composed of LinearElements
        TODO: 2024-08-22 10:14:28
        adapt for paths composed of all primitives
        """
        cLen = int(self.curveLength())
        
        if cLen == 0:
            return 0
        
        return len(self)/cLen
    
    @property
    def elements(self):
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
        self._position_ = (self.x, self.y)
        
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
            frameObj = self.objectForFrame(self.currentFrame, visible=True)
            if frameObj:
                x = min(o.x for o in frameObj) # ← now, THIS is OK
            else:
                x = 0
        else:
            x = 0
        return x
        
    @x.setter
    def x(self, value):
        if len(self._objects_):
            # I need this cache below, to find out 'x'
            frameObj = self.objectForFrame(self.currentFrame, visible=True)
            if frameObj:
                # do nothing if obj not visible in currentFrame!
                x_ = min(o.x for o in frameObj)
                delta_x = value - x_
                states = self.getState(self.currentFrame, visible=True)
                for s in states:
                    for descr in s.keys():
                        if "x" in descr:
                            s[descr] += delta_x
                    
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
            frameObj = self.objectForFrame(self.currentFrame, visible=True)
            if frameObj:
                y = min(o.y for o in frameObj)
            else:
                y = 0
        else:
            y = 0
        return y
        
    @y.setter
    def y(self, value):
        if len(self._objects_):
            # find out current y from a frame cache; do nothing if not visible
            # in current frame
            frameObj = self.objectForFrame(self.currentFrame, visible=True)
            if frameObj:
                y_ = min(o.y for o in frameObj)
                delta_y = value - y_
                states = self.getState(self.currentFrame, visible=True)
                for s in states:
                    for descr in s.keys():
                        if "y" in descr:
                            s[descr] += delta_y
                    
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
        return self._planar_graphics_type_
#         if all([isinstance(e, (Move, Line)) for e in self._objects_]):
#             if len(self._objects_) == 2:
#                 return PlanarGraphicsType.line
#             
#             elif len(self._objects_) == 4:
#                 if self.closed:
#                     return PlanarGraphicsType.rectangle
#                 
#                 else:
#                     return PlanarGraphicsType.polyline
#             
#             else:
#                 if self.closed:
#                     return PlanarGraphicsType.polygon
#                 
#                 else:
#                     return PlanarGraphicsType.polyline
# 
#         return PlanarGraphicsType.path
        
    @property
    def states(self):
        """Returns a list of lists of states (one list per element)
        """
        ## FIXME should this not be a list of states (as paths) instead?
        ## as it is right now it returns a list with as many elements as there are
        ## elements in the path, which is confusing;
        ## a path's state should return a single-state path corresponding to the
        ## queried state
        #uniqe_frames = self.frameIndices
        
        return [p.states for p in self._objects_]
        
    @property
    def indexedStates(self):
        return [(k, p.states) for k, p in enumerate(self._objects_)]
        
    @property
    def currentFrame(self):
        self._currentframe_ = self._objects_[0].currentFrame
        return self._currentframe_
        
    @currentFrame.setter
    def currentFrame(self, value):
        if not isinstance(value, int):
            raise TypeError("expecting an int; got %s instead" % type(value).__name__)
        
        for e in self._objects_:
            e.currentFrame = value
            
        self._currentframe_ = self._objects_[0].currentFrame
            
    @property
    def currentState(self):
        """ A Path object containing the list of objects visible in the current
        state.
        
        As for the currentStateIndexed property, the states are taken from the
        PlanarGraphics elements that compose this Path object, provided that they
        have a state associated with the current frame. 
        
        Elements that do NOT have a state given the current frame are skipped. 
        
        In the extreme case where none of this Path's elements have a defined 
        state for the current frame, the returned list will be empty.
        
        """
        states = self.getState()
        
        return states
        
        
        #states = [p.getState(self._currentframe_) for p in self._objects_] # may be empty
        
        #return Path(states) if len(states) else None
        
    @property
    def closed(self):
        return self._closed_
    
    @closed.setter
    def closed(self, value):
        if not isinstance(value, bool):
            raise TypeError("value expected to be a boolean; got %s instead" % type(value).__name__)
        
        if value:
            self.append(Line(self._objects_[-1].x,
                             self._objects_[-1].y,
                             self._objects_[0].x, 
                             self._objects_[0].y))
            
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
        
        if state is None: # or len(state) == 0:
            warnings.warn("%s.qPoints(): Undefined state" % self.__class__.__name__, stacklevel=2)
            return [QtCore.QPointF()]
        
        points = list()
        for e in self._objects_:
            points.append(e.qPoint())
                
        return points
        
    def setParameter(self, name, value, frame=None):
        raise NotImplementedError("Path objects do not support this method")
    
    def propagateState(self, frame, destframes):
        """Propagate the states at specified frame, to destframes
        """
        
        for o in self:
            if isinstance(o, Path):
                o.propagateState(frame, destframes)
                
            else:
                if frame in o.frameIndices:
                    state = o.getState(frame)
                    o.propagateState(state, destframes)
                
    def hasStateForFrame(self, frame:typing.Optional[int]=None):
        return any([o.hasStateForFrame(frame) for o in self])
        
    def objectForFrame(self, frame:typing.Optional[int]=None,
               visible:typing.Optional[bool] = True) -> object:
        """Returns a new Path object with frame-specific decriptors.
        
        WARNING: Since this is a new Path object, and NOT a reference to the 
        current descriptor values, modyfing it does not affect the original
        
        Parameters:
        ========================
        frame: int (frame index); optional, default is current frame

        visible: bool, optional, deftault is True: only include PlanarGraphics
            objects that are visible in the specified frame
        
        """
        elements = [o for o in map(lambda x: x.objectForFrame(frame, visible=visible), self) if o is not None]
        if elements:
            ret = Path(elements)
            # NOTE: 2022-01-10 14:50:04
            # the below is REQUIRED as state may be frame-specific!
            ret.currentFrame = self.currentFrame
            return ret
        
    def getState(self, frame:typing.Optional[int]=None,
                 visible:typing.Optional[bool]=True) -> typing.Optional[list]:
        """Returns this Path elements' states for the specified frame.
        
        A state is defined for the specified frame if either:
        * its z_frame == frame
        * its z_frame is None
        
        """
        if frame is None:
            frame = self.currentFrame
            
        # NOTE: 2022-01-10 12:58:33
        # not sure why the line below returns a list of PlanarGraphics instead
        # of a list of Bunch objects!
        #obj_states = list(filter(lambda o: o.getState(frame, visible=visible), self))
        
        obj_states = list(o.getState(frame, visible=visible) for o in self)
        
        return list(filter(lambda o:o, obj_states))
        
    def removeState(self, value):
        for o in self._objects_:
            o.removeState(value)
            
    def controlPoints(self, frame=None, inPath:bool=False):
        ret = list()
        
        for o in self:
            ret += list(o.controlPoints(frame, True)) # pass inPath as True
            
        if inPath:
            ret = ret[1:]
            
        return tuple(ret)
        
    def controlPath(self, frame=None, inPath:bool=False):
        """Returns a Path that represents a polyline connecting all control points.
        """
        ret = Path()
        
        cp = self.controlPoints(frame, inPath)
        
        for k, p in enumerate(cp):
            if k == 0:
                ret.append(Move(p[0],p[1]))
                
            else:
                ret.append(Line(cp[k-1][0], cp[k-1][1], p[0], p[1]))
                
        return ret
        
    def fromControlPath(self, path, frame=None):
        if not isinstance(path, Path):
            raise TypeError("path argument expected to be a Path; got %s instead" % type(path).__name__)
        
        if frame is None:
            state = self.currentState
            
        else:
            state = self.getState(frame)
        
        if state is None: # or len(state) == 0:
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
                self.append(Move(element.x, element.y, 
                                 frameindex=frameindex, currentframe=currentframe))
                
            elif p.elementAt(k).type == QtGui.QPainterPath.LineToElement:
                element = p.elementAt(k)
                if len(self) == 0:
                    self.append(Move(element.x, element.y, 
                                     frameindex=frameindex, currentframe=currentframe))
                else:
                    prevElement = self._objects_[-1].destination()
                    self.append(Line(prevElement[0], prevElement[1],
                                     element.x, element.y, 
                                     frameindex=frameindex, currentframe=currentframe))
                    
            elif p.elementAt(k).type == QtGui.QPainterPath.CurveToElement:
                # BUG: 2024-08-26 22:26:12 FIXME
                # distribution of path elements to Cubc is wrong
                # also needs to jump over next two elements in the path
                element = p.elementAt(k)
                c1 = p.elementAt(k+1)
                c2 = p.elementAt(k+2)
                if len(self) == 0:
                    self.append(Move(element.x, c2y=element.y))
                else:
                    prevElement = self._objects_[-1].destination()
                        
                    self.append(Cubic(prevElement[0], prevElement[1],
                                      x=c1.x, y=c1.y, 
                                    c1x=c2.x, c1y=c2.y, 
                                    c2x=element.x, c2y=element.y, 
                                    frameindex=frameindex, currentframe=currentframe))
                
            #else: # do not parse curve to data elements
                #continue 

#NOTE: Only Move, Line and Cubic correspond to QPainterPath.Element 
PathElements = (Move, Line, Cubic, Quad, Arc, ArcMove) # "tier 1" elements: primitives that can be called directly

LinearElements = (Move, Line)

CurveElements = (Cubic, Quad, Arc, ArcMove)

Tier2PathElements = (Ellipse, Rect) # can be used as parameters for the GraphicsObject c'tor

Tier3PathElements = () # TODO: connectPath, addPath, addRegion, addPolygon, addText

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
    sig_planar_changed = Signal(name="sig_planar_changed")
    
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
            raise TypeError("planarobject expected to be a PlanarGraphics object or None; got %s instead" % type(planarobject).__name__)
        
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
        
def simplifyPath(path:Path, max_adjacent_points:int = 5, 
                 frame:typing.Optional[int] = None):
    """Simplifies a Path that consists of a long sequence of Move & Line points.
    
    The Path is simplified by removing sequence of points that differ in one coordinate
    only (and thus can be replaced by a single horizontal or vertical line).
    
    If necessary, sequences of adjacent points with different copordinates and 
    longer than max_adjacent_points are approximated by B-spline interpolation.
    
    NOTE: This is NOT an implementation of the Ramer–Douglas–Peucker algorithm.
    
    See signalprocessing.simplify_2d_shape()
    
    Parameters:
    ===========
    path: Path without nested paths; must be composed only of Move and Line elements.
    
    max_adjacent_points: int (default, 5) or None -- see signalprocessing.simplify_2d_shape()
    
    frame: None (default) or an int: the index of the frame for which the (xy) 
        coordinates of the Path are to  be used.
        
        When None, the path's current frame will be used
        
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
    
    # state = path.getState(frame)
    
    frameindices_array = np.array(path.frameIndices)
    
    if frame is None:
        frame = path.currentFrame
        xy = np.array([(o.x, o.y) for o in path if o.currentFrame == frame])
        
    elif frame in frameindices_array.flatten():
        xy = np.array([(o.x, o.y) for o in path if o.currentFrame in (frame, list(), tuple())]) # to include those elements that have framelesss states
        
    else:
        raise ValueError("frame %s does not appear to be linked with this object's states" % frame)
        
    # print(f"simplifyPath: xy.shape = {xy.shape}")
    

    xy_unique, xy_splines = sgp.simplify_2d_shape(xy, max_points = max_adjacent_points,
                                                  k = 3)
    
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
        # print(f"simplifyPath: spline_points_xy = {spline_points_xy}")
        
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
                                           &  (xy_unique[:,0] <= np.max(first_last_spline_points[k,:,0])) \
                                           &  (xy_unique[:,1] >= np.min(first_last_spline_points[k,:,1])) \
                                           &  (xy_unique[:,1] <= np.max(first_last_spline_points[k,:,1])) )[0]) \
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
                        ret.append(Cubic(spline_points_xy[spline_index][0][0],
                                         spline_points_xy[spline_index][0][1],
                                         spline_points_xy[spline_index][1][0],
                                         spline_points_xy[spline_index][1][1],
                                         spline_points_xy[spline_index][2][0],
                                         spline_points_xy[spline_index][2][1],
                                         spline_points_xy[spline_index][3][0],
                                         spline_points_xy[spline_index][3][1],
                                         ))
                        
                        
                    else: # been in this spline before, so skip
                        continue
                    
                    visited_splines.add(spline_index)
                    
                else: # not in a spline segement --> append a Line
                    ret.append(Line(xy_unique[k-1,0], 
                                    xy_unique[k-1,1],
                                    xy_unique[k,0],
                                    xy_unique[k,1]))
                    
    else:
        for k in range(xy_unique.shape[0]):
            if k == 0:
                element = Move(xy_unique[k,0], xy_unique[k,1])
                
            else:
                element = Line(xy_unique[k-1,0], xy_unique[k-1,1],
                               xy_unique[k,0],   xy_unique[k,1])

            ret.append(element)
                
            
    return ret


class GraphicsObjectLnF(object):
    """Default styles and colours for GraphicsObject objects in Scipyen.
    GraphicsObjects are used as frontends for PlanarGraphics (which define
    data cursors and landmarks such as ROIs and lines for the ImageViewer).
    
    The following LnF components are defined:
    
    For Cursor objects:
        line:   pen:    style           The cursor's main line and whiskers
                        color
                        cap
                        join
        
        label:  pen:    style           The cursor label
                        color
                        cap
                        join
                        
                brush:  style 
                        color (when style is a patter or bitmap)
                        gradient
                        texture
                        
                text:   font (fontFamily)
                        size (pointSize)
                                    
    For non-cursor objects (e.g ROIs, paths, etc):
        line:   pen:    style           The main line
                        color
                        cap
                        join
        
        point:  pen:    style           The end-of-line point # not implemented
                        color
                        cap
                        join
                        
                brush   style (see comments above)
                        color
                        gradient
                        texture
                        
                visible (bool)
                        
        label:  pen:    style       The label
                        color
                        cap
                        join
                            
                brush:  style (see comments above)
                        color
                        gradient
                        texture
                        
                text:   font (fontFamily)
                        size (pointSize)
                                    
        control_line:   pen:    style
                                color
                                cap
                                join
                        
        control_point:  pen:    style
                                color
                                cap
                                join
                                
                        brush:  style (see comments above)
                                color
                                gradient
                                texture
                                
    In addition, these components must reflect one of the following four possible
    states:
        
                    Selection state         Linked state
                    ====================================
                
    Normal              No                      No
    Selected            Yes                     No
    Linked              No                      Yes
    LinkedSelected      Yes                     Yes
        
    This :class: takes an orthogonal approach by pre-defining default values for 
    the components listed above, from which specific attributes of the object
    look and feel can be selected dynamically
    """
    
    # Defaults used for control lines and points
    control_styles = Bunch(
        brush_label     = Bunch(style = QtCore.Qt.SolidPattern), # any of QBrushStyle, QGradient, QPixmap, QImage
        brush_point     = Bunch(style = QtCore.Qt.SolidPattern),
        pen_text        = Bunch(style = QtCore.Qt.SolidLine, width = 1,
                                   cap = QtCore.Qt.RoundCap, join = QtCore.Qt.RoundJoin,
                                   ), # label text
        pen_line        = Bunch(style = QtCore.Qt.DotLine, width = 1,
                                  cap = QtCore.Qt.RoundCap, join = QtCore.Qt.RoundJoin,
                                  ), # lineart pen
        pen_point       = Bunch(style = QtCore.Qt.SolidLine, width = 1,
                                  cap = QtCore.Qt.RoundCap, join = QtCore.Qt.RoundJoin,
                                  ), # lineart point pen !
        )
        
    control_colors = Bunch(
        brush_label     = QtGui.QColor(200, 200, 210, 120),
        brush_point     = QtGui.QColor(200, 200, 210, 120),
        pen_text        = QtCore.Qt.black, # label text pen
        pen_line        = QtCore.Qt.lightGray,   # lineart pen
        pen_point       = QtGui.QColor(50, 100, 120),   # point fills (when used)
        )
    
    selection_styles = Bunch({
        False: Bunch(
            brush_label     = Bunch(style = QtCore.Qt.SolidPattern, gradient = None,
                                      texture = None, textureImage = None,
                                      alow_none = True,
                                      ), # label background
            brush_point     = Bunch(style = QtCore.Qt.SolidPattern, gradient = None,
                                      texture = None, textureImage = None,
                                      alow_none = True,
                                      ), # point background
            pen_text        = Bunch(style = QtCore.Qt.SolidLine, width = 1, 
                                      cap = QtCore.Qt.RoundCap, join = QtCore.Qt.RoundJoin,
                                      ), # label text pen
            pen_line        = Bunch(style = QtCore.Qt.DashLine, width = 1,
                                      cap = QtCore.Qt.RoundCap, join = QtCore.Qt.RoundJoin,
                                      ), # lineart pen
            pen_point       = Bunch(style = QtCore.Qt.DashLine, width = 1,
                                      cap = QtCore.Qt.RoundCap, join = QtCore.Qt.RoundJoin,
                                      ), # lineart pen
            ),
        True : Bunch(
            brush_label     = Bunch(style = QtCore.Qt.SolidPattern, gradient = None, 
                                      texture = None, textureImage = None,
                                      allow_none = True,
                                      ),
            brush_point     = Bunch(style = QtCore.Qt.SolidPattern, gradient = None, 
                                      texture = None, textureImage = None,
                                      allow_none = True,
                                      ),
            pen_text        = Bunch(style = QtCore.Qt.SolidLine, width = 1,
                                      cap = QtCore.Qt.RoundCap, join = QtCore.Qt.RoundJoin,
                                      ),
            pen_line        = Bunch(style = QtCore.Qt.SolidLine, width = 1,
                                      cap = QtCore.Qt.RoundCap, join = QtCore.Qt.RoundJoin,
                                      ),
            pen_point       = Bunch(style = QtCore.Qt.SolidLine, width = 1,
                                      cap = QtCore.Qt.RoundCap, join = QtCore.Qt.RoundJoin,
                                      ),
            ),
        })
        
    link_colors = Bunch({
        True: Bunch(
            brush_label     = QtCore.Qt.white, # label text background
            brush_point     = QtCore.Qt.lightGray, # label text background
            pen_text        = QtCore.Qt.black, # label text pen
            pen_line        = QtCore.Qt.red,   # lineart pen
            pen_point       = QtCore.Qt.red,   # point fills (when used)
            ),
        False : Bunch(
            brush_label     = QtCore.Qt.white,
            brush_point     = QtCore.Qt.lightGray, # label text background
            pen_text        = QtCore.Qt.black,
            pen_line        = QtCore.Qt.magenta,
            pen_point       = QtCore.Qt.magenta,
            ),
        })
        
    pointsize = {"standard": 5, "control": 10}
    
    # won't work: when this code is executed there is no QGuiApplication running yet
    # therefore must be called in GUI client code
    #font = QtWidgets.QApplication.font()
    
    @staticmethod
    def pen(graphic="pen_line", control:bool=False, selected:bool=False, 
            linked:bool=False):
        if graphic not in ("pen_line", "pen_point", "pen_text"):
            raise ValueError("Unexpected graphic item %s; should've been 'pen_line', 'pen_point' or 'pen_text'" % graphic)
        
        if control:
            color = GraphicsObjectLnF.control_colors[graphic]
            style = GraphicsObjectLnF.control_styles[graphic]["style"]
            cap   = GraphicsObjectLnF.control_styles[graphic]["cap"]
            join  = GraphicsObjectLnF.control_styles[graphic]["join"]
        else:
            color = GraphicsObjectLnF.link_colors[linked][graphic]
            style = GraphicsObjectLnF.selection_styles[selected][graphic]["style"]
            cap   = GraphicsObjectLnF.selection_styles[selected][graphic]["cap"]
            join  = GraphicsObjectLnF.selection_styles[selected][graphic]["join"]
            
        ret = QtGui.QPen(color)
        
        if isinstance(style, QtCore.Qt.PenStyle):
            ret.setStyle(style)
            
        elif isinstance(style, dict):
            dashPattern = get(style, "dashes", [])
            dashOffset = get(style, "offset", 0.)
            if len(dashPattern):
                ret.setDashPattern(dashPattern)
                ret.setDashOffset(dashOffset)
            else:
                ret.setTyle(QtCore.Qt.SolidLine)
                
        elif isinstance(style, (tuple, list)):
            if len(style)%2:
                ret.setDashPattern(list(style[:-1]))
            else:
                ret.setDashPattern(style)
                
        ret.setCapStyle(cap)
        ret.setJoinStyle(join)
    
        return ret
    
    @staticmethod
    def brush(graphic="brush_label", control:bool=False, selected:bool=False, linked:bool=False):
        if graphic not in ("brush_label", "brush_point"):
            raise ValueError("Unexpected graphic item %s; should've been 'brush_label' or 'brush_point'" % graphic)
        
        if control:
            color = GraphicsObjectLnF.control_colors[graphic]
            style = GraphicsObjectLnF.control_styles[graphic]["style"]
        else:
            color = GraphicsObjectLnF.link_colors[linked][graphic]
            style = GraphicsObjectLnF.selection_styles[selected][graphic]["style"]
          
        if isinstance(color, (QtGui.QColor, QtCore.Qt.GlobalColor)):
            if isinstance(style, (QtGui.QPixmap, QtCore.Qt.BrushStyle)):
                ret = QtGui.QBrush(color, style)
                
            elif isinstance(style, (QtGui.QGradient, QtGui.QImage, QtGui.QBrush)):
                ret = QtGui.QBrush(style)
                
            else:
                ret = QtGui.QBrush(color, QtCore.Qt.SolidPattern)
                
        elif isinstance(style, (QtGui.QGradient, QtGui.QPixmap, QtGui.QImage, QtGui.QBrush, QtCore.Qt.BrushStyle)):
            ret = QtGui.QBrush(style)
            
        else:
            ret = QtGui.QBrush(QtCore.Qt.NoBrush)
            
        return ret
            
            
class GraphicsObject(QtWidgets.QGraphicsObject):
    """Frontend for PlanarGraphics objects using the Qt Graphics Framework.
    TODO
    FIXME Logic for building/editing ellipse, cubic, quad ROIs
    FIXME check cachedPath logic
    
    NOTE: 2019-03-09 10:05:30
    the correspondence between the display object and the PlanarGraphics object
    is to be managed by an instance of Planar2QGraphicsManager
        
    NOTE: 2018-01-17 21:56:23
    currentframe and framesVisibility __init__() parameters cached to be 
    available when exiting build mode (i.e., from within _finalizeShape_)
         
         
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
    defined in this module. In turn the PlanarGraphics objects are the "backend" 
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
    calling the appropriate addPlanarGraphics method in ImageViewer) will generate
    a GraphicsObject frontend in that image viewer's scene.
    
    From the GUI, the user can manipulate the frontend directly (mouse and key
    strokes) whereas the backends can only be are manipulated indirectly (via their 
    frontends).
    """
    
    # this is for Qt Graphics View Framework RTTI logic
    Type = QtWidgets.QGraphicsItem.UserType + PlanarGraphicsType.allObjectTypes
    
    #signalPosition = Signal(int, str, "QPointF", name="signalPosition")
    signalPosition = Signal(str, QtCore.QPointF, name="signalPosition")
    
    # used to notify the cursor manager (a graphics viewer widget) that this cursor has been selected
    selectMe = Signal(str, bool, name="selectMe") 
    
    signalGraphicsObjectPositionChange = Signal(QtCore.QPointF, name="signalGraphicsObjectPositionChange")
    
    # it is up to the cursor manager (a graphics viewer widget) to decide what 
    # to do with this (i.e., what menu & actions to generate)
    requestContextMenu = Signal(str, QtCore.QPoint, name="requestContextMenu")
    
    signalROIConstructed = Signal(int, str, name="signalROIConstructed")
    
    signalBackendChanged = Signal(object, name="signalBackendChanged")
    
    signalIDChanged = Signal(str, name="signalIDChanged")
    
    # 
    # NOTE: 2021-05-12 14:29:39 look-and-feel matrix:
    #           isolated/linked                   selected/unselected
    # what is   ----------------------------------------------------------------
    # changed:  line pen color                    line (pen) style and width   
    #           label (text) pen color(*)  
    #           label background brush color(**)  label background brush style(**)
    #
    # 
    #          
    # (*)  text pen style is always the solid line
    # (**) only for opaque labels
    
    # NOTE: 2021-05-12 14:33:03
    # for cursor and roi lines use QPen; for label background use QBrush
    # Pen and Brush style changes between selected/unselected item (except for text pen)
    # Pen and Brush color changes between linked and not linked items
    
    # NOTE: 2021-05-12 14:34:27
    # a "linked" item has a backend linked with the backed of another item
    # ATTENTION the linkage is in the backend; the item doesn't necessarily know
    # about the other backends (although it can gain access)
    
    
    # NOTE: 2021-07-03 12:43:10 APPEARANCE
    # Overhaul of styling - we define five possible states:
    # 1. unlinked unselected
    # 2. unlinked selected
    # 3. linked unselected
    # 4. linked selected
    # 5. control - for drawing "control path" line and points of ROIs in edit mode
    # 
    # Each state has the following drawn parts:
    # line_pen (color, style, cap, join, width)  -  pen for the line art
    # label_pen (color, style, cap, join, width) -  pen for the label text
    # point_pen (color, style, cap, join, width) -  pen for the control points
    # label_brush (style: pattern/color/gradient/texture) - brush for the label text background
    # point_brush (style: pattern/color/gradient/texture) - brush for the control points
    # 
    #
    # Any Cursor or ROI is drawn in one of the styles 1-4 above;
    # The decision of painting the item as "selected" or "unselected" is taken 
    # inside self.paint by interrogating the selected status with 
    # self.isSelected() method inherited from QGraphicsItem.
    #
    # The decision of painting the item as "linked" or "unlinked" is taken outside
    # paint at the time when the PlanarGraphics backend is linked/unlinked from
    # other PlanarGraphics.
    #
    # The same backend can be displayed by more than one frontend (GraphicsObject)
    # which are (should be) shown in different scenes with the same geometry.
    # The frontends that all display the same backend are NOT considered "linked".
    #
    #
    
    # NOTE: 2021-07-04 09:36:25 use plain dict here - avoid the Bunch
    # overhead since we don't necessarily need to observe the changes
    #

        
    def __init__(self, 
                 obj=None, 
                 labelShowsPosition=True, 
                 showLabel=True,
                 parentWidget=None,
                 roundCursorPoint=True):
                 
        """
        Named parameters:
        =================
        obj: (optional) a PlanarGraphics object or None (default)
                    
            When 'obj' is None this triggers the interactive drawing logic
            (to build the PlanarGraphics shape using the GUI).
                
        labelShowsPosition: bool (default is True)
        
        showLabel: bool (default is True)
        
        parentWidget: QtWidget (GraphicsImageViewerWidget) or None (default)
        
        roundCursorPoint: bool (default is True) - specifies how a Point cursor
            and the 'target' for a Point and Crosshair cursor are drawn.
            
            When True (the default), these will be drawn as an ellipse (circle).
            
            When False, these will be drawn as rectangles
        
        """
        if not isinstance(obj, (PlanarGraphics, type(None))):
            raise TypeError("First parameter expected a PlanarGraphics or None; got %s instead" % type(obj).__name__)

        super(QtWidgets.QGraphicsObject, self).__init__()

        self._backend_ = obj
        
        if not isinstance(parentWidget, QtWidgets.QWidget) and type(parentWidget).__name__ != "GraphicsImageViewerWidget":
            raise TypeError("'parentWidget' expected to be a GraphicsImageViewerWidget; got %s instead" % (type(self._parentWidget_).__name__))
        
        self._parentWidget_             = parentWidget
        self._labelShowsCoordinates_    = labelShowsPosition
        self._showLabel_                = showLabel
        self._roundCursor_              = roundCursorPoint
        # NOTE: this is the actual string used for label display; 
        # it may be suffixed with the position if labelShowsPosition is True
        self._displayStr_= "" 
        
        # generates self.controlLnF, self.basicLnF and self.linkedLnF
        self._setAppearance_()
        # NOT: 2017-11-24 22:30:00
        # assign this early
        # this MAY be overridden in __parse_parameters__
        #self._planar_graphics_type_ = objectType # an int or enum !!!
        

        # NOTE: 2018-01-17 15:33:58
        # used in buildMode or editMode; applies to non-cursor objects only
        #self._c_shape_point         = -1
        self._c_activePoint         = -1 # shape point editing - used in edit & build modes
        self._c_activeControlPoint  = -1 # path control point editing; valid values are 0 and 1
        self._control_points        = [None, None]  # used in curve (cubic, quad) segment building for path ROIs
        self._hover_point           = None    # because a null QPointF is still valid:
        self._constrainedPoint      = None
        self._movePoint             = False
        self._cachedPath_ = Path() # used in build mode
        
        # NOTE: 2017-06-29 08:32:11
        # flags when a new position change sequence has begun (the previous 
        # sequence, if any, ended with a mouse release event)
        self._positionChangeHasBegun = False
        
        
        # FIXME: 2021-05-04 11:08:40 get rid of this
        # NOTE: 2017-11-23 00:08:04 
        # unlike non-cursor types, cursors are NOT back-ended by a QGraphicsItem
        # but rather directly painted by self.paint() method
        # the flag below toggles the cursor painting ON / OFF
        # TODO sync me with current frame cf self._frameindex
        self.__objectVisible__ = True
        
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
        
        self._setDisplayStr_()
                    
        # FIXME: 2021-05-04 11:11:19 One backend per frontend!
        # NOTE: 2018-01-26 10:07:28
        # use a list of backends !!!
        #self._linkedGraphicsObjects = list()
                
        #self._isLinked = len(self._linkedGraphicsObjects)>0
        
        self.setFlags(QtWidgets.QGraphicsItem.ItemIsMovable                 | \
                      QtWidgets.QGraphicsItem.ItemIsFocusable               | \
                      QtWidgets.QGraphicsItem.ItemIsSelectable              | \
                      QtWidgets.QGraphicsItem.ItemSendsGeometryChanges      | \
                      QtWidgets.QGraphicsItem.ItemSendsScenePositionChanges)

        self.setAcceptHoverEvents(True)
        
        #self.setBoundingRegionGranularity(0.5)
        
        self._shapeIsEditable_      = False # control point editing
        self._movable_              = True # moveable by mouse or keyboard
        self._editable_             = True # switching to edit mode allowed
        self._transformable_        = False # rotation & skewing
        self._opaqueLabel_          = True
        self._curveBuild_           = False
        self._buildMode_            = self._backend_ is None
        
        if self._backend_ is not None:
            #if isinstance(self._backend_, (CrosshairCursor, PointCursor)) or \
                #self._backend_.type & (PlanarGraphicsType.crosshair_cursor | PlanarGraphicsType.point_cursor):
                #self.setBoundingRegionGranularity(0.5)
                
            self.__objectVisible__  = len(self._backend_.frameIndices)==0 or self._backend_.hasStateForFrame()
            
            if self not in self._backend_.frontends:
                self._backend_.frontends.append(self)
            
        self._makeObject_() 
    
        if isinstance(self._backend_, PlanarGraphics) and self._backend_.hasStateForFrame():
            self.setPos(self._backend_.x, self._backend_.y)
                    
        self.update()
        
    def __str__(self):
        return "%s, type %s, backend %s" \
            % (self.__repr__(), type(self.backend).__name__, self.backend.__repr__())
            
    def _setAppearance_(self, cosmeticPen:bool=True):
        """Sets up appearance parameters based on defaults set in GraphicsObjectLnF"""
        self.controlLnF = Bunch({"pen": Bunch({"line": GraphicsObjectLnF.pen(graphic ="pen_line", 
                                                                            control=True),
                                               "text": GraphicsObjectLnF.pen(graphic="pen_text",
                                                                            control=True),
                                               "point": GraphicsObjectLnF.pen(graphic="pen_point",
                                                                            control=True)}), 
                                 "brush": Bunch({"text": GraphicsObjectLnF.brush(graphic="brush_label",
                                                                                        control=True),
                                                 "point": GraphicsObjectLnF.brush(graphic="brush_point",
                                                                                        control=True)}),
                                "font":QtWidgets.QApplication.font(),
                                "pointsize": GraphicsObjectLnF.pointsize["control"]
                                })
        
        self.basicLnF = Bunch({False: Bunch({"pen": Bunch({"line" : GraphicsObjectLnF.pen(graphic="pen_line"),
                                                           "text":  GraphicsObjectLnF.pen(graphic="pen_text"),
                                                           "point": GraphicsObjectLnF.pen(graphic="pen_point")
                                                           }),
                                             "brush": Bunch({"text": GraphicsObjectLnF.brush(graphic="brush_label"),
                                                            "point": GraphicsObjectLnF.brush(graphic="brush_point")
                                                            }),
                                             "font":QtWidgets.QApplication.font(),
                                             "pointsize": GraphicsObjectLnF.pointsize["standard"]
                                            }), 
                                            
                               True: Bunch({"pen": Bunch({"line" : GraphicsObjectLnF.pen(graphic="pen_line",
                                                                                        selected=True),
                                                           "text": GraphicsObjectLnF.pen(graphic="pen_text",
                                                                                        selected=True),
                                                           "point": GraphicsObjectLnF.pen(graphic="pen_point",
                                                                                        selected=True)
                                                           }),
                                            "brush": Bunch({"text": GraphicsObjectLnF.brush(graphic="brush_label",
                                                                                            selected=True),
                                                            "point": GraphicsObjectLnF.brush(graphic="brush_point",
                                                                                                selected=True)
                                                            }),
                                            "font":QtWidgets.QApplication.font(),
                                            "pointsize" : GraphicsObjectLnF.pointsize["standard"],
                                            }),
                                })
                                    
        self.linkedLnF  = Bunch({False: Bunch({"pen": Bunch({"line" : GraphicsObjectLnF.pen(graphic="pen_line",
                                                                                 linked=True),
                                                            "text": GraphicsObjectLnF.pen(graphic="pen_text",
                                                                                                    linked=True),
                                                            "point": GraphicsObjectLnF.pen(graphic="pen_point",
                                                                                                    linked=True),
                                                            }),
                                                "brush": Bunch({"text": GraphicsObjectLnF.brush(graphic="brush_label",
                                                                                                linked=True),
                                                                "point": GraphicsObjectLnF.brush(graphic="brush_point",
                                                                                            linked=True)
                                                                }),
                                                "font":QtWidgets.QApplication.font(),
                                                "pointsize": GraphicsObjectLnF.pointsize["standard"]
                                                }),
                    
                                True:  Bunch({"pen": Bunch({"line" : GraphicsObjectLnF.pen(graphic="pen_line",
                                                                                        linked=True,
                                                                                        selected=True),
                                                            "text": GraphicsObjectLnF.pen(graphic="pen_text",
                                                                                                    linked=True,
                                                                                                    selected=True),
                                                            "point": GraphicsObjectLnF.pen(graphic="pen_point",
                                                                                                    linked=True,
                                                                                                    selected=True)
                                                            }),
                                            "brush": Bunch({"text": GraphicsObjectLnF.brush(graphic="brush_label",
                                                                                            linked=True,
                                                                                            selected=True),
                                                            "point": GraphicsObjectLnF.brush(graphic="brush_point",
                                                                                                    linked=True,
                                                                                                selected=True)
                                                            }),
                                            "font":QtWidgets.QApplication.font(),
                                            "pointsize": GraphicsObjectLnF.pointsize["standard"],
                                            })
                                })
                         
    @safeWrapper
    def _defaultLinePen(self, selected:bool=False, linked:bool=False, cosmetic:bool=True):
        pen = QtGui.QPen(self.link_colors["%s" % linked].pen,
                         self.lnf_default_selection_styles_default["%s" % selected].pen.style,
                         self.lnf_default_selection_styles_default["%s" % selected].pen.width,
                         self.lnf_default_selection_styles_default["%s" % selected].pen.cap,
                         self.lnf_default_selection_styles_default["%s" % selected].pen.join,
                         )
        
        pen.setCosmetic(cosmetic)
        
        return pen
    
    @safeWrapper
    def _defaultPointBrush(self, selected:bool=False, linked:bool=False):
        brush = QtGui.QBrush(QtGui.QColor(self.link_colors["%s" % linked].point).setAlpha(self.lnf_default_selection_styles_default["%s" % selected].pointBrushAlpha),
                             self.lnf_default_selection_styles_default["%s" % selected].point.style,
                             )
        
        return brush
        
    @safeWrapper
    def _defaultTextPen(self, selected:bool=False, linked:bool=False, cosmetic:bool=True):
        pen = QtGui.QPen(self.link_colors["%s" % linked].text,
                         self.lnf_default_selection_styles_default["%s" % selected].text.style,
                         self.lnf_default_selection_styles_default["%s" % selected].text.width,
                         self.lnf_default_selection_styles_default["%s" % selected].text.cap,
                         self.lnf_default_selection_styles_default["%s" % selected].text.join,
                         )
        
        pen.setCosmetic(cosmetic)
        
        return pen
    
    @safeWrapper
    def _defaultLabelBrush(self, selected:bool=False, linked:bool=False):
        brush = QtGui.QBrush(self.link_colors["%s" % linked].brush,
                             self.lnf_default_selection_styles_default["%s" % selected].brush.style,
                             )
        
        return brush
        
    @safeWrapper
    def _defaultControlLinePen(self, cosmetic:bool=True):
        pen = QtGui.QPen(self.lnf_control_default.pen.color,
                         self.lnf_control_default.pen.style,
                         self.lnf_control_default.pen.width,
                         self.lnf_control_default.pen.cap,
                         self.lnf_control_default.pen.join,
                         )
        
        pen.setCosmetic(cosmetic)
        
        return pen
    
    @safeWrapper
    def _defaultControlPointPen(self, cosmetic:bool=True):
        pen = QtGui.QPen(self.lnf_control_default.point.color,
                         self.lnf_control_default.point.style,
                         self.lnf_control_default.point.width,
                         self.lnf_control_default.point.cap,
                         self.lnf_control_default.point.join,
                         )
        
        pen.setCosmetic(cosmetic)
        
        return pen
    
    @safeWrapper
    def _defaultControlPointBrush(self):
        brush = QtGui.QBrush(self.lnf_control_default.brush.color,
                             self.lnf_control_default.brush.style,
                             )
        
        return brush
        
    @safeWrapper
    def _defaultControlTextPen(self, cosmetic:bool=True):
        pen = QtGui.Pen(self.lnf_control_default.text.color,
                        self.lnf_control_default.text.style,
                        self.lnf_control_default.text.width,
                        self.lnf_control_default.text.cap,
                        self.lnf_control_default.text.join,
                        )
        
        pen.setCosmetic(cosmetic)
        
        return pen
        
    @safeWrapper
    def _defaultControlLabelBrush(self):
        brush = QtGui.QBrush(self.lnf_control_default.brush.color,
                             self.lnf_control_default.brush.style,
                             )
        
        return brush
        
    def _setDisplayStr_(self, value:str=None):
        """Constructs the label string.
        
        Value may be an empty string
        """
        nameStr = value if isinstance(value, str) else self._backend_.name if isinstance(self._backend_, PlanarGraphics) else ""

        if self._labelShowsCoordinates_ and isinstance(self._backend_, Cursor):
            state = self._backend_.currentState
            if state:
                if isinstance(self._backend_, VerticalCursor):
                    nameStr += ": %g" % state.x
                elif isinstance(self._backend_, HorizontalCursor):
                    nameStr += ": %g" % state.y
                else:
                    nameStr += ": %g, %g" % (state.x, state.y)
                            
        self._displayStr_ = nameStr
        
    @safeWrapper
    def _updateLabelRect_(self):
        """Calculates label bounding rectangle
        """
        if len(self._displayStr_) > 0:
            fRect = self._parentWidget_.fontMetrics().boundingRect(self._displayStr_)
            self._labelRect.setRect(fRect.x(), fRect.y(), fRect.width(), fRect.height())

        else:
            self._labelRect  = QtCore.QRectF() # a null rect
        
    def _finalizeShape_(self):
        """Creates the _graphicsShapedItem, an instance of QGraphicsItem.
        Used only by non-cursor types, after exit from build mode.
        Relies on self._cachedPath_ which is a PlanarGraphics Path object. Therefore
        if makes inferences from self._planar_graphics_type_ and the number of elements in
        self._cachedPath_
        """
        #if self._planar_graphics_type_ & PlanarGraphicsType.allCursorTypes:
        if isinstance(self._backend_, Cursor):
            # NOTE: do NOT use _graphicsShapedItem for cursors !!!
            return
            
        else:#FIXME in build mode there is no _backend_; we create it here from the cached path
            #NOTE: for non-cursors, cachedPath is generated in build mode, or in
            #NOTE:  __parse_parameters__()
            # FIXME 2021-05-05 10:03:09 _planar_graphics_type_ it NOT used anymore!
            if len(self._cachedPath_):
                if self._backend_ is None:
                    # NOTE: 2018-01-23 20:20:38
                    # needs to create particular backends for Rect and Ellipse
                    # because self._cachedPath_ is a generic Path object
                    # (see __parse_parameters__)
                    if self._planar_graphics_type_ == PlanarGraphicsType.rectangle:
                        self._backend_ = Rect(self._cachedPath_[0].x,
                                             self._cachedPath_[0].y,
                                             self._cachedPath_[1].x-self._cachedPath_[0].x,
                                             self._cachedPath_[1].y-self._cachedPath_[0].y)
                        
                    elif self._planar_graphics_type_ == PlanarGraphicsType.ellipse:
                        self._backend_ = Ellipse(self._cachedPath_[0].x,
                                                self._cachedPath_[0].y,
                                                self._cachedPath_[1].x-self._cachedPath_[0].x,
                                                self._cachedPath_[1].y-self._cachedPath_[0].y)
                        
                        
                    else:
                        self._backend_ = self._cachedPath_.copy()
                        
                super().setPos(self._backend_.pos)
                
                self._buildMode_ = False
                self._control_points = [None, None]
                
                self._hover_point = None
            
                self.signalROIConstructed.emit(self.objectType, self.name)
                
                if self._backend_ is not None:
                    self._backend_.frontends.append(self)
            
            else:
                # no cached path exists
                self.signalROIConstructed.emit(0, "")
        
        self.update()

    def _makeObject_(self):
        """Generates the rendered graphics components.
        """
        if self._backend_ is None:
            return

        if isinstance(self._backend_, Cursor):
            self._makeCursor_()
            
        else:
            self._makeROI_()
            
    def _makeROI_(self):
        if self._buildMode_:
            return
        
        self.__updateCachedPathFromBackend__() # to make sure control points stay within scene's rectangle

        self.update()
        
    def _makeCursorLines_(self, state:dict, vert:bool=True, horiz:bool=True):
        """Draws the main cursor lines.
        state: dict (or Bunch) with x, y, height and width attributes (see Cursor)
        vert, horiz: bool (by default, both True) 
        
            Which line to draw:
            \   Cursor  Vertical    Horizontal  Crosshair   Point(*)
             \  type:
            ===================================================================
            vert:       True        False       True        False
            horiz:      False       True        True        False
            
        (*) This function is a noop when called with both vert and horiz set as 
        False - therefore it doesn't need to be called for a Point cursor
        """
        ## NOTE: 2018-01-18 15:16:55
        ## THE CORRECT WAY TO DRAW THE CURSOR LINES is by mapping the coordinates
        # of the PlanarGraphics backend object from scene (where they are defined)
        # to the coordinate system of the actual graphics object (in this case, 
        # the line)
        # 
        if not isinstance(self._backend_, Cursor):
            return
        
        if vert:
            self._vline = QtCore.QLineF(self.mapFromScene(QtCore.QPointF(state.x, 0)), 
                                        self.mapFromScene(QtCore.QPointF(state.x, state.height)))
                
        if horiz:
            self._hline = QtCore.QLineF(self.mapFromScene(QtCore.QPointF(0, state.y)), 
                                        self.mapFromScene(QtCore.QPointF(state.width, state.y)))

    def _makeCursorWhiskers_(self, state:dict, vert:bool=False, horiz:bool=False):
        """Draws the whisker bars orthogonal to the main cursor line(s)
        state: dict (or Bunch) with x, y, xwindow and ywindow attributes (see Cursor)
        vert:  draws the (horizontal) whisker for the vertical main line (horizontal whisker bar)
        horiz: draws the (vertical) whisker for horizontal main line (vertical whisker bar)
        
        CAUTION Semantics is different from that in _makeCursorLines_:
            Which whiskers to draw:
            \   Cursor  Vertical    Horizontal  Crosshair(*)   Point
             \  type:
            ===================================================================
            vert:       False       True        False          True
            horiz:      True        False       False          True
            
        (*) when both are False, this is a noop; best to avoid calling it for a
        Crosshair cursor
        """
        if not isinstance(self._backend_, Cursor):
            return
        
        if not vert:
            self._vwbar = QtCore.QLineF(self.mapFromScene(QtCore.QPointF(state.x, 
                                                                         state.y - state.ywindow/2)),
                                        self.mapFromScene(QtCore.QPointF(state.x,
                                                                         state.y + state.ywindow/2)))
                                        
        if not horiz:
            self._hwbar = QtCore.QLineF(self.mapFromScene(QtCore.QPointF(state.x - state.xwindow/2,
                                                                         state.y)), 
                                        self.mapFromScene(QtCore.QPointF(state.x + state.xwindow/2,
                                                                         state.y)))
        
    def _makeCursor_(self):
        """Draws cursor.
        Creates the graphic components, which are rendered by __paint__
        """
        state = self._backend_.currentState
        
        if state is None: # or len(state) == 0:
            return
        
        self.prepareGeometryChange() # inherited from QGraphicsObject
        
        try:
            #NOTE: 2018-01-16 22:20:38 API change:
            # do NOT store our own graphics descriptors any more; use backend properties
            # getters for the planar descriptors; 
            # ATTENTION backend descriptors are in scene coordinates; therefore they 
            # need to be mapped back on this item's coordinates (e.g. using 
            # map[...]FromScene family of functions
            # 
            # the access to the backend's planar descriptors always reads values 
            # from the current descriptor state of the backend, that is, either the
            # common state, or the state associated with the current image frame 
            # (for a data "volume") is the backend has frame-state associations
            
            # NOTE: 2021-05-05 09:34:59
            # _vline and _hline are the main cursor lines
            # _hwbar and _vwbar are their respective "whiskers" orthogonal to 
            # the main lines
            # _crect is the actual point for the point cursor
            # _wcrect is the "target" rect for both point and crosshair cursors
            
            # NOTE: 2021-05-06 20:54:14
            # to draw an ellipse (circle) instead of a rectangle (square) create
            # and use a user-configurable flag, then get the painter draw an 
            # ellipse using these rectangle coordinates by calling drawEllipse(...)
            # instead of drawRects(), in self.__paint__()
            # this is what the new constructor parameter roundCursorPoint sets.
            
            self._updateLabelRect_()
            
            vert = isinstance(self._backend_, (VerticalCursor, CrosshairCursor)) or \
                    self._backend_.type & (PlanarGraphicsType.vertical_cursor | PlanarGraphicsType.crosshair_cursor)
                    
            horiz = isinstance(self._backend_, (HorizontalCursor, CrosshairCursor)) or \
                    self._backend_.type & (PlanarGraphicsType.horizontal_cursor | PlanarGraphicsType.crosshair_cursor)
            
            if not isinstance(self._backend_, PointCursor) and \
                not self._backend_.type & PlanarGraphicsType.point_cursor:
                self._makeCursorLines_(state, vert, horiz) # avoid noop call
                
            if not isinstance(self._backend_, CrosshairCursor) and \
                not self._backend_.type & PlanarGraphicsType.crosshair_cursor:
                    self._makeCursorWhiskers_(state, vert, horiz)
            
            if isinstance(self._backend_, (CrosshairCursor, PointCursor)) or \
                self._backend_.type & (PlanarGraphicsType.crosshair_cursor | PlanarGraphicsType.point_cursor):
                # the "target" rect, component of the point cursor and of the crosshair cursor
                self._wrect = QtCore.QRectF(self.mapFromScene(QtCore.QPointF(state.x - state.xwindow/2,
                                                                            state.y - state.ywindow/2)),
                                            self.mapFromScene(QtCore.QPointF(state.x + state.xwindow/2,
                                                                            state.y + state.ywindow/2)))
                                            
            if isinstance(self._backend_, PointCursor) or \
                self._backend_.type & PlanarGraphicsType.point_cursor:
                # component of the point cursor (central rect)
                self._crect = QtCore.QRectF(self.mapFromScene(QtCore.QPointF(state.x - state.radius,
                                                                            state.y - state.radius)),
                                            self.mapFromScene(QtCore.QPointF(state.x + state.radius,
                                                                            state.y + state.radius)))
                
            super().update()
            
        except Exception as exc:
            traceback.print_exc()
        
    @property
    def isLinked(self):
        return self._backend_.isLinked
        #return self._backend_ and self in self._backend_.frontends and len(self._backend_.frontends) > 1
    
    # NOTE: 2017-06-30 12:04:24
    # TODO: functions/event handlers to implement/overload:
    # TODO OPTIONAL: collidesWithItem()
    # TODO OPTIONAL: contains() -- relies on shape()
    # TODO OPTIONAL: focusInEvent, focusOutEvent hoverEnterEvent hoverLeaveEvent 
    # TODO OPTIONAL: keyReleaseEvent (to move it by keyboard)
    # TODO OPTIONAL: hoverMoveEvent -- optional
    
    @safeWrapper
    def getShapePathElements(self):
        if isinstance(self._backend_, Cursor) or not self.hasState:
            return
        
        path = self.graphicsItem.shape() #  a QPainterPath with subpaths!
        
        elements = [path.elementAt(k) for k in range(path.elementCount())]
        
        # find subpaths: subpaths always begin with a moveTo element
        
        pathBreaks = [k for (k,e) in enumerate(elements) if e.type == QtGui.QPainterPath.MoveToElement]
        pathBreaks.append(len(elements))
        
        paths = [[e for e in elements[slice(pathBreaks[k], pathBreaks[k+1])]] for k in range(len(pathBreaks)-1)]
            
        return paths
    
    @safeWrapper
    def __updateCachedPathFromBackend__(self):
        """No mapping transformations here, as the cached path is a copy of the
        _backend_'s state associated with the current frame.
        """
        if isinstance(self._backend_, (Cursor, type(None))):
            return
        self._cachedPath_ = self._backend_.controlPath()
        
    def show(self):
        self.setVisible(True)
        
    def hide(self):
        self.setvibisle(False)
    
    #@safeWrapper
    def boundingRect(self):
        """Mandatory to get the bounding rectangle of this item
        """
        # TODO 2021-05-07 13:30:45
        # Factor this into PlanarGraphics; then map it to the item coordinates
        # using mapRectFromScene()
        bRect = QtCore.QRectF()
        sc = self.scene()

        if sc is None:
            if self._parentWidget_ is not None:
                sc = self._parentWidget_.scene
                
        if sc is None:
            return bRect #  return a null QRect!
            
        try:
            if isinstance(self._backend_, Cursor):
                state = self._backend_.currentState
                
                # NOTE: 2021-05-06 15:31:21 see NOTE: 2021-05-04 15:49:24
                # REMINDER: QRectF(x,y,w,h)
                # NOTE: 2021-05-07 13:34:17 
                # Use mapRectFromScene to obtain a QRectF instead of a QPolygonF
                # which would be returned by mapFromScene(rect)
                if isinstance(state, Bunch): # and len(state):
                    if isinstance(self._backend_, VerticalCursor) or \
                        self._backend_.type & PlanarGraphicsType.vertical_cursor:
                        bRect = self.mapRectFromScene(QtCore.QRectF(state.x - state.xwindow/2,
                                                                    0, 
                                                                    state.xwindow, 
                                                                    state.height))
                        
                    elif isinstance(self._backend_, HorizontalCursor) or \
                        self._backend_.type & PlanarGraphicsType.horizontal_cursor:
                        bRect = self.mapRectFromScene(QtCore.QRectF(0, 
                                                                    state.y - state.ywindow/2,  
                                                                    state.width, 
                                                                    state.ywindow))
                        
                    elif isinstance(self._backend_, CrosshairCursor) or \
                        self._backend_.type & PlanarGraphicsType.crosshair_cursor:
                        vRect = self.mapRectFromScene(QtCore.QRectF(state.x - state.xwindow/2,
                                                                    0, 
                                                                    state.xwindow, 
                                                                    state.height))
                        
                        hRect = self.mapRectFromScene(QtCore.QRectF(0, 
                                                                    state.y - state.ywindow/2,  
                                                                    state.width, 
                                                                    state.ywindow))
                        
                        bRect = vRect | hRect
                        
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
                #if self._backend_ is not None and self._backend_.hasStateForFrame(self._currentframe_) and self._backend_() is not None:
                if self._backend_ is not None and not isinstance(self._backend_, Cursor):
                    bRect = self.mapRectFromScene(self._backend_().boundingRect()) # relies on planar graphics's shape !!!!
                    #bRect = self.mapRectFromScene(self._backend_().controlPointRect()) # relies on planar graphics's shape !!!!
                    
                    if self.editMode:
                        bRect |= self.mapRectFromScene(self._cachedPath_().boundingRect())
                        
                else:
                    # no backend, or backend has no state
                    if self._buildMode_:
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
                
        return bRect
    
    def toScenePath(self):
        """Returns a new pictgui.Path object or None if isCursor is True.
        
        This constructs a new pictgui.Path object. 
        
        To reflect the changes in this object's values in an existing
        pictgui.Path object, use direct access to the attributes of the latter.
        
        Coordinates are mapped to scene's coordinate system
        
        NOTE: This is not a reference to the backend Path object
        """
        #if not self.hasState:
            #return
            
        if self._backend_ and len(self._cachedPath_ > 0):
            return Path([self.mapToScene(p) for p in self._cachedPath_.qPoints()])
        
        #if self._backend_ is not None and isinstance(self._backend_, Cursor):
            #if self.isText:
                ## TODO FIXME ???
                #raise NotImplementedError("Scene coordinates from text objects not yet implemented")
            
            #if len(self._cachedPath_ > 0):
                #return Path([self.mapToScene(p) for p in self._cachedPath_.qPoints()])
            
    def toSceneCursor(self):
        """Returns a new pictgui.Cursor object or None if isCursor is False.
        
        This constructs a new pictgui.Cursor object. 
        
        To reflect the changes in this object's values in an existing 
        pictgui.Cursor object use direct acces to the attributes of the latter.
        
        Coordinates are mapped to scene's coordinate system.
        
        NOTE: This does NOT return the reference to the backend Cursor object (which may exist)
        """
        #if not self.hasState:
            #return
        
        if isinstance(self._backend_, Cursor):
            state = self._backend_.getState()
            if state: # and len(state):
                p = self.mapToScene(QtCore.QPointF(state.x, state.y))
                return Cursor(self._backend_.name, p.x(), p.y(), self._backend_.width, self._backend_.height, self._backend_.xwindow, self._backend_.ywindow, self._backend_.radius)
            
    def getScenePosition(self):
        """Returns the position in the scene as x, y sequence
        FIXME
        """
        p = self.mapToScene(self._backend_.pos)
            
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
        stateDescriptor = self._backend_.getState(self._currentframe_)
        
        if len(stateDescriptor):
            if self.isCursor:
                p = self.mapToScene(QtCore.QPointF(self._backend_.x, self._backend_.y))
                ret = [p.x(), p.y(), self._backend_.width, self._backend_.height, self._backend_.xwindow, self._backend_.ywindow, self._backend_.radius]

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
    
    def _cursorsLineShape_(self, state:dict, vert:bool=True, horiz:bool=True):
        vRect = None
        hRect = None
        
        if vert:
            vRect = self.mapRectFromScene(QtCore.QRectF(state.x - state.xwindow/2,
                                                        0, 
                                                        state.xwindow, 
                                                        state.height))
        if horiz:
            hRect = self.mapRectFromScene(QtCore.QRectF(0, 
                                                        state.y - state.ywindow/2,  
                                                        state.width, 
                                                        state.ywindow))
        return [vRect, hRect]
    
    @safeWrapper
    def shape(self):
        """ Used in collision detection, etc.
        Currently return a path made of this item's bounding rectangle.
        """
        # TODO: 2021-05-07 13:32:01
        # Factor this into PlanarGraphics to return a QPainterPath, then map 
        # the result to ths item using mapFromScene(path)
        path = QtGui.QPainterPath()
        
        sc = self.scene()
        
        if sc is None:
            if self._parentWidget_ is not None:
                sc = self._parentWidget_.scene
                
        if sc is None:
            return path
        
        if self._buildMode_:
            if self._cachedPath_ is not None and len(self._cachedPath_)> 0:
                path.addPath(self._cachedPath_())
            
            path.addRect(sc.sceneRect()) # needed to find collisions with mouse
            
        else:
            path.addPath(self.mapFromScene(self._backend_()))
            
            if isinstance(self._backend_, Cursor):
                path.addRect(self._labelRect)
                #return path
                
            else:
                state = self._backend_.currentState
                if state: # and len(state):
                    if isinstance(self._backend_, Path):
                        path.addRect(self.mapRectFromScene(self._backend_().boundingRect()))
                    
                    if self.editMode:
                        if self._cachedPath_ is not None and len(self._cachedPath_)> 0:
                            path.addPath(self.mapFromScene(self._cachedPath_()))
                            
                        if len(self._cachedPath_) > 1:
                            for k, element in enumerate(self._cachedPath_):
                                pt = self.mapFromScene(QtCore.QPointF(element.x, 
                                                                    element.y))
                                
                                path.addEllipse(pt, self._pointSize, self._pointSize)

                lrect = QtCore.QRectF(self._labelRect.topLeft(),
                                        self._labelRect.bottomRight())
                
                lrect.moveBottomLeft(self.boundingRect().center())
                path.addRect(lrect)
                path.addRect(self.boundingRect())
                
                path.setFillRule(QtCore.Qt.WindingFill)
                
        return path
    
            #else: 
                # either no backend (in build mode), or no state for current frame
        #if isinstance(self._backend_, Cursor):
            #path.addRect(self._labelRect)
            #return path
            
        #else:
            #if self._backend_ is not None and self._backend_.hasStateForFrame() and self._backend_() is not None:
                ##path.addPath(self.mapFromScene(self._backend_()))
                
                #if isinstance(self._backend_, Line):
                    #p0 = self.mapFromScene(QtCore.QPointF(self._backend_[0].x, 
                                                          #self._backend_[0].y))
                    
                    #p1 = self.mapFromScene(QtCore.QPointF(self._backend_[1].x, 
                                                          #self._backend_[1].y))
                    
                    #path.addRect(QtCore.QRectF(p0,p1))
                    
                #elif isinstance(self._backend_, Path):
                    #path.addRect(self.mapRectFromScene(self._backend_().boundingRect()))
                
                #if self.editMode:
                    #if self._cachedPath_ is not None and len(self._cachedPath_)> 0:
                        #path.addPath(self.mapFromScene(self._cachedPath_()))
                        
                    #if len(self._cachedPath_) > 1:
                        #for k, element in enumerate(self._cachedPath_):
                            #pt = self.mapFromScene(QtCore.QPointF(element.x, 
                                                                  #element.y))
                            
                            #path.addEllipse(pt, self._pointSize, self._pointSize)

                #lrect = QtCore.QRectF(self._labelRect.topLeft(),
                                      #self._labelRect.bottomRight())
                
                #lrect.moveBottomLeft(self.boundingRect().center())
                #path.addRect(lrect)
                #path.addRect(self.boundingRect())
                
                #path.setFillRule(QtCore.Qt.WindingFill)
                
                #return path
    
            #else: 
                ## either no backend (in build mode), or no state for current frame
                #if self._buildMode_:
                    #if self._cachedPath_ is not None and len(self._cachedPath_)> 0:
                        #path.addPath(self._cachedPath_())
                    
                    #path.addRect(sc.sceneRect()) # needed to find collisions with mouse
                
        #return path
    
    def setPos(self, x, y=None):
        """Overloads QGraphicsItem.setPos()
        Parameters:
        ==========
        x: numbers.Real or QtCore.QPointF when y is None
        y: numbers.Real or None
        """
        # NOTE changes to backend are done by itemChange()
        #if self.objectType & PlanarGraphicsType.allCursorTypes:
        if all([isinstance(v, numbers.Real) for v in (x,y)]):
            super().setPos(x,y)
            
        elif isinstance(x, QtCore.QPointF):
            super().setPos(x)
            
        elif isinstance(x, QtCore.QPoint):
            super().setPos(QtCore.QPointF(x))
            
        else:
            raise TypeError("Either x and y must be supplied as floats, or x must be a QPointF or QPoint")
            
        #self.redraw()
        self.update()
        
    def update(self):
        if self.scene(): # because it may by Null at construction
            self.scene().update(self.boundingRect())
            
        else:
            super().update()
        
    def redraw(self):
        self._makeObject_()

        self._setDisplayStr_()
        self._updateLabelRect_()

        self.update() # calls paint() indirectly
        
    def paint(self, painter, styleOption, widget):
        # NOTE: 2021-03-07 18:30:02
        # to time the painter, uncomment "self.timed_paint(...)" below and comment
        # out the line after it ("self.__paint__(...)")
        # When times, the duration of one execution of __paint__ is printed on
        # stdout - CAUTION generates large output
        #self.timed_paint(painter, styleOption, widget)
        self.__paint__(painter, styleOption, widget)
        
    @timefunc # defined in core.prog
    def timed_paint(self, painter, styleOption, widget):
        # NOTE: 2021-03-07 18:32:00
        # timed version of the painter; to time the painter, call this function
        # instead of "__paint__" in self.paint(...) - see NOTE: 2021-03-07 18:30:02
        self.__paint__(painter, styleOption, widget)
        
    #@safeWrapper
    def __paint__(self, painter, styleOption, widget):
        """Does the actual painting of the item.
        Also called by self.update(), super().update() & scene.update()
        """
        # NOTE: 2021-03-07 18:33:05
        # both paint and timed_paint call this function; use timed_paint to
        # time the painter - i.e., to output the duration of the paint execution
        # on the stdout - CAUTION generates large outputs
        
        try:
            if not self.__objectVisible__:
                return
            
            if not self._buildMode_:
                if self._backend_ is None or not self._backend_.hasStateForFrame():
                    return
                    
            linePen = self.lnf["pen"]["line"]
            textPen = self.lnf["pen"]["text"]
            textBrush = self.lnf["brush"]["text"]
            
            pointSize = self.lnf["pointsize"]
            controlPointSize = self.controlLnF["pointsize"]
                
            labelPos = None         # NOTE: 2017-06-23 09:41:24
                                    # below I calculate a default label position
                                    # based on cursor type
                                    # this position will be then changed dynamically
                                    # according to the font metrics
                                    # when the painter becomes active
                                    
            painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing)
            
            if isinstance(self._backend_, Cursor): # cursor paint logic
                # NOTE: 2018-01-18 14:47:49
                # WARNING: DO NOT use _graphicsShapedItem to represent cursors,
                # because the Qt GraphicsView system renders its shape's bounding 
                # rect with a dotted line when item is selected.
                ### self._graphicsShapedItem.paint(painter, styleOption, widget)

                lines = list()
                rects = list()
                
                state = self._backend_.currentState
                
                if "GraphicsImageViewerScene" in type(self.scene()).__name__:
                    sceneWidth  = self.scene().rootImage.boundingRect().width()
                    sceneHeight = self.scene().rootImage.boundingRect().height()
                else:
                    sceneWidth  = state.width
                    sceneHeight = state.height
                    
                labelXmin = 0
                labelXmax = sceneWidth - self._labelRect.width()
                labelYmin = self._labelRect.height() 
                labelYmax = sceneHeight - self._labelRect.height()
                
                # NOTE: 2021-05-07 09:15:46 - new logic for itemChange and paint
                # Compensate for main cursor line displacement by resetting the
                # lines' points; in the past this was done by limiting/resetting
                # coordinates in the new position in self.itemChange() but its
                # 'undoing' (to allow the whiskers to move) was a pain
                # turned out to be a pain
                # 
                # Also, compensate label position so that it is drawn consistently
                # with the cursor type and does not clutter too much
                    
                # NOTE: 2021-05-04 15:49:24
                # the old-style type checks below is for backward compatibility
                if isinstance(self._backend_, VerticalCursor) or \
                    self._backend_.type == PlanarGraphicsType.vertical_cursor:
                        
                    lines = [self._vline, self._hwbar]
                    
                    labelX = max([min([state.x - self._labelRect.width()/2, labelXmax]), labelXmin])
                        
                    labelY = labelYmin
                    
                    # compensate vertical movement of vline
                    self._vline.setP1(self.mapFromScene(QtCore.QPointF(state.x, 0)))
                    self._vline.setP2(self.mapFromScene(QtCore.QPointF(state.x, sceneHeight)))

                elif isinstance(self._backend_, HorizontalCursor) or \
                    self._backend_.type == PlanarGraphicsType.horizontal_cursor:
                        
                    lines = [self._hline, self._vwbar]
                    
                    labelX = labelXmin
                        
                    labelY = max([min([state.y - self._labelRect.height(), labelYmax]), labelYmin])

                    # compensate horizontal lateral) movement of hline
                    self._hline.setP1(self.mapFromScene(QtCore.QPointF(0, state.y)))
                    self._hline.setP2(self.mapFromScene(QtCore.QPointF(sceneWidth, state.y)))
                        
                elif isinstance(self._backend_, CrosshairCursor) or \
                    self._backend_.type == PlanarGraphicsType.crosshair_cursor:
                        
                    lines = [self._vline, self._hline]
                    
                    rects = [self._wrect]
                    
                    labelX = state.x - self._labelRect.width()/2
                    
                    labelX = max([min([state.x - self._labelRect.width()/2, labelXmax]), labelXmin])
                    
                    labelY = labelYmin#self._labelRect.height()
                    
                    # compensate vertical movement of vline
                    self._vline.setP1(self.mapFromScene(QtCore.QPointF(state.x, 0)))
                    self._vline.setP2(self.mapFromScene(QtCore.QPointF(state.x, sceneHeight)))
                    
                    # compensate horizontal lateral) movement of hline
                    self._hline.setP1(self.mapFromScene(QtCore.QPointF(0, state.y)))
                    self._hline.setP2(self.mapFromScene(QtCore.QPointF(sceneWidth, state.y)))
                        
                else: # point cursor
                    lines = [self._vwbar, self._hwbar]
                    rects = [self._crect, self._wrect]

                    labelX = max([min([state.x - self._labelRect.width()/2, labelXmax]), labelXmin])
                    
                    labelY = max([min([state.y - self._labelRect.height(), labelYmax]), labelYmin])
                    
                painter.setPen(linePen)
                if len(lines):
                    painter.drawLines(lines)
                    
                if len(rects):
                    if self._roundCursor_:
                        for r in rects:
                            painter.drawEllipse(r)
                    else:
                        painter.drawRects(rects)

                labelPos = self.mapFromScene(QtCore.QPointF(labelX, labelY))
                    
            else: # non-cursor types
                # NOTE: FIXME be aware of undefined behaviours !!! (check flags and types)
                if self._buildMode_: # this only makes sense for non-cursors
                    if len(self._cachedPath_) == 0: # nothing to paint !
                        return
                    
                    # NOTE: 2018-01-24 15:57:16 
                    # THE SHAPE IN BUILD MODE = cached path
                    # first draw the shape
                    painter.setPen(self.controlLnF["pen"]["line"])
                    #painter.setPen(self._linePenSelected)
                    
                    if isinstance(self._backend_, Path):
                        if self._backend_.type == PlanarGraphicsType.polygon:
                            for k, element in enumerate(self._cachedPath_):
                                if k > 0:
                                    painter.drawLine(self._cachedPath_[k-1].point(), 
                                                     self._cachedPath_[k].point())
                        else:
                            painter.drawPath(self._cachedPath_)
                            
                            if self._curveBuild_ and self._hover_point is not None:
                                if self._control_points[0] is not None:
                                    path = QtGui.QPainterPath(self._cachedPath_[-1].point())
                                    
                                    if self._control_points[1] is not None:
                                        path.cubicTo(self._control_points[0], 
                                                    self._control_points[1], 
                                                    self._hover_point)
                                        
                                    else:
                                        path.quadTo(self._control_points[0], 
                                                    self._hover_point)
                                        
                                    painter.drawPath(path)
                                
                    if len(self._cachedPath_) > 1:
                        if isinstance(self._backend_, Line):
                            painter.drawLine(self._cachedPath_[-2].point(), 
                                            self._cachedPath_[-1].point())
                            
                        elif isinstance(self._backend_, Rect):
                            painter.drawRect(QtCore.QRectF(self._cachedPath_[-2].point(), 
                                                        self._cachedPath_[-1].point()))
                            
                        elif isinstance(self._backend_, Ellipse):
                            painter.drawEllipse(QtCore.QRectF(self._cachedPath_[-2].point(), 
                                                            self._cachedPath_[-1].point()))
                            
                        elif self.objectType & PlanarGraphicsType.polygon:
                            for k, element in enumerate(self._cachedPath_):
                                if k > 0:
                                    painter.drawLine(self._cachedPath_[k-1].point(), 
                                                     self._cachedPath_[k].point())
                        

                    # NOTE: 2018-01-24 15:56:51 
                    # CONTROL (HOVER) POINTS AND LINES IN BUILD MODE
                    # now draw control points and lines
                    # draw control points
                    painter.setPen(self.controlLnF["pen"]["point"]) 
                    painter.setBrush(self.controlLnF["brush"]["point"])
                    
                    for k, element in enumerate(self._cachedPath_):
                        painter.drawEllipse(element.x - controlPointSize,
                                            element.y - controlPointSize,
                                            controlPointSize * 2., 
                                            controlPointSize * 2.)
                        
                        if k > 0:
                            painter.drawLine(self._cachedPath_[k-1].point(), 
                                            element.point())
                            
                    # NOTE: 2018-01-24 15:58:33 
                    # EXTRA CONTROL POINTS AND HOVER POINT IN BUILD MODE WHERE THEY EXIST
                    if self.objectType & PlanarGraphicsType.path:
                        if self._control_points[0] is not None:
                            painter.drawEllipse(self._control_points[0].x() - controlPointSize,
                                                self._control_points[0].y() - controlPointSize,
                                                controlPointSize * 2., 
                                                controlPointSize * 2.)
                            
                            painter.drawLine(self._cachedPath_[-1].point(), 
                                            self._control_points[0])
                            
                            if self._control_points[1] is not None:
                                painter.drawEllipse(self._control_points[1].x() - controlPointSize,
                                                    self._control_points[1].y() - controlPointSize,
                                                    controlPointSize * 2., 
                                                    controlPointSize * 2.)
                                
                                painter.drawLine(self._control_points[0], 
                                                self._control_points[1])
                                
                                if self._hover_point is not None:
                                    painter.drawEllipse(self._hover_point.x() - controlPointSize, 
                                                        self._hover_point.y() - controlPointSize, 
                                                        controlPointSize * 2., 
                                                        controlPointSize *2.)
                                    
                                    painter.drawLine(self._control_points[1], 
                                                    self._hover_point)
                                    
                                
                            else:
                                if self._hover_point is not None:
                                    painter.drawEllipse(self._hover_point.x() - controlPointSize, 
                                                        self._hover_point.y() - controlPointSize, 
                                                        controlPointSize * 2., 
                                                        controlPointSize * 2.)
                                    
                                    painter.drawLine(self._control_points[0], 
                                                    self._hover_point)
                                    
                        elif self._hover_point is not None:
                            painter.drawEllipse(self._hover_point.x() - controlPointSize, 
                                                self._hover_point.y() - controlPointSize, 
                                                controlPointSize * 2., 
                                                controlPointSize * 2.)
                            
                            painter.drawLine(self._cachedPath_[-1].point(), 
                                            self._hover_point)
                        
                    elif self._hover_point is not None:
                        painter.drawEllipse(self._hover_point.x() - controlPointSize, 
                                            self._hover_point.y() -controlPointSize, 
                                            controlPointSize * 2., 
                                            controlPointSize * 2.)
                        
                        painter.drawLine(self._cachedPath_[-1].point(), 
                                        self._hover_point)

                        if self.objectType & PlanarGraphicsType.line:
                            painter.drawLine(self._cachedPath_[-1].point(), 
                                            self._hover_point)
                        
                        elif self.objectType & PlanarGraphicsType.rectangle:
                            painter.drawRect(QtCore.QRectF(self._cachedPath_[-1].point(), 
                                                        self._hover_point))
                            
                        elif self.objectType & PlanarGraphicsType.ellipse:
                            painter.drawEllipse(QtCore.QRectF(self._cachedPath_[-1].point(), 
                                                            self._hover_point))
                            
                        elif self.objectType & PlanarGraphicsType.polygon:
                            painter.drawLine(self._cachedPath_[-1].point(), 
                                            self._hover_point)

                    labelPos = self.boundingRect().center()
                    
                else:
                    # not in build mode
                    # NOTE: 2018-01-24 16:12:20
                    # DRAW SHAPE 
                    
                    # NOTE: 2018-01-24 16:12:43
                    # SELECT PEN & BRUSH FIRST
                    
                    painter.setPen(linePen)
                    
                    if self._backend_.type & PlanarGraphicsType.point:
                        painter.setBrush(textBrush)

                    # NOTE: 2018-01-24 16:13:03
                    # DRAW THE ACTUAL SHAPE
                    # NOTE: 2018-01-24 17:17:05
                    # WE SHOULD HAVE A _backend_ BY NOW
                    
                    if self._backend_ is not None:
                        if isinstance(self._backend_, Ellipse):
                            r_ = self.mapRectFromScene(self._backend_.x,
                                                       self._backend_.y,
                                                       self._backend_.w,
                                                       self._backend_.h)
                            
                            painter.drawEllipse(r_)

                        elif isinstance(self._backend_, Rect):
                            r_ = self.mapRectFromScene(self._backend_.x,
                                                       self._backend_.y,
                                                       self._backend_.w,
                                                       self._backend_.h)
                            
                            painter.drawRect(r_)
                            
                        elif self._backend_.type == PlanarGraphicsType.line:
                            qp = self._backend_.qPoints()
                            if len(qp):
                                qp = list(map(lambda x: self.mapFromScene(x), qp))
                                painter.drawLine(QtCore.QLineF(*qp))
                                                                            
                        elif self._backend_.type == PlanarGraphicsType.point:
                            p_ = self.mapFromScene(self._backend_.x,
                                                   self._backend_.y)
                            
                            r_ = self.mapRectFromScene(self._backend_.x - pointSize,
                                                       self._backend_.y - pointSize,
                                                       pointSize * 2.,
                                                       pointSize * 2.)
                            
                            painter.drawPoint(p_)
                            painter.drawEllipse(r_)
                            
                        else: # general Path backend, including polyline, polygon, etc.
                            path = self._backend_.objectForFrame() # this is a pictgui.Path
                            #qpath = self._backend_()
                            
                            # TODO: 2024-08-25 18:55:02
                            # check how many Move elements are there;
                            # if there are Move elements inside the path, then break
                            # it into subpaths and draw these individually
                            
                            # NOTE: 2024-08-25 19:03:06
                            # trying a workaround for very long polylines, which
                            # are painted TOO slowly; examples include PrairieView 
                            # free-hand scanline trajectory that resolve to very 
                            # long polylines, with each segment 'aliased' to a 
                            # single pixel shift in X and/or Y.
                            
                            qpath = self.mapFromScene(path())
                            
#                             if len(path) > 10 and all(isinstance(p, (Line, Move)) for p in path):
#                                 qpath = path().simplified()  # ← crashes Python
#                             else:
#                                 qpath = path()
#                                 
#                             qpath1 = self.mapFromScene(qpath)
                            
                            # if len(path) > 10 and all(isinstance(p, (Line, Move)) for p in path):
                            #     qpath = qpath.simplified() # ← crashes Python
                                
                        
                            if qpath.length() == 0:
                                painter.drawPoint(QtCore.QPointF(qpath.elementAt(0).x, qpath.elementAt(0).y))
                            else:
                                painter.drawPath(qpath)
                            
#                             if all(isinstance(p, (Line, Move)) for p in path):
#                                 # allLines = tuple(filter_type(path, Line))
#                                 qLines = tuple(map(lambda x: QtCore.QLineF(*x.qPoints()), filter_type(path, Line)))
#                                 painter.drawLines(qLines)
#                                 
#                             else:
#                                 # NOTE: 2021-05-04 14:10:24
#                                 # the path() call below generates a QPainterPath
#                                 # which is then mapped from scene to qpath
#                                 qpath = self.mapFromScene(path())
#                             
#                                 if qpath.length() == 0:
#                                     painter.drawPoint(QtCore.QPointF(qpath.elementAt(0).x, qpath.elementAt(0).y))
#                                 else:
#                                     painter.drawPath(qpath)
                            
                            
                    labelPos = self.boundingRect().center()
                    
                    if self.editMode:
                        # NOTE: 2018-01-24 16:14:15
                        # CONTROL AND HOVER POINTS AND CONTROL LINES IN EDIT MODE
                        
                        painter.setPen(self.controlLnF["pen"]["point"]) 
                        painter.setBrush(self.controlLnF["brush"]["point"])
                    
                        # ATTENTION for paths, curves have extra control points!
                        
                        if self._cachedPath_ is not None and len(self._cachedPath_) > 0:
                            if isinstance(self._backend_, Path):
                                for k, element in enumerate(self._cachedPath_):
                                    if isinstance(element, Quad):
                                        pt = self.mapFromScene(QtCore.QPointF(element.x, element.y))
                                        cp = self.mapFromScene(QtCore.QPointF(element.cx, element.cy))
                                        
                                        painter.drawEllipse(cp.x() - self._pointSize, \
                                                            cp.y() - self._pointSize, \
                                                            self._pointSize * 2., 
                                                            self._pointSize * 2.)
                                        
                                        painter.drawEllipse(pt.x() - self._pointSize, \
                                                            pt.y() - self._pointSize, \
                                                            self._pointSize * 2., 
                                                            self._pointSize * 2.)
                                        
                                        painter.drawLine(self.mapFromScene(self._cachedPath_[k-1].point()), cp)
                                        painter.drawLine(cp, pt)
                                        
                                    elif isinstance(element, Cubic):
                                        pt  = self.mapFromScene(QtCore.QPointF(element.x, element.y))
                                        cp1 = self.mapFromScene(QtCore.QPointF(element.c1x, element.c1y))
                                        cp2 = self.mapFromScene(QtCore.QPointF(element.c2x, element.c2y))
                                        
                                        painter.drawEllipse(cp1, self._pointSize, self._pointSize)
                                        
                                        painter.drawEllipse(cp2, self._pointSize, self._pointSize)
                                        
                                        painter.drawEllipse(pt,  self._pointSize, self._pointSize)
                                        
                                        painter.drawLine(self.mapFromScene(self._cachedPath_[k-1].point()), cp1)
                                        
                                        painter.drawLine(cp1, cp2)
                                        painter.drawLine(cp2, pt)
                                        
                                    else:
                                        
                                        pt = self.mapFromScene(QtCore.QPointF(element.x, element.y))
                                        
                                        painter.drawEllipse(pt, self._pointSize, self._pointSize)
                                        
                            elif self._backend_.type & (PlanarGraphicsType.rectangle | PlanarGraphicsType.ellipse):
                                p0 = self.mapFromScene(QtCore.QPointF(self._cachedPath_[0].x, 
                                                                      self._cachedPath_[0].y))
                                
                                p1 = self.mapFromScene(QtCore.QPointF(self._cachedPath_[1].x,
                                                                      self._cachedPath_[1].y))
                                    
                                painter.drawEllipse(p0, self._pointSize, self._pointSize)
                                painter.drawLine(p0,p1)
                                painter.drawEllipse(p1, self._pointSize, self._pointSize)
                                    
                            else:
                                for k, element in enumerate(self._cachedPath_):
                                    pt = self.mapFromScene(QtCore.QPointF(element.x, element.y))
                                    
                                    painter.drawEllipse(pt, self._pointSize, self._pointSize)
                                    
                                    if k > 0:
                                        painter.drawLine(self.mapFromScene(self._cachedPath_[k-1].point()), 
                                                        self.mapFromScene(element.point()))

            # CAUTION: DO NOT DELETE when commented-out 
            # this paints the boundingRect() and shape() of the thing when
            # debugging
            #### BEGIN DEBUGGING
            #painter.fillRect(self.boundingRect(), self._controlPointBrush) # FIXME
            #painter.fillPath(self.shape(), self._testBrush) # FIXME
            #painter.setPen(QtCore.Qt.darkRed)
            #painter.drawPath(self.shape())
            #### END DEBUGGING

            if self._showLabel_:
                if len(self._displayStr_) > 0 and labelPos is not None:
                    pen = painter.pen()
                    bgMode = painter.backgroundMode()
                    bg = painter.background()
                    
                    if self._opaqueLabel_:
                        painter.setBackgroundMode(QtCore.Qt.OpaqueMode)
                        painter.setBackground(textBrush)
                        
                    else:
                        painter.setBackgroundMode(QtCore.Qt.TransparentMode)
                        
                    painter.setPen(textPen)
                        
                    painter.drawText(labelPos, self._displayStr_)
                    
                    painter.setBackground(bg)
                    painter.setBackgroundMode(bgMode)
                    painter.setPen(pen)
            
        except Exception as exc:
            traceback.print_exc()
            
    @safeWrapper
    def itemChange(self, change, value):
        """Customizes the cursor movement by mouse or keyboard.
        
        1. For vertical/horizontal cursors, movement of cursor main line, whiskers
           and label are adjusted in self.__paint__() such that:
            1.1 The main cursor lines appear to span the entire height/width of
                the scene (except, of course, for point cursors which do not have 
                cursor lines)
            1.2 The cursor whiskers follow the position change    
            1.3 The label is drawn at the top of the main vertical cursor line
                for vertical & crosshair cursors, and at the left edge on top of
                the main horizontal line (for horizontal cursors) with adjustments
                at the scene boundaries
                
                For point cursors, the label is drawn above the cursor, with 
                adjustments at the scene boundaries
           
        2. For non-cursors:
            just updates the backend's x and y coordinates (the effects of which
            depend on what the backend is) for the current frame
        """
        #NOTE: 2018-01-23 18:01:36
        # ATTENTION only check for backend when position changed.
        # In build mode there is neither _backend_ nor _graphicsShapedItem.
        # If you return early without calling super().itemChange
        # the item won't be added to the scene when value is scene_change!
        
        if change == QtWidgets.QGraphicsItem.ItemPositionChange and self.scene():
            # NOTE: 2021-05-05 14:11:47
            # called by setPos() and during mouseMoveEvent
            # 
            # NOTE: 2021-05-07 12:41:29 the movement of the cursor line, whisker 
            # and label is now adjusted in self.__paint__()
            #
            # CAUTION 2021-05-05 15:10:56
            # value is a RELATIVE change (relative to the pos of the item when 
            # the change started)
            
            if self._backend_ is None:
                return value
            
            if not self._backend_.hasStateForFrame() or not self.__objectVisible__:
                return value
            
            if isinstance(self._backend_, Cursor): # cursor types
                # NOTE 2018-01-18 16:57:28
                # ATTENTION This is also called by self.setPos() (inherited)
                self._positionChangeHasBegun = True # flag used in _makeCursor_()
                
                # See NOTE: 2021-05-04 15:49:24 for the old style type checks below
                # vertical cursors:
                if value.x() <= 0.0:
                    value.setX(0.0)
                    
                if value.x() > self._backend_.width:
                    value.setX(self._backend_.width)

                if value.y() <= 0.0:
                    value.setY(0.0)
                    
                if value.y() > self._backend_.height:
                    value.setY(self._backend_.height)
                    
            self._backend_.x = value.x()
            self._backend_.y = value.y()
                        
            # NOTE: 2018-01-18 15:44:28
            # 'value' is already in scene coordinates, so no mapping needed here
            #state.x = value.x()
            #state.y = value.y()

            self._backend_.updateLinkedObjects()

            if self._labelShowsCoordinates_:
                self._setDisplayStr_()
                self._updateLabelRect_()
                
            self.update() # calls paint() indirectly
            
            self.signalBackendChanged.emit(self._backend_)
        
        # NOTE: 2017-08-11 13:19:28
        # selection change is applied to all GraphicsObject types, not just cursors
        elif change == QtWidgets.QGraphicsItem.ItemSelectedChange and self.scene() is not None:
            # NOTE: ZValue refers to the stack ordering of the graphics items in the scene
            # and it has nothing to do with frame visibility.
            if value:
                nItems = len(self.scene().items())
                self.setZValue(nItems+1)
                
            else:
                self.setZValue(0)
                
            self.selectMe.emit(self.ID, value)
            
        elif change == QtWidgets.QGraphicsItem.ItemScenePositionHasChanged and self.scene() is not None:
            # NOTE: NOT used for now...
            pass

        elif change == QtWidgets.QGraphicsItem.ItemSceneHasChanged: # now self.scene() is the NEW scene
            self._makeObject_()

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
        
        When ROI type is path and we are in _curveBuild_ mode, CTRL + ALT modifiers
        create a second control point, to create a cubic Bezier curve.
        
        
        """
        self.setCursor(QtCore.Qt.ClosedHandCursor)
        
        if self._buildMode_: # this is ALWAYS False for cursors
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
            
            if self.objectType == PlanarGraphicsType.allShapeTypes and \
                len(self._cachedPath_) == 0:
                # before adding first point, cheeck key modifiers and set
                # self._planar_graphics_type_ accordingly
                
                # NOTE: 2018-01-23 22:41:05
                # ATTENTION: do not delete commented-out "mods" code -- for debugging
                
                mods = ""
                
                if evt.modifiers() == QtCore.Qt.ShiftModifier: 
                    #### SHIFT => rectangle
                    self._planar_graphics_type_ = PlanarGraphicsType.rectangle
                    mods = "shift"
                    
                elif evt.modifiers() == QtCore.Qt.ControlModifier: 
                    #### CTRL => ellipse
                    self._planar_graphics_type_ = PlanarGraphicsType.ellipse
                    mods = "ctrl"
                    
                elif evt.modifiers() ==  QtCore.Qt.AltModifier: 
                    #### ALT => path
                    self._planar_graphics_type_ = PlanarGraphicsType.path
                    mods = "alt"
                
                elif evt.modifiers() == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
                    #### CTRL+SHIFT => polygon
                    self._planar_graphics_type_ = PlanarGraphicsType.polygon
                    mods = "ctrl+shift"
                    
                elif evt.modifiers() == (QtCore.Qt.AltModifier | QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
                    #### ALt+CTRL+SHIFT => point
                    mods = "alt+=ctrl+shift"
                    self._planar_graphics_type_ = PlanarGraphicsType.point
                    
                else: 
                    if evt.modifiers() == QtCore.Qt.NoModifier:
                        mods = "none"
                        
                    #### Anything else, or no modifiers => line
                    self._planar_graphics_type_ = PlanarGraphicsType.line
            
                #print("press at: ", evt.pos(), " mods: ", mods)
                
            if len(self._cachedPath_) == 0:
                # add first point
                self._cachedPath_.append(Move(evt.pos().x(), evt.pos().y()))
                
                if self.objectType & PlanarGraphicsType.point:
                    # stop here if building just a point
                    self._finalizeShape_()
                
            else:
                #print("last press: ", evt.pos(), " hover point: ", self._hover_point)
                
                # there are previous points in the _cachedPath
                # check if evt.pos() is "over" the last point in the _cachedPath
                #d = QtCore.QLineF(evt.pos(), self._cachedPath_[-1].point()).length()
                d = QtCore.QLineF(self._hover_point, self._cachedPath_[-1].point()).length()
                
                # NOTE: self._constrainedPoint is set by mouse hover event handler
                # we set it to None after using it, here
                if d > 2 * self._pointSize: # press event fired far away from last point
                    if self.objectType & (PlanarGraphicsType.line | PlanarGraphicsType.rectangle | PlanarGraphicsType.ellipse):
                        # does nothing is self._cachedPath_ already has more than one point
                        if len(self._cachedPath_) == 1:
                            # there is only one point prior to this one
                            
                            if self._constrainedPoint is not None and not self._constrainedPoint.isNull():
                                # append a constrained point is any
                                self._cachedPath_.append(Line(self._constrainedPoint.x(), self._constrainedPoint.y()))
                                self._constrainedPoint = None
                                
                            else:
                                # else append this point
                                if self._hover_point is not None and not self._hover_point.isNull():
                                    
                                    self._cachedPath_.append(Line(self._hover_point.x(), self._hover_point.y()))
                                    
                                else:
                                    self._cachedPath_.append(Line(evt.pos().x(), evt.pos().y()))
                                
                            #print("to finalize: ", self._cachedPath_)
                            
                            self._finalizeShape_()
                            
                    elif self.objectType & PlanarGraphicsType.polygon:
                        if self._constrainedPoint is not None:
                                self._cachedPath_.append(Line(self._constrainedPoint.x(), self._constrainedPoint.y()))
                                self._constrainedPoint = None
                                
                        else:
                            self._cachedPath_.append(Line(evt.pos().x(), evt.pos().y()))
                            
                    elif self.objectType & PlanarGraphicsType.path:
                        if self._curveBuild_:
                            # self._curveBuild_ is set in mouse move event handler
                            if evt.modifiers() == (QtCore.Qt.ControlModifier | QtCore.Qt.AltModifier):
                                self._control_points[1] = evt.pos()

                            else:
                                if self._control_points[0] is not None:
                                    if self._control_points[1] is not None:
                                        self._cachedPath_.append(Cubic(evt.pos().x(),
                                                                      evt.pos().y(),
                                                                      self._control_points[0].x(),
                                                                      self._control_points[0].y(),
                                                                      self._control_points[1].x(),
                                                                      self._control_points[1].y()))
                                        
                                        self._control_points[1] = None # cp has been used
                                        
                                    else:
                                        self._cachedPath_.append(Quad(evt.pos().x(),
                                                                     evt.pos().y(),
                                                                     self._control_points[0].x(),
                                                                     self._control_points[0].y()))
                                        
                                    self._control_points[0] = None # cp has been used
                                    
                                    self._curveBuild_ = False
                                    
                        else:
                            if evt.modifiers() == (QtCore.Qt.ControlModifier | QtCore.Qt.AltModifier): # allow the creation of a subpath
                                self._cachedPath_.append(Move(evt.pos().x(), evt.pos().y()))
                                
                            else:
                                if self._constrainedPoint is not None:
                                    self._cachedPath_.append(Line(self._constrainedPoint.x(), self._constrainedPoint.y()))
                                    self._constrainedPoint = None
                                else:
                                    self._cachedPath_.append(Line(evt.pos().x(), evt.pos().y()))

                else: # select the last point, possibly move it, if followed by mouse move
                    self._movePoint = True
            
            self.update() # force repaint, do not propagate event to superclass
            
            self.selectMe.emit(self.ID, True)

        if self.editMode: # this is ALWAYS False for cursors
            # select a control point according to mouse event position
            # see qt5 examples/widgets/painting/pathstroke/pathstroke.cpp
            distance = -1
            
            if self._cachedPath_ is None or len(self._cachedPath_) == 0:
                self._cachedPath_ = self._backend_.objectForFrame(self._currentframe_) 
                self._cachedPath_.frameIndices = [] # force current state into a common state

            for k, p in enumerate(self._cachedPath_):
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
                        
            
            self.selectMe.emit(self.ID, True)

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
        
        #print(self._backend_.x)
        
        
        if self._buildMode_: # "drawing" a new shape in GUI
            #mods = "none" 
            # build mode exists only for non-cursors
            # if objectType is a path then generate a curve (mouse is pressed) otherwise behave as for hoverMoveEvent
            self.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
            
            currentPoint = evt.pos()
            
            if evt.modifiers() == QtCore.Qt.ControlModifier:
                mods = "ctrl"
                
                if len(self._cachedPath_) > 0:
                    lastPoint = self._cachedPath_[-1].point()
                    currentPoint = __constrain_0_45_90__(lastPoint, evt.pos())
                    
            elif evt.modifiers() == QtCore.Qt.ShiftModifier:
                mods = "shift"
                
                if len(self._cachedPath_) > 0:
                    lastPoint = self._cachedPath_[-1].point()
                    currentPoint = __constrain_square__(lastPoint, evt.pos())
                    
            elif evt.modifiers() == QtCore.Qt.AltModifier:# and self.objectType == PlanarGraphicsType.path:
                mods ="alt"
                
                self._curveBuild_ = True # stays True until next mouse release or mouse press
                    
            #print("move at: ", evt.pos())
            #print("mods: ", mods)
            
            if self._movePoint:
                if len(self._cachedPath_) > 0:
                    if isinstance(self._cachedPath_[-1], Move):
                        self._cachedPath_[-1] = Move(evt.pos().x(), evt.pos().y())
                        
                    elif isinstance(self._cachedPath_[-1], Line):
                        self._cachedPath_[-1] = Line(evt.pos().x(), evt.pos().y())
                        
                    elif isinstance(self._cachedPath_[-1], Quad):
                        q = self._cachedPath_[-1]
                        self._cachedPath_[-1] = Quad(q.x1, q.y1, 
                                                       evt.pos().x(), evt.pos().y())
                        
                    elif isinstance(self._cachedPath_[-1], Cubic): # because the path may have been "normalized"
                        c = self._cachedPath_[-1]
                        self._cachedPath_[-1] = Quad(c.x, c.y, c.x1, c.y1, 
                                                       evt.pos().x(), evt.pos().y())
                    
                
            else:
                self._hover_point = currentPoint
                self._control_points[0] = None # avoid confusion in paint()
                
            self.update()
            
            self.selectMe.emit(self.ID, True)

            
            return

        else: # shape already exists => NOT in build mode
            self.setCursor(QtCore.Qt.ClosedHandCursor) # this is the windowing system mouse pointer !!!

            # NOTE: 2018-09-26 14:47:05
            # editMode: by design this can only be True for non-cursors
            if self.editMode and self._cachedPath_ is not None and len(self._cachedPath_) \
                and self._c_activePoint >= 0 and self._c_activePoint < len(self._cachedPath_):
                #self.prepareGeometryChange()
                element = self._cachedPath_[self._c_activePoint]
                
                epos = self.mapToScene(evt.pos())
                
                if isinstance(element, Move):
                    self._cachedPath_[self._c_activePoint] = Move(epos.x(), epos.y())
                    
                elif isinstance(element, Line):
                    self._cachedPath_[self._c_activePoint] = Line(epos.x(), epos.y())
                    
                elif isinstance(element, Quad):
                    if self._c_activeControlPoint == 0:
                        self._cachedPath_[self._c_activePoint] = Quad(cx=epos.x(), cy=epos.y(),
                                                                        x=element.x, y=element.y,)
                        
                    else:
                        self._cachedPath_[self._c_activePoint] = Quad(cx=element.cx, cy=element.cy,
                                                                        x=epos.x(), y=epos.y())
                    
                elif isinstance(element, Cubic):
                    if self._c_activeControlPoint == 0:
                        self._cachedPath_[self._c_activePoint] = Cubic(c1x=epos.x(), c1y=epos.y(),
                                                                         c2x=element.c2x, c2y=element.c2y,
                                                                         x=element.x, y=element.y,)
                        
                    elif self._c_activeControlPoint == 1:
                        self._cachedPath_[self._c_activePoint] = Cubic(c1x=element.c1x, c1y=element.c1y,
                                                                         c2x=epos.x(), c2y=epos.y(),
                                                                         x=element.x, y=element.y)
                        
                    else:
                        self._cachedPath_[self._c_activePoint] = Cubic(c1x=element.c1x, c1y=element.c1y,
                                                                         c2x=element.c2x, c2y=element.c2y,
                                                                         x=epos.x(), y=epos.y())
                        
                if self._backend_ is not None:
                    self.__updateBackendFromCachedPath__()
                    self.signalBackendChanged.emit(self._backend_)
            
                self.update() # calls paint() -- force repainting, do or propgate event to the superclass
                
                # NOTE: 2017-08-11 16:43:12
                # do NOT EVER call this here !!!
                # leave commented-out code as a reminder
                # ### super(GraphicsObject, self).mouseMoveEvent(evt)
                # ###
                #return

            elif self.canMove: # simple translations
                # this will also change the position of the control points!
                # NOTE: this will be captured by itemChange - position change
                # which changes the backend directly!, then
                # we call update there
                #if self._backend_ is not None:
                if isinstance(self._backend_, PlanarGraphics):
                    #self.__updateBackendFromCachedPath__() # just DON'T
                    #self.signalBackendChanged.emit(self._backend_)
                    
                    for f in self._backend_.frontends:
                        if f != self:
                            f.redraw()
            
                #self.signalPosition[int, str, "QPointF"].emit(self.objectType.value, self._ID_, self.pos())
                self.signalPosition[str, "QPointF"].emit(self.ID, self.pos())
                #self.__updateCachedPathFromBackend__()
                # NOTE 2017-08-12 13:22:26
                # this IS NEEDED for cursor movement by mouse !!!!
                # backend updating for cursors is dealt with in itemChange
                super(GraphicsObject, self).mouseMoveEvent(evt) # => notifies state changes with itemChange()
            
            self.selectMe.emit(self.ID, True)

    @safeWrapper
    def mouseReleaseEvent(self, evt):
        """Mouse release event handler
        """
        #print(self._backend_.x)
        self._c_activePoint = -1 # restore this anyway!
        
        self.unsetCursor()
        
        if self._buildMode_: # this is ALWAYS False for cursors
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
            #print("obj type: ", self._planar_graphics_type_)
            
            if self._curveBuild_:
                if self._control_points[1] is None: # we allow mod of 1st cp when there is no 2nd cp
                    self._control_points[0] = evt.pos()
                    
            self._hover_point = evt.pos()
            
            self.update()
            return
            
        if self.canMove:
            # together with itemChange, this implements special treatment
            # of the object shape in the case of cursors (see notes in itemChange code)
            if isinstance(self._backend_, Cursor):
                state = self._backend_.getState()
                
                if state is None: # or len(state) == 0:
                    return
                
                self._positionChangeHasBegun=False
                
        self.selectMe.emit(self.ID, True)

        super(GraphicsObject, self).mouseReleaseEvent(evt)
        
        evt.accept()

    #@safeWrapper
    #"def" mouseDoubleClickEvent(self, evt):
        #"""Mouse double-click event handler - do I need this ???
        #"""
        ## TODO: bring up cursor properties dialog
        ## NOTE: if in buildMode, end ROI construction 
        #if self._buildMode_:
            #self._finalizeShape_()
            
        #self.selectMe.emit(self._ID_, True)

        #super(GraphicsObject, self).mouseDoubleClickEvent(evt)

    @safeWrapper
    def contextMenuEvent(self, evt):
        """
        #TODO: popup context menu => Edit, Link/Unlink, Remove
        """
        self.selectMe.emit(self.ID, True)

        self.requestContextMenu.emit(self.ID, evt.screenPos())
        
        super(GraphicsObject, self).contextMenuEvent(evt)
        
        evt.accept()# so that this doesn't propagate to the underlying graphics items
        
    @safeWrapper
    def hoverEnterEvent(self, evt):
        if self._buildMode_:
            self.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
            
        if self.editMode:
            d = [QtCore.QLineF(evt.pos(), self.mapFromScene(p)).length() for p in self._cachedPath_.qPoints()]
            #print(d)
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
        
        if self._buildMode_:
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
                
            #if len(self._cachedPath_):
                #print("hovermove at :", evt.pos(), " mods ", mods)
            
            if evt.modifiers() == QtCore.Qt.ControlModifier:
                if len(self._cachedPath_) > 0:
                    lastPoint = self._cachedPath_[-1].point()
                    d = QtCore.QLineF(currentPoint, lastPoint).length()
                    
                    if d > 2 * self._pointSize:
                        currentPoint = __constrain_0_45_90__(lastPoint, evt.pos())
                        self._constrainedPoint = currentPoint
                    
            elif evt.modifiers() == QtCore.Qt.ShiftModifier:
                if len(self._cachedPath_) > 0:
                    lastPoint = self._cachedPath_[-1].point()
                    d = QtCore.QLineF(currentPoint, lastPoint).length()
                    
                    if d > 2 * self._pointSize:
                        currentPoint = __constrain_square__(lastPoint, evt.pos())
                        self._constrainedPoint = currentPoint
                    
            self._hover_point = currentPoint

            self.update()
            
            # NOTE do not call super().hoverMoveEvent here
            
            return
            
        if self.editMode and self._cachedPath_ is not None and len(self._cachedPath_):
            d = [QtCore.QLineF(evt.pos(), self.mapFromScene(p)).length() for p in self._cachedPath_.qPoints()]
            
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
        #if not self.hasState:
            #return
        
        if evt.key() == QtCore.Qt.Key_Delete:
            self.signalROIConstructed.emit(0, self.name) # deregisters self with parent and removes it
            
        if self._buildMode_:
            # exit build mode here
            if evt.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                self._finalizeShape_()

            elif evt.key() == QtCore.Qt.Key_Escape:
                self._buildMode_ = False
                #self._graphicsShapedItem = None
                self._constrainedPoint = None
                self._curveSegmentConstruction = False
                self._hover_point = None
                self._cachedPath_.clear()
                self.update()
                self.signalROIConstructed.emit(0, self.name) # in order to deregister self with the caller
                
            return
        
        if self.editMode:
            # exit edit mode here
            if evt.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter, QtCore.Qt.Key_Escape):
                self.editMode = False
                self._cachedPath_.clear()
        
        if not self.canMove:
            return
        
        if isinstance(self._backend_, Cursor):
            state = self._backend_.currentState
            if state is None: # or len(state) == 0:
                return
            
            dx =  1. if evt.key() == QtCore.Qt.Key_Right else -1. if evt.key() == QtCore.Qt.Key_Left else 0.
            dy = -1. if evt.key() == QtCore.Qt.Key_Up    else  1. if evt.key() == QtCore.Qt.Key_Down else 0
            
            if evt.modifiers() & QtCore.Qt.ShiftModifier:
                dx *= 10
                dy *= 10
                
            self.moveBy(dx, dy)
            
        else: # non-cursor types
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
                    
        self.update()

        super(GraphicsObject, self).keyPressEvent(evt)
        
    @property
    def hasTransparentLabel(self):
        return not self._opaqueLabel_
    
    def setTransparentLabel(self, value):
        self._opaqueLabel_ = not value
        
        self.redraw()
        #self.update()
        
    @Slot(int)
    @safeWrapper
    def slotFrameChanged(self, val):
        self._currentframe_ = val
        if self._backend_ is not None:
            self._backend_.currentFrame = val
            
            self._backend_.updateLinkedObjects()
            
            self.setVisible(len(self._backend_.frameIndices) > 0 or self._backend_.hasStateForFrame(val))
            
            if self.__objectVisible__:
                self.update()
            
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
        self.__objectVisible__ = value
        super(GraphicsObject, self).setVisible(value)
            
        self.update()
        
    @safeWrapper
    def __updateBackendFromCachedPath__(self):
        """Updates the backend primitive from this object, it being a ROI
        TODO/FIXME for now only supports Ellipse, Rect, and Path backends
        TODO expand for line, etc.
        NOTE: do not use for cursors !
        ATTENTION: does not work when _backend_ is None
        """
        if self._cachedPath_ is None or len(self._cachedPath_) == 0:
            return
        
        if self._backend_ is None:
            return
            #self._backend_ = self._cachedPath_.copy()
        
        # this is a reference; modifying state attributes effectively
        # modified self._backend_ state for _currentframe_
        
        # NOTE: 2019-03-25 20:44:39
        # TODO code for all non-Cursor types!
        if isinstance(self._backend_, (Ellipse, Rect)) and len(self._cachedPath_) >= 2:
            state = self._backend_.currentState
            if state: # and len(state):
                self._backend_.x = self._cachedPath_[0].x
                
                self._backend_.y = self._cachedPath_[0].y
                
                self._backend_.w = self._cachedPath_[1].x - self._cachedPath_[0].x
                
                self._backend_.h = self._cachedPath_[1].y - self._cachedPath_[0].y
                
                self._backend_.updateLinkedObjects()
                
        elif isinstance(self._backend_, Path):
            try:
                for k, element in enumerate(self._cachedPath_):
                    self._backend_[k].x = element.x
                    self._backend_[k].y = element.y
                    
                self._backend_.updateLinkedObjects()
                    
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
            if isinstance(self._backend_, Cursor):
                self.parentwidget.removeCursorByName(self.name)
                
            else:
                self.parentwidget.removeRoiByName(self.name)
        
        
    # NOTE: 2017-06-26 22:38:06 properties
    #
    
    @property
    def parentwidget(self):
        return self._parentWidget_
    
    @property
    def showLabel(self):
        return self._showLabel_
    
    @showLabel.setter
    def showLabel(self, value):
        self._showLabel_=value
        self.update()
    
    @property
    def backend(self):
        """Read-only!
        The backend is set up at __init__ and it may be None.
        """
        return self._backend_
    
    @property
    def cachedPath(self):
        """Read-only
        """
        return self._cachedPath_
    
    # NOTE: 2017-11-22 23:49:35
    # new property: a list of frame indices where this object is visible
    # if list is empty, this implies the object is visible in ALL frames
    # be careful: is the list contains only a frame index that is never reached
    # the object will never become visible
    @property
    def frameVisibility(self):
        return self._backend_.frameIndices
    
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
        
        if not isinstance(self._backend_, Path):
            self._backend_.frameIndices = value
        
        self._backend_.updateLinkedObjects()
        
        self.update()
        
        for f in self._backend_.frontends:
            if f != self:
                f.redraw()
                
        for  o in self._backend_.linkedObjects:
            for f in o.frontends:
                f.frameVisibility = value
        
    @property
    def currentFrame(self):
        return self._currentframe_
        
    @currentFrame.setter
    def currentFrame(self, value):
        #print("currentFrame.setter ", value)
        self._currentframe_ = value
        
    @property
    def currentBackendFrame(self):
        return self._backend_.currentFrame
    
    @currentBackendFrame.setter
    def currentBackendFrame(self, value):
        #print("currentBackendFrame.setter ", value)
        self._backend_.currentFrame=float(value)
        self._backend_.updateLinkedObjects()
        
    @property
    def hasState(self):
        return isinstance(self._backend_, PlanarGraphics) and self._backend_.hasStateForFrame()
        
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
        if self._backend_ is None:
            return "%s_%s" % (self.__class__.__name__, self.__hash__())
        
        return self._backend_.name
        #return self._ID_
    
    @ID.setter
    def ID(self, value):
        if self._backend_ is None:
            return
        if isinstance(value, str):
            if len(value.strip()):
                if self._backend_.name != value: # check to avoid recurrence
                    self._backend_.name = value
                    self._setDisplayStr_(self._backend_.name)
                    self._updateLabelRect_()
                    #if isinstance(self._backend_, PlanarGraphics):
                        #self._backend_.name = self._ID_
                    self.signalIDChanged.emit(self._backend_.name)
                    self.update()
                    #self.redraw()
                    
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
        return self._labelShowsCoordinates_
    
    @labelShowsPosition.setter
    def labelShowsPosition(self, value):
        self._labelShowsCoordinates_ = value
        #self.redraw()
        #self._makeObject_()
        self.update()
        
        for f in self._backend_.frontends:
            if f != self:
                f._labelShowsCoordinates_ = value
                #f.redraw()
                f.update()

    @property
    def x(self):
        """The x coordinate
        """
        return self.pos().x()
    
    @x.setter
    def x(self, val):
        y = self.pos().y()
        self.setPos(val,y)
        
        for f in self._backend_.frontends:
            if f != self:
                f.update()
                    
    @property
    def horizontalWindow(self):
        if not self.hasState:
            return
        
        if isinstance(self._backend_, Cursor):
            state = self._backend_.currentState
            return state.xwindow
    
    @horizontalWindow.setter
    def horizontalWindow(self, val):
        if not self.hasState:
            return
        
        if isinstance(self._backend_, Cursor):
            state = self._backend_.currentState
            
            state.xwindow = val
            self._backend_.updateLinkedObjects()
            self.update()
            #self.redraw()
            
            for f in self._backend_.frontends:
                if f != self:
                    f.redraw()
    
            #if len(self._linkedGraphicsObjects):
                #for c in self._linkedGraphicsObjects:
                    #if c != self._backend_:
                        #c.xwindow = val
                        
                        #for f in c.frontends:
                            #if f != self:
                                #f.redraw()
                                
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
        
        for f in self._backend_.frontends:
            if f != self:
                f.update()
                    
    @property
    def verticalWindow(self):
        if not self.hasState:
            return
        
        if isinstance(self._backend_, Cursor):
            return self._backend_.currentState.ywindow
    
    @verticalWindow.setter
    def verticalWindow(self, val):
        if not self.hasState:
            return
        
        if isinstance(self._backend_, Cursor):
            state = self._backend_.currentState
            state.ywindow = val
            self._backend_.updateLinkedObjects()
            self.redraw()
            
            for f in self._backend_.frontends:
                if f != self:
                    f.update()
                            
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
        if not self.hasState:
            return
        
        if isinstance(self._backend_, Cursor):
            return self._backend_.currentState.radius
            #stateDescriptor = self._backend_.getState(self._currentframe_)
            #if stateDescriptor is not None and len(stateDescriptor):
                #return stateDescriptor.radius
    
    @radius.setter
    def radius(self, val):
        if not self.hasState:
            return
        
        if isinstance(self._backend_, Cursor):
            state = self._backend_.currentState
            state.radius = val
            self.redraw()
            self._backend_.updateLinkedObjects()
            self._backend_.updateFrontends()
            
            for f in self._backend_.frontends:
                if f != self:
                    f.redraw()
            
    #### BEGIN Appearance properties & methods
    def getPen(self, selected:bool=False, linked:bool=False, text:bool=False,
               control:bool=False, controlpoint:bool=False, controltext:bool=False):
        if control:
            return self._controlLinePen
        elif controlpoint:
            return self._controlPointPen
        elif controltext:
            return self._controlTextPen
        else:
            if linked:
                if selected:
                    return self._textPenLinkedSelected if text else self._linePenLinkedSelected
                else:
                    return self._textPenLinked if text else self._linePenLinked
            else:
                if selected:
                    return self._textPenSelected if text else self._linePenSelected
                else:
                    return self._textPen if text else self._linePen
                
    def setPen(self, pen:QtGui.QPen, selected:bool=False, linked:bool=False, text:bool=False,
               control:bool=False, controlpoint:bool=False, controltext:bool=False):
        if not isinstance(pen, QtGui.QPen):
            raise TypeError("Expecting a QPen (Qt GUI); got %s instead" % type(pen).__name__)
        
        if control:
            self._controlLinePen = pen
        elif controlpoint:
            self._controlPointPen = pen
        elif controltext:
            self._controlTextPen = pen
        else:
            if linked:
                if selected:
                    if text:
                        self._textPenLinkedSelected = pen
                    else:
                        self._linePenLinkedSelected = pen
                else:
                    if text:
                        self._textPenLinked = pen
                    else:
                        self._linePenLinked = pen
            else:
                if selected:
                    if text:
                        self._textPenSelected = pen
                    else:
                        self._linePenSelected = pen
                else:
                    if text:
                        self._textPen = pen
                    else:
                        self._linePen = pen
            
        self.update()
        
    def getBrush(self, selected:bool=False, linked:bool=False,
                 control:bool=False, controlpoint:bool=False, controllabel:bool=False):
        if control:
            return self._controlLabelBrush
        elif controlpoint:
            return self._controlPointBrush
        elif controllabel:
            return self._controlLabelBrush
        else:
            if linked:
                if selected:
                    return self._labelBrushLinkedSelected
                else:
                    return self._labelBrushLinked
            else:
                if selected:
                    return self._labelBrushSelected
                else:
                    return self._labelBrush
                
    def setBrush(self, brush:QtGui.QBrush, selected:bool=False, linked:bool=False, 
                 control:bool=False, controlpoint:bool=False, controllabel:bool=False):
        if not isinstance(brush, QtGui.QBrush):
            raise TypeError("Expecting a QBrush (Qt GUI); got %s instead" % type(brush).__name__)
        
        if control:
            self._controlLabelBrush = brush
        elif controlpoint:
            self._controlPointBrush = brush
        elif controllabel:
            self._controlLabelBrush = brush
        else:
            if linked:
                if selected:
                    self._labelBrushLinkedSelected = brush
                else:
                    self._labelBrushLinked = brush
            else:
                if selected:
                    self._labelBrushSelected = brush
                else:
                    self._labelBrush = brush
                    
        self.update()
        
    def getColor(self, pen:bool=True, linked:bool=False, text:bool=False,
                 control:bool=False, controlpoint:bool=False, controltext:bool=False):
        """Colors for pen or brush.
        For main graphics, color depends on whether the backend is linked or not.
        For control lineart, there are different colors for control line pen,
        control point pen, control point fill, control label text and control 
        label background
        """
        if pen:
            return self.getPen(linked=linked, text=text, control=control, controlpoint=controlpoint).color()
        else:
            return self.getBrush(linked=linked, control=control, controlpoint=controlpoint, controllabel=controltext).color()
        
    def setColor(self, qcolor, pen:bool=True, selected:bool=False, linked:bool=False, text:bool=False,
                 control:bool=False, controlpoint:bool=False):
        """
        """
        if not isinstance(qcolor, QtGui.QColor):
            qcolor = QtGui.QColor(qcolor)
        
        if not qcolor.isValid():
            raise ValueError("%s is not a valid qcolor")
        
        if pen:
            self.getPen(selected=selected, linked=linked, text=text, control=control, controlpoint=controlpoint).setColor(qcolor)
        else:
            self.getBrush(selected=selected, linked=linked, control=control).setColor(qcolor)
        
        self.update()
        
    def getStyle(self, pen:bool=True, selected:bool=False, text:bool=False,
                 control:bool=False,controlpoint:bool=False, controltext:bool=False):
        if pen:
            return self.getPen(linked=linked, text=text, control=control, controlpoint=controlpoint).style()
        else:
            return self.getBrush(linked=linked, control=control, controlpoint=controlpoint, controllabel=controltext).style()
        
    def setStyle(self, style:typing.Union[QtCore.Qt.PenStyle, QtCore.Qt.BrushStyle],
                 selected:bool=False, text:bool=False,
                 control:bool=False,controlpoint:bool=False, controltext:bool=False):
        if isinstance(style, QtCore.Qt.PenStyle):
            self.getPen(linked=linked, text=text, control=control, controlpoint=controlpoint).setStyle(style)
        elif isinstance(style, QtCore.Qt.BrushStyle):
            self.getBrush(linked=linked, control=control, controlpoint=controlpoint, controllabel=controltext).setStyle(style)
        else:
            raise TypeError("Expecting a Qt Core Qt.PenStyle or Qt.BrushStyle; got %s instead" % type(style.__name__))
        
    @property
    def lnf(self) -> Bunch:
        return self.linkedLnF[self.isSelected()] if self._backend_.isLinked else self.basicLnF[self.isSelected()]
    
    @property
    def linkedColor(self):
        return self._linePenLinked.color()
    
    @linkedColor.setter
    def linkedColor(self, qcolor):
        """Set both the pen and text color to the same value
        """
        if isinstance(qcolor, QtGui.QColor) and qcolor.isValid():
            self._linePenLinked.setColor(qcolor)
            self._linePenLinkedSelected.setColor(qcolor)
            self._textPenLinked.setColor(qcolor)
            self._textPenLinkedSelected.setColor(qcolor)
            self.update()
    
    @property
    def penColor(self):
        return self._linePen.color()
    
    @penColor.setter
    def penColor(self, qcolor):
        if isinstance(qcolor, QtGui.QColor) and qcolor.isValid():
            self._linePen.setColor(qcolor)
            self._linePenSelected.setColor(qcolor)
            self.update()
        
    @property
    def linkedPenColor(self):
        return self._linePenLinked.color()
    
    @linkedPenColor.setter
    def linkedPenColor(self, qcolor):
        if isinstance(qcolor, QtGui.QColor) and qcolor.isValid():
            self._linePenLinked.setColor(qcolor)
            self._linePenLinkedSelected.setColor(qcolor)
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
        return self._textPenLinked.color()
    
    @linkedTextColor.setter
    def linkedTextColor(self, qcolor):
        if isinstance(qcolor, QtGui.QColor) and qcolor.isValid():
            self._textPenLinked.setColor(qcolor)
            self.update()
        
    @property
    def textBackground(self) -> QtGui.QBrush:
        return self.lnf.brush.text # self._textBackgroundBrush.color()
        #return self._textBackgroundBrush
    
    @textBackground.setter
    def textBackground(self, brush:QtGui.QBrush):
        if not isinstance(brush, QtGui.QBrush):
            raise TypeError(f"Expecting a QtGui.QBrush; got {type(brush).__name__} instead")
        
        self.lnf.brush.text = brush # self._textBackgroundBrush.color()
        self.update()
        
    @property
    def textBackgroundColor(self) -> QtGui.QColor:
        return self.lnf.brush.text.color() # self._textBackgroundBrush.color()
    
    @textBackground.setter
    def textBackgroundColor(self, qcolor):
        if not isinstance(qcolor, QtGui.QColor):
            raise TypeError(f"Expecting a QtGui.QColor; got {type(qcolor).__name__} instead")
        
        if qcolor.isValid():
            self.lnf.brush.text.setColor(qcolor)
            self.update()
        
    @property
    def opaqueLabel(self):
        return self._opaqueLabel_
    
    @opaqueLabel.setter
    def opaqueLabel(self, val):
        self._opaqueLabel_ = val
        self.update()
        
    @property
    def labelFont(self):
        return self._textFont
    
    @labelFont.setter
    def labelFont(self, font):
        self._textFont = font
        #self._makeObject_
        self.update()
    #### END Appearance properties
        
    @property
    def buildMode(self):
        """Read-only
        """
        return self._buildMode_
    
    @property
    def editMode(self):
        """When True, the shape of the object (non-cursor types) can be edited.
        Default if False.
        Editing is done via control points (GUI editing).
        
        """
        #if self.objectType & PlanarGraphicsType.allCursorTypes:
            #return False
        
        return self._shapeIsEditable_
    
    @editMode.setter
    def editMode(self, value):
        #if self.objectType & PlanarGraphicsType.allCursorTypes:
            #return

        self._shapeIsEditable_ = value
        
        if self._shapeIsEditable_:
            self.__updateCachedPathFromBackend__()
            
        self.update()
        
        
    @property
    def canMove(self):
        """Can this object be moved by mouse or keyboard.
        By default, all graphics object types can be moved.
        For ROI types, setting this to False also sets editMode to False.
        """
        return self._movable_
    
    @canMove.setter
    def canMove(self, value):
        self._movable_ = value
        
        if not self._movable_:
            self.editMode = False
        
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, value)
        
    @property
    def canEdit(self):
        return self._editable_
    
    @canEdit.setter
    def canEdit(self, value):
        self._editable_ = value
        
        if not self._editable_:
            self.editMode=False
        
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, value)
        
    @property
    def canTransform(self):
        """Can the object be transformed (rotated/scaled/skewed).
        By default, objects cannot be transformed, except for being moved
        around the scene (see "canMove").
        However, non-cursor objects can be rotated/scaled/skewed
        when this property is set to "True"
        """
        if isinstance(self._backend_, Cursor):
            return False
        
        return self._transformable_
    
    @canTransform.setter
    def canTransform(self, value):
        self._transformable_ = False if isinstance(self._backend_, Cursor) else value
        
                

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
            
        else: # do not parse curve to data elements
            s.append("controlPoint(x=%g, y=%g)" % (element.x, element.y)) 
    
    #s.append("]")
    
    return "[" + ", ".join(s) + "]"

def makeLnFBunch(linePen:typing.Optional[QtGui.QPen] = None, 
                 textPen:typing.Optional[QtGui.QPen] = None, 
                 pointPen:typing.Optional[QtGui.QPen] = None, 
                 textBrush:typing.Optional[QtGui.QBrush] = None, 
                 pointBrush:typing.Optional[QtGui.QBrush] = None,
                 font:typing.Optional[QtGui.QFont] = None, 
                 pointSize:typing.Optional[typing.Union[int, float]] = None, 
                 control:bool = False,
                 linked:bool = False,
                 selected:bool = False) -> Bunch:
    """Generates a LnF mapping (a traitlets.Bunch) for GraphicsObject instances.
    The mapping has the following structure:
    
    "pen"       -> Bunch: 
                    "line"  -> QtGui.QPen
                    "text"  -> QtGui.QPen
                    "point" -> QtGui.QPen
                
    "brush"     -> Bunch:
                    "text"  -> QtGui.QBrush
                    "point" -> QtGui.QBrush
                
    "font"      -> QtGui.QFont
    "pointsize" -> int or float > 0
    
    Individual changes to colours and styles can be made subsequently on the
    QtGui.QPen and QtGui.QBrush instances in the Bunch, using their appropriate
    methods.
    
    Explainer
    =========
    
    Scipyen's GraphicsObject objects are the visible frontend for Scipyen's
    PlanarGraphics. They inherit from on QtWidgets.QGraphicsObject and their 
    purpose is to render a PlanarGraphics in a QGraphicsScene (such as that used
    by Scipyen's ImageViewer).
    
    GraphicsObject instances are built up from simple Qt graphics primitives:
    lines (and curves), circles or squares (representing a 'point'), and text
    (for labels).
    
    Their appearance (visual aspect, or 'look-and-feel', LnF) is standardized in
    order to visually differentiate between the following five 'states':
    
    'control': LnF of control lines, points, and labels (where a 'point' is 
        rawn as a circle, optionally with an opaque background)
        
    'standard, not selected':
        LnF of lines, points and labels for standard, i.e. non-control,
        and non-linked (see below) graphics objects that are NOT selected in the
        scene.
        
    'standard, selected':
        as above, but for graphics obejcts that are selected in the scene
        
    'linked, not selected':
        LnF for graphics objects that are frontends for a common PlanarGraphics
        'backend' (e.g., they render the same PlanarGraphics instance, typically
        in two or more separate scenes); the frontends are NOT selected in their
        respective scenes.
        
    'linked, selected':
        as above, but the graphics objects are selected in their scene.
        
    The "standardization" consists of discrete changes in the specific aspects
    of the GraphicsObject frontend. The simple, general rule, is that selected 
    graphic objects are distinguished from non-selected ones by the style of 
    their lines (and possibly of the background of their labels and points), 
    whereas 'linked' graphics are distinguished from non-linked ones by the 
    colour of their components.
    
    Positional or named parameters:
    ===============================
    linePen, etc: see the schematic above; optional.
        Their default value (for this function) is None, in which case the 
        corresponding key in the inner Bunch will be mapped to a value selected 
        from GraphicsObjectLnF according to the parameters 'control', 'linked'
        and 'selected'
        
    control: bool, default False; when True, the LnF Bunch relates to the
        control lines and points drawn for a PlanarGraphics (currently, only
        non-cursor objects support control elements)
        
    linked: bool, default is False; when True, the LnF Bunch relates to "linked" 
        GraphicsObject instances (i.e. they act as frontends to the same
        PlanarGraphics backend)
        
    selected: bool, default is False; when True, the LnF Bunch relates to the 
        GraphicsObject instance in its 'selected' state.
        
        This parameter is only used when 'linked' is also True
        
    see also: GraphicsObjectLnF in this module
    
    """
    
    kw = dict()
    
    if control:
        kw["control"] = True
        
    elif linked:
        kw["linked"] = True
        if selected:
            kw["selected"] = True
    
    ret = Bunch()
    ret.pen = Bunch()
    ret.pen.line = linePen if isinstance(linePen, QtGui.QPen) else GraphicsObjectLnF.pen(graphic = "pen_line", *kw)
    ret.pen.text = textPen if isinstance(textPen, QtGui.QPen) else GraphicsObjectLnF.pen(graphic = "pen_text", *kw)
    ret.pen.point = pointPen if isinstance(pointPen, QtGui.QPen) else GraphicsObjectLnF.pen(graphics = "pen_point", *kw)
    ret.brush = Bunch()
    ret.brush.text = textBrush if isinstance(textBrush, QtGui.QBrush) else GraphicsObjectLnF.brush(graphic="brush_label", *kw)
    ret.brush.point = pointBrush if isinstance(pointBrush, QtGui.QBrush) else GraphicsObjectLnF.brush(graphic = "brush_point", *kw)
    ret.font = font if isinstance(font, QtGui.QFont) else QtWidgets.QApplication.font()
    ret.pointsize = pointSize if isinstance(pointSize, (int, float)) and pointSize > 0 else GraphicsObjectLnF.pointsize["control"] if control else GraphicsObjectLnF.pointsize["standard"]
    
    return ret

def makeControlLnF(linePen:typing.Optional[QtGui.QPen] = None, 
                   textPen:typing.Optional[QtGui.QPen] = None, 
                   pointPen:typing.Optional[QtGui.QPen] = None, 
                   textBrush:typing.Optional[QtGui.QBrush] = None, 
                   pointBrush:typing.Optional[QtGui.QBrush] = None,
                   font:typing.Optional[QtGui.QFont] = None, 
                   pointSize:typing.Optional[typing.Union[int, float]] = None):
    """Shortcut to generate a LnF Bunch for control graphics"""
    return makeLnFBunch(linePen=linePen, textPen=textPen, pointPen=pointPen,
                        textBrush=textBrush, pointBrush=pointBrush,
                        font=font, pointSize=pointSize, 
                        control=True)
