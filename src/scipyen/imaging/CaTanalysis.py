# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later


"""
Module for analysis of Ca2+ transients (CaTs)

NOTE: 2019-03-18 09:17:24
TODO:
    1) refine detrending (see scipy.signal.detrend):
        1.1) implement configurable break-points 
        1.2) implement "constant" detrending, but with specified value (i.e. 
        customize offset)
        
    2) implement the use of several different EPSCaT models when fitting,
        selectable according to protocol 
        (e.g. for 2epsp50 protocol, a single EPSCaT model doesn't work)

"""

# NOTE: 2017-07-03 21:28:18 
# this is a WORKING routine:
#
# BEGIN PSEUDOCODE
#   1)  find out stimulus delay from start of linescans (because linescanning does NOT
#       start at t0_ephys = 0!)
#       open abf file, view it in signalviewer
#       should visualize ALL axes, importantly the signal axis IN0(mV) IN1 (pA) 
#       and the TRIGGER axis (V)
#       place cursor v0 at onset of bAP-trigger (current injection pulse in IN1 axis) 
#       place cursor v1 at onset of the trigger TTL in TRIGGER axis
#       
#       stimulus delay = v0.x - v1.x
#
#       NOTE: linescan image begins at v1 relative to the electrophysiology data
#       therefore the stimulus (v0 in ephys data) will be at t0 = v0.x - v1.x 
#
#       t0 is the relative  stimulus time since the beginning of linescan
#
#
#       load alexa channel and fluo5 channel == Prairie view saves them as separate TIFF files
#
#       also load the xml file associated with the linescan cycle, open in XML Tree Viewer
#
#       save scanlinePeriod to a variable
#
#       (optionally) purelet the alexa and fluo5 images 
#           CAUTION: they need to be passed as 2D arrays, make sure you call in order:
#
#       dropChannelAxis() THEN np.squeeze()
#
#
#       or, directly: np.squeeze(alexa.dropChannelAxis())
#
#       the above axis reduction is REQUIRED regardless of whether they are filtered or not
#
#
#       visualize each image in its own image viewer, then 
#
#       place VERTICAL cursors in alexa viewer, on the appropriate structures; 
#
#       replicate these cursors in fluo5 image, link recirpcally with the corresponding
#           cursor in alexa image (move one => the other moves by same amount)
#
#       set place cursors on the middle of the structure,adjust xwindow to cover 
#       the width of the structure
#
#       place horizontal cursor in alexa image, adjust ywindow and y coordinate such that its end (bottom end)
#           reaches the onset of the signal (use the scanlinePeriod value to determine
#           cursor coordinates which are in pixels)
#
#       retrieve cursor regions: spanX for the vertical, spanY for the horizontal
#
#       from the xml document (see above) get micronsPerPixelXAxis
#
#           pack sampling data in a tuple
#           
#           sampling = (micronsPerPixelXAxis, scanlinePeriod)
#
#           pack units of measurement:
#
#           units = ( datatypes.arbitrary_units, pq.s)
#
#       CaT = CaTanalysis.computeLSCaT(spanX, spanY, fluo5, alexa, sampling, units, \
#               name="some_name", description="some_description")
#
#
#       CaT is the Ca2+ transient signal (dF/A) as a neo.AnalogSignal object
#
#       define fit prameters for single component signal:
#
#       p0 = [0.1, 0.01, 0.0, 0.01, stimDelay]
#
#       ATTENTION: for epscats, parameters must be bounded on the closed 
#           interval 0 .. +Inf otherwise fitting is unstable (epscats are 
#           upward transients!!!)
#
#       bounds = [0, np.inf] (these will be broadcast to all parameters)
#
#       fit model: (crvf is aliased to the curvefitting module in pict)
#
#       (fc, fcc, res) = crvf.fit_compound_exp_rise_multi_decay(CaT, p0, method="trf", bounds=[0, np.inf], loss="linear")
#
#       read scipy.optimize.least_squares documentation for method and loss options
#
#       compose a new AnalogSignal with two channels:
#
#           a copy of the CaT signal
#
#           the fitted curve
#
#       temp = np.full((CaT.shape[0],2), np.NaN)
#       temp[:,0] = CaT.magnitude[:,0]
#       temp[:,1] = fc
#
#
#       CaTfit = neo.AnalogSignal(temp, units=CaT.units, sampling_period = CaT.sampling_period, \
#           name="%s_fit" % CaT.name)
#
#       view it in SignalViewer
#
# END   PSEUDOCODE


#### BEGIN core python modules
# from __future__ import print_function
import os, sys, traceback, inspect
# try:
#     fi = inspect.getframeinfo(sys._getframe())
#     of = inspect.getouterframes(sys._getframe())
#     ofs = '\n\n'.join([f"{k}: {f}" for k,f in enumerate(of)])
#     print(f"CaTanalysis is being imported from {fi}...\n\nCall stack:\n {ofs}\n\n")
#     
#     # print(f"CaTanalysis is being imported from {sys._getframe(1).f_back.f_code.co_qualname}...\n\n")
#     # print(f"CaTanalysis is being imported from {sys._getframe(1).f_back.f_code.co_filename}...\n\n")
# except:
#     print(f"CaTanalysis is being imported from {sys._getframe().f_back.f_code.co_qualname}...\n\n")
#     # print(f"CaTanalysis is being imported from {sys._getframe().f_back.f_code.co_filename}...\n\n")
import sqlite3
import threading
import numbers
import math
import collections
import warnings
import datetime
import bisect
import typing
from functools import partial
from copy import deepcopy
#### END core python modules

from IPython.core.magic import (Magics, magics_class, line_magic,
                                cell_magic, line_cell_magic,
                                needs_local_scope)

#### BEGIN traitlets
#from traitlets import (HasTraits, Integer, Float, Complex, Unicode, Bytes,
                       #List, Set, Tuple, Dict, Bool, )
#### END

#### BEGIN 3rd party modules
from traitlets import Bunch

from qtpy import QtCore, QtGui, QtWidgets, QtXml
from qtpy.QtCore import Signal, Slot
from qtpy.uic import loadUiType as __loadUiType__ 
# from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml
# from PyQt5.QtCore import Signal, Slot
# from PyQt5.uic import loadUiType as __loadUiType__ 

import numpy as np
import pandas as pd
from scipy import optimize, signal, integrate, spatial, interpolate

import quantities as pq

import neo

from core.vigra_patches import vigra
#### END 3rd party modules

#### BEGIN pict.core modules
import core.tiwt as tiwt
import core.datatypes  
#from core.patchneo import neo
import core.strutils as strutils
import core.curvefitting as crvf
import core.models as models
import core.signalprocessing as sgp
import core.neoutils as neoutils

from core.quantities import (arbitrary_unit, check_time_units, units_convertible, 
                            unit_quantity_from_name_or_symbol, )
from core.datatypes import UnitTypes
from core.workspacefunctions import validate_varname
from core.utilities import (get_nested_value, set_nested_value, counter_suffix, 
                            reverse_mapping_lookup, 
                            get_index_for_seq, 
                            safe_identity_test,
                            eq,
                            sp_set_loc,
                            normalized_index,
                            unique,
                            duplicates,
                            GeneralIndexType,
                            counter_suffix,
                            yyMdd,
                            NestedFinder)

from core.prog import (safeWrapper, safeGUIWrapper, )
#import core.datasignal as datasignal
from core.datasignal import (DataSignal, IrregularlySampledDataSignal)
from core.datazone import DataZone
#import core.triggerprotocols
from core.triggerevent import (DataMark, TriggerEvent, TriggerEventType, )
from core.triggerprotocols import (TriggerProtocol,
                                   auto_detect_trigger_protocols,
                                   parse_trigger_protocols)
#from core.axisutils import (calibration, axisChannelName)
import core.traitcontainers
from core.traitcontainers import DataBag
# from core.traitutils import (trait_from_type, )
# from core.traitutils import (TraitsObserver, trait_from_type, )
                                  
from core.sysutils import adapt_ui_path

#### END pict.core modules

#### BEGIN pict.gui modules
import gui.imageviewer as iv
import gui.signalviewer as sv
import gui.textviewer as tv
import gui.tableeditor as te
import gui.matrixviewer as matview
import gui.pictgui as pgui
import gui.quickdialog as qd
import gui.scipyenviewer as scipyenviewer
from gui.scipyenviewer import (ScipyenViewer, ScipyenFrameViewer)
from gui.workspacegui import (WorkspaceGuiMixin, saveWindowSettings, loadWindowSettings)
from gui.itemslistdialog import ItemsListDialog
from gui import resources_rc
# from gui import resources_rc
#### END pict.gui modules

#### BEGIN imaging modules
from imaging import vigrautils as vu
from imaging.vigrautils import (imageIndexTuple, proposeLayout)
from imaging import imageprocessing as imgp
from imaging.imageprocessing import *

# NOTE: 2024-05-30 14:25:00 see  NOTE: 2024-05-30 14:16:25
from imaging import scandata
from imaging.scandata import (ScanData, AnalysisUnit, check_apiversion, scanDataOptions)
from imaging import axisutils
from imaging.axisutils import dimEnum
from imaging.axiscalibration import (AxesCalibration, 
                              AxisCalibrationData, 
                              ChannelCalibrationData,
                              CalibrationData,  
                              calibration, axisChannelName, getAxisResolution)
#### END imaging modules

#### BEGIN pict.iolib modules
import iolib.pictio as pio
#### END pict.iolib modules
import ephys.ephys as ephys

# NOTE: 2024-05-30 14:16:25 TODO/FIXME
# In the long run, scandata might be better placed in the plugins structure and
# OUT of Scipyen's tree - the pros are that it is a complex data type with a single, 
# well-defined purpose, and for which there is only a single viewer, defined here: 
# LSCaTWindow. Thewrefore, having CaTanalysis as a plugin while keeping scandata for general
# availability in Scipyen does not make much sense.
# 
# The same goes for other related modules and data types (epscat.py)
# 
# Unfortunately, there are plenty of dependencies on scandata, in Scipyen, including:
# iolib/h5io, (for hdf5 export/import)
# systems/PrairieView (which generates ScanData objects)
# gui.dictviewer (for inspecting the ScanData object structure)
# 
# This makes it hard to completely extricate scandata and other CaT analysis stuff
# from the main Scipyeh code tree — but not impossible.
#
# So until we redesign the dependencies, leave scandata INSIDE Scipyen's imaging 
# sub-directory, and bring CaTanalysis back into Scipyen's code tree
# from .. import scandata
# from ..scandata import (ScanData, AnalysisUnit, check_apiversion, scanDataOptions)

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__ui_path__ = adapt_ui_path(__module_path__,"LSCaTWindow.ui")

# print(f"CaTanalysis.py __ui_path__ {__ui_path__}")

# Form class,        Base class                                                                               package with the resources.qrc file
if os.environ["QT_API"] in ("pyqt5", "pyside2"):
    __UI_LSCaTWindow__, __QMainWindow__ = __loadUiType__(__ui_path__, from_imports=True, import_from="gui")
    # __UI_LSCaTWindow__, __QMainWindow__ = __loadUiType__(os.path.join(__module_path__,"LSCaTWindow.ui"), from_imports=True, import_from="gui")
else:
    __UI_LSCaTWindow__, __QMainWindow__ = __loadUiType__(__ui_path__)#, import_from="gui")

def vCursor2ScanlineProjection(v, path, span=None):
    """Maps the x coordinate for a vertical cursor in linescans space (x,y) coordinates on scanline path, in scene space.
    
    Returns the pair (x,y) of coordinates along the scanline "path" in the scene image,
    that correspond to the x coordinate of the vertical cursor "v" in the linescan image.
    
    v : vertical cursor
    
    path: sequence of PlanarGraphics primitive states (Move, Line, Cubic, Quad, see pictgui.curveLength()) - no checks are performed here
    
    span : int or None (optional, default is None) = the width of the linescan
        image in samples (pixels)
        
        When None (the default) the span is taken to be the value of its "width"
        descriptor.
    
    """
    
    def _project_on_path_(value, p, cum_len):
        obj_index = np.where(cum_len >= value)[0]
        
        if len(obj_index):
            obj_index = int(obj_index[0])
            
        else:
            x = y = None
            
            return (x, y)
            
        obj = p[obj_index]
        
        x1, y1 = obj.x, obj.y
        
        if obj_index  == 0:
            return (x1, y1) # assumes it is a Mmove
        
        x0, y0 = p[obj_index-1].x, p[obj_index-1].y
        
        rel_pos = value - cum_len[obj_index-1]
            
        element_len = cum_len[obj_index] - cum_len[obj_index-1] # faster than getting the element to calculate its own length
        
        if all([p in obj for p in ("c1x", "c1y", "c2x", "c2y")]):              # state of a Cubic
            t = np.zeros((8,))
            t[4:] = 1.
            
            c = np.array([[x0, y0], 
                          [obj.c1x, obj.c1y], 
                          [obj.c2x, obj.c2y],
                          [x1, y1]])
            
            spline = interpolate.BSpline(t, c, 3, extrapolate=True)
            
            u = rel_pos/element_len
            
            x, y = spline(u)
            
        elif all([p in obj for p in ("cx", "cy")]):                             # state of a Quad
            t = np.zeros((6,))
            t[3:] = 1.
            
            c = np.array([[x0,y0], 
                          [obj.cx, obj.cy], 
                          [x1, y1]])
            
            spline = interpolate.BSpline(t, c, 2, extrapolate=True)
            
            u_val = rel_pos/element_len
            
            x, y = spline(u_val)
            
        else:                                                                   # state of Move or Line
            dx = x1 - x0
            dy = y1 - y0
            
            alpha = np.arctan
            
            if dx == 0:
                if dy == 0: # point coincides with the coords of the previous point
                    return (x1, y1)
                
                else:
                    alpha = np.pi/2 if dy > 0 else np.pi * 3/2
                    
            elif dy == 0:
                if dx == 0:
                    return (x1, y1)
                
                else:
                    alpha = 0 if dx > 0 else np.pi
                    
            else:
                alpha = np.arctan((dy/dx))
                
            x = rel_pos * np.cos(alpha) + x0
            y = rel_pos * np.sin(alpha) + y0
            
        return float(x), float(y)
    
    if not isinstance(v, pgui.Cursor):
        raise TypeError("Expecting a pictgui.Cursor for the first parameter; got %s instead" % type(v).__name__)
    
    if v.type != pgui.GraphicsObjectType.vertical_cursor:
        raise TypeError("Expecting a vertical cursor for the first parameter; got %s instead" % v.type)
    
    #if not isinstance(path, pgui.PlanarGraphics):
        #raise TypeError("Expecting a pictgui.PlanarGraphics for the second parameter; got %s instead" % type(path).__name__)
    
    if not v.hasStateForFrame(v.currentFrame):
        raise RuntimeError("Vertical cursor %s has no state defined for frame %d" % (v.name, v.currentFrame))
    
    # NOTE: 2018-08-18 23:13:51
    # this is a stand-in for the linescan image width; we map the position of
    # v to a position for p along the path by taking this into account -- not 
    # very wise... 
    if span is None:
        # TODO find a way to get the real width of the linescan image served/scanned
        # by the vertical cursor "v"
        # as workaround, we introduce span as an optional parameter
        span = v.width
    
    if v.x < 0:
        v_pos = 0
        
    elif v.x >= span:
        v_pos = span-1
        
    else:
        v_pos = v.x
        
    if len(path) == 2: # linear interpolation between path's ends
        dx = path[1].x - path[0].x
        dy = path[1].y - path[0].y
        
        ret_x = v_pos * dx / span + path[0].x
        ret_y = v_pos * dy / span + path[0].y
        
    elif len(path) > 2:
        if any([any([p in o for p in ("cx", "cy", "c1x", "c1y", "c2x", "c2y")]) for o in path]): # there are Cubic and Quad states -> interpolate
            path_len, pe_len = pgui.curveLength(path)
        
            cum_pe_len = np.cumsum(pe_len)
            
            ret_x, ret_y = _project_on_path_(v_pos, path, cum_pe_len)
            
        else: # assumes all have "x" and "y" attributes; if this is False, key errors & attribute erroes will be raised 
            if len(path) == int(span): # good chances this is 1 element per pixel in a scan row
                ret_x = path[int(v_pos)].x
                ret_y = path[int(v_pos)].y
                
            else: # use interpolations
                path_len, pe_len = pgui.curveLength(path)
            
                cum_pe_len = np.cumsum(pe_len)
        
                ret_x, ret_y =  _project_on_path_(v_pos, path, cum_pe_len)
                
    else: # len(path) is 1
        ret_x = path[0].x
        ret_y = path[0].y
    
    return (ret_x, ret_y)

def vCursorPos2ScanlineCoords(v, path, span=None):
    """Maps the x coordinate for a vertical cursor in linescans space (x,y) coordinates on scanline path, in scene space.
    
    Returns the pair (x,y) of coordinates along the scanline "path" in the scene image,
    that correspond to the x coordinate of the vertical cursor "v" in the linescan image.
    
    v : vertical cursor
    
    path: planar graphics defining the scanning trajectory in the scene
    
    span : int or None (optional, default is None) = the width of the linescan
        image in samples (pixels)
        
        When None (the default) the span is taken to be the value of its "width"
        descriptor.
    
    """
    
    def _get_coords_for_proj_pos_on_path_(value, p, cum_len):
        obj_index = np.where(cum_len >= value)[0]
        
        #print(obj_index)
        
        #print("_get_coords_for_proj_pos_on_path_ value ", value)
        
        if len(obj_index):
            obj_index = int(obj_index[0])
            
        else:
            #print("_get_coords_for_proj_pos_on_path_ obj not found")
                    
            x = y = None
            
            return (x, y)
            
        obj = p[obj_index]
        
        #print("_get_coords_for_proj_pos_on_path_ obj_index: %d, %s, %s" % (obj_index, type(obj).__name__, obj.type))
        
        x1, y1 = obj.x, obj.y
        
        if obj_index  == 0:
            if isinstance(obj, pgui.Move):
                #print("_get_coords_for_proj_pos_on_path_ return on first Move", (x1, y1))
                return (x1, y1)
                
            x0 = y0 = 0.
            rel_pos = value
        
        else:
            x0, y0 = p[obj_index-1].x, p[obj_index-1].y
            
            #print(" prev object: %s, %s" % (type(p[obj_index-1]).__name__, p[obj_index-1].type), (x0, y0))
            
            rel_pos = value - cum_len[obj_index-1]
            
        
        #print("_get_coords_for_proj_pos_on_path_ rel_pos", rel_pos)
        
        element_len = cum_len[obj_index] - cum_len[obj_index-1] # faster than getting the element to calculate its own length
        
        if isinstance(obj, (pgui.Line, pgui.Move)): # include Move for subpaths
            dx = x1 - x0
            dy = y1 - y0
            
            alpha = np.arctan
            
            if dx == 0:
                if dy == 0: # points on the Line coincides with the coords of the previous point
                    return (x1, y1)
                
                else:
                    alpha = np.pi/2 if dy > 0 else np.pi * 3/2
                    
            elif dy == 0:
                if dx == 0:
                    return (x1, y1)
                
                else:
                    alpha = 0 if dx > 0 else np.pi
                    
            else:
                alpha = np.arctan((dy/dx))
                
            x = rel_pos * np.cos(alpha) + x0
            y = rel_pos * np.sin(alpha) + y0
            
        elif isinstance(obj, pgui.Cubic):
            #t = np.zeros((8,))
            #t[4:] = 1.

            #c = np.array([[x0, y0], [obj.c1x, obj.c1y], [obj.c2x, obj.c2y], [x1, y1]])
            
            #k = 3

            #spline = interpolate.BSpline(t, c, k, extrapolate=True)
            
            spline = obj.makeBSpline([x0, y0])
            
            u = rel_pos/element_len
            
            x, y = spline(u)
            
        elif isinstance(obj, pgui.Quad):
            #t = np.zeros((6,))
            #t[3:] = 1.
            
            #c = np.array([[x0,y0], [obj.cx, obj.cy], [x1, y1]])
            
            #k = 2
            
            #spline = interpolate.BSpline(t, c, k, extrapolate=True)
            
            spline = obj.makeBSpline([x0, y0])
            
            u_val = rel_pos/element_len
            
            #x, y = interpolate.splev(u_val, tck)
            x, y = spline(u_val)
            
            #print(" _get_coords_for_proj_pos_on_path_ on Quad", (x,y))
            #return float(x), float(y)

        else:
            raise NotImplementedError("Function is not implemented for %s objects (:class: %s)" % (obj.type, type(obj).__name__))
                    
        #print("_get_coords_for_proj_pos_on_path_", (x,y))
                    
        return float(x), float(y)
    
    if not isinstance(v, pgui.Cursor):
        raise TypeError("Expecting a pictgui.Cursor for the first parameter; got %s instead" % type(v).__name__)
    
    if v.type != pgui.GraphicsObjectType.vertical_cursor:
        raise TypeError("Expecting a vertical cursor for the first parameter; got %s instead" % v.type)
    
    if not isinstance(path, pgui.PlanarGraphics):
        raise TypeError("Expecting a pictgui.PlanarGraphics for the second parameter; got %s instead" % type(path).__name__)
    
    if not v.hasStateForFrame(v.currentFrame):
        raise RuntimeError("Vertical cursor %s has no state defined for frame %s" % (v.name, v.currentFrame))
    
    # NOTE: 2018-08-18 23:13:51
    # this is a stand-in for the linescan image width; we map the position of
    # v to a position for p along the path by taking this into account -- not 
    # very wise... 
    if span is None:
        # TODO find a way to get the real width of the linescan image served/scanned
        # by the vertical cursor "v"
        # as workaround, we introduce span as an optional parameter
        span = v.width if v.width > 0 else 1
        
    if span == 0:
        span =1
        
    if not isinstance(path, pgui.Path):
        raise TypeError("Expecting a Path object; got %s instead" % type(path).__name__)
    
    # ATTENTION: a pgui.Path with two points (Move, Line) encapsulates a 
    # straight line segment !
    
    #print("v.currentFrame", v.currentFrame)
    
    if isinstance(v.currentFrame, int):
        currentPath = path.asPath(v.currentFrame)
        
    else:
        currentPath = path.asPath(0)
    
    if currentPath is None or len(currentPath) == 0:
        #warnings.warn("%s object has no state defined for frame %s" % (path.name, v.currentFrame), RuntimeWarning)
        #raise RuntimeError("%s object has no state defined for frame %d" % (path.name, v.currentFrame))
    
        return None, None
    
    #print("vCursorPos2ScanlineCoords span", span)
    
    if v.x < 0:
        v_pos = 0
        
    elif v.x >= span:
        v_pos = span-1
        
    else:
        v_pos = v.x
        
    if all([isinstance(e, (pgui.Move, pgui.Line)) for e in currentPath]):
        # a line segment, a polyline or a polygon of line segments
        
        if len(currentPath) == 2: 
            # a simple line segment -- by definition it should span the entire 
            # linescan width (span)
            
            assert currentPath.type & (pgui.GraphicsObjectType.line | pgui.GraphicsObjectType.polyline)
            
            dx = currentPath[1].x - currentPath[0].x
            dy = currentPath[1].y - currentPath[0].y
            
            ret_x = v_pos * dx / span + currentPath[0].x
            ret_y = v_pos * dy / span + currentPath[0].y
                
            #return ret_x, ret_y
        
        elif len(currentPath) > 2:
            # NOTE: 2018-08-19 10:01:28
            # there are three situations:
            # a) there are as many elements as pixels in the linescan width 
            # (i.e., the "span") => each element in the currentPath maps to 
            # a sample along the linescan axis
            #
            # b) there are fewer elements than pixels in the span, which means
            # we need to interpolate inside each of the scanline segments
            #
            # c) that there are more elements than pixels in the linescan width, 
            # but I think this is practically impossible, as it would mean 
            # the scanning trajectory was oversampled
            #
            # NOTE: 2018-09-20 21:54:53 Case (c) could actually happen when
            # after concatenating linescan images fom scandata objects
            # will result in linescan width smaller that the number of elements
            # in the scanline path (in turn this will happen when the concatenated
            # linescans need to be resampled along the spatial axis, followed by
            # adjustments to the width of the linescan image)
            
            if len(currentPath) == int(span):
                # case (a) -- straightforward
                element = currentPath[int(v_pos)]
                ret_x = element.x
                ret_y = element.y
                
            else:
                # all other cases
                
                path_len, pe_len = currentPath.curveLength()
            
                cum_pe_len = np.cumsum(pe_len)
        
                ret_x, ret_y =  _get_coords_for_proj_pos_on_path_(v_pos, currentPath, cum_pe_len)
                
        else: # len is 1 
            ret_x = currentPath[0].x
            ret_y = currentPath[0].y
        
    elif all([isinstance(e, (pgui.Move, pgui.Line, pgui.Cubic, pgui.Quad)) for e in currentPath]):
        # a more complex shape, composed of Move, Line, Cubic and/or Quad
        
        path_len, pe_len = currentPath.curveLength()
    
        cum_pe_len = np.cumsum(pe_len)
        
        ret_x, ret_y = _get_coords_for_proj_pos_on_path_(v_pos, currentPath, cum_pe_len)
                
    else:
        raise NotImplementedError("Only paths composed of line segments and cubic curves are supported")
    
    #print("vCursorPos2ScanlineCoords", (ret_x, ret_y))
    
    return (ret_x, ret_y)

def mapScansVCToScenePCOnPath(v, p, path, span=None):
    """Maps the X coordinate of vertical cursor to a point cursor position on a path.
    
    ATTENTION: This is implemented only for the cases when the scanline is 
    1) a line defined by two points ("simple" or "classical" line scan trajectory)
    
    2) a polyline (Move and Line elements) where each element is mapped 1:1 to 
        the pixels in a row of the linescan image (a.k.a "freehand line" in 
        PrairieView) such that every integral X coordinate of the vertical cursor
        falls on an element in the scaline (scanRegion) path
    
    3) a Path with fewer elements than columns in the linescan image, and composed
        of Move, Line, Cubic or Quad curves. This is something obtained by
        "simplifying" a PrairieView free hand scanline.
    
    v : the vertical cursor
    
    p:  the point cursor
    
    path: the path along which the position of the point cursor "p" is set according
        to the X coordinate of the vertical cursors "v" and this mapping function
        
        This is a non-cursor pictgui.PlanarGraphics object
        
    span: None (default) or an int: the scan image width.
        When None, the vertical cursor's width attribute is used.
        
        A scan image of composed by repeated scanning along the scanline: each 
        row is the result of one such scanning. Therefore, a possibly curved
        path or polyline in the scene space is "mapped" to the 1D space of one
        row in the scan image.
        
        This function tries to "reverse-map" the X-coordinate of the vertical
        cursor (defined in the scan image space), to the XY coordinates of a 
        point on the scanline path in the 2D space of the scene image.
        
        Therefore, the length of the scanline path in the 2D space of the scene 
        image is considered to be mapped onto the entire width of the scan image, 
        or if this is not known, to the "width" attribute of the vertical cursor.
        
        Since this function is unaware of the image data, the scan image width
        may be given via the "span" parameter.
     
    """
    # CAUTION Path may NOT have a point for every X coordinate of the cursor
    
    # FIXME: 2018-08-18 10:17:47
    # we don't have direct access to the linescan width; we therefore assume 
    # that the vertical cursor's "width" parameter (for the current frame) is 
    # set to cover the entire width of the linescan image (and therefore we use 
    # this value in mapping the position of the vertical cursor onto the
    # position of the point cursor along the scanning path) 
    # WARNING: this will breakdown if for any reason the vertical cursor "width"
    # parameter gets changed, because in the maping process we map this width to
    # the entire path length.
    
    #print("mapScansVCToScenePCOnPath path.hasStateForFrame(%s): %s " % (v.currentFrame, path.hasStateForFrame(v.currentFrame)))
    
    #if not v.hasStateForFrame(v.currentFrame):
        #return
    
    #if not path.hasStateForFrame(v.currentFrame):
        #return
    
    if span is None:
        if len(v.frontends):
            pw = v.frontends[0].parentWidget
        
            if type(pw).__name__ == "ImageViewer":
                v.width = pw.imageWidth
                
        if v.width == 0:
            v.width = 1
        
        span = v.width # this is the stand-in for the linescan image width; we map 
                    # the position of v to a position for p along the path by
                    # taking this into account -- not very wise... 
                    # TODO find a way to get the real width of the linescan image
                    # served by the vertical cursor "v"
    
    if isinstance(path, pgui.Path):
        (point_x, point_y) = vCursorPos2ScanlineCoords(v, path, span=span)
        
    else:                                                                       # path is a sequence of states
        (point_x, point_y) = vCursor2ScanlineProjection(v, path, span=span)
    
    #print("mapScansVCToScenePCOnPath", (point_x, point_y))
    
    # apply the new coordinates to the point cursor "p"
    if not any([v is None for v in (point_x, point_y)]):
        p.x = point_x
        p.y = point_y
    
#@safeWrapper
def epscatDiscriminator(base, peak, func, pred, predValue, predFunc):#, accFcnBase, accFcnPeak, predFcn, predicate):
    """
    base, peak: single-channel 2D vigra.VigraArray, neo.AnalogSignals, datatypes.DataSignals or 1D numpy.ndarrays
    
    func:       tuple (str, dict): str = name of unary array function; dict = kwargs of function
    predFunc:   str: name of predicate function: binary function
    pred:       str: name of binary function returning a boolean (literally a comparison function) = "the predicate"
    predValue:  float: value to compare against the result of predFunc, using pred as comparator
    
    NOTE: an "unary array" function takes one np.ndarray argument and returns a scalar
    NOTE: a "binary" function takes two scalar arguments and returns a scalar
    
    """
    base_value = eval(func[0])(base, **func[1]) ** 2
    
    peak_value = eval(func[0])(peak, **func[1]) ** 2
    
    #print("base_value ", base_value)
    #print("peak_value ", peak_value)
    
    peak_base_value = eval(predFunc)(peak_value, base_value)
    
    return eval(pred)(peak_base_value, predValue), peak_value, base_value, peak_base_value

def getTimeSlice(scandata, t0, t1):
    """Returns a time slice of the linescans
    """
    cal = calibration(scandata.scans[0].axistags["t"])
    
    start = int(t0.magnitude / cal[2] + cal[1])
    
    stop = int(t1.magnitude / cal[2] + cal[1])
    
    scene = scandata.scene
    
    scans = [scan[:,start:stop,...] for scan in scandata.scans]
    
    ephys = ephys.get_time_slice(scandata.electrophysiology, t0, t1)
    
    ret = ScanData(scene, scans, 
                      electrophysiology=ephys, 
                      sceneFrameAxis = scandata.sceneFrameAxis,
                      scansFrameAxis = scandata.scansFrameAxis,
                      name = scandata.name,
                      analysisOptions = scandata.analysisOptions)
    
    ret.adoptTriggerProtocols(ephys)
    ret.sceneCursors.update(scandata.sceneCursors)
    ret.sceneRois.update(scandata.sceneRois)
    ret.scansCursors.update(scandata.scansCursors)
    ret.scansRois.update(scandata.scansRois)
    
    if len(scandata.scansBlock.segments) > 0:
        scansblock = ephys.get_time_slice(scandata.scansBlock, t0, t1)
        ret.scansBlock.segments[:] = scansblock.segments
        
    ret._scandatatype_ = scandata._scandatatype_
    ret._analysismode_ = scandata._analysismode_
    
    ret.__processed__ = scandata.__processed__
        
    return ret
    
def getProfile(scandata, roi, scene=True):
    """Generates scanline profiles from roi's contour in scene or scans.
    
    Does this for all available channels.
    
    The only required user input is to choose between raw and 
    filtered data for generating the profiles.
    
    TODO: not yet written!
    
    Parameters:
    ==========
    scandata: a datatypes.ScanData object
    
    roi: a shaped pictgui.PlanarGraphics object (i.e., not a pictgui.Cursor)
        or a vigra.AxisInfo object (in which case the _AVERAGE_ profile along the
        next higher orthogonal axis is returned)
        
    
    """
    
    if not isinstance(scandata, ScanData):
        raise TypeError("First parameter was expected to be a datatypes.ScanData; got %s instead" % type(scandata).__name__)
    
    
    if not isinstance(roi, (pgui.PlanarGraphics, vigra.AxisInfo)):
        raise TypeError("Second parameter was expected to be a pictgui.PlanarGraphics object or a vigra.AxisInfo object None; got %s instead" % type(roi).__name__)
    
    if isinstance(roi, pgui.PlanarGraphics) and roi.type % pgui.GraphicsObjectType.allCursors:
        raise TypeError("Second parameter was expected ot be a shaped PlanarGraphics; got %s instead" % roi.type)
    
    
    
    if scandata.analysisMode != ScanData.ScanDataAnalysisMode.frame:
        raise NotImplementedError("%s analysis not yet supported" % self.analysisMode)
    
    if scandata.scanType != ScanData.ScanDataType.linescan:
        raise NotImplementedError("%s not yet supported" % self.scanType)
    
def averageEPSCaTs(scandata, epscatname, frame_index = None):
    if not isinstance(scandata, ScanData):
        raise TypeError("Expecting a datatypes.ScanData object as the first parameter; got %s instead" % type(scandata).__name__)
    
    if len(scandata.scansBlock.segments) == 0:
        return
    
    if not isinstance(epscatname, str):
        raise TypeError("epscat name was expected to be a str; got %s instead" % type(epscat).__name__)
    
    
    if isinstance(frame_index, TriggerProtocol):
        frame_index = frame_index.segmentIndices()
    
    ret = ephys.average_segments_in_block(scandata.scansBlock, signal_index=epscatname, segment_index = frame_index)
    
    return ret

def analyseLSData(*args, **kwargs):
    """Batch analysis, useful for bulk (re-) analysis of ScanData objects.
    
    all analysisOptions are stored in the ScanData objects.
    
    Var-positional parameters:
    =========================
    args = sequence of ScanData objects;
    
    Var-named parameters:
    =====================
    kwargs: named parameters for the module-level function analyseFrame()
    
    """
    
    for data in args:
        if not isinstance(data, ScanData):
            raise TypeError("Expecting a datatypes.ScanData; got %s instead" % type(data).__name__)
        
        for frame in range(data.scansFrames):
            analyseFrame(data, frame, **kwargs)
    
#@safeWrapper
def analyseEPSCaT(lsdata, frame, indicator_channel_ndx, 
                  unit = None, reference_channel_ndx=None, do_fit = True,
                  detrend=False):
    """Calculates EPSCaT trace and optionally fits an EPSCaT model.
    
    The EPSCaT waveform is computed on an AnalysisUnit!
    
    Uses analysisOptions stored in lsdata.
    
    lsdata: a ScanData object
    
    """
    
    # NOTE 2018-08-02 15:50:46
    # apply discriminant AFTER computing the EPSCaT waveform
    # see NOTE:  2018-08-02 15:52:31 and NOTE: 2018-08-03 09:50:49
    #
    # NOTE: 2018-08-02 13:16:30
    # compute waveform amplitude AFTER computing the EPSCaT
    # so that if needed, we use the fitted delay
    # see NOTE: 2018-08-02 13:10:32
    #
    
    # NOTE: 2018-08-03 09:31:28
    # suitable defaults for discrimination
    discr_func={'np.linalg.norm': {'axis': None, 'ord': None}}
    discr_pred_func='lambda x,y: x/y'
    discr_pred='lambda x,y: x >= y'
    discr_value=1.3 
    min_r2_discr = 0.5
    discr_2D = True

    # NOTE: protocol will help establish the discrimination windows
    # according to triggers if so required by the analysisOptions
    
    protocol = None
    
    if not isinstance(lsdata, ScanData):
        raise TypeError("First parameters was expected to be a datatypes.ScanData; got %s instead" % type(lsdata).__name__)
    
    if len(lsdata.scans) == 0:
        raise ValueError("no linescan data was found in %s" % lsdata.name)
    
    if lsdata.scanType != ScanData.ScanDataType.linescan:
        raise ValueError("%s was expected to be a ScanData.ScanDataType.linescan experiment; it has %s instead" % (lsdata.name,lsdata.scanType))
        
    if lsdata.analysisMode != ScanData.ScanDataAnalysisMode.frame:
        raise ValueError("%s was expected to have a ScanData.ScanDataAnalysisMode.frame analysis mode; it has %s instead" % (lsdata.name, lsdata.analysisMode))
        
    if len(lsdata.analysisOptions) == 0:
        raise ValueError("%s has no analysis options" % lsdata.name)
    
    # NOTE: use analysis unit instead of cursor, but allow for cursor to be 
    # specified
    # the analysis unit/cursor determines the spatial boundaries (i.e., on X axis)
    # of the EPSCaT signal
    # 
    # the protocol associated with the frame is a gateway to various triggers
    #
    if isinstance(unit, pgui.Cursor) and unit.type == pgui.GraphicsObjectType.vertical_cursor:
        # NOTE: 2018-04-09 17:10:02
        # use a scan vertical cursor instead of a unit;
        # the cursor might not be associated with a unit 
        
        if len(lsdata.analysisUnits) > 0 and unit in [u.landmark for u in lsdata.analysisUnits]:
            units = [u for u in lsdata.analysisUnits if u.landmark == unit]
            
            if len(units) > 1:
                raise RuntimeError("Specified cursor appears to be associated with %d units in %s" % (len(units), lsdata.name))
            
            cursor_unit = units[0]
            
            cursor = cursor_unit.landmark
            
            protocol = cursor_unit.protocol(frame)
            
        else:
            # a verical scans cursor NOT associated with an analysis unit
            if unit not in lsdata.scansCursors.values():
                raise RuntimeError("Cursor %s does not appear to be defined in the %s data linescans images" % (unit.name, lsdata.name))
            
            cursor = unit
            
            if frame not in cursor.frameIndices:
                raise RuntimeError("Current frame (%d) does not appear to be associated with cursor %s" % (frame, cursor.name))
            
            protocol = lsdata.triggerProtocol(frame)
        
    elif isinstance(unit, str):
        # NOTE: 2018-04-09 17:10:57
        # allow a single analysis unit to be specified by its name
        
        if len(lsdata.analysisUnits) == 0 or unit not in [u.name for u in lsdata.analysisUnits]:
            raise ValueError("Specified unit (%s) does not exist in %s" % (unit, lsdata.name))
        
        analysisunits = [u for u in lsdata.analysisUnits if u.name  == unit]
        
        if len(analysisunit) > 1:
            raise RuntimeError("%s appears to contain several units with the same name %s" % (lsdata.name, unit))
        
        unit = analysisunits[0]
        
        cursor = unit.landmark
        
        protocol = unit.protocol(frame)
        
    elif isinstance(unit, AnalysisUnit):
        if len(lsdata.analysisUnits) == 0 and unit != lsdata.analysisUnit():
            raise ValueError("Unit %s not found in %s" % (unit, lsdata.name))
        
        else:
            if unit != lsdata.analysisUnit() and unit not in lsdata.analysisUnits:
                raise ValueError("Unit %s not found in %s" % (unit, lsdata.name))
            
        cursor = unit.landmark
        
        protocol = unit.protocol(frame)
            
    elif unit is None:
        unit = lsdata.analysisUnit()
        
        protocol = lsdata.triggerProtocol(frame)

        cursor = None
        
    else:
        raise TypeError("'unit' expected to be a datatypes.AnalysisUnit object, a vertical pictgui.Cursor, or None; got %s instead" % type(unit).__name__)
    
    # NOTE: determine roiRange: the spatial boundaries of the data
    # (i.e. the spread along the x axis)
    # NOTE: use the cursor name to compose the name of the EPSCaT object
    if cursor is None:
        # needed when the whole image is ONE analysis unit
        roiRange = [0, lsdata.scans[0].shape[0]] # dodgy! what if it's transposed?
        
        if hasattr(lsdata, "unit_name") and isinstance(lsdata.unit_name, str) and len(lsdata.unit_name):
            # NOTE: this is for old API
            epscatname = lsdata.unit_name
            
        elif hasattr(lsdata, "__analysis_unit__") and isinstance(lsdata.__analysis_unit__, AnalysisUnit):
            epscatname = lsdata.analysisUnit().name
            
        else:
            epscatname = "EPSCaT"
        
    elif len(cursor.frameIndices) > 0:
        if frame in cursor.frameIndices:
        #print("analyseEPSCaT frame %d, cursor %s" % (frame, cursor.name))
            state = cursor.getState(frame)
            
            roiRange = [int(state.x - state.xwindow//2), int(state.x + state.xwindow//2)]
            
            if roiRange[0] < 0:
                roiRange[0] = 0
                
            epscatname = "%s" % cursor.name
            
        elif len(cursor.frameIndices) == 1 and cursor.frameIndices[0] is None:
            roiRange = [int(cursor.x - cursor.xwindow//2), int(cursor.x + cursor.xwindow//2)]
            
            if roiRange[0] < 0:
                roiRange[0] = 0
                
            epscatname = "%s" % cursor.name
        
    else:
        warnings.warn("Cannot determine spatial boundaries for EPSCaT in frame %d of %s" % (frame, lsdata.name))
        return
        #raise RuntimeError("Cannot determine spatial boundaries for EPSCaT in frame %d of %s" % (frame, lsdata.name))
    
    # NOTE: determine the f0Range: the temporal boundaries of the F0 (on the t axis)
    #
    cal = AxesCalibration(lsdata.scans[0].axistags["t"])
    units = cal.getUnits(lsdata.scans[0].axistags["t"])
    origin = cal.getOrigin(lsdata.scans[0].axistags["t"])
    resolution = cal.getResolution(lsdata.scans[0].axistags["t"])
    
    f0TimeRange = lsdata.analysisOptions["Intervals"]["F0"]
    
    f0Range = [int((t + origin)/resolution) for t in f0TimeRange]
    
    # NOTE: define (extract) the spatially bounded EPSCaT data in the indicator channel
    
    if len(lsdata.scans) == lsdata.scansChannels:
        # array of possibily several single-band images
        ca_data = lsdata.scans[indicator_channel_ndx].bindAxis("c", 0).bindAxis(lsdata.scansFrameAxis, frame).squeeze()
    
    else:
        # array with one multi-band image
        ca_data = lsdata.scans[0].bindAxis("c", indicator_channel_ndx).bindAxis(lsdata.scansFrameAxis, frame).squeeze()
    
    # NOTE: define the spatially bounded reference data (in the reference channel)
    # if it exists
    ref_data = None
    
    if reference_channel_ndx is not None:
        if len(lsdata.scans) == lsdata.scansChannels:
            ref_data = lsdata.scans[reference_channel_ndx].bindAxis("c",0).bindAxis(lsdata.scansFrameAxis,frame).squeeze()
            
        else:
            ref_data = lsdata.scans[0].bindAxis("c",reference_channel_ndx).bindAxis(lsdata.scansFrameAxis,frame).squeeze()
        
    # NOTE: 2018-08-03 09:46:21
    # EPSCaT waveform computed here
    epscat = computeLSCaT(roiRange, f0Range, 
                          ca_data, 
                          ref_data = ref_data,
                          name=epscatname, units=arbitrary_unit,
                          detrend=detrend)
        
    # NOTE: 2018-08-03 10:04:57
    # EPSCaT waveform fitted here
    if do_fit:
        fit_p0    = lsdata.analysisOptions["Fitting"]["Initial"] # initial parameter values for the EPSCaT model
                                                                 # and their
        fit_lower = lsdata.analysisOptions["Fitting"]["Lower"]   # lower boundaries
        fit_upper = lsdata.analysisOptions["Fitting"]["Upper"]   # upper boundaries 
        
        fitWindow = lsdata.analysisOptions["Intervals"]["Fit"]   # signal is fitted within these temporal boundaries
        
        integrationInterval = lsdata.analysisOptions["Intervals"]["Integration"][1] # interval for the integration of the fitted curve
        
        # NOTE: 2018-08-03 09:59:13
        # fitted_EPSCaT contains BOTH the EPSCaT waveform and the fitted waveform(s)
        # 
        # NOTE there may be more than one fitted waveform
        #
        # NOTE all waveforms are packed as "channels" in the datatypes.DataSignal
        # i.e. as column vectors with a common time base
        #
        # NOTE: EPSCaT waveform is column 0, fitted EPSCaT is on column 1
        # and individual EPSCaT components (for a compound EPSCaT) are in order
        # on the next columns
        #
        # NOTE: therefore fitted_epscat contains AT LEAST two columns
        #
        try:
            fitted_epscat = fitEPSCaT(epscat, fit_p0, (fit_lower, fit_upper),
                                    fitWindow = fitWindow,
                                    integration = integrationInterval)
        except Exception as e:
            fitted_epscat = None
            traceback.print_exc()
            print("In analyseEPSCaT %s in frame %d of %s\n:" % (epscatname, frame, lsdata.name))
            raise e
    else:
        fitted_epscat = None
                
    # NOTE: 2018-08-03 09:49:38
    # Failure/Success discrimination calculated here on the EPSCaT signal
    # also calculate EPSCaT amplitude (both rely on the chosen method of 
    # determining the temporal boundaries for baseline and peak regions)
    # we have suitable defaults defined at NOTE: 2018-08-03 09:31:28
    # in case lsdata.analysisOptions does not provide them
    if "Discrimination" in lsdata.analysisOptions:
        discr_func      = lsdata.analysisOptions["Discrimination"].get("Function", discr_func)
        discr_pred_func = lsdata.analysisOptions["Discrimination"].get("PredicateFunc", discr_pred_func)
        discr_pred      = lsdata.analysisOptions["Discrimination"].get("Predicate", discr_pred)
        discr_value     = lsdata.analysisOptions["Discrimination"].get("PredicateValue", discr_value)
        discr_2D        = lsdata.analysisOptions["Discrimination"].get("Discr_2D", discr_2D)
        min_r2_discr    = lsdata.analysisOptions["Discrimination"].get("MinimumR2", min_r2_discr)
        
        

    #except:
        #pass # suitable defaults defined at the beginning of function at NOTE: 2018-08-03 09:31:28
        
    # NOTE: 2018-08-03 09:43:44
    # set up the intervals for failure/success (FS) discrimination and for the
    # calculation of waveform amplitude
    #
    # NOTE: we need a "baseline" region and a "peak" region for each transient
    # in the EPSCaT; 
    # these two regions will be used for FS discrimination, but also to calculate
    # waveform amplitude on the interval from the beginning of the "baseline" to
    # the end of the "peak"
    
    d_base_window   = int((lsdata.analysisOptions["Discrimination"]["BaseWindow"] + origin)/resolution)
    
    d_peak_window   = int((lsdata.analysisOptions["Discrimination"]["PeakWindow"] + origin)/resolution)
    
    d_base = ()
    d_peak = ()
    d_value = ()
    
    # NOTE: protocols are needed here only to query their trigger time stamps
    # and NOT for determining which frame to analyse; this is done in
    # analyse LSData
    if lsdata.analysisOptions["Discrimination"]["WindowChoice"] == "triggers":
        if protocol is None:
            raise RuntimeError("Analysis options require triggers for discrimination windows but no protocol could be found for frame %d" % frame)
    
        triggers = list()
    
        if hasattr(protocol, "imagingDelay"):
            img_del = (protocol.imagingDelay + origin)/resolution

        else:
            img_del = 0
            
        presyn = protocol.presynaptic
        
        postsyn = protocol.postsynaptic
            
        photo = protocol.photostimulation
            
        #print("img_del", img_del)
        
        #if protocol.presynaptic is not None and len(protocol.presynaptic):
        if presyn is not None and presyn.size > 0:
            #print("presyn", presyn)
            #print("presyn times", presyn.times)
            if presyn.size == 1:
                triggers.append((presyn.times + origin)/resolution - img_del)
                
            else:
                triggers.append((presyn.times[0] + origin)/resolution - img_del)
            
        #if protocol.postsynaptic is not None and len(protocol.postsynaptic):
        if postsyn is not None and postsyn.size > 0:
            #print("postsyn", postsyn)
            #print("postsyn times", postsyn.times)
            if postsyn.times.size ==1:
                triggers.append((postsyn.times + origin)/resolution - img_del)
            else:
                triggers.append((postsyn.times[0] + origin)/resolution - img_del)
            
        #if protocol.photostimulation is not None and len(protocol.photostimulation):
        if photo is not None and photo.size > 0:
            #print("photo", photo)
            #print("photo times", photo.times)
            if photo.times.size == 1:
                triggers.append((photo.times + origin)/resolution - img_del)
            else:
                triggers.append((photo.times[0] + origin)/resolution - img_del)
                
            
        if len(triggers):
            triggers.sort()
            
            if lsdata.analysisOptions["Discrimination"]["First"]:
                d_base = [(int(min(triggers) - d_base_window), int(min(triggers)))]
                d_peak = [(int(min(triggers)), int(min(triggers) + d_peak_window))]
                
            else:
                d_base = [(int(t - d_base_window), int(t)) \
                            for t in triggers]
                
                d_peak = [(int(t), int(t + d_peak_window)) \
                            for t in triggers]
            
        else:
            raise RuntimeError("Analysis options require triggers for discrimination windows but no triggers could be found for frame %d" % frame)
            
    elif lsdata.analysisOptions["Discrimination"]["WindowChoice"] == "delays":
        # NOTE: 2018-08-02 16:22:34
        # use fitted delay if fitted_epscat is not None, 
        # else use initial delay value given in the EPSCaT model in analysisOptions
        
        if fitted_epscat is not None:
            # use the fitted delay to calculate the discrimination windows
            delays = [(p[-1]*units + origin)/resolution\
                        for p in fitted_epscat.annotations["FitResult"]["Coefficients"]]
        
        else:
            # use delays as given in the initial parameter values for the EPSCaT fit model
            delays = [(p[-1]*units + origin)/resolution \
                        for p in lsdata.analysisOptions["Fitting"]["Initial"]]
            
        d_base = [(int(delay - d_base_window), int(delay)) \
                    for delay in delays]
        
        d_peak = [(int(delay), int(delay + d_peak_window)) \
                    for delay in delays]
        
        if lsdata.analysisOptions["Discrimination"]["First"]:
            d_base = [d_base[0]]
            d_peak = [d_peak[0]]
            
    elif lsdata.analysisOptions["Discrimination"]["WindowChoice"] == "cursors":
        h_cursors = sorted([(n,c) for (n,c) in lsdata.scansCursors.items()
                        if cbase.type == pgui.GraphicsObjectType.horizontal_cursor],
                        key = lambda x: x[1].y)
        
        if len(h_cursors) == 0:
            raise RuntimeError("No horizontal cursors are defined for the linescans")
        
        if len(h_cursors) % 2 == 0:
            baseCursors = h_cursors[slice(0, len(cursors), 1)]
            peakCursors = h_cursors[slice(1, len(cursors), 2)]
            
            d_base = [(int((c.y - c.ywindow//2 + origin.magnitude.flatten()[0])/resolution.magnitude.flatten()[0]), int((c.y + c.ywindow//2 + cal.origin.magnitude.flatten()[0])/cal.resolution.magnitude.flatten()[0])) \
                        for c in baseCursors]
            
            d_peak = [(int((c.y - c.ywindow//2 + origin.magnitude.flatten()[0])/resolution.magnitude.flatten()[0]), int((c.y + c.ywindow//2 + cal.origin.magnitude.flatten()[0])/cal.resolution.magnitude.flatten()[0])) \
                        for c in peakCursors]
            
        if lsdata.analysisOptions["Discrimination"]["First"]:
            d_base = [d_base[0]]
            d_peak = [d_peak[0]]
            
    # NOTE: 2018-02-01 08:52:26
    # at this point, d_peak is a list with either a single (beign, end) tuple, 
    # or several such tuples, one for each EPSCaT component;
    # NOTE: an EPSCaT component is a resolvable Ca2+ trasient which can have
    # one or several deday components
    # NOTE: compound EPSCaTs contain several EPSCaT components (e.g., 
    # elicited during a paired pulse stimulation where the inter-stimulus 
    # interval is large enough to allow each EPSCaT component to be resolved)

                
    # NOTE: 2018-08-02 15:52:31
    # perform FS discrimination on the EPSCaT waveform
    #
    # use "epscat" object instead of "fitted_epscat" (which although it contains
    # the EPSCaT waveform as the first channel, it only exists if doFit is True,
    # see NOTE: 2018-08-03 10:04:57)
    # 
    value       = list()
    success     = list()
    base_value  = list()
    peak_value  = list()
    
    # NOTE: 2018-08-03 09:50:49
    # FS discrimination code
    if len(d_base) and len(d_peak) and len(d_base) == len(d_peak) and \
    discr_func is not None and discr_pred_func is not None and \
    discr_value is not None and discr_pred is not None:
        for k_epscat, (base, peak) in enumerate(zip(d_base, d_peak)):
            if base[1] <= base[0]:
                raise ValueError("empty or negative base window: %s" % base)
            
            if peak[1] <= peak[0]:
                raise ValueError("empty or negative peak window")
            
            if base[0] < f0Range[0]:
                # NOTE: 2018-08-03 13:53:46
                # this can happen when the discrimination window is determined
                # by the delay and the fitted delay is slightly smaller (i.e, 
                # "earlier") which given the d_base_window size will bring its start
                # before the actual start of the waveform (in reality the waveform
                # time starts at 0 but contains are NaNs up to f0Range[0])
                # 
                
                # NOTE: 2018-08-03 14:00:54
                # one may avoid this by forcing the use of the model's delay 
                # instead of the fitted delay, for the discrimination only 
                # because the discrimination is performed on the unfitted 
                # EPSCaT.
                # In contrast, one would keep using the fitted delay to determine
                # the amplitude window for the fitted curve. 
                #
                # However this would require to keep track of two sets of 
                # intervals, one for the EPSCaT and the other for the fitted EPSCaT
                # which would complicate the code further.
                #
                # NOTE: 2018-08-03 14:02:23
                # another way to avoid this is to give a very tight lower bound to
                # the delay parameter in the model such as to "force" the fitted 
                # EPSCaT to keep the inital delay value -- not entirely sure this
                # is correct
                warnings.warn("Detection baseline window (Base: %s) starts before baseline fluorescence window (F0: %s); it's value has been adjusted" % (base, f0Range), RuntimeWarning)
                base = (f0Range[0], base[1]) # base is a tuple, therefore immutable
                
                # Now, if the base window size has changed (i.e. shortened) the peak window size
                # should be shortened as well
                
                #base[0] = f0Range[0]
            
            if any([peak[0] < b for b in base]) or any([peak[1] <= b for b in base]):
                raise ValueError("peak (%s) overlaps or precedes base %s)" % (peak, base))
            
            if discr_2D:
                #               space boundaries         time boundaries from start of baseline to end of data
                df2d = ca_data[roiRange[0]:roiRange[1], f0Range[0]:]
                
                # NOTE: 2018-01-28 11:38:54
                # CAUTION in vigra x axis (rows axis) is the first dimension!
                # while in all other np.array derivates the column axis if the first dimension
                baseData = df2d[:, base[0]:base[1]]
                
                peakData = df2d[:, peak[0]:peak[1]]
                
            else:
                # NOTE: 2018-01-28 11:38:54
                # CAUTION in vigra x axis (rows axis) is the first dimension!
                # while in all other np.array derivates the column axis if the first dimension
                baseData = epscat[base[0]:base[1],0]
                
                peakData = epscat[peak[0]:peak[1],0]
                
            fnc = list(discr_func.items())[0]
            
            discr, peak_val, base_val, peak_base_val = epscatDiscriminator(baseData, peakData, fnc, discr_pred, discr_value, discr_pred_func)
            
            base_value.append(base_val)
            peak_value.append(peak_val)
            value.append(peak_base_val)
            
            if fitted_epscat is not None:
                # enforce success value based on R2 of the fit: thisis useful epsecially for few traces where
                # variability in the filttered data is still an issue
                # NOTE: 2018-09-17 09:51:45
                # see Tigaret et al, Biophys J 2013 Figure S3 for why
                # we choose a minimum R squared of 0.5
                rsq = fitted_epscat.annotations["FitResult"]["Rsq"]
                #print("rsq", rsq)
                #print("discr", discr)
                #print("k_epscat", k_epscat)
                if len(rsq) == 2:
                    # a single EPSCaT (fullfit rsq and individual EPSCaT rsq)
                    discr &= rsq[0] >= min_r2_discr
                    
                else:
                    # check individual EPSCaT component
                    discr &= rsq[k_epscat+1] >= min_r2_discr
                #for kr, r in enumerate(rsq):
                    #discr[k] &= r >= 0.5
                #discr &= all([r >= 0.5 for r in rsq])
                
            success.append(discr)
            
        FS = collections.OrderedDict()
        
    FS["success"]       = success
    FS["base_value"]    = base_value
    FS["peak_value"]    = peak_value
    FS["discr_value"]   = value
    FS["Discr_2D"]      = discr_2D
    
    if fitted_epscat is not None:
        result_annotations = fitted_epscat.annotations
        
    else:
        result_annotations = epscat.annotations
        
    #print("analyseEPSCaT result_annotations", result_annotations)
    
    result_annotations["FailSuccess"] = FS

    # NOTE: 2018-08-03 09:41:16 calculate waveform amplitudes:
    # amplitude is calculated on the signal interval between the start of
    # the baseline and the end of the peak, so that one can avoid spurious
    # transients after the EPSCaT itself, in the EPSCaT waveform
    
    # NOTE: 2018-08-03 09:41:22
    # the problem with the next code line is that for compound EPSCaTs
    # this will only calculate the amplitude for the first EPSCaT component
    #amplitudeWindows = [[d_base[0][0], d_peak[0][1]]]
    
    # NOTE: 2018-08-03 09:41:44
    # set up amplitude windows for each EPSCaT component
    #
    # NOTE: this depends on how many EPSCaT Triggers are there, or how many delays
    # have been determined/defined in the model, or on how many horizontal cursors
    # have been manually places, according to the value of
    # lsdata.analysisOptions["Discrimination"]["WindowChoice"], see NOTE: 2018-08-03 09:43:44
    #
    if len(d_base) and len(d_peak) and len(d_base) == len(d_peak):
        amplitudeWindows = [[base[0], peak[1]] for base, peak in zip(d_base, d_peak)]
        
    else:
        amplitudeWindows = None
    
    amplitudeMethod = lsdata.analysisOptions["AmplitudeMethod"]
    
    # NOTE: 2018-08-02 13:10:32
    # compute EPSCaT amplitude(s) HERE
    
    if isinstance(amplitudeWindows, (tuple, list)) and len(amplitudeWindows):
        if all([isinstance(v, pq.Quantity) for v in amplitudeWindows]):
            amplitude = [sgp.waveform_amplitude(epscat.time_slice(amplitudeWindows[0], 
                                                                 amplitudeWindows[1])[:,0], 
                                              amplitudeMethod)]# * ret.units
            
            if fitted_epscat is not None:
                fit_amplitude = [sgp.waveform_amplitude(fitted_epscat.time_slice(amplitudeWindows[0], 
                                                                 amplitudeWindows[1])[:,1], 
                                              amplitudeMethod)]
                
            else:
                fit_amplitude = [np.nan]
            
        elif all([isinstance(v, numbers.Integral) for v in amplitudeWindows]):
            amplitude = [sgp.waveform_amplitude(epscat[amplitudeWindows[0]:amplitudeWindows[1],0], 
                                              amplitudeMethod)]# * ret.units
            
            if fitted_epscat is not None:
                fit_amplitude = [sgp.waveform_amplitude(fitted_epscat[amplitudeWindows[0]:amplitudeWindows[1],1], 
                                              amplitudeMethod)]
                
            else:
                fit_amplitude = [np.nan]
            
        elif all([isinstance(v, (tuple, list)) and len(v)==2 for v in amplitudeWindows]):
            # NOTE: 2018-01-31 22:30:51
            # amplitude of several individual components for compund EPSCaTs
            amplitude = list()
            fit_amplitude = list()
            
            for v in amplitudeWindows:
                if all([isinstance(v_, pq.Quantity) for v_ in v]):
                    amplitude.append(sgp.waveform_amplitude(epscat.time_slice(v[0], 
                                                                             v[1])[:,0],
                                                           amplitudeMethod))# * ret.units)
                    
                    if fitted_epscat is not None:
                        # NOTE: 2018-08-03 10:15:52
                        # FIXME: currently, this calculates the amplitude of the
                        # fitted EPSCaT components on component intervals in the 
                        # overall fitted curve
                        # TODO: should calculate this on the fitted individual component,
                        # instead
                        fit_amplitude.append(sgp.waveform_amplitude(fitted_epscat.time_slice(v[0], 
                                                                             v[1])[:,1],
                                                           amplitudeMethod))
                        
                    else:
                        fit_amplitude.append(np.nan)
                    
                elif all([isinstance(v_, numbers.Integral) for v_ in v]):
                    amplitude.append(sgp.waveform_amplitude(epscat[v[0]:v[1],0],
                                                           amplitudeMethod))# * ret.units)
                    
                    if fitted_epscat is not None:
                        # NOTE: 2018-08-03 13:49:34
                        # see FIXME & TODO in NOTE: 2018-08-03 10:15:52
                        fit_amplitude.append(sgp.waveform_amplitude(fitted_epscat[v[0]:v[1],1],
                                                           amplitudeMethod))
                        
                    else:
                        fit_amplitude.append(np.nan)
                    
                else:
                    raise TypeError("Invalid amplitude window specifications %s" % str(amplitudeWindows))
                
        else:
            raise TypeError("Invalid amplitude window specifications %s" % str(amplitudeWindows))
        
    else:
        # when no amplitudeWindows have been determined
        amplitude = [sgp.waveform_amplitude(epscat[:,0], amplitudeMethod)]
        fit_amplitude = [np.nan]
        
    result_annotations["Amplitude"] = amplitude
    
    #print("analyseEPSCaT fit_amplitude:", fit_amplitude)
    
    if fitted_epscat is None:
        epscat.annotations.update(result_annotations)
        return epscat #, src_base, src_peak
    
    else:
        result_annotations["FitResult"]["CoefficientNames"] = get_nested_value(lsdata.analysisOptions, ["Fitting", "CoefficientNames"])
        result_annotations["FitResult"]["FitAmplitude"] = fit_amplitude
        
        
        fitted_epscat.annotations.update(result_annotations)
        
        return fitted_epscat #, src_base, src_peak
    
def analyseFrame(lsdata:ScanData, frame:int, unit=None, indicator_channel_ndx=None, reference_channel_ndx=None, detrend=False, gen_long_fits=False):
    """Analyses a specific frame in a ScanData object.
    See also the module-level function CaTanalysis.analyseFrame(...)
    Modifies ScanData in place !
    Uses analysisOptions stored in lsdata.
    
    lsdata: a ScanData object
    
    frame: int; index of the frame to be analysed
    
    unit: None, an AnalysisUnit, a vertical scan cursor used in an Analysis unit, or the name of such cursor
        
            If "unit" is None then all landmark-based analysis units will be analysed.
                If there are no landmark-based analysis units then the analysis unit
                based on the entire data set will be analysed.
                Previous analysys results will be replaced.
                
            If "unit" is a str:
                analyse a landmark-based analysis unit with the name given in "unit"
                if it exists, otherwise:
                analyse along a vertical scan cursor with the name given in "unit"
                if it exists, otherwise:
                analyse the analysis unit associated with the entire data set
                
                
            use the AnalysisUnit define on the whole data set to specifically work on it.
    
    indicator_channel_ndx, reference_channel_ndx, indices of the indicator and reference channels for EPSCaT calculation
    
    """
    if not isinstance(lsdata, ScanData):
        raise TypeError("First parameters was expected to be a datatypes.ScanData; got %s instead" % type(lsdata).__name__)
    
    if len(lsdata.scans) == 0:
        raise ValueError("no linescan data was found in %s" % lsdata.name)
    
    if lsdata.scanType != ScanData.ScanDataType.linescan:
        raise ValueError("%s was expected to be a ScanData.ScanDataType.linescan experiment; it has %s instead" % (lsdata.name, lsdata.type))
        
    if lsdata.analysisMode != ScanData.ScanDataAnalysisMode.frame:
        raise ValueError("%s was expected to have a ScanData.ScanDataAnalysisMode.frame analysis mode; it has %s instead" % (lsdata.name, lsdata.analysisMode))
        
    if len(lsdata.analysisOptions) == 0:
        raise ValueError("%s has no analysis options defined" % lsdata.name)
    
    #if not isinstance(unit, (AnalysisUnit, type(None))):
        # work on AnalysisUnits, or None in which case find analysis units in lsdata
        # NOTE: 2018-04-09 17:14:46
        # then clauses below bring various options to a common denominator: AnalysisUnit
        
    if len(lsdata.triggers) == 0:
        raise RuntimeError("%s has no trigger protocols" % lsdata.name)
    
    if isinstance(unit, pgui.Cursor) and unit.type == pgui.GraphicsObjectType.vertical_cursor:
        # NOTE: 2018-04-09 17:10:02
        # allow a single unit to be specified as a scan vertical cursor
        # this allows to specify an individual unit
        # when the whole data set associates an analysis unit, then THAT unit must be 
        # passed here
        
        if len(lsdata.analysisUnits) == 0 or unit not in [u.landmark for u in lsdata.analysisUnits]:
            raise ValueError("A cursors (%s) was specified, but it is not used in an AnalysisUnit" % unit.name)
        
        units = [u for u in lsdata.analysisUnits if u.landmark == unit]
        
        if len(units) > 1:
            raise RuntimeError("Specified cursor appears to be associated with %d units in %s" % (len(units), lsdata.name))
        
        protocol = units[0].protocol(frame)
        
    elif isinstance(unit, str):
        # NOTE: 2018-04-09 17:10:57
        # allow a single unit to be specified by its name (which should be the name of the cursor)
        # this allows to specify an individual unit
        # when the whole data set associates an analysis unit, then THAT unit must be 
        # passed here
        
        if len(lsdata.analysisUnits) == 0 or unit not in [u.name for u in lsdata.analysisUnits]:
            raise ValueError("Specified unit (%s) does not exist in %s" % (unit, lsdata.name))
        
        units = [u for u in lsdata.analysisUnits if u.name  == unit]
        
        if len(units) > 1:
            raise RuntimeError("%s appears to contain several units with the same name %s" % (lsdata.name, unit))
            
        protocol = units[0].protocol(frame)
        
    elif isinstance(unit, AnalysisUnit):
        if len(lsdata.analysisUnits) == 0 and unit != lsdata.analysisUnit():
            raise ValueError("Unit %s not found in %s" % (unit, lsdata.name))
        
        else:
            if unit != lsdata.analysisUnit() and unit not in lsdata.analysisUnits:
                raise ValueError("Unit %s not found in %s" % (unit, lsdata.name))
            
        units = [unit]
        
        protocol = unit.protocol(frame)
        
    elif unit is None:
        if len(lsdata.analysisUnits):
            units = sorted(list(lsdata.analysisUnits), key = lambda x:x.name)
            
        else:
            units = [lsdata.analysisUnit()]
            
        protocol = lsdata.triggerProtocol(frame)

    else:
        raise TypeError("Expecting a datatypes.AnalysisUnit object, or None; got %s instead" % type(unit).__name__)
    
    if indicator_channel_ndx is None:
        indicator_channel_ndx = lsdata.scansChannelNames.index(lsdata.analysisOptions["Channels"]["Indicator"])
        
    elif not isinstance(indicator_channel_ndx, int):
        raise TypeError("indicator_channel_ndx was expected to be an int or None; got %s instead" % type(indicator_channel_ndx).__name__)

    if indicator_channel_ndx < 0 or indicator_channel_ndx >= lsdata.scansChannels:
        raise ValueError("invalid indicator channel index: %d; must satisfy 0 <= index < %d" % (indicator_channel_ndx, len(lsdata.scanChannels)))
    
    if len(lsdata.analysisOptions["Channels"]["Reference"]):
        if reference_channel_ndx is None:
            reference_channel_ndx = lsdata.scansChannelNames.index(lsdata.analysisOptions["Channels"]["Reference"])
            
        elif not isinstance(reference_channel_ndx, int):
            raise TypeError("reference_channel_ndx was expected to be an int or None; got %s instead" % type(reference_channel_ndx).__name__)
        
        if reference_channel_ndx < 0 or reference_channel_ndx >= lsdata.scansChannels:
            raise ValueError("invalid reference channel index: %d; must satisfy 0 <= index < %d" % (reference_channel_ndx, len(lsdata.scanChannels)))
        
        if reference_channel_ndx == indicator_channel_ndx:
            raise ValueError("Indicator and reference channel indices cannot be identical (%d)" % reference_channel_ndx)
        
    else:
        reference_channel_ndx = None

    cal = AxesCalibration(lsdata.scans[0].axistags["t"])
    #print("analyseFrame time axis calibration:")
    #print(cal)
    
    if "Fit" in lsdata.analysisOptions["Fitting"]:
        doFit = lsdata.analysisOptions["Fitting"]["Fit"]
        
    else:
        doFit = True
        
    epscats = list()
    
    # NOTE: 2018-08-03 12:31:47
    # there is (should be) ONE protocol for this frame
    # (and this frame should associate ONE protocol only)
    
    
    # FIXME: assign result to the EPSCaT corresponding to the unit name
    # find it by the analosignal name attribute
    epscats[:] = [analyseEPSCaT(lsdata, frame, indicator_channel_ndx,
                                unit=u, 
                                reference_channel_ndx=reference_channel_ndx,
                                do_fit = doFit,
                                detrend=detrend)
                    for u in units]
    
    epscats[:] = [e for e in epscats if e is not None]
    
    #print("epscats", epscats)
    
    epscat_names = [epscat.name for epscat in epscats]
    
    if len(lsdata.scansBlock.segments[frame].analogsignals) == 0:
        lsdata.scansBlock.segments[frame].analogsignals[:] = epscats
        
    else:
        # check which signal names are obsolete, given current analysis units in lsdata ScanData
        unit_names = [u.name for u in units]
        
        signals_to_keep = list()
        
        for signal in lsdata.scansBlock.segments[frame].analogsignals:
            if signal.name in unit_names:
                signals_to_keep.append(signal)
                
        lsdata.scansBlock.segments[frame].analogsignals = signals_to_keep
                
        #if len(units) != len(epscats):
            #raise RuntimeError("Not all units have been associated with an EPSCaT")
        
        # replace the currently analysed data signals, 
        sig_names = [sig.name for sig in lsdata.scansBlock.segments[frame].analogsignals]
        
        signals = lsdata.scansBlock.segments[frame].analogsignals
        
        epscat_names = [epscat.name for epscat in epscats]
        
        if len(signals) != len(epscats):
            obsolete_signal_names = [name for name in sig_names if name not in epscat_names]
            
            obsolete_signal_indices = [sig_names.index(name) for name in obsolete_signal_names]
            
            for index in obsolete_signal_indices:
                del signals[index]
                
            # update sig_names
            sig_names = [sig.name for sig in signals]
            
        for epscat in epscats:
            if epscat.name in sig_names:
                sig_index = sig_names.index(epscat.name)
                signals[sig_index] = epscat
                
            else:
                signals.append(epscat)
        
        lsdata.scansBlock.segments[frame].analogsignals = sorted(signals, key=lambda x:x.name)
        
    if gen_long_fits:
        # replate the default fits resticted ot the fitted segment
        # with fits on the whole of the time domain of signal
        for signal in lsdata.scansBlock.segments[frame].analogsignals:
            coeffs = signal.annotations["FitResult"]["Coefficients"]
            x = signal.times
            fc = models.compound_exp_rise_multi_decay(x.magnitude, coeffs)
            signal[:,1] = fc[0][:, np.newaxis]
        
        
    # set up events
    lsdata.scansBlock.segments[frame].events.clear()
    
    presyn = protocol.presynaptic
    
    postsyn = protocol.postsynaptic
        
    photo = protocol.photostimulation
            
    #if protocol.presynaptic is not None and len(protocol.presynaptic):
    if presyn is not None and presyn.size > 0:
        evt = protocol.presynaptic - protocol.imagingDelay
        evt.name = protocol.presynaptic.name
        lsdata.scansBlock.segments[frame].events.append(evt)
        
    #if protocol.postsynaptic is not None and len(protocol.postsynaptic):
    if postsyn is not None and postsyn.size > 0:
        evt = protocol.postsynaptic - protocol.imagingDelay
        evt.name = protocol.postsynaptic.name
        lsdata.scansBlock.segments[frame].events.append(evt)
        
    #if protocol.photostimulation is not None and len(protocol.photostimulation):
    if photo is not None and photo.size > 0:
        evt = protocol.photostimulation - protocol.imagingDelay
        evt.name = protocol.photostimulation.name
        lsdata.scansBlock.segments[frame].events.append(evt)
        
    #lsdata.scansBlock.segments[frame].name = "Segment %d (%s)" % (frame, protocol.name)
    lsdata.scansBlock.segments[frame].name = "%s" % protocol.name
        
#@safeWrapper
def computeLSCaT(roiRange, f0Range, ca_data, ref_data=None, detrend=False, name=None, description=None, units=pq.dimensionless, **annotations):
    """
    Generates an EPSCaT trace by calculating df/a or df/f on a linescan time series.
    
    Positional parameters:
    ======================
    roiRange, f0Range are start:stop tuples (in pixel coordinates)
    
    ca_data : 2D vigra.VigraArray with line scan series (Ca2+-sensitive dye channel e.g. fluo5)
    
    Named parameters:
    =================
    
    ref_data: 2D vigra.VigraArray with line scan series (reference dye channel e.g. alexa fluor)
    
    detrend: boolean, default False; when True, tries to compensate for a sliding background
    using scipy.signal.detrend ("linear" detrend type)
    
    discr_base: list of tuples (start, stop) in samples, or empty (default)
    discr_peak: list of tuples tuple (start, stop) in samples, or empty (default)

    discr_value: float, or None (default)
    
    discr_pred: function or None (default); see epscatDiscriminator() dosctring
                for details
    
    discr_2D: boolean, default is True
    
    amplitudeWindows: list of tuples (start, stop) in signal time units, or in samples
                    
    
    amplitudeMethod: str ("direct" or "levels") see signalprocessing.waveform_amplitude()
                        docstring for details
    
    NOTE: both ca_data and ref_data (when given) must be 2D arrays with axistags
            "x" (axis 0) and "t" (axis 1)
    
    """
    if not isinstance(ca_data, vigra.VigraArray):
        raise TypeError("Ca2+ image data must be a VigraArray")
    
    if ca_data.ndim != 2:
        raise ValueError("Ca2+ data must be a 2D VigraArray")
    
    if "x" not in ca_data.axistags:
        raise TypeError("Data does not have a defined X axis")
    
    if "t" not in ca_data.axistags:
        raise TypeError("Data does not have a defined t axis")
    
    w = ca_data.shape[0]
    h = ca_data.shape[1]
    
    if ref_data is not None:
        if not isinstance(ref_data, vigra.VigraArray):
            raise TypeError("Reference image data must be a vigra.VigraArray")
        
        if ca_data.shape != ref_data.shape:
            raise ValueError("Ca2+ and reference channels have different shapes")
        
        if ref_data.axistags != ca_data.axistags:
            raise TypeError("Mismatch between indicator and reference axistags")
        
    #print(f0Range)
    
    if f0Range[1] <= f0Range[0]:
        raise ValueError("baseline fluorescence window is not ordered: %s" % str(f0Range))
    
    if f0Range[1] < 0:
        raise ValueError("baseline fluorescence range is empty: %s" % str(f0Range))
        
    if f0Range[0] < 0:
        f0Range[0] = 0
        
    if f0Range[1] > h:
        f0Range[1] = h
        
    if f0Range[1] == h:
        warnings.warn("baseline fluorescence range extends over the entire signal: %s" % str(f0Range), RuntimeWarning)
        
    if f0Range[0] == f0Range[1]:
        warnings.warn("baseline fluorescence range is empty: %s" % str(f0Range), RuntimeWarning)
        
    #if any([f < 0 for f in f0Range]):
        #raise ValueError("baseline fluorescence window (%s) cannot have negative indices" % f0Range)
    
    if roiRange[1] <= roiRange[0]:
        raise ValueError("ROI window range is not ordered: %s" % str(roiRange))
    
    if roiRange[1] < 0:
        raise ValueError("ROI window range is empty: %s" % str(roiRange))
        
    
    if roiRange[0] < 0:
        raise ValueError("empty ROI window: %s" % str(roiRange))
    
    if roiRange[0] < 0:
        roiRange[0] = 0
        
    if roiRange[1] > w:
        roiRange[1] = w
        
    if roiRange[0] == roiRange[1]:
        warnings.warn("ROI window range is empty: %s" % str(roiRange), RuntimeWarning)
        
    tcal = AxesCalibration(ca_data.axistags["t"])
    tunits = tcal.getUnits(ca_data.axistags["t"])
    torigin = tcal.getOrigin(ca_data.axistags["t"])
    tresolution = tcal.getResolution(ca_data.axistags["t"])
    
    # NOTE: 2018-01-28 08:54:41
    # ATTENTION: VigraArrays are indexed with x first !
    # roiRange[0]:roiRange[1] takes the data _COLUMNS_ within the cursor xwindow
    # f0Range[0]:f0Range[1] takes the data _ROWS_ from f0 start to f0 end (or last row)
    
        
    
    
    # Fluo 5F               cursor xwindow           baseline fluorescence
    # NOTE: 2019-03-18 09:24:11 this is usually so short it doesn't need detrend
    # and because ocurs at the beginning of the linescan series, it it less likely
    # to be affected by intensity drift which usually kick in/is more pronounced 
    # later in the series
    #                    cursor xwindow           baseline fluorescence range
    #base_fluo5 = ca_data[roiRange[0]:roiRange[1], f0Range[0]:f0Range[1]]
    
    #if detrend:
        #base_fluo5 = signal.detrend(base_fluo5, axis=0)
    
    # FIXME for the sake of generality do implement detreding here also!
    f0 = np.nanmean(ca_data[roiRange[0]:roiRange[1], f0Range[0]:f0Range[1]])

    # Fluo 5F               cursor xwindow           all fluorescence from start of baseline to end of data
    f  = np.nanmean(ca_data[roiRange[0]:roiRange[1], f0Range[0]:], axis=0)
    
    # NOTE: 2019-03-18 09:25:45
    # THIS needs to be detrended all along, though...
    
    #if detrend:
        #f = signal.detrend(f, axis=0)
    
    df = f-f0
    
    ret = np.full((ca_data.shape[1], 1), np.NaN)
    
    if ref_data is not None:
        # NOTE: 2019-03-18 09:28:44
        # this IS a vector!
        # Alexa Fluor         cursor xwindow          all fluorescence from start of baseline to end of data
        a_mean = np.nanmean(ref_data[roiRange[0]:roiRange[1], f0Range[0]:], axis=0)
        
        #if detrend:
            #a_mean = signal.detrend(a_mean)
        
    else:
        # NOTE: 2019-03-18 09:28:55
        # this IS a scalar
        a_mean = f0
        
    epscat_signal = df/a_mean
    
    # NOTE: 2019-03-18 09:32:56
    # detrend HERE, otherwise you get numerical instability on the df/a_mean operation
    if detrend:
        epscat_signal = signal.detrend(epscat_signal)
        # re-correct for f0 baseline
        #epscat_base = np.nanmean(epscat_signal[f0Range[0]:f0Range[1]])
        #print(epscat_base)
        #epscat_signal -= epscat_base
        
    ret[f0Range[0]:, 0] =  epscat_signal
    
        
    ret = neo.AnalogSignal(ret, units=units, sampling_period=tresolution, \
                                name=name, description=description, **annotations)
    
    #ret.annotations["Date_Time"] = "%s" % datetime.datetime.now()
    ret.annotations["Date_Time"] = datetime.datetime.now()
    ret.annotations["EPSCaT"] = True
    
    return ret

#@safeWrapper
def fitEPSCaT(data, p0, bounds, fitWindow = None, integration=None):
    """Fit EPSCaT model defined by p0 parameters through data.
    
    Parameters:
    ============
    data:   neo.AnalogSignal = data to be fitted, containing at least one channel
            column-wise, as follows:
            
            column 0 contains the signal to be fitted
            column 1 contains a previous fitted curve, if it exists
            columns 2 ... contain fitted curves for individual EPSCaT component
                (in case of a compound EPSCaT)
    
    p0:     sequence of floats or sequence of sequences of floats = the initial parameters
    
            for a single EPSCaT, p0 is a sequence of N x 2 + 3 values
                where N is the number of decays 
                (see models.compound_exp_rise_multi_decay()
                and models.exp_rise_multi_decay())
                
            for a compound EPSCaT, p0 is a sequence of sequences, where the nested
            sequences contain initial parameters for individual EPSCaT components, 
            as above
         
    bounds: sequence of two elements with the lower and upper bounds for p0 values
        
        Both lower and upper can be:
        
        a real scalar (will be broadcasted for each value in p0)
        
        a sequence of real scalars, or a sequence of sequences real scalars, that
            mirror the structure of p0; 
            ATTENTION In this case there has to be one lower bound and one upper
            bound value for each value in p0.
            
    Named parameters:
    ================
   
    fitWindow: None( default) or a two-element sequence of real scalar numbers or
            python Quantities (also scalars).
            
            Specifies the time interval of the real signal that will be fitted.
            
            See NOTE: 2018-06-11 09:43:37 below for explanations
    
    integration: None (default), or: real scalar, scalar python Quantity or a 
            two-element sequence of real scalars or python Quantity objects.
        
            When a real scalar or python Quantity object, it specifies the END of the
            integration interval; see NOTE: 2018-06-11 09:43:53 below for further explanations
            
    amplitudeWindows: None (default) or a two-element sequence of floats or time (python Quantities)
    
    amplitudeMethod: str (default: "direct") 
        See signalprocessing.waveform_amplitude() for details.
    
        
    Returns:
    =======
    Analogsignal containing multi-channel data (one channel per column):
        column 0 contains the signal that has been fitted
        column 1 contains the fitted curve (possibly of a compound EPSCaT)
        for compound EPSCaTs, columns 2 - n-1 contain fitted curves for the 
            individual EPSCaT components

    TODO: export data for individual EPSCaTs in a compound EPSCaT
    
    NOTE: 2018-06-11 09:43:37 Fitting:
    ==================================
    Signal is fitted with a multi-component EPSCaT model (see models.compound_exp_rise_multi_decay())
    
    The fitting can be applied to the entire signal, or to a signal region defined
    by the half-open interval specified in the "fitWindow" parameter (this includes
    the first time point, but excludes the last time point).
    
    For compound EPSCaTs, individual components will also be fitted separately.
    
    NOTE: 2018-06-11 09:43:53 Integration:
    ======================================
    
    The time integral of the EPSCaT is calculated by the Simpson's method using
    the fitted parameters, on the time interval specified in "integration" parameter.
    
    (1) When "integration" is a scalar (real, or python Quantity), it is taken to 
        define the DURATION of the integration interval, starting at the time point
        given by the EPSCaT's "delay" parameter (x0).
    
        For compound EPSCaTs, individual EPSCaT components will also be integrated using
        their own x0 values as the beginning of the interval, for the duration specified 
        by the "integration" parameter.


    (2) When "integration" is a sequence of two values (either two real scalars, or
        two scalar python Quantities) then the integration will be computed on the 
        specified interval, for _ALL_ EPSCaT components (simple EPSCaT have ony one 
        component). WARNING: EPSCaTs falling out of this interval will appear to have
        very small time integrals.
        
    ATTENTION: Beware of integrating a curve containing np.nan values !
        
        
    NOTE: When given as python Quantity or a sequence of python quantities, units
    are assumed to be "s" (seconds). No checks are beign performed.
    """
    # TODO perform unit (dimensionality) check on the quantity, commensurate with
    # the signal's domain units (dimensionality)
    
    # FIXME: 2018-08-03 12:11:03
    # the components of a compund EPSCaT are always fitted; 
    # should this be optional?
    # if so, this would force the use of a single component exponential transient
    # when fit_components is False, which may result in a mistfit
    # TODO: get rid of the fit_components parameter and let the decision be driven
    # by the number of components in the model i.e., we fit as many components are there
    # defined in the model
    
    
    def _integral_func_(x, params):
        #print(params)
        y = models.compound_exp_rise_multi_decay(x, params)
        return y
    
    def _integrate_window_(x, window, name, column = 1):
        # NOTE: 2018-02-03 21:46:38
        # column specifies which fitted curve we're integrating on
        # becuase for compound EPSCaTs, each individual EPSCaT fit is also 
        # present in the signal, on columns 2, ...
        #
        # for single EPSCaTs the default is OK because columns 0 and 1 are ALWAYS
        # the data signal and its fit
        int_dict = collections.OrderedDict()
            
        int_dict["%s_Interval_begin" % name] = window[0]
        int_dict["%s_Interval_end" % name] = window[1]
        
        slice_begin = window[0]*x.times.units 
        slice_end   = window[1]*x.times.units
        
        if slice_begin < x.t_start:
            slice_begin = x.t_start
            
        if slice_end > x.t_stop:
            slice_end = x.t_stop
        
        simps_y = x.time_slice(slice_begin, slice_end)
        simps_dx = simps_y.sampling_period.magnitude
        
        if np.all(np.isnan(simps_y[:, column])):
            simps_integral = np.nan
            warnings.warn("Signal to integrate is all nans!", RuntimeWarning)
            
        else:
            valid = ~np.isnan(simps_y[:,column])
            
            
            simps_integral = integrate.simps(simps_y[:,column].magnitude[valid], dx=simps_dx, axis=0)
            
            #print(simps_integral)
            
        int_dict["%s_Simpson" % name] = simps_integral
        
        return int_dict
        
    if not isinstance(data, (neo.AnalogSignal, DataSignal)):
        raise TypeError("Expecting a neo.AnalogSignal or datatypes.DataSignal; got %s instead" % type(data).__name__)
    
    
    # CAUTION this may have been fitted before!
    # in which case its fitted curve is in the second column
    if data.ndim == 1 or data.shape[1] == 1:
        y = data
        
    else:
        y = data[:,0]
        
    #print("y: ", type(y))
    #print("y t_start: ", y.t_start)
    #print("y t_stop: ", y.t_stop)
    #print("integration: ", integration)
    #print("fitWindow: ", fitWindow)
    
    if fitWindow is not None:
        if not isinstance(fitWindow, (tuple, list)):
            raise TypeError("fitWindow expected to be a sequence or None; got %s instead" % type(fitWindow).__name__)
        
        if len(fitWindow) != 2:
            raise TypeError("fitWindow expected to have two elements; got %d instead" % len(fitWindow))
        
        if all([isinstance(t, numbers.Real) for t in fitWindow]):
            [fit_start, fit_end] = fitWindow[:] * pq.s
            
        elif all([isinstance(t, pq.Quantity) and t.size == 1 for t in fitWindow]):
            [fit_start, fit_end] = fitWindow[:]
            
        else:
            raise TypeError("fitWindow sequence must contain real scalars or scalar python Quantities")

        y_data = y.time_slice(fit_start, fit_end).copy() # NOTE: 2020-09-06 12:53:52 fit_end NOT included
        fit_ndx = [y.time_index(t) for t in [fit_start, fit_end]]
        fit_ndx[1] -= 1
        #print("fit_ndx", fit_ndx)
        #if fit_ndx[1] < len(y_data):
            ## see NOTE 2020-09-06 12:47:55
            #fit_ndx[1] += 1 # because for indexing this must be one past the end
            
    else:
        y_data = y.copy()
        fit_ndx = None
        
    originalAnnotations = data.annotations
    
    fittedLSCaT, fittedLSCatComponents, fitResult = crvf.fit_compound_exp_rise_multi_decay(y_data, p0, bounds = bounds)
    
    # write the fitted curve(s) into an array the size of the original signal
    nColumns = len(fittedLSCatComponents)
    
    fittedSignal = np.full((y.shape[0], nColumns), np.nan)
    
    #print("fittedSignal shape", fittedSignal.shape)
    
    if fit_ndx is not None:
        #print("fit_ndx", fit_ndx)
        #print("fittedLSCaT shape", fittedLSCaT.shape)
        # NOTE 2020-09-06 12:47:55 CAUTION fit_ndx[1] must be one past the end
        fittedSignal[fit_ndx[0]:fit_ndx[1],0] = fittedLSCaT[:]
        
    else:
        fittesSignal[:,0] = fittedLSCaT[:]
    
    for k, fittedComponent in enumerate(fittedLSCatComponents[1:]):# for a single component, the first component is just a copy of the fitted signal!
        fittedSignal[fit_ndx[0]:fit_ndx[1],k+1] = fittedComponent[:]
        
    # concatenate this with the original signal
    signal = np.concatenate([y.magnitude, fittedSignal], axis=1)
    
    # construct the new signal
    result = data.__class__(signal, units = y_data.units, sampling_period = y_data.sampling_period, name=y_data.name)
        
    # NOTE: 2018-08-02 13:09:19
    # amplitude calculation moved to analyseEPSCaT()
    
    fitres = collections.OrderedDict(fitResult)
    
    #fitres["FitAmplitude"] = amplitude
        
    fitres["Integration"] = list()
    
    # NOTE: 2018-02-03 21:07:23
    # set up integration intervals here
    
    #print(integration, " as given")
    
    if isinstance(integration, pq.Quantity):
        integration = integration.magnitude.flatten()
        
        if integration.size == 1:
            integration = float(integration)
            
    elif isinstance(integration, (tuple, list)):
        if len(integration) != 2:
            raise ValueError("When given as a sequence, 'integration' parameter must have exactly two elements; currently it has %s" % len(integration))
        
        if all([isinstance(i, pq.Quantity) and i.size == 1 for i in integration]):
            integration = [float(i.magnitude.flatten()) for i in integration]
            
        elif not all([isinstance(i, numbers.Real) for i in integration]):
            raise TypeError("When given as a sequence, 'integration' parameter must contain either two python qualtities, or two real scalars")
    
    if isinstance(integration, numbers.Real):
        # case when only the duration of the integration window is specified
        # the start of integration is the delay (onset) of the EPSCaT
        #
        # for compound EPSCaTs, we use this window with the first delay parameter
        # then for individual EPSCaTs in the compound we use its own delay 
        # as start of integration window, and the delay of the next individual EPSCaT
        # of the end of trace as the stop of the integration window
        
        if len(fitResult["Coefficients"]) == 1:
            # single EPSCaT is integrated from the fitted start (x0)
            int_0 = fitResult["Coefficients"][0][-1] # the "onset" or x0 parmeter
            integration = (int_0, int_0 + integration)
            
        else:
            # a compound EPSCaT:
            compound_start = fitResult["Coefficients"][0][-1]
            
            # the integration window for the ENTIRE compound EPSCaT
            compound_window = (compound_start, compound_start + integration)
            
            integration = [compound_window]
            
            # integration windows for the individual EPSCaT components
            for k, parameters in enumerate(fitResult["Coefficients"]):
                # integrate EPSCaT component from its own fitted start (x0)
                int_start = parameters[-1] # the onset or x0
                if k < len(fitResult["Coefficients"])-1:
                    int_end = fitResult["Coefficients"][k+1][-1] # the onset of next EPSCaT
                    
                else:
                    int_end = result.t_stop.flatten().magnitude
                    
                integration.append((int_start, int_end))
                
    else:
        if len(fitResult["Coefficients"]) == 1:
            # single EPSCaT
            integration = (integration)
            
        else:
            integration = [integration for k in range(len(fitResult["Coefficients"])+1)]
            
        
    # NOTE: 2018-02-03 21:39:30: perform the integration
    # NOTE: 2018-02-03 21:39:41
    # use Simpson's rule on the fitted curve !!!
    
    #print(integration, "as interpreted")
    
    # by now, integration should be a sequence of scalar pair sequences (tuples)
    # 
    if isinstance(integration, (tuple, list)):
        if all([isinstance(interval, (tuple, list)) and \
                  len(interval) == 2 and \
                      all([isinstance(i, numbers.Real) for i in interval]) for interval in integration]):
            # NOTE: 2018-02-03 21:12:12
            # integration is a sequence of n+1 integration intervals
            # where n is the number of EPSCaT 
            # components; each interval is a 2-element sequence of scalars (begin, end)
            # as real scalars (but as if in signal's domain units)
            
            if len(integration) != len(fitResult["Coefficients"]+1):
                raise ValueError("Mismatch between the number of integration intervals and that of EPSCaT components")
            
            int_dict = _integrate_window_(result, integration[0], "CompoundEPSCaT", column=1)
            fitres["Integration"].append(int_dict)
            
            for k in range(len(fitResult["Coefficients"])):
                int_dict = _integrate_window_(result, integration[k+1], "EPSCaT_%d" % k, column = k+2)
                fitres["Integration"].append(int_dict)
            
        elif len(integration) == 2:
            # NOTE: 2018-06-18 12:38:28
            # common integration interval for the compound EPSCaT and _ALL_
            # of its individual components
            if all([isinstance(x, pq.Quantity) for x in integration]):
                if not all([x.size == 1 for x in integration]):
                    raise TypeError("When integration is a tuple, its elements must be scalar python Quantity objects or real scalars")
                
                integration = [float(x) for x in integration]
        
            if all([isinstance(i, numbers.Real) for i in integration]): # check they are real scalars (but as if in signal's domain units)
                # use Simpson's rule; something is not quite right when using Quadrature
                # and the model function + coefficients
                if len(fitResult["Coefficients"]) > 1:
                    name = "CompoundEPSCaT"
                
                else:
                    name = "EPSCaT"
                    
                int_dict = _integrate_window_(result, integration, name, column=1)
                
                fitres["Integration"].append(int_dict)
                
                # NOTE: each sublist in parameters is:
                # a   = scale
                # d   = tau decay
                # o   = offset
                # r   = tau rise
                # x0  = delay (onset)
                
                if len(fitResult["Coefficients"]) > 1: # this is a compound EPSCaT
                    # integrate individual EPSCaT components
                    # ATTENTION this branch here takes a common integration window
                    # this is almost surely NOT what is wanted for, e.g. a theta train of EPSCaTs
                    
                    # NOTE: 2018-02-03 21:41:21
                    # use Simpson's rule, not the Quadrature anymore (see above)
                    
                    for k in range(len(fitResult["Coefficients"])):
                        int_dict = _integrate_window_(result, integration, "EPSCaT_%d" % k, column = k+2)
                        
                        fitres["Integration".append(int_dict)]
                        
            else:
                raise TypeError(("Integration interval expected to be a 2-sequence of scalars (start-stop) or a sequence of such pairs, for %d+1 EPSCaT components" % len(fitResult["Coefficients"])))
                
                    
        else:
            raise TypeError(("Integration interval expected to be a 2-sequence of scalars (start-stop) or a sequence of such pairs, for %d+1 EPSCaT components" % len(fitResult["Coefficients"])))
                    
    originalAnnotations["FitResult"] = fitres
    #originalAnnotations["Date_Time"] = "%s" % datetime.datetime.now()
    originalAnnotations["Date_Time"] = datetime.datetime.now()
    
    result.annotations.update(originalAnnotations)
    
    return result

def collateReports(data):
    """
    Concatenates several pandas DataFrame objects into one
    
    Wraps ps.concat for dataframes in *args. dataframes are concatenated along
    axis 0, a new axis 0 index is generated
    
    ATTENTION: Prerequisites:
    
    1) All column indices must be identical across the DataFrame objects in *args
    2) Columns must have compatible data types (e.g. categorical, etc)
    
    WARNING: Row indices are ignored (in fact, rows are re-indexed)
    
    """
    
    if not isinstance(data, (tuple, list)):
        raise TypeError("Expecting a sequence of objects")
    
    if len(data) < 1:
        #addSource(data)
        return 
    
    if len(data) < 2:
        if "Genotype" not in data[0].columns:
            addGenotype(data[0], "NA")
            
        if "Source" not in data[0].columns:
            addSource(data[0])
            
        if "Sex" not in data[0].columns:
            addSex(data[0], "NA")
            
        if "Age" not in data[0].columns:
            addAge(data[0], "NA")
        
        return data[0]
    
    try:
        for d in data:
            if "Genotype" not in d.columns:
                addGenotype(d, "NA")
                
            if "Source" not in d.columns:
                addSource(d)
            
            if "Sex" not in d.columns:
                addSex(d, "NA")
                
            if "Age" not in d.columns:
                addAge(d, "NA")
        
        return pd.concat(data, ignore_index=True, sort=False) # NOTE: must generate a new index !!!
    
    except Exception as e:
        traceback.print_exc()
        
def reportUnitAnalysis(scandata, analysis_unit=None, protocols=None, frame_index = None, filename=None, return_type="dataframe"):
    """Returns data containins LSCaT analysis result for the specified analysis unit(s).
    
    Parameters:
    ===========
    scandata: a ScanData object
    
    Named parameters:
    ================
    
    analysis_unit: an AnalysisUnit object, a str, or None
    
        When an AnalysisUnit, it can be landmark-based or data-based, and must 
        be found in the ScanData object
        
        When a str, this is the name of a landmark used to define a landmark-based
        AnalysisUnit
        
        When None, this takes the entire ScanData taken as an AnalysisUnit.
        
    protocols: either a str, a TriggerProtocol, a sequence of str, a sequence of 
        TriggerProtocol objects, an empty sequence, or None.
        
        When None or an empty sequence, ALL protocols associated with the landmark will be
        reported.
        
        Otherwise, it must resolve to valid TriggerProtocol object associated with the 
        analysis unit.
        
    frame_index: None, an int, a sequence of int, or an empty sequence
        Specifies which frame(s) to report results from.
        
        When None or an empty sequence, frame_index becomes the list of frames that
        simultaneously satisfy the following conditions:
        1) is associated with the specified analysis unit
        2) is associated with any of the specified protocol(s)
        3) is valid given the scandata
        
        When frame is an int or a sequence of ints, they must satisfy the above 
        conditions, with the caveat that a frame cannot be associated with more
        than one protocol.
        
        This means that when the 'protocols' parameter is resolved to a list of protocols,
        frame_index given as an int will fail to satisfy the last condition.
        
    filename: a str or None; when a str, the result will also be output to a csv 
        file named as <filename>.csv
        
        NOTE: the ".csv" extension will be added unless it is already present
        in "filename" parameter
    
    return_type: a string keyword, one of "dataframe", "list", or "html"
        
        When "dataframe" (default) the result is a pandas.DataFrame
        
        When "list" the result is a list of dict: a python list where each element
            is a dictionary mapping keys (EPSCaT analysis parameters) to values;
            this can be converted manually to a pandas.DataFrame
            
            Each analysis unit generated ONE such dictionary.
            
        When "html", the result is a string containing html-formatted text
        
        
    ATTENTION: When there is no signal in scandata.scansBlock that corresponds 
        to the specified analysis unit given the protocol(s) and frame(s), the 
        function outputs empty data.
    
    Returns:
    ========
    
    result = a pandas.DataFrame, a list of dict, or a html-formatted text, depending
        on the value of the "return_type" parameter
    
    Changelog:
    ==========
    NOTE: 2018-11-25 02:05:50
    returns a single variable: a pandas.DataFrame (default) a list of dict or a html-formatted text string
    
    
    """
    import io, csv
    
    if not isinstance(return_type, str):
        raise TypeError("return_type expected to be a string; got %s instead" % type(return_type).__name__)
    
    if return_type.lower().strip() not in ("dataframe", "list", "html"):
        raise ValueError("return_type expected to be one of 'dataframe', 'list', 'html'; got %s instead" % return_type)
    
    
    
    # placeholders for the returned variables in case we cannot run, but give up gracefully
    # (i.e. do not crash out raising exception)
    result = list()
    
    # parse the call parameters
    if not isinstance(scandata, ScanData):
        raise TypeError("first parameter should be a datatypes.ScanData object; got %s instead" % type(scandata).__name__)
    
    if analysis_unit is None: # when analysis unit is None, take the whole data as an analysis unit
        analysis_units = [scandata.analysisUnit]
        
    elif isinstance(analysis_unit, str): # analysis unit specified by its name
        if scandata.hasAnalysisUnit(analysis_unit) or analysis_unit is scandata.analysisUnit():
            analysis_units = [scandata.getAnalysisUnit(analysis_unit)]
            
        else:
            raise ValueError("analysis unit %s not found in scandata %s" % (analysis_unit, scandata.name))
    
    elif isinstance(analysis_unit, AnalysisUnit): # analysis unit specified as an AnalysisUnit object
        if not scandata.hasAnalysisUnit(analysis_unit) and analysis_unit is not scandata.analysisUnit():
            return
            #raise ValueError("analysis unit %s not found in scandata %s" % (analysis_unit.name, scandata.name))
        
        analysis_units = [analysis_unit]
        
    elif isinstance(analysis_unit, (tuple, list)): # we're given  list  of names and/or AnalysisUnit objects
        analysis_units = list()
        
        for a in analysis_unit:
            if isinstance(a, str):
                if scandata.hasAnalysisUnit(a) or analysis_unit is scandata.analysisUnit():
                    analysis_units.append(scandata.analysisUnit(a))
                    
                else:
                    raise ValueError("analysis unit %s not found in scandata %s" % (analysis_unit, scandata.name))
                    
            elif isinstance(a, AnalysisUnit):
                if scandata.hasAnalysisUnit(a) or analysis_unit is scandata.analysisUnit():
                    analysis_units.append(a)
                    
                else:
                    raise ValueError("analysis unit %s not found in scandata %s" % (analysis_unit, scandata.name))
                
            else:
                raise TypeError("'analysis_unit' sequence must contain onle str, and/or AnalysisUnit objects, or sequence of either str or AnalysisUnit objects; got %s instead" % type(a).__name__)
            
    else:
        raise TypeError("'analysis_unit' should be a str, an AnalysisUnit object, or sequence of either str or AnalysisUnit objects, or None; got %s instead" % type(analysis_unit).__name__)
    
    # iterate through the specified analysis unit and collect analysis data
    for analysis_unit in analysis_units:
        if not analysis_unit:
            continue
        # NOTE: 2018-10-14 11:05:29
        # generate a dict for each frame, for each analysis unit -- see NOTE: 2018-10-14 11:14:19
        # that we then collect into a list (result)
        # from this list we then generate a string varible (the "text_output")
        # and we also create a pandas.DataFrame if as_dictlist is False
        
        # check the protocols used (they indicate the frames to be used),
        # that means check they're found in the  scandata _AND_ in the analysis unit
        # HOWEVER: one can specify a list of protocols that are not present in ALL
        # units -- this is allowable !
        if protocols is None or (isinstance(protocols, (tuple, list)) and len(protocols) == 0): # no protocols specified in the call list
            protocols = analysis_unit.protocols
            # the analysis_unit.protocols should also be defined in the scandata,
            # but check this anyway:
            for p in protocols:
                if p not in scandata.triggers:
                    raise ValueError("protocol %s associated with analysis unit %s is not found in scan data %s" % \
                        (p.name, analysis_unit.name, scandata.name))
            
        elif isinstance(protocols, (tuple, list)): # a list of names or TriggerProtocol objects -- check they belong to the data
            for p in protocols:
                if isinstance(p, str): # protocol specified by its name
                    if p not in [p_.name for p_ in scandata.triggers]: # check it is found in the scandata
                        raise ValueError("protocol %s not found in scandata %s" % \
                            (p, scandata.name))
                    
                    if p not in [p_.name for p_ in analysis_unit.protocols]: # check it is found in the analysis unit
                        #raise ValueError("protocols %s is not associated with the analysis unit %s in scandata %s" %\
                            #(p, analysis_unit.name, scandata.name))
                        continue # why??? -- because one may ask for a protocol that is not necessarily present in all the specified units
                    
                elif isinstance(p, TriggerProtocol): # protocol specified as is (TriggerProtocol object)
                    if p not in scandata.triggers:
                        raise ValueError("protocol %s not found in scandata %s" % \
                            (p.name, scandata.name))
                    
                    if p not in analysis_unit.protocols:
                        #raise ValueError("protocol %s not found in analysis unit %s" % \
                            #(p.name, analysis_unit.name))
                        continue # why??? -- because one may ask for a protocol that is not necessarily present in all the specified units
                    
                else:
                    raise TypeError("'protocols' sequence must contain only str and TriggerProtocol objects; got %s instead" % type(p).__name__)
                        
        elif isinstance(protocols, str): #  a single protocol specified by name
            if protocols not in [p.name for p in scandata.triggers]:
                raise ValueError("protocol %s is not found in scandata %s" % \
                    (protocols, scandata.name))
            
            if protocols not in [p.name for p in analysis_unit.protocols]:
                #raise ValueError("protocol %s is not associated with the analysis unit %s in scandata %s" % \
                    #(protocols, analysis_unit.name, scandata.name))
                continue # why??? -- because one may ask for a protocol that is not necessarily present in all the specified units
            
            protocols = [p for p in analysis_unit.protocols if p.name  == protocols]
            
        elif isinstance(protocols, TriggerProtocol): #  a single TriggerProtocol object
            if protocols not in scandata.triggers:
                raise ValueError("protocol %s not found in scandata %s" % \
                    (protocols.name, scandata.name))
            
            if protocols not in analysis_unit.protocols:
                #raise ValueError("protocol %s is not associated with the analysis unit %s in scandata %s" %\
                    #(protocols.name, analysis_unit.name, scandata.name))
                continue # why??? -- because one may ask for a protocol that is not necessarily present in all the specified units

            protocols = [protocols]
            
        # does the analysis unit have a calculated EPSCaT in scansBlock?
        if len(scandata.scansBlock.segments) > 0:
            if frame_index is None or (isinstance(frame_index, (tuple, list)) and len(frame_index) == 0):
                frame_index = list()
                
                for protocol in protocols:
                    frame_index += [f for f in protocol.segmentIndices() if f in analysis_unit.frames]
                    
                if len(frame_index) == 0:
                    raise RuntimeError("there appears to be no frames in common with the analysis unit %s and specified protocols %s for scan data %s" %\
                        (analysis_unit.name, str([p.name for p in protocols]), scandata.name))
                
            else:
                if isinstance(frame_index, int):
                    frame_index = [frame_index]
                    
                elif isinstance(frame_index, (tuple, list)) and all([isinstance(f, int) for f in frame_index]):
                    pass
                
                else:
                    raise TypeError("frame_index parameter expected to be None, an int, or a sequence of int; got %s instead" % type(frame_index).__name__)
                    
                for f in frame_index:
                    if len(analysis_unit.frames) > 0 and f not in analysis_unit.frames:
                        continue
                    
                    p = [p_ for p_ in protocols if f in p_.segmentIndices()]
                    
                    if len(protocols) > 0 and len(p) == 0:
                        warnings.warn("frame %d is not associated with any of the specified protocols (%s) in analysis unit %s and scan data %s" %\
                            (f, str([p.name for p in protocols]), analysis_unit.name, scandata.name), category=RuntimeWarning)
                        
                        return text_output, result
                    
                    if len(p) > 1:
                        raise RuntimeError("frame %d appears to be associated with more than one protocol in %s for analysis unit %s and scan data %s" %\
                            (f, str([p.name for p in protocols]), analysis_unit.name, scandata.name))
                    
            for protocol in protocols:
                #print("protocol: ", protocol)
                for frame in protocol.segmentIndices():
                    if frame not in frame_index:# only select frames by frame_index
                        continue
                    
                    if len(analysis_unit.frames) > 0 and frame not in analysis_unit.frames:
                        continue
                    
                    if frame not in range(len(scandata.scansBlock.segments)):
                        continue
                    
                    if len(scandata.scansBlock.segments[frame].analogsignals) == 0:
                        continue
                    
                    if len(scandata.scansBlock.segments[frame].analogsignals) == 1:
                        sig_index = 0
                        
                    else:
                        sig_index = ephys.get_index_of_named_signal(scandata.scansBlock.segments[frame], analysis_unit.name, silent=True)
                        
                    #print("sig_index", sig_index)
                    #print("unit name", analysis_unit.name)
                        
                    if sig_index is None:
                        continue
                    
                    # NOTE: 2018-10-14 11:14:19
                    # a dictionary holding result for the given frame ;
                    # we make it a pandas.DataFrame and then we concatenate the data frames
                    # at the end
                    sig_result = collections.OrderedDict()
                    
                    genotype = strutils.str2symbol(analysis_unit.genotype)
                    #genotype = strutils.str2R(analysis_unit.genotype)
                    
                    if "na" in genotype.lower():
                        genotype = strutils.str2symbol(scandata.genotype)
                        #genotype = strutils.str2R(scandata.genotype)
                        
                    sex = strutils.str2symbol(analysis_unit.sex)
                    #sex = strutils.str2R(analysis_unit.sex)
                    
                    if "na" in sex.lower():
                        sex = strutils.str2symbol(scandata.sex)
                        #sex = strutils.str2R(scandata.sex)
                    
                    age = analysis_unit.age
                    
                    if isinstance(age, str) and "na" in age.lower():
                        age = scandata.age
                    
                    sig_result["Genotype"]  = genotype
                    sig_result["Data"]      = strutils.str2symbol(scandata.name)
                    #sig_result["Data"]      = strutils.str2R(scandata.name)
                    sig_result["Source"]    = strutils.str2symbol(analysis_unit.sourceID)
                    #sig_result["Source"]    = strutils.str2R(analysis_unit.sourceID)
                    sig_result["Sex"]    = sex
                    sig_result["Age"]       = age
                    sig_result["Cell"]      = strutils.str2symbol(analysis_unit.cell)
                    sig_result["Field"]     = strutils.str2symbol(analysis_unit.field)
                    sig_result["Unit"]      = strutils.str2symbol(analysis_unit.name)
                    sig_result["Unit_Type"] = strutils.str2symbol(analysis_unit.type)
                    
                    #sig_result["Cell"]      = strutils.str2R(analysis_unit.cell)
                    #sig_result["Field"]     = strutils.str2R(analysis_unit.field)
                    #sig_result["Unit"]      = strutils.str2R(analysis_unit.name)
                    #sig_result["Unit_Type"] = strutils.str2R(analysis_unit.type)
                        
                    if "Distance_From_Soma" not in analysis_unit.descriptors:
                        analysis_unit.descriptors["Distance_From_Soma"] = np.nan
                        
                    if analysis_unit.descriptors["Distance_From_Soma"] is np.nan:
                        analysis_unit.descriptors["somatic_distance"] = np.nan
                        
                    else:
                        if analysis_unit.descriptors["Distance_From_Soma"] < 100:
                            analysis_unit.descriptors["somatic_distance"] = "100"
                        
                        elif analysis_unit.descriptors["Distance_From_Soma"] >=100 and analysis_unit.descriptors["Distance_From_Soma"] < 150:
                            analysis_unit.descriptors["somatic_distance"] = "100-150"
                            
                        elif analysis_unit.descriptors["Distance_From_Soma"] >=150 and analysis_unit.descriptors["Distance_From_Soma"] < 200:
                            analysis_unit.descriptors["somatic_distance"] = "150-200"
                            
                        elif analysis_unit.descriptors["Distance_From_Soma"] >=200 and analysis_unit.descriptors["Distance_From_Soma"] < 250:
                            analysis_unit.descriptors["somatic_distance"] = "200-250"
                            
                        elif analysis_unit.descriptors["Distance_From_Soma"] >=250 and analysis_unit.descriptors["Distance_From_Soma"] < 300:
                            analysis_unit.descriptors["somatic_distance"] = "250-300"
                            
                        else:
                            analysis_unit.descriptors["somatic_distance"] = "300"
                            
                    if "Dendrite_Length" not in analysis_unit.descriptors:
                        analysis_unit.descriptors["Dendrite_Length"] = np.nan
                        
                    if "Branching_Points" not in analysis_unit.descriptors:
                        analysis_unit.descriptors["Branching_Points"] = np.nan
                        
                    if "Branch_Order" not in analysis_unit.descriptors:
                        analysis_unit.descriptors["Branch_Order"] = np.nan
                        
                    if "Spine_Length" not in analysis_unit.descriptors:
                        analysis_unit.descriptors["Spine_Length"] = np.nan
                    
                    if "Spine_Width" not in analysis_unit.descriptors:
                        analysis_unit.descriptors["Spine_Width"] = np.nan
                    
                    if "Dendrite_Width" not in analysis_unit.descriptors:
                        analysis_unit.descriptors["Dendrite_Width"] = np.nan
                    
                    for descriptor in sorted([d for d in analysis_unit.descriptors]):
                        descriptor = strutils.str2symbol(descriptor)
                        sig_result[descriptor] = analysis_unit.getDescriptor(descriptor)
                        
                    sig_result["Protocol"]  = protocol.name
                    
                    segment_name = scandata.scansBlock.segments[frame].name
                    
                    if segment_name is None or (isinstance(segment_name, str) and len(segment_name.strip()) == 0):
                        sig_result["Segment"] = "%s frame %d" % (protocol.name, frame)
                        
                    else:
                        sig_result["Segment"] = "%s frame %d" % (segment_name, frame)
                        
                    #print("sig_index", sig_index)
                    
                    sig_annots = scandata.scansBlock.segments[frame].analogsignals[sig_index].annotations
                    
                    if "Date_Time" in sig_annots:
                        if isinstance(sig_annots["Date_Time"], str):
                            try:
                                date_time = datetime.datetime.strptime(sig_annots["Date_Time"], "%Y-%m-%d %H:%M:%S.%f")
                                
                            except:
                                date_time = datetime.datetime.now()
                            
                        elif isinstance(sig_annots["Date_Time"], datetime.datetime):
                            date_time = sig_annots["Date_Time"]
                            
                        else:
                            date_time = datetime.datetime.now()
                            
                        sig_result["Analysis_Date_Time"] = date_time
            
                    n_components = len(sig_annots["Amplitude"])
                    
                    for i in range(n_components):
                        sig_result["Amplitude_EPSCaT_%d" % i] = float(sig_annots["Amplitude"][i].magnitude)
                        
                        # NOTE: 2018-02-01 09:40:28 fitting output contains:
                        # 1) a list of FitAmplitude values (one-element numpy arrays)
                        #
                        # 2) a list of coefficient names with as many elements as the 
                        #   inner lists in (3)
                        #
                        # 3) a list of parameter lists = fitted parameters;
                        #   the number of elements in each inner list depends on the 
                        #   model for the individual EPSCaT component (i.e., it depends 
                        #   on the number of decay time constants in the model)
                        #   and IS THE SAME for all EPSCaT components in a compound EPSCaT
                        #
                        # 4) r-squared: a list of n+1 values:
                        #   first value is the r-squared for the fit through the entire
                        #   compound EPSCaT
                        #
                        #   next n values are the r-squared for the fit throhugh each 
                        #   indivudual EPSCaT in the compound
                        #
                        # 5) Integration: a list of dictionaries with the result of 
                        #   integration for the whole fitted compound EPSCaT, possibly
                        #   followed by the integration results for each individual EPSCaT
                        #   component of the compound EPSCaT.
                        #
                        if "FitResult" in sig_annots:
                            sig_result["Fit_EPSCaT_%d_Amplitude" % i] = float(sig_annots["FitResult"]["FitAmplitude"][i].magnitude)
                            
                            if "Coefficients" in sig_annots["FitResult"]:
                                if "CoefficientNames" in sig_annots["FitResult"]:
                                    for k, p in enumerate(sig_annots["FitResult"]["CoefficientNames"]):
                                        coefName = strutils.str2symbol(p)
                                        sig_result["Fit_EPSCaT_%d_%s" % (i, coefName)] = float(sig_annots["FitResult"]["Coefficients"][i][k])
                                    
                                else:
                                    for k, p in enumerate(sig_annots["FitResult"]["Coefficients"]):
                                        sig_result["Fit_EPSCaT_%d_parameter_%d" % (i,k)] = float(sig_annots["FitResult"]["Coefficients"][i][k])
                                
                            if "Rsq" in sig_annots["FitResult"]:
                                sig_result["Fit_Rsq"] = float(sig_annots["FitResult"]["Rsq"][0])
                            
                                if n_components > 1 and i > 0:
                                    sig_result["Fit_EPSCaT_%d_Rsq" % i] = float(sig_annots["FitResult"]["Rsq"][i+1])

                        sig_result["FailSuccess_EPSCaT_%d_success" % i]      = bool(sig_annots["FailSuccess"]["success"][i]) # because this is a numpy.bool_
                        sig_result["FailSuccess_EPSCaT_%d_base" % i]         = float(sig_annots["FailSuccess"]["base_value"][i])
                        sig_result["FailSuccess_EPSCaT_%d_peak" % i]         = float(sig_annots["FailSuccess"]["peak_value"][i])
                        sig_result["FailSuccess_EPSCaT_%d_discriminant" % i] = float(sig_annots["FailSuccess"]["discr_value"][i])
                        sig_result["FailSuccess_EPSCaT_%d_2D" % i]           = bool(sig_annots["FailSuccess"].get("Discr_2D", True))
                        
                        if len(sig_annots["FitResult"]["Integration"]):
                            for int_dict in sig_annots["FitResult"]["Integration"]:
                                for (key, value) in int_dict.items():
                                    sig_result["Integration_%s" % key] = value
                    
                    result.append(sig_result)
                   
    # NOTE: 2019-01-08 23:12:34
    # here, result is a possibly empty list of Python dictionaries with identical
    # keys (see sig_result above)
    if len(result):
        if isinstance(filename, str) and len(filename.strip()):
            # write result to a csv file
            import os, sys
            (name, extn) = os.path.splitext(filename)
            
            if len(extn) == 0 or extn != ".csv":
                filename += ".csv"
                
                    #writer.writerow(d)
                    
        if return_type.lower() == "html":
            report_io = io.StringIO()
            
            print("<table>", file=report_io)
            
            for key in result[0].keys():
                s = ["<tr><td><b>%s:</b></td>" % key]
                
                for d in result:
                    s.append("<td>%s</td>" % str(d[key]))
                    
                s.append("</tr>")
                    
                print("".join(s), file=report_io)
            
            print("</table>", file=report_io)
            
            text_output = report_io.getvalue()
            
            report_io.close()
            
            if filename is not None:
                with open(filename, "w", newline="") as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=result[0].keys(), delimiter="\t", dialect=csv.unix_dialect)
                    
                    writer.writeheader()
                    
                    for d in result:
                        row = dict()
                        for key in d:
                            if isinstance(d[key], bool):
                                row[key] = str(d[key]).upper()
                                
                            else:
                                row[key] = d[key]
                        
                        writer.writerow(row)
            
            result = text_output
            
        elif return_type.lower() == "dataframe":
            result = pd.DataFrame(result)
            
            # NOTE: 2019-01-08 15:44:27
            # set categorical data types where needed
            categoriseLSCaTResult(result)
            
            
            if filename is not None:
                result.to_csv(filename, na_rep="NA")
                
        elif return_type.lower() == "list":
            if filename is not None:
                with open(filename, "w", newline="") as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=result[0].keys(), delimiter="\t", dialect=csv.unix_dialect)
                    
                    writer.writeheader()
                    
                    for d in result:
                        row = dict()
                        for key in d:
                            if isinstance(d[key], bool):
                                row[key] = str(d[key]).upper()
                                
                            else:
                                row[key] = d[key]
                        
                        writer.writerow(row)
                        
        else:
            raise ValueError("Invalid return_type specified; got %s while expecting %s" % (return_type, str(("dataframe", "html", "list"))))
            

    else: # empty results list
        if return_type.lower() == "html":
            result = "<table></table>"
            
        elif return_type.lower() == "dataframe":
            result = pd.DataFrame()
            
        # NOTE: 2018-11-30 21:45:09
        # result is a list initially 

    return result

def writeEPSCaTReport(result, filename):
    """Write analysis report to a csv file
    """
    import io, csv
    
    if isinstance(result, pd.DataFrame):
        result.to_csv(filename, na_rep = "NA")
        
    elif isinstance(result, list):
        if len(result) == 0:
            raise ValueError("Nothing to do with an empty list!")
        
        if not all([isinstance(d, collections.OrderedDict) for d in result]):
            raise TypeError("Expecting a python list of OrderedDict objects")
        
        if isinstance(filename, str) and len(filename.strip()):
            # write result to a csv file
            import os, sys
            (name, extn) = os.path.splitext(filename)
            
            if len(extn) == 0 or extn != ".csv":
                filename += ".csv"
                    
            with open(filename, "w", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=result[0].keys(), delimiter="\t", dialect=csv.unix_dialect)
                
                writer.writeheader()
                
                for d in result:
                    row = dict()
                    for key in d:
                        if isinstance(d[key], bool):
                            row[key] = str(d[key]).upper()
                            
                        else:
                            row[key] = d[key]
                    
                    writer.writerow(row)
                
    else:
        raise TypeError("Expecting a pandas.DataFrame or a python list; got %s instead" % type(result).__name__)
    

@safeWrapper
def detectRoisInProfile(profile, order, *args, **kwargs):
    if not isinstance(profile, (DataSignal, np.ndarray)):
        raise TypeError("Expecting a datatypes.DataBag or a numpy.ndarray; got %s instead" % type(profile).__name__)
    
    bounds = (0, np.inf)
    
    if len(args):
        ngauss, rem = divmod(len(args), 3)
        
        if ngauss < 1 or rem != 1:
            raise RuntimeError("There must be exactly n * 3 + 1; got %d instead" % len(args))
        
        roilocations = list()
        scale = list()
        width = list()
        
        for k in range(ngauss):
            a, b, c = args[slice(k*3, k*3 +3)]
            scale.append(a)
            roilocations.append(b)
            width.append(c)
        
        offset = args[-1]
        
    else:
        maximaNdx, _ = signal.argrelmax(profile, order=order)
        
        roilocations = list(maximaNdx)
        
        ngauss = len(roilocations)
        
        width = order
        
        scale = float(profile.range())
        
        offset = float(profile.min())

    if len(kwargs):
        if "scale" in kwargs:
            scale = kwargs["scale"]
            
        if "offset" in kwargs:
            offset = kwargs["offset"]
            
        if "width" in kwargs:
            width = kwargs["width"]
        
        if "bounds" in kwargs:
            bounds = kwargs["bounds"]
    
    
    x = np.arange(profile.shape[0])
    
    
    fitted_params, fitted_params_cov, fitted_curve = crvf.fitGauss1DSum(x, profile, roilocations, \
        width=width, scale=scale, offset=offset, bounds = bounds)
    
    _, individually_fitted_peaks = models.gaussianSum1D(x, *fitted_params, components=True)
    
    sst = np.sum((profile.magnitude.squeeze() - profile.magnitude.mean())**2)
    
    sse = np.sum((fitted_curve - profile.magnitude.squeeze())**2)
    
    rsquare = 1 - sse/sst
    
    fitted_scale = list(fitted_params[slice(0,-1,3)])
    
    fitted_scale_cov = list(fitted_params_cov[slice(0,-1,3)])
    
    fitted_location = list(fitted_params[slice(1,-1,3)])
    
    fitted_location_cov = list(fitted_params_cov[slice(1,-1,3)])
    
    fitted_width = list(fitted_params[slice(2,-1,3)])
    
    fitted_width_cov = list(fitted_params[slice(2,-1,3)])
    
    fitted_offset = fitted_params[-1]
    
    fitted_offset_cov = fitted_params_cov[-1]
    
    return  (fitted_scale, fitted_location, fitted_width, fitted_offset), \
            (fitted_scale_cov, fitted_location_cov, fitted_width_cov, fitted_offset_cov),\
            rsquare, fitted_curve, individually_fitted_peaks, (roilocations, width, scale, offset)
    


def addMirrorCursor(data, vc):
    """Generates a poin cursor on the scanline trajectory on the scene.
    The cursor's position on the scanline trajectory mirrors the corresponding
    vertical cursor X coordinate in the linescan image.
    
    Parameters:
    ===========
    
    data: datatypes.ScanData object
    
    vc: a str or a pictgui.Cursor with type == pictgui.GraphicsObjectType.vertical_cursor
    
        when a str, it must be the name of a vertical cursor already defined in 
        the data linescans
    
    The generated point cursor have the same name its corresponding vertical cursor.
    
    Raises errors if:
    
    a) data has no scene image or no scans image
    
    b) data has no scanline trajectory defined in the scene
    
    c) the scanline trajectory is not a line (defined by a Move point and a Line point)
     or is not a polyline/polygon where each vertex corresponds to a column on the 
     linescan image (i.e. scanline constructed at acquisition time as a freehand line)
    
    d) the vc cursor does not belong to this data
    
    """
    if not isinstance(data, ScanData):
        raise TypeError("Expecting a ScanData object; got %s instead" % type(data).__name__)

    if len(data.scene) == 0:
        raise ValueError("Data has no scene images")
    
    if len(data.scans) == 0:
        raise ValueError("Data has no linescan images")
    
    if isinstance(vc, str):
        if vc not in data.scansCursors.keys():
            raise KeyError("Cursor %s not present in data linescans" % vc.name)
        
        vc = data.scansCursors[vc]
        
    elif not isinstance(vc, pgui.Cursor) or vc.type != pgui.GraphicsObjectType.vertical_cursor:
        raise TypeError("Expecting a vertical cursor; got %s" % vc)
    
    elif vc not in data.scansCursors.values():
        raise ValueError("Specified verticcal cursor %s does not belong to this data" % vc)
    
    #if "scanline" not in data.sceneRois.keys() or not isinstance(data.sceneRois["scanline"], pgui.PlanarGraphics):
        #raise ValueError("Data does not have a scanline roi defined")
    
    #path = data.sceneRois["scanline"]
    
    data._upgrade_API_()
    
    if data.scanRegion is None:
        raise ValueError("Data does not have a scan region defined in the scene")
    
    path = data.scanRegion
    
    if path.type != pgui.GraphicsObjectType.line and \
        path.type != pgui.GraphicsObjectType.polyline:
        raise ValueError("This function accepts scanline rois of type line and polyline only; this data has scan region of type %s" % path.type)
    
    if not all([isinstance(e, (pgui.Move, pgui.Line)) for e in path]):
        raise TypeError("The scan region must be composed of pictgui.Move and pictgui.Line planar graphics only")
    
    if vc.name in data.sceneCursors.keys() and data.sceneCursors[vc.name].type == pgui.GraphicsObjectType.point_cursor:
        warnings.warn("%s already has a mirror cursor" % vc)
        return
    
    if len(path) == 2:
        dx = path[1].x - path[0].x
        dy = path[1].y - path[0].y
        
        l = math.sqrt(dx ** 2 + dy ** 2)
        
        nx = vc.x / l
        
        point_x = dx * nx + path[0].x
        point_y = dy * nx + path[0].y

    elif len(path) == int(data.scans[0].width):
        element = path[int(c.x)]
        point_x = element.x
        point_y = element.y
        
    else:
        raise NotImplementedError("Mirror points can only be added on a scanline trajectory that is a line or a freehand line")
        
    pc = pgui.Cursor(point_x, point_y,
                        data.scene[0].shape[0], data.scene[0].shape[1],
                        1, 1, c.xwindow//2,
                        name = c.name,
                        graphicstype = pgui.GraphicsObjectType.point_cursor)
    
    pc.frameIndices = c.frameIndices
    
    pc.linkFrames(hard = c.hasHardFrameAssociations)
    
    c.linkToObject(pc, mapScansVCToScenePCOnPath, path)
    #c.linkToObject(pc, c.map_to_pc_on_path, path)
    
    data.sceneCursors[c.name] = pc
    
def generateMirrorCursors(data):
    """Generates point_cursors on the scanline trajectory in the scene, to mirror the X coordinate of the vertical linescan cursors
    
    Unlike addMirrorCursor(), this function will REPLACE all objects in sceneCursors
    that have names identical to those of the vertical cursors in linescans.
    
    """
    if not isinstance(data, ScanData):
        raise TypeError("Expecting a ScanData object; got %s instead" % type(data).__name__)

    if len(data.scene) == 0:
        raise ValueError("Data has no scene images")
    
    if len(data.scans) == 0:
        raise ValueError("Data has no linescan images")
    
    if len(data.scansCursors) == 0:
        raise ValueError("Data has no linescan cursors defined")
    
    #if "scanline" not in data.sceneRois.keys() or not isinstance(data.sceneRois["scanline"], pgui.PlanarGraphics):
        #raise ValueError("Data does not have a scanline roi defined")
    
    #path = data.sceneRois["scanline"]
    
    data._upgrade_API_()
    
    if data.scanRegion is None:
        raise ValueError("Data does not have a scan region defined in the scene")
    
    path = data.scanRegion
    
    if path.type != pgui.GraphicsObjectType.line and \
        path.type != pgui.GraphicsObjectType.polyline:
        raise ValueError("This function accepts scanline rois of type line and polyline only; this data has scanline of type %s" % path.type)
    
    if not all([isinstance(e, (pgui.Move, pgui.Line)) for e in path]):
        raise TypeError("The scanline must be composed of pictgui.Move and pictgui.Line planar graphics only")
    
    lsc = [c for c in data.scansCursors.values() if c.type == pgui.GraphicsObjectType.vertical_cursor]

    if len(lsc) == 0:
        raise ValueError("Data has no vertical linescan cursors")
    
    for c in lsc:
        if c.name in data.sceneCursors.keys():
            warnings.warn("Data already has a scene cursor named %s; it will be replaced" % c.name)
            
        if len(path) == 2:
            dx = path[1].x - path[0].x
            dy = path[1].y - path[0].y
            
            l = math.sqrt(dx ** 2 + dy ** 2)
            
            nx = c.x / l
            
            point_x = dx * nx + path[0].x
            point_y = dy * nx + path[0].y
                                            
        elif len(path) == int(data.scans[0].width):
            element = path[int(c.x)]
            point_x = element.x
            point_y = element.y
            
        else:
            raise NotImplementedError("In %s: Mirror points can only be added on a scanline trajectory that is a line or a freehand line" % data.name)
            
        pc = pgui.Cursor(point_x, point_y,
                         data.scene[0].shape[0], data.scene[0].shape[1],
                         1, 1, c.xwindow//2,
                         name = c.name,
                         graphicstype = pgui.GraphicsObjectType.point_cursor)
        
        pc.frameIndices = c.frameIndices
        
        pc.linkFrames(hard = c.hasHardFrameAssociations)
        
        c.linkToObject(pc, mapScansVCToScenePCOnPath, path)
        #c.linkToObject(pc, c.map_to_pc_on_path, path)
        
        data.sceneCursors[c.name] = pc
        
def removeMirrorCursors(data):
    """Removes ALL mirror point cursors created with generateMirrorCursors()
    
    Uses the names of the linescan vertical cursors to remove the omonymous 
    point cursors from the scene. 
    WARNING: the scene cursors are nto checked that theyare point_cursors!!!
    
    """
    if not isinstance(data, ScanData):
        raise TypeError("Expecting a ScanData object; got %s instead" % type(data).__name__)

    if len(data.scene) == 0:
        raise ValueError("Data has no scene images")
    
    if len(data.scans) == 0:
        raise ValueError("Data has no linescan images")
    
    if len(data.scansCursors) == 0:
        raise ValueError("Data has no linescan cursors defined")
    
    lsc = [c for c in data.scansCursors.values() if c.type == pgui.GraphicsObjectType.vertical_cursor]

    if len(lsc) == 0:
        raise ValueError("Data has no vertical linescan cursors")
    
    for c in lsc:
        for obj in c.linkedObjects:
            c.unlinkFromObject(obj)
            if obj.name in data.sceneCursors.keys():
                data.sceneCursors.pop(obj.name, None)
            
def removeMirrorCursor(data, vc):
    """
    Parameters:
    ===========
    
    data: datatypes.ScanData object
    
    vc: a str or a pictgui.Cursor with type == pictgui.GraphicsObjectType.vertical_cursor
    
        when a str, it must be the name of a vertical cursor already defined in 
        the data linescans
    
    """
    
    if not isinstance(data, ScanData):
        raise TypeError("Expecting a ScanData object; got %s instead" % type(data).__name__)

    if len(data.scene) == 0:
        raise ValueError("Data has no scene images")
    
    if len(data.scans) == 0:
        raise ValueError("Data has no linescan images")
    
    if len(data.scansCursors) == 0:
        raise ValueError("Data has no linescan cursors defined")
    
    if isinstance(vc, str):
        if vc not in data.scansCursors.keys():
            raise KeyError("Cursor %s not present in data linescans" % vc.name)
        
        vc = data.scansCursors[vc]
        
    elif not isinstance(vc, pgui.Cursor) or vc.type != pgui.GraphicsObjectType.vertical_cursor:
        raise TypeError("Expecting a vertical cursor; got %s" % vc)
    
    elif vc not in data.scansCursors.values():
        raise ValueError("Specified vertical cursor %s does not belong to this data" % vc)
    
    data.sceneCursors.pop(vc.name, None)
    
    
class LSCaTWindow(ScipyenFrameViewer, __UI_LSCaTWindow__):
    # NOTE: 2021-09-23 10:43:12
    # ScipyenFrameViewer <- ScipyenViewer <- WorkspaceGuiMixin
    # NOTE: 2021-07-08 10:04:42 About configuration/settings
    #
    # Individual viewers include: sceneviewers, scansviewers, ephysviewers, 
    # sceneblockviewers, scansblockviewers, profileviewers and reportWindow.
    #
    # Their individual settings are stored in the LSCaTWindow category in 
    # Scipyen's Qt configuration file and are LOADED when the viewers are being
    # initialized (see self._setup_... methods)
    #
    # On the other hand, the settings for LSCaT and its client viewers are ALL
    # SAVED when LSCaTWindow is closed (see self.slot_Quit() PyQt slot)
    viewer_for_types = (ScanData,)
    
    view_action_name = "LSCaT Window"
    
    default_scanline_spline_order = 3
    
    # NOTE 2020-09-05 19:50:36
    # because defaultPureletFilterOptions is a class attribute, it will be
    # instantiated when this class is being defined upon importing this module
    defaultPureletFilterOptions = DataBag()
    
    #print(type(defaultPureletFilterOptions))
    
    defaultPureletFilterOptions.scene = DataBag()
    
    defaultPureletFilterOptions.scene.ref = DataBag()
    defaultPureletFilterOptions.scene.ref.alpha = 1
    defaultPureletFilterOptions.scene.ref.beta = 0
    defaultPureletFilterOptions.scene.ref.sigma = 0
    defaultPureletFilterOptions.scene.ref.j = 4
    defaultPureletFilterOptions.scene.ref.t = 3
    
    defaultPureletFilterOptions.scene.ind = DataBag()
    defaultPureletFilterOptions.scene.ind.alpha = 1
    defaultPureletFilterOptions.scene.ind.beta = 0
    defaultPureletFilterOptions.scene.ind.sigma = 0
    defaultPureletFilterOptions.scene.ind.j = 4
    defaultPureletFilterOptions.scene.ind.t = 3
    
    defaultPureletFilterOptions.scans = DataBag()
    
    defaultPureletFilterOptions.scans.ref = DataBag()
    defaultPureletFilterOptions.scans.ref.alpha = 1
    defaultPureletFilterOptions.scans.ref.beta = 0
    defaultPureletFilterOptions.scans.ref.sigma = 0
    defaultPureletFilterOptions.scans.ref.j = 4
    defaultPureletFilterOptions.scans.ref.t = 3
    
    defaultPureletFilterOptions.scans.ind = DataBag()
    defaultPureletFilterOptions.scans.ind.alpha = 1
    defaultPureletFilterOptions.scans.ind.beta = 0
    defaultPureletFilterOptions.scans.ind.sigma = 0
    defaultPureletFilterOptions.scans.ind.j = 4
    defaultPureletFilterOptions.scans.ind.t = 3
    
    defaultGaussianFilterOptions = DataBag()
    
    defaultGaussianFilterOptions.scene = DataBag()
    
    defaultGaussianFilterOptions.scene.ref = DataBag()
    defaultGaussianFilterOptions.scene.ref.size = 0
    defaultGaussianFilterOptions.scene.ref.sigma = 5
    
    defaultGaussianFilterOptions.scene.ind = DataBag()
    defaultGaussianFilterOptions.scene.ind.size = 0
    defaultGaussianFilterOptions.scene.ind.sigma = 5
    
    defaultGaussianFilterOptions.scans = DataBag()
    
    defaultGaussianFilterOptions.scans.ref = DataBag()
    defaultGaussianFilterOptions.scans.ref.size = 0
    defaultGaussianFilterOptions.scans.ref.sigma = 5
    
    defaultGaussianFilterOptions.scans.ind = DataBag()
    defaultGaussianFilterOptions.scans.ind.size = 0
    defaultGaussianFilterOptions.scans.ind.sigma = 5
    
    defaultBinomialFilterOptions = DataBag()
    
    defaultBinomialFilterOptions.scene = DataBag()
    defaultBinomialFilterOptions.scene.ref = DataBag()
    defaultBinomialFilterOptions.scene.ref.radius = 10
    defaultBinomialFilterOptions.scene.ind = DataBag()
    defaultBinomialFilterOptions.scene.ind.radius = 10
    
    defaultBinomialFilterOptions.scans = DataBag()
    defaultBinomialFilterOptions.scans.ref = DataBag()
    defaultBinomialFilterOptions.scans.ref.radius = 10
    defaultBinomialFilterOptions.scans.ind = DataBag()
    defaultBinomialFilterOptions.scans.ind.radius = 10

    def __init__(self, *args, parent:(QtWidgets.QMainWindow, type(None)) = None, win_title="LSCaT", **kwargs):
        self.threadpool = QtCore.QThreadPool()
        
        # guard variables for filtering
        self._scene_processing_idle_ = True
        self._scans_processing_idle_ = True
        self._epscat_analysis_idle_ = True
        self._generic_work_idle_ = True
        
        #self._data_ = None # inherited from ScipyenViewer
        self._current_frame_scan_region_ = list() # so that its contents will be updated
        
        self._data_var_name_ = None # optionally gets a str value further below
        
        self._selected_analysis_cursor_ = None
        self._selected_analysis_unit_ = None
        
        #self._default_cursors_color_ = pgui.GraphicsObject.defaultCBCursorColor
        
        #self._default_rois_color_ = QCore.Qt.green
        
        
        # ###
        # PrairieView import default values for trigger detection
        # ###
        # NOTE: 2018-06-20 12:20:26
        # DEPRECATED
        
        #self._linked_graphics_updater_ = QtCore.QThread()
        
        # ###
        # BEGIN window lists
        # ###
        
        self.sceneviewers   = list()    # list of ImageViewer
        
        self.scansviewers    = list()    # list of ImageViewer
        
        self.ephysviewers   = list()    # list of SignalViewer - only ONE window
        
        self.scansblockviewers  = list()    # list of SignalViewer - only ONE window
        
        self.sceneblockviewers = list()# list of SignalViewer - only ONE window
        
        self.profileviewers = list()    # list of SignalViewer - only ONE window
        
        # ###
        # END window lists
        # ###
        
        self._displayed_scene_channels_ = list()
        
        self._displayed_scan_channels_ = list()
        
        self._current_protocols_ = []
        
        self.currentSceneFrame = 0
        
        self.currentScanFrame = 0
        
        self._current_frame_index_ = 0
        
        self._frame_selector_ = None # a list/tuple of frames, typically
                                     # can also be a range or, when the total
                                     # number of frames in the data is known,
                                     # a slice object
        
        # ###
        # BEGIN channels configuration
        # ###
        
        self._scene_roi_channel_= 0
        self._scene_roi_channel_name_= ""
        
        # to be synchronised with values from the EPSCaT tab
        self._scan_ref_channel_ = 0
        self._scan_ref_channel_name_ =""
        
        self._scan_cat_channel_ = 1
        self._scan_cat_channel_name_ = ""
        
        
        # ###
        # END channels configuration
        # ###
        
        # ###
        # BEGIN Filter options
        # ###
        
        # NOTE: 2019-10-12 14:24:26
        # migrate filter logic from ScanData to here
        self._scene_filters_ = dict()
        self._scans_filters_ = dict()
        
        # NOTE: 2017-11-17 10:24:39
        # TODO set up configuration framework to make these persistent
        # TODO implement undo/redo/reset to default functionality
        # probably a pain to do it for every single value, address all params
        # "en bloc"
        
        #self.scanline_spline_order = 3
        
        #self.defaultPureletFilterOptions = DataBag()
        
        #self.defaultPureletFilterOptions.scene = DataBag()
        
        #self.defaultPureletFilterOptions.scene.ref = DataBag()
        #self.defaultPureletFilterOptions.scene.ref.alpha = 1
        #self.defaultPureletFilterOptions.scene.ref.beta = 0
        #self.defaultPureletFilterOptions.scene.ref.sigma = 0
        #self.defaultPureletFilterOptions.scene.ref.j = 4
        #self.defaultPureletFilterOptions.scene.ref.t = 3
        
        #self.defaultPureletFilterOptions.scene.ind = DataBag()
        #self.defaultPureletFilterOptions.scene.ind.alpha = 1
        #self.defaultPureletFilterOptions.scene.ind.beta = 0
        #self.defaultPureletFilterOptions.scene.ind.sigma = 0
        #self.defaultPureletFilterOptions.scene.ind.j = 4
        #self.defaultPureletFilterOptions.scene.ind.t = 3
        
        #self.defaultPureletFilterOptions.scans = DataBag()
        
        #self.defaultPureletFilterOptions.scans.ref = DataBag()
        #self.defaultPureletFilterOptions.scans.ref.alpha = 1
        #self.defaultPureletFilterOptions.scans.ref.beta = 0
        #self.defaultPureletFilterOptions.scans.ref.sigma = 0
        #self.defaultPureletFilterOptions.scans.ref.j = 4
        #self.defaultPureletFilterOptions.scans.ref.t = 3
        
        #self.defaultPureletFilterOptions.scans.ind = DataBag()
        #self.defaultPureletFilterOptions.scans.ind.alpha = 1
        #self.defaultPureletFilterOptions.scans.ind.beta = 0
        #self.defaultPureletFilterOptions.scans.ind.sigma = 0
        #self.defaultPureletFilterOptions.scans.ind.j = 4
        #self.defaultPureletFilterOptions.scans.ind.t = 3
        
        #self.defaultGaussianFilterOptions = DataBag()
        
        #self.defaultGaussianFilterOptions.scene = DataBag()
        
        #self.defaultGaussianFilterOptions.scene.ref = DataBag()
        #self.defaultGaussianFilterOptions.scene.ref.size = 0
        #self.defaultGaussianFilterOptions.scene.ref.sigma = 5
        
        #self.defaultGaussianFilterOptions.scene.ind = DataBag()
        #self.defaultGaussianFilterOptions.scene.ind.size = 0
        #self.defaultGaussianFilterOptions.scene.ind.sigma = 5
        
        #self.defaultGaussianFilterOptions.scans = DataBag()
        
        #self.defaultGaussianFilterOptions.scans.ref = DataBag()
        #self.defaultGaussianFilterOptions.scans.ref.size = 0
        #self.defaultGaussianFilterOptions.scans.ref.sigma = 5
        
        #self.defaultGaussianFilterOptions.scans.ind = DataBag()
        #self.defaultGaussianFilterOptions.scans.ind.size = 0
        #self.defaultGaussianFilterOptions.scans.ind.sigma = 5
        
        #self.defaultBinomialFilterOptions = DataBag()
        
        #self.defaultBinomialFilterOptions.scene = DataBag()
        #self.defaultBinomialFilterOptions.scene.ref = DataBag()
        #self.defaultBinomialFilterOptions.scene.ref.radius = 10
        #self.defaultBinomialFilterOptions.scene.ind = DataBag()
        #self.defaultBinomialFilterOptions.scene.ind.radius = 10
        
        #self.defaultBinomialFilterOptions.scans = DataBag()
        #self.defaultBinomialFilterOptions.scans.ref = DataBag()
        #self.defaultBinomialFilterOptions.scans.ref.radius = 10
        #self.defaultBinomialFilterOptions.scans.ind = DataBag()
        #self.defaultBinomialFilterOptions.scans.ind.radius = 10
        
        # ###
        # END filter options
        # ###
        
        self._report_dataframe_ = None
        
        scandata = None
        
        if len(args):
            if isinstance(args[0], ScanData):
                scandata = args[0]
                
            if len(args) == 2 and (isinstance(args[1], str) and len(args[1].strip())):
                self._data_var_name_ = args[1]
                
        # NOTE: 2022-01-16 13:08:12
        # super()._init__(...) below also calls self._configureUI_()
        super().__init__(data=scandata, win_title=win_title, doc_title=self._data_var_name_, 
                         parent=parent, **kwargs) # also calls self._configureUI_()
        
        self.loadSettings()
        
    def _connect_gui_slots_(self, signal_slots):
        for item in signal_slots:
            if len(item) == 3 and isinstance(item[2], QtCore.Qt.ConnectionType):
                item[0].connect(item[1], type = item[2])
                
            else:
                item[0].connect(item[1])
                
    def _disconnect_gui_slots_(self, signal_slots):
        for item in signal_slots:
            item[0].disconnect(item[1])
            
    #def saveSettings(self):
        #"""Overrides ScipyenViewer.saveSettings
        #"""
        ##print("%s.saveSettings %s" % (self.__class__.__name__, self.winTitle))
        ## NOTE: 2021-07-08 10:18:11
        ## Saves the settings for the QMainWindow instances of LSCaTWindow AND of
        ## its (child, or client) viewers
        #self.saveWindowSettings()# overrides ScipyenViewer.saveWindowSettings
        
        ## NOTE: 2021-07-08 10:19:45
        ## Saves the settings unrelated to the QMainWindow instances of LSCaTWindow
        ## AND of its clien viewers
        #self.saveViewerSettings()
    
    #def loadSettings(self):
        ##print("%s.loadSetting" % self.winTitle)
        ## NOTE: 2021-07-08 10:13:54
        ## loadWindowSettings is inherited from ScipyenViewer and will ONLY load
        ## LSCaTWindow settings for its main GUI window. 
        ## the settings for individual viewers are NOT loaded here. Instead, they 
        ## are loaded right after their initialization in the various 
        ## self._init_viewers_() method of LSCaTWindow
        #self.loadWindowSettings()
        
        ## NOTE: Similarly, settings for individual client viewers, unrelated to 
        ## their QMainWindow instances are also loaded after their initialization.
        #self.loadViewerSettings()
        
    def saveViewerSettings(self):
        """Overrides ScipyenViewer.saveViewerSettings()
        """
        # TODO/FIXME: 2021-07-08 10:55:21
        # settings for LnF of cursors & rois
        # TODO/FIXME 2021-08-23 18:43:36
        # use traitlets.config.Configurable and confuse
        from matplotlib.colors import Colormap
        
        #self.qsettings.setValue("LSCaTAnalysis/Use_Opaque_Labels", self.actionOpaque_cursor_labels.isChecked())
        
        #self.qsettings.setValue("LSCaTAnalysis/Link_Scan_Vertical_Cursors_to_Scene_Point_Cursors", self.actionLink_vertical_scan_cursors_to_scene_point_cursors.isChecked())
        
        #self.qsettings.setValue("LSCaTAnalysis/Plot_long_fits", self.actionPlot_long_fits.isChecked())

        #for k, w in enumerate(self.sceneviewers):
            #if isinstance(w.colorMap, Colormap):
                #self.qsettings.setValue("LSCaTAnalysis/SceneWindow_%d_ColorMap" % k, w.colorMap.name)
                
            #else:
                #self.qsettings.setValue("LSCaTAnalysis/SceneWindow_%d_ColorMap" % k, None)
                
        #for k, w in enumerate(self.scansviewers):
            #if isinstance(w.colorMap, Colormap):
                #self.qsettings.setValue("LSCaTAnalysis/ScansWindow_%d_ColorMap" % k, w.colorMap.name)
                
            #else:
                #self.qsettings.setValue("LSCaTAnalysis/ScansWindow_%d_ColorMap" % k, None)
                
        #if len(self.profileviewers):
            #w = self.profileviewers[0]
            #for dw in w.dockWidgets:
                #self.qsettings.setValue("LSCaTAnalysis/ProfileWindow_%s" % dw[0], dw[1].isVisible())
            
        #if len(self.scansblockviewers):
            #w = self.scansblockviewers[0]
            #for dw in w.dockWidgets:
                #self.qsettings.setValue("LSCaTAnalysis/ScansDataWindow_%s" % dw[0], dw[1].isVisible())
            
        #if len(self.ephysviewers):
            #w = self.ephysviewers[0]
            #for dw in w.dockWidgets:
                #self.qsettings.setValue("LSCaTAnalysis/EphysWindow_%s" % dw[0], dw[1].isVisible())
            
        #if len(self.scansblockviewers):
            #w = self.scansblockviewers[0]
            #for dw in w.dockWidgets:
                #self.qsettings.setValue("LSCaTAnalysis/SceneDataWindow_%s" % dw[0], dw[1].isVisible())
                
            
    def saveWindowSettings(self):
        """Overrides ScipyenViewer.saveWindowSettings()
        Also saves window settings for child windows.
        
        NOTE: The window settings for each of these child windows are loaded
        individually when they are initialized.
        """
        # NOTE: 2021-08-24 09:49:01
        # window settings for each child window MUST be saved here because
        # they all inherit from ScipyenViewer and WorkspaceGuiMixin and are NOT
        # toplevel!
        # because:
        # a) they are not top level 
        #print("%s.saveWindowSettings %s" % (self.__class__.__name__, self.winTitle))
        #print("%s.saveWindowSettings %s save client windows settings" % (self.__class__.__name__, self.winTitle))
        #for k, w in enumerate(self.sceneviewers):
            #custom = dict()
            #custom["ColorMap"] = w.colorMap.name
            
            #saveWindowSettings(self.qsettings, w, 
                               #prefix="SceneWindow_%d" % k, **custom)
                
        #for k, w in enumerate(self.scansviewers):
            #custom = dict()
            #custom["ColorMap"] = w.colorMap.name
            
            #saveWindowSettings(self.qsettings, w, 
                               #prefix="ScansWindow_%d" % k, **custom)
                    
        #if len(self.profileviewers):
            #w = self.profileviewers[0]
            #saveWindowSettings(self.qsettings, w, 
                               #prefix="ProfileWindow")
                
        #if len(self.scansblockviewers):
            #w = self.scansblockviewers[0]
            #saveWindowSettings(self.qsettings, w, 
                               #prefix="ScansDataWindow")
                
        #if self.reportWindow.isVisible():
            #saveWindowSettings(self.qsettings, w, prefix="ReportWindow")
            
        #if len(self.ephysviewers):
            #w = self.ephysviewers[0]
            #saveWindowSettings(self.qsettings, w, prefix="EphysWindow")
            
        #if len(self.scansblockviewers):
            #w = self.scansblockviewers[0]
            #saveWindowSettings(self.qsettings, w, prefix="SceneDataWindow")
                
        #print("%s.saveWindowSettings %s Call super().saveWindowSettings" % (self.__class__.__name__, self.winTitle))
        super().saveWindowSettings() # to save LSCaT window pos, geometry & state
            
    def loadViewerSettings(self):
        """Loads settings unrelated to QMainWindowe instance.
        Concerns only the LSCaTWindow and not its client image/signal viewers
        """
        pass
        # TODO/FIXME 2021-08-23 18:43:36
        # use traitlets.config.Configurable and confuse
        #use_opaque_labels = self.qsettings.value("LSCaTAnalysis/Use_Opaque_Labels", False)
        
        #if isinstance(use_opaque_labels, str):
            #self.actionOpaque_cursor_labels.setChecked(use_opaque_labels.lower().strip() == "true")
                
        #else:
            #self.actionOpaque_cursor_labels.setChecked(use_opaque_labels)
        
        #link_scan_vc_to_scene_pc = self.qsettings.value("LSCaTAnalysis/Link_Scan_Vertical_Cursors_to_Scene_Point_Cursors", False)
        
        #if isinstance(link_scan_vc_to_scene_pc, str):
            #self.actionLink_vertical_scan_cursors_to_scene_point_cursors.setChecked(link_scan_vc_to_scene_pc.lower().strip() == "true")

        #else:
            #self.actionLink_vertical_scan_cursors_to_scene_point_cursors.setChecked(link_scan_vc_to_scene_pc)
            
        #plot_long_fits = self.qsettings.value("LSCaTAnalysis/Plot_long_fits", False)
        
        #if isinstance(plot_long_fits, str):
            #self.actionPlot_long_fits.setChecked(plot_long_fits.lower().strip() == "true")
            
        #else:
            #self.actionPlot_long_fits.setChecked(plot_long_fits)
            
    def _configureUI_(self):
        self.setupUi(self)
        
        # NOTE: 2018-05-21 15:32:17
        # WARNING Manually-added GUI objects that need to be signal-slot connected, 
        # WARNING must be defined HERE !!!
        
        self.addProtocolAction = QtWidgets.QAction("Add protocol", self)
        self.removeProtocolAction = QtWidgets.QAction("Remove protocol", self)
        
        self.addEPSCaTAction = QtWidgets.QAction("Add component", self)
        self.removeEPSCaTAction = QtWidgets.QAction("Remove component", self)
        
        # NOTE: too complex to treat here: FIXME TODO
        self._filter_gui_slots_ = [
            ]
        
        self._menu_actions_gui_slots_ = [
                [self.whatsThisAction.triggered,                        self.slot_enterWhatsThisMode,           QtCore.Qt.QueuedConnection],
                [self.actionOpen.triggered,                             self.slot_openScanDataPickleFile,       QtCore.Qt.QueuedConnection],
                [self.actionImportPrairieView.triggered,                self.slot_importPrairieView,            QtCore.Qt.QueuedConnection],
                [self.actionLoadFromWorkspace.triggered,                self.slot_loadWorkspaceScanData,        QtCore.Qt.QueuedConnection],
                [self.actionUpdate.triggered,                           self.displayFrame,                    QtCore.Qt.QueuedConnection],
                [self.actionSave.triggered,                             self.slot_pickleLSData,                 QtCore.Qt.QueuedConnection],
                [self.actionCopy_to_workspace.triggered,                self.slot_exportCopyToWorkspace,        QtCore.Qt.QueuedConnection],
                [self.actionQuit.triggered,                             self.slot_Quit],
                [self.actionEphysFrom_file.triggered,                   self.slot_addReplaceElectrophysiologyFile,  QtCore.Qt.QueuedConnection],
                [self.actionEphysFrom_workspace.triggered,              self.slot_addReplaceElectrophysiologyWorkspace,  QtCore.Qt.QueuedConnection],
                [self.actionReorder_ephys_segments.triggered,           self.slot_reorderEphysSegments,  QtCore.Qt.QueuedConnection],
                [self.actionResults_window.triggered,                   self.slot_showReportWindow,            QtCore.Qt.QueuedConnection],
                [self.actionCollect.triggered,                          self.slot_collectAnalysisUnits,         QtCore.Qt.QueuedConnection],
                [self.actionReport.triggered,                           self.slot_reportLSCaTResults,           QtCore.Qt.QueuedConnection],
                [self.actionAdopt_options.triggered,                    self.slot_adoptAnalysisOptionsFromScanData, QtCore.Qt.QueuedConnection],
                [self.actionAdopt_units.triggered,                      self.slot_adoptAnalysisUnitsFromScanData, QtCore.Qt.QueuedConnection],
                [self.actionAdopt_protocols.triggered,                  self.slot_adoptTriggerProtocolsFromScanDataElectrophysiology, QtCore.Qt.QueuedConnection],
                [self.actionDetect_triggers.triggered,                  self.slot_detectTriggers,               QtCore.Qt.QueuedConnection],
                [self.actionRefresh.triggered,                          self.slot_refreshAllDisplays,           QtCore.Qt.QueuedConnection],
                [self.actionRemove_all_protocols.triggered,             self.slot_removeAllProtocols,           QtCore.Qt.QueuedConnection],
                [self.actionExport_analysis_options_to_file.triggered,  self.slot_exportScanDataOptions,          QtCore.Qt.QueuedConnection],
                [self.actionLoad_options_file.triggered,                self.slot_loadOptionsFile,              QtCore.Qt.QueuedConnection],
                [self.actionConcatenate.triggered,                      self.slot_concatenateLSData,            QtCore.Qt.QueuedConnection],
                [self.actionAppend_LSData.triggered,                    self.slot_appendLSData,                 QtCore.Qt.QueuedConnection],
                [self.actionOpaque_cursor_labels.triggered,             self.slot_toggle_opaque_cursor_labels,  QtCore.Qt.QueuedConnection],
                [self.actionCollate_reports.triggered,                  self.slot_collate_reports,              QtCore.Qt.QueuedConnection],
                [self.actionBatch_extract_and_write.triggered,          self.slot_batch_extract_reports,        QtCore.Qt.QueuedConnection],
                [self.actionImport_Data_wide_Descriptors.triggered,     self.slot_import_data_wide_descriptors, QtCore.Qt.QueuedConnection]
            ]
        
        # self._common_data_fields_gui_signal_slots_ = [
        #         [self.scanDataNameLineEdit.editingFinished,             self.slot_setDataName,              QtCore.Qt.QueuedConnection],
        #         [self.sourceIDLineEdit.editingFinished,                 self.slot_gui_changed_source_ID,    QtCore.Qt.QueuedConnection],
        #         [self.cellLineEdit.editingFinished,                     self.slot_gui_changed_cell_name,    QtCore.Qt.QueuedConnection],
        #         [self.fieldLineEdit.editingFinished,                    self.slot_gui_changed_field_name,   QtCore.Qt.QueuedConnection],
        #         [self.genotypeComboBox.currentTextChanged[str],         self.slot_gui_changed_genotype,     QtCore.Qt.QueuedConnection],
        #         [self.sexComboBox.currentIndexChanged[str],             self.slot_gui_changed_sex,       QtCore.Qt.QueuedConnection],
        #         [self.ageLineEdit.editingFinished,                      self.slot_gui_age_changed,          QtCore.Qt.QueuedConnection]
        #     ]
        
        self._base_scipyen_data_gui_signal_slots_ = [
            [self.baseScipyenDataWidget.sig_valueChanged, self.slot_baseScipyenDataChanged, QtCore.Qt.QueuedConnection],
            ]
        
        # NOTE: 2022-01-16 11:45:41
        # signal from client ScipyenFrameViewer frame navigator widgets carry
        # the viewer's data frame index (which may or may NOT be the same as 
        # the master frame index, depending on ScanData framesMap)
        # therefore self.slot_setFrameNumber should determine this;
        # however, below, the connection is for signals emitted by LSCaTWindow's
        # own navigation widgets.
        self._navigation_gui_signal_slots_ = [
                [self.frameQSlider.valueChanged[int],    self.slot_setFrameNumber, QtCore.Qt.QueuedConnection],
                [self.framesQSpinBox.valueChanged[int],  self.slot_setFrameNumber, QtCore.Qt.QueuedConnection]
            ]
        
        self._scene_gui_signal_slots_ = [
                [self.sceneDisplayChannelComboBox.currentIndexChanged[int], self.slot_sceneDisplayChannelChanged,   QtCore.Qt.QueuedConnection],
                [self.showScanlineCheckBox.stateChanged[int],               self.slot_showScanlineProfiles,         QtCore.Qt.QueuedConnection]
            ]
        
        self._frames_gui_signal_slots_ = [
                [self.protocolSelectionComboBox.currentIndexChanged[int],   self.slot_displayFramesWithProtocol,    QtCore.Qt.QueuedConnection],
                [self.scanDisplayChannelCombobox.currentIndexChanged[int],  self.slot_scanDisplayChannelChanged,    QtCore.Qt.QueuedConnection],
                [self.removeCurrentFrameBtn.clicked,                        self.slot_removeCurrentScanDataFrame,   QtCore.Qt.QueuedConnection],
                [self.removeFramesBtn.clicked,                              self.slot_removeScanDataFrames,         QtCore.Qt.QueuedConnection]
            ]
        
        self._analysis_unit_gui_widgets_ = [
            self.selectCursorSpinBox, self.cursorXposDoubleSpinBox, self.cursorYposDoubleSpinBox,
            self.cursorXwindow, self.cursorYwindow, self.unitTypeComboBox, 
            self.analysisUnitNameLineEdit, self.defineAnalysisUnitCheckBox, self.descriptorsEditorBtn, 
            self.extractCurrentUnitButton]
            
        self._analysis_unit_gui_signal_slots_ = [
                [self.selectCursorSpinBox.valueChanged[int],        self.slot_gui_spinbox_select_cursor_by_index],
                [self.cursorXposDoubleSpinBox.valueChanged[float],  self.slot_gui_changed_cursor_x_pos],
                [self.cursorYposDoubleSpinBox.valueChanged[float],  self.slot_gui_changed_cursor_y_pos],
                [self.cursorXwindow.valueChanged[float],            self.slot_gui_changed_cursor_xwindow],
                [self.cursorYwindow.valueChanged[float],            self.slot_gui_changed_cursor_ywindow],
                [self.unitTypeComboBox.currentIndexChanged[str],    self.slot_gui_changed_unit_type_string],
                [self.analysisUnitNameLineEdit.editingFinished,     self.slot_gui_changed_analysis_unit_name],
                [self.defineAnalysisUnitCheckBox.stateChanged[int], self.slot_change_analysis_unit_state],
                [self.descriptorsEditorBtn.clicked,                 self.slot_gui_edit_analysis_unit_descriptors],
                [self.extractCurrentUnitButton.clicked,             self.slot_exportCurrentAnalysisUnit],
                [self.extractUnitsButton.clicked,                   self.slot_exportAnalysisUnits,                      QtCore.Qt.QueuedConnection],
            ]
        
        self._protocol_gui_signal_slots_ = [
                [self.protocolTableWidget.itemChanged[QtWidgets.QTableWidgetItem],  self.slot_protocolTableEdited, QtCore.Qt.QueuedConnection],
                [self.addProtocolAction.triggered,                                  self.slot_addProtocol, QtCore.Qt.QueuedConnection],
                [self.removeProtocolAction.triggered,                               self.slot_removeProtocol, QtCore.Qt.QueuedConnection]
            ]
        
        self._epscat_channels_calibration_gui_signal_slots_ = [
                [self.indicatorChannelComboBox.currentIndexChanged[int], self.slot_epscatIndicatorChannelChanged,   QtCore.Qt.QueuedConnection],
                [self.referenceChannelComboBox.currentIndexChanged[int], self.slot_epscatReferenceChannelChanged,   QtCore.Qt.QueuedConnection],
                [self.ind2refBleedDoubleSpinBox.valueChanged[float],     self.slot_epscat_bleed_ind_ref_changed,    QtCore.Qt.QueuedConnection],
                [self.ref2indBleedDoubleSpinBox.valueChanged[float],     self.slot_epscat_bleed_ref_ind_changed,    QtCore.Qt.QueuedConnection],
                [self.indicatorNameLineEdit.textEdited[str],             self.slot_indicatorNameChanged,            QtCore.Qt.QueuedConnection],
                [self.indicatorKdDoubleSpinBox.valueChanged[float],      self.slot_indicatorKdChanged,              QtCore.Qt.QueuedConnection],
                [self.indicatorFminDoubleSpinBox.valueChanged[float],    self.slot_indicatorFminChanged,            QtCore.Qt.QueuedConnection],
                [self.indicatorFmaxDoubleSpinBox.valueChanged[float],    self.slot_indicatorFmaxChanged,            QtCore.Qt.QueuedConnection]
            ]
        
        self._epscat_detection_gui_signal_slots_ = [
                [self.fs_DiscriminantDoubleSpinBox.valueChanged[float],             self.slot_fsDiscriminantChanged,                QtCore.Qt.QueuedConnection],
                [self.minR2SpinBox.valueChanged[float],                             self.slot_minimumR2Changed,                     QtCore.Qt.QueuedConnection],
                [self.useIntervalsRadioButton.toggled[bool],                        self.slot_discriminationWindowChoiceChanged,    QtCore.Qt.QueuedConnection],
                [self.useTriggersRadioButton.toggled[bool],                         self.slot_discriminationWindowChoiceChanged,    QtCore.Qt.QueuedConnection],
                [self.useCursorsForDiscriminationRadioButton.toggled[bool],         self.slot_discriminationWindowChoiceChanged,    QtCore.Qt.QueuedConnection],
                [self.discriminate2DCheckBox.stateChanged[int],                     self.slot_discrimination2DChanged,              QtCore.Qt.QueuedConnection],
                [self.firstTriggerOnlyCheckBox.stateChanged[int],                   self.slot_useFirstDiscriminationWindowChanged,  QtCore.Qt.QueuedConnection],
                [self.baseDiscriminationWindowDoubleSpinBox.valueChanged[float],    self.slot_setBaseDiscriminationWindow,          QtCore.Qt.QueuedConnection],
                [self.peakDiscriminationWindowDoubleSpinBox.valueChanged[float],    self.slot_setPeakDiscriminationWindow,          QtCore.Qt.QueuedConnection],
                [self.doFitCheckBox.stateChanged[int],                              self.slot_toggleEPSCaTFit,                      QtCore.Qt.QueuedConnection]
            ]
        
        self._epscat_intervals_gui_signal_slots_ = [
                [self.epscatDarkCurrentBeginDoubleSpinBox.valueChanged[float],  self.slot_epscatDarkCurrentBeginChanged,    QtCore.Qt.QueuedConnection],
                [self.epscatDarkCurrentEndDoubleSpinBox.valueChanged[float],    self.slot_epscatDarkCurrentEndChanged,      QtCore.Qt.QueuedConnection],
                [self.epscatF0BeginDoubleSpinBox.valueChanged[float],           self.slot_epscatF0BeginChanged,             QtCore.Qt.QueuedConnection],
                [self.epscatF0EndDoubleSpinBox.valueChanged[float],             self.slot_epscatF0EndChanged,               QtCore.Qt.QueuedConnection],
                [self.epscatFitBeginDoubleSpinBox.valueChanged[float],          self.slot_epscatFitBeginChanged,            QtCore.Qt.QueuedConnection],
                [self.epscatFitEndDoubleSpinBox.valueChanged[float],            self.slot_epscatFitEndChanged,              QtCore.Qt.QueuedConnection],
                [self.epscatIntegralBeginDoubleSpinBox.valueChanged[float],     self.slot_epscatIntegralBeginChanged,       QtCore.Qt.QueuedConnection],
                [self.epscatIntegralEndDoubleSpinBox.valueChanged[float],       self.slot_epscatIntegralEndChanged,         QtCore.Qt.QueuedConnection]
            ]
        
        self._epscat_parameters_table_gui_signal_slots_ = [
                [self.epscatComponentsTableWidget.itemChanged[QtWidgets.QTableWidgetItem],  self.slot_epscatParameterChanged,   QtCore.Qt.QueuedConnection],
                [self.addEPSCaTAction.triggered,                                            self.slot_addEPSCaTComponent,       QtCore.Qt.QueuedConnection],
                [self.removeEPSCaTAction.triggered,                                         self.slot_removeEPSCaTComponent,    QtCore.Qt.QueuedConnection]
            ]
        
        self._process_buttons_gui_signal_slots_ = [
                [self.processDataBtn.clicked,   self.slot_processData],
                [self.processSceneBtn.clicked,  self.slot_processScene],
                [self.processScanBtn.clicked,   self.slot_processScans]
            ]
        
        self._analyse_buttons_gui_slots_ = [
                [self.analyseDataBtn.clicked,               self.slot_analyseData],
                [self.analyseRoiBtn.clicked,                self.slot_analyseCurrentLandmarkInCurrentFrame],
                [self.analyseFrameBtn.clicked,              self.slot_analyseCurrentFrame],
                [self.analyseRoiInSpecifedFrames.clicked,   self.slot_analyseCurrentLandmarkInFrames],
                [self.saveReportBtn.clicked,                self.slot_reportLSCaTResults, QtCore.Qt.QueuedConnection],
                [self.viewReportBtn.clicked,                self.slot_showReportWindow, QtCore.Qt.QueuedConnection]
            ]
        
        # NOTE: 2018-05-21 15:25:31
        # this function only does additional set up for gui objects
        # the slots are connected by call to _connect_slots_ at the end
        # except for the filters GUI objects, which are connected here
        
        # NOTE: 2018-05-21 15:27:28
        # also, signal-slot connections related to various windows are dealt with
        # upon first time (new) data is displayed
        
        # NOTE: 2018-04-06 10:27:32
        # except for the Filters tab, all other signal-slot connections
        # are made at the end of this function
        #self.showScanRawDataCheckBox.setChecked(QtCore.Qt.Unchecked)
        
        ####
        # BEGIN Units toolbar actions
        self.unitsToolbar.actionTriggered[QtWidgets.QAction].connect(self.slot_unitsToolbarAction)
        self.fileToolbar.actionTriggered[QtWidgets.QAction].connect(self.slot_fileToolbarAction)
        # END Units toolbar actions
        ####
        
        #### 
        # BEGIN Menu actions:
        #self.showScanRawDataCheckBox.stateChanged[int].connect(self.slot_displayChoiceChanged)
        
        # END Menu actions
        ####
        # # BEGIN common widgets
        # self.scanDataNameLineEdit.setClearButtonEnabled(True)
        # self.scanDataNameLineEdit.undoAvailable = True
        # self.scanDataNameLineEdit.redoAvailable = True
        #self.scanDataNameLineEdit.setValidator(strutils.QNameValidator())
        
        self.framesQSpinBox.setKeyboardTracking(False)
        self.framesQSpinBox.setMinimum(0)
        self.framesQSpinBox.setMaximum(0)
        self.framesQSpinBox.valueChanged.connect(self.slot_setFrameNumber)
        self._frames_spinner_ = self.framesQSpinBox
        
        
        self.frameQSlider.setMinimum(0)
        self.frameQSlider.setMaximum(0)
        self.frameQSlider.valueChanged.connect(self.slot_setFrameNumber)
        self._frames_slider_ = self.frameQSlider
        
        
        self.tabWidget.setCurrentIndex(0) # TODO make persistent configuration
        # END common widgets
        
        # ###
        # BEGIN Data tab
        
        # ### scene groupbox
        self.showScanlineCheckBox.setCheckState(QtCore.Qt.Checked)
        self.sceneDisplayChannelComboBox.addItem("All channels")
        self.sceneDisplayChannelComboBox.setCurrentIndex(0)
        
        # ### frames groupbox
        self.protocolSelectionComboBox.addItem("All")
        self.protocolSelectionComboBox.setCurrentIndex(0)
        
        self.scanDisplayChannelCombobox.addItem("All channels")
        self.scanDisplayChannelCombobox.setCurrentIndex(0)
        
        # ### analysis units groupbox
        self.selectCursorSpinBox.setSpecialValueText("none")
        self.selectCursorSpinBox.setRange(-1,0)
        self.analysisUnitNameLineEdit.setClearButtonEnabled(True)
        self.analysisUnitNameLineEdit.redoAvailable = True
        self.analysisUnitNameLineEdit.undoAvailable = True
        #self.analysisUnitNameLineEdit.setValidator(strutils.QRNameValidator())
         
        # NOTE: 2019-01-15 11:40:35
        # implements source ID field in ScanData
        # where by source one means cell culture, animal, patient
        # self.sourceIDLineEdit.setClearButtonEnabled(True)
        # self.sourceIDLineEdit.redoAvailable = True
        # self.sourceIDLineEdit.undoAvailable = True
        
         
        # self.cellLineEdit.setClearButtonEnabled(True)
        # self.cellLineEdit.redoAvailable = True
        # self.cellLineEdit.undoAvailable = True
        #self.cellLineEdit.setValidator(strutils.QRNameValidator())
        
        # self.fieldLineEdit.setClearButtonEnabled(True)
        # self.fieldLineEdit.redoAvailable = True
        # self.fieldLineEdit.undoAvailable = True
        #self.fieldLineEdit.setValidator(strutils.QRNameValidator())
        
        unit_types = sorted([v for v in UnitTypes.values()])
        unit_types.insert(0, "unknown")
        
        self.unitTypeComboBox.setEditable(True)
        self.unitTypeComboBox.lineEdit().setClearButtonEnabled(True)
        self.unitTypeComboBox.lineEdit().redoAvailable = True
        self.unitTypeComboBox.lineEdit().undoAvailable = True
        self.unitTypeComboBox.addItems(unit_types)
        self.unitTypeComboBox.setCurrentIndex(0)
        
        genotypes = ["NA", "wt", "het", "hom"]
        
        # self.genotypeComboBox.setEditable(True)
        # self.genotypeComboBox.lineEdit().setClearButtonEnabled(True)
        # self.genotypeComboBox.lineEdit().redoAvailable = True
        # self.genotypeComboBox.lineEdit().undoAvailable = True
        # self.genotypeComboBox.addItems(genotypes)
        # self.genotypeComboBox.setCurrentIndex(0)
        
        sex = ["NA", "F", "M"]
        
#         self.sexComboBox.setEditable(False)
#         self.sexComboBox.addItems(sex)
#         self.sexComboBox.setCurrentIndex(0)
#         
#         self.ageLineEdit.setText("NA")
#         self.ageLineEdit.setClearButtonEnabled(True)
#         self.ageLineEdit.redoAvailable = True
#         self.ageLineEdit.undoAvailable = True
        
        epscatComponentSuccessSelect = ["any", "all", "index"]
        self.selectFailureTestComponentComboBox.addItems(epscatComponentSuccessSelect)
        self.testEPSCaTComponentInputLineEdit.setClearButtonEnabled(True)
        self.testEPSCaTComponentInputLineEdit.redoAvailable = True
        self.testEPSCaTComponentInputLineEdit.undoAvailable = True
        
        
        # ### ### signal-slot connections left

        self.defineAnalysisUnitCheckBox.setTristate(False)
        
        # ### ### signal-slot connections right
        self.selectCursorSpinBox.setMinimum(-1)
        self.selectCursorSpinBox.setValue(-1)
        
        #self.reportWindow = tv.TextViewer(self._report_document_, win_title="Analysis Result", parent=self)
        #self.reportWindow = te.TableEditor(data=self._report_dataframe_, win_title="Analysis Result", parent=self)
        self.reportWindow = te.TableEditor(win_title="Analysis Result", parent=self)
        self.reportWindow.signal_window_will_close.connect(self.slot_report_window_closing)
        self.reportWindow.setVisible(False)
        
        # END Data tab
        # ###
        
        # ###
        # BEGIN Protocols tab
        #self.protocolTableWidget.horizontalHeader()..setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.protocolTableWidget.horizontalHeader().setSectionsMovable(False)
        self.protocolTableWidget.verticalHeader().setSectionsMovable(False)
        self.protocolTableWidget.setAlternatingRowColors(True)
        self.protocolTableWidget.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.protocolTableWidget.addAction(self.addProtocolAction)
        self.protocolTableWidget.addAction(self.removeProtocolAction)
        # END Protocols tab
        # ###
        
        # ###
        # BEGIN Filters tab
        self.blankUncagingArtifactBtn.clicked.connect(self.slot_removeUncagingArtifact)
        self.scanLineIterpOrderSpinBox.setValue(self.default_scanline_spline_order)
        self.scanLineIterpOrderSpinBox.valueChanged[int].connect(self.slot_splineInterpolatorOrderChanged, type = QtCore.Qt.QueuedConnection)
        # TODO: a dynamic way to generate filter config dialogs -- perhaps use vigra's 
        # QuickDialog subclasses and add them to (as) individual pages in the stacked widget?
        # TODO implement this using a plugin-like functionality, to also generte a UI dialog for
        # options & parameters
        
        # Scene filters group box
        self.sceneFiltersComboBox.addItems(["None", "Purelet", "Gaussian", "Binomial"])
        self.sceneFiltersComboBox.setCurrentIndex(1)
        self.sceneFiltersComboBox.currentIndexChanged[int].connect(self.slot_filterPageSelectionChanged, type = QtCore.Qt.QueuedConnection)
        
        self.sceneFiltersConfigStackedWidget.setCurrentIndex(0)
        
        #   purelet filter page
        # scene reference channel
        filterGUIFields =   [self.pureletAlphaSceneRefDoubleSpinBox, 
                             self.pureletBetaSceneRefDoubleSpinBox, 
                             self.pureletJSceneRefSpinBox,
                             self.pureletSigmaSceneRefDoubleSpinBox, 
                             self.pureletTSceneRefSpinBox]
        
        filterParams = self.defaultPureletFilterOptions.scene.ref.sortedkeys()
        
        filterParams.sort()
        #print("self.defaultPureletFilterOptions.scene.ref", filterParams)
        
        #print("set up purelet scene ref")
        for f, member in zip(filterGUIFields, filterParams):
            #print("member",member, "field", f,  self.defaultPureletFilterOptions.scene.ref[member])
            f.setValue(self.defaultPureletFilterOptions.scene.ref[member])
            if isinstance(f, QtWidgets.QDoubleSpinBox):
                f.valueChanged[float].connect(self.slot_filterParamChanged, type = QtCore.Qt.QueuedConnection)
            
            else:
                f.valueChanged[int].connect(self.slot_filterParamChanged, type = QtCore.Qt.QueuedConnection)
        
        # scene indicator channel
        filterGUIFields =   [self.pureletAlphaSceneIndDoubleSpinBox,
                             self.pureletBetaSceneIndDoubleSpinBox,
                             self.pureletJSceneIndSpinBox,
                             self.pureletSigmaSceneIndDoubleSpinBox,
                             self.pureletTSceneIndSpinBox]
        
        filterParams = self.defaultPureletFilterOptions.scene.ind.sortedkeys()
        
        filterParams.sort()
        
        for f, member in zip(filterGUIFields, filterParams):
            f.setValue(self.defaultPureletFilterOptions.scene.ind[member])
            if isinstance(f, QtWidgets.QDoubleSpinBox):
                f.valueChanged[float].connect(self.slot_filterParamChanged, type = QtCore.Qt.QueuedConnection)
            
            else:
                f.valueChanged[int].connect(self.slot_filterParamChanged, type = QtCore.Qt.QueuedConnection)
        
        # scans reference channel
        self.scanFiltersComboBox.addItems(["None", "Purelet", "Gaussian", "Binomial"])
        self.scanFiltersComboBox.setCurrentIndex(1)
        self.scanFiltersComboBox.currentIndexChanged[int].connect(self.slot_filterPageSelectionChanged)
        
        self.scanFiltersConfigStackedWidget.setCurrentIndex(0)
        
        
        filterGUIFields =   [self.pureletAlphaScansRefDoubleSpinBox, 
                             self.pureletBetaScansRefDoubleSpinBox, 
                             self.pureletJScansRefSpinBox,
                             self.pureletSigmaScansRefDoubleSpinBox, 
                             self.pureletTScansRefSpinBox]
        
        filterParams = self.defaultPureletFilterOptions.scans.ref.sortedkeys()
        
        filterParams.sort()
        
        for f, member in zip(filterGUIFields, filterParams):
            f.setValue(self.defaultPureletFilterOptions.scans.ref[member])
            if isinstance(f, QtWidgets.QDoubleSpinBox):
                f.valueChanged[float].connect(self.slot_filterParamChanged, type = QtCore.Qt.QueuedConnection)
            
            else:
                f.valueChanged[int].connect(self.slot_filterParamChanged, type = QtCore.Qt.QueuedConnection)
        
        # scans indicator channel
        filterGUIFields =   [self.pureletAlphaScansIndDoubleSpinBox, 
                             self.pureletBetaScansIndDoubleSpinBox, 
                             self.pureletJScansIndSpinBox,
                             self.pureletSigmaScansIndDoubleSpinBox, 
                             self.pureletTScansIndSpinBox]
        
        filterParams = self.defaultPureletFilterOptions.scans.ind.sortedkeys()
        
        filterParams.sort()
        
        for f, member in zip(filterGUIFields, filterParams):
            f.setValue(self.defaultPureletFilterOptions.scans.ind[member])
            if isinstance(f, QtWidgets.QDoubleSpinBox):
                f.valueChanged[float].connect(self.slot_filterParamChanged)
            
            else:
                f.valueChanged[int].connect(self.slot_filterParamChanged)
                
        # gaussian filter page
        self.previewGaussianSceneRefBtn.clicked.connect(self.slot_previewFilter)
        self.previewGaussianSceneIndBtn.clicked.connect(self.slot_previewFilter)
        self.previewGaussianScansRefBtn.clicked.connect(self.slot_previewFilter)
        self.previewGaussianScansIndBtn.clicked.connect(self.slot_previewFilter)

        # gaussian filter scene reference channel
        
        filterGUIFields = [self.gaussianSigmaSceneRefDoubleSpinBox,
                           self.gaussianSizeSceneRefSpinBox]
        
        filterParams = self.defaultGaussianFilterOptions.scene.ref.sortedkeys()
        
        filterParams.sort()
        
        for f, member in zip(filterGUIFields, filterParams):
            f.setValue(self.defaultGaussianFilterOptions.scene.ref[member])
            if isinstance(f, QtWidgets.QDoubleSpinBox):
                f.valueChanged[float].connect(self.slot_filterParamChanged, type = QtCore.Qt.QueuedConnection)
            
            else:
                f.valueChanged[int].connect(self.slot_filterParamChanged, type = QtCore.Qt.QueuedConnection)
                
        # gaussian filter scene indicator channel
        
        filterGUIFields = [self.gaussianSigmaSceneIndDoubleSpinBox,
                           self.gaussianSizeSceneIndSpinBox]
        
        filterParams = self.defaultGaussianFilterOptions.scene.ind.sortedkeys()
        
        filterParams.sort()
        
        for f, member in zip(filterGUIFields, filterParams):
            f.setValue(self.defaultGaussianFilterOptions.scene.ind[member])
            if isinstance(f, QtWidgets.QDoubleSpinBox):
                f.valueChanged[float].connect(self.slot_filterParamChanged)
            
            else:
                f.valueChanged[int].connect(self.slot_filterParamChanged)
                
        # gaussian filter scans reference channel
        filterGUIFields = [self.gaussianSigmaScansRefDoubleSpinBox,
                           self.gaussianSizeScansRefSpinBox]
        
        filterParams = self.defaultGaussianFilterOptions.scans.ref.sortedkeys()
        
        filterParams.sort()
        
        for f, member in zip(filterGUIFields, filterParams):
            f.setValue(self.defaultGaussianFilterOptions.scans.ref[member])
            if isinstance(f, QtWidgets.QDoubleSpinBox):
                f.valueChanged[float].connect(self.slot_filterParamChanged, type = QtCore.Qt.QueuedConnection)
            
            else:
                f.valueChanged[int].connect(self.slot_filterParamChanged, type = QtCore.Qt.QueuedConnection)
                
        # gaussian filter scans indicator channel
        filterGUIFields = [self.gaussianSigmaScansIndDoubleSpinBox,
                           self.gaussianSizeScansIndSpinBox]
        
        filterParams = self.defaultGaussianFilterOptions.scans.ind.sortedkeys()
        
        filterParams.sort()
        
        for f, member in zip(filterGUIFields, filterParams):
            f.setValue(self.defaultGaussianFilterOptions.scans.ind[member])
            if isinstance(f, QtWidgets.QDoubleSpinBox):
                f.valueChanged[float].connect(self.slot_filterParamChanged, type = QtCore.Qt.QueuedConnection)
            
            else:
                f.valueChanged[int].connect(self.slot_filterParamChanged, type = QtCore.Qt.QueuedConnection)
                
        # binomial filter page
        self.previewBinomialSceneRefBtn.clicked.connect(self.slot_previewFilter)
        self.previewBinomialSceneIndBtn.clicked.connect(self.slot_previewFilter)
        self.previewBinomialScansRefBtn.clicked.connect(self.slot_previewFilter)
        self.previewBinomialScansIndBtn.clicked.connect(self.slot_previewFilter)
        
        # binomial filter scene reference
        self.binomialOrderSceneRefSpinBox.setValue(self.defaultBinomialFilterOptions.scene.ref.radius)
        self.binomialOrderSceneRefSpinBox.valueChanged[int].connect(self.slot_filterParamChanged, type = QtCore.Qt.QueuedConnection)
        
        # binomial filter scene indicator
        self.binomialOrderSceneIndSpinBox.setValue(self.defaultBinomialFilterOptions.scene.ind.radius)
        self.binomialOrderSceneIndSpinBox.valueChanged[int].connect(self.slot_filterParamChanged, type = QtCore.Qt.QueuedConnection)
        
        # binomial filter scans reference
        self.binomialOrderScansRefSpinBox.setValue(self.defaultBinomialFilterOptions.scans.ref.radius)
        self.binomialOrderScansRefSpinBox.valueChanged[int].connect(self.slot_filterParamChanged, type = QtCore.Qt.QueuedConnection)
       
        # binomial filter scans indicator
        self.binomialOrderScansIndSpinBox.setValue(self.defaultBinomialFilterOptions.scans.ind.radius)
        self.binomialOrderScansIndSpinBox.valueChanged[int].connect(self.slot_filterParamChanged, type = QtCore.Qt.QueuedConnection)
        
        # END Filters tab
        # ###
        
        # ###
        # BEGIN epscat tab
        
        # Channels and calibration groupbox
        self.indicatorKdDoubleSpinBox.setSpecialValueText("nan")
        self.indicatorFminDoubleSpinBox.setSpecialValueText("nan")
        self.indicatorFmaxDoubleSpinBox.setSpecialValueText("nan")
        
        # Detection groupbox
        
        # Intervals groupbox
        
        # parameters table
        # NOTE: 2017-12-24 23:24:22
        # see NOTE: 2017-12-24 10:06:51 in _update_ui_fields_() about the 
        # contents of self.epscatComponentsTableWidget
        
        self.epscatComponentsTableWidget.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        #self.epscatComponentsTableWidget.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        
        self.epscatComponentsTableWidget.horizontalHeader().setSectionsMovable(False)
        self.epscatComponentsTableWidget.verticalHeader().setSectionsMovable(False)
        
        self.epscatComponentsTableWidget.setAlternatingRowColors(True)
        
        self.epscatComponentsTableWidget.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        
        self.epscatComponentsTableWidget.addAction(self.addEPSCaTAction)
        self.epscatComponentsTableWidget.addAction(self.removeEPSCaTAction)

        
        # END epscat tab
        
        # ###
        # BEGIN action buttons
        
        # process
        
        # analyse
        
        # output
        
        # END action buttons
        # ###
            
        self._connect_slots_()
        
    @safeWrapper
    def _connect_slots_(self):
        self._connect_gui_slots_(self._menu_actions_gui_slots_)
        # self._connect_gui_slots_(self._common_data_fields_gui_signal_slots_)
        self._connect_gui_slots_(self._base_scipyen_data_gui_signal_slots_)
        self._connect_gui_slots_(self._navigation_gui_signal_slots_)
        self._connect_gui_slots_(self._scene_gui_signal_slots_)
        self._connect_gui_slots_(self._frames_gui_signal_slots_)
        self._connect_gui_slots_(self._analysis_unit_gui_signal_slots_)
        self._connect_gui_slots_(self._protocol_gui_signal_slots_)
        self._connect_gui_slots_(self._epscat_channels_calibration_gui_signal_slots_)
        self._connect_gui_slots_(self._epscat_detection_gui_signal_slots_)
        self._connect_gui_slots_(self._epscat_intervals_gui_signal_slots_)
        self._connect_gui_slots_(self._epscat_parameters_table_gui_signal_slots_)
        self._connect_gui_slots_(self._process_buttons_gui_signal_slots_)
        self._connect_gui_slots_(self._analyse_buttons_gui_slots_)
        
    @safeWrapper
    def filterData(self, scene=True, scans=True):#, frames = None):
        """ Filters data with functions selected in the "Filters" tab.
        
        Wraps processData() function in separate pictgui.ProgressWorkerRunnable threads,
        one for the scans and one for the scene ⟹ there will be two progressbars
        showing.
        
        Data filtering function is associated with the individual ScanData object
        because it allows the processing to be tractable to the particular
        ScanData instance (the processing function & parameters are included in 
        the "analysisOptions "property of the ScanData object)
        
        NOTE: 2017-12-20 07:53:59 The ability to process selected frames has been
        dropped for two reasons:
        
        1) selectively applying filters to individual frames leads to the possibility
        of those frames being filtered with different filter function and/or parameters
        from the rest of the data subset, which may lead to biased data analysis.
        
        2) it would complicate the code unnecessarily: 
        
        2.1) filter functions and parameters  would have to be stored for each 
        individual frame so that the filtered data and analysis result can be 
        reproduced from the same original raw data

        2.2) would open the possibility of concatenating scandata objects with
        processed and non-processed data frames, further complicating the code to 
        manage this.
        
        TODO: 2017-12-07 00:03:04
        Implement progress dialog, ideally cancelable, perhaps even non-modal
        (separate thread)
        
        DONE, but still TODO implement Abort processing
        
        TODO FIXME 2021-03-09 22:02:59
        Allow filtering even if no Reference or Indicator channels 
        have been defined. This requires a re-design of the whole paradigm of
        defining filters (with respect to what is filterings and how these are 
        stored in the configuration)
        """
        if not isinstance(self._data_, ScanData):
            return
        
        if len(self._data_.analysisOptions) == 0:
            warnings.warn("No analysis options have been set up. Cannot continue")
            return
        
        if "Channels" not in self._data_.analysisOptions or len(self._data_.analysisOptions["Channels"]) == 0:
            warnings.warn("No analysis channels have been specified in the current analysis options. Cannot continue")
            return
            
        if "Reference" not in self._data_.analysisOptions["Channels"] or \
            self._data_.analysisOptions["Channels"]["Reference"] is None or \
                len(self._data_.analysisOptions["Channels"]["Reference"]) == 0:
                warnings.warn("No reference channel is mentioned in the current analysis options")
                return
                
        if "Indicator" not in self._data_.analysisOptions["Channels"] or \
            self._data_.analysisOptions["Channels"]["Indicator"] is None or \
                len(self._data_.analysisOptions["Channels"]["Indicator"]) == 0:
                warnings.warn("No indicator channel is mentioned in the current analysis options")
                return
            
        if len(self._data_.scene) > 0:
            if self._data_.analysisOptions["Channels"]["Reference"] not in self._data_.sceneChannelNames:
                warnings.warn("Reference channel %s not found among scene channels" % self._data_.analysisOptions["Channels"]["Reference"])
                return
            
            if self._data_.analysisOptions["Channels"]["Reference"] not in self._scene_filters_:
                warnings.warn("No filter function has been configured for scene reference channel %s" \
                    % self._data_.analysisOptions["Channels"]["Reference"])
                return
            
            if self._data_.analysisOptions["Channels"]["Indicator"] not in self._data_.sceneChannelNames:
                warnings.warn("Indicator channel %s not found among scene channels" % self._data_.analysisOptions["Channels"]["Indicator"])
                return
            
            if self._data_.analysisOptions["Channels"]["Indicator"] not in self._scene_filters_:
                warnings.warn("No filter function has been configured for scene indicator channel %s" \
                    % self._data_.analysisOptions["Channels"]["Indicator"])
                return
            
        if len(self._data_.scans) > 0:
            if self._data_.analysisOptions["Channels"]["Reference"] not in self._data_.scansChannelNames:
                warnings.warn("Reference channel %s not found among scans channels" % self._data_.analysisOptions["Channels"]["Reference"])
                return
            
            if self._data_.analysisOptions["Channels"]["Reference"] not in self._scans_filters_:
                warnings.warn("No filter function has been configured for scans reference channel %s" \
                    % self._data_.analysisOptions["Channels"]["Reference"])
                return
            
            if self._data_.analysisOptions["Channels"]["Indicator"] not in self._data_.scansChannelNames:
                warnings.warn("Indicator channel %s not found among scans channels" % self._data_.analysisOptions["Channels"]["Indicator"])
                return
            
            if self._data_.analysisOptions["Channels"]["Indicator"] not in self._scans_filters_:
                warnings.warn("No filter function has been configured for scans indicator channel %s" \
                    % self._data_.analysisOptions["Channels"]["Indicator"])
                return
            
        #### BEGIN unthreaded execution - for debugging
        # make sure to comment out the other one
        #if scene and len(self._data_.scene) > 0:
            #self._scene_processing_idle_ = True
            #f_scene = self.processData(scene=True, channel = [self._data_.analysisOptions["Channels"]["Reference"], 
                                                              #self._data_.analysisOptions["Channels"]["Indicator"]])
            #for k in range(len(self._data_.scene)):
                #self._data_.scene[k] = f_scene[k]
                
            #self._display_scene_()
            ##for win in self.sceneviewers:
                ##win.displayFrame()
                
        #if scans and len(self._data_.scans) > 0:
            #f_scans = self.processData(scene=False, channel = [self._data_.analysisOptions["Channels"]["Reference"], 
                                                               #self._data_.analysisOptions["Channels"]["Indicator"]])
            
            #for k in range(len(self._data_.scans)):
                #self._data_.scans[k] = f_scans[k]
                
            #self._display_scans_()
                
            ##for win in self.scansviewers:
                ##win.displayFrame()
                
            #self.generateScanRegionProfiles()
            #self._display_scanline_profiles_()
            
        #self._data_.updateAxesCalibrations()
        
        #self._data_.modified=True
        #self._data_.processed = True
        #self.displayFrame()
        #self.statusBar().showMessage("Done!")
        
        #### END unthreaded execution
        
        #### BEGIN Threaded execution - this should be used by default;
        # make sure you comment out the unthreaded bit above
            
        #NOTE: 2019-10-12 14:58:30
        # for self._data_.scene and self._data_.scans:
        # sets up a worker thread which calls self.processData()
        if scene and len(self._data_.scene) > 0:
            self._scene_processing_idle_ = False
            
            pdlg = QtWidgets.QProgressDialog("De-noising scene data...", "Abort", 0, self._data_.sceneFrames, self)

            sceneWorker = pgui.ProgressWorkerRunnable(self.processData, pdlg,
                                      channel = [self._data_.analysisOptions["Channels"]["Reference"], 
                                                 self._data_.analysisOptions["Channels"]["Indicator"]],
                                      scene=True)
            
            sceneWorker.signals.signal_Finished.connect(pdlg.reset)
            #sceneWorker.signals.signal_Finished.connect(self.slot_sceneProcessingDone)
            sceneWorker.signals.signal_Result[object].connect(self.slot_sceneProcessingDone)
                
        else:
            self._scene_processing_idle_ = True
            sceneWorker = None
            
        if scans and len(self._data_.scans) > 0:
            self._scans_processing_idle_ = False
            
            pdlg = QtWidgets.QProgressDialog("De-noising scans data...", "Abort", 0, self._data_.scansFrames, self)
            
            scansWorker = pgui.ProgressWorkerRunnable(self.processData, pdlg,
                                      channel = [self._data_.analysisOptions["Channels"]["Reference"], 
                                                 self._data_.analysisOptions["Channels"]["Indicator"]],
                                      scene=False)
            
            scansWorker.signals.signal_Finished.connect(pdlg.reset)
            #scansWorker.signals.signal_Finished.connect(self.slot_scansProcessingDone)
            scansWorker.signals.signal_Result[object].connect(self.slot_scansProcessingDone)
            
        else:
            self._scans_processing_idle_ = True
            scansWorker = None
            
        if sceneWorker is not None:
            self.threadpool.start(sceneWorker)
            
        if scansWorker is not None:
            self.threadpool.start(scansWorker)
            
        #### END Threaded execution
            
    @safeWrapper
    @Slot(object)
    def slot_sceneProcessingDone(self, result):
        if self._data_ is None:
            print("slot_sceneProcessingDone no data")
            return
        self._scene_processing_idle_= True
        for k in range(len(result)):
            #print("scene[%d]" %k)
            self._data_.scene[k][:] = result[k]
            
        #self._data_.sceneChannelNames = result[1]
        
        for win in self.sceneviewers:
            win.displayFrame()
            
        self.slot_processingDone()
        
    @safeWrapper
    @Slot(object)
    def slot_scansProcessingDone(self, result):
        if self._data_ is None:
            print("slot_scansProcessingDone no data")
            return
        self._scans_processing_idle_ = True
        for k in range(len(result)):
            #print("scans[%d]" % k)
            self._data_.scans[k][:] = result[k]
        #self._data_.scansChannelNames = result[1]
        for win in self.scansviewers:
            win.displayFrame()
        self.slot_processingDone()
        
    @Slot()
    @safeWrapper
    def slot_processingDone(self):
        if self._scene_processing_idle_ and self._scans_processing_idle_:
            self.generateScanRegionProfiles()
            
            self._data_.updateAxesCalibrations()
            
            self._data_.modified=True
            self._data_.processed = True
            self.displayFrame()
            self.statusBar().showMessage("Done!")
            
    @Slot()
    def slot_cancelCurrentProcess(self):
        # TODO
        pass
        
    # ###
    # BEGIN Properties
    # ###
    
    @property
    def currentProtocols(self):
        prname = self.protocolSelectionComboBox.currentText()
        
        if prname.lower() == "all":
            self._current_protocols_ = self._data_.triggers
            
        elif prname.lower() == "select..." and len(self._current_protocols_) == 0:
            pnames = [p.name for p in self._data_.triggers]
            if len(pnames):
                ret = pgui.checkboxDialogPrompt(self, "Select protocols", pnames)
                
                selected = [pnames[k] for (k,v) in enumerate(ret) if v]
                
                if len(selected):
                    result = list()
                    for n in selected:
                        result.append([p for p in self._data_.triggers if p.name == n][0])
                        
                    self._current_protocols_ = result
                
                else:
                    self._current_protocols_ = []
        
        else:
            self._current_protocols_ = [p for p in self._data_.triggers if p.name == prname]
            
        return self._current_protocols_

    @property
    def data(self):
        return self._data_
    
    @property
    def currentFrame(self):
        return self._current_frame_index_
    
    @currentFrame.setter
    def currentFrame(self, value:int):
        """Sets the current frame number without emitting signals.
        Updates the currentFrame attribute of various graphics objects.
        Call this when changing frame from outside this window
        """
        if self._data_ is None:
            return
        
        if not isinstance(value, int):
            return
        
        if value < 0: # we don't do negative frame indices!
            return
        
        # _frame_selector_ indicates a subset of frames to be navigated through
        # e.g. only frames with the same trigger protocol
        # it can be None i.e. no frame subset is defined, or it can be a
        # sequence (tuple, list), slice, or range
        #
        # below we skip any action if value is NOT in the subset indicated by 
        # _frame_selector_
        if isinstance(self._frame_selector_, (tuple, list, range)):
            if value not in self._frame_selector_:
                return
            
        elif isinstance(self._frame_selector_, slice):
            #if value not in range(self._frame_selector_.indices(self._data_.scansFrames)):
            if value not in range(self._frame_selector_.indices(self._data_.nFrames)):
                return
            
        elif isinstance(self._frame_selector_, int):
            if value != self._frame_selector_:
                return
            
        if value >= self._data_.nFrames() or value < 0:
            return

        self._current_frame_index_ = value
        
        # NOTE: 2022-01-12 09:30:49
        # update currentFrame for PlanarGraphics
        # if isinstance(self._data_.scanRegion, pgui.PlanarGraphics):
        #     self._data_.scanRegion.currentFrame = self._current_frame_index_
        
        if isinstance(self._data_.scansRois, dict):
            for obj in self._data_.scansRois.values():
                obj.currentFrame = self._current_frame_index_
                obj.updateLinkedObjects()
                obj.updateFrontends()
            
        if isinstance(self._data_.scansCursors, dict):
            for obj in self._data_.scansCursors.values():
                obj.currentFrame = self._current_frame_index_
                obj.updateLinkedObjects()
                obj.updateFrontends()
            
        
        if isinstance(self._data_.sceneRois, dict):
            for obj in self._data_.sceneRois.values():
                obj.currentFrame = self._current_frame_index_
                obj.updateLinkedObjects()
                obj.updateFrontends()
                
        if isinstance(self._data_.sceneCursors, dict):
            for obj in self._data_.sceneCursors.values():
                obj.currentFrame = self._current_frame_index_
                obj.updateLinkedObjects()
                obj.updateFrontends()
            
        if isinstance(self._data_.scanRegion, pgui.Path) and len(self._data_.scanRegion):
            self._data_.scanRegion.currentFrame = self._current_frame_index_
            self._data_.scanRegion.updateLinkedObjects()
            self._data_.scanRegion.updateFrontends()
            
            self._current_frame_scan_region_[:] = self._data_.scanRegion.getState(self._current_frame_index_)
            
        # see NOTE: 2018-09-25 22:19:58
        # update the display frame for data components
        signalBlockers = [QtCore.QSignalBlocker(widget) for widget in \
            (self.frameQSlider, self.framesQSpinBox)]
        
        self.framesQSpinBox.setValue(int(self._current_frame_index_))
        self.frameQSlider.setValue(int(self._current_frame_index_))

        #self.displayFrame()
        
        
    # ###
    # END Properties
    # ###
        
    # ###
    # BEGIN PyQt slots
    # ###
    
    @Slot(float)
    @safeWrapper
    def slot_epscat_bleed_ind_ref_changed(self, value):
        if self._data_ is None or len(self._data_.analysisOptions) == 0:
            return
        
        if value > 1:
            value = 1
            
        if value < 0:
            value = 0
            
        self._data_.analysisOptions["Channels"]["Bleed_ind_ref"] = value
        
    
    @Slot(float)
    @safeWrapper
    def slot_epscat_bleed_ref_ind_changed(self, value):
        if self._data_ is None or len(self._data_.analysisOptions) == 0:
            return
        
        if value > 1:
            value = 1
            
        if value < 0:
            value = 0
            
        self._data_.analysisOptions["Channels"]["Bleed_ref_ind"] = value
        
    @Slot()
    @safeWrapper
    def slot_openScanDataPickleFile(self):
        import mimetypes, io
        #from systems import PrairieView
        
        #targetDir = self._scipyenWindow_.recentDirectories[0]
        targetDir = self._scipyenWindow_.currentDir
        
        if sys.platform == "win32":
            options = QtWidgets.QFileDialog.Option.DontUseNativeDialog
            kw = {"options":options}
        else:
            kw = {}

        pickleFileName, _ = QtWidgets.QFileDialog.getOpenFileName(self,
                                                                  caption="Open ScanData file",
                                                                  filter="Pickle Files (*.pkl)",
                                                                  directory=targetDir, **kw)
        
        if len(pickleFileName) == 0:
            return
        
        data = pio.loadPickleFile(pickleFileName)
        
        if not self._check_for_linescan_data_(data):
            QtWidgets.QMessageBox.critical(self, "Open ScanData file", "Chosen file does not contain a valid ScanData object")
            return
        
        _data_var_name_ = os.path.splitext(os.path.basename(pickleFileName))[0]
        
        self.setData(data, _data_var_name_)
        
        #self._parsedata_(data, _data_var_name_)
        

        
        self._scipyenWindow_.assignToWorkspace(_data_var_name_, data)
        
    @Slot()
    def slot_loadOptionsFile(self):
        import io
        if self._data_ is None:
            return
        
        targetDir = self._scipyenWindow_.currentDir

        if sys.platform == "win32":
            options = QtWidgets.QFileDialog.Option.DontUseNativeDialog
            kw = {"options":options}
        else:
            kw = {}

        epscatOptionsFileName, _ = QtWidgets.QFileDialog.getOpenFileName(self,
                                                                         caption="Open EPSCaT Options file", 
                                                                         filter="Pickle Files (*.pkl)",
                                                                         directory=targetDir, **kw)
        
        if len(epscatOptionsFileName) == 0:
            epscatoptions = scanDataOptions()
            
        else:
            try:
                epscatoptions = pio.loadPickleFile(epscatOptionsFileName)
                
            except Exception as e:
                s = io.StringIO()
                sei = sys.exc_info()
                traceback.print_exception(file=s, *sei)
                msgbox = QtWidgets.QMessageBox()
                msgbox.setSizeGripEnabled(True)
                msgbox.setIcon(QtWidgets.QMessageBox.Critical)
                msgbox.setWindowTitle(type(e).__name__)
                #msgbox.setWindowTitle(sei[0].__class__.__name__)
                msgbox.setText(sei[0].__class__.__name__)
                msgbox.setDetailedText(s.getvalue())
                msgbox.exec()
                return
                
        self._data_.analysisOptions = epscatoptions
        
        self.displayFrame()
        
        self.statusBar().showMessage("Done!")
        
    @Slot()
    @safeWrapper
    def slot_import_data_wide_descriptors(self):
        from core.workspacefunctions import getvarsbytype
        
        if self._data_ is None:
            return

        scandata_name_vars = dict(getvarsbytype(ScanData, ws = self._scipyenWindow_.workspace))
        
        if len(scandata_name_vars) == 0:
            return
        
        name_list = sorted([name for name in scandata_name_vars.keys() if self._check_for_linescan_data_(scandata_name_vars[name])])
        
        if self._data_ is not None and self._data_.name in name_list:
            pre_selected = self._data_.name
            
        else:
            pre_selected = None
        
        choiceDialog = ItemsListDialog(parent=self, 
                                            title="Import Data-wide Descriptors From:", 
                                            itemsList = name_list, 
                                            preSelected = pre_selected)
        
        ans = choiceDialog.exec()
        
        if ans == QtWidgets.QDialog.Accepted and len(choiceDialog.selectedItemsText):

            lsdata = scandata_name_vars[choiceDialog.selectedItemsText[0]]
            
            for attribute in ("sourceID", "cell", "field", "age", "sex", "genotype"):
                if hasattr(lsdata, attribute):
                    # do this instead of prescribing a default value here, as we 
                    # don't want to override previus values
                    setattr(self._data_, attribute, getattr(lsdata, attribute))
                    
            for d in lsdata.analysisUnit().descriptors:
                self._data_.analysisUnit().setDescriptor(d, lsdata.analysisUnit().getDescriptor(d))
            
            self.displayFrame()
            
    @Slot(int)
    @safeWrapper
    def _slot_prairieViewImportGuiDone(self, value):
        if value:
            dlg = self.sender()
            if dlg is not None:
                self._scipyenWindow_.assignToWorkspace(dlg.scanDataVarName, dlg.scandata)
                self.setData(dlg.scandata, dlg.scanDataVarName)
            
            self.statusBar().showMessage("Import PrairieView done!")
            
    @Slot()
    @safeWrapper
    def slot_importPrairieView(self):
        import mimetypes, io
        from systems import PrairieView
        pvimp = PrairieView.PrairieViewImporter(parent=self) # see NOTE: 2021-04-18 12:25:11 in gui.mainwindow
        #pvimp = PrairieView.PrairieViewImporter(parent=self._scipyenWindow_) # see NOTE: 2021-04-18 12:25:11 in gui.mainwindow
        pvimp.finished[int].connect(self._slot_prairieViewImportGuiDone)
        pvimp.open()
        
    def _analyzeFrames_(self, frames, progressSignal=None, setMaxSignal=None, **kwargs):
        """Calls to the module-level analyseFrame() for each frame in frames.
        This is meant to be executed in a separate GUI thread, (i.e. it is called 
        by a ProgressWorkerRunnable) emits progressSignal(int) Signal
        
        Parameters:
        ==========
        frames: a sequence of int: indices of the data frames to be analysed
        progressSignal: a Signal with one int argument (the frame)
            This signal is emitted after the processing of one frame.
        
        """
        if self._data_ is None:
            return
        
        frames = kwargs.pop(frames)
        
        #print("LSCaTWindow._analyzeFrames_ progressSignal", progressSignal, "**kwargs", kwargs)
        
        #detrend = self.detrendEPSCaTsCheckBox.isChecked()
#         
        for frame in frames:
            analyseFrame(self._data_, frame, **kwargs)
            #analyseFrame(self._data_, frame, detrend=detrend, 
                         #gen_long_fits = self.actionPlot_long_fits.isChecked())
            
            if progressSignal is not None:
                progressSignal.emit(frame)

    def _analyzeUnitInFrames_(self, frames, unit, progressSignal=None, **kwargs):
        if self._data_ is None:
            return
        
        #detrend = self.detrendEPSCaTsCheckBox.isChecked()
        
        for frame in frames:
            analyseFrame(self._data_, frame, unit=unit, **kwargs)
            #analyseFrame(self._data_, frame, unit=unit, detrend=detrend, 
                         #gen_long_fits = self.actionPlot_long_fits.isChecked())
            
            if progressSignal is not None:
                progressSignal.emit(frame)

    @Slot()
    def slot_analyseFramesDone(self):
        self._epscat_analysis_idle_ = True
        self._update_report_()
        
        self._display_scans_block_()
        
        self.displayFrame()
        self.statusBar().showMessage("Done!")
        
    @Slot(object)
    def slot_concatenateLSDataDone(self, obj):
        self._generic_work_idle_ = True
        
        if obj is None:
            return
        
        elif isinstance(obj, str):
            QtWidgets.QMessageBox.critical(self, "Concatenate LSCaT data", obj)
            return
            
        elif isinstance(obj, (tuple, list)) and len(obj) == 3 and all([isinstance(s, str) for s in obj]):
            errMsgDlg = QtWidgets.QErrorMessage(self)
            errMsgDlg.setWindowTitle(obj[0])
            errMsgDlg.showMessage(obj[2])
            
        elif isinstance(obj, ScanData):
            
            dlg = qd.QuickDialog(self, "Store concatenated LSData as:")
            
            namePrompt = qd.StringInput(dlg, "Data name:")
            
            namePrompt.variable.setClearButtonEnabled(True)
            namePrompt.variable.redoAvailable=True
            namePrompt.variable.undoAvailable=True
            
            if len(obj.name.strip())  == 0:
                bname = "scandata"
                
            else:
                bname = strutils.str2symbol(obj.name)
            
            newVarName = validate_varname(bname, self._scipyenWindow_.workspace)
            
            namePrompt.setText(newVarName)
            
            if dlg.exec() == QtWidgets.QDialog.Accepted:
                newVarName = validate_varname(namePrompt.text(), self._scipyenWindow_.workspace)
                
                self._scipyenWindow_.assignToWorkspace(newVarName, obj)
                
            self.statusBar().showMessage("Done!")

    @Slot()
    def slot_appendLSData(self):
        import io
        from core.workspacefunctions import getvarsbytype
        
        if self._data_ is None:
            return
        
        scandata_name_vars = dict(getvarsbytype(ScanData, ws = self._scipyenWindow_.workspace))
        
        if len(scandata_name_vars) == 0:
            return

        name_list = sorted([name for name in scandata_name_vars.keys() if self._check_for_linescan_data_(scandata_name_vars[name])])
        
        choiceDialog = ItemsListDialog(title="Append ScanData Object", 
                                            parent=self, 
                                            itemsList = name_list)
        
        ans = choiceDialog.exec()
        
        if ans == QtWidgets.QDialog.Accepted or len(choiceDialog.selectedItemsText):
            lsdata = scandata_name_vars[choiceDialog.selectedItemsText[0]]
            
            try:
                self._data_.concatenate(lsdata)
                
            except Exception as e:
                s = io.StringIO()
                sei = sys.exc_info()
                traceback.print_exception(file=s, *sei)
                msgbox = QtWidgets.QMessageBox()
                msgbox.setSizeGripEnabled(True)
                msgbox.setIcon(QtWidgets.QMessageBox.Critical)
                msgbox.setWindowTitle(type(e).__name__)
                #msgbox.setWindowTitle(sei[0].__class__.__name__)
                msgbox.setText(sei[0].__class__.__name__)
                msgbox.setDetailedText(s.getvalue())
                msgbox.exec()
                return
                
        self._update_report_()
        
        self.displayFrame()
        
        self.statusBar().showMessage("Done!")
        
    @Slot()
    def slot_concatenateLSData(self):
        from core.workspacefunctions import getvarsbytype
        
        scandata_name_vars = dict(getvarsbytype(ScanData, ws = self._scipyenWindow_.workspace))
        
        if len(scandata_name_vars) == 0:
            return

        name_list = sorted([name for name in scandata_name_vars.keys() if self._check_for_linescan_data_(scandata_name_vars[name])])
        
        choiceDialog = ItemsListDialog(title="Concatenate ScanData Objects", 
                                            parent=self, itemsList = name_list, 
                                            selectmode=QtWidgets.QAbstractItemView.ExtendedSelection)
        
        ans = choiceDialog.exec()
        
        if ans != QtWidgets.QDialog.Accepted or len(choiceDialog.selectedItemsText) == 0:
            return
        
        selected_names = choiceDialog.selectedItemsText
        
        self._generic_work_idle_ = False
        
        pd = QtWidgets.QProgressDialog("Concatenating LSCaT data (ScanData) objects in Workspace", "Abort", 0, len(selected_names), self)
        
        worker = pgui.ProgressWorkerRunnable(self.concatenateScanData,  pd, selected_names)
        
        worker.signals.signal_Finished.connect(pd.reset)
        worker.signals.result[object].connect(self.slot_concatenateLSDataDone)
        
        self.threadpool.start(worker)
        
    @Slot()
    @safeWrapper
    def slot_adoptAnalysisOptionsFromScanData(self):
        from core.workspacefunctions import getvarsbytype

        if self._data_ is None:
            return
        
        scandata_name_vars = dict(getvarsbytype(ScanData, ws = self._scipyenWindow_.workspace))
        
        if len(scandata_name_vars) == 0:
            return
        
        name_list = sorted([name for name in scandata_name_vars.keys() if self._check_for_linescan_data_(scandata_name_vars[name])])
        
        if self._data_.name in name_list:
            pre_selected = self._data_.name
            
        else:
            pre_selected = None
        
        choiceDialog = ItemsListDialog(parent=self, 
                                            itemsList = name_list, 
                                            preSelected = pre_selected)
        
        ans = choiceDialog.exec()
        
        if ans == QtWidgets.QDialog.Accepted and len(choiceDialog.selectedItemsText):
            lsdata = scandata_name_vars[choiceDialog.selectedItemsText[0]]
            if len(lsdata.analysisOptions):
                if "TriggerEventDetection" not in lsdata.analysisOptions.keys():
                    default_options = scanDataOptions()
                    lsdata.analysisOptions["TriggerEventDetection"] = default_options["TriggerEventDetection"]
                    
                self._data_.adoptAnalysisOptions(lsdata)
            
            self._update_report_()
        
            self.displayFrame()
            
            self.statusBar().showMessage("Done!")
            
    @Slot()
    @safeWrapper
    def slot_adoptTriggerProtocolsFromScanDataElectrophysiology(self):
        import io
        from core.workspacefunctions import getvarsbytype
        
        if self._data_ is None:
            return
        try:
            scandata_name_vars = dict(getvarsbytype(ScanData, ws = self._scipyenWindow_.workspace))
            
            if len(scandata_name_vars) == 0:
                return
            
            name_list = sorted([name for name in scandata_name_vars.keys() if self._check_for_linescan_data_(scandata_name_vars[name])])
            
            if self._data_ is not None and self._data_.name in name_list:
                pre_selected = self._data_.name
                
            else:
                pre_selected = None
            
            choiceDialog = ItemsListDialog(parent=self, 
                                                itemsList = name_list, 
                                                preSelected = pre_selected)
            
            ans = choiceDialog.exec()
            
            if ans == QtWidgets.QDialog.Accepted and len(choiceDialog.selectedItemsText):
                lsdata = scandata_name_vars[choiceDialog.selectedItemsText[0]]
                self._data_.adoptTriggerProtocols(lsdata)
                self.displayFrame()
                #self.displayFrame(alldata=True)
            
                self.statusBar().showMessage("Done!")
            
        except Exception as e:  
            s = io.StringIO()
            sei = sys.exc_info()
            traceback.print_exception(file=s, *sei)
            msgbox = QtWidgets.QMessageBox()
            msgbox.setSizeGripEnabled(True)
            msgbox.setIcon(QtWidgets.QMessageBox.Critical)
            msgbox.setWindowTitle(type(e).__name__)
            #msgbox.setWindowTitle(sei[0].__class__.__name__)
            msgbox.setText(sei[0].__class__.__name__)
            msgbox.setDetailedText(s.getvalue())
            msgbox.exec()
            return

    @Slot()
    @safeWrapper
    def slot_adoptTriggerProtocolsFromScanDataImaging(self):
        from core.workspacefunctions import getvarsbytype
        
        if self._data_ is None:
            return
        
        try:
            scandata_name_vars = dict(getvarsbytype(ScanData, ws = self._scipyenWindow_.workspace))
            
            if len(scandata_name_vars) == 0:
                return
            
            name_list = sorted([name for name in scandata_name_vars.keys() if self._check_for_linescan_data_(scandata_name_vars[name])])
            
            
            if self._data_ is not None and self._data_.name in name_list:
                pre_selected = self._data_.name
                
            else:
                pre_selected = None
            
            choiceDialog = ItemsListDialog(parent=self, 
                                                itemsList = name_list, 
                                                preSelected = pre_selected)
            
            ans = choiceDialog.exec()
            
            if ans == QtWidgets.QDialog.Accepted and len(choiceDialog.selectedItemsText):
                lsdata = scandata_name_vars[choiceDialog.selectedItemsText[0]]
                self._data_.adoptTriggerProtocols(lsdata.scansBlock, imaging_source=True)
                self.displayFrame()
                #self.displayFrame(alldata = True)
                
                self.statusBar().showMessage("Done!")

        except Exception as e:  
            s = io.StringIO()
            sei = sys.exc_info()
            traceback.print_exception(file=s, *sei)
            msgbox = QtWidgets.QMessageBox()
            msgbox.setSizeGripEnabled(True)
            msgbox.setIcon(QtWidgets.QMessageBox.Critical)
            msgbox.setWindowTitle(type(e).__name__)
            #msgbox.setWindowTitle(sei[0].__class__.__name__)
            msgbox.setText(sei[0].__class__.__name__)
            msgbox.setDetailedText(s.getvalue())
            msgbox.exec()
            return

    @Slot()
    def slot_adoptAnalysisUnitsFromScanData(self):
        import io
        from core.workspacefunctions import getvarsbytype
        
        if self._data_ is None:
            return
        
        try:
            scandata_name_vars = dict(getvarsbytype(ScanData, ws = self._scipyenWindow_.workspace))
            
            if len(scandata_name_vars) == 0:
                return
            
            name_list = sorted([name for name in scandata_name_vars.keys() if self._check_for_linescan_data_(scandata_name_vars[name])])
            
            if self._data_.name in name_list:
                pre_selected = self._data_.name
                
            else:
                pre_selected = None
            
            choiceDialog = ItemsListDialog(parent=self, 
                                                itemsList = name_list, 
                                                preSelected = pre_selected)
            
            ans = choiceDialog.exec()
            
            if ans == QtWidgets.QDialog.Accepted and len(choiceDialog.selectedItemsText):
                lsdata = scandata_name_vars[choiceDialog.selectedItemsText[0]]
                self._data_.adoptAnalysisUnits(lsdata)
                for c in self._data_.scansCursors.values():
                    c.currentFrame = self.currentFrame
                    
                self.displayFrame()
                
                self._update_report_()
            
                self.statusBar().showMessage("Done!")
        
        except Exception as e:
            traceback.print_exc()
            s = io.StringIO()
            sei = sys.exc_info()
            traceback.print_exception(file=s, *sei)
            msgbox = QtWidgets.QMessageBox()
            msgbox.setSizeGripEnabled(True)
            msgbox.setIcon(QtWidgets.QMessageBox.Critical)
            msgbox.setWindowTitle(type(e).__name__)
            #msgbox.setWindowTitle(sei[0].__class__.__name__)
            msgbox.setText(sei[0].__class__.__name__)
            msgbox.setDetailedText(s.getvalue())
            msgbox.exec()
            return

            
    @Slot()
    def slot_addReplaceElectrophysiologyWorkspace(self):
        import mimetypes, io
        from core.workspacefunctions import getvarsbytype
        
        if self._data_ is None:
            return
        
        ephysData = None
        
        neo_block_name_vars = dict(getvarsbytype(neo.Block, ws = self._scipyenWindow_.workspace))
        
        if len(neo_block_name_vars) == 0:
            return
        
        name_list = sorted(name for name in neo_block_name_vars.keys())
        
        choiceDialog = ItemsListDialog(parent=self, itemsList = name_list)
        
        ans = choiceDialog.exec()
        
        if ans == QtWidgets.QDialog.Accepted and len(choiceDialog.selectedItemsText):
            ephysData = neo_block_name_vars[choiceDialog.selectedItemsText[0]]
            
            ephys_varname = choiceDialog.selectedItem
            
            if len(ephysData.segments) == 0:
                QtWidgets.QMessageBox.critical(self, "Import electrophysiology data", "Block has no segments")
                return
            
            nSignals = [len(seg.analogsignals) for seg in ephysData.segments]
            
            if any([v==0 for v in nSignals]):
                QtWidgets.QMessageBox.critical(self, "Import electrophysiology data", "Block has at least one segments without analog signals")
                return
            
            if any([v != nSignals[0] for v in nSignals]):
                QtWidgets.QMessageBox.critical(self, "Import electrophysiology data", "All segments must contain the same number of analog signals")
                return
            
            start_times = [seg.analogsignals[0].t_start for seg in ephysData.segments]
            
            if not all([np.isclose(t.magnitude.flatten()[0], start_times[0].magnitude.flatten()[0]) for t in start_times]):
                btn = QtWidgets.QMessageBox.question(self, "Import electrophysiology data", "Signals do not have the same start time across the segments. Do you wish to set the relative time to that fo the first segment?",
                                                     defaultButton = QtWidgets.QMessageBox.Yes)
                
                if btn == QtWidgets.QMessageBox.Yes:
                    ephysData = neoutils.set_relative_time_start(deepcopy(ephysData), start_times[0])
                    #ephysData = neoutils.set_relative_time_start(neoutils.neo_copy(ephysData), start_times[0])
                    
                else:
                    return
                    
        try:
            if isinstance(ephysData, neo.Block) and len(ephysData.segments):
                dlg = qd.QuickDialog(self, "Data parameters:")
                ephysStart = ephysData.segments[0].analogsignals[0].t_start.magnitude.flatten()[0]
                ephysEnd   = ephysData.segments[0].analogsignals[0].t_stop.magnitude.flatten()[0]
                
                ephysNamePrompt = qd.StringInput(dlg, "Electrophysiology name:")
                
                ephysNamePrompt.variable.setClearButtonEnabled(True)
                ephysNamePrompt.variable.redoAvailable=True
                ephysNamePrompt.variable.undoAvailable=True
                
                ephysNamePrompt.setText(strutils.str2symbol(ephys_varname))
                
                if "TriggerEventDetection" not in self._data_.analysisOptions:
                    default_options = scanDataOptions()
                    
                    self._data_.analysisOptions["TriggerEventDetection"] = default_options["TriggerEventDetection"]
                
                self._data_.electrophysiology = deepcopy(ephysData)
                #self._data_.electrophysiology = neoutils.neo_copy(ephysData)
                
                tp, _ = parse_trigger_protocols(self._data_.electrophysiology)
                
                if len(tp) == 0:
                    OK, trig_dlg_result = self._trigger_events_detection_gui_(self._data_.analysisOptions,
                                                                                ephysStart, ephysEnd,
                                                                                dlg=dlg)
                    
                    if OK:
                        presyn = trig_dlg_result[0]
                        postsyn = trig_dlg_result[1]
                        photo = trig_dlg_result[2]
                        imaging = trig_dlg_result[3]
                        options = trig_dlg_result[4]
                        
                        tp = auto_detect_trigger_protocols(self._data_.electrophysiology,
                                                presynaptic=presyn,
                                                postsynaptic=postsyn,
                                                photostimulation=photo,
                                                imaging=imaging,
                                                clear=True)
                        
                        self._data_.analysisOptions = options
                        
                    else:
                        return
                    
                self._data_.triggers = tp
                #self._data_.adoptTriggerProtocols(ephysData)

                self.displayFrame()
                self.statusBar().showMessage("Done!")
                    
        except Exception as e:
            s = io.StringIO()
            sei = sys.exc_info()
            traceback.print_exception(file=s, *sei)
            msgbox = QtWidgets.QMessageBox()
            msgbox.setSizeGripEnabled(True)
            msgbox.setIcon(QtWidgets.QMessageBox.Critical)
            msgbox.setWindowTitle(type(e).__name__)
            #msgbox.setWindowTitle(sei[0].__class__.__name__)
            msgbox.setText(sei[0].__class__.__name__)
            msgbox.setDetailedText(s.getvalue())
            msgbox.exec()
            return
        
    @Slot()
    def slot_reorderEphysSegments(self):
        if self._data_ is None:
            return 
        
        dlg = qd.QuickDialog(self, "Reorder electrophysiology segments")
        infotxt = "\n".join(["Enter comma-separated KEY>VALUE pairs, where:\n",
                   "KEY = CURRENT index for the segment\n",
                   "VALUE = NEW position of the segment at current index KEY\n",
                   "e.g. to place 2nd segment at position 0 and 1st segment at position 2 enter 2>0, 1>2 2:1"])
        
        #infotxt = "\n".join(["Enter comma-separated KEY:VALUE pairs, where:\n",
                   #"KEY = NEW index for the segment at current index VALUE\n",
                   #"VALUE = the CURRENT index for the segment to be reshuffled\n",
                   #"e.g. to place 2nd segment at position 0 and 1st segment at position 2 enter 0:2, 2:1"])
        
        dlg.addLabel(infotxt)
        dlg.addLabel("CAUTION! Make sure there are no duplicates/clashes !")
        
        indexPrompt = qd.StringInput(dlg, "New order")
        indexPrompt.variable.setClearButtonEnabled(True)
        indexPrompt.variable.redoAvailable=True
        indexPrompt.variable.undoAvailable=True
        indexPrompt.variable.setToolTip(infotxt)
        
        #dlg.setModal(False) # allow GUI interaction FIXME does not work because we call exec()
        
        if dlg.exec():
            txt = indexPrompt.text()
            
            if len(txt.strip()) == 0:
                return
            
            original_index_order = [k for k in range(self._data_.scansFrames)]
            new_index_order = [k for k in range(self._data_.scansFrames)]
            
            txt_items = txt.split(",")
            
            if len(txt_items):
                #ii = [i.split(":") for i in txt_items]
                ii = [i.split(">") for i in txt_items]
                
            for i in ii:
                if len(i) == 2:
                    try:
                        key = eval(i[0])
                        val = eval(i[1])
                        
                    except Exception as e:
                        QtWidgets.QMessageBox.critical(self, "Reorder electrophysiology segments",
                                                       "Could not parse index mapping from string %s" % i)
                        traceback.print_exc()
                        return
                    
                    if all([isinstance(v, int) for v in (key, val)]):
                        if key not in original_index_order:
                            QtWidgets.QMessageBox.critical(self, "Reorder electrophysiology segments",
                                                        "Invalid origin index %d in %s" % (key, txt))
                            
                            return
                        
                        # check for replications of key
                        replicates = [k for k in original_index_order if k == key]
                        
                        if len(replicates) > 1:
                            QtWidgets.QMessageBox.critical(self, "Reorder electrophysiology segments",
                                                        "Origin index %d is replicated %d times in %s" % (key, len(replicates)-1, txt))
                            
                            return
                        
                        if val not in original_index_order:
                            QtWidgets.QMessageBox.critical(self, "Reorder electrophysiology segments",
                                                        "Invalid destination index %d in %s" % (val, txt))
                            
                            return
                            
                        # check for replications of val
                        replicates = [k for k in original_index_order if k == val]
                        
                        if len(replicates) > 1:
                            QtWidgets.QMessageBox.critical(self, "Reorder electrophysiology segments",
                                                        "Destination index %d is replicated %d times in %s" % (val, len(replicates)-1, txt))
                            
                            return
                            
                        #new_index_order[key] = val
                        new_index_order[val] = key
                        
                    else:
                        QtWidgets.QMessageBox.critical(self, "Reorder electrophysiology segments",
                                                       "Invalid values for index mapping, %s" % i)
                        
                        return
                    
            #print("old index order", original_index_order)
            #print("new index order", new_index_order)
            
            new_index_mapping = dict(zip(new_index_order, original_index_order))
            
            #print("index mapping", new_index_mapping)
            
            # e.g. 
            # [0, 1, 2] = old
            # [2, 0, 1] = new_index_order
            # => segments get assigned in order:
            # 0 -> new_index_order[0] is 2 => segment at old pos [2] goes at pos [0]
            # 1 -> new_index_order[1] is 0 => segment at old pos [0] goes at pos [1]
            # 2 -> new_index_order[2] is 1 => segment at old pos [1] goes at pos [2]
            segments = [self._data_.electrophysiology.segments[k] for k in new_index_order]
            
            
            self._data_.electrophysiology.segments[:] = segments
            
            if len(self._data_.triggers):
                for protocol in self._data_.triggers:
                    protocol_old_segment_index = protocol.segmentIndices()
                    
                    protocol_new_segment_index = [new_index_mapping[k] for k in protocol_old_segment_index]
                    #print("protocol %s"%protocol.name, "old index:", protocol_old_segment_index, "new index:",protocol_new_segment_index)
                    
                    protocol.segmentIndex = protocol_new_segment_index
                    
                    # NOTE: 2019-03-16 22:39:08
                    # this does NOT change the events in ephys because they are
                    # stored by reference
                    #
                    # however the chages are not reflected in the events in 
                    # imaging blocks because they are stored by copy there
                    #
                    # so we update ONLY these:
                    
                    rev_p = protocol.reverseAcquisition(copy=True)
                    
                    ephys.embed_trigger_protocol(rev_p,
                                                    self._data_.scansBlock,
                                                    clearTriggers=True,
                                                    clearEvents=False)
                    
                    ephys.embed_trigger_protocol(rev_p,
                                                    self._data_.sceneBlock,
                                                    clearTriggers=True,
                                                    clearEvents=False)
                    
                    # analysis units SHOULD contain REFRENCES to these protocols, 
                    # so I'm not sure I need to do anything here -- FIXME?
                    # for u in self._data_.analysisUnits:
                        #pass
                        
                # sort the protocols in the list by the first value in their segment indices
                self._data_.triggers.sort(key=lambda x: x.segmentIndices()[0])
            
                
            self.displayFrame()
            
    @Slot()
    def slot_addReplaceElectrophysiologyFile(self):
        import mimetypes, io
        
        if self._data_ is None:
            return
        
        targetDir = self._scipyenWindow_.currentDir
        ephysFilesFilter = ";;".join(["Axon files (*.abf)", "Pickle files (*.pkl)"])
        

        if sys.platform == "win32":
            options = QtWidgets.QFileDialog.Option.DontUseNativeDialog
            kw = {"options":options}
        else:
            kw = {}

        ephysFileNames, _ = QtWidgets.QFileDialog.getOpenFileNames(self,
                                                               caption="Open electrophysiology files",
                                                               filter = ephysFilesFilter,
                                                               directory=targetDir, **kw)
        blocks = list()
        
        ephysData = None
        
        try:
            if len(ephysFileNames) > 0:
                #if all([mimetypes.guess_type(f)[0] == "application/axon-data" for f in ephysFileNames]):
                if all(["application/axon" in mimetypes.guess_type(f)[0] for f in ephysFileNames]):
                    blocks = [pio.loadAxonFile(f) for f in ephysFileNames]
                    
                else:
                    blocks = [pio.loadPickleFile(f) for f in ephysFileNames]
                    
            if len(blocks) > 0:
                if all([isinstance(b, neo.Block) for b in blocks]):
                    ephysData = ephys.concatenate_blocks(*blocks)
                    
                elif all([isinstance(b, neo.Segment) for b in blocks]):
                    ephysData = neo.Block()
                    ephysData.segments[:] = blocks[:]
                    
                else:
                    QtWidgets.QMessageBox.critical("Electrophysiology files must contain neo.Blocks or individual neo.Segments")
                    return
                
            if not isinstance(ephysData, neo.Block):
                return
                
            if len(ephysData.segments) == 0:
                QtWidgets.QMessageBox.critical(self, "Import electrophysiology data", "Block has no segments")
                ephysData = None
            
            nSignals = [len(seg.analogsignals) for seg in ephysData.segments]
            
            if any([v==0 for v in nSignals]):
                QtWidgets.QMessageBox.critical(self, "Import electrophysiology data", "Block has at least one segments without analog signals")
                ephysData = None
            
            if any([v != nSignals[0] for v in nSignals]):
                QtWidgets.QMessageBox.critical(self, "Import electrophysiology data", "All segments must contain the same number of analog signals")
                ephysData = None
            
            start_times = [seg.analogsignals[0].t_start for seg in ephysData.segments]
            
            if not all([np.isclose(t.magnitude.flatten()[0], start_times[0].magnitude.flatten()[0]) for t in start_times]):
                btn = QtWidgets.QMessageBox.question(self, "Import electrophysiology data", "Signals do not have the same start time across the segments. Do you wish to set the relative time to that fo the first segment?",
                                                     defaultButton = QtWidgets.QMessageBox.Yes)
                
                if btn == QtWidgets.QMessageBox.Yes:
                    ephysData = neoutils.set_relative_time_start(deepcopy(ephysData), start_times[0])
                    #ephysData = neoutils.set_relative_time_start(neoutils.neo_copy(ephysData), start_times[0])
                    
                else:
                    ephysData = None
                    
        except Exception as e:  
            traceback.print_exc()
            s = io.StringIO()
            sei = sys.exc_info()
            traceback.print_exception(file=s, *sei)
            msgbox = QtWidgets.QMessageBox()
            msgbox.setSizeGripEnabled(True)
            msgbox.setIcon(QtWidgets.QMessageBox.Critical)
            msgbox.setWindowTitle(type(e).__name__)
            #msgbox.setWindowTitle(sei[0].__class__.__name__)
            msgbox.setText(sei[0].__class__.__name__)
            msgbox.setDetailedText(s.getvalue())
            msgbox.exec()
            return

        try:
            if isinstance(ephysData, neo.Block) and len(ephysData.segments):
                dlg = qd.QuickDialog(self, "Data parameters:")
                ephysStart = ephysData.segments[0].analogsignals[0].t_start.magnitude.flatten()[0]
                ephysEnd   = ephysData.segments[0].analogsignals[0].t_stop.magnitude.flatten()[0]
                
                ephysNamePrompt = qd.StringInput(dlg, "Electrophysiology name:")
                
                ephysNamePrompt.variable.setClearButtonEnabled(True)
                ephysNamePrompt.variable.redoAvailable=True
                ephysNamePrompt.variable.undoAvailable=True
                
                ephysNamePrompt.setText(os.path.splitext(os.path.basename(ephysFileNames[0]))[0])
                
                if "TriggerEventDetection" not in self._data_.analysisOptions:
                    default_options = scanDataOptions()
                    self._data_.analysisOptions["TriggerEventDetection"] = default_options["TriggerEventDetection"]
                
                self._data_.electrophysiology = ephysData
                self._display_ephys_()
                
                tp, _ = parse_trigger_protocols(self._data_.electrophysiology)
                
                if len(tp) == 0:
                    # NOTE: 2020-12-03 12:51:46:
                    # passing a simple dialog here; this will be supplemented 
                    # with trigger protocol detection fields in _trigger_events_detection_gui_
                    OK, trig_dlg_result = self._trigger_events_detection_gui_(self._data_.analysisOptions,
                                                                                ephysStart, ephysEnd,
                                                                                dlg=dlg)
                    
                    if OK:
                        presyn = trig_dlg_result[0]
                        postsyn = trig_dlg_result[1]
                        photo = trig_dlg_result[2]
                        imaging = trig_dlg_result[3]
                        options = trig_dlg_result[4]
                        
                        tp = auto_detect_trigger_protocols(self._data_.electrophysiology,
                                                                        presynaptic=presyn,
                                                                        postsynaptic=postsyn,
                                                                        photostimulation=photo,
                                                                        imaging=imaging,
                                                                        clear=True)
                        
                        self._data_.analysisOptions = options
                        
                    else:
                        return
                    
                self._data_.triggers = tp
                #self._data_.adoptTriggerProtocols(ephysData)

                self.displayFrame()
                self.statusBar().showMessage("Done!")
                    
        except Exception as e:
            traceback.print_exc()
            s = io.StringIO()
            sei = sys.exc_info()
            traceback.print_exception(file=s, *sei)
            msgbox = QtWidgets.QMessageBox()
            msgbox.setSizeGripEnabled(True)
            msgbox.setIcon(QtWidgets.QMessageBox.Critical)
            msgbox.setWindowTitle(type(e).__name__)
            #msgbox.setWindowTitle(sei[0].__class__.__name__)
            msgbox.setText(sei[0].__class__.__name__)
            msgbox.setDetailedText(s.getvalue())
            msgbox.exec()
            return
            
    
    @Slot()
    @safeWrapper
    def slot_analyseData(self):
        if self._data_ is None or len(self._data_.analysisOptions)==0:
            return
        
        if len(self._data_.scansBlock.segments) != self._data_.scansFrames:
            warnings.warn("The number of segments in the data scans block is different from the number of scans frames; data in scans block segments will be reset", RuntimeWarning)
            self._data_.scansBlock.segments.clear()
            self._data_.scansBlock.segments[:] = [neo.Segment() for f in range(self._data_.scansFrames)]
            
        #for trigger_protocol in self._data_.triggers:
            #for index in trigger_protocol.segmentIndices():
                #self._data_.scansBlock.segments[index].name = "Segment %d (%s)" % (index, trigger_protocol.name)
    
        self._epscat_analysis_idle_ = False
        
        pd = QtWidgets.QProgressDialog("EPSCaT Analysis...", "Abort", 0, self._data_.scansFrames, self)
        
        worker = pgui.ProgressWorkerRunnable(self._analyzeFrames_, pd,
                             frames=range(self._data_.scansFrames),
                             detrend = self.detrendEPSCaTsCheckBox.isChecked(),
                             gen_long_fits=self.actionPlot_long_fits.isChecked())
        
        worker.signals.signal_Finished.connect(pd.reset)
        worker.signals.signal_Finished.connect(self.slot_analyseFramesDone)
        
        self.threadpool.start(worker)
        
    @Slot()
    @safeWrapper
    def slot_analyseCurrentFrame(self):
        if self._data_ is None or len(self._data_.analysisOptions)==0:
            return
        
        detrend = self.detrendEPSCaTsCheckBox.isChecked()
        
        analyseFrame(self._data_, self.currentFrame, 
                     detrend=detrend, 
                     gen_long_fits=self.actionPlot_long_fits.isChecked())
        
        self._update_report_()
        
        self.displayFrame()
        
        self.statusBar().showMessage("Done!")
        
        
    @Slot()
    @safeWrapper
    def slot_analyseCurrentLandmarkInCurrentFrame(self):
        if self._data_ is None or len(self._data_.analysisOptions) == 0:
            return
        
        detrend = self.detrendEPSCaTsCheckBox.isChecked()
        
        if len(self._data_.scansCursors) == 0:
            QtWidgets.QMessageBox.critical(self, "EPSCaT Analysis", "No vertical cursors are defined in the scans data")
            return
        
        if self._selected_analysis_unit_ is not None:
            unit = self._selected_analysis_unit_
            
        else:
            if self._selected_analysis_cursor_ is None:
                QtWidgets.QMessageBox.critical(self, "EPSCaT Analysis", "Please select a vertical scans cursor first")
                return
            
            else:
                if len(self._data_.analysisUnits):
                    if self._selected_analysis_cursor_ not in [u.landmark for u in self._data_.analysisUnits]:
                        QtWidgets.QMessageBox.critical(self, "EPSCaT Analysis", "Selected landmark is not assigned to an analysis unit.")
                        return
                    
                        # this should always return critical QMessageBox
                    
                else:
                    QtWidgets.QMessageBox.critical(self, "EPSCaT Analysis", "Selected landmark is not assigned to an analysis unit.")
                    return
                        
            
            unit = self._data_.analysisUnit(self._selected_analysis_cursor_)
        
        if unit is None:
            QtWidgets.QMessageBox.critical(self, "EPSCaT Analysis", "Selected landmark is not assigned to an analysis unit.")
            
        analyseFrame(self._data_, self.currentFrame, unit = unit, 
                     detrend=detrend,
                     gen_long_fits=self.actionPlot_long_fits.isChecked())
        
        self._update_report_()
        
        self.displayFrame()
        
        self.statusBar().showMessage("Done!")
        
    @Slot()
    @safeWrapper
    def slot_analyseCurrentLandmarkInFrames(self):
        if self._data_ is None or len(self._data_.analysisOptions) == 0:
            return
        
        if len(self._data_.scansCursors) == 0:
            QtWidgets.QMessageBox.critical(self, "EPSCaT Analysis", "No vertical cursors are defined in the scans data")
            return
        
        if self._selected_analysis_unit_ is not None:
            unit = self._selected_analysis_unit_
            
        else:
            if self._selected_analysis_cursor_ is None:
                QtWidgets.QMessageBox.critical(self, "EPSCaT Analysis", "Please select a vertical scans cursor first")
                return
            
            else:
                if len(self._data_.analysisUnits):
                    if self._selected_analysis_cursor_ not in [u.landmark for u in self._data_.analysisUnits]:
                        QtWidgets.QMessageBox.critical(self, "EPSCaT Analysis", "Selected landmark is not assigned to an analysis unit.")
                        return
                    
                    # this should always return critical QMessageBox
                    
                else:
                    QtWidgets.QMessageBox.critical(self, "EPSCaT Analysis", "Selected landmark is not assigned to an analysis unit.")
                    return
                        
            unit = self._data_.analysisUnit(self._selected_analysis_cursor_)
        
        if unit is None:
            QtWidgets.QMessageBox.critical(self, "EPSCaT Analysis", "Selected landmark is not assigned to an analysis unit.")
            
        frames = None
        
        protocolName = self.protocolSelectionComboBox.currentText()
        
        if protocolName.lower() == "all":
            frames = range(self._data_.scansFrames)
            
        else:
            frames = self._data_.getProtocolFrames(protocolName)
                
        if frames is None:
            QtWidgets.QMessageBox.critical(self, "EPSCaT Analysis", "No frames assigned for analysis.")
            return
        
        frames = [f for f in frames if f in unit.frames]
        
        if len(frames) == 0:
            QtWidgets.QMessageBox.critical(self, "EPSCaT Analysis", "No frames assigned for analysis.")
            return
            
        self._epscat_analysis_idle_ = False
        
        pd = QtWidgets.QProgressDialog("EPSCaT Analysis...", "Abort", 0, self._data_.scansFrames, self)
        
        worker = pgui.ProgressWorkerRunnable(self._analyzeUnitInFrames_, pd,
                             frames=frames, unit=unit)
        
        worker.signals.signal_Finished.connect(pd.reset)
        worker.signals.signal_Finished.connect(self.slot_analyseFramesDone)
        
        self.threadpool.start(worker)
        
    @Slot(QtWidgets.QTableWidgetItem)
    @safeWrapper
    def slot_epscatParameterChanged(self, item):
        if self._data_ is None or len(self._data_.analysisOptions) == 0:
            return
        
        row = item.row()
        col = item.column()
        s = item.text()
        
        epscatIndex = row // 3
        
        paramIndex = col-2
        
        if s not in ["initial", "lower", "upper"]:
            try:
                value = float(s)
                
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "EPSCaT Parameters", str(e))
                return
                
            if "Fitting" not in self._data_.analysisOptions.keys():
                return
        
            if row == epscatIndex: # initial value changed
                self._data_.analysisOptions["Fitting"]["Initial"][epscatIndex][paramIndex] = value
                
            elif row == epscatIndex + 1: # lower bound value changed
                self._data_.analysisOptions["Fitting"]["Lower"][epscatIndex][paramIndex] = value
                
            elif row == epscatIndex + 2: # upper bound value changed
                self._data_.analysisOptions["Fitting"]["Upper"][epscatIndex][paramIndex] = value
                
            # NOTE: 2018-06-17 21:01:31 DO NOT DELETE
            #self.statusBar().showMessage("Done!")
                
    @Slot(str)
    @safeWrapper
    def slot_indicatorNameChanged(self, value):
        if self._data_ is None or len(self._data_.analysisOptions) == 0:
            return
        
        if "IndicatorCalibration" not in self._data_.analysisOptions.keys():
            return
        
        self._data_.analysisOptions["IndicatorCalibration"]["Name"] = value
        
    @Slot(float)
    @safeWrapper
    def slot_indicatorKdChanged(self, value):
        if self._data_ is None or len(self._data_.analysisOptions) == 0:
            return
        
        if "IndicatorCalibration" not in self._data_.analysisOptions.keys():
            return
        
        if value == -1:
            self._data_.analysisOptions["IndicatorCalibration"]["Kd"] = np.nan
            
        else:
            self._data_.analysisOptions["IndicatorCalibration"]["Kd"] = value
        
    @Slot(float)
    @safeWrapper
    def slot_indicatorFminChanged(self, value):
        if self._data_ is None or len(self._data_.analysisOptions) == 0:
            return
        
        if "IndicatorCalibration" not in self._data_.analysisOptions.keys():
            return
        
        if value == -1:
            self._data_.analysisOptions["IndicatorCalibration"]["Fmin"] = np.nan
            
        else:
            self._data_.analysisOptions["IndicatorCalibration"]["Fmin"] = value
        
    @Slot(float)
    @safeWrapper
    def slot_indicatorFmaxChanged(self, value):
        if self._data_ is None or len(self._data_.analysisOptions) == 0:
            return
        
        if "IndicatorCalibration" not in self._data_.analysisOptions.keys():
            return
        
        if value == -1:
            self._data_.analysisOptions["IndicatorCalibration"]["Fmax"] = value
            
        else:
            self._data_.analysisOptions["IndicatorCalibration"]["Fmax"] = value
            
    @Slot(int)
    def slot_discrimination2DChanged(self, value):
        if self._data_ is None or len(self._data_.analysisOptions) == 0:
            return
        
        if "Discrimination" not in self._data_.analysisOptions.keys():
            self._data_.analysisOptions["Discrimination"] = collections.OrderedDict()
        
        if value == QtCore.Qt.Checked:
            self._data_.analysisOptions["Discrimination"]["Discr_2D"] = True
            
        else:
            self._data_.analysisOptions["Discrimination"]["Discr_2D"] = False
            
        self._data_.modified=True
        self.displayFrame()
            
    @Slot(int)
    def slot_useFirstDiscriminationWindowChanged(self, value):
        if self._data_ is None or len(self._data_.analysisOptions) == 0:
            return
        
        if "Discrimination" not in self._data_.analysisOptions.keys():
            return
        
        if value == QtCore.Qt.Checked:
            self._data_.analysisOptions["Discrimination"]["First"] = True
            
        else:
            self._data_.analysisOptions["Discrimination"]["First"] = False
            
        self._data_.modified=True
        self.displayFrame()
            
    @Slot(bool)
    def slot_discriminationWindowChoiceChanged(self, value):
        if self._data_ is None or len(self._data_.analysisOptions) == 0:
            return
        
        btn = self.sender()
        
        if "Discrimination" not in self._data_.analysisOptions.keys():
            return
        
        if value:
            if btn == self.useIntervalsRadioButton:
                self._data_.analysisOptions["Discrimination"]["WindowChoice"] = "delays"
                
            elif btn == self.useTriggersRadioButton:
                self._data_.analysisOptions["Discrimination"]["WindowChoice"] = "triggers"
                
            elif btn == self.useCursorsForDiscriminationRadioButton:
                self._data_.analysisOptions["Discrimination"]["WindowChoice"] = "cursors"
            
        self._data_.modified=True
        self.displayFrame()
        
    @Slot(float)
    def slot_minimumR2Changed(self, value):
        if self._data_ is None or len(self._data_.analysisOptions) == 0:
            return
        
        if "Discrimination" not in self._data_.analysisOptions.keys():
            return
        
        self._data_.analysisOptions["Discrimination"]["MinimumR2"] = value
            
        self._data_.modified=True
        self.displayFrame()
            
            
    @Slot(float)
    def slot_fsDiscriminantChanged(self, value):
        if self._data_ is None or len(self._data_.analysisOptions) == 0:
            return
        
        if "Discrimination" not in self._data_.analysisOptions.keys():
            return
        
        self._data_.analysisOptions["Discrimination"]["PredicateValue"] = value
            
        self._data_.modified=True
        self.displayFrame()
            
    @Slot(float)
    @safeWrapper
    def slot_setBaseDiscriminationWindow(self, value):
        if self._data_ is None or len(self._data_.analysisOptions) == 0:
            return
        
        if "Discrimination" not in self._data_.analysisOptions.keys():
            return
        
        window = self._data_.analysisOptions["Discrimination"]["BaseWindow"]
        self._data_.analysisOptions["Discrimination"]["BaseWindow"] = value * window.units
            
        self._data_.modified=True
        self.displayFrame()
            
    @Slot(float)
    @safeWrapper
    def slot_setPeakDiscriminationWindow(self, value):
        if self._data_ is None or len(self._data_.analysisOptions) == 0:
            return
        
        if "Discrimination" not in self._data_.analysisOptions.keys():
            return
        
        window = self._data_.analysisOptions["Discrimination"]["PeakWindow"]
        self._data_.analysisOptions["Discrimination"]["PeakWindow"] = value * window.units
        
        self._data_.modified=True
        self.displayFrame()
            
    @Slot(float)
    @safeWrapper
    def slot_epscatDarkCurrentBeginChanged(self, value=None):
        if self._data_ is None or len(self._data_.analysisOptions) == 0:
            return
        
        if value is None:
            value = self.peakWindowDoubleSpinBox.value()
        
        if "Intervals" not in self._data_.analysisOptions.keys():
            return
        
        self._data_.analysisOptions["Intervals"]["DarkCurrent"][0] = value * pq.s
        
    @Slot(float)
    @safeWrapper
    def slot_epscatDarkCurrentEndChanged(self, value):
        if self._data_ is None or len(self._data_.analysisOptions) == 0:
            return
        
        if "Intervals" not in self._data_.analysisOptions.keys():
            return
        
        self._data_.analysisOptions["Intervals"]["DarkCurrent"][1] = value * pq.s
        
    @Slot(float)
    @safeWrapper
    def slot_epscatF0BeginChanged(self, value):
        if self._data_ is None or len(self._data_.analysisOptions) == 0:
            return
        
        if "Intervals" not in self._data_.analysisOptions.keys():
            return
        
        self._data_.analysisOptions["Intervals"]["F0"][0] = value * pq.s
        
    @Slot(float)
    @safeWrapper
    def slot_epscatF0EndChanged(self, value):
        if self._data_ is None or len(self._data_.analysisOptions) == 0:
            return
        
        if "Intervals" not in self._data_.analysisOptions.keys():
            return
        
        self._data_.analysisOptions["Intervals"]["F0"][1] = value * pq.s
        
    @Slot(float)
    @safeWrapper
    def slot_epscatFitBeginChanged(self, value):
        if self._data_ is None or len(self._data_.analysisOptions) == 0:
            return
        
        if "Intervals" not in self._data_.analysisOptions.keys():
            return
        
        self._data_.analysisOptions["Intervals"]["Fit"][0] = value * pq.s
    
    @Slot(float)
    @safeWrapper
    def slot_epscatFitEndChanged(self, value):
        if self._data_ is None or len(self._data_.analysisOptions) == 0:
            return
        
        if "Intervals" not in self._data_.analysisOptions.keys():
            return
        
        self._data_.analysisOptions["Intervals"]["Fit"][1] = value * pq.s
        
    @Slot(float)
    @safeWrapper
    def slot_epscatIntegralBeginChanged(self, value):
        if self._data_ is None or len(self._data_.analysisOptions) == 0:
            return
        
        if "Intervals" not in self._data_.analysisOptions.keys():
            return
        
        self._data_.analysisOptions["Intervals"]["Integration"][0] = value * pq.s
        
    @Slot(float)
    @safeWrapper
    def slot_epscatIntegralEndChanged(self, value):
        if self._data_ is None or len(self._data_.analysisOptions) == 0:
            return
        
        if "Intervals" not in self._data_.analysisOptions.keys():
            return
        
        self._data_.analysisOptions["Intervals"]["Integration"][1] = value * pq.s
        
    @Slot(int)
    @safeWrapper
    def slot_change_analysis_unit_state(self, state):
        if self._data_ is None:
            return
        
        if state == QtCore.Qt.Unchecked:
            self.slot_remove_analysis_unit()
            
        elif state == QtCore.Qt.Checked:
            self.slot_define_analysis_unit()
    
        self._update_report_()
        
    @Slot(int)
    @safeWrapper
    def slot_toggleEPSCaTFit(self, value):
        if self._data_ is None:
            return
        
        if value == QtCore.Qt.Unchecked:
            self._data_.analysisOptions["Fitting"]["Fit"] = False
            
        elif value == QtCore.Qt.Checked:
            self._data_.analysisOptions["Fitting"]["Fit"] = True
            
    @Slot()
    @safeWrapper
    def slot_detectTriggers(self):
        import io
        if self._data_ is None:
            return
        
        if len(self._data_.electrophysiology.segments) == 0:
            QtWidgets.QMessageBox.critical(self, "Detect triggers", "There is no electrophysiology data")
            return
        
        try:
            ephysStart = self._data_.electrophysiology.segments[0].analogsignals[0].t_start.magnitude.flatten()[0]
            ephysEnd   = self._data_.electrophysiology.segments[0].analogsignals[0].t_stop.magnitude.flatten()[0]
            
            if "TriggerEventDetection" not in self._data_.analysisOptions.keys():
                default_options = scanDataOptions()
                self._data_.analysisOptions["TriggerEventDetection"] = default_options["TriggerEventDetection"]
                
            OK, trig_dlg_result = self._trigger_events_detection_gui_(self._data_.analysisOptions,
                                                                        ephysStart, ephysEnd)
            
            if OK:
                presyn = trig_dlg_result[0]
                postsyn = trig_dlg_result[1]
                photo = trig_dlg_result[2]
                imaging = trig_dlg_result[3]
                options = trig_dlg_result[4]
            
                tp = auto_detect_trigger_protocols(self._data_.electrophysiology, 
                                                presynaptic=presyn, 
                                                postsynaptic=postsyn,
                                                photostimulation=photo,
                                                imaging=imaging,
                                                clear=True)
                # NOTE: the events in the protocol list are already 
                # references to the events stored in the ephys block
                self._data_.triggers = tp
                self._data_.analysisOptions = options
                    
                self.displayFrame()
                self._update_report_()
        
            self.statusBar().showMessage("Done!")
            
        except Exception as e:  
            s = io.StringIO()
            sei = sys.exc_info()
            traceback.print_exception(file=s, *sei)
            msgbox = QtWidgets.QMessageBox()
            msgbox.setSizeGripEnabled(True)
            msgbox.setIcon(QtWidgets.QMessageBox.Critical)
            msgbox.setWindowTitle(type(e).__name__)
            #msgbox.setWindowTitle(sei[0].__class__.__name__)
            msgbox.setText(sei[0].__class__.__name__)
            msgbox.setDetailedText(s.getvalue())
            msgbox.exec()
            return

        
        
    @Slot()
    @safeWrapper
    def slot_define_analysis_unit(self):
        if self._data_ is None:
            return
        
        #print("slot_define_analysis_unit ", type(self._selected_analysis_cursor_))
        
        if self._selected_analysis_cursor_ is not None:
            #print("slot_define_analysis_unit selected cursor", self._selected_analysis_cursor_)
            #print("slot_define_analysis_unit selected unit", self._selected_analysis_unit_)
            self._define_analysis_unit_on_landmark_(self._selected_analysis_cursor_)
        
    @safeWrapper
    def _define_analysis_unit_on_landmark_(self, obj):
        if self._data_ is None:
            return
        
        if isinstance(obj, pgui.PlanarGraphics):
            self._selected_analysis_unit_ = self._data_.defineAnalysisUnit(obj, 
                                                                            scene=False,
                                                                            protocols=self._data_.triggers)
            
            self._data_.modified=True
        
            self._update_report_()
        
            self.displayFrame()
        
            
    @Slot()
    @safeWrapper
    def slot_remove_analysis_unit(self):
        #print("slot_remove_analysis_unit")
        if self._data_ is None:
            return
        
        if self._selected_analysis_unit_ is None:
            return
        
        # see NOTE: 2018-09-25 22:19:58
        signalBlockers = [QtCore.QSignalBlocker(w) for w in self.scansviewers + self.sceneviewers]
            
        try:
            #u = self._data_.removeAnalysisUnit(self._selected_analysis_cursor_.name, 
                                            #removeLandmark=False)
            u = self._data_.removeAnalysisUnit(self._selected_analysis_unit_, 
                                            removeLandmark=False)
            
            #print("slot_remove_analysis_unit unit %s with landmark %s " % (u, u.landmark))
            
        except Exception as e:
            traceback.print_exc()
        
        self._selected_analysis_cursor_ = None
        self._selected_analysis_unit_ = None
        
        self._data_.modified=True
        self._update_report_()
        
        self.displayFrame()
        
    @Slot()
    @safeWrapper
    def slot_remove_analysis_cursor(self):
        #print("slot_remove_analysis_cursor")
        if self._data_ is None:
            return
        
        if self._selected_analysis_cursor_ is None:
            return
        
        # see NOTE: 2018-09-25 22:19:58
        signalBlockers = [QtCore.QSignalBlocker(w) for w in self.scansviewers + self.sceneviewers]
        
        try:
            if self._selected_analysis_cursor_.name in [u.landmark.name for u in self._data_.analysisUnits]:
                self._data_.removeAnalysisUnit(self._selected_analysis_cursor_.name, 
                                                removeLandmark=True)
                
            else:
                self._data_.removeLandmark(self._selected_analysis_cursor_)
        
        except Exception as e:
            traceback.print_exc()
            
        self._selected_analysis_cursor_ = None
        self._selected_analysis_unit_ = None
    
        self._data_.modified=True
        self._update_report_()
        
        self.displayFrame()
        
    @Slot()
    @safeWrapper
    def slot_showReportWindow(self):
        self._update_report_()
        self.reportWindow.show()
        #self.reportWindow.view(self._report_dataframe_)
        
        windowSize = self.qsettings.value("LSCaTAnalysis/ReportWindow_Size", None)
        
        if windowSize is not None:
            self.reportWindow.resize(windowSize)
            
        windowPos = self.qsettings.value("LSCaTAnalysis/ReportWindow_Position", None)
        
        if windowPos is not None:
            self.reportWindow.move(windowPos)
            
        windowState = self.qsettings.value("LSCaTAnalysis/ReportWindow_State", None)
        
        if windowState is not None:
            self.reportWindow.restoreState(windowState)
            
        self.reportWindow.activateWindow()
        
    @Slot()
    def slot_removeCurrentScanDataFrame(self):
        if self._data_ is None:
            return
        
        self._data_.removeFrame(self.currentFrame)
        self.displayFrame()
        
    @Slot()
    def slot_removeScanDataFrames(self):
        if self._data_ is None:
            return
        
        dlg = qd.QuickDialog(self, "Remove frames")
        frames_index_prompt = qd.StringInput(dlg, "Frame inidices")
        frames_index_prompt.varibale.setToolTip("Specify the indices of frames to be removed as a comma-separated sequence of integers between 0 (inclusive) and %d (exclusive)" % self._data_.scansFrames)
        frames_index_prompt.variable.setClearButtonEnabled(True)
        frames_index_prompt.variable.redoAvailable = True
        frames_index_prompt.variable.undoAvailable = True
        
        frames_index_prompt.setText(" ")
        
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            txt = frames_index_prompt.text()
            
            if len(txt.strip()) == 0:
                return
            
            try:
                indices = [int(s) for s in txt.split(",")]
                
            except:
                return
            
            for k in range(len(indices)):
                    self._data_.removeFrame(indices[k])
                    
                    for k_,_ in enumerate(indices):
                        indices[k_] -= 1
        
    @Slot()
    @safeWrapper
    def slot_addProtocol(self):
        if self._data_ is None:
            return
        
        newProtocol = TriggerProtocol()
        
        segments_with_protocol = [p.segments for p in self._data_.triggers]
        
        data_segments = [k for k in range(self._data_.scansFrames)]
        
        if all([s in segments_with_protocol for s in data_segments]):
            QtWidgets.QMessageBox.critical(self, "Add Trigger Protocol", "All segments have a protocol assigned.\nCannot add a new protocol until at least one segment is protocol-free")
            return
        
        else:
            protocol_free_segments = [s for s in data_segments if s not in segments_with_protocol]
            
            newProtocol.segmentIndex = protocol_free_segments
                
        newProtocolRowNdx = len(self._data_.triggers)
        
        self.protocolTableWidget.insertRow(newProtocolRowNdx)

        self.protocolTableWidget.setItem(newProtocolRowNdx, 0, QtWidgets.QTableWidgetItem(newProtocol.name))
        
        if newProtocol.presynaptic is not None:
            txt = ", ".join(["%g" % i for i in newProtocol.presynaptic.times])
            self.protocolTableWidget.setItem(newProtocolRowNdx, 1, QtWidgets.QTableWidgetItem(txt) )
    
        if newProtocol.postsynaptic is not None:
            txt = ", ".join(["%g" % i for i in newProtocol.postsynaptic.times])
            self.protocolTableWidget.setItem(newProtocolRowNdx, 2, QtWidgets.QTableWidgetItem(txt))
    
        if newProtocol.photostimulation is not None:
            txt = ", ".join(["%g" % i for i in newProtocol.photostimulation.times])
            self.protocolTableWidget.setItem(newProtocolRowNdx, 3, QtWidgets.QTableWidgetItem(txt))
            
        txt = "%g" % newProtocol.imagingDelay.magnitude.flatten()[0]
        #print("imaging delay txt", txt)
        
        self.protocolTableWidget.setItem(newProtocolRowNdx, 4, QtWidgets.QTableWidgetItem(txt))
            
        # only add a protocol if there are segments without one, otherwise prompt 
        # to make available segments for the new protocol
        
        txt = ", ".join(["%g" % i for i in newProtocol.segmentIndices()])
        
        self.protocolTableWidget.setItem(newProtocolRowNdx, 5, QtWidgets.QTableWidgetItem(txt))
        
        self._data_.addTriggerProtocol(newProtocol)
            
        self._data_.modified=True
        self.displayFrame()
            
    @Slot()
    @safeWrapper
    def slot_removeProtocol(self):
        if self._data_ is None:
            return
        
        protocolNdx = self.protocolTableWidget.currentRow()
        
        self.protocolTableWidget.removeRow(protocolNdx)
        
        if protocolNdx >= len(self._data_.triggers) or protocolNdx < 0:
            return
        
        protocol = self._data_.triggers[protocolNdx]
        
        self._data_.removeTriggerProtocol(protocol)
        
        self._data_.modified=True
        self.displayFrame()
        
    @Slot()
    @safeWrapper
    def slot_addEPSCaTComponent(self):
        # TODO
        item = self.epscatComponentsTableWidget.currentItem()
        self.statusBar().showMessage("slot_addEPSCaTComponent currentItem row %d, col %d: %s" % (item.row(), item.column(), item.text()))
        #print("slot_addEPSCaTComponent currentItem row %d, col %d: %s" % (item.row(), item.column(), item.text()))
    
    @Slot()
    @safeWrapper
    def slot_removeEPSCaTComponent(self):
        # TODO
        item = self.epscatComponentsTableWidget.currentItem()
        self.statusBar().showMessage("slot_removeEPSCaTComponent currentItem row %d, col %d: %s" % (item.row(), item.column(), item.text()))
        #print("slot_removeEPSCaTComponent currentItem row %d, col %d: %s" % (item.row(), item.column(), item.text()))
    
    @Slot(QtWidgets.QTableWidgetItem)
    @safeWrapper
    def slot_protocolTableEdited(self, item):
        """Modifies lsdata's TriggerProtocols directly.
        
        Then calls lsdata.embedTriggerEvents
        """
        col = item.column()
        row = item.row()
        value = item.text()
        
        # columns:
        # 0 = protocol name
        # 1 = presynaptic times
        # 2 = postsynaptic times
        # 3 = photostimulation times
        # 4 = imaging delay
        # 5 = frame indices
        
        # rows: one for each defined protocol
        
        #print("slot_protocolTableEdited")
        
        if row < len(self._data_.triggers):
            protocol = self._data_.triggers[row]
            
            if col == 0: # protocol name
                if len(value.strip()) == 0:
                    value = "Protocol"
                    
                protocol.name=value
                
            elif col == 1: # presynaptic events:
                if len(value.strip()) == 0:
                    protocol.presynaptic = None
                    
                else:
                    #print("slot_protocolTableEdited col 1: value", value)
                    v = eval(value)
                    if isinstance(v, (tuple, list)):
                        evt_times = np.array(v)
                        
                    elif isinstance(v, numbers.Number):
                        evt_times = np.array([v])
                        
                    #print("slot_protocolTableEdited: %s evt_times"% type(evt_times).__name__, evt_times)
                    
                    event = TriggerEvent(times=evt_times*pq.s, event_type = "presynaptic", labels="epsp")#, name="epsp")
                    protocol.presynaptic = event
                
            elif col == 2: # postsynaptic events
                if len(value.strip()) == 0:
                    protocol.postsynaptic =  None
                    
                else:
                    #print("slot_protocolTableEdited col 2: value", value)
                    v = eval(value)
                    if isinstance(v, (tuple, list)):
                        evt_times = np.array(v)
                        
                    elif isinstance(v, numbers.Number):
                        evt_times = np.array([v])
                        
                    event = TriggerEvent(times=evt_times*pq.s, event_type = "postsynaptic", labels="ap")#, name="ap")
                    protocol.postsynaptic = event
                
            elif col == 3: # photostimulation events
                if len(value.strip()) == 0:
                    protocol.photostimulation=None
                    
                else:
                    #print("slot_protocolTableEdited col 3: value", value)
                    v = eval(value)
                    if isinstance(v, (tuple, list)):
                        evt_times = np.array(v)
                        
                    elif isinstance(v, numbers.Number):
                        evt_times = np.array([v])
                        
                    event = TriggerEvent(times=evt_times*pq.s, event_type = "photostimulation", labels="photo")#, name="photo")
                    protocol.photostimulation = event
                
            elif col == 4: # imaging delay 
                if len(value.strip()) == 0:
                    protocol.imagingDelay = 0
                    protocol.acquisition = None
                    
                else:
                    #print("slot_protocolTableEdited col 4: value", value)
                    # NOTE: 2019-03-14 10:52:50
                    # also create imaging event!
                    # TODO add imaging events columns in the table
                    protocol.imagingDelay = eval(value) * pq.s

                event = TriggerEvent(times = protocol.imagingDelay, event_type = "imaging_frame", labels="imaging")
                protocol.acquisition=event
                
            elif col == 5: # frame index
                if len(value.strip()) == 0:
                    value = 0
                    
                else:
                    ndx = eval(value)
                    
                if isinstance(ndx, tuple):
                    ndx = list(ndx)
                    
                elif isinstance(ndx, int):
                    ndx = [ndx]
                    
                protocol.segmentIndex = ndx

            #print("slot_protocolTableEdited", protocol)
            
            #self._data_.embedTriggerEvents(protocol) 
            self._data_.embedTriggerEvents(protocol, to_imaging=False)
            #ephys.embed_trigger_protocol(protocol, self._data_.electrophysiology, clearTriggers=True)
            
            #print("slot_protocolTableEdited", protocol)
            
        self._data_.modified=True
        self.displayFrame()
            
    @Slot(int)
    #@safeGUIWrapper
    @safeWrapper
    def slot_epscatIndicatorChannelChanged(self, value):
        # NOTE: 2017-12-22 11:49:51
        # cannot assume a standardized data structure for analysisOptions
        # other than it must be a dict and that is should contain a dict under
        # the "Channels" key
        # if neither of these are satisfied, the whole analysisOptions dict
        # will be modified/overwritten
        if self._data_ is None:
            return
        
        self._data_.analysisOptions["Channels"]["Indicator"] = self._data_.scansChannelNames[value]
        self._data_.modified=True
        self.displayFrame()
            
            
    @Slot(int)
    @safeWrapper
    def slot_epscatReferenceChannelChanged(self, value):
        if self._data_ is None or len(self._data_.analysisOptions) == 0:
            return
                
        self._data_.analysisOptions["Channels"]["Reference"] = self._data_.scansChannelNames[value]
        self._data_.modified=True
        self.displayFrame()
            
    @Slot()
    @safeWrapper
    def slot_deleteAllAnalysisUnits(self):
        if self._data_ is None:
            return
        
        if len(self._data_.analysisUnits) == 0:
            return
        
        unit_names = sorted([u.name for u in self._data_.analysisUnits])
        
        # see NOTE: 2018-09-25 22:19:58
        signalBlockers = [QtCore.QSignalBlocker(w) for w in self.scansviewers + self.sceneviewers]
        
        try:
            for name in unit_names:
                self._data_.removeAnalysisUnit(name, removeLandmark=True)

        except Exception as e:
            traceback.print_exc()
        
        self._selected_analysis_cursor_ = None
        self._selected_analysis_unit_ = None
        
        self._data_.modified = True

        self._update_report_()
        
        self.displayFrame()
                
    @Slot()
    def slot_removeAllProtocols(self):
        if self._data_ is None:
            return
        
        self._data_.clearTriggerProtocols()
        
        self.displayFrame()
        
    @Slot(QtWidgets.QAction)
    def slot_fileToolbarAction(self, action):
        if action  == self.actionToolbarOpenFile:
            self.slot_openScanDataPickleFile()
            
        elif action == self.actionToolbarDataLoad:
            self.slot_loadWorkspaceScanData()
            
        elif action == self.actionToolbarCopyToWorkspace:
            self.slot_exportCopyToWorkspace()
            
        elif action == self.actionToolbarSaveData:
            self.slot_pickleLSData()
            
        
    @Slot(QtWidgets.QAction)
    def slot_unitsToolbarAction(self, action):
        #print(action)
        if action == self.actionImportUnits:
            self.slot_adoptAnalysisUnitsFromScanData()
            
        elif action == self.actionAdd_unit:
            self.slot_gui_add_unit()
            
        elif action == self.actionRemove_unit:
            pass
            #self.slot_removeUnit()
            
        elif action == self.actionDeleteAllAnalysisUnits:
            self.slot_deleteAllAnalysisUnits()
            
        elif action == self.actionRemoveSpecifiedUnits:
            self.slot_deleteAnalysisUnits()
            
        elif action == self.actionSetup_Vertical_Cursors_In_Frame:
            self.slot_setupLinescanCursorsInCurrentFrame()
            
        elif action  == actionSetup_Vertical_Cursors_in_All_Frames:
            self.slot_setupLinescanCursorsInSpecifiedFrames()
        
    @Slot()
    @safeWrapper
    def slot_deleteAnalysisUnits(self):
        if self._data_ is None:
            return
        
        if len(self._data_.analysisUnits) == 0:
            return
        
        unit_names = sorted([u.name for u in self._data_.analysisUnits])
        
        choiceDialog = ItemsListDialog(parent=self, itemsList = unit_names,
                                            selectmode=QtWidgets.QAbstractItemView.ExtendedSelection)
        
        ans = choiceDialog.exec()
        
        if ans != QtWidgets.QDialog.Accepted or len(choiceDialog.selectedItemsText) == 0:
            return
        
        selected_names = choiceDialog.selectedItemsText
        
        # see NOTE: 2018-09-25 22:19:58
        signalBlockers = [QtCore.QSignalBlocker(w) for w in self.scansviewers + self.sceneviewers]
        
        try:
            for name in selected_names:
                self._data_.removeAnalysisUnit(name, removeLandmark=True)
        
        except Exception as e:
            traceback.print_exc()
        
        self._selected_analysis_cursor_ = None
        self._selected_analysis_unit_ = None
        
        self._data_.modified = True

        self._update_report_()
        
        self.displayFrame()
                
    @safeWrapper
    def displayFrame(self):
        if self._data_ is None:
            return
        
        viewers = self.scansviewers + self.sceneviewers + self.ephysviewers + self.scansblockviewers + self.sceneblockviewers
        
        
        if self.showScanlineCheckBox.checkState() == QtCore.Qt.Checked:
            viewers += self.profileviewers
        
        for win in viewers:
            win.displayFrame()
        
        self._display_graphics_overlays_()
        
        #if self.showScanlineCheckBox.checkState() == QtCore.Qt.Checked:# plot scanline profile
            #self._display_scanline_profiles_()
            
        self._update_protocol_display_()
        
        self._update_ui_fields_()
        
        #self.unsetCursor()
        
    def concatenateScanData(self, name_list, progressSignal=None):
        import io
        if len(name_list):
            try:
                self.statusBar().showMessage("Concatenating LSData ...")
                lsdata = self._scipyenWindow_.workspace[name_list[0]].copy()
                #print("concatenate to %s:" % lsdata.name)
                #lsdata = lsdata.copy()

                if progressSignal is not None:
                    progressSignal.emit(1)
            
                
                for k, name in enumerate(name_list[1:]):
                    scandata = self._scipyenWindow_.workspace[name]
                    #print("concatenate %s" % scandata.name)
                    
                    lsdata = lsdata.concatenate(scandata)
                
                    if progressSignal is not None:
                        progressSignal.emit(k+2)
                        
                return lsdata
                
            except Exception as e:
                traceback.print_exc()
                s = io.StringIO()
                sei = sys.exc_info()
                traceback.print_exception(file=s, *sei)
                return (sei[0].__class__.__name__, str(e), s.getvalue())
            
        #else:
            #if progressSignal is not None:
                #progressSignal.emit(0)
                
    #@safeWrapper
    def collectAnalysisUnits(self, name_list, progressSignal=None):
        """
        name_list: a list of ScanData objects (variables) names in the workspace
        
        progressSignal: None (default) or Signal when this function is
        called from a worker (to be run in a different thread)
        """
        import io
        
        doAverage = self.averageUnitsCheckBox.isChecked()
        exclude_failures = not self.includeFailuresCheckBox.isChecked()
        test_component = self.selectFailureTestComponentComboBox.currentText()
        
        if exclude_failures and test_component == "index":
            testComponentIndexText = self.testEPSCaTComponentInputLineEdit.text()
            
            if len(testComponentIndexText.strip()) == 0:
                QtWidgets.QMessageBox.critical(self, "Export analysis unit", "The EPSCaT test component index or indices must be specified.")
                return -1
            
            try:
                testComponentIndices = [eval(v) for v in testComponentIndexText.split(";")]
                
                if not all([isinstance(v, int) for v in testComponentIndices]):
                    QtWidgets.QMessageBox.critical(self, "Export analysis unit", "Expecting integers for EPSCaT test component indices")
                    return -1
                
                test_component = testComponentIndices
                
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "%s" % type(e).__name__, str(e))
                return -1
            
        if len(name_list):
            scandata = self._scipyenWindow_.workspace[name_list[0]]
            cell = scandata.cell
            field = scandata.field
            
            self.statusBar().showMessage("Collecting analysis units ...")
            
            scandata_units_dict = dict([(strutils.str2symbol("%s_%s_%s" % (cell, field, u.name)), u) \
                                        for u in scandata.extractAnalysisUnits(simple_name=True)])
            
            averaged_scandata_units = dict()
            
            if progressSignal is not None:
                progressSignal.emit(0)
                
            try:
                for k, name in enumerate(name_list[1:]):
                    scandata = self._scipyenWindow_.workspace[name]
                    
                    if scandata.cell == cell and scandata.field == field:
                        unit_data_dict = dict([(strutils.str2symbol("%s_%s_%s" % (cell, field, u.name)), u) \
                            for u in scandata.extractAnalysisUnits(simple_name=True)])
                        
                        for unit_key in unit_data_dict:
                            if unit_key in scandata_units_dict:
                                scandata_units_dict[unit_key].concatenate(unit_data_dict[unit_key])
                                
                            else:
                                scandata_units_dict[unit_key] = unit_data_dict[unit_key]
                        
                    if progressSignal is not None:
                        progressSignal.emit(k+1)
                        
                for key in scandata_units_dict.keys():
                    # canonic name
                    scandata_units_dict[key].name = strutils.str2symbol("%s_%s_%s" % (cell, field, scandata_units_dict[key].name))
                    
                    analyseLSData(scandata_units_dict[key])
                    
                    if doAverage:
                        self.statusBar().showMessage("Averaging data in extracted units ...")
                        
                        if exclude_failures:
                            namesfx = "averaged_success"
                            
                        else:
                            namesfx = "averaged"
                            
                        averaged_unit = scandata_units_dict[key].extractAnalysisUnit(scandata_units_dict[key].analysisUnit(), 
                                                                                        average = True,
                                                                                        exclude_failures = exclude_failures,
                                                                                        name="%s_%s" % (scandata_units_dict[key].name, namesfx))
                        analyseLSData(averaged_unit)
                        
                        averaged_scandata_units["%s_%s" % (key, namesfx)] = averaged_unit
                        
            except Exception as e:
                s0 = str(e)
                s = io.StringIO()
                sei = sys.exc_info()
                traceback.print_exception(file=s, *sei)
                s1 = s.getvalue()
                return (s0,s1)
            
            if doAverage:
                return (scandata_units_dict, averaged_scandata_units)
            
            else:
                return scandata_units_dict
            
    def extractAnalysisUnits(self):
        if self._data_ is None:
            return
        
        detrend = self.detrendEPSCaTsCheckBox.isChecked()
        
        doAverage = self.averageUnitsCheckBox.isChecked()
        excludeFailures = not self.includeFailuresCheckBox.isChecked()
        testComponent = self.selectFailureTestComponentComboBox.currentText()
        
        if excludeFailures and testComponent == "index":
            testComponentIndexText = self.testEPSCaTComponentInputLineEdit.text()
            
            if len(testComponentIndexText.strip()) == 0:
                QtWidgets.QMessageBox.critical(self, "Export analysis unit", "The EPSCaT test component index or indices must be specified.")
                return -1
            
            try:
                testComponentIndices = [eval(v) for v in testComponentIndexText.split(";")]
                
                if not all([isinstance(v, int) for v in testComponentIndices]):
                    QtWidgets.QMessageBox.critical(self, "Export analysis unit", "Expecting integers for EPSCaT test component indices")
                    return -1
                
                testComponent = testComponentIndices
                
            except Exception as e:
                traceback.print_exc()
                QtWidgets.QMessageBox.critical(self, "%s" % type(e).__name__, str(e))
                return -1
            
        try:
            # FIXME/TODO - -and DO NOT DELETE the next line
            #pd = QtWidgets.QProgressDialog("Extracting analysis units...", "Abort", 0, len(self._data_.analysisUnits, self))
            
            result = self._data_.extractAnalysisUnits(average=doAverage, 
                                                      exclude_failures=excludeFailures,
                                                      test_component=testComponent,
                                                      simple_name = True)
            
        except Exception as e:
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, type(e).__name__, str(e))
            return
        
        if result is None:
            QtWidgets.QMessageBox.critical(self, "Export analysis units", "No analysis landmarks/units have been defined")
            return
        
        if isinstance(result, (tuple, list)):
            for r in result:
                for frame in range(r.scansFrames):
                    analyseFrame(r, frame, 
                                 detrend=detrend,
                                 gen_long_fits=self.actionPlot_long_fits.isChecked())
                    
                # FIXME -- do not delete
                if doAverage:
                    r.name = "%s_%s_averaged" % (self._data_.name, r.name)
                else:
                    r.name = "%s_%s" % (self._data_.name, r.name)
                    
        elif isinstance(result, ScanData):
            # this hapens when a data-wide analysis unit is extracted
            for frame in range(result.scansFrames):
                analyseFrame(result, frame, 
                             detrend=detrend,
                             gen_long_fits=self.actionPlot_long_fits.isChecked())
                
                # FIXME do not delete
                
                if doAverage:
                    result.name = "%s_%s_averaged" % (self._data_.name, result.analysisUnit().name)
                    
                else:
                    result.name = "%s_%s" % (self._data_.name, result.analysisUnit().name)
                    
        return result
    
    def extractAnalysisUnit(self):
        """ Extract the selected analysis unit as a ScanData object.
        
        Returns a ScanData constructed from the data region and segments/frames 
        defined in the selected analysis unit and its attached protocols.
        
        If there is no landmark-based analysis unit selected, extracts the entire
        data (effectively copies it).
        
        """
        if self._data_ is None:
            return
        
        detrend =  self.actionDetrendOption.isChecked()
        
        average = self.averageUnitsCheckBox.isChecked()
        excludeFailures = not self.includeFailuresCheckBox.isChecked()
        testComponent = self.selectFailureTestComponentComboBox.currentText()
        
        if excludeFailures and testComponent == "index":
            testComponentIndexText = self.testEPSCaTComponentInputLineEdit.text()
            
            if len(testComponentIndexText.strip()) == 0:
                QtWidgets.QMessageBox.critical(self, "Export analysis unit", "The EPSCaT test component index or indices must be specified.")
                return -1
            
            try:
                testComponentIndices = [eval(v) for v in testComponentIndexText.split(";")]
                
                if not all([isinstance(v, int) for v in testComponentIndices]):
                    QtWidgets.QMessageBox.critical(self, "Export analysis unit", "Expecting integers for EPSCaT test component indices")
                    return -1
                
                testComponent = testComponentIndices
                
            except Exception as e:
                traceback.print_exc()
                QtWidgets.QMessageBox.critical(self, "%s" % type(e).__name__, str(e))
                return -1
            
        try:
            if self._selected_analysis_unit_ is None:
                result = self._data_.extractAnalysisUnit(self._data_.analysisUnit(), 
                                                             average=average, 
                                                             name=self._data_.analysisUnit().name,
                                                             exclude_failures=excludeFailures,
                                                             test_component=testComponent)
                
            else:
                result = self._data_.extractAnalysisUnit(self._selected_analysis_unit_,
                                                             average=average, 
                                                             name=self._selected_analysis_unit_.name,
                                                             exclude_failures=excludeFailures,
                                                             test_component=testComponent)
            
            if isinstance(result, ScanData):
                if self._selected_analysis_unit_ is not None:
                    for frame in range(result.scansFrames):
                        analyseFrame(result, frame, 
                                     detrend=detrend, 
                                     gen_long_fits=self.actionPlot_long_fits.isChecked())
                    
            return result
        
        except Exception as e:
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, "%s" % type(e).__name__, str(e))
            return -1
                
    def slot_batch_extract_reports(self):
        """Exports analysis results for selected workspace ScanData
        
        Analyis results are saved as pandas.DataFrame objects in the workspace
        
        They can be saved as CSV in the current directory, individually, using 
        workspace context menu actions
        
        """
        
        # NOTE: 2019-01-09 18:39:36
        # removed code for writing to CSV
        
        from core.workspacefunctions import getvarsbytype
        
        scandata_name_vars = dict(getvarsbytype(ScanData, ws = self._scipyenWindow_.workspace))
        
        if len(scandata_name_vars) == 0:
            return

        name_list = sorted([name for name in scandata_name_vars.keys() if self._check_for_linescan_data_(scandata_name_vars[name])])
        
        choiceDialog = ItemsListDialog(parent=self, itemsList = name_list, 
                                            selectmode=QtWidgets.QAbstractItemView.ExtendedSelection)
        
        ans = choiceDialog.exec()
        
        if ans != QtWidgets.QDialog.Accepted or len(choiceDialog.selectedItemsText) == 0:
            return
        
        selected_names = choiceDialog.selectedItemsText
        
        self.statusBar().showMessage("Generating reports ...")
        
        try:
            for name in selected_names:
                lsdata = self._scipyenWindow_.workspace[name]
                #filename = "%s.csv" % strutils.str2symbol(lsdata.name)

                # NOTE: 2018-11-25 01:40:51
                # give up on report in text form; use pandas DataFrame directly/exclusively
                if len(lsdata.analysisUnits):
                    #report = reportUnitAnalysis(lsdata, analysis_unit=lsdata.analysisUnits, filename=filename)
                    report = reportUnitAnalysis(lsdata, analysis_unit=lsdata.analysisUnits)#, filename=filename)
                    
                else:
                    #report = reportUnitAnalysis(lsdata, analysis_unit=None, filename=filename)
                    report = reportUnitAnalysis(lsdata, analysis_unit=None)#, filename=filename)
                    
                if len(report) > 0:
                    report_varname = "%s_result" % lsdata.name
                    self._scipyenWindow_.assignToWorkspace(report_varname, report)
                    
        except Exception as e:
            traceback.print_exc()
            
        self.statusBar().showMessage("Done!")
                
    @Slot()
    def slot_collate_reports(self):
        """Concatenates all analysis reports (pandas.DataFrames) from workspace.
        These not be all from the same cell/field/unit.
        """
        from core.workspacefunctions import getvarsbytype
        
        mandatory_keys = ['Data', 'Cell', 'Field', 'Unit', 'Unit_Type', \
                          'averaged', 'Protocol', 'Segment', 'Analysis_Date_Time']
    
        # NOTE: 2018-12-14 16:43:17
        # generate a dictionary of the dataframes in workspace
        dataframe_dict = dict(getvarsbytype(pd.DataFrame, ws = self._scipyenWindow_.workspace))
        
        if len(dataframe_dict) == 0:
            return
        
        # NOTE: 2018-12-14 16:43:42
        # of these picm up ones that have the required columns, as a minimum
        suitable_items = [item for item in dataframe_dict.items() if \
                          all([k in item[1].columns for k in mandatory_keys])]
        
        # NOTE: 2018-12-14 16:45:37 quit if nothing found
        if len(suitable_items) == 0:
            return
        
        # NOTE: 2018-12-14 16:44:26
        # ans sort these by their variable names (lexicographically)
        vars_list = sorted(suitable_items, key=lambda x: x[0])
        
        
        # NOTE: 2018-12-14 16:45:18
        # this is reductant here
        #if len(vars_list) == 0:
            #return
        
        # NOTE: 2018-12-14 16:48:07
        # will raise exception if dataframe variables don't have the same column names
        try:
            # NOTE: 2018-12-14 16:46:03
            # offer these in a list dialog -- allow the user to pick & choose
            choiceDialog = ItemsListDialog(parent=self, itemsList = [item[0] for item in vars_list], 
                                                selectmode=QtWidgets.QAbstractItemView.ExtendedSelection)
            
            ans = choiceDialog.exec()
            
            if ans != QtWidgets.QDialog.Accepted or len(choiceDialog.selectedItemsText):
                return
            
            selected_names = choiceDialog.selectedItems
            
            # NOTE: 2018-12-14 16:47:22
            # we need at least two of these to collate
            if len(selected_names) < 2:
                return
            #if len(selected_names) == 0:
                #return
            
            #elif len(selected_names) == 1:
                #result = dataframe_dict[selected_names[0]]
                #result = self._scipyenWindow_.workspace[selected_names[0]]
                
            else:
                dataframes = [dataframe_dict[name] for name in selected_names]
                #dataframes = [self._scipyenWindow_.workspace[name] for name in selected_names]
                
                result = collateReports(dataframes)
                
                if "Dd_Length" in result.columns:
                    del(result["Dd_Length"])
                    
                if "Number_Of_Branches" in result.columns:
                    del(result["Number_Of_Branches"])
                    
                categoriseLSCaTResult(result)
                
                # NOTE: 2018-12-14 16:49:56
                # adjust values as per the recent API: stop using "NA" as replacement for missing
                # values in numerical columns (bad idea, but initially used to export result to csv
                # importable intop R dataframe objects, BEFORE we started to use pandas)
                
                # NOTE: must do it manually !!!
                #for col in ("Branch_Order", "Branching_Points", "Distance_From_Soma", "Dendrite_Length", "Dendrite_Width", "Spine_Length", "Spine_Width"):
                    #result.loc[result.loc[:,col] == "NA", col] = np.nan
                    #result[col].astype(np.float64, copy=false)
            
            # NOTE: do all come from the same cell?
            
            if (result.Cell == result.Cell[0]).all():
                var_name = strutils.str2symbol("%s_collated_analysis_result" % result.Cell[0])
                
            else:
                var_name = "collated_analysis_result"
            
            
            newVarName = validate_varname(var_name, self._scipyenWindow_.workspace)
            
            dlg = qd.QuickDialog(self, "Export collated results")

            namePrompt = qd.StringInput(dlg, "Variable name:")
            
            namePrompt.variable.setClearButtonEnabled(True)
            namePrompt.variable.redoAvailable=True
            namePrompt.variable.undoAvailable=True
            
            namePrompt.setText(newVarName)
            
            exportCsvPrompt = qd.CheckBox(dlg, "Write to CSV file")
            
            exportCsvPrompt.setChecked(False)
            
            if dlg.exec() == QtWidgets.QDialog.Accepted:
                newVarName = strutils.str2symbol(namePrompt.text()) # allow user to overwrite variables if so wished
                
                write_to_csv = exportCsvPrompt.selection()
                
                self._scipyenWindow_.assignToWorkspace(newVarName, result)
                
                if write_to_csv:
                    namelist = [strutils.str2symbol(newVarName)]

                    targetDir = self._scipyenWindow_.currentDir
                    
                    fileFilter = "CSV files (*.csv)"
                        
                    namelist.append(".csv")
                    
                    filename = "".join(namelist)
                    

                    if sys.platform == "win32":
                        options = QtWidgets.QFileDialog.Option.DontUseNativeDialog
                        kw = {"options":options}
                    else:
                        kw = {}

                    filename, _ = QtWidgets.QFileDialog.getSaveFileName(self,
                                                                        caption="Export analysis result", 
                                                                        filter=fileFilter,
                                                                        directory=os.path.join(targetDir, filename),
                                                                        **kw)
                    
                    if len(filename.strip()) > 0:
                        result.to_csv(filename, na_rep="NA")

            return result
        
        except Exception as e:
            traceback.print_exc()
        
    @safeWrapper
    @Slot()
    def slot_reportLSCaTResults(self):
        """Exports analysis result (pandas.DataFrame) to workspace.
        
        The resulting variable can then be saved as CSV form workspace browser
        
        """
        
        # NOTE: 2019-01-09 17:55:18
        # ditched writing to CSV
        
        if self._data_ is None:
            return

        namelist = [strutils.str2symbol(self._data_.name)]
        #namelist = [strutils.str2symbol(self._data_.name)]
        
        if self._selected_analysis_unit_ is not None:
            namelist.append("_%s" % self._selected_analysis_unit_.name)
        
        #targetDir = self._scipyenWindow_.currentDir
        
        #fileFilter = "CSV files (*.csv)"
            
        #namelist.append(".csv")
        
        #filename = "".join(namelist)
        
        #filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, 
                                                            #caption="Export analysis result", 
                                                            #filter=fileFilter,
                                                            #directory=os.path.join(targetDir, filename))
        
        #if len(filename.strip()) == 0:
            #return
        
        #print("_selected_analysis_unit_", self._selected_analysis_unit_)
        
        try:
            # NOTE: 2018-11-25 01:43:45
            # use pandas DataFrame directly/exclusively
            if self._selected_analysis_unit_ is not None:
                #report_txt, report  = reportUnitAnalysis(self._data_, self._selected_analysis_unit_, filename=filename)
                #report  = reportUnitAnalysis(self._data_, self._selected_analysis_unit_, filename=filename)
                report  = reportUnitAnalysis(self._data_, self._selected_analysis_unit_)
                
            
            else:
                if len(self._data_.analysisUnits):
                    #report  = reportUnitAnalysis(self._data_, self._data_.analysisUnits, filename=filename)
                    report  = reportUnitAnalysis(self._data_, self._data_.analysisUnits)
                    
                else:
                    #report  = reportUnitAnalysis(self._data_, None, filename=filename)
                    report  = reportUnitAnalysis(self._data_, None)
                
        except Exception as e:
            traceback.print_exc()
            QtWidgets.QMessageBox.warning(self, "%s" % type(e).__name__, str(e))
            return
            
            
        if len(report) == 0:
            QtWidgets.QMessageBox.warning(self, "Export analysis result", "Selected unit(s) might have not been analysed!")
            
            return
        
        namelist = [self._data_.name]
            
        namelist.append("_result")
        
        report_varname = "".join(namelist)
        
        self._scipyenWindow_.assignToWorkspace(report_varname, report)
        
        self.statusBar().showMessage("Done!")
        
    @safeWrapper
    @Slot()
    def slot_collectAnalysisUnits(self):
        from core.workspacefunctions import getvarsbytype

        scandata_name_vars = dict(getvarsbytype(ScanData, ws = self._scipyenWindow_.workspace))
        
        if len(scandata_name_vars) == 0:
            return

        name_list = sorted([name for name in scandata_name_vars.keys() if self._check_for_linescan_data_(scandata_name_vars[name])])
        
        choiceDialog = ItemsListDialog(parent=self, itemsList = name_list, 
                                            selectmode=QtWidgets.QAbstractItemView.ExtendedSelection)
        
        ans = choiceDialog.exec()
        
        if ans != QtWidgets.QDialog.Accepted or len(choiceDialog.selectedItemsText) == 0:
            return
        
        selected_names = choiceDialog.selectedItemsText
        
        self._generic_work_idle_ = False
        
        pd = QtWidgets.QProgressDialog("Collecting Analysis Units from ScanData in Workspace", 
                                       "Abort", 0, len(selected_names), self)
        
        worker = pgui.ProgressWorkerRunnable(self.collectAnalysisUnits,  pd, selected_names)
        
        worker.signals.signal_Finished.connect(pd.reset)
        worker.signals.signal_Result[object].connect(self.slot_collectAnalysisDone)
        
        self.threadpool.start(worker)
        
    @safeWrapper
    @Slot(object)
    def slot_collectAnalysisDone(self, obj):
        self._generic_work_idle_ = True
        
        if obj is None:
            return
        
        elif isinstance(obj, str):
            QtWidgets.QMessageBox.critical(self, "Collect analysis units", obj)
            
        elif isinstance(obj, (tuple, list)) and len(obj) == 2 and \
            all([isinstance(o, str) for o in obj]):
            msgbox = QtWidgets.QMessageBox()
            msgbox.setSizeGripEnabled(True)
            msgbox.setIcon(QtWidgets.QMessageBox.Critical)
            msgbox.setWindowTitle("Collect analysis units")
            msgbox.setText(obj[0])
            msgbox.setDetailedText(obj[1])
            msgbox.exec()
            return
                
            
        elif isinstance(obj, dict):
            self._scipyenWindow_.workspace.update(obj)
            
            self._scipyenWindow_.slot_updateWorkspaceModel()
            #self._scipyenWindow_.slot_updateWorkspaceModel(False)
            
            self.statusBar().showMessage("Done!")
            
        elif isinstance(obj, (tuple, list)) and len(obj) == 2 and all([isinstance(o, dict) for o in obj]):
            self._scipyenWindow_.workspace.update(obj[0])
            self._scipyenWindow_.workspace.update(obj[1])
            
            self._scipyenWindow_.slot_updateWorkspaceModel()
            #self._scipyenWindow_.slot_updateWorkspaceModel(False)
            
            self.statusBar().showMessage("Done!")
            
    @Slot()
    def slot_report_window_closing(self):
        self.qsettings.setValue("LSCaTAnalysis/ReportWindow_Size", self.reportWindow.size())
        self.qsettings.setValue("LSCaTAnalysis/ReportWindow_Position", self.reportWindow.pos())
        self.qsettings.setValue("LSCaTAnalysis/ReportWindow_Geometry", self.reportWindow.geometry())
        self.qsettings.setValue("LSCaTAnalysis/ReportWindow_State", self.reportWindow.saveState())
                
    @safeWrapper
    @Slot()
    def slot_exportCurrentAnalysisUnit(self):
        if self._data_ is None:
            return
        
        try:
            result = self.extractAnalysisUnit()
            
        except Exception as e:
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, "%s" % type(e).__name__, str(e))
            return
        
        if result is None:
            QtWidgets.QMessageBox.critical(self, "Export analysis units", "No analysis landmarks/units have been defined")
            return
        
        elif result == -1:
            return
        
        var_name = strutils.str2symbol(result.name)
        
        if var_name in self._scipyenWindow_.workspace.keys():
            dlg = qd.QuickDialog(self, "Assign to workspace")
            dlg.addWidget(QtWidgets.QLabel("A variable named %s already exists" % var_name, parent=dlg))
            dlg.addWidget(QtWidgets.QLabel("You may wish to rename it below", parent=dlg))
            namePrompt = qd.StringInput(dlg, "New name:")
            namePrompt.setText(var_name)
            namePrompt.setToolTip("Enter new name to prevent overwriting in the workspace")
            
            if dlg.exec() == QtWidgets.QDialog.Accepted:
                var_name = namePrompt.text()
                
            else:
                return

        self._scipyenWindow_.workspace[var_name] = result
        self._scipyenWindow_.slot_updateWorkspaceModel()
        #self._scipyenWindow_.slot_updateWorkspaceModel(False)
        
        self.statusBar().showMessage("Done!")
        
    @Slot()
    def slot_exportScanDataOptions(self):
        if self._data_ is None:
            return
        
        targetDir = self._scipyenWindow_.currentDir
        
        fileFilter = "Pickle files (*.pkl)"
            

        if sys.platform == "win32":
            options = QtWidgets.QFileDialog.Option.DontUseNativeDialog
            kw = {"options":options}
        else:
            kw = {}

        if targetDir is not None and targetDir != "" and os.path.exists(targetDir):
            fName, _ = QtWidgets.QFileDialog.getSaveFileName(self, 
                                                          caption="Save options", 
                                                          filter=fileFilter, 
                                                          directory=targetDir, **kw)
            
        else:
            fName, _ = QtWidgets.QFileDialog.getSaveFileName(self, 
                                                          caption="Save options", 
                                                          filter=fileFilter, **kw)
        pio.savePickleFile(self._data_.analysisOptions, fName)
        
        
            
    @safeWrapper
    @Slot()
    def slot_exportAnalysisUnits(self):
        #QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        self.setCursor(QtCore.Qt.WaitCursor)
        
        try:
            result = self.extractAnalysisUnits()
            
            if isinstance(result, (tuple, list)):
                if len(result):
                    for r in result:
                        self._scipyenWindow_.workspace[strutils.str2symbol(r.name)] = r
            
                self._scipyenWindow_.slot_updateWorkspaceModel()
                #self._scipyenWindow_.slot_updateWorkspaceModel(False)
                
                self.statusBar().showMessage("Done!")
                
            elif isinstance(result, ScanData):
                self._scipyenWindow_.workspace[strutils.str2symbol(result.name)] = result
                
                self._scipyenWindow_.slot_updateWorkspaceModel()
                #self._scipyenWindow_.slot_updateWorkspaceModel(False)
                
                self.statusBar().showMessage("Done!")
                
        except Exception as e:
            traceback.print_exc()
            
        self.unsetCursor()
        
    @Slot()
    @safeWrapper
    def slot_processData(self):
        if self._data_ is None:
            return
        
        self.filterData()
        
    @Slot()
    @safeWrapper
    def slot_processScene(self):
        if self._data_ is None:
            return
        
        self.filterData(scans=False)
    
    @Slot()
    @safeWrapper
    def slot_processScans(self):
        if self._data_ is None:
            return
        
        self.filterData(scene=False)
        
        
    @Slot(int)
    @safeWrapper
    def slot_gui_spinbox_select_cursor_by_index(self, index):
        """ TODO FIXME Adapt to select/deselect AnalysisUnits
        or maybe create separate slots?
        """
        if self._data_ is None:
            return
        
        #print("slot_gui_spinbox_select_cursor_by_index %d" % index)
        # NOTE: 2018-09-25 22:22:21
        # see NOTE: 2018-09-25 22:19:58
        signalBlockers = [QtCore.QSignalBlocker(w) for w in [self.selectCursorSpinBox, self.analysisUnitNameLineEdit, self.defineAnalysisUnitCheckBox] + self.scansviewers + self.sceneviewers]
        
        if index == self.selectCursorSpinBox.minimum() or len(self._data_.scansCursors) == 0:
            self.cursorXposDoubleSpinBox.setEnabled(False)
            self.cursorXwindow.setEnabled(False)
            self.cursorYposDoubleSpinBox.setEnabled(False)
            self.cursorYwindow.setEnabled(False)
            
            # now, deselect graphics objects if spin box index is -1 
            for w in self.scansviewers + self.sceneviewers:
                for objdict in w.graphicsObjects().values():
                    for obj in objdict.values():
                        obj.setSelected(False)
                    
            self._selected_analysis_cursor_ = None
            self._selected_analysis_unit_ = None
            self._update_analysis_unit_ui_fields_()

            return
        
        if index < len(self._data_.scansCursors):
            self.cursorXposDoubleSpinBox.setEnabled(True)
            self.cursorXwindow.setEnabled(True)
            self.cursorYposDoubleSpinBox.setEnabled(True)
            self.cursorYwindow.setEnabled(True)
            
            #cursors = sorted([c for c in self._data_.scansCursors.values()], key=lambda x: x.name)
            cursors = sorted([c for c in self._data_.scansCursors.values() if c.hasStateForFrame(self.currentFrame)], key=lambda x: x.x)
            #cursors = sorted([c for c in self._data_.scansCursors.values() if c.hasStateForFrame(self.currentFrame)], key=lambda x: x.x)
            cursorNames = [c.name for c in cursors]
            
            selectedObj = cursors[index]
            
            #print("slot_gui_spinbox_select_cursor_by_index cursor %s" % selectedObj.name)
            
            if selectedObj.type == pgui.GraphicsObjectType.vertical_cursor:
                self._selected_analysis_cursor_ = selectedObj
                self._selected_analysis_unit_ = self._data_.analysisUnit(self._selected_analysis_cursor_)
                
            else:
                self._selected_analysis_cursor_ = None
                self._selected_analysis_unit_ = None
            
            #print("slot_gui_spinbox_select_cursor_by_index selected cursor %s" % self._selected_analysis_cursor_.name)
            #print("slot_gui_spinbox_select_cursor_by_index selected unit %s" % self._selected_analysis_unit_.name)
            
        else:
            self._selected_analysis_cursor_ = None
            self._selected_analysis_unit_ = None
            
        # first, deselect all graphics objects
        for w in self.scansviewers + self.sceneviewers:
            #for objdict in w.graphicsObjects().values():
                #for obj in objdict.values():
                    #obj.setSelected(False)
            for objdict in w.graphicsObjects:
                obj.setSelected(False)
                
        if self._selected_analysis_cursor_ is not None:
            for obj in self._selected_analysis_cursor_.frontends:
                obj.setSelected(True)
        

        self._update_analysis_unit_ui_fields_()
            
    @Slot(str)
    @safeWrapper
    def slot_gui_changed_unit_type_string(self, val):
        if self._data_ is None:
            return
            
        if self._selected_analysis_unit_ is not None:
            self._selected_analysis_unit_.type = val
            
        else:
            self._data_.analysisUnit().type = val
            
        if val not in self._data_.availableUnitTypes:
            self._data_.availableUnitTypes.append(val)
            
        self._update_report_()
        
    @Slot(str)
    @safeWrapper
    def slot_gui_changed_genotype(self, val):
        if self._data_ is None:
            return
            
        if self._selected_analysis_unit_ is not None:
            self._selected_analysis_unit_.genotype = val
            
        else:
            self._data_.analysisUnit().genotype = val
            for unit in self._data_.analysisUnits:
                unit.genotype = val
            
        if val not in self._data_._availableGenotypes_:
            self._data_._availableGenotypes_.append(val)
            
        self._update_report_()
        
    @Slot(str)
    @safeWrapper
    def slot_gui_changed_sex(self, val):
        if self._data_ is None:
            return
        
        if self._selected_analysis_unit_ is not None:
            self._selected_analysis_unit_.sex = val
            
        else:
            self._data_.analysisUnit().sex = val
            for unit in self._data_.analysisUnits:
                unit.sex = val
            
        self._update_report_()
        
    @Slot()
    @safeWrapper
    def slot_gui_edit_analysis_unit_descriptors(self):
        """
        """
        # we need:
        # distance from soma
        # dendrite length
        # number of branching points
        # branch order (1 = primary; 2 = secondary: branch of primary; 3 = tertiary: branch of secondary etc )
        # spine_width
        # spine_length
        # dendrite_width
        
        if self._data_ is None:
            return
        
        data_wide = False
        
        if len(self._data_.analysisUnits) == 0:
            unit = self._data_.analysisUnit()
            data_wide = True
            
        elif self._selected_analysis_cursor_ is None:
            if len(self._data_.scansCursors):
                if len(self._data_.analysisUnits):
                    btn = QtWidgets.QMessageBox.question(self, 
                                                "Edit analysis unit descriptors",
                                                "There are analysis units attached to cursors, but none was selected. \n If you continue, this will only modify the descriptors for the Analysis Unit attached to the entire data.\n Do you wish to continue?")
                    if btn != QtWidgets.QMessageBox.Yes:
                        return
                
                else:
                    btn = QtWidgets.QMessageBox.question(self, 
                                                "Edit analysis unit descriptors",
                                                "There are to vertical cursors defined in the scans data, but no analysis unit. \n If you continue, this will only modify the descriptors for the Analysis Unit attached to the entire data.\n Do you wish to continue?")
                    if btn != QtWidgets.QMessageBox.Yes:
                        return
                
            unit = self._data_.analysisUnit()
            unit._descriptors_.mutable_types=True
            data_wide = True
            
        else:
            cursorNames = sorted([k for k in self._data_.scansCursors.keys()])
            
            signalBlockers = [QtCore.QSignalBlocker(widget) for widget in \
                (self.selectCursorSpinBox, self.analysisUnitNameLineEdit, \
                self.cursorXposDoubleSpinBox, self.cursorYposDoubleSpinBox, \
                self.cursorXwindow, self.cursorYwindow, \
                self.unitTypeComboBox, self.genotypeComboBox, \
                self.sexComboBox, self.ageLineEdit, self.defineAnalysisUnitCheckBox)]
            
            if not self._data_.hasAnalysisUnit(self._selected_analysis_cursor_):
                self._data_.defineAnalysisUnit(self._selected_analysis_cursor_)
                
                self.selectCursorSpinBox.setValue(cursorNames.index(self._selected_analysis_cursor_.name))

                self.analysisUnitNameLineEdit.setText(self._selected_analysis_cursor_.name)

                self.cursorXposDoubleSpinBox.setValue(self._selected_analysis_cursor_.x)
                self.cursorYposDoubleSpinBox.setValue(self._selected_analysis_cursor_.y)

                self.cursorXwindow.setValue(self._selected_analysis_cursor_.xwindow)
                self.cursorYwindow.setValue(self._selected_analysis_cursor_.ywindow)
                
                self.defineAnalysisUnitCheckBox.setCheckState(QtCore.Qt.Checked)
                
            unit = self._data_.analysisUnit(self._selected_analysis_cursor_)
            unit._descriptors_.mutable_types=True
            data_wide = False
        
        dlg = qd.QuickDialog(self, "Edit analysis unit descriptors")
        
        if data_wide:
            somatic_distance_field = qd.StringInput(dlg, "Distance from soma (um) (*)")
            branch_order_field = qd.StringInput(dlg, "Branch order (*)")
            nbranches_field = qd.StringInput(dlg, "Branching points (*)")
        else:
            somatic_distance_field = qd.StringInput(dlg, "Distance from soma (um)")
            branch_order_field = qd.StringInput(dlg, "Branch order")
            nbranches_field = qd.StringInput(dlg, "Branching points")
            
        ddwidth_field = qd.StringInput(dlg, "Dendrite width (um)")
        ddlength_field = qd.StringInput(dlg, "Dendrite length (um)")
        splength_field = qd.StringInput(dlg, "Spine length (um)")
        spwidth_field = qd.StringInput(dlg, "Spine width (um)")
        
        if data_wide:
            propagate_check = qd.CheckBox(dlg, "(*) Propagate to nested units")
            propagate_check.setChecked(True)
        else:
            propagate_check = None
            
            
        somatic_distance_field.variable.setClearButtonEnabled(True)
        somatic_distance_field.variable.redoAvailable = True
        somatic_distance_field.variable.undoAvailable = True
        
        somatic_distance = unit.getDescriptor("Distance_From_Soma")
        
        if somatic_distance is None or (isinstance(somatic_distance, str) and somatic_distance.strip().lower() in ("na", "nan", "none")) or somatic_distance is np.nan:
            somatic_distance_field.setText("NA")
            
        else:
            somatic_distance_field.setText("%g" % somatic_distance)
        
        ddwidth_field.variable.setClearButtonEnabled(True)
        ddwidth_field.variable.redoAvailable = True
        ddwidth_field.variable.undoAvailable = True
        
        dendrite_width = unit.getDescriptor("Dendrite_Width")
        
        if dendrite_width is None or (isinstance(dendrite_width, str) and dendrite_width.strip().lower() in ("na", "nan", "none")) or dendrite_width is np.nan:
            ddwidth_field.setText("NA")
            
        else:
            ddwidth_field.setText("%g" % dendrite_width)
            
        ddlength_field.variable.setClearButtonEnabled(True)
        ddlength_field.variable.redoAvailable=True
        ddlength_field.variable.undoAvailable = True
        
        ddlength = unit.getDescriptor("Dendrite_Length")
        
        if ddlength is None or (isinstance(ddlength, str) and ddlength.strip().lower() in ("na", "nan", "none")) or ddlength is np.nan:
            ddlength_field.setText("NA")
            
        else:
            ddlength_field.setText("%g" % ddlength)
            
        branch_order_field.variable.setClearButtonEnabled(True)
        branch_order_field.variable.redoAvailable = True
        branch_order_field.variable.undoAvailable = True
            
        branch_order = unit.getDescriptor("Branch_Order")
        
        if branch_order is None or (isinstance(branch_order, str) and branch_order.strip().lower() in ("na", "nan", "none")) or branch_order is np.nan:
            branch_order_field.setText("NA")
            
        else:
            branch_order_field.setText("%d" % branch_order)
            
        nbranches_field.variable.setClearButtonEnabled(True)
        nbranches_field.variable.redoAvailable = True
        nbranches_field.variable.undoAvailable = True
        
        nbranches = unit.getDescriptor("Branching_Points")
        
        if nbranches is None or (isinstance(nbranches, str) and nbranches.strip().lower() in ("na", "nan", "none")) or nbranches is np.nan:
            nbranches_field.setText("NA")
            
        else:
            nbranches_field.setText("%d" % nbranches)
            
        spine_length = unit.getDescriptor("Spine_Length")
        
        if spine_length is None or (isinstance(spine_length, str) and spine_length.strip().lower() in ("na", "nan", "none")) or spine_length is np.nan:
            splength_field.setText("NA")
            
        else:
            splength_field.setText("%g" % spine_length)
        
        splength_field.variable.setClearButtonEnabled(True)
        splength_field.variable.redoAvailable = True
        splength_field.variable.undoAvailable = True
        
        
        spwidth_field.variable.setClearButtonEnabled(True)
        spwidth_field.variable.redoAvailable = True
        spwidth_field.variable.undoAvailable = True
        
        spine_width = unit.getDescriptor("Spine_Width")
        
        if spine_width is None or (isinstance(spine_width, str) and spine_width.strip().lower() in ("na", "nan", "none")) or spine_width is np.nan:
            spwidth_field.setText("NA")
            
        else:
            spwidth_field.setText("%g" % spine_width)
            
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            # NOTE: 2019-01-10 10:50:44 
            # dialog was accepted
            somatic_distance = somatic_distance_field.text()
            
            if somatic_distance.lower().strip() in ("", "na", "nan", "none"):
                somatic_distance = np.nan
                
            else:
                try:
                    somatic_distance = float(somatic_distance)
                    
                except Exception as e:
                    traceback.print_exc()
                    QtWidgets.QMessageBox.critical(self, "%s" % type(e).__name__, str(e))
                    return
            
            nbranches = nbranches_field.text()
            
            if nbranches.lower().strip() in ("", "na", "nan", "none"):
                nbranches = np.nan
                
            else:
                try:
                    nbranches = int(nbranches)
                    
                except Exception as e:
                    traceback.print_exc()
                    QtWidgets.QMessageBox.critical(self, "%s" % type(e).__name__, str(e))
                    return
                
            branch_order = branch_order_field.text()
            
            if branch_order.lower().strip() in ("", "na", "nan", "none"):
                branch_order = np.nan
                
            else:
                try:
                    branch_order = int(branch_order)
                    
                    if branch_order < 1:
                        QtWidgets.QMessageBox.critical(self, "Analysis Unit Descriptors", "The smallest branch order is 1; got %d instead" % branch_order)
                        return
                            
                except Exception as e:
                    traceback.print_exc()
                    QtWidgets.QMessageBox.critical(self, "%s" % type(e).__name__, str(e))
                    return
                
            ddlength = ddlength_field.text()
            
            if ddlength.lower().strip() in ("", "na", "nan", "none"):
                ddlength = np.nan
                
            else:
                try:
                    ddlength = float(ddlength)
                
                except Exception as e:
                    traceback.print_exc()
                    QtWidgets.QMessageBox.critical(self, "%s" % type(e).__name__, str(e))
                    return
                
            
            dendrite_width = ddwidth_field.text()
            
            if dendrite_width.lower().strip() in ("", "na", "nan", "none"):
                dendrite_width = np.nan
                
            else:
                try:
                    dendrite_width = float(dendrite_width)
                    
                except Exception as e:
                    traceback.print_exc()
                    QtWidgets.QMessageBox.critical(self, "%s" % type(e).__name__, str(e))
                    return
                
            spine_width = spwidth_field.text()
            
            if spine_width.lower().strip() in ("", "na", "nan", "none"):
                spine_width = np.nan
                
            else:
                try:
                    spine_width = float(spine_width)
                    
                except Exception as e:
                    traceback.print_exc()
                    QtWidgets.QMessageBox.critical(self, "%s" % type(e).__name__, str(e))
                    return
            
            spine_length = splength_field.text()
            
            if spine_length.lower().strip() in ("", "na", "nan", "none"):
                spine_length = np.nan
                
            else:
                try:
                    spine_length = float(spine_length)
                    
                except Exception as e:
                    traceback.print_exc()
                    QtWidgets.QMessageBox.critical(self, "%s" % type(e).__name__, str(e))
                    return
                
            unit.setDescriptor("Distance_From_Soma", float(somatic_distance))
            unit.setDescriptor("Branching_Points", nbranches)
            unit.setDescriptor("Branch_Order", branch_order)
            unit.setDescriptor("Dendrite_Width", float(dendrite_width))
            unit.setDescriptor("Dendrite_Length", float(ddlength))
            unit.setDescriptor("Spine_Width", float(spine_width))
            unit.setDescriptor("Spine_Length", float(spine_length))
            
            # propagate relevant data-wide unit descriptors to landmark-based units
            
            if unit == self._data_.analysisUnit() or unit.landmark is None:
                if data_wide and propagate_check is not None:
                    if propagate_check.isChecked():
                        for u in self._data_.analysisUnits:
                            u.setDescriptor("Distance_From_Soma", float(somatic_distance))
                            u.setDescriptor("Branching_Points", nbranches)
                            u.setDescriptor("Branch_Order", branch_order)
            
            self._data_.modified = True

            self._update_report_()
        
            self.displayFrame()
            
    @Slot()
    @safeWrapper
    def slot_gui_add_unit(self):
        if self._data_ is None:
            return
        
        if len(self.scansviewers) == 0:
            return
        
        if self._data_.scans is None or len(self._data_.scans) == 0:
            return
        
        # see NOTE: 2018-09-25 22:19:58
        signalBlockers = [QtCore.QSignalBlocker(w) for w in self.scansviewers + self.sceneviewers]
        
        self._add_vertical_cursor_(asUnit=True)
        
        
    @Slot()
    def slot_removeUnit(self):
        #print("LSCaTWindow.slot_removeUnit")
        if self._data_ is None:
            return
        
        if self._selected_analysis_unit_ is None:
            return
        
        sigBlockers = [QtCore.QSignalBlocker(w) for w in self.scansviewers + self.sceneviewers]
        
        if self._selected_analysis_unit_ in self._data_.analysisUnits:
            obj = self._selected_analysis_unit_.landmark
            
            if len(obj.linkedObjects):
                for linked_obj in obj.linkedObjects:
                    if linked_obj in self._data_.scansRois.values():
                        self._data_.removeRoi(linked_obj.name, scans=True)
                        ww = self.scansviewers
                        
                    elif linked_obj in self._data_.sceneRois.values():
                        self._data_.removeRoi(linked_obj.name, scans=False)
                        ww = self.sceneviewers
                        
                    elif linked_obj in self._data_.scansCursors.values():
                        self._data_.removeCursor(linked_obj.name, scans=True)
                        ww = self.scansviewers
                        
                    elif linked_obj in self._data_.sceneCursors.values():
                        self._data_.removeCursor(linked_obj.name, scans=False)
                        ww = self.sceneviewers
                        
                    else:
                        ww = None
                        
                    if ww is not None:
                        for w in ww:
                            w.removeGraphicsObject(linked_obj.name)
                                
            unit = self._data_.removeAnalysisUnit(self._selected_analysis_unit_, removeLandmark=True)
            
            #print("removed unit landmark: ", type(unit.landmark))
            
        self._data_.modified = True

        self._update_report_()
        
        self.displayFrame()

    @Slot()
    def slot_gui_add_vertical_cursor(self):
        self._add_vertical_cursor_()
        
    def _add_vertical_cursor_(self, asUnit=False):
        if self._data_ is None:
            return
        
        if len(self.scansviewers) == 0:
            return
        
        # NOTE: 2018-09-25 22:19:58
        # recipe to block re-entrant signals in the code below
        # cleaner than manually connecting and re-connecting
        # and also exception-safe
        signalBlockers = [QtCore.QSignalBlocker(w) for w in self.scansviewers + self.sceneviewers]
        
        # deselect all cursors first
        for w in self.scansviewers + self.sceneviewers:
            for objdict in w.graphicsObjects().values():
                for obj in objdict.values():
                    obj.setSelected(False)
                    #obj.selectMe.emit(obj.ID, False)
                
        self._selected_analysis_cursor_ = None
        self._selected_analysis_unit_ = None
        
        # go ahead and add a new cursor
        # NOTE: 2018-09-29 10:17:17
        # TODO: wait loop for picking up a window with mouse click
        # - if next click selects a scans window:
        #       call its viewerWidget.createNewCursor as below
        # - else return
        win = self.scansviewers[0]
        
        frontend_obj = win.viewerWidget.newGraphicsObject(pgui.VerticalCursor)
        #frontend_obj = win.viewerWidget.createNewCursor(pgui.GraphicsObjectType.vertical_cursor, autoSelect=True)
        
        obj = frontend_obj.backend # the added pictgui.Cursor
        
        self._data_.setCursor(obj, scans=True, append=True)
        
        self._selected_analysis_cursor_ = obj
        
        for w in self.scansviewers:
            if w != win:
                w.addPlanarGraphics(obj, label=obj.name, labelShowsPosition=False)
                
        for f in obj.frontends:
            f.labelShowsPosition = False
            f.setTransparentLabel(not self.actionOpaque_cursor_labels.isChecked())
            f.setSelected(True)

        if self.actionLink_vertical_scan_cursors_to_scene_point_cursors.isChecked():
            pc = self._link_scans_vcursor_to_scene_pcursor_(obj)

            if pc:
                for w in self.sceneviewers:
                    if w != win:
                        pcobj = w.addPlanarGraphics(pc, label = pc.name,
                                                labelShowsPosition=False)
                        
                        if (pcobj is not None):
                            pcobj.setTransparentLabel(not self.actionOpaque_cursor_labels.isChecked())
                
        cursors = sorted([c for c in self._data_.scansCursors.values() if c.type == pgui.GraphicsObjectType.vertical_cursor], key = lambda x: x.x)
        cursorNames = [c.name for c in cursors]
        
        # see NOTE: 2018-09-25 22:19:58
        sigBlock = QtCore.QSignalBlocker(self.selectCursorSpinBox)
        
        if len(cursorNames) and obj.name in cursorNames:
            if self.selectCursorSpinBox.maximum() != len(self._data_.scansCursors)-1:
                self.selectCursorSpinBox.setRange(-1, len(self._data_.scansCursors)-1)
                
            self.selectCursorSpinBox.setValue(cursorNames.index(obj.name))
            
        if asUnit:
            self._define_analysis_unit_on_landmark_(obj)
        
        self._data_.modified = True

        self._update_report_()
        
        self.displayFrame()
                
    @Slot()
    @safeWrapper
    def slot_gui_changed_source_ID(self):
        if self._data_ is None:
            return
        
        newname = strutils.str2symbol(self.sourceIDLineEdit.text())
        
        #print("newname")
        
        if len(newname.strip()) == 0:
            if len(self._data_.cell) and self._data_.cell != "NA":
                srcID = self._data_.cell.split(".")
                
                if len(srcID) == 0:
                    srcID= "NA"
                    
                elif len(srcID) in (1,2):
                    srcID = srcID[0]
                    
                    if len(srcID) == 0:
                        srcID = "NA"
                
                else:
                    srcID = ".".join(srcID[:-1])
                
                self._data_.sourceID = srcID
                
            else:
                self._data_.sourceID = "NA"
            
        else:
            self._data_.sourceID = newname
            
        # see NOTE: 2018-09-25 22:19:58
        sigBlock = QtCore.QSignalBlocker(self.sourceIDLineEdit)
        
        #self.cellLineEdit.editingFinished.disconnect(self.slot_gui_changed_cell_name)
        self.sourceIDLineEdit.setText(self._data_.sourceID)
        #self.cellLineEdit.editingFinished.connect(self.slot_gui_changed_cell_name, type = QtCore.Qt.QueuedConnection)
        
        self._data_.modified = True
        
        self._update_report_()
        
        self.displayFrame()
        
    @Slot()
    @safeWrapper
    def slot_gui_age_changed(self):
        if self._data_ is None:
            return
        
        signalBlocker = QtCore.QSignalBlocker(self.ageLineEdit)
        
        newage = self.ageLineEdit.text()
        
        if len(newage.strip().lower()) == 0:
            self._data_.age = "NA"
            self.ageLineEdit.setText("NA")
            return
            
        if newage.strip().lower() == "na":
            self._data_.age = "NA"
            return
        
        
        try:
            value_string, unit_string = newage.split()
            value = eval(value_string)
            units = unit_quantity_from_name_or_symbol(unit_string)
            
            if not check_time_units(u):
                raise TypeError("cannot resolve string %s a python time quantity" % newage)
            
            age = value * units
            
            self._data_.age = age
            
        except Exception as e:
            traceback.print_exc()
            
    @Slot()
    @safeWrapper
    def slot_gui_changed_cell_name(self):
        if self._data_ is None:
            return
        
        newname = strutils.str2symbol(self.cellLineEdit.text())
        
        if len(newname.strip()) == 0:
            self._data_.cell = "NA"
            
        else:
            self._data_.cell = newname
            
        # see NOTE: 2018-09-25 22:19:58
        sigBlock = QtCore.QSignalBlocker(self.cellLineEdit)
        
        #self.cellLineEdit.editingFinished.disconnect(self.slot_gui_changed_cell_name)
        self.cellLineEdit.setText(self._data_.cell)
        #self.cellLineEdit.editingFinished.connect(self.slot_gui_changed_cell_name, type = QtCore.Qt.QueuedConnection)
        
        if self._data_.sourceID == "NA" and self._data_.cell != "NA":
            srcID = self._data_.cell.split(".")
            
            if len(srcID) == 0:
                srcID= "NA"
                
            elif len(srcID) in (1,2):
                srcID = srcID[0]
                
                if len(srcID) == 0:
                    srcID = "NA"
            
            else:
                srcID = ".".join(srcID[:-1])
            
            self._data_.sourceID = srcID
            
            sigBlock2 = QtCore.QSignalBlocker(self.sourceIDLineEdit)
            self.sourceIDLineEdit.setText(self._data_.sourceID)
        
        self._data_.modified = True
        
        self._update_report_()
        
        self.displayFrame()
            
    @Slot()
    @safeWrapper
    def slot_gui_changed_field_name(self):
        if self._data_ is None:
            return
        
        newname = strutils.str2symbol(self.fieldLineEdit.text())
        
        if len(newname.strip()) == 0:
            self._data_.field = "NA"
            
        else:
            self._data_.field = newname
            
        # see NOTE: 2018-09-25 22:19:58
        sigBlock = QtCore.QSignalBlocker(self.fieldLineEdit)
            
        #self.fieldLineEdit.editingFinished.disconnect(self.slot_gui_changed_field_name)
        self.fieldLineEdit.setText(self._data_.field)
        #self.fieldLineEdit.editingFinished.connect(self.slot_gui_changed_field_name, type = QtCore.Qt.QueuedConnection)
        
        self._data_.modified = True
        
        self._update_report_()
        
        self.displayFrame()
        
    #@Slot(str)
    #@safeWrapper
    #def slot_gui_changed_analysis_unit_name(self, newName):
    @Slot()
    @safeWrapper
    def slot_gui_changed_analysis_unit_name(self):
        """Rename an analysis unit
        For landmark (PlanarGraphics) - based analysis units, this also changes
        the name of the landmark.
        
        For data-wise units, this changes the name of the unit iself.
        """
        if self._data_ is None:
            return
        
        signalBlockers = [QtCore.QSignalBlocker(w) for w in (self.selectCursorSpinBox, self.analysisUnitNameLineEdit, self.defineAnalysisUnitCheckBox)]
        
        newName = strutils.str2symbol(self.analysisUnitNameLineEdit.text())
        
        if len(newName.strip()) == 0:
            return
        
        cursorNdx = self.selectCursorSpinBox.value()
        
        if cursorNdx != -1: #  spin box points ot a cursors => renames a landmark-based unit
            cursors = sorted([c for c in self._data_.scansCursors.values()], key = lambda x: x.x)
            
            obj = cursors[cursorNdx] # a PlanarGraphics landmark
            
            #print("cursor name %s -> new name %s" % (obj.name, newName))
            
            if newName != obj.name:
                u = self._data_.renameLandmark(obj, newName)
                
                if u is not None:
                    self._selected_analysis_unit_ = u
            
            self._selected_analysis_cursor_ = obj
            
        else: # spin box reads "none" => renaming the data-wide unit
            if newName != self._data_.analysisUnit().name:
                self._data_.renameAnalysisUnit(newName)
                self._selected_analysis_unit_ = None
                    
        self._update_analysis_unit_ui_fields_()
        
        self._data_.modified = True
        
        self.displayFrame()
        
    @Slot(float)
    @safeWrapper
    def slot_gui_changed_cursor_x_pos(self, value):
        if len(self._data_.scansCursors) == 0:
            return
        
        if self._selected_analysis_unit_ is None:
            if self._selected_analysis_cursor_ is None:
                return
        else:
            self._selected_analysis_cursor_ = self._selected_analysis_unit_.landmark
            
        # see NOTE: 2018-09-25 22:19:58
        signalBlockers = [QtCore.QSignalBlocker(w) for w in self.scansviewers + self.sceneviewers]

        if self._selected_analysis_cursor_ is not None:
            self._selected_analysis_cursor_.x = value
            #self._selected_analysis_cursor_.updateLinkedObjects() # called by PlanarGraphics.__setattr__()
            self._selected_analysis_cursor_.updateFrontends()
        
        self._data_.modified = True
        
        self.displayFrame()
        
    @Slot(float)
    @safeWrapper
    def slot_gui_changed_cursor_y_pos(self, value):
        if len(self._data_.scansCursors) == 0:
            return
        
        if self._selected_analysis_unit_ is None:
            if self._selected_analysis_cursor_ is None:
                return
        else:
            self._selected_analysis_cursor_ = self._selected_analysis_unit_.landmark
            
        # see NOTE: 2018-09-25 22:19:58
        signalBlockers = [QtCore.QSignalBlocker(w) for w in self.scansviewers + self.sceneviewers]
        
        if self._selected_analysis_cursor_ is not None:
            self._selected_analysis_cursor_.y = value
            self._selected_analysis_cursor_.updateFrontends()

        self._data_.modified = True
        
        self.displayFrame()
        
    @Slot(float)
    @safeWrapper
    def slot_gui_changed_cursor_xwindow(self, value):
        if len(self._data_.scansCursors) == 0:
            return
        
        if self._selected_analysis_unit_ is None:
            if self._selected_analysis_cursor_ is None:
                return
        else:
            self._selected_analysis_cursor_ = self._selected_analysis_unit_.landmark
            
        # see NOTE: 2018-09-25 22:19:58
        signalBlockers = [QtCore.QSignalBlocker(w) for w in self.scansviewers + self.sceneviewers]
        
        if self._selected_analysis_cursor_ is not None:
            self._selected_analysis_cursor_.xwindow = value
            self._selected_analysis_cursor_.updateFrontends()
        
        self._data_.modified = True
        
        self.displayFrame()
        
    @Slot(float)
    @safeWrapper
    def slot_gui_changed_cursor_ywindow(self, value):
        if len(self._data_.scansCursors) == 0:
            return
        
        if self._selected_analysis_unit_ is None:
            if self._selected_analysis_cursor_ is None:
                return
        else:
            self._selected_analysis_cursor_ = self._selected_analysis_unit_.landmark
            
        # see NOTE: 2018-09-25 22:19:58
        signalBlockers = [QtCore.QSignalBlocker(w) for w in self.scansviewers + self.sceneviewers]
        
        if self._selected_analysis_cursor_ is not None:
            self._selected_analysis_cursor_.ywindow = value
            self._selected_analysis_cursor_.updateFrontends()
        
        self._data_.modified = True
        
        self.displayFrame()
        
    #@Slot(object, int)
    @Slot(object)
    @safeWrapper
    def slot_graphics_object_added_in_window(self, obj):
        """Slot to be connected to image viewer window signals emitted when a 
        GraphicsObject has been created in window
        
        obj: a pictgui.GraphicsObject backend i.e., a pictgui.PlanarGraphics
        of type pictgui.Cursor, or a primitive such as Path, PathElements, 
        CurveElements, Tier2PathElements
            
        frame: index of the image frame where this cursor has been added
        
        NOTE: the image viewer window object itself is the sender of the signal
        ATTENTION: the GraphicsObject already exists in the sender window, we just 
        need to add its backend to the repository in lsdata.
        
        If _display_graphics_overlays_ is called, we run the risk of 
        creating duplicate GraphicsObject frontend for the same backend.
        
        """
        if self._data_ is None:
            return
        
        win = self.sender() # image window object that emitted the signal
        #print(win)
        #print(win.windowTitle())
        
        # NOTE: 2018-09-25 22:24:03
        # see NOTE: 2018-09-25 22:19:58
        signalBlockers = [QtCore.QSignalBlocker(w) for w in self.scansviewers + self.sceneviewers]
        
        if isinstance(obj, pgui.Cursor):
            setterfunc = self._data_.setCursor
        
        else:
            setterfrunc = self._data_.setRoi
        
        scans = win in self.scansviewers and not win in self.sceneviewers
        
        if len(obj.frameIndices) == 0:
            obj.frameIndices = [f for f in range(self._data_.scansFrames)]
        
        setterfunc(obj, scans=scans, append=True)
        
        # NOTE: 2018-09-25 22:24:47
        # figure out what has been added
        # if a vertical cursor has been added in the scans then create and map it to
        # a point cursor in the scene
        if scans:
            windows = self.scansviewers
            
        else:
            windows = self.sceneviewers
            
        for w in windows:
            if w != win:
                w.addPlanarGraphics(obj, labelShowsPosition=False)
                #w.addPlanarGraphics(obj, label=obj.name, labelShowsPosition=False)
        
        # by now, obj has at least one frontend
        for f in obj.frontends:
            f.labelShowsPosition = False
            f.setTransparentLabel(not self.actionOpaque_cursor_labels.isChecked())
            #f.setTransparentLabel(True)
                
        # NOTE: for vertical cursors, set up point cursors in the scene to map the linescan
        # cursor coordinate to the structure in the 2D scene
        
        # TODO the inverse: set up analysis ROIs in the scene the populate scans windows
        # with vertical cursors on the X coordinate -- do I really need this?
        
        if scans and isinstance(obj, pgui.Cursor) and obj.type == pgui.GraphicsObjectType.vertical_cursor:
            # NOTE: if a vertical cursor is added to the scans the we need to:
            # 1) create linked cursors in the scene, for visual feedback
            # 2) define an AnalysisUnit in lsdata
            
            # (1) create linked cursors in the scene, only if there is a scanline
            # trajectory defined there
            
            # NOTE: 2019-03-31 16:50:24
            # this is way too expensive so we make it optional
            if self.actionLink_vertical_scan_cursors_to_scene_point_cursors.isChecked():
                pc = self._link_scans_vcursor_to_scene_pcursor_(obj)
                
                # pc is the "mirror" point cursor in the scene
                if pc:
                    for w in self.sceneviewers:
                        if w != win:
                            pcobj = w.addPlanarGraphics(pc, label = pc.name,
                                                    labelShowsPosition=False)
                            
                            if (pcobj is not None):
                                pcobj.setTransparentLabel(not self.actionOpaque_cursor_labels.isChecked())
                                #pcobj.setTransparentLabel(True)
                    
        if self.selectCursorSpinBox.maximum() != len(self._data_.scansCursors)-1:
            self.selectCursorSpinBox.setRange(-1, len(self._data_.scansCursors)-1)
            
        cursorNames = sorted([k for k in self._data_.scansCursors.keys() if self._data_.scansCursors[k].type == pgui.GraphicsObjectType.vertical_cursor])
        
        # see NOTE: 2018-09-25 22:19:58
        sigBlock = QtCore.QSignalBlocker(self.selectCursorSpinBox)
        
        if len(cursorNames) and obj.name in cursorNames:
            self.selectCursorSpinBox.setValue(cursorNames.index(obj.name))

        self._data_.modified = True
        
        self.displayFrame()
        
        
    @Slot(object)
    @safeWrapper
    def slot_graphics_object_changed_in_window(self, obj):
        """Triggered by direct interaction with a GraphicsObject cursor.
        Direct interaction means either that cursor was modified by mouse action,
        or cursor properties have been edited through a dialog.
        
        Parameters:
        =========
        "obj" is a pictgui.PlanarGraphics, a backend to the GraphicsObject that
        the user interacted with (i.e., changed its properties via EditCursor dialog
        in an ImageViewer). 
        
        The GraphicsObject objects inherits from QtGraphics framework, and is a
        frontend to the "obj" PlanarGraphics, which is a pure Python object.
        
        By the time this slot is called, the attributes of "obj" such as name and 
        position have already been changed directly from its frontend.

        
        """
        # NOTE: 2019-03-10 09:39:18
        # this is connected to signal_graphicsObjectChanged emitted by the
        # window where the GraphicsObject has been manipulated
        # any direct manipulation of the GraphicsObject directly changes
        # the plaran descriptors of the PlanarGraphics to which the 
        # manipulated GraphicsObject serves as frontend
        # therefore there is no need to set anything here for the PlanarGraphics
        # "backend" EXCEPT when the name of the GraphicsObject has changed,
        # as this needs to be reflected in the ScanData dictionaries and analysis
        # unit(s)
        
        if self._data_ is None: # NOTE: this can never happen, can it?
            return
        
        win = self.sender()
        
        graphicsObjects = None
        
        if win in self.sceneviewers:
            scans = False

            if isinstance(obj, pgui.Cursor):
                graphicsObjects = self._data_.sceneCursors
                
            else:
                graphicsObjects = self._data_.sceneRois

            
        elif win in self.scansviewers:
            scans = True
            
            if isinstance(obj, pgui.Cursor):
                graphicsObjects = self._data_.scansCursors
                
            else:
                graphicsObjects = self._data_.scansRois
                
        else:
            return
        
        if graphicsObjects is None:
            return
        
        # see NOTE: 2018-09-25 22:19:58
        guiBlockers = [QtCore.QSignalBlocker(widget) for widget in self._analysis_unit_gui_widgets_]
        
        # see NOTE: 2018-09-25 22:19:58
        signalBlockers = [QtCore.QSignalBlocker(w) for w in self.scansviewers + self.sceneviewers]

        # NOTE: check for name change
        # NOTE: 2018-02-01 21:15:37 
        # object identity is given by its memory position
        objj = [(o_name, o_) for (o_name, o_) in graphicsObjects.items() if o_ == obj] # there should be only one such object
        
        new_name = obj.name
        #print("new_name", new_name)
        
        new_labelShowsPosition = any([f.labelShowsPosition] for f in obj.frontends)
        
        if len(objj):
            old_name = objj[0][0] # each objj is a tuple (object_name, object)
            #print("old_name", old_name)
            #print("old_cursor_name in scans %s" % old_name)
            if obj.name != old_name:                                            #  name change
                #print("gui cursor name changed %s -> %s" % (old_name, new_name))
                # NOTE: 2019-03-17 10:44:54
                # because the landmark has already been renamed:
                # 1) calling lsdata.renameLandmark will have no effect
                #
                # 2) calling lsdata.renameAnalysisUnit will rename the unit but
                # leave the landmark alone
                # 
                # the consequence is that the lsdata landmarks dictionaries won't 
                # be updated by any of the above functions so we need to do that 
                # manually, here:
                lnd = graphicsObjects.pop(old_name, None)
                graphicsObjects[obj.name] = obj
                
                #for f in obj.frontends:
                    #if f.ID != obj.name:
                        #f_old_name = f.ID
                        #f.ID = obj.name
                        #cDict = f.parentwidget.viewerwidget._graphicsObjects[f.objectType]
                        #cDict.pop(f_olf_name, None)
                        #cDict[fID] = f
                
                # now we can call renameAnalysisUnit
                # is there an analysis unit associated with this landmark?
                landmark_units = [u for u in self._data_.analysisUnits]
                
                if obj in [u.landmark for u in self._data_.analysisUnits]:
                    units = [u for u in self._data_.analysisUnits if u.landmark == obj]
                    if len(units):
                        self._data_.renameAnalysisUnit(obj.name, units[0])
                        
                else:
                    self._data_.renameLandmark(obj)
                    
                self.displayFrame()
                
            else:
                landmark_units = [u for u in self._data_.analysisUnits]
                
                if obj in [u.landmark for u in self._data_.analysisUnits]:
                    units = [u for u in self._data_.analysisUnits if u.landmark == obj]
                    if len(units):
                        if len(obj.frameIndices):
                            for frame_ndx in obj.frameIndices:
                                for p in self._data_.triggers:
                                    if frame_ndx in p.segmentIndices():
                                        if p not in units[0].protocols:
                                            units[0].protocols.append(p)
                                            
                        else:
                            units[0].protocols[:] = self._data_.triggers
                                    
                        #self._data_.renameAnalysisUnit(obj.name, units[0])
                        
                
                    
        self._data_.modified = True
                
        self.displayFrame()
        
    @Slot()
    def slot_toggle_opaque_cursor_labels(self):
        if self._data_ is None:
            return
        
        opaque = self.actionOpaque_cursor_labels.isChecked()
        
        objects = [o for o in self._data_.sceneCursors.values()] + \
                  [o for o in self._data_.sceneRois.values()] + \
                  [o for o in self._data_.scansCursors.values()] + \
                  [o for o in self._data_.scansRois.values()]
              
        for o in objects:
            for f in o.frontends:
                f.setTransparentLabel(not opaque)
            #__internal_set_opaque_label__(o, opaque)
            
    @Slot()
    #@safeWrapper
    def slot_graphics_objects_deselected(self):
        if self._data_ is None:
            return
        
        # here NO graphics is selected; update the values in the Analysis Unit
        # groupbox (GUI) where relevant
        
        win = self.sender()
        
        # see NOTE: 2018-09-25 22:19:58
        signalBlockers = [QtCore.QSignalBlocker(w) for w in self.scansviewers + self.sceneviewers]

        try:
            for w in self.sceneviewers + self.scansviewers:
                if w != win:
                    w.viewerWidget.slot_setSelectedCursor("", False)
                    w.viewerWidget.slot_setSelectedRoi("", False)
                    
                    for c in w.cursors:
                        for f in c.frontends:
                            f.setSelected(False)
                            f.redraw()
                        
                    for r in w.rois:
                        for f in r.frontends:
                            f.setSelected(False)
                            f.redraw()
                    
            self._selected_analysis_cursor_ = None
            self._selected_analysis_unit_ = None
            
        except Exception as e:
            traceback.print_exc()
    
        self._update_analysis_unit_ui_fields_()
        
    #@Slot(object, int)
    @Slot(object)
    #@safeWrapper
    def slot_graphics_object_selected_in_window(self, obj):
        if self._data_ is None:
            return
        
        win = self.sender()
        
        # see NOTE: 2018-09-25 22:19:58
        signalBlockers = [QtCore.QSignalBlocker(w) for w in self.scansviewers + self.sceneviewers]
        
        try:
            rois = not isinstance(obj, pgui.Cursor)
            
            scene = win in self.sceneviewers and not win in self.scansviewers
            
            # deal with the possibility that the selected graphics object is part
            # of an analysis unit defined in lsdata
            # here we only deal with vertical cursors in the linescans
            if len(obj.frontends):
                for f in obj.frontends:
                    if rois:
                        if f not in win.rois:
                        #if f not in win.rois.values():
                            f.setSelected(True)
                            f.redraw()
                    else:
                        #if f not in win.cursors.values():
                        if f not in win.cursors:
                            f.setSelected(True)
                            f.redraw()
                    
            if len(obj.linkedObjects):
                for l in obj.linkedObjects:
                    for f in l.frontends:
                        f.setSelected(True)
                        f.redraw()
            
            if not rois and obj.type == pgui.GraphicsObjectType.vertical_cursor:
                # deal only with Cursor type and in scans only
                # NOTE: when a cursor is selected, unit type reflects what is
                # being selected
                # when no cursor is selected (or no cursor exists)
                # unit type is the one defined by the scandata
                self._selected_analysis_unit_ = None
                self._selected_analysis_cursor_ = None
                
                cursors = sorted([c for c in self._data_.scansCursors.values() if c.type == obj.type and c.hasStateForFrame(self.currentFrame)], key = lambda x:x.x)
                #cursors = sorted([c for c in self._data_.scansCursors.values() if c.type == obj.type and c.hasStateForFrame(self.currentFrame)], key = lambda x:x.x)
                cursor_names = [c.name for c in cursors]
                
                unit_names = sorted([u.landmark.name for u in self._data_.analysisUnits])
                
                if obj.name in cursor_names:
                    self._selected_analysis_cursor_ = obj
                    
                    if obj.name in unit_names:
                        self._selected_analysis_unit_ = self._data_.analysisUnit(obj.name)
                        
                    else:
                        self._selected_analysis_unit_ = None
                        
                else:
                    self._selected_analysis_cursor_ = None
            
        except Exception as e:
            traceback.print_exc()
            
        self._update_analysis_unit_ui_fields_()
            
    #@Slot(object, int)
    @Slot(object)
    #@safeWrapper
    def slot_graphics_object_removed_in_window(self, obj):
        if self._data_ is None:
            return
        
        win = self.sender()
        
        #print("LSCaTWindow.slot_graphics_object_removed_in_window %s type %s in %s" % (obj.name, obj.type, win.windowTitle()))
        
        # see NOTE: 2018-09-25 22:19:58
        signalBlockers = [QtCore.QSignalBlocker(w) for w in self.scansviewers + self.sceneviewers]

        rois = not isinstance(obj, pgui.Cursor)
        
        scene = win in self.sceneviewers
        
        try:
            if win in self.scansviewers:
                if rois:
                    self._data_.removeRoi(obj.name, scans=True)
                    
                else:
                    self._data_.removeCursor(obj.name, scans=True)
                    
                    # also remove the corresponding analysis unit, if defined
                    #if obj.type == pgui.GraphicsObjectType.vertical_cursor:
                        ## keep the landmark because we're removing it manually, below
                        #self._data_.removeAnalysisUnit(obj, removeLandmark=False) 
                        
                    
            elif win in self.sceneviewers:
                if rois:
                    self._data_.removeRoi(obj.name, scans=False)
                    
                else:
                    self._data_.removeCursor(obj.name, scans=False)
                    
            if len(obj.linkedObjects):
                for linked_obj in obj.linkedObjects:
                    if linked_obj in self._data_.scansRois.values():
                        self._data_.removeRoi(linked_obj.name, scans=True)
                        ww = self.scansviewers
                        
                    elif linked_obj in self._data_.sceneRois.values():
                        self._data_.removeRoi(linked_obj.name, scans=False)
                        ww = self.sceneviewers
                        
                    elif linked_obj in self._data_.scansCursors.values():
                        self._data_.removeCursor(linked_obj.name, scans=True)
                        ww = self.scansviewers
                        
                    elif linked_obj in self._data_.sceneCursors.values():
                        self._data_.removeCursor(linked_obj.name, scans=False)
                        ww = self.sceneviewers
                        
                    else:
                        ww = None
                        
                    if ww is not None:
                        for w in ww:
                            if w != win:
                                w.removeGraphicsObject(linked_obj.name)
                                
            unit = self._data_.analysisUnit(obj.name)
            
            #self._data_.removeAnalysisUnit(obj, removeLandmark=False) 
            
            if unit is not None:
                self._data_.removeAnalysisUnit(obj.name, removeLandmark=False)
                
        except Exception as e:
            traceback.print_exc()
            
        self._selected_analysis_cursor_ = None
        self._selected_analysis_unit_ = None
        
        self._data_.modified = True
        self._update_analysis_unit_ui_fields_()
        self.displayFrame()
    
    @Slot(int)
    @Slot(float)
    @safeWrapper
    def slot_filterParamChanged(self, value):
        if self._data_ is None:
            return
        
        #print("slot_filterParamChanged: %s" % value)
        # distinguish values here
        # purelet scene reference channel
        if self.sender() == self.pureletAlphaSceneRefDoubleSpinBox:
            self.defaultPureletFilterOptions.scene.ref.alpha = value
            
        elif self.sender() == self.pureletBetaSceneRefDoubleSpinBox:
            self.defaultPureletFilterOptions.scene.ref.beta =value
            
        elif self.sender() == self.pureletSigmaSceneRefDoubleSpinBox:
            self.defaultPureletFilterOptions.scene.ref.sigma =value
            
        elif self.sender() == self.pureletJSceneRefSpinBox:
            self.defaultPureletFilterOptions.scene.ref.j =value
            
        elif self.sender() == self.pureletTSceneRefSpinBox:
            self.defaultPureletFilterOptions.scene.ref.t =value
            
        # purelet scene indicator channel
        elif self.sender() == self.pureletAlphaSceneIndDoubleSpinBox:
            self.defaultPureletFilterOptions.scene.ind.alpha = value
            
        elif self.sender() == self.pureletBetaSceneIndDoubleSpinBox:
            self.defaultPureletFilterOptions.scene.ind.beta =value
            
        elif self.sender() == self.pureletSigmaSceneIndDoubleSpinBox:
            self.defaultPureletFilterOptions.scene.ind.sigma =value
            
        elif self.sender() == self.pureletJSceneIndSpinBox:
            self.defaultPureletFilterOptions.scene.ind.j =value
            
        elif self.sender() == self.pureletTSceneIndSpinBox:
            self.defaultPureletFilterOptions.scene.ind.t =value
            
        # purelet scans reference channel
        elif self.sender() == self.pureletAlphaScansRefDoubleSpinBox:
            self.defaultPureletFilterOptions.scans.ref.alpha = value
            
        elif self.sender() == self.pureletBetaScansRefDoubleSpinBox:
            self.defaultPureletFilterOptions.scans.ref.beta =value
            
        elif self.sender() == self.pureletSigmaScansRefDoubleSpinBox:
            self.defaultPureletFilterOptions.scans.ref.sigma =value
            
        elif self.sender() == self.pureletJScansRefSpinBox:
            self.defaultPureletFilterOptions.scans.ref.j =value
            
        elif self.sender() == self.pureletTScansRefSpinBox:
            self.defaultPureletFilterOptions.scans.ref.t =value
            
        # purelet scans indicator channel
        elif self.sender() == self.pureletAlphaScansIndDoubleSpinBox:
            self.defaultPureletFilterOptions.scans.ind.alpha = value
            
        elif self.sender() == self.pureletBetaScansIndDoubleSpinBox:
            self.defaultPureletFilterOptions.scans.ind.beta =value
            
        elif self.sender() == self.pureletSigmaScansIndDoubleSpinBox:
            self.defaultPureletFilterOptions.scans.ind.sigma =value
            
        elif self.sender() == self.pureletJScansIndSpinBox:
            self.defaultPureletFilterOptions.scans.ind.j =value
            
        elif self.sender() == self.pureletTScansIndSpinBox:
            self.defaultPureletFilterOptions.scans.ind.t =value
            
        # gaussian filters
        elif self.sender() == self.gaussianSigmaSceneRefDoubleSpinBox:
            self.defaultGaussianFilterOptions.scene.ref.sigma=value
            
        elif self.sender() == self.gaussianSizeSceneRefSpinBox:
            self.defaultGaussianFilterOptions.scene.ref.size=value
            
        elif self.sender() == self.gaussianSigmaSceneIndDoubleSpinBox:
            self.defaultGaussianFilterOptions.scene.ind.sigma=value
            
        elif self.sender() == self.gaussianSizeSceneIndSpinBox:
            self.defaultGaussianFilterOptions.scene.ind.size=value
            
        elif self.sender() == self.gaussianSigmaScansRefDoubleSpinBox:
            self.defaultGaussianFilterOptions.scans.ref.sigma=value
            
        elif self.sender() == self.gaussianSizeScansRefSpinBox:
            self.defaultGaussianFilterOptions.scene.ref.size=value
            
        elif self.sender() == self.gaussianSigmaScansIndDoubleSpinBox:
            self.defaultGaussianFilterOptions.scans.ind.sigma=value
            
        elif self.sender() == self.gaussianSizeScansIndSpinBox:
            self.defaultGaussianFilterOptions.scans.ind.size=value
            
        # binomial filters
        elif self.sender() == self.binomialOrderSceneRefSpinBox:
            self.defaultBinomialFilterOptions.scene.ref.radius = value
            
        elif self.sender() == self.binomialOrderSceneIndSpinBox:
            self.defaultBinomialFilterOptions.scene.ind.radius = value
            
        elif self.sender() == self.binomialOrderScansRefSpinBox:
            self.defaultBinomialFilterOptions.scans.ref.radius = value
            
        elif self.sender() == self.binomialOrderScansIndSpinBox:
            self.defaultBinomialFilterOptions.scand.ind.radius = value
            
        self.generateFilters()
        self._data_.modified=True
        self.displayFrame()
            
    @Slot()
    @safeWrapper
    def slot_previewFilter(self): # TODO
        if self._data_ is None:
            return
        
        if self.sender() == self.previewGaussianSceneRefBtn:
            pass
        
        elif self.sender() == self.previewGaussianSceneIndBtn:
            pass
        
        elif self.sender() == self.previewGaussianScansRefBtn:
            pass
        
        elif self.sender() == self.previewGaussianScansIndBtn:
            pass
        
        elif self.sender() == self.previewBinomialSceneRefBtn:
            pass
        
        elif self.sender() == self.previewBinomialSceneIndBtn:
            pass
        
        elif self.sender() == self.previewBinomialScansRefBtn:
            pass
        
        elif self.sender() == self.previewBinomialScansIndBtn:
            pass
            
            
    @Slot()
    def slot_removeUncagingArtifact(self):
        if self._data_ is None:
            return
        
        if len(self._data_.triggers) == 0:
            return
        
        for protocol in self._data_.triggers:
            if protocol.photostimulation is not None and protocol.imagingDelay is not None:
                times = protocol.photostimulation.times - protocol.imagingDelay
                frames = protocol.segmentIndex
                
                bstart = self.artifactBackgroundBeginDoubleSpinBox.value()
                bend = self.artifactBackgroundEndDoubleSpinBox.value()
                width = self.uncagingArtifactWidth_spinBox.value()
                
                bgstart = min([bstart, bend])
                bgstop = max([bstart, bend])
                
                for frame in frames:
                    blankUncageArtifactInLineScans(self._data_, times, width, bgstart, bgstop, frame)
                    
        self._display_scans_()
                
    
    @Slot()
    @safeWrapper
    def slot_pickleLSData(self):
        if self._data_ is None:
            return
        
        if len(self._data_var_name_) == 0:
            bname = "scandata"
            
        else:
            bname = self._data_var_name_
            
        #targetDir = self._scipyenWindow_.recentDirectories[0]
        targetDir = self._scipyenWindow_.currentDir
        
        fileFilter = "Pickle files (*.pkl)"
            

        if sys.platform == "win32":
            options = QtWidgets.QFileDialog.Option.DontUseNativeDialog
            kw = {"options":options}
        else:
            kw = {}

        if targetDir is not None and targetDir != "" and os.path.exists(targetDir):
            fName, _ = QtWidgets.QFileDialog.getSaveFileName(self, 
                                                          caption="Save scan data", 
                                                          filter=fileFilter, 
                                                          directory=targetDir, **kw)
            
        else:
            fName, _ = QtWidgets.QFileDialog.getSaveFileName(self, 
                                                          caption="Save scan data", 
                                                          filter=fileFilter, **kw)
            
        if len(fName) > 0:
            newVarName, ext = os.path.splitext(os.path.basename(fName))
            
            if len(ext) == 0:
                fName+=".pkl"
                
            self._data_.modified = False
            
            pio.savePickleFile(self._data_, fName)
            
            self._update_ui_fields_()
            
            try:
                if newVarName != self._data_var_name_:
                    newVarNameOK = validate_varname(newVarName, self._scipyenWindow_.workspace)
                    
                    if self._data_var_name_ != newVarNameOK:
                        self._scipyenWindow_.assignToWorkspace(newVarNameOK, self._data_)
                        self._data_var_name_ = newVarNameOK

            except Exception as e:
                traceback.print_exc()
                
            self._data_.modified=False
            self.displayFrame()
                
    @Slot()
    @safeWrapper
    def slot_exportCopyToWorkspace(self):
        if self._data_ is None:
            return
        
        if len(self._data_var_name_) == 0:
            bname = "scandata"
            
        else:
            bname = self._data_var_name_
            
        newVarName = validate_varname(bname, self._scipyenWindow_.workspace)
        
        dlg = qd.QuickDialog(self, "Export data copy to workspace")
        namePrompt = qd.StringInput(dlg, "Export data as:")
        
        namePrompt.variable.setClearButtonEnabled(True)
        namePrompt.variable.redoAvailable=True
        namePrompt.variable.undoAvailable=True
        
        namePrompt.setText(newVarName)
        
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            newVarName = validate_varname(namePrompt.text(), self._scipyenWindow_.workspace)
            
            self._scipyenWindow_.assignToWorkspace(newVarName, self._data_)
            
            self._data_.modified=False
            self.displayFrame()
            
            self.statusBar().showMessage("Done!")
        
    @Slot(int)
    @safeWrapper
    def slot_filterPageSelectionChanged(self, value):
        if self._data_ is None:
            return
        
        if self.sender() == self.sceneFiltersComboBox:
            if value > 0:
                self.sceneFiltersConfigStackedWidget.setCurrentIndex(value-1)
                
            else:
                self.sceneFiltersConfigStackedWidget.setCurrentIndex(0)
                
        elif self.sender() == self.scanFiltersComboBox:
            if value > 0:
                self.scanFiltersConfigStackedWidget.setCurrentIndex(value-1)
                
            else:
                self.scanFiltersConfigStackedWidget.setCurrentIndex(0)
        self.generateFilters()
                
    @Slot(int)
    @safeWrapper
    def slot_displayFramesWithProtocol(self, val):
        if self._data_ is None:
            return
        
        self.displaySelectFrames()

    @Slot(int)
    @safeWrapper
    def slot_splineInterpolatorOrderChanged(self, val):
        self.scanline_spline_order = val
        if self._data_ is not None:
            self._data_.generateScanRegionProfiles()
            
            self._display_scanline_profiles_()
            
            
    @Slot(int)
    @safeWrapper
    def slot_showScanlineProfiles(self, val):
        if self._data_ is None:
            return
        
        if val > 0:
            self._display_graphics_objects_(rois=True,  scene=True) 
                    
            if len(self._data_.scanRegionScansProfiles.segments) == 0:
                self._data_.generateScanlineProfilesFromScans()
                
            if len(self._data_.scanRegionSceneProfiles.segments) == 0:
                self._data_.generateScanlineProfilesFromScene()
                
            self._display_scanline_profiles_()
                
        else:
            for frame in range(self._data_.sceneFrames):
                for win in self.sceneviewers:
                    if win.hasRoi("scanline_%d" % frame):
                        win.removeRoi("scanline_%d" % frame)
            
            if len(self.profileviewers) > 0:
                self.profileviewers[0].clear()
                self.profileviewers[0].close()
                
        self._update_ui_fields_()
                
    @Slot()
    @safeWrapper
    def slot_enterWhatsThisMode(self):
        QtWidgets.QWhatsThis.enterWhatsThisMode()
        
    @Slot(int)
    @safeWrapper
    def _slot_frameChangedInChildViewer(self, value):
        """Captures frame index change in the child viewer
        Parameters:
        ===========
        value:int, index of the newly displayed frame in the viewer.
        This will be used to get the master index frame in the ScanData 
        'framesMap' attribute.
        """
        viewer = self.sender()
        winTitle = viewer.windowTitle().lower()
        
        childViewers = list(w for w in self.scansviewers + self.sceneviewers + self.ephysviewers + self.profileviewers + self.scansblockviewers + self.sceneblockviewers if w is not viewer)
        signalBlockers = [QtCore.QSignalBlocker(w) for w in childViewers]
        
        if "profile" in winTitle:
            self.currentFrame = value
            
            for win in self.sceneviewers + self.sceneblockviewers:
                frindex = self._data_.framesMap["scene"][self.currentFrame]
                win.currentFrame = frindex
        
            for win in self.scansviewers + self.scansblockviewers:
                frindex = self._data_.framesMap["scans"][self.currentFrame]
                win.currentFrame = frindex
                
            for win in self.ephysviewers:
                frindex = self._data_.framesMap["electrophysiology"][self.currentFrame]
                win.currentFrame = frindex
                
        else:
            if "scans" in winTitle:
                self.currentFrame = self._data_.framesMap.where("scans", value)
                
                for win in self.scansviewers + self.scansblockviewers:
                    if win is not viewer:
                        win.currentFrame = value
                        
                for win in self.sceneviewers + self.sceneblockviewers:
                    frindex = self._data_.framesMap["scene"][self.currentFrame]
                    win.currentFrame = frindex
                    
                for win in self.ephysviewers:
                    frindex = self._data_.framesMap["electrophysiology"][self.currentFrame]
                    win.currentFrame = frindex
                    
            elif "scene" in winTitle:
                for win in self.sceneviewers + self.sceneblockviewers:
                    if win is not viewer:
                        win.currentFrame = value
                
                self.currentFrame = self._data_.framesMap.where("scene", value)
                
                for win in self.scansviewers + self.scansblockviewers:
                    frindex = self._data_.framesMap["scans"][self.currentFrame]
                    win.currentFrame = frindex
                
                for win in self.ephysviewers:
                    frindex = self._data_.framesMap["electrophysiology"][self.currentFrame]
                    win.currentFrame = frindex
                    
            elif "electrophysiology" in winTitle:
                self.currentFrame = self._data_.framesMap.where("electrophysiology", value)
                
                for win in self.sceneviewers + self.sceneblockviewers:
                    frindex = self._data_.framesMap["scene"][self.currentFrame]
                    win.currentFrame = frindex
            
                for win in self.scansviewers + self.scansblockviewers:
                    frindex = self._data_.framesMap["scans"][self.currentFrame]
                    win.currentFrame = frindex
                    
    @Slot(int)
    @safeWrapper
    def slot_setFrameNumber(self, value):
        """Connected to frameQSlider or framesQSpinBox signals.
        """

        # NOTE: 2022-01-16 13:14:04
        # Broadcasts a corresponding frame index to the child data viewers
        # according to the FrameIndexLookup in self._data_.framesMap.
        # The child window may be showing a data with fewer frames than the
        # master frames index (see ScanData.framesMap property).
        # This slot takes care of this by selecting the corresponding master 
        # frame index in ScanData.
        # ATTENTION: LSCaTWindow frame navigation widgets ONLY deal with master 
        # frame indices.
        
        if self._data_ is None:
            return
        
        if value in range(0, self._data_.nFrames()):
            self._current_frame_index_ = value
        else:
            return
            
        # NOTE: 2022-01-16 13:20:04
        # Data frame mismatches are now ALLOWED between the primary data components
        # of the ScanData objects: scans, scene, and electrophysiology; therefore
        # the child viewers that display these components (respectively, 
        # scansviewers, sceneviewers, and ephysviewers) need to be sent a frame 
        # index value that is appropriate to the layout of the specific data
        # component.
        #
        # In addition, scansblockviewers, sceneblockviewers, and profileviewers
        # display data derived from these three primary data components, hence
        # their frame layout reflects that of the source primary data component
        # as follows:
        #
        # scansblockviewers <-> scansFrames
        # sceneblockviewers <-> sceneFrames
        # profileviewers    <-> master frames (each frame shows the scan 
        # trajectory profile simultaneously in scans and scene, or in one of
        # them if the other does not have a corresponding frame.
        
        childViewers = self.scansviewers + self.sceneviewers + self.ephysviewers + self.profileviewers + self.scansblockviewers + self.sceneblockviewers
        
        signalBlockers = [QtCore.QSignalBlocker(w) for w in childViewers]
        
        try:
            # NOTE: 2022-01-17 16:58:52 see # NOTE: 2022-01-17 16:57:06
            for viewer in self.scansviewers + self.scansblockviewers:
                frindex = self._data_.framesMap["scans"][value]
                viewer.currentFrame = frindex
                
            for viewer in self.sceneviewers + self.sceneblockviewers:
                frindex = self._data_.framesMap["scene"][value]
                viewer.currentFrame = frindex
                
            for viewer in self.ephysviewers:
                frindex = self._data_.framesMap["electrophysiology"][value]
                viewer.currentFrame = frindex
                
            for viewer in self.profileviewers: 
                # TODO: 2022-01-17 17:01:51
                # include results window here? - it is NOT a ScipyenFrameViewer!
                viewer.currentFrame = value # this should also change currentFrame in that window's graphics objects
                
            landmarks = [o for o in self._data_.sceneRois.values()]     + \
                        [o for o in self._data_.sceneCursors.values()]  + \
                        [o for o in self._data_.scansRois.values()]     + \
                        [o for o in self._data_.scansCursors.values()]  + \
                        [self._data_.scanRegion]
            
            for landmark in landmarks:
                if landmark is not None:
                    landmark.currentFrame = self._current_frame_index_
                    landmark.updateLinkedObjects()
                    landmark.updateFrontends()
                
            self._update_analysis_unit_ui_fields_()
            
            if self.sender() == self.framesQSpinBox:
                sigBlock = QtCore.QSignalBlocker(self.frameQSlider)
                self.frameQSlider.setValue(int(self._current_frame_index_))
                
            elif self.sender() == self.frameQSlider:
                sigBlock = QtCore.QSignalBlocker(self.framesQSpinBox)
                self.framesQSpinBox.setValue(int(self._current_frame_index_))
            
        except Exception as e:
            traceback.print_exc()
            
    @Slot()
    @safeWrapper
    def slot_setupLinescanCursorsInSpecifiedFrames(self):
        if self._data_ is None:
            return
        
        if len(self._data_.scanRegionScansProfiles.segments) == self._data_.scansFrames:
            for frame in range(self._data_.scansFrames):
                self.autoSetupLinescanCursorsInFrame(frame, displayFrame=False)
        
            self._display_graphics_objects_(rois=False, scene=False)
            
        else:
            warnings.warn("Mismatch between the number of segments in scanline profiles block and the number of scans frame. \nMost likely you need to generate profiles for all linescan frames first!")
    
        self._data_.modified=True
        self.displayFrame()
            
    @Slot()
    @safeWrapper
    def slot_setupLinescanCursorsInCurrentFrame(self):
        if self._data_ is None:
            return
        
        self.autoSetupLinescanCursorsInFrame(self.currentScanFrame)
            
        self._data_.modified=True
        self.displayFrame()
            
    @Slot(int)
    @safeWrapper
    def slot_scanDisplayChannelChanged(self, value):
        if self._data_ is None:
            return
        
        data = self._data_.scans # this is a reference, not a copy, unless you mod it!
        
        if len(data) > 1: # several single-band arrays
            if value in (-1, 0): # no current index or current index is 0 i.e. "All channels"
                # display everything in "what"
                self._displayed_scan_channels_ = self._data_.scansChannelNames
                
                for (k,win) in enumerate(self.scansviewers):
                    win.view(data[k])
                    win.setVisible(True)
                    
            elif value > len(data):
                # "Select... was chosen"
                # TODO: pop up dialog to select displayed channels
                #store in a configuration structure
                
                self._displayed_scan_channels_ = self._selectDisplayChannels_(False)
                self._displayChannels_(False, self._displayed_scan_channels_)

            else:
                for(k, win) in enumerate(self.scansviewers):
                    win.setVisible(k == value-1)
                    if k == value-1:
                        win.view(data[k])
                        self._displayed_scene_channels_ = [self._data_.scansChannelNames[k]]
                        
    @Slot(int)
    @safeWrapper
    def slot_sceneDisplayChannelChanged(self, value):
        """When scene is a sequence of single-band data, send this to the display.
        
        NOTE: index 0 means display ALL channels!
        """
        if self._data_ is None:
            return
        
        data = self._data_.scene # this is a reference, not a copy, unless you mod it!
        
        if len(data) > 1: # several single-band arrays
            if value in (-1, 0):
                self._displayed_scene_channels_ = self._data_.sceneChannelNames
                
                for (k,win) in enumerate(self.sceneviewers):
                    win.view(data[k])
                    win.setVisible(True)
                    
            elif value > len(data):
                self._displayed_scan_channels_ = self._selectDisplayChannels_()
                self._displayChannels_(True, self._displayed_scan_channels_)
                    
            else:
                for(k, win) in enumerate(self.sceneviewers):
                    win.setVisible(k == value-1)
                    if k == value-1:
                        win.view(data[k])
                        self._displayed_scene_channels_ = [self._data_.sceneChannelNames[k]]
                    
    @Slot()
    @safeWrapper
    def slot_loadWorkspaceScanData(self):
        
        if isinstance(self._data_, ScanData) and len(self._data_.name.strip()):
            preSel = self._data_.name
            
        else:
            preSel = None
        
        lsdata_vars = self.importWorkspaceData(dataTypes = ScanData,
                                               title="Load ScanData Object",
                                               single=True,
                                               preSelected=preSel,
                                               with_varName=True)
        
        if len(lsdata_vars) == 0:
            return
        
        lsdata_varname, lsdata = lsdata_vars[0]
        
        self.setData(newdata = lsdata, doc_title = lsdata_varname)
        
    @Slot()
    def slot_baseScipyenDataChanged(self):
        if self._data_ is None:
            return
        
        if not eq(self._data_.name, self.baseScipyenDataWidget.dataName):
            self._data_.name = self.baseScipyenDataWidget.dataName
            self._data_modifed_(True)
            
        if not eq(self._data_.sourceID, self.baseScipyenDataWidget.sourceID):
            # avoid pitfalls of pandas NAType
            self._data_.sourceID = self.baseScipyenDataWidget.sourceID
            self._data_modifed_(True)
            
        if not eq(self._data_.cell, self.baseScipyenDataWidget.cell):
            self._data_.cell = self.baseScipyenDataWidget.cell
            self._data_modifed_(True)
            
        if not eq (self._data_.field, self.baseScipyenDataWidget.field):
            self._data_.field = self.baseScipyenDataWidget.field
            self._data_modifed_(True)
            
        if not eq(self._data_.genotype, self.baseScipyenDataWidget.genotype):
            self._data_.genotype = self.baseScipyenDataWidget.genotype
            self._data_modifed_(True)
            
        if not eq(self._data_.sex, self.baseScipyenDataWidget.sex):
            self._data_.sex = self.baseScipyenDataWidget.sex
            self._data_modifed_(True)
            
        if not eq(self._data_.age, self.baseScipyenDataWidget.age):
            self._data_.age = self.baseScipyenDataWidget.age
            self._data_modifed_(True)

    @Slot()
    @safeWrapper
    def slot_setDataName(self):
        
        value = strutils.str2symbol(self.scanDataNameLineEdit.text())
        
        if len(value.strip()) == 0:
            return
        
        # see NOTE: 2018-09-25 22:19:58
        sigBlock = QtCore.QSignalBlocker(self.scanDataNameLineEdit)
        
        if self._data_.name != value:
            self._data_.name = value
            self._data_.modified = True
            self.scanDataVarNameLabel.setText(self._data_var_name_)
            
            if self._data_.modified:
                self.setWindowTitle("%s * \u2014 LSCaT" % (self._data_var_name_))
                
            else:
                self.setWindowTitle("%s \u2014 LSCaT" % (self._data_var_name_))
                
            
            #self.scanDataNameLineEdit.editingFinished.disconnect(self.slot_setDataName)
            self.scanDataNameLineEdit.setText(self._data_.name)
            #self.scanDataNameLineEdit.editingFinished.connect(self.slot_setDataName, type = QtCore.Qt.QueuedConnection)
            self._update_report_()
        
            
            #self.statusBar().showMessage("Done!")
            
    @safeWrapper
    def _check_for_linescan_data_(self, data):
        try:
            if not check_apiversion(data) and hasattr(data, "_upgrade_API_"):
                data._upgrade_API_()
                
            return data._scandatatype_ == ScanData.ScanDataType.linescan and data._analysismode_ == ScanData.ScanDataAnalysisMode.frame
        
        except Exception as e:
            traceback.print_exc()
            return False
        
    def _init_viewer_(self, winFactory, configTag, winSetup, winTitle, docTitle, nFrames):
        #print(f"{self.__class__.__name__}._init_viewer_: winFactory = {winFactory}")
        # win = winFactory(win_title=winTitle, doc_title=docTitle, parent=self, configTag=configTag)
        win = winFactory(win_title=winTitle, doc_title=docTitle, appWindow=self, configTag=configTag)
        #print(f"{self.__class__.__name__}._init_viewer_: win = {win}")
        #print(f"{self.__class__.__name__}._init_viewer_: winSetup = {winSetup}")
        if inspect.isfunction(winSetup):
            winSetup(self)
            
        if isinstance(win, ScipyenFrameViewer):
            if getattr(win, "framesSlider", None) is not None:
                win.framesSlider.setMaximum(nFrames)
                
            if getattr(win, "framesSpinner", None) is not None:
                win.framesSpinner.setMaximum(nFrames)
            
        return win
    
    def _update_viewer_(self, win, winTag, winTitle, docTitle, nFrames):
        win.configTag = winTag
        win.winTitle = winTitle
        win.docTitle = docTitle
        
        if isinstance(win, ScipyenFrameViewer):
            if getattr(win, "framesSlider", None) is not None:
                win.framesSlider.setMaximum(nFrames)
                
            if getattr(win, "framesSpinner", None) is not None:
                win.framesSpinner.setMaximum(nFrames)
        
    @safeWrapper
    def _init_data_viewers_(self, section:str):
        """Sets up the viewer(s) for a specific ScanData section
        Parameters:
        ==========
        section: str, one of: 
            "electrophysiology" "ephys", "scansProfiles", "sceneProfiles", 
            "scansBlock", "sceneBlock", "scans", "scene"
            
            Of these, the last two are lists of VigraArray objects; the others
            are neo.Block.
            
        NOTE: For the given data component ('section') calls self._init_viewer_
        if no corresponding viewer has been initialized, otherwise, calls
        self._update_viewer_.
        """
        wname, viewers, winFactory, winSetup = self._get_viewers_for_data_section(section)
        
        if any((v is None for v in (wname, viewers))):
            return
        
        nFrames = self._get_data_section_frames_(section)
        
        data = getattr(self._data_, section, None)
        
        if isinstance(data, list) and len(data) and all(isinstance(d, vigra.VigraArray) for d in data):
            #print(f"LSCaT _init_data_viewers_ {section}")
            if len(viewers) > len(data):
                # close & discard excess image viewers
                for w in viewers[len(data):]:
                    w.unlinkFromViewers()
                    w.close()
                    
                viewers = viewers[0:len(data)]
                
            for k in range(len(data)):
                winTag = f"{section}_{self._data_.scansChannelNames[k]}"
                winTitle = f"{wname} {self._data_.scansChannelNames[k]}"
                docTitle = f"{self._data_var_name_}"
                if k >= len(viewers):
                    # create new image viewer as needed
                    win = self._init_viewer_(winFactory, winTag, winSetup, winTitle, docTitle, nFrames)
                    win.signal_graphicsObjectAdded[object].connect(self.slot_graphics_object_added_in_window)
                    win.frameChanged.connect(self._slot_frameChangedInChildViewer)
                    viewers.append(win)
                else:
                    # clear the contents of the current image viewer
                    win = viewers[k]
                    win.unlinkFromViewers()
                    win.clear()
                    self._update_viewer_(win, winTag, winTitle, docTitle, nFrames)
                    
                win.view(data[k], get_focus=False)
                
        elif isinstance(data, neo.Block) and not neoutils.is_empty(data, ignore=(neo.Event, TriggerEvent, neo.Epoch)):
            #print(f"{self.__class__.__name__}._init_data_viewers_ {section}")
            winTag = f"{section}"
            winTitle = f"{wname}"
            docTitle = f"{self._data_var_name_}"
            if len(viewers):
                viewers = viewers[0:1]
                win = viewers[0]
                win.unlinkFromViewers()
                win.clear()
                self._update_viewer_(win, winTag, winTitle, docTitle, nFrames)
                
            else:
                win = self._init_viewer_(winFactory, winTag, winSetup, winTitle, docTitle, nFrames)
                win.frameChanged.connect(self._slot_frameChangedInChildViewer)
                viewers.append(win)
                
            win.view(data, get_focus=False)
                
        else:
            for w in viewers:
                w.unlinkFromViewers()
                w.clear()
                w.close()
            viewers.clear()
        
    @safeWrapper
    def _get_viewers_for_data_section(self, section:str) -> typing.Tuple[typing.Any]:
        """
        Parameters:
        ==========
        section: str, one of: 
            "electrophysiology" "ephys", "scansProfiles", "sceneProfiles", 
            "scansBlock", "sceneBlock", "scans", "scene"
        
        Returns:
        ========
        
        wname, viewers, winFactory, winSetup
        
        """
            #"electrophysiology" "ephys", "scansProfiles", "sceneProfiles", 
            #"scansBlock", "sceneBlock", "scans", "scene", "protocols"
        #if not self._data_.hasImageData(section):
            #if not self._data_.hasSignalData(section):
                #return
        
        if section in ("electrophysiology"):
            return "Electrophysiology", self.ephysviewers, sv.SignalViewer, self._signalviewer_setup_
        
        elif section in ("scansBlock",):
            return "Scans Data", self.scansblockviewers, sv.SignalViewer, self._signalviewer_setup_
           
        elif section in ("sceneBlock",):
            return "Scene Data", self.sceneblockviewers, sv.SignalViewer, self._signalviewer_setup_
        
        elif section in ("scansProfiles", "sceneProfiles"):
            return "Scan Region Profile", self.profileviewers, sv.SignalViewer, self._signalviewer_setup_
           
        elif section in ("scene",):
            return "Scene", self.sceneviewers, iv.ImageViewer, self._imageviewer_setup_
           
        elif section in ("scans",):
            return "Scans", self.scansviewers, iv.ImageViewer, self._imageviewer_setup_
        
        return (None, None, None, None)
    
    def _get_data_section_frames_(self, section):
        if self._data_ is None:
            return 0
        
        data = getattr(self._data_, section, None)
        
        if data is None:
            return 0
        
        if isinstance(data, neo.Block):
            if neoutils.is_empty(data, ignore=(TriggerEvent, neo.Event, neo.Epoch)):
                return 0
            
            return len(data.segments)
            
        elif isinstance(data, list) and all((isinstance(v, vigra.VigraArray) for v in data)):
            if section == "scene":
                return self._data_.sceneFrames
            
            else:
                return self._data_.scansFrames
        
        if section in ("electrophysiology", "ephys"):
            return self._data_.electrophysiologySweeps
        
        elif section in ("scansBlock",):
            if neoutils.is_empty(self._data_.scansBlock, ignore = (TriggerEvent, neo.Event, neo.Epoch)):
                return 0
            return len(self._data_.scansBlock.segments)
           
        elif section in ("sceneBlock",):
            if neoutils.is_empty(self._data_.sceneBlock, ignore = (TriggerEvent, neo.Event, neo.Epoch)):
                return 0
            
            return len(self._data_.sceneBlock.segments)
        
        elif section in ("scansProfiles", "sceneProfiles"):
            if neoutils.is_empty([self._data_.sceneProfiles, self._data_.scansProfiles]):
                return 0
            
            return max((len(x.segments) for x in (self._data_.sceneProfiles, self._data_.scansProfiles)))
           
        elif section in ("scene",):
            return self._data_.sceneFrames
           
        elif section in ("scans",):
            return self._data_.scansFrames
        
    def _imageviewer_setup_(self, win):
        win.signal_graphicsObjectAdded[object].connect(self.slot_graphics_object_added_in_window, type = QtCore.Qt.QueuedConnection)
        win.signal_graphicsObjectChanged[object].connect(self.slot_graphics_object_changed_in_window, type = QtCore.Qt.QueuedConnection)
        win.signal_graphicsObjectRemoved[object].connect(self.slot_graphics_object_removed_in_window, type = QtCore.Qt.QueuedConnection)
        win.signal_graphicsObjectSelected[object].connect(self.slot_graphics_object_selected_in_window, type = QtCore.Qt.QueuedConnection)
        win.signal_graphicsObjectDeselected.connect(self.slot_graphics_objects_deselected, type = QtCore.Qt.QueuedConnection)
        
    def _signalviewer_setup_(self, win):
        # TODO 2022-11-05 15:04:37 is this still required ?!?
        pass
            
    @safeWrapper
    def _init_viewers_(self):
        """Sets up the data viewers.
        Calls self._init_data_viewers_ for each data component attribute in ScanData instance
        """
        if self._data_ is None:
            return
        
        self.unlinkFromViewers()
        
        for d in self._data_._data_children_ + self._data_._derived_data_children_:
            self._init_data_viewers_(d[0])
        
        allviewers = [self] + self.sceneviewers + self.scansviewers + self.ephysviewers + self.profileviewers + self.scansblockviewers + self.sceneblockviewers
        
        # NOTE: 2022-01-17 16:57:06
        # to properly deal with frame indices from the ScanData.framesMap we 
        # don't link viewers anymore; instead, we capture changes in each viewer's
        # frame number throught the separate slot _slot_frameChangedInChildViewer
        #for viewer in allviewers:
            #viewer.linkToViewers(*allviewers, broadcast=False)
        
    @safeWrapper
    def _data_modifed_(self, value=False):
        if not isinstance(self._data_, ScanData):
            return
        
        if not isinstance(value, bool):
            raise TypeError("expecting a bool; got %s instead" % type(value).__name__)
        
        self._data_.modified = value
        
        if self._data_.modified:
            self.setWindowTitle("%s * \u2014 LSCaT" % (self._data_var_name_))
            
        else:
            self.setWindowTitle("%s \u2014 LSCaT" % (self._data_var_name_))
        
    @safeWrapper
    def _display_scene_(self):
        #print("LSCaTWindow _display_scene_")
        if self._data_ is None:
            return
        
        nArrays = len(self._data_.scene)
        
        if nArrays == 0:
            return
        
        #self._setup_scene_windows_(nArrays)
        
        for k in range(len(self._data_.scene)):
            self.sceneviewers[k].view(self._data_.scene[k])
            
            if len(self._data_.scene) > 1:
                # multiple single-channel arrays
                self.sceneviewers[k].setWindowTitle("%s %s" % ("Scene", AxesCalibration(self._data_.scene[k].axistags["c"]).channelIndicesAndNames()[0][1]))
                
            else: # single possibly multi-channel array
                axcal = AxesCalibration(self._data_.scene[k].axistags["c"])
                chnames = [s[1] for s in axcal.channelIndicesAndNames()]
                chnames = "+",join(chnames)
                
                self.sceneviewers[k].setWindowTitle("%s %s" % ("Scene", chnames))
            
        self.currentSceneFrame = self.sceneviewers[0].currentFrame
        
        # see NOTE: 2018-09-25 22:19:58
        sigBlock = QtCore.QSignalBlocker(self.sceneDisplayChannelComboBox)
        
        #self.sceneDisplayChannelComboBox.currentIndexChanged[int].disconnect(self.slot_sceneDisplayChannelChanged)
        
        displayChannelGUINDdx = self.sceneDisplayChannelComboBox.currentIndex()
        self.sceneDisplayChannelComboBox.clear()
        self.sceneDisplayChannelComboBox.addItems(["All channels"] + self._data_.sceneChannelNames + ["Select..."])
        self.sceneDisplayChannelComboBox.setCurrentIndex(displayChannelGUINDdx)
        
        #self.sceneDisplayChannelComboBox.currentIndexChanged[int].connect(self.slot_sceneDisplayChannelChanged)
            
    @safeWrapper
    def _display_scans_block_(self):
        if self._data_ is None:
            return
        
        if neoutils.is_empty(self._data_.scansBlock, ignore = (TriggerEvent, neo.Event, neo.Epoch)):
            return
        
        #if len(self._data_.scansBlock.segments) == 0 or all([len(seg.analogsignals) == 0 for seg in self._data_.scansBlock.segments]):
            #return
            
        if len(self.scansblockviewers) == 0:
            win = sv.SignalViewer(parent=self, configTag="scansBlock")
            if win.framesSlider is not None:
                win.framesSlider.setMaximum(len(self._self._data_.scansBlock.segments))
                
            if win.framesSpinner is not None:
                win.framesSpinner.setMaximum(len(self._self._data_.scansBlock.segments))
                
            
            self.scansblockviewers.append(sv.SignalViewer())
            
        self.scansblockviewers[0].view(self._data_.scansBlock)
        self.scansblockviewers[0].currentFrame = self.currentFrame
            
        self.scansblockviewers[0].setWindowTitle("%s - %s" % ("Scan Data", self._data_var_name_))
    
    @safeWrapper
    def _display_scanline_profiles_(self):
        if self._data_ is None:
            return
        
        # NOTE: there is only ONE scan profiles window!!!
        sceneProfiles = None
        scansProfiles = None
        
        if not neoutils.is_empty(self._data_.scanRegionSceneProfiles):
            sceneProfiles  = self._data_.scanRegionSceneProfiles
            
        if not neoutils.is_empty(elf._data_.scanRegionSceneProfiles):
            scansProfiles  = self._data_.scanRegionScansProfiles
            
        if all((s is None for s in (sceneProfiles, scanProfiles))):
            return
        
        if len(self.profileviewers):
            self.profileviewers[0]
        
        # NOTE: avoid overlays until we have written a suitable code for overlaying 
        # neo objects onto neo objects of compatible shape, in SignalViewer
        if len(self.profileviewers) == 0:
            self.profileviewers.append(sv.SignalViewer())
            
            winSettingsStrPrefix = "LSCaTAnalysis/ProfileWindow"
            
            win = self.profileviewers[0]
            
            if self.qsettings.contains("%s_Size" % winSettingsStrPrefix):
                windowSize = self.qsettings.value("%s_Size" % winSettingsStrPrefix, None)
                if windowSize is not None:
                    win.resize(windowSize)
                
            if self.qsettings.contains("%s_Position" %  winSettingsStrPrefix):
                windowPos = self.qsettings.value("%s_Position" %  winSettingsStrPrefix, None)
                if windowPos is not None:
                    win.move(windowPos)
                    
            if self.qsettings.contains("%s_State" % winSettingsStrPrefix):
                windowState = self.qsettings.value("%s_State" % winSettingsStrPrefix, None)
                if windowState is not None:
                    win.restoreState(windowState)
                                    
        if scansProfiles is not None and len(scansProfiles.segments) > 0:
            if all([len(s.analogsignals) for s in scansProfiles.segments]):
                self.profileviewers[0].view(scansProfiles)
            
        elif sceneProfiles is not None and len(sceneProfiles.segments) > 0:
            if all([len(s.analogsignals) for s in sceneProfiles.segments]):
                self.profileviewers[0].view(sceneProfiles)
                
        else:
            return
        
        if self._frame_selector_ is not None:
            if isinstance(self._frame_selector_, range):
                framelist = [k for k in self._frame_selector_]
                self.profileviewers[0].currentFrame = framelist[0]
                
            elif isinstance(self._frame_selector_, slice):
                framelist = [k for k in self._frame_selector_.indices(self._data_.scansFrames)]
                self.profileviewers[0].currentFrame = framelist[0]
                
            elif isinstance(self._frame_selector_, (tuple, list)):
                self.profileviewers[0].currentFrame = self._frame_selector_[0]
                
            elif isinstance(self._frame_selector_, int):
                self.profileviewers[0].currentFrame = self._frame_selector_
                
        self.profileviewers[0].setWindowTitle("%s %s" % ("Scanline profiles", self._data_.name))
        
    @safeWrapper
    def _display_ephys_(self):
        if self._data_ is None:
            return
        wname, viewers, winFactory, winSetup = self._get_viewers_for_data_section("ephys")
        winTitle = f"{wname}"
        winTag = "ephys"
        docTitle = f"{self._data_var_name_}"
        nFrames = self._get_data_section_frames_("ephys")
        
        if len(self.ephysviewers):
            self.ephysviewers[0].clear()
            self._update_viewer_(self.ephysviewers[0], winTag, winTitle, docTitle, nFrames)
            
        else:
            win = self._init_viewer_(winFactory, winTag, winSetup, winTitle, docTitle, nFrames)
            self.ephysviewers.append(win)
            
        self.ephysviewers[0].plot(self._data_.ephys)
        
        if self._frame_selector_ is not None:
            if isinstance(self._frame_selector_, range):
                framelist = [k for k in self._frame_selector_]
                if len(framelist):
                    self.ephysviewers[0].currentFrame = framelist[0]
                
            elif isinstance(self._frame_selector_, slice):
                framelist = [k for k in self._frame_selector_.indices(self._data_.scansFrames)]
                if len(framelist):
                    self.ephysviewers[0].currentFrame = framelist[0]
                
            elif isinstance(self._frame_selector_, (tuple, list)):
                self.ephysviewers[0].currentFrame = self._frame_selector_[0]
                
            elif isinstance(self._frame_selector_, int):
                self.ephysviewers[0].currentFrame = self._frame_selector_

    @safeWrapper
    def _trigger_events_detection_gui_(self, options, ephys_start, ephys_end, dlg = None, title = "Detect triggers"):
        
        if "TriggerEventDetection" not in options:
            default_options = scanDataOptions()
            options["TriggerEventDetection"] = default_options["TriggerEventDetection"]
        
        presynaptic_trigger = options["TriggerEventDetection"]["Presynaptic"]["DetectEvents"]
        presynaptic_channel = options["TriggerEventDetection"]["Presynaptic"]["Channel"]
        
        if isinstance(options["TriggerEventDetection"]["Presynaptic"]["DetectionBegin"], pq.Quantity) \
            and units_convertible(options["TriggerEventDetection"]["Presynaptic"]["DetectionBegin"].units, pq.s):
            presynaptic_trigger_begin = options["TriggerEventDetection"]["Presynaptic"]["DetectionBegin"].magnitude.flatten()[0]
            
        else:
            presynaptic_trigger_begin = 0
            
        if isinstance(options["TriggerEventDetection"]["Presynaptic"]["DetectionEnd"], pq.Quantity) \
            and units_convertible(options["TriggerEventDetection"]["Presynaptic"]["DetectionEnd"], pq.s):
            presynaptic_trigger_end = options["TriggerEventDetection"]["Presynaptic"]["DetectionEnd"].magnitude.flatten()[0]
            
        else:
            presynaptic_trigger_end = 0
            
        presynaptic_name = options["TriggerEventDetection"]["Presynaptic"]["Name"]
        if not isinstance(presynaptic_name, str) or len(presynaptic_name.strip()) == 0:
            presynaptic_name = "epsp"
        
        postsynaptic_trigger = options["TriggerEventDetection"]["Postsynaptic"]["DetectEvents"]
        postsynaptic_channel = options["TriggerEventDetection"]["Postsynaptic"]["Channel"]
        
        if isinstance(options["TriggerEventDetection"]["Postsynaptic"]["DetectionBegin"], pq.Quantity) \
            and units_convertible(options["TriggerEventDetection"]["Postsynaptic"]["DetectionBegin"], pq.s):
            postsynaptic_trigger_begin = options["TriggerEventDetection"]["Postsynaptic"]["DetectionBegin"].magnitude.flatten()[0]
            
        else:
            postsynaptic_trigger_begin = 0
            
        if isinstance(options["TriggerEventDetection"]["Postsynaptic"]["DetectionEnd"], pq.Quantity) \
            and units_convertible(options["TriggerEventDetection"]["Postsynaptic"]["DetectionEnd"], pq.s):
            postsynaptic_trigger_end = options["TriggerEventDetection"]["Postsynaptic"]["DetectionEnd"].magnitude.flatten()[0]
            
        else:
            postsynaptic_trigger_end = 0
            
        postsynaptic_name = options["TriggerEventDetection"]["Postsynaptic"]["Name"]
        
        if not isinstance(postsynaptic_name, str) or len(postsynaptic_name.strip()) == 0:
            postsynaptic_name = "bAP"
        
        photostimulation_trigger = options["TriggerEventDetection"]["Photostimulation"]["DetectEvents"]
        photostimulation_channel = options["TriggerEventDetection"]["Photostimulation"]["Channel"]
        
        if isinstance(options["TriggerEventDetection"]["Photostimulation"]["DetectionBegin"], pq.Quantity) \
            and units_convertible(options["TriggerEventDetection"]["Photostimulation"]["DetectionBegin"], pq.s):
            photostimulation_trigger_begin = options["TriggerEventDetection"]["Photostimulation"]["DetectionBegin"].magnitude.flatten()[0]
            
        else:
            photostimulation_trigger_begin = 0
            
        if isinstance(options["TriggerEventDetection"]["Photostimulation"]["DetectionEnd"], pq.Quantity) \
            and units_convertible(options["TriggerEventDetection"]["Photostimulation"]["DetectionEnd"], pq.s):
            photostimulation_trigger_end = options["TriggerEventDetection"]["Photostimulation"]["DetectionEnd"].magnitude.flatten()[0]
            
        else:
            photostimulation_trigger_end = 0
            
        photostimulation_name = options["TriggerEventDetection"]["Photostimulation"]["Name"]
        
        if not isinstance(photostimulation_name, str) or len(photostimulation_name.strip()) == 0:
            photostimulation_name = "uepsp"
        
        imaging_frame_trigger = options["TriggerEventDetection"]["Imaging frame trigger"]["DetectEvents"]
        imaging_frame_channel = options["TriggerEventDetection"]["Imaging frame trigger"]["Channel"]
        
        if isinstance(options["TriggerEventDetection"]["Imaging frame trigger"]["DetectionBegin"], pq.Quantity) \
            and units_convertible(options["TriggerEventDetection"]["Imaging frame trigger"]["DetectionBegin"], pq.s):
            imaging_frame_trigger_begin = options["TriggerEventDetection"]["Imaging frame trigger"]["DetectionBegin"].magnitude.flatten()[0]
            
        else:
            imaging_frame_trigger_begin = ephys_start
            
        if isinstance(options["TriggerEventDetection"]["Imaging frame trigger"]["DetectionEnd"], pq.Quantity) \
            and units_convertible(options["TriggerEventDetection"]["Imaging frame trigger"]["DetectionEnd"], pq.s):
            imaging_frame_trigger_end = options["TriggerEventDetection"]["Imaging frame trigger"]["DetectionEnd"].magnitude.flatten()[0]
            
        else:
            imaging_frame_trigger_end = ephys_end
            
        imaging_frame_name = options["TriggerEventDetection"]["Imaging frame trigger"]["Name"]
        
        if not isinstance(imaging_frame_name, str) or len(imaging_frame_name.strip()) == 0:
            imaging_frame_name = "imaging"
        
        if dlg is None:
            if not isinstance(title, str) or len(title.strip()) == 0:
                title = "Detect triggers"
                
            dlg = qd.QuickDialog(self, title)
        
        dlg.addLabel("Event triggers detection")
        
        triggersGroup = qd.HDialogGroup(dlg)
        
        presynGroup = qd.VDialogGroup(triggersGroup)
        
        presynDetect = qd.CheckBox(presynGroup, "Presynaptic")
        presynDetect.setToolTip("Detect presynaptic triggers")

                    
        presynTriggerChannel = qd.IntegerInput(presynGroup, "Channel:")
        presynTriggerChannel.variable.setClearButtonEnabled(True)
        presynTriggerChannel.variable.redoAvailable = True
        presynTriggerChannel.variable.undoAvailable = True
        presynTriggerChannel.setToolTip("Channel with the signal for presynaptic trigger")
        
        presynEventNamePrompt = qd.StringInput(presynGroup, "Name:")
        presynEventNamePrompt.variable.setClearButtonEnabled(True)
        presynEventNamePrompt.variable.redoAvailable=True
        presynEventNamePrompt.variable.undoAvailable=True
        presynEventNamePrompt.variable.setToolTip("Name")
        

        
        presynEventStartTimePrompt = qd.FloatInput(presynGroup,"Start (s):")
        presynEventStartTimePrompt.variable.setClearButtonEnabled(True)
        presynEventStartTimePrompt.variable.redoAvailable=True
        presynEventStartTimePrompt.variable.undoAvailable=True
        presynEventStartTimePrompt.variable.setToolTip("Beginning of interval to look for trigger pulse (s)")
        
        
        presynEventStopTimePrompt = qd.FloatInput(presynGroup,"Stop  (s):")
        presynEventStopTimePrompt.variable.setClearButtonEnabled(True)
        presynEventStopTimePrompt.variable.redoAvailable=True
        presynEventStopTimePrompt.variable.undoAvailable=True
        presynEventStopTimePrompt.variable.setToolTip("End of interval to look for trigger pulse (s)")
        
        #print("presynaptic", presynaptic_trigger, 
              #"channel", presynaptic_channel, 
              #"name", presynaptic_name,
              #"begin", presynaptic_trigger_begin,
              #"end", presynaptic_trigger_end)
        
        presynDetect.setChecked(presynaptic_trigger)
        presynTriggerChannel.setValue("%d" % presynaptic_channel)
        presynEventNamePrompt.setText(presynaptic_name)
        presynEventStartTimePrompt.setValue("%f" % presynaptic_trigger_begin)
        presynEventStopTimePrompt.setValue("%f" % presynaptic_trigger_end)
        
        postsynGroup = qd.VDialogGroup(triggersGroup)
        
        postsynDetect = qd.CheckBox(postsynGroup, "Postsynaptic")
        postsynDetect.setToolTip("Detect postsynaptic triggers")
        
        
        postsynTriggerChannel = qd.IntegerInput(postsynGroup, "Channel:")
        postsynTriggerChannel.variable.setClearButtonEnabled(True)
        postsynTriggerChannel.variable.redoAvailable = True
        postsynTriggerChannel.variable.undoAvailable = True
        postsynTriggerChannel.setToolTip("Channel with the signal for postsynaptic trigger")
        
            
        postsynEventNamePrompt = qd.StringInput(postsynGroup, "Name:")
        postsynEventNamePrompt.variable.setClearButtonEnabled(True)
        postsynEventNamePrompt.variable.redoAvailable=True
        postsynEventNamePrompt.variable.undoAvailable=True
        postsynEventNamePrompt.variable.setToolTip("Name")
        
        
        postsynEventStartTimePrompt = qd.FloatInput(postsynGroup,"Start (s):")
        postsynEventStartTimePrompt.variable.setClearButtonEnabled(True)
        postsynEventStartTimePrompt.variable.redoAvailable=True
        postsynEventStartTimePrompt.variable.undoAvailable=True
        postsynEventStartTimePrompt.variable.setToolTip("Beginning of interval to look for trigger pulse (s)")
        
        
        postsynEventStopTimePrompt = qd.FloatInput(postsynGroup,"Stop  (s):")
        postsynEventStopTimePrompt.variable.setClearButtonEnabled(True)
        postsynEventStopTimePrompt.variable.redoAvailable=True
        postsynEventStopTimePrompt.variable.undoAvailable=True
        postsynEventStopTimePrompt.variable.setToolTip("End of interval to look for trigger pulse (s)")
        
        #print("postsynaptic", postsynaptic_trigger, 
              #"channel", postsynaptic_channel, 
              #"name", postsynaptic_name,
              #"begin", postsynaptic_trigger_begin,
              #"end", postsynaptic_trigger_end)
        
        postsynDetect.setChecked(postsynaptic_trigger)
        postsynTriggerChannel.setValue("%d" % postsynaptic_channel)
        postsynEventNamePrompt.setText(postsynaptic_name)
        postsynEventStartTimePrompt.setValue("%f" % postsynaptic_trigger_begin)
        postsynEventStopTimePrompt.setValue("%f" % postsynaptic_trigger_end)

        photostimGroup = qd.VDialogGroup(triggersGroup)
        
        photostimDetect = qd.CheckBox(photostimGroup, "Photostimulation")
        photostimDetect.setToolTip("Detect photostimulation triggers")

        
        photostimTriggerChannel = qd.IntegerInput(photostimGroup, "Channel:")
        photostimTriggerChannel.variable.setClearButtonEnabled(True)
        photostimTriggerChannel.variable.redoAvailable = True
        photostimTriggerChannel.variable.undoAvailable = True
        photostimTriggerChannel.setToolTip("Channel with the signal for photostimulation trigger")
        
        
        photostimEventNamePrompt = qd.StringInput(photostimGroup, "Name:")
        photostimEventNamePrompt.variable.setClearButtonEnabled(True)
        photostimEventNamePrompt.variable.redoAvailable=True
        photostimEventNamePrompt.variable.undoAvailable=True
        photostimEventNamePrompt.variable.setToolTip("Name")
        
        photostimEventStartTimePrompt = qd.FloatInput(photostimGroup,"Start (s):")
        photostimEventStartTimePrompt.variable.setClearButtonEnabled(True)
        photostimEventStartTimePrompt.variable.redoAvailable=True
        photostimEventStartTimePrompt.variable.undoAvailable=True
        photostimEventStartTimePrompt.variable.setToolTip("Beginning of interval to look for trigger pulse (s)")
        
        photostimEventStopTimePrompt = qd.FloatInput(photostimGroup,"Stop  (s):")
        photostimEventStopTimePrompt.variable.setClearButtonEnabled(True)
        photostimEventStopTimePrompt.variable.redoAvailable=True
        photostimEventStopTimePrompt.variable.undoAvailable=True
        photostimEventStopTimePrompt.variable.setToolTip("End of interval to look for trigger pulse (s)")
        
        photostimDetect.setChecked(photostimulation_trigger)
        photostimTriggerChannel.setValue("%d" % photostimulation_channel)
        photostimEventNamePrompt.setText(photostimulation_name)
        photostimEventStartTimePrompt.setValue("%f" % photostimulation_trigger_begin)
        photostimEventStopTimePrompt.setValue("%f" % photostimulation_trigger_end)
        
        #print("photostimulation", photostimulation_trigger, 
              #"channel", photostimulation_channel, 
              #"name", photostimulation_name,
              #"begin", photostimulation_trigger_begin,
              #"end", photostimulation_trigger_end)
        
        imagingGroup = qd.VDialogGroup(triggersGroup)
        
        imagingDetect = qd.CheckBox(imagingGroup, "Imaging frame trigger")
        imagingDetect.setToolTip("Detect imaging frame trigger")

        
        imagingTriggerChannel = qd.IntegerInput(imagingGroup, "Channel:")
        imagingTriggerChannel.variable.setClearButtonEnabled(True)
        imagingTriggerChannel.variable.redoAvailable = True
        imagingTriggerChannel.variable.undoAvailable = True
        imagingTriggerChannel.setToolTip("Channel with the signal for imaging frame trigger")

        imagingEventNamePrompt = qd.StringInput(imagingGroup, "Name:")
        imagingEventNamePrompt.variable.setClearButtonEnabled(True)
        imagingEventNamePrompt.variable.redoAvailable=True
        imagingEventNamePrompt.variable.undoAvailable=True
        imagingEventNamePrompt.variable.setToolTip("Name")
        
        imagingEventStartTimePrompt = qd.FloatInput(imagingGroup,"Start (s):")
        imagingEventStartTimePrompt.variable.setClearButtonEnabled(True)
        imagingEventStartTimePrompt.variable.redoAvailable=True
        imagingEventStartTimePrompt.variable.undoAvailable=True
        imagingEventStartTimePrompt.variable.setToolTip("Beginning of interval to look for trigger pulse (s)")
        
        
        imagingEventStopTimePrompt = qd.FloatInput(imagingGroup,"Stop  (s):")
        imagingEventStopTimePrompt.variable.setClearButtonEnabled(True)
        imagingEventStopTimePrompt.variable.redoAvailable=True
        imagingEventStopTimePrompt.variable.undoAvailable=True
        imagingEventStopTimePrompt.variable.setToolTip("End of interval to look for trigger pulse (s)")
        
        #print("imaging_frame", imaging_frame_trigger, 
              #"channel", imaging_frame_channel, 
              #"name", imaging_frame_name,
              #"begin", imaging_frame_trigger_begin,
              #"end", imaging_frame_trigger_end)
        
        imagingDetect.setChecked(imaging_frame_trigger)
        imagingTriggerChannel.setValue("%d" % imaging_frame_channel)
        imagingEventNamePrompt.setText(imaging_frame_name)
        imagingEventStartTimePrompt.setValue("%f" % imaging_frame_trigger_begin)
        imagingEventStopTimePrompt.setValue("%f" % imaging_frame_trigger_end)
        
        presyn = ()
        postsyn = ()
        photo = ()
        imaging = ()

        if dlg.exec() == QtWidgets.QDialog.Accepted:
            presynaptic_trigger = presynDetect.selection()
            
            options["TriggerEventDetection"]["Presynaptic"]["DetectEvents"] = presynaptic_trigger
            
            if presynaptic_trigger:
                presynChannel   = presynTriggerChannel.value()
                presynName      = presynEventNamePrompt.text()
                presynStart     = presynEventStartTimePrompt.value() * pq.s
                presynStop      = presynEventStopTimePrompt.value() * pq.s

                options["TriggerEventDetection"]["Presynaptic"]["Channel"] = presynaptic_channel
                options["TriggerEventDetection"]["Presynaptic"]["DetectionBegin"] = presynStart
                options["TriggerEventDetection"]["Presynaptic"]["DetectionEnd"] = presynStop
                options["TriggerEventDetection"]["Presynaptic"]["Name"] = presynName
                
                presyn = (presynChannel, presynName, (presynStart, presynStop))
                
                presynaptic_channel         = presynChannel
                presynaptic_name            = presynName
                presynaptic_trigger_begin   = presynStart
                presynaptic_trigger_end     = presynStop
                
            postsynaptic_trigger = postsynDetect.selection()
            options["TriggerEventDetection"]["Postsynaptic"]["DetectEvents"] = postsynaptic_trigger
            
            if postsynaptic_trigger:
                postsynChannel  = postsynTriggerChannel.value()
                postsynName     = postsynEventNamePrompt.text()
                postsynStart    = postsynEventStartTimePrompt.value() * pq.s
                postsynStop     = postsynEventStopTimePrompt.value() * pq.s
                
                options["TriggerEventDetection"]["Postsynaptic"]["Channel"] = postsynChannel
                options["TriggerEventDetection"]["Postsynaptic"]["DetectionBegin"] = postsynStart
                options["TriggerEventDetection"]["Postsynaptic"]["DetectionEnd"] = postsynStop
                options["TriggerEventDetection"]["Postsynaptic"]["Name"] = postsynName
            
                postsyn = (postsynChannel, postsynName, (postsynStart, postsynStop))
                
                postsynaptic_channel = postsynChannel
                postsynaptic_name      = postsynName
                postsynaptic_trigger_begin    = postsynStart
                postsynaptic_trigger_end     = postsynStop
                
            photostimulation_trigger = photostimDetect.selection()
            options["TriggerEventDetection"]["Photostimulation"]["DetectEvents"] = photostimulation_trigger
            
            if photostimulation_trigger:
                photoChannel    = photostimTriggerChannel.value()
                photoName       = photostimEventNamePrompt.text()
                photoStart      = photostimEventStartTimePrompt.value() * pq.s
                photoStop       = photostimEventStopTimePrompt.value() * pq.s
                
                options["TriggerEventDetection"]["Photostimulation"]["Channel"] = photoChannel
                options["TriggerEventDetection"]["Photostimulation"]["DetectionBegin"] = photoName
                options["TriggerEventDetection"]["Photostimulation"]["DetectionEnd"] = photoStart
                options["TriggerEventDetection"]["Photostimulation"]["Name"] = photoStop

                photo = (photoChannel, photoName, (photoStart, photoStop))
                
                photostimulation_channel = photoChannel
                photostimulation_name      = photoName
                photostimulation_trigger_begin    = photoStart
                photostimulation_trigger_end     = photoStop
                
            imaging_frame_trigger = imagingDetect.selection()
            options["TriggerEventDetection"]["Imaging frame trigger"]["DetectEvents"] = imaging_frame_trigger
            
            if imaging_frame_trigger:
                imagingChannel = imagingTriggerChannel.value()
                imagingName = imagingEventNamePrompt.text()
                imagingStart = imagingEventStartTimePrompt.value() * pq.s
                imagingStop = imagingEventStopTimePrompt.value() * pq.s
                
                options["TriggerEventDetection"]["Imaging frame trigger"]["Channel"] = imagingChannel
                options["TriggerEventDetection"]["Imaging frame trigger"]["DetectionBegin"] = imagingStart
                options["TriggerEventDetection"]["Imaging frame trigger"]["DetectionEnd"] = imagingStop
                options["TriggerEventDetection"]["Imaging frame trigger"]["Name"] = imagingName
                
                imaging = (imagingChannel, imagingName, (imagingStart, imagingStop))
                
                imaging_frame_channel = imagingChannel
                imaging_frame_name      = imagingName
                imaging_frame_trigger_begin   = imagingStart
                imaging_frame_trigger_end     = imagingStop
                
            return True, (presyn, postsyn, photo, imaging, options)
        
        else:
            return False, tuple()
        
    @safeWrapper
    def _refresh_image_displays_(self):
        for win in self.scansviewers + self.sceneviewers:
            win.displayFrame()

    @Slot()
    @safeWrapper
    def slot_refreshAllDisplays(self):
        self.displayFrame()

    @Slot()
    @safeWrapper
    def slot_refreshDataDisplay(self, showFiltered = True):
        """ TODO/FIXME clean up this mess, 
        """
        if self._data_ is None:
            return
        
        self.displayFrame()
    
    @safeWrapper
    def _display_scans_(self):
        #print("_display_scans_")
        if self._data_ is None:
            return
        
        nArrays = len(self._data_.scans)
        #print("display raw scans : nArrays %d" % nArrays)
        if nArrays == 0:
            return
        
        for k in range(len(self._data_.scans)):
            self.scansviewers[k].view(self._data_.scans[k])
            
            if len(self._data_.scans) > 1:
                # multiple single-channel arrays
                self.scansviewers[k].setWindowTitle("%s %s" % ("Scan", AxesCalibration(self._data_.scans[k].axistags["c"]).channelIndicesAndNames()[0][1]))
                
            else:
                # single, possibly multi-channel array
                axcal = AxesCalibration(self._data_.scans[k].axistags["c"])
                chnames = [s[1] for s in axcal.channelIndicesAndNames()]
                chnales = "+".join(chnames)
                
                self.scansviewers[k].setWindowTitle("%s %s" % ("Scan", chnames))
        
        # see NOTE: 2018-09-25 22:19:58
        sigBblock = QtCore.QSignalBlocker(self.scanDisplayChannelCombobox)
        
        displayScanChannelGUINdx = self.scanDisplayChannelCombobox.currentIndex()
        self.scanDisplayChannelCombobox.clear()
        self.scanDisplayChannelCombobox.addItems(["All channels"] + self._data_.scansChannelNames + ["Choose..."])
        self.scanDisplayChannelCombobox.setCurrentIndex(displayScanChannelGUINdx)
        
    @safeWrapper
    def _display_graphics_overlays_(self):
        #print("_display_graphics_overlays_")
        if self._data_ is None:
            return
        
        #self._data_._upgrade_API_()
        #print("_display_graphics_overlays_ rois in scene")
        self._display_graphics_objects_(rois=True,  scene=True)
        #print("_display_graphics_overlays_ cursors in scene")
        self._display_graphics_objects_(rois=False, scene=True)
        #print("_display_graphics_overlays_ rois in scans")
        self._display_graphics_objects_(rois=True,  scene=False)
        #print("_display_graphics_overlays_ cursors in scans")
        self._display_graphics_objects_(rois=False, scene=False)
        
        self._display_scan_region_()
        
    @safeWrapper
    def _display_scan_region_(self):
        if self._data_ is None:
            return
        
        obj = self._data_.scanRegion
        #print("_display_scan_region_ %s: %s" % (type(obj).__name__, obj))
        
        if len(self._data_.scene) and len(self.sceneviewers) and isinstance(obj, pgui.PlanarGraphics):
            #print("LSCaT._display_scan_region_ %s: %d frontends" % (type(obj).__name__, len(obj.frontends)))

            # see NOTE: 2018-09-25 22:19:58
            signalBlockers = [QtCore.QSignalBlocker(w) for w in self.sceneviewers]
            
            #print("scanRegion frontends", obj.frontends)

            for k, win in enumerate(self.sceneviewers):
                #print("scene viewer: ",win.windowTitle())
                if len(obj.frontends):
                    obj.frontends.clear
                
                win.addPlanarGraphics(obj, showLabel=False, 
                                        movable=False, 
                                        editable=False,
                                        labelShowsPosition=False,
                                        autoSelect=False)
                        
    @safeWrapper
    def _display_graphics_objects_(self, rois=True, scene=True):
        """Displays a specified overlay type in a specific data subset.
        
        Keyword parameters:
        ====================
        rois    = boolean; choose between rois (True, default) or cursors display
        
        scene   = boolean; choose between scene (True default) or scans 
        
        NOTE: this function is intended to populate image viewer windows with
        GraphicsObject frontends for the cursors & rois already defined in lsdata
        (the backends).
        
        ATTENTION: make sure the backend does not already have a GraphicsObject
        frontend, otherwise  we end up with duplicate frontends.
        
        This effectively takes an "existing backend=>generate new frontend" approach.
        The safest way is to call this function only when loading a new lsdata set 
        (which may have its own backends already defined)
        
        """
        #print("_display_graphics_objects_(rois = %s, scene = %s)" % (rois, scene))
        if self._data_ is None:
            return
        
        if scene:
            channels    = self._data_.sceneChannelNames
            data        = self._data_.scene
            windows     = self.sceneviewers
            nFrames     = self._data_.sceneFrames
            
            if rois:
                graphicsObjects    = self._data_.sceneRois
                
            else:
                graphicsObjects    = self._data_.sceneCursors
            
        else:
            channels    = self._data_.scansChannelNames
            data        = self._data_.scans
            windows     = self.scansviewers
            nFrames     = self._data_.scansFrames
            
            
            if rois:
                graphicsObjects    = self._data_.scansRois
                
            else:
                graphicsObjects    = self._data_.scansCursors
                
                if isinstance(graphicsObjects, dict) and len(graphicsObjects):
                    if isinstance(self._data_.scans, (tuple, list)) and len(self._data_.scans):
                        cursor_span = self._data_.scans[0].shape[0]
                        
                    elif isinstance(self._data_.scans, vigra.VigraArray):
                        cursor_span = self._data_scans.shape[0]
                        
                    for c in graphicsObjects.values():
                        c.width = cursor_span
                        
                    # see NOTE: 2018-09-25 22:19:58
                    sigBlock = QtCore.QSignalBlocker(self.selectCursorSpinBox)
                    self.selectCursorSpinBox.setMaximum(len(self._data_.scansCursors)-1)
                
                
        if len(data) > 0 and len(windows) > 0:
            if isinstance(graphicsObjects, dict) and len(graphicsObjects):
                transparent_label = not self.actionOpaque_cursor_labels.isChecked()
                # see NOTE: 2018-09-25 22:19:58
                
                signalBlockers = [QtCore.QSignalBlocker(w) for w in windows]
                
                for obj in graphicsObjects.values():
                    #print("_display_graphics_objects_ obj", obj)
                    if len(obj.frontends) == 0:
                        for k, win in enumerate(windows):
                            gobj = win.addPlanarGraphics(obj, labelShowsPosition=False)
                            
                            #if gobj is not None:# it may be None if there is no image displayed in the window
                                #gobj.setTransparentLabel(transparent_label)
                            
    @safeWrapper
    def _update_filter_ui_fields_(self):
        if self._data_ is None:
            return
        
        pass
        
    def _update_report_(self):
        if not isinstance(self._data_, ScanData):
            return
        
        if self._selected_analysis_unit_ is not None:
            unit = self._selected_analysis_unit_
            cursor = self._selected_analysis_unit_.landmark
            
        else:
            unit = None
            cursor = self._selected_analysis_cursor_
        
        # NOTE 2018-11-25 01:36:44
        # use pandas.DataFrame
        try:
            if unit is not None:
                report = reportUnitAnalysis(self._data_, unit, frame_index = self.currentFrame)
                
                report_win_title = "%s - %s" % (self._data_.name, unit.name)
                
            else:
                if len(self._data_.analysisUnits):
                    # report on all landmark-based analysis units
                    #report, _ = reportUnitAnalysis(self._data_, self._data_.analysisUnits, frame_index = self.currentFrame)
                    # NOTE 2018-11-25 01:36:44
                    # use pandas.DataFrame
                    report = reportUnitAnalysis(self._data_, self._data_.analysisUnits, frame_index = self.currentFrame)
                    report_win_title = "%s" % self._data_.name
                    
                else:
                    # report data on global (data-wide) analysis unit
                    #report, _ = reportUnitAnalysis(self._data_, None, frame_index = self.currentFrame)
                    # NOTE 2018-11-25 01:36:44
                    # use pandas.DataFrame
                    report = reportUnitAnalysis(self._data_, None, frame_index = self.currentFrame)
                    report_win_title = "%s" % self._data_.name
            
            if report is not None:
                displayed_report = report.copy().transpose() # copy of transposed view of report
            
                # NOTE: 2019-01-10 11:23:55
                # relabels the columns (reindex axis 1) of the transposed DataFrame for convenience
                if "Unit" in report.columns and "Protocol" in report.columns and "Segment" in report.columns:
                    units = report.Unit
                    protocols = report.Protocol
                    segments = report.Segment
                    
                    new_colnames = dict(zip(report.index, ["|".join([units.iloc[i], protocols.iloc[i], segments.iloc[i]]) for i in range(len(units))]))
                    
                    displayed_report.rename(columns = new_colnames, copy=False, inplace=True)
                
                self.reportWindow.view(displayed_report, doc_title = report_win_title, got_focus=False)
                #self.reportWindow.view(displayed_report, doc_title = report_win_title, show=self.reportWindow.isVisible())
            
        except Exception as e:
            traceback.print_exc()

    @safeWrapper
    def _update_analysis_unit_ui_fields_(self):
        """Updates GUI fields in Analysis unit groupbox _AND_ the results in the text viewer window
        """
        
        
        if self._data_ is None:
            return
        
        if not isinstance(self._data_.scansCursors, dict) or len(self._data_.scansCursors) == 0:
            return
        
        # see NOTE: 2018-09-25 22:19:58
        signalBlockers = [QtCore.QSignalBlocker(widget) for widget in self._analysis_unit_gui_widgets_]
        signalBlockers += [QtCore.QSignalBlocker(self.genotypeComboBox), QtCore.QSignalBlocker(self.sexComboBox), QtCore.QSignalBlocker(self.ageLineEdit)]
        
        self.defineAnalysisUnitCheckBox.setTristate(False)
        
        cursorSpinBoxNdx = self.selectCursorSpinBox.value()
        
        cursors = sorted([c for c in self._data_.scansCursors.values() if c.hasStateForFrame(self.currentFrame)], key=lambda x:x.x)
        #cursors = sorted([c for c in self._data_.scansCursors.values() if c.hasStateForFrame(self.currentFrame)], key=lambda x:x.x)
        
        #print("_update_analysis_unit_ui_fields_ %d cursors" % len(cursors))
        #print("_update_analysis_unit_ui_fields_ cursor names %s" % [c.name for c in cursors])

        self.selectCursorSpinBox.setRange(-1, len(cursors)-1)
        
        cursor = None
        unit = None
        
        if self._selected_analysis_unit_ is not None:
            unit = self._selected_analysis_unit_
            if not isinstance(unit, pgui.PlanarGraphics) and hasattr(unit, "landmark"):
                cursor = self._selected_analysis_unit_.landmark
            else:
                cursor = self._selected_analysis_unit_
                
            self.defineAnalysisUnitCheckBox.setCheckState(QtCore.Qt.Checked)
            
        else:
            cursor = self._selected_analysis_cursor_
            self.defineAnalysisUnitCheckBox.setCheckState(QtCore.Qt.Unchecked)
            
        self.cursorXposDoubleSpinBox.setEnabled(self._selected_analysis_cursor_ is not None)
        self.cursorXwindow.setEnabled(self._selected_analysis_cursor_ is not None)
        self.cursorYposDoubleSpinBox.setEnabled(self._selected_analysis_cursor_ is not None)
        self.cursorYwindow.setEnabled(self._selected_analysis_cursor_ is not None)
    
        try:
            if self.reportWindow.isVisible():
                self._update_report_()
                    
            cursorNames = [c.name for c in cursors]
            
            if cursor is not None:
                if cursor.name in cursorNames:
                    self.selectCursorSpinBox.setValue(cursorNames.index(cursor.name))
                    
                    self.analysisUnitNameLineEdit.setText(cursor.name)
                    
                    if cursor.currentFrame != self.currentFrame:
                        cursor.currentFrame = self.currentFrame
                        
                    self.cursorXposDoubleSpinBox.setValue(cursor.x)
                    self.cursorYposDoubleSpinBox.setValue(cursor.y)
                    self.cursorXwindow.setValue(cursor.xwindow)
                    self.cursorYwindow.setValue(cursor.ywindow)
                    
                    #self.cursorXposDoubleSpinBox.setValue(cursor.x)
                    #self.cursorYposDoubleSpinBox.setValue(cursor.y)
                    #self.cursorXwindow.setValue(cursor.xwindow)
                    #self.cursorYwindow.setValue(cursor.ywindow)
                    
                    if unit is not None:
                        self.defineAnalysisUnitCheckBox.setCheckState(QtCore.Qt.Checked)
                        unit_type = unit.type
                        
                    else:
                        if self._data_.hasAnalysisUnit(cursor):
                            self.defineAnalysisUnitCheckBox.setCheckState(QtCore.Qt.Checked)
                            unit_type = self._data_.analysisUnit(cursor).type
                            
                        else:
                            self.defineAnalysisUnitCheckBox.setCheckState(QtCore.Qt.Unchecked)
                            unit_type = UnitTypes[cursor.name[0]]
                    
                    unit_type_index = self.unitTypeComboBox.findText(unit_type)
                
                    if unit_type_index == -1:
                        self.unitTypeComboBox.setCurrentIndex(0)
                        self.unitTypeComboBox.addItem(unit_type)
                    
                    else:
                        self.unitTypeComboBox.setCurrentIndex(unit_type_index)
        
                genotype_index = self.genotypeComboBox.findText(self._data_.genotype)
                
                if genotype_index == -1:
                    self.genotypeComboBox.addItem(self._data_.genotype)
                    self.genotypeComboBox.setCurrentIndex(self.genotypeComboBox.count())
                    if self._data_.genotype not in self._data_._availableGenotypes_:
                        self._data_._availableGenotypes_.append(self._data_.genotype)
                
                else:
                    self.genotypeComboBox.setCurrentIndex(genotype_index)
                    
                sex_index = self.sexComboBox.findText(self._data_.sex)
                
                if sex_index == -1:
                    sex_index = 0
                    self._data_.sex = "NA"
                    self.sexComboBox.setCurrentIndex(0)
                    
                else:
                    self.sexComboBox.setCurrentIndex(sex_index)
                    
                self.ageLineEdit.setText("%s" % self._data_.age)
                    
            else:
                #print("LSCaTWindow._update_analysis_unit_ui_fields_ no cursor")
                self.selectCursorSpinBox.setValue(-1)
                unitName = self._data_.defaultAnalysisUnit.name if isinstance(self._data_.defaultAnalysisUnit, AnalysisUnit) else "NA"
                self.analysisUnitNameLineEdit.setText(unitName)
                self.cursorXposDoubleSpinBox.setValue(0)
                self.cursorYposDoubleSpinBox.setValue(0)
                self.cursorXwindow.setValue(0)
                self.cursorYwindow.setValue(0)
            
                self.defineAnalysisUnitCheckBox.setCheckState(QtCore.Qt.Unchecked)
                
                unit_type_index = self.unitTypeComboBox.findText(self._data_.unitType)
                
                if unit_type_index == -1:
                    self.unitTypeComboBox.addItem(self._data_.unitType)
                    self.unitTypeComboBox.setCurrentIndex(self.unitTypeComboBox.count())
                    if self._data_.unitType not in self._data_.availableUnitTypes:
                        self._data_.availableUnitTypes.append(self._data_.unitType)
                
                else:
                    self.unitTypeComboBox.setCurrentIndex(unit_type_index)
                    
                genotype_index = self.genotypeComboBox.findText(self._data_.genotype)
                
                if genotype_index == -1:
                    self.genotypeComboBox.addItem(self._data_.genotype)
                    self.genotypeComboBox.setCurrentIndex(self.genotypeComboBox.count())
                    if self._data_.genotype not in self._data_._availableGenotypes_:
                        self._data_._availableGenotypes_.append(self._data_.genotype)
                
                else:
                    self.genotypeComboBox.setCurrentIndex(genotype_index)
                    
                sex_index = self.sexComboBox.findText(self._data_.sex)
                
                if sex_index == -1:
                    sex_index = 0
                    self._data_.sex = "NA"
                    self.sexComboBox.setCurrentIndex(0)
                    
                else:
                    self.sexComboBox.setCurrentIndex(sex_index)
                    
                self.ageLineEdit.setText("%s" % self._data_.age)
                    
        except Exception as e:
            traceback.print_exc()

        # see NOTE: 2018-09-25 22:19:58
        #self._connect_gui_slots_(self._analysis_unit_gui_signal_slots_)
            
    @safeWrapper
    def _update_ui_fields_(self):
        #print("LSCaTWindow._update_ui_fields_ BEGIN")
        #traceback.print_stack()
        
        if self._data_ is not None:
            if self._data_var_name_ is None:
                if hasattr(self._data_, "name") and self._data_.name is not None:
                    self._data_var_name_ = strutils.str2symbol(self._data_.name)
                    
                else:
                    self._data_var_name_ = ""
                    
            # self.scanDataVarNameLabel.setText(self._data_var_name_)
            self.baseScipyenDataWidget.dataVarNameLabel.setText(self._data_var_name_)
            
            if self._data_.modified:
                self.setWindowTitle("%s * \u2014 LSCaT" % (self._data_var_name_))
                
            else:
                self.setWindowTitle("%s \u2014 LSCaT" % (self._data_var_name_))
            
            if hasattr(self._data_, "name") and self._data_.name is not None:
                name = self._data_.name
                
            else:
                name = ""
                
            # ###
            # BEGIN Data tab
            dataWidgetsSignalBockers = [QtCore.QSignalBlocker(widget) for widget in \
                (self.unitTypeComboBox, )]
            
            # dataWidgetsSignalBockers = [QtCore.QSignalBlocker(widget) for widget in \
            #     (self.scanDataNameLineEdit, self.cellLineEdit, self.fieldLineEdit, self.genotypeComboBox, self.unitTypeComboBox, self.sexComboBox, self.ageLineEdit)]
            
            # self.sourceIDLineEdit.setText(self._data_.sourceID)
            
            # self.scanDataNameLineEdit.setText(self._data_.name)
            # self.cellLineEdit.setText(self._data_.cell)
            # self.fieldLineEdit.setText(self._data_.field)
            
#             genotypes = self._data_._availableGenotypes_
#             
#             self.genotypeComboBox.clear()
#             self.genotypeComboBox.addItems(genotypes)
            
            # genotype_index = self.genotypeComboBox.findText(self._data_.genotype)
            
#             if genotype_index == -1:
#                 self.genotypeComboBox.addItem(self._data_.genotype)
#                 self.genotypeComboBox.setCurrentIndex(self.genotypeComboBox.count())
#                 if self._data_.genotype not in self._data_._availableGenotypes_:
#                     self._data_._availableGenotypes_.append(self._data_.genotype)
#             
#             else:
#                 self.genotypeComboBox.setCurrentIndex(genotype_index)
            
            # sex_index = self.sexComboBox.findText(self._data_.sex)
#             
#             if sex_index == -1:
#                 self._data_.genotype = "NA"
#                 self.genotypeComboBox.setCurrentIndex(0)
#                 
#             else:
#                 self.genotypeComboBox.setCurrentIndex(sex_index)
                
            # self.ageLineEdit.setText("%s" % self._data_.age)
            
            # unit_types = self._data_.availableUnitTypes
            
            self.unitTypeComboBox.clear()
            self.unitTypeComboBox.addItems(self._data_.availableUnitTypes)
            
            unit_type = self._data_.analysisUnit.unit_type if isinstance(self._data_.analysisUnit, AnalysisUnit) else "NA"

            unit_type_index = self.unitTypeComboBox.findText(self._data_.unitType)
                
            if unit_type_index == -1:
                self.unitTypeComboBox.setCurrentIndex(0)
                self.unitTypeComboBox.addItem(unit_type)
            
            else:
                self.unitTypeComboBox.setCurrentIndex(unit_type_index)
            
            # update analysis unit fields
            self._update_analysis_unit_ui_fields_()
            
            self._update_filter_ui_fields_()
            
            # END Data tab
            # ###
    
            # ###
            # BEGIN epscat tab
            # see NOTE: 2018-09-25 22:19:58
            epscatWidgetsSignalBlockers = [QtCore.QSignalBlocker(widget) for widget in \
                (self.indicatorChannelComboBox, 
                 self.ind2refBleedDoubleSpinBox, self.ref2indBleedDoubleSpinBox, 
                 self.indicatorNameLineEdit, 
                 self.indicatorKdDoubleSpinBox, 
                 self.indicatorFminDoubleSpinBox, self.indicatorFmaxDoubleSpinBox, 
                 self.discriminate2DCheckBox, 
                 self.useIntervalsRadioButton, self.useTriggersRadioButton, self.useCursorsForDiscriminationRadioButton, 
                 self.fs_DiscriminantDoubleSpinBox, self.minR2SpinBox, 
                 self.baseDiscriminationWindowDoubleSpinBox, self.peakDiscriminationWindowDoubleSpinBox, 
                 self.epscatDarkCurrentBeginDoubleSpinBox, self.epscatDarkCurrentEndDoubleSpinBox, 
                 self.epscatF0BeginDoubleSpinBox, self.epscatF0EndDoubleSpinBox, 
                 self.epscatFitBeginDoubleSpinBox, self.epscatFitEndDoubleSpinBox, 
                 self.epscatIntegralBeginDoubleSpinBox, self.epscatIntegralEndDoubleSpinBox,
                 self.doFitCheckBox, self.epscatComponentsTableWidget)]
            
            if isinstance(self._data_.analysisOptions, dict) and len(self._data_.analysisOptions):
                # Channels groupbox
                val = get_nested_value(self._data_.analysisOptions, ["Channels", "Indicator"])
                
                if val is not None:
                    self.indicatorChannelComboBox.setCurrentIndex(self._data_.scansChannelNames.index(val))
                    
                else:
                    self.indicatorChannelComboBox.setCurrentIndex(0)
                    
                val = get_nested_value(self._data_.analysisOptions, ["Channels", "Reference"])
                
                if val is not None:
                    self.referenceChannelComboBox.setCurrentIndex(self._data_.scansChannelNames.index(val))
                    
                else:
                    self.referenceChannelComboBox.setCurrentIndex(0)
                
                val = get_nested_value(self._data_.analysisOptions, ["Channels", "Bleed_ind_ref"])
                
                if isinstance(val, float):
                    self.ind2refBleedDoubleSpinBox.setValue(val)
                    
                val = get_nested_value(self._data_.analysisOptions, ["Channels", "Bleed_ref_ind"])
                
                if isinstance(val, float):
                    self.ref2indBleedDoubleSpinBox.setValue(val)
                    
                # Indicator calibration group box
                val = get_nested_value(self._data_.analysisOptions, ["IndicatorCalibration", "Name"])
                
                if isinstance(val, str):
                    self.indicatorNameLineEdit.setText(val)
                    
                val = get_nested_value(self._data_.analysisOptions, ["IndicatorCalibration", "Kd"])
                
                if isinstance(val, float):
                    if np.isnan(val) or np.isinf(val):
                        self.indicatorKdDoubleSpinBox.setValue(-1)
                    else:
                        self.indicatorKdDoubleSpinBox.setValue(val)
                    
                val = get_nested_value(self._data_.analysisOptions, ["IndicatorCalibration", "Fmin"])
                
                if isinstance(val, float):
                    if np.isnan(val) or np.isinf(val):
                        self.indicatorFminDoubleSpinBox.setValue(-1)
                        
                    else:
                        self.indicatorFminDoubleSpinBox.setValue(val)
                    
                val = get_nested_value(self._data_.analysisOptions, ["IndicatorCalibration", "Fmax"])
                
                if isinstance(val, float):
                    if np.isnan(val) or np.isinf(val):
                        self.indicatorFmaxDoubleSpinBox.setValue(-1)
                    else:
                        self.indicatorFmaxDoubleSpinBox.setValue(val)
                    
                # BEGIN detection group box
                val = get_nested_value(self._data_.analysisOptions, ["Intervals", "DarkCurrent"])
                
                if isinstance(val, (tuple, list)) and len(val) == 2:
                    if isinstance(val[0], pq.Quantity) and check_time_units(val[0]):
                        self.epscatDarkCurrentBeginDoubleSpinBox.setValue(val[0].magnitude.flatten()[0])
                        
                    if isinstance(val[1], pq.Quantity) and check_time_units(val[1]):
                        self.espcatDarkCurrentEndDoubleSpinBox.setValue(val[1].magnitude.flatten()[0])
                        
                val = get_nested_value(self._data_.analysisOptions, ["Intervals", "F0"])
                #print("Intervals F0", val)

                if isinstance(val, (tuple, list)) and len(val) == 2:
                    if isinstance(val[0], pq.Quantity) and check_time_units(val[0]):
                        self.epscatF0BeginDoubleSpinBox.setValue(val[0].magnitude.flatten()[0])
                        
                    if isinstance(val[1], pq.Quantity) and check_time_units(val[1]):
                        self.epscatF0EndDoubleSpinBox.setValue(val[1].magnitude.flatten()[0])
                    
                val = get_nested_value(self._data_.analysisOptions, ["Intervals", "Fit"])
                #print("Intervals Fit", val)
                
                if isinstance(val, (tuple, list)) and len(val) == 2:
                    if isinstance(val[0], pq.Quantity) and check_time_units(val[0]):
                        self.epscatFitBeginDoubleSpinBox.setValue(val[0].magnitude.flatten()[0])
                        
                    if isinstance(val[1], pq.Quantity) and check_time_units(val[1]):
                        self.epscatFitEndDoubleSpinBox.setValue(val[1].magnitude.flatten()[0])
                
                val = get_nested_value(self._data_.analysisOptions, ["Intervals", "Integration"])
                #print("Intervals Integration", val)
                
                if isinstance(val, (tuple, list)) and len(val) == 2:
                    if isinstance(val[0], pq.Quantity) and check_time_units(val[0]):
                        self.epscatIntegralBeginDoubleSpinBox.setValue(val[0].magnitude.flatten()[0])
                
                    if isinstance(val[1], pq.Quantity) and check_time_units(val[1]):
                        self.epscatIntegralEndDoubleSpinBox.setValue(val[1].magnitude.flatten()[0])
                    
                # Cursor window and F/S discrimination row
                val = get_nested_value(self._data_.analysisOptions, ["Roi", "width"])
                
                if isinstance(val, int):
                    self.epscatCursorWindowSpinBox.setValue(val)
                    
                else:
                    self.epscatCursorWindowSpinBox.setValue(10)
                    
                val = get_nested_value(self._data_.analysisOptions, ["Discrimination", "PredicateValue"])
                
                if isinstance(val, float):
                    self.fs_DiscriminantDoubleSpinBox.setValue(val)
                    
                else:
                    self.fs_DiscriminantDoubleSpinBox.setValue(1.3)
                    
                val = get_nested_value(self._data_.analysisOptions, ["Discrimination", "MinimumR2"])
                
                if isinstance(val, float):
                    self.minR2SpinBox.setValue(val)
                    
                else:
                    self.minR2SpinBox.setValue(0.5)
                    
                val = get_nested_value(self._data_.analysisOptions, ["Discrimination", "BaseWindow"])
                
                if val:
                    self.baseDiscriminationWindowDoubleSpinBox.setValue(val.magnitude.flatten()[0])
                
                val = get_nested_value(self._data_.analysisOptions, ["Discrimination", "PeakWindow"])
                
                if val:
                    self.peakDiscriminationWindowDoubleSpinBox.setValue(val.magnitude.flatten()[0])
                
                val = get_nested_value(self._data_.analysisOptions, ["Discrimination", "Discr_2D"])
                
                if val:
                    self.discriminate2DCheckBox.setCheckState(QtCore.Qt.Checked)
                    
                else:
                    self.discriminate2DCheckBox.setCheckState(QtCore.Qt.Unchecked)
                    
                val = get_nested_value(self._data_.analysisOptions, ["Discrimination", "First"])
                
                if val:
                    self.firstTriggerOnlyCheckBox.setCheckState(QtCore.Qt.Checked)
                    
                else:
                    self.firstTriggerOnlyCheckBox.setCheckState(QtCore.Qt.Unchecked)
                    
                val = get_nested_value(self._data_.analysisOptions, ["Discrimination", "WindowChoice"])
                
                if val == "delays":
                    self.useIntervalsRadioButton.setChecked(True)
                    
                elif val == "triggers":
                    self.useTriggersRadioButton.setChecked(True)
                    
                elif val == "cursors":
                    self.useCursorsForDiscriminationRadioButton.setChecked(True)
                    
                if "Fitting" not in self._data_.analysisOptions:
                    self._data_.analysisOptions["Fitting"] = dict()
                    
                if "Fit" not in self._data_.analysisOptions["Fitting"] or not isinstance(self._data_.analysisOptions["Fitting"]["Fit"], bool):
                    self._data_.analysisOptions["Fitting"]["Fit"] = True
                    
                if self._data_.analysisOptions["Fitting"]["Fit"]:
                    self.doFitCheckBox.setCheckState(QtCore.Qt.Checked)
                    
                else:
                    self.doFitCheckBox.setCheckState(QtCore.Qt.Unchecked)
                
                # END detection
            
                # NOTE: 2017-12-24 10:06:51
                #
                # EPSCaT model table widget
                # columns:
                # 0 = component number
                # 1 = scale (scalar or iterable of scalars)
                # 2 = tau decay (scalar or iterable of scalars) ; same len as scale !!!
                # 3 = offset (scalar)
                # 4 = tau rise (scalar)
                # 5 = onset or "delay" (scalar)
                # for each component we need: initial, lower bounds, upper bounds
                
                # I decide on the following:
                # 1) for each EPSCaT component use three rows, one each for
                #   initial
                #   lower
                #   upper
                #
                #   where # is the 0-based index of EPSCaT component in the model
                #
                # 2) create one column for each EPSCaT parameter; if there are 
                # EPSCaT components with different numbers of decays,
                # ADD columns to acommodate the maximum of these
                #
                # The first two column are NOT editable
                #
                # For example:
                # "Component"  "parameters" "scale_0" "taudecay_0" "scale_1" "taudecay_1" "offset" "taurise" " delay"
                # 0               "initial"      a0_0      d0_0                              o0       r0      l0
                # 0               "lower"       la0_0     ld0_0                             lo0      lr0     ll0
                # 0               "upper"       ua0_0     ud0_0                             uo0      ur0     ul0
                # 1               "initial"      a1_0      d1_0       a1_1      d1_1         o1       r1      l1
                # 1               "lower"       la1_0     ld1_0      la1_1     ld1_1        lo1      lr1     ll1
                # 1               "upper"       ua1_0     ud1_0      ua1_1     ud1_1        uo1      ur1     ul1
                #
                # etc...
                #
            
                val = get_nested_value(self._data_.analysisOptions, ["Fitting", "CoefficientNames"])
                
                if isinstance(val, (tuple, list)) and all([isinstance(v, str) for v in val]):
                    
                    nDecays = models.check_rise_decay_params(get_nested_value(self._data_.analysisOptions, ["Fitting", "Initial"])[0])
                    
                    #if nDecays > 0:
                        
                    # NOTE: 2017-12-24 22:35:42
                    # this will acommodate the EPSCaT model with up to the maximum number of decay components
                    # defined in epscat options
                
                    columnLabels = ["Component", "Parameters"] + val
                    
                    #columnLabels = val
                    
                    self.epscatComponentsTableWidget.setColumnCount(len(columnLabels))
                    
                    self.epscatComponentsTableWidget.setHorizontalHeaderLabels(columnLabels)
                    
                    
                    init  = get_nested_value(self._data_.analysisOptions, ["Fitting", "Initial"])
                    lower = get_nested_value(self._data_.analysisOptions, ["Fitting", "Lower"])
                    upper = get_nested_value(self._data_.analysisOptions, ["Fitting", "Upper"])
                    
                    self.epscatComponentsTableWidget.setRowCount(len(init) * 3)
                    
                    for k in range(len(init)):
                        n_decays = models.check_rise_decay_params(init[k])
                        row = k * 3 
                        
                        self.epscatComponentsTableWidget.setItem(row, 0, QtWidgets.QTableWidgetItem("%d" % k))
                        
                        self.epscatComponentsTableWidget.setItem(row, 1, QtWidgets.QTableWidgetItem("initial"))
                        
                        ndx = [k_ for k_ in range(n_decays * 2)] + [k_ for k_ in range(len(init[k])-3, len(init[k]))]
                        
                        for k_ in ndx:
                            col = k_ + 2
                            self.epscatComponentsTableWidget.setItem(row, col, QtWidgets.QTableWidgetItem("%g" % init[k][k_]))
                            # do allow selection & editing
                            #self.epscatComponentsTableWidget.item(row, col).setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable)
                            
                        row += 1
                        
                        self.epscatComponentsTableWidget.setItem(row, 0, QtWidgets.QTableWidgetItem("%d" % k))
                        
                        self.epscatComponentsTableWidget.setItem(row, 1, QtWidgets.QTableWidgetItem("lower"))
                        
                        ndx = [k_ for k_ in range(n_decays * 2)] + [k_ for k_ in range(len(lower[k])-3, len(lower[k]))]
                        for k_ in ndx:
                            col = k_ + 2
                            self.epscatComponentsTableWidget.setItem(row, col, QtWidgets.QTableWidgetItem("%g" % lower[k][k_]))
                            # do allow selection & editing
                            #self.epscatComponentsTableWidget.item(row, col).setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable)
                            
                        row += 1
                        
                        self.epscatComponentsTableWidget.setItem(row, 0, QtWidgets.QTableWidgetItem("%d" % k))

                        self.epscatComponentsTableWidget.setItem(row, 1, QtWidgets.QTableWidgetItem("upper"))
                        
                        ndx = [k_ for k_ in range(n_decays * 2)] + [k_ for k_ in range(len(upper[k])-3, len(upper[k]))]
                        
                        for k_ in ndx:
                            col = k_ + 2
                            self.epscatComponentsTableWidget.setItem(row, col, QtWidgets.QTableWidgetItem("%g" % upper[k][k_]))
                            # do allow selection & editing
                            #self.epscatComponentsTableWidget.item(row, col).setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable)
                        
                        
                # disallow selection & editing for 1st two columns
                for r in range(self.epscatComponentsTableWidget.rowCount()):
                    self.epscatComponentsTableWidget.item(r,0).setFlags(QtCore.Qt.NoItemFlags)
                    self.epscatComponentsTableWidget.item(r,1).setFlags(QtCore.Qt.NoItemFlags)
                        
            # END epscat tab
            # ####
            
        else:
            self._data_var_name_ = ""
            self.baseScipyenDataWidget.dataVarNameLabel.setText(self._data_var_name_)
            # self.scanDataVarNameLabel.setText(self._data_var_name_)
#             
            
        # NOTE: 2017-11-14 12:10:15
        # this edits the name attribute of lsdata, which is NOT 
        # the variable's name in the user workspace
        # self.scanDataNameLineEdit.setText(name) 
            
        self.framesQSpinBox.setMinimum(0)
        self.framesQSpinBox.setMaximum(self._data_.scansFrames-1)
        self.totalFramesCountLabel.setText("of %d" % self._data_.scansFrames)
        
        self.frameQSlider.setMinimum(0)
        self.frameQSlider.setMaximum(self._data_.scansFrames-1)
        
        #print("LSCaTWindow._update_ui_fields_ END")
        
    #@safeWrapper
    #def _link_window_navigation_(self):
        #if self._data_ is None:
            #return
        
        #viewers = [w for w in self.sceneviewers] + \
                  #[w for w in self.scansviewers] + \
                  #[w for w in self.ephysviewers] + \
                  #[w for w in self.profileviewers] + \
                  #[w for w in self.scansblockviewers] + \
                  #[w for w in self.sceneblockviewers]
              
        ##print("LSCaTWindow _link_window_navigation_: %d windows" % len(viewers))
        ##for w in viewers:
            ##print(w.windowTitle())
        
        #self.linkToViewers(*viewers)
        
    @safeWrapper
    def _parsedata_(self, newdata=None, varname=None):
        """Parses metainformation and then actually assigns the data to the _data_ attribute
        """
        if isinstance(newdata, ScanData):
            #newdata._upgrade_API_()
            #print("LSCaTWindow _parsedata_ %s" % newdata.name)
            default_options = scanDataOptions()
            
            try: # old pickles don't have analysisOptions descriptors!
                analysisOptions = newdata.analysisOptions 
            except:
                analysisOptions = dict()
                
            if analysisOptions is None:
                analysisOptions = dict()
                
            if "Discrimination" not in analysisOptions:
                analysisOptions["Discrimination"] = collections.OrderedDict()
                analysisOptions["Discrimination"].update(default_options["Discrimination"])
                        
            #if "2D" not in in analysisOptions["Discrimination"]:
                #newdata.analysisOptions["Discrimination"]["Discr_2D"] = newdata.analysisOptions["Discrimination"]["2D"]
                #newdata.analysisOptions["Discrimination"].pop("2D", None)

            #if "data_2D" in newdata.analysisOptions["Discrimination"]:
                #newdata.analysisOptions["Discrimination"]["Discr_2D"] = newdata.analysisOptions["Discrimination"]["data_2D"]
                #newdata.analysisOptions["Discrimination"].pop("data_2D", None)
            
            if hasattr(newdata, "cell"):
                if isinstance(newdata.cell, str):
                    newdata.cell = strutils.str2symbol(newdata.cell)
                
            else:
                newdata.cell = "NA"
                
            if hasattr(newdata, "field"):
                if isinstance(newdata.field, str):
                    newdata.field = strutils.str2symbol(newdata.field)
                
            else:
                newdata.field = "NA"
                
            self._selected_analysis_cursor_ = None
            self._selected_analysis_unit_ = None
                
            self._data_ = newdata
            
            if isinstance(varname, str) and len(varname.strip()):
                self._data_var_name_ = varname
                
            else:
                self._data_var_name_ = newdata.name
            
        else:
            raise TypeError("Expecting a ScanData object or None; got %s instead" % type(newdata).__name__)
            
        if self._data_ is None:
            return
        
        # check if there are vertical cursors defined for scandata
        # and for each of these, check that they have a linked point
        # cursor in the scene -- create one if not found
        
        #self.currentFrame = 0
        self._current_frame_index_ = 0
        self._number_of_frames_ = self._data_.nFrames()
        
        if self.actionLink_vertical_scan_cursors_to_scene_point_cursors.isChecked():
            if isinstance(self._data_.scanRegion, pgui.Path) and len(self._data_.scanRegion):
                self._current_frame_scan_region_[:] = self._data_.scanRegion.getState(self.currentFrame)
                
                if len(self._data_.scansCursors):
                    for obj in self._data_.scansCursors.values():
                        if obj.type == pgui.GraphicsObjectType.vertical_cursor:
                            if len(obj.linkedObjects) == 0:
                                self._link_scans_vcursor_to_scene_pcursor_(obj)
                                
        
    @safeWrapper
    def autoSetupLinescanCursorsInFrame(self, frame, displayFrame=True):
        if self._data_ is None:
            return
        
        if len(self._data_.analysisOptions) == 0:
            warnings.warn("No analysis options in data yet")
            return
        
        defaultRoiWidth = self._data_.analysisOptions["Roi"]["width"]
        
        profiles = self._data_.scanRegionScansProfiles
        
        #if self.showScanRawDataCheckBox.checkState() == QtCore.Qt.Unchecked:
            #profiles = self._data_.scanlineFilteredScansProfiles
            
            #if any([len(s.analogsignals) == 0 for s in profiles.segments]):
                #profiles = self._data_.scanRegionScansProfiles
                
        if any([len(s.analogsignals) == 0 for s in profiles.segments]):
            warnings.warn("Scanline profiles should have been generated for all frames")
            return
        
        if frame < 0 or frame >= len(profiles.segments):
            raise ValueError("Invalid frame index specified: %d" % frame)
        
        refChannelName = self._data_.analysisOptions["Channels"]["Reference"]
        
        channel_ndx = ephys.get_index_of_named_signal(profiles.segments[frame], refChannelName, stype=DataSignal)
        
        fitted_params, fitted_pcov, \
            rsquare, fitted_profile, \
                fitted_peaks, initial_params = \
                    detectRoisInProfile(profiles.segments[frame].analogsignals[channel_ndx], 3)

        if len(fitted_params) == 4 and len(fitted_params[1]):
            cursors = list()
            
            for (k, (x, w)) in enumerate(zip(fitted_params[1], fitted_params[2])):
                #if self._data_.analysisOptions["Roi"]["auto"]:
                if defaultRoiWidth == "auto":
                    cursors.append(pgui.Cursor(x = int(x), xwindow = w, name="r%d" % k, \
                        cursortype = pgui.GraphicsObjectType.vertical_cursor))
                else:
                    cursors.append(pgui.Cursor(x = int(x), xwindow = defaultRoiWidth, name="r%d" % k, \
                        cursortype = pgui.GraphicsObjectType.vertical_cursor))
                
            if len(cursors):
                self._data_.removeCursors(scans=True)
                self._data_.setCursors(*cursors, scans=True)
                
        if displayFrame:
            self._display_graphics_objects_(rois=False, scene=False)
                
    @safeWrapper
    def displaySelectFrames(self):
        if self._data_ is None or len(self._data_.triggers) == 0:
            return
        
        if len(self.currentProtocols):
            prframeindices = list()
            
            for p in self.currentProtocols:
                prframeindices += p.segmentIndices()
            
            self._frame_selector_ = prframeindices
            
        else:
            self._frame_selector_ = None
        
            self.displayFrame()
        
    @safeWrapper
    def setScansFilterFunction(self, channel, value, *args, **kwargs):
        """Sets the filtering function for the specified scans channel
        
        channel: channel name (str)
        
        value:  function name (str that can be evaluated to a function in the 
                current namespace) or a function object (present in the current 
                namespace)
                
        *args:  comma-separated list of positional parameters to the filtering 
                function (optional, the default is empty)
                
        **kwargs: key-value pairs of keyword parameters to the filtering
                function (default is an empty dict)
        
        """
        if not isinstance(self._data_, ScanData):
            return
        
        if not isinstance(channel, str):
            raise TypeError("Expecting a channel name; got %s instead" % type(channel).__name__)
        
        if channel not in self._data_.scansChannelNames:
            raise ValueError("Channel %s not found in %s" % (channel, self._data_var_name_))
        
        if isinstance(value, str):
            value = eval(value) # raises NameError is value does not resolve to a function
            
        elif type(value).__name__ != "function":
            raise TypeError("New function must be a function or a str; got %s instead" % type(value).__name__)
            
        #print("function:  ", value)
        
        if len(self._scans_filters_) == 0 or not channel in self._scans_filters_.keys(): 
            self._scans_filters_[channel] = dict()
            
        self._scans_filters_[channel]["function"]  = value.__name__
        self._scans_filters_[channel]["args"]      = []
        self._scans_filters_[channel]["kwargs"]    = dict()
    
        # now modify args and/or kwargs if needed
        if len(args) > 0:
            self._scans_filters_[channel]["args"] = args

        if len(kwargs) > 0:
            self._scans_filters_[channel]["kwargs"] = kwargs
            
    @safeWrapper
    def getSceneFilterFunction(self, channel):
        """Returns the function object for filtering the specified scene channel
        """
        if not isinstance(self._data_, ScanData):
            return
        
        if not isinstance(channel, str):
            raise TypeError("Expecting a channel name; got %s instead" % type(channel).__name__)
        
        if channel not in self.sceneChannelNames:
            raise ValueError("Channel %s not found in %s" % (channel, self._data_var_name_))
        
        if len(self._scene_filters_) == 0:
            return
        
        if channel not in self._scene_filters_.keys():
            return
        
        if "function" not in self._scene_filters_[channel]:
            return
        
        # raises NameError if value does not resolve to a function
        return eval(self._scene_filters_[channel]["function"])
            
    @safeWrapper
    def setSceneFilterFunction(self, channel, value, *args, **kwargs):
        """Sets the filtering function for the specified scene channel
        
        channel: channel name (str)
        
        value:  function name (str that can be evaluated to a function in the 
                current namespace) or a function object (present in the current 
                namespace)
                
        *args:  comma-separated list of positional parameters to the filtering 
                function (optional, the default is empty)
                
        **kwargs: key-value pairs of keyword parameters to the filtering
                function (default is an empty dict)
        
        """
        if not isinstance(self._data_, ScanData):
            return
        
        if not isinstance(channel, str):
            raise TypeError("Expecting a channel name; got %s instead" % type(channel).__name__)
        
        if channel not in self._data_.sceneChannelNames:
            raise ValueError("Channel %s not found in %s" % (channel, self._data_var_name_))
        
        if isinstance(value, str):
            value = eval(value) # raises NameError is value does not resolve to a function
            
        elif type(value).__name__ != "function":
            raise TypeError("New function must be a function or a str; got %s instead" % type(value).__name__)
        
        if len(self._scene_filters_) == 0 or channel not in self._scene_filters_.keys():
            self._scene_filters_[channel] = dict()
            
        self._scene_filters_[channel]["function"]  = value.__name__
        self._scene_filters_[channel]["args"]      = []
        self._scene_filters_[channel]["kwargs"]    = dict()
    
        # now modify args and/or kwargs if needed
        if len(args) > 0:
            self._scene_filters_[channel]["args"] = args

        if len(kwargs) > 0:
            self._scene_filters_[channel]["kwargs"] = kwargs
            
    @safeWrapper
    def getScansFilterFunction(self, channel):
        """Returns the function object for filtering the specified scans channel
        """
        if not isinstance(self._data_, ScanData):
            return
        
        if not isinstance(channel, str):
            raise TypeError("Expecting a channel name; got %s instead" % type(channel).__name__)
        
        if channel not in self._data_.scansChannelNames:
            raise ValueError("Channel %s not found in %s" % (channel, self._data_var_name_))
        
        if len(self._scans_filters_) == 0:
            return
        
        if channel not in self._scans_filters_.keys():
            return
        
        if "function" not in self._scans_filters_[channel]:
            return
        
        # raises NameError if value does not resolve to a function
        return eval(self._scans_filters_[channel]["function"])
            
    @safeWrapper
    def generateFilters(self):
        """Generates filter specifications in ScanData
        
        Uses the specifications in data.analysisOptions to generate filter
        functions used for filtering (denoising) data.scene and data.scans.
        
        TODO 2019-10-12 14:19:22 this is a BAD design
        
        Filter logic should be independent of ScanData, and therefore moved 
        away from the structure and API of ScanData.
        
        TODO 2019-10-12 14:21:21
        Give the possibility for the user to set up their own filtering functions.
        
        
        NOTE: There are no signal-slot connections! The values in the UI fields
        are retrieved here.
        FIXME when do we populate these !?! sort this out !!!
        
        """
        # we need to store parameters for four filters in lsdata: 
        # 1) scene reference channel filter
        # 2) scene indicator channel filter
        # 3) scans reference channel filter
        # 4) scans indicator channel filter
        if not isinstance(self._data_, ScanData):
            return
        
        if not isinstance(self._data_.analysisOptions, dict) or len(self._data_.analysisOptions) == 0:
            return
        
        if "Channels" not in self._data_.analysisOptions.keys():
            return
        
        refChannel = self._data_.analysisOptions["Channels"]["Reference"]
        indChannel = self._data_.analysisOptions["Channels"]["Indicator"]
        
        currentSceneFilter = self.sceneFiltersComboBox.currentText()
        
        if len(currentSceneFilter) > 0:
            if currentSceneFilter == "Purelet":
                self.setSceneFilterFunction(refChannel, imgp.pureDenoise.__name__, \
                    alpha = self.pureletAlphaSceneRefDoubleSpinBox.value(), \
                    beta = self.pureletBetaSceneRefDoubleSpinBox.value(), \
                    sigma2 = self.pureletSigmaSceneRefDoubleSpinBox.value(), \
                    levels = self.pureletJSceneRefSpinBox.value(), \
                    threshold = self.pureletTSceneRefSpinBox.value())
                
                
                self.setSceneFilterFunction(indChannel, imgp.pureDenoise.__name__, \
                    alpha = self.pureletAlphaSceneIndDoubleSpinBox.value(), \
                    beta = self.pureletBetaSceneIndDoubleSpinBox.value(), \
                    sigma2 = self.pureletSigmaSceneIndDoubleSpinBox.value(), \
                    levels = self.pureletJSceneIndSpinBox.value(), \
                    threshold = self.pureletTSceneIndSpinBox.value())
                
            elif currentSceneFilter == "Gaussian":
                self.setSceneFilterFunction(refChannel, imgp.gaussianFilter1D.__name__, \
                    self.gaussianSizeSceneRefSpinBox.value(), 
                    window = self.gaussianSigmaSceneRefDoubleSpinBox.value())
                
                self.setSceneFilterFunction(indChannel, imgp.gaussianFilter1D.__name__, \
                    self.gaussianSizeSceneIndSpinBox.value(), \
                    window = self.gaussianSigmaSceneIndDoubleSpinBox.value())
                
            elif currentSceneFilter == "Binomial":
                self.setSceneFilterFunction(refChannel, imgp.binomialFilter1D.__name__, \
                    self.binomialOrderSceneRefSpinBox.value())
                
                self.setSceneFilterFunction(indChannel, imgp.binomialFilter1D.__name__, \
                    self.binomialOrderSceneIndSpinBox.value())
                
        currentScansFilter = self.scanFiltersComboBox.currentText()
        
        if len(currentScansFilter) > 0:
            if currentScansFilter == "Purelet":
                self.setScansFilterFunction(refChannel, imgp.pureDenoise.__name__, \
                    alpha = self.pureletAlphaScansRefDoubleSpinBox.value(), \
                    beta = self.pureletBetaScansRefDoubleSpinBox.value(),  \
                    sigma2 = self.pureletSigmaScansRefDoubleSpinBox.value(), \
                    levels = self.pureletJScansRefSpinBox.value(), \
                    threshold = self.pureletTScansRefSpinBox.value())
                
                self.setScansFilterFunction(indChannel, imgp.pureDenoise.__name__, \
                    alpha = self.pureletAlphaScansIndDoubleSpinBox.value(), \
                    beta = self.pureletBetaScansIndDoubleSpinBox.value(),  \
                    sigma2 = self.pureletSigmaScansIndDoubleSpinBox.value(), \
                    levels = self.pureletJScansIndSpinBox.value(), \
                    threshold = self.pureletTScansIndSpinBox.value())
            
            elif currentScansFilter == "Gaussian":
                self.setScansFilterFunction(refChannel, imgp.gaussianFilter1D.__name__, \
                    self.gaussianSizeScansRefSpinBox.value(), \
                    window = self.gaussianSigmaScansRefDoubleSpinBox.value())
                
                self.setScansFilterFunction(indChannel, imgp.gaussianFilter1D.__name__, \
                    self.gaussianSizeScansIndSpinBox.value(), \
                    window = self.gaussianSigmaScansIndDoubleSpinBox.value())
                
            elif currentScansFilter == "Binomial":
                self.setScansFilterFunction(refChannel, imgp.binomialFilter1D.__name__, \
                    self.binomialOrderScansRefSpinBox.value())
                
                self.setScansFilterFunction(indChannel, imgp.binomialFilter1D.__name__, \
                    self.binomialOrderScansIndSpinBox.value())
                
    @safeWrapper
    def generateScanRegionProfiles(self):
        """
        FIXME/TODO adapt to a new scenario where all scene image data is a single
        multi-channel VigraArray
        
        """
        if not isinstance(self._data_, ScanData):
            return
        
        if self._data_.analysisMode != ScanData.ScanDataAnalysisMode.frame:
            raise NotImplementedError("%s analysis not yet supported" % self._data_.analysisMode)
        
        if self._data_.type != ScanData.ScanDataType.linescan:
            raise NotImplementedError("%s not yet supported" % self._data_.type)

        self.generateScanRregionProfilesFromScans() 
        self.generateScanRegionProfilesFromScene() 

    @safeWrapper
    def generateScanRegionProfilesFromScene(self):
        """Generates scanline profiles from the scene rois
        
        FIXME/TODO adapt to a new scenario where all scene image data is a single
        multi-channel VigraArray
        
        Does this for all available channels, so it is application-agnostic
        
        The only required user input is to choose between raw and 
        filtered data for generating the profiles.
        
        """
        if not isinstance(self._data_, ScanData):
            return
        
        if self._data_.analysisMode != ScanData.ScanDataAnalysisMode.frame:
            raise NotImplementedError("%s analysis not yet supported" % self._data_.analysisMode)
        
        if self._data_.type != ScanData.ScanDataType.linescan:
            raise NotImplementedError("%s not yet supported" % self._data_.type)
        
        data = self._data_.scene
        target = self._data_.scanRegionSceneProfiles
        sigprefix = "Scene"
    
        # CAUTION the target is a neo.Block and its segments have all been initialized (as empty)
        # in _parse_image_arrays_
        
        # ATTENTION: the scans frames must ALL have an "x" axistag (the first non-temporal axis)
        # which si also the ONLY non-temporal axis in the case of linescans
        
        # ATTENTION: this will OVERWRITE analogsignals in all segments of the profile block
        
        if len(data) > 0:
            if len(self._data_.sceneRois) > 0:
                if len(data) == 1: 
                    # single array, either single-band or multi-band
                    # NOTE: 2017-11-22 21:49:35
                    # the following assumes scene is isotropic in "x" and "y" axes
                    # i.e. they have the same resolution; also implies "x" and "y"
                    # are both spatial axes
                    
                    # NOTE: 1st (outer) dim is frame; 2nd (inner) dim is channels
                    # the following conditions are met:
                    # len(profiles) == number of frames >>> True
                    # len(profiles[k]) == number of channels for k in range(number of frames) >>> all True
                    profiles = [[DataSignal(getProfile(img, self._data_.scanRegion.objectForFrame(k)), \
                                                sampling_period=getAxisResolution(img.axistags["x"]), \
                                                name="%s" % axisChannelName(subarray.axistags["c"], j), \
                                                index = j) \
                                            for j, img in dimEnum(subarray, "c")] \
                                    for k, subarray in dimEnum(data[0], self._data_.sceneFrameAxis)] \
                    
                    # NOTE: we want all channels from same frame to go into segment
                    # corresponding to frame
                    for k in range(data[0].shape[data[0].axistags.index(self._data_.sceneFrameAxis)]):
                        target.segments[k].analogsignals[:] = profiles[k]

                else: 
                    # NOTE: multiple channels stored separately as single-band arrays
                    # ATTENTION: they only have a singleton channel axis, but they must 
                    # ALL have the same number of frames -- checked in _parse_image_arrays_
                    #
                    
                    if len(self._data_.analysisOptions) == 0 or \
                        "Channels" not in self._data_.analysisOptions.keys() or \
                            "Reference" not in self._data_.analysisOptions["Channels"] or \
                                len(self._data_.analysisOptions["Channels"]["Reference"]) == 0:
                                    raise RuntimeError("No reference channel is defined, or it has no name, in %s" % self._data_var_name_)
                    
                    chNdx = self._data_.sceneChannelNames.index(self._data_.analysisOptions["Channels"]["Reference"])
                    
                    profiles = list()
                    
                    profiles = [[DataSignal(getProfile(subarray.bindAxis(self._data_.sceneFrameAxis, k), self._data_.scanRegion.objectForFrame(k)), \
                                                sampling_period=getAxisResolution(subarray.bindAxis(self._data_.sceneFrameAxis, k).axistags["x"]), \
                                                name="%s" % axisChannelName(subarray.axistags["c"], 0), index = j) \
                                            for j, subarray in enumerate(data)] \
                                    for k in range(self._data_.sceneFrames)]
                    
                    for k in range(data[chNdx].shape[data[chNdx].axistags.index(self._data_.sceneFrameAxis)]):
                        target.segments[k].analogsignals[:] = profiles[k]
                    
        #else:
            #warnings.warn("Data contains no scene!")
                
    @safeWrapper
    def generateScanRregionProfilesFromScans(self): 
        """Generates scanline profiles from the linescans X axis average.
        
        FIXME/TODO adapt to a new scenario where all scene image data is a single
        multi-channel VigraArray
        
        Does this for all available channels, so it is application-agnostic.
        
        The only required user input is to choose between raw and 
        filtered data for generating the profiles.
        
        """
        if not isinstance(self._data_, ScanData):
            return
        
        if self._data_.analysisMode != ScanData.ScanDataAnalysisMode.frame:
            raise NotImplementedError("%s analysis not yet supported" % self._data_.analysisMode)
        
        if self._data_.type != ScanData.ScanDataType.linescan:
            raise NotImplementedError("%s not yet supported" % self._data_.type)

        data = self._data_.scans
        target = self._data_.scanRegionSceneProfiles
        sigprefix = "Scans"
    
        # CAUTION: the target is a neo.Block and its segments have all been initialized (as empty)
        # in _parse_image_arrays_
        
        # ATTENTION: the scans frames must ALL have an "x" axistag (the first non-temporal axis)
        # which si also the ONLY non-temporal axis in the case of linescans
        
        # ATTENTION: this will OVERWRITE analogsignals in all segments of the profile block
        
        if len(data) > 0:
            if len(data) == 1: 
                # single array, either single-band or multi-band
                # SEE ALSO comments in self.generateScanRegionProfilesFromScene()
                profiles = [[DataSignal(np.array(img.mean(axis=1)), \
                                        sampling_period = getAxisResolution(img.axistags["x"]), \
                                        name="%s" % axisChannelName(subarray.axistags["c"], j), \
                                        index = j) \
                                    for j, img in dimEnum(subarray, "c")] \
                                for k, subarray in dimEnum(data[0], self._data_.scansFrameAxis)]

                for k in range(data[0].shape[data[0].axistags.index(self._data_.scansFrameAxis)]):
                    target.segments[k].analogsignals[:] = profiles[k]
                
            else: 
                # NOTE: multiple channels stored separately as single-band arrays
                # ATTENTION: they only have a singleton channel axis, but they must 
                # ALL have the same number of frames -- checked in _parse_image_arrays_
                #
                if len(self._data_.analysisOptions) == 0 or \
                    "Channels" not in self._data_.analysisOptions or \
                        "Reference" not in self._data_.analysisOptions["Channels"] or \
                            len(self._data_.analysisOptions["Channels"]["Reference"]) == 0:
                                raise RuntimeError("No reference channel is defined, or it has not been named, in %s" % self._data_var_name_)
                
                chNdx = self._data_.scansChannelNames.index(self._data_.analysisOptions["Channels"]["Reference"])
                
                profiles = [[DataSignal(np.array(subarray.bindAxis(self._data_.scansFrameAxis, k).mean(axis=1)), \
                                        sampling_period = getAxisResolution(subarray.bindAxis(self._data_.scansFrameAxis, k).axistags["x"]), \
                                        name="%s" % axisChannelName(subarray.axistags["c"],0), \
                                        index = j) \
                                    for j, subarray in enumerate(data)] \
                                for k in range(data[chNdx].shape[data[chNdx].axistags.index(self._data_.scansFrameAxis)])]
                
                for k in range(data[chNdx].shape[data[chNdx].axistags.index(self._data_.scansFrameAxis)]):
                    target.segments[k].analogsignals[:] = profiles[k]
                
        else:
            warnings.warn("Data contains no scans!")
                
    @safeWrapper
    def processData(self, progressSignal = None, setMaxSignal=None, **kwargs):#scene=True, channel = None, ):
        """Applies 2D filters frame-wise to raw scene or scans image data subsets.
        
        The function is meant to be called by a ProgressWorkerRunnable instance.
        
        FIXME/TODO adapt to a new scenario where all scene image data is a single
        multi-channel VigraArray
        
        Filters are defined in self._scene_filters_ and self._scans_filters_
        attributes, respectively, for scene and scans images.
        
        NOTE: selective processing of individual frames is not allowed (i.e. 
        ALL frames in the data subset should be processed with identical filter 
        parameters).
        
        Channels MAY be processed individually (or some channels omitted).
        
        ATTENTION: The filters are not supposed to modify axis resolution/calibration
        and axistags; processing is supposed to produce a result with shape and
        axistags identical to those of the source (with the exception of the number
        of channels).
        
        If this it not what is intended, then image arrays should be processed
        outside of the scandata API framework.
        
        CAUTION: Data is processed _IN_PLACE_: This function will overwrite any 
                source image data with the result of the processing
        
        Parameters:
        ===========
        
        scene: boolean (default True).
            When True (the default) the function processes the scene images;
            otherwise, it processed the scans images.
        
        channel: a str, an int, a sequence of str or a sequence of int, or None 
            (default is None, meaning all available raw data channels are processed)
            
        progressSignal: a callable Signal emitting an int, or None (default)
        
        """
        if not isinstance(self._data_, ScanData):
            return
        
        scene = kwargs.pop("scene", True)
        channel = kwargs.pop("channel", None)
        
        # choose what to process: data.scene or data.scans
        if scene:
            source = self._data_.scene
            source_chnames = self._data_.sceneChannelNames
            source_frames = self._data_.sceneFrames
            source_frameaxis = self._data_.sceneFrameAxis
            processing = self._scene_filters_
            #target = self._data_.scene
            #target_chnames = self._data_.sceneChannelNames
            
        else:
            source = self._data_.scans
            source_chnames = self._data_.scansChannelNames
            source_frames = self._data_.scansFrames
            source_frameaxis = self._data_.scansFrameAxis
            processing = self._scans_filters_
            #target = self._data_.scans
            #target_chnames = self._data_.scansChannelNames
            calibrations = self._data_.scansAxesCalibration
            
        if len(source) == 0:
            return
        
        if len(processing) == 0:
            return
        
        # figure out the channels to process
        if channel is None: 
            # no specific channel to process ⟹ process all channels
            process_channel_names = source_chnames
            process_channel_ndx = [source_chnames.index(c) for c in process_channel_names]
            untouched_channels_ndx = list()
            
        elif isinstance(channel, int):
            # channel specified by its index (int) ⟹ process indicated channel
            if channel < 0 or channel >= len(source_chnames):
                raise ValueError("Invalid channel index specified (%d) in %s" % (channel, self._data_var_name_))
            
            process_channel_names = [source_chnames[channel]]
            process_channel_ndx = [channel]
            untouched_channels_ndx = [[k for k in range(len(source_chnames)) if k != process_channel_ndx[0]]]
            
        elif isinstance(channel, str):
            # channel specified by its name ⟹ process named channel
            if channel not in source_chnames:
                raise ValueError("Channel %s not found in %s" % (channel, self._data_var_name_))
            
            process_channel_names = [channel]
            process_channel_ndx = [source_chnames.index(channel)]
            untouched_channels_ndx = [k for k in range(len(source_chnames)) if k != process_channel_ndx[0]]
            
        elif isinstance(channel, (tuple, list)):
            # specified a sequence of channel ⟹ process ONLY the channels specified
            if all([isinstance(c, str) for c in channel]):
                # channels to process are specified by name
                if any([c not in source_chnames for c in channel]):
                    raise ValueError("Not all specified channels (%s) were found in %s" % (channel, self._data_var_name_))
                
                process_channel_names = channel
                process_channel_ndx = [source_chnames.index(c) for c in channel]
                untouched_channels_ndx = [k for k in range(len(source_chnames)) if k not in process_channel_ndx]
                
            elif all([isinstance(c, int) for c in channel]):
                # channels to process are specified by int index
                if any([c < 0 or c >= len(source_chnames) for c in channel]):
                    raise ValueError("Invalid channel indices specified (%s) in %s" % (channel, self._data_var_name_))
                
                process_channel_names = [source_chnames[c] for c in channel]
                process_channel_ndx = channel
                untouched_channels_ndx = [k for k in range(len(source_chnames)) if k not in channel]
                
        else:
            raise TypeError("Invalid channel specification: %s for %s" % (channel, self._data_var_name_))
        
        # NOTE: 2022-11-18 22:05:54
        # the specified channels names MUST be present in the processing dict, 
        # as str keys, mapped to a dict with the following key/value pairs:
        #
        # "function" → the fully qualified name of the function (i.e. package.module.function_name)
        #   the package/module MUST have been already imported in this module
        #   FIXME/TODO: 2022-11-18 22:09:04 
        #   when factorising this code do NOT expect the above to happen; implement
        #   some dynamic module load/search rather than just going straight to eval
        #
        # "args" → a sequence (e.g. tuple, list) of positional (var-positional)
        #   parameters to the function in "function" (see above)
        #
        # "kwargs" → a mapping (e.g. a dict) with the var-keyword parameters of
        #   the function in "function" (see above)
    
        if any([c not in processing for c in process_channel_names]):
            raise ValueError("Processing functions are not defined for all channels")
        
        if len(source) == 1: # case when source data is a VigraArray (possibly, a multi-channel array)
            if source[0].channels != len(source_chnames):
                raise RuntimeError("Mismatch between reported channel names and actual number of channels")
            
            # allocate result array for purelet denoising -- same shape as source
            # NOTE: 2019-11-14 23:15:07 retain untouched channels
            result = [vigra.VigraArray(source[0].shape, init = True, value = 0, axistags = source[0].axistags)]

            # NOTE: 2019-10-12 14:51:54
            # does the actual processing of image frames in source
            for frame_index in range(source_frames):
                for chn_ndx in process_channel_ndx:
                    func   = eval(processing[process_channel_names[chn_ndx]]["function"])
                    args   = processing[process_channel_names[chn_ndx]]["args"]
                    kwargs = processing[process_channel_names[chn_ndx]]["kwargs"]
                
                    result[0].bindAxis("c", chn_ndx).bindAxis(source_frameaxis, frame_index)[:,:,:] = \
                        func(source[0].bindAxis("c", chn_ndx).bindAxis(source_frameaxis, frame_index), *args, **kwargs)
                    
                if progressSignal is not None:
                    progressSignal.emit(frame_index)
                    
                # retain untouched channels
                for ch_ndx in untouched_channels_ndx:
                    result[0].bindAxis("c", chn_ndx).bindAxis(source_frameaxis, frame_index)[:,:,:] = \
                        source[0].bindAxis("c", chn_ndx).bindAxis(source_frameaxis, frame_index)
                    
                if progresSignal is not None:
                    progressSignal.emit(frame_index)
                    
            source_chn_cal = AxesCalibration(source[0].axistags["c"])
            source_chn_cal.calibrateAxis(result[0].axistags["c"])
            
        else: # case when source data is a sequence of (single-channel) VigraArray objects
            if len(source) != len(source_chnames):
                raise RuntimeError("Mismatch between reported channel names and actual number of channels")
            
            # allocate list of arrays as the result for purelet denoising -- retain untouched channels
            result = [vigra.VigraArray(img, init=True, value=0, axistags = img.axistags) for img in source]

            # NOTE: 2019-10-12 14:54:10
            # process each image frame in the source  (in each channel)
            # parameters may be different for each channel hence they are indexed
            # using chn; this indexes into the process_channel_names list, to select
            # the key (channel name) mapped to the set of denoising parameters ("function",
            # "args", "kwargs")
            #print("processing", processing)
            for frame_index in range(source_frames):
                for chn_ndx in process_channel_ndx:
                    func   = eval(processing[process_channel_names[chn_ndx]]["function"])
                    args   = processing[process_channel_names[chn_ndx]]["args"]
                    kwargs = processing[process_channel_names[chn_ndx]]["kwargs"]
                    
                    result[chn_ndx].bindAxis(source_frameaxis, frame_index)[:,:,:] = \
                        func(source[chn_ndx].bindAxis(source_frameaxis, frame_index), *args, **kwargs)
                    
                # retain untouched channels
                for chn_ndx in untouched_channels_ndx:
                    result[chn_ndx].bindAxis(source_frameaxis, frame_index)[:,:,:] = \
                        source[chn_ndx].bindAxis(source_frameaxis, frame_index)
            
                if progressSignal is not None:
                    progressSignal.emit(frame_index)
                    
            for k in process_channel_ndx:
                chn_cal = AxesCalibration(source[k].axistags["c"])
                chn_cal.calibrateAxis(result[k].axistags["c"])
            
            #target[:] = result[:]
            #target_chnames[:] = process_channel_names
        
        self._data_.updateAxesCalibrations()
        
        self._processed_ = True
        
        return result# , process_channel_names

    @safeWrapper
    def _update_protocol_display_(self):
        # TODO: connect protocol table editing to the trigger protocols values
        # see NOTE: 2018-09-25 22:19:58
        signalBlockers = [QtCore.QSignalBlocker(widget) for widget in \
            (self.protocolTableWidget, self.protocolSelectionComboBox)]
        
        self.protocolTableWidget.clearContents()
        self.protocolSelectionComboBox.clear()
        
        if self._data_ is None or len(self._data_.triggers) == 0:
            return
        
        self.protocolSelectionComboBox.addItems(["All"] + [p.name for p in self._data_.triggers] + ["Select..."])
        
        self.protocolTableWidget.setRowCount(len(self._data_.triggers))
        
        for k in range(len(self._data_.triggers)):
            # columns:
            # 0 = protocol name
            # 1 = presynaptic times
            # 2 = postsynaptic times
            # 3 = photostimulation times
            # 4 = imaging delay
            # 5 = frame indices
            
            self.protocolTableWidget.setItem(k, 0, QtWidgets.QTableWidgetItem(self._data_.triggers[k].name))
            
            if self._data_.triggers[k].presynaptic is not None:
                evt_times = self._data_.triggers[k].presynaptic.times
                #print("_update_protocol_display_: presyn times in %s" % self._data_.triggers[k].name, evt_times)
                
                if evt_times.size == 1:
                    txt = "%g" % evt_times
                    
                elif evt_times.size > 1:
                    txt = ", ".join(["%g" % i for i in evt_times])
                
                else:
                    txt = ""
                    
                self.protocolTableWidget.setItem(k, 1, QtWidgets.QTableWidgetItem(txt) )
        
            if self._data_.triggers[k].postsynaptic is not None:
                evt_times = self._data_.triggers[k].postsynaptic.times
                #print("_update_protocol_display_: postsyn times in %s" % self._data_.triggers[k].name, evt_times)
                 
                if evt_times.size == 1:
                    txt = "%g" % evt_times
                    
                elif evt_times.size > 1:
                    txt = ", ".join(["%g" % i for i in evt_times])
                    
                else:
                    txt = ""
                    
                self.protocolTableWidget.setItem(k, 2, QtWidgets.QTableWidgetItem(txt))
        
            if self._data_.triggers[k].photostimulation is not None:
                evt_times = self._data_.triggers[k].photostimulation.times
                #print("_update_protocol_display_: photostim times in %s" % self._data_.triggers[k].name, evt_times)
                
                if evt_times.size == 1:
                    txt = "%g" % evt_times
                    
                elif evt_times.size > 1:
                    txt = ", ".join(["%g" % i for i in evt_times])
                else:
                    txt = ""
                    
                self.protocolTableWidget.setItem(k, 3, QtWidgets.QTableWidgetItem(txt))
                
            txt = "%g" % self._data_.triggers[k].imagingDelay.magnitude.flatten()[0]
            #print("imaging delay txt", txt)
            
            self.protocolTableWidget.setItem(k, 4, QtWidgets.QTableWidgetItem(txt))
                
            if len(self._data_.triggers[k].segmentIndices()) > 0:
                txt = ", ".join(["%g" % i for i in self._data_.triggers[k].segmentIndices()])
                self.protocolTableWidget.setItem(k, 5, QtWidgets.QTableWidgetItem(txt))
                
        #self.protocolTableWidget.itemChanged[QtWidgets.QTableWidgetItem].connect(self.slot_protocolTableEdited, type = QtCore.Qt.QueuedConnection)
        
    @safeWrapper
    def setData(self, newdata = None, doc_title=None, **kwargs):
        """When newdata is None this resets everything to their defaults"""
        uiParamsPrompt = kwargs.pop("uiParamsPrompt", False)
        
        if uiParamsPrompt:
            # TODO 2023-01-18 08:48:13
            pass
            # print(f"{self.__class__.__name__}.setData uiParamsPrompt")
            
        # NOTE: 2021-07-08 13:40:23
        # called by ScyipenViewer superclass
        self._clear_contents_()
        
        if isinstance(newdata, ScanData):
            #print(newdata.name, doc_title)
            if not isinstance(doc_title, str) or len(doc_title.strip()) == 0:
                if len(newdata.name.strip()):
                    doc_title = newdata.name
                    
                elif isinstance(self._data_var_name_, str) and len(self._data_var_name_.strip()):
                    doc_title = self._data_var_name_
                    
                else:
                    doc_title = "ScanData"
                    
            self._parsedata_(newdata, doc_title)
            
            self._data_modifed_(False)
            
            self.generateFilters()
            
            self._init_viewers_() # this MAY modify data (if scan region scene profile is enabled)
            
            self.displayFrame()
            
        else:
            # TODO in _parsedata_: when nothing is passed reset everything
            self._data_ = None
            self._data_var_name_ = None
            #self._clear_contents_()
            
    @Slot()
    @safeWrapper
    def slot_Quit(self):
        print("%s.slot_Quit %s" % (self.__class__.__name__, self.winTitle))
        self.close()
        #evt = QtGui.QCloseEvent()
        #self.closeEvent(evt)

    def closeEvent(self, evt):
        """Overrides ScipyenFrameViewer.closeEvent() for clean up.
        """
        #print("%s.closeEvent %s:" % (self.__class__.__name__, self.winTitle))
        #print("LSCaTWindow.closeEvent: isTopLevel", self.isTopLevel)
        
        #print("%s.closeEvent %s save settings" % (self.__class__.__name__, self.winTitle))
        self.saveSettings()
        self._clear_contents_()
        
        # NOTE: 2021-07-08 10:27:14
        # close client viewers and remove their references
        try: 
            #print("%s.closeEvent %s Closing client windows" % (self.__class__.__name__, self.winTitle))
            if len(self.sceneviewers) > 0:
                for k, win in enumerate(self.sceneviewers):
                    #saveWindowSettings(qsettings, win, 
                                       #prefix = "%s_%d" % (win.__class__.__name__, k))
                    win.close()
            self.sceneviewers.clear()
                        
            if len(self.scansviewers) > 0:
                for k, win in enumerate(self.scansviewers):
                    #saveWindowSettings(qsettings, win, 
                                       #prefix = "%s_%d" % (win.__class__.__name__, k))
                    win.close()
            self.scansviewers.clear()
                        
            if len(self.profileviewers) > 0:
                for win in self.profileviewers:
                    #saveWindowSettings(qsettings, win, 
                                       #prefix = "%s" % win.__class__.__name__)
                    win.close()
            self.profileviewers.clear()
            
            if len(self.ephysviewers):
                for win in self.ephysviewers:
                    #saveWindowSettings(qsettings, win, 
                                       #prefix = "%s" % win.__class__.__name__)
                    win.close()
            self.ephysviewers.clear()
                    
            if len(self.scansblockviewers):
                for win in self.scansblockviewers:
                    #saveWindowSettings(qsettings, win, 
                                       #prefix = "%s" % win.__class__.__name__)
                    win.close()
            self.scansblockviewers.clear()
                    
            if len(self.sceneblockviewers):
                for win in self.sceneblockviewers:
                    #saveWindowSettings(qsettings, win, 
                                       #prefix = "%s" % win.__class__.__name__)
                    win.close()
            self.sceneblockviewers.clear()
                    
            #saveWindowSettings(qsettings, self.reportwindow, 
                                #prefix = "%s" % win.__class__.__name__)
            self.reportWindow.close()
                
        except Exception as e:
            traceback.print_exc()
            
        self._data_ = None
        
        if self.isTopLevel:
            if any([v is self for v in self.appWindow.workspace.values()]):
                self.appWindow.deRegisterWindow(self) # this will also save settings and close the viewer window
                self.appWindow.removeFromWorkspace(self, by_name=False)
                # self.appWindow.slot_updateWorkspaceModel()

        #print("%s.closeEvent %s Call super().closeEvent" % (self.__class__.__name__, self.winTitle))
        # NOTE: 2021-07-08 15:59:47
        # call below needed so that the  LSCaTwindow instance is removed from 
        # Scipyen's main window workspace'
        #super().closeEvent(evt) 
        # finally close this window
        
        #print("%s.closeEvent %s accept event" % (self.__class__.__name__, self.winTitle))
        evt.accept()
        #self.close()
        
    def _clear_contents_(self):
        if self._data_ is None:
            return
        # see NOTE: 2018-09-25 22:19:58
        signalBlockers = [QtCore.QSignalBlocker(widget) for widget in \
            (self.selectCursorSpinBox, self.analysisUnitNameLineEdit, 
             self.cursorXposDoubleSpinBox, self.cursorYposDoubleSpinBox, 
             self.cursorXwindow, self.cursorYwindow, 
             self.unitTypeComboBox, self.defineAnalysisUnitCheckBox)]
        # signalBlockers = [QtCore.QSignalBlocker(widget) for widget in \
        #     (self.scanDataNameLineEdit, self.cellLineEdit, self.fieldLineEdit,
        #      self.selectCursorSpinBox, self.analysisUnitNameLineEdit, 
        #      self.cursorXposDoubleSpinBox, self.cursorYposDoubleSpinBox, 
        #      self.cursorXwindow, self.cursorYwindow, 
        #      self.unitTypeComboBox, self.genotypeComboBox,
        #      self.sexComboBox, self.defineAnalysisUnitCheckBox)]

        #self.scanDataNameLineEdit.editingFinished.disconnect(self.slot_setDataName)
        #self.cellLineEdit.editingFinished.disconnect(self.slot_gui_changed_cell_name)
        #self.fieldLineEdit.editingFinished.disconnect(self.slot_gui_changed_field_name)
        #self.selectCursorSpinBox.valueChanged[int].disconnect(self.slot_gui_spinbox_select_cursor_by_index)
        
        #self.analysisUnitNameLineEdit.editingFinished.disconnect(self.slot_gui_changed_analysis_unit_name)
        #self.cursorXposDoubleSpinBox.valueChanged[float].disconnect(self.slot_gui_changed_cursor_x_pos)
        #self.cursorYposDoubleSpinBox.valueChanged[float].disconnect(self.slot_gui_changed_cursor_y_pos)
        #self.cursorXwindow.valueChanged[float].disconnect(self.slot_gui_changed_cursor_xwindow)
        #self.cursorYwindow.valueChanged[float].disconnect(self.slot_gui_changed_cursor_ywindow)
        #self.unitTypeComboBox.currentIndexChanged[str].disconnect(self.slot_gui_changed_unit_type_string)
        #self.defineAnalysisUnitCheckBox.stateChanged[int].disconnect(self.slot_change_analysis_unit_state)

        if isinstance(self._data_.sceneRois, dict):
            for r in self._data_.sceneRois.values():
                r.frontends.clear()
            
        if isinstance(self._data_.sceneCursors, dict):
            for c in self._data_.sceneCursors.values():
                c.frontends.clear()
        
        if isinstance(self._data_.scansRois, dict):
            for r in self._data_.scansRois.values():
                r.frontends.clear()
            
        if isinstance(self._data_.scansCursors, dict):
            for c in self._data_.scansCursors.values():
                c.frontends.clear()
                
        if hasattr(self._data_, "scanRegion") and isinstance(self._data_.scanRegion, pgui.PlanarGraphics):
            self._data_.scanRegion.frontends.clear()
            
        if len(self.sceneviewers):
            for k, w in enumerate(self.sceneviewers):
                w.clear()

        if len(self.scansviewers):
            for k, w in enumerate(self.scansviewers):
                w.clear()
                
        if len(self.profileviewers):
            w = self.profileviewers[0]
            w.clear()
            
        if len(self.scansblockviewers):
            w = self.scansblockviewers[0]
            w.clear()
        
        if len(self.ephysviewers):
            w = self.ephysviewers[0]
            w.clear()
            
        if self.reportWindow.isVisible():
            self.reportWindow.clear()
            
        
        # self.scanDataVarNameLabel.clear()
        # self.scanDataNameLineEdit.clear()
        # self.cellLineEdit.clear()
        # self.fieldLineEdit.clear()
        self.analysisUnitNameLineEdit.clear()
        self.selectCursorSpinBox.setValue(-1)
        self.unitTypeComboBox.setCurrentIndex(0)
        # self.genotypeComboBox.setCurrentIndex(0)
        # self.sexComboBox.setCurrentIndex(0)
        
        self.protocolTableWidget.clearContents()
        self.protocolTableWidget.setRowCount(0)
        
        self._selected_analysis_cursor_ = None
        self._selected_analysis_unit_ = None
        
        self._data_ = None
        self._data_var_name_ = None
                    
    @safeWrapper
    def _link_scans_vcursor_to_scene_pcursor_(self, obj):
        if self._data_ is None:
            return
        
        self._data_._upgrade_API_()
        
        if self._data_.scanRegion is None:
            return

        #scanline = self._data_.scanRegion
        
        point_x = None
        point_y = None
        
        #(point_x, point_y) = vCursorPos2ScanlineCoords(obj, self._data_.scanRegion, span = self._data_.scans[0].width)
        (point_x, point_y) = vCursor2ScanlineProjection(obj, 
                                                        self._current_frame_scan_region_, 
                                                        span = self._data_.scans[0].width)
        
        #print("_link_scans_vcursor_to_scene_pcursor_ point_x", point_x, "point_y", point_y)
        if point_x is not None and point_y is not None:
            pc = pgui.Cursor(point_x, point_y,
                            self._data_.scene[0].shape[0], self._data_.scene[0].shape[1],
                            1, 1, obj.xwindow//2,
                            name = obj.name,
                            graphicstype = pgui.GraphicsObjectType.point_cursor)
            
            pc.frameIndices = obj.frameIndices
            
            #pc.linkFrames(hard = obj.hasHardFrameAssociations)
            #obj.linkToObject(pc, mapScansVCToScenePCOnPath, self._data_.scanRegion, span = self._data_.scans[0].width)
            obj.linkToObject(pc, mapScansVCToScenePCOnPath, 
                             self._current_frame_scan_region_, 
                             span = self._data_.scans[0].width)
            
            # add linked point cursor to the scene
            self._data_.sceneCursors[obj.name] = pc
            
            return pc
    
        else:
            raise NotImplementedError("Mirror point cursors not implemented for %s" % self._data_.scanRegion.type)
    
    @safeWrapper
    def _selectDisplayChannels_(self, scene=True):
        if self._data_ is None:
            return
        
        if scene:
            chnames = self._data_.sceneChannelNames
            item = "scene"
        else:
            chnames = self._data_.scansChannelNames
            item ="scan"
            
        ret = pgui.checkboxDialogPrompt(self, "Select %s channels:" % item, chnames)
        
        return [chnames[k] for (k,v) in enumerate(ret) if v]
        

    @safeWrapper
    def _displayChannels_(self, scene=True, channels=None):
        """Display selected channels in scene or frame data.
        
        scene: bool; when True (default), displays selected scene channels, 
            otherwise displays selected channels in the frame scans;
            
        channels: None (default), or a list of valid int channel indices (0-based)
            or a list of valid channel names
        """
        if self._data_ is None:
            return
        
        if scene:
            what = self._data_.scene
            wins = self.sceneviewers
            chnames = self._data_.sceneChannelNames
            data_subset = "scene data"
            
        else:
            what = self._data_.scans
            wins = self.scansviewers
            chnames = self._data_.scansChannelNames
            data_subset = "scan data"
        
        if len(what)==1:
            return
        
        if channels is None or len(channels) == 0:
            channels = [k for k in range(len(what))]
            
            for (k,win) in enumerate(wins):
                win.view(what[k])
                win.setVisible(True)
                
        elif isinstance(channels, (tuple, list)) and all([isinstance(c, str) for c in channels]):
            chindex = list()
            
            for c in channels:
                if c not in chnames:
                    raise ValueError("%s channel does not exist in %s." % (c, data_subset))
                
                chindex.append(chnames.index(c))
                
            for(k, win) in enumerate(wins):
                win.setVisible(k in chindex)
                if k in chindex:
                    win.view(what[k])
                        
        elif isinstance(channels, (tuple, list)) and all([isinstance(chindex, int) for chindex in channels]):
            for chindex in channels:
                if chindex < 0 or chindex >= len(what):
                    raise ValueError("Invalid channel index (%d) for %s." % (chindex, data_subset))
                
            for (k, win) in enumerate(wins):
                win.setVisible(k in chindex)
                if k in chindex:
                    win.view(what[k])
                        
        else:
            raise TypeError("channels is expected to be a list of str or int, or None")
                
def addSex(data, value):
    """Creates a 'Sex' column in the data.
    Parameters:
    ==========
    data: pandas.DataFrame with LSCaT results
    value = string, one of "m", "f", "na" (case-insensitive)
    
    ATTENTION: Data should all have the same source, otherwise the sex will be 
        coerced to "na"
        
    Modifies data in-place; the columns will be inserted after the source column,
    if present, or as the first column
    
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Expecting a pandas.DataFrame; got %s instead" % type(data).__name__)
    
    if not isinstance(value, str):
        raise TypeError("value parameter expectd a str; got %s instead" % type(value).__name__)
    
    if value.lower().strip() not in ("f", "m", "na"):
        raise ValueError("Sex expected to be one of 'f', 'm', or 'na' (case-insensitive); got %s instead" % value)
    
    if "Source" in data.columns:
        if all([s == data.Source[0] for s in data.Source]):
            gdr = pd.Series([value] * len(data.Source), name="Sex").astype("category")
            
        else:
            warnings.warn("Not all data have the same source; coercing Sex to 'NA'")
            gdr = pd.Series(["NA"] * len(data.Source), name="Sex").astype("category")
            
        data.insert(1, gdr)
        
    else:
        gdr = pd.Series([value] * len(data.Source), name="Sex").astype("category")
        index = data.columns.index("Source")
        data.insert(index, gdr)
        
def clean_NA(data):
    """
    CAUTION 2018-12-14 16:54:46
    Replaces the string "NA" with np.nan to represent missing values in numerical columns 
    (bad idea to use "NA", but initially used to export result to csv
    importable into R dataframe objects, BEFORE we started to use pandas)
                
    This should have already been done by CaTanalysis.LSCaTWindow.slot_collate_reports
    
    Returns:
    =======
    None (modifies data in-place)
    
    """
    #columns = ["Dendrite_Length", "Dendrite_Width", "Spine_Length", "Spine_Width"]
    
    for col in ("Age", "Branch_Order", "Branching_Points", "Distance_From_Soma", "Dendrite_Length", "Dendrite_Width", "Spine_Length", "Spine_Width"):
        #print(col)
        NA_index = [isinstance(v, str) and v == "NA" for v in data.loc[:,col]]
        data.loc[NA_index, col] = np.nan
        data[col].astype(np.float64, copy=False)
        
def fixAnalysisDateTime(data):
    """Changes the type of Analysis_Date_Time from string to datetime.
    
    More precisely, to the datetime64[ns] (numpy.dtype("<M8[ns]") i.e. "timestamp")
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Expecting a pandas.DataFrame; got %s instead" % type(data).__name__)

    if "Analysis_Date_Time" not in data.columns:
        raise KeyError("columns %s not found in data" % "Analysis_Date_Time")
    
    for k in range(data.Analysis_Date_Time.index.size):
        date_time = datetime.datetime.strptime(data.loc[k, "Analysis_Date_Time"], "%Y-%m-%d %H:%M:%S.%f")
        data.loc[k, "Analysis_Date_Time"] = date_time
    
    data.Analysis_Date_Time = data.Analysis_Date_Time.astype(np.dtype("<M8[ns]"))
    
def categorize_somatic_distance(data, bin_edges = (0,150,250,300)):
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Expecting a pandas.DataFrame; got %s instead" % type(data).__name__)

    #bin_edges = (0, 150, 250, 300)
    categoriseNumericalData(data, "Distance_From_Soma", bin_edges, "somatic_dist_2")
    
def convert_Branch_Order_to_category(data):
    """Does what its name says.
    Modifies data in place!
    """
    
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Expecting a pandas.DataFrame; got %s instead" % type(data).__name__)
    
    data.Branch_Order = pd.Categorical(data.Branch_Order.astype("category"))
    
def categorize_branching_points(data, bin_edges=(2,6,9)):
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Expecting a pandas.DataFrame; got %s instead" % type(data).__name__)

    #bin_edges= (2,6,9)
    categoriseNumericalData(data, "Branching_Points", bin_edges, "br_points_2")
    
def renameColumn(data, old_name, new_name, inplace = True):
    # NOTE: 2019-01-15 14:34:24 as a side note:
    # quickly rename one column
    
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Expecting a pandas.DataFrame; got %s instead" % type(data).__name__)

    if not isinstance(old_name, str):
        raise TypeError("old_name expected to be a string; got %s instead" % type(old_name).__name__)

    if not isinstance(new_name, str):
        raise TypeError("new_name expected to be a string; got %s instead" % type(new_name).__name__)
    
    if new_name in data.columns:
        raise ValueError("column %s already exists" % new_name)

    if old_name not in data.columns:
        raise KeyError("column %s does not exist in data" % old_name)
    
    old_names = [n for n in data.columns]
    new_names = old_names.copy()
    new_names[new_names.index(old_name)] = new_name
    
    if inplace:
        data.rename(columns = dict(zip(old_names, new_names)), inplace = inplace)
        
    else:
        return data.rename(columns = dict(zip(old_names, new_names)), copy = True, inplace = inplace)
    
            
def addAge(data, value):
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Expecting a pandas.DataFrame; got %s instead" % type(data).__name__)
    
        if isinstance(value, str):
            if value.strip().lower() != "na":
                raise ValueError("When a str, age must be 'NA'; got %s instead" % age)
            
            age = "NA"
            
        elif value is None:
            age = "NA"
            
        elif isinstance(value, datetime.timedelta):
            days = value.days
            seconds = value.seconds
            musecs = value.microseconds
            
            # NOTE: round up to the largest time unit
            
            if days == 0:
                # maybe seconds
                if seconds == 0:
                    age = musecs * pq.us
                
                else:
                    if musecs == 0:
                        age = seconds * pq.s
                        
                    else:
                        age = value.total_seconds() * pq.s
                        
            else:
                # just report age as days
                age = days * pq.day
                
        elif isinstance(value, pq.Quantity):
            if not check_time_units(value):
                raise TypeError("Expecting a time quantity; got %s instead" % type(value).__name__)
            
            age = value
            
            
        else:
            raise TypeError("Expecting a str ('NA'), a datetime.timedelta, a python time quantity, or None; got %s instead" % type(value).__name__)
        
        age_series = pd.Series([age] * len(data.index), name="Age")
        
        if "Source" in data.columns:
            if "Sex" in data.columns:
                index = data.columns.index("Sex")
            
            else:
                index = data.columns.index("Source")
                
        else:
            index = 0
            
        data.insert(index, age_series)
            
def addSource(data):
    """Creates a 'Source' column in the data 
    Animal ID is extracted from the string values in the "Cell" column by
    concatenating all but the last "."-separated tokens in the string 
    NOTE: This requires that the "Cell" field must contain "."-separated tokens, e.g.
    AnimalID.<something_else>.cell, etc.
    """
    # NOTE: 2019-01-14 21:31:48
    #  __sample_source__ field (str) defined in the datatypes.AnalysisUnit
    # TODO: adapt LSCaTWindow and datatypes.ScanData code for it to be used as 
    # sample (material) source for the culture/animal/patient ID column, in the 
    # future
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Expecting a pandas.DataFrame; got %s instead" % type(data).__name__)
    
    sources = list()
    
    for k in range(data.index.size):
        source = data.loc[k,"Cell"].split(".")
        
        if len(source) == 0:
            source = "NA"
            
        elif len(source) in (1,2):
            source = source[0]
            
            if len(source) == 0:
                source = "NA"
                
        else:
            source = ".".join(source[:-1])
                          
        sources.append(source)
        
    #sources = pd.Series([".".join(data.loc[k,"Cell"].split(".")[:-1]) for k in range(data.index.size)])
    sources = pd.Series(sources)
    sources.name = "Source"
    
    # force new "Animal" column to be the second column
    if "Source" in data.columns:
        if [s for s in data.columns].index("Source") != 2:
            del(data["Source"]) # less cumbersome than re-indexing the columns
            
        else:
            return

    data.insert(1, "Source", sources.astype("category"))
    
def renameCategory(data, level, old_name, new_name):
    """Renames a the category given by "old_name" to that in "new_name".
    
    Parameters:
    ===========
    
    data: pandas DataFrame. A LSCaT analysis result
    
    level: str. Name of a factor (categorical) column
    
    old_name: str. Name of a category in column given by "level"
    
    new_name: str. New cateogry name
    
    Returns:
    ========
    
    None. 
    
    CAUTION: Modifies data IN PLACE.
    
    Raises error when:
        * data is not a DataFrame,
        * level is not a categorical column in data
    
    Does nothing is old_name is not a category in level
    
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Expecting a pandas Data Frame; got %s instead" % type(data).__name__)
    
    if level not in data.columns:
        raise KeyError("Column %s not found" % level)
    
    if not isinstance(data[level].dtype, pd.api.types.CategoricalDtype):
        raise TypeError("Column %s is not categorical" % level)
    
    if old_name not in data[level].cat.categories:
        return
    
    old_categories = [c for c in data.Protocol.cat.categories]
    
    new_categories = [c for c in data.Protocol.cat.categories]
    
    new_categories[old_categories.index(old_name)] = new_name
    
    category_name_map = dict(zip(old_categories, new_categories))
    
    data.Protocol = data.Protocol.cat.rename_categories(category_name_map)
    
    
def categoriseLSCaTResult(data, inplace=True):
    """Converts a pre-defined set of columns to categorical data type in a LSCaT result DataFrame
    
    Positional parameters:
    ======================
    
    data -- pandas DataFrame containing a CaTanalysis result
    
    Named parameters:
    =================
    
    inplace -- boolean. When True (default) the data is modified in place. Otherwise,
        returns a new DataFrame.
        
        
    Returns:
    =======
    None if "inplace" parameter is True, otherwise, returns a copy of the data 
        where the columns in the pre-defined are set to categorical data type.
    
    
    NOTE: The pre-defined columns set to contain categorical data are:
    
    "Data", "Cell", "Field", "Unit", "Unit_Type", "Protocol", and 
    "somatic_distance"
    
    """
    
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Expecting a pandas Data Frame; got %s instead" % type(data).__name__)
    
    if "Data" not in data.columns:
        raise KeyError("Data not found in data columns")
    
    if "Cell" not in data.columns:
        raise KeyError("Cell not found in data columns")
    
    if "Field" not in data.columns:
        raise KeyError("Field not found in data columns")
    
    if "Unit" not in data.columns:
        raise KeyError("Unit not found in data columns")
    
    if "Unit_Type" not in data.columns:
        raise KeyError("Unit_Type not found in data columns")
        
    if "Protocol" not in data.columns:
        raise KeyError("Protocol not found in data columns")
        
    if "somatic_distance" not in data.columns:
        raise KeyError("somatic_distance not found in data columns")
    
    if inplace:
        data.Data = pd.Categorical(data.Data.astype("category"))
        data.Cell = pd.Categorical(data.Cell.astype("category"))
        data.Field = pd.Categorical(data.Field.astype("category"))
        data.Unit = pd.Categorical(data.Unit.astype("category"))
        data.Unit_Type = pd.Categorical(data.Unit_Type.astype("category"))
        data.Protocol = pd.Categorical(data.Protocol.astype("category"))
        data.somatic_distance = pd.Categorical(data.somatic_distance.astype("category"))
        
        #return data
        return 
        
    else:
        ret = data.copy()
        ret.Data = pd.Categorical(data.Data.astype("category"))
        ret.Cell = pd.Categorical(data.Cell.astype("category"))
        ret.Field = pd.Categorical(data.Field.astype("category"))
        ret.Unit = pd.Categorical(data.Unit.astype("category"))
        ret.Unit_Type = pd.Categorical(data.Unit_Type.astype("category"))
        ret.Protocol = pd.Categorical(data.Protocol.astype("category"))
        ret.somatic_distance = pd.Categorical(data.somatic_distance.astype("category"))
        
        return ret
        
        
def normaliseLSCaTResultVariables(data, 
    parameter=('Amplitude_EPSCaT_0', 'Fit_EPSCaT_0_Amplitude','Fit_EPSCaT_0_taudecay_0', 'Integration_EPSCaT_Simpson'),
    normalising_level = "Protocol", 
    normalising_reference_category = "1bAP", 
    normalising_target_categories = ("1bAP", "2bAP", "3bAP", "5bAP"),
    return_columns = ("Data", "Cell", "Field", "Unit", "Unit_Type", \
                        "Protocol", "Fit_Rsq", "FailSuccess_EPSCaT_0_success", \
                        "Branch_Order", "Branching_Points", \
                        "Dendrite_Length", "Dendrite_Width", \
                        "Spine_Length", "Spine_Width", \
                        "Distance_From_Soma", "somatic_distance", \
                        "averaged"),
    inplace=True):
    
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Expecting a pandas Data Frame; got %s instead" % type(data).__name__)
    
    if isinstance(parameter, str):
        if parameter not in data.columns:
            raise KeyError("parameter %s not found in data columns" % parameter)
        
        params = [parameter]
        
    elif isinstance(parameter, (tuple, list)) and all([isinstance(p, str) for p in parameter]):
        if any([p not in data.columns for p in parameter]):
            raise ValueError("some parameters in %s not found in data columns" % repr(parameter))
        
        params = [p for p in parameter]
        
    norm_series_names = ["%s_norm_to_%s" % (p, normalising_reference_category) for p in params]
    
    norm_series = [pd.Series(np.nan, index = data.index, name=n) for n in norm_series_names]
    
    cells = data.Cell.cat.categories
    fields = data.Field.cat.categories
    units = data.Unit.cat.categories
    norm_categories = data[normalising_level].cat.categories
    
    if normalising_reference_category not in norm_categories:
        warnings.warn("normalisation reference category %s not found in normalising level %s" % (normalising_reference_category, normalising_level), RuntimeWarning)
        return
        
    # index of data with the reference level to which we normalize (e.g. "1bAP")
    norm_ref_ndx = data[normalising_level] == normalising_reference_category
    
    for cell in cells:
        cellndx = data.Cell == cell # indexing by cell
        
        for field in fields:
            fieldndx = data.Field == field # indexing by field
            
            for unit in units:
                unitndx = data.Unit == unit # indexing by unit name
                
                fullndx = cellndx & fieldndx & unitndx # compound indexing for given cell, field and unit name
                
                if not fullndx.any(): # skip data NOT with the specified cell, field, unit name
                    continue
                
                refndx = fullndx & norm_ref_ndx
                
                if not refndx.any():
                    continue
                
                for category in normalising_target_categories: # these are protocols!
                    #print("normalised category %s" % category)
                    ndx = data[normalising_level] == category # data at category to be normalized
                    
                    if not np.any(ndx): # skip data with missing such category
                        continue
                    
                    targetndx = fullndx & ndx # the data of given cell field unit name and category
                    
                    if not targetndx.any(): # skip data that does not belong to given cell field unit name and category
                        continue

                    if data.loc[refndx, "FailSuccess_EPSCaT_0_success"].all():
                        for kp, p in enumerate(params):
                            try:
                                a = data.loc[targetndx, p].astype(np.float64).iloc[0] # data _to_be_ normalized
                                b = data.loc[refndx, p].astype(np.float64).iloc[0] # data to normalize _to_
                                
                                value = a/b
                                
                                norm_series[kp][targetndx] = value
                                
                            except Exception as e:
                                print("at target location [%s, %s]" % (np.where(targetndx), p))
                                print("at reference location [%s, %s]" % (np.where(refndx), p))
                                raise e
                        
    if inplace:
        for s in norm_series:
            data[s.name] = s
            
        return
            
    else:
        #ret = data.copy()
        # NOTE: 2019-01-08 22:47:22
        # when NOT in-place, return a data frame containing only the 
        # housekeeping columns, PLUS the normalized ones
        # Housekeeping columns are listed here:
        # column name: dtype:
        #=================
        # Data: category
        # Cell: category
        # Field: category
        # Unit: category
        # Unit_Type: category
        # Branch_Order: int64
        # Branching_Points: int64
        # Dendrite_Length: object
        # Dendrite_Width: object
        # Distance_From_Soma: float64
        # Spine_Length: object
        # Spine_Width: object
        # averaged: bool
        # somatic_distance: category
        # Protocol: category
        # Segment: object
        # Analysis_Date_Time: object
        # Fit_Rsq: float64
        # FailSuccess_EPSCaT_0_success: bool
        # FailSuccess_EPSCaT_0_2D: bool
        # somatic_distance_broad: category
        # branching_points_broad: category
        # somatic_dist_2: category
        
        #housekeeping_columns = ["Data", "Cell", "Field", "Unit", "Unit_Type", \
                                #"Protocol", "Segment", "Analysis_Date_Time", \
                                #"Fit_Rsq", "FailSuccess_EPSCaT_0_2D", "FailSuccess_EPSCaT_0_success", \
                                #"Branch_Order", "Branching_Points", \
                                #"Dendrite_Length", "Dendrite_Width", \
                                #"Spine_Length", "Spine_Width", \
                                #"Distance_From_Soma", "somatic_distance", \
                                #"somatic_distance_broad", "somatic_dist_2", \
                                #"branching_points_broad", 
                                #"averaged"]

        #housekeeping_columns = ["Data", "Cell", "Field", "Unit", "Unit_Type", \
                                #"Protocol", "Segment", "Analysis_Date_Time", \
                                #"Fit_Rsq", "FailSuccess_EPSCaT_0_2D", \
                                #"FailSuccess_EPSCaT_0_success", \
                                #"Branch_Order", "Branching_Points", \
                                #"Dendrite_Length", "Dendrite_Width", \
                                #"Spine_Length", "Spine_Width", \
                                #"Distance_From_Soma", "somatic_distance", \
                                #"averaged"]
        
        #housekeeping_columns = ["Data", "Cell", "Field", "Unit", "Unit_Type", \
                                #"Protocol", "Fit_Rsq", "FailSuccess_EPSCaT_0_success", \
                                #"Branch_Order", "Branching_Points", \
                                #"Dendrite_Length", "Dendrite_Width", \
                                #"Spine_Length", "Spine_Width", \
                                #"Distance_From_Soma", "somatic_distance", \
                                #"averaged"]

        ret = pd.DataFrame()
        
        for c in return_columns:
            ret[c] = data[c]
        

        for s in norm_series:
            ret[s.name] = s
            
        return ret
    
def categoriseNumericalData(data, parameter, values, name, inplace=True):
    """Generates a categorical column for a specified numerical data columns in DataFrame data.
    
    Useful to generate categorical "bins" from a numerical column, e.g. from
    morphometric parameters
    
    Parameters:
    ===========
    data: a pandas.DataFrame having column index 
    
    parameter: a valid column index element for data 
            (typically/usually, a string but this depends on data.columns.dtype)
            
    values: a sequence (tuple, list) with bin edges for the categories
            this is typically the bin_edges result of np.histogram()
            
            For example, to generate three categories, call:
            
            counts, bin_edges = np.histogram(x, 3)
            
            counts: 
            
    Returns:
    =======
    
    When in-place is True, returns None.
        The pandas.DataFrame "data" is modified in-place, by appending a categorical
        pandas.Series (as a new column).  The Series is named as specified in the "name" parameter.
        
    When in-place is False, returns a categorical pandas.Series (as above) and "data"
        is left unchanged.
    
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data expected a pandas.DataFrame; got %s instead" % type(data).__name__)
    
    #if not isinstance(parameter, str):
        #raise TypeError("parameter expected to be a str; got %s instead" % type(parameter).__name__)
    
    if parameter not in data.columns:
        raise ValueError("Parameter %s is not found in data columns" % parameter)
    
    if isinstance(values, (tuple, list)):
        if not all([isinstance(v, numbers.Number) for v in values]):
            raise TypeError("values sequence expected to contain only numbers")
        
    elif isinstance(values, np.ndarray):
        if values.ndim > 2:
            raise TypeError("when a numpy array, values must have atmost two dimensions; currently it has %d dimensions" % values.ndim)
        
        if values.ndim == 2:
            if any([s>1 for s in values.shape]):
                raise TypeError("when a 2D numpy array, values must be a vector; got %s shape instead" % str(values.shape))
            
            values = values.flatten()
            
        if not np.isreal(values.dtype):
            raise TypeError("values array expected to have builtin real number type; got %s instead" % values.dtype)
    
    else:
        raise TypeError("values expected to be a sequence (tuple or list) or a numpy array vector; got %s instead" % type(values).__name__)
    
    if not isinstance(name, str):
        raise TypeError("name expected to be a str; got %s instead" % type(name).__name__)
    
    name = strutils.str2symbol(name)
    
    categories = ["%d-%d" % (values[k-1], values[k]) for k in range(1, len(values))]
    
    #print(categories)
    
    cat_series = pd.Series(index = data.index, dtype="category", name = name)
    
    cat_series.cat.set_categories(categories, inplace=True)

    for i in data[parameter].index:
        val = data[parameter].loc[i]
        cat_val = None
        
        for k in range(1, len(categories)):
            if val >= values[k-1] and val <= values[k]:
                cat_val = categories[k-1]
                
            else:
                continue
            
        if cat_val is None:
            cat_val = categories[-1]
        
        cat_series.loc[i] = cat_val
        
    if inplace:
        data[name] = cat_series
        
    else:
        return cat_series
    
def addGenotype(data, value):
    """Adds genotype to LSCaT result data as categorical column.
    
    Modifies data in-place
    
    Positional parameters:
    ======================
    
    data -- LSCaT result DataFrame
    
    value -- string, typically one of "wt", "het", "hom", "na" 
            (case-insensitive) but not restricted to these
    
    Returns
    =======
    
    None (modified data in-place)
    
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Expecting a pandas.DataFrame; got %s instead" % type(data).__name__)
    
    if not isinstance(value, str):
        if len(value.strip()) == 0:
            value = "NA"
            
    elif value is None:
        value = "NA"
        
    else:
        raise TypeError("value expected to be a string or None; got %s instead" % type(value).__name__)
    
    #if value.lower().strip() not in ("wt", "het", "hom", "na"):
        #raise ValueError("value expected to be one of 'wt', 'het', 'hom', 'NA'; got %s instead" % value)
    
    genotype = pd.Series([value] * data.index.size)#.astype("category")
    genotype.name = "Genotype"
    
    data.insert(0, "Genotype", genotype.astype("category"))
    

    
def group(data,
        parameters=("Amplitude_EPSCaT_0", 
                    "Fit_EPSCaT_0_Amplitude", 
                    "Fit_EPSCaT_0_taudecay_0", 
                    "Integration_EPSCaT_Simpson", 
                    "Amplitude_EPSCaT_0_norm_to_1bAP", 
                    "Fit_EPSCaT_0_Amplitude_norm_to_1bAP", 
                    "Fit_EPSCaT_0_taudecay_0_norm_to_1bAP", 
                    "Integration_EPSCaT_Simpson_norm_to_1bAP"),
        grouping=("Unit_Type", "somatic_dist_2", "Protocol")):
    """Wrapper around pandas.DataFrame.groupby()
    Discards data according to boolean condition.
    
    Positional parameters:
    ======================
    data = a LSCaT result DataFrame
    
    Named parameters:
    ==================
    
    parameters = sequence (tuple, list) of LSCaT measures ; 
                default is ("Amplitude_EPSCaT_0", 
                            "Fit_EPSCaT_0_Amplitude", 
                            "Fit_EPSCaT_0_taudecay_0", 
                            "Integration_EPSCaT_Simpson", 
                            "Amplitude_EPSCaT_0_norm_to_1bAP", 
                            "Fit_EPSCaT_0_Amplitude_norm_to_1bAP", 
                            "Fit_EPSCaT_0_taudecay_0_norm_to_1bAP", 
                            "Integration_EPSCaT_Simpson_norm_to_1bAP")
                            
    grouping = str, or a sequence (tuple or list) of grouping LSCaT measures 
                (names of columns with categorical data)
                default is ("Unit_Type", "somatic_dist_2", "Protocol")
                
    Returns:
    ========
    ret: DataFrame with those parameters that are available in the series, among the selected parameters
    
    gby: a pd.DataFrameGroupedBy object (the result of the gouping)
    
    pars: list of str with the names of the available parameters returned in ret
    
    
    a GroupedBy object with the data grouping itself (actually, a DataFrameGroupedBy object)
        This contains all columns in the original data except for the 
        categorical ones used in grouping  unless "restricted" is True, in 
        which case it will only contain the columns specified by the 
        "parameters" argument.
        
            
    
                
    Called by aggregateParameters() function to perform grouping before applying
    any aggregation function.
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data expected to be a pandas DataFrame; got %s instead" % type(data).__name__)
    
    if parameters is None:
        parameters = ["all"]
        
    elif isinstance(parameters, str):
        if parameters not in data.columns:
            raise ValueError("parameter %s not found in data" % parameters)
        
        parameters = [parameters]
        
    elif isinstance(parameters, (tuple, list)):
        if len(parameters) == 0:
            parameters = ["all"]
            
        elif not all([isinstance(p, str) for p in parameters]):
            raise TypeError("parameters sequence must contain only strings")
        
    else:
        raise TypeError("parameters expected to be a string or a sequence of strings with vlaid columns names in data; got %s instead" % type(parameters).__name__)
    
    if isinstance(parameters, tuple):
        parameters = [p for p in parameters]
    
    if parameters[0].lower().strip() == "all":
        available_parameters = [p for p in data.columns if data[p].dtype == np.float64 ]
        
    else:
        available_parameters = [p for p in parameters if p in data.columns]
    
    if len(available_parameters) == 0:
        raise ValueError("None of the specified parameters were found in data")
    
    if not all([np.isreal(data[p]).all() or np.iscomplex(data[p]).all() for p in available_parameters]):
        raise TypeError("parameter data must be numeric")
    
    if isinstance(grouping, str):
        if grouping not in data.columns:
            raise ValueError("grouping %s not found in data" % grouping)
        
        grouping = [grouping]
            
    elif isinstance(grouping, (tuple, list)):
        if not all([isinstance(p, str) for p in grouping]):
            raise TypeError("grouping sequence must contain only strings (valid column names)")
        
    else:
        raise TypeError("grouping expected to be a string or a sequence of strings with valid columns names in data; got %s instead" % type(grouping).__name__)
    
    if isinstance(grouping, tuple):
        # NOTE: 2018-11-29 14:04:36 
        # if the grouping parameter is a tuple it might be interpreted as a single
        # key (I guess for multi indexing logic) so best is to convert it to a list
        
        grouping = [g for g in grouping]
        
    available_grouping = [p for p in grouping if p in data.columns]
    
    if len(available_grouping) == 0:
        raise ValueError("None of the specified grouping columns were found in data")
    
    if not all([data[p].dtype.name == "category" for p in available_grouping]):
        raise TypeError("all grouping parameters must contain categorical data")
    
    series_dict = dict()
    
    for c in available_grouping + available_parameters:
        series_dict[c] = data[c]
        
    ret = pd.DataFrame(series_dict)
    
    
    # NOTE: 2019-01-13 22:24:45
    # apply grouping on data_view (which is data filtered on ALL the conditions)
    return ret, ret.groupby(available_grouping), available_parameters
    
def group_cond(data,
        parameters=("Amplitude_EPSCaT_0", 
                    "Fit_EPSCaT_0_Amplitude", 
                    "Fit_EPSCaT_0_taudecay_0", 
                    "Integration_EPSCaT_Simpson", 
                    "Amplitude_EPSCaT_0_norm_to_1bAP", 
                    "Fit_EPSCaT_0_Amplitude_norm_to_1bAP", 
                    "Fit_EPSCaT_0_taudecay_0_norm_to_1bAP", 
                    "Integration_EPSCaT_Simpson_norm_to_1bAP"),
        grouping=("Unit_Type", "somatic_dist_2", "Protocol"),
        conditions="FailSuccess_EPSCaT_0_success",
        restrict=False):
    """Wraps around pandas.DataFrame.groupby()
    Discards data according to boolean condition.
    
    Positional parameters:
    ======================
    data = a LSCaT result DataFrame
    
    Named parameters:
    ==================
    
    parameters = sequence (tuple, list) of LSCaT measures ; 
                default is ("Amplitude_EPSCaT_0", 
                            "Fit_EPSCaT_0_Amplitude", 
                            "Fit_EPSCaT_0_taudecay_0", 
                            "Integration_EPSCaT_Simpson", 
                            "Amplitude_EPSCaT_0_norm_to_1bAP", 
                            "Fit_EPSCaT_0_Amplitude_norm_to_1bAP", 
                            "Fit_EPSCaT_0_taudecay_0_norm_to_1bAP", 
                            "Integration_EPSCaT_Simpson_norm_to_1bAP")
                            
    grouping = str, or a sequence (tuple or list) of grouping LSCaT measures 
                (names of columns with categorical data)
                default is ("Unit_Type", "somatic_dist_2", "Protocol")
                
    conditions = str, or a sequence (tuple or list) of names of boolean columns; only data 
                that is  simultaneously True in these columns will be considered
                default is ("FailSuccess_EPSCaT_0_success",)
                
                NOTE: if no condition is required, then pass the empty tuple: ()
                        
                NOTE: It is recommended to always have "FailSuccess_EPSCaT_0_success"
                        boolean column as a condition
                
    restrict = boolean, default False
            When True, only the columns for the parameters specified above will 
            be stored in the returned GroupedBy object (see below).
            
            When False (default), all columns in the data (except for the 
            categorical ones used in grouping) will be stored in the returned
            GroupedBy object.
                
    Returns:
    ========
    
    a GroupedBy object with the data grouping itself (actually, a DataFrameGroupedBy object)
        This contains all columns in the original data except for the 
        categorical ones used in grouping  unless "restricted" is True, in 
        which case it will only contain the columns specified by the 
        "parameters" argument.
        
            
    
                
    Called by aggregateParameters() function to perform grouping before applying
    any aggregation function.
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data expected to be a pandas DataFrame; got %s instead" % type(data).__name__)
    
    if isinstance(parameters, str):
        if parameters not in data.columns:
            raise ValueError("parameter %s not found in data" % parameters)
        
        parameters = [parameters]
        
    elif isinstance(parameters, (tuple, list)):
        if not all([isinstance(p, str) for p in parameters]):
            raise TypeError("parameters sequence must contain only strings")
        
        if any([p not in data.columns for p in parameters]):
            raise ValueError("at least one of the parameters is not found in data")
        
    else:
        raise TypeError("parameters expected to be a string or a sequence of strings with vlaid columns names in data; got %s instead" % type(parameters).__name__)
    
    if isinstance(parameters, tuple):
        parameters = [p for p in parameters]
    
    if not all([np.isreal(data[p]).all() or np.iscomplex(data[p]).all() for p in parameters]):
        raise TypeError("parameter data must be numeric")
    
    if isinstance(grouping, str):
        if grouping not in data.columns:
            raise ValueError("grouping %s not found in data" % grouping)
        
            grouping = [grouping]
            
    elif isinstance(grouping, (tuple, list)):
        if not all([isinstance(p, str) for p in grouping]):
            raise TypeError("grouping sequence must contain only strings (valid column names)")
        
        if any([p not in data.columns for p in grouping]):
            raise ValueError("at least one of the speicified grouping columns is not found in data")
        
    else:
        raise TypeError("grouping expected to be a string or a sequence of strings with valid columns names in data; got %s instead" % type(grouping).__name__)
    
    if isinstance(grouping, tuple):
        # NOTE: 2018-11-29 14:04:36 
        # if the grouping parameter is a tuple it might be interpreted as a single
        # key (I guess for multi indexing logic) so best is to convert it to a list
        
        grouping = [g for g in grouping]
        
    #print("conditions: ", conditions)
    
    if isinstance(conditions, str):
        if conditions not in data.columns:
            raise ValueError("condition %s not found in data" % conditions)
        
        conditions = [conditions]
    
    elif isinstance(conditions, (tuple, list)):
        if not all([isinstance(s, str) for s in conditions]):
            raise TypeError("conditions sequence must contain only strings (valid column names)")
        
        if any([p not in data.columns for p in conditions]):
            raise ValueError("at least one of the specified conditions is not found in data")
        
    else:
        raise TypeError("conditions are expected to be a string or a sequence of strings with valid columns names in data; got %s instead" % type(conditions).__name__)
            
    
    if not all([data[p].dtype.name == "category" for p in grouping]):
        raise TypeError("all grouping parameters must contain categorical data")
    
    if not all([data[p].dtype == bool for p in conditions]):
        raise TypeError("all conditions must contain boolean data")
    
    # NOTE: 2019-01-13 22:24:35
    # apply conditions = get a data view filtered on ALL conditions
    if len(conditions):
        data_true_index = data.loc[:,conditions[0]]
        
        if len(conditions) > 1:
            for c in conditions[1:]:
                data_true_index &= data.loc[:,c]
                
        data_view = data.loc[data_true_index, :]
        
    else:
        data_view = data
    
    if restrict:
        data_view = data_view.loc[:, [p for p in grouping + parameters]]
    
    # NOTE: 2019-01-13 22:24:45
    # apply grouping on data_view (which is data filtered on ALL the conditions)
    return data_view.groupby(grouping)
    
    
def aggregateParameters(data, 
                        parameters=("Amplitude_EPSCaT_0", 
                                    "Fit_EPSCaT_0_Amplitude", 
                                    "Fit_EPSCaT_0_taudecay_0", 
                                    "Integration_EPSCaT_Simpson", 
                                    "Amplitude_EPSCaT_0_norm_to_1bAP", 
                                    "Fit_EPSCaT_0_Amplitude_norm_to_1bAP", 
                                    "Fit_EPSCaT_0_taudecay_0_norm_to_1bAP", 
                                    "Integration_EPSCaT_Simpson_norm_to_1bAP"), 
                        grouping=("Unit_Type", "somatic_dist_2", "Protocol"),
                        functions=(np.nanmean, np.nanstd, sgp.nansem, sgp.nansize)):
    """Aggregates values in the LSCaT result DataFrame
    
    NOTE: the LSCaT result DataFrame would have already been pre-processed
        with categoriseLSCaTResult and categoriseNumericalData, especially if
        the default function parameter values are to be used
    
    Positional parameters:
    ======================
    data = a LSCaT result (pandas DataFrame)
    
    Named parameters:
    ==================
    
    parameters = sequence (tuple, list) of LSCaT measures ; 
                default is ("Amplitude_EPSCaT_0", 
                            "Fit_EPSCaT_0_Amplitude", "Fit_EPSCaT_0_taudecay_0", 
                            "Integration_EPSCaT_Simpson", 
                            "Amplitude_EPSCaT_0_norm_to_1bAP", 
                            "Fit_EPSCaT_0_Amplitude_norm_to_1bAP", "Fit_EPSCaT_0_taudecay_0_norm_to_1bAP", 
                            "Integration_EPSCaT_Simpson_norm_to_1bAP")
                            
    grouping = str, or a sequence (tuple or list) of grouping LSCaT measures 
                (names of columns with categorical data)
                default is ("Unit_Type", "somatic_dist_2", "Protocol")
                
    functions = sequence (tuple, list) of functions used to obtain agregated values
                default is (np.nanmean, sgp.sem)
                where sgp is an alias to signalprocessing module
                
    Returns
    =======
    
    tuple containing :
        a DataFrame with the aggregation
        
        a GroupedBy object with the data grouping itself (actually, a DataFrameGroupedBy object)
            This contains all columns in the original data except for the 
            categorical ones used in grouping  unless "restricted" is True, in 
            which case it will only contain the columns specified by the 
            "parameters" argument.
            
    Calls group(data, parameters, grouping to group data then aggregates with 
    each of the functions specified in "functions" parameter.
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data expected to be a pandas DataFrame; got %s instead" % type(data).__name__)
    
    if type(functions).__name__ in ("function", "partial"):
        functions = [functions]
        
    elif isinstance(functions, (tuple, list)):
        if not all([type(f).__name__ in ("function", "partial") for f in functions]):
            raise TypeError("functions expected to contain python functions of functool.partial functions")
        
    else:
        raise TypeError("functions expected to be a python function or a sequence of python functions; got %s instead" % type(functions).__name__)
    
    ret, ret_grouping, available_parameters = group(data, parameters=parameters, grouping=grouping)
    
    series_dict = dict()
    
    # use available_parameters as returned by group() function because some of them
    # may be missing
    for p in available_parameters:
        for f in functions:
            if type(f).__name__ == "partial":
                func_name = f.func.__name__
            else:
                func_name = f.__name__
                
            if "lambda" in func_name:
                s_name = p
                
            else:
                s_name = "%s_%s" % (p, func_name)
                
            #print("Calculating %s for %s" % (func_name, p))
            #s = data_grouping[p].agg(f)
            
            series_dict[s_name] = ret_grouping[p].agg(f)
            
    return pd.DataFrame(series_dict), ret_grouping
        
def aggregateParameters_cond(data, 
                        parameters=("Amplitude_EPSCaT_0", 
                                    "Fit_EPSCaT_0_Amplitude", 
                                    "Fit_EPSCaT_0_taudecay_0", 
                                    "Integration_EPSCaT_Simpson", 
                                    "Amplitude_EPSCaT_0_norm_to_1bAP", 
                                    "Fit_EPSCaT_0_Amplitude_norm_to_1bAP", 
                                    "Fit_EPSCaT_0_taudecay_0_norm_to_1bAP", 
                                    "Integration_EPSCaT_Simpson_norm_to_1bAP"), 
                        grouping=("Unit_Type", "somatic_dist_2", "Protocol"),
                        conditions = "FailSuccess_EPSCaT_0_success",
                        functions=(np.nanmean, np.nanstd, sgp.nansem, sgp.nansize),
                        restrict=False):
    """Aggregates values in the LSCaT result DataFrame
    
    NOTE: the LSCaT result DataFrame would have already been pre-processed
        with categoriseLSCaTResult and categoriseNumericalData, especially if
        the default function parameter values are to be used
    
    Positional parameters:
    ======================
    data = a LSCaT result (pandas DataFrame)
    
    Named parameters:
    ==================
    
    parameters = sequence (tuple, list) of LSCaT measures ; 
                default is ("Amplitude_EPSCaT_0", 
                            "Fit_EPSCaT_0_Amplitude", "Fit_EPSCaT_0_taudecay_0", 
                            "Integration_EPSCaT_Simpson", 
                            "Amplitude_EPSCaT_0_norm_to_1bAP", 
                            "Fit_EPSCaT_0_Amplitude_norm_to_1bAP", "Fit_EPSCaT_0_taudecay_0_norm_to_1bAP", 
                            "Integration_EPSCaT_Simpson_norm_to_1bAP")
                            
    grouping = str, or a sequence (tuple or list) of grouping LSCaT measures 
                (names of columns with categorical data)
                default is ("Unit_Type", "somatic_dist_2", "Protocol")
                
    conditions = str, or a sequence (tuple or list) of names of boolean columns; only data 
                that is  simultaneously True in these columns will be considered
                default is ("FailSuccess_EPSCaT_0_success",)
                
                NOTE: if no condition is required, then pass the empty tuple: ()
                        
                NOTE: It is recommended to always have "FailSuccess_EPSCaT_0_success"
                        boolean column as a condition
                
    functions = sequence (tuple, list) of functions used to obtain agregated values
                default is (np.nanmean, sgp.sem)
                where sgp is an alias to signalprocessing module
                
    restrict = boolean, default False
            When True, only the columns for the parameters specified above will 
            be stored in the returned GroupedBy object (see below).
            
            When False (default), all columns in the data (except for the 
            categorical ones used in grouping) will be stored in the returned
            GroupedBy object.
                
    Returns
    =======
    
    tuple containing :
        a DataFrame with the aggregation
        
        a GroupedBy object with the data grouping itself (actually, a DataFrameGroupedBy object)
            This contains all columns in the original data except for the 
            categorical ones used in grouping  unless "restricted" is True, in 
            which case it will only contain the columns specified by the 
            "parameters" argument.
            
            
        NOTE: regardless of "restrict", the aggregated DataFrame will only
            contain the aggregated data from the columns specified by "parameters"
            
    
    Calls group_cond(data, parameters, grouping, conditions, restrict) to group data
    then apply aggregation with each of the specified functions.    
                            
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data expected to be a pandas DataFrame; got %s instead" % type(data).__name__)
    
    if type(functions).__name__ in ("function", "partial"):
        functions = [functions]
        
    elif isinstance(functions, (tuple, list)):
        if not all([type(f).__name__ in ("function", "partial") for f in functions]):
            raise TypeError("functions expected to contain python functions of functool.partial functions")
        
    else:
        raise TypeError("functions expected to be a python function or a sequence of python functions; got %s instead" % type(functions).__name__)
    
    data_grouping = group(data, parameters=parameters, grouping=grouping, conditions=conditions, restrict=restrict)
    
    series_dict = dict()
    
    # parameters are to be found in the GroupedBy object
    for p in parameters:
        for f in functions:
            if type(f).__name__ == "partial":
                func_name = f.func.__name__
            else:
                func_name = f.__name__

            s_name = "%s_%s" % (p, func_name)
                
            #print("Calculating %s for %s" % (func_name, p))
            s = data_grouping[p].agg(f)
            
            series_dict[s_name] = s
            
    return pd.DataFrame(series_dict), data_grouping
        
#def getStatistic(data, parameter, func, **conditions):
    #"""Applies statistic function to a subset of data in the DataFrame data.
    #See aggregateParameters for a better solution to apply several statisical 
    #functions
    #Parameters
    #==========
    #data - pandas DataFrame: result of LSCaT analysis
    
    #parameter
    
    #parameter
    
    #"""
    #if not isinstance(data, pd.DataFrame):
        #raise TypeError("Expecting a pandas Data Frame; got %s instead" % type(data).__name__)
    
    
def collectParameterStatAcrossCells(data, parameter, protocol):
    """Brings together per-cell statistic
    
    Parameters:
    ===========
    data: a sequence of dataframes produced as cross-section view of a "stats"
        multi-indexed data frame (in itself produced by aggregateParameters(...))
        
        parameter: a str or a list of str
        
        protocol: a str (Protocol category)
    
    
    Returns:
    =======
    
    When parameters is a str:
        a new pandas.Series
        
    When parameters is a list of str:
        a new pandas.DataFrame
        
    If neither the parameters nor the protocol are found in data:
        returns None
    
    
    """
    
    #k = 0
    
    results = list()
    
    catindex = list()
    
    
    for df in data:
        #results.append(df.xs((protocol), level="Protocol")[parameter])
        try:
            val = df.xs((protocol), level="Protocol")[parameter]
            catindex.append(pd.Series(val.index))
            results.append(val)
            
        except:
            traceback.print_exc()
            
        #index = df.index

        #protocol_ndx = [i for i in index if protocol in i]
        
        #if len(protocol_ndx) == 0:
            #continue
        
        #if parameter not in df.columns:
            #continue
        
        #results.append(df.loc[protocol_ndx, parameter])
        
        #if k == 0:
            #result = df.loc[protocol_ndx, parameter]
            
        #else:
            #result = pd.concat(result, df.loc[protocol_ndx, parameter])
        
        #k += 1
    if len(results):
        result_index = pd.concat(catindex)
        result = pd.concat(tuple(results), ignore_index=True)
        result.index = result_index
        return result

    
def collectMeansAcrossCells(data, protocol):
    """Shorthand for collectParameterStatAcrossCells for "nanmean" values.
    """
    
    parameters = [c for c in data[0].columns if "nanmean" in c]
    
    return collectParameterStatAcrossCells(data, parameters, protocol)



def correctUnitType(data):
    #unit_types = sorted([v for v in UnitTypes.values()])
    
    unit_types = pd.Series([UnitTypes[x[0]] for x in data.Unit]).astype("category")
    
    data.Unit_Type = pd.Categorical(unit_types)
        
        
def blankUncageArtifactInLineScans(data, time, width, bgstart, bgend, frame=0):
    """
    Blanks uncaging artifact
    
    data: ScanData with line scan images.
    time: scalar float or quantity (s) or a sequence of these (including a numpy array)
    width: int pixels
    bgstart, bgend: int: start & end indices of the time axis (in axis units),
        for calculation of the background: the average of this region will be written over the 
        uncaging artifact.
    """
    scans = data.scans
    
    if isinstance(time, numbers.Number):
        times = [time]
        
    elif isinstance(time, np.ndarray):
        if time.size == 1:
            times = [time]
            
        else:
            times = list(time[:])
            
    elif isinstance(time, (tuple, list)):
        times = time
            
    else:
        raise TypeError("time expected a scalar or a sequence of values; got %s instead" % type(time).__name__)
    
    for img in scans:
        if "t" not in img.axistags:
            continue

        axcal = AxesCalibration(img.axistags["t"])
        
        
        for t in time:
            start = int(axcal.getDistanceInSamples(t, "t"))
            end = start + width
            
            bstart = int(axcal.getDistanceInSamples(bgstart, "t"))
            bend = int(axcal.getDistanceInSamples(bgend, "t"))
            
            #print("bstart", bstart, "bend", bend)
            
            if bend-bstart <=0:
                val = 0
                
            else:
                slicing = dict([(ax.key, None) for ax in img.axistags])
                slicing["t"] = range(bstart,bend)
                #print("background slicing", slicing)
                if img.ndim > 2:
                    slicing[img.axistags[2].key] = slice(frame, frame+1)
                    
                imgIndex = imageIndexTuple(img, slicing)
                #print("background index", imgIndex)
                val = img[imgIndex].mean()
                
            slicing = dict([(ax.key, None) for ax in img.axistags])
            slicing["t"] = range(start, end)
            
            #print("blanking slicing", slicing)
            imgIndex = imageIndexTuple(img, slicing)
            #print("blanking index", imgIndex)
            img[imgIndex] = val
        
@magics_class
class LSCaTMagics(Magics):
    @line_magic
    @needs_local_scope
    def LSCaT(self, line, local_ns):
        if len(line.strip()):
            lsdata = local_ns.get(line, None)
        else:
            lsdata = None
            
        mw = local_ns.get("mainWindow", None)
        
        if mw.__class__.__name__ == "ScipyenWindow":
            lscatWindow = mw.newViewer(LSCaTWindow, parent=mw, win_title="LSCaT")
            if isinstance(lsdata,  ScanData):
                lscatWindow.view(lsdata)
            else:
                lscatWindow.show()
        
def launch():
    try:
        win = mainWindow.newViewer(LSCaTWindow, parent = mainWindow, win_title="LSCaT")
        win.show()
    except:
        traceback.print_exc()
        
        
def init_scipyen_plugin():
    return {"Applications|LSCaT":launch}


def load_ipython_extension(ipython):
    ipython.register_magics(LSCaTMagics)
    
